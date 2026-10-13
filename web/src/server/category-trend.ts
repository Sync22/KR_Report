import "server-only";

import type { DatabaseSync } from "node:sqlite";

import type { CategoryTrendSnapshot } from "../domain/category-rotation.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 60;
const MAPPING_POLICY = "date-aware snapshot when available, latest stored category mapping otherwise";

type CategoryType = "sector" | "theme";
type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string;
  generated_at: string;
};

function isCategoryType(value: string): value is CategoryType {
  return value === "sector" || value === "theme";
}

export function parseCategoryTrendLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? DEFAULT_LIMIT : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, MAX_LIMIT)) : DEFAULT_LIMIT;
}

function snapshotRows(database: DatabaseSync, businessDate: string, snapshotDate: string, type: CategoryType, condition: "category_key" | "display_name", value: string): SummaryRow[] {
  const statement = condition === "category_key" ? database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max,
                    dss.dominant_opinion, dss.generated_at
    FROM daily_stock_summaries dss
    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
    WHERE dss.business_date = ? AND cms.snapshot_date = ? AND cms.category_type = ?
      AND cms.category_key = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `) : database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max,
                    dss.dominant_opinion, dss.generated_at
    FROM daily_stock_summaries dss
    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
    WHERE dss.business_date = ? AND cms.snapshot_date = ? AND cms.category_type = ?
      AND cms.display_name = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `);
  return statement.all(businessDate, snapshotDate, type, value) as unknown as SummaryRow[];
}

function legacySectorRows(database: DatabaseSync, businessDate: string, displayName: string): SummaryRow[] {
  return database.prepare(`
    SELECT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
           dss.broker_display, dss.target_price_min, dss.target_price_max,
           dss.dominant_opinion, dss.generated_at
    FROM daily_stock_summaries dss
    LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
    WHERE dss.business_date = ?
      AND COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, displayName) as unknown as SummaryRow[];
}

function legacyThemeRows(database: DatabaseSync, businessDate: string, displayName: string): SummaryRow[] {
  return database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count,
                    dss.broker_display, dss.target_price_min, dss.target_price_max,
                    dss.dominant_opinion, dss.generated_at
    FROM daily_stock_summaries dss
    JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
    WHERE dss.business_date = ?
      AND COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, displayName) as unknown as SummaryRow[];
}

function buildSnapshot(
  database: DatabaseSync,
  categoryType: string,
  categoryName: string,
  displayName: string,
  lookupMode: "category_key" | "display_name",
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): CategoryTrendSnapshot {
  const lookupName = lookupMode === "category_key" ? categoryName : displayName;
  if (!isCategoryType(categoryType) || !lookupName.trim() || lookupName.length > 120 || categoryName.length > 120 || displayName.length > 120) {
    throw new RangeError("Invalid category trend request");
  }
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
    throw new RangeError("Invalid category trend limit");
  }

  const type = categoryType;
  const candidates = database.prepare(`
    SELECT business_date
    FROM daily_stock_summaries
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT ?
  `).all(Math.max(limit * 4, limit));

  const hasSnapshot = database.prepare(`
    SELECT 1 AS found
    FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
    LIMIT 1
  `);
  const latestNamedSnapshot = database.prepare(`
    SELECT MAX(cms.snapshot_date) AS snapshot_date
    FROM category_membership_snapshots cms
    JOIN category_master cm
      ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
    WHERE cms.category_type = ? AND cms.display_name = ?
      AND cms.snapshot_date <= ? AND cm.enabled = 1
  `);
  const categoryEnabled = database.prepare(`
    SELECT enabled
    FROM category_master
    WHERE category_type = ? AND category_key = ?
  `);
  const latestKeySnapshot = database.prepare(`
    SELECT MAX(cms.snapshot_date) AS snapshot_date
    FROM category_membership_snapshots cms
    JOIN category_master cm
      ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
    WHERE cms.category_type = ? AND cms.category_key = ?
      AND cms.snapshot_date <= ? AND cm.enabled = 1
  `);

  const trend: CategoryTrendSnapshot["trend"] = [];
  for (const candidate of candidates) {
    const businessDate = candidate.business_date;
    if (typeof businessDate !== "string") throw new Error("Invalid stored category trend date");

    let rows: SummaryRow[];
    if (lookupMode === "category_key") {
      const catalog = categoryEnabled.get(type, categoryName);
      if (catalog?.enabled === 0) continue;
      const latest = latestKeySnapshot.get(type, categoryName, businessDate);
      const snapshotDate = latest?.snapshot_date;
      if (typeof snapshotDate === "string") {
        rows = snapshotRows(database, businessDate, snapshotDate, type, "category_key", categoryName);
      } else {
        rows = type === "sector"
          ? legacySectorRows(database, businessDate, categoryName)
          : legacyThemeRows(database, businessDate, categoryName);
      }
    } else if (hasSnapshot.get(type, businessDate)) {
      const latest = latestNamedSnapshot.get(type, displayName, businessDate);
      const snapshotDate = latest?.snapshot_date;
      if (typeof snapshotDate !== "string") continue;
      rows = snapshotRows(database, businessDate, snapshotDate, type, "display_name", displayName);
    } else {
      rows = type === "sector"
        ? legacySectorRows(database, businessDate, displayName)
        : legacyThemeRows(database, businessDate, displayName);
    }

    if (!rows.length) continue;
    const stockIdentities = new Set(rows.map((row) => row.stock_code || row.stock_name));
    trend.push({
      business_date: businessDate,
      stock_count: stockIdentities.size,
      report_count: rows.reduce((total, row) => total + row.mention_count, 0),
    });
    if (trend.length >= limit) break;
  }

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    category_type: type,
    category_label: type === "sector" ? "업종" : "테마",
    category_name: categoryName,
    display_name: displayName,
    public_category_id: `${type}|${displayName}|trend`,
    category_display_name: !displayName || displayName === "N/A"
      ? (type === "sector" ? "업종 미확인" : "테마 미확인")
      : displayName,
    mapping_policy: MAPPING_POLICY,
    trend,
  };
}

export function buildCategoryTrendSnapshot(
  database: DatabaseSync,
  categoryType: string,
  displayName: string,
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
  categoryName = "",
): CategoryTrendSnapshot {
  return buildSnapshot(database, categoryType, categoryName, displayName, "display_name", limit, now, timezone);
}

export function buildCategoryKeyTrendSnapshot(
  database: DatabaseSync,
  categoryType: string,
  categoryName: string,
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): CategoryTrendSnapshot {
  return buildSnapshot(database, categoryType, categoryName, categoryName, "category_key", limit, now, timezone);
}

export function getCategoryTrendSnapshot(categoryType: string, displayName: string, limit = DEFAULT_LIMIT, categoryName = ""): CategoryTrendSnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildCategoryTrendSnapshot(database, categoryType, displayName, limit, new Date(), timezone, categoryName));
}

export function getCategoryKeyTrendSnapshot(categoryType: string, categoryName: string, limit = DEFAULT_LIMIT): CategoryTrendSnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildCategoryKeyTrendSnapshot(database, categoryType, categoryName, limit, new Date(), timezone));
}
