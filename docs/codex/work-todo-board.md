# Work Todo Board

## Purpose

이 문서는 `02.Stock_Moniter`의 큰 작업축을 체크 가능한 형태로 모아둔 실행 보드다.

사용자가 `TODO-WV 진행`, `TODO-TG 해줘`, `TODO-DATA Toss 먼저`처럼 항목 ID를 말하면,
해당 항목의 범위, 산출물, 검증 기준을 기준으로 바로 작업을 시작한다.

## Use Rules

- 체크박스는 큰 작업축 완료 여부만 표시한다.
- 세부 기능을 작은 체크박스로 쪼개지 않는다.
- 새 작업축은 기존 ID와 겹치지 않는 stable ID를 부여한다.
- 완료 판정은 `Done When` 기준을 만족하고, 검증 명령 또는 실제 화면/출력 확인이 끝났을 때만 한다.
- 운영 적용은 별도 승인 전까지 보드 완료 조건이 아니다. 개발 검증과 운영 싱크는 분리한다.

## Current Priority

| Order | Todo ID | Why Now |
| --- | --- | --- |
| 1 | `TODO-OPS` | `ops-sync-preview` now emits an operating-PC handoff prompt, but default DB schema approval/handling and final operating-PC batch verification remain separate. |

## Todo Board

### [x] TODO-WV: Web-View Visible Product Flow

**Goal:**
`web-view`를 검증용 화면이 아니라 날짜별 브리핑, 후보 근거, 종목 상세, 시장/순환매 참고가 한 흐름으로 읽히는 화면으로 만든다.

**User Command Examples:**
`TODO-WV 진행`, `웹뷰 보이는 결과물 이어서`, `후보 근거 화면 정리`

**Scope:**

- 메인: 날짜 브리핑, top priority, news observation summary, intraday reference 상태.
- 관찰: candidate evidence, news badge, empty/low-evidence 상태.
- 종목: 종목 검색, 저장 리포트가 없는 종목의 empty state, stock detail news context.
- 시장: KRX/index/flow stored reference.
- 순환매: ETF rotation evidence, category/ETF context.
- `/v2` preview는 기존 `/` 대체가 아니라 정보구조 실험/검토 route로 유지한다.

**Done When:**

- fixture/test DB 기준으로 실제 브라우저에서 주요 화면과 클릭 흐름이 확인된다.
- 후보 카드에서 왜 봐야 하는지 한 줄로 읽힌다.
- 뉴스 근거가 있거나 없어도 숨기지 않고 표시된다.
- DOM/DTO에 점수, 매수/매도, 주문/브로커 실행 표현이 새지 않는다.
- `tests/test_web_view.py` 관련 검증과 browser/smoke 계열 검증이 통과한다.

**Start By Reading:**

- `docs/codex/surface-contract.md`
- `docs/codex/next-phase.md`
- `docs/codex/contracts/candidate-evidence-contract.md`
- `docs/codex/contracts/news-intelligence-contract.md`

**Completion Note:**
2026-06-05 dev commit `e48eeab`에서 개발 검증 기준으로 완료 처리했다. `dev-fixture-db --scenario visible-product-flow` fixture DB를 만들고, `web-view-value-qa`, `web-view-browser-smoke`, `tests/test_web_view.py`, 전체 pytest를 통과했다. 실제 브라우저 smoke에서 메인/관찰/종목/시장/순환매 탭, 종목 검색, 리포트 없는 종목 `Beta Memory / 000660`의 stock-detail empty state, GET-only/POST-block 경계를 확인했다. 운영 적용, 외부 provider smoke, Startup fallback 운영 관측은 `TODO-OPS` 범위로 남긴다.

### [x] TODO-TG: Telegram Market Briefing Output

**Goal:**
웹뷰의 stored evidence와 news observation을 활용해 장초/장중/장마감 복기용 Telegram briefing 문구를 실제 발송 가능한 형태로 만든다.

**User Command Examples:**
`TODO-TG 진행`, `시황 봇 문구 만들자`, `텔레그램 브리핑 이어서`

**Scope:**

- `국장 점심 브리핑`, `장마감 전 점검`, `오늘의 시장 분위기` 같은 time-slot 문구.
- 지수, 주요 종목, 리포트 흐름, news observation, KRX/ETF/flow reference 결합.
- 실제 발송 전 preview/read-only 출력.
- 수동 review send와 scheduled send gate 분리.
- Telegram command worker와 기존 daily notification 흐름을 깨지 않는다.

