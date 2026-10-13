import assert from "node:assert/strict";
import test from "node:test";

import {
  isMainTop2IndicatorsSnapshot,
  isIntradayMarketTopSnapshot,
  isPriorityQuoteSnapshot,
  isPriorityCurrentQuotesSnapshot,
  isTossMarketContextSnapshot,
  indicatorHistoryStatusLabel,
  indicatorPriceChartBars,
  priceThresholdState,
} from "../src/domain/main-top2.ts";

function indicatorSnapshot() {
  return {
    schemaVersion: 1, code: "005930", symbol: "005930.KS", market: "KOSPI", timeframe: "D",
    requestedAsOf: "2026-10-08", barAsOf: "2026-10-08", source: "Toss OpenAPI · 조정 일봉",
    sourceFetchedAt: "2026-10-08T16:00:00+09:00", sourceDate: "2026-10-08", barStatus: "unknown",
    confirmedPolicy: "Toss daily candle finality is unknown.", cacheHit: false, cacheAge: 0, stale: false,
    lastSuccessAt: "2026-10-08T16:00:00+09:00", dataRevision: "revision-1", calculationVersion: "stock-monitor-indicator-v2",
    sourceCalculationVersion: "toss-adjusted-daily-v1", servedAt: "2026-10-08T16:00:01+09:00",
    calculationBasis: { ohlcv: "adjusted", cutoff: "2026-10-08", candlePrecision: "provider", sourceSeries: "daily" },
    price: { open: 70000, high: 71000, low: 69000, close: 70500, volume: 1000 },
    indicators: {
      movingAverages: { sma20: 70000, sma60: 69000, sma120: 68000, sma200: 67000, ema20: 70000, ema60: 69000, ema120: 68000, ema200: 67000, wma20: 70000, wma60: 69000, wma120: 68000, wma200: 67000, status: "ready", calculationVersion: "technical-v4", emaSeedPolicy: "sma-period", wmaWeights: "linear" },
      bollinger20: { middle: 70000, upper: 72000, lower: 68000, status: "ready", period: 20, multiplier: 2, stddev: "population", calculationVersion: "technical-v4" },
      donchian20: { upper: 72000, middle: 70000, lower: 68000, status: "ready", period: 20, includeCurrent: true, calculationVersion: "technical-v4" },
      rsi14: { value: 55, status: "ready", provisional: null, method: "wilder", seedPolicy: "sma" },
      atr14: { value: 1000, status: "ready", provisional: null, method: "wilder", seedPolicy: "sma" },
      volume: { barVolume: 1000, ratio20: 1.3, status: "ready", period: 20, includeCurrent: true },
      macd129: { macd: 3, signal: 2, histogram: 1, status: "ready", fast: 12, slow: 26, signalPeriod: 9, seedPolicy: "sma", calculationVersion: "technical-v4" },
      obv: { value: 1000, delta5: 100, seedTime: "2026-10-01", status: "ready", delta5Status: "ready", seedPolicy: "first-bar-zero-stop-on-gap", calculationVersion: "technical-v4" },
      volumeProfile12: { version: "vp-1", method: "HLC3", from: "2026-09-01", to: "2026-10-08", count: 12, total: 12000, binCount: 12, bins: Array.from({ length: 12 }, (_, i) => ({ low: 60000 + i, high: 60001 + i, volume: 1000, share: 1 / 12, peak: i === 0 })), status: "ready" },
    },
    structures: [],
    structureStatus: { horizontal: "ready", flag: "paused", triangle: "insufficient-data" },
  };
}

function mainPayload() {
  const snapshot = indicatorSnapshot();
  return {
    surface: "web-view-priority-indicators", read_only: true, configured: true, live_fetch: true,
    source: "toss-openapi-adjusted-daily", adjusted: true, page_size: 200, max_pages: 4,
    writes_stock_monitor_db: false, sends_telegram: false, registers_scheduler: false, affects_ordering: false,
    business_date: "2026-10-08", derived_from: "web_view_candidate_evidence_top_2",
    items: [{
      stock_code: "005930", stock_name: "삼성전자", market: "KOSPI", market_source: "selected_date_toss_market_reference",
      market_source_date: "2026-10-08", available: true, requested_as_of: "2026-10-08", candle_count: 1, pages_fetched: 1,
      history_status: "complete", snapshot,
      chart: { bars: [{ time: "2026-10-08", open: 70000, high: 71000, low: 69000, close: 70500, volume: 1000, sma20: 70000, sma60: 69000, sma120: 68000, sma200: 67000, rsi14: 55, macd: 3, macdSignal: 2, macdHistogram: 1, obv: 1000, atr14: 1000 }] },
      price_conditions: { price_condition_state: "above_prior_20_bar_high", reference_bar_date: "2026-10-08", reference_close: 70500, prior_20_bar_high: 70000, prior_10_bar_low: 65000 },
      indicator_confirmation: { directional_alignment_state: "up_aligned", rsi_state: "up", macd_state: "up", moving_average_state: "up", sma_state: "up", ema_state: "up", wma_state: "up", bollinger_state: "up", donchian_state: "up", obv_state: "up", volume_confirmation_state: "confirmed", volume_ratio20: 1.3, atr14_value: 1000, atr14_percent_of_close: 1.4, volume_profile_state: "above_peak_volume_bins", peak_volume_bins: [{ low: 60000, high: 61000 }] },
      condition_status: "진입 조건 충족", condition_explanation: "사용자 정의 조건을 확인합니다.",
    }],
  };
}

