from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from stock_monitor.news import NewsArticle, build_news_intelligence_report
from stock_monitor.news.collectors import KST
from stock_monitor.news.collectors import (
    ManualNewsCollector,
    NaverStockNewsCollector,
    NewsSource,
    ScraplingNewsTransport,
    StockNewsQuery,
    build_naver_news_request_specs,
    collect_naver_news_preview,
    match_articles_to_stock,
    match_articles_to_stock_with_reasons,
    parse_naver_focus_news_json,
    parse_naver_news_markdown,
)


NAVER_MAINNEWS_MARKDOWN = """
주요뉴스
====

검색결과

* 최신순
* 날짜별

* 2026. 06. 01
  ------------

  증시 마감 후 (15:30~00:00)
  :   2026. 06. 01. 22:40

      [### 삼성전자, AI 반도체 공급 계약 체결

      삼성전자가 글로벌 고객사와 AI 반도체 공급 계약을 체결했다고 밝혔다.

      한국경제

      ![](https://imgnews.pstatic.net/image/origin/015/2026/06/01/1.jpg)](https://n.news.naver.com/article/015/0000001 "새 창에서 열기")
  :   2026. 06. 01. 22:18

      [### 코스피 최고치 경신, 외국인 매수세 지속

      외국인 순매수와 대형주 강세가 이어졌다는 분석이다.

      서울경제

      ![](https://imgnews.pstatic.net/image/origin/011/2026/06/01/2.jpg)](https://n.news.naver.com/article/011/0000002 "새 창에서 열기")
"""


NAVER_RANKNEWS_MARKDOWN = """
많이 본 뉴스
-------

* 2026. 06. 01. 17:57

  [### '신고가' 삼전닉스 "지금도 할인중"…61만전자·400만닉스 파격 전망

  삼성전자와 SK하이닉스 실적을 상향 조정해야 한다는 분석이 나왔다.

  머니투데이

  ![](https://imgnews.pstatic.net/image/origin/008/2026/06/01/1.jpg)](https://n.news.naver.com/article/008/0000001 "새 창에서 열기")
"""


NAVER_SECTION_MARKDOWN = """
시황·전망기업·종목분석해외증시채권·선물공시·메모환율

* 최신순
* 날짜별
* 2026. 06. 01. 20:29

  [컬리, AI 기업 ‘원지랩스’ 인수한다…AI 전환 속도 [시그널]
  ------------------------------------

  컬리가 인공지능 기술 연구 기업 원지랩스를 인수한다.

  서울경제

  ![](https://imgnews.naver.net/image/origin/011/2026/06/01/1.jpg)](https://n.news.naver.com/mnews/article/011/0000001?sid=101258401 "새 창에서 열기")
"""


NAVER_SECTION_MARKET_JSON = """
{
  "page": "1",
  "pageSize": "20",
  "articleTotal": "0",
  "recentdates": [],
  "date": "20260601",
  "articles": [
    {
      "officeHName": "매일경제",
      "articleID": "0005688140",
      "title": "비트코인 절대 팔지말라던 MSTR, 32개 매각",
      "subcontent": "세계 최대 비트코인 보유사 스트래티지가 비트코인을 매도했다.",
      "date": "20260601223708",
      "url": "https://n.news.naver.com/mnews/article/009/0005688140?sid=101258401"
    }
  ]
}
"""


NAVER_SECTION_COMPANY_JSON = """
{
  "page": "1",
  "pageSize": "20",
  "articleTotal": "0",
  "recentdates": [],
  "date": "20260601",
  "articles": [
    {
      "officeHName": "한국경제",
      "articleID": "0005293882",
      "title": "\\"주가 61만원 간다\\"…삼성전자 또 역대급 전망에 '들썩' [종목+]",
      "subcontent": "삼성전자가 6월의 첫 거래일 10%대 급등했다.",
      "date": "20260601220111",
      "url": "https://n.news.naver.com/mnews/article/015/0005293882?sid=101258402"
    }
  ]
}
"""


