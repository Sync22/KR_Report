# Architecture Guide

System map, source boundaries, CodeGraph navigation, and decision history.

## Included sections
- Project Map
- Architecture Risk Review
- Current Ownership and Plan Pointer
- CodeGraph Index
- Current Investigation Routing
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
with Toss 20:00 stored market context, historical KRX references, and observation evidence.

## Current Structure

Project root:

- `{PROJECT_ROOT}`

Current files:

- [AGENTS.md](../../AGENTS.md)
- [README.md](../../README.md)
- [CHANGELOG.md](../../CHANGELOG.md)
- [pyproject.toml](../../pyproject.toml)
- [stock_research_monitor_mvp.md](../../stock_research_monitor_mvp.md)
- [docs/codex/architecture-guide.md](architecture-guide.md)
- [docs/codex/operating-guide.md](operating-guide.md)
- [docs/codex/documentation-index.md](documentation-index.md)
- [docs/codex/surface-guide.md](surface-guide.md)
- [docs/codex/data-governance.md](data-governance.md)
- [docs/codex/candidate-evidence.md](candidate-evidence.md)
- [docs/codex/research-notes.md](research-notes.md)
- [docs/codex/market-data-runbook.md](market-data-runbook.md)
- [docs/codex/mini-pc-runbook.md](mini-pc-runbook.md)
- [docs/codex/history.md](history.md)
- Use [docs/codex/documentation-index.md](documentation-index.md) to find canonical documents and cleanup rules.

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
- Toss 20:00 stored snapshot for current web-view market, ETF, and flow references
- bounded read-only Toss Top2 quote, Top2 daily-candle, and latest-date market-context GETs; Top2 quotes may fall back to Naver, and none persist data or reorder candidates
- Existing KRX records and schemas remain for historical analysis/recovery; no normal KRX market-data refresh or investor-flow ingest is scheduled.
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

- [data/krx_api_intake.local.md](../../data/krx_api_intake.local.md)

Important currently observed modules:

- `src/stock_monitor/cli.py`
- `src/stock_monitor/toss_openapi_web_view.py`
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

## Working-tree note

Use git status and git diff for the live change list; this guide records stable architecture and review findings.

## Architecture Risk Review

## Purpose

This document records the current architecture and risk-review snapshot for `02.Stock_Moniter`.

Use it when starting broad investigation across:

- fetch -> parse -> persist -> summarize -> notify
- scheduler / CLI wrappers
- `admin-gui` and read-only `web-view`
- replay, migration, data-source, public-safe, and performance boundaries

This is an investigation reference, not an implementation plan. Before changing parser, summary, notification, admin-gui, or web-view behavior, check [data-governance.md](data-governance.md) and [surface-guide.md](surface-guide.md).

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
| CLI entry | `python -m stock_monitor` enters [__main__.py](../../src/stock_monitor/__main__.py) and dispatches through [cli.py](../../src/stock_monitor/cli.py). |
| Fetch / parse | Naver report collection lives in [fetch/naver_research.py](../../src/stock_monitor/fetch/naver_research.py). |
| Persist | SQLite access is centralized in [db/repository.py](../../src/stock_monitor/db/repository.py); schema and migrations are in [db/schema.py](../../src/stock_monitor/db/schema.py). |
| Summarize | Daily report summaries are built in [summary.py](../../src/stock_monitor/summary.py). |
| Notify | Telegram formatting/control state are under [notify/](../../src/stock_monitor/notify); scheduled/manual orchestration is in [cli.py](../../src/stock_monitor/cli.py). |
| Scheduler | PowerShell wrappers in [scripts/](../../scripts/) call guarded CLI commands. Current task registration is documented in [mini-pc-runbook.md](mini-pc-runbook.md). |
| Admin surface | `admin-gui` is a local/operator control surface with guarded routes in [cli.py](../../src/stock_monitor/cli.py). |
| User surface | `web-view` is a separate GET-only/read-only surface; `/auth/login` is its access-code POST exception. |
| Current market data | Toss 20:00 snapshots supply stored web-view market/ETF/flow context. Separate bounded GETs supply live Top2/Top20 references without persistence or candidate reordering. Existing KRX rows are historical review/recovery data only. |
## Key Paths

