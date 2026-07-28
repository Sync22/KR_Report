from datetime import datetime

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import AppSetting


class _HolidayDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 1, 10, 0, 0, tzinfo=tz)


class _RunSuppressedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 6, 2, 10, 0, 0, tzinfo=tz)


class _NotifyAllowedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 27, 8, 29, 0, tzinfo=tz)


class _NotifyEarlyDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 27, 7, 59, 0, tzinfo=tz)


class _NotifyLateDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 4, 27, 8, 31, 0, tzinfo=tz)


class _LoopOnceDateTime(datetime):
    values = (
        datetime(2026, 5, 6, 8, 0, 0),
        datetime(2026, 5, 6, 8, 0, 1),
        datetime(2026, 5, 6, 8, 0, 2),
        datetime(2026, 5, 6, 16, 31, 0),
        datetime(2026, 5, 6, 16, 31, 1),
        datetime(2026, 5, 6, 16, 31, 2),
    )
    index = 0

    @classmethod
    def now(cls, tz=None):
        value = cls.values[min(cls.index, len(cls.values) - 1)]
        cls.index += 1
        return cls(value.year, value.month, value.day, value.hour, value.minute, value.second, tzinfo=tz)


def _set_operation_profile(repository: StockMonitorRepository, value: str) -> None:
    repository.set_app_setting(
        AppSetting(
            setting_key="operation_profile",
            setting_value=value,
            value_type="enum",
            updated_at=datetime(2026, 5, 6, 8, 0, 0),
            updated_by="test",
            detail="test profile",
            restart_required=True,
        ),
        audit_actor="test",
        audit_detail="test profile",
    )


def test_scheduled_telegram_commands_skip_market_holiday(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_process(_config, _repository):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_process_telegram_commands", fake_process)

    result = cli_module._run_scheduled_telegram_commands(config, repository)

    assert result == 0
    assert called is False


def test_scheduled_poll_skips_run_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_manual_poll(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_manual_poll", fake_manual_poll)

    result = cli_module._run_scheduled_poll(
        config,
        repository,
        limit=50,
        dry_run=True,
        headless=True,
        send_intraday_alert=False,
    )

    assert result == 0
    assert called is False


def test_manual_only_profile_skips_scheduled_poll(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _LoopOnceDateTime)
    _LoopOnceDateTime.index = 0
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    _set_operation_profile(repository, "manual-only")
    called = False

    def fake_manual_poll(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_manual_poll", fake_manual_poll)

    result = cli_module._run_scheduled_poll(
        config,
        repository,
        limit=50,
        dry_run=True,
        headless=True,
        send_intraday_alert=False,
    )

    assert result == 0
    assert called is False
    assert "manual-only" in repository.list_recent_operation_events(limit=1)[0].detail


def test_scheduled_poll_enables_same_run_top_two_news_collection(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    captured: dict[str, object] = {}

    def fake_manual_poll(*_args, **kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(cli_module, "_run_manual_poll", fake_manual_poll)

    result = cli_module._run_scheduled_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        headless=True,
        send_intraday_alert=False,
    )

    assert result == 0
    assert captured["collect_top_candidate_news"] is True
    assert captured["scheduled_run_at"].isoformat() == "2026-06-02T10:00:00+09:00"


def test_scheduled_notify_skips_run_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_send_test_notification(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_send_test_notification", fake_send_test_notification)

    result = cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
    )

    assert result == 0
    assert called is False


def test_scheduled_notify_allows_late_run_until_0830(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _NotifyAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_send_test_notification(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_send_test_notification", fake_send_test_notification)

    result = cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
    )

    assert result == 0
    assert called is True


def test_scheduled_notify_skips_early_run_before_0800(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _NotifyEarlyDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_send_test_notification(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_send_test_notification", fake_send_test_notification)

    result = cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
    )
    events = repository.list_recent_operation_events(limit=1)

    assert result == 0
    assert called is False
    assert events[0].event_type == "early_notify"
    assert events[0].status == "skipped"


def test_scheduled_notify_skips_late_run_after_0830(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _NotifyLateDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_send_test_notification(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_send_test_notification", fake_send_test_notification)

    result = cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
    )
    events = repository.list_recent_operation_events(limit=1)

    assert result == 0
    assert called is False
    assert events[0].event_type == "late_notify"
    assert events[0].status == "skipped"


def test_scheduled_notify_allow_late_overrides_late_run_guard(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _NotifyLateDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_send_test_notification(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_send_test_notification", fake_send_test_notification)

    result = cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
        allow_late=True,
    )

    assert result == 0
    assert called is True


def test_scheduled_telegram_commands_skip_run_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_process(_config, _repository):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_process_telegram_commands", fake_process)

    result = cli_module._run_scheduled_telegram_commands(config, repository)

    assert result == 0
    assert called is False


def test_scheduled_shutdown_skips_run_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    result = cli_module._run_scheduled_shutdown(config, dry_run=False, delay_seconds=60)

    assert result == 0
    assert called is False


def test_scheduled_shutdown_skips_market_holiday(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    result = cli_module._run_scheduled_shutdown(config, dry_run=False, delay_seconds=60)

    assert result == 0
    assert called is False


def test_mini_pc_profile_skips_scheduled_shutdown(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _LoopOnceDateTime)
    _LoopOnceDateTime.index = 0
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    _set_operation_profile(repository, "mini-pc")
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    result = cli_module._run_scheduled_shutdown(config, dry_run=False, delay_seconds=60)

    assert result == 0
    assert called is False
    assert "mini-pc" in repository.list_recent_operation_events(limit=1)[0].detail


def test_scheduled_telegram_command_loop_skips_run_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_process(_config, _repository):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_process_telegram_commands", fake_process)

    result = cli_module._run_scheduled_telegram_command_loop(
        config,
        repository,
        end_time=cli_module._parse_hhmm_time("16:30"),
        interval_seconds=60,
    )

    assert result == 0
    assert called is False
    state = repository.get_worker_state(cli_module.TELEGRAM_COMMAND_LOOP_WORKER)
    assert state is not None
    assert state.status == "stopped"
    assert state.last_started_at is not None


def test_scheduled_telegram_command_loop_skips_market_holiday(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = False

    def fake_process(_config, _repository):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_process_telegram_commands", fake_process)

    result = cli_module._run_scheduled_telegram_command_loop(
        config,
        repository,
        end_time=cli_module._parse_hhmm_time("16:30"),
        interval_seconds=60,
    )

    assert result == 0
    assert called is False


def test_scheduled_telegram_command_loop_records_success_heartbeat(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    _LoopOnceDateTime.index = 0
    monkeypatch.setattr(cli_module, "datetime", _LoopOnceDateTime)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    called = 0

    def fake_process(_config, _repository):
        nonlocal called
        called += 1
        return 0

    monkeypatch.setattr(cli_module, "_run_process_telegram_commands", fake_process)

    result = cli_module._run_scheduled_telegram_command_loop(
        config,
        repository,
        end_time=cli_module._parse_hhmm_time("16:30"),
        interval_seconds=60,
    )
    state = repository.get_worker_state(cli_module.TELEGRAM_COMMAND_LOOP_WORKER)

    assert result == 0
    assert called == 1
    assert state is not None
    assert state.status == "stopped"
    assert state.last_started_at is not None
    assert state.last_success_at is not None
    assert state.interval_seconds == 60
    assert state.end_time == "16:30"
