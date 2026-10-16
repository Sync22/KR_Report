import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { ChartLabMonitorService } from "../src/server/chart-lab-monitor.ts";
import { readChartLabState } from "../src/server/chart-lab-store.ts";

const bars = Array.from({ length: 40 }, (_, index) => ({
  time: new Date(Date.UTC(2026, 8, index + 1)).toISOString().slice(0, 10),
  open: 10 + index, high: 12 + index, low: 9 + index, close: 11 + index, volume: 100 + index,
}));

const pattern = Object.freeze({
  kind: "ascending-triangle", family: "triangle", status: "forming", direction: "up", ruleVersion: "TRI-2",
  dataStatus: "complete", basis: { startIndex: 10, endIndex: 20, startTime: bars[10].time, endTime: bars[20].time },
  measurements: [{ name: "height", value: 4 }], geometry: [],
});

test("Chart Lab monitor stores immutable source-labelled pattern events and can pause", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-lab-monitor-"));
  const file = path.join(folder, "monitor.json");
  const monitor = new ChartLabMonitorService({
    statePath: file,
    getChart: async (date, symbol, timeframe) => ({ status: 200, payload: {
      available: true, requested_as_of: date, symbol, timeframe, source: "Yahoo Finance", source_fetched_at: "2026-10-16T00:00:00.000Z",
      source_date: "2026-10-15", adjusted: false, bar_status: "unknown", bars,
    } }),
    detectPatterns: () => [pattern],
    now: () => new Date("2026-10-16T00:00:00.000Z"),
  });
  try {
    await monitor.configure([{ symbol: "005930", name: "Samsung Electronics", focus: true }]);
    await monitor.start();
    await monitor.pollDueOnce();
    const state = await readChartLabState(file);
    assert.equal(state.lastPollAt, "2026-10-16T00:00:00.000Z");
    assert.equal(state.events.length, 1);
    assert.equal(state.events[0].source, "Yahoo Finance");
    assert.equal(state.events[0].bar_status, "unknown");
    assert.equal(state.events[0].basis_end_time, bars[20].time);
    assert.deepEqual(state.events[0].snapshot.bars, bars.slice(10, 21));
    await monitor.pause();
    assert.equal((await readChartLabState(file)).running, false);
  } finally {
    await monitor.pause().catch(() => undefined);
    await rm(folder, { recursive: true, force: true });
  }
});

test("Chart Lab monitor enforces 20-symbol and 3-focus limits", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-lab-monitor-"));
  const monitor = new ChartLabMonitorService({ statePath: path.join(folder, "monitor.json"), getChart: async () => { throw new Error("must not fetch"); } });
  try {
    await assert.rejects(monitor.configure(Array.from({ length: 21 }, (_, index) => ({ symbol: `SYM${index}`, name: "Test", focus: false }))), /invalid-chart-lab-state/);
    await assert.rejects(monitor.configure(Array.from({ length: 4 }, (_, index) => ({ symbol: `SYM${index}`, name: "Test", focus: true }))), /invalid-chart-lab-state/);
  } finally { await rm(folder, { recursive: true, force: true }); }
});
