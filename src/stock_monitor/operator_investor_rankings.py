from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from threading import Lock
from time import monotonic
from zoneinfo import ZoneInfo

from stock_monitor.fetch import toss_openapi


INVESTOR_RANKING_CANDIDATE_LIMIT = 10
_INVESTOR_LABELS = {"foreigner": "외국인", "institution": "기관", "individual": "개인"}
_SEOUL = ZoneInfo("Asia/Seoul")


class InvestorRankingsUnavailable(RuntimeError):
    def __init__(self, code: str, status: HTTPStatus, *, retry_after: int | None = None):
        super().__init__(code)
        self.status = status
        self.retry_after = retry_after


class TossInvestorRankingsLookup:
    """One operator session's bounded, explicitly authorized Toss lookup."""

    def __init__(
        self,
        config: toss_openapi.TossOpenApiLabConfig,
        *,
        confirm_token_reissue: bool,
        urlopen: Callable[..., object] = toss_openapi._urlopen_no_redirect,
        clock: Callable[[], float] = monotonic,
    ):
        if not confirm_token_reissue or not config.live_enabled:
            raise ValueError("Investor rankings require live enablement and token-reissue confirmation.")
        if not config.client_id or not config.client_secret:
            raise ValueError("Toss investor rankings credentials are not configured.")
        if not math.isfinite(config.timeout_seconds) or config.timeout_seconds <= 0:
            raise ValueError("Toss investor rankings timeout is invalid.")
        if config.base_url.rstrip("/") != toss_openapi.TOSS_OPENAPI_BASE_URL:
            raise ValueError("Toss investor rankings require the official HTTPS origin.")
        self._config = config
        self._timeout = min(config.timeout_seconds, 15.0)
        self._urlopen = urlopen
        self._clock = clock
        self._lock = Lock()
        self._token: toss_openapi.TossAccessToken | None = None
        self._issuance_attempted = False
        self._token_expires_at = 0.0
        self._next_lookup_at = 0.0

    def __call__(self) -> dict[str, toss_openapi.TossInvestorRanking]:
        if not self._lock.acquire(blocking=False):
            raise InvestorRankingsUnavailable("toss_lookup_busy", HTTPStatus.TOO_MANY_REQUESTS)
        try:
            now = self._clock()
            if now < self._next_lookup_at:
                raise InvestorRankingsUnavailable(
                    "toss_rate_limited", HTTPStatus.TOO_MANY_REQUESTS,
                    retry_after=math.ceil(self._next_lookup_at - now),
                )
            self._next_lookup_at = now + 1
            if not self._issuance_attempted:
                # Issuance may have succeeded even if the response was lost.
                self._issuance_attempted = True
                self._token = toss_openapi.issue_toss_access_token(
                    base_url=self._config.base_url,
                    client_id=self._config.client_id,
                    client_secret=self._config.client_secret,
                    timeout_seconds=self._timeout,
                    live_enabled=True,
                    confirm_token_reissue=True,
                    urlopen=self._urlopen,
                )
                self._token_expires_at = now + self._token.expires_in
            if self._token is None or self._clock() >= self._token_expires_at:
                raise InvestorRankingsUnavailable("toss_authentication_failed", HTTPStatus.BAD_GATEWAY)
            return toss_openapi.fetch_toss_investor_rankings(
                base_url=self._config.base_url,
                access_token=self._token.access_token,
                timeout_seconds=self._timeout,
                live_enabled=True,
                urlopen=self._urlopen,
            )
        except toss_openapi.TossOpenApiHttpError as exc:
            if exc.status_code == 401:
                self._token = None
                raise InvestorRankingsUnavailable("toss_authentication_failed", HTTPStatus.BAD_GATEWAY) from None
            if exc.status_code == 403:
                raise InvestorRankingsUnavailable("toss_permission_denied", HTTPStatus.BAD_GATEWAY) from None
            if exc.status_code == 429:
                if self._token is None:
                    # A rate-limit rejection can be retried on the next eligible click.
                    self._issuance_attempted = False
                delay = _retry_delay(exc.retry_after)
                self._next_lookup_at = self._clock() + delay
                raise InvestorRankingsUnavailable(
                    "toss_rate_limited", HTTPStatus.TOO_MANY_REQUESTS, retry_after=delay,
                ) from None
            raise InvestorRankingsUnavailable("toss_api_error", HTTPStatus.BAD_GATEWAY) from None
        except InvestorRankingsUnavailable:
            raise
        except (RuntimeError, OSError, ValueError):
            raise InvestorRankingsUnavailable("toss_api_error", HTTPStatus.BAD_GATEWAY) from None
        finally:
            self._lock.release()


def _retry_delay(value: str | None) -> int:
    if value and re.fullmatch(r"[0-9]{1,10}", value):
        return max(1, int(value))
    if value:
        try:
            until = parsedate_to_datetime(value)
            if until.tzinfo is not None:
                return max(1, math.ceil((until - datetime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            pass
    return 30


def build_investor_rankings_projection(
    business_date: date,
    candidates: list[dict[str, object]],
    rankings: Mapping[str, toss_openapi.TossInvestorRanking],
) -> dict[str, object]:
    source_states = {}
    rankings_by_code: dict[str, list[dict[str, object]]] = {}
    for investor, bucket in rankings.items():
        timestamp = bucket.ranked_at.astimezone(_SEOUL) if bucket.ranked_at is not None else None
        if timestamp is None or not (bucket.net_buy or bucket.net_sell):
            state = "no_data"
        elif timestamp.date() != business_date:
            state = "date_mismatch"
        else:
            state = "same_date"
        freshness = None
        if state == "same_date":
            freshness = (
                "provisional" if investor != "individual" and timestamp.time() < time(15, 30) else "may_update"
            )
            for direction, entries in (("net_buy", bucket.net_buy), ("net_sell", bucket.net_sell)):
                for item in entries:
                    rankings_by_code.setdefault(item.symbol, []).append({
                        "investor": investor,
                        "direction": direction,
                        "rank": item.rank,
                        "amount_krw": item.amount_krw,
                    })
        source_states[investor] = {
            "state": state, "ranked_at": timestamp.isoformat() if timestamp else None, "freshness": freshness,
        }

    matches = []
    for candidate in candidates:
        entries = rankings_by_code.get(candidate["stock_code"])
        if entries:
            matches.append({**candidate, "rankings": entries, "observations": _direction_observations(entries)})

    states = {item["state"] for item in source_states.values()}
    if matches:
        state = "matched"
    elif "same_date" in states:
        state = "no_match"
    elif "date_mismatch" in states:
        state = "date_mismatch"
    else:
        state = "no_data"
    return {
        "source": "toss_openapi",
        "business_date": business_date.isoformat(),
        "state": state,
        "candidate_count": len(candidates),
        "investors": source_states,
        "matches": matches,
    }


def _direction_observations(entries: list[dict[str, object]]) -> list[str]:
    buyers = {item["investor"] for item in entries if item["direction"] == "net_buy"}
    sellers = {item["investor"] for item in entries if item["direction"] == "net_sell"}
    observations = []
    if {"foreigner", "institution"} <= buyers - sellers:
        observations.append("외국인·기관 모두 순매수 상위")
    if buyers - sellers and sellers - buyers:
        buys = "·".join(label for key, label in _INVESTOR_LABELS.items() if key in buyers - sellers)
        sells = "·".join(label for key, label in _INVESTOR_LABELS.items() if key in sellers - buyers)
        observations.append(f"{buys} 순매수 · {sells} 순매도")
    return observations
