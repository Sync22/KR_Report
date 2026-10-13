import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, readTossOpenApiConfig } from "../src/server/toss-openapi.ts";
import { TossPriorityDailyCandlesService } from "../src/server/toss-priority-daily-candles.ts";
import * as route from "../src/app/api/toss-priority-daily-candles/route.ts";

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

const candleRows = {
  "005930": [
    { timestamp: "2026-07-10T00:00:00+09:00", openPrice: "70000", highPrice: "70100", lowPrice: "69900", closePrice: "70050", volume: "100", currency: "KRW" },
    { timestamp: "2026-07-13T00:00:00+09:00", openPrice: "70100", highPrice: "70200", lowPrice: "70050", closePrice: "70150", volume: "120", currency: "KRW" },
    { timestamp: "not-a-date", openPrice: "70200", highPrice: "70300", lowPrice: "70100", closePrice: "70250", volume: "130", currency: "KRW" },
  ],
  "000660": [
    { timestamp: "2026-07-09T15:00:00Z", openPrice: "200000", highPrice: "200100", lowPrice: "199900", closePrice: "200050", volume: "100", currency: "KRW" },
  ],
};

function pythonRouteFixture(projectRoot, tempRoot, databasePath) {
  const script = [
    "import json, sys, threading, urllib.request",
    "from datetime import date, datetime",
    "from pathlib import Path",
    "from stock_monitor.cli import RuntimeConfig, create_web_view_server",
    "from stock_monitor.db.repository import StockMonitorRepository",
    "from stock_monitor.models import Report",
    "root, database_path = Path(sys.argv[1]), Path(sys.argv[2])",
    "config = RuntimeConfig.from_env(root_dir=root)",
    "repository = StockMonitorRepository(database_path, timezone=config.timezone)",
    "repository.initialize()",
    "selected = date.fromisoformat('2026-07-10')",
    "later = date.fromisoformat('2026-07-13')",
    "reports = []",
    "for name, code, broker, minute, suffix in [('삼성전자','005930','NH투자증권',0,1),('SK하이닉스','000660','KB증권',2,1),('삼성전자','005930','KB증권',4,2),('SK하이닉스','000660','NH투자증권',6,2)]:",
    "    reports.append(Report(stock_name=name, stock_code=code, title=f'{name} report {suffix}', broker_name=broker, published_at=datetime(2026,7,10,9,minute), business_date=selected, collected_at=datetime(2026,7,10,9,minute+1), source_id=f'candles-{code}-{suffix}', identity_key=f'candles-{code}-{suffix}'))",
    "reports.append(Report(stock_name='NAVER', stock_code='035420', title='Later report', broker_name='신한투자증권', published_at=datetime(2026,7,13,9,0), business_date=later, collected_at=datetime(2026,7,13,9,1), source_id='candles-later', identity_key='candles-later'))",
    "repository.insert_reports(reports)",
    "repository.rebuild_daily_summaries(selected)",
    "repository.rebuild_daily_summaries(later)",
    "class Provider:",
    "    configured = True",
    "    def get_priority_stock_daily_candles(self, *, priority_symbols, before, count):",
    "        values = {'005930': [('2026-07-10T00:00:00+09:00','70000'), ('2026-07-13T00:00:00+09:00','70100'), ('not-a-date','70200')], '000660': [('2026-07-09T15:00:00Z','200000')]} ",
    "        items = []",
    "        for symbol in priority_symbols:",
    "            candles = [{'timestamp': stamp, 'openPrice': price, 'highPrice': str(int(price)+100), 'lowPrice': str(int(price)-100), 'closePrice': str(int(price)+50), 'volume': '100', 'currency': 'KRW'} for stamp, price in values[symbol]]",
    "            items.append({'symbol': symbol, 'candles': candles})",
    "        return {'surface':'web-view-toss-priority-daily-candles','read_only':True,'configured':True,'live_fetch':True,'writes_db':False,'sends_telegram':False,'registers_scheduler':False,'affects_ordering':False,'priority_date':before.date().isoformat(),'before':before.isoformat(timespec='seconds'),'interval':'1d','count':count,'adjusted':True,'symbols':list(priority_symbols),'items':items,'rate_limit':{symbol:{'limit':'10','remaining':'9'} for symbol in priority_symbols},'cache':'miss','available':True,'fetched_at':'2026-07-13T10:00:00+09:00'}",
    "server = create_web_view_server(config, repository, host='127.0.0.1', port=0, limit=5, toss_quote_provider=Provider())",
    "thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()",
    "try:",
    "    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/toss-priority-daily-candles?date=2026-07-10&days=90&symbols=999999', timeout=5) as response:",
    "        print(response.read().decode('utf-8'))",
    "finally:",
    "    server.shutdown(); server.server_close(); thread.join(timeout=5)",
  ].join("\n");
  const result = spawnSync("python", ["-c", script, tempRoot, databasePath], {
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
  return { status: 200, payload: JSON.parse(result.stdout) };
}

test("Next daily candles DTO matches the Python route and uses only stored Top2 symbols", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-toss-candles-"));
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
    const fetchImpl = async (input, init) => {
      const url = new URL(String(input));
      requests.push({ url, init });
      if (url.pathname === "/oauth2/token") {
        assert.equal(init.method, "POST");
        return token();
      }
      assert.equal(url.origin, TOSS_OPENAPI_BASE_URL);
      assert.equal(url.pathname, "/api/v1/candles");
      assert.equal(init.method, "GET");
      assert.equal(init.redirect, "error");
      assert.ok(init.signal instanceof AbortSignal);
      assert.equal(url.searchParams.get("interval"), "1d");
      assert.equal(url.searchParams.get("count"), "90");
      assert.equal(url.searchParams.get("before"), "2026-07-10T23:59:59+09:00");
      assert.equal(url.searchParams.get("adjusted"), "true");
      const symbol = url.searchParams.get("symbol");
      return new Response(JSON.stringify({ result: { candles: candleRows[symbol], nextBefore: null } }), {
        headers: { "x-ratelimit-limit": "10", "x-ratelimit-remaining": "9" },
      });
    };
    const service = new TossPriorityDailyCandlesService({
      config: configured(),
      fetchImpl,
      now: () => new Date("2026-07-13T01:00:00.000Z"),
    });
    const next = await service.getCandles(businessDate, 90);
    const afterRead = statSync(databasePath);

    assert.equal(next.status, python.status);
    assert.deepEqual(next.payload, python.payload);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.deepEqual(next.payload.symbols, ["005930", "000660"]);
    assert.deepEqual(next.payload.items.map((item) => item.symbol), ["005930", "000660"]);
    assert.deepEqual(next.payload.items.map((item) => item.excluded_candle_count), [2, 0]);
    assert.equal(next.payload.excluded_candle_count, 2);
    assert.deepEqual(next.payload.items[0].candles, [candleRows["005930"][0]]);
    assert.equal(next.payload.business_date, businessDate);
    assert.equal(next.payload.before, "2026-07-10T23:59:59+09:00");
    assert.equal(requests.length, 3);
    assert.deepEqual(requests.slice(1).map(({ url }) => url.searchParams.get("symbol")), ["005930", "000660"]);
    assert.doesNotMatch(JSON.stringify(next.payload), /private-(?:client-id|client-secret|access-token)-sentinel/);
  } finally {
    for (const name of envNames) {
      if (previousEnv[name] === undefined) delete process.env[name];
      else process.env[name] = previousEnv[name];
    }
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("disabled and empty Top2 candle requests do not call Toss", async () => {
  let calls = 0;
  const fetchImpl = async () => { calls += 1; throw new Error("unexpected upstream call"); };
  const disabled = new TossPriorityDailyCandlesService({
    config: readTossOpenApiConfig({}), fetchImpl,
    loadSymbols: () => ["005930"],
  });
  const disabledResult = await disabled.getCandles(businessDate, 90);
  assert.equal(disabledResult.status, 200);
  assert.equal(disabledResult.payload.configured, false);
  assert.equal(disabledResult.payload.live_fetch, false);
  assert.equal(disabledResult.payload.cache, "disabled");
  assert.equal(disabledResult.payload.reason, "not_configured");

  const empty = new TossPriorityDailyCandlesService({
    config: configured(), fetchImpl,
    loadSymbols: () => [],
  });
  const emptyResult = await empty.getCandles(businessDate, 90);
  assert.equal(emptyResult.status, 200);
  assert.equal(emptyResult.payload.reason, "no_priority_symbols");
  assert.deepEqual(emptyResult.payload.items, []);
  assert.equal(calls, 0);
});

test("future-only candle responses return the Python 409 DTO", async () => {
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.pathname === "/oauth2/token") return token();
    return new Response(JSON.stringify({ result: { candles: [
      { timestamp: "2026-07-13T00:00:00+09:00", openPrice: "1", highPrice: "2", lowPrice: "1", closePrice: "2", volume: "1", currency: "KRW" },
    ] } }));
  };
  const service = new TossPriorityDailyCandlesService({ config: configured(), fetchImpl, loadSymbols: () => ["005930"] });
  const result = await service.getCandles(businessDate, 30);
  assert.equal(result.status, 409);
  assert.equal(result.payload.reason, "no_candles_before_top2_business_date");
  assert.deepEqual(result.payload.items, []);
  assert.equal(result.payload.before, "2026-07-10T23:59:59+09:00");
});

test("upstream errors keep only safe metadata and abort the whole Top2 response", async () => {
  let candleCalls = 0;
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.pathname === "/oauth2/token") return token();
    candleCalls += 1;
    if (candleCalls === 1) return new Response(JSON.stringify({ result: { candles: [candleRows["005930"][0]] } }));
    return new Response(JSON.stringify({ code: "safe-provider_code-1", message: "private client-secret leaked here" }), { status: 503 });
  };
  const service = new TossPriorityDailyCandlesService({ config: configured(), fetchImpl, loadSymbols: () => ["005930", "000660"] });
  const result = await service.getCandles(businessDate, 90);
  assert.equal(result.status, 502);
  assert.equal(result.payload.reason, "upstream_unavailable");
  assert.equal(result.payload.error_type, "TossOpenApiHttpError");
  assert.equal(result.payload.upstream_status, 503);
  assert.equal(result.payload.provider_code, "safe-provider_code-1");
  assert.deepEqual(result.payload.items, []);
  assert.doesNotMatch(JSON.stringify(result.payload), /private client-secret leaked here|private-access-token-sentinel/);
  assert.equal(candleCalls, 2);
});

