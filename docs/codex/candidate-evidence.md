# Candidate Evidence

Candidate evidence DTO, implementation plans, target-progress boundaries, and operator-memo work.

## 판단 구조 개선 — 확정 방향 및 착수 준비 (2026-09-19)

상태: **방향 확정 / 구현 대기**. 사용자 요청은 진행 준비까지이며 아래 단계는 이번 턴의 구현·운영 변경·예약 등록 승인이 아니다. 참조 대화: `판단 구조 개선` (`6aae0602-20d0-83ee-956f-dc46cf694958`).

목표는 관찰 후보를 압축하고, 근거의 관계·반대 근거·미확인 사항으로 사용자의 생각을 확장하는 것이다. 추가 소스나 기사 수 확대보다 운영 누락 원인 정리와 판단 설명 개선을 우선한다. 기존 Top2 검색의 목적 달성은 유지한다.

사용자 우선순위 보충(검수 후 Git 저장 요청): 이후 1차 구현은 기능적 완성도나 전체 단계 완주보다 **의도한 바에 도달하는지 확인하는 최소 구현**에 초점을 둔다. 실제 저장 사례에서 기존 설명과 근거 묶음 설명을 나란히 보고, 중복 기여가 드러나는지·반대 근거와 미확인이 보존되는지·새 확인 관점이 생기는지를 먼저 판단한다. 초기 결과가 유용하지 않으면 기능을 늘려 보완하지 않고 원인과 다음 선택을 제시한다. 첫 사례 확인은 아래 5~10영업일 평가를 대체하지 않으며, 운영 순위 변경의 근거로 사용하지 않는다.

### 확정 계약

- 기존 선정 알고리즘과 정규장 Top2를 OLD 기준선으로 보존한다. 현재 Git 기준은 `da9a467a`이며 실제 착수 시 HEAD와 입력 계약을 다시 확인한다. NEW는 별도 로컬 비교 결과로 시작하며 운영 순위를 교체하지 않는다.
- OLD는 점수 함수만이 아니라 현재 선정 절차 전체다. 해당일 성공 `poll-news` 이벤트의 `target_stock_codes` 최대 2개 중 현재 후보에 존재하는 행을 우선하고, 유효한 정규장 행이 없으면 저장 근거 정렬의 eligible 최대 2개로 fallback한다. 순위 산술 비교와 이 cohort 보존 절차는 별도 결과로 기록한다. Top2는 최대 개수이며 후보가 0/1개면 억지로 채우지 않는다.
- 동일 사건의 재인용 자료는 Evidence Cluster로 묶되, 주제가 같다는 이유만으로 서로 다른 계약·발표를 합치지 않는다. 매칭이 불명확하면 억지로 병합하지 않고 미확인 관계로 남긴다.
- **기사 URL의 신규성, 사건 묶음의 구분, 근거의 독립성은 서로 다르다.** 9월 검색 평가의 26건은 고유 기사이고 계보는 unknown 19 / report_recap 7 / independent 0이었다. 참조 프롬프트의 ‘독립 기사 확보’는 ‘기존 수집 밖 참고 기사 확보’로 정정한다.
- SUPPORT / RISK / UNKNOWN을 별도로 보존한다. 같은 사건 안에도 지지·반대 주장이 공존할 수 있으므로 cluster에 단일 방향을 강제하지 않는다. 정보 부족 UNKNOWN과 출처 독립성 미확인은 별도 속성이다.
- 출처 종류와 계보, 근거 ID, 사건/주제 식별, 종목, 사건일·게시일·수집시각, 병합 사유, 검증 상태, 기존 관점 대비 신규성을 추적한다. 신뢰도·독립성은 근거 없이 숫자로 추정하지 않는다.
- Top2 추가 검색은 확인·반론·질문 확장용이다. 기사 수와 선택된 종목만 받은 추가 검색 정보는 공통 후보 순위 가산에 사용하지 않는다.
- NEW의 공통 후보 생성·eligibility·cluster 수·SUPPORT/RISK 존재 여부·정렬 feature를 만들기 **전에** `source_lane=top2_search`를 제외한다. 제외된 자료는 OLD가 선택한 Top2 설명에만 후결합한다. 단순 건수 비가산만으로 편향이 차단됐다고 주장하지 않는다. OLD에 같은 필터를 소급 적용해 기준선을 바꾸지는 않는다.
- 임의의 30/40/30 비율 모델, 공개 점수, 자동매매, 전체 CLI 재작성, 새 공급자·검색량 확대는 이번 단계에 포함하지 않는다.

### 최소 착수 순서와 산출물

| 단계 | 조사/구현 범위 | 검증 및 종료 조건 |
| --- | --- | --- |
| A 운영 원인 정리 | 16:30 경계, 9/18 Toss 후보 18개 중 2개 누락, success/partial/skipped 의미 추적 | 경계 직전/정각/직후 재현; 부분 수집을 완료로 위장하지 않고 누락 원인과 회복 가능성 기록 |
| B 근거 모델 | 기존 reports / linked news / 저장 수급을 읽는 순수 변환부터 설계 | 동일 사건 재보도와 서로 다른 사건 구분, 혼합 방향 보존, UNKNOWN 비감점 |
| C 최소 NEW | 수급 가산을 근거 축별로 설명하고, 확인된 중복 기여만 제거할 비교안을 별도 제안 | OLD 조건별 기여를 먼저 고정; 두 번째 +2 일괄 삭제 금지; 순위 규칙 선택 전에는 설명 비교만 |
| D 동시점 비교 | 같은 입력으로 OLD/NEW 후보·이유·차이 저장 | cutoff 이후 기사·20:00 수급의 장중 유입 금지, 입력 ID/버전/시각 기록, Top2 편향 방지 |
| E 관찰 판단 | 5영업일 먼저 검토, 자료 부족할 때 최대 10영업일 | 검토 후에만 순위 반영 여부 결정; 자동 승격 없음 |

