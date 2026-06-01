from __future__ import annotations

from datetime import datetime, timezone

from stock_monitor.news import NewsArticle, build_news_intelligence_report


def _article(title: str, summary: str, *, url: str) -> NewsArticle:
    return NewsArticle(
        title=title,
        summary=summary,
        source="Test News",
        published_at=datetime(2026, 6, 2, 9, 30, tzinfo=timezone.utc),
        url=url,
    )


def test_market_context_news_is_downweighted_in_report_judgment() -> None:
    articles = [
        _article(
            "삼성전자 직접 공급 계약 체결",
            "삼성전자가 글로벌 고객사와 AI 반도체 장기 공급 계약을 체결했다.",
            url="https://example.test/news/direct-contract",
        ),
        _article(
            "삼전닉스 레버리지 ETF 28조 거래",
            "코스피 레버리지 ETF와 반도체 ETF에 삼성전자와 SK하이닉스가 편입되며 수급 쏠림과 변동성 우려가 커졌다.",
            url="https://example.test/news/etf-flow",
        ),
        _article(
            "반도체 ETF 과열 주의",
            "삼성전자 편입 ETF의 단타 거래와 레버리지 과열 우려가 이어졌다.",
            url="https://example.test/news/etf-caution",
        ),
    ]

    report = build_news_intelligence_report(
        stock="삼성전자",
        stock_code="005930",
        articles=articles,
    ).to_dict()

    assert report["overall_sentiment"] < 80
    assert report["top_news"][0]["title"] == "삼성전자 직접 공급 계약 체결"


def test_low_coverage_report_summary_marks_additional_confirmation_needed() -> None:
    report = build_news_intelligence_report(
        stock="NAVER",
        stock_code="035420",
        articles=[
            _article(
                "네이버 52주 신고가",
                "네이버가 AI 협업 기대와 글로벌 사업 성장 기대감으로 신고가를 기록했다.",
                url="https://example.test/news/naver-high",
            ),
            _article(
                "네이버 글로벌 시장 성장",
                "네이버의 글로벌 사업 확장과 투자 확대가 주목된다.",
                url="https://example.test/news/naver-global",
            ),
        ],
    ).to_dict()

    assert report["overall_sentiment"] < 100
    assert "coverage 낮음" in report["operator_summary"]
    assert "추가 확인" in report["operator_summary"]


def test_management_event_requires_actual_leadership_change_context() -> None:
    report = build_news_intelligence_report(
        stock="NAVER",
        stock_code="035420",
        articles=[
            _article(
                "네이버, 젠슨 황 방문 기대감에 신고가",
                "엔비디아 CEO 젠슨 황 방문과 AI 협업 기대가 부각됐다.",
                url="https://example.test/news/jensen-visit",
            ),
            _article(
                "네이버 새 대표 선임",
                "네이버가 새 대표를 선임하고 경영진 교체를 마무리했다.",
                url="https://example.test/news/ceo-change",
            ),
        ],
    ).to_dict()

    management_titles = {
        event["source_title"]
        for event in report["important_events"]
        if event["event_type"] == "Management"
    }
    assert "네이버, 젠슨 황 방문 기대감에 신고가" not in management_titles
    assert "네이버 새 대표 선임" in management_titles
