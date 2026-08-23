from __future__ import annotations

from collections import Counter
from datetime import date, datetime

from stock_monitor.fetch.naver_stock_quote import StockQuoteSnapshot
from stock_monitor.fetch.naver_stock_search import StockCodeLookupEntry
from stock_monitor.models import DailyStockSummary, OPINION_PRIORITY, Report, StockResearchEntry, collapse_whitespace
from stock_monitor.summary import _group_reports_for_summary, build_daily_summaries


_OPINION_LABELS = {
    "buy": "매수",
    "neutral": "중립",
    "sell": "매도",
    "N/A": "의견 없음",
}

_WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def _weekday_label(target: date) -> str:
    return _WEEKDAY_LABELS[target.weekday()]


def _format_short_date(target: date) -> str:
    return target.strftime("%y.%m.%d")


def _format_short_datetime(target: datetime) -> str:
    return target.strftime("%y.%m.%d %H:%M")


def _format_opinion(opinion: str) -> str:
    return _OPINION_LABELS.get(opinion, opinion)


def _format_target_values(min_value: int | None, max_value: int | None) -> str:
    if min_value is None or max_value is None:
        return "-"
    if min_value == max_value:
        return f"{min_value:,}원"
    return f"{min_value:,}원 ~ {max_value:,}원"


def _format_target_range(summary: DailyStockSummary) -> str:
    return _format_target_values(summary.target_price_min, summary.target_price_max)


def _format_total_count(summaries: list[DailyStockSummary]) -> str:
    total_count = sum(summary.mention_count for summary in summaries)
    return f"{total_count:02d}"


def _truncate_broker_names(brokers: list[str], *, limit: int = 3) -> str:
    if len(brokers) <= limit:
        return ", ".join(brokers)
    remaining = len(brokers) - limit
    return f"{', '.join(brokers[:limit])} 외 {remaining}곳"


def _format_broker_display(summary: DailyStockSummary, *, limit: int = 3) -> str:
    brokers = [item.strip() for item in summary.broker_display.split(",") if item.strip()]
    return _truncate_broker_names(brokers, limit=limit)


def _sort_summaries(summaries: list[DailyStockSummary]) -> list[DailyStockSummary]:
    return sorted(summaries, key=lambda item: (-item.mention_count, item.stock_name))


def _format_stock_name(stock_name: str, stock_code: str | None) -> str:
    return f"{stock_name}({stock_code})" if stock_code else stock_name


def _format_quote_fragment(quote: StockQuoteSnapshot | None) -> str | None:
    if quote is None:
        return None
    parts: list[str] = []
    if quote.current_price is not None:
        parts.append(f"현재가 {quote.current_price:,}원")
    if quote.sector_name:
        parts.append(quote.sector_name)
    if not parts:
        return None
    return " | ".join(parts)


def _format_stock_header(stock_name: str, stock_code: str | None, quote: StockQuoteSnapshot | None = None) -> str:
    display_name = _format_stock_name(stock_name, stock_code)
    quote_fragment = _format_quote_fragment(quote)
    return display_name if quote_fragment is None else f"{display_name} | {quote_fragment}"


def _format_briefing_sector_focus(
    summaries: list[DailyStockSummary],
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None,
    *,
    limit: int = 3,
) -> list[str]:
    if not quotes_by_stock_code:
        return ["- 업종 정보 없음"]
    counts: Counter[str] = Counter()
    for summary in summaries:
        if not summary.stock_code:
            continue
        quote = quotes_by_stock_code.get(summary.stock_code)
        if quote is None or not quote.sector_name:
            continue
        counts[quote.sector_name] += summary.mention_count
    if not counts:
        return ["- 업종 정보 없음"]
    return [f"- {name} {count}건" for name, count in counts.most_common(limit)]


def _format_briefing_check_points() -> list[str]:
    return [
        "- 리포트가 몰린 업종과 수급 방향이 같은지 확인",
        "- 목표가 괴리율이 큰 종목은 웹뷰 관찰탭에서 세부 확인",
        "- 당일 현재가는 장 시작 후 변동 가능",
    ]


def _summary_group_lookup_key(summary: DailyStockSummary) -> tuple[object, ...]:
    if summary.stock_code:
        return (summary.business_date, "code", summary.stock_code)
    return (summary.business_date, "name", collapse_whitespace(summary.stock_name))


