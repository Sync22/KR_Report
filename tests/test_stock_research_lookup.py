from __future__ import annotations

import json
from datetime import date

from stock_monitor.fetch import naver_stock_research


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_stock_research_entries_filters_to_recent_lookback(monkeypatch) -> None:
    payload = [
        {
            "nid": "91703",
            "itemcode": "017670",
            "itemname": "SK텔레콤",
            "brokerName": "유안타증권",
            "title": "반영한다고 했제",
            "goalPrice": "118000",
            "opinion": "Buy",
            "writeDate": "2026-04-20",
        },
        {
            "nid": "91000",
            "itemcode": "017670",
            "itemname": "SK텔레콤",
            "brokerName": "테스트증권",
            "title": "오래된 리포트",
            "goalPrice": "70000",
            "opinion": "Hold",
            "writeDate": "2026-03-10",
        },
    ]

    def fake_urlopen(_request, timeout):  # noqa: ARG001
        return _FakeResponse(payload)

    monkeypatch.setattr(naver_stock_research.request, "urlopen", fake_urlopen)

    result = naver_stock_research.fetch_stock_research_entries(
        "017670",
        as_of_date=date(2026, 4, 25),
        lookback_days=15,
        page_size=20,
        max_pages=2,
    )

    assert result.stock_name == "SK텔레콤"
    assert len(result.entries) == 1
    assert result.entries[0].source_id == "91703"
    assert result.entries[0].source_url.endswith("/017670/research/91703")
