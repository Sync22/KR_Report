import gzip
import json
import inspect
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

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
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    NewsIntelligenceRun,
    Report,
    ReportLinkedNewsEvidenceRecord,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
    StockMetadata,
    StockThemeMembership,
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
}


def _assert_public_safe_payload(payload) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in PUBLIC_FORBIDDEN_KEYS
            _assert_public_safe_payload(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_public_safe_payload(item)


def _web_view_news_run(
    *,
    run_id: str = "news-web-view-run-1",
    target_date: date = date(2026, 6, 2),
    stock_name: str = "삼성전자",
    stock_code: str = "005930",
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
    relevance: str = "direct",
    sentiment: str = "Positive",
    stock_impact: str = "Strong Positive",
    operator_recommendation: str = "strengthen_report_candidate",
    target_date: date = date(2026, 6, 2),
    krx_reference_date: date | None = date(2026, 6, 2),
) -> ReportLinkedNewsEvidenceRecord:
    return ReportLinkedNewsEvidenceRecord(
        run_id=run_id,
        evidence_key=evidence_key,
        target_date=target_date,
        stock_code="005930",
        stock_name="삼성전자",
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


def test_web_view_main_layout_first_pass_static_markup() -> None:
    html = cli_module._render_web_view_html()

    assert '<section class="card span-12 date-picker-card" aria-label="날짜 선택">' in html
    assert "<h2>날짜 선택</h2>" not in html
    assert html.index('id="daily-briefing-headline"') < html.index('id="briefing-check-points"')
    assert html.index('id="briefing-check-points"') < html.index('id="briefing-one-line-comments"')
    assert html.index('id="briefing-one-line-comments"') < html.index('id="briefing-mood-card"')
    assert html.index('id="briefing-mood-card"') < html.index('class="briefing-reference-card"')
    daily_briefing_body = html.split('class="card span-12 daily-briefing"', 1)[1].split(
        'id="main-priority-card"', 1
    )[0]
    assert "확인 종목" not in daily_briefing_body
    assert 'id="briefing-watch-chips"' not in html
    assert "국장 시장 분위기" in html
    assert 'id="selection-status"' not in html
    assert "현재 선택" not in html
    assert "<h2>업종 요약</h2>" not in html
    assert "<h2>테마 요약</h2>" not in html
    assert "업종/테마 상세" in html
    assert "renderObservationBlock" in html
    assert "renderObservationMoodItem" in html
    assert "const breadthLabel = breadthItems.length ? `<span class=\"observation-item-line muted\">시장 폭 상위 흐름</span>` : \"\";" in html
    assert html.index("${observationLine}") < html.index("${breadthLabel}")
    assert "item.observation_line" in html
    assert "renderObservationReportItem" in html
    assert "renderObservationFlowItem" in html
    assert "renderObservationPriceItem" in html
    assert "observation-info-wrap" in html
    assert "observation-help-card" in html
    assert "renderSectorBreadthBars" in html
    assert "sector-breadth-bar" in html
    assert "renderTopTwoReviewCandidates" in html
    assert 'id="news-observation-summary"' in html
    assert "renderNewsObservationSummary" in html
    assert "top-two-candidates" in html
    assert "우선 확인 2개" in html
    top_two_renderer = html[
        html.index("function renderTopTwoReviewCandidates") : html.index("function candidateIntradayReferenceLabel")
    ]
    assert "핵심 저장 정보 있음" not in top_two_renderer
    assert "<span>부족한 정보: ${esc(candidateCompactLabel(gapItems, 1))}</span>" in top_two_renderer
    assert "${missingLine}" in top_two_renderer
    assert "순환매 참고 종목" in html
    assert "순환매 참고 ETF" in html
    assert "renderTargetPriceTrailRows" in html
    assert "renderDailyReferenceRows" in html
    assert "data-flow-expand" in html
    assert "dailyFlowExpanded" in html
    assert "sameMonthRows" in html
    assert 'id="intraday-market-top-check"' in html
    assert 'id="intraday-market-top-status"' in html
    assert 'id="intraday-market-top-overlap"' in html
    assert 'id="intraday-market-top-overlap" class="intraday-overlap-panel" hidden' in html
    assert ".intraday-overlap-panel[hidden] { display: none; }" in html
    assert "Naver 장중 참고" in html
    assert "loadIntradayMarketTopForSelectedDate" in html
    assert "intradayMarketTopCooldownMs" in html
    assert "Naver 장중 참고는 30초 간격으로 확인할 수 있습니다." in html
    assert "renderIntradayMarketTopOverlap" in html
    assert "intraday-overlap-chip" in html
    assert "호출 ${number(calls)}회" in html


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
        "display_label": "뉴스 관찰 없음",
        "reason": "저장된 뉴스 관찰 없음",
        "direct_count": 0,
        "caution_count": 0,
        "market_context_count": 0,
        "krx_reference_status": "missing",
        "top_titles": [],
        "empty_state": "저장된 뉴스 관찰 없음",
        "missing_context": ["stored_news_observation"],
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
    assert summary["display_label"] == "주의 뉴스 확인"
    assert summary["reason"] == "주의 문구가 있어 리포트 근거와 함께 확인합니다."
    assert summary["direct_count"] == 1
    assert summary["caution_count"] == 1
    assert summary["market_context_count"] == 1
    assert summary["krx_reference_status"] == "exact"
    assert summary["top_titles"] == [
        "삼성전자, AI 반도체 공급 계약 체결",
        "삼성전자, 변동성 확대 주의",
    ]
    assert "overall_sentiment" not in summary
    assert "sentiment_score" not in json.dumps(summary, ensure_ascii=False)
    assert "stock_impact" not in json.dumps(summary, ensure_ascii=False)
    assert "operator_recommendation" not in json.dumps(summary, ensure_ascii=False)
    _assert_public_safe_payload(snapshot)


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
                market="STK",
                investor_type="개인",
                net_buy_volume=-50,
                net_buy_amount=-100,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="STK",
                investor_type="외국인",
                net_buy_volume=100,
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
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
                market="STK",
                investor_type="외국인",
                net_buy_volume=500,
                net_buy_amount=1_000,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="개인",
                net_buy_volume=-300,
                net_buy_amount=-600,
                volume_unit="주",
                amount_unit="원",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
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
    }
    assert snapshot["krx_context"]["available"] is True
    assert snapshot["krx_context"]["snapshot_date"] == "2026-05-08"
    assert snapshot["krx_context"]["top_kospi_by_turnover"][0]["stock_code"] == "000660"
    assert snapshot["krx_context"]["top_kospi_by_turnover"][0]["volume"] == 50_000
    assert snapshot["krx_recent_flow"] == {
        "available": True,
        "source": "krx",
        "business_date": "2026-05-08",
        "reference_date": "2026-05-08",
        "exact_date_available": True,
        "notice": "선택 날짜를 포함한 최근 KRX 저장 스냅샷 기준입니다. 실시간값이나 확정 판단은 포함하지 않습니다.",
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
                },
                "kosdaq_top_by_turnover": None,
                "etf_top_by_turnover": None,
            },
        ],
    }
    assert snapshot["krx_investor_flow"]["available"] is True
    assert snapshot["krx_investor_flow"]["source"] == "krx_data_market"
    assert snapshot["krx_investor_flow"]["data_scope"] == "stored_krx_data_market_sample"
    assert snapshot["krx_investor_flow"]["live_fetch"] is False
    assert snapshot["krx_investor_flow"]["scoring"] is False
    assert snapshot["krx_investor_flow"]["market_flows"][0]["investor_type"] == "외국인"
    assert snapshot["krx_investor_flow"]["market_flows"][0]["investor_label"] == "외국인"
    assert snapshot["krx_investor_flow"]["market_flows"][0]["market_label"] == "KOSPI"
    assert snapshot["krx_investor_flow"]["market_flows"][0]["net_buy_amount"] == 200
    assert snapshot["krx_investor_flow"]["market_flows"][1]["investor_type"] == "개인"
    assert snapshot["krx_investor_flow"]["net_buy_top"][0]["stock_code"] == "005930"
    assert snapshot["krx_investor_flow"]["net_buy_top"][0]["investor_label"] == "외국인"
    assert snapshot["krx_investor_flow"]["net_buy_top"][0]["market_label"] == "KOSPI"
    assert snapshot["krx_investor_flow"]["net_buy_top"][0]["net_buy_amount"] == 300
    assert snapshot["market_reference_notice"] == "KRX 저장 스냅샷 기준입니다."
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
    assert mood_card["source"] == "stored_report_krx_market_mood_card"
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
    assert connect_count <= 14


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
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
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
    assert "외국인 순매수 상위 참고" in snapshot["rows"][1]["evidence_layers"]["support"]
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
        "KRX 가격 참고",
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
        "선택일 KRX 저장값 없음",
        "종목 수급 저장값 없음",
    ]
    assert public_snapshot["rows"][0]["evidence_layers"]["primary"] == []
    assert public_snapshot["rows"][0]["evidence_layers"]["support"] == []
    assert public_snapshot["rows"][0]["evidence_layers"]["gap"] == public_snapshot["rows"][0]["missing_information"]
    assert "quality_flags" not in public_snapshot["rows"][0]
    assert internal_snapshot["rows"][0]["internal_missing_information"][:2] == [
        "당일 KRX 없음",
        "종목 수급 데이터 없음",
    ]


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
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
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
        "KRX 가격 참고",
        "거래대금 참고",
        "거래량 위치 참고",
        "외국인 순매수 상위 참고",
    ]
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
            )
            for code, name in (("000001", "RankReference"), ("000999", "PlainReference"))
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
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
    assert "외국인 순매수 상위 참고" in snapshot["rows"][1]["evidence_layers"]["support"]


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
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
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
    assert "외국인 순매수 상위 참고" in snapshot["rows"][1]["evidence_layers"]["support"]
    assert snapshot["rows"][1]["missing_information"] == ["종목 수급 저장값 없음"]
    assert internal_snapshot["rows"][1]["internal_candidate_signals"][-1] == "외국인 순매수 상위"


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
    assert snapshot["rows"][0]["why_notable"] == ["리포트 집중", "목표가 상향"]
    assert snapshot["rows"][0]["missing_information"] == []
    assert snapshot["rows"][1]["why_notable"] == ["리포트 집중", "목표가 상향"]
    assert "외국인 순매수 상위 참고" in snapshot["rows"][1]["evidence_layers"]["support"]
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


