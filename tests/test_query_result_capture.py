"""Inline examples are synthetic controls, never measured provider evidence."""

import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from stock_monitor.news import CoreKeywordDocument, extract_core_keywords, plan_core_keyword_queries
from stock_monitor.news.query_result_evaluation import QueryResultJudgment, evaluate_query_results
from stock_monitor.news.query_result_capture import (
    CapturedQueryBatch, CapturedQueryResult, summarize_capture_evidence,
    to_evaluation_batches, validate_captured_query_results,
)

ROOT = Path(__file__).parent / "fixtures"
CONTRACT = json.loads((ROOT / "query_result_capture/capture_contract_v1.json").read_text(encoding="utf-8"))


def _plans():
    documents = json.loads((ROOT / "keyword_search_expansion/documents.json").read_text(encoding="utf-8"))
    return {
        item["id"]: tuple(q.query for q in plan_core_keyword_queries(
            item["stock_name"], extract_core_keywords(CoreKeywordDocument(**{
                key: item[key] for key in ("document_type", "stock_name", "stock_code", "title", "summary")
            }))
        ).queries) for item in documents
    }


def _capture():
    document_id = "news_samsung_hbm_supply_01"
    return CapturedQueryBatch(
        "synthetic-control", "2026-09-08T10:15:00+09:00", "synthetic-test-provider",
        document_id, _plans()[document_id][0],
        (CapturedQueryResult("r1", 1, "  HBM4 제목  ", "본문\n유지", "출처", "https://example.org/a?q=1", "2026-09-08"),
         CapturedQueryResult("r2", 2, "두 번째 제목", "", "출처", "https://example.org/b", None)),
    )


def _judgments():
    return tuple(QueryResultJudgment(f"r{i}", "relevant", None, None, None) for i in (1, 2))


def test_contract_and_models_keep_raw_facts_separate():
    for model, key in ((CapturedQueryBatch, "required_fields"), (CapturedQueryResult, "result_required_fields")):
        names = {field.name for field in fields(model)}
        assert names == set(CONTRACT[key])
        assert names.isdisjoint(CONTRACT["forbidden_fields"])
    with pytest.raises(TypeError):
        CapturedQueryResult(**{**vars(_capture().results[0]), "score": 1})


def test_capture_links_to_real_stage2_plan_without_rewriting():
    capture = _capture()
    before = repr(capture)
    validate_captured_query_results((capture,), planned_queries=_plans())
    assert repr(capture) == before


@pytest.mark.parametrize("changes", [
    {"captured_at": "2026-09-08T10:00:00"}, {"captured_at": "bad"},
    {"provider": " "}, {"capture_id": ""}, {"query": "not planned"}, {"document_id": "unknown"},
])
def test_invalid_capture_provenance_or_query_is_rejected(changes):
    with pytest.raises(ValueError):
        validate_captured_query_results((replace(_capture(), **changes),), planned_queries=_plans())


@pytest.mark.parametrize("changes", [
    {"rank": 0}, {"rank": True}, {"rank": 2}, {"result_id": ""},
    {"title": " "}, {"source": ""}, {"url": ""}, {"snippet": None},
    {"published_date": "2026-02-30"}, {"published_date": "20260908"},
])
def test_invalid_raw_result_is_rejected(changes):
    capture = _capture()
    with pytest.raises(ValueError):
        validate_captured_query_results((replace(capture, results=(replace(capture.results[0], **changes),)),), planned_queries=_plans())


def test_capture_and_result_ids_are_globally_unique():
    capture = _capture()
    with pytest.raises(ValueError, match="capture_id"):
        validate_captured_query_results((capture, capture), planned_queries=_plans())
    with pytest.raises(ValueError, match="result_id"):
        validate_captured_query_results((capture, replace(capture, capture_id="second")), planned_queries=_plans())


@pytest.mark.parametrize("count,status", [(0, "capture_unjudged"), (1, "capture_partially_judged"), (2, "capture_evaluable")])
def test_label_completeness_status(count, status):
    summary = summarize_capture_evidence((_capture(),), _judgments()[:count])
    assert summary.status == status
    assert summary.capture_count == 1 and summary.result_count == 2
    assert summary.judged_result_count == count and summary.unjudged_result_count == 2-count
    assert summary.evaluable_document_count == int(count == 2)


def test_no_capture_is_not_zero_quality_and_empty_capture_is_distinct():
    missing = summarize_capture_evidence((), ())
    assert missing.status == "no_capture" and missing.evaluable_document_count == 0
    empty = summarize_capture_evidence((replace(_capture(), results=()),), ())
    assert empty.status == CONTRACT["empty_capture_status"]
    assert empty.evaluable_document_count == 1 and empty.result_count == 0


def test_duplicate_and_orphan_judgments_are_rejected():
    for judgments in ((_judgments()[0],)*2, (replace(_judgments()[0], result_id="orphan"),)):
        with pytest.raises(ValueError):
            summarize_capture_evidence((_capture(),), judgments)


def test_adapter_preserves_facts_and_connects_to_stage3():
    capture = _capture()
    validate_captured_query_results((capture,), planned_queries=_plans())
    assert summarize_capture_evidence((capture,), _judgments()).status == "capture_evaluable"
    batches = to_evaluation_batches((capture,))
    assert vars(batches[0].results[0]) == vars(capture.results[0])
    assert batches[0].query == capture.query
    assert evaluate_query_results(batches, _judgments(), {}).documents[0].raw_result_count == 2
