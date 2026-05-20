from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


NEXT_COMMANDS = {"다음", "더", "더보기", "다음목록", "next", "more", "/다음", "/다음목록", "/next"}
ALL_COMMANDS = {"전부", "전체", "all", "/전부", "/all"}
RESET_COMMANDS = {"처음", "처음부터", "reset", "start", "/처음", "/reset"}
HELP_COMMANDS = {"도움말", "명령어", "help", "commands", "/도움말", "/명령어", "/help", "/commands"}
LOOKUP_COMMAND_NAMES = {"종목검색", "lookup", "stock", "search"}
CODE_COMMAND_NAMES = {"종목코드", "code"}
MEMO_COMMAND_NAMES = {"메모", "memo", "note"}
MARKET_COMMENTARY_COMMAND_NAMES = {"한줄", "코멘트", "시장코멘트", "commentary", "comment"}
PHOTO_COMMAND_NAMES = {"사진", "photo", "image"}
PROGRESS_COMMAND_NAMES = {"진행", "progress", "task"}
CHECK_COMMAND_NAMES = {"체크", "check"}
STATUS_COMMAND_NAMES = {"상태", "status"}
TODAY_RUN_COMMAND_NAMES = {"오늘돌아", "오늘돌아?", "today"}
SCHEDULE_STATUS_COMMAND_NAMES = {"스케줄상태", "schedule"}
WEB_VIEW_URL_COMMAND_NAMES = {"웹뷰주소", "webview"}


@dataclass(frozen=True)
class PendingStockSelectionCandidate:
    stock_code: str
    stock_name: str
    market_type: str
    source_url: str


@dataclass(frozen=True)
class PendingStockSelection:
    query: str
    command_name: str
    candidates: tuple[PendingStockSelectionCandidate, ...]
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now


@dataclass
class TelegramControlState:
    last_update_id: int = 0
    active_message_kind: str | None = None
    active_business_date: str | None = None
    delivered_counts: dict[str, int] = field(default_factory=dict)
    active_intraday_batch_id: str | None = None
    active_intraday_created_at: str | None = None
    active_intraday_delivered_count: int = 0
    pending_stock_selection: PendingStockSelection | None = None
    pending_photo_note: str | None = None
    memo_applied_update_ids: tuple[int, ...] = ()
    check_applied_update_ids: tuple[int, ...] = ()
    photo_applied_update_ids: tuple[int, ...] = ()
    progress_applied_update_ids: tuple[int, ...] = ()

    def delivered_for(self, business_date: date) -> int:
        return self.delivered_counts.get(business_date.isoformat(), 0)

    def set_delivered_for(self, business_date: date, delivered_count: int) -> None:
        key = business_date.isoformat()
        self.active_message_kind = "daily"
        self.active_business_date = key
        self.delivered_counts[key] = delivered_count
        self.active_intraday_batch_id = None
        self.active_intraday_created_at = None
        self.active_intraday_delivered_count = 0

    def set_active_intraday_delivery(
        self,
        *,
        batch_id: str,
        created_at: datetime,
        delivered_count: int,
    ) -> None:
        self.active_message_kind = "intraday"
        self.active_intraday_batch_id = batch_id
        self.active_intraday_created_at = created_at.isoformat()
        self.active_intraday_delivered_count = delivered_count

    def clear_active_intraday_delivery(self) -> None:
        self.active_intraday_batch_id = None
        self.active_intraday_created_at = None
        self.active_intraday_delivered_count = 0
        if self.active_message_kind == "intraday":
            self.active_message_kind = None

    def set_pending_stock_selection(
        self,
        *,
        query: str,
        command_name: str,
        candidates: list[PendingStockSelectionCandidate],
        expires_at: datetime,
    ) -> None:
        self.pending_stock_selection = PendingStockSelection(
            query=query,
            command_name=command_name,
            candidates=tuple(candidates),
            expires_at=expires_at,
        )

    def clear_pending_stock_selection(self) -> None:
        self.pending_stock_selection = None

    def set_pending_photo_note(self, note: str | None) -> None:
        self.pending_photo_note = (note or "").strip() or "사진 참고자료"

    def clear_pending_photo_note(self) -> None:
        self.pending_photo_note = None

    def has_applied_memo_update(self, update_id: int) -> bool:
        return update_id in set(self.memo_applied_update_ids)

    def mark_memo_update_applied(self, update_id: int, *, keep_last: int = 200) -> None:
        existing = list(self.memo_applied_update_ids)
        if update_id not in existing:
            existing.append(update_id)
        self.memo_applied_update_ids = tuple(existing[-keep_last:])

    def has_applied_check_update(self, update_id: int) -> bool:
        return update_id in set(self.check_applied_update_ids)

    def mark_check_update_applied(self, update_id: int, *, keep_last: int = 200) -> None:
        existing = list(self.check_applied_update_ids)
        if update_id not in existing:
            existing.append(update_id)
        self.check_applied_update_ids = tuple(existing[-keep_last:])

    def has_applied_photo_update(self, update_id: int) -> bool:
        return update_id in set(self.photo_applied_update_ids)

    def mark_photo_update_applied(self, update_id: int, *, keep_last: int = 200) -> None:
        existing = list(self.photo_applied_update_ids)
        if update_id not in existing:
            existing.append(update_id)
        self.photo_applied_update_ids = tuple(existing[-keep_last:])

    def has_applied_progress_update(self, update_id: int) -> bool:
        return update_id in set(self.progress_applied_update_ids)

    def mark_progress_update_applied(self, update_id: int, *, keep_last: int = 200) -> None:
        existing = list(self.progress_applied_update_ids)
        if update_id not in existing:
            existing.append(update_id)
        self.progress_applied_update_ids = tuple(existing[-keep_last:])


