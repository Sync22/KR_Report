"""Offline capture validation; metadata cannot authenticate provider origin.

Readiness reports label completeness, not label correctness or search quality.
Call validate_captured_query_results with the actual Stage 2 plans first, then
use the Stage 3 evaluator to validate judgments and the reference universe.
No provider data is fetched, normalized, or persisted here.
"""

from collections.abc import Mapping
from dataclasses import dataclass, asdict
from datetime import date, datetime

from .query_result_evaluation import QueryResultBatch, QueryResultFact, QueryResultJudgment


@dataclass(frozen=True)
class CapturedQueryResult:
    result_id: str
    rank: int
    title: str
    snippet: str
    source: str
    url: str
    published_date: str | None


@dataclass(frozen=True)
class CapturedQueryBatch:
    capture_id: str
    captured_at: str
    provider: str
    document_id: str
    query: str
    results: tuple[CapturedQueryResult, ...]


@dataclass(frozen=True)
class CaptureEvidenceStatus:
    capture_count: int
    result_count: int
    judged_result_count: int
    unjudged_result_count: int
    evaluable_document_count: int
    status: str


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_structure(captures: tuple[CapturedQueryBatch, ...]) -> None:
    capture_ids: set[str] = set()
    result_ids: set[str] = set()
    for capture in captures:
        for name in ("capture_id", "provider", "document_id", "query", "captured_at"):
            _nonempty(getattr(capture, name), name)
        if capture.capture_id in capture_ids:
            raise ValueError("capture_id must be globally unique")
        capture_ids.add(capture.capture_id)
        timestamp = datetime.fromisoformat(capture.captured_at)
        if timestamp.utcoffset() is None:
            raise ValueError("captured_at must include timezone")
        for rank, result in enumerate(capture.results, start=1):
            for name in ("result_id", "title", "source", "url"):
                _nonempty(getattr(result, name), name)
            if result.result_id in result_ids:
                raise ValueError("result_id must be globally unique")
            result_ids.add(result.result_id)
            if type(result.rank) is not int or result.rank != rank:
                raise ValueError("ranks must be the dense sequence 1..N in capture order")
            if not isinstance(result.snippet, str):
                raise ValueError("snippet must be a string")
            if result.published_date is not None:
                if not isinstance(result.published_date, str) or date.fromisoformat(result.published_date).isoformat() != result.published_date:
                    raise ValueError("published_date must be YYYY-MM-DD or null")


def validate_captured_query_results(
    captures: tuple[CapturedQueryBatch, ...],
    *,
    planned_queries: Mapping[str, tuple[str, ...]],
) -> None:
    """Validate raw metadata and exact membership in caller-supplied Stage 2 plans."""
    _validate_structure(captures)
    for capture in captures:
        if capture.document_id not in planned_queries:
            raise ValueError("unknown document_id")
        if capture.query not in planned_queries[capture.document_id]:
            raise ValueError("query must belong to the document Stage 2 plan")


def summarize_capture_evidence(
    captures: tuple[CapturedQueryBatch, ...],
    judgments: tuple[QueryResultJudgment, ...],
) -> CaptureEvidenceStatus:
    """Count labels, not quality. Empty captured results need no labels.

The caller must validate query membership; the evaluator remains authoritative
for relevance, duplicate-group consistency, and reference-set validity.
"""
    _validate_structure(captures)
    result_ids = {result.result_id for capture in captures for result in capture.results}
    judged_ids = {judgment.result_id for judgment in judgments}
    if len(judged_ids) != len(judgments):
        raise ValueError("duplicate judgment result_id")
    if not judged_ids <= result_ids:
        raise ValueError("judgment result_id is absent from captures")
    by_document: dict[str, set[str]] = {}
    for capture in captures:
        by_document.setdefault(capture.document_id, set()).update(result.result_id for result in capture.results)
    if not captures:
        status = "no_capture"
    elif judged_ids == result_ids:
        status = "capture_evaluable"
    elif not judged_ids:
        status = "capture_unjudged"
    else:
        status = "capture_partially_judged"
    return CaptureEvidenceStatus(
        capture_count=len(captures), result_count=len(result_ids),
        judged_result_count=len(judged_ids), unjudged_result_count=len(result_ids - judged_ids),
        evaluable_document_count=sum(ids <= judged_ids for ids in by_document.values()),
        status=status,
    )


def to_evaluation_batches(captures: tuple[CapturedQueryBatch, ...]) -> tuple[QueryResultBatch, ...]:
    """Lossless result-field adapter; retain captures separately for provenance.

Validate membership and check label completeness before evaluating. This
adapter does not certify readiness or calculate metrics.
"""
    _validate_structure(captures)
    return tuple(QueryResultBatch(
        document_id=capture.document_id, query=capture.query,
        results=tuple(QueryResultFact(**asdict(result)) for result in capture.results),
    ) for capture in captures)
