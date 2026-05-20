from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from stock_monitor.business_day import derive_business_date
from stock_monitor.config import RuntimeConfig
from stock_monitor.models import Report, collapse_whitespace, normalize_opinion, parse_target_price


@dataclass(frozen=True)
class CandidateRow:
    selector: str
    text: str
    href: str | None
    cells: tuple[str, ...]


@dataclass(frozen=True)
class PageInspection:
    url: str
    title: str
    tab_clicked: bool
    network_urls: tuple[str, ...]
    api_pages_fetched: int
    api_items: tuple[dict[str, Any], ...]
    candidate_rows: tuple[CandidateRow, ...]


def inspect_company_page(
    config: RuntimeConfig,
    *,
    limit: int = 10,
    headless: bool | None = None,
    api_max_pages: int | None = None,
    page_delay_seconds: float = 0,
) -> PageInspection:
    return asyncio.run(
        _inspect_company_page_async(
            config,
            limit=limit,
            headless=config.headless if headless is None else headless,
            api_max_pages=api_max_pages,
            page_delay_seconds=page_delay_seconds,
        )
    )


def fetch_reports(
    config: RuntimeConfig,
    *,
    limit: int | None = None,
    headless: bool | None = None,
    api_max_pages: int | None = None,
    page_delay_seconds: float = 0,
) -> tuple[list[Report], PageInspection]:
    inspection = inspect_company_page(
        config,
        limit=limit or 50,
        headless=headless,
        api_max_pages=api_max_pages,
        page_delay_seconds=page_delay_seconds,
    )
    collected_at = datetime.now(ZoneInfo(config.timezone))
    reports: list[Report] = []
    for item in inspection.api_items:
        parsed = _parse_api_item(item, collected_at, config.timezone, config.holiday_overrides)
        if parsed is not None:
            reports.append(parsed)

    if reports:
        return reports[:limit] if limit is not None else reports, inspection

    for candidate in inspection.candidate_rows:
        parsed = _parse_candidate_row(candidate, collected_at, config.timezone, config.holiday_overrides)
        if parsed is not None:
            reports.append(parsed)
    return reports, inspection


def inspection_to_fixture_payload(
    inspection: PageInspection,
    *,
    collected_at: datetime,
    timezone: str,
) -> dict[str, Any]:
    return {
        "schema": "naver_research_inspection_fixture_v1",
        "url": inspection.url,
        "title": inspection.title,
        "timezone": timezone,
        "collected_at": collected_at.isoformat(),
        "tab_clicked": inspection.tab_clicked,
        "network_urls": list(inspection.network_urls),
        "api_pages_fetched": inspection.api_pages_fetched,
        "api_items": list(inspection.api_items),
        "candidate_rows": [
            {
                "selector": row.selector,
                "text": row.text,
                "href": row.href,
                "cells": list(row.cells),
            }
            for row in inspection.candidate_rows
        ],
    }


def parse_reports_from_inspection_fixture_payload(
    payload: dict[str, Any],
    holiday_overrides: frozenset[datetime.date] | frozenset | set | None = None,
) -> list[Report]:
    timezone = str(payload.get("timezone") or "Asia/Seoul")
    collected_raw = payload.get("collected_at")
    collected_at = datetime.fromisoformat(str(collected_raw)) if collected_raw else datetime.now(ZoneInfo(timezone))
    api_reports = [
        report
        for item in payload.get("api_items", [])
        if isinstance(item, dict)
        for report in [_parse_api_item(item, collected_at, timezone, holiday_overrides)]
        if report is not None
    ]
    if api_reports:
        return api_reports

    reports: list[Report] = []
    for row in payload.get("candidate_rows", []):
        if not isinstance(row, dict):
            continue
        parsed = _parse_candidate_row(
            CandidateRow(
                selector=str(row.get("selector") or ""),
                text=str(row.get("text") or ""),
                href=str(row["href"]) if row.get("href") else None,
                cells=tuple(str(cell) for cell in row.get("cells", [])),
            ),
            collected_at,
            timezone,
            holiday_overrides,
        )
        if parsed is not None:
            reports.append(parsed)
    return reports


