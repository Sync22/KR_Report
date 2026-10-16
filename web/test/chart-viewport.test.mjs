import assert from "node:assert/strict";
import test from "node:test";

import { hasVisibleChartBar, panChartRange, resolveChartRange, zoomChartRange } from "../src/domain/chart-viewport.ts";

test("Chart Explorer opens the requested number of latest bars and clamps short histories", () => {
  assert.deepEqual(resolveChartRange(800, 200), { start: 600, end: 800 });
  assert.deepEqual(resolveChartRange(17, 200), { start: 0, end: 17 });
  assert.deepEqual(resolveChartRange(0, 200), { start: 0, end: 0 });
});

test("wheel zoom changes scale while keeping the pointer's time near its position", () => {
  const current = { start: 400, end: 600 };
  const zoomed = zoomChartRange(current, 800, "in", 0.25);
  assert.equal(zoomed.end - zoomed.start, 160);
  assert.ok(Math.abs((zoomed.start + 0.25 * (160 - 1)) - (current.start + 0.25 * (200 - 1))) <= 1);
  assert.deepEqual(zoomChartRange({ start: 0, end: 10 }, 800, "in", 0.5), { start: 0, end: 10 });
});

test("chart panning clamps at both ends without changing the visible bar count", () => {
  const current = { start: 300, end: 400 };
  assert.deepEqual(panChartRange(current, 500, -500), { start: 0, end: 100 });
  assert.deepEqual(panChartRange(current, 500, 500), { start: 400, end: 500 });
  assert.deepEqual(panChartRange(current, 500, 24), { start: 324, end: 424 });
});

test("a structure overlay is eligible only when its basis candle is inside the visible window", () => {
  const bars = [{ time: "2026-09-07" }, { time: "2026-10-08" }];
  assert.equal(hasVisibleChartBar(bars, "2026-10-08"), true);
  assert.equal(hasVisibleChartBar(bars, "2026-08-31"), false);
});
