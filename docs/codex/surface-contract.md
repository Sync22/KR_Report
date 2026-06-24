# Surface Contract

## Purpose

This document fixes the product boundary between the operator control surface, the shared read-only information surface, and the future private review surface.

The decision is:

- `admin-gui` is the local operator operations console.
- `web-view` is a separate read-only user page.
- `operator-review` is a future private review surface for raw judgment and evidence inspection.
- They may share SQLite, repository queries, and summary logic.
- They must not share HTTP control endpoints or raw operator status payloads.

This is a permission and API boundary, not just a visual layout boundary.

## Surface Split

| Surface | Audience | Purpose | Network boundary | HTTP methods | Capability |
| --- | --- | --- | --- | --- | --- |
| `admin-gui` | Operator only | Run operations status, local controls, recovery, settings, and audit | Loopback/local by default | `GET` + guarded `POST` | Scheduler, no-run dates, worker/status, recovery controls, safe settings, admin audit |
| `web-view` | Trusted friends or external read-only viewers | Consume public-safe stored-data projections | Loopback by default; shared read-only only through reviewed tunnel/access path | `GET` only, except `/auth/login` | Archive, daily summaries, dated categories, ETF/flow references, market mood, intraday history, public-safe candidate/news summaries |
| `operator-review` | Operator only | Future private review of raw judgment and linked evidence | Not implemented; define separately before use | TBD, preferably read-only first | Raw news observation review, candidate linkage review, internal labels, evidence comparison |

## Non-Negotiable Rules

- Do not add a read-only mode to `admin-gui` as the shared user page.
- Do not expose `admin-gui` to friends or external users.
- Do not add Telegram commands that open, bind, or expose `admin-gui` as a remote control surface.
- Do not proxy or reuse `admin-gui` `/api/status` as the `web-view` API.
- Do not hide buttons in the UI while leaving the same control APIs reachable.
- `web-view` user data routes remain GET-first, but a narrow access-gated operator action may use `POST /api/news-observations/collect` to turn the selected-date top priority news lane from `수집 전` into saved observation rows. The existing `/auth/login` POST remains the entry-code exception. No other public write/control POST route is allowed without a separate contract.
- `web-view` must be implemented with a separate handler/router and a separate read-only DTO contract.
- Shared DB/repository code is allowed. Shared HTTP control handlers are not allowed.
- Broker or execution API work, including Toss Securities OpenAPI beyond the approved top-2 current-price projection, must not be connected to `admin-gui`, production DB writes, broker secrets, or order routing by default. It belongs in a separate lab/staging lane until docs, permissions, sandbox/test keys, and read-only probes are verified.
- Toss OpenAPI is approved for server-derived latest-date top-2 `우선 확인` symbols in two bounded read-only consumers: the `web-view` current-price reference and the scheduled `09:15`/`12:00`/`15:15` market-briefing Telegram slots. It must not accept arbitrary symbols, expose account/order data, persist current quotes, affect ordering, or send a standalone trading instruction.
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

The shared page must preserve the user journey across those tabs. A selected observation candidate may carry its public-safe observation state, report reason, direct/supporting news summary, intraday-reference label, Toss current-price label, and Toss 20:00 baseline into stock detail. Detail may link onward to stored `시장` and `순환매` context. These links remain navigation over existing read-only data; they do not create a live fetch, DB write, Telegram action, scheduler action, order route, or public trading instruction.

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

Detailed data-quality rules are maintained in [data-quality-checklist.md](data-quality-checklist.md).
Source ownership and Korean display naming are fixed in [data-source-policy.md](data-source-policy.md).

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

The first `web-view` should prefer clarity over trading interpretation. It can say what was observed, identify what is still missing, and recommend what to check first, but should avoid unsupported scoring.

Broker-origin data is currently allowed only for the bounded Toss top-2 current-price reference. It must be labeled as `Toss 현재가`; KRX/report/flow values remain stored references, and the live quote must not imply a trading decision.

When that future lane is approved, `read-only` still means no DB write, no Telegram/scheduler automation, no admin control path, no broker secret exposure, and no order routing. It does not mean the intraday reference is forbidden from changing `우선 확인`, `관찰 우선순위`, or main-card emphasis.

If a later phase evaluates trading decisions, keep it out of the public `web-view` contract. It should be an operator-only decision-support or execution-lab surface with its own permission, audit, source freshness, failure, and order-safety contract.

