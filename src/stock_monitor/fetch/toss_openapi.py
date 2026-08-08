from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import MappingProxyType
from urllib import error, parse, request

from stock_monitor.config import _parse_bool, _read_dotenv


TOSS_OPENAPI_BASE_URL = "https://openapi.tossinvest.com"
TOSS_OPENAPI_MAX_RESPONSE_BYTES = 1_048_576
_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
_FORBIDDEN_GROUPS = ("account", "asset", "order-info", "order-history", "order", "conditional-order")
_PRICE_FIELDS = frozenset({"symbol", "timestamp", "lastPrice", "currency"})
_STOCK_FIELDS = frozenset(
    {
        "symbol",
        "name",
        "englishName",
        "isinCode",
        "market",
        "securityType",
        "isCommonShare",
        "status",
        "currency",
        "listDate",
        "delistDate",
        "sharesOutstanding",
        "leverageFactor",
        "koreanMarketDetail",
    }
)
_KR_MARKET_DETAIL_FIELDS = frozenset(
    {"liquidationTrading", "nxtSupported", "krxTradingSuspended", "nxtTradingSuspended"}
)
_KR_CALENDAR_FIELDS = frozenset({"today", "previousBusinessDay", "nextBusinessDay"})
_KR_MARKET_DAY_FIELDS = frozenset({"date", "integrated"})
_INTEGRATED_HOUR_FIELDS = frozenset({"preMarket", "regularMarket", "afterMarket"})
_MARKET_SESSION_FIELDS = frozenset(
    {"startTime", "endTime", "singlePriceAuctionStartTime", "singlePriceAuctionEndTime"}
)
_RANKING_RESPONSE_FIELDS = frozenset({"rankedAt", "rankings"})
_RANKING_ITEM_FIELDS = frozenset({"rank", "symbol", "currency", "price", "tradingVolume", "tradingAmount"})
_RANKING_PRICE_FIELDS = frozenset({"lastPrice", "basePrice", "changeRate"})
_INVESTOR_TRADING_RESPONSE_FIELDS = frozenset({"nextUntil", "records"})
_INVESTOR_TRADING_RECORD_FIELDS = frozenset(
    {"date", "updatedAt", "individual", "foreigner", "institution", "otherCorporation"}
)
_INVESTOR_TRADING_AMOUNT_FIELDS = frozenset({"buyAmount", "sellAmount"})
_STOCK_INVESTOR_TRADING_RECORD_FIELDS = frozenset(
    {"date", "updatedAt", "individual", "foreigner", "institution", "otherCorporation", "foreignerHolding", "cfd"}
)
_INVESTOR_TRADING_VOLUME_FIELDS = frozenset({"buyVolume", "sellVolume", "netBuyVolume"})
_STOCK_INSTITUTION_TRADING_VOLUME_FIELDS = _INVESTOR_TRADING_VOLUME_FIELDS | frozenset({"breakdown"})


class TossOpenApiSafetyError(RuntimeError):
    """Raised when a Toss request crosses the read-only lab boundary."""


