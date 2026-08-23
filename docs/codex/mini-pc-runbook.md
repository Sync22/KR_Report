# Mini PC Runbook

Migration, restore, scheduler handoff, and weekly main-PC sync.

## Included sections
- Mini PC Migration Handoff
- Weekly Mini PC Sync Guide
- Weekly Mini PC Sync Prompt

<!-- Merged from: docs/codex/mini-pc-runbook.md -->
## Mini PC Migration Handoff

## Purpose

This is the handoff for moving `02.Stock_Moniter` from the original desktop to an always-on Windows mini PC, plus the current post-restore operating checklist for the mini PC.

Use this as the migration checklist before copying the project, registering scheduler tasks, or exposing the friend-facing page. After restore, use it as the canonical checklist for validating scheduler evidence and external `web-view` readiness.

## Scope

Project folder:

```text
{PROJECT_ROOT}
```

Do not infer state from sibling folders.
The new Codex session on the mini PC should start from this project folder and read:

1. `AGENTS.md`
2. `docs/codex/documentation-index.md`
3. `docs/codex/operating-guide.md`
4. `docs/codex/operating-guide.md`
5. `docs/codex/surface-guide.md`
6. `docs/codex/market-data-runbook.md`
7. `CHANGELOG.md`
8. this file

## Migration Readiness Snapshot

Current snapshot as of `2026-05-17 17:02 KST`:

| Area | State | Migration note |
| --- | --- | --- |
| Core app | Runnable local Python MVP restored on the mini PC | Keep working inside this project folder and reinstall dependencies only if the venv is rebuilt. |
| DB | SQLite production DB lives under `data/stock_monitor.db` | Restored on the mini PC; keep backing up before KRX/data-changing work. |
| Latest verified backup | `data/backups/stock_monitor_{timestamp}_{tag}.db` | Created after the successful guarded `2026-05-15` KRX Open API retry and restore-smoked successfully. Create another fresh backup before future data-changing work. |
| Latest verified dry-run archive | `data/Stock_Moniter_migration_dryrun.zip` plus sidecar `data/Stock_Moniter_migration_dryrun.zip.sha256` | Verify the current sidecar with `verify_migration_archive.ps1`; do not pin the hash inside this file because the archive includes this document. The archive excludes `.env`, `data/access_code.json`, backups, generated archives, caches, logs, and experimental venvs. Recreate it after more data/code changes before the actual copy. |
| KRX Open API latest snapshot | Stored through `2026-05-15`; `krx-baseline-analysis` reports `missing_daily_snapshots=0` | The previous latest-date empty-row blocker was cleared by the backed-up `2026-05-17 08:17 KST` retry. |
| KRX Data Marketplace flow | Narrow automatic `[12009]` anchor-day mentioned-stock 31-day path exists | In normal live operation the anchor is the current business day; after restore or prefilled report ingestion, anchor to the latest report-mentioned business date. Broad all-stock/top-ranking scheduled ingest remains forbidden without separate approval. |
| Scheduler registration | Six default mini-PC tasks are registered/enabled, including hourly `StockMonitor-WebViewHourlyRestart` for the loopback web-view target | Elevated local `verify_task_scheduler_registration.ps1` passed after registration; `StockMonitor-Shutdown` is intentionally absent for always-on operation. Non-elevated shells may still show Task Scheduler `access_denied`. |
| External sharing | Cloudflare provider smoke passed for `https://web-view.example.invalid` | The `2026-05-17 17:46 KST` post-provider verification recorded success after checking `13` HTTP routes and `5` public JSON routes. `/health` returned `200`; unauthenticated user routes returned `401`; write/control routes stayed blocked with `405` or gated responses. Share only `web-view`, never `admin-gui`; keep the provider target on `{LOCAL_WEB_VIEW_TARGET}` and keep the access-code/allow-list gate enabled. |

## Current Operating Contract

This table is the current scheduler contract. Later KRX-specific procedures in this document are retained for historical recovery/reference only; they are not registered during normal operation.

| Task | Contract |
| --- | --- |
| `StockMonitor-Notify` | `08:20` KST on Korean business days. Runtime guard allows production send only from `08:00` to `08:30` unless `--allow-late` is explicit. |
| `StockMonitor-Poll` | Every 30 minutes from `08:30` to `16:30` KST on Korean business days. |
| `StockMonitor-MarketBriefingMood` / `Lunch` / `Preclose` | `09:15` / `12:00` / `15:15` KST operator briefing slots. |
| `StockMonitor-TossCloseSnapshot` | `20:00` KST on Korean business days; stores the bounded Toss close snapshot used by web-view market, ETF, and flow references. |
| `StockMonitor-TelegramCommands` | Hidden worker starts at `08:00`, checks Telegram commands every 1 minute, exits at `16:30`, and skips market holidays/no-run dates. During `09:00~15:30`, it also checks the official KIND `서킷브레이커/사이드카` market-action category and sends one operator alert per official acceptance number. |
| `StockMonitor-WebViewHourlyRestart` | Hourly restart, default first run `00:05`, for the read-only loopback `web-view` target on `{LOCAL_WEB_VIEW_TARGET}`. |
| `StockMonitor-Shutdown` | Desktop-validation only. It is not registered by the mini-PC scheduler wrapper and should remain absent during always-on operation. |

