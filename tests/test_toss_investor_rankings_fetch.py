import json
from datetime import datetime

import pytest

from stock_monitor.fetch.toss_openapi import (
    TOSS_OPENAPI_BASE_URL,
    TossInvestorRanking,
    TossInvestorRankingItem,
    TossOpenApiSafetyError,
    fetch_toss_investor_rankings,
    resolve_toss_market_context_endpoint,
    resolve_toss_readonly_endpoint,
)


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps({"result": payload}).encode("utf-8")
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]


def test_fetch_toss_investor_rankings_parses_official_snapshot_and_deduplicates():
    calls = []
    payload = {
        "foreigner": {
            "rankedAt": "2026-10-20T15:41:19+09:00",
            "netBuyRankings": [
                {"rank": 3, "symbol": "005930", "currency": "KRW", "netBuyAmount": "100"},
                {"rank": 2, "symbol": "0167A0", "currency": "KRW", "netBuyAmount": "43100000000"},
                {"rank": 1, "symbol": "005930", "currency": "KRW", "netBuyAmount": "386487682000"},
            ],
            "netSellRankings": [
                {"rank": 1, "symbol": "000660", "currency": "KRW", "netSellAmount": "391201805000"},
            ],
        },
        "institution": {"rankedAt": None, "netBuyRankings": [], "netSellRankings": []},
        "individual": {
            "rankedAt": "2026-10-19T20:17:53+09:00",
            "netBuyRankings": [
                {"rank": 1, "symbol": "005930", "currency": "KRW", "netBuyAmount": "189300000000"},
            ],
            "netSellRankings": [],
        },
    }

    def urlopen(http_request, *, timeout):
        calls.append((http_request, timeout))
        return FakeResponse(payload)

    result = fetch_toss_investor_rankings(
        base_url=TOSS_OPENAPI_BASE_URL,
        access_token="test-token",
        timeout_seconds=12,
        live_enabled=True,
        urlopen=urlopen,
    )

    request, timeout = calls[0]
    assert request.method == "GET"
    assert request.full_url == f"{TOSS_OPENAPI_BASE_URL}/api/v1/rankings/investor-trading?count=10"
    assert request.get_header("Authorization") == "Bearer test-token"
    assert timeout == 12
    assert result == {
        "foreigner": TossInvestorRanking(
            ranked_at=datetime.fromisoformat("2026-10-20T15:41:19+09:00"),
            net_buy=(
                TossInvestorRankingItem(rank=1, symbol="005930", amount_krw="386487682000"),
                TossInvestorRankingItem(rank=2, symbol="0167A0", amount_krw="43100000000"),
            ),
            net_sell=(TossInvestorRankingItem(rank=1, symbol="000660", amount_krw="391201805000"),),
        ),
        "institution": TossInvestorRanking(ranked_at=None, net_buy=(), net_sell=()),
        "individual": TossInvestorRanking(
            ranked_at=datetime.fromisoformat("2026-10-19T20:17:53+09:00"),
            net_buy=(TossInvestorRankingItem(rank=1, symbol="005930", amount_krw="189300000000"),),
            net_sell=(),
        ),
    }


@pytest.mark.parametrize(
    "item",
    [
        {"rank": True, "symbol": "005930", "currency": "KRW", "netBuyAmount": "1"},
        {"rank": 1, "symbol": "005930", "currency": "USD", "netBuyAmount": "1"},
        {"rank": 1, "symbol": "삼성전자", "currency": "KRW", "netBuyAmount": "1"},
        {"rank": 1, "symbol": "005930", "currency": "KRW", "netBuyAmount": 1},
        {"rank": 1, "symbol": "005930", "currency": "KRW", "netBuyAmount": "0"},
    ],
)
def test_fetch_toss_investor_rankings_rejects_invalid_ranking_items(item):
    payload = {
        "foreigner": {"rankedAt": "2026-10-20T15:41:19+09:00", "netBuyRankings": [item], "netSellRankings": []},
        "institution": {"rankedAt": None, "netBuyRankings": [], "netSellRankings": []},
        "individual": {"rankedAt": None, "netBuyRankings": [], "netSellRankings": []},
    }

    with pytest.raises(RuntimeError, match="unexpected shape"):
        fetch_toss_investor_rankings(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="test-token",
            timeout_seconds=12,
            live_enabled=True,
            urlopen=lambda *_args, **_kwargs: FakeResponse(payload),
        )


def test_fetch_toss_investor_rankings_empty_result_marks_every_bucket_unavailable():
    result = fetch_toss_investor_rankings(
        base_url=TOSS_OPENAPI_BASE_URL,
        access_token="test-token",
        timeout_seconds=12,
        live_enabled=True,
        urlopen=lambda *_args, **_kwargs: FakeResponse({}),
    )

    assert result == {
        investor: TossInvestorRanking(ranked_at=None, net_buy=(), net_sell=())
        for investor in ("foreigner", "institution", "individual")
    }


def test_fetch_toss_investor_rankings_requires_live_enablement_before_request():
    with pytest.raises(TossOpenApiSafetyError, match="explicit live enablement"):
        fetch_toss_investor_rankings(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="test-token",
            timeout_seconds=12,
            urlopen=lambda *_args, **_kwargs: pytest.fail("request must be blocked"),
        )


def test_investor_rankings_are_excluded_from_generic_endpoint_selectors():
    with pytest.raises(TossOpenApiSafetyError):
        resolve_toss_readonly_endpoint("investor-trading-rankings")
    with pytest.raises(TossOpenApiSafetyError):
        resolve_toss_market_context_endpoint("investor-trading-rankings")
