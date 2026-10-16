# Operating Guide

Current operating state, delivery sequence, roadmap, and work board.

## Included sections
- Current Work
- Work Todo Board
- Historical completion index

<!-- Merged from: docs/codex/operating-guide.md -->
## Current Work

### Next.js migration status (2026-10-16)

The target remains to replace the Python public `web-view` screens and GET APIs with Next.js + TypeScript. Python collection, scheduling, SQLite writes, Telegram, `admin-gui`, `operator-review`, and the gated Python public surface stay in place until the Next replacement passes development and N100 operating checks. Next remains GET-only, public-safe, read-only for SQLite, and without access-code/login routes.

| Workstream | State | Current evidence / next check |
| --- | --- | --- |
| Public routes | Implemented; two N100 14-route comparisons matched DTOs via scoped reference | 14 Next page files and 19 direct Next GET Route Handlers exist. Stored reads use read-only Node SQLite on cache misses; the 14 stored timing routes use a process-local 30-second response cache. Bounded provider reads use fixed server-side Naver/Toss endpoints. No Python HTTP bridge is present. The 2026-10-15 exact-snapshot and 2026-10-16 after-Poll comparisons both matched 14/14 DTOs and source/as-of/freshness fields after normalizing only dynamic `now` and Python's private rotation image path. Both used the user-authorized temporary Python reference with a copied DB and process-local missing access-code path; live 8780 and its gate were unchanged. The 09:35 supplemental run's source DB mtime changed during measurement, so the exact-snapshot 17:08 run remains the strict timing baseline. |
| Main / Watch / Stock consistency | Implemented; focused verification passed | The shared server page builds daily, candidate, flow, and selected-stock DTOs in one read-only SQLite transaction and shares them with all three panels. Tests verify one candidate-summary read per request, Python daily DTO parity, and conversion to the strict stock-summary DTO. External reads remain action/disclosure-triggered. |
| Selected-stock feature parity | Implemented | The Stock tab's selected panel includes stored target journey/progress, volume and investor-flow history, related category/ETF context, and saved-news detail in a collapsed disclosure. It reuses the supplied validated stock DTO. |
| Windows preview | Running on 3010 after restart recovery smoke | Build ID `eycpeDtIvb5OLXSWuyJyF` remains in use. PID 19032 was stopped normally and `scripts/start_next_web_view.ps1` started PID 7896 at 09:41 KST. It became Ready in 10.9 seconds; `/health` returned 200 with `x-stock-monitor-service: next-web-view`; `/api/archive?limit=50` returned 200 miss then hit. No rebuild occurred during recovery. |
| Development verification | Current cache implementation built successfully | On 2026-10-15, `npm test` passed **90/90**, `npm run typecheck`, `npm run test:routes` (**27/27**) passed, and `npm run build` passed again after `c01bdc9`. The route suite used a temporary loopback Python reference process; no persistent access-code setting changed. Earlier 375px viewport and Main→Watch→Stock browser checks remain separate evidence. |
| Intel N100 Operations PC | N100 preview acceptance PASS (scoped); production cutover separate | The Intel N100 / Windows 11 Pro host uses Node `v22.21.1` and Python `3.12.14`; read-only `db-verify --json` passed. Normal Polls at 08:30, 09:00, 09:30, and 10:30 on 2026-10-16 returned `0`. Cache-miss Next GETs during three Poll Running windows returned 200 without lock/busy errors. Active WAL contention was not observed and was not forced. Python, scheduler, and sharing remain unchanged. |
| API timing benchmark | Exact-snapshot baseline and after-Poll supplemental run recorded | The exact-snapshot 2026-10-15 17:08 run and the 2026-10-16 09:35 after-Poll run both returned 200 and matched DTOs 14/14. The later source DB mtime changed during the benchmark, so it is supplemental; the strict baseline and latest p50/p95 results are in [Operations performance observation](operations-performance-observation.md). |
| Operating performance | N100 preview measurement recorded | The 14-route p50/p95 and response-byte/cache comparison, a short CPU/working-set sample, and normal Next restart smoke are recorded. These are descriptive measurements, not an SLO or speedup claim. |
| UI polish | Deferred | Pixel matching, small dimensions/spacing, and style differences follow feature/data parity; clipping or unusable mobile controls remain functional defects. |

#### Developer-PC API timing benchmark

**Historical pre-cache baseline:** the following isolated-snapshot run predates the 2026-10-15 Next response-cache change. Its Python 30-second response cache was warm while Next read SQLite and rebuilt the DTO on every request. Do not interpret that apparent p50 gap as evidence of Next or host hardware being slower; the 2026-10-15 follow-up below corrects the cache-state mismatch.

The run below used the repeatable loopback HTTP runner and **14/14 stored routes returned `200`**. The environment was Node `v24.15.0`, Next.js `16.4.0` (`next start`), and Python `3.10.11`. The Python reference was a temporary process bound only to `127.0.0.1:8781`, reading a temporary SQLite backup created through a read-only source connection. Only that process's in-memory access-code path pointed to a non-existent temp file; the configured Python public access-code file and project `.env` were unchanged. The temporary DB was removed after the run. This developer-only setup measured the same Python route handlers without the access-gate round trip, which Next does not have. It is not a procedure for the Operations PC; there, use the existing gated listener and an already-authorized session.

The reusable runner can target the existing authenticated loopback Python listener with `STOCK_MONITOR_PYTHON_COOKIE`, or any temporary loopback reference process. It only accepts loopback origins and does not start a Python server itself. For a gated service, a `401` stops the run.

```powershell
Push-Location .\web
npm run bench:public-get
Pop-Location
```

Defaults are Next `127.0.0.1:3010`, Python `127.0.0.1:8780`, date `2026-10-08`, and stock code `005930`. Override with `STOCK_MONITOR_NEXT_ORIGIN`, `STOCK_MONITOR_PYTHON_WEB_VIEW_URL`, `STOCK_MONITOR_BENCH_DATE`, and `STOCK_MONITOR_BENCH_STOCK_CODE` if the selected local snapshot requires different values. A pre-authorized Python session cookie may be supplied locally as `STOCK_MONITOR_PYTHON_COOKIE`; the runner never prints or persists it. Both origins are restricted to loopback.

The runner sends each identical URL to both servers, uses `Accept-Encoding: identity`, performs five warm-ups and 30 measured requests, consumes each response body, and reports first-request time, post-warm-up p50/p95, status, and body bytes. `api-perf-summary --json` over this run's 490 Python log records confirmed 34 response-cache hits and one miss per route (14 endpoints); internal cache-hit p50/p95 ranged from 0.075/0.091ms to 0.087/0.356ms. These are server-internal timings, not full HTTP response times. Python's 30-second cached response path and Next's direct read-only SQLite path are different execution paths; these results compare the current HTTP experience, not equal amounts of DB work or a guaranteed speedup. Python first-miss `db_ms`, `build_ms`, and `json_ms` were also captured from `api_perf.log`; `db_ms` is part of `build_ms` and must not be added to it. For these 14 first misses, their medians were 16.055ms, 19.422ms, and 0.058ms respectively; one miss per route is descriptive, not a phase p95. Thirty HTTP samples provide a coarse p95 and are not an SLO.

This run used date `2026-10-08`, stock `005930`, the query inputs below, five warm-ups, and 30 measured requests per route. The source DB and WAL size/mtime were stable across the run; Python served a temporary backup of that snapshot. No DB rows or response bodies were printed. Body byte lengths differ slightly between Python and Next, so byte equality is not asserted here; compare DTO fields separately while retaining source/date/freshness/missing fields and normalizing only dynamic clock fields.

