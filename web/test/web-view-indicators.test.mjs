import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import test from "node:test";

import { buildPriorityIndicatorProjection } from "../src/server/web-view-indicators.ts";

const AS_OF = "2026-10-08";
const METADATA = {
  code: "005930",
  symbol: "005930.KS",
  market: "KOSPI",
  requestedAsOf: AS_OF,
  source: "Toss OpenAPI · 조정 일봉",
  sourceFetchedAt: "2026-10-08T16:00:00+09:00",
  sourceDate: AS_OF,
  barStatus: "unknown",
  confirmedPolicy: "Toss daily candles do not identify finality; status is not inferred.",
  cacheHit: false,
  stale: false,
  lastSuccessAt: "2026-10-08T16:00:00+09:00",
  sourceCalculationVersion: "toss-adjusted-daily-v1",
};

function bars(count, trend = "rise") {
  const start = Date.UTC(2025, 0, 1);
  return Array.from({ length: count }, (_, index) => {
    const time = new Date(start + index * 86_400_000).toISOString().slice(0, 10);
    const close = trend === "flat" ? 100 : trend === "fall" ? 500 - index : 100 + index;
    const volume = trend === "flat" ? 100 : 100 + (index % 7) * 10;
    return { time, open: close, high: close + 2, low: close - 2, close, volume };
  });
}

function flagBars() {
  return Array.from({ length: 70 }, (_, index) => {
    const time = bars(70)[index].time;
    if (index < 36) return { time, open: 100, high: 101, low: 99, close: 100, volume: 100 };
    if (index < 40) {
      const close = 100 + (index - 36) * (35 / 3);
      return { time, open: close, high: close + 1, low: close - 1, close, volume: 100 };
    }
    const offset = index - 40;
    const upper = 150 - 0.3 * offset + (offset % 5 === 2 ? 2 : 0);
    const lower = 130 - 0.3 * offset - (offset % 5 === 4 ? 2 : 0);
    const close = (upper + lower) / 2;
    return { time, open: close, high: upper, low: lower, close, volume: 100 + offset % 7 };
  });
}

function triangleBars() {
  return Array.from({ length: 70 }, (_, index) => {
    const time = bars(70)[index].time;
    if (index < 35) return { time, open: 160, high: 165, low: 155, close: 160, volume: 100 };
    const offset = index - 35;
    const upper = 230 - 1.8 * offset + (offset % 5 === 2 ? 5 : 0);
    const lower = 80 + 1.8 * offset - (offset % 5 === 4 ? 5 : 0);
    const close = (upper + lower) / 2;
    return { time, open: close, high: upper, low: lower, close, volume: 100 + offset % 7 };
  });
}

