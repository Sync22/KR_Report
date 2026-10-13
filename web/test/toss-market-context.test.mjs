import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, readTossOpenApiConfig } from "../src/server/toss-openapi.ts";
import { TossMarketContextService } from "../src/server/toss-market-context.ts";
import * as route from "../src/app/api/toss-market-context/route.ts";

const businessDate = "2026-07-10";
const clientId = "private-client-id-sentinel";
const clientSecret = "private-client-secret-sentinel";
const accessToken = "private-access-token-sentinel";

function configured() {
  return readTossOpenApiConfig({
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID: clientId,
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET: clientSecret,
    STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED: "true",
    STOCK_MONITOR_TOSS_OPENAPI_BASE_URL: TOSS_OPENAPI_BASE_URL,
    STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS: "5",
  });
}

function token(value = accessToken) {
  return new Response(JSON.stringify({ access_token: value, token_type: "Bearer", expires_in: 3600 }));
}

function endpointResult(key) {
  if (key === "ranking") return {
    result: { rankedAt: "2026-07-10T09:15:00+09:00", rankings: [
      { rank: 1, symbol: "005930", currency: "KRW", price: { lastPrice: "70000", basePrice: "69000", changeRate: "0.0145" }, tradingVolume: "300", tradingAmount: "1000" },
      { rank: 2, symbol: "069500", currency: "KRW", price: { lastPrice: "42000" }, tradingVolume: "200", tradingAmount: "900" },
      { rank: 3, symbol: "000660", currency: "KRW", price: { lastPrice: "200000" }, tradingVolume: "100", tradingAmount: "800" },
    ] },
  };
  if (key === "prices") return { result: [
    { symbol: "KOSPI", timestamp: "2026-07-10T09:15:00+09:00", lastPrice: "3120.45" },
    { symbol: "KOSDAQ", timestamp: "2026-07-10T09:15:00+09:00", lastPrice: "812.34" },
  ] };
  if (key === "KOSPI/candles") return { result: { candles: [
    { timestamp: "2026-07-09T09:00:00+09:00", openPrice: "3090", highPrice: "3110", lowPrice: "3080", closePrice: "3100", volume: "1" },
  ] } };
  if (key === "KOSDAQ/candles") return { result: { candles: [
    { timestamp: "2026-07-09T09:00:00+09:00", openPrice: "790", highPrice: "810", lowPrice: "780", closePrice: "800", volume: "1" },
  ] } };
  if (key === "KOSPI/investor-trading" || key === "KOSDAQ/investor-trading") return { result: { records: [
    { date: businessDate, updatedAt: "2026-07-10T18:00:00+09:00", individual: { buyAmount: 100, sellAmount: 90 }, foreigner: { buyAmount: 200, sellAmount: 210 }, institution: { buyAmount: 80, sellAmount: 120, breakdown: { financialInvestment: { buyAmount: 60, sellAmount: 70 } } }, otherCorporation: { buyAmount: 20, sellAmount: 10 } },
  ] } };
  if (key === "stocks") return { result: [
    { symbol: "005930", name: "Samsung Electronics", market: "KOSPI", securityType: "STOCK" },
    { symbol: "069500", name: "KODEX 200", market: "KOSPI", securityType: "ETF" },
    { symbol: "000660", name: "SK hynix", market: "KOSPI", securityType: "STOCK" },
  ] };
  throw new Error(`unexpected endpoint ${key}`);
}

function mockFetch(requests, options = {}) {
  return async (input, init) => {
    const url = new URL(String(input));
    requests.push({ url, init });
    if (url.pathname === "/oauth2/token") return token();
    if (options.failEndpoint === url.pathname) return new Response("private provider response", { status: 503 });
    let key;
    if (url.pathname === "/api/v1/rankings") key = "ranking";
    else if (url.pathname === "/api/v1/market-indicators/prices") key = "prices";
    else if (/^\/api\/v1\/market-indicators\/(KOSPI|KOSDAQ)\/candles$/.test(url.pathname)) key = url.pathname.split("/").at(-2) + "/candles";
    else if (/^\/api\/v1\/market-indicators\/(KOSPI|KOSDAQ)\/investor-trading$/.test(url.pathname)) key = url.pathname.split("/").at(-2) + "/investor-trading";
    else if (url.pathname === "/api/v1/stocks") key = "stocks";
    else throw new Error(`unexpected Toss request ${url.pathname}`);
    const payload = endpointResult(key);
    const rateLimit = key === "ranking" ? "5" : "10";
    return new Response(JSON.stringify(payload), {
      headers: { "content-type": "application/json", "x-ratelimit-limit": rateLimit, "x-ratelimit-remaining": "9" },
    });
  };
}