Operator-only news intelligence may produce sentiment scores, event impact labels, and recommendation-draft summaries for the operator lane. The v1 contract is [news-intelligence-contract.md](contracts/news-intelligence-contract.md): the default preview writes no DB rows, and only explicit `--save-observation` operator paths may write to operator-only observation tables. The batch `news-intelligence-briefing-collect` path also requires `--confirm-save` before writing. Those command surfaces still connect to no scheduler, Telegram, broker, admin-gui, or public route by default.

The production exception is narrow and explicit: enabled `scheduled-market-briefing-slot` runs at `09:15`, `12:00`, and `15:15` may, after their existing business-date, delivery-dedupe, phone-review, and slot-window guards pass, reuse the collector for the server-derived top two candidates of that date. They save only the two observation/evidence records needed by the briefing and then emit a compact Telegram projection for the same two candidates. The two codes are pinned for that run after collection starts, so a newly collected direct-news result cannot reorder the message and replace one collected candidate with an uncollected one. Naver candidate quote reads and Toss current-price reads remain read-only and carry their checked time; they are not persisted. A collection failure records a non-secret operation event and leaves the briefing send path available with the saved-data projection. This is not a broad news crawler, a generic news scheduler, a raw-payload Telegram feed, or a trading-alert path.

`news-flow-preview` is also operator-only, but it is source-flow oriented rather than stock/candidate oriented. It accepts only operator-provided source URLs through a fixture contract, emits text/JSON preview plus a Telegram draft, may run an explicitly approved `news-flow-source-probe` for supported Naver source URLs, and may feed a preview-only `market-briefing` source-flow section. It must remain disconnected from DB writes, Telegram real sends, scheduler tasks, `admin-gui`, and public `web-view` until a separate contract explicitly changes that boundary.

Once observations are saved, `market-briefing` and `web-view` should be allowed to show a thin public-safe projection instead of keeping the work invisible. That projection may show labels such as `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, direct/caution/market-context counts, KRX reference status, and one to three article titles. The web-view may also expose one access-gated operator action, `POST /api/news-observations/collect`, which runs the existing news briefing collection for the selected date/top candidates and saves only `news_intelligence_runs` / `report_linked_news_evidence` rows. It must not expose internal sentiment scores, numeric impact, operator recommendation-support labels, trading calls, broker/execution language, raw warnings, scheduler/Telegram/admin behavior, or broker/order data.

## Web-View API Contract

The current endpoint contract is GET-first, with one explicit operator-triggered collection exception:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /health` | Process health only | No secrets, no scheduler data. |
| `GET /api/archive?limit=20` | Recent business-date archive | Dates, report count, stock count, delivery summary if safe, and stored news-observation count. |
| `GET /api/daily/{date}` | Daily overview | Date-bound daily summary, public contract metadata, market mood, category rollups, selected-date `krx_context`, recent `krx_recent_flow` with explicit stored reference date, structured `market_briefing` blocks for index/turnover/flow/notable stocks/check points plus stored-data-only `market_briefing.news_observation_summary`, read-only investor-flow context when stored samples exist, and top-level stored-data-only `news_observation_summary`. |
| `GET /api/daily/{date}/stocks/{stock_code}` | Stock detail | Report details, same-date KRX reference, read-only stored-sample investor-flow rows when available, and stored-data-only `news_observation_detail`. |
| `GET /api/intraday?date={date}` | Intraday history | Batch time, new report count, safe alert outcome summary. |
| `GET /api/flow-trend?date={date}` | Investor-flow trend | Stored KRX Data Marketplace samples only; no live fetch, no public numeric scoring, no trading recommendation. |
| `GET /api/etf-trend?date={date}` | ETF trend | Stored KRX ETF snapshots only; no live fetch, no public numeric scoring, no trading recommendation. |
| `GET /api/toss-priority-quotes?date={date}` | Toss top-2 current-price reference | Latest stored business date only; server-derived top-2 candidate symbols only; no arbitrary symbol query, account/order data, DB write, scheduler, Telegram, scoring, or trading recommendation. |
| `POST /api/news-observations/collect` | Access-gated news evidence collection | Selected-date/top-priority operator action only. It may live-fetch Naver news through the existing news-intelligence briefing collector and write saved observation/evidence rows, then returns only a public-safe summary. It must not send Telegram, register scheduler tasks, expose raw operator payloads, expose sentiment/impact scores, or accept broker/order actions. |
| `GET /api/category?date={date}&type=sector|theme&name=...` | Category detail | Same-date category stock list with KRX stock references when available. |
| `GET /api/category-trend?type=sector|theme&name=...` | Category trend | Recent category report/stock counts, descriptive only; dated snapshot per date when available, latest stored category classification otherwise. |
| `GET /api/market` | Latest KRX market reference | Kept for compatibility; the main user page should prefer selected-date `krx_context` from daily DTO. |

