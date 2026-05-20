import json
from datetime import datetime

from stock_monitor.fetch import naver_stock_theme


def test_fetch_stock_theme_memberships_parses_theme_items(monkeypatch) -> None:
    payload = {
        "isSuccess": True,
        "detailCode": "",
        "message": "",
        "result": {
            "sectorCode": "505",
            "sectorName": "로봇",
            "risingCount": 0,
            "unChangedCount": 2,
            "fallingCount": 0,
            "items": [
                {"id": "000150", "name": "두산"},
                {"itemCode": "012450", "name": "한화에어로스페이스"},
            ],
        },
    }

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(naver_stock_theme.request, "urlopen", lambda *_args, **_kwargs: _Response())

    result = naver_stock_theme.fetch_stock_theme_memberships(
        "505",
        fetched_at=datetime(2026, 5, 7, 9, 0, 0),
    )

    assert result.theme_code == "505"
    assert result.theme_name == "로봇"
    assert [item.stock_code for item in result.memberships] == ["000150", "012450"]
    assert result.memberships[0].theme_name == "로봇"


def test_fetch_stock_theme_memberships_caps_page_size_at_naver_limit(monkeypatch) -> None:
    seen_urls: list[str] = []
    payload = {
        "isSuccess": True,
        "result": {
            "sectorName": "로봇",
            "risingCount": 0,
            "unChangedCount": 0,
            "fallingCount": 0,
            "items": [],
        },
    }

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, **_kwargs):
        seen_urls.append(request.full_url)
        return _Response()

    monkeypatch.setattr(naver_stock_theme.request, "urlopen", fake_urlopen)

    naver_stock_theme.fetch_stock_theme_memberships("505", page_size=100)

    assert "pageSize=50" in seen_urls[0]


def test_fetch_stock_industry_memberships_parses_industry_items(monkeypatch) -> None:
    seen_urls: list[str] = []
    seen_referers: list[str] = []
    payload = {
        "isSuccess": True,
        "detailCode": "",
        "message": "",
        "result": {
            "sectorCode": "1",
            "sectorName": "반도체",
            "risingCount": 1,
            "unChangedCount": 0,
            "fallingCount": 0,
            "items": [
                {"id": "005930", "name": "삼성전자"},
            ],
        },
    }

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, **_kwargs):
        seen_urls.append(request.full_url)
        seen_referers.append(request.headers["Referer"])
        return _Response()

    monkeypatch.setattr(naver_stock_theme.request, "urlopen", fake_urlopen)

    result = naver_stock_theme.fetch_stock_industry_memberships(
        "1",
        fetched_at=datetime(2026, 5, 8, 9, 0, 0),
    )

    assert "sectorType=upjong" in seen_urls[0]
    assert seen_referers[0].endswith("/industry/1")
    assert result.industry_code == "1"
    assert result.industry_name == "반도체"
    assert result.metadata_items[0].stock_code == "005930"
    assert result.metadata_items[0].sector_code == "1"
    assert result.metadata_items[0].sector_name == "반도체"
    assert result.metadata_items[0].source == "naver_industry"


def test_fetch_stock_industry_memberships_falls_back_to_current_upjong_api(monkeypatch) -> None:
    seen_urls: list[str] = []
    payloads = {
        "info": {
            "name": "전자제품",
        },
        "stocklist": [
            {"itemcode": "066570", "itemname": "LG전자"},
            {"itemcode": "092600", "itemname": "앤씨앤"},
        ],
    }

    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, **_kwargs):
        seen_urls.append(request.full_url)
        if "front-api/domestic/sector/item/list" in request.full_url:
            raise naver_stock_theme.error.HTTPError(
                request.full_url,
                404,
                "Not Found",
                hdrs=None,
                fp=None,
            )
        if "/upjong/307/info" in request.full_url:
            return _Response(payloads["info"])
        if "/upjong/307/stocklist" in request.full_url:
            return _Response(payloads["stocklist"])
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr(naver_stock_theme.request, "urlopen", fake_urlopen)

    result = naver_stock_theme.fetch_stock_industry_memberships(
        "307",
        fetched_at=datetime(2026, 5, 15, 15, 0, 0),
    )

    assert any("/front-api/domestic/sector/item/list" in url for url in seen_urls)
    assert any("/api/domestic/market/upjong/307/info" in url for url in seen_urls)
    assert any("/api/domestic/market/upjong/307/stocklist" in url for url in seen_urls)
    assert result.industry_code == "307"
    assert result.industry_name == "전자제품"
    assert [item.stock_code for item in result.metadata_items] == ["066570", "092600"]
    assert result.metadata_items[0].stock_name == "LG전자"
    assert result.metadata_items[0].sector_name == "전자제품"
    assert result.metadata_items[0].source == "naver_industry"


def test_fetch_stock_industry_catalog_parses_current_upjong_list(monkeypatch) -> None:
    seen_urls: list[str] = []
    payload = [
        {"no": "307", "type": "upjong", "name": "전자제품", "totalCnt": "16"},
        {"no": "329", "type": "upjong", "name": "도로와철도운송", "totalCnt": "7"},
    ]

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, **_kwargs):
        seen_urls.append(request.full_url)
        return _Response()

    monkeypatch.setattr(naver_stock_theme.request, "urlopen", fake_urlopen)

    items = naver_stock_theme.fetch_stock_industry_catalog(page_size=5, max_pages=1)

    assert "api/domestic/market/upjong/list" in seen_urls[0]
    assert "pageSize=5" in seen_urls[0]
    assert [(item.industry_code, item.industry_name, item.stock_count) for item in items] == [
        ("307", "전자제품", 16),
        ("329", "도로와철도운송", 7),
    ]