External `web-view` runtime note:

- The Cloudflare target is the read-only `web-view` on `{LOCAL_WEB_VIEW_TARGET}`.
- `scripts/run_web_view.ps1 -HostAddress <loopback-host> -Port <web-view-port>` is the canonical local runner.
- `scripts/restart_web_view.ps1 -HostAddress <loopback-host> -Port <web-view-port>` is the canonical scheduler restart helper; it stops the current port listener and starts only the read-only `web-view`.
- `StockMonitor-WebViewHourlyRestart` is registered by default by the mini-PC scheduler wrapper so Cloudflare keeps a fresh local target.
- `scripts/create_web_view_startup_shortcut.ps1` remains a logon fallback. The Startup shortcut starts only the `web-view` runner at logon; it must not point to `admin-gui`.
- On this mini PC, the Startup shortcut was created at `2026-05-17 18:00 KST`, and a follow-up external smoke for `https://web-view.example.invalid` returned issue count `0`.

Current important behavior:

- daily summary notification filters default to `2+` reports and target-price required
- intraday alert first page uses `7` stock blocks
- Telegram supports `다음`, `전부`, `처음`, `/종목검색`, `/종목코드`, `/메모`, `/도움말`, `/명령어`
- `admin-gui` is a local control-capable page, not a shared user page
- `web-view` exists as a separate GET-only user page and is the only candidate for future friend-facing sharing
- Broad ETF/flow product ingest is not enabled; KRX P1/P2 field validation and first snapshot/query paths exist, investor-flow Stage 4/5 validation is complete, and Stage 6 first design exists. The only scheduled Data Marketplace flow path is the narrow anchor-day mentioned-stock `[12009]` 31-day 보강 task.
- Docker is not part of the current Windows N100 plan; keep direct Python execution and Windows Task Scheduler unless the host changes to Linux/VPS or a multi-service deployment.

## Remote Access Candidate Notes

Keep the initial candidate set narrow:

| Candidate | Use | Decision note |
| --- | --- | --- |
| Tailscale | Owner-only remote access to the mini PC and local services. | Good first option for personal remote checking/control after migration. Friend access may require too much onboarding. |
| Cloudflare Tunnel | Shareable URL candidate for read-only `web-view`, mapped only to the local web-view port `{LOCAL_WEB_VIEW_TARGET}`. | Domain purchase, provider binding, and final smoke for `https://web-view.example.invalid` are done. Keep the local `access-code` gate enabled, keep any provider allow-list/Access policy in place, and do not map `admin-gui`. |
| Docker | Not used for the current Windows N100 deployment. | Defer until Linux/VPS, repeated multi-host deployment, Postgres/service split, or similar operational pressure appears. |

Do not expose `admin-gui` through a public URL.
Avoid direct router port forwarding by default.
Before any external URL is shared, confirm `python -m stock_monitor access-code status` reports enabled, review `python -m stock_monitor external-web-view-sharing-plan --json`, then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL -PythonExe .\.venv\Scripts\python.exe` against the final provider URL.

## Before Copy Checklist

Run from the current desktop before creating the migration archive:

```powershell
cd {PROJECT_ROOT}

python -m pytest -q
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag before_mini_pc_migration
python -m stock_monitor mini-pc-preflight --require-backup --require-env --require-mini-pc-profile
python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20
python -m stock_monitor web-view-browser-smoke --stock-limit 20
python -m stock_monitor ops-readiness --recent-business-days 4 --stock-limit 20 --json
python -m stock_monitor operator-status --json --health-exit
```

Equivalent bundled check. This also runs `db-restore-smoke` against the latest `data/backups/stock_monitor_*.db` backup unless `-SkipRestoreSmoke` is explicitly used:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_mini_pc_readiness.ps1 -RequireMiniPcProfile
```

