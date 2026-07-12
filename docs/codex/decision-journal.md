# Decision Journal

Decision Journal v0 read-only JSON contract.

## Included sections
- Decision Journal v0 JSON Contract

<!-- Merged from: docs/codex/decision-journal.md -->
## Decision Journal v0 JSON Contract

## Purpose

Decision Journal v0 records why the stored web-view candidate pool produced its current Top2 order.

It is a decision journal, not a stock recommendation system. Its job is to preserve what was known, what was missing, whether the Top2 boundary was clear, and which later outcome rows should be linked when a real persisted journal exists.

## Non-Goals

- No public score, rating, recommendation, buy/sell wording, target return, or broker execution path.
- No live fetch.
- No DB write.
- No `decision_journal_*` table until a separate migration is approved.
- No raw HTML, raw news body, secrets, operator diagnostics, or hidden scoring output.
- No change to existing web-view ordering from this dry-run contract alone.

## Dry-Run Rules

`decision-journal-dry-run` is read-only.

Required top-level invariants:

| Field | Value |
| --- | --- |
| `surface` | `decision-journal-v0` |
| `read_only` | `true` |
| `writes_db` | `false` |
| `live_fetch` | `false` |
| `scoring` | `false` |
| `recommendation` | `false` |

`--recent-business-days N` returns a read-only batch wrapper with `surface=decision-journal-v0-batch` and a `runs` array of normal `decision-journal-v0` payloads. The wrapper is validation output only. Persist v1 should store the per-date payloads, not the batch wrapper.

## Selection-Level Fields

| Field | Meaning | Persist v1 |
| --- | --- | --- |
| `algorithm_version` | Builder/version that created the dry-run payload. | persist |
| `business_date` | Candidate pool business date. | persist |
| `generated_at` | Dry-run generation timestamp. | persist |
| `candidate_limit` | Requested pool limit. | dry-run only |
| `candidate_pool_size` | Number of frozen candidates returned. | derive on read |
| `selected_top_n` | Number selected for TopN review, currently max 2. | persist |
| `tie_break_policy_version` | Version of explainability/tie-break metadata policy. | persist |
| `explainability_status` | Whether the Top2 boundary is clear, tied, weak, or not explainable. | persist |
| `explainability_notes` | Human-readable notes for `explainability_status`. | persist |
| `tie_break_applied` | `true` when the Top2 boundary needed a secondary tie-break. | derive on read |
| `fallback_reason` | Non-meaningful fallback reason at the Top2 boundary, or `null`. | derive on read |
| `data_completeness_status` | Whether the stored evidence is complete enough to interpret the decision. | persist |
| `data_completeness_notes` | Human-readable missing/freshness notes. | persist |
| `source_freshness` | Stored source freshness context. | persist compact summary |
| `sort_tuple_source` | Source builder for the frozen sort tuple. | persist |
| `field_coverage` | Dry-run readiness notes for future persistence. | dry-run only |

## Candidate-Level Fields

| Field | Meaning | Persist v1 |
| --- | --- | --- |
| `rank` | Candidate rank in the frozen pool. | persist |
| `stock_code` | Six-digit stock code. | persist |
| `stock_name` | Display name at selection time. | persist |
| `selected` | Whether the row was inside selected TopN. | persist |
| `observation_priority` | Stored public-safe observation priority label. | persist |
| `why_notable` | Public-safe reasons visible at selection time. | persist |
| `missing_information` | Public-safe missing evidence visible at selection time. | persist |
| `reference_notes` | Public-safe stored reference notes. | persist |
| `sort_tuple` | Frozen ordering tuple from the current builder. | persist |
| `report_count` | Stored report count. | persist |
| `broker_count` | Stored broker breadth. | persist |
| `turnover` | Stored KRX turnover reference, nullable. | persist |
| `krx_freshness` | KRX row freshness against `business_date`. | derive on write, persist value |
| `krx_exact_available` | Whether exact-date KRX exists. | derive on read |
| `investor_flow_freshness` | Stored stock-level flow freshness. | derive on write, persist value |
| `flow_freshness` | Alias for investor-flow freshness for journal readability. | derive on read |
| `news_freshness` | News evidence freshness. | derive on write, persist value |
| `news_direct_count` | Direct news match count. | persist |
| `news_collected_at` | News observation collection timestamp, nullable. | persist |
| `target_revision_available` | Whether target revision evidence exists. | derive on read |
| `price_reference_time` | Stored price/reference timestamp or date, nullable. | persist |
| `data_completeness_flags` | Candidate-level missing/freshness flags. | derive on read |
| `decision_explanation` | Human-readable explanation separated from machine features. | persist |
| `tie_group` | Group label for candidates sharing the meaningful tuple. | derive on read |
| `tie_break_reason` | Explainable feature that separated tied candidates, or `none`. | derive on read |
| `fallback_reason` | Non-meaningful deterministic fallback, or `null`. | derive on read |
| `comparable_to_rank_above` | Whether rank above shares the meaningful tuple. | derive on read |
| `comparable_to_rank_below` | Whether rank below shares the meaningful tuple. | derive on read |
| `rank_reason` | Human-readable rank boundary note. | derive on read |

