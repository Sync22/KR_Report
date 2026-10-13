import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { getRotationOverlaySnapshot } from "../src/server/rotation-overlay.ts";

const businessDate = "2026-10-08";

function makeFixture(databasePath) {
  const database = new DatabaseSync(databasePath);
  database.exec(`
    CREATE TABLE daily_stock_summaries (
      business_date TEXT NOT NULL, stock_name TEXT NOT NULL, stock_code TEXT,
      mention_count INTEGER NOT NULL, broker_display TEXT NOT NULL,
      target_price_min INTEGER, target_price_max INTEGER,
      dominant_opinion TEXT, generated_at TEXT NOT NULL
    );
    CREATE TABLE category_membership_snapshots (
      snapshot_date TEXT NOT NULL, category_type TEXT NOT NULL, category_key TEXT NOT NULL,
      display_name TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT,
      fetched_at TEXT NOT NULL, source TEXT NOT NULL
    );
    CREATE TABLE category_master (
      category_type TEXT NOT NULL, category_key TEXT NOT NULL,
      display_name TEXT NOT NULL, enabled INTEGER NOT NULL
    );
    CREATE TABLE stock_metadata (
      stock_code TEXT PRIMARY KEY, stock_name TEXT, sector_code TEXT,
      sector_name TEXT, updated_at TEXT NOT NULL, source TEXT NOT NULL
    );
    CREATE TABLE stock_market_daily (
      business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT NOT NULL,
      market TEXT NOT NULL, section_name TEXT, close_price INTEGER, change_amount INTEGER,
      change_percent REAL, open_price INTEGER, high_price INTEGER, low_price INTEGER,
      volume INTEGER, turnover INTEGER, market_cap INTEGER, listed_shares INTEGER,
      fetched_at TEXT NOT NULL, source TEXT NOT NULL
    );
    CREATE TABLE etf_daily_snapshots (
      business_date TEXT NOT NULL, etf_code TEXT NOT NULL, etf_name TEXT NOT NULL,
      close_price INTEGER, change_amount INTEGER, change_percent REAL, nav REAL,
      open_price INTEGER, high_price INTEGER, low_price INTEGER, volume INTEGER,
      turnover INTEGER, market_cap INTEGER, net_assets_total INTEGER, listed_shares INTEGER,
      underlying_index_name TEXT, underlying_index_close REAL,
      underlying_index_change_amount REAL, underlying_index_change_percent REAL,
      fetched_at TEXT NOT NULL, source TEXT NOT NULL
    );
  `);

  const addSummary = database.prepare("INSERT INTO daily_stock_summaries VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?)");
  const summary = (date, code, name, mentions, brokers = "증권사 A") =>
    addSummary.run(date, name, code, mentions, brokers, `${date}T20:00:00+09:00`);
  summary(businessDate, "005930", "삼성전자", 6, "NH투자증권(2), 삼성증권");
  summary(businessDate, "000660", "SK하이닉스", 6, "한국투자증권");
  summary(businessDate, "035420", "NAVER", 3);
  summary(businessDate, "068270", "셀트리온", 20);
  summary("2026-10-07", "005930", "삼성전자", 5);
  summary("2026-10-07", "000660", "SK하이닉스", 4);
  summary("2026-10-07", "068270", "셀트리온", 20);

  const addMaster = database.prepare("INSERT INTO category_master VALUES ('sector', ?, ?, ?)");
  addMaster.run("S1", "반도체와반도체장비", 1);
  addMaster.run("S2", "반도체와반도체장비", 1);
  addMaster.run("D1", "제약", 0);
  const addMembership = database.prepare("INSERT INTO category_membership_snapshots VALUES (?, 'sector', ?, ?, ?, ?, ?, 'fixture')");
  for (const [key, displayName, code, name] of [
    ["S1", "반도체와반도체장비", "005930", "삼성전자"], ["S1", "반도체와반도체장비", "000660", "SK하이닉스"],
    ["S2", "반도체와반도체장비", "005930", "삼성전자"], ["S2", "반도체와반도체장비", "035420", "NAVER"],
    ["D1", "제약", "068270", "셀트리온"],
  ]) addMembership.run(businessDate, key, displayName, code, name, `${businessDate}T20:00:00+09:00`);

  const addMetadata = database.prepare("INSERT INTO stock_metadata VALUES (?, ?, ?, ?, ?, 'fixture')");
  addMetadata.run("005930", "삼성전자", "A1", "반도체와반도체장비", `${businessDate}T20:00:00+09:00`);
  addMetadata.run("000660", "SK하이닉스", "A1", "반도체와반도체장비", `${businessDate}T20:00:00+09:00`);
  addMetadata.run("035420", "NAVER", "A1", "반도체와반도체장비", `${businessDate}T20:00:00+09:00`);
  addMetadata.run("068270", "셀트리온", "D1", "제약", `${businessDate}T20:00:00+09:00`);

  const addMarket = database.prepare("INSERT INTO stock_market_daily VALUES (?, ?, ?, ?, NULL, ?, NULL, ?, NULL, NULL, NULL, NULL, ?, NULL, NULL, ?, ?)");
  addMarket.run(businessDate, "005930", "삼성전자", "KOSPI", 70000, 1.25, 400_000_000, `${businessDate}T20:00:00+09:00`, "toss_openapi");
  addMarket.run(businessDate, "000660", "SK하이닉스", "KOSPI", 200000, -1.5, 900_000_000, `${businessDate}T20:00:00+09:00`, "toss_openapi");
  addMarket.run(businessDate, "035420", "NAVER", "KOSDAQ", 10000, 2, 50_000_000, `${businessDate}T20:00:00+09:00`, "krx");

  const addEtf = database.prepare("INSERT INTO etf_daily_snapshots VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, NULL, ?, NULL, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)");
  addEtf.run(businessDate, "069500", "KODEX 200", 40000, 1, 500_000_000, "KOSPI 200", `${businessDate}T20:00:00+09:00`, "toss_openapi");
  addEtf.run(businessDate, "069500", "KODEX 200 (KRX)", 39900, 0.8, 9_000_000_000, "KOSPI 200", `${businessDate}T20:00:00+09:00`, "krx");
  addEtf.run(businessDate, "102110", "TIGER 200", 30000, 0.5, 100_000_000, "KOSPI 200", `${businessDate}T20:00:00+09:00`, "toss_openapi");
  addEtf.run("2026-10-07", "069500", "KODEX 200", 39000, 1, 9_000_000_000, "KOSPI 200", "2026-10-07T20:00:00+09:00", "toss_openapi");
  database.close();
}

