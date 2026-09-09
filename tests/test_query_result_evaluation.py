import json
from dataclasses import replace
from pathlib import Path

import pytest

from stock_monitor.news import (
    CoreKeywordDocument,
    QueryResultBatch,
    QueryResultFact,
    QueryResultJudgment,
    evaluate_query_results,
    extract_core_keywords,
    plan_core_keyword_queries,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "query_result_evaluation"
KEYWORD_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "keyword_search_expansion"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


CONTRACT = _load(FIXTURE_DIR / "contract_v1.json")
RAW_CASES = _load(FIXTURE_DIR / "result_facts.json")
JUDGMENT_FIXTURE = _load(FIXTURE_DIR / "judgments.json")
DOCUMENTS = {item["id"]: item for item in _load(KEYWORD_FIXTURE_DIR / "documents.json")}


def test_raw_result_fixture_contains_facts_only() -> None:
    forbidden = set(CONTRACT["forbidden_raw_fact_fields"])
    case_ids: set[str] = set()
    result_ids: set[str] = set()
    for case in RAW_CASES:
        assert case["case_id"] not in case_ids
        case_ids.add(case["case_id"])
        assert [result["rank"] for result in case["results"]] == list(range(1, len(case["results"]) + 1))
        for result in case["results"]:
            assert forbidden.isdisjoint(result)
            assert result["result_id"] not in result_ids
            assert result["title"]
            assert result["url"].startswith("https://fixture.test/")
            result_ids.add(result["result_id"])


def test_every_result_has_exactly_one_valid_judgment() -> None:
    result_ids = [result["result_id"] for case in RAW_CASES for result in case["results"]]
    judgments = JUDGMENT_FIXTURE["result_judgments"]

    assert sorted(result_ids) == sorted(item["result_id"] for item in judgments)
    assert len({item["result_id"] for item in judgments}) == len(judgments)
    assert {item["relevance"] for item in judgments} <= set(CONTRACT["relevance_values"])
    assert {item["noise_reason"] for item in judgments if item["noise_reason"] is not None} <= set(
        CONTRACT["noise_reasons"]
    )
    assert all(not (item["relevance"] == "relevant" and item["noise_reason"] is not None) for item in judgments)


def test_fixture_queries_are_generated_by_stage2_plan() -> None:
    planned_by_document: dict[str, set[str]] = {}
    for document_id in {case["document_id"] for case in RAW_CASES}:
        fixture = DOCUMENTS[document_id]
        extraction = extract_core_keywords(_document(fixture))
        plan = plan_core_keyword_queries(fixture["stock_name"], extraction)
        planned_by_document[document_id] = {item.query for item in plan.queries}

    assert all(case["query"] in planned_by_document[case["document_id"]] for case in RAW_CASES)


def test_representative_metrics_match_frozen_denominator_semantics() -> None:
    evaluation = _evaluate_fixture()
    documents = {item.document_id: item for item in evaluation.documents}

    clean = documents["news_samsung_hbm_supply_01"]
    assert clean.precision_proxy == 1.0
    assert clean.reference_recall_proxy == 1.0
    assert clean.duplicate_count == 0
    assert clean.noise_count == 0

    duplicate = documents["news_hanwha_poland_contract_01"]
    assert duplicate.raw_result_count == 4
    assert duplicate.unique_result_count == 3
    assert duplicate.duplicate_count == 1
    assert duplicate.duplicate_rate == pytest.approx(1 / 4)
    assert duplicate.precision_proxy == pytest.approx(2 / 3)

    noise = documents["report_naver_ai_acronym_01"]
    assert noise.noise_count == 1
    assert noise.noise_rate == pytest.approx(1 / 3)
    assert noise.precision_proxy == pytest.approx(1 / 2)
    assert noise.reference_recall_proxy == pytest.approx(1 / 2)

    partial = documents["report_hd_shipbuilding_cycle_01"]
    assert partial.reference_recall_proxy == pytest.approx(2 / 3)

    empty = documents["report_generic_market_comment_01"]
    assert empty.raw_result_count == 0
    assert empty.duplicate_rate is None
    assert empty.noise_rate is None
    assert empty.precision_proxy is None
    assert empty.reference_recall_proxy is None


def test_query_rates_use_raw_rows_and_exclude_uncertain_from_relevance_denominator() -> None:
    evaluation = _evaluate_fixture()
    queries = {item.query: item for item in evaluation.queries}

    naver = queries["NAVER AI 반도체"]
    assert naver.result_count == 3
    assert naver.judged_count == 2
    assert naver.relevance_rate == pytest.approx(1 / 2)
    assert naver.noise_rate == pytest.approx(1 / 3)
    assert naver.duplicate_rate == 0.0


def test_evaluation_is_deterministic_and_immutable() -> None:
    first = _evaluate_fixture()
    second = _evaluate_fixture()

    assert first == second
    assert isinstance(first.queries, tuple)
    assert isinstance(first.documents, tuple)


def test_evaluator_rejects_missing_or_invalid_judgments() -> None:
    batches, judgments, references = _fixture_inputs()

    with pytest.raises(ValueError, match="exactly one judgment"):
        evaluate_query_results(batches, judgments[:-1], references)

    invalid = judgments[:-1] + (
        QueryResultJudgment(
            result_id=judgments[-1].result_id,
            relevance="relevant",
            noise_reason="off_target",
            duplicate_group=None,
            reference_evidence_id=judgments[-1].reference_evidence_id,
        ),
    )
    with pytest.raises(ValueError, match="relevant result cannot be noise"):
        evaluate_query_results(batches, invalid, references)


def _evaluate_fixture():
    return evaluate_query_results(*_fixture_inputs())


@pytest.mark.parametrize(
    "first_changes,second_changes",
    [
        ({"reference_evidence_id": None}, {"relevance": "irrelevant", "reference_evidence_id": None}),
        (
            {"relevance": "irrelevant", "reference_evidence_id": None, "noise_reason": "off_target"},
            {"relevance": "irrelevant", "reference_evidence_id": None, "noise_reason": "too_generic"},
        ),
        ({}, {"reference_evidence_id": None}),
    ],
    ids=["relevance", "noise_reason", "reference_evidence"],
)
def test_duplicate_group_requires_consistent_judgments(first_changes, second_changes) -> None:
    batches, judgments, references = _fixture_inputs()
    conflicting = tuple(
        replace(item, **first_changes) if item.result_id == "han1" else
        replace(item, **second_changes) if item.result_id == "han3" else item
        for item in judgments
    )
    with pytest.raises(ValueError, match="duplicate_group.*consistent"):
        evaluate_query_results(batches, conflicting, references)


@pytest.mark.parametrize("invalid_references", [("A", "A"), ("",), ("   ",)])
def test_reference_set_rejects_duplicate_or_empty_evidence_ids(invalid_references) -> None:
    with pytest.raises(ValueError, match="reference.*unique.*non-empty"):
        evaluate_query_results((), (), {"document": invalid_references})


def test_all_uncertain_results_have_no_precision_or_relevance_rate() -> None:
    batches, judgments, references = _fixture_inputs()
    uncertain = tuple(
        replace(item, relevance="uncertain", noise_reason=None, reference_evidence_id=None)
        for item in judgments
    )
    evaluation = evaluate_query_results(batches, uncertain, references)
    assert all(item.judged_count == 0 and item.relevance_rate is None for item in evaluation.queries)
    assert all(item.judged_unique_count == 0 and item.precision_proxy is None for item in evaluation.documents)


def _fixture_inputs():
    batches = tuple(
        QueryResultBatch(
            document_id=case["document_id"],
            query=case["query"],
            results=tuple(QueryResultFact(**result) for result in case["results"]),
        )
        for case in RAW_CASES
    )
    judgments = tuple(QueryResultJudgment(**item) for item in JUDGMENT_FIXTURE["result_judgments"])
    references = {
        item["document_id"]: tuple(item["reference_evidence_ids"])
        for item in JUDGMENT_FIXTURE["reference_sets"]
    }
    return batches, judgments, references


def _document(fixture: dict) -> CoreKeywordDocument:
    return CoreKeywordDocument(
        document_type=fixture["document_type"],
        stock_name=fixture["stock_name"],
        stock_code=fixture["stock_code"],
        title=fixture["title"],
        summary=fixture["summary"],
    )
