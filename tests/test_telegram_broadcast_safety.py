from __future__ import annotations

from datetime import date, datetime

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.notify import telegram


def _config_and_repository(tmp_path, monkeypatch) -> tuple[RuntimeConfig, StockMonitorRepository]:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    return config, repository


def test_telegram_transport_error_is_safe_and_marks_send_as_ambiguous(monkeypatch) -> None:
    def fake_urlopen(_request, timeout):  # noqa: ARG001
        raise telegram.error.URLError(OSError("https://api.telegram.org/botsecret-token/sendMessage timed out"))

    monkeypatch.setattr(telegram.request, "urlopen", fake_urlopen)

    with pytest.raises(telegram.TelegramRequestError) as captured:
        telegram.send_telegram_message(
            "secret-token",
            "chat-1",
            "hello",
            max_retries=1,
        )

    assert captured.value.ambiguous is True
    assert "secret-token" not in str(captured.value)
    assert "api.telegram.org" not in str(captured.value)


def test_ambiguous_daily_summary_is_held_and_not_sent_again(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    sends: list[dict[str, object]] = []

    def ambiguous_send(*_args, **kwargs):
        sends.append(kwargs)
        raise telegram.TelegramRequestError("Telegram sendMessage", 1, error_kind="TimeoutError", ambiguous=True)

    monkeypatch.setattr(cli_module, "send_telegram_message", ambiguous_send)

    with pytest.raises(telegram.TelegramRequestError):
        cli_module._send_production_daily_summary_fragments(
            config,
            repository,
            business_date=date(2026, 4, 24),
            messages=["daily summary"],
            effective_min_mentions=1,
            require_target_price=False,
        )

    with repository.connect() as connection:
        run = connection.execute(
            "SELECT run_id, status FROM daily_summary_delivery_runs WHERE business_date = ?",
            ("2026-04-24",),
        ).fetchone()
        fragment = connection.execute(
            "SELECT status FROM daily_summary_delivery_fragments WHERE run_id = ?",
            (run["run_id"],),
        ).fetchone()

    assert dict(run)["status"] == "ambiguous"
    assert fragment["status"] == "ambiguous"
    assert repository.list_pending_daily_summary_fragments(run["run_id"]) == []
    assert sends[0]["max_retries"] == 1
    events = repository.list_recent_operation_events(limit=1)
    trace = cli_module._build_telegram_timeout_trace(events[0].event_time, events)
    assert trace["ambiguous_failure_count"] == 1
    assert trace["latest"]["status"] == "ambiguous"

    with pytest.raises(RuntimeError, match="operator review is required"):
        cli_module._send_production_daily_summary_fragments(
            config,
            repository,
            business_date=date(2026, 4, 24),
            messages=["daily summary changed"],
            effective_min_mentions=1,
            require_target_price=False,
        )

    assert len(sends) == 1

    def reviewed_retry(*_args, **kwargs):
        sends.append(kwargs)
        return "reviewed-message"

    monkeypatch.setattr(cli_module, "send_telegram_message", reviewed_retry)
    message_ids = cli_module._send_production_daily_summary_fragments(
        config,
        repository,
        business_date=date(2026, 4, 24),
        messages=["daily summary changed"],
        effective_min_mentions=1,
        require_target_price=False,
        allow_ambiguous_repeat=True,
    )
    assert message_ids == ["reviewed-message"]
    assert len(sends) == 2
    with repository.connect() as connection:
        run_statuses = connection.execute(
            "SELECT status FROM daily_summary_delivery_runs WHERE business_date = ? ORDER BY started_at",
            ("2026-04-24",),
        ).fetchall()
    assert [row["status"] for row in run_statuses] == ["superseded", "sent"]


def test_ambiguous_intraday_batch_is_not_selected_for_automatic_retry(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import Opinion, Report

    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="실적 전망",
                broker_name="NH",
                published_at=datetime(2026, 4, 24, 9, 0),
                collected_at=datetime(2026, 4, 24, 9, 30),
                business_date=date(2026, 4, 24),
                target_price_raw="92000",
                target_price_value=92_000,
                opinion_raw="매수",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://example.test/report/1",
                source_id="1",
                identity_key="report-1",
            )
        ],
        queue_intraday_alerts=True,
    )
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    sends: list[dict[str, object]] = []

    def ambiguous_send(*_args, **kwargs):
        sends.append(kwargs)
        raise telegram.TelegramRequestError("Telegram sendMessage", 1, error_kind="TimeoutError", ambiguous=True)

    monkeypatch.setattr(cli_module, "send_telegram_message", ambiguous_send)

    with pytest.raises(RuntimeError, match="delivery failed"):
        cli_module._run_process_intraday_alerts(config, repository, dry_run=False)

    assert sends[0]["max_retries"] == 1
    assert repository.list_pending_intraday_alert_batches() == []
    assert repository.list_intraday_alert_batch_summaries(date(2026, 4, 24))[0].status == "ambiguous"
    assert cli_module._live_event_evidence_status(repository.list_recent_operation_events(limit=1)[0]) == "attention"

    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "reviewed-message")
    assert cli_module._run_process_intraday_alerts(config, repository, dry_run=False, retry_ambiguous=True) == 1
    assert repository.list_intraday_alert_batch_summaries(date(2026, 4, 24))[0].status == "sent"


