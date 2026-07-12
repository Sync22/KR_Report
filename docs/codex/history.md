# History

Historical restore, web-view hardening, and documentation reorganization records. Not current operating guidance.

## Included sections
- Mini PC Restore Change Log - 2026-05-16
- Web-View Five-Tab Hardening (2026-05-29)
- Web-View Stored Evidence Hardening Handoff
- Docs Role Reorganization Review - 2026-05-17
- Docs Role Reorganization Review Prompt

<!-- Merged from: docs/codex/history.md -->
## Mini PC Restore Change Log - 2026-05-16

## Purpose

This document records the changes made on the mini PC from the first restore conversation through the current state.

Use it when syncing the original desktop/source-managed copy with the mini PC work.
It intentionally does not include `.env` values, Telegram tokens, KRX keys, access-code values, cookies, or other secrets.

## Scope

Project folder only:

```text
{PROJECT_ROOT}
```

Source-of-truth documents read before work:

1. `AGENTS.md`
2. `docs/codex/documentation-index.md`
3. `docs/codex/mini-pc-runbook.md`
4. `docs/codex/market-data-runbook.md`
5. `docs/codex/operating-guide.md`
6. `docs/codex/operating-guide.md`
7. `docs/codex/research-notes.md`

No sibling project or older external project folder was used as guidance.

## High-Level Result

The mini PC restore reached operational readiness:

- Migration archive integrity was verified.
- Mini PC Python venv, editable install, dev dependencies, and Playwright Chromium were prepared.
- `.env` was created manually by the operator on the mini PC.
- A post-restore DB backup was created and checked.
- Mini PC scheduler tasks were registered without the desktop shutdown task.
- Scheduler registration and `operator-status --health-exit` passed after fixes.
- External `web-view` readiness checks passed after access-code was enabled.
- Narrow KRX `[12009]` mentioned-stock investor-flow catch-up was completed for the latest report anchor date.
- Documentation was updated to reflect anchor-date flow policy, mini PC operating boundaries, and next data-expansion direction.

## Operating State After Restore

Current report baseline in `data/stock_monitor.db`:

| Item | Value |
| --- | --- |
| First report business date | `2026-01-02` |
| Latest report business date | `2026-05-15` |
| Stored report business days | `90` |
| Total reports | `4,046` |
| Distinct report-mentioned stock codes | `715` |
| Latest date report count | `2026-05-15`: `51` reports |
| Latest date mentioned stock count | `2026-05-15`: `28` stocks |

Mini PC registered scheduler tasks:

- `StockMonitor-KrxDailyBackfill`
- `StockMonitor-Notify`
- `StockMonitor-Poll`
- `StockMonitor-KrxMentionedFlowBackfill`
- `StockMonitor-TelegramCommands`

Intentionally not registered for always-on mini PC operation:

- `StockMonitor-Shutdown`

Optional validation-only task remains disabled/not required by default:

- `StockMonitor-KrxFlowLoginReminder`

External sharing state:

- Access-code gate is enabled.
- `admin-gui` must remain local/private.
- Only `web-view` is a future external-sharing candidate.
- Candidate tunnel target remains `{LOCAL_WEB_VIEW_TARGET}`.

## Runtime and Setup Work

The initial generic `python` command resolved to the WindowsApps alias, so setup used the bundled Python runtime path available on this host.

`scripts/setup_mini_pc_environment.ps1` was run to prepare:

- `.venv`
- upgraded `pip`
- editable project install with dev dependencies
- Playwright Chromium

Network-dependent install steps required approval/escalation on the mini PC.

The operator manually wrote `.env`.
Secret values were not displayed or copied into chat.

Post-restore backup:

```text
data\backups\stock_monitor_{timestamp}_{tag}.db
```

Additional backup before latest mentioned-flow catch-up:

```text
data\backups\stock_monitor_{timestamp}_{tag}.db
```

## Code Changes

### PowerShell Setup And Scheduler Fixes

Updated:

- `scripts/setup_mini_pc_environment.ps1`
- `scripts/register_mini_pc_scheduler_tasks.ps1`
- `scripts/verify_task_scheduler_registration.ps1`

Reasons:

- Fixed PowerShell splatting so arguments are passed by name instead of being interpreted positionally.
- Replaced fragile nested command checks based on `$LASTEXITCODE` with `$?` where appropriate.
- Fixed a PowerShell parse issue around task-name interpolation in `verify_task_scheduler_registration.ps1`.

Result:

- Mini PC setup can run through venv/install/readiness bootstrap.
- Mini PC scheduler registration can call the underlying registration/verification scripts correctly.
- Scheduler verification handles the expected task names and confirms `StockMonitor-Shutdown` is absent by default.

### Operator Status Health Logic

Updated:

- `src/stock_monitor/cli.py`
- `tests/test_operator_status.py`

Reason:

- `operator-status --health-exit` incorrectly treated the optional `StockMonitor-KrxFlowLoginReminder` task as a warning/failure when it was intentionally unavailable or not registered during normal mini PC operation.

Behavior after change:

- Optional KRX flow login reminder statuses such as `disabled`, `missing`, and `unavailable` are not health warnings in the normal profile.
- `access_denied` remains a warning because it means Task Scheduler metadata could not be verified.

### Web-View Investor Flow Display

Updated:

- `src/stock_monitor/cli.py`
- `tests/test_web_view.py`

Reason:

- The user wanted simple recent-period 수급 visibility, not recommendation/scoring behavior.

Behavior after change:

- Selected-stock investor-flow period view defaults to the recent `31` stored rows instead of `20`.
- The stock detail section shows a period summary chip for:
  - date range
  - trading-day count
  - individual signed total
  - foreign signed total
  - institution signed total
- Copy is framed as stored `수급 참고`, not as buy/sell or score output.

### Mentioned-Stock Flow Default Delay

Verified existing defaults:

- `src/stock_monitor/cli.py`: `scheduled-krx-mentioned-flow-backfill --sleep-seconds` default is `1.0`.
- `scripts/register_task_scheduler_tasks.ps1`: `KrxMentionedFlowBackfillSleepSeconds = 1`.
- `scripts/run_scheduled_krx_mentioned_flow_backfill.ps1`: `SleepSeconds = 1`.

Documentation was updated so future operators keep the 1-second request pacing by default.

## Test And Verification Results

Verified successfully:

- Migration archive verification with `scripts/verify_migration_archive.ps1`.
- `db-backup --tag post-restore`.
- `scripts/verify_mini_pc_readiness.ps1 -SkipPytest` from elevated context.
- `scripts/verify_task_scheduler_registration.ps1`.
- `operator-status --health-exit`.
- `scripts/verify_external_web_view_readiness.ps1`.

Test results after code changes:

| Test command | Result |
| --- | --- |
| `pytest tests/test_scheduler_scripts.py -q` | `14 passed` |
| `pytest tests/test_operator_status.py -q` | `28 passed` |
| `pytest tests/test_web_view.py -q` | `28 passed` |
| `pytest -q` | `483 passed` |

Known acceptable warning:

- KRX Open API latest daily snapshot was stored through `2026-05-14`.
- `2026-05-15` was newer than the latest stored KRX snapshot at the time and was treated as a normal latest-day pending warning, not a migration failure.

## Data Work On Mini PC

### Latest Anchor Mentioned-Stock Flow Catch-Up

Latest report anchor date:

```text
2026-05-15
```

Initial dry-run found:

- `28` mentioned stocks
- `25` resolvable stocks
- unresolved stock codes: `351020`, `233990`, `052960`
- `21` Korean business dates in the `2026-04-15` through `2026-05-15` window
- default call cap required multiple runs

Live catch-up was run in bounded batches using:

- `[12009]` only
- anchor-date report-mentioned stocks only
- recent 31-day lookback
- `--max-calls 300`
- `--sleep-seconds 1`
- repeat until dry-run planned calls reached `0`

Post-catch-up state:

- `stock_investor_flow_daily` rows: `16,484`
- latest anchor dry-run planned calls: `0`
- investor-flow quality issues: `0`
- example checked stocks had `21` business dates and `273` investor rows each for the anchor window.

This remains the narrow approved flow lane.
It is not approval for broad all-stock ingest, `[12008]` market flow automation, or `[12010]` net-buy ranking automation.