test("Main Top2 validator accepts the selected cohort and exact schema-v1 allowlist", () => {
  const payload = mainPayload();
  assert.equal(isMainTop2IndicatorsSnapshot(payload, "2026-10-08", ["005930"]), true);
  assert.equal(isMainTop2IndicatorsSnapshot(payload, "2026-10-08", ["000660"]), false);
  assert.equal(isMainTop2IndicatorsSnapshot({ ...payload, affects_ordering: true }, "2026-10-08", ["005930"]), false);
  assert.equal(isMainTop2IndicatorsSnapshot({ ...payload, items: [{ ...payload.items[0], snapshot: { ...payload.items[0].snapshot, confidence: 0.9 } }] }, "2026-10-08", ["005930"]), false);
  assert.equal(isMainTop2IndicatorsSnapshot({ ...payload, items: [{ ...payload.items[0], snapshot: { ...payload.items[0].snapshot, barAsOf: "2026-10-09" } }] }, "2026-10-08", ["005930"]), false);
  const missingVolume = mainPayload();
  missingVolume.items[0].chart.bars[0].volume = null;
  assert.equal(isMainTop2IndicatorsSnapshot(missingVolume, "2026-10-08", ["005930"]), false);
});

test("bounded quote and market DTOs remain tied to server-selected symbols and dates", () => {
  const quotes = {
    surface: "web-view-toss-priority-quotes", read_only: true, configured: true, live_fetch: true,
    writes_db: false, sends_telegram: false, registers_scheduler: false, affects_ordering: false,
    priority_date: "2026-10-08", symbols: ["005930"], quotes: [{ symbol: "005930", lastPrice: 70500 }],
    investor_trading: { reference_date: "2026-10-08", available: true, items: [{ symbol: "005930", business_date: "2026-10-08", updated_at: "2026-10-08T10:00:00+09:00", foreigner_net_buy_volume: 100, institution_net_buy_volume: -10 }] },
  };
  assert.equal(isPriorityQuoteSnapshot(quotes, "2026-10-08", ["005930"]), true);
  assert.equal(isPriorityQuoteSnapshot({ ...quotes, symbols: ["999999"] }, "2026-10-08", ["005930"]), false);
  const naver = { surface: "web-view-priority-current-quotes", read_only: true, live_fetch: true, writes_db: false, sends_telegram: false, registers_scheduler: false, affects_ordering: false, priority_date: "2026-10-08", items: [{ stock_code: "005930", current_price: 70500, change_percent: 1, trade_amount: 1000 }] };
  assert.equal(isPriorityCurrentQuotesSnapshot(naver, "2026-10-08", ["005930"]), true);
  const market = { surface: "toss-market-context", read_only: true, reference_date: "2026-10-08", writes_db: false, sends_telegram: false, registers_scheduler: false, affects_ordering: false, rankings: [], market_prices: [], priority_overlap_symbols: [], investor_flow: {} };
  assert.equal(isTossMarketContextSnapshot(market, "2026-10-08"), true);
  assert.equal(isTossMarketContextSnapshot({ ...market, surface: "web-view-toss-market-context" }, "2026-10-08"), false);
});

