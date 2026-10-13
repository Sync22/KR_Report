import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import * as marketDomain from "../src/domain/market.ts";

test("market DTOs preserve stored source dates and missing-data states", () => {
  const market = {
    now: "2026-10-11T09:00:00+09:00",
    timezone: "Asia/Seoul",
    surface: "web-view",
    read_only: true,
    snapshot_source: "toss_openapi",
    snapshot_date: "2026-10-08",
    capture_status: "partial",
    missing_domains: ["market_flow"],
    latest_capture_attempt: { status: "partial", business_date: "2026-10-08", missing_domains: ["market_flow"] },
    top_kospi_stocks: [{ business_date: "2026-10-08", stock_code: "005930", stock_name: "삼성전자", market: "KOSPI", close_price: 70000, change_percent: 1, volume: 100, turnover: 7000000, fetched_at: "2026-10-08T20:00:00+09:00" }],
    top_kosdaq_stocks: [],
    top_etfs: [],
    market_indices: [],
  };
  assert.equal(marketDomain.isMarketSnapshot(market), true);
  assert.equal(marketDomain.isMarketSnapshot({ ...market, snapshot_source: "krx" }), false);
  assert.equal(marketDomain.isMarketSnapshot({ ...market, top_kospi_stocks: [{ ...market.top_kospi_stocks[0], business_date: "2026-10-09" }] }), false);

  const flow = {
    now: market.now,
    timezone: market.timezone,
    surface: "web-view",
    read_only: true,
    business_date: "2026-10-08",
    reference_date: "2026-10-07",
    exact_date_available: false,
    available: true,
    source: "toss_openapi",
    data_scope: "stored_toss_close_market_flow",
    live_fetch: false,
    scoring: false,
    notice: "이전 저장 수급 기준입니다.",
    items: [{ business_date: "2026-10-07", market_flows: [{ business_date: "2026-10-07", market: "KOSPI", market_label: "KOSPI", investor_type: "foreign", investor_label: "외국인", sell_volume: 10, buy_volume: 20, net_buy_volume: 10, sell_amount: 100, buy_amount: 200, net_buy_amount: 100, volume_unit: "주", amount_unit: "원", source: "toss_openapi" }] }],
  };
  assert.equal(marketDomain.isFlowTrendSnapshot(flow, "2026-10-08"), true);
  assert.equal(marketDomain.isFlowTrendSnapshot({ ...flow, reference_date: "2026-10-09" }, "2026-10-08"), false);
  assert.equal(marketDomain.isFlowTrendSnapshot({ ...flow, live_fetch: true }, "2026-10-08"), false);
});

