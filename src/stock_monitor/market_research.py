from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
SLOT_GRACE = timedelta(minutes=15)


def build_market_research_note(
    snapshot: dict[str, object],
    market_flow: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = _require_mapping(snapshot, "metadata")
    return {
        "surface": "market-research-note",
        "operator_only": True,
        "public_safe": False,
        "live_fetch": False,
        "writes_db": False,
        "sends_telegram": False,
        "registers_scheduler": False,
        "connects_web_view": False,
        "snapshot": _snapshot_context(metadata),
        "candidate_evidence": {"top2": _mapping_list(snapshot.get("top2"))},
        "market_context": _market_context(market_flow),
    }


def format_market_research_note_markdown(note: dict[str, object]) -> str:
    snapshot = _require_mapping(note, "snapshot")
    candidate_evidence = _require_mapping(note, "candidate_evidence")
    market_context = _require_mapping(note, "market_context")
    top2 = _mapping_list(candidate_evidence.get("top2"))
    lines = ["# Operator Market Research Note", "", "## Snapshot slot"]
    lines.extend(
        [
            f"- date: {snapshot.get('date')}",
            f"- target_time_kst: {snapshot.get('snapshot_time_kst')}",
            f"- generated_at_kst: {snapshot.get('generated_at_kst')}",
            f"- slot_status: {snapshot.get('slot_status')}",
            f"- slot_reason: {snapshot.get('slot_reason') or 'none'}",
            "",
            "## Candidate evidence",
        ]
    )
    if top2:
        lines.extend(
            f"- {item.get('rank') or '-'}: {item.get('stock_name') or 'unknown'} ({item.get('stock_code') or 'unknown'})"
            for item in top2
        )
    else:
        lines.append("- not supplied")
    lines.extend(["", "## Market context", f"- status: {market_context.get('status')}"])
    for source_url in market_context.get("source_urls", []):
        lines.append(f"- source: {source_url}")
    lines.append(f"- summary: {market_context.get('summary') or 'not supplied'}")
    if market_context.get("error"):
        lines.append(f"- error: {market_context['error']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "- operator_only: true",
            "- live_fetch: false",
            "- writes_db: false",
            "- sends_telegram: false",
            "- registers_scheduler: false",
            "- connects_web_view: false",
        ]
    )
    return "\n".join(lines) + "\n"


def _snapshot_context(metadata: dict[str, object]) -> dict[str, object]:
    try:
        target_date = date.fromisoformat(str(metadata["date"]))
        target_time = time.fromisoformat(str(metadata["snapshot_time_kst"]))
        generated_at = datetime.fromisoformat(str(metadata["generated_at_kst"])).astimezone(KST)
    except (KeyError, TypeError, ValueError):
        return {
            "date": metadata.get("date"),
            "snapshot_time_kst": metadata.get("snapshot_time_kst"),
            "generated_at_kst": metadata.get("generated_at_kst"),
            "slot_status": "invalid_for_slot",
            "slot_reason": "invalid_metadata",
        }

    deadline = datetime.combine(target_date, target_time, tzinfo=KST) + SLOT_GRACE
    if generated_at.date() != target_date:
        status, reason = "invalid_for_slot", "date_mismatch"
    elif generated_at > deadline:
        status, reason = "invalid_for_slot", "late_generation"
    else:
        status, reason = "valid", None
    return {
        "date": target_date.isoformat(),
        "snapshot_time_kst": target_time.strftime("%H:%M"),
        "generated_at_kst": generated_at.isoformat(),
        "slot_status": status,
        "slot_reason": reason,
    }


def _market_context(market_flow: dict[str, object] | None) -> dict[str, object]:
    if market_flow is None:
        return {"status": "not_supplied", "source_urls": [], "summary": None}
    if market_flow.get("surface") != "news-flow-source-probe" or market_flow.get("operator_only") is not True:
        raise ValueError("market flow must be an operator-only news-flow source probe")
    if market_flow.get("error"):
        return {
            "status": "unavailable",
            "source_urls": [str(item) for item in market_flow.get("source_urls", []) if str(item).strip()],
            "summary": None,
            "error": str(market_flow["error"]),
        }
    return {
        "status": "available",
        "source_urls": [str(item) for item in market_flow.get("source_urls", []) if str(item).strip()],
        "summary": market_flow.get("market_mood"),
        "sector_themes": _mapping_list(market_flow.get("sector_themes")),
        "key_issues": _mapping_list(market_flow.get("key_issues")),
        "caution_signals": _mapping_list(market_flow.get("caution_signals")),
        "warnings": [str(item) for item in market_flow.get("warnings", []) if str(item).strip()],
    }


def _require_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
