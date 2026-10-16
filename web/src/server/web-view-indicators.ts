import "server-only";
import { createHash } from "node:crypto";
import type {
  ChartExplorerChartBar,
  ChartExplorerSnapshot,
  ChartExplorerTimeframe,
} from "../domain/chart-explorer.ts";

const CALCULATION_VERSION = "stock-monitor-indicator-v2";
const TECHNICAL_VERSION = "technical-v4";
const PROFILE_VERSION = "vp-1";
const PERIODS = [20, 60, 120, 200] as const;
const ACTION_TERMS = ["entry", "exit", "trigger", "invalidation", "recommend", "score", "grade", "signal", "direction", "buy", "sell"];
const NON_MEASUREMENTS = new Set([
  "patternid", "eventid", "eventtype", "ruleversion", "reason", "symbol", "timeframe", "startindex", "endindex",
  "poleindex", "confirmedindex", "terminalindex", "apexindex", "fittoleranceatr", "minimumcontainment", "maxoutsiderun",
  "maxretracement", "maxadjustmentbars", "provisionalinvalidation",
]);

type ValueRecord = Record<string, unknown>;
type Bar = { time: string; open: number; high: number; low: number; close: number; volume: number };
type NullableSeries = Array<number | null>;
type Line = { slope: number; intercept: number };

export type PriorityIndicatorInput = {
  code: string;
  symbol: string;
  market: "KOSPI" | "KOSDAQ" | "unknown";
  requestedAsOf: string;
  candles: ReadonlyArray<ValueRecord>;
  source: string;
  sourceFetchedAt: string | null;
  sourceDate?: string | null;
  barStatus?: "confirmed" | "provisional" | "unknown";
  confirmedPolicy?: string;
  cacheHit?: boolean | null;
  cacheAge?: number | null;
  stale?: boolean | null;
  lastSuccessAt?: string | null;
  sourceCalculationVersion?: string | null;
};

export type PriorityIndicatorProjection = {
  snapshot: ValueRecord;
  chart: { bars: ValueRecord[] };
  price_conditions: ValueRecord;
  indicator_confirmation: ValueRecord;
  condition_status: string;
  condition_explanation: string;
};

function number(value: unknown): number | null {
  if (typeof value === "boolean" || value === null || value === undefined) return null;
  if (typeof value !== "number" && typeof value !== "string") return null;
  if (typeof value === "string" && !/^[+-]?(?:(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|inf(?:inity)?|nan)$/i.test(value.trim())) return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function status(values: ReadonlyArray<unknown>): string {
  const count = values.filter((value) => value !== null && value !== undefined).length;
  return count === values.length ? "ready" : count ? "partial-data" : "insufficient-data";
}

function dateIsValid(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(0);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCFullYear(year, month - 1, day);
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function validateBars(candles: ReadonlyArray<ValueRecord>, requestedAsOf: string): Bar[] {
  const selected: Bar[] = [];
  const seen = new Set<string>();
  for (const raw of candles) {
    const stamp = raw.time;
    if (!dateIsValid(stamp)) throw new TypeError("invalid-daily-bar-date");
    if (stamp > requestedAsOf) continue;
    if (seen.has(stamp)) throw new TypeError("duplicate-daily-bar-date");
    const row = { time: stamp } as Bar;
    for (const key of ["open", "high", "low", "close", "volume"] as const) {
      const parsed = number(raw[key]);
      if (parsed === null || (parsed <= 0 && key !== "volume") || (key === "volume" && parsed < 0)) {
        throw new TypeError("invalid-daily-ohlcv");
      }
      row[key] = parsed;
    }
    if (row.high < Math.max(row.open, row.low, row.close) || row.low > Math.min(row.open, row.high, row.close)) {
      throw new TypeError("invalid-daily-ohlcv");
    }
    seen.add(stamp);
    selected.push(row);
  }
  return selected.sort((left, right) => left.time.localeCompare(right.time));
}

// Match CPython 3.12's float sum so Python/Next indicator snapshots remain identical.
function pythonFloatSum(values: ReadonlyArray<number>): number {
  let total = 0;
  let compensation = 0;
  for (const value of values) {
    const next = total + value;
    compensation += Math.abs(total) >= Math.abs(value)
      ? (total - next) + value
      : (value - next) + total;
    total = next;
  }
  return compensation && Number.isFinite(compensation) ? total + compensation : total;
}

function sma(values: ReadonlyArray<number>, period: number): NullableSeries {
  const result: NullableSeries = Array(values.length).fill(null);
  for (let index = period - 1; index < values.length; index += 1) {
    const window = values.slice(index - period + 1, index + 1);
    if (window.every(Number.isFinite)) result[index] = pythonFloatSum(window.map(value => value / period));
  }
  return result;
}

function ema(values: ReadonlyArray<number>, period: number): NullableSeries {
  const result: NullableSeries = Array(values.length).fill(null);
  const alpha = 2 / (period + 1);
  let seed: number[] = [];
  let previous: number | null = null;
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (!Number.isFinite(value)) {
      seed = [];
      previous = null;
      continue;
    }
    if (previous === null) {
      seed.push(value);
      if (seed.length < period) continue;
      previous = pythonFloatSum(seed.map(item => item / period));
      seed = [];
    } else {
      previous += alpha * (value - previous);
    }
    if (Number.isFinite(previous)) result[index] = previous;
    else {
      seed = [];
      previous = null;
    }
  }
  return result;
}

function wma(values: ReadonlyArray<number>, period: number): NullableSeries {
  const result: NullableSeries = Array(values.length).fill(null);
  const denominator = period * (period + 1) / 2;
  for (let index = period - 1; index < values.length; index += 1) {
    const window = values.slice(index - period + 1, index + 1);
    if (window.every(Number.isFinite)) result[index] = pythonFloatSum(window.map((value, offset) => value * (offset + 1) / denominator));
  }
  return result;
}

function bollinger(values: ReadonlyArray<number>, period = 20): { middle: number; upper: number; lower: number } | null {
  if (values.length < period) return null;
  const window = values.slice(-period);
  if (!window.every(Number.isFinite)) return null;
  const middle = pythonFloatSum(window.map(value => value / period));
  const deviation = Math.sqrt(pythonFloatSum(window.map(value => (value - middle) ** 2 / period)));
  return { middle, upper: middle + 2 * deviation, lower: middle - 2 * deviation };
}

function donchian(bars: ReadonlyArray<Bar>, period = 20): { upper: number; middle: number; lower: number } | null {
  if (bars.length < period) return null;
  const window = bars.slice(-period);
  const upper = Math.max(...window.map((row) => row.high));
  const lower = Math.min(...window.map((row) => row.low));
  return { upper, middle: upper / 2 + lower / 2, lower };
}

function rsiSeries(values: ReadonlyArray<number>, period = 14): NullableSeries {
  const result: NullableSeries = Array(values.length).fill(null);
  if (values.length <= period) return result;
  const changes = values.slice(1).map((value, index) => value - values[index]);
  const gains = changes.map((change) => Math.max(change, 0));
  const losses = changes.map((change) => Math.max(-change, 0));
  let averageGain = pythonFloatSum(gains.slice(0, period)) / period;
  let averageLoss = pythonFloatSum(losses.slice(0, period)) / period;
  const calculate = () => averageGain === 0 && averageLoss === 0 ? 50 : averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss);
  result[period] = calculate();
  for (let index = period; index < gains.length; index += 1) {
    averageGain = (averageGain * (period - 1) + gains[index]) / period;
    averageLoss = (averageLoss * (period - 1) + losses[index]) / period;
    result[index + 1] = calculate();
  }
  return result;
}

function trueRanges(bars: ReadonlyArray<Bar>): number[] {
  return bars.map((bar, index) => {
    const previous = index ? bars[index - 1].close : bar.close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previous), Math.abs(bar.low - previous));
  });
}

