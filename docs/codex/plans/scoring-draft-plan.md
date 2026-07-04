# Scoring Draft Plan

> Archived / hold as of 2026-06-30: this lane is not active product scope.
> Keep this file only as historical research evidence. Hidden scoring CLI
> commands are excluded from top-level CLI help and must not drive public
> `web-view`, Telegram, daily briefing, ordering copy, roadmap progress, or
> investment decisions. Current product work should improve stored evidence,
> missing-data labels, and backtest/evidence snapshots without adding scores.

## Purpose

This document is a draft for a later scoring experiment.

It does not implement public numeric scoring, investment grades, trading recommendations, buy/sell signals, Telegram candidate alerts, or one-pick outputs. The current product remains an observation system with observation-candidate recommendation allowed through evidence ordering and reason text. Any public numeric scoring work must wait until read-only observation rows have been reviewed across enough dates.

## Current Status

| Area | Status |
| --- | --- |
| Candidate base | `mention_count >= 2` daily summary rows with stock code. |
| Backtest observation | BO-1~BO-7 complete: read-only calculation, API/UI exposure, and first multi-date QA. |
| Feature availability audit | SD-1 first pass exists as a read-only CLI command: `python -m stock_monitor observation-feature-audit --from-date YYYY-MM-DD --to-date YYYY-MM-DD`. |
| Reaction distribution audit | SD-2 first pass exists as a read-only CLI command: `python -m stock_monitor observation-reaction-distribution --from-date YYYY-MM-DD --to-date YYYY-MM-DD`. |
| Feature comparison audit | SD-3 first pass exists as a read-only CLI command: `python -m stock_monitor observation-feature-comparison --from-date YYYY-MM-DD --to-date YYYY-MM-DD`. |
| Internal weight draft | SD-4 first pass exists as an internal-only CLI command: `python -m stock_monitor observation-weight-draft --from-date YYYY-MM-DD --to-date YYYY-MM-DD`. |
| Hidden internal prototype | SD-5 first pass exists as internal-only CLI commands: `observation-hidden-prototype`, `observation-hidden-holdout`, and `observation-hidden-holdout-sweep`. |
| Tested dates | `2026-05-11`, `2026-05-08`, `2026-05-07`, plus full-range CLI audits over `2026-01-02`~`2026-05-12` and train/holdout checks using March/April/May windows. |
| Current caution added | Target-progress values now include `progress_caution` when baseline price starts inside/above target range. |
| Scoring implementation | Hidden/internal prototype only. Public scoring is not started. |
| User-facing score display | Not allowed yet. |

## Preconditions Before Scoring

| Requirement | Reason |
| --- | --- |
| More observation rows across 2026 | Short history can overfit to early-year market regime. |
| KRX latest-date backfill discipline | Reaction windows must not mix missing and future dates. |
| Multi-date QA | Misleading values must be labeled before any weighting. |
| Target-progress caution | Baseline-above-target and baseline-inside-target cases must not look like clean progress. |
| Flow coverage check | Missing stock flow should be treated as unavailable, not negative evidence. |
| No public decision wording | Even if internal scoring exists later, public copy must avoid trading-recommendation wording. Observation-candidate wording such as `오늘의 관찰 후보` and `우선 확인` is allowed. |

## Candidate Universe

Initial scoring experiments, if approved later, should use:

| Rule | Draft Decision |
| --- | --- |
| Base universe | Daily summary rows with `stock_code` and `mention_count >= 2`. |
| Date range | Stored 2026 report dates with matching KRX price rows. |
| Exclusions | No stock code, no base KRX close, impossible reaction window. |
| Kept as missing | Missing target price, missing flow, missing net-buy top inclusion. |
| No latest fallback | Flow, price, turnover, and net-buy rank must use exact stored dates only. |

## Feature Groups

The first scoring discussion should compare feature groups independently. Do not combine them into one score until the individual behavior is reviewed.