def test_web_view_daily_krx_context_is_exact_date_and_does_not_fallback_to_latest(tmp_path, monkeypatch) -> None:
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

    assert missing_context_snapshot["krx_context"]["available"] is False
    assert missing_context_snapshot["krx_context"]["snapshot_date"] is None
    assert missing_context_snapshot["krx_context"]["top_kospi_by_turnover"] == []
    assert missing_context_snapshot["stocks"][0]["market_reference"] is None
    assert "최신 날짜 값으로 대체하지 않습니다" in missing_context_snapshot["krx_context"]["notice"]

    context = exact_context_snapshot["krx_context"]
    assert context["available"] is True
    assert context["source"] == "krx"
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
    }
    assert context["indices"][0]["index_name"] == "코스피"
    assert "scheduler_tasks" not in context
    assert "worker_states" not in context
    assert "db_path" not in context
    _assert_public_safe_payload(missing_context_snapshot)
    _assert_public_safe_payload(exact_context_snapshot)


def test_web_view_recent_krx_flow_exposes_actual_reference_date_when_fallback(tmp_path, monkeypatch) -> None:
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
            )
        ]
    )

    snapshot = cli_module.build_web_view_daily_snapshot(
        config,
        repository,
        business_date=date(2026, 5, 11),
        now=datetime(2026, 5, 11, 16, 0, 0),
    )

    assert snapshot["krx_context"]["available"] is False
    assert snapshot["krx_recent_flow"]["business_date"] == "2026-05-11"
    assert snapshot["krx_recent_flow"]["reference_date"] == "2026-05-08"
    assert snapshot["krx_recent_flow"]["exact_date_available"] is False
    assert "최근 KRX 저장 스냅샷" in snapshot["krx_recent_flow"]["notice"]


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
            )
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
            )
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
    assert snapshot["investor_flow"]["available"] is True
    assert snapshot["investor_flow"]["data_scope"] == "stored_krx_data_market_sample"
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
            "opinion_display": "매수",
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
    assert cli_module._web_view_opinion_display("buy") == "매수"
    assert cli_module._web_view_opinion_display("neutral") == "중립"
    assert cli_module._web_view_opinion_display("sell") == "매도"


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


