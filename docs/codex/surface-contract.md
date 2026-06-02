# Surface Contract

## Purpose

This document fixes the product boundary between the operator control surface and the shared read-only information surface.

The decision is:

- `admin-gui` is the local operator console.
- `web-view` is a separate read-only user page.
- They may share SQLite, repository queries, and summary logic.
- They must not share HTTP control endpoints or raw operator status payloads.

This is a permission and API boundary, not just a visual layout boundary.

## Surface Split

| Surface | Audience | Purpose | Network boundary | HTTP methods | Capability |
| --- | --- | --- | --- | --- | --- |
| `admin-gui` | Operator only | Run diagnostics and local controls | Loopback/local by default | `GET` + guarded `POST` | Scheduler, no-run dates, worker/status, recovery controls |
| `web-view` | Trusted friends or external read-only viewers | Consume refined market/report information | Loopback by default; shared read-only only through reviewed tunnel/access path | `GET` only, except `/auth/login` | Archive, daily summaries, dated categories, ETF/flow references, market mood, intraday history |

## Non-Negotiable Rules

- Do not add a read-only mode to `admin-gui` as the shared user page.
- Do not expose `admin-gui` to friends or external users.
- Do not add Telegram commands that open, bind, or expose `admin-gui` as a remote control surface.
- Do not proxy or reuse `admin-gui` `/api/status` as the `web-view` API.
- Do not hide buttons in the UI while leaving the same control APIs reachable.
- `web-view` must not implement `POST`, `PUT`, `PATCH`, or `DELETE` data routes. The only allowed POST exception is `/auth/login` for the optional entry-code gate.
- `web-view` must be implemented with a separate handler/router and a separate read-only DTO contract.
- Shared DB/repository code is allowed. Shared HTTP control handlers are not allowed.
- Broker or execution API work, including future Toss Securities Open API evaluation, must not be connected to `admin-gui`, Telegram, scheduler, production DB writes, broker secrets, or order routing by default. It belongs in a separate lab/staging lane until docs, permissions, sandbox/test keys, and read-only probes are verified.
- A verified real-time quote/turnover/index lane may later feed `web-view` observation priority and top-2 `우선 확인` ordering. This is observation-candidate recommendation, not trading execution.
- The current public `web-view` trading-wording ban is not a permanent denial of the product's long-term direction. Trading-decision support belongs in a future operator-only decision-support lane after stable real-time data, permissions, failure handling, and execution safety are proven.
- External sharing candidates are limited to Tailscale for owner-only remote operation and Cloudflare Tunnel for a future friend-facing read-only `web-view` URL.
- Direct router port forwarding is not a preferred exposure model for this project.
- Browser-assisted source validation that depends on login state should use the connected Chrome extension session first. The Codex in-app browser is acceptable for local UI checks, but it must not be treated as equivalent to the operator's authenticated Chrome session.

## Operator Admin Surface

`admin-gui` may show and control:

- business-day status and explain-date results
- operator pause/no-run date state
- scheduler task state and classification
- run-now for allowed tasks
- scheduler enable/disable controls
- Telegram command worker heartbeat
- health status and failing checks
- DB freshness and operational logs
- recent deliveries and recent operation events
- pending intraday batches
- local-only safe settings and admin audit logs

`admin-gui` may include guarded write operations because it is an operator console.

`admin-gui` should not become the review workbench for raw judgment layers. News intelligence review rows, candidate linkage evaluation internals, sentiment scores, raw `stock_impact`, operator recommendation-support labels, and other decision-support payloads belong in `operator-review` if they need a private UI. The admin console may link to a future `operator-review` surface or show coarse operational readiness, but it should not host the review body.

`admin-gui` should also avoid read-only daily briefing and market-info duplication. Market mood, recent reports, sector/theme rollups, KRX market reference tables, ETF reference rows, stored news evidence badges, and candidate evidence rows are not admin screen body content. They belong in `web-view` when public-safe or `operator-review` when raw/private.

## Operator Review Surface

