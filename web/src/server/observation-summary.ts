import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { ObservationSummarySnapshot } from "../domain/observation.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
};

type ReportIntensity = {
  report_count: number;
  active_dates: number;
  broker_count: number;
};

type TargetRevision = {
  previous_date: string;
  previous_min: number;
  previous_max: number;
  previous_report_count: number;
  previous_broker_count: number;
};

type FlowRow = {
  business_date: string;
  stock_code: string;
  investor_type: string;
  net_buy_amount: number | null;
};

type MarketRow = {
  business_date: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
};

type CategoryRollup = {
  category_type: "sector" | "theme";
  display_name: string;
  stock_count: number;
  report_count: number;
  snapshot_date: string | null;
  mapping_source: string;
  category_code?: string | null;
};

type CandidateRow = { stock_code: string | null; selected?: boolean };

const DEFAULT_HOLIDAYS = new Set([
  "2024-01-01", "2024-02-09", "2024-02-12", "2024-03-01", "2024-04-10", "2024-05-01",
  "2024-05-06", "2024-05-15", "2024-06-06", "2024-08-15", "2024-09-16", "2024-09-17",
  "2024-09-18", "2024-10-03", "2024-10-09", "2024-12-25", "2024-12-31",
  "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-03",
  "2025-05-01", "2025-05-05", "2025-05-06", "2025-06-03", "2025-06-06", "2025-08-15",
  "2025-10-03", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
  "2025-12-31", "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02",
  "2026-05-01", "2026-05-05", "2026-05-25", "2026-06-03", "2026-07-17", "2026-08-17",
  "2026-09-24", "2026-09-25", "2026-10-05", "2026-10-09", "2026-12-25", "2026-12-31",
]);

function placeholders(count: number): string {
  return Array.from({ length: count }, () => "?").join(", ");
}

