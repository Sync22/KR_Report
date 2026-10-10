# Surface Guide

Public-safe web-view, operator admin surface, rotation overlay, and realtime-first information architecture.

## Included sections
- Surface Contract
- Admin GUI Plan
- Rotation Overlay Plan
- Realtime-First Pruning Plan
- Web-View Main Layout First Pass

<!-- Merged from: docs/codex/surface-guide.md -->
## Surface Contract

## Purpose

This document fixes the product boundary between the operator control surface, the shared read-only information surface, and the future private review surface.

The decision is:

- `admin-gui` is the local operator operations console.
- `web-view` is a separate read-only user page.
- `operator-review` is a standalone private review surface for selected-date candidate evidence.
- They may share SQLite, repository queries, and summary logic.
- They must not share HTTP control endpoints or raw operator status payloads.

This is a permission and API boundary, not just a visual layout boundary.

## Surface Split

| Surface | Audience | Purpose | Network boundary | HTTP methods | Capability |
| --- | --- | --- | --- | --- | --- |
| `admin-gui` | Operator only | Run operations status, local controls, recovery, settings, and audit | Loopback/local by default | `GET` + guarded `POST` | Scheduler, no-run dates, worker/status, recovery controls, safe settings, admin audit |
| `web-view` | Trusted friends or external read-only viewers | Consume public-safe stored-data projections | Loopback by default; shared read-only only through reviewed tunnel/access path | `GET` only, except `/auth/login` | Archive, daily summaries, dated categories, ETF/flow references, market mood, on-demand Top2 chart/indicator context, public-safe candidate/news summaries |
| `operator-review` | Operator only | Selected-date Main candidate and stored-evidence review | Loopback only at `127.0.0.1:8767` | `GET` only | Main cohort review, source/freshness/missing labels, local chart handoff |

## Non-Negotiable Rules

