import type { ChartExplorerBar, ChartExplorerTimeframe } from "../chart-explorer.ts";

// Pattern thresholds are adapted from Stock-Newbby (Apache-2.0): https://github.com/gmparkingplace/Stock-Newbby
// This TypeScript implementation is a separate, bounded snapshot engine; it does not copy its cache or monitor service.
export type ChartLabPatternKind =
  | "bull-flag" | "bear-flag"
  | "ascending-triangle" | "descending-triangle" | "symmetrical-triangle"
  | "support-breakout" | "resistance-breakout" | "diagnostic";
export type ChartLabPatternStatus =
  | "forming" | "observed-breakout" | "observed-crossing"
  | "unsupported-timeframe" | "insufficient-data" | "data-gap" | "invalid-data";
export type ChartLabPatternFamily = "flag" | "triangle" | "horizontal" | "all";
type PatternTimeframe = "1d" | "4h";
export type ChartLabPoint = Readonly<{ time: string; index: number; price: number }>;
export type ChartLabPattern = Readonly<{
  kind: ChartLabPatternKind;
  family: ChartLabPatternFamily;
  status: ChartLabPatternStatus;
  direction: "up" | "down" | "neutral" | null;
  ruleVersion: string;
  dataStatus: "complete" | "gap-split" | "unsupported" | "insufficient" | "invalid";
  basis: Readonly<{ startIndex: number | null; endIndex: number | null; startTime: string | null; endTime: string | null }>;
  measurements: Readonly<Record<string, number | string | boolean | null>>;
  geometry: Readonly<{
    upper?: Readonly<{ start: ChartLabPoint; end: ChartLabPoint }>;
    lower?: Readonly<{ start: ChartLabPoint; end: ChartLabPoint }>;
    boundary?: Readonly<{ start: ChartLabPoint; end: ChartLabPoint }>;
    pole?: readonly ChartLabPoint[];
    points?: readonly ChartLabPoint[];
  }>;
}>;

type Point = { index: number; price: number };
type Line = { slope: number; intercept: number };
type Segment = { start: number; end: number; afterGap: boolean };
type PivotSets = { highs: Point[]; lows: Point[] };
type Candidate = {
  kind: "bull-flag" | "bear-flag" | "ascending-triangle" | "descending-triangle" | "symmetrical-triangle";
  family: "flag" | "triangle";
  direction: "up" | "down" | "neutral";
  start: number;
  end: number;
  startTime: string;
  endTime: string;
  ruleVersion: string;
  measurements: Record<string, number | string | boolean | null>;
  upper: Line;
  lower: Line;
  pole?: readonly [Point, Point];
  dataStatus: "complete" | "gap-split";
};

const MAX_BARS = 240;
const FLAG_MAX_ADJUSTMENT = 30;
const TRIANGLE_MAX_BARS = 60;
const RULES: Record<Exclude<ChartLabPatternFamily, "all">, Record<PatternTimeframe, string>> = {
  flag: { "1d": "flag-d-v2", "4h": "flag-h4-v3" },
  triangle: { "1d": "triangle-d-v2", "4h": "triangle-h4-v3" },
  horizontal: { "1d": "horizontal-d-v1", "4h": "horizontal-h4-v1" },
} as const;

function freezeDeep<T>(value: T): T {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const child of Object.values(value as Record<string, unknown>)) freezeDeep(child);
    Object.freeze(value);
  }
  return value;
}

function barIsValid(bar: ChartExplorerBar): boolean {
  const values = [bar.open, bar.high, bar.low, bar.close, bar.volume];
  return typeof bar.time === "string" && Number.isFinite(Date.parse(bar.time)) &&
    values.every((value) => typeof value === "number" && Number.isFinite(value)) &&
    Math.min(bar.open, bar.high, bar.low, bar.close) > 0 && bar.volume >= 0 &&
    bar.high >= Math.max(bar.open, bar.low, bar.close) && bar.low <= Math.min(bar.open, bar.high, bar.close);
}

function gapLimitMs(timeframe: ChartExplorerTimeframe): number {
  return ({ "1d": 10, "1w": 35, "4h": 8, "1mo": 93 }[timeframe]) * 86_400_000;
}

