from __future__ import annotations

import json

from stock_monitor.fetch import naver_stock_search


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_stock_code_candidates_filters_to_stock_category(monkeypatch) -> None:
    payload = {
        "result": {
            "items": [
                {
                    "code": "017670",
                    "name": "SK텔레콤",
                    "typeName": "코스피",
                    "url": "/domestic/stock/017670/total",
                    "category": "stock",
                },
                {
                    "code": "SKY",
                    "name": "스카이 프로토콜",
                    "typeName": "업비트",
                    "url": "/crypto/UPBIT/SKY-R2",
                    "category": "coin",
                },
            ]
        }
    }

    def fake_urlopen(_request, timeout):  # noqa: ARG001
        return _FakeResponse(payload)

    monkeypatch.setattr(naver_stock_search.request, "urlopen", fake_urlopen)

    result = naver_stock_search.fetch_stock_code_candidates("SK")

    assert len(result) == 1
    assert result[0].stock_code == "017670"
    assert result[0].stock_name == "SK텔레콤"


def test_fetch_stock_code_candidates_encodes_korean_query_in_utf8(monkeypatch) -> None:
    payload = {"result": {"items": []}}
    captured_url: dict[str, str] = {}

    def fake_urlopen(req, timeout):  # noqa: ARG001
        captured_url["url"] = req.full_url
        return _FakeResponse(payload)

    monkeypatch.setattr(naver_stock_search.request, "urlopen", fake_urlopen)

    naver_stock_search.fetch_stock_code_candidates("로킷헬스케어")

    assert (
        "query=%EB%A1%9C%ED%82%B7%ED%97%AC%EC%8A%A4%EC%BC%80%EC%96%B4"
        in captured_url["url"]
    )
