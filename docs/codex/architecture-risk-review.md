# Architecture Risk Review

## Purpose

This document records the current architecture and risk-review snapshot for `02.Stock_Moniter`.

Use it when starting broad investigation across:

- fetch -> parse -> persist -> summarize -> notify
- scheduler / CLI wrappers
- `admin-gui` and read-only `web-view`
- replay, migration, data-source, public-safe, and performance boundaries

This is an investigation reference, not an implementation plan. Before changing parser, summary, notification, admin-gui, or web-view behavior, still check [data-quality-checklist.md](/docs/codex/data-quality-checklist.md), [surface-contract.md](/docs/codex/surface-contract.md), and [data-source-policy.md](/docs/codex/data-source-policy.md).

## Snapshot

Date: `2026-05-20`

Scope:

- Local project only: `{PROJECT_ROOT}`
- Investigation only; no code edits were made during the review.
- CodeGraph was checked first for structure, but the index did not include the highest-risk `src/stock_monitor/cli.py` file at the time of review, so results were corrected against real file contents.

Working-tree note:

- The workspace was already dirty during this review, including changes to docs, scheduler scripts, `src/stock_monitor/cli.py`, `src/stock_monitor/db/repository.py`, `src/stock_monitor/db/schema.py`, `src/stock_monitor/fetch/naver_stock_quote.py`, new `src/stock_monitor/web_perf.py`, and related tests.
- Treat this document as a snapshot of the current local state, not a clean release baseline.

## Architecture Summary

| Area | Current shape |
| --- | --- |
| CLI entry | `python -m stock_monitor` enters [__main__.py](/src/stock_monitor/__main__.py) and dispatches through [cli.py](/src/stock_monitor/cli.py). |
| Fetch / parse | Naver report collection lives in [fetch/naver_research.py](/src/stock_monitor/fetch/naver_research.py). It prefers captured API items and falls back to candidate DOM rows. |
| Persist | SQLite access is centralized in [db/repository.py](/src/stock_monitor/db/repository.py). Schema and migrations are in [db/schema.py](/src/stock_monitor/db/schema.py). |
| Summarize | Daily report summaries are built in [summary.py](/src/stock_monitor/summary.py). |
| Notify | Telegram formatting and control state are under [notify/](/src/stock_monitor/notify). Scheduled/manual delivery orchestration is in [cli.py](/src/stock_monitor/cli.py). |
| Scheduler | PowerShell wrappers in [scripts/](/scripts) call CLI scheduled commands. Python-side guards enforce business-day, no-run, time-window, and operation-profile rules. |
| Admin surface | `admin-gui` is a local/operator control surface with GET and guarded POST routes inside [cli.py](/src/stock_monitor/cli.py). |
| User surface | `web-view` is a separate GET-only/read-only surface, with `/auth/login` as the only POST exception and all other write methods returning `405`. |
| Market data | KRX Open API and KRX Data Marketplace fetch/parse helpers live in [fetch/krx_api.py](/src/stock_monitor/fetch/krx_api.py). KRX scheduling and display orchestration is mostly in [cli.py](/src/stock_monitor/cli.py). |

## Key Paths

| Concern | Path |
| --- | --- |
| Report fetch entry | [fetch/naver_research.py](/src/stock_monitor/fetch/naver_research.py) |
| Report identity | [models.py](/src/stock_monitor/models.py) |
| Report insert / intraday queue | [db/repository.py](/src/stock_monitor/db/repository.py) |
| Daily summary build | [summary.py](/src/stock_monitor/summary.py) |
| Daily delivery fragments | [db/schema.py](/src/stock_monitor/db/schema.py), [db/repository.py](/src/stock_monitor/db/repository.py) |
| Scheduled poll / notify | [scripts/run_scheduled_poll.ps1](/scripts/run_scheduled_poll.ps1), [scripts/run_scheduled_notify.ps1](/scripts/run_scheduled_notify.ps1), [cli.py](/src/stock_monitor/cli.py) |
| KRX daily backfill | [scripts/run_scheduled_krx_daily_backfill.ps1](/scripts/run_scheduled_krx_daily_backfill.ps1), [fetch/krx_api.py](/src/stock_monitor/fetch/krx_api.py), [cli.py](/src/stock_monitor/cli.py) |
| KRX mentioned-stock flow | [scripts/run_scheduled_krx_mentioned_flow_backfill.ps1](/scripts/run_scheduled_krx_mentioned_flow_backfill.ps1), [cli.py](/src/stock_monitor/cli.py) |
| Admin GUI handler | [cli.py](/src/stock_monitor/cli.py) |
| Web-view handler / DTOs | [cli.py](/src/stock_monitor/cli.py) |
| Public-safe smoke / QA | [tests/test_web_view.py](/tests/test_web_view.py), [tests/test_cli_commands.py](/tests/test_cli_commands.py) |