Daily and category DTOs may include public display labels such as `sector_display_name`, `theme_display_name`, or `category_display_name`. They must not include scheduler, worker heartbeat, DB path, `.env`, Telegram secrets, safe settings, or admin audit data.

Daily DTOs may include a public contract block with read-only/source-scope/trading-recommendation/control-exposure flags. This block is user-facing safety copy, not an operator health model. Observation-candidate recommendation is allowed when it is expressed as `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, or a top-card `판단 상태` label. The web-view may show graph-like sector/theme breadth bars, a top-2 `우선 확인` observation shortlist, and `순환매 참고 종목`/`순환매 참고 ETF` reference slots when they are stored-data-only and accompanied by missing-information labels where evidence is absent.

Daily and candidate DTOs may include public-safe news observation fields when they are derived from stored `news_intelligence_runs` / `report_linked_news_evidence` rows. The visible fields are `news_observation_summary`, candidate-row `news_observation_badge`, stock-detail `news_observation_detail`, archive `news_observation_count`, and a source-labelled `value_profile.evidence_direction`. The projection is candidate-linked, deduplicates same-date repeated evidence by its stored evidence key, and keeps a later collection time separate from its evidence. The main top-two projection, a completed collection response, and the matching market-briefing candidate rows use the same server-derived codes; broader candidates remain in `관찰`. Empty state should be actionable rather than invisible. The canonical direction, freshness, and evidence-precedence rules are [the Evidence Direction Rule](data-quality-checklist.md#evidence-direction-rule); this surface contract only defines the public DTO boundary.

Investor-flow DTOs must clearly mark that they are stored sample/read-only data, do not trigger live KRX fetches from the user page, and do not provide public numeric scoring or trading recommendations.

If a future `intraday_reference` DTO is enabled, it must expose source/freshness state clearly. An approved source may confirm or weaken observation priority only when the row identifies its source, market status, trade/checked time, and whether the candidate actually overlaps the measured market activity. Intraday price or turnover must not be presented as a standalone conclusion when the report/news evidence is missing or conflicting.

## Future Access Gate Checklist

Before any Cloudflare Tunnel URL is shared, confirm this checklist:

| Check | Required State |
| --- | --- |
| Target port | Only the `web-view` port, for example `<loopback web-view target>`. |
| Local bind | Keep `web-view` bound to `127.0.0.1` unless a deliberate private-network exception uses `--allow-non-loopback`. |
| HTTP methods | User data reads stay `GET`. Write/control methods return `405` except `/auth/login` and the access-gated `POST /api/news-observations/collect` operator action. |
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
| 3 | Add separate `web-view` CLI/server entrypoint | Done: `python -m stock_monitor web-view --host <loopback-host> --port <web-view-port>`; use `scripts/run_web_view.ps1` for the safer Cloudflare-prep operator wrapper and `scripts/restart_web_view.ps1` for the hourly mini-PC refresh task. |
| 4 | Add GET-only API tests | First pass done: archive/daily/market APIs reject writes and do not expose admin endpoints. |
| 5 | Build first user page | Daily pass done with archive, daily stocks, sector/theme, market mood, intraday history, selected-date KRX context, and mobile-card rendering for key tables. |
| 6 | Validate consistency | Same `business_date` shows consistent aggregation between Telegram/admin/web where intentionally overlapping. |
| 7 | Review exposure model | Only after local validation, decide private tunnel/VPN/shared access path. |

## External Access Candidates

| Candidate | Allowed target | Intended audience | Notes |
| --- | --- | --- | --- |
| Tailscale | Local services on the mini PC, primarily owner access | Owner devices first | Good for private remote operation. Friend sharing is possible but creates onboarding overhead. |
| Cloudflare Tunnel | `web-view` only, for example `<loopback web-view URL>` | Small trusted friend group | Best fit for a convenient friend-facing HTTPS URL after local validation and the local entry-code gate is enabled. |
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
- Start the local sharing target through `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_web_view.ps1 -PythonExe .\.venv\Scripts\python.exe -HostAddress <loopback-host> -Port <web-view-port>`; the wrapper prints the intended tunnel target and repeats that `admin-gui` must not be exposed. On the mini PC, keep `StockMonitor-WebViewHourlyRestart` enabled so `scripts/restart_web_view.ps1` refreshes this loopback target hourly.
- After a provider URL exists, prefer the wrapper `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL -PythonExe .\.venv\Scripts\python.exe` before sharing it. It validates that the URL is a non-loopback HTTPS provider origin, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless explicitly skipped, runs `external-web-view-smoke --record-success`, and then reruns `next-phase-readiness`.
- The underlying final URL check is `python -m stock_monitor external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json`. Pass the provider origin only, such as `https://view.example.com`, with no path, query, or fragment. This check does not accept or print the access-code; it verifies `/health`, the external URL scheme, user data-route method blocking, the root page is not `admin-gui`, `/api/status` is not publicly exposed, admin scheduler/operator/settings POST routes are unavailable or access-gated, and the archive/daily/candidate/stock-detail/flow-trend/ETF-trend/category-trend JSON does not expose known operator/admin keys. Its JSON output includes `public_json_routes_checked`; the same route contract is listed in `next-phase-readiness.external_web_view_sharing.provider_smoke_checks`. Without `--record-success` the command stays read-only; with it, a non-secret provider-smoke operation event is written only when all checks pass against a non-loopback HTTPS provider origin so `next-phase-readiness` can close the external sharing gate. A Cloudflare Access HTML/login page is treated as access-gated when it contains recognizable Cloudflare Access markers, so a provider that blocks unauthenticated reads can still pass without exposing user data.
- A response is not treated as access-gated if the body also looks like `admin-gui`; admin markers win over Cloudflare Access wording.

