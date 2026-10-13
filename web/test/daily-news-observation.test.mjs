import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

const pythonFixture = String.raw`
import json
import sys
from datetime import date, datetime
from pathlib import Path

from stock_monitor.cli import _build_web_view_news_observation_summary
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import NewsIntelligenceRun, ReportLinkedNewsEvidenceRecord

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
config.ensure_runtime_dirs()
repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
repository.initialize()
business_date = date(2026, 5, 8)

def run(run_id, stock_code, stock_name, created_at, matched_count):
    return NewsIntelligenceRun(
        run_id=run_id,
        target_date=business_date,
        stock_name=stock_name,
        stock_code=stock_code,
        aliases=(stock_name,),
        source_mode="naver_5_lane_preview",
        page_limit=5,
        full_day_complete=False,
        live_fetch=True,
        parsed_count=8,
        deduped_count=6,
        matched_count=matched_count,
        operator_summary_snapshot="operator-only news summary",
        warnings=("operator-only warning",),
        created_at=created_at,
    )

def evidence(run_id, evidence_key, stock_code, stock_name, title, *, created_at, relevance="direct", sentiment="Positive", stock_impact="Strong Positive", source_lane="mainnews", lineage_type="independent", krx_reference_date=business_date, published_at=datetime(2026, 5, 8, 9, 0), canonical_url=None, candidate_priority=True, event_types=("Contract",)):
    url = f"https://news.example.test/{evidence_key}"
    return ReportLinkedNewsEvidenceRecord(
        run_id=run_id,
        evidence_key=evidence_key,
        target_date=business_date,
        stock_code=stock_code,
        stock_name=stock_name,
        related_report_count=2,
        related_report_source_ids=("report-1", "report-2"),
        daily_summary_presence=True,
        candidate_priority_presence=candidate_priority,
        candidate_observation_priority="priority",
        krx_reference_presence=krx_reference_date is not None,
        krx_reference_date=krx_reference_date,
        krx_turnover=1000000 if krx_reference_date else None,
        investor_flow_presence=False,
        source_lane=source_lane,
        title=title,
        summary=f"{stock_name} 저장 뉴스 요약",
        source="테스트 뉴스",
        published_at=published_at,
        url=url,
        matched_alias=stock_name,
        match_reason="stock_name",
        match_scope="title",
        relevance=relevance,
        relevance_reason="종목명이 제목에 등장합니다.",
        sentiment=sentiment,
        sentiment_score=97,
        event_types=event_types,
        stock_impact=stock_impact,
        impact_explanation="operator-only impact explanation",
        evidence_case="operator-only evidence case",
        operator_recommendation="strengthen_report_candidate",
        recommendation_reason="operator-only recommendation reason",
        operator_summary_snapshot="operator-only evidence summary",
        created_at=created_at,
        canonical_url=canonical_url or url,
        lineage_type=lineage_type,
        lineage_reason="fixture lineage detail",
    )

first = run("samsung-run-1", "005930", "삼성전자", datetime(2026, 5, 8, 9, 0), 2)
repository.save_news_intelligence_observation(
    first,
    [
        evidence(first.run_id, "shared-early", "005930", "삼성전자", "삼성전자, 초기 공급 계약 확인", created_at=datetime(2026, 5, 8, 9, 10), canonical_url="https://news.example.test/shared"),
        evidence(first.run_id, "caution", "005930", "삼성전자", "삼성전자, 공급 일정 지연 우려", created_at=datetime(2026, 5, 8, 9, 20), sentiment="Mixed", stock_impact="Negative", krx_reference_date=date(2026, 5, 7), event_types=("Risk/Caution",)),
    ],
)
second = run("samsung-run-2", "005930", "삼성전자", datetime(2026, 5, 8, 10, 0), 2)
repository.save_news_intelligence_observation(
    second,
    [
        evidence(second.run_id, "shared-late", "005930", "삼성전자", "삼성전자, 공급 계약 세부 공개", created_at=datetime(2026, 5, 8, 10, 15), canonical_url="https://news.example.test/shared"),
        evidence(second.run_id, "top2-recap", "005930", "삼성전자", "삼성전자, 리포트 재인용 주의", created_at=datetime(2026, 5, 8, 10, 20), source_lane="top2_search", lineage_type="report_recap", sentiment="Caution", stock_impact="Negative", event_types=("Risk/Caution",)),
    ],
)
later_empty = run("samsung-run-empty", "005930", "삼성전자", datetime(2026, 5, 8, 15, 15), 0)
repository.save_news_intelligence_observation(later_empty, [])

context = run("context-run", "000002", "SK하이닉스", datetime(2026, 5, 8, 8, 0), 1)
repository.save_news_intelligence_observation(
    context,
    [
        evidence(context.run_id, "context", "000002", "SK하이닉스", "반도체 시장 수요 전망", created_at=datetime(2026, 5, 8, 8, 5), relevance="market_context", sentiment="Neutral", stock_impact="Neutral", lineage_type="report_recap", krx_reference_date=date(2026, 5, 6)),
    ],
)

latest = run("newest-unselected", "000003", "NAVER", datetime(2026, 5, 8, 16, 0), 1)
repository.save_news_intelligence_observation(
    latest,
    [evidence(latest.run_id, "unselected", "000003", "NAVER", "NAVER 저장 뉴스", created_at=datetime(2026, 5, 8, 16, 5))],
)

wrong_date = NewsIntelligenceRun(
    run_id="wrong-date-run", target_date=date(2026, 5, 7), stock_name="삼성전자", stock_code="005930",
    aliases=(), source_mode="fixture", page_limit=1, full_day_complete=False, live_fetch=False,
    parsed_count=1, deduped_count=1, matched_count=0, operator_summary_snapshot="ignored",
    warnings=(), created_at=datetime(2026, 5, 7, 20, 0),
)
repository.save_news_intelligence_observation(wrong_date, [])

with repository.read_session():
    print(json.dumps({
        "selected": _build_web_view_news_observation_summary(repository, business_date, limit=2, stock_codes=["000002", "005930"]),
        "default_scope": _build_web_view_news_observation_summary(repository, business_date, limit=1),
        "empty_date": _build_web_view_news_observation_summary(repository, date(2026, 5, 9), stock_codes=["005930"]),
    }, ensure_ascii=False, separators=(",", ":")))
`;