function dateShift(value: string, days: number): string {
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(0);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function configuredHolidays(): Set<string> {
  const holidays = new Set(DEFAULT_HOLIDAYS);
  for (const raw of (process.env.STOCK_MONITOR_HOLIDAYS ?? "").split(",")) {
    const value = raw.trim();
    if (isBusinessDate(value)) holidays.add(value);
  }
  return holidays;
}

export function isTradingBusinessDay(value: string): boolean {
  if (!isBusinessDate(value)) return false;
  const day = new Date(`${value}T00:00:00.000Z`).getUTCDay();
  return day !== 0 && day !== 6 && !configuredHolidays().has(value);
}

function recentBusinessDates(reference: string, count: number, holidays: Set<string>): string[] {
  if (count <= 0) return [];
  const dates = [reference];
  let probe = reference;
  while (dates.length < count) {
    probe = dateShift(probe, -1);
    while (new Date(`${probe}T00:00:00.000Z`).getUTCDay() === 0 ||
      new Date(`${probe}T00:00:00.000Z`).getUTCDay() === 6 || holidays.has(probe)) {
      probe = dateShift(probe, -1);
    }
    dates.push(probe);
  }
  return dates;
}

function brokerCount(value: string | null): number {
  const brokers = (value ?? "").split(",").filter((item) => item.trim()).map((item) =>
    item.trim().replace(/\(\d+\)$/, "").trim(),
  ).filter(Boolean);
  return new Set(brokers).size;
}

function compareText(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function hasDisplay<T extends { display?: unknown }>(item: T): item is T & { display: string } {
  return typeof item.display === "string";
}

function readSummaries(database: DatabaseSync, businessDate: string): SummaryRow[] {
  return database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
           target_price_min, target_price_max
    FROM daily_stock_summaries
    WHERE business_date = ?
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as SummaryRow[];
}

function readReportContext(database: DatabaseSync, businessDate: string, rows: SummaryRow[], dates: string[]) {
  const codes = [...new Set(rows.map((row) => row.stock_code).filter((code): code is string => !!code))];
  const intensity = new Map<string, ReportIntensity>();
  const revisions = new Map<string, TargetRevision>();
  if (!codes.length) return { intensity, revisions };

  const reportRows = database.prepare(`
    SELECT stock_code, COUNT(*) AS report_count,
           COUNT(DISTINCT business_date) AS active_dates,
           COUNT(DISTINCT NULLIF(TRIM(broker_name), '')) AS broker_count
    FROM reports
    WHERE stock_code IN (${placeholders(codes.length)})
      AND business_date IN (${placeholders(dates.length)})
    GROUP BY stock_code
  `).all(...codes, ...dates) as unknown as (ReportIntensity & { stock_code: string })[];
  for (const row of reportRows) intensity.set(row.stock_code, row);

  const revisionRows = database.prepare(`
    WITH latest_previous AS (
      SELECT stock_code, MAX(business_date) AS business_date
      FROM reports
      WHERE stock_code IN (${placeholders(codes.length)})
        AND business_date < ? AND target_price_value IS NOT NULL
      GROUP BY stock_code
    )
    SELECT r.stock_code, r.business_date AS previous_date,
           MIN(r.target_price_value) AS previous_min, MAX(r.target_price_value) AS previous_max,
           COUNT(*) AS previous_report_count,
           COUNT(DISTINCT NULLIF(TRIM(r.broker_name), '')) AS previous_broker_count
    FROM reports r
    JOIN latest_previous p ON p.stock_code = r.stock_code AND p.business_date = r.business_date
    WHERE r.target_price_value IS NOT NULL
    GROUP BY r.stock_code, r.business_date
  `).all(...codes, businessDate) as unknown as (TargetRevision & { stock_code: string })[];
  for (const row of revisionRows) revisions.set(row.stock_code, row);
  return { intensity, revisions };
}

function reportIntensity(
  stockCode: string,
  oneDayCount: number,
  dates: string[],
  values: Map<string, ReportIntensity>,
) {
  const row = values.get(stockCode);
  return {
    available: (row?.report_count ?? 0) > 0,
    one_day_report_count: oneDayCount,
    five_business_day_report_count: row?.report_count ?? 0,
    five_business_day_active_dates: row?.active_dates ?? 0,
    window_business_dates: dates,
  };
}

function targetRevision(
  summary: SummaryRow,
  previous: TargetRevision | undefined,
): Record<string, unknown> {
  const low = summary.target_price_min ?? summary.target_price_max;
  const high = summary.target_price_max ?? summary.target_price_min;
  if (low === null || high === null) {
    return {
      available: false, reason: "missing_current_target", current_min: summary.target_price_min,
      current_max: summary.target_price_max, previous_date: null, previous_min: null, previous_max: null,
      direction: null, direction_label: null,
    };
  }
  if (!previous) {
    return {
      available: false, reason: "no_previous_target", current_min: summary.target_price_min,
      current_max: summary.target_price_max, previous_date: null, previous_min: null, previous_max: null,
      direction: null, direction_label: null,
    };
  }
  const currentMid = (low + high) / 2;
  const previousMid = (previous.previous_min + previous.previous_max) / 2;
  const direction = currentMid > previousMid ? "up" : currentMid < previousMid ? "down" : "flat";
  const directionLabel = direction === "up" ? "상향" : direction === "down" ? "하향" : "유지";
  return {
    available: true,
    current_min: summary.target_price_min,
    current_max: summary.target_price_max,
    previous_date: previous.previous_date,
    previous_min: previous.previous_min,
    previous_max: previous.previous_max,
    previous_report_count: previous.previous_report_count,
    direction,
    direction_label: directionLabel,
  };
}

function reportConcentrationItem(
  summary: SummaryRow,
  businessDates: string[],
  intensityRows: Map<string, ReportIntensity>,
  revisions: Map<string, TargetRevision>,
) {
  const intensity = reportIntensity(summary.stock_code ?? "", summary.mention_count, businessDates, intensityRows);
  const revision = targetRevision(summary, revisions.get(summary.stock_code ?? ""));
  const intensityText = intensity.available &&
    !(intensity.five_business_day_report_count <= intensity.one_day_report_count && intensity.five_business_day_active_dates <= 1)
    ? ` · 5영업일 ${intensity.five_business_day_report_count}건 · ${intensity.five_business_day_active_dates}일 언급`
    : "";
  const revisionText = revision.available && typeof revision.direction_label === "string"
    ? ` · 목표가 저번 언급 대비 ${revision.direction_label}`
    : "";
  const publicIntensity = { ...intensity };
  const publicRevision = { ...revision };
  delete publicRevision.previous_broker_count;
  return {
    stock_name: summary.stock_name,
    stock_code: summary.stock_code,
    mention_count: summary.mention_count,
    broker_count: brokerCount(summary.broker_display),
    broker_display: summary.broker_display,
    report_intensity: publicIntensity,
    target_price_revision: publicRevision,
    target_price_display: {
      min: summary.target_price_min,
      max: summary.target_price_max,
      available: summary.target_price_min !== null || summary.target_price_max !== null,
    },
    display: `${summary.stock_name} / 리포트 ${summary.mention_count}건${intensityText}${revisionText}`,
  };
}

function readFlowRows(database: DatabaseSync, businessDate: string, codes: string[]): Map<string, FlowRow[]> {
  const byCode = new Map<string, FlowRow[]>();
  if (!codes.length) return byCode;
  const rows = database.prepare(`
    SELECT business_date, stock_code, investor_type, net_buy_volume AS net_buy_amount
    FROM stock_investor_flow_daily
    WHERE business_date BETWEEN ? AND ?
      AND stock_code IN (${placeholders(codes.length)})
      AND source = 'toss_openapi'
    ORDER BY stock_code ASC, business_date DESC, investor_type ASC
  `).all(dateShift(businessDate, -60), businessDate, ...codes) as unknown as FlowRow[];
  for (const row of rows) {
    const values = byCode.get(row.stock_code) ?? [];
    values.push(row);
    byCode.set(row.stock_code, values);
  }
  return byCode;
}

function sumFlow(rows: FlowRow[], investorTypes: Set<string>): number | null {
  const values = rows.filter((row) => investorTypes.has(row.investor_type) && row.net_buy_amount !== null)
    .map((row) => Number(row.net_buy_amount));
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function flowPersistence(rows: FlowRow[], types: Set<string>): Record<string, unknown> {
  const byDate = new Map<string, number>();
  for (const row of rows) {
    if (!types.has(row.investor_type) || row.net_buy_amount === null) continue;
    byDate.set(row.business_date, (byDate.get(row.business_date) ?? 0) + Number(row.net_buy_amount));
  }
  const ordered = [...byDate.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  const nonzero = ordered.map(([date, amount]) => ({ date, amount, direction: Math.sign(amount) })).filter((item) => item.direction !== 0);
  if (!nonzero.length) return {
    available: false, direction: null, direction_label: "중립", streak_days: 0, turn_date: null,
    turn_available: false, latest_amount: null,
  };
  const latest = nonzero[0];
  const streak = [latest];
  for (const item of nonzero.slice(1)) {
    if (item.direction !== latest.direction) break;
    streak.push(item);
  }
  const oldest = streak.reduce((date, item) => item.date < date ? item.date : date, streak[0].date);
  const priorOpposite = nonzero.some((item) => item.date < oldest && item.direction !== latest.direction);
  return {
    available: true,
    direction: latest.direction,
    direction_label: latest.direction > 0 ? "순유입" : "순유출",
    streak_days: streak.length,
    turn_date: priorOpposite ? oldest : null,
    turn_available: priorOpposite,
    latest_amount: latest.amount,
  };
}

function flowVolume(value: number | null): string {
  if (value === null) return "-";
  if (value > 0) return `순매수 ${value.toLocaleString("en-US")}주`;
  if (value < 0) return `순매도 ${Math.abs(value).toLocaleString("en-US")}주`;
  return "중립";
}

function persistenceText(items: Array<[string, Record<string, unknown>]>): string {
  const parts: string[] = [];
  for (const [label, item] of items) {
    if (item.available !== true) continue;
    const streakDays = Number(item.streak_days ?? 0);
    if (streakDays < 2) continue;
    const directionLabel = String(item.direction_label ?? "중립");
    const turnDate = item.turn_date;
    parts.push(turnDate
      ? `${label} ${directionLabel} 전환 ${String(turnDate).slice(5).replaceAll("-", ".")}부터 ${streakDays}일`
      : `${label} ${directionLabel} 연속 ${streakDays}일`);
  }
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}

function flowItem(summary: SummaryRow, rows: FlowRow[]) {
  const flowDates = [...new Set(rows.map((row) => row.business_date))].sort((a, b) => b.localeCompare(a));
  if (!flowDates.length) {
    return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code, windows: [] };
  }
  const windows = [5, 10, 20, 31].map((days) => {
    const picked = new Set(flowDates.slice(0, days));
    const windowRows = rows.filter((row) => picked.has(row.business_date));
    return {
      days,
      observed_days: picked.size,
      individual_net_buy_amount: sumFlow(windowRows, new Set(["개인"])),
      foreign_net_buy_amount: sumFlow(windowRows, new Set(["외국인"])),
      institution_net_buy_amount: sumFlow(windowRows, new Set(["기관", "기관합계"])),
    };
  });
  const persistence = {
    foreign: flowPersistence(rows, new Set(["외국인"])),
    institution: flowPersistence(rows, new Set(["기관", "기관합계"])),
  };
  return {
    available: true,
    stock_name: summary.stock_name,
    stock_code: summary.stock_code,
    reference_date: flowDates[0],
    observed_days: flowDates.length,
    windows,
    persistence,
    display: `${summary.stock_name} 외국인 ${flowVolume(windows[0].foreign_net_buy_amount)} · 기관 ${flowVolume(windows[0].institution_net_buy_amount)}` +
      persistenceText([["외국인", persistence.foreign], ["기관", persistence.institution]]),
  };
}

function readMarketHistory(database: DatabaseSync, businessDate: string, stockCode: string): MarketRow[] {
  return database.prepare(`
    SELECT business_date, close_price, change_percent, volume, turnover
    FROM stock_market_daily
    WHERE business_date <= ? AND stock_code = ? AND source = 'toss_openapi'
    ORDER BY business_date DESC
    LIMIT 252
  `).all(businessDate, stockCode) as unknown as MarketRow[];
}

function round(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  const scaled = value * factor;
  const lower = Math.floor(scaled);
  const fraction = scaled - lower;
  const tieTolerance = Number.EPSILON * Math.max(1, Math.abs(scaled)) * 2;
  const rounded = Math.abs(fraction - 0.5) <= tieTolerance
    ? lower % 2 === 0 ? lower : lower + 1
    : Math.round(scaled);
  return rounded / factor;
}

function closePosition(rows: MarketRow[], current: number): number | null {
  const closes = rows.map((row) => row.close_price).filter((value): value is number => value !== null);
  if (closes.length < 2) return null;
  const low = Math.min(...closes);
  const high = Math.max(...closes);
  return high === low ? 50 : round(((current - low) / (high - low)) * 100, 1);
}

function returnPercent(rows: MarketRow[], current: number, offset: number): number | null {
  if (rows.length <= offset || rows[offset].close_price === null || rows[offset].close_price === 0) return null;
  return round(((current - rows[offset].close_price) / rows[offset].close_price) * 100, 2);
}

function volumeMultiple(rows: MarketRow[], current: number | null): number | null {
  const volumes = rows.map((row) => row.volume).filter((value): value is number => value !== null && value > 0);
  if (current === null || current <= 0 || !volumes.length) return null;
  const average = volumes.reduce((sum, value) => sum + value, 0) / volumes.length;
  return average <= 0 ? null : round(current / average, 2);
}

function formatAmount(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000_000) return `${round(absolute / 1_000_000_000_000, 1).toFixed(1)}조`;
  if (absolute >= 100_000_000) return `${round(absolute / 100_000_000, 0).toFixed(0)}억`;
  return `${absolute.toLocaleString("en-US")}원`;
}

function optionalPercent(value: number | null, decimals: number, signed: boolean): string {
  if (value === null) return "-";
  return `${signed && value > 0 ? "+" : ""}${round(value, decimals).toFixed(decimals)}%`;
}

function priceVolumeItem(summary: SummaryRow, rows: MarketRow[]) {
  if (!summary.stock_code) return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code };
  const current = rows[0];
  if (!current || current.close_price === null) {
    return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code };
  }
  const position20 = closePosition(rows.slice(0, 20), current.close_price);
  const position60 = closePosition(rows.slice(0, 60), current.close_price);
  const position52w = rows.length >= 120 ? closePosition(rows.slice(0, 252), current.close_price) : null;
  const return5d = returnPercent(rows, current.close_price, 4);
  const return20d = returnPercent(rows, current.close_price, 19);
  const multiple = volumeMultiple(rows.slice(0, 20), current.volume);
  const positionParts = [`${summary.stock_name} 20일 위치 ${optionalPercent(position20, 1, false)}`];
  if (position52w !== null) positionParts.push(`52주 위치 ${optionalPercent(position52w, 1, false)}`);
  positionParts.push(`5일 ${optionalPercent(return5d, 2, true)}`);
  positionParts.push(`거래량 ${multiple === null ? "-" : `${multiple.toFixed(2)}배`}`);
  return {
    available: true,
    stock_name: summary.stock_name,
    stock_code: summary.stock_code,
    reference_date: current.business_date,
    close_price: current.close_price,
    change_percent: current.change_percent,
    turnover: current.turnover,
    turnover_display: current.turnover === null ? "저장값 없음" : formatAmount(current.turnover),
    close_position_20d_percent: position20,
    close_position_60d_percent: position60,
    close_position_52w_percent: position52w,
    close_position_52w_observed_days: Math.min(rows.length, 252),
    return_5d_percent: return5d,
    return_20d_percent: return20d,
    volume_multiple_20d: multiple,
    display: positionParts.join(" · "),
  };
}