| Identical GET input | Python first miss ms | Python cached p50/p95 ms | Next first ms | Next direct p50/p95 ms | Body bytes Python/Next |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/api/archive?limit=20` | 28.11 | 1.59 / 1.97 | 7.97 | 4.72 / 5.39 | 5603 / 5595 |
| `/api/daily/2026-10-08` | 324.77 | 1.79 / 1.97 | 173.24 | 165.59 / 175.20 | 64767 / 64745 |
| `/api/daily/2026-10-08/stocks/005930` | 133.43 | 1.63 / 1.98 | 35.59 | 34.35 / 35.55 | 18818 / 18816 |
| `/api/stocks/search?date=2026-10-08&q=삼성&limit=8` | 17.20 | 1.34 / 2.00 | 30.42 | 29.29 / 30.73 | 2943 / 2935 |
| `/api/candidate-evidence?date=2026-10-08&limit=8` | 277.21 | 1.76 / 2.00 | 93.87 | 94.20 / 104.77 | 48577 / 48555 |
| `/api/observation-summary?date=2026-10-08` | 318.25 | 1.57 / 2.13 | 111.36 | 111.25 / 117.51 | 16768 / 16748 |
| `/api/observation/backtest?date=2026-10-08&limit=20&mention_threshold=2` | 16.53 | 1.57 / 1.84 | 4.18 | 3.33 / 3.71 | 7782 / 7782 |
| `/api/market` | 32.21 | 1.60 / 1.93 | 20.19 | 19.06 / 19.89 | 2569 / 2561 |
| `/api/intraday?date=2026-10-08` | 4.46 | 1.53 / 1.74 | 3.22 | 3.25 / 3.68 | 1123 / 1115 |
| `/api/flow-trend?date=2026-10-08&limit=5` | 15.41 | 1.53 / 1.85 | 3.51 | 3.15 / 3.53 | 10680 / 10672 |
| `/api/etf-trend?date=2026-10-08&limit=5` | 24.62 | 1.39 / 1.91 | 20.43 | 18.78 / 19.58 | 581 / 573 |
| `/api/rotation-overlay?date=2026-10-08&limit=5&symbols=005930` | 17.58 | 1.55 / 1.77 | 5.41 | 3.75 / 4.20 | 2411 / 2366 |
| `/api/category?date=2026-10-08&type=sector&display_name=반도체&public_category_id=sector%7C반도체%7Cfallback` | 5.89 | 1.53 / 1.77 | 3.54 | 2.96 / 3.23 | 543 / 535 |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | 431.97 | 1.37 / 1.80 | 10.38 | 9.50 / 10.29 | 429 / 421 |

#### 2026-10-15 cache-matched exploratory timing (Intel N100; not acceptance)

**Why the earlier result looked unfair:** the 15:02 pre-cache run compared Python's warmed response-cache hits against uncached Next SQLite/DTO work. Python `api_perf.log` showed 34 hits and two misses in 36 requests on most routes, while Next had no stored-response cache. The apparent warm p50s were daily 6.37 ms Python vs 734.46 ms Next, candidate evidence 5.43 vs 440.26 ms, and observation summary 5.61 vs 484.58 ms. Those values mixed cache states and cannot establish a hardware comparison. In the cache-matched 15:40 run below, first misses were also faster in Next on the expensive routes: daily 952 ms vs 1,973 ms Python, candidate evidence 520 vs 1,097 ms, and observation summary 449 vs 1,508 ms. This establishes that the earlier result mixed cache states; the later N100 timings are exploratory and do not isolate a hardware effect or constitute authenticated acceptance evidence.

The Next cache correction applies a bounded process-local 30-second serialized-response cache to the same 14 stored GET routes as Python. Client/proxy caching remains `no-store`; live Naver/Toss routes and the optional daily Naver overlay are excluded. `now` reflects response-generation time; because the TTL starts after build and serialization, its age can be up to 30 seconds plus that build/serialization time, as in Python. Stored source/as-of/freshness fields are unchanged.

This follow-up ran on 2026-10-15 from 15:40:57.930 to 15:41:14.542 KST. A later host preflight confirmed that the same `3010` process was on the Intel N100 machine, correcting the earlier “Developer PC” label. Input was `date=2026-10-14`, `stock_code=005930`; the runner used five warm-ups and 30 measured sequential requests with identity encoding. Runtime was Node `v22.21.1`, npm `10.9.4`, Next `16.4.0` (`next start`), and Python `3.12.14`; branch `codex/next-v1`, base HEAD `e512f46` plus the then-uncommitted cache change. The temporary Python reference listener used a nonexistent in-memory access-code path, so this did not exercise an authorized Python session or the gate and is not an acceptance comparison. The active Next build ID is `nA1XzbaTDmGe1P5hU8jIc`; its trace predates `c01bdc9`, so this run does not prove that the pushed commit was served. The Next diagnostic status was opt-in via `x-stock-monitor-benchmark: 1`; Python ignored that header and its cache state came from `api_perf.log`. Each Next route's first request was a miss and all 30 measured samples were hits; Python recorded 34 hits and one miss per route. DTO/provenance matched 14/14 after normalizing only dynamic `now` and Python's private `rotation-overlay.image.path`.

The database snapshot was `576,135,168` bytes, mtime `2026-10-15 15:31:56 KST`; it remained unchanged through the run. WAL was `0` bytes and SHM was `32 KiB` after the read run. The 15:30 scheduled Poll had finished with result `0` before this benchmark; no Poll overlapped it. The temporary reference listener used a non-existent in-memory access-code path on loopback only, was stopped after the check, and created no access-code file. No response bodies or database rows were saved.

| Stored GET route | Python first ms | Python p50/p95 ms | Next first ms (cache) | Next measured hit/miss/unreported | Next p50/p95 ms | Bytes Python/Next |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `/api/archive?limit=20` | 129.65 | 4.36 / 7.50 | 35.02 (miss) | 30 / 0 / 0 | 4.74 / 9.41 | 5602 / 5594 |
| `/api/daily/2026-10-14` | 1972.98 | 4.21 / 11.16 | 952.42 (miss) | 30 / 0 / 0 | 5.54 / 7.73 | 61618 / 61596 |
| `/api/daily/2026-10-14/stocks/005930` | 678.78 | 5.44 / 11.93 | 145.95 (miss) | 30 / 0 / 0 | 5.77 / 11.55 | 19275 / 19273 |
| `/api/stocks/search?date=2026-10-14&q=삼성&limit=8` | 249.85 | 5.68 / 9.70 | 173.56 (miss) | 30 / 0 / 0 | 5.76 / 9.20 | 2947 / 2939 |
| `/api/candidate-evidence?date=2026-10-14&limit=8` | 1096.57 | 5.63 / 20.27 | 520.38 (miss) | 30 / 0 / 0 | 5.56 / 11.49 | 49619 / 49591 |
| `/api/observation-summary?date=2026-10-14` | 1508.35 | 4.47 / 8.28 | 449.10 (miss) | 30 / 0 / 0 | 4.73 / 11.20 | 17301 / 17281 |
| `/api/observation/backtest?date=2026-10-14&limit=20&mention_threshold=2` | 138.83 | 4.34 / 8.58 | 26.16 (miss) | 30 / 0 / 0 | 4.43 / 7.04 | 10137 / 10137 |
| `/api/market` | 189.01 | 3.97 / 6.90 | 94.81 (miss) | 30 / 0 / 0 | 3.81 / 5.46 | 2587 / 2579 |
| `/api/intraday?date=2026-10-14` | 54.52 | 5.25 / 9.83 | 22.70 (miss) | 30 / 0 / 0 | 5.43 / 9.21 | 841 / 833 |
| `/api/flow-trend?date=2026-10-14&limit=5` | 83.41 | 5.25 / 10.22 | 20.85 (miss) | 30 / 0 / 0 | 5.17 / 10.70 | 10689 / 10681 |
| `/api/etf-trend?date=2026-10-14&limit=5` | 120.02 | 3.87 / 15.13 | 70.48 (miss) | 30 / 0 / 0 | 3.87 / 6.59 | 581 / 573 |
| `/api/rotation-overlay?date=2026-10-14&limit=5&symbols=005930` | 132.09 | 4.07 / 6.24 | 24.07 (miss) | 30 / 0 / 0 | 4.41 / 6.81 | 2901 / 2850 |
| `/api/category?date=2026-10-14&type=sector&display_name=반도체&public_category_id=sector%7C반도체%7Cfallback` | 29.41 | 5.07 / 8.66 | 20.41 (miss) | 30 / 0 / 0 | 5.14 / 11.00 | 543 / 535 |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | 2243.80 | 4.89 / 10.49 | 53.19 (miss) | 30 / 0 / 0 | 4.50 / 8.54 | 429 / 421 |

The earlier pre-cache and this follow-up used the same date/route matrix but different database mtimes (`15:02:07` vs `15:31:56` KST), so treat the p50 change as an observed cache effect rather than a strict same-snapshot A/B. The 15:40 run used the same stable DB snapshot for Python and Next, but its Next build predates `c01bdc9`. The later 17:08 run below uses the rebuilt cache implementation and records the scoped N100 route matrix; active-writer/WAL and recovery checks remain outstanding.

The 2026-10-16 09:35 after-Poll recheck matched all 14 DTOs and cache states. Its Python snapshot was created at 09:34:43 from a DB last modified at 09:34:14; the main DB mtime advanced to 09:35:15 during the run. Treat it as a supplemental same-date result, not an exact-snapshot A/B. The current p50/p95 table and Poll/WAL evidence are in [Operations performance observation](operations-performance-observation.md).

#### 2026-10-15 17:08 N100 cache-matched comparison (temporary reference)

The run started at 17:08:42 and finished at 17:08:58 KST on the Intel N100 host. Next was PID 19032, build ID `eycpeDtIvb5OLXSWuyJyF`, built from `codex/next-v1` HEAD `067522093d6029c93f4217713caa6514af606445` after the cache implementation in `c01bdc9`. It used `date=2026-10-14`, `stock_code=005930`, five warm-ups, 30 measured sequential GETs per route, and identity encoding.

Python used a temporary loopback listener on `127.0.0.1:8781`, a SQLite backup made from a read-only connection to the current DB, and a process-local access-code path that did not exist. This was the user-authorized local reference fallback after the browser connector failed. The live Python listener on `8780`, `.env`, and `data/access_code.json` remained unchanged; the live gate still reported enabled. The temporary listener and copied snapshot were stopped and removed after comparison. The fallback excludes Python's access-gate round trip and does not test live authentication.

All **14/14** routes returned HTTP 200. Python `api_perf.log` recorded 35 requests per route (one miss, 34 hits); Next recorded a first-request miss and 30 measured hits per route. A separate in-memory DTO comparison matched **14/14** after normalizing only dynamic `now` and Python's private `rotation-overlay.image.path`; all other fields, including source/as-of/freshness, were compared. No response bodies or DB rows were saved. The source DB remained 576,159,744 bytes with mtime `2026-10-15 16:30:42 KST`; after the run WAL was 0 bytes and SHM was 32 KiB. No Poll was running, so this is not the active-writer/WAL observation.

| Stored GET route | Python first ms | Python p50/p95 ms | Next first ms (cache) | Next measured hit/miss/unreported | Next p50/p95 ms | Bytes Python/Next |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `/api/archive?limit=20` | 127.27 | 4.43 / 6.45 | 50.81 (miss) | 30 / 0 / 0 | 5.05 / 8.13 | 5602 / 5594 |
| `/api/daily/2026-10-14` | 1290.21 | 4.70 / 10.38 | 940.24 (miss) | 30 / 0 / 0 | 5.33 / 8.71 | 61618 / 61596 |
| `/api/daily/2026-10-14/stocks/005930` | 566.94 | 6.04 / 9.00 | 156.31 (miss) | 30 / 0 / 0 | 6.42 / 16.01 | 19275 / 19273 |
| `/api/stocks/search?date=2026-10-14&q=삼성&limit=8` | 210.88 | 5.76 / 8.68 | 171.61 (miss) | 30 / 0 / 0 | 6.04 / 13.08 | 2947 / 2939 |
| `/api/candidate-evidence?date=2026-10-14&limit=8` | 1062.83 | 5.56 / 13.82 | 520.78 (miss) | 30 / 0 / 0 | 5.57 / 9.89 | 49619 / 49591 |
| `/api/observation-summary?date=2026-10-14` | 1384.39 | 5.57 / 13.68 | 554.57 (miss) | 30 / 0 / 0 | 5.60 / 9.48 | 17301 / 17281 |
| `/api/observation/backtest?date=2026-10-14&limit=20&mention_threshold=2` | 145.87 | 5.46 / 9.43 | 30.88 (miss) | 30 / 0 / 0 | 4.79 / 9.57 | 10137 / 10137 |
| `/api/market` | 193.57 | 5.39 / 10.57 | 92.57 (miss) | 30 / 0 / 0 | 4.47 / 8.77 | 2587 / 2579 |
| `/api/intraday?date=2026-10-14` | 17.11 | 5.02 / 8.12 | 14.95 (miss) | 30 / 0 / 0 | 4.93 / 8.33 | 841 / 833 |
| `/api/flow-trend?date=2026-10-14&limit=5` | 58.54 | 5.84 / 9.10 | 25.17 (miss) | 30 / 0 / 0 | 5.67 / 10.53 | 10689 / 10681 |
| `/api/etf-trend?date=2026-10-14&limit=5` | 107.91 | 5.41 / 8.50 | 102.46 (miss) | 30 / 0 / 0 | 5.06 / 8.34 | 581 / 573 |
| `/api/rotation-overlay?date=2026-10-14&limit=5&symbols=005930` | 119.34 | 4.76 / 7.98 | 24.99 (miss) | 30 / 0 / 0 | 4.83 / 10.23 | 2901 / 2850 |
| `/api/category?date=2026-10-14&type=sector&display_name=반도체&public_category_id=sector%7C반도체%7Cfallback` | 25.75 | 5.67 / 8.64 | 21.73 (miss) | 30 / 0 / 0 | 4.78 / 9.67 | 543 / 535 |
| `/api/category-trend?type=sector&display_name=__e2e_category_trend__&limit=999` | 2366.41 | 5.41 / 7.99 | 41.53 (miss) | 30 / 0 / 0 | 5.64 / 8.32 | 429 / 421 |

These 14 routes are the stored/default timing set. The five provider routes—`/api/toss-market-context`, `/api/priority-indicators`, `/api/toss-priority-quotes`, `/api/toss-priority-daily-candles`, and `/api/priority-current-quotes`—and the optional Naver query on `/api/daily/{date}` are excluded from automated timing. They can make external calls and their latency depends on provider state; use existing mock/fixture checks for contract coverage. `/health` and the fixed image route are smoke checks, not data API samples. Rendered-page and browser-paint timing stay separate from API p50/p95.

The working-tree implementation remains a local preview, not an operating cutover. No scheduler, Telegram, schema, external-sharing, operations DB, or production Python listener change is part of this migration. For a rollback, stop the Next preview and continue using the unchanged Python public `web-view`; do not change the Python listener, scheduler, DB writer, or sharing target during development verification.

This status replaces older bridge counts, port observations, test totals, and performance priorities below. Those dated notes are retained only as historical evidence and must not be read as current runtime or acceptance results.

#### Windows Next preview procedure

- Check state: `.\scripts\start_next_web_view.ps1 -Status`. It reports stopped or checks `/health` and Main on port `3010` after confirming the listener belongs to this project. If Windows reports a system PID or omits the listener, the launcher requires the project Next command plus the `next-web-view` health marker and Main response; unknown listeners are left running.
- Start or restart: `.\scripts\start_next_web_view.ps1`. Keep this dedicated terminal open; the script runs one foreground server on `127.0.0.1:3010` and writes `logs/next-web-view.log`.
- Stop normally: press `Ctrl+C` in that same server terminal and wait for the process to exit. Then run the status command before restarting.
- If port `3010` is occupied, the launcher reports the owning PID/name and refuses to start or choose another port. Do not terminate the owner unless its process command is confirmed to be this project's Next server. Leave unrelated processes untouched.
- Preview rollback: stop Next in its terminal and open/continue using the existing Python public `web-view`. The launcher never changes the Python listener, DB, scheduler, or sharing target.

### Historical host snapshot (2026-09-28)

The repository is in live-market validation and operational hardening, not initial MVP construction. A read-only operator-status snapshot from this Windows work environment at 2026-09-28 09:01 KST showed `StockMonitor-TossCloseSnapshot` healthy, capture pending before 20:05, and no health warnings. This does not identify the environment as the designated main PC or mini PC, or verify today's close capture and Telegram delivery.

At that time, the documented boundaries described the Naver report-to-summary/Telegram pipeline, operator-only `admin-gui`, and GET-only, stored-data-first `web-view`; Toss 20:00 snapshots owned stored market/ETF/flow context and existing KRX rows were historical analysis/recovery data. Current Main Top2 behavior is documented in [surface-guide.md](surface-guide.md) and [data-governance.md](data-governance.md); this dated host snapshot does not establish current host behavior.

### Historical local implementation status (2026-10-10)

1. Candidate and nested daily DTOs strip the internal numeric sort field and identify Toss-backed dates/scope as Toss. `TODO2-WV-CONTENT-QA` completed on 2026-09-28; see its recent-date and responsive smoke evidence below.
2. Local Toss capture reports required-domain coverage, marks incomplete events partial/empty, preserves explicit security classification, and excludes candidate-only rows from snapshot dates. Web-view and market-briefing freshness carry partial status/missing domains; operator status warns when a healthy Toss task lacks a due capture; mini-PC preflight includes that task and no longer requires retired KRX backfill tasks. A late skipped capture warns as missing, while suppression and a prior successful capture remain non-alerting. The focused regression set recorded on 2026-09-28 passed 470 tests. Real host/date validation remains in `TODO2-DATA-FRESHNESS-LIVE`.
3. Web-view first-load query work now bounds recent-date reads by source and reuses the already loaded Toss snapshot date. Authenticated browser/API timing remains pending in `TODO2-WV-FIRST-LOAD`.
4. The current working tree propagates Telegram send failures, records empty-alert delivery failures, and includes intraday failures in operator health. This is local code/test evidence only; no real Telegram send, scheduler run, or operating-DB validation was performed.
5. Retry policy for an accepted Telegram send whose response is lost remains undecided and unchanged; it is tracked in `TODO2-TG-LIVE-DRYRUN`.
6. Lunch/pre-close briefings lead with same-day Toss context and its ranking/query timestamps. The 08:20 pre-open briefing labels prior-day report content as `전일 리포트`, saved market/flow values as `이전 종가 비교`, and adds generic Toss market-wide context only for the current briefing date with date-valid ranking/index/flow timestamps. Naver KRX quote enrichment appears as current only when its trade date matches the briefing date. Toss ranking venue inclusion for NXT remains unverified and is not labeled NXT. Mood remains unchanged.
7. Main Top2's on-demand Toss chart uses the selected-date server-derived candidates, adjusted daily candles, and local factual indicators. The complete calculation and condition contract is in [data-governance.md](data-governance.md); this guide records only current implementation status.
8. `operator-review` is a separate loopback-only GET panel (`127.0.0.1:8767`) for the selected-date Main candidate order, source dates, evidence, and information gaps. It opens Stock-Newbby charts only through an operator-clicked deep link; Newbby must already be running to fetch the linked symbol. Its SQLite connection is read-only. The public Main indicator route is a separate explicit-action exception documented in [surface-guide.md](surface-guide.md) and [data-governance.md](data-governance.md).
9. The public Main summary now surfaces the selected Main candidates' stored reasons and recorded information gaps, alongside existing date/source freshness. It adds no score, grade, or trading instruction.
10. The separate Main Top2 user-defined condition projection was approved 2026-10-09 and clarified 2026-10-10. Its canonical formula, states, provenance, and schema boundary are in [data-governance.md](data-governance.md); it is not an empirically validated trading rule.
11. Date changes now clear prior-date content and discard late daily, candidate-evidence, and flow-trend responses. Stale Toss market-context data shows its last successful fetch time. The authenticated Main page was inspected and the full suite passed 1,256 tests.
12. Integration of the separately scheduled web morning briefing remains on hold; its source, schedule, and date/data contract have not been identified. Do not duplicate or integrate it until that evidence is available.

Repository/code verification for the Main state correction is in commit 6557f398 on main. This does not confirm current mini-PC deployment, scheduler state, or Telegram delivery.
## Work Todo Board

## Purpose

이 문서는 `02.Stock_Moniter`의 큰 작업축을 체크 가능한 형태로 모아둔 실행 보드다.

현재 활성 작업은 아래 `TODO2-*` 항목이다. 이전 `TODO-*` 체크리스트는 완료 이력이며 새 구현 지시가 아니다.

## Use Rules

- 체크박스는 큰 작업축 완료 여부만 표시한다.
- 세부 기능을 작은 체크박스로 쪼개지 않는다.
- 새 작업축은 기존 ID와 겹치지 않는 stable ID를 부여한다.
- 완료 판정은 `Done When` 기준을 만족하고, 검증 명령 또는 실제 화면/출력 확인이 끝났을 때만 한다.
- 운영 적용은 별도 승인 전까지 보드 완료 조건이 아니다. 개발 검증과 운영 싱크는 분리한다.

## Current Priority

| Order | Todo ID | Why Now |
| --- | --- | --- |
| 1 | TODO2-NEXT-WEBVIEW-MIGRATION | Finish public screen/API feature and data parity, stabilize the single Windows preview, and complete staged development verification. |
| 2 | TODO2-DATA-FRESHNESS-LIVE | Validate current Toss freshness and capture/health/freshness agreement on representative dates and the operating host. |
| 3 | TODO2-ADMIN-ACCESS | Verify operator/public boundary on an approved operating-like environment. |
| 4 | TODO2-TG-LIVE-DRYRUN | Review paging/retry/outbox behavior; ambiguous-send retry changes await the policy choice. |
| 5 | TODO2-RT-PRUNE | Use the shared operating review to decide whether current evidence should move higher in the first-read path. |
| 6 | TODO2-NI-EVAL | Judge explanation usefulness on real stored samples without converting a small sample into a quality score. |

## Completed Work Record (Historical)

| Work ID | State | Current reference |
| --- | --- | --- |
| `TODO-WV`, `TODO-TG`, `TODO-NI`, `TODO-DATA`, `TODO-OPS`, `TODO-ADMIN`, `TODO-DOC` | Dev-side implementation slices were marked complete by 2026-06-05. This does not establish current host deployment or operating readiness. | [history.md](history.md), [surface-guide.md](surface-guide.md), [market-data-runbook.md](market-data-runbook.md) |

Detailed progress text and repeated verification outputs were removed from this live work board. Use dated history for operational evidence and inspect current source/tests for implementation state.
## Current TODO2 Task Definitions

### [x] TODO2-OPS-REAL: Operating-PC Sync And Real Migration Handoff

Completed on 2026-06-05 as a dev-side sync/readiness preparation. It did not perform an operating-PC migration, scheduler change, Telegram send, or admin process action. See [history.md](history.md#operating-pc-sync-and-readiness-closeout-2026-06-05); that dated result is not current host evidence.

### [ ] TODO2-NEXT-WEBVIEW-MIGRATION: Next.js Public Web-View Replacement

**Goal:**
Replace the existing public Python web-view screens and public GET APIs with the local Next.js + TypeScript app while retaining Python as the sole application-data writer and keeping the Python public surface available until operating acceptance.

**Current ordered work:**

| Order | State | Work |
| --- | --- | --- |
| 1 | N100 preview acceptance pass | All 14 Next pages and 19 GET handlers are inventoried. The 2026-10-15 same-snapshot comparison matched 14/14 stored DTOs through the user-authorized temporary Python reference. The live Python 8780 gate was left unchanged; testing that gate is not part of preview acceptance. |
| 2 | Done on development PC | Removed the confirmed duplicate candidate-summary query and shared one read-only snapshot across Main/Watch/Stock; explicit provider reads and the selected-stock route flow were checked. Continue distinguishing normal data refresh from a migration defect. |
| 3 | N100 preview lifecycle smoke passed | The 2026-10-15 rebuild produced build ID `eycpeDtIvb5OLXSWuyJyF`; a normal 2026-10-16 stop/start recovered the same build on port `3010` as PID 7896. `/health` returned 200 with the expected service marker. The running process still owns `.next`; do not rebuild in place. |
| 4 | Current build and scoped route comparison passed | Earlier `npm test` (90/90), typecheck, and route tests (27/27) passed; `npm run build` passed again after `c01bdc9`. On 2026-10-15, the same-snapshot 14-route run matched DTOs via the user-authorized temporary Python reference path. The live 8780 access-gate round trip was not part of that run. |
| 5 | N100 scheduled Poll overlap observed; WAL contention not established | On 2026-10-16, scheduled Polls at 08:30, 09:00, 09:30, and 10:30 returned result `0`; cache-miss Next GETs overlapped the 09:00, 09:30, and 10:30 Running windows and returned 200 without lock/busy errors. The 10:30 GET was limit53, 131 ms, 14,162 bytes. WAL was absent/0 bytes at sampled GETs; TelegramCommands also ran, so DB-mtime changes are not attributed solely to Poll. See [Operations performance observation](operations-performance-observation.md). |
| 6 | N100 preview acceptance pass; cutover not included | Exact-snapshot DTO parity, normal Poll/cache-miss read smoke, read-only SQLite setup, route timing, short resource sample, and normal restart are recorded. The local preview passes; this does not change the Python service, scheduler, gate, or sharing target. |
| 7 | Deferred | Refine small visual dimensions/styles only after feature/data parity, except clipping or inaccessible controls, which remain functional defects. |

**Done When:**

- All existing public screen features and public GET contracts are represented in Next or explicitly identified as access-gate exceptions; no Python HTTP bridge remains in Next.
- Public source/date/freshness/provisional/final/missing states and Main Top2's existing narrow condition contract remain intact. No operator/status DTO, score, generic trading advice, order route, or access-code path is added.
- Development tests and the 14-route API contract suite pass; the Main→Watch→Stock 375px browser flow is recorded.
- The one-port 3010 start/status/normal stop/restart path is verified without touching unrelated processes.
- N100 read-only DB configuration, Poll-time cache-miss GET, and normal restart are recorded; the unchanged Python public web remains the fallback. Production cutover is a separate decision.
- The N100 route timing and short resource measurements are recorded; make no SLO or speedup claim and optimize only for an observed user-facing problem.

No production URL, Task Scheduler entry, Telegram send, schema, operating DB, or external-sharing target is changed by this task. To roll back a preview, stop Next and continue on the unchanged Python public web-view.

### [ ] TODO2-RT-PRUNE: Realtime-First Public Surface Pruning

**Goal:**
Reorder public `web-view` and Telegram thinking around current observation evidence first, while lowering previous-day/stored/reference/reaction evidence to fallback/detail/review.

**Scope:**

- Use `오늘 볼 것 -> 현재 근거 -> 전일 참고 -> 부족한 근거 -> 복기/연구` as the shared ordering contract.
- Keep top-2 candidate identity, same-day saved news, current quote/turnover evidence, and source checked time in the first-read path when available.
- Keep KRX daily and `[12009]` rows only for historical review. Current market cards use Toss 20:00 stored context; any bounded intraday Toss reference remains separately source-labelled.
- Maintain the public boundary: no scores, grades, generic buy/sell calls, entry/exit price advice, take-profit/target-return/conviction, broker execution, or order routing. The sole wording exception is the separate user-defined Main Top2 condition in [data-governance.md](data-governance.md); [surface-guide.md](surface-guide.md) owns its controls and presentation.
- Reuse the checklist in `docs/codex/surface-guide.md` when judging live operating stability; it does not block local fixes or focused tests.
- Use the daily read-only routine in that plan; do not treat one clean preview or smoke run as completion.

**Done When:**

- Focused local changes have representative-date evidence and targeted tests; the shared operating review log is used to decide whether a changed first-read order is stable in operation.
- Each review row records the command evidence used for the check, including any command that could not run and its read-only substitute.
- Telegram no-send previews read in the new order and still pass public-safe wording checks.
- A reviewer can identify the top-2 candidate, current evidence, and gaps at a glance; “about 10 seconds” is a usability prompt, not a timed pass/fail gate.
- Stale KRX/flow/ETF and reaction/backtest evidence no longer dominate the first-read path.
- No production DB write, scheduler change, Telegram real send, admin-gui process action, or broker/order route is added for this TODO.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-WV-FIRST-LOAD: Web-View First-Entry Performance (Deferred)

**Status (2026-10-14):** No new timing run is claimed. The common stored-GET runner is prepared above, but a controlled Python/Next comparison needs the authorized Python loopback reference. The dated timings below are historical observations with their original cache/test conditions; do not treat them as current verification or a speed target. After N100 runtime and SQLite/WAL checks, use [Operations performance observation](operations-performance-observation.md) for actual operating-host measurements.

**Goal:**
Make the first stored-data view responsive without changing candidate ordering, market data, or public API boundaries.

**Implementation update (2026-09-30):** Recent Toss-market and investor-flow dates now use bounded per-source queries, and the daily snapshot reuses its already loaded Toss date. Missing market context no longer auto-opens the ETF reference details. On the same local 2026-09-29 data, the direct daily-snapshot builder profile went from 6.36s before the change to 1.16s after restart (5.20s / 82% lower). The latest 2026-09-30 builder took 0.89–0.91s across three unprofiled reads. Market dates matched the old UNION query for limits 1, 3, 5, and 20; flow dates matched at limits 1, 3, and 5 for both sources. The service restarted and `/health` returned `200 ok`. Authenticated HTTP timing remains pending: direct API access returned `401` at the access-code gate, and the existing cold-miss logs (4.48–21.92s) do not identify request origin.
**Implementation update (2026-10-10):** Date changes now invalidate old daily, candidate-evidence, and flow-trend responses, and stale Toss market-context results retain their last successful fetch time. The authenticated Main page was inspected. Cold/warm first-load timing remains unmeasured, so this TODO stays open.

**Implementation update (2026-10-11):** The current `python -m stock_monitor api-perf-summary --json` output contains 686 existing records across 27 endpoints; it is a preliminary log, not a controlled run. `/api/priority-indicators?date=2026-10-08` reports p50/p95 1,459/2,211ms, average DB 0.08ms, build 1,408.86ms, and JSON 4.08ms. `/api/daily/2026-10-08` reports p50/p95 334/2,114ms, average DB 380.75ms, build 384.82ms, and JSON 0.35ms. The current log's priority-indicator DB unit is milliseconds; its `build_ms` combines provider wait and DTO/indicator work, so it does not isolate those components.

The first Next.js archive slice was measured on the same actual database through read-only SQLite connections, with both HTTP servers on loopback, 5 warm-ups, and 30 warm-cache samples per API. A side-by-side `/api/archive?limit=100` response was byte-for-byte identical through Python and Next; the rendered table also matched the API rows for all 100 dates, report counts, stock counts, and news-observation counts. Python p50/p95 were 1.42/1.87ms; Next proxy p50/p95 were 2.52/3.62ms, both with 26,342-byte bodies. Next `/` server-rendered the archive in p50/p95 5.72/7.51ms (42,181-byte HTML). The page labels Naver report source and the DTO's KST freshness; the API retains its full category and missing-state fields. The temporary Python test server disabled the access-code gate. The main DB file size and write time remained unchanged, but SQLite read-only WAL access may create or update `-wal`/`-shm` coordination files ([SQLite WAL documentation](https://www.sqlite.org/wal.html)); these sidecars were present after the run (0-byte WAL, 32KB SHM) and were left in place because their pre-run state and other possible readers were unknown. Browser paint and cold-cache timings remain unmeasured. This supports the Python API proxy for the first slice: the measured extra hop is about 1.1ms at p50 and 1.8ms at p95, while current DTO and public-boundary logic stay shared. Direct SQLite remains a later option only if a representative route shows the Python HTTP or query path is a material bottleneck.

**Implementation update (2026-10-11, TypeScript archive reader):** The Next `/api/archive` route and the `/` and `/v2` archive pages now read the same development DB directly through Node `node:sqlite` with `readOnly: true` and `PRAGMA query_only`; the DB path is the configured Python path when passed in the Next process, otherwise `data/stock_monitor.db` relative to the project root. A 5-warm-up/30-sample comparison at `limit=100` returned identical DTO fields except for dynamic `now` and the timestamp's byte representation (Python body 26,342 bytes; Next 26,334). Python p50/p95 were 1.62/2.04ms; Next direct read was 5.25/5.87ms. The primary DB file size and write time stayed unchanged during the measurement. The direct route is a migration slice, not a speed claim; `node:sqlite` in Node v24.15 is a release candidate, and Operations PC/WAL behavior remains unverified. Other public routes still use the loopback Python reader.

The date-bound Next.js daily page and `GET /api/daily/{date}` use strict date validation and stored-only query behavior. A follow-up comparison used the development DB, the no-gate loopback Python listener on `8781`, and the Next server with no browser cookies. After 5 warm-ups, 30 warm-cache samples per route returned byte-identical responses: archive was 26,342 bytes with Python p50/p95 1.67/2.15ms and Next 3.51/4.64ms; daily was 64,767 bytes with Python 1.90/2.39ms and Next 3.78/4.42ms. The daily Server Component returned `200` without a login UI and accepted the Python DTO. On a 375px browser viewport, the document stayed 375px wide; the stock table scrolled within its own container, missing target prices displayed as unavailable, and the console had zero errors. This measures layout and warm API latency only; cold latency and browser paint remain unmeasured. The original Python daily log (p50/p95 334/2,114ms) remains an uncontrolled baseline. The `.db` file size and write time stayed at the previously recorded 575,025,152 bytes and `2026-10-09T11:05:06Z`; WAL/SHM sidecars were absent after both test servers stopped. Repeat DTO, access-boundary, and performance checks against the Operations PC database before any cutover review.

**Implementation update (2026-10-11, stock search/detail slice):** `GET /api/stocks/search?date=2026-10-08&q=삼성&limit=8` and `GET /api/daily/2026-10-08/stocks/005930` were compared directly through Python `8781` and Next `3001`, with 5 warm-ups and 30 warm samples each, no browser cookies. Both API bodies were byte-identical: search 2,943 bytes (Python p50/p95 1.52/1.73ms; Next 2.77/3.57ms) and detail 18,817 bytes (Python 1.86/2.30ms; Next 3.23/4.11ms). These show the measured loopback proxy overhead, not a Next.js speedup. Next server-rendered page HTTP timings were 4.90/6.43ms for search (14,946-byte HTML) and 7.31/9.50ms for detail (30,259-byte HTML); these are not browser-paint timings. At the time of measurement, Python `api-perf-summary` entries were cache-heavy: search 279 hits/6 misses, p50/p95 0.071/0.107ms and average DB/build/JSON 0.272/0.411/0.001ms; detail 282 hits/8 misses, p50/p95 0.195/0.261ms and average DB/build/JSON 5.926/10.232/0.008ms. Treat these as preliminary internal cached-path figures, not an uncached benchmark. These routes use stored data only, so they add no external source wait or indicator calculation. At 375px, search showed 8 results and qualified all 8 market values with source/date on or before the selected date; detail's 3 tables scroll within their containers. Both pages returned `200`, showed no access-code UI, internal status codes, or NaN, and the browser reported zero console errors. One Playwright detail-page navigation recorded `responseStart` 9.6ms and first contentful paint 32ms; that single smoke value is not a p50/p95 browser-paint benchmark. Cold timing and representative browser-paint samples remain unmeasured. The Operations PC database parity/performance check remains for the later move.

**Implementation update (2026-10-11, stored watch-candidate slice):** `GET /api/candidate-evidence?date=2026-10-08&limit=8` returned a byte-identical 48,577-byte body through Python `8781` and Next `3001`, with 5 warm-ups and 30 warm samples, no browser cookies. Python p50/p95 were 1.99/2.86ms; Next was 3.42/4.57ms. The Next Server Component page returned 15,974 bytes at p50/p95 5.64/7.14ms. Python's internal summary at the time contained 138 cache hits and 7 misses, p50/p95 0.291/0.594ms, average DB/build/JSON 20.156/20.434/0.020ms; it is a cache-heavy log, not a cold benchmark. Candidate ordering remains the Python builder's, and this page makes no live requests or indicator calculations. At 375px the document remained 375px wide, the 8-row table scrolled internally, no internal fields or login copy appeared, and the console had zero errors. Main Top2 UI is now implemented; its valid external GET calls remain unmeasured because the user-triggered controls were not invoked during automated verification.

**Implementation update (2026-10-11, stored market/flow slice):** Next `/market`, `GET /api/market`, and date-bound `GET /api/flow-trend` now preserve the Python-owned Toss stored DTOs, including snapshot/reference dates, partial/missing state, and investor-flow rows. Python `8781` and Next `3002` returned byte-identical responses for `/api/market` (2,569 bytes) and `/api/flow-trend?date=2026-10-08&limit=5` (10,680 bytes). With 5 warm-ups and 30 warm samples, Python vs Next API p50/p95 were 1.05/1.23ms vs 2.82/3.88ms for market, and 1.06/1.21ms vs 3.29/4.08ms for flow; the Next market Server Component page was 7.79/9.43ms. The measured proxy adds loopback overhead; it does not establish a Next speedup. Python's current internal log is cache-heavy: market p50/p95 0.07/0.10ms and flow 0.08/0.12ms, with average DB/build/JSON 2.83/3.04/0.001ms and 0.02/0.63/0.007ms respectively. At a 375px viewport, the document stayed 375px wide, long tables scrolled inside their containers, and the browser console had no errors. These are warm development-PC samples; cold timing and Operations PC parity/performance remain unverified.

**Implementation update (2026-10-11, stored ETF trend):** `GET /api/etf-trend?date=2026-10-08&limit=5` returned the same 581-byte body through Python `8781` and Next `3002`. With 5 warm-ups and 30 warm samples, Python p50/p95 were 0.91/0.99ms; Next API was 2.72/3.19ms; the Next ETF page was 4.31/5.10ms. The development DB has no eligible ETF snapshot for that selected date, and both paths preserve this missing state. Python's `api-perf-summary` log is cache-heavy: 120 hits/6 misses, p50/p95 0.07/0.17ms and average DB/build/JSON 3.40/3.60/0ms. At 375px the page stayed within the viewport and showed the missing snapshot and no-constituents notice. These warm development-PC timings are not a cutover benchmark.

**Implementation update (2026-10-11, category/rotation/observation slices):** For 5 warm-ups and 30 warm samples, Python `8781` vs Next `3002` API p50/p95 were category 0.98/1.10ms vs 2.77/3.26ms; category trend 0.97/1.14ms vs 2.84/3.42ms; rotation 1.00/1.19ms vs 3.15/3.62ms; observation summary 1.02/1.13ms vs 3.13/3.91ms; backtest observation 1.39/1.95ms vs 3.31/5.05ms. The category page rendered at 6.12/8.00ms, rotation at 6.02/6.84ms, and observation page at 8.30/11.88ms. Category/trend and observation bodies matched byte-for-byte (1,041, 1,102, 16,768, and 7,782 bytes); rotation matched after Next removed the local image `path` (Python 2,411 bytes, Next 2,366). Current Python `api-perf-summary` entries are cache-heavy: category 106/107 hits, p50/p95 0.076/0.317ms; category trend 106/107 hits, 0.072/0.161ms; rotation 120/128 hits, 0.086/17.054ms; observation summary 108/111 hits, 0.199/0.631ms; backtest 107/110 hits, 0.106/0.191ms. These internal cache-heavy figures are not cold benchmarks. At 375px category and observation documents stayed 375px wide; rotation's image loaded with three highlights and no horizontal overflow after correcting the figure margin. The historical backtest remains collapsed under `복기·연구`; no result influences current candidate ordering.

**Implementation update (2026-10-11, Main Top2 and intraday slices):** The local Next Main Top2 page now renders the selected stored cohort first; separate buttons request Naver market-top overlap, bounded Top2 Toss/Naver quotes, latest-date market context, and the adjusted-candle indicator projection. The SSR page itself makes no live request. At 375px, the page stayed within the viewport and showed all four controls; a browser network check recorded no data API request until a user action, and the console had zero errors. The Main route validates the complete schemaVersion 1 allowlist, chart series, source/finality fields, and user-defined condition states. The valid live-source GET buttons were not clicked during automated verification, so there is no new Python-vs-Next live-provider latency/parity result. The existing Python log's `/api/priority-indicators?date=2026-10-08` remains an uncontrolled baseline (p50/p95 1,459/2,211ms; average DB 0.08ms, build 1,408.86ms, JSON 4.08ms); `build_ms` combines provider wait and calculation work. Separately, stored `GET /api/intraday?date=2026-10-08` returned a byte-identical 1,123-byte body through Python and Next. With 5 warm-ups and 30 warm samples, Python vs Next API p50/p95 were 0.97/1.05ms vs 3.18/4.60ms; the Next Main page rendered at 6.40/9.52ms and the intraday history page at 5.97/27.99ms. Python's current `api-perf-summary` entry for intraday is cache-heavy (111/114 hits, 0.081/0.137ms p50/p95, average DB/build/JSON 0.114/0.184/0.001ms). These are warm development-PC measurements; the Operations PC check remains after the move.

**Follow-up update (2026-10-11, Next route coverage and Main Top2 follow-up):** The Python public GET route inventory is represented by Next route handlers, except `/auth/login` and `/auth/logout`, which are intentionally absent because Next has no access-code gate; operator/status routes also remain absent. This is route coverage, not a completed migration: most handlers still call the loopback Python GET bridge. The fixed Naver overlap request performs a same-date stored-status preflight; historical/missing eligibility returns the stored daily DTO without calling the Python live query, and the page disables the button. An E2E request for 2026-10-08 verified both live-fetch flags stayed false. Main Top2 shows separate entry/exit thresholds and strict reached/missed states; RSI 14 is the default chart series.

**Earlier implementation snapshot (2026-10-12, before direct daily DTO):** At that stage, the Windows developer preview was at `127.0.0.1:3006` and the required loopback Python bridge was at `127.0.0.1:8781`. Ten stored GET projections read SQLite through Next's read-only connection and nine other APIs remained on the Python bridge. Operator, admin-gui, and `/auth/*` routes were not moved. The developer PC reported Node `v24.15.0` and Python `3.10.11`; the `3006` launch path passed the effective DB path, timezone, and holiday calendar to Next without printing `.env`. This historical snapshot and its measurements below are superseded by the latest daily DTO follow-up. The earlier category, candidate, and intraday timings remain development-PC observations and do not establish a general speedup or SLO. The Operations PC DB/runtime and production start/recovery path remain unverified.
**Follow-up implementation update (2026-10-12, rotation overlay):** Next `/api/rotation-overlay` and `/daily/{date}/rotation` now use one read-only SQLite snapshot; `/assets/cycle.jpg` serves only the fixed project image. The API keeps GET-only behavior and omits the image path. The Python rollback builder now limits ETF candidates to exact-date `toss_openapi` rows, matching the data-governance rule. A temporary SQLite fixture compared dated-snapshot and legacy-fallback DTOs against Python; it also covered KRX/Toss rows for one ETF, active-vs-held mappings, missing dates, broker labels, and unchanged DB file stats. `scripts/start_next_web_view.ps1` now carries the resolved coordinate-config path into Next. Typecheck, production build, unit tests (52/52), Python rotation tests (2/2), and route E2E (24/24) passed. With 5 warm-ups and 30 sequential requests on the developer PC, `/api/rotation-overlay?date=2026-10-08&limit=5` measured Python p50/p95 1.48/2.23ms (2,411-byte body) and Next 3.70/4.35ms (2,366-byte body); DTOs matched after omitting the private image path. This warm local result shows no speedup and sets no response-time target. The screen and API parity check remains incomplete across other routes, and the Operations PC DB/runtime check is still pending.

**Follow-up UI comparison (2026-10-12):** At 1280×720 on 2026-10-08, Watch showed the same eight candidate cards and Stock the same three default multi-report rows in both apps. Next's `1건 포함` checkbox now applies immediately. Main per-stock news and secondary-screen links start collapsed, matching the summary-first hierarchy. The current full Main document is 1,471px tall versus 1,309px in Python; the added collapsed disclosures and flow panel account for remaining layout differences. Data labels and other routes still need review; this is not full screen parity.

**Follow-up implementation update (2026-10-12, Stock list screen):** `/daily/{date}/stocks` now reads `daily_stock_summaries` and exact-date `toss_openapi` market rows through one read-only SQLite transaction. A temp-database fixture compared row order and displayed values to the Python repository, including a missing stock code, an exact-date KRX-only reference, and a same-code Toss/KRX conflict; DB size and write time did not change. With the Python bridge stopped, the default Stock page still returned `200` with the summary and Toss column. Typecheck, production build, unit tests (53/53), and route E2E (24/24) passed. At the time of this slice, the full daily DTO still used Python; the following update replaces that default path.

**Follow-up implementation update (2026-10-12, direct daily DTO):** `web/src/server/daily-snapshot.ts` now composes the default `/api/daily/{date}` DTO from one caller-owned read-only SQLite transaction. It uses the direct base, candidate, market commentary, news observation, Toss context, and freshness helpers; recursively omits `null` object properties to match Python's compact public response; and keeps the public route's observation-summary deferred state. The Main and selected-date overview Server Components now call the same composer. An explicit, date-gated daily Naver market-top query remains on the Python bridge, along with six full live/backtest API routes. With Python bridge `8781` stopped, the direct daily API, overview, and Main all returned `200`; the bridge was then restored for the remaining API paths. The 2026-10-08 full daily DTO matched Python after omitting only dynamic clock fields. `npm run typecheck`, `npm test` (60/60), `npm run build`, and `npm run test:routes` (25/25) passed. The preview is being served on `127.0.0.1:3010`; no production/Task Scheduler/Operations PC/DB schema changes were made. Direct daily p50/p95 has not been measured yet, and the historical daily latency numbers above measured the old Python bridge path.

**Follow-up implementation update (2026-10-12, direct backtest, Naver quotes, and daily query reduction):** `GET /api/observation/backtest` and the observations page now use one direct read-only SQLite transaction and match the Python DTO, including Python rounding, nullable target notices, and non-empty legacy stock-code strings. `GET /api/priority-current-quotes` now derives Main Top2 codes from the stored candidate reader, enforces the latest-business-date rule, closes its database transaction before requesting the fixed Naver host, rejects redirects, uses an 8-second timeout and 256 KiB response cap, and does not write or reorder data. A review-discovered six-digit-only guard mismatch was reproduced, fixed, and covered along with a missing historical baseline-price case. The stored/default direct route count is now 14; the Top2 Naver quote route is another direct Next endpoint. Four Toss routes and the optional daily Naver market-top query still use the loopback Python bridge. The Next daily composer previously repeated a broad Toss-date union three times; it now shares one date list, fetching only the latest three distinct dates per source. `npm test` (63/63), `npm run typecheck`, `npm run build`, `npm run test:routes` (25/25), and `git diff --check` passed. A 5-warm-up/30-sample same-development-PC HTTP comparison for `2026-10-08` measured Python vs Next daily p50/p95 at 266.77/280.04ms vs 169.52/189.05ms, and backtest at 266.33/268.96ms vs 4.05/4.63ms. Daily response bodies were 64,767 and 64,745 bytes; backtest bodies were both 7,782 bytes. These measurements include local HTTP/response transfer but exclude browser paint, and Python's API cache and Next's direct query have different cache behavior, so they are not a general speedup claim. A separate 7-sample in-process Next daily profile measured total p50/p95 161.07/162.46ms, SQLite statement execution plus row materialization 141.65/143.03ms, and TypeScript composition 19.54/19.80ms across 97 statement executions. The Python `api-perf-summary` log is a mixed hit/miss historical view and does not split out provider wait from build time. No response-time target is set. Browser screenshot comparison shows matching 1120px content width and the corrected five-column freshness block, but Next route tabs still differ from Python's in-place panel switching; that UX parity gap remains open. Preview is active on `127.0.0.1:3010`; Operations PC DB/runtime validation remains for the later move.

Do not add Task Scheduler entries or expose/tunnel these developer ports.

On the warm development PC, `GET /api/daily/2026-10-08` returned a byte-identical 64,767-byte body through Python `8781` and Next `3002` (5 warm-ups, 30 samples): Python p50/p95 1.03/1.20ms; Next 4.59/6.26ms. The Next Main page rendered in 28,234 bytes at p50/p95 9.77/13.10ms; it reads stored candidate evidence and the stored eligibility status in parallel. The user-triggered `/api/priority-indicators?date=2026-10-08` returned HTTP 200 in the browser, preserved two server-selected symbols and dates, rendered the separate condition states, and kept the document at 375px with no console errors. A 5-warm-up/30-sample Python-vs-Next API comparison returned byte-identical 279,524-byte bodies with `live_fetch=true`; end-to-end p50/p95 were Python 302.09/330.82ms and Next 307.22/340.89ms. The current Python `api-perf-summary` row (84 records) reports internal total p50/p95 3.13/1,495.272ms, average DB/build/JSON 0.014/257.436/0.742ms, and route-cache hit/miss 70/14. These are different timing layers: the response's `snapshot.cacheHit` describes indicator source data, while the API log records response-cache hits; `build_ms` still combines provider wait and calculation. The selected-date Naver action was disabled and the fixed API query returned stored data because the date was historical/off-session; E2E verified no live Naver market-top or quote fetch. One Next GET each for Toss Top2 quotes, Naver Top2 fallback quotes, Toss market context, and 90-day daily candles returned HTTP 200 (1,241, 787, 7,533, and 32,721-byte responses); both quote DTOs validated against the server-selected symbols and the candle date/surface matched. The first market-context check found that Python returns `surface: toss-market-context`; the validator was corrected, then the actual Main button displayed the response at 375px with no console errors. Single-request end-to-end times were 1,006, 447, 1,402, and 545ms respectively; these are smoke timings, not p50/p95. The Main current-price button also displayed the Toss response. These measurements are local warm samples, not cold-start or browser-paint benchmarks. The Operations PC database parity/performance check remains for the later move.

No response-time target is set. Keep the measured p50/p95 values as development-PC observations; choose an SLO only after representative Operations PC measurements.

**Done When:**

- This performance-only TODO is not a Next migration acceptance gate. Its historical development-PC measurements are preserved above; the 2026-10-14 migration and N100 completion criteria are owned by [TODO2-NEXT-WEBVIEW-MIGRATION](#-todo2-next-webview-migration-nextjs-public-web-view-replacement).
- Do not repeat development-PC p50/p95 sampling to close this TODO. Complete the separately documented N100 measurement only after Operations-PC DB/WAL validation.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-TG-LIVE-DRYRUN: Telegram Real-Data No-Send Dry Run

**Implementation update (2026-10-01, working-tree only):** Regular and hourly Telegram send failures now produce a nonzero CLI result; empty-alert failures write a failed `delivery_log` row and `intraday/empty-send` operation event; operator health surfaces the latest intraday send status. Ten focused tests passed. No real Telegram send, scheduler change, operating-DB write, deployment, or ambiguous-response retry change was made. The accepted-send/lost-response policy below remains pending.

**Goal:**
Use operating-like stored data to prove Telegram briefing payload quality, paging, retry, and outbox/readiness behavior before any real Telegram send is approved.

**Scope:**

- Run market briefing preview for the key slots against representative recent stored data.
- Compare text and JSON payloads for public-safe wording and evidence coverage.
- Check paging, retry, and outbox/readiness behavior through read-only or no-send paths.
- Simulate a send accepted with a lost response and decide whether ambiguous fragments are held for operator review or resent at-least-once.
- Blocking decision before retry changes: choose between duplicate-avoidance (`unknown`/operator review) and at-least-once resend for ambiguous outcomes.
- Confirm Naver/Toss freshness and ETF/flow coverage are accurate; label legacy KRX explicitly historical and X as lab.
- Keep Telegram real send disabled until a separate explicit approval.

**Done When:**

- Mood/lunch/preclose previews render in the realtime-first order: `오늘 볼 것`, `현재 근거`, `전일 참고`, `부족한 근거`, `복기/연구`.
- Recent-data previews have no generic public trading call, numeric score, broker, or order-routing wording; the separate all-confirmation Main Top2 condition statuses approved 2026-10-09 and clarified 2026-10-10 are governed by [data-governance.md](data-governance.md), with their visible controls and presentation in [surface-guide.md](surface-guide.md).
- Outbox/readiness state can be reviewed without sending.
- Retry/paging behavior has focused test or CLI evidence.
- The selected ambiguous-send policy has a fixture test; do not claim exactly-once delivery from local retry state alone.
- Missing/stale source states are visible in the message instead of hidden.
- No-send preview quality is verified on representative stored dates. The shared operating log informs a later live-send proposal; it does not itself authorize sending.

**Start By Reading:**

- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/surface-guide.md`
- `docs/codex/news-intelligence.md`

### [x] TODO2-WV-CONTENT-QA: Web-View Recent-Date Content QA

**Goal:**
Move beyond fixture smoke and verify that recent-date web-view content is usable, scan-friendly, and public-safe across desktop, tablet, and mobile.

**Completed (2026-09-28):** `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json` scanned 2026-09-28, 2026-09-23, 2026-09-22, and 2026-09-21 with 0 issues; its one warning was the expected not-yet-due 2026-09-28 Toss 20:00 capture. Browser smoke passed for 2026-09-21, 22, 23, and latest 2026-09-28: 0 issues, correct five-tab flow, no horizontal overflow at desktop/tablet/large-mobile/mobile, GET APIs 200, POST 405, and `/api/status` 404. Manual first-read review of 9/21–23 found candidate reasons, evidence, missing states, and source/date labels understandable; no content fix was evidenced. The internal sort field remained absent and candidate order unchanged.

**Current navigation note (2026-10-01):** The current implementation has three top-level tabs (`메인`, `관찰`, `종목`); market and rotation/ETF references are nested or collapsed panels. The five-tab wording above remains the dated 2026-09-28 smoke record, not current navigation.

**Scope:**

- Select several recent business dates from stored data.
- Run value QA and browser smoke for daily, watchlist/candidate, stock detail, market, and ETF rotation surfaces.
- Review empty states, stale source indicators, search behavior, and candidate/news evidence labels.
- Confirm public DTOs do not expose raw sentiment, internal recommendation payloads, numeric scores, buy/sell calls, broker execution, or order-routing language; reconcile documented `rank_reference` with the current public projection.
- Recursively check candidate and daily JSON payloads for `sort_value_signal` and any Toss-backed fields still labeled `krx_reference_date` / `value_context.krx`; keep internal selection order unchanged.
- Capture any content-quality defects as concrete follow-up items instead of broad redesign work.

**Done When:**

- Multiple representative recent dates have CLI/browser evidence and first-read usefulness is recorded. The shared operating log is reused rather than requiring a separate 10-day sample for every TODO.
- Desktop/tablet/mobile smoke finds no blocking overlap or broken navigation.
- Public-safe wording scan passes.
- Internal numeric sort fields are absent, Toss-backed values use accurate source/date labels, and internal candidate order is unchanged.
- Empty/low-evidence states are understandable without operator context.
- Remaining defects are listed with date, surface, symptom, and suggested fix.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/news-intelligence.md`

### [ ] TODO2-DATA-FRESHNESS-LIVE: Live Source Freshness Verification

**Goal:**
Validate current Toss freshness and stored ETF/flow coverage on representative dates; label historical KRX and X/lab data separately.

**Implementation update (2026-09-28):** local capture coverage, metadata classification, snapshot-date ownership, and operator-health propagation are implemented. Operator status now queries the Toss close task and treats an overdue skipped capture as missing; web-view and market-briefing freshness share partial-capture status and missing domains. A read-only 2026-09-28 sample showed reports exact for 9/28, Toss market stale at 9/23, ETF missing, and investor flow stale at 9/17 in both stored-data views. The latest stored 9/23 capture event was `completed` with `candidate_missing=0`, so these states reflect age/coverage for the 9/28 candidates rather than a failed 9/23 capture. The no-send market-briefing preview separately labeled its Top2 Toss quote current at 08:49; web-view remained stored-only (`configured`, no live fetch). At 09:01, the Toss close task was healthy and capture was pending before 20:05. This TODO remains open until after-close capture evidence and additional operating dates are checked.

**Scope:**

- Re-run `data-source-lane-audit --json` and compare with web-view/Telegram freshness output.
- Verify that Toss capture completeness and the date used by the web-view agree; candidate-only rows must not advance the market snapshot date.
- Check that KOSPI/KOSDAQ indices, market flow, Top20 stock/ETF classification, and quote/flow references for all valid daily-summary close-reassessment candidates have explicit missing-state coverage; the public priority projection remains Top2.
- Carry incomplete `stock_metadata_available` and source component gaps into `partial` capture status instead of classifying unknown securities as stocks.
- Confirm `operator-status`/health surfaces failed or partial `poll-news` and `toss-market-context` events after their due windows.
- Keep KRX latest-date/publication rules only for historical analysis and recovery; do not use KRX as a current-view fallback.
- Verify ETF/index data presence and keep ETF constituents marked clearly when not loaded.
- Treat the promoted bounded Toss Top2/Top20 projection as `production_limited`; keep account/order, broad polling, and other Toss endpoints on hold, and keep X as lab.
- Document source-specific stale/missing cases with commands and observed dates.

**Done When:**

- Source lanes remain classified as production, production_limited, lab, or hold.
- Freshness output is consistent across CLI, web-view, and Telegram preview.
- Partial Toss capture does not appear as a complete current snapshot or a clean operator-health state.
- Historical KRX/flow data is explicitly historical-only. Missing or stale Toss data remains visible and is never filled from KRX.
- ETF constituent absence is explicit and not presented as loaded coverage.
- Promoted Toss projections may serve the bounded public GET-only `web-view` route and approved market-briefing context only; they do not connect to `admin-gui`, account/order endpoints, broad polling, or unapproved DB writes. X remains disconnected from production runtime paths.
- Any source gap has a dated evidence note and next action.

**Start By Reading:**

- `docs/codex/data-governance.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/toss-openapi-lab.md`

### [ ] TODO2-NI-EVAL: News Evidence Quality Evaluation

**Goal:**
Evaluate whether the news-intelligence evidence layer is useful on real samples, not only structurally present.

**Scope:**

- Sample recent dates and mentioned stocks with stored observations.
- Review candidate linkage labels, source modes, direct/caution/market-context separation, and stale or mislabeled source cues.
- Identify duplicate, stale, weak, or misleading evidence cases.
- Confirm raw sentiment/impact/internal recommendation details remain out of public surfaces.
- Turn quality issues into focused tests or CLI/report improvements.

**Done When:**

- Sample cases have a reviewed evidence table or CLI output.
- False-positive, duplicate, stale, and weak-evidence cases are classified.
- The review records whether direct/caution/no-match news changed the current top-2 reading or only belonged in fallback/detail.
- At least one quality improvement is implemented if a repeated defect appears.
- Public projection remains recommendation-safe.
- Remaining evaluation gaps are tied to specific sample dates or source lanes.

**Start By Reading:**

- `docs/codex/news-intelligence.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-ADMIN-ACCESS: Admin/Web-View Access Boundary Verification

**Goal:**
Verify the admin-gui, web-view, and future operator-review boundary in an operating-like environment without manipulating production admin processes unless explicitly approved.

**Scope:**

- Run `admin-boundary-audit --json` against the available approved DB/environment.
- Confirm web-view remains GET-only and does not expose operator/admin payloads.
- Confirm admin-gui remains operator-only and does not become a public evidence review surface.
- Keep future operator-review reserved unless separately scoped.
- Prepare operating-PC access checks that do not include process control by default.

**Done When:**

- Boundary audit is clean or lists concrete blockers.
- Public web-view rejects unsafe methods and lacks admin/status/operator endpoints.
- Admin-gui surfaces do not expose public-facing recommendation/evidence review content incorrectly.
- Operator-review remains explicitly reserved/unimplemented.
- Any operating-PC process action is separated behind an explicit approval step.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `tests/test_admin_gui.py`
- `tests/test_operator_status.py`

## Lab Branches To Keep Separate

| Branch / Lane | Todo Link | Current Rule |
| --- | --- | --- |
| `toss-openapi-readonly-lab` | `TODO-DATA` | Applies to account/order and other unapproved Toss endpoints. The approved bounded 20:00/Top2/Top20 lanes follow [market-data-runbook.md](market-data-runbook.md). |
| `telegram-market-briefing-slots` | `TODO-TG` | Product text/slot refinement lane; merge into dev when it improves the shared briefing contract. |
| `x-browser-recap-lab` | `TODO-DATA` | No-login/public-access feasibility lane; do not depend on an authenticated browser session by default. |

## Default Prompt Template

Use this when starting a todo item:

```text
<project root> 범위에서 dev 브랜치 기준으로 진행해줘.

목표:
<TODO-ID>를 진행한다. docs/codex/operating-guide.md의 해당 항목을 기준으로,
새로운 작은 기준/guard를 늘리기보다 실제 화면/출력/동작으로 확인 가능한 결과를 만든다.

전제:
- 관련 canonical docs를 먼저 확인한다.
- 운영 DB write, scheduler 등록/변경, Telegram 실발송, broker/order-routing은 명시 승인 전까지 하지 않는다.
- lab branch 내용은 실제 dev/main 반영분과 구분한다.
- public/shared surface에는 점수, 매수/매도, 주문/브로커 실행 표현을 노출하지 않는다.
- 구현 후 최소 검증을 실행하고, 커밋/푸시는 별도 지시가 있으면 한 번에 처리한다.

보고:
- 진행한 TODO-ID
- 실제 산출물
- 검증 결과
- 아직 남은 범위
- 다음에 이어갈 명령 예시
- 한줄리뷰
```

## Operator Market Research Note Run

When the operator needs daily market context beside the existing Top2 snapshot, keep the flow local and manual:

```powershell
python -m stock_monitor market-research-note --snapshot data\reviews\realtime-first\YYYY-MM-DD_1500.json --market-flow data\reviews\market-research\YYYY-MM-DD_flow.json
```

This command reads local JSON and writes a local JSON/Markdown review note. It does not fetch a provider, write SQLite, send Telegram, register a scheduler, or connect a public surface. Treat `invalid_for_slot` as an operational timing exception, not as market evidence.

`market-research-note` remains a local manual review artifact. The weekday `StockMonitor-Poll` task is the separate operating lane: every 30-minute in-window poll rebuilds report summaries and then collects bounded news observations for the same Top2 candidate codes. The shared `scheduled_run_at` and codes are recorded as a `poll-news` operation event.
