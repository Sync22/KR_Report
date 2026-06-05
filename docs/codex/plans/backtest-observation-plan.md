# Backtest Observation Plan

## Purpose

This document defines the next read-only analysis step for the `관찰` tab.

The goal is to calculate how stocks behaved after report publication using already stored 2026 data, then show the result as observation evidence. It can support observation-candidate recommendation, but it is not a public numeric score, investment grade, trading-ranking model, or buy/sell signal.

## Current Data Baseline

| Data | Current Coverage | Planned Use |
| --- | --- | --- |
| Naver reports | `2026-01-02` through `2026-05-12` | Report date, stock, broker count, mention count, opinion, target price range. |
| Daily summaries | Built from stored reports | Base candidate rows and report-level aggregation. |
| KRX stock price/volume/turnover | `2026-01-02` through `2026-05-08` | Base price, future reaction, turnover context. |
| KRX market/ETF/index snapshots | `2026-01-02` through `2026-05-08` | Market background only. |
| KRX investor flow | `2026-01-02` through `2026-05-08` | Stored investor-flow reference for covered stock-days. |
| KRX net-buy ranking | `2026-01-02` through `2026-05-08` | Whether a stock appeared in foreign net-buy top lists. |

Coverage after `2026-05-08` is intentionally treated as unavailable until KRX snapshot/backfill rows exist. Do not fill those dates from newer or older data.

## Candidate Boundary

| Rule | Decision |
| --- | --- |
| Base candidate | Daily summary rows with `stock_code` and `mention_count >= 2`. |
| Date boundary | Candidate business date must have matching stored KRX stock data. |
| Missing target price | Keep the row for observation, but exclude it from target gap/progress calculations. |
| Missing flow | Keep the row and label flow as unavailable; do not infer direction. |
| Missing future horizon | Mark the horizon as not available; do not shorten `20영업일` to a smaller window. |
| Output wording | Use `관찰`, `반응`, `근거`, `참고`, `범위`, `포함 여부`. |
| Forbidden wording | Do not use public numeric score, investment grade, rank-as-quality, buy candidate, sell candidate, or similar trading-decision wording. Observation-candidate wording such as `오늘의 관찰 후보` and `우선 확인` is allowed. |

## Reaction Horizons

The first calculation unit is stock reaction after the report business date.

| Horizon | Definition | Output |
| --- | --- | --- |
| `D+1` | First later KRX trading day for the same stock code. | Close return, turnover, flow availability. |
| `D+5` | Fifth later KRX trading day. | Close return and target-progress snapshot. |
| `D+10` | Tenth later KRX trading day. | Medium short-term reaction. |
| `D+20` | Twentieth later KRX trading day. | One-month observation window. |

Base price is the KRX close on the report business date. Future price is the KRX close on the exact horizon trading day. If the exact horizon date is not stored, the horizon is `unavailable`.

Initial reaction fields:

| Field | Meaning |
| --- | --- |
| `base_close_price` | KRX close on report business date. |
| `horizon_close_price` | KRX close on the target future trading day. |
| `close_return_percent` | `(horizon_close_price - base_close_price) / base_close_price * 100`. |
| `horizon_turnover` | KRX turnover on the horizon date if stored. |
| `horizon_volume` | KRX volume on the horizon date if stored. |
| `available` | Whether the exact horizon calculation is possible. |
| `unavailable_reason` | Missing base price, missing horizon date, or missing future stock row. |

High/low path metrics can be added later only if the stored KRX daily table has reliable high/low values for the full window.

## Comparison Dimensions

The first pass compares observation facts side by side. It must not combine them into a score.

| Dimension | Comparison Method |
| --- | --- |
| `mention_count` | Keep exact count and simple buckets such as `2`, `3-4`, `5+`. Default candidate filter is `>= 2`. |
| Broker breadth | Show broker count separately from mention count. Same broker multiple reports remain part of the report count, not broker breadth. |
| Target price gap | Compare report-date close price against target price min/max. Missing or non-numeric target prices are excluded from the numeric gap. |
| Target price progress | Compare base close and horizon close against target min/max, using stored price only. Progress is descriptive. |
| Flow availability | Show whether stock-level investor flow exists for the report date and horizon date. |
| Flow direction | Display personal/foreign/institution net flow values or simple dominant side labels only when stored rows exist. |
| Turnover | Compare report-date turnover against same-market stored turnover distribution for that date. Use percentile or bucket labels only after field quality is verified. |
| Net-buy top inclusion | Store/display whether the stock appears in the foreign net-buy top list for the report date or horizon dates. |
| Market background | Keep index and market-level flow as context; do not let it override stock-level observation. |

