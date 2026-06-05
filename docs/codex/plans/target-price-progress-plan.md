# Target Price Progress Plan

This document fixes the P1-prep boundary for target-price based observation.

It can support observation-candidate recommendation, but it does not approve public numeric scoring, investment grades, buy/sell judgment, or automatic historical report backfill.

## Purpose

The user-facing `web-view` now has separate tabs for:

- `메인`: date-based report summary and selected-stock detail
- `관찰`: stored evidence rows from reports, KRX market reference, and investor flow
- `ETF`: stored ETF trend reference
- `순환매`: descriptive cycle-image overlay

Target-price progress belongs to the `관찰` direction, not the current main report list.

## Metrics

| Metric | Formula | Use |
| --- | --- | --- |
| Target gap | `(target_price - current_price) / current_price` | Shows remaining upside/downside to the report target. |
| Target progress | `(current_price - baseline_price) / (target_price - baseline_price)` | Shows how much of the move from first observed report price to target has been reached. |
| Max progress | Maximum progress after the report date | Later backtest/validation metric. |
| Hit days | First business-day count until target is reached | Later factual validation metric. |

## Baseline Rule

| Item | Decision |
| --- | --- |
| Baseline date | First stored report date for the stock within the observation window. |
| Baseline price | KRX close price on that report date. |
| Target price | Valid numeric target only. Missing markers such as `N/A`, `-`, or empty values are excluded from calculations. |
| Multiple reports | Use min/max target range for display. Metric calculation can use representative target only after a separate policy decision. |
| Display wording | `진행률`, `괴리율`, `도달 여부`, `관찰 후보`, and `우선 확인` are allowed. Do not use public numeric `점수`, `투자등급`, `매수 후보`, or buy/sell decision wording. |

## Data Requirement

Current report data starts later than KRX price/volume data.

Because target progress depends on report issue date plus subsequent KRX prices, the safe first step is a report backfill preview, not real collection.

Preview command:

```powershell
python -m stock_monitor report-backfill-preview --lookback-days 31
python -m stock_monitor report-backfill-preview --from-date 2026-04-01 --to-date 2026-05-11 --json
```

The preview command must not call Naver and must not write DB rows.

Manual collection command:

```powershell
python -m stock_monitor report-backfill-manual --from-date 2026-04-21 --to-date 2026-04-23 --limit 1000 --dry-run
python -m stock_monitor db-backup
python -m stock_monitor report-backfill-manual --from-date 2026-04-21 --to-date 2026-04-23 --limit 1000 --confirm --i-backed-up
```

The manual command defaults to guarded behavior:

- `--dry-run` fetches pages but writes nothing.
- Real writes require both `--confirm` and `--i-backed-up`.
- It filters parsed reports to the requested business-date range.
- It rebuilds daily summaries only for dates that have selected reports.

## Real Backfill Guard

Real report backfill requires a separate explicit approval after preview output.

Before real collection:

- Run `python -m stock_monitor db-backup`.
- Keep request batches small.
- Add sleep between requests with `--page-delay-seconds`.
- Start with the most recent one-month window.
- Stop if Naver response shape changes or request failures increase.

## P1 Boundary

| Step | Status | Boundary |
| --- | --- | --- |
| P1-prep | Done | Web-view tab split, visible observation evidence, preview/report backfill guard. |
| P1 metric DTO | Done | `candidate_evidence.rows[].target_price_progress` now exposes stored-data-only target gap/progress in the `관찰` tab. |
| P1 backfill | Done for 2026 YTD baseline | `2026-01-02` through `2026-05-12` now has stored reports for all 87 covered business dates. Continue future backfill in small backed-up batches only. |
| P2+ validation | First read-only pass done | `target_observation` now exposes stored-window max progress and first target-hit D+ days when the baseline is below the target range. Longer-history interpretation remains observational only. |

## First Metric DTO Result

`target_price_progress` is now attached to each `candidate_evidence` row.