def load_control_state(path: Path) -> TelegramControlState:
    if not path.exists():
        return TelegramControlState()

    payload = json.loads(path.read_text(encoding="utf-8"))
    pending_payload = payload.get("pending_stock_selection")
    pending_selection = None
    if isinstance(pending_payload, dict):
        raw_candidates = pending_payload.get("candidates", [])
        candidates = tuple(
            PendingStockSelectionCandidate(
                stock_code=str(item.get("stock_code") or ""),
                stock_name=str(item.get("stock_name") or ""),
                market_type=str(item.get("market_type") or ""),
                source_url=str(item.get("source_url") or ""),
            )
            for item in raw_candidates
            if isinstance(item, dict)
            and item.get("stock_code")
            and item.get("stock_name")
            and item.get("source_url")
        )
        expires_at_raw = pending_payload.get("expires_at")
        if candidates and isinstance(expires_at_raw, str):
            pending_selection = PendingStockSelection(
                query=str(pending_payload.get("query") or "").strip(),
                command_name=str(pending_payload.get("command_name") or "stock_lookup").strip() or "stock_lookup",
                candidates=candidates,
                expires_at=datetime.fromisoformat(expires_at_raw),
            )

    return TelegramControlState(
        last_update_id=int(payload.get("last_update_id", 0)),
        active_message_kind=str(payload.get("active_message_kind") or "").strip() or None,
        active_business_date=payload.get("active_business_date"),
        delivered_counts={str(key): int(value) for key, value in payload.get("delivered_counts", {}).items()},
        active_intraday_batch_id=str(payload.get("active_intraday_batch_id") or "").strip() or None,
        active_intraday_created_at=str(payload.get("active_intraday_created_at") or "").strip() or None,
        active_intraday_delivered_count=int(payload.get("active_intraday_delivered_count", 0)),
        pending_stock_selection=pending_selection,
        pending_photo_note=str(payload.get("pending_photo_note") or "").strip() or None,
        memo_applied_update_ids=tuple(
            int(item)
            for item in payload.get("memo_applied_update_ids", [])
            if isinstance(item, int) or str(item).isdigit()
        ),
        check_applied_update_ids=tuple(
            int(item)
            for item in payload.get("check_applied_update_ids", [])
            if isinstance(item, int) or str(item).isdigit()
        ),
        photo_applied_update_ids=tuple(
            int(item)
            for item in payload.get("photo_applied_update_ids", [])
            if isinstance(item, int) or str(item).isdigit()
        ),
        progress_applied_update_ids=tuple(
            int(item)
            for item in payload.get("progress_applied_update_ids", [])
            if isinstance(item, int) or str(item).isdigit()
        ),
    )


