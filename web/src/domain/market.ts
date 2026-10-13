import { isBusinessDate } from "./daily.ts";

type RecordValue = Record<string, unknown>;

export type MarketSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  snapshot_source: "toss_openapi";
  snapshot_date: string | null;
  capture_status: string | null;
  missing_domains: string[];
  latest_capture_attempt: { status: string; business_date: string | null; missing_domains: string[] } | null;
  top_kospi_stocks: RecordValue[];
  top_kosdaq_stocks: RecordValue[];
  top_etfs: RecordValue[];
  market_indices: RecordValue[];
};

export type FlowTrendSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  reference_date: string | null;
  exact_date_available: boolean;
  available: boolean;
  source: "toss_openapi" | null;
  data_scope: "stored_toss_close_market_flow";
  live_fetch: false;
  scoring: false;
  notice: string;
  items: { business_date: string; market_flows: RecordValue[] }[];
};

export type EtfTrendSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  reference_date: string | null;
  reference_status: "exact" | "stale" | "missing";
  exact_date_available: boolean;
  available: boolean;
  source: "toss_openapi" | null;
  data_scope: "stored_toss_close_snapshot";
  basis: string;
  display_label: string;
  constituents_available: false;
  composition_scope: string;
  live_fetch: false;
  scoring: false;
  notice: string;
  items: { business_date: string; top_etfs_by_turnover: RecordValue[] }[];
};

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isNullableDate(value: unknown): value is string | null {
  return value === null || isBusinessDate(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isSnapshotTime(value: RecordValue): boolean {
  return (
    typeof value.now === "string" && Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" && value.timezone.length > 0
  );
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isMarketRow(value: unknown, snapshotDate: string | null, closeKey: "close_price" | "close_index" = "close_price"): value is RecordValue {
  return (
    isRecord(value) && isBusinessDate(value.business_date) && value.business_date === snapshotDate &&
    isNullableNumber(value[closeKey]) && isNullableNumber(value.change_percent) && isNullableNumber(value.turnover)
  );
}

export function isMarketSnapshot(value: unknown): value is MarketSnapshot {
  if (!isRecord(value) || !isSnapshotTime(value)) return false;
  const snapshotDate = value.snapshot_date;
  const capture = value.latest_capture_attempt;
  return (
    value.surface === "web-view" && value.read_only === true && value.snapshot_source === "toss_openapi" &&
    isNullableDate(snapshotDate) && (value.capture_status === null || typeof value.capture_status === "string") &&
    isStringArray(value.missing_domains) &&
    (capture === null || (
      isRecord(capture) && typeof capture.status === "string" && isNullableDate(capture.business_date) &&
      isStringArray(capture.missing_domains)
    )) &&
    ["top_kospi_stocks", "top_kosdaq_stocks", "top_etfs"].every((key) =>
      Array.isArray(value[key]) && (value[key] as unknown[]).every((row) => isMarketRow(row, snapshotDate))
    ) && Array.isArray(value.market_indices) && value.market_indices.every((row: unknown) => isMarketRow(row, snapshotDate, "close_index"))
  );
}

function isFlowRow(value: unknown, itemDate: string): value is RecordValue {
  return isRecord(value) && value.business_date === itemDate && typeof value.market_label === "string" &&
    typeof value.investor_label === "string" && value.source === "toss_openapi";
}

export function isFlowTrendSnapshot(value: unknown, expectedDate: string): value is FlowTrendSnapshot {
  if (!isRecord(value) || !isSnapshotTime(value) || !Array.isArray(value.items)) return false;
  const referenceDate = value.reference_date;
  const itemsValid = value.items.every((item: unknown) =>
    isRecord(item) && isBusinessDate(item.business_date) && item.business_date <= expectedDate &&
    Array.isArray(item.market_flows) && item.market_flows.every((row: unknown) => isFlowRow(row, item.business_date as string))
  );
  return (
    value.surface === "web-view" && value.read_only === true && value.business_date === expectedDate &&
    isBusinessDate(expectedDate) && isNullableDate(referenceDate) &&
    (referenceDate === null || referenceDate <= expectedDate) &&
    value.exact_date_available === (referenceDate === expectedDate) &&
    value.available === (value.items.length > 0) &&
    value.source === (value.available ? "toss_openapi" : null) &&
    value.data_scope === "stored_toss_close_market_flow" && value.live_fetch === false && value.scoring === false &&
    typeof value.notice === "string" && itemsValid &&
    (value.items.length === 0 ? referenceDate === null : value.items[0].business_date === referenceDate)
  );
}

export function isEtfTrendSnapshot(value: unknown, expectedDate: string): value is EtfTrendSnapshot {
  if (!isRecord(value) || !isSnapshotTime(value) || !Array.isArray(value.items) || !isBusinessDate(expectedDate)) return false;
  const referenceDate = value.reference_date;
  const itemsValid = value.items.every((item: unknown) =>
    isRecord(item) && isBusinessDate(item.business_date) && item.business_date <= expectedDate &&
    Array.isArray(item.top_etfs_by_turnover) && item.top_etfs_by_turnover.every((row: unknown) =>
      isRecord(row) && row.business_date === item.business_date && typeof row.etf_code === "string" && typeof row.etf_name === "string" &&
      isNullableNumber(row.close_price) && isNullableNumber(row.change_percent) && isNullableNumber(row.turnover)
    )
  );
  const status = referenceDate === expectedDate ? "exact" : referenceDate === null ? "missing" : "stale";
  return (
    value.surface === "web-view" && value.read_only === true && value.business_date === expectedDate &&
    isNullableDate(referenceDate) && (referenceDate === null || referenceDate <= expectedDate) &&
    value.reference_status === status && value.exact_date_available === (status === "exact") &&
    value.available === (value.items.length > 0) && value.source === (value.available ? "toss_openapi" : null) &&
    value.data_scope === "stored_toss_close_snapshot" && typeof value.basis === "string" &&
    typeof value.display_label === "string" && value.constituents_available === false &&
    typeof value.composition_scope === "string" && value.live_fetch === false && value.scoring === false &&
    typeof value.notice === "string" && itemsValid &&
    (value.items.length === 0 ? referenceDate === null : value.items[0].business_date === referenceDate)
  );
}
