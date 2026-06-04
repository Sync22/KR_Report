import gzip
import json

from stock_monitor.web_perf import (
    ApiPerfLogger,
    RequestMetrics,
    json_dumps_bytes,
    maybe_gzip,
    record_db_elapsed,
    request_metrics_context,
    summarize_api_perf_log,
)


def test_json_dumps_bytes_returns_compact_utf8_bytes() -> None:
    body = json_dumps_bytes({"stock": "삼성전자", "items": [1, 2]})

    assert isinstance(body, bytes)
    assert body == '{"stock":"삼성전자","items":[1,2]}'.encode("utf-8")


def test_maybe_gzip_only_compresses_large_accepted_payloads() -> None:
    small_body = b"x" * 100
    large_body = b"x" * 17_000

    assert maybe_gzip(small_body, "gzip") == (small_body, False)
    assert maybe_gzip(large_body, "") == (large_body, False)

    compressed, used_gzip = maybe_gzip(large_body, "br, gzip")

    assert used_gzip is True
    assert gzip.decompress(compressed) == large_body


def test_api_perf_logger_writes_jsonl_record(tmp_path) -> None:
    logger = ApiPerfLogger(tmp_path)

    logger.log(
        method="GET",
        path="/api/daily/latest",
        status=200,
        total_ms=12.3,
        db_ms=4.5,
        build_ms=6.7,
        json_ms=1.2,
        response_bytes=3456,
        cache="miss",
        gzip_used=True,
    )

    lines = (tmp_path / "api_perf.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["method"] == "GET"
    assert record["path"] == "/api/daily/latest"
    assert record["status"] == 200
    assert record["total_ms"] == 12.3
    assert record["db_ms"] == 4.5
    assert record["build_ms"] == 6.7
    assert record["json_ms"] == 1.2
    assert record["bytes"] == 3456
    assert record["cache"] == "miss"
    assert record["gzip"] is True
    assert "ts" in record


def test_request_metrics_context_accumulates_db_time_only_inside_context() -> None:
    metrics = RequestMetrics()

    record_db_elapsed(5.0)
    with request_metrics_context(metrics):
        record_db_elapsed(3.25)
        record_db_elapsed(1.75)
    record_db_elapsed(9.0)

    assert metrics.db_ms == 5.0


def test_summarize_api_perf_log_groups_endpoint_percentiles(tmp_path) -> None:
    log_path = tmp_path / "api_perf.log"
    log_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-05-20T10:00:00+09:00","method":"GET","path":"/api/daily/2026-05-19","status":200,"total_ms":100,"db_ms":60,"build_ms":80,"json_ms":10,"bytes":1000,"cache":"miss","gzip":false}',
                '{"ts":"2026-05-20T10:01:00+09:00","method":"GET","path":"/api/daily/2026-05-19","status":200,"total_ms":20,"db_ms":0,"build_ms":0,"json_ms":0,"bytes":1000,"cache":"hit","gzip":false}',
                '{"ts":"2026-05-20T10:01:30+09:00","method":"GET","path":"/api/daily/2026-05-19?intraday_market_top=1&market_top_limit=100","status":200,"total_ms":300,"db_ms":30,"build_ms":250,"json_ms":12,"bytes":1200,"cache":"miss","gzip":false}',
                '{"ts":"2026-05-20T10:02:00+09:00","method":"GET","path":"/api/market","status":200,"total_ms":50,"db_ms":30,"build_ms":40,"json_ms":5,"bytes":500,"cache":"miss","gzip":true}',
            ]
        ),
        encoding="utf-8",
    )

    summary = summarize_api_perf_log(log_path)

    assert summary["record_count"] == 4
    assert summary["endpoint_count"] == 3
    daily = next(item for item in summary["endpoints"] if item["path"] == "/api/daily/2026-05-19")
    assert daily["count"] == 2
    assert daily["path_family"] == "/api/daily/{date}"
    assert daily["cache_hits"] == 1
    assert daily["cache_misses"] == 1
    assert daily["p50_total_ms"] == 20.0
    assert daily["p95_total_ms"] == 100.0
    intraday = next(
        item
        for item in summary["endpoints"]
        if item["path"] == "/api/daily/2026-05-19?intraday_market_top=1&market_top_limit=100"
    )
    assert intraday["path_family"] == "/api/daily/{date}?intraday_market_top=1"
