# Market Data Runbook

## Current Operating Source

The active market-data path is one Toss OpenAPI capture at `20:05` KST on each Korean business day, after the Toss KR calendar's integrated after-market closes at `20:00`. The stored `baseline_time=20:00` denotes that market-close boundary; the actual request time remains in each row's fetched/observed timestamp. The capture stores only the bounded values used by the web-view: KOSPI/KOSDAQ level and change, market-level individual/foreigner/institution flow, named turnover Top20 split into stocks and ETFs, and the server-derived priority Top2 quote/flow references.

- `StockMonitor-TossCloseSnapshot` runs the close capture through `toss-market-context-capture`.
- KRX Open API and KRX Data Marketplace tasks are removed from normal scheduler registration.
- Existing KRX rows remain intact for historical analysis and old report windows; they are not a live fallback for the web-view.
- The Toss snapshot is a stored close reference, not an intraday quote or execution signal.

## Planned: KOSPI/KOSDAQ Rapid-Move Telegram Alert

### Official API Finding

The current Toss OpenAPI does **not** document a market-wide sidecar or circuit-breaker endpoint. The usable official facts for a market-wide rapid-move alert are the real-time KOSPI/KOSDAQ indicator price and the supported one-minute indicator candles. The latter provides a bounded short-window comparison without using account, order, or individual-stock APIs.

| Official endpoint | Available fact | Planned use |
| --- | --- | --- |
| `GET /api/v1/market-indicators/prices?symbols=KOSPI,KOSDAQ` | Current index level and timestamp | Current level plus previous-day-close change. |
| `GET /api/v1/market-indicators/{symbol}/candles?interval=1m&count=6` | Latest six one-minute index candles for `KOSPI` or `KOSDAQ` | Five-minute rapid-move comparison. |
| `GET /api/v1/market-calendar/KR` | KRX/NXT market-session timetable | Suppress checks outside the regular session and on holidays. |

The stock-level `warnings` API exposes VI and trading restrictions for one symbol, but it is not the requested market-wide signal and remains out of this alert's first scope.

### Scope

The product is a factual market-condition alert: notify only when KOSPI or KOSDAQ crosses an approved same-day or five-minute movement threshold. It is not a scheduled market briefing, Top2 message, stock selection change, or trading instruction.

| Area | First implementation |
| --- | --- |
| Universe | KOSPI and KOSDAQ only. |
| Source | Toss indicator price and 1-minute candle endpoints only. |
| Window | Korean regular session only, gated by Toss market calendar. |
| State | Reuse the existing delivery log for per-index, direction, threshold-bucket dedupe; no new table. |
| Telegram text | Index, current level, same-day change, five-minute change, observed KST time, and source label. |
| Excluded | Sidecar/circuit-breaker claim, Top2 changes, individual-stock warning polling, public score, buy/sell wording, account/order APIs. |

### Trigger Contract Requiring Approval

The API supplies the measurements, but it does not define what the operator considers “급격한”. Set these values explicitly before implementation; do not silently choose them:

| Setting | Meaning | Candidate default for review only |
| --- | --- | --- |
| `daily_change_threshold` | Absolute change from previous close that can alert | KOSPI `2.0%`, KOSDAQ `2.5%` |
| `five_minute_change_threshold` | Absolute change from the oldest of six one-minute candles | KOSPI `0.8%`, KOSDAQ `1.0%` |
| `cooldown_minutes` | Suppress same index/direction/threshold-bucket repeats | `30` minutes |
| `check_interval_minutes` | Regular-session source check cadence | `1` minute |

Crossing a threshold sends one factual alert. A later opposite-direction crossing uses a distinct direction key. A duplicate within the cooldown is suppressed. Missing candles, stale timestamps, or provider errors create an operator event/skip reason but never a fabricated market-state alert.

### Display Contract

```text
시장 급변 참고 · Toss 10:15
- KOSPI 6,461.49 (-5.94%) · 5분 -0.92%
- 기준: Toss 실시간 지수 / 관찰용 알림
```

The message must not state or imply a market-wide halt, sidecar, investment recommendation, buy/sell decision, forecast, or Top2 priority update. It reports only observed index moves and their timestamps.

### Implementation Sequence

1. Add exact read-only endpoint validation for the two indicator calls and the KR market calendar; keep account/order endpoint groups rejected.
2. Add one bounded `scheduled-market-rapid-move-alert` command that exits outside the market-calendar regular session.
3. Calculate previous-close and five-minute percentage changes, validate timestamps, and apply the approved threshold/cooldown keys through the existing delivery-log dedupe mechanism.
4. Send only a threshold-crossing Telegram text; write a clear skip reason for non-crossing, missing, stale, or provider-failure paths.
5. Register it only after a dry-run and one explicit Telegram test send confirm message length, duplicate suppression, and regular-session behavior.

### Acceptance Criteria

- Only KOSPI/KOSDAQ official indicator and market-calendar calls occur; no account, asset, holding, order, or stock-selection request occurs.
- The alert uses an explicit approved threshold, five-minute comparison, timestamp, and direction.
- One index/direction/threshold bucket cannot duplicate inside its cooldown, including across process restarts.
- Provider failure cannot generate an alert or block existing report/market-briefing deliveries.
- Fixture tests cover threshold crossing, no crossing, cooldown, opposite direction, stale/missing candle data, outside-session skip, and provider failure.

The KRX and investor-flow material below is retained as a historical-reference runbook only. It is not a normal scheduler, web-view, or close-snapshot fallback path.

## Included sections
- KRX Market Data Runbook
- ETF / Flow Source Study
- KRX API Field Validation
- KRX Flow Execution Stages
- KRX Flow Sample Capture Runbook
- KRX Investor Flow Schema
- KRX Investor Flow Source Plan

<!-- Merged from: docs/codex/market-data-runbook.md -->
## Historical KRX Market Data Runbook

## Purpose

This is the consolidated historical KRX and market-reference runbook.

Use this only for existing KRX records, historical analysis, or an explicitly approved reintroduction. The active web-view and scheduler source is Toss OpenAPI.

## Source Ownership

| Data | Source | Current use |
| --- | --- | --- |
| Research reports | Naver Stock research pages | Report collection, summaries, Telegram, web-view reports. |
| Stock, ETF, index daily price/volume/turnover | KRX Open API | Historical rows only; not an active web-view or scheduler source. |
| Investor flow `[12008]`, `[12009]`, `[12010]` | KRX Data Marketplace | Historical/sample rows only; not an active scheduler source. |
| Future intraday quote/turnover/index | Toss Securities Open API, KIS, or another approved source | Separate lab/staging lane first; may later affect top-2 observation priority after approval. |
| 업종/테마 | Naver taxonomy for now | Category rollups and dated snapshots; do not call this KRX-owned taxonomy yet. |

Display naming follows [data-governance.md](/docs/codex/data-governance.md).

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
| `2026-05-19` | 6/6 endpoints were `not_published` through unrestricted-network `07:28:32`; at unrestricted-network `08:28:38`, ETF/stock endpoints became `partial` and index endpoints became `available`, with reference date `2026-05-19`, raw rows `4011`, and parsed rows `3701`. At `09:17 KST`, after `db-verify`, backup `stock_monitor_{timestamp}_{tag}.db`, and restore-smoke success, a bounded live `krx-backfill-missing daily --to-date 2026-05-19 --max-dates 1` stored ETF `874`, KOSPI stock `923`, KOSDAQ stock `1777`, KRX index `36`, KOSPI index `51`, and KOSDAQ index `40` rows with `incomplete_endpoints=0`. |
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
| `2026-05-15` | Latest backed-up mini PC retry at `2026-05-17T08:17` KST used `data/backups/stock_monitor_{timestamp}_{tag}.db`, reached all 6 daily endpoints, and stored ETF 874 rows, stock 2701 rows, and index 127 rows with `incomplete_endpoints=0`. Post-success backup `data/backups/stock_monitor_{timestamp}_{tag}.db` was restore-smoked successfully. Earlier backed-up retries at `06:40`, `01:19`, and `00:52` returned empty rows. |
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

Detailed capture history remains in the original KRX detail documents listed from [documentation-index.md](/docs/codex/documentation-index.md).

## Non-Negotiables

- Do not store credentials outside local `.env`.
- Do not expose KRX credentials, cookies, headers, DB paths, or scheduler internals in `web-view`.
- Do not treat KRX flow alone as a trading recommendation or public numeric score. It may support observation-candidate ordering when combined with other stored evidence.
- Do not infer investor flow from report counts.
- Do not silently scale units; preserve screen/API units explicitly.
- Do not mix future category snapshots into older dates.


<!-- Merged from: docs/codex/market-data-runbook.md -->
## ETF / Flow Source Study

## Purpose

This note fixes the first source-study baseline for ETF and flow data.
It is not an ingest implementation plan yet.

The goal is to support the read-only `web-view` with separate evidence layers:

- report activity: already collected from Naver research
- ETF reference: market/theme/index context
- flow/supply-demand: volume, turnover, foreign/institution/individual direction

Do not merge ETF or flow data into `reports` or `daily_stock_summaries`.
They should stay as separate datasets and be joined only in read-only query/view models.

## Source Decision