function readCategoryRollups(database: DatabaseSync, businessDate: string, type: "sector" | "theme"): CategoryRollup[] {
  const latest = database.prepare(`
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
  `).get(type, businessDate)?.snapshot_date;
  if (typeof latest === "string") {
    const rows = database.prepare(`
      WITH latest_snapshots AS (
        SELECT cms.display_name AS display_name, MAX(cms.snapshot_date) AS snapshot_date
        FROM category_membership_snapshots cms
        JOIN category_master cm
          ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
        WHERE cms.category_type = ? AND cms.snapshot_date <= ? AND cm.enabled = 1
        GROUP BY cms.display_name
      ), category_stock_rows AS (
        SELECT cms.display_name AS display_name, cms.snapshot_date AS snapshot_date,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
               MAX(dss.mention_count) AS mention_count
        FROM daily_stock_summaries dss
        JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
        JOIN latest_snapshots latest
          ON latest.display_name = cms.display_name AND latest.snapshot_date = cms.snapshot_date
        WHERE dss.business_date = ? AND cms.category_type = ?
        GROUP BY cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
      )
      SELECT display_name, snapshot_date, COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count
      FROM category_stock_rows
      GROUP BY display_name, snapshot_date
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(type, businessDate, businessDate, type) as unknown as Omit<CategoryRollup, "category_type" | "mapping_source">[];
    return rows.map((row) => ({ ...row, category_type: type, mapping_source: "dated_snapshot" }));
  }

  const disabledRows = database.prepare(`
    SELECT category_key, display_name FROM category_master WHERE category_type = ? AND enabled = 0
  `).all(type) as unknown as { category_key: string; display_name: string }[];
  const disabled = new Set(disabledRows.flatMap((row) => [row.category_key, row.display_name]));
  if (type === "sector") {
    const rows = database.prepare(`
      WITH summary_with_category AS (
        SELECT COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS display_name,
               NULLIF(TRIM(sm.sector_code), '') AS category_code,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
               dss.mention_count AS mention_count
        FROM daily_stock_summaries dss
        LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
        WHERE dss.business_date = ?
      )
      SELECT display_name, MIN(category_code) AS category_code,
             COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count
      FROM summary_with_category
      GROUP BY display_name
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(businessDate) as unknown as Omit<CategoryRollup, "category_type" | "snapshot_date" | "mapping_source">[];
    return rows.filter((row) => !disabled.has(row.display_name) && !disabled.has(row.category_code ?? ""))
      .map((row) => ({ ...row, category_type: type, snapshot_date: null, mapping_source: "latest_mapping_fallback" }));
  }

  const rows = database.prepare(`
    WITH theme_stock_rows AS (
      SELECT COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS display_name,
             stm.theme_code AS category_code,
             COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
             MAX(dss.mention_count) AS mention_count
      FROM daily_stock_summaries dss
      JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
      WHERE dss.business_date = ?
      GROUP BY COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code),
               COALESCE(dss.stock_code, dss.stock_name)
    )
    SELECT display_name, MIN(category_code) AS category_code,
           COUNT(DISTINCT stock_identity) AS stock_count,
           COALESCE(SUM(mention_count), 0) AS report_count
    FROM theme_stock_rows
    GROUP BY display_name
    ORDER BY report_count DESC, stock_count DESC, display_name ASC
  `).all(businessDate) as unknown as Omit<CategoryRollup, "category_type" | "snapshot_date" | "mapping_source">[];
  return rows.filter((row) => !disabled.has(row.display_name) && !disabled.has(row.category_code ?? ""))
    .map((row) => ({ ...row, category_type: type, snapshot_date: null, mapping_source: "latest_mapping_fallback" }));
}

function roundPercent(value: number): number {
  return round(value, 1);
}

function breadthItems(rows: CategoryRollup[], categoryLabel: string, totalReportCount: number) {
  const maxReportCount = Math.max(0, ...rows.map((item) => item.report_count));
  return rows.map((item) => {
    const categoryDisplayName = !item.display_name || item.display_name === "N/A"
      ? item.category_type === "sector" ? "업종 미확인" : "테마 미확인"
      : item.display_name;
    const displayParts = [categoryDisplayName, `리포트 ${item.report_count}건`];
    if (!(item.report_count === 1 && item.stock_count === 1)) displayParts.push(`${item.stock_count}종목`);
    return {
      category_label: categoryLabel,
      category_type: item.category_type,
      public_category_id: `${item.category_type}|${item.display_name}|${item.snapshot_date ?? "fallback"}`,
      display_name: item.display_name,
      category_display_name: categoryDisplayName,
      stock_count: item.stock_count,
      report_count: item.report_count,
      share_percent: totalReportCount > 0 ? roundPercent((item.report_count / totalReportCount) * 100) : 0,
      bar_width_percent: maxReportCount > 0 ? roundPercent((item.report_count / maxReportCount) * 100) : 0,
      snapshot_date: item.snapshot_date,
      mapping_source: item.mapping_source,
      display: displayParts.join(" · "),
    };
  });
}

export function buildObservationSummaryFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  now = new Date(),
): ObservationSummarySnapshot {
  const summaries = readSummaries(database, businessDate);
  const candidate = buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, 2, now);
  const priorityCodes = candidate.rows
    .filter((row: CandidateRow) => row.selected !== false)
    .map((row: CandidateRow) => String(row.stock_code ?? "").trim())
    .filter(Boolean);
  const eligible = summaries.filter((summary) => !!summary.stock_code);
  const ordered = [...eligible].sort((left, right) =>
    right.mention_count - left.mention_count ||
    brokerCount(right.broker_display) - brokerCount(left.broker_display) ||
    compareText(left.stock_name, right.stock_name),
  );
  const byCode = new Map(ordered.map((summary) => [String(summary.stock_code), summary]));
  const priorityItems = priorityCodes.map((code) => byCode.get(code)).filter((item): item is SummaryRow => !!item);
  const priorityCodeSet = new Set(priorityItems.map((item) => String(item.stock_code)));
  const focused = [...priorityItems, ...ordered.filter((item) => !priorityCodeSet.has(String(item.stock_code)))].slice(0, 6);

  const businessDates = recentBusinessDates(businessDate, 5, configuredHolidays());
  const { intensity, revisions } = readReportContext(database, businessDate, summaries, businessDates);
  const flowRows = readFlowRows(database, businessDate, [...new Set(focused.map((item) => item.stock_code).filter((code): code is string => !!code))]);
  const reportItems = focused.map((item) => reportConcentrationItem(item, businessDates, intensity, revisions));
  const flowItems = focused.map((item) => flowItem(item, flowRows.get(item.stock_code ?? "") ?? []))
    .filter((item) => item.available).filter(hasDisplay);
  const priceItems = focused.map((item) => priceVolumeItem(item, item.stock_code ? readMarketHistory(database, businessDate, item.stock_code) : []))
    .filter((item) => item.available).filter(hasDisplay);

  const multiReportCount = summaries.filter((item) => item.mention_count >= 2).length;
  const reportCount = summaries.reduce((sum, item) => sum + item.mention_count, 0);
  const sectorItems = breadthItems(readCategoryRollups(database, businessDate, "sector").slice(0, 4), "업종", reportCount);
  const themeItems = breadthItems(readCategoryRollups(database, businessDate, "theme").slice(0, 4), "테마", reportCount);
  const breadth = [...sectorItems, ...themeItems].slice(0, 3).map((item) => item.display);
  const summaryLine = `리포트 ${reportCount}건이 ${summaries.length}종목에 모였습니다.`;
  const breadthLine = breadth.length
    ? `리포트가 몰린 쪽은 ${breadth.join(", ")}입니다.`
    : "업종/테마 분류는 저장 데이터 기준으로 정리 중입니다.";
  const observationLine = `반복 언급 ${multiReportCount}종목, 수급 참고가 붙은 관찰 종목은 ${flowItems.length}개입니다.`;

  return {
    source: "stored_report_toss_observation_summary",
    read_only: true,
    live_fetch: false,
    scoring: false,
    recommendation: false,
    business_date: businessDate,
    notice: "국장 관찰 요약은 저장된 리포트와 Toss 저장 가격·거래량·수급 참고값을 압축해 보여줍니다.",
    market_mood: {
      label: "시장 분위기",
      report_count: reportCount,
      stock_count: summaries.length,
      multi_report_stock_count: multiReportCount,
      display: summaryLine,
      lines: [summaryLine, breadthLine, observationLine],
      observation_line: observationLine,
    },
    report_concentration: { label: "리포트 집중", available: !!reportItems.length, items: reportItems },
    flow_reference: { label: "수급 참고", available: !!flowItems.length, items: flowItems },
    price_volume_reference: { label: "과열 참고", available: !!priceItems.length, items: priceItems },
    sector_breadth: {
      label: "시장 분위기",
      available: !!(sectorItems.length || themeItems.length),
      sectors: sectorItems,
      themes: themeItems,
    },
  } satisfies ObservationSummarySnapshot;
}

export function getObservationSummarySnapshot(businessDate: string, now = new Date()): ObservationSummarySnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid observation summary date");
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      return buildObservationSummaryFromDatabase(database, businessDate, now);
    } finally {
      database.exec("ROLLBACK");
    }
  });
}