| Group | Candidate Features | Notes |
| --- | --- | --- |
| Report concentration | `mention_count`, broker breadth, same-day report clustering. | Higher count is not automatically better; it may also reflect crowded consensus. |
| Price reaction | `D+1`, `D+5`, `D+10`, `D+20` close reaction. | Use for backtest observation first. |
| Target context | Target gap min/max, target progress min/max, `progress_caution`. | Caution cases should be handled separately, not silently scored. |
| Turnover context | Report-date turnover, horizon turnover, same-market turnover bucket. | Needs market-relative bucket validation. |
| Investor flow | Personal/foreign/institution net flow and availability. | Missing flow is unknown, not bad. |
| Net-buy top inclusion | Foreign net-buy top rank/value on report date or horizons. | Inclusion is context; rank is not a final quality label. |
| Market background | Index movement and market-level investor flow. | Context only; should not dominate stock facts. |

## Draft Experiment Stages

| Stage | Goal | Output |
| --- | --- | --- |
| `SD-0` | Draft only | This document exists and is linked from roadmap/current work. |
| `SD-1` | Feature audit | First pass implemented. Count how many candidate rows have each feature available through a read-only CLI audit. |
| `SD-2` | Reaction distribution | First pass implemented. Show distributions of `D+1/5/10/20` reactions by mention bucket, target availability, and stock-flow availability. |
| `SD-3` | Feature comparison | First pass implemented. Compare feature groups against reaction windows without producing a final score. |
| `SD-4` | Weight proposal | First pass implemented as internal-only draft weights. It does not create stock-level scores, rankings, recommendations, or public output. |
| `SD-5` | Internal score prototype | First pass implemented as a hidden/internal prototype value plus feature pruning, holdout bucket validation, and rolling holdout sweep. It is not ranked, not user-facing, and not sent to Telegram. |
| `SD-6` | User-facing decision | Separate approval required before any score, grade, or recommendation appears in `web-view` or Telegram. |

## Draft Display Policy

If scoring is ever prototyped, the default user-facing state should still be observation-first.

| Surface | Allowed In Draft | Blocked |
| --- | --- | --- |
| `web-view 관찰` | Raw evidence, reaction windows, coverage labels, caution labels, observation-candidate ordering, reason text. | Public numeric score, investment grade, ranking as investment quality, trading recommendation. |
| Admin/operator view | Internal experiment metrics after approval. | Automatic trading-style wording. |
| Telegram | No scoring output. | Candidate alert, one-pick, buy/sell wording. |

## Open Decisions

| Decision | Current Position |
| --- | --- |
| Minimum history | At least current 2026 baseline plus more live days; longer is better. |
| Mention threshold | Default `>= 2`; compare `>= 3` only after SD-2. |
| Target missing rows | Keep for observation; exclude or separate for scoring experiment. |
| Flow missing rows | Keep as unknown; do not penalize without coverage analysis. |
| Positive/negative reaction | Use neutral labels such as `상승 반응`, `하락 반응`, `데이터 없음`; avoid quality judgment. |

## SD-1 Command

The first scoring-prep command is intentionally read-only. It reports coverage only; it does not create public numeric scores, investment grades, investment rankings, trading recommendations, or Telegram alerts.

```powershell
python -m stock_monitor observation-feature-audit --from-date 2026-01-02 --to-date 2026-05-12
python -m stock_monitor observation-feature-audit --from-date 2026-01-02 --to-date 2026-05-12 --json
```

Current coverage fields:

| Field | Meaning |
| --- | --- |
| `base_market` | Candidate has same-date KRX stock price row. |
| `target_observation` | Candidate has numeric target gap/progress context. |
| `target_progress_caution` | Candidate has a target-progress caution case. |
| `stock_flow` | Candidate has same-date stock investor-flow rows. |
| `foreign_net_buy_top` | Candidate appears in same-date foreign net-buy top rows. |
| `base_turnover` | Candidate has same-date KRX turnover. |
| `D+N reaction` | Candidate has an exact stored trading-day reaction row for horizon `N`. |

## SD-2 Command

The reaction distribution command is also read-only. It groups stored candidate rows by mention bucket, target availability, stock-flow availability, and reaction horizon. It reports count, available rows, rising/falling/flat/missing rows, average reaction, and min/max reaction.

