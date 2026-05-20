from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from urllib import error, request

from stock_monitor.models import StockResearchEntry, normalize_opinion, parse_target_price


@dataclass(frozen=True)
class StockResearchLookupResult:
    stock_code: str
    stock_name: str | None
    as_of_date: date
    lookback_days: int
    entries: tuple[StockResearchEntry, ...]


def fetch_stock_research_entries(
    stock_code: str,
    *,
    as_of_date: date,
    lookback_days: int = 15,
    page_size: int = 20,
    max_pages: int = 5,
    timeout_seconds: float = 30,
) -> StockResearchLookupResult:
    normalized_stock_code = stock_code.strip().upper()
    cutoff_date = as_of_date - timedelta(days=lookback_days)
    entries: list[StockResearchEntry] = []
    stock_name: str | None = None

    for page in range(max_pages):
        url = (
            f"https://stock.naver.com/api/domestic/research/{normalized_stock_code}/research"
            f"?page={page}&size={page_size}"
        )
        payload = _load_json(url, timeout_seconds=timeout_seconds)
        if not isinstance(payload, list) or not payload:
            break

        page_entries = [_parse_entry(item) for item in payload]
        parsed_entries = [entry for entry in page_entries if entry is not None]
        if not parsed_entries:
            break

        if stock_name is None and parsed_entries:
            stock_name = parsed_entries[0].stock_name

        within_window = [entry for entry in parsed_entries if entry.write_date >= cutoff_date]
        entries.extend(within_window)

        oldest_page_date = min(entry.write_date for entry in parsed_entries)
        if oldest_page_date < cutoff_date:
            break
        if len(parsed_entries) < page_size:
            break

    ordered = tuple(sorted(entries, key=lambda item: (item.write_date, item.source_id or ""), reverse=True))
    return StockResearchLookupResult(
        stock_code=normalized_stock_code,
        stock_name=stock_name,
        as_of_date=as_of_date,
        lookback_days=lookback_days,
        entries=ordered,
    )


def _load_json(url: str, *, timeout_seconds: float) -> object:
    http_request = request.Request(url, headers={"User-Agent": "stock-monitor/0.1"})
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch stock research data: {exc}") from exc


def _parse_entry(item: object) -> StockResearchEntry | None:
    if not isinstance(item, dict):
        return None
    stock_code = str(item.get("itemcode") or "").strip()
    stock_name = str(item.get("itemname") or "").strip()
    broker_name = str(item.get("brokerName") or "").strip()
    title = str(item.get("title") or "").strip()
    write_date_raw = str(item.get("writeDate") or "").strip()
    if not all([stock_code, stock_name, broker_name, title, write_date_raw]):
        return None

    source_id = str(item.get("nid") or "").strip() or None
    source_url = (
        f"https://stock.naver.com/domestic/stock/{stock_code}/research/{source_id}"
        if source_id
        else None
    )
    target_price_raw = str(item.get("goalPrice") or "").strip() or None
    opinion_raw = str(item.get("opinion") or "").strip() or None
    return StockResearchEntry(
        stock_name=stock_name,
        stock_code=stock_code,
        broker_name=broker_name,
        title=title,
        write_date=date.fromisoformat(write_date_raw),
        target_price_value=parse_target_price(target_price_raw),
        opinion_normalized=normalize_opinion(opinion_raw),
        source_url=source_url,
        source_id=source_id,
    )
