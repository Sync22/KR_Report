import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { emptyChartLabState, readChartLabState, writeChartLabState } from "../src/server/chart-lab-store.ts";

test("Chart Lab state starts empty when its per-user file does not exist", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-lab-store-"));
  try {
    assert.deepEqual(await readChartLabState(path.join(folder, "monitor.json")), emptyChartLabState());
  } finally { await rm(folder, { recursive: true, force: true }); }
});

test("Chart Lab state round-trips bounded watch entries and immutable event snapshots", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-lab-store-"));
  const file = path.join(folder, "monitor.json");
  const state = {
    schemaVersion: 1,
    running: true,
    startedAt: "2026-10-16T00:00:00.000Z",
    lastPollAt: null,
    lastError: null,
    symbols: [{ symbol: "005930", name: "Samsung Electronics", focus: true, lastPolledAt: null, failureCount: 0 }],
    events: [{ event_id: "evt-1", symbol: "005930", kind: "triangle", basis_time: "2026-10-15", snapshot: { basis_close: 70000 } }],
  };
  try {
    await writeChartLabState(state, file);
    assert.deepEqual(await readChartLabState(file), state);
  } finally { await rm(folder, { recursive: true, force: true }); }
});

test("Chart Lab state rejects invalid monitor bounds without replacing the saved file", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-lab-store-"));
  const file = path.join(folder, "monitor.json");
  const original = emptyChartLabState();
  try {
    await writeChartLabState(original, file);
    await assert.rejects(writeChartLabState({ ...original, symbols: Array.from({ length: 21 }, (_, index) => ({ symbol: `SYM${index}`, name: "Test", focus: false, lastPolledAt: null, failureCount: 0 })) }, file), /invalid-chart-lab-state/);
    assert.deepEqual(await readChartLabState(file), original);
    await (await import("node:fs/promises")).writeFile(file, "not-json", "utf8");
    await assert.rejects(readChartLabState(file), /invalid-chart-lab-state/);
    assert.equal(await readFile(file, "utf8"), "not-json");
  } finally { await rm(folder, { recursive: true, force: true }); }
});
