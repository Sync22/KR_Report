from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CoreKeywordDocument:
    document_type: str
    stock_name: str
    stock_code: str | None
    title: str
    summary: str


@dataclass(frozen=True)
class CoreKeyword:
    value: str
    kind: str
    priority: int


@dataclass(frozen=True)
class RejectedCoreKeyword:
    value: str
    reason: str


@dataclass(frozen=True)
class CoreKeywordExtraction:
    accepted: tuple[CoreKeyword, ...]
    rejected: tuple[RejectedCoreKeyword, ...]


@dataclass(frozen=True)
class _PhraseRule:
    aliases: tuple[str, ...]
    canonical: str
    kind: str
    rank: int
    document_types: tuple[str, ...] = ("news", "report")


@dataclass(frozen=True)
class _GenericRule:
    value: str
    required_phrases: tuple[str, ...]
    document_types: tuple[str, ...] = ("news", "report")


_PHRASE_RULES = (
    _PhraseRule(("HBM4", "HBM 4"), "HBM4", "product", 10),
    _PhraseRule(("K9 자주포",), "K9 자주포", "product", 10),
    _PhraseRule(("로카모빌리티",), "로카모빌리티", "counterparty", 10),
    _PhraseRule(("미국 반도체 수출 규제",), "미국 반도체 수출 규제", "policy", 10),
    _PhraseRule(("염수 리튬",), "염수 리튬", "product", 10),
    _PhraseRule(("북미 ESS",), "북미 ESS", "industry", 10),
    _PhraseRule(("AI 반도체",), "AI 반도체", "technology", 10),
    _PhraseRule(("LNG선",), "LNG선", "product", 10),
    _PhraseRule(("엔비디아",), "엔비디아", "counterparty", 20),
    _PhraseRule(("폴란드 군비청",), "폴란드 군비청", "counterparty", 20),
    _PhraseRule(("로카모빌리티 인수",), "로카모빌리티 인수", "event", 20),
    _PhraseRule(("중국 공장 장비 반입",), "중국 공장 장비 반입", "event", 20),
    _PhraseRule(("아르헨티나 염수 리튬 상업 생산",), "아르헨티나 염수 리튬 상업 생산", "event", 20),
    _PhraseRule(("하이퍼클로바X",), "하이퍼클로바X", "product", 20),
    _PhraseRule(("메모리 업황 개선",), "메모리 업황 개선", "market_theme", 20),
    _PhraseRule(("ESS 수요",), "ESS 수요", "market_theme", 20),
    _PhraseRule(("고객 인증",), "고객 인증", "event", 20),
    _PhraseRule(("메탄올 추진선",), "메탄올 추진선", "technology", 20),
    _PhraseRule(("HBM4 공급 확대", "HBM 4 공급 확대"), "HBM4 공급 확대", "event", 30, ("news",)),
    _PhraseRule(("K9 자주포 추가 수주",), "K9 자주포 추가 수주", "event", 30),
    _PhraseRule(("모빌리티 데이터",), "모빌리티 데이터", "industry", 30),
    _PhraseRule(("첨단 반도체 장비",), "첨단 반도체 장비", "technology", 30),
    _PhraseRule(("리튬 가격",), "리튬 가격", "market_theme", 30),
    _PhraseRule(("기업용 서비스 출시",), "기업용 서비스 출시", "event", 30),
    _PhraseRule(("AI 메모리",), "AI 메모리", "technology", 30, ("report",)),
    _PhraseRule(("기업 검색",), "기업 검색", "product", 30),
    _PhraseRule(("카타르 LNG 프로젝트",), "카타르 LNG 프로젝트", "event", 30),
    _PhraseRule(("친환경 선박 사이클",), "친환경 선박 사이클", "market_theme", 40),
)