삽입 위치는 기존 수집·저장 이후, candidate read-model 생성과 operator 비교 출력 사이로 잡는다. 소스 후보는 `cli.py`의 `_web_view_observation_candidate_profile`, `_web_view_candidate_value_profile`, `build_web_view_candidate_evidence_snapshot` 및 기존 `news/linked_evidence.py`다. 초기에는 운영 schema/API 변경 없이 읽기 전용 입력과 로컬 JSON/Markdown 결과를 우선한다. 필요한 함수만 추출하고 모듈을 미리 여러 개 만들지 않는다. 웹뷰 설명 연결은 로컬 비교 결과 확인 뒤 별도 단계다.

OLD/NEW는 같은 날짜뿐 아니라 같은 관측 cutoff와 후보 universe를 사용한다. 장중/장후를 별도 비교하고, 이미 선택된 Top2만 보강된 검색 자료는 설명 평가에만 사용한다. 이 제약 아래 NEW 순위 규칙을 명시할 수 없다면 설명 비교까지만 시행하고 순위 개선을 주장하지 않는다.

현재 `build_web_view_candidate_evidence_snapshot(..., now=...)`는 과거 as-of 입력을 재구성하는 API가 아니다. `now`만 과거로 지정해도 해당일 최종 저장 행이 차단되지 않는다. 순위 비교는 당시 존재했다고 증명 가능한 고정 입력이 있을 때만 시행한다. 각 run에 `input_as_of`, 입력 ID·내용/버전 식별값, 게시·수집·저장시각 및 사용한 선정 이벤트를 기록하고 OLD/NEW가 같은 입력을 읽게 한다. cutoff 이후 정보가 섞인 run은 무효다. 일자별 최종 집계나 덮어쓴 행의 과거 버전을 입증할 수 없으면 그 날짜는 장중 순위 비교에서 제외하고 설명 구조 비교로 구분한다. 20:00 종가는 같은 날짜 정규장 비교에 사용하지 않는다.

### 코드 대조 후 보완한 계약

- OLD 수급 산술: `(수급 지속 and 당일 수급)`은 `priority_signal +2`; 별도로 `(당일 수급 and 리포트 집중 외 why_notable 존재)`는 `sort_signal +2`다. 수급 지속 자체가 why_notable에 포함되므로 두 조건이 함께 성립할 수 있지만, 목표가 변화와 당일 수급만으로도 두 번째 조건이 성립한다. 이 중 어느 조합을 중복 기여로 볼지는 사례로 확인하며 정책 변경은 아직 확정하지 않는다.
- OLD gold 사례는 ① 수급 지속+당일 수급(그 외 근거 없음), ② 목표가 변화+당일 수급(지속 없음; 상승/하락 구분), ③ 리포트 집중+당일 수급(다른 근거 없음)으로 잡는다. `priority_signal`, `sort_signal`, 설명 밀도, 최종 정렬/선정 기여를 구분한다.
- 현재 `_web_view_candidate_value_profile`은 뉴스에 따라 표시 상태를 바꾸지만 `sort_value_signal=base_signal`을 유지한다. 뉴스가 +2/+2의 직접 발생원이라는 참조 예시는 현재 코드와 다르다. 뉴스의 후보 자격 영향 등 다른 경로는 별도 추적한다.
- 최소 모델은 사건 관계(same_event/different_event/unresolved), 주장 방향(SUPPORT/RISK/UNKNOWN), 기존 계보(independent/report_recap/unknown), 검증 상태를 분리한다. 명칭은 구현 시 기존 타입과 맞춘다. 출처 계보가 unknown인 SUPPORT 주장도 보존할 수 있지만 독립 사실로 승격하지 않는다. 검증 상태에는 확인 대상과 근거를 연결하고 제목 매칭 확인을 사건 사실 검증으로 표현하지 않는다.
- 사건 병합은 종목·구체적 사건 식별·시점·명시적 재인용 관계를 우선한다. URL 일치는 동일 기사 식별에 사용하고 광범위한 주제 일치는 자동 병합 근거로 쓰지 않는다. 확신할 식별 정보가 부족하면 unresolved로 둔다. 임베딩/LLM 군집화는 초기 범위에서 제외한다.

### 비례적인 평가 기준

- 결정적 회귀 사례: 같은 사건 2리포트+3뉴스 중복 기여 억제, 다른 사건 보존, SUPPORT/RISK 비상쇄, UNKNOWN 비감점, Top2 검색 건수 비가산, 기존 선정·저장·GET-only 경계 유지.
- 같은 공통 입력에 top2_search 행을 추가/제거해도 NEW의 후보 자격과 순위는 불변이어야 한다. 설명 payload만 달라질 수 있다. eligible 0/1개, SUPPORT 2개+RISK 1개 양쪽 보존, 동일 cutoff 이후 입력 차단도 검사한다.
- 수동 검토는 우선 5영업일의 일별 Top2 설명 10개를 대상으로 한다. 유용한 설명 비율 80% 이상을 초기 유지 기준으로 제안하며, 기존 대비 새 관점 또는 반론 개선 사례 1개 이상을 실제 원문 근거로 제시한다. 순위 변화 자체는 성공 지표가 아니다.
- 위 10개는 최대 표본이다. 선정 후보가 0/1개면 실제 개수를 분모로 공개하고 부족하면 10영업일까지 관찰한다. 원문 근거 연결·주장 구분·구체적인 확인 관점을 사람이 확인한 설명을 유효로 세며, 불확실 판정을 임의 통과 처리하지 않는다. 80%는 설명 유지 기준이며 순위 개선 입증 기준은 아니다.
- 잘못된 사건 병합으로 설명을 왜곡하거나, 미확인 자료를 독립 근거로 승격하거나, 미래 자료를 사용한 비교는 통과 처리하지 않는다. 오류를 고친 범위만 재검증한다.
- 후보 변경은 모두 사유를 추적 가능하게 하고, 표본 부족/차이 없음은 미측정 또는 개선 미입증으로 기록한다. 주가 수익률은 이번 합격 기준이 아니다.
- 실제 검증 시작일과 예약은 구현·오프라인 검사 완료 후 확정한다. 지금은 자동 검증을 등록하지 않는다.

