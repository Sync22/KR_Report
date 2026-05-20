from datetime import date

from datetime import datetime

from stock_monitor.config import DEFAULT_MARKET_HOLIDAYS
from stock_monitor.business_day import derive_business_date, next_business_day, previous_business_day


def test_previous_business_day_skips_weekend() -> None:
    assert previous_business_day(date(2026, 4, 27)) == date(2026, 4, 24)


def test_next_business_day_respects_holiday_override() -> None:
    overrides = {date(2026, 5, 5)}
    assert next_business_day(date(2026, 5, 4), overrides) == date(2026, 5, 6)


def test_derive_business_date_rolls_back_weekend_and_holiday() -> None:
    overrides = {date(2026, 5, 5)}
    assert derive_business_date(datetime(2026, 4, 26, 9, 0, 0)) == date(2026, 4, 24)
    assert derive_business_date(datetime(2026, 5, 5, 9, 0, 0), overrides) == date(2026, 5, 4)


def test_default_holidays_cover_2024_2025_market_closures() -> None:
    assert previous_business_day(date(2024, 4, 11), DEFAULT_MARKET_HOLIDAYS) == date(2024, 4, 9)
    assert previous_business_day(date(2025, 1, 31), DEFAULT_MARKET_HOLIDAYS) == date(2025, 1, 24)
    assert previous_business_day(date(2025, 6, 4), DEFAULT_MARKET_HOLIDAYS) == date(2025, 6, 2)
