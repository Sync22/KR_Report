import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { MarketSnapshot } from "../domain/market.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const SOURCE = "toss_openapi";
const STOCK_LIMIT = 5;
const ETF_LIMIT = 5;
const INDEX_LIMIT = 10;
const SNAPSHOT_CUTOFF = "9999-12-31";
const ALLOWED_MISSING_DOMAINS = new Set([
  "top20",
  "security_metadata",
  "market_indices",
  "market_flow",
  "candidate_close_reassessment",
]);

type StockRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

type EtfRow = {
  business_date: string;
  etf_code: string;
  etf_name: string;
  close_price: number | null;
  change_percent: number | null;
  nav: number | null;
  volume: number | null;
  turnover: number | null;
  underlying_index_name: string | null;
};

type IndexRow = {
  business_date: string;
  index_series: string;
  index_name: string;
  close_index: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
};

function formatFlowAmount(value: number): string {
  const amount = Math.abs(value);
  if (amount >= 1_000_000_000_000) {
    return `${new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1, roundingMode: "halfEven", useGrouping: false }).format(amount / 1_000_000_000_000)}조`;
  }
  if (amount >= 100_000_000) {
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, roundingMode: "halfEven", useGrouping: false }).format(amount / 100_000_000)}억`;
  }
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount)}원`;
}

function formatNav(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    roundingMode: "halfEven",
  }).format(value);
}

function etfEvidenceLabel(item: EtfRow): string {
  const parts: string[] = [];
  if (item.turnover !== null) parts.push(`거래대금 ${formatFlowAmount(item.turnover)}`);
  if (item.nav !== null) parts.push(`NAV ${formatNav(item.nav)}`);
  if (item.underlying_index_name) parts.push(`기초지수 ${item.underlying_index_name}`);
  return parts.length ? parts.join(" · ") : "저장 ETF 일별매매정보";
}

function latestSnapshotDate(database: DatabaseSync): string | null {
  const row = database.prepare(`
    SELECT MAX(business_date) AS business_date
    FROM (
      SELECT MAX(business_date) AS business_date
      FROM toss_market_context_snapshots
      WHERE business_date <= ? AND source = ?
      UNION ALL
      SELECT MAX(business_date) AS business_date
      FROM stock_market_daily
      WHERE business_date <= ? AND source = ?
        AND (change_amount IS NOT NULL OR change_percent IS NOT NULL OR volume IS NOT NULL
             OR turnover IS NOT NULL OR market_cap IS NOT NULL OR listed_shares IS NOT NULL
             OR open_price IS NOT NULL OR high_price IS NOT NULL OR low_price IS NOT NULL)
      UNION ALL
      SELECT MAX(business_date) AS business_date
      FROM etf_daily_snapshots
      WHERE business_date <= ? AND source = ?
      UNION ALL
      SELECT MAX(business_date) AS business_date
      FROM market_index_daily
      WHERE business_date <= ? AND source = ?
    )
  `).get(
    SNAPSHOT_CUTOFF, SOURCE,
    SNAPSHOT_CUTOFF, SOURCE,
    SNAPSHOT_CUTOFF, SOURCE,
    SNAPSHOT_CUTOFF, SOURCE,
  );
  const value = row?.business_date;
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" || !isBusinessDate(value)) throw new Error("Invalid stored market snapshot date");
  return value;
}

function tossCaptureState(database: DatabaseSync, businessDate: string | null) {
  const row = businessDate === null
    ? database.prepare(`
        SELECT status, business_date, detail
        FROM operation_events
        WHERE component = ? AND event_type = ?
        ORDER BY event_time DESC, id DESC
        LIMIT 1
      `).get("toss-market-context", "capture")
    : database.prepare(`
        SELECT status, business_date, detail
        FROM operation_events
        WHERE component = ? AND event_type = ? AND business_date = ?
        ORDER BY event_time DESC, id DESC
        LIMIT 1
      `).get("toss-market-context", "capture", businessDate);
  if (!row) return null;
  if (typeof row.status !== "string") throw new Error("Invalid stored market capture status");
  let eventDate: string | null = null;
  if (row.business_date !== null && row.business_date !== undefined && row.business_date !== "") {
    if (typeof row.business_date !== "string" || !isBusinessDate(row.business_date)) {
      throw new Error("Invalid stored market capture date");
    }
    eventDate = row.business_date;
  }
  const detail = typeof row.detail === "string" ? row.detail : "";
  const missingPart = detail.split(";").find((part) => part.trim().startsWith("missing_domains="));
  const missingSeparator = missingPart?.indexOf("=") ?? -1;
  const missingRaw = missingPart && missingSeparator >= 0 ? missingPart.slice(missingSeparator + 1).trim() : "";
  return {
    status: row.status,
    business_date: eventDate,
    missing_domains: missingRaw.split(",").filter((value) => ALLOWED_MISSING_DOMAINS.has(value)),
  };
}

