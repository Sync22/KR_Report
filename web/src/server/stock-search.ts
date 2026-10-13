import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { StockSearchItem, StockSearchSnapshot } from "../domain/stocks.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const SOURCE = "stored_stock_universe";
const STOCK_SEARCH_DEFAULT_LIMIT = 8;
const STOCK_SEARCH_MAX_LIMIT = 20;

type StockSearchRow = Omit<StockSearchItem, "has_selected_date_report" | "has_selected_date_toss" | "has_news_observation" | "display_status">;

function emptyStockSearchSnapshot(businessDate: string, query: string, now: Date, timezone: string): StockSearchSnapshot {
  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    source: SOURCE,
    stock_universe_reference_date: null,
    live_fetch: false,
    available: false,
    query,
    items: [],
    empty_state: "검색어를 입력하세요.",
  };
}

function selectedDateCodes(
  database: DatabaseSync,
  table: "reports" | "report_linked_news_evidence",
  dateColumn: "business_date" | "target_date",
  businessDate: string,
  stockCodes: string[],
): Set<string> {
  if (!stockCodes.length) return new Set();
  const placeholders = stockCodes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT DISTINCT stock_code
    FROM ${table}
    WHERE ${dateColumn} = ? AND stock_code IN (${placeholders})
  `).all(businessDate, ...stockCodes);
  return new Set(rows.map((row) => String(row.stock_code || "")));
}

export function parseStockSearchLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? STOCK_SEARCH_DEFAULT_LIMIT : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, STOCK_SEARCH_MAX_LIMIT)) : STOCK_SEARCH_DEFAULT_LIMIT;
}

export function buildStockSearchSnapshot(
  database: DatabaseSync,
  businessDate: string,
  query: string,
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): StockSearchSnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid stock search date");
  const normalizedQuery = query.trim();
  const maxLimit = Number.isInteger(limit)
    ? Math.max(1, Math.min(limit, STOCK_SEARCH_MAX_LIMIT))
    : STOCK_SEARCH_DEFAULT_LIMIT;
  if (!normalizedQuery) return emptyStockSearchSnapshot(businessDate, normalizedQuery, now, timezone);

  const likeQuery = `%${normalizedQuery}%`;
  const universeRow = database.prepare(`
    SELECT MAX(business_date) AS business_date
    FROM toss_stock_universe_cache
    WHERE business_date <= ?
  `).get(businessDate);
  const rawUniverseReferenceDate = universeRow?.business_date;
  if (rawUniverseReferenceDate !== null && rawUniverseReferenceDate !== undefined &&
    (typeof rawUniverseReferenceDate !== "string" || !isBusinessDate(rawUniverseReferenceDate))) {
    throw new Error("Invalid stored stock universe date");
  }
  const universeReferenceDate = typeof rawUniverseReferenceDate === "string" ? rawUniverseReferenceDate : null;
  const rows = database.prepare(`
    WITH latest_krx AS (
      SELECT k.stock_code, k.stock_name, k.market, k.business_date
      FROM krx_stock_metadata k
      JOIN (
        SELECT stock_code, MAX(business_date) AS business_date
        FROM krx_stock_metadata
        WHERE business_date <= ?
        GROUP BY stock_code
      ) latest
        ON latest.stock_code = k.stock_code
       AND latest.business_date = k.business_date
    ),
    latest_toss_universe AS (
      SELECT stock_code, stock_name, market, business_date
      FROM toss_stock_universe_cache
      WHERE business_date = ?
    ),
    market_candidates AS (
      SELECT stock_code, market,
             'stored_toss_stock_universe' AS market_source,
             business_date AS market_reference_date,
             0 AS source_rank
      FROM latest_toss_universe
      UNION ALL
      SELECT stock_code, market,
             'stored_krx_stock_metadata' AS market_source,
             business_date AS market_reference_date,
             1 AS source_rank
      FROM latest_krx
    ),
    market_reference AS (
      SELECT stock_code, market, market_source, market_reference_date
      FROM (
        SELECT stock_code, market, market_source, market_reference_date,
               ROW_NUMBER() OVER (
                 PARTITION BY stock_code
                 ORDER BY source_rank ASC
               ) AS row_number
        FROM market_candidates
        WHERE NULLIF(TRIM(COALESCE(market, '')), '') IS NOT NULL
      )
      WHERE row_number = 1
    ),
    candidates AS (
      SELECT daily.stock_code, daily.stock_name, market.market, market.market_source,
             market.market_reference_date, 0 AS source_rank
      FROM daily_stock_summaries daily
      LEFT JOIN market_reference market ON market.stock_code = daily.stock_code
      WHERE daily.business_date = ? AND daily.stock_code IS NOT NULL
      UNION ALL
      SELECT toss.stock_code, toss.stock_name, market.market, market.market_source,
             market.market_reference_date, 1 AS source_rank
      FROM latest_toss_universe toss
      LEFT JOIN market_reference market ON market.stock_code = toss.stock_code
      WHERE toss.stock_code IS NOT NULL
      UNION ALL
      SELECT krx.stock_code, krx.stock_name, market.market, market.market_source,
             market.market_reference_date, 2 AS source_rank
      FROM latest_krx krx
      LEFT JOIN market_reference market ON market.stock_code = krx.stock_code
      WHERE krx.stock_code IS NOT NULL
      UNION ALL
      SELECT metadata.stock_code, metadata.stock_name, market.market, market.market_source,
             market.market_reference_date, 3 AS source_rank
      FROM stock_metadata metadata
      LEFT JOIN market_reference market ON market.stock_code = metadata.stock_code
      WHERE metadata.stock_code IS NOT NULL
      UNION ALL
      SELECT report.stock_code, report.stock_name, market.market, market.market_source,
             market.market_reference_date, 4 AS source_rank
      FROM reports report
      LEFT JOIN market_reference market ON market.stock_code = report.stock_code
      WHERE report.stock_code IS NOT NULL
    ),
    matched AS (
      SELECT TRIM(stock_code) AS stock_code,
             TRIM(COALESCE(stock_name, '')) AS stock_name,
             NULLIF(TRIM(COALESCE(market, '')), '') AS market,
             NULLIF(TRIM(COALESCE(market_source, '')), '') AS market_source,
             market_reference_date, source_rank
      FROM candidates
      WHERE TRIM(COALESCE(stock_code, '')) <> ''
        AND (
          stock_code LIKE ? COLLATE NOCASE
          OR stock_name LIKE ? COLLATE NOCASE
        )
    ),
    ranked AS (
      SELECT stock_code, stock_name, market, market_source, market_reference_date,
             source_rank,
             ROW_NUMBER() OVER (
               PARTITION BY stock_code
               ORDER BY source_rank ASC, stock_name ASC
             ) AS row_number
      FROM matched
    )
    SELECT stock_code, stock_name, market, market_source, market_reference_date
    FROM ranked
    WHERE row_number = 1
    ORDER BY CASE WHEN stock_code = ? THEN 0 ELSE 1 END,
             stock_name ASC,
             stock_code ASC
    LIMIT ?
  `).all(
    businessDate,
    universeReferenceDate,
    businessDate,
    likeQuery,
    likeQuery,
    normalizedQuery,
    maxLimit,
  ) as unknown as StockSearchRow[];

  const stockCodes = rows.filter((row) => row.stock_code).map((row) => row.stock_code);
  const reportCodes = selectedDateCodes(database, "reports", "business_date", businessDate, stockCodes);
  const newsCodes = selectedDateCodes(database, "report_linked_news_evidence", "target_date", businessDate, stockCodes);
  const tossCodes = stockCodes.length
    ? new Set(database.prepare(`
        SELECT stock_code
        FROM stock_market_daily
        WHERE business_date = ? AND source = ? AND stock_code IN (${stockCodes.map(() => "?").join(", ")})
      `).all(businessDate, "toss_openapi", ...stockCodes).map((row) => String(row.stock_code || "")))
    : new Set<string>();

  const items = rows.map((row) => {
    const hasReport = reportCodes.has(row.stock_code);
    const hasToss = tossCodes.has(row.stock_code);
    const hasNews = newsCodes.has(row.stock_code);
    return {
      ...row,
      stock_name: row.stock_name || row.stock_code,
      has_selected_date_report: hasReport,
      has_selected_date_toss: hasToss,
      has_news_observation: hasNews,
      display_status: [
        hasReport ? "당일 리포트 있음" : "당일 리포트 없음",
        hasToss ? "저장 Toss 있음" : "저장 Toss 없음",
        hasNews ? "뉴스 근거 있음" : "뉴스 근거 없음",
      ].join(" · "),
    };
  });

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    source: SOURCE,
    stock_universe_reference_date: universeReferenceDate,
    live_fetch: false,
    available: items.length > 0,
    query: normalizedQuery,
    items,
    empty_state: items.length ? null : "조회된 저장 종목이 없습니다.",
  };
}

export function getStockSearchSnapshot(
  businessDate: string,
  query: string,
  limit = STOCK_SEARCH_DEFAULT_LIMIT,
): StockSearchSnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid stock search date");
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  if (!query.trim()) {
    return emptyStockSearchSnapshot(businessDate, "", new Date(), timezone);
  }
  return withReadOnlyDatabase((database) => buildStockSearchSnapshot(database, businessDate, query, limit, new Date(), timezone));
}
