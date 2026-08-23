from __future__ import annotations

from datetime import date, datetime, timezone

from stock_monitor.news.linked_evidence import (
    ReportLinkedNewsContext,
    ReportLinkedNewsInput,
    build_report_linked_news_evidence,
)
from stock_monitor.news.models import NewsArticle
from stock_monitor.news.report import analyze_news_article


def _analyzed(title: str, summary: str, *, url: str, verified: bool = True) -> ReportLinkedNewsInput:
    article = NewsArticle(
        title=title,
        summary=summary,
        source="Test News",
        published_at=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        url=url,
        source_lane="mainnews",
    )
    return ReportLinkedNewsInput(
        analyzed_article=analyze_news_article(article),
        relevance="direct",
        match_scope="title",
        duplicate_count=1,
        lineage_type="independent" if verified else None,
        lineage_reason="fixture_provenance_verified" if verified else None,
    )


def _context(**overrides) -> ReportLinkedNewsContext:
    values = {
        "target_date": date(2026, 6, 1),
        "stock_name": "삼성전자",
        "stock_code": "005930",
        "related_report_count": 0,
        "related_report_source_ids": (),
        "daily_summary_presence": False,
        "candidate_priority_presence": False,
        "candidate_observation_priority": None,
        "krx_reference_presence": False,
        "krx_reference_date": None,
        "krx_turnover": None,
        "investor_flow_presence": False,
    }
    values.update(overrides)
    return ReportLinkedNewsContext(**values)


def test_report_linked_evidence_classifies_report_direct_positive_news() -> None:
    item = _analyzed(
        "삼성전자, 대규모 공급 계약 체결",
        "AI 반도체 수주 증가와 장기공급계약 확대가 실적 기대를 높였다.",
        url="https://example.test/direct-positive",
    )

    rows = build_report_linked_news_evidence(
        [item],
        _context(related_report_count=2, related_report_source_ids=("r1", "r2"), daily_summary_presence=True),
    )

    assert rows[0].evidence_case == "report_direct_positive_news"
    assert rows[0].operator_recommendation == "strengthen_report_candidate"
    assert rows[0].related_report_count == 2
    assert rows[0].related_report_source_ids == ("r1", "r2")


def test_report_linked_evidence_classifies_report_with_caution_news() -> None:
    item = _analyzed(
        "삼성전자 급등, 변동성 주의",
        "단기 과열과 차익실현 가능성이 커져 변동성 주의가 필요하다는 분석이다.",
        url="https://example.test/report-caution",
    )

    rows = build_report_linked_news_evidence(
        [item],
        _context(related_report_count=1, daily_summary_presence=True),
    )

    assert rows[0].evidence_case == "report_with_caution_news"
    assert rows[0].operator_recommendation == "review_with_caution"
    assert "주의" in rows[0].recommendation_reason


def test_report_linked_evidence_classifies_no_report_strong_direct_news() -> None:
    item = _analyzed(
        "삼성전자, 대규모 공급 계약 체결",
        "AI 반도체 수주 증가와 장기공급계약 확대가 실적 기대를 높였다.",
        url="https://example.test/no-report-strong",
    )

    rows = build_report_linked_news_evidence([item], _context())

    assert rows[0].evidence_case == "no_report_strong_direct_news"
    assert rows[0].operator_recommendation == "promote_news_only_candidate"


def test_report_linked_evidence_classifies_report_heavy_market_context_only() -> None:
    item = _analyzed(
        "반도체 ETF에 자금 쏠림",
        "삼성전자와 SK하이닉스 중심 수급 쏠림으로 코스피 지수가 상승했다.",
        url="https://example.test/market-context",
    )
    item = ReportLinkedNewsInput(
        analyzed_article=item.analyzed_article,
        relevance="market_context",
        match_scope="summary",
        duplicate_count=1,
        lineage_type=item.lineage_type,
        lineage_reason=item.lineage_reason,
    )

    rows = build_report_linked_news_evidence([item], _context(related_report_count=4))

    assert rows[0].evidence_case == "report_heavy_market_context_only"
    assert rows[0].operator_recommendation == "separate_market_context"


def test_report_linked_evidence_classifies_price_move_with_krx_turnover() -> None:
    item = _analyzed(
        "삼성전자 두자릿수 급등",
        "삼성전자가 장중 급등하며 거래대금도 크게 늘었다.",
        url="https://example.test/price-krx",
    )

    rows = build_report_linked_news_evidence(
        [item],
        _context(krx_reference_presence=True, krx_turnover=1_200_000_000),
    )

    assert rows[0].evidence_case == "price_move_with_krx_turnover"
    assert rows[0].operator_recommendation == "confirm_price_move_candidate"
    assert rows[0].krx_turnover == 1_200_000_000


def test_report_linked_evidence_classifies_price_move_without_krx_reference() -> None:
    item = _analyzed(
        "삼성전자 두자릿수 급등",
        "삼성전자가 장중 급등했다는 보도가 나왔다.",
        url="https://example.test/price-missing-krx",
    )

    rows = build_report_linked_news_evidence([item], _context())

    assert rows[0].evidence_case == "price_move_without_krx_reference"
    assert rows[0].operator_recommendation == "hold_until_market_reference"


def test_report_linked_evidence_classifies_news_only_caution() -> None:
    item = _analyzed(
        "삼성전자 변동성 주의",
        "단기 과열과 차익실현 가능성이 커졌다는 분석이다.",
        url="https://example.test/news-only-caution",
    )

    rows = build_report_linked_news_evidence([item], _context())

    assert rows[0].evidence_case == "news_only_caution"
    assert rows[0].operator_recommendation == "watch_risk_only"


def test_report_linked_evidence_classifies_weak_news_duplicate_context() -> None:
    item = _analyzed(
        "코스피 사상 최고치",
        "삼성전자가 지수 상승을 이끌었다는 유사 기사들이 반복됐다.",
        url="https://example.test/duplicate-context",
    )
    item = ReportLinkedNewsInput(
        analyzed_article=item.analyzed_article,
        relevance="market_context",
        match_scope="summary",
        duplicate_count=4,
        lineage_type=item.lineage_type,
        lineage_reason=item.lineage_reason,
    )

    rows = build_report_linked_news_evidence([item], _context())

    assert rows[0].evidence_case == "weak_news_duplicate_context"
    assert rows[0].operator_recommendation == "downrank_duplicate_context"


def test_automatic_news_lineage_never_promotes_unverified_article_to_independent() -> None:
    original_news = _analyzed(
        "삼성전자, 대규모 공급 계약 체결",
        "회사가 신규 고객과 장기 공급 계약을 체결했다고 밝혔다.",
        url="https://example.test/original-looking-news?utm_source=test#fragment",
        verified=False,
    )
    report_recap = _analyzed(
        "증권사 리포트로 본 삼성전자 목표가",
        "애널리스트가 투자의견과 목표가를 상향했다는 리포트 요약이다.",
        url="https://example.test/report-recap",
        verified=False,
    )

    original_row, recap_row = build_report_linked_news_evidence(
        [original_news, report_recap],
        _context(related_report_count=2, related_report_source_ids=("r1", "r2")),
    )

    assert original_row.lineage_type == "unknown"
    assert original_row.lineage_reason == "automatic_collection_origin_unverified"
    assert original_row.canonical_url == "https://example.test/original-looking-news"
    assert original_row.operator_recommendation == "hold_until_independence_verified"
    assert recap_row.lineage_type == "report_recap"
    assert recap_row.lineage_reason == "report_recap_language_detected"
    assert recap_row.operator_recommendation == "keep_as_report_recap"
