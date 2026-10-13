import "server-only";

import { DatabaseSync } from "node:sqlite";
import { resolve } from "node:path";

import { isBusinessDate } from "../domain/daily.ts";
import type { ArchiveSnapshot } from "../domain/archive.ts";

type DateCount = { business_date: string; count: number };
type CategorySnapshot = { category_type: "sector" | "theme"; snapshot_date: string };

const MAX_ARCHIVE_LIMIT = 100;
const DEFAULT_ARCHIVE_LIMIT = 20;

export function parseArchiveLimit(value: string | null): number {
  if (value === null || !/^[+-]?\d+$/.test(value.trim())) return DEFAULT_ARCHIVE_LIMIT;
  const digits = value.trim().replace(/^[+-]/, "").replace(/^0+(?=\d)/, "");
  if (value.trim().startsWith("-")) return 1;
  if (digits.length > String(MAX_ARCHIVE_LIMIT).length) return MAX_ARCHIVE_LIMIT;
  return Math.min(MAX_ARCHIVE_LIMIT, Math.max(1, Number(digits)));
}

function countByBusinessDate(database: DatabaseSync, table: "reports" | "daily_stock_summaries", limit: number): Map<string, number> {
  const rows = database.prepare(`
    SELECT business_date, COUNT(*) AS count
    FROM ${table}
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT ?
  `).all(limit);
  const counts = new Map<string, number>();
  for (const row of rows) {
    if (typeof row.business_date !== "string" || !isBusinessDate(row.business_date) ||
      typeof row.count !== "number" || !Number.isSafeInteger(row.count) || row.count < 0) {
      throw new Error("Invalid stored archive count row");
    }
    counts.set(row.business_date, row.count);
  }
  return counts;
}

function archiveCategoryMappings(database: DatabaseSync, businessDates: string[]) {
  const snapshots: Record<CategorySnapshot["category_type"], string[]> = { sector: [], theme: [] };
  if (!businessDates.length) return new Map<string, ArchiveSnapshot["dates"][number]["category_mapping"]>();

  const rows = database.prepare(`
    SELECT cms.category_type, cms.snapshot_date
    FROM category_membership_snapshots cms
    JOIN category_master cm
      ON cm.category_type = cms.category_type
     AND cm.category_key = cms.category_key
    WHERE cms.category_type IN ('sector', 'theme')
      AND cms.snapshot_date <= ?
      AND cm.enabled = 1
    GROUP BY cms.category_type, cms.snapshot_date
    ORDER BY cms.category_type ASC, cms.snapshot_date ASC
  `).all(businessDates[0]);

  for (const row of rows) {
    if ((row.category_type !== "sector" && row.category_type !== "theme") ||
      typeof row.snapshot_date !== "string" || !isBusinessDate(row.snapshot_date)) {
      throw new Error("Invalid stored archive category row");
    }
    snapshots[row.category_type].push(row.snapshot_date);
  }

  const latestSnapshot = (category: CategorySnapshot["category_type"], businessDate: string) => {
    let latest: string | null = null;
    for (const snapshotDate of snapshots[category]) {
      if (snapshotDate > businessDate) break;
      latest = snapshotDate;
    }
    return latest;
  };

  return new Map(businessDates.map((businessDate) => {
    const sectorDate = latestSnapshot("sector", businessDate);
    const themeDate = latestSnapshot("theme", businessDate);
    const dated = Boolean(sectorDate && themeDate);
    return [businessDate, {
      mapping_basis: dated ? "dated_snapshot" : "latest_mapping_fallback",
      sector_snapshot_date: sectorDate,
      theme_snapshot_date: themeDate,
      label: dated ? "카테고리 스냅샷" : "최신 저장 분류",
    }] as const;
  }));
}

export function buildArchiveSnapshot(
  database: DatabaseSync,
  limit: number,
  now: Date,
  timezone: string,
): ArchiveSnapshot {
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_ARCHIVE_LIMIT) {
    throw new RangeError("Archive limit is outside the allowed range");
  }

  const reportsByDate = countByBusinessDate(database, "reports", limit);
  const summariesByDate = countByBusinessDate(database, "daily_stock_summaries", limit);
  const businessDates = [...new Set([...reportsByDate.keys(), ...summariesByDate.keys()])]
    .sort((left, right) => right.localeCompare(left))
    .slice(0, limit);
  const categoryMappings = archiveCategoryMappings(database, businessDates);
  const newsCounts = new Map<string, number>();

  if (businessDates.length) {
    const placeholders = businessDates.map(() => "?").join(", ");
    const rows = database.prepare(`
      SELECT target_date, COUNT(DISTINCT run_id) AS run_count
      FROM report_linked_news_evidence
      WHERE target_date IN (${placeholders})
      GROUP BY target_date
    `).all(...businessDates);
    for (const row of rows) {
      if (typeof row.target_date !== "string" || !businessDates.includes(row.target_date) ||
        typeof row.run_count !== "number" || !Number.isSafeInteger(row.run_count) || row.run_count < 0) {
        throw new Error("Invalid stored archive news count row");
      }
      newsCounts.set(row.target_date, row.run_count);
    }
  }

  const dates = businessDates.map((businessDate) => ({
    business_date: businessDate,
    report_count: reportsByDate.get(businessDate) ?? 0,
    summary_stock_count: summariesByDate.get(businessDate) ?? 0,
    news_observation_count: newsCounts.get(businessDate) ?? 0,
    category_mapping: categoryMappings.get(businessDate)!,
  }));
  const datedSnapshotCount = dates.filter((item) => item.category_mapping.mapping_basis === "dated_snapshot").length;
  const fallbackCount = dates.length - datedSnapshotCount;

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    date_count: dates.length,
    latest_business_date: businessDates[0] ?? null,
    filter_hint: "날짜 또는 건수 기준으로 화면에서 빠르게 좁혀볼 수 있습니다.",
    category_mapping_summary: {
      dated_snapshot_count: datedSnapshotCount,
      fallback_count: fallbackCount,
      notice: fallbackCount
        ? "일부 날짜는 과거 source-date 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다."
        : "모든 날짜가 dated category snapshot 기준입니다.",
    },
    dates,
  };
}

export function getArchiveSnapshot(limit: number): ArchiveSnapshot {
  const projectRoot = resolve(process.cwd(), "..");
  const databasePath = resolve(projectRoot, process.env.STOCK_MONITOR_DB_PATH?.trim() || "data/stock_monitor.db");
  const database = new DatabaseSync(databasePath, { readOnly: true, timeout: 5000 });
  try {
    database.exec("PRAGMA query_only = ON");
    return buildArchiveSnapshot(database, limit, new Date(), process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul");
  } finally {
    database.close();
  }
}