function atrSeries(bars: ReadonlyArray<Bar>, period = 14): NullableSeries {
  const ranges = trueRanges(bars);
  const result: NullableSeries = Array(ranges.length).fill(null);
  if (ranges.length < period) return result;
  result[period - 1] = pythonFloatSum(ranges.slice(0, period)) / period;
  for (let index = period; index < ranges.length; index += 1) {
    result[index] = ((result[index - 1] as number) * (period - 1) + ranges[index]) / period;
  }
  return result;
}

function volumeProfile(bars: ReadonlyArray<Bar>): ValueRecord {
  if (bars.length < 10) return { version: PROFILE_VERSION, method: "hlc3", from: null, to: null, count: bars.length, total: 0, bins: [], status: "insufficient-data" };
  const low = Math.min(...bars.map((row) => row.low));
  const high = Math.max(...bars.map((row) => row.high));
  const count = high === low ? 1 : 12;
  const step = (high - low) / count;
  const bins = Array.from({ length: count }, (_, index) => ({ low: low + index * step, high: low + (index + 1) * step, volume: 0 }));
  for (const row of bars) {
    const typical = (row.high + row.low + row.close) / 3;
    const index = step ? Math.min(count - 1, Math.max(0, Math.trunc((typical - low) / step))) : 0;
    bins[index].volume += row.volume;
  }
  const total = pythonFloatSum(bins.map(item => item.volume));
  const peak = Math.max(...bins.map((item) => item.volume));
  return {
    version: PROFILE_VERSION,
    method: "hlc3",
    from: bars[0].time,
    to: bars.at(-1)?.time ?? null,
    count: bars.length,
    total,
    binCount: count,
    bins: bins.map((item) => ({ ...item, share: total ? item.volume / total : 0, peak: Boolean(total && item.volume === peak) })),
    status: "ready",
  };
}

function line(model: Line, index: number): number {
  return model.intercept + model.slope * index;
}

function fit(points: ReadonlyArray<[number, number]>): Line | null {
  if (points.length < 2) return null;
  const meanX = points.reduce((sum, [index]) => sum + index, 0) / points.length;
  const meanY = pythonFloatSum(points.map(([, value]) => value)) / points.length;
  const denominator = pythonFloatSum(points.map(([index]) => (index - meanX) ** 2));
  if (!denominator) return null;
  const slope = pythonFloatSum(points.map(([index, value]) => (index - meanX) * (value - meanY))) / denominator;
  return { slope, intercept: meanY - slope * meanX };
}

function pivots(bars: ReadonlyArray<Bar>, through: number): [Array<[number, number]>, Array<[number, number]>] {
  const highs: Array<[number, number]> = [];
  const lows: Array<[number, number]> = [];
  for (let index = 2; index < through - 1; index += 1) {
    const high = bars[index].high;
    const low = bars[index].low;
    if ([index - 2, index - 1].every((offset) => high >= bars[offset].high) && [index + 1, index + 2].every((offset) => high > bars[offset].high)) highs.push([index, high]);
    if ([index - 2, index - 1].every((offset) => low <= bars[offset].low) && [index + 1, index + 2].every((offset) => low < bars[offset].low)) lows.push([index, low]);
  }
  return [highs, lows];
}

function coverage(bars: ReadonlyArray<Bar>, start: number, end: number, upper: Line, lower: Line, tolerance: number): [number, number] {
  let inside = 0;
  let run = 0;
  let longest = 0;
  for (let index = start; index <= end; index += 1) {
    const contained = bars[index].high <= line(upper, index) + tolerance && bars[index].low >= line(lower, index) - tolerance;
    if (contained) {
      inside += 1;
      run = 0;
    } else {
      run += 1;
      longest = Math.max(longest, run);
    }
  }
  return end >= start ? [inside / (end - start + 1), longest] : [0, 0];
}

function measurementUnit(name: string, value: unknown): string {
  const key = name.split(".").at(-1)!.toLowerCase();
  if (typeof value === "string") return key.includes("time") || key === "observedthrough" ? "date" : "state";
  if (key.includes("price") || ["open", "high", "low", "close", "boundary", "polemove", "poleatr", "atr14previous"].includes(key) || key.endsWith("intercept")) return "price";
  if (key.includes("slope")) return "price-per-bar";
  if (key.includes("volume") && !key.includes("ratio")) return "volume";
  if (key.includes("ratio") || key.includes("containment") || key.includes("retracement")) return "ratio";
  if (key.includes("bar") || key.includes("offset")) return "bars";
  if (key.includes("count")) return "count";
  return "number";
}

