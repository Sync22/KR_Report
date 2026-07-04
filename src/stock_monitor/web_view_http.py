from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib import parse as url_parse


def query_int(query: str, name: str, *, default: int, minimum: int, maximum: int) -> int:
    params = url_parse.parse_qs(query)
    raw = params.get(name, [None])[0]
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def discard_http_request_body(handler: BaseHTTPRequestHandler) -> None:
    try:
        content_length = int(handler.headers.get("Content-Length") or "0")
    except ValueError:
        return
    if content_length <= 0:
        return
    try:
        handler.rfile.read(content_length)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        return


def write_http_response(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    body: str,
    *,
    content_type: str,
    headers: dict[str, str] | None = None,
) -> None:
    encoded = body.encode("utf-8")
    write_binary_http_response(handler, status, encoded, content_type=content_type, headers=headers)


def write_binary_http_response(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    body: bytes,
    *,
    content_type: str,
    headers: dict[str, str] | None = None,
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        return