function oracle(candles, metadata = METADATA, validatePublicSnapshot = false) {
  const input = JSON.stringify({ candles, metadata, validatePublicSnapshot });
  const script = String.raw`
import json, sys
sys.path.insert(0, ${JSON.stringify(path.resolve(process.cwd(), "../src"))})
from stock_monitor.web_view_indicators import (
    build_indicator_snapshot, build_indicator_chart_data, build_reference_conditions,
    build_indicator_confirmation, build_priority_condition_status,
    build_priority_condition_explanation,
)
payload = json.load(sys.stdin)
meta, candles = payload["metadata"], payload["candles"]
snapshot = build_indicator_snapshot(
    code=meta["code"], symbol=meta["symbol"], market=meta["market"],
    requested_as_of=meta["requestedAsOf"], candles=candles, source=meta["source"],
    source_fetched_at=meta["sourceFetchedAt"], source_date=meta.get("sourceDate"),
    bar_status=meta.get("barStatus", "unknown"), confirmed_policy=meta.get("confirmedPolicy", "unknown"),
    cache_hit=meta.get("cacheHit"), cache_age=meta.get("cacheAge"), stale=meta.get("stale"),
    last_success_at=meta.get("lastSuccessAt"), source_calculation_version=meta.get("sourceCalculationVersion"),
)
if payload.get("validatePublicSnapshot"):
    from stock_monitor.cli import _web_view_public_newbby_indicator_snapshot
    snapshot = _web_view_public_newbby_indicator_snapshot(snapshot)
price = build_reference_conditions(candles, meta["requestedAsOf"])
confirmation = build_indicator_confirmation(snapshot)
json.dump({
    "snapshot": snapshot,
    "chart": build_indicator_chart_data(candles, meta["requestedAsOf"]),
    "price_conditions": price,
    "indicator_confirmation": confirmation,
    "condition_status": build_priority_condition_status(price, confirmation),
    "condition_explanation": build_priority_condition_explanation(price, confirmation),
}, sys.stdout, ensure_ascii=False, allow_nan=False)
`;
  return JSON.parse(execFileSync("python", ["-c", script], { input, encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" } }));
}

function withoutRevision(projection) {
  return {
    ...projection,
    snapshot: { ...projection.snapshot, dataRevision: "<sha256>" },
  };
}

test("warm-up lengths and all trend shapes match the Python calculator", () => {
  for (const [count, trend] of [[10, "flat"], [13, "rise"], [20, "fall"], [21, "flat"], [199, "rise"], [200, "fall"], [220, "flat"], [385, "rise"]]) {
    const candles = bars(count, trend);
    const expected = oracle(candles);
    const actual = buildPriorityIndicatorProjection({ ...METADATA, candles });
    assert.equal(actual.snapshot.dataRevision, expected.snapshot.dataRevision, `revision count=${count}, trend=${trend}`);
    assert.deepEqual(withoutRevision(actual), withoutRevision(expected),
      `count=${count}, trend=${trend}`);
  }
});

test("as-of cutoff ignores future bars and keeps sorted chart and provenance dates", () => {
  const candles = bars(25);
  candles.push({ time: "2026-10-09", open: 999, high: 1000, low: 998, close: 999, volume: 50 });
  const result = buildPriorityIndicatorProjection({ ...METADATA, sourceDate: null, candles });
  assert.equal(result.snapshot.barAsOf, candles.at(-2).time);
  assert.equal(result.snapshot.sourceDate, "2026-10-09");
  assert.equal(result.chart.bars.at(-1).time, candles.at(-2).time);
  const expected = oracle(candles, { ...METADATA, sourceDate: null });
  assert.equal(result.snapshot.dataRevision, expected.snapshot.dataRevision);
  assert.deepEqual(withoutRevision(result), withoutRevision(expected));
});

test("bar and metadata trust boundaries reject invalid dates, duplicates, OHLCV, and symbols", () => {
  const valid = bars(21);
  for (const [bad, message] of [
    [[{ ...valid[0], time: "2026-02-30" }], "invalid-daily-bar-date"],
    [[valid[0], valid[0]], "duplicate-daily-bar-date"],
    [[{ ...valid[0], volume: -1 }], "invalid-daily-ohlcv"],
    [[{ ...valid[0], low: valid[0].high + 1 }], "invalid-daily-ohlcv"],
    [[{ ...valid[0], close: Infinity }], "invalid-daily-ohlcv"],
  ]) {
    assert.throws(() => buildPriorityIndicatorProjection({ ...METADATA, candles: bad }), new RegExp(message));
  }
  assert.throws(() => buildPriorityIndicatorProjection({ ...METADATA, symbol: "000000.KS", candles: valid }), /symbol-does-not-match-market/);
  assert.throws(() => buildPriorityIndicatorProjection({ ...METADATA, requestedAsOf: "2026-2-8", candles: valid }), /requested-as-of-must-be-YYYY-MM-DD/);
});

test("prior 20-bar high and 10-bar low use strict comparisons and exclude the current candle", () => {
  const base = bars(21, "flat");
  const setClose = (close) => base.map((bar, index) => index === 20
    ? { ...bar, open: close, high: close + 1, low: close - 1, close }
    : bar);
  const above = buildPriorityIndicatorProjection({ ...METADATA, candles: setClose(103) });
  const equalHigh = buildPriorityIndicatorProjection({ ...METADATA, candles: setClose(102) });
  const equalLow = buildPriorityIndicatorProjection({ ...METADATA, candles: setClose(98) });
  const below = buildPriorityIndicatorProjection({ ...METADATA, candles: setClose(97) });
  assert.equal(above.price_conditions.price_condition_state, "above_prior_20_bar_high");
  assert.equal(equalHigh.price_conditions.price_condition_state, "within_reference_band");
  assert.equal(equalLow.price_conditions.price_condition_state, "within_reference_band");
  assert.equal(below.price_conditions.price_condition_state, "below_prior_10_bar_low");
  assert.deepEqual(withoutRevision(above), withoutRevision(oracle(setClose(103))));
});

test("volume ratio uses the current-inclusive 20-bar window and accepts 1.2 equality", () => {
  const candles = bars(20, "flat").map((bar, index) => index < 19 ? { ...bar, volume: 100 } : { ...bar, volume: (5700 / 47) });
  const result = buildPriorityIndicatorProjection({ ...METADATA, candles });
  assert.equal(result.snapshot.indicators.volume.ratio20, 1.2);
  assert.equal(result.indicator_confirmation.volume_confirmation_state, "confirmed");
  const expected = oracle(candles);
  assert.equal(result.snapshot.dataRevision, expected.snapshot.dataRevision);
  assert.deepEqual(withoutRevision(result), withoutRevision(expected));
});

test("indicator calculations retain the EMA, RSI, Bollinger, Donchian, and OBV contracts", () => {
  const flat = bars(21, "flat");
  const flatResult = buildPriorityIndicatorProjection({ ...METADATA, candles: flat });
  const indicators = flatResult.snapshot.indicators;
  assert.equal(buildPriorityIndicatorProjection({ ...METADATA, candles: bars(19, "flat") }).snapshot.indicators.movingAverages.ema20, null);
  assert.equal(buildPriorityIndicatorProjection({ ...METADATA, candles: bars(20, "flat") }).snapshot.indicators.movingAverages.ema20, 100);
  assert.equal(indicators.movingAverages.ema20, 100);
  assert.equal(indicators.rsi14.value, 50);
  assert.deepEqual([indicators.bollinger20.middle, indicators.bollinger20.upper, indicators.bollinger20.lower], [100, 100, 100]);
  assert.deepEqual([indicators.donchian20.upper, indicators.donchian20.middle, indicators.donchian20.lower], [102, 100, 98]);
  assert.equal(indicators.donchian20.includeCurrent, true);
  assert.equal(indicators.obv.value, 0);
  assert.equal(indicators.obv.delta5, 0);
  assert.equal(indicators.obv.seedTime, flat[0].time);
  const advancing = bars(6).map((bar, index) => ({ ...bar, open: 100 + index, high: 101 + index, low: 99 + index, close: 100 + index, volume: 10 + index }));
  const obvResult = buildPriorityIndicatorProjection({ ...METADATA, candles: advancing });
  assert.equal(obvResult.snapshot.indicators.obv.value, 65);
  assert.equal(obvResult.snapshot.indicators.obv.delta5, 65);
  assert.deepEqual(withoutRevision(flatResult), withoutRevision(oracle(flat)));
  assert.deepEqual(withoutRevision(obvResult), withoutRevision(oracle(advancing)));
});

test("volume profile keeps separate tied peaks and each structure family matches Python", () => {
  const peakBars = Array.from({ length: 12 }, (_, index) => {
    const price = 10 + index * 10;
    return index === 11
      ? { time: bars(12)[index].time, open: 70, high: 120, low: 10, close: 70, volume: 1 }
      : { time: bars(12)[index].time, open: price, high: price, low: price, close: price, volume: index === 0 || index === 10 ? 10 : 1 };
  });
  const peak = buildPriorityIndicatorProjection({ ...METADATA, candles: peakBars });
  const profile = peak.snapshot.indicators.volumeProfile12;
  assert.equal(profile.bins.filter((bin) => bin.peak).length, 2);
  assert.equal(peak.indicator_confirmation.peak_volume_bins.length, 2);
  assert.equal(peak.indicator_confirmation.volume_profile_state, "between_peak_volume_bins");

  for (const [family, candles] of [["flag", flagBars()], ["triangle", triangleBars()]]) {
    const result = buildPriorityIndicatorProjection({ ...METADATA, candles });
    const expected = oracle(candles, METADATA, true);
    assert.equal(result.snapshot.dataRevision, expected.snapshot.dataRevision);
    assert.deepEqual(withoutRevision(result), withoutRevision(expected));
    assert.ok(result.snapshot.structures.some((row) => row.family === family), `${family} geometry should be recognized`);
    assert.ok(result.snapshot.structures.some((row) => row.family === "horizontal"));
    for (const item of result.snapshot.structures) {
      assert.ok(["horizontal", "flag", "triangle"].includes(item.family));
      assert.ok(Array.isArray(item.measurements));
      for (const measurement of item.measurements) {
        assert.equal(typeof measurement.name, "string");
        assert.equal(typeof measurement.label, "string");
        assert.equal(typeof measurement.unit, "string");
      }
    }
    assert.deepEqual(Object.keys(result.snapshot.structureStatus).sort(), ["flag", "horizontal", "triangle"]);
  }
});
