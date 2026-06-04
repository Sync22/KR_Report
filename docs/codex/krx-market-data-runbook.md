# KRX Market Data Runbook

## Purpose

This is the consolidated KRX and market-reference runbook.

Use this before touching KRX Open API snapshots, KRX Data Marketplace investor-flow samples, ETF references, flow display, or scheduled ingest planning.

## Source Ownership

| Data | Source | Current use |
| --- | --- | --- |
| Research reports | Naver Stock research pages | Report collection, summaries, Telegram, web-view reports. |
| Stock, ETF, index daily price/volume/turnover | KRX Open API | Stored read-only market reference and trend context. |
| Investor flow `[12008]`, `[12009]`, `[12010]` | KRX Data Marketplace | Stored sample/read-only flow reference. |
| Future intraday quote/turnover/index | Toss Securities Open API, KIS, or another approved source | Separate lab/staging lane first; may later affect top-2 observation priority after approval. |
| 업종/테마 | Naver taxonomy for now | Category rollups and dated snapshots; do not call this KRX-owned taxonomy yet. |

Display naming follows [data-source-policy.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-source-policy.md).

## Skill / Agent Use

| Work | Skill | Agent | Rule |
| --- | --- | --- | --- |
| Stock/ETF/index daily KRX Open API rows | none | `market-data-engineer`, `backend-developer`, `sql-pro` | Use existing Open API backfill and repository paths. Do not use browser probes for this lane. |
| KRX Data Marketplace session, LOGOUT, detection, or screen access | Existing request/login/sample validation first; `scrapling-official` only for bounded browser/source probes when needed | `market-data-engineer`, `debugger` | Scrapling is the active probe lane. Botasaurus is archived reference only. Do not wire probe output into production tables without the normal import/review path. |
| Investor-flow sample validation/import | none by default | `market-data-engineer`, `sql-pro`, `test-engineer` | Use manifest validation, compare, import-preview, guarded import, and `db-verify`. |
| Flow/ETF/user display | Browser/Chrome plugin for ordinary local visual checks; Playwright MCP only for repeatable lab/E2E-style checks | `web-ui-engineer`, `security-hardening` | GET-only and public-safe boundary remain mandatory. |
| OHLCV forecasting comparison | none by default; historical Kronos lane only if explicitly re-enabled | `market-data-engineer`, `reviewer` | Research-only. No Telegram, scheduler, public numeric score, or trading-recommendation output. |

## Current State

| Area | Status | Guard |
| --- | --- | --- |
| KRX Open API daily snapshots | 18-month target complete through latest stored date | `2024-11-08`~`2026-05-19` stored on the current main-PC DB after the guarded `2026-05-20 09:17 KST` repair. Use bounded backfill with backup confirmation for future repairs. |
| KRX Open API morning fill | Working path added | KRX Open API daily rows are officially available at the next Korean business day `08:00` KST. `scheduled-krx-daily-backfill` runs after that window and targets previous-business-day or earlier missing rows; do not fetch same-day rows. |
| KRX Open API availability probe | Manual evidence path added | `krx-openapi-availability-probe` records endpoint availability in `operation_events` only. It does not write snapshot tables or register scheduler tasks. The former same-day hourly follow-up automation was deleted on `2026-05-20` after the official next-business-day `08:00` publication rule was confirmed. |
| Stock/ETF/index reference tables | Working | Keep as market reference, not scoring. |
| Future intraday observation reference | Not implemented | A verified real-time source may later strengthen or lower `우선 확인` ordering and main-card emphasis. `read-only` blocks writes, automation, secrets, and orders; it does not block observation-priority impact. |
| KRX Data Marketplace raw login check | Working | Prefer `.env` raw login checks over browser automation. |
| `[12008]` market investor flow | Sample/import path exists | Stored read-only reference only. |
| `[12009]` stock investor flow | Mention-stock scheduled path added | At `16:00`, collect only anchor-day report-mentioned stocks over the recent 31-day window; skip already stored rows. Broad all-stock ingest remains forbidden. For migration catch-up, anchor to the latest report-mentioned business date. |
| `[12010]` top net-buy ranking | Sample/import path exists | Treat as ranking reference for context, not trading recommendation. |
| Stage 4 validation | Complete for `2026-05-08` and `2026-05-07` | Broad Stage 6 scheduled ingest remains disabled; only the narrow mentioned-stock `[12009]` task is scheduled. |
| Web-view flow display | Working | GET-only and stored-data by default. Manual current-business-day Naver `priceTop` lookup is allowed only through the `장중 거래대금 확인` button and is labeled `Naver 장중 참고`; it does not write DB rows or replace KRX official stored values. |

