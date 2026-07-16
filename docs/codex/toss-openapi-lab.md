# Toss OpenAPI Lab

Read-only Toss OpenAPI boundary, official inventory, and post-key probe procedure.

## Included sections
- Toss OpenAPI Read-Only Lab Contract
- Toss OpenAPI Official API Inventory
- Toss OpenAPI Post-Key Read-Only Lab Runbook

<!-- Merged from: docs/codex/toss-openapi-lab.md -->
## Toss OpenAPI Read-Only Lab Contract

## Purpose

This contract defines what can be prepared before Toss Securities OpenAPI keys,
accounts, tokens, or order permissions exist.

Current decision:

- Toss OpenAPI still has a read-only lab lane for docs, probes, and fixtures.
- The only promoted main feature is a public-safe `web-view` current-price
  projection for server-derived top-2 `우선 확인` candidates.
- The promoted path may read local `.env.toss-openapi` and call only the
  allowlisted `prices` market-data endpoint when live opt-in and credentials
  are present.
- No broker execution, order routing, public trading call, account data,
  scheduler, Telegram, admin-gui, or production DB write is approved.

Canonical project boundaries still live in:

- [surface-guide.md]({PROJECT_ROOT}/docs/codex/surface-guide.md)
- [data-governance.md]({PROJECT_ROOT}/docs/codex/data-governance.md)
- [data-governance.md]({PROJECT_ROOT}/docs/codex/data-governance.md)
- [candidate-evidence.md]({PROJECT_ROOT}/docs/codex/candidate-evidence.md)

This document supports those canonical docs. It does not override them.

The full official endpoint and schema inventory is maintained in
[toss-openapi-official-api-inventory.md]({PROJECT_ROOT}/docs/codex/toss-openapi-lab.md).

## Official Source Basis

Use official Toss Securities documents first:

| Source | Role |
| --- | --- |
| <https://developers.tossinvest.com/docs> | Human interactive API reference. |
| <https://developers.tossinvest.com/llms.txt> | Official LLM-readable source-of-truth pointer. |
| <https://openapi.tossinvest.com/openapi-docs/overview.md> | Overview, endpoint groups, auth, rate limits, and errors. |
| <https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md> | Markdown API reference index. |
| <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json> | Canonical OpenAPI document for exact endpoints and schemas. |

Observed official-doc facts as of `2026-07-16` (`1.2.4`, `27` paths, `30`
operations, `72` schemas):

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
| Stock/reference metadata | Future lab candidate | May be compared with KRX/Naver identity data, but must not overwrite source facts by default. |
| Market calendar/exchange rate | Future lab candidate | Reference only; label source/freshness if surfaced later. |
| Ranking/market indicators | Planned bounded Top20 observation; not runtime-approved | `tradingAmount`/`tradingVolume` may provide a separate current market-attention reference. It must not replace report candidates or stock-level KRX flow. |
| Account/balance read-only | Operator-only lab candidate | Never public. No production DB write. No scheduler or Telegram integration. |
| Order history/order info | Operator-only lab candidate at most | Treat as execution-adjacent; keep away from public surfaces. |
| Execution lab | Deferred | Requires separate order-safety, audit, permissions, failure, and rollback contract. |
| Public `web-view` projection | Approved only for top-2 current price | Public-safe source/freshness observation support; never account/order data. |

Toss is not a replacement for the current source ownership model:

- Naver remains the report source of truth.
- KRX remains the stored daily market reference source of truth.
- KRX Data Marketplace remains the investor-flow source.
- Toss may become a separate broker-origin intraday/reference lane only after
  post-key evidence proves permission, freshness, rate-limit behavior, and
  failure behavior.

## Pre-Key Allowed Work

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

## Pre-Key Forbidden Work

Forbidden outside the explicitly promoted top-2 current-price path:

- Reading general `.env` or any non-dedicated secret store for Toss credentials.
- Entering, storing, logging, or committing a real `client_id`,
  `client_secret`, access token, or account id.
- Calling `POST /oauth2/token` except through the promoted read-only
  in-memory token owner after `.env.toss-openapi` live opt-in.
- Calling any Toss `/api/v1/...` runtime endpoint except allowlisted
  market/reference endpoints, currently `prices` for the promoted `web-view`
  top-2 path and `stocks`/`market-calendar-kr` for manual probes.
