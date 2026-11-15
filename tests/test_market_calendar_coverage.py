from argparse import Namespace
from datetime import date, datetime
from zoneinfo import ZoneInfo

from stock_monitor import cli as cli_module
from stock_monitor.business_day import derive_business_date, is_business_day
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


class _UnsupportedCalendarDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2027, 1, 5, 8, 30, tzinfo=tz)


def test_2024_temporary_public_holiday_is_a_market_closure(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_HOLIDAYS", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    temporary_holiday = date(2024, 10, 1)

    assert temporary_holiday in config.holiday_overrides
    assert is_business_day(temporary_holiday, config.holiday_overrides) is False
    assert derive_business_date(temporary_holiday, config.holiday_overrides) == date(2024, 9, 30)


def test_run_date_blocks_unsupported_weekday_without_changing_date_helpers(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_HOLIDAYS", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    new_year = date(2027, 1, 1)
    explanation = cli_module._explain_run_date(config, repository, new_year)

    assert is_business_day(new_year, config.holiday_overrides) is True
    assert explanation["is_business_day"] is True
    assert explanation["runnable"] is False
    assert explanation["market_calendar_supported"] is False
    assert "market_calendar_unsupported_year" in explanation["effective_reason"]

    cli_module._run_operator_control(
        config,
        repository,
        Namespace(operator_action="explain-date", date=new_year, json=False),
    )
    output = capsys.readouterr().out
    assert "실행 제외" in output
    assert "기본 KRX 휴장일 표 연도 지원: N" in output
    assert "market_calendar_unsupported_year" in output

    verified = cli_module._explain_run_date(config, repository, date(2026, 12, 30))
    assert verified["market_calendar_supported"] is True
    assert verified["runnable"] is True


def test_extra_holiday_does_not_extend_default_calendar_coverage(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_HOLIDAYS", "2027-01-04")
    monkeypatch.delenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    coverage = cli_module._build_market_holiday_coverage_snapshot(
        config,
        datetime(2027, 1, 5, 8, 30, tzinfo=ZoneInfo(config.timezone)),
    )

    assert date(2027, 1, 4) in config.holiday_overrides
    assert coverage["configured_max_year"] == 2027
    assert coverage["renewal_required"] is True
    assert coverage["default_coverage_years"] == [2024, 2025, 2026]
    assert coverage["current_year_supported"] is False
    assert cli_module._scheduled_skip_reason(config, date(2027, 1, 5)) is not None
    status = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2027, 1, 5, 8, 30, tzinfo=ZoneInfo(config.timezone)),
        scheduler_tasks=[],
    )
    assert status["market_holiday_coverage"]["current_year_supported"] is False
    assert "market_calendar_unsupported_year" in status["run_skip_reason"]
    assert "market_holidays.calendar_unsupported_year" in status["health"]["warning_checks"]


def test_unsupported_calendar_blocks_scheduled_poll_and_notify_before_io(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_HOLIDAYS", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _UnsupportedCalendarDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    calls: list[str] = []

    def fetch_reports(*_args, **_kwargs):
        calls.append("fetch")
        raise AssertionError("unsupported calendar must block report fetching")

    def send_notification(*_args, **_kwargs):
        calls.append("notify")
        raise AssertionError("unsupported calendar must block notification")

    monkeypatch.setattr(cli_module, "fetch_reports", fetch_reports)
    monkeypatch.setattr(cli_module, "_run_send_test_notification", send_notification)

    assert cli_module._run_scheduled_poll(
        config,
        repository,
        limit=50,
        dry_run=True,
        headless=True,
        send_intraday_alert=False,
    ) == 0
    assert cli_module._run_scheduled_notify(
        config,
        repository,
        dry_run=True,
        allow_repeat=False,
    ) == 0

    assert calls == []
    assert "market_calendar_unsupported_year" in capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=2)
    assert {event.component for event in events} == {"poll", "notify"}
    assert all(event.status == "skipped" for event in events)
    assert all(event.event_type == "run-guard" for event in events)
    assert all("market_calendar_unsupported_year" in (event.detail or "") for event in events)