- Do not add a read-only mode to `admin-gui` as the shared user page.
- Do not expose `admin-gui` to friends or external users.
- Do not add Telegram commands that open, bind, or expose `admin-gui` as a remote control surface.
- Do not proxy or reuse `admin-gui` `/api/status` as the `web-view` API.
- Do not hide buttons in the UI while leaving the same control APIs reachable.
- `web-view` data and control routes are GET-only. `/auth/login` is the entry-code exception; rendering or interacting with the page must not fetch news and write observation rows.
- `web-view` must be implemented with a separate handler/router and a separate read-only DTO contract.
- Shared DB/repository code is allowed. Shared HTTP control handlers are not allowed.
- Broker or execution API work, including all Toss Securities OpenAPI capabilities outside the approved bounded projections, must not be connected to `admin-gui`, unapproved production DB writes, broker secrets, or order routing. Account, asset, order, broad polling, and execution capabilities remain separate lab/hold lanes.
- Toss OpenAPI public reads are limited to server-derived Top2 current-price/same-day flow, fixed latest-date Top20 market context, and the on-demand Top2 adjusted daily history used by the chart/indicator panel. The web-view remains GET-only and accepts no arbitrary symbols. The chart/indicator request does not persist data, run on a scheduler, or affect candidate ordering. Its sole condition-status projection follows [Data governance](data-governance.md#main-top2-technical-indicator-projection). Telegram does not gain a standalone trading alert or instruction.
- Stored web-view market, ETF, and flow sections use the bounded Toss `20:00` close snapshot. Existing KRX rows remain historical drilldown data and are not a current market fallback.
- User resolution (2026-10-09, clarified 2026-10-10): the blanket public restriction on chart-derived trading conditions is replaced by the narrow selected-date Main Top2 projection below. A price threshold alone does not confirm a condition; all user-defined indicator/volume confirmations must align. This transparent rule is not a numeric score or an empirically validated error-reduction claim, and it does not authorize generic recommendations, execution, or other strategy behavior.
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

`operator-review` is a separate local review panel for the selected-date Main cohort. Start it with `python -m stock_monitor operator-review`; it binds to `127.0.0.1:8767` and has no non-loopback host option. The panel and its `/api/operator-review?date=YYYY-MM-DD` endpoint use their own GET-only handler and DTO.

Phase 1 contract:

- Candidate membership and order come from the same selected-date candidate-evidence builder as Main; this panel adds no ranking logic.
- The date picker defaults to the latest stored report date. The operator can select a historical date.
- Candidate evidence shows its source, reference date, same-date/missing freshness, why-notable labels, evidence layers, and gaps. Toss same-day investor flow is labeled provisional.
- News is summarized with collection state and evidence counts. Raw news bodies, headlines, HTML, secrets, scores, and recommendation fields are not exposed.
- The response excludes post-date reaction/progress rows. Missing selected-date values stay missing instead of falling back to another source or date.
- SQLite opens through a read-only URI with query-only mode. The command does not initialize or migrate the database, fetch live sources, write rows, contact Telegram, or change scheduler state.
- Each candidate may link to the operator-configured local Stock-Newbby page at `{LOCAL_NEWBBY_BASE_URL}/chart-first.html?symbol=<six-digit-code>&asOf=<business-date>`.

The panel remains separate from both control and public surfaces: its route is absent from `admin-gui` HTML and public `web-view` HTML/routes. Its chart links remain operator-clicked. The public Main has the separate, user-triggered indicator exception below.

## Main Top2 Technical Indicator Block

The Main priority card provides an explicit chart/indicator check button, a 50/100/200-trading-day range selector (200 by default), and a supplementary-series selector (RSI 14 initially). Loading the page or changing the selected date does not fetch candles.

The public GET route /api/priority-indicators?date=YYYY-MM-DD derives at most the selected-date Main Top2 on the server; callers cannot choose symbols. In the Main browser, only the button triggers this GET; direct GET clients may also request the route. The chart displays candles, SMA 20/60/120/200, volume, and one selected supplementary series.

Each result labels the requested date, actual bar date, Toss source/fetch time, and candle-finality/pagination state. Missing and provider-error states remain visible. This read-only projection does not change candidate order, write Stock Monitor data, or invoke the scheduler, Telegram, or a Stock-Newbby server.

The exact source/classification fallback, pagination, calculation set, schemaVersion 1 allowlist, condition formulas and states, provenance, and safety contract live in [Data governance](data-governance.md#main-top2-technical-indicator-projection). Local credential and provider setup notes live in [Toss OpenAPI Lab](toss-openapi-lab.md#promoted-main-top2-technical-indicators-2026-10-08).

## Shared User Surface

`web-view` should show refined information only:

- recent business-date archive
- daily report overview
- top-level task split: `메인` for today's priority, `관찰` for candidate evidence, and `종목` for selected-stock detail; market and category/ETF references are nested panels, not top-level tabs
- intraday overlap checks stay in the `메인` priority flow while the `관찰` tab remains the full candidate-evidence surface; do not duplicate the top-2 priority cards as a separate watch-tab preface
- stock-level daily summary rows
- stock-level report detail
- sector rollup with dated snapshot policy
- theme rollup with dated snapshot policy
- market mood
- intraday batch history
- selected-date historical KRX reference cards and stored Toss market/ETF/flow panels
- later source-backed flow reference views
- stored-sample investor-flow trend views
- stored ETF trend views
- stored news-observation summary labels, archive counts, candidate badges, and stock-detail news context when they are public-safe and score-free
- bounded read-only Toss Top2 current-price/same-day provisional investor-volume reference and selected-date daily candles; the market-context GET also returns Top20/overlap, but the current panel renders indices and aggregate flow only

`web-view` should not show raw operational internals unless they are intentionally converted into simple public freshness labels.

Current screen organization keeps exactly `메인`, `관찰`, and `종목` as top-level tabs. Dated market references and ETF/category reference details are collapsed under Main; selected category details open under Stock. The current implementation remains Python-rendered HTML/JavaScript; no React frontend build is active.

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

## Current Main And Watch Hierarchy

- Main first shows the selected-date stored priority Top2, concise observation reasons, current reference labels, and expandable evidence; the reading summary, source freshness, and saved-news context follow.
- Toss current quote/flow and the adjusted-candle chart/indicator projection are labeled reference views initiated through their Main controls; they do not change stored candidate membership or order.
- Historical market and industry/ETF references stay collapsed below Main until opened.
- Watch remains a compact candidate selector; it does not repeat the stock-detail evidence grids or issue live source requests.
- Stock detail owns the complete report, target-history/progress, saved-news, historical KRX, and stock-flow context.

## Canonical Evidence Composition Purpose

The three top-level tabs and their nested reference panels are one evidence journey, not independent dashboards:

1. Stored Naver reports create the dated candidate pool and preserve its existing order.
2. Saved news observations explain whether same-day evidence strengthens, cautions, conflicts with, or does not directly connect to each candidate.
3. Toss current price and same-day provisional investor volume provide current reference for the fixed Top2. The user-triggered Naver intraday turnover overlap is a separate current comparison and must not silently reorder the candidates.
4. Toss 20:00 owns current stored market/ETF/flow references. KRX market and stock-level `[12009]` rows are historical references. A stale or missing reference is a freshness state, not negative evidence.
5. `메인` answers what to inspect first, `관찰` compares and selects from the pool, and `종목` owns detailed evidence. Market and category/ETF context remain nested panels.

The web-view is stored-data first: core reports, summaries, news observations, and market/ETF/flow context use stored rows. Its bounded live-reference GETs are listed below. News collection belongs to the existing scheduler/CLI collection path; the page must not create observations as a hidden side effect. This section is the canonical product-purpose rule for evidence composition; other documents should link here instead of redefining tab roles.

The user page is an archive/review surface, not a delivery mirror.

Detailed data-quality rules are maintained in [data-governance.md](data-governance.md).
Source ownership and Korean display naming are fixed in [data-governance.md](data-governance.md).

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
| Source ownership | Naver owns research reports; Toss owns new/current stored market references; KRX rows are historical analysis/recovery data. |
| Category naming | User-facing Korean labels are `업종`, `테마`, and generic `카테고리`; avoid leaking `sector/theme` or calling current category data KRX-owned. |
| Sector/theme limitation | If a dated category snapshot exists on or before the selected date, use the nearest snapshot per category key; otherwise label it as the latest stored category classification. Never mix future snapshots into older dates. Disabled categories stay hidden. |
| Category dedupe | Visible sector/theme dedupe is presentation-level and must not be treated as canonical taxonomy history. |
| Missing category mapping | Internal placeholders such as `N/A` may remain in raw DTO fields, but user-facing labels must render as `업종 미확인` or `테마 미확인`. |
| Selected-date KRX | Missing selected-date KRX data must remain missing; do not silently fall back to the latest snapshot. |

The first `web-view` should prefer clarity over trading interpretation. It can say what was observed, identify what is still missing, and recommend what to check first, but should avoid unsupported scoring.

Broker-origin data is currently allowed through bounded read-only GETs for Top2 current-price/same-day provisional investor-volume context, latest-date Top20 market context, and the user-triggered Top2 chart/indicator projection. Top2 quotes refresh when the server-derived cohort changes and may use the bounded Naver quote fallback if Toss is unavailable or incomplete. Market context and chart/indicator history require their respective user actions. The market-context response includes Top20/overlap, but the current panel renders indices and provisional aggregate flow only. Each projection must show source and checked time; none writes data, changes Top2 membership/order, or implies a generic trading recommendation. The separately approved Main threshold projection is specified in [Data governance](data-governance.md#main-top2-technical-indicator-projection); this guide owns its controls and presentation.

For this enabled reference lane, `read-only` means no DB write, Telegram/scheduler automation, admin control path, broker-secret exposure, or order routing. It supplies context for the fixed Top2 and does not change candidate membership or order. The narrow 2026-10-09 Main Top2 threshold projection specified in [Data governance](data-governance.md#main-top2-technical-indicator-projection) is the sole public chart-derived condition exception; any broader trading-decision support remains a separate operator-only lane.

If a later phase adds trading-decision support beyond the exact user-defined Main Top2 threshold projection, keep that broader capability out of the public `web-view` contract. It should be an operator-only decision-support or execution-lab surface with its own permission, audit, source freshness, failure, and order-safety contract.

Operator-only news intelligence may produce sentiment scores, event impact labels, and recommendation-draft summaries for the operator lane. The v1 contract is [news-intelligence.md](news-intelligence.md): the default preview writes no DB rows, and only explicit `--save-observation` operator paths may write to operator-only observation tables. The batch `news-intelligence-briefing-collect` path also requires `--confirm-save` before writing. Those command surfaces still connect to no scheduler, Telegram, broker, admin-gui, or public route by default.

The production exception is narrow and explicit: the approved hourly Telegram implementation must retain the existing 30-minute collection/dedupe trigger and deliver only at `08:30`, then `09:30` through `15:30` KST after existing business-day and delivery-window guards pass. `08:30` is report-first; later deliveries may add independent saved news, Top20 overlap, and the server-derived Top2 Toss current-price/same-day provisional investor-volume context when available. The report remains the candidate seed and order. Missing Toss data is neutral, never a reason to suppress a report briefing, lower a candidate, create a candidate, or make a score or trading instruction. Current-price reads remain read-only and are not persisted. This is not a broad news crawler, a generic news scheduler, a raw-payload Telegram feed, or a trading-alert path.

`news-flow-preview` is also operator-only, but it is source-flow oriented rather than stock/candidate oriented. It accepts only operator-provided source URLs through a fixture contract, emits text/JSON preview plus a Telegram draft, may run an explicitly approved `news-flow-source-probe` for supported Naver source URLs, and may feed a preview-only `market-briefing` source-flow section. It must remain disconnected from DB writes, Telegram real sends, scheduler tasks, `admin-gui`, and public `web-view` until a separate contract explicitly changes that boundary.

Once observations are saved by the existing scheduler/CLI path, `market-briefing` and `web-view` may show a thin public-safe projection instead of keeping the work invisible. That projection may show labels such as `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, direct/caution/market-context counts, KRX reference status, and one to three article titles. It must not expose internal sentiment scores, numeric impact, operator recommendation-support labels, trading calls, broker/execution language, raw warnings, scheduler/Telegram/admin behavior, or broker/order data.

## Web-View API Contract

Core page DTOs read stored data. The bounded live-reference GETs below may make upstream read-only requests; they do not persist the response. The current page/API contract is:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /health` | Process health only | No secrets, no scheduler data. |
| `GET /api/archive?limit=20` | Recent business-date archive | Dates, report count, stock count, delivery summary if safe, and stored news-observation count. |
| `GET /api/stocks/search?date={date}&q={query}&limit=8` | Selected-date stock search | Stored metadata/listing cache first; Naver autocomplete is the fallback. Search does not call Toss per query. |
| `GET /api/candidate-evidence?date={date}&limit={limit}` | Stored report/news evidence for the server-derived candidate pool | No live fetch, public score, candidate creation, or user-selected ordering. |
| `GET /api/observation-summary?date={date}` | Stored observation summary | Read-only projection of saved reports/category rows and server-derived priority codes. |
| `GET /api/observation/backtest?date={date}&limit={limit}&mention_threshold={threshold}` | Historical post-report reaction review | Stored review data only; no current quote fetch or trading instruction. |
| `GET /api/daily/{date}` | Daily overview | Date-bound summary, public contract metadata, market mood, category rollups, Toss 20:00 stored market context, and selected-date historical `krx_context`/`krx_recent_flow` with explicit source/reference dates. News fields use stored observations only. |
| `GET /api/daily/{date}/stocks/{stock_code}` | Stock detail | Report details, same-date historical KRX reference, read-only stored flow rows when available, and stored-data-only `news_observation_detail`. |
| `GET /api/daily/{date}?intraday_market_top=1` | Naver market-top overlap | User-triggered, bounded to the current business date; no storage or candidate reorder. |
| `GET /api/intraday?date={date}` | Intraday history | Batch time, new report count, safe alert outcome summary. |
| `GET /api/flow-trend?date={date}` | Investor-flow trend | Stored Toss close market-flow snapshots; no live fetch, public numeric scoring, or trading recommendation. |
| `GET /api/etf-trend?date={date}` | ETF trend | Stored Toss ETF snapshots only; no live fetch, no public numeric scoring, no trading recommendation. |
| `GET /api/priority-current-quotes?date={date}` | Naver current-price fallback for Top2 | Used only when the Toss Top2 quote read is unavailable or incomplete; server-derived Top2 only, no storage or reordering. |
| `GET /api/toss-priority-quotes?date={date}` | Toss Top2 current-price and same-day provisional investor-volume reference | Latest business date and server-derived Top2 only. Requested when the Top2 cohort changes; also has a manual refresh button. No arbitrary symbols, persistence, ordering change, account/order data, or trading recommendation. |
| `GET /api/priority-indicators?date={date}` | Main Top2 chart, technical references, and separate derived price-condition projection | Fetched only after the user presses `차트 · 지표 확인`; returns up to 800 adjusted daily bars plus aligned factual series, while the page displays a selectable 50/100/200-trading-day window (default 200) and initially selects RSI 14 as the supplementary indicator. The separate condition uses the approved exact labels/rules below and is outside schema-v1. No storage or ranking change. |
| `GET /api/toss-priority-daily-candles?date={date}&days={30,90,180}` | Bounded raw daily-candle projection | Retained as a GET-only server-derived Top2 route; the Main chart UI uses the combined indicator route above. No storage or ranking change. |
| `GET /api/toss-market-context?date={date}` | Toss latest-date market-context payload | Fetched only after the user presses `지수 · 수급 확인`; response includes fixed Top20/overlap and bounded KOSPI/KOSDAQ context. Current renderer shows indices and provisional aggregate flow only, not Top20/ETF rows. No storage or ranking change. |
| `GET /api/category?date={date}&type=sector|theme&name=...` | Category detail | Same-date category stock list; any KRX reference is historical and source/date labeled. |
| `GET /api/category-trend?type=sector|theme&name=...` | Category trend | Recent category report/stock counts, descriptive only; dated snapshot per date when available, latest stored category classification otherwise. |
| `GET /api/rotation-overlay?date={date}&limit=5` | Collapsed category/ETF reference panel | Dated report/category overlay and stored ETF mapping; descriptive only, no candidate reorder or persistence. |
| `GET /api/market` | Latest stored Toss market snapshot | Reads Toss 20:00 indices, KOSPI/KOSDAQ turnover Top5, ETF Top5, and capture state; KRX is not a current fallback. |

Daily and category DTOs may include public display labels such as `sector_display_name`, `theme_display_name`, or `category_display_name`. They must not include scheduler, worker heartbeat, DB path, `.env`, Telegram secrets, safe settings, or admin audit data.

Daily DTOs may include a public contract block with read-only/source-scope/trading-recommendation/control-exposure flags. This block is user-facing safety copy, not an operator health model. Observation-candidate recommendation is allowed when it is expressed as `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, or a top-card `판단 상태` label. The web-view may show graph-like sector/theme breadth bars, a top-2 `우선 확인` observation shortlist, and `순환매 참고 종목`/`순환매 참고 ETF` reference slots when they are stored-data-only and accompanied by missing-information labels where evidence is absent.

Daily and candidate DTOs may include public-safe news observation fields when they are derived from stored `news_intelligence_runs` / `report_linked_news_evidence` rows. The visible fields are `news_observation_summary`, candidate-row `news_observation_badge`, stock-detail `news_observation_detail`, archive `news_observation_count`, and a source-labelled `value_profile.evidence_direction`. The projection is candidate-linked, deduplicates same-date repeated evidence by its stored evidence key, and keeps a later collection time separate from its evidence. The main top-two projection, a completed collection response, and the matching market-briefing candidate rows use the same server-derived codes; broader candidates remain in `관찰`. Empty state should be actionable rather than invisible. The canonical direction, freshness, and evidence-precedence rules are [the Evidence Direction Rule](data-governance.md#evidence-direction-rule); this surface contract only defines the public DTO boundary.

Investor-flow DTOs must clearly mark that they are stored sample/read-only data, do not trigger live KRX fetches from the user page, and do not provide public numeric scoring or trading recommendations.

If a future `intraday_reference` DTO is enabled, it must expose source/freshness state clearly. An approved source may confirm or weaken observation priority only when the row identifies its source, market status, trade/checked time, and whether the candidate actually overlaps the measured market activity. Intraday price or turnover must not be presented as a standalone conclusion when the report/news evidence is missing or conflicting.

## Future Access Gate Checklist

Before any Cloudflare Tunnel URL is shared, confirm this checklist:

| Check | Required State |
| --- | --- |
| Target port | Only the `web-view` port, for example `<loopback web-view target>`. |
| Local bind | Keep `web-view` bound to `127.0.0.1` unless a deliberate private-network exception uses `--allow-non-loopback`. |
| HTTP methods | User data reads stay `GET`. Write/control methods return `405`; `/auth/login` remains the access-gate exception. |
| Admin separation | `admin-gui`, `/api/status`, scheduler/operator/settings POST routes, shutdown controls, `.env`, DB files, and Telegram secrets are not exposed. |
| Access gate | Prefer Cloudflare Access or another simple allow-list before wider sharing. |
| Access cookie | App entry-code cookies are `HttpOnly`, `SameSite=Lax`, and become `Secure` when the request arrives through an HTTPS proxy such as Cloudflare Tunnel. |
| Public copy | The page may recommend observation targets. Stored values must be labeled as stored references; approved real-time values must be labeled with source/freshness. The exact Main Top2 threshold status is a separate user-defined condition projection; it does not affect observation priority or authorize generic trading recommendations. |
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

- `web-view` has no data/control write routes. `/auth/login` is only an access-gate endpoint.
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
- Stored news-observation projection must remain public-safe: visible DTO/DOM output hides internal sentiment scores, numeric impact values, raw `stock_impact`, operator recommendation-support fields, and raw warnings. It may show the derived direct-evidence direction only with its count, reason, source scope, and freshness state. Collection remains outside the web-view.
- Public wording QA is evidence-based, not a mechanical forbidden-word filter. It must reject unsupported certainty, hidden scoring, fabricated action instructions, and any broker/order action. It may show attributed report opinion, a source-labelled directional assessment, and terms such as `상승 근거 우세`, `하방 위험 우세`, or `직접 근거 상충` when those labels are reproducible from stored direct evidence and do not conceal conflicting evidence.
- `web-view-browser-smoke` must pass before treating mobile/browser review as locally clean: desktop/tablet/large-mobile/mobile render without major horizontal overflow, the exact top-tab order is `메인`/`관찰`/`종목`, Main's market and industry/ETF disclosures open, stock search works, write methods stay blocked, and `/api/status` remains unavailable. The `/v2` preview route should be browser-checked separately while it is experimental.
- `external-web-view-smoke --record-success` must pass against the final Cloudflare/Tailscale URL before the URL is shared. If the access-code or Cloudflare Access gate blocks unauthenticated user data routes with `401`/`403` or a recognizable Cloudflare Access HTML/login page, that is acceptable; `/api/status` and admin scheduler/operator/settings POST routes must never return a public admin/control payload.


<!-- Merged from: docs/codex/surface-guide.md -->
## Admin GUI Plan

## Purpose

This is the consolidated local operator GUI plan.

Use this instead of starting from older admin review/progress notes. The older files remain as history, but this file is the active admin GUI direction.

## Current State

| Area | Status |
| --- | --- |
| Local `admin-gui` server | Implemented |
| Loopback-first boundary | Implemented |
| Scheduler cards/status | Implemented |
| Run-now for allowed tasks | Implemented |
| Scheduler enable/disable | Implemented |
| Shutdown run-now block | Implemented |
| No-run calendar | Implemented |
| Right-click reason editing | Implemented |
| No-run date server validation | Implemented |
| Safe settings panel | Implemented |
| Audit log display | Implemented |
| Operation profile editing | Implemented |
| TelegramCommands restart recovery | Implemented |
| Read-only recovery guidance | Implemented |
| DB backup/verify reminders | Implemented |
| Recent event readable summaries | Implemented |
| Operations-only screen trim | Implemented |

## Boundary

`admin-gui` is the operator operations surface.

It should stay focused on operations menu/status/control: scheduler state, pause/no-run controls, safe settings, recovery guidance, DB freshness, operation events, and admin audit.

It must not become the friend-facing shared page. Shared read-only information belongs in `web-view` and must stay GET-only.

It also must not become the main judgment review workbench. News intelligence, candidate linkage, raw recommendation-support labels, sentiment/impact internals, and candidate evidence review details belong in the future `operator-review` surface when a private review UI is needed. `admin-gui` may show coarse operational readiness for those lanes, but not the review body.

Market mood, recent report/category rollups, KRX market reference tables, ETF reference rows, and daily briefing content are intentionally not admin screen content. They belong in the public-safe stored-data `web-view` projection, CLI review output, or a future private `operator-review` surface depending on detail level.

## Next Admin Work

| Priority | Work | Done condition |
| --- | --- | --- |
| P0 | Keep status labels aligned with `operator-status` | GUI and CLI use the same health meaning. |
| P0 | Keep safe settings audited | Every setting write has validation, confirmation, and reason. |
| Done / P1-watch | Refine recovery controls | `operator-status` and `admin-gui` now show read-only safest-next-step recovery guidance; the only broad GUI recovery control remains TelegramCommands restart until live evidence justifies more controls. |
| Done | Improve event readability | Recent events keep raw detail in operator JSON but `admin-gui`/text status prefer readable summaries for KRX, flow, scheduler, notify, and admin failures. |
| Done | Add migration/backup reminders | `operator-status` JSON/text and `admin-gui` show latest DB backup presence plus db-verify/db-backup guidance before risky work. |

No-run date server validation rejects market holidays, env-level no-run dates, and past dates. DB-managed no-run dates should represent future or same-day manual exclusions only; historical explanation belongs in operation events/docs, not a scheduler override.

## Excluded From Admin GUI

- Raw `.env` editing.
- Telegram token or chat id editing.
- Raw shell command editing.
- One-click shutdown.
- Friend-facing read-only mode.
- Public tunnel exposure.
- News intelligence raw observation rows.
- Candidate evidence review workbench.
- Raw sentiment score, stock impact, recommendation-support, or candidate linkage internals.
- Market mood, recent report, sector/theme, KRX market, or ETF reference tables.

## Verification

```powershell
python -m stock_monitor operator-status --json --health-exit
python -m stock_monitor db-verify
python -m pytest tests\test_admin_gui.py tests\test_operator_status.py -q
```


<!-- Merged from: docs/codex/surface-guide.md -->
## Rotation Overlay Plan

## Purpose

This document defines the sector-first rotation overlay based on `example/Cycle.jpg`.

The overlay is a descriptive review view. It can support observation-candidate recommendation, but not prediction, public numeric score, investment grade, or trading recommendation.

The first alias-mapping boundary for the image text is fixed in [candidate-evidence.md](candidate-evidence.md).

## Current State

The original memo for rotation/flow tracking can be marked `[O]` for V1 foundation because KRX flow source validation, storage, and read-only display paths now exist.

The first visual overlay is implemented in the user `web-view` as a collapsed read-only section named `순환매 참고`.

Current implementation:

- serves the original image through `GET /assets/cycle.jpg`
- serves descriptive overlay data through `GET /api/rotation-overlay?date=YYYY-MM-DD`
- draws SVG circles on top of the JPG without modifying the original file
- highlights only sector categories that have a manual coordinate entry in `data/rotation_overlay_coordinates.json`
- uses `data/rotation_image_aliases.json` as the first image-text alias layer, mapping a human image label such as `우주항공` to the current sector display name and coordinate key
- validates active image aliases through `web-view-value-qa`; mapped coordinate labels must exist in `data/rotation_overlay_coordinates.json` or QA fails
- includes read-only `candidate_stocks` preview rows per highlighted sector, derived from same-date report summaries and exact-date KRX stock snapshots
- includes read-only `candidate_etfs` only when an operator-managed mapping exists in `data/rotation_etf_candidates.json`
- validates active `candidate_etfs` mappings through `web-view-value-qa`; mapped ETF codes must exist in the latest stored ETF snapshot or QA fails
- validates active `candidate_etfs` categories through `web-view-value-qa`; each active mapping must resolve to an overlay coordinate directly or through an active image alias
- lazy-loads the image and overlay only when the collapsed section is opened
- labels evidence as report/category rollup observations or observation-candidate recommendation, not trading recommendation
- treats themes as supporting evidence only; the overlay marker itself should not mix sector and theme labels until the taxonomy is stronger
- keeps the first image-text alias draft in `data/rotation_image_aliases.json`

## Implementation Shape

| Phase | Work | Notes |
| --- | --- | --- |
| 1 | Show `example/Cycle.jpg` with an SVG overlay layer | Done in `web-view`; collapsed by default. |
| 2 | Maintain a manual coordinate map | Done as `data/rotation_overlay_coordinates.json`; move to DB only if admin calibration is needed. |
| 3 | Highlight active sectors | First report-count based sector highlight is implemented through the alias layer. Same-date stock candidates are shown as separated observation candidates, not trading recommendations. Turnover or investor-flow observations must remain separate evidence labels. |
| 4 | Add admin calibration | Let operator adjust coordinates later if the fixed image needs tuning. |

## First Data Contract

The first version should accept a prepared list like:

| Field | Meaning |
| --- | --- |
| `category_type` | `sector` for the overlay marker. Theme labels are supporting evidence only. |
| `display_name` | User-facing category label. |
| `x`, `y` | Coordinate on the base image. |
| `radius` | Overlay circle size. |
| `evidence_label` | Short text such as `리포트 4건`, `거래대금 상위`, `외국인 순매수`. |
| `evidence_source` | `report`, `krx_turnover`, `krx_flow`, or mixed. |
| `candidate_stocks` | Read-only stock preview rows with report count and exact-date KRX price/turnover when available. |
| `candidate_etfs` | ETF preview rows with exact-date stored Toss ETF turnover/change evidence when an active operator-managed mapping exists. |

## Exclusions

- No trading recommendation.
- No public numeric score or investment grade.
- No auto-generated buy/sell signal.
- No unsupported mapping from report count to investor flow.

## Selection Readiness

Future `ETF 1개 + 종목 1개` selection must stay separate from the current overlay until these prerequisites are met:

| Prerequisite | Required State |
| --- | --- |
| Image text mapping | Cycle image labels have a manual alias table mapped to user-facing 업종 names. |
| Sector coordinates | The overlay coordinate map covers the target 업종 labels without mixing unrelated themes. |
| ETF candidates | A target 업종 may expose ETF candidates only when an active mapping and an exact-date stored Toss ETF row both exist. |
| ETF mapping reachability | Each active ETF mapping category has a direct overlay coordinate or an active alias that points to an existing coordinate. |
| Stock candidates | Each target 업종 has candidate stocks from report summaries, KRX stock master, and category snapshots. |
| Evidence separation | Report count, target-price range, price/turnover, investor flow, and ETF trend are stored/displayed as separate evidence. |
| Display boundary | The user page may call these rows `오늘의 관찰 후보`, `후보`, or `참고`, but not `매수 추천`, `매도 추천`, public numeric score, or investment grade. |

First implementation should be a read-only preview table:

| Field | Meaning |
| --- | --- |
| `rotation_label` | Label from the cycle image or its alias. |
| `category_display_name` | Matched 업종 label. |
| `candidate_etfs` | ETF candidates with stored KRX turnover/change evidence. |
| `candidate_stocks` | Stock candidates with report/flow/turnover evidence. |
| `evidence_summary` | Short separated evidence text, not a score. |

## Done Criteria For First Implementation

- [O] The image renders with SVG circles without modifying the original JPG.
- [O] The overlay can show at least one manually mapped sector category.
- [O] Missing coordinates simply skip overlay for that sector category.
- [O] The user page labels it as `순환매 참고`, not `순환매 판단`.
- [O] The API uses the draft image alias layer instead of treating coordinate labels as the source of truth.
- [O] Active image aliases are covered by `web-view-value-qa` so stale or mistyped coordinate labels do not silently remove an overlay marker.
- [O] Highlighted sectors can show read-only stock preview rows with separated report/KRX evidence.
- [O] Highlighted sectors can show read-only ETF preview rows only through an operator-managed mapping file.
- [O] Active ETF mappings are covered by `web-view-value-qa` so stale or mistyped ETF codes do not silently disappear from the user page.
- [O] Active ETF mapping categories are covered by `web-view-value-qa` so an ETF candidate cannot be registered for a category that the overlay cannot display.

## Next Improvement

- Review `data/rotation_image_aliases.json` against the actual Cycle image text before using aliases for ETF/stock candidate previews.
- Activate `data/rotation_etf_candidates.json` entries only after confirming sector-to-ETF semantics and exact-date availability in the stored Toss ETF lane.
- Add an operator/admin calibration screen later if the fixed image alignment needs manual tuning.
- Expand evidence labels only after category source-date coverage and KRX flow history are stronger.


<!-- Merged from: docs/codex/surface-guide.md -->
## Realtime-First Pruning Plan

## Purpose

This plan recenters Stock Monitor around evidence that helps answer "what should I look at now?" without adding broad new source lanes or trading advice.

The change is information architecture and operating judgment first:

- Put current or intraday evidence first when it exists.
- Keep stored same-day report/news evidence close to the top candidate.
- Move previous-day KRX daily rows, investor flow, ETF, reaction windows, and backtest-style review below the first-read path.
- Keep public `web-view` and Telegram free of generic buy/sell calls, numeric scores, investment grades, entry/exit price or target-return advice, conviction labels, broker execution, and order routing. The sole wording exception is the exact separate Main Top2 status `진입 조건 충족` / `청산 조건 충족` / `가격 기준 도달 · 보조지표 확인 필요` / `두 가격 조건 미충족` / `판정 불가`; it must not be generalized into recommendation copy.

## Current Finding

The existing implementation already has the right separation primitives:

| Axis | Current behavior | Pruning implication |
| --- | --- | --- |
| `web-view` daily API | `build_web_view_daily_snapshot` includes Top2 evidence, market briefing, source freshness, stored Toss context, and historical KRX references. | Keep the first read stored-data based; keep historical KRX below current Toss/source-freshness labels. |
| Candidate evidence | `build_web_view_candidate_evidence_snapshot` ranks stored report, news, KRX, `[12009]`, Toss 20:00 baseline, target progress, and support/gap labels without public scores. | Keep as the primary candidate engine, but expose only the rank-driving current/stored-now reason in the first 10 seconds. |
| Backtest/reaction | `/api/observation/backtest` loads stored post-report reaction windows in the `관찰` surface. | Keep it as review context, separate from the current market-reference panels. |
| Market/KRX/flow | Main keeps a collapsed market-reference panel; stored current market/ETF/flow comes from Toss 20:00, while KRX rows are historical. | Keep stale/missing labels explicit; never substitute KRX for a missing current Toss value. |
| Toss/current quote | `/api/toss-priority-quotes` is bounded to server-derived Top2 and requested when that cohort changes; the response is read-only. | Display it as current context only; it never changes Top2 membership/order. |
| Naver intraday reference | `/api/priority-current-quotes` is the Top2 fallback when Toss is unavailable/incomplete; daily `intraday_market_top=1` is a separate button-triggered check. | Label source/time. Treat non-overlap as scope, not a negative price or signal. |
| Telegram briefing | `market-briefing` builds candidate/news/source freshness around top-2 and can optionally include live candidate quotes. | Reorder copy so top candidates and current evidence appear before stored reference sections. |

## Toss Top20 Market-Attention Panel

### Current Market Source Order

Main keeps the market panel collapsed. The `/api/market` DTO contains the stored Toss 20:00 indices, market Top5, ETF Top5, and capture state; `/api/flow-trend` contains stored Toss close market-flow snapshots. These stored DTOs are separate from the live market-context button.

The `지수 · 수급 확인` button requests bounded latest-date Toss market context. That response includes Top20 rankings and Top2 overlap, while the current renderer shows only KOSPI/KOSDAQ indices and provisional aggregate flow; it does not render the ranking or ETF rows. The Top2 quote route refreshes after its server-derived cohort changes. The `차트 · 지표 확인` button fetches the selected Top2's adjusted daily history and renders the chosen 50/100/200-trading-day window, defaulting to 200 with RSI 14 initially selected. These live references do not persist data or alter Top2 membership/order.

In Telegram market-briefing, Top20 overlap remains supporting context after the fixed report Top2 seed; it cannot create or reorder candidates. Any replay capture is separate from these public GETs.

Selected-date KRX index, turnover, and `[12008]` rows remain collapsed as historical references. KRX `[12010]` net-buy ranks remain internal/history review only and must never fill missing current Toss values.

## Evidence Classification

| Class | Evidence | Use | Surface placement |
| --- | --- | --- | --- |
| Primary evidence | Top-2 candidate identity and visible `why_notable` / `value_profile` reason | First answer to "what to check now" | `web-view` main first block, Telegram `?ㅻ뒛 蹂?寃? |
| Primary evidence | Same-day saved direct/caution news observation for the top-2 | Confirms, conflicts with, or weakens the report hypothesis | Main top-2 cards and Telegram `?꾩옱 洹쇨굅` |
| Primary evidence | Approved top-2 current quote or turnover reference, including Toss current price or bounded Naver quote/market-top overlap | Currentness check, only with source/time/status | Main top-2 card and Telegram `?꾩옱 洹쇨굅` |
| Primary evidence | Source freshness state for reports/news/current quote/KRX/flow | Prevents stale evidence from looking current | Compact inline status near top-2 |
| Fallback evidence | KRX Open API stock/ETF/index daily snapshots | Stored market reference, usually previous business day or selected date | `?쒖옣` tab, collapsed main reference, Telegram `?꾩씪 李멸퀬` |
| Fallback evidence | KRX `[12009]` stock investor flow for selected candidates | Support context when exact and selected-candidate scoped | Candidate detail and Telegram `?꾩씪 李멸퀬` or `?꾩옱 洹쇨굅` only if exact/same candidate |
| Fallback evidence | KRX `[12008]` market flow and `[12010]` net-buy ranks | Market background and rank reference | `?쒖옣` detail, never top reason alone |
| Fallback evidence | ETF daily and rotation reference | Sector/theme support only | `?쒗솚留? tab, collapsed from main |
| Fallback evidence | Toss 20:00 stored baseline | End-of-day baseline, not intraday confirmation | Candidate detail, not top headline |
| Research/review only | Backtest observation, reaction windows, D+1/D+5/D+10/D+20 rows | Learn whether exposed evidence was useful later | `愿李? bottom or separate collapsed `蹂듦린/?곌뎄` block |
| Research/review only | Target-hit/max-progress and historical target reaction | Retrospective context | Stock detail or review block, not main top card |
| Research/review only | X recap lab and news search lane lab results | Lab feasibility and source quality review | Docs/lab branch only |
| Hold | Broad all-stock `[12009]`, `[12008]`, `[12010]` scheduled ingest | Not approved for production automation | Do not connect |
| Hold | Toss account, balance, order history/info, order endpoints | Broker/account/execution surface | Do not connect to public surface, scheduler, Telegram, DB write, or admin-gui |
| Hold | Public score, grade, generic trade call, entry/exit price advice, take-profit/target-return/conviction | Changes product risk profile | Blocked; the exact separately documented Main Top2 all-confirmation condition statuses are the sole exception. |
| Hold | `x-browser-recap-lab` merge into main | Main is the redesign basis; lab branch is behind | Reference ideas only |

## Web-View Repositioning

### Main screen: raise

- `?ㅻ뒛 蹂?寃?: top-2 candidates with one-line observation reason.
- `?꾩옱 洹쇨굅`: for each top-2, show same-day saved direct/caution news and current quote/turnover evidence only when it exists with source and checked time.
- `遺議깊븳 洹쇨굅`: show missing current quote, missing news collection, stale KRX, and missing exact `[12009]` as gaps.
- Source freshness as a one-line compact strip near the top, not a full diagnostic card.

### Main screen: lower

- KRX daily index/turnover cards when they are not same-day/current.
- Broad market/flow summaries that do not name the top-2 candidate.
- ETF and rotation references.
- Target progress and historical reaction wording.

### Send to detail, collapsed, or tabs

- Full candidate list stays in `愿李?.
- Stock-level report rows, target trail, Toss 20:00 baseline, and saved news detail stay in `醫낅ぉ`.
- KRX daily market, `[12008]`, `[12009]`, `[12010]`, and flow trend stay in `?쒖옣`.
- ETF and category/rotation stay in `?쒗솚留?.
- Backtest/reaction windows move to a collapsed `蹂듦린/?곌뎄` section under `愿李? or below stock detail.

### Hold completely

- Public numeric score, investment grade, trade instruction, target return, conviction, broker/order wording.
- Broad live source probing or scheduler wiring.
- Production use of X recap, Naver search lane, or Toss account/order endpoints.

### Mobile 10-second first-read block

The first mobile viewport should answer only this:

1. `?ㅻ뒛 蹂?寃?: top-2 stock names and why they are visible.
2. `?꾩옱 洹쇨굅`: news/current quote/turnover status for those two.
3. `遺議깊븳 洹쇨굅`: one short gap line, for example `?꾩옱媛 誘명솗??쨌 ?댁뒪 ?섏쭛 ??쨌 KRX ?꾩씪 湲곗?`.
4. `?꾩씪 李멸퀬`: one compact link or collapsed chip to KRX/flow detail.

Draft copy shape:

```text
?ㅻ뒛 蹂?寃?
1. 醫낅ぉA - 由ы룷??吏묒쨷 + 吏곸젒 ?댁뒪 洹쇨굅
   ?꾩옱 洹쇨굅: ?댁뒪 2嫄? Toss ?꾩옱媛 12:03 ?뺤씤
   遺議깊븳 洹쇨굅: [12009] ?섍툒? ?꾩씪 湲곗?
2. 醫낅ぉB - 由ы룷??吏묒쨷, ?댁뒪 洹쇨굅 ?湲?
   ?꾩옱 洹쇨굅: Naver ?μ쨷 嫄곕옒?湲?寃뱀묠 ?놁쓬
   遺議깊븳 洹쇨굅: 吏곸젒 ?댁뒪 ?놁쓬, KRX ?꾩씪 湲곗?
```

## Telegram Briefing Repositioning

Target order:

1. `?ㅻ뒛 蹂?寃?
   - Top-2 names, codes, and one observation reason each.
2. `?꾩옱 洹쇨굅`
   - Same-day saved news, current quote/turnover, checked time, source.
   - If no current evidence exists, say so here rather than silently falling back.
3. `?꾩씪 李멸퀬`
   - KRX daily index/turnover, `[12009]` flow, ETF only when concise and source-labelled.
4. `遺議깊븳 洹쇨굅`
   - Missing current quote, stale/missing KRX, no saved news, no exact flow.
5. `蹂듦린/?곌뎄`
   - Reaction/backtest reminder or link-style note only, normally omitted from short messages.

Compression rule:

- Telegram should not lead with broad market/KRX if a top-2 current evidence row exists.
- If current evidence is absent, the message should say `?꾩옱 洹쇨굅 遺議? before showing `?꾩씪 李멸퀬`.
- Keep one line per candidate where possible. Avoid source diagnostics unless they change what the operator should check next.

Draft shape:

```text
?ㅻ뒛 蹂?寃?
1. 醫낅ぉA 000000 - 由ы룷??吏묒쨷 + 吏곸젒 ?댁뒪 洹쇨굅
2. 醫낅ぉB 111111 - 由ы룷??吏묒쨷, ?댁뒪 ?뺤씤 ?湲?

?꾩옱 洹쇨굅
- 醫낅ぉA: ?댁뒪 2嫄?쨌 Toss ?꾩옱媛 12:03 ?뺤씤
- 醫낅ぉB: ?꾩옱媛 誘명솗??쨌 Naver ?μ쨷 寃뱀묠 ?놁쓬

?꾩씪 李멸퀬
- KRX 吏??嫄곕옒?湲? 2026-MM-DD ???湲곗?
- ?섍툒: Top2 以?1媛쒕쭔 [12009] exact

遺議깊븳 洹쇨굅
- 醫낅ぉB 吏곸젒 ?댁뒪 ?놁쓬
- ETF/?쒗솚留ㅻ뒗 ?곸꽭 李멸퀬

蹂듦린/?곌뎄
- 由ы룷?????먮쫫? ?댁쁺 寃?섑몴?먮쭔 湲곕줉
```

## 10-Business-Day Operating Review Checklist

Use one row per market day before marking the related TODO2 items complete.

Do not fabricate rows. Fill them only from same-day read-only previews and browser review.

| Day | Date | Slot / checked time | Top2 candidates | Current evidence | Previous-day reference usefulness | News evidence state | Telegram readability | Web-view 10-second readability | Keep/lower/delete decision | Next-day check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 2 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 3 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 4 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 5 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 6 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 7 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 8 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 9 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 10 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |

Daily read-only routine:

```powershell
python -m stock_monitor candidate-evidence-readiness --recent-report-dates 1 --stock-limit 20 --json
python -m stock_monitor market-briefing-readiness --recent-report-dates 1 --json
python -m stock_monitor market-briefing --date YYYY-MM-DD --layout realtime-first --json
python -m stock_monitor market-briefing --date YYYY-MM-DD --layout realtime-first
python -m stock_monitor data-source-lane-audit --json
python -m stock_monitor web-view-value-qa --date YYYY-MM-DD --stock-limit 20 --json
```

Routine limits:

- These commands are read-only review inputs.
- Do not use `--send`, scheduler registration, DB migration, or production source expansion for this checklist.
- If a command cannot run on the current PC, record the command, failure reason, and the nearest read-only substitute.

Minimum daily note:

```text
YYYY-MM-DD
- Slot / checked time:
- Top2:
- Current evidence:
  - same-day news: direct / caution / market-context / none / waiting / stale
  - current quote/turnover: present / absent / unavailable, source/time:
  - source freshness gap:
- Previous-day reference:
  - KRX daily/index: helped / distracted / neutral, why:
  - flow: helped / distracted / neutral, why:
  - ETF: helped / distracted / neutral, why:
- Telegram realtime-first preview: pass / revise, note:
- Web-view first 10 seconds: pass / revise, note:
- Tomorrow: keep / lower / hide:
- Next-day check:
```

Judgment rules:

- If current evidence is repeatedly useful, keep or raise it as top-2 primary evidence.
- If previous-day KRX, flow, or ETF repeatedly distracts, lower it further from the main top block.
- If news evidence is repeatedly empty, improve the empty/waiting UX before expanding automated collection.
- If reaction/backtest rarely changes operating judgment, isolate it as research/review only.
- If realtime-first preview is hard to read, shorten wording before adding another data lane.

## TODO Board Reinterpretation

Use each TODO's own observable completion evidence; a single clean command does not prove live-host readiness. The shared 10-business-day review is for deciding whether a changed first-read order or scheduled message is stable in operation. It does not block local correctness fixes, focused DTO/browser QA, or no-send previews.

| Todo ID | Proportionate completion evidence |
| --- | --- |
| `TODO2-TG-LIVE-DRYRUN` | Compare no-send previews for representative stored dates and slots. Any real send still needs separate explicit approval; use the shared review log before calling a changed scheduled message operationally stable. |
| `TODO2-WV-CONTENT-QA` | Review recent dates on desktop and mobile; verify that the first view explains the current candidate, available evidence, and gaps. A browser smoke alone does not establish content usefulness. |
| `TODO2-DATA-FRESHNESS-LIVE` | Compare source/date labels across CLI, web-view, and Telegram preview; KRX remains historical-only and missing current-source values stay explicit. |
| `TODO2-NI-EVAL` | Label sample cases as useful, neutral, misleading, or not evaluable, with a brief source-backed reason. Report the actual sample and limits; no fixed percentage is a universal pass gate. Wrong-stock attribution and false independence remain disqualifying errors for the affected claim. |

| `TODO2-RT-PRUNE` | Make a focused local ordering change when a concrete first-read issue is evidenced. Use the shared review log before claiming the new ordering is stable in operation. |

The shared review log can serve multiple TODO2 items; do not require a separate 10-day sample for each one.

## Smallest Implementation Sequence

1. Confirm the concrete issue with stored examples or a focused fixture.
2. Make the smallest local copy/ordering change that addresses it; do not add a data lane or alter ranking policy without a separate decision.
3. Run focused tests and representative-date DTO/browser QA.
4. Use the shared operating review after a user-facing priority change to decide whether it is stable, not as a prerequisite for starting local work.
5. Keep production DB writes, scheduler changes, real Telegram sends, and external sharing behind their existing approval gates.

Skipped for this plan:

- No DB writes.
- No schema migration.
- No Telegram real send.
- No scheduler registration or change.
- No admin-gui process action.
- No broker/order route.
- No `x-browser-recap-lab` merge.


<!-- Merged from: docs/codex/surface-guide.md -->
## Historical Main Layout Review

The former layout proposal and the point-in-time 2026-09-29 user review are preserved in [History](history.md#main-web-view-layout-and-top2-contract-reconciliation-2026-10-10). The current UI contract is above; the full Main Top2 data and condition contract is in [Data governance](data-governance.md#main-top2-technical-indicator-projection).