`operator-review` is reserved for future private review workflows that need more detail than public `web-view` may show and more judgment context than `admin-gui` should carry.

Allowed future examples:

- raw saved news-intelligence observation runs
- article-level evidence rows
- candidate linkage evaluation internals
- direct/indirect/market-context counts and warnings
- operator recommendation-support labels
- comparison between stored news observations, reports, KRX context, and candidate evidence

This surface is not implemented yet. Before implementation, define its route, access model, read/write behavior, and test contract separately. The first version should prefer read-only stored-data review unless the operator explicitly asks for review actions.

## Shared User Surface

`web-view` should show refined information only:

- recent business-date archive
- daily report overview
- top-tab task split: `메인` for today priority, `관찰` for candidate evidence and report-after-flow, `종목` for selected-stock detail, `시장` for stored market/flow references, and `순환매` for category/theme/ETF rotation context
- intraday overlap checks stay in the `메인` priority flow while the `관찰` tab remains the full candidate-evidence surface; do not duplicate the top-2 priority cards as a separate watch-tab preface
- stock-level daily summary rows
- stock-level report detail
- sector rollup with dated snapshot policy
- theme rollup with dated snapshot policy
- market mood
- intraday batch history
- selected-date KRX market reference cards
- later source-backed flow reference views
- stored-sample investor-flow trend views
- stored ETF trend views
- stored news-observation summary labels, archive counts, candidate badges, and stock-detail news context when they are public-safe and score-free
- future approved read-only intraday reference for top-2 observation candidates

`web-view` should not show raw operational internals unless they are intentionally converted into simple public freshness labels.

Current screen organization keeps stock-level daily summary in the `stock` tab, keeps the full candidate-evidence lane in the `watch` tab, keeps broad KOSPI/KOSDAQ/index and investor-flow references in the `market` tab, and keeps ETF/rotation evidence in the `rotation` tab. This is React-ready information architecture, but the current implementation remains the Python-rendered static page until a separate frontend build decision is made.

`GET /v2` is the first preview route for the next `web-view` information architecture. It must keep the same read-only API boundary as `/`, reuse stored-data DTOs, and make the distinction between market flow, observation candidates, evidence layers, stock detail, and rotation/ETF context easier to see. It is a review surface for the shared page, not an `admin-gui` or `operator-review` route.

Allowed examples:

- `최근 갱신: 26.05.07 16:30 KST`
- `데이터 기준일: 26.05.07`
- `업종/테마는 최신 저장 분류 기준`

Disallowed examples:

- DB file path
- raw scheduler task names
- scheduler access errors
- Telegram worker heartbeat internals
- Telegram token/chat id
- `.env` values
- shutdown status/control
- operator no-run date controls
- pause/resume controls
- Telegram-triggered admin page open links

## Web-View Data Semantics

The user page is an archive/review surface, not a delivery mirror.

Detailed data-quality rules are maintained in [data-quality-checklist.md](/c:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-quality-checklist.md).
Source ownership and Korean display naming are fixed in [data-source-policy.md](/c:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-source-policy.md).

| Item | Contract |
| --- | --- |
| Date basis | Korean market `business_date`, not raw `collected_at`. |
| Timezone | Display and filtering use KST. |
| Archive scope | Stored daily summaries and derived report data. |
| Telegram filter mismatch | Telegram can filter output for notification usefulness; `web-view` may show fuller archive data if clearly labeled. |
| Mention count | Number of newly collected reports for the stock on that business date. |
| Broker repeats | Same broker multiple reports may display as `broker_name(count)`, but report-level detail must remain available. |
| Target price range | Minimum and maximum parsed numeric target prices for the business date. |
| Missing target/opinion | Missing values are excluded from aggregate range/vote, then shown as `목표가 -` or `의견 없음` in detail/search surfaces. |
| Dominant opinion | Valid opinions are voted; `N/A` is used only when no valid opinion exists. |
| Source ownership | Naver owns research reports; KRX owns market reference data such as price, volume, turnover, ETF, index, and investor flow. |
| Category naming | User-facing Korean labels are `업종`, `테마`, and generic `카테고리`; avoid leaking `sector/theme` or calling current category data KRX-owned. |
| Sector/theme limitation | If a dated category snapshot exists on or before the selected date, use the nearest snapshot per category key; otherwise label it as the latest stored category classification. Never mix future snapshots into older dates. Disabled categories stay hidden. |
| Category dedupe | Visible sector/theme dedupe is presentation-level and must not be treated as canonical taxonomy history. |
| Missing category mapping | Internal placeholders such as `N/A` may remain in raw DTO fields, but user-facing labels must render as `업종 미확인` or `테마 미확인`. |
| Selected-date KRX | Missing selected-date KRX data must remain missing; do not silently fall back to the latest snapshot. |

