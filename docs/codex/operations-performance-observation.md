# Operations Performance Observation

## Purpose

Record actual Next.js web-view performance and stability on the Intel N100 Windows Operations PC after the project and operating database have been moved. This is a measurement record, not a development-PC benchmark or a production cutover approval.

## Status

**Not started — waiting for the Operations PC move and DB/WAL validation.**

No N100 CPU, memory, response-time, browser-paint, SQLite/WAL, concurrent-writer, or long-run stability measurement has been performed. Leave result fields as `Not run` until observed on that host. Do not copy development-PC results into this record.

## Entry Gate

Before collecting performance data:

- Complete the Next migration's development-PC feature/data contract checks and use the shared 14-route matrix in [Operating guide](operating-guide.md#developer-pc-api-timing-benchmark). Record any route still awaiting parity before interpreting latency.
- Confirm the Operations PC Node/Next runtime can use `node:sqlite` with a read-only connection.
- Compare representative Next DTOs against the Operations PC's existing Python public GET responses using one stable database state/date.
- Verify `query_only`, WAL sidecar behavior, and concurrent Python writes without changing the schema or making Next a writer.
- Verify Windows start, normal stop, restart, logs, and recovery on the Operations PC.
- Record the host's exact CPU model, installed memory, Windows version, Node/Python versions, app build identifier, and database snapshot time.

If an entry gate fails, stop the performance run and record the failure; do not tune around a data or runtime correctness problem.

## Measurement Procedure

1. Select representative dates and routes from the shared API matrix after checking that the underlying database snapshot is stable. Record the database file timestamp/size and WAL/SHM state without copying or printing database rows.
2. Record Python and Next builds, host load, test date, route/query, viewport, and whether the result is a cache hit, cache miss, or uncached request. Never compare different dates or source snapshots as if they were the same input.
3. From `web/`, run `npm run bench:public-get` against the existing loopback Python listener and the one Next preview. The runner uses five warm-ups, 30 sequential samples, and `Accept-Encoding: identity`; it reports the first request separately from p50/p95 and body bytes. Keep the Python 30-second response-cache behavior visible; do not mix warmed Python cache hits with Next direct SQLite reads without labeling that difference. Preserve the access-code gate and provide only an already-authorized Python session cookie through the local process environment if one is available. A `401` means the comparison was not run; never disable the gate to obtain numbers.
4. Measure representative rendered pages and browser paint separately from API time. Record desktop/mobile viewport, document errors, and any clipped or unreachable controls.
5. Capture CPU and memory for the Next process and overall host during idle, representative page reads, and Python collector/write overlap. Record sampling interval and observation window.
6. Separate SQLite statement execution plus row materialization, TypeScript DTO/UI composition, indicator calculations, and Naver/Toss provider wait. If an existing timing source cannot separate a phase, mark that phase `Not available`; do not infer it from total time.
7. Observe Python collection and SQLite writes while Next performs read-only requests. Record lock/busy/error outcomes and before/after WAL/SHM metadata. Do not interrupt an active collection or alter scheduler registration for the test.
8. Run the agreed long-run observation window, then verify normal shutdown, restart, log retention, and recovery from one controlled Next failure. Record the window and recovery commands.
9. Decide whether an optimization is warranted from the observed user-facing delay or resource constraint. Do not set an SLO or claim a speedup from these measurements alone.

## N100 API Results Matrix

**Status: Not run.** This matrix is for the Intel N100 Operations PC after the project and operating DB move. Development-PC values do not belong in the N100 columns. Run only after the entry gates above pass. Keep the five external provider rows out of automatic sampling; use the existing controlled/mock checks unless a separately authorized provider observation is needed.

| API route | Class | Python status / p50 / p95 | Next status / p50 / p95 | Response bytes | DTO / cache notes |
| --- | --- | --- | --- | --- | --- |
| `/api/archive?limit=20` | Stored | Not run | Not run | Not run | Python cache / Next direct read: not run |
| `/api/daily/{date}` | Stored default | Not run | Not run | Not run | Keep the optional Naver query out of this row |
| `/api/daily/{date}/stocks/{code}` | Stored | Not run | Not run | Not run | Same selected stock on both |
| `/api/stocks/search?date={date}&q=삼성&limit=8` | Stored | Not run | Not run | Not run | Same query and bound |
| `/api/candidate-evidence?date={date}&limit=8` | Stored | Not run | Not run | Not run | Preserve stored order and missing states |
| `/api/observation-summary?date={date}` | Stored | Not run | Not run | Not run | Builder/SQLite fixture parity passes; same-host HTTP comparison not recorded |
| `/api/observation/backtest?date={date}&limit=20&mention_threshold=2` | Stored | Not run | Not run | Not run | Builder/SQLite fixture parity passes; same-host HTTP comparison not recorded |
| `/api/market` | Stored | Not run | Not run | Not run | Stored Toss snapshot |
| `/api/intraday?date={date}` | Stored | Not run | Not run | Not run | Same historical date |
| `/api/flow-trend?date={date}&limit=5` | Stored | Not run | Not run | Not run | Stored Toss flow |
| `/api/etf-trend?date={date}&limit=5` | Stored | Not run | Not run | Not run | Preserve empty/missing state |
| `/api/rotation-overlay?date={date}&limit=5&symbols={code}` | Stored | Not run | Not run | Not run | Same date, code, and local mapping |
| `/api/category?date={date}&type=sector&display_name=반도체&public_category_id=...` | Stored | Not run | Not run | Not run | Use the exact same encoded category query |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | Stored | Not run | Not run | Not run | Descriptive trend only |
| `/api/toss-market-context?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/priority-indicators?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/toss-priority-quotes?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/toss-priority-daily-candles?date={date}&days=90` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/priority-current-quotes?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |

`/api/daily/{date}?intraday_market_top=1&market_top_limit=100&market_top_page_size=20` is a live Naver variant of the daily handler, not part of the stored default row. Do not invoke it in the standard route sweep. `/health`, the fixed image route, rendered HTML, and browser paint are recorded as separate smoke/page measurements, not mixed into this API table.

## Host And Stability Results Log

| Run | Status | Host / build | Input snapshot | Routes / viewport | CPU / memory | p50 / p95 | SQLite / assembly / indicators / providers | WAL / concurrent writes | Stability / recovery | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pending Operations PC move | Not run | Not run | Not run | Not run | Not run | Not run | Not run | Not run | Not run | Not assessed |

For each route, keep separate entries for API p50/p95 and rendered-page/browser-paint observations. Include sample count, warm-ups, cache state, body size or page dimensions, and errors in the run notes. Keep raw DB rows, credentials, tokens, cookies, and environment values out of this document.

## Acceptance And Rollback

Operating cutover requires functional/data parity, clean read-only SQLite and WAL/concurrent-writer behavior, and verified Windows restart/recovery. Performance is a separate decision based on this host's recorded observations.

If Next fails, stop the Next process and continue serving the existing Python `web-view`. Python collection, SQLite writes, scheduler, Telegram, access gate, and the existing sharing target remain the fallback; no database restore or schema rollback is part of the Next rollback.
