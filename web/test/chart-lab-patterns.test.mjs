import assert from "node:assert/strict";
import test from "node:test";

import { detectChartLabPatterns } from "../src/domain/chart-lab/patterns.ts";

function datedBars(count, build) {
  const first = Date.UTC(2026, 0, 1);
  return Array.from({ length: count }, (_, index) => {
    const time = new Date(first + index * 86_400_000).toISOString().slice(0, 10);
    return { time, ...build(index) };
  });
}

function flagBars(direction = "up", breakout = true, adjustment = 13) {
  const rows = [];
  const add = (close, high = close + 0.5, low = close - 0.5, volume = 100) => rows.push({
    time: new Date(Date.UTC(2026, 0, 1 + rows.length)).toISOString().slice(0, 10),
    open: close, high, low, close, volume,
  });
  for (let index = 0; index < 30; index += 1) add(100);
  for (const price of [102, 105, 108, 111, 114]) add(price, undefined, undefined, 300);
  for (let index = 0; index < adjustment; index += 1) {
    const middle = 113.5 - 0.1 * index;
    const high = 115 - 0.1 * index - (index % 4 === 2 ? 0 : 0.4);
    const low = 111.8 - 0.1 * index + (index % 4 === 0 ? 0 : 0.4);
    add(middle, high, low, 80);
  }
  if (breakout) add(118, 119, 112, 500);
  if (direction === "down") {
    for (const row of rows) {
      const { open, high, low, close } = row;
      Object.assign(row, { open: 220 - open, high: 220 - low, low: 220 - high, close: 220 - close });
    }
  }
  return rows;
}

