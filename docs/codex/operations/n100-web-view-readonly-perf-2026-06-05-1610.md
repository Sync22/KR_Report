# N100 web-view read-only observation

- scope: 2026-06-05 16:10 KST production `web-view` read-only observation on `<LOCAL_WEB_VIEW_URL>/`
- assumptions: no operator temporary access code was available inside this run context, so production post-gate UI could not be entered without violating the access boundary
- success criteria / verification commands:
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/health`
  - `.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json`
  - `.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json`
  - headless Playwright read-only root-page inspection against `<LOCAL_WEB_VIEW_URL>/`

## Health

- status: `200 OK`
- latency_ms: `2244.55`
- body: `ok`

## Browser Smoke

- business_date: `2026-06-05`
- issue_count: `0`
- api_checks:
  - `GET /api/daily/2026-06-05 -> 200`
  - `GET /api/daily/{date}?intraday_market_top=1 -> 200`
  - `GET /api/candidate-evidence -> 200`
  - `GET /api/daily/{date}/stocks/{stock_code} -> 200`
  - `POST /api/daily/2026-06-05 -> 405`
  - `GET /api/status -> 404`
- mobile_overflow:
  - desktop `0px`
  - tablet `0px`
  - large_mobile `0px`
  - mobile `0px`
- intraday_button_initial_state:
  - smoke-visible: `true` on all tested viewports
  - overlap_panel_present: `true`
  - overlap_panel_initial_visible: `false`
- news_observation_visibility:
  - `observation_summary_main_visible=false`
  - `watch_observation_summary_visible=true`

## Production Gate Observation

- root_title: `Stock Monitor 입장코드`
- access_gate_present: `true`
- access_gate_passed: `false`
- visible_text:
  - `입장코드 입력`
  - `사용자용 웹뷰 접근을 위해 지정된 코드를 입력하세요.`
  - `입장코드`
  - `입장`
- blocker: operator temporary access code was not available to this run, so the production post-gate UI could not be entered without violating the access boundary

## Intraday Button / Candidate / Search / News

- production post-gate observation: blocked by access gate
- `장중 거래대금 확인` button live click timing: not measured
- disabled/off-hours exact text: not observed
- status text / panel rows / chip names / market_status / `장중` text / `확인 HH:MM` text: not observed
- 30-second guard or cached-result second click behavior: not observed
- candidate card click -> stock detail fill: not observed
- stock search stable result: not observed
- exact visible news observation summary/badge/detail text after gate: not observed
- fallback evidence from smoke:
  - watch tab opens successfully on desktop/tablet/large-mobile/mobile
  - stock panel clickable on all tested viewports
  - market panel clickable on all tested viewports
  - rotation panel clickable on all tested viewports
  - candidate panel present on all tested viewports

## API Perf Summary

- `/api/daily/{date}` using `/api/daily/2026-06-05`
  - count `46`, cache `25 hit / 21 miss`
  - p50 `2.763 ms`, p95 `9331.194 ms`, max `23836.118 ms`
  - avg_db `1414.671 ms`, avg_build `2887.237 ms`
- `/api/daily/{date}?intraday_market_top=1` using `/api/daily/2026-06-05?intraday_market_top=1&market_top_limit=100&market_top_page_size=20`
  - count `13`, cache `0 hit / 13 miss`
  - p50 `500.546 ms`, p95 `32482.916 ms`, max `32482.916 ms`
  - avg_db `265.578 ms`, avg_build `5065.734 ms`
- `/api/candidate-evidence` using `/api/candidate-evidence?date=2026-06-05&limit=20`
  - count `45`, cache `25 hit / 20 miss`
  - p50 `1.141 ms`, p95 `2615.19 ms`, max `2842.548 ms`
  - avg_db `351.096 ms`, avg_build `618.769 ms`
- `/api/daily/{date}/stocks/{stock_code}` using `/api/daily/2026-06-05/stocks/383220`
  - count `12`, cache `0 hit / 12 miss`
  - p50 `1941.282 ms`, p95 `4243.198 ms`, max `4243.198 ms`
  - avg_db `441.265 ms`, avg_build `2256.392 ms`
- `/api/archive` using `/api/archive?limit=120`
  - count `157`, cache `77 hit / 80 miss`
  - p50 `23.119 ms`, p95 `328.726 ms`, max `2550.958 ms`
  - avg_db `11.059 ms`, avg_build `92.0 ms`
- `/api/market`
  - count `3`, cache `1 hit / 2 miss`
  - p50 `419.381 ms`, p95 `454.704 ms`, max `454.704 ms`
  - avg_db `259.168 ms`, avg_build `290.907 ms`

## Confirmed Public Boundary

- smoke confirmed `POST /api/daily` remains `405`
- smoke confirmed `/api/status` remains `404`
- root gated page showed only access-gate wording, with no public numeric score, buy/sell, investment grade, trading call, broker execution, or order-routing wording visible before login
- full post-gate public-safe wording review remains blocked until a temporary access code is supplied for the run

## Bottlenecks / Blockers

- largest latency hotspot in the collected perf summary is `/api/daily/{date}?intraday_market_top=1` with `p95=max 32482.916 ms` and `avg_build_ms 5065.734`
- next slow path is `/api/daily/{date}` with `p95 9331.194 ms` and `max 23836.118 ms`
- stock detail path also remains non-trivial at `p50 1941.282 ms`
- primary blocker for this exact 16:10 production observation is the missing operator-provided temporary access code

## One-line Review

- Read-only smoke and API boundary checks are clean, but the exact post-close production UI click observation is incomplete because the live access gate could not be passed in this run.