| Layer | First candidate | Status | Reason |
| --- | --- | --- | --- |
| ETF daily reference | KRX Open API `ETF 일별매매정보` | Preferred first source | Official KRX source, EOD-oriented, separate from company reports. |
| Stock daily price/volume/turnover | KRX Open API `유가증권 일별매매정보`, `코스닥 일별매매정보` | Preferred first source | Official daily market data available by market. |
| Stock investor flow | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Preferred validation source | Official KRX screen source for stock-level investor buy/sell/net-buy by investor type; request contract still needs tracing. |
| Market investor flow | KRX Data Marketplace `[12008] 투자자별 거래실적` | P1 validation source | Market-wide background for whether the day was foreign-led, institution-led, or individual-led. |
| Investor net-buy ranking | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | P1 validation source | Discovery/reference list for names receiving strong investor-category net buying. |
| KIS Developers investor flow | KIS Developers domestic stock market-analysis APIs | Deferred fallback | Use if KRX Data Marketplace proves unsuitable or unstable; requires KIS app credentials and token handling. |
| Current price / sector already used today | Naver stock detail API | Keep as existing tactical source | Already integrated for current price and sector metadata, but treat as unofficial and not the core flow source. |
| Historical helper libraries | `pykrx-openapi`, other wrappers | Optional helper only | Can reduce implementation work later, but should not become the source contract before official endpoint behavior is verified. |

Practical v1 recommendation:

1. Use KRX Open API first for ETF daily snapshots and stock daily market snapshots. This is implemented for the approved daily stock/ETF/index endpoints and currently used as read-only market reference data.
2. Validate KRX Data Marketplace `[12009]` first for investor flow, then `[12008]` and `[12010]` for background/ranking.
3. Do not add scoring, grade, or third-day alerts until at least several weeks of joined report/flow examples are reviewed.

## Why KRX First

KRX is the cleanest first source for after-market review because the planned view is not a trading bot.
The project needs end-of-day context more than real-time execution:

- ETF code/name, close, change, volume, turnover
- stock close, volume, turnover
- date-bound market snapshots that align with Korean business dates

KRX Open API requires membership, an authentication key request, and service usage approval.
The operator requested issuance up to the P2 scope on 2026-05-08.
That is acceptable for a later implementation step, but it means ingest code should not be started until the exact approved API products, endpoint IDs, response fields, and one-date samples are confirmed.

## Why KRX Data Marketplace Is Now The First Flow Candidate

The approved KRX Open API specs do not include investor-category flow fields, but the logged-in KRX Data Marketplace screen exposes the needed investor-flow tables.

Confirmed screens are tracked in [market-data-runbook.md](/docs/codex/market-data-runbook.md):

| Screen | Use |
| --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Core stock-level flow for report-related stocks. |
| `[12008] 투자자별 거래실적` | Market-wide background flow. |
| `[12010] 투자자별 순매수상위종목` | Top net-buy reference/discovery list. |

This should be validated before KIS because it keeps the first flow source in the KRX ecosystem and avoids extra credential/token handling.

## Why KIS Is Deferred But Important

KIS Developers exposes many domestic stock APIs, including ETF/ETN current price, ETF constituent price, stock investor trend, market investor trend, and real-time APIs.
This is attractive for flow and possibly richer ETF details.

The tradeoff is operational complexity:

- app key / app secret / token handling
- per-endpoint permissions and terms
- possible account linkage
- rate limits and token refresh
- more sensitive local `.env` handling

Therefore, KIS should be treated as a fallback source track:

- use it if KRX Data Marketplace cannot provide stable request/response behavior
- keep credentials out of admin GUI editing
- store only derived daily snapshots, not raw credentials or account data

## Minimum Data Model

These are planning shapes, not committed migrations.

```text
etf_metadata(
  etf_code,
  etf_name,
  provider,
  reference_index,
  category,
  source,
  updated_at
)

etf_daily_snapshots(
  business_date,
  etf_code,
  close_price,
  change_percent,
  volume,
  turnover,
  nav,
  fetched_at,
  source,
  primary key (business_date, etf_code, source)
)

stock_market_daily(
  business_date,
  stock_code,
  close_price,
  change_percent,
  volume,
  turnover,
  market,
  fetched_at,
  source,
  primary key (business_date, stock_code, source)
)

stock_flow_daily(
  business_date,
  stock_code,
  individual_net,
  foreign_net,
  institution_net,
  volume,
  turnover,
  fetched_at,
  source,
  primary key (business_date, stock_code, source)
)
```

Actual KRX Data Marketplace flow migrations should use the more explicit candidate shapes in [market-data-runbook.md](/docs/codex/market-data-runbook.md), including separate stock-level, market-level, and top-net-buy tables.

Keep `stock_market_daily` and investor-flow tables separate at first.
Some sources may provide price/volume without investor categories, while others may provide investor trend without the preferred close/turnover fields.

## Read-Only Web-View Use

Initial user-facing output should be descriptive:

| View | First output |
| --- | --- |
| Daily review | Reported stocks plus close/change/volume/turnover when available. |
| Flow snapshot | For report-related stocks, show foreign/institution/individual net direction from `[12009]` if the source is available. |
| Sector/theme rotation | Show report activity and flow direction side by side, explicitly as separate evidence. |
| ETF reference | ETF code/name, category/index, close/change, volume/turnover. |

Avoid phrases that imply certainty, such as `주도 섹터 확정`, until the source and history are strong enough.
Use wording like:

- `리포트 집중`
- `수급 동반`
- `거래대금 증가`
- `후속 확인 필요`

## Implementation Sequence

| Step | Work | Output |
| --- | --- | --- |
| 1 | Confirm approved KRX API products and response fields | Field contract note with sample response saved under docs. |
| 1A | Trace KRX Data Marketplace `[12009]` request contract | Endpoint, params, unit behavior, response root, and one masked/local sample. |
| 2 | Add config placeholders only after source choice | `.env.example` entries for API key names, no real secrets. |
| 3 | Add DB migrations for daily snapshots | New ETF/market/flow tables with idempotent upsert rules. |
| 4 | Add manual dry-run CLI | Fetch one date or one stock/date without changing Telegram behavior. |
| 5 | Add read-only repository queries | Date-bound joins against report summaries. |
| 6 | Add web-view cards/tables | Display only; no alert/scoring. |
| 7 | Review several weeks of data | Decide whether third-day interest alert or scoring is justified. |

## Risks And Guardrails

| Risk | Guardrail |
| --- | --- |
| Official API approval or field availability differs from docs | Start with manual field validation before schema migration. |
| KRX Data Marketplace request contract changes | Keep `source='krx_data_market'`, isolate fetch code, and add dry-run/smoke tests before scheduled ingestion. |
| KIS credentials increase secret-management burden | Keep credentials in `.env`, never in admin GUI or Telegram. |
| ETF data shape differs from company report data | Store in separate ETF tables and expose through separate views. |
| Investor flow categories can be interpreted too aggressively | Show raw direction and amounts first; no scoring until reviewed. |
| Naver unofficial endpoints can drift | Do not make them the only source for flow/ETF. |
| EOD timing may lag around close | Store `fetched_at` and display source/timestamp in admin/web-view. |

## Current Recommendation

For the next implementation batch, do not build a full ingest yet.
Do a narrow source validation batch:

1. fill `data/krx_api_intake.local.md` with non-secret approved-service details
2. keep the real `AUTH_KEY` only in local `.env`
3. capture one ETF daily response and one KOSPI/KOSDAQ daily response
4. trace KRX Data Marketplace `[12009]`, then `[12008]` and `[12010]`
5. only then add migrations and a manual `fetch-market-daily` style CLI

The field-validation checklist is tracked separately in [market-data-runbook.md](/docs/codex/market-data-runbook.md).


<!-- Merged from: docs/codex/market-data-runbook.md -->
## KRX API Field Validation

## Purpose

This document tracks the post-approval validation step before KRX data is added to code or SQLite tables.
It is intentionally a field-contract document, not an ingest implementation.

## Current Status

| Item | Status | Note |
| --- | --- | --- |
| KRX Open API account/service request | In progress | Operator requested issuance up to the P2 scope on 2026-05-08. |
| Real `AUTH_KEY` storage | Locally configured | Store only in local `.env` as `STOCK_MONITOR_KRX_AUTH_KEY`; do not print or copy into docs. |
| Approved service detail capture | Done | 8 provided docx specs were parsed into `data/krx_api_intake.local.md`. |
| One-date sample response capture | Done | 8 provided endpoints responded successfully for `basDd=20260507`; first-row samples are saved in `data/krx_api_dry_run_samples.local.json`. |
| DB migration | Done | Migration v2 added KRX stock/ETF/metadata/index snapshot tables. |
| Repeatable dry-run CLI | Done | `python -m stock_monitor krx-dry-run <endpoint|all> --date YYYY-MM-DD` prints row counts and fields without saving. |
| Manual ingest/upsert | First pass done | `python -m stock_monitor krx-fetch-snapshot <endpoint|all> --date YYYY-MM-DD` parses and upserts KRX snapshots. |
| Read/query methods | First pass done | `krx-query-snapshot` can read stored stock, ETF, and index snapshots by date. |
| Admin display | First pass done | `operator-status` and `admin-gui` expose latest KRX KOSPI/KOSDAQ/ETF/index snapshot tables from stored data. |
| KRX Data Marketplace investor-flow screen check | Screen validated | Logged-in KRX Data Marketplace screen confirms `[12008]`, `[12009]`, and `[12010]`; request contract still needs tracing before code. |
| Data Marketplace dry-run CLI | First pass done | `krx-flow-dry-run` can call `[12009]` candidate requests without DB writes after `isuCd` is provided or resolved from stored KRX metadata. |

