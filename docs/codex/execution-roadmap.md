# Execution Roadmap

## Purpose

This is the consolidated working roadmap for `02.Stock_Moniter`.

It combines the current implementation state, operator memos, admin GUI review, user web-view planning, and subagent feedback. Use this as the first planning reference before starting the next implementation batch.

## Current Product Shape

The current product direction is no longer "add every available data layer to the page." The priority is a compact daily-use briefing flow:

| Principle | Roadmap Impact |
| --- | --- |
| Rough usable result first | Ship readable Telegram/web summaries with clear caveats before adding more intermediate validation views. |
| Memo intent over implementation inventory | Mark an item complete only when the operator's intended user-facing outcome is met; backend scaffolding alone is partial. |
| Compressed user page | Move raw tables, operational reasoning, and debug evidence out of the shared page unless they directly explain the selected daily summary. |
| Observation curation allowed | `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `눈에 띄는`, `확인 후보`, `시장 분위기`, and `수급 참고` are allowed; public numeric scores, investment grades, and trading-call wording remain blocked. |
| Daily iteration | Use each market day's collected data to decide what is mature enough to refine. Do not wait for a perfect model before showing useful reference output. |
| Closing-market summary | Add a future `16:00`-around `오늘의 시장 분위기` briefing track, separate from the next-morning previous-day report briefing. |

| Area | Status | Notes |
| --- | --- | --- |
| Documentation structure | Canonical map fixed | `documentation-index.md` now defines which docs are authoritative and which older files are detailed references. |
| Naver research collection | Working MVP | Domestic stock research page is collected and deduped locally. |
| Data source policy | Fixed | Naver owns reports, KRX owns market reference data, and 업종/테마 are treated as a separate taxonomy layer. |
| SQLite storage | Working MVP | Reports, summaries, delivery logs, sectors, themes, category snapshots, operator controls, safe app settings, admin audit log, worker heartbeat state, fragment resume state, FK enforcement, and schema migrations exist. |
| Telegram notifications | Working MVP | Daily summary, intraday alerts, paging, stock search, memo capture, read-only status helpers, fragment resume, and filtered paging are implemented. |
| Windows Task Scheduler | Working MVP | Notify, poll, command worker, KRX daily backfill, KRX mentioned-stock flow, and hourly web-view restart tasks are registered for mini PC operation; the desktop-validation shutdown path exists but `StockMonitor-Shutdown` is intentionally absent on the mini PC. Shutdown run-now is blocked from CLI/GUI control paths. |
| Daily summary filters | Done | Low-signal one-off and no-target-price reports can be filtered from notification output. |
| Intraday paging | Done | Intraday output is limited and controlled with `다음`, `전부`, and `처음`. |
| Admin GUI | First control pass | Local dashboard exists with scheduler cards, calendar, reports, deliveries, events, sector/theme/mood cards. |
| Sector rollup | First pass done | Sector summary can be displayed from stored report data. |
| Theme rollup | First pass done | Theme membership refresh exists and theme summaries are shown in admin. |
| Market mood | First pass done | Simple market mood summary exists. |
| 사용자용 web-view | V1 closeout | Separate GET-only `web-view` command/server exists with archive, daily summary, stock/category detail, intraday API, and market reference APIs; the visible shared page is slimmed to report/category/market reading rather than operator-style diagnostics. |
| ETF / flow analytics | Raised planning priority | KRX Open API snapshots exist for price/volume/turnover, and KRX Data Marketplace screens `[12008]`, `[12009]`, `[12010]` now have screen-backed request candidates. Scoring remains deferred. |
| US market data expansion | New memo | Investigate official/semi-official US market APIs later; no implementation yet. |

## Progress Snapshot

Snapshot date: `2026-05-17`

These percentages are planning estimates, not formal release metrics. They combine local project state with reviewer, backend, and CLI subagent assessments.

## Current Completion Rebaseline

This is the current decision baseline for planning. It intentionally separates the runnable domestic MVP from future expansion items.

| Scope | Completion | Meaning |
| --- | ---: | --- |
| Current domestic MVP on the mini PC, excluding broad public sharing and US market expansion | 96-97% | Telegram, scheduler, DB, admin-gui, user web-view, KRX Open API baseline, KRX Data Marketplace read-only flow references, parser drift fixtures, read-only observation/backtest foundations, mini PC restore, access-code gate, mini-PC scheduler registration, external web-view local gate, Cloudflare provider smoke for `https://report.kr-stock.site`, latest KRX Open API row availability, and manual Telegram review sends are implemented. Remaining work is mostly live market-day observation, operator phone-readability acceptance, and watching the web-view Startup shortcut across logon/reboot. |
| Current domestic MVP, including public trading recommendation or scored investment decisions | 75-80% | Read-only observation and hidden/internal scoring-draft CLIs exist, but public numeric score, investment grade, Telegram trading alert, and buy/sell wording remain blocked until longer holdout validation is convincing. This is separate from observation-candidate recommendation. |

| Axis | Current Completion | Next Increase Condition |
| --- | ---: | --- |
| 리포트 수집/요약/Telegram | 92% | Several more real market-day briefing deliveries, parser drift fixture samples, and timeout-after-send trace review. |
| Scheduler / 운영 안정성 | 94% | Elevated/local Task Scheduler metadata is available, and elevated `verify_task_scheduler_registration.ps1` now reconfirms the six default mini-PC tasks: `StockMonitor-KrxDailyBackfill`, `StockMonitor-Notify`, `StockMonitor-Poll`, `StockMonitor-KrxMentionedFlowBackfill`, `StockMonitor-TelegramCommands`, and `StockMonitor-WebViewHourlyRestart`. The hourly restart task keeps the `127.0.0.1:8780` Cloudflare web-view target fresh; `StockMonitor-Shutdown` is absent as intended. The verifier distinguishes Task Scheduler metadata access-denied from genuinely missing task registration. Continue observing stale/missed-run and Telegram worker heartbeat behavior across more market days. |
| DB / schema / backup / verification | 97% | Keep `db-verify`, backup, restore-smoke, cleanup guard, and KRX backfill discipline green after future bulk data changes. Read-only diagnostics now check current schema without running the schema initializer when the DB already exists, reducing avoidable SQLite write-lock contention during parallel health checks. `db-restore-smoke` now records a local operation event, and `next-phase-readiness.db_safety` blocks completion when the latest backup is missing, lacks a matching successful restore-smoke, or `db-verify` has failing checks. |
| 사용자용 web-view | 93% | Direction reset is underway: the top daily briefing is now aligned with report flow, KRX index, turnover, 수급 참고, notable-stock chips, and short check points, while opinion-derived buy/sell signals are kept out of candidate/briefing reasons. The daily DTO now carries structured `market_briefing` blocks so the UI uses explicit index/turnover/flow/notable-stock/check-point fields instead of parsing display lines. The `2026-05-15` sector snapshot now uses verified Naver upjong rows for key active sectors instead of pure latest-mapping fallback, the local external-sharing gate passes value QA plus browser/mobile smoke with issue count `0`, and the Cloudflare provider smoke for `https://report.kr-stock.site` passes with issue count `0`. Remaining work is date-by-date visual review, evidence compression, and logon/reboot observation of the loopback web-view runtime. |
| admin-gui | 85% | Validate controls in live operation and refine status/log/settings UX without exposing admin externally. DB backup/verify reminders, readable recent-event summaries, and read-only recovery guidance are now visible in the operator status surface. |
| KRX / 수급 / ETF | 91% | Open API daily snapshots are current through `2026-05-15`; expand investor-flow coverage only through guarded/manual or separately approved scheduled ingest. |
| 관찰 후보 추천 / 백테스트 / 점수화 초안 | 84% | Build `오늘의 관찰 후보` ordering from stored evidence; the public `관찰` tab now has a top-2 `우선 확인` block, while reaction windows stay read-only and public numeric scores, investment grades, and trading calls remain blocked. |
| Documentation / roadmap consistency | 90% | Keep this roadmap, `current-work`, `next-phase`, source policy, and changelog synchronized whenever implementation moves. |