def test_build_naver_news_request_specs_defaults_to_date_mode() -> None:
    specs = build_naver_news_request_specs(date(2026, 6, 1))

    assert [spec.source for spec in specs] == [
        NewsSource.FLASHNEWS,
        NewsSource.MAINNEWS,
        NewsSource.RANKNEWS,
        NewsSource.SECTION_MARKET_OUTLOOK,
        NewsSource.SECTION_COMPANY_ANALYSIS,
    ]
    assert all(spec.collection_mode == "date" for spec in specs)
    assert all(spec.target_date == date(2026, 6, 1) for spec in specs)
    assert specs[0].page_url == "https://stock.naver.com/news/flashnews"
    assert specs[3].page_url == (
        "https://stock.naver.com/api/domestic/news/focus"
        "?sid=401&page=1&pageSize=20&date=20260601"
    )
    assert specs[4].page_url == (
        "https://stock.naver.com/api/domestic/news/focus"
        "?sid=402&page=1&pageSize=20&date=20260601"
    )
    assert specs[3].section_name == "시황·전망"
    assert specs[4].section_name == "기업·종목분석"
    assert specs[3].response_format == "focus_json"
    assert specs[4].response_format == "focus_json"


def test_parse_naver_news_markdown_fixture_extracts_articles() -> None:
    articles = parse_naver_news_markdown(
        NAVER_MAINNEWS_MARKDOWN,
        source=NewsSource.MAINNEWS,
        target_date=date(2026, 6, 1),
    )

    assert len(articles) == 2
    assert articles[0].title == "삼성전자, AI 반도체 공급 계약 체결"
    assert articles[0].source == "한국경제"
    assert articles[0].published_at.isoformat() == "2026-06-01T22:40:00+09:00"
    assert articles[0].url == "https://n.news.naver.com/article/015/0000001"
    assert articles[0].source_lane == "mainnews"


def test_parse_naver_news_markdown_handles_ranknews_bullet_dates() -> None:
    articles = parse_naver_news_markdown(
        NAVER_RANKNEWS_MARKDOWN,
        source=NewsSource.RANKNEWS,
        target_date=date(2026, 6, 1),
    )

    assert len(articles) == 1
    assert articles[0].title.startswith("'신고가' 삼전닉스")
    assert articles[0].source == "머니투데이"
    assert articles[0].source_lane == "ranknews"


def test_parse_naver_news_markdown_handles_section_underline_titles() -> None:
    articles = parse_naver_news_markdown(
        NAVER_SECTION_MARKDOWN,
        source=NewsSource.SECTION_COMPANY_ANALYSIS,
        target_date=date(2026, 6, 1),
    )

    assert len(articles) == 1
    assert articles[0].title == "컬리, AI 기업 ‘원지랩스’ 인수한다…AI 전환 속도 [시그널]"
    assert articles[0].source == "서울경제"
    assert articles[0].source_lane == "section_company_analysis"
    assert articles[0].url.startswith("https://n.news.naver.com/mnews/article/011/")


def test_parse_naver_focus_news_json_handles_market_outlook_api() -> None:
    articles = parse_naver_focus_news_json(
        NAVER_SECTION_MARKET_JSON,
        source=NewsSource.SECTION_MARKET_OUTLOOK,
        target_date=date(2026, 6, 1),
    )

    assert len(articles) == 1
    assert articles[0].title == "비트코인 절대 팔지말라던 MSTR, 32개 매각"
    assert articles[0].summary == "세계 최대 비트코인 보유사 스트래티지가 비트코인을 매도했다."
    assert articles[0].source == "매일경제"
    assert articles[0].published_at.isoformat() == "2026-06-01T22:37:08+09:00"
    assert articles[0].source_lane == "section_market_outlook"
    assert articles[0].url.endswith("sid=101258401")


def test_parse_naver_focus_news_json_handles_company_analysis_api() -> None:
    articles = parse_naver_focus_news_json(
        NAVER_SECTION_COMPANY_JSON,
        source=NewsSource.SECTION_COMPANY_ANALYSIS,
        target_date=date(2026, 6, 1),
    )

    assert len(articles) == 1
    assert articles[0].title.startswith('"주가 61만원 간다"')
    assert articles[0].summary == "삼성전자가 6월의 첫 거래일 10%대 급등했다."
    assert articles[0].source == "한국경제"
    assert articles[0].published_at.isoformat() == "2026-06-01T22:01:11+09:00"
    assert articles[0].source_lane == "section_company_analysis"
    assert articles[0].url.endswith("sid=101258402")


