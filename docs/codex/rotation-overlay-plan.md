# Rotation Overlay Plan

## Purpose

This document defines the sector-first rotation overlay based on `example/Cycle.jpg`.

The overlay is a descriptive review view. It can support observation-candidate recommendation, but not prediction, public numeric score, investment grade, or trading recommendation.

The first alias-mapping boundary for the image text is fixed in [candidate-evidence-contract.md](/docs/codex/contracts/candidate-evidence-contract.md).

## Current State

The original memo for rotation/flow tracking can be marked `[O]` for V1 foundation because KRX flow source validation, storage, and read-only display paths now exist.

The first visual overlay is implemented in the user `web-view` as a collapsed read-only section named `순환매 참고`.

Current implementation:

- serves the original image through `GET /assets/cycle.jpg`
- serves descriptive overlay data through `GET /api/rotation-overlay?date=YYYY-MM-DD`
- draws SVG circles on top of the JPG without modifying the original file
- highlights only sector categories that have a manual coordinate entry in `data/rotation_overlay_coordinates.json`
- uses `data/rotation_image_aliases.json` as the first image-text alias layer, mapping a human image label such as `우주항공` to the current sector display name and coordinate key
- validates active image aliases through `web-view-value-qa`; mapped coordinate labels must exist in `data/rotation_overlay_coordinates.json` or QA fails
- includes read-only `candidate_stocks` preview rows per highlighted sector, derived from same-date report summaries and exact-date KRX stock snapshots
- includes read-only `candidate_etfs` only when an operator-managed mapping exists in `data/rotation_etf_candidates.json`
- validates active `candidate_etfs` mappings through `web-view-value-qa`; mapped ETF codes must exist in the latest stored ETF snapshot or QA fails
- validates active `candidate_etfs` categories through `web-view-value-qa`; each active mapping must resolve to an overlay coordinate directly or through an active image alias
- lazy-loads the image and overlay only when the collapsed section is opened
- labels evidence as report/category rollup observations or observation-candidate recommendation, not trading recommendation
- treats themes as supporting evidence only; the overlay marker itself should not mix sector and theme labels until the taxonomy is stronger
- keeps the first image-text alias draft in `data/rotation_image_aliases.json`

## Implementation Shape

| Phase | Work | Notes |
| --- | --- | --- |
| 1 | Show `example/Cycle.jpg` with an SVG overlay layer | Done in `web-view`; collapsed by default. |
| 2 | Maintain a manual coordinate map | Done as `data/rotation_overlay_coordinates.json`; move to DB only if admin calibration is needed. |
| 3 | Highlight active sectors | First report-count based sector highlight is implemented through the alias layer. Same-date stock candidates are shown as separated observation candidates, not trading recommendations. Turnover or investor-flow observations must remain separate evidence labels. |
| 4 | Add admin calibration | Let operator adjust coordinates later if the fixed image needs tuning. |

## First Data Contract

The first version should accept a prepared list like:

| Field | Meaning |
| --- | --- |
| `category_type` | `sector` for the overlay marker. Theme labels are supporting evidence only. |
| `display_name` | User-facing category label. |
| `x`, `y` | Coordinate on the base image. |
| `radius` | Overlay circle size. |
| `evidence_label` | Short text such as `리포트 4건`, `거래대금 상위`, `외국인 순매수`. |
| `evidence_source` | `report`, `krx_turnover`, `krx_flow`, or mixed. |
| `candidate_stocks` | Read-only stock preview rows with report count and exact-date KRX price/turnover when available. |
| `candidate_etfs` | ETF preview rows with exact-date stored KRX ETF turnover/change evidence when an operator-managed mapping exists. |

## Exclusions

- No trading recommendation.
- No public numeric score or investment grade.
- No auto-generated buy/sell signal.
- No unsupported mapping from report count to investor flow.

## Selection Readiness

Future `ETF 1개 + 종목 1개` selection must stay separate from the current overlay until these prerequisites are met:

| Prerequisite | Required State |
| --- | --- |
| Image text mapping | Cycle image labels have a manual alias table mapped to user-facing 업종 names. |
| Sector coordinates | The overlay coordinate map covers the target 업종 labels without mixing unrelated themes. |
| ETF candidates | Each target 업종 has one or more ETF candidates from stored KRX ETF data or an operator-managed mapping. |
| ETF mapping reachability | Each active ETF mapping category has a direct overlay coordinate or an active alias that points to an existing coordinate. |
| Stock candidates | Each target 업종 has candidate stocks from report summaries, KRX stock master, and category snapshots. |
| Evidence separation | Report count, target-price range, price/turnover, investor flow, and ETF trend are stored/displayed as separate evidence. |
| Display boundary | The user page may call these rows `오늘의 관찰 후보`, `후보`, or `참고`, but not `매수 추천`, `매도 추천`, public numeric score, or investment grade. |

First implementation should be a read-only preview table:

| Field | Meaning |
| --- | --- |
| `rotation_label` | Label from the cycle image or its alias. |
| `category_display_name` | Matched 업종 label. |
| `candidate_etfs` | ETF candidates with stored KRX turnover/change evidence. |
| `candidate_stocks` | Stock candidates with report/flow/turnover evidence. |
| `evidence_summary` | Short separated evidence text, not a score. |

## Done Criteria For First Implementation

- [O] The image renders with SVG circles without modifying the original JPG.
- [O] The overlay can show at least one manually mapped sector category.
- [O] Missing coordinates simply skip overlay for that sector category.
- [O] The user page labels it as `순환매 참고`, not `순환매 판단`.
- [O] The API uses the draft image alias layer instead of treating coordinate labels as the source of truth.
- [O] Active image aliases are covered by `web-view-value-qa` so stale or mistyped coordinate labels do not silently remove an overlay marker.
- [O] Highlighted sectors can show read-only stock preview rows with separated report/KRX evidence.
- [O] Highlighted sectors can show read-only ETF preview rows only through an operator-managed mapping file.
- [O] Active ETF mappings are covered by `web-view-value-qa` so stale or mistyped ETF codes do not silently disappear from the user page.
- [O] Active ETF mapping categories are covered by `web-view-value-qa` so an ETF candidate cannot be registered for a category that the overlay cannot display.

## Next Improvement

- Review `data/rotation_image_aliases.json` against the actual Cycle image text before using aliases for ETF/stock candidate previews.
- Expand `data/rotation_etf_candidates.json` only after confirming sector-to-ETF semantics from stored KRX ETF names/index names.
- Add an operator/admin calibration screen later if the fixed image alignment needs manual tuning.
- Expand evidence labels only after category source-date coverage and KRX flow history are stronger.