function pythonSnapshot(root) {
  const projectRoot = resolve(process.cwd(), "..");
  const env = { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: resolve(projectRoot, "src") };
  delete env.STOCK_MONITOR_DB_PATH;
  const result = spawnSync("python", ["-c", pythonFixture, root], {
    cwd: projectRoot,
    encoding: "utf8",
    env,
    timeout: 30000,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  return JSON.parse(result.stdout);
}

function containsForbiddenPublicField(value) {
  const forbidden = new Set([
    "sentiment_score",
    "stock_impact",
    "operator_recommendation",
    "recommendation_reason",
    "operator_summary_snapshot",
    "warnings",
    "lineage_reason",
    "impact_explanation",
  ]);
  if (Array.isArray(value)) return value.some(containsForbiddenPublicField);
  if (value && typeof value === "object") {
    return Object.entries(value).some(([key, child]) => forbidden.has(key) || containsForbiddenPublicField(child));
  }
  return false;
}

test("daily news observation matches Python's stored projection using the caller's read-only database", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-daily-news-observation-"));
  const databasePath = resolve(root, "data", "stock_monitor.db");
  try {
    const expected = pythonSnapshot(root);
    const before = await stat(databasePath);
    const observation = await import("../src/server/daily-news-observation.ts").catch(() => ({}));
    assert.equal(typeof observation.buildNewsObservationSummaryFromDatabase, "function");

    const database = new DatabaseSync(databasePath, { readOnly: true });
    let actual;
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      actual = {
        selected: observation.buildNewsObservationSummaryFromDatabase(database, "2026-05-08", {
          limit: 2,
          stockCodes: ["000002", "005930"],
        }),
        default_scope: observation.buildNewsObservationSummaryFromDatabase(database, "2026-05-08", { limit: 1 }),
        empty_date: observation.buildNewsObservationSummaryFromDatabase(database, "2026-05-09", {
          stockCodes: ["005930"],
        }),
      };
      database.exec("COMMIT");
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    } finally {
      database.close();
    }

    assert.deepEqual(actual, expected);
    assert.deepEqual(actual.selected.items.map((item) => item.stock_code), ["000002", "005930"]);
    assert.equal(actual.selected.items[1].direct_count, 3);
    assert.equal(actual.selected.items[1].collection_run_count, 3);
    assert.equal(actual.selected.items[1].latest_collection_status, "no_match");
    assert.equal(actual.selected.items[1].daily_evidence_retained, true);
    assert.equal(actual.selected.items[1].top_title, "삼성전자, 공급 일정 지연 우려");
    assert.equal(actual.selected.evidence_direction, "직접 근거 상충");
    assert.equal(actual.default_scope.items[0].stock_code, "000003");
    assert.equal(actual.empty_date.available, false);
    assert.equal(containsForbiddenPublicField(actual), false);

    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
