import json
from argparse import Namespace
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from stock_monitor import cli
from stock_monitor.config import RuntimeConfig
from stock_monitor.models import Report
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.news.collectors import KST, NewsCollectionPreview, StockNewsQuery
from stock_monitor.news.top2_search import augment_preview, parse_search, search_query


NOW = datetime(2026, 9, 9, 11, 30, tzinfo=KST)
QUERY = StockNewsQuery("두산퓨얼셀", "336260", target_date=NOW.date())
FOCUS = {"items": [{"basis": "source_title", "source_title": "PAFC, 미국진출 성공"}]}


def card(title="[특징주] 두산퓨얼셀 공급 계약", *, when="25분 전", url="https://news.example/article/1"):
    return ("[![뉴스사 프로필 이미지](https://image.example/a)\n"
            "[뉴스사새 창 열림](https://news.example)\n" + when + "\n"
            f"[{title}새 창 열림]({url})[공급 계약 관련 내용새 창 열림]({url})\n")


def test_bounded_cards_identity_and_real_relative_timestamp():
    content = "뉴스검색 결과\n" + card("다른 종목 계약") + "".join(
        card(url=f"https://news.example/article/{n}") for n in range(8))
    articles, cards = parse_search(content, QUERY, NOW)
    assert len(cards) == 5
    assert len(articles) == 4
    assert cards[0]["rejection"] == "stock_not_in_title"
    assert articles[0].title.startswith("[특징주]")
    assert articles[0].published_at == datetime(2026, 9, 9, 11, 5, tzinfo=KST)
    assert cards[1]["raw_time"] == "25분 전"


@pytest.mark.parametrize("when", ["2026.09.09.", "1일 전", "2026.09.08. 12:30", "2026.09.09. 15:30", ""])
def test_no_invented_time_or_wrong_date(when):
    articles, cards = parse_search("뉴스검색 결과\n" + card(when=when), QUERY, NOW)
    assert not articles
    assert cards[0]["accepted"] is False


def test_failure_is_visible_and_does_not_discard_existing_preview():
    preview = NewsCollectionPreview([], [], 12, 10, 0, ["existing warning"])
    def failed_transport(spec):
        raise TimeoutError("private transport details")
    result, trace = augment_preview(preview, QUERY, FOCUS, failed_transport)
    assert result.parsed_count == 12
    assert result.warnings[0] == "existing warning"
    assert trace["status"] == "failed"
    assert "private transport" not in json.dumps(trace)
    assert result.sources[-1].fetched is False


def test_one_request_and_deduplication_and_audit_trace():
    calls = []
    def transport(spec):
        calls.append(spec)
        return "뉴스검색 결과\n" + card() + card()
    result, trace = augment_preview(NewsCollectionPreview([], [], 0, 0, 0, []),
                                   QUERY, FOCUS, transport, clock=lambda: NOW)
    assert len(calls) == 1
    assert trace["query"] == "두산퓨얼셀 PAFC"
    assert trace["added_count"] == result.matched_count == 1
    assert trace["captured_at"] == NOW.isoformat()
    again, trace2 = augment_preview(result, QUERY, FOCUS, transport, clock=lambda: NOW)
    assert again.matched_count == 1
    assert trace2["added_count"] == 0


def test_missing_topic_and_shape_vs_empty_result():
    assert search_query("두산퓨얼셀", {}) == ""
    with pytest.raises(ValueError):
        parse_search("captcha", QUERY, NOW)
    assert parse_search("검색결과가 없습니다", QUERY, NOW) == ([], [])


def test_relative_hour_near_midnight_does_not_claim_verified_date():
    midnight = NOW.replace(hour=0, minute=20)
    assert not parse_search("뉴스검색 결과\n" + card(when="0시간 전"), QUERY, midnight)[0]


def test_canonical_url_duplicate_with_changed_title_is_not_new():
    content = "뉴스검색 결과\n" + card() + card(
        "두산퓨얼셀 투자 확대", url="https://news.example/article/1?utm_source=naver")
    result, trace = augment_preview(NewsCollectionPreview([], [], 0, 0, 0, []),
        QUERY, FOCUS, lambda spec: content, clock=lambda: NOW)
    assert trace["added_count"] == result.matched_count == 1


