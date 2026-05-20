# KRX 18-Month Backfill Analysis

## Purpose

This document tracks the current 18-month KRX historical baseline work.

The goal is not to enable scoring, recommendations, or automated KRX Data Marketplace ingest. The goal is to build enough stored KRX market context for observation and future backtest work while keeping collection lanes, request volume, and DB safety explicit.

## Current Decision

| Lane | Use | Decision | Reason |
| --- | --- | --- | --- |
| KRX OpenAPI | Stock/ETF/index daily price, volume, turnover snapshots | Primary 18-month backfill lane | Approved API source, stable request shape, no browser session dependency. |
| KRX Data Marketplace | Investor flow `[12008]`, `[12009]`, `[12010]` | Manual/raw-login lane; broad scheduled ingest disabled; narrow `[12009]` same-day mentioned-stock 31-day backfill is the only automatic exception | Useful for flow reference, but login/session-dependent and higher operational risk. |
| Botasaurus/browser probe | Browser-gated source/session diagnostics | Probe only | Use only when Data Marketplace login/session/selectors or blocking behavior needs validation. |
| Naver report collector | Research reports | Keep separate | Report source remains Naver; do not use KRX for report history. |

## Skill And Agent Comparison

| Tool/agent | Best use | Not for | Current P2 decision |
| --- | --- | --- | --- |
| `botasaurus-stock-monitor` skill | Short-lived browser-gated KRX/Data Marketplace probes, session/blocking diagnostics | Main Naver collector, Telegram, SQLite operation, KRX OpenAPI daily snapshots | Available but not used for stock/ETF/index backfill. |
| `market-data-engineer` | KRX/KIS/ETF/flow source fields, request limits, source-boundary decisions | UI polish or scheduler recovery implementation | Used for lane comparison and backfill limit review. |
| `sql-pro` | DB retention, backup, row growth, migration/cleanup risk | Source semantics or browser probing | Used for 18-month DB safety and retention review. |
| `reviewer` | Business-day rules, stale docs, regression risk | Bulk data collection | Used for holiday expansion and documentation drift review. |

## Backfill Policy

| Rule | Value |
| --- | --- |
| Scope | KRX OpenAPI stock/ETF/index daily snapshots only |
| Lookback | `550` days |
| Live batch size | `5` business dates |
| Delay | `3` seconds between endpoint requests |
| Backup | Before broad work and every 10 business dates or major boundary |
| Verify | `db-verify` after each live batch |
| Cleanup retention | `550` days while observation/backtest work is active |
| Partial endpoint guard | Very small nonzero endpoint row counts are treated as incomplete and re-planned for repair |
| Holiday guard | Built-in `2024~2026` KRX closure dates plus `STOCK_MONITOR_HOLIDAYS` additions |

## Current Stored Coverage

As of the latest verified baseline check:

| Table group | Range | Business dates | Rows |
| --- | --- | ---: | ---: |
| `reports` | `2026-01-02` ~ `2026-05-15` | 90 | 4,046 |
| `daily_stock_summaries` | `2026-01-02` ~ `2026-05-15` | 90 | 2,570 |
| `stock_market_daily` | `2024-11-08` ~ `2026-05-14` | 367 | 999,768 |
| `etf_daily_snapshots` | `2024-11-08` ~ `2026-05-14` | 367 | 331,347 |
| `market_index_daily` | `2024-11-08` ~ `2026-05-14` | 367 | 45,875 |
| `stock_investor_flow_daily` | `2026-01-05` ~ `2026-05-12` | 75 | 9,724 |
| `market_investor_flow_daily` | `2026-01-02` ~ `2026-05-12` | 87 | 1,131 |
| `investor_net_buy_top_daily` | `2026-01-02` ~ `2026-05-12` | 87 | 74,872 |

## Current Backfill Progress

| Item | Value |
| --- | --- |
| Analysis window | `2024-11-12` ~ `2026-05-15` |
| Business dates in window | 366 |
| Loaded KRX OpenAPI daily dates | 367 |
| Missing KRX OpenAPI daily dates | `2026-05-15` only, pending latest-day publication |
| Current earliest stock/ETF/index date | `2024-11-08` |
| Next dry-run candidate batch | `2026-05-15` after KRX Open API rows are available |

## Repeatable Commands

```powershell
python -m stock_monitor krx-baseline-analysis --lookback-days 550 --max-missing-dates 5
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag before_krx_18m_batch_YYYYMMDD_YYYYMMDD
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --dry-run
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --sleep-seconds 3 --confirm --i-backed-up
python -m stock_monitor db-cleanup --dry-run --retention-days 550
```

## P2 Completion Criteria

| Criterion | Status |
| --- | --- |
| Tool/agent/source comparison recorded | Done |
| 2024~2026 holiday guard in code/tests | Done |
| Repeatable baseline analysis command | Done |
| Partial nonzero KRX endpoint guard | Done |
| OpenAPI 18-month backfill completed through latest stored date | Done |
| Data Marketplace 18-month broad flow collection | Deferred; requires separate request-volume decision. The narrow `[12009]` same-day mentioned-stock 31-day path is the only approved automatic exception. |
| Public scoring/recommendation | Blocked |