function segments(bars: readonly ChartExplorerBar[], offset: number, timeframe: ChartExplorerTimeframe): { segments: Segment[]; gaps: [number, number][] } {
  const groups: Segment[] = [];
  const gaps: [number, number][] = [];
  let start = 0;
  let afterGap = false;
  for (let index = 1; index < bars.length; index += 1) {
    if (Date.parse(bars[index].time) - Date.parse(bars[index - 1].time) > gapLimitMs(timeframe)) {
      groups.push({ start, end: index - 1, afterGap });
      gaps.push([offset + index - 1, offset + index]);
      start = index;
      afterGap = true;
    }
  }
  if (bars.length) groups.push({ start, end: bars.length - 1, afterGap });
  return { segments: groups, gaps };
}

function atrSeries(bars: readonly ChartExplorerBar[]): (number | null)[] {
  const values: (number | null)[] = [];
  let sum = 0;
  for (let index = 0; index < bars.length; index += 1) {
    const previousClose = bars[index - 1]?.close ?? bars[index].close;
    const range = Math.max(bars[index].high - bars[index].low, Math.abs(bars[index].high - previousClose), Math.abs(bars[index].low - previousClose));
    sum += range;
    values.push(index < 13 ? null : index === 13 ? sum / 14 : ((values[index - 1] as number) * 13 + range) / 14);
  }
  return values;
}

function fit(points: readonly Point[]): Line | null {
  if (points.length < 2) return null;
  const meanX = points.reduce((sum, point) => sum + point.index, 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point.price, 0) / points.length;
  const denominator = points.reduce((sum, point) => sum + (point.index - meanX) ** 2, 0);
  if (!denominator) return null;
  const slope = points.reduce((sum, point) => sum + (point.index - meanX) * (point.price - meanY), 0) / denominator;
  return { slope, intercept: meanY - slope * meanX };
}

function lineAt(line: Line, index: number): number { return line.intercept + line.slope * index; }

function pivots(bars: readonly ChartExplorerBar[], through: number): PivotSets {
  const highs: Point[] = [];
  const lows: Point[] = [];
  for (let index = 2; index < through - 1; index += 1) {
    const current = bars[index];
    if (current.high >= bars[index - 2].high && current.high >= bars[index - 1].high &&
      current.high > bars[index + 1].high && current.high > bars[index + 2].high) highs.push({ index, price: current.high });
    if (current.low <= bars[index - 2].low && current.low <= bars[index - 1].low &&
      current.low < bars[index + 1].low && current.low < bars[index + 2].low) lows.push({ index, price: current.low });
  }
  return { highs, lows };
}

function channelCoverage(bars: readonly ChartExplorerBar[], start: number, end: number, upper: Line, lower: Line, tolerance: number): { ratio: number; longestOutside: number } {
  let inside = 0;
  let run = 0;
  let longestOutside = 0;
  for (let index = start; index <= end; index += 1) {
    const contained = bars[index].high <= lineAt(upper, index) + tolerance && bars[index].low >= lineAt(lower, index) - tolerance;
    if (contained) { inside += 1; run = 0; }
    else { run += 1; longestOutside = Math.max(longestOutside, run); }
  }
  return { ratio: inside / (end - start + 1), longestOutside };
}

function point(bars: readonly ChartExplorerBar[], index: number, price: number, offset: number): ChartLabPoint {
  return { index: offset + index, time: bars[index].time, price };
}

