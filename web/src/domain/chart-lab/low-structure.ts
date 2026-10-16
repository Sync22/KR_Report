import type { ChartExplorerBar, ChartExplorerTimeframe } from "../chart-explorer.ts";

// Adapted from https://github.com/gmparkingplace/Stock-Newbby (Apache-2.0):
// results/dashboard/low-structure-model.js and low-structure-rules.js.
export const LOW_STRUCTURE_VERSION = "low-entry-v1";
const H4_LOW_ANALYSIS_BARS = 120;

export type LowFamily = "R" | "H";
export type LowPhase = "breached" | "reclaimed" | "tested" | "rising" | "ready" | "invalidated" | "expired" | "superseded";
export type LowStructureParameters = {
  leftBars: number; rightBars: number; atrPeriod: 14; lookback: number; minSeparation: number; maxSeparation: number;
  minSwingAtr: number; zoneAtr: number; breachAtr: number; maxDepthAtr: number; reclaimBars: number; retestBars: number;
  higherLowAtr: number; testRiseAtr: number; testNearAtr: number; triggerAtr: number; triggerBars: number;
  reviewBars: number; stopAtr: number; maxAtr: number;
};
export type LowStructureOptions = {
  symbol?: string;
  timeframe?: ChartExplorerTimeframe;
  asOf?: string;
  confirmedThrough?: string | null;
  params?: Partial<LowStructureParameters>;
};
export type ChartLabLowEntryOptions = {
  symbol?: string;
  timeframe: ChartExplorerTimeframe;
  asOfIndex: number;
  confirmedThroughIndex?: number | null;
  judgmentReady?: boolean;
  judgmentMessage?: string;
  historical?: boolean;
  selected?: ReadonlyArray<LowFamily>;
  params?: Partial<LowStructureParameters>;
};
export type LowEntryReviewCode = "blocked" | "avoid" | "chase" | "candidate" | "wait" | "historical";
export type LowEntryReviewRow = {
  id: LowFamily; name: string; signal: "entry" | "exit" | "none"; phase: LowPhase | "wait";
  code: LowEntryReviewCode; label: string; rule: string; structure: LowStructure | null;
  description: { label: string; reason: string; rowLabel: string };
};
export type ChartLabLowEntryResult = Omit<LowStructureAnalysis, "reason"> & {
  analysisReason?: string;
  reviewStatus: "ready" | "unconfirmed" | "historical";
  selected: LowFamily[];
  rows: LowEntryReviewRow[];
  setupDecision: { code: LowEntryReviewCode; label: string; reason: string };
  code: LowEntryReviewCode; label: string; reason: string; setup: string; structureId: string | null;
  anchorTime: string | null; signalAge: number | null; chaseLimit: number | null; maxAtr: number;
  family: "low"; matched: boolean; referenceType: "signal-close"; combinationNote: string;
};
export type LowSeriesPoint = {
  time: string; segment: number | null; priceReady: boolean; volumeStatus: "missing" | "zero" | "known";
  confirmed: boolean; tr: number | null; atr: number | null; previewAtr: number | null;
};
export type LowPivot = {
  kind: "low" | "high"; price: number; occurredAt: string; knownAt: string; index: number;
  knownIndex: number; segment: number; atrBefore: number | null;
};
export type LowEvidence = {
  id: string; label: string; basisTime: string; knownAt: string; observed: number | null;
  reference: number | null; result: "unknown" | "supportive" | "warning"; detail: string;
};
export type LowStructure = {
  id: string; family: LowFamily; phase: LowPhase; reason: string; label: string;
  startedAt: string; knownAt: string; knownIndex: number; anchorTimes: string[]; anchorIndexes: number[];
  atrAnchor: number; signalAt: string | null; signalIndex: number | null; triggerLevel: number | null;
  invalidationLevel: number | null; chaseLimit: number | null; referencePrice: number | null;
  segment: number; supportPrice?: number; supportIndex?: number; supportKnownAt?: string;
  supportZone?: { lower: number; upper: number }; breachIndex?: number; breachTime?: string;
  springLow?: number; springIndex?: number; springTime?: string; recoveredIndex?: number; recoveredAt?: string;
  testIndex?: number; testTime?: string; testPrice?: number; testKnownAt?: string; testKnownIndex?: number;
  peakIndex?: number; peakPrice?: number; previousLow?: number; low1Index?: number;
  phaseAt: string; phaseIndex: number; endedAt?: string; endedIndex?: number; evidence: LowEvidence[];
};
export type LowStructureEvent = { id: string; structureId: string; family: LowFamily; phase: LowPhase; time: string; index: number; reason: string };
export type LowStructureAnalysis = {
  version: typeof LOW_STRUCTURE_VERSION; stage: "foundation" | "structures"; status: "invalid-data" | "unsupported" | "unavailable" | "unconfirmed" | "insufficient-data" | "ready";
  error: { code: string; index?: number; time?: string; field?: string } | null; reason?: string;
  symbol?: string; timeframe?: ChartExplorerTimeframe; parameters: LowStructureParameters | null;
  observedThrough: string | null; confirmedThrough: string | null; basis: string | null; confirmedIndex: number;
  provisional: boolean; dataWarnings: Array<{ code: string; index: number; time: string }>;
  series: LowSeriesPoint[]; pivots: LowPivot[]; structures: LowStructure[]; events: LowStructureEvent[];
  current: Record<LowFamily, LowStructure | null>; comparison: { knownAt: string; previousLow: number; latestLow: number; direction: "higher" | "lower" | "same" } | null;
  price: number | null;
};