**Done When:**

- fixture 또는 저장 DB 기준 briefing text/json preview가 나온다.
- 같은 근거가 `web-view`와 Telegram에서 크게 엇갈리지 않는다.
- 문구가 관찰/복기 중심이며 거래 지시처럼 보이지 않는다.
- 수동 예문 발송 또는 발송 직전 preview 검증 경로가 명확하다.
- 운영 scheduler 자동 등록은 별도 승인 전까지 하지 않는다.

**Start By Reading:**

- `docs/codex/next-phase.md`
- `docs/codex/execution-roadmap.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/surface-contract.md`

**Completion Note:**
2026-06-05 dev commit `e48eeab`에서 개발 검증 기준으로 완료 처리했다. fixture DB 기준 `market-briefing --slot mood|lunch|preclose`, `--json` read-only preview, public-safe issue count `0`, stored news evidence 포함, `market-briefing-readiness` preview 경로를 확인했다. Telegram 실발송, 수동 review send 카운트 적립, phone review acceptance, scheduler 자동 등록은 별도 승인 전까지 운영 범위로 남긴다.

### [x] TODO-NI: News Intelligence Evidence Layer

**Goal:**
news intelligence를 독립 뉴스 수집기가 아니라 report/KRX/candidate evidence를 보강하는 판단 근거 레이어로 완성한다.

**User Command Examples:**
`TODO-NI 진행`, `뉴스 관찰 근거 이어서`, `candidate news 연결 더 해줘`

**Scope:**

- Naver 5-lane preview, source mode, coverage, indirect/summary-only guard.
- `--save-observation` 저장 결과의 readback, daily brief, text summary.
- candidate linkage evaluation과 web-view public projection.
- exact/stale KRX reference 표시.
- 운영 저장은 제한된 종목/영업일 기준으로 별도 승인 후 수행한다.

**Done When:**

- 저장 observation을 날짜/종목별로 읽고 비교할 수 있다.
- candidate evidence와 news observation 연결 근거가 화면과 CLI 양쪽에서 보인다.
- direct, caution, market-context 성격이 서로 섞여 보이지 않는다.
- stale KRX reference가 운영자에게 숨겨지지 않는다.
- raw sentiment/impact/internal recommendation payload는 shared surface에 노출되지 않는다.

**Start By Reading:**

- `docs/codex/contracts/news-intelligence-contract.md`
- `docs/codex/surface-contract.md`
- `docs/codex/data-source-policy.md`

**Progress Note:**
2026-06-05 dev commit `24cff27`에서 daily web-view의 news observation summary, candidate badge, stock detail, `/v2` rendering에 public-safe connection label/reason을 추가했다. `tests/test_web_view.py`, `tests/test_cli_commands.py`, fixture `web-view-value-qa`, `web-view-browser-smoke`, 전체 pytest가 통과했다. raw sentiment/impact/internal recommendation은 public payload에 노출하지 않았다. 남은 범위는 저장 observation readback, CLI 비교 출력, source-mode coverage 정리다.

**Completion Note:**
2026-06-05 dev commits `c8a4a67`/`2fe1d80`에서 저장 observation readback과 CLI 비교 출력을 완료했다. `news-intelligence-observations`는 저장 run 전체의 `source_mode_coverage`를 JSON으로 내보내며 source mode, source lane, direct/indirect/market-context 합계, match scope, KRX exact/stale/missing/none 상태, candidate-linkage label, operator recommendation-support label, read-only/operator-only 경계 플래그를 한 번에 비교할 수 있다. text 출력도 per-run evidence 앞에 같은 coverage 요약을 표시한다. `news-intelligence-daily-brief` JSON/text에도 표시 대상 saved-run 그룹 기준 coverage가 추가됐다. RED/GREEN 테스트, `python -m pytest tests\test_cli_commands.py tests\test_news_intelligence.py -q -k news_intelligence` (`29 passed`), 전체 CLI 테스트 (`323 passed`), temp DB CLI smoke에서 `source-mode coverage`, `source_modes: naver_5_lane_preview=2`, `labels: stale_krx_check_first=1, strengthen_existing_candidate=1`, KRX exact/stale 집계를 확인했다. public web-view raw sentiment/impact/internal recommendation 노출 금지는 기존 public projection 테스트로 유지했고 public route는 변경하지 않았다.