_GENERIC_RULES = (
    _GenericRule("공급", ("HBM4 공급 확대", "HBM 4 공급 확대"), ("news",)),
    _GenericRule("수주", ("추가 수주",)),
    _GenericRule("계약", ("공급 계약",)),
    _GenericRule("인수", ("로카모빌리티 인수",)),
    _GenericRule("규제", ("미국 반도체 수출 규제",)),
    _GenericRule("서비스", ("기업용 서비스 출시",)),
    _GenericRule("전망", ("하반기 사업 전망",), ("news",)),
    _GenericRule("점유율", ("HBM 점유율",)),
    _GenericRule("발주", ("발주가",)),
    _GenericRule("주가", ("주가와 시장",)),
    _GenericRule("시장", ("주가와 시장",)),
    _GenericRule("실적", ("실적과 시장",)),
)
_NUMERIC_PATTERNS = (r"\d+(?:\.\d+)?만원", r"\d+(?:\.\d+)?%")
_DATE_PATTERN = re.compile(r"\d{4}년\s*\d{1,2}월\s*\d{1,2}일")
_AI_PATTERN = re.compile(r"(?<![A-Za-z0-9])AI(?![A-Za-z0-9])", re.IGNORECASE)
_MAX_KEYWORDS = 5


def extract_core_keywords(
    document: CoreKeywordDocument,
    *,
    max_keywords: int = 5,
) -> CoreKeywordExtraction:
    if not 1 <= max_keywords <= _MAX_KEYWORDS:
        raise ValueError("max_keywords must be between 1 and 5")

    source = f"{document.title} {document.summary}".strip()
    normalized_source = _normalize_identity(source)
    discovered = [
        rule
        for rule in _PHRASE_RULES
        if document.document_type in rule.document_types
        and any(_normalize_identity(alias) in normalized_source for alias in rule.aliases)
    ]
    discovered.sort(key=lambda rule: (rule.rank, _source_position(source, rule.aliases), rule.canonical.casefold()))

    accepted = tuple(
        CoreKeyword(value=rule.canonical, kind=rule.kind, priority=index)
        for index, rule in enumerate(discovered[:max_keywords], start=1)
        if _normalize_identity(rule.canonical) in normalized_source
    )
    rejected = tuple(_discover_rejections(document, source, discovered))
    return CoreKeywordExtraction(accepted=accepted, rejected=rejected)


def _normalize_identity(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _source_position(source: str, aliases: tuple[str, ...]) -> int:
    normalized_source = _normalize_identity(source)
    positions = [normalized_source.find(_normalize_identity(alias)) for alias in aliases]
    return min(position for position in positions if position >= 0)


def _discover_rejections(
    document: CoreKeywordDocument,
    source: str,
    discovered: list[_PhraseRule],
) -> list[RejectedCoreKeyword]:
    rejected: list[RejectedCoreKeyword] = []
    normalized_source = _normalize_identity(source)

    rejected.append(RejectedCoreKeyword(document.stock_name, "target_identity"))
    if document.stock_code and _normalize_identity(document.stock_code) in normalized_source:
        rejected.append(RejectedCoreKeyword(document.stock_code, "target_identity"))

    for rule in _GENERIC_RULES:
        if document.document_type in rule.document_types and any(
            _normalize_identity(phrase) in normalized_source for phrase in rule.required_phrases
        ):
            rejected.append(RejectedCoreKeyword(rule.value, "too_generic"))

    for pattern in _NUMERIC_PATTERNS:
        for match in re.finditer(pattern, source):
            rejected.append(RejectedCoreKeyword(match.group(0), "numeric_noise"))

    if _AI_PATTERN.search(source) and (
        document.document_type == "news" or _normalize_identity("AI 투자") in normalized_source
    ):
        rejected.append(RejectedCoreKeyword("AI", "ambiguous_short_token"))

    date_match = _DATE_PATTERN.search(source)
    if date_match:
        rejected.append(RejectedCoreKeyword(date_match.group(0), "date_or_time"))

    for rule in discovered:
        for alias in rule.aliases:
            if alias != rule.canonical and alias.casefold() in source.casefold():
                rejected.append(RejectedCoreKeyword(alias, "duplicate"))

    return rejected
