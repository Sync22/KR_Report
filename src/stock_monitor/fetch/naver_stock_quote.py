from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib import error, request


@dataclass(frozen=True)
class StockQuoteSnapshot:
    stock_code: str
    stock_name: str | None
    sector_code: str | None
    sector_name: str | None
    current_price: int | None
    market_status: str | None
    trade_time: datetime | None
    prev_close_price: int | None
    prev_change_price: int | None = None
    prev_change_rate: float | None = None
    trade_amount: int | None = None
    trade_volume: int | None = None


@dataclass(frozen=True)
class NaverMarketTopStock:
    market: str
    sort_type: str | None
    stock_code: str
    stock_name: str | None
    stock_end_type: str | None
    current_price: int | None
    change_price: int | None
    change_percent: float | None
    trade_amount: int | None
    trade_volume: int | None
    market_status: str | None
    trade_time: datetime | None


def fetch_stock_quote_snapshot(
    stock_code: str,
    *,
    timeout_seconds: float = 30,
) -> StockQuoteSnapshot:
    normalized_stock_code = stock_code.strip().upper()
    url = f"https://stock.naver.com/api/domestic/detail/{normalized_stock_code}/detail?codeType=KRX"
    http_request = request.Request(url, headers={"User-Agent": "stock-monitor/0.1"})
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch stock quote data: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Failed to fetch stock quote data: unexpected response shape.")

    trade_time_raw = str(payload.get("tradeTime") or "").strip()
    trade_time = None
    if trade_time_raw:
        try:
            trade_time = datetime.strptime(trade_time_raw, "%Y%m%d%H%M%S")
        except ValueError:
            trade_time = None

    return StockQuoteSnapshot(
        stock_code=normalized_stock_code,
        stock_name=str(payload.get("itemname") or "").strip() or None,
        sector_code=str(payload.get("upjongCode") or "").strip() or None,
        sector_name=str(payload.get("upJongName") or "").strip() or None,
        current_price=_parse_int(payload.get("nowPrice")),
        market_status=str(payload.get("marketStatus") or "").strip() or None,
        trade_time=trade_time,
        prev_close_price=_parse_int(payload.get("prevClosePrice")),
        prev_change_price=_parse_int(payload.get("prevChangePrice")),
        prev_change_rate=_parse_float(payload.get("prevChangeRate")),
        trade_amount=_parse_int(payload.get("tradeAmount")),
        trade_volume=_parse_int(payload.get("tradeVolume")),
    )


def fetch_market_top_stocks(
    market: str,
    *,
    page: int = 1,
    page_size: int = 20,
    timeout_seconds: float = 30,
) -> list[NaverMarketTopStock]:
    normalized_market = market.strip().upper()
    if normalized_market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError("market must be KOSPI or KOSDAQ")
    normalized_page = max(int(page), 1)
    normalized_page_size = max(int(page_size), 1)
    url = (
        f"https://m.stock.naver.com/api/stocks/priceTop/{normalized_market}"
        f"?page={normalized_page}&pageSize={normalized_page_size}"
    )
    http_request = request.Request(url, headers={"User-Agent": "stock-monitor/0.1"})
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch Naver market top data: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Failed to fetch Naver market top data: unexpected response shape.")
    rows = payload.get("stocks")
    if not isinstance(rows, list):
        raise RuntimeError("Failed to fetch Naver market top data: missing stocks.")

    sort_type = str(payload.get("stockListSortType") or "").strip() or None
    items: list[NaverMarketTopStock] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stock_code = str(row.get("itemCode") or "").strip()
        if not stock_code:
            continue
        items.append(
            NaverMarketTopStock(
                market=normalized_market,
                sort_type=sort_type,
                stock_code=stock_code,
                stock_name=str(row.get("stockName") or "").strip() or None,
                stock_end_type=str(row.get("stockEndType") or "").strip() or None,
                current_price=_parse_int(row.get("closePriceRaw") or row.get("closePrice")),
                change_price=_parse_int(
                    row.get("compareToPreviousClosePriceRaw") or row.get("compareToPreviousClosePrice")
                ),
                change_percent=_parse_float(row.get("fluctuationsRatio")),
                trade_amount=_parse_int(
                    row.get("accumulatedTradingValueRaw") or row.get("accumulatedTradingValue")
                ),
                trade_volume=_parse_int(
                    row.get("accumulatedTradingVolumeRaw") or row.get("accumulatedTradingVolume")
                ),
                market_status=str(row.get("marketStatus") or "").strip() or None,
                trade_time=_parse_naver_market_time(row.get("localTradedAt")),
            )
        )
    return items


def _parse_int(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def _parse_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _parse_naver_market_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return None