test("market snapshot reads temporary SQLite read-only and matches the Python DTO", async () => {
  const { getMarketSnapshot } = await import("../src/server/market-snapshot.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-market-"));
  const fullPath = join(tempRoot, "full.db");
  const emptyPath = join(tempRoot, "empty.db");
  const eventOnlyPath = join(tempRoot, "event-only.db");
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;

  const createSchema = (database) => database.exec(`
    CREATE TABLE toss_market_context_snapshots (business_date TEXT NOT NULL, source TEXT NOT NULL);
    CREATE TABLE stock_market_daily (
      business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT, market TEXT,
      section_name TEXT, close_price INTEGER, change_amount INTEGER, change_percent REAL,
      open_price INTEGER, high_price INTEGER, low_price INTEGER, volume INTEGER,
      turnover INTEGER, market_cap INTEGER, listed_shares INTEGER, fetched_at TEXT NOT NULL,
      source TEXT NOT NULL
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
    CREATE TABLE market_index_daily (
      business_date TEXT NOT NULL, index_series TEXT NOT NULL, index_class TEXT NOT NULL,
      index_name TEXT NOT NULL, close_index REAL, change_amount REAL, change_percent REAL,
      open_index REAL, high_index REAL, low_index REAL, volume INTEGER, turnover INTEGER,
      market_cap INTEGER, fetched_at TEXT NOT NULL, source TEXT NOT NULL
    );
    CREATE TABLE operation_events (
      id INTEGER PRIMARY KEY, event_time TEXT NOT NULL, component TEXT NOT NULL,
      event_type TEXT NOT NULL, status TEXT NOT NULL, business_date TEXT, detail TEXT
    );
  `);

  const addMarketData = (database) => {
    database.prepare("INSERT INTO toss_market_context_snapshots VALUES (?, ?)").run("2026-10-08", "toss_openapi");
    const stock = database.prepare("INSERT INTO stock_market_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    const addStock = (code, market, turnover, source = "toss_openapi", date = "2026-10-08", closePrice = 10000) => stock.run(
      date, code, `${market} ${code}`, market, null, closePrice, 10, 1.25, 9900, 10100, 9800,
      1000, turnover, null, null, `${date}T20:00:00+09:00`, source,
    );
    addStock("005930", "KOSPI", 500);
    addStock("000660", "KOSPI", 1000);
    addStock("035420", "KOSPI", 1000);
    addStock("051910", "KOSPI", 750);
    addStock("005380", "KOSPI", 500);
    addStock("000270", "KOSPI", 100);
    addStock("999999", "KOSPI", 999999, "krx_data_market");
    addStock("035900", "KOSDAQ", 300);
    addStock("091990", "KOSDAQ", 200);
    stock.run("2026-10-09", "700001", "KOSPI 700001", "KOSPI", null, 100, null, null, null, null, null, null, null, null, null, "2026-10-09T20:00:00+09:00", "toss_openapi");

    const etf = database.prepare("INSERT INTO etf_daily_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    const addEtf = (code, name, turnover, source = "toss_openapi") => etf.run(
      "2026-10-08", code, name, 10000, 100, 1.25, 1000.05, 9900, 10100, 9800,
      5000, turnover, null, null, null, "KOSPI 200", 200, 1, 0.5,
      "2026-10-08T20:00:00+09:00", source,
    );
    addEtf("069500", "KODEX 200", 2000);
    addEtf("114800", "KODEX 인버스", 1000);
    addEtf("102110", "TIGER 200", 1000);
    addEtf("152100", "TIGER 200선물인버스2X", 750);
    addEtf("229200", "KODEX 코스닥150", 500);
    addEtf("234310", "TIGER 코스닥150", 100);
    addEtf("999999", "KRX ETF", 999999, "krx_data_market");

    const index = database.prepare("INSERT INTO market_index_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    const addIndex = (series, name, turnover, source = "toss_openapi") => index.run(
      "2026-10-08", series, "market", name, 2500, 10, 0.4, 2490, 2510, 2480,
      100000, turnover, null, "2026-10-08T20:00:00+09:00", source,
    );
    addIndex("KOSPI", "KOSPI 200", 2000);
    addIndex("KOSPI", "KOSPI", 1000);
    addIndex("KOSDAQ", "KOSDAQ", 500);
    addIndex("KRX", "KRX index", 999999, "krx_data_market");

    const event = database.prepare("INSERT INTO operation_events VALUES (?,?,?,?,?,?,?)");
    event.run(1, "2026-10-08T19:00:00+09:00", "toss-market-context", "capture", "complete", "2026-10-08", "missing_domains=");
    event.run(2, "2026-10-08T20:00:00+09:00", "toss-market-context", "capture", "partial", "2026-10-08", "missing_domains=top20,private_domain,market_flow");
    event.run(3, "2026-10-09T20:00:00+09:00", "toss-market-context", "capture", "failed", "2026-10-09", "missing_domains=security_metadata");
  };

  try {
    const fullDatabase = new DatabaseSync(fullPath);
    createSchema(fullDatabase);
    addMarketData(fullDatabase);
    fullDatabase.close();
    const emptyDatabase = new DatabaseSync(emptyPath);
    createSchema(emptyDatabase);
    emptyDatabase.close();
    const eventDatabase = new DatabaseSync(eventOnlyPath);
    createSchema(eventDatabase);
    eventDatabase.prepare("INSERT INTO operation_events VALUES (?,?,?,?,?,?,?)").run(
      1, "2026-10-08T20:00:00+09:00", "toss-market-context", "capture", "failed", "2026-10-08", "missing_domains=market_flow",
    );
    eventDatabase.close();

    const paths = [fullPath, emptyPath, eventOnlyPath];
    const nextSnapshots = [];
    const fileStats = paths.map((path) => {
      const { size, mtimeMs } = statSync(path);
      return { size, mtimeMs };
    });
    for (const path of paths) {
      process.env.STOCK_MONITOR_DB_PATH = path;
      nextSnapshots.push(getMarketSnapshot());
    }
    assert.deepEqual(paths.map((path) => {
      const { size, mtimeMs } = statSync(path);
      return { size, mtimeMs };
    }), fileStats);

    const pythonScript = `
import json, sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_market_snapshot
from stock_monitor.db.repository import StockMonitorRepository
config = SimpleNamespace(timezone="Asia/Seoul")
snapshots = [build_web_view_market_snapshot(config, StockMonitorRepository(Path(path), timezone="Asia/Seoul"), now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for path in sys.argv[1:]]
print(json.dumps(snapshots, ensure_ascii=False, separators=(",", ":")))
`;
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, ...paths], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout);
    const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
    assert.deepEqual(nextSnapshots.map(withoutNow), pythonSnapshots.map(withoutNow));

    const [full, empty, eventOnly] = nextSnapshots;
    assert.equal(marketDomain.isMarketSnapshot(full), true);
    assert.equal(full.snapshot_date, "2026-10-08");
    assert.equal(full.capture_status, "partial");
    assert.deepEqual(full.missing_domains, ["top20", "market_flow"]);
    assert.deepEqual(full.latest_capture_attempt, {
      status: "failed",
      business_date: "2026-10-09",
      missing_domains: ["security_metadata"],
    });
    assert.deepEqual(full.top_kospi_stocks.map((row) => row.stock_code), ["000660", "035420", "051910", "005380", "005930"]);
    assert.deepEqual(full.top_kosdaq_stocks.map((row) => row.stock_code), ["035900", "091990"]);
    assert.deepEqual(full.top_etfs.map((row) => row.etf_code), ["069500", "102110", "114800", "152100", "229200"]);
    assert.deepEqual(full.market_indices.map((row) => [row.index_series, row.index_name]), [
      ["KOSDAQ", "KOSDAQ"], ["KOSPI", "KOSPI"], ["KOSPI", "KOSPI 200"],
    ]);
    assert.equal(marketDomain.isMarketSnapshot(empty), true);
    assert.equal(empty.snapshot_date, null);
    assert.equal(empty.capture_status, null);
    assert.deepEqual(empty.missing_domains, []);
    assert.equal(empty.latest_capture_attempt, null);
    assert.equal(marketDomain.isMarketSnapshot(eventOnly), true);
    assert.equal(eventOnly.snapshot_date, null);
    assert.equal(eventOnly.capture_status, "failed");
    assert.deepEqual(eventOnly.missing_domains, ["market_flow"]);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("ETF trend keeps selection date, stale reference date, and no-composition scope", () => {
  const snapshot = {
    now: "2026-10-11T09:00:00+09:00",
    timezone: "Asia/Seoul",
    surface: "web-view",
    read_only: true,
    business_date: "2026-10-08",
    reference_date: "2026-10-07",
    reference_status: "stale",
    exact_date_available: false,
    available: true,
    source: "toss_openapi",
    data_scope: "stored_toss_close_snapshot",
    basis: "Toss 거래대금 상위 ETF",
    display_label: "ETF 저장 참고",
    constituents_available: false,
    composition_scope: "구성종목 미포함",
    live_fetch: false,
    scoring: false,
    notice: "이전 저장 ETF 참고입니다.",
    items: [{ business_date: "2026-10-07", top_etfs_by_turnover: [{ business_date: "2026-10-07", etf_code: "069500", etf_name: "KODEX 200", close_price: 1000, change_percent: 1, nav: 1000, volume: 10, turnover: 10000, underlying_index_name: "KOSPI 200", evidence_label: "저장값", rotation_reference: "저장 기준" }] }],
  };
  assert.equal(typeof marketDomain.isEtfTrendSnapshot, "function");
  assert.equal(marketDomain.isEtfTrendSnapshot(snapshot, "2026-10-08"), true);
  assert.equal(marketDomain.isEtfTrendSnapshot({ ...snapshot, constituents_available: true }, "2026-10-08"), false);
  assert.equal(marketDomain.isEtfTrendSnapshot({ ...snapshot, reference_date: "2026-10-09" }, "2026-10-08"), false);
});

