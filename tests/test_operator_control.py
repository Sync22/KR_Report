import json
from datetime import date, datetime

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 6, 9, 0, 0, tzinfo=tz)


def _repository(tmp_path, monkeypatch):
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    return config, repository


def test_operator_control_pause_and_resume(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)

    pause_args = cli_module.build_parser().parse_args(["operator-control", "pause", "--reason", "test"])
    resume_args = cli_module.build_parser().parse_args(["operator-control", "resume"])

    assert cli_module._run_operator_control(config, repository, pause_args) == 0
    assert repository.is_operator_paused() is True
    assert "운영 일시정지 완료" in capsys.readouterr().out

    assert cli_module._scheduled_skip_reason(config, date(2026, 5, 6), repository) == "Stock Monitor is paused by operator control."

    assert cli_module._run_operator_control(config, repository, resume_args) == 0
    assert repository.is_operator_paused() is False
    assert "운영 재개 완료" in capsys.readouterr().out


def test_operator_control_adds_and_removes_no_run_date(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)
    add_args = cli_module.build_parser().parse_args(
        ["operator-control", "add-no-run-date", "2026-06-02", "--reason", "personal off"]
    )
    list_args = cli_module.build_parser().parse_args(["operator-control", "list-no-run-dates"])
    remove_args = cli_module.build_parser().parse_args(["operator-control", "remove-no-run-date", "2026-06-02"])

    assert cli_module._run_operator_control(config, repository, add_args) == 0
    assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is True
    assert cli_module._scheduled_skip_reason(config, date(2026, 6, 2), repository) == (
        "2026-06-02 is configured as an operator no-run date."
    )

    assert cli_module._run_operator_control(config, repository, list_args) == 0
    assert "2026-06-02" in capsys.readouterr().out

    assert cli_module._run_operator_control(config, repository, remove_args) == 0
    assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is False


def test_operator_control_rejects_past_no_run_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)
    add_args = cli_module.build_parser().parse_args(
        ["operator-control", "add-no-run-date", "2026-05-04", "--reason", "past"]
    )

    try:
        cli_module._run_operator_control(config, repository, add_args)
    except ValueError as exc:
        assert "in the past" in str(exc)
    else:
        raise AssertionError("Expected past no-run date to fail.")
    assert repository.list_db_run_suppressed_dates() == []


