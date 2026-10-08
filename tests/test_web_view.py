import gzip
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, time as datetime_time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    CategoryCatalogItem,
    CategoryDailyRollup,
    CategoryMembershipSnapshot,
    EtfDailySnapshot,
    InvestorNetBuyTopDaily,
    KrxStockMetadataSnapshot,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    NewsIntelligenceRun,
    OperationEvent,
    Report,
    ReportLinkedNewsEvidenceRecord,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
    StockMetadata,
    StockThemeMembership,
    TossMarketContextSnapshot,
    TossPriorityQuoteBaseline,
    TossStockUniverseEntry,
)


PUBLIC_FORBIDDEN_KEYS = {
    "safe_settings",
    "recent_admin_audit_logs",
    "admin_audit_log",
    "scheduler_tasks",
    "worker_states",
    "health",
    "db_path",
    "quality_flags",
    "internal_candidate_signals",
    "internal_missing_information",
    "_internal_candidate_signals",
    "_internal_missing_information",
    "_sort_density",
    "_sort_signal",
    "five_business_day_broker_count",
    "previous_broker_count",
    "operation_profile",
    "daily_summary_min_mention_count",
    "daily_summary_require_target_price",
    "notification_default_limit",
    "overall_sentiment",
    "sentiment_score",
    "stock_impact",
    "operator_recommendation",
    "recommendation_support",
}


def _assert_public_safe_payload(payload) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in PUBLIC_FORBIDDEN_KEYS
            _assert_public_safe_payload(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_public_safe_payload(item)


def _assert_candidate_payload_has_no_internal_sort_fields(payload) -> None:
    internal_keys = {
        "sort_value_signal",
        "sort_signal",
        "sort_density",
        "sort_tuple",
        "rank_reference",
        "rank_reference_available",
    }
    if isinstance(payload, dict):
        assert not internal_keys.intersection(payload)
        for value in payload.values():
            _assert_candidate_payload_has_no_internal_sort_fields(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_candidate_payload_has_no_internal_sort_fields(item)


def _web_view_news_run(
    *,
    run_id: str = "news-web-view-run-1",
    target_date: date = date(2026, 6, 2),
    stock_name: str = "삼성전자",
    stock_code: str | None = "005930",
) -> NewsIntelligenceRun:
    return NewsIntelligenceRun(
        run_id=run_id,
        target_date=target_date,
        stock_name=stock_name,
        stock_code=stock_code,
        aliases=("삼전",),
        source_mode="naver_5_lane_preview",
        page_limit=1,
        full_day_complete=False,
        live_fetch=True,
        parsed_count=85,
        deduped_count=70,
        matched_count=2,
        operator_summary_snapshot=f"{stock_name} operator-only news summary",
        warnings=(),
        created_at=datetime(2026, 6, 2, 10, 0, 0),
    )


def _web_view_news_evidence(
    *,
    run_id: str = "news-web-view-run-1",
    evidence_key: str = "news-evidence-1",
    title: str = "삼성전자, AI 반도체 공급 계약 체결",
    stock_code: str | None = "005930",
    stock_name: str = "삼성전자",
    relevance: str = "direct",
    sentiment: str = "Positive",
    stock_impact: str = "Strong Positive",
    operator_recommendation: str = "strengthen_report_candidate",
    target_date: date = date(2026, 6, 2),
    krx_reference_date: date | None = date(2026, 6, 2),
    lineage_type: str = "independent",
) -> ReportLinkedNewsEvidenceRecord:
    return ReportLinkedNewsEvidenceRecord(
        run_id=run_id,
        evidence_key=evidence_key,
        target_date=target_date,
        stock_code=stock_code,
        stock_name=stock_name,
        related_report_count=2,
        related_report_source_ids=("92001", "92002"),
        daily_summary_presence=True,
        candidate_priority_presence=True,
        candidate_observation_priority="priority",
        krx_reference_presence=krx_reference_date is not None,
        krx_reference_date=krx_reference_date,
        krx_turnover=850_000_000_000 if krx_reference_date else None,
        investor_flow_presence=False,
        source_lane="mainnews",
        title=title,
        summary="삼성전자가 AI 반도체 공급 계약을 체결했다.",
        source="한국경제",
        published_at=datetime(2026, 6, 2, 9, 10, 0),
        url=f"https://n.news.naver.com/article/015/{evidence_key}",
        matched_alias="삼성전자",
        match_reason="stock_name",
        match_scope="title",
        relevance=relevance,
        relevance_reason="종목명이 제목에 등장합니다.",
        sentiment=sentiment,
        sentiment_score=82,
        event_types=("Contract",),
        stock_impact=stock_impact,
        impact_explanation="리포트 근거와 뉴스가 같은 방향입니다.",
        evidence_case="report_direct_positive_news",
        operator_recommendation=operator_recommendation,
        recommendation_reason="리포트와 뉴스가 같은 방향입니다.",
        operator_summary_snapshot="operator-only summary",
        created_at=datetime(2026, 6, 2, 10, 0, 0),
        canonical_url=f"https://n.news.naver.com/article/015/{evidence_key}",
        lineage_type=lineage_type,
        lineage_reason="explicit_test_fixture",
    )


def test_web_view_host_guard_allows_loopback_hosts() -> None:
    assert cli_module._is_loopback_web_view_host("127.0.0.1") is True
    assert cli_module._is_loopback_web_view_host("localhost") is True
    assert cli_module._is_loopback_web_view_host("::1") is True


def test_web_view_host_guard_rejects_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="web-view refuses non-loopback host"):
        cli_module._validate_web_view_host("0.0.0.0")


def test_web_view_host_guard_can_be_explicitly_overridden() -> None:
    cli_module._validate_web_view_host("0.0.0.0", allow_non_loopback=True)


def test_candidate_news_badge_keeps_report_recap_matches_visible() -> None:
    report_recap = _web_view_news_evidence(evidence_key="report-recap", lineage_type="report_recap")

    badge = cli_module._web_view_candidate_news_badge(
        [report_recap],
        business_date=date(2026, 6, 2),
    )

    assert badge["direct_count"] == 1
    assert badge["report_recap_count"] == 1
    assert badge["connection_label"] == "리포트 재인용 매칭"
    assert badge["evidence_direction"] == "리포트 재인용 흐름"
    assert badge["news_digest"][0]["evidence_label"] == "종목 직접 매칭"
    assert badge["news_digest"][0]["lineage_label"] == "리포트 재인용"
    assert cli_module._web_view_news_collection_status(badge) == "stored_evidence"


def test_candidate_value_profile_does_not_recast_report_recap_as_independent_direction() -> None:
    badge = cli_module._web_view_candidate_news_badge(
        [_web_view_news_evidence(evidence_key="report-recap-profile", lineage_type="report_recap")],
        business_date=date(2026, 6, 2),
    )

    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={"observation_priority": "확인 후보", "why_notable": ["리포트 집중"]},
        news_badge=badge,
        toss_baseline_reference={"available": False},
        market_reference=None,
        stock_flow_rows=[],
        rank_reference=None,
        current=datetime(2026, 6, 2, 12, 0, 0),
        business_date=date(2026, 6, 2),
    )

    assert profile["observation_priority"] == "확인 후보"
    assert profile["value_label"] == "리포트 재인용 매칭"
    assert profile["evidence_direction"] == "리포트 재인용 흐름"


def test_web_view_news_deduplicates_tracking_variants_by_canonical_url() -> None:
    earlier = _web_view_news_evidence(evidence_key="earlier")
    later = replace(
        _web_view_news_evidence(evidence_key="later"),
        canonical_url=earlier.canonical_url,
        created_at=datetime(2026, 6, 2, 11, 0, 0),
    )

    assert cli_module._web_view_unique_news_evidence_rows([earlier, later]) == [later]


def test_web_view_daily_snapshot_exposes_news_observation_empty_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 6, 2),
        now=datetime(2026, 6, 2, 10, 0, 0),
    )

    summary = snapshot["news_observation_summary"]
    assert summary == {
        "source": "stored_news_intelligence_observation",
        "read_only": True,
        "live_fetch": False,
        "available": False,
        "business_date": "2026-06-02",
        "display_label": "뉴스 근거 수집 전",
        "reason": "저장 뉴스 근거를 아직 수집하지 않았습니다.",
        "connection_note": "저장 뉴스 근거가 수집되면 우선 확인 후보와 연결됩니다.",
        "candidate_overlap_count": 0,
        "candidate_overlap_names": [],
        "direct_count": 0,
        "caution_count": 0,
        "market_context_count": 0,
        "krx_reference_status": "missing",
        "observed_at": None,
        "top_titles": [],
        "items": [],
        "empty_state": "뉴스 근거 수집 전",
        "missing_context": ["stored_news_observation"],
        "connection_label": "뉴스 근거 수집 전",
        "connection_reason": "저장 뉴스 근거가 수집되면 우선 확인 후보와 연결됩니다.",
    }
    _assert_public_safe_payload(snapshot)


def test_web_view_daily_snapshot_projects_saved_news_observation_public_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    run = _web_view_news_run()
    repository.save_news_intelligence_observation(
        run,
        [
            _web_view_news_evidence(),
            _web_view_news_evidence(
                evidence_key="news-evidence-2",
                title="삼성전자, 변동성 확대 주의",
                relevance="market_context",
                sentiment="Caution",
                stock_impact="Strong Negative",
                operator_recommendation="review_with_caution",
            ),
        ],
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 6, 2),
        now=datetime(2026, 6, 2, 10, 30, 0),
    )

    summary = snapshot["news_observation_summary"]
    assert summary["available"] is True
    assert summary["display_label"] == "종목 뉴스 매칭"
    assert summary["reason"] == "후보와 직접 매칭된 뉴스 1건이 저장돼 있습니다."
    assert summary["connection_label"] == "종목 뉴스 매칭"
    assert summary["connection_reason"] == "후보와 직접 매칭된 뉴스 1건이 저장돼 있습니다."
    assert summary["connection_note"] == "우선 확인 후보와 겹친 뉴스 근거: 삼성전자"
    assert summary["candidate_overlap_count"] == 1
    assert summary["candidate_overlap_names"] == ["삼성전자"]
    assert summary["direct_count"] == 1
    assert summary["positive_direct_count"] == 1
    assert summary["primary_caution_count"] == 0
    assert summary["caution_count"] == 1
    assert summary["market_context_count"] == 1
    assert summary["krx_reference_status"] == "exact"
    assert summary["observed_at"] == "2026-06-02T10:00:00"
    assert summary["evidence_direction"] == "상승 근거 우세"
    assert summary["evidence_direction_reason"] == "직접 긍정 뉴스 1건이 직접 주의 뉴스보다 우세합니다."
    assert summary["top_titles"] == [
        "삼성전자, AI 반도체 공급 계약 체결",
        "삼성전자, 변동성 확대 주의",
    ]
    assert [
        {
            key: value
            for key, value in item.items()
            if key
            not in {
                "collection_run_count",
                "latest_collection_at",
                "latest_collection_status",
                "daily_evidence_retained",
            }
        }
        for item in summary["items"]
    ] == [
        {
            "available": True,
            "stock_name": "삼성전자",
            "stock_code": "005930",
                "display_label": "종목 뉴스 매칭",
            "reason": "삼성전자, AI 반도체 공급 계약 체결",
            "direct_count": 1,
            "positive_direct_count": 1,
            "primary_caution_count": 0,
                "caution_count": 1,
                "market_context_count": 1,
                "independent_count": 2,
                "report_recap_count": 0,
                "unknown_count": 0,
                "krx_reference_status": "exact",
            "observed_at": "2026-06-02T10:00:00",
            "evidence_direction": "상승 근거 우세",
            "evidence_direction_reason": "직접 긍정 뉴스 1건이 직접 주의 뉴스보다 우세합니다.",
            "top_title": "삼성전자, AI 반도체 공급 계약 체결",
            "connection_label": "종목 뉴스 매칭",
            "connection_reason": "후보와 직접 매칭된 뉴스 1건이 저장돼 있습니다.",
        }
    ]
    assert summary["items"][0]["collection_run_count"] == 1
    assert summary["items"][0]["latest_collection_status"] == "matched"
    assert summary["items"][0]["daily_evidence_retained"] is False
    assert "overall_sentiment" not in summary
    assert "sentiment_score" not in json.dumps(summary, ensure_ascii=False)
    assert "stock_impact" not in json.dumps(summary, ensure_ascii=False)
    assert "operator_recommendation" not in json.dumps(summary, ensure_ascii=False)
    _assert_public_safe_payload(snapshot)


def test_web_view_stock_search_includes_stored_universe_without_same_day_report(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha Electronics",
                stock_code="005930",
                title="Alpha Electronics report",
                broker_name="NH",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="stock-search-report-a",
                identity_key="stock-search-report-a",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=business_date,
                standard_code="KR7000660001",
                stock_code="000660",
                stock_name="Beta Memory",
                market="KOSPI",
                fetched_at=datetime(2026, 6, 2, 18, 0, 0),
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000660",
                stock_name="Beta Memory",
                market="KOSPI",
                close_price=200_000,
                change_percent=1.2,
                turnover=123_000_000,
                fetched_at=datetime(2026, 6, 2, 18, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.save_news_intelligence_observation(
        _web_view_news_run(
            run_id="stock-search-news-run",
            target_date=business_date,
            stock_name="Beta Memory",
            stock_code="000660",
        ),
        [
            _web_view_news_evidence(
                run_id="stock-search-news-run",
                evidence_key="stock-search-news-evidence",
                title="Beta Memory expands AI memory supply",
                stock_code="000660",
                stock_name="Beta Memory",
                target_date=business_date,
            )
        ],
    )

    snapshot = cli_module.build_web_view_stock_search_snapshot(
        config,
        repository,
        business_date=business_date,
        query="Beta",
        now=datetime(2026, 6, 2, 10, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["live_fetch"] is False
    assert snapshot["available"] is True
    assert snapshot["items"] == [
        {
            "stock_code": "000660",
            "stock_name": "Beta Memory",
            "market": "KOSPI",
            "has_selected_date_report": False,
            "has_selected_date_toss": True,
            "has_news_observation": True,
            "display_status": "당일 리포트 없음 · 저장 Toss 있음 · 뉴스 근거 있음",
        }
    ]
    _assert_public_safe_payload(snapshot)


def test_web_view_stock_detail_uses_stored_name_when_selected_date_has_no_report(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=business_date,
                standard_code="KR7000660001",
                stock_code="000660",
                stock_name="Beta Memory",
                market="KOSPI",
                fetched_at=datetime(2026, 6, 2, 18, 0, 0),
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000660",
                stock_name="Beta Memory",
                market="KOSPI",
                close_price=200_000,
                change_percent=1.2,
                turnover=123_000_000,
                fetched_at=datetime(2026, 6, 2, 18, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="000660",
        now=datetime(2026, 6, 2, 10, 0, 0),
    )

    assert snapshot["stock_name"] == "Beta Memory"
    assert snapshot["has_selected_date_report"] is False
    assert snapshot["report_empty_state"] == "선택 날짜에 등록된 리포트가 없습니다."
    assert snapshot["reports"] == []
    assert snapshot["market_reference"]["close_price"] == 200_000
    _assert_public_safe_payload(snapshot)


def test_web_view_candidate_evidence_projects_public_safe_news_badge(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="?쇱꽦?꾩옄",
                stock_code="005930",
                title="?쇱꽦?꾩옄 ?먭? A",
                broker_name="NH?ъ옄利앷텒",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="news-badge-report-a",
                identity_key="news-badge-report-a",
            ),
            Report(
                stock_name="?쇱꽦?꾩옄",
                stock_code="005930",
                title="?쇱꽦?꾩옄 ?먭? B",
                broker_name="KB利앷텒",
                published_at=datetime(2026, 6, 2, 10, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 10, 0, 30),
                target_price_value=110_000,
                opinion_normalized="buy",
                source_id="news-badge-report-b",
                identity_key="news-badge-report-b",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    direct_evidence = _web_view_news_evidence(target_date=business_date, krx_reference_date=date(2026, 6, 1))
    repository.save_news_intelligence_observation(
        _web_view_news_run(target_date=business_date),
        [
            direct_evidence,
            _web_view_news_evidence(
                evidence_key="news-badge-caution",
                title="?쇱꽦?꾩옄, 蹂?숈꽦 ?뺣? 二쇱쓽",
                relevance="market_context",
                sentiment="Caution",
                stock_impact="Negative",
                operator_recommendation="review_with_caution",
                target_date=business_date,
                krx_reference_date=date(2026, 6, 1),
            ),
        ],
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )

    badge = snapshot["rows"][0]["news_observation_badge"]
    assert badge["available"] is True
    assert badge["display_label"] == "종목 뉴스 매칭"
    assert badge["reason"] == direct_evidence.title
    assert badge["direct_count"] == 1
    assert badge["caution_count"] == 1
    assert badge["market_context_count"] == 1
    assert badge["krx_reference_status"] == "stale"
    assert badge["observed_at"] == "2026-06-02T10:00:00"
    assert badge["connection_label"] == "종목 뉴스 매칭"
    assert badge["connection_reason"] == "후보와 직접 매칭된 뉴스 1건이 저장돼 있습니다."
    assert badge["top_title"] == direct_evidence.title
    assert badge["digest_label"] == "AI 반도체 공급 계약 체결"
    assert badge["news_digest"] == [
        {
            "date": "2026-06-02",
            "stock_name": "삼성전자",
            "label": "AI 반도체 공급 계약 체결",
                "evidence_label": "종목 직접 매칭",
                "lineage_type": "independent",
                "lineage_label": "독립 확인",
                "relevance": "direct",
            "source_lane": "mainnews",
        },
        {
            "date": "2026-06-02",
            "stock_name": "삼성전자",
            "label": "?쇱꽦?꾩옄, 蹂?숈꽦 ?뺣? 二쇱쓽",
                "evidence_label": "시장 맥락",
                "lineage_type": "independent",
                "lineage_label": "독립 확인",
                "relevance": "market_context",
            "source_lane": "mainnews",
        },
    ]
    payload = json.dumps(snapshot, ensure_ascii=False)
    assert "sentiment_score" not in payload
    assert "stock_impact" not in payload
    assert "operator_recommendation" not in payload
    _assert_public_safe_payload(snapshot)


def test_web_view_news_observation_badge_matches_stock_name_when_code_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="NameOnly Corp",
                stock_code="123456",
                title="NameOnly Corp check A",
                broker_name="NH",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="name-only-news-report-a",
                identity_key="name-only-news-report-a",
            ),
            Report(
                stock_name="NameOnly Corp",
                stock_code="123456",
                title="NameOnly Corp check B",
                broker_name="KB",
                published_at=datetime(2026, 6, 2, 10, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 10, 0, 30),
                target_price_value=110_000,
                opinion_normalized="buy",
                source_id="name-only-news-report-b",
                identity_key="name-only-news-report-b",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.save_news_intelligence_observation(
        _web_view_news_run(target_date=business_date, stock_name="NameOnly Corp", stock_code=None),
        [
            _web_view_news_evidence(
                evidence_key="name-only-news-evidence",
                title="NameOnly Corp expands supply",
                stock_code=None,
                stock_name="NameOnly Corp",
                target_date=business_date,
                krx_reference_date=business_date,
            )
        ],
    )

    candidate_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )
    stock_snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="123456",
        now=datetime(2026, 6, 2, 10, 30, 0),
    )

    badge = candidate_snapshot["rows"][0]["news_observation_badge"]
    assert badge["available"] is True
    assert badge["direct_count"] == 1
    assert badge["top_title"] == "NameOnly Corp expands supply"
    detail = stock_snapshot["news_observation_detail"]
    assert detail["available"] is True
    assert detail["direct_count"] == 1
    assert detail["top_titles"] == ["NameOnly Corp expands supply"]
    _assert_public_safe_payload(candidate_snapshot)
    _assert_public_safe_payload(stock_snapshot)


def test_web_view_candidate_evidence_projects_empty_news_badge(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="NAVER",
                stock_code="035420",
                title="NAVER ?먭?",
                broker_name="NH?ъ옄利앷텒",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=250_000,
                opinion_normalized="buy",
                source_id="news-badge-empty-report-a",
                identity_key="news-badge-empty-report-a",
            ),
            Report(
                stock_name="NAVER",
                stock_code="035420",
                title="NAVER ?먭? B",
                broker_name="KB利앷텒",
                published_at=datetime(2026, 6, 2, 10, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 10, 0, 30),
                target_price_value=260_000,
                opinion_normalized="buy",
                source_id="news-badge-empty-report-b",
                identity_key="news-badge-empty-report-b",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )

    assert snapshot["rows"][0]["news_observation_badge"] == {
        "available": False,
        "display_label": "뉴스 근거 수집 전",
        "reason": "저장 뉴스 근거를 아직 수집하지 않았습니다.",
        "connection_label": "뉴스 근거 수집 전",
        "connection_reason": "저장 뉴스 근거가 수집되면 후보와 연결됩니다.",
        "direct_count": 0,
        "caution_count": 0,
        "market_context_count": 0,
        "krx_reference_status": "missing",
        "observed_at": None,
        "top_title": None,
        "digest_label": None,
        "news_digest": [],
    }
    _assert_public_safe_payload(snapshot)


def test_web_view_stock_detail_projects_public_safe_news_observation_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="Samsung Electronics",
                stock_code="005930",
                title="AI semiconductor demand recovery",
                broker_name="NH",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="stock-detail-news-report-a",
                identity_key="stock-detail-news-report-a",
            )
        ]
    )
    repository.save_news_intelligence_observation(
        _web_view_news_run(target_date=business_date, stock_name="Samsung Electronics"),
        [
            _web_view_news_evidence(
                evidence_key="stock-detail-news-direct",
                title="Samsung expands AI semiconductor supply",
                target_date=business_date,
                krx_reference_date=business_date,
            ),
            _web_view_news_evidence(
                evidence_key="stock-detail-news-caution",
                title="Semiconductor volatility caution",
                relevance="market_context",
                sentiment="Caution",
                stock_impact="Negative",
                operator_recommendation="review_with_caution",
                target_date=business_date,
                krx_reference_date=date(2026, 6, 1),
            ),
        ],
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="005930",
        now=datetime(2026, 6, 2, 10, 30, 0),
    )

    detail = snapshot["news_observation_detail"]
    assert detail["source"] == "stored_news_intelligence_observation"
    assert detail["read_only"] is True
    assert detail["live_fetch"] is False
    assert detail["available"] is True
    assert detail["direct_count"] == 1
    assert detail["caution_count"] == 1
    assert detail["market_context_count"] == 1
    assert detail["krx_reference_status"] == "exact"
    assert detail["connection_label"] == "종목 뉴스 매칭"
    assert detail["connection_reason"] == "후보와 직접 매칭된 뉴스 1건이 저장돼 있습니다."
    assert detail["top_titles"] == [
        "Samsung expands AI semiconductor supply",
        "Semiconductor volatility caution",
    ]
    assert detail["digest_label"] == "Samsung expands AI semiconductor supply"
    assert detail["news_digest"] == [
        {
            "date": "2026-06-02",
            "stock_name": "삼성전자",
            "label": "Samsung expands AI semiconductor supply",
                "evidence_label": "종목 직접 매칭",
                "lineage_type": "independent",
                "lineage_label": "독립 확인",
                "relevance": "direct",
            "source_lane": "mainnews",
        },
        {
            "date": "2026-06-02",
            "stock_name": "삼성전자",
            "label": "Semiconductor volatility caution",
                "evidence_label": "시장 맥락",
                "lineage_type": "independent",
                "lineage_label": "독립 확인",
                "relevance": "market_context",
            "source_lane": "mainnews",
        },
    ]
    payload = json.dumps(snapshot, ensure_ascii=False)
    assert "sentiment_score" not in payload
    assert "stock_impact" not in payload
    assert "operator_recommendation" not in payload
    _assert_public_safe_payload(snapshot)


def test_web_view_stock_detail_projects_empty_news_observation_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="NAVER",
                stock_code="035420",
                title="Cloud growth check",
                broker_name="NH",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 0, 30),
                target_price_value=250_000,
                opinion_normalized="buy",
                source_id="stock-detail-news-empty-report-a",
                identity_key="stock-detail-news-empty-report-a",
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="035420",
        now=datetime(2026, 6, 2, 10, 30, 0),
    )

    detail = snapshot["news_observation_detail"]
    assert detail["source"] == "stored_news_intelligence_observation"
    assert detail["read_only"] is True
    assert detail["live_fetch"] is False
    assert detail["available"] is False
    assert detail["direct_count"] == 0
    assert detail["caution_count"] == 0
    assert detail["market_context_count"] == 0
    assert detail["krx_reference_status"] == "missing"
    assert detail["top_titles"] == []
    assert detail["missing_context"] == ["stored_news_observation"]
    _assert_public_safe_payload(snapshot)


def test_web_view_forbidden_public_keys_include_news_operator_fields() -> None:
    for key in [
        "overall_sentiment",
        "sentiment_score",
        "stock_impact",
        "operator_recommendation",
        "recommendation_support",
    ]:
        assert cli_module._is_web_view_forbidden_public_key(key) is True


def test_web_view_report_title_display_trims_only_trailing_parenthetical() -> None:
    assert cli_module._web_view_report_title_display("업황 회복 (요약)") == "업황 회복"
    assert cli_module._web_view_report_title_display("방산 지상군(이제 철도도 보자)") == "방산 지상군(이제 철도도 보자)"


def test_web_view_market_briefing_turnover_item_exposes_compact_display() -> None:
    item = StockMarketDailySnapshot(
        business_date=date(2026, 5, 14),
        stock_code="000660",
        stock_name="SK하이닉스",
        market="KOSPI",
        close_price=200_000,
        change_percent=3.2,
        volume=50_000,
        turnover=11_875_492_405_612,
        fetched_at=datetime(2026, 5, 14, 20, 0, 0),
    )

    payload = cli_module._web_view_market_briefing_turnover_item(item)

    assert payload["turnover"] == 11_875_492_405_612
    assert payload["turnover_display"] == "11.9조"


def test_web_view_market_briefing_turnover_summary_exposes_top_three_rows() -> None:
    business_date = date(2026, 5, 18)
    fetched_at = datetime(2026, 5, 18, 17, 0, 0)
    rows = {
        "KOSPI": [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                close_price=200_000,
                change_percent=1.2,
                volume=10,
                turnover=14_100_000_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=80_000,
                change_percent=-0.5,
                volume=10,
                turnover=10_700_000_000_000,
                fetched_at=fetched_at,
            ),
        ],
        "KOSDAQ": [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="089470",
                stock_name="코스모로보틱스",
                market="KOSDAQ",
                close_price=50_000,
                change_percent=2.0,
                volume=10,
                turnover=1_600_000_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000000",
                stock_name="제외후보",
                market="KOSDAQ",
                close_price=1_000,
                change_percent=0.1,
                volume=10,
                turnover=1_000_000,
                fetched_at=fetched_at,
            ),
        ],
    }

    payload = cli_module._web_view_market_briefing_turnover_summary_from_rows(
        business_date,
        reference_date=business_date,
        turnover_rows_by_market=rows,
    )

    assert [item["stock_code"] for item in payload["top_items"]] == ["000660", "005930", "089470"]
    assert len(payload["top_items"]) == 3


def test_web_view_observation_summary_market_mood_is_sentence_like(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    summaries = [
        cli_module.DailyStockSummary(
            business_date=business_date,
            stock_code="005930",
            stock_name="삼성전자",
            mention_count=3,
            broker_display="A증권, B증권",
            target_price_min=80000,
            target_price_max=90000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 18, 9, 5, 0),
        ),
        cli_module.DailyStockSummary(
            business_date=business_date,
            stock_code="000660",
            stock_name="SK하이닉스",
            mention_count=2,
            broker_display="C증권",
            target_price_min=150000,
            target_price_max=160000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 18, 9, 5, 0),
        ),
    ]
    sectors = [
        CategoryDailyRollup(
            business_date=business_date,
            category_type="sector",
            category_key="반도체",
            display_name="반도체",
            stock_count=2,
            report_count=5,
        )
    ]

    payload = cli_module._build_web_view_observation_summary(
        repository,
        business_date,
        summaries=summaries,
        sectors=sectors,
        themes=[],
        limit=3,
    )

    assert payload["market_mood"]["display"] == "리포트 5건이 2종목에 모였습니다."
    assert payload["market_mood"]["lines"] == [
        "리포트 5건이 2종목에 모였습니다.",
        "리포트가 몰린 쪽은 반도체 · 리포트 5건 · 2종목입니다.",
        "반복 언급 2종목, 수급 참고가 붙은 관찰 종목은 0개입니다.",
    ]
    assert payload["market_mood"]["observation_line"] == "반복 언급 2종목, 수급 참고가 붙은 관찰 종목은 0개입니다."
    assert payload["sector_breadth"]["sectors"][0]["display"] == "반도체 · 리포트 5건 · 2종목"
    assert payload["sector_breadth"]["sectors"][0]["share_percent"] == 100.0
    assert payload["sector_breadth"]["sectors"][0]["bar_width_percent"] == 100.0


