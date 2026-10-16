# Operations Performance Observation

## Purpose

Record Next.js web-view performance and normal-operation smoke evidence on the Intel N100 Windows Operations PC. This is a measurement record, not a production cutover approval.

## Status

**N100 Next preview acceptance PASS (scoped): host/build, route parity, normal Poll read smoke, performance snapshot, and normal restart verified. Production cutover is separate.**

On 2026-10-15, the current host was verified as Intel N100 / Windows 11 Pro with Node `v22.21.1` and Python `3.12.14`. Read-only `db-verify --json` passed. Next was built after `c01bdc9` with build ID `eycpeDtIvb5OLXSWuyJyF`. On 2026-10-16, scheduled Polls at 08:30, 09:00, 09:30, and 10:30 ended with `LastTaskResult=0`. Cache-miss Next GETs overlapped the 09:00, 09:30, and 10:30 Poll Running windows and returned 200 without lock/busy errors. During the 09:30 and 10:30 windows, DB mtime changed while the separate `StockMonitor-TelegramCommands` task was also Running, so writer attribution is not isolated. WAL was absent or 0 bytes at the GET snapshots; SHM appeared at 32 KiB during some Next reads and was later removed. No DB rows were inspected.

At 10:21 KST on 2026-10-16, a read-only point-in-time preflight confirmed Intel N100 / Windows 11 Pro, Next PID `7896` on `3010`, Python PID `27968` on `8780`, `/health` 200 with `x-stock-monitor-service: next-web-view`, and the Poll task Ready after its 10:00 run (`LastTaskResult=0`, next run 10:30). At 10:28 KST, the active `.next/BUILD_ID` was confirmed as `eycpeDtIvb5OLXSWuyJyF`. In a separate 10:25 KST metadata check, the configured operating DB resolved to the repository's default file (576,323,584 bytes); only file metadata was read. A local route-contract smoke returned 405 for `/api/archive` POST/HEAD/OPTIONS and 404 for `/login`, `/auth/login`, `/admin`, `/admin-gui`, and `/operator-review`. Source inspection confirmed the Next SQLite connection paths set `readOnly: true` and `PRAGMA query_only = ON`; this is code/config evidence, not a live SQL-write rejection test. These PIDs and sizes describe those snapshots, not a continuing runtime guarantee.

The 17:08 exact-snapshot 14-route comparison and a 09:35 after-Poll recheck both matched DTOs after normalizing only dynamic `now` and Python's private rotation image path. Both used the user-authorized temporary Python reference: a SQLite backup from a read-only source and a process-local nonexistent access-code path. Live Python 8780, `.env`, and `data/access_code.json` stayed unchanged; the live gate still reports enabled. For the 09:35 recheck, the main DB mtime advanced during measurement, so it is supplemental rather than an exact-snapshot A/B. Route results are below.

At 09:39, a 10.19-second idle sample and an 11.71-second cache-read sample recorded Next working set 32.0 MB idle and 32.0–34.2 MB during reads; process CPU increased by 0.328 seconds during 30 GETs (about 2.8% of one logical core over the 11.71-second read window). Host load snapshots were 33–35% idle and 32–42% during reads. A normal 3010 shutdown/restart at 09:41 recovered with the same build ID and health 200. These are descriptive samples, not an SLO or speedup claim.

## Benchmark Preconditions

For a new Next build or a requested remeasurement, confirm the current build ID, selected database metadata, date/route parameters, and matching cache states. Reuse the passing evidence above while code and database selection remain unchanged. The existing exact-snapshot 14-route comparison, read-only SQLite configuration, and normal Poll-time cache-miss reads satisfy the current N100 preview check. Do not wait for live Python authentication, an active WAL transaction, or a forced write to accept this preview.

## Measurement Procedure

Use only the steps relevant to a specific requested measurement. This procedure is not a checklist that must be rerun for an unchanged build.