Current `next-phase-readiness` audit (`2026-05-17`):

| Check | Current Evidence |
| --- | --- |
| Overall practical completion | Personal always-on operation is about `97%`; external `web-view` sharing readiness is about `97%` after Cloudflare provider smoke for `https://report.kr-stock.site`; the current observation-curation closeout is about `96-97%`. Public numeric scoring and trading recommendations are separate non-goals, not blockers for `오늘의 관찰 후보`. |
| Full regression suite | Latest `2026-05-17` local run passed with `557 passed`; no code-level regression blocker is currently known. |
| Local mini-PC readiness gate | `2026-05-17 09:50 KST` local run passed with mini-PC profile and access-code required, pytest/restore-smoke skipped because they were already verified, and operator-status skipped only because the current non-elevated shell cannot read Task Scheduler metadata. |
| Market-day observation usability | `market-day-observation` now reports `next_due_check` and per-task `verify_after_at` timestamps; for `2026-05-18`, the first due check is `StockMonitor-TelegramCommands` at `08:05` KST. `verify_market_day_observation.ps1 -Date YYYY-MM-DD` now wraps operator health, scheduler registration, market-day observation, `db-verify`, and `next-phase-readiness` so the operator can rerun the closeout evidence flow from elevated local PowerShell. |
| Continuation verification | `2026-05-17 10:12 KST` checks reconfirmed the then-open blockers: operator phone readability acceptance, real `2026-05-18` market-day observation, and final external `web-view` provider/final URL setup. The provider smoke blocker was later closed at `2026-05-17 17:46 KST`; remaining blockers are phone readability acceptance, real market-day observation, and post-logon/reboot observation of the web-view Startup fallback. |
| Elevated scheduler health recheck | `2026-05-17 17:02 KST` elevated local `verify_task_scheduler_registration.ps1` and `operator-status --json --health-exit` passed. The five default mini-PC tasks are registered/enabled/`Ready` for `2026-05-18`, `operator-status.health.level=ok`, and `StockMonitor-Shutdown` remains absent. The remaining scheduler closeout item is real market-day observation after the tasks become due. |
| Cloudflare pre-provider local gate | `2026-05-17 17:11 KST` `access-code status`, `external-web-view-sharing-plan --json`, and `verify_external_web_view_readiness.ps1` reconfirmed that the only allowed tunnel target is `web-view` on `http://127.0.0.1:8780`, access-code is enabled, mini-PC profile is active, latest backup exists, value QA issue count is `0`, browser/mobile smoke issue count is `0`, `POST /api/daily/2026-05-15` returns `405`, and `/api/status` returns `404`. Provider binding and final HTTPS URL smoke were later completed for `https://report.kr-stock.site`. |
| Cloudflare provider smoke | `2026-05-17 17:46 KST` final smoke for `https://report.kr-stock.site` passed and recorded an `external-web-view/provider-smoke` success event. The unrestricted network run reported issue count `0`, `/health` `200`, unauthenticated user routes `401`, user-data write `405`, and scheduler/operator/settings control POST routes `405`; `next-phase-readiness.external_web_view_provider_smoke.ready=true`. |
| Expanded closeout wrapper | `2026-05-17 20:51 KST` elevated/local `verify_next_phase_closeout.ps1 -Date 2026-05-18` passed with operator and Task Scheduler checks included. It verified DB integrity/schema, local web-view health, operator health, five mini-PC scheduler tasks, value QA, browser/mobile smoke, external sharing plan, category/rotation/KRX baseline audits, and aggregate readiness. Remaining blockers are still non-code gates: phone-readability acceptance, first real `2026-05-18` market-day scheduled-run observation, and post-logon/reboot Startup fallback observation. |
| Closeout gate evidence | `next-phase-readiness` now exposes `completion_gates` and `external_web_view_provider_smoke`, while `external-web-view-sharing-plan --json` prints the focused read-only Cloudflare/Tailscale sequence before provider setup. The final provider command is `external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json`; it records a non-secret provider-smoke operation event only after zero issues against a non-loopback HTTPS provider origin with no path/query/fragment, giving the external sharing blocker a durable closeout signal. After Cloudflare Tunnel is configured, prefer `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL` because it validates the provider origin, reruns local external readiness, records provider smoke success, and reruns readiness in one operator command. |
| Full regression suite | `2026-05-17` local run passed with `557 passed` after the closeout wrapper was expanded to cover reaction distribution, web-view QA/browser smoke, external sharing plan, category snapshot status/plan, rotation mapping audit, and KRX baseline analysis directly. |
| Latest report date | `2026-05-15`, 51 reports, 28 summary stocks |
| Observation reaction | Internal-only `observation_reaction` covers `2026-01-02`~`2026-05-15` with 493 `mention_count >= 2` candidates; completed windows are D+1 486/493, D+5 427/493, D+10 344/493, and D+20 296/493. It is not public-surface-ready for numeric scoring and does not produce public numeric scoring or trading-recommendation output. |
| Candidate evidence | Recent 5 report dates are review-ready `5/5`; QA issue dates `0` |
| Closing-market briefing | Preview-ready `5/5`; manual Telegram review sends recorded `3/3`; schedule gate remains closed until `market_briefing_phone_review_accepted=true` is set after operator readability acceptance |
| KRX latest-day baseline | `2026-05-15` daily Open API rows are now stored; `krx-baseline-analysis` reports `missing_daily_snapshots=0` |
| Market holiday coverage | Built-in/configured coverage currently runs through `2026-12-31`; no renewal blocker is active yet, but `next-phase-readiness` will surface one from October 2026 if future KRX closure dates are not configured. |
| Completion blockers | Real market-day scheduler observation, operator acceptance of the recorded Telegram phone review messages, and post-logon/reboot observation that the `web-view` Startup shortcut keeps the Cloudflare target available |

The manual Telegram phone review send gate has an explicit safe path: run `market-briefing-readiness --recent-report-dates 5` and use the printed `market-briefing --date YYYY-MM-DD --limit 5 --send` commands only for dates that are preview-ready and public-safe. On `2026-05-17`, manual sends were recorded for `2026-05-15`, `2026-05-14`, and `2026-05-13`, populating the `telegram_market_briefing` delivery log with `source=manual`; the remaining step is operator readability acceptance through `operator-settings set market_briefing_phone_review_accepted true --reason phone_readability_accepted --confirm` before scheduling.