## Documentation Changes

Updated:

- `AGENTS.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/mini-pc-runbook.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/research-notes.md`
- `docs/codex/documentation-index.md`

Main policy changes:

- Replaced overly narrow same-day wording with anchor-date wording for `[12009]` mentioned-stock flow.
- Normal live operation anchor is the current business day.
- Restore/prefilled report operation should use the latest report-mentioned business date or each stock's latest mentioned date as the catch-up anchor.
- The catch-up command should be repeated until dry-run returns `planned_call_count: 0`.
- Request pacing for this lane is default `--sleep-seconds 1`.
- Broad Data Marketplace ingest remains forbidden.

Domestic observation direction added:

- Use report-style information architecture only.
- Do not copy public `BUY`, `SELL`, score, grade, entry, exit, target-profit, or conviction wording.
- Allowed public framing includes `국장 관찰 요약`, `확인 후보`, `과열 참고`, and `수급 참고`.
- Needed future data/features include price position, short returns, volume/turnover expansion, 5/10/20/31-day investor-flow totals, flow persistence/turning point, report intensity, broker breadth, target-price revisions, sector/theme breadth, and post-report reaction windows.

## Files To Sync Back To Source-Managed Desktop Copy

Source/code/test/docs changes worth syncing:

- `AGENTS.md`
- `docs/codex/documentation-index.md`
- `docs/codex/mini-pc-runbook.md`
- `docs/codex/operating-guide.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/operating-guide.md`
- `docs/codex/research-notes.md`
- `docs/codex/history.md`
- `scripts/setup_mini_pc_environment.ps1`
- `scripts/register_mini_pc_scheduler_tasks.ps1`
- `scripts/verify_task_scheduler_registration.ps1`
- `src/stock_monitor/cli.py`
- `tests/test_scheduler_scripts.py`
- `tests/test_operator_status.py`
- `tests/test_web_view.py`

Runtime/data files to treat separately:

- `data/stock_monitor.db`
- `data/backups/*.db`
- `data/access_code.json`
- `.env`
- `.venv`
- `.pytest_cache`
- `Stock_Moniter_migration_*.zip`
- `Stock_Moniter_migration_*.zip.sha256`

Do not sync or commit secrets:

- `.env`
- Telegram token
- Telegram chat id if considered private
- KRX auth key
- KRX Data Marketplace ID/password
- access-code material

If the original desktop/source-managed copy should also carry the mini PC DB state, copy `data/stock_monitor.db` deliberately as a data snapshot, not as a normal source-code change.

## Current Recommended Next Prompt

Use this for the next operator/Codex session:

```text
{PROJECT_ROOT} only.
Read AGENTS.md and docs/codex/documentation-index.md first, then follow only the canonical docs.

Current mini PC state:
- Restore and setup are complete.
- Scheduler tasks are registered for mini PC always-on operation without StockMonitor-Shutdown.
- operator-status --health-exit passed.
- access-code is enabled.
- External sharing candidate is web-view only; admin-gui must not be exposed.
- Reports cover 2026-01-02 through 2026-05-15.
- Latest report date 2026-05-15 has 51 reports and 28 mentioned stocks.

Today's data rule:
- KRX Data Marketplace automatic collection is limited to [12009] stock-level investor flow.
- Use only report-mentioned stocks.
- For normal live operation, anchor on the current business day's mentioned stocks.
- For prefilled/restored history, use each stock's latest report-mentioned date, or process anchor dates from latest backward as bounded batches.
- For each anchor, fill the recent 31-day window only.
- Keep --max-calls 300 and the default 1-second request delay.
- Repeat dry-run/live cycles until planned_call_count is 0.
- Do not run broad ingest, all-stock ingest, [12008] automation, [12010] automation, recommendation, score, grade, or buy/sell output.

First checks:
1. Run operator-status --json --health-exit.
2. Run scripts/verify_task_scheduler_registration.ps1 with the venv Python path.
3. Check latest report-mentioned date and run scheduled-krx-mentioned-flow-backfill --dry-run --json.
4. If planned_call_count > 0, create a DB backup, run the live [12009] catch-up with default 1-second delay, then repeat dry-run until planned_call_count is 0.
5. Keep any new observation summary public-safe: use 수급 참고 / 확인 후보 wording only.
```

