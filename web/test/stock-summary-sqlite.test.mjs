import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isDailyStockSummarySnapshot } from "../src/domain/daily.ts";
import { getDailyStockSummarySnapshot } from "../src/server/stock-summary.ts";

test("stock summary page reader matches Python row order and exact-date Toss references", () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-stock-summary-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const businessDate = "2026-10-08";
  try {
    database.exec(`
      CREATE TABLE daily_stock_summaries (
        business_date TEXT NOT NULL, stock_name TEXT NOT NULL, stock_code TEXT,
        mention_count INTEGER NOT NULL, broker_display TEXT NOT NULL,
        target_price_min INTEGER, target_price_max INTEGER,
        dominant_opinion TEXT NOT NULL, generated_at TEXT NOT NULL
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
    addSummary.run(businessDate, "DL이앤씨", "375500", 3, "대신증권(2), 삼성증권", 93000, 120000, "buy", `${businessDate}T20:00:00+09:00`);
    addSummary.run(businessDate, "LG에너지솔루션", "373220", 3, "KB증권", null, null, "hold", `${businessDate}T20:00:00+09:00`);
    addSummary.run(businessDate, "미확인 종목", null, 1, "증권사 미확인", null, null, "hold", `${businessDate}T20:00:00+09:00`);
    addSummary.run("2026-10-09", "미래 행", "111111", 20, "미래증권", 1, 2, "buy", "2026-10-09T20:00:00+09:00");

    const addMarket = database.prepare("INSERT INTO stock_market_daily VALUES (?, ?, ?, ?, NULL, ?, NULL, ?, NULL, NULL, NULL, ?, ?, NULL, NULL, ?, ?)");
    addMarket.run(businessDate, "375500", "DL이앤씨", "KOSPI", 68000, 1.5, 1000, 800000000, `${businessDate}T19:59:00+09:00`, "toss_openapi");
    addMarket.run(businessDate, "375500", "DL이앤씨", "KOSPI", 67900, -9.9, 2000, 9900000000, `${businessDate}T20:00:00+09:00`, "krx");
    addMarket.run(businessDate, "373220", "LG에너지솔루션", "KOSPI", 400000, 2.5, 2000, 900000000, `${businessDate}T20:00:00+09:00`, "krx");
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const beforeRead = statSync(databasePath);
    const snapshot = getDailyStockSummarySnapshot(businessDate);
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.equal(isDailyStockSummarySnapshot(snapshot, businessDate), true);
    assert.equal(isDailyStockSummarySnapshot({ ...snapshot, business_date: "2026-10-09" }, businessDate), false);
    const marketReference = snapshot.stocks[0].market_reference;
    assert.ok(marketReference);
    const withMarketReference = (reference) => ({
      ...snapshot,
      stocks: snapshot.stocks.map((stock, index) => index === 0 ? { ...stock, market_reference: reference } : stock),
    });
    assert.equal(isDailyStockSummarySnapshot(withMarketReference({ ...marketReference, business_date: "2026-10-07" }), businessDate), false);
    for (const field of ["close_price", "change_percent", "volume", "turnover"]) {
      const missingField = { ...marketReference };
      delete missingField[field];
      assert.equal(isDailyStockSummarySnapshot(withMarketReference(missingField), businessDate), false, `market_reference.${field} is required`);
    }

    const pythonScript = `
import json, sys
from datetime import date
from pathlib import Path
from stock_monitor.cli import _web_view_stock_market_reference
from stock_monitor.db.repository import StockMonitorRepository
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
business_date = date.fromisoformat(sys.argv[2])
summaries = repository.list_daily_summaries(business_date)
market_refs = {item.stock_code: item for item in repository.list_stock_market_daily_for_codes(business_date, [summary.stock_code for summary in summaries if summary.stock_code], source="toss_openapi")}
rows = [{"business_date": item.business_date.isoformat(), "stock_name": item.stock_name, "stock_code": item.stock_code, "mention_count": item.mention_count, "broker_display": item.broker_display, "target_price_min": item.target_price_min, "target_price_max": item.target_price_max, "dominant_opinion": item.dominant_opinion, "market_reference": _web_view_stock_market_reference(market_refs.get(item.stock_code or ""))} for item in summaries]
print(json.dumps({"business_date": business_date.isoformat(), "stocks": rows}, ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, businessDate], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python stock summary comparison failed");
    const pythonSnapshot = JSON.parse(python.stdout);
    assert.deepEqual(snapshot, {
      surface: "web-view",
      read_only: true,
      live_fetch: false,
      ...pythonSnapshot,
    });
    assert.equal(snapshot.stocks[0].market_reference.close_price, 68000);
    assert.equal(snapshot.stocks[1].market_reference, null);
    assert.equal(snapshot.stocks[2].stock_code, null);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* The fixture closes before it is opened read-only. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
