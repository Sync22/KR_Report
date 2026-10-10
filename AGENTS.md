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
- public numeric score/grade, generic buy/sell recommendation, guaranteed price, broker execution은 금지다. Main Top2의 좁은 사용자 정의 가격·지표 조건 표시는 예외이며, 전체 계약은 [data-governance.md](docs/codex/data-governance.md#main-top2-technical-indicator-projection)가 소유한다.
- `web-view` 기본 로드는 stored-data 기반이어야 한다.
- KRX 저장 행은 과거 분석/복기 전용으로 유지하며, 신규 웹뷰·스케줄러 시장 기준값은 Toss 20:00 저장 스냅샷을 사용한다.
- `.env` raw login 확인이 가능하면 browser login automation보다 우선한다.
- 외부 실험 도구/라이브러리는 production runtime, scheduler task, public `web-view` 기능으로 바로 연결하지 않는다. Stock-Newbby 지표 기준을 참고하는 public 예외는 data-governance.md의 Main Top2 계약만 허용한다.

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
  - 저장 데이터 기반 후보·근거·누락 정보를 기본으로 유지한다. Toss 현재가/수급과 일봉 차트는 사용자가 요청한 참고 조회로 분리하고, 조회가 후보 순서나 저장값을 바꾸지 않게 한다.
  - 숫자 점수·등급·일반 매매 신호·추천·주문 기능을 노출하지 않는다. Main Top2의 별도 사용자 정의 가격·지표 조건 표시는 유일한 차트 파생 public 예외다.
  - Main Top2의 전체 source/API, 계산, schemaVersion 1 allowlist, 조건식·상태, provenance, 결측/오류 및 부작용 계약은 [data governance](docs/codex/data-governance.md#main-top2-technical-indicator-projection)가 소유한다. 사용자 조작과 표시 계약은 [surface guide](docs/codex/surface-guide.md#main-top2-technical-indicator-block)를 따른다. 두 계약을 다른 문서에 복제하지 말고 링크한다.

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
- Do not add public numeric scores, investment grades, generic trading calls, broker execution, or order-routing behavior. The separate user-defined Main Top2 threshold-condition projection is the sole chart-derived public exception; its contract is in [data-governance.md](docs/codex/data-governance.md#main-top2-technical-indicator-projection).
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
- no public numeric score / generic trading-call / broker-execution boundary, subject only to the Main Top2 condition contract in [data-governance.md](docs/codex/data-governance.md#main-top2-technical-indicator-projection)
- lab / global / project-local / production boundaries
- the no-bulk-restore project-local agent policy

Use Superpowers to improve task planning and execution discipline, not to reintroduce stale local-agent routing or bypass production safety gates.