function collectMeasurements(item: ValueRecord, family: string): ValueRecord[] {
  const output: ValueRecord[] = [];
  const special = (name: string): [string, string] | null => {
    if (family !== "triangle") return null;
    const key = name.toLowerCase();
    if (key === "geometry.points.2.price") return ["삼각형 교점 · 직선 외삽값(목표가 아님)", "projected-price"];
    if (key === "geometry.points.2.logicaloffset") return ["삼각형 시작점부터 교점까지 봉 수 · 직선 외삽", "projected-bars"];
    if (key === "apexremainingbars") return ["삼각형 교점까지 남은 봉 · 직선 외삽", "projected-bars"];
    return null;
  };
  const collect = (name: string, value: unknown) => {
    const key = name.split(".").at(-1)!.toLowerCase();
    if (ACTION_TERMS.some((term) => key.includes(term)) || NON_MEASUREMENTS.has(key)) return;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      for (const [child, nested] of Object.entries(value)) collect(name ? `${name}.${child}` : child, nested);
    } else if (Array.isArray(value)) {
      if (key.endsWith("times")) output.push({ name, label: name, value: value.length, unit: "count" });
      value.forEach((nested, index) => collect(`${name}.${index + 1}`, nested));
    } else if (typeof value === "string") {
      if (["type", "kind", "volumeevidence", "time", "observedthrough", "poleendtime", "polestarttime"].includes(key) || name.toLowerCase().includes("time")) {
        const normalized = key === "type" && family === "flag" ? "channel" : key === "type" && family === "triangle" ? "triangle" : value;
        const labelUnit = special(name);
        output.push({ name, label: labelUnit?.[0] ?? name, value: normalized, unit: labelUnit?.[1] ?? measurementUnit(name, normalized) });
      }
    } else if (typeof value === "number" && Number.isFinite(value)) {
      const labelUnit = special(name);
      output.push({ name, label: labelUnit?.[0] ?? name, value, unit: labelUnit?.[1] ?? measurementUnit(name, value) });
    }
  };
  for (const [key, value] of Object.entries(item)) if (!["status", "timeframe", "barTime"].includes(key)) collect(key, value);
  return output;
}

function flagCandidates(bars: ReadonlyArray<Bar>, atr: NullableSeries, highs: Array<[number, number]>, lows: Array<[number, number]>, timeframe = "D"): ValueRecord[] {
  const end = bars.length - 1;
  if (end < 20) return [];
  const found: ValueRecord[] = [];
  for (let start = Math.max(17, end - 30 + 1); start < end - 3; start += 1) {
    const choices: Array<{ move: number; length: number; pole: number; delta: number }> = [];
    for (let length = 3; length < 11; length += 1) {
      const pole = start - length;
      if (pole < 14 || atr[pole - 1] === null) continue;
      const delta = bars[start - 1].close - bars[pole].close;
      if (Math.abs(delta) >= 2.5 * (atr[pole - 1] as number)) choices.push({ move: Math.abs(delta), length, pole, delta });
    }
    if (!choices.length || atr[start - 1] === null) continue;
    choices.sort((left, right) => right.move - left.move || left.length - right.length);
    const { move, length, pole, delta } = choices[0];
    const sign = delta > 0 ? 1 : -1;
    if (sign * (bars[start].close - bars[start - 1].close) > 0.5 * (atr[start - 1] as number)) continue;
    const hp = highs.filter(([index]) => index >= start && index <= end - 2);
    const lp = lows.filter(([index]) => index >= start && index <= end - 2);
    if (hp.length < 2 || lp.length < 2 || atr[end - 1] === null || (atr[end - 1] as number) <= 0) continue;
    const upper = fit(hp);
    const lower = fit(lp);
    if (!upper || !lower) continue;
    const a = atr[end - 1] as number;
    if ([upper, lower].some((model) => sign * model.slope > 0.03 * a)) continue;
    if (Math.abs(upper.slope - lower.slope) > 0.12 * a) continue;
    if ([[hp, upper], [lp, lower]].some(([points, model]) => (points as Array<[number, number]>).some(([index, value]) => Math.abs(value - line(model as Line, index)) > 0.4 * a))) continue;
    if (Array.from({ length: end - start + 1 }, (_, offset) => start + offset).some((index) => line(upper, index) <= line(lower, index))) continue;
    const [contained, outsideRun] = coverage(bars, start, end, upper, lower, 0.4 * a);
    if (contained < 0.7 || outsideRun > 2) continue;
    const extreme = sign === 1 ? Math.min(...bars.slice(start, end + 1).map((row) => row.low)) : Math.max(...bars.slice(start, end + 1).map((row) => row.high));
    const retracement = Math.max(0, (sign === 1 ? bars[start - 1].close - extreme : extreme - bars[start - 1].close) / move);
    if (retracement > 0.618) continue;
    const poleVolume = pythonFloatSum(bars.slice(pole, start).map(row => row.volume)) / length;
    const adjustmentVolume = pythonFloatSum(bars.slice(start, end + 1).map(row => row.volume)) / (end - start + 1);
    found.push({
      type: sign === 1 ? "bull-flag" : "bear-flag", status: "forming", timeframe, barTime: bars[end].time,
      adjustmentStartTime: bars[start].time, poleStartTime: bars[pole].time, poleEndTime: bars[start - 1].time,
      poleStartPrice: bars[pole].close, poleEndPrice: bars[start - 1].close, poleMove: move,
      poleAtr: atr[pole - 1], upper, lower, pivotHighTimes: hp.map(([index]) => bars[index].time),
      pivotLowTimes: lp.map(([index]) => bars[index].time), containment: contained,
      adjustmentVolumeRatio: poleVolume ? adjustmentVolume / poleVolume : null, retracementRatio: retracement,
      geometry: {
        kind: "channel",
        points: [
          { time: bars[start].time, price: line(upper, start) }, { time: bars[end].time, price: line(upper, end) },
          { time: bars[end].time, price: line(lower, end) }, { time: bars[start].time, price: line(lower, start) },
        ],
        pole: [{ time: bars[pole].time, price: bars[pole].close }, { time: bars[start - 1].time, price: bars[start - 1].close }],
      },
    });
  }
  return ["bull-flag", "bear-flag"].flatMap((kind) => {
    const rows = found.filter((row) => row.type === kind);
    return rows.length ? [rows.reduce((latest, row) => String(row.adjustmentStartTime) > String(latest.adjustmentStartTime) ? row : latest)] : [];
  });
}

