import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { isStockDetailSnapshot } from "../src/domain/stocks.ts";

const businessDate = "2026-10-08";
const stockCode = "005930";

function createPythonFixture(root) {
  const script = String.raw`
import json, sys
from datetime import date, datetime
from pathlib import Path
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    EtfDailySnapshot, NewsIntelligenceRun, Report, ReportLinkedNewsEvidenceRecord,
    KrxStockMetadataSnapshot, StockInvestorFlowDaily, StockMarketDailySnapshot,
)
import stock_monitor.cli as cli

root = Path(sys.argv[1])
business_date = date.fromisoformat(sys.argv[2])
code = sys.argv[3]
config = RuntimeConfig.from_env(root_dir=root)
config.ensure_runtime_dirs()
repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
repository.initialize()

repository.insert_reports([
    Report(stock_name="삼성전자", stock_code=code, title="업황 회복", broker_name="NH투자증권",
           published_at=datetime(2026, 10, 8, 9, 0), business_date=business_date,
           collected_at=datetime(2026, 10, 8, 9, 5), target_price_value=110000,
           opinion_normalized="buy", source_url="https://stock.naver.com/research/company/1",
           source_id="1", identity_key="detail-1"),
    Report(stock_name="삼성전자", stock_code=code, title="목표가와 의견 없음", broker_name="신한투자증권",
           published_at=datetime(2026, 10, 8, 10, 30), business_date=business_date,
           collected_at=datetime(2026, 10, 8, 10, 35), target_price_value=None,
           opinion_normalized="N/A", source_url="https://stock.naver.com/research/company/2",
           source_id="2", identity_key="detail-2"),
    Report(stock_name="삼성전자", stock_code=code, title="이전 목표가", broker_name="NH투자증권",
           published_at=datetime(2026, 10, 7, 9, 0), business_date=date(2026, 10, 7),
           collected_at=datetime(2026, 10, 7, 9, 5), target_price_value=95000,
           opinion_normalized="neutral", source_url="https://stock.naver.com/research/company/3",
           source_id="3", identity_key="detail-3"),
])
repository.upsert_stock_market_daily([
    StockMarketDailySnapshot(business_date=date(2026, 10, 8), stock_code=code, stock_name="삼성전자",
        market="KOSPI", close_price=100000, change_percent=1.2, volume=10000, turnover=500000000,
        fetched_at=datetime(2026, 10, 8, 20, 0), source="toss_openapi"),
    StockMarketDailySnapshot(business_date=date(2026, 10, 8), stock_code=code, stock_name="삼성전자",
        market="KOSPI", close_price=101000, change_percent=2.2, high_price=112000, volume=11000,
        turnover=550000000, fetched_at=datetime(2026, 10, 8, 20, 1), source="krx"),
    StockMarketDailySnapshot(business_date=date(2026, 10, 9), stock_code=code, stock_name="삼성전자",
        market="KOSPI", close_price=108000, change_percent=6.9, high_price=111000, volume=12000,
        turnover=600000000, fetched_at=datetime(2026, 10, 9, 20, 0), source="krx"),
    StockMarketDailySnapshot(business_date=date(2026, 10, 7), stock_code=code, stock_name="삼성전자",
        market="KOSPI", close_price=99000, change_percent=-0.5, volume=9000, turnover=450000000,
        fetched_at=datetime(2026, 10, 7, 20, 0), source="toss_openapi"),
])
repository.upsert_stock_investor_flow_daily([
    StockInvestorFlowDaily(business_date=date(2026, 10, 8), stock_code=code, stock_name="삼성전자",
        market="STK", investor_type="개인", net_buy_volume=-50, net_buy_amount=-100,
        volume_unit="주", amount_unit="원", fetched_at=datetime(2026, 10, 8, 20, 0), source="toss_openapi"),
    StockInvestorFlowDaily(business_date=date(2026, 10, 8), stock_code=code, stock_name="삼성전자",
        market="STK", investor_type="외국인", net_buy_volume=100, net_buy_amount=200,
        volume_unit="주", amount_unit="원", fetched_at=datetime(2026, 10, 8, 20, 0), source="toss_openapi"),
    StockInvestorFlowDaily(business_date=date(2026, 10, 7), stock_code=code, stock_name="삼성전자",
        market="STK", investor_type="개인", net_buy_volume=10, net_buy_amount=20,
        volume_unit="주", amount_unit="원", fetched_at=datetime(2026, 10, 7, 20, 0), source="toss_openapi"),
])
repository.upsert_krx_stock_metadata([
    KrxStockMetadataSnapshot(business_date=date(2026, 10, 7), standard_code="BEFORE", stock_code="000660",
        stock_name="기준일 이전 이름", market="KOSPI", fetched_at=datetime(2026, 10, 7, 18, 0)),
    KrxStockMetadataSnapshot(business_date=date(2026, 10, 9), standard_code="AFTER", stock_code="000660",
        stock_name="선택일 이후 이름", market="KOSPI", fetched_at=datetime(2026, 10, 9, 18, 0)),
])
repository.upsert_etf_daily_snapshots([
    EtfDailySnapshot(business_date=business_date, etf_code="069500", etf_name="Toss KODEX 200",
        fetched_at=datetime(2026, 10, 8, 20, 0), source="toss_openapi", close_price=40000,
        change_percent=1.1, turnover=500000000, underlying_index_name="KOSPI"),
    EtfDailySnapshot(business_date=business_date, etf_code="069500", etf_name="KRX KODEX 200",
        fetched_at=datetime(2026, 10, 8, 20, 1), source="krx", close_price=99999,
        change_percent=9.9, turnover=9999999999, underlying_index_name="KRX KOSPI"),
])
repository.save_news_intelligence_observation(
    NewsIntelligenceRun(run_id="detail-news-run", target_date=business_date, stock_name="삼성전자", stock_code=code,
        aliases=(), source_mode="preview", page_limit=1, full_day_complete=False, live_fetch=True,
        parsed_count=3, deduped_count=3, matched_count=3, operator_summary_snapshot="operator only",
        warnings=(), created_at=datetime(2026, 10, 8, 10, 0)),
    [
        ReportLinkedNewsEvidenceRecord(run_id="detail-news-run", evidence_key="detail-news-direct", target_date=business_date,
            stock_code=code, stock_name="삼성전자", related_report_count=1, related_report_source_ids=("1",),
            daily_summary_presence=True, candidate_priority_presence=True, candidate_observation_priority="priority",
            krx_reference_presence=True, krx_reference_date=business_date, krx_turnover=1000000,
            investor_flow_presence=True, source_lane="mainnews", title="삼성전자 AI 공급 계약 확대",
            summary="삼성전자가 AI 공급 계약을 확대했다.", source="한국경제", published_at=datetime(2026, 10, 8, 9, 10),
            url="https://news.example.test/direct", matched_alias="삼성전자", match_reason="stock_name",
            match_scope="title", relevance="direct", relevance_reason="종목명이 제목에 등장합니다.",
            sentiment="Positive", sentiment_score=82, event_types=("Contract",), stock_impact="Strong Positive",
            impact_explanation="stored evidence", evidence_case="direct_positive", operator_recommendation="operator_only",
            recommendation_reason="operator only", operator_summary_snapshot="operator only",
            created_at=datetime(2026, 10, 8, 10, 0), canonical_url="https://news.example.test/direct",
            lineage_type="independent", lineage_reason="verified"),
        ReportLinkedNewsEvidenceRecord(run_id="detail-news-run", evidence_key="detail-news-market", target_date=business_date,
            stock_code=code, stock_name="삼성전자", related_report_count=1, related_report_source_ids=("1",),
            daily_summary_presence=True, candidate_priority_presence=True, candidate_observation_priority="priority",
            krx_reference_presence=True, krx_reference_date=date(2026, 10, 7), krx_turnover=900000,
            investor_flow_presence=True, source_lane="mainnews", title="삼성전자 반도체 시장 변동성 주의",
            summary="시장 변동성 주의가 이어졌다.", source="연합뉴스", published_at=datetime(2026, 10, 8, 9, 20),
            url="https://news.example.test/market", matched_alias="삼성전자", match_reason="stock_name",
            match_scope="title", relevance="market_context", relevance_reason="시장 맥락",
            sentiment="Caution", sentiment_score=20, event_types=("Risk/Caution",), stock_impact="Negative",
            impact_explanation="stored evidence", evidence_case="market_caution", operator_recommendation="operator_only",
            recommendation_reason="operator only", operator_summary_snapshot="operator only",
            created_at=datetime(2026, 10, 8, 10, 1), canonical_url="https://news.example.test/market",
            lineage_type="independent", lineage_reason="verified"),
        ReportLinkedNewsEvidenceRecord(run_id="detail-news-run", evidence_key="detail-news-risk-only", target_date=business_date,
            stock_code=code, stock_name="삼성전자", related_report_count=1, related_report_source_ids=("1",),
            daily_summary_presence=True, candidate_priority_presence=True, candidate_observation_priority="priority",
            krx_reference_presence=False, krx_reference_date=None, krx_turnover=None,
            investor_flow_presence=False, source_lane="mainnews", title="삼성전자 공급망 주의 문구",
            summary="확인할 사항이 남아 있다.", source="연합뉴스", published_at=datetime(2026, 10, 8, 9, 25),
            url="https://news.example.test/risk-only", matched_alias="삼성전자", match_reason="stock_name",
            match_scope="title", relevance="indirect", relevance_reason="보조 매칭",
            sentiment="Neutral", sentiment_score=0, event_types=("Risk/Caution",), stock_impact="Neutral",
            impact_explanation="stored evidence", evidence_case="risk_only", operator_recommendation="operator_only",
            recommendation_reason="operator only", operator_summary_snapshot="operator only",
            created_at=datetime(2026, 10, 8, 10, 2), canonical_url="https://news.example.test/risk-only",
            lineage_type="independent", lineage_reason="verified"),
    ],
)
with repository.connect() as connection:
    connection.execute(
        "INSERT INTO daily_stock_summaries (business_date, stock_name, stock_code, mention_count, broker_display, target_price_min, target_price_max, dominant_opinion, generated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (business_date.isoformat(), "삼성전자", code, 2, "NH투자증권, 신한투자증권", 110000, 110000, "buy", "2026-10-08T20:00:00"),
    )
    connection.commit()
snapshot = cli.build_web_view_stock_detail_snapshot(
    config, repository, business_date=business_date, stock_code=code,
    now=datetime(2026, 10, 8, 16, 0),
)
empty_snapshot = cli.build_web_view_stock_detail_snapshot(
    config, repository, business_date=business_date, stock_code="000660", now=datetime(2026, 10, 8, 16, 0),
)
print(json.dumps({"database_path": str(config.db_path.resolve()), "snapshot": snapshot, "empty_snapshot": empty_snapshot}, ensure_ascii=False, separators=(",", ":")))
`;
  const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
  const env = { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8", STOCK_MONITOR_TIMEZONE: "Asia/Seoul" };
  delete env.STOCK_MONITOR_DB_PATH;
  const result = spawnSync("python", ["-c", script, root, businessDate, stockCode], {
    cwd: projectRoot,
    env,
    encoding: "utf8",
    timeout: 30000,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message || "Python stock detail fixture failed");
  return JSON.parse(result.stdout);
}

test("stock detail reader matches the Python public DTO using exact Toss and historical KRX rows", async () => {
  const root = mkdtempSync(join(tmpdir(), "stock-monitor-stock-detail-"));
  const previousDatabasePath = process.env.STOCK_MONITOR_DB_PATH;
  const previousTimezone = process.env.STOCK_MONITOR_TIMEZONE;
  const previousOverlayPath = process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH;
  try {
    const overlayPath = join(root, "rotation_overlay_coordinates.json");
    writeFileSync(overlayPath, "{}");
    writeFileSync(join(root, "rotation_etf_candidates.json"), JSON.stringify({
      mappings: [{ category_type: "sector", category_display_name: "N/A", etf_codes: ["069500"] }],
    }));
    process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH = overlayPath;
    const { database_path: databasePath, snapshot: pythonSnapshot, empty_snapshot: pythonEmptySnapshot } = createPythonFixture(root);
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    const beforeRead = statSync(databasePath);
    const service = await import("../src/server/stock-detail.ts").catch(() => null);
    assert.equal(typeof service?.getStockDetailSnapshot, "function", "direct stock detail SQLite reader exists");
    const snapshot = service.getStockDetailSnapshot(businessDate, stockCode);
    const emptySnapshot = service.getStockDetailSnapshot(businessDate, "000660");
    const afterRead = statSync(databasePath);
    assert.equal(afterRead.size, beforeRead.size);
    assert.equal(afterRead.mtimeMs, beforeRead.mtimeMs);
    assert.equal(isStockDetailSnapshot(snapshot, businessDate, stockCode), true);
    const { now: _pythonNow, ...expected } = pythonSnapshot;
    const { now: _nextNow, ...actual } = snapshot;
    assert.deepEqual(actual, expected);
    const { now: _pythonEmptyNow, ...expectedEmpty } = pythonEmptySnapshot;
    const { now: _nextEmptyNow, ...actualEmpty } = emptySnapshot;
    assert.deepEqual(actualEmpty, expectedEmpty);
    assert.equal(snapshot.market_reference.close_price, 100000);
    assert.equal(snapshot.reports.find((report) => report.broker_name === "신한투자증권")?.target_price_display, "목표가 없음");
    assert.equal(snapshot.reports.find((report) => report.broker_name === "신한투자증권")?.opinion_display, "의견 없음");
    assert.equal(snapshot.target_journey.items[0].status, "hit");
    assert.equal(snapshot.investor_flow_tabs.reference_date, businessDate);
    assert.equal(snapshot.news_observation_detail.krx_reference_status, "exact");
    assert.equal(snapshot.news_observation_detail.direct_count, 1);
    assert.equal(snapshot.news_observation_detail.caution_count, 2);
    assert.equal(snapshot.news_observation_detail.market_context_count, 1);
    assert.equal(snapshot.news_observation_detail.news_digest[0].evidence_label, "종목 직접 매칭");
    assert.equal(snapshot.related_context.etf_source, "manual_mapping_stored_toss_etf_snapshot");
    assert.equal(snapshot.related_context.categories[0].related_etfs[0].etf_name, "Toss KODEX 200");
    const publicJson = JSON.stringify(snapshot);
    for (const key of ["operator_recommendation", "operator_summary_snapshot", "sentiment_score", "stock_impact"]) {
      assert.equal(publicJson.includes(key), false);
    }
    assert.equal(emptySnapshot.market_reference, null);
    assert.equal(emptySnapshot.stock_name, "기준일 이전 이름");
    assert.deepEqual(emptySnapshot.value_context.missing_labels, ["report", "toss", "current_price", "turnover", "investor_flow"]);
    assert.equal(emptySnapshot.value_context.news_collection_status, "next_check_needed");
  } finally {
    if (previousDatabasePath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = previousDatabasePath;
    if (previousTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = previousTimezone;
    if (previousOverlayPath === undefined) delete process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH;
    else process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH = previousOverlayPath;
    rmSync(root, { recursive: true, force: true });
  }
});
