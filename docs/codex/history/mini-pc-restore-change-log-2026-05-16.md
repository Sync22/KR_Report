# Mini PC Restore Change Log - 2026-05-16

## Purpose

This document records the changes made on the mini PC from the first restore conversation through the current state.

Use it when syncing the original desktop/source-managed copy with the mini PC work.
It intentionally does not include `.env` values, Telegram tokens, KRX keys, access-code values, cookies, or other secrets.

## Scope

Project folder only:

```text
C:\Users\MING\Codex\02.Stock_Moniter
```

Source-of-truth documents read before work:

1. `AGENTS.md`
2. `docs/codex/documentation-index.md`
3. `docs/codex/mini-pc-migration-handoff.md`
4. `docs/codex/krx-market-data-runbook.md`
5. `docs/codex/current-work.md`
6. `docs/codex/next-phase.md`
7. `docs/codex/plans/backtest-observation-plan.md`

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
- Candidate tunnel target remains `http://127.0.0.1:8780`.

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
data\backups\stock_monitor_20260516_0056_post-restore.db
```

Additional backup before latest mentioned-flow catch-up:

```text
data\backups\stock_monitor_20260516_0130_before_latest_mentioned_flow_31d_fill.db
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
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/mini-pc-migration-handoff.md`
- `docs/codex/current-work.md`
- `docs/codex/next-phase.md`
- `docs/codex/plans/backtest-observation-plan.md`
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
- `docs/codex/mini-pc-migration-handoff.md`
- `docs/codex/current-work.md`
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/next-phase.md`
- `docs/codex/plans/backtest-observation-plan.md`
- `docs/codex/history/mini-pc-restore-change-log-2026-05-16.md`
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
C:\Users\MING\Codex\02.Stock_Moniter only.
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
- `docs/codex/krx-market-data-runbook.md`: clarified that full restored-history catch-up must respect each stock's latest-anchor 31-day window.
- `docs/codex/next-phase.md`, `docs/codex/data-rebaseline-plan.md`, `docs/codex/execution-roadmap.md`, and `docs/codex/module-ownership.md`: stale same-day wording was aligned to anchor-date wording where it referred to the approved `[12009]` lane.

## 2026-05-16 Per-Stock Latest-Anchor Flow Catch-Up

The full restored-history `[12009]` catch-up was completed on the mini PC with the exact per-stock latest-anchor rule:

- Report range audited: `2026-01-02` through `2026-05-15`.
- Policy: each stock's latest report-mentioned date, then that stock's recent 31 calendar-day window filtered to Korean business days.
- Starting missing stock/date calls: `13,940`.
- Backup before live execution: `data\backups\stock_monitor_20260516_1100_before_latest_anchor_mentioned_flow_fill.db`.
- Completed live coverage: `13,940` stock/date calls and `181,220` stored `[12009]` rows.
- Batch shape: `46` full 300-call batches plus one final 140-call batch. One 300-call batch hit the shell timeout after DB writes; it left no completion event, but follow-up dry-run showed those rows were present and the next run resumed from the remaining stock/date calls.
- Final dry-run: `raw_call_count=0`, `planned_call_count=0`, `anchor_dates_with_missing_count=0`.
- Final `db-verify`: integrity `ok`, schema `5/5`, no pending migrations, no foreign key violations, no duplicate source ids, no investor-flow quality issues.
- Final `stock_investor_flow_daily` row count: `197,704`.
- Unresolved stock codes skipped before KRX requests: `052960`, `233990`, `351020`, `000001`, `0126Z0`, `0120G0`, `0008Z0`, `0004V0`, `0007C0`, `0009K0`.

Source updates made for this catch-up:

- `src/stock_monitor/cli.py`: added `krx-mentioned-flow-latest-anchor-backfill` for restored-history catch-up that plans by each stock's latest report anchor.
- `tests/test_cli_commands.py`: added regression coverage for the latest-anchor dry-run and live safety flags.
- `docs/codex/krx-market-data-runbook.md`: added the exact restored-history command sequence.
