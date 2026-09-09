import json
import re
from datetime import date
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "keyword_search_expansion"


def _load(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


CONTRACT = _load("contract_v1.json")
DOCUMENTS = _load("documents.json")
KEYWORD_GOLD = _load("keyword_gold.json")
QUERY_GOLD = _load("query_gold.json")


def _normalize(value: str) -> str:
    assert CONTRACT["normalization"] == {
        "casefold": True,
        "remove_whitespace": True,
        "accepted_phrase_must_exist_in_source": True,
        "duplicate_rejection_must_match_accepted": True,
    }
    return re.sub(r"\s+", "", value).casefold()


def _by_id(records: list[dict], key: str) -> dict[str, dict]:
    return {record[key]: record for record in records}


def test_fixture_document_ids_are_unique() -> None:
    ids = [document["id"] for document in DOCUMENTS]
    assert len(ids) == len(set(ids))


def test_documents_match_contract_shape() -> None:
    required = {
        "id",
        "document_type",
        "stock_name",
        "stock_code",
        "title",
        "summary",
        "source",
        "published_date",
        "case_categories",
    }
    for document in DOCUMENTS:
        assert set(document) == required
        assert document["document_type"] in CONTRACT["document_types"]
        assert document["id"].strip()
        assert document["stock_name"].strip()
        assert document["title"].strip()
        assert isinstance(document["summary"], str)
        assert document["source"] in {"fixture-news", "fixture-broker"}
        assert document["stock_code"] is None or re.fullmatch(r"\d{6}", document["stock_code"])
        assert date.fromisoformat(document["published_date"])
        assert document["case_categories"]


def test_gold_records_cover_exactly_the_fixture_documents() -> None:
    document_ids = {document["id"] for document in DOCUMENTS}
    assert {record["document_id"] for record in KEYWORD_GOLD} == document_ids
    assert {record["document_id"] for record in QUERY_GOLD} == document_ids


def test_keyword_gold_matches_declared_contract() -> None:
    documents = _by_id(DOCUMENTS, "id")
    for record in KEYWORD_GOLD:
        accepted = record["accepted"]
        rejected = record["rejected"]
        assert all(set(item) == {"value", "kind", "priority"} for item in accepted)
        assert all(set(item) == {"value", "reason"} for item in rejected)
        assert len(accepted) <= CONTRACT["limits"]["max_keywords_per_document"]
        assert [item["priority"] for item in accepted] == list(range(1, len(accepted) + 1))
        assert all(item["value"].strip() for item in accepted)
        assert all(item["kind"] in CONTRACT["keyword_kinds"] for item in accepted)
        assert all(item["value"].strip() for item in rejected)
        assert all(item["reason"] in CONTRACT["rejection_reasons"] for item in rejected)

        accepted_values = {_normalize(item["value"]) for item in accepted}
        rejected_values = {_normalize(item["value"]) for item in rejected}
        assert len(accepted_values) == len(accepted)
        overlap = accepted_values & rejected_values
        duplicate_values = {
            _normalize(item["value"]) for item in rejected if item["reason"] == "duplicate"
        }
        assert overlap == duplicate_values

        document = documents[record["document_id"]]
        assert _normalize(document["stock_name"]) not in accepted_values
        if document["stock_code"]:
            assert _normalize(document["stock_code"]) not in accepted_values
        source_text = _normalize(f'{document["title"]} {document["summary"]}')
        for item in accepted:
            assert _normalize(item["value"]) in source_text


def test_query_gold_uses_only_accepted_keywords_and_declared_strategies() -> None:
    documents = _by_id(DOCUMENTS, "id")
    keyword_gold = _by_id(KEYWORD_GOLD, "document_id")
    for record in QUERY_GOLD:
        document = documents[record["document_id"]]
        accepted = [item["value"] for item in keyword_gold[record["document_id"]]["accepted"]]
        assert record["keyword_values"] == accepted

        queries = record["expected_queries"]
        assert len(queries) <= CONTRACT["limits"]["max_queries_per_document"]
        assert [item["priority"] for item in queries] == list(range(1, len(queries) + 1))
        assert all(item["strategy"] in CONTRACT["query_strategies"] for item in queries)
        assert len({_normalize(item["query"]) for item in queries}) == len(queries)

        for item in queries:
            query = item["query"]
            assert query.split().count(document["stock_name"]) == 1
            used_keywords = [value for value in accepted if value in query]
            assert used_keywords
            if item["strategy"] == "target_plus_pair":
                assert len(used_keywords) >= 2
            assert query not in record["forbidden_queries"]


def test_zero_keyword_case_produces_no_expected_queries() -> None:
    zero_cases = [record for record in QUERY_GOLD if not record["keyword_values"]]
    assert zero_cases
    assert all(record["expected_queries"] == [] for record in zero_cases)


def test_representative_case_categories_are_present() -> None:
    assert len(DOCUMENTS) >= 12
    assert {document["document_type"] for document in DOCUMENTS} == {"news", "report"}
    assert sum(document["document_type"] == "news" for document in DOCUMENTS) >= 6
    assert sum(document["document_type"] == "report" for document in DOCUMENTS) >= 6
    present = {category for document in DOCUMENTS for category in document["case_categories"]}
    assert set(CONTRACT["required_case_categories"]) <= present
