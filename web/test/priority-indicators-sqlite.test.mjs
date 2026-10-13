import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, readTossOpenApiConfig } from "../src/server/toss-openapi.ts";
import { isMainTop2IndicatorsSnapshot } from "../src/domain/main-top2.ts";
import { PriorityIndicatorsService } from "../src/server/priority-indicators.ts";
import * as route from "../src/app/api/priority-indicators/route.ts";

const businessDate = "2026-07-10";
const clientId = "private-client-id-sentinel";
const clientSecret = "private-client-secret-sentinel";
const accessToken = "private-access-token-sentinel";
const fetchedAt = `${businessDate}T16:00:00+09:00`;

function configured() {
  return readTossOpenApiConfig({
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID: clientId,
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET: clientSecret,
    STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED: "true",
    STOCK_MONITOR_TOSS_OPENAPI_BASE_URL: TOSS_OPENAPI_BASE_URL,
    STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS: "5",
  });
}

function historyCandles(code, count = 220) {
  return Array.from({ length: count }, (_, offset) => {
    const date = new Date(`${businessDate}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - offset);
    const close = (code === "005930" ? 700 : 1200) + (count - offset) / 10;
    return {
      timestamp: `${date.toISOString().slice(0, 10)}T00:00:00+09:00`,
      openPrice: String(close - 1), highPrice: String(close + 2), lowPrice: String(close - 2),
      closePrice: String(close), volume: String(100 + offset), currency: "KRW",
    };
  });
}

function pythonRouteFixture(projectRoot, tempRoot, databasePath) {
  const script = [
    "import json, sys, threading, urllib.request",
    "from datetime import date, datetime",
    "from pathlib import Path",
    "from stock_monitor.cli import RuntimeConfig, create_web_view_server",
    "from stock_monitor.db.repository import StockMonitorRepository",
    "from stock_monitor.models import Report, TossStockUniverseEntry",
    "root, database_path = Path(sys.argv[1]), Path(sys.argv[2])",
    "config = RuntimeConfig.from_env(root_dir=root)",
    "repository = StockMonitorRepository(database_path, timezone=config.timezone); repository.initialize()",
    "selected = date.fromisoformat('2026-07-10')",
    "reports = []",
    "for name, code, broker, minute, suffix in [('삼성전자','005930','NH투자증권',0,1),('SK하이닉스','000660','KB증권',2,1),('삼성전자','005930','KB증권',4,2),('SK하이닉스','000660','NH투자증권',6,2)]:",
    "    reports.append(Report(stock_name=name, stock_code=code, title=f'{name} report {suffix}', broker_name=broker, published_at=datetime(2026,7,10,9,minute), business_date=selected, collected_at=datetime(2026,7,10,9,minute+1), source_id=f'indicator-{code}-{suffix}', identity_key=f'indicator-{code}-{suffix}'))",
    "repository.insert_reports(reports); repository.rebuild_daily_summaries(selected)",
    "repository.upsert_toss_stock_universe_cache([",
    "    TossStockUniverseEntry(business_date=selected, market='KOSPI', stock_code='005930', stock_name='삼성전자', security_type='STOCK', is_common_share=True, isin_code='KR7005930003', fetched_at=datetime(2026,7,10,20,5)),",
    "    TossStockUniverseEntry(business_date=selected, market='KOSPI', stock_code='000660', stock_name='SK하이닉스', security_type='STOCK', is_common_share=True, isin_code='KR7000660001', fetched_at=datetime(2026,7,10,20,5)),",
    "])",
    "def candles(code):",
    "    values = []",
    "    for offset in range(220):",
    "        day = date.fromordinal(selected.toordinal() - offset)",
    "        close = (700 if code == '005930' else 1200) + (220 - offset) / 10",
    "        values.append({'timestamp': f'{day.isoformat()}T00:00:00+09:00', 'openPrice': str(close-1), 'highPrice': str(close+2), 'lowPrice': str(close-2), 'closePrice': str(close), 'volume': str(100+offset), 'currency':'KRW'})",
    "    return values",
    "class Provider:",
    "    configured = True",
    "    def get_priority_stock_daily_history(self, *, priority_symbols, as_of):",
    "        return {'configured':True, 'live_fetch':True, 'page_size':200, 'max_pages':4, 'fetched_at':'2026-07-10T16:00:00+09:00', 'items':[{'symbol':code,'candles':candles(code),'pages_fetched':2,'history_status':'complete'} for code in priority_symbols]}",
    "server = create_web_view_server(config, repository, host='127.0.0.1', port=0, limit=5, toss_quote_provider=Provider())",
    "thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()",
    "try:",
    "    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/priority-indicators?date=2026-07-10', timeout=10) as response:",
    "        print(response.read().decode('utf-8'))",
    "finally:",
    "    server.shutdown(); server.server_close(); thread.join(timeout=5)",
  ].join("\n");
  const result = spawnSync("python", ["-c", script, tempRoot, databasePath], {
    cwd: projectRoot,
    encoding: "utf8",
    timeout: 30_000,
    env: {
      ...process.env,
      PYTHONPATH: [join(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter),
      STOCK_MONITOR_DB_PATH: databasePath,
      STOCK_MONITOR_TIMEZONE: "Asia/Seoul",
      STOCK_MONITOR_HOLIDAYS: "",
      PYTHONIOENCODING: "utf-8",
    },
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

function token() {
  return new Response(JSON.stringify({ access_token: accessToken, token_type: "Bearer", expires_in: 3600 }));
}

test("Next priority indicator DTO matches Python using only stored Top2 and read-only SQLite", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-priority-indicators-"));
  const databasePath = join(tempRoot, "fixture.db");
  const envNames = ["STOCK_MONITOR_DB_PATH", "STOCK_MONITOR_TIMEZONE", "STOCK_MONITOR_HOLIDAYS"];
  const previousEnv = Object.fromEntries(envNames.map((name) => [name, process.env[name]]));
  try {
    const python = pythonRouteFixture(projectRoot, tempRoot, databasePath);
    const beforeRead = statSync(databasePath);
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    process.env.STOCK_MONITOR_HOLIDAYS = "";

    const requests = [];
    const pages = Object.fromEntries(["005930", "000660"].map((code) => [code, historyCandles(code)]));
    const fetchImpl = async (input, init) => {
      const url = new URL(String(input));
      requests.push({ url, init });
      if (url.pathname === "/oauth2/token") return token();
      assert.equal(url.origin, TOSS_OPENAPI_BASE_URL);
      assert.equal(url.pathname, "/api/v1/candles");
      assert.equal(init.method, "GET");
      assert.equal(init.redirect, "error");
      assert.ok(init.signal instanceof AbortSignal);
      assert.equal(url.searchParams.get("interval"), "1d");
      assert.equal(url.searchParams.get("count"), "200");
      assert.equal(url.searchParams.get("adjusted"), "true");
      const code = url.searchParams.get("symbol");
      const cursor = url.searchParams.get("before");
      const values = pages[code];
      assert.ok(values, `server-selected symbol ${code}`);
      const start = cursor === `${businessDate}T23:59:59+09:00` ? 0 : 200;
      return new Response(JSON.stringify({ result: {
        candles: values.slice(start, start + 200),
        nextBefore: start === 0 ? `${values[199].timestamp}` : null,
      } }));
    };
    const service = new PriorityIndicatorsService({
      config: configured(), fetchImpl, now: () => new Date(fetchedAt),
    });
    const next = await service.getIndicators(businessDate);
    const afterRead = statSync(databasePath);

    assert.deepEqual(next.payload, python);
    assert.equal(next.status, 200);
    assert.deepEqual(next.payload.items.map((item) => item.stock_code), ["005930", "000660"]);
    assert.equal(isMainTop2IndicatorsSnapshot(next.payload, businessDate, ["005930", "000660"]), true);
    assert.deepEqual(next.payload.items.map((item) => item.market_source), ["stored_toss_stock_universe", "stored_toss_stock_universe"]);
    assert.ok(next.payload.items.every((item) => item.available));
    assert.equal(next.payload.items[0].candle_count, 220);
    assert.equal(next.payload.items[0].pages_fetched, 2);
    assert.equal(next.payload.items[0].history_status, "complete");
    assert.equal(next.payload.items[0].snapshot.sourceFetchedAt, fetchedAt);
    assert.equal(next.payload.items[0].snapshot.barAsOf, businessDate);
    assert.equal(next.payload.items[0].snapshot.indicators.movingAverages.sma200 !== null, true);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.equal(requests.length, 5);
    assert.deepEqual(requests.slice(1).map(({ url }) => [url.searchParams.get("symbol"), url.searchParams.get("before")]), [
      ["005930", `${businessDate}T23:59:59+09:00`], ["005930", "2025-12-23T00:00:00+09:00"],
      ["000660", `${businessDate}T23:59:59+09:00`], ["000660", "2025-12-23T00:00:00+09:00"],
    ]);
    assert.doesNotMatch(JSON.stringify(next.payload), /private-(?:client-id|client-secret|access-token)-sentinel/);
  } finally {
    for (const name of envNames) {
      if (previousEnv[name] === undefined) delete process.env[name];
      else process.env[name] = previousEnv[name];
    }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("priority indicators route is GET-only and rejects malformed or arbitrary query input", async () => {
  const invalidDate = await route.GET(new Request("http://next.local/api/priority-indicators?date=2026-02-30"));
  assert.equal(invalidDate.status, 400);
  const extra = await route.GET(new Request(`http://next.local/api/priority-indicators?date=${businessDate}&symbols=005930`));
  assert.equal(extra.status, 400);
  const post = await route.POST(new Request(`http://next.local/api/priority-indicators?date=${businessDate}`, { method: "POST" }));
  assert.equal(post.status, 405);
  assert.equal(post.headers.get("allow"), "GET");
  assert.equal(route.HEAD().status, 405);
  assert.equal(route.OPTIONS().status, 405);
});

test("priority indicator transport timeout keeps the Python per-item timeout state", async () => {
  const service = new PriorityIndicatorsService({
    config: configured(),
    loadCandidates: () => [{
      code: "005930", name: "삼성전자", market: "KOSPI",
      marketSource: "selected_date_toss_market_reference", marketSourceDate: businessDate,
    }],
    fetchImpl: async (input) => new URL(String(input)).pathname === "/oauth2/token"
      ? token()
      : Promise.reject(new DOMException("private timeout detail", "TimeoutError")),
    now: () => new Date(fetchedAt),
  });
  const result = await service.getIndicators(businessDate);
  assert.equal(result.status, 200);
  assert.equal(result.payload.live_fetch, true);
  assert.equal(result.payload.items[0].available, false);
  assert.equal(result.payload.items[0].reason, "provider_timeout");
  assert.doesNotMatch(JSON.stringify(result.payload), /private timeout detail|private-access-token-sentinel/);
});

test("priority indicator history preserves fractional timezone cursors", async () => {
  const code = "005930";
  const values = historyCandles(code);
  const cursors = [
    "2026-07-09T00:00:00.000123+09:00",
    "2026-07-09T00:00:00.000122+09:00",
  ];
  const requestedCursors = [];
  const service = new PriorityIndicatorsService({
    config: configured(),
    loadCandidates: () => [{
      code, name: "삼성전자", market: "KOSPI",
      marketSource: "selected_date_toss_market_reference", marketSourceDate: businessDate,
    }],
    fetchImpl: async (input) => {
      const url = new URL(String(input));
      if (url.pathname === "/oauth2/token") return token();
      requestedCursors.push(url.searchParams.get("before"));
      const pageIndex = requestedCursors.length - 1;
      return new Response(JSON.stringify({ result: {
        candles: pageIndex === 0 ? values.slice(0, 200) : pageIndex === 1 ? values.slice(200) : [],
        nextBefore: cursors[pageIndex] ?? null,
      } }));
    },
    now: () => new Date(fetchedAt),
  });

  const result = await service.getIndicators(businessDate);

  assert.equal(result.payload.items[0].available, true);
  assert.equal(result.payload.items[0].pages_fetched, 3);
  assert.equal(result.payload.items[0].candle_count, 220);
  assert.deepEqual(requestedCursors, [
    `${businessDate}T23:59:59+09:00`,
    cursors[0],
    cursors[1],
  ]);
});
