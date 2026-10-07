from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, NoReturn
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from stock_monitor.db.repository import StockMonitorRepository


DEFAULT_OPERATOR_REVIEW_HOST = "127.0.0.1"
DEFAULT_OPERATOR_REVIEW_PORT = 8767
DEFAULT_NEWBBY_BASE_URL = "http://127.0.0.1:8734"
OPERATOR_REVIEW_PAGE_PATH = "/"
OPERATOR_REVIEW_API_PATH = "/api/operator-review"
_STOCK_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class _ReadOnlyStockMonitorRepository(StockMonitorRepository):
    """Repository whose connections cannot create or modify the database."""

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        active_connection = self._active_read_connection.get()
        if active_connection is not None:
            yield active_connection
            return

        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> NoReturn:
        raise RuntimeError("operator-review is read-only and cannot initialize the database")

    def migrate_schema(self, *, dry_run: bool = False) -> NoReturn:
        raise RuntimeError("operator-review is read-only and cannot migrate the database")

    def enable_wal_mode(self) -> NoReturn:
        raise RuntimeError("operator-review is read-only and cannot change database journal mode")


def build_newbby_chart_url(
    stock_code: str,
    business_date: date,
    *,
    base_url: str = DEFAULT_NEWBBY_BASE_URL,
) -> str | None:
    if not _STOCK_CODE_PATTERN.fullmatch(str(stock_code or "")):
        return None
    parts = _validated_newbby_base_url(base_url)
    query = urlencode({"symbol": stock_code, "asOf": business_date.isoformat()})
    return urlunsplit((parts.scheme, parts.netloc, "/chart-first.html", query, ""))


