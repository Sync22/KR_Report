from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from stock_monitor.news.evidence_review import build_review


AS_OF = datetime(2026, 9, 19, tzinfo=timezone.utc)


def item(key, **kwargs):
    return dict(id=key, stock_code="326030", stock_name="SK바이오팜", title="SK바이오팜 임상 보류 영향 제한적",
                summary="추가 자료 제출 필요", source_lane="regular",
                lineage_type="unknown", available_at="2026-09-15T12:00:00+09:00",
                url="", **kwargs)


def test_exact_title_groups_but_preserves_mixed_claims_and_unknown_lineage():
    result = build_review([item("a"), item("b")], as_of=AS_OF, selected_codes=[])
    clusters = result["common_clusters"]
    assert len(clusters) == 1
    assert clusters[0]["member_ids"] == ["a", "b"]
    assert {c["direction"] for c in clusters[0]["claims"]} == {"SUPPORT", "RISK", "UNKNOWN"}
    assert clusters[0]["independence"] == "unverified"
    assert clusters[0]["relation"] == "unresolved"


def test_same_topic_different_titles_not_merged():
    a, b = item("a"), item("b")
    b["title"] = "임상 신규 시험 개시"
    assert len(build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"]) == 2


def test_search_excluded_before_common_projection_and_only_selected_enriched():
    base = build_review([item("a")], as_of=AS_OF, selected_codes=["326030"])
    search = item("s")
    search["source_lane"] = "top2_search"
    other = dict(search, id="other", stock_code="111111")
    result = build_review([item("a"), search, other], as_of=AS_OF, selected_codes=["326030"])
    assert result["common_clusters"] == base["common_clusters"]
    assert result["search_supplement"][0]["member_ids"] == ["s"]
    assert build_review([search], as_of=AS_OF, selected_codes=[])["search_supplement"] == []


def test_cutoff_and_missing_timestamp_fail_closed():
    future, missing = item("future"), item("missing")
    future["available_at"] = "2026-09-20T00:00:00+09:00"
    missing["available_at"] = ""
    result = build_review([item("ok"), future, missing], as_of=AS_OF, selected_codes=[])
    assert result["input_ids"] == ["ok"]
    assert {r["id"] for r in result["excluded"]} == {"future", "missing"}


def test_same_url_is_article_identity_not_independent_event():
    a, b = item("a"), item("b")
    a["url"] = b["url"] = "https://example.com/story"
    b["title"] = "수정된 제목"
    cluster = build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"][0]
    assert cluster["merge_reason"] == "same_article_url"
    assert cluster["independence"] == "unverified"


def test_confirmed_event_groups_reports_and_news_but_not_other_events():
    rows = [item(str(i)) for i in range(6)]
    for i, row in enumerate(rows):
        row.update(source_lane="report" if i < 2 else "regular", title=f"다른 제목 {i}",
                   confirmed_event=dict(id="contract-a" if i < 5 else "contract-b",
                                        date="2026-09-15", basis="fixture: separate contract announcement IDs"))
    clusters = build_review(rows, as_of=AS_OF, selected_codes=[])["common_clusters"]
    assert [len(c["member_ids"]) for c in clusters] == [5, 1]
    assert clusters[0]["relation"] == "same_event"
    assert clusters[0]["independence"] == "unverified"


def test_identical_title_on_different_dates_remains_separate():
    a, b = item("a"), item("b")
    b["available_at"] = "2026-09-16T12:00:00+09:00"
    assert len(build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"]) == 2


def test_unclassified_member_survives_beside_classified_claim():
    a, b = item("a"), item("b")
    a["url"] = b["url"] = "https://example.com/story"
    b.update(title="새로운 세부 내용", summary="")
    claims = build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"][0]["claims"]
    assert any(c["source_id"] == "b" and c["direction"] == "UNKNOWN" for c in claims)


@pytest.mark.parametrize("persistent,revision,mentions,expected", [
    (True, {}, 0, 4),
    (False, {"available": True, "direction": "up"}, 0, 3),
    (False, {"available": True, "direction": "down"}, 0, 2),
    (False, {}, 2, 1),
])
def test_old_flow_contributions_remain_characterized(persistent, revision, mentions, expected):
    from stock_monitor.cli import _web_view_observation_candidate_profile

    result = _web_view_observation_candidate_profile(
        SimpleNamespace(mention_count=mentions, dominant_opinion="N/A"),
        broker_count=0, target_range={}, market_reference=None,
        stock_flow_rows=[object()], rank_reference=None, report_intensity={},
        target_revision=revision, price_volume_reference={},
        flow_window_reference={"persistence": {"foreign": {"available": persistent, "streak_days": 2}}},
    )
    assert result["sort_signal"] == expected


def test_load_stored_does_not_change_database(tmp_path):
    import sqlite3
    from stock_monitor.news.evidence_review import load_stored

    path = tmp_path / "input.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE report_linked_news_evidence (run_id,evidence_key,stock_code,stock_name,matched_alias,title,summary,source_lane,lineage_type,published_at,created_at,url,target_date)")
        conn.execute("CREATE TABLE reports (id,business_date)")
        conn.execute("CREATE TABLE stock_investor_flow_daily (business_date,stock_code,investor_type)")
        conn.execute("CREATE TABLE operation_events (business_date,component,status,event_time,id)")
    before = path.read_bytes()
    assert load_stored(path, "2026-09-15") == ([], [], [], [])
    assert path.read_bytes() == before


def context_claims(title, summary):
    row = item("context")
    row.update(stock_name="롯데이노베이트", matched_alias="롯데이노베이트", title=title, summary=summary)
    return build_review([row], as_of=AS_OF, selected_codes=[])["common_clusters"][0]["claims"]


def test_digest_gap_does_not_attribute_other_topic_risk():
    claims = context_claims("롯데이노베이트, 데이터센터 성장", "롯데이노베이트의 사업이... 기본 모델 대비 성능 하락폭을 방어했다.")
    assert not any(c["direction"] == "RISK" for c in claims)
    assert any("성능 하락폭" in c["excerpt"] and c["direction"] == "UNKNOWN" for c in claims)


@pytest.mark.parametrize("summary", ["동사의 매출 성장세가 이어진다.", "매출 성장세가 이어진다.", "사업을 설명했다. 매출 성장세가 이어진다."])
def test_title_context_supports_pronouns_and_omitted_subject(summary):
    claims = context_claims("롯데이노베이트 사업 현황", summary)
    assert any(c["direction"] == "SUPPORT" and c.get("field") == "summary" for c in claims)


def test_explicit_subject_after_gap_restores_context():
    claims = context_claims("롯데이노베이트 현황", "기타 소식... 롯데이노베이트의 매출 성장세가 이어진다.")
    assert any(c["direction"] == "SUPPORT" for c in claims)


def test_unrecognized_paraphrase_is_visible_instead_of_dropped():
    claims = context_claims("롯데이노베이트 현황", "고객사 주문이 밀려 생산라인을 더 돌린다.")
    assert any(c["direction"] == "UNKNOWN" and "생산라인" in c["excerpt"] for c in claims)


def test_negated_loss_is_not_asserted_as_risk():
    claims = context_claims("롯데이노베이트 현황", "손실은 없었다.")
    assert not any(c["direction"] == "RISK" for c in claims)
    assert any("손실" in c["excerpt"] for c in claims)


def test_known_other_company_resets_inherited_subject():
    a, b = item("a"), item("b")
    a.update(title="SK바이오팜 현황", summary="다른회사는 손실이 발생했다. 손실이 이어졌다.")
    b.update(stock_code="111111", stock_name="다른회사", title="다른회사 현황", summary="")
    claims = build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"][0]["claims"]
    assert not any(c["direction"] == "RISK" for c in claims)


@pytest.mark.parametrize("phrase", ["임상 부분 보류", "임상 2·3상이 부분 보류", "임상보류"])
def test_clinical_hold_variants_do_not_require_exact_phrase(phrase):
    claims = context_claims("롯데이노베이트 현황", phrase)
    assert any(c["direction"] == "RISK" for c in claims)


def test_mixed_named_subjects_are_not_assigned_to_one_stock():
    a, b = item("a"), item("b")
    a.update(summary="SK바이오팜과 다른회사의 손실 현황을 비교했다.")
    b.update(stock_code="111111", stock_name="다른회사", title="다른회사 현황", summary="")
    claims = build_review([a, b], as_of=AS_OF, selected_codes=[])["common_clusters"][0]["claims"]
    assert not any(c["direction"] == "RISK" and c.get("field") == "summary" for c in claims)


@pytest.mark.parametrize("phrase", ["우려가 과도하다", "영향은 제한적일 것이다"])
def test_mitigating_phrase_accepts_particle(phrase):
    claims = context_claims("롯데이노베이트 현황", phrase)
    assert any(c["direction"] == "SUPPORT" for c in claims)


def test_negated_mitigation_not_promoted_to_support():
    claims = context_claims("롯데이노베이트 현황", "영향은 제한적이지 않다.")
    assert not any(c["direction"] == "SUPPORT" for c in claims)


@pytest.mark.parametrize("text", ["성장세는 다소 둔화했다.", "성장률 눈높이도 낮아졌다.", "성장세가 이번 3분기 다소 주춤할 수 있다."])
def test_growth_with_deterioration_is_not_positive(text):
    claims = context_claims("롯데이노베이트 현황", text)
    assert any(c["direction"] == "RISK" for c in claims)
    assert not any(c["direction"] == "SUPPORT" for c in claims)


def test_separate_growth_claim_survives_deterioration():
    claims = context_claims("롯데이노베이트 현황", "국내 성장세는 둔화했지만 해외 성장은 이어졌다.")
    assert {c["direction"] for c in claims} >= {"SUPPORT", "RISK"}


def test_negated_growth_deterioration_is_not_risk():
    claims = context_claims("롯데이노베이트 현황", "성장 둔화는 없었다.")
    assert not any(c["direction"] == "RISK" for c in claims)
