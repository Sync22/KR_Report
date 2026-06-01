from __future__ import annotations

from dataclasses import dataclass

from .preprocess import tokenize_news_text


POSITIVE_TERMS = {
    "agreement",
    "beat",
    "contract",
    "earnings",
    "growth",
    "improve",
    "investment",
    "launch",
    "launches",
    "major",
    "partnership",
    "profit",
    "revenue",
    "strong",
    "supply",
    "wins",
    "개선",
    "계약",
    "공급",
    "급등",
    "대규모",
    "상승",
    "상향",
    "성장",
    "수주",
    "신고가",
    "신규",
    "인수",
    "증가",
    "증자",
    "체결",
    "투자",
    "흑자",
}

NEGATIVE_TERMS = {
    "cost",
    "costs",
    "delay",
    "decline",
    "dispute",
    "fine",
    "investigation",
    "lawsuit",
    "loss",
    "probe",
    "recall",
    "regulatory",
    "uncertainty",
    "weak",
    "규제",
    "급락",
    "분쟁",
    "불확실",
    "불확실성",
    "소송",
    "손실",
    "조사",
    "적자",
    "하락",
    "하향",
}

CAUTION_TERMS = {
    "risk",
    "volatile",
    "caution",
    "과열",
    "단기",
    "단타",
    "리스크",
    "변동성",
    "소외",
    "우려",
    "주의",
    "차익실현",
    "투전판",
}

STOPWORDS = {
    "about",
    "after",
    "and",
    "for",
    "from",
    "into",
    "may",
    "new",
    "over",
    "the",
    "this",
    "with",
    "기자",
    "뉴스",
    "이번",
    "있다",
    "했다",
}


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: int
    keywords: list[str]


def analyze_sentiment(text: str) -> SentimentResult:
    tokens = tokenize_news_text(text)
    lowered = text.casefold()
    positive_hits = _hits(tokens, lowered, POSITIVE_TERMS)
    negative_hits = _hits(tokens, lowered, NEGATIVE_TERMS)
    caution_hits = _hits(tokens, lowered, CAUTION_TERMS)
    score = _sentiment_score(
        positive_count=len(positive_hits),
        negative_count=len(negative_hits),
        caution_count=len(caution_hits),
    )
    label = _sentiment_label(
        positive_hits=positive_hits,
        negative_hits=negative_hits,
        caution_hits=caution_hits,
        score=score,
    )
    signal_hits = positive_hits | negative_hits | caution_hits
    ranked_keywords = sorted(
        tokens - STOPWORDS,
        key=lambda token: (token not in signal_hits, token),
    )
    return SentimentResult(label=label, score=score, keywords=ranked_keywords[:8])


def _hits(tokens: set[str], lowered_text: str, terms: set[str]) -> set[str]:
    return {term for term in terms if term in tokens or term in lowered_text}


def _sentiment_score(*, positive_count: int, negative_count: int, caution_count: int) -> int:
    hit_count = positive_count + negative_count + caution_count
    if hit_count == 0:
        return 0
    raw = ((positive_count - negative_count - (caution_count * 0.6)) / hit_count) * 100
    return max(-100, min(100, round(raw)))


def _sentiment_label(
    *,
    positive_hits: set[str],
    negative_hits: set[str],
    caution_hits: set[str],
    score: int,
) -> str:
    if positive_hits and (negative_hits or caution_hits):
        return "Mixed"
    if negative_hits:
        return "Negative"
    if caution_hits:
        return "Caution"
    if score >= 20:
        return "Positive"
    if score <= -20:
        return "Negative"
    return "Neutral"