```powershell
python -m stock_monitor observation-reaction-distribution --from-date 2026-01-02 --to-date 2026-05-12
python -m stock_monitor observation-reaction-distribution --from-date 2026-01-02 --to-date 2026-05-12 --json
```

Current full-range first pass over `2026-01-02` through `2026-05-12`:

| Metric | Value |
| --- | ---: |
| Candidate rows | 456 |
| D+1 available | 456 |
| D+5 available | 395 |
| D+10 available | 326 |
| D+20 available | 290 |

Early reading rule: these values are distributions only. Positive averages must not be translated into trading recommendation, investment grade, or buy/sell copy without later validation.

## SD-3 Command

The feature comparison command compares each feature group independently against the same reaction windows. It is still a neutral analysis table, not a ranking or decision engine.

```powershell
python -m stock_monitor observation-feature-comparison --from-date 2026-01-02 --to-date 2026-05-12
python -m stock_monitor observation-feature-comparison --from-date 2026-01-02 --to-date 2026-05-12 --json
```

Current compared feature groups:

| Feature | Values |
| --- | --- |
| `mention_bucket` | `2`, `3`, `4+` |
| `target_available` | `yes`, `no` |
| `target_progress_caution` | `yes`, `no` |
| `stock_flow_available` | `yes`, `no` |
| `foreign_net_buy_top` | `yes`, `no` |
| `base_turnover_available` | `yes`, `no` |

Current first-pass read-only observation over `2026-01-02` through `2026-05-12`:

| Observation | Note |
| --- | --- |
| `stock_flow_available=no` | Longer horizons are mostly missing because stock-flow collection policy currently covers the candidate universe unevenly over earlier dates. |
| `foreign_net_buy_top=yes` | Shows higher average reaction than `no` in the stored sample, but this is only observation evidence until sample bias and market-regime effects are reviewed. |
| `mention_bucket=4+` | Does not dominate every horizon; mention count alone is not enough for a decision rule. |
| `target_progress_caution=yes` | Needs separate treatment; caution rows should not be silently mixed into ordinary target-progress interpretation. |

Latest read-only observation after the 18-month KRX Open API baseline:

| Observation | Current reading |
| --- | --- |
| `mention_bucket=2` | D+20 average reaction is higher than the full baseline in the stored sample, but this may reflect market regime and sample composition. |
| `mention_bucket=4+` | Does not behave as a stronger signal. In the latest full-range D+20 comparison it underperformed `mention_bucket=2`, so high report count must not be treated as automatically better. |
| `foreign_net_buy_top=yes` | Continues to separate better than `no` in D+10/D+20 averages, but remains evidence only. |
| Recent May D+20 holdout | Mostly unavailable because enough future KRX prices do not exist yet. Missing future reactions are not negative evidence. |

## SD-4 Command

The weight draft command converts SD-3 deltas into internal-only draft weights. It compares each feature group's average reaction with the same horizon's baseline average and applies a small directional weight only when the sample size is sufficient.

```powershell
python -m stock_monitor observation-weight-draft --from-date 2026-01-02 --to-date 2026-05-12
python -m stock_monitor observation-weight-draft --from-date 2026-01-02 --to-date 2026-05-12 --json
```

Current guardrails:

| Rule | Decision |
| --- | --- |
| Minimum sample size | Default `20`; smaller groups are `sample_too_small` and weight `0`. |
| Delta under `1.0%` | Neutral, weight `0`. |
| Delta `1.0%` to `<3.0%` | Directional weight `1` or `-1`. |
| Delta `3.0%` to `<7.0%` | Directional weight `2` or `-2`. |
| Delta `>=7.0%` | Directional weight `3` or `-3`. |
| Missing target / missing stock flow / missing turnover | Unknown, forced weight `0`. |
| `target_progress_caution=yes` | Separate review, forced weight `0`. |
| Output surface | CLI only, internal-only. |
| Blocked use | No public stock-level numeric score, no investment ranking, no trading recommendation, no Telegram alert, no user-facing score label. |