function triangleCandidate(bars: ReadonlyArray<Bar>, atr: NullableSeries, highs: Array<[number, number]>, lows: Array<[number, number]>, timeframe = "D"): ValueRecord | null {
  const end = bars.length - 1;
  if (end < 20 || atr[end - 1] === null || (atr[end - 1] as number) <= 0) return null;
  const a = atr[end - 1] as number;
  for (let requestedStart = Math.max(14, end - 59); requestedStart < end - 8 + 2; requestedStart += 1) {
    const hp = highs.filter(([index]) => index >= requestedStart && index <= end - 2);
    const lp = lows.filter(([index]) => index >= requestedStart && index <= end - 2);
    if (hp.length < 2 || lp.length < 2 || hp.length + lp.length < 5) continue;
    const start = Math.min(hp[0][0], lp[0][0]);
    if (end - start + 1 < 8 || end - start + 1 > 60) continue;
    const upper = fit(hp);
    const lower = fit(lp);
    if (!upper || !lower) continue;
    const { slope: upperSlope } = upper;
    const { slope: lowerSlope } = lower;
    let kind: string;
    if (upperSlope <= -0.02 * a && lowerSlope >= 0.02 * a) kind = "symmetrical-triangle";
    else if (Math.abs(upperSlope) <= 0.03 * a && lowerSlope >= 0.02 * a) kind = "ascending-triangle";
    else if (upperSlope <= -0.02 * a && Math.abs(lowerSlope) <= 0.03 * a) kind = "descending-triangle";
    else continue;
    if ([[hp, upper], [lp, lower]].some(([points, model]) => (points as Array<[number, number]>).some(([index, value]) => Math.abs(value - line(model as Line, index)) > 0.4 * a))) continue;
    const width = line(upper, start) - line(lower, start);
    const lastWidth = line(upper, end) - line(lower, end);
    if (width <= 0 || lastWidth <= 0 || lastWidth / width > 0.75) continue;
    const denominator = upperSlope - lowerSlope;
    if (denominator === 0) continue;
    const apex = (lower.intercept - upper.intercept) / denominator;
    if (apex <= end) continue;
    const [contained, outsideRun] = coverage(bars, start, end, upper, lower, 0.4 * a);
    if (contained < 0.7 || outsideRun > 2) continue;
    const apexPrice = line(upper, apex);
    return {
      type: kind, status: "forming", timeframe, barTime: bars[end].time, structureStartTime: bars[start].time,
      upper, lower, contactCount: hp.length + lp.length, containment: contained, convergenceRatio: lastWidth / width,
      apexRemainingBars: apex - end, pivotHighTimes: hp.map(([index]) => bars[index].time),
      pivotLowTimes: lp.map(([index]) => bars[index].time),
      geometry: {
        kind: "triangle",
        points: [
          { time: bars[start].time, price: line(upper, start) },
          { anchorTime: bars[start].time, logicalOffset: apex - start, price: apexPrice },
          { time: bars[start].time, price: line(lower, start) },
        ],
        observedThrough: bars[end].time,
      },
    };
  }
  return null;
}

function structures(bars: ReadonlyArray<Bar>, atr: NullableSeries, timeframe = "D"): { items: ValueRecord[]; status: ValueRecord } {
  const structureStatus: ValueRecord = { horizontal: "insufficient-data", flag: "insufficient-data", triangle: "insufficient-data" };
  if (!bars.length) return { items: [], status: structureStatus };
  const items: ValueRecord[] = [];
  const end = bars.length - 1;
  if (bars.length >= 21 && atr[end - 1] !== null) {
    const previousHigh = Math.max(...bars.slice(-21, -1).map((row) => row.high));
    const previousLow = Math.min(...bars.slice(-11, -1).map((row) => row.low));
    const previousAtr = atr[end - 1] as number;
    const previousVolumes = pythonFloatSum(bars.slice(end - 20, end).map(row => row.volume));
    const relativeVolume = previousVolumes > 0 ? bars[end].volume / (previousVolumes / 20) : null;
    for (const [kind, boundary] of [["prior-20-high", previousHigh], ["prior-10-low", previousLow]] as const) {
      const item: ValueRecord = {
        type: kind, status: "forming", timeframe, barTime: bars[end].time, boundary, close: bars[end].close,
        atr14Previous: previousAtr, rvol20Previous: relativeVolume,
        volumeEvidence: relativeVolume !== null && relativeVolume >= 1.2 ? "volume-confirmed" : "volume-insufficient",
      };
      items.push({ family: "horizontal", status: "forming", timeframe, barTime: bars[end].time, measurements: collectMeasurements(item, "horizontal") });
    }
    structureStatus.horizontal = "ready";
  } else if (bars.length >= 21) structureStatus.horizontal = "partial-data";

  const [highs, lows] = pivots(bars, end);
  const flags = bars.length >= 21 ? flagCandidates(bars, atr, highs, lows, timeframe) : [];
  for (const item of flags) items.push({ family: "flag", status: "forming", timeframe, barTime: item.barTime, measurements: collectMeasurements(item, "flag") });
  structureStatus.flag = flags.length ? "ready" : bars.length >= 31 ? "no-geometry" : "insufficient-data";
  const triangle = bars.length >= 21 ? triangleCandidate(bars, atr, highs, lows, timeframe) : null;
  if (triangle) items.push({ family: "triangle", status: "forming", timeframe, barTime: triangle.barTime, measurements: collectMeasurements(triangle, "triangle") });
  structureStatus.triangle = triangle ? "ready" : bars.length >= 31 ? "no-geometry" : "insufficient-data";
  return { items, status: structureStatus };
}

function pythonFloat(value: number): string {
  if (Object.is(value, -0)) return "-0.0";
  let raw = value.toString().toLowerCase();
  const absolute = Math.abs(value);
  const wantsExponent = absolute !== 0 && (absolute >= 1e16 || absolute < 1e-4);
  const expand = (digits: string, point: number): string => {
    if (point <= 0) return `0.${"0".repeat(-point)}${digits}`;
    if (point >= digits.length) return `${digits}${"0".repeat(point - digits.length)}`;
    return `${digits.slice(0, point)}.${digits.slice(point)}`;
  };
  let sign = "";
  if (raw.startsWith("-")) { sign = "-"; raw = raw.slice(1); }
  let [mantissa, exponentText] = raw.split("e");
  const exponent = exponentText === undefined ? 0 : Number(exponentText);
  const [whole, fraction = ""] = mantissa.split(".");
  const rawDigits = `${whole}${fraction}`;
  const leadingZeros = rawDigits.match(/^0*/)?.[0].length ?? 0;
  const digits = rawDigits.replace(/^0+/, "") || "0";
  const point = whole.length + exponent - leadingZeros;
  if (wantsExponent) {
    const significant = digits.replace(/0+$/, "") || "0";
    const power = point - 1;
    const exp = `${power >= 0 ? "+" : "-"}${String(Math.abs(power)).padStart(2, "0")}`;
    return `${sign}${significant[0]}${significant.length > 1 ? `.${significant.slice(1)}` : ""}e${exp}`;
  }
  const fixed = expand(digits, point);
  return `${sign}${fixed.includes(".") ? fixed : `${fixed}.0`}`;
}