test("flow trend reads bounded Toss dates and sorts markets and investors like Python", async () => {
  const { buildFlowTrendSnapshot, parseFlowTrendLimit } = await import("../src/server/flow-trend.ts");
  const database = new DatabaseSync(":memory:");
  try {
    database.exec(`
      CREATE TABLE market_investor_flow_daily (
        business_date TEXT NOT NULL, market TEXT NOT NULL, investor_type TEXT NOT NULL,
        sell_volume INTEGER, buy_volume INTEGER, net_buy_volume INTEGER,
        sell_amount INTEGER, buy_amount INTEGER, net_buy_amount INTEGER,
        volume_unit TEXT, amount_unit TEXT, source TEXT NOT NULL
      )
    `);
    const insert = database.prepare(`
      INSERT INTO market_investor_flow_daily (
        business_date, market, investor_type, sell_volume, buy_volume, net_buy_volume,
        sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit, source
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const add = (date, market, investor, amount = 100, source = "toss_openapi") => insert.run(
      date, market, investor, 10, 20, 10, amount, amount * 2, amount,
      "주", "원", source,
    );
    add("2026-10-08", "KOSDAQ", "individual", 600);
    add("2026-10-08", "KOSPI", "individual", 300);
    add("2026-10-08", "KOSPI", "institution", 200);
    add("2026-10-08", "KOSPI", "foreign", 100);
    add("2026-10-08", "KOSDAQ", "institution", 500);
    add("2026-10-08", "KOSDAQ", "foreign", 400);
    add("2026-10-08", "KOSPI", "foreign", 999, "krx_data_market");
    add("2026-10-07", "KOSPI", "foreign", 700);
    add("2026-10-06", "KOSDAQ", "individual", 800);
    add("2026-10-09", "KOSPI", "foreign", 900);

    const now = new Date("2026-10-11T00:00:00.000Z");
    const exact = buildFlowTrendSnapshot(database, "2026-10-08", 2, now, "Asia/Seoul");
    assert.equal(exact.now, now.toISOString());
    assert.equal(exact.timezone, "Asia/Seoul");
    assert.equal(exact.reference_date, "2026-10-08");
    assert.equal(exact.exact_date_available, true);
    assert.equal(exact.available, true);
    assert.equal(exact.source, "toss_openapi");
    assert.equal(exact.data_scope, "stored_toss_close_market_flow");
    assert.equal(exact.live_fetch, false);
    assert.equal(exact.scoring, false);
    assert.deepEqual(exact.items.map((item) => item.business_date), ["2026-10-08", "2026-10-07"]);
    assert.deepEqual(exact.items[0].market_flows.map((item) => [item.market_label, item.investor_label]), [
      ["KOSPI", "외국인"], ["KOSPI", "기관"], ["KOSPI", "개인"],
      ["KOSDAQ", "외국인"], ["KOSDAQ", "기관"], ["KOSDAQ", "개인"],
    ]);
    assert.deepEqual(exact.items[0].market_flows[0], {
      business_date: "2026-10-08", market: "KOSPI", market_label: "KOSPI",
      investor_type: "foreign", investor_label: "외국인", sell_volume: 10,
      buy_volume: 20, net_buy_volume: 10, sell_amount: 100, buy_amount: 200,
      net_buy_amount: 100, volume_unit: "주", amount_unit: "원", source: "toss_openapi",
    });
    assert.equal(buildFlowTrendSnapshot(database, "2026-10-08", 1, now).items.length, 1);

    const stale = buildFlowTrendSnapshot(database, "2026-10-10", 1, now);
    assert.equal(stale.reference_date, "2026-10-09");
    assert.equal(stale.exact_date_available, false);
    const missing = buildFlowTrendSnapshot(database, "2026-10-05", 5, now);
    assert.equal(missing.reference_date, null);
    assert.equal(missing.available, false);
    assert.equal(missing.source, null);
    assert.equal(missing.notice, "선택 날짜 이전 또는 해당 날짜의 저장 수급 데이터가 없습니다.");

    assert.equal(parseFlowTrendLimit(null), 5);
    assert.equal(parseFlowTrendLimit("invalid"), 5);
    assert.equal(parseFlowTrendLimit("0"), 1);
    assert.equal(parseFlowTrendLimit("999"), 20);
  } finally {
    database.close();
  }
});

test("ETF trend reads temporary Toss snapshots read-only and matches the Python DTO", async () => {
  const { getEtfTrendSnapshot, parseEtfTrendLimit } = await import("../src/server/etf-trend.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-etf-trend-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    database.exec(`
      CREATE TABLE etf_daily_snapshots (
        business_date TEXT NOT NULL, etf_code TEXT NOT NULL, etf_name TEXT NOT NULL,
        close_price INTEGER, change_amount INTEGER, change_percent REAL, nav REAL,
        open_price INTEGER, high_price INTEGER, low_price INTEGER, volume INTEGER,
        turnover INTEGER, market_cap INTEGER, net_assets_total INTEGER, listed_shares INTEGER,
        underlying_index_name TEXT, underlying_index_close REAL,
        underlying_index_change_amount REAL, underlying_index_change_percent REAL,
        fetched_at TEXT NOT NULL, source TEXT NOT NULL
      )
    `);
    const insert = database.prepare(`
      INSERT INTO etf_daily_snapshots VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
      )
    `);
    const add = (date, code, turnover, options = {}) => insert.run(
      date, code, options.name ?? code, 10000, 5, 1.25, options.nav === undefined ? 1000.05 : options.nav,
      9900, 10100, 9800, 5000, turnover, null, null, null,
      options.index === undefined ? "KOSPI 200" : options.index, 200, 1, 0.5,
      "2026-10-08T20:00:00+09:00", options.source ?? "toss_openapi",
    );
    add("2026-10-08", "069500", 1_250_000_000_000, { name: "KODEX 200" });
    add("2026-10-08", "114800", 200_000_000_000, { name: "KODEX 인버스" });
    add("2026-10-08", "000002", 200_000_000_000, { name: "두번째 ETF" });
    add("2026-10-08", "000001", 200_000_000_000, { name: "첫번째 ETF" });
    add("2026-10-08", "000003", 10, { name: "낮은 거래대금" });
    add("2026-10-08", "000004", 5, { name: "제외 ETF" });
    add("2026-10-08", "999999", 9_000_000_000_000, { source: "krx_data_market" });
    add("2026-10-07", "069500", 100_000_000, { nav: null, index: null });
    add("2026-10-06", "069500", null, { nav: null, index: null });
    add("2026-10-10", "888888", 1000, { name: "미래 날짜 ETF" });
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const cases = [["2026-10-08", 2], ["2026-10-09", 5], ["2026-10-05", 5], ["2026-10-08", 1], ["2026-10-08", 20]];
    const beforeRead = statSync(databasePath);
    const nextSnapshots = cases.map(([date, limit]) => getEtfTrendSnapshot(date, limit));
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = `
import json, sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from stock_monitor.cli import build_web_view_etf_trend_snapshot
from stock_monitor.db.repository import StockMonitorRepository
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
config = SimpleNamespace(timezone="Asia/Seoul")
cases = json.loads(sys.argv[2])
snapshots = [build_web_view_etf_trend_snapshot(config, repository, business_date=date.fromisoformat(day), limit=limit, now=datetime.fromisoformat("2026-10-12T09:00:00+09:00")) for day, limit in cases]
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

    const [exact, stale, missing, limited, extended] = nextSnapshots;
    assert.equal(marketDomain.isEtfTrendSnapshot(exact, "2026-10-08"), true);
    assert.equal(exact.reference_status, "exact");
    assert.equal(exact.exact_date_available, true);
    assert.equal(exact.display_label, "ETF 저장 참고");
    assert.deepEqual(exact.items.map((item) => item.business_date), ["2026-10-08", "2026-10-07"]);
    assert.deepEqual(exact.items[0].top_etfs_by_turnover.map((item) => item.etf_code), ["069500", "000001", "000002", "114800", "000003"]);
    assert.equal(exact.items[0].top_etfs_by_turnover[0].evidence_label, "거래대금 1.2조 · NAV 1,000.0 · 기초지수 KOSPI 200");
    assert.equal(exact.items[1].top_etfs_by_turnover[0].evidence_label, "거래대금 1억");
    assert.equal(stale.reference_status, "stale");
    assert.equal(stale.reference_date, "2026-10-08");
    assert.equal(missing.reference_status, "missing");
    assert.equal(missing.available, false);
    assert.equal(missing.source, null);
    assert.equal(missing.display_label, "ETF 저장값 없음");
    assert.equal(limited.items.length, 1);
    assert.equal(extended.items.length, 3);
    assert.equal(parseEtfTrendLimit(null), 5);
    assert.equal(parseEtfTrendLimit("invalid"), 5);
    assert.equal(parseEtfTrendLimit("0"), 1);
    assert.equal(parseEtfTrendLimit("999"), 20);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* The fixture closes before it is opened read-only. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
