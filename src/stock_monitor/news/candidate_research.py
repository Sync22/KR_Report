"""Source-backed research prompts for the existing Top2 surfaces.

Prompts are questions to investigate, never additional evidence or rank input.
The collector retains its stock-identity matching boundary.
"""

from urllib.parse import urlencode

from .core_keywords import CoreKeywordDocument, extract_core_keywords
from .query_planner import plan_core_keyword_queries


def build_candidate_research_focus(
    stock_name: str,
    documents: tuple[CoreKeywordDocument, ...],
) -> dict:
    items: list[dict] = []
    seen: set[str] = set()
    for document in documents:
        if document.stock_name != stock_name:
            continue
        title = document.title.strip()
        if not title or "\ufffd" in title or not stock_name.strip():
            continue
        extraction = extract_core_keywords(document)
        queries = plan_core_keyword_queries(stock_name, extraction).queries
        # Preserve a usable source title when the narrow keyword rules abstain.
        candidates = [query.query for query in queries] or [f"{stock_name} {title}"]
        for query in candidates:
            identity = "".join(query.casefold().split())
            if identity in seen:
                continue
            seen.add(identity)
            items.append({
                "topic": " · ".join(keyword.value for keyword in extraction.accepted[:2]) if queries else title,
                "source_title": title,
                "source_kind": "리포트" if document.document_type == "report" else "저장 뉴스",
                "basis": "keywords" if queries else "source_title",
                "query": query,
                "search_url": "https://search.naver.com/search.naver?" + urlencode({"where": "news", "query": query}),
            })
            if len(items) == 3:
                break
        if len(items) == 3:
            break
    return {
        "available": bool(items),
        "items": items,
        "notice": "원문에서 뽑은 확인 주제입니다. 검색 결과는 별도로 확인하세요.",
    }