1. Select representative dates and routes from the shared API matrix after checking that the underlying database snapshot is stable. Record the database file timestamp/size and WAL/SHM state without copying or printing database rows.
2. Record Python and Next builds, host load, test date, route/query, viewport, and whether the result is a cache hit, cache miss, or uncached request. Both services use a process-local 30-second response cache for the 14 stored routes; report cold requests separately from cache hits. The TTL starts after building and serializing the response, so a hit's response-generation `now` can be older by up to 30 seconds plus that build/serialization time; source/as-of/freshness fields remain from the stored snapshot. HTTP responses still use `Cache-Control: no-store`.
3. From `web/`, run `npm run bench:public-get` against the existing loopback Python listener and the one Next preview. The runner uses five warm-ups, 30 sequential samples, and `Accept-Encoding: identity`; it reports the first request separately from p50/p95 and body bytes. It sends `x-stock-monitor-benchmark: 1` to both origins; only Next returns `x-stock-monitor-cache: hit|miss` for that opt-in request, while Python cache state is checked in `api_perf.log`. Compare matching cache states; SQLite/DTO work occurs on misses, while hits return the serialized response. Preserve the access-code gate and provide only an already-authorized Python session cookie through the local process environment if one is available. A `401` means the comparison was not run; never disable the gate to obtain numbers.
4. If a page-render timing question arises, measure representative rendered pages separately from API time. Record viewport and document errors.
5. If a resource issue is observed, capture CPU and memory for the Next process and overall host under that condition.
6. Only when an existing timing source can separate them, report SQLite statement time, DTO/UI composition, indicator calculations, and provider wait separately; do not infer phases from total time.
7. For a new build that changes database reads, or a reported read error, observe one normal scheduled `StockMonitor-Poll` run. Only while the task reports `Running`, capture DB/WAL/SHM metadata and make one stored GET with `x-stock-monitor-benchmark: 1`; count it as a SQLite read only if it returns HTTP 200 with cache `miss`. Discard the body and do not inspect DB rows. Record the task result; never run Poll manually, create a test write, or force WAL contention. The 2026-10-16 overlap evidence is sufficient for the unchanged preview build; do not repeat it just to extend the record.
8. Decide whether an optimization is warranted from the observed user-facing delay or resource constraint. Do not set an SLO or claim a speedup from these measurements alone.

## N100 API Results Matrix

**Status: Exact-snapshot baseline and post-Poll 14-route comparison both matched DTOs 14/14 for `2026-10-14`; this satisfies N100 preview data parity.** The table below preserves the 17:08 exact-snapshot baseline. A 09:35 after-Poll supplemental timing table follows; the source DB mtime advanced during that later run, so use the first table for strict snapshot comparisons. Both runs used the user-authorized temporary Python reference and left live Python 8780 and its access gate unchanged. A live access-gate round trip was not needed for this preview check. Python had 1 miss and 34 hits per route; Next had 1 first-request miss and 30 measured hits per route. Development-PC values do not belong in the N100 columns. Keep the five external provider rows out of automatic sampling.

| API route | Class | Python status / p50 / p95 | Next status / p50 / p95 | Response bytes | DTO / cache notes |
| --- | --- | --- | --- | --- | --- |
| `/api/archive?limit=20` | Stored | 200 / 4.43 / 6.45 ms | 200 / 5.05 / 8.13 ms | 5602 / 5594 | DTO match |
| `/api/daily/2026-10-14` | Stored default | 200 / 4.70 / 10.38 ms | 200 / 5.33 / 8.71 ms | 61618 / 61596 | DTO match; optional Naver query excluded |
| `/api/daily/2026-10-14/stocks/005930` | Stored | 200 / 6.04 / 9.00 ms | 200 / 6.42 / 16.01 ms | 19275 / 19273 | DTO match; same selected stock |
| `/api/stocks/search?date=2026-10-14&q=삼성&limit=8` | Stored | 200 / 5.76 / 8.68 ms | 200 / 6.04 / 13.08 ms | 2947 / 2939 | DTO match; same query and bound |
| `/api/candidate-evidence?date=2026-10-14&limit=8` | Stored | 200 / 5.56 / 13.82 ms | 200 / 5.57 / 9.89 ms | 49619 / 49591 | DTO match; stored order preserved |
| `/api/observation-summary?date=2026-10-14` | Stored | 200 / 5.57 / 13.68 ms | 200 / 5.60 / 9.48 ms | 17301 / 17281 | DTO match |
| `/api/observation/backtest?date=2026-10-14&limit=20&mention_threshold=2` | Stored | 200 / 5.46 / 9.43 ms | 200 / 4.79 / 9.57 ms | 10137 / 10137 | DTO match |
| `/api/market` | Stored | 200 / 5.39 / 10.57 ms | 200 / 4.47 / 8.77 ms | 2587 / 2579 | DTO match; stored Toss snapshot |
| `/api/intraday?date=2026-10-14` | Stored | 200 / 5.02 / 8.12 ms | 200 / 4.93 / 8.33 ms | 841 / 833 | DTO match |
| `/api/flow-trend?date=2026-10-14&limit=5` | Stored | 200 / 5.84 / 9.10 ms | 200 / 5.67 / 10.53 ms | 10689 / 10681 | DTO match; stored Toss flow |
| `/api/etf-trend?date=2026-10-14&limit=5` | Stored | 200 / 5.41 / 8.50 ms | 200 / 5.06 / 8.34 ms | 581 / 573 | DTO match; missing state preserved |
| `/api/rotation-overlay?date=2026-10-14&limit=5&symbols=005930` | Stored | 200 / 4.76 / 7.98 ms | 200 / 4.83 / 10.23 ms | 2901 / 2850 | DTO match after omitting private Python image path |
| `/api/category?date=2026-10-14&type=sector&display_name=반도체&public_category_id=sector%7C반도체%7Cfallback` | Stored | 200 / 5.67 / 8.64 ms | 200 / 4.78 / 9.67 ms | 543 / 535 | DTO match; exact encoded key |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | Stored | 200 / 5.41 / 7.99 ms | 200 / 5.64 / 8.32 ms | 429 / 421 | DTO match; descriptive trend |
| `/api/toss-market-context?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/priority-indicators?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/toss-priority-quotes?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/toss-priority-daily-candles?date={date}&days=90` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |
| `/api/priority-current-quotes?date={date}` | Live provider | Not run | Not run | Not run | Excluded from automated benchmark |