The first `web-view` should prefer clarity over trading interpretation. It can say what was observed and recommend what to check first, but should avoid unsupported scoring.

Future real-time or broker-origin data must be labeled and reviewed as a separate source lane before it affects the shared page. Until then, `web-view` copy should treat KRX/report/flow values as stored references and avoid implying live quote freshness.

When that future lane is approved, `read-only` still means no DB write, no Telegram/scheduler automation, no admin control path, no broker secret exposure, and no order routing. It does not mean the intraday reference is forbidden from changing `우선 확인`, `관찰 우선순위`, or main-card emphasis.

If a later phase evaluates trading decisions, keep it out of the public `web-view` contract. It should be an operator-only decision-support or execution-lab surface with its own permission, audit, source freshness, failure, and order-safety contract.

Operator-only news intelligence may produce sentiment scores, event impact labels, and recommendation-draft summaries for the operator lane. The v1 contract is [news-intelligence-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/contracts/news-intelligence-contract.md): the default preview writes no DB rows, and only the explicit `--save-observation` operator path may write to operator-only observation tables. It still connects to no scheduler, Telegram, broker, or public route by default.

Once observations are saved, `web-view` should be allowed to show a thin public-safe projection instead of keeping the work invisible. That projection must be stored-data-only and may show labels such as `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, direct/caution/market-context counts, KRX reference status, and one to three article titles. It must not expose internal sentiment scores, numeric impact, operator recommendation-support labels, trading calls, broker/execution language, or any live fetch/write action.

## Web-View API Contract

The current endpoint contract is GET-only:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /health` | Process health only | No secrets, no scheduler data. |
| `GET /api/archive?limit=20` | Recent business-date archive | Dates, report count, stock count, delivery summary if safe, and stored news-observation count. |
| `GET /api/daily/{date}` | Daily overview | Date-bound daily summary, public contract metadata, market mood, category rollups, selected-date `krx_context`, recent `krx_recent_flow` with explicit stored reference date, structured `market_briefing` blocks for index/turnover/flow/notable stocks/check points, read-only investor-flow context when stored samples exist, and stored-data-only `news_observation_summary`. |
| `GET /api/daily/{date}/stocks/{stock_code}` | Stock detail | Report details, same-date KRX reference, read-only stored-sample investor-flow rows when available, and stored-data-only `news_observation_detail`. |
| `GET /api/intraday?date={date}` | Intraday history | Batch time, new report count, safe alert outcome summary. |
| `GET /api/flow-trend?date={date}` | Investor-flow trend | Stored KRX Data Marketplace samples only; no live fetch, no public numeric scoring, no trading recommendation. |
| `GET /api/etf-trend?date={date}` | ETF trend | Stored KRX ETF snapshots only; no live fetch, no public numeric scoring, no trading recommendation. |
| `GET /api/category?date={date}&type=sector|theme&name=...` | Category detail | Same-date category stock list with KRX stock references when available. |
| `GET /api/category-trend?type=sector|theme&name=...` | Category trend | Recent category report/stock counts, descriptive only; dated snapshot per date when available, latest stored category classification otherwise. |
| `GET /api/market` | Latest KRX market reference | Kept for compatibility; the main user page should prefer selected-date `krx_context` from daily DTO. |