def test_manual_collector_matches_stock_aliases_and_report_generation() -> None:
    articles = parse_naver_news_markdown(
        NAVER_MAINNEWS_MARKDOWN,
        source=NewsSource.MAINNEWS,
        target_date=date(2026, 6, 1),
    )
    query = StockNewsQuery(
        stock_name="삼성전자",
        stock_code="005930",
        aliases=("Samsung Electronics", "삼성"),
        target_date=date(2026, 6, 1),
    )

    collector = ManualNewsCollector(articles)
    matched = collector.collect(query)
    report = build_news_intelligence_report(
        stock=query.stock_name,
        stock_code=query.stock_code,
        articles=matched,
    ).to_dict()

    assert len(matched) == 1
    assert matched[0].title.startswith("삼성전자")
    assert report["article_count"] == 1
    assert report["operator_only"] is True
    assert report["connected_surfaces"] == []


def test_naver_collector_uses_injected_transport_without_live_fetch() -> None:
    calls: list[str] = []

    def transport(url: str) -> str:
        calls.append(url)
        if "sid=402" in url:
            return NAVER_SECTION_COMPANY_JSON
        if "sid=401" in url:
            return NAVER_SECTION_MARKET_JSON
        return NAVER_MAINNEWS_MARKDOWN

    query = StockNewsQuery(
        stock_name="삼성전자",
        stock_code="005930",
        aliases=("삼성",),
        target_date=date(2026, 6, 1),
    )
    collector = NaverStockNewsCollector(transport=transport)

    matched = collector.collect(query)

    assert matched
    assert all("삼성" in f"{article.title} {article.summary}" for article in matched)
    assert len(calls) == 5
    assert calls[0] == "https://stock.naver.com/news/flashnews"
    assert calls[3].endswith("sid=401&page=1&pageSize=20&date=20260601")
    assert calls[4].endswith("sid=402&page=1&pageSize=20&date=20260601")
    assert any(article.source_lane == "section_company_analysis" for article in matched)


def test_match_articles_to_stock_uses_name_code_and_aliases() -> None:
    articles = parse_naver_news_markdown(
        NAVER_MAINNEWS_MARKDOWN,
        source=NewsSource.MAINNEWS,
        target_date=date(2026, 6, 1),
    )

    matched = match_articles_to_stock(
        articles,
        StockNewsQuery(
            stock_name="Samsung Electronics",
            stock_code="005930",
            aliases=("삼성전자",),
            target_date=date(2026, 6, 1),
        ),
    )

    assert [article.title for article in matched] == ["삼성전자, AI 반도체 공급 계약 체결"]
def test_match_articles_to_stock_with_reasons_records_name_code_and_alias() -> None:
    articles = parse_naver_news_markdown(
        NAVER_MAINNEWS_MARKDOWN,
        source=NewsSource.MAINNEWS,
        target_date=date(2026, 6, 1),
    )

    name_matches = match_articles_to_stock_with_reasons(
        articles,
        StockNewsQuery(
            stock_name="삼성전자",
            stock_code="005930",
            aliases=("Samsung Electronics",),
            target_date=date(2026, 6, 1),
        ),
    )
    code_matches = match_articles_to_stock_with_reasons(
        articles,
        StockNewsQuery(
            stock_name="NoName",
            stock_code="005930",
            aliases=(),
            target_date=date(2026, 6, 1),
        ),
    )
    alias_matches = match_articles_to_stock_with_reasons(
        articles,
        StockNewsQuery(
            stock_name="NoName",
            stock_code=None,
            aliases=("AI",),
            target_date=date(2026, 6, 1),
        ),
    )

    assert name_matches[0].matched_alias == "삼성전자"
    assert name_matches[0].match_reason == "stock_name"
    assert code_matches == []
    assert alias_matches[0].matched_alias == "AI"
    assert alias_matches[0].match_reason == "alias"
    assert alias_matches[0].match_scope == "both"
    assert alias_matches[0].relevance == "direct"


def test_match_articles_to_stock_with_reasons_classifies_relevance_scope() -> None:
    articles = [
        NewsArticle(
            title="삼성전자 급등, 목표주가 상향",
            summary="삼성전자 실적 개선 기대가 커졌다.",
            source="한국경제",
            published_at=datetime(2026, 6, 1, 9, 0, tzinfo=KST),
            url="https://example.test/news/direct",
            source_lane="mainnews",
        ),
        NewsArticle(
            title="반도체 ETF에 자금 쏠림",
            summary="삼성전자와 SK하이닉스 중심 수급 쏠림으로 코스피 지수가 상승했다.",
            source="매일경제",
            published_at=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
            url="https://example.test/news/market-context",
            source_lane="ranknews",
        ),
        NewsArticle(
            title="장중 특징주 점검",
            summary="삼성전자가 상승을 이끌었다.",
            source="서울경제",
            published_at=datetime(2026, 6, 1, 11, 0, tzinfo=KST),
            url="https://example.test/news/indirect",
            source_lane="section_market_outlook",
        ),
    ]

    matched = match_articles_to_stock_with_reasons(
        articles,
        StockNewsQuery(
            stock_name="삼성전자",
            stock_code="005930",
            aliases=("삼전",),
            target_date=date(2026, 6, 1),
        ),
    )

    assert [article.match_scope for article in matched] == ["both", "summary", "summary"]
    assert [article.relevance for article in matched] == ["direct", "market_context", "indirect"]
    assert "title and summary" in matched[0].relevance_reason
    assert "market context" in matched[1].relevance_reason


