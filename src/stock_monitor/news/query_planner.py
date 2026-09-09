from __future__ import annotations

import re
from dataclasses import dataclass

from .core_keywords import CoreKeyword, CoreKeywordExtraction


@dataclass(frozen=True)
class PlannedCoreKeywordQuery:
    query: str
    strategy: str
    priority: int


@dataclass(frozen=True)
class CoreKeywordQueryPlan:
    target: str
    queries: tuple[PlannedCoreKeywordQuery, ...]


_MAX_QUERIES = 3
_SINGLE_STRATEGY = "target_plus_keyword"
_PAIR_STRATEGY = "target_plus_pair"


def plan_core_keyword_queries(
    target: str,
    extraction: CoreKeywordExtraction,
    *,
    max_queries: int = 3,
) -> CoreKeywordQueryPlan:
    normalized_target = target.strip()
    if not normalized_target:
        raise ValueError("target must be non-empty")
    if not 1 <= max_queries <= _MAX_QUERIES:
        raise ValueError("max_queries must be between 1 and 3")

    accepted = _unique_keywords(normalized_target, extraction.accepted)
    if not accepted:
        return CoreKeywordQueryPlan(target=normalized_target, queries=())

    candidates: list[tuple[str, str]] = [
        (f"{normalized_target} {accepted[0].value}", _SINGLE_STRATEGY)
    ]
    pair_partner_index = _select_pair_partner(accepted)
    if pair_partner_index is not None:
        first, second = _order_pair(accepted[0], accepted[pair_partner_index])
        candidates.append((f"{normalized_target} {first.value} {second.value}", _PAIR_STRATEGY))

    if len(accepted) >= 4:
        used = {0, pair_partner_index}
        breadth_index = next((index for index in range(1, len(accepted)) if index not in used), None)
        if breadth_index is not None:
            candidates.append((f"{normalized_target} {accepted[breadth_index].value}", _SINGLE_STRATEGY))

    queries: list[PlannedCoreKeywordQuery] = []
    seen: set[str] = set()
    for query, strategy in candidates:
        identity = _normalize_identity(query)
        if identity in seen:
            continue
        seen.add(identity)
        queries.append(PlannedCoreKeywordQuery(query=query, strategy=strategy, priority=len(queries) + 1))
        if len(queries) == max_queries:
            break

    return CoreKeywordQueryPlan(target=normalized_target, queries=tuple(queries))


def _unique_keywords(target: str, accepted: tuple[CoreKeyword, ...]) -> tuple[CoreKeyword, ...]:
    target_identity = _normalize_identity(target)
    seen: set[str] = set()
    result: list[CoreKeyword] = []
    for keyword in accepted:
        identity = _normalize_identity(keyword.value)
        if not identity or identity == target_identity or identity in seen:
            continue
        seen.add(identity)
        result.append(keyword)
    return tuple(result)


def _select_pair_partner(accepted: tuple[CoreKeyword, ...]) -> int | None:
    if len(accepted) < 2:
        return None
    anchor = accepted[0]
    anchor_identity = _normalize_identity(anchor.value)
    for index, candidate in enumerate(accepted[1:], start=1):
        if (
            anchor.kind == "counterparty"
            and candidate.kind == "event"
            and anchor_identity in _normalize_identity(candidate.value)
        ):
            continue
        return index
    return None


def _order_pair(first: CoreKeyword, second: CoreKeyword) -> tuple[CoreKeyword, CoreKeyword]:
    if first.kind == "product" and second.kind == "counterparty":
        return second, first
    return first, second


def _normalize_identity(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()
