# Stock Research Monitor Requirements

## 목적

`02.Stock_Moniter`는 네이버 증권 `리서치 > 종목분석 > 국내종목` 리포트를 장중 수집하고,
SQLite에 저장한 뒤 Telegram, 관리자 화면, 사용자용 웹뷰로 읽기 좋은 형태의 시장 참고 정보를 제공하는
개인용 국내 리서치 모니터링 MVP다.

초기 목적은 개인 Telegram 알림이었지만, 현재 범위는 아래까지 확장되어 있다.

- Naver 리포트 수집/저장/요약
- Telegram 전일 요약, 장중 알림, 명령 처리
- Windows Task Scheduler 기반 운영
- 로컬 운영자용 `admin-gui`
- 친구 공유 후보인 GET-only 사용자용 `web-view`
- KRX Open API 기반 가격/거래량/ETF/지수 참고 데이터
- KRX Data Marketplace 기반 투자자 수급 참고 데이터
- 관찰탭 기반 read-only 백테스트/후보 근거 검토
- 저장 데이터 기반 관찰 후보 추천, 우선 확인, 관심도 높은 흐름 정렬

이 프로젝트는 매매 추천을 하지 않지만 관찰 대상을 추천한다. 사용자-facing 기능은 `오늘의 관찰 후보`, `우선 확인`, `관심도 높은 흐름`, `왜 눈에 띄는지`처럼 저장 데이터 근거를 정렬해 보여줄 수 있다. 금지되는 것은 `매수 추천`, `매도 추천`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, `투자등급`, `오를 종목` 단정 같은 투자 의사결정 문구다.

## 대상 데이터 소스

| 영역 | 기준 소스 | 사용 목적 |
| --- | --- | --- |
| 리포트 | Naver Stock `research/company` 국내종목 | 종목별 리포트, 발행사, 목표가, 의견, 발행일시 |
| 주가/거래량/거래대금 | KRX Open API | 선택일 기준 시장 참고값, 웹뷰 현재가/거래량/ETF/지수 표시 |
| ETF/지수 | KRX Open API | ETF 흐름, 주요 지수, 시장 참고 카드 |
| 투자자 수급 | KRX Data Marketplace `[12008]`, `[12009]`, `[12010]` | 시장/종목/순매수 상위 수급 참고 |
| 업종/테마 | 별도 taxonomy/cache/snapshot layer | 화면 분류와 순환매 참고. KRX 공식 taxonomy로 부르지 않는다. |

리포트 원본은 Naver가 소유하고, 가격/거래대금/ETF/지수는 KRX가 소유한다.
업종/테마는 현재 프로젝트의 표시/분류 계층으로 관리한다.

## 현재 운영 스케줄

시간대는 `Asia/Seoul (KST)`이다.

| 작업 | 현재 계약 |
| --- | --- |
| `StockMonitor-KrxDailyBackfill` | 한국 영업일 `08:10`. 전 영업일 또는 최근 누락 KRX Open API snapshot 보강 |
| `StockMonitor-Notify` | 한국 영업일 `08:20`. `08:10` KRX 보강 이후 전 영업일 briefing 요약을 Telegram으로 발송 |
| `StockMonitor-Poll` | 한국 영업일 `08:30~16:30`, 30분 간격 |
| `StockMonitor-TelegramCommands` | 한국 영업일 `08:00` 시작, `16:30`까지 1분 간격 명령 확인 |
| `StockMonitor-KrxFlowLoginReminder` | KRX 수급 검증일 전용 선택 작업. 기본 운영에서는 비활성 |
| `StockMonitor-Shutdown` | desktop-validation 기간 `17:10`, 내부 영업일 가드 적용 |

`operation_profile`은 `desktop-validation`, `mini-pc`, `manual-only`를 지원한다.
미니 PC 이전 전까지는 shutdown 정책과 외부공유 정책을 별도로 확인해야 한다.

## 수집 및 저장 요구사항

### Naver 리포트

수집 대상은 `{NAVER_RESEARCH_URL}`의 국내종목 리포트다.
다른 탭은 아직 기본 운영 범위가 아니다.

리포트는 아래 식별값을 최대한 안정적으로 조합해 중복 저장을 방지한다.

- 종목명
- 종목코드
- 리포트 제목
- 발행사
- 발행일시
- source id 또는 URL 기반 식별값

최소 저장 항목:

- 종목명, 종목코드
- 제목
- 발행사
- 발행일시
- 목표주가 원문과 숫자 정규화 값
- 투자의견 원문과 정규화 값
- 수집 시각
- source URL 또는 source id

### KRX Open API

KRX 일별 snapshot은 stock/ETF/index reference layer로 저장한다.
자동 scheduled path는 이전 영업일 또는 최근 누락일만 대상으로 하며, 대량 재기준화는 `db-verify`, `db-backup`, `--dry-run`, `--confirm`, `--i-backed-up` 절차를 거친다.

### KRX Data Marketplace 수급

수급 데이터는 아직 scheduled ingest를 켜지 않는다.
현재는 검증된 로그인/샘플/수동 backfill/read-only 표시 경로만 사용한다.

수급은 다음 원칙을 따른다.

- `[12008]`: 시장 투자자별 거래실적
- `[12009]`: 개별종목 투자자별 거래실적
- `[12010]`: 투자자별 순매수 상위종목
- 저장된 값만 웹뷰에 표시
- 실시간 호출, 매매 추천, 공개 숫자 점수화, Telegram 매매 후보 알림과 연결하지 않음

## 집계 및 표시 요구사항

### 일간 리포트 집계

집계 단위는 `종목 x 영업일`이다.
`언급횟수`는 해당 영업일의 신규 리포트 건수다.

집계는 `stock_code`를 우선 기준으로 묶는다.
코드 없는 리포트는 같은 날짜/같은 종목명에 단일 코드 후보가 있을 때만 해당 코드 그룹에 흡수한다.
충돌하거나 후보가 없으면 normalized stock name fallback 그룹으로 둔다.

대표 종목명은 그룹 내 최빈 이름을 우선하고, 동률이면 최신 `published_at`, `collected_at`, `identity_key` 순서로 고른다.

### 목표주가

- 목표주가 범위는 유효 숫자만 사용해 `최저값 ~ 최고값`으로 계산한다.
- `N/A`, `-`, 빈 값, 파싱 불가 값은 range/ranking/대표값 계산에 섞지 않는다.
- 원문 결측은 상세 화면에서만 missing state로 노출할 수 있다.

### 투자의견

투자의견은 `매수`, `중립`, `매도`, `N/A`로 정규화한다.
동률이면 `매수 > 중립 > 매도 > N/A` 우선순위를 따른다.

### 발행사 표시

같은 발행사가 하루에 여러 건을 낸 경우 `발행사명(n)`으로 묶는다.
사용자 화면에서는 과밀 표시를 피하고, 2개 이상 발행사는 `대표증권사 외 N곳` 같은 display-only 표기를 사용할 수 있다.

## Telegram 요구사항

Telegram은 개인 운영용 알림과 명령 처리 채널이다.

| 기능 | 요구사항 |
| --- | --- |
| 전일 요약 | 다음 영업일 `08:20` 발송. `08:30` 이후 지연 실행은 기본 skip, `--allow-late`일 때만 우회 |
| 기본 포맷 | `scheduled-notify`는 당분간 `briefing` 기본값. 기존 포맷은 `--format summary`로 우회 |
| 테스트 발송 | `send-test-notification` 기본값은 기존 `summary` 유지 |
| 장중 알림 | 30분 수집 후 신규 리포트/0건 상태를 알림 |
| 페이징 | `다음`, `전부`, `처음` |
| 명령 | `/명령어`, `/도움말`, `/메모`, `/종목코드`, `/종목검색`, `/상태`, `/오늘돌아?`, `/스케줄상태`, `/웹뷰주소` |
| Replay safety | `/메모`, `/체크 로그인`, daily fragment는 중복 side effect를 방지 |

전일 요약 production 발송은 fragment run/fragment 상태를 DB에 저장한다.
중간 실패 후 재시도 시 이미 성공한 fragment는 다시 보내지 않는다.

## Admin GUI 요구사항

`admin-gui`는 운영자 전용 로컬 제어 화면이다.

요구사항:

- 기본 loopback-only
- 외부 공유 금지
- scheduler 상태 확인
- no-run calendar
- safe settings 표시/수정
- audit log 표시
- operation profile 확인/수정
- 최근 리포트/발송/운영 이벤트 확인
- Shutdown 즉시 실행 차단

`admin-gui`는 친구용 정보 화면이 아니다.

## 사용자용 web-view 요구사항

`web-view`는 별도 GET-only/read-only 사용자 화면이다.
`admin-gui`의 read-only mode가 아니라 독립 surface로 유지한다.