If the current shell cannot read Task Scheduler metadata because it is not elevated, rerun from an administrator PowerShell or use `-SkipOperatorStatus` only for a local file/DB/package check:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_mini_pc_readiness.ps1 -SkipOperatorStatus
```

Use `-SkipRestoreSmoke` only when the latest backup was already smoke-tested in the same migration session.

Interpretation:

- `operator-status --health-exit` can fail if Task Scheduler still reports an old failed result, but the cause must be understood and recorded before migration.
- `web-view-value-qa` may warn about documented non-blocking public-surface gaps. On the current mini PC, the only warning is unresolved stock code `351020` with no KRX metadata mapping. Same-date KRX snapshot availability warnings are acceptable only when the KRX Open API also returned no rows for that latest date.
- `web-view-browser-smoke` is the local desktop/mobile browser gate for the read-only user page. It must keep the smoke server on `127.0.0.1`, check that write methods stay blocked, and confirm `/api/status` remains unavailable.
- After moving a new web-view build to the mini PC, restart through `scripts/restart_web_view.ps1`, then run `python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json` and `python -m stock_monitor web-view-browser-smoke --stock-limit 20 --json`. The browser smoke now also checks the `장중 거래대금 확인` button and the `Naver 장중 참고` overlap panel in the observation tab; it remains read-only and does not send Telegram or register scheduler tasks.
- Do not proceed if `db-verify` reports integrity, migration, duplicate, or category quality issues.
- `mini-pc-preflight --require-backup --require-env --require-mini-pc-profile` checks DB readiness, latest backup presence, required scheduler script files, required project/canonical handoff files, required user web-view/rotation assets, Telegram/KRX environment presence without printing secret values, expected scheduler task names, `operation_profile=mini-pc`, and the KRX Data Marketplace scope boundary.
- `mini-pc-preflight --require-access-code --require-backup --require-env` should be reserved for the external-sharing preflight because access-code is not required for local-only migration.

## Files To Carry

Carry the whole project folder unless a later cleanup says otherwise.

Must include:

- `src/`
- `tests/`
- `scripts/`
- `docs/`
- `data/stock_monitor.db`
- `AGENTS.md`
- `README.md`
- `CHANGELOG.md`
- `pyproject.toml`
- `.env.example`
- local `.env` if intentionally migrating secrets

Recommended sensitive handling:

- Do not paste Telegram bot token into chat.
- Prefer editing `.env` directly on the mini PC.
- If copying `.env`, treat the migration zip as sensitive.

## Migration Archive Command

Run from the project folder after the before-copy checks pass:

```powershell
cd {PROJECT_ROOT}
.\scripts\create_migration_archive.ps1
```

Default behavior:

- runs `mini-pc-preflight --require-backup --require-env` first on the source desktop; add `--require-mini-pc-profile` only on the target mini PC after setting `operation_profile=mini-pc`
- includes `data/stock_monitor.db`
- excludes `.env`
- always excludes `data/access_code.json`; set a fresh entry code on the target host with `python -m stock_monitor access-code set`
- excludes `data/backups`
- excludes `.venv`, `.pytest_cache`, `_tmp_webview`, Playwright reports, experimental virtualenvs, and webview log files
- excludes `Stock_Moniter_migration_*.zip` and matching `.zip.sha256` files so a previous migration archive is not nested into the next archive
- writes a `SHA256` sidecar at `<archive>.sha256` for transfer verification

Options:

```powershell
.\scripts\create_migration_archive.ps1 -IncludeEnv
.\scripts\create_migration_archive.ps1 -IncludeBackups
.\scripts\create_migration_archive.ps1 -DestinationPath {MIGRATION_ARCHIVE_PATH}
```

If the zip includes `.env` or `data/stock_monitor.db`, treat it as sensitive and do not upload it to public storage.
`data/access_code.json` is never included by the bundled archive script; if a manually created archive contains it, treat that archive as sensitive and replace the access-code on the target host.

Verify the archive after copying it to the target host:

```powershell
.\scripts\verify_migration_archive.ps1 -ArchivePath {MIGRATION_ARCHIVE_PATH} -FailOnSensitiveEntries
```

The command reads the adjacent `.sha256` sidecar by default and fails if the copied zip does not match.
The verifier also checks that required project entries such as `AGENTS.md`, `pyproject.toml`, `src/stock_monitor/cli.py`, `data/stock_monitor.db`, canonical docs, migration scripts, external-readiness scripts, and mini-PC scheduler scripts exist inside the zip.
Use `-FailOnSensitiveEntries` when validating a manually created archive or any archive intended for non-local transfer; it fails if `.env`, `data/access_code.json`, `data/backups`, `data/restore-smoke`, log files, or nested migration zip files appear inside the zip.

## Restore Draft

Expected target path on mini PC:

```text
{PROJECT_ROOT}
```

After extracting:

```powershell
cd {PROJECT_ROOT}

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_mini_pc_environment.ps1
```

The setup script creates or reuses `.venv`, upgrades `pip`, installs the project with dev dependencies, installs Playwright Chromium unless skipped, and runs a first bundled readiness check with the venv Python.
Because the migration archive intentionally excludes `.env` and `data/backups`, the setup-time readiness check skips the env requirement, backup requirement, and restore-smoke check by default.
Because scheduler tasks are normally not registered yet at this point, the setup script also skips the `operator-status --health-exit` readiness check by default.
After setup, create or edit `.env`, create a fresh `post-restore` backup on the mini PC, then run the full readiness check.
Run scheduler registration and scheduler verification first, then run `operator-status --json --health-exit`.

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
python -m playwright install chromium
```

If `.env` was not copied, create it after setup and before final readiness:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill at minimum:

```text
STOCK_MONITOR_TELEGRAM_BOT_TOKEN=
STOCK_MONITOR_TELEGRAM_CHAT_ID=
STOCK_MONITOR_KRX_AUTH_KEY=
```

Review before mini PC operation:

```text
STOCK_MONITOR_DB_PATH=data/stock_monitor.db
STOCK_MONITOR_TASK_PREFIX=StockMonitor
STOCK_MONITOR_POLL_START_TIME=08:30
STOCK_MONITOR_POLL_END_TIME=16:30
STOCK_MONITOR_RUN_SUPPRESSED_DATES=
STOCK_MONITOR_ACCESS_CODE_PATH=data/access_code.json
```

Optional only when running the approved anchor-day mentioned-stock `[12009]` investor-flow backfill:

