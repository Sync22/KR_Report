import assert from "node:assert/strict";
import test from "node:test";

import { fetchNaverMarketTopStocks } from "../src/server/naver-market-top.ts";
import {
  buildIntradayMarketTopReference,
  overlayDailyIntradayMarketTop,
} from "../src/server/daily-market-commentary.ts";

const date = "2026-10-12";

function stock(code, amount, overrides = {}) {
  return {
    market: "KOSPI", sort_type: "tradeValue", stock_code: code, stock_name: code,
    stock_end_type: "stock", current_price: 100, change_price: 1, change_percent: 1,
    trade_amount: amount, trade_volume: 10, market_status: "OPEN", trade_time: null,
    ...overrides,
  };
}

function snapshot(overrides = {}) {
  return {
    timezone: "Asia/Seoul",
    business_date: date,
    stocks: [
      { stock_code: "005930", stock_name: "삼성전자", mention_count: 3 },
      { stock_code: "000660", stock_name: "SK하이닉스", mention_count: 2 },
    ],
    priority_candidate_evidence: { rows: [
      { selected: true, stock_code: "005930" },
      { selected: true, stock_code: "000660" },
    ] },
    market_briefing: { turnover_reference_lines: ["거래대금", "- 저장 기준 없음"], flow_reference_lines: ["수급"] },
    market_commentary: {
      business_date: date,
      live_fetch: false,
      same_day_report_status: {
        business_date: date, can_overlap_intraday_market_top: true, reason: "당일 리포트 종목 기준",
      },
      intraday_market_top_reference: { live_fetch: false, items: [], errors: [] },
      intraday_quote_reference: { live_fetch: false, items: [], errors: [] },
      comments: [
        { phase: "midday", comment: "저장 문구", details: [] },
        { phase: "preclose", comment: "저장 문구", details: [] },
      ],
    },
    ...overrides,
  };
}

test("Naver market-top provider uses the fixed endpoint and parses Python fields", async () => {
  let received;
  const result = await fetchNaverMarketTopStocks("KOSPI", {
    page: 2,
    pageSize: 20,
    fetchImpl: async (url, init) => {
      received = { url: new URL(url), init };
      return new Response(JSON.stringify({ stockListSortType: "tradeValue", stocks: [{
        itemCode: "005930", stockName: "삼성전자", stockEndType: "stock", closePriceRaw: "70,000",
        compareToPreviousClosePriceRaw: "500", fluctuationsRatio: "0.71", accumulatedTradingValueRaw: "1,234,000",
        accumulatedTradingVolumeRaw: "10,000", marketStatus: "OPEN", localTradedAt: "2026-10-12 10:00:00",
      }] }));
    },
  });

  assert.equal(received.url.origin, "https://m.stock.naver.com");
  assert.equal(received.url.pathname, "/api/stocks/priceTop/KOSPI");
  assert.equal(received.url.search, "?page=2&pageSize=20");
  assert.equal(received.init.method, "GET");
  assert.equal(received.init.redirect, "error");
  assert.ok(received.init.signal instanceof AbortSignal);
  assert.deepEqual(result, [stock("005930", 1234000, {
    market: "KOSPI", sort_type: "tradeValue", stock_name: "삼성전자", current_price: 70000,
    change_price: 500, change_percent: 0.71, trade_volume: 10000, trade_time: "2026-10-12T10:00:00",
  })]);
});

test("Naver provider rejects oversized bodies and hides the response text", async () => {
  const error = await fetchNaverMarketTopStocks("KOSDAQ", {
    page: 1,
    pageSize: 20,
    fetchImpl: async () => new Response("x".repeat(300_000)),
  }).then(() => null, (caught) => caught);
  assert.equal(error.code, "response_too_large");
  assert.doesNotMatch(error.message, /x{20}/);
});

