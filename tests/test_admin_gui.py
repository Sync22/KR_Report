import json
import threading
import urllib.error
import urllib.request
from datetime import date, datetime

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


ADMIN_GUI_JUDGMENT_REVIEW_FORBIDDEN_TOKENS = (
    "news-intelligence",
    "news_observation",
    "candidate-evidence",
    "candidate_evidence",
    "candidate_linkage",
    "sentiment_score",
    "stock_impact",
    "operator_recommendation",
    "recommendation_support",
)


def test_admin_gui_html_contains_status_shell() -> None:
    html = cli_module._render_admin_gui_html()

    assert "Stock Monitor Admin" in html
    assert "/api/status" in html
    assert "스케줄러 작업" in html
    assert "시장 분위기" not in html
    assert "mood-total-reports" not in html
    assert "최근 리포트/요약" not in html
    assert "report-rows" not in html
    assert "섹터 요약" not in html
    assert "sector-rows" not in html
    assert "테마 요약" not in html
    assert "theme-rows" not in html
    assert "KRX 시장 데이터" not in html
    assert "KOSPI 거래대금 상위" not in html
    assert "KOSDAQ 거래대금 상위" not in html
    assert "ETF 거래대금 상위" not in html
    assert "시장 지수" not in html
    assert "krx-kospi-rows" not in html
    assert "krx-kosdaq-rows" not in html
    assert "krx-etf-rows" not in html
    assert "krx-index-rows" not in html
    assert "안전 설정" in html
    assert "safe-setting-rows" in html
    assert "설정 변경 이력" in html
    assert "audit-log-rows" in html
    assert "/api/settings/set" in html
    assert "<h2>운영 제어</h2>" not in html
    assert "<h2>DB 실행 제외일</h2>" not in html
    assert "/api/scheduler/run-now" in html
    assert "/api/scheduler/set-enabled" in html
    assert "/api/scheduler/restart" in html
    assert "실행 차단" in html
    assert "전일 요약 발송" in html
    assert "장중 리포트 수집" in html
    assert "KRX 로그인 알림" in html
    assert "16:45 검증용 알림" in html
    assert "krx-flow-login-reminder" in html
    assert '""": "&quot;' not in html
    assert "const replacements" in html
    assert "작업 실패" in html
    assert "환경 제외" in html
    assert "오늘 실행" in html
    assert "장중 대기" in html
    assert "DB 백업" in html
    assert "backup-status" in html
    assert "backup-reminder" in html
    assert "복구 안내" in html
    assert "recovery-action-rows" in html
    assert "detail_display" in html
    assert "종가(포인트)" not in html
    assert "데스크톱 검증" in html
    assert "scheduled wrapper" not in html
    assert "실행 제외 달력" in html
    assert "overflow-x: hidden" in html
    assert "min-width: 0" in html
    assert "text-overflow: ellipsis" in html
    assert "data-calendar-date" in html
    assert "calendar-prev" in html
    assert "시장 휴장일" in html
    assert "로컬 전용 관리자 화면입니다" in html
    assert "로컬 전용 읽기 화면입니다" not in html


def test_admin_gui_html_excludes_judgment_review_surfaces() -> None:
    html = cli_module._render_admin_gui_html()

    assert "/api/status" in html
    assert "/api/scheduler/run-now" in html
    assert "/api/settings/set" in html
    assert "audit-log-rows" in html
    for token in ADMIN_GUI_JUDGMENT_REVIEW_FORBIDDEN_TOKENS:
        assert token not in html


def test_admin_gui_host_guard_allows_loopback_hosts() -> None:
    assert cli_module._is_loopback_admin_host("127.0.0.1") is True
    assert cli_module._is_loopback_admin_host("localhost") is True
    assert cli_module._is_loopback_admin_host("::1") is True


def test_admin_gui_host_guard_rejects_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="refuses non-loopback host"):
        cli_module._validate_admin_gui_host("0.0.0.0")


def test_admin_gui_host_guard_can_be_explicitly_overridden() -> None:
    cli_module._validate_admin_gui_host("0.0.0.0", allow_non_loopback=True)