Category data is intentionally outside the KRX market-reference lane.
Only `sector` catalog rows verified through Naver upjong-compatible sources (`source=naver_industry` or `source=naver_upjong`) are eligible for `refresh-industries`.
Display/cache/manual sector rows (`naver_quote`, `operator`, or custom sources) remain labels until validated with `refresh-industry CODE --dry-run`.

### Intraday Index Source Check

The current KRX Open API lane is daily snapshot oriented. Do not assume it can provide a 5-minute intraday KOSPI/KOSDAQ feed for the `web-view`.

Verified source notes as of `2026-05-18`:

- KRX's own data-receipt guidance says private investors who want real-time or delayed market quote data should use securities firms, data vendors, terminals, or portal sites, while professional redistribution requires a Koscom market-data contract. This makes KRX Open API unsuitable as the default 5-minute intraday index source for this toy `web-view`.
- Korea Investment Securities Open API is a candidate source because its official sample repository includes REST/WebSocket examples and authentication for domestic stock quote data. Treat it as a future separate source lane: credentials, rate limits, index TR coverage, storage schema, and observation-priority boundaries must be reviewed before any scheduler or live polling is added.
- Until a source lane is approved, `지수 참고` in `web-view` should continue to show stored KRX daily index values and clearly label them as stored data. The separate manual Naver `priceTop` overlap check is only a same-day stock turnover reference, not an intraday KRX index lane.

Implementation guard:

- A future intraday poller may target a 5-minute display cadence only after the source is approved and documented here.
- The intraday index lane may affect observation priority only after approval. It must not widen KRX Data Marketplace investor-flow automation, expose credentials, write production DB rows by default, trigger Telegram/scheduler automation, or create public trading signals.
- If real-time evidence later becomes strong enough for trading-decision review, treat that as a separate operator-only decision-support/execution-lab step, not as a public `web-view` wording change or automatic order path.

## Operating Commands

```powershell
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag pre-krx-work
python -m stock_monitor scheduled-krx-daily-backfill --dry-run --json
python -m stock_monitor krx-openapi-availability-probe --date latest --endpoint daily --json
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --max-dates 5 --dry-run --json
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --max-dates 5 --confirm --i-backed-up
python -m stock_monitor scheduled-krx-mentioned-flow-backfill --dry-run
python -m stock_monitor scheduled-krx-mentioned-flow-backfill
python -m stock_monitor krx-flow-login-check --date 2026-05-08 --market STK
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --strict
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw --allow-right-extra-top-rows
```

## KRX Backfill Rule

Use KRX backfill for reproducible price/volume/turnover context.

| Rule | Decision |
| --- | --- |
| Official publication window | Daily rows are officially available at the next Korean business day `08:00` KST. |
| Normal scheduled time | `08:10` KST on Korean business days, after the official publication window. |
| Scheduled target date | Previous business day or earlier recent missing business dates only. Never same-day rows. |
| Analysis window | 3 months is the default useful window. |
| Backtest/rebaseline window | Up to 18 months for stock/ETF/index snapshots when explicitly backfilling historical KRX Open API data. |
| Retention | 18 months for stock/ETF/index snapshots while backtest/observation work is active. The CLI cleanup default is now `550` days. |
| Batch size | Prefer 10 business dates or less when rebaselining. |
| Safety | Run `db-verify` and `db-backup` before real backfill. |
| Cleanup | Weekly cleanup, monthly `db-vacuum --dry-run`; real VACUUM requires `--confirm`. |

Manual broad rebaseline still requires `db-verify` and `db-backup`. The narrow scheduled fill is limited to recent missing KRX Open API daily endpoints, skips existing rows, targets the previous business day or earlier missing dates, and remains separate from KRX Data Marketplace investor-flow ingest.

### Open API Availability Probe

Use `krx-openapi-availability-probe` when the question is "has KRX published rows yet?" rather than "write rows into the snapshot tables?"

```powershell
python -m stock_monitor krx-openapi-availability-probe --date latest --endpoint daily --json
python -m stock_monitor krx-openapi-availability-probe --date YYYY-MM-DD --endpoint daily --json
python -m stock_monitor krx-openapi-probe-summary --date YYYY-MM-DD --json
```

Probe contract:

