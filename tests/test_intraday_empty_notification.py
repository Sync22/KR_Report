from datetime import date, datetime

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import Opinion, Report


def _report(
    *,
    title: str = "recovery visible",
    broker_name: str = "NH",
    source_id: str = "91999",
    identity_key: str = "identity-1",
    target_price_value: int = 92_000,
) -> Report:
    return Report(
        stock_name="Samsung Electronics",
        stock_code="005930",
        title=title,
        broker_name=broker_name,
        published_at=datetime(2026, 4, 24, 9, 0, 0),
        collected_at=datetime(2026, 4, 24, 9, 30, 0),
        business_date=date(2026, 4, 24),
        target_price_raw=str(target_price_value),
        target_price_value=target_price_value,
        opinion_raw="Buy",
        opinion_normalized=Opinion.BUY.value,
        source_url=f"https://stock.naver.com/research/company/{source_id}",
        source_id=source_id,
        identity_key=identity_key,
    )


def _inspection(row_count: int) -> object:
    return type(
        "Inspection",
        (),
        {
            "api_pages_fetched": 1,
            "api_items": [{} for _ in range(row_count)],
            "candidate_rows": [object() for _ in range(row_count)],
        },
    )()


def _config_and_repository(tmp_path, monkeypatch) -> tuple[RuntimeConfig, StockMonitorRepository]:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    return config, repository


def test_manual_poll_sends_intraday_empty_notification_when_no_new_reports(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=False)

    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))

    empty_calls: list[datetime | None] = []
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda _config, _repository, *, polled_at=None, dry_run=False: empty_calls.append(polled_at) or 0,
    )
    process_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda *_args, **_kwargs: process_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=True,
    )

    assert result == 0
    assert len(process_calls) == 1
    assert len(empty_calls) == 1


def test_manual_poll_retries_pending_intraday_batches_before_empty_notification(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=True)

    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))

    process_calls: list[object] = []
    empty_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda _config, _repository, **_kwargs: process_calls.append(_kwargs) or 1,
    )
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda *_args, **_kwargs: empty_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=True,
    )

    assert result == 0
    assert len(process_calls) == 1
    assert not empty_calls


def test_process_intraday_alerts_returns_processed_batch_count(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=True)
    sent_messages: list[str] = []

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_send(_token, _chat_id, message, **_kwargs):
        sent_messages.append(message)
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    result = cli_module._run_process_intraday_alerts(
        config,
        repository,
        dry_run=False,
        batch_ids=None,
    )

    assert result == 1
    assert len(sent_messages) == 1


def test_manual_poll_rebuilds_summaries_before_intraday_alert_delivery_failure(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=False)
    repository.rebuild_daily_summaries(date(2026, 4, 24))

    second = _report(
        title="memory rebound",
        broker_name="Meritz",
        source_id="92000",
        identity_key="identity-2",
        target_price_value=100_000,
    )
    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report(), second], _inspection(2)))
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("send failed")),
    )

    with pytest.raises(RuntimeError, match="send failed"):
        cli_module._run_manual_poll(
            config,
            repository,
            limit=50,
            dry_run=False,
            inspect_only=False,
            headless=True,
            send_intraday_alert=True,
        )

    summaries = repository.list_daily_summaries(date(2026, 4, 24))
    assert len(summaries) == 1
    assert summaries[0].mention_count == 2
    assert "NH" in summaries[0].broker_display
    assert "Meritz" in summaries[0].broker_display
