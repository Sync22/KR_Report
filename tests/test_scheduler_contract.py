from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER = PROJECT_ROOT / "scripts" / "task_scheduler_contract.ps1"
PWSH = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PWSH is None, reason="PowerShell Core is required")


def test_weekday_task_contract_checks_enablement_and_exact_times() -> None:
    task = {
        "State": "Ready",
        "Settings": {"Enabled": True},
        "Triggers": [
            {
                "CimClass": {"CimClassName": "MSFT_TaskWeeklyTrigger"},
                "Enabled": True,
                "StartBoundary": f"2026-11-16T{time}:00",
                "DaysOfWeek": 62,
                "WeeksInterval": 1,
            }
            for time in ("08:30", "09:00")
        ],
    }
    expected = {"Type": "weekly", "Times": ["08:30", "09:00"]}

    assert run_contract(task, expected) == []

    task["Triggers"][1]["StartBoundary"] = "2026-11-16T09:30:00"
    assert "weekly trigger times differ" in run_contract(task, expected)[0]
    task["Triggers"][1]["StartBoundary"] = "2026-11-16T09:00:00"
    task["Settings"]["Enabled"] = False
    assert "task is disabled" in run_contract(task, expected)[0]
    task["Settings"]["Enabled"] = True
    task["Triggers"][0]["Enabled"] = False
    assert "disabled or missing trigger" in run_contract(task, expected)[0]
    task["Triggers"][0]["Enabled"] = True
    task["Triggers"][0]["DaysOfWeek"] = 31
    assert "weekdays or interval differ" in run_contract(task, expected)[0]
    task["Triggers"][0]["DaysOfWeek"] = 62
    task["Triggers"][0]["EndBoundary"] = "2026-11-16T17:00:00"
    assert "weekly trigger must not have an end boundary" in run_contract(task, expected)[0]
    task["Triggers"][0].pop("EndBoundary")
    task["Triggers"][0]["RandomDelay"] = "PT1M"
    assert "weekly trigger must not have random delay" in run_contract(task, expected)[0]
    task["Triggers"][0].pop("RandomDelay")
    task["Triggers"][0]["Repetition"] = {"Interval": "PT1M", "Duration": "P1D"}
    assert "weekly trigger must not repeat" in run_contract(task, expected)[0]
    task["Triggers"][0].pop("Repetition")
    task["Triggers"][0]["StartBoundary"] = "2026-11-16T08:30:15"
    assert "weekly trigger seconds must be zero" in run_contract(task, expected)[0]
    task["Triggers"][0]["StartBoundary"] = "invalid"
    assert "weekly trigger start boundary is invalid" in run_contract(task, expected)[0]


def test_hourly_task_contract_checks_start_and_repetition() -> None:
    task = {
        "State": "Ready",
        "Settings": {"Enabled": True},
        "Triggers": [{
            "CimClass": {"CimClassName": "MSFT_TaskDailyTrigger"},
            "Enabled": True,
            "StartBoundary": "2026-11-16T00:05:00",
            "DaysInterval": 1,
            "Repetition": {"Interval": "PT1H", "Duration": "P1D", "StopAtDurationEnd": False},
        }],
    }
    expected = {"Type": "hourly", "Start": "00:05", "Interval": "PT1H"}

    assert run_contract(task, expected) == []

    task["Triggers"][0]["Repetition"]["Interval"] = "PT2H"
    assert "hourly repetition differs" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"]["Interval"] = "PT1H"
    task["Triggers"][0]["Repetition"]["Duration"] = "PT12H"
    assert "daily repetition duration is too short" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"]["Duration"] = "P1D"
    task["Triggers"][0]["DaysInterval"] = 2
    assert "daily trigger must recur every day" in run_contract(task, expected)[0]
    task["Triggers"][0]["DaysInterval"] = 1
    task["Triggers"][0]["Repetition"]["StopAtDurationEnd"] = True
    assert "daily repetition must not stop a running task" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"]["StopAtDurationEnd"] = False
    task["Triggers"][0]["Repetition"]["Duration"] = "invalid"
    assert "daily repetition duration is invalid" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"]["StopAtDurationEnd"] = False
    task["Triggers"][0]["EndBoundary"] = "2026-11-17T00:05:00"
    assert "hourly daily trigger must not have an end boundary" in run_contract(task, expected)[0]


def test_open_ended_time_trigger_is_an_hourly_schedule() -> None:
    task = {
        "State": "Ready",
        "Settings": {"Enabled": True},
        "Triggers": [{
            "CimClass": {"CimClassName": "MSFT_TaskTimeTrigger"},
            "Enabled": True,
            "StartBoundary": "2026-11-16T00:05:00",
            "Repetition": {"Interval": "PT1H", "StopAtDurationEnd": False},
        }],
    }
    expected = {"Type": "hourly", "Start": "00:05", "Interval": "PT1H"}

    assert run_contract(task, expected) == []

    task["Triggers"][0]["Repetition"]["Duration"] = "PT12H"
    assert "time trigger must repeat indefinitely" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"].pop("Duration")
    task["Triggers"][0]["Repetition"]["StopAtDurationEnd"] = True
    assert "time trigger must repeat indefinitely" in run_contract(task, expected)[0]
    task["Triggers"][0]["Repetition"]["StopAtDurationEnd"] = False
    task["Triggers"][0]["RandomDelay"] = "PT1M"
    assert "hourly trigger must not have random delay" in run_contract(task, expected)[0]


def run_contract(task: dict, expected: dict) -> list[str]:
    script = (
        f'. "{HELPER}"; '
        '$null = Get-Command Test-ScheduledTaskContract -ErrorAction Stop; '
        f'$task = ConvertFrom-Json \'{json.dumps(task)}\'; '
        f'$expected = ConvertFrom-Json \'{json.dumps(expected)}\'; '
        '$errors = @(Test-ScheduledTaskContract -Task $task -Expected $expected); '
        'ConvertTo-Json -InputObject $errors -Compress'
    )
    result = subprocess.run([PWSH, "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