## Domestic Observation Feature Gaps

For a future `국장 관찰 요약`, calculate feature availability before designing any public display. These are observation features, not scores or trading signals.

| Feature | Definition | Data need |
| --- | --- | --- |
| Price position | Distance from 52-week high, 20-day high, and 60-day high on the report date. | Stored KRX daily close history. |
| Short return | 5-day and 20-day close return before or through the report date. | Stored KRX daily close history. |
| Volume expansion | Report-date volume divided by prior 20-trading-day average volume. | Stored KRX daily volume history. |
| Turnover expansion | Report-date turnover divided by prior 20-trading-day average turnover. | Stored KRX daily turnover history. |
| Flow totals | Foreign, institution, and individual net-buy volume totals over 5/10/20/31 trading days. | Stored `[12009]` stock investor-flow rows. |
| Flow persistence | Count of positive/negative net-buy days by investor group in the same windows. | Stored `[12009]` stock investor-flow rows. |
| Flow turn | First recent date where foreign/institution flow switched direction. | Stored `[12009]` stock investor-flow rows. |
| Report momentum | Same-stock report count over 1 and 5 business days. | Stored Naver reports. |
| Broker breadth | Number of distinct brokers over 1 and 5 business days. | Stored Naver reports. |
| Target revision | Latest target price vs prior stored target range for the same stock. | Stored reports with numeric target prices. |
| Sector breadth | Same-sector report count, positive price breadth, turnover breadth, and flow-covered stock count. | Category snapshots plus KRX daily and `[12009]` rows. |

Initial audit output should answer:

- Which latest report-mentioned stocks have complete 31-day `[12009]` coverage?
- Which stocks have enough KRX price/volume/turnover history for 20-day and 52-week metrics?
- Which observation features are sparse enough to hide or label as unavailable?
- Which features correlate with completed D+1/D+5/D+10/D+20 reaction windows without being promoted to a public score?

## Read-Only Calculation Shape

The first implementation should be query/DTO based. Do not introduce destructive DB changes.

Suggested internal builder:

| Builder | Purpose |
| --- | --- |
| `build_backtest_observation_rows(business_date, mention_threshold=2)` | Returns read-only observation rows for a stored candidate date. |
| `ReactionWindow` | Holds exact-horizon `1/5/10/20영업일` price/volume/turnover reaction values. |
| `TargetObservation` | Holds target gap/progress values only when numeric targets and stored prices exist. |
| `StockFlowObservation` / `NetBuyTopObservation` | Holds same-date investor-flow and foreign net-buy top inclusion evidence. |

Suggested optional API after the query shape is stable:

| API | Purpose |
| --- | --- |
| `GET /api/observation/backtest?date=YYYY-MM-DD` | Selected-date observation rows. |
| `GET /api/observation/backtest?from=YYYY-MM-DD&to=YYYY-MM-DD` | Bounded archive review. |

Every new endpoint must remain `GET-only`, public-safe, and read-only.

## Web-View Observation Tab

The `관찰` tab should show evidence in layers, not as a decision screen.

| Area | Content |
| --- | --- |
| Header notice | Stored-data coverage, no trading-recommendation/public-score wording, and latest available KRX date. |
| Controls | Date range, horizon toggle `1/5/10/20영업일`, mention threshold default `2+`, target-price availability filter. |
| Candidate list | Stock name/code, report date, mention count, broker breadth, target price range, report-date close. |
| Target context | Target gap and target progress as descriptive percentages. |
| Reaction columns | `D+1`, `D+5`, `D+10`, `D+20` close reaction. Missing horizons show `데이터 없음`. |
| Flow context | Flow available/unavailable, personal/foreign/institution net flow summary if stored. |
| Turnover context | Report-date turnover and optional same-day market bucket after validation. |
| Net-buy context | Foreign net-buy top inclusion and rank/value only if stored. |
| Row detail | Full report titles, brokers, source date, raw missing-value hints. |