function flagCandidate(
  bars: readonly ChartExplorerBar[], atr: readonly (number | null)[], pivotsAtEnd: PivotSets,
  start: number, end: number, timeframe: PatternTimeframe, afterGap: boolean,
): Candidate | null {
  const choices: { move: number; length: number; pole: number; delta: number }[] = [];
  for (let length = 3; length <= 10; length += 1) {
    const pole = start - length;
    const poleAtr = atr[pole - 1];
    if (pole >= 14 && poleAtr && Math.abs(bars[start - 1].close - bars[pole].close) >= 2.5 * poleAtr) {
      const delta = bars[start - 1].close - bars[pole].close;
      choices.push({ move: Math.abs(delta), length, pole, delta });
    }
  }
  choices.sort((a, b) => b.move - a.move || a.length - b.length);
  const pole = choices[0];
  if (!pole) return null;
  const direction = pole.delta > 0 ? "up" : "down";
  const sign = direction === "up" ? 1 : -1;
  const adjustmentAtr = atr[start - 1];
  if (!adjustmentAtr || sign * (bars[start].close - bars[start - 1].close) > 0.5 * adjustmentAtr) return null;
  const highs = pivotsAtEnd.highs.filter((item) => item.index >= start && item.index <= end - 2);
  const lows = pivotsAtEnd.lows.filter((item) => item.index >= start && item.index <= end - 2);
  if (highs.length < 2 || lows.length < 2) return null;
  const atrNow = atr[end - 1];
  const upper = fit(highs);
  const lower = fit(lows);
  if (!atrNow || !upper || !lower || [upper, lower].some((model) => sign * model.slope > 0.03 * atrNow) ||
    Math.abs(upper.slope - lower.slope) > 0.12 * atrNow ||
    [...highs.map((item) => [item, upper] as const), ...lows.map((item) => [item, lower] as const)]
      .some(([item, model]) => Math.abs(item.price - lineAt(model, item.index)) > 0.4 * atrNow)) return null;
  for (let index = start; index <= end; index += 1) if (lineAt(upper, index) <= lineAt(lower, index)) return null;
  const coverage = channelCoverage(bars, start, end, upper, lower, 0.4 * atrNow);
  if (coverage.ratio < 0.7 || coverage.longestOutside > 2) return null;
  const extreme = direction === "up"
    ? Math.min(...bars.slice(start, end + 1).map((bar) => bar.low))
    : Math.max(...bars.slice(start, end + 1).map((bar) => bar.high));
  const retracement = Math.max(0, (direction === "up" ? bars[start - 1].close - extreme : extreme - bars[start - 1].close) / pole.move);
  if (retracement > 0.618) return null;
  const poleStart = { index: pole.pole, price: bars[pole.pole].close };
  const poleEnd = { index: start - 1, price: bars[start - 1].close };
  return {
    kind: direction === "up" ? "bull-flag" : "bear-flag", family: "flag", direction,
    start, end, startTime: bars[start].time, endTime: bars[end].time,
    ruleVersion: RULES.flag[timeframe], upper, lower, pole: [poleStart, poleEnd],
    dataStatus: afterGap ? "gap-split" : "complete",
    measurements: {
      poleMove: pole.move, poleAtr: atr[pole.pole - 1] as number,
      poleAtrMultiple: pole.move / (atr[pole.pole - 1] as number),
      atr14Previous: atrNow, adjustmentBars: end - start + 1,
      adjustmentVolumeRatio: averageVolume(bars, start, end) / averageVolume(bars, pole.pole, start - 1),
      rvol20Previous: relativeVolume(bars, end),
      volumeEvidence: (relativeVolume(bars, end) ?? 0) >= 1.2 ? "volume-confirmed" : "volume-insufficient",
      retracementRatio: retracement, channelContainment: coverage.ratio,
      upperSlope: upper.slope, lowerSlope: lower.slope, confirmedPivotHighs: highs.length, confirmedPivotLows: lows.length,
    },
  };
}

function averageVolume(bars: readonly ChartExplorerBar[], start: number, end: number): number {
  if (start > end) return 0;
  return bars.slice(start, end + 1).reduce((sum, bar) => sum + bar.volume, 0) / (end - start + 1);
}

function relativeVolume(bars: readonly ChartExplorerBar[], index: number): number | null {
  if (index < 20) return null;
  const mean = averageVolume(bars, index - 20, index - 1);
  return mean > 0 ? bars[index].volume / mean : null;
}