export const LOW_STRUCTURE_DEFAULTS: Readonly<LowStructureParameters> = Object.freeze({
  leftBars: 2, rightBars: 2, atrPeriod: 14, lookback: 60, minSeparation: 3, maxSeparation: 30,
  minSwingAtr: 1, zoneAtr: 0.2, breachAtr: 0.1, maxDepthAtr: 1, reclaimBars: 3, retestBars: 8,
  higherLowAtr: 0.25, testRiseAtr: 0.1, testNearAtr: 0.5, triggerAtr: 0.1, triggerBars: 5,
  reviewBars: 3, stopAtr: 0.2, maxAtr: 0.5,
});
export const LOW_STRUCTURE_LABELS: Readonly<Record<LowPhase, string>> = Object.freeze({
  breached: "지지 이탈 · 회복 대기", reclaimed: "저점 회복 · 재시험 대기", tested: "지지 재확인 · 반등 대기",
  rising: "저점 상승 · 고점 돌파 대기", ready: "진입 검토", invalidated: "구조 실패 · 진입 보류",
  expired: "조건 만료", superseded: "새 구조로 전환",
});

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const absent = (value: unknown): value is null | undefined => value === null || value === undefined;
const terminal = (phase: LowPhase): boolean => ["invalidated", "expired", "superseded"].includes(phase);

function parameters(input?: Partial<LowStructureParameters>): LowStructureParameters | null {
  if (input && (typeof input !== "object" || Array.isArray(input) || Object.keys(input).some((key) => !Object.hasOwn(LOW_STRUCTURE_DEFAULTS, key)))) return null;
  const p = { ...LOW_STRUCTURE_DEFAULTS, ...input };
  for (const key of ["leftBars", "rightBars"] as const) {
    if (!Number.isInteger(p[key]) || p[key] < 1 || p[key] > 5) return null;
  }
  for (const key of ["lookback", "minSeparation", "maxSeparation", "reclaimBars", "retestBars", "triggerBars", "reviewBars"] as const) {
    if (!Number.isInteger(p[key]) || p[key] < 1 || p[key] > 300) return null;
  }
  for (const key of ["minSwingAtr", "zoneAtr", "breachAtr", "maxDepthAtr", "higherLowAtr", "testRiseAtr", "testNearAtr", "triggerAtr", "stopAtr", "maxAtr"] as const) {
    if (!finite(p[key]) || p[key] <= 0 || p[key] > 10) return null;
  }
  return p.minSeparation <= p.maxSeparation && p.maxSeparation <= p.lookback && p.breachAtr < p.maxDepthAtr ? p : null;
}

function invalidResult(code: string, details: { index?: number; time?: string; field?: string } = {}): LowStructureAnalysis {
  return {
    version: LOW_STRUCTURE_VERSION, stage: "foundation", status: "invalid-data", error: { code, ...details },
    parameters: null, observedThrough: null, confirmedThrough: null, basis: null, confirmedIndex: -1, provisional: true,
    dataWarnings: [], series: [], pivots: [], structures: [], events: [], current: { R: null, H: null }, comparison: null, price: null,
  };
}

function isDailyTime(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000-")) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function isIntradayTime(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
}

function validateBar(bar: ChartExplorerBar, index: number, previousTime: string | null, timeframe: ChartExplorerTimeframe): LowStructureAnalysis["error"] {
  if (!bar || typeof bar !== "object") return { code: "invalid-bar", index };
  if (typeof bar.time !== "string" || !(timeframe === "1d" ? isDailyTime(bar.time) : timeframe === "4h" && isIntradayTime(bar.time))) {
    return { code: "invalid-bar-time", index, time: String(bar.time) };
  }
  if (previousTime !== null && bar.time <= previousTime) return { code: "invalid-bar-order", index, time: bar.time };
  if (timeframe === "4h" && (!Number.isSafeInteger(bar.missingBarsBefore) || bar.missingBarsBefore! < 0)) {
    return { code: "session-continuity-required", index, time: bar.time };
  }
  for (const field of ["open", "high", "low", "close"] as const) {
    const value: unknown = bar[field];
    if (!absent(value) && (!finite(value) || value <= 0)) return { code: "invalid-price", index, time: bar.time, field };
  }
  if ((finite(bar.high) && finite(bar.low) && bar.high < bar.low) ||
    (["open", "close"] as const).some((key) => finite(bar[key]) && ((finite(bar.high) && bar[key] > bar.high) || (finite(bar.low) && bar[key] < bar.low)))) {
    return { code: "invalid-ohlc-range", index, time: bar.time };
  }
  const volume: unknown = bar.volume;
  if (!absent(volume) && (!finite(volume) || volume < 0)) return { code: "invalid-volume", index, time: bar.time };
  return null;
}

