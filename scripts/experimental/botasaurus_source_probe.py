"""Research-only Botasaurus browser probe for candidate source sites.

This stays outside the production fetch, parse, store, and scheduler paths.
It checks whether a target page can be loaded through Botasaurus and reports
only lightweight page metadata.
"""

from __future__ import annotations

import json

from botasaurus.browser import Driver, browser


TARGETS = [
    {
        "label": "naver_research_company",
        "url": "https://stock.naver.com/research/company",
        "expect": "research",
    },
    {
        "label": "krx_data_market_main",
        "url": "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd",
        "expect": "KRX",
    },
]


@browser(cache=False, parallel=1, headless=True)
def run_probe(driver: Driver, item: dict[str, str]) -> dict[str, object]:
    driver.get(item["url"])
    title = driver.title
    current_url = driver.current_url
    body_text = driver.run_js("return document.body ? document.body.innerText : ''") or ""
    return {
        "label": item["label"],
        "url": item["url"],
        "current_url": current_url,
        "title": title,
        "body_length": len(body_text),
        "expect_text_present": item["expect"].lower() in body_text.lower(),
    }


def main() -> int:
    results = run_probe(TARGETS)
    print(
        json.dumps(
            {
                "surface": "botasaurus_source_probe",
                "read_only": True,
                "production_integration": False,
                "targets": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
