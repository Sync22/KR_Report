import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isStockSearchSnapshot } from "../src/domain/stocks.ts";

test("stock search uses a read-only SQLite fixture and matches Python source precedence", async () => {
  const { getStockSearchSnapshot, parseStockSearchLimit } = await import("../src/server/stock-search.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-stock-search-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    database.exec(`
      CREATE TABLE toss_stock_universe_cache (
        business_date TEXT NOT NULL, stock_code TEXT, stock_name TEXT, market TEXT
      );
      CREATE TABLE krx_stock_metadata (
        business_date TEXT NOT NULL, stock_code TEXT, stock_name TEXT, market TEXT
      );
      CREATE TABLE daily_stock_summaries (
        business_date TEXT NOT NULL, stock_code TEXT, stock_name TEXT
      );
      CREATE TABLE stock_metadata (stock_code TEXT, stock_name TEXT);
      CREATE TABLE reports (business_date TEXT, stock_code TEXT, stock_name TEXT);
      CREATE TABLE report_linked_news_evidence (target_date TEXT, stock_code TEXT);
      CREATE TABLE stock_market_daily (
        business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT,
        market TEXT, section_name TEXT, close_price INTEGER, change_amount INTEGER,
        change_percent REAL, open_price INTEGER, high_price INTEGER, low_price INTEGER,
        volume INTEGER, turnover INTEGER, market_cap INTEGER, listed_shares INTEGER,
        fetched_at TEXT NOT NULL, source TEXT NOT NULL
      );
    `);
    const addRows = (table, columns, rows) => {
      const placeholders = columns.map(() => "?").join(", ");
      const insert = database.prepare(`INSERT INTO ${table} (${columns.join(", ")}) VALUES (${placeholders})`);
      for (const row of rows) insert.run(...row);
    };
    addRows("toss_stock_universe_cache", ["business_date", "stock_code", "stock_name", "market"], [
      ["2026-10-07", "000006", "삼성 이전 Toss", "KOSDAQ"],
      ["2026-10-08", "000001", "삼성 Toss 이름", "KOSPI"],
      ["2026-10-08", "000002", "삼성전자", "KOSPI"],
      ["2026-10-09", "000007", "삼성 미래 Toss", "KOSDAQ"],
    ]);
    addRows("krx_stock_metadata", ["business_date", "stock_code", "stock_name", "market"], [
      ["2026-10-05", "000001", "삼성 KRX 이름", "KOSDAQ"],
      ["2026-10-05", "000002", "삼성전자 KRX 이름", "KOSDAQ"],
      ["2026-10-06", "000003", "삼성SDI", "KOSDAQ"],
      ["2026-10-09", "000003", "삼성SDI 최신", "KOSPI"],
    ]);
    addRows("daily_stock_summaries", ["business_date", "stock_code", "stock_name"], [
      ["2026-10-08", "000001", "삼성전자 일일 요약"],
    ]);
    addRows("stock_metadata", ["stock_code", "stock_name"], [
      ["000001", "삼성 Master 이름"],
      ["000004", "삼성바이오"],
      ["000006", "Samsung Master"],
      ["000008", "000001 reference name"],
      ["000009", ""],
    ]);
    addRows("reports", ["business_date", "stock_code", "stock_name"], [
      ["2026-10-08", "000001", "삼성전자 선택일 리포트"],
      ["2026-10-07", "000001", "삼성전자 이전 리포트"],
      ["2026-10-07", "000005", "삼성전기 이전 리포트"],
    ]);
    addRows("report_linked_news_evidence", ["target_date", "stock_code"], [
      ["2026-10-08", "000001"],
      ["2026-10-07", "000002"],
    ]);
    addRows("stock_market_daily", [
      "business_date", "stock_code", "stock_name", "market", "section_name", "close_price",
      "change_amount", "change_percent", "open_price", "high_price", "low_price", "volume",
      "turnover", "market_cap", "listed_shares", "fetched_at", "source",
    ], [
      ["2026-10-08", "000001", "삼성전자", "KOSPI", null, 70000, 1000, 1.4, 69000, 71000, 68000, 500, 35000000, null, null, "2026-10-08T20:00:00+09:00", "toss_openapi"],
      ["2026-10-08", "000003", "삼성SDI", "KOSDAQ", null, 30000, 500, 1.7, 29000, 31000, 28500, 100, 3000000, null, null, "2026-10-08T20:00:00+09:00", "krx_data_market"],
    ]);
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const cases = [
      ["2026-10-08", "  삼성  ", 20],
      ["2026-10-08", "000001", 20],
      ["2026-10-08", "samsung", 20],
      ["2026-10-08", "%", 20],
      ["2026-10-08", "없는 종목", 8],
      ["2026-10-08", "  ", 8],
      ["2026-10-09", "삼성", 20],
      ["2026-10-08", "삼성", 1],
      ["2026-10-08", "' OR 1=1 --", 20],
    ];
    const beforeRead = statSync(databasePath);
    const nextSnapshots = cases.map(([date, query, limit]) => getStockSearchSnapshot(date, query, limit));
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = `
import json, sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_stock_search_snapshot
from stock_monitor.db.repository import StockMonitorRepository
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
config = SimpleNamespace(timezone="Asia/Seoul")
cases = json.loads(sys.argv[2])
snapshots = [build_web_view_stock_search_snapshot(config, repository, business_date=date.fromisoformat(day), query=query, limit=limit, now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for day, query, limit in cases]
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
    assert.deepEqual(nextSnapshots.map(withoutNow), pythonSnapshots.map(withoutNow));

    const [korean, exactCode, english, wildcard, noResults, empty, selectedLater, limited, injection] = nextSnapshots;
    assert.equal(isStockSearchSnapshot(korean, "2026-10-08", "  삼성  "), true);
    assert.equal(korean.query, "삼성");
    assert.equal(korean.stock_universe_reference_date, "2026-10-08");
    const dailyPreferred = korean.items.find((item) => item.stock_code === "000001");
    assert.equal(dailyPreferred.stock_name, "삼성전자 일일 요약");
    assert.equal(dailyPreferred.market, "KOSPI");
    assert.equal(dailyPreferred.market_source, "stored_toss_stock_universe");
    assert.equal(dailyPreferred.market_reference_date, "2026-10-08");
    assert.equal(dailyPreferred.has_selected_date_report, true);
    assert.equal(dailyPreferred.has_selected_date_toss, true);
    assert.equal(dailyPreferred.has_news_observation, true);
    assert.equal(korean.items.find((item) => item.stock_code === "000003").market_reference_date, "2026-10-06");
    assert.equal(korean.items.find((item) => item.stock_code === "000004").market_source, null);
    assert.equal(exactCode.items[0].stock_code, "000001");
    assert.equal(english.items[0].stock_code, "000006");
    assert.deepEqual(wildcard.items.map((item) => item.stock_code).sort(), ["000001", "000002", "000003", "000004", "000005", "000006", "000008", "000009"]);
    assert.equal(wildcard.items.find((item) => item.stock_code === "000009").stock_name, "000009");
    assert.equal(noResults.available, false);
    assert.equal(noResults.empty_state, "조회된 저장 종목이 없습니다.");
    assert.equal(empty.query, "");
    assert.equal(empty.stock_universe_reference_date, null);
    assert.equal(empty.empty_state, "검색어를 입력하세요.");
    assert.equal(selectedLater.stock_universe_reference_date, "2026-10-09");
    assert.equal(limited.items.length, 1);
    assert.equal(injection.items.length, 0);
    assert.equal(parseStockSearchLimit(null), 8);
    assert.equal(parseStockSearchLimit("invalid"), 8);
    assert.equal(parseStockSearchLimit("0"), 1);
    assert.equal(parseStockSearchLimit("999"), 20);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* The fixture closes before it is opened read-only. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