Daily and category DTOs may include public display labels such as `sector_display_name`, `theme_display_name`, or `category_display_name`. They must not include scheduler, worker heartbeat, DB path, `.env`, Telegram secrets, safe settings, or admin audit data.

Daily DTOs may include a public contract block with read-only/source-scope/trading-recommendation/control-exposure flags. This block is user-facing safety copy, not an operator health model. Observation-candidate recommendation is allowed when it is expressed as `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, or `왜 눈에 띄는지`. The web-view may show graph-like sector/theme breadth bars, a top-2 `우선 확인` observation shortlist, and `순환매 참고 종목`/`순환매 참고 ETF` reference slots when they are stored-data-only and accompanied by missing-information labels where evidence is absent.

Daily and candidate DTOs may include public-safe news observation fields when they are derived only from stored `news_intelligence_runs` / `report_linked_news_evidence` rows. The current visible fields are `news_observation_summary`, candidate-row `news_observation_badge`, stock-detail `news_observation_detail`, and archive `news_observation_count`. Empty state should be explicit rather than invisible: `저장된 뉴스 관찰 없음`, `저장 뉴스 근거 없음`, `뉴스 근거 부족`, or `추가 확인 필요` is preferable to hiding the block until the model is perfect.

Investor-flow DTOs must clearly mark that they are stored sample/read-only data, do not trigger live KRX fetches from the user page, and do not provide public numeric scoring or trading recommendations.

If a future `intraday_reference` DTO is enabled, it must expose source/freshness state clearly. A disabled placeholder may use `affects_ordering=false`; an approved source may use ordering influence only for observation priority, never for public score, buy/sell wording, broker execution, or order routing.

## Future Access Gate Checklist

Before any Cloudflare Tunnel URL is shared, confirm this checklist:

| Check | Required State |
| --- | --- |
| Target port | Only the `web-view` port, for example `127.0.0.1:8780`. |
| Local bind | Keep `web-view` bound to `127.0.0.1` unless a deliberate private-network exception uses `--allow-non-loopback`. |
| HTTP methods | `GET` only for user data routes; write methods return `405`. `/auth/login` is the only allowed POST exception. |
| Admin separation | `admin-gui`, `/api/status`, scheduler/operator/settings POST routes, shutdown controls, `.env`, DB files, and Telegram secrets are not exposed. |
| Access gate | Prefer Cloudflare Access or another simple allow-list before wider sharing. |
| Access cookie | App entry-code cookies are `HttpOnly`, `SameSite=Lax`, and become `Secure` when the request arrives through an HTTPS proxy such as Cloudflare Tunnel. |
| Public copy | The page may recommend observation targets. Stored values must be labeled as stored references; approved real-time values must be labeled with source/freshness and may affect observation priority only, not trading recommendations. |
| Rollback | Tunnel can be disabled without changing local scheduler or DB state. |

## Forbidden In Web-View

- scheduler run-now
- scheduler enable/disable
- operator pause/resume
- no-run date add/remove
- shutdown action or shutdown enablement
- raw Task Scheduler command metadata
- raw operation event internals
- raw health failing checks intended only for the operator
- safe settings, `app_settings`, or operator configuration values
- admin audit logs or setting-change history
- `operator-settings` CLI details
- `.env` editing or display
- Telegram token/chat id
- arbitrary shell command execution
- DB writes or side effects
- cache-refresh actions that mutate DB state

## Deferred Telegram Ideas

The operator considered commands such as `/관리자페이지 열기`.
This is intentionally deferred.

Reason:

- `admin-gui` is a control-capable local console.
- Opening or exposing it through Telegram would blur the admin/user boundary.
- Remote admin access should be handled through direct private access to the mini PC, not through a chat command.

Implemented safer Telegram candidates are read-only:

- `/상태`: concise operator health summary
- `/오늘돌아?`: explain whether scheduled jobs should run today
- `/스케줄상태`: scheduler/worker health summary without control actions
- `/웹뷰주소`: return the read-only `web-view` URL only after the exposure path is intentionally configured

These candidates must not start servers, expose `admin-gui`, or perform write/control actions.

## Implementation Sequence

| Step | Work | Output |
| --- | --- | --- |
| 1 | Keep this surface contract current | Future sessions know the boundary before coding. |
| 2 | Define read-only query/DTO layer | Done: user API does not depend on `build_operator_status_snapshot()`. |
| 3 | Add separate `web-view` CLI/server entrypoint | Done: `python -m stock_monitor web-view --host 127.0.0.1 --port 8780`; use `scripts/run_web_view.ps1` for the safer Cloudflare-prep operator wrapper and `scripts/restart_web_view.ps1` for the hourly mini-PC refresh task. |
| 4 | Add GET-only API tests | First pass done: archive/daily/market APIs reject writes and do not expose admin endpoints. |
| 5 | Build first user page | Daily pass done with archive, daily stocks, sector/theme, market mood, intraday history, selected-date KRX context, and mobile-card rendering for key tables. |
| 6 | Validate consistency | Same `business_date` shows consistent aggregation between Telegram/admin/web where intentionally overlapping. |
| 7 | Review exposure model | Only after local validation, decide private tunnel/VPN/shared access path. |

## External Access Candidates

| Candidate | Allowed target | Intended audience | Notes |
| --- | --- | --- | --- |
| Tailscale | Local services on the mini PC, primarily owner access | Owner devices first | Good for private remote operation. Friend sharing is possible but creates onboarding overhead. |
| Cloudflare Tunnel | `web-view` only, for example `http://127.0.0.1:8780` | Small trusted friend group | Best fit for a convenient friend-facing HTTPS URL after local validation and the local entry-code gate is enabled. |
| Docker | None for the current Windows N100 path | Not a sharing mechanism | Deferred. Direct Python + Windows Task Scheduler is the operating target unless the host moves to Linux/VPS or multi-service deployment. |

