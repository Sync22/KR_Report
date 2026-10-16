import type { ChartExplorerBar, ChartExplorerTimeframe } from "../chart-explorer.ts";
import { calculateChartLabIndicators, type ChartLabIndicatorPoint } from "./indicators.ts";

// Adapted from https://github.com/gmparkingplace/Stock-Newbby (Apache-2.0):
// scripts/signals.py and results/dashboard/entry-model.js (ENTRY-2026-10-06).
export const CHART_LAB_ENTRY_VERSION = "ENTRY-2026-10-06";

export type ChartLabStrategy = "A" | "B" | "C" | "F";
export type ChartLabSignal = "entry" | "exit" | "none";
export type ChartLabReviewCode = "blocked" | "avoid" | "chase" | "candidate" | "wait" | "historical";
export type EntryReviewOptions = {
  asOf?: string;
  confirmedThrough?: string | null;
  judgmentReady?: boolean;
  judgmentMessage?: string;
  historical?: boolean;
  selected?: ReadonlyArray<ChartLabStrategy>;
  mode?: "all" | "any";
  maxAtr?: number;
};
export type EntryStrategyRow = {
  id: ChartLabStrategy;
  name: string;
  rule: string;
  signal: ChartLabSignal;
  signalAge: number | null;
  phase: "unavailable" | "exit" | "new" | "maintained" | "tracking" | "wait";
  readiness: { ready: boolean; missing: string[] };
};
export type EntryReviewDecision = { code: ChartLabReviewCode; label: string; reason: string };
export type EntryReview = {
  version: typeof CHART_LAB_ENTRY_VERSION;
  status: "ready" | "unconfirmed" | "invalid-data" | "historical";
  basis: string | null;
  selected: ChartLabStrategy[];
  mode: "all" | "any";
  maxAtr: number;
  rows: EntryStrategyRow[];
  signalHistory: Record<ChartLabStrategy, ChartLabSignal[]>;
  setup: string;
  matched: boolean;
  continuation: boolean;
  reviewMatched: boolean;
  setupDecision: EntryReviewDecision;
  code: ChartLabReviewCode;
  label: string;
  reason: string;
  judgmentMode: "closed-confirmed" | "live-snapshot" | "unknown" | "blocked";
  modeMessage: string;
  anchorTime: string | null;
  signalAge: number | null;
  referencePrice: number | null;
  referenceType: "breakout" | "signal-close";
  chaseLimit: number | null;
  chase: boolean;
  provisional: boolean;
  combinationNote: string | null;
};
export type ChartLabEntryOptions = Omit<EntryReviewOptions, "asOf" | "confirmedThrough"> & {
  timeframe: ChartExplorerTimeframe;
  asOfIndex: number;
  confirmedThroughIndex?: number | null;
};
export type ChartLabEntryResult = EntryReview & { timeframe: ChartExplorerTimeframe; asOfIndex: number };

const STRATEGY_RULES: Record<ChartLabStrategy, { name: string; rule: string }> = {
  A: { name: "추세 전환", rule: "20봉 평균이 60봉 평균을 아래에서 위로 교차하는 봉" },
  B: { name: "침체 반등", rule: "RSI가 직전 봉 30 이하에서 현재 봉 30 위로 회복" },
  C: { name: "고점 돌파", rule: "종가가 직전 20봉의 최고가를 초과" },
  F: { name: "추세·거래량 돌파", rule: "C 돌파 + 종가·20봉 평균이 60봉 평균 위 + 거래량 비율 > 1 + 돌파 폭 > 0.1 ATR" },
};
const STRATEGIES = Object.keys(STRATEGY_RULES) as ChartLabStrategy[];
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const emptyHistory = (): Record<ChartLabStrategy, ChartLabSignal[]> => ({ A: [], B: [], C: [], F: [] });

function validBar(bar: ChartExplorerBar): boolean {
  return !!bar && typeof bar === "object" && typeof bar.time === "string" && Number.isFinite(Date.parse(bar.time)) &&
    [bar.open, bar.high, bar.low, bar.close, bar.volume].every(finite) &&
    bar.open > 0 && bar.high > 0 && bar.low > 0 && bar.close > 0 && bar.volume >= 0 &&
    bar.high >= Math.max(bar.open, bar.low, bar.close) && bar.low <= Math.min(bar.open, bar.high, bar.close);
}

