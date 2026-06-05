# Operations Observation 2026-06-01

## Scope

- Workspace: `<PROJECT_ROOT>`
- Observation run time: `2026-05-31 15:24~15:27 KST`
- Target business date: `2026-06-01`
- Mode: read-only observation summary.

This run did not edit code, run migrations, write snapshot tables, send Telegram messages, change scheduler tasks, run external provider smoke, or read `.env`/secret contents. The only write performed for this task is this markdown summary.

Important timing note: this observation was run on `2026-05-31`, before the `2026-06-01` scheduled task due times. Scheduled-run checks for `2026-06-01` are therefore correctly `pending`, not failed.

## Commands Run

- `.venv\Scripts\python.exe -m stock_monitor next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json`
- `.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json`
- `.venv\Scripts\python.exe -m stock_monitor market-day-observation --date 2026-06-01 --json`
- `.venv\Scripts\python.exe -m stock_monitor krx-baseline-analysis --json`
- `.venv\Scripts\python.exe -m stock_monitor candidate-evidence-readiness --recent-report-dates 1 --stock-limit 5 --json`
- `.venv\Scripts\python.exe -m stock_monitor market-briefing-readiness --recent-report-dates 5 --json`
- `.venv\Scripts\python.exe -m stock_monitor web-view-startup-fallback-check --json`
- `.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json`
- `git status --short`

## Scheduled-Run Observation

`market-day-observation --date 2026-06-01 --json` returned:

- `read_only=true`
- `writes_database=false`
- `sends_telegram=false`
- `registers_scheduler=false`
- `business_date=2026-06-01`
- `status=pending`
- `observed_enough_for_scheduler=false`

All expected checks were `pending` because the run happened before their verify times:

| Task | Scheduled | Verify After | Status |
| --- | --- | --- | --- |
| StockMonitor-TelegramCommands | 08:00 | 08:05 | pending, not yet due |
| StockMonitor-KrxDailyBackfill | 08:10 | 08:20 | pending, not yet due |
| StockMonitor-Notify | 08:20 | 08:30 | pending, not yet due |
| StockMonitor-Poll | 08:30~16:30 | 09:00 | pending, not yet due |
| StockMonitor-KrxMentionedFlowBackfill | 16:00 | 16:10 | pending, not yet due |

Log summary:

- `logs/api_perf.log` exists and had fresh entries from the local browser smoke around `2026-05-31 15:24 KST`.
- `data/logs/web_view_*.log` files inspected by name/size were present but zero bytes in the latest listed files.
- No raw DB row dump or secret-bearing log content was copied into this note.

## KRX Daily Snapshot State

`krx-baseline-analysis --json` and `next-phase-readiness` agree that stored KRX OpenAPI daily snapshots currently cover:

- `stock_market_daily`: through `2026-05-27`
- `etf_daily_snapshots`: through `2026-05-27`
- `market_index_daily`: through `2026-05-27`

Missing publishable daily snapshot date:

- `2026-05-28`, all six daily endpoints missing:
  - `etf-daily`
  - `stock-kospi-daily`
  - `stock-kosdaq-daily`
  - `index-krx-daily`
  - `index-kospi-daily`
  - `index-kosdaq-daily`

KRX rule reminder: same-day rows for `2026-06-01` are not expected until the official next-business-day publication window. The current blocker is the older publishable `2026-05-28` gap, not same-day `2026-06-01`.

## Next-Phase Readiness

`next-phase-readiness` completed as read-only and returned `completion_ready=false`.

Confirmed ready/healthy items:

- Latest stored report date: `2026-05-29`
- Latest report count: `28`
- Candidate evidence: `5/5` recent dates review-ready, QA issue dates `0`
- Market briefing: preview-ready `5/5`
- Market briefing manual review sends: `3/3`
- Market briefing phone review: accepted
- External web-view provider smoke: recorded ready from prior evidence
- Market holiday coverage: ready

Current blockers:

- KRX OpenAPI daily snapshot still missing for `2026-05-28`
- Latest DB backup restore-smoke missing
- web-view Startup fallback post-logon observation missing
- Real market-day scheduled-run observation still pending for `2026-06-01`

## Web-View Browser Smoke

`web-view-browser-smoke --date latest --json` completed with:

- `issue_count=0`
- Smoke business date: `2026-05-29`
- Access-code mode: temporary disabled for the local smoke server
- Viewports checked: desktop, tablet, large mobile, mobile
- Tab contract: 5 tabs in order `main`, `watch`, `stock`, `market`, `rotation`
- Horizontal overflow: `0px` across checked viewports
- GET-only boundary:
  - `GET /api/daily/2026-05-29`: `200`
  - `GET /api/daily/{date}?intraday_market_top=1`: `200`
  - `GET /api/candidate-evidence`: `200`
  - `GET /api/daily/{date}/stocks/{stock_code}`: `200`
  - `POST /api/daily/2026-05-29`: `405`
  - `GET /api/status`: `404`

