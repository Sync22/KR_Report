import assert from "node:assert/strict";
import test from "node:test";

import { DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT } from "../src/app/api/chart-lab/report-alerts/route.ts";

test("report-alert route stays loopback-only and validates selected-date input", async () => {
  const remote = await GET(new Request("http://example.com/api/chart-lab/report-alerts?date=2026-10-22", { headers: { host: "example.com" } }));
  const invalid = await GET(new Request("http://127.0.0.1:3010/api/chart-lab/report-alerts?date=not-a-date", { headers: { host: "127.0.0.1:3010" } }));
  const extra = await GET(new Request("http://127.0.0.1:3010/api/chart-lab/report-alerts?date=2026-10-22&symbol=005930", { headers: { host: "127.0.0.1:3010" } }));
  assert.equal(remote.status, 403);
  assert.equal(invalid.status, 400);
  assert.equal(extra.status, 400);
});

test("report-alert mutation is same-origin and accepts only bounded JSON actions", async () => {
  const base = { host: "127.0.0.1:3010", origin: "http://127.0.0.1:3010", "content-type": "application/json" };
  const crossOrigin = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/report-alerts", {
    method: "POST", headers: { ...base, origin: "http://attacker.example" }, body: JSON.stringify({ action: "start" }),
  }));
  const invalidAction = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/report-alerts", {
    method: "POST", headers: base, body: JSON.stringify({ action: "write-db" }),
  }));
  const oversized = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/report-alerts", {
    method: "POST", headers: { ...base, "content-length": "17000" }, body: "x".repeat(17_000),
  }));
  assert.equal(crossOrigin.status, 403);
  assert.equal(invalidAction.status, 400);
  assert.equal(oversized.status, 413);
  assert.equal(HEAD().status, 405);
  assert.equal(OPTIONS().status, 405);
  assert.equal(PUT().status, 405);
  assert.equal(PATCH().status, 405);
  assert.equal(DELETE().status, 405);
});