def test_web_view_market_snapshot_exposes_krx_reference_without_admin_state(tmp_path, monkeypatch) -> None:
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
    assert snapshot["krx_snapshot_date"] == "2026-05-07"
    assert snapshot["krx_top_kospi_stocks"][0]["stock_code"] == "005930"
    assert snapshot["krx_top_etfs"][0]["etf_code"] == "069500"
    assert snapshot["krx_market_indices"][0]["index_name"] == "코스피"
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
                market="STK",
                investor_type="외국인",
                net_buy_amount=200,
                volume_unit="주",
                amount_unit="원",
                fetched_at=fetched_at,
            ),
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                market="KSQ",
                investor_type="개인",
                net_buy_amount=-150,
                volume_unit="주",
                amount_unit="원",
                fetched_at=fetched_at,
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
    assert snapshot["data_scope"] == "stored_krx_data_market_sample"
    assert snapshot["live_fetch"] is False
    assert snapshot["scoring"] is False
    assert [item["business_date"] for item in snapshot["items"]] == ["2026-05-08", "2026-05-07"]
    assert snapshot["items"][0]["market_flows"][0]["market_label"] == "KOSPI"
    assert snapshot["items"][0]["market_flows"][0]["investor_label"] == "외국인"
    assert snapshot["items"][0]["foreign_net_buy_top"][0]["stock_code"] == "005930"
    assert "scheduler_tasks" not in snapshot
    assert "worker_states" not in snapshot
    _assert_public_safe_payload(snapshot)


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
    assert snapshot["highlights"][0]["label"] == "우주항공"
    assert snapshot["highlights"][0]["evidence_label"] == "리포트 1건 / 1종목"
    assert "추천" not in snapshot["notice"]
    assert "확정 판단" in snapshot["notice"]
    _assert_public_safe_payload(snapshot)


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
        with urllib.request.urlopen(base_url + "/api/archive", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base_url + "/api/daily/2026-05-08", timeout=5) as response:
            daily_payload = json.loads(response.read().decode("utf-8"))
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
    assert "Daily Report" in html
    assert 'data-view-tab="main"' in html
    assert 'data-view-tab="watch"' in html
    assert 'data-view-tab="stock"' in html
    assert 'data-view-tab="market"' in html
    assert 'data-view-tab="rotation"' in html
    assert html.index('data-view-tab="main"') < html.index('data-view-tab="watch"')
    assert html.index('data-view-tab="watch"') < html.index('data-view-tab="stock"')
    assert html.index('data-view-tab="stock"') < html.index('data-view-tab="market"')
    assert html.index('data-view-tab="market"') < html.index('data-view-tab="rotation"')
    assert 'data-view-tab="main" aria-current="page" aria-pressed="true"' in html
    assert 'data-view-tab="watch" aria-current="false" aria-pressed="false"' in html
    assert 'button.setAttribute("aria-current", isActive ? "page" : "false");' in html
    assert 'button.setAttribute("aria-pressed", isActive ? "true" : "false");' in html
    assert "moveViewTabFromKeyboard" in html
    assert '["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)' in html
    assert 'page.keyboard.press("ArrowRight")' not in html
    assert 'class="card span-12 market-reference-card" id="market-reference-card" data-view-panel="market" hidden open' in html
    assert 'document.getElementById("market-reference-card").open = true' in html
    assert "눈에 띄는 종목" in html
    assert 'item.turnover_display || compactAmount(item.turnover, "원")' in html
    assert "리포트 후 흐름" in html
    assert "<th>리포트 후 반응</th>" in html
    assert "<th>D+1</th><th>D+5</th><th>D+10</th><th>D+20</th>" not in html
    assert 'id="backtest-observation-rows"><tr><td colspan="5"' in html
    assert 'backtest-observation-rows").innerHTML = `<tr><td colspan="5"' in html
    assert 'backtest-observation-rows").innerHTML = \'<tr><td colspan="5"' in html
    assert 'colspan="8"' not in html
    assert "관찰 후보 근거" not in html
    assert "리포트 후 반응 관찰" not in html
    assert "read-only</span>" not in html
    assert "저장 기준</span>" in html
    assert "관찰 근거" in html
    assert "candidate-evidence-rows" in html
    assert "backtest-observation-rows" in html
    assert (
        'class="card span-12 main-priority-card" id="main-priority-card" '
        'data-view-panel="main"'
    ) in html
    assert ".main-priority-card { order: -1; }" in html
    main_priority_body = html.split('id="main-priority-card"', 1)[1].split(
        'id="candidate-evidence-card"', 1
    )[0]
    daily_briefing_body = html.split('class="card span-12 daily-briefing"', 1)[1].split(
        'id="main-priority-card"', 1
    )[0]
    assert 'id="intraday-market-top-check"' in main_priority_body
    assert 'id="intraday-market-top-status"' in main_priority_body
    assert 'id="intraday-market-top-overlap" class="intraday-overlap-panel" hidden' in main_priority_body
    assert "전체 근거는 관찰 탭에서 확인합니다." in main_priority_body
    assert "메인은 오늘 먼저 볼 2종만 압축합니다." not in html
    assert 'class="live-source-pill"' not in main_priority_body
    assert ".live-source-pill" not in html
    assert 'id="intraday-market-top-check"' not in daily_briefing_body
    assert 'id="intraday-market-top-status"' not in daily_briefing_body
    assert 'id="candidate-evidence-card" data-view-panel="watch"' in html
    assert 'id="candidate-evidence-card" data-view-panel="main"' not in html
    assert 'id="observation-summary-card" data-view-panel="watch" hidden' in html
    assert 'id="observation-summary-card" data-view-panel="main"' not in html
    assert "관찰 탭은 전체 후보 근거와 리포트 후 흐름을 함께 확인하는 화면입니다." in html
    assert "candidate-evidence-panel" in html
    assert 'id="backtest-observation-card" data-view-panel="watch"' in html
    assert html.index('id="main-priority-card"') < html.index('id="observation-summary-date"')
    assert html.index('id="candidate-evidence-card"') < html.index('id="observation-summary-card"')
    assert html.index('id="observation-summary-card"') < html.index('id="backtest-observation-card"')
    assert html.index('id="candidate-evidence-card"') < html.index('id="backtest-observation-card"')
    assert html.index('id="candidate-evidence-rows"') < html.index('id="backtest-observation-card"')
    assert html.index('id="candidate-evidence-card"') < html.index('id="stock-rows"')
    assert "renderCandidateEvidence(data.candidate_evidence)" not in html
    assert "loadCandidateEvidence(date)" in html
    assert 'document.getElementById("main-priority-rows").innerHTML = message;' in html
    assert 'if (activeViewTab === "main") {\n        await loadCandidateEvidence(date);' in html
    load_daily_body = html.split("async function loadDaily(date)", 1)[1].split("function renderDailyBriefing", 1)[0]
    assert "loadBacktestObservation(date)" not in load_daily_body
    assert "loadEtfTrend(date)" not in load_daily_body
    assert "loadFlowTrend(date)" not in load_daily_body
    assert "loadTabDataForActiveView(date)" in load_daily_body
    assert "loadBacktestObservation(date)" in html
    assert "renderBacktestObservation" in html
    assert "renderObservationEvidenceNotes" in html
    assert "reactionSummaryLabel(item.reaction_windows)" in html
    assert "candidateDisplayFlags(item.quality_flags)" not in html
    assert "observationEvidenceNotesForDisplay(notes)" in html
    assert 'new Set(["missing_stock_flow", "rank_not_present"])' not in html
    assert 'new Set(["당일 수급 없음", "외국인 순매수 상위 미포함"])' in html
    assert "backtest-observation-show-more" in html
    assert "const BACKTEST_OBSERVATION_DEFAULT_LIMIT = 6" in html
    assert "let backtestObservationVisibleLimit = BACKTEST_OBSERVATION_DEFAULT_LIMIT" in html
    assert "rows.slice(0, backtestObservationVisibleLimit)" in html
    assert "/api/observation/backtest" in html
    assert "진행률 해석 주의" in html
    assert "targetValidationLabel(target)" in html
    assert "최대 진행" in html
    assert "도달 " in html
    assert "candidateTargetMetrics(report, item.target_price_progress)" in html
    assert "candidateFlowMetrics(rank, turnover, flowLine)" in html
    assert "candidateMarketInline(item.market_reference)" in html
    assert "candidateIntradayReferenceLabel(item.intraday_reference)" in html
    assert "candidate-intraday-line" in html
    assert "실시간 소스 미확정" in html
    assert "candidate-info-grid" in html
    assert "candidate-title-stock" in html
    assert "candidate-stock-name" in html
    assert "candidate-stock-code" in html
    assert "candidate-title-separator" in html
    assert ".candidate-title-separator { width: 1px; align-self: stretch;" in html
    assert "candidate-quality-grid" in html
    assert "quality-chip--why" in html
    assert "quality-chip--support" in html
    assert "quality-chip--missing" in html
    assert ".candidate-quality-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr) minmax(0, .95fr);" in html
    assert ".candidate-quality-grid .quality-line:first-child { grid-column: span 2;" not in html
    assert "renderQualityChips(whyNotable, \"quality-chip--why\", 2)" in html
    assert "renderQualityChips(supportEvidence, \"quality-chip--support\", 3)" in html
    assert "renderQualityChips(missingInformation, \"quality-chip--missing\", 1)" in html
    assert "candidateCompactLabel(whyItems, 2)" in html
    assert "candidateCompactLabel(gapItems, 1)" in html
    assert "candidateEvidenceLayers(item)" in html
    assert "candidateWhyDisplayItems(layers.primary)" in html
    assert "return values;" in html
    assert "브로커 폭" not in html
    assert 'item !== "브로커 폭"' not in html
    assert "quality-chip-overflow" in html
    assert "QUALITY_CHIP_VISIBLE_LIMIT = 6" in html
    assert ".quality-chip.quality-chip--why" in html
    assert ".candidate-quality-grid .quality-line { display: block;" in html
    assert ".candidate-quality-grid .quality-chip { margin: 0 6px 5px 0;" in html
    assert "border-bottom: 1px solid rgba(222,216,204,.8)" in html
    assert "candidate-target-grid" in html
    assert "candidate-market-inline" in html
    assert ".candidate-market-inline span:first-child" in html
    assert "font-size: 18px; font-weight: 900;" in html
    assert "candidate-flow-grid" in html
    assert ".candidate-evidence-grid { display: grid; grid-template-columns: minmax(120px, .72fr) minmax(0, 1.14fr) minmax(0, 1.14fr);" in html
    assert ".candidate-target-grid { grid-template-columns: repeat(3, minmax(0, 1fr));" in html
    assert ".candidate-target-grid, .candidate-flow-grid { grid-template-columns: repeat(2, minmax(0, 1fr));" in html
    assert ".candidate-evidence-grid { grid-template-columns: 1fr; }" in html
    assert '["의견", opinion(report.dominant_opinion)]' not in html
    assert "증권사 ${number(report.broker_count)}곳" not in html
    assert "<b>KRX</b>" not in html
    assert "renderTopTwoReviewCandidates(rows) + rows.map" not in html
    assert 'document.getElementById("candidate-evidence-rows").innerHTML = rows.map' in html
    assert 'document.getElementById("main-priority-rows").innerHTML = renderTopTwoReviewCandidates(rows);' in html
    assert "오늘의 우선순위" in html
    assert '<p class="brief" id="candidate-evidence-notice"></p>' in html
    assert 'document.getElementById("candidate-evidence-notice").textContent = "";' in html
    assert "${market} <span class=\"status-pill\"" in html
    assert '["순매수", rank || "순매수 상위 없음"]' in html
    assert '["외국인/기관", flowLine || "-"]' in html
    assert '["거래대금", turnover || "-"]' in html
    assert 'replace(/\\s*·\\s*/g, "<br>")' in html
    assert 'item.observation_priority || "우선 확인"' in html
    assert "compactTurnover(item.market_reference.turnover)" in html
    assert "목표가/지표" in html
    assert "괴리/진행 계산 불가" in html
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
    assert "선택 날짜 KRX 마감 대기" in html
    assert "선택 날짜 KRX 마감값 없음" not in html
    assert "marketReference(item.market_reference, krxSnapshotMissing)" in html
    assert "archive-category-summary" not in html
    assert "카테고리 기준:" not in html
    assert "archive-calendar" in html
    assert "calendar-prev" in html
    assert "calendar-next" in html
    assert "stock-search-input" in html
    assert "stock-search-results" in html
    assert "stock-search-status" in html
    assert "현재 날짜 종목명/코드" in html
    assert "날짜를 선택하면 현재 날짜 종목을 찾을 수 있습니다." in html
    assert "stockSearchDefaultStatus" in html
    assert "syncStockSearchInput" in html
    assert "renderStockSearchResults" in html
    assert "selectStockFromSearch" in html
    assert "오늘 읽을 요약" in html
    assert "daily-briefing-headline" in html
    assert "briefing-report-flow" not in html
    assert "briefing-turnover" in html
    assert "briefing-investor-flow" in html
    assert "briefing-market-index" not in html
    assert "briefing-market-index-title" not in html
    assert "briefing-turnover-title" in html
    assert "시장 참고" in html
    assert "briefing-reference-head" in html
    assert "briefing-reference-title" in html
    assert "briefingReferenceTitle" in html
    assert "briefingIndexPair" not in html
    assert "briefing-box span:empty" in html
    assert "briefingPairTitle" in html
    assert 'label: ""' in html
    assert "briefing-investor-flow-sub" in html
    assert "briefing-market-row" in html
    assert "briefing-reference-card" in html
    assert "briefing-reference-divider" in html
    assert "briefing-card-lines" in html
    assert "briefing-flow-lines" in html
    assert "briefing-detail-flow" in html
    assert "renderBriefingDetailLine" in html
    assert "09:15" in html
    assert "12:00" in html
    assert "15:15" in html
    assert "item.time" in html
    assert "setBriefingPairValue" in html
    assert "눈에 띄는 업종" not in html
    assert "briefing-watch-chips" not in html
    assert "briefing-check-points" in html
    assert "renderBriefingCheckPoints" in html
    assert "briefingTurnoverPair" in html
    assert "top_items" in html
    assert 'items.map((item) => `${esc(item.stock_name' not in html
    assert 'indices.map((item) => `${esc(item.index_series' not in html
    assert "renderDailyBriefing(data)" in html
    assert "date-calendar-cell" in html
    assert "class=\"weekday\"" not in html
    assert "선택 날짜 KRX 시장 참고" in html
    assert "현재 선택" not in html
    assert "선택 상태" not in html
    assert "stock-single-toggle" in html
    assert "1건 포함" in html
    assert "stock-show-more" in html
    assert "const DAILY_STOCK_DEFAULT_LIMIT = 6" in html
    assert "let dailyStockVisibleLimit = DAILY_STOCK_DEFAULT_LIMIT" in html
    assert "filteredStocks.slice(0, dailyStockVisibleLimit)" in html
    assert "리포트 요약 지표" not in html
    assert "추천이나 점수가 아니라" not in html
    assert "추천 순위" not in html
    assert "추천이나 매수/매도" not in html
    assert "저장 데이터 기반 확인용입니다" in html
    assert "업종 분류 데이터 정비 후 표시합니다" not in html
    assert "공유 화면 기준" not in html
    assert "관리자 제어 없음" not in html
    assert "public-contract" not in html
    assert "scroll-panel" in html
    assert "stock-summary-panel" in html
    assert "Number.isFinite" in html
    assert "const price = (value) => compactAmount(value, \"원\")" in html
    assert "const compactTurnover = (value, unit = \"원\")" in html
    assert "compactTurnover(item.market_reference.turnover)" in html
    assert "거래대금 ${compactTurnover(entry.horizon_turnover)}" in html
    assert "${compactTurnover(item.turnover)}</span>" in html
    assert html.count('labeled("거래대금", compactTurnover(item.turnover))') >= 8
    assert 'labeled("거래대금", compactAmount(item.turnover))' not in html
    assert "${compactTurnover(item.turnover)} · ${percent(item.change_percent)}" in html
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
    assert html.index('id="stock-detail-card"') < html.index('id="backtest-observation-card"')
    assert 'setViewTab("stock");' in html
    assert "scrollIntoView" in html
    assert "market-notice" in html
    assert "mobile-card-table" in html
    assert "URLSearchParams" in html
    assert "history.replaceState" in html
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
    assert "KRX 시장 참고" in html
    assert "시장 탭은 해석 문장이 아니라 선택 날짜의 저장 KRX/수급 근거를 확인하는 화면입니다." in html
    assert "KRX 최근 흐름" in html
    assert "주기 데이터 점검" not in html
    assert "저장된 테마 구성 종목 중 선택 날짜에 리포트가 나온 종목" not in html
    assert "투자자 수급 참고" in html
    assert "수급 흐름" in html
    assert "순환매 참고" in html
    assert "순환매 탭은 업종/테마 흐름과 ETF 참고를 같은 보조 관찰 축으로 묶어 봅니다." in html
    assert "rotation-details" in html
    assert 'document.getElementById("rotation-details").open = true' in html
    assert "renderRotationCandidateStocks(item.candidate_stocks)" in html
    assert "renderRotationCandidateEtfs(item.candidate_etfs)" in html
    assert "순환매 참고 종목" in html
    assert "순환매 참고 ETF" in html
    assert "category-trend-details" in html
    assert "업종 기준 좌표" in html
    assert "펼치면 순환매 참고 이미지를 불러옵니다" in html
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
    assert "investor-top-rows" in html
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
    assert daily_payload["market_briefing"]["source"] == "stored_report_krx_market_briefing"
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
    assert "krx_recent_flow" in daily_payload
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


