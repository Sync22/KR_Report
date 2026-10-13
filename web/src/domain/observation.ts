import { isBusinessDate } from "./daily.ts";

type RecordValue = Record<string, unknown>;

export type ObservationSummarySnapshot = RecordValue & {
  source: "stored_report_toss_observation_summary";
  read_only: true;
  live_fetch: false;
  scoring: false;
  recommendation: false;
  business_date: string;
  notice: string;
  market_mood: RecordValue & { label: string; display: string; lines: string[]; observation_line: string };
  report_concentration: DisplaySection;
  flow_reference: DisplaySection;
  price_volume_reference: DisplaySection;
  sector_breadth: RecordValue & { label: string; sectors: BreadthItem[]; themes: BreadthItem[] };
};

export type BacktestObservationSnapshot = RecordValue & {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  available: boolean;
  data_scope: "stored_report_krx_backtest_observation";
  live_fetch: false;
  scoring: false;
  recommendation: false;
  mention_threshold: number;
  horizons: number[];
  notice: string;
  rows: BacktestObservationRow[];
};

type DisplayItem = RecordValue & { display: string; stock_name: string; stock_code: string | null };
type DisplaySection = RecordValue & { label: string; available: boolean; items: DisplayItem[] };
type BreadthItem = RecordValue & { category_type: "sector" | "theme"; public_category_id: string; display_name: string; category_display_name: string; snapshot_date: string | null; display: string };
type BacktestReaction = RecordValue & { horizon_days: number; available: boolean; horizon_date: string | null; close_return_percent: number | null; unavailable_reason: string | null };
type BacktestTargetObservation = RecordValue & { progress_caution: boolean; progress_notice: string | null; validation_notice: string | null };
type BacktestObservationRow = RecordValue & {
  business_date: string;
  stock_code: string;
  stock_name: string;
  report_summary: RecordValue & { report_count: number; broker_count: number; broker_display: string; target_price_min: number | null; target_price_max: number | null; dominant_opinion: string | null };
  base_market: RecordValue | null;
  reaction_windows: BacktestReaction[];
  target_observation: BacktestTargetObservation;
  stock_flow_observation: RecordValue;
  net_buy_top_observation: RecordValue;
  evidence_notes: string[];
};

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isNumberOrNull(value: unknown): value is number | null {
  return value === null || isNumber(value);
}

function isCount(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 0;
}

function isNullableDate(value: unknown): value is string | null {
  return value === null || isBusinessDate(value);
}

function hasNoNewSignals(value: RecordValue): boolean {
  return !["score", "grade", "buy_signal", "sell_signal"].some((key) => key in value);
}

function isDisplaySection(value: unknown): value is DisplaySection {
  return isRecord(value) && typeof value.label === "string" && typeof value.available === "boolean" &&
    Array.isArray(value.items) && value.items.every((item: unknown) =>
      isRecord(item) && typeof item.display === "string" && typeof item.stock_name === "string" &&
      (item.stock_code === null || /^\d{6}$/.test(String(item.stock_code)))
    );
}

function isMarketMood(value: unknown): value is ObservationSummarySnapshot["market_mood"] {
  return isRecord(value) && typeof value.label === "string" && isCount(value.report_count) &&
    isCount(value.stock_count) && isCount(value.multi_report_stock_count) && typeof value.display === "string" &&
    Array.isArray(value.lines) && value.lines.every((line: unknown) => typeof line === "string") &&
    typeof value.observation_line === "string";
}

function isFlowReference(value: unknown, expectedDate: string): value is DisplaySection {
  return isDisplaySection(value) && value.items.every((item: unknown) =>
    isRecord(item) && (item.reference_date === null || (isBusinessDate(item.reference_date) && item.reference_date <= expectedDate)) &&
    typeof item.available === "boolean" && Array.isArray(item.windows)
  );
}