def test_similar_company_name_is_not_target():
    assert not parse_search("뉴스검색 결과\n" + card("두산퓨얼셀파워 신제품"), QUERY, NOW)[0]


def test_market_context_retains_existing_relevance_classification():
    preview, _ = augment_preview(NewsCollectionPreview([], [], 0, 0, 0, []),
        QUERY, FOCUS, lambda spec: "뉴스검색 결과\n" + card("두산퓨얼셀 등 업종 전반 동향"), clock=lambda: NOW)
    assert preview.articles[0].relevance == "market_context"


def test_collect_save_and_stored_projection_without_independent_promotion(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repo = StockMonitorRepository(config.db_path)
    repo.initialize()
    repo.insert_reports([Report(stock_name=QUERY.stock_name, stock_code=QUERY.stock_code,
        title="PAFC, 미국진출 성공", broker_name="Test", business_date=NOW.date(),
        published_at=NOW, collected_at=NOW, source_id="search-test", identity_key="search-test")])
    repo.rebuild_daily_summaries(NOW.date())
    calls = []
    def transport(spec):
        calls.append(spec.source.value)
        if spec.source.value == "top2_search":
            return "뉴스검색 결과\n" + card(when="2026.09.09. 09:00")
        return '{"articles": []}' if spec.response_format == "focus_json" else ""
    args = Namespace(date=NOW.date(), limit=2, stock_code=[QUERY.stock_code],
                     observation_session="after_close",
                     search_stock_codes=[QUERY.stock_code], scrapling_exe=None,
                     db_path=config.db_path, save_observation=True, confirm_save=True, format="json")
    assert cli._run_news_intelligence_briefing_collect(args, transport=transport) == 0
    payload = json.loads(capsys.readouterr().out)
    assert calls.count("top2_search") == 1
    assert payload["items"][0]["search_collection"]["added_count"] == 1
    assert payload["saved_evidence_count"] == 1
    runs = repo.list_news_intelligence_runs(target_date=NOW.date(), limit=10)
    assert runs[0].source_mode == "naver_5_lane_with_top2_search"
    assert any("top2_search:" in warning for warning in runs[0].warnings)
    assert "top2_session: after_close" in runs[0].warnings
    snapshot = cli.build_web_view_daily_snapshot(config, repo, business_date=NOW.date(), now=NOW)
    summary = snapshot["news_observation_summary"]
    assert summary["unknown_count"] == 1
    assert summary["independent_count"] == summary["positive_direct_count"] == 0
    assert payload["sends_telegram"] is False


@pytest.mark.parametrize("missing,throws", [(False, False), (True, False), (False, True)])
def test_after_close_uses_separate_cohort_and_does_not_replace_poll_event(tmp_path, monkeypatch, missing, throws):
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    events, calls = [], []
    repo = SimpleNamespace(record_operation_event=events.append)
    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", lambda *a, **kw: {
        "rows": [{"stock_code": "111111"}, {"stock_code": "222222"}],
        "close_reassessment": {"available": True, "rows": [
            {"stock_code": "333333"}, {"stock_code": "444444"}, {"stock_code": "555555"}]},
    })
    monkeypatch.setattr(cli, "_resolve_web_view_scrapling_exe", lambda config: None)
    def collect(args):
        calls.append(args)
        if throws:
            raise TimeoutError("transport failed")
        print(json.dumps({"items": [{"search_collection": {"status": "success"}} for _ in args.stock_code],
                          "saved_evidence_count": 2}))
        return 0
    monkeypatch.setattr(cli, "_run_news_intelligence_briefing_collect", collect)
    result = cli._collect_after_close_top2_news(config, repo, business_date=NOW.date(),
        incomplete_codes={"333333"} if missing else set())
    assert result["status"] == ("skipped" if missing else "failed" if throws else "success")
    assert len(calls) == (0 if missing else 1)
    if calls:
        assert calls[0].stock_code == calls[0].search_stock_codes == ["333333", "444444"]
        assert calls[0].observation_session == "after_close"
    assert len(events) == 1
    assert events[0].component == "after-close-news"
