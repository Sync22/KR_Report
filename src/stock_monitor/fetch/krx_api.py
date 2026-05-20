from __future__ import annotations

import json
import re
from http.cookiejar import CookieJar
from dataclasses import dataclass
from datetime import date, datetime
from urllib import error, request
from urllib import parse as url_parse

from stock_monitor.models import (
    EtfDailySnapshot,
    InvestorNetBuyTopDaily,
    KrxStockMetadataSnapshot,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    StockMarketDailySnapshot,
    StockInvestorFlowDaily,
)


@dataclass(frozen=True)
class KrxEndpoint:
    key: str
    label: str
    path: str


@dataclass(frozen=True)
class KrxDryRunResult:
    endpoint: KrxEndpoint
    business_date: date
    row_count: int
    field_keys: tuple[str, ...]
    rows: tuple[dict[str, object], ...]
    first_row: dict[str, object] | None


@dataclass(frozen=True)
class KrxDataMarketEndpoint:
    key: str
    label: str
    bld: str


@dataclass(frozen=True)
class KrxDataMarketDryRunResult:
    endpoint: KrxDataMarketEndpoint
    params: dict[str, str]
    row_count: int
    field_keys: tuple[str, ...]
    rows: tuple[dict[str, object], ...]
    first_row: dict[str, object] | None


class KrxDataMarketAuthError(RuntimeError):
    """Raised when KRX Data Marketplace authentication is missing or rejected."""


KRX_ENDPOINTS: dict[str, KrxEndpoint] = {
    "etf-daily": KrxEndpoint("etf-daily", "ETF 일별매매정보", "/svc/apis/etp/etf_bydd_trd"),
    "stock-kospi-daily": KrxEndpoint("stock-kospi-daily", "유가증권 일별매매정보", "/svc/apis/sto/stk_bydd_trd"),
    "stock-kosdaq-daily": KrxEndpoint("stock-kosdaq-daily", "코스닥 일별매매정보", "/svc/apis/sto/ksq_bydd_trd"),
    "stock-kospi-basic": KrxEndpoint("stock-kospi-basic", "유가증권 종목기본정보", "/svc/apis/sto/stk_isu_base_info"),
    "stock-kosdaq-basic": KrxEndpoint("stock-kosdaq-basic", "코스닥 종목기본정보", "/svc/apis/sto/ksq_isu_base_info"),
    "index-krx-daily": KrxEndpoint("index-krx-daily", "KRX 시리즈 일별시세정보", "/svc/apis/idx/krx_dd_trd"),
    "index-kospi-daily": KrxEndpoint("index-kospi-daily", "KOSPI 시리즈 일별시세정보", "/svc/apis/idx/kospi_dd_trd"),
    "index-kosdaq-daily": KrxEndpoint("index-kosdaq-daily", "KOSDAQ 시리즈 일별시세정보", "/svc/apis/idx/kosdaq_dd_trd"),
}

KRX_DATA_MARKET_ENDPOINTS: dict[str, KrxDataMarketEndpoint] = {
    "investor-flow-market-period": KrxDataMarketEndpoint(
        "investor-flow-market-period",
        "[12008] 투자자별 거래실적 기간합계",
        "dbms/MDC/STAT/standard/MDCSTAT02201",
    ),
    "investor-flow-stock-period": KrxDataMarketEndpoint(
        "investor-flow-stock-period",
        "[12009] 투자자별 거래실적(개별종목) 기간합계",
        "dbms/MDC/STAT/standard/MDCSTAT02301",
    ),
    "investor-flow-stock-trend": KrxDataMarketEndpoint(
        "investor-flow-stock-trend",
        "[12009] 투자자별 거래실적(개별종목) 일별추이",
        "dbms/MDC/STAT/standard/MDCSTAT02302",
    ),
    "investor-net-buy-top": KrxDataMarketEndpoint(
        "investor-net-buy-top",
        "[12010] 투자자별 순매수상위종목",
        "dbms/MDC/STAT/standard/MDCSTAT02401",
    ),
}