Current first-pass caution:

| Caution | Reason |
| --- | --- |
| `stock_flow_available=no` longer horizons | Mostly unavailable because stock-flow collection focuses on candidate rows and earlier ranges are uneven. |
| `target_available=no` | Too few rows to draft a meaningful weight. |
| `target_progress_caution=yes` | Some horizons have small samples and must stay separated. |
| Positive `D+20` deltas | Need regime and survivorship review before using as any decision input. |

## SD-5 Command

The hidden prototype applies SD-4 draft weights to candidate rows and emits an internal `prototype_value`. This is not a product score and must not be sorted into a public ranking.

```powershell
python -m stock_monitor observation-hidden-prototype --from-date 2026-01-02 --to-date 2026-05-12 --horizon-days 20
python -m stock_monitor observation-hidden-prototype --from-date 2026-01-02 --to-date 2026-05-12 --horizon-days 20 --json
python -m stock_monitor observation-hidden-prototype --train-from-date 2026-01-02 --train-to-date 2026-05-07 --from-date 2026-05-08 --to-date 2026-05-12 --horizon-days 20
python -m stock_monitor observation-hidden-prototype --train-from-date 2026-01-02 --train-to-date 2026-04-30 --from-date 2026-05-01 --to-date 2026-05-12 --horizon-days 20 --exclude-feature target_progress_caution
python -m stock_monitor observation-hidden-holdout --train-from-date 2026-01-02 --train-to-date 2026-05-07 --holdout-from-date 2026-05-08 --holdout-to-date 2026-05-12 --horizon-days 20
python -m stock_monitor observation-hidden-holdout --train-from-date 2026-01-02 --train-to-date 2026-05-07 --holdout-from-date 2026-05-08 --holdout-to-date 2026-05-12 --horizon-days 20 --json
python -m stock_monitor observation-hidden-holdout-sweep --train-from-date 2026-01-02 --train-to-date 2026-04-30 --holdout-from-date 2026-05-01 --holdout-to-date 2026-05-12 --horizon-days 5 --horizon-days 20 --window-days 5 --exclude-feature target_progress_caution
```

Current guardrails:

| Rule | Decision |
| --- | --- |
| Public output | Blocked. |
| Ranking | Blocked; output order remains date/stock order. |
| Telegram output | Blocked. |
| Web-view output | Blocked. |
| Trading-recommendation wording | Blocked. |
| Latest-date use | Use separate train/apply ranges. Same-window training can produce mostly zero values for recent D+20 checks. |
| Holdout range | Holdout dates must start after the training range; overlapping train/holdout ranges are rejected. |
| Holdout use | Use `observation-hidden-holdout` to bucket internal prototype values against a separate reaction window before interpreting any direction. |
| Feature pruning | Use `--exclude-feature` to remove weak or biased feature names from SD-5 prototype components. Unknown feature names are rejected instead of being silently ignored. |
| Sweep use | Use `observation-hidden-holdout-sweep` to compare multiple holdout windows and horizons at once. |

Current holdout validation output:

| Field | Meaning |
| --- | --- |
| `bucket_name` | Internal prototype bucket only: `positive`, `neutral`, or `negative`. This is not a trading-recommendation label. |
| `candidate_count` | Holdout candidate rows in the bucket. |
| `available_count` | Rows with the selected D+N reaction available. |
| `average_return_percent` | Average stored reaction for the bucket and horizon. |
| `prototype_value_min/max` | Internal value range inside the bucket. |

Current sweep caution:

| Observation | Interpretation |
| --- | --- |
| Recent D+20 windows often have `available_count=0` | This is expected when not enough future KRX prices exist yet. Do not interpret missing holdout buckets as weak or strong evidence. |
| `target_progress_caution` can be excluded | This prevents baseline-above-target or inside-target cases from shaping the hidden prototype while the policy is still under review. |
| Feature pruning is explicit | Invalid `--exclude-feature` names fail fast so a typo cannot produce a misleading validation run. |
| Train/holdout overlap is blocked | Holdout validation must stay out-of-sample; overlapping date ranges are treated as invalid input. |