function stockMarketItem(row: StockRow) {
  return {
    business_date: row.business_date,
    stock_code: row.stock_code,
    stock_name: row.stock_name,
    market: row.market,
    close_price: row.close_price,
    change_percent: row.change_percent,
    volume: row.volume,
    turnover: row.turnover,
    fetched_at: row.fetched_at,
  };
}

function etfItem(row: EtfRow) {
  return {
    business_date: row.business_date,
    etf_code: row.etf_code,
    etf_name: row.etf_name,
    close_price: row.close_price,
    change_percent: row.change_percent,
    nav: row.nav,
    volume: row.volume,
    turnover: row.turnover,
    underlying_index_name: row.underlying_index_name,
    evidence_label: etfEvidenceLabel(row),
    rotation_reference: "저장 ETF 거래대금/NAV/기초지수 기준",
  };
}

function marketIndexItem(row: IndexRow) {
  return {
    business_date: row.business_date,
    index_series: row.index_series,
    index_name: row.index_name,
    close_index: row.close_index,
    change_percent: row.change_percent,
    volume: row.volume,
    turnover: row.turnover,
  };
}

export function buildMarketSnapshot(
  database: DatabaseSync,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): MarketSnapshot {
  const snapshotDate = latestSnapshotDate(database);
  const captureState = tossCaptureState(database, snapshotDate);
  const latestCaptureAttempt = tossCaptureState(database, null);
  const stockRows = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, close_price, change_percent, volume, turnover, fetched_at
    FROM stock_market_daily
    WHERE business_date = ? AND market = ? AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, stock_code ASC
    LIMIT ?
  `);
  const etfRows = database.prepare(`
    SELECT business_date, etf_code, etf_name, close_price, change_percent, nav, volume, turnover, underlying_index_name
    FROM etf_daily_snapshots
    WHERE business_date = ? AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
    LIMIT ?
  `);
  const indexRows = database.prepare(`
    SELECT business_date, index_series, index_name, close_index, change_percent, volume, turnover
    FROM market_index_daily
    WHERE business_date = ? AND source = ?
    ORDER BY index_series ASC, index_name ASC
    LIMIT ?
  `);
  const topKospiStocks = snapshotDate
    ? (stockRows.all(snapshotDate, "KOSPI", SOURCE, STOCK_LIMIT) as unknown as StockRow[]).map(stockMarketItem)
    : [];
  const topKosdaqStocks = snapshotDate
    ? (stockRows.all(snapshotDate, "KOSDAQ", SOURCE, STOCK_LIMIT) as unknown as StockRow[]).map(stockMarketItem)
    : [];
  const topEtfs = snapshotDate
    ? (etfRows.all(snapshotDate, SOURCE, ETF_LIMIT) as unknown as EtfRow[]).map(etfItem)
    : [];
  const marketIndices = snapshotDate
    ? (indexRows.all(snapshotDate, SOURCE, INDEX_LIMIT) as unknown as IndexRow[]).map(marketIndexItem)
    : [];

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    snapshot_source: SOURCE,
    snapshot_date: snapshotDate,
    capture_status: captureState?.status ?? null,
    missing_domains: captureState?.missing_domains ?? [],
    latest_capture_attempt: latestCaptureAttempt,
    top_kospi_stocks: topKospiStocks,
    top_kosdaq_stocks: topKosdaqStocks,
    top_etfs: topEtfs,
    market_indices: marketIndices,
  };
}

export function getMarketSnapshot(): MarketSnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildMarketSnapshot(database, new Date(), timezone));
}