function withoutImagePath(payload) {
  const { path: _path, ...image } = payload.image;
  return { ...payload, image };
}

test("rotation overlay stays equal to the Python DTO for dated snapshots and fallback", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-rotation-overlay-"));
  const databasePath = join(tempRoot, "fixture.db");
  const coordinatesPath = join(tempRoot, "rotation_overlay_coordinates.json");
  const aliasPath = join(tempRoot, "rotation_image_aliases.json");
  const etfPath = join(tempRoot, "rotation_etf_candidates.json");
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousCoordinatesPath = process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH;
  try {
    makeFixture(databasePath);
    writeFileSync(coordinatesPath, JSON.stringify({
      image: { path: "example/Cycle.jpg", width: 1376, height: 768 },
      coordinates: [{ display_name: "반도체", x: 490, y: 210, radius: 58, label: "반도체" }],
    }));
    writeFileSync(aliasPath, JSON.stringify({ aliases: [{
      status: "active", category_type: "sector", category_display_name: "반도체와반도체장비",
      coordinate_display_name: "반도체", rotation_label: "칩", mapping_basis: "manual_alias",
    }] }));
    writeFileSync(etfPath, JSON.stringify({ mappings: [
      { status: "active", category_type: "sector", category_display_name: "반도체와반도체장비", etf_codes: ["069500", "102110"] },
      { status: "hold", category_type: "sector", category_display_name: "반도체와반도체장비", etf_codes: ["396500"] },
    ] }));
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH = coordinatesPath;

    const cases = [businessDate, "2026-10-07"];
    const beforeRead = statSync(databasePath);
    const nextSnapshots = cases.map((date) => getRotationOverlaySnapshot(date));
    const pythonScript = `
import json, sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_rotation_overlay_snapshot
from stock_monitor.db.repository import StockMonitorRepository
config = SimpleNamespace(rotation_overlay_coordinates_path=Path(sys.argv[2]))
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
print(json.dumps([build_web_view_rotation_overlay_snapshot(config, repository, business_date=date.fromisoformat(value)) for value in json.loads(sys.argv[3])], ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, coordinatesPath, JSON.stringify(cases)], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout).map(withoutImagePath);
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.deepEqual(nextSnapshots, pythonSnapshots);
    assert.equal(nextSnapshots[0].highlights[0].candidate_stocks[0].stock_code, "000660");
    assert.equal(nextSnapshots[0].highlights[0].candidate_stocks[1].broker_count_label, "증권사 2곳");
    assert.deepEqual(nextSnapshots[0].highlights[0].candidate_etfs.map((item) => item.etf_code), ["069500", "102110"]);
    assert.equal(nextSnapshots[0].highlights[0].candidate_etfs[0].etf_name, "KODEX 200");
    assert.equal(nextSnapshots[1].highlights[0].public_category_id, "sector|반도체와반도체장비|fallback");

  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousCoordinatesPath === undefined) delete process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH;
    else process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH = previousCoordinatesPath;
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