async def _inspect_company_page_async(
    config: RuntimeConfig,
    *,
    limit: int,
    headless: bool,
    api_max_pages: int | None,
    page_delay_seconds: float,
) -> PageInspection:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `python -m pip install -e .[dev]` and "
            "`python -m playwright install chromium` before using browser commands."
        ) from exc

    network_urls: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()

        def _capture_response(response: Any) -> None:
            if response.request.resource_type not in {"xhr", "fetch"}:
                return
            if response.url not in network_urls:
                network_urls.append(response.url)

        page.on("response", _capture_response)
        try:
            await page.goto(config.base_url, wait_until="domcontentloaded", timeout=config.browser_timeout_ms)
            await page.wait_for_timeout(1500)
            tab_clicked = await _activate_domestic_tab(page)
            await page.wait_for_timeout(1500)
            api_result = await page.evaluate(
                """
                async ({ pageSize, maxPages, desiredItems, pageDelayMs }) => {
                  const items = [];
                  let pagesFetched = 0;
                  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

                  for (let page = 1; page <= maxPages; page += 1) {
                    const response = await fetch(
                      `/api/domestic/research/category?category=COMPANY&page=${page}&pageSize=${pageSize}`
                    );
                    const payload = await response.json();
                    const pageItems = Array.isArray(payload?.content)
                      ? payload.content
                      : Array.isArray(payload?.result?.itemList)
                        ? payload.result.itemList
                        : Array.isArray(payload?.result)
                          ? payload.result
                          : Array.isArray(payload)
                            ? payload
                            : [];
                    pagesFetched += 1;
                    if (!pageItems.length) {
                      break;
                    }
                    items.push(...pageItems);
                    if (desiredItems && items.length >= desiredItems) {
                      return { items: items.slice(0, desiredItems), pagesFetched };
                    }
                    if (pageItems.length < pageSize) {
                      break;
                    }
                    if (pageDelayMs > 0) {
                      await delay(pageDelayMs);
                    }
                  }

                  return { items, pagesFetched };
                }
                """,
                {
                    "pageSize": config.api_page_size,
                    "maxPages": api_max_pages or config.api_max_pages,
                    "desiredItems": limit,
                    "pageDelayMs": max(0, int(page_delay_seconds * 1000)),
                },
            )
            candidates = await page.evaluate(
                """
                ({ limit }) => {
                  const selectors = [
                    "table tbody tr",
                    "tbody tr",
                    "[role='row']",
                    "ul li",
                    "ol li",
                    "article",
                    "section div"
                  ];
                  const rows = [];
                  const seen = new Set();
                  for (const selector of selectors) {
                    const nodes = Array.from(document.querySelectorAll(selector));
                    for (const node of nodes) {
                      const text = (node.innerText || "").replace(/\\s+/g, " ").trim();
                      if (!text || text.length < 12) {
                        continue;
                      }
                      if (!(/[0-9]{4}\\.[0-9]{2}\\.[0-9]{2}|증권|리포트|목표|의견/.test(text))) {
                        continue;
                      }
                      const href = node.querySelector("a")?.href || null;
                      const cells = Array.from(node.children)
                        .map((child) => (child.innerText || "").replace(/\\s+/g, " ").trim())
                        .filter(Boolean);
                      const key = `${selector}|${text}`;
                      if (seen.has(key)) {
                        continue;
                      }
                      seen.add(key);
                      rows.push({ selector, text, href, cells });
                      if (rows.length >= limit) {
                        return rows;
                      }
                    }
                  }
                  return rows;
                }
                """,
                {"limit": limit},
            )
            title = await page.title()
            url = page.url
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out while opening {config.base_url}") from exc
        finally:
            await browser.close()

    candidate_rows = tuple(
        CandidateRow(
            selector=row["selector"],
            text=row["text"],
            href=row.get("href"),
            cells=tuple(row.get("cells", [])),
        )
        for row in candidates
    )
    return PageInspection(
        url=url,
        title=title,
        tab_clicked=tab_clicked,
        network_urls=tuple(network_urls[:20]),
        api_pages_fetched=int(api_result.get("pagesFetched", 0)),
        api_items=tuple(_extract_api_items(api_result.get("items", []))),
        candidate_rows=candidate_rows,
    )


