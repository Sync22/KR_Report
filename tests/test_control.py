from datetime import date, datetime

from stock_monitor.notify.control import (
    PendingStockSelectionCandidate,
    TelegramControlState,
    load_control_state,
    parse_telegram_command,
    save_control_state,
)


def test_control_state_tracks_delivered_count_per_business_date() -> None:
    state = TelegramControlState()
    business_date = date(2026, 4, 24)

    state.set_delivered_for(business_date, 7)

    assert state.active_business_date == "2026-04-24"
    assert state.delivered_for(business_date) == 7


def test_control_state_tracks_pending_stock_selection() -> None:
    state = TelegramControlState()
    candidates = [
        PendingStockSelectionCandidate(
            stock_code="005930",
            stock_name="삼성전자",
            market_type="코스피",
            source_url="https://stock.naver.com/domestic/stock/005930/total",
        )
    ]

    state.set_pending_stock_selection(
        query="삼성전자",
        command_name="stock_lookup",
        candidates=candidates,
        expires_at=datetime(2026, 4, 26, 8, 5, 0),
    )

    assert state.pending_stock_selection is not None
    assert state.pending_stock_selection.query == "삼성전자"
    assert state.pending_stock_selection.candidates[0].stock_code == "005930"


def test_control_state_tracks_active_intraday_delivery() -> None:
    state = TelegramControlState()
    created_at = datetime(2026, 4, 27, 12, 0, 0)

    state.set_active_intraday_delivery(
        batch_id="batch-1",
        created_at=created_at,
        delivered_count=7,
    )

    assert state.active_message_kind == "intraday"
    assert state.active_intraday_batch_id == "batch-1"
    assert state.active_intraday_created_at == created_at.isoformat()
    assert state.active_intraday_delivered_count == 7


def test_control_state_persists_memo_applied_update_ids(tmp_path) -> None:
    path = tmp_path / "telegram_control.json"
    state = TelegramControlState(last_update_id=10)
    state.mark_memo_update_applied(11)
    state.mark_memo_update_applied(11)
    state.mark_memo_update_applied(12)
    state.mark_check_update_applied(13)
    state.mark_check_update_applied(13)

    save_control_state(path, state)
    loaded = load_control_state(path)

    assert loaded.memo_applied_update_ids == (11, 12)
    assert loaded.has_applied_memo_update(11)
    assert not loaded.has_applied_memo_update(13)
    assert loaded.check_applied_update_ids == (13,)
    assert loaded.has_applied_check_update(13)
    assert not loaded.has_applied_check_update(14)


def test_save_control_state_atomically_replaces_existing_file(tmp_path) -> None:
    path = tmp_path / "nested" / "telegram_control.json"
    save_control_state(path, TelegramControlState(last_update_id=1))
    save_control_state(path, TelegramControlState(last_update_id=2, active_message_kind="daily"))

    loaded = load_control_state(path)

    assert loaded.last_update_id == 2
    assert loaded.active_message_kind == "daily"
    assert list(path.parent.glob("*.tmp")) == []


def test_parse_telegram_command_supports_text_slash_and_selection_inputs() -> None:
    assert parse_telegram_command("다음") == ("next", None)
    assert parse_telegram_command("/다음목록") == ("next", None)
    assert parse_telegram_command("/전부") == ("all", None)
    assert parse_telegram_command("/처음@TestBot") == ("reset", None)
    assert parse_telegram_command("/명령어") == ("help", None)
    assert parse_telegram_command("/메모 웹뷰에 섹터 정리 추가") == ("memo", "웹뷰에 섹터 정리 추가")
    assert parse_telegram_command("/메모") == ("memo", None)
    assert parse_telegram_command("/한줄") == ("market_commentary", None)
    assert parse_telegram_command("/코멘트 2026-05-18") == ("market_commentary", "2026-05-18")
    assert parse_telegram_command("/사진 리포트 예시") == ("photo", "리포트 예시")
    assert parse_telegram_command("/진행 KRX OpenAPI 상태 확인") == ("progress_request", "KRX OpenAPI 상태 확인")
    assert parse_telegram_command("/progress web-view QA") == ("progress_request", "web-view QA")
    assert parse_telegram_command("진행 건강상태 체크") == ("progress_request", "건강상태 체크")
    assert parse_telegram_command("/종목검색 017670") == ("stock_lookup", "017670")
    assert parse_telegram_command("/종목코드 SK텔레콤") == ("stock_code_lookup", "SK텔레콤")
    assert parse_telegram_command("2") == ("selection", "2")
    assert parse_telegram_command("/없는명령어") == ("unknown_slash", "/없는명령어")
