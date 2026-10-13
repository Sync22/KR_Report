import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, TOSS_OPENAPI_MAX_RESPONSE_BYTES, readTossOpenApiConfig } from "../src/server/toss-openapi.ts";
import { TossPriorityQuotesService } from "../src/server/toss-priority-quotes.ts";
import * as route from "../src/app/api/toss-priority-quotes/route.ts";

const businessDate = "2026-10-08";
const clientId = "private-client-id-sentinel";
const clientSecret = "private-client-secret-sentinel";

function configured() {
  return readTossOpenApiConfig({
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID: clientId,
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET: clientSecret,
    STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED: "true",
    STOCK_MONITOR_TOSS_OPENAPI_BASE_URL: TOSS_OPENAPI_BASE_URL,
    STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS: "5",
  });
}

function token(accessToken) {
  return new Response(JSON.stringify({ access_token: accessToken, token_type: "Bearer", expires_in: 3600 }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function storedContext(overrides = {}) {
  return {
    latestBusinessDate: businessDate,
    symbols: ["005930", "000660", "999999", "bad"],
    ...overrides,
  };
}

test("Toss priority quote reads use only the fixed server-derived Top2 endpoints and keep credentials private", async () => {
  const requests = [];
  const fetchImpl = async (input, init) => {
    const url = new URL(String(input));
    requests.push({ url, init });
    if (url.pathname === "/oauth2/token") {
      assert.equal(init.method, "POST");
      const body = new URLSearchParams(init.body);
      assert.equal(body.get("client_id"), clientId);
      assert.equal(body.get("client_secret"), clientSecret);
      return token("private-access-token-sentinel");
    }
    assert.equal(url.origin, TOSS_OPENAPI_BASE_URL);
    assert.equal(init.method, "GET");
    assert.equal(init.redirect, "error");
    assert.ok(init.signal instanceof AbortSignal);
    if (url.pathname === "/api/v1/prices") {
      assert.equal(url.searchParams.get("symbols"), "005930,000660");
      return new Response(JSON.stringify({ result: [
        { symbol: "005930", lastPrice: "70000", currency: "KRW" },
        { symbol: "000660", lastPrice: "200000", currency: "KRW" },
      ] }), { status: 200, headers: { "x-ratelimit-limit": "20", "x-ratelimit-remaining": "19" } });
    }
    assert.match(url.pathname, /^\/api\/v1\/stocks\/(005930|000660)\/investor-trading$/);
    assert.equal(url.searchParams.get("count"), "1");
    assert.equal(url.searchParams.get("until"), businessDate);
    return new Response(JSON.stringify({ result: { records: [{
      date: businessDate,
      updatedAt: "2026-10-08T10:00:00+09:00",
      individual: { netBuyVolume: "100" },
      foreigner: { netBuyVolume: "200" },
      institution: { netBuyVolume: "-50" },
    }] } }));
  };
  const service = new TossPriorityQuotesService({ config: configured(), fetchImpl, loadContext: () => storedContext() });

  const response = await service.getQuotes(businessDate);

  assert.equal(response.status, 200);
  assert.deepEqual(response.payload.symbols, ["005930", "000660"]);
  assert.deepEqual(response.payload.quotes.map((item) => item.symbol), ["005930", "000660"]);
  assert.deepEqual(response.payload.investor_trading.items.map((item) => item.symbol), ["005930", "000660"]);
  assert.deepEqual(response.payload.rate_limit, { limit: "20", remaining: "19" });
  assert.equal(response.payload.latest_business_date, businessDate);
  assert.equal(response.payload.derived_from, "web_view_candidate_evidence_top_2");
  assert.equal(requests.length, 4);
  assert.doesNotMatch(JSON.stringify(response.payload), /private-(?:client-id|client-secret|access-token)-sentinel/);
});

test("latest-date rejection and disabled configuration never call Toss", async () => {
  let calls = 0;
  const fetchImpl = async () => { calls += 1; throw new Error("unexpected upstream call"); };
  const service = new TossPriorityQuotesService({
    config: configured(), fetchImpl,
    loadContext: () => storedContext({ latestBusinessDate: "2026-10-09" }),
  });
  const conflict = await service.getQuotes(businessDate);
  assert.equal(conflict.status, 409);
  assert.equal(conflict.payload.reason, "latest_business_date_only");
  assert.equal(conflict.payload.latest_business_date, "2026-10-09");
  assert.equal(calls, 0);

  const disabled = new TossPriorityQuotesService({
    config: readTossOpenApiConfig({}), fetchImpl,
    loadContext: () => storedContext(),
  });
  const noCredentials = await disabled.getQuotes(businessDate);
  assert.equal(noCredentials.status, 200);
  assert.equal(noCredentials.payload.configured, false);
  assert.equal(noCredentials.payload.live_fetch, false);
  assert.equal(noCredentials.payload.cache, "disabled");
  assert.equal(calls, 0);
});

test("default service derives the selected Top2 from a read-only SQLite snapshot", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const tempRoot = mkdtempSync(join(tmpdir(), "stock-monitor-toss-quotes-"));
  const databasePath = join(tempRoot, "fixture.db");
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousTimezone = process.env.STOCK_MONITOR_TIMEZONE;
  const previousHolidays = process.env.STOCK_MONITOR_HOLIDAYS;
  try {
    const initialized = spawnSync("python", ["-c", [
      "import sqlite3, sys",
      "from stock_monitor.db.schema import initialize_schema",
      "connection = sqlite3.connect(sys.argv[1])",
      "initialize_schema(connection)",
      "connection.commit()",
      "connection.close()",
    ].join("\n"), databasePath], {
      cwd: projectRoot,
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: [join(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter) },
    });
    assert.equal(initialized.status, 0, initialized.stderr);
    const database = new DatabaseSync(databasePath);
    const addSummary = database.prepare(`
      INSERT INTO daily_stock_summaries
        (business_date, stock_name, stock_code, mention_count, broker_display, dominant_opinion, generated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);
    const addReport = database.prepare(`
      INSERT INTO reports
        (identity_key, stock_name, stock_code, title, broker_name, published_at, business_date,
         opinion_normalized, collected_at, source_url, source_id)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    for (const [code, name, mentions] of [["005930", "삼성전자", 3], ["000660", "SK하이닉스", 2], ["035420", "NAVER", 1]]) {
      addSummary.run(businessDate, name, code, mentions, "증권사 A (1), 증권사 B (1)", "매수", businessDate + "T20:00:00+09:00");
      for (const [index, broker] of ["증권사 A", "증권사 B"].entries()) {
        const sourceId = code + "-" + index;
        addReport.run(sourceId, name, code, name + " 분석", broker,
          businessDate + "T09:00:00+09:00", businessDate, "매수", businessDate + "T09:05:00+09:00",
          "https://finance.naver.com/item/main.naver?code=" + code, sourceId);
      }
    }
    database.close();
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    process.env.STOCK_MONITOR_HOLIDAYS = "";
    const { getCandidateEvidenceSnapshot } = await import("../src/server/candidate-evidence.ts");
    const expected = getCandidateEvidenceSnapshot(businessDate, 2).rows
      .filter((candidate) => candidate.selected && /^\d{6}$/.test(candidate.stock_code))
      .map((candidate) => candidate.stock_code);
    const before = statSync(databasePath);
    const service = new TossPriorityQuotesService({ config: readTossOpenApiConfig({}) });
    const latest = await service.getQuotes(businessDate);
    assert.deepEqual(latest.payload.symbols, expected.slice(0, 2));
    assert.ok(latest.payload.symbols.length <= 2);
    const oldDate = await service.getQuotes("2026-10-07");
    assert.equal(oldDate.status, 409);
    assert.equal(oldDate.payload.reason, "latest_business_date_only");
    assert.equal(oldDate.payload.symbols.length, 0);
    const after = statSync(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = previousTimezone;
    if (previousHolidays === undefined) delete process.env.STOCK_MONITOR_HOLIDAYS;
    else process.env.STOCK_MONITOR_HOLIDAYS = previousHolidays;
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("quote cache uses 30-second hits and serves stale success for at most 300 seconds", async () => {
  let now = 0;
  let failQuotes = false;
  let requests = 0;
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    requests += 1;
    if (url.pathname === "/oauth2/token") return token("access");
    if (url.pathname === "/api/v1/prices" && failQuotes) return new Response("provider-private-error", { status: 503 });
    if (url.pathname === "/api/v1/prices") return new Response(JSON.stringify({ result: [{ symbol: "005930", lastPrice: "70000" }] }));
    return new Response(JSON.stringify({ result: { records: [] } }));
  };
  const service = new TossPriorityQuotesService({
    config: configured(), fetchImpl, clock: () => now,
    loadContext: () => storedContext({ symbols: ["005930"] }),
  });

  assert.equal((await service.getQuotes(businessDate)).payload.cache, "miss");
  assert.equal((await service.getQuotes(businessDate)).payload.cache, "hit");
  assert.equal(requests, 3);
  now = 31;
  failQuotes = true;
  const stale = await service.getQuotes(businessDate);
  assert.equal(stale.status, 200);
  assert.equal(stale.payload.cache, "stale");
  assert.equal(stale.payload.stale_reason, "upstream_unavailable");
  assert.equal(stale.payload.quotes[0].symbol, "005930");
  assert.doesNotMatch(JSON.stringify(stale.payload), /provider-private-error/);
  now = 301;
  const expired = await service.getQuotes(businessDate);
  assert.equal(expired.status, 502);
  assert.equal(expired.payload.reason, "upstream_unavailable");
});

test("investor-trading failure does not discard quotes and a 401 retries once", async () => {
  let tokenRequests = 0;
  let priceRequests = 0;
  const fetchImpl = async (input, init) => {
    const url = new URL(String(input));
    if (url.pathname === "/oauth2/token") return token("token-" + (++tokenRequests));
    if (url.pathname === "/api/v1/prices") {
      priceRequests += 1;
      if (priceRequests === 1) return new Response("private 401 detail", { status: 401 });
      return new Response(JSON.stringify({ result: [{ symbol: "005930", lastPrice: "70000" }] }));
    }
    return new Response("private investor error", { status: 503 });
  };
  const service = new TossPriorityQuotesService({
    config: configured(), fetchImpl,
    loadContext: () => storedContext({ symbols: ["005930"] }),
  });

  const response = await service.getQuotes(businessDate);

  assert.equal(response.status, 200);
  assert.equal(priceRequests, 2);
  assert.equal(tokenRequests, 2);
  assert.equal(response.payload.quotes[0].symbol, "005930");
  assert.deepEqual(response.payload.investor_trading, { reference_date: businessDate, available: false, items: [] });
  assert.doesNotMatch(JSON.stringify(response.payload), /token-[12]|private .*error|private 401 detail/);
});

test("untrusted Toss origins, redirects, and oversized responses fail closed", async () => {
  const untrusted = readTossOpenApiConfig({
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID: clientId,
    STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET: clientSecret,
    STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED: "true",
    STOCK_MONITOR_TOSS_OPENAPI_BASE_URL: "https://attacker.example",
  });
  assert.equal(untrusted.configured, false);

  for (const responseForPrices of [
    () => new Response("redirect body contains no public data", { status: 302, headers: { location: "https://attacker.example" } }),
    () => new Response(new Uint8Array(TOSS_OPENAPI_MAX_RESPONSE_BYTES + 1), { status: 200 }),
  ]) {
    const requests = [];
    const fetchImpl = async (input, init) => {
      const url = new URL(String(input));
      requests.push({ url, init });
      if (url.pathname === "/oauth2/token") return token("access");
      return responseForPrices();
    };
    const service = new TossPriorityQuotesService({
      config: configured(), fetchImpl, loadContext: () => storedContext({ symbols: ["005930"] }),
    });
    const result = await service.getQuotes(businessDate);
    assert.equal(result.status, 502);
    assert.equal(result.payload.reason, "upstream_unavailable");
    assert.equal(requests.length, 2);
    assert.ok(requests.every(({ url, init }) => url.origin === TOSS_OPENAPI_BASE_URL && init.redirect === "error"));
    assert.doesNotMatch(JSON.stringify(result.payload), /attacker\.example|redirect body|access/);
  }
});

test("Toss quote route is strict date-only GET", async () => {
  const invalid = await route.GET(new Request(`http://next.local/api/toss-priority-quotes?date=${businessDate}&symbols=005930`));
  assert.equal(invalid.status, 400);
  const malformed = await route.GET(new Request("http://next.local/api/toss-priority-quotes?date=2026-02-30"));
  assert.equal(malformed.status, 400);
  const options = route.OPTIONS(new Request(`http://next.local/api/toss-priority-quotes?date=${businessDate}`, { method: "OPTIONS" }));
  assert.equal(options.status, 405);
  assert.equal(options.headers.get("allow"), "GET");
});

test("Next Toss quote DTO matches the Python provider for success, disabled, and investor failure", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const pythonProviderScript = [
    "import json, sys",
    "from datetime import date",
    "from stock_monitor.fetch.toss_openapi import TossAccessToken, TossOpenApiLabConfig, TossReadonlyResponse, TOSS_OPENAPI_BASE_URL",
    "from stock_monitor.toss_openapi_web_view import TossPriorityQuoteProvider",
    "scenario = sys.argv[1]",
    "investor_calls = []",
    "config = TossOpenApiLabConfig(client_id='test-client-id', client_secret='test-client-secret', live_enabled=scenario != 'disabled', base_url=TOSS_OPENAPI_BASE_URL, timeout_seconds=5)",
    "def issue_token(**_kwargs):",
    "    return TossAccessToken(access_token='test-access-token', expires_in=3600)",
    "def fetch_quotes(*, endpoint, params, **_kwargs):",
    "    if endpoint.key == 'prices':",
    "        result = [{'symbol': '005930', 'lastPrice': '70000', 'currency': 'KRW'}, {'symbol': '000660', 'lastPrice': '200000', 'currency': 'KRW'}]",
    "        return TossReadonlyResponse(endpoint=endpoint, result=result, row_count=len(result), rate_limit={'limit': '20', 'remaining': '19'})",
    "    investor_calls.append(params['symbol'])",
    "    if scenario == 'partial' and params['symbol'] == '000660':",
    "        raise RuntimeError('private mock provider error')",
    "    symbol = params['symbol']",
    "    values = {'005930': ('100', '200', '-50'), '000660': ('11', '-12', '13')}[symbol]",
    "    record = {'date': params['until'], 'updatedAt': '2026-10-08T10:00:00+09:00', 'individual': {'netBuyVolume': values[0]}, 'foreigner': {'netBuyVolume': values[1]}, 'institution': {'netBuyVolume': values[2]}}",
    "    result = {'records': [record]}",
    "    return TossReadonlyResponse(endpoint=endpoint, result=result, row_count=1, rate_limit={})",
    "provider = TossPriorityQuoteProvider(config=config, issue_token=issue_token, fetch_quotes=fetch_quotes)",
    "payload = provider.get_quotes(priority_date=date.fromisoformat('2026-10-08'), symbols=('005930', '000660'), include_investor_trading=True)",
    "print(json.dumps({'payload': payload, 'investor_calls': investor_calls}))",
  ].join("\n");
  const pythonPayload = (scenario) => {
    const result = spawnSync("python", ["-c", pythonProviderScript, scenario], {
      cwd: projectRoot,
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: [join(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter) },
    });
    assert.equal(result.status, 0, result.stderr);
    return JSON.parse(result.stdout);
  };
  const quotes = [
    { symbol: "005930", lastPrice: "70000", currency: "KRW" },
    { symbol: "000660", lastPrice: "200000", currency: "KRW" },
  ];
  const investorItems = [
    { symbol: "005930", business_date: businessDate, updated_at: "2026-10-08T10:00:00+09:00", individual_net_buy_volume: 100, foreigner_net_buy_volume: 200, institution_net_buy_volume: -50 },
    { symbol: "000660", business_date: businessDate, updated_at: "2026-10-08T10:00:00+09:00", individual_net_buy_volume: 11, foreigner_net_buy_volume: -12, institution_net_buy_volume: 13 },
  ];

  for (const scenario of ["success", "disabled", "partial"]) {
    const isDisabled = scenario === "disabled";
    const nextInvestorCalls = [];
    const fetchImpl = async (input) => {
      const url = new URL(String(input));
      if (isDisabled) throw new Error("disabled service attempted a request");
      if (url.pathname === "/oauth2/token") return token("test-access-token");
      if (url.pathname === "/api/v1/prices") {
        return new Response(JSON.stringify({ result: quotes }), {
          headers: { "x-ratelimit-limit": "20", "x-ratelimit-remaining": "19" },
        });
      }
      const symbol = url.pathname.split("/")[4];
      nextInvestorCalls.push(symbol);
      if (scenario === "partial" && symbol === "000660") return new Response("private mock provider error", { status: 503 });
      const item = investorItems.find((candidate) => candidate.symbol === symbol);
      const [individual, foreigner, institution] = item
        ? [item.individual_net_buy_volume, item.foreigner_net_buy_volume, item.institution_net_buy_volume]
        : [null, null, null];
      return new Response(JSON.stringify({ result: { records: [{
        date: businessDate,
        updatedAt: "2026-10-08T10:00:00+09:00",
        individual: { netBuyVolume: String(individual) },
        foreigner: { netBuyVolume: String(foreigner) },
        institution: { netBuyVolume: String(institution) },
      }] } }));
    };
    const service = new TossPriorityQuotesService({
      config: isDisabled ? readTossOpenApiConfig({}) : configured(),
      fetchImpl,
      loadContext: () => storedContext({ latestBusinessDate: businessDate, symbols: ["005930", "000660"] }),
    });
    const next = await service.getQuotes(businessDate);
    const pythonOutput = pythonPayload(scenario);
    const python = pythonOutput.payload;

    assert.equal(next.status, 200);
    assert.equal(next.payload.latest_business_date, businessDate);
    assert.equal(next.payload.derived_from, "web_view_candidate_evidence_top_2");
    assert.doesNotMatch(JSON.stringify(next.payload), /test-client-id|test-client-secret|test-access-token|private mock provider error/);
    assert.deepEqual(nextInvestorCalls, pythonOutput.investor_calls, scenario + " investor endpoint calls");

    const normalizedPython = { ...python };
    const normalizedNext = { ...next.payload };
    delete normalizedNext.latest_business_date;
    delete normalizedNext.derived_from;
    for (const payload of [normalizedPython, normalizedNext]) {
      delete payload.latency_ms;
      delete payload.cache;
      if (payload.fetched_at !== undefined) {
        const instant = Date.parse(payload.fetched_at);
        assert.ok(Number.isFinite(instant), `${scenario} fetched_at must identify an instant`);
        payload.fetched_at = instant;
      }
    }
    if (normalizedPython.fetched_at !== undefined) {
      assert.ok(Math.abs(normalizedPython.fetched_at - normalizedNext.fetched_at) <= 5000, `${scenario} fetched_at instants should be close`);
    }
    delete normalizedPython.fetched_at;
    delete normalizedNext.fetched_at;
    assert.deepEqual(normalizedNext, normalizedPython, scenario + " DTO parity");
    if (scenario === "success") assert.deepEqual(next.payload.investor_trading.items, investorItems);
    if (scenario === "partial") assert.deepEqual(next.payload.investor_trading, { reference_date: businessDate, available: false, items: [] });
  }
});

test("Python and Next enforce one automatic 401 token reissue per provider lifetime", async () => {
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const script = [
    "import json",
    "from datetime import date",
    "from stock_monitor.fetch.toss_openapi import TossAccessToken, TossOpenApiHttpError, TossOpenApiLabConfig, TossReadonlyResponse, TOSS_OPENAPI_BASE_URL",
    "from stock_monitor.toss_openapi_web_view import TossPriorityQuoteProvider",
    "counts = {'tokens': 0, 'prices': 0, 'investors': 0}",
    "def issue_token(**_kwargs):",
    "    counts['tokens'] += 1",
    "    return TossAccessToken(access_token='test-token-' + str(counts['tokens']), expires_in=3600)",
    "def fetch_quotes(*, endpoint, params, **_kwargs):",
    "    if endpoint.key == 'prices':",
    "        counts['prices'] += 1",
    "        if counts['prices'] in (1, 3):",
    "            raise TossOpenApiHttpError('mock unauthorized', status_code=401)",
    "        result = [{'symbol': '005930', 'lastPrice': '70000'}]",
    "        return TossReadonlyResponse(endpoint=endpoint, result=result, row_count=1, rate_limit={})",
    "    counts['investors'] += 1",
    "    result = {'records': [{'date': params['until'], 'updatedAt': '2026-10-08T10:00:00+09:00', 'individual': {'netBuyVolume': '1'}}]} ",
    "    return TossReadonlyResponse(endpoint=endpoint, result=result, row_count=1, rate_limit={})",
    "config = TossOpenApiLabConfig(client_id='test-id', client_secret='test-secret', live_enabled=True, base_url=TOSS_OPENAPI_BASE_URL, timeout_seconds=5)",
    "provider = TossPriorityQuoteProvider(config=config, issue_token=issue_token, fetch_quotes=fetch_quotes)",
    "first = provider.get_quotes(priority_date=date.fromisoformat('2026-10-08'), symbols=('005930',), include_investor_trading=True)",
    "second_failed = False",
    "try:",
    "    provider.get_quotes(priority_date=date.fromisoformat('2026-10-09'), symbols=('005930',), include_investor_trading=True)",
    "except RuntimeError:",
    "    second_failed = True",
    "print(json.dumps({'first': first, 'second_failed': second_failed, 'counts': counts}))",
  ].join("\n");
  const pythonResult = spawnSync("python", ["-c", script], {
    cwd: projectRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: [join(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter) },
  });
  assert.equal(pythonResult.status, 0, pythonResult.stderr);
  const python = JSON.parse(pythonResult.stdout);

  const counts = { tokens: 0, prices: 0, investors: 0 };
  const fetchImpl = async (input) => {
    const url = new URL(String(input));
    if (url.pathname === "/oauth2/token") return token("test-token-" + (++counts.tokens));
    if (url.pathname === "/api/v1/prices") {
      counts.prices += 1;
      if (counts.prices === 1 || counts.prices === 3) return new Response("private 401 detail", { status: 401 });
      return new Response(JSON.stringify({ result: [{ symbol: "005930", lastPrice: "70000" }] }));
    }
    counts.investors += 1;
    return new Response(JSON.stringify({ result: { records: [{
      date: url.searchParams.get("until"),
      updatedAt: "2026-10-08T10:00:00+09:00",
      individual: { netBuyVolume: "1" },
    }] } }));
  };
  const service = new TossPriorityQuotesService({
    config: configured(), fetchImpl,
    loadContext: (date) => ({ latestBusinessDate: date, symbols: ["005930"] }),
  });
  const first = await service.getQuotes("2026-10-08");
  const second = await service.getQuotes("2026-10-09");

  assert.equal(first.status, 200);
  assert.equal(second.status, 502);
  assert.equal(second.payload.reason, "upstream_unavailable");
  assert.equal(python.second_failed, true);
  assert.deepEqual(counts, python.counts);
  assert.equal(counts.tokens, 2);
  assert.equal(counts.prices, 3);
  assert.equal(counts.investors, 1);
  assert.doesNotMatch(JSON.stringify(second.payload), /private 401 detail|test-token|test-secret/);
});