### 남은 선택과 다음 착수 지시

시장 브리핑 09:15/12:00/15:15는 최근 수동 검토 발송 0/3으로 차단된 상태다. 사용할지 결정되기 전에는 활성화하거나 검토 요건을 우회하지 않는다. 이 결정은 A의 다른 원인 조사와 B 설계를 막지 않는다.

이번 재검수의 추천 착수 단위는 **A 원인 재현 + OLD 입력/기여 기록 + 근거 묶음 순수 변환/설명 비교**까지다. 사용자는 이후 진행 여부를 판단한다. NEW 순위 변경 규칙(두 번째 +2 처리 포함)은 OLD 사례를 본 뒤 정하고, 실제 관찰 실행은 입력 시점 재현 가능성과 오프라인 검사 후 결정한다. 이로써 설명 구조 작업을 위해 순위 정책까지 미리 확정할 필요가 없다.

검수 출처: 2026-09-19 기존 ChatGPT 협업 대화 `6a9b8669-9e4c-83e8-aa40-f991fd21e97d`, task `c2c_review_0919`. ChatGPT가 연결된 workspace/HEAD와 문서 diff, 현재 후보 함수를 읽어 제시한 네 가지 핵심 보완 및 OLD/최대 2개 정의를 Codex가 코드 대조 후 반영했다. 이는 준비 문서 검수이며 운영 품질 검증이나 구현 완료 판정이 아니다.

수정본 재검수: 같은 task의 iteration 1에서 ChatGPT가 문서와 diff를 다시 읽고 `DONE — preparation review sufficient / implementation not authorized`로 판정했다. 남은 수급 보너스/NEW 순위 정책은 의도적으로 미확정이며, 준비 문서의 중대한 결함으로 보지 않았다. Codex의 `git diff --check`도 통과했다. 사용자의 이후 진행 판단을 기다리는 상태다.

다음 구현 지시가 오면: 현 상태 확인 → A 재현과 최소 보정 → B/C 결정적 로컬 모델 및 검사 → D 비교 산출물 → E 실제 일정 확정 순서로 진행한다. 운영 데이터 쓰기·서비스/예약 변경·외부 발송은 당시 승인 범위에 맞춘다. 이번 준비 작업에서는 구현과 배포를 시작하지 않았다.

## Current Evidence Ownership (2026-08-23)

- The selected-date stored market reference is Toss 20:00 data. Live Top2 values are labeled `Toss 조회 ... (미저장)` and must not be presented as the selected date's stored fact.
- The 20:00 capture target is every valid stock code in that date's daily summaries, requested in quote batches of at most two. A candidate is complete only when a non-null close baseline and both foreigner and institution flow values are stored.
- The latest successful regular-session `poll-news` target order is the main Top2 cohort for that business date. Toss close rows must not replace that cohort.
- A changed post-close ordering is exposed separately as `close_reassessment` / `종가 재평가` for next-business-day reference. A stored Toss close alone never makes a candidate eligible, and a target-price decrease is not a positive priority signal.
- KRX stock/index rows are historical review data. Event reaction uses the last common pre-event baseline and D0/D+1/D+5/D+20 stock returns; market and excess returns remain null when the same-date benchmark is absent.
- Event reaction is labeled `과거 반응(KRX)`, never changes candidate ordering, and is not a forecast or trading call.
- Older CE-1 planning sections below remain design history where they describe KRX as the current selected-date reference or Top2 as the persistence universe; this section is the current contract.

## Included sections
- Candidate Evidence Contract
- Candidate Evidence Plan
- Candidate Evidence Batching Implementation Plan
- Target Price Progress Plan
- Operator Memo Progress Implementation Plan
- Operator Memo Surface Reflection Implementation Plan
- Observation Candidate Recommendation Goal Prompt

<!-- Merged from: docs/codex/candidate-evidence.md -->
## Candidate Evidence Contract

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
| Stock market reference | Toss OpenAPI stored snapshot | `stock_market_daily`, `repository.list_stock_market_daily_for_codes(..., source="toss_openapi")` | Exact-date price/change/volume/turnover when stored |
| Stock investor flow | Toss OpenAPI | `stock_investor_flow_daily`, bounded Top2 projection | Stock-level flow reference when stored or explicitly queried; query results do not alter ordering |
| Market investor flow | Toss OpenAPI | `market_investor_flow_daily`, Toss market context | Top-level provisional market context, not a score |
| Legacy KRX flow/ranking | Existing stored KRX rows | historical flow tables | Historical review only; absence is not a current candidate defect |
| Category rollup | Snapshot-aware taxonomy layer | `repository.list_category_rollups_by_display_name_for_business_date(...)` | Separate context only |
| ETF reference | Toss OpenAPI stored snapshot | `etf_daily_snapshots`, `repository.list_etf_daily_by_turnover(..., source="toss_openapi")` | Not part of a stock candidate row; show only when actual ETF rows exist |

