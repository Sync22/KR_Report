from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsArticle:
    title: str
    summary: str
    source: str
    published_at: datetime
    url: str
    source_lane: str | None = None

    def text(self) -> str:
        return f"{self.title} {self.summary}".strip()

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "url": self.url,
            "source_lane": self.source_lane,
        }


@dataclass(frozen=True)
class AnalyzedNewsArticle:
    article: NewsArticle
    concise_summary: str
    sentiment: str
    sentiment_score: int
    keywords: list[str]
    event_types: list[str]
    stock_impact: str
    impact_explanation: str
    importance: int

    def to_dict(self) -> dict[str, object]:
        payload = self.article.to_dict()
        payload.update(
            {
                "concise_summary": self.concise_summary,
                "sentiment": self.sentiment,
                "sentiment_score": self.sentiment_score,
                "keywords": self.keywords,
                "event_types": self.event_types,
                "stock_impact": self.stock_impact,
                "impact_explanation": self.impact_explanation,
                "importance": self.importance,
            }
        )
        return payload


@dataclass(frozen=True)
class ImportantNewsEvent:
    event_type: str
    stock_impact: str
    description: str
    source_title: str

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "stock_impact": self.stock_impact,
            "description": self.description,
            "source_title": self.source_title,
        }


@dataclass(frozen=True)
class NewsIntelligenceReport:
    stock: str
    stock_code: str | None
    article_count: int
    operator_only: bool
    public_safe: bool
    live_provider: str | None
    connected_surfaces: list[str]
    overall_sentiment: int
    sentiment_distribution: dict[str, int]
    important_events: list[ImportantNewsEvent]
    top_news: list[AnalyzedNewsArticle]
    operator_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "stock": self.stock,
            "stock_code": self.stock_code,
            "article_count": self.article_count,
            "operator_only": self.operator_only,
            "public_safe": self.public_safe,
            "live_provider": self.live_provider,
            "connected_surfaces": self.connected_surfaces,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_distribution": self.sentiment_distribution,
            "important_events": [event.to_dict() for event in self.important_events],
            "top_news": [article.to_dict() for article in self.top_news],
            "operator_summary": self.operator_summary,
        }
