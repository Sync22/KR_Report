from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib import error, parse, request

from stock_monitor.models import StockMetadata, StockThemeMembership


@dataclass(frozen=True)
class NaverThemeFetchResult:
    theme_code: str
    theme_name: str
    memberships: tuple[StockThemeMembership, ...]


@dataclass(frozen=True)
class NaverIndustryFetchResult:
    industry_code: str
    industry_name: str
    metadata_items: tuple[StockMetadata, ...]


@dataclass(frozen=True)
class NaverIndustryCatalogItem:
    industry_code: str
    industry_name: str
    stock_count: int


def fetch_stock_theme_memberships(
    theme_code: str,
    *,
    timeout_seconds: float = 30,
    page_size: int = 50,
    max_pages: int = 10,
    fetched_at: datetime | None = None,
) -> NaverThemeFetchResult:
    normalized_theme_code = theme_code.strip()
    if not normalized_theme_code:
        raise ValueError("theme_code is required.")
    safe_page_size = min(max(page_size, 1), 50)

    fetched_time = fetched_at or datetime.now()
    memberships: list[StockThemeMembership] = []
    theme_name = ""

    for page in range(1, max_pages + 1):
        payload = _fetch_sector_page(
            normalized_theme_code,
            sector_type="theme",
            page=page,
            page_size=safe_page_size,
            timeout_seconds=timeout_seconds,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Failed to fetch theme memberships: unexpected response shape.")

        theme_name = str(result.get("sectorName") or theme_name or normalized_theme_code).strip()
        items = result.get("items")
        if not isinstance(items, list):
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            stock_code = str(item.get("id") or item.get("itemCode") or "").strip()
            if not stock_code:
                continue
            memberships.append(
                StockThemeMembership(
                    theme_code=normalized_theme_code,
                    theme_name=theme_name or normalized_theme_code,
                    stock_code=stock_code,
                    stock_name=str(item.get("name") or "").strip() or None,
                    updated_at=fetched_time,
                    source="naver_theme",
                )
            )

        total_count = _safe_int(result.get("risingCount")) + _safe_int(result.get("unChangedCount")) + _safe_int(result.get("fallingCount"))
        if len(memberships) >= total_count or len(items) < safe_page_size:
            break

    return NaverThemeFetchResult(
        theme_code=normalized_theme_code,
        theme_name=theme_name or normalized_theme_code,
        memberships=tuple(memberships),
    )


def fetch_stock_industry_memberships(
    industry_code: str,
    *,
    timeout_seconds: float = 30,
    page_size: int = 50,
    max_pages: int = 10,
    fetched_at: datetime | None = None,
) -> NaverIndustryFetchResult:
    normalized_industry_code = industry_code.strip()
    if not normalized_industry_code:
        raise ValueError("industry_code is required.")
    safe_page_size = min(max(page_size, 1), 50)

    try:
        return _fetch_stock_industry_memberships_legacy(
            normalized_industry_code,
            timeout_seconds=timeout_seconds,
            page_size=safe_page_size,
            max_pages=max_pages,
            fetched_at=fetched_at,
        )
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
        return _fetch_stock_industry_memberships_current(
            normalized_industry_code,
            timeout_seconds=timeout_seconds,
            page_size=safe_page_size,
            max_pages=max_pages,
            fetched_at=fetched_at,
        )


def _fetch_stock_industry_memberships_legacy(
    normalized_industry_code: str,
    *,
    timeout_seconds: float,
    page_size: int,
    max_pages: int,
    fetched_at: datetime | None,
) -> NaverIndustryFetchResult:
    safe_page_size = min(max(page_size, 1), 50)

    fetched_time = fetched_at or datetime.now()
    metadata_items: list[StockMetadata] = []
    industry_name = ""

    for page in range(1, max_pages + 1):
        payload = _fetch_sector_page(
            normalized_industry_code,
            sector_type="industry",
            page=page,
            page_size=safe_page_size,
            timeout_seconds=timeout_seconds,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Failed to fetch industry memberships: unexpected response shape.")

        industry_name = str(result.get("sectorName") or industry_name or normalized_industry_code).strip()
        items = result.get("items")
        if not isinstance(items, list):
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            stock_code = str(item.get("id") or item.get("itemCode") or "").strip()
            if not stock_code:
                continue
            metadata_items.append(
                StockMetadata(
                    stock_code=stock_code,
                    stock_name=str(item.get("name") or "").strip() or None,
                    sector_code=normalized_industry_code,
                    sector_name=industry_name or normalized_industry_code,
                    updated_at=fetched_time,
                    source="naver_industry",
                )
            )

        total_count = _safe_int(result.get("risingCount")) + _safe_int(result.get("unChangedCount")) + _safe_int(result.get("fallingCount"))
        if len(metadata_items) >= total_count or len(items) < safe_page_size:
            break

    return NaverIndustryFetchResult(
        industry_code=normalized_industry_code,
        industry_name=industry_name or normalized_industry_code,
        metadata_items=tuple(metadata_items),
    )


def fetch_stock_industry_catalog(
    *,
    timeout_seconds: float = 30,
    page_size: int = 100,
    max_pages: int = 1,
) -> tuple[NaverIndustryCatalogItem, ...]:
    safe_page_size = min(max(page_size, 1), 100)
    items: list[NaverIndustryCatalogItem] = []
    for page in range(1, max_pages + 1):
        start_idx = (page - 1) * safe_page_size
        query = parse.urlencode(
            {
                "startIdx": start_idx,
                "pageSize": safe_page_size,
                "sortType": "changeRate",
            }
        )
        url = f"https://stock.naver.com/api/domestic/market/upjong/list?{query}"
        payload = _fetch_current_upjong_json(url, industry_code="catalog", timeout_seconds=timeout_seconds)
        if not isinstance(payload, list):
            raise RuntimeError("Failed to fetch industry catalog: unexpected current upjong list shape.")
        for item in payload:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "").strip() != "upjong":
                continue
            industry_code = str(item.get("no") or "").strip()
            industry_name = str(item.get("name") or "").strip()
            if not industry_code or not industry_name:
                continue
            items.append(
                NaverIndustryCatalogItem(
                    industry_code=industry_code,
                    industry_name=industry_name,
                    stock_count=_safe_int(item.get("totalCnt")),
                )
            )
        if len(payload) < safe_page_size:
            break
    return tuple(items)


def _fetch_stock_industry_memberships_current(
    normalized_industry_code: str,
    *,
    timeout_seconds: float,
    page_size: int,
    max_pages: int,
    fetched_at: datetime | None,
) -> NaverIndustryFetchResult:
    safe_page_size = min(max(page_size, 1), 100)
    fetched_time = fetched_at or datetime.now()
    info_payload = _fetch_current_upjong_json(
        f"https://stock.naver.com/api/domestic/market/upjong/{parse.quote(normalized_industry_code)}/info?marketType=ALL",
        industry_code=normalized_industry_code,
        timeout_seconds=timeout_seconds,
    )
    industry_name = str(info_payload.get("name") or normalized_industry_code).strip()
    metadata_items: list[StockMetadata] = []

    for page in range(1, max_pages + 1):
        start_idx = (page - 1) * safe_page_size
        query = parse.urlencode(
            {
                "marketType": "ALL",
                "orderType": "priceTop",
                "startIdx": start_idx,
                "pageSize": safe_page_size,
            }
        )
        items_payload = _fetch_current_upjong_json(
            f"https://stock.naver.com/api/domestic/market/upjong/{parse.quote(normalized_industry_code)}/stocklist?{query}",
            industry_code=normalized_industry_code,
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(items_payload, list):
            raise RuntimeError("Failed to fetch industry memberships: unexpected current upjong stocklist shape.")
        for item in items_payload:
            if not isinstance(item, dict):
                continue
            stock_code = str(item.get("itemcode") or item.get("itemCode") or "").strip()
            if not stock_code:
                continue
            metadata_items.append(
                StockMetadata(
                    stock_code=stock_code,
                    stock_name=str(item.get("itemname") or item.get("itemName") or "").strip() or None,
                    sector_code=normalized_industry_code,
                    sector_name=industry_name or normalized_industry_code,
                    updated_at=fetched_time,
                    source="naver_industry",
                )
            )
        if len(items_payload) < safe_page_size:
            break

    return NaverIndustryFetchResult(
        industry_code=normalized_industry_code,
        industry_name=industry_name or normalized_industry_code,
        metadata_items=tuple(metadata_items),
    )


def _fetch_current_upjong_json(url: str, *, industry_code: str, timeout_seconds: float) -> object:
    http_request = request.Request(
        url,
        headers={
            "User-Agent": "stock-monitor/0.1",
            "Referer": f"https://stock.naver.com/market/stock/kr/industry/1?no={industry_code}",
        },
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch industry memberships: {exc}") from exc


def _fetch_sector_page(
    theme_code: str,
    *,
    sector_type: str,
    page: int,
    page_size: int,
    timeout_seconds: float,
) -> dict:
    if sector_type not in {"theme", "industry"}:
        raise ValueError(f"Unsupported Naver sector type: {sector_type}")
    api_sector_type = "upjong" if sector_type == "industry" else sector_type
    query = parse.urlencode(
        {
            "sectorCode": theme_code,
            "sectorType": api_sector_type,
            "page": page,
            "pageSize": page_size,
            "sectorSortType": "CHANGE_RATE",
        }
    )
    url = f"https://m.stock.naver.com/front-api/domestic/sector/item/list?{query}"
    http_request = request.Request(
        url,
        headers={
            "User-Agent": "stock-monitor/0.1",
            "Referer": f"https://m.stock.naver.com/domestic/home/{sector_type}/{theme_code}",
        },
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch {sector_type} memberships: {exc}") from exc

    if not isinstance(payload, dict) or not payload.get("isSuccess"):
        raise RuntimeError(f"Failed to fetch {sector_type} memberships: unsuccessful response.")
    return payload


def _safe_int(value: object) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0
