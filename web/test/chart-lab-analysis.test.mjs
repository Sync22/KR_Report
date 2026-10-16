import assert from "node:assert/strict";
import test from "node:test";

import { buildChartLabAnalysis } from "../src/domain/chart-lab/analysis.ts";

function makeBars(count) {
  return Array.from({ length: count }, (_, index) => ({
    time: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
    open: 50 + index, high: 51 + index, low: 49 + index, close: 50.5 + index, volume: 1000 + index * 10,
  }));
}

test("Chart Lab analysis uses only bars through the selected historical basis", () => {
  const baseline = makeBars(45);
  const bars = [...baseline];
  bars[30] = { ...bars[30], high: 999_999, close: 999_000, volume: 999_000_000 };
  const prefix = buildChartLabAnalysis(baseline, {
    symbol: "005930", timeframe: "1d", asOfIndex: 29, selected: ["A", "B", "C", "F"], mode: "any", maxAtr: 0.5,
  });
  const full = buildChartLabAnalysis(bars, {
    symbol: "005930", timeframe: "1d", asOfIndex: 29, selected: ["A", "B", "C", "F"], mode: "any", maxAtr: 0.5,
  });
  assert.deepEqual(full, prefix);
  assert.equal(full.basis, bars[29].time);
  assert.equal(full.barCount, 30);
  assert.ok(full.patterns.every((pattern) => pattern.basis.endIndex === null || pattern.basis.endIndex <= 29));
  assert.equal(full.entry.code, "historical");
  assert.equal(full.entry.judgmentMode, "unknown");
});