## Local Intake File

Use:

- `data/krx_api_intake.local.md`

That file is under `data/`, so it is intentionally local-only.
It now contains the parsed endpoint URLs and response fields from `data/API_Specification/*.docx`.
It can also contain masked real sample responses later.

Do not store the real `AUTH_KEY` in documentation.
Use `.env` only:

```env
STOCK_MONITOR_KRX_AUTH_KEY=
STOCK_MONITOR_KRX_BASE_URL={KRX_OPENAPI_BASE_URL}
STOCK_MONITOR_KRX_DATA_MARKET_BASE_URL={KRX_DATA_MARKET_BASE_URL}
STOCK_MONITOR_KRX_DATA_MARKET_ID=
STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD=
STOCK_MONITOR_KRX_TIMEOUT_SECONDS=30
```

## Required First-Pass Services

| Priority | Service | Why Needed | Expected Project Layer |
| --- | --- | --- | --- |
| P1 | 유가증권 일별매매정보 | KOSPI stock close, volume, turnover, market-cap context | `stock_market_daily` candidate |
| P1 | 코스닥 일별매매정보 | KOSDAQ stock close, volume, turnover, market-cap context | `stock_market_daily` candidate |
| P1 | ETF 일별매매정보 | ETF close, NAV, volume, turnover context | `etf_daily_snapshots` candidate |
| P2 | 종목기본정보 | Code/name/market metadata verification and code mapping | `stock_metadata` enrichment candidate |
| P2 | 지수 일별매매정보 | Market/index context for after-market web-view | `market_index_daily` candidate |
| P0 | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Report-stock foreign/institution/individual flow | `stock_investor_flow_daily` candidate; not part of approved Open API specs |
| P1 | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide investor background | `market_investor_flow_daily` candidate; not part of approved Open API specs |
| P1 | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Investor-category top net-buy names | `investor_net_buy_top_daily` candidate; not part of approved Open API specs |

## KRX Data Marketplace Request Candidates

These are not approved Open API endpoints.
They are candidate screen-backed request contracts that still need a dry-run validation step before DB migrations.

| Screen | Candidate BLD | Candidate params | Validation status |
| --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | `dbms/MDC/STAT/standard/MDCSTAT02201` | `strtDd`, `endDd`, `mktId`, `etf`, `etn`, `elw` | Candidate only. |
| `[12009] 투자자별 거래실적(개별종목)` 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02301` | `strtDd`, `endDd`, `isuCd` | Candidate only; `isuCd` mapping required. |
| `[12009] 투자자별 거래실적(개별종목)` 일별추이 | `dbms/MDC/STAT/standard/MDCSTAT02302` | `strtDd`, `endDd`, `isuCd`, `trdVolVal`, `askBid` | Candidate only; use after period aggregate works. |
| `[12010] 투자자별 순매수상위종목` | `dbms/MDC/STAT/standard/MDCSTAT02401` | `strtDd`, `endDd`, `mktId`, `invstTpCd` | Candidate only. |

Dry-run acceptance requirements:

1. Print the screen number, BLD, full non-secret params, source unit labels, raw row count, and normalized row preview.
2. Confirm how 6-digit `stock_code` maps to `[12009]` `isuCd`.
3. Save no cookies, browser session tokens, or login state into the project.
4. Keep result rows out of production DB until units, investor labels, and duplicate keys are stable.

Current dry-run commands:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view market --date YYYY-MM-DD --market STK --value amount --side net-buy --show-first-row
python -m stock_monitor krx-flow-dry-run --view top --date YYYY-MM-DD --market STK --investor foreign --show-first-row
```

If stored KRX metadata is missing, fetch approved basic metadata first or pass `--isu-cd` explicitly for one-off validation.
Before live Data Marketplace calls, use `krx-flow-login-check --date YYYY-MM-DD --market STK` to verify local `.env` raw login and the representative `[12008]` endpoint without DB writes.
If the response body is `LOGOUT`, treat it as an authentication failure and do not write DB rows.

## Field Capture Requirements

For every approved endpoint, capture:

- service name
- API ID
- request URL
- method and content type
- required parameters
- date parameter name and date format
- paging or row-limit behavior
- response root path
- response success/error shape
- full output field list
- one small masked sample response

## Minimum Field Mapping To Confirm

### Stock Daily Market Data

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Must align to Korean trading date. |
| `stock_code` | Yes | Prefer 6-digit code. |
| `stock_name` | Yes | Useful for validation, not primary key. |
| `market` | Yes | KOSPI/KOSDAQ separation. |
| `close_price` | Yes | Required for web-view context. |
| `change_amount` | Optional | Useful display field. |
| `change_percent` | Yes | Required for strong/weak list. |
| `open_price` | Optional | Useful later. |
| `high_price` | Optional | Useful later. |
| `low_price` | Optional | Useful later. |
| `volume` | Yes | Required for attention/flow context. |
| `turnover` | Yes | Required for trading-value context. |
| `market_cap` | Optional | Useful for ranking normalization. |

### ETF Daily Data

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Trading date. |
| `etf_code` | Yes | ETF identifier. |
| `etf_name` | Yes | Display/search. |
| `close_price` | Yes | Display. |
| `change_amount` | Optional | Display. |
| `change_percent` | Yes | Ranking/context. |
| `nav` | Yes if available | ETF-specific value. |
| `volume` | Yes | Liquidity context. |
| `turnover` | Yes | Trading-value context. |
| `aum_or_net_assets` | Optional | Useful for ETF scale. |
| `underlying_index` | Optional | May come from metadata rather than daily data. |

### Investor Flow Data

The approved KRX Open API specs do not expose it, but KRX Data Marketplace screens do.
Use [market-data-runbook.md](/docs/codex/market-data-runbook.md) as the source-boundary document.

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Trading date. |
| `stock_code` | Yes | Join key. |
| `individual_net` | Yes | Individual net buy/sell. |
| `foreign_net` | Yes | Foreign net buy/sell. |
| `institution_net` | Yes | Institution net buy/sell. |
| `source_unit` | Yes | Shares, KRW, or other unit must be explicit. |

Confirmed Data Marketplace screen columns for `[12009]` include investor type, sell/buy/net-buy volume, and sell/buy/net-buy trading amount.
The screen allows unit choices for shares and money, so the ingest contract must persist the chosen units.

## Validation Output

After the local intake file is filled and one-date API calls are validated, the next Codex task should produce:

1. confirmed endpoint list
2. accepted/rejected field mapping table
3. missing fields and fallback source recommendation
4. proposed DB table list, still without applying migrations
5. proposed manual dry-run CLI contract

## Parsed Spec Summary

| Service | Endpoint | Priority | First use |
| --- | --- | --- | --- |
| ETF 일별매매정보 | `/svc/apis/etp/etf_bydd_trd` | P1 | ETF daily snapshot |
| 유가증권 일별매매정보 | `/svc/apis/sto/stk_bydd_trd` | P1 | KOSPI stock daily market data |
| 코스닥 일별매매정보 | `/svc/apis/sto/ksq_bydd_trd` | P1 | KOSDAQ stock daily market data |
| 유가증권 종목기본정보 | `/svc/apis/sto/stk_isu_base_info` | P2 | KOSPI stock metadata |
| 코스닥 종목기본정보 | `/svc/apis/sto/ksq_isu_base_info` | P2 | KOSDAQ stock metadata |
| KRX 시리즈 일별시세정보 | `/svc/apis/idx/krx_dd_trd` | P2 | Market index context |
| KOSPI 시리즈 일별시세정보 | `/svc/apis/idx/kospi_dd_trd` | P2 | KOSPI index context |
| KOSDAQ 시리즈 일별시세정보 | `/svc/apis/idx/kosdaq_dd_trd` | P2 | KOSDAQ index context |

Dry-run result:

Sample file: `data/krx_api_dry_run_samples.local.json`

| Service | Rows | Status |
| --- | ---: | --- |
| ETF 일별매매정보 | 1099 | OK |
| 유가증권 일별매매정보 | 948 | OK |
| 코스닥 일별매매정보 | 1822 | OK |
| 유가증권 종목기본정보 | 948 | OK |
| 코스닥 종목기본정보 | 1822 | OK |
| KRX 시리즈 일별시세정보 | 34 | OK |
| KOSPI 시리즈 일별시세정보 | 51 | OK |
| KOSDAQ 시리즈 일별시세정보 | 40 | OK |

Resolved validation points:

- auth placement is request header field `AUTH_KEY`
- HTTP method is `POST`
- body is JSON with `basDd`
- response root is `OutBlock_1`

Open validation questions:

- daily stock `ISU_CD` must be checked to confirm whether it is the 6-digit join key
- KOSPI daily `ISU_CD` validation kept 923 of 948 rows for `2026-05-07`; non-6-digit rows are skipped until their instrument class is reviewed
- investor-category flow is not covered by the provided KRX Open API specs
- KRX Data Marketplace `[12009]`, `[12008]`, and `[12010]` request endpoint/params/response roots are Stage 4 validated for two business dates
- Scheduled ingestion is still disabled until separate approval

## Guardrails

- Do not paste real API keys into chat, docs, screenshots, or Telegram.
- Do not enable broad scheduled Data Marketplace ingest until separate approval. The only current automatic exception is `StockMonitor-KrxMentionedFlowBackfill`, limited to same-day report-mentioned stocks and `[12009]` stock-level rows.
- Do not mix ETF rows into company report tables.
- Do not infer investor flow from report count.
- Keep KRX daily market snapshots separate from current Naver quote lookups.


