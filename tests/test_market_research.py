from __future__ import annotations

import pytest

from stock_monitor.market_research import build_market_research_note, format_market_research_note_markdown


def _snapshot(*, generated_at_kst: str = "2026-07-28T15:05:00+09:00") -> dict[str, object]:
    return {
        "metadata": {
            "date": "2026-07-28",
            "snapshot_time_kst": "15:00",
            "generated_at_kst": generated_at_kst,
        },
        "top2": [{"stock_code": "005930", "stock_name": "Samsung Electronics"}],
    }


def _market_flow() -> dict[str, object]:
    return {
        "surface": "news-flow-source-probe",
        "operator_only": True,
        "source_urls": ["https://stock.naver.com/news/mainnews"],
        "market_mood": "Theme-led market flow",
        "sector_themes": [{"label": "Semiconductor/AI", "article_count": 2}],
        "key_issues": [],
        "caution_signals": [],
        "warnings": [],
    }


def test_build_market_research_note_keeps_candidate_and_market_flow_separate() -> None:
    note = build_market_research_note(_snapshot(), _market_flow())

    assert note["operator_only"] is True
    assert note["writes_db"] is False
    assert note["candidate_evidence"]["top2"][0]["stock_code"] == "005930"
    assert note["market_context"]["status"] == "available"
    assert note["market_context"]["source_urls"] == ["https://stock.naver.com/news/mainnews"]


def test_build_market_research_note_marks_late_snapshot_invalid_for_slot() -> None:
    note = build_market_research_note(_snapshot(generated_at_kst="2026-07-28T23:09:00+09:00"))

    assert note["snapshot"]["slot_status"] == "invalid_for_slot"
    assert note["snapshot"]["slot_reason"] == "late_generation"
    assert note["candidate_evidence"]["top2"][0]["stock_code"] == "005930"


def test_build_market_research_note_rejects_non_operator_market_flow() -> None:
    with pytest.raises(ValueError, match="operator-only news-flow source probe"):
        build_market_research_note(_snapshot(), {"surface": "other", "operator_only": False})


def test_build_market_research_note_marks_failed_market_flow_unavailable() -> None:
    note = build_market_research_note(
        _snapshot(),
        {
            "surface": "news-flow-source-probe",
            "operator_only": True,
            "error": "missing Scrapling executable",
            "source_urls": ["https://stock.naver.com/news/mainnews"],
        },
    )

    assert note["market_context"]["status"] == "unavailable"
    assert note["market_context"]["error"] == "missing Scrapling executable"


def test_market_research_markdown_keeps_the_operator_boundary_visible() -> None:
    output = format_market_research_note_markdown(build_market_research_note(_snapshot(), _market_flow()))

    assert "## Snapshot slot" in output
    assert "## Candidate evidence" in output
    assert "## Market context" in output
    assert "- writes_db: false" in output


def test_market_research_markdown_shows_market_context_error() -> None:
    output = format_market_research_note_markdown(
        build_market_research_note(
            _snapshot(),
            {"surface": "news-flow-source-probe", "operator_only": True, "error": "probe failed"},
        )
    )

    assert "- error: probe failed" in output