function revisionHash(bars: ReadonlyArray<Bar>): string {
  const serialized = `[${bars.map((bar) => `{"close":${pythonFloat(bar.close)},"high":${pythonFloat(bar.high)},"low":${pythonFloat(bar.low)},"open":${pythonFloat(bar.open)},"time":${JSON.stringify(bar.time)},"volume":${pythonFloat(bar.volume)}}`).join(",")}]`;
  return `sha256:${createHash("sha256").update(serialized, "utf8").digest("hex")}`;
}

function buildSnapshot(input: PriorityIndicatorInput, bars: ReadonlyArray<Bar>, structureTimeframe = "D"): ValueRecord {
  const closes = bars.map((row) => row.close);
  const volumes = bars.map((row) => row.volume);
  const moving: ValueRecord = {};
  for (const [kind, compute] of [["sma", sma], ["ema", ema], ["wma", wma]] as const) {
    for (const period of PERIODS) {
      const series = compute(closes, period);
      moving[`${kind}${period}`] = series.at(-1) ?? null;
    }
  }
  const movingValues = Object.values(moving);
  const bb = bollinger(closes);
  const dc = donchian(bars);
  const rsi = rsiSeries(closes).at(-1) ?? null;
  const atr = atrSeries(bars).at(-1) ?? null;
  const volumeTotal = pythonFloatSum(volumes.slice(-20));
  const ratio = volumes.length >= 20 && volumeTotal > 0 ? volumes.at(-1)! / (volumeTotal / 20) : null;
  const fast = ema(closes, 12);
  const slow = ema(closes, 26);
  const macdSeries = closes.map((_, index) => fast[index] !== null && slow[index] !== null ? (fast[index] as number) - (slow[index] as number) : Number.NaN);
  const signal = ema(macdSeries, 9);
  const lastMacd = macdSeries.at(-1);
  const macdLine = lastMacd !== undefined && Number.isFinite(lastMacd) ? lastMacd : null;
  const lastSignal = signal.at(-1);
  const signalLine = lastSignal !== null && lastSignal !== undefined && Number.isFinite(lastSignal) ? lastSignal : null;
  const histogram = macdLine !== null && signalLine !== null ? macdLine - signalLine : null;
  const obvValues: number[] = [];
  for (let index = 0; index < bars.length; index += 1) {
    const direction = index ? closes[index] > closes[index - 1] ? 1 : closes[index] < closes[index - 1] ? -1 : 0 : 0;
    obvValues.push((obvValues.at(-1) ?? 0) + direction * bars[index].volume);
  }
  const obv = obvValues.at(-1) ?? null;
  const delta5 = obvValues.length >= 6 ? obvValues.at(-1)! - obvValues.at(-6)! : null;
  const profile = volumeProfile(bars);
  const structure = structures(bars, atrSeries(bars), structureTimeframe);
  const last = bars.at(-1);
  const price: ValueRecord = Object.fromEntries(["open", "high", "low", "close", "volume"].map((key) => [key, last?.[key as keyof Bar] ?? null]));
  const macdObject = { macd: macdLine, signal: signalLine, histogram };
  const volumeStatus = price.volume !== null && ratio !== null ? "ready" : price.volume !== null ? "partial-data" : "insufficient-data";
  const obvStatus = obv !== null && delta5 !== null ? "ready" : obv !== null ? "partial-data" : "insufficient-data";
  const market = input.market;
  const sourceDate = input.sourceDate || input.candles.reduce<string | null>((latest, row) => {
    const stamp = typeof row.time === "string" ? row.time : null;
    return stamp && (!latest || stamp > latest) ? stamp : latest;
  }, null);
  return {
    schemaVersion: 1,
    code: input.code,
    symbol: input.symbol,
    market,
    timeframe: "D",
    requestedAsOf: input.requestedAsOf,
    barAsOf: last?.time ?? null,
    source: input.source,
    sourceFetchedAt: input.sourceFetchedAt,
    sourceDate,
    barStatus: bars.length ? input.barStatus ?? "unknown" : "unknown",
    confirmedPolicy: input.confirmedPolicy ?? "unknown",
    cacheHit: input.cacheHit ?? null,
    cacheAge: input.cacheAge ?? null,
    stale: input.stale ?? null,
    lastSuccessAt: input.lastSuccessAt || input.sourceFetchedAt,
    dataRevision: revisionHash(bars),
    calculationVersion: CALCULATION_VERSION,
    sourceCalculationVersion: input.sourceCalculationVersion ?? null,
    calculationBasis: {
      ohlcv: "provider-adjusted daily candles",
      cutoff: "last candle on or before requestedAsOf; calculations use only that prefix",
      candlePrecision: "source OHLC precision preserved; volume as provided",
      sourceSeries: "all indicators calculated from the same adjusted OHLCV prefix",
    },
    price,
    indicators: {
      movingAverages: { ...moving, status: status(movingValues), calculationVersion: TECHNICAL_VERSION, emaSeedPolicy: "sma-period", wmaWeights: "linear-oldest-1-newest-period" },
      bollinger20: { ...(bb ?? { middle: null, upper: null, lower: null }), status: status(Object.values(bb ?? { middle: null, upper: null, lower: null })), period: 20, multiplier: 2, stddev: "population", calculationVersion: TECHNICAL_VERSION },
      donchian20: { ...(dc ?? { upper: null, middle: null, lower: null }), status: status(Object.values(dc ?? { upper: null, middle: null, lower: null })), period: 20, includeCurrent: true, calculationVersion: TECHNICAL_VERSION },
      rsi14: { value: rsi, status: rsi !== null ? "ready" : "insufficient-data", provisional: input.barStatus === "provisional" ? true : input.barStatus === "confirmed" ? false : null, method: "wilder", seedPolicy: "simple-average-14-changes" },
      atr14: { value: atr, status: atr !== null ? "ready" : "insufficient-data", provisional: input.barStatus === "provisional" ? true : input.barStatus === "confirmed" ? false : null, method: "wilder", seedPolicy: "simple-average-14-true-ranges" },
      volume: { barVolume: price.volume, ratio20: ratio, status: volumeStatus, period: 20, includeCurrent: true },
      macd129: { ...macdObject, status: status(Object.values(macdObject)), fast: 12, slow: 26, signalPeriod: 9, seedPolicy: "sma-period", calculationVersion: TECHNICAL_VERSION },
      obv: { value: obv, delta5, seedTime: bars[0]?.time ?? null, status: obvStatus, delta5Status: delta5 !== null ? "ready" : "insufficient-data", seedPolicy: "first-bar-zero-stop-on-gap", calculationVersion: TECHNICAL_VERSION },
      volumeProfile12: profile,
    },
    structures: structure.items,
    structureStatus: structure.status,
  };
}

