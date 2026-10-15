# Operations Performance Observation

## Purpose

Record actual Next.js web-view performance and stability on the Intel N100 Windows Operations PC after the project and operating database have been moved. This is a measurement record, not a development-PC benchmark or a production cutover approval.

## Status

**N100 host preflight passed; operating acceptance remains pending.**

On 2026-10-15, the current host was verified as Intel N100 / Windows 11 Pro with Node `v22.21.1` and Python `3.12.14`. Read-only `db-verify --json` passed. The active Next listener on 3010 returned `/health` 200 and `/api/archive?limit=19` returned 200 with a cache miss followed by a cache hit; its build ID `nA1XzbaTDmGe1P5hU8jIc` predates pushed commit `c01bdc9`, so exact source provenance is unverified and the smoke check is not acceptance evidence. The 2026-10-15 15:40 14-route timing is documented in [Operating guide](operating-guide.md#2026-10-15-cache-matched-exploratory-timing-intel-n100-not-acceptance), but used a temporary Python listener with a nonexistent in-memory access-code path; it is exploratory, not an authenticated Python comparison. `StockMonitor-Poll` is Ready for 2026-10-16 08:30 KST; its 2026-10-15 16:30 result was `1`. Scheduler operational history is disabled and no poll log was found. An earlier report mentioned a Next GET at 15:00:07 while Poll was Running, but did not record cache state or paired DB/WAL/SHM metadata; it does not prove a SQLite read. No verified cache-miss SQLite read during an active normal writer, authenticated Python comparison, accepted N100 route matrix, CPU/memory sample, long-run stability, or recovery result has been recorded. Leave the formal matrix as `Not run` until verified; do not copy development-PC results into it.

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
2. Record Python and Next builds, host load, test date, route/query, viewport, and whether the result is a cache hit, cache miss, or uncached request. Both services use a process-local 30-second response cache for the 14 stored routes; report cold requests separately from cache hits. The TTL starts after building and serializing the response, so a hit's response-generation `now` can be older by up to 30 seconds plus that build/serialization time; source/as-of/freshness fields remain from the stored snapshot. HTTP responses still use `Cache-Control: no-store`.
3. From `web/`, run `npm run bench:public-get` against the existing loopback Python listener and the one Next preview. The runner uses five warm-ups, 30 sequential samples, and `Accept-Encoding: identity`; it reports the first request separately from p50/p95 and body bytes. It sends `x-stock-monitor-benchmark: 1` to both origins; only Next returns `x-stock-monitor-cache: hit|miss` for that opt-in request, while Python cache state is checked in `api_perf.log`. Compare matching cache states; SQLite/DTO work occurs on misses, while hits return the serialized response. Preserve the access-code gate and provide only an already-authorized Python session cookie through the local process environment if one is available. A `401` means the comparison was not run; never disable the gate to obtain numbers.
4. Measure representative rendered pages and browser paint separately from API time. Record desktop/mobile viewport, document errors, and any clipped or unreachable controls.
5. Capture CPU and memory for the Next process and overall host during idle, representative page reads, and Python collector/write overlap. Record sampling interval and observation window.
6. Separate SQLite statement execution plus row materialization, TypeScript DTO/UI composition, indicator calculations, and Naver/Toss provider wait. If an existing timing source cannot separate a phase, mark that phase `Not available`; do not infer it from total time.
7. Observe the normal `StockMonitor-Poll` task through its scheduled window; poll task state read-only every 2 seconds from 08:29 to 09:30 and send no Next request until the task reports `Running`. While it is running, record DB/WAL/SHM metadata, then make one stored `GET /api/archive?limit=19` with `x-stock-monitor-benchmark: 1`. The validated limit is part of the semantic response-cache key. Confirm HTTP status and `x-stock-monitor-cache: miss` before counting it as a SQLite read; a cache hit does not test WAL concurrency. If it is a hit, try another valid unused limit (1–100) only while Poll is still `Running`; do not add ignored query parameters to force misses. Record Poll start/end, GET start/end, elapsed time, status, response byte count, cache state, and before/after DB/WAL/SHM metadata only. Discard the body and do not inspect DB rows. After the scheduled run ends, record its `LastTaskResult`; only result `0` counts as a successful Poll for acceptance. If it is nonzero, record failure and the available error evidence without rerunning Poll. If the Poll ends before a miss can be observed, wait for the next normal scheduled Poll; never run Poll manually or change the scheduler. If none overlaps by 09:30, record `Not run` and the next scheduled time. Record lock/busy/error outcomes and do not interrupt an active collection.
8. Run the agreed long-run observation window, then verify normal shutdown, restart, log retention, and recovery from one controlled Next failure. Record the window and recovery commands.
9. Decide whether an optimization is warranted from the observed user-facing delay or resource constraint. Do not set an SLO or claim a speedup from these measurements alone.

## N100 API Results Matrix

**Status: Formal acceptance matrix not run.** This matrix records the full authenticated 14-route comparison on the Intel N100 host after the entry gates above pass. The separate exploratory timing in the operating guide does not fill these fields. Development-PC values do not belong in the N100 columns. Keep the five external provider rows out of automatic sampling; use the existing controlled/mock checks unless a separately authorized provider observation is needed.

| API route | Class | Python status / p50 / p95 | Next status / p50 / p95 | Response bytes | DTO / cache notes |
| --- | --- | --- | --- | --- | --- |
| `/api/archive?limit=20` | Stored | Not run | Not run | Not run | Both 30s process-local caches; formal acceptance matrix not run |
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
| N100 preflight 2026-10-15 | Preflight only | Intel N100 / Windows 11 Pro; Node 22.21.1; active Next build `nA1XzbaTDmGe1P5hU8jIc` predates `c01bdc9` | DB 576,159,744 bytes; mtime 16:30:42 KST; read-only DB verify passed | `/health` 200; `/api/archive?limit=19` 200 miss then hit; smoke only | Not run | Not a benchmark | Read-only; schema 11/11; integrity ok; no pending migrations or reported consistency issues | WAL 0 bytes, SHM 32 KiB at preflight; no verified cache-miss read during Poll (15:00:07 GET was reported, cache state absent) | Poll last result 1 at 16:30; Task Scheduler history disabled; no recovery test | Acceptance pending |

For each route, keep separate entries for API p50/p95 and rendered-page/browser-paint observations. Include sample count, warm-ups, cache state, body size or page dimensions, and errors in the run notes. Keep raw DB rows, credentials, tokens, cookies, and environment values out of this document.

## Acceptance And Rollback

Operating cutover requires functional/data parity, clean read-only SQLite and WAL/concurrent-writer behavior, and verified Windows restart/recovery. Performance is a separate decision based on this host's recorded observations.

If Next fails, stop the Next process and continue serving the existing Python `web-view`. Python collection, SQLite writes, scheduler, Telegram, access gate, and the existing sharing target remain the fallback; no database restore or schema rollback is part of the Next rollback.
