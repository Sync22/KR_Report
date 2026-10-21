import assert from "node:assert/strict";
import test from "node:test";

import { compactMarketDateTime, formatMarketTurnover } from "../src/domain/market-display.ts";

test("market turnover is shown in truncated 억 and 만 units", () => {
  assert.equal(formatMarketTurnover(123_456_789), "1억 2,345만");
  assert.equal(formatMarketTurnover(99_999_999), "9,999만");
  assert.equal(formatMarketTurnover(9_999), "9,999원");
  assert.equal(formatMarketTurnover(null), "자료 없음");
});

test("market timestamps stay short and naive Naver timestamps use KST", () => {
  assert.equal(compactMarketDateTime("2026-10-20T09:36:41"), "10.20 09:36");
  assert.equal(compactMarketDateTime("2026-10-20T09:36:41+09:00"), "10.20 09:36");
  assert.equal(compactMarketDateTime("not a timestamp"), null);
});
