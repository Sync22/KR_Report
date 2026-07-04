from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import json


@dataclass(frozen=True)
class WebViewCheckRuntime:
    render_web_view_html: Callable[[], str]
    build_web_view_archive_snapshot: Callable[..., dict[str, Any]]
    build_web_view_market_snapshot: Callable[..., dict[str, Any]]
    collect_rotation_alias_mapping_qa_issues: Callable[..., None]
    collect_rotation_etf_mapping_qa_issues: Callable[..., None]
    build_web_view_daily_snapshot: Callable[..., dict[str, Any]]
    build_web_view_candidate_evidence_snapshot: Callable[..., dict[str, Any]]
    build_web_view_backtest_observation_snapshot: Callable[..., dict[str, Any]]
    build_web_view_intraday_snapshot: Callable[..., dict[str, Any]]
    build_web_view_category_detail_snapshot: Callable[..., dict[str, Any]]
    build_web_view_category_trend_snapshot: Callable[..., dict[str, Any]]
    build_web_view_flow_trend_snapshot: Callable[..., dict[str, Any]]
    build_web_view_etf_trend_snapshot: Callable[..., dict[str, Any]]
    build_web_view_rotation_overlay_snapshot: Callable[..., dict[str, Any]]
    build_web_view_stock_detail_snapshot: Callable[..., dict[str, Any]]
    create_web_view_server: Callable[..., Any]


def forbidden_public_json_keys(body: bytes) -> list[str]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return []
    forbidden = {
        "admin_audit_log",
        "db_path",
        "env_run_suppressed_dates",
        "health",
        "internal_candidate_signals",
        "internal_missing_information",
        "operator_controls",
        "operation_profile",
        "quality_flags",
        "recent_admin_audit_logs",
        "safe_settings",
        "scheduler_tasks",
        "worker_states",
        "_internal_candidate_signals",
        "_internal_missing_information",
        "_sort_density",
        "_sort_signal",
        "five_business_day_broker_count",
        "previous_broker_count",
    }
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key) in forbidden:
                    found.add(str(key))
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return sorted(found)