def test_operator_status_exposes_db_operator_controls(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config, repository = _repository(tmp_path, monkeypatch)
    repository.set_operator_pause(paused=True, updated_at=datetime(2026, 5, 6, 9, 0, 0), detail="test")
    repository.add_run_suppressed_date(date(2026, 6, 2), updated_at=datetime(2026, 5, 6, 9, 0, 0))

    assert cli_module._run_operator_status(config, repository, as_json=False, limit=1) == 0

    output = capsys.readouterr().out
    assert "운영 일시정지: Y" in output


def test_operator_status_uses_db_safe_settings(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)
    args = cli_module.build_parser().parse_args(
        [
            "operator-settings",
            "set",
            "notification_default_limit",
            "9",
            "--reason",
            "paging",
            "--confirm",
        ]
    )

    assert cli_module._run_operator_settings(config, repository, args) == 0
    capsys.readouterr()
    assert cli_module._run_operator_status(config, repository, as_json=False, limit=1) == 0

    output = capsys.readouterr().out
    assert "기본 알림 표시 수: 9 (db)" in output


def test_operator_control_explain_date_json_uses_priority_and_db_reason(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    config, repository = _repository(tmp_path, monkeypatch)
    repository.add_run_suppressed_date(
        date(2026, 6, 2),
        updated_at=datetime(2026, 5, 6, 9, 0, 0),
        detail="personal off",
    )
    args = cli_module.build_parser().parse_args(["operator-control", "explain-date", "2026-06-02", "--json"])

    assert cli_module._run_operator_control(config, repository, args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["date"] == "2026-06-02"
    assert payload["runnable"] is False
    assert payload["effective_reason"] == "2026-06-02 is configured as an env no-run date."
    assert payload["matched_reasons"] == ["env_no_run_date", "db_no_run_date"]
    assert payload["is_business_day"] is True
    assert payload["is_env_run_suppressed"] is True
    assert payload["is_db_run_suppressed"] is True
    assert payload["db_reason"] == "personal off"
    assert payload["previous_business_day"] == "2026-06-01"
    assert payload["next_business_day"] == "2026-06-04"


def test_operator_control_explain_date_text_shows_holiday_reason(tmp_path, monkeypatch, capsys) -> None:
    config, repository = _repository(tmp_path, monkeypatch)
    args = cli_module.build_parser().parse_args(["operator-control", "explain-date", "2026-05-01"])

    assert cli_module._run_operator_control(config, repository, args) == 0

    output = capsys.readouterr().out
    assert "실행일 판단: 2026-05-01 | 실행 제외" in output
    assert "시장 휴장일: Y" in output


def test_operator_settings_list_shows_defaults_and_db_source(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)

    list_args = cli_module.build_parser().parse_args(["operator-settings", "list"])
    set_args = cli_module.build_parser().parse_args(
        [
            "operator-settings",
            "set",
            "daily_summary_min_mention_count",
            "3",
            "--reason",
            "noise reduction",
            "--confirm",
        ]
    )

    assert cli_module._run_operator_settings(config, repository, list_args) == 0
    assert "daily_summary_min_mention_count | value=2 | source=env/default" in capsys.readouterr().out

    assert cli_module._run_operator_settings(config, repository, set_args) == 0
    assert "설정 변경 완료 | daily_summary_min_mention_count | 2 -> 3 | source=db" in capsys.readouterr().out

    assert cli_module._run_operator_settings(config, repository, list_args) == 0
    assert "daily_summary_min_mention_count | value=3 | source=db" in capsys.readouterr().out


def test_operator_settings_set_requires_confirm(tmp_path, monkeypatch, capsys) -> None:
    config, repository = _repository(tmp_path, monkeypatch)
    args = cli_module.build_parser().parse_args(
        ["operator-settings", "set", "notification_default_limit", "9", "--reason", "paging test"]
    )

    assert cli_module._run_operator_settings(config, repository, args) == 2
    assert repository.get_app_setting("notification_default_limit") is None
    assert "--confirm is required" in capsys.readouterr().err


def test_operator_settings_rejects_invalid_values(tmp_path, monkeypatch) -> None:
    config, repository = _repository(tmp_path, monkeypatch)
    args = cli_module.build_parser().parse_args(
        [
            "operator-settings",
            "set",
            "notification_default_limit",
            "99",
            "--reason",
            "too high",
            "--confirm",
        ]
    )

    try:
        cli_module._run_operator_settings(config, repository, args)
    except ValueError as exc:
        assert "notification_default_limit must be between 3 and 20" in str(exc)
    else:
        raise AssertionError("Expected invalid setting value to fail.")
    logs = repository.list_admin_audit_logs()
    assert logs[0].status == "validation_failed"
    assert logs[0].setting_key == "notification_default_limit"


def test_operator_settings_same_effective_value_does_not_write_audit(tmp_path, monkeypatch, capsys) -> None:
    config, repository = _repository(tmp_path, monkeypatch)
    args = cli_module.build_parser().parse_args(
        [
            "operator-settings",
            "set",
            "daily_summary_min_mention_count",
            "2",
            "--reason",
            "same default",
            "--confirm",
        ]
    )

    assert cli_module._run_operator_settings(config, repository, args) == 0
    assert repository.get_app_setting("daily_summary_min_mention_count") is None
    assert repository.list_admin_audit_logs() == []
    assert "변경 없음 | daily_summary_min_mention_count | 2" in capsys.readouterr().out


def test_operator_settings_audit_log_json(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "datetime", _FixedDateTime)
    config, repository = _repository(tmp_path, monkeypatch)
    set_args = cli_module.build_parser().parse_args(
        [
            "operator-settings",
            "set",
            "daily_summary_require_target_price",
            "false",
            "--actor",
            "tester",
            "--reason",
            "include missing targets",
            "--confirm",
        ]
    )
    audit_args = cli_module.build_parser().parse_args(["operator-settings", "history", "--json"])

    assert cli_module._run_operator_settings(config, repository, set_args) == 0
    capsys.readouterr()
    assert cli_module._run_operator_settings(config, repository, audit_args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["actor"] == "tester"
    assert payload[0]["setting_key"] == "daily_summary_require_target_price"
    assert payload[0]["new_value"] == "false"