function analyzeFoundation(bars: readonly ChartExplorerBar[], input: LowStructureOptions, p: LowStructureParameters): LowStructureAnalysis {
  const timeframe = input.timeframe ?? "1d";
  const asOf = input.asOf ?? bars.at(-1)?.time ?? null;
  if (asOf === null || !(timeframe === "1d" ? isDailyTime(asOf) : timeframe === "4h" && isIntradayTime(asOf))) return invalidResult("invalid-observed-cutoff");
  const observedIndex = bars.findIndex((bar) => bar.time === asOf);
  if (observedIndex < 0) return invalidResult("observed-cutoff-not-found");
  const observedBars = bars.slice(0, observedIndex + 1);
  let previousTime: string | null = null;
  for (let index = 0; index < observedBars.length; index += 1) {
    const error = validateBar(observedBars[index], index, previousTime, timeframe);
    if (error) return { ...invalidResult(error.code, error), error };
    previousTime = observedBars[index].time;
  }
  const confirmedThrough = input.confirmedThrough ?? null;
  if (confirmedThrough !== null && !(timeframe === "1d" ? isDailyTime(confirmedThrough) : timeframe === "4h" && isIntradayTime(confirmedThrough))) return invalidResult("invalid-confirmed-cutoff");
  if (confirmedThrough !== null && confirmedThrough > asOf) return invalidResult("confirmation-after-observation");
  const confirmedIndex = confirmedThrough === null ? -1 : observedBars.findIndex((bar) => bar.time === confirmedThrough);
  if (confirmedThrough !== null && confirmedIndex < 0) return invalidResult("confirmed-cutoff-not-found");
  if (confirmedIndex > observedIndex) return invalidResult("confirmation-after-observation");

  const warnings: LowStructureAnalysis["dataWarnings"] = [];
  const series: LowSeriesPoint[] = [];
  let segment = -1;
  let needsSegment = true;
  let previousClose: number | null = null;
  let seed: number[] = [];
  let atr: number | null = null;
  for (let index = 0; index < observedBars.length; index += 1) {
    const bar = observedBars[index];
    const priceReady = [bar.open, bar.high, bar.low, bar.close].every(finite);
    const volumeStatus = absent(bar.volume) ? "missing" : bar.volume === 0 ? "zero" : "known";
    if (volumeStatus === "missing") warnings.push({ code: "volume-missing", index, time: bar.time });
    if (timeframe === "4h" && index > 0 && bar.missingBarsBefore! > 0) {
      warnings.push({ code: "bar-gap", index, time: bar.time });
      needsSegment = true; previousClose = null; seed = []; atr = null;
    }
    if (!priceReady) {
      warnings.push({ code: "price-missing", index, time: bar.time });
      needsSegment = true; previousClose = null; seed = []; atr = null;
      series.push({ time: bar.time, segment: null, priceReady: false, volumeStatus, confirmed: index <= confirmedIndex, tr: null, atr: null, previewAtr: null });
      continue;
    }
    if (needsSegment) { segment += 1; needsSegment = false; }
    const tr = previousClose === null ? bar.high - bar.low : Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
    if (atr === null) {
      seed.push(tr);
      if (seed.length === p.atrPeriod) {
        atr = seed.reduce((mean, value, position) => mean + (value - mean) / (position + 1), 0);
        seed = [];
      }
    } else atr += (tr - atr) / p.atrPeriod;
    previousClose = bar.close;
    series.push({ time: bar.time, segment, priceReady: true, volumeStatus, confirmed: index <= confirmedIndex,
      tr: index <= confirmedIndex ? tr : null, atr: index <= confirmedIndex ? atr : null, previewAtr: index > confirmedIndex ? atr : null });
  }

  const pivots: LowPivot[] = [];
  for (let index = p.leftBars; index + p.rightBars <= confirmedIndex; index += 1) {
    const center = series[index];
    if (!center.priceReady) continue;
    const start = index - p.leftBars;
    const finish = index + p.rightBars;
    if (series.slice(start, finish + 1).some((bar) => !bar.priceReady || bar.segment !== center.segment)) continue;
    for (const [kind, field, direction] of [["low", "low", -1], ["high", "high", 1]] as const) {
      const price = observedBars[index][field];
      const left = observedBars.slice(start, index).every((bar) => direction * price >= direction * bar[field]);
      const right = observedBars.slice(index + 1, finish + 1).every((bar) => direction * price > direction * bar[field]);
      if (left && right) pivots.push({ kind, price, occurredAt: center.time, knownAt: series[finish].time, index, knownIndex: finish,
        segment: center.segment!, atrBefore: series[index - 1]?.segment === center.segment ? series[index - 1].atr : null });
    }
  }
  const current = series[confirmedIndex];
  const ready = !!current?.priceReady && finite(current.atr) && current.atr > 0;
  const status: LowStructureAnalysis["status"] = confirmedIndex < 0 ? "unconfirmed" : ready ? "ready" : "insufficient-data";
  const reason = confirmedIndex < 0 ? "no-confirmed-bars" : !current.priceReady ? "price-gap" : current.atr === 0 ? "atr-zero" : ready ? undefined : "atr-warmup";
  return {
    version: LOW_STRUCTURE_VERSION, stage: "foundation", status, error: null, ...(reason ? { reason } : {}),
    symbol: input.symbol?.trim().toUpperCase() || "UNKNOWN", timeframe, parameters: p,
    observedThrough: asOf, confirmedThrough, basis: confirmedIndex < 0 ? null : series[confirmedIndex].time, confirmedIndex,
    provisional: confirmedIndex < observedIndex, dataWarnings: warnings, series, pivots, structures: [], events: [],
    current: { R: null, H: null }, comparison: null, price: finite(observedBars[confirmedIndex]?.close) ? observedBars[confirmedIndex].close : null,
  };
}

