import { isBusinessDate } from "./daily.ts";

type RecordValue = Record<string, unknown>;

export type PriceThresholdState = "reached" | "missed" | "insufficient_data";

export function priceThresholdState(close: unknown, threshold: unknown, direction: "above" | "below"): PriceThresholdState {
  if (!finite(close) || !finite(threshold)) return "insufficient_data";
  return direction === "above" ? (close > threshold ? "reached" : "missed") : (close < threshold ? "reached" : "missed");
}

export type IndicatorSnapshot = RecordValue & {
  schemaVersion: 1;
  code: string;
  symbol: string;
  market: string;
  timeframe: "D";
  requestedAsOf: string;
  barAsOf: string | null;
  source: string | null;
  sourceFetchedAt: string | null;
  sourceDate: string | null;
  barStatus: "confirmed" | "provisional" | "unknown";
  confirmedPolicy: string;
  price: RecordValue;
  indicators: RecordValue;
  structures: RecordValue[];
  structureStatus: RecordValue;
};

export type IndicatorChartBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20: number | null;
  sma60: number | null;
  sma120: number | null;
  sma200: number | null;
  rsi14: number | null;
  macd: number | null;
  macdSignal: number | null;
  macdHistogram: number | null;
  obv: number | null;
  atr14: number | null;
};

export function indicatorPriceChartBars(value: unknown, limit: number): IndicatorChartBar[] {
  if (!Array.isArray(value) || !Number.isInteger(limit) || limit < 1) return [];
  const valid: IndicatorChartBar[] = [];
  let previous = "";
  for (const raw of value) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) continue;
    const bar = raw as RecordValue;
    const time = bar.time;
    const open = finite(bar.open) ? bar.open : null;
    const high = finite(bar.high) ? bar.high : null;
    const low = finite(bar.low) ? bar.low : null;
    const close = finite(bar.close) ? bar.close : null;
    const volume = finite(bar.volume) ? bar.volume : null;
    if (!isBusinessDate(time) || time <= previous || open === null || high === null || low === null || close === null || volume === null ||
      low <= 0 || volume < 0 || low > Math.min(open, close) || high < Math.max(open, close)) continue;
    const optional = (key: string) => finite(bar[key]) ? bar[key] as number : null;
    valid.push({
      time, open, high, low, close, volume,
      sma20: optional("sma20"), sma60: optional("sma60"), sma120: optional("sma120"), sma200: optional("sma200"),
      rsi14: optional("rsi14"), macd: optional("macd"), macdSignal: optional("macdSignal"), macdHistogram: optional("macdHistogram"),
      obv: optional("obv"), atr14: optional("atr14"),
    });
    previous = time;
  }
  return valid.slice(-Math.min(limit, 380));
}

export function indicatorHistoryStatusLabel(value: unknown): string {
  return ({
    complete: "이력 종료",
    cursor_not_provided: "추가 이력 cursor 미제공",
    page_limit_reached: "800봉 요청 상한",
  } as Record<string, string>)[String(value)] ?? "이력 상태 미확인";
}

export type MainTop2IndicatorItem = RecordValue & {
  stock_code: string;
  stock_name: string;
  market: string | null;
  market_source: string | null;
  market_source_date: string | null;
  available: boolean;
  requested_as_of: string;
  candle_count?: number;
  pages_fetched?: number;
  history_status?: "complete" | "cursor_not_provided" | "page_limit_reached";
  snapshot?: IndicatorSnapshot;
  chart?: { bars: RecordValue[] };
  price_conditions?: RecordValue;
  indicator_confirmation?: RecordValue;
  condition_status?: string;
  condition_explanation?: string;
};

export type MainTop2IndicatorsSnapshot = RecordValue & {
  surface: "web-view-priority-indicators";
  read_only: true;
  configured: boolean;
  live_fetch: boolean;
  source: "toss-openapi-adjusted-daily";
  adjusted: true;
  page_size: 200;
  max_pages: 4;
  writes_stock_monitor_db: false;
  sends_telegram: false;
  registers_scheduler: false;
  affects_ordering: false;
  business_date: string;
  derived_from: "web_view_candidate_evidence_top_2";
  items: MainTop2IndicatorItem[];
};