| Concern | Path |
| --- | --- |
| Report fetch entry | [fetch/naver_research.py](../../src/stock_monitor/fetch/naver_research.py) |
| Report identity | [models.py](../../src/stock_monitor/models.py) |
| Report insert / intraday queue | [db/repository.py](../../src/stock_monitor/db/repository.py) |
| Daily summary build | [summary.py](../../src/stock_monitor/summary.py) |
| Daily delivery fragments | [db/schema.py](../../src/stock_monitor/db/schema.py), [db/repository.py](../../src/stock_monitor/db/repository.py) |
| Scheduled poll / notify | [scripts/run_scheduled_poll.ps1](../../scripts/run_scheduled_poll.ps1), [scripts/run_scheduled_notify.ps1](../../scripts/run_scheduled_notify.ps1), [cli.py](../../src/stock_monitor/cli.py) |
| Historical KRX recovery | [scripts/run_scheduled_krx_daily_backfill.ps1](../../scripts/run_scheduled_krx_daily_backfill.ps1), [fetch/krx_api.py](../../src/stock_monitor/fetch/krx_api.py), [cli.py](../../src/stock_monitor/cli.py); not an active scheduled baseline |
| Historical KRX mentioned-stock flow | [scripts/run_scheduled_krx_mentioned_flow_backfill.ps1](../../scripts/run_scheduled_krx_mentioned_flow_backfill.ps1), [cli.py](../../src/stock_monitor/cli.py); retained for historical/recovery use |
| Admin GUI handler | [cli.py](../../src/stock_monitor/cli.py) |
| Web-view handler / DTOs | [cli.py](../../src/stock_monitor/cli.py) |
| Bounded live web-view Toss provider | [toss_openapi_web_view.py](../../src/stock_monitor/toss_openapi_web_view.py); GET handlers and rendering in [cli.py](../../src/stock_monitor/cli.py) |
| Public-safe smoke / QA | [tests/test_web_view.py](../../tests/test_web_view.py), [tests/test_cli_commands.py](../../tests/test_cli_commands.py) |

## Confirmed Findings

1. Report identity and deduplication are enforced by repository constraints and indexes.
2. Missing target prices and opinions are excluded from aggregate ranges/votes while remaining visible in detail.
3. Telegram delivery fragments have durable status and resume support; ambiguous send outcomes still need a policy decision in the active TODO2 plan.
4. `admin-gui` and GET-only `web-view` use separate handlers and access boundaries.
5. Host binding defaults are guarded; non-loopback exposure requires an explicit option.
6. Current web-view market, ETF, and flow context comes from stored Toss 20:00 snapshots. KRX backfill/import paths are historical/recovery only and are not normal scheduled sources.
7. Web-view routes use existing caching, compression, performance logging, and query batching; preserve their regression checks when changing DTO builders.
## Plausible Risks

| Risk | Why it matters |
| --- | --- |
| `cli.py` concentration | It owns CLI dispatch, scheduler guards, both HTTP surfaces, DTO builders, source orchestration, and rendered HTML/JS. |
| CodeGraph refresh repeatability | The index was refreshed on 2026-09-27, but this runtime lacks the updater; refresh after future source changes from an environment that has it. |
| Summary uniqueness under stock-name drift | Rebuild groups code-first, while a uniqueness constraint includes `stock_name`; test migration/rebuild behavior if names change. |
| Naver live reference exception | Manual same-day `priceTop` is display/reference-only and must not become an unreviewed production source lane. |
| Public/operator boundary | Keep operator decision support separate from public `web-view` and Telegram. |
| Free-text operation event details | Keep raw event details operator-only or project them into safe public labels before exposure. |
| Dirty working tree baseline | Distinguish local edits from committed behavior during reviews. |
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
| KRX Open API | Existing rows are historical references; current stored market baseline is Toss 20:00. | Keep KRX reads out of current web-view fallback and normal refresh scheduling. |
| KRX Data Marketplace | Existing samples are historical/recovery references; current market flow uses stored Toss 20:00 snapshots. | Do not restore KRX scheduled ingestion as part of the current source baseline. |
| Naver `priceTop` | Manual same-day display-only web-view reference. | Ensure no DB writes, Telegram sends, scheduler changes, KRX replacement, or scoring are tied to this route. |
| Bounded live web-view references | Toss provides Top2 current quotes/provisional investor volume, Top2 candles, and latest-date market context through read-only GETs; Naver current quotes are a bounded Top2 fallback and Naver market-top is a separate user-triggered comparison. | Preserve server-derived Top2 scope, source/freshness labels, no persistence, and no candidate creation/reordering, Telegram/scheduler automation, account/order access, scores, or trading calls. |
| Future additional market sources | Any source beyond these bounded Toss/Naver references remains a separate lab/staging proposal before public use. | Do not connect new probes to DB writes, Telegram/scheduler automation, broker execution, public scores, or trading-call wording. |
| Future operator decision/execution lane | Separate from public `web-view` and Telegram. | It may evaluate trading-decision support only after stable real-time data, permission, audit, failure handling, and order-safety gates are defined. |
| Category taxonomy | 업종/테마 is a separate taxonomy layer, not official KRX taxonomy. | Ensure historical dates do not silently receive future/current category snapshots. |

