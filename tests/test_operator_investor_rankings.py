from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from http.client import HTTPConnection
from io import BytesIO
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from stock_monitor import cli, operator_review_server as review
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.fetch.toss_openapi import TossOpenApiLabConfig
from stock_monitor.models import Report

DAY = date(2026, 10, 20)
PATH = "/api/operator-review/investor-rankings?date=2026-10-20"
ACTION = {"X-Operator-Review-Action": "investor-rankings", "Sec-Fetch-Site": "same-origin"}
ACCESS_TOKEN = "mock-private-access-token"
CLIENT_SECRET = "mock-private-client-secret"


def ranking(at=None, *, buy=(), sell=()):
    def items(rows, amount_key):
        return [
            {"rank": rank, "symbol": code, "currency": "KRW", amount_key: amount}
            for rank, code, amount in rows
        ]

    return {
        "rankedAt": at,
        "netBuyRankings": items(buy, "netBuyAmount"),
        "netSellRankings": items(sell, "netSellAmount"),
    }


def provider_result():
    return {
        "foreigner": ranking(
            "2026-10-20T01:34:28Z",
            buy=[(1, "005930", "9007199254740993"), (2, "000660", "31501"), (3, "000011", "52")],
        ),
        "institution": ranking(
            "2026-10-20T10:00:00+09:00",
            buy=[(1, "000660", "1234")],
            sell=[(2, "005930", "87898296000")],
        ),
        "individual": ranking("2026-10-19T20:17:53+09:00", sell=[(1, "005930", "120400000000")]),
    }


class FakeResponse(BytesIO):
    headers = {}


class MockTransport:
    def __init__(self, result=None, failures=()):
        self.requests = []
        self.result = provider_result() if result is None else result
        self.failures = iter(failures)

    def __call__(self, request, *, timeout):
        self.requests.append((request.get_method(), request.full_url))
        assert timeout == 5.0
        if request.get_method() == "POST":
            assert CLIENT_SECRET in request.data.decode()
            return FakeResponse(json.dumps({
                "access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 86400,
            }).encode())
        assert request.get_header("Authorization") == f"Bearer {ACCESS_TOKEN}"
        failure = next(self.failures, None)
        if failure == "timeout":
            raise TimeoutError(CLIENT_SECRET)
        if failure:
            code, retry_after = failure
            raise HTTPError(request.full_url, code, CLIENT_SECRET, {"Retry-After": retry_after}, BytesIO(
                json.dumps({"error": {"code": ACCESS_TOKEN, "message": CLIENT_SECRET}}).encode()
            ))
        return FakeResponse(json.dumps({"result": self.result}).encode())


@pytest.fixture
def stored_review(tmp_path, monkeypatch):
    db = tmp_path / "review.db"
    repository = StockMonitorRepository(db, timezone="Asia/Seoul")
    repository.initialize()
    config = SimpleNamespace(db_path=db, timezone="Asia/Seoul")
    order = ["000660", "005930", *(f"{index:06}" for index in range(3, 12))]
    rows = [
        {
            "stock_code": code, "stock_name": f"종목 {code}", "selected": index < 2,
            "why_notable": ["저장 근거"], "report_summary": {"report_count": 2},
            "stock_flow_reference": {
                "available": True, "snapshot_date": DAY.isoformat(), "amount_unit": "KRW",
                "foreign_net_buy_amount": 700,
            },
        }
        for index, code in enumerate(order)
    ]
    published = datetime(2026, 10, 20, 12)
    repository.insert_reports([
        Report(row["stock_name"], f"Report {index}", "테스트증권", published, published, DAY, row["stock_code"])
        for row in rows
        for index in range(2)
    ])
    repository.rebuild_daily_summaries(DAY)
    limits = []

    def build_snapshot(_config, _repository, *, business_date, limit):
        limits.append(limit)
        return {"selection_basis": "stored_candidate_evidence", "rows": rows[:limit] if business_date == DAY else []}

    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", build_snapshot)
    return config, limits


def build_lookup(transport, clock=lambda: 100.0):
    from stock_monitor.operator_investor_rankings import TossInvestorRankingsLookup

    return TossInvestorRankingsLookup(
        TossOpenApiLabConfig("mock-client", CLIENT_SECRET, True, "https://openapi.tossinvest.com", 5.0),
        confirm_token_reissue=True, urlopen=transport, clock=clock,
    )