Out of scope for CE-1:

- live fetch
- scheduled ingest changes
- DB schema changes
- writing candidate rows into SQLite
- trading-recommendation wording
- public numeric score, investment grade, or weight fields

Future intraday boundary:

- A future real-time or broker-origin probe must start outside this DTO as a lab/staging read-only lane.
- The first candidate scope is only the top-2 `우선 확인` candidates, at a coarse cadence such as 5 minutes only after source burden is reviewed.
- Read-only means no production DB writes, no Telegram/scheduler automation, no `admin-gui` control path, no broker secrets, and no order routing. It does not mean the signal is display-only forever.
- Current approved exception: Toss `getStockInvestorTrading` supplies only same-day provisional foreigner/institution net-volume beside the server-derived Top2, with provider update time. It remains context-only: it is not stored and cannot change candidate ordering or Top2 composition.
- After a source is approved, verified intraday price/turnover/index references are allowed to affect observation priority, top-2 `우선 확인` ordering, and main-card emphasis as observation-candidate recommendation signals.
- Those signals must still stay below trading advice: no public numeric score, investment grade, buy/sell instruction, entry/exit, target return, conviction, broker execution, or order-routing wording.
- This restriction is for the public CE-1/web-view contract. It does not reject a future operator-only decision-support or execution-lab lane after real-time source stability and safety gates are proven.
- Stored CE-1 wording must therefore keep KRX/report/flow values labeled as stored references, not live/current intraday facts.
- The public `web-view` may show a disabled top-2 `장중 참고` slot before a source is approved. While disabled it must use `source_configured=false`, `live_fetch=false`, and `affects_ordering=false`; those values describe current source absence, not the future ordering policy.

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
| `evidence_layers.primary` | Short public reasons copied from `why_notable` | derived display projection | report, target-revision, and `[12009]` flow-persistence reasons only; no internal sort vocabulary |
| `evidence_layers.support` | Stored context that supports the reasons | KRX/price-volume/rank derived display projection | KRX price, turnover, 52-week position, volume-position labels, and `[12010]` rank-reference labels only when stored evidence exists |
| `evidence_layers.gap` | Missing public evidence copied from `missing_information` | derived display projection | missing context, not negative evidence |
| `value_profile` | Public-safe observation value state | candidate/news/KRX/flow/Toss reference mix | labels whether the row is `뉴스 근거 확인`, `정보 보강`, `뉴스 매칭 없음`, `실시간 확인 대기`, or stored-reference-only; no numeric score |
| `intraday_reference` | Top-2-only future real-time reference slot | disabled source placeholder now; approved intraday source later | disabled placeholders use `source_configured=false`, `live_fetch=false`, `affects_ordering=false`; approved sources may set `affects_ordering=true` only for observation priority/display ordering, never trading execution |
| `quality_flags` | Missing/fallback markers | derived | required |
| `evidence_notes` | Flat fact labels only | derived | no score text |

Internal sort and operator diagnostics are separate from public labels.

- `why_notable` and `missing_information` are public-visible display vocabulary for `web-view`.
- Sort-only signals such as broker breadth, target-range availability, turnover availability, and price/volume position must not be exposed by relying on frontend filtering.
- Every candidate signal must be classified as `rank-driving evidence`, `context-only support`, or `gap-only missing context` before it is added to the DTO.
- `rank-driving evidence` is limited to report focus, stored report target revision, exact-date `[12009]` flow-persistence evidence, and public-safe `value_profile` adjustments that are visibly derived from news/KRX/flow/Toss reference state.
- `context-only support` includes stored KRX price/turnover, 52-week position, volume position, target range/opinion details, and `[12010]` rank reference.
- `gap-only missing context` includes selected-date KRX missing, selected-date `[12009]` stock flow missing, and target/opinion/price-volume context missing.
- Context-only and gap-only signals must not change public row ordering, `observation_priority`, or top-2 composition by themselves. They may lower a target-only row only when the visible `value_profile` also explains that news matching, KRX, flow, or Toss evidence is missing.
- `[12010]` rank presence is a reference-level support signal only. It may appear publicly as a cautious rank-reference label in `evidence_layers.support`, but it must not appear in `why_notable` or `evidence_layers.primary`, and it must not dominate candidates that have composite stored evidence.
- Flow-persistence wording is public-primary evidence only when selected-date `[12009]` stock flow exists. Without stock-level flow rows, persistence remains internal/readiness context and the public card should show the flow gap as missing context.
- Exact-date `[12009]` stock flow plus a public non-report reason such as target revision is stronger observation evidence than `[12010]` rank presence without stock-level flow.
- `missing_stock_flow_reference` is an evidence gap, not negative evidence about the stock.
- Direct/caution/market-context news evidence may raise a row's observation emphasis when it is shown through public-safe labels and counts. A completed news collection with no matched article should not remain equal to a candidate with direct news support.
- A public top-2 card may show `판단 상태` text from `value_profile`, but it must not expose a numeric score, internal weight, raw sentiment/impact label, or operator recommendation-support vocabulary.
- Operator/readiness commands may inspect internal candidate signals, but those counts must be named separately from visible label counts.
- No hidden factor may determine public inclusion or ordering unless a public-safe rank-driving label for the same factor is visible on the row.
- `candidate-evidence-readiness` should report visible label counts and internal signal counts separately so operator review and friend-facing cards do not use different hidden vocabularies.
- `candidate-evidence-readiness` may also report operator-only `explanation_quality` diagnostics such as `report_only_candidate`, `missing_krx_reference`, `missing_stock_flow_reference`, `rank_without_stock_flow`, `missing_price_volume_context`, `missing_52w_position`, and `composite_evidence`. These diagnostics are for audit/readiness only and must not appear in the public `/api/candidate-evidence` response.
- `candidate-evidence-readiness` may also summarize top-2-only maturity through operator-only fields such as `top_candidate_explanation_quality_counts`, `top_candidate_support_counts`, `top_candidate_gap_counts`, `top_candidate_next_evidence_gap_counts`, `top_candidate_review_reason_counts`, `top_candidate_review_priority_counts`, `top_candidate_review_date_count`, and per-date `top_candidate_maturity`. These fields identify which recent dates need stored-evidence backfill or review; they are not public DTO fields.
- The public `/api/candidate-evidence` projection should stay thinner than the internal review row. Public rows keep display-ready labels and evidence boxes, but must not expose `quality_flags`, `evidence_notes`, `opinion_summary`, `report_summary.broker_count`, `report_summary.broker_display`, `report_summary.dominant_opinion`, `report_intensity.five_business_day_broker_count`, `target_price_revision.previous_broker_count`, or internal sort vocabulary such as broker breadth in public policy copy. Those fields may remain available only when the builder is called for operator/readiness review with internal diagnostics enabled.

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
Public rank wording should stay reference-framed, such as `외국인 순매수 상위 참고`, because it is stored `[12010]` context and may coexist with missing stock-level `[12009]` flow.
The label belongs in `evidence_layers.support`, not `why_notable` or `evidence_layers.primary`, and it must not drive public ordering by itself.

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


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Candidate Evidence Plan

