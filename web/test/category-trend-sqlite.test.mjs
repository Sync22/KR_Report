import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isCategoryTrendSnapshot } from "../src/domain/category-rotation.ts";
import * as categoryTrendRoute from "../src/app/api/category-trend/route.ts";

test("category trend uses dated snapshots and legacy fallback exactly like Python", async () => {
  const { getCategoryTrendSnapshot, parseCategoryTrendLimit } = await import("../src/server/category-trend.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-category-trend-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    database.exec(`
      CREATE TABLE daily_stock_summaries (
        business_date TEXT NOT NULL, stock_name TEXT NOT NULL, stock_code TEXT,
        mention_count INTEGER NOT NULL, broker_display TEXT NOT NULL,
        target_price_min INTEGER, target_price_max INTEGER,
        dominant_opinion TEXT NOT NULL, generated_at TEXT NOT NULL
      );
      CREATE TABLE category_membership_snapshots (
        snapshot_date TEXT NOT NULL, category_type TEXT NOT NULL, category_key TEXT NOT NULL,
        display_name TEXT NOT NULL, stock_code TEXT NOT NULL
      );
      CREATE TABLE category_master (
        category_type TEXT NOT NULL, category_key TEXT NOT NULL, enabled INTEGER NOT NULL
      );
      CREATE TABLE stock_metadata (stock_code TEXT, sector_name TEXT);
      CREATE TABLE stock_theme_memberships (stock_code TEXT, theme_name TEXT, theme_code TEXT);
    `);
    const addSummary = database.prepare(`
      INSERT INTO daily_stock_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const addSnapshot = database.prepare(`
      INSERT INTO category_membership_snapshots VALUES (?, ?, ?, ?, ?)
    `);
    const addCatalog = database.prepare("INSERT INTO category_master VALUES (?, ?, ?)");
    const add = (date, code, name, mentions = 1) => addSummary.run(
      date, name, code, mentions, "증권사 A", null, null, "N/A", `${date}T20:00:00+09:00`,
    );

    for (const date of ["2026-10-12", "2026-10-11", "2026-10-10", "2026-10-09", "2026-10-08"]) {
      add(date, "000003", "삼성전자", date === "2026-10-12" ? 2 : 1);
      add(date, "000004", "SK하이닉스", date === "2026-10-12" ? 3 : 2);
      add(date, "000005", "LG전자", date === "2026-10-12" ? 4 : 1);
      add(date, "000006", "테마 구성 종목", 2);
      add(date, "000009", "새 분류 후보", 5);
      add(date, "000012", "숨겨진 테마 후보", 7);
    }
    for (const date of ["2026-10-07", "2026-10-06", "2026-10-05"]) {
      add(date, "000001", "삼성 이전 종목", 1);
      add(date, "000002", "하이닉스 이전 종목", 2);
    }
    add("2026-10-08", "000007", "OldOnly 코드", 1);
    add("2026-10-08", "", "OldOnly 이름", 3);
    add("2026-10-04", "000008", "legacy 업종", 6);
    add("2026-10-04", "000010", "legacy 미확인 업종", 4);
    add("2026-10-04", "000011", "legacy 테마", 5);
    add("2026-10-04", "000013", "category-key legacy fallback", 8);
    add("2026-10-04", "000014", "disabled-key legacy candidate", 9);

    addCatalog.run("sector", "S1", 1);
    addCatalog.run("sector", "S2", 1);
    addCatalog.run("sector", "S3", 0);
    addCatalog.run("sector", "S4", 0);
    addCatalog.run("sector", "O1", 1);
    addCatalog.run("sector", "O2", 1);
    addCatalog.run("theme", "T1", 1);
    addCatalog.run("theme", "T2", 1);
    addCatalog.run("theme", "T3", 0);
    addSnapshot.run("2026-10-05", "sector", "S1", "반도체", "000001");
    addSnapshot.run("2026-10-05", "sector", "S2", "반도체", "000001");
    addSnapshot.run("2026-10-05", "sector", "S1", "반도체", "000002");
    addSnapshot.run("2026-10-08", "sector", "S1", "반도체", "000003");
    addSnapshot.run("2026-10-08", "sector", "S2", "반도체", "000003");
    addSnapshot.run("2026-10-08", "sector", "S1", "반도체", "000004");
    addSnapshot.run("2026-10-08", "sector", "S3", "반도체", "000005");
    addSnapshot.run("2026-10-08", "sector", "S4", "새 분류", "000009");
    addSnapshot.run("2026-10-08", "sector", "O1", "OldOnly", "000007");
    addSnapshot.run("2026-10-08", "sector", "O2", "OldOnly", "000007");
    addSnapshot.run("2026-10-08", "sector", "O1", "OldOnly", "");
    addSnapshot.run("2026-10-15", "sector", "S1", "반도체", "999999");
    addSnapshot.run("2026-10-08", "theme", "T1", "AI반도체", "000006");
    addSnapshot.run("2026-10-08", "theme", "T2", "AI반도체", "000006");
    addSnapshot.run("2026-10-08", "theme", "T3", "숨겨진 테마", "000012");
    addSnapshot.run("2026-10-15", "theme", "T1", "AI반도체", "999999");

    database.prepare("INSERT INTO stock_metadata VALUES (?, ?)").run("000008", "반도체");
    database.prepare("INSERT INTO stock_metadata VALUES (?, ?)").run("000009", "새 분류");
    database.prepare("INSERT INTO stock_metadata VALUES (?, ?)").run("000010", null);
    database.prepare("INSERT INTO stock_metadata VALUES (?, ?)").run("000013", "S1");
    database.prepare("INSERT INTO stock_metadata VALUES (?, ?)").run("000014", "S3");
    database.prepare("INSERT INTO stock_theme_memberships VALUES (?, ?, ?)").run("000011", "AI반도체", "T1");
    database.prepare("INSERT INTO stock_theme_memberships VALUES (?, ?, ?)").run("000012", "숨겨진 테마", "T3");
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const cases = [
      ["sector", "반도체", 20],
      ["theme", "AI반도체", 20],
      ["sector", "새 분류", 20],
      ["sector", "N/A", 20],
      ["theme", "숨겨진 테마", 20],
      ["sector", "OldOnly", 1],
      ["sector", "OldOnly", 2],
      ["sector", "반도체", 1],
    ];
    const beforeRead = statSync(databasePath);
    const nextSnapshots = cases.map(([type, name, limit]) => getCategoryTrendSnapshot(type, name, limit));
    const keyCases = [["sector", "S1", 20], ["sector", "S3", 20]];
    const keyRouteSnapshots = keyCases.map(([type, name, limit]) => {
      const response = categoryTrendRoute.GET(new Request(`http://next.local/api/category-trend?type=${type}&name=${name}&limit=${limit}`));
      assert.equal(response.status, 200);
      return response.json();
    });
    const resolvedKeyRouteSnapshots = await Promise.all(keyRouteSnapshots);
    const routeResponse = categoryTrendRoute.GET(new Request("http://next.local/api/category-trend?type=sector&display_name=%EB%B0%98%EB%8F%84%EC%B2%B4&limit=20&ignored=1"));
    assert.equal(routeResponse.status, 200);
    const routeSnapshot = await routeResponse.json();
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = `
import json, sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_category_trend_snapshot
from stock_monitor.db.repository import StockMonitorRepository
config = SimpleNamespace(timezone="Asia/Seoul")
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
cases = json.loads(sys.argv[2])
key_cases = json.loads(sys.argv[3])
snapshots = [build_web_view_category_trend_snapshot(config, repository, category_type=category_type, category_name="", category_display_name=display_name, limit=limit, now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for category_type, display_name, limit in cases]
key_snapshots = [build_web_view_category_trend_snapshot(config, repository, category_type=category_type, category_name=category_name, limit=limit, now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for category_type, category_name, limit in key_cases]
print(json.dumps({"display": snapshots, "keys": key_snapshots}, ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, JSON.stringify(cases), JSON.stringify(keyCases)], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout);
    const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
    assert.deepEqual(nextSnapshots.map(withoutNow), pythonSnapshots.display.map(withoutNow));
    assert.deepEqual(resolvedKeyRouteSnapshots.map(withoutNow), pythonSnapshots.keys.map(withoutNow));
    assert.deepEqual(withoutNow(routeSnapshot), withoutNow(nextSnapshots[0]));

    const [sector, theme, disabledSector, missingLabel, disabledTheme, oldOnlyShort, oldOnlyLong, onePoint] = nextSnapshots;
    assert.equal(isCategoryTrendSnapshot(sector, "sector", "반도체"), true);
    assert.equal(sector.category_name, "");
    assert.equal(sector.category_label, "업종");
    assert.equal(sector.mapping_policy, "date-aware snapshot when available, latest stored category mapping otherwise");
    assert.deepEqual(sector.trend.map((item) => item.business_date), [
      "2026-10-12", "2026-10-11", "2026-10-10", "2026-10-09", "2026-10-08",
      "2026-10-07", "2026-10-06", "2026-10-05", "2026-10-04",
    ]);
    assert.deepEqual(sector.trend[0], { business_date: "2026-10-12", stock_count: 3, report_count: 9 });
    assert.equal(theme.category_label, "테마");
    assert.ok(theme.trend.some((item) => item.business_date === "2026-10-04"));
    assert.equal(disabledSector.trend.length, 0);
    assert.equal(missingLabel.category_display_name, "업종 미확인");
    assert.deepEqual(missingLabel.trend, [{ business_date: "2026-10-04", stock_count: 2, report_count: 9 }]);
    assert.equal(disabledTheme.trend.length, 0);
    assert.deepEqual(oldOnlyShort.trend, []);
    assert.deepEqual(oldOnlyLong.trend, [{ business_date: "2026-10-08", stock_count: 2, report_count: 4 }]);
    assert.equal(onePoint.trend.length, 1);
    const [categoryKey, disabledKey] = resolvedKeyRouteSnapshots;
    assert.equal(categoryKey.category_name, "S1");
    assert.equal(categoryKey.display_name, "S1");
    assert.deepEqual(categoryKey.trend[0], { business_date: "2026-10-12", stock_count: 2, report_count: 5 });
    assert.deepEqual(categoryKey.trend.at(-1), { business_date: "2026-10-04", stock_count: 1, report_count: 8 });
    assert.equal(disabledKey.trend.length, 0);
    assert.equal(parseCategoryTrendLimit(null), 20);
    assert.equal(parseCategoryTrendLimit("invalid"), 20);
    assert.equal(parseCategoryTrendLimit("0"), 1);
    assert.equal(parseCategoryTrendLimit("999"), 60);

    for (const response of [
      categoryTrendRoute.HEAD(), categoryTrendRoute.OPTIONS(), categoryTrendRoute.POST(),
      categoryTrendRoute.PUT(), categoryTrendRoute.PATCH(), categoryTrendRoute.DELETE(),
    ]) {
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(categoryTrendRoute.GET(new Request("http://next.local/api/category-trend?type=bad&display_name=anything")).status, 400);
    assert.equal(categoryTrendRoute.GET(new Request(`http://next.local/api/category-trend?type=sector&display_name=${"x".repeat(121)}`)).status, 400);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* The fixture closes before it is opened read-only. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
