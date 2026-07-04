from __future__ import annotations

import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


def create_web_view_server(
    config: Any,
    repository: Any,
    *,
    host: str,
    port: int,
    limit: int,
    make_handler: Callable[..., type[BaseHTTPRequestHandler]],
    allow_non_loopback: bool = False,
    toss_quote_provider: Any = None,
) -> ThreadingHTTPServer:
    _validate_web_view_host(host, allow_non_loopback=allow_non_loopback)
    repository.enable_wal_mode()
    handler = make_handler(config, repository, limit=limit, toss_quote_provider=toss_quote_provider)
    return ThreadingHTTPServer((host, port), handler)


def _validate_web_view_host(host: str, *, allow_non_loopback: bool = False) -> None:
    if allow_non_loopback or _is_loopback_web_view_host(host):
        return
    raise ValueError(
        "web-view refuses non-loopback host by default. "
        "Use --host 127.0.0.1 and tunnel that local port; pass --allow-non-loopback only on a trusted private network."
    )


def _is_loopback_web_view_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False
