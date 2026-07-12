# Architecture Guide

System map, ownership, agent use, and decision history.

## Included sections
- Project Map
- Architecture Risk Review
- Module Ownership
- Agent Guide
- Agent Reassessment
- Decision Log

<!-- Merged from: docs/codex/architecture-guide.md -->
## Project Map

## Scope

This map describes only:

- `{PROJECT_ROOT}`

No assumptions should be made from any path outside this folder.

## Project Purpose

Monitor the Naver Stock research company page for the domestic stocks tab,
store newly observed research reports during Korean business hours,
send Telegram summaries/alerts, and provide separate local operator and read-only user surfaces
with KRX market reference, investor-flow reference, and observation evidence.

## Current Structure

Project root:

- `{PROJECT_ROOT}`

Current files:

- [AGENTS.md](/AGENTS.md)
- [README.md](/README.md)
- [CHANGELOG.md](/CHANGELOG.md)
- [pyproject.toml](/pyproject.toml)
- [stock_research_monitor_mvp.md](/stock_research_monitor_mvp.md)
- [docs/codex/architecture-guide.md](/docs/codex/architecture-guide.md)
- [docs/codex/operating-guide.md](/docs/codex/operating-guide.md)
- [docs/codex/documentation-index.md](/docs/codex/documentation-index.md)
- [docs/codex/surface-guide.md](/docs/codex/surface-guide.md)
- [docs/codex/data-governance.md](/docs/codex/data-governance.md)
- [docs/codex/candidate-evidence.md](/docs/codex/candidate-evidence.md)
- [docs/codex/research-notes.md](/docs/codex/research-notes.md)
- [docs/codex/market-data-runbook.md](/docs/codex/market-data-runbook.md)
- [docs/codex/mini-pc-runbook.md](/docs/codex/mini-pc-runbook.md)
- [docs/codex/history.md](/docs/codex/history.md)
- Use [docs/codex/documentation-index.md](/docs/codex/documentation-index.md) to find canonical documents and cleanup rules.

Current directories:

- `.codex/` (local Codex metadata; project-local `.codex/agents/` is intentionally absent)
- `src/`
- `src/stock_monitor/`
- `tests/`
- `scripts/`
- `data/`
- `docs/`
- `docs/codex/`

## Core Paths

- Project root: `{PROJECT_ROOT}`
- Requirements anchor: `{PROJECT_ROOT}\stock_research_monitor_mvp.md`
- Codex handoff docs: `{PROJECT_ROOT}\docs\codex`

## Current Reality

What exists now:

- runnable Python MVP implementation
- Telegram notifier and command-processing flow
- SQLite storage and repository layer
- Task Scheduler wrapper scripts
- regression tests for parser, scheduler, Telegram, and summary behavior
- regression tests for delivery fragments, operator health, scheduler classification, admin boundary, and DB hardening
- separate GET-only user `web-view`
- KRX Open API daily snapshot ingest/backfill for stock, ETF, and index reference data
- KRX Data Marketplace investor-flow source plan for `[12008]`, `[12009]`, and `[12010]`
- KRX Data Marketplace investor-flow sample capture runbook and local manifest templates
- KRX Data Marketplace investor-flow additive schema v4 and `db-verify` quality gate
- KRX Data Marketplace investor-flow manual backfill/read-only display path
- read-only observation/backtest DTO/API and `web-view` observation tab
- internal-only scoring-draft CLI paths with no public numeric score or trading-recommendation output
- requirements/spec document
- Codex handoff documents
- mini PC migration handoff, restore/change log, and external web-view sharing runbooks
- mini PC local operation/readiness scripts, scheduler registration checks, Cloudflare post-provider verification wrapper, hourly web-view restart helper, and current-user web-view Startup shortcut helper

What does not exist yet:

- automatic holiday-source refresh for years beyond 2026
- long-run validation across more live weekday runs
- Tailscale owner-only access setup, if it is still needed after the verified Cloudflare `web-view` path
- multi-day validation that the current-user `web-view` Startup shortcut keeps the Cloudflare loopback target available after Windows logon/reboot
- US market source study or implementation
- broad/all-stock KRX Data Marketplace scheduled investor-flow ingest enablement
- KIS investor-flow ingest implementation
- public trading recommendation, numeric score, investment grade, or buy/sell signal
- a separately reviewed operator-only decision-support or execution-lab lane for trading decisions after stable real-time data and safety gates

## Recommended Near-Term Layout

Current implementation layout:

- `src/stock_monitor/`
- `src/stock_monitor/fetch/`
- `src/stock_monitor/db/`
- `src/stock_monitor/notify/`
- `scripts/`
- `data/`
- `tests/`

Local-only intake files:

- [data/krx_api_intake.local.md](/data/krx_api_intake.local.md)

Important currently observed modules:

- `src/stock_monitor/cli.py`
- `src/stock_monitor/business_day.py`
- `src/stock_monitor/summary.py`
- `src/stock_monitor/fetch/naver_research.py`
- `src/stock_monitor/fetch/naver_stock_research.py`
- `src/stock_monitor/fetch/naver_stock_search.py`
- `src/stock_monitor/fetch/naver_stock_quote.py`
- `src/stock_monitor/db/repository.py`
- `src/stock_monitor/db/schema.py`
- `src/stock_monitor/notify/formatter.py`
- `src/stock_monitor/notify/control.py`
- `src/stock_monitor/notify/telegram.py`
- `.env.example`
- `scripts/register_task_scheduler_tasks.ps1`
- `scripts/register_mini_pc_scheduler_tasks.ps1`
- `scripts/create_migration_archive.ps1`
- `scripts/disable_source_desktop_scheduler_tasks.ps1`
- `scripts/setup_mini_pc_environment.ps1`
- `scripts/verify_cloudflare_web_view_tunnel.ps1`
- `scripts/verify_external_web_view_readiness.ps1`
- `scripts/verify_migration_archive.ps1`
- `scripts/verify_mini_pc_readiness.ps1`
- `scripts/verify_market_day_observation.ps1`
- `scripts/verify_next_phase_closeout.ps1`
- `scripts/verify_task_scheduler_registration.ps1`
- `scripts/run_scheduled_poll.ps1`
- `scripts/run_scheduled_notify.ps1`
- `scripts/run_scheduled_krx_daily_backfill.ps1`
- `scripts/run_scheduled_krx_mentioned_flow_backfill.ps1`
- `scripts/run_krx_flow_login_reminder.ps1`
- `scripts/run_process_telegram_commands.ps1`
- `scripts/run_scheduled_shutdown.ps1`
- `scripts/run_web_view.ps1`
- `scripts/restart_web_view.ps1`
- `scripts/create_web_view_startup_shortcut.ps1`

Important review docs:

- `docs/codex/documentation-index.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/surface-guide.md`
- `docs/codex/architecture-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`

## Key Domain Objects

Current key entities and persisted state:

