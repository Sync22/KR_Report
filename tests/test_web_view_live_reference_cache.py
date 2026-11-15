from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime as RealDateTime
from io import BytesIO
from threading import Event
import json

from stock_monitor import cli
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import Report


class _FakeRequest:
    def __init__(self, path: str) -> None:
        self.path = path
        self.command = "GET"
        self.headers = {"Accept-Encoding": ""}
        self.wfile = BytesIO()
        self.status = 0
        self.response_headers: dict[str, str] = {}

    def send_response(self, status: int) -> None:
        self.status = int(status)

    def send_header(self, name: str, value: str) -> None:
        self.response_headers[name] = value

    def end_headers(self) -> None:
        pass


def _fixture(tmp_path, monkeypatch, business_date: date):
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    published_at = RealDateTime(business_date.year, business_date.month, business_date.day, 10, 0)
    repository.insert_reports([
        Report(
            stock_name="삼성전자", stock_code="005930", title="삼성전자 첫 보고서", broker_name="NH",
            published_at=published_at, business_date=business_date, collected_at=published_at,
            source_id="live-cache-1", identity_key="live-cache-1",
        ),
        Report(
            stock_name="삼성전자", stock_code="005930", title="삼성전자 두 번째 보고서", broker_name="KB",
            published_at=published_at, business_date=business_date, collected_at=published_at,
            source_id="live-cache-2", identity_key="live-cache-2",
        ),
        Report(
            stock_name="SK하이닉스", stock_code="000660", title="SK하이닉스 첫 보고서", broker_name="NH",
            published_at=published_at, business_date=business_date, collected_at=published_at,
            source_id="live-cache-3", identity_key="live-cache-3",
        ),
        Report(
            stock_name="SK하이닉스", stock_code="000660", title="SK하이닉스 두 번째 보고서", broker_name="KB",
            published_at=published_at, business_date=business_date, collected_at=published_at,
            source_id="live-cache-4", identity_key="live-cache-4",
        ),
    ])
    repository.rebuild_daily_summaries(business_date)
    monkeypatch.setattr(cli, "_access_http_gate", lambda *_args, **_kwargs: True)
    return config, repository


def _payload(handler_type, path: str) -> tuple[int, dict[str, object]]:
    request = _FakeRequest(path)
    handler_type.do_GET(request)
    return request.status, json.loads(request.wfile.getvalue().decode("utf-8"))


class _FrozenDateTime(RealDateTime):
    current = RealDateTime(2026, 11, 16, 10, 0, 0)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current
        return cls.current.replace(tzinfo=tz)


