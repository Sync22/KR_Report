import io
from urllib import error

import pytest

from stock_monitor.fetch.toss_openapi import (
    TOSS_OPENAPI_BASE_URL,
    TOSS_READONLY_ENDPOINTS,
    TossOpenApiLabConfig,
    TossOpenApiSafetyError,
    TossReadonlyEndpoint,
    _NoRedirectHandler,
    build_toss_readonly_probe_plan,
    fetch_toss_readonly_endpoint,
    issue_toss_access_token,
    resolve_toss_readonly_endpoint,
    run_toss_readonly_probe,
)


class FakeResponse:
    def __init__(self, body: bytes, *, headers: dict[str, str] | None = None) -> None:
        self.body = body
        self.headers = headers or {}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]


def test_toss_lab_config_reads_only_dedicated_env_file(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text(
        "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=wrong-general-env",
        encoding="utf-8",
    )
    (tmp_path / ".env.toss-openapi").write_text(
        "\n".join(
            [
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=client-value",
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET=secret-value",
                "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true",
                "STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS=12",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID",
        "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET",
        "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED",
        "STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    config = TossOpenApiLabConfig.from_env(root_dir=tmp_path)

    assert config.client_id == "client-value"
    assert config.client_secret == "secret-value"
    assert config.live_enabled is True
    assert config.base_url == TOSS_OPENAPI_BASE_URL
    assert config.timeout_seconds == 12


def test_toss_lab_config_does_not_accept_process_env_live_override(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env.toss-openapi").write_text(
        "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=false",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED", "true")

    config = TossOpenApiLabConfig.from_env(root_dir=tmp_path)

    assert config.live_enabled is False


def test_resolve_toss_readonly_endpoint_allows_market_reference_only() -> None:
    assert resolve_toss_readonly_endpoint("stocks").path == "/api/v1/stocks"
    assert resolve_toss_readonly_endpoint("market-calendar-kr").path == "/api/v1/market-calendar/KR"
    assert resolve_toss_readonly_endpoint("prices").path == "/api/v1/prices"

    for forbidden in ("accounts", "holdings", "orders", "buying-power", "commissions"):
        with pytest.raises(TossOpenApiSafetyError, match="not allowed"):
            resolve_toss_readonly_endpoint(forbidden)


def test_toss_readonly_allowlist_is_immutable() -> None:
    with pytest.raises(TypeError):
        TOSS_READONLY_ENDPOINTS["accounts"] = TossReadonlyEndpoint(  # type: ignore[index]
            key="accounts",
            operation_id="getAccounts",
            path="/api/v1/accounts",
            rate_group="ACCOUNT",
        )


def test_toss_http_redirects_are_rejected() -> None:
    handler = _NoRedirectHandler()

    assert handler.redirect_request(None, None, 302, "redirect", {}, "https://example.invalid") is None


def test_toss_sensitive_dataclass_repr_is_redacted(tmp_path) -> None:
    (tmp_path / ".env.toss-openapi").write_text(
        "\n".join(
            [
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=client-value",
                "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET=secret-value",
            ]
        ),
        encoding="utf-8",
    )

    config = TossOpenApiLabConfig.from_env(root_dir=tmp_path)
    token = issue_toss_access_token(
        base_url=TOSS_OPENAPI_BASE_URL,
        client_id="client-value",
        client_secret="secret-value",
        timeout_seconds=12,
        live_enabled=True,
        confirm_token_reissue=True,
        urlopen=lambda *_args, **_kwargs: FakeResponse(
            b'{"access_token":"token-value","token_type":"Bearer","expires_in":86400}'
        ),
    )

    assert "secret-value" not in repr(config)
    assert "client-value" not in repr(config)
    assert "token-value" not in repr(token)


def test_build_toss_readonly_probe_plan_is_no_network_and_top_two_only() -> None:
    plan = build_toss_readonly_probe_plan(endpoint_selector="prices", symbols=("005930", "000660"))

    assert plan["surface"] == "toss-openapi-readonly-probe"
    assert plan["mode"] == "plan"
    assert plan["live_fetch"] is False
    assert plan["reads_secrets"] is False
    assert plan["writes_db"] is False
    assert plan["sends_telegram"] is False
    assert plan["registers_scheduler"] is False
    assert plan["connects_admin_gui"] is False
    assert plan["connects_web_view"] is False
    assert plan["endpoint"] == "prices"
    assert plan["params"] == {"symbols": "005930,000660"}
    assert plan["requires_token_reissue_confirmation"] is True
    assert "account" in plan["forbidden_groups"]
    assert "order" in plan["forbidden_groups"]

    with pytest.raises(TossOpenApiSafetyError, match="at most 2 symbols"):
        build_toss_readonly_probe_plan(
            endpoint_selector="prices",
            symbols=("005930", "000660", "035420"),
        )
    with pytest.raises(TossOpenApiSafetyError, match="six-digit Korean stock codes"):
        build_toss_readonly_probe_plan(endpoint_selector="prices", symbols=("AAPL",))


def test_issue_toss_access_token_posts_form_without_leaking_secret() -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(http_request, timeout: float):  # noqa: ANN001
        seen["url"] = http_request.full_url
        seen["method"] = http_request.get_method()
        seen["headers"] = dict(http_request.header_items())
        seen["body"] = http_request.data.decode("utf-8")
        seen["timeout"] = timeout
        return FakeResponse(b'{"access_token":"token-value","token_type":"Bearer","expires_in":86400}')

    token = issue_toss_access_token(
        base_url=TOSS_OPENAPI_BASE_URL,
        client_id="client-value",
        client_secret="secret-value",
        timeout_seconds=12,
        live_enabled=True,
        confirm_token_reissue=True,
        urlopen=fake_urlopen,
    )

    assert seen["url"] == f"{TOSS_OPENAPI_BASE_URL}/oauth2/token"
    assert seen["method"] == "POST"
    assert seen["headers"]["Content-type"] == "application/x-www-form-urlencoded"
    assert seen["body"] == (
        "grant_type=client_credentials&client_id=client-value&client_secret=secret-value"
    )
    assert token.access_token == "token-value"
    assert token.expires_in == 86400

    def failing_urlopen(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise error.HTTPError(
            f"{TOSS_OPENAPI_BASE_URL}/oauth2/token",
            401,
            "secret-value token-value",
            {},
            None,
        )

    with pytest.raises(RuntimeError) as exc_info:
        issue_toss_access_token(
            base_url=TOSS_OPENAPI_BASE_URL,
            client_id="client-value",
            client_secret="secret-value",
            timeout_seconds=12,
            live_enabled=True,
            confirm_token_reissue=True,
            urlopen=failing_urlopen,
        )

    message = str(exc_info.value)
    assert "secret-value" not in message
    assert "token-value" not in message
    assert "HTTP 401" in message


def test_issue_toss_access_token_accepts_case_insensitive_bearer_type() -> None:
    token = issue_toss_access_token(
        base_url=TOSS_OPENAPI_BASE_URL,
        client_id="client-value",
        client_secret="secret-value",
        timeout_seconds=12,
        live_enabled=True,
        confirm_token_reissue=True,
        urlopen=lambda *_args, **_kwargs: FakeResponse(
            b'{"access_token":"token-value","token_type":"bearer","expires_in":86400}'
        ),
    )

    assert token.access_token == "token-value"


def test_fetch_toss_readonly_endpoint_uses_bearer_without_account_header() -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(http_request, timeout: float):  # noqa: ANN001
        seen["url"] = http_request.full_url
        seen["method"] = http_request.get_method()
        seen["headers"] = dict(http_request.header_items())
        seen["timeout"] = timeout
        return FakeResponse(
            b'{"result":[{"symbol":"005930","lastPrice":"72000","currency":"KRW"}]}',
            headers={
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "9",
                "X-RateLimit-Reset": "1",
            },
        )

    response = fetch_toss_readonly_endpoint(
        base_url=TOSS_OPENAPI_BASE_URL,
        access_token="token-value",
        endpoint=resolve_toss_readonly_endpoint("prices"),
        params={"symbols": "005930"},
        timeout_seconds=12,
        live_enabled=True,
        urlopen=fake_urlopen,
    )

    assert seen["url"] == f"{TOSS_OPENAPI_BASE_URL}/api/v1/prices?symbols=005930"
    assert seen["method"] == "GET"
    assert seen["headers"]["Authorization"] == "Bearer token-value"
    assert "x-tossinvest-account" not in {str(key).lower() for key in seen["headers"]}
    assert response.row_count == 1
    assert response.result[0]["symbol"] == "005930"
    assert response.rate_limit == {"limit": "10", "remaining": "9", "reset": "1"}


def test_fetch_toss_readonly_endpoint_preserves_safe_http_error_metadata() -> None:
    def failing_urlopen(*_args, **_kwargs):
        raise error.HTTPError(
            f"{TOSS_OPENAPI_BASE_URL}/api/v1/prices?symbols=005930",
            429,
            "secret-value token-value",
            {"Retry-After": "3"},
            io.BytesIO(b'{"error":"rate_limited","error_description":"slow down"}'),
        )

    with pytest.raises(RuntimeError) as exc_info:
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=resolve_toss_readonly_endpoint("prices"),
            params={"symbols": "005930"},
            timeout_seconds=12,
            live_enabled=True,
            urlopen=failing_urlopen,
        )

    assert getattr(exc_info.value, "status_code", None) == 429
    assert getattr(exc_info.value, "provider_code", None) == "rate_limited"
    assert getattr(exc_info.value, "retry_after", None) == "3"
    assert "secret-value" not in str(exc_info.value)
    assert "token-value" not in str(exc_info.value)


def test_fetch_toss_readonly_endpoint_rejects_forged_allowlist_entry() -> None:
    forged = TossReadonlyEndpoint(
        key="prices",
        operation_id="getAccounts",
        path="/api/v1/accounts",
        rate_group="ACCOUNT",
    )

    with pytest.raises(TossOpenApiSafetyError, match="fixed Toss read-only endpoint allowlist"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=forged,
            params={},
            timeout_seconds=12,
            live_enabled=True,
        )


def test_fetch_toss_readonly_endpoint_revalidates_top_two_and_query_keys() -> None:
    endpoint = resolve_toss_readonly_endpoint("prices")

    with pytest.raises(TossOpenApiSafetyError, match="at most 2 symbols"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=endpoint,
            params={"symbols": "005930,000660,035420"},
            timeout_seconds=12,
            live_enabled=True,
        )

    with pytest.raises(TossOpenApiSafetyError, match="unsupported query parameters"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=endpoint,
            params={"symbols": "005930", "accountSeq": "1"},
            timeout_seconds=12,
            live_enabled=True,
        )


def test_fetch_toss_readonly_endpoint_rejects_wrong_shape_and_accepts_missing_rate_limit_headers() -> None:
    endpoint = resolve_toss_readonly_endpoint("prices")

    with pytest.raises(RuntimeError, match="unexpected shape"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=endpoint,
            params={"symbols": "005930"},
            timeout_seconds=12,
            live_enabled=True,
            urlopen=lambda *_args, **_kwargs: FakeResponse(
                b'{"result":{"symbol":"005930"}}',
                headers={
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "9",
                    "X-RateLimit-Reset": "1",
                },
            ),
        )

    response = fetch_toss_readonly_endpoint(
        base_url=TOSS_OPENAPI_BASE_URL,
        access_token="token-value",
        endpoint=endpoint,
        params={"symbols": "005930"},
        timeout_seconds=12,
        live_enabled=True,
        urlopen=lambda *_args, **_kwargs: FakeResponse(b'{"result":[]}'),
    )

    assert response.rate_limit == {}


def test_fetch_toss_readonly_endpoint_rejects_oversized_response() -> None:
    endpoint = resolve_toss_readonly_endpoint("prices")

    with pytest.raises(RuntimeError, match="exceeded the lab size limit"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=endpoint,
            params={"symbols": "005930"},
            timeout_seconds=12,
            live_enabled=True,
            urlopen=lambda *_args, **_kwargs: FakeResponse(b"{" + b"x" * 1_048_576),
        )


def test_fetch_toss_readonly_endpoint_rejects_unexpected_sensitive_fields() -> None:
    with pytest.raises(RuntimeError, match="included unexpected fields"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=resolve_toss_readonly_endpoint("prices"),
            params={"symbols": "005930"},
            timeout_seconds=12,
            live_enabled=True,
            urlopen=lambda *_args, **_kwargs: FakeResponse(
                b'{"result":[{"symbol":"005930","lastPrice":"72000","currency":"KRW","accountNo":"123"}]}',
                headers={
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "9",
                    "X-RateLimit-Reset": "1",
                },
            ),
        )

    with pytest.raises(RuntimeError, match="unexpected nested content"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=resolve_toss_readonly_endpoint("prices"),
            params={"symbols": "005930"},
            timeout_seconds=12,
            live_enabled=True,
            urlopen=lambda *_args, **_kwargs: FakeResponse(
                b'{"result":[{"symbol":{"orderId":"123"},"lastPrice":"72000","currency":"KRW"}]}',
                headers={
                    "X-RateLimit-Limit": "10",
                    "X-RateLimit-Remaining": "9",
                    "X-RateLimit-Reset": "1",
                },
            ),
        )


def test_fetch_toss_readonly_endpoint_requires_live_enablement_before_network() -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("network must not be used")

    with pytest.raises(TossOpenApiSafetyError, match="explicit live enablement"):
        fetch_toss_readonly_endpoint(
            base_url=TOSS_OPENAPI_BASE_URL,
            access_token="token-value",
            endpoint=resolve_toss_readonly_endpoint("prices"),
            params={"symbols": "005930"},
            timeout_seconds=12,
            urlopen=fail_if_called,
        )


def test_toss_live_probe_rejects_nonofficial_base_url_and_redacts_output() -> None:
    with pytest.raises(TossOpenApiSafetyError, match="official HTTPS origin"):
        issue_toss_access_token(
            base_url="https://example.invalid",
            client_id="client-value",
            client_secret="secret-value",
            timeout_seconds=12,
            live_enabled=True,
            confirm_token_reissue=True,
        )

    requests: list[object] = []

    def fake_urlopen(http_request, timeout: float):  # noqa: ANN001
        requests.append(http_request)
        if http_request.full_url.endswith("/oauth2/token"):
            return FakeResponse(
                b'{"access_token":"token-value","token_type":"Bearer","expires_in":86400}'
            )
        return FakeResponse(
            (
                b'{"result":[{"symbol":"005930","name":"Samsung","englishName":"Samsung",'
                b'"isinCode":"KR7005930003","market":"KOSPI","securityType":"STOCK",'
                b'"isCommonShare":true,"status":"ACTIVE","currency":"KRW",'
                b'"sharesOutstanding":"5919637922"}]}'
            ),
            headers={
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "9",
                "X-RateLimit-Reset": "1",
            },
        )

    payload = run_toss_readonly_probe(
        base_url=TOSS_OPENAPI_BASE_URL,
        client_id="client-value",
        client_secret="secret-value",
        endpoint_selector="stocks",
        symbols=("005930",),
        timeout_seconds=12,
        live_enabled=True,
        confirm_token_reissue=True,
        urlopen=fake_urlopen,
    )

    assert len(requests) == 2
    assert payload["mode"] == "live"
    assert payload["live_fetch"] is True
    assert payload["writes_db"] is False
    assert payload["token_expires_in"] == 86400
    assert payload["result"][0]["symbol"] == "005930"
    assert "token-value" not in str(payload)
    assert "client-value" not in str(payload)
    assert "secret-value" not in str(payload)


def test_toss_live_probe_requires_direct_call_gates_before_network() -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("network must not be used")

    with pytest.raises(TossOpenApiSafetyError, match="explicit live enablement"):
        run_toss_readonly_probe(
            base_url=TOSS_OPENAPI_BASE_URL,
            client_id="client-value",
            client_secret="secret-value",
            endpoint_selector="stocks",
            symbols=("005930",),
            timeout_seconds=12,
            urlopen=fail_if_called,
        )

    with pytest.raises(TossOpenApiSafetyError, match="token-reissue confirmation"):
        run_toss_readonly_probe(
            base_url=TOSS_OPENAPI_BASE_URL,
            client_id="client-value",
            client_secret="secret-value",
            endpoint_selector="stocks",
            symbols=("005930",),
            timeout_seconds=12,
            live_enabled=True,
            urlopen=fail_if_called,
        )


def test_issue_toss_access_token_requires_direct_call_gates_before_network() -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("network must not be used")

    with pytest.raises(TossOpenApiSafetyError, match="explicit live enablement"):
        issue_toss_access_token(
            base_url=TOSS_OPENAPI_BASE_URL,
            client_id="client-value",
            client_secret="secret-value",
            timeout_seconds=12,
            urlopen=fail_if_called,
        )

    with pytest.raises(TossOpenApiSafetyError, match="token-reissue confirmation"):
        issue_toss_access_token(
            base_url=TOSS_OPENAPI_BASE_URL,
            client_id="client-value",
            client_secret="secret-value",
            timeout_seconds=12,
            live_enabled=True,
            urlopen=fail_if_called,
        )