- `report`
- `daily_stock_summary`
- `delivery_log`
- `daily_summary_delivery_runs`
- `daily_summary_delivery_fragments`
- `operation_events`
- `operator_controls`
- `worker_state`
- `app_settings`
- `admin_audit_log`
- `stock_metadata`
- `stock_theme_memberships`
- `stock_market_daily`
- `etf_daily_snapshots`
- `krx_stock_metadata`
- `market_index_daily`
- `market_investor_flow_daily`
- `stock_investor_flow_daily`
- `investor_net_buy_top_daily`
- `category_master`
- `category_membership_snapshots`
- `intraday_alert_batches`
- Telegram control state
- operator memos

## Recent Changed Files

Files currently known as the most recently updated within this folder:

- `stock_research_monitor_mvp.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/architecture-guide.md`
- `docs/codex/documentation-index.md`
- `README.md`
- `CHANGELOG.md`


<!-- Merged from: docs/codex/architecture-guide.md -->
## Architecture Risk Review

## Purpose

This document records the current architecture and risk-review snapshot for `02.Stock_Moniter`.

Use it when starting broad investigation across:

- fetch -> parse -> persist -> summarize -> notify
- scheduler / CLI wrappers
- `admin-gui` and read-only `web-view`
- replay, migration, data-source, public-safe, and performance boundaries

This is an investigation reference, not an implementation plan. Before changing parser, summary, notification, admin-gui, or web-view behavior, still check [data-governance.md](/docs/codex/data-governance.md), [surface-guide.md](/docs/codex/surface-guide.md), and [data-governance.md](/docs/codex/data-governance.md).

## Snapshot

Date: `2026-05-20`

Scope:

- Local project only: `{PROJECT_ROOT}`
- Investigation only; no code edits were made during the review.
- CodeGraph was checked first for structure, but the index did not include the highest-risk `src/stock_monitor/cli.py` file at the time of review, so results were corrected against real file contents.

Working-tree note:

- The workspace was already dirty during this review, including changes to docs, scheduler scripts, `src/stock_monitor/cli.py`, `src/stock_monitor/db/repository.py`, `src/stock_monitor/db/schema.py`, `src/stock_monitor/fetch/naver_stock_quote.py`, new `src/stock_monitor/web_perf.py`, and related tests.
- Treat this document as a snapshot of the current local state, not a clean release baseline.

## Reconciliation (2026-06-21)

- CodeGraph now resolves `build_web_view_daily_snapshot`, stock-detail builders, and the `cli.py` web-view path in this workspace. Treat the older coverage-gap note as historical; recheck index freshness after large `cli.py` changes.
- The central product risk is not a missing tab. It is a broken evidence handoff between `메인`, `관찰`, `종목`, `시장`, and `순환매`. Browser smoke now verifies a candidate action, retained detail context, and market/rotation navigation across desktop and mobile viewports.
- `cli.py` remains concentrated and is still the main ownership/performance risk. This pass adds no new server family or control surface; it reuses the existing public DTOs and client-side tab transitions.

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


<!-- Merged from: docs/codex/architecture-guide.md -->
## Module Ownership

## Purpose

This document proposes role boundaries for future implementation work.

The project is small enough that one developer can still edit across modules, but the work axes are now distinct enough that subagents should be assigned by responsibility instead of by generic availability.

## Ownership Map

| Module / Axis | Primary Role | Supporting Role | Scope |
| --- | --- | --- | --- |
| Naver report collection | `backend-developer` | `python-pro`, `test-engineer` | Fetch, parse, normalize, dedupe, and parser drift tests. |
| Summary aggregation | `python-pro` | `sql-pro`, `reviewer` | Daily summaries, stock-code-first grouping, target/opinion aggregation, output filters. |
| SQLite schema/repository | `sql-pro` | `backend-developer`, `test-engineer` | Migrations, FK integrity, upserts, replay safety, backup/verify/cleanup contracts. |
| Telegram notifications | `backend-developer` | `cli-developer`, `test-engineer` | Daily summary delivery, fragment resume, intraday outbox, command parsing, paging, memo replay safety. |
| Scheduler/CLI operations | `cli-developer` | `debugger`, `reviewer` | Task Scheduler wrappers, `operator-status`, `operator-control`, health exits, scheduled guards. |
| Admin GUI | `admin-ui-engineer` | `cli-developer`, `reviewer` | Local operator controls, scheduler cards, no-run calendar, safe settings, audit display, recovery controls. |
| User web-view | `web-ui-engineer` | `backend-developer`, `test-engineer` | GET-only friend-facing page, public-safe DTOs, archive/calendar, selected-stock display, market reference UI. |
| KRX Open API market data | `market-data-engineer` | `sql-pro`, `backend-developer` | Stock/ETF/index snapshots, field validation, backfill safety, KRX source ownership. |
| KRX Data Marketplace flow | `market-data-engineer` | `debugger`, `sql-pro`, `test-engineer` | `[12008]`, `[12009]`, `[12010]` request validation, sample capture, import, scheduled-ingest design. |
| Category/taxonomy | `market-data-engineer` | `sql-pro`, `web-ui-engineer` | 업종/테마 source rules, category snapshots, fallback handling, display naming. |
| Candidate evidence | `market-data-engineer` | `sql-pro`, `web-ui-engineer`, `reviewer` | Read-only candidate evidence DTO, evidence separation, exclusion rules, no-scoring boundary. |
| Future intraday observation reference | `market-data-engineer` | `web-ui-engineer`, `security-hardening`, `reviewer`, `test-engineer` | Lab/staging read-only quote/turnover/index source review, top-2 `우선 확인` priority impact, freshness/failure behavior, no broker execution. |
| Future operator decision/execution lane | `market-data-engineer` + `security-hardening` | `reviewer`, `sql-pro`, `test-engineer`, `cli-developer` | Only after stable real-time source proof. Operator-only decision support and execution-lab safety; never collapse into public `web-view`. |
| Rotation overlay | `web-ui-engineer` | `market-data-engineer`, `admin-ui-engineer` | Cycle image overlay, alias mapping, coordinate map, future calibration UI. |
| Access gate / public-safe boundary | `security-hardening` | `web-ui-engineer`, `admin-ui-engineer`, `reviewer` | Entry-code gate, GET-only regression, admin/web-view separation, external-sharing safety checks. |
| External sharing / mini PC | `documentation-engineer` | `reviewer`, `cli-developer` | Handoff docs, access gate, Cloudflare/Tailscale boundary, operation profile notes. |
| Documentation consistency | `documentation-engineer` | `reviewer` | Canonical docs, roadmap/current-work sync, stale plan cleanup. |

## Current Role Split Candidates