<!-- Merged from: docs/codex/market-data-runbook.md -->
## KRX Flow Execution Stages

This document fixes the execution stages for KRX Data Marketplace investor-flow expansion.
Use these stage numbers when requesting work, for example: `Stage 2까지 진행` or `Stage 4까지 밀어`.

## Current Rule

Scheduled KRX Data Marketplace ingest remains disabled even after Stage 4/5 validation.
Stage 6 first design exists, but actual scheduled ingest enablement requires separate explicit approval.

Current status:

| Item | Status |
| --- | --- |
| `2026-05-08` Stage 1 | Done. Raw-network JSON bodies exist for 7 manifests. |
| `2026-05-08` Stage 2 | Done. Strict raw validation passed for 7 manifests. |
| `2026-05-08` Stage 3 | Done with `--allow-right-extra-top-rows`. `[12010]` raw response is a compatible superset of the visible-grid sample. |
| `2026-05-07` Stage 1 | Done. Raw-network JSON bodies exist for 7 manifests under `data\krx_samples_raw_20260507`. |
| `2026-05-07` Stage 2 | Done. Strict raw validation passed for 7 manifests. |
| `2026-05-07` Stage 3 | Done with `--allow-right-extra-top-rows`. Visible-grid baseline exists under `data\krx_samples_visible_20260507` and matches raw rows. |
| Stage 4 | Done. Two business dates have strict raw validation and visible-grid/raw parity success. |
| Stage 5 | Done. User `web-view` has a GET-only read-only investor-flow trend route and section from stored samples. |

## Stage Table

| Stage | Name | Goal | Completion Criteria |
| ---: | --- | --- | --- |
| 0 | Baseline fixed | Keep the visible-grid sample import and raw sample directory state clear. | Visible-grid samples and raw manifest/sample directories are documented, and scheduled ingest is disabled. |
| 1 | Raw response fill | Put raw-network JSON response bodies into `data\krx_samples_raw`. | All 7 raw JSON files referenced by raw manifests exist. |
| 2 | Strict raw validation | Validate raw-network samples without login, network, or DB writes. | `krx-flow-validate-samples` passes for `data\krx_samples_raw`. |
| 3 | Visible/raw parity | Compare normalized visible-grid rows and raw-network rows. | `krx-flow-compare-samples` exits successfully. |
| 4 | Repeated business-day validation | Repeat Stages 1-3 for at least 2 business days. | At least 2 dates have strict raw validation and parity success. Current validated dates: `2026-05-08`, `2026-05-07`. |
| 5 | Read-only trend view | Add investor-flow trend display to user `web-view` without scoring. | Done: `GET /api/flow-trend?date=YYYY-MM-DD` and the user page show stored-sample `수급 흐름` only. |
| 6 | Scheduled ingest design | Design scheduled ingestion candidate without enabling it. | Done as a first draft below; actual enablement requires explicit approval. |

## Stage Details

| Stage | Entry Condition | Commands / Work | Stop Condition | Next Stage |
| ---: | --- | --- | --- | --- |
| 0 | Current project state after visible-grid import. | `python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw` | Raw placeholders are missing or scheduled ingest is accidentally enabled. | Stage 1 |
| 1 | Operator has raw response bodies from KRX Data Marketplace. | Save only JSON response bodies under `data\krx_samples_raw` using the manifest `sample_file` names. Do not save cookies, headers, credentials, screenshots, or account data. | Any file includes credentials, HTML login pages, `LOGOUT`, or non-JSON content. | Stage 2 |
| 2 | All raw sample files exist. | `python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized` | Strict validation fails, required investor rows are missing, or normalized row count is suspicious. | Stage 3 |
| 3 | Raw strict validation passed. | `python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw` | Any mismatch, missing manifest, or missing normalized row appears. | Stage 4 |
| 4 | One validated date exists. | Repeat Stage 1-3 on another business date using the same capture and validation policy. | Date-specific mismatch or inconsistent unit mapping appears. | Stage 5 |
| 5 | At least 2 validated dates exist. | Add GET-only web-view trend presentation from stored investor-flow rows. Keep labels descriptive and avoid public numeric score or trading-recommendation wording. | Display requires unvalidated source fields or suggests buy/sell judgment. | Stage 6 |
| 6 | Trend display is useful and stable. | Draft scheduled ingest design with login/session handling, retry, skip-on-LOGOUT, audit event, and manual enable gate. | Any design requires exposing KRX credentials, bypassing operator session policy, or enabling scheduled ingest without approval. | Separate approval |

## Fixed Commands

```powershell
python -m stock_monitor krx-flow-raw-sample-scaffold --source-manifest-dir data\krx_samples --output-dir data\krx_samples_raw
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw --allow-right-extra-top-rows
```

## Stage 1 Raw Files

`Stage 1` is complete only when these files exist and contain raw KRX Data Marketplace JSON response bodies:

```text
data\krx_samples_raw\12008_market_STK_20260508.local.json
data\krx_samples_raw\12009_017670_20260508.local.json
data\krx_samples_raw\12009_032640_20260508.local.json
data\krx_samples_raw\12009_079550_20260508.local.json
data\krx_samples_raw\12009_278470_20260508.local.json
data\krx_samples_raw\12009_329180_20260508.local.json
data\krx_samples_raw\12010_top_STK_20260508_foreign.local.json
```

After filling them, run:

```powershell
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
```

The second validated date uses:

```powershell
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw_20260507
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw_20260507 --normalized-dir data\krx_samples_raw_20260507\normalized
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_visible_20260507 --normalized-dir data\krx_samples_visible_20260507\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples_visible_20260507 --right-manifest-dir data\krx_samples_raw_20260507 --allow-right-extra-top-rows
```

## Stage 3 Top-Ranking Superset Rule

For `[12010]` top-ranking samples, the visible-grid DOM may expose only rendered rows while the raw response can contain the full ranked list.
This is acceptable only when every visible-grid row matches the raw response as an ordered prefix.
Use `--allow-right-extra-top-rows` for Stage 3 comparison and still fail on missing rows, changed values, changed order, or extra rows on non-top screens.

## Guardrails

- Keep `reports`, `daily_stock_summaries`, KRX Open API snapshots, and KRX Data Marketplace investor-flow rows separate.
- Treat imported flow as `수급 참고`. It may support observation-candidate ordering, but not a public numeric score, trading recommendation, or confirmed rotation signal.
- Preserve source units and do not infer scaling silently.
- Prefer `.env` raw login smoke-check via `krx-flow-login-check`; use operator-managed Chrome login/session only as fallback/debug.
- Stage 5 is complete, but scheduled ingest still requires a separate Stage 6 design and explicit approval before enablement.

## Stage 6 Draft Design

Stage 6 is design-only until the operator separately approves scheduled ingest enablement.

Required ingest contract:

| Guard | Required Behavior |
| --- | --- |
| Login check | Run `.env` Data Marketplace login smoke check before fetch work. |
| LOGOUT handling | If response indicates `LOGOUT`, record a skipped/failed operation event and write no flow rows. |
| Retry | Use bounded retry only for transient fetch failures; do not retry malformed business data blindly. |
| Event recording | Record run start, skip, failure, and success with date/view/row counts. |
| Batch size | Keep stock-level `[12009]` limited to leadership-candidate or same-day report-mentioned stock/date keys, not whole-market crawling. |
| Backup/verify | Require recent `db-verify` and backup before first real scheduled ingest enablement. |
| Partial writes | Avoid partial DB writes for failed login or malformed response sets. |
| Enable gate | Task registration/enablement is outside Stage 6 design and requires explicit approval. |

## Login Handling Decision

For source validation, prefer the local `.env` Data Marketplace login path and raw HTTP fetch.
This path performs warmup, login, and data POST with an in-memory cookie jar and does not save browser cookies, headers, or credentials.
Use this smoke check before future raw capture or ingest-design work:

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

The command verifies login and a representative `[12008]` JSON endpoint without DB writes.
It returns exit code `0` only when the endpoint returns rows; missing credentials, rejected login, `LOGOUT`, fetch failure, or empty rows return exit code `2`.

Browser UI login remains a fallback/debug path only:

| Path | Decision |
| --- | --- |
| Direct `{KRX_LOGIN_FALLBACK_PATH}` tab | Preferred browser fallback. It exposes the login fields without the wrapper iframe. |
| Wrapper `MDCCOMS001.cmd` iframe | Works, but is less stable and not needed when direct login page is available. |
| Chrome saved-password/PIN/Windows Hello | Manual-only. Do not automate OS/native security prompts. |
| Browser raw network capture | Not available in the current browser automation surface. |

If duplicate-login confirmation appears, selecting confirmation can replace the existing KRX web session.
Do this only during validation.
Keep broad scheduled ingest disabled until separate approval; the narrow same-day report-mentioned `[12009]` recent 31-day backfill task is the only automatic exception.


<!-- Merged from: docs/codex/market-data-runbook.md -->
## KRX Flow Sample Capture Runbook

This runbook fixes the manual capture process for KRX Data Marketplace investor-flow samples.
It is for validation only. Do not store credentials, cookies, tokens, or personal login payloads.

## Scope

