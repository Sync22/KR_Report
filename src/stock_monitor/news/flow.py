from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .preprocess import normalize_news_text, title_similarity


KST = ZoneInfo("Asia/Seoul")

COMPANY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Samsung Electronics", ("Samsung Electronics", "삼성전자")),
    ("SK Hynix", ("SK Hynix", "Hynix", "SK하이닉스", "에스케이하이닉스")),
    ("Hyundai Motor", ("Hyundai Motor", "현대차", "현대자동차")),
    ("LG Energy Solution", ("LG Energy Solution", "LG에너지솔루션", "LG엔솔")),
    ("NAVER", ("NAVER", "네이버")),
    ("Kakao", ("Kakao", "카카오")),
    ("POSCO Holdings", ("POSCO Holdings", "POSCO", "포스코홀딩스")),
    ("Celltrion", ("Celltrion", "셀트리온")),
    ("Doosan Enerbility", ("Doosan Enerbility", "두산에너빌리티")),
)

THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Semiconductor/AI", ("semiconductor", "chip", "hbm", "memory", "ai", "반도체", "메모리")),
    ("Battery/EV", ("battery", "secondary battery", "ev", "electric vehicle", "2차전지", "배터리", "전기차")),
    ("Auto/mobility", ("auto", "mobility", "vehicle", "car", "자동차", "모빌리티")),
    ("Platform/internet", ("platform", "internet", "search", "commerce", "플랫폼", "인터넷")),
    ("Bio/healthcare", ("bio", "healthcare", "drug", "pharma", "바이오", "제약")),
    ("Shipbuilding/defense", ("shipbuilding", "defense", "조선", "방산")),
    ("Finance/rates", ("bank", "securities", "rate", "yield", "은행", "증권", "금리", "채권")),
    ("Energy/materials", ("energy", "oil", "gas", "steel", "materials", "에너지", "철강", "소재")),
)

ISSUE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Supply/contract", ("supply", "contract", "agreement", "order", "customer", "공급", "계약", "수주")),
    ("Investment/capex", ("investment", "capex", "factory", "expansion", "funding", "투자", "증설")),
    ("Earnings/guidance", ("earnings", "profit", "revenue", "guidance", "실적", "매출", "이익")),
    ("Policy/regulation", ("policy", "regulation", "subsidy", "probe", "investigation", "규제", "정책", "보조금")),
    ("Macro/rates/fx", ("rate", "yield", "dollar", "fx", "inflation", "금리", "환율", "달러", "물가")),
    ("Trade/geopolitics", ("tariff", "export", "sanction", "geopolitics", "관세", "수출", "제재")),
    ("Listing/IPO", ("ipo", "listing", "상장")),
)

CAUTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Volatility/overheating", ("volatility", "overheating", "sharp move", "caution", "risk", "변동성", "과열", "주의")),
    ("Policy/regulation risk", ("policy uncertainty", "regulation", "probe", "subsidy", "규제", "정책 불확실")),
    ("Earnings slowdown", ("slowdown", "miss", "loss", "부진", "적자")),
    ("Supply disruption", ("disruption", "delay", "shortage", "차질", "지연", "부족")),
    ("Legal/dispute", ("lawsuit", "dispute", "litigation", "소송", "분쟁")),
    ("Macro pressure", ("rate", "yield", "fx", "inflation", "금리", "환율", "물가")),
)

LOW_SIGNAL_TITLE_MARKERS = (
    "바로잡습니다",
    "[인사]",
    "[경제계 인사]",
    "[부고]",
    "[알림]",
    "correction",
    "appointments",
    "personnel",
)

DRAFT_LABELS = {
    "Semiconductor/AI": "반도체/AI",
    "Battery/EV": "2차전지/EV",
    "Auto/mobility": "자동차/모빌리티",
    "Platform/internet": "플랫폼/인터넷",
    "Bio/healthcare": "바이오/헬스케어",
    "Shipbuilding/defense": "조선/방산",
    "Finance/rates": "금융/금리",
    "Energy/materials": "에너지/소재",
    "Supply/contract": "공급/계약",
    "Investment/capex": "투자/증설",
    "Earnings/guidance": "실적/가이던스",
    "Policy/regulation": "정책/규제",
    "Macro/rates/fx": "매크로/금리/환율",
    "Trade/geopolitics": "무역/지정학",
    "Listing/IPO": "상장/IPO",
    "Volatility/overheating": "변동성/과열",
    "Policy/regulation risk": "정책/규제 리스크",
    "Earnings slowdown": "실적 둔화",
    "Supply disruption": "공급 차질",
    "Legal/dispute": "법적 분쟁",
    "Macro pressure": "매크로 부담",
}

