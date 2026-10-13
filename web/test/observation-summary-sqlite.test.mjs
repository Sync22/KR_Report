import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isObservationSummarySnapshot } from "../src/domain/observation.ts";

const OBSERVATION_DATE = "2026-10-12";
const FIXED_NOW = "2026-10-12T10:00:00+09:00";

function recursivelyContainsForbiddenSignal(value) {
  if (!value || typeof value !== "object") return false;
  return Object.entries(value).some(([key, child]) =>
    ["score", "grade", "buy_signal", "sell_signal"].includes(key) || recursivelyContainsForbiddenSignal(child),
  );
}

test("observation summary matches the Python builder from a read-only SQLite snapshot", async () => {
  const service = await import("../src/server/observation-summary.ts");
  const route = await import("../src/app/api/observation-summary/route.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-observation-summary-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousTimezone = process.env.STOCK_MONITOR_TIMEZONE;
  const previousHolidays = process.env.STOCK_MONITOR_HOLIDAYS;
  try {
    database.exec([
      "CREATE TABLE daily_stock_summaries (business_date TEXT NOT NULL, stock_name TEXT NOT NULL, stock_code TEXT, mention_count INTEGER NOT NULL, broker_display TEXT NOT NULL, target_price_min INTEGER, target_price_max INTEGER, dominant_opinion TEXT, generated_at TEXT NOT NULL)",
      "CREATE TABLE reports (stock_name TEXT NOT NULL, stock_code TEXT, title TEXT NOT NULL, broker_name TEXT NOT NULL, published_at TEXT NOT NULL, business_date TEXT NOT NULL, target_price_raw TEXT, target_price_value INTEGER, opinion_raw TEXT, opinion_normalized TEXT, collected_at TEXT NOT NULL, source_url TEXT, source_id TEXT, identity_key TEXT NOT NULL)",
      "CREATE TABLE stock_market_daily (business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT NOT NULL, market TEXT NOT NULL, section_name TEXT, close_price INTEGER, change_amount INTEGER, change_percent REAL, open_price INTEGER, high_price INTEGER, low_price INTEGER, volume INTEGER, turnover INTEGER, market_cap INTEGER, listed_shares INTEGER, fetched_at TEXT NOT NULL, source TEXT NOT NULL)",
      "CREATE TABLE stock_investor_flow_daily (business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT, market TEXT, investor_type TEXT NOT NULL, sell_volume INTEGER, buy_volume INTEGER, net_buy_volume INTEGER, sell_amount INTEGER, buy_amount INTEGER, net_buy_amount INTEGER, volume_unit TEXT, amount_unit TEXT, candidate_score INTEGER, candidate_reasons TEXT, fetched_at TEXT NOT NULL, source TEXT NOT NULL)",
      "CREATE TABLE market_index_daily (business_date TEXT NOT NULL, index_series TEXT NOT NULL, index_class TEXT NOT NULL, index_name TEXT NOT NULL, close_index REAL, change_amount REAL, change_percent REAL, open_index REAL, high_index REAL, low_index REAL, volume INTEGER, turnover INTEGER, market_cap INTEGER, fetched_at TEXT NOT NULL, source TEXT NOT NULL)",
      "CREATE TABLE market_investor_flow_daily (business_date TEXT NOT NULL, market TEXT NOT NULL, investor_type TEXT NOT NULL, sell_volume INTEGER, buy_volume INTEGER, net_buy_volume INTEGER, sell_amount INTEGER, buy_amount INTEGER, net_buy_amount INTEGER, volume_unit TEXT, amount_unit TEXT, fetched_at TEXT NOT NULL, source TEXT NOT NULL)",
      "CREATE TABLE toss_priority_quote_baselines (business_date TEXT NOT NULL, stock_code TEXT NOT NULL, stock_name TEXT, baseline_time TEXT NOT NULL, last_price INTEGER, currency TEXT, source TEXT NOT NULL, fetched_at TEXT NOT NULL)",
      "CREATE TABLE news_intelligence_runs (run_id TEXT PRIMARY KEY, target_date TEXT NOT NULL, stock_name TEXT NOT NULL, stock_code TEXT, aliases_json TEXT NOT NULL, source_mode TEXT NOT NULL, page_limit INTEGER NOT NULL, full_day_complete INTEGER NOT NULL, live_fetch INTEGER NOT NULL, parsed_count INTEGER NOT NULL, deduped_count INTEGER NOT NULL, matched_count INTEGER NOT NULL, operator_summary_snapshot TEXT NOT NULL, warnings_json TEXT NOT NULL, created_at TEXT NOT NULL)",
      "CREATE TABLE report_linked_news_evidence (run_id TEXT NOT NULL, evidence_key TEXT NOT NULL, target_date TEXT NOT NULL, stock_code TEXT, stock_name TEXT NOT NULL, related_report_count INTEGER NOT NULL, related_report_source_ids_json TEXT NOT NULL, daily_summary_presence INTEGER NOT NULL, candidate_priority_presence INTEGER NOT NULL, candidate_observation_priority TEXT, krx_reference_presence INTEGER NOT NULL, krx_reference_date TEXT, krx_turnover INTEGER, investor_flow_presence INTEGER NOT NULL, source_lane TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, source TEXT NOT NULL, published_at TEXT NOT NULL, url TEXT NOT NULL, matched_alias TEXT NOT NULL, match_reason TEXT NOT NULL, match_scope TEXT NOT NULL, relevance TEXT NOT NULL, relevance_reason TEXT NOT NULL, sentiment TEXT NOT NULL, sentiment_score INTEGER NOT NULL, event_types_json TEXT NOT NULL, stock_impact TEXT NOT NULL, impact_explanation TEXT NOT NULL, evidence_case TEXT NOT NULL, operator_recommendation TEXT NOT NULL, recommendation_reason TEXT NOT NULL, operator_summary_snapshot TEXT NOT NULL, created_at TEXT NOT NULL, canonical_url TEXT NOT NULL, lineage_type TEXT NOT NULL, lineage_reason TEXT NOT NULL)",
      "CREATE TABLE operation_events (id INTEGER PRIMARY KEY, event_time TEXT NOT NULL, component TEXT NOT NULL, event_type TEXT NOT NULL, status TEXT NOT NULL, business_date TEXT, detail TEXT)",
      "CREATE TABLE category_master (category_type TEXT NOT NULL, category_key TEXT NOT NULL, display_name TEXT NOT NULL, enabled INTEGER NOT NULL)",
      "CREATE TABLE category_membership_snapshots (snapshot_date TEXT NOT NULL, category_type TEXT NOT NULL, category_key TEXT NOT NULL, display_name TEXT NOT NULL, stock_code TEXT NOT NULL)",
      "CREATE TABLE stock_metadata (stock_code TEXT PRIMARY KEY, stock_name TEXT, sector_code TEXT, sector_name TEXT)",
      "CREATE TABLE stock_theme_memberships (theme_code TEXT NOT NULL, theme_name TEXT NOT NULL, stock_code TEXT NOT NULL)",
    ].join(";\n"));

    const summaryInsert = database.prepare("INSERT INTO daily_stock_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    const stockRows = [
      ["000001", "삼성전자", 7, "증권사 A (1), 증권사 B (1)", 10000, 12000],
      ["000002", "SK하이닉스", 6, "증권사 A (1), 증권사 B (1)", null, null],
      ["000003", "NAVER", 6, "증권사 B (1)", null, null],
      ["000004", "현대차", 4, "증권사 C (1)", null, null],
      ["000005", "LG화학", 3, "증권사 D (1)", null, null],
      ["000006", "카카오", 2, "증권사 E (1)", null, null],
      ["000007", "두산", 1, "증권사 F (1)", null, null],
    ];
    for (const [code, name, mentions, brokers, min, max] of stockRows) {
      summaryInsert.run(OBSERVATION_DATE, name, code, mentions, brokers, min, max, "N/A", `${OBSERVATION_DATE}T20:00:00+09:00`);
    }
    for (const [code, name, mentions] of stockRows.slice(0, 3)) {
      summaryInsert.run("2026-10-08", name, code, mentions, "증권사 A (1)", null, null, "N/A", "2026-10-08T20:00:00+09:00");
    }

    const reportInsert = database.prepare("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    let reportId = 0;
    const addReport = (date, code, name, broker, target = null) => {
      reportId += 1;
      const identity = `report-${reportId}`;
      reportInsert.run(
        name, code, `${name} 저장 리포트 ${reportId}`, broker, `${date}T09:00:00+09:00`, date,
        target === null ? null : String(target), target, null, "N/A", `${date}T09:05:00+09:00`,
        `https://example.test/${identity}`, identity, identity,
      );
    };
    addReport(OBSERVATION_DATE, "000001", "삼성전자", "증권사 A", 10000);
    addReport(OBSERVATION_DATE, "000001", "삼성전자", "증권사 B", 12000);
    addReport("2026-10-09", "000001", "삼성전자", "증권사 A", 8000);
    addReport("2026-10-09", "000001", "삼성전자", "증권사 B", 9000);
    addReport("2026-10-08", "000001", "삼성전자", "증권사 C");
    addReport("2026-10-07", "000001", "삼성전자", "증권사 A");
    addReport("2026-10-06", "000001", "삼성전자", "증권사 C");
    for (const [code, name] of stockRows.slice(1)) addReport(OBSERVATION_DATE, code, name, `증권사 ${code.slice(-1)}`);
    for (const [code, name] of stockRows.slice(0, 3)) addReport("2026-10-08", code, name, "증권사 A");

    database.prepare("INSERT INTO operation_events VALUES (?, ?, ?, ?, ?, ?, ?)").run(
      1, "2026-10-12T09:00:00+09:00", "poll-news", "scheduled-collect", "success", OBSERVATION_DATE,
      "target_stock_codes=000006,000001,000003",
    );

    const addCategory = database.prepare("INSERT INTO category_master VALUES (?, ?, ?, ?)");
    const sectors = ["반도체", "반도체", "IT서비스", "자동차", "화학", "기계", "N/A"];
    for (let index = 0; index < stockRows.length; index += 1) {
      const [code, name] = stockRows[index];
      const key = `S${index + 1}`;
      const displayName = sectors[index];
      addCategory.run("sector", key, displayName, 1);
      database.prepare("INSERT INTO category_membership_snapshots VALUES (?, ?, ?, ?, ?)").run(
        "2026-10-10", "sector", key, displayName, code,
      );
      database.prepare("INSERT INTO stock_metadata VALUES (?, ?, ?, ?)").run(code, name, key, displayName);
    }
    addCategory.run("sector", "DISABLED", "비활성 분류", 0);
    database.prepare("INSERT INTO category_membership_snapshots VALUES (?, ?, ?, ?, ?)").run(
      "2026-10-10", "sector", "DISABLED", "비활성 분류", "000001",
    );
    const themes = ["AI반도체", "AI반도체", "포털", "자동차", "화학", "기계", "THEME7"];
    for (let index = 0; index < stockRows.length; index += 1) {
      const [code] = stockRows[index];
      const name = themes[index];
      database.prepare("INSERT INTO stock_theme_memberships VALUES (?, ?, ?)").run(`T${index + 1}`, name, code);
    }

    const addMarket = database.prepare("INSERT INTO stock_market_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    for (let index = 0; index < 25; index += 1) {
      const day = new Date(`${OBSERVATION_DATE}T00:00:00.000Z`);
      day.setUTCDate(day.getUTCDate() - index);
      const date = day.toISOString().slice(0, 10);
      const close = 12000 - index * 100;
      const volume = 1000 + index * 100;
      addMarket.run(date, "000001", "삼성전자", "KOSPI", null, close, null, 1.25, null, close + 100, close - 100, volume, close * volume, null, null, `${date}T20:00:00+09:00`, "toss_openapi");
      if (index === 0) {
        addMarket.run(date, "000001", "삼성전자", "KOSPI", null, 99999, null, 99, null, null, null, 999999, 999999999, null, null, `${date}T20:01:00+09:00`, "krx");
      }
    }

    const addFlow = database.prepare("INSERT INTO stock_investor_flow_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    for (let index = 0; index < 31; index += 1) {
      const day = new Date(`${OBSERVATION_DATE}T00:00:00.000Z`);
      day.setUTCDate(day.getUTCDate() - index);
      const date = day.toISOString().slice(0, 10);
      for (const [investor, net] of [["개인", -(index + 1)], ["외국인", index + 1], ["기관합계", index % 2 === 0 ? index + 1 : -(index + 1)]]) {
        addFlow.run(date, "000001", "삼성전자", "KOSPI", investor, null, null, net, null, null, net * 1000, "주", "원", null, null, `${date}T20:00:00+09:00`, "toss_openapi");
        addFlow.run(date, "000001", "삼성전자", "KOSPI", investor, null, null, 999999, null, null, 999999, "주", "원", null, null, `${date}T20:00:00+09:00`, "krx_data_market");
      }
    }
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    process.env.STOCK_MONITOR_HOLIDAYS = "";
    const beforeRead = statSync(databasePath);
    const direct = service.getObservationSummarySnapshot(OBSERVATION_DATE, new Date(FIXED_NOW));
    const routeResponse = route.GET(new Request(`http://next.local/api/observation-summary?date=${OBSERVATION_DATE}&date=2026-02-30&limit=1&ignored=value`));
    assert.equal(routeResponse.status, 200);
    const routed = await routeResponse.json();
    const legacyFallback = service.getObservationSummarySnapshot("2026-10-08", new Date(FIXED_NOW));
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = [
      "import json, os, sys",
      "from datetime import date, datetime",
      "from pathlib import Path",
      "from types import SimpleNamespace",
      "from zoneinfo import ZoneInfo",
      "from stock_monitor.cli import _build_web_view_observation_summary, _web_view_selected_candidate_rows, build_web_view_candidate_evidence_snapshot",
      "from stock_monitor.config import DEFAULT_MARKET_HOLIDAYS",
      "from stock_monitor.db.repository import StockMonitorRepository",
      "extra = {date.fromisoformat(item) for item in os.environ.get('STOCK_MONITOR_HOLIDAYS', '').split(',') if item}",
      "config = SimpleNamespace(timezone='Asia/Seoul', holiday_overrides=DEFAULT_MARKET_HOLIDAYS | extra)",
      "repository = StockMonitorRepository(Path(sys.argv[1]), timezone='Asia/Seoul')",
      "fixed_now = datetime.fromisoformat(sys.argv[2]).astimezone(ZoneInfo('Asia/Seoul'))",
      "def build(raw_date):",
      "    business_date = date.fromisoformat(raw_date)",
      "    candidate = build_web_view_candidate_evidence_snapshot(config, repository, business_date=business_date, limit=2, now=fixed_now)",
      "    priority = [str(row.get('stock_code') or '') for row in _web_view_selected_candidate_rows(candidate.get('rows', [])) if str(row.get('stock_code') or '')]",
      "    return _build_web_view_observation_summary(repository, business_date, summaries=repository.list_daily_summaries(business_date), sectors=repository.list_category_rollups_by_display_name_for_business_date(business_date, 'sector'), themes=repository.list_category_rollups_by_display_name_for_business_date(business_date, 'theme'), holiday_overrides=config.holiday_overrides, priority_stock_codes=priority)",
      "with repository.read_session(): results = [build(item) for item in json.loads(sys.argv[3])]",
      "print(json.dumps(results, ensure_ascii=False, separators=(',', ':'))) ",
    ].join("\n");
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const python = spawnSync("python", ["-c", pythonScript, databasePath, FIXED_NOW, JSON.stringify([OBSERVATION_DATE, "2026-10-08"])], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python observation summary DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout);
    assert.deepEqual(direct, pythonSnapshots[0]);
    assert.deepEqual(legacyFallback, pythonSnapshots[1]);
    assert.deepEqual(routed, direct);

    const beforeSharedRead = statSync(databasePath);
    const sharedDatabase = new DatabaseSync(databasePath, { readOnly: true });
    let sharedDatabaseSnapshot;
    try {
      sharedDatabase.exec("PRAGMA query_only = ON; BEGIN");
      const configuredDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
      process.env.STOCK_MONITOR_DB_PATH = join(tempRoot, "must-not-open.db");
      try {
        sharedDatabaseSnapshot = service.buildObservationSummaryFromDatabase(
          sharedDatabase,
          OBSERVATION_DATE,
          new Date(FIXED_NOW),
        );
      } finally {
        process.env.STOCK_MONITOR_DB_PATH = configuredDatabasePath;
        sharedDatabase.exec("ROLLBACK");
      }
    } finally {
      sharedDatabase.close();
    }
    const afterSharedRead = statSync(databasePath);
    assert.deepEqual(sharedDatabaseSnapshot, pythonSnapshots[0]);
    assert.equal(afterSharedRead.size, beforeSharedRead.size);
    assert.equal(afterSharedRead.mtimeMs, beforeSharedRead.mtimeMs);

    assert.equal(isObservationSummarySnapshot(direct, OBSERVATION_DATE), true);
    assert.equal(direct.source, "stored_report_toss_observation_summary");
    assert.equal(direct.read_only, true);
    assert.equal(direct.live_fetch, false);
    assert.equal(direct.scoring, false);
    assert.equal(direct.recommendation, false);
    assert.equal(direct.market_mood.label, "시장 분위기");
    assert.equal(direct.market_mood.display, "리포트 29건이 7종목에 모였습니다.");
    assert.deepEqual(direct.report_concentration.items.slice(0, 2).map((item) => item.stock_code), ["000006", "000001"]);
    assert.deepEqual(direct.report_concentration.items.slice(2, 4).map((item) => item.stock_code), ["000002", "000003"]);
    const samsung = direct.report_concentration.items.find((item) => item.stock_code === "000001");
    assert.equal(samsung.report_intensity.five_business_day_report_count, 6);
    assert.equal(samsung.report_intensity.five_business_day_active_dates, 4);
    assert.equal(samsung.target_price_revision.direction, "up");
    const flow = direct.flow_reference.items.find((item) => item.stock_code === "000001");
    assert.deepEqual(flow.windows.map((window) => window.days), [5, 10, 20, 31]);
    assert.deepEqual(flow.windows.map((window) => window.observed_days), [5, 10, 20, 31]);
    assert.equal(flow.windows[0].foreign_net_buy_amount, 15);
    assert.equal(flow.windows[0].individual_net_buy_amount, -15);
    assert.equal(flow.persistence.foreign.streak_days, 31);
    assert.equal(direct.flow_reference.items.length, 1);
    const price = direct.price_volume_reference.items.find((item) => item.stock_code === "000001");
    assert.equal(price.reference_date, OBSERVATION_DATE);
    assert.equal(price.close_price, 12000);
    assert.equal(price.close_position_20d_percent, 100);
    assert.equal(direct.sector_breadth.sectors.length, 4);
    assert.equal(direct.sector_breadth.themes.length, 4);
    assert.equal(direct.sector_breadth.sectors[0].display_name, "반도체");
    assert.equal(direct.sector_breadth.sectors[0].stock_count, 2);
    assert.equal(direct.sector_breadth.themes[0].mapping_source, "latest_mapping_fallback");
    assert.equal(legacyFallback.sector_breadth.sectors[0].mapping_source, "latest_mapping_fallback");
    assert.equal(recursivelyContainsForbiddenSignal(direct), false);

    for (const response of [route.HEAD(), route.OPTIONS(), route.POST(), route.PUT(), route.PATCH(), route.DELETE()]) {
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(route.GET(new Request("http://next.local/api/observation-summary")).status, 400);
    assert.equal(route.GET(new Request("http://next.local/api/observation-summary?date=2026-02-30")).status, 400);
    assert.equal(route.GET(new Request("http://next.local/api/observation-summary?date=2026-02-30&date=2026-10-12")).status, 400);

    const writable = new DatabaseSync(databasePath);
    writable.exec("BEGIN IMMEDIATE; ROLLBACK");
    writable.close();
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = previousTimezone;
    if (previousHolidays === undefined) delete process.env.STOCK_MONITOR_HOLIDAYS;
    else process.env.STOCK_MONITOR_HOLIDAYS = previousHolidays;
    try { database.close(); } catch { /* The fixture closes before read verification. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("observation summary route returns a generic failure and releases its read transaction", async () => {
  const route = await import("../src/app/api/observation-summary/route.ts");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-observation-error-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    database.exec("CREATE TABLE unrelated (value TEXT)");
    database.close();
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const response = route.GET(new Request(`http://next.local/api/observation-summary?date=${OBSERVATION_DATE}`));
    assert.equal(response.status, 503);
    assert.equal(await response.text(), "observation summary unavailable");
    const writable = new DatabaseSync(databasePath);
    writable.exec("BEGIN IMMEDIATE; ROLLBACK");
    writable.close();
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* Closed before exercising the error path. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