test("intraday market-top overlay keeps its Naver source and does not change candidate ordering", () => {
  const payload = {
    surface: "web-view", read_only: true, business_date: "2026-10-08",
    market_commentary: {
      surface: "market-commentary-practice", read_only: true, live_fetch: true, business_date: "2026-10-08",
      same_day_report_status: { business_date: "2026-10-08", can_overlap_intraday_market_top: true, reason: "리포트 종목 기준으로 겹침을 확인합니다." },
      intraday_market_top_reference: {
        source: "naver_price_top", live_fetch: true, writes_snapshot_tables: false, markets: ["KOSPI", "KOSDAQ"],
        limit: 100, page_size: 20, checked_at: "2026-10-08T10:00:00+09:00", calls: 2, errors: [], empty_reason: null,
        items: [{ source: "naver_price_top", market: "KOSPI", rank: 1, stock_name: "삼성전자", stock_code: "005930", mention_count: 2, current_price: 70000, change_price: 1000, change_percent: 1.2, trade_amount: 1000000, trade_volume: 100, market_status: "OPEN", trade_time: "2026-10-08T10:00:00+09:00", checked_at: "2026-10-08T10:00:00+09:00", stock_end_type: "stock" }],
      },
      intraday_quote_reference: {
        source: "naver_quote", live_fetch: true, writes_snapshot_tables: false, limit: 1, delay_seconds: 0, errors: [],
        items: [{ stock_name: "삼성전자", stock_code: "005930", mention_count: 2, current_price: 70000, prev_close_price: 69000, change_price: 1000, change_percent: 1.2, trade_amount: 1000000, trade_volume: 100, market_status: "OPEN", trade_time: "2026-10-08T10:00:00+09:00", resolution_source: "summary_stock_code" }],
      },
      boundary: { public_numeric_score: false, trading_recommendation: false, telegram_send: false },
    },
  };
  assert.equal(isIntradayMarketTopSnapshot(payload, "2026-10-08", ["005930"]), true);
  assert.equal(isIntradayMarketTopSnapshot({ ...payload, business_date: "2026-10-07" }, "2026-10-08", ["005930"]), false);
  assert.equal(isIntradayMarketTopSnapshot({ ...payload, market_commentary: { ...payload.market_commentary, same_day_report_status: { ...payload.market_commentary.same_day_report_status, business_date: "2026-10-07" } } }, "2026-10-08", ["005930"]), false);
  assert.equal(isIntradayMarketTopSnapshot({ ...payload, market_commentary: { ...payload.market_commentary, intraday_quote_reference: { ...payload.market_commentary.intraday_quote_reference, items: [{ ...payload.market_commentary.intraday_quote_reference.items[0], stock_code: "000660" }] } } }, "2026-10-08", ["005930"]), false);
  assert.equal(isIntradayMarketTopSnapshot({ ...payload, market_commentary: { ...payload.market_commentary, boundary: { ...payload.market_commentary.boundary, trading_recommendation: true } } }, "2026-10-08", ["005930"]), false);
});

test("price threshold states use strict thresholds and report missing values", () => {
  assert.equal(priceThresholdState(101, 100, "above"), "reached");
  assert.equal(priceThresholdState(100, 100, "above"), "missed");
  assert.equal(priceThresholdState(99, 100, "above"), "missed");
  assert.equal(priceThresholdState(99, 100, "below"), "reached");
  assert.equal(priceThresholdState(100, 100, "below"), "missed");
  assert.equal(priceThresholdState(null, 100, "below"), "insufficient_data");
});

test("price chart input keeps valid OHLC candles and the selected date range", () => {
  const bars = [
    { time: "2026-10-05", open: 10, high: 12, low: 9, close: 11, volume: 4, sma20: 10 },
    { time: "2026-10-06", open: 11, high: 13, low: 10, close: 12, volume: 5, sma20: 11 },
    { time: "2026-10-07", open: 12, high: 10, low: 11, close: 12, volume: 6, sma20: 12 },
    { time: "2026-10-08", open: 12, high: 14, low: 11, close: 13, volume: 7, sma20: 12 },
  ];
  assert.deepEqual(indicatorPriceChartBars(bars, 2).map((bar) => bar.time), ["2026-10-06", "2026-10-08"]);
  assert.deepEqual(indicatorPriceChartBars([], 200), []);
  assert.deepEqual(indicatorPriceChartBars([{ time: "2026-10-08", open: 10, high: 12, low: 9, close: 11, volume: null }], 200), []);
});

test("indicator history status keeps cursor and page-limit gaps explicit", () => {
  assert.equal(indicatorHistoryStatusLabel("complete"), "이력 종료");
  assert.equal(indicatorHistoryStatusLabel("cursor_not_provided"), "추가 이력 cursor 미제공");
  assert.equal(indicatorHistoryStatusLabel("page_limit_reached"), "800봉 요청 상한");
  assert.equal(indicatorHistoryStatusLabel("unknown"), "이력 상태 미확인");
});
