export const CHART_EXPLORER_TIMEFRAMES = ["1d", "1w", "4h", "1mo"] as const;

export type ChartExplorerTimeframe = typeof CHART_EXPLORER_TIMEFRAMES[number];
export type ChartExplorerBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  missingBarsBefore?: number;
};
export type ChartExplorerSession = { date: string; open: string; close: string };
export type ChartExplorerChartBar = ChartExplorerBar & {
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
export type ChartExplorerMeasurement = { name: string; label: string; value: string | number; unit: string };
export type ChartExplorerStructure = {
  family: "horizontal" | "flag" | "triangle";
  status: "forming";
  timeframe: ChartExplorerTimeframe;
  barTime: string;
  measurements: ChartExplorerMeasurement[];
};
export type ChartExplorerSnapshot = {
  barAsOf: string | null;
  timeframe: ChartExplorerTimeframe;
  price: Record<"open" | "high" | "low" | "close" | "volume", number | null>;
  indicators: {
    movingAverages: Record<"sma20" | "sma60" | "sma120" | "sma200" | "ema20" | "ema60" | "ema120" | "ema200" | "wma20" | "wma60" | "wma120" | "wma200", number | null> & {
      status: string; calculationVersion: string; emaSeedPolicy: string; wmaWeights: string;
    };
    bollinger20: { middle: number | null; upper: number | null; lower: number | null; status: string; period: number; multiplier: number; stddev: string; calculationVersion: string };
    donchian20: { upper: number | null; middle: number | null; lower: number | null; status: string; period: number; includeCurrent: boolean; calculationVersion: string };
    rsi14: { value: number | null; status: string; provisional: boolean | null; method: string; seedPolicy: string };
    atr14: { value: number | null; status: string; provisional: boolean | null; method: string; seedPolicy: string };
    volume: { barVolume: number | null; ratio20: number | null; status: string; period: number; includeCurrent: boolean };
    macd129: { macd: number | null; signal: number | null; histogram: number | null; status: string; fast: number; slow: number; signalPeriod: number; seedPolicy: string; calculationVersion: string };
    obv: { value: number | null; delta5: number | null; seedTime: string | null; status: string; delta5Status: string; seedPolicy: string; calculationVersion: string };
    volumeProfile12: {
      version: string; method: string; from: string | null; to: string | null; count: number; total: number;
      binCount?: number; bins: Array<{ low: number; high: number; volume: number; share: number; peak: boolean }>; status: string;
    };
  };
  structures: ChartExplorerStructure[];
  structureStatus: { horizontal: string; flag: string; triangle: string };
};
type ChartExplorerMetadata = {
  surface: "web-view-chart-explorer";
  read_only: true;
  writes_stock_monitor_db: false;
  live_fetch: boolean;
  requested_as_of: string | null;
  symbol: string | null;
  display_name: string;
  instrument_type: "stock" | "crypto" | null;
  timeframe: ChartExplorerTimeframe | null;
};
export type ChartExplorerSuccess = ChartExplorerMetadata & {
  requested_as_of: string;
  symbol: string;
  instrument_type: "stock";
  timeframe: ChartExplorerTimeframe;
  available: true;
  source: string;
  source_fetched_at: string;
  source_date: string | null;
  bar_status: "unknown";
  adjusted: boolean;
  currency: string | null;
  bars: ChartExplorerBar[];
  snapshot: ChartExplorerSnapshot;
  chart: { bars: ChartExplorerChartBar[] };
};
export type ChartExplorerUnavailable = ChartExplorerMetadata & {
  available: false;
  source: string | null;
  source_fetched_at: string | null;
  source_date: string | null;
  bar_status: "unknown" | null;
  adjusted: boolean | null;
  currency: string | null;
  reason: string;
};
export type ChartExplorerResponse = ChartExplorerSuccess | ChartExplorerUnavailable;

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

function isNumberOrNull(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isStringOrNull(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNumberRecord(value: unknown, keys: readonly string[]): boolean {
  return isRecord(value) && hasKeys(value, keys) && keys.every((key) => isNumberOrNull(value[key]));
}

function isVolumeProfile(value: unknown): boolean {
  if (!isRecord(value) || Object.keys(value).some((key) => !["version", "method", "from", "to", "count", "total", "binCount", "bins", "status"].includes(key)) ||
    !["version", "method", "from", "to", "count", "total", "bins", "status"].every((key) => Object.hasOwn(value, key)) ||
    typeof value.version !== "string" || value.method !== "hlc3" || !isStringOrNull(value.from) || !isStringOrNull(value.to) ||
    !Number.isInteger(value.count) || (value.count as number) < 0 || !isNumberOrNull(value.total) || typeof value.status !== "string" ||
    (value.binCount !== undefined && (!Number.isInteger(value.binCount) || (value.binCount as number) < 0)) || !Array.isArray(value.bins)) return false;
  return value.bins.every((bin) => isRecord(bin) && hasKeys(bin, ["low", "high", "volume", "share", "peak"]) &&
    isNumberOrNull(bin.low) && isNumberOrNull(bin.high) && isNumberOrNull(bin.volume) && isNumberOrNull(bin.share) && typeof bin.peak === "boolean");
}

export function isChartExplorerSnapshot(value: unknown): value is ChartExplorerSnapshot {
  if (!isRecord(value) || !hasKeys(value, ["barAsOf", "timeframe", "price", "indicators", "structures", "structureStatus"]) ||
    !isStringOrNull(value.barAsOf) || !isChartExplorerTimeframe(value.timeframe) ||
    !isNumberRecord(value.price, ["open", "high", "low", "close", "volume"]) || !isRecord(value.indicators) ||
    !hasKeys(value.indicators, ["movingAverages", "bollinger20", "donchian20", "rsi14", "atr14", "volume", "macd129", "obv", "volumeProfile12"]) ||
    !Array.isArray(value.structures) || !isRecord(value.structureStatus) ||
    !hasKeys(value.structureStatus, ["horizontal", "flag", "triangle"]) ||
    ![value.structureStatus.horizontal, value.structureStatus.flag, value.structureStatus.triangle].every((item) => typeof item === "string")) return false;

  const indicators = value.indicators;
  const movingKeys = ["sma20", "sma60", "sma120", "sma200", "ema20", "ema60", "ema120", "ema200", "wma20", "wma60", "wma120", "wma200"];
  const moving = indicators.movingAverages;
  if (!isRecord(moving) || !hasKeys(moving, [...movingKeys, "status", "calculationVersion", "emaSeedPolicy", "wmaWeights"]) ||
    !movingKeys.every((key) => isNumberOrNull(moving[key])) ||
    !["status", "calculationVersion", "emaSeedPolicy", "wmaWeights"].every((key) => typeof moving[key] === "string")) return false;

  const numericGroups = [
    [indicators.bollinger20, ["middle", "upper", "lower"]],
    [indicators.donchian20, ["upper", "middle", "lower"]],
    [indicators.rsi14, ["value"]], [indicators.atr14, ["value"]],
    [indicators.volume, ["barVolume", "ratio20"]],
    [indicators.macd129, ["macd", "signal", "histogram"]],
    [indicators.obv, ["value", "delta5"]],
  ] as const;
  if (numericGroups.some(([group, numericKeys]) => !isRecord(group) || numericKeys.some((key) => !isNumberOrNull(group[key])))) return false;
  const bollinger = indicators.bollinger20;
  if (!isRecord(bollinger) || !hasKeys(bollinger, ["middle", "upper", "lower", "status", "period", "multiplier", "stddev", "calculationVersion"]) ||
    !["status", "stddev", "calculationVersion"].every((key) => typeof bollinger[key] === "string") ||
    !Number.isFinite(bollinger.period) || !Number.isFinite(bollinger.multiplier)) return false;
  if (!isRecord(indicators.donchian20) || !hasKeys(indicators.donchian20, ["upper", "middle", "lower", "status", "period", "includeCurrent", "calculationVersion"]) ||
    typeof indicators.donchian20.status !== "string" || typeof indicators.donchian20.calculationVersion !== "string" ||
    !Number.isFinite(indicators.donchian20.period) || typeof indicators.donchian20.includeCurrent !== "boolean") return false;
  for (const [group, keys] of [[indicators.rsi14, ["value", "status", "provisional", "method", "seedPolicy"]],
    [indicators.atr14, ["value", "status", "provisional", "method", "seedPolicy"]]] as const) {
    if (!isRecord(group) || !hasKeys(group, keys) || typeof group.status !== "string" ||
      (group.provisional !== null && typeof group.provisional !== "boolean") || typeof group.method !== "string" || typeof group.seedPolicy !== "string") return false;
  }
  if (!isRecord(indicators.volume) || !hasKeys(indicators.volume, ["barVolume", "ratio20", "status", "period", "includeCurrent"]) ||
    typeof indicators.volume.status !== "string" || !Number.isFinite(indicators.volume.period) || typeof indicators.volume.includeCurrent !== "boolean") return false;
  const macd = indicators.macd129;
  if (!isRecord(macd) || !hasKeys(macd, ["macd", "signal", "histogram", "status", "fast", "slow", "signalPeriod", "seedPolicy", "calculationVersion"]) ||
    typeof macd.status !== "string" || !["fast", "slow", "signalPeriod"].every((key) => Number.isFinite(macd[key])) ||
    typeof macd.seedPolicy !== "string" || typeof macd.calculationVersion !== "string") return false;
  const obv = indicators.obv;
  if (!isRecord(obv) || !hasKeys(obv, ["value", "delta5", "seedTime", "status", "delta5Status", "seedPolicy", "calculationVersion"]) ||
    !isStringOrNull(obv.seedTime) || !["status", "delta5Status", "seedPolicy", "calculationVersion"].every((key) => typeof obv[key] === "string") ||
    !isVolumeProfile(indicators.volumeProfile12)) return false;

  return value.structures.every((item) => isRecord(item) && hasKeys(item, ["family", "status", "timeframe", "barTime", "measurements"]) &&
    ["horizontal", "flag", "triangle"].includes(String(item.family)) && item.status === "forming" && isChartExplorerTimeframe(item.timeframe) &&
    typeof item.barTime === "string" && Array.isArray(item.measurements) && item.measurements.every((measurement) =>
      isRecord(measurement) && hasKeys(measurement, ["name", "label", "value", "unit"]) && typeof measurement.name === "string" &&
      typeof measurement.label === "string" && (typeof measurement.value === "string" || Number.isFinite(measurement.value)) && typeof measurement.unit === "string"));
}

export function isChartExplorerTimeframe(value: unknown): value is ChartExplorerTimeframe {
  return typeof value === "string" && CHART_EXPLORER_TIMEFRAMES.includes(value as ChartExplorerTimeframe);
}

export function isChartExplorerSymbol(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9^][A-Za-z0-9.^=_-]{0,23}$/.test(value);
}

function dailyBucket(time: string, timeframe: "1w" | "1mo"): string {
  if (timeframe === "1mo") return `${time.slice(0, 7)}-01`;
  const date = new Date(`${time}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
  return date.toISOString().slice(0, 10);
}

function combine(bars: ChartExplorerBar[], time: string): ChartExplorerBar {
  return {
    time,
    open: bars[0].open,
    high: Math.max(...bars.map((bar) => bar.high)),
    low: Math.min(...bars.map((bar) => bar.low)),
    close: bars.at(-1)!.close,
    volume: bars.reduce((total, bar) => total + bar.volume, 0),
  };
}

export function aggregateDailyBars(
  bars: ReadonlyArray<ChartExplorerBar>,
  timeframe: "1d" | "1w" | "1mo",
): ChartExplorerBar[] {
  if (timeframe === "1d") return [...bars];
  const groups = new Map<string, ChartExplorerBar[]>();
  for (const bar of bars) {
    const key = dailyBucket(bar.time, timeframe);
    groups.set(key, [...(groups.get(key) ?? []), bar]);
  }
  return [...groups].map(([time, group]) => combine(group, time));
}

export function aggregateHourlyBarsToFourHours(
  bars: ReadonlyArray<ChartExplorerBar>, timezone: string, sessions?: ReadonlyArray<ChartExplorerSession>,
): ChartExplorerBar[] {
  if (sessions) {
    const sorted = [...sessions].sort((a, b) => a.open.localeCompare(b.open));
    const observed = new Map<string, ChartExplorerBar>();
    for (const bar of bars) {
      if (!Number.isFinite(Date.parse(bar.time)) || observed.has(bar.time)) throw new TypeError("invalid-hourly-bars");
      observed.set(bar.time, bar);
    }
    const result: ChartExplorerBar[] = [];
    let missing = 0;
    for (const session of sorted) {
      const start = Date.parse(session.open);
      const end = Date.parse(session.close);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(session.date) || !Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
        throw new TypeError("invalid-session-window");
      }
      const slots: number[] = [];
      // Yahoo's KRX 1h series ends at the 14:00 start slot for a 15:30 close.
      const slotCount = Math.floor((end - start) / (60 * 60 * 1000));
      for (let index = 0; index < slotCount; index += 1) slots.push(start + index * 60 * 60 * 1000);
      for (let offset = 0; offset < slots.length; offset += 4) {
        const group = slots.slice(offset, offset + 4).map((time) => observed.get(new Date(time).toISOString()));
        if (group.some((bar) => !bar)) { missing += 1; continue; }
        const row = combine(group as ChartExplorerBar[], new Date(slots[offset]).toISOString());
        result.push({ ...row, missingBarsBefore: missing });
        missing = 0;
      }
    }
    return result;
  }

  const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" });
  const days = new Map<string, ChartExplorerBar[]>();
  for (const bar of bars) {
    const parts = formatter.formatToParts(new Date(bar.time));
    const fields = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
    const day = `${fields.year}-${fields.month}-${fields.day}`;
    days.set(day, [...(days.get(day) ?? []), bar]);
  }
  return [...days].flatMap(([, dayBars]) => Array.from({ length: Math.ceil(dayBars.length / 4) }, (_, index) => {
    const group = dayBars.slice(index * 4, index * 4 + 4);
    return combine(group, group[0].time);
  }));
}

function isChartBar(value: unknown): value is ChartExplorerChartBar {
  const keys = ["time", "open", "high", "low", "close", "volume", "sma20", "sma60", "sma120", "sma200", "rsi14", "macd", "macdSignal", "macdHistogram", "obv", "atr14"];
  return isRecord(value) && hasKeys(value, keys) && typeof value.time === "string" &&
    ["open", "high", "low", "close", "volume"].every((key) => typeof value[key] === "number" && Number.isFinite(value[key])) &&
    ["sma20", "sma60", "sma120", "sma200", "rsi14", "macd", "macdSignal", "macdHistogram", "obv", "atr14"].every((key) => isNumberOrNull(value[key]));
}

export function isChartExplorerResponse(value: unknown): value is ChartExplorerResponse {
  if (!isRecord(value) || value.surface !== "web-view-chart-explorer" || value.read_only !== true ||
    value.writes_stock_monitor_db !== false || typeof value.live_fetch !== "boolean" ||
    (value.requested_as_of !== null && (typeof value.requested_as_of !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value.requested_as_of))) ||
    (value.symbol !== null && !isChartExplorerSymbol(value.symbol)) || typeof value.display_name !== "string" ||
    (value.instrument_type !== null && value.instrument_type !== "stock" && value.instrument_type !== "crypto") ||
    (value.timeframe !== null && !isChartExplorerTimeframe(value.timeframe)) || typeof value.available !== "boolean") return false;

  if (!value.available) {
    return hasKeys(value, ["surface", "read_only", "writes_stock_monitor_db", "live_fetch", "requested_as_of", "symbol", "display_name", "instrument_type", "timeframe", "available", "source", "source_fetched_at", "source_date", "bar_status", "adjusted", "currency", "reason"]) &&
      isStringOrNull(value.source) && isStringOrNull(value.source_fetched_at) && isStringOrNull(value.source_date) &&
      (value.bar_status === null || value.bar_status === "unknown") && (value.adjusted === null || typeof value.adjusted === "boolean") &&
      isStringOrNull(value.currency) && typeof value.reason === "string";
  }

  const keys = ["surface", "read_only", "writes_stock_monitor_db", "live_fetch", "requested_as_of", "symbol", "display_name", "instrument_type", "timeframe", "available", "source", "source_fetched_at", "source_date", "bar_status", "adjusted", "currency", "bars", "snapshot", "chart"];
  if (!hasKeys(value, keys) || typeof value.requested_as_of !== "string" || typeof value.symbol !== "string" ||
    value.instrument_type !== "stock" || !isChartExplorerTimeframe(value.timeframe) || typeof value.source !== "string" ||
    typeof value.source_fetched_at !== "string" || !Number.isFinite(Date.parse(value.source_fetched_at)) || !isStringOrNull(value.source_date) || value.bar_status !== "unknown" ||
    typeof value.adjusted !== "boolean" || !isStringOrNull(value.currency) || (typeof value.currency === "string" && !/^[A-Z]{3}$/.test(value.currency)) || !Array.isArray(value.bars) || !value.bars.every((bar) =>
      isRecord(bar) && hasKeys(bar, ["time", "open", "high", "low", "close", "volume"]) && typeof bar.time === "string" &&
      ["open", "high", "low", "close", "volume"].every((key) => typeof bar[key] === "number" && Number.isFinite(bar[key]))) ||
    !isChartExplorerSnapshot(value.snapshot) || !isRecord(value.chart) || !hasKeys(value.chart, ["bars"]) || !Array.isArray(value.chart.bars) ||
    !value.chart.bars.every(isChartBar) || value.bars.length !== value.chart.bars.length) return false;
  const chart = value.chart;
  const chartBars = chart.bars;
  if (!Array.isArray(chartBars)) return false;
  return value.bars.every((bar, index) => {
      const chartBar = chartBars[index] as ChartExplorerChartBar;
      return isRecord(bar) && bar.time === chartBar.time && bar.open === chartBar.open && bar.high === chartBar.high &&
        bar.low === chartBar.low && bar.close === chartBar.close && bar.volume === chartBar.volume;
    });
}
