from __future__ import annotations

import hashlib
import errno
import json
import os
import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from contextlib import contextmanager
from uuid import uuid4
from zoneinfo import ZoneInfo

from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.notify.telegram import send_telegram_message

MAX_SPOOL_FILES = 500
MAX_EVENT_BYTES = 32 * 1024
SUPPORTED_RULES = {"flag-m1-v1", "triangle-m1-v1", "horizontal-m1-v1"}
SUPPORTED_KINDS = {
    "bull-flag", "bear-flag", "ascending-triangle", "descending-triangle", "symmetrical-triangle",
    "support-breakout", "resistance-breakout",
}
SUPPORTED_STATES = {"forming", "observed-breakout", "observed-crossing"}
SUPPORTED_DIRECTIONS = {"up", "down", "neutral"}
KIND_DIRECTIONS = {
    "bull-flag": "up",
    "bear-flag": "down",
    "ascending-triangle": "neutral",
    "descending-triangle": "neutral",
    "symmetrical-triangle": "neutral",
    "support-breakout": "down",
    "resistance-breakout": "up",
}
EVENT_KEYS = {
    "schema_version", "event_id", "watch_id", "report_business_date", "stock_code", "stock_name", "report_count",
    "report_reason", "rule_key", "rule_version", "timeframe", "kind", "direction", "observed_state",
    "basis_start_time", "basis_bar_time", "source", "source_fetched_at", "finality", "observed_at",
}

Sender = Callable[..., str]


def default_chart_alert_spool_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    state_root = values.get("LOCALAPPDATA") or values.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_root) / "StockMonitor" / "ChartLab" / "alert-spool"


