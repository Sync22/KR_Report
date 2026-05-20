# AGENTS.md

## Scope Rule

This handoff is scoped only to the folder:

- `C:\Users\MING\Codex\02.Stock_Moniter`

Do not infer project state from sibling folders or older paths.
All judgments, next steps, and file references should come only from this folder tree.

## Project Purpose

This project is an MVP for monitoring the Naver Stock research company page for the domestic stocks tab,
collecting newly published reports during Korean market business hours, saving them locally,
building a daily per-stock summary, and sending a next-business-day morning notification for personal use.

Current functional intent:

- poll the page every 30 minutes from `08:30` to `16:30` KST on Korean business days
- detect newly seen reports
- aggregate daily mention counts by stock
- summarize target price range and dominant investment opinion
- backfill missing KRX Open API stock/ETF/index daily snapshots at `08:10` KST on Korean business days, after the officially confirmed next-business-day `08:00` KST publication window, targeting only the previous business day or earlier recent missing dates
- send the previous business day's enhanced briefing summary at `08:20` KST on the next Korean business day, after the official `08:00` KST KRX Open API publication window and the `08:10` backfill check
- backfill KRX Data Marketplace `[12009]` stock-level investor flow at `16:00` KST for stocks mentioned on the anchor report date, covering the recent 31-day window, skipping already stored rows, and pacing calls with a 1-second delay by default
- start a hidden Telegram command worker at `08:00` KST on weekdays; it checks commands every 1 minute until `16:30` and exits immediately on Korean market holidays
- keep the desktop-validation shutdown path guarded and separate; the mini PC always-on profile must not register `StockMonitor-Shutdown`

Current scheduler note:

- `StockMonitor-KrxMentionedFlowBackfill` is the narrow approved KRX Data Marketplace automatic path: anchor-day mentioned stocks only, stock-level `[12009]` only, recent 31-day window, newest dates first, default maximum 300 requests per run, no market-wide/top-ranking broad ingest. In normal live operation the anchor is the current business day; after restore or prefilled report ingestion, use the latest report-mentioned business date as the anchor and repeat until dry-run reports no remaining calls.
- `StockMonitor-KrxFlowLoginReminder` is an optional KRX investor-flow validation reminder. Keep this task disabled during normal operation unless a deliberate validation day needs an operator login reminder.

## Current State

This folder now contains a runnable Python MVP implementation.
The collector, parser, SQLite storage, Telegram notifier, CLI commands, and Windows Task Scheduler scripts exist.
The project is in live-market validation and operational hardening mode.

The main requirements anchor is:

- [stock_research_monitor_mvp.md](/c:/Users/MING/Codex/02.Stock_Moniter/stock_research_monitor_mvp.md)

## Current Structure

Known files inside this project folder:

- [AGENTS.md](/c:/Users/MING/Codex/02.Stock_Moniter/AGENTS.md)
- [stock_research_monitor_mvp.md](/c:/Users/MING/Codex/02.Stock_Moniter/stock_research_monitor_mvp.md)
- [docs/codex/project-map.md](/c:/Users/MING/Codex/02.Stock_Moniter/docs/codex/project-map.md)
- [docs/codex/current-work.md](/c:/Users/MING/Codex/02.Stock_Moniter/docs/codex/current-work.md)
- [docs/codex/decision-log.md](/c:/Users/MING/Codex/02.Stock_Moniter/docs/codex/decision-log.md)

## Important Notes