def _build_intraday_stock_blocks(
    polled_at: datetime,
    reports: list[Report],
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None = None,
) -> list[list[str]]:
    grouped_reports = _group_reports_for_summary(reports)

    summaries = _sort_summaries(build_daily_summaries(reports, generated_at=polled_at))
    blocks: list[list[str]] = []
    for summary in summaries:
        group = grouped_reports.get(_summary_group_lookup_key(summary), [])
        summary_quote = None
        if summary.stock_code and quotes_by_stock_code:
            summary_quote = quotes_by_stock_code.get(summary.stock_code)
        if len(group) == 1:
            report = group[0]
            report_quote = None
            if report.stock_code and quotes_by_stock_code:
                report_quote = quotes_by_stock_code.get(report.stock_code)
            blocks.append(
                [
                    _format_stock_header(report.stock_name, report.stock_code, report_quote),
                    report.broker_name,
                    report.title,
                    f"목표가 {_format_target_values(report.target_price_value, report.target_price_value)} | "
                    f"{_format_opinion(report.opinion_normalized)}",
                ]
            )
        else:
            blocks.append(
                [
                    _format_stock_header(summary.stock_name, summary.stock_code, summary_quote),
                    f"{summary.mention_count}건 | {_format_broker_display(summary)}",
                    f"목표가 {_format_target_range(summary)} | {_format_opinion(summary.dominant_opinion)}",
                ]
            )
    return blocks


def format_daily_summary_message(
    business_date: date,
    summaries: list[DailyStockSummary],
    *,
    offset: int = 0,
    limit: int | None = None,
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None = None,
) -> str:
    lines = [f"전일자 리포트 (총 {_format_total_count(summaries)}건 | {_format_short_date(business_date)}({_weekday_label(business_date)}))"]
    if not summaries:
        lines.append("- 신규 리포트 없음")
        return "\n".join(lines)

    ordered = _sort_summaries(summaries)
    visible = ordered[offset:] if limit is None else ordered[offset : offset + limit]
    if not visible:
        lines.append("- 표시할 종목이 없습니다")
        return "\n".join(lines)

    lines.append("")
    for index, summary in enumerate(visible):
        summary_quote = None
        if summary.stock_code and quotes_by_stock_code:
            summary_quote = quotes_by_stock_code.get(summary.stock_code)
        lines.append(_format_stock_header(summary.stock_name, summary.stock_code, summary_quote))
        lines.append(f"{summary.mention_count}건 | {_format_broker_display(summary)}")
        lines.append(f"목표가 {_format_target_range(summary)} | {_format_opinion(summary.dominant_opinion)}")
        if index < len(visible) - 1:
            lines.append("")

    remaining = len(ordered) - (offset + len(visible))
    if remaining > 0:
        lines.append("")
        lines.append(f"나머지 {remaining}개 종목 있음")
        lines.append("다음, 전부, 처음")

    return "\n".join(lines)


def format_daily_summary_messages(
    business_date: date,
    summaries: list[DailyStockSummary],
    *,
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None = None,
    max_chars: int = 3000,
) -> list[str]:
    header = f"전일자 리포트 (총 {_format_total_count(summaries)}건 | {_format_short_date(business_date)}({_weekday_label(business_date)}))"
    if not summaries:
        return ["\n".join([header, "- 신규 리포트 없음"])]

    blocks: list[str] = []
    for summary in _sort_summaries(summaries):
        summary_quote = None
        if summary.stock_code and quotes_by_stock_code:
            summary_quote = quotes_by_stock_code.get(summary.stock_code)
        blocks.append(
            "\n".join(
                [
                    _format_stock_header(summary.stock_name, summary.stock_code, summary_quote),
                    f"{summary.mention_count}건 | {_format_broker_display(summary)}",
                    f"목표가 {_format_target_range(summary)} | {_format_opinion(summary.dominant_opinion)}",
                ]
            )
        )

    pages: list[list[str]] = []
    current_blocks: list[str] = []
    current_length = len(header) + 2
    for block in blocks:
        separator_length = 2 if current_blocks else 0
        next_length = current_length + separator_length + len(block)
        if current_blocks and next_length > max_chars:
            pages.append(current_blocks)
            current_blocks = [block]
            current_length = len(header) + 2 + len(block)
        else:
            current_blocks.append(block)
            current_length = next_length

    if current_blocks:
        pages.append(current_blocks)

    if len(pages) == 1:
        return ["\n\n".join([header, *pages[0]])]

    return [
        "\n\n".join([f"{header} ({index}/{len(pages)})", *page_blocks])
        for index, page_blocks in enumerate(pages, start=1)
    ]


