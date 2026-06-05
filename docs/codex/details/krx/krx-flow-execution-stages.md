# KRX Flow Execution Stages

This document fixes the execution stages for KRX Data Marketplace investor-flow expansion.
Use these stage numbers when requesting work, for example: `Stage 2까지 진행` or `Stage 4까지 밀어`.

## Current Rule

Scheduled KRX Data Marketplace ingest remains disabled even after Stage 4/5 validation.
Stage 6 first design exists, but actual scheduled ingest enablement requires separate explicit approval.

Current status:

| Item | Status |
| --- | --- |
| `2026-05-08` Stage 1 | Done. Raw-network JSON bodies exist for 7 manifests. |
| `2026-05-08` Stage 2 | Done. Strict raw validation passed for 7 manifests. |
| `2026-05-08` Stage 3 | Done with `--allow-right-extra-top-rows`. `[12010]` raw response is a compatible superset of the visible-grid sample. |
| `2026-05-07` Stage 1 | Done. Raw-network JSON bodies exist for 7 manifests under `data\krx_samples_raw_20260507`. |
| `2026-05-07` Stage 2 | Done. Strict raw validation passed for 7 manifests. |
| `2026-05-07` Stage 3 | Done with `--allow-right-extra-top-rows`. Visible-grid baseline exists under `data\krx_samples_visible_20260507` and matches raw rows. |
| Stage 4 | Done. Two business dates have strict raw validation and visible-grid/raw parity success. |
| Stage 5 | Done. User `web-view` has a GET-only read-only investor-flow trend route and section from stored samples. |

## Stage Table

| Stage | Name | Goal | Completion Criteria |
| ---: | --- | --- | --- |
| 0 | Baseline fixed | Keep the visible-grid sample import and raw sample directory state clear. | Visible-grid samples and raw manifest/sample directories are documented, and scheduled ingest is disabled. |
| 1 | Raw response fill | Put raw-network JSON response bodies into `data\krx_samples_raw`. | All 7 raw JSON files referenced by raw manifests exist. |
| 2 | Strict raw validation | Validate raw-network samples without login, network, or DB writes. | `krx-flow-validate-samples` passes for `data\krx_samples_raw`. |
| 3 | Visible/raw parity | Compare normalized visible-grid rows and raw-network rows. | `krx-flow-compare-samples` exits successfully. |
| 4 | Repeated business-day validation | Repeat Stages 1-3 for at least 2 business days. | At least 2 dates have strict raw validation and parity success. Current validated dates: `2026-05-08`, `2026-05-07`. |
| 5 | Read-only trend view | Add investor-flow trend display to user `web-view` without scoring. | Done: `GET /api/flow-trend?date=YYYY-MM-DD` and the user page show stored-sample `수급 흐름` only. |
| 6 | Scheduled ingest design | Design scheduled ingestion candidate without enabling it. | Done as a first draft below; actual enablement requires explicit approval. |

## Stage Details

| Stage | Entry Condition | Commands / Work | Stop Condition | Next Stage |
| ---: | --- | --- | --- | --- |
| 0 | Current project state after visible-grid import. | `python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw` | Raw placeholders are missing or scheduled ingest is accidentally enabled. | Stage 1 |
| 1 | Operator has raw response bodies from KRX Data Marketplace. | Save only JSON response bodies under `data\krx_samples_raw` using the manifest `sample_file` names. Do not save cookies, headers, credentials, screenshots, or account data. | Any file includes credentials, HTML login pages, `LOGOUT`, or non-JSON content. | Stage 2 |
| 2 | All raw sample files exist. | `python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized` | Strict validation fails, required investor rows are missing, or normalized row count is suspicious. | Stage 3 |
| 3 | Raw strict validation passed. | `python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw` | Any mismatch, missing manifest, or missing normalized row appears. | Stage 4 |
| 4 | One validated date exists. | Repeat Stage 1-3 on another business date using the same capture and validation policy. | Date-specific mismatch or inconsistent unit mapping appears. | Stage 5 |
| 5 | At least 2 validated dates exist. | Add GET-only web-view trend presentation from stored investor-flow rows. Keep labels descriptive and avoid public numeric score or trading-recommendation wording. | Display requires unvalidated source fields or suggests buy/sell judgment. | Stage 6 |
| 6 | Trend display is useful and stable. | Draft scheduled ingest design with login/session handling, retry, skip-on-LOGOUT, audit event, and manual enable gate. | Any design requires exposing KRX credentials, bypassing operator session policy, or enabling scheduled ingest without approval. | Separate approval |