def explicit_request(config, lookup, path=PATH):
    status, _, raw = review._route_operator_review_request(
        "GET", path, config, investor_rankings=lookup, investor_action=True,
    )
    assert ACCESS_TOKEN not in raw.decode() and CLIENT_SECRET not in raw.decode()
    return int(status), json.loads(raw)


def test_ranking_route_is_distinct_and_rejects_plain_navigation(stored_review):
    config, _ = stored_review
    status, _, _ = review._route_operator_review_request("GET", PATH, config)
    assert int(status) == 403


def test_rankings_cross_match_same_kst_day_in_candidate_order_and_leave_main_unchanged(stored_review):
    config, limits = stored_review
    original_db = config.db_path.read_bytes()
    main_before = review.build_operator_review_snapshot(config, DAY)
    transport = MockTransport()

    status, payload = explicit_request(config, build_lookup(transport))

    assert status == 200 and payload["state"] == "matched"
    assert payload["candidate_count"] == 10
    assert [item["stock_code"] for item in payload["matches"]] == ["000660", "005930"]
    first, second = payload["matches"]
    assert {item["investor"] for item in first["rankings"]} == {"foreigner", "institution"}
    assert first["observations"] == ["외국인·기관 모두 순매수 상위"]
    assert second["observations"] == ["외국인 순매수 · 기관 순매도"]
    assert first["report_count"] == 2 and first["brokers"] == "테스트증권(2)"
    assert first["why_notable"] == ["저장 근거"]
    assert first["stored_flow"]["foreign_net_buy_amount"] == "700"
    assert [(item["investor"], item["direction"], item["rank"], item["amount_krw"]) for item in second["rankings"]] == [
        ("foreigner", "net_buy", 1, "9007199254740993"), ("institution", "net_sell", 2, "87898296000"),
    ]
    assert payload["investors"]["individual"]["state"] == "date_mismatch"
    assert payload["investors"]["foreigner"]["ranked_at"] == "2026-10-20T10:34:28+09:00"
    assert payload["investors"]["foreigner"]["freshness"] == "provisional"
    assert payload["investors"]["institution"]["ranked_at"] == "2026-10-20T10:00:00+09:00"
    assert transport.requests == [
        ("POST", "https://openapi.tossinvest.com/oauth2/token"),
        ("GET", "https://openapi.tossinvest.com/api/v1/rankings/investor-trading?count=10"),
    ]
    assert review.build_operator_review_snapshot(config, DAY) == main_before
    assert limits == [2, 10, 2]
    assert config.db_path.read_bytes() == original_db


@pytest.mark.parametrize(("bucket", "expected"), [
    (ranking(), "no_data"),
    (ranking("2026-10-19T20:17:53+09:00", buy=[(1, "005930", "1")]), "date_mismatch"),
    (ranking("2026-10-20T17:00:00+09:00", buy=[(1, "999999", "1")]), "no_match"),
])
def test_non_match_states_remain_distinct(stored_review, bucket, expected):
    config, _ = stored_review
    transport = MockTransport({investor: bucket for investor in ("foreigner", "institution", "individual")})
    status, payload = explicit_request(config, build_lookup(transport))
    assert status == 200 and payload["state"] == expected and payload["matches"] == []
    if expected == "no_match":
        assert payload["investors"]["individual"]["freshness"] == "may_update"


@pytest.mark.parametrize(("failure", "status_code", "state"), [
    ((401, ""), 502, "toss_authentication_failed"),
    ((403, ""), 502, "toss_permission_denied"),
    ((429, "7"), 429, "toss_rate_limited"),
    ((500, ""), 502, "toss_api_error"),
    ("timeout", 502, "toss_api_error"),
])
def test_provider_failures_are_sanitized_and_do_not_retry(stored_review, failure, status_code, state):
    config, _ = stored_review
    transport = MockTransport(failures=[failure])
    now = [100.0]
    lookup = build_lookup(transport, clock=lambda: now[0])
    status, payload = explicit_request(config, lookup)
    assert (status, payload["error"]) == (status_code, state)
    assert len(transport.requests) == 2
    if status == 429:
        assert payload["retry_after_seconds"] == 7
        now[0] += 1
        assert explicit_request(config, lookup)[1]["retry_after_seconds"] == 6
        assert len(transport.requests) == 2
        now[0] += 6
        assert explicit_request(config, lookup)[0] == 200
        assert Counter(method for method, _ in transport.requests) == {"POST": 1, "GET": 2}
    elif failure == (401, ""):
        now[0] += 10
        assert explicit_request(config, lookup)[1]["error"] == "toss_authentication_failed"
        assert len(transport.requests) == 2