def test_python_priority_quotes_cache_actual_order_and_preserve_checked_at(tmp_path, monkeypatch) -> None:
    business_date = date(2026, 11, 16)
    config, repository = _fixture(tmp_path, monkeypatch, business_date)
    monkeypatch.setattr(cli, "datetime", _FrozenDateTime)
    latest_date = [business_date.isoformat()]
    selected_codes = ["005930", "000660"]
    candidate_calls = 0
    second_candidate_read = Event()

    def archive(*_args, **_kwargs):
        return {"latest_business_date": latest_date[0]}

    def candidates(*_args, **_kwargs):
        nonlocal candidate_calls
        candidate_calls += 1
        if candidate_calls >= 2:
            second_candidate_read.set()
        return {"rows": [{"selected": True, "stock_code": code} for code in selected_codes]}

    calls: list[str] = []
    quote_started = Event()
    release_quote = Event()

    def quote(stock_code: str, **_kwargs):
        calls.append(stock_code)
        if len(calls) == 1:
            quote_started.set()
            assert release_quote.wait(2)
        return cli.StockQuoteSnapshot(
            stock_code=stock_code, stock_name=f"종목 {stock_code}", sector_code=None, sector_name=None,
            current_price=100, market_status="OPEN", trade_time=_FrozenDateTime.current,
            prev_close_price=99, prev_change_rate=1.0, trade_amount=1000, trade_volume=10,
        )

    monkeypatch.setattr(cli, "build_web_view_archive_snapshot", archive)
    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", candidates)
    monkeypatch.setattr(cli, "fetch_stock_quote_snapshot", quote)
    handler_type = cli._make_web_view_handler(config, repository, limit=5)
    path = f"/api/priority-current-quotes?date={business_date.isoformat()}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(_payload, handler_type, path)
        assert quote_started.wait(2)
        shared = executor.submit(_payload, handler_type, path)
        assert second_candidate_read.wait(2)
        release_quote.set()
        first_status, first_payload = first.result(timeout=2)
        shared_status, shared_payload = shared.result(timeout=2)

    assert first_status == shared_status == 200
    assert calls == ["005930", "000660"]
    assert first_payload["checked_at"] == shared_payload["checked_at"]

    _FrozenDateTime.current = RealDateTime(2026, 11, 16, 10, 0, 5)
    cached_status, cached_payload = _payload(handler_type, path)
    assert cached_status == 200
    assert cached_payload["checked_at"] == first_payload["checked_at"]
    assert calls == ["005930", "000660"]

    selected_codes[:] = ["000660", "005930"]
    reordered_status, reordered_payload = _payload(handler_type, path)
    assert reordered_status == 200
    assert [item["stock_code"] for item in reordered_payload["items"]] == ["000660", "005930"]
    assert calls == ["005930", "000660", "000660", "005930"]

    latest_date[0] = "2026-11-17"
    conflict_status, conflict_payload = _payload(handler_type, path)
    assert conflict_status == 409
    assert conflict_payload["reason"] == "latest_business_date_only"
    assert len(calls) == 4


def test_python_priority_quotes_retry_partial_failure_without_caching(tmp_path, monkeypatch) -> None:
    business_date = date(2026, 11, 16)
    config, repository = _fixture(tmp_path, monkeypatch, business_date)
    monkeypatch.setattr(cli, "datetime", _FrozenDateTime)
    monkeypatch.setattr(cli, "build_web_view_archive_snapshot", lambda *_args, **_kwargs: {"latest_business_date": business_date.isoformat()})
    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", lambda *_args, **_kwargs: {
        "rows": [{"selected": True, "stock_code": "005930"}, {"selected": True, "stock_code": "000660"}],
    })
    calls: list[str] = []
    fail = True

    def quote(stock_code: str, **_kwargs):
        nonlocal fail
        calls.append(stock_code)
        if fail and stock_code == "005930":
            raise RuntimeError("provider unavailable")
        return cli.StockQuoteSnapshot(
            stock_code=stock_code, stock_name=f"종목 {stock_code}", sector_code=None, sector_name=None,
            current_price=100, market_status="OPEN", trade_time=_FrozenDateTime.current,
            prev_close_price=99, prev_change_rate=1.0, trade_amount=1000, trade_volume=10,
        )

    monkeypatch.setattr(cli, "fetch_stock_quote_snapshot", quote)
    handler_type = cli._make_web_view_handler(config, repository, limit=5)
    path = f"/api/priority-current-quotes?date={business_date.isoformat()}"

    status, failed = _payload(handler_type, path)
    fail = False
    retry_status, retried = _payload(handler_type, path)

    assert status == retry_status == 200
    assert failed["errors"] == ["005930"]
    assert retried["errors"] == []
    assert calls == ["005930", "000660", "005930", "000660"]


