# Operations Observation - 2026-06-02 Intraday Button

## Scope

- Workspace: `<PROJECT_ROOT>`
- Observation time: `2026-06-02T09:45:02+09:00`
- Purpose: Read-only operating check for the local `web-view` intraday trading-value button.
- No code change, scheduler change, Telegram send, migration, backfill, commit, or sync was performed.
- No `.env`, token, access code, or raw provider response was recorded.

## Local State

- Current Codex shell account: `ming\codexsandboxoffline`
- Operational elevated check account: `ming\ming`
- `git status --short`: existing local changes/untracked runtime data remain present; no staging was performed by this observation.
- Local `web-view` health: `200 ok`
- Local `web-view` listener:
  - Address: `<LOCAL_WEB_VIEW_HOSTPORT>`
  - PID: `11272`
  - Owner: `MING\MING`
  - Command: bundled Python running `stock_monitor web-view --host <LOCAL_WEB_VIEW_HOST> --port <LOCAL_WEB_VIEW_PORT> --no-open`

## Web-View Smoke

Command:

```powershell
.\.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json
```

Result summary:

- Exit: `0`
- Business date: `2026-06-02`
- Issues: `0`
- Access mode: `<LOCAL_SMOKE_ACCESS_MODE>`
- API checks:
  - `GET /api/daily/2026-06-02`: `200`
  - `GET /api/daily/{date}?intraday_market_top=1`: `200`
  - `GET /api/candidate-evidence`: `200`
  - `GET /api/daily/{date}/stocks/{stock_code}`: `200`
  - `POST /api/daily/2026-06-02`: `405`
  - `GET /api/status`: `404`

Viewport contract:

- Desktop/tablet/large-mobile/mobile all reported:
  - `intraday_button=True`
  - `intraday_overlap_panel=True`
  - `intraday_overlap_initial_visible=False`
  - `candidate_panel=True`
  - `horizontal_overflow_px=0`

Interpretation:

- GET-only/read-only boundary is intact in smoke: public daily POST rejected with `405`; admin status route hidden with `404`.
- Button exists and overlap panel is initially hidden in all smoke viewports.

## Current Operating Web-View Access Gate

Unauthenticated direct requests to the current running local `web-view` returned:

- `GET <LOCAL_WEB_VIEW_URL>/`: `401 Unauthorized`
- `GET /api/daily/2026-06-02?intraday_market_top=1...`: `401 Unauthorized`

Interpretation:

- The current operating `web-view` is protected by the access gate.
- Secret/access code files were not read.
- A temporary operator-provided access code was used for the authenticated browser observation. The value is intentionally not recorded.

## Intraday Live Fetch Equivalent

Operational account read-only equivalent command:

```powershell
.\.venv\Scripts\python.exe -m stock_monitor market-commentary-practice --date latest --intraday-market-top --market-top-limit 100 --market-top-page-size 20 --market-top-delay-seconds 0 --json
```

Result summary:

- Exit: `0`
- Elapsed: about `2513 ms`
- `live_fetch=True`
- Naver market-top calls: `10`
- Errors: `0`
- Overlap items: `3`
- `market_status` present: `3/3`
- `trade_time` present: `0/3`

Interpretation:

- The provider/socket path worked from the operational account.
- This was not a `401/403`, `WinError 10013`, timeout, or provider-empty case.
- Current returned overlap items include market status but not trade time.

## Button Observation

Pre-click:

- Login form was present and authenticated successfully.
- Login elapsed: about `1098 ms`.
- Button count: `1`
- Button visible: `true`
- Button initially enabled: `false`
- Status text before click: `날짜를 선택하면 우선 확인 종목과 장중 거래대금 교집합을 확인할 수 있습니다.`
- Overlap panel visible before click: `false`
- Overlap panel `hidden` attribute before click: `true`

Post-click:

- Direct browser click against the current access-protected page: observed.
- Click elapsed: about `7855 ms`.
- Status text after click: `Naver 거래대금 상위와 리포트 언급이 겹친 종목: 한미약품, 올릭스, 케이엠더블유 · Naver 장중 참고 · 호출 10회`
- Overlap panel visible after click: `true`
- Overlap panel `hidden` attribute after click: `false`
- Chip count: `3`
- Chip text summary:
  - `한미약품 128940KOSPI 62위 · 995억 · 장중`
  - `올릭스 226950KOSDAQ 12위 · 622억 · 장중`
  - `케이엠더블유 032500KOSDAQ 60위 · 124억 · 장중`
- `market_status`: represented in UI as `장중`; live API had `market_status` for `3/3` items.
- `trade_time`: not represented in UI; live API had `trade_time` for `0/3` items.

## Failure Cause Separation

- Access gate: current operating page/API returned `401` without access code.
- Access gate with temporary operator-provided code: passed.
- Socket restriction: not observed in the operational account; prior sandbox-only `WinError 10013` pattern remains separated from current `MING\MING` web-view process.
- Timeout: not observed.
- Provider empty: not observed.
- JS/render issue: not observed.

## Judgment

- Operating health/smoke/API boundary: normal.
- Intraday Naver market-top live fetch equivalent: normal.
- Current access-protected page direct button click: normal observation.
- Intraday data display status: `market_status` is available; `trade_time` is currently absent in returned items.

## Remaining Read-Only Recheck

- No immediate recheck is required for the button/fetch path.
- If the temporary access code is rotated after this observation, repeat only the authenticated browser click check if needed.
- If trade-time display becomes a hard requirement, inspect the Naver `priceTop` payload mapping separately; current live items did not carry `trade_time`.

## One-Line Review

2026-06-02 장중 기준 운영 web-view의 `장중 거래대금 확인` 버튼은 access 통과 후 정상 클릭/표시됐고, 결과 chip과 장중 상태는 표시되며 `trade_time`은 현재 결과에 없다.
