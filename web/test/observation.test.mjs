import assert from "node:assert/strict";
import test from "node:test";

import * as domain from "../src/domain/observation.ts";

test("observation summary keeps stored, selected-date facts and rejects recommendation changes", () => {
  const summary = {
    source: "stored_report_toss_observation_summary", read_only: true, live_fetch: false, scoring: false, recommendation: false,
    business_date: "2026-10-08", notice: "저장 참고",
    market_mood: { label: "시장 분위기", report_count: 3, stock_count: 2, multi_report_stock_count: 1, display: "리포트 3건", lines: ["리포트 3건"], observation_line: "반복 언급 1종목" },
    report_concentration: { label: "리포트 집중", available: true, items: [{ stock_name: "종목", stock_code: "005930", mention_count: 2, broker_count: 1, broker_display: "A", target_price_display: "자료 없음", display: "종목 / 리포트 2건", report_intensity: { available: false }, target_price_revision: { available: false } }] },
    flow_reference: { label: "수급 참고", available: false, items: [] },
    price_volume_reference: { label: "가격 거래량 참고", available: false, items: [] },
    sector_breadth: { label: "시장 분위기", available: false, sectors: [], themes: [] },
  };
  assert.equal(typeof domain.isObservationSummarySnapshot, "function");
  assert.equal(domain.isObservationSummarySnapshot(summary, "2026-10-08"), true);
  assert.equal(domain.isObservationSummarySnapshot({ ...summary, recommendation: true }, "2026-10-08"), false);
  assert.equal(domain.isObservationSummarySnapshot({ ...summary, business_date: "2026-10-07" }, "2026-10-08"), false);
});

test("backtest DTO retains dated historical reactions and explicit non-scoring flags", () => {
  const backtest = {
    now: "2026-10-11T09:00:00+09:00", timezone: "Asia/Seoul", surface: "web-view", read_only: true,
    business_date: "2026-10-08", available: true, data_scope: "stored_report_krx_backtest_observation",
    live_fetch: false, scoring: false, recommendation: false, mention_threshold: 2, horizons: [1, 5, 10, 20], notice: "과거 복기",
    rows: [{ business_date: "2026-10-08", stock_code: "005930", stock_name: "삼성전자", report_summary: { report_count: 2, broker_count: 1, broker_display: "A", target_price_min: 70000, target_price_max: 80000, dominant_opinion: "buy" }, base_market: null,
      reaction_windows: [1, 5, 10, 20].map((days) => ({ horizon_days: days, available: days === 1, horizon_date: days === 1 ? "2026-10-09" : null, base_close_price: 70000, horizon_close_price: days === 1 ? 71000 : null, close_return_percent: days === 1 ? 1.43 : null, horizon_volume: null, horizon_turnover: null, unavailable_reason: days === 1 ? null : "future_window_incomplete" })),
      target_observation: { available: false, gap_available: false, progress_available: false, baseline_date: null, baseline_price: null, current_date: null, current_price: null, target_price_min: null, target_price_max: null, target_gap_min_percent: null, target_gap_max_percent: null, progress_to_min_percent: null, progress_to_max_percent: null, progress_caution: false, progress_notice: null, validation_available: false, validation_window_days: null, max_progress_to_min_percent: null, max_progress_to_max_percent: null, hit_min_horizon_days: null, hit_max_horizon_days: null, validation_notice: null, unavailable_reason: "missing_base_close_price" },
      stock_flow_observation: { available: false, individual_net_buy_volume: null, foreign_net_buy_volume: null, institution_net_buy_volume: null, individual_net_buy_amount: null, foreign_net_buy_amount: null, institution_net_buy_amount: null, investor_types: [] },
      net_buy_top_observation: { available: false, foreign_top_rank: null, market: null, net_buy_volume: null, net_buy_amount: null }, evidence_notes: ["리포트 2건"] }],
  };
  assert.equal(domain.isBacktestObservationSnapshot(backtest, "2026-10-08"), true);
  assert.equal(domain.isBacktestObservationSnapshot({ ...backtest, scoring: true }, "2026-10-08"), false);
  assert.equal(domain.isBacktestObservationSnapshot({ ...backtest, rows: [{ ...backtest.rows[0], reaction_windows: [] }] }, "2026-10-08"), false);
});
