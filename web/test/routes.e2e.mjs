import assert from "node:assert/strict";
import test from "node:test";

const origin = process.env.STOCK_MONITOR_NEXT_ORIGIN ?? "http://127.0.0.1:3000";
const pythonOrigin = process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL ?? "http://127.0.0.1:8781";

function dailyStockSelectionCodes(html) {
  return [...html.matchAll(/<a class="stock-selection-link"[^>]*href="\/daily\/2026-10-08\/stocks\?stock=(\d{6})(?:&amp;(?:include_single=1|limit=\d+))*#selected-stock"/g)].map((match) => match[1]);
}

test("archive API accepts GET and rejects other methods", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/archive", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") {
      assert.equal(response.headers.get("allow"), "GET");
    }
  }
});

test("root opens the latest Main view without an access-code", async () => {
  const archiveResponse = await fetch(new URL("/api/archive?limit=20", origin));
  assert.equal(archiveResponse.status, 200);
  const archive = await archiveResponse.json();
  const response = await fetch(new URL("/", origin), { redirect: "manual" });
  assert.equal(response.status, 200);
  assert.equal(response.url, new URL("/", origin).href);
  assert.equal(response.headers.get("location"), null);
  const html = await response.text();
  assert.match(html, /aria-label="일일 화면"/);
  assert.ok(html.includes('<div id="daily-main-panel" role="tabpanel" aria-labelledby="daily-main-tab">'));
  assert.match(html, new RegExp(archive.latest_business_date));
  assert.match(html, /aria-label="Main Top2 저장 근거"/);
  assert.doesNotMatch(html, /입장코드|로그인/i);
});