async def _activate_domestic_tab(page: Any) -> bool:
    for locator_factory in (
        lambda: page.get_by_role("link", name="국내종목"),
        lambda: page.get_by_role("button", name="국내종목"),
        lambda: page.locator("text=국내종목"),
    ):
        locator = locator_factory()
        if await locator.count():
            await locator.first.click()
            return True
    return False


def _parse_candidate_row(
    candidate: CandidateRow,
    collected_at: datetime,
    timezone: str,
    holiday_overrides: frozenset[datetime.date] | frozenset | set | None = None,
) -> Report | None:
    stock_name, title, broker_name, published_at = _extract_core_fields(candidate, timezone)
    if not all([stock_name, title, broker_name, published_at]):
        return None

    target_price_raw = _extract_target_price_raw(candidate.text)
    opinion_raw = _extract_opinion_raw(candidate.text)
    source_id = _canonical_source_id(source_url=candidate.href)
    source_url = (
        f"https://stock.naver.com/research/company/{source_id}"
        if source_id and source_id.isdigit()
        else candidate.href
    )

    return Report(
        stock_name=stock_name,
        stock_code=_extract_stock_code(candidate.text),
        title=title,
        broker_name=broker_name,
        published_at=published_at,
        collected_at=collected_at,
        business_date=derive_business_date(published_at, holiday_overrides),
        target_price_raw=target_price_raw,
        target_price_value=parse_target_price(target_price_raw),
        opinion_raw=opinion_raw,
        opinion_normalized=normalize_opinion(opinion_raw),
        source_url=source_url,
        source_id=source_id,
    ).with_identity()


def _parse_api_item(
    item: dict[str, Any],
    collected_at: datetime,
    timezone: str,
    holiday_overrides: frozenset[datetime.date] | frozenset | set | None = None,
) -> Report | None:
    stock_name = item.get("itemName")
    title = item.get("title")
    broker_name = item.get("brokerName")
    published_at = _parse_published_at(item.get("writeDate", ""), timezone)
    if not all([stock_name, title, broker_name, published_at]):
        return None

    goal_price = item.get("goalPrice")
    target_price_raw = str(goal_price) if goal_price not in {None, ""} else None
    source_id = _canonical_source_id(item.get("researchId"), item.get("endUrl"))
    source_url = (
        f"https://stock.naver.com/research/company/{source_id}"
        if source_id
        else item.get("endUrl")
    )

    return Report(
        stock_name=str(stock_name),
        stock_code=str(item.get("itemCode")) if item.get("itemCode") else None,
        title=str(title),
        broker_name=str(broker_name),
        published_at=published_at,
        collected_at=collected_at,
        business_date=derive_business_date(published_at, holiday_overrides),
        target_price_raw=target_price_raw,
        target_price_value=parse_target_price(target_price_raw),
        opinion_raw=item.get("opinion"),
        opinion_normalized=normalize_opinion(item.get("opinion")),
        source_url=source_url,
        source_id=source_id,
    ).with_identity()


