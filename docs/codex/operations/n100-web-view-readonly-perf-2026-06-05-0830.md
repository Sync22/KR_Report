# N100 Pre-Open Web-View Read-Only Perf Check

- requested_window: `2026-06-05 08:30 KST`
- observed_window: `2026-06-05 09:25` to `2026-06-05 09:48` KST
- scope: read-only production `web-view` pre-open health, access-gate, smoke, and stored-data perf check
- verification_commands:
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/health`
  - `.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/api/archive?limit=20`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/api/daily/2026-06-05`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/api/candidate-evidence?date=2026-06-05&limit=20`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/api/market`
  - `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/api/status`
  - `.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json`

## Health Result

- local live target: `<LOCAL_WEB_VIEW_URL>`
- `GET /health` -> `200`, body `ok`
- measured live latency: `2961.22 ms`
- interpretation: loopback service was up, but pre-open health latency was still close to `3.0s`

## Smoke Result

- `surface=web-view-browser-smoke`
- `business_date=2026-06-05`
- `read_only=true`
- `access_code_mode=<LOCAL_SMOKE_ACCESS_MODE>`
- `issue_count=0`
- required smoke API checks:
  - `GET /api/daily/2026-06-05` -> `200`
  - `GET /api/daily/{date}?intraday_market_top=1` -> `200`
  - `GET /api/candidate-evidence` -> `200`
  - `GET /api/daily/{date}/stocks/{stock_code}` -> `200`
  - `POST /api/daily/2026-06-05` -> `405`
  - `GET /api/status` -> `404`

## Mobile / Layout Observation

- tested viewports: `desktop`, `tablet`, `large_mobile`, `mobile`
- all four viewports reported tab order `main / watch / stock / market / rotation`
- `search_input=true`, `intraday_button=true`, `intraday_overlap_panel=true`, `candidate_panel=true`
- `watch_observation_summary_visible=true` on all viewports
- `observation_summary_main_visible=false` and `intraday_overlap_initial_visible=false` on all viewports
- `horizontal_overflow_px=0` on all viewports

## Live Route Timing

| Route | Method | Status | Latency ms | Note |
| --- | --- | ---: | ---: | --- |
| `/` | `GET` | `401` | `57.15` | `access_gate_401`; returned login page title `Stock Monitor 입장코드` |
| `/api/archive?limit=20` | `GET` | `401` | `10.65` | `access_gate_401` |
| `/api/daily/2026-06-05` | `GET` | `401` | `7.42` | `access_gate_401` |
| `/api/candidate-evidence?date=2026-06-05&limit=20` | `GET` | `401` | `4.94` | `access_gate_401` |
| `/api/market` | `GET` | `401` | `3.66` | `access_gate_401` |
| `/api/daily/2026-06-05/stocks/<stock_code>` | `GET` | n/a | n/a | live stock code was not discoverable without bypassing the gate |
| `/api/daily/2026-06-05` | `POST` | `405` | `4.34` | method block intact on the protected live route |
| `/api/status` | `GET` | `401` | `3.76` | live gate blocked before route-level `404`; smoke still confirmed `404` behind the local smoke server |

## Access Gate / Browser Observation

- direct live root and JSON routes were access-gated; no access code, `.env`, secret, cookie value, token, or bypass was supplied
- browser snapshot on `<LOCAL_WEB_VIEW_URL>/` showed:
  - title: `Stock Monitor 입장코드`
  - heading: `입장코드 입력`
  - helper text: `사용자용 웹뷰 접근을 위해 지정된 코드를 입력하세요.`
- actual intraday market-top click was not attempted against user data because no already-authenticated browser session was available
- recorded result: `live_click_blocked_by_access_gate`

## Stored-Data Perf Baseline

- source: `logs/api_perf.log`
- summary snapshot: `record_count=864`, `endpoint_count=97`
- latest relevant stored-data rows remained date-bound to `2026-06-04`; there was no dated perf row for `2026-06-05` yet

| Stored-data route | Count | Cache hits/misses | p50 total ms | p95 total ms | avg db ms | avg build ms |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `/api/daily/2026-06-04` | `48` | `29 / 19` | `10.051` | `13884.595` | `1176.994` | `2684.700` |
| `/api/daily/2026-06-04?intraday_market_top=1&market_top_limit=100&market_top_page_size=20` | `10` | `2 / 8` | `297.233` | `10352.149` | `899.407` | `2225.672` |
| `/api/daily/2026-06-04/stocks/005930` | `3` | `0 / 3` | `6198.846` | `15586.345` | `1167.791` | `8696.132` |
| `/api/candidate-evidence?date=2026-06-04&limit=20` | `47` | `30 / 17` | `4.707` | `1522.403` | `166.670` | `439.411` |
| `/api/archive?limit=20` | `3` | `0 / 3` | `2201.996` | `2357.626` | `12.219` | `1573.743` |
| `/api/market` | `3` | `1 / 2` | `419.381` | `454.704` | `259.168` | `290.907` |

## Bottleneck Candidates

- by `p95_total_ms`, the worst relevant path was stock detail `'/api/daily/2026-06-04/stocks/005930'` at `15586.345 ms`; most of that cost sat in `avg_build_ms=8696.132`, not JSON serialization
- the dated daily overview `'/api/daily/2026-06-04'` stayed the main high-volume pressure point with `p95_total_ms=13884.595 ms`, `avg_db_ms=1176.994`, and `avg_build_ms=2684.700`
- the intraday overlap variant `'/api/daily/2026-06-04?intraday_market_top=1...'` remained the next material pre-open risk with `p95_total_ms=10352.149 ms` and `8/10` cache misses
- by `avg_db_ms`, heavier historical dated daily rows still clustered on earlier uncached paths such as `2026-05-20` and `2026-05-28`, but for the current pre-open baseline the dated daily overview and slow stock-detail path were the relevant live-facing concerns
- `candidate-evidence` and `market` were materially lighter than the daily and stock-detail builders

## News Observation / Badge State

- exact empty-state text confirmed from current render contract and tests:
  - daily summary empty state: `저장된 뉴스 관찰 없음`
  - candidate badge empty state: `저장 뉴스 근거 없음`
- exact available-state labels currently rendered by the stored-data contract:
  - `뉴스로 후보 강화`
  - `주의 뉴스 확인`
  - `시장 맥락 참고`
  - `KRX 기준일 확인 필요`
  - `뉴스 근거 부족`
- live protected page content could not be verified past the access gate without an authenticated session, so this run did not confirm which one of those labels was visible on `2026-06-05`
- smoke evidence still confirmed the summary area existed on the watch tab and did not register a visibility/layout issue

## GET-Only / Public-Safe Boundary

- confirmed again that `POST /api/daily/2026-06-05` remained `405`
- smoke confirmed `/api/status` remained `404` on the user-data smoke surface
- direct live requests returned `401` before route evaluation, so live `401` on `/api/status` is interpreted as gate protection, not public admin exposure
- no public numeric score, buy/sell wording, investment grade, broker execution, or order-routing behavior was introduced or exercised in this check

## Blockers / Hold Items

- hold: direct live route timings reflect the access gate, not post-auth payload latency
- hold: live intraday button click remained blocked because no already-authenticated browser session was available without secrets
- hold: news observation visible label for `2026-06-05` could not be confirmed on the protected live page after the gate; only the stored-data contract text set was confirmable
- blocker: none for the read-only observation pass

## One-Line Review

- healthy loopback and intact access gate, but pre-open stored-data latency risk still concentrates in dated daily, intraday overlap, and stock-detail build paths