def test_admin_gui_server_serves_html_and_status_json(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 5, 6, 9, 0, 0, tzinfo=tz)

    monkeypatch.setattr(cli_module, "datetime", FixedDatetime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.set_operator_pause(paused=True, updated_at=datetime(2026, 5, 6, 9, 0, 0), detail="test")
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base_url + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        with urllib.request.urlopen(base_url + "/api/status", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert "Stock Monitor Admin" in html
    assert payload["is_operator_paused"] is True
    assert payload["run_skip_reason"] == "Stock Monitor is paused by operator control."
    assert "2026-05-01" in payload["market_holidays"]
    assert payload["backup"]["exists"] is False
    assert "db-verify" in payload["data_safety_reminders"][0]
    assert any(action["key"] == "create_db_backup" for action in payload["recovery_actions"])
    assert "daily_summary_min_mention_count" in payload["safe_settings"]
    assert payload["recent_admin_audit_logs"] == []
    payload_text = json.dumps(payload, ensure_ascii=False)
    for token in ADMIN_GUI_JUDGMENT_REVIEW_FORBIDDEN_TOKENS:
        assert token not in payload_text


def test_admin_gui_access_code_gate_protects_status_until_login(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    cli_module._write_access_code_record(config, "2468")
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(base_url + "/api/status", timeout=5)
        login_html = exc_info.value.read().decode("utf-8")

        correct_request = urllib.request.Request(
            base_url + "/auth/login",
            data=b"access_code=2468",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        opener = urllib.request.build_opener(NoRedirect)
        with pytest.raises(urllib.error.HTTPError) as redirect_exc_info:
            opener.open(correct_request, timeout=5)
        cookie = redirect_exc_info.value.headers["Set-Cookie"].split(";", 1)[0]

        status_request = urllib.request.Request(base_url + "/api/status", headers={"Cookie": cookie})
        with urllib.request.urlopen(status_request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert exc_info.value.code == 401
    assert "입장코드 입력" in login_html
    assert "관리자 화면" in login_html
    assert redirect_exc_info.value.code == 303
    assert "daily_summary_min_mention_count" in payload["safe_settings"]


def test_access_code_sessions_are_surface_specific(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    cli_module._write_access_code_record(config, "2468")
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    web_server = cli_module.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=2)
    admin_server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    web_thread = threading.Thread(target=web_server.serve_forever, daemon=True)
    admin_thread = threading.Thread(target=admin_server.serve_forever, daemon=True)
    web_thread.start()
    admin_thread.start()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        web_base_url = f"http://127.0.0.1:{web_server.server_port}"
        admin_base_url = f"http://127.0.0.1:{admin_server.server_port}"
        web_login_request = urllib.request.Request(
            web_base_url + "/auth/login",
            data=b"access_code=2468",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        opener = urllib.request.build_opener(NoRedirect)
        with pytest.raises(urllib.error.HTTPError) as web_redirect_exc_info:
            opener.open(web_login_request, timeout=5)
        web_cookie = web_redirect_exc_info.value.headers["Set-Cookie"].split(";", 1)[0]

        admin_status_request = urllib.request.Request(
            admin_base_url + "/api/status",
            headers={"Cookie": web_cookie},
        )
        with pytest.raises(urllib.error.HTTPError) as admin_exc_info:
            urllib.request.urlopen(admin_status_request, timeout=5)
    finally:
        web_server.shutdown()
        admin_server.shutdown()
        web_server.server_close()
        admin_server.server_close()
        web_thread.join(timeout=5)
        admin_thread.join(timeout=5)

    assert web_redirect_exc_info.value.code == 303
    assert admin_exc_info.value.code == 401


def test_admin_gui_status_reuses_scheduler_status_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    calls = {"count": 0}

    def fake_load_scheduler_task_statuses(_prefix="StockMonitor"):
        calls["count"] += 1
        return [
            {
                "task_name": "StockMonitor-Poll",
                "available": True,
                "exists": True,
                "state": "Ready",
                "enabled": True,
                "next_run_time": None,
                "last_run_time": None,
                "last_task_result": None,
                "detail": None,
            }
        ]

    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", fake_load_scheduler_task_statuses)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        first_payload = _get_json(base_url + "/api/status")
        second_payload = _get_json(base_url + "/api/status")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert calls["count"] == 1
    assert first_payload["scheduler_tasks"][0]["task_name"] == "StockMonitor-Poll"
    assert second_payload["scheduler_tasks"][0]["task_name"] == "StockMonitor-Poll"


def test_admin_gui_scheduler_action_invalidates_status_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    calls = {"count": 0}

    def fake_load_scheduler_task_statuses(_prefix="StockMonitor"):
        calls["count"] += 1
        return [
            {
                "task_name": "StockMonitor-Poll",
                "available": True,
                "exists": True,
                "state": f"Ready-{calls['count']}",
                "enabled": True,
                "next_run_time": None,
                "last_run_time": None,
                "last_task_result": None,
                "detail": None,
            }
        ]

    def fake_execute(action, task_name):
        assert action == "run-now"
        assert task_name == "StockMonitor-Poll"
        return {"state": "Running"}

    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", fake_load_scheduler_task_statuses)
    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        first_payload = _get_json(base_url + "/api/status")
        _post_json(base_url + "/api/scheduler/run-now", {"task": "poll", "confirm_text": "실행"})
        second_payload = _get_json(base_url + "/api/status")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert calls["count"] == 2
    assert first_payload["scheduler_tasks"][0]["state"] == "Ready-1"
    assert second_payload["scheduler_tasks"][0]["state"] == "Ready-2"


def test_admin_gui_operator_control_posts_update_state(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 1, 9, 0, 0, tzinfo=tz)

    monkeypatch.setattr(cli_module, "datetime", FixedDatetime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _post_json(base_url + "/api/operator/pause", {"reason": "test pause"})
        assert repository.is_operator_paused() is True

        _post_json(base_url + "/api/operator/resume", {})
        assert repository.is_operator_paused() is False

        _post_json(base_url + "/api/operator/add-no-run-date", {"date": "2026-06-02", "reason": "test"})
        assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is True

        _post_json(base_url + "/api/operator/remove-no-run-date", {"date": "2026-06-02"})
        assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_admin_gui_post_failure_records_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    server = cli_module.create_admin_gui_server(config, repository, host="127.0.0.1", port=0, limit=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with pytest.raises(urllib.error.HTTPError):
            _post_json(base_url + "/api/scheduler/run-now", {"task": "poll", "confirm_text": "아님"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    events = repository.list_recent_operation_events(limit=1)
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "post"
    assert events[0].status == "failed"
    assert "/api/scheduler/run-now" in (events[0].detail or "")


def test_admin_gui_scheduler_run_now_requires_confirmation(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="confirm"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/scheduler/run-now",
            {"task": "poll", "confirm_text": "nope"},
        )


def test_admin_gui_scheduler_run_now_blocks_shutdown(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="Shutdown"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/scheduler/run-now",
            {"task": "shutdown", "confirm_text": "실행"},
        )


def test_admin_gui_rejects_no_run_date_for_market_holiday(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="no DB no-run override"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/operator/add-no-run-date",
            {"date": "2026-05-01", "reason": "holiday"},
        )

    assert repository.list_db_run_suppressed_dates() == []


def test_admin_gui_rejects_past_no_run_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="in the past"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/operator/add-no-run-date",
            {"date": "2026-05-14", "reason": "stale click"},
        )

    assert repository.list_db_run_suppressed_dates() == []


def test_admin_gui_scheduler_run_now_records_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "run-now"
        assert task_name == "StockMonitor-Poll"
        return {"state": "Running"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/scheduler/run-now",
        {"task": "poll", "confirm_text": "실행"},
    )

    events = repository.list_recent_operation_events(limit=1)
    assert status.value == 200
    assert payload["ok"] is True
    assert payload["task_name"] == "StockMonitor-Poll"
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "scheduler-run-now"


def test_admin_gui_scheduler_set_enabled_requires_confirmation(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="confirm"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/scheduler/set-enabled",
            {"task": "poll", "enabled": False, "confirm_text": "nope"},
        )


def test_admin_gui_scheduler_set_enabled_requires_boolean_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="boolean"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/scheduler/set-enabled",
            {"task": "poll", "enabled": "false", "confirm_text": "변경"},
        )


def test_admin_gui_scheduler_set_enabled_records_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "disable"
        assert task_name == "StockMonitor-Poll"
        return {"state": "Disabled"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/scheduler/set-enabled",
        {"task": "poll", "enabled": False, "confirm_text": "변경"},
    )

    events = repository.list_recent_operation_events(limit=1)
    assert status.value == 200
    assert payload["ok"] is True
    assert payload["state"] == "Disabled"
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "scheduler-disable"


def test_admin_gui_scheduler_set_enabled_supports_krx_login_reminder(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "disable"
        assert task_name == "StockMonitor-KrxFlowLoginReminder"
        return {"state": "Disabled"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/scheduler/set-enabled",
        {"task": "krx-flow-login-reminder", "enabled": False, "confirm_text": "변경"},
    )

    events = repository.list_recent_operation_events(limit=1)
    assert status.value == 200
    assert payload["ok"] is True
    assert payload["task_name"] == "StockMonitor-KrxFlowLoginReminder"
    assert payload["state"] == "Disabled"
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "scheduler-disable"


def test_admin_gui_scheduler_restart_telegram_commands_records_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_execute(action, task_name):
        assert action == "restart"
        assert task_name == "StockMonitor-TelegramCommands"
        return {"state": "Running"}

    monkeypatch.setattr(cli_module, "_execute_scheduler_control_action", fake_execute)

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/scheduler/restart",
        {"task": "telegram-commands", "confirm_text": "재시작"},
    )

    events = repository.list_recent_operation_events(limit=1)
    assert status.value == 200
    assert payload["ok"] is True
    assert payload["state"] == "Running"
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "scheduler-restart"


def test_admin_gui_safe_setting_change_records_audit_and_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/settings/set",
        {
            "key": "notification_default_limit",
            "value": "9",
            "reason": "admin setting test",
            "confirm_text": "변경",
        },
    )

    setting = repository.get_app_setting("notification_default_limit")
    logs = repository.list_admin_audit_logs()
    events = repository.list_recent_operation_events(limit=1)
    assert status.value == 200
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert setting is not None
    assert setting.setting_value == "9"
    assert setting.updated_by == "admin-gui"
    assert logs[0].actor == "admin-gui"
    assert logs[0].setting_key == "notification_default_limit"
    assert logs[0].old_value is None
    assert logs[0].new_value == "9"
    assert events[0].component == "admin-gui"
    assert events[0].event_type == "setting-set"


def test_admin_gui_safe_setting_requires_confirmation(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="confirm"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/settings/set",
            {
                "key": "notification_default_limit",
                "value": "9",
                "reason": "admin setting test",
                "confirm_text": "아님",
            },
        )


def test_admin_gui_can_update_operation_profile_after_policy_is_wired(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/settings/set",
        {
            "key": "operation_profile",
            "value": "mini-pc",
            "reason": "profile test",
            "confirm_text": "변경",
        },
    )

    setting = repository.get_app_setting("operation_profile")
    assert status.value == 200
    assert payload["ok"] is True
    assert setting is not None
    assert setting.setting_value == "mini-pc"


def test_admin_gui_safe_setting_validation_failure_records_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    with pytest.raises(ValueError, match="between 3 and 20"):
        cli_module._handle_admin_gui_post(
            config,
            repository,
            "/api/settings/set",
            {
                "key": "notification_default_limit",
                "value": "99",
                "reason": "bad value",
                "confirm_text": "변경",
            },
        )

    logs = repository.list_admin_audit_logs()
    assert logs[0].actor == "admin-gui"
    assert logs[0].setting_key == "notification_default_limit"
    assert logs[0].status == "validation_failed"


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