## Field Semantics

### `explainability_status`

Allowed values:

| Value | Meaning |
| --- | --- |
| `clear` | Top2 separates on meaningful stored features. |
| `near_tie` | Top2 boundary shares the meaningful tuple with rank 3 or nearby candidates. |
| `weak` | A candidate can be ordered, but freshness or evidence gaps reduce confidence. |
| `insufficient_data` | Stored evidence is too weak to justify the Top2 boundary. |

### `data_completeness_status`

Allowed values:

| Value | Meaning |
| --- | --- |
| `complete` | Required v0 stored references are present. |
| `partial` | Core references exist, but the Top2 boundary still needs tie-break metadata. |
| `weak` | Important references are missing or stale. |
| `insufficient` | Evidence gaps make the decision weak enough that the system must say so. |

### `tie_break_reason`

This is for explainable feature-based separation only.

Allowed values:

| Value | Meaning |
| --- | --- |
| `meaningful_tuple` | Meaningful tuple separates the candidate without a secondary tie-break. |
| `report_count` | Report count separates tied candidates. |
| `broker_count` | Broker breadth separates tied candidates. |
| `turnover` | Stored KRX turnover separates tied candidates. |
| `news_direct_count` | Direct news evidence separates tied candidates. |
| `freshness` | Freshness separates tied candidates. |
| `target_revision` | Target revision direction/availability separates tied candidates. |
| `none` | No explainable feature separated the tie. |

### `fallback_reason`

This is only for non-meaningful deterministic fallback. Explainable features such as `turnover`, `report_count`, `broker_count`, `news_direct_count`, target revision, or freshness must not appear here.

Allowed values:

| Value | Meaning |
| --- | --- |
| `null` | No non-meaningful fallback was used. |
| `deterministic_order` | Stable deterministic fallback was needed. |
| `stock_code` | Stock-code fallback was used. |
| `input_order` | Input order fallback was used. |

## Example JSON

```json
{
  "surface": "decision-journal-v0",
  "read_only": true,
  "writes_db": false,
  "live_fetch": false,
  "scoring": false,
  "recommendation": false,
  "business_date": "2026-06-30",
  "selected_top_n": 2,
  "tie_break_policy_version": "decision-journal-tie-break-v0",
  "explainability_status": "near_tie",
  "tie_break_applied": true,
  "fallback_reason": null,
  "data_completeness_status": "partial",
  "candidates": [
    {
      "rank": 2,
      "stock_code": "005930",
      "selected": true,
      "tie_group": "tie:2-4",
      "tie_break_reason": "turnover",
      "fallback_reason": null,
      "data_completeness_flags": ["missing_news"]
    }
  ]
}
```

## DB Migration Preconditions

Before a v1 migration:

1. Confirm this JSON contract against at least 10 business dates.
2. Freeze `tie_break_policy_version`.
3. Decide whether `sort_tuple` is stored as JSON text or normalized columns.
4. Add outcome linkage design for D+1/D+5/D+20 before storing outcome rows.
5. Add rollback plan that drops only `decision_journal_*` tables and leaves web-view data untouched.
6. Add tests proving dry-run and persisted journal payloads agree for the same stored source data.

## Do Not Store

- Raw HTML.
- Raw news body.
- Hidden scoring weights or draft scores.
- Buy/sell/recommendation labels.
- Public numeric score or investment grade.
- Operator diagnostics not needed to explain the decision.
- Secrets, cookies, tokens, account data, or broker/order state.