## Source Management Notes

This mini PC work includes both source changes and local operational state.

Recommended sync order for the original desktop/source-managed copy:

1. Apply source, script, test, and docs files listed above.
2. Run the focused tests first:
   - `pytest tests/test_scheduler_scripts.py -q`
   - `pytest tests/test_operator_status.py -q`
   - `pytest tests/test_web_view.py -q`
3. Run full `pytest -q`.
4. Decide separately whether to copy `data/stock_monitor.db`.
5. Do not copy `.env` or `data/access_code.json` through source management.
6. If scheduler tasks are re-registered on any host, confirm whether that host is the mini PC or the old desktop before disabling/enabling tasks.

## 2026-05-16 Follow-Up Goal Check

Additional mini PC checks after the restore session:

- `operator-status --json --health-exit` passed with health `ok`.
- `verify_task_scheduler_registration.ps1` passed when using the same PythonExe string registered in Task Scheduler: `.\.venv\Scripts\python.exe`.
- The registered scheduler actions use the relative venv Python path and each wrapper changes to the project root before invoking Python.
- `access-code status` reported enabled.
- `mini-pc-preflight --require-access-code --require-backup --require-env` passed with only the expected external tunnel/provider manual-verification warning.
- `db-verify` passed with integrity `ok`, schema `5/5`, no foreign key violations, no duplicate source ids, no KRX investor-flow quality issues, and `stock_investor_flow_daily` at `16,484` rows.
- The latest report date remains `2026-05-15`, with `51` reports and `28` mentioned stocks.

Latest-date `[12009]` dry-run:

- Anchor date: `2026-05-15`
- Lookback window: `2026-04-15` through `2026-05-15`
- Mentioned stocks: `28`
- Resolvable stocks: `25`
- Unresolved stocks: `351020`, `233990`, `052960`
- `raw_call_count`: `0`
- `planned_call_count`: `0`

Full restored-history per-stock latest-anchor audit:

- Policy audited: each stock's latest report-mentioned date, then that stock's recent 31 calendar-day `[12009]` window, skipping already stored rows.
- Distinct report-mentioned stock codes: `715`
- Resolvable stock codes: `705`
- Unresolved stock codes: `10`
- Unresolved codes: `052960`, `233990`, `351020`, `000001`, `0126Z0`, `0120G0`, `0008Z0`, `0004V0`, `0007C0`, `0009K0`
- Expected resolvable stock/business-date pairs: `14,857`
- Missing stock/date calls: `13,940`
- Estimated 300-call batches: `47`
- Anchor dates with missing calls: `83`

Decision:

- No live historical per-stock catch-up was run in this follow-up check.
- The existing scheduled command is date-anchor based. It is safe for the latest anchor date and normal daily operation, but blindly iterating every historical report date can collect extra stock/date pairs outside a stock's latest-anchor 31-day window.
- Before running the full January-May catch-up, add or use an exact per-stock latest-anchor mode, or run explicit bounded stock/date windows that preserve the latest-anchor rule.

Additional source updates from this follow-up:

- `src/stock_monitor/cli.py`: mini-PC preflight and baseline-analysis wording now says `anchor-date` rather than stale `same-day` for the approved `[12009]` automatic lane.
- `tests/test_cli_commands.py`: updated the matching assertion.
- `docs/codex/market-data-runbook.md`: clarified that full restored-history catch-up must respect each stock's latest-anchor 31-day window.
- `docs/codex/operating-guide.md`, `docs/codex/data-governance.md`, `docs/codex/operating-guide.md`, and `docs/codex/architecture-guide.md`: stale same-day wording was aligned to anchor-date wording where it referred to the approved `[12009]` lane.

## 2026-05-16 Per-Stock Latest-Anchor Flow Catch-Up

The full restored-history `[12009]` catch-up was completed on the mini PC with the exact per-stock latest-anchor rule:

- Report range audited: `2026-01-02` through `2026-05-15`.
- Policy: each stock's latest report-mentioned date, then that stock's recent 31 calendar-day window filtered to Korean business days.
- Starting missing stock/date calls: `13,940`.
- Backup before live execution: `data\backups\stock_monitor_{timestamp}_{tag}.db`.
- Completed live coverage: `13,940` stock/date calls and `181,220` stored `[12009]` rows.
- Batch shape: `46` full 300-call batches plus one final 140-call batch. One 300-call batch hit the shell timeout after DB writes; it left no completion event, but follow-up dry-run showed those rows were present and the next run resumed from the remaining stock/date calls.
- Final dry-run: `raw_call_count=0`, `planned_call_count=0`, `anchor_dates_with_missing_count=0`.
- Final `db-verify`: integrity `ok`, schema `5/5`, no pending migrations, no foreign key violations, no duplicate source ids, no investor-flow quality issues.
- Final `stock_investor_flow_daily` row count: `197,704`.
- Unresolved stock codes skipped before KRX requests: `052960`, `233990`, `351020`, `000001`, `0126Z0`, `0120G0`, `0008Z0`, `0004V0`, `0007C0`, `0009K0`.

Source updates made for this catch-up:

- `src/stock_monitor/cli.py`: added `krx-mentioned-flow-latest-anchor-backfill` for restored-history catch-up that plans by each stock's latest report anchor.
- `tests/test_cli_commands.py`: added regression coverage for the latest-anchor dry-run and live safety flags.
- `docs/codex/market-data-runbook.md`: added the exact restored-history command sequence.


<!-- Merged from: docs/codex/history/web-view-five-tab-hardening-2026-05-29.md -->
## Web-View Five-Tab Hardening (2026-05-29)

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


<!-- Merged from: docs/codex/history/web-view-stored-evidence-hardening-2026-05-27.md -->
## Web-View Stored Evidence Hardening Handoff

## Intent

This dev-branch change hardens the friend-facing `web-view` around stored-data observation.

The goal is not to add live trading, broker integration, real-time quote logic, or a new data-ingest lane. The goal is to make the existing stored Naver report, KRX reference, and investor-flow evidence easier to read, safer to expose, and easier to review before an operation-side sync.

## Main Changes

- Main `web-view` candidate cards emphasize stored evidence rather than internal diagnostic signals.
- Public candidate labels stay limited to visible `why_notable` and `missing_information`.
- Internal candidate signals remain available through operator/readiness output.
- Public `/api/candidate-evidence` rows are thinner than internal readiness rows.
- Public candidate rows no longer expose `quality_flags`, `evidence_notes`, `opinion_summary`, `report_summary.broker_count`, `report_summary.broker_display`, or `report_summary.dominant_opinion`.
- Candidate card display no longer shows broker breadth or dominant opinion wording in the public card body.
- Mobile candidate cards keep the current three-box evidence structure, but compress inner metric grids for narrow viewports.
- `국장 시장 분위기` remains an interpretation block.
- `시장 참고` remains a stored-data evidence block.
- Broker/OpenAPI work remains future lab/staging only.

## Boundaries

No changes are intended for:

- production DB contents
- schema or migrations
- Telegram send behavior
- scheduler registration or timing
- `admin-gui` control behavior
- broker/OpenAPI integration
- external tunnel/provider setup

## Public-Safe Rules

This change keeps:

- `web-view` GET-only
- no public numeric score
- no public recommendation
- no buy/sell signal wording
- no broker/execution hookup
- no scheduler/admin/env/DB-path exposure

## Validation

Passed locally on `2026-05-27`:

- `python -m pytest tests\test_web_view.py -q` -> `49 passed`
- `python -m pytest tests\test_cli_commands.py -q` -> `277 passed`
- `python -m stock_monitor candidate-evidence-readiness --recent-report-dates 5 --stock-limit 20 --json`
  - `review_ready_count=5`
  - `qa_issue_date_count=0`
  - `qa_warning_date_count=0`
  - visible/public label counts and internal signal counts are separated
- `python -m stock_monitor web-view-browser-smoke --date latest --json`
  - `issue_count=0`
  - desktop/tablet/large-mobile/mobile horizontal overflow all `0`
  - `POST /api/daily/2026-05-15` returned `405`
  - `/api/status` returned `404`