def format_daily_briefing_messages(
    business_date: date,
    summaries: list[DailyStockSummary],
    *,
    briefing_date: date,
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None = None,
    market_reference_lines: list[str] | None = None,
    flow_reference_lines: list[str] | None = None,
    core_point_lines: list[str] | None = None,
    max_items: int = 7,
    max_chars: int = 3000,
) -> list[str]:
    header = f"국장 시작 전 리포트 브리핑 · {_format_short_date(briefing_date)}"
    basis = "기준: 전일 리포트 / Toss 저장값은 항목별 기준일 표시"
    if not summaries:
        return ["\n".join([header, basis, "", "리포트 집중", "- 신규 리포트 없음"])]

    ordered = _sort_summaries(summaries)
    focus_lines = _format_briefing_sector_focus(ordered, quotes_by_stock_code)
    blocks: list[str] = []
    for summary in ordered[:max_items]:
        summary_quote = None
        if summary.stock_code and quotes_by_stock_code:
            summary_quote = quotes_by_stock_code.get(summary.stock_code)
        blocks.append(
            "\n".join(
                [
                    _format_stock_header(summary.stock_name, summary.stock_code, summary_quote),
                    f"{summary.mention_count}건 | {_format_broker_display(summary)}",
                    f"목표가 {_format_target_range(summary)} | {_format_opinion(summary.dominant_opinion)}",
                ]
            )
        )

    remaining = len(ordered) - len(blocks)
    footer_lines = _format_briefing_check_points()
    if remaining > 0:
        footer_lines = [f"- 추가 {remaining}개 종목은 웹뷰/다음 페이지에서 확인", *footer_lines]

    full_message = "\n\n".join(
        [section for section in [
            "\n".join([header, basis]),
            "\n".join(["리포트 집중", *focus_lines]),
            "\n".join(market_reference_lines) if market_reference_lines else "",
            "\n".join(flow_reference_lines) if flow_reference_lines else "",
            "\n".join(core_point_lines) if core_point_lines else "",
            "\n\n".join(["주요 종목", *blocks]),
            "\n".join(["확인 포인트", *footer_lines]),
        ] if section]
    )
    if len(full_message) <= max_chars:
        return [full_message]
    return format_daily_summary_messages(
        business_date,
        summaries,
        quotes_by_stock_code=quotes_by_stock_code,
        max_chars=max_chars,
    )


def format_market_close_briefing_message(
    business_date: date,
    *,
    report_count: int,
    stock_count: int,
    market_reference_lines: list[str] | None = None,
    turnover_reference_lines: list[str] | None = None,
    flow_reference_lines: list[str] | None = None,
    notable_lines: list[str] | None = None,
    check_point_lines: list[str] | None = None,
) -> str:
    header = f"오늘의 시장 분위기 · {_format_short_date(business_date)}"
    basis = "기준: 당일 리포트 / Toss 저장값은 항목별 기준일 표시"
    report_lines = [
        "리포트 흐름",
        f"- 리포트 {report_count}건 / {stock_count}종목",
    ]
    if notable_lines:
        report_lines.extend(notable_lines)
    else:
        report_lines.append("- 눈에 띄는 다건 언급 종목 없음")

    point_lines = check_point_lines or [
        "확인 포인트",
        "- 지수, 수급 참고, 리포트 집중 종목을 함께 확인",
        "- 세부 근거는 사용자 웹뷰에서 확인",
    ]

    return "\n\n".join(
        section
        for section in [
            "\n".join([header, basis]),
            "\n".join(market_reference_lines) if market_reference_lines else "",
            "\n".join(turnover_reference_lines) if turnover_reference_lines else "",
            "\n".join(flow_reference_lines) if flow_reference_lines else "",
            "\n".join(report_lines),
            "\n".join(point_lines),
        ]
        if section
    )


