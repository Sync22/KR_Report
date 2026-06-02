from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

from .models import NewsArticle
from .preprocess import deduplicate_articles


KST = ZoneInfo("Asia/Seoul")
NAVER_NEWS_BASE_URL = "https://stock.naver.com/news"
NAVER_FOCUS_NEWS_API_URL = "https://stock.naver.com/api/domestic/news/focus"


class NewsSource(str, Enum):
    FLASHNEWS = "flashnews"
    MAINNEWS = "mainnews"
    RANKNEWS = "ranknews"
    SECTION_MARKET_OUTLOOK = "section_market_outlook"
    SECTION_COMPANY_ANALYSIS = "section_company_analysis"


@dataclass(frozen=True)
class StockNewsQuery:
    stock_name: str
    stock_code: str | None = None
    aliases: tuple[str, ...] = ()
    target_date: date | None = None


@dataclass(frozen=True)
class NaverNewsRequestSpec:
    source: NewsSource
    page_url: str
    target_date: date
    collection_mode: str = "date"
    source_fetch_mode: str = "latest_rendered_page_date_filter"
    section_name: str | None = None
    response_format: str = "markdown"


@dataclass(frozen=True)
class MatchedNewsArticle:
    article: NewsArticle
    matched_alias: str
    match_reason: str
    match_scope: str
    relevance: str
    relevance_reason: str

    @property
    def source_lane(self) -> str | None:
        return self.article.source_lane

    def to_dict(self) -> dict[str, object]:
        payload = self.article.to_dict()
        payload.update(
            {
                "matched_alias": self.matched_alias,
                "match_reason": self.match_reason,
                "match_scope": self.match_scope,
                "relevance": self.relevance,
                "relevance_reason": self.relevance_reason,
            }
        )
        return payload


@dataclass(frozen=True)
class NewsSourcePreview:
    source: NewsSource
    page_url: str
    target_date: date
    collection_mode: str
    source_fetch_mode: str
    section_name: str | None
    response_format: str
    fetched: bool
    fetch_error: str | None
    parsed_count: int
    matched_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "page_url": self.page_url,
            "target_date": self.target_date.isoformat(),
            "collection_mode": self.collection_mode,
            "source_fetch_mode": self.source_fetch_mode,
            "section_name": self.section_name,
            "response_format": self.response_format,
            "fetched": self.fetched,
            "fetch_error": self.fetch_error,
            "parsed_count": self.parsed_count,
            "matched_count": self.matched_count,
        }


@dataclass(frozen=True)
class NewsCollectionPreview:
    sources: list[NewsSourcePreview]
    articles: list[MatchedNewsArticle]
    parsed_count: int
    deduped_count: int
    matched_count: int
    warnings: list[str]


class NewsCollector(Protocol):
    def collect(self, query: StockNewsQuery) -> list[NewsArticle]:
        ...


def build_naver_news_request_specs(target_date: date) -> list[NaverNewsRequestSpec]:
    date_param = target_date.strftime("%Y%m%d")
    return [
        NaverNewsRequestSpec(
            source=NewsSource.FLASHNEWS,
            page_url=f"{NAVER_NEWS_BASE_URL}/flashnews",
            target_date=target_date,
        ),
        NaverNewsRequestSpec(
            source=NewsSource.MAINNEWS,
            page_url=f"{NAVER_NEWS_BASE_URL}/mainnews",
            target_date=target_date,
        ),
        NaverNewsRequestSpec(
            source=NewsSource.RANKNEWS,
            page_url=f"{NAVER_NEWS_BASE_URL}/ranknews",
            target_date=target_date,
        ),
        NaverNewsRequestSpec(
            source=NewsSource.SECTION_MARKET_OUTLOOK,
            page_url=(
                f"{NAVER_FOCUS_NEWS_API_URL}?sid=401&page=1&pageSize=20&date={date_param}"
            ),
            target_date=target_date,
            source_fetch_mode="date_api",
            section_name="시황·전망",
            response_format="focus_json",
        ),
        NaverNewsRequestSpec(
            source=NewsSource.SECTION_COMPANY_ANALYSIS,
            page_url=(
                f"{NAVER_FOCUS_NEWS_API_URL}?sid=402&page=1&pageSize=20&date={date_param}"
            ),
            target_date=target_date,
            source_fetch_mode="date_api",
            section_name="기업·종목분석",
            response_format="focus_json",
        ),
    ]


