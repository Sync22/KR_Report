from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from stock_monitor.models import DailyStockSummary, OPINION_PRIORITY, Opinion, Report, collapse_whitespace


def _dominant_opinion(reports: list[Report]) -> str:
    broker_representatives = [
        max(
            group,
            key=lambda report: (
                report.published_at,
                report.collected_at,
                report.identity_key or "",
            ),
        )
        for group in _group_by_broker(reports).values()
    ]
    counts = Counter(
        report.opinion_normalized
        for report in broker_representatives
        if report.opinion_normalized != Opinion.NA.value
    )
    if not counts:
        return Opinion.NA.value
    return max(
        counts.items(),
        key=lambda item: (item[1], OPINION_PRIORITY.get(item[0], -1)),
    )[0]


def _group_by_broker(reports: list[Report]) -> dict[str, list[Report]]:
    grouped: dict[str, list[Report]] = defaultdict(list)
    for report in reports:
        grouped[collapse_whitespace(report.broker_name)].append(report)
    return grouped


def _summary_group_key(report: Report) -> tuple[object, ...]:
    if report.stock_code:
        return (report.business_date, "code", report.stock_code)
    return (report.business_date, "name", collapse_whitespace(report.stock_name))


def _representative_stock_name(reports: list[Report]) -> str:
    names: dict[str, tuple[int, datetime, datetime, str]] = {}
    for report in reports:
        stock_name = collapse_whitespace(report.stock_name)
        previous = names.get(stock_name)
        latest_key = (
            report.published_at,
            report.collected_at,
            report.identity_key or "",
        )
        if previous is None:
            names[stock_name] = (1, *latest_key)
            continue
        count, latest_published_at, latest_collected_at, latest_identity = previous
        if latest_key > (latest_published_at, latest_collected_at, latest_identity):
            names[stock_name] = (count + 1, *latest_key)
        else:
            names[stock_name] = (count + 1, latest_published_at, latest_collected_at, latest_identity)
    return max(names.items(), key=lambda item: item[1])[0]


def _group_reports_for_summary(reports: list[Report]) -> dict[tuple[object, ...], list[Report]]:
    grouped: dict[tuple[object, ...], list[Report]] = defaultdict(list)
    coded_keys_by_name: dict[tuple[object, ...], set[tuple[object, ...]]] = defaultdict(set)

    for report in reports:
        if not report.stock_code:
            continue
        key = _summary_group_key(report)
        grouped[key].append(report)
        coded_keys_by_name[(report.business_date, collapse_whitespace(report.stock_name))].add(key)

    for report in reports:
        if report.stock_code:
            continue
        matching_keys = coded_keys_by_name[(report.business_date, collapse_whitespace(report.stock_name))]
        key = next(iter(matching_keys)) if len(matching_keys) == 1 else _summary_group_key(report)
        grouped[key].append(report)

    return grouped


def _select_stock_code(reports: list[Report]) -> str | None:
    available_codes = [report.stock_code for report in reports if report.stock_code]
    if not available_codes:
        return None
    code_counts = Counter(available_codes)
    return max(code_counts.items(), key=lambda item: (item[1], item[0]))[0]


def build_daily_summaries(
    reports: list[Report],
    *,
    timezone: str = "Asia/Seoul",
    generated_at: datetime | None = None,
) -> list[DailyStockSummary]:
    if not reports:
        return []

    timestamp = generated_at or datetime.now(ZoneInfo(timezone))
    grouped = _group_reports_for_summary(reports)

    summaries: list[DailyStockSummary] = []
    for group_key, group in sorted(grouped.items()):
        business_date = group_key[0]
        stock_name = _representative_stock_name(group)
        broker_counts = Counter(report.broker_name for report in group)
        broker_display = ", ".join(
            f"{broker}({count})"
            for broker, count in sorted(
                broker_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        target_values = sorted(
            report.target_price_value
            for report in group
            if report.target_price_value is not None
        )
        summaries.append(
            DailyStockSummary(
                business_date=business_date,
                stock_name=stock_name,
                stock_code=_select_stock_code(group),
                mention_count=len(group),
                broker_display=broker_display,
                target_price_min=target_values[0] if target_values else None,
                target_price_max=target_values[-1] if target_values else None,
                dominant_opinion=_dominant_opinion(group),
                generated_at=timestamp,
            )
        )

    return summaries
