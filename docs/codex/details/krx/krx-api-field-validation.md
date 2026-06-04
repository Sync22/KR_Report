# KRX API Field Validation

## Purpose

This document tracks the post-approval validation step before KRX data is added to code or SQLite tables.
It is intentionally a field-contract document, not an ingest implementation.

## Current Status

| Item | Status | Note |
| --- | --- | --- |
| KRX Open API account/service request | In progress | Operator requested issuance up to the P2 scope on 2026-05-08. |
| Real `AUTH_KEY` storage | Locally configured | Store only in local `.env` as `STOCK_MONITOR_KRX_AUTH_KEY`; do not print or copy into docs. |
| Approved service detail capture | Done | 8 provided docx specs were parsed into `data/krx_api_intake.local.md`. |
| One-date sample response capture | Done | 8 provided endpoints responded successfully for `basDd=20260507`; first-row samples are saved in `data/krx_api_dry_run_samples.local.json`. |
| DB migration | Done | Migration v2 added KRX stock/ETF/metadata/index snapshot tables. |
| Repeatable dry-run CLI | Done | `python -m stock_monitor krx-dry-run <endpoint|all> --date YYYY-MM-DD` prints row counts and fields without saving. |
| Manual ingest/upsert | First pass done | `python -m stock_monitor krx-fetch-snapshot <endpoint|all> --date YYYY-MM-DD` parses and upserts KRX snapshots. |
| Read/query methods | First pass done | `krx-query-snapshot` can read stored stock, ETF, and index snapshots by date. |
| Admin display | First pass done | `operator-status` and `admin-gui` expose latest KRX KOSPI/KOSDAQ/ETF/index snapshot tables from stored data. |
| KRX Data Marketplace investor-flow screen check | Screen validated | Logged-in `data.krx.co.kr` screen confirms `[12008]`, `[12009]`, and `[12010]`; request contract still needs tracing before code. |
| Data Marketplace dry-run CLI | First pass done | `krx-flow-dry-run` can call `[12009]` candidate requests without DB writes after `isuCd` is provided or resolved from stored KRX metadata. |

## Local Intake File

Use:

- `data/krx_api_intake.local.md`

That file is under `data/`, so it is intentionally local-only.
It now contains the parsed endpoint URLs and response fields from `data/API_Specification/*.docx`.
It can also contain masked real sample responses later.

Do not store the real `AUTH_KEY` in documentation.
Use `.env` only:

```env
STOCK_MONITOR_KRX_AUTH_KEY=
STOCK_MONITOR_KRX_BASE_URL={KRX_OPENAPI_BASE_URL}
STOCK_MONITOR_KRX_DATA_MARKET_BASE_URL={KRX_DATA_MARKET_BASE_URL}
STOCK_MONITOR_KRX_DATA_MARKET_ID=
STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD=
STOCK_MONITOR_KRX_TIMEOUT_SECONDS=30
```

## Required First-Pass Services

| Priority | Service | Why Needed | Expected Project Layer |
| --- | --- | --- | --- |
| P1 | 유가증권 일별매매정보 | KOSPI stock close, volume, turnover, market-cap context | `stock_market_daily` candidate |
| P1 | 코스닥 일별매매정보 | KOSDAQ stock close, volume, turnover, market-cap context | `stock_market_daily` candidate |
| P1 | ETF 일별매매정보 | ETF close, NAV, volume, turnover context | `etf_daily_snapshots` candidate |
| P2 | 종목기본정보 | Code/name/market metadata verification and code mapping | `stock_metadata` enrichment candidate |
| P2 | 지수 일별매매정보 | Market/index context for after-market web-view | `market_index_daily` candidate |
| P0 | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Report-stock foreign/institution/individual flow | `stock_investor_flow_daily` candidate; not part of approved Open API specs |
| P1 | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide investor background | `market_investor_flow_daily` candidate; not part of approved Open API specs |
| P1 | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Investor-category top net-buy names | `investor_net_buy_top_daily` candidate; not part of approved Open API specs |

