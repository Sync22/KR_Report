import assert from "node:assert/strict";
import test from "node:test";

import { GET, HEAD, POST, PUT } from "../src/app/api/chart-lab/monitor/route.ts";

test("Chart Lab monitor API rejects a non-loopback request", async () => {
  const response = await GET(new Request("http://example.com/api/chart-lab/monitor", { headers: { host: "example.com" } }));
  assert.equal(response.status, 403);
});

test("Chart Lab monitor POST rejects a cross-origin caller before parsing control data", async () => {
  const response = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST",
    headers: { host: "127.0.0.1:3010", origin: "http://attacker.example", "content-type": "application/json" },
    body: JSON.stringify({ action: "start" }),
  }));
  assert.equal(response.status, 403);
});

test("Chart Lab monitor API only accepts bounded JSON controls and POST/GET", async () => {
  const base = { host: "127.0.0.1:3010", origin: "http://127.0.0.1:3010", "content-type": "application/json" };
  const invalidAction = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST", headers: base, body: JSON.stringify({ action: "delete-database" }),
  }));
  const oversized = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST", headers: { ...base, "content-length": "17000" }, body: "x".repeat(17_000),
  }));
  assert.equal(invalidAction.status, 400);
  assert.equal(oversized.status, 413);
  assert.equal(HEAD().status, 405);
  assert.equal(PUT().status, 405);
});
