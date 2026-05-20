# Docs Role Reorganization Review - 2026-05-17

## Context

This review was prepared on the mini PC.

The mini PC is the current live-operation machine. Weekly source sync artifacts that should be reviewed on the main PC belong under:

- `handoff/mini_pc_changes/`

This document started as a proposal. The operator approved a limited reorganization on `2026-05-17`, and only non-canonical detail/history/plan/contract documents were moved.

Canonical documents such as `current-work.md`, `next-phase.md`, `execution-roadmap.md`, `project-map.md`, `documentation-index.md`, `surface-contract.md`, `data-quality-checklist.md`, `data-source-policy.md`, `krx-market-data-runbook.md`, and `mini-pc-migration-handoff.md` stayed in `docs/codex/`.

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
| `docs/codex/current-work.md` | Status | No | `docs/status/current-work.md` after compatibility update. |
| `docs/codex/next-phase.md` | Status | No | `docs/status/next-phase.md` after compatibility update. |
| `docs/codex/execution-roadmap.md` | Status | No | `docs/status/execution-roadmap.md` after compatibility update. |
| `docs/codex/project-map.md` | Index/control | No | `docs/status/project-map.md` or keep as compatibility anchor. |
| `docs/codex/decision-log.md` | History/status | Not moved | Keep near canonical docs for now because it is referenced from `AGENTS.md`. |
| `docs/codex/surface-contract.md` | Contract | Not moved | Keep at canonical path. |
| `docs/codex/data-quality-checklist.md` | Contract | Not moved | Keep at canonical path because parser/UI instructions point here. |
| `docs/codex/data-source-policy.md` | Contract | Not moved | Keep at canonical path. |
| `docs/codex/contracts/candidate-evidence-contract.md` | Contract | Moved | Current path. |
| `docs/codex/krx-market-data-runbook.md` | Runbook | Not moved | Keep at canonical path. |
| `docs/codex/krx-18m-backfill-analysis.md` | Runbook/detail | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/data-rebaseline-plan.md` | Runbook/plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/mini-pc-migration-handoff.md` | Runbook | Not moved | Keep at canonical path. |
| `docs/codex/history/mini-pc-restore-change-log-2026-05-16.md` | History | Moved | Current path. |
| `docs/codex/admin-gui-plan.md` | Plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/plans/backtest-observation-plan.md` | Plan | Moved | Current path. |
| `docs/codex/plans/candidate-evidence-plan.md` | Plan | Moved | Current path. |
| `docs/codex/data-rebaseline-plan.md` | Plan/runbook | Later | Pick one owner; avoid duplicates. |
| `docs/codex/rotation-overlay-plan.md` | Plan | Not moved | Keep at current path because archive verification currently expects it. |
| `docs/codex/plans/scoring-draft-plan.md` | Plan | Moved | Current path. |
| `docs/codex/plans/target-price-progress-plan.md` | Plan | Moved | Current path. |
| `docs/codex/plans/telegram-briefing-plan.md` | Plan | Moved | Current path. |
| `docs/codex/agent-guide.md` | Agents | No | `docs/agents/agent-guide.md` after archive tests update. |
| `docs/codex/module-ownership.md` | Agents | No | `docs/agents/module-ownership.md` after archive tests update. |
| `docs/codex/agent-reassessment.md` | Agents | No | `docs/agents/agent-reassessment.md` after archive tests update. |
| `docs/codex/details/krx/etf-flow-source-study.md` | KRX detail/history | Moved | Current path. |
| `docs/codex/details/krx/krx-api-field-validation.md` | KRX detail/runbook | Moved | Current path. |
| `docs/codex/details/krx/krx-flow-execution-stages.md` | KRX runbook | Moved | Current path. |
| `docs/codex/details/krx/krx-flow-sample-capture-runbook.md` | KRX runbook | Moved | Current path. |
| `docs/codex/details/krx/krx-investor-flow-schema.md` | KRX contract | Moved | Current path. |
| `docs/codex/details/krx/krx-investor-flow-source-plan.md` | KRX detail/plan | Moved | Current path. |
| `docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md` | Weekly sync | Later | `docs/weekly-sync/WEEKLY_SYNC_GUIDE.md` after prompt/reference updates. |
| `docs/codex/weekly-sync/WEEKLY_SYNC_PROMPT.md` | Weekly sync | Later | `docs/weekly-sync/WEEKLY_SYNC_PROMPT.md` after prompt/reference updates. |

## Do Not Move First

Do not move these in the first patch:

- `docs/codex/documentation-index.md`
- `docs/codex/current-work.md`
- `docs/codex/next-phase.md`
- `docs/codex/execution-roadmap.md`
- `docs/codex/project-map.md`
- `docs/codex/surface-contract.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/data-source-policy.md`
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/mini-pc-migration-handoff.md`

Reason: these are canonical, are referenced by CLI/archive checks/tests/scripts, or appear in operator prompts.

## Safer First Move Candidates

If the operator approves a staged move, start with lower-risk detail documents:

- `docs/codex/history/mini-pc-restore-change-log-2026-05-16.md`
- KRX detail documents currently listed as detailed references in `documentation-index.md`
- plan-only documents that are linked mostly from `current-work.md` and `execution-roadmap.md`

Even these should be moved only with link updates in the same patch.

## Required Link Updates

Before any move, search and update:

```powershell
rg -n "docs/codex/|docs\\codex\\|current-work\\.md|next-phase\\.md|execution-roadmap\\.md|documentation-index\\.md|project-map\\.md" AGENTS.md docs src tests scripts pyproject.toml
```

High-risk files to update if paths move:

- `AGENTS.md`
- `docs/codex/documentation-index.md`
- `docs/codex/project-map.md`
- `docs/codex/current-work.md`
- `docs/codex/execution-roadmap.md`
- `docs/codex/mini-pc-migration-handoff.md`
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