test("market-top reference pages both markets, intersects report codes, deduplicates, and orders by turnover", async () => {
  const requests = [];
  const reference = await buildIntradayMarketTopReference([
    { stock_code: "005930", stock_name: "삼성전자", mention_count: 3 },
    { stock_code: "000660", stock_name: "SK하이닉스", mention_count: 2 },
  ], {
    now: new Date("2026-10-12T01:00:00.000Z"),
    delaySeconds: 0,
    fetchPage: async (market, page, pageSize) => {
      requests.push([market, page, pageSize]);
      if (market === "KOSPI") return [
        stock("005930", 100, { market, stock_name: "삼성전자" }),
        stock("123456", 999, { market, stock_name: "미언급 종목" }),
        stock("000660", 200, { market, stock_name: "SK하이닉스" }),
      ];
      return [stock("005930", 100, { market, stock_name: "중복 삼성전자" })];
    },
  });

  assert.deepEqual(requests, [["KOSPI", 1, 20], ["KOSDAQ", 1, 20]]);
  assert.equal(reference.source, "naver_price_top");
  assert.equal(reference.live_fetch, true);
  assert.equal(reference.writes_snapshot_tables, false);
  assert.equal(reference.calls, 2);
  assert.deepEqual(reference.items.map((item) => [item.stock_code, item.market, item.rank]), [
    ["000660", "KOSPI", 3], ["005930", "KOSPI", 1],
  ]);
  assert.equal(reference.checked_at, "2026-10-12T10:00:00.000+09:00");
  assert.equal(reference.empty_reason, null);
});

test("market-top reference keeps successful pages and emits safe page errors", async () => {
  const requests = [];
  const fullPage = Array.from({ length: 20 }, (_, index) => stock(`0000${String(index).padStart(2, "0")}`, 20 - index));
  const reference = await buildIntradayMarketTopReference([
    { stock_code: "000001", stock_name: "대상", mention_count: 1 },
  ], {
    delaySeconds: 0,
    fetchPage: async (market, page) => {
      requests.push([market, page]);
      if (market === "KOSPI" && page === 1) return fullPage;
      if (market === "KOSPI") throw new Error("secret response body and cookie");
      return [stock("000001", 100, { market })];
    },
  });

  assert.deepEqual(requests, [["KOSPI", 1], ["KOSPI", 2], ["KOSDAQ", 1]]);
  assert.equal(reference.calls, 2);
  assert.deepEqual(reference.errors, [{ market: "KOSPI", page: "2", error: "upstream_unavailable" }]);
  assert.equal(reference.items.length, 1);
  assert.equal(reference.empty_reason, null);
  assert.doesNotMatch(JSON.stringify(reference), /secret response|cookie/);
});

test("daily overlay fails closed on date or eligibility mismatches", async () => {
  let calls = 0;
  const dependencies = {
    fetchPage: async () => { calls += 1; return []; },
    fetchQuote: async () => { calls += 1; return {}; },
  };
  for (const altered of [
    { business_date: "2026-10-11" },
    { market_commentary: { ...snapshot().market_commentary, business_date: "2026-10-11" } },
    { market_commentary: { ...snapshot().market_commentary, same_day_report_status: { business_date: "2026-10-11", can_overlap_intraday_market_top: true } } },
    { market_commentary: { ...snapshot().market_commentary, same_day_report_status: { business_date: date, can_overlap_intraday_market_top: false } } },
  ]) {
    const base = snapshot(altered);
    assert.equal(await overlayDailyIntradayMarketTop(base, date, dependencies), base);
  }
  assert.equal(calls, 0);
});

test("eligible daily overlay includes Naver market and quote references for server-selected candidates", async () => {
  const base = snapshot();
  const result = await overlayDailyIntradayMarketTop(base, date, {
    now: new Date("2026-10-12T01:00:00.000Z"),
    delaySeconds: 0,
    fetchPage: async (market) => market === "KOSPI" ? [stock("005930", 50, { market })] : [],
    fetchQuote: async (code) => ({
      stock_code: code, stock_name: code === "005930" ? "삼성전자" : "SK하이닉스", current_price: 70000,
      prev_close_price: 69000, change_price: 1000, change_percent: 1.45, trade_amount: 1000000,
      trade_volume: 100, market_status: "OPEN", trade_time: "2026-10-12T10:00:00", sector_name: "전기전자",
    }),
  });

  assert.equal(result.business_date, date);
  assert.equal(result.market_commentary.live_fetch, true);
  assert.equal(result.market_commentary.intraday_quote_reference.source, "naver_quote");
  assert.deepEqual(result.market_commentary.intraday_quote_reference.items.map((item) => item.stock_code), ["005930", "000660"]);
  assert.deepEqual(result.market_commentary.intraday_quote_reference.items.map((item) => item.resolution_source), ["summary_stock_code", "summary_stock_code"]);
  assert.equal(result.market_commentary.intraday_quote_reference.writes_snapshot_tables, false);
  assert.equal(result.market_commentary.intraday_market_top_reference.items[0].stock_code, "005930");
  assert.equal(result.market_commentary.comments[0].phase, "midday");
  assert.match(result.market_commentary.comments[0].comment, /Naver 거래대금 상위 기준/);
  assert.doesNotMatch(JSON.stringify(result), /client_secret|access_token|response body/i);
});