- `python -m stock_monitor web-view-value-qa --recent-business-days 5 --stock-limit 20 --json`
  - `issue_count=0`
  - `warning_count=5`

Known warning:

- `web-view-value-qa` reports `krx_snapshot_not_yet_available` for dates newer than latest stored KRX snapshot `2026-05-19`.
- This is expected under the stored-data model and does not imply live intraday support.

## Operation-Side Review Checklist

After pulling this dev branch, review:

1. Latest report-date main page in a browser.
2. Candidate cards on desktop and mobile.
3. Public `/api/candidate-evidence` payload shape.
4. `candidate-evidence-readiness` visible/internal counts.
5. Whether top-2 candidate duplication is still useful in daily use.

Do not connect this branch to broker/OpenAPI, Telegram scheduling, admin controls, or production DB write paths without a separate reviewed goal.

## Notes For Merge Review

- `data/` runtime, sample, log, backup, and local intake files are intentionally not part of this handoff.
- `AGENTS.md` is already dirty in the dev worktree and appears as a broader project-instruction rewrite. Review it separately from the web-view hardening code if merging to another branch.


<!-- Merged from: docs/DOCS_ROLE_REORG_REVIEW_2026-05-17.md -->
## Docs Role Reorganization Review - 2026-05-17

## Context

This review was prepared on the mini PC.

The mini PC is the current live-operation machine. Weekly source sync artifacts that should be reviewed on the main PC belong under:

- `handoff/mini_pc_changes/`

This document started as a proposal. The operator approved a limited reorganization on `2026-05-17`, and only non-canonical detail/history/plan/contract documents were moved.

Canonical documents such as `operating-guide.md`, `operating-guide.md`, `operating-guide.md`, `architecture-guide.md`, `documentation-index.md`, `surface-guide.md`, `data-governance.md`, `data-governance.md`, `market-data-runbook.md`, and `mini-pc-runbook.md` stayed in `docs/codex/`.

## Current Finding

Role-based folders under `docs/` are a good direction, but a direct move of canonical `docs/codex/*.md` is not safe yet.

Several current paths are hardcoded in:

- `AGENTS.md`
- `src/stock_monitor/cli.py`
- `scripts/verify_migration_archive.ps1`
- `tests/test_cli_commands.py`
- `tests/test_scheduler_scripts.py`
- many Markdown links under `docs/codex/`

The safest path remains staged:

1. Keep canonical documents at their current paths.
2. Move small/detail documents first, then update links/tests/scripts in one reviewed patch.
3. Defer any canonical path migration until it is worth changing scripts/tests/operator prompts together.

## Recommended Role Folders

| Folder | Purpose |
| --- | --- |
| `docs/codex/details/krx/` | Detailed KRX/Data Marketplace source notes, capture runbooks, and schema-stage references |
| `docs/codex/contracts/` | Specific DTO/display/data-shape contracts that support canonical policy docs |
| `docs/codex/plans/` | Detailed feature or analysis plans that remain useful but are not current-status anchors |
| `docs/codex/history/` | Historical restore/change logs kept for traceability |
| `docs/codex/weekly-sync/` | Weekly main-PC/mini-PC sync guide and prompt |

## File Classification

