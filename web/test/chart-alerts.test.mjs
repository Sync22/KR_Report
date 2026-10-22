import assert from "node:assert/strict";
import test from "node:test";

import { chartAlertEventId, isReportFocusCandidate, parseMinuteCandles } from "../src/domain/chart-alerts.ts";

test("report alert eligibility requires the exact selected-date report-focus evidence", () => {
  const row = {
    business_date: "2026-10-22",
    stock_code: "005930",
    stock_name: "삼성전자",
    report_summary: { report_count: 2 },
    why_notable: ["리포트 집중"],
  };
  assert.equal(isReportFocusCandidate(row, "2026-10-22"), true);
  assert.equal(isReportFocusCandidate({ ...row, business_date: "2026-10-21" }, "2026-10-22"), false);
  assert.equal(isReportFocusCandidate({ ...row, stock_code: "AAPL" }, "2026-10-22"), false);
  assert.equal(isReportFocusCandidate({ ...row, report_summary: { report_count: 1 } }, "2026-10-22"), false);
  assert.equal(isReportFocusCandidate({ ...row, why_notable: ["리포트 언급"] }, "2026-10-22"), false);
});

test("minute candles are validated, sorted and capped to one provider page", () => {
  const later = { timestamp: "2026-10-22T01:02:00Z", openPrice: 100, highPrice: 103, lowPrice: 99, closePrice: 102, volume: 10, currency: "KRW" };
  const earlier = { ...later, timestamp: "2026-10-22T01:01:00Z", closePrice: 101 };
  assert.deepEqual(parseMinuteCandles([later, earlier]), [
    { time: "2026-10-22T01:01:00.000Z", open: 100, high: 103, low: 99, close: 101, volume: 10 },
    { time: "2026-10-22T01:02:00.000Z", open: 100, high: 103, low: 99, close: 102, volume: 10 },
  ]);
  assert.throws(() => parseMinuteCandles([later, later]), /duplicate/);
  assert.throws(() => parseMinuteCandles([{ ...later, highPrice: 98 }]), /invalid/);
  assert.throws(() => parseMinuteCandles(Array.from({ length: 201 }, (_, index) => ({ ...later, timestamp: `2026-10-22T01:${String(index).padStart(2, "0")}:00Z` }))), /limit/);
});

test("event identity is deterministic but records a new state transition", () => {
  const base = { watchId: "2026-10-22-005930", symbol: "005930", reportBusinessDate: "2026-10-22", stockName: "삼성전자", reportCount: 2,
    ruleVersion: "horizontal-m1-v1", kind: "resistance-breakout", direction: "down", basisStartTime: "2026-10-22T01:00:00.000Z" };
  const first = chartAlertEventId({ ...base, status: "forming" });
  assert.equal(first, chartAlertEventId({ ...base, status: "forming" }));
  assert.notEqual(first, chartAlertEventId({ ...base, status: "observed-crossing" }));
  assert.match(first, /^[a-f0-9]{64}$/);
});