| Screen | Purpose | Priority |
| --- | --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Leadership-candidate stock-level investor flow | P0 |
| `[12008] 투자자별 거래실적` | Market-wide investor background | P1 |
| `[12010] 투자자별 순매수상위종목` | Net-buy ranking by investor category | P1 |

## Capture Steps

1. Run candidate preview for the target date.

```powershell
python -m stock_monitor krx-flow-candidates --date YYYY-MM-DD --limit 10
```

2. Confirm request params before touching KRX Data Marketplace.

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code STOCKCODE --request-only
python -m stock_monitor krx-flow-dry-run --view market --date YYYY-MM-DD --market STK --value amount --side net-buy --request-only
python -m stock_monitor krx-flow-dry-run --view top --date YYYY-MM-DD --market STK --investor foreign --request-only
```

3. Prefer raw `.env` login smoke-check before any live Data Marketplace validation.

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

This verifies login and the representative `[12008]` endpoint without DB writes.
If it fails with `LOGOUT` or `auth_rejected`, use Chrome only as fallback/debug.

4. If browser fallback is needed, open the operator Chrome session and log in to KRX Data Marketplace.

- Use the Chrome extension-connected browser when available.
- Keep only the JSON response body. Do not save headers, cookies, credentials, or screenshots containing account details.
- If `[12009]` shows `개별종목을 검색해주세요`, close the dialog, select the stock, confirm `STOCKCODE/종목명`, then query again.

5. Save raw JSON under `data/krx_samples`.

| Screen | Raw filename |
| --- | --- |
| `[12009]` | `12009_STOCKCODE_YYYYMMDD.local.json` |
| `[12008]` | `12008_market_YYYYMMDD.local.json` |
| `[12010]` | `12010_top_YYYYMMDD_INVESTOR.local.json` |

5. Generate or copy a manifest and fill the explicit conditions.

| Screen | Template |
| --- | --- |
| `[12009]` | `data/krx_samples/templates/12009_stock.manifest.template.json` |
| `[12008]` | `data/krx_samples/templates/12008_market.manifest.template.json` |
| `[12010]` | `data/krx_samples/templates/12010_top.manifest.template.json` |

Preferred capture-set scaffold command:

```powershell
python -m stock_monitor krx-flow-sample-scaffold --date YYYY-MM-DD --stock-code STOCKCODE --market STK --top-investor foreign
python -m stock_monitor krx-flow-sample-scaffold --date YYYY-MM-DD --from-candidates --candidate-limit 5 --market STK --top-investor foreign
```

This writes `[12009]` stock, `[12008]` market, and `[12010]` top-ranking manifest scaffolds together.
Use `--from-candidates` when local daily summary and KRX snapshot data already exist for the date.

Single-manifest scaffold command:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code STOCKCODE --manifest-output data\krx_samples\12009_STOCKCODE_YYYYMMDD.manifest.local.json
```

6. Validate strictly and write a normalized artifact.

```powershell
python -m stock_monitor krx-flow-dry-run --date YYYY-MM-DD --sample-manifest data\krx_samples\MANIFEST.local.json --normalized-output data\krx_samples\NORMALIZED.local.json --strict-sample --show-first-row
```

7. After several manifests are captured, validate the batch before any ingest work.

```powershell
python -m stock_monitor krx-flow-capture-checklist --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized
python -m stock_monitor krx-flow-import-preview --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

`krx-flow-capture-checklist` converts manifests into an operator checklist: screen, condition, raw filename, manifest path, and validation command.
`krx-flow-sample-status` checks whether `[12008]`, `[12009]`, and `[12010]` manifests and sample files are present, then lists the next raw files to capture.
`krx-flow-validate-samples` performs no login, network call, or DB write. It fails if any manifest produces strict sample warnings unless `--allow-warnings` is explicit. Use `--normalized-dir` to write per-manifest normalized artifacts.
`krx-flow-import-preview` calculates the target SQLite investor-flow table row counts without writing rows.
`krx-flow-import-samples` writes rows only after explicit `--confirm --i-validated` and refuses samples with validation warnings.

## Visible Grid vs Raw Response Parity

The first imported `2026-05-08` sample set was captured from the logged-in visible grid DOM.
This is useful for user-facing validation, but scheduled ingest must not be enabled from visible-grid samples alone.

When raw-network response bodies are captured later, save them in a separate local directory such as `data\krx_samples_raw`.
Use the same manifest conditions and filenames whenever possible, then compare the normalized rows against the visible-grid baseline:

```powershell
python -m stock_monitor krx-flow-raw-sample-scaffold --source-manifest-dir data\krx_samples --output-dir data\krx_samples_raw
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw --allow-right-extra-top-rows
```

`krx-flow-raw-sample-scaffold` copies only manifest conditions from the visible-grid set and marks them as `capture_method=raw_network_response`.
It does not copy sample JSON files, so `krx-flow-sample-status` should report `sample=N` until raw response bodies are placed under `data\krx_samples_raw`.
`krx-flow-compare-samples` performs no login, network call, or DB write.
It compares normalized row values and ignores volatile fields such as fetch time/source.
Use `--allow-right-extra-top-rows` for `[12010]` because the visible grid can contain only rendered rows while the raw response contains the full ranked list. This option is valid only when visible rows match the raw rows as an ordered prefix.
If this command reports mismatches or missing manifests, keep broad scheduled ingest disabled and inspect the sample pair manually. The narrow same-day mentioned-stock `[12009]` task remains the only automatic exception.
For staged execution, treat raw body capture as `Stage 1`, strict raw validation as `Stage 2`, and visible-grid/raw parity comparison as `Stage 3` in [market-data-runbook.md](/docs/codex/market-data-runbook.md).

## Promotion Criteria

| Check | Required |
| --- | --- |
| Raw response has rows | Yes |
| Normalized rows exist | Yes |
| Units are explicit | Yes |
| `[12009]`/`[12008]` includes expected investors | `외국인`, `기관합계`, `개인` |
| Normalized artifact has no quality warnings | Yes |
| Visible-grid and raw-network normalized rows match | Yes, before scheduled ingest |
| SQLite write performed | Manual local sample import only after `--confirm --i-validated`; broad scheduled ingest remains disabled except the narrow same-day mentioned-stock `[12009]` backfill task. |

## Current Blocker

Scheduled ingest remains blocked until real `[12008]`, `[12009]`, and `[12010]` raw response samples pass strict validation and parity comparison against the visible-grid samples.


<!-- Merged from: docs/codex/market-data-runbook.md -->
## KRX Investor Flow Schema

## Purpose

This document fixes the SQLite storage contract for KRX Data Marketplace investor-flow data.

The schema is ready as additive migration v4, and Stage 4 raw/visible validation is complete for two business dates.
Scheduled ingest is still disabled until separate approval.

## Source Boundary

| Table | Source | Intended Use |
| --- | --- | --- |
| `stock_investor_flow_daily` | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Leadership-candidate stock/date flow context. |
| `market_investor_flow_daily` | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide background by investor type. |
| `investor_net_buy_top_daily` | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Discovery/ranking reference by market and investor type. |

These rows must stay separate from Naver research `reports`, `daily_stock_summaries`, and KRX Open API daily snapshot tables.

## Table Contract

| Table | Primary Key | Required Identity Fields | Numeric Fields |
| --- | --- | --- | --- |
| `stock_investor_flow_daily` | `business_date, stock_code, investor_type, source` | `business_date`, 6-digit `stock_code`, `investor_type`, `source`, `fetched_at` | sell/buy/net-buy volume and amount fields. |
| `market_investor_flow_daily` | `business_date, market, investor_type, source` | `business_date`, `market`, `investor_type`, `source`, `fetched_at` | sell/buy/net-buy volume and amount fields. |
| `investor_net_buy_top_daily` | `business_date, market, investor_type, rank, source` | `business_date`, `market`, `investor_type`, positive `rank`, 6-digit `stock_code`, `stock_name`, `source`, `fetched_at` | net-buy volume and amount fields. |

## Unit Policy

- Store source units explicitly in `volume_unit` and `amount_unit` for `[12008]` and `[12009]`.
- Do not guess or auto-scale units during sample validation.
- `N/A`, empty strings, and dash-like missing markers become `NULL` numeric values.
- Missing numeric values must not be treated as zero.

## DB Verify Gate

`python -m stock_monitor db-verify` now fails if any of these investor-flow quality issues are present:

| Check | Meaning |
| --- | --- |
| `stock_invalid_code` | `[12009]` row has a non-6-digit stock code. |
| `stock_missing_units` | `[12009]` row is missing `volume_unit` or `amount_unit`. |
| `stock_no_numeric_flow` | `[12009]` row has no numeric volume or amount values. |
| `market_missing_units` | `[12008]` row is missing `volume_unit` or `amount_unit`. |
| `market_no_numeric_flow` | `[12008]` row has no numeric volume or amount values. |
| `top_invalid_rank` | `[12010]` row has rank less than 1. |
| `top_invalid_code` | `[12010]` row has a non-6-digit stock code. |
| `top_no_net_buy` | `[12010]` row has neither net-buy volume nor net-buy amount. |

This makes bad rows visible before they affect web-view cards or future analysis.

## Promotion Conditions

Scheduled investor-flow ingest remains blocked until all conditions are met:

1. Raw endpoint samples for `[12008]`, `[12009]`, and `[12010]` are captured.
2. Sample manifests preserve screen/date/filter/unit conditions.
3. `krx-flow-dry-run --strict-sample` passes on representative samples.
4. `db-verify` passes after test inserts into a non-production database.
5. Ingest scope remains bounded to leadership candidates, market background, and top rankings.

Manual local sample import is allowed only through:

```powershell
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

