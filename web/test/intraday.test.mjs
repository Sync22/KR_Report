import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isIntradaySnapshot } from "../src/domain/intraday.ts";
import { getIntradaySnapshot } from "../src/server/intraday.ts";

test("intraday snapshot validates selected-date batch summaries only", () => {
  const snapshot = {
    now: "2026-10-11T10:00:00+09:00", timezone: "Asia/Seoul", surface: "web-view", read_only: true,
    business_date: "2026-10-08", batches: [{ business_date: "2026-10-08", created_at: "2026-10-08T09:30:00+09:00", status_label: "발송됨", report_count: 3, stock_count: 2 }],
  };
  assert.equal(isIntradaySnapshot(snapshot, "2026-10-08"), true);
  assert.equal(isIntradaySnapshot({ ...snapshot, batches: [{ ...snapshot.batches[0], business_date: "2026-10-09" }] }, "2026-10-08"), false);
  assert.equal(isIntradaySnapshot({ ...snapshot, operator_status: { scheduler: "running" } }, "2026-10-08"), false);
});

test("intraday SQLite reader matches Python summaries and leaves the database unchanged", () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const directory = mkdtempSync(join(tmpdir(), "stock-monitor-next-intraday-"));
  const databasePath = join(directory, "intraday.db");
  const database = new DatabaseSync(databasePath);
  database.exec(`
    CREATE TABLE intraday_alert_batches (
      batch_id TEXT PRIMARY KEY, business_date TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL
    );
    CREATE TABLE intraday_alert_batch_reports (batch_id TEXT NOT NULL, report_identity_key TEXT NOT NULL);
    CREATE TABLE reports (identity_key TEXT PRIMARY KEY, stock_code TEXT, stock_name TEXT);
    INSERT INTO intraday_alert_batches VALUES
      ('batch-b', '2026-10-08', '2026-10-08T09:40:00+09:00', 'pending'),
      ('batch-a', '2026-10-08', '2026-10-08T09:30:00+09:00', 'sent'),
      ('batch-c', '2026-10-08', '2026-10-08T09:50:00+09:00', 'failed'),
      ('other-date', '2026-10-09', '2026-10-09T09:30:00+09:00', 'sent');
    INSERT INTO reports VALUES
      ('r1', '005930', '삼성전자'), ('r2', '005930', '삼성전자'),
      ('r3', ' ', 'DL이앤씨'), ('r4', '373220', 'LG에너지솔루션');
    INSERT INTO intraday_alert_batch_reports VALUES
      ('batch-a', 'r1'), ('batch-a', 'r2'), ('batch-a', 'r3'), ('batch-c', 'r4'), ('other-date', 'r1');
  `);
  database.close();

  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousTimezone = process.env.STOCK_MONITOR_TIMEZONE;
  const before = statSync(databasePath);
  const fixedNow = new Date("2026-10-12T00:00:00.000Z");
  process.env.STOCK_MONITOR_DB_PATH = databasePath;
  process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
  try {
    const snapshot = getIntradaySnapshot("2026-10-08", fixedNow);
    assert.equal(isIntradaySnapshot(snapshot, "2026-10-08"), true);
    assert.deepEqual(snapshot.batches.map(({ business_date, created_at, status_label, report_count, stock_count }) => ({
      business_date, created_at, status_label, report_count, stock_count,
    })), [
      { business_date: "2026-10-08", created_at: "2026-10-08T09:30:00+09:00", status_label: "발송됨", report_count: 3, stock_count: 2 },
      { business_date: "2026-10-08", created_at: "2026-10-08T09:40:00+09:00", status_label: "대기", report_count: 0, stock_count: 0 },
      { business_date: "2026-10-08", created_at: "2026-10-08T09:50:00+09:00", status_label: "확인필요", report_count: 1, stock_count: 1 },
    ]);
    const after = statSync(databasePath);
    assert.deepEqual({ size: after.size, mtimeMs: after.mtimeMs }, { size: before.size, mtimeMs: before.mtimeMs });

    const pythonScript = `
import json, sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_intraday_snapshot
from stock_monitor.db.repository import StockMonitorRepository
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
config = SimpleNamespace(timezone="Asia/Seoul")
snapshot = build_web_view_intraday_snapshot(config, repository, business_date=date.fromisoformat(sys.argv[2]), now=datetime.fromisoformat("2026-10-12T00:00:00+00:00"))
print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, "2026-10-08"], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python intraday DTO comparison failed");
    const pythonSnapshot = JSON.parse(python.stdout);
    const withoutNow = ({ now: _now, ...value }) => value;
    assert.deepEqual(withoutNow(snapshot), withoutNow(pythonSnapshot));
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = previousTimezone;
    rmSync(directory, { recursive: true, force: true });
  }
});
