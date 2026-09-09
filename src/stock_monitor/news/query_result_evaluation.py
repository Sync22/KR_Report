from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryResultFact:
    result_id: str
    rank: int
    title: str
    snippet: str
    source: str
    url: str
    published_date: str | None


@dataclass(frozen=True)
class QueryResultBatch:
    document_id: str
    query: str
    results: tuple[QueryResultFact, ...]


@dataclass(frozen=True)
class QueryResultJudgment:
    result_id: str
    relevance: str
    noise_reason: str | None
    duplicate_group: str | None
    reference_evidence_id: str | None


@dataclass(frozen=True)
class QueryEvaluationMetrics:
    document_id: str
    query: str
    result_count: int
    judged_count: int
    relevant_count: int
    irrelevant_count: int
    uncertain_count: int
    duplicate_count: int
    noise_count: int
    relevance_rate: float | None
    duplicate_rate: float | None
    noise_rate: float | None


@dataclass(frozen=True)
class DocumentEvaluationMetrics:
    document_id: str
    query_count: int
    raw_result_count: int
    unique_result_count: int
    relevant_unique_count: int
    judged_unique_count: int
    duplicate_count: int
    noise_count: int
    duplicate_rate: float | None
    noise_rate: float | None
    precision_proxy: float | None
    reference_recall_proxy: float | None
    matched_reference_evidence_count: int
    reference_evidence_count: int


@dataclass(frozen=True)
class QueryResultEvaluation:
    queries: tuple[QueryEvaluationMetrics, ...]
    documents: tuple[DocumentEvaluationMetrics, ...]


_RELEVANCE_VALUES = frozenset({"relevant", "irrelevant", "uncertain"})
_NOISE_REASONS = frozenset({"off_target", "too_generic", "stale", "weak_context"})


def evaluate_query_results(
    batches: tuple[QueryResultBatch, ...],
    judgments: tuple[QueryResultJudgment, ...],
    reference_sets: Mapping[str, tuple[str, ...]],
) -> QueryResultEvaluation:
    for reference_set in reference_sets.values():
        if len(reference_set) != len(set(reference_set)) or any(not item.strip() for item in reference_set):
            raise ValueError("reference evidence IDs must be unique and non-empty")

    facts = [fact for batch in batches for fact in batch.results]
    fact_ids = [fact.result_id for fact in facts]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("result_id must be globally unique")

    judgment_by_id: dict[str, QueryResultJudgment] = {}
    for judgment in judgments:
        if judgment.result_id in judgment_by_id:
            raise ValueError("every result must have exactly one judgment")
        if judgment.relevance not in _RELEVANCE_VALUES:
            raise ValueError("unsupported relevance")
        if judgment.noise_reason is not None and judgment.noise_reason not in _NOISE_REASONS:
            raise ValueError("unsupported noise_reason")
        if judgment.relevance == "relevant" and judgment.noise_reason is not None:
            raise ValueError("relevant result cannot be noise")
        judgment_by_id[judgment.result_id] = judgment
    if set(fact_ids) != set(judgment_by_id):
        raise ValueError("every result must have exactly one judgment")

    document_by_result = {
        fact.result_id: batch.document_id for batch in batches for fact in batch.results
    }
    group_labels: dict[tuple[str, str], tuple[str, str | None, str | None]] = {}
    for judgment in judgments:
        document_id = document_by_result[judgment.result_id]
        references = set(reference_sets.get(document_id, ()))
        if judgment.relevance == "irrelevant" and judgment.reference_evidence_id is not None:
            raise ValueError("irrelevant result cannot reference evidence")
        if judgment.reference_evidence_id is not None and judgment.reference_evidence_id not in references:
            raise ValueError("reference_evidence_id must belong to the document reference set")
        if judgment.duplicate_group is not None:
            group_key = (document_id, judgment.duplicate_group)
            labels = (judgment.relevance, judgment.noise_reason, judgment.reference_evidence_id)
            if group_key in group_labels and group_labels[group_key] != labels:
                raise ValueError("duplicate_group judgments must be consistent within a document")
            group_labels[group_key] = labels

    query_metrics = tuple(_evaluate_batch(batch, judgment_by_id) for batch in batches)
    document_ids = sorted({batch.document_id for batch in batches} | set(reference_sets))
    document_metrics = tuple(
        _evaluate_document(
            document_id,
            tuple(batch for batch in batches if batch.document_id == document_id),
            judgment_by_id,
            reference_sets.get(document_id, ()),
        )
        for document_id in document_ids
    )
    return QueryResultEvaluation(queries=query_metrics, documents=document_metrics)


