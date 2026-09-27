"""Offline explanation comparison. Never used for candidate selection or delivery."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from stock_monitor.news.linked_evidence import canonicalize_news_url


VERSION = "evidence-review-v1.2-context"
KST = ZoneInfo("Asia/Seoul")
MARKERS = {
    "SUPPORT": ("영향 제한", "우려 과도", "우려는 과도", "자사주", "성장", "상향"),
    "RISK": ("임상 보류", "임상보류", "하락", "손실", "중단", "리스크"),
    "UNKNOWN": ("추가 자료", "추가자료", "예정", "전망", "기대", "가능성"),
}


def _time(value):
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=KST) if parsed.tzinfo is None else parsed


def _claims(member, other_names=()):
    """Keep uncertain text visible; context attribution is not semantic verification."""
    names = [name for name in (member.get("stock_name"), member.get("matched_alias")) if name]
    anchored = member["source_lane"] in ("report", "stored_flow")
    claims = []
    for field in ("title", "summary"):
        text = member.get(field) or ""
        # A truncated digest cannot carry an entity across the missing passage.
        parts = re.split(r"(\.{3,}|…+|[◆■]|\n+)|(?<=[.!?])\s+", text)
        for part in parts:
            if not part or not part.strip():
                continue
            if re.fullmatch(r"\.{3,}|…+|[◆■]|\n+", part):
                anchored = False
                continue
            direct = any(name in part for name in names)
            other_subject = any(name in part for name in other_names)
            if other_subject:
                anchored = False
            anchored = (anchored or direct) and not other_subject
            relation = "mixed" if direct and other_subject else "direct" if direct else "context" if anchored else "unresolved"
            found = False
            deteriorating_growth = list(re.finditer(
                r"성장(?:세|률)?[^.!?,\n]{0,18}?(?:둔화|주춤|낮아)", part))
            for direction, markers in MARKERS.items():
                hits = [marker for marker in markers if marker in part]
                if direction == "SUPPORT" and "성장" in hits and deteriorating_growth:
                    remaining = part
                    for match in reversed(deteriorating_growth):
                        remaining = remaining[:match.start()] + remaining[match.end():]
                    if "성장" not in remaining:
                        hits.remove("성장")
                if direction == "RISK":
                    hits.extend(match.group() for match in deteriorating_growth)
                if direction == "SUPPORT":
                    hits.extend(m.group() for m in re.finditer(
                        r"우려(?:가|는)?\s*과도|영향(?:은|이|는)?\s*제한", part)
                        if m.group() not in hits)
                if direction == "RISK" and not any("임상" in hit for hit in hits):
                    hold = re.search(r"임상[^.!?\n]{0,16}?보류", part)
                    if hold:
                        hits.append(hold.group())
                if not hits:
                    continue
                negated = direction == "RISK" and all(
                    re.search(re.escape(hit) + r"(?:이|은|는|도|가)?\s*(?:없|아니|발생하지 않)", part)
                    for hit in hits)
                if direction == "SUPPORT" and re.search(
                    r"(?:과도|제한)(?:적)?(?:이지|하지)\s*않", part):
                    negated = True
                reason = "negation_requires_review" if negated else (
                    "subject_unresolved" if not anchored else "text_cue_only")
                claims.append(dict(direction="UNKNOWN" if reason != "text_cue_only" else direction,
                                   source_id=member["id"], field=field, excerpt=part.strip(),
                                   markers=hits, verification=reason, attribution=relation))
                found = True
            if not found:
                claims.append(dict(direction="UNKNOWN", source_id=member["id"], field=field,
                                   excerpt=part.strip(), verification="unclassified_text",
                                   attribution=relation))
    return claims


def _clusters(rows):
    groups = {}
    subjects = {(row["stock_code"], row["stock_name"]) for row in rows if row.get("stock_name")}
    for row in rows:
        url = canonicalize_news_url(row.get("url") or "")
        title = re.sub(r"\s+", " ", row["title"]).strip()
        event = row.get("confirmed_event")
        if event and not all(event.get(k) for k in ("id", "date", "basis")):
            raise ValueError("confirmed_event requires id, date and verification basis")
        identity = ("event", event["date"], event["id"]) if event else (
            ("article", url) if url else ("title", (row.get("published_at") or row["available_at"])[:10],
                                         title or row["id"]))
        key = (row["stock_code"], identity)
        groups.setdefault(key, []).append(row)
    result = []
    for (code, _), members in groups.items():
        claims = []
        for member in members:
            claims.extend(_claims(member, [name for stock_code, name in subjects if stock_code != code]))
        result.append(dict(stock_code=code, title=members[0]["title"],
                           member_ids=[m["id"] for m in members], claims=claims,
                           relation="same_event" if members[0].get("confirmed_event") else "unresolved",
                           independence="unverified",
                           merge_reason=("explicit_verified_event" if members[0].get("confirmed_event")
                                         else "same_article_url" if members[0].get("url") else "exact_title_only"),
                           event_verification=[m["confirmed_event"] for m in members if m.get("confirmed_event")],
                           lineage=[dict(source_id=m["id"], value=m.get("lineage_type", "unknown"))
                                    for m in members]))
    return result


def build_review(rows, *, as_of, selected_codes):
    """Project a fixed input into common evidence and selected-only search context."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    included, excluded = [], []
    for row in rows:
        try:
            available = _time(row["available_at"])
            published = _time(row["published_at"]) if row.get("published_at") else available
        except (KeyError, ValueError, TypeError):
            excluded.append(dict(id=row["id"], reason="unknown_timestamp"))
            continue
        if max(available, published) > as_of:
            excluded.append(dict(id=row["id"], reason="after_cutoff"))
        else:
            included.append(dict(row))
    common = [r for r in included if r["source_lane"] != "top2_search"]
    search = [r for r in included if r["source_lane"] == "top2_search"
              and r["stock_code"] in selected_codes]
    serialized = json.dumps(included, ensure_ascii=False, sort_keys=True)
    return dict(version=VERSION, input_as_of=as_of.isoformat(),
                mode="stored_explanation_comparison_not_intraday_replay",
                input_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
                input_ids=[r["id"] for r in included], inputs=included, excluded=excluded,
                common_clusters=_clusters(common), search_supplement=_clusters(search),
                selected_codes=list(selected_codes), ranking_changed=False)