def _extract_core_fields(
    candidate: CandidateRow,
    timezone: str,
) -> tuple[str | None, str | None, str | None, datetime | None]:
    cells = [cell for cell in candidate.cells if cell]
    published_raw = None
    published_index = None
    broker_name = None
    broker_index = None

    for index, cell in enumerate(cells):
        if _parse_published_at(cell, timezone) is not None:
            published_raw = cell
            published_index = index
            break

    for index, cell in enumerate(cells):
        if index == published_index:
            continue
        if _extract_broker_name(cell):
            broker_name = _extract_broker_name(cell)
            broker_index = index
            break

    core_cells = [
        cell
        for index, cell in enumerate(cells)
        if index not in {published_index, broker_index}
        and not _looks_like_target_or_opinion_cell(cell)
    ]
    stock_name = core_cells[0] if core_cells else None
    title = core_cells[1] if len(core_cells) >= 2 else None
    published_at = _parse_published_at(published_raw or candidate.text, timezone)

    if not stock_name:
        stock_name = _guess_stock_name(candidate.text)
    if not title:
        title = _guess_title(candidate.text)
    if not broker_name:
        broker_name = _extract_broker_name(candidate.text)

    return stock_name, title, broker_name, published_at


def _parse_published_at(value: str, timezone: str) -> datetime | None:
    patterns = (
        r"(?P<year>\d{4})[./-](?P<month>\d{2})[./-](?P<day>\d{2})\s+(?P<hour>\d{2}):(?P<minute>\d{2})",
        r"(?P<year>\d{4})[./-](?P<month>\d{2})[./-](?P<day>\d{2})",
    )
    for pattern in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        parts = {key: int(raw) for key, raw in match.groupdict(default="0").items()}
        return datetime(
            year=parts["year"],
            month=parts["month"],
            day=parts["day"],
            hour=parts.get("hour", 0),
            minute=parts.get("minute", 0),
            tzinfo=ZoneInfo(timezone),
        )
    return None


def _extract_broker_name(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9가-힣&]+(?:증권|리서치))", text)
    return match.group(1) if match else None


def _looks_like_target_or_opinion_cell(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if _extract_target_price_raw(stripped) or _extract_opinion_raw(stripped):
        return True
    return bool(re.fullmatch(r"[0-9,.]+(?:만)?\s*원?", stripped))


def _guess_stock_name(text: str) -> str | None:
    segments = [segment.strip() for segment in re.split(r"[|/]", text) if segment.strip()]
    for segment in segments:
        if "증권" in segment or re.search(r"\d{4}[./-]\d{2}[./-]\d{2}", segment):
            continue
        words = segment.split()
        if words:
            return words[0]
    return None


def _guess_title(text: str) -> str | None:
    parts = [part.strip() for part in re.split(r"[|/]", text) if part.strip()]
    for part in parts:
        if re.search(r"\d{4}[./-]\d{2}[./-]\d{2}", part):
            continue
        if "증권" in part:
            continue
        return part
    return None


def _extract_stock_code(text: str) -> str | None:
    match = re.search(r"\((\d{6})\)", text)
    return match.group(1) if match else None


def _extract_target_price_raw(text: str) -> str | None:
    match = re.search(r"(?:목표주가|TP)\s*[:=]?\s*([0-9.,]+(?:만)?\s*원?)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_opinion_raw(text: str) -> str | None:
    for token in (
        "Strong Buy",
        "Trading Buy",
        "Outperform",
        "Overweight",
        "Marketperform",
        "Underperform",
        "Neutral",
        "Hold",
        "Reduce",
        "Sell",
        "Buy",
        "매수",
        "중립",
        "보유",
        "매도",
        "비중축소",
    ):
        if token.lower() in text.lower():
            return token
    return None


def _extract_api_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("content"), list):
        return [item for item in payload["content"] if isinstance(item, dict)]

    candidates: list[list[dict[str, Any]]] = []
    for value in payload.values():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            candidates.append(value)
        elif isinstance(value, dict):
            nested = _extract_api_items(value)
            if nested:
                candidates.append(nested)

    if not candidates:
        return []

    return max(candidates, key=len)


def _canonical_source_id(source_id: Any = None, source_url: str | None = None) -> str | None:
    raw_source_id = collapse_whitespace(str(source_id)) if source_id not in {None, ""} else ""
    if raw_source_id:
        match = re.search(r"(\d+)", raw_source_id)
        return match.group(1) if match else raw_source_id

    if source_url:
        match = re.search(r"/research/company/(\d+)", source_url)
        if match:
            return match.group(1)

    return None