def chart_alert_event_id(
    *, watch_id: str, symbol: str, report_business_date: str, stock_name: str, report_count: int,
    rule_version: str, kind: str, direction: str, basis_start_time: str, status: str,
) -> str:
    identity = "|".join((watch_id, symbol, report_business_date, stock_name, str(report_count), "1m", rule_version, kind, direction, basis_start_time, status))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def validate_chart_alert_event(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != EVENT_KEYS:
        raise ValueError("invalid-chart-alert-event")
    event = value
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ValueError("invalid-chart-alert-event")
    event_id = event["event_id"]
    business_date = event["report_business_date"]
    stock_code = event["stock_code"]
    report_count = event["report_count"]
    if not isinstance(event_id, str) or not re.fullmatch(r"[a-f0-9]{64}", event_id):
        raise ValueError("invalid-chart-alert-event")
    if not isinstance(business_date, str) or not _is_date(business_date) or not isinstance(stock_code, str) or not re.fullmatch(r"\d{6}", stock_code):
        raise ValueError("invalid-chart-alert-event")
    if event["watch_id"] != f"{business_date}-{stock_code}" or type(report_count) is not int or not 2 <= report_count <= 1000:
        raise ValueError("invalid-chart-alert-event")
    name = event["stock_name"]
    if not isinstance(name, str) or not name.strip() or len(name) > 120 or _has_controls(name):
        raise ValueError("invalid-chart-alert-event")
    rule_version = event["rule_version"]
    if rule_version not in SUPPORTED_RULES or event["rule_key"] != rule_version:
        raise ValueError("invalid-chart-alert-event")
    if event["report_reason"] != "리포트 집중" or event["timeframe"] != "1m" or event["kind"] not in SUPPORTED_KINDS:
        raise ValueError("invalid-chart-alert-event")
    if event["direction"] not in SUPPORTED_DIRECTIONS or event["observed_state"] not in SUPPORTED_STATES:
        raise ValueError("invalid-chart-alert-event")
    if event["direction"] != KIND_DIRECTIONS[event["kind"]]:
        raise ValueError("invalid-chart-alert-event")
    if event["source"] != "Toss OpenAPI · 1m candles" or event["finality"] != "unknown":
        raise ValueError("invalid-chart-alert-event")
    for field in ("basis_start_time", "basis_bar_time", "source_fetched_at", "observed_at"):
        if not _is_offset_datetime(event[field]):
            raise ValueError("invalid-chart-alert-event")
    expected_id = chart_alert_event_id(
        watch_id=event["watch_id"], symbol=stock_code, report_business_date=business_date, stock_name=name,
        report_count=report_count, rule_version=rule_version, kind=event["kind"], direction=event["direction"],
        basis_start_time=event["basis_start_time"], status=event["observed_state"],
    )
    if event_id != expected_id:
        raise ValueError("invalid-chart-alert-event")
    return event


def build_chart_alert_message(event: dict[str, Any]) -> str:
    event = validate_chart_alert_event(event)
    kind = {
        "bull-flag": "상승 깃발 구조", "bear-flag": "하락 깃발 구조", "ascending-triangle": "상승 삼각 구조",
        "descending-triangle": "하락 삼각 구조", "symmetrical-triangle": "대칭 삼각 구조",
        "support-breakout": "지지 경계 하향 관찰", "resistance-breakout": "저항 경계 상향 관찰",
    }[event["kind"]]
    state = {"forming": "형성 관찰", "observed-breakout": "경계 이탈 관찰", "observed-crossing": "경계 교차 관찰"}[event["observed_state"]]
    return "\n".join((
        f"{event['stock_name']}({event['stock_code']}) · 기술 관찰",
        f"1분봉 · {kind} · {state} · 기준 {_display_time(event['basis_bar_time'])}",
        f"Toss OpenAPI · 수집 {_display_time(event['source_fetched_at'])} · 봉 확정 상태 제공 안 됨",
        f"리포트 집중 {event['report_business_date']} · {event['report_count']}건 · 매매·주문 신호 아님",
    ))


def process_chart_alert_spool(
    repository: StockMonitorRepository,
    spool_dir: Path,
    *,
    send: bool = False,
    bot_token: str | None = None,
    chat_id: str | None = None,
    sender: Sender = send_telegram_message,
    limit: int = 50,
) -> dict[str, Any]:
    if not send:
        return _process_chart_alert_spool(repository, spool_dir, send=False, bot_token=bot_token, chat_id=chat_id, sender=sender, limit=limit)
    with _chart_alert_dispatch_lock(spool_dir):
        return _process_chart_alert_spool(repository, spool_dir, send=True, bot_token=bot_token, chat_id=chat_id, sender=sender, limit=limit)


def _process_chart_alert_spool(
    repository: StockMonitorRepository,
    spool_dir: Path,
    *,
    send: bool,
    bot_token: str | None,
    chat_id: str | None,
    sender: Sender,
    limit: int,
) -> dict[str, Any]:
    files = sorted(spool_dir.glob("*.json")) if spool_dir.exists() else []
    if len(files) > MAX_SPOOL_FILES or not 1 <= limit <= 200:
        raise ValueError("chart-alert-spool-limit")
    if send and (not bot_token or not chat_id):
        raise ValueError("telegram-configuration-missing")
    if send and not repository.db_path.exists():
        raise ValueError("chart-alert-schema-required")
    if not repository.db_path.exists():
        return {
            "surface": "chart-alert-dispatch",
            "mode": "dry-run",
            "preview_count": 0,
            "inserted_count": 0,
            "sent_count": 0,
            "ambiguous_count": 0,
            "rejected_count": len(files),
            "previews": [],
        }

    accepted: list[tuple[Path, dict[str, Any], str]] = []
    rejected_count = 0
    for file_path in files:
        try:
            if not re.fullmatch(r"[a-f0-9]{64}\.json", file_path.name) or file_path.stat().st_size > MAX_EVENT_BYTES:
                raise ValueError("invalid-chart-alert-event")
            event = validate_chart_alert_event(json.loads(file_path.read_text(encoding="utf-8")))
            if file_path.stem != event["event_id"]:
                raise ValueError("invalid-chart-alert-event")
            message = build_chart_alert_message(event)
            accepted.append((file_path, event, message))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            rejected_count += 1

    valid_events: list[tuple[Path, dict[str, Any], str]] = []
    with repository.read_session():
        with repository.connect() as connection:
            for item in accepted:
                event = item[1]
                row = connection.execute(
                    "SELECT COUNT(*) FROM reports WHERE business_date = ? AND stock_code = ?",
                    (event["report_business_date"], event["stock_code"]),
                ).fetchone()
                if row and int(row[0]) >= 2:
                    valid_events.append(item)
                else:
                    rejected_count += 1

    if not send:
        return {
            "surface": "chart-alert-dispatch",
            "mode": "dry-run",
            "preview_count": len(valid_events),
            "inserted_count": 0,
            "sent_count": 0,
            "ambiguous_count": 0,
            "rejected_count": rejected_count,
            "previews": [message for _, _, message in valid_events[:limit]],
        }

    _require_chart_alert_table(repository)
    now = datetime.now(timezone.utc).isoformat()
    inserted_count = 0
    with repository.connect() as connection, connection:
        connection.execute(
            "UPDATE chart_alert_outbox SET status = 'ambiguous', last_error_kind = 'interrupted_during_send', updated_at = ? WHERE status = 'sending'",
            (now,),
        )
        for _, event, message in valid_events:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO chart_alert_outbox (
                    event_id, watch_id, report_business_date, stock_code, stock_name, report_count, rule_key, rule_version,
                    timeframe, kind, direction, observed_state, basis_bar_time, source, source_fetched_at, finality,
                    message_text, status, attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)
                """,
                (event["event_id"], event["watch_id"], event["report_business_date"], event["stock_code"], event["stock_name"],
                 event["report_count"], event["rule_key"], event["rule_version"], event["timeframe"], event["kind"],
                 event["direction"], event["observed_state"], event["basis_bar_time"], event["source"],
                 event["source_fetched_at"], event["finality"], message, now, now),
            )
            inserted_count += cursor.rowcount

    for file_path, _, _ in valid_events:
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass

    sent_count = 0
    ambiguous_count = 0
    pending: list[sqlite3.Row] = []
    with repository.connect() as connection:
        connection.row_factory = sqlite3.Row
        pending = connection.execute(
            "SELECT event_id, message_text FROM chart_alert_outbox WHERE status = 'pending' ORDER BY created_at, event_id LIMIT ?",
            (limit,),
        ).fetchall()

    for row in pending:
        event_id = str(row["event_id"])
        started_at = datetime.now(timezone.utc).isoformat()
        with repository.connect() as connection, connection:
            cursor = connection.execute(
                "UPDATE chart_alert_outbox SET status = 'sending', attempts = attempts + 1, updated_at = ? WHERE event_id = ? AND status = 'pending'",
                (started_at, event_id),
            )
        if cursor.rowcount != 1:
            continue
        try:
            message_id = sender(
                bot_token or "", chat_id or "", str(row["message_text"]), timeout_seconds=30,
                max_retries=1, retry_delay_seconds=0,
            )
        except Exception as error:
            ambiguous_count += 1
            finished_at = datetime.now(timezone.utc).isoformat()
            with repository.connect() as connection, connection:
                connection.execute(
                    "UPDATE chart_alert_outbox SET status = 'ambiguous', last_error_kind = ?, updated_at = ? WHERE event_id = ? AND status = 'sending'",
                    (type(error).__name__[:80], finished_at, event_id),
                )
        else:
            sent_count += 1
            finished_at = datetime.now(timezone.utc).isoformat()
            with repository.connect() as connection, connection:
                connection.execute(
                    "UPDATE chart_alert_outbox SET status = 'sent', telegram_message_id = ?, sent_at = ?, updated_at = ? WHERE event_id = ? AND status = 'sending'",
                    (str(message_id)[:80], finished_at, finished_at, event_id),
                )

    return {
        "surface": "chart-alert-dispatch",
        "mode": "send",
        "preview_count": 0,
        "inserted_count": inserted_count,
        "sent_count": sent_count,
        "ambiguous_count": ambiguous_count,
        "rejected_count": rejected_count,
        "previews": [],
    }


@contextmanager
def _chart_alert_dispatch_lock(spool_dir: Path):
    lock_path = spool_dir.parent / "alert-dispatch.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    contents = json.dumps({"pid": os.getpid(), "token": token, "started_at": datetime.now(timezone.utc).isoformat()})
    for attempt in range(2):
        try:
            with lock_path.open("x", encoding="utf-8") as handle:
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
            break
        except FileExistsError:
            if attempt or not _stale_dispatch_lock(lock_path):
                raise ValueError("chart-alert-dispatch-owned-elsewhere")
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
    try:
        yield
    finally:
        try:
            owner = json.loads(lock_path.read_text(encoding="utf-8"))
            if owner.get("pid") == os.getpid() and owner.get("token") == token:
                lock_path.unlink()
        except (AttributeError, FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
            pass


def _stale_dispatch_lock(lock_path: Path) -> bool:
    try:
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        pid = owner.get("pid") if isinstance(owner, dict) else None
        if type(pid) is not int or pid <= 0 or not isinstance(owner.get("token"), str):
            return False
        try:
            os.kill(pid, 0)
            return False
        except OSError as error:
            return isinstance(error, ProcessLookupError) or error.errno == errno.ESRCH or getattr(error, "winerror", None) in (87, 1168)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def _require_chart_alert_table(repository: StockMonitorRepository) -> None:
    with repository.read_session():
        with repository.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chart_alert_outbox'"
            ).fetchone()
    if row is None:
        raise ValueError("chart-alert-schema-required")


def _is_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _is_offset_datetime(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def _has_controls(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _display_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(ZoneInfo("Asia/Seoul")).strftime("%y.%m.%d %H:%M KST")