def resolve_krx_endpoints(selector: str) -> tuple[KrxEndpoint, ...]:
    normalized = selector.strip().lower()
    if normalized == "all":
        return tuple(KRX_ENDPOINTS.values())
    if normalized not in KRX_ENDPOINTS:
        valid = ", ".join(("all", *KRX_ENDPOINTS.keys()))
        raise ValueError(f"Unknown KRX endpoint '{selector}'. Valid values: {valid}")
    return (KRX_ENDPOINTS[normalized],)


def resolve_krx_data_market_endpoint(selector: str) -> KrxDataMarketEndpoint:
    normalized = selector.strip().lower()
    if normalized not in KRX_DATA_MARKET_ENDPOINTS:
        valid = ", ".join(KRX_DATA_MARKET_ENDPOINTS.keys())
        raise ValueError(f"Unknown KRX Data Marketplace endpoint '{selector}'. Valid values: {valid}")
    return KRX_DATA_MARKET_ENDPOINTS[normalized]


def fetch_krx_endpoint(
    *,
    base_url: str,
    auth_key: str,
    endpoint: KrxEndpoint,
    business_date: date,
    timeout_seconds: float,
) -> KrxDryRunResult:
    url = f"{base_url.rstrip('/')}{endpoint.path}"
    body = json.dumps({"basDd": business_date.strftime("%Y%m%d")}).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "AUTH_KEY": auth_key,
            "Content-Type": "application/json",
            "User-Agent": "stock-monitor/0.1",
        },
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch KRX endpoint {endpoint.key}: {exc}") from exc

    rows = payload.get("OutBlock_1") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError(f"Unexpected KRX response shape for {endpoint.key}.")

    normalized_rows = tuple(row for row in rows if isinstance(row, dict))
    first_row = normalized_rows[0] if normalized_rows else None
    field_keys = tuple(str(key) for key in first_row.keys()) if first_row else ()
    return KrxDryRunResult(
        endpoint=endpoint,
        business_date=business_date,
        row_count=len(normalized_rows),
        field_keys=field_keys,
        rows=normalized_rows,
        first_row=first_row,
    )


