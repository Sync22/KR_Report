from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import AnalyzedNewsArticle


@dataclass(frozen=True)
class ReportLinkedNewsContext:
    target_date: date
    stock_name: str
    stock_code: str | None
    related_report_count: int
    related_report_source_ids: tuple[str, ...]
    daily_summary_presence: bool
    candidate_priority_presence: bool
    candidate_observation_priority: str | None
    krx_reference_presence: bool
    krx_reference_date: date | None
    krx_turnover: int | None
    investor_flow_presence: bool


@dataclass(frozen=True)
class ReportLinkedNewsInput:
    analyzed_article: AnalyzedNewsArticle
    relevance: str
    match_scope: str
    duplicate_count: int = 1


@dataclass(frozen=True)
class ReportLinkedNewsEvidence:
    target_date: date
    stock_name: str
    stock_code: str | None
    article: AnalyzedNewsArticle
    relevance: str
    match_scope: str
    duplicate_count: int
    related_report_count: int
    related_report_source_ids: tuple[str, ...]
    daily_summary_presence: bool
    candidate_priority_presence: bool
    candidate_observation_priority: str | None
    krx_reference_presence: bool
    krx_reference_date: date | None
    krx_turnover: int | None
    investor_flow_presence: bool
    evidence_case: str
    operator_recommendation: str
    recommendation_reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "target_date": self.target_date.isoformat(),
            "stock_name": self.stock_name,
            "stock_code": self.stock_code,
            "article": self.article.to_dict(),
            "relevance": self.relevance,
            "match_scope": self.match_scope,
            "duplicate_count": self.duplicate_count,
            "related_report_count": self.related_report_count,
            "related_report_source_ids": list(self.related_report_source_ids),
            "daily_summary_presence": self.daily_summary_presence,
            "candidate_priority_presence": self.candidate_priority_presence,
            "candidate_observation_priority": self.candidate_observation_priority,
            "krx_reference_presence": self.krx_reference_presence,
            "krx_reference_date": self.krx_reference_date.isoformat() if self.krx_reference_date else None,
            "krx_turnover": self.krx_turnover,
            "investor_flow_presence": self.investor_flow_presence,
            "evidence_case": self.evidence_case,
            "operator_recommendation": self.operator_recommendation,
            "recommendation_reason": self.recommendation_reason,
        }


def build_report_linked_news_evidence(
    articles: list[ReportLinkedNewsInput],
    context: ReportLinkedNewsContext,
) -> list[ReportLinkedNewsEvidence]:
    return [_build_evidence_row(article, context) for article in articles]


def _build_evidence_row(
    article: ReportLinkedNewsInput,
    context: ReportLinkedNewsContext,
) -> ReportLinkedNewsEvidence:
    evidence_case, operator_recommendation, recommendation_reason = _classify_evidence_case(article, context)
    return ReportLinkedNewsEvidence(
        target_date=context.target_date,
        stock_name=context.stock_name,
        stock_code=context.stock_code,
        article=article.analyzed_article,
        relevance=article.relevance,
        match_scope=article.match_scope,
        duplicate_count=article.duplicate_count,
        related_report_count=context.related_report_count,
        related_report_source_ids=context.related_report_source_ids,
        daily_summary_presence=context.daily_summary_presence,
        candidate_priority_presence=context.candidate_priority_presence,
        candidate_observation_priority=context.candidate_observation_priority,
        krx_reference_presence=context.krx_reference_presence,
        krx_reference_date=context.krx_reference_date,
        krx_turnover=context.krx_turnover,
        investor_flow_presence=context.investor_flow_presence,
        evidence_case=evidence_case,
        operator_recommendation=operator_recommendation,
        recommendation_reason=recommendation_reason,
    )


def _classify_evidence_case(
    article: ReportLinkedNewsInput,
    context: ReportLinkedNewsContext,
) -> tuple[str, str, str]:
    analyzed = article.analyzed_article
    events = set(analyzed.event_types)
    has_report = context.related_report_count > 0
    is_direct = article.relevance == "direct"
    is_market_context = article.relevance == "market_context"
    is_positive = analyzed.stock_impact in {"Positive", "Strong Positive"} or analyzed.sentiment == "Positive"
    is_strong = analyzed.stock_impact in {"Strong Positive", "Strong Negative"} or abs(analyzed.sentiment_score) >= 70
    is_caution = (
        analyzed.stock_impact == "Caution"
        or analyzed.sentiment in {"Caution", "Mixed"}
        or "Risk/Caution" in events
    )
    has_price_move = "Price Move" in events

    if article.duplicate_count >= 3 and is_market_context:
        return (
            "weak_news_duplicate_context",
            "downrank_duplicate_context",
            "유사한 시장 맥락 기사가 반복되어 종목 고유 근거보다 중복 노이즈 가능성을 먼저 봅니다.",
        )
    if has_report and context.related_report_count >= 3 and is_market_context:
        return (
            "report_heavy_market_context_only",
            "separate_market_context",
            "리포트는 많지만 뉴스는 시장/업종 맥락 중심이라 종목 고유 근거와 분리해 봅니다.",
        )
    if has_price_move and context.krx_reference_presence and context.krx_turnover is not None:
        return (
            "price_move_with_krx_turnover",
            "confirm_price_move_candidate",
            "가격 움직임 뉴스와 KRX 거래대금 참고값이 함께 있어 우선 확인 근거를 강화합니다.",
        )
    if has_report and is_caution:
        return (
            "report_with_caution_news",
            "review_with_caution",
            "리포트 근거가 있는 종목에 주의/혼합 뉴스가 붙어 리스크 확인을 추천합니다.",
        )
    if has_price_move and not context.krx_reference_presence:
        return (
            "price_move_without_krx_reference",
            "hold_until_market_reference",
            "가격 움직임 뉴스는 있으나 KRX 기준 데이터가 없어 거래 반응 확인 전까지 보류합니다.",
        )
    if has_report and is_direct and is_positive:
        return (
            "report_direct_positive_news",
            "strengthen_report_candidate",
            "리포트 근거와 종목 직접 긍정 뉴스가 겹쳐 관찰 우선순위를 강화할 수 있습니다.",
        )
    if not has_report and is_direct and is_strong:
        return (
            "no_report_strong_direct_news",
            "promote_news_only_candidate",
            "리포트는 없지만 종목 직접 강한 뉴스가 있어 뉴스 단독 후보로 올려볼 수 있습니다.",
        )
    if not has_report and is_caution:
        return (
            "news_only_caution",
            "watch_risk_only",
            "리포트 없이 주의 뉴스만 있어 추천 강화보다 리스크 관찰 대상으로 둡니다.",
        )
    return (
        "linked_news_context",
        "keep_as_supporting_evidence",
        "리포트/시장 데이터와 연결된 보조 뉴스 근거로 유지합니다.",
    )