## Purpose

This document defines the safe path from current report/flow/reference data to future `관찰 후보 추천` views.

It approves observation-candidate recommendation and priority ordering, but it does not approve trading recommendations, public numeric scoring, investment grades, or buy/sell judgment.

The exact CE-1 DTO and alias-mapping contract is fixed in [candidate-evidence.md](/docs/codex/candidate-evidence.md).

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


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Candidate Evidence Batching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `web-view` observation candidate latency by batching stored-data lookups inside `build_web_view_candidate_evidence_snapshot` without changing public wording, trading boundaries, or KRX ingest scope.

**Architecture:** Keep the public DTO shape stable around `rows`, `why_notable`, `missing_information`, and non-numeric `observation_priority`. Add an internal per-date candidate context that preloads report intensity, target revision, same-date flow, flow windows, price/volume history, target-progress baseline rows, and validation market series for all candidate stock codes. Existing single-stock helper logic remains the formatting/reference contract, but candidate snapshot construction should read from the preloaded context instead of opening repeated per-stock queries.

**Tech Stack:** Python, SQLite repository access, pytest, existing `stock_monitor.cli` web-view DTO builders.

---

## Scope

In scope:

- Optimize stored read-only candidate evidence generation.
- Keep `web-view` GET-only/read-only.
- Keep `rows` as the canonical candidate-evidence response key.
- Keep `admin-gui`, secrets, DB path, scheduler state, and operator-only data out of `web-view`.
- Preserve observation wording and block public score/grade/trading-call wording.

Out of scope:

- No KRX network calls.
- No broad ingest or all-stock collection.
- No `[12008]`/`[12010]` automation.
- No Telegram or scheduler changes.
- No public numeric score, grade, buy/sell, entry/exit, take-profit, target-return, or conviction copy.

## Files

- Modify: `src/stock_monitor/cli.py`
  - Add internal candidate evidence batching helpers.
  - Update `build_web_view_candidate_evidence_snapshot` to use the preloaded context.
- Modify: `tests/test_web_view.py`
  - Add a regression test that counts repository connection openings while building candidate evidence for multiple stocks.
  - Preserve existing public DTO assertions.
- Modify: `docs/codex/operating-guide.md`
  - Record the batching result and measured mini PC impact.
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`
  - Add the source-sync note for the batching pass.

## Tasks

### Task 1: Add RED Query-Budget Test

**Files:**

- Modify: `tests/test_web_view.py`

- [x] **Step 1: Write the failing test**

Add a focused test near the candidate-evidence tests:

```python
def test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    reports = []
    market_rows = []
    flow_rows = []
    for index, code in enumerate(("005930", "000660", "035420"), start=1):
        stock_name = f"테스트{index}"
        reports.append(Report(... two same-date reports with target_price_value ...))
        market_rows.append(StockMarketDailySnapshot(... business_date=business_date, stock_code=code ...))
        flow_rows.append(StockInvestorFlowDaily(... business_date=business_date, stock_code=code, investor_type="외국인" ...))
    repository.insert_reports(reports)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(market_rows)
    repository.upsert_stock_investor_flow_daily(flow_rows)
    connect_count = 0
    original_connect = repository.connect

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(repository, "connect", counting_connect)
    payload = cli_module.build_web_view_candidate_evidence_snapshot(config, repository, business_date=business_date, limit=3)

    assert [row["stock_code"] for row in payload["rows"]] == ["005930", "000660", "035420"]
    assert connect_count <= 14
```

Use real model constructors already imported in the file. The current implementation should exceed the budget because it repeatedly opens connections per stock.

- [x] **Step 2: Run the RED test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py::test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks -q
```

Expected: fail on `connect_count <= 14`.

### Task 2: Add Candidate Evidence Batch Context

**Files:**

- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Add internal helper functions**

Add helpers that load grouped stored data:

```python
def _build_candidate_evidence_batch_context(repository, *, business_date, summaries, holiday_overrides):
    stock_codes = [summary.stock_code for summary in summaries if summary.stock_code]
    return {
        "same_day_flow_by_code": _load_candidate_same_day_flow_by_code(repository, business_date, stock_codes),
        "flow_window_rows_by_code": _load_candidate_flow_window_rows_by_code(repository, business_date, stock_codes),
        "market_history_by_code": _load_candidate_market_history_by_code(repository, business_date, stock_codes),
        "first_target_date_by_code": _load_candidate_first_target_dates_by_code(repository, business_date, stock_codes),
        "previous_target_by_code": _load_candidate_previous_target_by_code(repository, business_date, stock_codes),
        "report_intensity_by_code": _load_candidate_report_intensity_by_code(repository, business_date, summaries, holiday_overrides),
    }
```

Keep helper names internal and local to `cli.py` because this is a web-view DTO optimization, not a repository-wide contract yet.

- [x] **Step 2: Add cached variants of existing single-stock computations**

Add variants that accept preloaded rows:

```python
def _web_view_stock_flow_window_item_from_rows(summary, *, business_date, rows):
    ...

def _web_view_price_volume_position_item_from_rows(summary, *, rows):
    ...

def _web_view_target_price_progress_from_context(summary, market_reference, *, baseline_date, baseline_market, market_series):
    ...
```

Keep output dictionaries byte-for-byte compatible with the existing helper outputs where possible.

### Task 3: Wire Builder To Context

**Files:**

- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Build context once**

Inside `build_web_view_candidate_evidence_snapshot`, after `market_refs` and rank rows are prepared, build the batch context once for all summaries.

- [x] **Step 2: Replace per-stock reads**

For each summary:

- use `same_day_flow_by_code[stock_code]` instead of `repository.list_stock_investor_flow_daily(...)`
- use cached report intensity and target revision
- use cached flow window rows for `flow_window_reference`
- use cached market history rows for price/volume reference
- use cached baseline date/baseline market/market series for target progress

- [x] **Step 3: Preserve public DTO**

Keep these fields stable:

- `rows`
- `observation_priority`
- `why_notable`
- `missing_information`
- `report_summary`
- `target_price_progress`
- `flow_window_reference`
- `price_volume_reference`

Do not restore the removed `candidates` duplicate response key.

### Task 4: Verify And Document

**Files:**

- Modify: `docs/codex/operating-guide.md`
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`

- [x] **Step 1: Run focused tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py::test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks tests\test_web_view.py::test_web_view_candidate_evidence_marks_missing_information_without_public_score tests\test_web_view.py::test_web_view_server_serves_get_only_archive -q
```

Expected: all pass.

- [x] **Step 2: Run relevant regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py tests\test_cli_commands.py -q
```

Expected: all pass.

- [x] **Step 3: Run QA/smoke**

```powershell
.venv\Scripts\python.exe -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json
.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json
```

Expected: `issue_count=0`.

- [x] **Step 4: Measure**

Run a local timing probe for latest report date and record:

- candidate evidence bytes
- candidate evidence elapsed time
- daily payload elapsed time if affected

- [x] **Step 5: Restart runtime**

Restart only the local `web-view` runtime on `{LOCAL_WEB_VIEW_TARGET}`, then verify:

```powershell
Invoke-WebRequest -UseBasicParsing {LOCAL_WEB_VIEW_TARGET}/health
.venv\Scripts\python.exe -m stock_monitor external-web-view-smoke --url https://web-view.example.invalid --date 2026-05-15 --json
```

Expected: local health `200`, external smoke `issue_count=0`.

## Self-Review

- No new public trading language is introduced.
- No network collection path is changed.
- No scheduler or Telegram path is changed.
- The plan is a single implementation unit: candidate-evidence read performance.
- The test proves behavior through real repository calls and should fail before batching.

## Result

- RED result before implementation: `connect_count == 33`, above the query budget.
- GREEN result after implementation: `test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks` passed and the full relevant regression passed with `278 passed`.
- Latest mini PC measurement for `2026-05-15`: daily payload about `49KB` / `1.1s`, `candidate-evidence?limit=20` about `95KB` / `0.3s`.
- `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json`: `issue_count=0`; warnings were expected stored-data coverage notes for `2026-05-18` KRX snapshot availability and stock code `351020` KRX metadata.
- `web-view-browser-smoke --date latest --json`: `issue_count=0` across desktop, tablet, large mobile, and mobile.
- Local runtime was restarted on `{LOCAL_WEB_VIEW_TARGET}` with PID `9016`; `/health` returned `200`.
- `external-web-view-smoke --url https://web-view.example.invalid --date 2026-05-15 --json`: `issue_count=0`.


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Target Price Progress Plan

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


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Operator Memo Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current operator memo backlog into a checkable status surface and create first implementation artifacts for the open `2026-05-18` memos.

**Architecture:** Keep operator memos as local rough ideas in `data/operator_memos.md`, but add read-only CLI surfaces that can prove whether a memo has moved beyond discussion. The implementation adds no scheduler, Telegram send, live network fetch, public score, trading recommendation, secret output, or `admin-gui` exposure.

**Tech Stack:** Python CLI, SQLite repository reads, pytest, Markdown documentation.

---

## Scope

In scope:

- Parse and report all operator memo statuses.
- Add a stored-data one-line market commentary practice preview.
- Add a local photo inbox status command for future example screenshots.
- Add a read-only periodic data needs audit.
- Update memo status docs once real artifacts exist.

Out of scope:

- No Telegram sending.
- No scheduler registration.
- No live KRX/Naver/browser fetch.
- No broad ingest, all-stock collection, or `[12008]`/`[12010]` automation.
- No public numeric score, grade, buy/sell, entry/exit, target-return, or conviction wording.

## Current Memo Check

`data/operator_memos.md` now has:

- `[O]` completed: 7
- `[△]` partial/foundation: 9
- `[ ]` not started: 1

Open `[ ]` memo:

- `26.05.08 00:00` US market API source investigation: still intentionally deferred until domestic operation is stable.