function buildEvidence(s: LowStructure, bars: readonly ChartExplorerBar[], series: readonly LowSeriesPoint[], index: number,
  pivots: readonly LowPivot[], p: LowStructureParameters): LowEvidence[] {
  const bar = bars[index];
  const atr = s.atrAnchor;
  const result: LowEvidence[] = [];
  const add = (id: string, label: string, observed: number | null, reference: number | null, supportive: boolean, detail: string) => result.push({
    id, label, basisTime: bar.time, knownAt: bar.time, observed: finite(observed) ? observed : null, reference: finite(reference) ? reference : null,
    result: !finite(observed) || !finite(reference) ? "unknown" : supportive ? "supportive" : "warning", detail,
  });
  const mean = (from: number, to: number): number | null => {
    if (from < 0 || from > to || to >= bars.length) return null;
    const rows = bars.slice(from, to + 1);
    if (!rows.length || rows.some((row) => !finite(row.volume))) return null;
    return rows.reduce((value, row, position) => value + (row.volume - value) / (position + 1), 0);
  };
  const priorVolume = mean(index - 20, index - 1);
  const relativeVolume = finite(priorVolume) && priorVolume > 0 && finite(bar.volume) ? bar.volume / priorVolume : null;
  add("relative-volume", "직전 20봉 대비 거래량", relativeVolume, 1, relativeVolume !== null && relativeVolume >= 1, "현재 봉을 평균에서 제외");
  const range = series[index].priceReady ? (bar.high - bar.low) / atr : null;
  const closePosition = series[index].priceReady && bar.high > bar.low ? (bar.close - bar.low) / (bar.high - bar.low) : null;
  add("range", "ATR 대비 봉 범위", range, 1, range !== null && range >= 1, "가격 변동 폭이며 방향 신호가 아님");
  add("close-position", "봉 안의 종가 위치", closePosition, 0.6, closePosition !== null && closePosition >= 0.6, "범위 0 또는 가격 누락은 미확인");
  const extension = finite(s.referencePrice) && finite(s.triggerLevel) ? (s.referencePrice - s.triggerLevel) / atr : null;
  add("initial-extension", "최초 돌파봉 상승 폭", extension, p.maxAtr, extension !== null && extension <= p.maxAtr, "첫 신호봉 급등은 별도 위험이며 현재 추격 상한 검사와 다름");
  const peaks = pivots.filter((pivot) => pivot.kind === "high" && pivot.segment === s.segment && pivot.knownIndex <= index);
  const upper = peaks.filter((pivot) => pivot.price >= bar.close).sort((a, b) => a.price - b.price)[0]?.price ?? null;
  const stalled = finite(relativeVolume) && finite(range) && finite(closePosition) && finite(upper)
    ? relativeVolume >= 1.5 && range < 0.75 && closePosition <= 0.4 && upper - bar.close <= atr : null;
  add("upward-stall", "저항 부근 상승 정체", stalled === null ? null : Number(stalled), 1, stalled === false, "고거래량·좁은 범위도 위치에 따라 다른 의미, 분산 확정 아님");
  let initial: number | null = null;
  let test: number | null = null;
  if (s.family === "R") {
    const stop = s.springIndex!;
    let peak = s.supportIndex! + 1;
    for (let cursor = peak + 1; cursor < stop; cursor += 1) if (bars[cursor].high > bars[peak].high) peak = cursor;
    initial = mean(peak, stop);
    if (s.testIndex != null) test = mean(s.peakIndex!, s.testIndex);
  } else {
    let peak = Math.max(0, s.low1Index! - 10);
    for (let cursor = peak + 1; cursor < s.low1Index!; cursor += 1) if (bars[cursor].high > bars[peak].high) peak = cursor;
    initial = mean(peak, s.low1Index!);
    test = mean(s.peakIndex!, s.testIndex!);
  }
  const testRatio = finite(initial) && initial > 0 && finite(test) ? test / initial : null;
  add("test-volume", "조정 파동의 평균 거래량", testRatio, 1, testRatio !== null && testRatio < 1, "파동 길이가 달라도 봉당 평균을 비교");
  const rebound = s.testIndex != null ? mean(s.testIndex + 1, index) : null;
  const reboundRatio = finite(test) && test > 0 && finite(rebound) ? rebound / test : null;
  add("rebound-volume", "반등 파동의 평균 거래량", reboundRatio, 1, reboundRatio !== null && reboundRatio >= 1, "낮은 거래량만으로 공급 약화를 확정하지 않음");
  const trough = s.family === "R" ? s.springLow! : s.previousLow!;
  const top = s.peakPrice;
  const progress = finite(top) && finite(trough) && top > trough && finite(bar.close) ? (bar.close - trough) / (top - trough) : null;
  add("rebound-progress", "직전 하락폭 대비 회복", progress, 1, progress !== null && progress >= 1, "보조 비율, 반등 고점 종가 돌파를 대신하지 않음");
  const reference = s.supportPrice ?? s.testPrice;
  const near = finite(reference) && bar.close >= reference && bar.close - reference <= atr;
  const absorption = finite(relativeVolume) && finite(range) && finite(closePosition) ? relativeVolume >= 1.5 && range < 0.75 && closePosition >= 0.6 && near : null;
  add("price-response", "지지 부근 하락 둔화", absorption === null ? null : Number(absorption), 1, absorption === true, "거래량 대비 가격 반응의 근사, 매집·흡수 확정 아님");
  let obv = 0;
  let obvValid = true;
  for (let cursor = s.anchorIndexes[0] + 1; cursor <= index; cursor += 1) {
    if (!finite(bars[cursor].volume) || !series[cursor].priceReady || !series[cursor - 1]?.priceReady || series[cursor].segment !== s.segment) { obvValid = false; break; }
    obv += Math.sign(bars[cursor].close - bars[cursor - 1].close) * bars[cursor].volume;
  }
  add("obv-change", "구조 시작 후 OBV 변화", obvValid ? obv : null, 0, obv >= 0, "누적값 차이, 실제 순매수 금액 아님");
  const resistance = peaks.filter((pivot) => pivot.price > Math.max(s.triggerLevel ?? Infinity, bar.close)).reduce((value, pivot) => Math.min(value, pivot.price), Infinity);
  const risk = finite(s.invalidationLevel) ? bar.close - s.invalidationLevel : null;
  const room = Number.isFinite(resistance) && finite(risk) && risk > 0 ? (resistance - bar.close) / risk : null;
  add("resistance-room", "알려진 저항까지 가격 여유", room, 1.5, room !== null && room >= 1.5, "목표 수익률 아님, 미확인이나 가까운 저항으로 자동 탈락시키지 않음");
  return result;
}