```text
STOCK_MONITOR_KRX_DATA_MARKET_ID=
STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD=
```

Do not copy `.env` through the migration archive. Enter these values directly on the target PC, set the always-on app profile with `python -m stock_monitor operator-settings set operation_profile mini-pc --reason mini_pc_always_on_profile --confirm`, then run `python -m stock_monitor mini-pc-preflight --require-backup --require-env --require-mini-pc-profile` so required Telegram/KRX settings and the mini PC profile are checked without printing secrets.

## First Verification Commands

Run inside the activated venv:

```powershell
python -m pytest -q
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag post-restore
python -m stock_monitor db-restore-smoke data\backups\stock_monitor_YYYYMMDD_HHMM_post-restore.db
python -m stock_monitor operator-control explain-date 2026-06-02 --json
python -m stock_monitor mini-pc-preflight --require-backup --require-env --require-mini-pc-profile
python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20
python -m stock_monitor web-view-browser-smoke --stock-limit 20
python -m stock_monitor operator-status --json
python -m stock_monitor operator-status --json --health-exit
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_market_day_observation.ps1 -PythonExe .\.venv\Scripts\python.exe
```

Notes:

- `operator-status --health-exit` may return exit code `3` if Windows Task Scheduler tasks are not registered yet.
- That is expected before scheduler registration.

## Scheduler Registration Draft

Register Windows Task Scheduler jobs after environment verification.

For the always-on mini PC profile, use the wrapper that skips the desktop validation shutdown task:

```powershell
$pythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe $pythonExe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe $pythonExe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_market_day_observation.ps1 -PythonExe $pythonExe
```

In mini PC default mode, `verify_task_scheduler_registration.ps1` fails if `StockMonitor-Shutdown` is still registered. That is intentional: the always-on mini PC profile should not keep the desktop validation shutdown task.

Desktop validation equivalent, if scheduled shutdown is intentionally desired:

```powershell
$pythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_task_scheduler_tasks.ps1 -PythonExe $pythonExe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe $pythonExe -IncludeShutdown
```

Then check:

```powershell
python -m stock_monitor operator-status --json
```

## Source Desktop Cutover

Do not let the old desktop and the mini PC run Stock Monitor automation at the same time.
After the mini PC scheduler tasks are registered and verified, disable the source desktop scheduler tasks.

Preview on the old desktop:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\disable_source_desktop_scheduler_tasks.ps1 -DryRun
```

Disable on the old desktop only after the mini PC is verified:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\disable_source_desktop_scheduler_tasks.ps1 -ConfirmDisable
```

This calls `python -m stock_monitor scheduler-control disable --task all --confirm`.
It is intentionally separate from mini PC registration so the operator can verify the new host before disabling the old one.

Expected scheduler task names in normal operation:

- `StockMonitor-Notify`
- `StockMonitor-Poll`
- `StockMonitor-MarketBriefingMood`
- `StockMonitor-MarketBriefingLunch`
- `StockMonitor-MarketBriefingPreclose`
- `StockMonitor-TossCloseSnapshot`
- `StockMonitor-TelegramCommands`
- `StockMonitor-WebViewHourlyRestart`

Desktop validation-only task:

- `StockMonitor-Shutdown`

Legacy KRX scheduler names are intentionally absent. Use the historical sections below only for an explicitly approved recovery/reference task; do not re-register them as an opt-in mini-PC path.

When using a virtual environment, always pass the explicit venv Python path through `-PythonExe`.
Do not rely on a generic `python` PATH lookup for unattended Task Scheduler jobs.

Web-view restart policy:

- `register_mini_pc_scheduler_tasks.ps1` registers `StockMonitor-WebViewHourlyRestart` by default.
- The default trigger is hourly, starting at `00:05`.
- The task must run `scripts/restart_web_view.ps1` and keep the server bound to `{LOCAL_WEB_VIEW_TARGET}`.
- A healthy run should leave `/health` returning `200 ok` and `verify_task_scheduler_registration.ps1` showing `restart_web_view.ps1` for the task action.

Mini PC shutdown policy:

- `register_mini_pc_scheduler_tasks.ps1` intentionally does not register `StockMonitor-Shutdown`.
- If `verify_task_scheduler_registration.ps1` reports that `StockMonitor-Shutdown` is already registered by a desktop-style command, disable it before leaving the mini PC unattended:

```powershell
python -m stock_monitor scheduler-control disable --task shutdown --dry-run
python -m stock_monitor scheduler-control disable --task shutdown --confirm
```

## Admin GUI Draft

Local operator page:

```powershell
python -m stock_monitor admin-gui
```

No browser auto-open:

```powershell
python -m stock_monitor admin-gui --no-open
```

Boundary:

- Keep `admin-gui` local/private.
- Do not expose `admin-gui` directly to friends or the public internet.
- Friend/user sharing should use the separate `web-view`, GET-only, and not reuse admin `/api/status`.
- If Cloudflare Tunnel is used later, point it only to the local `web-view` port, not the admin GUI port.

User web-view draft:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress <loopback-host> -Port <web-view-port>
```

Hourly restart helper:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\restart_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress <loopback-host> -Port <web-view-port>
```

Cloudflare Tunnel target candidate:

```text
HTTP -> {LOCAL_WEB_VIEW_TARGET}
```

External sharing preflight:

```powershell
python -m stock_monitor access-code status
python -m stock_monitor external-web-view-sharing-plan --json
python -m stock_monitor mini-pc-preflight --require-access-code --require-backup --require-env
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_external_web_view_readiness.ps1 -PythonExe .\.venv\Scripts\python.exe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress <loopback-host> -Port <web-view-port>
python -m stock_monitor web-view-startup-fallback-check --json
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_next_phase_closeout.ps1 -PythonExe .\.venv\Scripts\python.exe -Date YYYY-MM-DD
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL -PythonExe .\.venv\Scripts\python.exe
python -m stock_monitor external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json
```

Cloudflare Tunnel connection sequence:

1. Confirm `python -m stock_monitor access-code status` reports enabled.
2. Run `python -m stock_monitor external-web-view-sharing-plan --json` to print the read-only operator sequence without changing Cloudflare, scheduler state, DB state, or secrets.
3. Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_external_web_view_readiness.ps1 -PythonExe .\.venv\Scripts\python.exe` before touching the provider.
4. Start only the user page locally through the safe wrapper: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress <loopback-host> -Port <web-view-port>`.
5. In Cloudflare, point the public hostname only to `{LOCAL_WEB_VIEW_TARGET}`.
6. Do not map the hostname, tunnel, or any fallback route to `admin-gui`, `/api/status`, scheduler, settings, DB, `.env`, Telegram, or shell/control endpoints.
7. Keep Cloudflare Access or an equivalent allow-list enabled before sharing the URL.
8. Register or verify `StockMonitor-WebViewHourlyRestart` so the local tunnel target is refreshed hourly.
9. Verify only the provider origin with `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL`; do not pass a path, query, fragment, localhost URL, or HTTP URL.
10. Share the URL only after the wrapper records provider-smoke success and `next-phase-readiness` no longer lists the external provider smoke as blocked.

Required external sharing state:

- Access-code gate is enabled before a URL is shared.
- Tunnel target is only the `web-view` port, normally `{LOCAL_WEB_VIEW_TARGET}`.
- The local `web-view` process stays bound to `127.0.0.1`. Non-loopback binding requires `--allow-non-loopback` and should not be the default sharing path.
- `admin-gui` remains local/private and is not tunneled.
- No raw router port forwarding is used as the default exposure path.
- The public page remains read-only; `POST`, `PUT`, `PATCH`, and `DELETE` data routes stay blocked.
- The app entry-code cookie is `HttpOnly`, `SameSite=Lax`, and gains `Secure` when Cloudflare or another HTTPS proxy sends the usual forwarded HTTPS headers.
- `mini-pc-preflight --require-access-code --require-backup --require-env --require-mini-pc-profile` checks app-side prerequisites only.
- `external-web-view-sharing-plan --json` is the focused read-only plan command for Cloudflare/Tailscale sharing. It repeats the allowed `web-view` target, forbidden `admin-gui` boundary, required provider controls, smoke routes, and next commands without configuring a provider.
- `verify_external_web_view_readiness.ps1` also runs the public-safe web-view value QA, the local browser/mobile smoke gate, and prints the required tunnel target.
- `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL` is the post-provider wrapper. It rejects HTTP, localhost/loopback, and path/query/fragment URLs, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless skipped, runs `external-web-view-smoke --record-success`, and then reruns `next-phase-readiness`.
- `external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json` is the final provider URL check after Cloudflare/Tailscale is configured. Pass only the provider origin, such as `https://view.example.com`, with no path, query, or fragment. It does not accept or print the access-code; unauthenticated `401`/`403` or a recognizable Cloudflare Access HTML/login page for protected user routes is acceptable, but `/api/status` must be absent or blocked and write methods must not be public. `--record-success` writes a non-secret operation event only if the smoke has zero issues against a non-loopback HTTPS provider origin; this is the evidence used by `next-phase-readiness.external_web_view_provider_smoke`.
- `web-view-startup-fallback-check --json` verifies the current-user `{WEB_VIEW_STARTUP_SHORTCUT}` Startup fallback and local `/health` without changing Cloudflare or exposing secrets. After a real Windows logon/reboot check, run `python -m stock_monitor web-view-startup-fallback-check --record-success --json` to record the non-secret Startup fallback observation used by `next-phase-readiness.web_view_startup_fallback`.
- `verify_next_phase_closeout.ps1 -Date YYYY-MM-DD` is the final repeatable closeout wrapper. It combines DB verification, Startup fallback health, optional `-RecordStartupFallbackSuccess`, operator health, scheduler registration verification, market-day observation, direct `observation-summary-audit` feature-availability review, direct `observation-reaction-distribution` reaction-window coverage review, direct `candidate-evidence-readiness` target-progress review, direct `market-briefing-readiness` phone-readability/scheduling-gate review, direct web-view value QA, direct web-view browser smoke, direct external web-view sharing plan review, direct category snapshot status/plan review, direct rotation mapping audit, direct KRX baseline analysis, and `next-phase-readiness` without sending Telegram, registering tasks, configuring Cloudflare, fetching live KRX data, or exposing `admin-gui`. The reaction-distribution command can derive the stored summary baseline when dates are omitted, so the wrapper does not hardcode the current report range; `-Date` is only for market-day observation, while rotation mapping uses its own latest stored-date default.
- If a response body also looks like `admin-gui`, admin markers win over Cloudflare Access wording and the provider smoke must fail.
- The actual Cloudflare/Tailscale tunnel target and allow-list must still be verified in the tunnel provider UI.