`admin-gui` must not be exposed through either candidate as a public/friend-facing surface.

## Local Entry-Code Gate

Both `admin-gui` and `web-view` support the same optional first-layer entry-code gate.

- Gate status is controlled by the presence of the local hash file at `STOCK_MONITOR_ACCESS_CODE_PATH`, default `data/access_code.json`.
- Create or replace the gate with `python -m stock_monitor access-code set`.
- Check status with `python -m stock_monitor access-code status`.
- Disable it only intentionally with `python -m stock_monitor access-code clear --confirm`.
- The file stores PBKDF2-SHA256 `salt + hash`, not the plaintext code.
- When the hash file exists, HTML pages, JSON APIs, and image assets require the entry-code session cookie first. `/health` remains available for local liveness checks.
- `admin-gui` and `web-view` use separate session cookie names, so logging into the friend-facing page does not authenticate the operator console.
- Entry-code session cookies use `HttpOnly` and `SameSite=Lax`. When the request carries `X-Forwarded-Proto: https`, `Forwarded: proto=https`, or `X-Forwarded-Ssl: on`, the cookie also uses `Secure`.
- This is a lightweight app-level gate, not a replacement for Cloudflare Access, OS account security, or keeping `admin-gui` private.

Cloudflare Tunnel rule:

- Tunnel only the local `web-view` HTTP port.
- Keep the local `web-view` server on loopback (`127.0.0.1`) for tunnel sharing; non-loopback binding requires `--allow-non-loopback` and should not be the default.
- Do not tunnel `admin-gui`, `.env`, DB files, Telegram token/chat id, scheduler APIs, shutdown controls, or arbitrary shell/control endpoints.
- Do not use router port forwarding as the default exposure model.
- Cloudflare handles the public URL, TLS, and optional Access gate; this project must still keep the exposed app read-only and free of control surfaces.
- Before provider setup, run `python -m stock_monitor external-web-view-sharing-plan --json` to print the focused read-only Cloudflare/Tailscale sequence. This command does not configure Cloudflare, DNS, scheduler tasks, DB state, or secrets.
- Start the local sharing target through `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress 127.0.0.1 -Port 8780`; the wrapper prints the intended tunnel target and repeats that `admin-gui` must not be exposed. On the mini PC, keep `StockMonitor-WebViewHourlyRestart` enabled so `scripts/restart_web_view.ps1` refreshes this loopback target hourly.
- After a provider URL exists, prefer the wrapper `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL -PythonExe .\.venv\Scripts\python.exe` before sharing it. It validates that the URL is a non-loopback HTTPS provider origin, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless explicitly skipped, runs `external-web-view-smoke --record-success`, and then reruns `next-phase-readiness`.
- The underlying final URL check is `python -m stock_monitor external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json`. Pass the provider origin only, such as `https://view.example.com`, with no path, query, or fragment. This check does not accept or print the access-code; it verifies `/health`, the external URL scheme, user data-route method blocking, the root page is not `admin-gui`, `/api/status` is not publicly exposed, admin scheduler/operator/settings POST routes are unavailable or access-gated, and the archive/daily/candidate/stock-detail/flow-trend/ETF-trend/category-trend JSON does not expose known operator/admin keys. Its JSON output includes `public_json_routes_checked`; the same route contract is listed in `next-phase-readiness.external_web_view_sharing.provider_smoke_checks`. Without `--record-success` the command stays read-only; with it, a non-secret provider-smoke operation event is written only when all checks pass against a non-loopback HTTPS provider origin so `next-phase-readiness` can close the external sharing gate. A Cloudflare Access HTML/login page is treated as access-gated when it contains recognizable Cloudflare Access markers, so a provider that blocks unauthenticated reads can still pass without exposing user data.
- A response is not treated as access-gated if the body also looks like `admin-gui`; admin markers win over Cloudflare Access wording.