| Current file | Recommended role | Move now? | Proposed path |
| --- | --- | --- | --- |
| `docs/DOCS_ROLE_REORG_REVIEW_PROMPT.md` | Reorg control | No | Keep at `docs/DOCS_ROLE_REORG_REVIEW_PROMPT.md` until the reorg is complete. |
| `docs/DOCS_ROLE_REORG_REVIEW_2026-05-17.md` | Reorg control | No | Keep at `docs/DOCS_ROLE_REORG_REVIEW_2026-05-17.md` until the reorg is complete. |
| `docs/codex/documentation-index.md` | Index/control | No | Keep until all links/scripts/tests are updated. |
| `docs/codex/operating-guide.md` | Status | No | `docs/status/operating-guide.md` after compatibility update. |
| `docs/codex/operating-guide.md` | Status | No | `docs/status/operating-guide.md` after compatibility update. |
| `docs/codex/operating-guide.md` | Status | No | `docs/status/operating-guide.md` after compatibility update. |
| `docs/codex/architecture-guide.md` | Index/control | No | `docs/status/architecture-guide.md` or keep as compatibility anchor. |
| `docs/codex/architecture-guide.md` | History/status | Not moved | Keep near canonical docs for now because it is referenced from `AGENTS.md`. |
| `docs/codex/surface-guide.md` | Contract | Not moved | Keep at canonical path. |
| `docs/codex/data-governance.md` | Contract | Not moved | Keep at canonical path because parser/UI instructions point here. |
| `docs/codex/data-governance.md` | Contract | Not moved | Keep at canonical path. |
| `docs/codex/candidate-evidence.md` | Contract | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | Runbook | Not moved | Keep at canonical path. |
| `docs/codex/data-governance.md` | Runbook/detail | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/data-governance.md` | Runbook/plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/mini-pc-runbook.md` | Runbook | Not moved | Keep at canonical path. |
| `docs/codex/history.md` | History | Moved | Current path. |
| `docs/codex/surface-guide.md` | Plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/research-notes.md` | Plan | Moved | Current path. |
| `docs/codex/candidate-evidence.md` | Plan | Moved | Current path. |
| `docs/codex/data-governance.md` | Plan/runbook | Later | Pick one owner; avoid duplicates. |
| `docs/codex/surface-guide.md` | Plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/research-notes.md` | Plan | Moved | Current path. |
| `docs/codex/candidate-evidence.md` | Plan | Moved | Current path. |
| `docs/codex/research-notes.md` | Plan | Moved | Current path. |
| `docs/codex/architecture-guide.md` | Agents | No | `docs/agents/architecture-guide.md` after archive tests update. |
| `docs/codex/architecture-guide.md` | Agents | No | `docs/agents/module-ownership.md` after archive tests update. |
| `docs/codex/architecture-guide.md` | Agents | No | `docs/agents/agent-reassessment.md` after archive tests update. |
| `docs/codex/market-data-runbook.md` | KRX detail/history | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | KRX detail/runbook | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | KRX runbook | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | KRX runbook | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | KRX contract | Moved | Current path. |
| `docs/codex/market-data-runbook.md` | KRX detail/plan | Moved | Current path. |
| `docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md` | Weekly sync | Later | `docs/weekly-sync/WEEKLY_SYNC_GUIDE.md` after prompt/reference updates. |
| `docs/codex/weekly-sync/WEEKLY_SYNC_PROMPT.md` | Weekly sync | Later | `docs/weekly-sync/WEEKLY_SYNC_PROMPT.md` after prompt/reference updates. |

## Do Not Move First

Do not move these in the first patch:

- `docs/codex/documentation-index.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/architecture-guide.md`
- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/data-governance.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/mini-pc-runbook.md`

Reason: these are canonical, are referenced by CLI/archive checks/tests/scripts, or appear in operator prompts.

## Safer First Move Candidates

If the operator approves a staged move, start with lower-risk detail documents:

- `docs/codex/history.md`
- KRX detail documents currently listed as detailed references in `documentation-index.md`
- plan-only documents that are linked mostly from `operating-guide.md` and `operating-guide.md`

Even these should be moved only with link updates in the same patch.

## Required Link Updates

Before any move, search and update:

```powershell
rg -n "docs/codex/|docs\\codex\\|current-work\\.md|next-phase\\.md|execution-roadmap\\.md|documentation-index\\.md|project-map\\.md" AGENTS.md docs src tests scripts pyproject.toml
```

High-risk files to update if paths move:

- `AGENTS.md`
- `docs/codex/documentation-index.md`
- `docs/codex/architecture-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/mini-pc-runbook.md`
- `scripts/verify_migration_archive.ps1`
- `src/stock_monitor/cli.py`
- `tests/test_cli_commands.py`
- `tests/test_scheduler_scripts.py`
- `docs/codex/weekly-sync/WEEKLY_SYNC_PROMPT.md`
- `docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md`

## Weekly Sync Prompt Impact

The current weekly sync guide/prompt is correct for the current layout:

- guide/prompt docs: `docs/codex/weekly-sync/`
- generated mini-PC -> main-PC artifacts: `handoff/mini_pc_changes/`

If docs are later reorganized, update the weekly sync prompt to include the new `docs/` role folders in the zip allow-list. Until then, keep the existing paths.

## Pre-Move Commands

Run before any real move:

```powershell
rg --files docs
rg -n "docs/codex/|docs\\codex\\" AGENTS.md docs src tests scripts pyproject.toml
.\.venv\Scripts\python.exe -m pytest tests\test_scheduler_scripts.py tests\test_cli_commands.py -q
```

## Post-Move Commands

Run after any approved real move:

```powershell
rg -n "missing|docs/codex/|docs\\codex\\" AGENTS.md docs src tests scripts pyproject.toml
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_migration_archive.ps1 -ArchivePath <archive.zip>
.\.venv\Scripts\python.exe -m pytest tests\test_scheduler_scripts.py tests\test_cli_commands.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Use the archive verifier only against an actual sync/migration archive. Do not create or include `.env`, access-code material, DB files, or backups for this docs-only reorg.