## Telegram Smoke Draft

After `.env` is ready:

```powershell
python -m stock_monitor telegram-get-updates
python -m stock_monitor send-test-notification --message "Stock Monitor mini PC migration test"
python -m stock_monitor process-telegram-commands
```

Expected:

- Telegram test message arrives.
- If a command was sent to the bot, `process-telegram-commands` replies and advances update id.

## DB Safety Checks

Read-only checks:

```powershell
python -m stock_monitor db-verify
```

Before future ETF/flow schema work:

- run `python -m stock_monitor db-backup --tag pre-migrate`
- test migrations against the copy first
- do not run schema experiments directly on the production DB

Current DB retention/backup policy:

| Item | Policy |
| --- | --- |
| Core source data | Keep `reports` and delivery safety state. Do not cleanup yet. |
| Derived summaries | Rebuild from `reports` when needed. |
| KRX snapshots | Keep 6 months; use 3 months as default flow window. |
| KRX missing backfill | Use [data-governance.md](/docs/codex/data-governance.md) before migration. Normal operation uses 5-date batches; migration rebaseline may use 10-date batches only after backup, dry-run review, and `--allow-large-batch`. |
| Backup cadence | Twice daily target after automation: after the early KRX retry window and around `16:35`. Manual backup before migration/backfill/cleanup. |
| Backup pruning | Keep at least 30 recent backups initially; prune only after `--dry-run` review. |
| Restore smoke | Use `python -m stock_monitor db-restore-smoke <backup.db>` to verify a backup copy without touching production DB. |
| Cleanup command | Use `python -m stock_monitor db-cleanup --dry-run --retention-days 183` first. Actual deletion requires `--confirm` when rows are affected. |
| VACUUM | Use `python -m stock_monitor db-vacuum --dry-run` monthly or after large cleanup. Actual VACUUM requires `--confirm`; do not run it weekly by default. |

## Mini PC Operation Profile Decisions

Before leaving the mini PC unattended, decide and record:

| Decision | Default |
| --- | --- |
| `StockMonitor-Shutdown` | Disable for always-on mini PC operation unless desktop-style shutdown is still desired. |
| `StockMonitor-KrxFlowLoginReminder` | Keep disabled except deliberate manual validation days. |
| `StockMonitor-KrxMentionedFlowBackfill` | Keep enabled only for the approved narrow `[12009]` anchor-day mentioned-stock recent 31-day path. For migration catch-up, anchor to the latest report-mentioned business date and repeat live runs only until dry-run reports `planned_call_count: 0`. |
| `StockMonitor-WebViewHourlyRestart` | Keep enabled on the mini PC so the Cloudflare `web-view` target is refreshed hourly. |
| External URL | Do not create until web-view access-code gate is enabled and `admin-gui` exposure is confirmed absent. |
| Broad KRX Data Marketplace ingest | Do not enable. |

## New Codex Session Briefing

Paste this into the new mini PC Codex session:

```text
{PROJECT_ROOT} only.
This is the Stock Monitor project moved from the desktop to the mini PC.
Read AGENTS.md, docs/codex/operating-guide.md, docs/codex/operating-guide.md, docs/codex/surface-guide.md, docs/codex/mini-pc-runbook.md, docs/codex/data-governance.md, docs/codex/data-governance.md, and CHANGELOG.md first.

Current operating contract:
- Notify: 08:20 KST after KRX daily backfill, production send allowed only 08:00~08:30 unless --allow-late.
- Poll: 08:30~16:30 every 30 minutes on Korean business days.
- Telegram command worker: 08:00~16:30, 1-minute loop; KIND official sidecar/circuit-breaker confirmation check runs within the same worker from 09:00~15:30.
- KRX Open API daily retry: StockMonitor-KrxDailyBackfill checks previous-business-day/recent missing stock/ETF/index snapshots at 08:10 on Korean business days, after the officially confirmed next-business-day 08:00 publication window.
- Web-view hourly restart: StockMonitor-WebViewHourlyRestart refreshes only {LOCAL_WEB_VIEW_TARGET} every hour.
- Shutdown: desktop validation only. For mini PC always-on operation, use scripts/register_mini_pc_scheduler_tasks.ps1 so StockMonitor-Shutdown is not registered.

Do not expose admin-gui publicly.
admin-gui is local control-capable.
The separate GET-only web-view exists. Keep it read-only and expose only that surface if remote sharing is added later. Its default load is stored-data based; the manual current-business-day `장중 거래대금 확인` button may fetch Naver `priceTop` only as `Naver 장중 참고` and must not write DB rows, send Telegram, alter scheduler state, or replace KRX official stored values.
Reports are preserved as original Naver history. KRX market reference data may have been rebaselined in reviewed 10-business-date batches before migration.

First actions:
1. Check .env exists and does not need secrets pasted into chat.
2. If this was copied as a zip, run .\scripts\verify_migration_archive.ps1 -ArchivePath <zip path> -FailOnSensitiveEntries before extracting or before trusting the copied artifact.
3. Run powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_mini_pc_environment.ps1 if the target venv is not already prepared.
4. Create or edit .env on the target host; do not paste secrets into chat.
5. Run pytest -q.
6. Run python -m stock_monitor operator-status --json.
7. Run python -m stock_monitor db-verify.
8. Run python -m stock_monitor db-backup --tag post-restore so the target host has its own first backup.
9. Run python -m stock_monitor operator-settings set operation_profile mini-pc --reason mini_pc_always_on_profile --confirm, then python -m stock_monitor mini-pc-preflight --require-backup --require-env --require-mini-pc-profile.
10. Run python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 and python -m stock_monitor web-view-browser-smoke --stock-limit 20.
11. Or run powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_mini_pc_readiness.ps1 from an administrator PowerShell to execute the main verification set. Before scheduler registration, use -SkipOperatorStatus or rely on setup_mini_pc_environment.ps1, which already skips env, backup, and operator-status checks by default.
12. If scheduler tasks are missing, prefer powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe .\.venv\Scripts\python.exe.
13. After registering, run powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe .\.venv\Scripts\python.exe.
14. Confirm StockMonitor-Shutdown is not registered or is disabled for always-on mini PC operation.
15. If external sharing is needed, expose only web-view after access-code status is enabled.
```

