from __future__ import annotations

from .preprocess import tokenize_news_text


EVENT_RULES: tuple[tuple[str, set[str]], ...] = (
    ("Earnings", {"earnings", "profit", "revenue", "guidance", "실적", "흑자", "적자", "매출", "영업이익"}),
    ("Contract", {"contract", "agreement", "supply", "partnership", "계약", "공급", "수주", "체결", "장기공급계약"}),
    ("Investment", {"investment", "invest", "capex", "funding", "투자", "증자", "유치", "상장", "증설"}),
    ("Regulation", {"regulatory", "probe", "investigation", "fine", "규제", "조사", "당국", "제재"}),
    ("Lawsuit", {"lawsuit", "patent", "dispute", "litigation", "소송", "분쟁", "특허", "리스크"}),
    ("Management", {"appoints", "appointment", "ceo", "cfo", "management", "chief", "대표", "임원", "경영진", "회장"}),
    ("M&A", {"acquisition", "merger", "takeover", "m&a", "인수", "합병", "매각", "합작"}),
    ("Product Launch", {"launch", "launches", "product", "release", "제품", "출시", "신제품"}),
    ("Analyst Target", {"목표주가", "목표가", "상향", "하향", "투자의견", "증권가", "전망"}),
    ("Price Move", {"급등", "급락", "상승", "하락", "신고가", "최고가", "두자릿수"}),
    ("Supply/Demand", {"수급", "매수", "매도", "쏠림", "외국인", "기관", "자금"}),
    ("Industry Cycle", {"업황", "사이클", "반도체", "hbm", "메모리", "ai", "코스피", "etf"}),
    ("Risk/Caution", {"주의", "과열", "변동성", "우려", "불확실성", "소외", "단타", "차익실현", "투전판"}),
)


def classify_news_events(text: str) -> list[str]:
    tokens = tokenize_news_text(text)
    lowered = text.casefold()
    event_types: list[str] = []
    for event_type, terms in EVENT_RULES:
        if tokens & terms or any(_term_matches_text(term, lowered) for term in terms):
            event_types.append(event_type)
    return event_types


def _term_matches_text(term: str, lowered_text: str) -> bool:
    if term.isascii() and len(term) <= 3:
        return False
    return term in lowered_text
