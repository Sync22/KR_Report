from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import date, datetime

from stock_monitor.fetch.toss_openapi import (
    TossAccessToken,
    TossOpenApiLabConfig,
    TossOpenApiSafetyError,
    TossReadonlyEndpoint,
    TossReadonlyResponse,
    fetch_toss_readonly_endpoint,
    issue_toss_access_token,
    resolve_toss_market_context_endpoint,
    resolve_toss_readonly_endpoint,
)


def _project_market_investor_flow_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, dict):
        return None
    projected: dict[str, object] = {
        key: record[key]
        for key in ("date", "updatedAt")
        if key in record
    }
    for investor in ("individual", "foreigner", "institution", "otherCorporation"):
        amount = record.get(investor)
        if isinstance(amount, dict):
            projected[investor] = {
                key: amount[key]
                for key in ("buyAmount", "sellAmount")
                if key in amount
            }
    return projected


def _project_market_price_changes(
    *,
    market_prices: object,
    candle_results: dict[str, object],
    reference_date: date,
) -> dict[str, dict[str, object]]:
    prices = {
        str(item.get("symbol") or "").strip(): item.get("lastPrice")
        for item in market_prices
        if isinstance(item, dict) and str(item.get("symbol") or "").strip()
    } if isinstance(market_prices, list) else {}
    changes: dict[str, dict[str, object]] = {}
    for symbol, result in candle_results.items():
        page = result if isinstance(result, dict) else {}
        candles = page.get("candles") if isinstance(page.get("candles"), list) else []
        prior = max(
            (
                item
                for item in candles
                if isinstance(item, dict)
                and isinstance(item.get("timestamp"), str)
                and item["timestamp"][:10] < reference_date.isoformat()
            ),
            key=lambda item: str(item["timestamp"]),
            default=None,
        )
        if prior is None:
            continue
        try:
            base_close = float(str(prior.get("closePrice")))
            current_price = float(str(prices.get(symbol)))
        except (TypeError, ValueError):
            continue
        if base_close <= 0:
            continue
        changes[symbol] = {
            "base_date": str(prior["timestamp"])[:10],
            "base_close": str(prior.get("closePrice")),
            "change_rate": (current_price - base_close) / base_close,
        }
    return changes


