from __future__ import annotations

from datetime import datetime, timezone

from stock_monitor.news import NewsArticle, build_news_intelligence_report


def _article(
    title: str,
    summary: str,
    *,
    url: str,
    source: str = "Test News",
) -> NewsArticle:
    return NewsArticle(
        title=title,
        summary=summary,
        source=source,
        published_at=datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc),
        url=url,
    )


def test_build_news_intelligence_report_returns_operator_only_json() -> None:
    articles = [
        _article(
            "Samsung wins large AI chip supply contract",
            "The company announced a major supply agreement expected to support earnings growth.",
            url="https://example.test/news/contract",
        ),
        _article(
            "Samsung wins large AI chip supply contract",
            "Duplicate copy of the same supply agreement.",
            url="https://example.test/news/contract",
        ),
        _article(
            "Samsung faces regulatory lawsuit over patent dispute",
            "The lawsuit may create legal costs and regulatory uncertainty.",
            url="https://example.test/news/lawsuit",
        ),
        _article(
            "Samsung launches new memory product",
            "The new product launch adds market attention but early sales impact is unclear.",
            url="https://example.test/news/product",
        ),
    ]

    report = build_news_intelligence_report(
        stock="Samsung Electronics",
        stock_code="005930",
        articles=articles,
    ).to_dict()

    assert report["stock"] == "Samsung Electronics"
    assert report["stock_code"] == "005930"
    assert report["operator_only"] is True
    assert report["public_safe"] is False
    assert report["live_provider"] is None
    assert report["connected_surfaces"] == []
    assert report["sentiment_distribution"]["positive"] == 2
    assert report["sentiment_distribution"]["negative"] == 1
    assert report["sentiment_distribution"]["caution"] == 0
    assert report["sentiment_distribution"]["mixed"] == 0
    assert -100 <= report["overall_sentiment"] <= 100
    assert len(report["top_news"]) == 3
    assert len(report["top_news"]) <= 5
    assert report["top_news"][0]["sentiment"] in {"Positive", "Negative"}
    assert "운영자 전용" in report["operator_summary"]

    event_types = {event["event_type"] for event in report["important_events"]}
    assert {"Contract", "Product Launch", "Regulation", "Lawsuit"} <= event_types
    assert any(
        event["stock_impact"] in {"Positive", "Strong Positive"}
        for event in report["important_events"]
    )
    assert any(
        event["stock_impact"] in {"Negative", "Strong Negative"}
        for event in report["important_events"]
    )


def test_news_intelligence_deduplicates_similar_titles() -> None:
    articles = [
        _article(
            "Hyundai announces new EV investment plan",
            "Management announced an investment plan for electric vehicles.",
            url="https://example.test/news/a",
        ),
        _article(
            "Hyundai announces new EV investment plan",
            "A second source repeats the same investment plan.",
            url="https://example.test/news/b",
            source="Other News",
        ),
        _article(
            "Hyundai appoints new chief financial officer",
            "The management change is expected to improve governance communication.",
            url="https://example.test/news/c",
        ),
    ]

    report = build_news_intelligence_report(
        stock="Hyundai Motor",
        stock_code="005380",
        articles=articles,
    ).to_dict()

    assert len(report["top_news"]) == 2
    assert report["article_count"] == 2
    assert {event["event_type"] for event in report["important_events"]} == {
        "Investment",
        "Management",
    }


def test_news_intelligence_detects_korean_events_and_sentiment() -> None:
    articles = [
        _article(
            "삼성전자, AI 반도체 공급 계약 체결",
            "삼성전자가 글로벌 고객사와 대규모 수주 계약을 체결했고 실적 개선 기대가 커졌다.",
            url="https://example.test/news/korean-contract",
            source="한국경제",
        ),
        _article(
            "컬리, AI 기업 원지랩스 인수한다",
            "컬리가 인공지능 기술 기업을 인수하고 신규 투자를 확대한다.",
            url="https://example.test/news/korean-ma",
            source="서울경제",
        ),
        _article(
            "범한메카텍, 1600억 규모 프리 IPO 마무리",
            "범한메카텍이 증자와 투자 유치를 마무리하며 상장 준비에 속도를 낸다.",
            url="https://example.test/news/korean-investment",
            source="매일경제",
        ),
        _article(
            "카카오, 규제 조사와 소송 리스크 확대",
            "금융당국 조사가 이어지고 소송 분쟁 우려가 커지며 실적 하락 가능성이 제기됐다.",
            url="https://example.test/news/korean-negative",
            source="테스트경제",
        ),
    ]

    report = build_news_intelligence_report(
        stock="Korean sample",
        stock_code=None,
        articles=articles,
    ).to_dict()

    event_types = {event["event_type"] for event in report["important_events"]}
    assert {"Contract", "Earnings", "M&A", "Investment", "Regulation", "Lawsuit"} <= event_types
    assert report["sentiment_distribution"]["positive"] >= 3
    assert report["sentiment_distribution"]["negative"] == 1
    assert any(
        article["stock_impact"] in {"Positive", "Strong Positive"}
        for article in report["top_news"]
    )
    assert any(article["stock_impact"] == "Strong Negative" for article in report["top_news"])


def test_news_intelligence_classifies_korean_operator_judgment_context() -> None:
    articles = [
        _article(
            "삼성전자 급등, 목표주가 61만원으로 상향",
            "증권가는 HBM 공급 확대와 실적 개선을 근거로 목표주가를 상향했다.",
            url="https://example.test/news/target-up",
        ),
        _article(
            "삼성전자·우선주 두자릿수 급등, 변동성 주의",
            "단기 과열과 차익실현 가능성이 커져 변동성 주의가 필요하다는 분석이다.",
            url="https://example.test/news/caution",
        ),
        _article(
            "반도체 ETF 과열 주의",
            "삼성전자와 SK하이닉스 중심 수급 쏠림과 단기 과열 주의가 제기됐다.",
            url="https://example.test/news/etf-flow",
        ),
        _article(
            "삼성전자, 대규모 공급 계약 체결",
            "AI 반도체 수주 증가와 장기공급계약 확대가 실적 기대를 높였다.",
            url="https://example.test/news/contract",
        ),
        _article(
            "삼성전자 규제 조사 우려",
            "당국 조사와 소송 리스크가 확대되며 불확실성이 커졌다.",
            url="https://example.test/news/regulation",
        ),
    ]

    report = build_news_intelligence_report(
        stock="삼성전자",
        stock_code="005930",
        articles=articles,
    ).to_dict()

    event_types = {event["event_type"] for event in report["important_events"]}
    assert {
        "Analyst Target",
        "Price Move",
        "Risk/Caution",
        "Supply/Demand",
        "Industry Cycle",
        "Contract",
        "Regulation",
        "Lawsuit",
    } <= event_types
    sentiments = {article["sentiment"] for article in report["top_news"]}
    assert {"Positive", "Caution", "Mixed"} <= sentiments
    impacts = {article["stock_impact"] for article in report["top_news"]}
    assert "Caution" in impacts
    assert "Strong Positive" in impacts
    assert "오늘 뉴스에서 볼 점" in report["operator_summary"]
    assert "추가 확인" in report["operator_summary"]
