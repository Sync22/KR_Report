import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "typescript";

const businessDate = "2026-10-08";
const stockCode = "005930";

function detailSnapshot() {
  return {
    now: "2026-10-14T09:00:00+09:00",
    timezone: "Asia/Seoul",
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    stock_code: stockCode,
    stock_name: "삼성전자",
    has_selected_date_report: true,
    report_empty_state: null,
    market_reference: {
      business_date: businessDate,
      market: "KOSPI",
      close_price: 100000,
      change_percent: 1.2,
      volume: 10000,
      turnover: 500000000,
      fetched_at: "2026-10-08T20:00:00+09:00",
    },
    value_context: {
      report_reference_date: businessDate,
      toss_reference_date: businessDate,
      current_price_reference_time: "2026-10-08T20:00:00+09:00",
      current_price_basis: "Toss stored snapshot",
      turnover_reference_date: businessDate,
      investor_flow_reference_date: businessDate,
      news_collection_status: "stored_evidence",
      missing_labels: [],
    },
    target_price_progress: {
      validation_available: true,
      hit_min_horizon_days: 3,
      hit_max_horizon_days: null,
      validation_notice: "stored_horizon",
    },
    target_price_trail: {
      available: true,
      source: "stored_reports",
      live_fetch: false,
      scoring: false,
      recommendation: false,
      business_date: businessDate,
      stock_code: stockCode,
      summary: "최근 저장 목표가 기준",
      current_price: 100000,
      current_target_price: 110000,
      attainment_percent: 90.9,
      notice: "stored_reports",
    },
    target_journey: {
      available: true,
      source: "stored_reports_and_stock_market_daily",
      live_fetch: false,
      scoring: false,
      recommendation: false,
      business_date: businessDate,
      stock_code: stockCode,
      price_basis: "KRX historical window",
      items: [{
        report_date: businessDate,
        broker_name: "NH투자증권",
        target_price_value: 110000,
        target_price_display: "목표가 110,000원",
        revision_direction_label: "유지",
        status: "in_progress",
        hit_date: null,
        hit_trading_days: null,
        current_attainment_percent: 90.9,
        max_attainment_percent: 98.2,
        observed_through: "2026-10-14",
      }],
      notice: "저장 가격 이력 없음",
    },
    related_context: {
      available: true,
      source: "stored_category_rollup",
      etf_source: "manual_mapping_stored_toss_etf_snapshot",
      live_fetch: false,
      scoring: false,
      recommendation: false,
      business_date: businessDate,
      stock_code: stockCode,
      categories: [{
        category_type: "sector",
        category_label: "업종",
        category_display_name: "반도체",
        public_category_id: "sector|반도체|2026-10-07",
        display: "업종 반도체 · 리포트 3건 · 2종목",
        etf_notice: "저장 ETF 없음",
        related_etfs: [{ etf_code: "069500", etf_name: "KODEX 200", evidence_label: "저장 ETF 참고" }],
      }],
      notice: "저장 업종/테마 없음",
    },
    news_observation_detail: {
      source: "stored_news_intelligence_observation",
      read_only: true,
      live_fetch: false,
      available: true,
      display_label: "저장 뉴스 1건",
      reason: "저장 근거 연결",
      connection_label: "종목 직접 매칭",
      connection_reason: "선택 종목에 연결된 저장 뉴스 근거입니다.",
      direct_count: 1,
      caution_count: 0,
      market_context_count: 0,
      krx_reference_status: "exact",
      news_digest: [{
        date: businessDate,
        stock_name: "삼성전자",
        label: "selected-stock-inline-news-sentinel",
        evidence_label: "종목 직접 매칭",
        lineage_label: "독립 확인",
      }],
    },
    recent_volume_days: {
      available: true,
      source: "toss_openapi",
      live_fetch: false,
      business_date: businessDate,
      reference_date: businessDate,
      exact_date_available: true,
      items: [{ business_date: businessDate, close_price: 100000, change_percent: 1.2, volume: 10000, volume_unit: "주" }],
      notice: "저장 거래량 참고",
    },
    investor_flow: {
      available: true,
      source: "toss_openapi",
      data_scope: "stored_toss_close_priority_flow",
      live_fetch: false,
      scoring: false,
      snapshot_date: businessDate,
      notice: "저장 수급 참고",
      rows: [],
    },
    investor_flow_tabs: {
      available: true,
      source: "toss_openapi",
      live_fetch: false,
      business_date: businessDate,
      reference_date: businessDate,
      exact_date_available: true,
      volume_unit: "주",
      retail_foreign_institution: [{
        business_date: businessDate,
        individual: -50,
        foreign: 100,
        institution: -50,
      }],
      notice: "저장 수급 이력",
    },
    reports: [{
      stock_name: "삼성전자",
      stock_code: stockCode,
      title: "업황 회복",
      title_display: "업황 회복",
      broker_name: "NH투자증권",
      published_at: "2026-10-08T09:00:00+09:00",
      target_price_value: 110000,
      target_price_display: "목표가 110,000원",
      opinion_normalized: "buy",
      opinion_display: "리포트 표기: 매수",
      source_url: "https://stock.naver.com/research/company/1",
    }],
  };
}

