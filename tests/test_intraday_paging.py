from datetime import date, datetime

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import Opinion, Report
from stock_monitor.notify.control import TelegramControlState, load_control_state, save_control_state


def _report(
    *,
    stock_name: str = "삼성전자",
    stock_code: str = "005930",
    title: str = "상황 회복 가시화",
    broker_name: str = "NH투자증권",
    source_id: str = "91999",
    identity_key: str = "identity-1",
    collected_at: datetime = datetime(2026, 4, 24, 9, 30, 0),
) -> Report:
    return Report(
        stock_name=stock_name,
        stock_code=stock_code,
        title=title,
        broker_name=broker_name,
        published_at=datetime(2026, 4, 24, 9, 0, 0),
        collected_at=collected_at,
        business_date=date(2026, 4, 24),
        target_price_raw="92000",
        target_price_value=92_000,
        opinion_raw="Buy",
        opinion_normalized=Opinion.BUY.value,
        source_url=f"https://stock.naver.com/research/company/{source_id}",
        source_id=source_id,
        identity_key=identity_key,
    )


def _unique_report(index: int, *, collected_at: datetime = datetime(2026, 4, 24, 9, 30, 0)) -> Report:
    return _report(
        stock_name=f"Stock {index}",
        stock_code=f"{index:06d}",
        title=f"report {index}",
        broker_name="Broker",
        source_id=f"{91000 + index}",
        identity_key=f"identity-{index}",
        collected_at=collected_at,
    )


def _runtime_config(tmp_path, monkeypatch) -> RuntimeConfig:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    return config


def test_process_intraday_alerts_does_not_keep_state_for_single_page_batch(tmp_path, monkeypatch) -> None:
    config = _runtime_config(tmp_path, monkeypatch)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports([_report()], queue_intraday_alerts=True)

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")

    result = cli_module._run_process_intraday_alerts(config, repository, dry_run=False)

    state = load_control_state(config.telegram_control_state_path)
    assert result == 1
    assert state.active_intraday_batch_id is None
    assert state.active_intraday_created_at is None
    assert state.active_intraday_delivered_count == 0
    assert state.active_message_kind is None


def test_process_telegram_commands_falls_back_to_daily_after_intraday_is_exhausted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_DAILY_SUMMARY_MIN_MENTION_COUNT", "1")
    config = _runtime_config(tmp_path, monkeypatch)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    insert_result = repository.insert_reports([_report()], queue_intraday_alerts=True)
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    with repository.connect() as connection:
        row = connection.execute(
            "SELECT created_at FROM intraday_alert_batches WHERE batch_id = ?",
            (insert_result.intraday_batch_ids[0],),
        ).fetchone()
    assert row is not None

    state = TelegramControlState(
        last_update_id=0,
        active_message_kind="intraday",
        active_business_date="2026-04-24",
        delivered_counts={"2026-04-24": 0},
        active_intraday_batch_id=insert_result.intraday_batch_ids[0],
        active_intraday_created_at=row["created_at"],
        active_intraday_delivered_count=1,
    )
    save_control_state(config.telegram_control_state_path, state)

    sent_messages: list[str] = []

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [
                {
                    "update_id": 1,
                    "message": {
                        "chat": {"id": "chat-1"},
                        "text": "다음",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda _token, _chat_id, message, **_kwargs: sent_messages.append(message) or "message-2",
    )

    result = cli_module._run_process_telegram_commands(config, repository)

    updated_state = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert len(sent_messages) == 1
    assert updated_state.last_update_id == 1
    assert updated_state.active_intraday_batch_id is None
    assert updated_state.active_intraday_created_at is None
    assert updated_state.active_intraday_delivered_count == 0
    assert updated_state.active_message_kind == "daily"
    assert updated_state.delivered_for(date(2026, 4, 24)) == 1


def test_process_intraday_alerts_stops_after_first_multi_page_batch(tmp_path, monkeypatch) -> None:
    config = _runtime_config(tmp_path, monkeypatch)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    first_result = repository.insert_reports([_unique_report(index) for index in range(8)], queue_intraday_alerts=True)
    second_result = repository.insert_reports(
        [_unique_report(20, collected_at=datetime(2026, 4, 24, 10, 0, 0))],
        queue_intraday_alerts=True,
    )

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    send_calls: list[str] = []
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda *_args, **_kwargs: send_calls.append("sent") or f"message-{len(send_calls)}",
    )

    result = cli_module._run_process_intraday_alerts(config, repository, dry_run=False)

    state = load_control_state(config.telegram_control_state_path)
    pending_batches = repository.list_pending_intraday_alert_batches()
    assert result == 1
    assert len(send_calls) == 1
    assert state.active_intraday_batch_id == first_result.intraday_batch_ids[0]
    assert state.active_intraday_delivered_count == config.notification_default_limit
    assert [batch.batch_id for batch in pending_batches] == [second_result.intraday_batch_ids[0]]
