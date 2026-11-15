import assert from "node:assert/strict";
import test from "node:test";

import { overlayDailyIntradayMarketTop } from "../src/server/daily-market-commentary.ts";

const businessDate = "2026-11-16";
const now = new Date("2026-11-16T01:00:00.000Z");

function snapshot(mentionCount = 3) {
  return {
    business_date: businessDate,
    timezone: "Asia/Seoul",
    stocks: [
      { stock_code: "987654", stock_name: "Cache Cohort A", mention_count: mentionCount },
      { stock_code: "876543", stock_name: "Cache Cohort B", mention_count: 2 },
    ],
    priority_candidate_evidence: { rows: [
      { selected: true, stock_code: "987654" },
      { selected: true, stock_code: "876543" },
    ] },
    market_briefing: { turnover_reference_lines: ["거래대금"], flow_reference_lines: ["수급"] },
    market_commentary: {
      business_date: businessDate,
      live_fetch: false,
      same_day_report_status: { business_date: businessDate, can_overlap_intraday_market_top: true },
      comments: [],
    },
  };
}

function quote(stock_code) {
  return {
    stock_code,
    stock_name: stock_code,
    current_price: 100,
    prev_close_price: 99,
    change_price: 1,
    change_percent: 1,
    trade_amount: 10,
    trade_volume: 1,
    market_status: "OPEN",
    trade_time: null,
    sector_name: null,
  };
}

test("daily Naver references share in-flight and cached cohorts without refreshing source time", async () => {
  let cacheNow = 0;
  let checkedAt = now;
  const pageCalls = [];
  const quoteCalls = [];
  const dependencies = {
    now: checkedAt,
    clock: () => cacheNow,
    delaySeconds: 0,
    fetchPage: async (market, page, pageSize) => {
      pageCalls.push([market, page, pageSize]);
      await Promise.resolve();
      return [];
    },
    fetchQuote: async (stockCode) => {
      quoteCalls.push(stockCode);
      await Promise.resolve();
      return quote(stockCode);
    },
  };
  const base = snapshot();

  const [first, shared] = await Promise.all([
    overlayDailyIntradayMarketTop(base, businessDate, dependencies),
    overlayDailyIntradayMarketTop(base, businessDate, dependencies),
  ]);
  const firstReference = first.market_commentary.intraday_market_top_reference;
  assert.deepEqual(pageCalls, [["KOSPI", 1, 20], ["KOSDAQ", 1, 20]]);
  assert.deepEqual(quoteCalls, ["987654", "876543"]);
  assert.equal(shared.market_commentary.intraday_market_top_reference.checked_at, firstReference.checked_at);

  cacheNow = 5_000;
  checkedAt = new Date("2026-11-16T01:00:05.000Z");
  dependencies.now = checkedAt;
  const cached = await overlayDailyIntradayMarketTop(base, businessDate, dependencies);
  assert.equal(cached.market_commentary.intraday_market_top_reference.checked_at, firstReference.checked_at);
  assert.equal(pageCalls.length, 2);
  assert.equal(quoteCalls.length, 2);

  await overlayDailyIntradayMarketTop(snapshot(4), businessDate, dependencies);
  assert.equal(pageCalls.length, 4);
  assert.equal(quoteCalls.length, 4);

  cacheNow = 35_001;
  checkedAt = new Date("2026-11-16T01:00:35.001Z");
  dependencies.now = checkedAt;
  const expired = await overlayDailyIntradayMarketTop(snapshot(4), businessDate, dependencies);
  assert.equal(pageCalls.length, 6);
  assert.equal(quoteCalls.length, 6);
  assert.notEqual(expired.market_commentary.intraday_market_top_reference.checked_at, firstReference.checked_at);
});

test("daily Naver reference errors share in-flight results but are retried later", async () => {
  let failing = true;
  const pageCalls = [];
  const quoteCalls = [];
  const dependencies = {
    now,
    clock: () => 0,
    delaySeconds: 0,
    fetchPage: async (market, page, pageSize) => {
      pageCalls.push([market, page, pageSize]);
      await Promise.resolve();
      if (failing && market === "KOSPI") throw new Error("private upstream detail");
      return [];
    },
    fetchQuote: async (stockCode) => {
      quoteCalls.push(stockCode);
      await Promise.resolve();
      return quote(stockCode);
    },
  };
  const base = snapshot(5);

  const [first, shared] = await Promise.all([
    overlayDailyIntradayMarketTop(base, businessDate, dependencies),
    overlayDailyIntradayMarketTop(base, businessDate, dependencies),
  ]);
  const reference = first.market_commentary.intraday_market_top_reference;
  assert.equal(reference.errors.length, 1);
  assert.deepEqual(shared.market_commentary.intraday_market_top_reference.errors, reference.errors);
  assert.equal(pageCalls.length, 2);
  assert.equal(quoteCalls.length, 2);
  assert.doesNotMatch(JSON.stringify(first), /private upstream detail/);

  failing = false;
  const retried = await overlayDailyIntradayMarketTop(base, businessDate, dependencies);
  assert.equal(retried.market_commentary.intraday_market_top_reference.errors.length, 0);
  assert.equal(pageCalls.length, 4);
  assert.equal(quoteCalls.length, 2);
});
