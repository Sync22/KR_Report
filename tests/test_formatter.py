from datetime import date, datetime

from stock_monitor.fetch.naver_stock_quote import StockQuoteSnapshot
from stock_monitor.fetch.naver_stock_search import StockCodeLookupEntry
from stock_monitor.models import DailyStockSummary, Opinion, Report, StockResearchEntry
from stock_monitor.notify.formatter import (
    format_daily_briefing_messages,
    format_daily_summary_message,
    format_daily_summary_messages,
    format_market_close_briefing_message,
    format_intraday_empty_message,
    format_intraday_batch_message,
    format_stock_code_lookup_message,
    format_stock_research_lookup_message,
    format_stock_selection_message,
)


def test_format_daily_summary_message_uses_short_date_labels_and_sorted_output() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="현대차",
            stock_code="005380",
            mention_count=1,
            broker_display="교보증권(1)",
            target_price_min=800_000,
            target_price_max=800_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        ),
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="JB금융지주",
            stock_code="175330",
            mention_count=2,
            broker_display="교보증권(2)",
            target_price_min=38_000,
            target_price_max=39_000,
            dominant_opinion="neutral",
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        ),
    ]

    quotes_by_stock_code = {
        "175330": StockQuoteSnapshot(
            stock_code="175330",
            stock_name="JB금융지주",
            sector_code="40",
            sector_name="은행",
            current_price=15_500,
            market_status="CLOSE",
            trade_time=datetime(2026, 4, 24, 15, 30, 0),
            prev_close_price=15_000,
        ),
        "005380": StockQuoteSnapshot(
            stock_code="005380",
            stock_name="현대차",
            sector_code="33",
            sector_name="자동차",
            current_price=412_000,
            market_status="CLOSE",
            trade_time=datetime(2026, 4, 24, 15, 30, 0),
            prev_close_price=405_000,
        ),
    }

    message = format_daily_summary_message(
        date(2026, 4, 24),
        summaries,
        quotes_by_stock_code=quotes_by_stock_code,
    )
    lines = message.splitlines()

    assert lines[0] == "전일자 리포트 (총 03건 | 26.04.24(금))"
    assert lines[2] == "JB금융지주(175330) | 현재가 15,500원 | 은행"
    assert lines[3] == "2건 | 교보증권(2)"
    assert lines[4] == "목표가 38,000원 ~ 39,000원 | 중립"
    assert lines[6] == "현대차(005380) | 현재가 412,000원 | 자동차"
    assert lines[7] == "1건 | 교보증권(1)"
    assert lines[8] == "목표가 800,000원 | 매수"


def test_format_daily_summary_message_truncates_long_broker_list() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="SK하이닉스",
            stock_code="000660",
            mention_count=6,
            broker_display="DS투자증권(1), 교보증권(1), 대신증권(1), 유안타증권(1), 하나증권(1), 한화투자증권(1)",
            target_price_min=1_600_000,
            target_price_max=1_900_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        )
    ]

    quotes_by_stock_code = {
        "000660": StockQuoteSnapshot(
            stock_code="000660",
            stock_name="SK하이닉스",
            sector_code="27",
            sector_name="반도체와반도체장비",
            current_price=1_720_000,
            market_status="CLOSE",
            trade_time=datetime(2026, 4, 24, 15, 30, 0),
            prev_close_price=1_700_000,
        )
    }

    message = format_daily_summary_message(
        date(2026, 4, 24),
        summaries,
        quotes_by_stock_code=quotes_by_stock_code,
    )
    lines = message.splitlines()

    assert lines[2] == "SK하이닉스(000660) | 현재가 1,720,000원 | 반도체와반도체장비"
    assert lines[3] == "6건 | DS투자증권(1), 교보증권(1), 대신증권(1) 외 3곳"
    assert lines[4] == "목표가 1,600,000원 ~ 1,900,000원 | 매수"


