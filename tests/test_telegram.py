from __future__ import annotations

import json
from urllib import error

from stock_monitor.notify import telegram


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_send_telegram_message_retries_then_succeeds(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(_request, timeout):  # noqa: ARG001
        calls["count"] += 1
        if calls["count"] < 3:
            raise error.URLError(OSError("timed out"))
        return _FakeResponse({"ok": True, "result": {"message_id": 42}})

    monkeypatch.setattr(telegram.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(telegram.time, "sleep", lambda _seconds: None)

    message_id = telegram.send_telegram_message(
        "token",
        "chat",
        "hello",
        timeout_seconds=1,
        max_retries=3,
        retry_delay_seconds=0,
    )

    assert message_id == "42"
    assert calls["count"] == 3


def test_get_telegram_updates_raises_readable_error_after_retries(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(_request, timeout):  # noqa: ARG001
        calls["count"] += 1
        raise error.URLError(OSError("timed out"))

    monkeypatch.setattr(telegram.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(telegram.time, "sleep", lambda _seconds: None)

    try:
        telegram.get_telegram_updates(
            "token",
            timeout_seconds=1,
            max_retries=2,
            retry_delay_seconds=0,
        )
    except RuntimeError as exc:
        assert "Telegram getUpdates failed after 2 attempts" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert calls["count"] == 2