test("V2 renders the independent date, candidate, evidence, and stock-detail screen", async () => {
  const response = await fetch(new URL("/v2?date=2026-10-08", origin), { redirect: "manual" });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("location"), null);
  const html = await response.text();
  assert.match(html, /KR-Stock V2 Preview/);
  assert.match(html, /aria-label="날짜 선택"/);
  assert.match(html, /오늘의 흐름/);
  assert.match(html, /볼 종목/);
  assert.match(html, /근거 레이어/);
  assert.match(html, /종목 상세/);
  assert.match(html, /2026-10-08/);
  assert.match(html, /\/v2\?date=2026-10-08&amp;stock=\d{6}"/);
  assert.doesNotMatch(html, /\/v2\?date=2026-10-08[^" ]*#stock-detail/);
  assert.doesNotMatch(html, /입장코드|로그인|주문/i);

  const candidateResponse = await fetch(new URL("/api/candidate-evidence?date=2026-10-08&limit=8", origin));
  assert.equal(candidateResponse.status, 200);
  const candidate = (await candidateResponse.json()).rows[0];
  assert.ok(candidate);
  const selected = await fetch(new URL(`/v2?date=2026-10-08&stock=${candidate.stock_code}`, origin), { redirect: "manual" });
  assert.equal(selected.status, 200);
  const selectedHtml = await selected.text();
  assert.ok(selectedHtml.includes(candidate.stock_name));
  assert.ok(selectedHtml.includes(candidate.stock_code));
  assert.match(selectedHtml, /저장 뉴스 관찰|KRX|뉴스 근거/);
});

test("public header keeps the legacy Main, Watch, Stock, calendar, and stock suggestion controls", async () => {
  const response = await fetch(new URL("/daily/2026-10-08/main", origin));
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /aria-label="상단 탭"/);
  assert.match(html, />메인</);
  assert.match(html, />관찰</);
  assert.match(html, />종목</);
  assert.match(html, /aria-label="기준일 달력"/);
  assert.match(html, /aria-autocomplete="list"/);
});

test("daily legacy routes render all three tab panels with only the requested panel visible", async () => {
  for (const [route, active] of [["main", "main"], ["candidates", "watch"], ["stocks", "stock"]]) {
    const response = await fetch(new URL(`/daily/2026-10-08/${route}`, origin));
    assert.equal(response.status, 200);
    assert.equal(new URL(response.url).pathname, `/daily/2026-10-08/${route}`);
    const html = await response.text();
    for (const tab of ["main", "watch", "stock"]) {
      const panel = `<div id="daily-${tab}-panel" role="tabpanel" aria-labelledby="daily-${tab}-tab"`;
      assert.ok(html.includes(panel), `${route} should server-render the ${tab} panel`);
      const expectedHidden = tab === active ? "" : " hidden=\"\"";
      assert.ok(html.includes(`${panel}${expectedHidden}>`), `${route} should ${tab === active ? "show" : "hide"} the ${tab} panel`);
    }
  }

  const candidates = await (await fetch(new URL("/api/candidate-evidence?date=2026-10-08&limit=8", origin))).json();
  const stockCode = candidates.rows[0]?.stock_code;
  assert.match(stockCode ?? "", /^\d{6}$/);
  const selectedResponse = await fetch(new URL(`/daily/2026-10-08/stocks?stock=${stockCode}`, origin));
  assert.equal(selectedResponse.status, 200);
  const selectedHtml = await selectedResponse.text();
  assert.equal([...selectedHtml.matchAll(/id="selected-stock"/g)].length, 1);
  assert.equal([...selectedHtml.matchAll(/id="watch-selected-stock"/g)].length, 1);
  assert.equal([...selectedHtml.matchAll(/id="selected-stock-heading"/g)].length, 1);
  assert.equal([...selectedHtml.matchAll(/id="watch-selected-stock-heading"/g)].length, 1);
});

test("archive dates open the selected-date Main view", async () => {
  const [archiveResponse, pageResponse] = await Promise.all([
    fetch(new URL("/api/archive?limit=20", origin)),
    fetch(new URL("/archive", origin)),
  ]);
  assert.equal(archiveResponse.status, 200);
  assert.equal(pageResponse.status, 200);
  const archive = await archiveResponse.json();
  const html = await pageResponse.text();
  for (const item of archive.dates) {
    assert.ok(html.includes(`href="/daily/${item.business_date}/main"`), `${item.business_date} should open Main`);
  }
});

test("Next archive GET matches the Python DTO while reading SQLite directly", async () => {
  const [pythonResponse, nextResponse] = await Promise.all([
    fetch(`${pythonOrigin}/api/archive?limit=20`),
    fetch(new URL("/api/archive?limit=20", origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(nextResponse.status, 200);
  const [pythonPayload, nextPayload] = await Promise.all([pythonResponse.json(), nextResponse.json()]);
  const withoutNow = ({ now: _now, ...payload }) => payload;
  assert.deepEqual(withoutNow(nextPayload), withoutNow(pythonPayload));
});

test("Next daily default GET matches the Python stored DTO", async () => {
  const [pythonResponse, nextResponse] = await Promise.all([
    fetch(`${pythonOrigin}/api/daily/2026-10-08`),
    fetch(new URL("/api/daily/2026-10-08", origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(nextResponse.status, 200);
  const [pythonPayload, nextPayload] = await Promise.all([pythonResponse.json(), nextResponse.json()]);
  const withoutDynamicClockFields = (snapshot) => {
    const { now: _now, priority_candidate_evidence: candidate, ...payload } = snapshot;
    const { now: _candidateNow, ...priorityCandidate } = candidate;
    return { ...payload, priority_candidate_evidence: priorityCandidate };
  };
  assert.deepEqual(withoutDynamicClockFields(nextPayload), withoutDynamicClockFields(pythonPayload));
  assert.equal("observation_summary" in nextPayload, false);
  assert.equal(nextPayload.observation_summary_deferred, true);
});

test("daily API rejects invalid dates and methods without widening the public route", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/daily/2026-10-08", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") {
      assert.equal(response.headers.get("allow"), "GET");
    }
  }

  const invalidDate = await fetch(new URL("/api/daily/2026-02-30", origin));
  assert.equal(invalidDate.status, 400);
  assert.equal((await fetch(new URL("/api/daily/2026-10-08?symbols=005930", origin))).status, 400);
  assert.equal((await fetch(new URL("/api/daily/2026-10-08?intraday_market_top=1", origin))).status, 400);

  const historicalOverlap = await fetch(new URL("/api/daily/2026-10-08?intraday_market_top=1&market_top_limit=100&market_top_page_size=20", origin));
  assert.equal(historicalOverlap.status, 200);
  const storedDaily = await historicalOverlap.json();
  assert.equal(storedDaily.market_commentary.same_day_report_status.can_overlap_intraday_market_top, false);
  assert.equal(storedDaily.market_commentary.intraday_market_top_reference.live_fetch, false);
  assert.equal(storedDaily.market_commentary.intraday_quote_reference.live_fetch, false);
});

test("selected-date overview preserves stored market context and per-stock Toss references", async () => {
  const [pageResponse, apiResponse] = await Promise.all([
    fetch(new URL("/daily/2026-10-08", origin)),
    fetch(new URL("/api/daily/2026-10-08", origin)),
  ]);
  assert.equal(pageResponse.status, 200);
  assert.equal(apiResponse.status, 200);
  const [html, daily] = await Promise.all([pageResponse.text(), apiResponse.json()]);
  assert.match(html, /Toss 참고/);
  assert.match(html, /시장 문맥 · Toss 당일 · Toss 저장/);
  assert.match(html, /<details class="daily-briefing daily-market-context">/);
  assert.ok(html.includes(daily.toss_context.notice));
  if (daily.toss_context.missing_domains.length) assert.match(html, /저장 누락 항목/);
  for (const match of html.matchAll(/href="\/daily\/2026-10-08\/stocks\/([^"]+)"/g)) assert.match(match[1], /^\d{6}$/);
  const referencedStock = daily.stocks.find((stock) => typeof stock.market_reference?.close_price === "number");
  assert.ok(referencedStock);
  const storedPrice = `${new Intl.NumberFormat("ko-KR").format(referencedStock.market_reference.close_price)}원`;
  assert.ok(html.includes(storedPrice));
  assert.ok(html.includes(referencedStock.stock_code));
});

test("stock search API is GET-only and rejects invalid dates", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/stocks/search?date=2026-10-08&q=", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }

  const invalidDate = await fetch(new URL("/api/stocks/search?date=2026-02-30&q=test", origin));
  assert.equal(invalidDate.status, 400);
  const validGet = await fetch(new URL("/api/stocks/search?date=2026-10-08&q=", origin));
  assert.notEqual(validGet.status, 405);
  const emptySearch = await validGet.json();
  assert.equal(emptySearch.query, "");
  assert.equal(emptySearch.stock_universe_reference_date, null);

  const query = new URLSearchParams({ date: "2026-10-08", q: "삼성" });
  const [pythonResponse, nextResponse] = await Promise.all([
    fetch(`${pythonOrigin}/api/stocks/search?${query}`),
    fetch(new URL(`/api/stocks/search?${query}`, origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(nextResponse.status, 200);
  const [pythonPayload, nextPayload] = await Promise.all([pythonResponse.json(), nextResponse.json()]);
  const withoutNow = ({ now: _now, ...payload }) => payload;
  assert.deepEqual(withoutNow(nextPayload), withoutNow(pythonPayload));
  assert.equal(nextPayload.query, "삼성");

  const searchPage = await fetch(new URL(`/daily/2026-10-08/stocks?${query}`, origin));
  assert.equal(searchPage.status, 200);
  const searchHtml = await searchPage.text();
  assert.match(searchHtml, /저장 종목 검색/);
  assert.ok(searchHtml.includes('value="삼성"'));
});

test("stock detail API is GET-only and rejects invalid dates and stock codes", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/daily/2026-10-08/stocks/005930", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }

  const invalidDate = await fetch(new URL("/api/daily/2026-02-30/stocks/005930", origin));
  const invalidCode = await fetch(new URL("/api/daily/2026-10-08/stocks/not-a-code", origin));
  assert.equal(invalidDate.status, 400);
  assert.equal(invalidCode.status, 400);
  const validGet = await fetch(new URL("/api/daily/2026-10-08/stocks/005930", origin));
  assert.notEqual(validGet.status, 405);

  const detailPage = await fetch(new URL("/daily/2026-10-08/stocks/375500", origin));
  assert.equal(detailPage.status, 200);
  const detailHtml = await detailPage.text();
  assert.match(detailHtml, /당일 시장 · 수급 보기/);
  assert.match(detailHtml, /href="\/daily\/2026-10-08\/main#toss-market-refresh"/);
});

test("candidate evidence API is GET-only and exposes only stored public evidence", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/candidate-evidence?date=2026-10-08&limit=8", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }

  const invalidDate = await fetch(new URL("/api/candidate-evidence?date=2026-02-30", origin));
  assert.equal(invalidDate.status, 400);
  const [validGet, pythonGet] = await Promise.all([
    fetch(new URL("/api/candidate-evidence?date=2026-10-08&limit=8", origin)),
    fetch(`${pythonOrigin}/api/candidate-evidence?date=2026-10-08&limit=8`),
  ]);
  assert.equal(validGet.status, 200);
  assert.equal(pythonGet.status, 200);
  const payload = await validGet.json();
  const pythonPayload = await pythonGet.json();
  const withoutNow = ({ now: _now, ...value }) => value;
  assert.deepEqual(withoutNow(payload), withoutNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.business_date, "2026-10-08");
  assert.equal(payload.live_fetch, false);
  assert.equal(payload.scoring, false);
  assert.equal(payload.recommendation, false);
  assert.ok(Array.isArray(payload.rows));
  for (const row of payload.rows) {
    assert.equal("sort_tuple" in row, false);
    assert.equal("_sort_value_signal" in row, false);
    assert.equal("_sort_tuple" in row, false);
    assert.equal("internal_candidate_signals" in row, false);
    assert.equal("internal_missing_information" in row, false);
    assert.equal("quality_flags" in row, false);
    assert.equal("evidence_notes" in row, false);
    assert.equal("opinion_summary" in row, false);
  }

  const watchHtml = await (await fetch(new URL("/daily/2026-10-08/candidates", origin))).text();
  const watchPanelStart = watchHtml.indexOf('<div id="daily-watch-panel"');
  const stockPanelStart = watchHtml.indexOf('<div id="daily-stock-panel"');
  assert.ok(watchPanelStart >= 0 && stockPanelStart > watchPanelStart);
  const watchPanelHtml = watchHtml.slice(watchPanelStart, stockPanelStart);
  const watchCodes = [...watchPanelHtml.matchAll(/href="\/daily\/2026-10-08\/stocks\?stock=(\d{6})#selected-stock"/g)].map((match) => match[1]);
  assert.deepEqual(watchCodes, payload.rows.map((row) => row.stock_code));
  const selectedWatch = await fetch(new URL(`/daily/2026-10-08/stocks?stock=${watchCodes[0]}`, origin));
  assert.equal(selectedWatch.status, 200);
  const selectedWatchHtml = await selectedWatch.text();
  assert.match(selectedWatchHtml, /id="selected-stock"/);
  assert.match(selectedWatchHtml, /class="selected-stock-report-list"/);
  const selectedWatchCandidate = payload.rows.find((row) => row.stock_code === watchCodes[0]);
  assert.ok(selectedWatchCandidate);
  assert.ok(selectedWatchHtml.includes(selectedWatchCandidate.why_notable[0]));
  const dailyResponse = await fetch(new URL("/api/daily/2026-10-08", origin));
  const daily = await dailyResponse.json();
  const dailyCodes = daily.stocks.map((row) => row.stock_code).filter(Boolean);
  const invalidStockCode = ["000000", "999999"].find((code) => !dailyCodes.includes(code));
  assert.ok(invalidStockCode);
  const invalidSelectedWatch = await fetch(new URL(`/daily/2026-10-08/stocks?stock=${invalidStockCode}`, origin));
  assert.doesNotMatch(await invalidSelectedWatch.text(), /id="selected-stock"/);
  const mainHtml = await (await fetch(new URL("/daily/2026-10-08/main", origin))).text();
  const mainCodes = [...mainHtml.matchAll(/class="main-top2-candidate[^\"]*"[\s\S]*?href="\/daily\/2026-10-08\/stocks\?stock=(\d{6})#selected-stock"/g)].map((match) => match[1]);
  assert.deepEqual(mainCodes, payload.rows.filter((row) => row.selected).slice(0, 2).map((row) => row.stock_code));
  const selectedHtml = await (await fetch(new URL(`/daily/2026-10-08/stocks?stock=${mainCodes[0]}#selected-stock`, origin))).text();
  assert.match(selectedHtml, /id="selected-stock"/);
  assert.match(selectedHtml, /class="selected-stock-report-list"/);
  const selectedMainCandidate = payload.rows.find((row) => row.stock_code === mainCodes[0]);
  assert.ok(selectedMainCandidate);
  assert.ok(selectedHtml.includes(selectedMainCandidate.why_notable[0]));
  assert.ok(invalidStockCode);
  const ignoredSelection = await (await fetch(new URL(`/daily/2026-10-08/stocks?stock=${invalidStockCode}`, origin))).text();
  assert.doesNotMatch(ignoredSelection, /id="selected-stock"/);
});

test("market API is GET-only and exposes the stored Toss snapshot contract", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/market?symbols=005930", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }
  const [pythonResponse, response] = await Promise.all([
    fetch(`${pythonOrigin}/api/market`),
    fetch(new URL("/api/market?symbols=005930", origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(response.status, 200);
  const [pythonPayload, payload] = await Promise.all([pythonResponse.json(), response.json()]);
  const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
  assert.deepEqual(withoutNow(payload), withoutNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.snapshot_source, "toss_openapi");
  assert.ok(payload.snapshot_date === null || /^\d{4}-\d{2}-\d{2}$/.test(payload.snapshot_date));
  assert.ok(Array.isArray(payload.missing_domains));
  for (const key of ["top_kospi_stocks", "top_kosdaq_stocks", "top_etfs", "market_indices"]) assert.ok(Array.isArray(payload[key]));
  assert.equal("operator_status" in payload, false);
  assert.equal("settings" in payload, false);
});

test("flow-trend API is GET-only, date-bounded, and read-only", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/flow-trend?date=2026-10-08&limit=5", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL("/api/flow-trend?date=2026-02-30", origin))).status, 400);
  const [pythonResponse, response] = await Promise.all([
    fetch(`${pythonOrigin}/api/flow-trend?date=2026-10-08&limit=5`),
    fetch(new URL("/api/flow-trend?date=2026-10-08&limit=5&symbols=005930", origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(response.status, 200);
  const [pythonPayload, payload] = await Promise.all([pythonResponse.json(), response.json()]);
  const withoutCategoryNow = ({ now: _now, ...value }) => value;
  assert.deepEqual(withoutCategoryNow(payload), withoutCategoryNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.business_date, "2026-10-08");
  assert.equal(payload.data_scope, "stored_toss_close_market_flow");
  assert.equal(payload.live_fetch, false);
  assert.equal(payload.scoring, false);
  assert.ok(payload.items.every((item) => item.business_date <= payload.business_date));
  const bounded = await fetch(new URL("/api/flow-trend?date=2026-10-08&limit=999&symbols=005930", origin));
  assert.equal(bounded.status, 200);
  assert.ok((await bounded.json()).items.length <= 20);
});

test("market page stays a public read-only view", async () => {
  const [apiResponse, pageResponse] = await Promise.all([
    fetch(new URL("/api/market", origin)),
    fetch(new URL("/market", origin)),
  ]);
  assert.equal(apiResponse.status, 200);
  assert.equal(pageResponse.status, 200);
  const market = await apiResponse.json();
  const html = await pageResponse.text();
  assert.match(html, /시장 참고/);
  assert.match(html, /저장 시장 스냅샷 기준일/);
  assert.match(html, /저장 시장 수급 흐름/);
  if (market.snapshot_date) assert.ok(html.includes(market.snapshot_date));
  else assert.match(html, /저장된 Toss 20:00 시장 스냅샷이 없습니다/);
  assert.doesNotMatch(html, /access.code|로그인/i);
});

test("ETF trend API and selected-date page preserve stored-date states", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/etf-trend?date=2026-10-08&limit=5", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL("/api/etf-trend?date=2026-02-30", origin))).status, 400);
  const [pythonResponse, response] = await Promise.all([
    fetch(`${pythonOrigin}/api/etf-trend?date=2026-10-08&limit=20`),
    fetch(new URL("/api/etf-trend?date=2026-10-08&limit=999&symbols=005930", origin)),
  ]);
  assert.equal(pythonResponse.status, 200);
  assert.equal(response.status, 200);
  const [pythonPayload, payload] = await Promise.all([pythonResponse.json(), response.json()]);
  const withoutNow = ({ now: _now, ...snapshot }) => snapshot;
  assert.deepEqual(withoutNow(payload), withoutNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.business_date, "2026-10-08");
  assert.ok(["exact", "stale", "missing"].includes(payload.reference_status));
  if (payload.reference_status === "exact") assert.equal(payload.reference_date, payload.business_date);
  if (payload.reference_status === "stale") assert.ok(payload.reference_date < payload.business_date);
  if (payload.reference_status === "missing") assert.equal(payload.reference_date, null);
  assert.equal(payload.data_scope, "stored_toss_close_snapshot");
  assert.equal(payload.live_fetch, false);
  assert.equal(payload.constituents_available, false);
  assert.ok(payload.items.every((item) => item.business_date <= payload.business_date));
  assert.ok(payload.items.length <= 20);
  const page = await fetch(new URL("/daily/2026-10-08/etf", origin));
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.match(html, /ETF 저장 흐름/);
  if (payload.items.length) assert.ok(html.includes(payload.items[0].business_date));
  else assert.ok(html.includes(payload.notice));
  assert.match(html, /구성종목이나 매매 판단은 포함하지 않습니다/);
});

test("category and category-trend APIs are GET-only and date labelled", async () => {
  const params = new URLSearchParams({ date: "2026-10-08", type: "sector", display_name: "반도체", public_category_id: "sector|반도체|fallback", arbitrary: "x" });
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL(`/api/category?${params}`, origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL(`/api/category?${new URLSearchParams({ ...Object.fromEntries(params), date: "2026-02-30" })}`, origin))).status, 400);
  const response = await fetch(new URL(`/api/category?${params}`, origin));
  const pythonResponse = await fetch(`${pythonOrigin}/api/category?${params}`);
  assert.equal(response.status, 200);
  assert.equal(pythonResponse.status, 200);
  const payload = await response.json();
  const pythonPayload = await pythonResponse.json();
  const withoutCategoryNow = ({ now: _now, ...value }) => value;
  assert.deepEqual(withoutCategoryNow(payload), withoutCategoryNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.business_date, "2026-10-08");
  assert.equal(payload.category_type, "sector");
  assert.ok(payload.snapshot_date === null || payload.snapshot_date <= payload.business_date);
  assert.ok(payload.stocks.every((item) => item.business_date === payload.business_date));
  const idOnlyParams = new URLSearchParams({ date: "2026-10-08", public_category_id: "sector|반도체|fallback" });
  const [idOnly, pythonIdOnly] = await Promise.all([
    fetch(new URL(`/api/category?${idOnlyParams}`, origin)),
    fetch(`${pythonOrigin}/api/category?${idOnlyParams}`),
  ]);
  assert.equal(idOnly.status, 200);
  assert.equal(pythonIdOnly.status, 200);
  assert.deepEqual(withoutCategoryNow(await idOnly.json()), withoutCategoryNow(await pythonIdOnly.json()));
  const typeMismatch = new URLSearchParams({ date: "2026-10-08", type: "theme", public_category_id: "sector|반도체|fallback" });
  assert.equal((await fetch(new URL(`/api/category?${typeMismatch}`, origin))).status, 400);
  assert.equal((await fetch(`${pythonOrigin}/api/category?${typeMismatch}`)).status, 400);

  const trendParams = new URLSearchParams({ type: "sector", display_name: "__e2e_category_trend__", limit: "999", arbitrary: "x" });
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL(`/api/category-trend?${trendParams}`, origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL("/api/category-trend?type=unknown&display_name=x", origin))).status, 400);
  const trend = await fetch(new URL(`/api/category-trend?${trendParams}`, origin));
  assert.equal(trend.status, 200);
  const trendPayload = await trend.json();
  const pythonTrend = await fetch(`${pythonOrigin}/api/category-trend?${trendParams}`);
  assert.equal(pythonTrend.status, 200);
  const pythonTrendPayload = await pythonTrend.json();
  const withoutNow = ({ now: _now, ...value }) => value;
  assert.deepEqual(withoutNow(trendPayload), withoutNow(pythonTrendPayload));
  for (const [query, status] of [
    [new URLSearchParams({ type: "sector", name: "__e2e_name_alias__", limit: "20" }), 200],
    [new URLSearchParams({ public_category_id: "sector|__e2e_id_only__|trend", limit: "20" }), 200],
    [new URLSearchParams({ type: "sector", display_name: "__e2e_overridden__", public_category_id: "sector|__e2e_id_override__|trend", limit: "20" }), 200],
    [new URLSearchParams({ type: "theme", public_category_id: "sector|__e2e_id_mismatch__|trend", limit: "20" }), 400],
  ]) {
    const [nextResponse, pythonResponse] = await Promise.all([
      fetch(new URL(`/api/category-trend?${query}`, origin)),
      fetch(`${pythonOrigin}/api/category-trend?${query}`),
    ]);
    assert.equal(nextResponse.status, status);
    assert.equal(pythonResponse.status, status);
    if (status === 200) {
      const [nextPayload, pythonPayload] = await Promise.all([nextResponse.json(), pythonResponse.json()]);
      assert.deepEqual(withoutNow(nextPayload), withoutNow(pythonPayload));
    }
  }
  assert.equal(trendPayload.read_only, true);
  assert.equal(trendPayload.category_type, "sector");
  assert.ok(Array.isArray(trendPayload.trend));
  const page = await fetch(new URL(`/daily/2026-10-08/category?${params}`, origin));
  assert.equal(page.status, 200);
  assert.match(await page.text(), /저장 분류 흐름/);
  const overriddenPage = await fetch(new URL(`/daily/2026-10-08/category?${new URLSearchParams({
    type: "sector", display_name: "다른 분류", public_category_id: "sector|반도체|fallback",
  })}`, origin));
  assert.equal(overriddenPage.status, 200);
  const overriddenHtml = await overriddenPage.text();
  const plainOverriddenHtml = overriddenHtml.replaceAll("<!-- -->", "");
  assert.match(plainOverriddenHtml, /업종: 반도체/);
  assert.doesNotMatch(plainOverriddenHtml, /업종: 다른 분류/);
  const mismatchedPage = await fetch(new URL(`/daily/2026-10-08/category?${new URLSearchParams({
    type: "theme", display_name: "AI반도체", public_category_id: "sector|반도체|fallback",
  })}`, origin));
  assert.equal(mismatchedPage.status, 404);
});

test("rotation and fixed cycle image routes stay public GET-only without local image paths", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/rotation-overlay?date=2026-10-08&limit=5", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL("/api/rotation-overlay?date=2026-02-30", origin))).status, 400);
  const response = await fetch(new URL("/api/rotation-overlay?date=2026-10-08&limit=999&symbols=005930", origin));
  assert.equal(response.status, 200);
  const payload = await response.json();
  const pythonResponse = await fetch(`${pythonOrigin}/api/rotation-overlay?date=2026-10-08&limit=10&symbols=005930`);
  assert.equal(pythonResponse.status, 200);
  const pythonPayload = await pythonResponse.json();
  const withoutImagePath = ({ image, ...value }) => {
    const { path: _path, ...publicImage } = image;
    return { ...value, image: publicImage };
  };
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.business_date, "2026-10-08");
  assert.equal("path" in payload.image, false);
  assert.ok(Array.isArray(payload.highlights));
  assert.deepEqual(withoutImagePath(payload), withoutImagePath(pythonPayload));
  const image = await fetch(new URL("/assets/cycle.jpg", origin));
  assert.equal(image.status, 200);
  assert.match(image.headers.get("content-type") ?? "", /image\/jpeg/);
  const page = await fetch(new URL("/daily/2026-10-08/rotation", origin));
  assert.equal(page.status, 200);
  assert.match(await page.text(), /업종·테마 위치 참고/);
});

test("observation summary and historical backtest remain GET-only and non-scoring", async () => {
  for (const path of ["/api/observation-summary?date=2026-10-08", "/api/observation/backtest?date=2026-10-08&limit=20&mention_threshold=2"]) {
    for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
      const response = await fetch(new URL(path, origin), { method });
      assert.equal(response.status, 405, `${method} must be rejected for ${path}`);
      if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
    }
  }
  assert.equal((await fetch(new URL("/api/observation-summary?date=2026-02-30", origin))).status, 400);
  const summaryResponse = await fetch(new URL("/api/observation-summary?date=2026-10-08&stock=005930", origin));
  assert.equal(summaryResponse.status, 200);
  const summary = await summaryResponse.json();
  assert.equal(summary.source, "stored_report_toss_observation_summary");
  assert.equal(summary.business_date, "2026-10-08");
  assert.equal(summary.live_fetch, false);
  assert.equal(summary.scoring, false);
  assert.equal(summary.recommendation, false);

  const backtestResponse = await fetch(new URL("/api/observation/backtest?date=2026-10-08&limit=999&mention_threshold=999&arbitrary=x", origin));
  assert.equal(backtestResponse.status, 200);
  const backtest = await backtestResponse.json();
  assert.equal(backtest.data_scope, "stored_report_krx_backtest_observation");
  assert.equal(backtest.business_date, "2026-10-08");
  assert.equal(backtest.live_fetch, false);
  assert.equal(backtest.scoring, false);
  assert.equal(backtest.recommendation, false);
  assert.deepEqual(backtest.horizons, [1, 5, 10, 20]);
  assert.ok(backtest.rows.length <= 100);
  const page = await fetch(new URL("/daily/2026-10-08/observations", origin));
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.match(html, /저장 관찰 요약/);
  assert.match(html, /과거 리포트 반응과 목표가 확인/);
  assert.doesNotMatch(html, /buy signal|sell signal|access.code|로그인/i);
});

test("priority reference APIs remain bounded GET-only paths; live reads are not triggered by this check", async () => {
  const invalidPaths = [
    "/api/toss-market-context?date=2026-02-30",
    "/api/toss-priority-quotes?date=2026-02-30",
    "/api/priority-current-quotes?date=2026-02-30",
    "/api/toss-priority-daily-candles?date=2026-02-30&days=90",
    "/api/priority-indicators?date=2026-02-30",
    "/api/intraday?date=2026-02-30",
  ];
  for (const path of invalidPaths) assert.equal((await fetch(new URL(path, origin))).status, 400);
  assert.equal((await fetch(new URL("/api/priority-indicators?date=2026-10-08&symbols=005930", origin))).status, 400);
  const paths = [
    "/api/toss-market-context?date=2026-10-08",
    "/api/toss-priority-quotes?date=2026-10-08",
    "/api/priority-current-quotes?date=2026-10-08",
    "/api/toss-priority-daily-candles?date=2026-10-08&days=90",
    "/api/priority-indicators?date=2026-10-08",
    "/api/intraday?date=2026-10-08",
  ];
  for (const path of paths) {
    for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
      const response = await fetch(new URL(path, origin), { method });
      assert.equal(response.status, 405, `${method} must be rejected for ${path}`);
      if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
    }
  }
});

test("Next health reports only process health and is GET-only", async () => {
  const response = await fetch(new URL("/health", origin));
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "ok");
  assert.equal(response.headers.get("x-stock-monitor-service"), "next-web-view");
  assert.equal((await fetch(new URL("/health", origin), { method: "POST" })).status, 405);
});

test("Main Top2 page renders the stored cohort before any user-triggered live reference", async () => {
  const response = await fetch(new URL("/daily/2026-10-08/main", origin));
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /KR-Stock/);
  assert.match(html, /aria-label="상단 탭"/);
  assert.match(html, /메인/);
  assert.match(html, /관찰/);
  assert.match(html, /종목/);
  assert.match(html, /저장 종목 검색/);
  assert.match(html, /오늘의 우선순위/);
  assert.match(html, /class="main-top2-market-reference"/);
  assert.match(html, /Toss 선택일 저장/);
  assert.match(html, /aria-current="page"/);
  assert.match(html, /일봉 범위/);
  assert.match(html, /보조 지표/);
  assert.match(html, /top-two-evidence-details/);
  assert.match(html, /Naver 저장 리포트 · 기준일/);
  assert.match(html, /오늘 읽을 요약/);
  assert.match(html, /href="\/daily\/2026-10-08\/candidates"/);
  assert.match(html, /href="\/daily\/2026-10-08\/stocks"/);
  assert.doesNotMatch(html, /main-observation-candidate-preview|main-daily-stock-preview/);
  assert.match(html, /class="news-observation-summary"/);
  assert.doesNotMatch(html, /main-news-details|main-news-items-heading/);
  assert.match(html, /<details class="daily-briefing main-industry-etf-details"/);
  for (const path of ["intraday", "etf", "rotation"]) {
    assert.match(html, new RegExp(`href="/daily/2026-10-08/${path}"`));
  }
  assert.doesNotMatch(html, /href="\/daily\/2026-10-08\/category"/);
  assert.match(html, /데이터 기준/);
  assert.match(html, /시장 문맥 · Toss 당일 · Toss 저장/);
  assert.match(html, /<details class="daily-briefing daily-market-context">/);
  assert.match(html, /선택일 저장 지수/);
  assert.match(html, /최근 Toss 저장 흐름/);
  assert.match(html, /Toss 저장 시장 수급/);
  assert.match(html, /class="market-context-flow-trend"/);
  assert.doesNotMatch(html, /class="daily-briefing main-flow-trend"/);
  assert.doesNotMatch(html, /<details class="daily-briefing daily-market-context"[^>]* open=""/);
  assert.doesNotMatch(html, /<details class="market-context-flow-trend"[^>]* open=""/);
  assert.match(html, /수급 흐름/);
  assert.match(html, /Toss 저장값 · 실시간 호출 없음/);
  assert.match(html.replaceAll("<!-- -->", ""), /선택 기준일 2026-10-08 · 수급 기준일/);
  assert.match(html, /저장 뉴스/);
  assert.match(html, /수집 시각/);
  assert.match(html, /직접 근거/);
  const candidatesResponse = await fetch(new URL("/api/candidate-evidence?date=2026-10-08", origin));
  assert.equal(candidatesResponse.status, 200);
  const candidateRows = (await candidatesResponse.json()).rows;
  const selectedCandidates = candidateRows.filter((row) => row.selected);
  for (const candidate of selectedCandidates) {
    if (candidate.research_focus?.items?.length) {
      assert.match(html, /연결된 원문 제목/);
      for (const item of candidate.research_focus.items.slice(0, 3)) assert.ok(html.includes(item.source_title));
    }
    if (candidate.target_price_revision?.available) {
      assert.match(html, /목표가 변경 참고/);
      assert.ok(html.includes(candidate.target_price_revision.previous_date));
    }
  }
  const newsResponse = await fetch(new URL("/api/daily/2026-10-08", origin));
  assert.equal(newsResponse.status, 200);
  const dailyPayload = await newsResponse.json();
  for (const item of dailyPayload.source_freshness_summary.items) {
    const number = (value) => new Intl.NumberFormat("ko-KR").format(value);
    if (item.count !== undefined && item.count !== null) assert.ok(html.includes(`${number(item.count)}건`));
    if (item.coverage_count !== undefined && item.candidate_count !== undefined) {
      assert.ok(html.includes(`후보 ${number(item.coverage_count)}/${number(item.candidate_count)}`));
    }
  }
  const news = dailyPayload.news_observation_summary;
  const observationItems = news.items ?? [];
  const featuredObservation = observationItems.find((item) => item.connection_label === news.display_label) ?? observationItems[0];
  assert.ok(featuredObservation);
  assert.match(html, /class="news-observation-summary-featured"/);
  assert.ok(html.includes(featuredObservation.stock_name));
  assert.ok(html.includes(featuredObservation.connection_label || featuredObservation.display_label));
  const featuredText = String(featuredObservation.top_title || featuredObservation.reason)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#x27;");
  assert.ok(html.includes(featuredText));
  assert.doesNotMatch(html, /main-news-observation-items|main-news-details/);
  for (const name of (news.candidate_overlap_names ?? []).slice(0, 3)) assert.ok(html.includes(name));
  if (news.available && news.top_titles?.length) {
    assert.match(html, /news-observation-summary-titles/);
    for (const title of news.top_titles.slice(0, 3)) {
      const escapedTitle = String(title).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#x27;");
      assert.ok(html.includes(escapedTitle));
    }
  }
  assert.match(html, /지수 참고:/);
  assert.ok(html.indexOf("오늘 읽을 요약") > html.indexOf("오늘의 우선순위"));
  assert.match(html, /오늘의 우선순위/);
  assert.match(html, /Toss 현재가 · 수급/);
  assert.match(html, /지수 · 수급 확인/);
  assert.match(html, /차트 · 지표 확인/);
  assert.match(html, /거래대금 겹침/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>거래대금 겹침/);
  assert.doesNotMatch(html, /access.code|로그인|주문/i);
  const v2 = await fetch(new URL("/v2", origin), { redirect: "manual" });
  assert.equal(v2.status, 200);
  const v2Html = await v2.text();
  assert.match(v2Html, /KR-Stock V2 Preview/);
  assert.match(v2Html, /오늘의 흐름/);
  assert.match(v2Html, /근거 레이어/);
  const watch = await fetch(new URL("/daily/2026-10-08/candidates", origin));
  assert.equal(watch.status, 200);
  const watchHtml = await watch.text();
  assert.match(watchHtml, /aria-label="상단 탭"/);
  assert.match(watchHtml, /class="daily-briefing watch-candidate-panel"/);
  assert.match(watchHtml, /h1 id="watch-candidates-heading"/);
  assert.match(watchHtml, /우선 확인/);
  assert.match(watchHtml, /class="watch-candidate-grid"/);
  assert.match(watchHtml, /class="watch-candidate-card"/);
  assert.match(watchHtml, /실시간 조회 없음/);
  assert.doesNotMatch(watchHtml, /조회 시각/);
  assert.doesNotMatch(watchHtml, /확인 필요 · 저장 누락 없음/);
  assert.match(watchHtml, /종목 상세 보기/);
  const watchPanelStart = watchHtml.indexOf('<div id="daily-watch-panel"');
  const stockPanelStart = watchHtml.indexOf('<div id="daily-stock-panel"');
  assert.ok(watchPanelStart >= 0 && stockPanelStart > watchPanelStart);
  assert.doesNotMatch(watchHtml.slice(watchPanelStart, stockPanelStart), /<table/);
  assert.match(watchHtml.slice(stockPanelStart), /<table/);
});

test("stock tab shows the daily report summary and toggles single-mention rows", async () => {
  const dailyResponse = await fetch(new URL("/api/daily/2026-10-08", origin));
  assert.equal(dailyResponse.status, 200);
  const daily = await dailyResponse.json();
  const multiReportCodes = daily.stocks.filter((item) => item.mention_count > 1 && item.stock_code).map((item) => item.stock_code);
  const allCodes = daily.stocks.filter((item) => item.stock_code).map((item) => item.stock_code);

  const summaryPage = await fetch(new URL("/daily/2026-10-08/stocks", origin));
  assert.equal(summaryPage.status, 200);
  const summaryHtml = await summaryPage.text();
  assert.match(summaryHtml, /일일 종목 요약/);
  assert.match(summaryHtml, /class="daily-briefing stock-summary-page"/);
  assert.match(summaryHtml, /h1 id="stock-summary-heading"/);
  assert.match(summaryHtml, /caption class="sr-only"/);
  assert.doesNotMatch(summaryHtml, /적용/);
  assert.match(summaryHtml, /원문 의견/);
  assert.match(summaryHtml, /Toss 참고/);
  for (const match of summaryHtml.matchAll(/href="\/daily\/2026-10-08\/stocks\?stock=(\d{6})(?:&amp;(?:include_single=1|limit=\d+))*#selected-stock"/g)) assert.match(match[1], /^\d{6}$/);
  assert.match(summaryHtml, /1건 포함/);
  assert.match(summaryHtml, /원문 의견/);
  assert.match(summaryHtml, /Toss 참고/);
  assert.match(summaryHtml, /mobile-card-table/);
  const shownCodes = dailyStockSelectionCodes(summaryHtml);
  assert.deepEqual(shownCodes, multiReportCodes.slice(0, 6));
  assert.doesNotMatch(summaryHtml, /id="selected-stock"/);

  const selectedStockCode = shownCodes[0];
  const selectedStockPage = await fetch(new URL(`/daily/2026-10-08/stocks?stock=${selectedStockCode}`, origin));
  assert.equal(selectedStockPage.status, 200);
  const selectedStockHtml = await selectedStockPage.text();
  assert.match(selectedStockHtml, /id="selected-stock"/);
  assert.match(selectedStockHtml, /class="selected-stock-report-list"/);

  const detailPage = await fetch(new URL(`/daily/2026-10-08/stocks/${selectedStockCode}`, origin));
  assert.equal(detailPage.status, 200);
  const detailHtml = await detailPage.text();
  assert.ok(detailHtml.includes(`href="/daily/2026-10-08/main?stock=${selectedStockCode}"`));
  assert.ok(detailHtml.includes(`href="/daily/2026-10-08/candidates?stock=${selectedStockCode}"`));

  const statefulPage = await fetch(new URL(`/daily/2026-10-08/stocks?stock=${selectedStockCode}&include_single=1&limit=12`, origin));
  const statefulHtml = await statefulPage.text();
  assert.match(statefulHtml, new RegExp(`name="stock" value="${selectedStockCode}"`));
  assert.match(statefulHtml, /name="limit" value="12"/);
  const statefulLinks = dailyStockSelectionCodes(statefulHtml);
  assert.deepEqual(statefulLinks, allCodes.slice(0, 12));

  const allRowsPage = await fetch(new URL("/daily/2026-10-08/stocks?include_single=1", origin));
  assert.equal(allRowsPage.status, 200);
  const allRowsHtml = await allRowsPage.text();
  const allShownCodes = dailyStockSelectionCodes(allRowsHtml);
  assert.deepEqual(allShownCodes, allCodes.slice(0, 6));
  assert.match(allRowsHtml, /더 보기/);

  const expandedRowsPage = await fetch(new URL("/daily/2026-10-08/stocks?include_single=1&limit=12", origin));
  assert.equal(expandedRowsPage.status, 200);
  const expandedRowsHtml = await expandedRowsPage.text();
  const expandedCodes = dailyStockSelectionCodes(expandedRowsHtml);
  assert.deepEqual(expandedCodes, allCodes.slice(0, 12));

  const searchPage = await fetch(new URL("/daily/2026-10-08/stocks?q=005930", origin));
  assert.equal(searchPage.status, 200);
  assert.match(await searchPage.text(), /저장 종목 검색/);
});

test("intraday history is a date-bound public summary with no operator payload", async () => {
  for (const method of ["OPTIONS", "POST", "PUT", "PATCH", "DELETE", "HEAD"]) {
    const response = await fetch(new URL("/api/intraday?date=2026-10-08", origin), { method });
    assert.equal(response.status, 405, `${method} must be rejected`);
    if (method === "OPTIONS" || method === "HEAD") assert.equal(response.headers.get("allow"), "GET");
  }
  assert.equal((await fetch(new URL("/api/intraday?date=2026-02-30", origin))).status, 400);
  const [response, pythonResponse] = await Promise.all([
    fetch(new URL("/api/intraday?date=2026-10-08&task=StockMonitor-Poll", origin)),
    fetch(`${pythonOrigin}/api/intraday?date=2026-10-08`),
  ]);
  assert.equal(response.status, 200);
  assert.equal(pythonResponse.status, 200);
  const payload = await response.json();
  const pythonPayload = await pythonResponse.json();
  const withoutNow = ({ now: _now, ...value }) => value;
  assert.deepEqual(withoutNow(payload), withoutNow(pythonPayload));
  assert.equal(payload.surface, "web-view");
  assert.equal(payload.read_only, true);
  assert.equal(payload.business_date, "2026-10-08");
  assert.ok(payload.batches.every((item) => item.business_date === payload.business_date));
  assert.equal("task_name" in payload, false);
  assert.equal("operator_status" in payload, false);
  const page = await fetch(new URL("/daily/2026-10-08/intraday", origin));
  assert.equal(page.status, 200);
  const pageHtml = await page.text();
  assert.match(pageHtml, /class="daily-briefing intraday-summary"/);
  assert.match(pageHtml, /h1 id="intraday-heading"/);
  assert.match(pageHtml, /장중 리포트 기록/);
});

test("Next.js does not expose access-code login or logout routes", async () => {
  for (const path of ["/auth/login", "/auth/logout"]) {
    const response = await fetch(new URL(path, origin));
    assert.equal(response.status, 404, `${path} must not be present on Next.js`);
  }
});

test("operator paths are not present on the public app", async () => {
  for (const path of ["/api/status", "/admin", "/operator-review"]) {
    const response = await fetch(new URL(path, origin));
    assert.equal(response.status, 404, `${path} must stay unavailable`);
  }
});
