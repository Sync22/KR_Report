import subprocess

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


def test_scheduler_control_refuses_without_confirm(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    called = False

    def fake_execute(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="disable",
        task_selector="poll",
        dry_run=False,
        confirm=False,
    )

    assert result == 2
    assert called is False
    assert "without --confirm" in capsys.readouterr().out


def test_scheduler_control_dry_run_lists_target_tasks(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="run-now",
        task_selector="all",
        dry_run=True,
        confirm=False,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "StockMonitor-Notify" in output
    assert "StockMonitor-Poll" in output
    assert "StockMonitor-Shutdown" not in output
    assert "Start-ScheduledTask" in output


def test_scheduler_control_refuses_run_now_shutdown(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    called = False

    def fake_execute(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="run-now",
        task_selector="shutdown",
        dry_run=False,
        confirm=True,
    )

    assert result == 2
    assert called is False
    assert "Shutdown task" in capsys.readouterr().out


def test_scheduler_control_restart_only_allows_telegram_commands(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    called = False

    def fake_execute(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="restart",
        task_selector="poll",
        dry_run=False,
        confirm=True,
    )

    assert result == 2
    assert called is False
    assert "TelegramCommands" in capsys.readouterr().out


def test_scheduler_control_records_success_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "enable"
        assert task_name == "StockMonitor-Notify"
        return {"state": "Ready"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="enable",
        task_selector="notify",
        dry_run=False,
        confirm=True,
    )

    events = repository.list_recent_operation_events(limit=1)
    assert result == 0
    assert events[0].component == "scheduler-control"
    assert events[0].event_type == "enable"
    assert events[0].status == "success"
    assert "StockMonitor-Notify" in (events[0].detail or "")


def test_scheduler_control_restart_records_success_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "restart"
        assert task_name == "StockMonitor-TelegramCommands"
        return {"state": "Running"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    result = cli_module._run_scheduler_control(
        config,
        repository,
        action="restart",
        task_selector="telegram-commands",
        dry_run=False,
        confirm=True,
    )

    events = repository.list_recent_operation_events(limit=1)
    assert result == 0
    assert events[0].component == "scheduler-control"
    assert events[0].event_type == "restart"
    assert events[0].status == "success"


def test_scheduler_control_uses_configured_task_prefix() -> None:
    assert cli_module._resolve_scheduler_control_task_names("MyMonitor", "poll") == ("MyMonitor-Poll",)
    assert cli_module._resolve_scheduler_control_task_names("MyMonitor", "web-view-hourly-restart") == (
        "MyMonitor-WebViewHourlyRestart",
    )
    assert cli_module._resolve_scheduler_control_task_names("MyMonitor", "web-view-manual") == (
        "MyMonitor-WebViewManual",
    )
    assert cli_module._resolve_scheduler_control_task_names("MyMonitor", "all") == (
        "MyMonitor-Notify",
        "MyMonitor-Poll",
        "MyMonitor-KrxDailyBackfill",
        "MyMonitor-KrxMentionedFlowBackfill",
        "MyMonitor-KrxFlowLoginReminder",
        "MyMonitor-TelegramCommands",
        "MyMonitor-WebViewHourlyRestart",
        "MyMonitor-WebViewManual",
        "MyMonitor-Shutdown",
    )


def test_execute_scheduler_control_action_parses_powershell_result(monkeypatch) -> None:
    monkeypatch.setattr(cli_module.sys, "platform", "win32")

    def fake_run(command, **_kwargs):
        script = command[-1]
        assert "Start-ScheduledTask" in script
        assert "StockMonitor-Poll" in script
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"task_name":"StockMonitor-Poll","action":"run-now","state":"Running"}',
            stderr="",
        )

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    result = cli_module._execute_scheduler_control_action("run-now", "StockMonitor-Poll")

    assert result["task_name"] == "StockMonitor-Poll"
    assert result["state"] == "Running"


def test_execute_scheduler_restart_uses_stop_then_start(monkeypatch) -> None:
    monkeypatch.setattr(cli_module.sys, "platform", "win32")

    def fake_run(command, **_kwargs):
        script = command[-1]
        assert "Stop-ScheduledTask" in script
        assert "Start-ScheduledTask" in script
        assert "StockMonitor-TelegramCommands" in script
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='{"task_name":"StockMonitor-TelegramCommands","action":"restart","state":"Running"}',
            stderr="",
        )

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    result = cli_module._execute_scheduler_control_action("restart", "StockMonitor-TelegramCommands")

    assert result["task_name"] == "StockMonitor-TelegramCommands"
    assert result["state"] == "Running"
