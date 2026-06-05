# Operator Memo Surface Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move partial operator memo artifacts from CLI-only checks into actual user/operator surfaces and verification loops.

**Architecture:** Keep new behavior read-only except for explicit Telegram photo intake, which stores only operator-sent files into the local photo inbox. Web-view receives stored one-line commentary and periodic-data status blocks through existing daily DTOs; Telegram receives safe one-line commentary through a command response and optional caption-based `/사진` intake. No scheduler registration, broad KRX ingest, public scoring, or trading-decision copy is added.

**Tech Stack:** Python CLI, Telegram Bot API, SQLite repository reads, existing web-view HTML/JS, pytest.

---

## Tasks

### Task 1: One-Line Commentary On Web-View And Telegram

- [x] Add failing tests that daily web-view DTO exposes `market_commentary`.
- [x] Add failing tests that Telegram `/한줄` returns three safe one-line comments.
- [x] Implement `market_commentary` in `build_web_view_daily_snapshot`.
- [x] Render the comments in the top `오늘 읽을 요약` card.
- [x] Add Telegram command parser support for `/한줄`, `/코멘트`, and `/시장코멘트`.

### Task 2: Telegram Photo Intake

- [x] Add failing tests for `/사진` command parsing.
- [x] Add failing tests for saving a photo/document from Telegram update metadata into `data/operator_photo_inbox`.
- [x] Add Telegram file helpers for `getFile` and file download.
- [x] Support both caption-based `/사진 설명` and pending `/사진 설명` then next photo.
- [x] Keep replay safety through control-state applied update ids.

### Task 3: Periodic Data Needs On Operator/User Surfaces

- [x] Add failing tests that daily web-view DTO exposes `periodic_data_needs`.
- [x] Render a compact status in `시장` or top summary without exposing admin state or secrets.
- [x] Include the same read-only block in `operator-status`.

### Task 4: Docs, Memo Status, QA

- [x] Update `operator_memos.md`, `current-work.md`, `execution-roadmap.md`, and mini-PC handoff.
- [x] Run focused tests, `tests/test_cli_commands.py`, `tests/test_control.py`, `tests/test_telegram_command_replay.py`, `tests/test_web_view.py`.
- [x] Run `web-view-value-qa` and `web-view-browser-smoke`.

## Boundaries

- `admin-gui` remains private.
- `web-view` remains GET-only/read-only.
- Telegram photo intake writes only local files sent by the configured chat.
- `.env`, token, KRX key, access-code, password, cookie, and DB path are not printed.
- `[12008]` and `[12010]` automation remains blocked.
- Public score, grade, buy/sell, entry/exit, target-return, and conviction wording remains blocked.