function blockedResult(reason: string, basis: string | null = null): EntryReview {
  const decision: EntryReviewDecision = { code: "blocked", label: "자료 부족 · 판단 보류", reason };
  return {
    version: CHART_LAB_ENTRY_VERSION, status: "invalid-data", basis, selected: [], mode: "all", maxAtr: 0.5, rows: [],
    signalHistory: emptyHistory(), setup: "조건 대기", matched: false, continuation: false, reviewMatched: false,
    setupDecision: decision, ...decision, judgmentMode: "blocked", modeMessage: reason,
    anchorTime: null, signalAge: null, referencePrice: null, referenceType: "signal-close",
    chaseLimit: null, chase: false, provisional: true, combinationNote: null,
  };
}

function readiness(strategy: ChartLabStrategy, index: number, indicators: readonly ChartLabIndicatorPoint[]): { ready: boolean; missing: string[] } {
  const current = indicators[index];
  const previous = indicators[index - 1];
  const requirements: Array<[string, number | null]> = [
    ["SMA 60", current?.sma60 ?? null], ["RSI", current?.rsi14 ?? null],
    ["20봉 고점", current?.donchianHigh20 ?? null], ["10봉 저점", current?.donchianLow10 ?? null],
  ];
  if (strategy === "A") requirements.push(["SMA 20", current?.sma20 ?? null], ["직전 SMA 20", previous?.sma20 ?? null], ["직전 SMA 60", previous?.sma60 ?? null]);
  if (strategy === "B") requirements.push(["직전 RSI", previous?.rsi14 ?? null]);
  if (strategy === "F") requirements.push(["SMA 20", current?.sma20 ?? null], ["ATR", current?.atr14 !== null && current?.atr14 !== undefined && current.atr14 > 0 ? current.atr14 : null], ["거래량 비율", current?.volumeRatio20 ?? null]);
  const missing = requirements.filter(([, value]) => !finite(value)).map(([name]) => name);
  return { ready: missing.length === 0, missing };
}

function signalsFor(bars: readonly ChartExplorerBar[], indicators: readonly ChartLabIndicatorPoint[]): Record<ChartLabStrategy, ChartLabSignal[]> {
  const signals = emptyHistory();
  for (let index = 0; index < bars.length; index += 1) {
    const current = indicators[index];
    const previous = indicators[index - 1];
    const close = bars[index].close;
    const sma60 = current.sma60;
    const rsi14 = current.rsi14;
    const donchianHigh20 = current.donchianHigh20;
    const donchianLow10 = current.donchianLow10;
    if (!finite(sma60) || !finite(rsi14) || !finite(donchianHigh20) || !finite(donchianLow10)) {
      for (const strategy of STRATEGIES) signals[strategy].push("none");
      continue;
    }
    const sma20 = current.sma20;
    const crossUp = finite(sma20) && finite(previous?.sma20) && finite(previous?.sma60) && previous.sma20 <= previous.sma60 && sma20 > sma60;
    const crossDown = finite(sma20) && finite(previous?.sma20) && finite(previous?.sma60) && previous.sma20 >= previous.sma60 && sma20 < sma60;
    const rsiUp = finite(current.rsi14) && finite(previous?.rsi14) && previous.rsi14 <= 30 && current.rsi14 > 30;
    const rsiDown = finite(current.rsi14) && finite(previous?.rsi14) && previous.rsi14 >= 70 && current.rsi14 < 70;
    const highBreak = close > donchianHigh20;
    const lowBreak = close < donchianLow10;
    const atr14 = current.atr14;
    const atrReady = finite(atr14) && atr14 > 0;
    const fGate = close > sma60 && finite(sma20) && sma20 > sma60;
    const fEntry = highBreak && fGate && finite(current.volumeRatio20) && current.volumeRatio20 > 1 && atrReady && (close - donchianHigh20) / atr14 > 0.1;
    signals.A.push(crossUp ? "entry" : crossDown ? "exit" : "none");
    signals.B.push(rsiUp ? "entry" : rsiDown ? "exit" : "none");
    signals.C.push(highBreak ? "entry" : lowBreak ? "exit" : "none");
    signals.F.push(fEntry ? "entry" : lowBreak || crossDown ? "exit" : "none");
  }
  return signals;
}