- The folder name is intentionally `02.Stock_Moniter` and currently uses that spelling.
- The project is now implemented enough for live-market validation.
- Korean text may render incorrectly if PowerShell is not reading files as UTF-8; prefer `Get-Content -Encoding UTF8` when checking docs.
- Use `docs/codex/documentation-index.md` as the canonical document map before following older planning notes. Do not use deleted/superseded documents such as `future-webview-operation-plan.md`, `p2-execution-plan.md`, or `docs/codex/archive/*` as current guidance.
- Before parser, summary, notification, admin-gui, or web-view changes, check `docs/codex/data-quality-checklist.md`.
- Treat raw/source values, parsed/storage values, aggregate values, and display values separately; missing markers such as `N/A` must not distort ranges, representative opinions, rankings, or duplicate-display decisions.
- Treat operator memos by their original user-facing intent. A DB/API/test/display foundation is not the same as intent completion; distinguish `기반 구현 완료` from `작성 의도 달성`.
- The user-facing `web-view` should be a compact daily briefing and evidence-check surface, not a raw table or validation-process viewer. Push operating details, debug tables, and full validation chains to `admin-gui`, CLI, tests, or docs.
- Public trading recommendations and scored investment decisions remain blocked: do not expose `매수 추천`, `매도 추천`, `점수`, `등급`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, or buy/sell signals. Observation curation is allowed: wording such as `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `확인 후보`, `시장 분위기`, `수급 참고`, and `과열 참고` is allowed and preferred for rough daily-use summaries.
- Treat a future `16:00`-around `오늘의 시장 분위기` Telegram briefing as a valid product axis, separate from the next-morning previous-business-day report briefing.
- Keep `admin-gui` as the operator control surface and `web-view` as the friend-facing GET-only information surface.
- The `web-view` default load must remain stored-data based. The only live reference currently allowed there is the manual current-business-day `장중 거래대금 확인` button, which fetches Naver `priceTop` as `Naver 장중 참고` without DB writes, Telegram sends, scheduler changes, or KRX snapshot replacement.
- KRX Data Marketplace automatic collection is limited to anchor-day report-mentioned stocks, stock-level `[12009]`, recent 31-day backfill. Do not broaden to market-wide/top-ranking/all-stock scheduled ingest without separate approval. For migration catch-up, anchor to the latest report-mentioned business date rather than the wall-clock date.
- For KRX Data Marketplace validation, prefer `.env` raw login checks over browser login automation. If browser work depends on the operator's real login/session state, prefer the connected Chrome extension browser over the Codex in-app browser. Use the in-app browser only for simple local UI checks or when Chrome extension control is unavailable.
- A global skill named `botasaurus-stock-monitor` may be available for anti-detect browser probes or source-validation experiments. Use it only for bounded KRX/Data Marketplace or future browser-gated source probing, not as a replacement for the main Naver/Telegram/SQLite pipeline.
- A global skill named `kronos-market-forecast` may be available for research-only forecasting experiments on stored KRX OHLCV data. Use it only for offline comparison against observation/evidence work, never for public trading recommendations, numeric public scoring, Telegram trading alerts, or production automation.
- The 2026-05-19 GitHub/tool bookmarks are approved only as local study/setup candidates except `scrcpy`, which is intentionally excluded for now. Candidates are `codegraph`, `codex-complexity-optimizer`, `QuantDinger`, and `botasaurus`, but do not assume they are currently runnable until their separate environment checks pass. Treat them as isolated local developer/research/probing tools, not production runtime dependencies, scheduler tasks, public `web-view` features, or automatic data-ingest paths.
- `codegraph` may be used for local codebase indexing/visualization and MCP-style code navigation if it stays outside production runtime behavior.
- `codex-complexity-optimizer` may be used for local source-maintenance reports and complexity review; report output must be reviewed before any code changes.
- `QuantDinger` may be installed or studied only as a research/backtest reference. It must not introduce public scoring, buy/sell recommendations, trading alerts, portfolio automation, or broker execution into this project.
- `botasaurus` remains allowed only for bounded browser-gated source probes such as KRX Data Marketplace/session validation. Do not wire Botasaurus output directly into production tables without the normal sample validation/import path.
- `codegraph` is now initialized in `C:\Users\MING\Codex\02.Stock_Moniter\.codegraph`. Treat it as a local MCP-style code navigation tool, not a runtime dependency or product feature.

## Recommended Initial Stack

- `Python`
- `Playwright`
- `SQLite`
- `Telegram Bot`
- `Windows Task Scheduler`

## Immediate Next Work

1. Continue validating live scheduled runs across market days.
2. Keep Telegram paging, intraday retry, and daily summary state behavior regression-tested.
3. Track future sector rollups and web-view ideas as backlog until the data shape is stable.
4. Keep 2027+ Korean market holiday handling on the maintenance backlog.

## Recommended Subagents

For small and obvious single-surface edits, work locally.
For non-trivial work, prefer splitting investigation, implementation, and review across the appropriate local subagents.
Close completed agents after their result is integrated so agent slots do not remain occupied.

- `backend-developer`: harden fetch -> parse -> persist -> summarize -> notify behavior without widening scope.
- `python-pro`: fix parsing, typing, and runtime code contracts in the Python modules.
- `cli-developer`: refine manual commands, scheduler wrappers, and operator-facing command behavior.
- `sql-pro`: review dedupe, aggregation, replay safety, and migration logic.
- `reviewer`: review business-day rules, delivery-state safety, and regression risk.
- `debugger`: isolate unattended-run, scheduler, or runtime-state failures.
- `test-engineer`: add focused regression tests for scheduler, Telegram, outbox, or replay-sensitive flows.
- `admin-ui-engineer`: improve `admin-gui`, operator-facing status surfaces, and the future read-only web-view boundary.
- `documentation-engineer`: reconcile AGENTS, roadmap, current-work, and admin/web-view plan docs with implementation reality.
- `market-data-engineer`: evaluate KRX/KIS/ETF/flow source fields and plan schema-safe ingest expansion.
- `web-ui-engineer`: improve the separate read-only `web-view`, archive navigation, and user-facing market/report rendering while keeping the GET-only boundary.
- `security-hardening`: review and tighten access-code gate behavior, admin/web-view separation, public-safe DTO exposure, and future external-sharing assumptions.

## CodeGraph MCP Rule

Use `codegraph` before broad text search when the task depends on quickly narrowing:

- fetch -> parse -> persist -> summarize -> notify ownership
- scheduler / CLI wrapper entry points
- `admin-gui` / `web-view` read paths and DTO boundaries
- schema or migration impact

Best-fit cases:

- source ownership is unclear
- a change spans multiple modules
- you need callers / callees / impact before editing
- you are reviewing whether a new tool, source, or experiment touches production behavior

Lower-value cases:

- a known single-file patch
- obvious copy or UI wording changes
- a tiny test fix with fully known scope

Routing guidance:

- `debugger`, `backend-developer`, `market-data-engineer`, `sql-pro`, and `reviewer` should prefer `codegraph` first when tracing cross-module behavior.
- `web-ui-engineer` and `admin-ui-engineer` may use it when route ownership or DTO fan-out is unclear.
- Always confirm the final edit against the real file contents after using `codegraph`.