function triangleCandidate(
  bars: readonly ChartExplorerBar[], atr: readonly (number | null)[], pivotsAtEnd: PivotSets,
  end: number, pivotStart: number, timeframe: PatternTimeframe, afterGap: boolean,
): Candidate | null {
  const highPivots = pivotsAtEnd.highs.filter((item) => item.index >= pivotStart && item.index <= end - 2);
  const lowPivots = pivotsAtEnd.lows.filter((item) => item.index >= pivotStart && item.index <= end - 2);
  if (highPivots.length < 2 || lowPivots.length < 2 || highPivots.length + lowPivots.length < 5) return null;
  const start = Math.min(highPivots[0].index, lowPivots[0].index);
  if (end - start + 1 < 8 || end - start + 1 > TRIANGLE_MAX_BARS) return null;
  const atrNow = atr[end - 1];
  const upper = fit(highPivots);
  const lower = fit(lowPivots);
  if (!atrNow || !upper || !lower) return null;
  const flatSlope = 0.03 * atrNow;
  const trendSlope = 0.02 * atrNow;
  let kind: Candidate["kind"];
  if (upper.slope <= -trendSlope && lower.slope >= trendSlope) kind = "symmetrical-triangle";
  else if (Math.abs(upper.slope) <= flatSlope && lower.slope >= trendSlope) kind = "ascending-triangle";
  else if (upper.slope <= -trendSlope && Math.abs(lower.slope) <= flatSlope) kind = "descending-triangle";
  else return null;
  if ([...highPivots.map((item) => [item, upper] as const), ...lowPivots.map((item) => [item, lower] as const)]
    .some(([item, model]) => Math.abs(item.price - lineAt(model, item.index)) > 0.4 * atrNow)) return null;
  const initialWidth = lineAt(upper, start) - lineAt(lower, start);
  const currentWidth = lineAt(upper, end) - lineAt(lower, end);
  if (initialWidth <= 0 || currentWidth <= 0 || currentWidth / initialWidth > 0.75) return null;
  const apex = (lower.intercept - upper.intercept) / (upper.slope - lower.slope);
  if (apex <= end) return null;
  const coverage = channelCoverage(bars, start, end, upper, lower, 0.4 * atrNow);
  if (coverage.ratio < 0.7 || coverage.longestOutside > 2) return null;
  return {
    kind, family: "triangle", direction: "neutral", start, end, startTime: bars[start].time, endTime: bars[end].time,
    ruleVersion: RULES.triangle[timeframe], upper, lower, dataStatus: afterGap ? "gap-split" : "complete",
    measurements: {
      atr14Previous: atrNow,
      structureBars: end - start + 1, contactCount: highPivots.length + lowPivots.length,
      convergenceRatio: currentWidth / initialWidth, channelContainment: coverage.ratio,
      rvol20Previous: relativeVolume(bars, end),
      volumeEvidence: (relativeVolume(bars, end) ?? 0) >= 1.2 ? "volume-confirmed" : "volume-insufficient",
      upperSlope: upper.slope, lowerSlope: lower.slope,
    },
  };
}

function horizontalPatterns(
  bars: readonly ChartExplorerBar[], atr: readonly (number | null)[], segment: Segment, offset: number,
  timeframe: PatternTimeframe, patterns: ChartLabPattern[],
): void {
  for (let index = segment.start + 21; index <= segment.end; index += 1) {
    const previousAtr = atr[index - 1];
    if (!previousAtr) continue;
    const previous = bars[index - 1];
    const current = bars[index];
    const priorHighs = bars.slice(index - 20, index).map((bar) => bar.high);
    const priorLows = bars.slice(index - 10, index).map((bar) => bar.low);
    const upperBoundary = Math.max(...priorHighs);
    const lowerBoundary = Math.min(...priorLows);
    const oldHighBoundary = Math.max(...bars.slice(index - 21, index - 1).map((bar) => bar.high));
    const oldLowBoundary = Math.min(...bars.slice(index - 11, index - 1).map((bar) => bar.low));
    const upperTrigger = upperBoundary + 0.1 * previousAtr;
    const lowerTrigger = lowerBoundary - 0.1 * previousAtr;
    const oldUpperTrigger = oldHighBoundary + 0.1 * (atr[index - 2] ?? previousAtr);
    const oldLowerTrigger = oldLowBoundary - 0.1 * (atr[index - 2] ?? previousAtr);
    const crossedUp = current.close > upperTrigger && previous.close <= upperTrigger && previous.close <= oldUpperTrigger;
    const crossedDown = current.close < lowerTrigger && previous.close >= lowerTrigger && previous.close >= oldLowerTrigger;
    if (!crossedUp && !crossedDown) continue;
    const up = crossedUp;
    const boundary = up ? upperBoundary : lowerBoundary;
    const trigger = up ? upperTrigger : lowerTrigger;
    const start = index - (up ? 20 : 10);
    const boundaryIndex = up
      ? start + priorHighs.lastIndexOf(upperBoundary)
      : index - 10 + priorLows.lastIndexOf(lowerBoundary);
    patterns.push(snapshot({
      kind: up ? "resistance-breakout" : "support-breakout", family: "horizontal", status: "observed-crossing",
      direction: up ? "up" : "down", ruleVersion: RULES.horizontal[timeframe], dataStatus: segment.afterGap ? "gap-split" : "complete",
      basis: { startIndex: offset + start, endIndex: offset + index, startTime: bars[start].time, endTime: current.time },
      measurements: {
        boundary, triggerPrice: trigger, atr14Previous: previousAtr, lookbackBars: up ? 20 : 10,
        rvol20Previous: relativeVolume(bars, index),
        volumeEvidence: (relativeVolume(bars, index) ?? 0) >= 1.2 ? "volume-confirmed" : "volume-insufficient",
      },
      geometry: { boundary: { start: point(bars, start, boundary, offset), end: point(bars, index, boundary, offset) },
        points: [point(bars, boundaryIndex, boundary, offset)] },
    }));
  }
}

