# Market Data Runbook

## Current Operating Source

The active market-data path is one Toss OpenAPI capture at `20:05` KST on each Korean business day, after the Toss KR calendar's integrated after-market closes at `20:00`. The stored `baseline_time=20:00` denotes that market-close boundary; the actual request time remains in each row's fetched/observed timestamp. The capture stores the bounded web-view values: KOSPI/KOSDAQ level and change, market-level individual/foreigner/institution flow, and named turnover Top20 split into stocks and ETFs. It also refreshes the full KR listing cache from fixed `KOSPI`, `KOSDAQ`, and `KR_ETC` `stocks/all` calls; stored search reads this cache without calling Toss. To calculate next-day close reassessment, it requests available quote and flow references for every valid daily-summary candidate in batches of at most two symbols; the public priority projection remains Top2.

- `StockMonitor-TossCloseSnapshot` runs the close capture through `toss-market-context-capture`.
- KRX Open API and KRX Data Marketplace tasks are removed from normal scheduler registration.
- Existing KRX rows remain intact for historical analysis and old report windows; they are not a live fallback for the web-view.
- The Toss snapshot is a stored close reference, not an intraday quote or execution signal.

The capture event is `completed` only when all required domains are present: exactly 20 unique ranked turnover symbols with amounts, usable stock/ETF classification for each ranked symbol, both KOSPI/KOSDAQ index values and changes, six market-flow groups (three investor types for each market), a complete stock-universe response, and stored close quote plus foreigner/institution flow for every valid daily-summary candidate. Otherwise the event is `partial` or `empty` and names missing domains. Incomplete stock-universe responses do not replace the last complete cache. Unclassified symbols are not persisted as stocks by default, and operator health flags partial/failed capture events. Snapshot-date lookup uses ranked capture rows, so candidate-only quote rows cannot advance the market snapshot date.

The GET-only market view carries the capture status and missing domains into its stored context/freshness fields. A same-date partial capture is labeled `partial`, not `exact`; a failed attempt with no saved rows is exposed separately from the last stored snapshot date. An absent event after the scheduled window warns in operator health when the Toss task is registered and healthy and the Korean business date is not suppressed.

## KR Calendar Cross-Check

Use the operator command when checking a proposed observation schedule or test window. It reads the Toss KR calendar, compares explicit dates with local weekday/holiday rules, and never changes either source of scheduling authority:

```powershell
python -m stock_monitor toss-market-calendar-check --date 2026-10-01 --date 2026-10-02 --json
python -m stock_monitor toss-market-calendar-check --date 2026-10-01 --date 2026-10-02 --live --confirm-token-reissue --json
```

Plan mode makes no network request. Live mode reports each match, mismatch, or unverified date; any mismatch or unknown result exits nonzero. The command performs no DB write and adds no scheduled task. The existing 20:05 capture requires the stock-universe cache schema to be current before its next scheduled run.

## Parked Proposal: KOSPI/KOSDAQ Rapid-Move Telegram Alert

This older idea is outside the active TODO2 queue. Its API availability and trigger thresholds are not currently verified or approved. Reopen it as a separate planning task and check current Toss documentation before implementation.
## Historical KRX Data and Recovery

Existing KRX Open API and Data Marketplace rows remain available for historical analysis. Their refresh tasks have been removed from normal scheduling; KRX data must not fill missing current Toss values.

| Data | Historical use | Current boundary |
| --- | --- | --- |
| KRX Open API daily stock/ETF/index rows | Review past dates and existing reports. | No normal refresh schedule or current web-view fallback. |
| KRX Data Marketplace `[12008]` / `[12009]` / `[12010]` rows | Review previously stored samples and historical flow. | No normal scheduled ingest; do not treat old `[12009]` catch-up instructions as active. |
| Naver taxonomy and operator category snapshots | Explain the source and date of historical category labels. | Keep separate from Toss market references and do not copy today’s labels backward. |

A new KRX repair/import is a separate, bounded operation that needs explicit scope. Before any approved write, inspect the current CLI help, run `db-verify`, take a backup, review a date-limited dry run, and verify the stored result. Do not register or revive a KRX scheduler task from this historical record.

Detailed May 2026 capture, backfill, login, schema, and sample-validation notes were superseded by the current Toss baseline. Historical execution evidence remains in [history.md](history.md); the current market contract is this page’s [Current Operating Source](#current-operating-source), and scheduler timings are in [mini-pc-runbook.md](mini-pc-runbook.md).
