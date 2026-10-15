import assert from "node:assert/strict";
import test from "node:test";
import { buildBenchmarkCases, countCacheStates, loopbackOrigin, nearestRank } from "../scripts/benchmark-public-get.mjs";

test("benchmark matrix covers the 14 stored GET routes with shared date and stock inputs", () => {
  const cases = buildBenchmarkCases("2026-10-08", "005930");
  assert.equal(cases.length, 14);
  assert.equal(new Set(cases.map(({ path }) => path)).size, 14);
  assert.ok(cases.every(({ path }) => path.startsWith("/api/")));
  assert.ok(cases.every(({ kind }) => kind === "stored"));
  assert.ok(cases.some(({ path }) => path === "/api/daily/2026-10-08/stocks/005930"));
  assert.ok(cases.some(({ path }) => path.includes("/api/rotation-overlay?date=2026-10-08")));
  assert.ok(cases.some(({ path }) => path.includes("/api/category?date=2026-10-08")));
  assert.ok(cases.every(({ path }) => !/toss-market-context|priority-indicators|priority-current-quotes|toss-priority/.test(path)));
});

test("nearestRank uses a stable nearest-rank percentile for the benchmark sample", () => {
  assert.equal(nearestRank([9, 1, 5, 3, 7], 0.5), 5);
  assert.equal(nearestRank([9, 1, 5, 3, 7], 0.95), 9);
  assert.throws(() => nearestRank([], 0.95), RangeError);
});

test("benchmark cache-state accounting distinguishes unreported services", () => {
  assert.deepEqual(countCacheStates(["hit", "hit", "miss", null]), { hit: 2, miss: 1, unreported: 1 });
});

test("benchmark input accepts only valid dates, stock codes, and loopback origins", () => {
  assert.throws(() => buildBenchmarkCases("2026-02-30", "005930"), TypeError);
  assert.throws(() => buildBenchmarkCases("2026-10-08", "00593x"), TypeError);
  assert.equal(loopbackOrigin("http://127.0.0.1:3010/path", "Next origin"), "http://127.0.0.1:3010");
  assert.throws(() => loopbackOrigin("https://example.com", "Next origin"), /loopback/);
});