## Performance Candidates

1. Web-view daily DTO builders combine reports, categories, market briefing, Toss close context, rotation evidence, and optional Naver intraday reference; keep their query budget visible.

2. Repository methods open a SQLite connection per call. WAL mode, cache size, busy timeout, and recent batching reduce risk, but DTO paths should keep query-budget tests.

3. The CodeGraph snapshot from 2026-09-27 indexed `cli.py`, `web_perf.py`, and `news/evidence_review.py`. Changes to `cli.py` and `repository.py` on 2026-09-28 and 2026-09-30, plus the current 2026-10-01 working-tree changes, make those call edges stale until an updater is available.

4. `candidate-evidence`, archive, and daily payload generation already have documented performance improvements. Future regressions should be checked with the existing web performance tests and browser smoke commands before adding more caching.

## Current Ownership and Plan Pointer

The path and flow tables above are the architecture map. Current role routing and project boundaries are owned by the root AGENTS.md; this guide does not maintain a second agent roster. Current follow-up tasks are owned by the active TODO2 board in [operating-guide.md](operating-guide.md).

## CodeGraph Index

The ignored `{PROJECT_ROOT}\.codegraph\codegraph.db` is local navigation data, not a product or runtime dependency.

**Last index snapshot (2026-09-27):** the upper-folder session refreshed CodeGraph after raising `maxFileSize` to 2 MiB so the 1.88 MiB `cli.py` was indexed. That snapshot contains 103 files, 3,831 nodes, and 8,672 edges, including 1,033 CLI nodes, 36 `web_perf.py` nodes, and 21 `news/evidence_review.py` nodes. `cli.py` and `repository.py` changed on 2026-09-28 and 2026-09-30; the current working tree also changes `cli.py`. Treat those indexed nodes and edges as stale until an updater runs. This runtime has no `codegraph` executable or configured MCP, so refresh from an environment that has the updater.

Treat CodeGraph as a code-navigation backend for existing agents, not as a new product dependency.

Prefer it first when the task is about:

- fetch -> parse -> persist -> summarize -> notify ownership
- scheduler wrapper or CLI entry paths
- admin/web-view route ownership
- schema / migration impact
- deciding whether an experiment or source probe leaks into production behavior

Use the current task-specific Luna role from the root `AGENTS.md`; CodeGraph narrows the paths and impact edges for that review.
Do not overuse it for:

- known single-file edits
- obvious doc wording changes
- tiny local test updates with fully known scope

After using `codegraph`, still read the real file contents before editing or making a final claim.

## Current Investigation Routing

Use the root AGENTS.md for current global skills, Luna roles, and project-specific safety rules. Use the CodeGraph section above for structural navigation, then inspect source files before making implementation claims. The decision log below is historical context, not a current work queue.

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
- At that time, this window covered desktop-validation polling and was separate from the then-scheduled KRX backfill and daily briefing.
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
- The persistent checklist is [data-governance.md](data-governance.md).

### Technical Direction

- Recommended MVP stack is `Python + Playwright + SQLite + Telegram Bot + Windows Task Scheduler`.
- The first implementation can run on the main Windows PC, but the operating model should remain portable to a separate always-on Windows mini PC without major redesign.
- Environment-based configuration, local scheduler scripts, and self-contained SQLite storage are preferred because they lower the cost of later host migration.

### Telegram Summary Paging

- Summary notifications should support `다음`, `전부`, and `처음` commands in the Telegram chat.
- The system tracks how many stocks have already been delivered for the active business date.

### Notification Modes