def test_format_daily_summary_message_displays_missing_values_without_na_label() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="무목표",
            stock_code="123456",
            mention_count=1,
            broker_display="테스트증권(1)",
            target_price_min=None,
            target_price_max=None,
            dominant_opinion=Opinion.NA.value,
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        )
    ]

    message = format_daily_summary_message(date(2026, 4, 24), summaries)

    assert "목표가 - | 의견 없음" in message
    assert "N/A" not in message


def test_format_daily_summary_message_supports_offset_and_limit_footer() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name=f"종목{i}",
            stock_code=f"{i:06d}",
            mention_count=1,
            broker_display="교보증권(1)",
            target_price_min=10_000 + i,
            target_price_max=10_000 + i,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        )
        for i in range(12)
    ]

    message = format_daily_summary_message(date(2026, 4, 24), summaries, offset=0, limit=10)

    assert "나머지 2개 종목 있음" in message
    assert "다음, 전부, 처음" in message


def test_format_daily_summary_messages_splits_large_daily_summary_on_stock_boundaries() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name=f"긴종목명{i}",
            stock_code=f"{i:06d}",
            mention_count=3,
            broker_display="교보증권(1), 대신증권(1), 하나증권(1)",
            target_price_min=10_000 + i,
            target_price_max=12_000 + i,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 25, 7, 0, 0),
        )
        for i in range(8)
    ]

    messages = format_daily_summary_messages(date(2026, 4, 24), summaries, max_chars=260)

    assert len(messages) > 1
    assert all(len(message) <= 260 for message in messages)
    assert "(1/" in messages[0].splitlines()[0]
    assert "긴종목명0" in messages[0]
    assert "긴종목명7" in messages[-1]


def test_format_daily_briefing_messages_builds_morning_briefing_without_recommendation_copy() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 5, 13),
            stock_name="삼성전자",
            stock_code="005930",
            mention_count=4,
            broker_display="NH투자증권(2), KB증권(1), 하나증권(1)",
            target_price_min=280_000,
            target_price_max=320_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 13, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=date(2026, 5, 13),
            stock_name="현대차",
            stock_code="005380",
            mention_count=2,
            broker_display="DS투자증권(1), 교보증권(1)",
            target_price_min=650_000,
            target_price_max=700_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 13, 16, 0, 0),
        ),
    ]
    quotes_by_stock_code = {
        "005930": StockQuoteSnapshot(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="24",
            sector_name="반도체와반도체장비",
            current_price=279_000,
            market_status="CLOSE",
            trade_time=datetime(2026, 5, 13, 15, 30, 0),
            prev_close_price=285_000,
        ),
        "005380": StockQuoteSnapshot(
            stock_code="005380",
            stock_name="현대차",
            sector_code="25",
            sector_name="자동차",
            current_price=646_000,
            market_status="CLOSE",
            trade_time=datetime(2026, 5, 13, 15, 30, 0),
            prev_close_price=640_000,
        ),
    }

    messages = format_daily_briefing_messages(
        date(2026, 5, 13),
        summaries,
        briefing_date=date(2026, 5, 14),
        quotes_by_stock_code=quotes_by_stock_code,
        market_reference_lines=[
            "지수 참고 · 26.05.13 KRX 저장값",
            "- KOSPI 7,844.01 +2.63% / KOSDAQ 1,176.93 -0.20%",
        ],
        flow_reference_lines=[
            "수급 참고 · 26.05.12 KOSPI 저장값 / 리포트일 전 최신",
            "- 개인 매수 우위 6.7조 / 외국인 매도 우위 5.6조 / 기관 매도 우위 1.2조",
        ],
        core_point_lines=[
            "핵심 포인트",
            "- KOSPI 상승, KOSDAQ 하락으로 시장 방향이 엇갈림",
            "- 리포트 집중 1위: 반도체와반도체장비 4건",
        ],
        max_items=2,
    )
    message = messages[0]

    assert "국장 시작 전 리포트 브리핑 · 26.05.14" in message
    assert "기준: 전일 리포트 / KRX 저장값은 항목별 기준일 표시" in message
    assert "리포트 집중" in message
    assert "- 반도체와반도체장비 4건" in message
    assert "지수 참고 · 26.05.13 KRX 저장값" in message
    assert "KOSPI 7,844.01 +2.63%" in message
    assert "수급 참고 · 26.05.12 KOSPI 저장값 / 리포트일 전 최신" in message
    assert "개인 매수 우위 6.7조" in message
    assert "핵심 포인트" in message
    assert "리포트 집중 1위: 반도체와반도체장비 4건" in message
    assert "주요 종목" in message
    assert "삼성전자(005930) | 현재가 279,000원 | 반도체와반도체장비" in message
    assert "확인 포인트" in message
    assert "추천" not in message
    assert "매수 기회" not in message
    assert "전략 제안" not in message