function snapshot(value: Omit<ChartLabPattern, "basis"> & { basis: ChartLabPattern["basis"] }): ChartLabPattern {
  return freezeDeep(value);
}

function lineGeometry(bars: readonly ChartExplorerBar[], candidate: Candidate, offset: number) {
  return {
    upper: {
      start: point(bars, candidate.start, lineAt(candidate.upper, candidate.start), offset),
      end: point(bars, candidate.end, lineAt(candidate.upper, candidate.end), offset),
    },
    lower: {
      start: point(bars, candidate.start, lineAt(candidate.lower, candidate.start), offset),
      end: point(bars, candidate.end, lineAt(candidate.lower, candidate.end), offset),
    },
  };
}

function asPattern(candidate: Candidate, status: "forming" | "observed-breakout", direction: "up" | "down" | "neutral", bars: readonly ChartExplorerBar[], offset: number, end: number): ChartLabPattern {
  const sign = direction === "up" ? 1 : direction === "down" ? -1 : 0;
  const atr = candidate.measurements.atr14Previous as number | undefined;
  const upper = lineAt(candidate.upper, end);
  const lower = lineAt(candidate.lower, end);
  const triggerPrice = sign > 0 ? upper + 0.1 * (atr ?? 0) : sign < 0 ? lower - 0.1 * (atr ?? 0) : null;
  return snapshot({
    kind: candidate.kind, family: candidate.family, status, direction, ruleVersion: candidate.ruleVersion,
    dataStatus: candidate.dataStatus,
    basis: { startIndex: offset + candidate.start, endIndex: offset + end, startTime: candidate.startTime, endTime: bars[end].time },
    measurements: { ...candidate.measurements, upperBoundary: upper, lowerBoundary: lower, triggerPrice },
    geometry: {
      ...lineGeometry(bars, { ...candidate, end }, offset),
      ...(candidate.pole ? { pole: [point(bars, candidate.pole[0].index, candidate.pole[0].price, offset), point(bars, candidate.pole[1].index, candidate.pole[1].price, offset)] } : {}),
    },
  });
}

function diagnostic(family: ChartLabPatternFamily, status: ChartLabPatternStatus, reason: string, ruleVersion: string,
  dataStatus: ChartLabPattern["dataStatus"], startIndex: number | null, endIndex: number | null,
  startTime: string | null, endTime: string | null): ChartLabPattern {
  return snapshot({ kind: "diagnostic", family, status, direction: null, ruleVersion, dataStatus,
    basis: { startIndex, endIndex, startTime, endTime }, measurements: { reason }, geometry: {} });
}