## Validation Gates

- `web-view` has no write/data-mutation routes. `/auth/login` is only an access gate endpoint.
- `web-view` does not import or expose admin POST dispatcher logic.
- `web-view` responses exclude scheduler controls, shutdown controls, secrets, `.env`, DB path, and raw operational internals.
- `web-view` responses and HTML exclude safe settings, admin audit logs, operator profiles, and `/api/settings` routes.
- `admin-gui` remains loopback/local control by default.
- `web-view` archive uses `business_date` and KST semantics.
- Telegram notification filters and web archive scope are documented so differences are intentional.
- Historical sector/theme responses use dated snapshots when available and label the latest stored category classification only when no prior snapshot exists.
- Selected-date daily pages must not silently fall back to the latest KRX snapshot when that date has no KRX data.
- Missing category placeholders such as internal `N/A` must use public labels in the user page.
- Stored news-observation projection must remain read-only and public-safe: no live news fetch, no `--save-observation` trigger, no internal sentiment score, no numeric impact, no raw `stock_impact`, no operator recommendation-support field, and no buy/sell/trading-call wording.
- Public-safe wording QA is context-based. It may allow explanatory copy such as `추천 판단 아님`, `점수 없이 저장 근거만 확인`, `등급 없음`, `리포트 의견 참고`, and `뉴스 근거`; it must block explicit trading-call or scored labels such as `매수 추천`, `매수 기회`, `전략 제안`, `점수: 92`, and `등급: A`.
- `web-view-browser-smoke` must pass before treating mobile/browser review as locally clean: desktop/tablet/large-mobile/mobile render without major horizontal overflow, the exact top-tab order is `메인`/`관찰`/`종목`/`시장`/`순환매`, each non-main tab opens its representative panel, stock search exists, write methods stay blocked, and `/api/status` remains unavailable. The `/v2` preview route should be browser-checked separately while it is experimental.
- `external-web-view-smoke --record-success` must pass against the final Cloudflare/Tailscale URL before the URL is shared. If the access-code or Cloudflare Access gate blocks unauthenticated user data routes with `401`/`403` or a recognizable Cloudflare Access HTML/login page, that is acceptable; `/api/status` and admin scheduler/operator/settings POST routes must never return a public admin/control payload.
