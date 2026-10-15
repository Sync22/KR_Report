import assert from "node:assert/strict";
import test from "node:test";

import { cachedStoredJsonResponse } from "../src/server/stored-response-cache.ts";

test("stored JSON responses cache by path and semantic inputs, ignoring unused query parameters", async () => {
  let builds = 0;
  const build = () => ({ value: ++builds });
  const request = new Request("http://localhost/api/daily?date=2026-10-14");

  const first = cachedStoredJsonResponse(request, ["2026-10-14"], build);
  const ignoredQuery = cachedStoredJsonResponse(new Request("http://localhost/api/daily?date=2026-10-14&tracking=one"), ["2026-10-14"], build);
  const otherDate = cachedStoredJsonResponse(new Request("http://localhost/api/daily?date=2026-10-15"), ["2026-10-15"], build);
  const otherPath = cachedStoredJsonResponse(new Request("http://localhost/api/other?date=2026-10-14"), ["2026-10-14"], build);

  assert.notEqual(first, ignoredQuery);
  assert.equal(first.headers.get("content-type"), "application/json");
  assert.equal(first.headers.get("cache-control"), "no-store");
  assert.equal(await first.text(), await ignoredQuery.text());
  assert.deepEqual(await otherDate.json(), { value: 2 });
  assert.deepEqual(await otherPath.json(), { value: 3 });
  assert.equal(builds, 3);
});

test("thrown builders are not cached", async () => {
  let builds = 0;
  const request = new Request("http://localhost/api/archive?limit=20");

  assert.throws(() => cachedStoredJsonResponse(request, [20], () => {
    builds += 1;
    throw new Error("builder failed");
  }), /builder failed/);
  const response = cachedStoredJsonResponse(request, [20], () => {
    builds += 1;
    return { ok: true };
  });

  assert.deepEqual(await response.json(), { ok: true });
  assert.equal(builds, 2);
});

test("cache diagnostics are opt-in and report misses and hits", () => {
  const request = () => new Request("http://localhost/api/benchmark-cache-check", {
    headers: { "x-stock-monitor-benchmark": "1" },
  });
  const first = cachedStoredJsonResponse(request(), [], () => ({ ok: true }));
  const second = cachedStoredJsonResponse(request(), [], () => ({ ok: false }));

  assert.equal(first.headers.get("x-stock-monitor-cache"), "miss");
  assert.equal(second.headers.get("x-stock-monitor-cache"), "hit");
  const normal = cachedStoredJsonResponse(new Request("http://localhost/api/normal-cache-check"), [], () => ({ ok: true }));
  assert.equal(normal.headers.get("x-stock-monitor-cache"), null);
  assert.deepEqual([...normal.headers.keys()].sort(), ["cache-control", "content-type"]);
});
