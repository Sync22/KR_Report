import assert from "node:assert/strict";
import test from "node:test";

import { analyzeLowStructures, evaluateChartLabLowEntry } from "../src/domain/chart-lab/low-structure.ts";

const day = (index) => new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10);

function sample(family = "H") {
  const bars = Array.from({ length: 44 }, () => ({ time: "", open: 100, high: 102, low: 98, close: 100, volume: 100 }));
  const set = (index, low, high, close, volume = 100) => {
    bars[index] = { time: day(index), open: Math.min(high, Math.max(low, close - 0.5)), low, high, close, volume };
  };
  bars.forEach((bar, index) => { bar.time = day(index); });
  set(18, 95, 99, 97, 200); set(19, 97, 103, 100); set(20, 98, 104, 101);
  if (family === "H") {
    set(23, 98, 103, 100); set(24, 97, 100, 98, 80); set(25, 98, 103, 101); set(26, 99, 106, 105, 200);
    for (let index = 27; index < 44; index += 1) set(index, 103, 107, 105, 150);
  } else {
    set(24, 93.7, 100, 97, 200); set(25, 97, 103, 101); set(26, 98, 104, 102);
    set(27, 97, 101, 99); set(28, 95.5, 99, 97, 60); set(29, 97, 103, 100, 70); set(30, 98, 107, 105, 200);
    for (let index = 31; index < 44; index += 1) set(index, 103, 107, 105, 150);
  }
  return bars;
}

function run(bars, index = bars.length - 1, options = {}) {
  return analyzeLowStructures(bars, {
    symbol: "TEST",
    asOf: bars[index]?.time,
    confirmedThrough: bars[index]?.time ?? null,
    ...options,
  });
}

test("H higher-low pattern is known only after its two-bar right confirmation", () => {
  const bars = sample("H");
  assert.equal(run(bars, 25).current.H, null);
  const result = run(bars, 26);

  assert.equal(result.version, "low-entry-v1");
  assert.equal(result.current.H.phase, "ready");
  assert.equal(result.current.H.testTime, day(24));
  assert.equal(result.current.H.knownAt, day(26));
  assert.equal(result.current.H.signalAt, day(26));
});

test("R low-reclaim structure advances breach, reclaim, retest, then close breakout", () => {
  const bars = sample("R");
  const unreclaimed = structuredClone(bars);
  unreclaimed[24].close = 94;
  assert.equal(run(unreclaimed, 24).current.R.phase, "breached");
  assert.equal(run(bars, 24).current.R.phase, "reclaimed");
  assert.equal(run(bars, 27).current.R.phase, "reclaimed");
  const result = run(bars, 30);

  assert.equal(result.current.R.phase, "ready");
  assert.equal(result.current.R.testTime, day(28));
  assert.equal(result.current.R.testKnownAt, day(30));
  assert.equal(result.current.R.signalAt, day(30));
  assert.deepEqual(result.events.filter((event) => event.family === "R").map((event) => event.phase), ["breached", "reclaimed", "tested", "ready"]);
  assert.equal(new Set(result.events.map((event) => event.id)).size, result.events.length);
});

test("confirmed cutoff and historical as-of prevent right-side lookahead", () => {
  const bars = sample("R");
  const options = { asOf: day(30), confirmedThrough: day(30), symbol: "TEST" };
  const baseline = analyzeLowStructures(bars, options);
  const changedFuture = structuredClone(bars);
  changedFuture[40] = { ...changedFuture[40], time: "9999-12-31", low: 1, close: 1 };

  assert.deepEqual(analyzeLowStructures(changedFuture, options), baseline);
  assert.equal(analyzeLowStructures(bars, { ...options, confirmedThrough: null }).status, "unconfirmed");
  assert.equal(analyzeLowStructures(bars, { ...options, confirmedThrough: day(27) }).basis, day(27));
});

test("deep breach, stop line and post-trigger close rules are strict and do not revive", () => {
  const deep = sample("R");
  deep[24].low = 88;
  assert.equal(run(deep, 24).current.R.phase, "invalidated");

  const stopped = sample("H");
  const initial = run(stopped, 26).current.H;
  stopped[27].low = initial.invalidationLevel - 1e-8;
  assert.equal(run(stopped, 27).current.H.phase, "invalidated");
  stopped[27].low = initial.invalidationLevel;
  assert.equal(run(stopped, 27).current.H.phase, "ready", "equality at the strict invalidation line remains valid");
});

test("unsupported timeframe, malformed ordering and invalid parameters fail closed", () => {
  const bars = sample("H");
  assert.equal(run(bars, 26, { timeframe: "1w" }).status, "unsupported");
  const reversed = structuredClone(bars);
  [reversed[20].time, reversed[21].time] = [reversed[21].time, reversed[20].time];
  assert.equal(run(reversed, 26).error.code, "invalid-bar-order");
  assert.equal(run(bars, 26, { params: { leftBars: 40 } }).error.code, "invalid-parameters");
});

