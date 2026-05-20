import json
from datetime import datetime
from pathlib import Path

from stock_monitor.fetch.naver_research import (
    CandidateRow,
    _extract_api_items,
    _parse_api_item,
    _parse_candidate_row,
    parse_reports_from_inspection_fixture_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_extract_api_items_prefers_nested_result_item_list() -> None:
    payload = {
        "status": "ok",
        "result": {
            "itemList": [
                {"researchId": "1", "title": "A"},
                {"researchId": "2", "title": "B"},
            ]
        },
    }

    items = _extract_api_items(payload)

    assert [item["researchId"] for item in items] == ["1", "2"]


def test_parse_api_item_uses_research_id_for_source_and_identity() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    item = {
        "itemName": "삼성전자",
        "itemCode": "005930",
        "researchId": "91999",
        "title": "업황 회복 가시화",
        "brokerName": "NH투자증권",
        "writeDate": "2026-04-24",
        "opinion": "Buy",
        "goalPrice": "92000",
        "endUrl": "https://m.stock.naver.com/research/company/91999",
    }

    report = _parse_api_item(item, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.source_id == "91999"
    assert report.source_url == "https://stock.naver.com/research/company/91999"
    assert report.target_price_value == 92000
    assert report.identity_key == report.with_identity().identity_key


def test_parse_api_item_canonicalizes_decorated_research_id_and_mobile_url() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    item = {
        "itemName": "삼성전자",
        "itemCode": "005930",
        "researchId": "research-91999",
        "title": "업황 회복 가시화",
        "brokerName": "NH투자증권",
        "writeDate": "2026-04-24",
        "opinion": "Buy",
        "goalPrice": "92000",
        "endUrl": "https://m.stock.naver.com/research/company/91999?foo=bar",
    }

    report = _parse_api_item(item, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.source_id == "91999"
    assert report.source_url == "https://stock.naver.com/research/company/91999"


def test_parse_api_item_derives_source_id_from_end_url_when_research_id_missing() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    item = {
        "itemName": "삼성전자",
        "itemCode": "005930",
        "title": "업황 회복 가시화",
        "brokerName": "NH투자증권",
        "writeDate": "2026-04-24",
        "opinion": "Buy",
        "goalPrice": "92000",
        "endUrl": "https://m.stock.naver.com/research/company/91999?foo=bar",
    }

    report = _parse_api_item(item, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.source_id == "91999"
    assert report.source_url == "https://stock.naver.com/research/company/91999"


def test_parse_api_item_derives_business_date_with_holiday_override() -> None:
    collected_at = datetime(2026, 5, 6, 8, 0, 0)
    item = {
        "itemName": "삼성전자",
        "itemCode": "005930",
        "researchId": "92000",
        "title": "휴장일 리포트",
        "brokerName": "NH투자증권",
        "writeDate": "2026-05-05",
        "opinion": "Buy",
        "goalPrice": "92000",
    }

    report = _parse_api_item(item, collected_at, "Asia/Seoul", {datetime(2026, 5, 5).date()})

    assert report is not None
    assert report.business_date.isoformat() == "2026-05-04"


def test_parse_candidate_row_handles_standard_dom_fallback_row() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    row = CandidateRow(
        selector="tr",
        text="삼성전자 (005930) 업황 회복 가시화 목표주가 92,000원 Buy NH투자증권 2026.04.24",
        href="https://m.stock.naver.com/research/company/91999",
        cells=("삼성전자", "업황 회복 가시화", "92,000", "Buy", "NH투자증권", "2026.04.24"),
    )

    report = _parse_candidate_row(row, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.stock_name == "삼성전자"
    assert report.stock_code == "005930"
    assert report.title == "업황 회복 가시화"
    assert report.broker_name == "NH투자증권"
    assert report.published_at.date().isoformat() == "2026-04-24"
    assert report.target_price_value == 92000
    assert report.opinion_normalized == "buy"
    assert report.source_url == "https://stock.naver.com/research/company/91999"


def test_parse_candidate_row_canonicalizes_mobile_url_with_query_params() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    row = CandidateRow(
        selector="tr",
        text="삼성전자 (005930) 업황 회복 가시화 목표주가 92,000원 Buy NH투자증권 2026.04.24",
        href="https://m.stock.naver.com/research/company/91999?foo=bar",
        cells=("삼성전자", "업황 회복 가시화", "92,000", "Buy", "NH투자증권", "2026.04.24"),
    )

    report = _parse_candidate_row(row, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.source_id == "91999"
    assert report.source_url == "https://stock.naver.com/research/company/91999"


def test_parse_candidate_row_handles_shifted_date_first_dom_row() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    row = CandidateRow(
        selector="li",
        text="2026-04-24 삼성전자 업황 회복 가시화 NH투자증권 목표주가 92,000원 매수",
        href="https://stock.naver.com/research/company/92000",
        cells=("2026-04-24", "삼성전자", "업황 회복 가시화", "NH투자증권"),
    )

    report = _parse_candidate_row(row, collected_at, "Asia/Seoul")

    assert report is not None
    assert report.stock_name == "삼성전자"
    assert report.stock_code is None
    assert report.title == "업황 회복 가시화"
    assert report.broker_name == "NH투자증권"
    assert report.target_price_value == 92000
    assert report.opinion_normalized == "buy"


def test_parse_candidate_row_returns_none_when_required_fields_are_missing() -> None:
    collected_at = datetime(2026, 4, 25, 8, 0, 0)
    row = CandidateRow(
        selector="tr",
        text="삼성전자 업황 회복 가시화 목표주가 N/A",
        href=None,
        cells=("삼성전자", "업황 회복 가시화"),
    )

    assert _parse_candidate_row(row, collected_at, "Asia/Seoul") is None


def test_parse_reports_from_inspection_fixture_payload_prefers_api_items_over_dom_rows() -> None:
    payload = {
        "collected_at": "2026-04-25T08:00:00+09:00",
        "timezone": "Asia/Seoul",
        "api_items": [
            {
                "itemName": "삼성전자",
                "itemCode": "005930",
                "researchId": "research-91999",
                "title": "업황 회복 가시화",
                "brokerName": "NH투자증권",
                "writeDate": "2026-04-24",
                "opinion": "Buy",
                "goalPrice": "92000",
                "endUrl": "https://m.stock.naver.com/research/company/91999?foo=bar",
            }
        ],
        "candidate_rows": [
            {
                "selector": "tr",
                "href": "https://m.stock.naver.com/research/company/91999?foo=bar",
                "cells": ["삼성전자", "DOM fallback duplicate", "92,000", "Buy", "NH투자증권", "2026.04.24"],
                "text": "삼성전자 (005930) DOM fallback duplicate 목표주가 92,000원 Buy NH투자증권 2026.04.24",
            }
        ],
    }

    reports = parse_reports_from_inspection_fixture_payload(payload)

    assert len(reports) == 1
    assert reports[0].source_id == "91999"
    assert reports[0].title == "업황 회복 가시화"


def test_saved_2026_05_14_live_fixture_parses_api_reports() -> None:
    fixture_path = PROJECT_ROOT / "data" / "naver_fixtures" / "naver_research_2026-05-14.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    reports = parse_reports_from_inspection_fixture_payload(payload)

    assert len(reports) == 20
    assert reports[0].source_id == "92967"
    assert reports[0].stock_code == "035720"


def test_saved_2026_05_15_live_fixture_parses_api_reports() -> None:
    fixture_path = PROJECT_ROOT / "data" / "naver_fixtures" / "naver_research_2026-05-15.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    reports = parse_reports_from_inspection_fixture_payload(payload)

    assert len(reports) == 20
    assert reports[0].source_id == "93018"
    assert reports[0].stock_code == "138040"