def test_format_market_close_briefing_message_keeps_observation_wording() -> None:
    message = format_market_close_briefing_message(
        date(2026, 5, 14),
        report_count=12,
        stock_count=5,
        market_reference_lines=[
            "지수 참고 · 26.05.14 KRX 저장값",
            "- KOSPI 7,844.01 +2.63% / KOSDAQ 1,176.93 -0.20%",
        ],
        turnover_reference_lines=[
            "거래대금 참고 · 26.05.14 KRX 저장값",
            "- KOSPI: 삼성전자 2.3조 / SK하이닉스 1.9조",
        ],
        flow_reference_lines=[
            "수급 참고 · 26.05.14 KOSPI 저장값",
            "- 개인 매수 우위 / 외국인 매도 우위 / 기관 매수 우위",
        ],
        notable_lines=[
            "눈에 띄는 종목",
            "- 삼성전자(005930) 3건 / 목표가 280,000원~320,000원",
        ],
    )

    assert "오늘의 시장 분위기 · 26.05.14" in message
    assert "기준: 당일 리포트 / KRX 저장값은 항목별 기준일 표시" in message
    assert "거래대금 참고 · 26.05.14 KRX 저장값" in message
    assert "리포트 12건 / 5종목" in message
    assert "눈에 띄는 종목" in message
    assert "확인 포인트" in message
    assert "추천" not in message
    assert "점수" not in message
    assert "등급" not in message
    assert "매수 기회" not in message
    assert "전략 제안" not in message


def test_format_intraday_batch_message_keeps_single_report_detail() -> None:
    reports = [
        Report(
            stock_name="삼성전자",
            stock_code="005930",
            title="상황 회복 가시화",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw="92000",
            target_price_value=92_000,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url="https://stock.naver.com/research/company/91999",
            source_id="91999",
            identity_key="identity-1",
        )
    ]

    quotes_by_stock_code = {
        "005930": StockQuoteSnapshot(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="27",
            sector_name="반도체와반도체장비",
            current_price=91_500,
            market_status="OPEN",
            trade_time=datetime(2026, 4, 24, 9, 30, 0),
            prev_close_price=90_000,
        )
    }

    message = format_intraday_batch_message(
        datetime(2026, 4, 24, 9, 30, 0),
        reports,
        quotes_by_stock_code=quotes_by_stock_code,
    )
    lines = message.splitlines()

    assert lines[0] == "장중 신규 리포트 (1건 | 26.04.24 09:30)"
    assert lines[2] == "삼성전자(005930) | 현재가 91,500원 | 반도체와반도체장비"
    assert lines[3] == "NH투자증권"
    assert lines[4] == "상황 회복 가시화"
    assert lines[5] == "목표가 92,000원 | 매수"