export function analyzeLowStructures(bars: ReadonlyArray<ChartExplorerBar>, input: LowStructureOptions = {}): LowStructureAnalysis {
  if (!Array.isArray(bars) || !input || typeof input !== "object" || Array.isArray(input)) return invalidResult("invalid-input");
  const timeframe = input.timeframe ?? "1d";
  if (timeframe !== "1d" && timeframe !== "4h") {
    const result = invalidResult("timeframe-not-supported");
    return { ...result, status: "unsupported", error: null,
      reason: "timeframe-not-supported", parameters: parameters(input.params) };
  }
  if (timeframe === "4h") {
    const asOf = input.asOf ?? bars.at(-1)?.time;
    const observedIndex = asOf ? bars.findIndex((bar) => bar.time === asOf) : -1;
    if (observedIndex >= 0 && bars.slice(0, observedIndex + 1).some((bar) => !Number.isSafeInteger(bar.missingBarsBefore) || bar.missingBarsBefore! < 0)) {
      const result = invalidResult("session-continuity-required");
      return { ...result, status: "unsupported", error: null, reason: "4h-session-continuity-required", parameters: parameters(input.params) };
    }
  }
  const p = parameters(input.params);
  if (!p) return invalidResult("invalid-parameters");
  if (!bars.length) return { ...invalidResult("no-candles"), status: "unavailable", error: null, reason: "no-candles", parameters: p };
  if (input.symbol !== undefined && (typeof input.symbol !== "string" || !input.symbol.trim() || input.symbol.length > 32)) return invalidResult("invalid-symbol");
  const foundation = analyzeFoundation(bars, input, p);
  if (foundation.error || foundation.status === "unsupported" || foundation.status === "unavailable" || foundation.status === "unconfirmed") return { ...foundation, stage: "structures" };
  const observedBars = bars.slice(0, foundation.series.length);
  const end = foundation.confirmedIndex;
  const byKnown = new Map<number, LowPivot[]>();
  for (const pivot of foundation.pivots) byKnown.set(pivot.knownIndex, [...(byKnown.get(pivot.knownIndex) ?? []), pivot]);
  const history: LowStructure[] = [];
  const events: LowStructureEvent[] = [];
  const active: Record<LowFamily, LowStructure | null> = { R: null, H: null };
  const spent = new Set<number>();
  const lows: LowPivot[] = [];
  let lastLow: LowPivot | null = null;
  let comparison: LowStructureAnalysis["comparison"] = null;
  const stamp = (index: number) => observedBars[index].time;
  const extreme = (kind: "high" | "low", start: number, finish: number): { price: number; index: number } => {
    if (start > finish || start < 0 || finish >= observedBars.length) return { price: Number.NaN, index: -1 };
    let index = start;
    for (let cursor = start + 1; cursor <= finish; cursor += 1) if (kind === "high" ? observedBars[cursor].high > observedBars[index].high : observedBars[cursor].low < observedBars[index].low) index = cursor;
    return { price: observedBars[index][kind], index };
  };
  const id = (family: LowFamily, indexes: number[]) => JSON.stringify([LOW_STRUCTURE_VERSION, foundation.symbol, foundation.timeframe, family, indexes.map(stamp), Object.values(p)]);
  const move = (structure: LowStructure, phase: LowPhase, index: number, reason?: string) => {
    if (structure.phase === phase) return;
    structure.phase = phase; structure.reason = reason ?? LOW_STRUCTURE_LABELS[phase]; structure.phaseAt = stamp(index); structure.phaseIndex = index;
    if (terminal(phase)) { structure.endedAt = stamp(index); structure.endedIndex = index; }
    events.push({ id: JSON.stringify([structure.id, phase, stamp(index)]), structureId: structure.id, family: structure.family, phase, time: stamp(index), index, reason: structure.reason });
  };
  const create = (family: LowFamily, indexes: number[], index: number, atr: number, phase: LowPhase,
    extra: Partial<Omit<LowStructure, "label">>): LowStructure => {
    const previous = active[family];
    if (previous && !terminal(previous.phase)) move(previous, "superseded", index, "새로 확인된 구조로 전환");
    const structure: LowStructure = { id: id(family, indexes), family, phase: phase === "breached" ? "expired" : "breached", reason: "", label: LOW_STRUCTURE_LABELS[phase], startedAt: stamp(indexes[0]), knownAt: stamp(index), knownIndex: index,
      anchorTimes: indexes.map(stamp), anchorIndexes: indexes, atrAnchor: atr, signalAt: null, signalIndex: null, triggerLevel: null,
      invalidationLevel: null, chaseLimit: null, referencePrice: null, segment: foundation.series[index].segment!, phaseAt: stamp(index), phaseIndex: index, evidence: [], ...extra };
    history.push(structure); active[family] = structure; move(structure, phase, index); return structure;
  };
  const check = (structure: LowStructure | null, index: number, allowSignal = true) => {
    if (!structure || terminal(structure.phase)) return;
    const bar = observedBars[index]; const point = foundation.series[index]; const atr = structure.atrAnchor;
    if (!point.priceReady || point.segment !== structure.segment) { move(structure, "invalidated", index, "가격 자료 단절 · 구조 종료"); return; }
    if (structure.family === "R" && structure.recoveredIndex != null && bar.low < structure.springLow! - p.testRiseAtr * atr) { move(structure, "invalidated", index, "회복 당시 저점 재이탈"); return; }
    if (structure.invalidationLevel != null && bar.low < structure.invalidationLevel) { move(structure, "invalidated", index, "고정 무효선 이탈"); return; }
    if (structure.phase === "breached") {
      if (bar.low < structure.springLow!) { structure.springLow = bar.low; structure.springIndex = index; structure.springTime = stamp(index); }
      if (bar.low < structure.supportZone!.lower - p.maxDepthAtr * atr) { move(structure, "invalidated", index, "깊은 이탈 · 해당 전략 제외"); return; }
      if (index - structure.breachIndex! >= p.reclaimBars) { move(structure, "expired", index, "회복 기한 초과"); return; }
      if (bar.close >= structure.supportZone!.upper) {
        structure.recoveredIndex = index; structure.recoveredAt = stamp(index); structure.invalidationLevel = structure.springLow! - p.testRiseAtr * atr; move(structure, "reclaimed", index);
      }
    }
    if (structure.phase === "reclaimed") {
      if (index - structure.recoveredIndex! > p.retestBars) { move(structure, "expired", index, "재시험 확인 기한 초과"); return; }
      const pivot = (byKnown.get(index) ?? []).find((item) => item.kind === "low" && item.index > structure.recoveredIndex! && item.segment === structure.segment &&
        item.price >= structure.springLow! + p.testRiseAtr * atr && item.price >= structure.supportZone!.lower && item.price <= structure.supportZone!.upper + p.testNearAtr * atr);
      if (pivot) {
        const peak = extreme("high", structure.recoveredIndex!, pivot.index - 1);
        if (peak.price - pivot.price >= p.minSwingAtr * atr) {
          structure.testIndex = pivot.index; structure.testTime = pivot.occurredAt; structure.testPrice = pivot.price;
          structure.testKnownAt = pivot.knownAt; structure.testKnownIndex = index; structure.peakIndex = peak.index; structure.peakPrice = peak.price;
          structure.triggerLevel = peak.price + p.triggerAtr * atr; structure.invalidationLevel = pivot.price - p.stopAtr * atr; move(structure, "tested", index);
          if (extreme("low", pivot.index, index).price < structure.invalidationLevel) { move(structure, "invalidated", index, "저점 확인 전에 무효선 이탈"); return; }
        }
      }
    }
    if (structure.phase === "tested" || structure.phase === "rising") {
      const anchor = structure.family === "R" ? structure.testKnownIndex! : structure.knownIndex;
      if (index - anchor >= p.triggerBars) { move(structure, "expired", index, "반등 돌파 대기 기한 초과"); return; }
      if (allowSignal && bar.close > structure.triggerLevel!) {
        structure.signalAt = stamp(index); structure.signalIndex = index; structure.referencePrice = bar.close;
        structure.chaseLimit = bar.close + p.maxAtr * atr; move(structure, "ready", index);
      }
    }
    if (structure.phase === "ready") {
      if (index - structure.signalIndex! > p.reviewBars) move(structure, "expired", index, "신호 후 검토 기한 초과");
      else if (bar.close < structure.triggerLevel!) move(structure, "invalidated", index, "반등 기준 아래로 종가 복귀");
    }
  };

  for (let index = 0; index <= end; index += 1) {
    check(active.R, index); check(active.H, index, false);
    if (!foundation.series[index].priceReady) { lastLow = null; continue; }
    for (const pivot of byKnown.get(index) ?? []) {
      if (pivot.kind !== "low") continue;
      const previous = lastLow; const atr = pivot.atrBefore;
      lows.push(pivot);
      if (previous && previous.segment === pivot.segment && finite(atr) && atr > 0) {
        const gap = pivot.index - previous.index; const peak = extreme("high", previous.index + 1, pivot.index - 1);
        comparison = { knownAt: pivot.knownAt, previousLow: previous.price, latestLow: pivot.price,
          direction: pivot.price - previous.price >= p.higherLowAtr * atr ? "higher" : pivot.price < previous.price ? "lower" : "same" };
        if (comparison.direction === "higher") {
          const structure = create("H", [previous.index, pivot.index], index, atr, "rising", { segment: pivot.segment,
            previousLow: previous.price, low1Index: previous.index, testIndex: pivot.index, testTime: pivot.occurredAt,
            testKnownAt: pivot.knownAt, testPrice: pivot.price, peakIndex: peak.index, peakPrice: peak.price,
            triggerLevel: peak.price + p.triggerAtr * atr, invalidationLevel: pivot.price - p.stopAtr * atr });
          if (extreme("low", pivot.index, index).price < structure.invalidationLevel!) move(structure, "invalidated", index, "저점 확인 전에 무효선 이탈");
          else check(structure, index);
          lastLow = pivot;
        } else if (gap > p.maxSeparation || gap < p.minSeparation && pivot.price < previous.price || peak.price - previous.price < p.minSwingAtr * atr && pivot.price < previous.price) lastLow = pivot;
      } else lastLow = pivot;
    }
    check(active.H, index);
    if (index < 1 || !foundation.series[index - 1].priceReady || !finite(foundation.series[index - 1].atr) || foundation.series[index - 1].atr! <= 0 || active.R && !terminal(active.R.phase)) continue;
    const atr = foundation.series[index - 1].atr!;
    let support: LowPivot | undefined;
    for (let cursor = lows.length - 1; cursor >= 0; cursor -= 1) {
      const candidate = lows[cursor];
      if (candidate.knownIndex < index && candidate.segment === foundation.series[index].segment && index - candidate.index <= p.lookback && !spent.has(candidate.index) &&
        extreme("high", candidate.index + 1, index - 1).price - candidate.price >= p.minSwingAtr * atr) { support = candidate; break; }
    }
    if (!support) continue;
    const lower = support.price - p.zoneAtr * atr; const upper = support.price + p.zoneAtr * atr;
    if (observedBars[index - 1].close >= lower && observedBars[index].low < lower - p.breachAtr * atr) {
      spent.add(support.index);
      create("R", [support.index, index], index, atr, "breached", { segment: foundation.series[index].segment!, supportPrice: support.price,
        supportIndex: support.index, supportKnownAt: support.knownAt, supportZone: { lower, upper }, breachIndex: index, breachTime: stamp(index),
        springLow: observedBars[index].low, springIndex: index, springTime: stamp(index) });
      check(active.R, index);
    }
  }
  const structures = history.map((structure) => ({ ...structure, label: LOW_STRUCTURE_LABELS[structure.phase], evidence: buildEvidence(structure, observedBars, foundation.series, end, foundation.pivots, p) }));
  const out: LowStructureAnalysis = { ...foundation, stage: "structures", parameters: p, structures, events,
    current: { R: structures.findLast((structure) => structure.family === "R") ?? null, H: structures.findLast((structure) => structure.family === "H") ?? null }, comparison,
    price: finite(observedBars[end]?.close) ? observedBars[end].close : null };
  return out;
}