function validateChartExplorerBars(candles: ReadonlyArray<ValueRecord>, requestedAsOf: string, sourceTimezone: string): Bar[] {
  if (candles.length > 10_000) throw new TypeError("chart-history-exceeds-limit");
  const dateFormatter = new Intl.DateTimeFormat("en-CA", { timeZone: sourceTimezone, year: "numeric", month: "2-digit", day: "2-digit" });
  const seen = new Set<string>();
  const selected: Bar[] = [];
  for (const raw of candles) {
    const stamp = raw.time;
    if (typeof stamp !== "string" || (Object.keys(raw).some((key) => !["time", "open", "high", "low", "close", "volume"].includes(key))) ||
      ["time", "open", "high", "low", "close", "volume"].some((key) => !Object.hasOwn(raw, key))) {
      throw new TypeError("invalid-chart-bar-shape");
    }
    const daily = isDailyDate(stamp);
    const parsedTime = daily ? Date.parse(`${stamp}T00:00:00Z`) :
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(stamp) && dateIsValid(stamp.slice(0, 10)) ? Date.parse(stamp) : NaN;
    if (!daily && Number.isFinite(parsedTime) && new Date(parsedTime).toISOString() !== stamp) throw new TypeError("invalid-chart-bar-time");
    if (!Number.isFinite(parsedTime) || (daily && parsedTime > Date.parse(`${requestedAsOf}T00:00:00Z`))) {
      if (daily && stamp > requestedAsOf) continue;
      throw new TypeError("invalid-chart-bar-time");
    }
    if (!daily) {
      const parts = dateFormatter.formatToParts(new Date(parsedTime));
      const localDate = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
      if (`${localDate.year}-${localDate.month}-${localDate.day}` > requestedAsOf) continue;
    }
    if (seen.has(stamp)) throw new TypeError("duplicate-chart-bar-time");
    const row = { time: stamp } as Bar;
    for (const key of ["open", "high", "low", "close", "volume"] as const) {
      const parsed = number(raw[key]);
      if (parsed === null || (parsed <= 0 && key !== "volume") || (key === "volume" && parsed < 0)) {
        throw new TypeError("invalid-chart-ohlcv");
      }
      row[key] = parsed;
    }
    if (row.high < Math.max(row.open, row.low, row.close) || row.low > Math.min(row.open, row.high, row.close)) {
      throw new TypeError("invalid-chart-ohlcv");
    }
    seen.add(stamp);
    selected.push(row);
  }
  return selected.sort((left, right) => left.time.localeCompare(right.time));
}

function isDailyDate(value: string): boolean { return dateIsValid(value); }

export function buildChartExplorerProjection(input: {
  requestedAsOf: string;
  symbol: string;
  timeframe: ChartExplorerTimeframe;
  candles: ReadonlyArray<ValueRecord>;
  source: string;
  sourceFetchedAt: string;
  sourceTimezone: string;
}): {
  snapshot: ChartExplorerSnapshot;
  chart: { bars: ChartExplorerChartBar[] };
} {
  if (!dateIsValid(input.requestedAsOf)) throw new TypeError("requested-as-of-must-be-YYYY-MM-DD");
  if (typeof input.symbol !== "string" || !input.symbol || typeof input.source !== "string" || !input.source ||
    typeof input.sourceFetchedAt !== "string" || !Number.isFinite(Date.parse(input.sourceFetchedAt)) || typeof input.sourceTimezone !== "string" || !input.sourceTimezone) {
    throw new TypeError("invalid-chart-provenance");
  }
  const bars = validateChartExplorerBars(input.candles, input.requestedAsOf, input.sourceTimezone);
  if (!bars.length) throw new TypeError("no-chart-bars");

  const internal: PriorityIndicatorInput = {
    code: input.symbol,
    symbol: input.symbol,
    market: "unknown",
    requestedAsOf: input.requestedAsOf,
    candles: bars,
    source: input.source,
    sourceFetchedAt: input.sourceFetchedAt,
    barStatus: "unknown",
    confirmedPolicy: "Provider does not identify candle finality; status is not inferred.",
  };
  const calculated = buildSnapshot(internal, bars, input.timeframe);
  const fullChart = chartData(bars).bars as ChartExplorerChartBar[];
  const chartBars = fullChart.slice(-380);
  const snapshot = {
    barAsOf: bars.at(-1)?.time ?? null,
    timeframe: input.timeframe,
    price: calculated.price,
    indicators: calculated.indicators,
    structures: Array.isArray(calculated.structures) ? calculated.structures : [],
    structureStatus: calculated.structureStatus,
  } as ChartExplorerSnapshot;
  return {
    snapshot,
    chart: { bars: chartBars },
  };
}

