import assert from "node:assert/strict";
import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { ChartAlertMonitorService } from "../src/server/chart-alert-monitor.ts";
import { acquireChartAlertLock, readChartAlertState, writeChartAlertState } from "../src/server/chart-alert-store.ts";

function pattern(status) {
  return {
    kind: "support-breakout", family: "horizontal", status, direction: "down", ruleVersion: "horizontal-m1-v1",
    dataStatus: "complete", basis: { startIndex: 0, endIndex: 29, startTime: "2026-10-22T00:33:00.000Z", endTime: "2026-10-22T01:02:00.000Z" },
    measurements: {}, geometry: {},
  };
}

test("report-focus chart monitor baselines old patterns and spools one new 1-minute transition", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-monitor-"));
  const statePath = path.join(folder, "report-alerts.json");
  const spoolPath = path.join(folder, "spool");
  let now = new Date("2026-10-22T10:02:00+09:00");
  let patternStatus = "forming";
  let requests = 0;
  const bars = Array.from({ length: 30 }, (_, index) => ({
    time: new Date(Date.parse("2026-10-22T00:33:00.000Z") + index * 60_000).toISOString(),
    open: 100, high: 101, low: 99, close: 100, volume: 100,
  }));
  const monitor = new ChartAlertMonitorService({
    statePath, spoolPath, lockPath: `${statePath}.lock`, now: () => now, marketOpen: () => true, providerConfigured: () => true,
    getMinuteBars: async (date, symbol) => {
      requests += 1;
      assert.equal(date, "2026-10-22");
      assert.equal(symbol, "005930");
      return { status: 200, available: true, symbol, displayName: "삼성전자", bars, source: "Toss OpenAPI · 1m candles", sourceFetchedAt: now.toISOString(), barStatus: "unknown" };
    },
    detectPatterns: () => [pattern(patternStatus)],
  });
  try {
    await monitor.addWatch({ report_business_date: "2026-10-22", stock_code: "005930", stock_name: "삼성전자", report_count: 2, report_reason: "리포트 집중" });
    await monitor.start();
    await monitor.pollOnce();
    assert.equal((await readChartAlertState(statePath)).events.length, 0, "first poll is a historical baseline");
    assert.equal((await readdir(spoolPath).catch(() => [])).length, 0);

    now = new Date(now.getTime() + 61_000);
    patternStatus = "observed-crossing";
    await monitor.pollOnce();

    const state = await readChartAlertState(statePath);
    const spoolFiles = await readdir(spoolPath);
    assert.equal(requests, 2);
    assert.equal(state.events.length, 1);
    assert.equal(state.events[0].source, "Toss OpenAPI · 1m candles");
    assert.equal(state.events[0].finality, "unknown");
    assert.equal(state.events[0].report_reason, "리포트 집중");
    assert.equal(spoolFiles.length, 1);
    await monitor.pause();
    assert.equal((await readChartAlertState(statePath)).running, false);
  } finally {
    await monitor.pause().catch(() => undefined);
    await rm(folder, { recursive: true, force: true });
  }
});

test("one report-alert monitor owns the shared local poll lease", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-lock-"));
  const statePath = path.join(folder, "report-alerts.json");
  let providerCalls = 0;
  const first = new ChartAlertMonitorService({ statePath, lockPath: `${statePath}.lock`, marketOpen: () => false, providerConfigured: () => true,
    getMinuteBars: async () => { providerCalls += 1; throw new Error("closed market must not request candles"); } });
  const second = new ChartAlertMonitorService({ statePath, lockPath: `${statePath}.lock`, marketOpen: () => false, providerConfigured: () => true });
  try {
    await first.addWatch({ report_business_date: "2026-10-22", stock_code: "005930", stock_name: "삼성전자", report_count: 2, report_reason: "리포트 집중" });
    await first.start();
    await first.pollOnce();
    assert.equal((await second.getStatus()).ownerActiveElsewhere, true);
    await assert.rejects(second.start(), /owned-elsewhere/);
    assert.equal(providerCalls, 0);
  } finally {
    await first.pause().catch(() => undefined);
    await second.pause().catch(() => undefined);
    await rm(folder, { recursive: true, force: true });
  }
});