function isPriceVolumeReference(value: unknown, expectedDate: string): value is DisplaySection {
  return isDisplaySection(value) && value.items.every((item: unknown) =>
    isRecord(item) && (item.reference_date === null || (isBusinessDate(item.reference_date) && item.reference_date <= expectedDate)) &&
    isNumberOrNull(item.close_price) && isNumberOrNull(item.change_percent) && isNumberOrNull(item.turnover) &&
    isNumberOrNull(item.close_position_20d_percent) && isNumberOrNull(item.close_position_60d_percent) &&
    isNumberOrNull(item.close_position_52w_percent) && isNumberOrNull(item.return_5d_percent) &&
    isNumberOrNull(item.return_20d_percent) && isNumberOrNull(item.volume_multiple_20d)
  );
}

function isBreadthItem(value: unknown, expectedDate: string): value is BreadthItem {
  return isRecord(value) && (value.category_type === "sector" || value.category_type === "theme") &&
    typeof value.public_category_id === "string" && typeof value.display_name === "string" &&
    typeof value.category_display_name === "string" && isCount(value.stock_count) && isCount(value.report_count) &&
    isNumber(value.share_percent) && isNumber(value.bar_width_percent) && value.bar_width_percent >= 0 && value.bar_width_percent <= 100 &&
    isNullableDate(value.snapshot_date) && (value.snapshot_date === null || value.snapshot_date <= expectedDate) &&
    typeof value.mapping_source === "string" && typeof value.display === "string";
}

function isSectorBreadth(value: unknown, expectedDate: string): value is ObservationSummarySnapshot["sector_breadth"] {
  return isRecord(value) && typeof value.label === "string" && typeof value.available === "boolean" &&
    Array.isArray(value.sectors) && value.sectors.every((item: unknown) => isBreadthItem(item, expectedDate)) &&
    Array.isArray(value.themes) && value.themes.every((item: unknown) => isBreadthItem(item, expectedDate));
}

export function isObservationSummarySnapshot(value: unknown, expectedDate: string): value is ObservationSummarySnapshot {
  if (!isRecord(value)) return false;
  return (
    value.source === "stored_report_toss_observation_summary" && value.read_only === true &&
    value.live_fetch === false && value.scoring === false && value.recommendation === false &&
    value.business_date === expectedDate && isBusinessDate(expectedDate) && typeof value.notice === "string" &&
    isMarketMood(value.market_mood) && isDisplaySection(value.report_concentration) &&
    isFlowReference(value.flow_reference, expectedDate) && isPriceVolumeReference(value.price_volume_reference, expectedDate) &&
    isSectorBreadth(value.sector_breadth, expectedDate) && hasNoNewSignals(value)
  );
}

function isBacktestMarketReference(value: unknown, rowDate: string): boolean {
  return value === null || (
    isRecord(value) && isBusinessDate(value.business_date) && value.business_date <= rowDate &&
    (value.market === null || typeof value.market === "string") && isNumberOrNull(value.close_price) &&
    isNumberOrNull(value.change_percent) && isNumberOrNull(value.volume) && isNumberOrNull(value.turnover) &&
    typeof value.fetched_at === "string" && Number.isFinite(Date.parse(value.fetched_at))
  );
}

function isReactionWindow(value: unknown, horizon: number): value is BacktestReaction {
  return isRecord(value) && value.horizon_days === horizon && typeof value.available === "boolean" &&
    isNullableDate(value.horizon_date) && isNumberOrNull(value.base_close_price) &&
    isNumberOrNull(value.horizon_close_price) && isNumberOrNull(value.close_return_percent) &&
    isNumberOrNull(value.horizon_volume) && isNumberOrNull(value.horizon_turnover) &&
    (value.unavailable_reason === null || typeof value.unavailable_reason === "string");
}