| Area | Progress | Current Meaning | Next Increase Condition |
| --- | ---: | --- | --- |
| MVP pipeline | 88% | Fetch, parse, dedupe, persist, summarize, notify, and admin status paths exist with recent operational hardening. `operator-status` now includes live operation-event evidence, labels not-yet-due same-day components as `pending`, and distinguishes KRX latest-date `attention(incomplete_snapshot)` from scheduler failure. `StockMonitor-KrxMentionedFlowBackfill` now skips unresolved KRX metadata codes before Data Marketplace requests instead of failing the whole run. | More live market-day validation, especially the next `StockMonitor-KrxMentionedFlowBackfill` execution after unresolved-code hardening and Telegram delivery traces. |
| Naver collection and SQLite storage | 86% | Core report collection is working; report dedupe is DB unique-index plus `INSERT OR IGNORE`, schema changes now have a migration runner, DOM/API parser fixture coverage includes mobile URL/query canonicalization, intraday queueing is regression-tested against same-`source_id` duplicates, and live `inspect-page` snapshots can be saved as parser drift fixtures. Saved live fixtures now cover `2026-05-14` and `2026-05-15`, both parsing 20 API reports. | Add more saved fixtures from real market pages. |
| DB/schema maturity | 99% | Main operational tables exist with fragment state, worker heartbeat, safe settings, admin audit log, FK enforcement, `PRAGMA user_version`, `schema_migrations`, stronger report uniqueness, KRX snapshot tables, additive investor-flow schema v4 tables, category snapshot schema v5, investor-flow/category quality checks in `db-verify`, deep DB verification, backup/restore-smoke commands, db-verify and restore-smoke evidence in readiness, KRX cleanup/VACUUM dry-run/confirm protection, and KRX missing-date backfill guardrails. | Do not enable broad investor-flow scheduled ingest until separate approval; keep the narrow `[12009]` mentioned-stock 31-day lane bounded. |
| Summary correctness | 83% | Target price range, opinion, count filters, current price, sector/theme, stock-code-first grouping, and filtered paging are usable. Same-broker latest opinion and tied-opinion priority are now explicitly regression-tested. | Continue live-data validation for parser drift and code-missing edge cases. |
| Telegram operations | 94% | Daily summary, temporary default morning briefing format for `scheduled-notify`, intraday alerts, paging, stock search, replay-safe memo/check side effects, fragment resume, early/late notify guard, production/test delivery separation, worker heartbeat, TelegramCommands restart recovery, timeout-after-send fragment trace detail, and atomic JSON control-state saves are implemented and checklist-tracked. Timeout trace is visible in JSON and text operator status. | Validate worker heartbeat, timeout trace usefulness, and Telegram briefing readability across several unattended market days. |
| Telegram command worker | 93% | Hidden 1-minute loop, command parsing, paging, search, replay-safe memo flows, atomic paging/selection state saves, heartbeat, stale-state reporting, and guarded scheduler restart recovery are working. | Validate restart behavior during real Task Scheduler operation. |
| Windows scheduler operation | 96% | Notify, Poll, TelegramCommands, KRX daily backfill, and KRX mentioned-stock flow backfill are registered/enabled on the mini PC. KRX login reminder has business-day/no-run/late-run guards and stays disabled/unregistered for normal operation. Scheduler health is classified, never-run future tasks are not over-reported as failures, Shutdown run-now is blocked, and elevated/local metadata confirmed the five default mini-PC tasks are available and waiting for their first `2026-05-18` scheduled run. The registration verifier now reports Task Scheduler metadata access-denied separately from real missing tasks. `StockMonitor-Shutdown` is absent as required for always-on mini-PC operation. | Keep validating stale thresholds and the next real run behavior over several unattended market days. |
| Admin GUI | 86% | Local dashboard and first control surface exist; loopback guard, backend no-run date validation including holiday/env/past-date rejection, first KRX market-data tables, safe-settings audit controls, operation profile editing, TelegramCommands restart recovery, DB backup/verify reminders, readable recent-event summaries, and read-only safest-next-step recovery guidance are in place. | Validate controls over live scheduler use and refine UX copy. |
| Admin control operations | 79% | Run-now, enable/disable, no-run calendar, events, operation profile, TelegramCommands restart recovery, and Shutdown run-now/restart guard exist. | Add broader recovery actions only after live validation. |
| Operator diagnostics | 93% | `operator-status`, operation events, explain-date, health exit, worker heartbeat, scheduler classification, never-run scheduled-task handling, same-day live evidence fallback, pending live components, KRX Open API `empty`/`partial`/`incomplete_snapshot` attention warnings, optional KRX login reminder warning separation, category snapshot refreshability warnings, market-holiday coverage expiry warnings, and read-only schema-current checks are implemented. Elevated/local scheduler metadata has been verified, and the `2026-05-15` KRX incomplete-snapshot warning was cleared by the backed-up successful latest-day fill. Non-elevated scheduler metadata `access_denied` is treated as a permission check, not registration repair evidence. | Tune thresholds with elevated scheduler metadata and live logs. |
| Safety and observability | 86% | Health is machine-checkable, key scheduler/worker/DB integrity states are guarded, safe settings changes are auditable, DB verify/backup/restore-smoke/cleanup guard commands exist, KRX backfill requires explicit backup confirmation, KRX Open API calls that return 0 stored rows no longer look like successful data loads, and limited GUI recovery exists. | Observe live scheduler behavior and add only proven recovery actions. |
| Documentation consistency | 100% | Canonical document map, KRX runbook, admin plan, agent guide, rotation overlay plan, memo status cleanup, and current-stage 100% definition are recorded. | Keep new planning changes in canonical docs instead of adding scattered `.md` files. |
| Mini PC operation/sharing readiness | 98% local / 97% external | Windows scheduler, local paths, health checks, KRX scheduler tasks, required scheduler script checks, explicit scheduler Python path guidance, required project/canonical handoff file checks, `.env.example` archive inclusion, user web-view/rotation asset checks, non-secret Telegram/KRX environment presence checks, before-copy/post-restore checks, read-only `mini-pc-preflight` CLI, bundled `setup_mini_pc_environment.ps1`, mini-PC-specific `register_mini_pc_scheduler_tasks.ps1` wrapper that skips `StockMonitor-Shutdown`, source-desktop cutover helper, `verify_mini_pc_readiness.ps1`, scheduler registration verifier, external-share-only `verify_external_web_view_readiness.ps1`, focused read-only `external-web-view-sharing-plan --json`, post-provider `verify_cloudflare_web_view_tunnel.ps1`, migration archive integrity checks, separate admin/web access sessions, web-view loopback-by-default host guard, HTTPS-proxy `Secure` access-cookie behavior, stronger final-URL `external-web-view-smoke` admin/control-route checks, current-user `StockMonitor-WebView.lnk` Startup fallback, migration handoff, Docker deferral, access-code preflight, and Cloudflare/Tailscale exposure boundaries are documented. Actual mini-PC restore, `.env` creation, access-code enablement, scheduler registration, local external-sharing gate verification, Cloudflare provider smoke for `https://report.kr-stock.site`, domain purchase, and manual Telegram review sends are complete. | Real market-day scheduled-run observation, operator phone-readability acceptance, and logon/reboot observation of the web-view Startup fallback remain. |
| Sector/theme data | 99% | Sector rollup, explicit/batch Naver industry refresh, first Naver theme refresh, display-level duplicate cleanup, category master, dated category membership snapshot tables/CLI, per-category snapshot lookup, disabled-category hiding, cache-to-snapshot promotion, dated/fallback status inspection/filtering/counts, next-action guard, read-only snapshot planning, per-date missing snapshot type output, source-date capture guard, catalog source/refreshability display in text and JSON, current Naver upjong catalog discovery with existing-display-match flags, single upjong-code dry-run validation with next catalog-add command output, verified-source-only sector refreshability checks, batch dry-run previews, request-delay controls, `--confirm` protection for real batch refresh, and DB coverage reporting are available. On `2026-05-15`, 8 verified `source=naver_industry` rows were added separately from existing `naver_quote` labels and refreshed into a dated sector snapshot; `db-verify` no longer warns `sector_catalog_not_refreshable`. | Continue source-date snapshots for older fallback dates only when needed; do not relabel or overwrite existing `naver_quote` rows. |
| 사용자용 웹뷰 완성도 | 92% | Boundaries and APIs are strong, and the visible page has started moving back toward the attached-image style daily briefing. The top `오늘 읽을 요약` block now mirrors Telegram market-briefing axes through structured `market_briefing` fields instead of leading with unstable category summaries, opinion-derived buy/sell signals, or JS-parsed display text. `2026-05-15` now has a dated sector snapshot for key verified upjong rows, `web-view-value-qa` still reports 0 issues, and `web-view-browser-smoke` now verifies desktop/mobile rendering, observation-tab clickability, stock search, no major horizontal overflow, data-route write blocking, and `/api/status` absence. | Continue compressing selected-stock evidence and category/rotation sections, then rerun date-by-date value QA and browser smoke after visible changes. |
| Web-view API readiness | 97% | Archive, daily, stock detail, category detail, category trend, market, intraday, flow-trend, and ETF-trend DTO/APIs exist; archive APIs expose category mapping state and category snapshot/fallback counts for operator/debug use, while the visible archive UI keeps only simple date/report filtering. Daily DTO includes exact-date `krx_context`, recent `krx_recent_flow` with actual `reference_date`/`exact_date_available`, structured `market_briefing`, read-only `krx_investor_flow`, category contract, and public contract metadata; stock detail includes read-only investor-flow rows with stored-sample/no-live-fetch/no-scoring metadata, and still excludes admin/operator internals. `2026-05-08` category snapshots are populated, and fallback dates are inspectable through CLI/API rather than friend-facing filters. | Populate more dated category snapshots and keep public-safe regression tests active. |
| ETF/flow data | 100% | First source study is documented; KRX P1/P2 specs are parsed, daily stock/ETF/index snapshots are stored/queryable through `2026-05-15`, and the stored 18-month Open API target window is complete through that latest snapshot date. KRX Data Marketplace investor-flow request candidates are identified, `[12008]`/`[12009]`/`[12010]` dry-run CLI exists without DB writes, login reminder CLI exists, `krx-flow-candidates` previews leadership candidates, saved sample normalization/scaffold/status/validation/compare/import-preview/import paths exist, first visible-grid import set is stored, two business dates (`2026-05-08`, `2026-05-07`) have raw/visible-grid parity validation, schema contract and `db-verify` quality checks exist, investor-flow parser/schema v4 paths are tested, stored investor-flow rows cover through `2026-05-12`, and Stage 5 read-only trend display exists. | Keep only the approved narrow automatic `[12009]` anchor-date mentioned-stock 31-day 보강 path active; broad `[12008]`/`[12010]` or all-stock scheduled ingest requires separate approval. |
| ETF/flow product readiness | 91% | Display direction and source separation are documented; KRX stock/ETF/index snapshots can be shown as read-only reference cards, investor-flow dry-run plumbing exists, `[12009]` product scope is narrowed to leadership candidates, candidate preview output exists, sample manifest validation with expected investor coverage, capture-set and candidate-driven scaffold generation, capture checklist output, sample coverage status, batch validation, batch normalized artifact output, DB import preview, guarded manual import, first visible-grid import set, raw-network sample capture for two dates, visible-grid/raw parity gate for two dates, GET-only web-view investor-flow reference DTO/UI, stored flow rows through `2026-05-12`, stored-sample flow trend display, and `krx-baseline-analysis` source-lane comparison exist. Broad scheduled ingest remains disabled; the narrow `[12009]` mentioned-stock 보강 path is the only approved automatic lane. | Continue 18-month OpenAPI baseline; do not broaden Data Marketplace into whole-market stock flow without separate approval. |
| Backtest observation readiness | 92% | BO-1~BO-7 exists for `mention_count >= 2` candidates: exact-horizon `1/5/10/20영업일` reactions, target gap/progress, stored-window max progress, first target-hit D+ days, same-date flow, turnover, foreign net-buy top inclusion, public-safe API, first `관찰` tab table, and initial multi-date QA with target-progress caution labels. `next-phase-readiness.observation_reaction` now surfaces the full stored summary baseline `2026-01-02`~`2026-05-15`: 493 candidates, D+1 486/493, D+5 427/493, D+10 344/493, D+20 296/493. | Continue reading completed reaction windows only; do not treat missing D+20 as bad evidence. |
| Scoring draft readiness | 98% | [scoring-draft-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/plans/scoring-draft-plan.md) exists as a draft-only path. SD-1 feature coverage, SD-2 reaction distribution, SD-3 feature comparison, SD-4 internal-only weight draft, and SD-5 hidden internal prototype CLI outputs exist. SD-5 now supports separate training/apply ranges, validated feature pruning, non-overlapping holdout validation, and rolling holdout sweep. Latest validation suggests internal observation value in `mention_count=2` and foreign net-buy top inclusion, while `mention_count=4+` is not automatically stronger. No public numeric score, grade, trading recommendation, Telegram trading alert, or public decision wording is implemented. | Interpret only completed reaction windows; recent D+20 holdouts stay unavailable until enough future KRX prices exist. |
| US market data expansion | 3% | Operator memo exists to investigate US market APIs later. | Compare official/semi-official sources, cost, rate limits, and redistribution limits. |

