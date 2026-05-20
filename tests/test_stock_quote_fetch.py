from __future__ import annotations

import json
from datetime import datetime

from stock_monitor.fetch import naver_stock_quote


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_stock_quote_snapshot_parses_price_and_trade_time(monkeypatch) -> None:
    payload = {
        "itemcode": "005930",
        "itemname": "삼성전자",
        "upjongCode": "27",
        "upJongName": "반도체와반도체장비",
        "marketStatus": "CLOSE",
        "nowPrice": "219500",
        "prevClosePrice": "224500",
        "prevChangePrice": "-5000",
        "prevChangeRate": "-2.23",
        "tradeAmount": "10234426000",
        "tradeVolume": "171736",
        "tradeTime": "20260424161020",
    }

    def fake_urlopen(_request, timeout):  # noqa: ARG001
        return _FakeResponse(payload)

    monkeypatch.setattr(naver_stock_quote.request, "urlopen", fake_urlopen)

    snapshot = naver_stock_quote.fetch_stock_quote_snapshot("005930")

    assert snapshot.stock_code == "005930"
    assert snapshot.stock_name == "삼성전자"
    assert snapshot.sector_code == "27"
    assert snapshot.sector_name == "반도체와반도체장비"
    assert snapshot.current_price == 219_500
    assert snapshot.prev_close_price == 224_500
    assert snapshot.prev_change_price == -5_000
    assert snapshot.prev_change_rate == -2.23
    assert snapshot.trade_amount == 10_234_426_000
    assert snapshot.trade_volume == 171_736
    assert snapshot.market_status == "CLOSE"
    assert snapshot.trade_time == datetime(2026, 4, 24, 16, 10, 20)


def test_fetch_naver_market_top_stocks_parses_price_top_rows(monkeypatch) -> None:
    payload = {
        "stockListSortType": "PRICE_TOP",
        "stockListCategoryType": "KOSPI",
        "stocks": [
            {
                "itemCode": "005930",
                "stockName": "삼성전자",
                "stockEndType": "stock",
                "closePriceRaw": "273250",
                "compareToPreviousClosePriceRaw": "-1500",
                "fluctuationsRatio": "-0.54",
                "accumulatedTradingVolumeRaw": "25550000",
                "accumulatedTradingValueRaw": "6972656000000",
                "marketStatus": "OPEN",
                "localTradedAt": "2026-05-20 12:41:03",
            },
            {
                "itemCode": "122630",
                "stockName": "KODEX 레버리지",
                "stockEndType": "etf",
                "closePriceRaw": "12345",
                "fluctuationsRatio": "-3.06",
                "accumulatedTradingVolumeRaw": "111",
                "accumulatedTradingValueRaw": "2702288000000",
                "marketStatus": "OPEN",
                "localTradedAt": "2026-05-20 12:41:03",
            },
        ],
    }

    def fake_urlopen(http_request, timeout):  # noqa: ARG001
        assert "priceTop/KOSPI" in http_request.full_url
        return _FakeResponse(payload)

    monkeypatch.setattr(naver_stock_quote.request, "urlopen", fake_urlopen)

    rows = naver_stock_quote.fetch_market_top_stocks("KOSPI", page=1, page_size=20)

    assert rows[0].market == "KOSPI"
    assert rows[0].sort_type == "PRICE_TOP"
    assert rows[0].stock_code == "005930"
    assert rows[0].stock_name == "삼성전자"
    assert rows[0].stock_end_type == "stock"
    assert rows[0].current_price == 273_250
    assert rows[0].change_price == -1_500
    assert rows[0].change_percent == -0.54
    assert rows[0].trade_volume == 25_550_000
    assert rows[0].trade_amount == 6_972_656_000_000
    assert rows[0].market_status == "OPEN"
    assert rows[0].trade_time == datetime(2026, 5, 20, 12, 41, 3)