/** Detect recent causal pattern snapshots. Latest-bar status remains observational without a source finality cutoff. */
export function detectChartLabPatterns(bars: readonly ChartExplorerBar[], timeframe: ChartExplorerTimeframe): ChartLabPattern[] {
  const result: ChartLabPattern[] = [];
  if (timeframe !== "1d" && timeframe !== "4h") {
    result.push(diagnostic("all", "unsupported-timeframe", "Stock-Newbby pattern rules cover daily and 4-hour bars.",
      "patterns-unsupported-v1", "unsupported", null, null, null, null));
    return freezeDeep(result);
  }
  if (bars.some((bar, index) => !barIsValid(bar) || (index > 0 && Date.parse(bar.time) <= Date.parse(bars[index - 1].time)))) {
    result.push(diagnostic("all", "invalid-data", "Bars must have valid OHLCV values and strictly increasing times.",
      "patterns-input-v1", "invalid", null, null, null, null));
    return freezeDeep(result);
  }
  if (!bars.length) {
    result.push(diagnostic("all", "insufficient-data", "No bars were supplied.", "patterns-input-v1", "insufficient", null, null, null, null));
    return freezeDeep(result);
  }

  const offset = Math.max(0, bars.length - MAX_BARS);
  const recent = bars.slice(offset);
  const split = segments(recent, offset, timeframe);
  const required = { flag: 30, triangle: 30, horizontal: 21 } as const;
  if (split.gaps.length) {
    for (const [before, after] of split.gaps) {
      result.push(diagnostic("all", "data-gap", "Large time gap split the input; no pattern crosses it.", "patterns-data-v1", "gap-split",
        before, after, bars[before].time, bars[after].time));
    }
  }

  const longestSegment = split.segments.reduce<Segment | null>((best, part) =>
    !best || part.end - part.start > best.end - best.start ? part : best, null);
  const longest = longestSegment ? longestSegment.end - longestSegment.start + 1 : 0;
  for (const family of ["flag", "triangle", "horizontal"] as const) {
    if (longest < required[family]) result.push(diagnostic(family, "insufficient-data", `Requires at least ${required[family]} contiguous bars.`,
      RULES[family][timeframe], "insufficient", longestSegment ? offset + longestSegment.start : null, bars.length - 1,
      longestSegment ? recent[longestSegment.start].time : null, bars.at(-1)?.time ?? null));
  }

  const latestByStructure = new Map<string, ChartLabPattern>();
  for (const segment of split.segments) {
    const rows = recent.slice(segment.start, segment.end + 1);
    const segmentOffset = offset + segment.start;
    const atr = atrSeries(rows);
    if (rows.length >= required.horizontal) horizontalPatterns(rows, atr, { start: 0, end: rows.length - 1, afterGap: segment.afterGap }, segmentOffset, timeframe, result);
    if (rows.length < required.flag) continue;
    const earliest = Math.max(0, rows.length - FLAG_MAX_ADJUSTMENT - 12);
    for (let end = earliest; end < rows.length; end += 1) {
      const pivotsAtEnd = pivots(rows, end);
      const startFrom = Math.max(17, end - FLAG_MAX_ADJUSTMENT + 1);
      for (let start = startFrom; start < end - 3; start += 1) {
        const candidate = flagCandidate(rows, atr, pivotsAtEnd, start, end, timeframe, segment.afterGap);
        if (!candidate) continue;
        const sign = candidate.direction === "up" ? 1 : -1;
        const currentAtr = candidate.measurements.atr14Previous as number;
        const boundary = lineAt(candidate.direction === "up" ? candidate.upper : candidate.lower, end);
        const trigger = boundary + sign * 0.1 * currentAtr;
        const breakout = sign * (rows[end].close - trigger) > 0;
        const found = asPattern(candidate, breakout ? "observed-breakout" : "forming", candidate.direction, rows, segmentOffset, end);
        latestByStructure.set(`${candidate.kind}:${candidate.startTime}`, found);
        break;
      }
    }
    if (rows.length < required.triangle) continue;
    const triangleStart = Math.max(14, rows.length - TRIANGLE_MAX_BARS - 2);
    for (let end = triangleStart; end < rows.length; end += 1) {
      const endPivots = pivots(rows, end);
      let candidate: Candidate | null = null;
      for (let start = Math.max(14, end - TRIANGLE_MAX_BARS + 1); start <= end - 7; start += 1) {
        candidate = triangleCandidate(rows, atr, endPivots, end, start, timeframe, segment.afterGap);
        if (candidate) break;
      }
      if (!candidate) continue;
      const currentUpper = lineAt(candidate.upper, end);
      const currentLower = lineAt(candidate.lower, end);
      const triggerAtr = candidate.measurements.atr14Previous as number;
      const up = rows[end].close > currentUpper + 0.1 * triggerAtr;
      const down = rows[end].close < currentLower - 0.1 * triggerAtr;
      const found = asPattern(candidate, up || down ? "observed-breakout" : "forming", up ? "up" : down ? "down" : "neutral",
        rows, segmentOffset, end);
      latestByStructure.set(`${candidate.kind}:${candidate.startTime}`, found);
    }
  }
  result.push(...latestByStructure.values());
  return freezeDeep(result);
}
