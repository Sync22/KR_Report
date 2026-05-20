from datetime import date, datetime
from zoneinfo import ZoneInfo

from stock_monitor.models import Opinion, Report
from stock_monitor.summary import build_daily_summaries


def _report(
    *,
    stock_name: str,
    stock_code: str | None = "005930",
    broker_name: str,
    published_at: datetime,
    target_price_value: int | None,
    opinion_normalized: str,
) -> Report:
    return Report(
        stock_name=stock_name,
        stock_code=stock_code,
        title=f"{stock_name} update",
        broker_name=broker_name,
        published_at=published_at,
        business_date=date(2026, 4, 24),
        collected_at=published_at,
        target_price_value=target_price_value,
        opinion_normalized=opinion_normalized,
    ).with_identity()


def test_build_daily_summaries_groups_brokers_and_target_range() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=92_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=101_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone),
            target_price_value=None,
            opinion_normalized=Opinion.BUY.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.stock_name == "삼성전자"
    assert summary.mention_count == 3
    assert summary.broker_display == "NH투자증권(2), KB증권(1)"
    assert summary.target_price_min == 92_000
    assert summary.target_price_max == 101_000
    assert summary.dominant_opinion == Opinion.BUY.value


def test_build_daily_summaries_ignores_na_opinion_for_dominant_opinion() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=None,
            opinion_normalized=Opinion.NA.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=101_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="신한투자증권",
            published_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone),
            target_price_value=None,
            opinion_normalized=Opinion.NA.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert summaries[0].target_price_min == 101_000
    assert summaries[0].target_price_max == 101_000
    assert summaries[0].dominant_opinion == Opinion.BUY.value


def test_build_daily_summaries_uses_latest_report_per_broker_for_opinion() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=92_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=91_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone),
            target_price_value=101_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert summaries[0].dominant_opinion == Opinion.NEUTRAL.value


def test_build_daily_summaries_uses_opinion_priority_when_broker_counts_tie() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=92_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
        _report(
            stock_name="삼성전자",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=101_000,
            opinion_normalized=Opinion.BUY.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert summaries[0].dominant_opinion == Opinion.BUY.value


def test_build_daily_summaries_keeps_na_opinion_only_when_no_valid_opinion_exists() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="삼성전자",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=None,
            opinion_normalized=Opinion.NA.value,
        )
    ]

    summaries = build_daily_summaries(reports)

    assert summaries[0].target_price_min is None
    assert summaries[0].target_price_max is None
    assert summaries[0].dominant_opinion == Opinion.NA.value


def test_build_daily_summaries_collapses_missing_and_present_stock_code() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        Report(
            stock_name="삼성전자",
            stock_code=None,
            title="리포트 A",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            business_date=date(2026, 4, 24),
            collected_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            opinion_normalized=Opinion.BUY.value,
        ).with_identity(),
        Report(
            stock_name="삼성전자",
            stock_code="005930",
            title="리포트 B",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            business_date=date(2026, 4, 24),
            collected_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            opinion_normalized=Opinion.NEUTRAL.value,
        ).with_identity(),
    ]

    summaries = build_daily_summaries(reports)

    assert len(summaries) == 1
    assert summaries[0].stock_code == "005930"


def test_build_daily_summaries_groups_same_code_even_when_stock_name_changes() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=60_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="SK Telecom",
            stock_code="017670",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=62_000,
            opinion_normalized=Opinion.BUY.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert len(summaries) == 1
    assert summaries[0].stock_code == "017670"
    assert summaries[0].stock_name == "SK Telecom"
    assert summaries[0].mention_count == 2


def test_build_daily_summaries_keeps_same_name_different_codes_separate() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="HD현대",
            stock_code="267250",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=80_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="HD현대",
            stock_code="329180",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=45_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert len(summaries) == 2
    assert {summary.stock_code for summary in summaries} == {"267250", "329180"}


def test_build_daily_summaries_keeps_missing_code_as_name_group_when_code_match_is_ambiguous() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    reports = [
        _report(
            stock_name="HD현대",
            stock_code="267250",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone),
            target_price_value=80_000,
            opinion_normalized=Opinion.BUY.value,
        ),
        _report(
            stock_name="HD현대",
            stock_code="329180",
            broker_name="KB증권",
            published_at=datetime(2026, 4, 24, 10, 0, tzinfo=timezone),
            target_price_value=45_000,
            opinion_normalized=Opinion.NEUTRAL.value,
        ),
        _report(
            stock_name="HD현대",
            stock_code=None,
            broker_name="신한투자증권",
            published_at=datetime(2026, 4, 24, 11, 0, tzinfo=timezone),
            target_price_value=82_000,
            opinion_normalized=Opinion.BUY.value,
        ),
    ]

    summaries = build_daily_summaries(reports)

    assert len(summaries) == 3
    fallback = [summary for summary in summaries if summary.stock_code is None]
    assert len(fallback) == 1
    assert fallback[0].mention_count == 1