## Open Migration Questions

| Question | Current Default |
| --- | --- |
| Should `StockMonitor-Shutdown` stay enabled on mini PC? | Probably no for always-on operation. |
| Should DB be copied with all history? | Yes, unless a clean start is explicitly desired. |
| Should `.env` be copied directly? | Acceptable only if the zip is treated as sensitive. |
| Should KRX/KIS keys be added before migration? | KRX key exists locally; copy only through a sensitive `.env` handoff. KIS remains future work. |
| Should web-view be exposed remotely? | Possible later through Cloudflare Tunnel, but only the GET-only `web-view`, not `admin-gui`. |


<!-- Merged from: docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md -->
## Weekly Mini PC Sync Guide

미니PC에서 생긴 코드/문서/테스트 변경을 본컴 소스 기준으로 주간 동기화하기 위한 행동지침입니다.

## 목적

- 미니PC는 실운영 기준이다.
- 본컴은 소스 정리, 검토, 백업, 다음 개발 기준이다.
- 미니PC 변경은 주 1회 또는 큰 수정 후 본컴으로 가져와 검토 반영한다.
- 운영 데이터와 비밀값은 코드 동기화 대상이 아니다.
- 이 채팅/작업 위치가 미니PC일 때 `handoff/mini_pc_changes/`는 본컴으로 넘길 변경 묶음을 정리하는 outbound 위치다.

## 미니PC에서 매주 작성할 파일

권장 파일명:

```text
mini-pc-sync-YYYY-MM-DD.md
```

권장 위치:

```text
handoff/mini_pc_changes/
```

## 작성 양식