function isTargetObservation(value: unknown): boolean {
  return isRecord(value) && ["available", "gap_available", "progress_available", "validation_available"].every((key) => typeof value[key] === "boolean") &&
    ["baseline_date", "current_date"].every((key) => isNullableDate(value[key])) &&
    ["baseline_price", "current_price", "target_price_min", "target_price_max", "target_gap_min_percent", "target_gap_max_percent", "progress_to_min_percent", "progress_to_max_percent", "max_progress_to_min_percent", "max_progress_to_max_percent"].every((key) => isNumberOrNull(value[key])) &&
    (value.validation_window_days === null || (typeof value.validation_window_days === "number" && Number.isInteger(value.validation_window_days))) &&
    (value.hit_min_horizon_days === null || (typeof value.hit_min_horizon_days === "number" && Number.isInteger(value.hit_min_horizon_days))) &&
    (value.hit_max_horizon_days === null || (typeof value.hit_max_horizon_days === "number" && Number.isInteger(value.hit_max_horizon_days))) &&
    typeof value.progress_caution === "boolean" &&
    (value.progress_notice === null || typeof value.progress_notice === "string") &&
    (value.validation_notice === null || typeof value.validation_notice === "string") &&
    (value.unavailable_reason === null || typeof value.unavailable_reason === "string");
}

function isStockFlowObservation(value: unknown): boolean {
  return isRecord(value) && typeof value.available === "boolean" &&
    ["individual_net_buy_volume", "foreign_net_buy_volume", "institution_net_buy_volume", "individual_net_buy_amount", "foreign_net_buy_amount", "institution_net_buy_amount"].every((key) => isNumberOrNull(value[key])) &&
    Array.isArray(value.investor_types) && value.investor_types.every((item: unknown) => typeof item === "string");
}

function isNetBuyObservation(value: unknown): boolean {
  return isRecord(value) && typeof value.available === "boolean" &&
    (value.foreign_top_rank === null || (typeof value.foreign_top_rank === "number" && Number.isInteger(value.foreign_top_rank))) &&
    (value.market === null || typeof value.market === "string") &&
    isNumberOrNull(value.net_buy_volume) && isNumberOrNull(value.net_buy_amount);
}

function isBacktestRow(value: unknown, expectedDate: string): value is BacktestObservationRow {
  if (!isRecord(value) || !Array.isArray(value.reaction_windows) || !isBusinessDate(value.business_date) || value.business_date !== expectedDate || typeof value.stock_code !== "string" || !value.stock_code.trim()) return false;
  const report = value.report_summary;
  const reactions = value.reaction_windows;
  return (
    hasNoNewSignals(value) && typeof value.stock_name === "string" && isRecord(report) &&
    isCount(report.report_count) && isCount(report.broker_count) && typeof report.broker_display === "string" &&
    isNumberOrNull(report.target_price_min) && isNumberOrNull(report.target_price_max) &&
    (report.dominant_opinion === null || typeof report.dominant_opinion === "string") &&
    isBacktestMarketReference(value.base_market, expectedDate) &&
    reactions.length === 4 && [1, 5, 10, 20].every((horizon, index) => isReactionWindow(reactions[index], horizon)) &&
    isTargetObservation(value.target_observation) && isStockFlowObservation(value.stock_flow_observation) &&
    isNetBuyObservation(value.net_buy_top_observation) && Array.isArray(value.evidence_notes) &&
    value.evidence_notes.every((item: unknown) => typeof item === "string")
  );
}

export function isBacktestObservationSnapshot(value: unknown, expectedDate: string): value is BacktestObservationSnapshot {
  if (!isRecord(value) || !Array.isArray(value.rows)) return false;
  return (
    typeof value.now === "string" && Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" && value.timezone.length > 0 &&
    value.surface === "web-view" && value.read_only === true && value.business_date === expectedDate &&
    isBusinessDate(expectedDate) && value.data_scope === "stored_report_krx_backtest_observation" &&
    value.live_fetch === false && value.scoring === false && value.recommendation === false &&
    Number.isInteger(value.mention_threshold) && (value.mention_threshold as number) >= 1 && (value.mention_threshold as number) <= 20 &&
    Array.isArray(value.horizons) && value.horizons.length === 4 && value.horizons.every((horizon: unknown, index: number) => horizon === [1, 5, 10, 20][index]) &&
    typeof value.available === "boolean" && value.available === (value.rows.length > 0) && value.rows.length <= 100 &&
    typeof value.notice === "string" && hasNoNewSignals(value) && value.rows.every((row: unknown) => isBacktestRow(row, expectedDate))
  );
}
