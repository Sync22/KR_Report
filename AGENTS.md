# AGENTS.md

## Behavioral Priority

이 파일의 최우선 기준은 아래 네 가지다.

1. 생각부터 한다.
   - 가정을 숨기지 않는다.
   - 해석이 여러 개면 조용히 하나를 고르지 않는다.
   - 더 단순한 길이 있으면 먼저 말한다.
2. 단순성을 우선한다.
   - 요청하지 않은 기능, 추상화, 유연성, 방어 코드는 넣지 않는다.
   - 과한 구현이면 줄인다.
3. 수술식으로 바꾼다.
   - 필요한 파일과 줄만 건드린다.
   - 인접 리팩터링, 포맷 정리, 주석 손질을 멋대로 하지 않는다.
   - 내 변경이 만든 찌꺼기만 치운다.
4. 검증 가능한 목표로 끝낸다.
   - 재현, 테스트, 명령 출력 같은 확인 기준을 먼저 둔다.
   - "작동할 것 같다"는 완료 기준이 아니다.

## Scope

이 handoff는 `{PROJECT_ROOT}`에만 적용된다.

- 프로젝트 루트: `{PROJECT_ROOT}`
- 문서 루트: `{PROJECT_ROOT}\docs\codex`

다른 폴더나 과거 경로를 기준으로 상태를 추론하지 않는다.

## Default Working Rule

작업 전 순서는 기본적으로 아래다.

1. `AGENTS.md`와 `docs/codex/documentation-index.md`를 먼저 읽는다.
2. 구조 추적이나 영향 범위 확인이 필요하면 broad grep 전에 `CodeGraph`를 먼저 쓴다.
3. 작고 단순한 수정이 아니면 조사/구현/리뷰를 분리한다.
4. 수정 전에는 성공 기준과 검증 명령을 짧게 정한다.
5. 수정 후에는 확인된 사실과 아직 추정인 내용을 섞지 않는다.

## Project Purpose

이 프로젝트는 Naver 증권 리서치 종목 페이지를 기준으로 보고서를 수집하고,
SQLite에 저장하고, 다음 영업일 아침 브리핑과 운영용 상태 점검을 제공하는 Python MVP다.

현재 핵심 기능:

- 한국 영업일 장중 보고서 polling
- 신규 보고서 감지
- 종목별 일일 요약
- Toss 20:00 시장 종가 스냅샷(지수, 거래대금 Top20, 시장 수급, 우선 후보 수급)
- Telegram 알림 및 명령 worker
- Task Scheduler 기반 운영
- `admin-gui` 와 `web-view` 분리 운영

## Non-Negotiable Product Constraints

- `admin-gui`는 operator-only, `web-view`는 friend-facing GET-only surface다.
- public numeric score/grade, generic buy/sell recommendation, guaranteed price, broker execution은 금지다. 단, 아래 Main Top2 차트 계약에 정의한 재현 가능한 가격 조건 표시는 별도 예외다.
- `web-view` 기본 로드는 stored-data 기반이어야 한다.
- KRX 저장 행은 과거 분석/복기 전용으로 유지하며, 신규 웹뷰·스케줄러 시장 기준값은 Toss 20:00 저장 스냅샷을 사용한다.
- `.env` raw login 확인이 가능하면 browser login automation보다 우선한다.
- 외부 실험 도구/라이브러리는 production runtime, scheduler task, public `web-view` 기능으로 바로 연결하지 않는다. Stock-Newbby 지표 기준을 참고하는 Main Top2 예외는 아래 계약만 허용한다.

## Current Operating State

현재는 구현 초기 단계가 아니라 live-market validation / operational hardening 단계다.
대표 우선축은 아래다.

- scheduled run 검증
- Telegram paging / retry / outbox 상태 안전성
- `web-view` 품질과 public-safe 노출 경계
- Toss 20:00 종가 스냅샷의 완결성과 기준일 정확성
- schema / replay / migration 안전성

## Important Working Rules

- parser, summary, notification, admin-gui, web-view 변경 전에는 `docs/codex/data-governance.md`를 먼저 본다.
- raw/source 값, parsed/storage 값, aggregate 값, display 값을 분리해서 생각한다.
- operator memo의 "기반 구현"과 "의도 달성"을 구분한다.
- source probe 실험 결과는 production behavior와 분리한다.
- browser-gated probe가 필요해도 Telegram, scheduler, SQLite write path를 우회해 붙이지 않는다.

