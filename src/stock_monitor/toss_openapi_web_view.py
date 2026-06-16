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
    resolve_toss_readonly_endpoint,
)


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
        self._cache: dict[tuple[str, tuple[str, ...]], tuple[float, dict[str, object]]] = {}
        self._inflight: dict[tuple[str, tuple[str, ...]], threading.Event] = {}
        self._cache_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._config.live_enabled and self._config.client_id and self._config.client_secret)

    def get_quotes(self, *, priority_date: date, symbols: tuple[str, ...]) -> dict[str, object]:
        normalized_symbols = tuple(symbol.strip() for symbol in symbols if symbol.strip())
        if not self.configured:
            return self._disabled_payload(priority_date=priority_date, symbols=normalized_symbols)
        if not normalized_symbols:
            return self._empty_payload(priority_date=priority_date)

        cache_key = (priority_date.isoformat(), normalized_symbols)
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
            "cache": "disabled",
            "reason": "not_configured",
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
            "cache": "empty",
            "reason": "no_priority_symbols",
        }

    def _fetch_with_token_recovery(self, symbols: tuple[str, ...]) -> TossReadonlyResponse:
        token = self._get_token()
        try:
            return self._fetch(token, symbols)
        except RuntimeError as exc:
            if getattr(exc, "status_code", None) != 401:
                raise
        return self._fetch(self._reissue_token_once(failed_token=token), symbols)

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
        return self._fetch_quotes(
            base_url=self._config.base_url,
            access_token=token.access_token,
            endpoint=self._endpoint,
            params={"symbols": ",".join(symbols)},
            timeout_seconds=self._config.timeout_seconds,
            live_enabled=True,
        )