test("candles allow one automatic 401 token reissue and reject redirects and oversized data", async () => {
  let tokenCalls = 0;
  let candleCalls = 0;
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.pathname === "/oauth2/token") return token(`token-${++tokenCalls}`);
    candleCalls += 1;
    if (candleCalls === 1) return new Response("private 401 body", { status: 401 });
    return new Response(JSON.stringify({ result: { candles: [candleRows["005930"][0]] } }));
  };
  const service = new TossPriorityDailyCandlesService({ config: configured(), fetchImpl, loadSymbols: () => ["005930"] });
  assert.equal((await service.getCandles(businessDate, 90)).status, 200);
  assert.equal(tokenCalls, 2);
  assert.equal(candleCalls, 2);

  for (const response of [
    () => new Response("private redirect body", { status: 302, headers: { location: "https://attacker.example" } }),
    () => new Response(new Uint8Array(1_048_577), { status: 200 }),
  ]) {
    const invalidService = new TossPriorityDailyCandlesService({
      config: configured(),
      loadSymbols: () => ["005930"],
      fetchImpl: async (input) => new URL(String(input)).pathname === "/oauth2/token" ? token() : response(),
    });
    const failed = await invalidService.getCandles(businessDate, 90);
    assert.equal(failed.status, 502);
    assert.equal(failed.payload.reason, "upstream_unavailable");
    assert.doesNotMatch(JSON.stringify(failed.payload), /private redirect body|attacker\.example|private 401 body/);
  }
});

test("daily candles route is GET-only and rejects invalid dates, integers, and counts", async () => {
  const post = route.GET(new Request(`http://next.local/api/toss-priority-daily-candles?date=${businessDate}`, { method: "POST" }));
  assert.equal((await post).status, 405);
  const invalidDate = await route.GET(new Request("http://next.local/api/toss-priority-daily-candles?date=2026-02-30"));
  assert.equal(invalidDate.status, 400);
  const invalidInteger = await route.GET(new Request(`http://next.local/api/toss-priority-daily-candles?date=${businessDate}&days=90.5`));
  assert.equal(invalidInteger.status, 400);
  const unsupported = await route.GET(new Request(`http://next.local/api/toss-priority-daily-candles?date=${businessDate}&days=60`));
  assert.equal(unsupported.status, 400);
  assert.equal((await unsupported.json()).reason, "unsupported_candle_count");
  const options = route.OPTIONS(new Request(`http://next.local/api/toss-priority-daily-candles?date=${businessDate}`, { method: "OPTIONS" }));
  assert.equal((await options).status, 405);
});