## Optional Skills and Tool Lanes

허용되지만 용도가 제한된 전역 skill:

- `botasaurus-stock-monitor`
  - legacy/reference-only lane for historical Botasaurus probes
  - do not treat as active maintained tooling unless the user explicitly asks to restore it
- `scrapling-official`
  - preferred active browser/source-probe tool for browser-gated, rendered-page, anti-bot-sensitive, and future-source checks
  - use `--ai-targeted` for Scrapling CLI extraction commands
  - production DB writes, Telegram, scheduler, admin-gui, and public `web-view` integration remain blocked
- `kronos-market-forecast`
  - not in the current active global baseline; treat old results as historical research-only references unless explicitly re-enabled
  - public score, recommendation, Telegram trading alert 연결 금지
- `codex-complexity-optimizer`
  - local complexity/performance review 전용
  - 결과를 그대로 코드 변경으로 간주하지 않는다
- `chart-assistant` (Stock-Newbby)
  - global Codex skill로 설치됨. 사용자가 요청한 경우 on-demand 차트/기술 근거 검토에 사용한다
  - 출력에 source, 기준 시각, provisional/confirmation 상태를 보존하고 수익성·매매 지시로 해석하지 않는다
  - Stock-Newbby의 별도 cache/provider는 main 후보 순서, Stock Monitor DB, scheduler, Telegram에 연결하지 않는다. public `web-view`에서는 아래 명시적 Main Top2 버튼만 예외로 허용한다
  - 로컬 서버 시작, 실시간 source 요청, monitor start/pause는 사용자 요청이 있을 때만 수행한다
- `operator-review`
  - `admin-gui`와 public `web-view`에 넣지 않는 operator 전용 근거 검토면이며, 별도 GET-only 서버로 `127.0.0.1`에만 바인딩한다
  - 선택 날짜의 Main 후보 순서와 저장 근거를 읽기 전용 SQLite 연결로 표시한다. 스키마 초기화·마이그레이션·저장은 금지한다
  - Stock-Newbby 차트 링크는 operator가 직접 클릭할 때만 사용한다. Newbby 서버를 자동 시작하지 않는다. public `web-view`의 별도 Main 지표 버튼 계약은 operator-review 기능으로 취급하지 않는다
