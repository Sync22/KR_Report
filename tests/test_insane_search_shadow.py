from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "lab" / "run_insane_search_shadow.py"
SCHEDULED_WRAPPER = PROJECT_ROOT / "scripts" / "lab" / "run_insane_search_shadow_scheduled.ps1"


def _load_shadow_module():
    spec = importlib.util.spec_from_file_location("insane_search_shadow", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shadow_run_skips_non_business_day_without_creating_manifest(tmp_path: Path) -> None:
    output = tmp_path / "shadow.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cutoff",
            "2026-08-23T12:00:00+09:00",
            "--output",
            str(output),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "skipped_non_business_day"
    assert payload["writes_production_db"] is False
    assert output.exists() is False


def test_shadow_aggregate_marks_missing_manifest_incomplete(tmp_path: Path) -> None:
    output = tmp_path / "missing.jsonl"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--aggregate", "--output", str(output)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "reason": "manifest_missing",
        "run_count": 0,
        "status": "aggregate_incomplete",
    }


def test_shadow_run_accepts_1500_kst_slot(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cutoff",
            "2026-08-24T15:00:00+09:00",
            "--db-path",
            str(tmp_path / "missing.db"),
            "--output",
            str(tmp_path / "shadow.jsonl"),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "blocked_missing_database"


def test_shadow_aggregate_requires_ten_runs_for_two_daily_slots(tmp_path: Path) -> None:
    output = tmp_path / "shadow.jsonl"
    run = {
        "schema": "insane-search-shadow-run/v2",
        "status": "no_candidate_pool",
        "candidate_pool": [],
        "baseline": {"articles": []},
        "articles": [],
    }
    output.write_text("".join(json.dumps(run) + "\n" for _ in range(5)), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--aggregate", "--output", str(output)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "aggregate_incomplete"
    assert payload["expected_run_count"] == 10


def test_candidate_manifest_row_preserves_web_view_selection_contract() -> None:
    shadow = _load_shadow_module()

    row = shadow._candidate_manifest_row(
        1,
        {
            "stock_code": "035720",
            "stock_name": "카카오",
            "selected": True,
            "sort_tuple": {"report_count": 6},
            "news_observation_badge": {"evidence_direction": "리포트 재인용 흐름"},
        },
    )

    assert row["selected"] is True
    assert row["selection_reason"] == "eligible_top2"
    assert row["evidence_direction"] == "리포트 재인용 흐름"


def test_shadow_aggregate_excludes_pre_contract_runs_and_counts_search_trace(tmp_path: Path) -> None:
    output = tmp_path / "shadow.jsonl"
    legacy = {
        "schema": "insane-search-shadow-run/v1",
        "status": "completed",
        "business_date": "2026-08-24",
        "candidate_pool": [{"stock_code": "035720"}],
        "baseline": {"articles": []},
        "articles": [],
    }
    current = {
        "schema": "insane-search-shadow-run/v2",
        "status": "completed",
        "business_date": "2026-08-25",
        "candidate_pool": [{"stock_code": "035720", "selected": True}],
        "baseline": {"articles": []},
        "search_attempts": [{"stock_code": "035720", "ok": True, "trace_count": 2}],
        "articles": [],
    }
    output.write_text(json.dumps(legacy) + "\n" + json.dumps(current) + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--aggregate", "--output", str(output)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["run_count"] == 1
    assert payload["pre_contract_run_count"] == 1
    assert payload["candidate_observation_count"] == 1
    assert payload["candidate_count"] == 1
    assert payload["access_success_rate"] == 1.0
    assert payload["trace_complete"] is True


def test_scheduled_wrapper_freezes_requested_slot() -> None:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCHEDULED_WRAPPER),
            "-Slot",
            "15:00",
            "-RunDate",
            "2026-08-24",
            "-DryRun",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["cutoff"] == "2026-08-24T15:00:00+09:00"
    assert payload["dry_run"] is True