Known next refinement:

| Item | Reason |
| --- | --- |
| Mature holdout windows | Run holdout sweeps where D+N reaction values are actually available before any stronger claim. |
| Feature pruning review | Compare default output against pruned output, especially `target_progress_caution` and sparse feature groups. |
| Missing-value guard | Keep `missing_is_unknown` and `caution_separate_review` at weight `0`; they must not become negative evidence. |

## 2026-05-15 Baseline Snapshot

The Open API KRX daily stock/ETF/index baseline covers the stored 18-month window through the latest available snapshot date. The current same-day row is not expected from KRX Open API; the official publication window is the next Korean business day at `08:00` KST.

| Check | Result |
| --- | --- |
| KRX daily window | `2024-11-08`~`2026-05-14` stored. |
| Target analysis window | `2024-11-12`~`2026-05-15`. |
| Missing Open API business dates | `2026-05-15` only, pending latest-day publication. |
| DB verification | `integrity_check: ok`, schema `5/5`, partial KRX snapshot dates `0`. |
| Report-driven candidate window | Use completed reaction windows only; `2026-05-15` report rows exist but future reaction windows are not mature. |
| Candidate count | Recompute with the observation CLI for each validation run. |

Latest repeated validation commands:

```powershell
python -m stock_monitor db-verify
python -m stock_monitor krx-baseline-analysis --lookback-days 550 --max-missing-dates 20
python -m stock_monitor observation-feature-audit --from-date 2026-01-02 --to-date 2026-05-12 --mention-threshold 2
python -m stock_monitor observation-reaction-distribution --from-date 2026-01-02 --to-date 2026-05-12 --mention-threshold 2
python -m stock_monitor observation-feature-comparison --from-date 2026-01-02 --to-date 2026-05-12 --mention-threshold 2
python -m stock_monitor observation-weight-draft --from-date 2026-01-02 --to-date 2026-05-12 --mention-threshold 2 --min-sample-size 5
python -m stock_monitor observation-hidden-holdout --train-from-date 2026-01-02 --train-to-date 2026-03-31 --holdout-from-date 2026-04-01 --holdout-to-date 2026-04-30 --mention-threshold 2 --horizon-days 20 --min-sample-size 5
python -m stock_monitor observation-hidden-holdout-sweep --train-from-date 2026-01-02 --train-to-date 2026-04-30 --holdout-from-date 2026-05-01 --holdout-to-date 2026-05-14 --mention-threshold 2 --horizon-days 5 --horizon-days 20 --window-days 5 --min-sample-size 5 --exclude-feature target_progress_caution
```

Current interpretation:

| Point | Decision |
| --- | --- |
| 2026-04 D+20 holdout | `2026-01-02`~`2026-03-31` train, `2026-04-01`~`2026-04-30` holdout 기준 후보 107건, D+20 available 36건. Positive bucket 평균 `24.89%`, neutral `17.53%`, negative `17.76%`였으나 4월 시장 상승 효과와 missing count가 커서 public score로 해석하지 않는다. |
| 2026-05 sweep | `2026-05-01`~`2026-05-14` sweep에서 D+5 일부만 available이고, D+20은 아직 0건이다. Recent windows are observation-only. |
| Useful internal signal | Keep watching `mention_count=2`, foreign net-buy top inclusion, and D+20 reaction where available. |
| Unsafe shortcut | Do not assume `mention_count=4+` is better. |
| Public score readiness | Not ready. |
| User-facing wording | Keep `관찰`, `근거`, `반응`, `참고`, `오늘의 관찰 후보`, and `우선 확인`; do not use public numeric score, investment grade, trading recommendation, buy/sell, or one-pick wording. |

## Next Safe Work

The next safe work is still not public numeric scoring. It is SD-5 refinement plus observation-candidate reason quality: feature pruning and broader holdout validation can inform `오늘의 관찰 후보`, but do not expose any public numeric score, investment grade, trading recommendation, investment ranking, Telegram alert, or public decision wording without separate approval.
