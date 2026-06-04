# Web-View Main Layout First Pass

## Purpose

Refine the public `web-view` main page into a faster briefing surface without changing data collection, scheduler behavior, Telegram behavior, or public API routes.

## Scope

- Keep the calendar, but remove the visible `날짜 선택` heading.
- Reorder `오늘 읽을 요약` to show one-line comments first, then compact report summary, then pill-style watch candidates.
- Improve `국장 관찰 요약` by using sentence-like `시장 분위기`, clearer item separators, and a single `시장 폭` block for sector/theme summary.
- Remove separate sector/theme summary cards from the main page; keep `업종/테마 상세` drilldown.
- Remove the selected-stock `현재 선택` strip.
- Normalize selected-stock target trail rows.
- Split investor-flow period totals into a distinct `기간합계` line using `|` separators.
- Default daily flow/volume rows to the selected month, with an expand/collapse control for all stored rows.

## Boundaries

- No new public API route.
- No admin-gui/control surface/secret/DB path exposure in `web-view`.
- No Telegram or scheduler change.
- No broad ingest or KRX automation policy change.
- No trading recommendation wording, numeric score, grade, buy/sell signal, entry price, exit price, target return, or confidence wording.

## Verification

- `python -m pytest tests/test_web_view.py -q`
- `python -m pytest tests/test_cli_commands.py -q`
- `python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json`
- `python -m stock_monitor web-view-browser-smoke --date latest --json`

## Implementation Notes

- Implemented in `src/stock_monitor/cli.py`.
- Regression coverage updated in `tests/test_web_view.py`.
- Local `web-view` was restarted on `{LOCAL_WEB_VIEW_TARGET}` after verification.