def parse_naver_news_markdown(
    content: str,
    *,
    source: NewsSource,
    target_date: date,
) -> list[NewsArticle]:
    articles: list[NewsArticle] = []
    matches = list(
        re.finditer(
            r"(?:^|\n)\s*(?:[:*])\s*(\d{4})\.\s*(\d{2})\.\s*(\d{2})\.\s*(\d{2}):(\d{2})",
            content,
        )
    )
    for index, match in enumerate(matches):
        year, month, day, hour, minute = (int(part) for part in match.groups())
        if date(year, month, day) != target_date:
            continue
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.end() : block_end]
        title = _extract_markdown_title(block)
        if not title:
            continue
        url = _extract_article_url(block)
        if not url:
            continue
        body_lines = _article_body_lines(block)
        source_name = _extract_source_name(body_lines)
        summary = _extract_summary(body_lines, source_name)
        articles.append(
            NewsArticle(
                title=title,
                summary=summary,
                source=source_name,
                published_at=datetime(year, month, day, hour, minute, tzinfo=KST),
                url=url,
                source_lane=source.value,
            )
        )
    return articles


def parse_naver_focus_news_json(
    content: str,
    *,
    source: NewsSource,
    target_date: date,
) -> list[NewsArticle]:
    payload = json.loads(content)
    rows = payload.get("articles", []) if isinstance(payload, dict) else []
    articles: list[NewsArticle] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        published_at = _parse_focus_news_datetime(str(row.get("date", "")))
        if published_at is None or published_at.date() != target_date:
            continue
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not title or not url:
            continue
        articles.append(
            NewsArticle(
                title=title,
                summary=str(row.get("subcontent") or "").strip(),
                source=str(row.get("officeHName") or "").strip(),
                published_at=published_at,
                url=url,
                source_lane=source.value,
            )
        )
    return articles


def match_articles_to_stock(
    articles: list[NewsArticle],
    query: StockNewsQuery,
) -> list[NewsArticle]:
    return [match.article for match in match_articles_to_stock_with_reasons(articles, query)]


def match_articles_to_stock_with_reasons(
    articles: list[NewsArticle],
    query: StockNewsQuery,
) -> list[MatchedNewsArticle]:
    matched: list[MatchedNewsArticle] = []
    for article in articles:
        match = _match_article_to_stock(article, query)
        if match is None:
            continue
        matched_alias, match_reason, match_scope, relevance, relevance_reason = match
        matched.append(
            MatchedNewsArticle(
                article=article,
                matched_alias=matched_alias,
                match_reason=match_reason,
                match_scope=match_scope,
                relevance=relevance,
                relevance_reason=relevance_reason,
            )
        )
    return matched


class ManualNewsCollector:
    def __init__(self, articles: list[NewsArticle]) -> None:
        self._articles = articles

    def collect(self, query: StockNewsQuery) -> list[NewsArticle]:
        return match_articles_to_stock(deduplicate_articles(self._articles), query)


class NaverStockNewsCollector:
    def __init__(self, *, transport: Callable[[str], str]) -> None:
        self._transport = transport

    def collect(self, query: StockNewsQuery) -> list[NewsArticle]:
        target_date = query.target_date or datetime.now(tz=KST).date()
        collected: list[NewsArticle] = []
        for spec in build_naver_news_request_specs(target_date):
            response_text = self._transport(spec.page_url)
            if spec.response_format == "focus_json":
                collected.extend(
                    parse_naver_focus_news_json(
                        response_text,
                        source=spec.source,
                        target_date=target_date,
                    )
                )
            else:
                collected.extend(
                    parse_naver_news_markdown(
                        response_text,
                        source=spec.source,
                        target_date=target_date,
                    )
                )
        return match_articles_to_stock(deduplicate_articles(collected), query)


