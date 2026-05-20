# ETF / Flow Source Study

## Purpose

This note fixes the first source-study baseline for ETF and flow data.
It is not an ingest implementation plan yet.

The goal is to support the read-only `web-view` with separate evidence layers:

- report activity: already collected from Naver research
- ETF reference: market/theme/index context
- flow/supply-demand: volume, turnover, foreign/institution/individual direction

Do not merge ETF or flow data into `reports` or `daily_stock_summaries`.
They should stay as separate datasets and be joined only in read-only query/view models.

## Source Decision

| Layer | First candidate | Status | Reason |
| --- | --- | --- | --- |
| ETF daily reference | KRX Open API `ETF 일별매매정보` | Preferred first source | Official KRX source, EOD-oriented, separate from company reports. |
| Stock daily price/volume/turnover | KRX Open API `유가증권 일별매매정보`, `코스닥 일별매매정보` | Preferred first source | Official daily market data available by market. |
| Stock investor flow | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Preferred validation source | Official KRX screen source for stock-level investor buy/sell/net-buy by investor type; request contract still needs tracing. |
| Market investor flow | KRX Data Marketplace `[12008] 투자자별 거래실적` | P1 validation source | Market-wide background for whether the day was foreign-led, institution-led, or individual-led. |
| Investor net-buy ranking | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | P1 validation source | Discovery/reference list for names receiving strong investor-category net buying. |
| KIS Developers investor flow | KIS Developers domestic stock market-analysis APIs | Deferred fallback | Use if KRX Data Marketplace proves unsuitable or unstable; requires KIS app credentials and token handling. |
| Current price / sector already used today | Naver stock detail API | Keep as existing tactical source | Already integrated for current price and sector metadata, but treat as unofficial and not the core flow source. |
| Historical helper libraries | `pykrx-openapi`, other wrappers | Optional helper only | Can reduce implementation work later, but should not become the source contract before official endpoint behavior is verified. |

Practical v1 recommendation:

1. Use KRX Open API first for ETF daily snapshots and stock daily market snapshots. This is implemented for the approved daily stock/ETF/index endpoints and currently used as read-only market reference data.
2. Validate KRX Data Marketplace `[12009]` first for investor flow, then `[12008]` and `[12010]` for background/ranking.
3. Do not add scoring, grade, or third-day alerts until at least several weeks of joined report/flow examples are reviewed.

## Why KRX First

KRX is the cleanest first source for after-market review because the planned view is not a trading bot.
The project needs end-of-day context more than real-time execution:

- ETF code/name, close, change, volume, turnover
- stock close, volume, turnover
- date-bound market snapshots that align with Korean business dates

KRX Open API requires membership, an authentication key request, and service usage approval.
The operator requested issuance up to the P2 scope on 2026-05-08.
That is acceptable for a later implementation step, but it means ingest code should not be started until the exact approved API products, endpoint IDs, response fields, and one-date samples are confirmed.

## Why KRX Data Marketplace Is Now The First Flow Candidate

The approved KRX Open API specs do not include investor-category flow fields, but the logged-in KRX Data Marketplace screen exposes the needed investor-flow tables.

Confirmed screens are tracked in [krx-investor-flow-source-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-investor-flow-source-plan.md):

| Screen | Use |
| --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Core stock-level flow for report-related stocks. |
| `[12008] 투자자별 거래실적` | Market-wide background flow. |
| `[12010] 투자자별 순매수상위종목` | Top net-buy reference/discovery list. |

This should be validated before KIS because it keeps the first flow source in the KRX ecosystem and avoids extra credential/token handling.

## Why KIS Is Deferred But Important

KIS Developers exposes many domestic stock APIs, including ETF/ETN current price, ETF constituent price, stock investor trend, market investor trend, and real-time APIs.
This is attractive for flow and possibly richer ETF details.

The tradeoff is operational complexity:

- app key / app secret / token handling
- per-endpoint permissions and terms
- possible account linkage
- rate limits and token refresh
- more sensitive local `.env` handling

Therefore, KIS should be treated as a fallback source track:

- use it if KRX Data Marketplace cannot provide stable request/response behavior
- keep credentials out of admin GUI editing
- store only derived daily snapshots, not raw credentials or account data