const SNAPSHOT_FIELDS = [
  "schemaVersion", "code", "symbol", "market", "timeframe", "requestedAsOf", "barAsOf", "source", "sourceFetchedAt", "sourceDate",
  "barStatus", "confirmedPolicy", "cacheHit", "cacheAge", "stale", "lastSuccessAt", "dataRevision", "calculationVersion",
  "sourceCalculationVersion", "calculationBasis", "price", "indicators", "structures", "structureStatus", "servedAt",
];
const INDICATOR_FIELDS: Record<string, string[]> = {
  movingAverages: ["sma20", "sma60", "sma120", "sma200", "ema20", "ema60", "ema120", "ema200", "wma20", "wma60", "wma120", "wma200", "status", "calculationVersion", "emaSeedPolicy", "wmaWeights"],
  bollinger20: ["middle", "upper", "lower", "status", "period", "multiplier", "stddev", "calculationVersion"],
  donchian20: ["upper", "middle", "lower", "status", "period", "includeCurrent", "calculationVersion"],
  rsi14: ["value", "status", "provisional", "method", "seedPolicy"],
  atr14: ["value", "status", "provisional", "method", "seedPolicy"],
  volume: ["barVolume", "ratio20", "status", "period", "includeCurrent"],
  macd129: ["macd", "signal", "histogram", "status", "fast", "slow", "signalPeriod", "seedPolicy", "calculationVersion"],
  obv: ["value", "delta5", "seedTime", "status", "delta5Status", "seedPolicy", "calculationVersion"],
  volumeProfile12: ["version", "method", "from", "to", "count", "total", "binCount", "bins", "status"],
};
const INDICATOR_STATUS = ["ready", "partial-data", "insufficient-data"];
const STRUCTURE_STATUS = ["disabled", "paused", "unsupported", "error", "no-geometry", "insufficient-data", "ready"];
const STRUCTURE_FAMILIES = ["horizontal", "flag", "triangle"];
const STRUCTURE_ITEM_STATUS = ["forming", "confirmed", "breakout-pending", "paused", "failed", "expired", "retested"];
const STRUCTURE_UNITS = ["price", "price-per-bar", "projected-price", "projected-bars", "volume", "ratio", "bars", "count", "number", "date", "state"];
const CONDITION_STATES = ["판정 불가", "두 가격 조건 미충족", "진입 조건 충족", "청산 조건 충족", "가격 기준 도달 · 보조지표 확인 필요"];
const ALIGNMENT_STATES = ["up_aligned", "down_aligned", "mixed", "insufficient_data"];
const DIRECTION_STATES = ["up", "down", "mixed", "neutral", "insufficient_data"];

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function keysAllowed(value: unknown, allowed: readonly string[], required: readonly string[] = allowed): value is RecordValue {
  return isRecord(value) && Object.keys(value).every((key) => allowed.includes(key)) && required.every((key) => key in value);
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function nullableNumber(value: unknown): value is number | null {
  return value === null || finite(value);
}

function nullableBoolean(value: unknown): value is boolean | null {
  return value === null || typeof value === "boolean";
}

function nullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isDateOrNull(value: unknown, throughDate: string): value is string | null {
  return value === null || (isBusinessDate(value) && value <= throughDate);
}

function isDateTimeOrNull(value: unknown): boolean {
  return value === null || (typeof value === "string" && Number.isFinite(Date.parse(value)));
}

function finiteFields(value: RecordValue, fields: readonly string[]): boolean {
  return fields.every((key) => nullableNumber(value[key]));
}

function requiredTypes(value: RecordValue, fields: readonly string[], type: "string" | "boolean" | "integer"): boolean {
  return fields.every((key) => type === "string" ? typeof value[key] === "string" : type === "boolean" ? typeof value[key] === "boolean" : Number.isInteger(value[key]));
}

function isIndicatorSnapshot(value: unknown, date: string, code: string): value is IndicatorSnapshot {
  const requiredSnapshotFields = SNAPSHOT_FIELDS.filter((field) => field !== "servedAt");
  if (!keysAllowed(value, SNAPSHOT_FIELDS, requiredSnapshotFields)) return false;
  const indicatorsValue = value.indicators;
  const structureStatusValue = value.structureStatus;
  if (
    value.schemaVersion !== 1 || value.code !== code || typeof value.symbol !== "string" ||
    !(value.market === "KOSPI" || value.market === "KOSDAQ" || value.market === "unknown") ||
    value.timeframe !== "D" || value.requestedAsOf !== date || !isBusinessDate(value.requestedAsOf) ||
    !isDateOrNull(value.barAsOf, date) || !nullableString(value.source) || !isDateTimeOrNull(value.sourceFetchedAt) ||
    !isDateOrNull(value.sourceDate, date) || !["confirmed", "provisional", "unknown"].includes(String(value.barStatus)) ||
    typeof value.confirmedPolicy !== "string" || !nullableBoolean(value.cacheHit) || !nullableNumber(value.cacheAge) ||
    !nullableBoolean(value.stale) || !isDateTimeOrNull(value.lastSuccessAt) || !nullableString(value.dataRevision) ||
    typeof value.calculationVersion !== "string" || !nullableString(value.sourceCalculationVersion) ||
    !keysAllowed(value.price, ["open", "high", "low", "close", "volume"]) ||
    !finiteFields(value.price, ["open", "high", "low", "close", "volume"]) ||
    !keysAllowed(value.calculationBasis, ["ohlcv", "cutoff", "candlePrecision", "sourceSeries"]) ||
    !requiredTypes(value.calculationBasis, ["ohlcv", "cutoff", "candlePrecision", "sourceSeries"], "string") ||
    !keysAllowed(indicatorsValue, Object.keys(INDICATOR_FIELDS)) ||
    !Array.isArray(value.structures) || !keysAllowed(structureStatusValue, STRUCTURE_FAMILIES) ||
    !STRUCTURE_FAMILIES.every((family) => STRUCTURE_STATUS.includes(String(structureStatusValue[family])))
  ) return false;
  if (value.servedAt !== undefined && !isDateTimeOrNull(value.servedAt)) return false;
  if (value.barAsOf !== null && (!isBusinessDate(value.barAsOf) || value.barAsOf > date)) return false;
  if (value.sourceDate !== null && (!isBusinessDate(value.sourceDate) || value.sourceDate > date)) return false;
  if (!Object.keys(INDICATOR_FIELDS).every((group) => group in indicatorsValue)) return false;

  const indicators = indicatorsValue;
  for (const [group, fields] of Object.entries(INDICATOR_FIELDS)) {
    const required = group === "volumeProfile12" ? fields.filter((field) => field !== "binCount") : fields;
    const item = indicators[group];
    if (!keysAllowed(item, fields, required) || typeof item.status !== "string" || !INDICATOR_STATUS.includes(item.status)) return false;
    const numericFields: string[] = [];
    const stringFields: string[] = [];
    const integerFields: string[] = [];
    const booleanFields: string[] = [];
    const nullableBooleanFields: string[] = [];
    if (group === "movingAverages") {
      numericFields.push(...fields.filter((field) => !["status", "calculationVersion", "emaSeedPolicy", "wmaWeights"].includes(field)));
      stringFields.push("calculationVersion", "emaSeedPolicy", "wmaWeights");
    } else if (group === "bollinger20") {
      numericFields.push("middle", "upper", "lower"); integerFields.push("period", "multiplier"); stringFields.push("calculationVersion", "stddev");
    } else if (group === "donchian20") {
      numericFields.push("upper", "middle", "lower"); integerFields.push("period"); booleanFields.push("includeCurrent"); stringFields.push("calculationVersion");
    } else if (group === "rsi14" || group === "atr14") {
      numericFields.push("value"); stringFields.push("method", "seedPolicy"); nullableBooleanFields.push("provisional");
    } else if (group === "volume") {
      numericFields.push("barVolume", "ratio20"); integerFields.push("period"); booleanFields.push("includeCurrent");
    } else if (group === "macd129") {
      numericFields.push("macd", "signal", "histogram"); integerFields.push("fast", "slow", "signalPeriod"); stringFields.push("seedPolicy", "calculationVersion");
    } else if (group === "obv") {
      numericFields.push("value", "delta5"); stringFields.push("status", "delta5Status", "seedPolicy", "calculationVersion");
    } else if (group === "volumeProfile12") {
      numericFields.push("total"); integerFields.push("count"); stringFields.push("version", "method");
      if ("binCount" in item) integerFields.push("binCount");
      if (!nullableString(item.from) || !nullableString(item.to) || !Array.isArray(item.bins)) return false;
      if (item.status !== "insufficient-data" && (!Number.isInteger(item.binCount) || (item.binCount as number) < 1)) return false;
      if (!item.bins.every((bin: unknown) => keysAllowed(bin, ["low", "high", "volume", "share", "peak"]) &&
        finiteFields(bin, ["low", "high", "volume", "share"]) && typeof bin.peak === "boolean")) return false;
    }
    if (!finiteFields(item, numericFields) || !requiredTypes(item, stringFields, "string") ||
      !requiredTypes(item, integerFields, "integer") || !requiredTypes(item, booleanFields, "boolean") ||
      !nullableBooleanFields.every((field) => nullableBoolean(item[field]))) return false;
    if (group === "obv" && !["ready", "insufficient-data"].includes(String(item.delta5Status))) return false;
  }

  for (const structure of value.structures) {
    if (!keysAllowed(structure, ["family", "status", "timeframe", "barTime", "measurements"])) return false;
    const family = structure.family;
    if (!STRUCTURE_FAMILIES.includes(String(family)) || !STRUCTURE_ITEM_STATUS.includes(String(structure.status)) ||
      typeof structure.timeframe !== "string" || !nullableString(structure.barTime) || !Array.isArray(structure.measurements)) return false;
    for (const measurement of structure.measurements) {
      if (!keysAllowed(measurement, ["name", "label", "value", "unit"]) || typeof measurement.name !== "string" ||
        typeof measurement.label !== "string" || typeof measurement.unit !== "string" ||
        !(typeof measurement.value === "string" || finite(measurement.value)) || !STRUCTURE_UNITS.includes(measurement.unit) ||
        !structureMeasurementAllowed(String(family), measurement.name)) return false;
      const special = specialStructureLabel(String(family), measurement.name);
      if (special ? measurement.label !== special[0] || measurement.unit !== special[1] : measurement.label !== measurement.name) return false;
      if (measurement.name === "type" && !({ horizontal: ["prior-20-high", "prior-10-low", "user-resistance", "user-support"], flag: ["channel"], triangle: ["triangle"] }[String(family)] ?? []).includes(String(measurement.value))) return false;
      if (measurement.name === "geometry.kind" && !({ flag: ["channel"], triangle: ["triangle"] }[String(family)] ?? []).includes(String(measurement.value))) return false;
      if (measurement.name === "volumeEvidence" && !["volume-confirmed", "volume-insufficient"].includes(String(measurement.value))) return false;
    }
  }
  return true;
}

function structureMeasurementAllowed(family: string, name: string): boolean {
  if ((STRUCTURE_MEASUREMENT_NAMES[family] ?? []).includes(name)) return true;
  if (family === "flag") return /^pivot(?:High|Low)Times(?:\.\d+)?$/.test(name) || /^geometry\.points\.[1-4]\.(?:time|price)$/.test(name) || /^geometry\.pole\.[1-2]\.(?:time|price)$/.test(name);
  if (family === "triangle") return /^pivot(?:High|Low)Times(?:\.\d+)?$/.test(name) || /^geometry\.points\.(?:1|3)\.(?:time|price)$/.test(name) || /^geometry\.points\.2\.(?:anchorTime|logicalOffset|price)$/.test(name);
  return false;
}

function specialStructureLabel(family: string, name: string): [string, string] | undefined {
  if (family === "triangle" && name === "geometry.points.2.price") return ["삼각형 교점 · 직선 외삽값(목표가 아님)", "projected-price"];
  if (family === "triangle" && name === "geometry.points.2.logicalOffset") return ["삼각형 시작점부터 교점까지 봉 수 · 직선 외삽", "projected-bars"];
  if (family === "triangle" && name === "apexRemainingBars") return ["삼각형 교점까지 남은 봉 · 직선 외삽", "projected-bars"];
  return undefined;
}

const STRUCTURE_MEASUREMENT_NAMES: Record<string, string[]> = {
  horizontal: ["type", "boundary", "atr14Previous", "rvol20Previous", "volumeEvidence", "barTime", "close"],
  flag: ["type", "poleStartTime", "poleStartPrice", "poleEndTime", "poleEndPrice", "poleMove", "poleAtr", "adjustmentStartTime", "discoveredTime", "upper.slope", "upper.intercept", "lower.slope", "lower.intercept", "atr14Previous", "anchorTime", "pivotHighTimes", "pivotLowTimes", "containment", "barTime", "close", "upperPrice", "lowerPrice", "geometry.kind", "adjustmentBars", "rvol20Previous", "volumeEvidence", "retracementRatio", "adjustmentVolumeRatio"],
  triangle: ["type", "anchorTime", "structureStartTime", "discoveredTime", "upper.slope", "upper.intercept", "lower.slope", "lower.intercept", "atr14Previous", "pivotHighTimes", "pivotLowTimes", "contactCount", "containment", "barTime", "close", "geometry.kind", "geometry.observedThrough", "structureBars", "upperPrice", "lowerPrice", "boundary", "convergenceRatio", "apexRemainingBars", "rvol20Previous", "volumeEvidence"],
};

function isIndicatorChart(value: unknown, date: string): value is { bars: RecordValue[] } {
  if (!keysAllowed(value, ["bars"]) || !Array.isArray(value.bars) || value.bars.length > 380) return false;
  const fields = ["time", "open", "high", "low", "close", "volume", "sma20", "sma60", "sma120", "sma200", "rsi14", "macd", "macdSignal", "macdHistogram", "obv", "atr14"];
  let previous = "";
  for (const bar of value.bars) {
    if (!keysAllowed(bar, fields) || !isBusinessDate(bar.time) || bar.time > date || bar.time <= previous ||
      !fields.slice(1, 6).every((field) => finite(bar[field])) ||
      !fields.slice(6).every((field) => nullableNumber(bar[field]))) return false;
    previous = bar.time;
  }
  return true;
}

function isPriceConditions(value: unknown, date: string): value is RecordValue {
  return keysAllowed(value, ["price_condition_state", "reference_bar_date", "reference_close", "prior_20_bar_high", "prior_10_bar_low"]) &&
    ["insufficient_data", "above_prior_20_bar_high", "below_prior_10_bar_low", "within_reference_band"].includes(String(value.price_condition_state)) &&
    isDateOrNull(value.reference_bar_date, date) && ["reference_close", "prior_20_bar_high", "prior_10_bar_low"].every((key) => nullableNumber(value[key]));
}

function isIndicatorConfirmation(value: unknown): value is RecordValue {
  const fields = ["directional_alignment_state", "rsi_state", "macd_state", "moving_average_state", "sma_state", "ema_state", "wma_state", "bollinger_state", "donchian_state", "obv_state", "volume_confirmation_state", "volume_ratio20", "atr14_value", "atr14_percent_of_close", "volume_profile_state", "peak_volume_bins"];
  if (!keysAllowed(value, fields) || !ALIGNMENT_STATES.includes(String(value.directional_alignment_state)) ||
    !DIRECTION_STATES.includes(String(value.moving_average_state)) || !["confirmed", "below_threshold", "missing"].includes(String(value.volume_confirmation_state)) ||
    !["within_peak_volume_bins", "below_peak_volume_bins", "above_peak_volume_bins", "between_peak_volume_bins", "insufficient_data"].includes(String(value.volume_profile_state))) return false;
  for (const key of ["rsi_state", "macd_state", "sma_state", "ema_state", "wma_state", "bollinger_state", "donchian_state", "obv_state"]) {
    if (!["up", "down", "mixed", "neutral", "insufficient_data"].includes(String(value[key]))) return false;
  }
  return ["volume_ratio20", "atr14_value", "atr14_percent_of_close"].every((key) => nullableNumber(value[key])) &&
    Array.isArray(value.peak_volume_bins) && value.peak_volume_bins.every((bin: unknown) =>
      keysAllowed(bin, ["low", "high"]) && finite(bin.low) && finite(bin.high) && bin.low <= bin.high
    );
}

function isAvailableIndicatorItem(value: RecordValue, date: string): boolean {
  if (!isRecord(value.snapshot) || !isIndicatorSnapshot(value.snapshot, date, String(value.stock_code)) ||
    !isIndicatorChart(value.chart, date) || !isPriceConditions(value.price_conditions, date) ||
    !isIndicatorConfirmation(value.indicator_confirmation) || !CONDITION_STATES.includes(String(value.condition_status)) ||
    typeof value.condition_explanation !== "string") return false;
  const expectedSymbol = value.snapshot.market === "KOSPI" ? `${value.stock_code}.KS` : value.snapshot.market === "KOSDAQ" ? `${value.stock_code}.KQ` : String(value.stock_code);
  return value.snapshot.symbol === expectedSymbol && value.snapshot.barAsOf !== null;
}

export function isMainTop2IndicatorsSnapshot(value: unknown, date: string, expectedCodes: readonly string[]): value is MainTop2IndicatorsSnapshot {
  const fields = ["surface", "read_only", "configured", "live_fetch", "source", "adjusted", "page_size", "max_pages", "writes_stock_monitor_db", "sends_telegram", "registers_scheduler", "affects_ordering", "business_date", "derived_from", "items"];
  if (!keysAllowed(value, fields) || !isBusinessDate(date) || value.surface !== "web-view-priority-indicators" ||
    value.read_only !== true || typeof value.configured !== "boolean" || typeof value.live_fetch !== "boolean" ||
    value.source !== "toss-openapi-adjusted-daily" || value.adjusted !== true || value.page_size !== 200 || value.max_pages !== 4 ||
    value.writes_stock_monitor_db !== false || value.sends_telegram !== false || value.registers_scheduler !== false ||
    value.affects_ordering !== false || value.business_date !== date || value.derived_from !== "web_view_candidate_evidence_top_2" ||
    !Array.isArray(value.items) || value.items.length > 2 || value.items.length !== expectedCodes.length) return false;
  return value.items.every((item: unknown, index: number) => {
    const allowed = ["stock_code", "stock_name", "market", "market_source", "market_source_date", "available", "requested_as_of", "reason", "upstream_status", "candle_count", "pages_fetched", "history_status", "snapshot", "chart", "price_conditions", "indicator_confirmation", "condition_status", "condition_explanation"];
    if (!keysAllowed(item, allowed, allowed.slice(0, 7)) || !/^\d{6}$/.test(String(item.stock_code)) ||
      item.stock_code !== expectedCodes[index] || typeof item.stock_name !== "string" ||
      !(item.market === null || item.market === "KOSPI" || item.market === "KOSDAQ") ||
      !(item.market_source === null || item.market_source === "selected_date_toss_market_reference" || item.market_source === "stored_toss_stock_universe") ||
      !isDateOrNull(item.market_source_date, date) || typeof item.available !== "boolean" || item.requested_as_of !== date) return false;
    if (!item.available) return typeof item.reason === "string" && !["snapshot", "chart", "price_conditions", "indicator_confirmation", "condition_status", "condition_explanation"].some((key) => key in item);
    return (item.market === null ? item.market_source === null && item.market_source_date === null : item.market_source_date !== null) &&
      isAvailableIndicatorItem(item, date) &&
      Number.isInteger(item.candle_count) && (item.candle_count as number) >= 0 &&
      Number.isInteger(item.pages_fetched) && (item.pages_fetched as number) >= 1 && (item.pages_fetched as number) <= 4 &&
      ["complete", "cursor_not_provided", "page_limit_reached"].includes(String(item.history_status));
  });
}

export function isPriorityQuoteSnapshot(value: unknown, date: string, codes: readonly string[]): value is RecordValue {
  return isRecord(value) && value.surface === "web-view-toss-priority-quotes" && value.read_only === true &&
    value.priority_date === date && isBusinessDate(date) && typeof value.configured === "boolean" && typeof value.live_fetch === "boolean" &&
    value.writes_db === false && value.sends_telegram === false && value.registers_scheduler === false && value.affects_ordering === false &&
    Array.isArray(value.symbols) && value.symbols.length === codes.length && value.symbols.every((code: unknown, index: number) => code === codes[index]) &&
    Array.isArray(value.quotes) && value.quotes.every((quote: unknown) => isRecord(quote) && codes.includes(String(quote.symbol))) &&
    isRecord(value.investor_trading) && value.investor_trading.reference_date === date &&
    typeof value.investor_trading.available === "boolean" && Array.isArray(value.investor_trading.items) &&
    value.investor_trading.items.every((item: unknown) => isRecord(item) && codes.includes(String(item.symbol)) && item.business_date === date);
}

export function isPriorityCurrentQuotesSnapshot(value: unknown, date: string, codes: readonly string[]): value is RecordValue {
  return isRecord(value) && value.surface === "web-view-priority-current-quotes" && value.read_only === true && value.priority_date === date &&
    typeof value.live_fetch === "boolean" && value.writes_db === false && value.sends_telegram === false && value.registers_scheduler === false &&
    value.affects_ordering === false && Array.isArray(value.items) && value.items.every((item: unknown) =>
      isRecord(item) && codes.includes(String(item.stock_code)) && (item.current_price === null || finite(item.current_price)) &&
      (item.change_percent === null || finite(item.change_percent)) && (item.trade_amount === null || finite(item.trade_amount))
    );
}

export function isTossMarketContextSnapshot(value: unknown, date: string): value is RecordValue {
  return isRecord(value) && value.surface === "toss-market-context" && value.read_only === true &&
    value.reference_date === date && isBusinessDate(date) && value.writes_db === false && value.sends_telegram === false &&
    value.registers_scheduler === false && value.affects_ordering === false && Array.isArray(value.rankings) &&
    Array.isArray(value.market_prices) && Array.isArray(value.priority_overlap_symbols) && isRecord(value.investor_flow);
}

export function isIntradayMarketTopSnapshot(value: unknown, date: string, codes: readonly string[]): value is RecordValue {
  if (!isRecord(value) || !isBusinessDate(date) || value.surface !== "web-view" || value.read_only !== true || value.business_date !== date) return false;
  const commentary = value.market_commentary;
  if (!isRecord(commentary) || commentary.surface !== "market-commentary-practice" || commentary.read_only !== true || commentary.business_date !== date || typeof commentary.live_fetch !== "boolean") return false;
  const status = commentary.same_day_report_status;
  const reference = commentary.intraday_market_top_reference;
  const quoteReference = commentary.intraday_quote_reference;
  const boundary = commentary.boundary;
  if (!isRecord(status) || status.business_date !== date || typeof status.can_overlap_intraday_market_top !== "boolean" || typeof status.reason !== "string" ||
    !isRecord(reference) || reference.source !== "naver_price_top" || typeof reference.live_fetch !== "boolean" ||
    reference.writes_snapshot_tables !== false || !Array.isArray(reference.markets) || !reference.markets.every((market: unknown) => market === "KOSPI" || market === "KOSDAQ") ||
    !Number.isInteger(reference.limit) || (reference.limit as number) < 0 || (reference.limit as number) > 100 ||
    !Number.isInteger(reference.page_size) || (reference.page_size as number) < 1 || (reference.page_size as number) > 20 ||
    !isDateTimeOrNull(reference.checked_at) || !Array.isArray(reference.items) || !Array.isArray(reference.errors) ||
    !isRecord(quoteReference) || quoteReference.source !== "naver_quote" || typeof quoteReference.live_fetch !== "boolean" ||
    quoteReference.writes_snapshot_tables !== false || !Number.isInteger(quoteReference.limit) || (quoteReference.limit as number) < 0 ||
    (quoteReference.limit as number) > codes.length || !(quoteReference.delay_seconds === null || (finite(quoteReference.delay_seconds) && quoteReference.delay_seconds >= 0)) ||
    !Array.isArray(quoteReference.items) || !Array.isArray(quoteReference.errors) ||
    !isRecord(boundary) || boundary.public_numeric_score !== false || boundary.trading_recommendation !== false || boundary.telegram_send !== false) return false;
  return reference.items.every((item: unknown) => isRecord(item) && item.source === "naver_price_top" &&
    typeof item.stock_name === "string" && /^\d{6}$/.test(String(item.stock_code ?? "")) &&
    (item.market === "KOSPI" || item.market === "KOSDAQ") && Number.isInteger(item.rank) &&
    Number.isInteger(item.mention_count) && nullableNumber(item.current_price) && nullableNumber(item.change_price) &&
    nullableNumber(item.change_percent) && nullableNumber(item.trade_amount) && nullableNumber(item.trade_volume) &&
    typeof item.market_status === "string" && (item.trade_time === null || (typeof item.trade_time === "string" && Number.isFinite(Date.parse(item.trade_time)))) &&
    typeof item.checked_at === "string" && Number.isFinite(Date.parse(item.checked_at))) &&
    quoteReference.items.every((item: unknown) => isRecord(item) && typeof item.stock_name === "string" &&
      typeof item.stock_code === "string" && codes.includes(item.stock_code) && Number.isInteger(item.mention_count) &&
      ["current_price", "prev_close_price", "change_price", "change_percent", "trade_amount", "trade_volume"].every((key) => nullableNumber(item[key])) &&
      (item.market_status === null || typeof item.market_status === "string") && isDateTimeOrNull(item.trade_time) &&
      (item.resolution_source === "summary_stock_code" || item.resolution_source === "naver_search"));
}
