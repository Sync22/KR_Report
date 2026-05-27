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

이 handoff는 `C:\Users\MING\Codex\02.Stock_Moniter`에만 적용된다.

- 프로젝트 루트: `C:\Users\MING\Codex\02.Stock_Moniter`
- 문서 루트: `C:\Users\MING\Codex\02.Stock_Moniter\docs\codex`

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
- KRX Open API 일봉/ETF/index 누락 백필
- KRX Data Marketplace `[12009]` 투자자 수급의 제한적 자동 백필
- Telegram 알림 및 명령 worker
- Task Scheduler 기반 운영
- `admin-gui` 와 `web-view` 분리 운영

## Non-Negotiable Product Constraints

- `admin-gui`는 operator-only, `web-view`는 friend-facing GET-only surface다.
- public trading recommendation, buy/sell signal, numeric score는 계속 금지다.
- `web-view` 기본 로드는 stored-data 기반이어야 한다.
- KRX Data Marketplace 자동 수집은 anchor-day mentioned stocks + stock-level `[12009]` + recent 31-day window까지만 허용한다.
- `.env` raw login 확인이 가능하면 browser login automation보다 우선한다.
- 외부 실험 도구/라이브러리는 production runtime, scheduler task, public `web-view` 기능으로 바로 연결하지 않는다.

## Current Operating State

현재는 구현 초기 단계가 아니라 live-market validation / operational hardening 단계다.
대표 우선축은 아래다.

- scheduled run 검증
- Telegram paging / retry / outbox 상태 안전성
- `web-view` 품질과 public-safe 노출 경계
- KRX latest-date evidence와 backfill 판단 정확성
- schema / replay / migration 안전성

## Important Working Rules

- parser, summary, notification, admin-gui, web-view 변경 전에는 `docs/codex/data-quality-checklist.md`를 먼저 본다.
- raw/source 값, parsed/storage 값, aggregate 값, display 값을 분리해서 생각한다.
- operator memo의 "기반 구현"과 "의도 달성"을 구분한다.
- source probe 실험 결과는 production behavior와 분리한다.
- browser-gated probe가 필요해도 Telegram, scheduler, SQLite write path를 우회해 붙이지 않는다.

## Optional Skills and Tool Lanes

허용되지만 용도가 제한된 전역 skill:

- `botasaurus-stock-monitor`
  - KRX/Data Marketplace 같은 browser-gated source probe 전용
  - main Naver/Telegram/SQLite pipeline 대체 금지
- `kronos-market-forecast`
  - stored KRX OHLCV 기반 research-only forecast 실험 전용
  - public score, recommendation, Telegram trading alert 연결 금지
- `codex-complexity-optimizer`
  - local complexity/performance review 전용
  - 결과를 그대로 코드 변경으로 간주하지 않는다

## CodeGraph

이 프로젝트는 `C:\Users\MING\Codex\02.Stock_Moniter\.codegraph` 인덱스를 이미 갖고 있다.
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