## Minimum Data Model

These are planning shapes, not committed migrations.

```text
etf_metadata(
  etf_code,
  etf_name,
  provider,
  reference_index,
  category,
  source,
  updated_at
)

etf_daily_snapshots(
  business_date,
  etf_code,
  close_price,
  change_percent,
  volume,
  turnover,
  nav,
  fetched_at,
  source,
  primary key (business_date, etf_code, source)
)

stock_market_daily(
  business_date,
  stock_code,
  close_price,
  change_percent,
  volume,
  turnover,
  market,
  fetched_at,
  source,
  primary key (business_date, stock_code, source)
)

stock_flow_daily(
  business_date,
  stock_code,
  individual_net,
  foreign_net,
  institution_net,
  volume,
  turnover,
  fetched_at,
  source,
  primary key (business_date, stock_code, source)
)
```

Actual KRX Data Marketplace flow migrations should use the more explicit candidate shapes in [krx-investor-flow-source-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-investor-flow-source-plan.md), including separate stock-level, market-level, and top-net-buy tables.

Keep `stock_market_daily` and investor-flow tables separate at first.
Some sources may provide price/volume without investor categories, while others may provide investor trend without the preferred close/turnover fields.

## Read-Only Web-View Use

Initial user-facing output should be descriptive:

| View | First output |
| --- | --- |
| Daily review | Reported stocks plus close/change/volume/turnover when available. |
| Flow snapshot | For report-related stocks, show foreign/institution/individual net direction from `[12009]` if the source is available. |
| Sector/theme rotation | Show report activity and flow direction side by side, explicitly as separate evidence. |
| ETF reference | ETF code/name, category/index, close/change, volume/turnover. |

Avoid phrases that imply certainty, such as `주도 섹터 확정`, until the source and history are strong enough.
Use wording like:

- `리포트 집중`
- `수급 동반`
- `거래대금 증가`
- `후속 확인 필요`

## Implementation Sequence

| Step | Work | Output |
| --- | --- | --- |
| 1 | Confirm approved KRX API products and response fields | Field contract note with sample response saved under docs. |
| 1A | Trace KRX Data Marketplace `[12009]` request contract | Endpoint, params, unit behavior, response root, and one masked/local sample. |
| 2 | Add config placeholders only after source choice | `.env.example` entries for API key names, no real secrets. |
| 3 | Add DB migrations for daily snapshots | New ETF/market/flow tables with idempotent upsert rules. |
| 4 | Add manual dry-run CLI | Fetch one date or one stock/date without changing Telegram behavior. |
| 5 | Add read-only repository queries | Date-bound joins against report summaries. |
| 6 | Add web-view cards/tables | Display only; no alert/scoring. |
| 7 | Review several weeks of data | Decide whether third-day interest alert or scoring is justified. |

## Risks And Guardrails

| Risk | Guardrail |
| --- | --- |
| Official API approval or field availability differs from docs | Start with manual field validation before schema migration. |
| KRX Data Marketplace request contract changes | Keep `source='krx_data_market'`, isolate fetch code, and add dry-run/smoke tests before scheduled ingestion. |
| KIS credentials increase secret-management burden | Keep credentials in `.env`, never in admin GUI or Telegram. |
| ETF data shape differs from company report data | Store in separate ETF tables and expose through separate views. |
| Investor flow categories can be interpreted too aggressively | Show raw direction and amounts first; no scoring until reviewed. |
| Naver unofficial endpoints can drift | Do not make them the only source for flow/ETF. |
| EOD timing may lag around close | Store `fetched_at` and display source/timestamp in admin/web-view. |

## Current Recommendation

For the next implementation batch, do not build a full ingest yet.
Do a narrow source validation batch:

1. fill `data/krx_api_intake.local.md` with non-secret approved-service details
2. keep the real `AUTH_KEY` only in local `.env`
3. capture one ETF daily response and one KOSPI/KOSDAQ daily response
4. trace KRX Data Marketplace `[12009]`, then `[12008]` and `[12010]`
5. only then add migrations and a manual `fetch-market-daily` style CLI

The field-validation checklist is tracked separately in [krx-api-field-validation.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/details/krx/krx-api-field-validation.md).
