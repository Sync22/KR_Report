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
        "schema": "insane-search-shadow-run/v3",
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


def test_article_title_match_rechecks_effective_title_conservatively() -> None:
    shadow = _load_shadow_module()

    assert shadow._article_title_matches_candidate("카카오", "카카오, 신규 서비스 공개") is True
    assert shadow._article_title_matches_candidate("현대건설", "대우건설, 정비사업 수주") is False
    assert shadow._article_title_matches_candidate("LS", "LS, 전선 사업 확대") is True
    assert shadow._article_title_matches_candidate("LS", "LS증권, 모의투자대회 개최") is False
    assert shadow._article_title_matches_candidate("LS", "LS ELECTRIC 신규 수주") is False


def test_shadow_aggregate_applies_title_identity_filter_to_existing_runs(tmp_path: Path) -> None:
    output = tmp_path / "shadow.jsonl"
    run = {
        "schema": "insane-search-shadow-run/v3",
        "status": "completed",
        "business_date": "2026-08-25",
        "candidate_pool": [{"stock_code": "035720", "selected": True}],
        "baseline": {"articles": []},
        "search_attempts": [{"stock_code": "035720", "ok": True, "trace_count": 1}],
        "articles": [
            {
                "stock_code": "035720",
                "stock_name": "카카오",
                "title": "카카오, 신규 서비스 공개",
                "canonical_url": "https://example.com/valid",
                "classification": "unknown",
                "point_in_time": True,
                "status": "matched",
                "access_attempts": [{"ok": True, "trace_count": 1}],
                "replay_consistent": True,
            },
            {
                "stock_code": "000720",
                "stock_name": "현대건설",
                "title": "대우건설, 정비사업 수주",
                "canonical_url": "https://example.com/noise",
                "classification": "unknown",
                "point_in_time": True,
                "status": "matched",
                "access_attempts": [{"ok": True, "trace_count": 1}],
                "replay_consistent": True,
            },
            {
                "stock_code": "035720",
                "stock_name": "카카오",
                "title": "카카오 주가, 장중 3% 상승",
                "canonical_url": "https://example.com/market-noise",
                "classification": "unknown",
                "point_in_time": True,
                "status": "matched",
                "access_attempts": [{"ok": True, "trace_count": 1}],
                "replay_consistent": True,
            },
        ],
    }
    output.write_text(json.dumps(run) + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--aggregate", "--output", str(output)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["raw_point_in_time_additional_count"] == 3
    assert payload["point_in_time_additional_count"] == 1
    assert payload["point_in_time_unique_canonical_count"] == 1
    assert payload["stock_identity_filter_rejected_count"] == 1
    assert payload["noise_filter_rejected_count"] == 1


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
        "schema": "insane-search-shadow-run/v3",
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


def test_engine_fetch_does_not_require_fetch_result_elapsed_ms(tmp_path: Path) -> None:
    shadow = _load_shadow_module()
    engine_root = tmp_path / "engine"
    engine_root.mkdir()
    (engine_root / "__init__.py").write_text(
        "class Result:\n"
        "    ok = True\n"
        "    verdict = 'valid_content'\n"
        "    profile_used = 'test'\n"
        "    summary = '\u00a9'\n"
        "    trace = []\n"
        "    content = '<html><title>ok</title><main id=\"main_pack\"></main></html>'\n"
        "def fetch(*args, **kwargs):\n"
        "    return Result()\n",
        encoding="utf-8",
    )
    bs4_root = tmp_path / "bs4"
    bs4_root.mkdir()
    (bs4_root / "__init__.py").write_text(
        "class BeautifulSoup:\n"
        "    title = None\n"
        "    def __init__(self, *args, **kwargs): pass\n"
        "    def select(self, *args, **kwargs): return []\n"
        "    def select_one(self, *args, **kwargs): return None\n",
        encoding="utf-8",
    )

    payload = shadow._engine_fetch(
        engine_python=Path(sys.executable),
        engine_root=engine_root,
        url="https://example.invalid/",
        selector="#main_pack",
    )

    assert payload["ok"] is True
    assert isinstance(payload["elapsed_ms"], float)


def test_shadow_status_fails_when_every_search_attempt_fails() -> None:
    shadow = _load_shadow_module()

    assert shadow._shadow_status([{"stock_code": "035720"}], [{"ok": False}]) == "search_failed"
    assert shadow._shadow_status([{"stock_code": "035720"}], [{"ok": True}]) == "completed"


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
