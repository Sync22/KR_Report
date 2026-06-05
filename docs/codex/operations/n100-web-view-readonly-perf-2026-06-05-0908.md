# N100 web-view read-only perf check

- check time: `2026-06-05 09:08 KST`
- scope: production-like live `<LOCAL_WEB_VIEW_URL>` read-only observation only
- guardrails: no `.env` read, no access-code bypass, no DB writes, no migrations, no scheduler/Telegram/admin/web-view process changes

## Health

| item | result |
| --- | --- |
| `/health` status | `200 ok` |
| `/health` latency | `2724.94 ms` |

## Smoke summary

Command: `.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json`

| field | result |
| --- | --- |
| `business_date` | `2026-06-05` |
| `issue_count` | `0` |
| `access_code_mode` | `<LOCAL_SMOKE_ACCESS_MODE>` |
| desktop/tablet/mobile overflow | all `0 px` |
| intraday button present | all viewports `true` |
| intraday overlap panel present | all viewports `true` |
| intraday overlap initial visible | all viewports `false` |
| watch observation summary visible | all viewports `true` |
| candidate panel present | all viewports `true` |

Smoke API checks:

| path | method | status |
| --- | --- | --- |
| `/api/daily/2026-06-05` | `GET` | `200` |
| `/api/daily/{date}?intraday_market_top=1` | `GET` | `200` |
| `/api/candidate-evidence` | `GET` | `200` |
| `/api/daily/{date}/stocks/{stock_code}` | `GET` | `200` |
| `/api/daily/2026-06-05` | `POST` | `405` |
| `/api/status` | `GET` | `404` |

## Live route timings

Direct unauthenticated requests to the live listener returned the access gate on protected routes. Per request instruction, this was recorded as `access_gate_401` and not bypassed.

| path | status | latency_ms | note |
| --- | --- | ---: | --- |
| `/api/archive?limit=20` | `401` | `149.96` | `access_gate_401` |
| `/api/daily/2026-06-05` | `401` | `17.36` | `access_gate_401` |
| `/api/candidate-evidence?date=2026-06-05&limit=20` | `401` | `19.12` | `access_gate_401` |
| `/api/market` | `401` | `58.57` | `access_gate_401` |
| `/api/daily/2026-06-05/stocks/383220` | `401` | `38.99` | `access_gate_401`, stock code chosen from read-only DTO |
| `/api/daily/2026-06-05` | `POST 405` | `11.69` | method boundary still enforced |
| `/api/status` | `401` | `135.83` | live listener is gated before route handling |

Access gate page probe:

- `GET /` returned `401`
- visible title text in response HTML: `Stock Monitor 입장코드`

## API perf bottlenecks

Command: `.venv\Scripts\python.exe -m stock_monitor api-perf-summary --json`

Highest total-time entries seen in the summary:

| path | max_total_ms | avg_db_ms | avg_build_ms | notes |
| --- | ---: | ---: | ---: | --- |
| `/api/daily/2026-06-04` | `26273.607` | `1176.994` | `2684.700` | heavy cold-path outlier |
| `/api/daily/2026-06-04/stocks/005930` | `15586.345` | `1167.791` | `8696.132` | stock detail build-heavy |
| `/api/daily/2026-06-02?intraday_market_top=1...` | `14360.260` | `2005.227` | `5713.249` | intraday overlay + upstream fetch risk |
| `/api/daily/2026-05-27?intraday_market_top=1...` | `13268.025` | `1663.387` | `6988.399` | intraday overlay build-heavy |

Highest DB-heavy entries seen in the summary:

| path | avg_db_ms | max_total_ms | note |
| --- | ---: | ---: | --- |
| `/api/daily/2026-05-20` | `3416.776` | `9658.917` | daily payload can become DB-dominant |
| `/api/daily/2026-05-28` | `3062.376` | `7253.702` | daily payload DB pressure |
| `/api/daily/2026-05-21` | `2710.472` | `6496.089` | daily payload DB pressure |
| `/api/candidate-evidence?date=2026-05-26&limit=20` | `2179.208` | `2586.551` | candidate evidence can lean DB-heavy |

