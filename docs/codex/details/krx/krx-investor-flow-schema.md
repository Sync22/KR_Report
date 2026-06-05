# KRX Investor Flow Schema

## Purpose

This document fixes the SQLite storage contract for KRX Data Marketplace investor-flow data.

The schema is ready as additive migration v4, and Stage 4 raw/visible validation is complete for two business dates.
Scheduled ingest is still disabled until separate approval.

## Source Boundary

| Table | Source | Intended Use |
| --- | --- | --- |
| `stock_investor_flow_daily` | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Leadership-candidate stock/date flow context. |
| `market_investor_flow_daily` | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide background by investor type. |
| `investor_net_buy_top_daily` | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Discovery/ranking reference by market and investor type. |

These rows must stay separate from Naver research `reports`, `daily_stock_summaries`, and KRX Open API daily snapshot tables.

## Table Contract

| Table | Primary Key | Required Identity Fields | Numeric Fields |
| --- | --- | --- | --- |
| `stock_investor_flow_daily` | `business_date, stock_code, investor_type, source` | `business_date`, 6-digit `stock_code`, `investor_type`, `source`, `fetched_at` | sell/buy/net-buy volume and amount fields. |
| `market_investor_flow_daily` | `business_date, market, investor_type, source` | `business_date`, `market`, `investor_type`, `source`, `fetched_at` | sell/buy/net-buy volume and amount fields. |
| `investor_net_buy_top_daily` | `business_date, market, investor_type, rank, source` | `business_date`, `market`, `investor_type`, positive `rank`, 6-digit `stock_code`, `stock_name`, `source`, `fetched_at` | net-buy volume and amount fields. |

## Unit Policy

- Store source units explicitly in `volume_unit` and `amount_unit` for `[12008]` and `[12009]`.
- Do not guess or auto-scale units during sample validation.
- `N/A`, empty strings, and dash-like missing markers become `NULL` numeric values.
- Missing numeric values must not be treated as zero.

## DB Verify Gate

`python -m stock_monitor db-verify` now fails if any of these investor-flow quality issues are present:

| Check | Meaning |
| --- | --- |
| `stock_invalid_code` | `[12009]` row has a non-6-digit stock code. |
| `stock_missing_units` | `[12009]` row is missing `volume_unit` or `amount_unit`. |
| `stock_no_numeric_flow` | `[12009]` row has no numeric volume or amount values. |
| `market_missing_units` | `[12008]` row is missing `volume_unit` or `amount_unit`. |
| `market_no_numeric_flow` | `[12008]` row has no numeric volume or amount values. |
| `top_invalid_rank` | `[12010]` row has rank less than 1. |
| `top_invalid_code` | `[12010]` row has a non-6-digit stock code. |
| `top_no_net_buy` | `[12010]` row has neither net-buy volume nor net-buy amount. |

This makes bad rows visible before they affect web-view cards or future analysis.

## Promotion Conditions

Scheduled investor-flow ingest remains blocked until all conditions are met:

1. Raw endpoint samples for `[12008]`, `[12009]`, and `[12010]` are captured.
2. Sample manifests preserve screen/date/filter/unit conditions.
3. `krx-flow-dry-run --strict-sample` passes on representative samples.
4. `db-verify` passes after test inserts into a non-production database.
5. Ingest scope remains bounded to leadership candidates, market background, and top rankings.

Manual local sample import is allowed only through:

```powershell
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

This path refuses warning samples and writes only parsed local raw samples. It does not call KRX, does not log in, and does not enable scheduled collection.

## Operational Rule

Investor flow is a reference signal only. It may support observation-candidate ordering, but do not label it as a trading recommendation, public numeric score, or confirmed sector rotation until enough history and explicit rules exist.
