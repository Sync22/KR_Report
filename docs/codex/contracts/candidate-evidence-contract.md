# Candidate Evidence Contract

## Purpose

This document fixes the first implementable read-only `candidate_evidence` DTO boundary and the first rotation image alias-mapping step.

It approves observation-candidate evidence and future observation-candidate recommendation, but it does not approve public numeric scoring, investment ranking weights, trading recommendations, or final ETF/stock picks.

Use this when changing the computed `관찰 후보 근거` API/DTO or planning its future UI.

## Source And Persistence Boundary Analyzed

The first DTO must stay inside already stored project data.

Approved source/persistence boundary:

| Layer | Source | Current persistence/query path | Use in CE-1 |
| --- | --- | --- | --- |
| Report summary | Naver Research | `daily_stock_summaries`, `repository.list_daily_summaries(business_date)` | Primary row seed |
| Report detail | Naver Research | `reports`, `repository.list_reports_for_business_date(business_date)` | Broker count, detail-only guard, source links |
| Stock market reference | KRX Open API | `stock_market_daily`, `repository.list_stock_market_daily_for_codes(...)` | Exact-date price/change/volume/turnover |
| Stock investor flow | KRX Data Marketplace `[12009]` | `stock_investor_flow_daily`, `repository.list_stock_investor_flow_daily(...)` | Stock-level flow reference when stored |
| Market investor flow | KRX Data Marketplace `[12008]` | `market_investor_flow_daily`, `repository.list_market_investor_flow_daily(...)` | Top-level market context, not a score |
| Net-buy ranking | KRX Data Marketplace `[12010]` | `investor_net_buy_top_daily`, `repository.list_investor_net_buy_top_daily(...)` | Rank-presence reference only |
| Category rollup | Snapshot-aware taxonomy layer | `repository.list_category_rollups_by_display_name_for_business_date(...)` | Separate context only |
| ETF reference | KRX Open API | `etf_daily_snapshots`, `repository.list_etf_daily_by_turnover(...)` | Not part of stock CE-1 row; used later for rotation preview |

Out of scope for CE-1:

- live fetch
- scheduled ingest changes
- DB schema changes
- writing candidate rows into SQLite
- trading-recommendation wording
- public numeric score, investment grade, or weight fields

## First Implementable DTO

CE-1 is a read-only snapshot builder, not a new table.

Current builder shape:

```text
build_web_view_candidate_evidence_snapshot(config, repository, business_date, limit=20) -> dict
```

Top-level payload:

| Field | Meaning | Source |
| --- | --- | --- |
| `surface` | Always `web-view` | constant |
| `read_only` | Always `true` | constant |
| `business_date` | Requested business date | input |
| `available` | At least one row exists | derived |
| `data_scope` | `stored_report_krx_evidence` | constant |
| `scoring` | Always `false` | constant |
| `notice` | Explain read-only/no-trading-recommendation boundary | constant |
| `market_flow_context` | `[12008]` summary rows for the date | stored flow |
| `rows` | Per-stock evidence rows | joined read model |

Per-stock row:

| Field | Meaning | Source | Notes |
| --- | --- | --- | --- |
| `business_date` | Trading date | summary | required |
| `stock_code` | 6-digit stock code | summary | required for CE-1 row inclusion |
| `stock_name` | Display name | summary | required |
| `report_summary.report_count` | Mention count | `DailyStockSummary.mention_count` | required |
| `report_summary.broker_count` | Unique broker count | `reports.broker_name` | derive from stored reports; no schema change |
| `report_summary.broker_display` | Existing display string | summary | display-only |
| `report_summary.target_price_min` | Aggregated min target | summary | nullable |
| `report_summary.target_price_max` | Aggregated max target | summary | nullable |
| `report_summary.dominant_opinion` | Aggregated opinion | summary | keep current summary semantics |
| `market_reference.market` | KOSPI/KOSDAQ | KRX stock daily | nullable when exact-date KRX row missing |
| `market_reference.close_price` | Close price | KRX stock daily | nullable |
| `market_reference.change_percent` | Daily change | KRX stock daily | nullable |
| `market_reference.volume` | Volume | KRX stock daily | nullable |
| `market_reference.turnover` | Turnover | KRX stock daily | nullable |
| `stock_flow_reference.available` | Whether `[12009]` row set exists | stock flow | required |
| `stock_flow_reference.snapshot_date` | Stored flow date | stock flow | exact date only |
| `stock_flow_reference.foreign_net_buy_volume` | Foreign net-buy volume | stock flow | sum normalized `외국인` rows only |
| `stock_flow_reference.institution_net_buy_volume` | Institution net-buy volume | stock flow | sum `기관`/`기관합계` only |
| `stock_flow_reference.individual_net_buy_volume` | Individual net-buy volume | stock flow | sum `개인` only |
| `stock_flow_reference.amount_unit` | Stored amount unit | stock flow | preserve source unit |
| `stock_flow_reference.volume_unit` | Stored volume unit | stock flow | preserve source unit |
| `rank_reference.foreign_top_rank` | `[12010]` foreign rank if present | top-net-buy table | nullable |
| `why_notable` | Public display labels for differentiating why the row is visible | derived display projection | exclude always-on coverage facts that are already in evidence boxes |
| `missing_information` | Public display labels for true missing information | derived display projection | do not use `not in top list` as a missing-data label |
| `quality_flags` | Missing/fallback markers | derived | required |
| `evidence_notes` | Flat fact labels only | derived | no score text |

