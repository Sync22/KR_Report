import { isBusinessDate } from "./daily.ts";

type RecordValue = Record<string, unknown>;
type CategoryType = "sector" | "theme";

export type CategoryDetailSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  category_type: CategoryType;
  category_label: string;
  category_name: string;
  display_name: string;
  public_category_id: string;
  category_display_name: string;
  stock_count: number;
  report_count: number;
  mapping_source: "dated_snapshot" | "latest_mapping_fallback";
  snapshot_date: string | null;
  mapping_notice: string;
  stocks: RecordValue[];
};

export type CategoryTrendSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  category_type: CategoryType;
  category_label: string;
  category_name: string;
  display_name: string;
  public_category_id: string;
  category_display_name: string;
  mapping_policy: string;
  trend: RecordValue[];
};

export type RotationOverlaySnapshot = {
  surface: "web-view";
  read_only: true;
  business_date: string;
  image: { path?: string; width: number; height: number };
  notice: string;
  highlights: RotationHighlight[];
};

type RotationCandidate = RecordValue & {
  stock_name?: string;
  stock_code?: string | null;
  etf_name?: string;
  etf_code?: string | null;
  mention_count?: number;
  market?: string | null;
  close_price: number | null;
  change_percent: number | null;
  turnover: number | null;
  evidence_label: string;
};

type RotationHighlight = RecordValue & {
  category_type: CategoryType;
  category_label: string;
  display_name: string;
  public_category_id: string;
  rotation_label: string;
  coordinate_display_name: string;
  mapping_basis: string;
  label: string;
  x: number;
  y: number;
  radius: number;
  evidence_label: string;
  evidence_source: "report_category_rollup";
  candidate_stocks: RotationCandidate[];
  candidate_etfs: RotationCandidate[];
};

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isCategoryType(value: unknown): value is CategoryType {
  return value === "sector" || value === "theme";
}

