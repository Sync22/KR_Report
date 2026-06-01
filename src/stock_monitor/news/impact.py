from __future__ import annotations


HIGH_POSITIVE_EVENTS = {
    "Contract",
    "Earnings",
    "Investment",
    "M&A",
}
HIGH_NEGATIVE_EVENTS = {
    "Lawsuit",
    "Regulation",
}
CAUTION_EVENTS = {
    "Risk/Caution",
    "Price Move",
    "Supply/Demand",
}


def estimate_stock_impact(
    sentiment_score: int,
    event_types: list[str],
    *,
    sentiment_label: str = "Neutral",
) -> tuple[str, str]:
    events = set(event_types)
    has_positive_event = bool(events & HIGH_POSITIVE_EVENTS)
    has_negative_event = bool(events & HIGH_NEGATIVE_EVENTS)
    has_caution_event = bool(events & CAUTION_EVENTS)

    if sentiment_score <= -40 and has_negative_event:
        label = "Strong Negative"
    elif sentiment_label == "Caution":
        label = "Caution"
    elif sentiment_score <= -20:
        label = "Negative"
    elif has_caution_event and sentiment_score < 60:
        label = "Caution"
    elif sentiment_score >= 70 and has_positive_event:
        label = "Strong Positive"
    elif sentiment_score >= 20:
        label = "Positive"
    elif sentiment_label == "Mixed" or has_caution_event:
        label = "Caution"
    else:
        label = "Neutral"

    return label, _impact_explanation(label, event_types)


def impact_importance(sentiment_score: int, event_types: list[str]) -> int:
    event_bonus = 15 if event_types else 0
    high_impact_bonus = 20 if set(event_types) & (HIGH_POSITIVE_EVENTS | HIGH_NEGATIVE_EVENTS) else 0
    caution_bonus = 15 if set(event_types) & CAUTION_EVENTS else 0
    return min(100, abs(sentiment_score) + event_bonus + high_impact_bonus + caution_bonus)


def _impact_explanation(label: str, event_types: list[str]) -> str:
    if not event_types:
        return f"주요 이벤트 분류는 없으며 현재 뉴스 톤은 {label} 참고 맥락입니다."
    event_text = ", ".join(event_types)
    if label == "Caution":
        return f"{event_text} 맥락이 있어 단기 과열, 변동성, 간접 기사 여부를 운영자가 확인해야 합니다."
    if label in {"Strong Positive", "Positive"}:
        return f"{event_text} 맥락이 있어 실적, 수급, 업황 확인 우선순위를 높일 수 있습니다."
    if label in {"Strong Negative", "Negative"}:
        return f"{event_text} 맥락이 있어 리스크와 후속 공시 확인이 필요합니다."
    return f"{event_text} 맥락은 있으나 방향성은 중립에 가깝습니다."