def test_ambiguous_scheduled_intraday_batch_is_held(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import Opinion, Report

    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="실적 전망",
                broker_name="NH",
                published_at=datetime(2026, 4, 24, 9, 0),
                collected_at=datetime(2026, 4, 24, 9, 30),
                business_date=date(2026, 4, 24),
                target_price_raw="92000",
                target_price_value=92_000,
                opinion_raw="매수",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://example.test/report/1",
                source_id="1",
                identity_key="report-1",
            )
        ],
        queue_intraday_alerts=True,
    )
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    sends: list[dict[str, object]] = []

    def ambiguous_send(*_args, **kwargs):
        sends.append(kwargs)
        raise telegram.TelegramRequestError("Telegram sendMessage", 1, error_kind="HTTPError 502", ambiguous=True)

    monkeypatch.setattr(cli_module, "send_telegram_message", ambiguous_send)

    with pytest.raises(RuntimeError, match="Hourly intraday briefing delivery failed"):
        cli_module._run_scheduled_intraday_briefing(
            config,
            repository,
            scheduled_run_at=datetime(2026, 4, 24, 8, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
            dry_run=False,
        )

    assert sends[0]["max_retries"] == 1
    assert repository.list_pending_intraday_alert_batches() == []
    assert repository.list_intraday_alert_batch_summaries(date(2026, 4, 24))[0].status == "ambiguous"


def test_market_briefing_ambiguous_send_is_recorded_for_guard(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    sends: list[dict[str, object]] = []

    def ambiguous_send(*_args, **kwargs):
        sends.append(kwargs)
        raise telegram.TelegramRequestError("Telegram sendMessage", 1, error_kind="TimeoutError", ambiguous=True)

    monkeypatch.setattr(cli_module, "send_telegram_message", ambiguous_send)

    with pytest.raises(telegram.TelegramRequestError):
        cli_module._send_market_briefing_message(
            config,
            repository,
            business_date=date(2026, 4, 24),
            message="market briefing",
            source="scheduled:lunch",
            channel="telegram_market_briefing:lunch",
        )

    assert sends[0]["max_retries"] == 1
    assert repository.has_delivery_status(date(2026, 4, 24), "telegram_market_briefing:lunch", status="ambiguous")
    assert repository.has_latest_delivery_status(date(2026, 4, 24), "telegram_market_briefing:lunch", status="ambiguous")
    assert cli_module._live_event_evidence_status(repository.list_recent_operation_events(limit=1)[0]) == "attention"


def test_scheduled_intraday_with_no_new_reports_does_not_send_empty_broadcast(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no empty broadcast")),
    )

    result = cli_module._run_scheduled_intraday_briefing(
        config,
        repository,
        scheduled_run_at=datetime(2026, 4, 24, 9, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
        dry_run=False,
    )

    assert result == 0
    assert repository.list_recent_deliveries(limit=10) == []
