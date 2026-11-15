from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock

import pytest

from stock_monitor.chart_alerts import (
    build_chart_alert_message,
    chart_alert_event_id,
    process_chart_alert_spool,
    validate_chart_alert_event,
)
from stock_monitor.cli import build_parser
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.file_lock import FILE_LOCK_MARKER, exclusive_file_lock
import stock_monitor.chart_alerts as chart_alerts


def event_payload(
    status: str = "observed-crossing",
    *,
    kind: str = "resistance-breakout",
    direction: str = "up",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "event_id": "",
        "watch_id": "2026-10-22-005930",
        "report_business_date": "2026-10-22",
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "report_count": 2,
        "report_reason": "리포트 집중",
        "rule_key": "horizontal-m1-v1",
        "rule_version": "horizontal-m1-v1",
        "timeframe": "1m",
        "kind": kind,
        "direction": direction,
        "observed_state": status,
        "basis_start_time": "2026-10-22T01:00:00.000Z",
        "basis_bar_time": "2026-10-22T01:21:00.000Z",
        "source": "Toss OpenAPI · 1m candles",
        "source_fetched_at": "2026-10-22T01:22:00.000Z",
        "finality": "unknown",
        "observed_at": "2026-10-22T01:22:01.000Z",
    }
    payload["event_id"] = chart_alert_event_id(
        watch_id=str(payload["watch_id"]), symbol=str(payload["stock_code"]),
        report_business_date=str(payload["report_business_date"]), stock_name=str(payload["stock_name"]),
        report_count=int(payload["report_count"]), rule_version=str(payload["rule_version"]),
        kind=str(payload["kind"]), direction=str(payload["direction"]), basis_start_time=str(payload["basis_start_time"]), status=status,
    )
    return payload


