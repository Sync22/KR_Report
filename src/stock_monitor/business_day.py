from __future__ import annotations

from datetime import date, datetime, time, timedelta


def is_business_day(target: date, holiday_overrides: set[date] | frozenset[date] | None = None) -> bool:
    holidays = holiday_overrides or set()
    return target.weekday() < 5 and target not in holidays


def previous_business_day(
    reference: date,
    holiday_overrides: set[date] | frozenset[date] | None = None,
) -> date:
    probe = reference - timedelta(days=1)
    while not is_business_day(probe, holiday_overrides):
        probe -= timedelta(days=1)
    return probe


def next_business_day(
    reference: date,
    holiday_overrides: set[date] | frozenset[date] | None = None,
) -> date:
    probe = reference + timedelta(days=1)
    while not is_business_day(probe, holiday_overrides):
        probe += timedelta(days=1)
    return probe


def derive_business_date(
    published_at: date | datetime,
    holiday_overrides: set[date] | frozenset[date] | None = None,
) -> date:
    probe = published_at.date() if isinstance(published_at, datetime) else published_at
    while not is_business_day(probe, holiday_overrides):
        probe -= timedelta(days=1)
    return probe


def is_within_time_window(current: time, start: time, end: time) -> bool:
    return start <= current <= end