function isValidTime(value: RecordValue): boolean {
  return typeof value.now === "string" && Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" && value.timezone.length > 0;
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function hasNoRecommendationFields(value: RecordValue): boolean {
  return !["score", "grade", "recommendation", "buy_signal", "sell_signal"].some((key) => key in value);
}

function isCategoryMarketReference(value: unknown, expectedDate: string): boolean {
  return value === null || (
    isRecord(value) && isBusinessDate(value.business_date) && value.business_date <= expectedDate &&
    isNullableNumber(value.close_price) && isNullableNumber(value.change_percent) &&
    isNullableNumber(value.volume) && isNullableNumber(value.turnover) &&
    typeof value.fetched_at === "string" && Number.isFinite(Date.parse(value.fetched_at))
  );
}

function isCategoryStock(value: unknown, expectedDate: string): value is RecordValue {
  return (
    isRecord(value) && hasNoRecommendationFields(value) && value.business_date === expectedDate &&
    typeof value.stock_name === "string" &&
    (value.stock_code === null || typeof value.stock_code === "string") &&
    Number.isInteger(value.mention_count) && (value.mention_count as number) >= 0 &&
    typeof value.broker_display === "string" && isNullableNumber(value.target_price_min) &&
    isNullableNumber(value.target_price_max) &&
    (value.dominant_opinion === null || typeof value.dominant_opinion === "string") &&
    isCategoryMarketReference(value.market_reference, expectedDate)
  );
}

export function isCategoryDetailSnapshot(
  value: unknown,
  expectedDate: string,
  expectedType: string,
  expectedName: string,
): value is CategoryDetailSnapshot {
  if (!isRecord(value) || !Array.isArray(value.stocks)) return false;
  return (
    isValidTime(value) && value.surface === "web-view" && value.read_only === true &&
    value.business_date === expectedDate && isBusinessDate(expectedDate) &&
    value.category_type === expectedType && isCategoryType(value.category_type) &&
    typeof value.category_label === "string" && typeof value.category_name === "string" &&
    value.display_name === expectedName && typeof value.public_category_id === "string" &&
    typeof value.category_display_name === "string" &&
    Number.isInteger(value.stock_count) && (value.stock_count as number) >= 0 &&
    Number.isInteger(value.report_count) && (value.report_count as number) >= 0 &&
    (value.mapping_source === "dated_snapshot" || value.mapping_source === "latest_mapping_fallback") &&
    (value.snapshot_date === null || (isBusinessDate(value.snapshot_date) && value.snapshot_date <= expectedDate)) &&
    (value.mapping_source === "dated_snapshot") === (value.snapshot_date !== null) &&
    typeof value.mapping_notice === "string" && value.live_fetch === undefined && hasNoRecommendationFields(value) &&
    value.stocks.every((row: unknown) => isCategoryStock(row, expectedDate))
  );
}

export function isCategoryTrendSnapshot(
  value: unknown,
  expectedType: string,
  expectedName: string,
): value is CategoryTrendSnapshot {
  if (!isRecord(value) || !Array.isArray(value.trend)) return false;
  return (
    isValidTime(value) && value.surface === "web-view" && value.read_only === true &&
    value.category_type === expectedType && isCategoryType(value.category_type) &&
    typeof value.category_label === "string" && typeof value.category_name === "string" &&
    value.display_name === expectedName && typeof value.public_category_id === "string" &&
    typeof value.category_display_name === "string" && typeof value.mapping_policy === "string" &&
    value.live_fetch === undefined && hasNoRecommendationFields(value) && value.trend.every((row: unknown) =>
      isRecord(row) && hasNoRecommendationFields(row) && isBusinessDate(row.business_date) &&
      Number.isInteger(row.stock_count) && (row.stock_count as number) >= 0 &&
      Number.isInteger(row.report_count) && (row.report_count as number) >= 0
    )
  );
}

function isRotationCandidate(value: unknown, kind: "stock" | "etf"): value is RotationCandidate {
  if (!isRecord(value) || typeof value.evidence_label !== "string") return false;
  const nameKey = kind === "stock" ? "stock_name" : "etf_name";
  const codeKey = kind === "stock" ? "stock_code" : "etf_code";
  return typeof value[nameKey] === "string" && (value[codeKey] === null || typeof value[codeKey] === "string") &&
    isNullableNumber(value.close_price) && isNullableNumber(value.change_percent) &&
    isNullableNumber(value.turnover) && hasNoRecommendationFields(value);
}

function isRotationHighlight(value: unknown, width: number, height: number): value is RotationHighlight {
  return (
    isRecord(value) && hasNoRecommendationFields(value) && isCategoryType(value.category_type) &&
    typeof value.category_label === "string" && typeof value.display_name === "string" &&
    typeof value.public_category_id === "string" && typeof value.rotation_label === "string" &&
    typeof value.coordinate_display_name === "string" && typeof value.mapping_basis === "string" &&
    typeof value.label === "string" && typeof value.evidence_label === "string" &&
    value.evidence_source === "report_category_rollup" &&
    typeof value.x === "number" && Number.isFinite(value.x) && value.x >= 0 && value.x <= width &&
    typeof value.y === "number" && Number.isFinite(value.y) && value.y >= 0 && value.y <= height &&
    typeof value.radius === "number" && Number.isFinite(value.radius) && value.radius > 0 &&
    Array.isArray(value.candidate_stocks) && value.candidate_stocks.every((item: unknown) => isRotationCandidate(item, "stock")) &&
    Array.isArray(value.candidate_etfs) && value.candidate_etfs.every((item: unknown) => isRotationCandidate(item, "etf"))
  );
}

export function isRotationOverlaySnapshot(value: unknown, expectedDate: string): value is RotationOverlaySnapshot {
  if (!isRecord(value) || !isRecord(value.image) || !Array.isArray(value.highlights)) return false;
  const { width, height } = value.image;
  return (
    value.surface === "web-view" && value.read_only === true && value.business_date === expectedDate &&
    isBusinessDate(expectedDate) && (value.image.path === undefined || typeof value.image.path === "string") &&
    Number.isInteger(width) && (width as number) > 0 && Number.isInteger(height) && (height as number) > 0 &&
    typeof value.notice === "string" && hasNoRecommendationFields(value) &&
    value.highlights.every((item: unknown) => isRotationHighlight(item, width as number, height as number))
  );
}