def test_collect_naver_news_preview_reports_source_and_match_counts() -> None:
    def transport(spec) -> str:
        if spec.source == NewsSource.SECTION_COMPANY_ANALYSIS:
            return NAVER_SECTION_COMPANY_JSON
        if spec.source == NewsSource.SECTION_MARKET_OUTLOOK:
            return NAVER_SECTION_MARKET_JSON
        if spec.source == NewsSource.RANKNEWS:
            return NAVER_RANKNEWS_MARKDOWN
        return NAVER_MAINNEWS_MARKDOWN

    query = StockNewsQuery(
        stock_name="삼성전자",
        stock_code="005930",
        aliases=("AI",),
        target_date=date(2026, 6, 1),
    )

    preview = collect_naver_news_preview(query, transport=transport)

    assert preview.parsed_count == 7
    assert preview.deduped_count == 5
    assert preview.matched_count == 3
    assert len(preview.sources) == 5
    assert all(source.fetched for source in preview.sources)
    assert all(source.fetch_error is None for source in preview.sources)
    assert preview.sources[0].parsed_count == 2
    assert preview.sources[0].matched_count == 1
    assert {article.match_reason for article in preview.articles} == {"stock_name"}
    assert {article.source_lane for article in preview.articles} == {
        "flashnews",
        "ranknews",
        "section_company_analysis",
    }


def test_collect_naver_news_preview_keeps_partial_fetch_failures_as_warnings() -> None:
    def transport(spec) -> str:
        if spec.source == NewsSource.FLASHNEWS:
            raise RuntimeError("network blocked")
        if spec.source == NewsSource.SECTION_COMPANY_ANALYSIS:
            return NAVER_SECTION_COMPANY_JSON
        if spec.source == NewsSource.SECTION_MARKET_OUTLOOK:
            return NAVER_SECTION_MARKET_JSON
        return NAVER_MAINNEWS_MARKDOWN

    preview = collect_naver_news_preview(
        StockNewsQuery(
        stock_name="삼성전자",
            aliases=("AI",),
            target_date=date(2026, 6, 1),
        ),
        transport=transport,
    )

    failed = [source for source in preview.sources if source.fetch_error]
    assert len(failed) == 1
    assert failed[0].source == NewsSource.FLASHNEWS
    assert preview.parsed_count > 0
    assert preview.matched_count > 0
    assert any("flashnews" in warning for warning in preview.warnings)


def test_scrapling_transport_uses_expected_commands_and_deletes_temp_files(tmp_path) -> None:
    calls: list[list[str]] = []
    written_paths: list[str] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(command, **_kwargs):
        calls.append(list(command))
        output_path = command[4]
        written_paths.append(output_path)
        if command[2] == "get":
            Path(output_path).write_text(NAVER_SECTION_COMPANY_JSON, encoding="utf-8")
        else:
            Path(output_path).write_text(NAVER_MAINNEWS_MARKDOWN, encoding="utf-8")
        return Result()

    transport = ScraplingNewsTransport(scrapling_exe=tmp_path / "scrapling.exe", runner=runner)
    specs = build_naver_news_request_specs(date(2026, 6, 1))

    page_text = transport(specs[0])
    api_text = transport(specs[4])

    assert "주요뉴스" in page_text
    assert "articles" in api_text
    assert calls[0][:3] == [str(tmp_path / "scrapling.exe"), "extract", "fetch"]
    assert "--ai-targeted" in calls[0]
    assert "--network-idle" in calls[0]
    assert calls[1][:3] == [str(tmp_path / "scrapling.exe"), "extract", "get"]
    assert "--timeout" in calls[1]
    assert all(not Path(path).exists() for path in written_paths)
