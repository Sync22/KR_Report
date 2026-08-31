from __future__ import annotations

from dataclasses import replace
import html
from http import HTTPStatus
import json
import math
import re
import secrets
import threading
from datetime import date, datetime, timedelta
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request
from zoneinfo import ZoneInfo

from stock_monitor.business_day import is_business_day
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.web_view_runtime import WebViewCheckRuntime, forbidden_public_json_keys

def _build_web_view_value_qa_payload(
    config: RuntimeConfig,
    repository: StockMonitorRepository,
    *,
    dates: tuple[date, ...],
    stock_limit: int,
    runtime: WebViewCheckRuntime,
) -> dict[str, object]:
    issues: list[dict] = []
    warnings: list[dict] = []
    _collect_web_view_static_html_copy_issues(runtime.render_web_view_html(), issues=issues)
    archive = runtime.build_web_view_archive_snapshot(config, repository, limit=max(1, stock_limit))
    _collect_web_view_value_qa_issues(archive, path="archive", issues=issues, warnings=warnings)
    market = runtime.build_web_view_market_snapshot(config, repository)
    _collect_web_view_value_qa_issues(market, path="market", issues=issues, warnings=warnings)
    latest_toss_snapshot_date = repository.latest_toss_market_snapshot_date()
    runtime.collect_rotation_alias_mapping_qa_issues(
        config,
        issues=issues,
    )
    runtime.collect_rotation_etf_mapping_qa_issues(
        config,
        repository,
        snapshot_date=latest_toss_snapshot_date,
        source="toss_openapi",
        issues=issues,
        warnings=warnings,
    )
    for business_date in dates:
        toss_snapshot_not_yet_available = latest_toss_snapshot_date is not None and business_date > latest_toss_snapshot_date
        if toss_snapshot_not_yet_available:
            warnings.append(
                {
                    "code": "toss_close_snapshot_not_yet_available",
                    "path": f"daily[{business_date.isoformat()}].market_reference",
                    "message": (
                        f"selected date is newer than latest stored Toss close snapshot "
                        f"{latest_toss_snapshot_date.isoformat()}; the 20:00 capture has not completed for this date"
                    ),
                }
            )
        daily = runtime.build_web_view_daily_snapshot(config, repository, business_date=business_date)
        _collect_web_view_value_qa_issues(daily, path=f"daily[{business_date.isoformat()}]", issues=issues, warnings=warnings)
        candidate_evidence = runtime.build_web_view_candidate_evidence_snapshot(
            config,
            repository,
            business_date=business_date,
            limit=max(1, stock_limit),
        )
        _collect_web_view_value_qa_issues(
            candidate_evidence,
            path=f"candidate_evidence[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        priority_stock_codes = {
            str(row.get("stock_code") or "")
            for row in list(candidate_evidence.get("rows") or [])[:2]
            if isinstance(row, dict) and row.get("stock_code")
        }
        backtest_observation = runtime.build_web_view_backtest_observation_snapshot(
            config,
            repository,
            business_date=business_date,
            limit=max(1, stock_limit),
        )
        _collect_web_view_value_qa_issues(
            backtest_observation,
            path=f"backtest_observation[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        intraday = runtime.build_web_view_intraday_snapshot(config, repository, business_date=business_date)
        _collect_web_view_value_qa_issues(
            intraday,
            path=f"intraday[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        for category in _web_view_value_qa_category_targets(daily, limit=max(1, stock_limit)):
            category_type = category["category_type"]
            display_name = category["display_name"]
            category_detail = runtime.build_web_view_category_detail_snapshot(
                config,
                repository,
                business_date=business_date,
                category_type=category_type,
                category_name=category.get("category_name") or display_name,
                category_display_name=display_name,
            )
            _collect_web_view_value_qa_issues(
                category_detail,
                path=f"category[{business_date.isoformat()}:{category_type}:{display_name}]",
                issues=issues,
                warnings=warnings,
            )
            category_trend = runtime.build_web_view_category_trend_snapshot(
                config,
                repository,
                category_type=category_type,
                category_name=category.get("category_name") or display_name,
                category_display_name=display_name,
                limit=max(1, stock_limit),
            )
            _collect_web_view_value_qa_issues(
                category_trend,
                path=f"category_trend[{category_type}:{display_name}]",
                issues=issues,
                warnings=warnings,
            )
        flow_trend = runtime.build_web_view_flow_trend_snapshot(config, repository, business_date=business_date, limit=max(1, stock_limit))
        _collect_web_view_value_qa_issues(
            flow_trend,
            path=f"flow_trend[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        etf_trend = runtime.build_web_view_etf_trend_snapshot(config, repository, business_date=business_date, limit=max(1, stock_limit))
        _collect_web_view_value_qa_issues(
            etf_trend,
            path=f"etf_trend[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        rotation_overlay = runtime.build_web_view_rotation_overlay_snapshot(config, repository, business_date=business_date)
        _collect_web_view_value_qa_issues(
            rotation_overlay,
            path=f"rotation_overlay[{business_date.isoformat()}]",
            issues=issues,
            warnings=warnings,
        )
        stocks = daily.get("stocks", [])
        if daily.get("report_count", 0) and not stocks:
            warnings.append(
                {
                    "code": "missing_stock_rows",
                    "path": f"daily[{business_date.isoformat()}].stocks",
                    "message": "report_count exists but stock summary rows are empty",
                }
            )
        for stock in stocks[: max(0, stock_limit)]:
            stock_code = stock.get("stock_code")
            if not stock_code:
                warnings.append(
                    {
                        "code": "missing_stock_code",
                        "path": f"daily[{business_date.isoformat()}].stocks",
                        "message": f"stock without code: {stock.get('stock_name') or '-'}",
                    }
                )
                continue
            detail = runtime.build_web_view_stock_detail_snapshot(
                config,
                repository,
                business_date=business_date,
                stock_code=str(stock_code),
            )
            _collect_web_view_value_qa_issues(
                detail,
                path=f"stock[{business_date.isoformat()}:{stock_code}]",
                issues=issues,
                warnings=warnings,
            )
            if (
                str(stock_code) in priority_stock_codes
                and detail.get("market_reference") is None
                and not toss_snapshot_not_yet_available
            ):
                issues.append(
                    {
                        "code": "missing_market_reference",
                        "path": f"stock[{business_date.isoformat()}:{stock_code}].market_reference",
                        "message": "selected stock has no same-date Toss market reference",
                    }
                )

    payload = {
        "surface": "web-view-value-qa",
        "read_only": True,
        "dates": [item.isoformat() for item in dates],
        "stock_limit": stock_limit,
        "scanned_surfaces": [
            "static_html",
            "archive",
            "market",
            "rotation_alias_mapping",
            "rotation_etf_mapping",
            "daily",
            "candidate_evidence",
            "backtest_observation",
            "intraday",
            "category",
            "category_trend",
            "flow_trend",
            "etf_trend",
            "rotation_overlay",
            "stock_detail",
        ],
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
    }
    return payload

def _run_web_view_value_qa(
    config: RuntimeConfig,
    repository: StockMonitorRepository,
    *,
    dates: tuple[date, ...],
    stock_limit: int,
    as_json: bool,
    runtime: WebViewCheckRuntime,
) -> int:
    payload = _build_web_view_value_qa_payload(
        config,
        repository,
        dates=dates,
        stock_limit=stock_limit,
        runtime=runtime,
    )
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if payload["issue_count"] else 0

    print("Web-view value QA")
    print(f"- dates: {', '.join(payload['dates'])}")
    print(f"- scanned surfaces: {', '.join(payload['scanned_surfaces'])}")
    print(f"- issues: {payload['issue_count']}")
    print(f"- warnings: {payload['warning_count']}")
    for issue in payload["issues"]:
        print(f"- issue | {issue['code']} | {issue['path']} | {issue['message']}")
    for warning in payload["warnings"]:
        print(f"- warning | {warning['code']} | {warning['path']} | {warning['message']}")
    return 1 if payload["issue_count"] else 0

def _run_web_view_browser_smoke(
    config: RuntimeConfig,
    repository: StockMonitorRepository,
    *,
    business_date: date | None,
    stock_limit: int,
    respect_access_code: bool,
    as_json: bool,
    runtime: WebViewCheckRuntime,
) -> int:
    if stock_limit < 1:
        raise ValueError("--stock-limit must be at least 1.")
    resolved_date = business_date or _resolve_web_view_browser_smoke_date(repository)
    payload = _probe_web_view_browser_smoke(
        config,
        repository,
        business_date=resolved_date,
        stock_limit=stock_limit,
        respect_access_code=respect_access_code,
        runtime=runtime,
    )
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if payload["issue_count"] else 0

    print("Web-view browser smoke")
    print(f"- read-only: {payload['read_only']}")
    print(f"- host: {payload['host']}")
    print(f"- business date: {payload['business_date']}")
    print(f"- stock limit: {payload['stock_limit']}")
    print(f"- access code mode: {payload['access_code_mode']}")
    print(f"- viewports: {len(payload['viewports'])}")
    print(f"- api checks: {len(payload['api_checks'])}")
    print(f"- issues: {payload['issue_count']}")
    for viewport in payload["viewports"]:
        tab_order = "/".join(viewport.get("tab_order") or [])
        panel_state = (
            f"watch={viewport.get('watch_panel_clickable')} "
            f"stock_waiting_for_selection={viewport.get('stock_panel_hidden_before_selection')} "
            f"market={viewport.get('market_panel_clickable')} "
            f"rotation={viewport.get('rotation_panel_clickable')}"
        )
        print(
            f"- viewport | {viewport['name']} | {viewport['width']}x{viewport['height']} | "
            f"tabs={viewport['tab_count']} | order={tab_order} | panels={panel_state} | "
            f"overflow={viewport['horizontal_overflow_px']}px"
        )
    for check in payload["api_checks"]:
        print(f"- api | {check['path']} | {check['method']} | {check['status']}")
    for issue in payload["issues"]:
        print(f"- issue | {issue['code']} | {issue['path']} | {issue['message']}")
    return 1 if payload["issue_count"] else 0

def _resolve_web_view_browser_smoke_date(repository: StockMonitorRepository) -> date:
    summary_dates = repository.count_summaries_by_business_date(limit=1)
    if summary_dates:
        return summary_dates[0][0]
    raise ValueError("No daily summary date is available for web-view-browser-smoke. Pass --date explicitly.")

def _probe_web_view_browser_smoke(
    config: RuntimeConfig,
    repository: StockMonitorRepository,
    *,
    business_date: date,
    stock_limit: int,
    respect_access_code: bool,
    runtime: WebViewCheckRuntime,
) -> dict[str, object]:
    smoke_config = config
    access_code_mode = "configured"
    if not respect_access_code:
        access_code_mode = "temporary_disabled_for_local_smoke"
        smoke_config = replace(
            config,
            access_code_path=config.data_dir / f".web_view_browser_smoke_{secrets.token_hex(8)}.json",
        )

    issues: list[dict[str, object]] = []
    viewports: list[dict[str, object]] = []
    api_checks: list[dict[str, object]] = []
    server = runtime.create_web_view_server(
        smoke_config,
        repository,
        host="127.0.0.1",
        port=0,
        limit=stock_limit,
        allow_non_loopback=False,
    )
    base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _collect_web_view_browser_api_smoke_issues(
            base_url,
            business_date=business_date,
            stock_limit=stock_limit,
            issues=issues,
            api_checks=api_checks,
        )
        _collect_web_view_browser_render_smoke_issues(
            config,
            base_url=base_url,
            business_date=business_date,
            issues=issues,
            viewports=viewports,
        )
    finally:
        server.shutdown()
        server.server_close()

    return {
        "surface": "web-view-browser-smoke",
        "read_only": True,
        "sends_telegram": False,
        "registers_scheduler": False,
        "host": "127.0.0.1",
        "business_date": business_date.isoformat(),
        "stock_limit": stock_limit,
        "access_code_mode": access_code_mode,
        "issue_count": len(issues),
        "issues": issues,
        "viewports": viewports,
        "api_checks": api_checks,
    }

def _collect_web_view_browser_api_smoke_issues(
    base_url: str,
    *,
    business_date: date,
    stock_limit: int,
    issues: list[dict[str, object]],
    api_checks: list[dict[str, object]],
) -> None:
    daily_path = f"/api/daily/{business_date.isoformat()}"
    daily_status, daily_body, daily_content_type = _web_view_smoke_http_request(f"{base_url}{daily_path}")
    api_checks.append({"path": daily_path, "method": "GET", "status": daily_status})
    daily_payload: dict[str, object] | None = None
    if daily_status != HTTPStatus.OK:
        issues.append(
            {
                "code": "daily_api_unavailable",
                "path": daily_path,
                "message": f"GET daily API returned {daily_status}",
            }
        )
    elif "application/json" not in daily_content_type:
        issues.append(
            {
                "code": "daily_api_not_json",
                "path": daily_path,
                "message": f"GET daily API returned content-type {daily_content_type or '-'}",
            }
        )
    else:
        try:
            daily_payload = json.loads(daily_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                {
                    "code": "daily_api_invalid_json",
                    "path": daily_path,
                    "message": str(exc),
                }
            )
        if daily_payload is not None and "business_date" not in daily_payload:
            issues.append(
                {
                    "code": "daily_api_missing_business_date",
                    "path": daily_path,
                    "message": "daily API response does not include business_date",
                }
            )

    live_daily_path = (
        f"/api/daily/{business_date.isoformat()}"
        "?intraday_market_top=1&market_top_limit=100&market_top_page_size=20"
    )
    live_daily_status, live_daily_body, live_daily_content_type = _web_view_smoke_http_request(
        f"{base_url}{live_daily_path}"
    )
    api_checks.append({"path": "/api/daily/{date}?intraday_market_top=1", "method": "GET", "status": live_daily_status})
    if live_daily_status != HTTPStatus.OK:
        issues.append(
            {
                "code": "daily_intraday_market_top_api_unavailable",
                "path": live_daily_path,
                "message": f"GET live daily API returned {live_daily_status}",
            }
        )
    elif "application/json" not in live_daily_content_type:
        issues.append(
            {
                "code": "daily_intraday_market_top_api_not_json",
                "path": live_daily_path,
                "message": f"GET live daily API returned content-type {live_daily_content_type or '-'}",
            }
        )
    else:
        forbidden_keys = forbidden_public_json_keys(live_daily_body)
        if forbidden_keys:
            issues.append(
                {
                    "code": "daily_intraday_market_top_json_exposes_operator_keys",
                    "path": live_daily_path,
                    "message": f"GET live daily API exposes operator/admin keys: {', '.join(forbidden_keys)}.",
                }
            )
        try:
            live_daily_payload = json.loads(live_daily_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                {
                    "code": "daily_intraday_market_top_api_invalid_json",
                    "path": live_daily_path,
                    "message": str(exc),
                }
            )
        else:
            commentary = live_daily_payload.get("market_commentary")
            reference = commentary.get("intraday_market_top_reference") if isinstance(commentary, dict) else None
            same_day_status = commentary.get("same_day_report_status") if isinstance(commentary, dict) else None
            can_overlap = not isinstance(same_day_status, dict) or same_day_status.get("can_overlap_intraday_market_top") is not False
            if can_overlap and (not isinstance(reference, dict) or reference.get("live_fetch") is not True):
                issues.append(
                    {
                        "code": "daily_intraday_market_top_not_live",
                        "path": live_daily_path,
                        "message": "live daily API did not mark intraday_market_top_reference.live_fetch=true.",
                    }
                )
            if isinstance(reference, dict) and reference.get("writes_snapshot_tables") is not False:
                issues.append(
                    {
                        "code": "daily_intraday_market_top_write_boundary",
                        "path": live_daily_path,
                        "message": "live daily API must not write snapshot tables.",
                    }
                )

    candidate_path = f"/api/candidate-evidence?date={business_date.isoformat()}&limit={max(1, min(stock_limit, 20))}"
    candidate_status, candidate_body, candidate_content_type = _web_view_smoke_http_request(f"{base_url}{candidate_path}")
    api_checks.append({"path": "/api/candidate-evidence", "method": "GET", "status": candidate_status})
    if candidate_status != HTTPStatus.OK or "application/json" not in candidate_content_type:
        issues.append(
            {
                "code": "candidate_api_unavailable",
                "path": candidate_path,
                "message": f"candidate evidence API returned {candidate_status} / {candidate_content_type or '-'}",
            }
        )
    else:
        try:
            json.loads(candidate_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                {
                    "code": "candidate_api_invalid_json",
                    "path": candidate_path,
                    "message": str(exc),
                }
            )
        forbidden_keys = forbidden_public_json_keys(candidate_body)
        if forbidden_keys:
            issues.append(
                {
                    "code": "candidate_json_exposes_operator_keys",
                    "path": candidate_path,
                    "message": f"candidate evidence JSON exposed forbidden keys: {', '.join(forbidden_keys)}",
                }
            )

    first_stock_code = ""
    if daily_payload is not None:
        stocks = daily_payload.get("stocks")
        if isinstance(stocks, list):
            first_stock = next((item for item in stocks if isinstance(item, dict) and item.get("stock_code")), None)
            if first_stock:
                first_stock_code = str(first_stock["stock_code"])
    if first_stock_code:
        stock_path = f"/api/daily/{business_date.isoformat()}/stocks/{url_parse.quote(first_stock_code)}"
        stock_status, stock_body, stock_content_type = _web_view_smoke_http_request(f"{base_url}{stock_path}")
        api_checks.append({"path": "/api/daily/{date}/stocks/{stock_code}", "method": "GET", "status": stock_status})
        if stock_status != HTTPStatus.OK or "application/json" not in stock_content_type:
            issues.append(
                {
                    "code": "stock_detail_api_unavailable",
                    "path": stock_path,
                    "message": f"stock detail API returned {stock_status} / {stock_content_type or '-'}",
                }
            )
        else:
            try:
                json.loads(stock_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                issues.append(
                    {
                        "code": "stock_detail_api_invalid_json",
                        "path": stock_path,
                        "message": str(exc),
                    }
                )

    post_status, _post_body, _post_content_type = _web_view_smoke_http_request(
        f"{base_url}{daily_path}",
        method="POST",
        data=b"{}",
    )
    api_checks.append({"path": daily_path, "method": "POST", "status": post_status})
    if post_status != HTTPStatus.METHOD_NOT_ALLOWED:
        issues.append(
            {
                "code": "write_method_not_blocked",
                "path": daily_path,
                "message": f"POST daily API returned {post_status}, expected 405",
            }
        )

    admin_status, _admin_body, _admin_content_type = _web_view_smoke_http_request(f"{base_url}/api/status")
    api_checks.append({"path": "/api/status", "method": "GET", "status": admin_status})
    if admin_status != HTTPStatus.NOT_FOUND:
        issues.append(
            {
                "code": "admin_status_exposed",
                "path": "/api/status",
                "message": f"web-view /api/status returned {admin_status}, expected 404",
            }
        )

def _collect_web_view_browser_render_smoke_issues(
    config: RuntimeConfig,
    *,
    base_url: str,
    business_date: date,
    issues: list[dict[str, object]],
    viewports: list[dict[str, object]],
) -> None:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - exercised only when Playwright is missing locally.
        issues.append(
            {
                "code": "playwright_unavailable",
                "path": "web-view-browser-smoke",
                "message": f"Playwright is not importable: {exc}",
            }
        )
        return

    timeout_ms = max(1_000, min(config.browser_timeout_ms, 15_000))
    viewport_specs = (
        {"name": "desktop", "width": 1366, "height": 900},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "large_mobile", "width": 430, "height": 932},
        {"name": "mobile", "width": 390, "height": 844},
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                preview_context = browser.new_context(viewport={"width": 1366, "height": 900})
                try:
                    preview_page = preview_context.new_page()
                    preview_page.goto(
                        f"{base_url}/v2?date={business_date.isoformat()}",
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                    preview_page.wait_for_selector("#v2-candidate-list", timeout=timeout_ms)
                    preview_page.wait_for_function(
                        """
                        () => document.querySelector('#v2-candidate-list')?.dataset.loaded === 'true'
                        """,
                        timeout=timeout_ms,
                    )
                    v2_runtime_error = "불러오기 오류:" in preview_page.locator("#v2-candidate-list").inner_text(
                        timeout=timeout_ms
                    )
                    if v2_runtime_error:
                        issues.append(
                            {
                                "code": "v2_preview_runtime_error",
                                "path": "/v2",
                                "message": "web-view v2 candidate layer reported a runtime error",
                            }
                        )
                finally:
                    preview_context.close()
                for spec in viewport_specs:
                    context = browser.new_context(viewport={"width": spec["width"], "height": spec["height"]})
                    page = context.new_page()
                    try:
                        page.goto(
                            f"{base_url}/?date={business_date.isoformat()}",
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        page.wait_for_selector("#calendar-open", timeout=timeout_ms)
                        page.locator("#calendar-open").click(timeout=timeout_ms)
                        page.wait_for_selector("#archive-calendar", timeout=timeout_ms)
                        calendar_dialog_open = bool(
                            page.locator("#archive-calendar-dialog").evaluate("(node) => node.open")
                        )
                        page.locator("#calendar-close").click(timeout=timeout_ms)
                        page.wait_for_function(
                            "expected => document.querySelector('#main-priority-date')?.textContent?.includes(expected)",
                            arg=business_date.isoformat(),
                            timeout=timeout_ms,
                        )
                        body_text = page.locator("body").inner_text(timeout=timeout_ms)
                        rendered_business_date = (
                            page.locator("#main-priority-date").inner_text(timeout=timeout_ms).strip().strip("()")
                        )
                        view_tab_locator = page.locator("[data-view-tab]")
                        tab_count = view_tab_locator.count()
                        tab_order = view_tab_locator.evaluate_all(
                            "(nodes) => nodes.map((node) => node.getAttribute('data-view-tab'))"
                        )
                        current_tab_count = page.locator('[data-view-tab][aria-current="page"]').count()
                        search_count = page.locator("#stock-search-input").count()
                        intraday_button_visible = page.locator("#intraday-market-top-check").is_visible()
                        intraday_overlap_count = page.locator("#intraday-market-top-overlap").count()
                        candidate_count = page.locator("#main-priority-rows").count()
                        horizontal_overflow_px = int(
                            page.evaluate(
                                """
                                () => Math.max(
                                  0,
                                  Math.max(
                                    document.documentElement.scrollWidth,
                                    document.body ? document.body.scrollWidth : 0
                                  ) - document.documentElement.clientWidth
                                )
                                """
                            )
                        )
                        candidate_panel_visible = page.locator("#main-priority-rows").is_visible()
                        intraday_overlap_initial_visible = page.locator("#intraday-market-top-overlap").is_visible()
                        page.locator('[data-view-tab="watch"]').click(timeout=timeout_ms)
                        page.wait_for_function(
                            """
                            () => {
                              const panel = document.querySelector('#candidate-evidence-rows');
                              if (!panel) return false;
                              return Boolean(panel.querySelector('.watch-candidate-row'))
                                || panel.textContent.includes('데이터가 없습니다');
                            }
                            """,
                            timeout=timeout_ms,
                        )
                        watch_panel_visible = page.locator("#candidate-evidence-card").is_visible()
                        watch_candidate_selector_visible = page.locator("#candidate-evidence-rows .watch-candidate-row").count() > 0
                        watch_tab_current = page.locator('[data-view-tab="watch"]').get_attribute("aria-current") == "page"
                        page.locator('[data-view-tab="stock"]').click(timeout=timeout_ms)
                        page.wait_for_timeout(250)
                        stock_panel_hidden_before_selection = not page.locator("#stock-context-card").is_visible()
                        stock_tab_current = page.locator('[data-view-tab="stock"]').get_attribute("aria-current") == "page"
                        stock_search_flow = page.evaluate(
                            """
                            async ({ date }) => {
                              const result = {
                                queried: true,
                                matched_no_report_stock: false,
                                clicked_visible_result: false,
                                visible_empty_state: false,
                                stock_detail_empty_state: false,
                                picked_stock_code: null,
                                picked_stock_name: null,
                                report_empty_state: null,
                              };
                              const response = await fetch(`/api/stocks/search?date=${encodeURIComponent(date)}&q=Beta&limit=5`, { cache: "no-store" });
                              const search = await response.json();
                              const picked = (search.items || []).find((item) => item.has_selected_date_report === false);
                              if (!picked) return result;
                              result.matched_no_report_stock = true;
                              result.picked_stock_code = picked.stock_code || null;
                              result.picked_stock_name = picked.stock_name || null;
                              const detailResponse = await fetch(`/api/daily/${encodeURIComponent(date)}/stocks/${encodeURIComponent(picked.stock_code)}`, { cache: "no-store" });
                              const detail = await detailResponse.json();
                              result.report_empty_state = detail.report_empty_state || null;
                              result.stock_detail_empty_state = detail.has_selected_date_report === false && Array.isArray(detail.reports) && detail.reports.length === 0;
                              return result;
                            }
                            """,
                            {"date": business_date.isoformat()},
                        )
                        if isinstance(stock_search_flow, dict) and stock_search_flow.get("matched_no_report_stock"):
                            picked_name = str(stock_search_flow.get("picked_stock_name") or "Beta")
                            picked_code = str(stock_search_flow.get("picked_stock_code") or "")
                            search_input = page.locator("#stock-search-input")
                            search_input.fill(picked_name, timeout=timeout_ms)
                            page.wait_for_timeout(350)
                            result_locator = page.locator(f'[data-stock-search-code="{picked_code}"]').first
                            if result_locator.count():
                                result_locator.click(timeout=timeout_ms)
                                page.wait_for_timeout(350)
                                stock_search_flow["clicked_visible_result"] = True
                                detail_text = page.locator("#stock-detail").inner_text(timeout=timeout_ms)
                                stock_search_flow["visible_empty_state"] = "선택 날짜에 등록된 리포트가 없습니다." in detail_text
                        candidate_journey_flow = {
                            "candidate_action_found": False,
                            "stock_observation_journey_visible": False,
                        }
                        page.locator('[data-view-tab="watch"]').click(timeout=timeout_ms)
                        page.wait_for_function(
                            """
                            () => {
                              const button = document.querySelector("#candidate-evidence-rows .candidate-detail-action");
                              return Boolean(button && !button.disabled);
                            }
                            """,
                            timeout=timeout_ms,
                        )
                        candidate_action = page.locator("#candidate-evidence-rows .candidate-detail-action").first
                        if candidate_action.count():
                            candidate_journey_flow["candidate_action_found"] = True
                            candidate_code = candidate_action.get_attribute("data-stock-code") or ""
                            candidate_action.click(timeout=timeout_ms)
                            if candidate_code:
                                page.wait_for_selector("#stock-context-card:not([hidden]) #stock-context .stock-observation-journey", timeout=timeout_ms)
                            else:
                                page.wait_for_selector("#stock-context .stock-observation-journey", timeout=timeout_ms)
                            candidate_journey_flow["stock_observation_journey_visible"] = page.locator(
                                "#stock-context .stock-observation-journey"
                            ).is_visible()
                        page.locator('[data-view-tab="market"]').click(timeout=timeout_ms)
                        page.wait_for_timeout(250)
                        market_panel_visible = page.locator("#market-reference-card").is_visible()
                        market_tab_current = page.locator('[data-view-tab="market"]').get_attribute("aria-current") == "page"
                        page.locator('[data-view-tab="rotation"]').click(timeout=timeout_ms)
                        page.wait_for_timeout(250)
                        rotation_panel_visible = page.locator("#rotation-details").is_visible()
                        rotation_tab_current = page.locator('[data-view-tab="rotation"]').get_attribute("aria-current") == "page"
                        page.locator('[data-view-tab="stock"]').focus(timeout=timeout_ms)
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(250)
                        keyboard_market_current = page.locator('[data-view-tab="market"]').get_attribute("aria-current") == "page"
                        viewport_result = {
                            "name": spec["name"],
                            "width": spec["width"],
                            "height": spec["height"],
                            "rendered_business_date": rendered_business_date,
                            "tab_count": tab_count,
                            "tab_order": tab_order,
                            "current_tab_count": current_tab_count,
                            "search_input": bool(search_count),
                            "calendar_dialog_open": calendar_dialog_open,
                            "intraday_button": intraday_button_visible,
                            "intraday_overlap_panel": bool(intraday_overlap_count),
                            "candidate_panel": bool(candidate_count) and candidate_panel_visible,
                            "intraday_overlap_initial_visible": intraday_overlap_initial_visible,
                            "watch_panel_clickable": watch_panel_visible,
                            "watch_candidate_selector_visible": watch_candidate_selector_visible,
                            "stock_panel_hidden_before_selection": stock_panel_hidden_before_selection,
                            "stock_search_flow": stock_search_flow,
                            "candidate_journey_flow": candidate_journey_flow,
                            "market_panel_clickable": market_panel_visible,
                            "rotation_panel_clickable": rotation_panel_visible,
                            "watch_tab_current": watch_tab_current,
                            "stock_tab_current": stock_tab_current,
                            "market_tab_current": market_tab_current,
                            "rotation_tab_current": rotation_tab_current,
                            "keyboard_market_current": keyboard_market_current,
                            "horizontal_overflow_px": horizontal_overflow_px,
                        }
                        viewports.append(viewport_result)
                        if rendered_business_date != business_date.isoformat():
                            issues.append(
                                {
                                    "code": "rendered_business_date_mismatch",
                                    "path": f"viewport[{spec['name']}].main",
                                    "message": (
                                        f"requested {business_date.isoformat()} but rendered "
                                        f"{rendered_business_date or '-'}"
                                    ),
                                }
                            )
                        for text in ("오늘 읽을 요약", "오늘의 우선순위"):
                            if text not in body_text:
                                issues.append(
                                    {
                                        "code": "missing_required_text",
                                        "path": f"viewport[{spec['name']}].body",
                                        "message": f"required visible text is missing: {text}",
                                    }
                                )
                        expected_tab_order = ["main", "watch", "stock", "market", "rotation"]
                        if tab_count != len(expected_tab_order):
                            issues.append(
                                {
                                    "code": "missing_view_tabs",
                                    "path": f"viewport[{spec['name']}].tabs",
                                    "message": f"expected exactly {len(expected_tab_order)} view tabs, found {tab_count}",
                                }
                            )
                        if tab_order != expected_tab_order:
                            issues.append(
                                {
                                    "code": "invalid_view_tab_order",
                                    "path": f"viewport[{spec['name']}].tabs",
                                    "message": "expected view tab order main/watch/stock/market/rotation",
                                }
                            )
                        if current_tab_count != 1:
                            issues.append(
                                {
                                    "code": "invalid_current_tab_count",
                                    "path": f"viewport[{spec['name']}].tabs",
                                    "message": f"expected exactly one current tab, found {current_tab_count}",
                                }
                            )
                        if not search_count:
                            issues.append(
                                {
                                    "code": "missing_stock_search",
                                    "path": f"viewport[{spec['name']}].search",
                                    "message": "stock search input is missing",
                                }
                            )
                        if not intraday_button_visible:
                            issues.append(
                                {
                                    "code": "missing_intraday_market_top_button",
                                    "path": f"viewport[{spec['name']}].intraday_button",
                                    "message": "intraday market-top check button is missing",
                                }
                            )
                        if intraday_overlap_initial_visible:
                            issues.append(
                                {
                                    "code": "intraday_overlap_visible_before_check",
                                    "path": f"viewport[{spec['name']}].intraday_overlap",
                                    "message": "intraday market-top overlap panel should stay hidden before the user checks it",
                                }
                            )
                        if not watch_panel_visible:
                            issues.append(
                                {
                                    "code": "watch_tab_not_clickable",
                                    "path": f"viewport[{spec['name']}].watch_tab",
                                    "message": "watch tab did not expose candidate evidence panel",
                                }
                            )
                        if not watch_candidate_selector_visible:
                            issues.append(
                                {
                                    "code": "watch_candidate_selector_missing",
                                    "path": f"viewport[{spec['name']}].watch_tab",
                                    "message": "watch tab did not expose a candidate selector row",
                                }
                            )
                        if not watch_tab_current:
                            issues.append(
                                {
                                    "code": "watch_tab_state_not_current",
                                    "path": f"viewport[{spec['name']}].watch_tab",
                                    "message": "watch tab did not expose current state after click",
                                }
                            )
                        if not calendar_dialog_open:
                            issues.append(
                                {
                                    "code": "calendar_dialog_not_opened",
                                    "path": f"viewport[{spec['name']}].calendar",
                                    "message": "calendar trigger did not expose the date-selection dialog",
                                }
                            )
                        if not stock_panel_hidden_before_selection:
                            issues.append(
                                {
                                    "code": "stock_panel_visible_without_selection",
                                    "path": f"viewport[{spec['name']}].stock_tab",
                                    "message": "stock detail panel should stay hidden until a stock is selected",
                                }
                            )
                        if not stock_tab_current:
                            issues.append(
                                {
                                    "code": "stock_tab_state_not_current",
                                    "path": f"viewport[{spec['name']}].stock_tab",
                                    "message": "stock tab did not expose current state after click",
                                }
                            )
                        if (
                            isinstance(stock_search_flow, dict)
                            and stock_search_flow.get("matched_no_report_stock")
                            and not stock_search_flow.get("stock_detail_empty_state")
                        ):
                            issues.append(
                                {
                                    "code": "stock_search_empty_state_api_missing",
                                    "path": f"viewport[{spec['name']}].stock_search",
                                    "message": "stored no-report stock did not expose report_empty_state through stock detail API",
                                }
                            )
                        if candidate_journey_flow["candidate_action_found"] and not candidate_journey_flow[
                            "stock_observation_journey_visible"
                        ]:
                            issues.append(
                                {
                                    "code": "candidate_journey_missing_in_stock_detail",
                                    "path": f"viewport[{spec['name']}].candidate_journey",
                                    "message": "candidate detail action did not preserve observation context in stock detail",
                                }
                            )
                        if (
                            isinstance(stock_search_flow, dict)
                            and stock_search_flow.get("matched_no_report_stock")
                            and not stock_search_flow.get("visible_empty_state")
                        ):
                            issues.append(
                                {
                                    "code": "stock_search_empty_state_not_visible",
                                    "path": f"viewport[{spec['name']}].stock_search",
                                    "message": "stored no-report stock search flow did not render the selected-date empty state",
                                }
                            )
                        if not market_panel_visible:
                            issues.append(
                                {
                                    "code": "market_tab_not_clickable",
                                    "path": f"viewport[{spec['name']}].market_tab",
                                    "message": "market tab did not expose market reference panel",
                                }
                            )
                        if not market_tab_current:
                            issues.append(
                                {
                                    "code": "market_tab_current_state_missing",
                                    "path": f"viewport[{spec['name']}].market_tab",
                                    "message": "market tab did not expose current state after click",
                                }
                            )
                        if not rotation_panel_visible:
                            issues.append(
                                {
                                    "code": "rotation_tab_not_clickable",
                                    "path": f"viewport[{spec['name']}].rotation_tab",
                                    "message": "rotation tab did not expose rotation reference panel",
                                }
                            )
                        if not rotation_tab_current:
                            issues.append(
                                {
                                    "code": "rotation_tab_current_state_missing",
                                    "path": f"viewport[{spec['name']}].rotation_tab",
                                    "message": "rotation tab did not expose current state after click",
                                }
                            )
                        if not keyboard_market_current:
                            issues.append(
                                {
                                    "code": "top_tab_keyboard_navigation_failed",
                                    "path": f"viewport[{spec['name']}].tabs",
                                    "message": "ArrowRight from stock tab did not move current state to market tab",
                                }
                            )
                        if not intraday_overlap_count:
                            issues.append(
                                {
                                    "code": "missing_intraday_overlap_panel",
                                    "path": f"viewport[{spec['name']}].intraday_overlap",
                                    "message": "main tab did not expose Naver intraday overlap panel",
                                }
                            )
                        if horizontal_overflow_px > 8:
                            issues.append(
                                {
                                    "code": "horizontal_overflow",
                                    "path": f"viewport[{spec['name']}].layout",
                                    "message": f"document overflows viewport by {horizontal_overflow_px}px",
                                }
                            )
                    finally:
                        context.close()
            finally:
                browser.close()
    except (PlaywrightError, PlaywrightTimeoutError, RuntimeError) as exc:
        issues.append(
            {
                "code": "browser_smoke_failed",
                "path": "web-view-browser-smoke",
                "message": str(exc),
            }
        )

def _web_view_smoke_http_request(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
) -> tuple[int, bytes, str]:
    request = url_request.Request(url, data=data, method=method, headers={"User-Agent": "StockMonitorWebViewSmoke/1.0"})
    try:
        with url_request.urlopen(request, timeout=10) as response:
            return int(response.status), response.read(), response.headers.get("Content-Type", "")
    except url_error.HTTPError as exc:
        return int(exc.code), exc.read(), exc.headers.get("Content-Type", "")
    except url_error.URLError as exc:
        return 0, str(exc).encode("utf-8"), ""

def _resolve_web_view_value_qa_dates(
    config: RuntimeConfig,
    *,
    explicit_dates: tuple[date, ...],
    recent_business_days: int | None,
    today: date | None = None,
) -> tuple[date, ...]:
    resolved: list[date] = []
    seen: set[date] = set()
    for item in explicit_dates:
        if item not in seen:
            resolved.append(item)
            seen.add(item)
    if recent_business_days is not None:
        if recent_business_days < 1:
            raise ValueError("--recent-business-days must be at least 1.")
        probe = today or datetime.now(ZoneInfo(config.timezone)).date()
        while len([item for item in resolved if item not in explicit_dates]) < recent_business_days:
            if is_business_day(probe, config.holiday_overrides) and probe not in seen:
                resolved.append(probe)
                seen.add(probe)
            probe -= timedelta(days=1)
    if not resolved:
        raise ValueError("Pass at least one --date or --recent-business-days N.")
    return tuple(resolved)

def _web_view_value_qa_category_targets(daily_snapshot: dict, *, limit: int) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for default_type, key in (("sector", "sector_rollups"), ("theme", "theme_rollups")):
        for item in daily_snapshot.get(key, []) or []:
            if not isinstance(item, dict):
                continue
            category_type = str(item.get("category_type") or default_type)
            if category_type not in {"sector", "theme"}:
                continue
            display_name = str(
                item.get("display_name")
                or item.get("category_display_name")
                or item.get("category_name")
                or item.get("category_key")
                or ""
            ).strip()
            if not display_name:
                continue
            identity = (category_type, display_name)
            if identity in seen:
                continue
            seen.add(identity)
            targets.append(
                {
                    "category_type": category_type,
                    "display_name": display_name,
                    "category_name": str(item.get("category_name") or item.get("category_key") or display_name),
                }
            )
            if len(targets) >= limit:
                return targets
    return targets

def _collect_web_view_static_html_copy_issues(markup: str, *, issues: list[dict]) -> None:
    text = html.unescape(markup)
    generic_text = text
    blocked_internal_copy = {
        "read-only</span>": "read-only",
        "관찰 후보 근거": "관찰 후보 근거",
        "리포트 후 반응 관찰": "리포트 후 반응 관찰",
        "선택 상태": "선택 상태",
        "<th>D+1</th><th>D+5</th><th>D+10</th><th>D+20</th>": "D+ reaction columns",
        'colspan="8"': "8-column observation table",
        "선택 날짜 KRX 마감값 없음": "선택 날짜 KRX 마감값 없음",
        "선택 날짜 KRX 확정 이력": "선택 날짜 KRX 확정 이력",
        "KRX 최근 흐름": "KRX 최근 흐름",
        "구성종목이 아닌 KRX ETF 일별매매정보 기준": "KRX ETF 오표기",
        "웹뷰에서 뉴스 근거 저장을 실행하면": "GET-only 뉴스 저장 안내",
    }
    blocked_decision_copy = {
        "추천/점수 아님": "추천/점수 아님",
        "추천 순위": "추천 순위",
        "추천이나 매수/매도": "추천이나 매수/매도",
    }
    blocked_admin_copy = (
        "/api/status",
        "/api/scheduler",
        "operator-settings",
        "admin-gui",
        "db_path",
        ".env",
        "Telegram token",
        "shutdown",
    )
    for needle, label in blocked_internal_copy.items():
        if needle in text:
            issues.append(
                {
                    "code": "public_html_internal_copy",
                    "path": f"web_view_html.{label}",
                    "message": "static web-view HTML exposes old internal/process copy",
                }
            )
    for needle, label in blocked_decision_copy.items():
        if needle in text:
            issues.append(
                {
                    "code": "public_html_decision_wording",
                    "path": f"web_view_html.{label}",
                    "message": "static web-view HTML exposes blocked decision/disclaimer wording",
                }
            )
            generic_text = generic_text.replace(needle, "")
    for needle in ("추천", "점수", "등급", "매수 후보", "매도 신호"):
        if needle in generic_text:
            issues.append(
                {
                    "code": "public_html_decision_wording",
                    "path": f"web_view_html.{needle}",
                    "message": "static web-view HTML exposes blocked decision/disclaimer wording",
                }
            )
    for needle in blocked_admin_copy:
        if needle in text:
            issues.append(
                {
                    "code": "public_html_admin_surface_leak",
                    "path": f"web_view_html.{needle}",
                    "message": "static web-view HTML exposes an admin/operator surface reference",
                }
            )

def _collect_web_view_value_qa_issues(
    value: object,
    *,
    path: str,
    issues: list[dict],
    warnings: list[dict],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _is_web_view_forbidden_public_key(key):
                issues.append(
                    {
                        "code": "public_dto_admin_key",
                        "path": child_path,
                        "message": "public web-view DTO exposes an admin/operator key",
                    }
                )
            _collect_web_view_value_qa_issues(
                child,
                path=child_path,
                issues=issues,
                warnings=warnings,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_web_view_value_qa_issues(
                child,
                path=f"{path}[{index}]",
                issues=issues,
                warnings=warnings,
            )
        return
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        issues.append({"code": "invalid_number", "path": path, "message": f"invalid numeric value: {value}"})
        return
    if isinstance(value, str):
        normalized = value.strip().upper()
        field_name = path.rsplit(".", 1)[-1]
        if path.endswith(".category_contract.mapping_basis") and value.strip() == "latest_mapping_fallback":
            warnings.append(
                {
                    "code": "category_mapping_fallback",
                    "path": path,
                    "message": "selected date uses latest stored category classification instead of a source-date snapshot",
                }
            )
        if normalized in {"NAN", "INF", "INFINITY", "-INF", "-INFINITY"}:
            issues.append({"code": "invalid_number", "path": path, "message": f"invalid numeric string: {value}"})
            return
        _collect_public_observation_text_issue(value, path=path, issues=issues)
        is_display_field = _is_web_view_display_field(field_name)
        if is_display_field and re.search(r"\b00:00(?::00)?\b", value):
            issues.append(
                {
                    "code": "display_placeholder_time",
                    "path": path,
                    "message": "display field exposes a midnight placeholder time",
                }
            )
        if (
            normalized in {"N/A", "NA", "NULL", "NONE", "-"}
            or (normalized == "" and field_name.endswith(("_display_name", "_display")))
        ) and (
            is_display_field
            or field_name.endswith("_display_name")
            or field_name in {"title_display", "category_display_name", "sector_display_name", "theme_display_name"}
        ):
            issues.append({"code": "display_na", "path": path, "message": "display field exposes internal N/A marker"})
        if _is_market_briefing_turnover_display_path(path) and _looks_like_raw_won_amount(value):
            issues.append(
                {
                    "code": "public_market_briefing_raw_turnover_display",
                    "path": path,
                    "message": "market briefing turnover display should use compact 조/억 units",
                }
            )

def _is_web_view_display_field(field_name: str) -> bool:
    return field_name.endswith(("_display", "_display_name", "_label"))

def _is_market_briefing_turnover_display_path(path: str) -> bool:
    return ".market_briefing.turnover_summary." in path and path.endswith(".turnover_display")

def _looks_like_raw_won_amount(value: str) -> bool:
    text = value.strip()
    if not text.endswith("원"):
        return False
    numeric = text[:-1].replace(",", "").strip()
    return numeric.isdigit() and len(numeric) >= 10

def _is_web_view_forbidden_public_key(key: str) -> bool:
    return key in {
        "safe_settings",
        "recent_admin_audit_logs",
        "admin_audit_log",
        "scheduler_tasks",
        "worker_states",
        "health",
        "db_path",
        "operation_profile",
        "daily_summary_min_mention_count",
        "daily_summary_require_target_price",
        "notification_default_limit",
        "overall_sentiment",
        "sentiment_score",
        "stock_impact",
        "operator_recommendation",
        "recommendation_support",
    }

def _collect_public_observation_text_issue(value: str, *, path: str, issues: list[dict]) -> None:
    lower = value.lower()
    if any(token in lower for token in ("prototype_value", "candidate_score", "candidate_reasons")):
        issues.append(
            {
                "code": "public_observation_internal_value",
                "path": path,
                "message": "public observation text exposes an internal prototype/scoring field",
            }
        )
        return
    if _is_source_report_text_path(path):
        return
    if _has_public_observation_decision_wording(value):
        issues.append(
            {
                "code": "public_observation_decision_wording",
                "path": path,
                "message": "public observation text uses blocked decision wording",
            }
        )

def _is_source_report_text_path(path: str) -> bool:
    return ".reports[" in path and path.rsplit(".", 1)[-1] in {"title", "title_display"}

def _has_public_observation_decision_wording(value: str) -> bool:
    text = value.strip()
    lower = text.lower()
    if any(token in text for token in ("추천 후보", "추천 종목", "추천주", "매수 후보", "매수추천")):
        return True
    if any(token in text for token in ("점수:", "점수=", "등급:", "등급=")):
        return True
    if "추천" in text:
        return True
    if "점수" in text:
        return True
    if "등급" in text:
        return True
    if any(
        token in lower
        for token in (
            "buy candidate",
            "sell candidate",
            "buy signal",
            "sell signal",
            "recommendation candidate",
            "entry price",
            "exit price",
            "take-profit",
            "take profit",
            "conviction",
            "score=",
            "score:",
            "rating=",
        )
    ):
        return True
    return False