| Near-Term Work | Recommended Owner | Why |
| --- | --- | --- |
| User web-view search bar | `web-ui-engineer` | UI/navigation change on the friend-facing surface. |
| `candidate_evidence` DTO | `market-data-engineer` + `sql-pro` | Requires source separation and stable joins across report/KRX/flow/category data. |
| Candidate evidence web-view preview | `web-ui-engineer` | Should preserve the no-trading-recommendation boundary and compact layout while allowing observation-candidate wording. |
| Rotation image text alias table | `market-data-engineer` | Needs taxonomy mapping discipline before UI polish. |
| Rotation overlay calibration UI | `admin-ui-engineer` | Calibration is operator-facing, not friend-facing. |
| KRX scheduled-ingest design | `market-data-engineer` + `debugger` | Requires login/session, skip, retry, and audit/event thinking. |
| Live scheduler review | `debugger` | Focus is root-cause isolation and unattended-run evidence. |
| DB backup/restore/cleanup policy | `sql-pro` | Data safety and retention boundaries. |
| Access-code/public sharing hardening | `security-hardening` | Should review exposed DTOs, blocked routes, and external-sharing assumptions before Cloudflare/Tailscale work. |

## Module Boundaries To Preserve

| Boundary | Rule |
| --- | --- |
| `admin-gui` vs `web-view` | Do not merge them. Admin has controls; web-view is read-only. |
| Reports vs KRX data | Do not store market data in report tables or overwrite report facts with market facts. |
| Category labels vs KRX market data | Do not call current 업종/테마 labels KRX-owned taxonomy unless verified. |
| Candidate evidence vs scoring | Evidence rows and observation-candidate recommendation can be built now; public numeric scoring and trading recommendation require later policy approval. |
| Real-time reference vs execution | Future intraday data may affect observation priority after approval, but must stay separate from broker secrets, order routing, production DB writes, and Telegram/scheduler automation until separately approved. |
| Public observation vs operator decision | Public `web-view` can recommend what to observe. Trading-decision support, if pursued later, is operator-only and requires a separate source/audit/safety contract. |
| Flow samples vs scheduled ingest | Manual/sample/import path exists. The only automatic flow path is the narrow anchor-date mentioned-stock `[12009]` 31-day backfill; broad scheduled ingest remains disabled until separate approval. |
| Access gate vs real auth | Entry-code gate is a lightweight layer, not enterprise authentication. |

## Escalation Points

Pause and ask for user approval before:

- destructive DB migration, broad deletion, or real VACUUM without explicit confirmation
- enabling scheduled KRX Data Marketplace ingest
- connecting a real-time/broker source to production writes, Telegram, scheduler, admin controls, broker secrets, or order routing
- exposing `admin-gui` beyond loopback/private owner access
- adding trading recommendation, public numeric score, investment grade, or buy/sell wording
- silently copying today's category mapping backward into historical dates
- storing new secret material outside `.env` or approved local files

## Suggested Subagent Use

Default operating rule:

- Keep small and obvious single-surface edits local.
- For non-trivial work, prefer a subagent split before implementing.
- Use investigation -> implementation -> review as the default shape when the task touches data, DB, scheduler, Telegram, `admin-gui`, `web-view`, external sharing, or candidate evidence.

| Situation | Use |
| --- | --- |
| UI rendering bug, layout density, public-safe copy | `web-ui-engineer` |
| Admin controls, status cards, operator actions | `admin-ui-engineer` |
| DB schema/upsert/verify/backup concerns | `sql-pro` |
| Parser/runtime/typing failures | `python-pro` |
| Scheduled run or worker heartbeat failure | `debugger` |
| Access gate, GET-only, or public-safe exposure review | `security-hardening` |
| KRX/ETF/flow field or source question | `market-data-engineer` |
| Regression test expansion | `test-engineer` |
| Design/roadmap/doc drift | `documentation-engineer` |
| Risk review before exposing or enabling automation | `reviewer` |


<!-- Merged from: docs/codex/architecture-guide.md -->
## Agent Guide

## Purpose

This is the consolidated agent usage guide for `02.Stock_Moniter`.

Use this before spawning or assigning subagents. Older agent prompt/planning files remain as reference, but this file is the active routing guide.

2026-05-29 update: project-local `.codex/agents/` is intentionally absent. Use the global Codex agent/skill layer plus CodeGraph first. Role names below are ownership/routing vocabulary for prompts and reviews, not a request to recreate local TOML agents.

## Default Rule

For small and obvious single-surface edits, keep the work local.

For non-trivial work, prefer subagent use by default. Split the task into investigation, implementation, and review when that reduces risk or gives a clearer handoff.

Typical split:

| Work slice | Preferred routing |
| --- | --- |
| Investigation / source or code boundary | `explorer`, `debugger`, `market-data-engineer`, `sql-pro`, or the relevant UI/backend specialist |
| Implementation | `backend-developer`, `python-pro`, `cli-developer`, `web-ui-engineer`, `admin-ui-engineer`, `market-data-engineer`, or `test-engineer` |
| Review / risk check | `reviewer`, `security-hardening`, `sql-pro`, or `test-engineer` |

Do not keep agents open after their result is integrated. Close completed agents to avoid slot exhaustion.

## Role Routing

| Need | Preferred agent |
| --- | --- |
| Parser, summary, runtime Python contracts | `python-pro` |
| Fetch, parse, persist, notify pipeline | `backend-developer` |
| CLI, scheduler wrappers, shell-facing workflows | `cli-developer` |
| SQLite schema, migrations, dedupe, backup/restore | `sql-pro` |
| Regression tests and unattended-run checks | `test-engineer` |
| PR-style risk review | `reviewer` |
| Runtime/scheduler/Telegram failure isolation | `debugger` |
| KRX/KIS/ETF/flow source boundaries | `market-data-engineer` |
| Local operator UI | `admin-ui-engineer` |
| Shared GET-only user page | `web-ui-engineer` |
| Access gate, exposure boundary, public-safe route review | `security-hardening` |
| Roadmap, handoff, changelog, docs | `documentation-engineer` |

## Optional Global Skill

`$scrapling-official` is the preferred active source-probe skill for new browser-gated, rendered-page, anti-bot-sensitive, or future-source work.

If the old global skill `$botasaurus-stock-monitor` is present, treat it as legacy/archived reference only. Do not use it as an active maintained probe lane unless the user explicitly asks to restore it.

If the global skill `$scrapling-official` is installed, use it as an active source-probe lane for:

- rendered-page extraction where simple request or API paths return only an app shell
- browser-gated or anti-bot-sensitive source checks
- bounded source comparison before deciding whether a source should remain probe-only, become fallback, or be proposed for later integration

For Scrapling CLI extraction commands, include `--ai-targeted`. The installed shared runtime is `{USER_HOME}\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe`. Do not wire Scrapling into production DB writes, Telegram automation, scheduler tasks, `admin-gui`, or public `web-view`. KRX/Data Marketplace should still prefer existing request/login/sample validation paths first; use Scrapling only for bounded source probing when those paths are insufficient or the source is new/unstable.

`$kronos-market-forecast` is not part of the current active global baseline. Treat old Kronos outputs as historical research-only references unless the user explicitly re-enables that lane. If it is re-enabled later, use it only for:

- offline OHLCV forecast experiments on stored KRX data
- comparison against backtest-observation or candidate-evidence views
- hidden research work before any scoring policy discussion

