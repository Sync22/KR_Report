import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test, { after } from "node:test";

import { acquireChartAlertLock } from "../src/server/chart-alert-store.ts";
import { chartLabStatePath } from "../src/server/chart-lab-store.ts";

const previousLocalAppData = process.env.LOCALAPPDATA;
const stateRoot = await mkdtemp(path.join(os.tmpdir(), "chart-lab-monitor-route-"));
process.env.LOCALAPPDATA = stateRoot;
const statePath = chartLabStatePath();
const { GET, HEAD, POST, PUT } = await import("../src/app/api/chart-lab/monitor/route.ts");
if (previousLocalAppData === undefined) delete process.env.LOCALAPPDATA;
else process.env.LOCALAPPDATA = previousLocalAppData;

after(async () => { await rm(stateRoot, { recursive: true, force: true }); });

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

test("Chart Lab monitor API reports ownership held by another local server", async () => {
  const release = await acquireChartAlertLock(`${statePath}.lock`);
  assert.ok(release);
  try {
    const headers = { host: "127.0.0.1:3010", origin: "http://127.0.0.1:3010", "content-type": "application/json" };
    const status = await GET(new Request("http://127.0.0.1:3010/api/chart-lab/monitor", { headers }));
    const start = await POST(new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
      method: "POST", headers, body: JSON.stringify({ action: "start" }),
    }));
    assert.equal((await status.json()).ownerActiveElsewhere, true);
    assert.equal(start.status, 409);
    assert.equal((await start.json()).error, "monitor-owned-elsewhere");
  } finally { await release(); }
});
