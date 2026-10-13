import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { buildDailyBaseSnapshot } from "../src/server/daily-base.ts";

function runPython(projectRoot, script, args, label) {
  const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
  const result = spawnSync("python", ["-c", script, ...args], {
    cwd: projectRoot,
    env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
    encoding: "utf8",
    timeout: 30000,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message || label);
  return result.stdout;
}

function addFixtureRows(database) {
  const addSummary = database.prepare([
    "INSERT INTO daily_stock_summaries (business_date, stock_name, stock_code, mention_count, broker_display,",
    "target_price_min, target_price_max, dominant_opinion, generated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
  ].join("\n"));
  const summary = (date, name, code, mentions, min, max, opinion) =>
    addSummary.run(date, name, code, mentions, "증권사 미확인", min, max, opinion, date + "T20:00:00+09:00");
  summary("2026-10-08", "삼성전자", "005930", 3, 65000, 80000, "buy");
  summary("2026-10-08", "SK하이닉스", "000660", 2, null, null, "hold");
  summary("2026-10-08", "NAVER", "035420", 1, 40000, 45000, "sell");
  summary("2026-10-08", "LG화학", "051910", 3, 250000, 300000, "hold");
  summary("2026-10-08", "셀트리온", "068270", 5, null, null, "buy");
  summary("2026-10-08", "미확인 종목", null, 1, null, null, "hold");
  summary("2026-10-06", "삼성전자", "005930", 2, null, null, "hold");
  summary("2026-10-06", "NAVER", "035420", 1, null, null, "sell");
  summary("2026-10-06", "미확인 종목", null, 1, null, null, "hold");
  summary("2026-10-09", "미래 행", "111111", 20, 1, 2, "buy");

  const addMetadata = database.prepare([
    "INSERT INTO stock_metadata (stock_code, stock_name, sector_code, sector_name, updated_at, source)",
    "VALUES (?, ?, ?, ?, ?, 'fixture')",
  ].join("\n"));
  addMetadata.run("005930", "삼성전자", "S1", "반도체와반도체장비", "2026-10-08T20:00:00+09:00");
  addMetadata.run("000660", "SK하이닉스", "S1", "반도체와반도체장비", "2026-10-08T20:00:00+09:00");
  addMetadata.run("035420", "NAVER", "S3", "인터넷", "2026-10-08T20:00:00+09:00");
  addMetadata.run("051910", "LG화학", "S2", "반도체와반도체장비", "2026-10-08T20:00:00+09:00");
  addMetadata.run("068270", "셀트리온", "D1", "제약", "2026-10-08T20:00:00+09:00");

  const addTheme = database.prepare([
    "INSERT INTO stock_theme_memberships (theme_code, theme_name, stock_code, stock_name, updated_at, source)",
    "VALUES (?, ?, ?, ?, ?, 'fixture')",
  ].join("\n"));
  addTheme.run("T1", "AI반도체", "005930", "삼성전자", "2026-10-08T20:00:00+09:00");
  addTheme.run("T1", "AI반도체", "000660", "SK하이닉스", "2026-10-08T20:00:00+09:00");
  addTheme.run("T2", "2차전지", "051910", "LG화학", "2026-10-08T20:00:00+09:00");

  const addMaster = database.prepare([
    "INSERT INTO category_master (category_type, category_key, display_name, source, enabled, updated_at)",
    "VALUES (?, ?, ?, 'fixture', ?, ?)",
  ].join("\n"));
  for (const [type, key, name, enabled] of [
    ["sector", "S1", "반도체와반도체장비", 1],
    ["sector", "S2", "반도체와반도체장비", 1],
    ["sector", "S3", "인터넷", 1],
    ["sector", "D1", "제약", 0],
    ["theme", "T1", "AI반도체", 1],
    ["theme", "T2", "2차전지", 1],
  ]) addMaster.run(type, key, name, enabled, "2026-10-08T20:00:00+09:00");

  const addMembership = database.prepare([
    "INSERT INTO category_membership_snapshots (snapshot_date, category_type, category_key, display_name,",
    "stock_code, stock_name, fetched_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'fixture')",
  ].join("\n"));
  const membership = (date, type, key, displayName, code, name) =>
    addMembership.run(date, type, key, displayName, code, name, date + "T20:00:00+09:00");
  membership("2026-10-07", "sector", "S1", "반도체와반도체장비", "005930", "삼성전자");
  membership("2026-10-07", "sector", "S1", "반도체와반도체장비", "000660", "SK하이닉스");
  membership("2026-10-07", "sector", "S2", "반도체와반도체장비", "005930", "삼성전자");
  membership("2026-10-07", "sector", "S2", "반도체와반도체장비", "051910", "LG화학");
  membership("2026-10-07", "sector", "S3", "인터넷", "035420", "NAVER");
  membership("2026-10-07", "sector", "D1", "제약", "068270", "셀트리온");
  membership("2026-10-08", "theme", "T1", "AI반도체", "005930", "삼성전자");
  membership("2026-10-08", "theme", "T1", "AI반도체", "000660", "SK하이닉스");
  membership("2026-10-08", "theme", "T2", "2차전지", "051910", "LG화학");
  membership("2026-10-10", "sector", "S1", "미래 반도체", "005930", "삼성전자");

  const addMarket = database.prepare([
    "INSERT INTO stock_market_daily (business_date, stock_code, stock_name, market, close_price, change_percent,",
    "volume, turnover, fetched_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
  ].join("\n"));
  addMarket.run("2026-10-08", "005930", "삼성전자", "KOSPI", 70000, 1.25, 1000, 70000000, "2026-10-08T20:00:00+09:00", "toss_openapi");
  addMarket.run("2026-10-08", "005930", "삼성전자", "KOSPI", 69900, -9.9, 2000, 990000000, "2026-10-08T20:00:00+09:00", "krx");
  addMarket.run("2026-10-08", "000660", "SK하이닉스", "KOSPI", 190000, 9.9, 2000, 900000000, "2026-10-08T20:00:00+09:00", "krx");
  addMarket.run("2026-10-07", "035420", "NAVER", "KOSDAQ", 10000, 1.5, 500, 5000000, "2026-10-07T20:00:00+09:00", "toss_openapi");
}

test("daily base projection matches Python for dated and legacy category mappings without changing SQLite", () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-daily-base-"));
  const databasePath = join(tempRoot, "fixture.db");
  const businessDates = ["2026-10-08", "2026-10-06"];
  const pythonSetup = [
    "import sys",
    "from pathlib import Path",
    "from stock_monitor.db.repository import StockMonitorRepository",
    "StockMonitorRepository(Path(sys.argv[1]), timezone='Asia/Seoul').initialize()",
  ].join("\n");
  const pythonDaily = [
    "import json, sys",
    "from datetime import date, datetime",
    "from pathlib import Path",
    "from stock_monitor.cli import build_web_view_daily_snapshot",
    "from stock_monitor.config import RuntimeConfig",
    "from stock_monitor.db.repository import StockMonitorRepository",
    "root, database_path = Path(sys.argv[1]), Path(sys.argv[2])",
    "business_dates = json.loads(sys.argv[3])",
    "config = RuntimeConfig.from_env(root_dir=root, db_path=database_path, headless=True)",
    "repository = StockMonitorRepository(database_path, timezone=config.timezone)",
    "keys = ('report_count', 'summary_stock_count', 'mapping_notice', 'category_contract', 'stocks', 'sectors', 'themes', 'market_mood', 'watch_candidates')",
    "snapshots = [build_web_view_daily_snapshot(config, repository, business_date=date.fromisoformat(value), now=datetime.fromisoformat('2026-10-12T09:00:00+09:00'), include_observation_summary=False) for value in business_dates]",
    "print(json.dumps([{key: snapshot[key] for key in keys} for snapshot in snapshots], ensure_ascii=False, separators=(',', ':')))",
  ].join("\n");

  try {
    runPython(projectRoot, pythonSetup, [databasePath], "Fixture database initialization failed");
    const writer = new DatabaseSync(databasePath);
    try {
      addFixtureRows(writer);
    } finally {
      writer.close();
    }

    const beforeRead = statSync(databasePath);
    const database = new DatabaseSync(databasePath, { readOnly: true });
    let snapshots;
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      snapshots = businessDates.map((businessDate) => buildDailyBaseSnapshot(database, businessDate));
      database.exec("COMMIT");
    } catch (error) {
      try { database.exec("ROLLBACK"); } catch { /* The transaction may already be closed. */ }
      throw error;
    } finally {
      database.close();
    }
    assert.deepEqual(
      { size: statSync(databasePath).size, mtimeMs: statSync(databasePath).mtimeMs },
      { size: beforeRead.size, mtimeMs: beforeRead.mtimeMs },
    );

    const pythonSnapshots = JSON.parse(runPython(
      projectRoot,
      pythonDaily,
      [tempRoot, databasePath, JSON.stringify(businessDates)],
      "Python daily snapshot comparison failed",
    ));
    assert.deepEqual(snapshots, pythonSnapshots);
    assert.equal(snapshots[0].stocks.find((item) => item.stock_code === "005930").market_reference.close_price, 70000);
    assert.equal(snapshots[0].stocks.find((item) => item.stock_code === "000660").market_reference, null);
    assert.equal(snapshots[0].stocks.find((item) => item.stock_code === "005930").primary_category.category_type, "sector");
    assert.deepEqual(snapshots[0].category_contract.snapshot_dates, ["2026-10-08", "2026-10-07"]);
    assert.equal(snapshots[0].sectors.some((item) => item.display_name === "미래 반도체"), false);
    assert.deepEqual(snapshots[0].watch_candidates.map((item) => item.stock_name), ["LG화학", "삼성전자"]);
    assert.equal(snapshots[1].category_contract.mapping_basis, "latest_mapping_fallback");
    assert.equal(snapshots[1].market_mood.active_sector_count, 2);
    assert.deepEqual(
      { size: statSync(databasePath).size, mtimeMs: statSync(databasePath).mtimeMs },
      { size: beforeRead.size, mtimeMs: beforeRead.mtimeMs },
    );
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
