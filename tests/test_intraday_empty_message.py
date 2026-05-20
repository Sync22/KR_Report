from datetime import datetime

from stock_monitor.notify.formatter import format_intraday_empty_message


def test_format_intraday_empty_message_uses_short_datetime() -> None:
    message = format_intraday_empty_message(datetime(2026, 4, 27, 12, 30, 0))

    assert message == "장중 신규 리포트가 없습니다 (0건 | 26.04.27 12:30)"
