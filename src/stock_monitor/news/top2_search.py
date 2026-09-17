"""One bounded search per selected stock; search snippets remain unverified evidence."""

import json
import re
from dataclasses import replace
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urlencode
from typing import Callable

from .collectors import (
    KST, NaverNewsRequestSpec, NewsCollectionPreview,
    NewsSource, NewsSourcePreview, StockNewsQuery, match_articles_to_stock_with_reasons,
)
from .models import NewsArticle
from .linked_evidence import canonicalize_news_url
from .preprocess import deduplicate_articles


def search_query(stock_name: str, focus: dict) -> str:
    items = focus.get("items") or []
    if not items:
        return ""
    item = items[0]
    if item.get("basis") == "keywords":
        return str(item["query"])
    # A full report headline is too restrictive. Keep its first source phrase.
    phrase = str(item.get("source_title") or "").split(",", 1)[0]
    phrase = " ".join(phrase.split()[:2]).strip()
    return f"{stock_name} {phrase}" if phrase else ""


def parse_search(content: str, query: StockNewsQuery, captured_at: datetime) -> tuple[list[NewsArticle], list[dict]]:
    """Parse at most five cards, retaining timestamp precision in the audit trace."""
    empty = "검색결과가 없습니다" in content or "검색 결과가 없습니다" in content
    if "뉴스검색 결과" not in content and not empty:
        raise ValueError("unrecognized_search_page")
    articles = []
    cards = []
    publisher = ""
    raw_time = ""
    for line in content.splitlines():
        line = line.strip()
        if "프로필 이미지" in line:
            publisher, raw_time = "", ""
        if re.fullmatch(r"(?:\d+\s*(?:분|시간|일) 전|\d{4}\.\d{2}\.\d{2}\.?(?:\s+\d{2}:\d{2})?)", line):
            raw_time = line
            continue
        if not line.startswith("[") or line.startswith("[!"):
            continue
        links = re.findall(r"\[(.+?)새 창 열림\]\((https?://[^\s)]+)\)", line)
        if not links:
            continue
        if len(links) == 1:
            if not raw_time:
                publisher = links[0][0].strip()
            continue
        title, url = links[0]
        if links[1][1] != url:
            continue
        title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
        snippet = unescape(re.sub(r"<[^>]+>", "", links[1][0])).strip()
        card = {"title": title, "url": url, "source": publisher,
                "raw_time": raw_time, "accepted": False}
        cards.append(card)
        timestamp = None
        relative = re.fullmatch(r"(\d+)\s*(분|시간) 전", raw_time)
        if relative:
            amount = int(relative[1])
            timestamp = captured_at - timedelta(minutes=amount if relative[2] == "분" else amount * 60)
            card["time_precision"] = "relative_minute" if relative[2] == "분" else "relative_hour"
            uncertainty = timedelta(seconds=59) if relative[2] == "분" else timedelta(minutes=59)
            if (timestamp - uncertainty).date() != query.target_date:
                timestamp = None
        else:
            try:
                timestamp = datetime.strptime(raw_time, "%Y.%m.%d. %H:%M").replace(tzinfo=KST)
                card["time_precision"] = "minute"
            except ValueError:
                pass
        identity = r"(?<!\w)" + re.escape(query.stock_name) + r"(?:은|는|이|가|의|도|와|과|에|를|을)?(?!\w)"
        if not re.search(identity, title, re.IGNORECASE):
            card["rejection"] = "stock_not_in_title"
        elif not publisher or not timestamp or timestamp.date() != query.target_date or timestamp > captured_at:
            card["rejection"] = "missing_source_or_unverified_date"
        else:
            card.update(accepted=True, published_at=timestamp.isoformat())
            articles.append(NewsArticle(title=title, summary=snippet, source=publisher,
                                        published_at=timestamp, url=url, source_lane="top2_search"))
        raw_time = ""
        if len(cards) == 5:
            break
    if not cards and not empty:
        raise ValueError("search_cards_not_recognized")
    return articles, cards


def augment_preview(preview: NewsCollectionPreview, query: StockNewsQuery,
                    focus: dict, transport: Callable[[NaverNewsRequestSpec], str], *,
                    clock: Callable[[], datetime] | None = None) -> tuple[NewsCollectionPreview, dict]:
    text = search_query(query.stock_name, focus)
    trace = {"query": text, "source_title": (focus.get("items") or [{}])[0].get("source_title"),
             "status": "skipped_no_topic", "cards": [], "added_count": 0}
    if not text:
        return replace(preview, warnings=[*preview.warnings, "top2_search: " + json.dumps(trace)]), trace
    day = query.target_date.strftime("%Y.%m.%d")
    url = "https://search.naver.com/search.naver?" + urlencode(
        dict(where="news", query=text, sort="1", pd="3", ds=day, de=day))
    spec = NaverNewsRequestSpec(source=NewsSource.TOP2_SEARCH, page_url=url,
                               target_date=query.target_date, source_fetch_mode="bounded_search_snippets")
    error = None
    articles = []
    try:
        content = transport(spec)
        captured_at = clock() if clock else datetime.now(KST)
        trace["captured_at"] = captured_at.isoformat()
        articles, cards = parse_search(content, query, captured_at)
        trace.update(status="success", cards=cards)
    except Exception as exc:
        # A failed optional lane must not discard the five existing source lanes.
        error = type(exc).__name__
        trace.update(status="failed", error=error)
    seen_urls = {canonicalize_news_url(match.article.url) for match in preview.articles}
    unique = []
    for article in articles:
        canonical = canonicalize_news_url(article.url)
        if canonical not in seen_urls:
            unique.append(article)
            seen_urls.add(canonical)
    retained = deduplicate_articles([match.article for match in preview.articles] + unique)
    new_articles = [article for article in retained if any(article is row for row in articles)]
    matches = list(preview.articles) + match_articles_to_stock_with_reasons(new_articles, query)
    trace.update(added_count=len(new_articles), page_url=url)
    source = NewsSourcePreview(source=spec.source, page_url=url, target_date=query.target_date,
        collection_mode=spec.collection_mode, source_fetch_mode=spec.source_fetch_mode,
        section_name=None, response_format="markdown", fetched=error is None, fetch_error=error,
        parsed_count=len(trace["cards"]), matched_count=len(articles))
    return replace(preview, sources=[*preview.sources, source], articles=matches,
        parsed_count=preview.parsed_count + len(trace["cards"]),
        deduped_count=preview.deduped_count + len(new_articles), matched_count=len(matches),
        warnings=[*preview.warnings, "top2_search: " + json.dumps(trace, ensure_ascii=False)]), trace