Default sort should be transparent, such as date descending or mention count descending. Avoid labels that imply quality or decision priority.

## Execution Stages

| Stage | Goal | Completion Criteria |
| --- | --- | --- |
| `BO-0` | Plan only | This document exists and is linked from roadmap/current work. |
| `BO-1` | Read-only candidate/market query | `mention_count >= 2` candidate rows and exact-date KRX market rows are queryable without schema changes. |
| `BO-2` | Reaction horizon calculation | `D+1/5/10/20` exact stored-trading-row selection and close-return calculation are tested. |
| `BO-3` | Target comparison values | Target gap/progress are calculated only when numeric target and price values exist. |
| `BO-4` | Flow/turnover/net-buy context | Same-date stock flow, base/horizon turnover, and foreign net-buy top inclusion are attached without latest-date fallback. |
| `BO-5` | Public DTO/API | User-facing DTO/API exposes BO-1~BO-4 results as public-safe read-only data. |
| `BO-6` | Web-view tab polish | `관찰` tab displays observation rows without decision wording. |
| `BO-7` | Multi-date review | At least several stored dates are manually reviewed for misleading/missing values. |
| `BO-8` | Later discussion gate | Only after BO-7 can weighting or stronger filtering be discussed. Scoring remains separate. |

## Test Plan For Future Implementation

| Test Area | Required Checks |
| --- | --- |
| Horizon calculation | Exact later KRX trading day is selected for `1/5/10/20`; weekends/holidays are skipped by stored trading rows. |
| Missing data | Missing base price, future price, target price, or flow data produces explicit unavailable labels. |
| Candidate filter | `mention_count >= 2` is default, configurable, and does not mutate stored summaries. |
| Target values | `N/A` or blank target prices do not enter numeric min/max/gap/progress. |
| Flow context | Flow rows are joined by stock code and date only; no latest-date fallback. |
| Net-buy inclusion | Inclusion is a boolean/context field, not a quality ranking. |
| Public safety | No admin status, scheduler state, DB path, `.env`, Telegram token, or control endpoint leaks into DTOs. |
| Language guard | Web-view copy may recommend observation targets, but avoids public numeric score, investment grade, and buy/sell decision wording. |

Suggested verification commands after implementation:

```powershell
python -m pytest tests\test_web_view.py tests\test_repository.py tests\test_cli_commands.py -q
python -m stock_monitor db-verify
```

## Risks And Constraints

| Risk | Handling |
| --- | --- |
| Short history | 2026 history is useful for observation, but not enough for confident decision modeling. Keep the screen descriptive. |
| Fast market regime | Early 2026 market behavior may bias short reaction windows. Show raw observation and date coverage. |
| Incomplete latest KRX dates | Do not calculate horizons from missing or mixed dates. |
| Report backfill quality | Naver report history remains the report source of truth, but old page availability/parser drift must be treated as a data-quality risk. |
| Category drift | Category/theme context is secondary and should not drive backtest calculations until dated taxonomy coverage improves. |

## Next Action

Current implementation status:

| Stage | Status |
| --- | --- |
| `BO-0` | Done. |
| `BO-1` | Done through `StockMonitorRepository.list_daily_summaries_for_backtest_observation()` and exact-date KRX market lookup. |
| `BO-2` | Done through `ReactionWindow` calculation and regression tests. |
| `BO-3` | Done through `TargetObservation` calculation with missing target protection. |
| `BO-4` | Done through same-date stock flow, turnover, and foreign net-buy top inclusion context. |
| `BO-5` | Done through `GET /api/observation/backtest?date=YYYY-MM-DD` and `build_web_view_backtest_observation_snapshot()`. |
| `BO-6` | Done through the `관찰` tab `리포트 후 반응 관찰` table. |
| `BO-7` | Done for `2026-05-11`, `2026-05-08`, and `2026-05-07`; added target-progress caution labeling for misleading progress cases. |
| `BO-8+` | Not started as implementation. [scoring-draft-plan.md](scoring-draft-plan.md) records the draft-only path; actual scoring remains blocked. |