class TossPriorityQuoteProvider:
    """Read-only Toss quote cache for web-view priority candidates."""

    def __init__(
        self,
        *,
        config: TossOpenApiLabConfig,
        endpoint: TossReadonlyEndpoint | None = None,
        issue_token: Callable[..., TossAccessToken] = issue_toss_access_token,
        fetch_quotes: Callable[..., TossReadonlyResponse] = fetch_toss_readonly_endpoint,
        cache_ttl_seconds: float = 30.0,
        stale_ttl_seconds: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._endpoint = endpoint or resolve_toss_readonly_endpoint("prices")
        self._issue_token = issue_token
        self._fetch_quotes = fetch_quotes
        self._cache_ttl_seconds = cache_ttl_seconds
        self._stale_ttl_seconds = stale_ttl_seconds
        self._clock = clock
        self._token: TossAccessToken | None = None
        self._automatic_reissue_used = False
        self._token_lock = threading.Lock()
        self._cache: dict[tuple[str, tuple[str, ...], bool], tuple[float, dict[str, object]]] = {}
        self._inflight: dict[tuple[str, tuple[str, ...], bool], threading.Event] = {}
        self._cache_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._config.live_enabled and self._config.client_id and self._config.client_secret)

    def get_quotes(
        self,
        *,
        priority_date: date,
        symbols: tuple[str, ...],
        include_investor_trading: bool = False,
    ) -> dict[str, object]:
        normalized_symbols = tuple(symbol.strip() for symbol in symbols if symbol.strip())
        if not self.configured:
            return self._disabled_payload(priority_date=priority_date, symbols=normalized_symbols)
        if not normalized_symbols:
            return self._empty_payload(priority_date=priority_date)

        cache_key = (priority_date.isoformat(), normalized_symbols, include_investor_trading)
        now_monotonic = self._clock()
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and now_monotonic - cached[0] <= self._cache_ttl_seconds:
                return {**cached[1], "cache": "hit"}
            inflight = self._inflight.get(cache_key)
            if inflight is None:
                inflight = threading.Event()
                self._inflight[cache_key] = inflight
                owns_request = True
            else:
                owns_request = False

        if not owns_request:
            inflight.wait(timeout=max(self._config.timeout_seconds * 4 + 1.0, 1.0))
            with self._cache_lock:
                shared = self._cache.get(cache_key)
            if shared:
                age = self._clock() - shared[0]
                if age <= self._cache_ttl_seconds:
                    return {**shared[1], "cache": "shared"}
                if age <= self._stale_ttl_seconds:
                    return {**shared[1], "cache": "stale", "stale_reason": "upstream_unavailable"}
            raise RuntimeError("Toss priority quote request failed.")

        started = time.perf_counter()
        try:
            response = self._fetch_with_token_recovery(normalized_symbols)
            investor_trading = {
                "reference_date": priority_date.isoformat(),
                "available": False,
                "items": [],
            }
            if include_investor_trading:
                try:
                    investor_trading = self._fetch_priority_investor_trading(
                        priority_date=priority_date,
                        symbols=normalized_symbols,
                    )
                except RuntimeError:
                    pass
            payload: dict[str, object] = {
                "surface": "web-view-toss-priority-quotes",
                "read_only": True,
                "configured": True,
                "live_fetch": True,
                "writes_db": False,
                "sends_telegram": False,
                "registers_scheduler": False,
                "affects_ordering": False,
                "priority_date": priority_date.isoformat(),
                "symbols": list(normalized_symbols),
                "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "rate_limit": response.rate_limit,
                "quotes": response.result,
                "investor_trading": investor_trading,
                "cache": "miss",
            }
            with self._cache_lock:
                self._cache[cache_key] = (self._clock(), payload)
            return payload
        except RuntimeError:
            with self._cache_lock:
                stale = self._cache.get(cache_key)
            if stale and self._clock() - stale[0] <= self._stale_ttl_seconds:
                return {**stale[1], "cache": "stale", "stale_reason": "upstream_unavailable"}
            raise
        finally:
            with self._cache_lock:
                event = self._inflight.pop(cache_key, None)
                if event is not None:
                    event.set()

    def _disabled_payload(self, *, priority_date: date, symbols: tuple[str, ...]) -> dict[str, object]:
        return {
            "surface": "web-view-toss-priority-quotes",
            "read_only": True,
            "configured": False,
            "live_fetch": False,
            "writes_db": False,
            "sends_telegram": False,
            "registers_scheduler": False,
            "affects_ordering": False,
            "priority_date": priority_date.isoformat(),
            "symbols": list(symbols),
            "quotes": [],
            "investor_trading": {
                "reference_date": priority_date.isoformat(),
                "available": False,
                "items": [],
            },
            "cache": "disabled",
            "reason": "not_configured",
        }

    def get_market_context(
        self,
        *,
        reference_date: date,
        priority_symbols: tuple[str, ...],
    ) -> dict[str, object]:
        normalized_symbols = tuple(dict.fromkeys(symbol.strip() for symbol in priority_symbols if symbol.strip()))[:2]
        if not self.configured:
            return self._disabled_market_context(reference_date=reference_date, priority_symbols=normalized_symbols)

        cache_key = (f"market-context:{reference_date.isoformat()}", normalized_symbols)
        now_monotonic = self._clock()
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and now_monotonic - cached[0] <= self._cache_ttl_seconds:
                return {**cached[1], "cache": "hit"}
            inflight = self._inflight.get(cache_key)
            if inflight is None:
                inflight = threading.Event()
                self._inflight[cache_key] = inflight
                owns_request = True
            else:
                owns_request = False

        if not owns_request:
            inflight.wait(timeout=max(self._config.timeout_seconds * 4 + 1.0, 1.0))
            with self._cache_lock:
                shared = self._cache.get(cache_key)
            if shared:
                age = self._clock() - shared[0]
                if age <= self._cache_ttl_seconds:
                    return {**shared[1], "cache": "shared"}
                if age <= self._stale_ttl_seconds:
                    return {**shared[1], "cache": "stale", "stale_reason": "upstream_unavailable"}
            raise RuntimeError("Toss market-context request failed.")

        started = time.perf_counter()
        try:
            ranking_endpoint = resolve_toss_market_context_endpoint("ranking-kr-top20")
            ranking_response = self._fetch_endpoint_with_token_recovery(
                endpoint=ranking_endpoint,
                params=dict(ranking_endpoint.fixed_params),
            )
            price_endpoint = resolve_toss_market_context_endpoint("market-indicator-prices")
            price_response = self._fetch_endpoint_with_token_recovery(
                endpoint=price_endpoint,
                params=dict(price_endpoint.fixed_params),
            )
            candle_results: dict[str, object] = {}
            investor_flow: dict[str, object] = {}
            rate_limit = {
                ranking_endpoint.key: ranking_response.rate_limit,
                price_endpoint.key: price_response.rate_limit,
            }
            for market, endpoint_key in (
                ("KOSPI", "market-indicator-kospi-daily-candles"),
                ("KOSDAQ", "market-indicator-kosdaq-daily-candles"),
            ):
                endpoint = resolve_toss_market_context_endpoint(endpoint_key)
                response = self._fetch_endpoint_with_token_recovery(
                    endpoint=endpoint,
                    params=dict(endpoint.fixed_params),
                )
                candle_results[market] = response.result
                rate_limit[endpoint.key] = response.rate_limit
            for market, endpoint_key in (("KOSPI", "market-investor-kospi"), ("KOSDAQ", "market-investor-kosdaq")):
                endpoint = resolve_toss_market_context_endpoint(endpoint_key)
                response = self._fetch_endpoint_with_token_recovery(
                    endpoint=endpoint,
                    params={**dict(endpoint.fixed_params), "until": reference_date.isoformat()},
                )
                result = response.result if isinstance(response.result, dict) else {}
                records = result.get("records") if isinstance(result.get("records"), list) else []
                record = next(
                    (
                        item
                        for item in records
                        if isinstance(item, dict) and item.get("date") == reference_date.isoformat()
                    ),
                    None,
                )
                investor_flow[market] = _project_market_investor_flow_record(record)
                rate_limit[endpoint.key] = response.rate_limit

            ranking_result = ranking_response.result if isinstance(ranking_response.result, dict) else {}
            rankings = ranking_result.get("rankings") if isinstance(ranking_result.get("rankings"), list) else []
            ranking_symbols = tuple(
                str(item.get("symbol") or "").strip()
                for item in rankings
                if isinstance(item, dict) and str(item.get("symbol") or "").strip()
            )
            stock_names: dict[str, str] = {}
            etf_symbols: list[str] = []
            if ranking_symbols:
                try:
                    stock_endpoint = resolve_toss_market_context_endpoint("market-ranking-stocks")
                    stock_response = self._fetch_endpoint_with_token_recovery(
                        endpoint=stock_endpoint,
                        params={"symbols": ",".join(ranking_symbols)},
                    )
                    rate_limit[stock_endpoint.key] = stock_response.rate_limit
                    stock_names = {
                        str(item.get("symbol") or "").strip(): str(item.get("name") or "").strip()
                        for item in stock_response.result
                        if isinstance(item, dict)
                        and str(item.get("symbol") or "").strip()
                        and str(item.get("name") or "").strip()
                    }
                    etf_symbols = [
                        str(item.get("symbol") or "").strip()
                        for item in stock_response.result
                        if isinstance(item, dict)
                        and str(item.get("symbol") or "").strip()
                        and str(item.get("securityType") or "").upper() == "ETF"
                    ]
                except RuntimeError:
                    pass
            market_prices = price_response.result if isinstance(price_response.result, list) else []
            ranked_symbols = {
                str(item.get("symbol") or "").strip()
                for item in rankings
                if isinstance(item, dict) and str(item.get("symbol") or "").strip()
            }
            payload: dict[str, object] = {
                "surface": "toss-market-context",
                "read_only": True,
                "configured": True,
                "live_fetch": True,
                "writes_db": False,
                "sends_telegram": False,
                "registers_scheduler": False,
                "affects_ordering": False,
                "reference_date": reference_date.isoformat(),
                "ranked_at": ranking_result.get("rankedAt"),
                "rankings": rankings,
                "stock_names": stock_names,
                "etf_symbols": etf_symbols,
                "market_prices": market_prices,
                "market_price_changes": _project_market_price_changes(
                    market_prices=market_prices,
                    candle_results=candle_results,
                    reference_date=reference_date,
                ),
                "priority_overlap_symbols": [symbol for symbol in normalized_symbols if symbol in ranked_symbols],
                "investor_flow": investor_flow,
                "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "rate_limit": rate_limit,
                "cache": "miss",
            }
            with self._cache_lock:
                self._cache[cache_key] = (self._clock(), payload)
            return payload
        except RuntimeError:
            with self._cache_lock:
                stale = self._cache.get(cache_key)
            if stale and self._clock() - stale[0] <= self._stale_ttl_seconds:
                return {**stale[1], "cache": "stale", "stale_reason": "upstream_unavailable"}
            raise
        finally:
            with self._cache_lock:
                event = self._inflight.pop(cache_key, None)
                if event is not None:
                    event.set()

    def get_market_ranking(self) -> dict[str, object]:
        if not self.configured:
            return {
                "surface": "toss-market-ranking",
                "read_only": True,
                "configured": False,
                "live_fetch": False,
                "ranked_at": None,
                "rankings": [],
                "rate_limit": None,
                "reason": "not_configured",
            }
        started = time.perf_counter()
        endpoint = resolve_toss_market_context_endpoint("ranking-kr-top20")
        response = self._fetch_endpoint_with_token_recovery(
            endpoint=endpoint,
            params=dict(endpoint.fixed_params),
        )
        result = response.result if isinstance(response.result, dict) else {}
        rankings = result.get("rankings") if isinstance(result.get("rankings"), list) else []
        return {
            "surface": "toss-market-ranking",
            "read_only": True,
            "configured": True,
            "live_fetch": True,
            "ranked_at": result.get("rankedAt"),
            "rankings": rankings,
            "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "rate_limit": response.rate_limit,
        }

    def _empty_payload(self, *, priority_date: date) -> dict[str, object]:
        return {
            "surface": "web-view-toss-priority-quotes",
            "read_only": True,
            "configured": True,
            "live_fetch": False,
            "writes_db": False,
            "sends_telegram": False,
            "registers_scheduler": False,
            "affects_ordering": False,
            "priority_date": priority_date.isoformat(),
            "symbols": [],
            "quotes": [],
            "investor_trading": {
                "reference_date": priority_date.isoformat(),
                "available": False,
                "items": [],
            },
            "cache": "empty",
            "reason": "no_priority_symbols",
        }

    def _disabled_market_context(
        self,
        *,
        reference_date: date,
        priority_symbols: tuple[str, ...],
    ) -> dict[str, object]:
        return {
            "surface": "toss-market-context",
            "read_only": True,
            "configured": False,
            "live_fetch": False,
            "writes_db": False,
            "sends_telegram": False,
            "registers_scheduler": False,
            "affects_ordering": False,
            "reference_date": reference_date.isoformat(),
            "ranked_at": None,
            "rankings": [],
            "market_prices": [],
            "priority_overlap_symbols": [],
            "investor_flow": {"KOSPI": None, "KOSDAQ": None},
            "priority_symbols": list(priority_symbols),
            "cache": "disabled",
            "reason": "not_configured",
        }

    def _fetch_with_token_recovery(self, symbols: tuple[str, ...]) -> TossReadonlyResponse:
        return self._fetch_endpoint_with_token_recovery(
            endpoint=self._endpoint,
            params={"symbols": ",".join(symbols)},
        )

    def _fetch_priority_investor_trading(
        self,
        *,
        priority_date: date,
        symbols: tuple[str, ...],
    ) -> dict[str, object]:
        endpoint = resolve_toss_market_context_endpoint("priority-investor-trading")
        items: list[dict[str, object]] = []
        for symbol in symbols:
            response = self._fetch_endpoint_with_token_recovery(
                endpoint=endpoint,
                params={"symbol": symbol, "count": "1", "until": priority_date.isoformat()},
            )
            result = response.result if isinstance(response.result, dict) else {}
            records = result.get("records") if isinstance(result.get("records"), list) else []
            record = next(
                (
                    item
                    for item in records
                    if isinstance(item, dict)
                    and item.get("date") == priority_date.isoformat()
                    and isinstance(item.get("updatedAt"), str)
                ),
                None,
            )
            if record is None:
                continue
            items.append(
                {
                    "symbol": symbol,
                    "business_date": priority_date.isoformat(),
                    "updated_at": record["updatedAt"],
                    "foreigner_net_buy_volume": _nested_int(record.get("foreigner"), "netBuyVolume"),
                    "institution_net_buy_volume": _nested_int(record.get("institution"), "netBuyVolume"),
                }
            )
        return {
            "reference_date": priority_date.isoformat(),
            "available": bool(items),
            "items": items,
        }

    def _fetch_endpoint_with_token_recovery(
        self,
        *,
        endpoint: TossReadonlyEndpoint,
        params: dict[str, str],
    ) -> TossReadonlyResponse:
        token = self._get_token()
        try:
            return self._fetch_endpoint(token, endpoint=endpoint, params=params)
        except RuntimeError as exc:
            if getattr(exc, "status_code", None) != 401:
                raise
        return self._fetch_endpoint(self._reissue_token_once(failed_token=token), endpoint=endpoint, params=params)

    def _get_token(self) -> TossAccessToken:
        with self._token_lock:
            if self._token is None:
                self._token = self._issue_token(
                    base_url=self._config.base_url,
                    client_id=self._config.client_id or "",
                    client_secret=self._config.client_secret or "",
                    timeout_seconds=self._config.timeout_seconds,
                    live_enabled=self._config.live_enabled,
                    confirm_token_reissue=True,
                )
            return self._token

    def _reissue_token_once(self, *, failed_token: TossAccessToken) -> TossAccessToken:
        with self._token_lock:
            if self._token is not None and self._token is not failed_token:
                return self._token
            if self._automatic_reissue_used:
                raise TossOpenApiSafetyError("Toss automatic token reissue budget is exhausted.")
            self._automatic_reissue_used = True
            self._token = self._issue_token(
                base_url=self._config.base_url,
                client_id=self._config.client_id or "",
                client_secret=self._config.client_secret or "",
                timeout_seconds=self._config.timeout_seconds,
                live_enabled=self._config.live_enabled,
                confirm_token_reissue=True,
            )
            return self._token

    def _fetch(self, token: TossAccessToken, symbols: tuple[str, ...]) -> TossReadonlyResponse:
        return self._fetch_endpoint(token, endpoint=self._endpoint, params={"symbols": ",".join(symbols)})

    def _fetch_endpoint(
        self,
        token: TossAccessToken,
        *,
        endpoint: TossReadonlyEndpoint,
        params: dict[str, str],
    ) -> TossReadonlyResponse:
        return self._fetch_quotes(
            base_url=self._config.base_url,
            access_token=token.access_token,
            endpoint=endpoint,
            params=params,
            timeout_seconds=self._config.timeout_seconds,
            live_enabled=True,
        )


def _nested_int(value: object, key: str) -> int | None:
    if not isinstance(value, dict):
        return None
    try:
        return int(str(value.get(key)))
    except (TypeError, ValueError):
        return None