### 2026-10-16 09:35 KST after-Poll supplemental route timing

The runner started at 09:35:07 and finished at 09:35:22 KST after the 09:30 Poll returned `0`. It used the same date and route set as the baseline: `2026-10-14`, stock `005930`, five warm-ups, and 30 measured sequential GETs per route. All responses were HTTP 200; Python recorded 1 miss and 34 hits per route, and Next recorded a first-request miss plus 30 measured hits. A separate in-memory DTO comparison matched 14/14 after normalizing only `now` and `rotation-overlay.image.path`.

Python used a read-only SQLite backup created at 09:34:43 from the main DB, whose mtime was 09:34:14. The source DB mtime advanced to 09:35:15 during the benchmark; therefore these timings are a supplemental same-date comparison, not an exact-snapshot A/B. No response bodies or DB rows were saved.

| Stored GET route | Python first ms | Python p50/p95 ms | Next first ms (cache) | Next measured hit/miss/unreported | Next p50/p95 ms | Bytes Python/Next |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `/api/archive?limit=20` | 132.75 | 4.34 / 6.44 | 38.88 (miss) | 30 / 0 / 0 | 4.26 / 6.01 | 5602 / 5594 |
| `/api/daily/2026-10-14` | 1200.59 | 5.81 / 8.96 | 801.22 (miss) | 30 / 0 / 0 | 6.45 / 10.46 | 61618 / 61596 |
| `/api/daily/2026-10-14/stocks/005930` | 684.96 | 5.52 / 12.95 | 134.39 (miss) | 30 / 0 / 0 | 6.38 / 10.53 | 19275 / 19273 |
| `/api/stocks/search?date=2026-10-14&q=삼성&limit=8` | 184.58 | 5.56 / 8.86 | 141.89 (miss) | 30 / 0 / 0 | 5.47 / 7.85 | 2947 / 2939 |
| `/api/candidate-evidence?date=2026-10-14&limit=8` | 1071.62 | 5.16 / 6.23 | 407.09 (miss) | 30 / 0 / 0 | 5.26 / 8.30 | 49619 / 49591 |
| `/api/observation-summary?date=2026-10-14` | 1493.83 | 5.69 / 9.76 | 446.28 (miss) | 30 / 0 / 0 | 5.59 / 9.71 | 17301 / 17281 |
| `/api/observation/backtest?date=2026-10-14&limit=20&mention_threshold=2` | 64.80 | 5.44 / 9.82 | 9.02 (miss) | 30 / 0 / 0 | 5.14 / 8.05 | 10137 / 10137 |
| `/api/market` | 181.77 | 3.86 / 8.18 | 75.41 (miss) | 30 / 0 / 0 | 3.69 / 6.65 | 2722 / 2714 |
| `/api/intraday?date=2026-10-14` | 11.24 | 4.97 / 7.21 | 9.82 (miss) | 30 / 0 / 0 | 4.95 / 6.28 | 841 / 833 |
| `/api/flow-trend?date=2026-10-14&limit=5` | 95.80 | 5.55 / 6.53 | 11.80 (miss) | 30 / 0 / 0 | 5.16 / 6.09 | 10689 / 10681 |
| `/api/etf-trend?date=2026-10-14&limit=5` | 95.24 | 4.11 / 7.02 | 68.99 (miss) | 30 / 0 / 0 | 3.73 / 5.79 | 581 / 573 |
| `/api/rotation-overlay?date=2026-10-14&limit=5&symbols=005930` | 101.52 | 4.89 / 7.42 | 16.90 (miss) | 30 / 0 / 0 | 4.32 / 8.67 | 2901 / 2850 |
| `/api/category?date=2026-10-14&type=sector&display_name=반도체&public_category_id=sector%7C반도체%7Cfallback` | 20.76 | 5.72 / 10.01 | 11.53 (miss) | 30 / 0 / 0 | 4.96 / 8.48 | 543 / 535 |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | 2552.27 | 5.19 / 7.69 | 74.16 (miss) | 30 / 0 / 0 | 4.43 / 7.28 | 429 / 421 |