## KRX Data Marketplace Request Candidates

These are not approved Open API endpoints.
They are candidate screen-backed request contracts that still need a dry-run validation step before DB migrations.

| Screen | Candidate BLD | Candidate params | Validation status |
| --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | `dbms/MDC/STAT/standard/MDCSTAT02201` | `strtDd`, `endDd`, `mktId`, `etf`, `etn`, `elw` | Candidate only. |
| `[12009] 투자자별 거래실적(개별종목)` 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02301` | `strtDd`, `endDd`, `isuCd` | Candidate only; `isuCd` mapping required. |
| `[12009] 투자자별 거래실적(개별종목)` 일별추이 | `dbms/MDC/STAT/standard/MDCSTAT02302` | `strtDd`, `endDd`, `isuCd`, `trdVolVal`, `askBid` | Candidate only; use after period aggregate works. |
| `[12010] 투자자별 순매수상위종목` | `dbms/MDC/STAT/standard/MDCSTAT02401` | `strtDd`, `endDd`, `mktId`, `invstTpCd` | Candidate only. |

Dry-run acceptance requirements:

1. Print the screen number, BLD, full non-secret params, source unit labels, raw row count, and normalized row preview.
2. Confirm how 6-digit `stock_code` maps to `[12009]` `isuCd`.
3. Save no cookies, browser session tokens, or login state into the project.
4. Keep result rows out of production DB until units, investor labels, and duplicate keys are stable.

Current dry-run commands:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view market --date YYYY-MM-DD --market STK --value amount --side net-buy --show-first-row
python -m stock_monitor krx-flow-dry-run --view top --date YYYY-MM-DD --market STK --investor foreign --show-first-row
```

If stored KRX metadata is missing, fetch approved basic metadata first or pass `--isu-cd` explicitly for one-off validation.
Before live Data Marketplace calls, use `krx-flow-login-check --date YYYY-MM-DD --market STK` to verify local `.env` raw login and the representative `[12008]` endpoint without DB writes.
If the response body is `LOGOUT`, treat it as an authentication failure and do not write DB rows.

## Field Capture Requirements

For every approved endpoint, capture:

- service name
- API ID
- request URL
- method and content type
- required parameters
- date parameter name and date format
- paging or row-limit behavior
- response root path
- response success/error shape
- full output field list
- one small masked sample response

## Minimum Field Mapping To Confirm

### Stock Daily Market Data

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Must align to Korean trading date. |
| `stock_code` | Yes | Prefer 6-digit code. |
| `stock_name` | Yes | Useful for validation, not primary key. |
| `market` | Yes | KOSPI/KOSDAQ separation. |
| `close_price` | Yes | Required for web-view context. |
| `change_amount` | Optional | Useful display field. |
| `change_percent` | Yes | Required for strong/weak list. |
| `open_price` | Optional | Useful later. |
| `high_price` | Optional | Useful later. |
| `low_price` | Optional | Useful later. |
| `volume` | Yes | Required for attention/flow context. |
| `turnover` | Yes | Required for trading-value context. |
| `market_cap` | Optional | Useful for ranking normalization. |

### ETF Daily Data

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Trading date. |
| `etf_code` | Yes | ETF identifier. |
| `etf_name` | Yes | Display/search. |
| `close_price` | Yes | Display. |
| `change_amount` | Optional | Display. |
| `change_percent` | Yes | Ranking/context. |
| `nav` | Yes if available | ETF-specific value. |
| `volume` | Yes | Liquidity context. |
| `turnover` | Yes | Trading-value context. |
| `aum_or_net_assets` | Optional | Useful for ETF scale. |
| `underlying_index` | Optional | May come from metadata rather than daily data. |

### Investor Flow Data

The approved KRX Open API specs do not expose it, but KRX Data Marketplace screens do.
Use [krx-investor-flow-source-plan.md](/docs/codex/details/krx/krx-investor-flow-source-plan.md) as the source-boundary document.