def test_normal_reads_and_untrusted_requests_do_not_contact_toss(stored_review):
    config, _ = stored_review
    transport = MockTransport()
    lookup = build_lookup(transport)
    with review.ThreadingHTTPServer(("127.0.0.1", 0),
                                    review._make_operator_review_handler(config, investor_rankings=lookup)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]

        def get(path, headers=None, method="GET"):
            with_http = HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                with_http.request(method, path, headers=headers or {})
                response = with_http.getresponse()
                return response.status, response.read()
            finally:
                with_http.close()

        try:
            assert get("/?date=2026-10-20")[0] == 200
            assert get("/api/operator-review?date=2026-10-20")[0] == 200
            assert get(PATH)[0] == 403
            assert get(PATH, {**ACTION, "Host": f"rebound.example:{port}"})[0] == 403
            assert get(PATH, {**ACTION, "Sec-Fetch-Site": "cross-site"})[0] == 403
            assert get(PATH, {**ACTION, "X-Forwarded-For": "203.0.113.1"})[0] == 403
            assert get(PATH, ACTION, method="POST")[0] == 405
            assert get(PATH + "&count=100", ACTION)[0] == 400
            assert get(PATH.replace("10-20", "10-19"), ACTION)[0] == 200
            assert transport.requests == []
            assert get(PATH, ACTION)[0] == 200
            assert len(transport.requests) == 2
        finally:
            server.shutdown()
            thread.join(timeout=3)



def test_read_only_route_uses_actual_candidate_builder_order(stored_review, monkeypatch):
    config, _ = stored_review
    monkeypatch.undo()
    config.holiday_overrides = ()
    repository = review._ReadOnlyStockMonitorRepository(config.db_path, timezone=config.timezone)
    snapshot = cli.build_web_view_candidate_evidence_snapshot(config, repository, business_date=DAY, limit=10)
    codes = [row["stock_code"] for row in snapshot["rows"]]
    matching_codes = codes[-3:][::-1]
    transport = MockTransport({
        "foreigner": ranking("2026-10-20T17:00:00+09:00",
                             buy=[(index, code, "100") for index, code in enumerate(matching_codes, 1)]),
        "institution": ranking(),
        "individual": ranking(),
    })
    before = config.db_path.read_bytes()
    status, payload = explicit_request(config, build_lookup(transport))

    assert status == 200
    assert [row["stock_code"] for row in payload["matches"]] == codes[-3:]
    assert config.db_path.read_bytes() == before


def test_token_expiry_requires_new_session_without_reissue(stored_review):
    config, _ = stored_review
    transport = MockTransport()
    now = [100.0]
    lookup = build_lookup(transport, clock=lambda: now[0])
    assert explicit_request(config, lookup)[0] == 200
    now[0] += 86400
    assert explicit_request(config, lookup)[1]["error"] == "toss_authentication_failed"
    assert Counter(method for method, _ in transport.requests) == {"POST": 1, "GET": 1}



def test_token_rate_limit_delays_next_explicit_attempt_without_retrying_automatically(stored_review):
    config, _ = stored_review
    transport = MockTransport()
    token_attempts = []

    def token_rate_limited_once(request, *, timeout):
        if request.get_method() == "POST":
            token_attempts.append(request.full_url)
            if len(token_attempts) == 1:
                raise HTTPError(request.full_url, 429, "", {"Retry-After": "7"}, BytesIO(b"{}"))
        return transport(request, timeout=timeout)

    now = [100.0]
    lookup = build_lookup(token_rate_limited_once, clock=lambda: now[0])
    assert explicit_request(config, lookup)[1]["retry_after_seconds"] == 7
    now[0] += 6
    assert explicit_request(config, lookup)[1]["retry_after_seconds"] == 1
    assert len(token_attempts) == 1 and transport.requests == []
    now[0] += 1
    assert explicit_request(config, lookup)[0] == 200
    assert len(token_attempts) == 2
    assert Counter(method for method, _ in transport.requests) == {"POST": 1, "GET": 1}


def test_ambiguous_token_failure_does_not_repeat_issuance(stored_review):
    config, _ = stored_review
    requests = []

    def failed_transport(request, *, timeout):
        requests.append(request.get_method())
        raise TimeoutError(CLIENT_SECRET)

    now = [100.0]
    lookup = build_lookup(failed_transport, clock=lambda: now[0])
    assert explicit_request(config, lookup)[1]["error"] == "toss_api_error"
    now[0] += 2
    assert explicit_request(config, lookup)[1]["error"] == "toss_authentication_failed"
    assert requests == ["POST"]