KRX investor-flow execution should now follow [krx-flow-execution-stages.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-flow-execution-stages.md).
Use stage numbers as the execution boundary; Stage 6 first design exists, but broad scheduled KRX Data Marketplace ingest remains disabled until separate approval. The narrow `[12009]` anchor-date mentioned-stock backfill lane is the only approved automatic exception.

P2 category/ETF execution is now summarized in this roadmap and [next-phase.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/next-phase.md).
The first P2 implementation pass is complete: schema v5 category snapshots, category catalog/refresh CLI, snapshot-aware web-view category DTOs, `GET /api/etf-trend`, and Telegram read-only status helpers exist.

Data source ownership and display naming are fixed in [data-source-policy.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-source-policy.md).
Use `업종`, `테마`, and `카테고리` in user-facing Korean copy; keep KRX labels for market reference data, not for the current category taxonomy.

Current broad estimate:

| Layer | Progress | Interpretation |
| --- | ---: | --- |
| Current domestic MVP aggregate | 96-97% | Includes the completed mini-PC restore path, access-code enablement, scheduler registration, local external-sharing gate, Cloudflare provider smoke for the read-only web-view URL, Telegram/admin/web-view/KRX/backtest-observation foundations, hidden/internal scoring-draft CLIs, and strengthened parser/dedupe/scoring guardrail regression coverage. Excludes broad public sharing, US market expansion, and public-facing scoring. |
| Current domestic MVP with public scoring/recommendation expectation | 75-80% | Public score, grade, recommendation, Telegram candidate alert, and buy/sell wording remain blocked. Internal observation and hidden scoring-draft commands exist, but holdout stability is not enough for public use. |
| Personal Telegram MVP | 92% | Usable for live validation with fragment resume, filtered paging, briefing format, early/late notify guard, production/test separation, worker heartbeat checklist, and timeout trace in place. |
| Local operator console | 82% | Useful now; safe settings and operation profile are editable in `admin-gui`, audit logging exists, and TelegramCommands restart recovery is available. |
| 사용자용 웹뷰 | 93% | Separate GET-only shell and broad DTO/API coverage exist, display-value QA passes, browser/mobile smoke passes, the local external-sharing gate is ready, and the Cloudflare provider smoke for `https://report.kr-stock.site` passes. The remaining gap is continued visible screen quality review and logon/reboot observation of the local web-view runtime. |
| Data expansion layer | 90% | Stock/ETF/index Open API baseline is current through `2026-05-15` and investor-flow read-only plumbing exists. The remaining gap is separately approved policy for any broader Data Marketplace lane. |

## 2026-05-09 100% Target Board

`100%` means the current stage is decision-complete, not that all future analytics are finished.

| Track | From | Target | Done definition |
| --- | ---: | ---: | --- |
| Personal Telegram MVP | 84% | 88% | Fragment resume, production/test delivery separation, and worker heartbeat checks are explicitly tracked. |
| Scheduler / operation stability | 86% | 90% | Notify/Poll/TelegramCommands/Shutdown contracts and check order are documented. |
| Admin GUI | 66% | 82% | Safe settings, audit log, operation profile behavior, and first TelegramCommands recovery control are implemented through DB/CLI/admin-gui. |
| 사용자용 web-view | 80% | 94-96% | GET-only/read-only boundary, selection-state UX, missing-state policy, archive/mobile polish, selected-date KRX context, recent KRX flow, and public-safe DTO tests are fixed as the V1 closeout scope. |
| Data expansion layer | 47% | 86% | KRX/ETF/flow and sector/theme snapshot immediate/deferred items are separated; recent March-to-May KRX price/turnover backfill guard exists, KRX Data Marketplace `[12008]/[12009]/[12010]` dry-run commands are ready, and login reminder CLI is implemented for live validation. |
| Mini PC / external sharing readiness | 66% | 98% local / 97% external | Docker is deferred; preflight, bundled venv/install/readiness bootstrap, mini-PC scheduler wrapper with shutdown skipped, readiness check runner, scheduler registration verifier, external web-view readiness gate with value QA and browser/mobile smoke, final-URL smoke checks for admin root/control routes/operator JSON leaks, migration archive packaging with SHA256 sidecar, archive verification, explicit scheduler Python path guidance, separate admin/web access sessions, web-view loopback guard, HTTPS-proxy `Secure` access-cookie behavior, post-provider Cloudflare wrapper, current-user web-view Startup shortcut fallback, and Cloudflare/Tailscale boundaries are in place. Actual mini PC restore, access-code enablement, scheduler registration, domain purchase, local external-sharing readiness, provider binding, and final shared-URL smoke for `https://report.kr-stock.site` now pass. |
| Documentation consistency | 75% | 100% | `current-work`, this roadmap, `surface-contract`, and mini PC handoff no longer conflict on current state. |