def _evaluate_batch(
    batch: QueryResultBatch,
    judgment_by_id: Mapping[str, QueryResultJudgment],
) -> QueryEvaluationMetrics:
    rows = [(fact, judgment_by_id[fact.result_id]) for fact in batch.results]
    relevant = sum(judgment.relevance == "relevant" for _, judgment in rows)
    irrelevant = sum(judgment.relevance == "irrelevant" for _, judgment in rows)
    uncertain = sum(judgment.relevance == "uncertain" for _, judgment in rows)
    judged = relevant + irrelevant
    duplicates = _duplicate_count(tuple(judgment for _, judgment in rows))
    noise = sum(judgment.noise_reason is not None for _, judgment in rows)
    total = len(rows)
    return QueryEvaluationMetrics(
        document_id=batch.document_id,
        query=batch.query,
        result_count=total,
        judged_count=judged,
        relevant_count=relevant,
        irrelevant_count=irrelevant,
        uncertain_count=uncertain,
        duplicate_count=duplicates,
        noise_count=noise,
        relevance_rate=_ratio(relevant, judged),
        duplicate_rate=_ratio(duplicates, total),
        noise_rate=_ratio(noise, total),
    )


def _evaluate_document(
    document_id: str,
    batches: tuple[QueryResultBatch, ...],
    judgment_by_id: Mapping[str, QueryResultJudgment],
    reference_set: tuple[str, ...],
) -> DocumentEvaluationMetrics:
    rows = [
        (fact, judgment_by_id[fact.result_id])
        for batch in batches
        for fact in sorted(batch.results, key=lambda item: (item.rank, item.result_id))
    ]
    unique_rows = _unique_rows(rows)
    relevant_unique = sum(judgment.relevance == "relevant" for _, judgment in unique_rows)
    judged_unique = sum(judgment.relevance != "uncertain" for _, judgment in unique_rows)
    matched_references = {
        judgment.reference_evidence_id
        for _, judgment in unique_rows
        if judgment.relevance == "relevant" and judgment.reference_evidence_id is not None
    }
    return DocumentEvaluationMetrics(
        document_id=document_id,
        query_count=len(batches),
        raw_result_count=len(rows),
        unique_result_count=len(unique_rows),
        relevant_unique_count=relevant_unique,
        judged_unique_count=judged_unique,
        duplicate_count=len(rows) - len(unique_rows),
        noise_count=sum(judgment.noise_reason is not None for _, judgment in rows),
        duplicate_rate=_ratio(len(rows) - len(unique_rows), len(rows)),
        noise_rate=_ratio(sum(judgment.noise_reason is not None for _, judgment in rows), len(rows)),
        precision_proxy=_ratio(relevant_unique, judged_unique),
        reference_recall_proxy=_ratio(len(matched_references), len(reference_set)),
        matched_reference_evidence_count=len(matched_references),
        reference_evidence_count=len(reference_set),
    )


def _unique_rows(
    rows: list[tuple[QueryResultFact, QueryResultJudgment]],
) -> list[tuple[QueryResultFact, QueryResultJudgment]]:
    seen_groups: set[str] = set()
    unique: list[tuple[QueryResultFact, QueryResultJudgment]] = []
    for row in rows:
        group = row[1].duplicate_group
        if group is not None and group in seen_groups:
            continue
        if group is not None:
            seen_groups.add(group)
        unique.append(row)
    return unique


def _duplicate_count(judgments: tuple[QueryResultJudgment, ...]) -> int:
    groups = [judgment.duplicate_group for judgment in judgments if judgment.duplicate_group is not None]
    return len(groups) - len(set(groups))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