def test_python_daily_live_references_cache_success_and_check_eligibility_before_cache(tmp_path, monkeypatch) -> None:
    business_date = date(2026, 11, 16)
    _FrozenDateTime.current = RealDateTime(2026, 11, 16, 10, 0, 0)
    config, repository = _fixture(tmp_path, monkeypatch, business_date)
    monkeypatch.setattr(cli, "datetime", _FrozenDateTime)
    monkeypatch.setattr(cli, "is_business_day", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    page_calls = []
    quote_calls = []

    def fetch_market_top(market, **kwargs):
        page_calls.append((market, kwargs["page"], kwargs["page_size"]))
        return []

    def fetch_quote(stock_code, **_kwargs):
        quote_calls.append(stock_code)
        return cli.StockQuoteSnapshot(
            stock_code=stock_code, stock_name=f"종목 {stock_code}", sector_code=None, sector_name=None,
            current_price=100, market_status="OPEN", trade_time=_FrozenDateTime.current,
            prev_close_price=99, prev_change_rate=1.0, trade_amount=1000, trade_volume=10,
        )

    monkeypatch.setattr(cli, "fetch_market_top_stocks", fetch_market_top)
    monkeypatch.setattr(cli, "fetch_stock_quote_snapshot", fetch_quote)
    handler_type = cli._make_web_view_handler(config, repository, limit=5)
    path = f"/api/daily/{business_date.isoformat()}?intraday_market_top=1&market_top_limit=100&market_top_page_size=20"

    first_status, first = _payload(handler_type, path)
    cached_status, cached = _payload(handler_type, path)

    assert first_status == cached_status == 200
    assert first["market_commentary"]["intraday_market_top_reference"]["live_fetch"] is True
    assert first["market_commentary"]["intraday_market_top_reference"]["checked_at"] == cached["market_commentary"]["intraday_market_top_reference"]["checked_at"]
    assert len(page_calls) == 2
    assert len(quote_calls) > 0
    first_quote_count = len(quote_calls)

    limit_path = f"/api/daily/{business_date.isoformat()}?intraday_market_top=1&market_top_limit=20&market_top_page_size=20"
    limited_status, limited = _payload(handler_type, limit_path)
    assert limited_status == 200
    assert limited["market_commentary"]["intraday_market_top_reference"]["limit"] == 20
    assert len(page_calls) == 4
    assert len(quote_calls) == first_quote_count * 2

    _FrozenDateTime.current = RealDateTime(2026, 11, 17, 10, 0, 0)
    ineligible_status, ineligible = _payload(handler_type, path)
    assert ineligible_status == 200
    assert ineligible["market_commentary"]["intraday_market_top_reference"]["live_fetch"] is False
    assert len(page_calls) == 4


def test_python_daily_live_reference_errors_are_retried(tmp_path, monkeypatch) -> None:
    business_date = date(2026, 11, 16)
    _FrozenDateTime.current = RealDateTime(2026, 11, 16, 10, 0, 0)
    config, repository = _fixture(tmp_path, monkeypatch, business_date)
    monkeypatch.setattr(cli, "datetime", _FrozenDateTime)
    monkeypatch.setattr(cli, "is_business_day", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    page_calls = []
    fail = True

    def fetch_market_top(market, **kwargs):
        nonlocal fail
        page_calls.append((market, kwargs["page"], kwargs["page_size"]))
        if fail and market == "KOSPI":
            fail = False
            raise RuntimeError("private provider response")
        return []

    monkeypatch.setattr(cli, "fetch_market_top_stocks", fetch_market_top)
    monkeypatch.setattr(cli, "fetch_stock_quote_snapshot", lambda code, **_kwargs: cli.StockQuoteSnapshot(
        stock_code=code, stock_name=code, sector_code=None, sector_name=None, current_price=100,
        market_status="OPEN", trade_time=_FrozenDateTime.current, prev_close_price=99,
        prev_change_rate=1.0, trade_amount=1000, trade_volume=10,
    ))
    handler_type = cli._make_web_view_handler(config, repository, limit=5)
    path = f"/api/daily/{business_date.isoformat()}?intraday_market_top=1&market_top_limit=100&market_top_page_size=20"

    first_status, first = _payload(handler_type, path)
    retry_status, retried = _payload(handler_type, path)

    assert first_status == retry_status == 200
    assert first["market_commentary"]["intraday_market_top_reference"]["errors"]
    assert retried["market_commentary"]["intraday_market_top_reference"]["errors"] == []
    assert len(page_calls) == 4
