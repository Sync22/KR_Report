from datetime import date, datetime
from urllib import error

import pytest

from stock_monitor.fetch.krx_api import (
    KrxDataMarketAuthError,
    KrxDataMarketDryRunResult,
    KrxDryRunResult,
    build_krx_data_market_result_from_payload,
    fetch_krx_data_market_endpoint,
    fetch_krx_endpoint,
    parse_investor_net_buy_top_daily,
    parse_krx_stock_metadata,
    parse_market_index_daily,
    parse_market_investor_flow_daily,
    parse_stock_market_daily,
    parse_stock_investor_flow_daily,
    resolve_krx_data_market_endpoint,
    resolve_krx_endpoints,
)


def test_resolve_krx_endpoints_supports_single_and_all() -> None:
    single = resolve_krx_endpoints("etf-daily")
    all_endpoints = resolve_krx_endpoints("all")

    assert single[0].label == "ETF 일별매매정보"
    assert len(all_endpoints) == 8


def test_resolve_krx_endpoints_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="Unknown KRX endpoint"):
        resolve_krx_endpoints("missing")


def test_build_krx_data_market_result_from_payload_accepts_saved_output() -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-stock-period")

    result = build_krx_data_market_result_from_payload(
        endpoint=endpoint,
        params={"strtDd": "20260508"},
        payload={"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVAL": "1,000"}]},
    )

    assert result.endpoint.key == "investor-flow-stock-period"
    assert result.row_count == 1
    assert result.field_keys == ("INVST_TP_NM", "NETBID_TRDVAL")
    assert result.first_row == {"INVST_TP_NM": "외국인", "NETBID_TRDVAL": "1,000"}


def test_fetch_krx_endpoint_posts_auth_header_and_json_body(monkeypatch) -> None:
    endpoint = resolve_krx_endpoints("stock-kospi-daily")[0]
    seen: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"OutBlock_1":[{"BAS_DD":"20260507","ISU_CD":"005930","ISU_NM":"Samsung"}]}'
            )

    def fake_urlopen(http_request, timeout: float):  # noqa: ANN001
        seen["url"] = http_request.full_url
        seen["method"] = http_request.get_method()
        seen["headers"] = dict(http_request.header_items())
        seen["body"] = http_request.data
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.urlopen", fake_urlopen)

    result = fetch_krx_endpoint(
        base_url="https://data-dbg.krx.co.kr",
        auth_key="secret",
        endpoint=endpoint,
        business_date=date(2026, 5, 7),
        timeout_seconds=12,
    )

    assert seen["url"] == "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
    assert seen["method"] == "POST"
    assert dict(seen["headers"])["Auth_key"] == "secret"
    assert seen["body"] == b'{"basDd": "20260507"}'
    assert seen["timeout"] == 12
    assert result.row_count == 1
    assert result.field_keys == ("BAS_DD", "ISU_CD", "ISU_NM")
    assert result.rows[0]["ISU_CD"] == "005930"