def test_web_view_browser_smoke_checks_tablet_and_large_mobile_viewports() -> None:
    source = inspect.getsource(cli_module._collect_web_view_browser_render_smoke_issues)

    assert '"desktop", "width": 1366, "height": 900' in source
    assert '"tablet", "width": 768, "height": 1024' in source
    assert '"large_mobile", "width": 430, "height": 932' in source
    assert '"mobile", "width": 390, "height": 844' in source
    assert "#intraday-market-top-check" in source
    assert "#intraday-market-top-overlap" in source
    assert "intraday_overlap_panel" in source
    assert "intraday_overlap_initial_visible" in source
    assert "intraday_overlap_visible_before_check" in source
    assert "#observation-summary-card" in source
    assert "observation_summary_main_visible" in source
    assert "watch_observation_summary_visible" in source
    assert "observation_summary_visible_on_main" in source
    assert "watch_observation_summary_missing" in source
    assert 'for text in ("오늘 읽을 요약", "오늘의 우선순위")' in source
    assert '"국장 관찰 요약")' not in source
    assert ".is_visible()" in source


def test_web_view_intraday_market_top_button_js_has_safe_click_flow() -> None:
    html = cli_module._render_web_view_html()

    assert "currentStatus.can_overlap_intraday_market_top === false" in html
    assert "장중 참고 데이터를 가져오지 못했습니다. 저장된 요약을 계속 표시합니다." in html
    assert "Naver 장중 참고 오류" in html
    assert "장중 거래대금 상위와 리포트 언급이 겹친 종목이 없습니다." in html
    assert "intradayMarketTopFreshnessLabel(item)" in html
    assert "marketStatusLabel(item?.market_status)" in html
    assert "거래시각" in html
    assert "item?.checked_at" in html
    assert "확인" in html
    assert "node.hidden = true;" in html
    assert "node.hidden = false;" in html
    assert "overlapNode.hidden = false;" in html
    assert "intradayMarketTopLastLoadedAt = Date.now();" in html
    assert "setViewTab(\"main\");" in html
    assert "setViewTab(\"watch\");" not in html
    assert "scrollIntoView({ block: \"nearest\" })" in html


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