def test_web_view_observation_summary_scales_sector_theme_breadth_bars(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    summaries = [
        cli_module.DailyStockSummary(
            business_date=business_date,
            stock_code="005930",
            stock_name="삼성전자",
            mention_count=3,
            broker_display="A증권",
            target_price_min=80000,
            target_price_max=90000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 18, 9, 5, 0),
        ),
        cli_module.DailyStockSummary(
            business_date=business_date,
            stock_code="012450",
            stock_name="한화에어로스페이스",
            mention_count=1,
            broker_display="B증권",
            target_price_min=300000,
            target_price_max=320000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 18, 9, 5, 0),
        ),
    ]
    sectors = [
        CategoryDailyRollup(
            business_date=business_date,
            category_type="sector",
            category_key="semi",
            display_name="반도체",
            stock_count=1,
            report_count=3,
        ),
        CategoryDailyRollup(
            business_date=business_date,
            category_type="sector",
            category_key="defense",
            display_name="우주항공과국방",
            stock_count=1,
            report_count=1,
        ),
    ]
    themes = [
        CategoryDailyRollup(
            business_date=business_date,
            category_type="theme",
            category_key="505",
            display_name="AI반도체",
            stock_count=1,
            report_count=2,
        )
    ]

    payload = cli_module._build_web_view_observation_summary(
        repository,
        business_date,
        summaries=summaries,
        sectors=sectors,
        themes=themes,
        limit=3,
    )

    sector_bars = payload["sector_breadth"]["sectors"]
    theme_bars = payload["sector_breadth"]["themes"]
    assert [item["category_display_name"] for item in sector_bars] == ["반도체", "우주항공과국방"]
    assert sector_bars[1]["display"] == "우주항공과국방 · 리포트 1건"
    assert "1종목" not in sector_bars[1]["display"]
    assert not sector_bars[1]["display"].startswith("업종 ")
    assert sector_bars[0]["bar_width_percent"] == 100.0
    assert sector_bars[0]["share_percent"] == 75.0
    assert sector_bars[1]["bar_width_percent"] == 33.3
    assert sector_bars[1]["share_percent"] == 25.0
    assert theme_bars[0]["bar_width_percent"] == 100.0
    assert theme_bars[0]["share_percent"] == 50.0


def test_web_view_archive_snapshot_is_read_only_and_public_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    snapshot = cli_module.build_web_view_archive_snapshot(
        config,
        repository,
        limit=10,
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["date_count"] == 1
    assert snapshot["latest_business_date"] == "2026-05-08"
    assert "빠르게 좁혀볼 수 있습니다" in snapshot["filter_hint"]
    assert snapshot["category_mapping_summary"] == {
        "dated_snapshot_count": 0,
        "fallback_count": 1,
        "notice": "일부 날짜는 과거 source-date 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다.",
    }
    assert snapshot["dates"] == [
        {
            "business_date": "2026-05-08",
            "report_count": 1,
            "summary_stock_count": 1,
            "news_observation_count": 0,
            "category_mapping": {
                "mapping_basis": "latest_mapping_fallback",
                "sector_snapshot_date": None,
                "theme_snapshot_date": None,
        "label": "최신 저장 분류",
            },
        }
    ]
    assert "scheduler_tasks" not in snapshot
    assert "db_path" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_archive_snapshot_marks_news_observation_count(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="archive-news-count-report",
                identity_key="archive-news-count-report",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.save_news_intelligence_observation(
        _web_view_news_run(run_id="archive-news-count-run", target_date=business_date),
        [_web_view_news_evidence(run_id="archive-news-count-run", target_date=business_date)],
    )

    snapshot = cli_module.build_web_view_archive_snapshot(config, repository, limit=10)

    assert snapshot["dates"][0]["business_date"] == "2026-05-08"
    assert snapshot["dates"][0]["news_observation_count"] == 1
    _assert_public_safe_payload(snapshot)


def test_web_view_archive_snapshot_marks_dated_category_mapping(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import CategoryCatalogItem, CategoryMembershipSnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 10, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="archive-category-1",
                identity_key="archive-category-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "test", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(date(2026, 5, 8), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    snapshot = cli_module.build_web_view_archive_snapshot(config, repository, limit=10)

    assert snapshot["dates"][0]["category_mapping"] == {
        "mapping_basis": "dated_snapshot",
        "sector_snapshot_date": "2026-05-08",
        "theme_snapshot_date": "2026-05-08",
        "label": "카테고리 스냅샷",
    }
    assert snapshot["category_mapping_summary"] == {
        "dated_snapshot_count": 1,
        "fallback_count": 0,
        "notice": "모든 날짜가 dated category snapshot 기준입니다.",
    }
    _assert_public_safe_payload(snapshot)


def test_web_view_archive_snapshot_batches_category_mapping_without_per_date_lookup(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 10, 0, 0)
    for index, business_date in enumerate((date(2026, 5, 8), date(2026, 5, 9)), start=1):
        repository.insert_reports(
            [
                Report(
                    stock_name="삼성전자",
                    stock_code="005930",
                    title=f"업황 회복 {index}",
                    broker_name="NH투자증권",
                    published_at=datetime.combine(business_date, datetime.min.time()).replace(hour=9),
                    business_date=business_date,
                    collected_at=datetime.combine(business_date, datetime.min.time()).replace(hour=9, minute=5),
                    source_id=f"archive-category-batch-{index}",
                    identity_key=f"archive-category-batch-{index}",
                )
            ]
        )
        repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "test", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(date(2026, 5, 8), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    def fail_per_date_lookup(**_kwargs):
        raise AssertionError("archive snapshot should batch category mapping lookups")

    monkeypatch.setattr(repository, "latest_category_snapshot_date", fail_per_date_lookup)

    snapshot = cli_module.build_web_view_archive_snapshot(config, repository, limit=10)

    assert [item["category_mapping"]["mapping_basis"] for item in snapshot["dates"]] == [
        "dated_snapshot",
        "dated_snapshot",
    ]
    assert snapshot["category_mapping_summary"]["dated_snapshot_count"] == 2


def test_web_view_daily_snapshot_includes_read_only_summary_layers(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="전일후보A",
                stock_code="111111",
                title="전일 점검 A",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 7, 9, 0, 0),
                business_date=date(2026, 5, 7),
                collected_at=datetime(2026, 5, 7, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/y1",
                source_id="daily-yesterday-1",
                identity_key="daily-yesterday-1",
            ),
            Report(
                stock_name="전일후보B",
                stock_code="222222",
                title="전일 점검 B",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 7, 9, 30, 0),
                business_date=date(2026, 5, 7),
                collected_at=datetime(2026, 5, 7, 9, 35, 0),
                source_url="https://stock.naver.com/research/company/y2",
                source_id="daily-yesterday-2",
                identity_key="daily-yesterday-2",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized="buy",
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="identity-2",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 7))
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=99_000,
                change_percent=-0.5,
                volume=8_000,
                turnover=400,
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                volume=10_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=99_000,
                change_percent=-0.5,
                volume=9_000,
                turnover=400,
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                close_price=200_000,
                change_percent=3.2,
                volume=50_000,
                turnover=900,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="069500",
                etf_name="KODEX 200",
                close_price=40_000,
                change_percent=0.5,
                nav=40_100.5,
                volume=5_000,
                turnover=300,
                underlying_index_name="코스피 200",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="1",
            sector_name="반도체",
            updated_at=datetime(2026, 5, 8, 10, 0, 0),
        )
    )
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="AI반도체",
                stock_code="005930",
                stock_name="삼성전자",
                updated_at=datetime(2026, 5, 8, 10, 0, 0),
            )
        ]
    )
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="KOSPI",
                investor_type="개인",
                net_buy_volume=-50,
                net_buy_amount=-100,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="KOSPI",
                investor_type="외국인",
                net_buy_volume=100,
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 8),
                market="STK",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_amount=300,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                investor_type="외국인",
                net_buy_volume=500,
                net_buy_amount=1_000,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                investor_type="개인",
                net_buy_volume=-300,
                net_buy_amount=-600,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
        ]
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["business_date"] == "2026-05-08"
    assert snapshot["public_contract"] == {
        "read_only": True,
        "source_scope": "저장 데이터 기준",
        "missing_value_policy": "누락값은 계산에서 제외하고 상세에 '-'로 표시합니다.",
        "recommendation": False,
        "control_exposed": False,
    }
    assert snapshot["category_contract"] == {
        "mapping_basis": "latest_mapping_fallback",
        "dated_snapshots_available": False,
        "snapshot_dates": [],
        "notice": "선택 날짜 이전의 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다.",
    }
    assert snapshot["report_count"] == 2
    assert snapshot["summary_stock_count"] == 1
    assert snapshot["stocks"][0]["stock_code"] == "005930"
    assert snapshot["stocks"][0]["primary_category"] == {
        "category_type": "sector",
        "category_label": "업종",
        "display_name": "반도체",
        "category_display_name": "반도체",
        "public_category_id": "sector|반도체|fallback",
        "snapshot_date": None,
        "mapping_source": "latest_mapping_fallback",
    }
    assert snapshot["stocks"][0]["market_reference"] == {
        "business_date": "2026-05-08",
        "market": "KOSPI",
        "close_price": 100_000,
            "change_percent": 1.2,
            "volume": 10_000,
            "turnover": 500,
            "fetched_at": "2026-05-08T20:00:00",
    }
    assert snapshot["toss_context"]["available"] is True
    assert snapshot["toss_context"]["snapshot_date"] == "2026-05-08"
    assert "20:00 저장을 보장하지 않으며" in snapshot["toss_context"]["notice"]
    assert snapshot["toss_context"]["top_kospi_by_turnover"][0]["stock_code"] == "000660"
    assert snapshot["toss_context"]["top_kospi_by_turnover"][0]["volume"] == 50_000
    source_freshness_items = {
        item["key"]: item for item in snapshot["source_freshness_summary"]["items"]
    }
    assert snapshot["source_freshness_summary"]["source"] == "stored_source_freshness"
    assert snapshot["source_freshness_summary"]["read_only"] is True
    assert snapshot["source_freshness_summary"]["live_fetch"] is False
    assert snapshot["source_freshness_summary"]["scoring"] is False
    assert source_freshness_items["reports"]["status"] == "exact"
    assert source_freshness_items["reports"]["reference_date"] == "2026-05-08"
    assert source_freshness_items["toss_market"]["status"] == "exact"
    assert source_freshness_items["toss_market"]["source"] == "toss_openapi"
    assert source_freshness_items["toss_market"]["reference_date"] == "2026-05-08"
    assert source_freshness_items["toss_market"]["exact_date_available"] is True
    assert source_freshness_items["toss_etf"]["status"] == "exact"
    assert source_freshness_items["investor_flow"]["status"] == "exact"
    assert source_freshness_items["investor_flow"]["source"] == "toss_openapi"
    assert source_freshness_items["toss_openapi"]["status"] == "disabled"
    assert source_freshness_items["toss_openapi"]["live_fetch"] is False
    assert source_freshness_items["toss_openapi"]["affects_ordering"] is False
    assert snapshot["toss_recent_flow"] == {
        "available": True,
        "source": "toss_openapi",
        "business_date": "2026-05-08",
        "reference_date": "2026-05-08",
        "exact_date_available": True,
        "notice": "선택 날짜를 포함한 최근 Toss 저장 스냅샷 기준입니다. 실시간값이나 확정 판단은 포함하지 않습니다.",
        "items": [
            {
                "business_date": "2026-05-08",
                "kospi_top_by_turnover": {
                    "business_date": "2026-05-08",
                    "stock_code": "000660",
                    "stock_name": "SK하이닉스",
                    "market": "KOSPI",
                    "close_price": 200_000,
                    "change_percent": 3.2,
                    "volume": 50_000,
                    "turnover": 900,
                    "fetched_at": "2026-05-08T20:00:00",
                },
                "kosdaq_top_by_turnover": None,
                "etf_top_by_turnover": {
                    "business_date": "2026-05-08",
                    "etf_code": "069500",
                    "etf_name": "KODEX 200",
                    "close_price": 40_000,
                    "change_percent": 0.5,
                    "nav": 40_100.5,
                    "volume": 5_000,
                    "turnover": 300,
                    "underlying_index_name": "코스피 200",
                    "evidence_label": "거래대금 300원 · NAV 40,100.5 · 기초지수 코스피 200",
                    "rotation_reference": "저장 ETF 거래대금/NAV/기초지수 기준",
                },
            },
            {
                "business_date": "2026-05-07",
                "kospi_top_by_turnover": {
                    "business_date": "2026-05-07",
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "market": "KOSPI",
                    "close_price": 99_000,
                    "change_percent": -0.5,
                    "volume": 9_000,
                    "turnover": 400,
                    "fetched_at": "2026-05-07T20:00:00",
                },
                "kosdaq_top_by_turnover": None,
                "etf_top_by_turnover": None,
            },
        ],
    }
    assert snapshot["toss_investor_flow"]["available"] is True
    assert snapshot["toss_investor_flow"]["source"] == "toss_openapi"
    assert snapshot["toss_investor_flow"]["data_scope"] == "stored_toss_close_market_flow"
    assert snapshot["toss_investor_flow"]["live_fetch"] is False
    assert snapshot["toss_investor_flow"]["scoring"] is False
    assert snapshot["toss_investor_flow"]["market_flows"][0]["investor_type"] == "외국인"
    assert snapshot["toss_investor_flow"]["market_flows"][0]["investor_label"] == "외국인"
    assert snapshot["toss_investor_flow"]["market_flows"][0]["market_label"] == "KOSPI"
    assert snapshot["toss_investor_flow"]["market_flows"][0]["net_buy_amount"] == 200
    assert snapshot["toss_investor_flow"]["market_flows"][1]["investor_type"] == "개인"
    assert "net_buy_top" not in snapshot["toss_investor_flow"]
    assert snapshot["market_reference_notice"] == "Toss 저장 스냅샷 기준입니다."
    assert snapshot["market_briefing"]["index_summary"]["available"] is False
    assert snapshot["market_briefing"]["turnover_summary"]["available"] is True
    assert snapshot["market_briefing"]["turnover_summary"]["markets"][0]["market"] == "KOSPI"
    assert snapshot["market_briefing"]["turnover_summary"]["markets"][0]["items"][0]["stock_code"] == "000660"
    assert snapshot["market_briefing"]["flow_summary"]["available"] is True
    assert snapshot["market_briefing"]["flow_summary"]["items"][0]["investor_label"] == "개인"
    assert snapshot["market_briefing"]["notable_stocks"][0]["stock_code"] == "005930"
    assert snapshot["market_briefing"]["notable_stocks"][0]["mention_count"] == 2
    assert "사용자 웹뷰" not in " ".join(snapshot["market_briefing"]["check_points"])
    assert "아래 종목/관찰 탭에서 세부 근거 확인" in snapshot["market_briefing"]["check_points"]
    mood_card = snapshot["market_briefing"]["time_slot_mood_card"]
    assert mood_card["source"] == "stored_report_toss_market_mood_card"
    assert mood_card["read_only"] is True
    assert mood_card["live_fetch"] is False
    assert mood_card["scoring"] is False
    assert mood_card["recommendation"] is False
    assert mood_card["production_integration"] is False
    assert mood_card["manual_review_candidate"] is True
    assert mood_card["title"] == "국장 시장 분위기"
    assert "삼성전자" in mood_card["headline"]
    assert [section["label"] for section in mood_card["sections"]] == ["지수", "주요 종목", "핵심 포인트", "확인 포인트"]
    assert mood_card["sections"][0]["available"] is False
    assert not any("intraday" in item["code"] for item in mood_card["source_gaps"])
    assert not any(item["code"] == "index_stored_reference_missing" for item in mood_card["source_gaps"])
    assert "목표가 참고 100,000원~110,000원" in mood_card["sections"][1]["items"][0]
    assert "{'min'" not in json.dumps(mood_card, ensure_ascii=False)
    assert snapshot["market_commentary"]["read_only"] is True
    assert snapshot["market_commentary"]["live_fetch"] is False
    assert snapshot["market_commentary"]["same_day_report_status"] == {
        "business_date": "2026-05-08",
        "report_count": 2,
        "summary_stock_count": 1,
        "summary_stock_code_count": 1,
        "can_overlap_intraday_market_top": True,
        "reason": "리포트 요약 1개 종목 기준으로 Naver 거래대금 상위와 교집합을 확인할 수 있습니다.",
    }
    assert [item["phase"] for item in snapshot["market_commentary"]["comments"]] == ["opening", "midday", "preclose"]
    assert [item["time"] for item in snapshot["market_commentary"]["comments"]] == ["09:15", "12:00", "15:15"]
    opening_comment = snapshot["market_commentary"]["comments"][0]
    assert opening_comment["reference_date"] == "2026-05-07"
    assert opening_comment["comment"] == ""
    assert "전일후보A" in " ".join(opening_comment["details"])
    assert "전일후보B" in " ".join(opening_comment["details"])
    assert all(item["details"] for item in snapshot["market_commentary"]["comments"])
    assert "periodic_data_needs" not in snapshot
    assert snapshot["sectors"][0]["sector_name"] == "반도체"
    assert snapshot["sectors"][0]["sector_display_name"] == "반도체"
    assert snapshot["themes"][0]["theme_name"] == "AI반도체"
    assert snapshot["themes"][0]["theme_display_name"] == "AI반도체"
    assert "buy_opinion_count" not in snapshot["market_mood"]
    assert snapshot["watch_candidates"][0]["stock_code"] == "005930"
    assert "리포트 2건" in snapshot["watch_candidates"][0]["reason"]
    assert "매수 의견" not in snapshot["watch_candidates"][0]["reason"]
    assert "candidate_evidence" not in snapshot
    concentration_item = snapshot["observation_summary"]["report_concentration"]["items"][0]
    assert "five_business_day_broker_count" not in concentration_item["report_intensity"]
    assert "previous_broker_count" not in concentration_item["target_price_revision"]
    assert "scheduler_tasks" not in snapshot
    assert "db_path" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_time_slot_mood_card_deduplicates_index_check_points() -> None:
    card = cli_module._web_view_time_slot_market_mood_card(
        date(2026, 5, 15),
        summaries=[],
        index_summary={
            "available": True,
            "reference_date": "2026-05-15",
            "exact_date_available": True,
            "indices": [
                {"index_name": "코스피", "close_index": 7493.18, "change_percent": -6.12},
                {"index_name": "코스닥", "close_index": 1129.82, "change_percent": -5.14},
            ],
        },
        turnover_summary={},
        flow_summary={},
        notable_stocks=[],
        check_points=[
            "KOSPI 하락, KOSDAQ 하락 흐름",
            "아래 종목/관찰 탭에서 세부 근거 확인",
        ],
    )

    sections = {section["key"]: section for section in card["sections"]}
    assert sections["core_points"]["items"] == [
        "리포트 0건 / 0종목 기준으로 압축",
        "지수 참고: 코스피 하락 / 코스닥 하락",
    ]
    assert sections["check_points"]["items"] == ["아래 종목/관찰 탭에서 세부 근거 확인"]
    assert not any(
        "점심/마감 전 장중 등락률" in item
        for section in card["sections"]
        for item in section.get("items", [])
    )


def test_web_view_daily_snapshot_default_does_not_fetch_intraday_market_top(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 9, 30, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="기본로딩",
                stock_code="000001",
                title="기본 로딩 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fail_market_top(*_args, **_kwargs):
        raise AssertionError("default web-view daily snapshot must not fetch Naver market top data")

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fail_market_top)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
    )

    assert snapshot["market_commentary"]["live_fetch"] is False
    assert snapshot["market_commentary"]["intraday_market_top_reference"]["live_fetch"] is False
    assert snapshot["market_commentary"]["same_day_report_status"]["can_overlap_intraday_market_top"] is True


def test_web_view_daily_snapshot_reports_no_same_day_summary_for_intraday_overlap(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 9, 30, 0)

    def fail_market_top(*_args, **_kwargs):
        raise AssertionError("no report summary should not need Naver market top fetch unless explicitly requested")

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fail_market_top)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
    )

    status = snapshot["market_commentary"]["same_day_report_status"]
    assert status["business_date"] == "2026-05-20"
    assert status["report_count"] == 0
    assert status["summary_stock_count"] == 0
    assert status["can_overlap_intraday_market_top"] is False
    assert status["reason"] == "당일 리포트 요약이 없어 거래대금 교집합을 만들 수 없습니다."


def test_web_view_daily_snapshot_skips_intraday_market_top_when_summaries_lack_stock_codes(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 9, 30, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="코드없음",
                stock_code=None,
                title="코드 없는 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fail_market_top(*_args, **_kwargs):
        raise AssertionError("summaries without stock codes must not fetch Naver market top data")

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fail_market_top)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
        include_intraday_market_top=True,
    )

    status = snapshot["market_commentary"]["same_day_report_status"]
    reference = snapshot["market_commentary"]["intraday_market_top_reference"]
    assert status["report_count"] == 1
    assert status["summary_stock_count"] == 1
    assert status["summary_stock_code_count"] == 0
    assert status["can_overlap_intraday_market_top"] is False
    assert status["reason"] == "종목 코드가 있는 당일 리포트 요약이 없어 거래대금 교집합을 만들 수 없습니다."
    assert reference["live_fetch"] is False
    assert reference["empty_reason"] == status["reason"]


def test_web_view_daily_snapshot_blocks_intraday_market_top_for_archive_dates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 20, 12, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="과거날짜",
                stock_code="000001",
                title="과거 리포트",
                broker_name="테스트증권",
                published_at=datetime(2026, 5, 18, 9, 30, 0),
                collected_at=datetime(2026, 5, 18, 9, 31, 0),
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fail_market_top(*_args, **_kwargs):
        raise AssertionError("archive dates must not fetch current Naver market top data")

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fail_market_top)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
        include_intraday_market_top=True,
    )

    status = snapshot["market_commentary"]["same_day_report_status"]
    reference = snapshot["market_commentary"]["intraday_market_top_reference"]
    assert status["can_overlap_intraday_market_top"] is False
    assert status["reason"] == "오늘 정규장 시간에만 확인 할 수 있습니다."
    assert reference["live_fetch"] is False
    assert reference["empty_reason"] == status["reason"]


def test_web_view_daily_snapshot_can_include_explicit_intraday_market_top_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 9, 30, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="웹뷰겹침",
                stock_code="000001",
                title="웹뷰 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_market_top(market: str, **_kwargs):
        if market != "KOSPI":
            return []
        return [
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="000001",
                stock_name="웹뷰겹침",
                stock_end_type="stock",
                current_price=10_500,
                change_price=500,
                change_percent=5.0,
                trade_amount=90_000_000_000,
                trade_volume=1_200_000,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 20, 12, 1, 0),
            )
        ]

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
        include_intraday_market_top=True,
        intraday_market_top_limit=20,
        intraday_market_top_page_size=20,
        intraday_market_top_delay_seconds=0,
    )

    reference = snapshot["market_commentary"]["intraday_market_top_reference"]
    assert reference["live_fetch"] is True
    assert reference["items"][0]["stock_code"] == "000001"
    assert reference["items"][0]["market_status"] == "OPEN"
    assert reference["items"][0]["trade_time"] == "2026-05-20T12:01:00"
    assert reference["items"][0]["checked_at"] == "2026-05-20T09:30:00"
    assert reference["empty_reason"] is None
    assert snapshot["market_commentary"]["same_day_report_status"]["can_overlap_intraday_market_top"] is True
    assert "Naver 거래대금 상위 기준" in snapshot["market_commentary"]["comments"][1]["comment"]
    _assert_public_safe_payload(snapshot)


def test_web_view_intraday_market_top_reference_marks_checked_at_when_trade_time_missing(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 9, 35, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="한미약품",
                stock_code="128940",
                title="한미약품 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_market_top(market: str, **_kwargs):
        if market != "KOSPI":
            return []
        return [
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="128940",
                stock_name="한미약품",
                stock_end_type="stock",
                current_price=302_000,
                change_price=10_000,
                change_percent=3.42,
                trade_amount=120_000_000_000,
                trade_volume=450_000,
                market_status="OPEN",
                trade_time=None,
            )
        ]

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
        include_intraday_market_top=True,
        intraday_market_top_limit=20,
        intraday_market_top_page_size=20,
        intraday_market_top_delay_seconds=0,
    )

    item = snapshot["market_commentary"]["intraday_market_top_reference"]["items"][0]
    assert item["stock_code"] == "128940"
    assert item["market_status"] == "OPEN"
    assert item["trade_time"] is None
    assert item["checked_at"] == "2026-05-20T09:35:00"
    _assert_public_safe_payload(snapshot)