const LOW_NAMES: Record<LowFamily, string> = { R: "저점 회복", H: "저점 상승" };
const LOW_RULES: Record<LowFamily, string> = {
  R: "이전 저점 위로 회복 → 다시 눌려도 저점 유지 → 반등 고점 위 마감",
  H: "이전보다 높은 저점 → 중간 반등 고점 위 마감",
};

function describeLowStructure(structure: LowStructure | null, p: LowStructureParameters): LowEntryReviewRow["description"] {
  if (!structure) return { label: "저점 확인을 기다리세요", reason: "선택한 방식에 맞는 저점과 반등이 아직 확인되지 않았어요.", rowLabel: "확인된 저점 없음" };
  const stages: Partial<Record<LowPhase, LowEntryReviewRow["description"]>> = {
    breached: { label: "지지 가격 회복을 기다리세요", reason: "이전 저점 아래로 내려왔어요. 종가가 지지 구간 위로 돌아오는지 확인하세요.", rowLabel: "지지 가격 회복 대기" },
    reclaimed: { label: "다시 눌릴 때 지지를 확인하세요", reason: "지지 가격을 회복했어요. 다시 내려올 때 회복 당시 저점을 지키는지 확인하세요.", rowLabel: "다시 눌려도 저점을 지키는지 확인" },
    tested: { label: "반등 고점 돌파를 기다리세요", reason: "다시 눌린 저점을 확인했어요. 종가가 반등 기준 위에서 마감하는지 확인하세요.", rowLabel: "저점 지지 확인 · 반등 돌파 대기" },
    rising: { label: "저점은 높아졌어요 · 돌파 대기", reason: "새 저점이 이전보다 높아요. 두 저점 사이의 반등 고점을 종가가 넘는지 확인하세요.", rowLabel: "높아진 저점 확인 · 반등 돌파 대기" },
    ready: { label: "진입 검토", reason: "저점 확인 후 반등 기준을 종가가 넘었어요.", rowLabel: "저점 확인 · 반등 돌파 충족" },
    superseded: { label: "새 저점을 확인하고 있어요", reason: "더 최근에 확인된 저점을 기준으로 다시 살펴봅니다.", rowLabel: "새 저점으로 기준 변경" },
  };
  if (structure.phase === "invalidated") {
    const causes: Record<string, LowEntryReviewRow["description"]> = {
      "고정 무효선 이탈": { label: "지지선 이탈 · 매수 대기", reason: "확정봉의 저가가 정해 둔 지지 하한선 아래로 내려왔어요. 새 저점과 반등을 기다리세요.", rowLabel: "지지 하한선 아래로 하락" },
      "회복 당시 저점 재이탈": { label: "저점 재이탈 · 매수 대기", reason: "확정봉의 저가가 회복 당시 저점 아래로 다시 내려왔어요. 새 저점과 반등을 기다리세요.", rowLabel: "회복했던 저점을 다시 이탈" },
      "깊은 이탈 · 해당 전략 제외": { label: "하락 폭이 큼 · 매수 대기", reason: "지지 가격 아래로 내려간 폭이 허용 범위를 넘었어요. 새 저점과 반등을 기다리세요.", rowLabel: "지지 아래 하락 폭이 큼" },
      "저점 확인 전에 무효선 이탈": { label: "지지선 이탈 · 매수 대기", reason: "저점을 확인하는 동안 가격이 지지 하한선 아래로 내려왔어요. 새 저점과 반등을 기다리세요.", rowLabel: "저점 확인 중 지지선 이탈" },
      "반등 기준 아래로 종가 복귀": { label: "반등 약해짐 · 매수 대기", reason: "확정 종가가 돌파했던 반등 기준 아래로 돌아왔어요. 새 저점과 반등을 기다리세요.", rowLabel: "돌파 기준 아래로 다시 마감" },
      "가격 자료 단절 · 구조 종료": { label: "가격 자료를 다시 확인하세요", reason: "봉 자료가 끊겨 저점과 반등을 이어서 확인할 수 없어요.", rowLabel: "가격 자료 연결 끊김" },
    };
    return causes[structure.reason] ?? { label: "근거가 사라졌어요", reason: "이전 저점의 지지가 유지되지 않았어요. 새 저점과 반등을 기다리세요.", rowLabel: "저점 지지 확인 중단" };
  }
  if (structure.phase === "expired") {
    const causes: Record<string, LowEntryReviewRow["description"]> = {
      "회복 기한 초과": { label: "새 매수 신호를 기다리세요", reason: `이탈 봉부터 ${p.reclaimBars}봉 안에 지지 가격을 회복하지 못했어요.`, rowLabel: "지지 회복 시간 경과" },
      "재시험 확인 기한 초과": { label: "새 매수 신호를 기다리세요", reason: `회복 후 ${p.retestBars}봉 안에 저점을 다시 지키는 모습이 확인되지 않았어요.`, rowLabel: "다시 눌린 저점 확인 안 됨" },
      "반등 돌파 대기 기한 초과": { label: "새 매수 신호를 기다리세요", reason: `저점 확인 봉부터 ${p.triggerBars}봉 안에 반등 고점을 넘지 못했어요.`, rowLabel: "반등 고점 돌파 안 됨" },
      "신호 후 검토 기한 초과": { label: "새 매수 신호를 기다리세요", reason: `이전 매수 신호의 확인 기간(발생봉과 이후 ${p.reviewBars}봉)이 끝났어요.`, rowLabel: "이전 매수 신호 확인 기간 종료" },
    };
    return causes[structure.reason] ?? { label: "새 매수 신호를 기다리세요", reason: "이전 저점에서 기다리던 확인 기간이 끝났어요.", rowLabel: "이전 확인 기간 종료" };
  }
  return stages[structure.phase] ?? { label: "저점 확인을 기다리세요", reason: "저점과 반등을 확인하고 있어요.", rowLabel: "저점 확인 대기" };
}

