# N100 Web-View Read-Only Perf Makeup - 2026-06-05 10:17 KST

## Scope

- Purpose: makeup check for the missed/blocked live intraday button portion of the 08:30 and 09:08 automations.
- Mode: read-only web-view observation.
- DB write: no.
- Migration: no.
- Scheduler/Telegram/admin-gui/web-view process changes: no.
- Secret/access-code output: no. The provided temporary entry code was used only to pass the local access gate for this browser check.

## Automation Status

- `n100-detailed-pre-open-web-view-read-only-check` did run and wrote `docs/codex/operations/n100-web-view-readonly-perf-2026-06-05-0830.md`.
- `n100-detailed-market-open-web-view-read-only-check` did run and wrote `docs/codex/operations/n100-web-view-readonly-perf-2026-06-05-0908.md`.
- Both runs recorded the same practical gap: the live root page was behind the access gate, so actual browser button click was blocked instead of measured.
- Remaining scheduled automations are still active for 12:00, 15:15, 16:10, and 20:00 KST.

## Basic Health

- `/health`: `200 ok`.
- Manual health probe latency at 10:13 KST: `7989.4 ms`.
- `web-view-browser-smoke --date latest --json`: `issue_count=0`, `business_date=2026-06-05`.
- Smoke GET-only checks:
  - `GET /api/daily/2026-06-05`: `200`
  - `GET /api/daily/{date}?intraday_market_top=1`: `200`
  - `GET /api/candidate-evidence`: `200`
  - `GET /api/daily/{date}/stocks/{stock_code}`: `200`
  - `POST /api/daily/2026-06-05`: `405`
  - `GET /api/status`: `404`
- Smoke mobile overflow: `0 px` for desktop/tablet/large_mobile/mobile viewports.

## Browser Intraday Button Observation

- Access gate: passed with temporary provided entry code; the value is not recorded here.
- Button visible: yes.
- Button enabled: yes.
- First successful observed panel state:
  - Status: `Naver 거래대금 상위와 리포트 언급이 겹친 종목: 삼성전기, 라이콤, 피에스케이 · Naver 장중 참고 · 호출 10회`
  - Panel rows:
    - 삼성전기 `009150` KOSPI 7위, `7,270억`, `장중`, `확인 10:14`
    - 라이콤 `388790` KOSDAQ 19위, `390억`, `장중`, `확인 10:14`
    - 피에스케이 `319660` KOSDAQ 22위, `336억`, `장중`, `확인 10:14`
    - RFHIC `218410` KOSDAQ 42위, `159억`, `장중`, `확인 10:14`
- Repeat click inside the 30-second guard:
  - UI response: `Naver 장중 참고는 30초 간격으로 확인할 수 있습니다.`
  - Panel remained visible with the previous rows.
- After cooldown:
  - Loading text appeared in about `0.42 s`.
  - Final panel updated to `확인 10:17`.
  - api_perf recorded the actual intraday route request at `32482.916 ms`.
  - Final rows:
    - 삼성전기 `009150` KOSPI 7위, `7,346억`, `장중`, `확인 10:17`
    - 라이콤 `388790` KOSDAQ 19위, `393억`, `장중`, `확인 10:17`
    - 피에스케이 `319660` KOSDAQ 22위, `341억`, `장중`, `확인 10:17`
    - RFHIC `218410` KOSDAQ 41위, `162억`, `장중`, `확인 10:17`

## News Observation Text

- Visible empty/news text observed:
  - `뉴스 관찰 없음`
  - `저장된 뉴스 관찰 없음`
  - `저장 뉴스 관찰이 없습니다.`
  - candidate rows show `뉴스 근거: 저장 뉴스 근거 없음`

## API Performance Notes

- `api-perf-summary --json` record count: `871`, endpoint count: `97`.
- Relevant current-day endpoint families:
  - `/api/daily/{date}` for `2026-06-05`: max `23836.118 ms`, avg `db_ms=808.484`, avg `build_ms=2930.211`, cache hits `9/12`.
  - `/api/daily/{date}?intraday_market_top=1`: max `18768.661 ms` before the final makeup click; the later raw log recorded `32482.916 ms`.
  - `/api/candidate-evidence` for `2026-06-05`: p50 `0.651 ms`, max `2654.105 ms`, cache hits `9/12`.
  - `/api/archive?limit=120`: p50 `14.011 ms`, p95 `328.726 ms`, max `2550.958 ms`.
  - `/api/market`: p50 `419.381 ms`, max `454.704 ms`.
- Latest raw intraday route log:
  - path: `/api/daily/2026-06-05?intraday_market_top=1&market_top_limit=100&market_top_page_size=20`
  - status: `200`
  - total_ms: `32482.916`
  - db_ms: `3359.945`
  - build_ms: `32477.657`
  - json_ms: `0.544`
  - cache: `miss`
  - gzip: `true`

## Assessment

- The automations did run, but the important live click measurement was incomplete because the access gate blocked browser interaction.
- With the temporary entry code, the live button is enabled and works.
- The panel displays market status and checked time.
- The primary bottleneck is the intraday market-top route build/fetch path, not JSON serialization.
- The UI handles the wait by showing a loading status quickly, but final result latency can exceed 30 seconds in this run.

## One-Line Review

Automation execution existed, but the live-click requirement was effectively incomplete until access-gated browser verification was rerun; the button works, but intraday fetch latency is still the main N100 watch item.
