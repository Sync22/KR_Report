# Project Map

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
- [docs/codex/project-map.md](/docs/codex/project-map.md)
- [docs/codex/current-work.md](/docs/codex/current-work.md)
- [docs/codex/next-phase.md](/docs/codex/next-phase.md)
- [docs/codex/module-ownership.md](/docs/codex/module-ownership.md)
- [docs/codex/decision-log.md](/docs/codex/decision-log.md)
- [docs/codex/documentation-index.md](/docs/codex/documentation-index.md)
- [docs/codex/execution-roadmap.md](/docs/codex/execution-roadmap.md)
- [docs/codex/admin-gui-plan.md](/docs/codex/admin-gui-plan.md)
- [docs/codex/surface-contract.md](/docs/codex/surface-contract.md)
- [docs/codex/data-source-policy.md](/docs/codex/data-source-policy.md)
- [docs/codex/data-rebaseline-plan.md](/docs/codex/data-rebaseline-plan.md)
- [docs/codex/plans/candidate-evidence-plan.md](/docs/codex/plans/candidate-evidence-plan.md)
- [docs/codex/contracts/candidate-evidence-contract.md](/docs/codex/contracts/candidate-evidence-contract.md)
- [docs/codex/plans/target-price-progress-plan.md](/docs/codex/plans/target-price-progress-plan.md)
- [docs/codex/plans/backtest-observation-plan.md](/docs/codex/plans/backtest-observation-plan.md)
- [docs/codex/plans/scoring-draft-plan.md](/docs/codex/plans/scoring-draft-plan.md)
- [docs/codex/plans/telegram-briefing-plan.md](/docs/codex/plans/telegram-briefing-plan.md)
- [docs/codex/krx-market-data-runbook.md](/docs/codex/krx-market-data-runbook.md)
- [docs/codex/details/krx/etf-flow-source-study.md](/docs/codex/details/krx/etf-flow-source-study.md)
- [docs/codex/details/krx/krx-api-field-validation.md](/docs/codex/details/krx/krx-api-field-validation.md)
- [docs/codex/details/krx/krx-flow-execution-stages.md](/docs/codex/details/krx/krx-flow-execution-stages.md)
- [docs/codex/details/krx/krx-flow-sample-capture-runbook.md](/docs/codex/details/krx/krx-flow-sample-capture-runbook.md)
- [docs/codex/details/krx/krx-investor-flow-source-plan.md](/docs/codex/details/krx/krx-investor-flow-source-plan.md)
- [docs/codex/details/krx/krx-investor-flow-schema.md](/docs/codex/details/krx/krx-investor-flow-schema.md)
- [docs/codex/data-quality-checklist.md](/docs/codex/data-quality-checklist.md)
- [docs/codex/mini-pc-migration-handoff.md](/docs/codex/mini-pc-migration-handoff.md)
- [docs/codex/history/mini-pc-restore-change-log-2026-05-16.md](/docs/codex/history/mini-pc-restore-change-log-2026-05-16.md)
- [docs/codex/agent-guide.md](/docs/codex/agent-guide.md)
- [docs/codex/agent-reassessment.md](/docs/codex/agent-reassessment.md)
- [docs/codex/rotation-overlay-plan.md](/docs/codex/rotation-overlay-plan.md)
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
- `docs/codex/contracts/`
- `docs/codex/details/krx/`
- `docs/codex/history/`
- `docs/codex/plans/`
- `docs/codex/weekly-sync/`

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
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/admin-gui-plan.md`
- `docs/codex/agent-guide.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/surface-contract.md`
- `docs/codex/execution-roadmap.md`

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
- `docs/codex/current-work.md`
- `docs/codex/next-phase.md`
- `docs/codex/execution-roadmap.md`
- `docs/codex/project-map.md`
- `docs/codex/documentation-index.md`
- `README.md`
- `CHANGELOG.md`
