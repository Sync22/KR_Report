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
| 1 | `TODO-WV` | 눈에 보이는 결과물이 부족하면 기능 성숙도를 판단하기 어렵다. |
| 2 | `TODO-TG` | 웹뷰와 같은 근거를 Telegram briefing 문구로 재사용하면 실사용 가치가 바로 보인다. |
| 3 | `TODO-NI` | news observation은 이미 저장/요약/웹뷰 노출 축이 있으므로 candidate evidence와의 연결 완성도가 중요하다. |
| 4 | `TODO-DATA` | KRX/ETF/Toss/X 같은 외부 데이터 축은 실제 동작 가능성과 source freshness 기준을 먼저 잡아야 한다. |
| 5 | `TODO-OPS` | 운영 싱크와 성능 관측은 기능 개발 후 묶어서 처리해야 충돌과 재작업이 줄어든다. |

## Todo Board

### [ ] TODO-WV: Web-View Visible Product Flow

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

### [ ] TODO-TG: Telegram Market Briefing Output

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

### [ ] TODO-NI: News Intelligence Evidence Layer

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

### [ ] TODO-DATA: Market Data, ETF, And Source Freshness

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

### [ ] TODO-ADMIN: Admin / Web-View / Operator-Review Boundary

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

### [ ] TODO-DOC: Public Documentation And Information Hygiene

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

## Lab Branches To Keep Separate

| Branch / Lane | Todo Link | Current Rule |
| --- | --- | --- |
| `toss-openapi-readonly-lab` | `TODO-DATA` | Read-only docs/probe lane only until keys, permissions, and order-boundary review are complete. |
| `telegram-market-briefing-slots` | `TODO-TG` | Product text/slot refinement lane; merge into dev when it improves the shared briefing contract. |
| `x-browser-recap-lab` | `TODO-DATA` | No-login/public-access feasibility lane; do not depend on an authenticated browser session by default. |

## Default Prompt Template

Use this when starting a todo item:

```text
C:\Users\MING\Codex\02.Stock_Moniter 범위에서 dev 브랜치 기준으로 진행해줘.

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