- Endpoint set `daily` means `stock-kospi-daily`, `stock-kosdaq-daily`, `etf-daily`, `index-krx-daily`, `index-kospi-daily`, and `index-kosdaq-daily`.
- The command records call time, target business date, endpoint, HTTP/API success, raw row count, parsed row count, response/reference date, previous-probe delta, status, and `stored=false`.
- Status is `available`, `partial`, `empty_rows`, `not_published`, `error`, or `transport_blocked`.
- Non-dry-run writes only `operation_events`; it never writes `stock_market_daily`, `etf_daily_snapshots`, or `market_index_daily`.
- Local socket-block failures such as Windows `WinError 10013` are classified as `transport_blocked` and are not written to the provider availability timeline. Rerun the same read-only probe with the narrow network allowance, then interpret only the provider result.
- `--dry-run --json` fetches and prints the same shape without recording an event.
- `krx-openapi-probe-summary` is read-only. It summarizes recorded provider probe slots for one business date, including `first_data_slot_kst`, `not_published_until_kst`, latest status counts, raw rows, and parsed rows.
- Scheduler registration is not used for same-day probing. If a future validation task is approved, use an opt-in diagnostic task, not a default mini-PC task.

Recommended observation shape:

| Slot | Purpose |
| --- | --- |
| Next Korean business day `08:00` | Official KRX Open API daily publication window. |
| `08:10` | Normal scheduled backfill slot after the official window. |
| Manual only | `krx-openapi-availability-probe` may still be run by an operator when diagnosing provider/API behavior, but it is no longer a recurring same-day automation. |

Main-PC evidence from `2026-05-20 00:59~09:17 KST`:

| Target date | Result |
| --- | --- |
| `2026-05-15` | 6/6 endpoints reachable; ETF/KOSPI/KOSDAQ parsed above minimum with filtered extra raw rows, and index endpoints fully available. Backfilled successfully after backup/restore-smoke. |
| `2026-05-18` | 6/6 endpoints reachable with the same available/partial pattern. Backfilled successfully after backup/restore-smoke. |
| `2026-05-19` | 6/6 endpoints were `not_published` through unrestricted-network `07:28:32`; at unrestricted-network `08:28:38`, ETF/stock endpoints became `partial` and index endpoints became `available`, with reference date `2026-05-19`, raw rows `4011`, and parsed rows `3701`. At `09:17 KST`, after `db-verify`, backup `stock_monitor_20260520_0916_before_krx_20260519_backfill.db`, and restore-smoke success, a bounded live `krx-backfill-missing daily --to-date 2026-05-19 --max-dates 1` stored ETF `874`, KOSPI stock `923`, KOSDAQ stock `1777`, KRX index `36`, KOSPI index `51`, and KOSDAQ index `40` rows with `incomplete_endpoints=0`. |
| `2026-05-20` | 6/6 endpoints HTTP/API success but raw/parsed rows were `0`; recorded as `not_published` at `01:01`, `01:28`, unrestricted-network `02:28:43`, unrestricted-network `03:28:36`, unrestricted-network `04:28:46`, unrestricted-network `05:28:45`, unrestricted-network `06:28:41`, unrestricted-network `07:28:33`, unrestricted-network `08:28:42`, `17:09`, `18:09`, and `19:09` with no row-count delta. This is now treated as expected behavior because the official rule is next-business-day `08:00`, not same-day publication. |

Interpretation: KRX Open API is daily provider evidence, not a real-time market mood source. At the observed `08:28 KST` window it exposed the previous business day `2026-05-19` rows, and the guarded `09:17 KST` backfill stored them successfully. The official operating rule is now next-business-day `08:00` publication followed by the `08:10` scheduled backfill; same-day `not_published` is normal and should not keep a probe automation running. Sandboxed `02:28 KST` through `09:16 KST` probes/backfill attempts recorded local socket-access errors; treat those as environment evidence only, not as KRX publication status.

## Mentioned-Stock Investor Flow Rule

This is the only automatic KRX Data Marketplace investor-flow path approved for normal operation.

| Rule | Decision |
| --- | --- |
| Scheduler task | `StockMonitor-KrxMentionedFlowBackfill` |
| Normal scheduled time | `16:00` KST on Korean business days, after the regular market close delay. |
| Normal scheduled CLI | `scheduled-krx-mentioned-flow-backfill` |
| Restore-history CLI | `krx-mentioned-flow-latest-anchor-backfill` |
| Anchor universe | Stocks mentioned in the anchor business day's Naver reports. Default threshold is `mention_count >= 1`. For restore/migration or any case where reports were filled before flow rows, use the latest report-mentioned business date as the anchor, not the wall-clock date. |
| Lookback | Recent `31` calendar days, filtered to Korean business days. |
| Request cap | Default `--max-calls 300` per run, newest business dates first. Use `0` only for deliberate unlimited manual execution. |
| Request pacing | Default `--sleep-seconds 1` for the CLI and Task Scheduler wrapper. Keep this delay unless a deliberate dry-run or operator-reviewed local test needs `0`. |
| Data source | KRX Data Marketplace `[12009]` stock-level investor flow only. |
| Skip behavior | Existing `stock_investor_flow_daily` rows are skipped by default. |
| Excluded | `[12008]` market flow and `[12010]` net-buy top are not fetched by this scheduled path. |
| Guard | Business-day/no-run/operator-pause guard plus `15:30` earliest and `17:00` latest time window for automatic runs. |