## Fixed Commands

```powershell
python -m stock_monitor krx-flow-raw-sample-scaffold --source-manifest-dir data\krx_samples --output-dir data\krx_samples_raw
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw --allow-right-extra-top-rows
```

## Stage 1 Raw Files

`Stage 1` is complete only when these files exist and contain raw KRX Data Marketplace JSON response bodies:

```text
data\krx_samples_raw\12008_market_STK_20260508.local.json
data\krx_samples_raw\12009_017670_20260508.local.json
data\krx_samples_raw\12009_032640_20260508.local.json
data\krx_samples_raw\12009_079550_20260508.local.json
data\krx_samples_raw\12009_278470_20260508.local.json
data\krx_samples_raw\12009_329180_20260508.local.json
data\krx_samples_raw\12010_top_STK_20260508_foreign.local.json
```

After filling them, run:

```powershell
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
```

The second validated date uses:

```powershell
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw_20260507
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw_20260507 --normalized-dir data\krx_samples_raw_20260507\normalized
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_visible_20260507 --normalized-dir data\krx_samples_visible_20260507\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples_visible_20260507 --right-manifest-dir data\krx_samples_raw_20260507 --allow-right-extra-top-rows
```

## Stage 3 Top-Ranking Superset Rule

For `[12010]` top-ranking samples, the visible-grid DOM may expose only rendered rows while the raw response can contain the full ranked list.
This is acceptable only when every visible-grid row matches the raw response as an ordered prefix.
Use `--allow-right-extra-top-rows` for Stage 3 comparison and still fail on missing rows, changed values, changed order, or extra rows on non-top screens.

## Guardrails

- Keep `reports`, `daily_stock_summaries`, KRX Open API snapshots, and KRX Data Marketplace investor-flow rows separate.
- Treat imported flow as `수급 참고`. It may support observation-candidate ordering, but not a public numeric score, trading recommendation, or confirmed rotation signal.
- Preserve source units and do not infer scaling silently.
- Prefer `.env` raw login smoke-check via `krx-flow-login-check`; use operator-managed Chrome login/session only as fallback/debug.
- Stage 5 is complete, but scheduled ingest still requires a separate Stage 6 design and explicit approval before enablement.

## Stage 6 Draft Design

Stage 6 is design-only until the operator separately approves scheduled ingest enablement.

Required ingest contract:

| Guard | Required Behavior |
| --- | --- |
| Login check | Run `.env` Data Marketplace login smoke check before fetch work. |
| LOGOUT handling | If response indicates `LOGOUT`, record a skipped/failed operation event and write no flow rows. |
| Retry | Use bounded retry only for transient fetch failures; do not retry malformed business data blindly. |
| Event recording | Record run start, skip, failure, and success with date/view/row counts. |
| Batch size | Keep stock-level `[12009]` limited to leadership-candidate or same-day report-mentioned stock/date keys, not whole-market crawling. |
| Backup/verify | Require recent `db-verify` and backup before first real scheduled ingest enablement. |
| Partial writes | Avoid partial DB writes for failed login or malformed response sets. |
| Enable gate | Task registration/enablement is outside Stage 6 design and requires explicit approval. |

## Login Handling Decision

For source validation, prefer the local `.env` Data Marketplace login path and raw HTTP fetch.
This path performs warmup, login, and data POST with an in-memory cookie jar and does not save browser cookies, headers, or credentials.
Use this smoke check before future raw capture or ingest-design work:

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

The command verifies login and a representative `[12008]` JSON endpoint without DB writes.
It returns exit code `0` only when the endpoint returns rows; missing credentials, rejected login, `LOGOUT`, fetch failure, or empty rows return exit code `2`.

Browser UI login remains a fallback/debug path only:

| Path | Decision |
| --- | --- |
| Direct `{KRX_LOGIN_FALLBACK_PATH}` tab | Preferred browser fallback. It exposes the login fields without the wrapper iframe. |
| Wrapper `MDCCOMS001.cmd` iframe | Works, but is less stable and not needed when direct login page is available. |
| Chrome saved-password/PIN/Windows Hello | Manual-only. Do not automate OS/native security prompts. |
| Browser raw network capture | Not available in the current browser automation surface. |

If duplicate-login confirmation appears, selecting confirmation can replace the existing KRX web session.
Do this only during validation.
Keep broad scheduled ingest disabled until separate approval; the narrow same-day report-mentioned `[12009]` recent 31-day backfill task is the only automatic exception.