function pythonRouteFixture(projectRoot, tempRoot, databasePath, scenario = "success", requestedDate = businessDate) {
  const script = [
    "import json, sys, threading, urllib.request, urllib.error",
    "from datetime import date, datetime",
    "from pathlib import Path",
    "from types import SimpleNamespace",
    "from stock_monitor.cli import RuntimeConfig, create_web_view_server",
    "from stock_monitor.db.repository import StockMonitorRepository",
    "from stock_monitor.models import Report",
    "from stock_monitor.fetch.toss_openapi import TOSS_OPENAPI_BASE_URL",
    "from stock_monitor.toss_openapi_web_view import TossPriorityQuoteProvider",
    "root, database_path, scenario, requested_date = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]",
    "config = RuntimeConfig.from_env(root_dir=root)",
    "repository = StockMonitorRepository(database_path, timezone=config.timezone); repository.initialize()",
    "selected = date.fromisoformat('2026-07-10')",
    "reports = [Report(stock_name=name, stock_code=code, title=f'{name} report {suffix}', broker_name=broker, published_at=datetime(2026,7,10,9,minute), business_date=selected, collected_at=datetime(2026,7,10,9,minute+1), source_id=f'market-context-{code}-{suffix}', identity_key=f'market-context-{code}-{suffix}') for name,code,broker,minute,suffix in [('삼성전자','005930','NH투자증권',0,1),('SK하이닉스','000660','KB증권',2,1),('삼성전자','005930','KB증권',4,2),('SK하이닉스','000660','NH투자증권',6,2)]]",
    "repository.insert_reports(reports); repository.rebuild_daily_summaries(selected)",
    "seen = []",
    "def fetch(**kwargs):",
    "    endpoint, params = kwargs['endpoint'], kwargs['params']; seen.append([endpoint.key, params])",
    "    key = endpoint.key",
    "    if scenario == 'metadata-failure' and key == 'market-ranking-stocks': raise RuntimeError('private metadata provider failure')",
    "    if key == 'ranking-kr-top20': result = {'rankedAt':'2026-07-10T09:15:00+09:00','rankings':[{'rank':1,'symbol':'005930','currency':'KRW','price':{'lastPrice':'70000','basePrice':'69000','changeRate':'0.0145'},'tradingVolume':'300','tradingAmount':'1000'},{'rank':2,'symbol':'069500','currency':'KRW','price':{'lastPrice':'42000'},'tradingVolume':'200','tradingAmount':'900'},{'rank':3,'symbol':'000660','currency':'KRW','price':{'lastPrice':'200000'},'tradingVolume':'100','tradingAmount':'800'}]} ",
    "    elif key == 'market-indicator-prices': result = [{'symbol':'KOSPI','timestamp':'2026-07-10T09:15:00+09:00','lastPrice':'3120.45'},{'symbol':'KOSDAQ','timestamp':'2026-07-10T09:15:00+09:00','lastPrice':'812.34'}]",
    "    elif key.endswith('/daily-candles') or key in ('market-indicator-kospi-daily-candles','market-indicator-kosdaq-daily-candles'):",
    "        market = 'KOSPI' if 'kospi' in key.lower() else 'KOSDAQ'; close = '3100' if market == 'KOSPI' else '800'; base = '3090' if market == 'KOSPI' else '790'; high = '3110' if market == 'KOSPI' else '810'; low = '3080' if market == 'KOSPI' else '780'; result = {'candles':[{'timestamp':'2026-07-09T09:00:00+09:00','openPrice':base,'highPrice':high,'lowPrice':low,'closePrice':close,'volume':'1'}]}",
    "    elif key.startswith('market-investor-'):",
    "        result = {'records':[{'date':params['until'],'updatedAt':params['until']+'T18:00:00+09:00','individual':{'buyAmount':100,'sellAmount':90},'foreigner':{'buyAmount':200,'sellAmount':210},'institution':{'buyAmount':80,'sellAmount':120,'breakdown':{'financialInvestment':{'buyAmount':60,'sellAmount':70}}},'otherCorporation':{'buyAmount':20,'sellAmount':10}}]} ",
    "    elif key == 'market-ranking-stocks': result = [{'symbol':'005930','name':'Samsung Electronics','market':'KOSPI','securityType':'STOCK'},{'symbol':'069500','name':'KODEX 200','market':'KOSPI','securityType':'ETF'},{'symbol':'000660','name':'SK hynix','market':'KOSPI','securityType':'STOCK'}]",
    "    else: raise AssertionError(key)",
    "    return SimpleNamespace(result=result, rate_limit={'limit':'5' if key == 'ranking-kr-top20' else '10','remaining':'9'})",
    "provider_config = SimpleNamespace(client_id='test-id', client_secret='test-secret', live_enabled=scenario != 'disabled', base_url=TOSS_OPENAPI_BASE_URL, timeout_seconds=5)",
    "provider = TossPriorityQuoteProvider(config=provider_config, issue_token=lambda **_kwargs: SimpleNamespace(access_token='test-token'), fetch_quotes=fetch)",
    "class Wrapper:",
    "    configured = provider.configured",
    "    def get_market_context(self, **kwargs):",
    "        self.priority_symbols = kwargs['priority_symbols']",
    "        return provider.get_market_context(**kwargs)",
    "wrapper = Wrapper()",
    "server = create_web_view_server(config, repository, host='127.0.0.1', port=0, limit=5, toss_quote_provider=wrapper)",
    "thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()",
    "try:",
    "    try:",
    "        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/toss-market-context?date={requested_date}', timeout=5) as response: status, payload = response.status, json.loads(response.read().decode('utf-8'))",
    "    except urllib.error.HTTPError as error: status, payload = error.code, json.loads(error.read().decode('utf-8'))",
    "finally:",
    "    server.shutdown(); server.server_close(); thread.join(timeout=5)",
    "print(json.dumps({'status':status,'payload':payload,'priority_symbols':list(getattr(wrapper,'priority_symbols',())),'requests':seen}))",
  ].join("\n");
  const result = spawnSync("python", ["-c", script, tempRoot, databasePath, scenario, requestedDate], {
    cwd: projectRoot,
    encoding: "utf8",
    timeout: 20_000,
    env: {
      ...process.env,
      PYTHONPATH: [join(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter),
      STOCK_MONITOR_DB_PATH: databasePath,
      STOCK_MONITOR_TIMEZONE: "Asia/Seoul",
      STOCK_MONITOR_HOLIDAYS: "",
    },
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("Next market-context DTO matches Python provider and route using stored Top2", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-market-context-"));
  const databasePath = join(tempRoot, "fixture.db");
  const envNames = ["STOCK_MONITOR_DB_PATH", "STOCK_MONITOR_TIMEZONE", "STOCK_MONITOR_HOLIDAYS"];
  const previousEnv = Object.fromEntries(envNames.map((name) => [name, process.env[name]]));
  try {
    const python = pythonRouteFixture(projectRoot, tempRoot, databasePath);
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    process.env.STOCK_MONITOR_HOLIDAYS = "";
    const beforeRead = statSync(databasePath);
    const requests = [];
    const service = new TossMarketContextService({ config: configured(), fetchImpl: mockFetch(requests) });
    const next = await service.getMarketContext(businessDate);
    const afterRead = statSync(databasePath);

    assert.equal(next.status, python.status);
    const expected = { ...python.payload };
    const actual = { ...next.payload };
    for (const payload of [expected, actual]) {
      assert.ok(Number.isFinite(Date.parse(payload.fetched_at)));
      payload.fetched_at = Date.parse(payload.fetched_at);
    }
    assert.ok(Math.abs(expected.fetched_at - actual.fetched_at) <= 5000);
    delete expected.fetched_at;
    delete actual.fetched_at;
    delete expected.latency_ms;
    delete actual.latency_ms;
    assert.deepEqual(actual, expected);
    assert.deepEqual(python.priority_symbols, ["005930", "000660"]);
    assert.deepEqual(next.payload.priority_overlap_symbols, ["005930", "000660"]);
    assert.deepEqual(requests.slice(1).map(({ url }) => url.pathname), [
      "/api/v1/rankings",
      "/api/v1/market-indicators/prices",
      "/api/v1/market-indicators/KOSPI/candles",
      "/api/v1/market-indicators/KOSDAQ/candles",
      "/api/v1/market-indicators/KOSPI/investor-trading",
      "/api/v1/market-indicators/KOSDAQ/investor-trading",
      "/api/v1/stocks",
    ]);
    for (const { url, init } of requests) {
      assert.equal(url.origin, TOSS_OPENAPI_BASE_URL);
      assert.equal(init.redirect, "error");
      assert.ok(init.signal instanceof AbortSignal);
      assert.equal(init.method, url.pathname === "/oauth2/token" ? "POST" : "GET");
    }
    assert.deepEqual(Object.fromEntries(requests[1].url.searchParams), {
      type: "MARKET_TRADING_AMOUNT", marketCountry: "KR", duration: "realtime", count: "20",
    });
    assert.deepEqual(Object.fromEntries(requests[2].url.searchParams), { symbols: "KOSPI,KOSDAQ" });
    for (const index of [3, 4]) assert.deepEqual(Object.fromEntries(requests[index].url.searchParams), { interval: "1d", count: "2" });
    for (const index of [5, 6]) assert.deepEqual(Object.fromEntries(requests[index].url.searchParams), { interval: "1d", count: "1", until: businessDate });
    assert.equal(requests.at(-1).url.searchParams.get("symbols"), "005930,069500,000660");
    assert.deepEqual(requests.slice(5, 7).map(({ url }) => url.searchParams.get("until")), [businessDate, businessDate]);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.doesNotMatch(JSON.stringify(next.payload), /test-id|test-secret|test-token|private-client|private-access/);

    const oldDate = await service.getMarketContext("2026-07-09");
    assert.equal(oldDate.status, 409);
    assert.equal(oldDate.payload.reason, "latest_business_date_only");
    assert.equal(oldDate.payload.latest_business_date, businessDate);

    const pythonDisabled = pythonRouteFixture(projectRoot, tempRoot, databasePath, "disabled");
    const disabledRequests = [];
    const disabled = await new TossMarketContextService({
      config: readTossOpenApiConfig({}),
      fetchImpl: mockFetch(disabledRequests),
    }).getMarketContext(businessDate);
    assert.equal(disabled.status, pythonDisabled.status);
    assert.deepEqual(disabled.payload, pythonDisabled.payload);
    assert.equal(disabledRequests.length, 0);

    const pythonPartial = pythonRouteFixture(projectRoot, tempRoot, databasePath, "metadata-failure");
    const failedRequests = [];
    const partial = await new TossMarketContextService({
      config: configured(),
      fetchImpl: mockFetch(failedRequests, { failEndpoint: "/api/v1/stocks" }),
    }).getMarketContext(businessDate);
    assert.equal(partial.status, pythonPartial.status);
    const expectedPartial = { ...pythonPartial.payload };
    const actualPartial = { ...partial.payload };
    for (const payload of [expectedPartial, actualPartial]) {
      payload.fetched_at = Date.parse(payload.fetched_at);
    }
    assert.ok(Math.abs(expectedPartial.fetched_at - actualPartial.fetched_at) <= 5000);
    delete expectedPartial.fetched_at;
    delete actualPartial.fetched_at;
    delete expectedPartial.latency_ms;
    delete actualPartial.latency_ms;
    assert.deepEqual(actualPartial, expectedPartial);
    assert.equal(partial.payload.stock_metadata_reason, "stock_metadata_unavailable");
    assert.doesNotMatch(JSON.stringify(partial.payload), /private metadata provider failure|private provider response|test-secret/);
  } finally {
    for (const name of envNames) {
      if (previousEnv[name] === undefined) delete process.env[name];
      else process.env[name] = previousEnv[name];
    }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("unavailable latest date and mismatched dates never call Toss", async () => {
  let calls = 0;
  const fetchImpl = async () => { calls += 1; throw new Error("upstream must remain unused"); };
  const service = new TossMarketContextService({
    config: configured(), fetchImpl,
    loadContext: () => ({ latestBusinessDate: "2026-07-10", symbols: ["005930", "000660"] }),
  });
  const oldDate = await service.getMarketContext("2026-07-09");
  assert.equal(oldDate.status, 409);
  assert.equal(oldDate.payload.reason, "latest_business_date_only");
  assert.equal(oldDate.payload.latest_business_date, businessDate);
  assert.equal(calls, 0);

  const unavailable = new TossMarketContextService({
    config: configured(), fetchImpl,
    loadContext: () => ({ latestBusinessDate: null, symbols: [] }),
  });
  const noDate = await unavailable.getMarketContext(businessDate);
  assert.equal(noDate.status, 409);
  assert.equal(noDate.payload.reason, "latest_business_date_unavailable");
  assert.equal(calls, 0);
});

test("market-context cache matches 30-second freshness, 300-second stale fallback, and single-flight calls", async () => {
  let now = 0;
  let fail = false;
  const requests = [];
  const service = new TossMarketContextService({
    config: configured(),
    loadContext: () => ({ latestBusinessDate: businessDate, symbols: ["005930", "000660"] }),
    clock: () => now,
    fetchImpl: async (...args) => {
      if (fail && String(args[0]).includes("/api/v1/rankings")) return new Response("private failure", { status: 503 });
      return mockFetch(requests)(...args);
    },
  });
  const first = await service.getMarketContext(businessDate);
  assert.equal(first.payload.cache, "miss");
  const cached = await service.getMarketContext(businessDate);
  assert.equal(cached.payload.cache, "hit");
  assert.equal(requests.length, 8);
  now = 31;
  fail = true;
  const stale = await service.getMarketContext(businessDate);
  assert.equal(stale.payload.cache, "stale");
  assert.equal(stale.payload.stale_reason, "upstream_unavailable");
  now = 301;
  const expired = await service.getMarketContext(businessDate);
  assert.equal(expired.status, 200);
  assert.equal(expired.payload.reason, "upstream_unavailable");
  assert.equal(expired.payload.live_fetch, false);

  let release;
  const gate = new Promise((resolveGate) => { release = resolveGate; });
  const singleRequests = [];
  const singleFlight = new TossMarketContextService({
    config: configured(),
    loadContext: () => ({ latestBusinessDate: businessDate, symbols: ["005930", "000660"] }),
    fetchImpl: async (...args) => {
      const url = new URL(String(args[0]));
      if (url.pathname === "/api/v1/rankings") await gate;
      return mockFetch(singleRequests)(...args);
    },
  });
  const concurrent = [singleFlight.getMarketContext(businessDate), singleFlight.getMarketContext(businessDate)];
  await new Promise((resolveWait) => setTimeout(resolveWait, 5));
  release();
  const shared = await Promise.all(concurrent);
  assert.deepEqual(shared.map((result) => result.payload.cache).sort(), ["miss", "shared"]);
  assert.equal(singleRequests.length, 8);
});

test("market-context route requires one date parameter and permits only GET", async () => {
  const wrongMethod = await route.GET(new Request(`http://next.local/api/toss-market-context?date=${businessDate}`, { method: "POST" }));
  assert.equal(wrongMethod.status, 405);
  for (const query of ["", "date=2026-02-30", `date=${businessDate}&symbols=999999`, `date=${businessDate}&date=${businessDate}`]) {
    const invalid = await route.GET(new Request(`http://next.local/api/toss-market-context${query ? `?${query}` : ""}`));
    assert.equal(invalid.status, 400);
  }
  assert.equal(route.HEAD().status, 405);
  assert.equal(route.OPTIONS().status, 405);
});