This implementation moved the three `2026-05-18` open memos to partial by creating first artifacts. US market expansion remains explicitly deferred by canonical scope.

## Files

- Modify: `src/stock_monitor/cli.py`
  - Add `operator-memo-status`.
  - Add `market-commentary-practice`.
  - Add `operator-photo-inbox-status`.
  - Add `periodic-data-needs-audit`.
- Modify: `tests/test_cli_commands.py`
  - Add focused tests for the new read-only helpers.
- Modify: `data/operator_memos.md`
  - Reclassify the three `2026-05-18` memos from `[ ]` to `[△]` after the artifacts pass tests.
- Modify: `docs/codex/operating-guide.md`
  - Record the memo-progress implementation pass.
- Modify: `docs/codex/operating-guide.md`
  - Update `Operator Memo Status` with the new artifact names.
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`
  - Add source-sync note for main PC.

## Tasks

### Task 1: Add Memo Status Surface

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Add tests that create a temporary `operator_memos.md`, call the parser/snapshot helper, and assert status counts plus the open memo rows are present.

- [x] **Step 2: Run the RED tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_cli_commands.py::test_operator_memo_status_snapshot_parses_status_counts -q
```

Expected: fail because the helper does not exist yet.

- [x] **Step 3: Implement parser and CLI**

Implement a read-only parser for memo lines shaped like:

```text
- [△] 26.05.18 12:01 | 값 정제하기...
```

Add `operator-memo-status --json`.

- [x] **Step 4: Run GREEN tests**

Run the focused memo-status tests and confirm they pass.

### Task 2: Add One-Line Commentary Practice

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Create stored reports, summaries, and KRX index rows, then assert `market-commentary-practice` returns exactly three neutral phases: `opening`, `midday`, and `preclose`.

- [x] **Step 2: Implement read-only preview**

Use stored report count, summary stock count, and KOSPI/KOSDAQ stored index references to produce neutral one-line comments. Use labels such as `장초반`, `점심`, and `장 마감 전`; do not output buy/sell, score, grade, conviction, or strategy wording.

### Task 3: Add Photo Inbox Status

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Create an image-like file under a temp inbox and assert the status command lists it without reading image contents.

- [x] **Step 2: Implement read-only inbox status**

Default the inbox to `data/operator_photo_inbox`. Report path, file count, allowed extensions, and next action. Do not upload, expose, or transform files.

### Task 4: Add Periodic Data Needs Audit

**Files:**

- Modify: `tests/test_cli_commands.py`
- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Write the failing tests**

Seed stored report summaries and market index rows, then assert the audit identifies KOSPI/KOSDAQ index coverage as already stored through KRX Open API snapshots and keeps investor-flow broad collection blocked.

- [x] **Step 2: Implement read-only audit**

Return machine-readable rows for report, KRX index, stock/ETF daily, `[12009]` mentioned-stock flow, and blocked broad flow/ranking sources.

### Task 5: Document And Verify

**Files:**

- Modify: `data/operator_memos.md`
- Modify: `docs/codex/operating-guide.md`
- Modify: `docs/codex/operating-guide.md`
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`

- [x] **Step 1: Update memo statuses**

Mark the three `2026-05-18` memos as `[△]` with the implemented artifact command names.

- [x] **Step 2: Run verification**

Run:

```powershell
.venv\Scripts\python.exe -m py_compile src\stock_monitor\cli.py tests\test_cli_commands.py
.venv\Scripts\python.exe -m pytest tests\test_cli_commands.py -q
.venv\Scripts\python.exe -m stock_monitor operator-memo-status --json
.venv\Scripts\python.exe -m stock_monitor market-commentary-practice --date latest --json
.venv\Scripts\python.exe -m stock_monitor operator-photo-inbox-status --json
.venv\Scripts\python.exe -m stock_monitor periodic-data-needs-audit --date latest --json
```

Expected: tests pass and all four CLI commands are read-only.

## Self-Review

- The plan handles all current memos by status and creates real artifacts for the three open domestic-operation memos.
- US market API expansion remains deferred because it is outside current domestic mini-PC scope.
- All new commands are read-only and local.
- No public trading-decision wording or broader KRX automation is introduced.

## Result

- Added `operator-memo-status`, `market-commentary-practice`, `operator-photo-inbox-status`, and `periodic-data-needs-audit`.
- Added focused tests for all four new read-only helpers.
- Created local-only inbox documentation at `data/operator_photo_inbox/README.md`.
- Updated `data/operator_memos.md` so implemented domestic-operation artifacts are no longer `[ ]`.
- Final memo status: done `7`, partial `9`, open `1`, other `0`.
- The only remaining open memo is US market API expansion, intentionally deferred from the domestic mini-PC scope.
- Verification passed:
  - `py_compile src\stock_monitor\cli.py tests\test_cli_commands.py`
  - `pytest tests\test_cli_commands.py -q`: `252 passed`
  - `pytest tests\test_web_view.py -q`: `30 passed`
  - all four new CLI commands returned read-only JSON successfully.


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Operator Memo Surface Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move partial operator memo artifacts from CLI-only checks into actual user/operator surfaces and verification loops.

**Architecture:** Keep new behavior read-only except for explicit Telegram photo intake, which stores only operator-sent files into the local photo inbox. Web-view receives stored one-line commentary and periodic-data status blocks through existing daily DTOs; Telegram receives safe one-line commentary through a command response and optional caption-based `/사진` intake. No scheduler registration, broad KRX ingest, public scoring, or trading-decision copy is added.

**Tech Stack:** Python CLI, Telegram Bot API, SQLite repository reads, existing web-view HTML/JS, pytest.

---

## Tasks

### Task 1: One-Line Commentary On Web-View And Telegram

- [x] Add failing tests that daily web-view DTO exposes `market_commentary`.
- [x] Add failing tests that Telegram `/한줄` returns three safe one-line comments.
- [x] Implement `market_commentary` in `build_web_view_daily_snapshot`.
- [x] Render the comments in the top `오늘 읽을 요약` card.
- [x] Add Telegram command parser support for `/한줄`, `/코멘트`, and `/시장코멘트`.

### Task 2: Telegram Photo Intake

- [x] Add failing tests for `/사진` command parsing.
- [x] Add failing tests for saving a photo/document from Telegram update metadata into `data/operator_photo_inbox`.
- [x] Add Telegram file helpers for `getFile` and file download.
- [x] Support both caption-based `/사진 설명` and pending `/사진 설명` then next photo.
- [x] Keep replay safety through control-state applied update ids.

### Task 3: Periodic Data Needs On Operator/User Surfaces

- [x] Add failing tests that daily web-view DTO exposes `periodic_data_needs`.
- [x] Render a compact status in `시장` or top summary without exposing admin state or secrets.
- [x] Include the same read-only block in `operator-status`.

### Task 4: Docs, Memo Status, QA

- [x] Update `operator_memos.md`, `operating-guide.md`, `operating-guide.md`, and mini-PC handoff.
- [x] Run focused tests, `tests/test_cli_commands.py`, `tests/test_control.py`, `tests/test_telegram_command_replay.py`, `tests/test_web_view.py`.
- [x] Run `web-view-value-qa` and `web-view-browser-smoke`.

## Boundaries

- `admin-gui` remains private.
- `web-view` remains GET-only/read-only.
- Telegram photo intake writes only local files sent by the configured chat.
- `.env`, token, KRX key, access-code, password, cookie, and DB path are not printed.
- `[12008]` and `[12010]` automation remains blocked.
- Public score, grade, buy/sell, entry/exit, target-return, and conviction wording remains blocked.


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Observation Candidate Recommendation Goal Prompt

Use this prompt when starting the next implementation pass for stored-data based observation-candidate recommendation.

```text
/goal {PROJECT_ROOT} only.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 작업해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

