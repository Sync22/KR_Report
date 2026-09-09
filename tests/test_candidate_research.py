from urllib.parse import parse_qs, urlparse

from stock_monitor.news.core_keywords import CoreKeywordDocument
from stock_monitor.news.candidate_research import build_candidate_research_focus


def test_known_keywords_use_stage2_queries_and_preserve_source():
    document = CoreKeywordDocument("report", "삼성전자", "005930", "HBM4 고객 인증", "")
    focus = build_candidate_research_focus("삼성전자", (document,))
    assert focus["items"][0]["query"] == "삼성전자 HBM4"
    assert focus["items"][0]["source_title"] == document.title
    assert focus["items"][0]["basis"] == "keywords"


def test_unseen_report_keeps_source_title_instead_of_inventing_keywords():
    title = "아시아 유일 통합 AI 팩토리 사업자로의 부상"
    document = CoreKeywordDocument("report", "NAVER", "035420", title, "")
    focus = build_candidate_research_focus("NAVER", (document, document))
    assert len(focus["items"]) == 1
    item = focus["items"][0]
    assert item["topic"] == title and item["basis"] == "source_title"
    assert parse_qs(urlparse(item["search_url"]).query)["query"] == ["NAVER " + title]


def test_empty_and_foreign_and_corrupt_documents_do_not_create_prompts():
    documents = tuple(CoreKeywordDocument("report", name, None, title, "") for name, title in (
        ("NAVER", ""), ("NAVER", "깨진\ufffd제목"), ("다른종목", "HBM4"),
    ))
    assert build_candidate_research_focus("NAVER", documents)["available"] is False


def test_prompts_are_bounded_and_url_values_are_encoded():
    documents = tuple(CoreKeywordDocument("report", "NAVER", None, f"제목 {i} & query=evil", "") for i in range(5))
    focus = build_candidate_research_focus("NAVER", documents)
    assert len(focus["items"]) == 3
    params = parse_qs(urlparse(focus["items"][0]["search_url"]).query)
    assert params == {"where": ["news"], "query": ["NAVER 제목 0 & query=evil"]}


def test_actual_candidate_snapshot_attaches_focus_only_to_selected_rows(tmp_path, monkeypatch):
    from dataclasses import replace
    from datetime import date, datetime
    from stock_monitor import cli
    from stock_monitor.config import RuntimeConfig
    from stock_monitor.db.repository import StockMonitorRepository
    from stock_monitor.models import Report

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    day = date(2026, 9, 8)
    reports = [Report(
        stock_name=f"테스트{i}", stock_code=f"00000{i}", title=f"미관측 주제 {i}",
        broker_name="증권사", published_at=datetime(2026, 9, 8, 9), business_date=day,
        collected_at=datetime(2026, 9, 8, 9), target_price_value=10000,
        opinion_normalized="buy", identity_key=f"research-{i}", source_id=f"research-{i}",
    ) for i in range(3)]
    repository.insert_reports(reports + [replace(
        report, broker_name="다른증권사", title=report.title + " 후속",
        identity_key=report.identity_key + "-2", source_id=report.source_id + "-2",
    ) for report in reports])
    repository.rebuild_daily_summaries(day)
    snapshot = cli.build_web_view_candidate_evidence_snapshot(config, repository, business_date=day, limit=3)
    selected = [row for row in snapshot["rows"] if row["selected"]]
    assert len(selected) == 2
    for row in selected:
        item = row["research_focus"]["items"][0]
        assert item["query"].startswith(row["stock_name"] + " ")
        assert item["basis"] == "source_title"
    assert all("research_focus" not in row for row in snapshot["rows"] if not row["selected"])


def test_main_renders_research_link_outside_stock_detail_button():
    from stock_monitor import cli
    html = cli._render_web_view_html()
    assert '</button>${renderCandidateResearchFocus(item.research_focus)}</div>' in html
    assert "encodeURIComponent(query)" in html
    assert "esc(item.topic || item.source_title" in html
    assert 'rel="noopener noreferrer"' in html


def test_stored_news_title_can_supply_a_topic_without_report():
    from stock_monitor import cli
    focus = cli._candidate_research_focus("NAVER", "035420", [], news_titles=("기업 검색 신규 계약",))
    assert focus["items"][0]["source_kind"] == "저장 뉴스"
    assert focus["items"][0]["source_title"] == "기업 검색 신규 계약"