- Capturing real account, holding, order, conditional-order, buying-power,
  sellable-quantity, or commission data.
- Writing Toss data into production SQLite.
- Registering a standalone Toss scheduler task beyond the approved 20:00 baseline task.
- Sending Toss-derived Telegram messages outside the approved `09:15`/`12:00`/`15:15` market-briefing slots.
- Connecting Toss to `admin-gui` or any scheduler flow other than the approved market-briefing slots and 20:00 baseline task.
- Connecting Toss to public `web-view` beyond the top-2 current-price
  projection described in this contract.
- Implementing order or conditional-order creation, modification,
  cancellation, automatic execution, or routing.
- Implementing public numeric scores, investment grades, buy/sell wording,
  entry/exit levels, target returns, conviction, or execution language.

## Endpoint Classification

| Group | Endpoints | Pre-key classification |
| --- | --- | --- |
| Auth | `POST /oauth2/token` | Document only. No call before keys and explicit approval. |
| Market Data | `GET /api/v1/prices`, `orderbook`, `trades`, `price-limits`, `candles` | `prices` only is allowlisted for top-2 web-view current price. Other market-data endpoints remain lab candidates. |
| Stock Info | `GET /api/v1/stocks`, `GET /api/v1/stocks/{symbol}/warnings` | Future read-only lab allowlist after token review. |
| Market Info | `GET /api/v1/exchange-rate`, `GET /api/v1/market-calendar/KR`, `GET /api/v1/market-calendar/US` | Future read-only lab allowlist after token review. |
| Ranking | `GET /api/v1/rankings` | Documentation only until ranking semantics and source burden are separately reviewed. |
| Market Indicators | `GET /api/v1/market-indicators/prices`, `.../{symbol}/candles`, `.../{symbol}/investor-trading` | Documentation only. Investor trading is aggregate market context, not stock-level KRX flow. |
| Account | `GET /api/v1/accounts` | Operator-only lab candidate. Account id is sensitive operational context. |
| Asset | `GET /api/v1/holdings` | Operator-only lab only. Never public. |
| Order History | `GET /api/v1/orders`, `GET /api/v1/orders/{orderId}` | Execution-adjacent operator-only lab only. |
| Order Info | `GET /api/v1/buying-power`, `sellable-quantity`, `commissions` | Execution-adjacent operator-only lab only. |
| Order | `POST /api/v1/orders`, `modify`, `cancel` | Denylist. Separate execution-lab contract required. |
| Conditional Order / History | `POST`/`DELETE`/`GET /api/v1/conditional-orders...` | Denylist. Automatic execution or execution-adjacent context; separate execution-lab contract required. |

## Surface Contract

| Surface | Allowed now | Later condition |
| --- | --- | --- |
| Default/public `web-view` | Top-2 `우선 확인` current-price projection only. | Server-derived latest-date symbols, GET-only, no arbitrary symbol query, no account/order data, no persistence. |
| Loopback lab `web-view` preview | Superseded by the promoted top-2 projection. | New visual experiments still require separate review before broadening the main path. |
| `admin-gui` | Nothing Toss-connected. | Coarse readiness status only after lab contract and secret redaction are implemented; no token/account display. |
| `operator-review` | Not implemented. | Preferred future surface for raw read-only Toss probe review and response comparison. |
| Telegram | Scheduled market-briefing slots may show up to two server-derived current prices with source and checked time. | No account/order data, arbitrary symbols, numerical score, or trading instruction. |
| Scheduler | The three scheduled market-briefing slots may issue the bounded read-only top-2 quote call; the 20:00 baseline task may persist its separate baseline. | No broad Toss polling, no account/order endpoints, and no current-quote DB persistence. |
| Production DB | Nothing Toss-connected. | No write until schema, source semantics, replay, retention, and privacy are reviewed. |

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
- The only live allowlisted operations are `getStocks`,
  `getKrMarketCalendar`, and `getPrices`.
- Live use requires local credentials, env opt-in, `--live`, and
  `--confirm-token-reissue`.
- Account, asset, order-info/history, and order operations remain absent.
- The only default/public `web-view` Toss route is the top-2 current-price
  projection. It uses server-derived candidate symbols, latest stored date
  only, in-memory token/cache, and no DB writes.