def save_control_state(path: Path, state: TelegramControlState) -> None:
    pending_payload = None
    if state.pending_stock_selection is not None:
        pending_payload = {
            "query": state.pending_stock_selection.query,
            "command_name": state.pending_stock_selection.command_name,
            "expires_at": state.pending_stock_selection.expires_at.isoformat(),
            "candidates": [
                {
                    "stock_code": candidate.stock_code,
                    "stock_name": candidate.stock_name,
                    "market_type": candidate.market_type,
                    "source_url": candidate.source_url,
                }
                for candidate in state.pending_stock_selection.candidates
            ],
        }

    payload = {
        "last_update_id": state.last_update_id,
        "active_message_kind": state.active_message_kind,
        "active_business_date": state.active_business_date,
        "delivered_counts": state.delivered_counts,
        "active_intraday_batch_id": state.active_intraday_batch_id,
        "active_intraday_created_at": state.active_intraday_created_at,
        "active_intraday_delivered_count": state.active_intraday_delivered_count,
        "pending_stock_selection": pending_payload,
        "pending_photo_note": state.pending_photo_note,
        "memo_applied_update_ids": list(state.memo_applied_update_ids),
        "check_applied_update_ids": list(state.check_applied_update_ids),
        "photo_applied_update_ids": list(state.photo_applied_update_ids),
        "progress_applied_update_ids": list(state.progress_applied_update_ids),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(serialized, encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def parse_telegram_command(text: str) -> tuple[str | None, str | None]:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return None, None

    if normalized.isdigit():
        return "selection", normalized

    canonical_text = normalized
    command_name = None
    remainder = ""
    if normalized.startswith("/"):
        token, _, remainder = normalized.partition(" ")
        command_name = token[1:].split("@", 1)[0].lower()
        canonical_text = f"/{command_name}"
        if remainder:
            canonical_text = f"{canonical_text} {remainder.strip()}"

    lowered = canonical_text.lower()
    if lowered in {item.lower() for item in NEXT_COMMANDS}:
        return "next", None
    if lowered in {item.lower() for item in ALL_COMMANDS}:
        return "all", None
    if lowered in {item.lower() for item in RESET_COMMANDS}:
        return "reset", None
    if lowered in {item.lower() for item in HELP_COMMANDS}:
        return "help", None

    if not normalized.startswith("/"):
        return None, None

    if command_name in LOOKUP_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "stock_lookup", argument
    if command_name in CODE_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "stock_code_lookup", argument
    if command_name in MEMO_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "memo", argument
    if command_name in MARKET_COMMENTARY_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "market_commentary", argument
    if command_name in PHOTO_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "photo", argument
    if command_name in PROGRESS_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "progress_request", argument
    if command_name in CHECK_COMMAND_NAMES:
        argument = remainder.strip() or None
        return "check", argument
    if command_name in STATUS_COMMAND_NAMES:
        return "operator_status", None
    if command_name in TODAY_RUN_COMMAND_NAMES:
        return "today_status", None
    if command_name in SCHEDULE_STATUS_COMMAND_NAMES:
        return "schedule_status", None
    if command_name in WEB_VIEW_URL_COMMAND_NAMES:
        return "webview_url", None
    return "unknown_slash", normalized
