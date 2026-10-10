# Toss OpenAPI Lab

Read-only Toss OpenAPI boundary, official inventory, and post-key probe procedure.

## Current 20:00 Persistence Contract (2026-08-23)

- The approved 20:00 path persists Toss selected-date market context and the full daily-summary candidate cohort. Public stock context remains bounded to server-derived Top2; the daily-candle view is a separate on-demand, non-persistent projection for those candidates.
- Candidate quote requests are split into batches of at most two symbols. Completion requires a non-null close baseline plus both foreigner and institution flow values for every candidate, and a saved market-context snapshot.
- A rerun may refresh a sparse candidate close row but must not overwrite an existing richer Toss daily snapshot with sparse quote data.
- This persistence exception is read-only market data only. It does not approve account/order APIs, broker execution, public scores, Telegram trading calls, or arbitrary public symbol queries.
- Older pre-key and Top2-only planning language below is historical unless it concerns the bounded live projection; this section defines the current storage contract.

## Current Approved API Additions (2026-09-29)

- `GET /api/v1/stocks/all` is allowlisted for the fixed `KOSPI`, `KOSDAQ`, and `KR_ETC` market queries inside the existing `20:05` Toss close capture. Its listing metadata is saved in `toss_stock_universe_cache` and powers stored web-view, Telegram, and CLI lookup. Lookup does not call Toss; it falls back to Naver when the stored list has no match. Web-view search uses the latest complete cache only when its reference date is not after the selected date; it does not reconstruct historical listings.
- `GET /api/v1/market-calendar/KR` is available through `toss-market-calendar-check` for explicit operator-supplied dates. It compares Toss sessions with local weekday/holiday rules, reports mismatches or unknown dates, and never edits calendar rules, SQLite, Telegram, or scheduler registration.
- Live calendar checks require `--live --confirm-token-reissue`. The existing close task requires the existing live/token/save gates and current DB schema; no separate scheduler task is added.
- `GET /api/v1/stocks/{symbol}/warnings` and all other unapproved APIs remain deferred.
- These decisions supersede the pre-key planning language below. The current operational details are in [market-data-runbook.md](market-data-runbook.md) and [mini-pc-runbook.md](mini-pc-runbook.md).

## Daily Top2 Candle Chart — Original UI Decision (2026-09-29)

The original raw-candle chart route remains available. The Main UI now uses the combined Top2 technical-indicator panel documented below; that panel offers 50/100/200 trading-day display windows, defaults to 200, initially selects RSI 14, and uses adjusted prices. The 30/90/180 choice recorded below is historical and was superseded by the current 50/100/200 selector on 2026-10-10.