DRAFT_MOOD_LABELS = {
    "No parsed articles in the requested source URLs": "요청 source URL에서 파싱된 기사가 없습니다",
    "Active theme flow with visible caution signals": "주도 테마는 뚜렷하지만 경계 신호가 함께 보입니다",
    "Theme-led market flow": "테마 중심 흐름입니다",
    "Issue-led market flow": "이슈 중심 흐름입니다",
    "Sparse or uncategorized news flow": "기사 흐름이 아직 성기거나 분류가 제한적입니다",
}


@dataclass(frozen=True)
class NewsFlowArticle:
    title: str
    published_at: datetime
    url: str
    source: str
    summary: str
    source_page_url: str

    def text(self) -> str:
        return f"{self.title} {self.summary}".strip()

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "date": self.published_at.isoformat(),
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "source_page_url": self.source_page_url,
        }


@dataclass(frozen=True)
class NewsFlowSourcePreview:
    source_url: str
    source_name: str
    parsed_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "parsed_count": self.parsed_count,
        }


@dataclass(frozen=True)
class NewsFlowCollection:
    source_urls: tuple[str, ...]
    sources: list[NewsFlowSourcePreview]
    articles: list[NewsFlowArticle]
    parsed_count: int
    deduped_count: int
    warnings: list[str]


@dataclass(frozen=True)
class NewsFlowTopic:
    label: str
    article_count: int
    source_count: int
    article_titles: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "article_count": self.article_count,
            "source_count": self.source_count,
            "article_titles": list(self.article_titles),
        }


@dataclass(frozen=True)
class NewsFlowStockMention:
    name: str
    article_count: int
    source_count: int
    article_titles: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "article_count": self.article_count,
            "source_count": self.source_count,
            "article_titles": list(self.article_titles),
        }


@dataclass(frozen=True)
class NewsFlowPreview:
    source_urls: tuple[str, ...]
    sources: list[NewsFlowSourcePreview]
    articles: list[NewsFlowArticle]
    parsed_count: int
    deduped_count: int
    repeated_stocks: list[NewsFlowStockMention]
    sector_themes: list[NewsFlowTopic]
    key_issues: list[NewsFlowTopic]
    caution_signals: list[NewsFlowTopic]
    market_mood: str
    telegram_draft: str
    warnings: list[str]

    @property
    def article_count(self) -> int:
        return len(self.articles)

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": "news-flow-preview",
            "operator_only": True,
            "public_safe": False,
            "live_fetch": False,
            "writes_db": False,
            "sends_telegram": False,
            "registers_scheduler": False,
            "connects_web_view": False,
            "source_urls": list(self.source_urls),
            "source_count": len(self.source_urls),
            "sources": [source.to_dict() for source in self.sources],
            "parsed_count": self.parsed_count,
            "deduped_count": self.deduped_count,
            "article_count": self.article_count,
            "articles": [article.to_dict() for article in self.articles],
            "repeated_stocks": [stock.to_dict() for stock in self.repeated_stocks],
            "sector_themes": [theme.to_dict() for theme in self.sector_themes],
            "key_issues": [issue.to_dict() for issue in self.key_issues],
            "caution_signals": [signal.to_dict() for signal in self.caution_signals],
            "market_mood": self.market_mood,
            "telegram_draft": self.telegram_draft,
            "warnings": self.warnings,
        }


def parse_news_flow_json(content: str, *, source_urls: Sequence[str]) -> NewsFlowCollection:
    return parse_news_flow_payload(json.loads(content), source_urls=source_urls)