def test_format_intraday_batch_message_groups_reports_by_stock_when_multiple() -> None:
    reports = [
        Report(
            stock_name="삼성전자",
            stock_code="005930",
            title="상황 회복 가시화",
            broker_name="NH투자증권",
            published_at=datetime(2026, 4, 24, 9, 0, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw="92000",
            target_price_value=92_000,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url="https://stock.naver.com/research/company/91999",
            source_id="91999",
            identity_key="identity-1",
        ),
        Report(
            stock_name="삼성전자",
            stock_code="005930",
            title="메모리 업황 반등",
            broker_name="메리츠증권",
            published_at=datetime(2026, 4, 24, 9, 5, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw="100000",
            target_price_value=100_000,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url="https://stock.naver.com/research/company/92000",
            source_id="92000",
            identity_key="identity-2",
        ),
    ]

    quotes_by_stock_code = {
        "005930": StockQuoteSnapshot(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="27",
            sector_name="반도체와반도체장비",
            current_price=96_000,
            market_status="OPEN",
            trade_time=datetime(2026, 4, 24, 9, 30, 0),
            prev_close_price=90_000,
        )
    }

    message = format_intraday_batch_message(
        datetime(2026, 4, 24, 9, 30, 0),
        reports,
        quotes_by_stock_code=quotes_by_stock_code,
    )
    lines = message.splitlines()

    assert lines[0] == "장중 신규 리포트 (2건 | 26.04.24 09:30)"
    assert lines[2] == "삼성전자(005930) | 현재가 96,000원 | 반도체와반도체장비"
    assert lines[3] == "2건 | NH투자증권(1), 메리츠증권(1)"
    assert lines[4] == "목표가 92,000원 ~ 100,000원 | 매수"


def test_format_intraday_batch_message_groups_same_code_name_drift() -> None:
    reports = [
        Report(
            stock_name="SK텔레콤",
            stock_code="017670",
            title="wireless re-rating",
            broker_name="NH",
            published_at=datetime(2026, 4, 24, 9, 0, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw="120000",
            target_price_value=120_000,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url="https://example.com/1",
            source_id="1",
            identity_key="identity-1",
        ),
        Report(
            stock_name="SK Telecom",
            stock_code="017670",
            title="cash flow visible",
            broker_name="Meritz",
            published_at=datetime(2026, 4, 24, 9, 10, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw="140000",
            target_price_value=140_000,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url="https://example.com/2",
            source_id="2",
            identity_key="identity-2",
        ),
    ]

    message = format_intraday_batch_message(datetime(2026, 4, 24, 9, 30, 0), reports)

    assert "2건 |" in message
    assert "목표가 120,000원 ~ 140,000원 | 매수" in message
    assert "cash flow visible" not in message


def test_format_intraday_batch_message_supports_stock_paging_footer() -> None:
    reports = [
        Report(
            stock_name=f"종목{i}",
            stock_code=f"{i:06d}",
            title=f"리포트{i}",
            broker_name="교보증권",
            published_at=datetime(2026, 4, 24, 9, 0, 0),
            collected_at=datetime(2026, 4, 24, 9, 30, 0),
            business_date=date(2026, 4, 24),
            target_price_raw=str(10000 + i),
            target_price_value=10_000 + i,
            opinion_raw="Buy",
            opinion_normalized="buy",
            source_url=f"https://stock.naver.com/research/company/{90000 + i}",
            source_id=str(90000 + i),
            identity_key=f"identity-{i}",
        )
        for i in range(9)
    ]

    message = format_intraday_batch_message(
        datetime(2026, 4, 24, 9, 30, 0),
        reports,
        offset=0,
        limit=7,
    )

    assert "나머지 2개 종목 있음" in message
    assert "다음, 전부, 처음" in message


def test_format_stock_research_lookup_message_shows_current_price_on_first_line() -> None:
    entries = [
        StockResearchEntry(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="유안타증권",
            title="반영한다고 했제",
            write_date=date(2026, 4, 20),
            target_price_value=118_000,
            opinion_normalized="buy",
            source_url="https://stock.naver.com/domestic/stock/017670/research/91703",
            source_id="91703",
        ),
        StockResearchEntry(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="하나증권",
            title="이제 5G SA 시대에 적응하셔야 합니다",
            write_date=date(2026, 4, 17),
            target_price_value=140_000,
            opinion_normalized="buy",
            source_url="https://stock.naver.com/domestic/stock/017670/research/91676",
            source_id="91676",
        ),
    ]
    quote = StockQuoteSnapshot(
        stock_code="017670",
        stock_name="SK텔레콤",
        sector_code="45",
        sector_name="무선통신서비스",
        current_price=219_500,
        market_status="CLOSE",
        trade_time=datetime(2026, 4, 24, 16, 10, 20),
        prev_close_price=224_500,
    )

    message = format_stock_research_lookup_message(
        "017670",
        "SK텔레콤",
        entries,
        lookback_days=15,
        quote=quote,
    )

    assert "종목 리포트 조회 (SK텔레콤(017670) | 최근 15일)" in message
    assert "SK텔레콤(017670) | 현재가 219,500원 | 무선통신서비스" in message
    assert "2건 | 유안타증권, 하나증권" in message
    assert "목표가 118,000원 ~ 140,000원 | 매수" in message
    assert "- 26.04.20 | 유안타증권 | 목표가 118,000원 | 매수 | 반영한다고 했제" in message


def test_format_stock_research_lookup_message_omits_current_price_when_missing() -> None:
    entries = [
        StockResearchEntry(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="유안타증권",
            title="반영한다고 했제",
            write_date=date(2026, 4, 20),
            target_price_value=118_000,
            opinion_normalized="buy",
            source_url="https://stock.naver.com/domestic/stock/017670/research/91703",
            source_id="91703",
        )
    ]

    message = format_stock_research_lookup_message(
        "017670",
        "SK텔레콤",
        entries,
        lookback_days=15,
        quote=None,
    )

    assert "SK텔레콤(017670) | 현재가" not in message
    assert "SK텔레콤(017670)" in message
    assert "1건 | 유안타증권" in message


def test_format_stock_research_lookup_message_ignores_na_opinion_for_dominant_opinion() -> None:
    entries = [
        StockResearchEntry(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="유안타증권",
            title="목표가 없음",
            write_date=date(2026, 4, 20),
            target_price_value=None,
            opinion_normalized=Opinion.NA.value,
        ),
        StockResearchEntry(
            stock_name="SK텔레콤",
            stock_code="017670",
            broker_name="하나증권",
            title="매수 유지",
            write_date=date(2026, 4, 17),
            target_price_value=140_000,
            opinion_normalized=Opinion.BUY.value,
        ),
    ]

    message = format_stock_research_lookup_message("017670", "SK텔레콤", entries, lookback_days=15)

    assert "목표가 140,000원 | 매수" in message
    assert "- 26.04.20 | 유안타증권 | 목표가 - | 의견 없음 | 목표가 없음" in message


def test_format_stock_code_lookup_message_lists_candidates() -> None:
    candidates = [
        StockCodeLookupEntry(
            stock_code="017670",
            stock_name="SK텔레콤",
            market_type="코스피",
            source_url="https://stock.naver.com/domestic/stock/017670/total",
        ),
        StockCodeLookupEntry(
            stock_code="001510",
            stock_name="SK증권",
            market_type="코스피",
            source_url="https://stock.naver.com/domestic/stock/001510/total",
        ),
    ]

    message = format_stock_code_lookup_message("SK", candidates)

    assert "종목코드 조회 (SK)" in message
    assert "후보 2건" in message
    assert "- SK텔레콤(017670) | 코스피" in message


def test_format_stock_selection_message_asks_for_number_choice() -> None:
    candidates = [
        StockCodeLookupEntry(
            stock_code="005930",
            stock_name="삼성전자",
            market_type="코스피",
            source_url="https://stock.naver.com/domestic/stock/005930/total",
        ),
        StockCodeLookupEntry(
            stock_code="016360",
            stock_name="삼성증권",
            market_type="코스피",
            source_url="https://stock.naver.com/domestic/stock/016360/total",
        ),
    ]

    message = format_stock_selection_message("삼성", candidates)

    assert "종목 선택 (삼성)" in message
    assert "1. 삼성전자(005930) | 코스피" in message
    assert "2. 삼성증권(016360) | 코스피" in message
    assert "몇 번으로 선택할까요?" in message
