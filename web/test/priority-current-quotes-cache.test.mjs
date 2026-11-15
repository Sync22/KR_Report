import assert from "node:assert/strict";
import test from "node:test";

import * as priorityQuotes from "../src/server/priority-current-quotes.ts";

const businessDate = "2026-11-16";

function quote(stockCode) {
  return {
    stock_code: stockCode,
    stock_name: `종목 ${stockCode}`,
    sector_code: null,
    sector_name: null,
    current_price: 100,
    market_status: "OPEN",
    trade_time: "2026-11-16T10:00:00",
    prev_close_price: 99,
    change_price: 1,
    change_percent: 1,
    trade_amount: 1000,
    trade_volume: 10,
  };
}

function service(options) {
  assert.equal(typeof priorityQuotes.PriorityCurrentQuotesService, "function");
  return new priorityQuotes.PriorityCurrentQuotesService(options);
}

test("priority Naver quotes share in-flight and cache successful Top2 cohort with original checked time", async () => {
  let clock = 0;
  let now = new Date("2026-11-16T01:00:00.000Z");
  let selection = { latestBusinessDate: businessDate, codes: ["987654", "876543"] };
  const calls = [];
  const quotes = service({
    loadSelection: () => selection,
    fetchQuote: async (code) => { calls.push(code); await Promise.resolve(); return quote(code); },
    clock: () => clock,
    now: () => now,
  });

  const [first, shared] = await Promise.all([
    quotes.getQuotes(businessDate),
    quotes.getQuotes(businessDate),
  ]);
  assert.deepEqual(calls, ["987654", "876543"]);
  assert.equal(first.payload.checked_at, shared.payload.checked_at);

  clock = 5;
  now = new Date("2026-11-16T01:00:05.000Z");
  const cached = await quotes.getQuotes(businessDate);
  assert.equal(calls.length, 2);
  assert.equal(cached.payload.checked_at, first.payload.checked_at);

  selection = { latestBusinessDate: businessDate, codes: ["876543", "987654"] };
  await quotes.getQuotes(businessDate);
  assert.deepEqual(calls, ["987654", "876543", "876543", "987654"]);

  clock = 35.001;
  now = new Date("2026-11-16T01:00:35.001Z");
  const expired = await quotes.getQuotes(businessDate);
  assert.equal(calls.length, 6);
  assert.notEqual(expired.payload.checked_at, cached.payload.checked_at);
});

test("priority Naver quote failures share in-flight results but are retried on a later request", async () => {
  let fail = true;
  const calls = [];
  const quotes = service({
    loadSelection: () => ({ latestBusinessDate: businessDate, codes: ["987653", "876542"] }),
    fetchQuote: async (code) => {
      calls.push(code);
      await Promise.resolve();
      if (fail && code === "987653") throw new Error("private upstream detail");
      return quote(code);
    },
    clock: () => 0,
    now: () => new Date("2026-11-16T01:00:00.000Z"),
  });

  const [first, shared] = await Promise.all([
    quotes.getQuotes(businessDate),
    quotes.getQuotes(businessDate),
  ]);
  assert.deepEqual(first.payload.errors, ["987653"]);
  assert.deepEqual(shared.payload.errors, first.payload.errors);
  assert.deepEqual(calls, ["987653", "876542"]);
  assert.doesNotMatch(JSON.stringify(first.payload), /private upstream detail/);

  fail = false;
  const retry = await quotes.getQuotes(businessDate);
  assert.deepEqual(retry.payload.errors, []);
  assert.deepEqual(calls, ["987653", "876542", "987653", "876542"]);
});

test("priority Naver quotes validate latest date before consulting the cache", async () => {
  let calls = 0;
  let latestBusinessDate = businessDate;
  const quotes = service({
    loadSelection: () => ({ latestBusinessDate, codes: ["987652"] }),
    fetchQuote: async () => { calls += 1; return quote("987652"); },
    clock: () => 0,
    now: () => new Date("2026-11-16T01:00:00.000Z"),
  });

  const initial = await quotes.getQuotes(businessDate);
  assert.equal(initial.status, 200);
  assert.equal(calls, 1);

  latestBusinessDate = "2026-11-17";
  const result = await quotes.getQuotes(businessDate);
  assert.equal(result.status, 409);
  assert.equal(result.payload.reason, "latest_business_date_only");
  assert.equal(calls, 1);
});