export function evaluateEntryReview(bars: ReadonlyArray<ChartExplorerBar>, options: EntryReviewOptions = {}): EntryReview {
  if (!bars.length) return blockedResult("차트 봉이 없습니다.");
  const index = options.asOf === undefined ? bars.length - 1 : bars.findIndex((bar) => bar.time === options.asOf);
  if (index < 0) return blockedResult("요청 기준 봉을 찾지 못했습니다.");
  const prefix = bars.slice(0, index + 1);
  for (let cursor = 0; cursor < prefix.length; cursor += 1) {
    if (!validBar(prefix[cursor])) return blockedResult("잘못된 OHLCV 봉이 있어 계산을 중단했습니다.", prefix[cursor]?.time ?? null);
    if (cursor && prefix[cursor].time <= prefix[cursor - 1].time) return blockedResult("봉 순서가 오름차순이 아닙니다.", prefix[cursor].time);
  }
  const maxAtr = options.maxAtr ?? 0.5;
  if (!finite(maxAtr) || maxAtr <= 0 || maxAtr > 5) return blockedResult("추격 상한은 0보다 크고 5 ATR 이하여야 합니다.", prefix.at(-1)!.time);
  const mode = options.mode === "any" ? "any" : "all";
  const selected = [...new Set<ChartLabStrategy>(options.selected ?? ["F"])].filter((value) => STRATEGIES.includes(value));
  const indicators = calculateChartLabIndicators(prefix);
  const signalHistory = signalsFor(prefix, indicators);
  const signal = (strategy: ChartLabStrategy, at: number): ChartLabSignal => signalHistory[strategy][at] ?? "none";
  const readinessByStrategy = Object.fromEntries(STRATEGIES.map((strategy) => [strategy, readiness(strategy, index, indicators)])) as Record<ChartLabStrategy, { ready: boolean; missing: string[] }>;
  const allKnown = selected.length > 0 && selected.every((strategy) => readinessByStrategy[strategy].ready);
  const matches = (at: number): boolean => selected.length > 0 && (mode === "any"
    ? selected.some((strategy) => signal(strategy, at) === "entry")
    : selected.every((strategy) => signal(strategy, at) === "entry"));
  const matched = allKnown && matches(index);
  const exit = selected.some((strategy) => signal(strategy, index) === "exit");
  let anchor: number | null = null;
  for (let at = index; at >= Math.max(0, index - 20); at -= 1) {
    if (selected.some((strategy) => signal(strategy, at) === "exit")) break;
    if (matches(at)) {
      anchor = at;
      while (anchor > 0 && matches(anchor - 1) && index - anchor < 20) anchor -= 1;
      break;
    }
  }
  const held = (strategy: ChartLabStrategy, at: number): boolean => {
    const bar = prefix[at];
    const point = indicators[at];
    return finite(bar?.close) && finite(point?.donchianLow10) && bar.close >= point.donchianLow10 &&
      (strategy === "A" ? finite(point.sma20) && finite(point.sma60) && point.sma20 > point.sma60 : finite(point.rsi14) && point.rsi14 > 30);
  };
  const heldSince = (strategy: ChartLabStrategy, at: number): boolean => {
    for (let cursor = at + 1; cursor <= index; cursor += 1) if (!held(strategy, cursor) || signal(strategy, cursor) === "exit") return false;
    return true;
  };
  let reviewAnchor: number | null = null;
  for (let at = index - 1; at >= Math.max(0, index - 3); at -= 1) {
    if (selected.some((strategy) => signal(strategy, at) === "exit")) break;
    if (!matches(at)) continue;
    const qualifies = (strategy: ChartLabStrategy): boolean => ["A", "B"].includes(strategy)
      ? signal(strategy, at) === "entry" && heldSince(strategy, at)
      : signal(strategy, index) === "entry";
    const hasHeldAb = selected.some((strategy) => ["A", "B"].includes(strategy) && signal(strategy, at) === "entry" && heldSince(strategy, at));
    if (hasHeldAb && (mode === "any" ? selected.some(qualifies) : selected.every(qualifies))) { reviewAnchor = at; break; }
  }
  const newEvent = matched && selected.some((strategy) => ["A", "B"].includes(strategy) && signal(strategy, index) === "entry");
  const continuation = !exit && allKnown && reviewAnchor !== null && !newEvent;
  if (newEvent) anchor = index;
  else if (continuation) anchor = reviewAnchor;
  const reviewMatched = matched || continuation;
  const atr = anchor === null ? null : indicators[anchor]?.atr14 ?? null;
  const price = prefix[index].close;
  const breakout = anchor === null ? null : indicators[anchor]?.donchianHigh20 ?? null;
  const referencePrice = anchor === null ? null : selected.some((strategy) => strategy === "C" || strategy === "F") && finite(breakout)
    ? Math.min(prefix[anchor].close, breakout) : prefix[anchor].close;
  const chaseLimit = finite(atr) && atr > 0 && finite(referencePrice) ? referencePrice + maxAtr * atr : null;
  const chase = chaseLimit !== null && price > chaseLimit;
  const age = anchor === null ? null : index - anchor;
  const reviewLowExit = anchor !== null && selected.some((strategy) => ["A", "B"].includes(strategy) && signal(strategy, anchor!) === "entry") &&
    age! > 0 && age! <= 3 && finite(indicators[index].donchianLow10) && price < indicators[index].donchianLow10;

  const rows: EntryStrategyRow[] = STRATEGIES.map((strategy) => {
    let recent: number | null = null;
    for (let at = index; at >= Math.max(0, index - 3); at -= 1) {
      if (signal(strategy, at) === "exit") break;
      if (signal(strategy, at) === "entry") { recent = at; break; }
    }
    const currentSignal = signal(strategy, index);
    const rowReadiness = readinessByStrategy[strategy];
    const phase: EntryStrategyRow["phase"] = !rowReadiness.ready ? "unavailable" : currentSignal === "exit" ? "exit" : currentSignal === "entry"
      ? ["C", "F"].includes(strategy) && signal(strategy, index - 1) === "entry" ? "maintained" : "new"
      : ["A", "B"].includes(strategy) && recent !== null && heldSince(strategy, recent) ? "tracking" : "wait";
    return { id: strategy, ...STRATEGY_RULES[strategy], signal: currentSignal, signalAge: recent === null ? null : index - recent, phase, readiness: rowReadiness };
  });

  let setup = exit || reviewLowExit ? "이탈 신호" : continuation ? `A/B 신호 후 검토 · ${index - reviewAnchor!}/3봉` : matched ? "진입 조건 충족" : "진입 조건 대기";
  let code: ChartLabReviewCode = "wait";
  let label = "조건 대기";
  let reason = "선택한 전략의 진입 신호가 아직 충족되지 않았어요.";
  if (!allKnown) {
    code = "blocked"; label = "자료 부족 · 판단 보류";
    reason = selected.length ? `선택 전략 계산에 필요한 자료 부족: ${[...new Set(selected.flatMap((strategy) => readinessByStrategy[strategy].missing))].join(" · ") || "기준 봉"}. 원래 전략의 공통 준비 조건은 유지합니다.` : "전략을 선택하세요.";
  } else if (exit) { code = "avoid"; label = "진입 보류 · 이탈 신호"; reason = "선택한 전략 중 이탈 신호가 있어 진입 검토를 보류합니다."; }
  else if (reviewLowExit) { code = "avoid"; label = "진입 보류 · 저점 이탈"; reason = "최근 10봉 저점 아래로 내려가 A/B 신호 후 검토를 중단합니다."; }
  else if (chase) { code = "chase"; label = "추격 주의 · 진입 보류"; reason = "신호 발생봉 종가에서 설정한 가격 상한을 넘었어요. 새 조건을 기다립니다."; }
  else if (age !== null && age > 3) reason = "이전 신호에서 3봉 넘게 지났어요. 과거 진입 화살표를 현재 허가로 사용하지 않아요.";
  else if (reviewMatched && chaseLimit === null) { code = "blocked"; label = "판단 보류"; reason = "추격 여부를 확인할 ATR 자료가 부족해요."; }
  else if (reviewMatched) { code = "candidate"; label = "진입 검토"; reason = continuation ? "A/B 신호 후 3봉 이내이며 유지 조건과 추격 상한을 통과했습니다." : "선택한 조건과 가격 상한을 충족했습니다. 주문·체결을 의미하지 않습니다."; }
  const setupDecision: EntryReviewDecision = { code, label, reason };

  const rawConfirmedThrough = options.confirmedThrough;
  const confirmedIndex = rawConfirmedThrough == null ? -1 : prefix.findIndex((bar) => bar.time === rawConfirmedThrough);
  if (rawConfirmedThrough != null && confirmedIndex < 0) return blockedResult("확정 기준 봉을 차트 자료에서 찾지 못했습니다.", prefix[index].time);
  const provisional = confirmedIndex < index;
  let judgmentMode: EntryReview["judgmentMode"] = rawConfirmedThrough == null ? "unknown" : provisional ? "live-snapshot" : "closed-confirmed";
  if (options.historical) { code = "historical"; label = "당시 조건 비교"; reason = "선택한 과거 봉의 결과예요. 현재 안내가 아닙니다."; }
  else if (options.judgmentReady !== true) { code = "blocked"; label = "진입 판단 보류"; reason = options.judgmentMessage || "자료 시각과 봉 확정 상태를 확인하지 못했습니다."; judgmentMode = "blocked"; }
  else if (rawConfirmedThrough == null) { code = "blocked"; label = "진입 판단 보류"; reason = "확정된 기준 봉을 확인하지 못했습니다."; judgmentMode = "unknown"; }
  else if (provisional && code === "candidate") { code = "wait"; label = "봉 확정 대기"; reason = "현재 봉은 잠정입니다. 마감 후 확정된 가격을 확인하세요."; }

  return {
    version: CHART_LAB_ENTRY_VERSION,
    status: rawConfirmedThrough == null || provisional ? "unconfirmed" : options.historical ? "historical" : options.judgmentReady !== true ? "unconfirmed" : "ready",
    basis: prefix[index].time, selected, mode, maxAtr, rows, signalHistory,
    setup, matched, continuation, reviewMatched, setupDecision, code, label, reason, judgmentMode,
    modeMessage: options.judgmentMessage ?? (provisional ? "진행 중인 봉은 잠정입니다." : ""),
    anchorTime: anchor === null ? null : prefix[anchor].time, signalAge: age, referencePrice,
    referenceType: selected.some((strategy) => strategy === "C" || strategy === "F") && finite(breakout) ? "breakout" : "signal-close",
    chaseLimit, chase, provisional,
    combinationNote: selected.includes("C") && selected.includes("F") ? "F는 C 조건을 포함해요. 두 신호가 켜져도 독립적인 확인 두 번이나 높은 승률을 뜻하지 않아요." : null,
  };
}

export function evaluateChartLabEntry(bars: ReadonlyArray<ChartExplorerBar>, options: ChartLabEntryOptions): ChartLabEntryResult {
  const { timeframe, asOfIndex, confirmedThroughIndex, ...reviewOptions } = options;
  if (!Number.isInteger(asOfIndex) || asOfIndex < 0 || asOfIndex >= bars.length) {
    return { ...blockedResult("선택 기준 봉 인덱스가 차트 범위를 벗어났습니다."), timeframe, asOfIndex };
  }
  if (confirmedThroughIndex != null && (!Number.isInteger(confirmedThroughIndex) || confirmedThroughIndex < 0 || confirmedThroughIndex > asOfIndex)) {
    return { ...blockedResult("확정 기준 봉 인덱스가 선택 봉보다 뒤에 있거나 유효하지 않습니다."), timeframe, asOfIndex };
  }
  return {
    ...evaluateEntryReview(bars, { ...reviewOptions, asOf: bars[asOfIndex].time,
      confirmedThrough: confirmedThroughIndex == null ? null : bars[confirmedThroughIndex].time,
      historical: reviewOptions.historical ?? asOfIndex < bars.length - 1 }),
    timeframe,
    asOfIndex,
  };
}