function triangleBars(kind = "ascending", breakout = false) {
  const rows = datedBars(30, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  for (let index = 0; index < 36; index += 1) {
    const upper = kind === "symmetrical" ? 114 - 0.16 * index : 114;
    const lower = 104 + 0.2 * index;
    const close = (upper + lower) / 2;
    const margin = Math.min(0.5, Math.max(0.05, (upper - lower) / 4));
    const high = index % 6 === 2 ? upper : close + margin;
    const low = index % 6 === 5 ? lower : close - margin;
    rows.push({
      time: new Date(Date.UTC(2026, 0, 31 + index)).toISOString().slice(0, 10),
      open: close, high: Math.max(high, close), low: Math.min(low, close), close, volume: 100,
    });
  }
  if (breakout) {
    const upper = 114;
    rows.push({
      time: new Date(Date.UTC(2026, 2, 8)).toISOString().slice(0, 10),
      open: 110, high: 118, low: 109.8, close: 117, volume: 400,
    });
  }
  if (kind === "descending") {
    for (const row of rows) {
      const { open, high, low, close } = row;
      Object.assign(row, { open: 220 - open, high: 220 - low, low: 220 - high, close: 220 - close });
    }
  }
  return rows;
}

test("detects an observed bull flag with fixed source-bar basis and immutable snapshot", () => {
  const bars = flagBars();
  const patterns = detectChartLabPatterns(bars, "1d");
  const flag = patterns.find((pattern) => pattern.kind === "bull-flag");
  assert.ok(flag);
  assert.equal(flag.ruleVersion, "flag-d-v2");
  assert.equal(flag.basis.startIndex, 35);
  assert.equal(flag.basis.startTime, bars[35].time);
  assert.equal(flag.basis.endIndex, bars.length - 1);
  assert.equal(flag.status, "observed-breakout");
  assert.ok(flag.measurements.poleMove > 0);
  assert.ok(flag.measurements.poleAtr > 0);
  assert.ok(flag.measurements.poleAtrMultiple >= 2.5);
  assert.ok(flag.measurements.rvol20Previous > 1.2);
  assert.equal(flag.measurements.volumeEvidence, "volume-confirmed");
  assert.ok(Object.isFrozen(patterns));
  assert.ok(Object.isFrozen(flag));
  assert.ok(Object.isFrozen(flag.basis));
  assert.throws(() => { flag.measurements.retracementRatio = 999; }, TypeError);
});

test("detects a forming ascending triangle without inventing a breakout", () => {
  const bars = triangleBars("ascending");
  const pattern = detectChartLabPatterns(bars, "1d").find((item) => item.kind === "ascending-triangle");
  assert.ok(pattern);
  assert.equal(pattern.status, "forming");
  assert.equal(pattern.direction, "neutral");
  assert.equal(pattern.ruleVersion, "triangle-d-v2");
  assert.ok(pattern.measurements.contactCount >= 5);
  assert.equal(pattern.measurements.volumeEvidence, "volume-insufficient");
  assert.ok(pattern.basis.startIndex < pattern.basis.endIndex);
});

test("detects mirrored bear flags and all three upstream triangle classes", () => {
  const bear = detectChartLabPatterns(flagBars("down"), "1d").find((item) => item.kind === "bear-flag");
  assert.ok(bear);
  assert.equal(bear.direction, "down");

  for (const kind of ["ascending", "descending", "symmetrical"]) {
    const pattern = detectChartLabPatterns(triangleBars(kind), "1d").find((item) => item.kind === `${kind}-triangle`);
    assert.ok(pattern, `expected ${kind} triangle`);
  }
});

test("uses previous-window high crossing for an observed resistance break", () => {
  const bars = datedBars(24, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  bars[23] = { ...bars[23], open: 140, high: 141, low: 139, close: 140, volume: 240 };
  const pattern = detectChartLabPatterns(bars, "1d").find((item) => item.kind === "resistance-breakout");
  assert.ok(pattern);
  assert.equal(pattern.status, "observed-crossing");
  assert.equal(pattern.measurements.boundary, 101);
  assert.equal(pattern.measurements.triggerPrice, 101.2);
  assert.equal(pattern.measurements.rvol20Previous, 2.4);
  assert.equal(pattern.measurements.volumeEvidence, "volume-confirmed");
  assert.equal(pattern.ruleVersion, "horizontal-d-v1");
});

test("uses previous-window low crossing for an observed support break", () => {
  const bars = datedBars(24, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  bars[23] = { ...bars[23], open: 60, high: 101, low: 59, close: 60, volume: 240 };
  const pattern = detectChartLabPatterns(bars, "1d").find((item) => item.kind === "support-breakout");
  assert.ok(pattern);
  assert.equal(pattern.status, "observed-crossing");
  assert.equal(pattern.measurements.boundary, 99);
  assert.equal(pattern.measurements.triggerPrice, 98.8);
  assert.equal(pattern.measurements.rvol20Previous, 2.4);
});

test("reports unsupported, insufficient, and calendar-gap data explicitly", () => {
  const short = datedBars(12, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  assert.ok(detectChartLabPatterns(short, "1w").some((item) => item.status === "unsupported-timeframe"));
  assert.ok(detectChartLabPatterns(short, "1d").some((item) => item.status === "insufficient-data"));

  const afterGap = datedBars(6, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  afterGap.forEach((bar, index) => { bar.time = new Date(Date.UTC(2026, 2, 1 + index)).toISOString().slice(0, 10); });
  const gap = [...short.slice(0, 6), ...afterGap];
  assert.ok(detectChartLabPatterns(gap, "1d").some((item) => item.status === "data-gap"));

  const brokenFlag = flagBars();
  for (let index = 40; index < brokenFlag.length; index += 1) {
    brokenFlag[index].time = new Date(Date.parse(brokenFlag[index].time) + 30 * 86_400_000).toISOString().slice(0, 10);
  }
  const splitResult = detectChartLabPatterns(brokenFlag, "1d");
  assert.ok(splitResult.some((item) => item.status === "data-gap"));
  assert.equal(splitResult.some((item) => item.kind === "bull-flag"), false);
});

test("rejects malformed OHLC and duplicate timestamps as invalid data", () => {
  const bars = datedBars(24, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  bars[10] = { ...bars[10], high: 98 };
  assert.equal(detectChartLabPatterns(bars, "1d")[0].status, "invalid-data");
  bars[10] = { ...bars[10], high: 101, time: bars[9].time };
  assert.equal(detectChartLabPatterns(bars, "1d")[0].status, "invalid-data");
});

test("caps pattern calculations to a recent window while preserving original input indices", () => {
  const bars = datedBars(260, () => ({ open: 100, high: 101, low: 99, close: 100, volume: 100 }));
  const tail = flagBars().slice(30);
  tail.forEach((bar, index) => {
    bar.time = new Date(Date.parse(bars.at(-1).time) + (index + 1) * 86_400_000).toISOString().slice(0, 10);
  });
  bars.push(...tail);
  const patterns = detectChartLabPatterns(bars, "1d");
  const flag = patterns.find((item) => item.kind === "bull-flag");
  assert.ok(flag);
  assert.ok(flag.basis.endIndex >= 260);
  assert.ok(flag.basis.endIndex - flag.basis.startIndex < 60);
});