def test_web_view_daily_snapshot_batches_primary_category_hints(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 10, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="daily-primary-category-batch-1",
                identity_key="daily-primary-category-batch-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "test", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(business_date, "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(business_date, "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    def fail_per_rollup_lookup(*_args, **_kwargs):
        raise AssertionError("daily snapshot should batch primary category lookups")

    monkeypatch.setattr(repository, "list_daily_summaries_for_category_display_name", fail_per_rollup_lookup)

    snapshot = cli_module.build_web_view_daily_snapshot(config, repository, business_date=business_date)

    assert snapshot["stocks"][0]["primary_category"] == {
        "category_type": "sector",
        "category_label": "업종",
        "display_name": "반도체",
        "category_display_name": "반도체",
        "public_category_id": "sector|반도체|2026-05-08",
        "snapshot_date": "2026-05-08",
        "mapping_source": "dated_snapshot",
    }


def test_web_view_daily_snapshot_reuses_recent_krx_snapshot_dates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="daily-krx-date-cache-1",
                identity_key="daily-krx-date-cache-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    original = repository.list_recent_krx_snapshot_dates
    call_count = 0

    def counted_recent_krx_dates(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(repository, "list_recent_krx_snapshot_dates", counted_recent_krx_dates)

    cli_module.build_web_view_daily_snapshot(config, repository, business_date=business_date)

    assert call_count <= 1


def test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    stock_rows = [
        ("005930", "삼성전자", 100_000, 1_000),
        ("000660", "SK하이닉스", 200_000, 2_000),
        ("035420", "NAVER", 180_000, 1_500),
    ]
    reports = []
    market_rows = []
    flow_rows = []
    for index, (stock_code, stock_name, close_price, net_buy_amount) in enumerate(stock_rows, start=1):
        reports.extend(
            [
                Report(
                    stock_name=stock_name,
                    stock_code=stock_code,
                    title=f"{stock_name} 점검 A",
                    broker_name="NH투자증권",
                    published_at=datetime(2026, 5, 8, 9, index, 0),
                    business_date=business_date,
                    collected_at=datetime(2026, 5, 8, 9, index, 30),
                    target_price_value=close_price + 10_000,
                    opinion_normalized="buy",
                    source_id=f"batch-candidate-{stock_code}-a",
                    identity_key=f"batch-candidate-{stock_code}-a",
                ),
                Report(
                    stock_name=stock_name,
                    stock_code=stock_code,
                    title=f"{stock_name} 점검 B",
                    broker_name="KB증권",
                    published_at=datetime(2026, 5, 8, 10, index, 0),
                    business_date=business_date,
                    collected_at=datetime(2026, 5, 8, 10, index, 30),
                    target_price_value=close_price + 20_000,
                    opinion_normalized="buy",
                    source_id=f"batch-candidate-{stock_code}-b",
                    identity_key=f"batch-candidate-{stock_code}-b",
                ),
            ]
        )
        market_rows.extend(
            [
                StockMarketDailySnapshot(
                    business_date=date(2026, 5, 7),
                    stock_code=stock_code,
                    stock_name=stock_name,
                    market="KOSPI",
                    close_price=close_price - 5_000,
                    change_percent=-0.5,
                    volume=900 + index,
                    turnover=900_000 + index,
                    fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                ),
                StockMarketDailySnapshot(
                    business_date=business_date,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    market="KOSPI",
                    close_price=close_price,
                    change_percent=1.2,
                    volume=1_000 + index,
                    turnover=1_000_000 + index,
                    fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                ),
                StockMarketDailySnapshot(
                    business_date=date(2026, 5, 11),
                    stock_code=stock_code,
                    stock_name=stock_name,
                    market="KOSPI",
                    close_price=close_price + 5_000,
                    change_percent=1.0,
                    volume=1_100 + index,
                    turnover=1_100_000 + index,
                    fetched_at=datetime(2026, 5, 11, 20, 0, 0),
                ),
            ]
        )
        for investor_type, amount in (("외국인", net_buy_amount), ("기관", net_buy_amount // 2), ("개인", -net_buy_amount)):
            flow_rows.append(
                StockInvestorFlowDaily(
                    business_date=business_date,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    market="STK",
                    investor_type=investor_type,
                    net_buy_volume=amount,
                    net_buy_amount=amount,
                    volume_unit="주",
                    amount_unit="원",
                    fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                )
            )
    repository.insert_reports(reports)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(market_rows)
    repository.upsert_stock_investor_flow_daily(flow_rows)

    connect_count = 0
    original_connect = repository.connect

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(repository, "connect", counting_connect)

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=3,
    )

    assert {row["stock_code"] for row in snapshot["rows"]} == {"005930", "000660", "035420"}
    assert "candidates" not in snapshot
    assert connect_count <= 15


def test_web_view_candidate_evidence_prioritizes_backtest_supported_observation_signals(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 16, 0, 0)

    def reports_for(stock_code: str, stock_name: str, count: int) -> list[Report]:
        return [
            Report(
                stock_name=stock_name,
                stock_code=stock_code,
                title=f"{stock_name} 점검 {index}",
                broker_name=f"증권사{index}",
                published_at=datetime(2026, 5, 8, 9, index, 0),
                business_date=business_date,
                collected_at=fetched_at,
                target_price_value=100_000 + index,
                opinion_normalized="buy",
                source_id=f"supported-signal-{stock_code}-{index}",
                identity_key=f"supported-signal-{stock_code}-{index}",
            )
            for index in range(1, count + 1)
        ]

    repository.insert_reports(
        reports_for("000002", "TwoReportForeignTop", 2)
        + reports_for("000004", "FourReportFlowStreak", 4)
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000002",
                stock_name="TwoReportForeignTop",
                market="KOSPI",
                close_price=50_000,
                volume=1_000,
                turnover=10_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000004",
                stock_name="FourReportFlowStreak",
                market="KOSPI",
                close_price=50_000,
                volume=1_000,
                turnover=10_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000002",
                stock_name="TwoReportForeignTop",
                market="KOSPI",
                close_price=50_000,
                volume=1_000,
                turnover=10_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000004",
                stock_name="FourReportFlowStreak",
                market="KOSPI",
                close_price=50_000,
                volume=1_000,
                turnover=10_000_000,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000002",
                stock_name="TwoReportForeignTop",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="000004",
                stock_name="FourReportFlowStreak",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000004",
                stock_name="FourReportFlowStreak",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000004",
                stock_name="FourReportFlowStreak",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
                source="toss_openapi",
            ),
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=3,
                stock_code="000002",
                stock_name="TwoReportForeignTop",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    assert snapshot["scoring"] is False
    assert snapshot["recommendation"] is False
    assert "브로커 폭" not in json.dumps(snapshot, ensure_ascii=False)
    assert "브로커 폭" not in snapshot["display_policy"]
    assert "확인용으로 묶어 보여줍니다" in snapshot["display_policy"]
    assert "추천" not in snapshot["display_policy"]
    assert "실시간 시세가 아닙니다" in snapshot["notice"]
    assert [row["stock_code"] for row in snapshot["rows"]] == ["000004", "000002"]
    assert snapshot["rows"][0]["why_notable"] == ["리포트 집중", "수급 전환 지속"]
    assert snapshot["rows"][1]["why_notable"] == ["리포트 집중"]
    assert "외국인 순매수 상위 참고" not in snapshot["rows"][1]["evidence_layers"]["support"]
    assert snapshot["rows"][0]["intraday_reference"] == {
        "available": False,
        "source_configured": False,
        "read_only": True,
        "live_fetch": False,
        "scope": "top_2_priority_candidates",
        "cadence_minutes": 5,
        "reference_time": None,
        "price": None,
        "change_percent": None,
        "turnover": None,
        "affects_ordering": False,
        "notice": "장중 실시간 참고 소스가 아직 확정되지 않았습니다.",
    }
    assert snapshot["rows"][1]["intraday_reference"]["affects_ordering"] is False
    assert "거래대금 참고" not in snapshot["rows"][0]["why_notable"]
    assert "목표가 범위" not in snapshot["rows"][0]["why_notable"]
    assert "브로커 폭" not in snapshot["rows"][0]["why_notable"]
    assert snapshot["rows"][0]["evidence_layers"]["primary"] == snapshot["rows"][0]["why_notable"]
    assert snapshot["rows"][0]["evidence_layers"]["support"] == [
        "Toss 저장 가격 참고",
        "거래대금 참고",
        "거래량 위치 참고",
    ]
    assert snapshot["rows"][0]["evidence_layers"]["gap"] == []
    assert "internal_candidate_signals" not in snapshot["rows"][0]
    assert "internal_missing_information" not in snapshot["rows"][0]
    assert "explanation_quality" not in snapshot["rows"][0]
    assert "top_candidate_maturity" not in snapshot
    assert "top_candidate_explanation_quality_counts" not in snapshot
    assert "top_candidate_review_priority_counts" not in snapshot
    assert "top_candidate_next_evidence_gap_counts" not in snapshot
    assert "quality_flags" not in snapshot["rows"][0]
    assert "evidence_notes" not in snapshot["rows"][0]
    assert "opinion_summary" not in snapshot["rows"][0]
    assert "broker_count" not in snapshot["rows"][0]["report_summary"]
    assert "broker_display" not in snapshot["rows"][0]["report_summary"]
    assert "dominant_opinion" not in snapshot["rows"][0]["report_summary"]
    assert "five_business_day_broker_count" not in snapshot["rows"][0]["report_intensity"]
    assert "previous_broker_count" not in snapshot["rows"][0]["target_price_revision"]
    assert "외국인 순매수 상위 참고" not in snapshot["rows"][1]["why_notable"]


def test_web_view_candidate_evidence_public_missing_labels_are_stored_reference_based(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="저장값대기",
                stock_code="000001",
                title="저장 근거 점검",
                broker_name="테스트증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="candidate-missing-stored-reference",
                identity_key="candidate-missing-stored-reference",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    public_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )
    internal_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
        include_internal=True,
    )

    assert public_snapshot["rows"][0]["missing_information"] == [
        "선택일 Toss 저장값 없음",
        "종목 수급 저장값 없음",
    ]
    assert public_snapshot["rows"][0]["evidence_layers"]["primary"] == []
    assert public_snapshot["rows"][0]["evidence_layers"]["support"] == []
    assert public_snapshot["rows"][0]["evidence_layers"]["gap"] == public_snapshot["rows"][0]["missing_information"]
    assert "quality_flags" not in public_snapshot["rows"][0]
    assert internal_snapshot["rows"][0]["internal_missing_information"][:2] == [
        "당일 Toss 저장값 없음",
        "종목 수급 데이터 없음",
    ]


def test_candidate_flow_context_uses_toss_for_selected_date_and_krx_for_history(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                net_buy_volume=120,
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                net_buy_volume=80,
                source="krx_data_market",
            ),
        ]
    )

    context = cli_module._load_candidate_flow_context(
        repository,
        business_date=business_date,
        stock_codes=["005930"],
    )

    assert [row.source for row in context["same_day_flow_by_code"]["005930"]] == ["toss_openapi"]
    assert [row["source"] for row in context["flow_window_rows_by_code"]["005930"]] == ["krx_data_market"]


def test_candidate_evidence_adds_same_source_market_relative_event_reaction(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 11, 20, 0, 0)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="삼성전자",
                stock_code="005930",
                title="실적 확인",
                broker_name="테스트증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                collected_at=datetime(2026, 5, 8, 9, 1, 0),
                source_id="market-relative-reaction",
                identity_key="market-relative-reaction",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=day,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=fetched_at,
                close_price=close_price,
                source="krx",
            )
            for day, close_price in (
                (date(2026, 5, 7), 100_000),
                (business_date, 110_000),
                (date(2026, 5, 11), 120_000),
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=day,
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                fetched_at=fetched_at,
                close_index=close_index,
                source="krx",
            )
            for day, close_index in (
                (date(2026, 5, 7), 1_000.0),
                (business_date, 1_050.0),
                (date(2026, 5, 11), 1_100.0),
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )

    reaction = snapshot["rows"][0]["event_reaction"]
    assert reaction["source"] == "krx"
    assert reaction["historical_review"] is True
    assert reaction["benchmark"] == "KOSPI"
    assert reaction["affects_ordering"] is False
    assert reaction["windows"] == [
        {
            "horizon": "D0",
            "business_date": "2026-05-08",
            "stock_return_percent": 10.0,
            "benchmark_return_percent": 5.0,
            "excess_return_percent": 5.0,
        },
        {
            "horizon": "D+1",
            "business_date": "2026-05-11",
            "stock_return_percent": 20.0,
            "benchmark_return_percent": 10.0,
            "excess_return_percent": 10.0,
        },
    ]


def test_market_relative_event_reaction_does_not_invent_d0_without_event_row() -> None:
    fetched_at = datetime(2026, 5, 11, 20, 0, 0)
    reaction = cli_module._web_view_market_relative_event_reaction(
        business_date=date(2026, 5, 8),
        stock_rows=[
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=fetched_at,
                close_price=100_000,
                source="krx",
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=fetched_at,
                close_price=110_000,
                source="krx",
            ),
        ],
        index_rows_by_series={"KOSPI": [], "KOSDAQ": []},
    )

    assert reaction["available"] is False
    assert reaction["windows"] == []
    assert reaction["unavailable_reason"] == "missing_event_stock_row"


def test_market_relative_event_reaction_keeps_stock_horizon_when_benchmark_is_missing() -> None:
    fetched_at = datetime(2026, 5, 11, 20, 0, 0)
    stock_rows = [
        StockMarketDailySnapshot(
            business_date=day,
            stock_code="005930",
            stock_name="삼성전자",
            market="KOSPI",
            fetched_at=fetched_at,
            close_price=close_price,
            source="krx",
        )
        for day, close_price in (
            (date(2026, 5, 7), 100_000),
            (date(2026, 5, 8), 110_000),
            (date(2026, 5, 11), 120_000),
        )
    ]
    index_rows = [
        MarketIndexDailySnapshot(
            business_date=day,
            index_series="KOSPI",
            index_class="대표",
            index_name="코스피",
            fetched_at=fetched_at,
            close_index=close_index,
            source="krx",
        )
        for day, close_index in (
            (date(2026, 5, 7), 1_000.0),
            (date(2026, 5, 8), 1_050.0),
        )
    ]

    reaction = cli_module._web_view_market_relative_event_reaction(
        business_date=date(2026, 5, 8),
        stock_rows=stock_rows,
        index_rows_by_series={"KOSPI": index_rows, "KOSDAQ": []},
    )

    assert reaction["windows"][1] == {
        "horizon": "D+1",
        "business_date": "2026-05-11",
        "stock_return_percent": 20.0,
        "benchmark_return_percent": None,
        "excess_return_percent": None,
        "market_unavailable_reason": "missing_same_date_benchmark",
    }


def test_web_view_candidate_evidence_rank_reason_stays_reference_when_stock_flow_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="랭크참고",
                stock_code="000001",
                title="외국인 순매수 상위 참고",
                broker_name="테스트증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="candidate-rank-reference",
                identity_key="candidate-rank-reference",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000001",
                stock_name="랭크참고",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000001",
                stock_name="랭크참고",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=3,
                stock_code="000001",
                stock_name="랭크참고",
                net_buy_amount=1_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    public_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
    )
    internal_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=1,
        include_internal=True,
    )

    row = public_snapshot["rows"][0]
    assert "외국인 순매수 상위 참고" not in row["why_notable"]
    assert "외국인 순매수 상위" not in row["why_notable"]
    assert row["missing_information"] == ["종목 수급 저장값 없음"]
    assert row["evidence_layers"]["primary"] == []
    assert row["evidence_layers"]["support"] == [
        "Toss 저장 가격 참고",
        "거래대금 참고",
        "거래량 위치 참고",
    ]
    assert "rank_reference" not in row
    assert row["evidence_layers"]["gap"] == row["missing_information"]
    assert "외국인 순매수 상위" in internal_snapshot["rows"][0]["internal_candidate_signals"]


def test_web_view_candidate_evidence_rank_reference_does_not_drive_public_order(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 16, 0, 0)

    def report(stock_code: str, stock_name: str) -> Report:
        return Report(
            stock_name=stock_name,
            stock_code=stock_code,
            title=f"{stock_name} 점검",
            broker_name="테스트증권",
            published_at=datetime(2026, 5, 8, 9, 0, 0),
            business_date=business_date,
            collected_at=fetched_at,
            target_price_value=100_000,
            opinion_normalized="buy",
            source_id=f"rank-context-only-{stock_code}",
            identity_key=f"rank-context-only-{stock_code}",
        )

    repository.insert_reports([report("000001", "RankReference"), report("000999", "PlainReference")])
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code=code,
                stock_name=name,
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            )
            for code, name in (("000001", "RankReference"), ("000999", "PlainReference"))
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=1,
                stock_code="000001",
                stock_name="RankReference",
                net_buy_amount=1_000,
                fetched_at=fetched_at,
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    assert [row["stock_code"] for row in snapshot["rows"]] == ["000999", "000001"]
    assert snapshot["rows"][1]["why_notable"] == []
    assert "외국인 순매수 상위 참고" not in snapshot["rows"][1]["evidence_layers"]["support"]


def test_web_view_candidate_evidence_prefers_composite_flow_over_rank_without_stock_flow(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 16, 0, 0)

    def report(stock_code: str, stock_name: str, index: int) -> Report:
        return Report(
            stock_name=stock_name,
            stock_code=stock_code,
            title=f"{stock_name} 점검 {index}",
            broker_name=f"증권사{index}",
            published_at=datetime(2026, 5, 8, 9, index, 0),
            business_date=business_date,
            collected_at=fetched_at,
            target_price_value=100_000 + index,
            opinion_normalized="buy",
            source_id=f"rank-vs-composite-{stock_code}-{index}",
            identity_key=f"rank-vs-composite-{stock_code}-{index}",
        )

    repository.insert_reports(
        [
            report("000101", "RankOnlyNoFlow", 1),
            report("000101", "RankOnlyNoFlow", 2),
            report("000202", "CompositeFlow", 1),
            report("000202", "CompositeFlow", 2),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000202",
                stock_name="CompositeFlow",
                market="KOSPI",
                close_price=90_000,
                change_percent=1.5,
                volume=20_000,
                turnover=200_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000202",
                stock_name="CompositeFlow",
                market="KOSPI",
                close_price=90_000,
                change_percent=1.5,
                volume=20_000,
                turnover=200_000_000,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="000202",
                stock_name="CompositeFlow",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000202",
                stock_name="CompositeFlow",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000202",
                stock_name="CompositeFlow",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
                source="toss_openapi",
            ),
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=1,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                net_buy_amount=1_000,
                fetched_at=fetched_at,
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )
    internal_snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
        include_internal=True,
    )

    assert [row["stock_code"] for row in snapshot["rows"]] == ["000202", "000101"]
    assert snapshot["rows"][0]["why_notable"] == ["리포트 집중", "수급 전환 지속"]
    assert snapshot["rows"][1]["why_notable"] == ["리포트 집중"]
    assert "외국인 순매수 상위 참고" not in snapshot["rows"][1]["evidence_layers"]["support"]
    assert snapshot["rows"][1]["missing_information"] == ["종목 수급 저장값 없음"]
    assert "외국인 순매수 상위" in internal_snapshot["rows"][1]["internal_candidate_signals"]


def test_web_view_candidate_evidence_prefers_exact_flow_composite_over_rank_only(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    previous_date = date(2026, 5, 7)
    fetched_at = datetime(2026, 5, 8, 16, 0, 0)

    def report(stock_code: str, stock_name: str, index: int, target: int, day: date) -> Report:
        return Report(
            stock_name=stock_name,
            stock_code=stock_code,
            title=f"{stock_name} 점검 {day.isoformat()} {index}",
            broker_name=f"증권사{index}",
            published_at=datetime(day.year, day.month, day.day, 9, index, 0),
            business_date=day,
            collected_at=fetched_at,
            target_price_value=target,
            opinion_normalized="buy",
            source_id=f"rank-only-calibration-{stock_code}-{day.isoformat()}-{index}",
            identity_key=f"rank-only-calibration-{stock_code}-{day.isoformat()}-{index}",
        )

    repository.insert_reports(
        [
            report("000101", "RankOnlyNoFlow", 1, 80_000, previous_date),
            report("000101", "RankOnlyNoFlow", 1, 90_000, business_date),
            report("000101", "RankOnlyNoFlow", 2, 90_000, business_date),
            report("000202", "ExactFlowComposite", 1, 80_000, previous_date),
            report("000202", "ExactFlowComposite", 1, 90_000, business_date),
            report("000202", "ExactFlowComposite", 2, 90_000, business_date),
        ]
    )
    repository.rebuild_daily_summaries(previous_date)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000202",
                stock_name="ExactFlowComposite",
                market="KOSPI",
                close_price=90_000,
                change_percent=1.5,
                volume=20_000,
                turnover=200_000_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                market="KOSPI",
                close_price=80_000,
                change_percent=1.2,
                volume=10_000,
                turnover=100_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000202",
                stock_name="ExactFlowComposite",
                market="KOSPI",
                close_price=90_000,
                change_percent=1.5,
                volume=20_000,
                turnover=200_000_000,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="000202",
                stock_name="ExactFlowComposite",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_amount=1_000,
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=1,
                stock_code="000101",
                stock_name="RankOnlyNoFlow",
                net_buy_amount=1_000,
                fetched_at=fetched_at,
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    assert [row["stock_code"] for row in snapshot["rows"]] == ["000202", "000101"]
    assert snapshot["rows"][0]["observation_priority"] == "확인 후보"
    assert snapshot["rows"][0]["why_notable"] == ["리포트 집중", "일자 집계 목표가 범위 상향"]
    assert snapshot["rows"][0]["missing_information"] == []
    assert snapshot["rows"][1]["why_notable"] == ["리포트 집중", "일자 집계 목표가 범위 상향"]
    assert "외국인 순매수 상위 참고" not in snapshot["rows"][1]["evidence_layers"]["support"]
    assert snapshot["rows"][1]["missing_information"] == ["종목 수급 저장값 없음"]


def test_web_view_daily_category_contract_uses_snapshot_availability_without_rollups(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 10, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 9, 5, 0),
                source_id="daily-contract-no-rollup",
                identity_key="daily-contract-no-rollup",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 12))
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "test", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "semi", "반도체", "000660", "SK하이닉스", fetched_at, "test"),
            CategoryMembershipSnapshot(date(2026, 5, 8), "theme", "505", "AI반도체", "000660", "SK하이닉스", fetched_at, "test"),
        ]
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 12),
        now=datetime(2026, 5, 12, 16, 0, 0),
    )

    assert snapshot["sectors"] == []
    assert snapshot["themes"] == []
    assert snapshot["category_contract"] == {
        "mapping_basis": "dated_snapshot",
        "dated_snapshots_available": True,
        "snapshot_dates": ["2026-05-08"],
        "notice": "업종/테마는 선택 날짜 이하의 가장 가까운 저장 스냅샷 기준입니다. 실시간 갱신이나 확정 판단은 포함하지 않습니다.",
    }


def test_web_view_backtest_observation_snapshot_is_public_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_id="backtest-1",
                identity_key="backtest-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=120_000,
                opinion_normalized="buy",
                source_id="backtest-2",
                identity_key="backtest-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                volume=10_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                volume=12_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_volume=500,
                net_buy_amount=1_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_amount=1_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    payload = cli_module.build_web_view_backtest_observation_snapshot(
        config,
        repository,
        business_date=business_date,
        mention_threshold=2,
        limit=5,
    )

    assert payload["surface"] == "web-view"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is False
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["business_date"] == "2026-05-08"
    assert payload["mention_threshold"] == 2
    assert payload["available"] is True
    row = payload["rows"][0]
    assert row["stock_code"] == "005930"
    assert row["report_summary"]["report_count"] == 2
    assert row["reaction_windows"][0]["horizon_days"] == 1
    assert row["reaction_windows"][0]["horizon_date"] == "2026-05-11"
    assert row["reaction_windows"][0]["close_return_percent"] == 10.0
    assert row["target_observation"]["target_gap_min_percent"] == 0.0
    assert row["target_observation"]["target_gap_max_percent"] == 20.0
    assert row["target_observation"]["validation_available"] is False
    assert row["target_observation"]["validation_window_days"] is None
    assert row["target_observation"]["hit_min_horizon_days"] is None
    assert row["target_observation"]["hit_max_horizon_days"] is None
    assert row["target_observation"]["max_progress_to_max_percent"] is None
    assert row["target_observation"]["validation_notice"] == "baseline_inside_target_range"
    assert row["stock_flow_observation"]["foreign_net_buy_volume"] == 500
    assert row["net_buy_top_observation"]["foreign_top_rank"] == 1
    assert row["evidence_notes"] == [
        "리포트 2건",
        "목표가 있음",
        "당일 수급 있음",
        "외국인 순매수 상위 포함",
        "D+1 반응 가능",
        "D+5/D+10/D+20 대기",
    ]
    assert "candidate_score" not in json.dumps(payload, ensure_ascii=False)
    assert "candidate_reasons" not in json.dumps(payload, ensure_ascii=False)
    assert "prototype_value" not in json.dumps(payload, ensure_ascii=False)
    _assert_public_safe_payload(payload)


def test_web_view_backtest_observation_keeps_target_available_when_only_base_market_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 15)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성화재",
                stock_code="000810",
                title="실적 점검",
                broker_name="신한투자증권",
                published_at=datetime(2026, 5, 15, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 15, 9, 5, 0),
                target_price_value=600_000,
                opinion_normalized="buy",
                source_id="backtest-missing-base-1",
                identity_key="backtest-missing-base-1",
            ),
            Report(
                stock_name="삼성화재",
                stock_code="000810",
                title="목표가 상향",
                broker_name="키움증권",
                published_at=datetime(2026, 5, 15, 10, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 15, 10, 5, 0),
                target_price_value=750_000,
                opinion_normalized="buy",
                source_id="backtest-missing-base-2",
                identity_key="backtest-missing-base-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    payload = cli_module.build_web_view_backtest_observation_snapshot(
        config,
        repository,
        business_date=business_date,
        mention_threshold=2,
        limit=5,
    )

    row = payload["rows"][0]
    assert row["report_summary"]["target_price_min"] == 600_000
    assert row["report_summary"]["target_price_max"] == 750_000
    assert row["target_observation"]["unavailable_reason"] == "missing_base_close_price"
    assert "목표가 있음" in row["evidence_notes"]
    assert "목표가 없음" not in row["evidence_notes"]
    assert "KRX 기준가 대기" in row["evidence_notes"]


def test_web_view_daily_snapshot_uses_public_label_for_missing_sector_mapping(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="미분류종목",
                stock_code="123456",
                title="신규 리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/1",
                source_id="missing-sector-1",
                identity_key="missing-sector-identity-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    daily = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 16, 0, 0),
    )
    detail = cli_module.build_web_view_category_detail_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        category_type="sector",
        category_name="N/A",
        now=datetime(2026, 5, 8, 16, 0, 0),
    )
    trend = cli_module.build_web_view_category_trend_snapshot(
        config,
        repository,
        category_type="sector",
        category_name="N/A",
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert daily["sectors"][0]["sector_name"] == "N/A"
    assert daily["sectors"][0]["sector_display_name"] == "업종 미확인"
    assert detail["category_name"] == "N/A"
    assert detail["category_display_name"] == "업종 미확인"
    assert trend["category_name"] == "N/A"
    assert trend["category_display_name"] == "업종 미확인"


def test_web_view_daily_toss_context_is_exact_date_and_does_not_fallback_to_latest(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 7, 9, 0, 0),
                business_date=date(2026, 5, 7),
                collected_at=datetime(2026, 5, 7, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="identity-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 7))
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=101_000,
                change_percent=2.0,
                volume=20_000,
                turnover=900,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="069500",
                etf_name="KODEX 200",
                close_price=40_000,
                change_percent=0.5,
                nav=40_100.5,
                volume=5_000,
                turnover=300,
                underlying_index_name="코스피 200",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 5, 8),
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                close_index=3000.1,
                change_percent=0.8,
                volume=100,
                turnover=1000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    missing_context_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 7),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )
    exact_context_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert missing_context_snapshot["toss_context"]["available"] is False
    assert missing_context_snapshot["toss_context"]["snapshot_date"] is None
    assert missing_context_snapshot["toss_context"]["top_kospi_by_turnover"] == []
    assert missing_context_snapshot["stocks"][0]["market_reference"] is None
    missing_freshness = {
        item["key"]: item for item in missing_context_snapshot["source_freshness_summary"]["items"]
    }
    assert missing_freshness["reports"]["status"] == "exact"
    assert missing_freshness["reports"]["reference_date"] == "2026-05-07"
    assert missing_freshness["toss_market"]["status"] == "missing"
    assert missing_freshness["toss_market"]["reference_date"] is None
    assert missing_freshness["toss_etf"]["status"] == "missing"
    assert missing_freshness["investor_flow"]["status"] == "missing"
    assert missing_freshness["toss_openapi"]["status"] == "disabled"
    assert "최신 날짜 값으로 대체하지 않습니다" in missing_context_snapshot["toss_context"]["notice"]

    context = exact_context_snapshot["toss_context"]
    assert context["available"] is True
    assert context["source"] == "toss_openapi"
    assert context["snapshot_date"] == "2026-05-08"
    assert context["top_kospi_by_turnover"][0]["stock_code"] == "005930"
    assert context["top_etfs_by_turnover"][0] == {
        "business_date": "2026-05-08",
        "etf_code": "069500",
        "etf_name": "KODEX 200",
        "close_price": 40_000,
        "change_percent": 0.5,
        "nav": 40_100.5,
        "volume": 5_000,
        "turnover": 300,
        "underlying_index_name": "코스피 200",
        "evidence_label": "거래대금 300원 · NAV 40,100.5 · 기초지수 코스피 200",
        "rotation_reference": "저장 ETF 거래대금/NAV/기초지수 기준",
    }
    assert context["indices"][0]["index_name"] == "코스피"
    exact_freshness = {
        item["key"]: item for item in exact_context_snapshot["source_freshness_summary"]["items"]
    }
    assert exact_freshness["toss_market"]["status"] == "exact"
    assert exact_freshness["toss_market"]["reference_date"] == "2026-05-08"
    assert exact_freshness["toss_etf"]["status"] == "exact"
    assert exact_freshness["investor_flow"]["status"] == "missing"
    assert exact_freshness["toss_openapi"]["live_fetch"] is False
    assert "scheduler_tasks" not in context
    assert "worker_states" not in context
    assert "db_path" not in context
    _assert_public_safe_payload(missing_context_snapshot)
    _assert_public_safe_payload(exact_context_snapshot)