class ScraplingNewsTransport:
    def __init__(
        self,
        *,
        scrapling_exe: Path,
        runner: Callable[..., object] | None = None,
        timeout_ms: int = 45_000,
        wait_ms: int = 1_500,
    ) -> None:
        self._scrapling_exe = Path(scrapling_exe)
        self._runner = runner or subprocess.run
        self._timeout_ms = timeout_ms
        self._wait_ms = wait_ms

    def __call__(self, spec: NaverNewsRequestSpec) -> str:
        suffix = ".txt" if spec.response_format == "focus_json" else ".md"
        temp_path = _make_temp_output_path(suffix)
        try:
            command = self._build_command(spec, temp_path)
            result = self._runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=(self._timeout_ms / 1000) + 15,
            )
            if result.returncode != 0:
                raise RuntimeError(_format_scrapling_error(result.returncode))
            return temp_path.read_text(encoding="utf-8")
        finally:
            temp_path.unlink(missing_ok=True)

    def _build_command(self, spec: NaverNewsRequestSpec, temp_path: Path) -> list[str]:
        if spec.response_format == "focus_json":
            return [
                str(self._scrapling_exe),
                "extract",
                "get",
                spec.page_url,
                str(temp_path),
                "--timeout",
                str(self._timeout_ms),
            ]
        return [
            str(self._scrapling_exe),
            "extract",
            "fetch",
            spec.page_url,
            str(temp_path),
            "--ai-targeted",
            "--network-idle",
            "--wait",
            str(self._wait_ms),
            "--timeout",
            str(self._timeout_ms),
        ]


def collect_naver_news_preview(
    query: StockNewsQuery,
    *,
    transport: Callable[[NaverNewsRequestSpec], str],
) -> NewsCollectionPreview:
    target_date = query.target_date or datetime.now(tz=KST).date()
    all_articles: list[NewsArticle] = []
    source_previews: list[NewsSourcePreview] = []
    warnings: list[str] = []

    for spec in build_naver_news_request_specs(target_date):
        fetched = False
        fetch_error: str | None = None
        parsed: list[NewsArticle] = []
        try:
            response_text = transport(spec)
            fetched = True
            parsed = _parse_naver_news_response(response_text, spec)
        except Exception as exc:
            fetch_error = _public_error_message(exc)
            warnings.append(f"{spec.source.value}: {fetch_error}")
        source_previews.append(
            NewsSourcePreview(
                source=spec.source,
                page_url=spec.page_url,
                target_date=spec.target_date,
                collection_mode=spec.collection_mode,
                source_fetch_mode=spec.source_fetch_mode,
                section_name=spec.section_name,
                response_format=spec.response_format,
                fetched=fetched,
                fetch_error=fetch_error,
                parsed_count=len(parsed),
                matched_count=len(match_articles_to_stock_with_reasons(parsed, query)),
            )
        )
        all_articles.extend(parsed)

    deduped_articles = deduplicate_articles(all_articles)
    matched_articles = match_articles_to_stock_with_reasons(deduped_articles, query)
    if not all_articles:
        warnings.append("No Naver news articles were parsed from the selected source lanes.")
    if not matched_articles and all_articles:
        warnings.append("No parsed articles matched the requested stock name, code, or aliases.")
    return NewsCollectionPreview(
        sources=source_previews,
        articles=matched_articles,
        parsed_count=len(all_articles),
        deduped_count=len(deduped_articles),
        matched_count=len(matched_articles),
        warnings=warnings,
    )


def _extract_markdown_title(block: str) -> str:
    match = re.search(r"\[(?:###\s*)?(.+?)(?:\n|$)", block)
    return match.group(1).strip() if match else ""


def _parse_naver_news_response(response_text: str, spec: NaverNewsRequestSpec) -> list[NewsArticle]:
    if spec.response_format == "focus_json":
        return parse_naver_focus_news_json(
            response_text,
            source=spec.source,
            target_date=spec.target_date,
        )
    return parse_naver_news_markdown(
        response_text,
        source=spec.source,
        target_date=spec.target_date,
    )


