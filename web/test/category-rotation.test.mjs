import assert from "node:assert/strict";
import test from "node:test";

import * as domain from "../src/domain/category-rotation.ts";

test("category DTOs preserve selected-date stocks and separately dated trend rows", () => {
  const detail = {
    now: "2026-10-11T09:00:00+09:00", timezone: "Asia/Seoul", surface: "web-view", read_only: true,
    business_date: "2026-10-08", category_type: "sector", category_label: "업종", category_name: "반도체",
    category_key: "반도체", display_name: "반도체", public_category_id: "sector|반도체|2026-10-07",
    category_display_name: "반도체", stock_count: 1, report_count: 2, mapping_source: "dated_snapshot",
    snapshot_date: "2026-10-07", mapping_notice: "선택 날짜 이하의 가장 가까운 카테고리 스냅샷 기준입니다.",
    stocks: [{ business_date: "2026-10-08", stock_name: "삼성전자", stock_code: "005930", mention_count: 2, broker_display: "증권사 A", target_price_min: 70000, target_price_max: 80000, dominant_opinion: "buy", market_reference: { business_date: "2026-10-08", market: "KOSPI", close_price: 70000, change_percent: 1, volume: 100, turnover: 7000000, fetched_at: "2026-10-08T20:00:00+09:00" } }],
  };
  assert.equal(typeof domain.isCategoryDetailSnapshot, "function");
  assert.equal(domain.isCategoryDetailSnapshot(detail, "2026-10-08", "sector", "반도체"), true);
  assert.equal(domain.isCategoryDetailSnapshot({ ...detail, snapshot_date: "2026-10-09" }, "2026-10-08", "sector", "반도체"), false);
  assert.equal(domain.isCategoryDetailSnapshot({ ...detail, stocks: [{ ...detail.stocks[0], market_reference: { ...detail.stocks[0].market_reference, business_date: "2026-10-09" } }] }, "2026-10-08", "sector", "반도체"), false);

  const trend = { now: detail.now, timezone: detail.timezone, surface: "web-view", read_only: true, category_type: "sector", category_label: "업종", category_name: "반도체", display_name: "반도체", public_category_id: "sector|반도체|trend", category_display_name: "반도체", mapping_policy: "date-aware snapshot when available, latest stored category mapping otherwise", trend: [{ business_date: "2026-10-09", stock_count: 2, report_count: 3 }] };
  assert.equal(domain.isCategoryTrendSnapshot(trend, "sector", "반도체"), true);
  assert.equal(domain.isCategoryTrendSnapshot({ ...trend, live_fetch: true }, "sector", "반도체"), false);
});

test("rotation DTO validates public coordinates and descriptive stored evidence", () => {
  const snapshot = {
    surface: "web-view", read_only: true, business_date: "2026-10-08",
    image: { path: "example/Cycle.jpg", width: 1376, height: 768 },
    notice: "분류 참고이며 확정 판단은 아닙니다.",
    highlights: [{ category_type: "sector", category_label: "업종", display_name: "반도체", public_category_id: "sector|반도체|2026-10-07", rotation_label: "회복", coordinate_display_name: "반도체", mapping_basis: "direct_coordinate", label: "회복", x: 500, y: 400, radius: 20, evidence_label: "리포트 2건 / 1종목", evidence_source: "report_category_rollup", candidate_stocks: [{ stock_code: "005930", stock_name: "삼성전자", mention_count: 2, broker_count_label: "증권사 2곳", market: "KOSPI", close_price: 70000, change_percent: 1, turnover: 7000000, evidence_label: "리포트 2건" }], candidate_etfs: [{ etf_code: "069500", etf_name: "KODEX 200", close_price: 1000, change_percent: 1, turnover: 10000, underlying_index_name: "KOSPI 200", evidence_label: "거래대금 참고" }] }],
  };
  assert.equal(typeof domain.isRotationOverlaySnapshot, "function");
  assert.equal(domain.isRotationOverlaySnapshot(snapshot, "2026-10-08"), true);
  assert.equal(domain.isRotationOverlaySnapshot({ ...snapshot, highlights: [{ ...snapshot.highlights[0], x: 2000 }] }, "2026-10-08"), false);
  assert.equal(domain.isRotationOverlaySnapshot({ ...snapshot, business_date: "2026-10-07" }, "2026-10-08"), false);
});

\n