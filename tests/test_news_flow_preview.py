from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from stock_monitor.news.flow import (
    build_news_flow_preview,
    format_news_flow_preview_text,
    format_news_flow_slot_section,
    parse_news_flow_json,
)


SOURCE_URLS = (
    "https://example.test/market-flow",
    "https://example.test/sector-flow",
)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "news_flow_preview" / "market_flow_2026_06_01.json"


def _fixture_payload() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_parse_news_flow_json_uses_only_requested_source_urls() -> None:
    collection = parse_news_flow_json(_fixture_payload(), source_urls=SOURCE_URLS)

    assert collection.source_urls == SOURCE_URLS
    assert collection.parsed_count == 4
    assert collection.deduped_count == 4
    assert [source.source_url for source in collection.sources] == list(SOURCE_URLS)
    assert collection.articles[0].title == "Samsung Electronics and SK Hynix rise on AI chip supply news"
    assert collection.articles[0].published_at.date() == date(2026, 6, 1)
    assert collection.articles[0].source_page_url == SOURCE_URLS[0]
    assert any("not in requested source URLs" in warning for warning in collection.warnings)


def test_build_news_flow_preview_summarizes_market_flow_without_candidate_language() -> None:
    collection = parse_news_flow_json(_fixture_payload(), source_urls=SOURCE_URLS)

    preview = build_news_flow_preview(collection).to_dict()

    assert preview["surface"] == "news-flow-preview"
    assert preview["operator_only"] is True
    assert preview["writes_db"] is False
    assert preview["sends_telegram"] is False
    assert preview["registers_scheduler"] is False
    assert preview["connects_web_view"] is False
    assert preview["source_urls"] == list(SOURCE_URLS)
    assert preview["article_count"] == 4
    assert preview["repeated_stocks"][0]["name"] == "Samsung Electronics"
    assert preview["repeated_stocks"][0]["article_count"] == 2
    assert any(theme["label"] == "Semiconductor/AI" for theme in preview["sector_themes"])
    assert any(issue["label"] == "Supply/contract" for issue in preview["key_issues"])
    assert any(signal["label"] == "Volatility/overheating" for signal in preview["caution_signals"])

    draft = str(preview["telegram_draft"])
    forbidden = ("recommendation", "buy", "sell", "score", "grade", "candidate")
    assert not any(term in draft.casefold() for term in forbidden)
    assert "source URL" in draft


def test_format_news_flow_preview_text_includes_draft_and_source_boundaries() -> None:
    collection = parse_news_flow_json(_fixture_payload(), source_urls=SOURCE_URLS)
    preview = build_news_flow_preview(collection)

    output = format_news_flow_preview_text(preview)

    assert "News flow preview" in output
    assert "source URLs: 2" in output
    assert "repeated stocks:" in output
    assert "telegram draft:" in output
    assert "writes_db: False" in output
    assert "sends_telegram: False" in output


def test_format_news_flow_slot_section_uses_current_market_briefing_slots() -> None:
    collection = parse_news_flow_json(_fixture_payload(), source_urls=SOURCE_URLS)
    preview = build_news_flow_preview(collection)

    mood_output = "\n".join(format_news_flow_slot_section(preview, slot="mood"))
    lunch_output = "\n".join(format_news_flow_slot_section(preview, slot="lunch"))
    preclose_output = "\n".join(format_news_flow_slot_section(preview, slot="preclose"))

    assert "당일 흐름 참고" in mood_output
    assert "오전 누적 확인" in lunch_output
    assert "마감 전 유지 흐름" in preclose_output
    for output in (mood_output, lunch_output, preclose_output):
        assert "뉴스 source flow" in output
        for forbidden in ("추천", "매수 기회", "전략 제안", "점수", "등급"):
            assert forbidden not in output


def test_news_flow_preview_does_not_match_short_terms_inside_unrelated_words() -> None:
    content = json.dumps(
        {
            "sources": [
                {
                    "source_url": "https://example.test/unrelated",
                    "articles": [
                        {
                            "title": "Company said revenue was flat",
                            "date": "2026-06-01T09:30:00+09:00",
                            "url": "https://news.example/unrelated-1",
                            "summary": "The chairman explained a routine quarterly update.",
                        }
                    ],
                }
            ]
        }
    )

    preview = build_news_flow_preview(
        parse_news_flow_json(content, source_urls=("https://example.test/unrelated",))
    )

    assert preview.sector_themes == []
    assert preview.key_issues == []
    assert preview.caution_signals == []


def test_news_flow_preview_ignores_low_signal_notice_articles_for_topics() -> None:
    content = json.dumps(
        {
            "sources": [
                {
                    "source_url": "https://example.test/notices",
                    "articles": [
                        {
                            "title": "Correction: rate chart source",
                            "date": "2026-06-01T09:30:00+09:00",
                            "url": "https://news.example/notice-1",
                            "summary": "The inflation and yield chart attribution was corrected.",
                        }
                    ],
                }
            ]
        }
    )

    preview = build_news_flow_preview(
        parse_news_flow_json(content, source_urls=("https://example.test/notices",))
    )

    assert preview.sector_themes == []
    assert preview.key_issues == []
    assert preview.caution_signals == []


def test_news_flow_preview_detects_korean_theme_and_caution_terms() -> None:
    content = json.dumps(
        {
            "sources": [
                {
                    "source_url": "https://example.test/korean-flow",
                    "source": "국내시황",
                    "articles": [
                        {
                            "title": "삼성전자·SK하이닉스, HBM 공급 기대에 반도체 강세",
                            "date": "2026-06-01T09:30:00+09:00",
                            "url": "https://news.example/k1",
                            "source": "국내시황",
                            "summary": "AI 메모리 수요와 공급 계약 기대가 반도체 업종 흐름을 이끌었다.",
                        },
                        {
                            "title": "삼성전자 단기 급등 후 변동성 주의",
                            "date": "2026-06-01T10:00:00+09:00",
                            "url": "https://news.example/k2",
                            "source": "국내시황",
                            "summary": "과열 부담과 차익실현 가능성이 경계 신호로 언급됐다.",
                        },
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )

    preview = build_news_flow_preview(
        parse_news_flow_json(content, source_urls=("https://example.test/korean-flow",))
    ).to_dict()

    assert preview["repeated_stocks"][0]["name"] == "Samsung Electronics"
    assert any(theme["label"] == "Semiconductor/AI" for theme in preview["sector_themes"])
    assert any(signal["label"] == "Volatility/overheating" for signal in preview["caution_signals"])
    assert "매매 판단 없이" in preview["telegram_draft"]
