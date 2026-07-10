# Toss OpenAPI Read-Only Lab Contract

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

- [surface-contract.md]({PROJECT_ROOT}/docs/codex/surface-contract.md)
- [data-source-policy.md]({PROJECT_ROOT}/docs/codex/data-source-policy.md)
- [data-quality-checklist.md]({PROJECT_ROOT}/docs/codex/data-quality-checklist.md)
- [candidate-evidence-contract.md]({PROJECT_ROOT}/docs/codex/contracts/candidate-evidence-contract.md)

This document supports those canonical docs. It does not override them.

The full official endpoint and schema inventory is maintained in
[toss-openapi-official-api-inventory.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-official-api-inventory.md).

## Official Source Basis

Use official Toss Securities documents first:

| Source | Role |
| --- | --- |
| <https://developers.tossinvest.com/docs> | Human interactive API reference. |
| <https://developers.tossinvest.com/llms.txt> | Official LLM-readable source-of-truth pointer. |
| <https://openapi.tossinvest.com/openapi-docs/overview.md> | Overview, endpoint groups, auth, rate limits, and errors. |
| <https://openapi.tossinvest.com/openapi-docs/latest/api-reference/README.md> | Markdown API reference index. |
| <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json> | Canonical OpenAPI document for exact endpoints and schemas. |

Observed official-doc facts as of `2026-07-10` (`1.2.2`, `27` paths, `30`
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
| Ranking/market indicators | Documentation only | Ranking basis and index-level investor trading do not match current candidate or stock-level KRX-flow semantics. |
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
  [toss-openapi-postkey-readonly-lab-runbook.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-postkey-readonly-lab-runbook.md).

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