def repository_with_focus_reports(tmp_path: Path) -> StockMonitorRepository:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    with repository.connect() as connection, connection:
        for index in range(2):
            connection.execute(
                """
                INSERT INTO reports (identity_key, stock_name, stock_code, title, broker_name, published_at,
                    business_date, opinion_normalized, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"alert-report-{index}", "삼성전자", "005930", f"보고서 {index}", f"증권사 {index}",
                 f"2026-10-22T0{index}:00:00+09:00", "2026-10-22", "중립", "2026-10-22T01:00:00+09:00"),
            )
    return repository


def test_chart_alert_event_requires_exact_report_focus_source_and_hash() -> None:
    event = event_payload()
    assert validate_chart_alert_event(event)["event_id"] == event["event_id"]
    message = build_chart_alert_message(event)
    assert message.splitlines() == [
        "삼성전자(005930) · 기술 관찰",
        "1분봉 · 저항 경계 상향 관찰 · 경계 교차 관찰 · 기준 26.10.22 10:21 KST",
        "Toss OpenAPI · 수집 26.10.22 10:22 KST · 봉 확정 상태 제공 안 됨",
        "리포트 집중 2026-10-22 · 2건 · 매매·주문 신호 아님",
    ]
    assert chart_alert_event_id(
        watch_id="2026-10-22-005930", symbol="005930", rule_version="horizontal-m1-v1",
        report_business_date="2026-10-22", stock_name="삼성전자", report_count=2, direction="up",
        kind="resistance-breakout", basis_start_time="2026-10-22T01:00:00.000Z", status="observed-crossing",
    ) == event["event_id"]

    with pytest.raises(ValueError, match="invalid-chart-alert-event"):
        validate_chart_alert_event({**event, "report_reason": "다른 사유"})
    with pytest.raises(ValueError, match="invalid-chart-alert-event"):
        validate_chart_alert_event({**event, "finality": "confirmed"})
    with pytest.raises(ValueError, match="invalid-chart-alert-event"):
        validate_chart_alert_event({**event, "report_count": 20})
    contradictory = event_payload(kind="resistance-breakout", direction="down")
    with pytest.raises(ValueError, match="invalid-chart-alert-event"):
        validate_chart_alert_event(contradictory)


def test_chart_alert_dry_run_does_not_write_db_send_or_consume_spool(tmp_path: Path) -> None:
    repository = repository_with_focus_reports(tmp_path)
    spool = tmp_path / "spool"
    spool.mkdir()
    event = event_payload()
    (spool / f"{event['event_id']}.json").write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
    sender_calls: list[str] = []

    result = process_chart_alert_spool(repository, spool, send=False, sender=lambda *_args, **_kwargs: sender_calls.append("send"))

    assert result["preview_count"] == 1
    assert result["inserted_count"] == 0
    assert sender_calls == []
    assert len(list(spool.glob("*.json"))) == 1
    with repository.connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM chart_alert_outbox").fetchone()[0]
    assert count == 0


def test_chart_alert_send_is_event_keyed_and_never_retries_ambiguous_delivery(tmp_path: Path) -> None:
    repository = repository_with_focus_reports(tmp_path)
    repository.migrate_schema()
    spool = tmp_path / "spool"
    spool.mkdir()
    event = event_payload()
    file_path = spool / f"{event['event_id']}.json"
    file_path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
    sender_calls: list[str] = []

    first = process_chart_alert_spool(repository, spool, send=True, bot_token="test-token", chat_id="test-chat",
        sender=lambda _token, _chat, message, **_kwargs: sender_calls.append(message) or "42")
    second = process_chart_alert_spool(repository, spool, send=True, bot_token="test-token", chat_id="test-chat",
        sender=lambda *_args, **_kwargs: sender_calls.append("duplicate") or "43")

    assert first["sent_count"] == 1
    assert second["sent_count"] == 0
    assert len(sender_calls) == 1
    assert not file_path.exists()
    with repository.connect() as connection:
        row = connection.execute("SELECT status, attempts, telegram_message_id FROM chart_alert_outbox WHERE event_id = ?", (event["event_id"],)).fetchone()
    assert tuple(row) == ("sent", 1, "42")


def test_chart_alert_transport_error_is_ambiguous_and_not_resent(tmp_path: Path) -> None:
    repository = repository_with_focus_reports(tmp_path)
    repository.migrate_schema()
    spool = tmp_path / "spool"
    spool.mkdir()
    event = event_payload("forming")
    (spool / f"{event['event_id']}.json").write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
    calls = 0

    def fail_once(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("may have been accepted")

    first = process_chart_alert_spool(repository, spool, send=True, bot_token="test-token", chat_id="test-chat", sender=fail_once)
    second = process_chart_alert_spool(repository, spool, send=True, bot_token="test-token", chat_id="test-chat", sender=fail_once)

    assert first["ambiguous_count"] == 1
    assert second["sent_count"] == 0
    assert calls == 1
    with repository.connect() as connection:
        row = connection.execute("SELECT status, attempts FROM chart_alert_outbox WHERE event_id = ?", (event["event_id"],)).fetchone()
    assert tuple(row) == ("ambiguous", 1)


def test_chart_alert_cli_defaults_to_preview_and_requires_send_for_watch_mode() -> None:
    parser = build_parser()
    preview = parser.parse_args(["chart-alerts-dispatch"])
    sender = parser.parse_args(["chart-alerts-dispatch", "--send", "--watch", "--interval-seconds", "5"])

    assert preview.send is False
    assert preview.watch is False
    assert sender.send is True
    assert sender.watch is True


def test_concurrent_chart_alert_recovery_does_not_remove_a_new_lock_owner(tmp_path: Path) -> None:
    spool = tmp_path / "ChartLab" / "alert-spool"
    spool.mkdir(parents=True)
    lock_path = spool.parent / "alert-dispatch.lock"
    lock_path.write_text(json.dumps({"pid": 2_147_483_647, "token": "dead"}), encoding="utf-8")
    child_code = "\n".join((
        "import sys, time",
        "sys.path.insert(0, sys.argv[1])",
        "sys.path.insert(0, sys.argv[3])",
        "from pathlib import Path",
        "from stock_monitor.chart_alerts import _chart_alert_dispatch_lock",
        "try:",
        "    with _chart_alert_dispatch_lock(Path(sys.argv[2])):",
        "        print('acquired', flush=True)",
        "        time.sleep(30)",
        "except ValueError as error:",
        "    print(f'busy:{error}', flush=True)",
        "    sys.exit(2)",
    ))
    process = None
    try:
        process = subprocess.Popen(
            [sys._base_executable, "-c", child_code, str(Path(__file__).resolve().parents[1] / "src"), str(spool), str(Path(sys.prefix) / "Lib" / "site-packages")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "acquired"
        with pytest.raises(ValueError, match="chart-alert-dispatch-owned-elsewhere"):
            with chart_alerts._chart_alert_dispatch_lock(spool):
                raise AssertionError("a second dispatcher must not acquire the native lock")
        process.kill()
        assert process.wait(timeout=5) != 0
        with exclusive_file_lock(lock_path, blocking=False) as handle:
            native_lock = handle.read()
        assert native_lock.endswith(b"\n" + FILE_LOCK_MARKER)

        with chart_alerts._chart_alert_dispatch_lock(spool):
            pass
        assert lock_path.read_bytes() == native_lock
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_chart_alert_dispatch_fails_closed_for_a_live_legacy_owner(tmp_path: Path, monkeypatch) -> None:
    spool = tmp_path / "ChartLab" / "alert-spool"
    spool.mkdir(parents=True)
    lock_path = spool.parent / "alert-dispatch.lock"
    legacy_lock = json.dumps({"pid": os.getpid(), "token": "legacy-owner"})
    lock_path.write_text(legacy_lock, encoding="utf-8")
    monkeypatch.setattr(chart_alerts, "_windows_dispatch_lock_stale", lambda _pid: False)
    with pytest.raises(ValueError, match="chart-alert-dispatch-owned-elsewhere"):
        with chart_alerts._chart_alert_dispatch_lock(spool):
            raise AssertionError("a live legacy owner must remain exclusive")
    assert lock_path.read_text(encoding="utf-8") == legacy_lock


def test_windows_legacy_lock_probe_uses_waitable_process_handles(monkeypatch) -> None:
    if os.name != "nt":
        pytest.skip("Windows process handles are platform-specific")
    process = subprocess.Popen([sys._base_executable, "-c", "import time; time.sleep(30)"])

    def forbidden_kill(*_args) -> None:
        raise AssertionError("Windows liveness checks must not call os.kill")

    try:
        monkeypatch.setattr(chart_alerts.os, "kill", forbidden_kill)
        legacy_lock = json.dumps({"pid": process.pid, "token": "legacy-owner"}).encode("utf-8")
        assert chart_alerts._stale_dispatch_lock(legacy_lock) is False
        process.kill()
        process.wait(timeout=5)
        assert chart_alerts._stale_dispatch_lock(legacy_lock) is True
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
