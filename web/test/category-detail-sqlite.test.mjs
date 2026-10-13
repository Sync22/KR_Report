import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isCategoryDetailSnapshot } from "../src/domain/category-rotation.ts";

test("category detail reads temporary SQLite exactly like the Python builder", async () => {
  const detailService = await import("../src/server/category-detail.ts");
  const categoryRoute = await import("../src/app/api/category/route.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-category-detail-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
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
      CREATE TABLE stock_theme_memberships (
        theme_code TEXT NOT NULL, theme_name TEXT NOT NULL, stock_code TEXT NOT NULL,
        stock_name TEXT, updated_at TEXT NOT NULL, source TEXT NOT NULL
      );
      CREATE TABLE stock_market_daily (
        business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT NOT NULL,
        market TEXT NOT NULL, section_name TEXT, close_price INTEGER, change_amount INTEGER,
        change_percent REAL, open_price INTEGER, high_price INTEGER, low_price INTEGER,
        volume INTEGER, turnover INTEGER, market_cap INTEGER, listed_shares INTEGER,
        fetched_at TEXT NOT NULL, source TEXT NOT NULL
      );
    `);

    const addSummary = database.prepare("INSERT INTO daily_stock_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    const add = (date, code, name, mentions, opinion = "hold") => addSummary.run(
      date, name, code, mentions, "증권사 A", null, null, opinion, `${date}T20:00:00+09:00`,
    );
    for (const date of ["2026-10-12", "2026-10-09"]) {
      add(date, "005930", "삼성전자", 5, "buy");
      add(date, "000660", "SK하이닉스", 3);
      add(date, "035420", "NAVER", 3);
      add(date, "068270", "셀트리온", 2);
    }
    add("2026-10-12", "777777", "Legacy mapped without dated key", 1);
    add("2026-10-04", "111111", "Legacy sector", 4);
    add("2026-10-04", "222222", "Legacy theme", 3);
    add("2026-10-04", null, "Unknown sector", 6, null);

    const addCatalog = database.prepare("INSERT INTO category_master VALUES (?, ?, ?, ?)");
    addCatalog.run("sector", "S1", "반도체", 1);
    addCatalog.run("sector", "S2", "반도체", 1);
    addCatalog.run("sector", "D1", "반도체", 0);
    addCatalog.run("theme", "T1", "AI반도체", 1);
    const addSnapshot = database.prepare("INSERT INTO category_membership_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    for (const snapshotDate of ["2026-10-08", "2026-10-10"]) {
      addSnapshot.run(snapshotDate, "sector", "S1", "반도체", "005930", "삼성전자", `${snapshotDate}T20:00:00+09:00`, "fixture");
      addSnapshot.run(snapshotDate, "sector", "S1", "반도체", "000660", "SK하이닉스", `${snapshotDate}T20:00:00+09:00`, "fixture");
      addSnapshot.run(snapshotDate, "sector", "S2", "반도체", "005930", "삼성전자", `${snapshotDate}T20:00:00+09:00`, "fixture");
      addSnapshot.run(snapshotDate, "sector", "S2", "반도체", "035420", "NAVER", `${snapshotDate}T20:00:00+09:00`, "fixture");
      addSnapshot.run(snapshotDate, "sector", "D1", "반도체", "068270", "셀트리온", `${snapshotDate}T20:00:00+09:00`, "fixture");
    }
    addSnapshot.run("2026-10-09", "theme", "T1", "AI반도체", "000660", "SK하이닉스", "2026-10-09T20:00:00+09:00", "fixture");

    database.prepare("INSERT INTO stock_metadata VALUES (?, ?, ?, ?, ?, ?)").run("111111", "Legacy sector", "legacy-sector", "legacy-sector", "2026-10-04T20:00:00+09:00", "fixture");
    database.prepare("INSERT INTO stock_metadata VALUES (?, ?, ?, ?, ?, ?)").run("777777", "Legacy mapped without dated key", "no-snapshot-key", "NoSnapshotKey", "2026-10-12T20:00:00+09:00", "fixture");
    database.prepare("INSERT INTO stock_theme_memberships VALUES (?, ?, ?, ?, ?, ?)").run("legacy-theme", "legacy-theme", "222222", "Legacy theme", "2026-10-04T20:00:00+09:00", "fixture");

    const addMarket = database.prepare("INSERT INTO stock_market_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    addMarket.run("2026-10-12", "005930", "삼성전자", "KOSPI", null, 70000, null, 1.25, null, null, null, 1000, 70000000, null, null, "2026-10-12T20:00:00+09:00", "toss_openapi");
    addMarket.run("2026-10-12", "000660", "SK하이닉스", "KOSPI", null, null, null, -1.5, null, null, null, null, null, null, null, "2026-10-12T20:00:00+09:00", "toss_openapi");
    addMarket.run("2026-10-12", "035420", "NAVER", "KOSDAQ", null, 10000, null, 2, null, null, null, 100, 1000000, null, null, "2026-10-12T20:00:00+09:00", "krx");
    addMarket.run("2026-10-11", "035420", "NAVER", "KOSDAQ", null, 9900, null, 1, null, null, null, 90, 900000, null, null, "2026-10-11T20:00:00+09:00", "toss_openapi");
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const cases = [
      { date: "2026-10-12", type: "sector", name: "S1", pythonName: "S1", pythonDisplayName: null },
      { date: "2026-10-12", type: "sector", displayName: "반도체", publicId: "sector|반도체|2026-10-10", pythonName: "", pythonDisplayName: "반도체" },
      { date: "2026-10-12", type: "sector", name: "D1", pythonName: "D1", pythonDisplayName: null },
      { date: "2026-10-12", type: "sector", displayName: "없는 분류", pythonName: "", pythonDisplayName: "없는 분류" },
      { date: "2026-10-09", type: "sector", displayName: "반도체", pythonName: "", pythonDisplayName: "반도체" },
      { date: "2026-10-04", type: "sector", name: "legacy-sector", pythonName: "legacy-sector", pythonDisplayName: null, publicId: "sector|legacy-sector|fallback" },
      { date: "2026-10-04", type: "theme", name: "legacy-theme", pythonName: "legacy-theme", pythonDisplayName: null },
      { date: "2026-10-04", type: "sector", name: "N/A", pythonName: "N/A", pythonDisplayName: null },
      { date: "2026-10-12", type: "sector", name: "S1", publicId: "sector|반도체|2026-10-10", pythonName: "S1", pythonDisplayName: "반도체" },
      { date: "2026-10-12", type: "sector", name: "NoSnapshotKey", pythonName: "NoSnapshotKey", pythonDisplayName: null },
    ];
    const beforeRead = statSync(databasePath);
    const serviceSnapshots = cases.map((item) => detailService.getCategoryDetailSnapshot(
      item.date, item.type, item.pythonName, item.pythonDisplayName,
    ));
    const nextSnapshots = await Promise.all(cases.map(async (item) => {
      const query = new URLSearchParams({ date: item.date, type: item.type });
      if (item.name) query.set("name", item.name);
      if (item.displayName) query.set("display_name", item.displayName);
      if (item.publicId) query.set("public_category_id", item.publicId);
      const response = categoryRoute.GET(new Request(`http://next.local/api/category?${query}`));
      assert.equal(response.status, 200);
      return response.json();
    }));
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = `
import json, sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_category_detail_snapshot
from stock_monitor.db.repository import StockMonitorRepository
config = SimpleNamespace(timezone="Asia/Seoul")
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
cases = json.loads(sys.argv[2])
snapshots = [build_web_view_category_detail_snapshot(config, repository, business_date=date.fromisoformat(item["date"]), category_type=item["type"], category_name=item["pythonName"], category_display_name=item["pythonDisplayName"], now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for item in cases]
print(json.dumps(snapshots, ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, JSON.stringify(cases)], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout);
    const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
    assert.deepEqual(nextSnapshots.map(withoutNow), serviceSnapshots.map(withoutNow));
    assert.deepEqual(nextSnapshots.map(withoutNow), pythonSnapshots.map(withoutNow));

    const [key, display, disabledKey, missingDisplay, stale, legacySector, legacyTheme, missingLabel] = nextSnapshots;
    assert.equal(isCategoryDetailSnapshot(key, "2026-10-12", "sector", "S1"), true);
    assert.equal(key.category_key, "S1");
    assert.equal(key.display_name, "S1");
    assert.equal(key.public_category_id, "sector|S1|2026-10-10");
    assert.deepEqual(key.stocks.map((item) => item.stock_code), ["005930", "000660"]);
    assert.deepEqual(display.stocks.map((item) => item.stock_code), ["005930", "035420", "000660", "068270"]);
    assert.equal(display.stocks[0].market_reference.close_price, 70000);
    assert.equal(display.stocks[1].market_reference, null);
    assert.equal(display.stocks[2].market_reference.close_price, null);
    assert.equal(disabledKey.stocks.length, 0);
    assert.equal(missingDisplay.stocks.length, 0);
    assert.equal(stale.snapshot_date, "2026-10-08");
    assert.equal(legacySector.mapping_source, "latest_mapping_fallback");
    assert.equal(legacySector.public_category_id, "sector|legacy-sector|fallback");
    assert.equal(legacyTheme.mapping_source, "latest_mapping_fallback");
    assert.equal(missingLabel.category_display_name, "업종 미확인");
    assert.equal(missingLabel.stocks[0].stock_code, null);
    assert.equal(missingLabel.stocks[0].dominant_opinion, null);
    assert.equal(missingLabel.stocks[0].market_reference, null);
    assert.equal(nextSnapshots[8].category_name, "S1");
    assert.equal(nextSnapshots[8].display_name, "반도체");
    assert.equal(nextSnapshots[9].mapping_source, "dated_snapshot");
    assert.equal(nextSnapshots[9].snapshot_date, "2026-10-10");
    assert.equal(nextSnapshots[9].public_category_id, "sector|NoSnapshotKey|2026-10-10");
    assert.equal(nextSnapshots[9].stocks[0].stock_code, "777777");

    for (const response of [categoryRoute.HEAD(), categoryRoute.OPTIONS(), categoryRoute.POST(), categoryRoute.PUT(), categoryRoute.PATCH(), categoryRoute.DELETE()]) {
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(categoryRoute.GET(new Request("http://next.local/api/category?date=invalid&type=sector&name=S1")).status, 400);
    assert.equal(categoryRoute.GET(new Request("http://next.local/api/category?date=2026-10-12&type=theme&name=S1&public_category_id=sector%7C반도체%7C2026-10-10")).status, 400);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* The fixture closes before it is opened read-only. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