Internal sort and operator diagnostics are separate from public labels.

- `why_notable` and `missing_information` are public-visible display vocabulary for `web-view`.
- Sort-only signals such as broker breadth, target-range availability, turnover availability, and price/volume position must not be exposed by relying on frontend filtering.
- Operator/readiness commands may inspect internal candidate signals, but those counts must be named separately from visible label counts.
- `candidate-evidence-readiness` should report visible label counts and internal signal counts separately so operator review and friend-facing cards do not use different hidden vocabularies.
- The public `/api/candidate-evidence` projection should stay thinner than the internal review row. Public rows keep display-ready labels and evidence boxes, but must not expose `quality_flags`, `evidence_notes`, `opinion_summary`, `report_summary.broker_count`, `report_summary.broker_display`, `report_summary.dominant_opinion`, or internal sort vocabulary such as broker breadth in public policy copy. Those fields may remain available only when the builder is called for operator/readiness review with internal diagnostics enabled.

## Exact Repository Fields To Use

CE-1 should use only current repository methods and current dataclass fields.

### Seed rows

`repository.list_daily_summaries(business_date)`

- `business_date`
- `stock_code`
- `stock_name`
- `mention_count`
- `broker_display`
- `target_price_min`
- `target_price_max`
- `dominant_opinion`

### Broker count and detail guard

`repository.list_reports_for_business_date(business_date)`

- `stock_code`
- `broker_name`
- `target_price_value`
- `opinion_normalized`
- `published_at`
- `source_url`

Use this only to derive `broker_count` and optional detail-presence flags.
Do not recompute target ranges or dominant opinion from scratch in CE-1.
Keep `daily_stock_summaries` as the aggregate owner.

### Exact-date stock market reference

`repository.list_stock_market_daily_for_codes(business_date, stock_codes)`

- `market`
- `close_price`
- `change_percent`
- `volume`
- `turnover`

Do not fall back to the latest stored KRX date.
If the selected date has no KRX row, keep the market block nullable and add a quality flag.

### Stock-level investor flow reference

`repository.list_stock_investor_flow_daily(business_date, stock_code)`

- `investor_type`
- `net_buy_volume`
- `net_buy_amount`
- `volume_unit`
- `amount_unit`

Use only stored exact-date rows.
Do not use `candidate_score` or `candidate_reasons`.
Those fields came from source-validation work and must stay out of CE-1.

### Market-wide flow context

`repository.list_market_investor_flow_daily(business_date, market)`

- `market`
- `investor_type`
- `net_buy_volume`
- `net_buy_amount`
- `volume_unit`
- `amount_unit`

This should stay in the top-level `market_flow_context`, not be repeated into every stock row.

### Net-buy rank presence

`repository.list_investor_net_buy_top_daily(business_date, market, "foreign", limit=10)`

- `rank`
- `stock_code`
- `stock_name`
- `net_buy_volume`
- `net_buy_amount`

CE-1 should expose only rank presence for the current stock.
Do not convert rank presence into a score.

## CE-1 Exclusion And Quality Rules

| Rule | Implementation meaning |
| --- | --- |
| Missing stock code excludes the row. | A candidate-evidence row without stable KRX join keys is not safe. |
| Missing target/opinion must not improve a row. | Preserve detail visibility, but do not add positive notes for missing values. |
| Missing exact-date KRX stock row is a flag, not a latest-date fallback. | Keep `market_reference` nullable, add `missing_krx_stock_snapshot`, and use public wording such as `선택일 KRX 저장값 없음`. |
| Missing `[12009]` flow is a flag, not neutral evidence. | Add `missing_stock_flow` or `partial_stock_flow`, and use public wording such as `종목 수급 저장값 없음`. |
| Category fallback must stay outside stock evidence for CE-1. | Per-stock dated category lookup is not yet implemented; do not silently attach current sector names. |
| `candidate_score` and `candidate_reasons` are ignored. | They are operator/source-validation fields, not public evidence. |

