import json
from pathlib import Path

import pytest

from stock_monitor.news import (
    CoreKeyword,
    CoreKeywordDocument,
    CoreKeywordExtraction,
    extract_core_keywords,
    plan_core_keyword_queries,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "keyword_search_expansion"


def _load(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


DOCUMENTS = _load("documents.json")
QUERY_GOLD = {record["document_id"]: record for record in _load("query_gold.json")}


@pytest.mark.parametrize("fixture", DOCUMENTS, ids=lambda item: item["id"])
def test_document_to_query_plan_matches_frozen_gold(fixture: dict) -> None:
    extraction = extract_core_keywords(_document(fixture))
    plan = plan_core_keyword_queries(fixture["stock_name"], extraction)
    gold = QUERY_GOLD[fixture["id"]]

    assert [
        {"query": item.query, "strategy": item.strategy, "priority": item.priority}
        for item in plan.queries
    ] == gold["expected_queries"]
    assert {item.query for item in plan.queries}.isdisjoint(gold["forbidden_queries"])


def test_zero_keywords_produce_zero_queries() -> None:
    plan = plan_core_keyword_queries("현대차", CoreKeywordExtraction(accepted=(), rejected=()))

    assert plan.target == "현대차"
    assert plan.queries == ()


def test_product_counterparty_pair_places_counterparty_first() -> None:
    extraction = _extraction(
        CoreKeyword("HBM4", "product", 1),
        CoreKeyword("엔비디아", "counterparty", 2),
    )

    plan = plan_core_keyword_queries("삼성전자", extraction)

    assert plan.queries[1].query == "삼성전자 엔비디아 HBM4"


def test_redundant_counterparty_event_uses_next_partner() -> None:
    extraction = _extraction(
        CoreKeyword("로카모빌리티", "counterparty", 1),
        CoreKeyword("로카모빌리티 인수", "event", 2),
        CoreKeyword("모빌리티 데이터", "industry", 3),
    )

    plan = plan_core_keyword_queries("카카오", extraction)

    assert plan.queries[1].query == "카카오 로카모빌리티 모빌리티 데이터"


def test_third_query_requires_four_accepted_keywords() -> None:
    three = _extraction(
        CoreKeyword("LNG선", "product", 1),
        CoreKeyword("메탄올 추진선", "technology", 2),
        CoreKeyword("카타르 LNG 프로젝트", "event", 3),
    )
    four = _extraction(*three.accepted, CoreKeyword("친환경 선박 사이클", "market_theme", 4))

    assert len(plan_core_keyword_queries("HD한국조선해양", three).queries) == 2
    assert [item.query for item in plan_core_keyword_queries("HD한국조선해양", four).queries] == [
        "HD한국조선해양 LNG선",
        "HD한국조선해양 LNG선 메탄올 추진선",
        "HD한국조선해양 카타르 LNG 프로젝트",
    ]


def test_planner_deduplicates_normalized_keywords_and_is_deterministic() -> None:
    extraction = _extraction(
        CoreKeyword("HBM4", "product", 1),
        CoreKeyword("HBM 4", "product", 2),
        CoreKeyword("고객 인증", "event", 3),
    )

    first = plan_core_keyword_queries(" 삼성전자 ", extraction)
    second = plan_core_keyword_queries("삼성전자", extraction)

    assert first == second
    assert isinstance(first.queries, tuple)
    assert [item.query for item in first.queries] == [
        "삼성전자 HBM4",
        "삼성전자 HBM4 고객 인증",
    ]


@pytest.mark.parametrize("max_queries", [0, 4])
def test_max_queries_must_stay_within_frozen_contract(max_queries: int) -> None:
    with pytest.raises(ValueError, match="max_queries must be between 1 and 3"):
        plan_core_keyword_queries("삼성전자", _extraction(CoreKeyword("HBM4", "product", 1)), max_queries=max_queries)


def test_max_queries_one_returns_only_primary_query() -> None:
    extraction = _extraction(
        CoreKeyword("HBM4", "product", 1),
        CoreKeyword("엔비디아", "counterparty", 2),
    )

    assert [item.query for item in plan_core_keyword_queries("삼성전자", extraction, max_queries=1).queries] == [
        "삼성전자 HBM4"
    ]


@pytest.mark.parametrize("target", ["", "   "])
def test_target_must_be_non_empty(target: str) -> None:
    with pytest.raises(ValueError, match="target must be non-empty"):
        plan_core_keyword_queries(target, _extraction(CoreKeyword("HBM4", "product", 1)))


def _extraction(*keywords: CoreKeyword) -> CoreKeywordExtraction:
    return CoreKeywordExtraction(accepted=keywords, rejected=())


def _document(fixture: dict) -> CoreKeywordDocument:
    return CoreKeywordDocument(
        document_type=fixture["document_type"],
        stock_name=fixture["stock_name"],
        stock_code=fixture["stock_code"],
        title=fixture["title"],
        summary=fixture["summary"],
    )
