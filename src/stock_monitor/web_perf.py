from __future__ import annotations

import gzip as gzip_module
import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

try:  # pragma: no cover - optional runtime optimization
    import orjson  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - depends on operator environment
    orjson = None  # type: ignore[assignment]


GZIP_MIN_BYTES = 16 * 1024
API_PERF_LOG_MAX_BYTES = 10 * 1024 * 1024
API_PERF_LOG_BACKUP_COUNT = 10
_KST = ZoneInfo("Asia/Seoul")
_CURRENT_REQUEST_METRICS: ContextVar["RequestMetrics | None"] = ContextVar(
    "stock_monitor_current_request_metrics",
    default=None,
)


@dataclass
class RequestMetrics:
    db_ms: float = 0.0
    build_ms: float = 0.0
    json_ms: float = 0.0
    total_ms: float = 0.0
    response_bytes: int = 0
    cache_hit: bool = False
    gzip: bool = False


class ApiPerfLogger:
    def __init__(
        self,
        log_dir: Path,
        *,
        filename: str = "api_perf.log",
        max_bytes: int = API_PERF_LOG_MAX_BYTES,
        backup_count: int = API_PERF_LOG_BACKUP_COUNT,
    ) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / filename
        self._logger = logging.getLogger(f"stock_monitor.api_perf.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        handler = RotatingFileHandler(
            self.path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

    def log(
        self,
        *,
        method: str,
        path: str,
        status: int,
        total_ms: float,
        db_ms: float,
        build_ms: float,
        json_ms: float,
        response_bytes: int,
        cache: str,
        gzip_used: bool,
    ) -> None:
        record = {
            "ts": datetime.now(_KST).isoformat(timespec="seconds"),
            "method": method,
            "path": path,
            "status": status,
            "total_ms": round(total_ms, 3),
            "db_ms": round(db_ms, 3),
            "build_ms": round(build_ms, 3),
            "json_ms": round(json_ms, 3),
            "bytes": response_bytes,
            "cache": cache,
            "gzip": gzip_used,
        }
        self._logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))


def json_dumps_bytes(payload: Any) -> bytes:
    if orjson is not None:
        return orjson.dumps(payload)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def maybe_gzip(body: bytes, accept_encoding: str | None) -> tuple[bytes, bool]:
    if len(body) < GZIP_MIN_BYTES:
        return body, False
    if "gzip" not in (accept_encoding or "").lower():
        return body, False
    return gzip_module.compress(body, compresslevel=3), True


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


@contextmanager
def request_metrics_context(metrics: RequestMetrics) -> Iterator[RequestMetrics]:
    token = _CURRENT_REQUEST_METRICS.set(metrics)
    try:
        yield metrics
    finally:
        _CURRENT_REQUEST_METRICS.reset(token)


def record_db_elapsed(db_ms: float) -> None:
    metrics = _CURRENT_REQUEST_METRICS.get()
    if metrics is None:
        return
    metrics.db_ms += db_ms


def summarize_api_perf_log(log_path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    if not log_path.exists():
        return {
            "surface": "api-perf-summary",
            "log_path": str(log_path),
            "record_count": 0,
            "endpoint_count": 0,
            "endpoints": [],
        }
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        path = str(record.get("path") or "")
        if not path:
            continue
        grouped[path].append(record)

    endpoints = [_summarize_api_perf_endpoint(path, rows) for path, rows in grouped.items()]
    endpoints.sort(key=lambda item: (float(item["p95_total_ms"]), int(item["count"])), reverse=True)
    return {
        "surface": "api-perf-summary",
        "log_path": str(log_path),
        "record_count": len(records),
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
    }


def _summarize_api_perf_endpoint(path: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_values = _numeric_values(rows, "total_ms")
    db_values = _numeric_values(rows, "db_ms")
    build_values = _numeric_values(rows, "build_ms")
    json_values = _numeric_values(rows, "json_ms")
    byte_values = _numeric_values(rows, "bytes")
    return {
        "path": path,
        "count": len(rows),
        "status_codes": sorted({int(row.get("status") or 0) for row in rows}),
        "cache_hits": sum(1 for row in rows if row.get("cache") == "hit"),
        "cache_misses": sum(1 for row in rows if row.get("cache") == "miss"),
        "gzip_count": sum(1 for row in rows if bool(row.get("gzip"))),
        "p50_total_ms": _percentile(total_values, 50),
        "p95_total_ms": _percentile(total_values, 95),
        "p99_total_ms": _percentile(total_values, 99),
        "max_total_ms": max(total_values) if total_values else 0.0,
        "avg_db_ms": _average(db_values),
        "avg_build_ms": _average(build_values),
        "avg_json_ms": _average(json_values),
        "max_bytes": int(max(byte_values)) if byte_values else 0,
    }


def _numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        try:
            values.append(float(row.get(key) or 0))
        except (TypeError, ValueError):
            continue
    return sorted(values)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = max(1, int((percentile / 100) * len(sorted_values) + 0.999999))
    return round(sorted_values[min(rank - 1, len(sorted_values) - 1)], 3)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)
