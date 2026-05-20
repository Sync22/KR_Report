from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, parse, request


@dataclass(frozen=True)
class StockCodeLookupEntry:
    stock_code: str
    stock_name: str
    market_type: str
    source_url: str


def fetch_stock_code_candidates(
    query: str,
    *,
    timeout_seconds: float = 30,
    limit: int = 5,
) -> list[StockCodeLookupEntry]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    url = "https://stock.naver.com/api/autocomplete/search/autoComplete?" + parse.urlencode(
        {
            "query": normalized_query,
            "target": "stock,index,marketindicator,coin,ipo",
        },
        encoding="utf-8",
        errors="strict",
    )
    req = request.Request(url, headers={"User-Agent": "stock-monitor/0.1"})
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch stock code candidates: {exc}") from exc

    items = payload.get("result", {}).get("items", [])
    candidates: list[StockCodeLookupEntry] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("category") != "stock":
            continue
        stock_code = str(item.get("code") or "").strip()
        stock_name = str(item.get("name") or "").strip()
        market_type = str(item.get("typeName") or "").strip()
        url_path = str(item.get("url") or "").strip()
        if not stock_code or not stock_name or not url_path:
            continue
        key = (stock_code, stock_name)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            StockCodeLookupEntry(
                stock_code=stock_code,
                stock_name=stock_name,
                market_type=market_type,
                source_url=f"https://stock.naver.com{url_path}",
            )
        )
        if len(candidates) >= limit:
            break
    return candidates