Manual broad investor-flow backfills remain separate and should still be reviewed with `--dry-run` before live execution.

### Latest Mentioned-Date Catch-Up

When reports already exist for a date but `[12009]` rows are incomplete, catch up from the latest report-mentioned business date:

```powershell
python -m stock_monitor db-backup --tag before_latest_mentioned_flow_31d_fill
python -m stock_monitor scheduled-krx-mentioned-flow-backfill --date YYYY-MM-DD --lookback-days 31 --mention-threshold 1 --max-calls 300 --dry-run --json
python -m stock_monitor scheduled-krx-mentioned-flow-backfill --date YYYY-MM-DD --lookback-days 31 --mention-threshold 1 --max-calls 300 --sleep-seconds 1
```

After a live run, repeat the dry-run. If `planned_call_count` is still above `0`, run the same command again for the same anchor date until the dry-run reports `planned_call_count: 0`.

This is still the approved narrow path when the anchor date is the latest report-mentioned date and the stock universe is limited to that date's mentioned stocks. It is not approval to collect all historical report-mentioned stocks, all market stocks, `[12008]` market flow, or `[12010]` net-buy rankings automatically.

For a full restored-history catch-up, the intended policy is each stock's latest report-mentioned date, then that stock's recent 31-day window. Do not blindly iterate every historical report date with the date-level command if that would collect stock/date pairs outside a stock's latest-anchor 31-day window.

Use the exact per-stock latest-anchor mode for that restored-history case:

```powershell
python -m stock_monitor krx-mentioned-flow-latest-anchor-backfill --lookback-days 31 --max-calls 300 --dry-run --json
python -m stock_monitor db-backup --tag before_latest_anchor_mentioned_flow_fill
python -m stock_monitor krx-mentioned-flow-latest-anchor-backfill --lookback-days 31 --max-calls 300 --sleep-seconds 1 --confirm --i-backed-up
python -m stock_monitor db-verify
python -m stock_monitor krx-mentioned-flow-latest-anchor-backfill --lookback-days 31 --max-calls 300 --dry-run --json
```

Repeat only while the dry-run reports `planned_call_count > 0`. Keep `--max-calls 300`, keep `--sleep-seconds 1` for live runs, and stop on network/KRX errors rather than retrying blindly. This command still only uses `[12009]`, report-mentioned stocks, each stock's latest report anchor, and already-stored row skipping.

### 18-Month Open API Backfill Note

Use the existing KRX Open API path for stock/ETF/index daily snapshots. Do not switch this lane to browser scraping or Botasaurus because the approved API already returns the required price, volume, turnover, ETF, and index rows.

Recommended broad-backfill shape:

```powershell
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag before_krx_18m_batch
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --dry-run --json
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --sleep-seconds 3 --confirm --i-backed-up
```

Operational limits:

- Use `5` business dates per live batch by default. Increase only after dry-run review and a recent backup.
- Use `--dry-run --json` when an operator handoff or automation needs a machine-readable missing-endpoint plan. JSON mode is intentionally planning-only for this lane; live fetches keep text logs and operation events.
- Keep `sleep-seconds` at `3` or higher.
- Run `db-verify` after each batch.
- Back up every 10 business dates or before any larger/manual boundary change. Avoid creating a backup for every tiny batch because `data/backups` can outgrow the live DB quickly.
- `db-verify` and backfill planning treat very small nonzero endpoint row counts as incomplete, not complete.
- The current built-in holiday guard includes vetted 2024, 2025, and 2026 KRX closure dates. Historical backfill still requires dry-run review because ad-hoc exchange closures can exist and future years are not automatic. `operator-status` exposes `market_holiday_coverage` and warns from October 2026 if no verified future-year dates are configured.
- Do not fetch same-day rows. KRX Open API daily rows are expected at next Korean business day `08:00`; prefer `--to-date` as the latest confirmed stored/trading date for manual repairs.

Current 18-month rebaseline progress:

| Date | Result |
| --- | --- |
| `2026-05-15` | Latest backed-up mini PC retry at `2026-05-17T08:17` KST used `data/backups/stock_monitor_20260517_0815_before_krx_20260515_retry_5.db`, reached all 6 daily endpoints, and stored ETF 874 rows, stock 2701 rows, and index 127 rows with `incomplete_endpoints=0`. Post-success backup `data/backups/stock_monitor_20260517_0818_after_krx_20260515_success.db` was restore-smoked successfully. Earlier backed-up retries at `06:40`, `01:19`, and `00:52` returned empty rows. |
| `2024-11-08`~`2026-05-15` | Stock/ETF/index daily snapshots stored. The extra `2024-11-08` row is harmless and sits just before the dynamic target window. |
| `krx-baseline-analysis` | Reports `missing_daily_snapshots=0` after the successful `2026-05-15` fill. It also includes `recent_backfill_observations` so operators can see recent `success`, `empty`, or `partial` KRX Open API attempts before retrying future missing dates. |
| `2025-12-30`, `2025-12-29`, `2025-12-26` | Loaded successfully. |
| `2025-12-24`, `2025-12-23`, `2025-12-22`, `2025-12-19`, `2025-12-18` | Loaded successfully. |
| `2025-12-17`, `2025-12-16`, `2025-12-15`, `2025-12-12`, `2025-12-11` | Loaded successfully. |
| `2025-12-10`, `2025-12-09`, `2025-12-08`, `2025-12-05`, `2025-12-04` | Loaded successfully. |

## Investor-Flow Rule

Investor flow is not a whole-market crawler in the current stage.

| Screen | Scope |
| --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Leadership-candidate stock/date keys plus explicitly selected stock-code history when the visible UI needs a selected-stock trend. |
| `[12008] 투자자별 거래실적` | Market background. |
| `[12010] 투자자별 순매수상위종목` | Ranking/reference. |

Do not enable broad scheduled Data Marketplace ingest until Stage 6 is separately approved. The exception is the narrow `StockMonitor-KrxMentionedFlowBackfill` task, which only fills recent `[12009]` rows for the anchor day's report-mentioned stocks. In normal live operation the anchor is the current business day; after restore or backfilled report ingestion, use the latest report-mentioned business date and verify remaining calls with dry-run.

## Stage Boundary

| Stage | Meaning | Current status |
| --- | --- | --- |
| Stage 0 | Visible-grid sample baseline and placeholders | Done |
| Stage 1 | Raw network response bodies | Done for two business dates |
| Stage 2 | Strict raw sample validation | Done for two business dates |
| Stage 3 | Visible-grid/raw parity | Done for two business dates |
| Stage 4 | Repeated business-day validation | Done |
| Stage 5 | Read-only trend/view display | Done |
| Stage 6 | Scheduled ingest design | Design only; enable blocked |

## Manual Investor-Flow Backfill

Use this only after `db-verify` and `db-backup`.
It is an explicit operator-run command, not scheduled ingest.

```powershell
python -m stock_monitor krx-flow-backfill-manual --from-date 2026-05-01 --to-date 2026-05-08 --candidate-limit 5 --market STK --top-investor foreign --dry-run
python -m stock_monitor krx-flow-backfill-manual --from-date 2026-05-01 --to-date 2026-05-08 --candidate-limit 5 --market STK --top-investor foreign --sleep-seconds 1.5 --confirm --i-backed-up
python -m stock_monitor krx-flow-backfill-manual --from-date 2026-04-01 --to-date 2026-05-08 --candidate-limit 0 --stock-code 329180 --stock-code 032640 --dry-run
```

Current policy:

- `[12008]` market flow: STK, amount, net-buy.
- `[12010]` net-buy top: STK, foreign.
- `[12009]` stock flow: leadership candidates per business date, or explicit `--stock-code` history when selected-stock status needs a longer trend.
- Use `--candidate-limit 0` with repeated `--stock-code` values when the goal is explicit stock history only.
- Existing stock/date keys are skipped by default unless `--no-skip-existing` is explicit.
- Scheduled investor-flow ingest remains disabled until separately approved.

Detailed capture history remains in the original KRX detail documents listed from [documentation-index.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/documentation-index.md).

## Non-Negotiables

- Do not store credentials outside local `.env`.
- Do not expose KRX credentials, cookies, headers, DB paths, or scheduler internals in `web-view`.
- Do not treat KRX flow alone as a trading recommendation or public numeric score. It may support observation-candidate ordering when combined with other stored evidence.
- Do not infer investor flow from report counts.
- Do not silently scale units; preserve screen/API units explicitly.
- Do not mix future category snapshots into older dates.