def test_web_view_source_freshness_marks_toss_configured_without_live_quote(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    (tmp_path / ".env.toss-openapi").write_text(
        "\n".join(
            [
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=test-client",
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET=test-secret",
                "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true",
            ]
        ),
        encoding="utf-8",
    )
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="toss-ready-env-1",
                identity_key="toss-ready-env-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    snapshot = cli_module.build_web_view_daily_snapshot(config, repository, business_date=business_date)

    source_freshness_items = {
        item["key"]: item for item in snapshot["source_freshness_summary"]["items"]
    }
    assert source_freshness_items["toss_openapi"]["status"] == "configured"
    assert source_freshness_items["toss_openapi"]["available"] is False
    assert source_freshness_items["toss_openapi"]["live_fetch"] is False
    assert source_freshness_items["toss_openapi"]["affects_ordering"] is False


def test_web_view_toss_priority_quotes_route_uses_server_derived_top_two_only(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 AI 반도체 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="toss-route-1",
                identity_key="toss-route-1",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="SK하이닉스 HBM 점검",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 9, 30, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 35, 0),
                source_id="toss-route-2",
                identity_key="toss-route-2",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 두 번째 점검",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 9, 40, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 45, 0),
                source_id="toss-route-3",
                identity_key="toss-route-3",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="SK하이닉스 두 번째 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 50, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 55, 0),
                source_id="toss-route-4",
                identity_key="toss-route-4",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_quote(stock_code: str, **_kwargs) -> cli_module.StockQuoteSnapshot:
        return cli_module.StockQuoteSnapshot(
            stock_code=stock_code,
            stock_name={"005930": "삼성전자", "000660": "SK하이닉스"}[stock_code],
            sector_code=None,
            sector_name=None,
            current_price=1000,
            market_status="OPEN",
            trade_time=datetime(2026, 5, 8, 10, 0, 0),
            prev_close_price=990,
            prev_change_rate=1.01,
            trade_amount=123_000_000,
        )

    monkeypatch.setattr(cli_module, "fetch_stock_quote_snapshot", fake_quote)

    class FakeTossProvider:
        configured = True

        def __init__(self) -> None:
            self.calls: list[tuple[date, tuple[str, ...], bool]] = []

        def get_quotes(
            self,
            *,
            priority_date: date,
            symbols: tuple[str, ...],
            include_investor_trading: bool = False,
        ) -> dict[str, object]:
            self.calls.append((priority_date, symbols, include_investor_trading))
            return {
                "surface": "web-view-toss-priority-quotes",
                "read_only": True,
                "configured": True,
                "live_fetch": True,
                "writes_db": False,
                "sends_telegram": False,
                "registers_scheduler": False,
                "affects_ordering": False,
                "priority_date": priority_date.isoformat(),
                "symbols": list(symbols),
                "quotes": [{"symbol": symbol, "lastPrice": 1000, "currency": "KRW"} for symbol in symbols],
                "investor_trading": {
                    "reference_date": priority_date.isoformat(),
                    "available": True,
                    "items": [
                        {
                            "symbol": symbol,
                            "business_date": priority_date.isoformat(),
                            "updated_at": "2026-05-08T10:15:00+09:00",
                            "foreigner_net_buy_volume": 60,
                            "institution_net_buy_volume": -20,
                        }
                        for symbol in symbols
                    ],
                },
                "cache": "miss",
            }

    provider = FakeTossProvider()
    server = cli_module.create_web_view_server(
        config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=5,
        toss_quote_provider=provider,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base_url + "/api/daily/2026-05-08", timeout=5) as response:
            assert response.status == 200
            json.loads(response.read().decode("utf-8"))

        def fail_candidate_rebuild(*_args, **_kwargs) -> dict[str, object]:
            raise AssertionError("priority quote routes must reuse cached daily candidates")

        monkeypatch.setattr(cli_module, "build_web_view_candidate_evidence_snapshot", fail_candidate_rebuild)
        with urllib.request.urlopen(
            base_url + "/api/toss-priority-quotes?date=2026-05-08&symbols=999999",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(
            base_url + "/api/priority-current-quotes?date=2026-05-08",
            timeout=5,
        ) as response:
            current_payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert payload["surface"] == "web-view-toss-priority-quotes"
    assert payload["read_only"] is True
    assert payload["writes_db"] is False
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["affects_ordering"] is False
    assert payload["derived_from"] == "web_view_candidate_evidence_top_2"
    assert provider.calls
    assert provider.calls[0][0] == business_date
    assert set(provider.calls[0][1]) == {"005930", "000660"}
    assert provider.calls[0][2] is True
    assert "999999" not in provider.calls[0][1]
    assert payload["investor_trading"] == {
        "reference_date": "2026-05-08",
        "available": True,
        "items": [
            {
                "symbol": "005930",
                "business_date": "2026-05-08",
                "updated_at": "2026-05-08T10:15:00+09:00",
                "foreigner_net_buy_volume": 60,
                "institution_net_buy_volume": -20,
            },
            {
                "symbol": "000660",
                "business_date": "2026-05-08",
                "updated_at": "2026-05-08T10:15:00+09:00",
                "foreigner_net_buy_volume": 60,
                "institution_net_buy_volume": -20,
            },
        ],
    }
    assert current_payload["surface"] == "web-view-priority-current-quotes"
    assert current_payload["read_only"] is True
    assert current_payload["live_fetch"] is True
    assert current_payload["writes_db"] is False
    assert [item["stock_code"] for item in current_payload["items"]] == ["005930", "000660"]
    _assert_public_safe_payload(current_payload)


def test_web_view_toss_market_context_route_uses_server_derived_top_two_only(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 10)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 보고서",
                broker_name="NH투자증권",
                published_at=datetime(2026, 7, 10, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 7, 10, 9, 1, 0),
                source_id="toss-market-route-1",
                identity_key="toss-market-route-1",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="SK하이닉스 보고서",
                broker_name="KB증권",
                published_at=datetime(2026, 7, 10, 9, 2, 0),
                business_date=business_date,
                collected_at=datetime(2026, 7, 10, 9, 3, 0),
                source_id="toss-market-route-2",
                identity_key="toss-market-route-2",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 추가 보고서",
                broker_name="KB증권",
                published_at=datetime(2026, 7, 10, 9, 4, 0),
                business_date=business_date,
                collected_at=datetime(2026, 7, 10, 9, 5, 0),
                source_id="toss-market-route-3",
                identity_key="toss-market-route-3",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="SK하이닉스 추가 보고서",
                broker_name="NH투자증권",
                published_at=datetime(2026, 7, 10, 9, 6, 0),
                business_date=business_date,
                collected_at=datetime(2026, 7, 10, 9, 7, 0),
                source_id="toss-market-route-4",
                identity_key="toss-market-route-4",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    class FakeTossProvider:
        configured = True

        def get_quotes(self, **_kwargs) -> dict[str, object]:
            return {"configured": True, "live_fetch": False, "quotes": [], "cache": "disabled"}

        def get_market_context(self, *, reference_date: date, priority_symbols: tuple[str, ...]) -> dict[str, object]:
            assert reference_date == date(2026, 7, 10)
            self.symbols = priority_symbols
            return {
                "surface": "web-view-toss-market-context",
                "read_only": True,
                "configured": True,
                "live_fetch": True,
                "writes_db": False,
                "sends_telegram": False,
                "registers_scheduler": False,
                "affects_ordering": False,
                "reference_date": reference_date.isoformat(),
                "ranked_at": "2026-07-10T09:15:00+09:00",
                "rankings": [{"rank": 1, "symbol": "005930", "tradingAmount": 1000}],
                "market_prices": [{"symbol": "KOSPI", "lastPrice": "3120.45"}],
                "priority_overlap_symbols": ["005930"],
                "investor_flow": {"KOSPI": {"date": "2026-07-10"}, "KOSDAQ": {"date": "2026-07-10"}},
            }

    provider = FakeTossProvider()
    server = cli_module.create_web_view_server(
        config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=5,
        toss_quote_provider=provider,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(
            base_url + "/api/toss-market-context?date=2026-07-10&symbols=999999",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert payload["derived_from"] == "web_view_candidate_evidence_top_2"
    assert payload["priority_overlap_symbols"] == ["005930"]
    assert provider.symbols == ("005930", "000660")
    _assert_public_safe_payload(payload)
def test_web_view_toss_market_context_rejects_when_latest_date_is_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    class FakeTossProvider:
        configured = True
        calls = 0

        def get_market_context(self, *, reference_date: date, priority_symbols: tuple[str, ...]) -> dict[str, object]:
            self.calls += 1
            raise AssertionError("must not call provider without a stored latest date")

    provider = FakeTossProvider()
    server = cli_module.create_web_view_server(
        config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=5,
        toss_quote_provider=provider,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            urllib.request.urlopen(base_url + "/api/toss-market-context?date=2026-07-10", timeout=5)
        except urllib.error.HTTPError as exc:
            status = exc.code
            payload = json.loads(exc.read().decode("utf-8"))
        else:
            status = 200
            payload = {}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status == 409
    assert payload["latest_business_date"] is None
    assert payload["reason"] == "latest_business_date_unavailable"
    assert provider.calls == 0


def test_web_view_daily_top_two_candles_use_selected_date_and_allowed_window(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    selected_date = date(2026, 7, 10)
    later_date = date(2026, 7, 13)
    repository.insert_reports(
        [
            Report(
                stock_name=name,
                stock_code=code,
                title=f"{name} report {suffix}",
                broker_name=broker,
                published_at=datetime(2026, 7, 10, 9, minute, 0),
                business_date=selected_date,
                collected_at=datetime(2026, 7, 10, 9, minute + 1, 0),
                source_id=f"daily-candle-{code}-{suffix}",
                identity_key=f"daily-candle-{code}-{suffix}",
            )
            for name, code, broker, minute, suffix in (
                ("삼성전자", "005930", "NH투자증권", 0, 1),
                ("SK하이닉스", "000660", "KB증권", 2, 1),
                ("삼성전자", "005930", "KB증권", 4, 2),
                ("SK하이닉스", "000660", "NH투자증권", 6, 2),
            )
        ]
        + [
            Report(
                stock_name="NAVER",
                stock_code="035420",
                title="NAVER later report",
                broker_name="신한투자증권",
                published_at=datetime(2026, 7, 13, 9, 0, 0),
                business_date=later_date,
                collected_at=datetime(2026, 7, 13, 9, 1, 0),
                source_id="daily-candle-later",
                identity_key="daily-candle-later",
            )
        ]
    )
    repository.rebuild_daily_summaries(selected_date)
    repository.rebuild_daily_summaries(later_date)

    class FakeTossProvider:
        configured = True
        calls: list[tuple[tuple[str, ...], datetime, int]] = []
        raise_error = False

        def get_priority_stock_daily_candles(
            self,
            *,
            priority_symbols: tuple[str, ...],
            before: datetime,
            count: int,
        ) -> dict[str, object]:
            self.calls.append((priority_symbols, before, count))
            if self.raise_error:
                error = RuntimeError("safe provider error")
                error.status_code = 404
                error.provider_code = "symbol-not-found"
                raise error
            return {
                "surface": "toss-priority-stock-daily-candles",
                "read_only": True,
                "configured": True,
                "live_fetch": True,
                "interval": "1d",
                "requested_count": count,
                "adjusted": True,
                "fetched_at": "2026-07-13T10:00:00+09:00",
                "items": [
                    {
                        "symbol": symbol,
                        "candles": [
                            {
                                "timestamp": "2026-07-10T00:00:00+09:00",
                                "openPrice": "70000",
                                "highPrice": "70100",
                                "lowPrice": "69900",
                                "closePrice": "70050",
                                "volume": "100",
                            },
                            {
                                "timestamp": "2026-07-13T00:00:00+09:00",
                                "openPrice": "70100",
                                "highPrice": "70200",
                                "lowPrice": "70050",
                                "closePrice": "70150",
                                "volume": "120",
                            },
                        ],
                        "next_before": None,
                    }
                    for symbol in priority_symbols
                ],
                "rate_limit": {},
            }

    provider = FakeTossProvider()
    server = cli_module.create_web_view_server(
        config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=5,
        toss_quote_provider=provider,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(
            base_url + "/api/toss-priority-daily-candles?date=2026-07-10&days=90&symbols=999999",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        try:
            urllib.request.urlopen(base_url + "/api/toss-priority-daily-candles?date=2026-07-10&days=60", timeout=5)
        except urllib.error.HTTPError as exc:
            invalid_window_status = exc.code
        else:
            invalid_window_status = 200
        provider.raise_error = True
        try:
            urllib.request.urlopen(base_url + "/api/toss-priority-daily-candles?date=2026-07-10&days=90", timeout=5)
        except urllib.error.HTTPError as exc:
            upstream_failure_status = exc.code
            upstream_failure_payload = json.loads(exc.read().decode("utf-8"))
        else:
            upstream_failure_status = 200
            upstream_failure_payload = {}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert payload["business_date"] == selected_date.isoformat()
    assert payload["requested_count"] == 90
    assert payload["adjusted"] is True
    assert [item["symbol"] for item in payload["items"]] == ["005930", "000660"]
    assert all(
        candle["timestamp"].startswith("2026-07-10")
        for item in payload["items"]
        for candle in item["candles"]
    )
    assert all(item["excluded_candle_count"] == 1 for item in payload["items"])
    assert len(provider.calls) == 2
    assert provider.calls[0][0] == ("005930", "000660")
    assert provider.calls[0][1].isoformat() == "2026-07-10T23:59:59+09:00"
    assert provider.calls[0][2] == 90
    assert invalid_window_status == 400
    assert upstream_failure_status == 502
    assert upstream_failure_payload["upstream_status"] == 404
    assert upstream_failure_payload["provider_code"] == "symbol-not-found"
    _assert_public_safe_payload(payload)
    _assert_public_safe_payload(upstream_failure_payload)


def test_web_view_main_has_toss_market_context_panel() -> None:
    html = cli_module._render_web_view_html()
    market_context_body = html.split("function renderTossMarketContext(data)", 1)[1].split(
        "async function loadTossMarketContext", 1
    )[0]
    briefing_body = html.split("function renderDailyBriefing(data)", 1)[1].split(
        "function renderSourceFreshnessSummary", 1
    )[0]
    active_tab_body = html.split("async function loadTabDataForActiveView(date)", 1)[1].split(
        "async function loadDaily(date, options = {})", 1
    )[0]

    assert 'id="toss-market-context"' in html
    assert "/api/toss-market-context" in html
    assert "지수와 시장 수급을 확인 중입니다." in html
    assert "당일 시장 · 수급" in html
    assert 'id="toss-market-context" class="intraday-overlap-panel" aria-live="polite"' in html
    assert "전일 Toss 저장값/수급/ETF는 참고 영역입니다." not in html
    assert "후보 수급 [12009]은 관찰 후보·종목 상세에서 확인" not in html
    assert "data.stock_names" not in market_context_body
    assert "data.etf_symbols" not in market_context_body
    assert "data.market_price_changes" in market_context_body
    assert '["개인", record.individual]' in market_context_body
    assert 'data.cache === "stale"' in market_context_body
    assert '["hit", "shared"].includes(data.cache)' in market_context_body
    assert "Toss 거래대금 상위 Top10" not in market_context_body
    assert "Toss 거래대금 상위 ETF Top5" not in market_context_body
    assert "시장 수급 · 잠정" in market_context_body
    assert 'id="main-market-context-card" data-view-panel="main"' in html
    assert 'id="toss-market-refresh"' in html
    assert 'id="market-reference-card" data-view-panel="main"' in html
    assert 'data-view-tab="market"' not in html
    assert 'data-view-tab="rotation"' not in html
    assert "toss-priority-candles" not in html
    assert 'id="top2-daily-range"' in html
    assert 'id="top2-indicator-series"' in html
    assert 'id="newbby-indicator-refresh"' in html
    assert '<option value="30">30거래일</option>' in html
    assert '<option value="90" selected>90거래일</option>' in html
    assert '<option value="180">180거래일</option>' in html
    assert "function renderPriorityIndicatorPriceChart" in html
    assert "function renderPriorityIndicatorAuxChart" in html
    assert "SMA 20/60/120/200" not in html
    assert "const colors = {sma20:" in html
    assert "선택 날짜 Main Top2의 수정주가 일봉과 기술 지표를 조회합니다." in html
    assert "RSI 14" in html
    assert "MACD 12·26·9" in html
    assert "/api/priority-indicators?date=" in html
    assert "loadTopTwoDailyCandles" not in active_tab_body
    assert 'loadNewbbyIndicatorSnapshot(selectedDate);' in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in html
    assert "moodCard.headline" in briefing_body
    assert "priorityNames" not in briefing_body
    assert "priorityEvidenceRows" in briefing_body
    assert "row.why_notable" in briefing_body
    assert "row.missing_information" in briefing_body
    assert "관찰 근거" in briefing_body
    assert "확인 공백" in briefing_body
    assert "2건 이상" in briefing_body
    assert "freshnessItems" not in briefing_body
    assert "loadTossMarketContext" not in active_tab_body
    assert 'loadTossMarketContext(selectedDate);' in html


def test_web_view_html_labels_top_two_toss_flow_as_unstored_query_reference() -> None:
    html = cli_module._render_web_view_html()
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function updateTossPriorityRefreshButton()", 1
    )[0]

    assert "Toss 조회 수급 참고(미저장)" not in top_two_body
    assert "Toss 당일 수급" not in top_two_body
    assert '<strong>당일 수급</strong>' in top_two_body
    assert 'class="top-two-evidence-details"' in top_two_body
    assert "loadTossPriorityQuotes(tossPriorityDate)" in html


def test_web_view_main_separates_close_reassessment_from_regular_session_top_two() -> None:
    html = cli_module._render_web_view_html()
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function topTwoMissingEvidenceLine", 1
    )[0]

    assert "종가 재평가" in top_two_body
    assert "Toss 종가" in top_two_body
    assert "현재 근거 부족" not in top_two_body


def test_web_view_stock_detail_missing_toss_flow_names_selected_date_stored_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    context = cli_module._build_web_view_stock_investor_flow_context(
        repository,
        date(2026, 8, 21),
        "388210",
    )

    assert context["available"] is False
    assert context["data_scope"] == "stored_toss_close_priority_flow"
    assert context["live_fetch"] is False
    assert context["notice"] == "선택일 Toss 20:00 저장 우선 후보 수급 데이터가 없습니다."


def test_web_view_candidate_evidence_uses_stored_toss_2000_baseline(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 18)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 AI 반도체 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 6, 18, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 18, 9, 5, 0),
                source_id="toss-baseline-view-1",
                identity_key="toss-baseline-view-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.save_toss_priority_quote_baselines(
        [
            TossPriorityQuoteBaseline(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                baseline_time="20:00",
                last_price=72000,
                currency="KRW",
                source="toss_openapi",
                fetched_at=datetime(2026, 6, 18, 20, 0, 4),
            )
        ]
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    reference = snapshot["rows"][0]["toss_baseline_reference"]
    assert reference == {
        "available": True,
        "source": "toss_openapi",
        "read_only": True,
        "live_fetch": False,
        "writes_db": False,
        "baseline_time": "20:00",
        "reference_time": "2026-06-18T20:00:04",
        "last_price": 72000,
        "currency": "KRW",
        "affects_ordering": False,
        "notice": "Toss 20:00 기준 저장값",
    }
    assert snapshot["rows"][0]["selected"] is False
    assert "intraday_reference" not in snapshot["rows"][0]
    _assert_public_safe_payload(snapshot)


def test_web_view_candidate_evidence_exposes_value_context_from_stored_references(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="005930",
                title="Alpha report",
                broker_name="NH",
                published_at=datetime(2026, 7, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 7, 2, 9, 5, 0),
                source_id="value-context-report",
                identity_key="value-context-report",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="Alpha",
                market="KOSPI",
                close_price=72_000,
                change_percent=1.2,
                volume=1_000_000,
                turnover=500_000_000_000,
                fetched_at=datetime(2026, 7, 2, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="Alpha",
                market="STK",
                investor_type="외국인",
                net_buy_volume=100,
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 7, 2, 20, 1, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.save_toss_priority_quote_baselines(
        [
            TossPriorityQuoteBaseline(
                business_date=business_date,
                stock_code="005930",
                stock_name="Alpha",
                baseline_time="20:00",
                last_price=72_500,
                currency="KRW",
                source="toss_openapi",
                fetched_at=datetime(2026, 7, 2, 20, 0, 4),
            )
        ]
    )
    run = _web_view_news_run(
        run_id="value-context-news",
        target_date=business_date,
        stock_name="Alpha",
        stock_code="005930",
    )
    repository.save_news_intelligence_observation(run, [])

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    context = snapshot["rows"][0]["value_context"]
    assert context["report_reference_date"] == "2026-07-02"
    assert context["toss_reference_date"] == "2026-07-02"
    assert "krx_reference_date" not in context
    assert context["turnover_reference_date"] == "2026-07-02"
    assert context["current_price_reference_time"] == "2026-07-02T20:00:04"
    assert context["current_price_basis"] == "20:00 stored"
    assert context["investor_flow_reference_date"] == "2026-07-02"
    assert context["news_collection_status"] == "stored_no_match"
    assert context["missing_labels"] == []
    assert snapshot["data_scope"] == "stored_report_toss_evidence"
    _assert_public_safe_payload(snapshot)
    _assert_candidate_payload_has_no_internal_sort_fields(snapshot)
    _assert_public_safe_payload(json.loads(json.dumps(snapshot)))

    daily_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=datetime(2026, 7, 2, 21, 0, 0),
    )
    daily_candidates = daily_snapshot["priority_candidate_evidence"]
    assert daily_candidates["data_scope"] == "stored_report_toss_evidence"
    daily_context = daily_candidates["rows"][0]["value_context"]
    assert daily_context["toss_reference_date"] == "2026-07-02"
    assert "krx_reference_date" not in daily_context
    _assert_public_safe_payload(daily_candidates)
    _assert_candidate_payload_has_no_internal_sort_fields(daily_candidates)


def test_web_view_stock_search_uses_cached_toss_stock_universe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.upsert_toss_stock_universe_cache(
        [
            TossStockUniverseEntry(
                business_date=business_date,
                market="KOSDAQ",
                stock_code="123456",
                stock_name="테스트바이오",
                security_type="STOCK",
                is_common_share=True,
                isin_code="KR7123456000",
                fetched_at=datetime(2026, 6, 2, 20, 5),
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_search_snapshot(
        config,
        repository,
        business_date=business_date,
        query="테스트바이오",
        now=datetime(2026, 6, 2, 20, 10),
    )

    assert snapshot["available"] is True
    assert snapshot["items"][0]["stock_code"] == "123456"
    assert snapshot["items"][0]["stock_name"] == "테스트바이오"
    assert snapshot["items"][0]["market"] == "KOSDAQ"
    assert snapshot["items"][0]["has_selected_date_report"] is False
    assert snapshot["stock_universe_reference_date"] == business_date.isoformat()
    _assert_public_safe_payload(snapshot)

    repository.upsert_toss_stock_universe_cache(
        [
            TossStockUniverseEntry(
                business_date=date(2026, 6, 3),
                market="KOSPI",
                stock_code="234567",
                stock_name="다음날상장",
                security_type="STOCK",
                is_common_share=True,
                isin_code="KR7234567000",
                fetched_at=datetime(2026, 6, 3, 20, 5),
            )
        ]
    )
    historical_snapshot = cli_module.build_web_view_stock_search_snapshot(
        config,
        repository,
        business_date=business_date,
        query="테스트바이오",
        now=datetime(2026, 6, 3, 20, 10),
    )
    assert historical_snapshot["available"] is False
    assert historical_snapshot["stock_universe_reference_date"] is None


def test_web_view_news_observation_keeps_unique_direct_evidence_after_later_empty_collection(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    report = Report(
        business_date=business_date,
        stock_name="삼성전자",
        stock_code="005930",
        title="삼성전자 보고서",
        broker_name="테스트증권",
        published_at=datetime(2026, 6, 2, 9, 0, 0),
        collected_at=datetime(2026, 6, 2, 9, 1, 0),
        source_id="news-dedupe-report",
        identity_key="news-dedupe-report",
    )
    repository.insert_reports([report])
    repository.rebuild_daily_summaries(business_date)

    first_run = _web_view_news_run(run_id="news-direct-first")
    repeated_run = replace(
        _web_view_news_run(run_id="news-direct-repeat"),
        created_at=datetime(2026, 6, 2, 10, 5, 0),
    )
    later_empty_run = replace(
        _web_view_news_run(run_id="news-later-empty"),
        matched_count=0,
        created_at=datetime(2026, 6, 2, 15, 15, 0),
    )
    evidence = _web_view_news_evidence(run_id=first_run.run_id, evidence_key="same-direct-news")
    repository.save_news_intelligence_observation(first_run, [evidence])
    repository.save_news_intelligence_observation(
        repeated_run,
        [replace(evidence, run_id=repeated_run.run_id, created_at=repeated_run.created_at)],
    )
    repository.save_news_intelligence_observation(later_empty_run, [])

    daily = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=datetime(2026, 6, 2, 15, 20, 0),
    )
    candidates = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    summary = daily["news_observation_summary"]
    assert summary["direct_count"] == 1
    assert summary["candidate_overlap_names"] == ["삼성전자"]
    assert summary["items"][0]["display_label"] == "종목 뉴스 매칭"
    assert summary["items"][0]["direct_count"] == 1
    assert summary["items"][0]["collection_run_count"] == 3
    assert summary["items"][0]["latest_collection_status"] == "no_match"
    assert summary["items"][0]["daily_evidence_retained"] is True
    assert candidates["rows"][0]["news_observation_badge"]["direct_count"] == 1
    assert candidates["rows"][0]["news_observation_badge"]["display_label"] == "종목 뉴스 매칭"
    assert candidates["rows"][0]["news_observation_badge"]["collection_run_count"] == 3
    assert candidates["rows"][0]["news_observation_badge"]["latest_collection_status"] == "no_match"
    assert candidates["rows"][0]["news_observation_badge"]["daily_evidence_retained"] is True


def test_web_view_intraday_overlay_populates_priority_quote_when_market_top_has_no_overlap(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 20)
    now = datetime(2026, 5, 20, 12, 1, 0)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="웹뷰후보",
                stock_code="000001",
                title="웹뷰후보 보고서",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                source_id="priority-quote-report",
                identity_key="priority-quote-report",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        cli_module,
        "fetch_stock_quote_snapshot",
        lambda *_args, **_kwargs: cli_module.StockQuoteSnapshot(
            stock_code="000001",
            stock_name="웹뷰후보",
            sector_code=None,
            sector_name=None,
            current_price=10_500,
            market_status="OPEN",
            trade_time=now,
            prev_close_price=10_000,
            prev_change_price=500,
            prev_change_rate=5.0,
            trade_amount=90_000_000_000,
            trade_volume=1_200_000,
        ),
    )
    base_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=now,
    )

    snapshot = cli_module._overlay_web_view_daily_intraday_market_top(
        config,
        repository,
        base_snapshot,
        business_date=business_date,
        limit=20,
        page_size=20,
    )

    commentary = snapshot["market_commentary"]
    assert commentary["intraday_market_top_reference"]["items"] == []
    assert commentary["intraday_quote_reference"]["live_fetch"] is True
    assert commentary["intraday_quote_reference"]["items"] == [
        {
            "stock_name": "웹뷰후보",
            "stock_code": "000001",
            "mention_count": 1,
            "current_price": 10_500,
            "prev_close_price": 10_000,
            "change_price": 500,
            "change_percent": 5.0,
            "trade_amount": 90_000_000_000,
            "trade_volume": 1_200_000,
            "market_status": "OPEN",
            "trade_time": "2026-05-20T12:01:00",
            "sector_name": None,
            "resolution_source": "summary_stock_code",
        }
    ]


def test_stock_flow_reference_keeps_each_priority_candidate_reference_date_visible(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name=stock_name,
                stock_code=stock_code,
                title=f"{stock_name} 보고서",
                broker_name="테스트증권",
                published_at=datetime(2026, 6, 2, 9, index, 0),
                collected_at=datetime(2026, 6, 2, 9, index, 30),
                source_id=f"flow-date-{stock_code}",
                identity_key=f"flow-date-{stock_code}",
            )
            for index, (stock_code, stock_name) in enumerate((("000001", "후보A"), ("000002", "후보B")))
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=flow_date,
                stock_code=stock_code,
                stock_name=stock_name,
                investor_type=investor_type,
                net_buy_volume=amount,
                net_buy_amount=amount,
                fetched_at=datetime(2026, 6, 2, 15, 0, 0),
                source="toss_openapi",
            )
            for flow_date, stock_code, stock_name, investor_type, amount in (
                (date(2026, 6, 2), "000001", "후보A", "외국인", 100_000_000),
                (date(2026, 6, 2), "000001", "후보A", "기관합계", 50_000_000),
                (date(2026, 6, 1), "000002", "후보B", "외국인", -20_000_000),
                (date(2026, 6, 1), "000002", "후보B", "기관합계", -10_000_000),
            )
        ]
    )
    summaries = repository.list_daily_summaries(business_date)

    lines = cli_module._build_stock_flow_briefing_reference_lines(
        repository,
        business_date,
        summaries=summaries,
        limit=2,
        priority_stock_codes=("000001", "000002"),
    )
    freshness = cli_module._build_stock_flow_source_freshness_item(
        repository,
        business_date,
        summaries=summaries,
        priority_stock_codes=("000001", "000002"),
    )

    assert lines[0] == "수급 참고 · Toss 우선 후보 저장값 / 기준일 혼합"
    assert lines[1].startswith("- [26.06.02] 후보A")
    assert lines[2].startswith("- [26.06.01] 후보B")
    assert freshness is not None
    assert freshness["status"] == "partial"
    assert freshness["reference_dates"] == ["2026-06-02", "2026-06-01"]


def test_web_view_stock_detail_includes_stored_target_hit_window(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha target update",
                broker_name="Broker",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 2, 9, 5, 0),
                target_price_value=130_000,
                source_id="target-window-report",
                identity_key="target-window-report",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 6, day),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=close_price,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, day, 18, 0, 0),
            )
            for day, close_price in ((2, 100_000), (3, 120_000), (4, 130_000))
        ]
        + [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=100_000,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 2, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="000001",
        now=datetime(2026, 6, 4, 18, 0, 0),
    )

    progress = snapshot["target_price_progress"]
    assert progress["validation_available"] is True
    assert progress["hit_min_horizon_days"] == 2
    assert progress["hit_max_horizon_days"] == 2
    _assert_public_safe_payload(snapshot)


