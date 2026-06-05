# Candidate Evidence Plan

## Purpose

This document defines the safe path from current report/flow/reference data to future `관찰 후보 추천` views.

It approves observation-candidate recommendation and priority ordering, but it does not approve trading recommendations, public numeric scoring, investment grades, or buy/sell judgment.

The exact CE-1 DTO and alias-mapping contract is fixed in [candidate-evidence-contract.md](/docs/codex/contracts/candidate-evidence-contract.md).

Current rule:

- Use `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `후보`, `참고`, `근거`, or `관찰`.
- Do not use `매수 추천`, `매도 추천`, `지금 사라/팔아라`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, `투자등급`, public numeric `점수`, or automated strategy wording.
- Keep report evidence, KRX market reference, investor flow, category/rotation context, and ETF context as separate layers.

## Requested Ideas

| Memo | Intended Outcome | Current Decision |
| --- | --- | --- |
| 리포트와 수급을 통해 다음날 기준 2종목 정도를 추천하고자 한다면 어떤 가중치가 필요한지 | Next-day observation-candidate shortlist | Build `candidate_evidence` first, then expose it as observation-candidate recommendation with no trading-call wording. |
| 순환매 기준 표기가 완성된 이후 해당 순환매쪽 ETF와 종목을 각 1개씩 뽑아낼 수 있는지 | Rotation-linked ETF and stock candidate preview | Build sector/ETF/stock evidence preview first. No final single pick yet. |

## Work That Can Start Now

| Work | Why It Is Safe Now | Output |
| --- | --- | --- |
| Define evidence fields | Uses existing stored data and does not change scoring policy. | First computed `candidate_evidence` DTO/API exists. |
| Add read-only preview plan | Shows why a row appears without saying it is a buy. | Future visible `web-view` candidate evidence section. |
| Define exclusion rules | Prevents bad rows from polluting candidate previews. | Missing/low-quality data guard list. |
| Define rotation alias table | Needed before image text can map to current 업종/테마 labels. | Manual alias map plan. |
| Define ETF/category mapping need | Current ETF data exists, but sector-to-ETF relation is not canonical. | Operator-managed mapping plan. |

## Work That Must Wait

| Work | Blocker |
| --- | --- |
| Weighted score | Needs enough history and an agreed policy for weights. |
| Public trading recommendation or scored investment decision | Out of scope; observation-candidate recommendation can proceed without this. |
| Rotation ETF/stock one-pick | Needs alias map, ETF mapping, and evidence coverage first. |
| Telegram candidate alert | Needs user-facing preview stability and false-positive review first. |
| Auto buy/sell wording | Out of scope. |

## Candidate Evidence Fields

First pass should produce a read-only row per stock/date.

| Field | Source Layer | Display Rule |
| --- | --- | --- |
| `business_date` | App business date | Required. |
| `stock_code`, `stock_name` | Report summary / KRX stock master | Required. |
| `category_display_name` | Category snapshot | Optional; label fallback if not dated. |
| `report_count` | Naver reports | Count only stored reports. |
| `broker_count` | Naver reports | Count unique brokers. |
| `target_price_range` | Parsed report target prices | Exclude missing values from range. |
| `opinion_summary` | Parsed report opinions | Preserve `의견 없음` as display-only detail. |
| `price_change_percent` | KRX stock daily | Observation only. |
| `turnover` | KRX stock daily | Observation only. |
| `volume` | KRX stock daily | Observation only. |
| `foreign_net`, `institution_net`, `individual_net` | KRX Data Marketplace `[12009]` | Observation only; retain units. |
| `market_flow_context` | KRX Data Marketplace `[12008]` | Market background only. |
| `net_buy_rank_context` | KRX Data Marketplace `[12010]` | Ranking context only. |
| `evidence_notes` | Derived display text | Explain facts without scoring. |

## Exclusion Rules

| Rule | Reason |
| --- | --- |
| Exclude stocks with no valid stock code from candidate preview. | KRX joins and flow lookup become unreliable. |
| Keep report rows with missing target/opinion in detail, but do not let them improve evidence strength. | Missing values should not boost a candidate. |
| Do not rank by report count alone. | Report activity without price/flow context can mislead. |
| Do not rank by investor flow alone. | 수급 is a supporting signal, not a thesis. |
| Mark category fallback explicitly. | Today's category mapping must not silently explain old dates. |
| Mark insufficient KRX flow coverage. | Absence of flow data is not neutral evidence. |

## Rotation ETF / Stock Candidate Preview

This is a separate preview from the stock candidate evidence table.

| Step | Needed Data | Status |
| --- | --- | --- |
| 1 | Cycle image text labels | Need manual extraction or OCR review. |
| 2 | Alias from image label to 업종 display name | Not started. |
| 3 | 업종 coordinate map | First pass exists for some categories. |
| 4 | 업종 -> ETF candidates | Needs operator-managed mapping or verified source. |
| 5 | 업종 -> stock candidates | Can derive from report/category/KRX data after alias is stable. |
| 6 | Evidence preview | Can show report count, turnover, flow, ETF trend separately. |
| 7 | One ETF + one stock final pick | Deferred until history and policy are stronger. |

## Proposed Implementation Stages

| Stage | Goal | Completion Criteria |
| --- | --- | --- |
| CE-0 | Document policy and field contract | This document exists and is linked from roadmap/current-work. |
| CE-1 | Add read-only candidate evidence builder | Repository/DTO returns separated evidence rows for a date. Implemented as computed `web-view` DTO/API. |
| CE-2 | Add web-view preview table | User page shows `오늘의 관찰 후보` and `관찰 후보 근거`, not trading recommendations. |
| CE-3 | Add rotation alias table draft | Manual image-label-to-category mapping exists as `data/rotation_image_aliases.json` draft. |
| CE-4 | Add ETF/category mapping draft | Operator-managed ETF candidates per 업종 exist. |
| CE-5 | Add rotation candidate preview | Shows ETF/stock candidates by rotation label with evidence. |
| CE-6 | Evaluate simple weights offline | Only after enough history and manual review. |

## UI Copy Rules

Use:

- `오늘의 관찰 후보`
- `우선 확인`
- `관찰 우선순위`
- `관심도 높은 흐름`
- `왜 눈에 띄는지`
- `관찰 후보`
- `후보 근거`
- `리포트 근거`
- `수급 참고`
- `거래대금 참고`
- `순환매 참고`

Avoid:

- `매수 추천`
- `매도 추천`
- `매수 후보`
- `지금 사라/팔아라`
- `진입가`
- `청산가`
- `익절가`
- `목표 수익률`
- `확신도`
- `투자등급`
- public numeric `점수`
- `확정`

## Next Action

The next safe implementation unit is `CE-2`: review the read-only `candidate_evidence` DTO across several stored dates, then add a compact visible `오늘의 관찰 후보` / `우선 확인` section with `왜 눈에 띄는지` reason text.

Do not add Telegram alerts, public numeric scoring, investment grades, trading final picks, or weight fields in `CE-2`.