| Project field | Needed | Notes |
| --- | --- | --- |
| `business_date` | Yes | Trading date. |
| `stock_code` | Yes | Join key. |
| `individual_net` | Yes | Individual net buy/sell. |
| `foreign_net` | Yes | Foreign net buy/sell. |
| `institution_net` | Yes | Institution net buy/sell. |
| `source_unit` | Yes | Shares, KRW, or other unit must be explicit. |

Confirmed Data Marketplace screen columns for `[12009]` include investor type, sell/buy/net-buy volume, and sell/buy/net-buy trading amount.
The screen allows unit choices for shares and money, so the ingest contract must persist the chosen units.

## Validation Output

After the local intake file is filled and one-date API calls are validated, the next Codex task should produce:

1. confirmed endpoint list
2. accepted/rejected field mapping table
3. missing fields and fallback source recommendation
4. proposed DB table list, still without applying migrations
5. proposed manual dry-run CLI contract

## Parsed Spec Summary

| Service | Endpoint | Priority | First use |
| --- | --- | --- | --- |
| ETF 일별매매정보 | `/svc/apis/etp/etf_bydd_trd` | P1 | ETF daily snapshot |
| 유가증권 일별매매정보 | `/svc/apis/sto/stk_bydd_trd` | P1 | KOSPI stock daily market data |
| 코스닥 일별매매정보 | `/svc/apis/sto/ksq_bydd_trd` | P1 | KOSDAQ stock daily market data |
| 유가증권 종목기본정보 | `/svc/apis/sto/stk_isu_base_info` | P2 | KOSPI stock metadata |
| 코스닥 종목기본정보 | `/svc/apis/sto/ksq_isu_base_info` | P2 | KOSDAQ stock metadata |
| KRX 시리즈 일별시세정보 | `/svc/apis/idx/krx_dd_trd` | P2 | Market index context |
| KOSPI 시리즈 일별시세정보 | `/svc/apis/idx/kospi_dd_trd` | P2 | KOSPI index context |
| KOSDAQ 시리즈 일별시세정보 | `/svc/apis/idx/kosdaq_dd_trd` | P2 | KOSDAQ index context |

Dry-run result:

Sample file: `data/krx_api_dry_run_samples.local.json`

| Service | Rows | Status |
| --- | ---: | --- |
| ETF 일별매매정보 | 1099 | OK |
| 유가증권 일별매매정보 | 948 | OK |
| 코스닥 일별매매정보 | 1822 | OK |
| 유가증권 종목기본정보 | 948 | OK |
| 코스닥 종목기본정보 | 1822 | OK |
| KRX 시리즈 일별시세정보 | 34 | OK |
| KOSPI 시리즈 일별시세정보 | 51 | OK |
| KOSDAQ 시리즈 일별시세정보 | 40 | OK |

Resolved validation points:

- auth placement is request header field `AUTH_KEY`
- HTTP method is `POST`
- body is JSON with `basDd`
- response root is `OutBlock_1`

Open validation questions:

- daily stock `ISU_CD` must be checked to confirm whether it is the 6-digit join key
- KOSPI daily `ISU_CD` validation kept 923 of 948 rows for `2026-05-07`; non-6-digit rows are skipped until their instrument class is reviewed
- investor-category flow is not covered by the provided KRX Open API specs
- KRX Data Marketplace `[12009]`, `[12008]`, and `[12010]` request endpoint/params/response roots are Stage 4 validated for two business dates
- Scheduled ingestion is still disabled until separate approval

## Guardrails

- Do not paste real API keys into chat, docs, screenshots, or Telegram.
- Do not enable broad scheduled Data Marketplace ingest until separate approval. The only current automatic exception is `StockMonitor-KrxMentionedFlowBackfill`, limited to same-day report-mentioned stocks and `[12009]` stock-level rows.
- Do not mix ETF rows into company report tables.
- Do not infer investor flow from report count.
- Keep KRX daily market snapshots separate from current Naver quote lookups.
