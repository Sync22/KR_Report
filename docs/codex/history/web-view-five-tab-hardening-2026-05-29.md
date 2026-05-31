# Web-View Five-Tab Hardening (2026-05-29)

## Scope

- Friend-facing `web-view` observation surface only.
- Main focus was top navigation role split, stored candidate evidence visibility, public DTO boundary, and regression smoke coverage.
- No production DB contents, schema/migrations, Telegram behavior, scheduler registration, admin-gui controls, broker/OpenAPI lane, or real-time fetch path was changed.

## Confirmed Facts

- Top navigation is now treated as five fixed roles: `main`, `watch`, `stock`, `market`, and `rotation`.
- Browser smoke verifies exact tab order, representative panel visibility, keyboard navigation from `stock` to `market`, horizontal overflow, public write blocking, and `/api/status` non-exposure.
- Candidate evidence is loaded on the observation path instead of being embedded in the daily archive payload.
- Public JSON tests cover internal diagnostic leakage such as `internal_candidate_signals`, `internal_missing_information`, `quality_flags`, `_sort_density`, and `_sort_signal` on candidate evidence, plus nested broker-count diagnostics in the daily observation summary.
- External and local web-view smoke now treat leaked candidate diagnostic fields as public JSON exposure issues.
- Broker breadth remains internal/readiness-only and is not a public why-notable chip, static HTML label, or nested public JSON field such as `report_intensity.five_business_day_broker_count` / `target_price_revision.previous_broker_count`.
- The intraday overlap action stays on `main`, where its panel is visible, and `watch` shows the full candidate evidence list without repeating the main top-2 preface.
- Market reference remains stored-reference evidence. It does not imply live intraday KRX state.

## Assumptions

- The five-tab split is the current product direction: `main` for priority overview, `watch` for candidate evidence, `stock` for selected-stock detail, `market` for stored market reference, and `rotation` for category/ETF/rotation context.
- KRX snapshot gaps after the latest stored date are data freshness limitations, not web-view rendering failures.
- Future top-2 intraday checks remain a separate lab/staging read-only lane until source burden and permissions are proven.

## Validation Performed

- `python -m pytest tests\test_web_view.py -q` -> 54 passed.
- `python -m pytest tests\test_cli_commands.py -q` -> 280 passed.
- `python -m pytest -q` -> 631 passed.
- `python -m stock_monitor candidate-evidence-readiness --recent-report-dates 10 --stock-limit 20 --json` -> `review_ready_count` 10, `qa_issue_date_count` 0, `qa_warning_date_count` 0.
- `python -m stock_monitor web-view-value-qa --recent-business-days 5 --stock-limit 20 --json` -> `issue_count` 0, `warning_count` 5 for stored KRX snapshot not yet available after 2026-05-19.
- `python -m stock_monitor web-view-browser-smoke --date latest --json` -> `issue_count` 0, exact five-tab order, representative panels visible/clickable, candidate JSON diagnostic leak check clean, and 0px horizontal overflow across tested viewports.
- `git diff --check` -> no whitespace errors; CRLF warnings only.

## Operational Impact

- Local and external smoke checks now catch top-tab regressions and public candidate diagnostic leaks earlier; unit tests also pin daily observation-summary diagnostic stripping.
- Public web-view remains GET-only and stored-data based.
- Operator-facing readiness can still carry internal diagnostic signals separately from public labels.

## Residual Risk

- Production URL should still be checked after deploy/sync because local smoke cannot prove external tunnel/provider behavior.
- Dense real-market dates should be reviewed visually after operation, especially days with many chips or missing flow/KRX evidence.
- KRX freshness gaps require source/backfill review rather than web-view wording changes.

## Remaining Verification Items

- Confirm the deployed public surface still exposes only the intended GET endpoints.
- Re-run browser smoke after the next production sync.
- Keep future top-2 5-minute intraday probing out of `web-view`, Telegram, scheduler, DB writes, and broker execution until a separate lab plan is approved.