### [x] TODO-DATA: Market Data, ETF, And Source Freshness

**Goal:**
KRX/ETF/flow/Toss/X 같은 외부 데이터 축을 실제 동작 가능한 source lane으로 분리하고, freshness와 한계를 화면/문구에 드러낸다.

**User Command Examples:**
`TODO-DATA 진행`, `TODO-DATA Toss 먼저`, `ETF 쪽 실제 기능 확인`, `데이터 소스 정리`

**Aliases:**
`TODO-TOSS`, `TODO-ETF`, `TODO-X`는 모두 `TODO-DATA`의 하위 범위로 해석한다.

**Scope:**

- KRX Open API daily stock/ETF/index baseline과 next-business-day `08:00` publication rule.
- KRX Data Marketplace `[12009]` report-mentioned stock flow lane.
- ETF rotation evidence와 구성종목/source 가능성 검토.
- Toss OpenAPI read-only lab: 공식 문서, 권한, rate limit, quote/account/order boundary.
- X/no-login recap lab: 로그인 없이 접근 가능한 공개 글/링크 요약 가능성.

**Done When:**

- 각 source lane이 production/lab/hold로 분리된다.
- 실제 동작 가능한 read-only probe와 불가능/보류 범위가 문서화된다.
- web-view/Telegram에 붙일 때 freshness 표시가 모호하지 않다.
- Toss/X는 별도 lab branch에서 검증하고, dev에는 합의된 결과만 병합한다.

**Start By Reading:**