- The official [Toss Market Data guide](https://developers.tossinvest.com/docs/market-data) documents `interval=1m|1d`, up to 200 bars per request, newest-first ordering, inclusive `before` pagination, and `adjusted=true` by default. There is no native `15m` interval. Candles use the separate `MARKET_DATA_CHART` rate group.
- `GET /api/toss-priority-daily-candles?date=...&days=...` remains bounded to 30, 90, or 180 daily bars per server-derived Top2 stock. The Main chart does not call this raw projection; it uses `/api/priority-indicators` below.
- The initial chart default was 90 trading days; the user changed it to 180 on 2026-10-09. On 2026-10-10, the current selector changed to 50/100/200 trading days with 200 default and RSI 14 initially selected. The chart shows actual dates without filling missing sessions and remains on-demand and non-persistent. It does not affect Top2 ordering, news, or scoring.
- The raw chart remains historical price/volume context. The separate user-defined Main Top2 condition projection is documented below; it is not an empirically validated prediction or generic trading recommendation.

### Selected User Choices

| Choice | Direction | Benefit | Cost / limitation | State |
|---|---|---|---|---|
| **A** | Fixed 60 trading-day window, ending on the Top2 candidate's business date. | Roughly one-quarter of daily bars; one bounded request, no future-date leakage, simple display. | Does not show longer context unless the window changes later. | Not selected. |
| **B — selected (historical)** | Let the user choose 30/90/180 trading-day windows, ending on the Top2 business date. | Matches the user's one-month/quarter/half-year views; 180 rows fit within one API response. | Adds a small range control; the exact calendar span varies with market holidays. | Superseded on 2026-10-10 by the current 50/100/200 selector with 200 default. |

| Choice | Price basis | Benefit | Cost / limitation | State |
|---|---|---|---|---|
| **A — selected** | `adjusted=true` for daily history. | Better continuity across splits and other corporate actions when comparing a multi-month path. | Historical adjusted values can differ from the prices originally quoted at the time. | Implemented. |
| **B** | `adjusted=false`. | Shows unadjusted historical traded prices. | Corporate-action jumps can look like real trend breaks. | Not selected. |

#### Chart end-date basis

| Choice | Direction | Benefit | Cost / limitation | State |
|---|---|---|---|---|
| **A — selected** | End the series on the Top2 candidate's business date. | Candidate evidence and price history share one date; avoids future data when viewing an archived Top2. | The chart stops at the archived candidate date, even if a newer market date exists. | Implemented. |
| **B** | End the series on the latest market date regardless of the Top2 candidate date. | Shows newer market movement beside the candidate. | Mixes an older candidate decision with later price action and can bias historical review. | Not selected. |

**Fixed chart rules:** use only the server-derived Top2; set inclusive `before` to the chosen end date's 23:59:59 in the project timezone (the `+09:00` offset is URL-encoded); show the received count and exact date range; do not fill missing dates. Each response timestamp is checked against the Top2 business-date bound. The chart draws a boundary line and month label at each new month represented in the returned trading bars.

**Assessment:** the user's daily-bar direction is implemented. Compared with a 180-minute window, daily bars cover the requested month/quarter/half-year periods and expose month transitions. This improves historical comparison, but the chart remains descriptive context rather than a predictive signal.

## Included sections
- Toss OpenAPI Read-Only Lab Contract
- Toss OpenAPI Official API Inventory
- Toss OpenAPI Post-Key Read-Only Lab Runbook

<!-- Merged from: docs/codex/toss-openapi-lab.md -->
## Toss OpenAPI Read-Only Lab Contract

## Purpose

This contract defines the allowed Toss Securities OpenAPI read-only runtime,
the remaining lab boundary, and the historical pre-key plan.

Current decision:

- Toss OpenAPI still has a read-only lab lane for docs, probes, and fixtures.
- Promoted features include the public-safe `web-view` current-price and same-day
  provisional investor-trading-volume projection for server-derived top-2 `우선 확인`
  candidates, plus same-day KOSPI/KOSDAQ indicator prices, provisional aggregate
  investor flow, the latest-date Top20 market-attention projection, and the
  once-daily full Korean stock-universe cache. The on-demand selected-date Main
  Top2 chart/indicator panel is also public-safe and read-only; it displays
  50/100/200 trading days (default 200) with RSI 14 initially selected.
- The promoted paths may read local `.env.toss-openapi` after live opt-in and
  credentials are present. They call only allowlisted `prices`, the bounded
  Top2 daily `candles` projection (`interval=1d`, `adjusted=true`, up to 200 per
  page and four pages maximum; display range 50/100/200 trading days, default
  200),
  the fixed `MARKET_TRADING_AMOUNT` Top20 ranking, fixed KOSPI/KOSDAQ aggregate
  investor-trading references, the fixed current-day top-2 stock
  investor-trading-volume reference, and `stocks/all` for the three fixed KR
  markets in the close capture. `market-calendar/KR` is used only by the explicit
  operator date-check command.
- No broker execution, order routing, public trading call, account data, or
  admin-gui connection is approved. The existing `20:05` close task persists
  the approved market context and stock-universe cache. Lookup remains stored-
  data based and does not trigger a live Toss request.

Canonical project boundaries still live in:

- [surface-guide.md]({PROJECT_ROOT}/docs/codex/surface-guide.md)
- [data-governance.md]({PROJECT_ROOT}/docs/codex/data-governance.md)
- [data-governance.md]({PROJECT_ROOT}/docs/codex/data-governance.md)
- [candidate-evidence.md]({PROJECT_ROOT}/docs/codex/candidate-evidence.md)

This document supports those canonical docs. It does not override them.

The official `openapi.json` remains the full endpoint and schema inventory.
This document tracks every operation identity and only the schema handling
needed for this project's approved and denied surfaces.

## Official Source Basis

Use official Toss Securities documents first:

| Source | Role |
| --- | --- |
| <https://developers.tossinvest.com/docs> | Human interactive API reference. |
| <https://developers.tossinvest.com/llms.txt> | Official LLM-readable source-of-truth pointer. |
| <https://openapi.tossinvest.com/openapi-docs/overview.md> | Overview, endpoint groups, auth, rate limits, and errors. |
| <https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md> | Markdown API reference index. |
| <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json> | Canonical OpenAPI document for exact endpoints and schemas. |

Observed official-doc facts as of `2026-10-08` (`1.2.24`, `38` paths, `41`
operations, `101` schemas):

- Base server is `https://openapi.tossinvest.com`.
- Authentication uses OAuth 2.0 Client Credentials Grant.
- All API calls except `POST /oauth2/token` require
  `Authorization: Bearer {access_token}`.
- Account, asset, order-history, order-info, order, and conditional-order APIs require
  `X-Tossinvest-Account` when the endpoint is account-contextual.
- Market data, stock info, market info, ranking, and market indicators are
  user-account-independent but still require an access token.
- Conditional orders register automatic execution and are denied alongside
  direct order creation, modification, and cancellation.

## Product Role

| Role | Current status | Boundary |
| --- | --- | --- |
| Read-only quote/reference | Promoted for `web-view` and scheduled market-briefing top-2 current price | Server derives up to two `우선 확인` symbols; no arbitrary symbol query. |
| Stock/reference metadata | Promoted as once-daily stored KR stock-universe cache | Fixed KOSPI/KOSDAQ/KR_ETC results support listing lookup and Top20 classification; no per-query Toss request. |
| Market calendar/exchange rate | KR calendar promoted for explicit operator date checks; exchange rate remains future | Calendar reports local/Toss differences and does not alter local scheduling rules. |
| Ranking/market indicators | Promoted as an opt-in read-only market-context projection | Fixed `tradingAmount` Top20, KOSPI/KOSDAQ current indicator prices, and same-day provisional aggregate investor flow provide the primary current market context. They must not replace report candidates or stock-level KRX flow. |
| Account/balance read-only | Operator-only lab candidate | Never public. No production DB write. No scheduler or Telegram integration. |
| Order history/order info | Operator-only lab candidate at most | Treat as execution-adjacent; keep away from public surfaces. |
| Execution lab | Deferred | Requires separate order-safety, audit, permissions, failure, and rollback contract. |
| Public `web-view` projection | Approved for top-2 current price, same-day investor volume, latest-date market context, and selected-date Top2 chart/indicators | Current market context is Toss-first; stored KRX daily rows are collapsed confirmed-history/fallback reference. Candles are adjusted, date-bounded, up to 800 fetched bars and displayed in 50/100/200-trading-day windows (default 200, RSI 14 initially selected); never account/order data. |

Toss is not a replacement for the current source ownership model:

- Naver remains the report source of truth.
- KRX remains the stored daily market-history and confirmed fallback source.
- KRX Data Marketplace remains the historical stock-flow and `[12010]` source;
  `[12010]` has no public candidate or market projection.
- Toss is the primary read-only intraday/reference lane for the bounded current
  market context; it does not replace the KRX archive or stock-flow history.

## Pre-Key Allowed Work (Historical)

Allowed before key issuance:

- Maintain this contract and an endpoint allowlist/denylist.
- Review official docs, OpenAPI schemas, auth model, error envelope, and rate
  limits.
- Define secret naming policy without creating or reading real secret values.
- Design fixture-only parsers using non-secret mock payloads.
- Design a provider interface with fake transport only.
- Add tests that prove a future lab client has no network by default.
- Add tests that block order endpoints, account headers, production DB writes,
  Telegram sends, scheduler registration, and public surface integration.
- Use disabled placeholder DTOs such as:
  - `source_configured=false`
  - `live_fetch=false`
  - `writes_db=false`
  - `sends_telegram=false`
  - `registers_scheduler=false`
  - `connects_admin_gui=false`
  - `connects_web_view=false`
  - `affects_ordering=false`

## Pre-Key Forbidden Work (Historical; current exceptions are listed above)

Forbidden outside the explicitly promoted read-only projections:

- Reading general `.env` or any non-dedicated secret store for Toss credentials.
- Entering, storing, logging, or committing a real `client_id`,
  `client_secret`, access token, or account id.
- Calling `POST /oauth2/token` except through the promoted read-only
  in-memory token owner after `.env.toss-openapi` live opt-in.
- Calling any Toss `/api/v1/...` runtime endpoint except allowlisted
  market/reference endpoints: `prices` and fixed same-day stock
  `investor-trading` for the promoted `web-view` top-2 path; fixed Top20 ranking
  and KOSPI/KOSDAQ aggregate investor-trading references for the promoted
  market-context projection; and
  `stocks`/`market-calendar-kr` for manual probes.
- Capturing real account, holding, order, conditional-order, buying-power,
  sellable-quantity, or commission data.
- Writing Toss data into production SQLite.
- Registering a standalone Toss scheduler task beyond the approved 20:00 baseline task.
- Sending Toss-derived Telegram messages outside the approved `09:15`/`12:00`/`15:15` market-briefing slots.
- Connecting Toss to `admin-gui` or any scheduler flow other than the approved market-briefing slots and 20:00 baseline task.
- Connecting live Toss requests to public `web-view` beyond the bounded top-2
  current-price, same-day investor-volume, latest-date Top20 market-context,
  and selected-date Top2 chart/indicator projections defined above. Daily
  candles allow only `interval=1d`, `adjusted=true`, 200 bars per page, and at
  most four inclusive `nextBefore` pages; the UI display windows are
  50/100/200 trading days (default 200, RSI 14 initially selected).
  GET-only stock search may read the stored listing cache described in the
  current approved additions above; it must not call Toss per query.
- Implementing order or conditional-order creation, modification,
  cancellation, automatic execution, or routing.
- Implementing public numeric scores, investment grades, buy/sell wording,
  entry/exit levels, target returns, conviction, or execution language.

## Endpoint Classification

| Group | Endpoints | Pre-key classification |
| --- | --- | --- |
| Auth | `POST /oauth2/token` | Document only. No call before keys and explicit approval. |
| Market Data | `GET /api/v1/prices`, `orderbook`, `trades`, `price-limits`, `candles` | `prices` is allowlisted for top-2 current price; `candles` is allowlisted only for the selected-date server-derived Top2 chart/indicator projection with `interval=1d`, `adjusted=true`, 200 bars per page, and at most four pages. `1m`, arbitrary symbols, and other market-data queries remain unapproved. |
| Stock Info | `GET /api/v1/stocks`, `GET /api/v1/stocks/all`, `GET /api/v1/stocks/{symbol}/warnings`, and five daily trading-trend endpoints | `stocks/all` is allowlisted for fixed KOSPI/KOSDAQ/KR_ETC queries in the existing 20:05 capture; Top2 `investor-trading` remains bounded. Warnings and other daily trend endpoints remain deferred. |
| Market Info | `GET /api/v1/exchange-rate`, `GET /api/v1/market-calendar/KR`, `GET /api/v1/market-calendar/US` | KR calendar is allowlisted only for the explicit read-only operator date-check CLI. Exchange rate and US calendar remain deferred. |
| Ranking | `GET /api/v1/rankings` | Fixed `MARKET_TRADING_AMOUNT / KR / realtime / count=20` is allowlisted for the latest-date Top20 market-context projection only. Other ranking queries remain documentation only. |
| Market Indicators | `GET /api/v1/market-indicators/prices`, `.../{symbol}/candles`, `.../{symbol}/investor-trading` | Fixed KOSPI/KOSDAQ current prices and same-day aggregate investor-trading references are allowlisted for the market-context projection. Other indicator queries remain documentation only; this is not stock-level KRX flow. |
| Account | `GET /api/v1/accounts` | Operator-only lab candidate. Account id is sensitive operational context. |
| Asset | `GET /api/v1/holdings` | Operator-only lab only. Never public. |
| Order History | `GET /api/v1/orders`, `GET /api/v1/orders/{orderId}` | Execution-adjacent operator-only lab only. |
| Order Info | `GET /api/v1/buying-power`, `sellable-quantity`, `commissions` | Execution-adjacent operator-only lab only. |
| Order | `POST /api/v1/orders`, `modify`, `cancel` | Denylist. Separate execution-lab contract required. |
| Conditional Order / History | `POST`/`DELETE`/`GET /api/v1/conditional-orders...` | Denylist. Automatic execution or execution-adjacent context; separate execution-lab contract required. |

## Surface Contract

| Surface | Allowed now | Later condition |
| --- | --- | --- |
| Default/public `web-view` | Top-2 `우선 확인` current-price, same-day provisional investor-volume, current KOSPI/KOSDAQ prices, provisional aggregate investor flow, latest-date Top20 market-context projections, the selected-date server-derived Top2 chart/indicator projection (up to 800 adjusted bars, 50/100/200 trading days displayed, default 200, RSI 14 initially selected), and GET-only search over eligible stored listing cache. | Show source, requested business date, actual candle count/date, and listing-cache reference date. No arbitrary symbols, account/order data, public score, or trading call. |
| Loopback lab `web-view` preview | Superseded by the promoted top-2 projection. | New visual experiments still require separate review before broadening the main path. |
| `admin-gui` | Nothing Toss-connected. | Coarse readiness status only after lab contract and secret redaction are implemented; no token/account display. |
| `operator-review` | Not implemented. | Preferred future surface for raw read-only Toss probe review and response comparison. |
| Telegram | Scheduled market-briefing slots may show the bounded current-price and market context; on-demand stock lookup uses the stored Toss universe before Naver fallback. | No live Toss request from a lookup command; no account/order data, numerical score, or trading instruction. |
| Scheduler | Existing `StockMonitor-TossCloseSnapshot` at 20:05 captures market context and the three fixed KR stock-universe lists. Calendar checks remain manual. | No new scheduler registration, broad polling, or account/order endpoint calls. |
| Production DB | The existing 20:05 capture writes the bounded market context and `toss_stock_universe_cache` behind the current schema and live/token/save gates. | Calendar checks do not write DB. A schema migration must be applied through the documented operator procedure before the capture can run with this version. |

If an approved future intraday reference affects `우선 확인` or
`관찰 우선순위`, the public row must show source and freshness. It must never
show public scores, buy/sell calls, account data, order state, or execution
language.

## Secret Policy

Future names should be documented before use, but no values should be created
or read in the pre-key phase.

Candidate names:

- `TOSS_OPENAPI_CLIENT_ID`
- `TOSS_OPENAPI_CLIENT_SECRET`
- `TOSS_OPENAPI_ACCOUNT_SEQ`

Rules:

- `client_secret`, access tokens, and account sequence values are secrets or
  sensitive operational identifiers.
- Do not print these values in CLI output, logs, JSON, HTML, operation events,
  test snapshots, or exception messages.
- Do not add these values to `.env.example` with real-looking values.
- Do not store access tokens in SQLite.
- The manual CLI probe owns a memory-only token for one invocation. No token,
  credential, or provider response is persisted.

## Minimal Implementation Candidates

Current post-key branch status:

- Candidate 1, the bounded portion of Candidate 2, and the promoted
  `web-view` top-2 current-price projection are implemented.
- `toss-openapi-readonly-probe` is no-network by default.
- The manual CLI probe live allowlist is `getStocks`,
  `getKrMarketCalendar`, and `getPrices`; the separate promoted market-context
  projection uses only its fixed ranking and aggregate investor-trading queries.
- Live use requires local credentials, env opt-in, `--live`, and
  `--confirm-token-reissue`.
- Account, asset, order-info/history, and order operations remain absent.
- Default/public `web-view` Toss projections remain bounded to the top-2
  current-price and same-day provisional investor-volume references, the
  selected-date Top2 daily-candle chart, current KOSPI/KOSDAQ values, aggregate
  investor flow, and latest-date Top20 context. Stock search is a separate
  GET-only read of the stored daily listing cache; it makes no Toss request and
  does not expose market scores or calls.
- No Toss value is connected to `admin-gui`. Telegram market-briefing slots
  remain bounded; on-demand stock lookup reads the stored universe before its
  Naver fallback. The existing 20:05 capture refreshes the listing cache.
- See
  [toss-openapi-postkey-readonly-lab-runbook.md]({PROJECT_ROOT}/docs/codex/toss-openapi-lab.md).

### Candidate 1: Contract And Tests Only

Smallest safe first implementation:

1. Keep this contract current.
2. Add a static endpoint capability matrix in code or test fixtures only.
3. Add denylist tests proving order and account-context endpoints cannot be
   selected by a default read-only lab profile.

No network, no env, no DB, no scheduler, no Telegram, no public route.

### Candidate 2: Fixture-Only Interface

Second safe implementation:

1. Define a provider protocol that receives fake transport.
2. Parse mock `prices`, `stocks`, and `market-calendar/KR` payloads only.
3. Return disabled intraday-reference placeholders until post-key approval.
4. Keep account, holdings, buying-power, order history, and order operations
   out of the interface.

No real HTTP client should be wired by default.

## Post-Key Verification Sequence

After keys exist and the operator explicitly approves a post-key pass:

1. Confirm API permission scope, sandbox/test-key availability, and whether
   order permissions can be disabled.
2. Confirm secret names and redaction in a local-only dry run without network.
3. Issue one token manually only after approval; do not log token response.
4. Probe account-independent endpoints first:
   `stocks`, `market-calendar/KR`, then a tiny `prices` request.
5. Verify rate-limit headers and 401/403/429/error envelope behavior.
6. Probe only the top-2 observation candidate symbols.
7. Keep results in stdout or fixture files only until DB/source semantics are
   separately approved.
8. Review whether source/freshness labels remain clear in the promoted top-2
   `web-view` projection.
9. Only after that, consider an operator-only account read probe.
10. Keep all order `POST` endpoints blocked until a separate execution-lab
    contract is written and reviewed.

## Open Questions

- Does Toss provide sandbox or test credentials?
- Can an app/key be restricted to market-data-only permissions?
- Can order permissions be disabled separately from account/asset reads?
- What is the official token lifetime and revocation behavior?
- Does the API agreement allow redisplaying market data in a small shared
  `web-view`?
- Are WebSocket endpoints officially available, or only planned?
- Are market data values delayed, real-time, or permission-tier dependent?
- Are KRX and NXT venue distinctions represented in price/trade responses?

## Done Criteria For Pre-Key Work

Pre-key preparation is complete when:

- The contract identifies allowlisted and denylisted endpoint groups.
- Tests or review notes prove no network path runs by default.
- Tests or review notes prove no order endpoint can be selected by the default
  read-only profile.
- No secret values are read, written, logged, or committed.
- No production DB, scheduler, Telegram, or `admin-gui` connection exists.
- Public `web-view` connections are limited to the approved top-2
  current-price, same-day provisional investor volume, KOSPI/KOSDAQ current
  prices, aggregate investor flow, and latest-date Top20 market-context
  projections, with no account/order data, candidate reordering, or arbitrary
  symbol query.


<!-- Merged from: docs/codex/toss-openapi-lab.md -->
## Toss OpenAPI Official API Inventory

## Purpose

This is the local memory note for the official Toss Securities OpenAPI surface.

It records the full official API shape before any key, account, token, runtime
probe, or production integration exists. The intent is broad preparation first,
then later pruning through reviewed patches.

This is not an approval to call Toss runtime APIs. The active safety contract is
[toss-openapi-readonly-lab-contract.md]({PROJECT_ROOT}/docs/codex/toss-openapi-lab.md).

## Snapshot

| Item | Value |
| --- | --- |
| Snapshot date | `2026-10-08` |
| Official spec version | `1.2.24` |
| OpenAPI document version | `3.1.0` |
| Base server | `https://openapi.tossinvest.com` |
| Paths | 38 |
| Operations | 41 |
| Schema count | 101 |
| Auth model | OAuth 2.0 Client Credentials |
| Runtime calls made during inventory | None |
| Keys/accounts/tokens used | None |

Official sources:

- <https://developers.tossinvest.com/docs>
- <https://developers.tossinvest.com/llms.txt>
- <https://openapi.tossinvest.com/openapi-docs/overview.md>
- <https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md>
- <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json>

## Global Auth And Headers

| Concern | Official behavior | Project handling |
| --- | --- | --- |
| Token issue | `POST /oauth2/token`, form body, Client Credentials Grant | Document-only before keys. Do not call. |
| Access token | JWT access token in `Authorization: Bearer {access_token}` | Secret. Never log, store in DB, expose in UI, or put in fixtures. |
| Refresh token | Not provided. Reissue through the token endpoint. | Token lifecycle must be designed post-key. |
| Active token count | One valid access token per client; reissue invalidates previous token. | Avoid background token refresh by default. |
| Account header | `X-Tossinvest-Account` uses `accountSeq` from `GET /api/v1/accounts` | Sensitive operational identifier. Operator-only. |
| Public surface | Auth/account/order values may not reach `web-view`; market projections stay bounded to the approved quote, index/flow, and Top20 values. GET-only stock search may read the stored listing cache without making a live Toss request. | Enforce through tests before any surface connection. |

## Rate Limits

Official overview says limits are enforced by client and API group. Current
limits are visible in response headers and may change without prior notice.

| Group | Base TPS | Peak TPS | Project note |
| --- | ---: | ---: | --- |
| `AUTH` | 5 | - | Token calls must be rare and manual in lab. |
| `ACCOUNT` | 1 | - | Operator-only, no polling. |
| `ASSET` | 5 | - | Operator-only, no public surface. |
| `STOCK` | 5 | - | Reference data; cache if ever used. |
| `MARKET_INFO` | 3 | - | Calendar/exchange-rate reference only. |
| `MARKET_DATA` | 10 | - | Future top-2 quote probe candidate. |
| `MARKET_DATA_CHART` | 5 | - | Candles can be heavier; no broad polling. |
| `RANKING` | 5 | - | Ranking semantics differ from the project's candidate evidence; document-only until compared. |
| `MARKET_INDICATOR` | 10 | - | Current endpoint descriptions assign both market-indicator prices and investor trading here; investor trading is aggregate KOSPI/KOSDAQ context, not stock-level flow. |
| `MARKET_INDICATOR_CHART` | 5 | - | Market-index candles; no broad polling. |
| `ORDER` | 6 | 3 from 09:00 to 09:10 KST | Denylisted until execution-lab contract. |
| `ORDER_HISTORY` | 5 | - | Execution-adjacent operator-only. |
| `ORDER_INFO` | 6 | 3 from 09:00 to 09:10 KST | Execution-adjacent operator-only. |
| `CONDITIONAL_ORDER` | 5 | - | Denylisted automatic-execution capability. |
| `CONDITIONAL_ORDER_HISTORY` | 10 | - | Execution-adjacent conditional-order context. |

Relevant response headers:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`
- `Retry-After` on 429

The overview currently lists a separate `MARKET_INDICATOR_PRICE` group, but
the canonical `getMarketIndicatorPrices` endpoint description names
`MARKET_INDICATOR`. Treat the endpoint description and returned rate-limit
headers as the runtime source of truth.

Default retry policy for any future lab client:

1. No automatic retry before a post-key contract exists.
2. If approved later, honor `Retry-After`.
3. Use exponential backoff plus jitter.
4. Stop on auth/account/order-safety errors instead of looping.

## Endpoint Inventory

| Group | Method | Path | Operation | Required account header | Main params/body | Rate group | Default project stance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Auth | `POST` | `/oauth2/token` | `issueOAuth2Token` | No | form: `grant_type`, `client_id`, `client_secret` | `AUTH` | Document-only before keys. |
| Market Data | `GET` | `/api/v1/prices` | `getPrices` | No | `symbols`, max 200 comma-separated | `MARKET_DATA` | Promoted only for bounded top-2 `web-view` current-price reference. |
| Market Data | `GET` | `/api/v1/orderbook` | `getOrderbook` | No | `symbol` | `MARKET_DATA` | Future read-only lab allowlist, top-2 only. |
| Market Data | `GET` | `/api/v1/trades` | `getTrades` | No | `symbol`, optional `count` max 50 | `MARKET_DATA` | Future read-only lab allowlist, top-2 only. |
| Market Data | `GET` | `/api/v1/price-limits` | `getPriceLimit` | No | `symbol` | `MARKET_DATA` | Future read-only lab allowlist. |
| Market Data | `GET` | `/api/v1/candles` | `getCandles` | No | server-derived Top2 `symbol`, `interval=1d`, `count=200` per page, selected-date `before`/`nextBefore`, `adjusted=true`, maximum four pages | `MARKET_DATA_CHART` | Promoted only for the on-demand public Top2 chart/indicator panel. The UI selects a 50/100/200-trading-day display window (default 200, RSI 14 initially selected) from the bounded history. `1m`, arbitrary symbols, DB persistence, and scheduler use remain out of scope. |
| Stock Info | `GET` | `/api/v1/stocks` | `getStocks` | No | `symbols`, max 200 comma-separated | `STOCK` | Future reference allowlist. |
| Stock Info | `GET` | `/api/v1/stocks/all` | `listStocks` | No | required `market`; optional `status`, `securityType`, `commonShare` | `STOCK_ALL` | Fixed KOSPI/KOSDAQ/KR_ETC once-daily capture; stored lookup and Top20 classification only. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/warnings` | `getStockWarnings` | No | path `symbol` | `STOCK` | Future caution/reference allowlist. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/investor-trading` | `getStockInvestorTrading` | No | fixed path KR Top2 `symbol`, `count=1`, latest-date `until` | `STOCK_TRADING_TREND` | Promoted only as current-day provisional foreigner/institution net-volume reference beside the existing Top2. No DB write, candidate ordering, or trading call. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/program-trades` | `getStockProgramTrades` | No | path KR `symbol`, optional `count` max 100/`until` | `STOCK_TRADING_TREND` | Document only. Daily stock-level trend; source semantics must be reviewed before any lab use. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/short-selling` | `getStockShortSelling` | No | path KR `symbol`, optional `count` max 100/`until` | `STOCK_TRADING_TREND` | Document only. Daily stock-level trend; source semantics must be reviewed before any lab use. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/credit-trades` | `getStockCreditTrades` | No | path KR `symbol`, optional `count` max 100/`until` | `STOCK_TRADING_TREND` | Document only. Daily stock-level trend; source semantics must be reviewed before any lab use. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/securities-lending` | `getStockSecuritiesLending` | No | path KR `symbol`, optional `count` max 100/`until` | `STOCK_TRADING_TREND` | Document only. Daily stock-level trend; source semantics must be reviewed before any lab use. |
| Market Info | `GET` | `/api/v1/exchange-rate` | `getExchangeRate` | No | `baseCurrency`, `quoteCurrency`, optional `dateTime` | `MARKET_INFO` | Future reference only; not order FX. |
| Market Info | `GET` | `/api/v1/market-calendar/KR` | `getKrMarketCalendar` | No | optional `date` | `MARKET_INFO` | Explicit operator date-check command only; read-only, no rule or scheduler mutation. |
| Market Info | `GET` | `/api/v1/market-calendar/US` | `getUsMarketCalendar` | No | optional `date` | `MARKET_INFO` | Future only if US scope is approved. |
| Ranking | `GET` | `/api/v1/rankings` | `getRankings` | No | `type`, `marketCountry`, `duration`, optional caution exclusion/count | `RANKING` | Promoted only as fixed `MARKET_TRADING_AMOUNT / KR / realtime / count=20` market context; never changes candidate priority. |
| Sector | `GET` | `/api/v1/sectors` | `listSectors` | No | none | `SECTOR` | Document only. No runtime allowlist or surface expansion. |
| Sector | `GET` | `/api/v1/sectors/rankings` | `getSectorRankings` | No | `type`, `marketCountry`, `duration` | `SECTOR_RANKING` | Document only. No runtime allowlist or surface expansion. |
| Sector | `GET` | `/api/v1/sectors/{sectorId}` | `getSector` | No | path `sectorId`, `marketCountry` | `SECTOR` | Document only. No runtime allowlist or surface expansion. |
| Sector | `GET` | `/api/v1/sectors/{sectorId}/stocks` | `getSectorStocks` | No | path `sectorId`, `marketCountry` | `SECTOR` | Document only. No runtime allowlist or surface expansion. |
| Sector | `GET` | `/api/v1/sectors/{sectorId}/etfs` | `getSectorEtfs` | No | path `sectorId`, `marketCountry` | `SECTOR` | Document only. No runtime allowlist or surface expansion. |
| Market Indicators | `GET` | `/api/v1/market-indicators/prices` | `getMarketIndicatorPrices` | No | `symbols` | `MARKET_INDICATOR` | Future market-context lab only. |
| Market Indicators | `GET` | `/api/v1/market-indicators/{symbol}/candles` | `getMarketIndicatorCandles` | No | path `symbol`, `interval`, `count`, optional `before` | `MARKET_INDICATOR_CHART` | Future market-context lab only; no broad backfill. |
| Market Indicators | `GET` | `/api/v1/market-indicators/{symbol}/investor-trading` | `getMarketIndicatorInvestorTrading` | No | path `symbol`, `interval`, `count`, optional `until` | `MARKET_INDICATOR` | Promoted only as fixed previous-business-day KOSPI/KOSDAQ aggregate context; never replaces stock-level KRX flow. |
| Account | `GET` | `/api/v1/accounts` | `getAccounts` | No | none | `ACCOUNT` | Operator-only lab candidate; never public. |
| Asset | `GET` | `/api/v1/holdings` | `getHoldings` | Yes | optional `symbol` | `ASSET` | Operator-only lab; never public. |
| Order History | `GET` | `/api/v1/orders` | `getOrders` | Yes | required `status`, optional `symbol/from/to/cursor/limit` | `ORDER_HISTORY` | Execution-adjacent, operator-only lab at most. |
| Order History | `GET` | `/api/v1/orders/{orderId}` | `getOrder` | Yes | path `orderId` | `ORDER_HISTORY` | Execution-adjacent, operator-only lab at most. |
| Order Info | `GET` | `/api/v1/buying-power` | `getBuyingPower` | Yes | `currency=KRW|USD` | `ORDER_INFO` | Execution-adjacent, not public. |
| Order Info | `GET` | `/api/v1/sellable-quantity` | `getSellableQuantity` | Yes | `symbol` | `ORDER_INFO` | Execution-adjacent, not public. |
| Order Info | `GET` | `/api/v1/commissions` | `getCommissions` | Yes | none | `ORDER_INFO` | Operator-only reference at most. |
| Order | `POST` | `/api/v1/orders` | `createOrder` | Yes | `OrderCreateRequest` | `ORDER` | Denylist. Requires separate execution-lab contract. |
| Order | `POST` | `/api/v1/orders/{orderId}/modify` | `modifyOrder` | Yes | `OrderModifyRequest` | `ORDER` | Denylist. Requires separate execution-lab contract. |
| Order | `POST` | `/api/v1/orders/{orderId}/cancel` | `cancelOrder` | Yes | optional body | `ORDER` | Denylist. Requires separate execution-lab contract. |
| Conditional Order History | `GET` | `/api/v1/conditional-orders` | `getConditionalOrders` | Yes | `status`, optional `symbol/cursor/limit` | `CONDITIONAL_ORDER_HISTORY` | Execution-adjacent; never public. |
| Conditional Order History | `GET` | `/api/v1/conditional-orders/{conditionalOrderId}` | `getConditionalOrder` | Yes | path `conditionalOrderId` | `CONDITIONAL_ORDER_HISTORY` | Execution-adjacent; never public. |
| Conditional Order | `POST` | `/api/v1/conditional-orders` | `createConditionalOrder` | Yes | conditional-order create request | `CONDITIONAL_ORDER` | Denylist. Automatic execution; separate execution-lab contract required. |
| Conditional Order | `POST` | `/api/v1/conditional-orders/{conditionalOrderId}/modify` | `modifyConditionalOrder` | Yes | conditional-order modify request | `CONDITIONAL_ORDER` | Denylist. Automatic execution; separate execution-lab contract required. |
| Conditional Order | `DELETE` | `/api/v1/conditional-orders/{conditionalOrderId}` | `cancelConditionalOrder` | Yes | path `conditionalOrderId` | `CONDITIONAL_ORDER` | Denylist. Automatic execution; separate execution-lab contract required. |

## Response And Error Model

Most non-auth APIs return the common `ApiResponse` envelope with a `result`
field. Auth token responses use OAuth2 standard response shape instead.

Error envelope:

- `error.requestId`
- `error.code`
- `error.message`
- optional `error.data`

Important handling rules:

- Treat unknown error codes as expected future compatibility cases.
- Use `code` for internal mapping; official docs note `message` can be blank.
- Include `requestId` in operator-only troubleshooting, but do not expose it in
  public `web-view` unless separately reviewed.
- Never include auth tokens, account ids, order ids, or request bodies in public
  error copy.

Common HTTP statuses seen in the spec:

- `400`: invalid request, validation, unsupported closed-order history, etc.
- `401`: invalid/missing/expired token or account auth failure.
- `403`: forbidden or edge-blocked.
- `404`: missing stock, account, order, exchange-rate, or route.
- `409`: order mutation conflict.
- `422`: order/business-rule failure.
- `429`: rate limit.
- `500`: internal error or maintenance.

## Key Models To Remember

### Auth

| Model | Fields | Handling |
| --- | --- | --- |
| `OAuth2TokenResponse` | `access_token`, `token_type`, `expires_in` | Entire response is sensitive. Do not log or persist. |
| `OAuth2ErrorResponse` | `error`, `error_description`, `error_uri` | Operator-only troubleshooting. |

### Market Data

| Model | Fields | Project use candidate |
| --- | --- | --- |
| `PriceResponse` | `symbol`, nullable `timestamp`, `lastPrice`, `currency` | Top-2 intraday source/freshness reference. |
| `OrderbookResponse` | nullable `timestamp`, `currency`, `asks`, `bids` | Operator lab only until burden and display value are proven. |
| `OrderbookEntry` | `price`, `volume` | No public depth display by default. |
| `Trade` | `price`, `volume`, `timestamp`, `currency` | Possible freshness check; no trading signal. |
| `PriceLimitResponse` | `timestamp`, `currency`, upper/lower limit fields in schema | Caution/reference only. |
| `Candle` | `timestamp`, `openPrice`, `highPrice`, `lowPrice`, `closePrice`, `volume`, `currency` | Lab comparison only; KRX remains stored daily source. |
| `CandlePageResponse` | `candles`, `nextBefore` | No broad historical backfill without separate approval. |

### Stock And Market Info

| Model | Fields | Project use candidate |
| --- | --- | --- |
| `StockInfo` | `symbol`, `name`, `englishName`, `isinCode`, `market`, `securityType`, `isCommonShare`, `status`, `currency`, dates, shares, leverage, KR detail | Reference comparison with KRX/Naver identity. Do not overwrite by default. |
| `StockWarning` | `warningType`, `exchange`, `startDate`, `endDate` | Caution/reference label. Allow unknown codes. |
| `KrMarketCalendarResponse` | `today`, `previousBusinessDay`, `nextBusinessDay` | Calendar comparison candidate. |
| `KrMarketDay` | `date`, nullable `integrated` trading hours | KST business-day reference only. |
| `UsMarketCalendarResponse` | `today`, `previousBusinessDay`, `nextBusinessDay` | Future only if US scope is approved. |
| `ExchangeRateResponse` | `baseCurrency`, `quoteCurrency`, `rate`, `midRate`, `basisPoint`, `rateChangeType`, `validFrom`, `validUntil` | Reference only; docs say actual order FX may differ. |

### Ranking And Market Indicators

| Model / endpoint | Project use candidate |
| --- | --- |
| `GET /api/v1/rankings` | Future market-attention comparison only. The official basis includes market-wide and Toss Securities execution-based rankings, so it must not directly alter existing report/candidate priority. |
| `GET /api/v1/market-indicators/prices` and `.../{symbol}/candles` | Future market-index or government-bond context only. |
| `GET /api/v1/market-indicators/{symbol}/investor-trading` | Future aggregate market context only. It covers KOSPI/KOSDAQ investor trading amount, not per-stock daily investor flow; KRX Data Marketplace remains the stock-level flow source. |

### Account And Asset

| Model | Fields | Handling |
| --- | --- | --- |
| `Account` | `accountNo`, `accountSeq`, `accountType` | Sensitive. Operator-only lab. |
| `HoldingsOverview` | purchase amount, market value, profit/loss, daily P/L, items | Private account data. Never public. |
| `HoldingsItem` | `symbol`, `name`, country/currency, quantity, last price, average purchase price, market value, P/L, cost | Private account data. Never public. |
| `BuyingPowerResponse` | `currency`, `cashBuyingPower` | Execution-adjacent. Never public. |
| `SellableQuantityResponse` | `sellableQuantity` | Execution-adjacent. Never public. |
| `Commission` | market country, commission rate, start/end dates | Operator-only reference at most. |

### Order

| Model | Fields | Handling |
| --- | --- | --- |
| `OrderCreateRequest` | quantity-based or amount-based order fields | Denylist until execution-lab contract. |
| `OrderCreateQuantityBased` | `clientOrderId`, `symbol`, `side`, `orderType`, `timeInForce`, `quantity`, optional `price`, `confirmHighValueOrder` | Do not implement now. |
| `OrderCreateAmountBased` | US market amount order fields including `orderAmount` | Do not implement now. |
| `OrderModifyRequest` | `orderType`, optional `quantity`, optional `price`, `confirmHighValueOrder` | Do not implement now. |
| `Order` | `orderId`, `symbol`, `side`, `orderType`, `timeInForce`, `status`, price/quantity/order amount, currency, timestamps, execution | Private execution data. |
| `OrderExecution` | filled quantity, average price, filled amount, commission, tax, filled time, settlement date | Private execution data. |
| `OrderStatus` | `PENDING`, `PENDING_CANCEL`, `PENDING_REPLACE`, `PARTIAL_FILLED`, `FILLED`, `CANCELED`, `REJECTED`, `CANCEL_REJECTED`, `REPLACE_REJECTED`, `REPLACED` | Execution-lab only if ever used. |

### Conditional Order

| Model / endpoint | Handling |
| --- | --- |
| Conditional-order create/modify/cancel and history | Automatic execution capability, including `SINGLE`, `OCO`, and `OTO`. Keep entirely denylisted from this project until a separately approved execution-lab contract exists. |

Order safety facts from official docs:

- `clientOrderId` is an optional idempotency key, valid for 10 minutes.
- Price rules differ between KR and US.
- KR limit prices must follow tick size.
- US price precision differs below/above 1 USD.
- High-value orders require `confirmHighValueOrder`.
- Very high value modifications can still be rejected.
- US quantity modification is not supported.
- US amount orders are regular-market only.

These facts are stored here only so a future execution-lab design does not
start from memory. They do not approve any order implementation.

## Broad-First Profiles For Later Pruning

The project can keep the official API memory broad while keeping runtime behavior
narrow. Future patches should choose one profile explicitly.

| Profile | Includes | Excludes | Default state |
| --- | --- | --- | --- |
| `docs_only` | Full operation identity inventory and canonical schema reference | All runtime calls | Current default. |
| `market_reference_lab` | `prices`, `stocks`, `stock warnings`, `market-calendar/KR`, maybe `trades` for freshness | Account, holdings, order info/history, order POST | Candidate after keys and approval. |
| `operator_account_lab` | `accounts`, maybe `holdings` with redaction | Public surfaces, DB write, Telegram, scheduler, order POST | Not approved now. |
| `execution_review_lab` | Order docs, order fixture schemas, safety tests | Real order create/modify/cancel | Separate contract required. |
| `public_projection` | Source/freshness labels, current prices and same-day provisional investor volume for server-derived Top2 candidates, selected-date Top2 candles (`adjusted=true`, up to 800 fetched / 50/100/200 trading days displayed, default 200, RSI 14 initially selected), bounded latest-date Top20 context, and GET-only stored-listing search | Account, holdings, orders, buying power, sellable quantity, commissions, score/trading call, arbitrary public symbols or candle intervals | Approved only for the listed projections; stock search makes no live Toss request and shows its stored reference date. |

## Cut-Down Rules

When pruning later:

1. Prefer removing runtime access before removing documentation.
2. Keep denylisted order knowledge documented even if no code path exists.
3. Keep account/asset/order-info grouped as private account context.
4. Keep Market Data separate from KRX stored daily reference.
5. If a field cannot be shown with clear source/freshness, keep it out of
   public `web-view`.
6. If a field implies ability or intent to trade, keep it out of public
   `web-view` and Telegram.
7. If a feature needs `X-Tossinvest-Account`, it is not a public feature.

## Verification Notes

This inventory was built from official documentation endpoints only:

- Markdown reference pages were fetched for endpoint and model descriptions.
- The canonical OpenAPI JSON was fetched to count operations and schemas.
- No `POST /oauth2/token` call was made.
- No `/api/v1/...` runtime endpoint was called.
- No `.env` value, key, token, account, holding, or order value was read.
- The `2026-07-10` `1.2.2` recheck expanded the spec from `20` to `27` paths,
  `21` to `30` operations, and `53` to `72` schemas. Added groups are Ranking,
  Market Indicators, Conditional Order, and Conditional Order History. The
  manual probe profile allows `stocks`, `market-calendar/KR`, and `prices`; the
  promoted market-context projection separately allows only its fixed ranking
  and KOSPI/KOSDAQ aggregate-investor queries.
- The `2026-07-16` `1.2.4` recheck kept all `30` documented
  method/path/operationId entries and the `72` schema count unchanged.
- The `2026-07-28` `1.2.5` recheck again kept all `30` documented
  method/path/operationId entries and the `72` schema count unchanged.
- The `2026-08-06` `1.2.9` recheck again kept all `30` documented
  method/path/operationId entries and the `72` schema count unchanged.
- The detailed `2026-08-06` audit also confirmed the 13 official tags,
  OAuth2 client-credentials scheme, and all documented operation identities;
  it corrected stale wording so the promoted Top20 market-context projection
  is not misdescribed as an unapproved public route.
- The `2026-08-08` `1.2.13` recheck expanded the spec to `32` paths, `35`
  operations, and `89` schemas. It added five KR stock-level daily trading-trend
  reads: investor trading, program trades, short selling, credit trades, and
  securities lending. They remain documentation-only pending a dedicated
  source-semantics review; no runtime call or surface expansion is approved.
- The `2026-08-11` recheck kept version `1.2.13` but expanded the spec to `33`
  paths, `36` operations, and `90` schemas with `GET /api/v1/stocks/all`
  (`listStocks`). It is a bulk market-universe endpoint with a dedicated
  `STOCK_ALL` rate group and remains document only: no runtime allowlist,
  broad ingest, or public-surface use is approved.
- The `2026-08-12` `1.2.14` recheck kept all `33` paths, `36` operations,
  `90` schemas, and every documented method/path/operationId unchanged. No
  runtime allowlist or surface decision changed.
- The `2026-09-09` `1.2.15` recheck kept all `33` paths, `36` operations,
  `90` schemas, and every documented method/path/operationId unchanged. No
  runtime allowlist or surface decision changed.
- The `2026-09-14` `1.2.17` recheck kept all `33` paths, `36` operations,
  `90` schemas, and every documented method/path/operationId unchanged. No
  runtime allowlist or surface decision changed.
- The `2026-09-29` `1.2.19` recheck kept all `33` paths, `36` operations,
  `90` schemas, and every documented method/path/operationId unchanged. No
  runtime allowlist or surface decision changed.
- The `2026-10-07` `1.2.21` recheck kept all `33` paths, `36` operations,
  `90` schemas, and every documented method/path/operationId unchanged. No
  runtime allowlist or surface decision changed.
- The `2026-10-08` `1.2.24` recheck expanded the spec to `38` paths, `41`
  operations, and `101` schemas with five Sector reads: `listSectors`,
  `getSectorRankings`, `getSector`, `getSectorStocks`, and `getSectorEtfs`.
  They remain documentation-only; no runtime allowlist or surface decision
  changed.


<!-- Merged from: docs/codex/toss-openapi-lab.md -->
## Toss OpenAPI Post-Key Read-Only Lab Runbook

## Purpose

This runbook covers the first bounded Toss Securities OpenAPI validation after
client credentials have been issued.

It does not approve account, asset, order-info, order-history, conditional-order
history, order or conditional-order creation/modification/cancellation,
production DB writes, scheduler, Telegram, `admin-gui`, or general `web-view`
integration. The separately approved, read-only Main Top2 chart/indicator
exception is defined in the 2026-10-08 section below.

The active implementation remains a manual lab CLI:

```text
python -m stock_monitor toss-openapi-readonly-probe
```

The command is no-network by default. A live request requires all three gates:

1. `--live`
2. local `.env.toss-openapi` value `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`
3. `--confirm-token-reissue`

The third gate exists because official documentation says issuing a new token
invalidates the client's previously issued token.

## Official Basis

Verified on `2026-10-08` against:

- <https://developers.tossinvest.com/docs>
- <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json>

Current official spec snapshot:

| Item | Value |
| --- | --- |
| OpenAPI document version | `3.1.0` |
| Official spec version | `1.2.24` |
| Paths | `38` |
| Operations | `41` |
| Schemas | `101` |

## Local Key Input

Do not paste credentials into chat, source files, commands, screenshots, logs,
or test fixtures.

Add only the real values to the local ignored `.env.toss-openapi` file. Use
[.env.toss-openapi.example]({PROJECT_ROOT}/.env.toss-openapi.example) as the
field template:

```dotenv
STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=
STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET=
STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=false
STOCK_MONITOR_TOSS_OPENAPI_BASE_URL=https://openapi.tossinvest.com
STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS=15
```

The general project `.env` is not the Toss credential input path.

Start with `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=false`. Change it to
`true` only for an explicitly reviewed manual probe, then return it to `false`
after the probe.

No Toss account sequence field is prepared yet. Account-context APIs remain
outside this lab profile.

## Allowed Endpoints

`stocks/all` is not a manual probe selector: the existing gated 20:05 capture
calls it once for each of the three fixed Korean markets. Calendar comparisons
use the dedicated `toss-market-calendar-check` command below.

| CLI endpoint | Official operation | Required argument | Limit |
| --- | --- | --- | --- |
| `stocks` | `GET /api/v1/stocks` | one or two `--symbol` values | Reference only |
| `market-calendar-kr` | `GET /api/v1/market-calendar/KR` | optional `--date` | Calendar comparison only |
| `prices` | `GET /api/v1/prices` | one or two `--symbol` values | Intraday reference only |

The CLI has no account, asset, order-info, order-history, or order endpoint
selector.

## Plan-Only Checks

These commands do not read `.env`, issue a token, or call Toss:

```powershell
python -m stock_monitor toss-openapi-readonly-probe --endpoint stocks --symbol 005930 --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint market-calendar-kr --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint prices --symbol 005930 --json
python -m stock_monitor toss-market-calendar-check --date 2026-10-01 --date 2026-10-02 --json
```

Review that each output says:

- `mode=plan`
- `live_fetch=false`
- credentials are not read
- `writes_db=false`
- `sends_telegram=false`
- `registers_scheduler=false`
- `connects_admin_gui=false`
- `connects_web_view=false`

## First Live Validation

The calendar command's plan mode does not read credentials. Use live only after
reviewing the plan and local `.env.toss-openapi` fields:

```powershell
python -m stock_monitor toss-openapi-readonly-probe --endpoint stocks --symbol 005930 --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint market-calendar-kr --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint prices --symbol 005930 --live --confirm-token-reissue --json
python -m stock_monitor toss-market-calendar-check --date 2026-10-01 --date 2026-10-02 --live --confirm-token-reissue --json
```

Use one command at a time. Every live command issues a new token and can
invalidate a previously issued token.

The live output may include the selected market-reference result and rate-limit
headers. It must not contain client credentials or the access token.

## Safety Properties

- Credentials and live opt-in are accepted only from the dedicated local
  `.env.toss-openapi` file; process environment values do not activate it.
- Live credentials may be sent only to `https://openapi.tossinvest.com`.
- HTTP redirects are rejected before credentials or Bearer tokens can be
  forwarded to another origin.
- The default command does not read secrets or use network access.
- The direct client runner repeats the live-enable and token-reissue gates.
- The low-level token helper repeats the same live-enable and token-reissue
  gates.
- The low-level GET helper also requires explicit live enablement.
- The endpoint allowlist is immutable and revalidated immediately before GET.
- Query parameters are revalidated immediately before GET.
- Successful live responses must match the endpoint-level result container
  shape and contain only official allowlisted response fields. Available
  rate-limit headers are captured but are not assumed to be mandatory.
- Symbols are limited to two per probe.
- Results are printed only; no DB write path exists.
- No retry loop, scheduler task, Telegram send, admin route, or public route is
  connected.
- Account and order endpoint groups remain blocked.

## Stop Conditions

Stop the probe sequence and keep `LIVE_ENABLED=false` when:

- token issuance returns `400`, `401`, `403`, or `429`
- the response shape differs from the official spec
- rate-limit behavior is unexpected or returns `429`
- the key appears to include permissions beyond the reviewed market-reference
  scope
- any output contains a credential, token, account identifier, or order context

Do not continue to account or order APIs after a market-reference error.

## First Live Validation Evidence

Completed manually on `2026-06-12` with one-symbol read-only requests only.
No account header, account/asset/order endpoint, DB write, scheduler, Telegram,
`admin-gui`, or `web-view` connection was used.

| Check | Result |
| --- | --- |
| OAuth token issuance | Succeeded; token remained memory-only |
| `stocks` / `005930` | Succeeded; `STOCK` limit header reported `5` |
| `market-calendar/KR` | Succeeded; `MARKET_INFO` limit header reported `3` |
| `prices` / `005930` after KR market close | Succeeded; provider timestamp remained at the final after-market time |
| Historical separate-lab US probe | `AAPL` was used only for early provider validation; the main manual profile now accepts six-digit Korean stock codes only. |
| `MARKET_DATA` limit header | Reported `10`; requests were paced below the limit |
| Post-check state | Local `LIVE_ENABLED` returned to `false` |

This proves that the bounded `prices` probe can observe changing live market
values during an active market session. It does not approve continuous polling,
storage, account access, or execution. The only approved projection is the
main `web-view` top-2 priority current-price reference described below.

## Promoted Top20 Market-Attention Contract

The existing `StockMonitor-TossCloseSnapshot` at `20:05` calls the fixed
`MARKET_TRADING_AMOUNT / KR / realtime / count=20` ranking query, the bounded
index/aggregate-flow references, Top2 candidate close/flow references, and
`stocks/all` for KOSPI/KOSDAQ/KR_ETC. It persists the stored market context and
complete listing cache after the live, token-reissue, save, and schema gates.
No new task is registered. The Top20 does not create observation candidates,
change candidate order, claim stock-level market flow, expose account data, or
produce a score. The listing cache powers GET-only lookup without a per-query
Toss request.

## Promoted Web-View Priority Quote Projection

The former lab preview was promoted to the main GET-only `web-view` in a
bounded form.

The normal `web-view` command can show Toss current-price and same-day provisional
investor-volume references directly
in the existing top-two `?곗꽑 ?뺤씤` rows when `.env.toss-openapi` has
credentials and `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`:

```powershell
python -m stock_monitor web-view --host 127.0.0.1 --port 8792 --no-open
```

- No extra Toss-specific CLI flag is required; `.env.toss-openapi` is the opt-in boundary.
- Uses the existing `web-view` host/access boundary plus server-derived
  top-2 symbols; it does not accept arbitrary public symbols.
- Adds the reference only to priority rows on the web-view.
- Fetches current prices and the same-day stock investor volume only for the
  latest stored business date's top-two six-digit Korean stock codes. Historical
  dates do not call Toss.
- Recomputes and verifies the latest stored date's top-two priority codes on
  the server before calling Toss; arbitrary symbols are rejected.
- Fetches only when priority rows load or the operator manually refreshes them.
- Issues one memory-only token lazily on the first quote request. A `401`
  response permits one token reissue and one repeated GET for the server
  lifetime; no provider-specific error-code spelling or other automatic retry
  loop is assumed.
- Merges concurrent identical date/symbol requests so they produce one
  bounded price-plus-Top2-investor-volume request set.
- Reuses the same date/symbol response for 30 seconds. When Toss is
  unavailable, a successful response no older than 5 minutes may be returned
  with `cache=stale` and `stale_reason=upstream_unavailable`.
- Investor volume is labelled as same-day provisional data with the provider
  update time; it is not final KRX stock-level flow and not a recommendation.
- Labels the value as `Toss ?꾩옱媛`; it is not the selected historical date's price.
- Reuses the existing `?곗씠??湲곗?` section to show `ready/current/disabled` and cache
  state after a successful quote response; it does not add a separate Toss screen.
- This projection exposes only the bounded top-2 quote and same-day investor-volume
  reference route; the separate Top20 market-context projection remains subject to
  its own contract.
- Exposes no account, order, DB write, scheduler, Telegram, or admin control.
- It is public-safe only as current-price and factual provisional-volume reference
  beside server-derived priority candidates.

## Promoted Raw Daily Top2 Candle Projection (retained from 2026-09-29)

`GET /api/toss-priority-daily-candles?date={business_date}&days={30|90|180}` adds a bounded historical daily-price view in the public GET-only `web-view`.

- The server derives Top2 for the requested archived business date. It calls only those one or two six-digit Korean stock symbols; a caller-supplied `symbols` parameter is ignored.
- The route fixes `interval=1d` and `adjusted=true`, allows only `days=30`, `90`, or `180`, and sets inclusive `before` to 23:59:59 on the Top2 business date in the project timezone. It removes any candle dated after that boundary.
- This raw-candle route remains available to bounded GET clients. The current Main UI uses the combined indicator route below. A user action is required; it does not store daily candles, alter ranking/news, or connect to Telegram, scheduler, `admin-gui`, account, or order APIs.
- The UI shows each stock's actual returned dates and bar count, and highlights the first returned trading day of each calendar month. Missing dates are left missing.
- The chart is descriptive historical price/volume context only. It must not expose public scores, grades, trading recommendations, or claim to forecast trend.

## Promoted Main Top2 Technical Indicators (2026-10-08)

### Local setup and use

1. Keep Toss credentials in the ignored project-root `.env.toss-openapi` file. The exact variable names and safe template are in [Local Key Input](#local-key-input); do not put values in `.env`, source, chat, screenshots, or logs.
2. The read requires `STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID`, `STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET`, `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`, and `MARKET_DATA_CHART` permission on the Toss API client. The live-enabled value is a shared Toss read switch, so only enable it when the existing Toss live operations are intended to be available.
3. Start or restart the local server with `python -m stock_monitor web-view --host 127.0.0.1 --port 8780 --no-open`, sign in through the existing local access gate, select a date with loaded Main candidates, then press `차트 · 지표 확인`.
4. There is no Stock-Newbby server, fork URL, extra cache, or API key to configure. Stock Monitor fetches Toss candles and calculates the factual indicator series locally.

`GET /api/priority-indicators?date={business_date}` derives the Main Top2 on the server and requests only their Toss adjusted daily candles. It uses the existing Toss read-only credentials/configuration, `interval=1d`, `adjusted=true`, up to 200 bars per request and at most four inclusive `nextBefore` pages (800 bars total). Boundary duplicates and candles after the requested date are removed before the local Stock Monitor calculator runs. Since Toss declares `nextBefore` optional, a missing cursor keeps the returned bars visible but labels history as cursor-unavailable; malformed or non-monotonic cursor values fail explicitly. The item-level chart projection carries up to 380 aligned bars; the UI displays a selectable 50/100/200-trading-day window (default 200) with RSI 14 initially selected, candlesticks, SMA 20/60/120/200, volume, and a selected RSI/MACD/OBV/ATR pane.

The browser calls this GET only after the user presses `차트 · 지표 확인`; direct route callers still cannot provide symbols. The projection follows Stock-Newbby's factual indicator settings, is not stored, and does not change candidates, scheduler, Telegram, or `admin-gui`. It does not call a Stock-Newbby server or update a Newbby cache. Toss source time, last returned bar date, requested date, and unknown candle-finality status remain separate. Missing market classification does not block the candle query: keep market `unknown`, use the six-digit Toss symbol without a guessed suffix, and disclose that label gap. Missing candles and provider errors stay explicit. The separate `/api/toss-priority-daily-candles` projection remains available as a bounded raw-candle route, but the Main chart UI uses the combined indicator route. The chart shows each SMA/EMA/WMA family's individual 20/60/120/200 values with its own stack state.

### User-defined Main Top2 condition projection (clarified 2026-10-10)

Price triggers alone do not confirm a condition. The UI shows `진입 확인 기준` and `탈출 확인 기준` rows with threshold, selected-date close, and reached/missed state. Both compare the adjusted close against completed bars preceding the actual bar: prior 20-bar high for entry, prior 10-bar low for exit. A plain-language `condition_explanation` explains that indicators and volume must confirm a reached price trigger and names blockers such as mixed MA stacks or volume below 1.2. A confirmed entry additionally requires all direction components to be up: RSI14 > 50, MACD > signal, each strict adjusted-price stack close>SMA20>SMA60>SMA120>SMA200 / close>EMA20>EMA60>EMA120>EMA200 / close>WMA20>WMA60>WMA120>WMA200, close above Bollinger20 middle, close above Donchian20 middle, and OBV delta5 > 0. A confirmed exit requires the strict reverse of each component. Volume ratio20 >= 1.2 is a separate gate for both. Neutral/mixed checks do not confirm. Missing required price, direction, or volume data shows `판정 불가`; with all required inputs present, a reached price trigger with mixed/failed confirmation shows `가격 기준 도달 · 보조지표 확인 필요` and component states; neither trigger shows `두 가격 조건 미충족` with context.

ATR14 and each separate `peak=true` bin from the HLC3 volume profile are displayed as context only; the closing price is labeled within a bin, between bins, above all bins, or below all bins without combining distinct bins into a single area. Structure labels distinguish `수평 가격 기준 · 기준선 계산됨` from unavailable recognized shapes `조건에 맞는 채널 구조 없음` and `조건에 맞는 삼각형 구조 없음`; no recognized shape is not evidence in the opposite direction. Structure measurements are separate. No score or vote totals are generated. The flat-RSI neutral correction is recorded in root `calculationVersion=stock-monitor-indicator-v2`; existing indicator groups retain `TECHNICAL_VERSION=technical-v4`. The schemaVersion 1 snapshot shape/allowlist is unchanged. This is the user's transparent filter, not an empirically validated rule or an error-reduction claim. It remains separate from candidate order, persistence, scheduler, Telegram, broker/order access, and automatic execution.

## Verification Commands

```powershell
python -m pytest tests/test_toss_openapi.py tests/test_config.py -q
python -m pytest tests/test_cli_commands.py -q -k "data_source_lane_audit or toss_openapi_readonly_probe"
python -m pytest tests/test_web_view.py -q -k "toss_priority or toss_ready"
python -m stock_monitor data-source-lane-audit --json
```