def test_web_view_target_hit_window_uses_selected_report_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    first_date = date(2026, 6, 2)
    selected_date = date(2026, 6, 4)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha first target",
                broker_name="Broker",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=first_date,
                collected_at=datetime(2026, 6, 2, 9, 5, 0),
                target_price_value=130_000,
                source_id="target-first-report",
                identity_key="target-first-report",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha revised target",
                broker_name="Broker",
                published_at=datetime(2026, 6, 4, 9, 0, 0),
                business_date=selected_date,
                collected_at=datetime(2026, 6, 4, 9, 5, 0),
                target_price_value=150_000,
                source_id="target-selected-report",
                identity_key="target-selected-report",
            ),
        ]
    )
    repository.rebuild_daily_summaries(first_date)
    repository.rebuild_daily_summaries(selected_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 6, day),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=close_price,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, day, 18, 0, 0),
            )
            for day, close_price in ((2, 100_000), (4, 130_000), (5, 150_000))
        ]
        + [
            StockMarketDailySnapshot(
                business_date=selected_date,
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=130_000,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 4, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=selected_date,
        stock_code="000001",
        now=datetime(2026, 6, 5, 18, 0, 0),
    )

    progress = snapshot["target_price_progress"]
    assert progress["baseline_date"] == "2026-06-04"
    assert progress["hit_min_horizon_days"] == 1


def test_web_view_stock_detail_target_revision_trail_exposes_report_timeline(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    selected_date = date(2026, 6, 26)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha target 1",
                broker_name="AA Securities",
                published_at=datetime(2026, 6, 12, 9, 0, 0),
                business_date=date(2026, 6, 12),
                collected_at=datetime(2026, 6, 12, 9, 5, 0),
                target_price_value=85_000,
                source_id="target-trail-1",
                identity_key="target-trail-1",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha target 2",
                broker_name="AA Securities",
                published_at=datetime(2026, 6, 19, 9, 0, 0),
                business_date=date(2026, 6, 19),
                collected_at=datetime(2026, 6, 19, 9, 5, 0),
                target_price_value=90_000,
                source_id="target-trail-2",
                identity_key="target-trail-2",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha target 3",
                broker_name="AA Securities",
                published_at=datetime(2026, 6, 26, 9, 0, 0),
                business_date=selected_date,
                collected_at=datetime(2026, 6, 26, 9, 5, 0),
                target_price_value=95_000,
                source_id="target-trail-3",
                identity_key="target-trail-3",
            ),
        ]
    )
    for report_date in (date(2026, 6, 12), date(2026, 6, 19), selected_date):
        repository.rebuild_daily_summaries(report_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=selected_date,
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=88_300,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 26, 18, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=selected_date,
        stock_code="000001",
        now=datetime(2026, 6, 26, 18, 0, 0),
    )

    trail = snapshot["target_price_trail"]
    assert trail["summary"]
    assert trail["latest_report_date"] == "2026-06-26"
    assert trail["direction_label"] == "상향"
    assert trail["attainment_percent"] == pytest.approx(92.9)
    assert trail["items"][0]["broker_name"] == "AA Securities"
    assert trail["items"][0]["previous_target_price_value"] == 90_000
    assert trail["items"][0]["direction_label"] == "상향"
    assert trail["items"][1]["direction_label"] == "상향"
    _assert_public_safe_payload(snapshot)


def test_web_view_target_trail_does_not_compare_different_brokers(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 26)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="AA target",
                broker_name="AA Securities",
                published_at=datetime(2026, 6, 26, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 26, 9, 5, 0),
                target_price_value=95_000,
                source_id="target-broker-aa",
                identity_key="target-broker-aa",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="BB target",
                broker_name="BB Securities",
                published_at=datetime(2026, 6, 26, 9, 1, 0),
                business_date=business_date,
                collected_at=datetime(2026, 6, 26, 9, 5, 0),
                target_price_value=50_000,
                source_id="target-broker-bb",
                identity_key="target-broker-bb",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=business_date,
        stock_code="000001",
    )

    assert all(item["previous_target_price_value"] is None for item in snapshot["target_price_trail"]["items"])
    assert all(item["direction_label"] is None for item in snapshot["target_price_trail"]["items"])


def test_web_view_stock_detail_target_journey_tracks_report_target_events(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    selected_date = date(2026, 6, 3)
    repository.insert_reports(
        [
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha high hit target",
                broker_name="AA Securities",
                published_at=datetime(2026, 6, 1, 9, 0, 0),
                business_date=date(2026, 6, 1),
                collected_at=datetime(2026, 6, 1, 9, 5, 0),
                target_price_value=100_000,
                source_id="target-journey-high-hit",
                identity_key="target-journey-high-hit",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha close fallback target",
                broker_name="BB Securities",
                published_at=datetime(2026, 6, 2, 9, 0, 0),
                business_date=date(2026, 6, 2),
                collected_at=datetime(2026, 6, 2, 9, 5, 0),
                target_price_value=130_000,
                source_id="target-journey-close-hit",
                identity_key="target-journey-close-hit",
            ),
            Report(
                stock_name="Alpha",
                stock_code="000001",
                title="Alpha pending target",
                broker_name="CC Securities",
                published_at=datetime(2026, 6, 3, 9, 0, 0),
                business_date=selected_date,
                collected_at=datetime(2026, 6, 3, 9, 5, 0),
                target_price_value=200_000,
                source_id="target-journey-progress",
                identity_key="target-journey-progress",
            ),
            Report(
                stock_name="Beta",
                stock_code="000002",
                title="Beta missing market target",
                broker_name="DD Securities",
                published_at=datetime(2026, 6, 3, 9, 0, 0),
                business_date=selected_date,
                collected_at=datetime(2026, 6, 3, 9, 5, 0),
                target_price_value=50_000,
                source_id="target-journey-no-market",
                identity_key="target-journey-no-market",
            ),
        ]
    )
    for report_date in (date(2026, 6, 1), date(2026, 6, 2), selected_date):
        repository.rebuild_daily_summaries(report_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 6, 1),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=90_000,
                high_price=95_000,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 1, 18, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 6, 2),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=99_000,
                high_price=110_000,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 2, 18, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 6, 3),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=125_000,
                high_price=None,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 3, 18, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 6, 4),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=130_000,
                high_price=None,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 4, 18, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 6, 5),
                stock_code="000001",
                stock_name="Alpha",
                market="KOSPI",
                close_price=130_000,
                high_price=160_000,
                change_percent=0.0,
                turnover=100_000_000,
                fetched_at=datetime(2026, 6, 5, 18, 0, 0),
            ),
        ]
    )

    alpha_snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=selected_date,
        stock_code="000001",
        now=datetime(2026, 6, 5, 18, 0, 0),
    )
    beta_snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=selected_date,
        stock_code="000002",
        now=datetime(2026, 6, 5, 18, 0, 0),
    )

    journey = alpha_snapshot["target_journey"]
    assert journey["available"] is True
    assert journey["source"] == "stored_reports_and_stock_market_daily"
    assert journey["price_basis"] == "high_price_then_close_price"
    assert [item["status"] for item in journey["items"]] == ["in_progress", "hit", "hit"]

    in_progress = journey["items"][0]
    assert in_progress["report_date"] == "2026-06-03"
    assert in_progress["broker_name"] == "CC Securities"
    assert all(item["revision_direction_label"] is None for item in journey["items"])
    assert in_progress["current_attainment_percent"] == pytest.approx(65.0)
    assert in_progress["max_attainment_percent"] == pytest.approx(80.0)
    assert in_progress["observed_through"] == "2026-06-05"

    close_fallback_hit = journey["items"][1]
    assert close_fallback_hit["hit_date"] == "2026-06-04"
    assert close_fallback_hit["hit_trading_days"] == 2
    assert close_fallback_hit["current_attainment_percent"] == pytest.approx(100.0)
    assert close_fallback_hit["max_attainment_percent"] == pytest.approx(123.1)

    high_hit = journey["items"][2]
    assert high_hit["hit_date"] == "2026-06-02"
    assert high_hit["hit_trading_days"] == 1

    missing_journey = beta_snapshot["target_journey"]
    assert missing_journey["available"] is True
    assert missing_journey["items"][0]["status"] == "no_market_data"
    assert missing_journey["items"][0]["hit_date"] is None
    assert missing_journey["items"][0]["hit_trading_days"] is None
    assert missing_journey["items"][0]["current_attainment_percent"] is None
    assert missing_journey["items"][0]["max_attainment_percent"] is None
    _assert_public_safe_payload(alpha_snapshot)
    _assert_public_safe_payload(beta_snapshot)


def test_web_view_html_renders_target_revision_line_in_top_two_cards() -> None:
    html = cli_module._render_web_view_html()
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function updateTossPriorityRefreshButton()", 1
    )[0]

    assert "targetRevisionTrailLine(item)" in top_two_body
    assert "target-revision-line" in top_two_body


def test_web_view_html_renders_target_journey_in_stock_detail_only() -> None:
    html = cli_module._render_web_view_html()
    stock_context_body = html.split("function renderStockContext(data)", 1)[1].split(
        "function targetProgressDetailLabel(progress)", 1
    )[0]
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function updateTossPriorityRefreshButton()", 1
    )[0]

    assert "data.target_journey" in stock_context_body
    assert "renderTargetJourney" in stock_context_body
    assert "리포트 변화·도달 기록" in stock_context_body
    assert "선택일 이후 저장 가격 이력 · 고가 우선/종가 보조" in stock_context_body
    assert "item.observed_through" in stock_context_body
    assert "목표가 Journey" not in stock_context_body
    assert "가격 검증 대기" in stock_context_body
    assert "시장 데이터 없음" not in stock_context_body
    assert stock_context_body.index("${targetJourneyBlock}") < stock_context_body.index("${targetTrailBlock}")
    assert "renderTargetPriceTrailRows(targetTrail.items)" not in stock_context_body
    assert "현재 목표가 진행" in stock_context_body
    assert ".target-direction-label { white-space: nowrap; flex-shrink: 0; }" in html
    assert ".stock-context-panel { max-height: none; overflow: visible; padding-right: 0; }" in html
    assert "target_journey" not in top_two_body


def test_web_view_html_renders_value_context_in_stock_detail_only() -> None:
    html = cli_module._render_web_view_html()
    stock_context_body = html.split("function renderStockContext(data)", 1)[1].split(
        "function renderStockValueContext(context)", 1
    )[0]
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function updateTossPriorityRefreshButton()", 1
    )[0]

    assert "candidateValueContextLine(item.value_context)" not in top_two_body
    assert "top-two-value-context" not in top_two_body
    assert "renderStockValueContext(data.value_context)" in stock_context_body
    assert "value-context-grid" in html


def test_web_view_html_exposes_toss_source_and_compact_evidence_ledger() -> None:
    html = cli_module._render_web_view_html()
    stock_context_body = html.split("function renderStockContext(data)", 1)[1].split(
        "function targetProgressDetailLabel(progress)", 1
    )[0]
    news_summary_body = html.split("function renderNewsObservationSummary(summary)", 1)[1].split(
        "function selectStablePriorityRows", 1
    )[0]
    top_two_body = html.split("function topTwoCurrentEvidenceLine(item)", 1)[1].split(
        "function topTwoTossQuoteIsCurrent", 1
    )[0]
    stock_journey_body = html.split("function renderStockCandidateJourney(data)", 1)[1].split(
        "function targetAttainmentLine", 1
    )[0]

    assert "선택 날짜 Toss 저장 기준" in html
    assert "Toss 저장 최근 흐름" in html
    assert "구성종목을 포함하지 않는 Toss 저장 ETF 거래대금 기준" in html
    assert "Toss 저장 기준일" in html
    assert "publishedLabel(data.market_reference.fetched_at)" in stock_context_body
    assert "Toss 20:00 ${price(data.market_reference.close_price)}" not in stock_context_body
    assert "웹뷰에서 뉴스 근거 저장을 실행하면" not in html
    assert "선택 날짜 KRX 확정 이력" not in html
    assert "KRX 최근 흐름" not in html
    assert "const actionableItems" in news_summary_body
    assert "newsObservationSummaryGroups(actionableItems)" in news_summary_body
    assert "candidateNewsHasActionableEvidence" in top_two_body
    assert "뉴스 직접 매칭 없음" in top_two_body
    assert "<b>근거 원장</b>" in stock_journey_body
    assert "리포트 근거:" in stock_journey_body
    assert "과거 반응(KRX):" in stock_journey_body
    assert "candidateEventReactionLine(candidate.event_reaction)" in stock_journey_body
    assert "function candidateEventReactionLine(reaction)" in html
    assert "저장 기준:" in stock_journey_body
    assert "Toss 현재가 확인 전" not in stock_journey_body
    assert "tossPriorityQuoteByCode.has" in stock_journey_body


def test_web_view_etf_trend_snapshot_exposes_rotation_evidence_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="396500",
                etf_name="TIGER 반도체TOP10",
                close_price=12_345,
                change_percent=2.4,
                nav=12_400.5,
                turnover=98_765_432_100,
                underlying_index_name="FnGuide 반도체 TOP10",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_etf_trend_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert snapshot["reference_status"] == "exact"
    assert snapshot["basis"] == "Toss 거래대금 상위 ETF"
    assert snapshot["constituents_available"] is False
    assert snapshot["composition_scope"] == "구성종목 미포함"
    assert snapshot["display_label"] == "ETF 저장 참고"
    first = snapshot["items"][0]["top_etfs_by_turnover"][0]
    assert first["evidence_label"] == "거래대금 988억 · NAV 12,400.5 · 기초지수 FnGuide 반도체 TOP10"
    assert first["rotation_reference"] == "저장 ETF 거래대금/NAV/기초지수 기준"
    _assert_public_safe_payload(snapshot)


def test_web_view_etf_trend_snapshot_marks_stale_reference_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 7),
                etf_code="069500",
                etf_name="KODEX 200",
                close_price=40_000,
                change_percent=-0.3,
                nav=40_050.0,
                turnover=1_000_000_000,
                underlying_index_name="코스피 200",
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_etf_trend_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert snapshot["reference_status"] == "stale"
    assert snapshot["reference_date"] == "2026-05-07"
    assert snapshot["notice"] == "선택 날짜의 ETF 저장값이 없어 2026-05-07 기준 Toss ETF 흐름만 표시합니다."
    _assert_public_safe_payload(snapshot)


def test_web_view_etf_trend_snapshot_does_not_claim_empty_market_dates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.0,
                volume=10_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_etf_trend_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert snapshot["available"] is False
    assert snapshot["reference_date"] is None
    assert snapshot["reference_status"] == "missing"
    assert snapshot["items"] == []


def test_web_view_source_freshness_does_not_infer_etf_from_stock_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="삼성전자 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="no-etf-freshness-1",
                identity_key="no-etf-freshness-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.0,
                volume=10_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=datetime(2026, 5, 8, 21, 0, 0),
    )
    freshness = {item["key"]: item for item in snapshot["source_freshness_summary"]["items"]}

    assert freshness["toss_market"]["status"] == "exact"
    assert freshness["toss_etf"]["status"] == "missing"
    assert freshness["toss_etf"]["reference_date"] is None


def test_web_view_recent_toss_flow_exposes_actual_reference_date_when_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 11, 9, 0, 0),
                business_date=date(2026, 5, 11),
                collected_at=datetime(2026, 5, 11, 9, 5, 0),
                source_id="recent-flow-fallback-1",
                identity_key="recent-flow-fallback-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 11))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=101_000,
                change_percent=2.0,
                volume=20_000,
                turnover=900,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 11),
        now=datetime(2026, 5, 11, 16, 0, 0),
    )

    assert snapshot["toss_context"]["available"] is False
    assert snapshot["toss_recent_flow"]["business_date"] == "2026-05-11"
    assert snapshot["toss_recent_flow"]["reference_date"] == "2026-05-08"
    assert snapshot["toss_recent_flow"]["exact_date_available"] is False
    assert "최근 Toss 저장 스냅샷" in snapshot["toss_recent_flow"]["notice"]


def test_web_view_stock_detail_snapshot_exposes_reports_without_admin_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="다른 종목",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="identity-2",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="목표가와 의견 없음",
                broker_name="신한투자증권",
                published_at=datetime(2026, 5, 8, 10, 30, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 35, 0),
                target_price_value=None,
                opinion_normalized="N/A",
                source_url="https://stock.naver.com/research/company/3",
                source_id="3",
                identity_key="identity-3",
            ),
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=99_000,
                change_percent=-0.5,
                volume=8_000,
                turnover=400,
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                volume=10_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="개인",
                net_buy_volume=10,
                net_buy_amount=20,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_volume=-30,
                net_buy_amount=-60,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="개인",
                net_buy_volume=-50,
                net_buy_amount=-100,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_volume=100,
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            ),
        ]
    )

    snapshot = cli_module.build_web_view_stock_detail_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        stock_code="005930",
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["stock_name"] == "삼성전자"
    assert snapshot["market_reference"]["close_price"] == 100_000
    assert snapshot["value_context"] == {
        "report_reference_date": "2026-05-08",
        "toss_reference_date": "2026-05-08",
        "current_price_reference_time": "2026-05-08T20:00:00",
        "current_price_basis": "Toss stored snapshot",
        "turnover_reference_date": "2026-05-08",
        "investor_flow_reference_date": "2026-05-08",
        "news_collection_status": "next_check_needed",
        "missing_labels": [],
    }
    assert snapshot["investor_flow"]["available"] is True
    assert snapshot["investor_flow"]["data_scope"] == "stored_toss_close_priority_flow"
    assert snapshot["investor_flow"]["live_fetch"] is False
    assert snapshot["investor_flow"]["scoring"] is False
    assert snapshot["investor_flow"]["rows"][0]["investor_type"] == "외국인"
    assert snapshot["investor_flow"]["rows"][0]["investor_label"] == "외국인"
    assert snapshot["investor_flow"]["rows"][0]["market_label"] == "KOSPI"
    assert snapshot["investor_flow"]["rows"][0]["net_buy_amount"] == 200
    assert snapshot["investor_flow"]["rows"][1]["investor_type"] == "개인"
    assert snapshot["recent_volume_days"]["available"] is True
    assert [item["business_date"] for item in snapshot["recent_volume_days"]["items"]] == ["2026-05-08", "2026-05-07"]
    assert snapshot["recent_volume_days"]["items"][0]["volume"] == 10_000
    assert snapshot["investor_flow_tabs"]["retail_foreign_institution"] == [
        {
            "business_date": "2026-05-08",
            "individual": -50,
            "foreign": 100,
            "institution": None,
            "individual_buy": None,
            "individual_sell": None,
            "foreign_buy": None,
            "foreign_sell": None,
            "institution_buy": None,
            "institution_sell": None,
        },
        {
            "business_date": "2026-05-07",
            "individual": 10,
            "foreign": -30,
            "institution": None,
            "individual_buy": None,
            "individual_sell": None,
            "foreign_buy": None,
            "foreign_sell": None,
            "institution_buy": None,
            "institution_sell": None,
        }
    ]
    assert snapshot["reports"] == [
        {
            "stock_name": "삼성전자",
            "stock_code": "005930",
            "title": "목표가와 의견 없음",
            "title_display": "목표가와 의견 없음",
            "broker_name": "신한투자증권",
            "published_at": "2026-05-08T10:30:00",
            "target_price_value": None,
            "target_price_display": "목표가 없음",
            "opinion_normalized": "N/A",
            "opinion_display": "의견 없음",
            "source_url": "https://stock.naver.com/research/company/3",
        },
        {
            "stock_name": "삼성전자",
            "stock_code": "005930",
            "title": "업황 회복",
            "title_display": "업황 회복",
            "broker_name": "NH투자증권",
            "published_at": "2026-05-08T09:00:00",
            "target_price_value": 100_000,
            "target_price_display": "목표가 100,000원",
            "opinion_normalized": "buy",
            "opinion_display": "리포트 표기: 매수",
            "source_url": "https://stock.naver.com/research/company/1",
        }
    ]
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_market_display_uses_public_unknown_label() -> None:
    assert cli_module._web_view_market_display("N/A") == "시장 미확인"
    assert cli_module._web_view_market_display(None) == "시장 미확인"


def test_web_view_investor_display_uses_public_unknown_label() -> None:
    assert cli_module._web_view_investor_display("N/A") == "투자자 미확인"
    assert cli_module._web_view_investor_display(None) == "투자자 미확인"


def test_web_view_report_display_values_are_user_facing() -> None:
    assert cli_module._web_view_target_price_display(None) == "목표가 없음"
    assert cli_module._web_view_target_price_display(100_000) == "목표가 100,000원"
    assert cli_module._web_view_opinion_display("N/A") == "의견 없음"
    assert cli_module._web_view_opinion_display(None) == "의견 없음"
    assert cli_module._web_view_opinion_display("buy") == "리포트 표기: 매수"
    assert cli_module._web_view_opinion_display("neutral") == "리포트 표기: 중립"
    assert cli_module._web_view_opinion_display("sell") == "리포트 표기: 매도"


def test_web_view_category_detail_snapshot_exposes_sector_stocks_without_admin_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized="buy",
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="다른 종목",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="identity-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="005930",
                stock_name="삼성전자",
                sector_code="1",
                sector_name="반도체",
                updated_at=datetime(2026, 5, 8, 10, 0, 0),
            ),
            StockMetadata(
                stock_code="000660",
                stock_name="SK하이닉스",
                sector_code="1",
                sector_name="반도체",
                updated_at=datetime(2026, 5, 8, 10, 0, 0),
            ),
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_category_detail_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        category_type="sector",
        category_name="반도체",
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["category_label"] == "업종"
    assert snapshot["category_name"] == "반도체"
    assert snapshot["stock_count"] == 2
    assert snapshot["report_count"] == 2
    assert [item["stock_code"] for item in snapshot["stocks"]] == ["000660", "005930"]
    assert snapshot["stocks"][1]["market_reference"]["close_price"] == 100_000
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_category_trend_snapshot_exposes_recent_dates_without_admin_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 7, 9, 0, 0),
                business_date=date(2026, 5, 7),
                collected_at=datetime(2026, 5, 7, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="identity-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 7))
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="1",
            sector_name="반도체",
            updated_at=datetime(2026, 5, 8, 10, 0, 0),
        )
    )

    snapshot = cli_module.build_web_view_category_trend_snapshot(
        config,
        repository,
        category_type="sector",
        category_name="반도체",
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["category_label"] == "업종"
    assert snapshot["trend"] == [
        {"business_date": "2026-05-08", "stock_count": 1, "report_count": 1},
        {"business_date": "2026-05-07", "stock_count": 1, "report_count": 1},
    ]
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_market_snapshot_exposes_toss_reference_without_admin_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 7),
                etf_code="069500",
                etf_name="KODEX 200",
                close_price=40_000,
                change_percent=0.5,
                turnover=300,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 5, 7),
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                close_index=3000.1,
                change_percent=0.8,
                turnover=1000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
                source="toss_openapi",
            )
        ]
    )

    snapshot = cli_module.build_web_view_market_snapshot(
        config,
        repository,
        now=datetime(2026, 5, 8, 20, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["snapshot_source"] == "toss_openapi"
    assert snapshot["snapshot_date"] == "2026-05-07"
    assert snapshot["top_kospi_stocks"][0]["stock_code"] == "005930"
    assert snapshot["top_etfs"][0]["etf_code"] == "069500"
    assert snapshot["market_indices"][0]["index_name"] == "코스피"
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_flow_trend_snapshot_uses_stored_samples_only(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 20, 0, 0)
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="KOSPI",
                investor_type="외국인",
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                market="KOSDAQ",
                investor_type="개인",
                net_buy_amount=-150,
                volume_unit="주",
                amount_unit="원",
                fetched_at=fetched_at,
                source="toss_openapi",
            ),
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 8),
                market="STK",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_amount=300,
                fetched_at=fetched_at,
            ),
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 7),
                market="KSQ",
                investor_type="foreign",
                rank=1,
                stock_code="196170",
                stock_name="알테오젠",
                net_buy_amount=250,
                fetched_at=fetched_at,
            ),
        ]
    )

    snapshot = cli_module.build_web_view_flow_trend_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        limit=5,
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["available"] is True
    assert snapshot["data_scope"] == "stored_toss_close_market_flow"
    assert snapshot["live_fetch"] is False
    assert snapshot["scoring"] is False
    assert [item["business_date"] for item in snapshot["items"]] == ["2026-05-08", "2026-05-07"]
    assert snapshot["items"][0]["market_flows"][0]["market_label"] == "KOSPI"
    assert snapshot["items"][0]["market_flows"][0]["investor_label"] == "외국인"
    assert "foreign_net_buy_top" not in snapshot["items"][0]
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_flow_trend_hides_stale_market_only_samples(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 1),
                market="STK",
                investor_type="foreign",
                net_buy_amount=200,
                volume_unit="shares",
                amount_unit="KRW",
                fetched_at=datetime(2026, 5, 1, 20, 0, 0),
            )
        ]
    )

    snapshot = cli_module.build_web_view_flow_trend_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 21, 0, 0),
    )

    assert snapshot["available"] is False
    assert snapshot["reference_date"] is None
    assert snapshot["items"] == []


def test_market_briefing_does_not_substitute_stale_market_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 1),
                market="STK",
                investor_type="foreign",
                net_buy_amount=200,
                volume_unit="shares",
                amount_unit="KRW",
                fetched_at=datetime(2026, 5, 1, 20, 0, 0),
            )
        ]
    )

    briefing = cli_module._build_web_view_market_briefing_context(
        repository,
        date(2026, 5, 8),
        summaries=[],
        recent_krx_snapshot_dates=[date(2026, 5, 7)],
        recent_flow_dates=[date(2026, 5, 1)],
    )

    assert briefing["flow_summary"]["available"] is False
    assert briefing["flow_reference_lines"] == []


def test_web_view_intraday_snapshot_is_public_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="identity-1",
            )
        ],
        queue_intraday_alerts=True,
    )
    batch = repository.list_pending_intraday_alert_batches()[0]
    repository.mark_intraday_alert_batch_sent(
        batch.batch_id,
        sent_at=datetime(2026, 5, 8, 9, 10, 0),
        message_id="telegram-message-id",
    )

    snapshot = cli_module.build_web_view_intraday_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
        now=datetime(2026, 5, 8, 16, 0, 0),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["business_date"] == "2026-05-08"
    assert snapshot["batches"][0]["status_label"] == "발송됨"
    assert snapshot["batches"][0]["report_count"] == 1
    assert "message_id" not in snapshot["batches"][0]
    assert "error_detail" not in snapshot["batches"][0]
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