def test_fetch_krx_endpoint_wraps_network_errors(monkeypatch) -> None:
    endpoint = resolve_krx_endpoints("etf-daily")[0]

    def fake_urlopen(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise error.URLError("boom")

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Failed to fetch KRX endpoint etf-daily"):
        fetch_krx_endpoint(
            base_url="https://data-dbg.krx.co.kr",
            auth_key="secret",
            endpoint=endpoint,
            business_date=date(2026, 5, 7),
            timeout_seconds=12,
        )


def test_fetch_krx_data_market_endpoint_posts_form_bld_and_params(monkeypatch) -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-stock-period")
    seen: dict[str, object] = {}

    class FakeResponse:
        def __init__(self, body: bytes = b"{}") -> None:
            self.body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    class FakeOpener:
        def open(self, http_request, timeout: float):  # noqa: ANN001
            seen.setdefault("urls", []).append(http_request.full_url)
            seen["method"] = http_request.get_method()
            seen["headers"] = dict(http_request.header_items())
            seen["timeout"] = timeout
            if http_request.data is not None:
                seen["body"] = http_request.data.decode("utf-8")
                return FakeResponse(
                    b'{"output":[{"INVST_TP_NM":"\xea\xb0\x9c\xec\x9d\xb8","NETBID_TRDVOL":"1,000"}]}'
                )
            return FakeResponse()

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.build_opener", lambda *_args: FakeOpener())

    result = fetch_krx_data_market_endpoint(
        base_url="https://data.krx.co.kr",
        endpoint=endpoint,
        params={
            "strtDd": "20260508",
            "endDd": "20260508",
            "isuCd": "KR7005930003",
            "inqTpCd": "1",
            "trdVolVal": "1",
            "askBid": "1",
        },
        timeout_seconds=12,
    )

    assert seen["urls"] == [
        "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd",
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
    ]
    assert seen["method"] == "POST"
    assert "bld=dbms%2FMDC%2FSTAT%2Fstandard%2FMDCSTAT02301" in str(seen["body"])
    assert "isuCd=KR7005930003" in str(seen["body"])
    assert seen["timeout"] == 12
    assert result.row_count == 1
    assert result.field_keys == ("INVST_TP_NM", "NETBID_TRDVOL")
    assert result.rows[0]["INVST_TP_NM"] == "개인"


def test_fetch_krx_data_market_endpoint_logs_in_before_data_post(monkeypatch) -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-market-period")
    seen_urls: list[str] = []
    seen_bodies: list[str] = []

    class FakeResponse:
        def __init__(self, body: bytes = b"{}") -> None:
            self.body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    class FakeOpener:
        def open(self, http_request, timeout: float):  # noqa: ANN001
            seen_urls.append(http_request.full_url)
            if http_request.data is not None:
                body = http_request.data.decode("utf-8")
                seen_bodies.append(body)
                if "mbrId=user" in body:
                    return FakeResponse(b'{"_error_code":"CD001"}')
                return FakeResponse('{"output":[{"INVST_TP_NM":"외국인","NETBID_TRDVAL":"1,000"}]}'.encode("utf-8"))
            return FakeResponse()

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.build_opener", lambda *_args: FakeOpener())

    result = fetch_krx_data_market_endpoint(
        base_url="https://data.krx.co.kr",
        endpoint=endpoint,
        params={
            "strtDd": "20260508",
            "endDd": "20260508",
            "mktId": "STK",
            "etf": "",
            "etn": "",
            "elw": "",
        },
        timeout_seconds=12,
        login_id="user",
        login_password="pw",
    )

    assert seen_urls == [
        "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd",
        "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd",
        "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc",
        "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd",
        "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
    ]
    assert "mbrId=user" in seen_bodies[0]
    assert "pw=pw" in seen_bodies[0]
    assert "bld=dbms%2FMDC%2FSTAT%2Fstandard%2FMDCSTAT02201" in seen_bodies[1]
    assert result.row_count == 1


def test_fetch_krx_data_market_endpoint_raises_auth_error_on_logout_payload(monkeypatch) -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-market-period")

    class FakeResponse:
        def __init__(self, body: bytes = b"{}") -> None:
            self.body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    class FakeOpener:
        def open(self, http_request, timeout: float):  # noqa: ANN001
            if http_request.data is not None:
                return FakeResponse(b'{"message":"LOGOUT"}')
            return FakeResponse()

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.build_opener", lambda *_args: FakeOpener())

    with pytest.raises(KrxDataMarketAuthError, match="login is required"):
        fetch_krx_data_market_endpoint(
            base_url="https://data.krx.co.kr",
            endpoint=endpoint,
            params={"strtDd": "20260508", "endDd": "20260508", "mktId": "STK"},
            timeout_seconds=12,
        )


def test_fetch_krx_data_market_endpoint_raises_auth_error_on_login_failure(monkeypatch) -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-market-period")

    class FakeResponse:
        def __init__(self, body: bytes = b"{}") -> None:
            self.body = body

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    class FakeOpener:
        def open(self, http_request, timeout: float):  # noqa: ANN001
            if http_request.data is not None:
                return FakeResponse(b'{"_error_code":"CD999","_error_message":"bad login"}')
            return FakeResponse()

    monkeypatch.setattr("stock_monitor.fetch.krx_api.request.build_opener", lambda *_args: FakeOpener())

    with pytest.raises(KrxDataMarketAuthError, match="login failed"):
        fetch_krx_data_market_endpoint(
            base_url="https://data.krx.co.kr",
            endpoint=endpoint,
            params={"strtDd": "20260508", "endDd": "20260508", "mktId": "STK"},
            timeout_seconds=12,
            login_id="user",
            login_password="wrong",
        )


def test_parse_stock_market_daily_converts_numeric_strings() -> None:
    endpoint = resolve_krx_endpoints("stock-kospi-daily")[0]
    result = KrxDryRunResult(
        endpoint=endpoint,
        business_date=date(2026, 5, 7),
        row_count=1,
        field_keys=("BAS_DD", "ISU_CD", "ISU_NM"),
        rows=(
            {
                "BAS_DD": "20260507",
                "ISU_CD": "005930",
                "ISU_NM": "Samsung",
                "MKT_NM": "KOSPI",
                "TDD_CLSPRC": "100,000",
                "FLUC_RT": "1.25",
                "ACC_TRDVOL": "N/A",
                "ACC_TRDVAL": "NULL",
            },
        ),
        first_row={"BAS_DD": "20260507", "ISU_CD": "005930", "ISU_NM": "Samsung"},
    )

    snapshots = parse_stock_market_daily(result, fetched_at=datetime(2026, 5, 8, 20, 0, 0))

    assert snapshots[0].business_date == date(2026, 5, 7)
    assert snapshots[0].stock_code == "005930"
    assert snapshots[0].stock_name == "Samsung"
    assert snapshots[0].close_price == 100000
    assert snapshots[0].change_percent == 1.25
    assert snapshots[0].volume is None
    assert snapshots[0].turnover is None


def test_parse_stock_market_daily_rejects_date_mismatch() -> None:
    endpoint = resolve_krx_endpoints("stock-kospi-daily")[0]
    result = KrxDryRunResult(
        endpoint=endpoint,
        business_date=date(2026, 5, 7),
        row_count=1,
        field_keys=("BAS_DD", "ISU_CD", "ISU_NM", "MKT_NM"),
        rows=({"BAS_DD": "20260506", "ISU_CD": "005930", "ISU_NM": "Samsung", "MKT_NM": "KOSPI"},),
        first_row={"BAS_DD": "20260506", "ISU_CD": "005930", "ISU_NM": "Samsung"},
    )

    with pytest.raises(RuntimeError, match="outside requested date"):
        parse_stock_market_daily(result, fetched_at=datetime(2026, 5, 8, 20, 0, 0))


def test_parse_krx_stock_metadata_prefers_short_name_for_display() -> None:
    endpoint = resolve_krx_endpoints("stock-kospi-basic")[0]
    result = KrxDryRunResult(
        endpoint=endpoint,
        business_date=date(2026, 5, 7),
        row_count=1,
        field_keys=("ISU_CD", "ISU_SRT_CD", "ISU_NM", "ISU_ABBRV", "MKT_TP_NM"),
        rows=(
            {
                "ISU_CD": "KR7005930003",
                "ISU_SRT_CD": "005930",
                "ISU_NM": "삼성전자보통주",
                "ISU_ABBRV": "삼성전자",
                "MKT_TP_NM": "KOSPI",
            },
        ),
        first_row={"ISU_CD": "KR7005930003", "ISU_SRT_CD": "005930", "ISU_NM": "삼성전자보통주"},
    )

    snapshots = parse_krx_stock_metadata(result, fetched_at=datetime(2026, 5, 8, 20, 0, 0))

    assert snapshots[0].stock_code == "005930"
    assert snapshots[0].stock_name == "삼성전자"


def test_parse_market_index_daily_allows_blank_price_fields() -> None:
    endpoint = resolve_krx_endpoints("index-kospi-daily")[0]
    result = KrxDryRunResult(
        endpoint=endpoint,
        business_date=date(2026, 5, 7),
        row_count=1,
        field_keys=("BAS_DD", "IDX_CLSS", "IDX_NM", "CLSPRC_IDX"),
        rows=({"BAS_DD": "20260507", "IDX_CLSS": "KOSPI", "IDX_NM": "코스피", "CLSPRC_IDX": ""},),
        first_row={"BAS_DD": "20260507", "IDX_CLSS": "KOSPI", "IDX_NM": "코스피"},
    )

    snapshots = parse_market_index_daily(result, fetched_at=datetime(2026, 5, 8, 20, 0, 0))

    assert snapshots[0].index_series == "KOSPI"
    assert snapshots[0].close_index is None


def test_parse_stock_investor_flow_daily_normalizes_visible_12009_columns() -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-stock-period")
    result = KrxDataMarketDryRunResult(
        endpoint=endpoint,
        params={"isuCd": "KR7005930003"},
        row_count=1,
        field_keys=("INVST_TP_NM", "ASK_TRDVOL", "BID_TRDVOL", "NETBID_TRDVOL", "ASK_TRDVAL", "BID_TRDVAL", "NETBID_TRDVAL"),
        rows=(
            {
                "INVST_TP_NM": "외국인",
                "ASK_TRDVOL": "1,335,279",
                "BID_TRDVOL": "1,158,857",
                "NETBID_TRDVOL": "-176,422",
                "ASK_TRDVAL": "897,002,755,301",
                "BID_TRDVAL": "777,591,072,301",
                "NETBID_TRDVAL": "-119,411,683,000",
            },
        ),
        first_row=None,
    )

    rows = parse_stock_investor_flow_daily(
        result,
        business_date=date(2026, 5, 8),
        stock_code="329180",
        stock_name="HD현대중공업",
        market="KOSPI",
        candidate_score=85,
        candidate_reasons="리포트 6건; 목표가 있음",
        fetched_at=datetime(2026, 5, 9, 9, 2, 37),
    )

    assert len(rows) == 1
    assert rows[0].stock_code == "329180"
    assert rows[0].investor_type == "외국인"
    assert rows[0].sell_volume == 1335279
    assert rows[0].buy_volume == 1158857
    assert rows[0].net_buy_volume == -176422
    assert rows[0].sell_amount == 897002755301
    assert rows[0].buy_amount == 777591072301
    assert rows[0].net_buy_amount == -119411683000
    assert rows[0].candidate_score == 85


def test_parse_market_investor_flow_daily_normalizes_12008_rows() -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-flow-market-period")
    result = KrxDataMarketDryRunResult(
        endpoint=endpoint,
        params={"mktId": "STK"},
        row_count=1,
        field_keys=("INVST_TP_NM", "NETBID_TRDVOL", "NETBID_TRDVAL"),
        rows=({"INVST_TP_NM": "기관합계", "NETBID_TRDVOL": "3,984,844", "NETBID_TRDVAL": "888,240,872,250"},),
        first_row=None,
    )

    rows = parse_market_investor_flow_daily(
        result,
        business_date=date(2026, 5, 8),
        market="STK",
        fetched_at=datetime(2026, 5, 9, 9, 2, 37),
    )

    assert rows[0].market == "STK"
    assert rows[0].investor_type == "기관합계"
    assert rows[0].net_buy_volume == 3984844
    assert rows[0].net_buy_amount == 888240872250


def test_parse_investor_net_buy_top_daily_normalizes_12010_rows() -> None:
    endpoint = resolve_krx_data_market_endpoint("investor-net-buy-top")
    result = KrxDataMarketDryRunResult(
        endpoint=endpoint,
        params={"mktId": "STK", "invstTpCd": "9000"},
        row_count=1,
        field_keys=("RANK", "ISU_SRT_CD", "ISU_ABBRV", "NETBID_TRDVAL"),
        rows=({"RANK": "1", "ISU_SRT_CD": "005930", "ISU_ABBRV": "삼성전자", "NETBID_TRDVAL": "100,000"},),
        first_row=None,
    )

    rows = parse_investor_net_buy_top_daily(
        result,
        business_date=date(2026, 5, 8),
        market="STK",
        investor_type="foreign",
        fetched_at=datetime(2026, 5, 9, 9, 2, 37),
    )

    assert rows[0].rank == 1
    assert rows[0].stock_code == "005930"
    assert rows[0].stock_name == "삼성전자"
    assert rows[0].net_buy_amount == 100000
