from __future__ import annotations

from typing import Protocol

from .events import classify_news_events
from .impact import estimate_stock_impact, impact_importance
from .models import AnalyzedNewsArticle, ImportantNewsEvent, NewsArticle, NewsIntelligenceReport
from .preprocess import deduplicate_articles
from .sentiment import analyze_sentiment


class NewsArticleAnalyzer(Protocol):
    def analyze(self, article: NewsArticle) -> AnalyzedNewsArticle:
        ...


def _concise_summary(article: NewsArticle) -> str:
    summary = article.summary.strip() or article.title.strip()
    if len(summary) <= 180:
        return summary
    return summary[:177].rstrip() + "..."


def analyze_news_article(article: NewsArticle) -> AnalyzedNewsArticle:
    text = article.text()
    sentiment = analyze_sentiment(text)
    event_types = classify_news_events(text)
    stock_impact, impact_explanation = estimate_stock_impact(
        sentiment.score,
        event_types,
        sentiment_label=sentiment.label,
    )
    return AnalyzedNewsArticle(
        article=article,
        concise_summary=_concise_summary(article),
        sentiment=sentiment.label,
        sentiment_score=sentiment.score,
        keywords=sentiment.keywords,
        event_types=event_types,
        stock_impact=stock_impact,
        impact_explanation=impact_explanation,
        importance=impact_importance(sentiment.score, event_types),
    )


def build_news_intelligence_report(
    *,
    stock: str,
    articles: list[NewsArticle],
    stock_code: str | None = None,
    analyzer: NewsArticleAnalyzer | None = None,
) -> NewsIntelligenceReport:
    deduped_articles = deduplicate_articles(articles)
    analyzed = [
        analyzer.analyze(article) if analyzer is not None else analyze_news_article(article)
        for article in deduped_articles
    ]
    analyzed.sort(key=lambda article: (article.importance, article.article.published_at), reverse=True)

    distribution = {"positive": 0, "neutral": 0, "negative": 0, "caution": 0, "mixed": 0}
    for article in analyzed:
        distribution[article.sentiment.lower()] += 1
    overall_sentiment = _overall_sentiment(analyzed)
    important_events = _important_events(analyzed)
    return NewsIntelligenceReport(
        stock=stock,
        stock_code=stock_code,
        article_count=len(analyzed),
        operator_only=True,
        public_safe=False,
        live_provider=None,
        connected_surfaces=[],
        overall_sentiment=overall_sentiment,
        sentiment_distribution=distribution,
        important_events=important_events,
        top_news=analyzed[:5],
        operator_summary=_operator_summary(stock, overall_sentiment, distribution, important_events),
    )


def _overall_sentiment(articles: list[AnalyzedNewsArticle]) -> int:
    if not articles:
        return 0
    return round(sum(article.sentiment_score for article in articles) / len(articles))


def _important_events(articles: list[AnalyzedNewsArticle]) -> list[ImportantNewsEvent]:
    events: list[ImportantNewsEvent] = []
    seen: set[tuple[str, str]] = set()
    for article in articles:
        for event_type in article.event_types:
            key = (event_type, article.article.url)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                ImportantNewsEvent(
                    event_type=event_type,
                    stock_impact=article.stock_impact,
                    description=article.impact_explanation,
                    source_title=article.article.title,
                )
            )
    return events


def _operator_summary(
    stock: str,
    overall_sentiment: int,
    distribution: dict[str, int],
    important_events: list[ImportantNewsEvent],
) -> str:
    if not sum(distribution.values()):
        return f"{stock} 운영자 전용 뉴스 입력이 없습니다."
    event_types = ", ".join(event.event_type for event in important_events[:4]) or "주요 이벤트 없음"
    caution_count = distribution.get("caution", 0) + distribution.get("mixed", 0)
    return (
        f"{stock} 운영자 전용 뉴스 판단입니다. 오늘 뉴스에서 볼 점: "
        f"전체 톤 {overall_sentiment}, 긍정 {distribution['positive']}건, "
        f"중립 {distribution['neutral']}건, 부정 {distribution['negative']}건, "
        f"주의/혼합 {caution_count}건입니다. 주요 이벤트: {event_types}. "
        "추가 확인: 실제 거래대금, 수급 쏠림, 중복 기사, 간접 시장 맥락 여부를 확인해야 합니다."
    )