def _extract_article_url(block: str) -> str:
    urls = re.findall(r"\]\((https?://[^)\s]+)", block)
    for url in urls:
        if "n.news.naver.com" in url:
            return url
    return urls[-1] if urls else ""


def _article_body_lines(block: str) -> list[str]:
    lines: list[str] = []
    seen_title = False
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and not line.startswith("![]("):
            seen_title = True
            continue
        if not seen_title:
            continue
        if line.startswith("![]("):
            break
        if re.fullmatch(r"-{3,}", line):
            continue
        lines.append(line)
    return lines


def _extract_source_name(lines: list[str]) -> str:
    if not lines:
        return ""
    return lines[-1].split("](", 1)[0].strip()


def _extract_summary(lines: list[str], source_name: str) -> str:
    summary_lines = lines[:-1] if source_name else lines
    return " ".join(summary_lines).strip()


def _query_aliases(query: StockNewsQuery) -> tuple[str, ...]:
    raw_aliases = (query.stock_name, query.stock_code or "", *query.aliases)
    return tuple(alias.casefold() for alias in raw_aliases if alias and alias.strip())


def _query_alias_rules(query: StockNewsQuery) -> tuple[tuple[str, str, str], ...]:
    rules: list[tuple[str, str, str]] = []
    if query.stock_name and query.stock_name.strip():
        rules.append((query.stock_name, query.stock_name.casefold(), "stock_name"))
    if query.stock_code and query.stock_code.strip():
        rules.append((query.stock_code, query.stock_code.casefold(), "stock_code"))
    for alias in query.aliases:
        if alias and alias.strip():
            rules.append((alias, alias.casefold(), "alias"))
    return tuple(rules)


def _match_article_to_stock(article: NewsArticle, query: StockNewsQuery) -> tuple[str, str, str, str, str] | None:
    title = article.title.casefold()
    summary = article.summary.casefold()
    haystack = f"{title} {summary}"
    for display_alias, normalized_alias, match_reason in _query_alias_rules(query):
        title_hit = normalized_alias in title
        summary_hit = normalized_alias in summary
        if title_hit or summary_hit:
            match_scope = _match_scope(title_hit=title_hit, summary_hit=summary_hit)
            relevance, relevance_reason = _article_relevance(
                article,
                match_scope=match_scope,
                matched_alias=display_alias,
            )
            return display_alias, match_reason, match_scope, relevance, relevance_reason
    return None


def _match_scope(*, title_hit: bool, summary_hit: bool) -> str:
    if title_hit and summary_hit:
        return "both"
    if title_hit:
        return "title"
    return "summary"


def _article_relevance(article: NewsArticle, *, match_scope: str, matched_alias: str) -> tuple[str, str]:
    text = f"{article.title} {article.summary}".casefold()
    if _contains_market_context(text):
        return "market_context", f"{matched_alias} appears inside broader market context."
    if match_scope in {"title", "both"}:
        return "direct", f"{matched_alias} appears in article title and summary." if match_scope == "both" else f"{matched_alias} appears in article title."
    return "indirect", f"{matched_alias} appears only in article summary/body."


def _contains_market_context(text: str) -> bool:
    market_terms = (
        "etf",
        "index",
        "kospi",
        "sector",
        "코스피",
        "코스닥",
        "지수",
        "업종",
        "상장지수펀드",
        "레버리지",
        "수급 쏠림",
        "시장 전반",
    )
    return any(term in text for term in market_terms)


def _make_temp_output_path(suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="stock-monitor-news-", suffix=suffix, delete=False)
    handle.close()
    return Path(handle.name)


def _format_scrapling_error(returncode: int) -> str:
    return f"Scrapling exited with code {returncode}"


def _public_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message.replace("\r", " ").replace("\n", " ")[:240]


def _parse_focus_news_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if len(normalized) < 12:
        return None
    for length, pattern in ((14, "%Y%m%d%H%M%S"), (12, "%Y%m%d%H%M")):
        if len(normalized) >= length:
            try:
                return datetime.strptime(normalized[:length], pattern).replace(tzinfo=KST)
            except ValueError:
                continue
    return None