class TossOpenApiHttpError(RuntimeError):
    """Safe provider HTTP error metadata without response-body or credential leakage."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        provider_code: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider_code = provider_code
        self.retry_after = retry_after


@dataclass(frozen=True)
class TossReadonlyEndpoint:
    key: str
    operation_id: str
    path: str
    rate_group: str
    requires_symbols: bool = False
    accepts_date: bool = False
    fixed_params: tuple[tuple[str, str], ...] = ()
    path_symbol: bool = False


@dataclass(frozen=True)
class TossAccessToken:
    access_token: str = field(repr=False)
    expires_in: int


@dataclass(frozen=True)
class TossReadonlyResponse:
    endpoint: TossReadonlyEndpoint
    result: object
    row_count: int
    rate_limit: dict[str, str]


@dataclass(frozen=True)
class TossOpenApiLabConfig:
    client_id: str | None = field(repr=False)
    client_secret: str | None = field(repr=False)
    live_enabled: bool
    base_url: str
    timeout_seconds: float

    @classmethod
    def from_env(cls, root_dir: Path | None = None) -> "TossOpenApiLabConfig":
        project_root = root_dir or Path(__file__).resolve().parents[3]
        env = _read_dotenv(project_root / ".env.toss-openapi")
        return cls(
            client_id=env.get("STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID") or None,
            client_secret=env.get("STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET") or None,
            live_enabled=_parse_bool(env.get("STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED"), False),
            base_url=env.get("STOCK_MONITOR_TOSS_OPENAPI_BASE_URL", TOSS_OPENAPI_BASE_URL).rstrip("/"),
            timeout_seconds=float(env.get("STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS", "15")),
        )


_PROBE_READONLY_ENDPOINTS = (
    TossReadonlyEndpoint("stocks", "getStocks", "/api/v1/stocks", "STOCK", requires_symbols=True),
    TossReadonlyEndpoint(
        "market-calendar-kr",
        "getKrMarketCalendar",
        "/api/v1/market-calendar/KR",
        "MARKET_INFO",
        accepts_date=True,
    ),
    TossReadonlyEndpoint("prices", "getPrices", "/api/v1/prices", "MARKET_DATA", requires_symbols=True),
)
_MARKET_CONTEXT_ENDPOINTS = (
    TossReadonlyEndpoint(
        "ranking-kr-top20",
        "getRankings",
        "/api/v1/rankings",
        "RANKING",
        fixed_params=(
            ("type", "MARKET_TRADING_AMOUNT"),
            ("marketCountry", "KR"),
            ("duration", "realtime"),
            ("count", "20"),
        ),
    ),
    TossReadonlyEndpoint(
        "market-investor-kospi",
        "getMarketIndicatorInvestorTrading",
        "/api/v1/market-indicators/KOSPI/investor-trading",
        "MARKET_INDICATOR",
        fixed_params=(("interval", "1d"), ("count", "1")),
    ),
    TossReadonlyEndpoint(
        "market-investor-kosdaq",
        "getMarketIndicatorInvestorTrading",
        "/api/v1/market-indicators/KOSDAQ/investor-trading",
        "MARKET_INDICATOR",
        fixed_params=(("interval", "1d"), ("count", "1")),
    ),
    TossReadonlyEndpoint(
        "priority-investor-trading",
        "getStockInvestorTrading",
        "/api/v1/stocks/{symbol}/investor-trading",
        "STOCK_TRADING_TREND",
        fixed_params=(("count", "1"),),
        path_symbol=True,
    ),
)
_FIXED_READONLY_ENDPOINTS = _PROBE_READONLY_ENDPOINTS + _MARKET_CONTEXT_ENDPOINTS
TOSS_READONLY_ENDPOINTS: Mapping[str, TossReadonlyEndpoint] = MappingProxyType(
    {endpoint.key: endpoint for endpoint in _PROBE_READONLY_ENDPOINTS}
)


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def _urlopen_no_redirect(http_request: request.Request, *, timeout: float) -> object:
    return request.build_opener(_NoRedirectHandler()).open(http_request, timeout=timeout)


def resolve_toss_readonly_endpoint(selector: str) -> TossReadonlyEndpoint:
    selector_key = selector.strip().lower()
    endpoint = next(
        (candidate for candidate in _PROBE_READONLY_ENDPOINTS if candidate.key == selector_key),
        None,
    )
    if endpoint is None:
        allowed = ", ".join(endpoint.key for endpoint in _PROBE_READONLY_ENDPOINTS)
        raise TossOpenApiSafetyError(
            f"Toss endpoint '{selector}' is not allowed by the read-only lab profile. Allowed values: {allowed}."
        )
    return endpoint


def resolve_toss_market_context_endpoint(selector: str) -> TossReadonlyEndpoint:
    selector_key = selector.strip().lower()
    endpoint = next(
        (candidate for candidate in _MARKET_CONTEXT_ENDPOINTS if candidate.key == selector_key),
        None,
    )
    if endpoint is None:
        raise TossOpenApiSafetyError(f"Toss market-context endpoint '{selector}' is not allowed.")
    return endpoint


def build_toss_readonly_probe_plan(
    *,
    endpoint_selector: str,
    symbols: tuple[str, ...] = (),
    query_date: date | None = None,
) -> dict[str, object]:
    endpoint = resolve_toss_readonly_endpoint(endpoint_selector)
    params = _build_readonly_params(endpoint, symbols=symbols, query_date=query_date)
    return {
        "surface": "toss-openapi-readonly-probe",
        "mode": "plan",
        "read_only": True,
        "live_fetch": False,
        "reads_secrets": False,
        "writes_db": False,
        "sends_telegram": False,
        "registers_scheduler": False,
        "connects_admin_gui": False,
        "connects_web_view": False,
        "affects_ordering": False,
        "endpoint": endpoint.key,
        "operation_id": endpoint.operation_id,
        "path": endpoint.path,
        "rate_group": endpoint.rate_group,
        "params": params,
        "requires_live_flag": True,
        "requires_env_opt_in": "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true",
        "requires_token_reissue_confirmation": True,
        "forbidden_groups": list(_FORBIDDEN_GROUPS),
    }


def issue_toss_access_token(
    *,
    base_url: str,
    client_id: str,
    client_secret: str,
    timeout_seconds: float,
    live_enabled: bool = False,
    confirm_token_reissue: bool = False,
    urlopen: Callable[..., object] = _urlopen_no_redirect,
) -> TossAccessToken:
    _validate_official_base_url(base_url)
    if not live_enabled:
        raise TossOpenApiSafetyError("Token issuance requires explicit live enablement.")
    if not confirm_token_reissue:
        raise TossOpenApiSafetyError("Token issuance requires token-reissue confirmation.")
    if not client_id or not client_secret:
        raise TossOpenApiSafetyError("Toss OpenAPI client credentials are required for a live probe.")
    body = parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    http_request = request.Request(
        f"{TOSS_OPENAPI_BASE_URL}/oauth2/token",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "stock-monitor-toss-readonly-lab/0.1",
        },
    )
    payload = _open_json(http_request, timeout_seconds=timeout_seconds, urlopen=urlopen, action="token request")
    access_token = payload.get("access_token")
    token_type = payload.get("token_type")
    expires_in = payload.get("expires_in")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Toss OpenAPI token response did not include an access token.")
    if (
        not isinstance(token_type, str)
        or token_type.lower() != "bearer"
        or not isinstance(expires_in, int)
        or expires_in <= 0
    ):
        raise RuntimeError("Toss OpenAPI token response had an unexpected shape.")
    return TossAccessToken(access_token=access_token, expires_in=expires_in)


def fetch_toss_readonly_endpoint(
    *,
    base_url: str,
    access_token: str,
    endpoint: TossReadonlyEndpoint,
    params: dict[str, str],
    timeout_seconds: float,
    live_enabled: bool = False,
    urlopen: Callable[..., object] = _urlopen_no_redirect,
) -> TossReadonlyResponse:
    _validate_official_base_url(base_url)
    if not live_enabled:
        raise TossOpenApiSafetyError("Live Toss fetches require explicit live enablement.")
    if endpoint not in _FIXED_READONLY_ENDPOINTS:
        raise TossOpenApiSafetyError("Only the fixed Toss read-only endpoint allowlist may be fetched.")
    _validate_fetch_params(endpoint, params)
    if not access_token:
        raise TossOpenApiSafetyError("A Toss OpenAPI access token is required for a live probe.")
    path = endpoint.path
    query_params = params
    if endpoint.path_symbol:
        symbol = params["symbol"]
        path = path.replace("{symbol}", parse.quote(symbol, safe=""))
        query_params = {key: value for key, value in params.items() if key != "symbol"}
    url = f"{TOSS_OPENAPI_BASE_URL}{path}"
    if query_params:
        url = f"{url}?{parse.urlencode(query_params)}"
    http_request = request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "stock-monitor-toss-readonly-lab/0.1",
        },
    )
    try:
        with urlopen(http_request, timeout=timeout_seconds) as response:
            payload = _decode_json_response(response, action=f"{endpoint.key} request")
            rate_limit = _read_rate_limit_headers(getattr(response, "headers", {}))
    except error.HTTPError as exc:
        raise _safe_http_error(exc, action=f"{endpoint.key} request") from None
    except (error.URLError, TimeoutError, OSError):
        raise RuntimeError(f"Toss OpenAPI {endpoint.key} request failed (transport error).") from None
    result = payload.get("result")
    expected_type = dict if endpoint.key in {
        "market-calendar-kr",
        "ranking-kr-top20",
        "market-investor-kospi",
        "market-investor-kosdaq",
        "priority-investor-trading",
    } else list
    if not isinstance(result, expected_type):
        raise RuntimeError(f"Toss OpenAPI {endpoint.key} response had an unexpected shape.")
    _validate_readonly_result(endpoint, result)
    return TossReadonlyResponse(
        endpoint=endpoint,
        result=result,
        row_count=len(result) if isinstance(result, list) else 1,
        rate_limit=rate_limit,
    )


def run_toss_readonly_probe(
    *,
    base_url: str,
    client_id: str,
    client_secret: str,
    endpoint_selector: str,
    symbols: tuple[str, ...] = (),
    query_date: date | None = None,
    timeout_seconds: float,
    live_enabled: bool = False,
    confirm_token_reissue: bool = False,
    urlopen: Callable[..., object] = _urlopen_no_redirect,
) -> dict[str, object]:
    plan = build_toss_readonly_probe_plan(
        endpoint_selector=endpoint_selector,
        symbols=symbols,
        query_date=query_date,
    )
    if not live_enabled:
        raise TossOpenApiSafetyError("Direct live Toss probes require explicit live enablement.")
    if not confirm_token_reissue:
        raise TossOpenApiSafetyError("Direct live Toss probes require token-reissue confirmation.")
    token = issue_toss_access_token(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=timeout_seconds,
        live_enabled=live_enabled,
        confirm_token_reissue=confirm_token_reissue,
        urlopen=urlopen,
    )
    response = fetch_toss_readonly_endpoint(
        base_url=base_url,
        access_token=token.access_token,
        endpoint=resolve_toss_readonly_endpoint(endpoint_selector),
        params=dict(plan["params"]),
        timeout_seconds=timeout_seconds,
        live_enabled=live_enabled,
        urlopen=urlopen,
    )
    return {
        **plan,
        "mode": "live",
        "live_fetch": True,
        "reads_secrets": True,
        "token_expires_in": token.expires_in,
        "row_count": response.row_count,
        "rate_limit": response.rate_limit,
        "result": response.result,
    }


def _build_readonly_params(
    endpoint: TossReadonlyEndpoint,
    *,
    symbols: tuple[str, ...],
    query_date: date | None,
) -> dict[str, str]:
    if endpoint.fixed_params:
        if symbols or query_date is not None:
            raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' accepts only its fixed market-context query.")
        return dict(endpoint.fixed_params)
    normalized_symbols = tuple(symbol.strip() for symbol in symbols if symbol.strip())
    if len(normalized_symbols) > 2:
        raise TossOpenApiSafetyError("The Toss read-only lab probe accepts at most 2 symbols.")
    if any(not _SYMBOL_PATTERN.fullmatch(symbol) for symbol in normalized_symbols):
        raise TossOpenApiSafetyError("The main Toss lab profile accepts only six-digit Korean stock codes.")
    if endpoint.requires_symbols and not normalized_symbols:
        raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' requires at least one --symbol.")
    if not endpoint.requires_symbols and normalized_symbols:
        raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' does not accept --symbol.")
    if query_date is not None and not endpoint.accepts_date:
        raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' does not accept --date.")
    params: dict[str, str] = {}
    if normalized_symbols:
        params["symbols"] = ",".join(normalized_symbols)
    if query_date is not None:
        params["date"] = query_date.isoformat()
    return params


def _validate_fetch_params(endpoint: TossReadonlyEndpoint, params: dict[str, str]) -> None:
    if endpoint.fixed_params:
        expected = dict(endpoint.fixed_params)
        if endpoint.key.startswith("market-investor-"):
            expected["until"] = params.get("until", "")
            try:
                date.fromisoformat(expected["until"])
            except ValueError:
                raise TossOpenApiSafetyError("Toss market investor context requires an ISO reference date.") from None
        if endpoint.key == "priority-investor-trading":
            expected["symbol"] = params.get("symbol", "")
            expected["until"] = params.get("until", "")
            if not _SYMBOL_PATTERN.fullmatch(expected["symbol"]):
                raise TossOpenApiSafetyError("Toss priority investor context requires a six-digit Korean stock code.")
            try:
                date.fromisoformat(expected["until"])
            except ValueError:
                raise TossOpenApiSafetyError("Toss priority investor context requires an ISO reference date.") from None
        if params != expected:
            raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' received a noncanonical fixed query.")
        return
    allowed_keys = {"symbols"} if endpoint.requires_symbols else set()
    if endpoint.accepts_date:
        allowed_keys.add("date")
    if not set(params).issubset(allowed_keys):
        raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' received unsupported query parameters.")
    raw_symbols = params.get("symbols", "")
    symbols = tuple(raw_symbols.split(",")) if raw_symbols else ()
    raw_date = params.get("date")
    try:
        query_date = date.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        raise TossOpenApiSafetyError("Toss query date must use YYYY-MM-DD.") from None
    expected = _build_readonly_params(endpoint, symbols=symbols, query_date=query_date)
    if params != expected:
        raise TossOpenApiSafetyError(f"Toss endpoint '{endpoint.key}' received noncanonical query parameters.")


def _validate_readonly_result(endpoint: TossReadonlyEndpoint, result: object) -> None:
    if endpoint.key == "prices":
        rows = _validate_object_list(result, allowed=_PRICE_FIELDS, label="prices")
        for row in rows:
            _validate_scalar_values(row, nested_fields=frozenset(), label="prices item")
        return
    if endpoint.key == "ranking-kr-top20":
        ranking = _validate_object(result, allowed=_RANKING_RESPONSE_FIELDS, label="ranking")
        ranked_at = ranking.get("rankedAt")
        if ranked_at is not None and not isinstance(ranked_at, str):
            raise RuntimeError("Toss OpenAPI ranking result had an unexpected rankedAt value.")
        rows = _validate_object_list(ranking.get("rankings"), allowed=_RANKING_ITEM_FIELDS, label="ranking rows")
        if len(rows) > 20:
            raise RuntimeError("Toss OpenAPI ranking result exceeded the fixed Top20 limit.")
        for row in rows:
            _validate_scalar_values(row, nested_fields=frozenset({"price"}), label="ranking item")
            price = row.get("price")
            if price is not None:
                price_object = _validate_object(price, allowed=_RANKING_PRICE_FIELDS, label="ranking item.price")
                _validate_scalar_values(price_object, nested_fields=frozenset(), label="ranking item.price")
        return
    if endpoint.key.startswith("market-investor-"):
        investor = _validate_object(result, allowed=_INVESTOR_TRADING_RESPONSE_FIELDS, label="market investor trading")
        records = _validate_object_list(
            investor.get("records"),
            allowed=_INVESTOR_TRADING_RECORD_FIELDS,
            label="market investor trading records",
        )
        if len(records) > 1:
            raise RuntimeError("Toss OpenAPI market investor context exceeded the fixed one-record limit.")
        for record in records:
            _validate_scalar_values(
                record,
                nested_fields=frozenset({"individual", "foreigner", "institution", "otherCorporation"}),
                label="market investor trading record",
            )
            for key in ("individual", "foreigner", "institution", "otherCorporation"):
                amount = record.get(key)
                if amount is not None:
                    amount_object = _validate_object(
                        amount,
                        allowed=_INVESTOR_TRADING_AMOUNT_FIELDS,
                        label=f"market investor trading record.{key}",
                        report_unknown_fields=True,
                    )
                    _validate_scalar_values(
                        amount_object,
                        nested_fields=frozenset(),
                        label=f"market investor trading record.{key}",
                    )
        return
    if endpoint.key == "priority-investor-trading":
        investor = _validate_object(result, allowed=_INVESTOR_TRADING_RESPONSE_FIELDS, label="priority investor trading")
        records = _validate_object_list(
            investor.get("records"),
            allowed=_STOCK_INVESTOR_TRADING_RECORD_FIELDS,
            label="priority investor trading records",
        )
        if len(records) > 1:
            raise RuntimeError("Toss OpenAPI priority investor context exceeded the fixed one-record limit.")
        for record in records:
            _validate_scalar_values(
                record,
                nested_fields=frozenset(
                    {"individual", "foreigner", "institution", "otherCorporation", "foreignerHolding", "cfd"}
                ),
                label="priority investor trading record",
            )
            for key, allowed in (
                ("foreigner", _INVESTOR_TRADING_VOLUME_FIELDS),
                ("institution", _STOCK_INSTITUTION_TRADING_VOLUME_FIELDS),
            ):
                value = record.get(key)
                if value is not None:
                    item = _validate_object(value, allowed=allowed, label=f"priority investor trading record.{key}")
                    _validate_scalar_values(
                        item,
                        nested_fields=frozenset({"breakdown"}),
                        label=f"priority investor trading record.{key}",
                    )
        return
    if endpoint.key == "stocks":
        rows = _validate_object_list(result, allowed=_STOCK_FIELDS, label="stocks")
        for row in rows:
            _validate_scalar_values(
                row,
                nested_fields=frozenset({"koreanMarketDetail"}),
                label="stocks item",
            )
            detail = row.get("koreanMarketDetail")
            if detail is not None:
                detail_object = _validate_object(
                    detail,
                    allowed=_KR_MARKET_DETAIL_FIELDS,
                    label="stocks.koreanMarketDetail",
                )
                _validate_scalar_values(
                    detail_object,
                    nested_fields=frozenset(),
                    label="stocks.koreanMarketDetail",
                )
        return
    calendar = _validate_object(result, allowed=_KR_CALENDAR_FIELDS, label="market-calendar-kr")
    for day_key, day_value in calendar.items():
        day = _validate_object(
            day_value,
            allowed=_KR_MARKET_DAY_FIELDS,
            label=f"market-calendar-kr.{day_key}",
        )
        _validate_scalar_values(
            day,
            nested_fields=frozenset({"integrated"}),
            label=f"market-calendar-kr.{day_key}",
        )
        integrated = day.get("integrated")
        if integrated is None:
            continue
        sessions = _validate_object(
            integrated,
            allowed=_INTEGRATED_HOUR_FIELDS,
            label=f"market-calendar-kr.{day_key}.integrated",
        )
        for session_key, session_value in sessions.items():
            if session_value is not None:
                session = _validate_object(
                    session_value,
                    allowed=_MARKET_SESSION_FIELDS,
                    label=f"market-calendar-kr.{day_key}.integrated.{session_key}",
                )
                _validate_scalar_values(
                    session,
                    nested_fields=frozenset(),
                    label=f"market-calendar-kr.{day_key}.integrated.{session_key}",
                )


def _validate_object_list(
    value: object,
    *,
    allowed: frozenset[str],
    label: str,
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise RuntimeError(f"Toss OpenAPI {label} result had an unexpected shape.")
    return [_validate_object(item, allowed=allowed, label=f"{label} item") for item in value]


def _validate_object(
    value: object,
    *,
    allowed: frozenset[str],
    label: str,
    report_unknown_fields: bool = False,
) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RuntimeError(f"Toss OpenAPI {label} result had an unexpected shape.")
    unknown = set(value).difference(allowed)
    if unknown:
        if report_unknown_fields:
            field_names = ", ".join(sorted(unknown))
            raise RuntimeError(f"Toss OpenAPI {label} result included unexpected fields: {field_names}.")
        raise RuntimeError(f"Toss OpenAPI {label} result included unexpected fields.")
    return value


def _validate_scalar_values(
    value: dict[str, object],
    *,
    nested_fields: frozenset[str],
    label: str,
) -> None:
    if any(isinstance(item, (dict, list)) for key, item in value.items() if key not in nested_fields):
        raise RuntimeError(f"Toss OpenAPI {label} result included unexpected nested content.")


def _validate_official_base_url(base_url: str) -> None:
    if base_url.rstrip("/") != TOSS_OPENAPI_BASE_URL:
        raise TossOpenApiSafetyError(
            "Live Toss OpenAPI probes may send credentials only to the official HTTPS origin."
        )


def _open_json(
    http_request: request.Request,
    *,
    timeout_seconds: float,
    urlopen: Callable[..., object],
    action: str,
) -> dict[str, object]:
    try:
        with urlopen(http_request, timeout=timeout_seconds) as response:
            return _decode_json_response(response, action=action)
    except error.HTTPError as exc:
        raise _safe_http_error(exc, action=action) from None
    except (error.URLError, TimeoutError, OSError):
        raise RuntimeError(f"Toss OpenAPI {action} failed (transport error).") from None


def _decode_json_response(response: object, *, action: str) -> dict[str, object]:
    try:
        body = response.read(TOSS_OPENAPI_MAX_RESPONSE_BYTES + 1)
        if len(body) > TOSS_OPENAPI_MAX_RESPONSE_BYTES:
            raise RuntimeError(f"Toss OpenAPI {action} response exceeded the lab size limit.")
        payload = json.loads(body.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError(f"Toss OpenAPI {action} returned invalid JSON.") from None
    if not isinstance(payload, dict):
        raise RuntimeError(f"Toss OpenAPI {action} returned an unexpected JSON shape.")
    return payload


def _read_rate_limit_headers(headers: object) -> dict[str, str]:
    try:
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
    except AttributeError:
        return {}
    values: dict[str, str] = {}
    for output_key, header_name in (
        ("limit", "x-ratelimit-limit"),
        ("remaining", "x-ratelimit-remaining"),
        ("reset", "x-ratelimit-reset"),
        ("retry_after", "retry-after"),
    ):
        if header_name in normalized:
            values[output_key] = normalized[header_name]
    return values


def _safe_http_error(exc: error.HTTPError, *, action: str) -> TossOpenApiHttpError:
    provider_code = None
    try:
        body = exc.read(8192)
        payload = json.loads(body.decode("utf-8"))
        if isinstance(payload, dict):
            raw_code = payload.get("code")
            nested_error = payload.get("error")
            if not isinstance(raw_code, str) and isinstance(nested_error, str):
                raw_code = nested_error
            if not isinstance(raw_code, str) and isinstance(nested_error, dict):
                raw_code = nested_error.get("code")
            if isinstance(raw_code, str) and len(raw_code) <= 100:
                provider_code = raw_code
    except (AttributeError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    retry_after = _read_rate_limit_headers(getattr(exc, "headers", {})).get("retry_after")
    return TossOpenApiHttpError(
        f"Toss OpenAPI {action} failed (HTTP {exc.code}).",
        status_code=exc.code,
        provider_code=provider_code,
        retry_after=retry_after,
    )
