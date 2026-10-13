import assert from "node:assert/strict";
import test from "node:test";

import {
  dailyReportOpinionLabel,
  defaultIncludeSingleReportStocks,
  parseDailyStockLimit,
} from "../src/domain/daily.ts";

test("stock summary includes single-report rows by default when no multi-report rows exist", () => {
  assert.equal(defaultIncludeSingleReportStocks([{ mention_count: 1 }], false), true);
  assert.equal(defaultIncludeSingleReportStocks([{ mention_count: 1 }, { mention_count: 2 }], false), false);
  assert.equal(defaultIncludeSingleReportStocks([{ mention_count: 2 }], true), true);
});

test("stock summary row limit stays in the legacy six-row increment range", () => {
  assert.equal(parseDailyStockLimit(null), 6);
  assert.equal(parseDailyStockLimit("invalid"), 6);
  assert.equal(parseDailyStockLimit("1"), 6);
  assert.equal(parseDailyStockLimit("12"), 12);
  assert.equal(parseDailyStockLimit("999"), 100);
});

test("stored report opinion keeps the legacy hold and missing labels", () => {
  assert.equal(dailyReportOpinionLabel("hold"), "리포트 표기: 중립");
  assert.equal(dailyReportOpinionLabel("neutral"), "리포트 표기: 중립");
  assert.equal(dailyReportOpinionLabel("N/A"), "의견 없음");
  assert.equal(dailyReportOpinionLabel(""), "-");
});