def _validated_newbby_base_url(value: str):
    parts = urlsplit(str(value or "").strip())
    try:
        parts.port
    except ValueError as exc:
        raise ValueError("Newbby URL must use a valid loopback port.") from exc
    if (
        parts.scheme != "http"
        or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Newbby URL must be an HTTP loopback origin without a path or query.")
    return parts


def build_operator_review_payload(
    config,
    repository: StockMonitorRepository,
    business_date: date,
    *,
    newbby_base_url: str = DEFAULT_NEWBBY_BASE_URL,
) -> dict[str, object]:
    if not repository.list_daily_summaries(business_date):
        return {
            "surface": "operator-review",
            "business_date": business_date.isoformat(),
            "source": "selected_date_main_snapshot",
            "selection_basis": "stored_daily_summaries_missing",
            "available": False,
            "read_only": True,
            "live_fetch": False,
            "writes_db": False,
            "scoring": False,
            "recommendation": False,
            "candidates": [],
            "empty_state": "선택 날짜의 저장된 후보 요약이 없습니다. 이 화면에서는 요약을 재생성하지 않습니다.",
        }

    # Use the same selected-date builder as Main without invoking its broader
    # daily summary path, which may repair missing opening-context summaries.
    from stock_monitor.cli import build_web_view_candidate_evidence_snapshot

    candidate_snapshot = build_web_view_candidate_evidence_snapshot(
        config,
        repository,
        business_date=business_date,
        limit=2,
    )
    rows = candidate_snapshot.get("rows") if isinstance(candidate_snapshot, dict) else []
    candidates = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("selected") is not True:
            continue
        stock_code = str(row.get("stock_code") or "")
        market = row.get("market_reference") if isinstance(row.get("market_reference"), dict) else {}
        news = row.get("news_observation_badge") if isinstance(row.get("news_observation_badge"), dict) else {}
        flow = row.get("stock_flow_reference") if isinstance(row.get("stock_flow_reference"), dict) else {}
        baseline = row.get("toss_baseline_reference") if isinstance(row.get("toss_baseline_reference"), dict) else {}
        report = row.get("report_summary") if isinstance(row.get("report_summary"), dict) else {}
        layers = row.get("evidence_layers") if isinstance(row.get("evidence_layers"), dict) else {}

        news_status = _news_collection_status(news)
        news_available = news_status != "not_collected"
        market_available = market.get("available") is True
        flow_available = flow.get("available") is True
        baseline_available = baseline.get("available") is True
        flow_date = flow.get("snapshot_date")
        flow_freshness = _date_freshness(flow_date, business_date, available=flow_available)
        if flow_freshness != "same_date":
            flow_available = False
            flow_date = None
            flow_freshness = "missing"
        missing = list(row.get("missing_information") or [])
        if news_status == "collected_no_match" and "뉴스 수집 완료 · 매칭 없음" not in missing:
            missing.append("뉴스 수집 완료 · 매칭 없음")
        elif news_status == "not_collected" and "뉴스 수집 없음" not in missing:
            missing.append("뉴스 수집 없음")
        if not market_available and "같은 날 Toss 종목 기준값 없음" not in missing:
            missing.append("같은 날 Toss 종목 기준값 없음")
        if not flow_available and "같은 날 Toss 수급 근거 없음" not in missing:
            missing.append("같은 날 Toss 수급 근거 없음")
        if not baseline_available and "Toss 20:00 저장 기준값 없음" not in missing:
            missing.append("Toss 20:00 저장 기준값 없음")

        candidates.append(
            {
                "stock_code": stock_code,
                "stock_name": str(row.get("stock_name") or stock_code or "종목명 미확인"),
                "selected": True,
                "observation_priority": row.get("observation_priority"),
                "why_notable": list(row.get("why_notable") or []),
                "missing_information": missing,
                "evidence_layers": {
                    "primary": list(layers.get("primary") or []),
                    "support": list(layers.get("support") or []),
                    "gap": list(layers.get("gap") or []),
                },
                "report_summary": {
                    "source": "naver_research",
                    "reference_date": business_date.isoformat(),
                    "freshness": "same_date" if int(report.get("report_count") or 0) > 0 else "missing",
                    "report_count": report.get("report_count"),
                    "target_price_min": report.get("target_price_min"),
                    "target_price_max": report.get("target_price_max"),
                    "opinion": report.get("dominant_opinion"),
                },
                "market_reference": _reference_projection(
                    market,
                    source="toss_openapi",
                    business_date=business_date,
                ),
                "news_evidence": {
                    "source": "stored_news_intelligence",
                    "reference_date": business_date.isoformat(),
                    "freshness": "same_date" if news_available else "missing",
                    "status": news_status,
                    "display_label": news.get("display_label") or "자료 없음",
                    "direct_count": int(news.get("direct_count") or 0),
                    "caution_count": int(news.get("caution_count") or 0),
                    "market_context_count": int(news.get("market_context_count") or 0),
                    "observed_at": news.get("observed_at"),
                    "collection_run_count": int(news.get("collection_run_count") or 0),
                    "latest_collection_at": news.get("latest_collection_at"),
                    "evidence_direction": news.get("evidence_direction"),
                },
                "flow_reference": {
                    "source": "toss_openapi",
                    "reference_date": flow_date,
                    "freshness": flow_freshness if flow_freshness != "after_selected_date" else "missing",
                    "status": (
                        "provisional"
                        if flow_available and flow_date == business_date.isoformat()
                        else "missing"
                    ),
                    "provisional": flow_available and flow_date == business_date.isoformat(),
                    "available": flow_available,
                    "individual_net_buy_amount": flow.get("individual_net_buy_amount") if flow_available else None,
                    "foreign_net_buy_amount": flow.get("foreign_net_buy_amount") if flow_available else None,
                    "institution_net_buy_amount": flow.get("institution_net_buy_amount") if flow_available else None,
                    "individual_net_buy_volume": flow.get("individual_net_buy_volume") if flow_available else None,
                    "foreign_net_buy_volume": flow.get("foreign_net_buy_volume") if flow_available else None,
                    "institution_net_buy_volume": flow.get("institution_net_buy_volume") if flow_available else None,
                    "amount_unit": flow.get("amount_unit") if flow_available else None,
                    "volume_unit": flow.get("volume_unit") if flow_available else None,
                },
                "toss_baseline": {
                    "source": "toss_openapi",
                    "reference_date": business_date.isoformat() if baseline_available else None,
                    "freshness": "same_date" if baseline_available else "missing",
                    "status": "available" if baseline_available else "missing",
                    "baseline_time": baseline.get("baseline_time") or "20:00",
                    "reference_time": baseline.get("reference_time"),
                    "last_price": baseline.get("last_price"),
                },
                "newbby_chart_url": build_newbby_chart_url(
                    stock_code,
                    business_date,
                    base_url=newbby_base_url,
                ),
            }
        )

    return {
        "surface": "operator-review",
        "business_date": business_date.isoformat(),
        "source": "selected_date_main_snapshot",
        "selection_basis": candidate_snapshot.get("selection_basis"),
        "available": bool(candidates),
        "read_only": True,
        "live_fetch": False,
        "writes_db": False,
        "scoring": False,
        "recommendation": False,
        "candidates": candidates,
        "empty_state": None if candidates else "선택한 날짜의 저장된 메인 후보가 없습니다.",
    }


def _reference_projection(value: dict, *, source: str, business_date: date) -> dict[str, object]:
    available = value.get("available") is True
    reference_date = value.get("reference_date") or value.get("business_date")
    if not reference_date and available:
        reference_date = business_date.isoformat()
    freshness = _date_freshness(reference_date, business_date, available=available)
    if freshness != "same_date":
        available = False
        reference_date = None
        freshness = "missing"
    return {
        "source": source,
        "reference_date": reference_date,
        "freshness": freshness,
        "status": "available" if available and reference_date == business_date.isoformat() else "missing",
        "available": available,
        "close_price": value.get("close_price") if available else None,
        "change_percent": value.get("change_percent") if available else None,
        "turnover": value.get("turnover") if available else None,
        "fetched_at": value.get("fetched_at") if available else None,
    }


def _date_freshness(reference_date: object, business_date: date, *, available: bool) -> str:
    if not available or not reference_date:
        return "missing"
    if str(reference_date) == business_date.isoformat():
        return "same_date"
    return "prior_date" if str(reference_date) < business_date.isoformat() else "after_selected_date"


def _news_collection_status(news: dict[str, object]) -> str:
    status = news.get("latest_collection_status")
    if status == "matched":
        return "matched"
    if status == "no_match":
        return "collected_no_match"
    if status == "not_collected":
        return "not_collected"
    if news.get("available") is not True:
        return "not_collected"
    evidence_count_keys = (
        "direct_count",
        "caution_count",
        "market_context_count",
        "independent_count",
        "report_recap_count",
        "unknown_count",
    )
    if any(int(news.get(key) or 0) for key in evidence_count_keys):
        return "matched"
    return "collected_no_match"


def build_operator_review_snapshot(
    config,
    business_date: date,
    *,
    newbby_base_url: str = DEFAULT_NEWBBY_BASE_URL,
) -> dict[str, object]:
    repository = _ReadOnlyStockMonitorRepository(config.db_path, timezone=config.timezone)
    return build_operator_review_payload(
        config,
        repository,
        business_date,
        newbby_base_url=newbby_base_url,
    )


def render_operator_review_html(default_date: str | None = None) -> str:
    safe_default_date = escape(default_date or "", quote=True)
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Monitor · Operator Review</title>
  <style>
    :root { color-scheme: dark; font-family: Segoe UI, sans-serif; background: #101722; color: #edf2f7; }
    body { margin: 0; padding: 24px; max-width: 1100px; margin-inline: auto; }
    h1 { font-size: 1.55rem; margin: 0 0 8px; }
    p, small { color: #aab7c7; }
    form { display: flex; gap: 10px; align-items: center; margin: 22px 0; }
    input, button {
      font: inherit; padding: 9px 12px; border-radius: 8px;
      border: 1px solid #34445a; background: #182332; color: inherit;
    }
    button { cursor: pointer; background: #214c67; }
    #status { min-height: 1.5em; }
    .cards { display: grid; gap: 14px; }
    article { border: 1px solid #34445a; border-radius: 12px; padding: 16px; background: #151f2d; }
    article h2 { margin: 0 0 8px; font-size: 1.15rem; }
    .meta { display: flex; gap: 8px; flex-wrap: wrap; color: #aab7c7; font-size: .9rem; }
    section { margin-top: 14px; }
    section h3 { margin: 0 0 6px; font-size: .95rem; color: #9fd5ec; }
    ul { margin: 5px 0 0; padding-left: 20px; }
    li { margin: 4px 0; }
    a { color: #9fd5ec; }
    .empty { border: 1px dashed #526277; border-radius: 10px; padding: 16px; color: #c1cbd8; }
  </style>
</head>
<body>
  <header>
    <h1>종목 근거 검토</h1>
    <p>저장된 Main 후보와 선택일 기준 근거만 표시합니다. 실시간 조회나 저장은 하지 않습니다.</p>
  </header>
  <form id="date-form" method="get" action="/">
    <label for="business-date">기준일</label>
    <input id="business-date" name="date" type="date" value="__DEFAULT_DATE__" required>
    <button type="submit">불러오기</button>
  </form>
  <p id="status" role="status">기준일을 선택하세요.</p>
  <main id="cards" class="cards" aria-live="polite"></main>
  <script>
    const input = document.getElementById('business-date');
    const statusNode = document.getElementById('status');
    const cardsNode = document.getElementById('cards');
    const query = new URLSearchParams(window.location.search);
    const selectedDate = query.get('date') || input.value || '';
    input.value = selectedDate;

    function appendText(parent, tag, text, className) {
      const node = document.createElement(tag);
      node.textContent = text || '자료 없음';
      if (className) node.className = className;
      parent.appendChild(node);
      return node;
    }

    function appendList(parent, title, values) {
      const section = document.createElement('section');
      appendText(section, 'h3', title);
      const items = Array.isArray(values) ? values.filter(Boolean) : [];
      if (!items.length) appendText(section, 'p', '자료 없음');
      else {
        const list = document.createElement('ul');
        items.forEach(value => appendText(list, 'li', String(value)));
        section.appendChild(list);
      }
      parent.appendChild(section);
    }

    function renderCandidate(candidate) {
      const card = document.createElement('article');
      appendText(card, 'h2', `${candidate.stock_name} · ${candidate.stock_code}`);
      appendText(card, 'p', candidate.observation_priority || '관찰 라벨 없음');
      appendText(card, 'p',
        `리포트 ${candidate.report_summary.report_count ?? '자료 없음'}건` +
        ` · 출처 ${candidate.report_summary.source}` +
        ` · ${candidate.report_summary.reference_date} · ${candidate.report_summary.freshness}`,
        'meta');
      appendList(card, '왜 눈에 띄는지', candidate.why_notable);
      appendList(card, '주요 근거', candidate.evidence_layers.primary);
      appendList(card, '보조 근거', candidate.evidence_layers.support);
      appendList(card, '부족한 정보', candidate.missing_information);

      const refs = document.createElement('section');
      appendText(refs, 'h3', '저장 기준값');
      appendText(refs, 'p',
        `Toss 종목 기준값 · ${candidate.market_reference.reference_date || '자료 없음'}` +
        ` · ${candidate.market_reference.freshness} · 종가 ${candidate.market_reference.close_price ?? '자료 없음'}`);
      appendText(refs, 'p',
        `Toss 수급 · ${candidate.flow_reference.reference_date || '자료 없음'}` +
        ` · ${candidate.flow_reference.status} · 잠정 ${candidate.flow_reference.provisional ? '예' : '아니오'}` +
        ` · 외인 ${candidate.flow_reference.foreign_net_buy_amount ?? '자료 없음'}` +
        ` ${candidate.flow_reference.amount_unit || ''}`);
      appendText(refs, 'p',
        `뉴스 근거 · ${candidate.news_evidence.reference_date} · ${candidate.news_evidence.status}` +
        ` · 직접 ${candidate.news_evidence.direct_count}, 주의 ${candidate.news_evidence.caution_count}` +
        `, 시장맥락 ${candidate.news_evidence.market_context_count}` +
        ` · 최근 수집 ${candidate.news_evidence.latest_collection_at || '없음'}`);
      appendText(refs, 'p',
        `Toss 20:00 기준값 · ${candidate.toss_baseline.reference_date || '자료 없음'}` +
        ` · ${candidate.toss_baseline.freshness} · 가격 ${candidate.toss_baseline.last_price ?? '자료 없음'}`);
      card.appendChild(refs);

      if (candidate.newbby_chart_url) {
        const link = document.createElement('a');
        link.href = candidate.newbby_chart_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Stock-Newbby 차트 확인';
        card.appendChild(link);
      }
      return card;
    }

    async function loadReview() {
      if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(selectedDate)) return;
      statusNode.textContent = `${selectedDate} 저장 근거를 읽는 중…`;
      try {
        const params = new URLSearchParams({date: selectedDate});
        const response = await fetch(`/api/operator-review?${params}`, {
          headers: {Accept: 'application/json'}
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '저장 자료를 읽을 수 없습니다.');
        cardsNode.replaceChildren();
        if (!payload.candidates.length) appendText(cardsNode, 'p', payload.empty_state, 'empty');
        else payload.candidates.forEach(candidate => cardsNode.appendChild(renderCandidate(candidate)));
        statusNode.textContent = `${payload.business_date} · ${payload.source} · 읽기 전용`;
      } catch (error) {
        cardsNode.replaceChildren();
        statusNode.textContent = error.message || '저장 자료를 읽을 수 없습니다.';
      }
    }
    if (selectedDate) loadReview();
    else statusNode.textContent = '저장된 기준일이 없습니다. 데이터를 수집하거나 기준일을 선택하세요.';
  </script>
</body>
</html>""".replace("__DEFAULT_DATE__", safe_default_date)


def _json_response(status: HTTPStatus, payload: dict[str, object]) -> tuple[HTTPStatus, str, bytes]:
    return status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _route_operator_review_request(
    method: str,
    target: str,
    config,
    *,
    newbby_base_url: str = DEFAULT_NEWBBY_BASE_URL,
) -> tuple[HTTPStatus, str, bytes]:
    if method != "GET":
        return _json_response(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
    parsed = urlsplit(target)
    if parsed.path == OPERATOR_REVIEW_PAGE_PATH:
        requested_dates = parse_qs(parsed.query, keep_blank_values=True).get("date", [])
        selected_date = requested_dates[0] if len(requested_dates) == 1 else None
        if not requested_dates:
            try:
                selected_date = _latest_stored_business_date(config)
            except (OSError, sqlite3.Error, RuntimeError):
                selected_date = None
        elif not _valid_iso_date(str(selected_date or "")):
            selected_date = None
        return (
            HTTPStatus.OK,
            "text/html; charset=utf-8",
            render_operator_review_html(selected_date).encode("utf-8"),
        )
    if parsed.path != OPERATOR_REVIEW_API_PATH:
        return _json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
    query = parse_qs(parsed.query, keep_blank_values=True)
    dates = query.get("date", [])
    if len(dates) != 1 or not _valid_iso_date(dates[0]):
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "expected_date_yyyy_mm_dd"})
    business_date = date.fromisoformat(dates[0])
    try:
        payload = build_operator_review_snapshot(
            config,
            business_date,
            newbby_base_url=newbby_base_url,
        )
    except (OSError, sqlite3.Error, RuntimeError):
        return _json_response(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "stored_review_data_unavailable"})
    return _json_response(HTTPStatus.OK, payload)


def _valid_iso_date(value: str) -> bool:
    if not _DATE_PATTERN.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _latest_stored_business_date(config) -> str | None:
    from stock_monitor.cli import build_web_view_archive_snapshot

    repository = _ReadOnlyStockMonitorRepository(config.db_path, timezone=config.timezone)
    archive = build_web_view_archive_snapshot(config, repository, limit=1)
    latest_date = archive.get("latest_business_date")
    return str(latest_date) if latest_date and _valid_iso_date(str(latest_date)) else None


def _make_operator_review_handler(config, *, newbby_base_url: str = DEFAULT_NEWBBY_BASE_URL):
    _validated_newbby_base_url(newbby_base_url)

    class OperatorReviewHandler(BaseHTTPRequestHandler):
        server_version = "StockMonitorOperatorReview/1.0"

        def _respond(self, status: HTTPStatus, content_type: str, body: bytes, *, allow: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            if allow:
                self.send_header("Allow", allow)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            status, content_type, body = _route_operator_review_request(
                "GET",
                self.path,
                config,
                newbby_base_url=newbby_base_url,
            )
            self._respond(status, content_type, body)

        def do_POST(self) -> None:
            status, content_type, body = _route_operator_review_request("POST", self.path, config)
            self._respond(status, content_type, body, allow="GET")

        def log_message(self, format: str, *args) -> None:
            return

    return OperatorReviewHandler


def create_operator_review_server(
    config,
    *,
    port: int = DEFAULT_OPERATOR_REVIEW_PORT,
    newbby_base_url: str = DEFAULT_NEWBBY_BASE_URL,
) -> ThreadingHTTPServer:
    if not 1 <= int(port) <= 65535:
        raise ValueError("operator-review port must be between 1 and 65535")
    handler = _make_operator_review_handler(config, newbby_base_url=newbby_base_url)
    return ThreadingHTTPServer((DEFAULT_OPERATOR_REVIEW_HOST, int(port)), handler)