## Confirmed Findings

1. Report dedupe has multiple layers.

   `reports.identity_key` is unique, `source_id` is unique when present, and a legacy visible-field unique index exists for `(stock_name, title, broker_name, published_at)`.

2. Missing report values are handled correctly in the core summary path.

   Target price range uses only non-`None` numeric target values. Dominant opinion excludes `N/A` from the valid vote and uses `N/A` only when no valid opinion exists.

3. Daily Telegram delivery replay has durable state.

   `daily_summary_delivery_runs` and `daily_summary_delivery_fragments` store summary signature, pending/failed/sent fragments, message hashes, message IDs, and error state so failed fragments can resume without resending already successful fragments.

4. `admin-gui` and `web-view` are separate HTTP handlers.

   `admin-gui` exposes `/api/status` and guarded POST operations. `web-view` has separate read-only JSON routes, does not expose `/api/status`, and returns `405` for write methods except the access-code login path.

5. Host binding defaults are guarded.

   Both `admin-gui` and `web-view` refuse non-loopback binding by default and require an explicit `--allow-non-loopback`.

6. The approved automatic KRX Data Marketplace path is narrow in code and docs.

   `scheduled-krx-mentioned-flow-backfill` plans calls only for report-mentioned stocks on the anchor date, uses `[12009]`, skips existing rows, honors time guards for automatic runs, and records operation events.

7. Web-view performance work is already present.

   Public JSON routes use a short in-process cache, optional gzip, and API performance logging. Recent docs record earlier batching work for daily, archive, market-briefing, and candidate-evidence payloads.

## Plausible Risks

| Risk | Why it matters | Suggested owner |
| --- | --- | --- |
| `cli.py` concentration | The file owns CLI dispatch, scheduler guards, admin server, web-view server, DTO builders, KRX orchestration, smoke checks, and rendered HTML/JS. That makes ownership and impact analysis harder. | `cli-developer`, `web-ui-engineer`, `security-hardening` |
| CodeGraph coverage gap | The review found CodeGraph did not include `src/stock_monitor/cli.py`, which is the most important cross-boundary file. Impact checks may be incomplete until indexing is corrected. | `debugger`, `documentation-engineer` |
| Summary uniqueness under stock-name drift | Summary rebuild groups code-first, but `daily_stock_summaries` uniqueness includes `stock_name`. A stock name or representative-name change could leave migration/rebuild edge cases worth testing. | `sql-pro`, `python-pro` |
| Naver live reference exception | `web-view` allows the manual same-day `intraday_market_top` / Naver `priceTop` reference. This current exception is display/reference-only because it is not an approved stable real-time lane. Future approved intraday sources are different: they may affect observation priority after source-burden, freshness, and failure behavior review. | `market-data-engineer`, `security-hardening`, `web-ui-engineer` |
| Public limit mistaken as final product goal | Current public surfaces block trading-decision wording, but the longer-term direction may include operator-only decision support or execution-lab once real-time source and safety gates are proven. Treating the current wording guard as permanent would undercut the intended path. | `reviewer`, `security-hardening`, `market-data-engineer` |
| Free-text operation event details | `operation_events.detail` is useful for operators but should remain admin-only or be converted into public labels before any web-view exposure. | `security-hardening`, `reviewer` |
| Dirty working tree baseline | Many files were already modified during the review. Any later conclusion should distinguish current local changes from a clean committed baseline. | `reviewer`, `documentation-engineer` |

## Boundary And Security Candidates

1. Recheck public DTO key filtering for every current `web-view` route:

   - `/api/archive`
   - `/api/daily/{date}`
   - `/api/daily/{date}/stocks/{stock_code}`
   - `/api/candidate-evidence`
   - `/api/observation/backtest`
   - `/api/intraday`
   - `/api/flow-trend`
   - `/api/etf-trend`
   - `/api/rotation-overlay`
   - `/api/category`
   - `/api/category-trend`
   - `/api/market`

2. Keep `/api/status`, scheduler/operator/settings routes, admin audit logs, safe settings, `.env`, DB paths, Telegram tokens, and scheduler internals out of `web-view`.

3. Keep `/assets/cycle.jpg` behind the same access-code gate as the `web-view` page when the gate is enabled.

4. Continue treating Cloudflare/Tailscale checks as read-only verification. Do not let provider-smoke success mutate anything except the approved non-secret operation-event success row.

5. Keep blocked public copy out of Telegram and web-view:

   - `매수 추천`
   - `매도 추천`
   - `점수`
   - `등급`
   - `진입가`
   - `청산가`
   - `익절가`
   - `목표 수익률`
   - `확신도`
   - buy/sell signal wording

## Source Boundary Candidates

