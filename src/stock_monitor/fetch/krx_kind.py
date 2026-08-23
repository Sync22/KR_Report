from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
from urllib import error, parse, request


KIND_MARKET_ACTION_SEARCH_URL = "https://kind.krx.co.kr/disclosure/details.do"
KIND_MARKET_ACTION_CATEGORY = "0347"
KIND_MARKET_ACTION_MAX_RESPONSE_BYTES = 1_048_576
_ACCEPTANCE_NUMBER_PATTERN = re.compile(r"openDisclsViewer\('(?P<number>\d{14})'")


@dataclass(frozen=True)
class KrxKindMarketAction:
    acceptance_number: str
    published_at: datetime
    title: str
    submitter: str | None


class _KrxKindMarketActionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.notices: list[KrxKindMarketAction] = []
        self._cells: list[str] = []
        self._cell_parts: list[str] | None = None
        self._acceptance_number: str | None = None
        self._in_row = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._cells = []
            self._acceptance_number = None
        elif self._in_row and tag == "td":
            self._cell_parts = []
        elif self._in_row and tag == "a":
            onclick = dict(attrs).get("onclick") or ""
            match = _ACCEPTANCE_NUMBER_PATTERN.search(onclick)
            if match:
                self._acceptance_number = match.group("number")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell_parts is not None:
            self._cells.append(_normalize_text("".join(self._cell_parts)))
            self._cell_parts = None
        elif tag == "tr" and self._in_row:
            self._append_current_row()
            self._in_row = False

    def _append_current_row(self) -> None:
        if not self._acceptance_number or len(self._cells) < 5:
            return
        try:
            published_at = datetime.strptime(self._cells[1], "%Y-%m-%d %H:%M")
        except ValueError:
            return
        title = self._cells[3]
        if not title:
            return
        self.notices.append(
            KrxKindMarketAction(
                acceptance_number=self._acceptance_number,
                published_at=published_at,
                title=title,
                submitter=self._cells[4] or None,
            )
        )


def fetch_krx_kind_market_actions(
    target_date: date,
    *,
    timeout_seconds: float = 15,
) -> list[KrxKindMarketAction]:
    encoded = parse.urlencode(
        {
            "method": "searchDetailsSub",
            "currentPageSize": "15",
            "pageIndex": "1",
            "orderMode": "1",
            "orderStat": "D",
            "forward": "details_sub",
            "disclosureType01": "",
            "disclosureType02": f"{KIND_MARKET_ACTION_CATEGORY}|",
            "disclosureType03": "",
            "disclosureType04": "",
            "disclosureType05": "",
            "disclosureType06": "",
            "disclosureType07": "",
            "disclosureType08": "",
            "disclosureType09": "",
            "disclosureType10": "",
            "disclosureType11": "",
            "disclosureType13": "",
            "disclosureType14": "",
            "disclosureType20": "",
            "pDisclosureType01": "",
            "pDisclosureType02": f"{KIND_MARKET_ACTION_CATEGORY}|",
            "pDisclosureType03": "",
            "pDisclosureType04": "",
            "pDisclosureType05": "",
            "pDisclosureType06": "",
            "pDisclosureType07": "",
            "pDisclosureType08": "",
            "pDisclosureType09": "",
            "pDisclosureType10": "",
            "pDisclosureType11": "",
            "pDisclosureType13": "",
            "pDisclosureType14": "",
            "pDisclosureType20": "",
            "searchCodeType": "",
            "repIsuSrtCd": "",
            "allRepIsuSrtCd": "",
            "oldSearchCorpName": "",
            "disclosureType": "",
            "disTypevalue": "",
            "reportNm": "",
            "reportCd": "",
            "searchCorpName": "",
            "business": "",
            "marketType": "",
            "settlementMonth": "",
            "securities": "",
            "submitOblgNm": "",
            "enterprise": "",
            "fromDate": target_date.isoformat(),
            "toDate": target_date.isoformat(),
            "reportNmTemp": "",
            "reportNmPop": "",
            "bfrDsclsType": "on",
            "disclosureTypeArr02": KIND_MARKET_ACTION_CATEGORY,
        }
    ).encode("ascii")
    http_request = request.Request(
        KIND_MARKET_ACTION_SEARCH_URL,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://kind.krx.co.kr/disclosure/details.do?method=searchDetailsMain",
            "User-Agent": "stock-monitor/0.1",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            payload = response.read(KIND_MARKET_ACTION_MAX_RESPONSE_BYTES + 1)
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch KRX KIND market actions: {exc}") from exc
    if len(payload) > KIND_MARKET_ACTION_MAX_RESPONSE_BYTES:
        raise RuntimeError("Failed to fetch KRX KIND market actions: response too large.")
    return parse_krx_kind_market_actions(payload.decode("utf-8", errors="replace"))


def parse_krx_kind_market_actions(payload: str) -> list[KrxKindMarketAction]:
    parser = _KrxKindMarketActionParser()
    parser.feed(payload)
    parser.close()
    return parser.notices


def _normalize_text(value: str) -> str:
    return " ".join(unescape(value).split())