Documentation consolidation result:

| Area | Canonical document |
| --- | --- |
| Document routing | [documentation-index.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/documentation-index.md) |
| KRX/ETF/flow | [krx-market-data-runbook.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/krx-market-data-runbook.md) |
| Admin GUI | [admin-gui-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/admin-gui-plan.md) |
| Agent usage | [agent-guide.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/agent-guide.md) |
| 순환매 SVG overlay | [rotation-overlay-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/rotation-overlay-plan.md) |

Current-stage 100% excludes broad public sharing and US market expansion. The mini-PC restore itself is complete, and Cloudflare provider smoke for the read-only `web-view` has passed; the remaining mini-PC work is real market-day observation, operator phone-readability acceptance for the recorded Telegram review sends, and logon/reboot observation of the local web-view runtime.

Today-priority items:

| Priority | Item | Decision |
| --- | --- | --- |
| P0 | Documentation consistency | Must be completed before more implementation. |
| P0 | Scheduler / Telegram / live-validation gates | Must remain visible as operating checks. |
| P0 | `web-view` read-only boundary | Must stay fixed before any Cloudflare sharing. |
| P0 | Data-quality rules | Must be checked before parser, summary, Telegram, admin-gui, or web-view changes. |
| P0 | KRX Data Marketplace login check | Prefer `.env` raw login smoke-check via `krx-flow-login-check`; Chrome session is fallback/debug only. |
| Done / optional | KRX Data Marketplace session reminder CLI/scheduler | `krx-flow-login-reminder` sends a Telegram reminder about 5 minutes before planned flow work, skips on business-day/no-run/late-run guards, and `StockMonitor-KrxFlowLoginReminder` is registered separately from collection. Normal operation now uses the narrow `StockMonitor-KrxMentionedFlowBackfill` path, so keep the reminder task disabled unless a manual validation day needs it. |
| Done | Safe settings + audit model | DB/CLI and first admin-gui controls are implemented for low-risk settings. |
| Done | Operation profile | `desktop-validation`, `mini-pc`, and `manual-only` behavior is implemented and audited through safe settings; the mini PC is set to `mini-pc`. |
| Done / provider-smoked | Cloudflare Tunnel preparation | Domain purchase, local validation, access-code gate, provider binding, and final shared-URL smoke for `https://report.kr-stock.site` are done. Keep the provider pointed only to `web-view`; never expose `admin-gui`. |
| Done / P2-watch | Theme snapshot / ETF read-only expansion | Schema/CLI/API first pass is implemented; scheduled KRX Data Marketplace ingest remains design-only. |
| Deferred | Scoring, recommendations, flow-based interest alerts | Defer until enough source-backed history exists. |

Top risks:

1. Future holiday years still require manual maintenance until an external holiday source or yearly update workflow is added. `operator-status` now shows the built-in/configured holiday coverage end date and warns near default coverage expiry.
2. Scheduler metadata is now observable in elevated/local checks, but stale thresholds are conservative and still need tuning after several real market days.
3. `admin-gui` is control-capable; loopback enforcement exists, and only the separate GET-only `web-view` may be considered for future external sharing.
4. Telegram response timeout after an actual send can still duplicate a sent chat message. Fragment failure detail now includes `message_hash` and `ambiguous_send`, but this is audit visibility rather than full duplicate prevention.
5. ETF/flow can improve interpretation, but scoring before enough history would create false confidence.

## Operator Memo Status

| Memo / Idea | Status | Planning Note |
| --- | --- | --- |
| Sector graph and sector rollup | [O] | `web-view` `국장 관찰 요약` now renders sector/theme breadth as graph-like bars with report count, active stock count, selected-day share, and category drilldown. Historical fallback taxonomy remains labeled data debt. |
| Market mood snapshot | [O] | `web-view` has one-line comments and a sentence-style `시장 분위기`; `market-briefing`/`market-briefing-readiness` provide the Telegram-style preview/manual review loop. Task Scheduler registration remains gated by operator phone-readability acceptance. |
| Theme 505 / domestic theme grouping | [O] | `refresh-theme` first pass stores theme memberships. |
| Exclude single-report / no-target-price output | [O] | Notification filtering has been handled as an output policy. |
| Local admin program | [O] | Basic local admin surface exists. |
| N100 mini PC migration | [O] / watch | Restore, `.env` creation, access-code enablement, scheduler registration, local readiness gates, and Cloudflare provider smoke are complete on the mini PC. The `web-view` Startup fallback is configured and locally healthy; continue real market-day observation and record `web-view-startup-fallback-check --record-success --json` after logon/reboot. |
| Admin/shared page split | [O] | Separate GET-only `web-view` first pass exists and does not expose admin status/control APIs. |
| External access candidates | [O] / watch | Keep the candidate set narrow: Tailscale for owner-only remote operation if still needed, Cloudflare Tunnel for friend-facing read-only `web-view` sharing. Cloudflare provider smoke for `https://report.kr-stock.site` passes; keep access-code/allow-list controls enabled and keep `admin-gui` private. |
| Theme v2 / dated theme history | [O] / watch | Stored theme rollups are now surfaced in the same market-width bars and category drilldown as sectors. Broader theme catalog/history coverage remains a data-quality watch item, not a missing V1 surface. |
| Rotation / flow tracking foundation | [O] | The `순환매` tab connects image aliases, report category evidence, stock candidates, ETF candidates, and missing information in user-facing cards without broad ingest or trading-call wording. |
| 순환매 SVG overlay | [O] / watch | Overlay, active aliases, evidence-backed highlights, and separated stock/ETF reference slots are visible. Continue optional alias/ETF coverage expansion through audits. |
| ETF tracking | [O] | Source study, KRX intake templates, snapshot tables, manual ingest, stored query paths, admin display, and `web-view` ETF trend exist; keep ETF data separate from company reports. |
| KRX historical snapshots | [O] | Prefer recent stock/ETF/index daily snapshot backfill over old report backfill. `2024-11-08` through `2026-05-15` are stored for daily stock/ETF/index endpoints. Use for trend/reference context only, not scoring. |
| Candidate evidence / next-day candidates | [O] / watch | The computed DTO/API and visible `관찰` tab expose non-numeric `observation_priority`, `왜 눈에 띄는지`, `부족한 정보`, and a top-2 `우선 확인` shortlist. Continue market-day review, but public numeric scoring is a non-goal rather than a blocker. |
| Backtest observation / report reaction | [O] / watch | [backtest-observation-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/plans/backtest-observation-plan.md) defines the read-only path. BO-1~BO-7 calculations/API/UI/initial QA exist; broader QA continues. |
| Scoring draft | [△] | [scoring-draft-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/plans/scoring-draft-plan.md) records a draft-only path. SD-1~SD-5 audit/draft/prototype CLIs exist, including train/apply separation, feature pruning, holdout validation, and rolling holdout sweep; public numeric scoring, investment grades, trading recommendations, and Telegram trading alerts remain blocked. |
| US market API expansion | [ ] | New memo captured; investigate later after domestic operating base and mini PC path are stable. |
| 2026-05-19 GitHub/tool bookmarks | [△] | `scrcpy` is excluded. `QuantDinger` remains environment-blocked until Docker is available. `botasaurus` is import-verified and a browser probe loaded Naver/KRX pages, but the current Naver Playwright/API path and KRX raw login/request path both tested cleaner, so Botasaurus remains a session/source-probe fallback. `codegraph` is locally installed and indexed 54 Python files, useful for impact review. `codex-complexity-optimizer` is locally installed as a report-only scanner; its first `src` scan flags `analysis/backtest_observation.py` and `cli.py` as the main refactor-review areas. None of these are production runtime dependencies, scheduler jobs, public `web-view` features, broker/trading automation, or broad ingest paths. |
| One-line market commentary practice | [O] | Stored-data `장초반`/`점심`/`장 마감 전` one-line drafts are visible in `web-view` and available through Telegram `/한줄`, without scheduler registration, live fetch, score, grade, or trading-decision wording. |
| Time-slot market mood card | [O] / watch | The `시황 예시` photo reference now has a real stored-data/manual-review card in `web-view` and `market-briefing-readiness`. It shows title/headline, index, notable stocks, core points, check points, and source gaps without live fetch, public scoring, recommendation, production integration, scheduler registration, or broad ingest. On the main PC it is preview-ready but still blocked from scheduling by manual Telegram review `0/3` and KRX latest snapshot fallback after `2026-05-14`. |
| Operator photo/reference intake | [O] | Telegram `/사진` stores operator images in `data/operator_photo_inbox/` with sidecar metadata for later implementation review. It does not upload or expose them through `web-view`. |
| Operator memo surface reflection | [O] | The 2026-05-18 partial memos now reach real surfaces: one-line comments appear in `web-view` and Telegram `/한줄`, Telegram `/사진` stores operator images in the local inbox, and periodic data needs appear in `web-view` market tab plus `operator-status`. |
| Periodic data needs audit | [O] | `periodic-data-needs-audit` shows that report rows and KRX Open API daily index/stock/ETF snapshots cover most market-background needs, `[12009]` remains limited to report-mentioned 31-day windows, and `[12008]`/`[12010]` automation remains blocked; real-time KOSPI/sidecar detection is a separate source/rate-limit review item. |
| Holiday / manual no-run management | [O] / watch | Calendar control and explain-date exist. Admin/CLI no-run add paths reject market holidays, env no-run dates, and past dates so DB overrides stay meaningful. |
| Quiet background operation | [△] | Scheduler, hidden worker, heartbeat, and health output exist; live threshold tuning remains. |