This path refuses warning samples and writes only parsed local raw samples. It does not call KRX, does not log in, and does not enable scheduled collection.

## Operational Rule

Investor flow is a reference signal only. It may support observation-candidate ordering, but do not label it as a trading recommendation, public numeric score, or confirmed sector rotation until enough history and explicit rules exist.


<!-- Merged from: docs/codex/market-data-runbook.md -->
## KRX Investor Flow Source Plan

## Purpose

This document fixes the source boundary for investor-flow data discovered on the KRX Data Marketplace host.
It is a planning and validation note, not an ingest implementation.

The goal is to add source-backed supply/demand context without mixing it into the existing Naver report tables.

## Confirmed KRX Data Marketplace Screens

| Priority | Screen | Screen No. | Role |
| --- | --- | --- | --- |
| P0 | 투자자별 거래실적(개별종목) | `[12009]` | Core stock-level flow for reported stocks. |
| P1 | 투자자별 거래실적 | `[12008]` | Market-wide investor background. |
| P1 | 투자자별 순매수상위종목 | `[12010]` | Discovery/ranking view for strong net-buy names. |

Confirmed navigation:

```text
기본 통계 > 주식 > 거래실적
```

Confirmed menu IDs from Chrome-extension validation:

| Screen | Menu ID | Screen title | Navigation status |
| --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | `MDC0201020301` | `[12008] 투자자별 거래실적` | Main page -> menu navigation succeeds. |
| `[12009] 투자자별 거래실적(개별종목)` | `MDC0201020302` | `[12009] 투자자별 거래실적(개별종목)` | Main page -> menu navigation succeeds; stock-name direct input plus `Enter` resolves the selector. |
| `[12010] 투자자별 순매수상위종목` | `MDC0201020303` | `[12010] 투자자별 순매수상위종목` | Main page -> menu navigation succeeds. |

Validation notes:

- Directly opening BLD-like URLs such as `MDCSTAT02201` is not the screen route. Use the menu IDs above for browser validation.
- The internal request BLDs remain separate from the browser route IDs and are still candidates until payload/response tracing is complete.
- `[12008]` and `[12010]` expose a `조회` control with default conditions after menu navigation.
- `[12009]` blocks query without stock selection and shows `개별종목을 검색해주세요`.
- The stock field accepts direct stock-name typing. Typing `삼성전자` and pressing `Enter` resolves the selector to `005930/삼성전자`; after that, `조회` returns the investor-flow table.
- Keep the direct-input flow as the browser-validation path. Programmatic ingest still needs a stable `stock_code` to KRX issue-code mapping before scheduled collection.

Browser validation guard for `[12009]`:

1. Inspect the visible page state first, not only hidden/internal form values.
2. If `개별종목을 검색해주세요` is visible, click the visible `닫기` button before typing or querying again.
3. Type the stock name into `tboxisuCd_finder_stkisu0_0`.
4. Press `Enter` and wait until the visible input resolves to `NNNNNN/종목명`.
5. Click `조회` only after the visible selector is resolved.
6. Treat a reappearing `개별종목을 검색해주세요` message as selector failure and do not proceed to data collection.

Pseudo flow:

```text
if visible_text includes "개별종목을 검색해주세요":
  click visible "닫기"
type stock name
press Enter
wait for visible input matching "\d{6}/"
if not matched:
  stop as unresolved stock selector
click "조회"
```

Observed `[12009]` columns:

| Group | Columns |
| --- | --- |
| 투자자구분 | 금융투자, 보험, 투신, 사모, 은행, 기타금융, 연기금 등, 기관합계, 기타법인, 개인, 외국인, 기타외국인, 전체 |
| 거래량 | 매도, 매수, 순매수 |
| 거래대금 | 매도, 매수, 순매수 |

## Source Decision

| Source | Status | Use |
| --- | --- | --- |
| KRX Open API approved daily endpoints | Implemented for price/volume/turnover snapshots | Market reference and exact-date stock/ETF/index context. |
| KRX Data Marketplace `[12009]` | Stage 4 source validation complete for two business dates | First source candidate for stock-level investor flow. |
| KRX Data Marketplace `[12008]` | Stage 4 source validation complete for two business dates | Market-wide flow background after `[12009]`. |
| KRX Data Marketplace `[12010]` | Stage 4 source validation complete for two business dates | Net-buy ranking/reference after `[12009]`. |
| Naver internal stock trend API | Confirmed but unofficial | Fallback or comparison source only. |
| KIS Developers | Deferred candidate | Use only if KRX Data Marketplace proves unsuitable or unstable. |

## API vs Screen-Based Collection Rule

| Data | Collection mode | Reason |
| --- | --- | --- |
| KOSPI/KOSDAQ daily stock price, volume, turnover | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| ETF daily trading data | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| KRX/KOSPI/KOSDAQ index daily data | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| Stock basic metadata | KRX Open API, explicit only | Approved API specs exist, but it should not replace sector/theme labels until field meaning is reviewed. |
| Stock-level investor flow | KRX Data Marketplace `[12009]` | Not present in the approved Open API specs; screen contract must be followed. |
| Market-wide investor flow | KRX Data Marketplace `[12008]` | Not present in the approved Open API specs; screen contract must be followed. |
| Investor net-buy ranking | KRX Data Marketplace `[12010]` | Not present in the approved Open API specs; screen contract must be followed. |

Rules:

1. Use KRX Open API whenever the approved API provides the needed data.
2. Use KRX Data Marketplace only for data absent from the approved Open API specs.
3. For screen-based data, preserve the screen conditions exactly: query type, stock selection, date range, market filter, investor category, share unit, and money unit.
4. Store `source='krx_open_api'` and `source='krx_data_market'` separately.
5. Do not implement scheduled screen-based ingestion until a dry-run command can print the exact normalized rows and source units.

## Collection Timing

| Environment | Recommended time | Reason |
| --- | --- | --- |
| Main desktop validation | `16:50` KST or later | KRX/Data Marketplace values may lag by about 20 minutes. |
| Future N100 always-on host | `18:30~19:30` KST | Safer after close and possible NXT-related timing noise. |

## Historical Range Decision

Use different windows for different data layers.

| Layer | Default analysis window | Storage target | Reason |
| --- | ---: | ---: | --- |
| KRX Open API stock/ETF/index daily snapshots | 3 months | 6 months | Price, volume, turnover, and index context are low-risk API data and already small enough in SQLite. |
| KRX Data Marketplace stock-level investor flow `[12009]` | 20 trading days first, then 3 months | 6 months after stable validation | Screen-backed source is more fragile and session-dependent, so collect only leadership candidates, not every report stock. |
| KRX Data Marketplace market-wide investor flow `[12008]` | 3 months | 6 months | Low request volume by market/date and useful as background context. |
| KRX Data Marketplace net-buy ranking `[12010]` | 3 months | 6 months | Useful discovery/reference data, but should remain descriptive. |
| Old Naver report backfill | Not a priority | Keep newly collected reports indefinitely for now | Historical reports before this project's collection start are lower value than price/flow context. |

Recommended investor-flow backfill shape:

1. Validate one live day first with `[12009]`, `[12008]`, and `[12010]`.
2. Backfill `[12009]` only for leadership-candidate or same-day report-mentioned stock/date pairs, not all listed stocks.
3. For follow-up analysis, add candidate date `D` and next business day `D+1` only after the same-day path is stable.
4. Start with the latest 10 business days or currently stored report dates, then expand to 3 months.
5. Do not expand to 6 months until response shape, units, retry behavior, duplicate handling, and candidate-selection rules are proven.

Current operating estimate as of `2026-05-09`:

| Existing data | Count |
| --- | ---: |
| Stored reports | 777 |
| Stored report business dates | 9 |
| Distinct report stock codes | 249 |
| Distinct report stock-date keys | 344 |
| Stored KRX Open API daily snapshot dates | 47 |

Implication: even report-related stock-date keys are only the upper bound.
`[12009]` stock-level flow should be narrower: collect only leadership candidates selected from report signal, price/turnover signal, sector/theme concentration, and `[12010]` net-buy ranking overlap.
It is not feasible or necessary to crawl all stocks or every report stock for every historical date.

## Leadership Candidate Policy

`[12009]` should answer "is this leading/interesting name receiving investor flow?" rather than "collect flow for every report row."

Candidate sources:

| Signal | Source | Candidate rule |
| --- | --- | --- |
| Report concentration | Naver reports / daily summaries | Multi-report names, target-bearing reports, or names in the day's concentrated sector/theme. |
| Price/turnover attention | KRX Open API daily snapshots | Names with high turnover, high volume, or strong same-day movement among currently observed stocks. |
| Investor ranking overlap | `[12010]` net-buy top | Names appearing in foreign/institution/individual net-buy top lists. |
| Market context | `[12008]` market investor flow | Use only as a background label, not as a stock selector by itself. |
| Manual watch | Operator search/memo | Optional one-off candidate, useful during validation. |

Initial candidate rule:

1. Build a daily candidate set from filtered daily summaries, not raw reports.
2. Add candidates that overlap with `[12010]` top net-buy lists after `[12010]` is validated.
3. Add high-turnover/high-volume names from KRX snapshots only when they appear in a report sector/theme or operator watch context.
4. Cap `[12009]` stock-level flow calls per day until the source is stable.
5. Store why each candidate was selected, for example `report_multi`, `target_present`, `sector_concentration`, `top_net_buy_overlap`, `operator_watch`.