현재 위치는 미니PC다.
이 미니PC는 운영 기준이고, 메인PC로 넘길 변경 묶음은 handoff/mini_pc_changes/에 정리한다.

비밀값 주의:
.env, Telegram token, KRX key, access-code, password, cookie는 출력하지 마.
admin-gui는 외부 공유 금지.
web-view만 외부 공유 후보.
KRX Data Marketplace 자동 수집은 리포트 언급 종목 [12009] 최근 31일 보강만 허용한다.
broad ingest, 전체 종목 수집, [12008]/[12010] 자동 수집은 금지한다.

이번 목표:
저장된 리포트/KRX/수급 데이터 기준으로 web-view의 관찰 후보 추천 v1을 구현해줘.

제품 경계:
이 프로젝트는 매매 추천은 하지 않지만, 관찰 대상을 추천한다.
허용: 오늘의 관찰 후보, 우선 확인, 관찰 우선순위, 관심도 높은 흐름, 왜 눈에 띄는지, 리포트 집중, 수급 참고, 과열 참고, 시장 분위기, 확인 포인트.
금지: 매수 추천, 매도 추천, 지금 사라/팔아라, 진입가, 청산가, 익절가, 목표 수익률, 확신도, 투자등급, 오를 종목 단정, 자동 매매/전략 제안처럼 보이는 문구.

구현 요구:
1. 먼저 AGENTS.md, docs/codex/documentation-index.md, docs/codex/operating-guide.md, docs/codex/operating-guide.md, docs/codex/surface-guide.md, docs/codex/data-governance.md를 읽어.
2. 현재 candidate_evidence와 observation_summary DTO/API/UI 구조를 확인해.
3. 내부 정렬 기준은 observation_priority 또는 evidence_density처럼 공개 숫자 점수로 보이지 않는 이름을 사용해.
4. v1 public surface에는 숫자 점수/등급을 노출하지 말고, 정렬된 목록과 근거 문장만 보여줘.
5. web-view에는 오늘의 관찰 후보, 우선 확인, 왜 눈에 띄는지, 부족한 정보가 보이게 해.
6. 부족한 데이터가 있으면 숨기지 말고 부족한 정보로 표시해.
7. admin-gui/control surface/secret/DB path/operator-only 상태는 web-view에 노출하지 마.
8. Telegram 발송/스케줄러 변경은 이번 목표에 포함하지 마. 먼저 web-view read-only 표시만 고도화해.

관찰 후보 v1에서 우선 검토할 근거:
- 리포트 집중 기준
- 브로커 폭은 내부 정렬/진단 참고로만 사용하고 public `왜 눈에 띄는지` 알약에는 노출하지 않음
- 목표가 변화
- 외국인/기관 5/10/20/31일 누적 수급
- 수급 전환 지속일
- 거래대금/거래량 증가율
- 20/60일 가격 위치
- 52주 위치
- 업종/테마 동반성
- 제외할 종목 조건

검증:
- rg로 금지 문구가 public web-view/Telegram copy에 새로 생기지 않았는지 확인
- python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json
- python -m stock_monitor web-view-browser-smoke --date latest --json
- 관련 pytest 최소 실행

최종 보고:
1. 구현한 파일 목록
2. 관찰 후보 추천 v1의 정렬 기준 요약
3. public surface에 표시되는 문구 예시
4. 부족한 정보로 처리한 항목
5. 검증 명령과 결과
6. 메인PC로 넘길 handoff/mini_pc_changes/ 반영 필요 여부
```