def load_stored(db_path, target_date):
    """Read a consistent SQLite snapshot without initializing or migrating it."""
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        rows = [dict(r) for r in conn.execute(
            "SELECT run_id || ':' || evidence_key AS id, stock_code, stock_name, matched_alias, title, summary, "
            "source_lane, lineage_type, published_at, created_at AS available_at, url "
            "FROM report_linked_news_evidence WHERE target_date=? ORDER BY run_id,evidence_key",
            (target_date,))]
        reports = [dict(r) for r in conn.execute(
            "SELECT * FROM reports WHERE business_date=? ORDER BY id", (target_date,))]
        flows = [dict(r) for r in conn.execute(
            "SELECT * FROM stock_investor_flow_daily WHERE business_date=? "
            "ORDER BY stock_code,investor_type", (target_date,))]
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM operation_events WHERE business_date=? AND component='poll-news' "
            "AND status='success' ORDER BY event_time DESC,id DESC", (target_date,))]
    return rows, reports, flows, events


def stored_inputs(news, reports, flows):
    rows = list(news)
    for report in reports:
        rows.append(dict(id=f"report:{report['id']}", stock_code=report["stock_code"],
                         stock_name=report["stock_name"],
                         title=report["title"], summary="", url=report["source_url"],
                         source_lane="report", lineage_type="original_report",
                         published_at=report["published_at"], available_at=report["collected_at"]))
    for flow in flows:
        rows.append(dict(id=f"flow:{flow['business_date']}:{flow['stock_code']}:{flow['investor_type']}",
                         stock_code=flow["stock_code"],
                         title=f"{flow['investor_type']} 저장 수급 ({flow['business_date']})",
                         summary=f"순매수량 {flow['net_buy_volume']} {flow['volume_unit']}; "
                                 f"순매수금액 {flow['net_buy_amount']} {flow['amount_unit']}",
                         url="", source_lane="stored_flow", lineage_type="stored_measurement",
                         available_at=flow["fetched_at"]))
    return rows


def render_markdown(result):
    lines = ["# 저장 근거 설명 비교", "", f"- 버전: {result['version']}",
             f"- 입력 관측 시각: {result['input_as_of']}",
             f"- 입력 SHA256: {result['input_sha256']}",
             "- 일자 최종 저장 설명 비교. 과거 장중 순위 재현 및 NEW 순위 평가는 하지 않음.",
             "- 자동 묶음은 동일 URL/동일 제목까지만. 사건 관계·독립성은 미확인.",
             "- 명시적 사건 관계가 입력된 경우에만 사건 병합. 관계 검토와 사실 검증은 별개.",
             "- 방향은 제목/요약의 문자열 단서이며 원문 사실 확인이 아님.",
             "- UNKNOWN은 미분류 또는 확인 필요 문구이며 출처 계보 unknown과 별개. 감점 없음.", ""]
    for label, key in (("공통 근거", "common_clusters"), ("선정 종목 검색 보충", "search_supplement")):
        lines += [f"## {label}", ""]
        for cluster in result[key]:
            lines += [f"### {cluster['stock_code']} · {cluster['title']}", "",
                      f"기존 저장 행 {len(cluster['member_ids'])}개 → 기사/제목 묶음 1개. "
                      "독립 사건 수로 해석하지 않음.", ""]
            lines += [f"- 병합 근거: {cluster['merge_reason']} / 관계: {cluster['relation']}"]
            lines += [f"- 관계 검토: {event['basis']}" for event in cluster["event_verification"][:1]]
            seen = set()
            for claim in cluster["claims"]:
                identity = (claim["direction"], claim["excerpt"])
                if identity not in seen:
                    lines.append(f"- {claim['direction']}: {claim['excerpt']} "
                                 f"({claim['verification']}; {claim.get('attribution', 'unresolved')})")
                    seen.add(identity)
            lines += ["- 확인할 점: 원문에서 사건 시점·후속 조치·재인용 출처를 확인.", ""]
            sources = {r["id"]: r for r in result["inputs"]}
            urls = dict.fromkeys(sources[s]["url"] for s in cluster["member_ids"] if sources[s].get("url"))
            lines += [f"- [저장 출처]({url})" for url in urls]
            lines += [f"- 입력 ID: `{', '.join(cluster['member_ids'])}`", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Current read only: no --as-of option that could imply historical row versions.
    as_of = datetime.now(KST)
    rows, reports, flows, events = load_stored(args.db, args.date)
    match = re.search(r"(?:^|;\s*)target_stock_codes=([^;]*)", events[0]["detail"]) if events else None
    selected = match.group(1).split(",")[:2] if match else []
    result = build_review(stored_inputs(rows, reports, flows), as_of=as_of, selected_codes=selected)
    result.update(target_date=args.date, stored_reports=reports, stored_flows=flows,
                  selection_events=events, selection_mode="recorded_regular_targets_not_OLD_reconstruction",
                  implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "review.md").write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(dict(input_rows=len(result["input_ids"]),
                          common_clusters=len(result["common_clusters"]),
                          search_clusters=len(result["search_supplement"]),
                          excluded=len(result["excluded"])), ensure_ascii=False))


if __name__ == "__main__":
    main()