Do not use it for public numeric scores, trading recommendations, Telegram alerts, scheduler decisions, or direct product-surface changes.

## CodeGraph MCP

`codegraph` is available for this project and already initialized under `{PROJECT_ROOT}\.codegraph`.
Treat it as a code-navigation backend for existing agents, not as a new product dependency.

Prefer it first when the task is about:

- fetch -> parse -> persist -> summarize -> notify ownership
- scheduler wrapper or CLI entry paths
- admin/web-view route ownership
- schema / migration impact
- deciding whether an experiment or source probe leaks into production behavior

Good pairings:

| Need | Preferred agent + CodeGraph use |
| --- | --- |
| runtime flow trace | `debugger` or `backend-developer` + callers/callees/impact |
| source/market-data boundary trace | `market-data-engineer` + callers/callees/impact |
| schema or replay risk | `sql-pro` + impact |
| exposure/public-safe review | `security-hardening` or `reviewer` + route/DTO impact |
| admin/web-view path ownership | `web-ui-engineer` or `admin-ui-engineer` + path narrowing |

Do not overuse it for:

- known single-file edits
- obvious doc wording changes
- tiny local test updates with fully known scope

After using `codegraph`, still read the real file contents before editing or making a final claim.

## Skill vs Agent Comparison

Skills and agents are not interchangeable.

Use a skill when the task needs a specialized workflow or tool lane. Use an agent when the task needs role-based investigation, implementation, or review inside this project.

| Task type | Prefer skill | Prefer agent | Why |
| --- | --- | --- | --- |
| KRX Open API stock/ETF/index daily data | none | `market-data-engineer`, `backend-developer`, `sql-pro` | The approved Open API path already exists in the main codebase. No browser or anti-detect probe is needed. |
| KRX Data Marketplace login/session/source probing | Existing request/login/sample validation first; `scrapling-official` only for bounded browser/source probes when needed | `market-data-engineer`, `debugger` | Scrapling is the active probe tool, but source semantics and production boundary still need project agents. Botasaurus is legacy reference only unless explicitly restored. |
| KRX investor-flow schema/import/display | none by default | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` | The data should flow through existing repository/schema/web-view contracts, not through a separate probe lane. |
| Future real-time quote/turnover lane | source-specific skill or `scrapling-official` only for bounded reachability probes | `market-data-engineer`, `web-ui-engineer`, `security-hardening`, `reviewer`, `test-engineer` | Read-only lab/staging first. After approval, values may affect observation priority and `우선 확인`, but not broker execution, public scores, or trading calls. |
| Future operator decision/execution lane | source/broker skills only after explicit approval | `market-data-engineer`, `security-hardening`, `reviewer`, `sql-pro`, `test-engineer`, `cli-developer` | Do not treat current public wording limits as a permanent goal. Trading-decision support is possible only as a separate operator-only/execution-lab path after real-time source, audit, permission, and order-safety gates. |
| Naver report collection/parser | none by default; `scrapling-official` only for bounded source discovery | `backend-developer`, `python-pro`, `test-engineer` | Main Naver pipeline is production code; Scrapling probes must not replace stable request/API paths without documented evidence. |
| Telegram/scheduler/SQLite operation | none | `cli-developer`, `debugger`, `test-engineer`, `reviewer` | Operational behavior needs CLI/DB/replay safety, not a browser skill. |
| User `web-view` / admin UI | Browser/Chrome plugin for ordinary local inspection; Playwright MCP only for repeatable lab/E2E-style checks | `web-ui-engineer`, `admin-ui-engineer`, `security-hardening` | Browser tools verify UI, but implementation/review should stay with UI/security agents. |
| OHLCV forecast experiment | none by default; historical Kronos lane only if explicitly re-enabled | `market-data-engineer`, `reviewer` | Keep forecast comparisons research-only; they must not feed public scoring directly. |
| Public numeric scoring / trading recommendation | none for production | `reviewer`, `market-data-engineer`, `sql-pro`, `test-engineer` | Still blocked. Skills can support experiments only; public score requires data/holdout policy first. Observation-candidate recommendation remains a product/UI task, not a trading recommendation. |
| Documentation/roadmap/handoff | `superpowers:writing-plans` for large implementation plans | `documentation-engineer` | The skill structures plans; the agent keeps local docs consistent. |

Context7 is the preferred docs lookup for current library/framework/API documentation. HeroUI guidance is relevant only for a future React/Next rewrite, not for the current Python `admin-gui` or `web-view`.

Practical rule:

- If the question is "can this source be reached or probed?", consider a skill.
- If the question is "should this become product behavior?", use agents and repository tests.
- If the result would touch Telegram, scheduler, SQLite, `admin-gui`, or `web-view`, do not let a skill bypass the normal implementation/review path.

## Required Context For Agents

Always include:

- Scope is only `{PROJECT_ROOT}`.
- Read `AGENTS.md`.
- Check [data-governance.md]({PROJECT_ROOT}/docs/codex/data-governance.md) before data-display or parsing work.
- Preserve `admin-gui` vs `web-view` boundary from [surface-guide.md]({PROJECT_ROOT}/docs/codex/surface-guide.md).
- Do not enable KRX Data Marketplace scheduled ingest without explicit approval.

## Closure Rule

After each agent task:

1. Integrate or record the result.
2. Close the agent if no follow-up is needed.
3. Update roadmap or changelog only if the result changes project state.

## Avoid

- Multiple agents reviewing the same stale issue without new code context.
- Agents holding slots after final response.
- Agent tasks that ask broad questions instead of producing a concrete patch, finding, or decision.


<!-- Merged from: docs/codex/architecture-guide.md -->
## Agent Reassessment

2026-05-29 decision: keep project-local `.codex/agents/` absent. The role names below remain useful ownership vocabulary, but the default execution layer is now global agents/skills plus CodeGraph. Do not recreate or bulk-restore the old local TOML agent set unless repeated Stock Monitor work proves one exact missing role.

## Current work axes

| Axis | Current state | Primary local evidence |
| --- | --- | --- |
| Live operation validation | Runnable MVP is in live-market validation and operational hardening mode. | `AGENTS.md`, `operating-guide.md` |
| Telegram MVP | Scheduled daily summary, intraday alert, paging, memo capture, status helpers, and fragment resume exist. | `operating-guide.md`, `operating-guide.md` |
| Admin GUI | `admin-gui` is a local control-capable operator surface. | `operating-guide.md`, `module-ownership.md` |
| User web-view | Separate GET-only read-only `web-view` exists for friend/user information display. | `operating-guide.md`, `surface-guide.md` |
| KRX market reference | Stock/ETF/index snapshots exist and are treated as read-only market context. | `operating-guide.md`, `data-governance.md` |
| KRX investor flow | Data Marketplace validation/import/display paths exist, but scheduled ingest is disabled. | `operating-guide.md`, `market-data-runbook.md` |
| Category/taxonomy | 업종/테마 are a separate taxonomy layer with category snapshots and fallback debt. | `operating-guide.md`, `data-governance.md` |
| Candidate evidence | Read-only evidence rows can support observation-candidate recommendation; no public numeric scoring or trading recommendation. | `candidate-evidence-plan.md`, `operating-guide.md` |
| Future operator decision lane | Not built. Possible only after stable real-time data, source freshness, failure behavior, permission, and order-safety gates are proven. | `operating-guide.md`, `operating-guide.md`, `surface-guide.md` |
| External sharing | Optional entry-code gate exists; Cloudflare/Tailscale not configured. | `operating-guide.md`, `surface-guide.md` |

## Next-phase axes

| Axis | Needed work | Likely owner set |
| --- | --- | --- |
| Operational closeout | Scheduler/worker/delivery/DB health observation across market days. | `debugger`, `cli-developer`, `reviewer`, `test-engineer` |
| User web-view closeout | Stock search bar, mobile QA, display cleanup, public-safe regression. | `web-ui-engineer`, `test-engineer`, `security-hardening` |
| Candidate evidence foundation | Read-only DTO combining report/KRX/flow/category facts without score. | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` |
| Future operator-only decision support | Boundary design only after real-time source proof. | `market-data-engineer`, `security-hardening`, `reviewer`, `sql-pro`, `test-engineer` |
| Rotation / ETF candidate preview | Cycle image alias mapping, 업종-to-ETF candidates, preview only. | `market-data-engineer`, `web-ui-engineer`, `admin-ui-engineer` |
| Category snapshot cleanup | Reduce fallback dates through explicit source-date refresh and safe DB workflow. | `market-data-engineer`, `sql-pro`, `backend-developer`, `test-engineer` |
| Mini PC / external sharing prep | Access gate, Cloudflare/Tailscale boundary, operation profile, no public admin. | `security-hardening`, `documentation-engineer`, `cli-developer`, `reviewer` |