Current implemented preview:

| Signal | Implemented in `krx-flow-candidates` |
| --- | --- |
| Filtered daily summary | Yes; uses effective minimum mention count and target-price-required settings. |
| Buy opinion | Yes. |
| Sector concentration | Yes; top sector rollups from stored Naver sector metadata. |
| KRX turnover rank | Yes; top 30 same-date KRX turnover snapshot. |
| KRX same-date movement | Yes; absolute change percent of at least 3%. |
| `[12010]` net-buy overlap | Not yet; add after `[12010]` live response is validated and stored. |
| Manual watch | Not yet; add after operator watchlist storage exists. |

Do not use these as candidates by default:

- every one-report stock
- every no-target-price stock
- every stock in a reported sector/theme
- every top-turnover stock in the full market
- every stock from `[12010]` without a report, sector/theme, or operator-watch reason

## Collection Priority And Guardrails

| Priority | Scope | Source | Collection rule | Why |
| --- | --- | --- | --- | --- |
| P0 | One stock/date smoke test | `[12009]` | Use `--request-only`, then live dry-run with one known stock such as `005930` | Confirms `stock_code -> isuCd -> params -> response rows`. |
| P0 | Leadership candidates for the current day | `[12009]` | After close, collect only stocks that passed the leadership candidate rule | Gives the highest signal with bounded requests. |
| P1 | Same leadership candidates on `D+1` | `[12009]` | Add only after same-day collection is stable | Supports the planned follow-up/interest observation without crawling broadly. |
| P1 | Market background by KOSPI/KOSDAQ | `[12008]` | One row set per market/date after close | Helps interpret whether flow was broad-market or stock-specific. |
| P1 | Top net-buy names by investor category | `[12010]` | Foreign/institution/individual, KOSPI/KOSDAQ, after close | Helps discover whether report names overlap with strong net-buy names. |
| P2 | 3-month scoped backfill | `[12009]`, `[12008]`, `[12010]` | Small batches only after backup/verify and live-day validation | Useful for web-view trend context; not required for Telegram MVP. |
| Blocked | Whole-market stock-level flow | `[12009]` | Do not run | Too many requests, fragile source, low immediate value. |

Operational cautions:

- Always run `db-verify` and `db-backup` before real investor-flow backfill.
- Use request previews before live calls:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
```

- Keep screen-backed calls in small batches. Start with 5 business dates or fewer, and sleep between calls.
- Treat `LOGOUT`, validation popups, missing stock selectors, or changed units as a hard stop for DB writes.
- Preserve raw units and normalized numeric values separately.
- Do not infer "주도 섹터" from investor flow alone. Show it as `수급 참고` until enough history and transparent rules exist.

## Login Session Operating Policy

Assumption from operator validation: KRX Data Marketplace login sessions are short-lived, roughly 30 minutes.

For scheduled investor-flow collection, do not rely on an old browser/login session.
The preferred source-validation model is local `.env` raw login: the process warms up KRX, posts the Data Marketplace login form with local credentials, then calls the representative JSON endpoint using an in-memory cookie jar.
This avoids browser-session fragility and does not persist cookies, headers, or credentials outside local `.env`.

Browser control policy:

- Prefer raw `.env` login for repeatable Data Marketplace JSON validation.
- Use the connected Chrome extension browser only for UI fallback/debug validation because it can use the operator's real Chrome login/session state.
- Use the Codex in-app browser only for simple read-only inspection, local UI checks, or fallback when Chrome extension control is unavailable.
- Do not mix browser surfaces during one validation run unless the operator explicitly asks for a fallback; otherwise session assumptions become ambiguous.

| Step | Timing | Action |
| --- | --- | --- |
| 1 | Before planned flow dry-run/collection | Run `krx-flow-login-check --date YYYY-MM-DD` to verify raw `.env` login and a representative `[12008]` JSON endpoint. |
| 2 | If login-check passes | Continue only with validation/dry-run work; do not treat this as scheduled ingest approval. |
| 3 | If login-check fails with `auth_rejected` or `LOGOUT` | Fall back to manual Chrome validation or notify the operator. Do not write investor-flow rows. |
| 4 | If browser fallback is used | Operator logs in on the single Chrome-extension-controlled KRX tab, then `/체크 로그인` records acknowledgement only. The next dry-run still decides the real connection verdict. |

Implementation boundary:

- Do not auto-store or expose Data Marketplace credentials through `admin-gui`, `web-view`, Telegram, or docs.
- Automatic raw login may use only the local `.env` keys and must not save cookies, headers, password dumps, or browser profile state.
- `StockMonitor-KrxFlowLoginReminder` is a reminder-only scheduler task, separate from actual flow collection. It sends Telegram only and should not use `--open-browser`.
- Actual source-backed flow ingestion must remain disabled until separate explicit approval.
- `/체크 로그인` must not be treated as proof that the Data Marketplace HTTP endpoint is authenticated. It means the operator completed the remote Chrome login step; the following dry-run decides whether the connection is really usable.
- To avoid duplicate tabs during manual validation, Codex should open one Chrome-extension-controlled KRX tab first, and the operator should log in on that same tab. Do not open another normal Chrome tab with `Start-Process` unless Chrome extension control is unavailable.

Raw login check:

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

Reminder command for browser fallback:

```powershell
python -m stock_monitor krx-flow-login-reminder --minutes-before 5 --planned-time 16:50
```

Dry-run:

```powershell
python -m stock_monitor krx-flow-login-reminder --minutes-before 5 --planned-time 16:50 --dry-run
```

Request preview without login/network:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
```

Use `--request-only` before live Data Marketplace calls to confirm that stored KRX metadata resolves the 6-digit stock code to the expected `isuCd` and request params.

Leadership candidate preview without login/network:

```powershell
python -m stock_monitor krx-flow-candidates --date 2026-05-08 --limit 10
```

Use `krx-flow-candidates` before `[12009]` calls. It reads local daily summaries, sector metadata, and KRX price/turnover snapshots, then prints the narrowed stock list and per-stock `--request-only` command.

## Observed `[12009]` Screen Conditions

Observed after logging in through the Chrome extension-connected KRX Data Marketplace tab.

| Condition | Observed value / behavior | Implementation note |
| --- | --- | --- |
| Screen no. | `[12009]` | `투자자별 거래실적(개별종목)` |
| Navigation | `기본 통계 > 주식 > 거래실적` | Keep this in source docs for future manual verification. |
| Query type | `기간합계`, `일별추이` radio options | Preserve the chosen query type in request params and saved metadata. |
| Stock selector | `주식 종목 검색`; typing a stock name and pressing `Enter` resolves to selected display example `005930/삼성전자` | Browser validation can use direct name input; fetch should use a stable code/ISIN param after request contract tracing, not display text alone. |
| Date range | `strtDd`, `endDd` inputs | Use KST business dates; for daily flow prefer one date at a time first. |
| Share unit | `주`, `천주`, `백만주` style selector | Store unit explicitly; prefer raw `주` if available. |
| Money unit | `원`, `천원`, `백만원`, `십억원` style selector | Store unit explicitly; prefer raw `원` if available. |
| Rows | investor-type rows | Preserve detailed investor rows and derive foreign/institution/individual summary separately. |

Additional live screen validation on `2026-05-09`:

| Screen | Validation | Result |
| --- | --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Chrome extension-connected KRX Data Marketplace tab, stock `329180/HD현대중공업`, date range `20260430~20260508`, query clicked after stock selector resolution | Visible table rendered investor rows with `거래량` and `거래대금` split into `매도`, `매수`, `순매수`. |
| `[12009]` stock selector | Numeric stock-code search worked when Korean text input through the extension was unreliable | Keep automated validation code tolerant of stock selector popup text such as `개별종목을 검색해주세요`; close it before retrying selection. |
| Raw HTTP response | Not captured in this validation pass | Parser aliases and DB migration remain a controlled draft until direct endpoint response samples are verified. |
| Saved raw sample path | `krx-flow-dry-run --sample-file <json>` | Normalizes a saved Data Marketplace JSON payload without login, network call, or DB write. Use this for DevTools/browser-captured samples before scheduled ingest. |
| Saved sample manifest | `krx-flow-dry-run --sample-manifest <json>` | Stores sample file, screen, date, stock/market/investor filters, and units together so validation can be repeated without relying on memory. |
| Manifest scaffold | `--manifest-output <json>` | Writes a local manifest scaffold from CLI conditions; no login, network call, or DB write. |
| Capture-set scaffold | `krx-flow-sample-scaffold --date YYYY-MM-DD --stock-code STOCKCODE` | Writes `[12009]`, `[12008]`, and `[12010]` manifest scaffolds together for a capture date. Use `--from-candidates` to populate `[12009]` stocks from local preview signals. |
| Capture checklist | `krx-flow-capture-checklist --manifest-dir data\krx_samples` | Prints screen, condition, raw filename, manifest path, and validation command for each manifest. |
| Normalized artifact | `--normalized-output <json>` | Writes normalized validation output to a local JSON artifact; still no DB write. |
| Strict sample validation | `--strict-sample` | Returns exit code `2` when raw rows or normalized rows are suspicious. Use before treating a sample as an ingest reference. |
| Sample coverage status | `krx-flow-sample-status --manifest-dir data\krx_samples` | Reports whether `[12008]`, `[12009]`, and `[12010]` manifests and raw files are present, including next capture filenames. No login, network call, or DB write. |
| Batch sample validation | `krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized` | Validates all local manifests with strict sample rules and can write normalized artifacts; still no login, network call, or DB write. |
| Import preview | `krx-flow-import-preview --manifest-dir data\krx_samples` | Computes target investor-flow table row counts from local manifests; still no DB write. |
| Guarded manual import | `krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated` | Upserts warning-free local samples into investor-flow tables. Scheduled ingest remains disabled. |
| Expected sample coverage | `expected_min_rows`, `expected_min_normalized_rows`, `expected_investors` | Manifest expectations for minimum coverage and required investor rows. |
| Unit override | `--volume-unit`, `--amount-unit` | Preserve the visible KRX screen unit in normalized rows; do not infer or scale values silently. |

