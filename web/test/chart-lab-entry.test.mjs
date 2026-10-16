import assert from "node:assert/strict";
import test from "node:test";

import { calculateChartLabIndicators } from "../src/domain/chart-lab/indicators.ts";
import { evaluateChartLabEntry, evaluateEntryReview } from "../src/domain/chart-lab/entry.ts";

function bars(closes, volumes = closes.map(() => 100)) {
  return closes.map((close, index) => ({
    time: new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10),
    open: close,
    high: close + 1,
    low: close - 1,
    close,
    volume: volumes[index],
  }));
}

const closed = (barsValue) => ({
  confirmedThrough: barsValue.at(-1)?.time ?? null,
  judgmentReady: true,
});

test("Newbby signal inputs keep rolling seeds, prior-bar Donchian and current-inclusive volume ratio", () => {
  const input = bars(Array(65).fill(100));
  const output = calculateChartLabIndicators(input);

  assert.equal(output.length, input.length);
  assert.ok(Math.abs(output[13].atr14 - 2) < 1e-12);
  assert.equal(output[14].rsi14, 100);
  assert.equal(output[19].sma20, 100);
  assert.equal(output[59].sma60, 100);
  assert.equal(output[19].donchianHigh20, null);
  assert.equal(output[20].donchianHigh20, 101);
  assert.equal(output[10].donchianLow10, 99);
  assert.equal(output[19].volumeRatio20, 1);
});

test("overlay indicators match Newbby EMA/WMA seeds, population Bollinger and current-bar Donchian", () => {
  const input = bars(Array.from({ length: 45 }, (_, index) => index + 1));
  const output = calculateChartLabIndicators(input);
  const point = output[19];
  const squares = Array.from({ length: 20 }, (_, index) => (index + 1) ** 2).reduce((sum, value) => sum + value, 0);

  assert.ok(Math.abs(point.ema20 - 10.5) < 1e-12);
  assert.ok(Math.abs(point.wma20 - squares / 210) < 1e-12);
  assert.ok(Math.abs(point.bollinger20.middle - 10.5) < 1e-12);
  assert.ok(Math.abs(point.bollinger20.upper - (10.5 + 2 * Math.sqrt(33.25))) < 1e-12);
  assert.equal(point.donchian20.upper, 21);
  assert.equal(point.donchian20.lower, 0);
  assert.equal(output[18].ema20, null);
  assert.equal(output[20].donchianHigh20, 21, "entry breakout excludes the current candle");
});

test("rolling indicators restart after a missing close instead of bridging the gap", () => {
  const input = bars(Array.from({ length: 45 }, (_, index) => index + 1));
  input[20] = { ...input[20], close: null };
  const output = calculateChartLabIndicators(input);

  assert.equal(output[20].ema20, null);
  assert.equal(output[39].ema20, null);
  assert.equal(output[40].ema20, 31.5);
  assert.equal(output[40].sma20, 31.5);
  assert.equal(output[40].bollinger20.middle, 31.5);
});

test("C and F use the upstream strict breakout and F gates, without assigning a score", () => {
  const input = bars(Array(65).fill(100));
  input[64] = { ...input[64], close: 103, high: 104, volume: 300 };
  const result = evaluateEntryReview(input, { ...closed(input), selected: ["C", "F"], maxAtr: 2 });

  assert.equal(result.code, "candidate");
  assert.equal(result.matched, true);
  assert.equal(result.rows.find((row) => row.id === "C").signal, "entry");
  assert.equal(result.rows.find((row) => row.id === "F").signal, "entry");
  assert.equal(result.rows.find((row) => row.id === "C").phase, "new");
  assert.equal("score" in result, false);
  assert.equal("score" in result.setupDecision, false);
});

test("A moving-average crossover and B RSI recovery are distinct same-bar events", () => {
  const input = bars(Array.from({ length: 85 }, (_, index) => index < 40 ? 100 : index < 60 ? 80 : 80 + (index - 59) * 3));
  const signals = evaluateEntryReview(input, { ...closed(input), selected: ["A", "B"], mode: "any" });
  const indicators = calculateChartLabIndicators(input);
  const aIndex = signals.signalHistory.A.findIndex((signal) => signal === "entry");
  const bIndex = signals.signalHistory.B.findIndex((signal) => signal === "entry");

  assert(aIndex > 0);
  assert(indicators[aIndex - 1].sma20 <= indicators[aIndex - 1].sma60);
  assert(indicators[aIndex].sma20 > indicators[aIndex].sma60);
  assert(bIndex > 0);
  assert(indicators[bIndex - 1].rsi14 <= 30);
  assert(indicators[bIndex].rsi14 > 30);
});

test("selected historical cutoff ignores every later bar", () => {
  const input = bars(Array(70).fill(100));
  input[64] = { ...input[64], close: 103, high: 104, volume: 300 };
  const options = { asOf: input[64].time, confirmedThrough: input[64].time, historical: true, selected: ["C"], maxAtr: 2 };
  const before = evaluateEntryReview(input, options);
  const changedFuture = structuredClone(input);
  changedFuture[69] = { ...changedFuture[69], time: "9999-12-31", close: 99999, high: 100000 };

  assert.deepEqual(evaluateEntryReview(changedFuture, options), before);
  assert.equal(before.code, "historical");
  assert.equal(before.setupDecision.code, "candidate");
});

test("unknown or provisional finality and missing readiness never become a live candidate", () => {
  const input = bars(Array(65).fill(100));
  input[64] = { ...input[64], close: 103, high: 104, volume: 300 };
  const unknown = evaluateEntryReview(input, { selected: ["C"], maxAtr: 2 });
  const provisional = evaluateEntryReview(input, { ...closed(input), confirmedThrough: input[63].time, selected: ["C"], maxAtr: 2 });
  const notReady = evaluateEntryReview(input, { ...closed(input), judgmentReady: false, selected: ["C"], maxAtr: 2 });

  assert.equal(unknown.code, "blocked");
  assert.equal(unknown.setupDecision.code, "candidate");
  assert.equal(provisional.code, "wait");
  assert.equal(provisional.label, "봉 확정 대기");
  assert.equal(notReady.code, "blocked");
});

test("invalid periods and malformed cutoff inputs return blocked output rather than throwing", () => {
  const input = bars(Array(65).fill(100));
  assert.equal(evaluateEntryReview(input, { ...closed(input), maxAtr: 11 }).code, "blocked");
  assert.equal(evaluateEntryReview(input, { ...closed(input), asOf: "2026-02-30" }).code, "blocked");
});

test("index-based chart contract exposes raw strategy rows and keeps unknown source finality unconfirmed", () => {
  const input = bars(Array(65).fill(100));
  input[64] = { ...input[64], close: 103, high: 104, volume: 300 };
  const result = evaluateChartLabEntry(input, { timeframe: "1d", asOfIndex: 64, selected: ["C"], maxAtr: 2 });
  const confirmed = evaluateChartLabEntry(input, { timeframe: "1d", asOfIndex: 64, confirmedThroughIndex: 64, judgmentReady: true, selected: ["C"], maxAtr: 2 });

  assert.equal(result.status, "unconfirmed");
  assert.equal(result.rows.length, 4);
  assert.equal(result.rows.find((row) => row.id === "C").signal, "entry");
  assert.equal(confirmed.status, "ready");
  assert.equal(confirmed.code, "candidate");
});