function chartData(bars: ReadonlyArray<Bar>): { bars: ValueRecord[] } {
  const closes = bars.map((row) => row.close);
  const moving = Object.fromEntries(PERIODS.map((period) => [`sma${period}`, sma(closes, period)])) as Record<string, NullableSeries>;
  const rsi = rsiSeries(closes);
  const atr = atrSeries(bars);
  const fast = ema(closes, 12);
  const slow = ema(closes, 26);
  const macd = closes.map((_, index) => fast[index] !== null && slow[index] !== null ? (fast[index] as number) - (slow[index] as number) : Number.NaN);
  const signal = ema(macd, 9);
  const obv: number[] = [];
  for (let index = 0; index < bars.length; index += 1) {
    const direction = index ? closes[index] > closes[index - 1] ? 1 : closes[index] < closes[index - 1] ? -1 : 0 : 0;
    obv.push((obv.at(-1) ?? 0) + direction * bars[index].volume);
  }
  const start = Math.max(0, bars.length - 380);
  return { bars: bars.slice(start).map((bar, offset) => {
    const index = start + offset;
    const macdValue = Number.isFinite(macd[index]) ? macd[index] : null;
    const signalValue = signal[index] !== null && Number.isFinite(signal[index] as number) ? signal[index] : null;
    return {
      ...bar,
      ...Object.fromEntries(Object.entries(moving).map(([name, series]) => [name, series[index]])),
      rsi14: rsi[index],
      macd: macdValue,
      macdSignal: signalValue,
      macdHistogram: macdValue !== null && signalValue !== null ? macdValue - signalValue : null,
      obv: obv[index],
      atr14: atr[index],
    };
  }) };
}

function referenceConditions(bars: ReadonlyArray<Bar>): ValueRecord {
  if (!bars.length) return { price_condition_state: "insufficient_data", reference_bar_date: null, reference_close: null, prior_20_bar_high: null, prior_10_bar_low: null };
  const prior = bars.slice(0, -1);
  const prior20 = prior.length >= 20 ? Math.max(...prior.slice(-20).map((row) => row.high)) : null;
  const prior10 = prior.length >= 10 ? Math.min(...prior.slice(-10).map((row) => row.low)) : null;
  const close = bars.at(-1)!.close;
  const state = prior20 === null || prior10 === null ? "insufficient_data" : close > prior20 ? "above_prior_20_bar_high" : close < prior10 ? "below_prior_10_bar_low" : "within_reference_band";
  return { price_condition_state: state, reference_bar_date: bars.at(-1)!.time, reference_close: close, prior_20_bar_high: prior20, prior_10_bar_low: prior10 };
}

function section(value: unknown): ValueRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ValueRecord : {};
}

function indicatorConfirmation(snapshot: ValueRecord): ValueRecord {
  const price = section(snapshot.price);
  const indicators = section(snapshot.indicators);
  const close = number(price.close);
  const rsi = number(section(indicators.rsi14).value);
  const rsiState = rsi === null || rsi < 0 || rsi > 100 ? "insufficient_data" : rsi > 50 ? "up" : rsi < 50 ? "down" : "neutral";
  const macd = section(indicators.macd129);
  const macdValue = number(macd.macd);
  const macdSignal = number(macd.signal);
  const macdState = macdValue === null || macdSignal === null ? "insufficient_data" : macdValue > macdSignal ? "up" : macdValue < macdSignal ? "down" : "neutral";
  const moving = section(indicators.movingAverages);
  const movingStates: Record<string, string> = {};
  for (const kind of ["sma", "ema", "wma"]) {
    const averages = PERIODS.map((period) => number(moving[`${kind}${period}`]));
    if (close === null || close <= 0 || averages.some((value) => value === null || value <= 0)) movingStates[kind] = "insufficient_data";
    else {
      const stack = [close, ...averages as number[]];
      movingStates[kind] = stack.every((value, index) => index === stack.length - 1 || value > stack[index + 1]) ? "up" :
        stack.every((value, index) => index === stack.length - 1 || value < stack[index + 1]) ? "down" : "mixed";
    }
  }
  const movingAverageState = Object.values(movingStates).includes("insufficient_data") ? "insufficient_data" :
    Object.values(movingStates).every((value) => value === "up") ? "up" :
      Object.values(movingStates).every((value) => value === "down") ? "down" : "mixed";
  const bollingerMiddle = number(section(indicators.bollinger20).middle);
  const bollingerState = close === null || bollingerMiddle === null ? "insufficient_data" : close > bollingerMiddle ? "up" : close < bollingerMiddle ? "down" : "neutral";
  const donchianMiddle = number(section(indicators.donchian20).middle);
  const donchianState = close === null || donchianMiddle === null ? "insufficient_data" : close > donchianMiddle ? "up" : close < donchianMiddle ? "down" : "neutral";
  const obvDelta = number(section(indicators.obv).delta5);
  const obvState = obvDelta === null ? "insufficient_data" : obvDelta > 0 ? "up" : obvDelta < 0 ? "down" : "neutral";
  const directional = [rsiState, macdState, movingAverageState, bollingerState, donchianState, obvState];
  const alignment = directional.includes("insufficient_data") ? "insufficient_data" : directional.every((value) => value === "up") ? "up_aligned" : directional.every((value) => value === "down") ? "down_aligned" : "mixed";
  const volumeRatio = number(section(indicators.volume).ratio20);
  const volumeState = volumeRatio === null || volumeRatio < 0 ? "missing" : volumeRatio >= 1.2 ? "confirmed" : "below_threshold";
  let atr = number(section(indicators.atr14).value);
  if (atr !== null && atr < 0) atr = null;
  const atrPercent = atr !== null && close !== null && close > 0 ? atr / close * 100 : null;
  const bins = section(indicators.volumeProfile12).bins;
  const peakBins: Array<{ low: number; high: number }> = [];
  if (Array.isArray(bins)) for (const row of bins) {
    if (!row || typeof row !== "object" || (row as ValueRecord).peak !== true) continue;
    const low = number((row as ValueRecord).low);
    const high = number((row as ValueRecord).high);
    if (low !== null && high !== null && low <= high) peakBins.push({ low, high });
  }
  const profileState = close === null || !peakBins.length ? "insufficient_data" :
    peakBins.some(({ low, high }) => low <= close && close <= high) ? "within_peak_volume_bins" :
      close < Math.min(...peakBins.map(({ low }) => low)) ? "below_peak_volume_bins" :
        close > Math.max(...peakBins.map(({ high }) => high)) ? "above_peak_volume_bins" : "between_peak_volume_bins";
  return {
    directional_alignment_state: alignment, rsi_state: rsiState, macd_state: macdState, moving_average_state: movingAverageState,
    sma_state: movingStates.sma, ema_state: movingStates.ema, wma_state: movingStates.wma, bollinger_state: bollingerState,
    donchian_state: donchianState, obv_state: obvState, volume_confirmation_state: volumeState, volume_ratio20: volumeRatio,
    atr14_value: atr, atr14_percent_of_close: atrPercent, volume_profile_state: profileState, peak_volume_bins: peakBins,
  };
}