def format_intraday_batch_message(
    polled_at: datetime,
    reports: list[Report],
    *,
    quotes_by_stock_code: dict[str, StockQuoteSnapshot] | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> str:
    lines = [f"장중 신규 리포트 ({len(reports)}건 | {_format_short_datetime(polled_at)})"]
    if not reports:
        lines.append("- 신규 리포트 없음")
        return "\n".join(lines)

    blocks = _build_intraday_stock_blocks(polled_at, reports, quotes_by_stock_code)
    visible_blocks = blocks[offset:] if limit is None else blocks[offset : offset + limit]
    if not visible_blocks:
        lines.append("- 표시할 종목이 없습니다")
        return "\n".join(lines)

    lines.append("")
    for index, block in enumerate(visible_blocks):
        lines.extend(block)
        if index < len(visible_blocks) - 1:
            lines.append("")

    remaining = len(blocks) - (offset + len(visible_blocks))
    if remaining > 0:
        lines.append("")
        lines.append(f"나머지 {remaining}개 종목 있음")
        lines.append("다음, 전부, 처음")

    return "\n".join(lines)


def format_intraday_empty_message(polled_at: datetime) -> str:
    return f"장중 신규 리포트가 없습니다 (0건 | {_format_short_datetime(polled_at)})"


def format_stock_research_lookup_message(
    stock_code: str,
    stock_name: str | None,
    entries: list[StockResearchEntry],
    *,
    lookback_days: int,
    quote: StockQuoteSnapshot | None = None,
    entry_limit: int = 5,
) -> str:
    display_name = _format_stock_name(stock_name or "종목", stock_code)
    header = f"종목 리포트 조회 ({display_name} | 최근 {lookback_days}일)"
    quote_fragment = _format_quote_fragment(quote)

    if not entries:
        first_line = display_name if quote_fragment is None else f"{display_name} | {quote_fragment}"
        return "\n".join([header, "", first_line, "0건 | 리포트 없음", "목표가 - | 의견 없음"])

    target_values = sorted(entry.target_price_value for entry in entries if entry.target_price_value is not None)
    opinion_counts = Counter(entry.opinion_normalized for entry in entries if entry.opinion_normalized != "N/A")
    dominant_opinion = (
        max(
            opinion_counts.items(),
            key=lambda item: (item[1], OPINION_PRIORITY.get(item[0], -1)),
        )[0]
        if opinion_counts
        else "N/A"
    )

    unique_brokers: list[str] = []
    for entry in entries:
        if entry.broker_name not in unique_brokers:
            unique_brokers.append(entry.broker_name)

    first_line = display_name if quote_fragment is None else f"{display_name} | {quote_fragment}"
    lines = [
        header,
        "",
        first_line,
        f"{len(entries)}건 | {_truncate_broker_names(unique_brokers)}",
        f"목표가 {_format_target_values(target_values[0] if target_values else None, target_values[-1] if target_values else None)} | {_format_opinion(dominant_opinion)}",
    ]

    visible_entries = entries[:entry_limit]
    if visible_entries:
        lines.extend(["", "최근 리포트"])
        for entry in visible_entries:
            lines.append(
                f"- {_format_short_date(entry.write_date)} | {entry.broker_name} | "
                f"목표가 {_format_target_values(entry.target_price_value, entry.target_price_value)} | "
                f"{_format_opinion(entry.opinion_normalized)} | {entry.title}"
            )

    remaining = len(entries) - len(visible_entries)
    if remaining > 0:
        lines.extend(["", f"추가 {remaining}건은 생략"])

    return "\n".join(lines)


def format_stock_code_lookup_message(query: str, candidates: list[StockCodeLookupEntry]) -> str:
    header = f"종목코드 조회 ({query})"
    if not candidates:
        return "\n".join([header, "", "- 검색 결과 없음"])

    lines = [header, "", f"후보 {len(candidates)}건"]
    for candidate in candidates:
        market_suffix = f" | {candidate.market_type}" if candidate.market_type else ""
        lines.append(f"- {candidate.stock_name}({candidate.stock_code}){market_suffix}")
    return "\n".join(lines)


def format_stock_selection_message(query: str, candidates: list[StockCodeLookupEntry]) -> str:
    header = f"종목 선택 ({query})"
    if not candidates:
        return "\n".join(
            [
                header,
                "",
                "- 검색 결과 없음",
                "/종목검색 삼성전자 또는 /종목검색 005930",
            ]
        )

    lines = [header, "", f"후보 {len(candidates)}건"]
    for index, candidate in enumerate(candidates, start=1):
        market_suffix = f" | {candidate.market_type}" if candidate.market_type else ""
        lines.append(f"{index}. {candidate.stock_name}({candidate.stock_code}){market_suffix}")
    lines.extend(
        [
            "",
            "몇 번으로 선택할까요?",
            "숫자만 입력하거나 /종목검색 종목코드를 다시 입력해보세요.",
        ]
    )
    return "\n".join(lines)
