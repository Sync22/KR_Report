from __future__ import annotations

import re

from .models import NewsArticle


_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def normalize_news_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower()))


def tokenize_news_text(value: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(value.lower()) if len(token) >= 2}


def title_similarity(left: str, right: str) -> float:
    left_tokens = tokenize_news_text(left)
    right_tokens = tokenize_news_text(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def deduplicate_articles(
    articles: list[NewsArticle],
    *,
    similar_title_threshold: float = 0.82,
) -> list[NewsArticle]:
    deduped: list[NewsArticle] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    for article in articles:
        normalized_url = article.url.strip().lower()
        normalized_title = normalize_news_text(article.title)
        if normalized_url and normalized_url in seen_urls:
            continue
        if any(
            normalized_title == title
            or title_similarity(normalized_title, title) >= similar_title_threshold
            for title in seen_titles
        ):
            continue
        deduped.append(article)
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.append(normalized_title)
    return deduped
