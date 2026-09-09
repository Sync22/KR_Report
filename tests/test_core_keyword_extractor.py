import json
from pathlib import Path

import pytest

from stock_monitor.news import CoreKeywordDocument, extract_core_keywords


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "keyword_search_expansion"


def _load(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


DOCUMENTS = _load("documents.json")
KEYWORD_GOLD = {record["document_id"]: record for record in _load("keyword_gold.json")}


@pytest.mark.parametrize("fixture", DOCUMENTS, ids=lambda item: item["id"])
def test_extract_core_keywords_matches_frozen_gold(fixture: dict) -> None:
    result = extract_core_keywords(_document(fixture))
    gold = KEYWORD_GOLD[fixture["id"]]

    assert [
        {"value": item.value, "kind": item.kind, "priority": item.priority}
        for item in result.accepted
    ] == gold["accepted"]
    assert [
        {"value": item.value, "reason": item.reason}
        for item in result.rejected
    ] == gold["rejected"]


def test_extractor_is_deterministic_and_returns_immutable_values() -> None:
    document = _document(DOCUMENTS[0])
    first = extract_core_keywords(document)
    second = extract_core_keywords(document)

    assert first == second
    assert isinstance(first.accepted, tuple)
    assert isinstance(first.rejected, tuple)


def test_max_keywords_caps_and_reprioritizes_the_result() -> None:
    result = extract_core_keywords(_document(DOCUMENTS[0]), max_keywords=2)

    assert [(item.value, item.priority) for item in result.accepted] == [
        ("HBM4", 1),
        ("엔비디아", 2),
    ]


@pytest.mark.parametrize("max_keywords", [0, 6])
def test_max_keywords_must_stay_within_frozen_contract(max_keywords: int) -> None:
    with pytest.raises(ValueError, match="max_keywords must be between 1 and 5"):
        extract_core_keywords(_document(DOCUMENTS[0]), max_keywords=max_keywords)


def test_default_result_never_exceeds_frozen_contract_limit() -> None:
    document = CoreKeywordDocument(
        document_type="news",
        stock_name="테스트종목",
        stock_code=None,
        title="HBM4 엔비디아 K9 자주포 폴란드 군비청 로카모빌리티",
        summary="미국 반도체 수출 규제와 염수 리튬, 북미 ESS 수요가 함께 언급됐다.",
    )

    assert len(extract_core_keywords(document).accepted) == 5
def test_summary_only_and_title_only_documents_are_supported() -> None:
    summary_only = next(item for item in DOCUMENTS if "summary_only_signal" in item["case_categories"])
    title_only = next(item for item in DOCUMENTS if "empty_summary" in item["case_categories"])

    assert [item.value for item in extract_core_keywords(_document(summary_only)).accepted] == [
        "염수 리튬",
        "아르헨티나 염수 리튬 상업 생산",
        "리튬 가격",
    ]
    assert [item.value for item in extract_core_keywords(_document(title_only)).accepted] == [
        "하이퍼클로바X",
        "기업용 서비스 출시",
    ]


def test_normalized_alias_is_reported_as_duplicate() -> None:
    fixture = next(item for item in DOCUMENTS if "normalization_duplicate" in item["case_categories"])
    result = extract_core_keywords(_document(fixture))

    assert result.accepted[0].value == "HBM4"
    assert ("HBM 4", "duplicate") in [(item.value, item.reason) for item in result.rejected]


def test_generic_document_does_not_force_a_keyword() -> None:
    fixture = next(item for item in DOCUMENTS if "zero_keyword" in item["case_categories"])

    assert extract_core_keywords(_document(fixture)).accepted == ()


def _document(fixture: dict) -> CoreKeywordDocument:
    return CoreKeywordDocument(
        document_type=fixture["document_type"],
        stock_name=fixture["stock_name"],
        stock_code=fixture["stock_code"],
        title=fixture["title"],
        summary=fixture["summary"],
    )