## Role Vocabulary To Keep

| Role | Keep reason | Use when |
| --- | --- | --- |
| `backend-developer` | Still needed for production behavior across fetch, parse, store, summarize, notify. | End-to-end backend behavior changes after the boundary is known. |
| `python-pro` | Still useful for Python runtime contracts, parsing, typing, and implementation seams. | Runtime/typing/parser bugs or Python module refactors. |
| `cli-developer` | Required for scheduler wrappers, operator commands, safe flags, and automation-facing UX. | CLI command, exit-code, Task Scheduler wrapper, or shell workflow changes. |
| `sql-pro` | Needed as read-only reviewer for schema/query/dedupe/migration correctness. | DB contract review before repository or migration work. |
| `reviewer` | Needed for PR-style risk review around business days, dedupe, delivery, and missing tests. | Before/after high-risk changes or when user asks for a review. |
| `debugger` | Needed for unattended-run, scheduler, worker heartbeat, and runtime-state failures. | When observed behavior differs from expected scheduled behavior. |
| `test-engineer` | Needed because replay, paging, outbox, scheduler, and DTO boundaries are regression-sensitive. | Add or repair focused tests after behavior changes. |
| `admin-ui-engineer` | Still distinct from web-view because `admin-gui` is control-capable. | Operator-facing GUI/status/control work. |
| `web-ui-engineer` | Still distinct from admin because `web-view` is friend-facing and GET-only. | User page layout, public DTO rendering, archive/search/detail UX. |
| `documentation-engineer` | Needed because current state is document-heavy and easy to drift. | Roadmap/current-work/handoff/surface-contract sync. |
| `market-data-engineer` | Strongly needed for KRX/ETF/flow, category snapshots, and candidate evidence. | Source/field/schema boundary and market-data expansion. |
| `security-hardening` | Now justified by access-code gate and future external sharing. | Entry-code gate, public-safe DTO, GET-only/admin boundary checks. |

## Add

No new local agent is required immediately.

| Potential new agent | Decision | Reason |
| --- | --- | --- |
| `candidate-analytics-engineer` | Do not add now. | Candidate evidence can be covered by `market-data-engineer` + `sql-pro` + `web-ui-engineer` + `reviewer`. Adding a scoring/analytics role too early would encourage premature trading-recommendation logic. |
| `deployment-engineer` | Do not add now. | Mini PC and Cloudflare/Tailscale are still preparation work. `security-hardening`, `cli-developer`, and `documentation-engineer` cover the current scope. |
| `data-visualization-engineer` | Do not add now. | Rotation overlay and web-view visuals are covered by `web-ui-engineer`; calibration can use `admin-ui-engineer`. |

## Merge or restore

No project-local agent should be restored now.

| Agents | Assessment | Action |
| --- | --- | --- |
| `backend-developer` / `python-pro` | Overlap exists around implementation, but boundary is manageable: backend owns product behavior, python-pro owns runtime/module contracts. | Keep both as routing vocabulary; choose one primary per task. |
| `admin-ui-engineer` / `web-ui-engineer` | Intentional split. Admin is control-capable; web-view is public-safe read-only. | Keep both as routing vocabulary; do not merge the surfaces. |
| `market-data-engineer` / `sql-pro` | Overlap on schema planning, but market-data owns source semantics and sql-pro owns DB correctness. | Keep both as routing vocabulary; use sql-pro as review/contract specialist. |
| `reviewer` / `test-engineer` | Overlap on risk, but reviewer finds issues and test-engineer codifies regressions. | Keep both as routing vocabulary. |
| `documentation-engineer` / `reviewer` | Overlap on correctness, but documentation-engineer owns doc drift while reviewer owns behavioral risk. | Keep both as routing vocabulary. |
| `security-hardening` / `reviewer` | Overlap on risk review, but security-hardening is specifically exposure/public-surface focused. | Keep both as routing vocabulary due to access gate and future sharing. |

## Why

The old local agent set was broad but the role boundaries are justified by the project shape.

The project is no longer only a scraper. It now has independent operating axes:

- unattended scheduled operation
- replay-safe Telegram delivery
- SQLite schema and migration safety
- local control-capable admin UI
- separate friend-facing read-only web-view
- KRX market and investor-flow data expansion
- category/taxonomy history
- candidate-evidence planning
- external-sharing preparation

The main risk is not missing an agent. The main risk is assigning the wrong agent to a task and blurring boundaries:

- Do not let `web-ui-engineer` add control behavior to `web-view`.
- Do not let `admin-ui-engineer` turn admin into a friend-facing surface.
- Do not let `market-data-engineer` move from evidence to public numeric scoring or public trading recommendation without reviewer approval. Observation-candidate recommendation remains a web-view/product copy boundary. Future trading-decision support, if pursued, is operator-only and needs a separate execution-lab/source-safety contract.
- Do not let `backend-developer` make DB-shape changes without sql/repository review.
- Do not let `security-hardening` become broad enterprise-auth work; keep it focused on local exposure risk.

When work is multi-step, cross-module, high-risk, or needs separate review, use these boundaries with the global layer and CodeGraph to split investigation, implementation, and review. Do not spawn agents for small, low-risk, single-surface edits.

