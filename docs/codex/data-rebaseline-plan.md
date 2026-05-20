# Data Rebaseline Plan

## Purpose

This document explains why and how the project will refresh non-report data before moving to the future mini PC.

The goal is not to erase the MVP history.
The goal is to separate:

- early validation data used to prove KRX/API/screen behavior
- operating reference data that should move to the mini PC

## Decision

Keep report and delivery data as the durable project history.

Rebuild or extend market-reference data as needed because it is reproducible from approved sources.

| Data Area | Mini PC Migration Policy | Reason |
| --- | --- | --- |
| `reports` | Keep | Naver report rows are source history and dedupe evidence. |
| `daily_stock_summaries` | Keep, rebuildable | Derived from reports; useful for current web-view/archive continuity. |
| delivery/run/fragment logs | Keep | Needed to explain Telegram send state and replay safety. |
| operation events | Keep | Useful for migration/debug history unless noise becomes a problem later. |
| KRX stock/ETF/index daily snapshots | Rebuild/extend by date | Reproducible reference data; safe to upsert missing dates. |
| KRX stock master | Refresh latest before migration | Good candidate to become stock master/search reference. |
| KRX investor-flow rows | Keep current validated samples; extend only through staged flow process | Broad scheduled ingest remains disabled. The narrow anchor-date report-mentioned `[12009]` recent 31-day backfill is the only automatic exception. |
| 업종/테마 snapshots | Rebuild/extend slowly by source date | Current taxonomy is not KRX-owned and should not be silently copied backward. |

## Current Baseline

As of `2026-05-15`:

| Area | State |
| --- | --- |
| DB integrity | `db-verify` passes. |
| Schema | `5/5`, no pending migrations. |
| KRX daily snapshot range | `2024-11-08` through `2026-05-14` for stock/ETF/index daily endpoints. |
| Next KRX daily backfill candidate | `2026-05-15` only, pending normal latest-day Open API publication. |
| Category snapshot status | 90 summary dates, 6 sector-dated dates, 7 theme-dated dates, 84 fallback dates. |
| Investor-flow validation | Stage 4 complete for two dates; Stage 5 read-only display exists; broad scheduled ingest disabled. The narrow anchor-date report-mentioned `[12009]` recent 31-day backfill is the only automatic exception. |

## Rebaseline Strategy

Use the scheduled `08:10` KRX daily backfill for the newest previous-business-day gap, after the officially confirmed next-business-day `08:00` publication window.
Use the manual rolling rebaseline process only for repairs or future migration checks.

The current operator-approved execution order is:

1. KRX daily market-reference latest-day check and repair-only rebaseline.
2. Category snapshot fallback reduction.
3. User `web-view` display polish.
4. 순환매 SVG overlay first pass.
5. Detailed-doc archive cleanup.

Do not run destructive deletes as part of the normal rebaseline.
Use upsert/backfill first.
Only cleanup after the mini PC copy is verified and only if there is a specific reason.

### Standard Loop

Run this loop repeatedly:

```powershell
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag pre-krx-rebaseline
python -m stock_monitor krx-backfill-missing daily --lookback-days 183 --max-dates 10 --dry-run --allow-large-batch
python -m stock_monitor krx-backfill-missing daily --lookback-days 183 --max-dates 10 --confirm --i-backed-up --allow-large-batch
python -m stock_monitor db-verify
```

Stop when the dry-run no longer shows missing KRX daily endpoints inside the intended retention window.
The current 18-month Open API baseline is complete through `2026-05-14`; `2026-05-15` is expected to appear only after KRX publishes the latest business-day rows.

### Why `--allow-large-batch`

The default real-call guard is 5 dates.
For the rebaseline window, 10 business dates is acceptable only after:

- `db-verify` passes
- `db-backup` is created
- dry-run output is reviewed
- KRX request delay remains non-zero

## Category Rebaseline

Category data is different from KRX daily market data.

It is taxonomy data, not market-reference data.
Current source is Naver industry/theme plus operator-managed snapshots.

Current limitation:

- Existing sector catalog rows from `naver_quote` are display/cache metadata, not verified Naver `upjong` API codes.
- `refresh-industries --enabled` refreshes only sector catalog rows with `source=naver_industry` or `source=naver_upjong`.
- `naver_quote`, `operator`, and other custom sector catalog sources are not treated as Naver `upjong` API codes until separately verified.
- Theme `505` can be refreshed as a Naver theme snapshot, but broader historical category accuracy still needs a verified source-date taxonomy plan.

Use this sequence for fallback summary dates:

```powershell
python -m stock_monitor category-snapshot-status --limit 30
python -m stock_monitor category-snapshot-plan --limit 30
python -m stock_monitor refresh-industry UPJONG_CODE --snapshot-date SOURCE_DATE --dry-run
python -m stock_monitor category-catalog add sector UPJONG_CODE --name "업종명" --source naver_industry
python -m stock_monitor refresh-industries --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3
python -m stock_monitor refresh-themes --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3
```

Rules:

- Fill source-date snapshots only.
- Check `category-snapshot-plan` `plan_summary` first. If `source_date_capture_allowed_count` is `0`, do not run refresh commands for older fallback dates just to reduce the fallback count.
- Do not bulk-promote today's cache backward without explicit approval.
- Do not run `refresh-industries` or `refresh-themes` with an old `snapshot-date` just to reduce fallback counts. `category-snapshot-plan` now emits refresh commands only when the target date is the current source date; older dates should remain labeled as latest stored category classification unless separately verified.
- Do not use `naver_quote` sector keys as Naver `upjong` API keys.
- Do not use `operator` or custom sector catalog keys for batch refresh unless they are re-added with a verified Naver source label.
- Validate any newly proposed Naver upjong code with `refresh-industry UPJONG_CODE --dry-run` before adding it to the enabled sector catalog or running a confirmed snapshot refresh. The dry-run output prints the next `category-catalog add sector ... --source naver_industry` command when the code returns a usable industry name and membership count.
- Keep user-facing labels as `업종`, `테마`, and `카테고리`.
- Do not call current category data `KRX 업종/테마`.

## KRX Stock Master Refresh

Before mini PC migration, refresh latest KRX stock master separately from daily snapshots:

```powershell
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date YYYY-MM-DD --dry-run
python -m stock_monitor krx-fetch-snapshot stock-kosdaq-basic --date YYYY-MM-DD --dry-run
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date YYYY-MM-DD
python -m stock_monitor krx-fetch-snapshot stock-kosdaq-basic --date YYYY-MM-DD
```

Use the most recent confirmed KRX business date.

## Migration Explanation For Future Codex Sessions

If a future mini PC session asks why data looks this way:

- Reports were kept because they are original Naver research collection history.
- KRX daily market data was expanded later in bounded batches because it is reproducible reference data.
- Category snapshots were not blindly backfilled because industry/theme membership is a taxonomy layer and historical labels can drift.
- Broad investor-flow scheduled ingest was intentionally not enabled. Current flow rows came from validated staged samples/manual import plus the narrow anchor-date report-mentioned `[12009]` recent 31-day automatic backfill lane.

## Completion Criteria

The rebaseline is ready for migration when:

- `db-verify` passes.
- KRX daily snapshots cover the intended 18-month observation window. Current status: covered from `2024-11-08` through `2026-05-14`; `2026-05-15` is the normal latest-day pending candidate.
- The latest KRX stock master is refreshed.
- Category fallback dates are either filled with source-date snapshots or explicitly accepted as fallback.
- A final `db-backup --tag pre-mini-pc-migrate` exists.
- `docs/codex/mini-pc-migration-handoff.md` points to this plan.
