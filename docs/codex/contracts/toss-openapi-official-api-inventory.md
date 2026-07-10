# Toss OpenAPI Official API Inventory

## Purpose

This is the local memory note for the official Toss Securities OpenAPI surface.

It records the full official API shape before any key, account, token, runtime
probe, or production integration exists. The intent is broad preparation first,
then later pruning through reviewed patches.

This is not an approval to call Toss runtime APIs. The active safety contract is
[toss-openapi-readonly-lab-contract.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-readonly-lab-contract.md).

## Snapshot

| Item | Value |
| --- | --- |
| Snapshot date | `2026-07-10` |
| Official spec version | `1.2.2` |
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
| Public surface | Auth/account/order values may not reach `web-view`; bounded top-2 prices plus fixed ranking/aggregate-flow market context are approved. | Enforce source, freshness, fixed-query, and public-safe DTO tests before any surface connection. |

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
| Ranking | `GET` | `/api/v1/rankings` | `getRankings` | No | `type`, `marketCountry`, `duration`, optional caution exclusion/count | `RANKING` | Promoted only as fixed KR real-time market-trading-amount Top20. It may show Top2 overlap but cannot reorder candidates. |
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
| `public_projection` | Source/freshness labels, current prices for server-derived top-2 candidates, and fixed market-context ranking/aggregate flow | Account, holdings, orders, buying power, sellable quantity, commissions, score/trading call, arbitrary public queries | Approved only for bounded latest-date `web-view` top-2 current-price and fixed market-context projections. |

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