| Field group | Meaning |
| --- | --- |
| `available`, `gap_available`, `progress_available` | Whether each calculation has enough stored report/KRX price data. |
| `baseline_date`, `baseline_price` | First stored target-price report date for the stock and the KRX close price on that date. |
| `current_date`, `current_price` | Selected business date and the stored KRX close price for that date. |
| `target_price_min`, `target_price_max` | Valid numeric target-price range from the daily summary. |
| `target_gap_min_percent`, `target_gap_max_percent` | Current price gap to the target range. |
| `progress_to_min_percent`, `progress_to_max_percent` | Progress from baseline price toward the target range. |
| `validation_available`, `validation_window_days` | Whether stored future KRX rows are enough to show factual validation and how many later trading rows were inspected. |
| `max_progress_to_min_percent`, `max_progress_to_max_percent` | Maximum observed progress toward the target range inside the stored window. |
| `hit_min_horizon_days`, `hit_max_horizon_days` | First D+ trading-day index where the close reached the lower/upper target. |
| `validation_notice` | Why the validation is available or skipped, such as `stored_window_only` or `baseline_inside_target_range`. |

Display wording remains limited to `괴리` and `진행`.
This is evidence for review and observation-candidate ordering only. It is not a public numeric score, investment grade, or buy/sell signal.

## First Backfill Result

On `2026-05-11`, guarded report backfill was completed for the current one-month operating window.

| Range | API pages | Parsed reports | Selected reports | Inserted | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `2026-04-21` ~ `2026-04-23` | 20 | 1000 | 82 | 82 | First 3-business-day batch. |
| `2026-04-13` ~ `2026-04-17` | 60 | 3000 | 246 | 246 | First 5-business-day batch after raising page depth. |
| `2026-04-10` ~ `2026-04-20` | 100 | 5000 | 320 | 74 | Filled remaining `04-10` and `04-20`; already-filled dates deduped. |

Follow-up preview for `2026-04-10` through `2026-05-11` showed no remaining empty business dates.

Current DB counts after the backfill:

- `reports`: `1276`
- `daily_stock_summaries`: `759`
- covered business dates in `2026-04-10` through `2026-05-11`: `20 / 20`

## Recommended 3-Month Backfill Result

On `2026-05-11`, the recommended 3-month analysis line was also filled.

| Range | API pages | Parsed reports | Selected reports | Inserted | Page delay |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2026-04-03` ~ `2026-04-09` | 120 | 6000 | 184 | 184 | `0.2s` |
| `2026-03-30` ~ `2026-04-02` | 160 | 8000 | 106 | 106 | `0.2s` |
| `2026-03-23` ~ `2026-03-27` | 200 | 10000 | 102 | 102 | `0.25s` |
| `2026-03-16` ~ `2026-03-20` | 240 | 12000 | 81 | 81 | `0.25s` |
| `2026-03-09` ~ `2026-03-13` | 280 | 14000 | 72 | 72 | `0.3s` |
| `2026-03-03` ~ `2026-03-06` | 320 | 16000 | 91 | 91 | `0.3s` |
| `2026-02-23` ~ `2026-02-27` | 400 | 20000 | 152 | 152 | `0.35s` |
| `2026-02-09` ~ `2026-02-20` | 520 | 26000 | 521 | 521 | `0.4s` |

Final coverage after this run:

- `2026-02-09` through `2026-05-11`: `60 / 60` business dates covered
- `reports`: `2585`
- `daily_stock_summaries`: `1708`
- `db-verify`: passed
- `pytest`: `314 passed`

## 2026 YTD Report Backfill Result

On `2026-05-12`, the earlier 2026 report gap was filled from the first KRX trading day.

| Range | API pages | Parsed reports | Selected reports | Inserted | Page delay |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2026-01-02` ~ `2026-01-09` | 120 | 6000 | 124 | 124 | `0.4s` |
| `2026-01-12` ~ `2026-01-16` | 120 | 6000 | 209 | 209 | `0.4s` |
| `2026-01-19` ~ `2026-01-23` | 120 | 6000 | 188 | 188 | `0.4s` |
| `2026-01-26` ~ `2026-01-30` | 120 | 6000 | 294 | 294 | `0.4s` |
| `2026-02-02` ~ `2026-02-06` | 120 | 6000 | 367 | 367 | `0.4s` |

Coverage after this run:

- `2026-01-02` through `2026-05-12`: `87 / 87` stored report business dates
- `reports`: `3813`
- `daily_stock_summaries`: `2453`
- `db-verify`: passed