def test_web_view_rotation_overlay_snapshot_uses_manual_coordinates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    config.rotation_overlay_coordinates_path.write_text(
        json.dumps(
            {
                "image": {"path": "example/Cycle.jpg", "width": 1376, "height": 768},
                "coordinates": [
                    {"display_name": "우주항공과국방", "x": 760, "y": 190, "radius": 54, "label": "우주항공"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="한화에어로스페이스",
                stock_code="012450",
                title="방산 수주 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="rotation-1",
                identity_key="rotation-1",
            )
        ]
    )
    repository.upsert_category_catalog_items(
        [CategoryCatalogItem("sector", "27", "우주항공과국방", "test", True, fetched_at)]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(
                date(2026, 5, 8),
                "sector",
                "27",
                "우주항공과국방",
                "012450",
                "한화에어로스페이스",
                fetched_at,
                "test",
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="012450",
                stock_name="한화에어로스페이스",
                market="KOSPI",
                close_price=322000,
                change_percent=2.5,
                turnover=123_456_789_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="012450",
                stock_name="한화에어로스페이스",
                market="KOSPI",
                close_price=322000,
                change_percent=2.5,
                turnover=123_456_789_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    snapshot = cli_module.build_web_view_rotation_overlay_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
    )

    assert snapshot["surface"] == "web-view"
    assert snapshot["read_only"] is True
    assert snapshot["image"]["path"] == "example/Cycle.jpg"
    assert snapshot["highlights"][0]["display_name"] == "우주항공과국방"
    assert snapshot["highlights"][0]["public_category_id"] == "sector|우주항공과국방|2026-05-08"
    assert snapshot["highlights"][0]["label"] == "우주항공"
    assert snapshot["highlights"][0]["evidence_label"] == "리포트 1건 / 1종목"
    assert "추천" not in snapshot["notice"]
    assert "확정 판단" in snapshot["notice"]
    _assert_public_safe_payload(snapshot)


def test_web_view_html_connects_rotation_and_stock_related_categories() -> None:
    html = cli_module._render_web_view_html()
    rotation_body = html.split("async function loadRotationOverlay(date)", 1)[1].split(
        "function renderRotationCandidateStocks", 1
    )[0]
    stock_journey_body = html.split("function renderStockCandidateJourney(data)", 1)[1].split(
        "function targetAttainmentLine", 1
    )[0]

    assert 'class="rotation-category-link"' in rotation_body
    assert "safePublicCategoryId(item.category_type, item.public_category_id)" in rotation_body
    assert "data-category-display-name" in rotation_body
    assert "const firstRelatedCategory" in stock_journey_body
    assert "safePublicCategoryId(firstRelatedCategory.category_type, firstRelatedCategory.public_category_id)" in stock_journey_body
    assert 'data-journey-view="rotation"' not in stock_journey_body


def test_web_view_html_uses_truthful_candidate_and_market_copy() -> None:
    html = cli_module._render_web_view_html()
    watch_body = html.split("function renderWatchCandidateRow(item, index)", 1)[1].split(
        "function renderTopTwoReviewCandidates", 1
    )[0]

    assert "Top2 뉴스 수집 대상 아님" in watch_body
    assert "index >= 2 && news.available !== true" in watch_body
    assert "const renderCandidateCard" not in html
    assert "현재값 우선 참고" not in html
    assert "실시간 집계" not in html
    assert "조회값과 저장값을 구분해 표시" in html


def test_web_view_rotation_overlay_snapshot_uses_image_alias_layer(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    config.rotation_overlay_coordinates_path.write_text(
        json.dumps(
            {
                "image": {"path": "example/Cycle.jpg", "width": 1376, "height": 768},
                "coordinates": [
                    {"display_name": "항공방산영역", "x": 760, "y": 190, "radius": 54, "label": "좌표라벨"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_image_aliases.json").write_text(
        json.dumps(
            {
                "version": 1,
                "aliases": [
                    {
                        "rotation_label": "우주항공",
                        "category_type": "sector",
                        "category_display_name": "우주항공과국방",
                        "coordinate_display_name": "항공방산영역",
                        "mapping_basis": "manual_alias",
                        "status": "active",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_etf_candidates.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mappings": [
                    {
                        "rotation_label": "우주항공",
                        "category_type": "sector",
                        "category_display_name": "우주항공과국방",
                        "etf_codes": ["123456"],
                        "status": "active",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="한화에어로스페이스",
                stock_code="012450",
                title="방산 수주 점검",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="rotation-alias-1",
                identity_key="rotation-alias-1",
            )
        ]
    )
    repository.upsert_category_catalog_items(
        [CategoryCatalogItem("sector", "27", "우주항공과국방", "test", True, fetched_at)]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(
                date(2026, 5, 8),
                "sector",
                "27",
                "우주항공과국방",
                "012450",
                "한화에어로스페이스",
                fetched_at,
                "test",
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="012450",
                stock_name="한화에어로스페이스",
                market="KOSPI",
                close_price=322000,
                change_percent=2.5,
                turnover=123_456_789_000,
                fetched_at=fetched_at,
                source="toss_openapi",
            )
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="123456",
                etf_name="TEST 우주항공 ETF",
                close_price=12345,
                change_percent=1.2,
                turnover=98_765_432_100,
                underlying_index_name="우주항공 테스트 지수",
                fetched_at=fetched_at,
                source="toss_openapi",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    snapshot = cli_module.build_web_view_rotation_overlay_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 8),
    )

    highlight = snapshot["highlights"][0]
    assert highlight["display_name"] == "우주항공과국방"
    assert highlight["rotation_label"] == "우주항공"
    assert highlight["coordinate_display_name"] == "항공방산영역"
    assert highlight["label"] == "우주항공"
    assert highlight["mapping_basis"] == "manual_alias"
    assert highlight["x"] == 760
    assert highlight["evidence_label"] == "리포트 1건 / 1종목"
    assert highlight["candidate_stocks"] == [
        {
            "stock_code": "012450",
            "stock_name": "한화에어로스페이스",
            "mention_count": 1,
            "broker_count_label": "증권사 1곳",
            "market": "KOSPI",
            "close_price": 322000,
            "change_percent": 2.5,
            "turnover": 123_456_789_000,
            "evidence_label": "리포트 1건 · 거래대금 1235억",
        }
    ]
    assert highlight["candidate_etfs"] == [
        {
            "etf_code": "123456",
            "etf_name": "TEST 우주항공 ETF",
            "close_price": 12345,
            "change_percent": 1.2,
            "turnover": 98_765_432_100,
            "underlying_index_name": "우주항공 테스트 지수",
            "evidence_label": "거래대금 988억",
        }
    ]
    _assert_public_safe_payload(snapshot)


def test_web_view_server_serves_get_only_archive(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="server-archive-1",
                identity_key="server-archive-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base_url + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        with urllib.request.urlopen(base_url + "/v2", timeout=5) as response:
            v2_html = response.read().decode("utf-8")
        with urllib.request.urlopen(base_url + "/api/archive", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/daily/2026-05-08", timeout=5) as response:
            daily_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/observation-summary?date=2026-05-08", timeout=5) as response:
            observation_summary_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/candidate-evidence?date=2026-05-08", timeout=5) as response:
            candidate_evidence_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/observation/backtest?date=2026-05-08", timeout=5) as response:
            backtest_observation_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/daily/2026-05-08/stocks/005930", timeout=5) as response:
            stock_detail_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/market", timeout=5) as response:
            market_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/intraday?date=2026-05-08", timeout=5) as response:
            intraday_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/flow-trend?date=2026-05-08", timeout=5) as response:
            flow_trend_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/rotation-overlay?date=2026-05-08", timeout=5) as response:
            rotation_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/assets/cycle.jpg", timeout=5) as response:
            cycle_status = response.status
            cycle_content_type = response.headers.get("Content-Type")
        with urllib.request.urlopen(
            base_url + "/api/category?date=2026-05-08&type=sector&name=%EB%B0%98%EB%8F%84%EC%B2%B4",
            timeout=5,
        ) as response:
            category_payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(
            base_url + "/api/category-trend?type=sector&name=%EB%B0%98%EB%8F%84%EC%B2%B4",
            timeout=5,
        ) as response:
            category_trend_payload = json.loads(response.read().decode("utf-8"))
        try:
            urllib.request.urlopen(
                base_url
                + "/api/category?date=2026-05-08&type=sector&display_name=%EB%B0%98%EB%8F%84%EC%B2%B4"
                + "&public_category_id=theme%7C%EB%B0%98%EB%8F%84%EC%B2%B4%7C2026-05-08",
                timeout=5,
            )
        except urllib.error.HTTPError as exc:
            category_mismatch_status = exc.code
            category_mismatch_body = exc.read().decode("utf-8")
        else:
            category_mismatch_status = 200
            category_mismatch_body = ""
        try:
            urllib.request.urlopen(
                base_url
                + "/api/category-trend?type=sector&display_name=%EB%B0%98%EB%8F%84%EC%B2%B4"
                + "&public_category_id=theme%7C%EB%B0%98%EB%8F%84%EC%B2%B4%7Ctrend",
                timeout=5,
            )
        except urllib.error.HTTPError as exc:
            category_trend_mismatch_status = exc.code
            category_trend_mismatch_body = exc.read().decode("utf-8")
        else:
            category_trend_mismatch_status = 200
            category_trend_mismatch_body = ""

        request = urllib.request.Request(base_url + "/api/archive", data=b"{}", method="POST")
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            post_status = exc.code
        else:
            post_status = 200
        v2_request = urllib.request.Request(base_url + "/v2", data=b"{}", method="POST")
        try:
            urllib.request.urlopen(v2_request, timeout=5)
        except urllib.error.HTTPError as exc:
            v2_post_status = exc.code
        else:
            v2_post_status = 200

        forbidden_control_route_statuses = {}
        for route, method, body in (
            ("/api/status", "GET", None),
            ("/api/scheduler/run-now", "POST", b'{"task":"poll"}'),
            ("/api/scheduler/set-enabled", "POST", b'{"task":"poll","enabled":false}'),
            ("/api/operator/pause", "POST", b'{"reason":"web-view boundary test"}'),
            ("/api/settings/set", "POST", b'{"key":"operation_profile","value":"manual-only"}'),
        ):
            request = urllib.request.Request(base_url + route, data=body, method=method)
            try:
                urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as exc:
                forbidden_control_route_statuses[(method, route)] = exc.code
            else:
                forbidden_control_route_statuses[(method, route)] = 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert "<h1>KR-Stock</h1>" in html
    assert "일일 리포트" in html
    assert 'class="hero-title-row"' in html
    assert 'id="calendar-open" class="calendar-trigger"' in html
    assert 'id="calendar-selected-date" class="calendar-selected-date"' in html
    assert 'id="main-priority-date"' not in html
    assert 'id="daily-briefing-date"' not in html
    assert 'id="archive-calendar-dialog" class="calendar-dialog"' in html
    assert 'id="calendar-close" class="dialog-close"' in html
    assert 'selectedDate ? `(${selectedDate})` : ""' in html
    assert "KR-Stock V2 Preview" in v2_html
    assert 'id="surface-v2-app"' in v2_html
    assert 'data-v2-section="candidates"' in v2_html
    assert 'data-view-tab="main"' in html
    assert 'data-view-tab="watch"' in html
    assert 'data-view-tab="stock"' in html
    assert 'data-view-tab="market"' not in html
    assert 'data-view-tab="rotation"' not in html
    assert html.index('data-view-tab="main"') < html.index('data-view-tab="watch"')
    assert html.index('data-view-tab="watch"') < html.index('data-view-tab="stock"')
    assert 'data-view-tab="main" aria-current="page" aria-pressed="true"' in html
    assert 'data-view-tab="watch" aria-current="false" aria-pressed="false"' in html
    assert 'button.setAttribute("aria-current", isActive ? "page" : "false");' in html
    assert 'button.setAttribute("aria-pressed", isActive ? "true" : "false");' in html
    assert "moveViewTabFromKeyboard" in html
    assert '["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)' in html
    assert 'page.keyboard.press("ArrowRight")' not in html
    assert 'class="card span-12 market-reference-card" id="market-reference-card" data-view-panel="main"' in html
    assert 'document.getElementById("market-reference-card").open = true' not in html
    assert 'id="main-market-context-card" data-view-panel="main"' in html
    assert 'id="toss-market-refresh"' in html
    assert "눈에 띄는 종목" in html
    assert 'labeled("거래대금", compactTurnover(item.turnover))' in html
    assert "<th>D+1</th><th>D+5</th><th>D+10</th><th>D+20</th>" not in html
    assert 'colspan="8"' not in html
    assert "관찰 후보 근거" not in html
    assert "리포트 후 반응 관찰" not in html
    assert "read-only</span>" not in html
    assert "candidate-evidence-rows" in html
    assert (
        'class="card span-12 main-priority-card" id="main-priority-card" '
        'data-view-panel="main"'
    ) in html
    assert ".main-priority-card { order: -1; }" not in html
    assert html.index('id="main-priority-card"') < html.index('class="card span-12 daily-briefing"')
    main_priority_body = html.split('id="main-priority-card"', 1)[1].split(
        'class="card span-12 daily-briefing"', 1
    )[0]
    indicator_query_body = html.split("async function loadNewbbyIndicatorSnapshot(date)", 1)[1].split(
        "function tossQuoteTimeLabel", 1
    )[0]
    daily_briefing_body = html.split('class="card span-12 daily-briefing"', 1)[1].split(
        'id="main-market-context-card"', 1
    )[0]
    assert 'id="intraday-market-top-check"' in main_priority_body
    assert 'id="intraday-market-top-status"' in main_priority_body
    assert 'id="intraday-market-top-overlap" class="intraday-overlap-panel" hidden' in main_priority_body
    assert 'id="newbby-indicator-refresh"' in main_priority_body
    assert 'id="newbby-indicator-status"' in main_priority_body
    assert 'id="newbby-indicator-panel"' in main_priority_body
    assert 'class="main-priority-controls"' in main_priority_body
    assert '`/api/priority-indicators?date=${encodeURIComponent(date)}`' in indicator_query_body
    assert 'cache: "no-store"' in indicator_query_body
    assert "newbbyIndicatorData = data" in indicator_query_body
    assert 'method: "POST"' not in indicator_query_body
    assert "메인은 오늘 먼저 볼 2종만 압축합니다." not in html
    assert 'class="live-source-pill"' not in main_priority_body
    assert ".live-source-pill" not in html
    assert 'id="intraday-market-top-check"' not in daily_briefing_body
    assert 'id="intraday-market-top-status"' not in daily_briefing_body
    assert 'id="candidate-evidence-card" data-view-panel="watch"' in html
    assert 'id="candidate-evidence-card" data-view-panel="main"' not in html
    assert 'id="observation-summary-card"' not in html
    assert 'id="stock-quick-picks-card"' not in html
    assert "candidate-evidence-panel" in html
    assert 'id="backtest-observation-card"' not in html
    assert 'id="news-observation-collect"' not in html
    assert 'fetch("/api/news-observations/collect"' not in html
    assert "maybeAutoCollectNewsObservation" not in html
    assert "function renderWatchCandidateRow(item, index)" in html
    assert 'class="watch-candidate-row candidate-detail-action"' in html
    assert html.index('id="candidate-evidence-card"') < html.index('id="stock-rows"')
    assert "renderCandidateEvidence(data.candidate_evidence)" not in html
    assert "loadCandidateEvidence(date, { initialData: currentDailyData?.priority_candidate_evidence })" in html
    assert 'document.getElementById("main-priority-rows").innerHTML = message;' in html
    assert 'if (activeViewTab === "main") {\n        await loadCandidateEvidence(date, { initialData: currentDailyData?.priority_candidate_evidence });' in html
    load_daily_body = html.split("async function loadDaily(date, options = {})", 1)[1].split(
        "function renderDailyBriefing", 1
    )[0]
    assert "loadBacktestObservation(date)" not in load_daily_body
    assert "loadEtfTrend(date)" not in load_daily_body
    assert "loadFlowTrend(date)" not in load_daily_body
    assert "loadTabDataForActiveView(date)" in load_daily_body
    assert "candidateDisplayFlags(item.quality_flags)" not in html
    assert 'new Set(["missing_stock_flow", "rank_not_present"])' not in html
    assert "candidateIntradayReferenceLabel(item.intraday_reference)" in html
    assert "function candidateNewsCompactLine(badge)" in html
    assert "function candidateNewsDigestLine(badge)" in html
    assert "근거 상태:" not in html
    assert "판단 상태:" not in html
    assert "topTwoIntradayReferenceForRow(row, reference, firstMarketStatus)" in html
    assert "Naver 상위 미포함" in html
    assert "뉴스 기준일 이전값" in html
    assert "뉴스 기준일 stale" not in html
    news_compact_body = html.split("function candidateNewsCompactLine(badge)", 1)[1].split(
        "function candidateNewsPrimaryLabel", 1
    )[0]
    assert "보조 확인" in news_compact_body
    assert "krxNewsReferenceLabel" not in news_compact_body
    top_two_body = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1].split(
        "function updateTossPriorityRefreshButton", 1
    )[0]
    assert "esc(valueLine)" not in top_two_body
    assert "현재 근거:" not in top_two_body
    assert "현재 미확인:" not in top_two_body
    assert "<strong>근거</strong>" in top_two_body
    assert "<strong>확인 필요</strong>" in top_two_body
    assert 'targetRevisionLine === "최근 조정 없음"' in top_two_body
    assert 'class="top-two-evidence-details"' in top_two_body
    assert 'candidate-research-focus-body' in html
    assert "당일 Toss 20:00 저장 예정" in top_two_body
    assert "오늘 누적 뉴스" in html
    assert "topTwoCurrentEvidenceLine(item)" in top_two_body
    assert "topTwoMissingEvidenceLine(item, tossQuote)" in top_two_body
    assert "top-two-news-line" not in top_two_body
    assert "top-two-value-context" not in top_two_body
    assert "근거 기준:" not in top_two_body
    assert "candidateCompactLabel(valueProfile.reference_notes, 4)" not in top_two_body
    assert "valueProfile.value_reason" not in top_two_body
    assert "esc(newsLine)" not in top_two_body
    assert "esc(tossBaselineLine)" not in top_two_body
    toss_quote_body = html.split("async function loadTossPriorityQuotes(date, options = {})", 1)[1].split(
        "async function loadPriorityCurrentQuotes", 1
    )[0]
    assert 'document.getElementById("main-priority-rows").innerHTML = renderTopTwoReviewCandidates(tossPriorityRows);' in toss_quote_body
    assert "await loadPriorityCurrentQuotes(date);" in toss_quote_body
    priority_load_body = html.split("tossPriorityRows = priorityRows.filter((row) => row?.selected !== false).slice(0, 2);", 1)[1].split(
        'document.getElementById("candidate-evidence-rows")', 1
    )[0]
    assert "loadTossPriorityQuotes(tossPriorityDate);" in priority_load_body
    assert "tossPriorityCohortKey" in priority_load_body
    assert "force: true" in html
    assert "loadPriorityCurrentQuotes(tossPriorityDate);" not in priority_load_body
    assert 'const hasCurrentPrice = item?.intraday_reference?.available === true || topTwoTossQuoteIsCurrent(tossQuote);' in html
    assert 'if (!hasCurrentPrice) missing.push("현재가 확인 전");' in html
    assert 'missing.push("Toss 현재가 확인 전")' not in top_two_body
    assert 'function targetPriceRange(minimum, maximum)' in html
    assert "목표가 범위(일자 집계)" in top_two_body
    assert '<span>뉴스: ${esc(candidateNewsCompactLine(candidate.news_observation_badge))}</span>' in html
    assert "확인 전" in html
    assert "candidateCompactLabel(whyItems, 2)" in html
    assert "candidateCompactLabel(candidateWhyDisplayItems(layers.primary), 3)" in html
    assert "candidateCompactLabel(gapItems, 1)" not in html
    assert "candidateEvidenceLayers(item)" in html
    assert "candidateWhyDisplayItems(layers.primary)" in html
    assert "return values;" in html
    assert "브로커 폭" not in html
    assert 'item !== "브로커 폭"' not in html
    assert '["의견", opinion(report.dominant_opinion)]' not in html
    assert "증권사 ${number(report.broker_count)}곳" not in html
    assert "<b>KRX</b>" not in html
    assert "renderTopTwoReviewCandidates(rows) + rows.map" not in html
    assert 'document.getElementById("main-priority-rows").innerHTML = renderTopTwoReviewCandidates(priorityRows);' in html
    assert "오늘의 우선순위" in html
    assert 'item.observation_priority || "우선 확인"' in html
    assert "확인 후보" in html
    assert "추천/점수 아님" not in html
    assert "이전 날짜" not in html
    assert "다음 날짜" not in html
    assert "archive-filter" not in html
    assert "archive-toolbar" not in html
    assert "data-archive-mode=\"dated-category\"" not in html
    assert "data-archive-mode=\"fallback-category\"" not in html
    assert "카테고리 스냅샷" not in html
    assert "카테고리 fallback" not in html
    assert "fallback" not in html
    assert "최신 매핑" not in html
    assert "마감 대기" in html
    assert "선택 날짜 Toss 저장 대기" in html
    assert "선택 날짜 KRX 마감" not in html
    assert "marketReference(item.market_reference, krxSnapshotMissing)" in html
    assert "archive-category-summary" not in html
    assert "카테고리 기준:" not in html
    assert "archive-calendar" in html
    assert "news_observation_count" in html
    assert "has-news-observation" in html
    assert "news-count" in html
    assert "뉴스 관찰 ${number(item.news_observation_count)}건" in html
    assert "뉴스 ${number(item.news_observation_count)}건" in html
    assert "calendar-prev" in html
    assert "calendar-next" in html
    assert "stock-search-input" in html
    assert "stock-search-results" in html
    assert "stock-search-status" in html
    assert "전체 저장 종목명/코드" in html
    assert "날짜를 선택하면 저장 종목을 찾을 수 있습니다." in html
    assert "stockSearchDefaultStatus" in html
    assert "syncStockSearchInput" in html
    assert "renderStockSearchResults" in html
    assert "loadStockSearchResults" in html
    assert "/api/stocks/search?" in html
    assert "selectStockFromSearch" in html
    assert "오늘 읽을 요약" in html
    assert "daily-briefing-headline" in html
    assert "briefing-report-flow" not in html
    assert "briefing-turnover" not in html
    assert "briefing-investor-flow" not in html
    assert "briefing-market-index" not in html
    assert "briefing-market-index-title" not in html
    assert "briefing-turnover-title" not in html
    assert "briefing-saved-market-details" not in html
    assert "briefingIndexPair" not in html
    assert "briefing-box span:empty" not in html
    assert "briefingPairTitle" not in html
    assert "briefing-investor-flow-sub" not in html
    assert "briefing-market-row" not in html
    assert "briefing-reference-card" not in html
    assert "briefing-reference-divider" not in html
    assert "briefing-card-lines" not in html
    assert "briefing-flow-lines" not in html
    assert "briefing-detail-flow" not in html
    assert "setBriefingPairValue" not in html
    assert "눈에 띄는 업종" not in html
    assert "briefing-watch-chips" not in html
    assert "briefing-check-points" in html
    assert "renderBriefingCheckPoints" in html
    assert "reportFlowPoint" not in html
    assert "briefingTurnoverPair" not in html
    assert "top_items" not in html
    assert 'items.map((item) => `${esc(item.stock_name' not in html
    assert 'indices.map((item) => `${esc(item.index_series' not in html
    assert "renderDailyBriefing(data)" in html
    assert html.index('id="main-priority-card"') < html.index('id="news-observation-summary"')
    assert "item?.data_scope" not in html
    assert '${actionableItems.length ? "" : `<p class="news-observation-summary-connection">' in html
    assert "date-calendar-cell" in html
    assert "class=\"weekday\"" not in html
    assert "당일 시장 · 수급" in html
    assert "선택 날짜 Toss 저장 기준" in html
    assert html.index("당일 시장 · 수급") < html.index("선택 날짜 Toss 저장 기준")
    assert "현재 선택" not in html
    assert "선택 상태" not in html
    assert "stock-single-toggle" in html
    assert '<div class="card span-12" data-view-panel="stock" hidden>\n        <div class="section-header">\n          <h2>일일 종목 요약' in html
    assert "1건 포함" in html
    assert "stock-show-more" in html
    assert "const DAILY_STOCK_DEFAULT_LIMIT = 6" in html
    assert "let dailyStockVisibleLimit = DAILY_STOCK_DEFAULT_LIMIT" in html
    assert "filteredStocks.slice(0, dailyStockVisibleLimit)" in html
    assert "리포트 요약 지표" not in html
    assert "추천이나 점수가 아니라" not in html
    assert "추천 순위" not in html
    assert "추천이나 매수/매도" not in html
    assert "업종 분류 데이터 정비 후 표시합니다" not in html
    assert "공유 화면 기준" not in html
    assert "관리자 제어 없음" not in html
    assert "public-contract" not in html
    assert "scroll-panel" in html
    assert "stock-summary-panel" in html
    assert "Number.isFinite" in html
    assert "const price = (value) => compactAmount(value, \"원\")" in html
    assert "const compactTurnover = (value, unit = \"원\")" in html
    assert "${esc(item.evidence_label || compactTurnover(item.turnover))}</span>" in html
    assert html.count('labeled("거래대금", compactTurnover(item.turnover))') >= 3
    assert "market-etf-rows" not in html
    assert "ETF 거래대금 상위" not in html
    assert "ETF는 메인의 업종·ETF 참고에서 확인합니다." in html
    assert "ETF는 메인의 업종·ETF 참고에서 확인합니다." in html
    assert 'labeled("거래대금", compactAmount(item.turnover))' not in html
    assert "${compactTurnover(item.turnover)} · ${percent(item.change_percent)}" in html
    assert 'String(flow?.notice || "저장된 ETF 데이터 기준입니다.")' in html
    assert "publishedLabel(item.published_at)" in html
    assert "timePart !== \"00:00\"" in html
    assert "100000000" not in html
    assert ">= 10000" not in html
    assert "const quantity = (value, unit = \"주\")" in html
    assert "active-selection" in html
    assert "stock-context-card" in html
    assert 'id="stock-context-card" data-view-panel="stock"' in html
    assert 'id="stock-context-card" data-view-panel="watch"' not in html
    assert 'id="stock-context-card" data-view-panel="main"' not in html
    assert "card span-7 focus-card stock-focus-card" in html
    assert "stock-context-panel" in html
    assert "stock-context" in html
    assert "선택 종목</h2>" in html
    assert "stock-selection-status" in html
    assert "검색 또는 후보/요약 행을 선택하세요." in html
    assert "검색, 우선순위, 관찰 후보, 일일 종목 요약에서 선택한 종목의 저장 근거를 확인합니다." in html
    assert "선택 종목 상태" not in html
    assert "stock-detail-card" in html
    assert 'id="stock-detail-card" data-view-panel="stock"' in html
    assert 'id="stock-detail-card" data-view-panel="watch"' not in html
    assert 'id="stock-detail-card" data-view-panel="main"' not in html
    assert "card span-5 focus-card stock-focus-card" in html
    assert "stock-report-panel" in html
    assert "category-detail-card" in html
    assert "category-selection-status" in html
    assert "업종 또는 테마 행을 선택하면 상세 종목과 최근 흐름을 불러옵니다." in html
    assert "selectedCategoryLabel || selectedCategoryDisplayName" in html
    assert html.index('id="candidate-evidence-card"') < html.index('id="stock-context-card"')
    assert 'setViewTab("stock");' in html
    assert "scrollIntoView" in html
    assert "market-notice" in html
    assert "mobile-card-table" in html
    assert "URLSearchParams" in html
    assert "history.replaceState" in html
    assert "item.evidence_label" in html
    assert "구성종목을 포함하지 않는 Toss 저장 ETF 거래대금 기준" in html
    assert "장중 흐름" not in html
    assert "loadIntradayMarketTopForSelectedDate" in html
    assert "intraday_market_top=1&market_top_limit=100&market_top_page_size=20" in html
    assert "선택 종목 리포트" in html
    assert "선택 종목 리포트 리스트" not in html
    assert "report-no-opinion-toggle" in html
    assert 'id="report-no-opinion-toggle" type="checkbox" checked' not in html
    assert "let hideNoOpinionReports = false;" in html
    assert "#stock-detail-card .section-header { align-items: center; flex-direction: row; }" in html
    assert "의견없음 제외" in html
    assert "report-filter-status" in html
    assert "isNoOpinionReport" in html
    assert "renderStockReports(data)" in html
    assert "opinion_normalized" in html
    assert "업종/테마 상세" in html
    assert "업종/테마 최근 흐름" in html
    assert "분류 기준이 완전히 통일되기 전까지는 참고 흐름" in html
    assert "item.target_price_display || `목표가 ${price(item.target_price_value)}`" in html
    assert "item.opinion_display || opinion(item.opinion_normalized)" in html
    assert "`리포트 표기: ${label}`" in html
    assert "data-public-category-id" in html
    assert "data-category-name" not in html
    assert "기간별 수급량" in html
    assert "구분: 주" in html
    assert ".flow-side-lines { display: grid; gap: 2px; text-align: center;" in html
    assert "단위: 주</span></b>${renderInvestorFlowBars" not in html
    assert "weekLabel(item.business_date)" in html
    assert "일별 수급량 및 거래량" in html
    assert "일별 수급량 및 거래량 <span class=\"muted\">해당 월 기본</span>" in html
    assert "data-flow-expand" in html
    assert "sameMonthRows" in html
    assert "일별 수급량 <span class=\"muted\">최근 20영업일 · 최신일 우선</span>" not in html
    assert "최근 20영업일 · 최신일 우선 · 단위: 주" not in html
    assert "일별 시장 거래량" not in html
    assert "data-flow-tab=\"daily-flow\"" in html
    assert "data-flow-tab=\"daily-volume\"" in html
    assert "수급량</button>" in html
    assert "거래량</button>" in html
    assert "data-flow-panel=\"daily-flow\"" in html
    assert "data-flow-panel=\"daily-volume\"" in html
    assert "일별 시장 거래량 <span class=\"muted\">최신일 우선 · 단위: 주</span>" not in html
    assert "flow-bars" in html
    assert "flow-up" in html
    assert "flow-down" in html
    assert ".slice(0, 4)" in html
    assert ".reverse()" in html
    assert 'dominance("개인", item.individual)' in html
    assert 'dominance("외국인", item.foreign)' in html
    assert 'dominance("기관", item.institution)' in html
    assert '${label} ${parsed > 0 ? "순유입" : "순유출"}`' in html
    assert '${label} ${parsed > 0 ? "매수" : "매도"} 우위 ${quantity' not in html
    assert "개인 매수 ${quantity(item.individual_buy)} | 매도 ${quantity(item.individual_sell)}" not in html
    assert "data-flow-tab=\"retail\"" not in html
    assert "data-flow-tab=\"institution\"" not in html
    assert "전체 증권사 보기" not in html
    assert "item.title_display || item.title" in html
    assert "<b>${esc(data.stock_name || \"-\")} ${esc(data.stock_code || \"\")} | ${market}</b>" in html
    assert "brokerDisplay(item.broker_display)" in html
    assert "시장 문맥" in html
    assert "선택 날짜의 Toss 저장 시장·수급 근거를 확인합니다. 최신 당일 조회는 메인 탭의 명시적 요청으로 제공합니다." in html
    assert "Toss 저장 최근 흐름" in html
    assert "주기 데이터 점검" not in html
    assert "저장된 테마 구성 종목 중 선택 날짜에 리포트가 나온 종목" not in html
    assert "투자자 수급 참고" in html
    assert "수급 흐름" in html
    assert "순환매 참고" not in html
    assert "리포트 분류와 저장 ETF 값의 참고 화면입니다. 실제 자금 순환을 계산하지 않습니다." in html
    assert 'id="industry-etf-details" data-view-panel="main"' in html
    assert 'document.getElementById("industry-etf-details").open = true' not in html
    assert "renderRotationCandidateStocks(item.candidate_stocks)" in html
    assert "renderRotationCandidateEtfs(item.candidate_etfs)" in html
    assert "업종 참고 종목" in html
    assert "ETF 참고" in html
    assert "category-trend-details" in html
    assert "수동 좌표가 있는 항목만 예시 이미지에 표시합니다." in html
    assert "펼치면 업종·테마 참고를 불러옵니다" in html
    assert "safePublicCategoryId" in html
    assert 'value.startsWith(`${categoryType}|`)' in html
    assert "syncCategoryFromStock" in html
    assert "dailyStockCategoryAttrs" in html
    assert "data-stock-category-id" in html
    assert "syncCategoryFromStock(stockItem)" in html
    assert "syncCategoryFromStock(picked)" in html
    assert "/api/rotation-overlay" in html
    assert "/assets/cycle.jpg" in html
    assert "/api/flow-trend" in html
    assert "investor-flow-title" in html
    assert "investor-market-rows" in html
    assert "investor-top-rows" not in html
    assert "/api/status" not in html
    assert "/api/scheduler" not in html
    assert "/api/settings" not in html
    assert "안전 설정" not in html
    assert "설정 변경 이력" not in html
    assert "operator-settings" not in html
    assert "admin_audit" not in html
    assert payload["surface"] == "web-view"
    assert payload["read_only"] is True
    assert payload["dates"][0]["category_mapping"]["mapping_basis"] in {
        "dated_snapshot",
        "latest_mapping_fallback",
    }
    assert payload["dates"][0]["category_mapping"]["label"] in {
        "카테고리 스냅샷",
        "최신 저장 분류",
    }
    assert "source-date 카테고리 스냅샷" in payload["category_mapping_summary"]["notice"]
    assert daily_payload["surface"] == "web-view"
    assert daily_payload["public_contract"]["read_only"] is True
    assert daily_payload["public_contract"]["control_exposed"] is False
    assert "observation_summary" not in daily_payload
    assert daily_payload["observation_summary_deferred"] is True
    assert observation_summary_payload["source"] == "stored_report_toss_observation_summary"
    assert observation_summary_payload["read_only"] is True
    assert observation_summary_payload["live_fetch"] is False
    assert daily_payload["market_briefing"]["source"] == "stored_report_toss_market_briefing"
    assert daily_payload["market_briefing"]["scoring"] is False
    assert "market_reference_lines" in daily_payload["market_briefing"]
    assert "turnover_reference_lines" in daily_payload["market_briefing"]
    assert "flow_reference_lines" in daily_payload["market_briefing"]
    assert "index_summary" in daily_payload["market_briefing"]
    assert "turnover_summary" in daily_payload["market_briefing"]
    assert "flow_summary" in daily_payload["market_briefing"]
    assert "notable_stocks" in daily_payload["market_briefing"]
    assert "check_points" in daily_payload["market_briefing"]
    assert "candidate_evidence" not in daily_payload
    assert "periodic_data_needs" not in daily_payload
    assert "toss_recent_flow" in daily_payload
    assert candidate_evidence_payload["surface"] == "web-view"
    assert candidate_evidence_payload["read_only"] is True
    assert candidate_evidence_payload["live_fetch"] is False
    assert candidate_evidence_payload["scoring"] is False
    assert candidate_evidence_payload["recommendation"] is False
    assert "오늘의 관찰 후보" in candidate_evidence_payload["notice"]
    assert "관찰 후보 근거" not in candidate_evidence_payload["notice"]
    assert "rows" in candidate_evidence_payload
    assert "candidates" not in candidate_evidence_payload
    assert all("internal_candidate_signals" not in row for row in candidate_evidence_payload["rows"])
    assert all("internal_missing_information" not in row for row in candidate_evidence_payload["rows"])
    assert all("quality_flags" not in row for row in candidate_evidence_payload["rows"])
    assert all("evidence_notes" not in row for row in candidate_evidence_payload["rows"])
    assert all("opinion_summary" not in row for row in candidate_evidence_payload["rows"])
    assert all("broker_count" not in (row.get("report_summary") or {}) for row in candidate_evidence_payload["rows"])
    assert all("broker_display" not in (row.get("report_summary") or {}) for row in candidate_evidence_payload["rows"])
    assert all("dominant_opinion" not in (row.get("report_summary") or {}) for row in candidate_evidence_payload["rows"])
    assert backtest_observation_payload["surface"] == "web-view"
    assert backtest_observation_payload["read_only"] is True
    assert backtest_observation_payload["live_fetch"] is False
    assert backtest_observation_payload["scoring"] is False
    assert backtest_observation_payload["recommendation"] is False
    assert "리포트 후 흐름" in backtest_observation_payload["notice"]
    assert "리포트 후 반응 관찰" not in backtest_observation_payload["notice"]
    assert stock_detail_payload["surface"] == "web-view"
    assert stock_detail_payload["read_only"] is True
    assert market_payload["surface"] == "web-view"
    assert intraday_payload["surface"] == "web-view"
    assert intraday_payload["read_only"] is True
    assert flow_trend_payload["surface"] == "web-view"
    assert flow_trend_payload["read_only"] is True
    assert flow_trend_payload["live_fetch"] is False
    assert flow_trend_payload["scoring"] is False
    assert category_payload["surface"] == "web-view"
    assert category_payload["read_only"] is True
    assert category_trend_payload["surface"] == "web-view"
    assert category_trend_payload["read_only"] is True
    assert category_mismatch_status == 400
    assert category_mismatch_body == "category type mismatch"
    assert category_trend_mismatch_status == 400
    assert category_trend_mismatch_body == "category type mismatch"
    assert rotation_payload["surface"] == "web-view"
    assert rotation_payload["read_only"] is True
    assert rotation_payload["image"]["path"] == "example/Cycle.jpg"
    assert cycle_status == 200
    assert cycle_content_type == "image/jpeg"
    for public_payload in (
        payload,
        daily_payload,
        candidate_evidence_payload,
        backtest_observation_payload,
        stock_detail_payload,
        market_payload,
        intraday_payload,
        flow_trend_payload,
        category_payload,
        category_trend_payload,
    ):
        _assert_public_safe_payload(public_payload)
    assert post_status == 405
    assert v2_post_status == 405
    assert forbidden_control_route_statuses == {
        ("GET", "/api/status"): 404,
        ("POST", "/api/scheduler/run-now"): 405,
        ("POST", "/api/scheduler/set-enabled"): 405,
        ("POST", "/api/operator/pause"): 405,
        ("POST", "/api/settings/set"): 405,
    }


def test_web_view_server_logs_api_perf_and_gzips_large_json(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "build_web_view_archive_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "blob": "x" * 20_000},
    )

    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        request = urllib.request.Request(base_url + "/api/archive", headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(request, timeout=5) as response:
            first_body = response.read()
            first_content_length = int(response.headers["Content-Length"])
            first_encoding = response.headers.get("Content-Encoding")

        second_request = urllib.request.Request(base_url + "/api/archive", headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(second_request, timeout=5) as response:
            second_body = response.read()
            second_content_length = int(response.headers["Content-Length"])
            second_encoding = response.headers.get("Content-Encoding")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert first_encoding == "gzip"
    assert second_encoding == "gzip"
    assert first_content_length == len(first_body)
    assert second_content_length == len(second_body)
    assert json.loads(gzip.decompress(first_body).decode("utf-8"))["blob"] == "x" * 20_000
    assert gzip.decompress(second_body) == gzip.decompress(first_body)

    records = [
        json.loads(line)
        for line in (tmp_path / "logs" / "api_perf.log").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    assert records[0]["path"] == "/api/archive"
    assert records[0]["cache"] == "miss"
    assert records[0]["gzip"] is True
    assert records[0]["bytes"] == len(first_body)
    assert records[0]["status"] == 200
    assert records[0]["build_ms"] >= 0
    assert records[0]["json_ms"] >= 0
    assert records[1]["path"] == "/api/archive"
    assert records[1]["cache"] == "hit"
    assert records[1]["gzip"] is True
    assert records[1]["bytes"] == len(second_body)


def test_web_view_server_coalesces_concurrent_cache_misses(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    build_count = 0
    build_count_lock = threading.Lock()

    def build_archive(*_args, **_kwargs) -> dict[str, object]:
        nonlocal build_count
        with build_count_lock:
            build_count += 1
        time.sleep(0.1)
        return {"surface": "web-view", "rows": []}

    monkeypatch.setattr(cli_module, "build_web_view_archive_snapshot", build_archive)
    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"

        def fetch_archive() -> dict[str, object]:
            with urllib.request.urlopen(base_url + "/api/archive", timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))

        with ThreadPoolExecutor(max_workers=2) as executor:
            payloads = list(executor.map(lambda _unused: fetch_archive(), range(2)))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert build_count == 1
    assert payloads == [{"surface": "web-view", "rows": []}] * 2
    records = [
        json.loads(line)
        for line in (tmp_path / "logs" / "api_perf.log").read_text(encoding="utf-8").splitlines()
    ]
    assert sorted(record["cache"] for record in records) == ["hit", "miss"]


def test_web_view_api_perf_log_separates_db_time_for_real_builder(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="perf-db-split-1",
                identity_key="perf-db-split-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base_url + "/api/archive", timeout=5) as response:
            assert response.status == 200
            json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    records = [
        json.loads(line)
        for line in (tmp_path / "logs" / "api_perf.log").read_text(encoding="utf-8").splitlines()
    ]
    assert records[-1]["path"] == "/api/archive"
    assert records[-1]["cache"] == "miss"
    assert records[-1]["db_ms"] > 0
    assert records[-1]["build_ms"] >= records[-1]["db_ms"]


def test_web_view_intraday_market_top_route_reuses_cached_base_daily_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = datetime.now().date()
    now = datetime.combine(business_date, datetime_time(9, 30, 0))
    repository.insert_reports(
        [
            Report(
                stock_name="Cache Target",
                stock_code="000001",
                title="Cache Target Report",
                broker_name="NH",
                published_at=now,
                collected_at=now,
                business_date=business_date,
                source_id="intraday-cache-1",
                identity_key="intraday-cache-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_market_top(market: str, **_kwargs):
        if market != "KOSPI":
            return []
        return [
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="000001",
                stock_name="Cache Target",
                stock_end_type="stock",
                current_price=10_500,
                change_price=500,
                change_percent=5.0,
                trade_amount=90_000_000_000,
                trade_volume=1_200_000,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 20, 12, 1, 0),
            )
        ]

    original_build_daily = cli_module.build_web_view_daily_snapshot
    include_modes: list[bool] = []

    def wrapped_build_daily(*args, **kwargs):
        include_intraday = bool(kwargs.get("include_intraday_market_top"))
        include_modes.append(include_intraday)
        if include_intraday:
            raise AssertionError("intraday route should overlay market-top data onto the cached base daily payload")
        return original_build_daily(*args, **kwargs)

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module, "is_business_day", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(cli_module, "build_web_view_daily_snapshot", wrapped_build_daily)

    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base_url + f"/api/daily/{business_date.isoformat()}", timeout=5) as response:
            assert response.status == 200
            json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(
            base_url
            + f"/api/daily/{business_date.isoformat()}?intraday_market_top=1"
            + "&market_top_limit=20&market_top_page_size=20",
            timeout=5,
        ) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    reference = payload["market_commentary"]["intraday_market_top_reference"]
    assert reference["live_fetch"] is True
    assert reference["items"][0]["stock_code"] == "000001"
    assert include_modes == [False]


def test_web_view_daily_json_compaction_omits_none_fields_on_allowlisted_endpoint() -> None:
    payload = {
        "surface": "web-view",
        "required_none": None,
        "stocks": [
            {
                "stock_code": "005930",
                "target_price_min": None,
                "target_price_max": 100_000,
                "primary_category": {"snapshot_date": None, "mapping_source": "latest_mapping_fallback"},
            }
        ],
        "sectors": [{"sector_name": "반도체", "sector_code": None}],
    }

    compacted = cli_module._compact_web_view_json_payload("daily:2026-05-08", payload)

    assert "required_none" not in compacted
    assert "target_price_min" not in compacted["stocks"][0]
    assert "snapshot_date" not in compacted["stocks"][0]["primary_category"]
    assert "sector_code" not in compacted["sectors"][0]


def test_web_view_server_handles_short_concurrent_json_gets(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="concurrent-web-view-1",
                identity_key="concurrent-web-view-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"

        def fetch(path: str) -> int:
            with urllib.request.urlopen(base_url + path, timeout=5) as response:
                response.read()
                return response.status

        paths = ["/api/archive", "/api/daily/2026-05-08", "/api/market", "/api/archive"] * 3
        with ThreadPoolExecutor(max_workers=6) as executor:
            statuses = list(executor.map(fetch, paths))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert statuses == [200] * 12


def test_web_view_rejects_news_observation_collect_post(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=business_date,
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="news-collect-api-1",
                identity_key="news-collect-api-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    calls = []

    def fake_collect(config_arg, repository_arg, *, business_date, limit):
        calls.append((config_arg, repository_arg, business_date, limit))
        raise AssertionError("GET-only web-view must not call the news collector")

    monkeypatch.setattr(cli_module, "_collect_web_view_news_observations", fake_collect)
    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        request = urllib.request.Request(
            base_url + "/api/news-observations/collect",
            data=json.dumps({"date": business_date.isoformat(), "limit": 2}).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Stock-Monitor-Web-Action": "news-observation-collect",
            },
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request, timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert exc_info.value.code == HTTPStatus.METHOD_NOT_ALLOWED
    assert calls == []


def test_web_view_news_observation_collect_uses_candidate_priority_top_two(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 19)
    captured_args = []
    summary_codes = []

    def fake_candidate_snapshot(config_arg, repository_arg, *, business_date, limit):
        assert config_arg is config
        assert repository_arg is repository
        assert business_date == date(2026, 6, 19)
        assert limit == 2
        return {
            "rows": [
                {"stock_name": "LS에코에너지", "stock_code": "229640"},
                {"stock_name": "BNK금융지주", "stock_code": "138930"},
                {"stock_name": "BGF리테일", "stock_code": "282330"},
            ]
        }

    def fake_run(args):
        captured_args.append(args)
        print(
            json.dumps(
                {
                    "saved_observation_count": 2,
                    "saved_evidence_count": 0,
                    "target_stock_count": 2,
                    "live_fetch": True,
                    "writes_db": True,
                    "items": [],
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        )
        return 0

    def fake_summary(_repository, _business_date, *, stock_codes=None):
        summary_codes.append(tuple(stock_codes or ()))
        return {"available": True, "items": []}

    monkeypatch.setattr(cli_module, "build_web_view_candidate_evidence_snapshot", fake_candidate_snapshot)
    monkeypatch.setattr(cli_module, "_run_news_intelligence_briefing_collect", fake_run)
    monkeypatch.setattr(cli_module, "_build_web_view_news_observation_summary", fake_summary)

    status, payload = cli_module._collect_web_view_news_observations(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    assert status == HTTPStatus.OK
    assert payload["ok"] is True
    assert payload["saved_observation_count"] == 2
    assert [args.stock_code for args in captured_args] == [["229640", "138930"]]
    assert summary_codes == [("229640", "138930")]


def test_web_view_news_observation_collect_deduplicates_candidate_stock_codes(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 24)
    captured_stock_codes = []
    summary_codes = []

    def fake_candidate_snapshot(_config, _repository, *, business_date, limit):
        assert business_date == date(2026, 6, 24)
        assert limit == 2
        return {
            "rows": [
                {"stock_name": "DL이앤씨", "stock_code": "375500"},
                {"stock_name": "DL이앤씨", "stock_code": "375500"},
            ]
        }

    def fake_run(args):
        captured_stock_codes.append(list(args.stock_code))
        print(
            json.dumps(
                {
                    "saved_observation_count": 1,
                    "saved_evidence_count": 0,
                    "target_stock_count": 1,
                    "live_fetch": True,
                    "writes_db": True,
                    "items": [],
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        )
        return 0

    def fake_summary(_repository, _business_date, *, stock_codes=None):
        summary_codes.append(tuple(stock_codes or ()))
        return {"available": True, "items": []}

    monkeypatch.setattr(cli_module, "build_web_view_candidate_evidence_snapshot", fake_candidate_snapshot)
    monkeypatch.setattr(cli_module, "_run_news_intelligence_briefing_collect", fake_run)
    monkeypatch.setattr(cli_module, "_build_web_view_news_observation_summary", fake_summary)

    status, payload = cli_module._collect_web_view_news_observations(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )

    assert status == HTTPStatus.OK
    assert payload["target_stock_codes"] == ["375500"]
    assert captured_stock_codes == [["375500"]]
    assert summary_codes == [("375500",)]


def test_web_view_daily_snapshot_scopes_news_summary_to_top_two_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 19)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name=name,
                stock_code=code,
                title=f"{name} report",
                broker_name="Test",
                published_at=datetime(2026, 6, 19, 9, index, 0),
                collected_at=datetime(2026, 6, 19, 9, index, 30),
                source_id=f"daily-top-two-{code}",
                identity_key=f"daily-top-two-{code}",
            )
            for index, (code, name) in enumerate(
                (("000001", "Alpha"), ("000002", "Beta"), ("000003", "Gamma"))
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    candidate_limits = []
    summary_codes = []

    def fake_candidate_snapshot(_config, _repository, *, business_date, limit):
        candidate_limits.append(limit)
        return {
            "rows": [
                {"stock_code": "000001", "stock_name": "Alpha"},
                {"stock_code": "000002", "stock_name": "Beta"},
                {"stock_code": "000003", "stock_name": "Gamma"},
            ]
        }

    def fake_summary(_repository, _business_date, *, stock_codes=None):
        summary_codes.append(tuple(stock_codes or ()))
        return {"available": False, "items": []}

    monkeypatch.setattr(cli_module, "build_web_view_candidate_evidence_snapshot", fake_candidate_snapshot)
    monkeypatch.setattr(cli_module, "_build_web_view_news_observation_summary", fake_summary)

    cli_module.build_web_view_daily_snapshot(config, repository, business_date=business_date)

    assert candidate_limits == [2]
    assert summary_codes == [("000001", "000002")]


def test_web_view_candidate_value_profile_keeps_report_basis_when_news_has_no_match() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["목표가 하향"],
            "missing_information": ["선택일 Toss 저장값 없음", "종목 수급 저장값 없음"],
            "sort_signal": 3,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "매칭 뉴스 없음",
            "direct_count": 0,
            "caution_count": 0,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": False},
        market_reference=None,
        stock_flow_rows=[],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["observation_priority"] == "확인 후보"
    assert profile["value_label"] == "리포트 기준 확인"
    assert profile["time_mode"] == "intraday"
    assert profile["value_reason"] == "목표가 변화가 확인됐고 같은 날짜 뉴스 매칭은 없습니다."
    assert int(profile["sort_value_signal"]) == 3
    assert "score" not in json.dumps(profile, ensure_ascii=False).lower()


def test_web_view_priority_selection_does_not_force_single_report_gap_candidate() -> None:
    assert cli_module._web_view_priority_candidate_is_eligible(
        {
            "report_summary": {"report_count": 1},
            "news_observation_badge": {"available": True, "direct_count": 0},
            "stock_flow_reference": {"available": False},
            "toss_baseline_reference": {"available": False},
        }
    ) is False
    assert cli_module._web_view_priority_candidate_is_eligible(
        {
            "report_summary": {"report_count": 2},
            "news_observation_badge": {"available": True, "direct_count": 0},
            "stock_flow_reference": {"available": False},
            "toss_baseline_reference": {"available": False},
        }
    ) is True


def test_web_view_priority_selection_ignores_non_ordering_toss_close_baseline() -> None:
    assert cli_module._web_view_priority_candidate_is_eligible(
        {
            "report_summary": {"report_count": 1},
            "news_observation_badge": {"available": True, "direct_count": 0},
            "stock_flow_reference": {"available": False},
            "toss_baseline_reference": {"available": True, "affects_ordering": False},
        }
    ) is False


def test_web_view_target_price_decrease_does_not_raise_candidate_priority() -> None:
    common = {
        "summary": SimpleNamespace(mention_count=1, dominant_opinion="매수"),
        "broker_count": 1,
        "target_range": {"available": True},
        "market_reference": None,
        "stock_flow_rows": [],
        "rank_reference": None,
        "report_intensity": {},
        "flow_window_reference": {"available": False},
        "price_volume_reference": {"available": False},
    }

    upward = cli_module._web_view_observation_candidate_profile(
        **common,
        target_revision={"available": True, "direction": "up", "direction_label": "상향"},
    )
    downward = cli_module._web_view_observation_candidate_profile(
        **common,
        target_revision={"available": True, "direction": "down", "direction_label": "하향"},
    )

    assert upward["sort_signal"] == 1
    assert downward["sort_signal"] == 0
    assert downward["observation_priority"] == "확인 후보"


def test_web_view_candidate_evidence_keeps_regular_session_cohort_and_separates_close_reassessment(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 8, 28)
    stocks = (
        ("000001", "Regular One"),
        ("000002", "Regular Two"),
        ("000003", "Close One"),
        ("000004", "Close Two"),
    )
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name=name,
                stock_code=code,
                title=f"{name} report",
                broker_name="Test",
                published_at=datetime(2026, 8, 28, 9, index, 0),
                collected_at=datetime(2026, 8, 28, 9, index, 30),
                source_id=f"close-reassessment-{code}",
                identity_key=f"close-reassessment-{code}",
            )
            for index, (code, name) in enumerate(stocks)
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 8, 28, 16, 0, 0),
            component="poll-news",
            event_type="scheduled-collect",
            status="success",
            business_date=business_date,
            detail="scheduled_run_at=2026-08-28T16:00:00+09:00; target_stock_codes=000001,000002; saved_observations=2",
        )
    )
    repository.save_toss_priority_quote_baselines(
        [
            TossPriorityQuoteBaseline(
                business_date=business_date,
                stock_code="000003",
                stock_name="Close One",
                baseline_time="20:00",
                last_price=30_000,
                currency="KRW",
                source="toss_openapi",
                fetched_at=datetime(2026, 8, 28, 20, 5, 0),
            )
        ]
    )
    monkeypatch.setattr(
        cli_module,
        "_web_view_priority_candidate_is_eligible",
        lambda row: row.get("stock_code") in {"000003", "000004"},
    )

    snapshot = cli_module.build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=4,
        now=datetime(2026, 8, 28, 20, 10, 0),
    )

    assert [row["stock_code"] for row in snapshot["rows"] if row["selected"]] == ["000001", "000002"]
    assert snapshot["selection_basis"] == "regular_session_news_cohort"
    assert snapshot["close_reassessment"]["changed"] is True
    assert [row["stock_code"] for row in snapshot["close_reassessment"]["rows"]] == ["000004", "000003"]


def test_web_view_candidate_value_profile_keeps_no_match_from_reordering_supported_candidate() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["리포트 집중"],
            "missing_information": [],
            "sort_signal": 3,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "매칭 뉴스 없음",
            "direct_count": 0,
            "caution_count": 0,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[object()],
        rank_reference=None,
        current=datetime(2026, 6, 23, 10, 0, 0),
        business_date=date(2026, 6, 23),
    )

    assert profile["value_label"] == "뉴스 매칭 없음"
    assert int(profile["sort_value_signal"]) == 3


def test_web_view_candidate_value_profile_reference_notes_are_public_facing() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["리포트 집중"],
            "missing_information": ["선택일 Toss 저장값 없음", "종목 수급 저장값 없음"],
            "sort_signal": 3,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "종목 뉴스 매칭",
            "independent_count": 1,
            "direct_count": 1,
            "positive_direct_count": 0,
            "primary_caution_count": 0,
            "caution_count": 0,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": True},
        market_reference=None,
        stock_flow_rows=[],
        rank_reference=None,
        current=datetime(2026, 6, 23, 20, 5, 0),
        business_date=date(2026, 6, 23),
    )

    assert profile["reference_notes"] == [
        "뉴스: 종목 직접 매칭",
        "Toss: 선택일 저장값 없음",
        "수급: 저장값 없음",
        "20:00 저장 현재가 기준",
    ]
    rendered = json.dumps(profile, ensure_ascii=False).lower()
    assert "missing" not in rendered
    assert "score" not in rendered


def test_web_view_candidate_value_profile_keeps_base_sort_signal_for_direct_news() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["목표가 상향"],
            "missing_information": [],
            "sort_signal": 1,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "직접 뉴스",
            "connection_label": "종목 뉴스 매칭",
            "independent_count": 1,
            "direct_count": 1,
            "positive_direct_count": 1,
            "primary_caution_count": 0,
            "caution_count": 0,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[object()],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["observation_priority"] == "우선 확인"
    assert profile["value_label"] == "상승 근거 우세"
    assert profile["value_reason"] == "직접 긍정 뉴스 1건이 직접 주의 뉴스보다 우세합니다."
    assert int(profile["sort_value_signal"]) == 1


def test_web_view_candidate_value_profile_keeps_direct_news_ahead_of_support_caution() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["목표가 유지"],
            "missing_information": [],
            "sort_signal": 1,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "직접 뉴스",
            "connection_label": "종목 뉴스 매칭",
            "independent_count": 2,
            "direct_count": 2,
            "positive_direct_count": 2,
            "primary_caution_count": 0,
            "caution_count": 1,
            "market_context_count": 1,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[object()],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["observation_priority"] == "우선 확인"
    assert profile["value_label"] == "상승 근거 우세"
    assert profile["value_reason"] == "직접 긍정 뉴스 2건이 직접 주의 뉴스보다 우세합니다. · 보조 확인 1건 · 시장맥락 1건"


def test_web_view_candidate_value_profile_exposes_direct_evidence_direction_without_trading_call() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["목표가 상향"],
            "missing_information": [],
            "sort_signal": 1,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "직접 뉴스",
            "connection_label": "종목 뉴스 매칭",
            "independent_count": 2,
            "direct_count": 2,
            "positive_direct_count": 2,
            "primary_caution_count": 0,
            "caution_count": 1,
            "market_context_count": 1,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[object()],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["evidence_direction"] == "상승 근거 우세"
    assert profile["evidence_direction_reason"] == "직접 긍정 뉴스 2건이 직접 주의 뉴스보다 우세합니다."
    assert int(profile["sort_value_signal"]) == 1
    rendered = json.dumps(profile, ensure_ascii=False)
    assert "매수" not in rendered
    assert "매도" not in rendered


def test_web_view_candidate_value_profile_marks_conflicting_direct_evidence_without_promotion() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["리포트 집중"],
            "missing_information": [],
            "sort_signal": 3,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "직접 뉴스",
            "connection_label": "뉴스 근거 확인",
            "independent_count": 2,
            "direct_count": 2,
            "positive_direct_count": 1,
            "primary_caution_count": 1,
            "caution_count": 1,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["evidence_direction"] == "직접 근거 상충"
    assert profile["observation_priority"] == "근거 엇갈림"
    assert profile["value_label"] == "직접 근거 상충"
    assert "직접 긍정 뉴스 1건" in profile["value_reason"]
    assert "직접 주의 뉴스 1건" in profile["value_reason"]
    assert int(profile["sort_value_signal"]) == 3


def test_web_view_candidate_value_profile_demotes_direct_caution_evidence() -> None:
    profile = cli_module._web_view_candidate_value_profile(
        candidate_profile={
            "observation_priority": "확인 후보",
            "why_notable": ["리포트 집중"],
            "missing_information": [],
            "sort_signal": 3,
            "sort_density": 1,
        },
        news_badge={
            "available": True,
            "display_label": "주의 뉴스",
            "connection_label": "주의 뉴스 확인",
            "independent_count": 1,
            "direct_count": 1,
            "positive_direct_count": 0,
            "primary_caution_count": 1,
            "caution_count": 1,
            "market_context_count": 0,
        },
        toss_baseline_reference={"available": False},
        market_reference=object(),
        stock_flow_rows=[object()],
        rank_reference=None,
        current=datetime(2026, 6, 19, 10, 0, 0),
        business_date=date(2026, 6, 19),
    )

    assert profile["evidence_direction"] == "하방 위험 우세"
    assert profile["observation_priority"] == "주의 확인"
    assert int(profile["sort_value_signal"]) == 3


def test_web_view_access_code_gate_protects_content_until_login(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    cli_module._write_access_code_record(config, "123456")
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(base_url + "/api/archive", timeout=5)
        login_html = exc_info.value.read().decode("utf-8")
        with pytest.raises(urllib.error.HTTPError) as asset_exc_info:
            urllib.request.urlopen(base_url + "/assets/cycle.jpg", timeout=5)
        with urllib.request.urlopen(base_url + "/health", timeout=5) as health_response:
            health_body = health_response.read().decode("utf-8")
        unauth_post_request = urllib.request.Request(base_url + "/api/archive", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as unauth_post_exc_info:
            urllib.request.urlopen(unauth_post_request, timeout=5)

        wrong_request = urllib.request.Request(
            base_url + "/auth/login",
            data=b"access_code=wrong",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with pytest.raises(urllib.error.HTTPError) as wrong_exc_info:
            urllib.request.urlopen(wrong_request, timeout=5)

        correct_request = urllib.request.Request(
            base_url + "/auth/login",
            data=b"access_code=123456",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        opener = urllib.request.build_opener(NoRedirect)
        with pytest.raises(urllib.error.HTTPError) as redirect_exc_info:
            opener.open(correct_request, timeout=5)
        cookie = redirect_exc_info.value.headers["Set-Cookie"].split(";", 1)[0]

        authed_request = urllib.request.Request(base_url + "/api/archive", headers={"Cookie": cookie})
        with urllib.request.urlopen(authed_request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        post_request = urllib.request.Request(
            base_url + "/api/archive",
            data=b"{}",
            method="POST",
            headers={"Cookie": cookie},
        )
        with pytest.raises(urllib.error.HTTPError) as post_exc_info:
            urllib.request.urlopen(post_request, timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert exc_info.value.code == 401
    assert "입장코드 입력" in login_html
    assert "사용자용 웹뷰" in login_html
    assert asset_exc_info.value.code == 401
    assert health_body == "ok"
    assert unauth_post_exc_info.value.code == 405
    assert wrong_exc_info.value.code == 401
    assert redirect_exc_info.value.code == 303
    assert payload["surface"] == "web-view"
    assert post_exc_info.value.code == 405


def test_web_view_access_code_gate_marks_cookie_secure_behind_https_proxy(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    cli_module._write_access_code_record(config, "123456")
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        correct_request = urllib.request.Request(
            base_url + "/auth/login",
            data=b"access_code=123456",
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Forwarded-Proto": "https",
            },
        )
        opener = urllib.request.build_opener(NoRedirect)
        with pytest.raises(urllib.error.HTTPError) as redirect_exc_info:
            opener.open(correct_request, timeout=5)
        set_cookie = redirect_exc_info.value.headers["Set-Cookie"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert redirect_exc_info.value.code == 303
    assert "; Secure" in set_cookie


def test_web_view_news_connection_does_not_present_stale_krx_as_news_evidence() -> None:
    label, reason = cli_module._web_view_news_observation_connection(
        direct_count=0,
        caution_count=0,
        positive_direct_count=0,
        primary_caution_count=0,
        market_context_count=0,
        krx_reference_status="stale",
    )

    assert label == "관련 뉴스 매칭"
    assert "KRX" not in reason


def test_web_view_marks_partial_toss_capture_instead_of_exact_market_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 10)
    captured_at = datetime(2026, 7, 10, 20, 5)
    repository.save_toss_market_context_snapshots(
        [
            TossMarketContextSnapshot(
                business_date=business_date,
                observed_at=captured_at,
                rank=1,
                stock_code="005930",
                trading_amount=1000,
                trading_volume=100,
                source="toss_openapi",
                checked_at=captured_at,
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=70_000,
                change_percent=1.2,
                volume=100,
                turnover=1000,
                fetched_at=captured_at,
                source="toss_openapi",
            )
        ]
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=captured_at,
            component="toss-market-context",
            event_type="capture",
            status="partial",
            business_date=business_date,
            detail="missing_domains=market_indices,market_flow",
        )
    )

    daily_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=datetime(2026, 7, 10, 21, 0),
    )
    market_snapshot = cli_module.build_web_view_market_snapshot(
        config,
        repository,
        now=datetime(2026, 7, 10, 21, 0),
    )

    freshness = {item["key"]: item for item in daily_snapshot["source_freshness_summary"]["items"]}
    assert daily_snapshot["toss_context"]["capture_status"] == "partial"
    assert daily_snapshot["toss_context"]["missing_domains"] == ["market_indices", "market_flow"]
    assert freshness["toss_market"]["status"] == "partial"
    assert freshness["toss_market"]["exact_date_available"] is False
    assert market_snapshot["capture_status"] == "partial"
    assert market_snapshot["missing_domains"] == ["market_indices", "market_flow"]


def test_web_view_exposes_failed_toss_capture_without_new_snapshot_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 10)
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 7, 10, 20, 5),
            component="toss-market-context",
            event_type="capture",
            status="failed",
            business_date=business_date,
            detail="command_error=provider unavailable",
        )
    )

    daily_snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=business_date,
        now=datetime(2026, 7, 10, 21, 0),
    )
    market_snapshot = cli_module.build_web_view_market_snapshot(
        config,
        repository,
        now=datetime(2026, 7, 10, 21, 0),
    )

    freshness = {item["key"]: item for item in daily_snapshot["source_freshness_summary"]["items"]}
    assert daily_snapshot["toss_context"]["capture_status"] == "failed"
    assert daily_snapshot["toss_context"]["snapshot_date"] is None
    assert freshness["toss_market"]["capture_status"] == "failed"
    assert freshness["toss_market"]["status"] == "missing"
    assert market_snapshot["latest_capture_attempt"]["status"] == "failed"
    assert market_snapshot["snapshot_date"] is None


def test_web_view_priority_indicators_fetches_server_top_two_from_toss(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 10)
    selected_rows = [
        {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "selected": True,
            "market_reference": {"market": "KOSPI", "business_date": "2026-07-10"},
        },
        {
            "stock_code": "035420",
            "stock_name": "NAVER",
            "selected": True,
            "market_reference": {"business_date": "2026-07-10"},
        },
        {
            "stock_code": "000660",
            "stock_name": "SK하이닉스",
            "selected": True,
            "market_reference": {"market": "KOSPI", "business_date": "2026-07-10"},
        },
    ]
    monkeypatch.setattr(
        cli_module,
        "build_web_view_candidate_evidence_snapshot",
        lambda *_args, **_kwargs: {"rows": selected_rows},
    )
    monkeypatch.setattr(
        repository,
        "get_toss_stock_universe_entry_as_of",
        lambda code, *, as_of_date: (
            SimpleNamespace(
                stock_code=code,
                market="KOSDAQ" if code == "035420" else "KOSPI",
                business_date=as_of_date,
            )
            if code == "035420" or code == "005930" and as_of_date == date(2026, 7, 12)
            else None
        ),
    )

    class FakeTossProvider:
        configured = True

        def __init__(self) -> None:
            self.calls = []

        def get_priority_stock_daily_history(self, *, priority_symbols, as_of):
            self.calls.append((priority_symbols, as_of))
            if as_of == date(2026, 7, 12):
                return {
                    "configured": True,
                    "live_fetch": True,
                    "page_size": 200,
                    "max_pages": 4,
                    "fetched_at": f"{as_of.isoformat()}T16:00:00+09:00",
                    "items": [
                        {
                            "symbol": "005930",
                            "candles": [
                                {
                                    "timestamp": f"{as_of.isoformat()}T00:00:00+09:00",
                                    "openPrice": "700",
                                    "highPrice": "702",
                                    "lowPrice": "698",
                                    "closePrice": "701",
                                    "volume": "100",
                                }
                            ],
                            "pages_fetched": 1,
                            "history_status": "complete",
                        },
                        {
                            "symbol": "035420",
                            "candles": [],
                            "pages_fetched": 0,
                            "history_status": "provider_error",
                            "reason": "provider_http_error",
                            "upstream_status": 429,
                        },
                    ],
                }
            items = []
            for code in priority_symbols:
                base_price = 700 if code == "005930" else 1200
                candles = []
                for offset in range(220):
                    candle_date = date.fromordinal(as_of.toordinal() - offset)
                    close = base_price + (220 - offset) / 10
                    candles.append({
                        "timestamp": f"{candle_date.isoformat()}T00:00:00+09:00",
                        "openPrice": str(close - 1),
                        "highPrice": str(close + 2),
                        "lowPrice": str(close - 2),
                        "closePrice": str(close),
                        "volume": str(100 + offset),
                    })
                items.append({
                    "symbol": code,
                    "candles": candles,
                    "pages_fetched": 2,
                    "history_status": "complete",
                })
            return {
                "configured": True,
                "live_fetch": True,
                "page_size": 200,
                "max_pages": 4,
                "fetched_at": f"{as_of.isoformat()}T16:00:00+09:00",
                "items": items,
            }

    provider = FakeTossProvider()
    server = cli_module.create_web_view_server(
        config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=5,
        toss_quote_provider=provider,
    )
    real_urlopen = urllib.request.urlopen
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with real_urlopen(base_url + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
        assert provider.calls == []
        assert 'id="newbby-indicator-refresh"' in page
        assert "/api/indicator-snapshot" not in page
        assert "시장 분류 미확인 · 6자리 코드 조회" in page
        with real_urlopen(base_url + "/api/priority-indicators?date=2026-07-10", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with real_urlopen(base_url + "/api/priority-indicators?date=2026-07-10", timeout=5):
            assert len(provider.calls) == 1
        try:
            real_urlopen(base_url + "/api/priority-indicators?date=2026-07-10&symbols=999999", timeout=5)
        except urllib.error.HTTPError as exc:
            arbitrary_symbol_status = exc.code
        else:
            arbitrary_symbol_status = HTTPStatus.OK
        request = urllib.request.Request(
            base_url + "/api/priority-indicators?date=2026-07-10",
            data=b"",
            method="POST",
        )
        try:
            real_urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            post_status = exc.code
        else:
            post_status = HTTPStatus.OK
        with real_urlopen(base_url + "/api/priority-indicators?date=2026-07-11", timeout=5) as response:
            unclassified_market_payload = json.loads(response.read().decode("utf-8"))
        with real_urlopen(base_url + "/api/priority-indicators?date=2026-07-12", timeout=5) as response:
            invalid_provider_payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert arbitrary_symbol_status == HTTPStatus.BAD_REQUEST
    assert post_status == HTTPStatus.METHOD_NOT_ALLOWED
    assert payload["surface"] == "web-view-priority-indicators"
    assert payload["derived_from"] == "web_view_candidate_evidence_top_2"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is True
    assert payload["writes_stock_monitor_db"] is False
    assert [item["stock_code"] for item in payload["items"]] == ["005930", "035420"]
    assert all(item["available"] is True for item in payload["items"])
    assert payload["items"][0]["snapshot"]["source"] == "Toss OpenAPI · 조정 일봉"
    assert payload["items"][0]["snapshot"]["indicators"]["movingAverages"]["sma200"] is not None
    assert payload["items"][0]["candle_count"] == 220
    assert payload["items"][0]["pages_fetched"] == 2
    assert payload["items"][0]["history_status"] == "complete"
    chart_bars = payload["items"][0]["chart"]["bars"]
    assert len(chart_bars) == 220
    assert [item["time"] for item in chart_bars] == sorted(item["time"] for item in chart_bars)
    assert chart_bars[-1]["sma200"] is not None
    assert chart_bars[-1]["rsi14"] is not None
    assert chart_bars[-1]["macd"] is not None
    assert chart_bars[-1]["macdSignal"] is not None
    assert chart_bars[-1]["obv"] is not None
    assert chart_bars[-1]["atr14"] is not None
    assert payload["items"][1]["market_source"] == "stored_toss_stock_universe"
    assert unclassified_market_payload["items"][0]["available"] is True
    assert unclassified_market_payload["items"][0]["market"] is None
    assert unclassified_market_payload["items"][0]["snapshot"]["market"] == "unknown"
    assert unclassified_market_payload["items"][0]["snapshot"]["symbol"] == "005930"
    assert unclassified_market_payload["items"][1]["available"] is True
    assert invalid_provider_payload["items"][0]["available"] is True
    assert invalid_provider_payload["items"][1]["reason"] == "provider_http_error"
    assert invalid_provider_payload["items"][1]["upstream_status"] == 429
    assert "chart" not in invalid_provider_payload["items"][1]
    assert provider.calls == [
        (("005930", "035420"), business_date),
        (("005930", "035420"), date(2026, 7, 11)),
        (("005930", "035420"), date(2026, 7, 12)),
    ]

def test_web_view_newbby_indicator_snapshot_keeps_missing_states_and_neutral_fields() -> None:
    snapshot = {
        "schemaVersion": 1,
        "code": "005930",
        "symbol": "fixture",
        "market": "KOSPI",
        "timeframe": "D",
        "requestedAsOf": "2026-07-10",
        "barAsOf": "2026-07-09",
        "source": "fixture",
        "sourceFetchedAt": "2026-07-10T16:00:00+09:00",
        "sourceDate": "2026-07-10",
        "barStatus": "provisional",
        "confirmedPolicy": "next-session confirmation",
        "cacheHit": True,
        "cacheAge": 12,
        "stale": True,
        "lastSuccessAt": "2026-07-10T15:50:00+09:00",
        "dataRevision": "fixture-data-v1",
        "calculationVersion": "fixture-calc-v1",
        "sourceCalculationVersion": "cache-v1",
        "servedAt": "2026-07-10T16:00:01+09:00",
        "calculationBasis": {
            "ohlcv": "provider-adjusted daily candles",
            "cutoff": "last candle through requestedAsOf",
            "candlePrecision": "OHLC 4 decimals",
            "sourceSeries": "aligned dashboard series",
        },
        "price": {"open": 1, "high": 2, "low": 1, "close": 2, "volume": 3},
        "indicators": {
            "movingAverages": {
                "sma20": None,
                "sma60": 2,
                "sma120": 3,
                "sma200": 4,
                "ema20": 1,
                "ema60": 2,
                "ema120": 3,
                "ema200": 4,
                "wma20": 1,
                "wma60": 2,
                "wma120": 3,
                "wma200": 4,
                "status": "partial-data",
                "calculationVersion": "technical-v3",
                "emaSeedPolicy": "sma-period",
                "wmaWeights": "linear-oldest-1-newest-period",
            },
            "bollinger20": {"middle": None, "upper": None, "lower": None, "status": "insufficient-data", "period": 20, "multiplier": 2, "stddev": "population", "calculationVersion": "technical-v3"},
            "donchian20": {"upper": 3, "middle": 2, "lower": 1, "status": "ready", "period": 20, "includeCurrent": True, "calculationVersion": "technical-v3"},
            "rsi14": {"value": None, "status": "insufficient-data", "provisional": True, "method": "wilder", "seedPolicy": "simple-average-14-changes"},
            "atr14": {"value": 1, "status": "ready", "provisional": False, "method": "wilder", "seedPolicy": "simple-average-14-true-ranges"},
            "volume": {"barVolume": 3, "ratio20": None, "status": "partial-data", "period": 20, "includeCurrent": True},
            "macd129": {"macd": 1, "signal": None, "histogram": None, "status": "partial-data", "fast": 12, "slow": 26, "signalPeriod": 9, "seedPolicy": "sma-period", "calculationVersion": "technical-v3"},
            "obv": {"value": 3, "delta5": None, "seedTime": "2026-07-09", "status": "partial-data", "delta5Status": "insufficient-data", "seedPolicy": "first-bar-zero-stop-on-gap", "calculationVersion": "technical-v3"},
            "volumeProfile12": {
                "version": "vp-1",
                "method": "close-weighted",
                "from": "2026-06-01",
                "to": "2026-07-09",
                "count": 12,
                "total": 12,
                "binCount": 12,
                "bins": [{"low": index, "high": index + 1, "volume": 1, "share": 1 / 12, "peak": index == 0} for index in range(12)],
                "status": "ready",
            },
        },
        "structures": [
            {
                "family": "horizontal",
                "status": "forming",
                "timeframe": "D",
                "barTime": "2026-07-09",
                "measurements": [
                    {"name": "type", "label": "type", "value": "prior-20-high", "unit": "state"},
                    {"name": "volumeEvidence", "label": "volumeEvidence", "value": "volume-confirmed", "unit": "state"},
                    {"name": "rvol20Previous", "label": "rvol20Previous", "value": 1.5, "unit": "ratio"},
                ],
            },
            {
                "family": "flag",
                "status": "paused",
                "timeframe": "D",
                "barTime": None,
                "measurements": [
                    {"name": "type", "label": "type", "value": "channel", "unit": "state"},
                    {"name": "geometry.kind", "label": "geometry.kind", "value": "channel", "unit": "state"},
                ],
            },
            {
                "family": "triangle",
                "status": "forming",
                "timeframe": "D",
                "barTime": "2026-07-09",
                "measurements": [
                    {"name": "type", "label": "type", "value": "triangle", "unit": "state"},
                    {"name": "geometry.kind", "label": "geometry.kind", "value": "triangle", "unit": "state"},
                    {"name": "volumeEvidence", "label": "volumeEvidence", "value": "volume-insufficient", "unit": "state"},
                    {
                        "name": "geometry.points.2.logicalOffset",
                        "label": "삼각형 시작점부터 교점까지 봉 수 · 직선 외삽",
                        "value": 14,
                        "unit": "projected-bars",
                    },
                    {
                        "name": "geometry.points.2.price",
                        "label": "삼각형 교점 · 직선 외삽값(목표가 아님)",
                        "value": 101.25,
                        "unit": "projected-price",
                    },
                    {
                        "name": "apexRemainingBars",
                        "label": "삼각형 교점까지 남은 봉 · 직선 외삽",
                        "value": 3,
                        "unit": "projected-bars",
                    },
                ],
            },
        ],
        "structureStatus": {"horizontal": "ready", "flag": "paused", "triangle": "ready"},
    }

    public_snapshot = cli_module._web_view_public_newbby_indicator_snapshot(snapshot)

    assert public_snapshot["requestedAsOf"] == "2026-07-10"
    assert public_snapshot["barAsOf"] == "2026-07-09"
    assert public_snapshot["barStatus"] == "provisional"
    assert public_snapshot["sourceFetchedAt"] == "2026-07-10T16:00:00+09:00"
    assert public_snapshot["sourceDate"] == "2026-07-10"
    assert public_snapshot["requestedAsOf"] == "2026-07-10"
    assert public_snapshot["timeframe"] == "D"
    assert public_snapshot["cacheHit"] is True
    assert public_snapshot["stale"] is True
    assert public_snapshot["indicators"]["movingAverages"]["sma20"] is None
    assert set(public_snapshot["indicators"]["movingAverages"]) == {
        "sma20", "sma60", "sma120", "sma200", "ema20", "ema60", "ema120", "ema200",
        "wma20", "wma60", "wma120", "wma200", "status", "calculationVersion", "emaSeedPolicy", "wmaWeights",
    }
    assert {
        "movingAverages", "bollinger20", "donchian20", "rsi14", "atr14", "volume", "macd129", "obv", "volumeProfile12"
    } == set(public_snapshot["indicators"])
    assert public_snapshot["indicators"]["bollinger20"]["status"] == "insufficient-data"
    assert len(public_snapshot["indicators"]["volumeProfile12"]["bins"]) == 12
    assert any(
        item["name"] == "rvol20Previous" and item["value"] == 1.5
        for item in public_snapshot["structures"][0]["measurements"]
    )
    assert public_snapshot["structureStatus"]["flag"] == "paused"
    assert public_snapshot["structures"][1]["measurements"][0]["value"] == "channel"
    triangle_measurements = public_snapshot["structures"][2]["measurements"]
    assert next(item for item in triangle_measurements if item["name"] == "geometry.points.2.logicalOffset")["label"] == "삼각형 시작점부터 교점까지 봉 수 · 직선 외삽"
    assert next(item for item in triangle_measurements if item["name"] == "geometry.points.2.price")["unit"] == "projected-price"
    assert next(item for item in triangle_measurements if item["name"] == "apexRemainingBars")["unit"] == "projected-bars"

    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot({**snapshot, "confidence": 0.9})
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot({**snapshot, "signal": "unknown"})
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot({**snapshot, "source": {"confidence": 0.9}})
    unsupported_macd_signal = {
        **snapshot,
        "indicators": {
            **snapshot["indicators"],
            "rsi14": {**snapshot["indicators"]["rsi14"], "signal": 1},
        },
    }
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot(unsupported_macd_signal)
    unsupported_missing_field = {
        **snapshot,
        "indicators": {
            **snapshot["indicators"],
            "movingAverages": {
                key: value
                for key, value in snapshot["indicators"]["movingAverages"].items()
                if key != "wma200"
            },
        },
    }
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot(unsupported_missing_field)
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot({**snapshot, "timeframe": "H4"})
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot({**snapshot, "barAsOf": "2026-07-11"})
    bad_status = {
        **snapshot,
        "indicators": {
            **snapshot["indicators"],
            "rsi14": {**snapshot["indicators"]["rsi14"], "status": "BUY"},
        },
    }
    bad_bar_status = {**snapshot, "barStatus": "BUY"}
    bad_delta_status = {
        **snapshot,
        "indicators": {
            **snapshot["indicators"],
            "obv": {**snapshot["indicators"]["obv"], "delta5Status": "BUY"},
        },
    }
    bad_structure_status = {
        **snapshot,
        "structures": [
            {**snapshot["structures"][0], "status": "BUY"},
            *snapshot["structures"][1:],
        ],
    }
    bad_type = {
        **snapshot,
        "structures": [
            {
                **snapshot["structures"][0],
                "measurements": [
                    {**item, "value": "BUY"} if item["name"] == "type" else item
                    for item in snapshot["structures"][0]["measurements"]
                ],
            },
            *snapshot["structures"][1:],
        ],
    }
    bad_volume_evidence = {
        **snapshot,
        "structures": [
            {
                **snapshot["structures"][0],
                "measurements": [
                    {**item, "value": "BUY"} if item["name"] == "volumeEvidence" else item
                    for item in snapshot["structures"][0]["measurements"]
                ],
            },
            *snapshot["structures"][1:],
        ],
    }
    bad_geometry_kind = {
        **snapshot,
        "structures": [
            *snapshot["structures"][:2],
            {
                **snapshot["structures"][2],
                "measurements": [
                    {**item, "value": "BUY"} if item["name"] == "geometry.kind" else item
                    for item in snapshot["structures"][2]["measurements"]
                ],
            },
        ],
    }
    for unsupported_snapshot in (
        bad_status, bad_bar_status, bad_delta_status, bad_structure_status,
        bad_type, bad_volume_evidence, bad_geometry_kind,
    ):
        with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
            cli_module._web_view_public_newbby_indicator_snapshot(unsupported_snapshot)
    ready_profile_without_count = {
        **snapshot,
        "indicators": {
            **snapshot["indicators"],
            "volumeProfile12": {
                key: value
                for key, value in snapshot["indicators"]["volumeProfile12"].items()
                if key != "binCount"
            },
        },
    }
    with pytest.raises(cli_module._UnsupportedNewbbyIndicatorSchema):
        cli_module._web_view_public_newbby_indicator_snapshot(ready_profile_without_count)

    page = cli_module._render_web_view_html()
    assert "function renderPriorityIndicatorPriceChart" in page
    assert "function renderPriorityIndicatorAuxChart" in page
    assert "function renderPriorityIndicatorSummary" in page
    assert "loadNewbbyIndicatorSnapshot(selectedDate)" in page
    assert "sourceFetchedAt" in page
    assert "barAsOf" in page
    assert "SMA 20/60/120/200" not in page
    assert "const colors = {sma20:" in page
    assert "MACD 12·26·9" in page
    assert "OBV · 누적 거래량" in page
    assert "RSI 14" in page
    assert "ATR 14" in page
    assert 'Toss ${number(item.candle_count)}봉' in page
    assert '차트 ${number(chartBarCount)}봉' in page
    assert "시그널" in page
    assert "파랑은 MACD, 주황은 시그널" in page
    assert "차트 · 지표 확인" in page
    assert "geometry 없음은 반대 방향의 근거로 취급하지 않습니다." in page
    assert "삼각형 교점 값은 직선 외삽 측정값이며 목표가가 아닙니다." in page
    assert "지원하지 않는 기술 지표 형식입니다." in page
    assert "선택 날짜 Main Top2의 수정주가 일봉과 기술 지표를 조회합니다." in page
    assert "/api/priority-indicators?date=" in page


def test_web_view_newbby_v1_structure_allowlist_covers_all_analyzer_measurement_paths() -> None:
    expected = {
        "horizontal": {
            "type", "boundary", "atr14Previous", "rvol20Previous", "volumeEvidence", "barTime", "close",
        },
        "flag": {
            "type", "poleStartTime", "poleStartPrice", "poleEndTime", "poleEndPrice", "poleMove", "poleAtr",
            "adjustmentStartTime", "discoveredTime", "upper.slope", "upper.intercept", "lower.slope",
            "lower.intercept", "atr14Previous", "anchorTime", "pivotHighTimes", "pivotLowTimes", "containment",
            "barTime", "close", "upperPrice", "lowerPrice", "geometry.kind", "adjustmentBars",
            "rvol20Previous", "volumeEvidence", "retracementRatio", "adjustmentVolumeRatio",
            "pivotHighTimes.1", "pivotLowTimes.3", "geometry.points.4.time", "geometry.points.4.price",
            "geometry.pole.2.time", "geometry.pole.2.price",
        },
        "triangle": {
            "type", "anchorTime", "structureStartTime", "discoveredTime", "upper.slope", "upper.intercept",
            "lower.slope", "lower.intercept", "atr14Previous", "pivotHighTimes", "pivotLowTimes", "contactCount",
            "containment", "barTime", "close", "geometry.kind", "geometry.observedThrough", "structureBars",
            "upperPrice", "lowerPrice", "boundary", "convergenceRatio", "apexRemainingBars", "rvol20Previous",
            "volumeEvidence", "pivotHighTimes.2", "pivotLowTimes.4", "geometry.points.1.time",
            "geometry.points.1.price", "geometry.points.2.anchorTime", "geometry.points.2.logicalOffset",
            "geometry.points.2.price", "geometry.points.3.time", "geometry.points.3.price",
        },
    }

    assert all(
        cli_module._newbby_structure_measurement_name_allowed(family, name)
        for family, names in expected.items()
        for name in names
    )
    assert not cli_module._newbby_structure_measurement_name_allowed("triangle", "confidence")
    assert not cli_module._newbby_structure_measurement_name_allowed("unknown", "type")


def test_calculated_flag_and_triangle_snapshots_pass_public_indicator_allowlist() -> None:
    as_of = date(2026, 7, 10)

    def project(bars: list[dict[str, object]]) -> dict[str, object]:
        return cli_module._web_view_public_newbby_indicator_snapshot(
            cli_module.build_indicator_snapshot(
                code="005930",
                symbol="005930.KS",
                market="KOSPI",
                requested_as_of=bars[-1]["time"],
                candles=bars,
                source="Toss OpenAPI",
                source_fetched_at=f"{as_of.isoformat()}T16:00:00+09:00",
                bar_status="unknown",
                confirmed_policy="Toss candle finality is not identified.",
            )
        )

    flag_bars = []
    for index in range(40):
        if index < 15:
            close, high, low = 100.0, 102.0, 98.0
        elif index < 20:
            close = 100.0 + 6.0 * (index - 14)
            high, low = close + 2.0, close - 2.0
        else:
            close = 130.0
            high = 137.0 if index in {22, 26, 30, 34} else 134.0
            low = 126.0 if index in {24, 28, 32, 36} else 129.0
        flag_bars.append({
            "time": date.fromordinal(as_of.toordinal() - (39 - index)).isoformat(),
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": 100 + index,
        })
    flag_snapshot = project(flag_bars)
    flag_structure = next(item for item in flag_snapshot["structures"] if item["family"] == "flag")
    flag_type = next(item for item in flag_structure["measurements"] if item["name"] == "type")
    assert flag_type["value"] == "channel"

    highs = {18, 22, 26, 30}
    lows = {20, 24, 28, 32}
    triangle_bars = []
    for index in range(35):
        upper = 160 - 1.3 * index
        lower = 60 + 1.3 * index
        high = upper if index in highs else upper - 4
        low = lower if index in lows else lower + 4
        triangle_bars.append({
            "time": date.fromordinal(as_of.toordinal() - 34 + index).isoformat(),
            "open": 110.0,
            "high": high,
            "low": low,
            "close": 110.0,
            "volume": 1000 + index,
        })
    triangle_snapshot = project(triangle_bars)
    triangle = next(item for item in triangle_snapshot["structures"] if item["family"] == "triangle")
    triangle_type = next(item for item in triangle["measurements"] if item["name"] == "type")
    assert triangle_type["value"] == "triangle"