def parse_news_flow_payload(payload: object, *, source_urls: Sequence[str]) -> NewsFlowCollection:
    requested_urls = _normalize_source_urls(source_urls)
    source_rows = _payload_sources(payload)
    warnings: list[str] = []
    articles: list[NewsFlowArticle] = []
    sources: list[NewsFlowSourcePreview] = []
    seen_source_urls: set[str] = set()

    for source_index, source_row in enumerate(source_rows):
        if not isinstance(source_row, dict):
            warnings.append(f"source[{source_index}] is not an object")
            continue
        source_url = str(source_row.get("source_url") or source_row.get("url") or "").strip()
        if source_url not in requested_urls:
            warnings.append(f"{source_url or '<missing>'} is not in requested source URLs")
            continue
        source_name = str(source_row.get("source") or source_row.get("source_name") or "").strip()
        parsed_for_source = _parse_source_articles(
            source_row,
            source_url=source_url,
            source_name=source_name,
            warnings=warnings,
        )
        articles.extend(parsed_for_source)
        sources.append(
            NewsFlowSourcePreview(
                source_url=source_url,
                source_name=source_name or source_url,
                parsed_count=len(parsed_for_source),
            )
        )
        seen_source_urls.add(source_url)

    for source_url in requested_urls:
        if source_url in seen_source_urls:
            continue
        warnings.append(f"{source_url} was requested but not present in the fixture")
        sources.append(NewsFlowSourcePreview(source_url=source_url, source_name=source_url, parsed_count=0))

    deduped = _deduplicate_flow_articles(articles)
    return NewsFlowCollection(
        source_urls=requested_urls,
        sources=sources,
        articles=deduped,
        parsed_count=len(articles),
        deduped_count=len(deduped),
        warnings=warnings,
    )


def build_news_flow_preview(collection: NewsFlowCollection) -> NewsFlowPreview:
    repeated_stocks = _rank_stock_mentions(collection.articles)
    sector_themes = _rank_topics(collection.articles, THEME_RULES)
    key_issues = _rank_topics(collection.articles, ISSUE_RULES)
    caution_signals = _rank_topics(collection.articles, CAUTION_RULES)
    market_mood = _market_mood(
        article_count=len(collection.articles),
        sector_themes=sector_themes,
        key_issues=key_issues,
        caution_signals=caution_signals,
    )
    return NewsFlowPreview(
        source_urls=collection.source_urls,
        sources=collection.sources,
        articles=collection.articles,
        parsed_count=collection.parsed_count,
        deduped_count=collection.deduped_count,
        repeated_stocks=repeated_stocks,
        sector_themes=sector_themes,
        key_issues=key_issues,
        caution_signals=caution_signals,
        market_mood=market_mood,
        telegram_draft=_telegram_draft(
            source_count=len(collection.source_urls),
            article_count=len(collection.articles),
            market_mood=market_mood,
            repeated_stocks=repeated_stocks,
            sector_themes=sector_themes,
            key_issues=key_issues,
            caution_signals=caution_signals,
        ),
        warnings=collection.warnings,
    )


def format_news_flow_preview_text(preview: NewsFlowPreview) -> str:
    lines = [
        "News flow preview",
        f"source URLs: {len(preview.source_urls)}",
        f"articles: {preview.article_count} (parsed {preview.parsed_count}, deduped {preview.deduped_count})",
        f"market mood: {preview.market_mood}",
        "writes_db: False",
        "sends_telegram: False",
        "registers_scheduler: False",
        "connects_web_view: False",
        "",
        "repeated stocks:",
    ]
    lines.extend(_topic_lines(preview.repeated_stocks, empty_label="none repeated"))
    lines.append("")
    lines.append("sector/themes:")
    lines.extend(_topic_lines(preview.sector_themes, empty_label="none detected"))
    lines.append("")
    lines.append("key issues:")
    lines.extend(_topic_lines(preview.key_issues, empty_label="none detected"))
    lines.append("")
    lines.append("caution signals:")
    lines.extend(_topic_lines(preview.caution_signals, empty_label="none detected"))
    if preview.warnings:
        lines.append("")
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in preview.warnings)
    lines.append("")
    lines.append("telegram draft:")
    lines.append(preview.telegram_draft)
    return "\n".join(lines) + "\n"


def _payload_sources(payload: object) -> list[object]:
    if isinstance(payload, dict):
        sources = payload.get("sources")
        if isinstance(sources, list):
            return sources
    if isinstance(payload, list):
        return payload
    raise ValueError("news-flow fixture must be a JSON object with sources[]")