### 09:05-09:15 overlap risk

Observed `2026-06-05 09:05-09:15 KST` log window highlights:

| path | count | max_total_ms | max_db_ms | misses |
| --- | ---: | ---: | ---: | ---: |
| `/api/daily/2026-06-05` | `5` | `8288.798` | `6689.873` | `1` |
| `/api/candidate-evidence?date=2026-06-05&limit=20` | `5` | `1503.841` | `1109.945` | `1` |
| `/api/daily/2026-06-05/stocks/383220` | `1` | `1446.832` | `500.452` | `1` |
| `/api/etf-trend?date=2026-06-05&limit=5` | `4` | `1401.763` | `792.072` | `1` |
| `/api/flow-trend?date=2026-06-05&limit=5` | `4` | `738.403` | `237.935` | `1` |
| `/api/daily/2026-06-05?intraday_market_top=1&market_top_limit=100&market_top_page_size=20` | `1` | `442.819` | `8.756` | `1` |

Interpretation:

- The main overlap risk remains the first uncached `/api/daily/2026-06-05` build. In this window it peaked at `8288.798 ms`, with `6689.873 ms` inside DB work.
- `candidate-evidence` is the next notable same-window pressure point. Its cold miss reached `1503.841 ms`, with `1109.945 ms` DB time.
- ETF/flow side panels also contribute on first miss (`1401.763 ms` and `738.403 ms`), but they were materially smaller than the daily payload miss.
- Intraday market-top overlay itself was not the dominant cost in this window (`442.819 ms` on its miss). The broader overlap risk is scheduler-time DB/cache pressure plus any concurrent external-source latency if a fresh intraday overlay also needs upstream data.

## Intraday button click

- actual live browser click: `live_click_blocked_by_access_gate`
- reason: live root returned `401` gate page and no already-authenticated browser session was available without reading or printing an access code
- additional note: Playwright browser automation could not be attached in this session because the shared browser profile was already in use

## News observation summary / badge text

Read-only DTO inspection for `2026-06-05` showed the empty-state path.

Summary card state:

- `available`: `false`
- visible summary label: `뉴스 관찰 없음`
- visible summary reason: `저장된 뉴스 관찰 없음`
- visible summary empty_state: `저장된 뉴스 관찰 없음`
- visible summary connection_note: `우선 확인 후보와 연결할 저장 뉴스 관찰이 없습니다.`

Candidate badge state:

- first candidate stock: `383220` (`F&F`)
- badge `available`: `false`
- visible badge label: `저장 뉴스 근거 없음`
- visible badge reason: `같은 종목의 저장 뉴스 observation이 없습니다.`
- compact line renderer text for empty state: `뉴스 근거: 저장 뉴스 근거 없음`

Stock detail badge state for `383220`:

- `available`: `false`
- visible detail label: `저장 뉴스 근거 없음`
- visible detail reason: `같은 종목의 저장 뉴스 observation이 없습니다.`
- visible detail empty_state: `저장 뉴스 근거 없음`

## GET-only / public-safe boundary

- Smoke confirmed `POST /api/daily` remains `405`.
- Smoke confirmed `/api/status` remains `404` on the ungated local smoke server.
- Direct live unauthenticated access hit `401` before protected GET routes, so no access-code bypass was used.
- No public numeric score, buy/sell, investment grade, trading call, broker execution, or order-routing behavior was exercised or exposed in this check.

## Blockers / hold

- `live_click_blocked_by_access_gate`
- live protected-route timings are limited to gate response times unless an already-authenticated browser session exists
- `/health` was healthy but relatively slow at `2724.94 ms`; this is worth rechecking if morning contention repeats

## One-line review

`2026-06-05 09:08 KST` 기준 live web-view는 health `200 ok`와 GET-only boundary는 유지됐지만, 09:05-09:15 구간의 cold `/api/daily` DB-heavy miss가 가장 큰 성능 겹침 위험입니다.
