import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { CategoryDetailSnapshot } from "../domain/category-rotation.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type CategoryType = "sector" | "theme";
type CategoryDetailDTO = CategoryDetailSnapshot & { category_key: string };
type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string | null;
  generated_at: string;
};
type MarketReferenceRow = {
  business_date: string;
  stock_code: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

function isCategoryType(value: string): value is CategoryType {
  return value === "sector" || value === "theme";
}

function latestTypeSnapshotDate(database: DatabaseSync, type: CategoryType, businessDate: string): string | null {
  const row = database.prepare(`
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
  `).get(type, businessDate);
  const value = row?.snapshot_date;
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" || !isBusinessDate(value)) throw new Error("Invalid stored category snapshot date");
  return value;
}

function legacySectorRows(database: DatabaseSync, businessDate: string, categoryName: string): SummaryRow[] {
  return database.prepare(`
    SELECT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
           dss.broker_display, dss.target_price_min, dss.target_price_max, dss.dominant_opinion,
           dss.generated_at
    FROM daily_stock_summaries dss
    LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
    WHERE dss.business_date = ?
      AND COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, categoryName) as unknown as SummaryRow[];
}

function legacyThemeRows(database: DatabaseSync, businessDate: string, categoryName: string): SummaryRow[] {
  return database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max, dss.dominant_opinion,
                    dss.generated_at
    FROM daily_stock_summaries dss
    JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
    WHERE dss.business_date = ?
      AND COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, categoryName) as unknown as SummaryRow[];
}

function categoryKeyRows(database: DatabaseSync, businessDate: string, snapshotDate: string, type: CategoryType, categoryName: string): SummaryRow[] {
  return database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max, dss.dominant_opinion,
                    dss.generated_at
    FROM daily_stock_summaries dss
    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
    WHERE dss.business_date = ? AND cms.snapshot_date = ?
      AND cms.category_type = ? AND cms.category_key = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, snapshotDate, type, categoryName) as unknown as SummaryRow[];
}

function displayNameRows(database: DatabaseSync, businessDate: string, type: CategoryType, displayName: string): SummaryRow[] {
  return database.prepare(`
    WITH latest_snapshot AS (
      SELECT MAX(cms.snapshot_date) AS snapshot_date
      FROM category_membership_snapshots cms
      JOIN category_master cm
        ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
      WHERE cms.category_type = ? AND cms.display_name = ?
        AND cms.snapshot_date <= ? AND cm.enabled = 1
    )
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max, dss.dominant_opinion,
                    dss.generated_at
    FROM daily_stock_summaries dss
    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
    JOIN latest_snapshot latest ON latest.snapshot_date = cms.snapshot_date
    WHERE dss.business_date = ? AND cms.category_type = ? AND cms.display_name = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(type, displayName, businessDate, businessDate, type, displayName) as unknown as SummaryRow[];
}

function selectedDateMarketReferences(database: DatabaseSync, businessDate: string, summaries: SummaryRow[]): Map<string, MarketReferenceRow> {
  const codes = [...new Set(summaries
    .map((item) => item.stock_code)
    .filter((code): code is string => typeof code === "string" && !!code.trim())
    .map((code) => code.trim()))].sort();
  if (!codes.length) return new Map();

  const placeholders = codes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT business_date, stock_code, market, close_price, change_percent,
           volume, turnover, fetched_at
    FROM stock_market_daily
    WHERE business_date = ? AND source = ? AND stock_code IN (${placeholders})
    ORDER BY stock_code ASC
  `).all(businessDate, "toss_openapi", ...codes) as unknown as MarketReferenceRow[];
  return new Map(rows.map((item) => [item.stock_code, item]));
}

function formatCategoryDisplayName(value: string, type: CategoryType): string {
  return !value || value === "N/A" ? (type === "sector" ? "업종 미확인" : "테마 미확인") : value;
}

export function buildCategoryDetailSnapshot(
  database: DatabaseSync,
  businessDate: string,
  categoryType: string,
  categoryName: string,
  categoryDisplayName: string | null = null,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): CategoryDetailDTO {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid category detail date");
  if (!isCategoryType(categoryType) || categoryName.length > 120 || (categoryDisplayName?.length ?? 0) > 120) {
    throw new RangeError("Invalid category detail request");
  }
  if (!(categoryDisplayName || categoryName)) throw new RangeError("Invalid category detail request");

  const type = categoryType;
  const displayName = categoryDisplayName || categoryName;
  const snapshotDate = latestTypeSnapshotDate(database, type, businessDate);
  let summaries: SummaryRow[];

  if (categoryDisplayName) {
    if (snapshotDate === null) {
      summaries = type === "sector"
        ? legacySectorRows(database, businessDate, displayName)
        : legacyThemeRows(database, businessDate, displayName);
    } else {
      summaries = displayNameRows(database, businessDate, type, displayName);
    }
  } else {
    const catalog = database.prepare(`
      SELECT enabled FROM category_master WHERE category_type = ? AND category_key = ?
    `).get(type, categoryName);
    if (catalog?.enabled === 0) {
      summaries = [];
    } else {
      const row = database.prepare(`
        SELECT MAX(cms.snapshot_date) AS snapshot_date
        FROM category_membership_snapshots cms
        JOIN category_master cm
          ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
        WHERE cms.category_type = ? AND cms.category_key = ?
          AND cms.snapshot_date <= ? AND cm.enabled = 1
      `).get(type, categoryName, businessDate);
      const categorySnapshotDate = row?.snapshot_date;
      summaries = typeof categorySnapshotDate === "string"
        ? categoryKeyRows(database, businessDate, categorySnapshotDate, type, categoryName)
        : type === "sector"
          ? legacySectorRows(database, businessDate, categoryName)
          : legacyThemeRows(database, businessDate, categoryName);
    }
  }

  const references = selectedDateMarketReferences(database, businessDate, summaries);
  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    category_type: type,
    category_label: type === "sector" ? "업종" : "테마",
    category_name: categoryName,
    category_key: categoryName,
    display_name: displayName,
    public_category_id: `${type}|${displayName}|${snapshotDate ?? "fallback"}`,
    category_display_name: formatCategoryDisplayName(displayName, type),
    stock_count: summaries.length,
    report_count: summaries.reduce((total, item) => total + item.mention_count, 0),
    mapping_source: snapshotDate ? "dated_snapshot" : "latest_mapping_fallback",
    snapshot_date: snapshotDate,
    mapping_notice: snapshotDate
      ? "선택 날짜 이하의 가장 가까운 카테고리 스냅샷 기준입니다."
      : "선택 날짜 이전의 카테고리 스냅샷이 없어 최신 저장 분류 기준입니다.",
    stocks: summaries.map((item) => {
      const market = references.get(item.stock_code || "");
      return {
        business_date: item.business_date,
        stock_name: item.stock_name,
        stock_code: item.stock_code,
        mention_count: item.mention_count,
        broker_display: item.broker_display,
        target_price_min: item.target_price_min,
        target_price_max: item.target_price_max,
        dominant_opinion: item.dominant_opinion,
        market_reference: market ? {
          business_date: market.business_date,
          market: market.market,
          close_price: market.close_price,
          change_percent: market.change_percent,
          volume: market.volume,
          turnover: market.turnover,
          fetched_at: market.fetched_at,
        } : null,
      };
    }),
  };
}

export function getCategoryDetailSnapshot(
  businessDate: string,
  categoryType: string,
  categoryName: string,
  categoryDisplayName: string | null = null,
): CategoryDetailDTO {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildCategoryDetailSnapshot(
    database, businessDate, categoryType, categoryName, categoryDisplayName, new Date(), timezone,
  ));
}