- `docs/codex/data-source-policy.md`
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/contracts/toss-openapi-readonly-lab-contract.md`
- `docs/codex/contracts/toss-openapi-official-api-inventory.md`

**Progress Note:**
2026-06-05 dev commits `80c9b98`/`f420bdc`에서 daily web-view API와 화면에 `source_freshness_summary`를 추가했다. 선택 날짜별 Naver reports, KRX Open API market/ETF, KRX Data Marketplace investor flow, Toss OpenAPI lab-hold 상태가 `exact`/`stale`/`missing`/`lab_hold`로 표시된다. 기본 DB는 schema가 오래되어 read-only QA가 migration 안내로 중단됐으므로, production/default DB를 쓰지 않고 temp fixture DB로 `web-view-value-qa`, `web-view-browser-smoke`, `tests/test_web_view.py`, `tests/test_cli_commands.py`, 전체 pytest를 통과시켰다. 남은 범위는 Toss/X lab feasibility, ETF 구성종목/source 검토, Telegram freshness 문구 연결이다.

**Progress Note:**
2026-06-05 dev commits `247a420`/`4838b22`에서 `market-briefing` Telegram preview에도 source freshness를 연결했다. text preview는 `데이터 기준` 섹션으로 Naver reports, KRX market, ETF daily, Investor flow, Toss OpenAPI 상태를 `exact`/`missing`/`lab-hold`와 기준일로 표시한다. JSON preview는 web-view와 같은 `source_freshness_summary`를 포함하고, Toss OpenAPI는 `lab_hold`, `live_fetch=false`, `affects_ordering=false`로 남긴다. RED/GREEN 테스트와 `python -m pytest tests\test_cli_commands.py -q -k market_briefing` (`16 passed`)를 확인했고, temp fixture DB smoke에서 message의 source freshness 줄과 JSON summary를 확인했다. 남은 범위는 Toss/X lab feasibility와 ETF 구성종목/source 검토다.

**Completion Note:**
2026-06-05 dev commits `65d41f4`/`d2c641e` completed the remaining source-lane boundary slice with the read-only `data-source-lane-audit` CLI. The command emits a concrete JSON/text audit with Naver reports, KRX stock/index/ETF daily, KRX investor flow, Toss OpenAPI, and X public recap classified as `production`, `production_limited`, `hold`, or `lab`. The output explicitly states `etf_daily | production | constituents=not_loaded`, `toss_openapi | hold | live_fetch=false | affects_ordering=false`, and `x_public_recap | lab | separate_lab_branch=true | login_dependency_allowed=false`; the JSON `done_when_coverage` confirms source lanes are classified, web-view freshness is connected, Telegram freshness is connected, Toss/X are not exaggerated, and ETF constituent status is explicit. Verified `python -m stock_monitor data-source-lane-audit`, `python -m stock_monitor data-source-lane-audit --json`, `python -m pytest tests\test_cli_commands.py -q -k data_source_lane_audit` (`3 passed`), `python -m pytest tests\test_cli_commands.py -q` (`326 passed`), and full `python -m pytest -q` (`732 passed`). No live fetch, DB write, Telegram send, scheduler registration, admin-gui connection, or web-view connection was added.

### [ ] TODO-OPS: Operations, Sync, And Performance Closeout

**Goal:**
개발 결과를 dev에 모으고, 운영 적용은 묶음 단위로 싱크하면서 성능/버튼/GET-only/read-only 계약을 재관측한다.

**User Command Examples:**
`TODO-OPS 진행`, `운영 싱크 준비`, `N100 관측 결과 반영`

**Scope:**

- dev branch를 실험 결과 통합/검토 기준으로 유지.
- main/operating PC cherry-pick은 batch 단위로 적용.
- `/api/daily/{date}?intraday_market_top=1` 같은 cold/warm perf 재관측.
- archive/news count, candidate badge, stock detail click, `/v2` preview, ETF rotation smoke.
- 운영 관측 메모는 `docs/codex/operations/`에 두되 public docs에는 세부값을 노출하지 않는다.

**Done When:**

- dev와 운영 main의 적용 대상 차이가 subject 기준으로 설명된다.
- batch 적용 순서와 충돌 예상 파일이 정리된다.
- read-only smoke, GET-only contract, public wording scan이 통과한다.
- 운영 관측에서 나온 UI/perf 문제는 다음 개발 항목으로 환류된다.

**Start By Reading:**

- `docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md`
- `docs/codex/surface-contract.md`
- `docs/codex/architecture-risk-review.md`

**Progress Note:**
2026-06-05 dev commits `77a2321`/`02f13f7`에서 read-only `ops-sync-preview` CLI를 추가했다. 이 출력은 `origin/main..dev` commit subjects, changed file groups, conflict watch paths, `data/` untracked 분리, batch 제외 경로, 별도 승인 필요 작업, 검증 명령을 JSON/text로 보여준다. 기본 DB schema가 target보다 오래된 경우 stack trace 대신 `default_db_schema_not_current` blocker로 표시한다. fixture DB 기준 `web-view-value-qa` issue/warning `0`, `web-view-browser-smoke` issue `0`, `api-perf-summary` 읽기 성공, 전체 pytest `720 passed`를 확인했다. 남은 범위는 기본 DB migration 승인/처리 여부 결정, 실제 운영 적용 batch 검증, 운영 관측에서 나온 perf/UI 항목 환류다.

**Progress Note:**
2026-06-05 dev commits `4b4f2e2`/`6cc9973`에서 `ops-sync-preview --json`에 `operating_pc_handoff`를 추가했다. handoff prompt의 첫 줄은 운영/개발 경계 규칙에 맞춰 `운영 PC용`이며, 비교 범위, source sync readiness, `data/` untracked 제외 안내, 커밋 요약, 변경 파일 그룹, 충돌 주의 경로, 검증 명령, 현재 blocker, 별도 승인 전 금지 작업, 적용 batch 제외 항목을 한 번에 출력한다. 이 기능은 read-only이며 DB write, scheduler 변경, Telegram 실발송, admin-gui 프로세스 조작을 하지 않는다. `python -m pytest tests\test_cli_commands.py -q -k ops_sync_preview` (`3 passed`)와 실제 `ops-sync-preview --base origin/main --head dev --json` handoff prompt 생성을 확인했다. 기본 DB schema blocker와 실제 운영 PC batch 검증은 여전히 별도 승인/운영 세션 범위다.

**Progress Note:**
2026-06-05 dev commits `9524f56`/`1b1c0dc` improved default-DB stale-schema handling for OPS verification commands. When the default DB is still schema `5/7`, `db-verify --json` and `ops-readiness --json` now return structured JSON with `surface`, `ready=false`, `schema_status.status=migration_required`, `pending_versions=[6,7]`, `default_db_schema_not_current`, review commands, and separate-approval requirements instead of a stack trace. `api-perf-summary --json` now runs without requiring DB schema current because it only reads API performance logs; the current dev-PC log smoke returned `record_count=1980` and `endpoint_count=62`. Verified focused stale-schema tests (`2 passed`), actual default-DB CLI smoke for `db-verify --json`, `ops-readiness --json`, `api-perf-summary --json`, `ops-sync-preview --json`, full CLI tests (`328 passed`), and full `python -m pytest -q` (`734 passed`). Remaining scope is still explicit migration approval/handling for the default or operating PC DB and final operating-PC batch verification.

**Progress Note:**
2026-06-05 dev commits `01d27d1`/`ffddffb` added `schema_action_plan` to `ops-sync-preview --json` and the generated `operating_pc_handoff.prompt`. The handoff now separates pre-approval checks (`ops-sync-preview`, `db-migrate --dry-run`, `db-verify --json`) from post-approval commands (`db-backup --tag pre-schema-migration`, `db-migrate`, `db-verify --json`, `ops-readiness --json`) and repeats the forbidden-without-approval list including `schema migration on operating PC`. Actual default-DB smoke returned `source_sync_ready=false`, `schema_status=migration_required`, `approval_required=true`, `pre_approval_count=3`, `post_approval_count=4`, and prompt markers for `Schema action plan` and `post-approval`. Verified `python -m pytest tests\test_cli_commands.py -q -k ops_sync_preview` (`3 passed`), full CLI tests (`328 passed`), and full `python -m pytest -q` (`734 passed`). Remaining scope is the explicit approval decision and actual operating-PC batch verification.

**Progress Note:**
2026-06-05 dev commits `087cfcd`/`413ce3f` added `db-migration-rehearsal`, which uses a temporary SQLite backup copy to apply migrations and run verification without writing the source DB. Actual default-DB smoke with a `%TEMP%` work dir returned `ready=true`, `read_only_source=true`, `writes_source_db=false`, `copy_retained=false`, source schema `5/7` before and after, copy schema `5/7 -> 7/7`, `copy_verify_ready=true`, and `blocker_count=0`. Verified focused rehearsal tests (`2 passed`), full CLI tests (`330 passed`), and full `python -m pytest -q` (`736 passed`). Remaining scope is not technical rehearsal anymore; it is explicit approval for the real default/operating-PC DB migration and the actual operating-PC batch verification.

### [x] TODO-ADMIN: Admin / Web-View / Operator-Review Boundary

**Goal:**
admin-gui는 운영 상태/제어/복구/설정/audit만 담당하고, 판단 화면은 web-view projection 또는 future operator-review로 분리한다.

**User Command Examples:**
`TODO-ADMIN 진행`, `관리자 화면 정리`, `operator-review 경계 잡자`

**Scope:**

- admin-gui 메뉴와 payload에서 판단/후보/raw news review가 섞이지 않는지 확인.
- web-view는 shared read-only stored-data projection으로 유지.
- operator-review는 future private review surface로만 정의하고, 구현 전 route/access/test contract를 별도 수립.

**Done When:**

- admin-gui에 candidate evidence/raw news/internal judgment review가 screen body로 들어가지 않는다.
- web-view public projection 허용 범위가 문서와 테스트에서 일치한다.
- future operator-review가 admin-gui와 같은 것으로 오해되지 않는다.

**Start By Reading:**

- `docs/codex/surface-contract.md`
- `docs/codex/admin-gui-plan.md`
- `tests/test_admin_gui.py`

**Completion Note:**
2026-06-05 dev commits `72312a3`/`3de33c4` added a read-only `admin-boundary-audit` CLI and tests. The audit emits a concrete JSON/text boundary report for `admin-gui`, `web-view`, and future `operator-review`: no live fetch, no DB write, no Telegram send, no scheduler registration, admin HTML judgment-review token count, public-content token count, operator status payload availability, web-view `/api/status` expected 404, and operator-review reserved/unimplemented state. Default DB remains untouched; when its schema is stale the command returns `default_db_schema_not_current` as a blocker instead of a stack trace. Fixture DB verification returned `ready=true`, zero admin HTML judgment-review matches, zero admin HTML public-content matches, zero operator status forbidden matches, and `operator_review.route_present_in_admin_html=false`. Verified with `python -m stock_monitor admin-boundary-audit --json`, fixture `admin-boundary-audit --json`, `python -m pytest tests\test_admin_gui.py tests\test_operator_status.py tests\test_cli_commands.py -q -k "admin_boundary_audit or admin_gui or operator_status"` (`65 passed`), and full `python -m pytest -q` (`723 passed`).

### [x] TODO-DOC: Public Documentation And Information Hygiene

**Goal:**
README, roadmap, contracts, changelog가 현재 main/dev 현실과 맞고, 공개 문서에 개인 경로, secret, 실행 가능한 민감 URL, 과한 운영 세부가 남지 않게 유지한다.

**User Command Examples:**
`TODO-DOC 진행`, `문서 현행화`, `README 다시 훑어봐`

**Scope:**

- README 공개용 설명 유지.
- canonical docs 간 상태/목표/완료율 충돌 제거.
- public docs hygiene test 유지.
- lab branch는 완료 기능처럼 쓰지 않고 roadmap/lab으로만 표현.
- 운영 관측 상세는 `docs/codex/operations/`에 두고 public docs에는 요약만 반영.

**Done When:**

- `documentation-index.md`가 새 문서/계약을 찾을 수 있게 갱신된다.
- README와 canonical docs가 서로 다른 완료율/방향을 말하지 않는다.
- 공개 문서 정보노출 회귀 테스트가 통과한다.
- Toss/Telegram/X lab 상태가 과장되지 않는다.

**Start By Reading:**

- `README.md`
- `docs/codex/documentation-index.md`
- `docs/codex/current-work.md`
- `docs/codex/next-phase.md`
- `docs/codex/execution-roadmap.md`

**Completion Note:**
2026-06-05 dev commits `3d549b3`/`d066886` added a read-only `docs-hygiene-audit` CLI and refreshed public/canonical docs. The audit scans README, the core canonical status/roadmap docs, `surface-contract.md`, `data-source-policy.md`, `data-quality-checklist.md`, and `contracts/news-intelligence-contract.md` for local absolute user paths, real external provider URLs, secret-like assignments, and raw access-code examples while returning only redacted file/line/count metadata. `documentation-index.md`, roadmap, and core contract links were converted from local absolute workspace paths to relative links, historical external web-view provider URL mentions were replaced with placeholders, and README now lists `admin-boundary-audit --json` and `docs-hygiene-audit --json`. Verified `docs-hygiene-audit --json` returned `ready=true`, `scanned_file_count=9`, and `issue_count=0`; `tests/test_cli_commands.py -q -k docs_hygiene_audit` returned `4 passed`; `tests/test_cli_commands.py -q` returned `321 passed`.

## Lab Branches To Keep Separate

| Branch / Lane | Todo Link | Current Rule |
| --- | --- | --- |
| `toss-openapi-readonly-lab` | `TODO-DATA` | Read-only docs/probe lane only until keys, permissions, and order-boundary review are complete. |
| `telegram-market-briefing-slots` | `TODO-TG` | Product text/slot refinement lane; merge into dev when it improves the shared briefing contract. |
| `x-browser-recap-lab` | `TODO-DATA` | No-login/public-access feasibility lane; do not depend on an authenticated browser session by default. |

## Default Prompt Template

Use this when starting a todo item:

```text
<project root> 범위에서 dev 브랜치 기준으로 진행해줘.

목표:
<TODO-ID>를 진행한다. docs/codex/work-todo-board.md의 해당 항목을 기준으로,
새로운 작은 기준/guard를 늘리기보다 실제 화면/출력/동작으로 확인 가능한 결과를 만든다.

전제:
- 관련 canonical docs를 먼저 확인한다.
- 운영 DB write, scheduler 등록/변경, Telegram 실발송, broker/order-routing은 명시 승인 전까지 하지 않는다.
- lab branch 내용은 실제 dev/main 반영분과 구분한다.
- public/shared surface에는 점수, 매수/매도, 주문/브로커 실행 표현을 노출하지 않는다.
- 구현 후 최소 검증을 실행하고, 커밋/푸시는 별도 지시가 있으면 한 번에 처리한다.

보고:
- 진행한 TODO-ID
- 실제 산출물
- 검증 결과
- 아직 남은 범위
- 다음에 이어갈 명령 예시
- 한줄리뷰
```
