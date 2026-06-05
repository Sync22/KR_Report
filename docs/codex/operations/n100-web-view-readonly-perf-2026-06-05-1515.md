# N100 Web-View Read-Only Observation

- observed_at: 2026-06-05 15:15 KST
- scope: `<LOCAL_WEB_VIEW_HOSTPORT>` production web-view read-only observation
- constraints respected: no DB writes, no migrations, no scheduler/Telegram/admin-gui/web-view process changes, no git changes, no secret or access-code disclosure

## Health

- `GET /health`: `200 OK`
- latency: `1820.4 ms`
- body: `ok`

## CLI Smoke

Command:

```powershell
.\.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json
```

Confirmed:

- `business_date`: `2026-06-05`
- `issue_count`: `0`
- `access_code_mode`: `<LOCAL_SMOKE_ACCESS_MODE>`
- `read_only=true`
- `desktop/tablet/large_mobile/mobile horizontal_overflow_px`: all `0`
- `intraday_button`: visible on all four viewports
- `intraday_overlap_initial_visible`: `false` on all four viewports
- `observation_summary_main_visible`: `false` on all four viewports
- `watch_observation_summary_visible`: `true` on all four viewports

Smoke API checks:

| Path | Method | Status |
| --- | --- | --- |
| `/api/daily/2026-06-05` | `GET` | `200` |
| `/api/daily/{date}?intraday_market_top=1` | `GET` | `200` |
| `/api/candidate-evidence` | `GET` | `200` |
| `/api/daily/{date}/stocks/{stock_code}` | `GET` | `200` |
| `/api/daily/2026-06-05` | `POST` | `405` |
| `/api/status` | `GET` | `404` |

## Browser / Playwright Observation

Attempted direct browser observation against `<LOCAL_WEB_VIEW_URL>/`.

Confirmed:

- direct root request returned `401`
- access gate is present
- visible gate text: `Stock Monitor 입장코드 입장코드 입력 사용자용 웹뷰 접근을 위해 지정된 코드를 입력하세요. 입장코드 입장`
- `access_gate_passed=false`

Operational note:

- Browser plugin Node REPL path failed in this session with a runtime sandbox error before browser attachment.
- Fallback used local Python Playwright for the same read-only observation target.

Blocked items due access gate:

- `장중 거래대금 확인` first click delay to loading text
- first click delay to final panel/result/empty/error state
- final status text, panel rows, chip/result names, `market_status` / `장중`, `trade_time` / `확인 HH:MM`
- second click cooldown or cached-result timing
- candidate-card click to stock detail fill
- stock search stability check
- exact production-gated news observation summary/badge/detail text

Observed browser-side error while gated:

- console: `Failed to load resource: the server responded with a status of 401 (Unauthorized)`

## API Perf Summary

Source:

```powershell
.\.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json
```

Relevant path-family summary from `logs/api_perf.log`:

| path_family | count | p50 ms | p95 ms | max ms | cache hit/miss | avg_db ms | avg_build ms |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `/api/daily/{date}` | 197 | 85.915 | 9016.517 | 26273.607 | 99 / 98 | 1516.069 | 2427.970 |
| `/api/daily/{date}?intraday_market_top=1` | 51 | 2924.139 | 14360.260 | 32482.916 | 2 / 49 | 967.469 | 4782.656 |
| `/api/candidate-evidence` | 179 | 4.486 | 2580.261 | 3936.560 | 98 / 81 | 384.069 | 604.144 |
| `/api/daily/{date}/stocks/{stock_code}` | 54 | 1019.493 | 4722.283 | 15586.345 | 0 / 54 | 373.253 | 1969.727 |
| `/api/archive` | 158 | 28.630 | 329.844 | 2550.958 | 74 / 84 | 11.182 | 123.848 |
| `/api/market` | 3 | 419.381 | 454.704 | 454.704 | 1 / 2 | 259.168 | 290.907 |
| `/api/flow-trend` | 87 | 0.377 | 828.155 | 2384.660 | 61 / 26 | 81.143 | 183.537 |
| `/api/etf-trend` | 85 | 0.629 | 1401.763 | 1912.156 | 57 / 28 | 222.071 | 288.318 |

Bottlenecks:

- worst family is `/api/daily/{date}?intraday_market_top=1`: `p95 14.36s`, `max 32.48s`, `49/51` misses
- next is `/api/daily/{date}`: `p95 9.02s`, `max 26.27s`
- stock detail family is materially slower than candidate/archive/market helper routes: `p95 4.72s`, `max 15.59s`

## Public Boundary

Confirmed:

- smoke/API checks show `POST /api/daily` returns `405`
- smoke/API checks show `GET /api/status` returns `404`
- access-gate page visible text did not show numeric score, buy/sell recommendation, investment grade, trading call, broker execution, or order-routing wording

Still unverified on the gated post-login page:

- production page-body scan for public trading-call / investment-grade wording after gate pass

## Blockers

- this session did not include the operator temporary access code needed to pass the live local gate
- therefore required checks `3` through `7` could not be completed on the actual gated production page

## One-Line Review

CLI smoke and API boundary checks were clean, but the 15:15 production UI observation is incomplete because the live `<LOCAL_WEB_VIEW_HOSTPORT>/` page stopped at the access gate.
