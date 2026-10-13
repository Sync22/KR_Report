import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isCandidateEvidenceSnapshot } from "../src/domain/candidate-evidence.ts";

test("candidate evidence preserves stored cohort order and drives latest-date-only Top2 quotes", async () => {
  const service = await import("../src/server/candidate-evidence.ts");
  const route = await import("../src/app/api/candidate-evidence/route.ts");
  const quoteRoute = await import("../src/app/api/priority-current-quotes/route.ts");
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-candidate-evidence-"));
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
    ].join(";\n"));

    const addSummary = database.prepare("INSERT INTO daily_stock_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    const addSummaryRow = (date, code, name, mentions, brokers, min = null, max = null, opinion = "N/A") => addSummary.run(
      date, name, code, mentions, brokers, min, max, opinion, date + "T20:00:00+09:00",
    );
    addSummaryRow("2026-10-12", "000001", "삼성전자", 2, "증권사 A (1), 증권사 B (1)", 120000, 130000, "매수");
    addSummaryRow("2026-10-12", "000002", "SK하이닉스", 2, "증권사 A (1)");
    addSummaryRow("2026-10-12", "000003", "NAVER", 3, "증권사 A (1), 증권사 B (1)", 150000, null, "N/A");
    addSummaryRow("2026-10-08", "000001", "삼성전자", 2, "증권사 A (1)");
    addSummaryRow("2026-10-08", "000002", "SK하이닉스", 2, "증권사 A (1)");

    const addReport = database.prepare("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    const addReportRow = (date, code, name, title, broker, target, sourceId) => addReport.run(
      name, code, title, broker, date + "T09:00:00+09:00", date,
      target === null ? null : String(target), target, null, "N/A",
      date + "T09:05:00+09:00", "https://finance.naver.com/item/main.naver?code=" + code, sourceId, sourceId,
    );
    addReportRow("2026-10-12", "000001", "삼성전자", "삼성전자 AI 반도체 공급 계약 전망", "증권사 A", 120000, "a-1");
    addReportRow("2026-10-12", "000001", "삼성전자", "삼성전자 AI 반도체 실적 전망", "증권사 B", 130000, "a-2");
    addReportRow("2026-10-08", "000001", "삼성전자", "삼성전자 과거 리포트", "증권사 A", 90000, "a-old-1");
    addReportRow("2026-10-08", "000001", "삼성전자", "삼성전자 과거 리포트 추가", "증권사 A", 100000, "a-old-2");
    addReportRow("2026-10-12", "000002", "SK하이닉스", "SK하이닉스 공급 계약 확인", "증권사 A", null, "b-1");
    addReportRow("2026-10-12", "000002", "SK하이닉스", "SK하이닉스 리포트 추가", "증권사 A", null, "b-2");
    addReportRow("2026-10-08", "000002", "SK하이닉스", "SK하이닉스 과거 리포트", "증권사 A", null, "b-old-1");
    addReportRow("2026-10-08", "000002", "SK하이닉스", "SK하이닉스 과거 리포트 추가", "증권사 A", null, "b-old-2");
    addReportRow("2026-10-12", "000003", "NAVER", "NAVER 기업 검색 서비스 전망", "증권사 A", 150000, "c-1");
    addReportRow("2026-10-12", "000003", "NAVER", "NAVER 사업 실적 전망", "증권사 B", null, "c-2");
    addReportRow("2026-10-12", "000003", "NAVER", "NAVER 시장 분석", "증권사 A", null, "c-3");

    const addMarket = database.prepare("INSERT INTO stock_market_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    addMarket.run("2026-10-12", "000001", "삼성전자", "KOSPI", null, 125000, null, 1.2, null, null, null, 1000, 50000000, null, null, "2026-10-12T20:00:00+09:00", "toss_openapi");
    addMarket.run("2026-10-11", "000002", "SK하이닉스", "KOSPI", null, 200000, null, 1, null, null, null, 500, 10000000, null, null, "2026-10-11T20:00:00+09:00", "toss_openapi");
    for (const [date, close, change] of [["2026-10-08", 100000, 0], ["2026-10-12", 115000, 1], ["2026-10-13", 130000, 2]]) {
      addMarket.run(date, "000001", "삼성전자", "KOSPI", null, close, null, change, null, close + 1000, close - 1000, 1000, 40000000, null, null, date + "T16:00:00+09:00", "krx");
    }
    for (const [date, close] of [["2026-10-08", 1000], ["2026-10-12", 1020], ["2026-10-13", 1040]]) {
      database.prepare("INSERT INTO market_index_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
        date, "KOSPI", "stock", "코스피", close, null, 1, null, null, null, 0, 0, null, date + "T16:00:00+09:00", "krx",
      );
    }
    const addStockFlow = database.prepare("INSERT INTO stock_investor_flow_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    addStockFlow.run("2026-10-12", "000001", "삼성전자", "KOSPI", "외국인", 10, 20, 10, 100, 200, 100, "주", "원", null, null, "2026-10-12T20:00:00+09:00", "toss_openapi");
    addStockFlow.run("2026-10-08", "000001", "삼성전자", "KOSPI", "외국인", 0, 10, 10, 0, 100, 100, "주", "원", null, null, "2026-10-08T20:00:00+09:00", "krx_data_market");
    addStockFlow.run("2026-10-07", "000001", "삼성전자", "KOSPI", "외국인", 0, 5, 5, 0, 50, 50, "주", "원", null, null, "2026-10-07T20:00:00+09:00", "krx_data_market");
    database.prepare("INSERT INTO market_investor_flow_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
      "2026-10-12", "KOSPI", "외국인", 100, 200, 100, 10000, 20000, 10000, "주", "원", "2026-10-12T20:00:00+09:00", "toss_openapi",
    );
    database.prepare("INSERT INTO toss_priority_quote_baselines VALUES (?, ?, ?, ?, ?, ?, ?, ?)").run(
      "2026-10-12", "000001", "삼성전자", "20:00", 124000, "KRW", "toss_openapi", "2026-10-12T20:00:00+09:00",
    );
    database.prepare("INSERT INTO news_intelligence_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
      "run-b", "2026-10-12", "SK하이닉스", "000002", "[]", "fixture", 20, 1, 0, 1, 1, 1, "{}", "[]", "2026-10-12T10:00:00+09:00",
    );
    database.prepare("INSERT INTO report_linked_news_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
      "run-b", "e-b", "2026-10-12", "000002", "SK하이닉스", 1, "[\"b-1\"]", 1, 0, null,
      1, "2026-10-12", 1000000, 1, "mainnews", "SK하이닉스 공급 계약 체결",
      "장기 공급 계약을 체결했습니다.", "테스트 뉴스", "2026-10-12T09:30:00+09:00",
      "https://example.test/sk-contract", "SK하이닉스", "direct", "title", "direct", "긍정 근거",
      "Positive", 1, "[\"Supply\"]", "Positive", "공급 계약 확인", "positive_direct_news",
      "strengthen_report_candidate", "긍정 뉴스가 확인됐습니다.", "{}", "2026-10-12T10:01:00+09:00",
      "https://example.test/sk-contract", "independent", "fixture_verified",
    );
    database.prepare("INSERT INTO operation_events VALUES (?, ?, ?, ?, ?, ?, ?)").run(
      1, "2026-10-12T09:00:00+09:00", "poll-news", "scheduled-collect", "success", "2026-10-12", "target_stock_codes=000002,000001,999999",
    );
    database.close();

    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    process.env.STOCK_MONITOR_HOLIDAYS = "";
    const now = new Date("2026-10-12T10:00:00+09:00");
    const beforeRead = statSync(databasePath);
    const directRegular = service.getCandidateEvidenceSnapshot("2026-10-12", 8, now);
    const directFallback = service.getCandidateEvidenceSnapshot("2026-10-08", 8, now);
    const regularRouteResponse = route.GET(new Request("http://next.local/api/candidate-evidence?date=2026-10-12&limit=999&ignored=1"));
    assert.equal(regularRouteResponse.status, 200);
    const regularRoute = await regularRouteResponse.json();
    const oneRouteResponse = route.GET(new Request("http://next.local/api/candidate-evidence?date=2026-10-12&limit=1"));
    assert.equal(oneRouteResponse.status, 200);
    const oneRoute = await oneRouteResponse.json();

    const originalFetch = globalThis.fetch;
    const originalPythonUrl = process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL;
    const quoteRequests = [];
    process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL = "http://127.0.0.1:1";
    globalThis.fetch = async (input, init) => {
      const url = new URL(String(input));
      quoteRequests.push({ url: url.href, method: init?.method ?? "GET", timeout: init?.signal instanceof AbortSignal, cache: init?.cache, redirect: init?.redirect });
      if (url.pathname === "/api/domestic/detail/000002/detail") return new Response(JSON.stringify({
        itemname: "SK하이닉스", nowPrice: "70,500", prevChangeRate: "1.2", tradeAmount: "1,234,567",
        marketStatus: "장중", tradeTime: "20261012093000",
      }), { status: 200, headers: { "content-type": "application/json" } });
      return new Response(JSON.stringify({
        itemname: "삼성전자", nowPrice: "malformed", prevChangeRate: "-", tradeAmount: null,
        marketStatus: "", tradeTime: "not-a-time",
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    let quoteResponse;
    try {
      quoteResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12"));
    } finally {
      globalThis.fetch = originalFetch;
      if (originalPythonUrl === undefined) delete process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL;
      else process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL = originalPythonUrl;
    }
    assert.equal(quoteResponse.status, 200);
    const quoteSnapshot = await quoteResponse.json();
    assert.equal(quoteSnapshot.surface, "web-view-priority-current-quotes");
    assert.equal(quoteSnapshot.read_only, true);
    assert.equal(quoteSnapshot.live_fetch, true);
    assert.equal(quoteSnapshot.writes_db, false);
    assert.equal(quoteSnapshot.sends_telegram, false);
    assert.equal(quoteSnapshot.registers_scheduler, false);
    assert.equal(quoteSnapshot.affects_ordering, false);
    assert.equal(quoteSnapshot.priority_date, "2026-10-12");
    assert.equal(quoteSnapshot.latest_business_date, "2026-10-12");
    assert.match(quoteSnapshot.checked_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+09:00$/);
    assert.deepEqual(quoteSnapshot.items, [
      { stock_code: "000002", stock_name: "SK하이닉스", current_price: 70500, change_percent: 1.2,
        trade_amount: 1234567, market_status: "장중", trade_time: "2026-10-12T09:30:00" },
      { stock_code: "000001", stock_name: "삼성전자", current_price: null, change_percent: null,
        trade_amount: null, market_status: null, trade_time: null },
    ]);
    assert.deepEqual(quoteSnapshot.errors, []);
    assert.deepEqual(quoteRequests, [
      { url: "https://stock.naver.com/api/domestic/detail/000002/detail?codeType=KRX", method: "GET", timeout: true, cache: "no-store", redirect: "error" },
      { url: "https://stock.naver.com/api/domestic/detail/000001/detail?codeType=KRX", method: "GET", timeout: true, cache: "no-store", redirect: "error" },
    ]);

    const priorDateResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-08"));
    assert.equal(priorDateResponse.status, 409);
    const priorDateSnapshot = await priorDateResponse.json();
    assert.equal(priorDateSnapshot.reason, "latest_business_date_only");
    assert.equal(priorDateSnapshot.latest_business_date, "2026-10-12");
    assert.deepEqual(priorDateSnapshot.items, []);
    assert.equal(quoteRequests.length, 2, "historical requests must not contact Naver");

    const arbitraryCodeResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12&symbols=005930"));
    assert.equal(arbitraryCodeResponse.status, 400, "browser-supplied stock codes are rejected");
    assert.equal((await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-02-30"))).status, 400);
    assert.equal((await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12&date=2026-10-08"))).status, 400);
    assert.equal(quoteRequests.length, 2, "invalid dates and query parameters must not contact Naver");
    for (const method of ["HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]) {
      const response = await quoteRoute[method](new Request("http://next.local/api/priority-current-quotes?date=2026-10-12", { method }));
      assert.equal(response.status, 405, `${method} must be rejected`);
      assert.equal(response.headers.get("allow"), "GET");
    }

    const failingFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      if (String(input).includes("000002")) return new Response("[]", { status: 200 });
      throw new Error("provider detail must not be exposed");
    };
    let failedQuoteResponse;
    try {
      failedQuoteResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12"));
    } finally {
      globalThis.fetch = failingFetch;
    }
    assert.equal(failedQuoteResponse.status, 200);
    const failedQuoteSnapshot = await failedQuoteResponse.json();
    assert.deepEqual(failedQuoteSnapshot.items, []);
    assert.deepEqual(failedQuoteSnapshot.errors, ["000002", "000001"]);
    assert.doesNotMatch(JSON.stringify(failedQuoteSnapshot), /provider detail/);

    const partialFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      if (String(input).includes("000002")) return new Response(JSON.stringify({ itemname: "SK하이닉스", nowPrice: "70500" }), { status: 200 });
      throw new Error("one quote failed");
    };
    let partialQuoteResponse;
    try {
      partialQuoteResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12"));
    } finally {
      globalThis.fetch = partialFetch;
    }
    const partialQuoteSnapshot = await partialQuoteResponse.json();
    assert.deepEqual(partialQuoteSnapshot.items.map((item) => item.stock_code), ["000002"]);
    assert.deepEqual(partialQuoteSnapshot.errors, ["000001"]);

    const redirectFetch = globalThis.fetch;
    const redirectRequests = [];
    globalThis.fetch = async (input, init) => {
      redirectRequests.push({ url: String(input), redirect: init?.redirect });
      return new Response(null, { status: 302, headers: { location: "http://127.0.0.1:1/private" } });
    };
    let redirectQuoteResponse;
    try {
      redirectQuoteResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12"));
    } finally {
      globalThis.fetch = redirectFetch;
    }
    const redirectQuoteSnapshot = await redirectQuoteResponse.json();
    assert.deepEqual(redirectRequests.map((item) => item.redirect), ["error", "error"]);
    assert.deepEqual(redirectQuoteSnapshot.errors, ["000002", "000001"]);

    const oversizedPayload = JSON.stringify({ itemname: "SK하이닉스", nowPrice: "70500", pad: "x".repeat(300_000) });
    const oversizedFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(oversizedPayload, { status: 200, headers: { "content-type": "application/json" } });
    let oversizedQuoteResponse;
    try {
      oversizedQuoteResponse = await quoteRoute.GET(new Request("http://next.local/api/priority-current-quotes?date=2026-10-12"));
    } finally {
      globalThis.fetch = oversizedFetch;
    }
    const oversizedQuoteSnapshot = await oversizedQuoteResponse.json();
    assert.deepEqual(oversizedQuoteSnapshot.items, []);
    assert.deepEqual(oversizedQuoteSnapshot.errors, ["000002", "000001"]);

    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);

    const pythonScript = [
      "import json, sys",
      "from datetime import date, datetime",
      "from pathlib import Path",
      "from types import SimpleNamespace",
      "from zoneinfo import ZoneInfo",
      "from stock_monitor.cli import build_web_view_candidate_evidence_snapshot",
      "from stock_monitor.config import DEFAULT_MARKET_HOLIDAYS",
      "from stock_monitor.db.repository import StockMonitorRepository",
      "config = SimpleNamespace(timezone='Asia/Seoul', holiday_overrides=DEFAULT_MARKET_HOLIDAYS)",
      "repository = StockMonitorRepository(Path(sys.argv[1]), timezone='Asia/Seoul')",
      "cases = json.loads(sys.argv[2])",
      "result = [build_web_view_candidate_evidence_snapshot(config, repository, business_date=date.fromisoformat(item['date']), limit=item['limit'], now=datetime.fromisoformat(item['now'].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Seoul'))) for item in cases]",
      "print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))",
    ].join("\n");
    const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
    const pythonCases = [
      { date: "2026-10-12", limit: 8, now: "2026-10-12T10:00:00+09:00" },
      { date: "2026-10-08", limit: 8, now: "2026-10-12T10:00:00+09:00" },
      { date: "2026-10-12", limit: 20, now: regularRoute.now },
      { date: "2026-10-12", limit: 1, now: oneRoute.now },
    ];
    const python = spawnSync("python", ["-c", pythonScript, databasePath, JSON.stringify(pythonCases)], {
      cwd: projectRoot,
      env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
      encoding: "utf8",
      timeout: 30000,
    });
    assert.equal(python.status, 0, python.stderr || python.error?.message || "Python candidate DTO comparison failed");
    const pythonSnapshots = JSON.parse(python.stdout);
    const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
    assert.deepEqual(withoutNow(directRegular), withoutNow(pythonSnapshots[0]));
    assert.deepEqual(withoutNow(directFallback), withoutNow(pythonSnapshots[1]));
    assert.deepEqual(withoutNow(regularRoute), withoutNow(pythonSnapshots[2]));
    assert.deepEqual(withoutNow(oneRoute), withoutNow(pythonSnapshots[3]));

    assert.equal(isCandidateEvidenceSnapshot(directRegular, "2026-10-12"), true);
    assert.equal(directRegular.selection_basis, "regular_session_news_cohort");
    assert.deepEqual(directRegular.rows.filter((row) => row.selected).map((row) => row.stock_code), ["000002", "000001"]);
    assert.equal(directRegular.rows[0].news_observation_badge.positive_direct_count, 1);
    assert.equal(directRegular.rows[1].market_reference.business_date, "2026-10-12");
    assert.equal(directRegular.rows.find((row) => row.stock_code === "000002").market_reference, null);
    assert.equal(directFallback.selection_basis, "stored_candidate_evidence");
    assert.deepEqual(directFallback.rows.filter((row) => row.selected).map((row) => row.stock_code), ["000002", "000001"]);
    assert.equal(oneRoute.rows.length, 1);
    assert.equal(oneRoute.rows[0].selected, true);

    for (const response of [route.HEAD(), route.OPTIONS(), route.POST(), route.PUT(), route.PATCH(), route.DELETE()]) {
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(route.GET(new Request("http://next.local/api/candidate-evidence?date=2026-02-30")).status, 400);
    assert.equal(service.parseCandidateEvidenceLimit(null), 5);
    assert.equal(service.parseCandidateEvidenceLimit("invalid"), 5);
    assert.equal(service.parseCandidateEvidenceLimit("0"), 1);
    assert.equal(service.parseCandidateEvidenceLimit("999"), 20);

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
    try { database.close(); } catch { /* The fixture closes before service reads. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("candidate read transaction rolls back and closes after a failed read", async () => {
  const route = await import("../src/app/api/candidate-evidence/route.ts");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-candidate-error-"));
  const databasePath = join(tempRoot, "fixture.db");
  const database = new DatabaseSync(databasePath);
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    database.exec("CREATE TABLE unrelated (value TEXT)");
    database.close();
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const response = route.GET(new Request("http://next.local/api/candidate-evidence?date=2026-10-12"));
    assert.equal(response.status, 503);
    assert.equal(await response.text(), "candidate evidence unavailable");
    const writable = new DatabaseSync(databasePath);
    writable.exec("BEGIN IMMEDIATE; ROLLBACK");
    writable.close();
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    try { database.close(); } catch { /* Closed before exercising the read-only failure path. */ }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