노출 가능:

- 날짜 선택
- 일일 리포트 요약
- 선택 종목
- 선택 종목 리포트
- 업종/테마 참고
- ETF/시장 참고
- 저장된 KRX 가격/거래량/수급 참고
- 관찰탭의 read-only 반응/근거 값
- 순환매 이미지 및 overlay 참고

노출 금지:

- scheduler 제어
- shutdown
- `.env`
- Telegram token/chat id
- DB path
- operator-status 내부 health/scheduler/worker detail
- admin audit/internal setting
- POST/PUT/PATCH/DELETE control API

## 관찰/백테스트/관찰 후보 추천/점수화 경계

현재 관찰탭은 read-only evidence surface이며, 저장 데이터 기반 관찰 후보 추천과 우선 확인 정렬을 제공할 수 있다.

허용:

- 오늘의 관찰 후보
- 우선 확인
- 관찰 우선순위
- 관심도 높은 흐름
- 왜 눈에 띄는지 설명
- 리포트 후 `1/5/10/20영업일` 반응 산출
- 목표가 괴리율
- 목표가 진행률
- 수급 존재 여부
- 거래대금
- 외국인 순매수 상위 포함 여부
- missing/caution label

금지:

- 매수 추천
- 매도 추천
- 지금 사라/팔아라
- 진입가
- 청산가
- 익절가
- 목표 수익률
- 확신도
- 투자등급
- 오를 종목 단정
- 자동 매매/전략 제안처럼 보이는 문구
- Telegram 매매 후보 알림
- public scored investment ranking

내부 scoring draft CLI는 research-only이며 public surface와 연결하지 않는다.

## 데이터 품질 규칙

모든 변경은 raw/source, parsed/storage, aggregate, display 값을 분리한다.

- 원본 결측값은 원본으로 보존 가능
- 계산에는 유효 숫자만 사용
- 표시값은 사용자 문맥에 맞게 정제
- fallback은 반드시 fallback임을 표시
- 최신값을 과거 날짜에 조용히 섞지 않음
- KRX snapshot이 없는 선택일은 최신값으로 대체하지 않음

## 보안 및 외부 공유

외부 공유 후보는 `web-view`뿐이다.
`admin-gui`는 로컬 또는 본인 원격관리 전용이다.

현재 방침:

- Docker는 보류
- Windows 직접 실행 + Task Scheduler 유지
- N100 mini PC 복원과 기본 상시 운영 준비는 완료
- Cloudflare Tunnel은 `web-view` 포트만 후보이며 provider binding과 최종 URL smoke가 남음
- Tailscale은 본인 원격관리 후보
- entry-code gate는 가벼운 1차 보호로 사용 가능
- 외부 공유 전 `external-web-view-sharing-plan --json`으로 read-only 공유 순서를 확인
- Cloudflare provider URL이 생기면 `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL`로 최종 검증
- Tunnel target은 `{LOCAL_WEB_VIEW_TARGET}` 같은 loopback `web-view` 포트만 허용
- 최종 URL smoke에서 Cloudflare Access 로그인 HTML은 차단 응답으로 허용하지만, `admin-gui`처럼 보이는 응답은 항상 실패 처리

## 현재 불안정/관찰 필요

- 첫 mini PC 실영업일 scheduled-run 관찰
- Naver parser drift fixture 추가
- Telegram timeout-after-send residual duplicate risk 추적
- 웹뷰 표시값 QA 지속
- category snapshot fallback 축소
- KRX Data Marketplace broad scheduled ingest는 별도 승인 전까지 비활성
- 외부 공유는 Cloudflare/Tailscale provider binding과 최종 shared-URL smoke 전까지 보류
- 2027년 이후 한국 휴장일 유지보수

## 범위 밖

- 미국장 확장
- `admin-gui` 또는 control surface 외부 공개
- 최종 provider smoke 전 Cloudflare URL 공유
- 다중 사용자 권한 관리
- public trading recommendation/scored investment decision
- broad/all-stock KRX Data Marketplace scheduled ingest enable

## 대표 문서

- `docs/codex/current-work.md`
- `docs/codex/execution-roadmap.md`
- `docs/codex/next-phase.md`
- `docs/codex/surface-contract.md`
- `docs/codex/data-source-policy.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/krx-market-data-runbook.md`
- `docs/codex/backtest-observation-plan.md`
- `docs/codex/scoring-draft-plan.md`