```markdown
## Mini PC Sync - YYYY-MM-DD

## 1. 요약

- 이번 주 변경 목적:
- 운영 중 발견한 문제:
- 최종 상태:

## 2. 일자별 변경 내역

| 날짜 | 변경 내용 | 이유 |
| --- | --- | --- |
| YYYY-MM-DD |  |  |

## 3. 일자별 변경 파일

| 날짜 | 파일 | 변경 성격 |
| --- | --- | --- |
| YYYY-MM-DD | `src/...` | 코드 / 테스트 / 문서 / 스크립트 |

## 4. 예상했던 조치 후 나아진 점

| 조치 | 기대 효과 | 실제 확인 |
| --- | --- | --- |
|  |  |  |

## 5. 패치 후 생길 수 있을 법한 문제

| 위험 | 영향 | 확인/완화 방법 |
| --- | --- | --- |
|  |  |  |

## 6. 검증 결과

| 명령 | 결과 |
| --- | --- |
| `python -m pytest -q` |  |
| `python -m stock_monitor db-verify` |  |
| `python -m stock_monitor operator-status --json --health-exit` |  |
| `python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20` |  |

## 7. 본컴 반영 필요 파일

```text
AGENTS.md
README.md
CHANGELOG.md
docs/codex/...
src/stock_monitor/...
tests/...
scripts/...
```

## 8. 본컴 반영 제외

```text
.env
data/access_code.json
data/stock_monitor.db
data/backups/*.db
.venv/
.pytest_cache/
Stock_Moniter_migration_*.zip
Stock_Moniter_migration_*.zip.sha256
```

## 9. 특이사항

- access-code, Telegram token, KRX key, password, cookie, DB backup 원본은 기록하지 않는다.
- DB 상태를 전달해야 하면 row count, 날짜 범위, backup 파일명, SHA256만 기록한다.
```

## 압축 파일 기준

미니PC에서 본컴으로 가져올 zip은 source/code/test/docs/script 변경만 포함합니다.

포함 가능:

- `AGENTS.md`
- `README.md`
- `CHANGELOG.md`
- `.env.example`
- `pyproject.toml`
- `docs/`
- `src/`
- `tests/`
- `scripts/`
- `example/Cycle.jpg`
- `data/rotation_*.json`
- `handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md`

제외:

- `.env`
- `data/access_code.json`
- `data/stock_monitor.db`
- `data/backups/`
- `data/restore-smoke/`
- `*.log`
- `.venv/`
- `.pytest_cache/`
- `Stock_Moniter_migration_*.zip`
- `Stock_Moniter_migration_*.zip.sha256`
- Telegram/KRX/access-code/password/cookie 같은 비밀값

## 본컴에서 받을 때 처리 순서

1. `handoff/mini_pc_changes/`에 zip과 sync markdown을 둔다.
2. 압축을 임시 폴더에 푼다.
3. 파일별 diff를 확인한다.
4. 실제 본문 파일에 선택 반영한다.
5. focused tests를 먼저 돌린다.
6. 전체 `python -m pytest -q`를 돌린다.
7. canonical 문서와 `CHANGELOG.md`를 현행화한다.
8. 필요하면 본컴에서 다시 미니PC 반영용 patch zip을 만든다.

## 판단 기준

- 미니PC 운영 중 수정된 내용이 항상 정답은 아니다. 본컴 반영 전 테스트와 canonical 문서 기준으로 검토한다.
- DB/운영 데이터는 source sync가 아니라 별도 backup/restore 정책으로 다룬다.
- 외부공유, access-code, admin-gui 노출, KRX broad ingest, public numeric 점수화, 투자등급, 매수·매도 신호, 매매 추천 관련 변경은 본컴 반영 전 별도 검토가 필요하다. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위` 같은 관찰 후보 추천 문구는 canonical 허용 경계에 맞는지 확인한다.


<!-- Merged from: docs/codex/weekly-sync/WEEKLY_SYNC_PROMPT.md -->
## Weekly Mini PC Sync Prompt

아래 프롬프트를 미니PC 쪽 Codex 세션에 붙여 넣어 주간 변경 묶음을 만들 때 사용한다.

```text
{PROJECT_ROOT}만 기준으로 작업해줘.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 판단해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

이번 작업 목표는 “이번 주 미니PC에서 생긴 변경점을 본컴 소스와 맞추기 위한 sync 묶음으로 정리”하는 것이다.

먼저 handoff/mini_pc_changes/WEEKLY_SYNC_GUIDE.md를 읽고, 그 양식에 맞춰 아래 파일을 작성해줘.

작성 파일:
handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md

반드시 포함할 내용:
1. 일자별 변경 내역
2. 일자별 변경 파일
3. 예상했던 조치 후 나아진 점
4. 패치 후 생길 수 있을 법한 문제
5. 검증 결과
6. 본컴 반영 필요 파일
7. 본컴 반영 제외 파일

변경 파일 판단 기준:
- source/code/test/docs/script 변경만 포함
- 운영 DB, backup, .env, access-code, token/key/password/cookie는 제외
- DB 상태를 설명해야 하면 row count, 날짜 범위, backup 파일명, SHA256만 기록

가능하면 아래 명령으로 현재 상태를 확인해줘.

python -m pytest -q
python -m stock_monitor db-verify
python -m stock_monitor operator-status --json --health-exit
python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20

그 다음 mini-pc-sync-YYYY-MM-DD.md의 “본컴 반영 필요 파일” 목록 기준으로 source/code/test/docs/script 파일만 zip으로 묶어줘.

압축 파일명:
handoff/mini_pc_changes/mini_pc_sync_YYYY-MM-DD.zip

SHA256 파일명:
handoff/mini_pc_changes/mini_pc_sync_YYYY-MM-DD.zip.sha256

zip 포함 가능:
- AGENTS.md
- README.md
- CHANGELOG.md
- .env.example
- pyproject.toml
- docs/
- src/
- tests/
- scripts/
- example/Cycle.jpg
- data/rotation_*.json
- handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md

zip 제외:
- .env
- data/access_code.json
- data/stock_monitor.db
- data/backups/
- data/restore-smoke/
- *.log
- .venv/
- .pytest_cache/
- Stock_Moniter_migration_*.zip
- Stock_Moniter_migration_*.zip.sha256
- Telegram token
- KRX key
- password
- cookie
- access-code material

주의:
- public numeric 점수/투자등급/매수·매도 신호/매매 추천이 섞인 변경은 별도 위험으로 표시해. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위` 같은 관찰 후보 추천 문구는 허용 경계 안에서 검토해.
- admin-gui 외부 노출, 0.0.0.0 바인딩, Cloudflare tunnel target 변경은 별도 위험으로 표시해.
- KRX Data Marketplace broad ingest 관련 변경은 별도 위험으로 표시해.
- 미니PC 운영 중 임시로 고친 내용이라도 본컴 반영 전 검토가 필요하므로 “왜 바꿨는지”를 반드시 적어.

최종 보고:
핵심 변경:
- 작성한 sync 문서
- 생성한 zip/sha256 경로

검증:
- 실행한 명령과 결과

남은 작업:
- 본컴에서 확인해야 할 diff/주의사항
```
