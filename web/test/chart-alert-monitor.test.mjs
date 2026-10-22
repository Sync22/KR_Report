import assert from "node:assert/strict";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { ChartAlertMonitorService } from "../src/server/chart-alert-monitor.ts";
import { readChartAlertState } from "../src/server/chart-alert-store.ts";

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