## Recommendation

Do not reorganize `docs/codex` during the current mini-PC closeout window. The remaining live-operation blockers are non-code gates, and a broad doc-path move would add avoidable sync risk.

For weekly main-PC sync, include this review document and let the main PC decide whether to perform the path migration as a separate source-control patch.


<!-- Merged from: docs/DOCS_ROLE_REORG_REVIEW_PROMPT.md -->
## Docs Role Reorganization Review Prompt

Use this prompt before moving or splitting files under `{PROJECT_ROOT}\docs`.

```text
{PROJECT_ROOT}만 기준으로 작업해줘.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 판단해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

목표:
docs 폴더 전체를 역할별 폴더로 나눌 수 있는지 검토하고, 실제 이동 전 안전한 재분류 계획을 작성해줘.

중요 경계:
- .env, Telegram token, KRX key, access-code는 출력하지 마.
- admin-gui는 외부 공유 금지.
- web-view만 외부 공유 후보.
- 추천/점수/등급/매수·매도 신호는 금지.
- KRX Data Marketplace 자동 수집은 리포트 언급 종목 [12009] 최근 31일 보강만 허용.
- broad ingest, 전체 종목 수집, [12008]/[12010] 자동 수집은 금지.

검토 기준:
1. docs/codex/documentation-index.md의 canonical 문서 목록을 먼저 기준으로 삼아.
2. operating-guide.md, operating-guide.md, operating-guide.md처럼 자주 참조되는 문서는 이동 전 링크 영향도를 확인해.
3. 단순 history/detail 문서는 canonical 문서와 분리해도 되는지 확인해.
4. 문서 이동은 바로 하지 말고, 먼저 제안만 작성해.
5. 실제 이동이 필요하면 링크 수정 범위, 깨질 수 있는 참조, 검증 명령을 함께 제안해.

권장 역할 폴더 초안:
- docs/codex/details/krx/ : KRX/Data Marketplace 세부 근거, 캡처, 스키마 단계 문서
- docs/codex/contracts/ : canonical 정책 문서를 보조하는 세부 DTO/display/data-shape 계약
- docs/codex/plans/ : 현재 상태 anchor는 아니지만 여전히 유효한 세부 계획
- docs/codex/history/ : restore/change log 등 기록성 문서
- docs/codex/weekly-sync/ : 주간 sync guide/prompt 문서

주의:
operating-guide.md, operating-guide.md, operating-guide.md, documentation-index.md, architecture-guide.md, surface-guide.md, data-governance.md, data-governance.md, market-data-runbook.md, mini-pc-runbook.md 같은 canonical/운영 anchor는 경로를 유지하는 것을 기본값으로 삼아.

산출물:
1. 현재 docs 파일별 추천 역할 분류표
2. 이동하지 말아야 할 문서와 이유
3. 이동해도 되는 문서와 예상 새 경로
4. 링크 수정이 필요한 문서 목록
5. 실제 이동 전 확인 명령
6. 실제 이동 후 확인 명령
7. 주간 sync 프롬프트에서 바꿔야 할 경로가 있으면 수정 제안

주의:
문서 이동은 구현보다 링크 안정성이 중요하다. 실제 파일 이동은 내가 별도로 승인하기 전에는 하지 마.
```
