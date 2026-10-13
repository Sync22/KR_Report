import assert from "node:assert/strict";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { buildArchiveSnapshot, getArchiveSnapshot, parseArchiveLimit } from "../src/server/archive.ts";

function seedArchiveDatabase(database) {
  database.exec(`
    CREATE TABLE reports (business_date TEXT NOT NULL);
    CREATE TABLE daily_stock_summaries (business_date TEXT NOT NULL);
    CREATE TABLE report_linked_news_evidence (target_date TEXT NOT NULL, run_id TEXT NOT NULL);
    CREATE TABLE category_master (category_type TEXT NOT NULL, category_key TEXT NOT NULL, enabled INTEGER NOT NULL);
    CREATE TABLE category_membership_snapshots (category_type TEXT NOT NULL, category_key TEXT NOT NULL, snapshot_date TEXT NOT NULL);

    INSERT INTO reports VALUES ('2026-10-08'), ('2026-10-08'), ('2026-10-07');
    INSERT INTO daily_stock_summaries VALUES ('2026-10-08'), ('2026-10-06');
    INSERT INTO report_linked_news_evidence VALUES
      ('2026-10-08', 'run-a'), ('2026-10-08', 'run-a'), ('2026-10-08', 'run-b');
    INSERT INTO category_master VALUES ('sector', 'semi', 1), ('theme', 'chip', 1);
    INSERT INTO category_membership_snapshots VALUES
      ('sector', 'semi', '2026-10-08'), ('sector', 'semi', '2026-10-07'), ('theme', 'chip', '2026-10-08');
  `);
}

test("archive builder preserves Python date counts, news run counts, and dated category mapping", () => {
  const database = new DatabaseSync(":memory:");
  try {
    seedArchiveDatabase(database);

    const snapshot = buildArchiveSnapshot(database, 2, new Date("2026-10-11T00:00:00.000Z"), "Asia/Seoul");

    assert.equal(snapshot.date_count, 2);
    assert.equal(snapshot.latest_business_date, "2026-10-08");
    assert.deepEqual(snapshot.dates, [
      {
        business_date: "2026-10-08",
        report_count: 2,
        summary_stock_count: 1,
        news_observation_count: 2,
        category_mapping: {
          mapping_basis: "dated_snapshot",
          sector_snapshot_date: "2026-10-08",
          theme_snapshot_date: "2026-10-08",
          label: "카테고리 스냅샷",
        },
      },
      {
        business_date: "2026-10-07",
        report_count: 1,
        summary_stock_count: 0,
        news_observation_count: 0,
        category_mapping: {
          mapping_basis: "latest_mapping_fallback",
          sector_snapshot_date: "2026-10-07",
          theme_snapshot_date: null,
          label: "최신 저장 분류",
        },
      },
    ]);
    assert.deepEqual(snapshot.category_mapping_summary, {
      dated_snapshot_count: 1,
      fallback_count: 1,
      notice: "일부 날짜는 과거 source-date 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다.",
    });
    assert.equal(snapshot.read_only, true);
  } finally {
    database.close();
  }
});

test("archive loader reads the configured database without changing it or using the Python bridge", () => {
  const directory = mkdtempSync(join(tmpdir(), "stock-monitor-next-archive-"));
  const databasePath = join(directory, "archive.db");
  const fixtureDatabase = new DatabaseSync(databasePath);
  seedArchiveDatabase(fixtureDatabase);
  fixtureDatabase.close();
  const before = statSync(databasePath);
  const fileStateBefore = { size: before.size, modified: before.mtimeMs };
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousPythonUrl = process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL;
  const previousTimezone = process.env.STOCK_MONITOR_TIMEZONE;

  process.env.STOCK_MONITOR_DB_PATH = databasePath;
  process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL = "https://invalid.example";
  process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
  try {
    const snapshot = getArchiveSnapshot(2);
    assert.equal(snapshot.latest_business_date, "2026-10-08");
    assert.equal(snapshot.dates[0].news_observation_count, 2);
    assert.equal(snapshot.dates[1].category_mapping.mapping_basis, "latest_mapping_fallback");
    const after = statSync(databasePath);
    assert.deepEqual({ size: after.size, modified: after.mtimeMs }, fileStateBefore);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousPythonUrl === undefined) delete process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL;
    else process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL = previousPythonUrl;
    if (previousTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = previousTimezone;
    rmSync(directory, { recursive: true, force: true });
  }
});

test("archive limit defaults on invalid input and stays within the Python bounds", () => {
  assert.equal(parseArchiveLimit(null), 20);
  assert.equal(parseArchiveLimit("not-a-number"), 20);
  assert.equal(parseArchiveLimit("0"), 1);
  assert.equal(parseArchiveLimit("999"), 100);
});
