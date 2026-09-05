from __future__ import annotations

"""Append one isolated Insane Search shadow-run record.

This is deliberately not a Stock Monitor CLI command: it copies the operating
SQLite database into a temporary file, builds the existing candidate snapshot
there, and writes only the lab JSONL manifest.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "codex" / "operations" / "insane-search-shadow.jsonl"
CURRENT_SCHEMA = "insane-search-shadow-run/v3"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one 12:00/15:00 KST Insane Search lab shadow pass.")
    parser.add_argument("--cutoff", help="KST ISO timestamp; defaults to now.")
    parser.add_argument("--db-path", type=Path, default=PROJECT_ROOT / "data" / "stock_monitor.db")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--engine-python", type=Path)
    parser.add_argument("--engine-root", type=Path)
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--search-top-n", type=int, default=5)
    parser.add_argument("--article-limit", type=int, default=5)
    parser.add_argument("--aggregate", action="store_true", help="Read the append-only manifest and print aggregate metrics.")
    return parser.parse_args()


def _cutoff(value: str | None) -> datetime:
    parsed = datetime.fromisoformat(value) if value else datetime.now(KST)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST).replace(microsecond=0)


def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _copy_database_read_only(source_path: Path, destination_path: Path) -> None:
    source_uri = f"file:{source_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(destination_path) as destination:
        source.backup(destination)


def _engine_fetch(
    *,
    engine_python: Path,
    engine_root: Path,
    url: str,
    selector: str,
) -> dict[str, object]:
    # Content stays inside this subprocess result and is reduced to article metadata.
    program = r'''
import json, sys
from urllib.parse import urljoin, urlparse
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).parent))
from bs4 import BeautifulSoup
from engine import fetch
result = fetch(sys.argv[2], success_selectors=[sys.argv[3]], timeout=25)
payload = {
  "ok": bool(result.ok), "verdict": result.verdict,
  "profile_used": result.profile_used,
  "summary": result.summary,
  "trace_count": len(result.trace or []), "links": [],
  "title": None, "published_at": None, "source": None,
}
if result.ok:
  soup = BeautifulSoup(result.content or "", "html.parser")
  if sys.argv[4] == "search":
    for anchor in soup.select("a[href]"):
      title = anchor.get_text(" ", strip=True)
      href = urljoin(sys.argv[2], anchor.get("href", ""))
      if title and href.startswith("http"):
        payload["links"].append({"title": title, "url": href})
  else:
    title = soup.select_one("meta[property='og:title']")
    published = soup.select_one("meta[property='article:published_time'], meta[name='article:published_time'], time[datetime]")
    payload["title"] = (title.get("content") if title else soup.title.get_text(" ", strip=True) if soup.title else None)
    payload["published_at"] = (published.get("content") or published.get("datetime")) if published else None
    payload["source"] = urlparse(sys.argv[2]).netloc
print(json.dumps(payload, ensure_ascii=False))
'''
    started = time.perf_counter()
    result = subprocess.run(
        [str(engine_python), "-c", program, str(engine_root), url, selector, "search" if selector == "#main_pack" else "article"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=90,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    if result.returncode != 0:
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": "engine_subprocess_failed"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": "engine_invalid_json"}
    payload["elapsed_ms"] = elapsed_ms
    return payload


def _published_before_cutoff(value: object, cutoff: datetime) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST) <= cutoff


def _article_title_matches_candidate(stock_name: object, title: object) -> bool:
    raw_name = str(stock_name or "").strip()
    raw_title = str(title or "").strip()
    normalized_name = re.sub(r"[^0-9a-z\uac00-\ud7a3]+", "", raw_name.casefold())
    if not normalized_name or not raw_title:
        return False
    if normalized_name.isascii() and len(normalized_name) <= 3:
        return re.search(
            rf"(?<![0-9A-Za-z\uac00-\ud7a3]){re.escape(raw_name)}(?!\s*[0-9A-Za-z\uac00-\ud7a3])",
            raw_title,
            flags=re.IGNORECASE,
        ) is not None
    normalized_title = re.sub(r"[^0-9a-z\uac00-\ud7a3]+", "", raw_title.casefold())
    return normalized_name in normalized_title


def _article_noise_reason(stock_name: object, title: object) -> str | None:
    from stock_monitor.cli import _news_search_lane_post_filter_v2_exclusion_reason

    return _news_search_lane_post_filter_v2_exclusion_reason(
        str(title or ""),
        stock_name=str(stock_name or ""),
    )


def _classify_lineage(title: str) -> tuple[str, str]:
    if any(marker in title for marker in ("리포트", "목표가", "투자의견", "애널리스트", "증권사")):
        return "report_recap", "report_recap_language_detected"
    return "unknown", "automatic_source_origin_unverified"


def _append(output: Path, payload: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _access_view(payload: dict[str, object]) -> dict[str, object]:
    return {key: payload.get(key) for key in ("ok", "verdict", "profile_used", "trace_count", "elapsed_ms", "error")}


def _replay_matches(first: dict[str, object], replay: dict[str, object]) -> bool:
    return all(first.get(key) == replay.get(key) for key in ("ok", "verdict", "title"))


def _candidate_manifest_row(rank: int, row: dict[str, object]) -> dict[str, object]:
    selected = row.get("selected") is True
    news_badge = row.get("news_observation_badge") or {}
    return {
        "rank": rank,
        "stock_code": row.get("stock_code"),
        "stock_name": row.get("stock_name"),
        "selected": selected,
        "selection_reason": "eligible_top2" if selected else "observation_pool_only",
        "sort_tuple": row.get("sort_tuple"),
        "observation_priority": row.get("observation_priority"),
        "why_notable": row.get("why_notable"),
        "missing_information": row.get("missing_information"),
        "evidence_direction": news_badge.get("evidence_direction") if isinstance(news_badge, dict) else None,
    }


def _shadow_status(candidates: list[dict[str, object]], search_attempts: list[dict[str, object]]) -> str:
    if not candidates:
        return "no_candidate_pool"
    if search_attempts and not any(attempt.get("ok") is True for attempt in search_attempts):
        return "search_failed"
    return "completed"


def _aggregate(output: Path) -> dict[str, object]:
    if not output.exists():
        return {"status": "aggregate_incomplete", "run_count": 0, "reason": "manifest_missing"}
    recorded_runs: list[dict[str, object]] = []
    for line in output.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("status") in {"completed", "no_candidate_pool"}:
            recorded_runs.append(row)
    runs = [run for run in recorded_runs if run.get("schema") == CURRENT_SCHEMA]
    pre_contract_runs = [run for run in recorded_runs if run.get("schema") != CURRENT_SCHEMA]
    baseline_articles = [
        article
        for run in runs
        for article in list((run.get("baseline") or {}).get("articles") or [])
        if isinstance(article, dict)
    ]
    articles = [
        article for run in runs for article in list(run.get("articles") or []) if isinstance(article, dict)
    ]
    filtered_exclusion_reasons = {
        "stock_identity_unverified_after_fetch",
        "market_noise",
        "parser_artifact",
        "false_positive",
    }
    raw_matched = [
        article
        for article in articles
        if article.get("point_in_time")
        and (
            article.get("status") == "matched"
            or article.get("exclusion_reason") in filtered_exclusion_reasons
        )
    ]
    identity_matched = [
        article
        for article in raw_matched
        if _article_title_matches_candidate(article.get("stock_name"), article.get("title"))
    ]
    matched = [
        article
        for article in identity_matched
        if _article_noise_reason(article.get("stock_name"), article.get("title")) is None
    ]
    rejected_by_identity = len(raw_matched) - len(identity_matched)
    rejected_as_noise = len(identity_matched) - len(matched)
    independent = [article for article in matched if article.get("classification") == "independent"]
    reviewed_independent = [
        article
        for article in independent
        if article.get("blind_review_classification") in {"independent", "report_recap", "unknown"}
    ]
    recaps_as_independent = [
        article for article in reviewed_independent if article.get("blind_review_classification") == "report_recap"
    ]
    replay_values = [article.get("replay_consistent") for article in articles if "replay_consistent" in article]
    article_access_attempts = [
        attempt
        for article in articles
        for attempt in list(article.get("access_attempts") or [])
        if isinstance(attempt, dict)
    ]
    search_attempts = [
        attempt
        for run in runs
        for attempt in list(run.get("search_attempts") or [])
        if isinstance(attempt, dict)
    ]
    access_attempts = [*search_attempts, *article_access_attempts]
    baseline_canonical = {str(article.get("canonical_url") or "") for article in baseline_articles if article.get("canonical_url")}
    discovered_canonical = {str(article.get("canonical_url") or "") for article in articles if article.get("canonical_url")}
    matched_canonical = {str(article.get("canonical_url") or "") for article in matched if article.get("canonical_url")}
    candidate_observations = [
        (str(run.get("business_date") or ""), str(candidate.get("stock_code") or ""))
        for run in runs
        for candidate in list(run.get("candidate_pool") or [])
        if isinstance(candidate, dict) and candidate.get("stock_code")
    ]
    return {
        "status": "aggregate_complete" if len(runs) >= 10 else "aggregate_incomplete",
        "expected_run_count": 10,
        "run_count": len(runs),
        "pre_contract_run_count": len(pre_contract_runs),
        "candidate_observation_count": len(candidate_observations),
        "candidate_count": len(set(candidate_observations)),
        "baseline_article_count_before_canonical_dedupe": len(baseline_articles),
        "baseline_article_count_after_canonical_dedupe": len(baseline_canonical),
        "insane_discovered_count_before_canonical_dedupe": len(articles),
        "insane_discovered_count_after_canonical_dedupe": len(discovered_canonical),
        "raw_point_in_time_additional_count": len(raw_matched),
        "point_in_time_additional_count": len(matched),
        "point_in_time_unique_canonical_count": len(matched_canonical),
        "stock_identity_filter_rejected_count": rejected_by_identity,
        "noise_filter_rejected_count": rejected_as_noise,
        "independent_additional_count": len(independent),
        "independent_precision": (
            None
            if not reviewed_independent
            else sum(article.get("blind_review_classification") == "independent" for article in reviewed_independent)
            / len(reviewed_independent)
        ),
        "independent_precision_reason": None if reviewed_independent else "blind_review_pending",
        "report_recap_promoted_to_independent": len(recaps_as_independent),
        "verified_missing_recovery_rate": None,
        "verified_missing_recovery_reason": "no blind verified-missing denominator is available from the manifest alone",
        "replay_consistency": None if not replay_values else sum(bool(value) for value in replay_values) / len(replay_values),
        "access_success_rate": None if not access_attempts else sum(bool(item.get("ok")) for item in access_attempts) / len(access_attempts),
        "trace_complete": bool(access_attempts) and all(item.get("trace_count") is not None for item in access_attempts),
        "production_side_effect_count": 0,
        "point_in_time_count": len(matched),
        "retrospective_search_count": sum(1 for article in articles if not article.get("point_in_time")),
        "recommendation": "CONDITIONAL",
    }


def main() -> int:
    args = _parse_args()
    if args.aggregate:
        return _emit(_aggregate(args.output))
    cutoff = _cutoff(args.cutoff)

    from stock_monitor.business_day import is_business_day
    from stock_monitor.config import RuntimeConfig

    config = RuntimeConfig.from_env(root_dir=PROJECT_ROOT)
    if not is_business_day(cutoff.date(), config.holiday_overrides):
        return _emit({
            "status": "skipped_non_business_day",
            "cutoff": cutoff.isoformat(),
            "writes_production_db": False,
        })
    if (cutoff.hour, cutoff.minute) not in {(12, 0), (15, 0)}:
        return _emit({
            "status": "skipped_outside_shadow_slots",
            "cutoff": cutoff.isoformat(),
            "writes_production_db": False,
        })
    if not args.db_path.exists():
        return _emit({"status": "blocked_missing_database", "cutoff": cutoff.isoformat(), "writes_production_db": False})
    if not args.engine_python or not args.engine_root or not args.engine_python.exists() or not args.engine_root.exists():
        return _emit({"status": "blocked_missing_insane_search_runtime", "cutoff": cutoff.isoformat(), "writes_production_db": False})

    from stock_monitor.cli import build_web_view_candidate_evidence_snapshot
    from stock_monitor.db.repository import StockMonitorRepository
    from stock_monitor.news.linked_evidence import canonicalize_news_url

    with tempfile.TemporaryDirectory(prefix="stock-monitor-insane-shadow-") as temp_dir:
        clone_path = Path(temp_dir) / "snapshot.db"
        _copy_database_read_only(args.db_path, clone_path)
        clone_config = replace(config, db_path=clone_path)
        repository = StockMonitorRepository(clone_path, timezone=config.timezone)
        repository.initialize()  # Temporary clone only; never the production source.
        snapshot = build_web_view_candidate_evidence_snapshot(
            clone_config,
            repository,
            business_date=cutoff.date(),
            limit=max(1, args.candidate_limit),
            now=cutoff,
            include_internal=True,
        )
        rows = list(snapshot.get("rows") or [])
        candidates = [_candidate_manifest_row(rank, row) for rank, row in enumerate(rows, start=1)]
        baseline_by_code: dict[str, set[str]] = {}
        baseline_articles: list[dict[str, object]] = []
        for candidate in candidates:
            code = str(candidate.get("stock_code") or "")
            baseline_by_code[code] = set()
            for item in repository.list_report_linked_news_evidence(
                target_date=cutoff.date(), stock_code=code, limit=500
            ):
                if item.created_at.astimezone(KST) > cutoff or item.published_at.astimezone(KST) > cutoff:
                    continue
                canonical = canonicalize_news_url(item.canonical_url or item.url)
                baseline_by_code[code].add(canonical)
                baseline_articles.append(
                    {
                        "stock_code": code,
                        "stock_name": item.stock_name,
                        "title": item.title,
                        "url": item.url,
                        "canonical_url": canonical,
                        "source": item.source,
                        "published_at": item.published_at.isoformat(),
                        "search_lane": item.source_lane,
                        "query": None,
                        "classification": item.lineage_type or "unknown",
                        "classification_reason": item.lineage_reason or "legacy_row_unverified",
                        "point_in_time": True,
                        "status": "baseline",
                        "exclusion_reason": None,
                    }
                )

        articles: list[dict[str, object]] = []
        search_attempts: list[dict[str, object]] = []
        for candidate in candidates[: max(0, args.search_top_n)]:
            stock_name = str(candidate.get("stock_name") or "").strip()
            stock_code = str(candidate.get("stock_code") or "").strip()
            if not stock_name or not stock_code:
                continue
            day = cutoff.strftime("%Y.%m.%d")
            search_url = f"https://search.naver.com/search.naver?where=news&query={stock_name}&sm=tab_opt&sort=1&pd=3&ds={day}&de={day}"
            search = _engine_fetch(engine_python=args.engine_python, engine_root=args.engine_root, url=search_url, selector="#main_pack")
            search_attempts.append(
                {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "query": stock_name,
                    "search_lane": "naver_news_search",
                    "link_count": len(list(search.get("links") or [])),
                    **_access_view(search),
                }
            )
            seen: set[str] = set()
            matches = 0
            for link in list(search.get("links") or []):
                if not isinstance(link, dict):
                    continue
                title = str(link.get("title") or "").strip()
                url = str(link.get("url") or "").strip()
                canonical = canonicalize_news_url(url)
                if not title or not canonical or stock_name not in title:
                    continue
                if canonical in seen:
                    continue
                seen.add(canonical)
                matches += 1
                if matches > max(0, args.article_limit):
                    articles.append({"stock_code": stock_code, "stock_name": stock_name, "title": title, "url": url, "canonical_url": canonical, "source": urlparse(url).netloc, "search_lane": "naver_news_search", "query": stock_name, "status": "excluded", "exclusion_reason": "article_limit", "point_in_time": False})
                    continue
                article = _engine_fetch(engine_python=args.engine_python, engine_root=args.engine_root, url=url, selector="article")
                replay = _engine_fetch(engine_python=args.engine_python, engine_root=args.engine_root, url=url, selector="article")
                effective_title = str(article.get("title") or title).strip()
                lineage_type, lineage_reason = _classify_lineage(effective_title)
                point_in_time = bool(article.get("ok")) and _published_before_cutoff(article.get("published_at"), cutoff)
                exclusion_reason = None
                status = "matched"
                if canonical in baseline_by_code.get(stock_code, set()):
                    status, exclusion_reason = "excluded", "canonical_duplicate_of_baseline"
                elif not article.get("ok"):
                    status, exclusion_reason = "excluded", "article_access_failed"
                elif not _replay_matches(article, replay):
                    status, exclusion_reason = "excluded", "replay_inconsistent"
                elif not point_in_time:
                    status, exclusion_reason = "excluded", "published_at_unverified_for_cutoff"
                elif not _article_title_matches_candidate(stock_name, effective_title):
                    status, exclusion_reason = "excluded", "stock_identity_unverified_after_fetch"
                elif noise_reason := _article_noise_reason(stock_name, effective_title):
                    status, exclusion_reason = "excluded", noise_reason
                articles.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "title": effective_title,
                    "url": url,
                    "canonical_url": canonical,
                    "source": article.get("source") or urlparse(url).netloc,
                    "published_at": article.get("published_at"),
                    "search_lane": "naver_news_search",
                    "query": stock_name,
                    "classification": lineage_type,
                    "classification_reason": lineage_reason,
                    "blind_review_classification": None,
                    "blind_review_status": "pending",
                    "point_in_time": point_in_time,
                    "access_attempts": [_access_view(article), _access_view(replay)],
                    "replay_consistent": _replay_matches(article, replay),
                    "status": status,
                    "exclusion_reason": exclusion_reason,
                })

        payload: dict[str, object] = {
            "schema": CURRENT_SCHEMA,
            "execution_id": f"{cutoff:%Y%m%dT%H%M%S%z}",
            "cutoff": cutoff.isoformat(),
            "business_date": cutoff.date().isoformat(),
            "status": _shadow_status(candidates, search_attempts),
            "candidate_pool": candidates,
            "searched_candidate_count": min(len(candidates), max(0, args.search_top_n)),
            "search_attempts": search_attempts,
            "baseline": {"source": "stored_report_linked_news_evidence", "read_only": True, "articles": baseline_articles},
            "articles": articles,
            "production_effects": {"writes_db": False, "registers_scheduler": False, "sends_telegram": False, "connects_web_view": False, "changes_candidate_ordering": False},
        }
    _append(args.output, payload)
    _emit({"status": payload["status"], "cutoff": payload["cutoff"], "manifest": str(args.output), "writes_production_db": False})
    return 1 if payload["status"] == "search_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