def fetch_krx_data_market_endpoint(
    *,
    base_url: str,
    endpoint: KrxDataMarketEndpoint,
    params: dict[str, str],
    timeout_seconds: float,
    login_id: str | None = None,
    login_password: str | None = None,
) -> KrxDataMarketDryRunResult:
    root_url = base_url.rstrip("/")
    warmup_url = f"{root_url}/contents/MDC/MDI/outerLoader/index.cmd"
    url = f"{root_url}/comm/bldAttendant/getJsonData.cmd"
    body = url_parse.urlencode({"bld": endpoint.bld, **params}).encode("utf-8")
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": root_url,
        "Referer": warmup_url,
        "User-Agent": user_agent,
        "X-Requested-With": "XMLHttpRequest",
    }
    opener = request.build_opener(request.HTTPCookieProcessor(CookieJar()))
    http_request = request.Request(
        url,
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        warmup_request = request.Request(warmup_url, method="GET", headers={"User-Agent": user_agent})
        with opener.open(warmup_request, timeout=timeout_seconds):
            pass
        if login_id and login_password:
            _login_krx_data_market(
                opener=opener,
                root_url=root_url,
                login_id=login_id,
                login_password=login_password,
                timeout_seconds=timeout_seconds,
                user_agent=user_agent,
            )
        with opener.open(http_request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body_snippet = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body_snippet = ""
        detail = f" HTTP {exc.code}"
        if body_snippet:
            detail += f" body={body_snippet!r}"
        if "LOGOUT" in body_snippet.upper():
            detail += " (KRX Data Marketplace login is required or the login session was rejected.)"
            raise KrxDataMarketAuthError(
                f"Failed to fetch KRX Data Marketplace endpoint {endpoint.key}:{detail}"
            ) from exc
        raise RuntimeError(f"Failed to fetch KRX Data Marketplace endpoint {endpoint.key}:{detail}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch KRX Data Marketplace endpoint {endpoint.key}: {exc}") from exc

    if _is_krx_data_market_logout_payload(payload):
        raise KrxDataMarketAuthError(
            f"KRX Data Marketplace login is required or the login session was rejected for {endpoint.key}."
        )

    rows = payload.get("output") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        message = payload.get("message") if isinstance(payload, dict) else None
        status = payload.get("status") if isinstance(payload, dict) else None
        detail = f" status={status!r} message={message!r}" if status or message else ""
        raise RuntimeError(f"Unexpected KRX Data Marketplace response shape for {endpoint.key}.{detail}")

    normalized_rows = tuple(row for row in rows if isinstance(row, dict))
    first_row = normalized_rows[0] if normalized_rows else None
    field_keys = tuple(str(key) for key in first_row.keys()) if first_row else ()
    safe_params = {key: value for key, value in params.items()}
    return KrxDataMarketDryRunResult(
        endpoint=endpoint,
        params=safe_params,
        row_count=len(normalized_rows),
        field_keys=field_keys,
        rows=normalized_rows,
        first_row=first_row,
    )


def build_krx_data_market_result_from_payload(
    *,
    endpoint: KrxDataMarketEndpoint,
    params: dict[str, str],
    payload: object,
) -> KrxDataMarketDryRunResult:
    rows = _extract_data_market_rows(payload)
    normalized_rows = tuple(row for row in rows if isinstance(row, dict))
    first_row = normalized_rows[0] if normalized_rows else None
    field_keys = tuple(str(key) for key in first_row.keys()) if first_row else ()
    return KrxDataMarketDryRunResult(
        endpoint=endpoint,
        params={key: value for key, value in params.items()},
        row_count=len(normalized_rows),
        field_keys=field_keys,
        rows=normalized_rows,
        first_row=first_row,
    )


def _extract_data_market_rows(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected KRX Data Marketplace sample shape.")
    for key in ("output", "OutBlock_1", "rows", "data", "result"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return rows
    message = payload.get("message")
    status = payload.get("status")
    detail = f" status={status!r} message={message!r}" if status or message else ""
    raise RuntimeError(f"Unexpected KRX Data Marketplace sample shape.{detail}")


def _login_krx_data_market(
    *,
    opener: request.OpenerDirector,
    root_url: str,
    login_id: str,
    login_password: str,
    timeout_seconds: float,
    user_agent: str,
) -> None:
    login_page_url = f"{root_url}/contents/MDC/COMS/client/MDCCOMS001.cmd"
    login_jsp_url = f"{root_url}/contents/MDC/COMS/client/view/login.jsp?site=mdc"
    login_url = f"{root_url}/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
    warmup_headers = {"User-Agent": user_agent}
    for url in (login_page_url, login_jsp_url):
        warmup_request = request.Request(url, method="GET", headers=warmup_headers)
        with opener.open(warmup_request, timeout=timeout_seconds):
            pass

    payload = {
        "mbrNm": "",
        "telNo": "",
        "di": "",
        "certType": "",
        "mbrId": login_id,
        "pw": login_password,
    }
    response_payload = _post_krx_login_payload(
        opener=opener,
        login_url=login_url,
        payload=payload,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
        referer=login_page_url,
    )
    if response_payload.get("_error_code") == "CD011":
        payload["skipDup"] = "Y"
        response_payload = _post_krx_login_payload(
            opener=opener,
            login_url=login_url,
            payload=payload,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            referer=login_page_url,
        )
    if response_payload.get("_error_code") != "CD001":
        error_code = response_payload.get("_error_code") or "unknown"
        error_message = response_payload.get("_error_message") or response_payload.get("error_message") or ""
        raise KrxDataMarketAuthError(f"KRX Data Marketplace login failed: code={error_code}, message={error_message}")


def _is_krx_data_market_logout_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    values = [
        payload.get("status"),
        payload.get("message"),
        payload.get("_error_code"),
        payload.get("_error_message"),
        payload.get("error_code"),
        payload.get("error_message"),
    ]
    return any("LOGOUT" in str(value).upper() for value in values if value is not None)


def _post_krx_login_payload(
    *,
    opener: request.OpenerDirector,
    login_url: str,
    payload: dict[str, str],
    timeout_seconds: float,
    user_agent: str,
    referer: str,
) -> dict[str, object]:
    body = url_parse.urlencode(payload).encode("utf-8")
    login_request = request.Request(
        login_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": referer,
            "User-Agent": user_agent,
        },
    )
    with opener.open(login_request, timeout=timeout_seconds) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected KRX Data Marketplace login response shape.")
    return result


def parse_stock_market_daily(result: KrxDryRunResult, *, fetched_at: datetime) -> tuple[StockMarketDailySnapshot, ...]:
    market = _market_from_endpoint(result.endpoint.key)
    if market is None:
        return ()
    _validate_required_keys(result, ("BAS_DD", "ISU_CD", "ISU_NM", "MKT_NM"))
    return tuple(
        StockMarketDailySnapshot(
            business_date=_parse_yyyymmdd(str(row.get("BAS_DD") or "")) or result.business_date,
            stock_code=_clean_text(row.get("ISU_CD")) or "",
            stock_name=_clean_text(row.get("ISU_NM")) or "",
            market=_clean_text(row.get("MKT_NM")) or market,
            section_name=_clean_text(row.get("SECT_TP_NM")),
            close_price=_parse_int(row.get("TDD_CLSPRC")),
            change_amount=_parse_int(row.get("CMPPREVDD_PRC")),
            change_percent=_parse_float(row.get("FLUC_RT")),
            open_price=_parse_int(row.get("TDD_OPNPRC")),
            high_price=_parse_int(row.get("TDD_HGPRC")),
            low_price=_parse_int(row.get("TDD_LWPRC")),
            volume=_parse_int(row.get("ACC_TRDVOL")),
            turnover=_parse_int(row.get("ACC_TRDVAL")),
            market_cap=_parse_int(row.get("MKTCAP")),
            listed_shares=_parse_int(row.get("LIST_SHRS")),
            fetched_at=fetched_at,
        )
        for row in result.rows
        if _is_six_digit_code(_clean_text(row.get("ISU_CD"))) and _clean_text(row.get("ISU_NM"))
    )


def parse_etf_daily(result: KrxDryRunResult, *, fetched_at: datetime) -> tuple[EtfDailySnapshot, ...]:
    if result.endpoint.key != "etf-daily":
        return ()
    _validate_required_keys(result, ("BAS_DD", "ISU_CD", "ISU_NM"))
    return tuple(
        EtfDailySnapshot(
            business_date=_parse_yyyymmdd(str(row.get("BAS_DD") or "")) or result.business_date,
            etf_code=_clean_text(row.get("ISU_CD")) or "",
            etf_name=_clean_text(row.get("ISU_NM")) or "",
            close_price=_parse_int(row.get("TDD_CLSPRC")),
            change_amount=_parse_int(row.get("CMPPREVDD_PRC")),
            change_percent=_parse_float(row.get("FLUC_RT")),
            nav=_parse_float(row.get("NAV")),
            open_price=_parse_int(row.get("TDD_OPNPRC")),
            high_price=_parse_int(row.get("TDD_HGPRC")),
            low_price=_parse_int(row.get("TDD_LWPRC")),
            volume=_parse_int(row.get("ACC_TRDVOL")),
            turnover=_parse_int(row.get("ACC_TRDVAL")),
            market_cap=_parse_int(row.get("MKTCAP")),
            net_assets_total=_parse_int(row.get("INVSTASST_NETASST_TOTAMT")),
            listed_shares=_parse_int(row.get("LIST_SHRS")),
            underlying_index_name=_clean_text(row.get("IDX_IND_NM")),
            underlying_index_close=_parse_float(row.get("OBJ_STKPRC_IDX")),
            underlying_index_change_amount=_parse_float(row.get("CMPPREVDD_IDX")),
            underlying_index_change_percent=_parse_float(row.get("FLUC_RT_IDX")),
            fetched_at=fetched_at,
        )
        for row in result.rows
        if _is_six_digit_code(_clean_text(row.get("ISU_CD"))) and _clean_text(row.get("ISU_NM"))
    )


def parse_krx_stock_metadata(
    result: KrxDryRunResult,
    *,
    fetched_at: datetime,
) -> tuple[KrxStockMetadataSnapshot, ...]:
    market = _metadata_market_from_endpoint(result.endpoint.key)
    if market is None:
        return ()
    _validate_required_keys(result, ("ISU_CD", "ISU_SRT_CD", "ISU_NM", "ISU_ABBRV", "MKT_TP_NM"))
    return tuple(
        KrxStockMetadataSnapshot(
            business_date=result.business_date,
            standard_code=_clean_text(row.get("ISU_CD")) or "",
            stock_code=_clean_text(row.get("ISU_SRT_CD")) or "",
            stock_name=_clean_text(row.get("ISU_ABBRV")) or _clean_text(row.get("ISU_NM")) or "",
            stock_short_name=_clean_text(row.get("ISU_ABBRV")),
            stock_english_name=_clean_text(row.get("ISU_ENG_NM")),
            listed_date=_parse_yyyymmdd(str(row.get("LIST_DD") or "")),
            market=_clean_text(row.get("MKT_TP_NM")) or market,
            security_group=_clean_text(row.get("SECUGRP_NM")),
            section_name=_clean_text(row.get("SECT_TP_NM")),
            stock_certificate_type=_clean_text(row.get("KIND_STKCERT_TP_NM")),
            par_value=_clean_text(row.get("PARVAL")),
            listed_shares=_parse_int(row.get("LIST_SHRS")),
            fetched_at=fetched_at,
        )
        for row in result.rows
        if _clean_text(row.get("ISU_CD"))
        and _is_six_digit_code(_clean_text(row.get("ISU_SRT_CD")))
        and _clean_text(row.get("ISU_NM"))
    )


def parse_market_index_daily(result: KrxDryRunResult, *, fetched_at: datetime) -> tuple[MarketIndexDailySnapshot, ...]:
    series = _index_series_from_endpoint(result.endpoint.key)
    if series is None:
        return ()
    _validate_required_keys(result, ("BAS_DD", "IDX_CLSS", "IDX_NM"))
    return tuple(
        MarketIndexDailySnapshot(
            business_date=_parse_yyyymmdd(str(row.get("BAS_DD") or "")) or result.business_date,
            index_series=series,
            index_class=_clean_text(row.get("IDX_CLSS")) or series,
            index_name=_clean_text(row.get("IDX_NM")) or "",
            close_index=_parse_float(row.get("CLSPRC_IDX")),
            change_amount=_parse_float(row.get("CMPPREVDD_IDX")),
            change_percent=_parse_float(row.get("FLUC_RT")),
            open_index=_parse_float(row.get("OPNPRC_IDX")),
            high_index=_parse_float(row.get("HGPRC_IDX")),
            low_index=_parse_float(row.get("LWPRC_IDX")),
            volume=_parse_int(row.get("ACC_TRDVOL")),
            turnover=_parse_int(row.get("ACC_TRDVAL")),
            market_cap=_parse_int(row.get("MKTCAP")),
            fetched_at=fetched_at,
        )
        for row in result.rows
        if _clean_text(row.get("IDX_NM"))
    )


def parse_stock_investor_flow_daily(
    result: KrxDataMarketDryRunResult,
    *,
    business_date: date,
    stock_code: str,
    stock_name: str | None,
    fetched_at: datetime,
    market: str | None = None,
    volume_unit: str | None = "주",
    amount_unit: str | None = "원",
    candidate_score: int | None = None,
    candidate_reasons: str | None = None,
) -> tuple[StockInvestorFlowDaily, ...]:
    _validate_data_market_endpoint(result, {"investor-flow-stock-period", "investor-flow-stock-trend"})
    normalized_stock_code = _clean_text(stock_code)
    if not _is_six_digit_code(normalized_stock_code):
        raise RuntimeError("KRX stock investor flow requires a six-digit stock_code.")
    rows: list[StockInvestorFlowDaily] = []
    for row in result.rows:
        investor_type = _clean_text(_value_by_alias(row, "INVST_TP_NM", "INVST_TP", "INVST_TP_CD_NM"))
        if investor_type is None:
            continue
        rows.append(
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code=normalized_stock_code,
                stock_name=_clean_text(stock_name),
                market=_clean_text(market),
                investor_type=investor_type,
                sell_volume=_parse_int(_value_by_alias(row, "ASK_TRDVOL", "SELL_TRDVOL")),
                buy_volume=_parse_int(_value_by_alias(row, "BID_TRDVOL", "BUY_TRDVOL")),
                net_buy_volume=_parse_int(_value_by_alias(row, "NETBID_TRDVOL", "NET_BUY_TRDVOL")),
                sell_amount=_parse_int(_value_by_alias(row, "ASK_TRDVAL", "SELL_TRDVAL")),
                buy_amount=_parse_int(_value_by_alias(row, "BID_TRDVAL", "BUY_TRDVAL")),
                net_buy_amount=_parse_int(_value_by_alias(row, "NETBID_TRDVAL", "NET_BUY_TRDVAL")),
                volume_unit=volume_unit,
                amount_unit=amount_unit,
                candidate_score=candidate_score,
                candidate_reasons=candidate_reasons,
                fetched_at=fetched_at,
            )
        )
    return tuple(rows)


def parse_market_investor_flow_daily(
    result: KrxDataMarketDryRunResult,
    *,
    business_date: date,
    market: str,
    fetched_at: datetime,
    volume_unit: str | None = "주",
    amount_unit: str | None = "원",
) -> tuple[MarketInvestorFlowDaily, ...]:
    _validate_data_market_endpoint(result, {"investor-flow-market-period"})
    normalized_market = _clean_text(market) or "ALL"
    rows: list[MarketInvestorFlowDaily] = []
    for row in result.rows:
        investor_type = _clean_text(_value_by_alias(row, "INVST_TP_NM", "INVST_TP", "INVST_TP_CD_NM"))
        if investor_type is None:
            continue
        rows.append(
            MarketInvestorFlowDaily(
                business_date=business_date,
                market=normalized_market,
                investor_type=investor_type,
                sell_volume=_parse_int(_value_by_alias(row, "ASK_TRDVOL", "SELL_TRDVOL")),
                buy_volume=_parse_int(_value_by_alias(row, "BID_TRDVOL", "BUY_TRDVOL")),
                net_buy_volume=_parse_int(_value_by_alias(row, "NETBID_TRDVOL", "NET_BUY_TRDVOL")),
                sell_amount=_parse_int(_value_by_alias(row, "ASK_TRDVAL", "SELL_TRDVAL")),
                buy_amount=_parse_int(_value_by_alias(row, "BID_TRDVAL", "BUY_TRDVAL")),
                net_buy_amount=_parse_int(_value_by_alias(row, "NETBID_TRDVAL", "NET_BUY_TRDVAL")),
                volume_unit=volume_unit,
                amount_unit=amount_unit,
                fetched_at=fetched_at,
            )
        )
    return tuple(rows)


def parse_investor_net_buy_top_daily(
    result: KrxDataMarketDryRunResult,
    *,
    business_date: date,
    market: str,
    investor_type: str,
    fetched_at: datetime,
) -> tuple[InvestorNetBuyTopDaily, ...]:
    _validate_data_market_endpoint(result, {"investor-net-buy-top"})
    normalized_market = _clean_text(market) or "ALL"
    normalized_investor = _clean_text(investor_type) or "all"
    rows: list[InvestorNetBuyTopDaily] = []
    for index, row in enumerate(result.rows, start=1):
        stock_code = _clean_text(_value_by_alias(row, "ISU_SRT_CD", "ISU_CD", "CODE"))
        stock_name = _clean_text(_value_by_alias(row, "ISU_ABBRV", "ISU_NM", "ISU_NM_KOR", "NAME"))
        if not _is_six_digit_code(stock_code) or stock_name is None:
            continue
        rank = _parse_int(_value_by_alias(row, "RANK", "RNK", "NO")) or index
        rows.append(
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market=normalized_market,
                investor_type=normalized_investor,
                rank=rank,
                stock_code=stock_code,
                stock_name=stock_name,
                net_buy_volume=_parse_int(_value_by_alias(row, "NETBID_TRDVOL", "NET_BUY_TRDVOL")),
                net_buy_amount=_parse_int(_value_by_alias(row, "NETBID_TRDVAL", "NET_BUY_TRDVAL")),
                fetched_at=fetched_at,
            )
        )
    return tuple(rows)


def _market_from_endpoint(endpoint_key: str) -> str | None:
    return {
        "stock-kospi-daily": "KOSPI",
        "stock-kosdaq-daily": "KOSDAQ",
    }.get(endpoint_key)


def _metadata_market_from_endpoint(endpoint_key: str) -> str | None:
    return {
        "stock-kospi-basic": "KOSPI",
        "stock-kosdaq-basic": "KOSDAQ",
    }.get(endpoint_key)


def _index_series_from_endpoint(endpoint_key: str) -> str | None:
    return {
        "index-krx-daily": "KRX",
        "index-kospi-daily": "KOSPI",
        "index-kosdaq-daily": "KOSDAQ",
    }.get(endpoint_key)


def _clean_text(value: object) -> str | None:
    text = str(value or "").strip()
    if not text or text == "-" or text.upper() in {"N/A", "NA", "NULL", "NONE"}:
        return None
    return text


def _parse_int(value: object) -> int | None:
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return int(float(text.replace(",", "")))
    except ValueError:
        return None


def _parse_float(value: object) -> float | None:
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _parse_yyyymmdd(value: str) -> date | None:
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return date(year=int(text[:4]), month=int(text[4:6]), day=int(text[6:8]))
    except (ValueError, IndexError):
        return None


def _validate_required_keys(result: KrxDryRunResult, required_keys: tuple[str, ...]) -> None:
    if not result.rows:
        return
    missing_by_key = {key: 0 for key in required_keys}
    date_mismatches = 0
    for row in result.rows:
        for key in required_keys:
            if key not in row:
                missing_by_key[key] += 1
        row_date = row.get("BAS_DD")
        if row_date is not None and _parse_yyyymmdd(str(row_date)) not in {None, result.business_date}:
            date_mismatches += 1
    missing = {key: count for key, count in missing_by_key.items() if count}
    if missing:
        raise RuntimeError(f"KRX endpoint {result.endpoint.key} missing required field(s): {missing}")
    if date_mismatches:
        raise RuntimeError(f"KRX endpoint {result.endpoint.key} returned rows outside requested date.")


def _validate_data_market_endpoint(result: KrxDataMarketDryRunResult, allowed_keys: set[str]) -> None:
    if result.endpoint.key not in allowed_keys:
        allowed = ", ".join(sorted(allowed_keys))
        raise RuntimeError(f"KRX Data Marketplace endpoint {result.endpoint.key} is not valid for parser. Expected: {allowed}")


def _value_by_alias(row: dict[str, object], *aliases: str) -> object:
    for alias in aliases:
        if alias in row:
            return row.get(alias)
    return None


def _is_six_digit_code(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"\d{6}", value))