## Key Decision: Build Order

The next phase should not start with more visual cards or speculative analytics. The implementation is now useful enough that the next risk is operational correctness.

Recommended build order from the current state:

1. Keep live-operation validation running and review fragment/worker/scheduler evidence after each market day.
2. Continue bounded KRX missing-date backfill only after `db-verify` and `db-backup`, using `--confirm --i-backed-up`.
3. Polish the existing GET-only user `web-view`: access-gate planning and public display labels.
4. Add theme v2 history model for better rotation context.
5. Draft KRX Data Marketplace Stage 6 broad scheduled-ingest design; do not enable broader `[12008]`/`[12010]` or all-stock scheduled ingest without separate approval.
6. Run SD-5 holdout sweep only on mature reaction windows before any public scoring discussion.
7. Add rotation analytics and actual scoring later, only after enough source-backed history exists and after a separate approval.

## Security Posture Adjustment

Expected users are limited to the owner and a small number of trusted external viewers. Security should stay lightweight, but the control boundary still matters.

Recommended posture:

| Surface | Exposure | Required Guard |
| --- | --- | --- |
| `admin-gui` | Local machine or private remote access only | Control buttons, scheduler actions, shutdown policy, and settings stay here. |
| shared `web-view` | Small trusted audience | Read-only pages only; no scheduler, shutdown, token, or settings controls. |
| public internet | Avoid by default | If needed later, use a private tunnel/VPN or simple access gate before adding features. |

Practical rule: do not spend effort on enterprise-grade auth yet, but never expose POST/control endpoints through the shared page.

External access candidates are intentionally limited for now:

| Candidate | Intended use | Status |
| --- | --- | --- |
| Tailscale | Owner-only remote access to the mini PC and local services. | Planning candidate; useful for personal remote operation, but less convenient for friends because they need onboarding. |
| Cloudflare Tunnel | Friend-facing URL candidate for the read-only `web-view` only. | Provider smoke passed for `https://report.kr-stock.site`; keep it mapped only to `127.0.0.1:8780` and do not share `admin-gui`. |

Avoid direct router port forwarding for this project unless a later security review explicitly changes the posture.

The detailed boundary is fixed in [surface-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/surface-contract.md):
`admin-gui` is the operator control surface, while `web-view` is a separate shared read-only information surface.

## Phase 0: Operating Contract Freeze

Why this matters: older docs and early notes still contain historical times such as `07:00`, `08:00~15:00`, and `08:00~16:00`. The current operating contract is:

| Task | Current Contract |
| --- | --- |
| `StockMonitor-KrxDailyBackfill` | `08:10` KST on Korean business days, after the officially confirmed next-business-day `08:00` KRX Open API publication window; fills stock/ETF/index snapshots for the previous business day or earlier recent missing dates |
| `StockMonitor-Notify` | `08:20` KST on Korean business days; sends the previous-business-day briefing after the `08:10` KRX Open API fill attempt |
| `StockMonitor-Poll` | every 30 minutes from `08:30` to `16:30` KST on Korean business days |
| `StockMonitor-KrxMentionedFlowBackfill` | `16:00` KST on Korean business days; fills recent 31-day `[12009]` stock investor flow for stocks mentioned in that day's reports, newest dates first, default 300-call cap |
| `StockMonitor-KrxFlowLoginReminder` | Optional `16:45` KST validation reminder; currently disabled unless a manual KRX flow validation day needs it |
| `StockMonitor-TelegramCommands` | hidden worker from `08:00` to `16:30` KST on Korean business days |
| `StockMonitor-WebViewHourlyRestart` | hourly from `00:05` KST; restarts only the read-only loopback `web-view` target on `127.0.0.1:8780` |
| `StockMonitor-Shutdown` | `17:10` KST during desktop live validation, guarded by business-day logic |

Work items:

- Reconcile old operating-time references in docs, scripts, README, and GUI labels.
- Confirm scheduler triggers match the documented contract. Current elevated mini-PC verification should confirm the six default tasks are registered/enabled, including the `08:10` KRX Open API daily fill and hourly web-view restart.
- Define catch-up policy for missed daily summary delivery.
- Define exact meaning of `RUN_SUPPRESSED_DATES` versus market holidays.
- Keep the operation profile names stable: `desktop-validation`, `mini-pc`, and `manual-only`.

Done criteria:

- A future session can read one document and understand the current schedule without guessing.
- GUI, CLI, docs, and scheduler output use the same terms.

## Phase 1: Correctness And Delivery Hardening

Priority work:

| Priority | Item | Reason |
| --- | --- | --- |
| Done | Daily summary split-send fragment resume | Fragment-level send state exists and resumes unsent fragments. |
| Done | Notify time-window guard | Production scheduled notify sends only in the `08:00~08:30` window unless `--allow-late` is explicit. |
| Done | Stock-code-first summary grouping | Daily and intraday grouping prefer stock code where available. |
| Done | Separate scheduled/manual delivery labels | Manual tests use `telegram_test`; production scheduled sends use `telegram`. |
| Done / P2-watch | Telegram control state durability | Command paging and pending selections are still stored in JSON, but saves now use temp-file plus atomic replace to avoid partially written state after interruption. `/메모` and `/체크 로그인` side effects remain update-id replay-safe. SQLite-backed state can wait until real restart evidence says JSON is not enough. |

Candidate storage additions:

| Table | Purpose |
| --- | --- |
| `daily_summary_delivery_runs` | One row per business date and delivery attempt. |
| `daily_summary_delivery_fragments` | One row per Telegram fragment, with sent/skipped/error status. |

## Phase 2: Admin Safety And Observability

Priority work:

| Priority | Item | Reason |
| --- | --- | --- |
| Done | Loopback-only admin guard | Control-capable admin refuses non-loopback binding unless explicitly allowed. |
| Done | Server-side no-run date validation | Market holidays, env no-run dates, and past dates are rejected as redundant or ineffective DB no-run dates. |
| Done | Scheduler status classification | Access denied, disabled, missing, failed, running, stale, and unavailable states are distinct. |
| Done | `operator-status --json --health-exit` | Scheduler/admin automation can fail fast when core health is bad. |
| Done | `operator-control explain-date` | A date explains whether it is runnable and why. |
| Done | Telegram worker heartbeat | Admin/operator status shows whether command polling is alive. |
| Done | Telegram loop restart control | TelegramCommands restart recovery is available through CLI/admin-gui and remains the only broad restart action. |
| Done | Operation profile and shutdown policy | `mini-pc` disables scheduled shutdown behavior and `StockMonitor-Shutdown` is not registered on the mini PC. |
| Done | Migration/backup reminders | `operator-status` JSON/text and `admin-gui` show latest backup presence plus db-verify/db-backup reminders before risky DB/KRX work. |
| Done | Recent event readability | `operator-status` now adds `detail_display` summaries and `admin-gui` uses them so KRX, flow, scheduler, notify, and admin failure rows read as operator actions instead of raw key/value strings. |
| Done / P1-watch | Safe recovery guidance | `operator-status` now exposes `recovery_actions`, and `admin-gui` shows them as read-only safest-next-step guidance. New write/restart controls remain blocked except TelegramCommands restart until real live evidence proves a safe rollback path. |

Admin GUI should answer three questions first:

1. Is the system supposed to run today?
2. Did the scheduled work actually run?
3. If not, what is the most likely cause and safest recovery action?

## Phase 3: Safe Settings Model

Do not expose raw `.env` editing through the admin GUI.

DB/CLI first pass status: implemented. Schema migration v3 adds `app_settings` and `admin_audit_log`, `operator-settings list/set/history` provides the CLI interface, and admin-gui exposes guarded controls for the approved safe settings.

Recommended configuration layers:

| Layer | Contents | Editable From GUI |
| --- | --- | --- |
| `.env` | Telegram token, chat id, bootstrap paths, sensitive or restart-required values | No |
| `app_settings` | Safe operational knobs | Yes, through validated DB settings and guarded admin-gui controls |
| `worker_state` | Runtime heartbeat and status | Read-only or controlled actions only |

First safe knobs:

| Setting | Purpose |
| --- | --- |
| `daily_summary_min_mention_count` | Hide low-signal daily summary entries. |
| `daily_summary_require_target_price` | Hide entries with no target price. |
| `notification_default_limit` | Default visible item count for Telegram paging. |
| `operation_profile` | Switch between desktop validation, mini PC, and manual-only behavior. |

Required support tables:

| Table | Purpose |
| --- | --- |
| `app_settings` | Validated operator settings. Implemented in migration v3. |
| `admin_audit_log` | Who changed what, when, and from which interface. Implemented in migration v3. |
| `worker_state` | Last heartbeat and current status for poll, notify, and command workers. |

Excluded from GUI settings:

- Telegram bot token editing.
- Telegram chat id editing.
- Raw shell command editing.
- One-click shutdown.
- One-click disable all scheduled tasks.

## Phase 4: User Web-View V1

The user web-view is separate from the control-capable admin GUI.
This means a separate page, separate HTTP handler/router, separate GET-only API contract, and separate read-only DTOs.
It must not be implemented as a read-only mode on `admin-gui`.

Current command:

```powershell
python -m stock_monitor web-view --host 127.0.0.1 --port 8780
```

Current screens:

| Screen | Contents |
| --- | --- |
| Date archive | Daily report count, delivery state, sector/theme highlights, and previous/next navigation. |
| Daily review | Stock-level summary with target price range, opinion, current price, sector/theme, and stock detail drilldown. |
| Sector/theme rollup | Category report counts, representative stocks, category detail, and recent category trend. |
| Market mood | Report-flow tilt, target-price availability, active sectors, and observation-candidate hints without trading-action wording. |
| Intraday batches | Same-date intraday collection and delivery history. |
| KRX reference | Selected-date KOSPI/KOSDAQ/ETF/index cards and recent KRX flow reference. |

Current API shape is read-only:

- `GET /health`
- `GET /api/archive?limit=20`
- `GET /api/daily/YYYY-MM-DD`
- `GET /api/daily/YYYY-MM-DD/stocks/STOCK_CODE`
- `GET /api/intraday?date=YYYY-MM-DD`
- `GET /api/category?date=YYYY-MM-DD&type=sector|theme&name=...`
- `GET /api/category-trend?type=sector|theme&name=...`
- `GET /api/etf-trend?date=YYYY-MM-DD&limit=5`
- `GET /api/market`

No POST/control endpoints in the shared web-view.

Do not reuse `build_operator_status_snapshot()` as the user API.
That snapshot is an operator/admin model containing scheduler, worker, and health internals.
Build and maintain date-bound read-only query models for archive/review pages instead.

## Phase 5: Category V2

Current sector/theme refresh is useful, but the model should mature before theme trend judgment is trusted.

Current additions:

| Data | Purpose |
| --- | --- |
| `category_master` | Stable display taxonomy for sectors/themes before web-view analytics depend on source-specific codes. |
| `category_membership_snapshots` | Dated sector/theme membership history to avoid silently mixing future mappings into past dates. |
| Theme coverage report | Shows which reported stocks have no theme mapping. |

Operational direction:

- Keep `refresh-theme <theme_code>` as a debug tool, with optional `--snapshot-date`.
- Keep `refresh-industry <industry_code>` as an explicit, slow operator-triggered refresh before any broad scheduled crawl, with optional `--snapshot-date`.
- Use `category-catalog` and `refresh-themes --enabled --snapshot-date SOURCE_DATE` only when the source date is the actual capture date. Do not label current theme membership as a historical source-date snapshot.
- Treat theme membership as slowly changing reference data.

## Phase 6: ETF And Flow Data

ETF and flow should be planned as separate data layers. Priority has been raised from distant backlog to source-study and read-only display planning because they are useful for interpreting sector/theme rotation.

ETF candidate fields:

- ETF code and name.
- Underlying index.
- Management company.
- Constituents or top holdings if source is stable.
- Daily NAV/price/volume if source is stable.

Flow candidate fields:

- Stock code.
- Trade date.
- Individual, foreign, institution net buy/sell.
- Volume and turnover.

Current flow source priority:

| Priority | Source | Use |
| --- | --- | --- |
| P0 | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Stock-level investor flow for leadership candidates. |
| P1 | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide investor background. |
| P1 | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Top net-buy names by investor category. |
| Fallback | KIS Developers | Use only if KRX Data Marketplace cannot be made stable enough. |

Deferred analytics:

- Report day plus one-day flow check.
- Third-day interest alert.
- Sector/theme rotation view.
- Target price achievement rate and days-to-target.
- Scoring or grade systems.

Do not implement scoring until enough historical data exists to validate whether it adds signal.

Near-term display direction:

| View | Useful First Output |
| --- | --- |
| ETF reference | ETF code/name, category/theme/index, price change, volume, and linked representative stocks. |
| Flow snapshot | Stock-level foreign/institution/individual net buy and volume for leadership candidates. |
| Sector/theme rotation | Report activity plus flow direction shown side by side, without producing a score yet. |
| Daily review | "Reports appeared here, money appears to be moving here" shown as separated evidence layers. |

## Current Implementation Batch Status