async function loadSelectedStockPanel() {
  const sourcePath = new URL("../src/components/server/selected-stock-panel.tsx", import.meta.url);
  const source = readFileSync(sourcePath, "utf8");
  let compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  compiled = compiled
    .replace('import "server-only";', "")
    .replaceAll('from "@/domain/daily"', 'from "' + new URL("../src/domain/daily.ts", import.meta.url).href + '"')
    .replaceAll('from "@/domain/stocks"', 'from "' + new URL("../src/domain/stocks.ts", import.meta.url).href + '"')
    .replace(
      'import { getStockDetailSnapshot } from "@/server/stock-detail";',
      'const getStockDetailSnapshot = () => { globalThis.__selectedStockDetailReads += 1; throw new Error("unexpected detail read"); };',
    )
    .replaceAll(
      'from "react/jsx-runtime"',
      'from "' + new URL("../node_modules/react/jsx-runtime.react-server.js", import.meta.url).href + '"',
    );
  const moduleUrl = "data:text/javascript;base64," + Buffer.from(compiled).toString("base64");
  return (await import(moduleUrl)).default;
}

function textFromNode(node) {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textFromNode).join("");
  if (typeof node.type === "function") return textFromNode(node.type(node.props));
  return textFromNode(node.props?.children);
}

test("selected Stock panel renders validated detail context inline without another detail read", async () => {
  globalThis.__selectedStockDetailReads = 0;
  try {
    const SelectedStockPanel = await loadSelectedStockPanel();
    const snapshot = detailSnapshot();
    const element = await SelectedStockPanel({
      date: businessDate,
      selectedStockCode: stockCode,
      allowedStocks: [{ stock_code: stockCode }],
      detailSnapshot: snapshot,
    });
    const markup = textFromNode(element);

    assert.equal(globalThis.__selectedStockDetailReads, 0);
    assert.equal(element.props.id, "selected-stock");
    assert.equal(element.props["aria-labelledby"], "selected-stock-heading");
    for (const label of [
      "저장 리포트 목표가 흐름",
      "저장 업종·테마와 ETF 참고",
      "기간별 수급량",
      "저장 거래량",
      "저장 뉴스 관찰",
      "목표가 · 수급 · 거래량 · 업종/ETF · 뉴스 저장 이력",
      "현재 +90.9%",
      "최대 +98.2%",
      "하단 3거래일",
      "10,000주",
      "100,000원",
      "+1.2%",
      "저장 ETF 참고",
      "KODEX 200",
      "selected-stock-inline-news-sentinel",
    ]) {
      assert.ok(markup.includes(label), "missing inline stock-detail context: " + label);
    }
    assert.match(markup, /2026-10-14/);

    const watchPanel = await SelectedStockPanel({
      date: businessDate,
      selectedStockCode: stockCode,
      allowedStocks: [{ stock_code: stockCode }],
      detailSnapshot: snapshot,
      sectionId: "watch-selected-stock",
    });
    assert.equal(watchPanel.props.id, "watch-selected-stock");
    assert.equal(watchPanel.props["aria-labelledby"], "watch-selected-stock-heading");

    const suppliedEmpty = await SelectedStockPanel({
      date: businessDate,
      selectedStockCode: stockCode,
      allowedStocks: [{ stock_code: stockCode }],
      detailSnapshot: null,
    });
    assert.equal(globalThis.__selectedStockDetailReads, 0);
    assert.match(textFromNode(suppliedEmpty), /저장 상세를 불러오지 못했습니다/);

    const mismatchedSnapshot = await SelectedStockPanel({
      date: businessDate,
      selectedStockCode: stockCode,
      allowedStocks: [{ stock_code: stockCode }],
      detailSnapshot: { ...snapshot, business_date: "2026-10-09" },
    });
    assert.equal(globalThis.__selectedStockDetailReads, 0);
    assert.match(textFromNode(mismatchedSnapshot), /저장 상세를 불러오지 못했습니다/);

    const fallback = await SelectedStockPanel({
      date: businessDate,
      selectedStockCode: stockCode,
      allowedStocks: [{ stock_code: stockCode }],
    });
    assert.equal(globalThis.__selectedStockDetailReads, 1);
    assert.match(textFromNode(fallback), /저장 상세를 불러오지 못했습니다/);
  } finally {
    delete globalThis.__selectedStockDetailReads;
  }
});