def _parse_source_articles(
    source_row: dict[str, object],
    *,
    source_url: str,
    source_name: str,
    warnings: list[str],
) -> list[NewsFlowArticle]:
    rows = source_row.get("articles")
    if not isinstance(rows, list):
        warnings.append(f"{source_url} has no articles[] list")
        return []
    parsed: list[NewsFlowArticle] = []
    for article_index, row in enumerate(rows):
        if not isinstance(row, dict):
            warnings.append(f"{source_url} article[{article_index}] is not an object")
            continue
        article = _parse_article_row(
            row,
            source_url=source_url,
            source_name=source_name,
            warning_prefix=f"{source_url} article[{article_index}]",
        )
        if article is None:
            warnings.append(f"{source_url} article[{article_index}] is missing title/date/url/source contract fields")
            continue
        parsed.append(article)
    return parsed


def _parse_article_row(
    row: dict[str, object],
    *,
    source_url: str,
    source_name: str,
    warning_prefix: str,
) -> NewsFlowArticle | None:
    title = str(row.get("title") or "").strip()
    raw_date = str(row.get("date") or row.get("published_at") or "").strip()
    url = str(row.get("url") or "").strip()
    source = str(row.get("source") or source_name or "").strip()
    if not title or not raw_date or not url or not source:
        return None
    if not _is_http_url(url):
        return None
    try:
        published_at = _parse_article_datetime(raw_date)
    except ValueError as exc:
        raise ValueError(f"{warning_prefix} has invalid date: {raw_date}") from exc
    return NewsFlowArticle(
        title=title,
        published_at=published_at,
        url=url,
        source=source,
        summary=str(row.get("summary") or "").strip(),
        source_page_url=source_url,
    )


def _parse_article_datetime(value: str) -> datetime:
    normalized = value.strip()
    try:
        if len(normalized) == 10:
            parsed_date = date.fromisoformat(normalized)
            return datetime.combine(parsed_date, time.min, tzinfo=KST)
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(value) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed


def _normalize_source_urls(source_urls: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_url in source_urls:
        url = str(raw_url).strip()
        if not url:
            continue
        if not _is_http_url(url):
            raise ValueError(f"source URL must be http(s): {url}")
        if url in seen:
            continue
        normalized.append(url)
        seen.add(url)
    if not normalized:
        raise ValueError("at least one source URL is required")
    return tuple(normalized)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _deduplicate_flow_articles(articles: list[NewsFlowArticle]) -> list[NewsFlowArticle]:
    deduped: list[NewsFlowArticle] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    for article in articles:
        normalized_url = article.url.strip().casefold()
        normalized_title = normalize_news_text(article.title)
        if normalized_url and normalized_url in seen_urls:
            continue
        if any(
            normalized_title == title
            or title_similarity(normalized_title, title) >= 0.82
            for title in seen_titles
        ):
            continue
        deduped.append(article)
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.append(normalized_title)
    return deduped


def _rank_stock_mentions(articles: list[NewsFlowArticle]) -> list[NewsFlowStockMention]:
    counts: Counter[str] = Counter()
    source_urls: dict[str, set[str]] = defaultdict(set)
    titles: dict[str, list[str]] = defaultdict(list)
    first_seen: dict[str, int] = {}
    rule_order = {name: order for order, (name, _aliases) in enumerate(COMPANY_RULES)}
    for index, article in enumerate(articles):
        if _is_low_signal_flow_article(article):
            continue
        text = article.text().casefold()
        for name, aliases in COMPANY_RULES:
            if not any(alias.casefold() in text for alias in aliases):
                continue
            counts[name] += 1
            source_urls[name].add(article.source_page_url)
            if len(titles[name]) < 3:
                titles[name].append(article.title)
            first_seen.setdefault(name, index)
    ranked_names = sorted(
        (name for name, count in counts.items() if count >= 2),
        key=lambda name: (-counts[name], first_seen[name], rule_order[name]),
    )
    return [
        NewsFlowStockMention(
            name=name,
            article_count=counts[name],
            source_count=len(source_urls[name]),
            article_titles=tuple(titles[name]),
        )
        for name in ranked_names[:8]
    ]


def _rank_topics(
    articles: list[NewsFlowArticle],
    rules: tuple[tuple[str, tuple[str, ...]], ...],
) -> list[NewsFlowTopic]:
    counts: Counter[str] = Counter()
    source_urls: dict[str, set[str]] = defaultdict(set)
    titles: dict[str, list[str]] = defaultdict(list)
    first_seen: dict[str, int] = {}
    for index, article in enumerate(articles):
        if _is_low_signal_flow_article(article):
            continue
        text = article.text().casefold()
        for label, terms in rules:
            if not any(_contains_topic_term(text, term) for term in terms):
                continue
            counts[label] += 1
            source_urls[label].add(article.source_page_url)
            if len(titles[label]) < 3:
                titles[label].append(article.title)
            first_seen.setdefault(label, index)
    ranked_labels = sorted(
        counts,
        key=lambda label: (-counts[label], first_seen[label], label),
    )
    return [
        NewsFlowTopic(
            label=label,
            article_count=counts[label],
            source_count=len(source_urls[label]),
            article_titles=tuple(titles[label]),
        )
        for label in ranked_labels[:8]
    ]


def _is_low_signal_flow_article(article: NewsFlowArticle) -> bool:
    title = article.title.casefold().strip()
    return any(marker.casefold() in title for marker in LOW_SIGNAL_TITLE_MARKERS)


def _contains_topic_term(text: str, term: str) -> bool:
    normalized_term = term.casefold().strip()
    if not normalized_term:
        return False
    if _is_ascii_word_phrase(normalized_term):
        return re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", text) is not None
    return normalized_term in text


def _is_ascii_word_phrase(value: str) -> bool:
    return all(char.isascii() and (char.isalnum() or char.isspace()) for char in value)


def _market_mood(
    *,
    article_count: int,
    sector_themes: list[NewsFlowTopic],
    key_issues: list[NewsFlowTopic],
    caution_signals: list[NewsFlowTopic],
) -> str:
    if article_count == 0:
        return "No parsed articles in the requested source URLs"
    if caution_signals and (sector_themes or key_issues):
        return "Active theme flow with visible caution signals"
    if sector_themes:
        return "Theme-led market flow"
    if key_issues:
        return "Issue-led market flow"
    return "Sparse or uncategorized news flow"


def _telegram_draft(
    *,
    source_count: int,
    article_count: int,
    market_mood: str,
    repeated_stocks: list[NewsFlowStockMention],
    sector_themes: list[NewsFlowTopic],
    key_issues: list[NewsFlowTopic],
    caution_signals: list[NewsFlowTopic],
) -> str:
    return "\n".join(
        [
            "[뉴스 흐름 브리핑 초안]",
            f"제공 source URL {source_count}개, 기사 {article_count}건 기준 시장 분위기: {_draft_mood(market_mood)}.",
            f"반복 등장 종목: {_compact_items(repeated_stocks, name_attr='name')}",
            f"섹터/테마: {_compact_items(sector_themes)}",
            f"주요 이슈: {_compact_items(key_issues)}",
            f"경계 신호: {_compact_items(caution_signals)}",
            "매매 판단 없이 제공 source URL 기사 흐름만 요약했습니다.",
        ]
    )


def _draft_mood(market_mood: str) -> str:
    return DRAFT_MOOD_LABELS.get(market_mood, market_mood)


def _draft_label(label: str) -> str:
    return DRAFT_LABELS.get(label, label)


def _compact_items(items: Sequence[object], *, name_attr: str = "label") -> str:
    if not items:
        return "없음"
    parts: list[str] = []
    for item in items[:4]:
        name = _draft_label(str(getattr(item, name_attr)))
        count = int(getattr(item, "article_count"))
        parts.append(f"{name}({count})")
    return ", ".join(parts)


def _topic_lines(items: Sequence[object], *, empty_label: str) -> list[str]:
    if not items:
        return [f"- {empty_label}"]
    lines: list[str] = []
    for item in items[:5]:
        label = str(getattr(item, "name", getattr(item, "label", "-")))
        article_count = int(getattr(item, "article_count"))
        source_count = int(getattr(item, "source_count"))
        lines.append(f"- {label}: {article_count} articles / {source_count} sources")
    return lines