## Request Contract Candidates

These are implementation candidates derived from KRX Data Marketplace screen observation and the public `pykrx` wrapper source.
They are not yet project-ingest contracts.
Before adding migrations or scheduled collection, verify them with a local dry-run command that prints request conditions, raw row counts, normalized rows, and units without DB writes.

| Screen | Query | Candidate BLD | Candidate params | Notes |
| --- | --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02201` | `strtDd`, `endDd`, `mktId`, `etf`, `etn`, `elw` | Market-wide investor background. |
| `[12009] 투자자별 거래실적(개별종목)` | 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02301` | `strtDd`, `endDd`, `isuCd` | First target for report-stock investor flow. |
| `[12009] 투자자별 거래실적(개별종목)` | 일별추이 | `dbms/MDC/STAT/standard/MDCSTAT02302` | `strtDd`, `endDd`, `isuCd`, `trdVolVal`, `askBid` | Useful after period aggregate is stable. |
| `[12010] 투자자별 순매수상위종목` | 순매수상위 | `dbms/MDC/STAT/standard/MDCSTAT02401` | `strtDd`, `endDd`, `mktId`, `invstTpCd` | Ranking/reference source by investor category. |

Observed control fields from Chrome-extension validation:

| Screen | Observed controls | Immediate status |
| --- | --- | --- |
| `[12008]` | `inqTpCd`, `mktId`, disabled `segTpCd`, optional `etf`/`etn`/`elw`, `strtDd`, `endDd`, `share`, `money`, `search` | Default search button is reachable. |
| `[12009]` | `inqTpCd`, stock search input `tboxisuCd_finder_stkisu0_0`, `strtDd`, `endDd`, `share`, `money`, `search` | Direct stock-name input plus `Enter` resolves to `005930/삼성전자`; missing stock still shows validation dialog. |
| `[12010]` | `mktId`, disabled `segTpCd`, `invstTpCd`, `strtDd`, `endDd`, `share`, `money`, `search` | Default search button is reachable. |

Candidate parameter meanings:

| Param | Meaning | Candidate values |
| --- | --- | --- |
| `mktId` | Market filter | `STK`, `KSQ`, `ALL` |
| `trdVolVal` | Trend value type | `1` 거래량, `2` 거래대금 |
| `askBid` | Sell/buy/net-buy selector | `1` 매도, `2` 매수, `3` 순매수 |
| `invstTpCd` | Investor category for `[12010]` | `1000` 금융투자, `2000` 보험, `3000` 투신, `3100` 사모, `4000` 은행, `5000` 기타금융, `6000` 연기금, `7050` 기관합계, `7100` 기타법인, `8000` 개인, `9000` 외국인, `9001` 기타외국인, `9999` 전체 |

Important implementation risk:

- `[12009]` candidate params use `isuCd`, which appears to be an ISIN-style issue code rather than the 6-digit stock code.
- Do not call `[12009]` directly from `stock_code` until a 6-digit code to `isuCd` mapping is confirmed from approved KRX metadata or a Data Marketplace lookup response.
- If the dry-run cannot reproduce the screen output without session-specific or hidden browser state, keep this as a manual validation source and do not add scheduled ingestion.
- For UI login fallback, prefer the direct `{KRX_LOGIN_FALLBACK_PATH}` page over the wrapper iframe page. Browser UI login is for validation/debug only; the `.env` raw fetch path is the standard sample-capture path while credentials remain local-only.
- Do not automate Chrome saved-password, PIN, Windows Hello, or other OS/native security prompts. These remain manual operator actions.

## Initial Data Model Candidates

Migration v4 now contains these tables with repository upsert/list tests.
The operating DB may have the additive tables, but scheduled ingestion must remain disabled until separate explicit approval.

```text
stock_investor_flow_daily(
  business_date,
  stock_code,
  investor_type,
  sell_volume,
  buy_volume,
  net_buy_volume,
  sell_amount,
  buy_amount,
  net_buy_amount,
  volume_unit,
  amount_unit,
  source,
  fetched_at,
  primary key (business_date, stock_code, investor_type, source)
)

market_investor_flow_daily(
  business_date,
  market,
  investor_type,
  sell_volume,
  buy_volume,
  net_buy_volume,
  sell_amount,
  buy_amount,
  net_buy_amount,
  volume_unit,
  amount_unit,
  source,
  fetched_at,
  primary key (business_date, market, investor_type, source)
)

investor_net_buy_top_daily(
  business_date,
  market,
  investor_type,
  rank,
  stock_code,
  stock_name,
  net_buy_volume,
  net_buy_amount,
  source,
  fetched_at,
  primary key (business_date, market, investor_type, rank, source)
)
```

## Implementation Order

| Order | Work | Output |
| ---: | --- | --- |
| 1 | Trace `[12009]` request contract | Done as candidate: `MDCSTAT02301` period aggregate and `MDCSTAT02302` trend. |
| 2 | Add dry-run fetch for one stock/date | `krx-flow-dry-run` added; no DB writes; `--request-only` validates `stock_code -> isuCd -> params` without login/network. |
| 3 | Add migration for investor-flow tables | Done as additive schema v4 with repository upsert/list tests and `db-verify` quality checks; operating tables are empty until ingest is explicitly added. |
| 4 | Fetch report-stock flow only | Start with stocks that appeared in Naver reports; avoid broad all-stock crawling. |
| 5 | Trace `[12008]` and `[12010]` | Stage 4 live/raw parity is complete for two business dates; scheduled ingest still requires separate Stage 6 design. |
| 6 | Add read-only web-view cards | Done for manually imported rows: daily context exposes market flow and net-buy top references, and stock detail exposes stock-level investor rows. Labels remain descriptive only. |
| 7 | Review several weeks | Decide later whether rotation/interest alerts are defensible. |

## Guardrails

- Keep these tables separate from `reports`, `daily_stock_summaries`, and KRX Open API snapshot tables.
- Store `source='krx_data_market'` for Data Marketplace-derived rows.
- Do not call this public numeric scoring, trading recommendation, or confirmed rotation. It may support observation-candidate ordering only with other stored evidence.
- Display as `수급 참고`, `외국인 순매수`, `기관 순매수`, or `후속 확인 필요`.
- `web-view` may show manually imported investor-flow rows as read-only reference data, but must not expose Data Marketplace credentials, raw request internals, scheduler state, DB paths, or control endpoints.
- Do not crawl the whole market first; start with leadership candidates plus market/top-ranking screens.
- Run collection after the data delay window, not immediately at the regular market close.
- Preserve source units because KRX screens can switch between shares/thousand shares and KRW/thousand/million/billion KRW.
- If a screen condition cannot be reproduced programmatically, stop at manual validation and do not silently approximate it.
- Use [market-data-runbook.md](/docs/codex/market-data-runbook.md) and `data/krx_samples/templates/*.json` before promoting any raw sample to an ingest reference.
- Use [market-data-runbook.md](/docs/codex/market-data-runbook.md) as the table contract and `db-verify` quality gate reference before enabling any scheduled ingest.

Dry-run commands:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view market --date 2026-05-08 --market STK --value amount --side net-buy --show-first-row
python -m stock_monitor krx-flow-dry-run --view top --date 2026-05-08 --market STK --investor foreign --show-first-row
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
python -m stock_monitor krx-flow-candidates --date 2026-05-08 --limit 10
```

If `krx_stock_metadata` has no `standard_code` for the stock, either fetch basic metadata first or pass `--isu-cd` explicitly:

```powershell
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date 2026-05-08
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --sample-file data\krx_samples\12009_005930_20260508.local.json --volume-unit 주 --amount-unit 원 --show-first-row
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --stock-code 005930 --market STK --top-investor foreign
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --from-candidates --candidate-limit 5 --market STK --top-investor foreign
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --manifest-output data\krx_samples\12009_005930_20260508.manifest.local.json
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --normalized-output data\krx_samples\12009_005930_20260508.normalized.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --normalized-output data\krx_samples\12009_005930_20260508.normalized.local.json --strict-sample --show-first-row
python -m stock_monitor krx-flow-capture-checklist --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized
python -m stock_monitor krx-flow-import-preview --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

KRX Data Marketplace can return `LOGOUT` without a logged-in session.
For dry-run validation only, credentials may be provided through local `.env` keys:

```env
STOCK_MONITOR_KRX_DATA_MARKET_ID=
STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD=
```

Keep these separate from `STOCK_MONITOR_KRX_AUTH_KEY`.
Do not print them, store them in docs, or expose them through `admin-gui` or `web-view`.