- No Toss value is connected to `admin-gui`, Telegram, scheduler, or
  production DB.
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
- The only public `web-view` connection is the approved top-2 current-price
  projection with no account/order data and no arbitrary symbol query.


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
| Snapshot date | `2026-07-16` |
| Official spec version | `1.2.4` |
| OpenAPI document version | `3.1.0` |
| Base server | `https://openapi.tossinvest.com` |
| Paths | 27 |
| Operations | 30 |
| Schema count | 72 |
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
| Public surface | Auth/account/order values may not reach `web-view`; only bounded top-2 market price projection is approved. | Enforce through tests before any surface connection. |

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
| Market Data | `GET` | `/api/v1/prices` | `getPrices` | No | `symbols`, max 200 comma-separated | `MARKET_DATA` | Future read-only lab allowlist. |
| Market Data | `GET` | `/api/v1/orderbook` | `getOrderbook` | No | `symbol` | `MARKET_DATA` | Future read-only lab allowlist, top-2 only. |
| Market Data | `GET` | `/api/v1/trades` | `getTrades` | No | `symbol`, optional `count` max 50 | `MARKET_DATA` | Future read-only lab allowlist, top-2 only. |
| Market Data | `GET` | `/api/v1/price-limits` | `getPriceLimit` | No | `symbol` | `MARKET_DATA` | Future read-only lab allowlist. |
| Market Data | `GET` | `/api/v1/candles` | `getCandles` | No | `symbol`, `interval=1m|1d`, `count` max 200, `before`, `adjusted` | `MARKET_DATA_CHART` | Future lab only; no broad backfill. |
| Stock Info | `GET` | `/api/v1/stocks` | `getStocks` | No | `symbols`, max 200 comma-separated | `STOCK` | Future reference allowlist. |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/warnings` | `getStockWarnings` | No | path `symbol` | `STOCK` | Future caution/reference allowlist. |
| Market Info | `GET` | `/api/v1/exchange-rate` | `getExchangeRate` | No | `baseCurrency`, `quoteCurrency`, optional `dateTime` | `MARKET_INFO` | Future reference only; not order FX. |
| Market Info | `GET` | `/api/v1/market-calendar/KR` | `getKrMarketCalendar` | No | optional `date` | `MARKET_INFO` | Future calendar comparison candidate. |
| Market Info | `GET` | `/api/v1/market-calendar/US` | `getUsMarketCalendar` | No | optional `date` | `MARKET_INFO` | Future only if US scope is approved. |
| Ranking | `GET` | `/api/v1/rankings` | `getRankings` | No | `type`, `marketCountry`, `duration`, optional caution exclusion/count | `RANKING` | Documentation only. Ranking basis must not overwrite candidate priority. |
| Market Indicators | `GET` | `/api/v1/market-indicators/prices` | `getMarketIndicatorPrices` | No | `symbols` | `MARKET_INDICATOR` | Future market-context lab only. |
| Market Indicators | `GET` | `/api/v1/market-indicators/{symbol}/candles` | `getMarketIndicatorCandles` | No | path `symbol`, `interval`, `count`, optional `before` | `MARKET_INDICATOR_CHART` | Future market-context lab only; no broad backfill. |
| Market Indicators | `GET` | `/api/v1/market-indicators/{symbol}/investor-trading` | `getMarketIndicatorInvestorTrading` | No | path `symbol`, `interval`, `count`, optional `until` | `MARKET_INDICATOR` | Future aggregate KOSPI/KOSDAQ context only; not a replacement for stock-level KRX flow. |
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
| `docs_only` | Full endpoint and schema inventory | All runtime calls | Current default. |
| `market_reference_lab` | `prices`, `stocks`, `stock warnings`, `market-calendar/KR`, maybe `trades` for freshness | Account, holdings, order info/history, order POST | Candidate after keys and approval. |
| `operator_account_lab` | `accounts`, maybe `holdings` with redaction | Public surfaces, DB write, Telegram, scheduler, order POST | Not approved now. |
| `execution_review_lab` | Order docs, order fixture schemas, safety tests | Real order create/modify/cancel | Separate contract required. |
| `public_projection` | Source/freshness labels and current prices for server-derived top-2 observation candidates | Account, holdings, orders, buying power, sellable quantity, commissions, score/trading call, arbitrary public symbols | Approved only for bounded `web-view` top-2 current-price projection. |

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
  bounded implementation still allows only `stocks`, `market-calendar/KR`, and
  `prices`; no new operation was promoted.
- The `2026-07-16` `1.2.4` recheck kept all `30` documented
  method/path/operationId entries and the `72` schema count unchanged.


<!-- Merged from: docs/codex/toss-openapi-lab.md -->
## Toss OpenAPI Post-Key Read-Only Lab Runbook

## Purpose

This runbook covers the first bounded Toss Securities OpenAPI validation after
client credentials have been issued.

It does not approve account, asset, order-info, order-history, conditional-order
history, order or conditional-order creation/modification/cancellation,
production DB writes, scheduler, Telegram, `admin-gui`, or any `web-view`
integration in main.

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

Verified on `2026-07-16` against:

- <https://developers.tossinvest.com/docs>
- <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json>

Current official spec snapshot:

| Item | Value |
| --- | --- |
| OpenAPI document version | `3.1.0` |
| Official spec version | `1.2.4` |
| Paths | `27` |
| Operations | `30` |
| Schemas | `72` |

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

Run only after reviewing the plan and local `.env.toss-openapi` fields:

```powershell
python -m stock_monitor toss-openapi-readonly-probe --endpoint stocks --symbol 005930 --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint market-calendar-kr --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint prices --symbol 005930 --live --confirm-token-reissue --json
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