| Step | Task | Status | Output |
| --- | --- | --- | --- |
| 1 | Reconcile operating contract references | Done | README/current-work/roadmap now describe the current operating contract. |
| 2 | Add explain-date | Done | `operator-control explain-date YYYY-MM-DD [--json]` explains runnable/skip causes. |
| 3 | Add operator-status health exit and Telegram worker heartbeat | Done | `worker_state`, `worker_states.telegram_command_loop`, and `--health-exit` exist. |
| 4 | Improve scheduler status classification | Done | Scheduler tasks now expose `status_class` and `status_reason`. |
| 5 | Live-validate fragment-resume daily delivery | In progress | Code/tests exist; real long-summary retry behavior still needs live observation. |
| 6 | Start ETF/flow source study | Stage 4 done | [etf-flow-source-study.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/etf-flow-source-study.md) fixes KRX-first and no-scoring boundaries. [krx-api-field-validation.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-api-field-validation.md) tracks Open API field capture. [krx-investor-flow-source-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-investor-flow-source-plan.md) fixes Data Marketplace `[12008]`, `[12009]`, `[12010]` as screen-backed request candidates. `krx-flow-login-check` verifies raw `.env` login without DB writes, and Chrome login reminder remains fallback/debug only. |
| 7 | Document deferred Telegram admin-open idea | Done | `/관리자페이지 열기` is recorded as deferred; safer read-only Telegram status commands are implemented. |
| 8 | Operational hardening review fixes | Done | Shutdown run-now guard, notify early guard, filtered paging, intraday 0-count fix, and backend no-run validation are implemented. |
| 9 | DB hardening first pass | Done | `foreign_keys=ON`, schema version marker, report unique indexes, `INSERT OR IGNORE`, fragment resume cleanup, and worker error clearing exist. |
| 10 | Draft mini PC migration handoff | Done | [mini-pc-migration-handoff.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/mini-pc-migration-handoff.md) captures zip/restore/verify/new-Codex briefing. |
| 11 | Capture US market API expansion memo | Backlog | `data/operator_memos.md` records future investigation of official/semi-official US market APIs. |
| 12 | Web-view V1.1 intraday and KRX display pass | Done | `GET /api/intraday?date=YYYY-MM-DD` exposes public-safe intraday batch history, and the user page now splits KRX KOSPI/KOSDAQ/ETF/index reference cards. |
| 13 | Web-view same-date KRX stock reference pass | Done | `GET /api/daily/YYYY-MM-DD` stock rows can include same-business-date KRX close price, change percent, turnover, and market without scoring. |
| 14 | Web-view stock detail route pass | Done | `GET /api/daily/YYYY-MM-DD/stocks/STOCK_CODE` exposes same-date report detail and KRX reference data without admin/operator internals. |
| 15 | Web-view archive navigation pass | Done | The user page supports `?date=YYYY-MM-DD`, previous/next archive buttons, active date chips, and URL state updates without adding write/control APIs. |
| 16 | Web-view category detail pass | Done | `GET /api/category?date=YYYY-MM-DD&type=sector|theme&name=...` exposes category stock lists with same-date KRX references; sector/theme rows are clickable in the user page. |
| 17 | Web-view category trend pass | Done | `GET /api/category-trend?type=sector|theme&name=...` exposes recent category report/stock counts and the page shows category flow tables without scoring. |
| 18 | Web-view V1 closeout planning | Done | Selection-state UX, missing-state display, archive/mobile polish, GET-only tests, and public-safe DTO checks are fixed as the V1 closeout gate. |
| 19 | External sharing boundary planning | Done | Docker is deferred; Cloudflare Tunnel may target only `web-view` on localhost; Tailscale remains owner-management candidate; `admin-gui`, `.env`, DB, Telegram, scheduler controls remain private. |
| 20 | Safe settings/audit DB+CLI pass | Done | Migration v3 adds `app_settings` and `admin_audit_log`; `operator-settings list/set/history` validates and audits safe setting changes; effective settings feed daily summary filters, Telegram paging limit, and `operator-status`. |
| 21 | Safe settings admin-gui first pass | Done | `admin-gui` shows safe settings, allows guarded edits for daily summary min mentions, target-price-required, default display limit, and operation profile, and shows recent audit logs. |
| 22 | DB backup/verify first pass | Done | `db-verify` checks integrity/schema/counts/dedupe/orphan fragments. `db-backup` creates consistent SQLite backups with integrity check. `db-backup-prune` previews/deletes old backups with confirmation. |
| 23 | KRX cleanup guard first pass | Done | `db-cleanup --dry-run --retention-days 183` previews expired KRX snapshot rows, protects `reports` and delivery state, and requires `--confirm` before deleting affected KRX rows. |
| 24 | KRX missing-date backfill guard first pass | 18-month Open API target complete through latest stored date | `krx-backfill-missing daily --lookback-days 90 --dry-run` finds missing business-date/endpoint pairs from newest business dates first and reuses `krx-fetch-snapshot` for actual bounded fills. Real manual rebaseline calls require `--confirm --i-backed-up`, default to 5 business dates, sleep between endpoint requests, and reject larger batches without `--allow-large-batch`. `scheduled-krx-daily-backfill` is the narrow automatic path: it runs at `08:10` after the officially confirmed next-business-day `08:00` publication window, targets the previous business day or earlier recent missing dates, and does not fetch same-day rows. Stock/ETF/index snapshots currently cover `2024-11-08` through `2026-05-15`; investor-flow rows currently cover through `2026-05-12` after guarded manual backfill. |
| 25 | Restore smoke and profile/recovery pass | Done | `db-restore-smoke` verifies backup copies without touching production DB. `operation_profile` now controls scheduled wrappers, and TelegramCommands restart is available through CLI/admin-gui. |

Do not start ETF/flow scoring before source quality and enough history exist. ETF/flow source study can start after the operational health outputs behave correctly in live runs.

Next practical sequence, updated after the 18-month Open API baseline completion:

1. Keep daily KRX Open API backfill healthy through the `08:10` scheduler path after the official next-business-day `08:00` publication window, and re-run `krx-baseline-analysis` after cleanup or large data changes.
2. Review SD-5 holdout output only where D+N reaction rows are available; keep public scoring blocked.
3. Polish the friend-facing `web-view` observation tab so it shows evidence reasons, not a score.
4. Reduce category snapshot fallback by filling source-date 업종/테마 snapshots where practical.
5. Add 순환매 overlay calibration only after the JSON coordinate map proves useful.

Operational live validation remains important, but it is now treated as a parallel observation track rather than the next feature-build order.

## Testing Gates

| Area | Gate |
| --- | --- |
| Operating contract | Scheduler listing and docs agree on Notify, Poll, Commands, Shutdown times. |
| Admin boundary | Admin server rejects non-loopback bind unless explicitly allowed. |
| No-run dates | Market holiday, manual exclusion, and normal business day each return a clear reason. |
| Scheduler status | Disabled, missing, access denied, and healthy states are distinguishable in CLI and GUI. |
| Daily delivery | Fragmented Telegram delivery can resume without duplicate already-sent fragments. |
| Summary grouping | Same stock code aggregates even when names vary slightly. |
| Worker health | Telegram command worker heartbeat is visible and stale state is reported. |
| DB hardening | `reports` dedupe unique indexes, `foreign_keys=ON`, and schema version marker are covered by tests. |
| Safe settings | `operator-settings` validates value ranges, requires confirmation/reason, records audit rows, suppresses duplicate no-op audit spam, and feeds runtime effective settings. |
| DB backup/cleanup | `db-verify` passes before risky DB work, `db-backup` creates an integrity-checked backup, backup prune requires preview/confirmation, and `db-cleanup` only targets KRX snapshot tables with confirmation for actual deletion. |
| KRX API rate safety | Backfill must be reviewed with `--dry-run`, real calls require `--confirm`, default batches are capped at 5 business dates, endpoint requests sleep by default, and larger batches require explicit `--allow-large-batch`. |
| Web-view V1 | Shared web-view exposes read-only data only. |
| Data quality | Raw/source, parsed/storage, aggregate, and display contracts stay documented and preserved across Telegram, admin-gui, and web-view; missing markers are excluded from aggregate values but remain visible in detail views as missing states. |
| External sharing | Cloudflare Tunnel targets only `127.0.0.1:8780` or the chosen `web-view` port; `admin-gui`, DB, `.env`, Telegram, and scheduler/control endpoints are not exposed. |
| Mini PC migration | Docker is not required for the current Windows N100 path; direct Python + Task Scheduler remains the target unless the host changes to Linux/VPS. |


