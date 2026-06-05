# Operator Memo Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current operator memo backlog into a checkable status surface and create first implementation artifacts for the open `2026-05-18` memos.

**Architecture:** Keep operator memos as local rough ideas in `data/operator_memos.md`, but add read-only CLI surfaces that can prove whether a memo has moved beyond discussion. The implementation adds no scheduler, Telegram send, live network fetch, public score, trading recommendation, secret output, or `admin-gui` exposure.

**Tech Stack:** Python CLI, SQLite repository reads, pytest, Markdown documentation.

---

## Scope

In scope:

- Parse and report all operator memo statuses.
- Add a stored-data one-line market commentary practice preview.
- Add a local photo inbox status command for future example screenshots.
- Add a read-only periodic data needs audit.
- Update memo status docs once real artifacts exist.

Out of scope:

- No Telegram sending.
- No scheduler registration.
- No live KRX/Naver/browser fetch.
- No broad ingest, all-stock collection, or `[12008]`/`[12010]` automation.
- No public numeric score, grade, buy/sell, entry/exit, target-return, or conviction wording.

## Current Memo Check

`data/operator_memos.md` now has:

- `[O]` completed: 7
- `[△]` partial/foundation: 9
- `[ ]` not started: 1

Open `[ ]` memo:

- `26.05.08 00:00` US market API source investigation: still intentionally deferred until domestic operation is stable.

This implementation moved the three `2026-05-18` open memos to partial by creating first artifacts. US market expansion remains explicitly deferred by canonical scope.

## Files

- Modify: `src/stock_monitor/cli.py`
  - Add `operator-memo-status`.
  - Add `market-commentary-practice`.
  - Add `operator-photo-inbox-status`.
  - Add `periodic-data-needs-audit`.
- Modify: `tests/test_cli_commands.py`
  - Add focused tests for the new read-only helpers.
- Modify: `data/operator_memos.md`
  - Reclassify the three `2026-05-18` memos from `[ ]` to `[△]` after the artifacts pass tests.
- Modify: `docs/codex/current-work.md`
  - Record the memo-progress implementation pass.
- Modify: `docs/codex/execution-roadmap.md`
  - Update `Operator Memo Status` with the new artifact names.
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`
  - Add source-sync note for main PC.

## Tasks

### Task 1: Add Memo Status Surface

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Add tests that create a temporary `operator_memos.md`, call the parser/snapshot helper, and assert status counts plus the open memo rows are present.

- [x] **Step 2: Run the RED tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_cli_commands.py::test_operator_memo_status_snapshot_parses_status_counts -q
```

Expected: fail because the helper does not exist yet.

- [x] **Step 3: Implement parser and CLI**

Implement a read-only parser for memo lines shaped like:

```text
- [△] 26.05.18 12:01 | 값 정제하기...
```

Add `operator-memo-status --json`.

- [x] **Step 4: Run GREEN tests**

Run the focused memo-status tests and confirm they pass.

### Task 2: Add One-Line Commentary Practice

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Create stored reports, summaries, and KRX index rows, then assert `market-commentary-practice` returns exactly three neutral phases: `opening`, `midday`, and `preclose`.

- [x] **Step 2: Implement read-only preview**

Use stored report count, summary stock count, and KOSPI/KOSDAQ stored index references to produce neutral one-line comments. Use labels such as `장초반`, `점심`, and `장 마감 전`; do not output buy/sell, score, grade, conviction, or strategy wording.

### Task 3: Add Photo Inbox Status

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Create an image-like file under a temp inbox and assert the status command lists it without reading image contents.

- [x] **Step 2: Implement read-only inbox status**

Default the inbox to `data/operator_photo_inbox`. Report path, file count, allowed extensions, and next action. Do not upload, expose, or transform files.

### Task 4: Add Periodic Data Needs Audit

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Seed stored report summaries and market index rows, then assert the audit identifies KOSPI/KOSDAQ index coverage as already stored through KRX Open API snapshots and keeps investor-flow broad collection blocked.

- [x] **Step 2: Implement read-only audit**

Return machine-readable rows for report, KRX index, stock/ETF daily, `[12009]` mentioned-stock flow, and blocked broad flow/ranking sources.

### Task 5: Document And Verify

**Files:**

- Modify: `data/operator_memos.md`
- Modify: `docs/codex/current-work.md`
- Modify: `docs/codex/execution-roadmap.md`
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`

- [x] **Step 1: Update memo statuses**

Mark the three `2026-05-18` memos as `[△]` with the implemented artifact command names.

- [x] **Step 2: Run verification**

Run:

```powershell
.venv\Scripts\python.exe -m py_compile src\stock_monitor\cli.py tests\test_cli_commands.py
.venv\Scripts\python.exe -m pytest tests\test_cli_commands.py -q
.venv\Scripts\python.exe -m stock_monitor operator-memo-status --json
.venv\Scripts\python.exe -m stock_monitor market-commentary-practice --date latest --json
.venv\Scripts\python.exe -m stock_monitor operator-photo-inbox-status --json
.venv\Scripts\python.exe -m stock_monitor periodic-data-needs-audit --date latest --json
```

Expected: tests pass and all four CLI commands are read-only.

## Self-Review

- The plan handles all current memos by status and creates real artifacts for the three open domestic-operation memos.
- US market API expansion remains deferred because it is outside current domestic mini-PC scope.
- All new commands are read-only and local.
- No public trading-decision wording or broader KRX automation is introduced.

## Result

- Added `operator-memo-status`, `market-commentary-practice`, `operator-photo-inbox-status`, and `periodic-data-needs-audit`.
- Added focused tests for all four new read-only helpers.
- Created local-only inbox documentation at `data/operator_photo_inbox/README.md`.
- Updated `data/operator_memos.md` so implemented domestic-operation artifacts are no longer `[ ]`.
- Final memo status: done `7`, partial `9`, open `1`, other `0`.
- The only remaining open memo is US market API expansion, intentionally deferred from the domestic mini-PC scope.
- Verification passed:
  - `py_compile src\stock_monitor\cli.py tests\test_cli_commands.py`
  - `pytest tests\test_cli_commands.py -q`: `252 passed`
  - `pytest tests\test_web_view.py -q`: `30 passed`
  - all four new CLI commands returned read-only JSON successfully.