| Boundary | Current rule | Candidate check |
| --- | --- | --- |
| Naver reports | Naver owns report facts and report identity. | Ensure KRX values never overwrite report title, broker, target, opinion, or report date facts. |
| KRX Open API | KRX owns stock/ETF/index daily reference values. | Ensure same-day `not_published` remains normal and does not trigger same-day probe automation or silent latest-date fallback. |
| KRX Data Marketplace | Stored investor-flow samples and narrow `[12009]` mentioned-stock automation only. | Ensure `[12008]`, `[12010]`, market-wide, and all-stock broad scheduled ingest remain blocked without separate approval. |
| Naver `priceTop` | Manual same-day display-only web-view reference. | Ensure no DB writes, Telegram sends, scheduler changes, KRX replacement, or scoring are tied to this route. |
| Future approved intraday source | Separate read-only lab/staging lane before public use. | If approved, it may affect top-2 `우선 확인` ordering and main-card emphasis, but must not create DB writes, Telegram/scheduler automation, broker execution, public score, or trading-call wording. |
| Future operator decision/execution lane | Separate from public `web-view` and Telegram. | It may evaluate trading-decision support only after stable real-time data, permission, audit, failure handling, and order-safety gates are defined. |
| Category taxonomy | 업종/테마 is a separate taxonomy layer, not official KRX taxonomy. | Ensure historical dates do not silently receive future/current category snapshots. |

## Performance Candidates

1. Web-view daily DTO builders remain the main area to watch because one request can combine report summaries, category rollups, market briefing, KRX reference, investor flow, rotation evidence, and optional Naver intraday reference.

2. Repository methods open a SQLite connection per call. WAL mode, cache size, busy timeout, and recent batching reduce risk, but DTO paths should keep query-budget tests.

3. `src/stock_monitor/web_perf.py` and API perf logs should be included in CodeGraph once the index is refreshed.

4. `candidate-evidence`, archive, and daily payload generation already have documented performance improvements. Future regressions should be checked with the existing web performance tests and browser smoke commands before adding more caching.

## Recommended Next Investigations

| Investigation | Goal | Owner |
| --- | --- | --- |
| Refresh or repair CodeGraph indexing | Ensure `cli.py` and `web_perf.py` are indexed before future impact analysis. | `debugger` or `documentation-engineer` |
| `cli.py` responsibility map | Split the file logically by command group, route handler, DTO builder, and operational guard without editing yet. | `cli-developer` |
| Web-view public DTO audit | Confirm all public routes exclude admin/operator/secrets and blocked public wording, while preserving clear observation recommendation language where evidence supports `우선 확인`. | `security-hardening` + `web-ui-engineer` |
| Operator decision-support boundary | Define where future trading-decision review could live without leaking into public `web-view` or automatic execution. | `market-data-engineer` + `security-hardening` + `reviewer` |
| Summary identity/rebuild audit | Test stock-code-first grouping, representative name drift, code-missing rows, and `daily_stock_summaries` uniqueness. | `sql-pro` + `python-pro` |
| Scheduler wrapper audit | Check scripts against Python-side guards and main-PC vs mini-PC operation profile expectations. | `cli-developer` + `debugger` |
| KRX source boundary audit | Confirm same-day KRX Open API behavior, mentioned-stock `[12009]` limits, and manual Naver `priceTop` display-only behavior. | `market-data-engineer` |
| Replay safety review | Recheck Telegram daily fragments, intraday alert batches, command replay side effects, and migration restore behavior. | `backend-developer` + `test-engineer` |
| Query budget review | Measure daily, archive, candidate-evidence, and stock-detail DTO paths after current dirty changes settle. | `web-ui-engineer` + `test-engineer` |

## Agent Ownership Matrix

| Area | Primary owner | Supporting agents |
| --- | --- | --- |
| Fetch -> parse -> persist -> notify | `backend-developer` | `python-pro`, `test-engineer` |
| Summary aggregation and missing values | `python-pro` | `sql-pro`, `reviewer` |
| Schema, replay, migration, dedupe | `sql-pro` | `backend-developer`, `test-engineer` |
| Scheduler wrappers and CLI guards | `cli-developer` | `debugger`, `reviewer` |
| Runtime scheduled-run failures | `debugger` | `cli-developer`, `reviewer` |
| Admin GUI boundary | `admin-ui-engineer` | `security-hardening`, `reviewer` |
| Web-view read-only public surface | `web-ui-engineer` | `security-hardening`, `test-engineer` |
| Public-safe exposure and access gate | `security-hardening` | `web-ui-engineer`, `reviewer` |
| KRX/OpenAPI/Data Marketplace/source policy | `market-data-engineer` | `sql-pro`, `debugger` |
| Performance/query budget | `test-engineer` | `web-ui-engineer`, `python-pro` |
| Documentation consistency | `documentation-engineer` | `reviewer` |