export function evaluateChartLabLowEntry(bars: ReadonlyArray<ChartExplorerBar>, options: ChartLabLowEntryOptions): ChartLabLowEntryResult {
  const { asOfIndex, confirmedThroughIndex, ...analysisOptions } = options;
  if (!Array.isArray(bars) || !Number.isInteger(asOfIndex) || asOfIndex < 0 || asOfIndex >= bars.length) {
    const invalid = invalidResult("invalid-as-of-index");
    return { ...invalid, analysisReason: invalid.reason, reviewStatus: "unconfirmed", selected: [], rows: [], setupDecision: { code: "blocked", label: "자료 확인 필요", reason: "선택 기준 봉 인덱스가 차트 범위를 벗어났습니다." },
      code: "blocked", label: "자료 확인 필요", reason: "선택 기준 봉 인덱스가 차트 범위를 벗어났습니다.", setup: "조건 대기", structureId: null, anchorTime: null,
      signalAge: null, chaseLimit: null, maxAtr: LOW_STRUCTURE_DEFAULTS.maxAtr, family: "low", matched: false, referenceType: "signal-close", combinationNote: "선택한 저점 확인 방식 중 하나가 충족되면 검토합니다." };
  }
  if (confirmedThroughIndex != null && (!Number.isInteger(confirmedThroughIndex) || confirmedThroughIndex < 0 || confirmedThroughIndex > asOfIndex)) {
    const invalid = invalidResult("invalid-confirmed-index");
    return { ...invalid, analysisReason: invalid.reason, reviewStatus: "unconfirmed", selected: [], rows: [], setupDecision: { code: "blocked", label: "자료 확인 필요", reason: "확정 기준 봉 인덱스가 선택 봉보다 뒤에 있거나 유효하지 않습니다." },
      code: "blocked", label: "자료 확인 필요", reason: "확정 기준 봉 인덱스가 선택 봉보다 뒤에 있거나 유효하지 않습니다.", setup: "조건 대기", structureId: null, anchorTime: null,
      signalAge: null, chaseLimit: null, maxAtr: LOW_STRUCTURE_DEFAULTS.maxAtr, family: "low", matched: false, referenceType: "signal-close", combinationNote: "선택한 저점 확인 방식 중 하나가 충족되면 검토합니다." };
  }
  const prefix = bars.slice(0, asOfIndex + 1);
  const offset = analysisOptions.timeframe === "4h" ? Math.max(0, prefix.length - H4_LOW_ANALYSIS_BARS) : 0;
  const analysisBars = prefix.slice(offset);
  const confirmedIndex = confirmedThroughIndex == null ? -1 : confirmedThroughIndex - offset;
  const analysis = analyzeLowStructures(analysisBars, { ...analysisOptions, asOf: analysisBars.at(-1)!.time,
    confirmedThrough: confirmedIndex < 0 ? null : analysisBars[confirmedIndex].time });
  const selected = [...new Set(analysisOptions.selected ?? ["R", "H"])].filter((value): value is LowFamily => value === "R" || value === "H");
  const rows: LowEntryReviewRow[] = selected.map((id) => {
    const structure = analysis.current[id];
    const description = describeLowStructure(structure, analysis.parameters ?? LOW_STRUCTURE_DEFAULTS);
    let code: LowEntryReviewCode = "wait";
    let label = description.rowLabel;
    if (!["ready", "insufficient-data"].includes(analysis.status)) { code = "blocked"; label = analysis.status === "unsupported" ? "지원 준비 중" : "자료 확인 필요"; }
    else if (structure?.phase === "invalidated") { code = "avoid"; label = description.rowLabel; }
    else if (structure?.phase === "ready") {
      const price = analysis.price;
      code = finite(price) && finite(structure.chaseLimit) && price > structure.chaseLimit ? "chase" : "candidate";
      label = code === "chase" ? "추격 주의" : "진입 검토";
      if (analysis.confirmedIndex - structure.signalIndex! > analysis.parameters!.reviewBars) { code = "wait"; label = "이전 매수 신호 확인 기간 종료"; }
    } else if (structure) label = description.rowLabel;
    if (analysis.status === "insufficient-data") { code = "blocked"; label = "가격/ATR 준비 중"; }
    return { id, name: LOW_NAMES[id], signal: code === "candidate" ? "entry" : code === "avoid" ? "exit" : "none",
      phase: structure?.phase ?? "wait", code, label, rule: LOW_RULES[id], structure, description };
  });
  const hasWaiting = rows.some((row) => row.code === "wait" && row.structure && !["expired", "superseded"].includes(row.structure.phase));
  const rank = (row: LowEntryReviewRow): number => row.code === "candidate" ? 0 : row.code === "wait" && row.structure && !["expired", "superseded"].includes(row.structure.phase) ? 1 :
    row.code === "chase" ? hasWaiting ? 2 : 1 : row.code === "avoid" ? 3 : row.code === "wait" ? 3.5 : 4;
  const ordered = rows.slice().sort((a, b) => rank(a) - rank(b) ||
    (b.structure?.testKnownIndex ?? b.structure?.knownIndex ?? -1) - (a.structure?.testKnownIndex ?? a.structure?.knownIndex ?? -1) || (a.id === "H" ? -1 : b.id === "H" ? 1 : 0));
  const best = ordered[0]; const structure = best?.structure ?? null;
  let code: LowEntryReviewCode = best?.code ?? "blocked";
  let label = code === "candidate" ? `${best.name} · 진입 검토` : code === "chase" ? "가격이 많이 올랐어요 · 매수 대기" : code === "blocked" ? best?.label ?? "전략을 선택하세요" : best?.description.label ?? "저점 확인을 기다리세요";
  let reason = code === "candidate" ? best!.description.reason : code === "chase" ? "최초 신호에서 정한 매수 상한을 넘었어요. 가격을 따라가기보다 새 신호를 기다리세요." :
    code === "blocked" ? best?.label ?? "저점 매수 방식을 하나 이상 선택하세요." : best?.description.reason ?? "저점과 반등을 확인하고 있어요.";
  if (rows.length === 0) { code = "blocked"; label = "전략을 선택하세요"; reason = "저점 확인 방식을 하나 이상 선택하세요."; }
  const setupDecision = { code, label, reason };
  const isHistorical = analysisOptions.historical ?? asOfIndex < bars.length - 1;
  const finalityUnknown = analysis.status === "unconfirmed" || analysis.provisional || confirmedThroughIndex == null;
  let reviewStatus: ChartLabLowEntryResult["reviewStatus"] = finalityUnknown ? "unconfirmed" : isHistorical ? "historical" : analysisOptions.judgmentReady === true ? "ready" : "unconfirmed";
  if (isHistorical && !finalityUnknown) { code = "historical"; label = "당시 조건 비교"; reason = "선택한 과거 봉의 결과예요. 현재 진입 안내가 아니에요."; }
  else if (analysisOptions.judgmentReady !== true) { code = "blocked"; label = "진입 판단 보류"; reason = analysisOptions.judgmentMessage || "자료 시각을 확인하지 못했습니다."; }
  else if (finalityUnknown && code === "candidate") { code = "wait"; label = "봉 확정 대기"; reason = "현재 봉은 잠정입니다. 확정된 가격을 확인하세요."; }
  if (finalityUnknown) reviewStatus = "unconfirmed";
  return {
    ...analysis, analysisReason: analysis.reason,
    reviewStatus, selected, rows, setupDecision, code, label, reason, setup: best?.label ?? "조건 대기", structureId: structure?.id ?? null,
    anchorTime: structure?.signalAt ?? null, signalAge: structure?.signalIndex != null ? analysis.confirmedIndex - structure.signalIndex : null,
    chaseLimit: structure?.chaseLimit ?? null, maxAtr: analysis.parameters?.maxAtr ?? LOW_STRUCTURE_DEFAULTS.maxAtr,
    family: "low", matched: best?.code === "candidate", referenceType: "signal-close",
    combinationNote: "선택한 저점 확인 방식 중 하나를 충족해도 검토합니다. 같은 저점에서 신호가 겹쳐도 확인 횟수를 더하지 않아요.",
  };
}