test("index-based R/H contract is explicit about unknown finality and missing 4h session continuity", () => {
  const bars = sample("H");
  const unknown = evaluateChartLabLowEntry(bars, { timeframe: "1d", asOfIndex: 26, symbol: "TEST" });
  const confirmed = evaluateChartLabLowEntry(bars, { timeframe: "1d", asOfIndex: 26, confirmedThroughIndex: 26, judgmentReady: true, historical: false, selected: ["H"], symbol: "TEST" });
  const provisional = evaluateChartLabLowEntry(bars, { timeframe: "1d", asOfIndex: 27, confirmedThroughIndex: 26, judgmentReady: true, selected: ["H"], symbol: "TEST" });
  const h4 = evaluateChartLabLowEntry(bars, { timeframe: "4h", asOfIndex: 26, confirmedThroughIndex: 26, symbol: "TEST" });

  assert.equal(unknown.status, "unconfirmed");
  assert.equal(unknown.current.H, null);
  assert.equal(confirmed.current.H.phase, "ready");
  assert.equal(confirmed.code, "candidate");
  assert.equal(confirmed.rows[0].signal, "entry");
  assert.equal(provisional.code, "wait");
  assert.equal(provisional.setupDecision.code, "candidate");
  assert.equal(h4.status, "unsupported");
  assert.equal(h4.analysisReason, "4h-session-continuity-required");
});

test("stock H4 R/H uses supplied session-gap metadata and restarts ATR after missing bars", () => {
  const bars = sample("H").map((bar, index) => ({
    ...bar,
    time: new Date(Date.UTC(2026, 0, 5, 9) + index * 4 * 60 * 60 * 1000).toISOString(),
    missingBarsBefore: 0,
  }));
  const analyze = (inputBars) => analyzeLowStructures(inputBars, {
    symbol: "005930", timeframe: "4h", asOf: inputBars[26].time, confirmedThrough: inputBars[26].time,
  });
  const supported = analyze(bars);
  const broken = structuredClone(bars);
  broken[22].missingBarsBefore = 1;
  const afterGap = analyze(broken);

  assert.equal(supported.current.H.phase, "ready");
  assert.equal(afterGap.series[22].segment, afterGap.series[21].segment + 1);
  assert.ok(afterGap.dataWarnings.some((warning) => warning.code === "bar-gap" && warning.index === 22));
  assert.equal(afterGap.current.H, null);
});

test("stock H4 stays unsupported when any bar lacks validated session continuity", () => {
  const bars = sample("H").map((bar, index) => ({
    ...bar,
    time: new Date(Date.UTC(2026, 0, 5, 9) + index * 4 * 60 * 60 * 1000).toISOString(),
    missingBarsBefore: 0,
  }));
  delete bars[20].missingBarsBefore;
  const result = analyzeLowStructures(bars, {
    symbol: "005930", timeframe: "4h", asOf: bars[26].time, confirmedThrough: bars[26].time,
  });

  assert.equal(result.status, "unsupported");
  assert.equal(result.reason, "4h-session-continuity-required");
});

test("index-based stock H4 review runs only with continuity metadata and keeps finality separate", () => {
  const bars = sample("H").map((bar, index) => ({
    ...bar,
    time: new Date(Date.UTC(2026, 0, 5, 9) + index * 4 * 60 * 60 * 1000).toISOString(),
    missingBarsBefore: 0,
  }));
  const confirmed = evaluateChartLabLowEntry(bars, {
    timeframe: "4h", asOfIndex: 26, confirmedThroughIndex: 26, judgmentReady: true, historical: false, symbol: "005930",
  });
  const unknown = evaluateChartLabLowEntry(bars, {
    timeframe: "4h", asOfIndex: 26, judgmentReady: true, symbol: "005930",
  });

  assert.equal(confirmed.current.H.phase, "ready");
  assert.equal(confirmed.code, "candidate");
  assert.equal(unknown.reviewStatus, "unconfirmed");
  assert.equal(unknown.current.H, null);
});

test("stock H4 continuity only requires the bounded R/H context through the selected bar", () => {
  const bars = Array.from({ length: 150 }, (_, index) => ({
    time: new Date(Date.UTC(2026, 0, 5, 9) + index * 4 * 60 * 60 * 1000).toISOString(),
    open: 100, high: 102, low: 98, close: 100, volume: 100,
    ...(index >= 30 ? { missingBarsBefore: 0 } : {}),
  }));
  const result = evaluateChartLabLowEntry(bars, {
    timeframe: "4h", asOfIndex: 149, confirmedThroughIndex: 149, judgmentReady: true, historical: false, symbol: "005930",
  });

  assert.notEqual(result.analysisReason, "4h-session-continuity-required");
  assert.equal(result.observedThrough, bars[149].time);
});
