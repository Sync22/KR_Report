# N100 web-view read-only observation - 2026-06-05 12:00 KST

## scope

- Target: production `web-view` observation for `<LOCAL_WEB_VIEW_URL>/`
- Mode: read-only only
- DB writes, migrations, scheduler, Telegram, admin-gui, git, and process changes: not performed

## assumptions

- The required temporary access code was not available inside this session, so the actual production root could only be observed up to the access gate response.
- UI interaction timings below were captured on the existing Playwright-backed local smoke mirror path (`web-view-browser-smoke` style temporary local server with access code temporarily disabled) because the gated production root could not be entered.

## success criteria / verification

- `Invoke-WebRequest <LOCAL_WEB_VIEW_URL>/health`
- `.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json`
- `GET <LOCAL_WEB_VIEW_URL>/` for gate presence check
- Read-only Playwright smoke-mirror click/search observation
- `.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json`

## exact path

- Observation markdown: `docs/codex/operations/n100-web-view-readonly-perf-2026-06-05-1200.md`

## confirmed findings

### 1. health / gate

- `GET /health` on `<LOCAL_WEB_VIEW_HOSTPORT>` returned `200` with body `ok`.
- Observed latency: `803 ms`.
- `GET /` on `<LOCAL_WEB_VIEW_HOSTPORT>` returned `401`.
- Access gate status: `access_gate_present=true`, `access_gate_passed=false`, `reason=temporary_code_unavailable_in_session`.

### 2. browser smoke baseline

- `business_date=2026-06-05`
- `issue_count=0`
- `access_code_mode=<LOCAL_SMOKE_ACCESS_MODE>`
- API checks:
  - `GET /api/daily/2026-06-05 -> 200`
  - `GET /api/daily/{date}?intraday_market_top=1 -> 200`
  - `GET /api/candidate-evidence -> 200`
  - `GET /api/daily/{date}/stocks/{stock_code} -> 200`
  - `POST /api/daily/2026-06-05 -> 405`
  - `GET /api/status -> 404`
- Viewport checks:
  - desktop/tablet/large_mobile/mobile `horizontal_overflow_px=0`
  - `intraday_button=true`
  - `intraday_overlap_initial_visible=false`
  - `observation_summary_main_visible=false`
  - `watch_observation_summary_visible=true`

### 3. intraday button observation

- Initial visible text:
  - `리포트 요약 26개 종목 기준으로 Naver 거래대금 상위와 교집합을 확인할 수 있습니다.`
- Button state before click: visible and enabled
- First click timeline on smoke mirror:
  - loading/status text appeared by about `92 ms`
  - final status/error text appeared by about `566 ms`
- First click final status text:
  - `Naver 거래대금 상위 확인 중 오류가 발생했습니다. · Naver 장중 참고 · 호출 0회 · 오류 2건`
- First click panel text:
  - `Naver 장중 참고 · 호출 0회 · 오류 2건`
  - `Naver 거래대금 상위 확인 중 오류가 발생했습니다.`
- First click panel rows: `0`
- First click chip/result names: none
- First click market/freshness text: none rendered
- First click outcome: provider/live-fetch error, no overlap result chips
- Second click:
  - guard text appeared in about `12 ms`
  - status text: `Naver 장중 참고는 30초 간격으로 확인할 수 있습니다.`
  - cached prior error panel remained visible

### 4. candidate card / stock detail / search

- Candidate card click succeeded on smoke mirror.
- Confirmed selected card:
  - `종목 F&F 383220`
- Stock detail filled with visible report text:
  - `테일러메이드 매각 vs 인수 시나리오 분석`
  - `유진투자증권 · 2026-06-05 · 목표가 100,000원 · 매수`
- Search stability:
  - Query `F&F` returned stable `2` results:
    - `F&F 383220 / 당일 리포트 있음 · 저장 KRX 없음 · 뉴스 근거 없음`
    - `F&F홀딩스 007700 / 당일 리포트 없음 · 저장 KRX 없음 · 뉴스 근거 없음`
  - Query `007700` returned stable `1` result:
    - `F&F홀딩스 007700 / 당일 리포트 없음 · 저장 KRX 없음 · 뉴스 근거 없음`
  - Non-current-stock search click did not reliably populate detail during this observation.

### 5. news observation visible text

- Main summary exact visible text:
  - `뉴스 관찰 없음`
  - `저장 뉴스`
  - `저장된 뉴스 관찰 없음`
  - `우선 확인 후보와 연결할 저장 뉴스 관찰이 없습니다.`
  - `저장된 뉴스 관찰 없음`
- Candidate badge exact visible text:
  - `저장 뉴스 근거 없음`
  - `같은 종목의 저장 뉴스 observation이 없습니다.`
- Stock context news state on selected candidate:
  - visible as empty-state wording inside the stock context block
  - effective state: stored news observation unavailable for the selected stock

### 6. GET-only / public-safe boundary

- Confirmed from smoke/API checks:
  - `POST /api/daily -> 405`
  - `/api/status -> 404`
- No numeric score or investment grade wording was observed.
- Public-surface wording issue observed on stock detail:
  - visible text included `매수`
  - this fails the requested `no buy/sell / trading call wording visible` check for the observed smoke-mirror UI path

## api_perf summary

Raw source: `logs/api_perf.log`, summarized from matching route families.

| path_family | count | p50 ms | p95 ms | max ms | cache hit/miss | avg db ms | avg build ms |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `/api/daily/{date}` | 30 | 1.896 | 9189.589 | 23836.118 | 17 / 13 | 1114.573 | 2759.595 |
| `/api/daily/{date}?intraday_market_top=1` | 11 | 480.356 | 25625.789 | 32482.916 | 0 / 11 | 313.226 | 5886.743 |
| `/api/candidate-evidence` | 30 | 1.076 | 2636.593 | 2842.548 | 17 / 13 | 337.909 | 632.413 |
| `/api/daily/{date}/stocks/{stock_code}` | 8 | 2148.691 | 4554.603 | 4722.283 | 0 / 8 | 501.359 | 2658.256 |
| `/api/archive` | 149 | 26.178 | 330.118 | 2550.958 | 71 / 78 | 11.100 | 125.788 |
| `/api/market` | 3 | 419.381 | 451.172 | 454.704 | 1 / 2 | 259.168 | 290.907 |

### api_perf bottlenecks

- Worst path family remains `/api/daily/{date}?intraday_market_top=1` with `p95 25.6s`, `max 32.5s`, all cache misses.
- `/api/daily/{date}` has a fast cache-hit median but still shows a heavy long tail: `p95 9.2s`, `max 23.8s`.
- `/api/daily/{date}/stocks/{stock_code}` is materially slower than `/api/candidate-evidence` and `/api/market`.

## blockers

- Production root gate could not be passed because the temporary operator code was not available in this session.
- Intraday button did not produce result rows in the smoke-mirror observation; it failed with `호출 0회 · 오류 2건`.
- Search result click for a non-current-stock/no-same-day-report entry was not reliable in this run.
- Public-safe wording boundary is not clean because selected stock detail exposed `매수`.

## one-line review

- Read-only surface is healthy and GET-only checks passed, but the noon intraday path is erroring and the stock-detail surface still leaks `매수` wording.
