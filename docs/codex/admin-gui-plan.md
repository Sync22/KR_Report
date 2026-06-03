# Admin GUI Plan

## Purpose

This is the consolidated local operator GUI plan.

Use this instead of starting from older admin review/progress notes. The older files remain as history, but this file is the active admin GUI direction.

## Current State

| Area | Status |
| --- | --- |
| Local `admin-gui` server | Implemented |
| Loopback-first boundary | Implemented |
| Scheduler cards/status | Implemented |
| Run-now for allowed tasks | Implemented |
| Scheduler enable/disable | Implemented |
| Shutdown run-now block | Implemented |
| No-run calendar | Implemented |
| Right-click reason editing | Implemented |
| No-run date server validation | Implemented |
| Safe settings panel | Implemented |
| Audit log display | Implemented |
| Operation profile editing | Implemented |
| TelegramCommands restart recovery | Implemented |
| Read-only recovery guidance | Implemented |
| DB backup/verify reminders | Implemented |
| Recent event readable summaries | Implemented |
| KRX/admin display cards | First pass |

## Boundary

`admin-gui` is the operator operations surface.

It should stay focused on operations menu/status/control: scheduler state, pause/no-run controls, safe settings, recovery guidance, DB freshness, operation events, and admin audit.

It must not become the friend-facing shared page. Shared read-only information belongs in `web-view` and must stay GET-only.

It also must not become the main judgment review workbench. News intelligence, candidate linkage, raw recommendation-support labels, sentiment/impact internals, and candidate evidence review details belong in the future `operator-review` surface when a private review UI is needed. `admin-gui` may show coarse operational readiness for those lanes, but not the review body.

## Next Admin Work

| Priority | Work | Done condition |
| --- | --- | --- |
| P0 | Keep status labels aligned with `operator-status` | GUI and CLI use the same health meaning. |
| P0 | Keep safe settings audited | Every setting write has validation, confirmation, and reason. |
| Done / P1-watch | Refine recovery controls | `operator-status` and `admin-gui` now show read-only safest-next-step recovery guidance; the only broad GUI recovery control remains TelegramCommands restart until live evidence justifies more controls. |
| Done | Improve event readability | Recent events keep raw detail in operator JSON but `admin-gui`/text status prefer readable summaries for KRX, flow, scheduler, notify, and admin failures. |
| Done | Add migration/backup reminders | `operator-status` JSON/text and `admin-gui` show latest DB backup presence plus db-verify/db-backup guidance before risky work. |

No-run date server validation rejects market holidays, env-level no-run dates, and past dates. DB-managed no-run dates should represent future or same-day manual exclusions only; historical explanation belongs in operation events/docs, not a scheduler override.

## Excluded From Admin GUI

- Raw `.env` editing.
- Telegram token or chat id editing.
- Raw shell command editing.
- One-click shutdown.
- Friend-facing read-only mode.
- Public tunnel exposure.
- News intelligence raw observation rows.
- Candidate evidence review workbench.
- Raw sentiment score, stock impact, recommendation-support, or candidate linkage internals.

## Verification

```powershell
python -m stock_monitor operator-status --json --health-exit
python -m stock_monitor db-verify
python -m pytest tests\test_admin_gui.py tests\test_operator_status.py -q
```