## Planned Top20 Market-Attention Contract

`GET /api/v1/rankings` is not promoted by this document. The planned first use is a fixed 15:00 KST, read-only Top20 observation carrying only rank, stock code, trading amount, trading volume, source, and checked time. It supports report/news/Top20 overlap display, not candidate selection, scoring, stock-level investor-flow claims, account access, or broad polling.

No database write, scheduler registration, Telegram send, or public route is approved for this contract yet. Add persistent replay only after a separate schema, retention, replay, and public-boundary review. The unmerged `codex/toss-openapi` branch is reference material, not approval to widen the runtime allowlist.

## Promoted Web-View Priority Quote Projection

The former lab preview was promoted to the main GET-only `web-view` in a
bounded form.

The normal `web-view` command can show Toss current-price references directly
in the existing top-two `?곗꽑 ?뺤씤` rows when `.env.toss-openapi` has
credentials and `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`:

```powershell
python -m stock_monitor web-view --host 127.0.0.1 --port 8792 --no-open
```

- No extra Toss-specific CLI flag is required; `.env.toss-openapi` is the opt-in boundary.
- Uses the existing `web-view` host/access boundary plus server-derived
  top-2 symbols; it does not accept arbitrary public symbols.
- Adds the reference only to priority rows on the web-view.
- Fetches current prices only for the latest stored business date's top-two
  six-digit Korean stock codes. Historical dates do not call Toss.
- Recomputes and verifies the latest stored date's top-two priority codes on
  the server before calling Toss; arbitrary symbols are rejected.
- Fetches only when priority rows load or the operator manually refreshes them.
- Issues one memory-only token lazily on the first quote request. A `401`
  response permits one token reissue and one repeated GET for the server
  lifetime; no provider-specific error-code spelling or other automatic retry
  loop is assumed.
- Merges concurrent identical date/symbol requests so they produce one
  MARKET_DATA call.
- Reuses the same date/symbol response for 30 seconds. When Toss is
  unavailable, a successful response no older than 5 minutes may be returned
  with `cache=stale` and `stale_reason=upstream_unavailable`.
- Labels the value as `Toss ?꾩옱媛`; it is not the selected historical date's price.
- Reuses the existing `?곗씠??湲곗?` section to show `ready/current/disabled` and cache
  state after a successful quote response; it does not add a separate Toss screen.
- The normal `web-view` command exposes only the bounded top-2 quote reference route.
- Exposes no account, order, DB write, scheduler, Telegram, or admin control.
- It is public-safe only as current-price reference beside server-derived priority candidates.

## Verification Commands

```powershell
python -m pytest tests/test_toss_openapi.py tests/test_config.py -q
python -m pytest tests/test_cli_commands.py -q -k "data_source_lane_audit or toss_openapi_readonly_probe"
python -m pytest tests/test_web_view.py -q -k "toss_priority or toss_ready"
python -m stock_monitor data-source-lane-audit --json
```