test("pause keeps the shared poll lease until an in-flight request finishes", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-pause-lock-"));
  const statePath = path.join(folder, "report-alerts.json");
  const pending = [];
  let requests = 0;
  let active = 0;
  let maxActive = 0;
  const makeMonitor = () => new ChartAlertMonitorService({
    statePath, lockPath: `${statePath}.lock`, spoolPath: path.join(folder, "spool"), marketOpen: () => true, providerConfigured: () => true,
    getMinuteBars: async () => {
      requests += 1;
      active += 1;
      maxActive = Math.max(maxActive, active);
      await new Promise((resolve) => pending.push(resolve));
      active -= 1;
      const time = new Date().toISOString();
      return { status: 200, available: true, symbol: "005930", displayName: "삼성전자", bars: [{ time, open: 100, high: 101, low: 99, close: 100, volume: 1 }], source: "Toss OpenAPI · 1m candles", sourceFetchedAt: time, barStatus: "unknown" };
    },
    detectPatterns: () => [],
  });
  const first = makeMonitor();
  const second = makeMonitor();
  const watch = { report_business_date: "2026-10-22", stock_code: "005930", stock_name: "삼성전자", report_count: 2, report_reason: "리포트 집중" };
  const waitFor = async (condition) => {
    for (let attempt = 0; attempt < 200 && !condition(); attempt += 1) await new Promise((resolve) => setTimeout(resolve, 5));
    assert.ok(condition());
  };
  try {
    await first.addWatch(watch);
    await second.addWatch(watch);
    await first.start();
    await waitFor(() => requests === 1);
    assert.equal((await first.pause()).running, false);
    await assert.rejects(second.start(), /chart-alert-monitor-owned-elsewhere/);

    pending[0]();
    let restarted = false;
    for (let attempt = 0; attempt < 200 && !restarted; attempt += 1) {
      try { await second.start(); restarted = true; }
      catch (error) {
        assert.match(error.message, /chart-alert-monitor-owned-elsewhere/);
        await new Promise((resolve) => setTimeout(resolve, 5));
      }
    }
    assert.equal(restarted, true);
    await waitFor(() => requests === 2);
    assert.equal(maxActive, 1);
    await second.pause();
  } finally {
    for (const resolve of pending) resolve();
    await first.pause().catch(() => undefined);
    await second.pause().catch(() => undefined);
    await new Promise((resolve) => setTimeout(resolve, 20));
    await rm(folder, { recursive: true, force: true });
  }
});

test("concurrent starts on one report-alert service keep the acquired lease", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-start-race-"));
  const monitors = [];
  try {
    for (let index = 0; index < 20; index += 1) {
      const statePath = path.join(folder, `${index}.json`);
      const monitor = new ChartAlertMonitorService({ statePath, marketOpen: () => false, providerConfigured: () => true });
      monitors.push(monitor);
      await monitor.addWatch({ report_business_date: "2026-10-22", stock_code: "005930", stock_name: "삼성전자", report_count: 2, report_reason: "리포트 집중" });
      const starts = await Promise.allSettled(Array.from({ length: 8 }, () => monitor.start()));
      assert.ok(starts.some((result) => result.status === "fulfilled"));
      assert.equal((await monitor.pause()).running, false);
    }
  } finally {
    await Promise.all(monitors.map((monitor) => monitor.pause().catch(() => undefined)));
    await new Promise((resolve) => setTimeout(resolve, 20));
    await rm(folder, { recursive: true, force: true });
  }
});

test("concurrent status recovery on one report-alert service keeps the acquired lease", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-status-race-"));
  const monitors = [];
  try {
    for (let index = 0; index < 20; index += 1) {
      const statePath = path.join(folder, `${index}.json`);
      const monitor = new ChartAlertMonitorService({ statePath, marketOpen: () => false, providerConfigured: () => true });
      monitors.push(monitor);
      await monitor.addWatch({ report_business_date: "2026-10-22", stock_code: "005930", stock_name: "삼성전자", report_count: 2, report_reason: "리포트 집중" });
      const state = await readChartAlertState(statePath);
      await writeChartAlertState({ ...state, running: true }, statePath);
      await Promise.all(Array.from({ length: 8 }, () => monitor.getStatus()));
      assert.equal((await monitor.getStatus()).ownerActiveElsewhere, false);
      assert.equal((await monitor.pause()).running, false);
    }
  } finally {
    await Promise.all(monitors.map((monitor) => monitor.pause().catch(() => undefined)));
    await new Promise((resolve) => setTimeout(resolve, 20));
    await rm(folder, { recursive: true, force: true });
  }
});

test("report-alert lock recovery preserves stale-looking locks for manual verification", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "chart-alert-stale-lock-"));
  const lockPath = path.join(folder, "report-alerts.json.lock");
  const contents = JSON.stringify({ pid: 2_000_000_000, token: "old-owner", started_at: "2026-10-22T00:00:00.000Z" });
  try {
    await writeFile(lockPath, contents);
    assert.equal(await acquireChartAlertLock(lockPath), null);
    assert.equal(await readFile(lockPath, "utf8"), contents);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});