function conditionStatus(price: ValueRecord, confirmation: ValueRecord): string {
  const priceState = price.price_condition_state;
  const direction = confirmation.directional_alignment_state;
  const volume = confirmation.volume_confirmation_state;
  if (!["above_prior_20_bar_high", "below_prior_10_bar_low", "within_reference_band"].includes(String(priceState)) ||
      !["up_aligned", "down_aligned", "mixed"].includes(String(direction)) || !["confirmed", "below_threshold"].includes(String(volume))) return "판정 불가";
  if (priceState === "within_reference_band") return "두 가격 조건 미충족";
  if (priceState === "above_prior_20_bar_high" && direction === "up_aligned" && volume === "confirmed") return "진입 조건 충족";
  if (priceState === "below_prior_10_bar_low" && direction === "down_aligned" && volume === "confirmed") return "청산 조건 충족";
  return "가격 기준 도달 · 보조지표 확인 필요";
}

function conditionExplanation(price: ValueRecord, confirmation: ValueRecord): string {
  const result = conditionStatus(price, confirmation);
  const priceState = price.price_condition_state;
  const direction = confirmation.directional_alignment_state;
  const volumeState = confirmation.volume_confirmation_state;
  if (result === "판정 불가") {
    if (!["above_prior_20_bar_high", "below_prior_10_bar_low", "within_reference_band"].includes(String(priceState))) return "직전 20봉 고가와 10봉 저가를 계산할 자료가 부족합니다.";
    if (direction === "insufficient_data") return "필수 방향 보조지표 값이 부족해 조건을 확인할 수 없습니다.";
    if (volumeState === "missing") return "거래량 20일 비교값이 없어 조건을 확인할 수 없습니다.";
    return "조건 확인에 필요한 자료 상태를 판정할 수 없습니다.";
  }
  if (result === "두 가격 조건 미충족") return "현재 종가는 진입 기준을 넘지 않았고 탈출 기준을 하회하지 않았습니다.";
  if (result === "진입 조건 충족" || result === "청산 조건 충족") return "가격 기준, 방향 지표, 거래량 기준이 모두 일치합니다.";
  const expected = priceState === "above_prior_20_bar_high" ? "up" : "down";
  const blockers: string[] = [];
  const movingState = confirmation.moving_average_state;
  if (movingState === "mixed") blockers.push("SMA·EMA·WMA 이동평균 배열이 혼합");
  else if (movingState !== expected) blockers.push("이동평균 배열이 가격 기준과 다른 방향");
  for (const [key, label] of [["rsi_state", "RSI"], ["macd_state", "MACD"], ["bollinger_state", "볼린저"], ["donchian_state", "돈치안"], ["obv_state", "OBV"]]) {
    const component = confirmation[key];
    if (component === expected) continue;
    if (component === "neutral") blockers.push(`${label} 중립`);
    else if (component === "mixed") blockers.push(`${label} 방향 혼합`);
    else if (component === "insufficient_data") blockers.push(`${label} 자료 부족`);
    else blockers.push(`${label} 방향이 가격 기준과 다른 방향`);
  }
  if (volumeState === "below_threshold") {
    const ratio = number(confirmation.volume_ratio20);
    blockers.push(`거래량 ${ratio !== null ? `${ratio.toFixed(2)}배 ` : ""}(1.2배 기준 미달)`);
  }
  const reason = blockers.join(" · ") || "방향 지표가 한 방향으로 모이지 않음";
  return `${expected === "up" ? "진입" : "탈출"} 가격 조건은 도달했지만, 확인 항목은 ${reason}입니다.`;
}

export function buildPriorityIndicatorProjection(input: PriorityIndicatorInput): PriorityIndicatorProjection {
  const { requestedAsOf, code, market, symbol, source, candles } = input;
  if (!dateIsValid(requestedAsOf)) throw new TypeError("requested-as-of-must-be-YYYY-MM-DD");
  if (typeof code !== "string" || !/^[0-9]{6}$/.test(code)) throw new TypeError("code-must-be-six-digits");
  if (!["KOSPI", "KOSDAQ", "unknown"].includes(market)) throw new TypeError("market-must-be-KOSPI-KOSDAQ-or-unknown");
  const expectedSymbol = market === "KOSPI" ? `${code}.KS` : market === "KOSDAQ" ? `${code}.KQ` : code;
  if (symbol !== expectedSymbol) throw new TypeError("symbol-does-not-match-market");
  if (typeof source !== "string" || !source) throw new TypeError("source-required");
  if (typeof (input.confirmedPolicy ?? "unknown") !== "string") throw new TypeError("invalid-confirmed-policy");
  for (const [value, field] of [[input.sourceFetchedAt, "source-fetched-at"], [input.sourceDate ?? null, "source-date"], [input.lastSuccessAt ?? null, "last-success-at"], [input.sourceCalculationVersion ?? null, "source-calculation-version"]] as const) {
    if (value !== null && typeof value !== "string") throw new TypeError(`invalid-${field}`);
  }
  const barStatus = input.barStatus ?? "unknown";
  if (!["confirmed", "provisional", "unknown"].includes(barStatus)) throw new TypeError("invalid-bar-status");
  for (const [value, field] of [[input.cacheHit ?? null, "cache-hit"], [input.stale ?? null, "stale"]] as const) {
    if (value !== null && typeof value !== "boolean") throw new TypeError(`invalid-${field}`);
  }
  const cacheAge = input.cacheAge ?? null;
  if (cacheAge !== null && (number(cacheAge) === null || cacheAge < 0)) throw new TypeError("invalid-cache-age");
  const bars = validateBars(candles, requestedAsOf);
  const snapshot = buildSnapshot({ ...input, barStatus }, bars);
  const price = referenceConditions(bars);
  const confirmation = indicatorConfirmation(snapshot);
  return {
    snapshot,
    chart: chartData(bars),
    price_conditions: price,
    indicator_confirmation: confirmation,
    condition_status: conditionStatus(price, confirmation),
    condition_explanation: conditionExplanation(price, confirmation),
  };
}