Suggested `quality_flags` values:

- `missing_krx_stock_snapshot`
- `missing_stock_flow`
- `missing_target_price`
- `missing_valid_opinion`
- `rank_not_present`

## Why Category Is Not In The First Stock Row

Current repository coverage is strong for:

- date-aware category rollups
- category detail by category name/display name

Current repository coverage is not yet direct for:

- one stock -> one dated sector display lookup row for CE-1

Because snapshot semantics matter, CE-1 should not reach back to current `stock_metadata.sector_name` as a shortcut.

Safe rule:

1. Keep stock `candidate_evidence` rows category-free in CE-1.
2. Keep category/rotation as a separate descriptive layer.
3. Add a dedicated read-only repository helper for dated stock->category membership later if needed.

## First Rotation Image Alias-Mapping Step

Current state:

- `data/rotation_overlay_coordinates.json` is keyed by current category `display_name`
- `build_web_view_rotation_overlay_snapshot(...)` matches rollup `display_name` directly to that coordinate key
- the overlay `label` field is display text only, not a canonical join key

The first alias step must therefore be a separate artifact, not a coordinate-file rewrite.

Suggested future artifact:

```text
data/rotation_image_aliases.json
```

Suggested row shape:

| Field | Meaning |
| --- | --- |
| `rotation_label` | Human-reviewed text label from `example/Cycle.jpg` |
| `category_type` | Start with `sector` only |
| `category_display_name` | Current dated rollup/display name to match in repository output |
| `coordinate_display_name` | Existing key in `rotation_overlay_coordinates.json` |
| `mapping_basis` | `manual_alias` |
| `status` | `active`, `unmatched`, or `review_needed` |
| `note` | Optional operator memo |

Guardrails:

- Do not overload `coordinates[].label` as the alias source of truth.
- Do not map directly from image label to ETF code in this step.
- Do not mix theme aliases into the sector overlay until taxonomy coverage is stronger.

## Smallest Safe Next Implementation Step

1. Add a read-only builder that joins `daily_stock_summaries`, exact-date KRX stock rows, exact-date `[12009]` rows, and `[12010]` rank presence.
2. Keep `[12008]` market flow in a top-level context block.
3. Leave per-stock category membership out of CE-1.
4. Use the draft `data/rotation_image_aliases.json` only as a review artifact until the image labels are manually confirmed.
5. Add UI only after the DTO snapshot is manually reviewed across several dates.

No migration is required for steps 1-4.

## Migration And Schema Implications

Current recommendation:

- no new SQLite table
- no schema version bump
- no live DB edits

If later work requires a stored artifact, add it through the migration runner only after the runner exists.
Until then, keep:

- `candidate_evidence` as a computed DTO only
- rotation alias mapping as a flat local JSON artifact

## Backtest-Period Guidance

Use two separate review windows.

### DTO/manual review window

Use `2026-05-04` through `2026-05-08` first.

Reason:

- exact-date web-view KRX context is already validated for these dates
- market-flow visibility is already part of the stored read-only paths
- stock-level `[12009]` data exists for observed candidate names during this period

This window is good for row-shape review and missing-data flag review.
It is not good enough for scoring conclusions.

### Future scoring/backtest window

Do not start score or hit-rate backtests on `2026-01-02` through `2026-05-08` as one uniform dataset.

Reason:

- KRX stock/ETF/index snapshots are broad for that period
- stock-level `[12009]` flow coverage is still candidate-selective and manually backfilled
- dated per-stock category membership is not yet exposed as a stable read-only join

Minimum future rule for scoring/backtest:

1. use only a contiguous window with complete daily summary coverage
2. require exact-date KRX stock snapshots for all evaluated dates
3. require explicit coverage rules for `[12009]` stock flow across the evaluated universe
4. keep the first quantitative window at least `40` to `60` Korean business days

Until those conditions are met, treat `2026-04-01` through `2026-05-08` as an offline evidence review window only.

## Future Ownership

Future scoring/backtest work should be owned by:

- `market-data-engineer`: primary owner for feature boundary, source coverage, and no-leakage evidence design
- `sql-pro`: coverage checks, replay-safe dataset extraction, and later migration-runner alignment
- `test-engineer`: fixture windows, regression tests, and backtest harness safety
- `reviewer`: leakage review, trading-recommendation-boundary review, and policy challenge

Secondary roles after the score boundary is approved:

- `python-pro`: scoring/backtest implementation details
- `web-ui-engineer`: read-only score display only after policy approval