- public `web-view` Main
  - 저장 후보, 관찰 요약, 출처/기준일, 근거와 누락 정보를 직관적으로 읽을 수 있는 공개 화면으로 유지한다
  - 차트 도구의 로컬 데이터나 숫자 점수·등급·일반 매매 신호를 노출하지 않는다. 아래 Main Top2 가격 조건 projection만 별도 허용 예외다
  - Main 우선순위 카드의 사용자가 `차트 · 지표 확인`을 눌렀을 때만 Toss 조정 일봉을 조회해 Newbby 기준의 사실 지표와 차트를 계산한다. public GET `/api/priority-indicators?date=...`는 직접 호출할 수 있으나 서버가 고른 Main Top2만 사용한다. 선택일 Toss 시장 분류가 없으면 선택일 이전 최신 Toss 종목 유니버스 분류와 기준일을 사용하고, 둘 다 없으면 시장을 `unknown`으로 표시하며 6자리 Toss 종목 코드로 계속 조회한다. `.KS`/`.KQ` suffix나 KRX 분류를 추측하지 않는다
  - 일봉은 `adjusted=true`, 페이지당 최대 200봉, 최대 4페이지(800봉)까지 요청한다. inclusive cursor 경계 중복과 선택일 이후 봉을 제외한다. `nextBefore`가 없으면 반환된 봉 범위와 cursor 미제공 상태를 표시하고, 잘못된 cursor는 응답 오류로 처리한다. 각 성공 항목의 별도 `chart.bars` 투영은 최신 380봉의 OHLCV와 정렬된 SMA 20/60/120/200, RSI 14, MACD/시그널/히스토그램, OBV, ATR 14를 제공한다. 화면은 50/100/200봉 범위를 선택해 캔들·이동평균·거래량 및 보조지표를 그린다. Stock Monitor DB, 후보 순서, scheduler, Telegram, Stock-Newbby 서버/cache에는 반영하지 않으며 KRX fallback도 사용하지 않는다. source/fetch time/bar date와 확인 상태 및 missing/error 상태를 표시한다
  - schemaVersion 1의 전체 허용 필드를 검증한다: 모든 지표 group/계산 기준·provenance, 전체 profile bins, 세 `structureStatus` family, family별 geometry measurement 이름/label/unit. `servedAt`과 insufficient-data profile의 `binCount`만 optional이다. MACD `signal` 선은 객관 지표로 표시한다. unknown/missing v1 field는 unsupported 상태로 표시한다
  - 빈 geometry는 음성 근거나 확인 완료로 해석하지 않는다. 삼각형 교점 price 및 봉 거리에는 직선 외삽/목표가 아님 label을 표시한다. 매매 action/signal, score, grade 필드는 노출하지 않는다
  - 별도 파생 projection은 선택일 Main Top2에만 허용한다. actual bar를 제외한 직전 20봉 고가 초과 또는 직전 10봉 저가 미만은 가격 trigger일 뿐이며, 각각 RSI14>50 / <50, MACD>signal / <signal, SMA·EMA·WMA 각각의 strict `close>SMA20>SMA60>SMA120>SMA200` / strict reverse, close>Bollinger20 middle / <middle, close>Donchian20 middle / <middle, OBV delta5>0 / <0가 모두 같은 방향이어야 한다. volume ratio20>=1.2는 별도 gate다. 필요한 방향·가격·거래량 입력 누락은 `판정 불가`; 모든 입력이 존재하나 가격 trigger 후 비교 방향이 섞이거나 volume gate 미통과면 `가격 기준 도달 · 보조지표 확인 필요`; 둘 다 미도달은 `두 가격 조건 미충족` 및 문맥으로 표시한다. UI는 SMA/EMA/WMA 각각의 20/60/120/200 수치와 stack 상태를 같이 표시한다. 이 unanimity는 사용자 정의의 투명한 필터이지 numeric score나 경험적 오류 감소 보장이 아니다. ATR14와 HLC3 volume-profile의 각 `peak=true` bin 구간은 방향 문맥만 제공하고, 종가 위치(각 bin 안/두 bin 사이/모든 peak bin 위/아래)를 따로 표시한다. 분리된 peak bin들을 하나의 연속 area로 합치지 않으며 structure measurement도 별도 표시한다. RSI flat-window 중립 50 수정은 root `calculationVersion=stock-monitor-indicator-v2`에 기록하고 기존 indicator-group `TECHNICAL_VERSION=technical-v4` provenance를 유지한다. schemaVersion 1 shape/allowlist는 바뀌지 않는다. 점수나 표결 합계는 만들지 않고 각 구성요소의 값·상태·출처·날짜와 봉 확정성을 표시한다. Toss source/fetch/sourceDate 및 선택 요청일/실제 기준 봉일을 보존한다. 이 projection은 후보 순서·DB·scheduler·Telegram·broker/order·자동 실행에 연결하지 않으며 일반 매수/매도 추천이나 보장 가격이 아니다

  - API item-level `price_conditions`, `indicator_confirmation`, and `condition_status` remain outside schemaVersion 1 snapshots.

## CodeGraph

이 프로젝트는 `{PROJECT_ROOT}\.codegraph` 인덱스를 이미 갖고 있다.
`codegraph`는 runtime dependency가 아니라 로컬 코드 탐색 도구다.

우선 사용이 맞는 경우:

- `fetch -> parse -> persist -> summarize -> notify` ownership 추적
- scheduler / CLI wrapper entry path 추적
- `admin-gui` / `web-view` route 와 DTO 경계 추적
- schema, replay, migration impact 확인
- 새 실험 도구가 production behavior에 닿는지 점검

굳이 우선하지 않아도 되는 경우:

- 단일 파일의 명확한 copy/UI wording 수정
- 범위가 확정된 작은 테스트 보정
- 이미 owning file이 확정된 좁은 patch

## Subagent Routing

작고 명확한 수정은 메인 세션에서 바로 처리한다.
그 외에는 아래처럼 역할을 나눈다.