The local persistent web-view `/health` also returned `200` through `web-view-startup-fallback-check --json`, but startup fallback is still not marked ready because no post-logon success event has been recorded.

## Main Priority Candidates

The latest stored report date is `2026-05-29`, not `2026-06-01`. Therefore the visible current candidate state is based on `2026-05-29` stored data.

`candidate-evidence-readiness --recent-report-dates 1 --stock-limit 5 --json` reported the first two top rows as:

| Rank | Stock | Priority | Public reasons | Missing public context |
| --- | --- | --- | --- | --- |
| 1 | 네오위즈 `095660` | 우선 확인 | 목표가 하향, 수급 전환 지속 | 선택일 KRX 저장값 없음 |
| 2 | 아모레퍼시픽 `090430` | 우선 확인 | 목표가 하향, 수급 전환 지속 | 선택일 KRX 저장값 없음 |

Both rows had public support evidence of `52주 위치 참고` and `거래량 위치 참고`. The top-2 maturity summary still asks for KRX backfill because exact selected-date KRX snapshots are missing.

## Intraday Turnover Button Observation

Before-click state:

- Browser smoke confirmed the intraday button exists in all checked viewports.
- Browser smoke confirmed `intraday_overlap_initial_visible=false`, so the overlap panel is hidden before the user checks it.
- This matches the expected "do not show trading-value overlap before explicit user action" behavior.

Click/API-equivalent state:

- Browser smoke confirmed the GET route used by the button returned `200` on the temporary local smoke server.
- A direct call to the persistent local server was blocked by the access-code gate, which is expected for the real web-view surface. No access code or secret was read.
- A read-only CLI equivalent of the button path, `market-commentary-practice --date latest --intraday-market-top --json`, reported:
  - `live_fetch=true`
  - `writes_snapshot_tables=false`
  - `can_overlap_intraday_market_top=true`
  - status reason: report summaries for 28 stocks can be intersected with Naver trading-value top data
  - `items=[]`
  - `empty_reason=Naver 거래대금 상위 확인 중 오류가 발생했습니다.`
  - errors on KOSPI/KOSDAQ page 1 due local socket access denial: `WinError 10013`

Overlap chip / empty-error result:

- No overlap chips were available in this run.
- Expected user-facing outcome after click is the empty/error state, not a populated chip list.
- The stored report summary remains visible; the intraday reference failure should not block stored-data web-view rendering.

`market_status` / `trade_time`:

- The UI code and tests support showing `market_status` and `trade_time` on overlap chips when Naver items are available.
- This run could not verify actual displayed `market_status` or `trade_time` because Naver trading-value top fetch returned no items under the local socket restriction.

Perceived latency:

- `api_perf_summary` for `/api/daily/2026-05-29?intraday_market_top=1&market_top_limit=100&market_top_page_size=20` showed:
  - count `6`
  - p50 `1138.534ms`
  - p95/max `6876.927ms`
  - status `200`
- This feels acceptable when cached/fast, but the uncached intraday path can still feel several seconds long.

## Telegram And Market Briefing Review

Market briefing readiness:

- `preview_ready_count=5`
- `public_safe_issue_count=0`
- `manual_review_send_count=3`
- manual review dates: `2026-05-15`, `2026-05-14`, `2026-05-13`
- `phone_review_accepted=true`
- `schedule_candidate_ready=true`
- schedule window: `16:10~16:45`

Data warnings still present:

- `missing_notable_stocks`
- `krx_snapshot_fallback:2026-05-27`

Telegram scheduled-run evidence for `2026-06-01` is not judged yet because the observation ran before the `08:05` verify time.

## Still Not Decidable From Current Data

- Whether the `2026-06-01` scheduled tasks actually ran, because the check was before due times.
- Whether `2026-06-01` same-day reports and KRX same-day rows exist, because the target business day had not happened yet.
- Whether the intraday overlap chip can show real `market_status` / `trade_time` on this PC, because the Naver trading-value top fetch failed with local socket access denial.
- Whether Startup fallback is fully closed after reboot/logon, because no `--record-success` event was written and this task was read-only.
- Whether the latest backup restore-smoke is clean, because restore-smoke was not run in this read-only observation.

## Git Status At Observation Time

Existing local changes remained outside this observation summary:

- `.codegraph/config.json`
- `docs/codex/mini-pc-migration-handoff.md`
- `scripts/register_task_scheduler_tasks.ps1`
- `scripts/run_process_telegram_commands.ps1`
- `tests/test_scheduler_scripts.py`
- `data/`

This observation added:

- `docs/codex/operations/operations-observation-2026-06-01.md`

## One-Line Review

As of the pre-day read-only check on `2026-05-31`, the web-view surface is healthy and GET-only, market briefing review gates are closed, but `2026-06-01` scheduled-run proof is still naturally pending and intraday turnover overlap is blocked by local socket access rather than by the stored-data web-view pipeline.
