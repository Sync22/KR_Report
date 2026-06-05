# Web-View Read-Only Performance Observation 2026-06-05

## Scope

- Environment: operating mini PC, existing local web-view process.
- Base URL: local loopback web-view.
- Observation time: 2026-06-05 around 00:20 KST.
- Data date observed: latest stored report date `2026-06-04`.
- Access gate was used for browser observation, but the code value is intentionally not recorded here.

## Guardrails

- No DB write, migration, scheduler change, Telegram send, admin-gui change, or web-view restart was performed.
- No `.env`, secret, cookie, or access-code value is recorded.
- Intraday direct checks were limited to the requested read-only GET contract and existing web-view route.

## Basic Health

- `/health`: `200 ok`.
- `web-view-browser-smoke --date latest --json`: `issue_count=0`.
- Smoke API contract:
  - `GET /api/daily/2026-06-04`: `200`
  - `GET /api/daily/{date}?intraday_market_top=1`: `200`
  - `GET /api/candidate-evidence`: `200`
  - `GET /api/daily/{date}/stocks/{stock_code}`: `200`
  - `POST /api/daily/{date}`: `405`
  - `GET /api/status`: `404`

## Screen Observation

### `/`

- Main page loaded after access gate.
- Archive calendar showed report-count cells for recent stored dates. News count DOM placeholders existed, but visible count text was empty for the latest observed date.
- Main news observation summary showed empty state:
  - `뉴스 관찰 없음`
  - `저장된 뉴스 관찰 없음`
  - `우선 확인 후보와 연결할 저장 뉴스 관찰이 없습니다.`
- Candidate cards in the watch tab showed public-safe empty news badges:
  - `저장 뉴스 근거 없음`
  - `같은 종목의 저장 뉴스 observation이 없습니다.`
- Candidate card click on first candidate switched to the stock tab, but selected stock detail did not populate. Follow-up UI click contract check is recommended.
- Stock detail API itself returned `200`, so the issue is likely UI click/selection wiring rather than the stock-detail endpoint.
- ETF rotation evidence was visible in the rotation tab. Example observed: KODEX/TIGER ETF rows with stored reference date `2026-06-02` and an explicit stale-reference note for selected date `2026-06-04`.
- Stock search was available. One observation returned stored Samsung rows with empty news evidence wording; a later date-bound search attempt returned no visible result. Treat stock-search behavior as needing another focused pass before calling it fully clean.

### `/v2`

- `/v2` loaded as `KR-Stock Web View V2`.
- It stayed a preview route and did not replace `/`.
- It showed:
  - `KR-Stock V2 Preview`
  - stored-data / GET-only markers
  - candidate cards with `저장 뉴스 근거 없음`
  - evidence layers including report/news/KRX/ETF sections
- No forbidden public-safe terms were observed in `/v2` body sample.

## Intraday Market-Top Button

- Button was visible with id `intraday-market-top-check`.
- At observation time the button was disabled because the market was outside regular trading hours.
- Status text:
  - `오늘 정규장 시간에만 확인 할 수 있습니다.`
- UI click attempts:
  - First click: not executed because button was disabled; Playwright timed out after about `5008 ms`.
  - Second click: not executed because button was disabled; Playwright timed out after about `5017 ms`.
- Panel:
  - `intraday-market-top-overlap` remained hidden.
  - chip count: `0`.
- No timeout/provider-empty/WinError 10013 was observed through the disabled UI path.

Read-only route timings for the same date:

- First `GET /api/daily/2026-06-04?intraday_market_top=1&market_top_limit=100&market_top_page_size=20`: `200`, about `235.9 ms`.
- Second same GET: `200`, about `6.5 ms`.
- This suggests the optimized/cached route is effective when base payload/cache is warm. The actual button UX still needs an in-hours observation because the button is disabled outside regular market time.

## API Perf Summary

`api-perf-summary --json` reported:

- records: `765`
- endpoint families: `86`

Key route families:

| path_family | sample p50 ms | sample p95 ms | sample max ms | cache | avg_db_ms | avg_build_ms | note |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `/api/daily/{date}` | `7.298` | `9551.905` | `26273.607` | 28 hit / 16 miss on 2026-06-04 sample | `935.962` | `2389.983` | Cold build remains the main long-tail risk. |
| `/api/daily/{date}?intraday_market_top=1` | `297.233` | `10352.149` | `10352.149` | 2 hit / 8 miss on 2026-06-04 sample | `899.407` | `2225.672` | `path_family` is present; warm direct check was fast. |
| `/api/candidate-evidence` | `324.524` | `897.227` | `897.227` | 0 hit / 2 miss on sample | `234.678` | `608.693` | Not current bottleneck in latest sample. |
| `/api/daily/{date}/stocks/{stock_code}` | `1473.700` | `1656.826` | `1656.826` sample; worst `15586.345` | 0 hit / 5 miss sample | `587.961` | `1333.146` | Stock detail has occasional long tail. |
| `/api/archive` | `207.829` | `300.629` | `300.629` sample; worst `2550.958` | 0 hit / 2 miss sample | `3.347` | `231.992` | Generally acceptable. |
| `/api/etf-trend` | `0.342` | `1465.076` | `1912.156` | 15 hit / 7 miss on 2026-06-04 sample | `297.900` | `364.883` | Warm path is cheap; cold path acceptable. |

## Public-Safe Check

The checked DOM/DTO samples did not expose:

- `sentiment_score`
- `stock_impact`
- `operator_recommendation`
- `recommendation_support`
- `buy/sell`
- `trading call`
- `order-routing`
- `broker execution`
- `numeric score`

One caveat: user-facing Korean text includes normal report opinion words such as `매수` in broker report opinion context. That is existing report metadata, not a public trading call or order-routing surface.

## Bottleneck Candidates

1. Daily cold build remains the largest long-tail risk.
2. Stock detail has an occasional long tail and should be profiled separately.
3. Intraday market-top optimized path appears much faster when warm, but UI button latency cannot be concluded from this off-hours run.
4. Candidate evidence, archive, ETF trend are not the main bottleneck in this observation.

## Follow-Up

- Repeat intraday button UI click during regular market hours, preferably 09:05-09:15 and 12:00 KST.
- Re-check candidate-card click and stock-search click-to-detail behavior; observed candidate click switched tabs but did not load selected detail.
- If detail click issue reproduces, handle as a UI routing/selection bug, separate from backend API performance.

## One-Line Review

The latest web-view is read-only/public-safe and the optimized intraday route is visible in perf logs, but actual button UX still needs in-hours validation because the button was disabled during this run.