## Validation Gates

- `web-view` has no admin/control write routes. `/auth/login` is only an access gate endpoint; `POST /api/news-observations/collect` is the only approved data-write exception and is limited to saved news observation/evidence rows for the selected date/top candidates.
- `web-view` does not import or expose admin POST dispatcher logic.
- `web-view` responses exclude scheduler controls, shutdown controls, secrets, `.env`, DB path, and raw operational internals.
- `web-view` responses and HTML exclude safe settings, admin audit logs, operator profiles, and `/api/settings` routes.
- `web-view` Toss current-price responses expose only `prices` for server-derived top-2 symbols and must not expose tokens, credentials, account ids, order ids, holdings, buying power, sellable quantity, commissions, or arbitrary public symbol lookups.
- `admin-gui` remains loopback/local control by default.
- `web-view` archive uses `business_date` and KST semantics.
- Telegram notification filters and web archive scope are documented so differences are intentional.
- Historical sector/theme responses use dated snapshots when available and label the latest stored category classification only when no prior snapshot exists.
- Selected-date daily pages must not silently fall back to the latest KRX snapshot when that date has no KRX data.
- Missing category placeholders such as internal `N/A` must use public labels in the user page.
- Stored news-observation projection must remain public-safe: the page may trigger the approved access-gated news observation collect action, but visible DTO/DOM output must still hide internal sentiment scores, numeric impact values, raw `stock_impact`, operator recommendation-support fields, and raw warnings. It may show the derived direct-evidence direction only with its count, reason, source scope, and freshness state.
- Public wording QA is evidence-based, not a mechanical forbidden-word filter. It must reject unsupported certainty, hidden scoring, fabricated action instructions, and any broker/order action. It may show attributed report opinion, a source-labelled directional assessment, and terms such as `상승 근거 우세`, `하방 위험 우세`, or `직접 근거 상충` when those labels are reproducible from stored direct evidence and do not conceal conflicting evidence.
- `web-view-browser-smoke` must pass before treating mobile/browser review as locally clean: desktop/tablet/large-mobile/mobile render without major horizontal overflow, the exact top-tab order is `메인`/`관찰`/`종목`/`시장`/`순환매`, each non-main tab opens its representative panel, stock search exists, write methods stay blocked, and `/api/status` remains unavailable. The `/v2` preview route should be browser-checked separately while it is experimental.
- `external-web-view-smoke --record-success` must pass against the final Cloudflare/Tailscale URL before the URL is shared. If the access-code or Cloudflare Access gate blocks unauthenticated user data routes with `401`/`403` or a recognizable Cloudflare Access HTML/login page, that is acceptable; `/api/status` and admin scheduler/operator/settings POST routes must never return a public admin/control payload.