`/api/daily/{date}?intraday_market_top=1&market_top_limit=100&market_top_page_size=20` is a live Naver variant of the daily handler, not part of the stored default row. Do not invoke it in the standard route sweep. `/health`, the fixed image route, rendered HTML, and browser paint are recorded as separate smoke/page measurements, not mixed into this API table.

## Host And Operation Results Log

| Run | Status | Host / build | Input snapshot | Routes / viewport | CPU / memory | p50 / p95 | SQLite / assembly / indicators / providers | WAL / concurrent writes | Lifecycle smoke | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N100 preflight 2026-10-15 | Historical preflight; superseded | Intel N100 / Windows 11 Pro; Node 22.21.1; build ID before rebuild `nA1XzbaTDmGe1P5hU8jIc` | DB 576,159,744 bytes; mtime 16:30:42 KST; read-only DB verify passed | `/health` 200; `/api/archive?limit=19` 200 miss then hit; smoke only | Not run | Not a benchmark | Read-only; schema 11/11; integrity ok; no pending migrations or reported consistency issues | WAL 0 bytes, SHM 32 KiB; 15:00:07 GET cache state absent; 16:30 Poll result 1, followed by successful 10/16 Polls | Historical snapshot only | Superseded by the 10/16 preview acceptance checks |
| N100 route comparison 2026-10-15 17:08 KST | PASS for data parity and baseline timing | Intel N100; Node 22.21.1; Python 3.12.14; Next build `eycpeDtIvb5OLXSWuyJyF` / HEAD `0675220` | DB 576,159,744 bytes; mtime 16:30:42 KST; Python used a temporary SQLite backup | 14 stored GETs; date 2026-10-14; 5 warm-ups + 30 samples; 005930 | Not sampled | See route matrix above | 14/14 DTO matched after `now` and private image-path normalization; no provider calls | No Poll overlap; source DB unchanged; WAL 0 bytes, SHM 32 KiB after run | Not a lifecycle run | Exact-snapshot route parity/timing baseline |
| N100 Poll/Next read overlap 2026-10-16 09:00–09:32 | Polls PASS (`0`); cache-miss reads PASS | Intel N100; Poll PID 21140 at 09:00 and PID 16796 at 09:30; Next PID 19032 / build `eycpeDtIvb5OLXSWuyJyF` | 09:00 DB 576,278,528 B, mtime 08:59:29.618; 09:30 DB 576,319,488 B, mtime 09:30:14.159 | 09:00 `/api/archive?limit=41` miss 200, 410 ms, 11,042 B. 09:30 limit45 hit, then limit46 miss 200, 69 ms, 12,341 B; after DB mtime changes, limit47 miss 200, 92 ms, 12,602 B | Not sampled | As above | GETs succeeded with no lock/busy response; no response bodies or DB rows inspected | WAL absent/0 B at GET snapshots; SHM absent/32 KiB. DB mtime changed at 09:31:09 and 09:31:12 while Poll was Running; TelegramCommands was also active, so writer attribution is not isolated | 09:00 and 09:30 Polls ended with result 0; 09:30 end observed 09:32:13 | Read overlap verified; no lock/busy error |
| N100 after-Poll route recheck 2026-10-16 09:35 | Scoped PASS; supplemental snapshot | Intel N100; Python 3.12.14 reference on 8781; Next PID 19032 / build `eycpeDtIvb5OLXSWuyJyF` | Read-only backup created 09:34:43 from DB mtime 09:34:14; main DB mtime advanced to 09:35:15 during run | 14 stored GETs; date 2026-10-14; 5 warm-ups + 30 samples; 005930 | Not sampled | See supplemental table above | 14/14 DTOs matched after documented normalization; Python 1 miss/34 hits per route; Next 1 miss/30 hits | No provider calls; live 8780 gate stayed enabled; temporary server and DB copy removed | DB mtime drift means this was not an exact-snapshot A/B; date-specific DTOs still matched | Confirms route result after successful Poll; strict timing baseline remains 17:08 |
| N100 Next resource sample 2026-10-16 09:39 | Sampled | Next PID 19032; build `eycpeDtIvb5OLXSWuyJyF` | 10.19-second idle then 11.71-second cached GET phase; process PID stable | 30 GETs to `/api/archive?limit=49`; 200; 1 miss/29 hits | Idle working set avg/min/max 32.0 MB; read phase 33.3/32.0/34.2 MB; host CPU load snapshots 33→35% idle, 32→42% reads | Process CPU delta 0.000 s idle; 0.328 s reads (~2.8% of one core over 11.71 s) | Read-only route; no provider call | Idle/read sample only; not concurrent with Poll | Short resource sample | Descriptive N100 resource sample, no SLO inferred |
| N100 normal restart recovery 2026-10-16 09:41 | PASS | Next PID 19032 stopped by Ctrl+C; PID 7896 started from same build ID `eycpeDtIvb5OLXSWuyJyF` | Source DB unchanged by restart | Start script Ready in 10.9 s; `/health` 200; `/api/archive?limit=50` miss then hit, both 200 / 13,381 B | Not sampled | Miss 114 ms; hit 10 ms | Build artifact reused; no DB rows changed by us | Python 8780/gate unchanged | Normal shutdown/start and health recovery passed | Preview lifecycle smoke passed |
| N100 Poll/Next read overlap 2026-10-16 10:30–10:32 | Poll PASS (`0`); cache-miss read PASS | Intel N100; GET began/ended 10:31:03.858–10:31:03.993 while task was Running; scheduled-poll process chain PIDs 23104 → 16556; Next PID 7896 / build `eycpeDtIvb5OLXSWuyJyF` | DB 576,323,584 B; mtime 10:30:13.399 before and 10:31:04.338 after | `/api/archive?limit=53` 200 miss, 131 ms, 14,162 B; task Running both before and after GET | Not sampled | As above | Read-only stored GET; body discarded, no DB rows inspected | WAL/SHM absent before/after. DB mtime changed across the interval; TelegramCommands was Running at 10:30:27, so writer attribution is not isolated | Poll end observed Ready at 10:32:02.900; `LastTaskResult=0`; next scheduled 11:00. No manual Poll or test write | Scheduled read smoke passed; no lock/busy error |

For any requested follow-up measurement, keep API p50/p95 separate from rendered-page timing and include sample count, cache state, and response bytes. Keep raw DB rows, credentials, tokens, cookies, and environment values out of this document.

## Acceptance And Rollback

**N100 preview acceptance: PASS (as of 2026-10-16).** The current build is healthy on `3010`; stored DTOs matched 14/14 on an exact snapshot; GET-only and read-only boundaries were checked; a cache-miss Next read succeeded during normal scheduled Poll runs with no lock/busy error; route timing/resource samples are recorded; and normal stop/restart recovered the same build.

The live Python access gate was left unchanged. WAL was absent or 0 bytes in sampled reads; SHM was absent or 32 KiB depending on the sample. All scheduled Poll-time reads succeeded without a lock/busy error. Production cutover remains separate and is not approved by this result.

If Next fails, stop the Next process and continue serving the existing Python `web-view`. Python collection, SQLite writes, scheduler, Telegram, access gate, and the existing sharing target remain the fallback; no database restore or schema rollback is part of the Next rollback.
