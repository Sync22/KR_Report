from datetime import time

from stock_monitor.business_day import is_within_time_window


def test_is_within_time_window_inclusive() -> None:
    start = time(8, 0)
    end = time(16, 0)

    assert is_within_time_window(time(8, 0), start, end) is True
    assert is_within_time_window(time(16, 0), start, end) is True
    assert is_within_time_window(time(7, 59), start, end) is False
    assert is_within_time_window(time(16, 1), start, end) is False
