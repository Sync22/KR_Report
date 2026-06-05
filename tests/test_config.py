import os
from datetime import date, time
from pathlib import Path

from stock_monitor.config import DEFAULT_MARKET_HOLIDAYS, RuntimeConfig


def test_runtime_config_loads_dotenv_without_overriding_existing_env(tmp_path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "STOCK_MONITOR_TELEGRAM_CHAT_ID=1234567890",
                "STOCK_MONITOR_HEADLESS=false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCK_MONITOR_HEADLESS", "true")

    config = RuntimeConfig.from_env(root_dir=tmp_path)

    assert config.telegram_chat_id == "1234567890"
    assert config.headless is True


def test_runtime_config_does_not_mutate_process_environment_from_dotenv(tmp_path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "STOCK_MONITOR_DB_PATH=data/custom.db",
                "STOCK_MONITOR_TELEGRAM_CHAT_ID=1234567890",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", raising=False)

    config = RuntimeConfig.from_env(root_dir=tmp_path)

    assert config.db_path == Path("data/custom.db")
    assert config.telegram_chat_id == "1234567890"
    assert "STOCK_MONITOR_DB_PATH" not in os.environ
    assert "STOCK_MONITOR_TELEGRAM_CHAT_ID" not in os.environ


def test_runtime_config_defaults_include_market_window_and_2024_to_2026_holidays(tmp_path, monkeypatch) -> None:
    for key in (
        "STOCK_MONITOR_POLL_START_TIME",
        "STOCK_MONITOR_POLL_END_TIME",
        "STOCK_MONITOR_TASK_PREFIX",
        "STOCK_MONITOR_HOLIDAYS",
        "STOCK_MONITOR_RUN_SUPPRESSED_DATES",
        "STOCK_MONITOR_KRX_AUTH_KEY",
        "STOCK_MONITOR_KRX_BASE_URL",
        "STOCK_MONITOR_KRX_DATA_MARKET_ID",
        "STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD",
        "STOCK_MONITOR_KRX_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    config = RuntimeConfig.from_env(root_dir=tmp_path)

    assert config.poll_start_time == time(8, 30)
    assert config.poll_end_time == time(16, 30)
    assert config.scheduler_task_prefix == "StockMonitor"
    assert config.notification_default_limit == 7
    assert config.daily_summary_min_mention_count == 2
    assert config.daily_summary_require_target_price is True
    assert config.krx_auth_key is None
    assert config.krx_base_url == "https://data-dbg.krx.co.kr"
    assert config.krx_data_market_base_url == "https://data.krx.co.kr"
    assert config.krx_data_market_login_id is None
    assert config.krx_data_market_login_password is None
    assert config.krx_timeout_seconds == 30
    assert config.access_code_path == tmp_path / "data" / "access_code.json"
    assert config.holiday_overrides == DEFAULT_MARKET_HOLIDAYS
    assert config.run_suppressed_dates == frozenset()
    assert date(2024, 4, 10) in config.holiday_overrides
    assert date(2024, 5, 1) in config.holiday_overrides
    assert date(2024, 5, 15) in config.holiday_overrides
    assert date(2025, 1, 27) in config.holiday_overrides
    assert date(2025, 6, 3) in config.holiday_overrides
    assert date(2026, 6, 3) in config.holiday_overrides
    assert date(2026, 7, 17) in config.holiday_overrides
    assert date(2026, 12, 31) in config.holiday_overrides


def test_runtime_config_merges_extra_holidays_and_separates_run_suppressed_dates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_HOLIDAYS", "2026-06-01")
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")

    config = RuntimeConfig.from_env(root_dir=tmp_path)

    assert date(2026, 5, 1) in config.holiday_overrides
    assert date(2026, 6, 1) in config.holiday_overrides
    assert date(2026, 6, 2) not in config.holiday_overrides
    assert config.run_suppressed_dates == frozenset({date(2026, 6, 2)})