## Skills versus agents

The current active global skill inventory exposes `scrapling-official` for this project. Older project-specific lanes remain as historical or optional references:

- `scrapling-official` is active for bounded browser/source probes.
- `botasaurus-stock-monitor` is archived legacy reference only unless explicitly restored.
- `kronos-market-forecast` is historical research-only/hold unless explicitly re-enabled.

These lanes are not replacements for repository ownership review.

| Capability | Skill fit | Agent fit | Decision |
| --- | --- | --- | --- |
| KRX Open API stock/ETF/index backfill | No special skill needed. | `market-data-engineer`, `backend-developer`, `sql-pro` | Keep using the existing Open API CLI/repository path. |
| KRX Data Marketplace browser/session probing | Existing request/login/sample validation first; `scrapling-official` only when a bounded browser/source probe is needed. | `market-data-engineer`, `debugger` define what success means and whether it should influence the product. | Scrapling is active tooling; Botasaurus is legacy reference only. |
| Browser-gated rendered-page/source probing | `scrapling-official` is appropriate for bounded rendered extraction and anti-bot-sensitive source comparison. | `market-data-engineer`, `debugger`, `reviewer` decide whether the result stays probe-only, becomes fallback, or needs later integration design. | Use Scrapling as the preferred active probe tool; do not wire it into production ingest or public surfaces. |
| KRX investor-flow import/display | No skill by default. | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` | Use the normal DB/DTO/UI path. |
| Stored OHLCV forecasting experiment | No active skill by default; historical Kronos results are reference-only unless explicitly re-enabled. | `market-data-engineer`, `reviewer`, `test-engineer` judge whether results are meaningful. | Keep forecast output offline and hidden. |
| Web-view visual verification | Browser/Chrome plugin is appropriate for ordinary local UI inspection; Playwright MCP is optional for repeatable lab/E2E-style checks. | `web-ui-engineer`, `security-hardening` implement and review public-safe UI behavior. | Browser tools verify; agents own changes. |
| Telegram/scheduler/SQLite safety | No project skill should handle this. | `cli-developer`, `debugger`, `sql-pro`, `test-engineer`, `reviewer` | Keep in local code/review workflow. |
| Public numeric score / trading recommendation | No skill should directly produce product behavior. | `reviewer`, `market-data-engineer`, `sql-pro` must approve data/holdout policy first. | Still blocked from public surfaces; observation-candidate recommendation is allowed separately. Future operator-only decision support is a separate lane, not a skill shortcut. |

The reason this comparison was not previously prominent is that the data targets overlapped: both skills and agents can touch "market data" in a broad sense. The actual boundary is narrower:

- Scrapling answers browser/source-access, rendered-page extraction, anti-bot-sensitive source reachability, and source comparison questions.
- Botasaurus remains historical reference only unless explicitly restored.
- Kronos is not active in the current baseline; keep old offline forecast-experiment output as historical reference unless explicitly re-enabled.
- Local agents answer product correctness, DB safety, UI boundaries, Telegram operations, and documentation consistency.

## Suggested prompt examples

### User web-view search

```text
Use web-ui-engineer to add the top-right stock search flow to the GET-only web-view.
Keep admin-gui separate, do not add write/control routes, and add public-safe regression tests.
```

### Candidate evidence DTO

```text
Use market-data-engineer and sql-pro to design the first read-only candidate_evidence DTO.
Use only stored Naver report summaries, KRX market snapshots, stored investor-flow rows, and category snapshots.
Do not add public numeric scoring, trading-recommendation wording, Telegram alerts, or final picks. Observation-candidate wording such as `오늘의 관찰 후보` is allowed only after the UI boundary is checked.
```

### Candidate evidence UI

```text
Use web-ui-engineer to render candidate_evidence as 관찰 후보 근거 in web-view.
Keep evidence separated by report, price/turnover, investor flow, and category context.
Allow `오늘의 관찰 후보`, `우선 확인`, and `관찰 우선순위`; block public numeric 점수, 투자등급, 매수/매도 추천, and buy/sell wording.
```

### KRX Data Marketplace scheduled ingest design

```text
Use market-data-engineer and debugger to draft Stage 6 scheduled-ingest design for KRX Data Marketplace flow.
Focus on login/session checks, LOGOUT skip behavior, retry, operation events, backup/verify prerequisites, and disabled-by-default scheduling.
Do not enable the scheduler.
```

### DB migration or repository change

```text
Use sql-pro to review the proposed schema/repository change first, then use backend-developer or python-pro for implementation.
Preserve migration-runner discipline, foreign keys, idempotent upserts, and db-verify coverage.
```

### Admin GUI operation control

```text
Use admin-ui-engineer to improve the local admin-gui operator flow.
Keep it loopback/operator-only, preserve confirmation text for risky controls, and do not expose admin behavior through web-view.
```

### External sharing hardening

```text
Use security-hardening to review access-code gate behavior and web-view public-safe responses before Cloudflare Tunnel setup.
Confirm admin-gui, scheduler controls, settings, DB paths, .env, Telegram token/chat id, and audit logs are not exposed.
```

### Live scheduler issue

```text
Use debugger to isolate the scheduled-run failure.
Compare expected task window, operator profile, business-day guard, worker heartbeat, operation events, and delivery/outbox state.
Return confirmed evidence separately from hypotheses.
```

### Documentation drift

```text
Use documentation-engineer to reconcile AGENTS.md, current-work, next-phase, module-ownership, and execution-roadmap with current implementation.
Do not add a new planning document unless the content cannot fit an existing canonical doc.
```

## External reference assessment

External references reviewed on `2026-05-11`:

- `Vibe-Trading`
- `spec-kit`
- `lightweight-charts`

### What to take

- `Vibe-Trading`
  - Reinforces keeping security/public-surface boundaries explicit before broader sharing.
  - Confirms the value of dedicated source/tool/domain roles rather than one generic implementation agent.
- `spec-kit`
  - Reinforces the existing document-first flow around `current-work`, `next-phase`, `module-ownership`, `surface-contract`, and `candidate-evidence-plan`.
- `lightweight-charts`
  - Useful as a future implementation library candidate if `web-view` later needs interactive market charts.

### What not to take now

- `Vibe-Trading` trading-strategy, backtest, portfolio, swarm-finance roles
  - Too broad and too domain-specific for the current Stock Monitor scope.
- `spec-kit` as a new dedicated agent
  - Current `documentation-engineer` plus existing docs already cover the immediate need.
- `lightweight-charts`-driven chart agent
  - The next-phase docs emphasize search, candidate evidence, public-safe DTOs, and sharing boundaries before charts.

## Final keep / add / merge-remove

### Keep

- `backend-developer`
- `python-pro`
- `cli-developer`
- `sql-pro`
- `reviewer`
- `debugger`
- `test-engineer`
- `admin-ui-engineer`
- `web-ui-engineer`
- `documentation-engineer`
- `market-data-engineer`
- `security-hardening`

### Add

- none now

### Merge or remove

- none now

The external references did not justify another immediate local agent beyond the already-added `security-hardening`.


<!-- Merged from: docs/codex/architecture-guide.md -->
## Decision Log

## Scope Constraint

- All decisions here apply only to `{PROJECT_ROOT}`.
- No external folder state should be treated as part of this project.

## 2026-04-24 to 2026-04-25

### Project Purpose

- Build a personal-use MVP that monitors the Naver Stock research company page for the domestic stocks tab.
- Collect newly observed reports during Korean business hours.
- Send a next-business-day morning summary.

### Page Scope

- MVP scope is limited to the domestic stocks tab on the target research page.
- Other tabs are intentionally excluded for now because parsing rules are not yet clearly defined there.

### Polling Window

- Poll every 30 minutes from `08:30` to `16:30` KST.
- This window intentionally covers the current desktop-validation monitoring window and is separate from the `08:10` KRX Open API backfill after the official next-business-day `08:00` publication window and the `08:20` daily briefing sequence.
- Polling hours remain configurable through environment variables and task registration arguments.

### Business-Day Rule

- Scheduling follows Korean market business days.
- Daily summary is sent at `07:00` KST on the next Korean business day.
- 2024~2026 KRX market holidays and year-end closures are treated as default business-day overrides.

### Meaning of Mention Count

- Mention count is defined as the number of new reports for a stock on that business day.
- It is not defined as scroll exposure count across polling runs.

### New Report Identity

- A report is treated as new based on:
- stock
- title
- broker
- published datetime

### Daily Aggregation Rule

- Aggregate by `stock x business day`.
- Daily summary notification sends the top `7` summarized stocks by default.
- Additional summary pages are fetched on demand through Telegram commands.

### Same Broker Multiple Reports

- Notification display should group same-broker repeats as `broker_name(count)`.
- Representative target price for the same broker uses the maximum parsed value.
- Representative opinion for the same broker uses the most recent report.

### Target Price Summary

- Daily stock target price summary uses the minimum and maximum parsed values from that day's new reports.
- Missing or non-numeric target prices are not aggregate values.
- If no numeric target price is available, summary/detail display uses `-`, while raw/detail views still make it clear that the source report had no target price.

### Opinion Normalization

- Normalize opinions into:
- `buy`
- `neutral`
- `sell`
- `N/A`

- Daily dominant opinion uses the mode of valid normalized values.
- `N/A` is excluded from dominant-opinion voting and is used only when no valid opinion exists.
- Tie-break priority for valid opinions is `buy > neutral > sell`.

### Data Quality Boundary

- Raw/source values, parsed/storage values, aggregate values, and display values must be reviewed separately.
- `N/A`, `NA`, `NULL`, `NONE`, `-`, and blank numeric fields are missing markers, not numeric or ranking values.
- Missing values may be preserved in stock detail or stock search output, but must not distort target ranges, representative opinions, rankings, or market summaries.
- Display placeholders such as `목표가 -`, `의견 없음`, and `KRX 기준값 없음` are surface-specific presentation text and must not overwrite stored facts.
- Report identity is based on `source_id` or `identity_key`, not display text.
- `broker_display` is display-only derived text; do not parse it back as canonical broker data.
- `published_at`, `business_date`, and `collected_at` have separate meanings; archive and summary grouping use `business_date`.
- The persistent checklist is [data-governance.md](/docs/codex/data-governance.md).

### Technical Direction

- Recommended MVP stack is `Python + Playwright + SQLite + Telegram Bot + Windows Task Scheduler`.
- The first implementation can run on the main Windows PC, but the operating model should remain portable to a separate always-on Windows mini PC without major redesign.
- Environment-based configuration, local scheduler scripts, and self-contained SQLite storage are preferred because they lower the cost of later host migration.

### Telegram Summary Paging

- Summary notifications should support `다음`, `전부`, and `처음` commands in the Telegram chat.
- The system tracks how many stocks have already been delivered for the active business date.

### Notification Modes

- There are two intended notification modes:
- next-business-day daily summary
- intraday monitoring during the configured poll window

- Intraday alerts are emitted per polling batch of newly inserted reports.
- Intraday alert delivery is backed by a durable outbox so failed sends can be retried on the next processing run.

### Telegram Command Surface

- The current Telegram command surface is intentionally minimal and text-based.
- Daily summary paging currently accepts:
- `다음`, `더`, `더보기`
- `전부`, `전체`
- `처음`, `처음부터`
- Slash aliases are also accepted for paging:
- `/다음`
- `/전부`
- `/처음`

- Stock-specific lookup is supported as:
- `/종목검색 017670`
- `/종목코드 삼성전자`

- `/종목검색` now acts as the main stock-query entry point:
- stock-code input resolves directly
- stock-name input returns numbered candidates first
- numeric follow-up input selects the target stock

- `/종목코드` remains as a helper command for explicit stock-code discovery.
- Slash commands such as `/다음목록` are accepted as operator ergonomics aliases.

### Stock Query Backlog

- The stock query version uses the stock-specific Naver research API and summarizes recent reports within a `D-15` window.
- `/종목검색` should always favor user confirmation when a stock-name query can map to multiple plausible listed names.
- Numeric follow-up selection is stored in Telegram control state with expiry so the polling-style command processor can complete the 2-step flow safely.
- Stock-query responses may include current price at the time of the lookup, but this is a query-time aid rather than part of the scheduled daily summary.
- Future enhancements can add richer pagination, broader historical windows, or quote freshness labels when needed.

### Future Sector View Direction

- A later phase may extend beyond per-stock alerts into sector-level accumulation and ranking.
- The first sector goal is to infer which sectors are leading on a given day by aggregating report counts and recency at the sector level.
- A second sector goal is to compare representative stocks within the same sector and later pair those names with daily demand or flow-style signals.
- This should be treated as a later data-product layer on top of the existing report collector rather than mixed into the MVP alert format immediately.
- Future UI work may expose this data through a lightweight web view once the stored data shape and operator preferences are stable enough.

### Future Operator Workflow

- The intended medium-term workflow is:
- Telegram for morning summary and intraday alerts
- a later web view for after-market review, browsing, and thinking
- That means the web layer does not need to replace Telegram; it should complement the notification flow with richer read-oriented views after the market session.
- Until several live-market days have validated the current batches and stored data, web-view work should remain in memo/backlog mode rather than active implementation.
- The `example/report_*.jpg` references are useful as layout and information-architecture inspiration, but the project should not copy unsupported trading-signal semantics directly.
- Useful reference patterns include market mood, strong/weak lists, category rotation, and next-watch candidates.
- `example/Cycle.jpg` should be treated as a conceptual reference for a future sector/theme rotation view, showing possible attention movement across broad market groups.
- Any rotation-cycle view should be descriptive and data-backed by accumulated report/sector/theme history, not a hard-coded prediction that money must move in a fixed order.
- Score, grade, and conviction-style displays should wait until there is enough historical data and a clear calculation rule.

### Future Operator/Admin Program

- A local admin surface is likely useful once the system moves toward N100 or other always-on operation.
- `admin-gui` must remain a local control surface. If a mini PC or remote access path is added, the read-only shared/web-view surface must be separate from the control admin surface.
- This separation is a permission/API boundary, not only a UI boundary.
- Do not implement the shared user page by adding a read-only mode to `admin-gui`.
- The `web-view` uses a separate page/server handler and GET-only read model.
- `web-view` can share SQLite, repository queries, and summary logic, but it must not expose admin control handlers or raw `build_operator_status_snapshot()` output.
- Remote access should use private access paths such as VPN, mesh networking, restricted tunnel, or remote desktop rather than directly exposing the control admin page.
- The read-only `web-view` must not include POST controls for scheduler execution, scheduler enable/disable, shutdown, pause/resume, `.env`, or token/config changes.
- Telegram shortcuts that open or expose `admin-gui`, such as `/관리자페이지 열기`, are deferred.
- Future Telegram operator shortcuts should prefer read-only status and guidance, such as `/상태`, `/오늘돌아?`, `/스케줄상태`, and `/웹뷰주소`.
- KRDS (Korea Design System) should be the primary design reference for the local admin program and later web-view, so the project has a consistent baseline for layout, components, patterns, accessibility, and feedback.
- The admin surface should prioritize operator confidence over feature density: scheduler state, run-now controls, pause/resume controls, next run time, and recent errors matter first.
- It should also expose human-review surfaces such as local memos, pending ideas, data freshness, and last successful Telegram delivery.
- Configuration editing should be constrained to safe operational knobs at first, such as poll windows, default display limits, shutdown enablement, and holiday overrides.
- The first admin version should stay local-only and avoid turning into a public web service until security and deployment boundaries are deliberate.
- Backlog priority should favor operational confidence before richer analytics: admin/status visibility first, sector and mood summaries second, advanced scoring or flow-based alerts later.
- The initial admin view does not need a polished public web stack; a local-only page, simple server, or even a focused CLI/TUI is acceptable if it makes scheduler and data state visible.
- Holiday override management should be operator-editable because temporary holidays, personal off-days, and ad-hoc no-run days cannot be covered reliably by a static yearly holiday list.
- The admin view should expose recent operational logs in a visible status area, especially batch sends, skips, Telegram command-worker activity, and errors, because hidden scheduled work is hard to trust without feedback.
- A later admin/worker architecture should aim to avoid visible CMD/PowerShell windows by running tasks through direct Python calls, no-window subprocess options, or a service-style background worker. Task Scheduler shell wrappers can remain as a fallback, but the preferred operator experience is status in the admin panel rather than flashing console windows.
- KRDS should be adapted as a usability/design system, not copied as a government identity: official masthead or government-service wording is unnecessary for this private local tool, but KRDS-style consistency, readable typography, feedback, form, list, filter, error, and confirmation patterns should be followed.

### Future Data Preparation

- Keep per-report sector labels stable and available in stored views so sector rollups can be rebuilt historically.
- Sector/theme history should eventually use dated mapping snapshots. Until then, any historical sector/theme rollup should be treated as "latest mapping applied" rather than guaranteed historical classification.
- Be prepared to add a separate derived table for sector-day aggregates instead of recalculating everything only from Telegram-facing summary output.
- If representative-stock demand or flow signals are later added, they should likely live in their own ingest path and join onto the report-derived sector summary rather than overloading the current report schema directly.
- ETF data should use a separate ingest and display model rather than being inserted into company-report summaries.
- Report count is an attention signal, not supply/demand flow. Flow, volume, and trading-value data should be collected through a separate market-data ingest before rotation or interest-alert features rely on it.
- Naver industry/theme pages are the preferred domestic taxonomy source for industry/theme labels. KRX remains the preferred source for market data such as price, volume, turnover, ETF, and index context.
- Industry refresh should remain explicit and slow first (`refresh-industry <code>`), not broad automatic crawling, until source stability and rate behavior are observed.
- Store industry as the representative sector-like label in `stock_metadata`; keep theme membership as a separate many-to-many layer because one stock can belong to multiple themes.

### Future Target-Price Progress View

- A later web view may show how far each stock has progressed toward report target prices after the first target-bearing report is observed.
- A candidate display idea is `목표가의 N% 도달 (M일차)`.
- This is mainly a review/interest feature, not a trading signal by itself.
- The baseline should be the first observed report date with a numeric target price for the stock.
- The comparison price should use a clearly defined price source and timestamp, because current price and close price can tell different stories.
- This feature should wait until enough history exists to avoid over-interpreting a very short collection window.

### Future Follow-Up Interest Alert

- A later notification idea is to watch stocks that had reports today and then review supply/demand behavior through report day plus the next trading day.
- On the third trading day, the system could send a separate `관심종목` style alert if the follow-up conditions look notable.
- Foreign/institution/individual flow is a candidate input because the operator values supply/demand, but it should remain a supporting indicator rather than a standalone conclusion.
- The report collector should not be overloaded with this data; supply/demand or volume data should be collected through a separate ingest path and joined later.
- The exact trigger rules should be decided after studying a few live examples and any supplementary indicators that may help avoid noisy alerts.

### Host Operation

- Windows Task Scheduler registration is now part of the active operating model rather than a future task.
- The host only needs to be powered on and connected before the scheduled windows; the monitor does not require a permanently running foreground shell.
- Current weekday scheduler windows are `KrxDailyBackfill 08:10`, `Notify 08:20`, `Poll 08:30~16:30`, and `TelegramCommands 08:00~16:30`.
- During the live validation period, `StockMonitor-Shutdown` shuts the host down at `17:10` with a 60-second delay, so the `16:45` KRX login reminder and `16:50` flow validation window can complete first.
- The shutdown task should not use missed-run catch-up, because a delayed shutdown after a later boot would be more harmful than a missed same-day shutdown.
- Windows Task Scheduler itself is weekday-based and does not know Korean market holidays, so command processing and shutdown must use scheduled Python wrappers with internal business-day guards.
- Telegram command processing should use a single hidden daily worker loop rather than one Task Scheduler launch per minute, because per-minute launches can create visible console flicker even when each run immediately skips on holidays.
- Manual Telegram test sends must not share the same successful-delivery channel as production scheduled summaries.
- Production morning summaries use the `telegram` delivery channel.
- Manual operator test sends use the `telegram_test` delivery channel so weekend or ad-hoc testing cannot block the next weekday `08:20` briefing summary.
- Operator ideas sent through `/메모` are stored as local Markdown under `data/operator_memos.md`, not in source-controlled docs, so rough ideas can be captured quickly without turning into committed requirements too early.

### Known Documentation Issue

- `stock_research_monitor_mvp.md` appears with garbled Korean text in current shell output.
- Treat encoding verification as an explicit follow-up task before heavy editing.