- There are two report-notification modes:
- next-business-day daily summary
- scheduled intraday briefing

- Scheduled polling collects and deduplicates reports every 30 minutes; it does not send a Telegram message at every poll.
- Intraday delivery is limited to `08:30`, then hourly from `09:30` through `15:30` KST. Merge current-business-date batches into one message at the next delivery slot.
- After a successful scheduled poll, if a delivery slot has no current-business-date batch, send the existing `0건` notice. Leave prior-date batches pending for operator recovery; they must not suppress the current-date empty notice or be relabeled as current reports.
- Later non-empty briefings may append the bounded Toss context; the report batch remains the candidate seed and ordering source.
- Intraday alert delivery is backed by a durable outbox so failed sends can be retried on the next processing run.
- The separate `09:15` / `12:00` / `15:15` `market-briefing` schedule is independent of report count and has additional live-send readiness guards; see the mini-PC runbook.

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

### Historical Sector View Proposal

The basic report-backed `업종`/`테마` rollups and reference panels are implemented. The broader flow-based sector ranking and interest-alert ideas below remain future work and must not be inferred from report counts alone.

- A later phase may extend beyond per-stock alerts into sector-level accumulation and ranking.
- The first sector goal is to infer which sectors are leading on a given day by aggregating report counts and recency at the sector level.
- A second sector goal is to compare representative stocks within the same sector and later pair those names with daily demand or flow-style signals.
- This should be treated as a later data-product layer on top of the existing report collector rather than mixed into the MVP alert format immediately.
- Future UI work may expose this data through a lightweight web view once the stored data shape and operator preferences are stable enough.

### Historical Operator Workflow Proposal

The original memo/backlog-only web-view direction below is superseded. The Python-rendered GET-only web-view and operator-only `admin-gui` are implemented as separate surfaces; current validation work is tracked in [operating-guide.md](operating-guide.md) and current route/source rules are in [surface-guide.md](surface-guide.md).

- The intended medium-term workflow is:
- Telegram for morning summary and intraday alerts
- a later web view for after-market review, browsing, and thinking
- That means the web layer does not need to replace Telegram; it should complement the notification flow with richer read-oriented views after the market session.
- The original proposal to keep web-view in memo/backlog mode before live-market validation is historical; it is no longer current implementation guidance.
- The `example/report_*.jpg` references are useful as layout and information-architecture inspiration, but the project should not copy unsupported trading-signal semantics directly.
- Useful reference patterns include market mood, strong/weak lists, category rotation, and next-watch candidates.
- `example/Cycle.jpg` should be treated as a conceptual reference for a future sector/theme rotation view, showing possible attention movement across broad market groups.
- Any rotation-cycle view should be descriptive and data-backed by accumulated report/sector/theme history, not a hard-coded prediction that money must move in a fixed order.
- Score, grade, and conviction-style displays should wait until there is enough historical data and a clear calculation rule.

### Historical Operator/Admin Program Proposal

The local `admin-gui` and separate GET-only `web-view` described as future work below have since been implemented. Retain this section as planning history; current boundaries and verification live in [AGENTS.md](../../AGENTS.md) and [surface-guide.md](surface-guide.md).

- The original proposal treated a local admin surface as future work; `admin-gui` is now implemented as an operator-only surface.
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
- Naver industry/theme pages remain the preferred domestic taxonomy source. The older KRX market-source preference is superseded: Toss 20:00 owns new/current stored market references, while existing KRX rows remain historical/recovery data only. See [data-governance.md](data-governance.md).
- Industry refresh should remain explicit and slow first (`refresh-industry <code>`), not broad automatic crawling, until source stability and rate behavior are observed.
- Store industry as the representative sector-like label in `stock_metadata`; keep theme membership as a separate many-to-many layer because one stock can belong to multiple themes.

### Historical Target-Price Progress Proposal

Stored target history/progress is now part of candidate evidence and stock detail; see [candidate-evidence.md](candidate-evidence.md). The broader display ideas below remain subject to source/date and missing-state rules.

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
- Current weekday scheduler windows are `Notify 08:20`, `Poll 08:30~16:30`, market briefings at `09:15`/`12:00`/`15:15`, `TelegramCommands 08:00~16:30`, and `TossCloseSnapshot 20:00`.
- `StockMonitor-Shutdown` is desktop-validation only and must remain absent on the always-on mini PC.
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
