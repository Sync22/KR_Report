import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { EtfTrendSnapshot } from "../domain/market.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const SOURCE = "toss_openapi";
const MAX_ETF_TREND_LIMIT = 20;
const DEFAULT_ETF_TREND_LIMIT = 5;
const ETF_ROW_LIMIT = 5;

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

export function parseEtfTrendLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? DEFAULT_ETF_TREND_LIMIT : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, MAX_ETF_TREND_LIMIT)) : DEFAULT_ETF_TREND_LIMIT;
}

export function buildEtfTrendSnapshot(
  database: DatabaseSync,
  businessDate: string,
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): EtfTrendSnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid ETF trend date");
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_ETF_TREND_LIMIT) throw new RangeError("Invalid ETF trend limit");

  const snapshotDates = database.prepare(`
    SELECT business_date
    FROM etf_daily_snapshots
    WHERE business_date <= ? AND source = ?
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT ?
  `).all(businessDate, SOURCE, limit).map((row) => {
    if (typeof row.business_date !== "string" || !isBusinessDate(row.business_date)) {
      throw new Error("Invalid stored ETF date");
    }
    return row.business_date;
  });

  const listEtfs = database.prepare(`
    SELECT business_date, etf_code, etf_name, close_price, change_percent,
           nav, volume, turnover, underlying_index_name
    FROM etf_daily_snapshots
    WHERE business_date = ? AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
    LIMIT ?
  `);
  const items = snapshotDates.map((snapshotDate) => ({
    business_date: snapshotDate,
    top_etfs_by_turnover: (listEtfs.all(snapshotDate, SOURCE, ETF_ROW_LIMIT) as unknown as EtfRow[]).map((item) => ({
      business_date: item.business_date,
      etf_code: item.etf_code,
      etf_name: item.etf_name,
      close_price: item.close_price,
      change_percent: item.change_percent,
      nav: item.nav,
      volume: item.volume,
      turnover: item.turnover,
      underlying_index_name: item.underlying_index_name,
      evidence_label: etfEvidenceLabel(item),
      rotation_reference: "저장 ETF 거래대금/NAV/기초지수 기준",
    })),
  }));

  const referenceDate = snapshotDates[0] ?? null;
  const referenceStatus = referenceDate === businessDate ? "exact" : referenceDate ? "stale" : "missing";
  const available = items.length > 0;
  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    reference_date: referenceDate,
    reference_status: referenceStatus,
    exact_date_available: referenceStatus === "exact",
    available,
    source: available ? SOURCE : null,
    data_scope: "stored_toss_close_snapshot",
    basis: "Toss 거래대금 상위 ETF",
    display_label: available ? "ETF 저장 참고" : "ETF 저장값 없음",
    constituents_available: false,
    composition_scope: "구성종목 미포함",
    live_fetch: false,
    scoring: false,
    notice: available && referenceStatus === "exact"
      ? "선택 날짜 이하 최근 Toss 저장 스냅샷의 ETF 거래대금 흐름입니다. 구성종목은 포함하지 않습니다."
      : available && referenceDate
        ? `선택 날짜의 ETF 저장값이 없어 ${referenceDate} 기준 Toss ETF 흐름만 표시합니다.`
        : "선택 날짜 이전 또는 해당 날짜의 ETF 저장 스냅샷이 없습니다.",
    items,
  };
}

export function getEtfTrendSnapshot(businessDate: string, limit = DEFAULT_ETF_TREND_LIMIT): EtfTrendSnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildEtfTrendSnapshot(database, businessDate, limit, new Date(), timezone));
}