- `backend-developer`: fetch -> parse -> persist -> summarize -> notify 흐름 수정
- `python-pro`: Python typing, parser, runtime contract 수정
- `cli-developer`: CLI, scheduler wrapper, operator-facing command 수정
- `sql-pro`: dedupe, migration, replay safety, schema impact 검토
- `debugger`: unattended-run, scheduler, Telegram, runtime-state failure 분리
- `test-engineer`: scheduler, Telegram, outbox, replay-sensitive flow 회귀 검증
- `market-data-engineer`: KRX/KIS/ETF/flow source semantics와 ingest boundary 검토
- `web-ui-engineer`: GET-only `web-view` 구현/정리
- `admin-ui-engineer`: operator-facing admin surface 정리
- `security-hardening`: access gate, exposure boundary, public-safe DTO 검토
- `documentation-engineer`: roadmap/current-work/decision-log/document drift 정리
- `reviewer`: business-day rule, delivery-state safety, regression risk 최종 검토

권장 흐름:

- source ownership 불명: `debugger` 또는 `backend-developer` + `CodeGraph` -> 구현 agent -> `reviewer`
- schema/replay risk: `sql-pro` -> 구현 agent -> `reviewer` 또는 `test-engineer`
- source/market-data boundary: `market-data-engineer` -> 구현 agent -> `reviewer`
- public-safe 노출 점검: `security-hardening` -> 구현 agent -> `reviewer`

## Output Rule

결과는 가능하면 아래 형식으로 정리한다.

- scope
- assumptions
- success criteria or verification command
- exact path or changed path
- confirmed findings or changes
- validation performed
- residual risk
- blocked or still-unverified items

## Global Agent Layer Rule 2026-05-29

Use the global Codex agent/skill layer before considering project-local agents.

Current decision:

- Keep `{PROJECT_ROOT}\.codex\agents` absent.
- Do not recreate or bulk-restore the old local agent set.
- Use global agents/skills plus CodeGraph first.
- Restore a project-local agent only after repeated Stock Monitor work proves a specific gap.
- If a restore is needed, restore only the one exact role from `{GLOBAL_AGENT_BACKUP_ROOT}\agent-skill-reset-2026-05-29`.

Global mapping:

- Python / backend review: global `python-reviewer`, `code-reviewer`, CodeGraph
- DB / schema / migration review: global `database-reviewer`, `database-migrations`
- security / public-surface review: global `security-reviewer`, `security-review`, `security-scan`
- validation: global `verification-loop`, `e2e-testing`, `eval-harness`, `qa`
- documentation: global `doc-updater`, `docs-researcher`, `handoff`
- triage/debugging: global `diagnose`, `silent-failure-hunter`, `code-explorer`

Stock Monitor-specific rule:

- Preserve the `admin-gui` vs GET-only `web-view` boundary.
- Do not add public numeric scores, investment grades, generic trading calls, broker execution, or order-routing behavior. The exact separate Main Top2 threshold-condition projection defined above is the sole chart-derived public exception.
- Do not connect lab/source probes to production DB writes, Telegram, scheduler, admin-gui, or web-view.
- SchemaSpy remains lab-only / repeatable-lab candidate after jars are staged.
- QuantDinger remains hold.
- OpenAlgo remains future-lab only.
- HeroUI is for future React/Next UI work only; do not apply it to the current Python/admin/web-view surfaces without an explicit frontend rewrite.
- Exa remains hold unless normal web/docs lookup repeatedly proves insufficient.
- If any old role is restored later, `market-data-engineer` is the first likely candidate, but only after repeated KRX/Data Marketplace/source-semantics work proves the global layer is insufficient.

Reference:

- `{GLOBAL_LAB_RESULTS_ROOT}\post-global-layer-project-survey-2026-05-29.md`

## Superpowers Rule 2026-05-29

Superpowers may be used as a planning and execution aid.

It must not override:

- this project `AGENTS.md`
- `docs/codex` project rules
- CodeGraph-first tracing when ownership is unclear
- admin-gui vs GET-only web-view boundary
- no public numeric score / generic trading-call / broker-execution boundary, subject to the narrow Main Top2 threshold-condition exception defined above
- lab / global / project-local / production boundaries
- the no-bulk-restore project-local agent policy

Use Superpowers to improve task planning and execution discipline, not to reintroduce stale local-agent routing or bypass production safety gates.
