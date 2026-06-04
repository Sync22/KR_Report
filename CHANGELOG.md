# 변경 이력

> 개인용 네이버 증권 리포트 모니터 `Stock Monitor`의 주요 변경 기록입니다.  
> 초기 일부 항목은 대화 흐름과 실제 반영 시점을 기준으로 정리했습니다.

## 2026-05-20

- 메인 PC 기준으로 `시황 예시` 사진을 실제 stored-data 운영 후보로 반영했다. `web-view` daily `market_briefing`에 `time_slot_mood_card`를 추가해 `국장 시장 분위기`, headline, `지수`, `주요 종목`, `핵심 포인트`, `확인 포인트`, source gap을 노출하고, `market-briefing-readiness` JSON에서도 같은 preview contract와 source gap count를 확인할 수 있게 했다. 이 카드는 read-only/manual-review 후보이며 live fetch, public scoring, recommendation, production integration, scheduler registration은 모두 false로 고정된다.
- `오늘 읽을 요약` 상단에 예시 사진 구조를 따른 compact market mood card를 렌더링했다. 메인 PC 실데이터 smoke에서 최신 report date `2026-05-15`는 리포트 51건/JYP Ent. 7건 headline과 `2026-05-14` KRX index/turnover fallback을 명시했고, intraday index/stock quote source는 아직 미구성 source gap으로 표시한다.

## 2026-05-19

- 스크래핑/프로젝트 관리 후보 도구를 read-only로 실측했다. Naver는 기존 Playwright/API inspect가 정상 파싱했고, KRX Data Marketplace는 `request-only`와 raw login-check가 통과해 현재는 Botasaurus보다 기존 경로가 우선임을 확인했다. Botasaurus는 브라우저 probe 전용 스크립트를 추가했고, CodeGraph는 로컬 설치 후 54개 Python 파일/1,450 nodes/5,570 edges를 인덱싱했다. `codex-complexity-optimizer`는 전역 skill 설치 대신 로컬 scanner를 사용해 `analysis/backtest_observation.py`와 `cli.py` 중심의 refactor 후보를 문서화했다.
- 외부 퀀트 후보 비교를 코드와 문서에 research-only로 고정했다. `scripts/experimental/kronos_backtest_experiment.py`를 추가해 저장된 KRX OHLCV와 저장 리포트 후보만으로 Kronos 백테스트를 돌릴 수 있게 했고, `2026-01-02`~`2026-05-15` 전체 저장 후보 sweep 결과 D+10만 연구 가치가 있으며 생산 정렬 신호로는 채택하지 않는 것으로 `next-phase`에 기록했다. Hugging Face 모델 캐시는 `scripts/experimental/.hf-kronos/`로 격리하고 git 추적에서 제외했다. QuantDinger와 나머지 외부 비교 후보는 환경 준비가 필요한 상태로 낮춰 기록했다.
- 실데이터 백테스트 관찰을 `web-view` 후보근거 정렬에 좁게 반영했다. 공개 점수/추천/등급은 추가하지 않고, 내부 정렬용 임시값으로만 `외국인 순매수 상위`와 `mention_count=2~3` 관찰 신호를 보강해 리포트 다건수만으로 후보가 과도하게 앞서지 않도록 했다.
- `scrcpy`를 제외한 GitHub/tool 북마크(`codegraph`, `codex-complexity-optimizer`, `QuantDinger`, `botasaurus`)를 로컬 설치/사용 후보로 선언했다. 모두 개발/연구/검증 보조도구로만 허용하며, 생산 런타임 의존성, 공개 `web-view` 기능, 스케줄러 자동화, 광범위 수집, 브로커/매매 자동화로 연결하지 않는 경계를 `AGENTS`, `operator_memos`, `current-work`, `execution-roadmap`에 반영했다.
- 본컴을 GitHub `origin/main` 기준으로 맞춘 뒤, 기존 데스크톱 cutover에서 확인된 `StockMonitor-WebViewManual` 누락 보강을 다시 적용했다. 원격 기준의 `StockMonitor-WebViewHourlyRestart`는 유지하면서 `scheduler-control --task web-view-manual`과 `--task all`이 수동 웹뷰 스케줄러 작업까지 포함한다.

## 2026-05-15

- `.env.example`을 미니PC 이전용 섹션형 예시로 정리했다. Telegram, scheduler, access-code, KRX Open API, KRX Data Marketplace 값을 필수/선택 맥락으로 구분하고, migration archive에는 `.env`와 access-code hash를 넣지 않는 기준을 README와 mini-PC handoff에 다시 고정했다. 또한 `verify_migration_archive.ps1`의 required-entry 목록에 `.env.example`을 추가해 대상 PC에서 `.env` 작성 기준 파일이 누락된 archive를 실패 처리한다.
- `documentation-index.md`, `project-map.md`, `current-work.md`, `execution-roadmap.md`의 미니PC/외부공유 안내를 현재 script set과 맞췄다. 특히 source-desktop cutover helper와 `.env.example` archive inclusion을 canonical 문서에서 추적 가능하게 했다.
- `verify_migration_archive.ps1`의 required-entry 목록을 `mini-pc-preflight`의 필수 프로젝트/스케줄러 파일 기준에 더 가깝게 확장했다. 이제 `CHANGELOG.md`, `stock_research_monitor_mvp.md`, `execution-roadmap.md`, `surface-contract.md`, `data-quality-checklist.md`, 실제 scheduled run wrapper 누락도 archive 검증 단계에서 잡는다.
- `verify_migration_archive.ps1`의 required-entry 목록에 canonical 문서군과 사용자용 web-view/순환매 자산(`example/Cycle.jpg`, rotation JSON 3종)을 추가했다. 미니PC에서 새 세션이 현재 문서 기준과 화면 자산 없이 시작되는 archive를 복사 단계에서 차단한다.
- `scripts/disable_source_desktop_scheduler_tasks.ps1`를 추가했다. 미니PC 스케줄러 검증 후 기존 데스크톱의 StockMonitor 작업을 `-DryRun`으로 확인하고 `-ConfirmDisable`로 비활성화해 두 호스트가 동시에 수집/발송하지 않도록 한다.
- `mini-pc-preflight`와 archive required-entry 기준에 source desktop cutover helper를 포함했다.
- `verify_migration_archive.ps1`의 required-entry 목록을 `mini-pc-preflight` 필수 스크립트와 맞췄다. archive 생성/검증 스크립트와 외부공유 readiness 스크립트도 zip 내부 필수 항목으로 확인한다.
- `setup_mini_pc_environment.ps1`의 setup-time readiness가 `.env` 요구도 건너뛰도록 했다. 기본 migration archive가 `.env`를 제외하므로, 미니PC 첫 설치는 env 없이 venv/install/기본 점검을 진행하고 이후 대상 PC에서 `.env`를 직접 작성한 뒤 최종 readiness에서 `--require-env`를 확인한다.
- `verify_mini_pc_readiness.ps1`에 `-SkipEnvRequirement`를 추가했다. 초기 setup 단계에서는 env 요구를 건너뛰고, 실제 운영/외부공유 전에는 기존처럼 env 존재를 요구할 수 있다.
- `verify_migration_archive.ps1 -FailOnSensitiveEntries`가 수동 archive 안의 `data/backups`, `data/restore-smoke`, 로그 파일, 중첩 `Stock_Moniter_migration_*.zip`도 차단하도록 확장됐다. 기본 생성 스크립트가 제외하는 불필요/민감 항목을 수동 zip 검증에서도 잡는다.
- `verify_migration_archive.ps1`가 필수 이관 항목(`AGENTS.md`, `pyproject.toml`, `src/stock_monitor/cli.py`, `data/stock_monitor.db`, canonical docs, mini-PC scripts 등)을 확인하도록 했다. 해시가 맞고 민감 파일이 없어도 잘못 만든 zip이면 실패한다.
- `create_migration_archive.ps1`의 기본 제외 규칙에 `*.log`와 `data/*.log`를 추가했다. 이관 zip에 불필요한 운영 로그가 섞이지 않게 한다.
- `verify_external_web_view_readiness.ps1`의 실패 출력을 정리했다. 외부공유 preflight가 access-code disabled 등으로 실패할 때 PowerShell stack trace 대신 실패 단계와 `access-code set/status` 다음 조치를 출력하고 종료한다.
- 미니PC 초기 setup 흐름을 실제 archive 정책에 맞췄다. `setup_mini_pc_environment.ps1`는 archive가 `data/backups`를 제외하는 점을 고려해 setup-time readiness에서 백업 요구와 restore-smoke를 건너뛰고, post-restore 백업 생성 후 `verify_mini_pc_readiness.ps1` 전체 검증을 실행하는 흐름으로 문서화했다.
- `verify_mini_pc_readiness.ps1`에 `-SkipBackupRequirement`를 추가했다. 초기 설치처럼 백업이 아직 없는 단계에서는 백업 요구와 restore-smoke를 스킵하고, 최종 readiness에서는 기존처럼 최신 백업과 restore-smoke를 강제할 수 있다.
- `verify_migration_archive.ps1`에 `-FailOnSensitiveEntries`를 추가했다. 수동 archive나 비로컬 전송용 archive 검증 시 `.env` 또는 `data/access_code.json`이 발견되면 warning에 그치지 않고 실패시킬 수 있다.
- `verify_migration_archive.ps1`가 archive 내부 entry 목록을 실제로 몇 개 검사했는지 `archive_entries_checked`로 출력하도록 했다. 민감 파일 검사 단계가 수행됐는지 복사 후 검증 로그에서 바로 확인할 수 있다.
- `verify_migration_archive.ps1`의 민감 파일 warning이 규칙명 대신 실제 zip 내부 경로를 출력하도록 했다. 폴더째 수동 압축된 `.env`나 `data/access_code.json`도 suffix 기준으로 감지한다.
- 기본 migration archive에서 `data/access_code.json`을 제외하도록 했다. access-code hash도 외부공유 인증 재료이므로 대상 미니PC에서 `access-code set`으로 새로 설정하는 기준으로 정리했다.
- 외부공유 preflight에서 access-code가 필수인데 꺼져 있을 때 `recommended_commands` 맨 앞에 `python -m stock_monitor access-code set`과 `python -m stock_monitor access-code status`를 표시하도록 했다. 이제 `verify_external_web_view_readiness.ps1` 실패 출력만 보고도 다음 조치를 바로 알 수 있다.
- `operator-status`의 `live_observation`에서 아직 예정 시간이 오지 않은 당일 작업을 `missing` 대신 `pending`으로 표시하도록 했다. 예를 들어 `StockMonitor-KrxMentionedFlowBackfill`은 `16:30` 전까지 실행 이벤트가 없어도 미실행 누락처럼 보이지 않는다.
- Task Scheduler metadata `access_denied`의 strict health 의미를 테스트/문서로 고정했다. 당일 `live_observation`이 있어도 작업 등록/다음 실행 예약을 검증한 것은 아니므로 `--health-exit`은 계속 fail을 반환한다.
- `operator-status` 텍스트 출력에도 strict health 해석 줄을 추가했다. 이제 `access_denied` 상태에서 당일 실행 흔적이 같이 보여도, 해당 흔적이 스케줄러 메타데이터 검증을 대체하지 않는다는 점이 바로 보인다.
- 정상 운영에서 꺼두는 optional `StockMonitor-KrxFlowLoginReminder`는 metadata `access_denied`를 core scheduler fail이 아니라 warning으로 분리했다. Notify/Poll/KRX daily backfill/KRX mentioned flow/TelegramCommands 같은 핵심 작업의 `access_denied`는 계속 fail이다.
- `sector_catalog_not_refreshable` 경고의 의미를 README에 명확히 했다. `source=naver_quote` 업종 row는 화면 표시/cache용 분류이며, 검증된 `source=naver_industry` 또는 `source=naver_upjong` row만 `refresh-industries` 대상이다.
- `refresh-industry`가 구형 모바일 `front-api` 404 시 현재 Naver PC 업종 API(`upjong/{no}/info`, `upjong/{no}/stocklist`)로 fallback하도록 보강했다. `refresh-industry 307 --dry-run`으로 `전자제품` 업종 preview가 DB 쓰기 없이 동작함을 확인했다.
- `category-catalog discover-industries`를 추가했다. 현재 Naver PC 업종 catalog를 DB 쓰기 없이 조회하고, 각 후보별 `category-catalog add sector ... --source naver_industry` 명령을 출력해 업종 fallback 축소 작업이 브라우저 수동 추적에 의존하지 않게 했다.
- `category-catalog discover-industries` 출력에 기존 sector catalog 표시명 매칭 정보를 추가했다. 예를 들어 현재 후보 `광고`는 기존 `12/naver_quote`와 같은 표시명으로 `existing=Y(12/naver_quote)`가 표시되어, 검증된 `naver_industry` row를 새로 추가할지 기존 display/cache row와 충돌하는지 먼저 볼 수 있다.
- 검증된 Naver PC upjong 후보 8개를 기존 `naver_quote` row와 별도로 `source=naver_industry` catalog에 추가했다. 대상은 `가정용품(297)`, `광고(310)`, `방송과엔터테인먼트(285)`, `상업서비스와공급품(324)`, `섬유,의류,신발,호화품(274)`, `손해보험(315)`, `전문소매(328)`, `전자제품(307)`이다. DB 백업 후 `refresh-industries --enabled --snapshot-date 2026-05-15 --confirm`으로 234개 dated sector membership row를 저장했고, `db-verify`의 `sector_catalog_not_refreshable` 경고가 사라졌다.
- KRX Open API endpoint 호출은 성공했지만 파싱/저장 가능한 row가 0건인 경우 `fetch-snapshot` operation event를 `success`가 아니라 `empty`로 기록하도록 했다. `krx-backfill-missing` 요약 이벤트도 실행 후 endpoint가 계속 기준 미달이면 `empty` 또는 `partial`로 남겨 최신일 API 미게시 상태가 실제 적재 완료처럼 보이지 않게 했다.
- `operator-status`의 `live_observation`도 `empty`/`partial` KRX backfill 이벤트를 단순 `observed`가 아니라 `attention`으로 분류하고 health warning에 포함하도록 했다. 기존처럼 `success`로 남은 이벤트라도 해당 날짜의 KRX daily endpoint row가 기준 미달이면 `incomplete_snapshot` warning으로 보정한다.
- `operator-status` 텍스트 출력에서도 live observation의 attention 사유를 `attention(incomplete_snapshot)`처럼 함께 보여주도록 했다.
- `operator-status`의 최근 운영 이벤트 목록도 표시용 status를 보정한다. API/JSON의 원본 `status`는 그대로 두고 `status_display`만 추가해, KRX backfill은 `success(attention:incomplete_snapshot)`, 0행 fetch는 `success(attention:empty_rows)`로 보여 저장된 과거 status와 실제 데이터 상태가 엇갈려 보이지 않게 했다.
- `operator-status` 텍스트 출력 상단에 health `failing_checks`와 `warning_checks`를 각각 `실패 항목`, `확인 항목`으로 표시해 JSON을 열지 않아도 현재 fail/warn 원인을 바로 볼 수 있게 했다.
- `2026-05-15` elevated/local `operator-status --json --health-exit`로 Task Scheduler metadata를 재확인했다. `Notify`, `Poll`, `KrxDailyBackfill`, `TelegramCommands`, `Shutdown`은 healthy/running이고, `StockMonitor-KrxMentionedFlowBackfill`은 등록된 상태다. 이후 첫 `16:00` 실행은 KRX 메타데이터 미해결 종목 때문에 실패했고, 코드 패치와 bounded retry 후 operation-event 계층은 `completed_with_warnings`로 정상화됐지만 Task Scheduler `LastTaskResult=1`은 다음 scheduled run 전까지 남는다.
- `scheduled-krx-mentioned-flow-backfill --date 2026-05-15 --dry-run --json`으로 첫 16:00 보강 폭을 확인했다. 당일 리포트 언급 종목 28개, 최근 31일 raw 후보 583콜 중 기본 cap 300콜만 계획되므로 첫 실행은 최신일 우선으로 일부 처리하고 다음 실행에서 이어받는 것이 정상 동작이다.
- `StockMonitor-KrxMentionedFlowBackfill`의 첫 실제 실행에서 KRX 메타데이터가 없는 언급 종목이 1건만 있어도 전체 작업이 실패하던 문제를 수정했다. 이제 스케줄러용 언급종목 수급 보강은 `unresolved_stock_codes`를 계획/결과에 남기고, 해당 종목은 KRX 요청 전에 건너뛰며, 나머지 resolvable 종목은 계속 처리한다. `2026-05-15` 기준 unresolved는 `351020`, `233990`, `052960`이고, dry-run은 28개 언급 종목 중 25개 resolvable 종목으로 504 raw callable candidates / 300 planned calls를 만든다. 패치 후 `--max-calls 5` bounded retry로 65개 row 저장과 `completed_with_warnings` operation event를 확인했다. 단, Windows Task Scheduler의 `LastTaskResult=1`은 이미 실패한 16:00 작업 메타데이터라 다음 scheduled run 전까지 health fail로 남는다.
- Naver live parser drift fixture `data/naver_fixtures/naver_research_2026-05-15.json`을 추가했다. `inspect-page --require-parsed-reports`로 저장 당시 API 20건 파싱을 확인했고, 저장 fixture regression 테스트도 추가했다.
- KRX Data Marketplace source-lane 문구를 현재 운영 정책과 맞췄다. broad scheduled ingest는 계속 금지하되, `StockMonitor-KrxMentionedFlowBackfill`의 same-day report-mentioned `[12009]` recent 31-day 자동 보강은 예외로 명시한다.
- 사용자용 `web-view`와 canonical 문서의 업종/테마 분류 부족 안내를 `최신 저장 분류 기준`으로 정리했다. API/QA의 내부 기계값(`latest_mapping_fallback`, `category_mapping_fallback`)은 유지하지만, 친구용 화면과 대표 문서에는 `최신 매핑` 같은 구현 용어가 새로 노출되지 않게 했다.
- `category-snapshot-plan`에 source-date capture guard를 추가했다. 과거 fallback 날짜에는 현재 업종/테마 구성을 과거 snapshot처럼 저장하는 refresh 명령을 제안하지 않고, `source_date_capture_allowed=false`와 차단 사유를 출력한 뒤 사용자 화면 QA 명령만 남긴다.
- 사용자용 `web-view` 일일 종목 요약의 KRX 참고 표시를 보정했다. 선택 날짜의 KRX 마감 스냅샷 자체가 아직 없을 때는 종목별로 `KRX 없음` 대신 `마감 대기`를 표시해 실제 종목 결측과 최신일 데이터 대기를 구분한다.
- 같은 상황에서 일일 종목 요약 상태 문구도 `선택 날짜 KRX 마감 대기`로 바꿨다. 이제 최신일 Open API 대기 상태를 결측처럼 읽히게 하지 않는다.
- `web-view-value-qa` 정적 HTML guard에 과거 문구 `선택 날짜 KRX 마감값 없음`을 추가했다. 최신일 데이터 대기 상태를 결측처럼 표현하는 문구가 다시 들어오면 QA에서 실패한다.
- 아침 전일자 briefing과 `market-briefing` 상단 기준 문구를 `KRX 저장값은 항목별 기준일 표시` 원칙으로 정리했다. KRX 지수/거래대금/수급 기준일이 리포트일과 다를 수 있음을 첫 줄부터 명확히 한다.
- 사용자용 `web-view`의 daily `category_contract`가 실제 source-date snapshot 존재 여부가 아니라 화면 rollup 유무만 보고 fallback으로 판단하던 문제를 수정했다. 이제 선택 날짜 이하의 저장 카테고리 스냅샷이 있으면 해당 날짜 요약 종목과 매칭되는 rollup이 없어도 `dated_snapshot`으로 표시되어 불필요한 QA warning이 줄어든다.
- 사용자용 `web-view`의 상단 확인 포인트에서 Telegram용 문구인 `사용자 웹뷰에서 확인`이 그대로 보이지 않게 했다. 웹뷰 내부에서는 `아래 종목/관찰 탭에서 세부 근거 확인`으로 표시한다.
- `선택 종목 리포트`의 `의견없음 제외` 필터 기본값을 해제했다. 상세 근거 화면은 `의견 없음`과 `목표가 -` 리포트도 기본으로 보여 주고, 사용자가 원할 때만 필터로 숨기도록 맞췄다.
- `관찰` 탭의 evidence note가 목표가는 있는데 KRX 기준가가 아직 없는 최신일 종목을 `목표가 없음`으로 잘못 표시하던 문제를 수정했다. 이제 `목표가 있음`과 `KRX 기준가 대기`를 분리해 보여 준다.
- `관찰` 탭의 `리포트 후 흐름` 표를 압축했다. D+1/D+5/D+10/D+20을 각각 별도 열로 펼치지 않고 `리포트 후 반응` 한 열에 가능한 구간과 대기 구간을 요약해 표시한다.
- `web-view-value-qa` 정적 HTML guard에 예전 `D+1/D+5/D+10/D+20` 별도 열과 8열 관찰표 패턴을 추가했다. 관찰탭이 다시 검증표처럼 길어지는 회귀가 들어오면 QA에서 실패한다.
- `web-view-value-qa`에 `--recent-business-days N` 옵션을 추가했다. 이제 최근 한국 영업일 N개를 자동으로 골라 사용자용 public surface QA를 실행할 수 있어, 날짜를 매번 수동으로 나열하지 않아도 된다.
- `RuntimeConfig.from_env()`가 `.env` 값을 `os.environ`에 주입하지 않도록 수정했다. `.env`는 설정 병합에만 사용하고 프로세스 전역 환경변수는 오염시키지 않으므로, pytest 중 실 운영 DB 경로가 임시 DB 테스트로 새는 위험을 줄였다.
- 직전 테스트 환경 누수로 운영 DB에 들어간 pytest fixture 행을 백업 후 정리했다. 테스트 리포트/시세/operator control/category/수급 fixture 값을 제거 또는 정상 백업 기준으로 복원했고, `2026-05-14` 요약을 재생성한 뒤 `db-verify` 정상 상태를 확인했다.
- `market-briefing` 메시지에도 public-safe QA guard를 추가했다. `추천`, `점수`, `등급`, `전략 제안`, `매수 기회` 같은 금지 문구와 `N/A`/`NULL`류 원시 결측 마커가 들어가면 preview/send 전에 실패한다. `개인 매수 우위` 같은 수급 방향 문구는 허용한다.
- 사용자용 `web-view` 상단 `오늘 읽을 요약`의 거래대금 참고 표시를 압축했다. 저장 DTO의 raw `turnover` 값은 유지하되 브리핑 전용 `turnover_display`를 사용해 `11,875,492,405,612원` 같은 긴 원 단위 대신 `11.9조`, `7709억`처럼 읽히게 했다.
- `web-view-value-qa`에 시장 브리핑 거래대금 표시값 검사를 추가했다. `market_briefing.turnover_summary`의 `turnover_display`가 다시 긴 원 단위 raw 금액으로 노출되면 `public_market_briefing_raw_turnover_display` issue로 실패한다.
- 사용자용 `web-view`의 `일일 종목 요약` 기본 노출량을 6종목으로 제한하고 `더 보기` 버튼을 추가했다. 기본 화면은 2건 이상 언급 종목 6개만 먼저 보여주고, 추가 종목은 6개 단위로 확장해 화면 과밀도를 줄인다.
- `current-work`, `next-phase`, `execution-roadmap`의 실제 데이터 커버리지 기준을 운영 DB와 맞췄다. 현재 리포트/요약은 `2026-01-02`~`2026-05-15`, KRX stock/ETF/index snapshot은 `2024-11-08`~`2026-05-14`, 투자자 수급은 `2026-05-12`까지로 기록한다. `krx-baseline-analysis` 기준 `2026-05-15`는 최신일 Open API 대기 후보로 별도 표시한다.
- KRX 상세 문서(`krx-18m-backfill-analysis`, `krx-market-data-runbook`, `scoring-draft-plan`)도 같은 기준으로 보정했다. 18개월 baseline은 최신 저장일 `2026-05-14`까지 완료, `2026-05-15`는 Open API 최신일 pending으로 본다.
- 사용자용 `web-view` 관찰 탭의 KRX/반응 거래대금 표시를 조/억 단위로 압축했다. 목표가·현재가 같은 가격 표시는 그대로 두고, 관찰 근거의 거래대금만 `263,571,426,500원` 같은 긴 원 단위 대신 짧은 시장 참고값으로 읽히게 했다.
- 사용자용 `web-view` 관찰 탭의 반복 문구를 줄였다. `missing_stock_flow`, `rank_not_present`, `당일 수급 없음`, `외국인 순매수 상위 미포함`은 원본 DTO에는 유지하되 화면의 품질 플래그/관찰 근거에서는 숨기고, `수급/순위` 칸에서만 `수급 없음`, `순매수 상위 없음`으로 표시한다.
- 사용자용 `web-view` 관찰 탭의 `리포트 후 흐름` 표도 기본 6행만 표시하고 `더 보기`로 확장되게 했다. 고리포트일에 20행짜리 검증표가 한 번에 펼쳐지는 문제를 줄이고, 필요할 때만 추가 행을 볼 수 있게 했다.
- 사용자용 `web-view`의 `순환매` 탭을 누르면 `순환매 참고` 상세가 자동으로 열리도록 수정했다. 기존에는 탭 전환 후 한 번 더 펼쳐야 SVG overlay와 근거가 보여 화면이 비어 보였고, 이제 같은 날짜 overlay 요청은 중복 로드되지 않게 막았다.
- 사용자용 `web-view`의 `ETF` 탭 거래대금 표시도 조/억 단위로 압축했다. 기존에는 ETF 흐름에서 `3,281,215,703,345원` 같은 raw 원 단위가 노출됐고, 이제 `3.3조`, `9825억` 같은 시장 참고용 표시로 맞춘다.
- `순환매 참고` API가 `data/rotation_image_aliases.json`을 사용하도록 연결했다. 이제 이미지 문구 기준 라벨(`우주항공`, `게임`, `통신` 등)과 현재 업종명/좌표 키를 분리해 관리하며, 좌표 파일의 `label`을 canonical alias처럼 오용하지 않는다.
- 사용자용 `web-view`의 접힘형 `시장 참고`와 최근 KRX 흐름에서도 거래대금 표기를 조/억 단위로 통일했다. 관리자 화면의 KRX 거래대금 상위 표도 같은 압축 표기를 사용한다.
- `순환매 참고` highlight에 read-only `candidate_stocks` preview를 추가했다. 같은 날짜 리포트 요약과 exact-date KRX 주가/거래대금만 사용하며, 화면에는 `종목 참고`로 표시한다. ETF 후보는 operator-managed mapping이 생기기 전까지 비워둔다.
- `data/rotation_etf_candidates.json`를 추가하고 `순환매 참고` highlight에 read-only `candidate_etfs` preview를 연결했다. ETF 후보는 자동 추정하지 않고 operator-managed mapping에 등록된 ETF 코드만 exact-date KRX ETF snapshot으로 표시한다.
- `web-view-value-qa`에 `rotation_etf_mapping` 검사를 추가했다. `data/rotation_etf_candidates.json`의 active ETF 코드가 최신 저장 ETF snapshot에 없으면 `rotation_etf_mapping_missing_snapshot` issue로 실패해, 순환매 ETF 참고값이 조용히 사라지는 상황을 사전에 잡는다.
- `web-view-value-qa`의 `rotation_etf_mapping` 검사를 보강했다. active ETF 매핑의 업종명이 `data/rotation_overlay_coordinates.json` 좌표나 active `data/rotation_image_aliases.json` alias 어느 쪽에도 연결되지 않으면 `rotation_etf_mapping_unreachable_category` issue로 실패한다.
- `관찰` 탭의 `target_observation`에 저장 데이터 기반 `max_progress_to_min/max`, `hit_min/max_horizon_days`, `validation_window_days`를 추가했다. 목표가 진행률이 정상 해석 가능한 경우에만 최대 진행률과 목표가 도달 D+일을 표시하며, 추천/점수/등급 표현은 넣지 않는다.
- `web-view-value-qa`가 선택 날짜의 category contract가 `latest_mapping_fallback`이면 `category_mapping_fallback` warning을 남기도록 했다. 친구용 화면에서는 fallback 필터를 숨기지만, 운영 QA에서는 source-date 카테고리 스냅샷이 부족한 날짜를 계속 추적한다.
- `category-snapshot-plan`의 command template에 `web-view-value-qa --date YYYY-MM-DD --stock-limit 20` 확인 명령을 추가했다. source-date 업종/테마 snapshot 보강 후 같은 날짜 사용자용 DTO QA까지 이어서 확인하는 흐름을 한 출력에서 볼 수 있다.
- `category-snapshot-plan --json`에 날짜별 `missing_snapshot_types`와 실제 날짜가 들어간 `dry_run_commands`를 추가했다. 이제 fallback 날짜가 업종만 필요한지, 테마까지 필요한지, 그리고 어떤 dry-run을 먼저 돌릴지 출력만 보고 구분할 수 있다.
- `category-snapshot-plan`이 enabled sector catalog 중 실제 `refresh-industries`로 갱신 가능한 항목 수를 분리해 표시하도록 했다. 검증된 Naver upjong source가 없으면 `sector_catalog_not_refreshable` warning을 내고 업종 refresh 명령을 actionable template에서 제외한다.
- `db-verify`에도 category snapshot refreshability warning을 추가했다. category fallback 날짜가 남아 있는데 enabled sector catalog에 검증된 Naver upjong source가 없으면 `sector_catalog_not_refreshable`을 출력하되, 무결성 오류는 아니므로 exit code는 실패로 바꾸지 않는다.
- `operator-status` JSON/텍스트 출력에도 category snapshot coverage와 refreshability warning을 추가했다. 운영자가 DB 검증을 별도로 돌리지 않아도 fallback 날짜 수와 업종 catalog 갱신 불가 상태를 기본 상태 화면에서 확인할 수 있다.
- `category-catalog list` 출력에 catalog `source`와 `refreshable=Y/N`을 추가했다. display/cache/manual 업종 label이 왜 `refresh-industries` 대상이 아닌지 운영자가 catalog 목록에서 바로 확인할 수 있다.
- `category-catalog list --json`에도 `refreshable`과 `refresh_block_reason`을 추가했다. 관리자 화면이나 자동 점검이 텍스트 파싱 없이 display/cache/manual 업종 catalog의 한계를 읽을 수 있다.
- `refresh-industry <code>`에 `--dry-run`을 추가했다. 새 Naver upjong code 후보를 DB 쓰기 없이 fetch/preview로 확인한 뒤 catalog 등록이나 confirmed snapshot refresh로 넘어갈 수 있다.
- `refresh-industry <code> --dry-run` 출력에 다음 `category-catalog add sector ... --source naver_industry` 명령을 표시하도록 했다. 검증된 upjong code를 refresh 가능한 sector catalog로 등록하는 흐름을 텍스트 조립 없이 이어갈 수 있다.
- 업종 catalog refreshability 기준을 더 좁혔다. `sector` catalog는 `source=naver_industry` 또는 `source=naver_upjong`일 때만 `refresh-industries` 대상이 되며, `naver_quote`뿐 아니라 `operator`/custom source도 검증 전에는 batch refresh에서 제외된다.
- `krx-baseline-analysis` source-lane 출력에서 KRX Data Marketplace 정책을 현재 상태와 맞췄다. 이제 broad scheduled ingest 금지와 narrow `[12009]` same-day report-mentioned 31-day 자동 예외를 구분해 보여준다.
- 사용자용 `web-view`의 업종/테마 source-date 부족 안내에서 `fallback`, `최신 매핑` 같은 구현/검증 용어를 제거하고 `최신 저장 분류 기준`으로 바꿨다. API의 기계 필드(`latest_mapping_fallback`)는 유지하되 친구가 보는 label/notice/정적 HTML 문구는 제품 언어로 정리했다.
- `web-view-value-qa`에 `rotation_alias_mapping` 검사를 추가했다. `data/rotation_image_aliases.json`의 active alias가 `data/rotation_overlay_coordinates.json`에 없는 좌표명을 가리키면 `rotation_alias_missing_coordinate` issue로 실패한다.

## 2026-05-14

- `market-briefing` CLI를 추가해 `16:00` 전후 `오늘의 시장 분위기` 메시지를 수동 preview/선택 발송할 수 있게 했다. 저장된 당일 리포트, KRX 지수 참고, KRX 거래대금 상위 종목, KOSPI 수급 참고, 다건 언급 종목을 사용하며 `추천`, `점수`, `등급`, `전략 제안` 표현은 넣지 않는다. `scheduled-market-briefing` 후보 CLI도 추가해 영업일/no-run/중복발송/`16:00~16:45` 시간창 guard를 갖췄지만, 실제 Task Scheduler 등록은 며칠간 폰 화면 가독성 확인 후 판단한다.
- 사용자용 `web-view` 상단 `오늘 읽을 요약`을 Telegram 시장 브리핑 축과 맞췄다. 기존의 불안정한 `눈에 띄는 업종` 중심 카드 대신 `리포트 흐름`, `지수 참고`, `거래대금 참고`, `수급 참고`, `눈에 띄는 종목` 칩으로 압축 표시한다. 이 데이터는 저장된 KRX/수급/리포트 값만 사용하며 추천/점수 표현은 넣지 않는다.
- `GET /api/daily/{date}`의 `market_briefing`을 구조화했다. 기존 line 배열은 호환용으로 유지하면서 `index_summary`, `turnover_summary`, `flow_summary`, `notable_stocks`, `check_points`를 추가해 사용자용 `web-view`가 표시 텍스트를 파싱하지 않고 저장 데이터 기준 필드를 직접 렌더링한다.
- 사용자용 `web-view` 상단 `오늘 읽을 요약`에 `확인 포인트` 칩을 추가했다. Telegram 시장 브리핑의 마지막 요약 축을 화면에도 짧게 보여주되, 추천/점수/전략 문구 없이 저장 데이터 기반 확인 문장만 노출한다.
- 사용자용 `web-view`의 `관찰` 탭 문구를 압축했다. 기존 `관찰 후보 근거`, `리포트 후 반응 관찰`, `추천/점수 아님`처럼 검증/금지 문구가 앞서는 표현을 `눈에 띄는 종목`, `리포트 후 흐름`, `확인 후보` 중심으로 바꿔 친구용 화면의 첫 인상을 정보 확인 화면에 맞췄다.
- 사용자용 `web-view`의 visible `read-only` 배지를 `저장 기준`으로 바꿨다. read-only 계약은 API/테스트/문서에 유지하되, 친구가 보는 화면에는 제품 언어만 남긴다.
- 사용자용 `web-view` 선택 종목 카드의 보조 라벨을 `선택 상태`에서 `현재 선택`으로 바꿔 내부 상태 패널처럼 읽히는 느낌을 줄였다.
- 사용자용 `web-view`의 테마/순환매/KRX 안내문에서 반복되던 `추천 아님`, `점수 아님` 계열 부정문을 줄이고 `저장 데이터 참고`, `확정 판단 아님` 표현으로 정리했다. public 추천/점수 금지선은 테스트와 데이터 품질 문서에 유지한다.
- `web-view-value-qa`의 public text guard를 강화했다. 원문 리포트 제목은 그대로 허용하지만, 사용자용 DTO의 관찰/notice 문구에 `추천`, `점수`, `등급` 표현이 들어가면 부정문 형태라도 issue로 잡는다.
- `web-view-value-qa`가 사용자용 정적 HTML 템플릿도 검사하도록 보강했다. DTO가 깨끗해도 `read-only`, `관찰 후보 근거`, `리포트 후 반응 관찰`, `선택 상태`, `추천/점수 아님` 같은 과거 내부/금지 문구나 변형된 `추천`/`점수`/`등급` 문구가 화면 템플릿에 되살아나면 issue로 잡는다.
- 같은 정적 HTML QA에 `/api/status`, `/api/scheduler`, `operator-settings`, `admin-gui`, `db_path`, `.env`, Telegram token, shutdown 같은 운영자/관리자 표면 노출 검사도 추가했다.
- `web-view-value-qa`가 public DTO 내부의 금지 키도 공통 검사하도록 보강했다. `scheduler_tasks`, `worker_states`, `db_path`, `safe_settings`, `operation_profile` 같은 운영자 키가 `web-view` DTO에 섞이면 issue로 실패한다.
- `web-view-value-qa`의 스캔 범위를 daily/stock/detail 중심에서 archive, market, flow-trend, ETF-trend, rotation-overlay까지 확장했다. 날짜 QA 한 번으로 사용자용 public surface 전반의 표시값/금지 키/금지 문구를 같이 확인한다.
- `web-view-value-qa`가 intraday, category detail, category trend DTO까지 같이 검사하도록 확장했다. daily DTO의 업종/테마 rollup을 seed로 삼아 해당 카테고리 상세와 최근 흐름의 public-safe 상태를 날짜 QA 안에서 확인한다.
- `web-view-value-qa` 출력과 JSON payload에 `scanned_surfaces`를 추가했다. 운영자가 QA 결과만 보고도 static HTML, archive, daily, 관찰, 장중, 카테고리, market, ETF/flow, 순환매, stock detail이 검사 범위에 들어갔는지 확인할 수 있다.
- 사용자용 `web-view` 후보/요약 레이어에서 리포트 의견을 `매수 의견` 같은 후보 선정 이유로 승격하지 않도록 정리했다. 원문 의견은 종목 상세 리포트에는 남기되, 상단 브리핑과 확인 후보 근거는 리포트 수/목표가/시장 참고 중심으로 유지한다. `KRX 최근 흐름` DTO에는 실제 저장 기준일과 exact-date 여부를 추가해 선택일 기준값처럼 오해하지 않도록 했다.
- 사용자 피드백을 반영해 제품 원칙을 재정의했다. 앞으로는 완벽한 판단 모델보다 러프한 실사용 브리핑을 우선하고, 메모 상태는 `기반 구현`과 `작성 의도 달성`을 분리한다. 사용자용 `web-view`는 raw/process-heavy 표를 줄이고, `시장 분위기`, `눈에 띄는 종목`, `확인 후보`, `수급 참고`를 압축해 보여주는 방향으로 재설정한다. `추천`, `점수`, `등급`, 매수/매도 신호는 계속 금지한다.
- `current-work`, `execution-roadmap`, `next-phase`, `data-quality-checklist`, `operator_memos`에 새 원칙을 반영했다. 특히 `16:00` 전후 `오늘의 시장 분위기` Telegram 브리핑을 다음 제품 축으로 추가하고, 순환매/섹터 그래프/시장 분위기 항목은 단순 기반 구현이 아니라 원래 사용자-facing 의도 기준으로 다시 보도록 정리했다.
- 중복/과거 Markdown을 정리했다. `docs/codex/archive/`의 구 관리자/에이전트 문서 7개와, 현재 대표 문서에 흡수된 `future-webview-operation-plan.md`, `p2-execution-plan.md`를 삭제했다. 현재 기준은 `documentation-index.md`, `current-work.md`, `next-phase.md`, `execution-roadmap.md`, `admin-gui-plan.md`, `agent-guide.md`, `surface-contract.md`로 본다.
- 사용자용 `web-view`에서 `일일 종목 요약` 종목 행을 선택할 때 해당 종목의 대표 업종/테마 카테고리 상세와 최근 흐름도 함께 갱신되도록 수정했다. 일일 종목 DTO에 `primary_category` 힌트를 추가하고, 화면 클릭/검색 선택 흐름에서 카테고리 선택 상태를 동기화한다.
- `inspect-page --require-parsed-reports`를 추가해 Naver parser drift fixture 저장 직후 실제 리포트가 1건 이상 파싱되는지 확인하도록 했다. 빈 API/DOM 캡처나 파서 drift가 있는 fixture는 즉시 실패하므로 잘못된 fixture가 회귀 기준으로 남는 위험을 줄였다.
- `naver-fixture-validate PATH` read-only CLI를 추가해 저장된 Naver parser drift fixture가 현재 파서로 몇 건 파싱되는지 재검증할 수 있게 했다.
- 첫 live Naver parser drift fixture `data/naver_fixtures/naver_research_2026-05-14.json`을 저장하고 테스트 fixture로 연결했다. 현재 파서 기준 API 리포트 20건이 파싱된다.
- `web-view-value-qa`를 최근 날짜(`2026-05-14`, `2026-05-13`, `2026-05-12`, `2026-05-11`) 기준으로 재확인. 표시값/관찰 텍스트 issue는 0건이고, `2026-05-14`가 최신 저장 KRX snapshot `2026-05-13`보다 늦어 발생하는 market reference warning 1건만 남았다.
- `web-view-value-qa`가 표시용 필드의 `00:00` placeholder time과 display-facing `N/A`/`NULL`/`-` 계열 누출을 더 넓게 잡도록 보강. 실제 QA에서 잡힌 `investor_flow.rows[].market_label=N/A`는 사용자용 `시장 미확인`으로 정제했다.
- `investor_label` 계열도 알 수 없는 값이 `N/A`처럼 노출되지 않도록 `투자자 미확인`으로 정제했다. 최근 4개 날짜 web-view QA는 issue `0건`, KRX 최신일 미제공 warning `1건` 상태다.
- 사용자용 `web-view` 선택 종목 리포트 DTO에 `target_price_display`, `opinion_display`를 추가했다. 화면은 raw `target_price_value`/`opinion_normalized` 대신 `목표가 없음`, `목표가 100,000원`, `의견 없음`, `매수` 같은 표시값을 우선 사용한다.
- `web-view-value-qa`의 public observation wording 검사를 조정. `관찰`/후보 근거 문구의 추천·점수 표현은 계속 차단하되, 원문 리포트 제목에 포함된 “추천” 같은 단어는 원문 텍스트로 보고 오탐하지 않도록 했다. 최근 4개 날짜 `stock-limit 20` QA도 issue `0건`이다.
- Telegram timeout-after-send 추적을 operator health warning에 연결. 같은 날 `ambiguous_send=true` fragment 실패가 있으면 `operator-status`의 `warning_checks`에 `telegram.timeout_trace.ambiguous_send`가 표시된다.
- SD-5 holdout/pruning을 최신 범위로 재실행. `2026-04` D+20 holdout은 후보 107건 중 36건만 available이고 positive bucket 평균은 높았지만 4월 시장 상승 효과와 missing count가 커서 public score로 해석하지 않기로 유지했다. `2026-05` sweep은 D+20 available 0건이라 관찰 대기 상태다.
- `stock_research_monitor_mvp.md`를 초기 Telegram MVP 메모에서 현재 제품 요구사항 정의서로 현행화. 현재 범위는 Naver 리포트 수집/요약, Telegram 운영, Windows Scheduler, `admin-gui`, GET-only `web-view`, KRX Open API 시장 참고, KRX Data Marketplace 수급 참고, read-only 관찰/백테스트 경계까지 포함한다.
- `current-work`, `next-phase`, `project-map`, `documentation-index`, `execution-roadmap`, `README`의 상태 표현을 현재 DB/운영 상태에 맞춰 정리. 리포트 기준선은 `2026-01-02`~`2026-05-14`, KRX stock/ETF/index snapshot 최신 저장일은 `2026-05-13`, investor-flow 최신 저장일은 `2026-05-12`로 맞췄다.
- 문서 기준에서 public scoring/recommendation, KRX Data Marketplace scheduled ingest enable, 실제 Cloudflare 공개, 미국장 확장, 실제 mini PC 이전은 계속 범위 밖으로 고정했다.
- KRX 18개월 historical baseline은 `주식/ETF/지수 일봉=KRX Open API`, `수급=KRX Data Marketplace`로 분리하기로 확정. Botasaurus/browser probe는 Data Marketplace 세션/차단 이슈 확인용으로만 두고, stock/ETF/index 일봉에는 쓰지 않기로 했다.
- KRX Open API stock/ETF/index daily snapshot을 `2024-11-08`까지 확장해 현재 18개월 분석창(`2024-11-10`~`2026-05-13`) 기준 누락 영업일 `0건`을 확인. 최종 `db-verify`는 `integrity_check: ok`, schema `5/5`, partial KRX snapshot `0건`으로 정상.
- 18개월 KRX 일봉 적재 이후 SD-1~SD-5 관찰/백테스트 CLI를 반복 실행. `mention_count >= 2` 후보 456건 기준 D+1은 456건 전부, D+20은 290건이 반응 산출 가능했다. 내부 관찰상 `mention_count=2`와 외국인 순매수 상위 포함 여부는 계속 볼 가치가 있으나, `mention_count=4+`가 자동으로 더 강한 신호는 아니라는 점을 문서화했다.
- 4월 holdout과 5월 holdout을 나눠 검증한 결과, 5월 D+20은 아직 미래 가격 row 부족으로 해석 불가하고 4월 D+20도 시장 상승 효과가 섞였을 가능성이 있어 public score/recommendation은 계속 차단하기로 했다.
- DB 백업 후 KRX Open API stock/ETF/index daily snapshot을 5영업일 단위로 추가 backfill. `2025-12-30`, `2025-12-29`, `2025-12-26`, `2025-12-24`, `2025-12-23`, `2025-12-22`, `2025-12-19`, `2025-12-18`, `2025-12-17`, `2025-12-16`, `2025-12-15`, `2025-12-12`, `2025-12-11`, `2025-12-10`, `2025-12-09`, `2025-12-08`, `2025-12-05`, `2025-12-04`까지 적재했고, 최종 `db-verify` 정상 및 partial KRX snapshot `0건`을 확인했다.
- 18개월 백필 중 발견된 `183일 cleanup 기본값` 충돌을 `krx-market-data-runbook.md`에 고정. backtest/observation 기간에는 stock/ETF/index snapshot retention을 18개월로 보고, historical backfill은 5영업일/3초 delay와 ad-hoc closure dry-run review 기준으로 진행한다.
- 2024~2025 KRX 휴장일을 기본 holiday set에 추가. `2024-04-10` 총선, `2024-05-01` 근로자의 날, `2024-05-15` 부처님오신날, `2025-01-27` 임시공휴일, `2025-06-03` 대선 휴장, 각 연말 휴장 등이 기본 business-day 계산에 반영된다.
- `krx-baseline-analysis` CLI를 추가해 리포트/KRX 일봉/수급 커버리지, 다음 누락 후보, OpenAPI/Data Marketplace/Botasaurus 역할 비교, 550일 retention 기준을 read-only로 한 번에 확인할 수 있게 했다.
- KRX 일봉 백필/검증에서 endpoint row count가 `0`이 아니어도 비정상적으로 작은 경우 incomplete로 보고 재백필 대상으로 잡도록 보강. `db-cleanup` 기본 retention도 18개월 기준에 맞춰 `550일`로 변경했다.
- Telegram briefing TB-5.5로 저장된 KOSPI 투자자 수급 참고 줄을 추가. 수급 기준일이 리포트일보다 이전이면 `리포트일 전 최신`으로 표시해 같은 날짜 데이터처럼 오해하지 않도록 했다.
- Telegram briefing 기본 주요 종목 노출 수를 `7개`에서 `5개`로 줄였다. 기존 상세 목록은 웹뷰/summary 우회 포맷에서 확인하는 방향으로 정리한다.
- Telegram briefing TB-6로 저장된 KRX KOSPI/KOSDAQ 지수 참고와 중립적인 `핵심 포인트` 자동문장을 추가. `전략 제안`, 추천, 점수 표현 없이 지수 방향, 리포트 집중 1위, KOSPI 수급 방향만 요약한다.
- `StockMonitor-Notify` 기본 등록 시간을 `08:00`에서 `08:20`으로 조정하는 운영 기준을 반영했다. `08:10` KRX Open API 전영업일 보강 이후 저장된 KRX 지수/시장 참고값을 전일자 briefing에 반영하기 위한 순서다.
- SQLite 연결에 `busy_timeout=30000ms`를 적용해 Telegram command loop, poll, notify, web/admin 조회가 짧게 겹칠 때 즉시 `database is locked`로 실패하는 가능성을 줄였다.
- `agent-guide`, `agent-reassessment`, `krx-market-data-runbook`에 스킬/에이전트 비교표를 추가했다. Botasaurus는 KRX Data Marketplace 같은 browser-gated source probe 전용, Kronos는 stored KRX OHLCV research-only forecast 전용, 제품 구현/DB/Telegram/web-view/admin 경계는 로컬 에이전트와 테스트 경로로 처리하도록 고정했다.
- 진행률 기준을 재정립했다. 외부공유 실제 개방, 미국장 확장, 실제 mini PC 이전, public scoring/recommendation을 제외한 국내 MVP는 `90~92%`, public scoring/recommendation까지 포함하면 `75~80%`로 분리해 `execution-roadmap`, `current-work`, `next-phase`에 반영했다.
- `scheduled-krx-mentioned-flow-backfill`과 `StockMonitor-KrxMentionedFlowBackfill`을 추가했다. 평일 `16:00`에 당일 리포트 언급 종목만 대상으로 최근 31일 KRX Data Marketplace `[12009]` 종목별 수급을 보강하며, 이미 저장된 날짜/종목 row는 건너뛴다. 첫 실행 요청 폭주를 막기 위해 최신일 우선, 기본 1회 최대 300콜로 제한하고 다음 실행에서 이어받도록 했다. 시장 전체 `[12008]`, 순매수 상위 `[12010]`, 전체 종목 자동 수집은 계속 제외한다.

## 2026-05-10

- `StockMonitor-KrxFlowLoginReminder`는 KRX 자동 수급 배치가 아직 비활성인 상태에서 불필요한 Telegram 알림을 만들 수 있어 실제 스케줄러 작업을 비활성화. CLI/스크립트는 수동 검증일용으로 유지하고, `admin-gui`에서도 KRX 로그인 알림 작업을 활성화/비활성화할 수 있게 정리.
- `scheduled-telegram-commands` CLI 도움말을 legacy one-shot 경로로 명시. 실제 Task Scheduler는 계속 `scheduled-telegram-command-loop`를 사용한다.
- 사용자용 `web-view`를 `메인`, `관찰`, `ETF`, `순환매` 탭 구조로 분리. `관찰` 탭에는 저장된 리포트/KRX/수급 기반 `candidate_evidence`를 추천/점수 없이 노출하도록 준비.
- `candidate_evidence`에 저장 데이터 기반 `target_price_progress`를 추가. `관찰` 탭에서 목표가 범위 대비 `괴리`와 첫 목표가 리포트 기준 `진행`을 표시하되, 추천/점수/매수 후보 표현은 계속 차단.
- `report-backfill-preview`와 `report-backfill-manual` CLI를 추가. preview는 네트워크/DB 쓰기 없이 커버리지만 계산하고, manual 실수집은 `--confirm --i-backed-up` 없이는 DB에 쓰지 못하도록 guard를 둠.
- `docs/codex/target-price-progress-plan.md`를 추가해 목표가 괴리율/진행률 기준과 리포트 backfill 경계를 문서화.
- DB 백업(`data/backups/stock_monitor_{timestamp}_{tag}.db`) 후 `2026-04-21`~`2026-04-23` 리포트 82건을 수동 backfill. 날짜별 요약은 `2026-04-21=4`, `2026-04-22=41`, `2026-04-23=21`개로 재생성.
- DB 백업(`data/backups/stock_monitor_{timestamp}_{tag}.db`) 후 `2026-04-13`~`2026-04-17` 리포트 246건을 5영업일 단위로 수동 backfill. 기본 20페이지 한도에서는 과거 날짜가 잡히지 않아 60페이지/3000건 dry-run 후 진행.
- DB 백업(`data/backups/stock_monitor_{timestamp}_{tag}.db`) 후 남은 `2026-04-10`, `2026-04-20` 리포트 74건을 추가 backfill. `2026-04-10`~`2026-05-11` 20영업일 리포트 coverage가 `20/20`으로 채워짐.
- `report-backfill-manual`에 `--api-max-pages`, `--page-delay-seconds` 옵션을 추가해 과거 리포트 backfill 시 페이지 깊이와 요청 간 딜레이를 명령에서 직접 제어할 수 있게 함.
- 권장 분석선인 `2026-02-09`~`2026-05-11` 리포트 coverage를 `60/60` 영업일로 확장. 페이지 딜레이 `0.2~0.4초`, 단계별 DB 백업, dry-run 후 confirm 방식으로 진행했고 최종 `reports=2585`, `daily_stock_summaries=1708`, `pytest=314 passed`, `db-verify` 정상 확인.
- `admin-gui`와 사용자용 `web-view`에 공통 1차 입장코드 게이트를 추가. `python -m stock_monitor access-code set`으로 켜고, 코드는 평문이 아니라 `data/access_code.json`의 PBKDF2-SHA256 salt/hash로 보관한다.
- 신규 메모의 `다음날 2종목 후보`, `순환매 ETF/종목 후보`는 바로 추천/점수화하지 않고 `candidate_evidence` 기반 read-only 근거표부터 진행하도록 `docs/codex/candidate-evidence-plan.md`를 추가.
- 데이터 소스 정책 문서 `docs/codex/data-source-policy.md`를 추가. 리포트는 네이버, 가격/거래량/거래대금/ETF/지수/수급은 KRX, 업종/테마는 별도 taxonomy layer로 고정.
- 사용자-facing 네이밍을 `업종`, `테마`, `카테고리`, `시장 참고`, `리포트 요약`으로 정리하고, 현재 업종/테마 데이터를 `KRX 업종/테마`처럼 부르지 않도록 문서화.
- `surface-contract`, `current-work`, `execution-roadmap`, `project-map`에 데이터 소스 정책 문서 링크와 표시명 기준을 연결.
- 미니PC 이전 전 데이터 재기준화 문서 `docs/codex/data-rebaseline-plan.md`를 추가. 리포트/발송 이력은 보존하고, KRX 시장 참고 데이터는 10영업일 단위로 1월까지 확장 가능한 운영 절차로 정리.
- 문서 통폐합 기준 문서 `docs/codex/documentation-index.md`를 추가하고, KRX/수급은 `krx-market-data-runbook.md`, 관리자 화면은 `admin-gui-plan.md`, 에이전트 운영은 `agent-guide.md`, 순환매 오버레이는 `rotation-overlay-plan.md`로 대표 문서를 고정.
- `data/operator_memos.md`의 V1 완료 항목을 `[O]`로 재분류하고, 순환매 SVG overlay는 별도 `[△]` 고도화 항목으로 분리.
- `execution-roadmap`에 미국장 확장과 실제 미니PC 이전을 제외한 current-stage 100% 기준과 대표 문서 링크를 반영.
- 다음 진행 순서를 `KRX 재기준화 -> category fallback 축소 -> web-view 표시 polish -> 순환매 SVG overlay -> 상세 문서 archive 정리`로 고정.
- KRX daily snapshot 재기준화를 10영업일 단위 안전 루프로 진행해 `2026-01-02`부터 `2026-05-08`까지 stock/ETF/index daily endpoint를 확보. 각 batch 전 DB 백업을 생성했고 최종 `db-verify` 정상 확인.
- category fallback 축소 착수 중 Naver 업종 API가 `sectorType=upjong`을 요구하고, 현재 `naver_quote` sector keys는 upjong API code가 아님을 확인. `refresh-industries --enabled`가 `naver_quote` sector rows를 건너뛰도록 guard를 추가하고, `2026-05-07` 테마 `505` snapshot 67건을 추가.
- 사용자용 `web-view` 표시 polish를 진행해 `리포트 포인트`를 `리포트 요약 지표`로 정리하고, `활성 업종`을 `분류 업종`으로 바꿔 업종/테마가 저장 분류 참고값임을 명확히 표시.
- 사용자용 `web-view`의 업종/테마 최근 흐름을 기본 접힘 영역으로 조정하고, fallback 가능성이 있는 분류 데이터는 추천/판단이 아닌 참고 흐름 문구로 표기.
- 사용자용 `web-view`에 `순환매 참고` 1차 섹션을 추가. `example/Cycle.jpg`를 원본 그대로 제공하고, 수동 좌표가 있는 업종/테마만 SVG 원으로 겹쳐 표시하는 GET-only/API-only 읽기 전용 구조로 구현.
- 순환매 overlay 좌표맵을 Python hardcode에서 `data/rotation_overlay_coordinates.json`으로 분리하고, `.env.example`에 `STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH` 설정을 추가.
- 사용자용 `web-view`에서 순환매 이미지는 날짜 선택 시 즉시 로드하지 않고, `순환매 참고` 섹션을 펼칠 때만 불러오도록 lazy-load 처리.
- 사용자용 `web-view` 날짜 선택을 칩 나열 중심에서 월간 캘린더형 선택으로 개편. 각 날짜 셀에 요일과 리포트/종목 건수를 표시하고, 직접 날짜 클릭으로 이동하도록 조정.
- 선택 종목 상세의 수급/거래량 표시를 정리. 기간별 수급량은 개인/외국인/기관 3개 막대 그래프로 표시하고, 일별 수급량은 `투자자별`/`기관별` 탭으로 최신일 우선 정렬.
- 중복 계획 문서 6개를 `docs/codex/archive/`로 이동하고, 현재 대표 문서를 `admin-gui-plan.md`와 `agent-guide.md`로 고정.
- 사용자용 `web-view`에서 캘린더 셀 내부 요일을 제거하고 색상 대비를 강화. `리포트 요약 지표` 카드를 제거하고, 일일 종목 요약은 5종목 안팎 높이의 내부 스크롤 영역으로 축소.
- 금액 표시는 축약 단위 대신 `000,000원` 형태의 콤마 숫자로 통일하고, 기간별 수급량 그래프는 0선을 기준으로 양수는 위, 음수는 아래로 표시하도록 조정.
- 순환매 overlay 기준을 업종 우선으로 고정. 테마는 보조 근거로만 두고, SVG 원 표시는 업종 좌표와 저장된 업종 리포트 분류 요약을 기준으로 생성.
- 선택 종목 상세를 `선택 종목 상태`와 `선택 종목 리포트`로 분리. KRX 현재가, 기간별 수급량, 일별 수급량, 일별 시장 거래량은 상태 카드에 두고, 리포트 카드에는 리포트 목록만 남김.
- 리포트 발행 시간이 `00:00`으로 들어오는 경우 시간 대신 날짜를 표시하고, 일별 시장 거래량 제목에서 중복 단위 문구를 제거.
- `krx-flow-backfill-manual` 명령을 추가해 수급 데이터를 날짜 범위별로 명시 수동 적재할 수 있게 함. 자동 scheduled ingest는 여전히 비활성 상태.
- DB 백업 후 2026년 5월 현재 확보 가능 영업일(`05-04`, `05-06`, `05-07`, `05-08`)의 KRX 수급 데이터를 수동 backfill. `stock_investor_flow_daily=260`, `market_investor_flow_daily=52`, `investor_net_buy_top_daily=2612`까지 확대.
- 사용자용 `web-view` 날짜 선택을 캘린더 단독 UI로 단순화하고, 상단 문구를 `리포트 뷰 / 날짜별 리포트와 시장 참고`로 축약. 우측 상단에는 ETF 섹션으로 이동하는 탭 자리만 추가.
- `일일 종목 요약` 스크롤 높이를 6건 기준으로 조정하고, `기간별 수급량` 표기를 `구분: 주`로 변경. 기간별 수급 막대는 일별 값이 아니라 `5월 1주` 같은 주차 단위 합산으로 표시.
- `테마 요약`에 “저장된 테마 구성 종목 중 선택 날짜에 리포트가 나온 종목을 테마별로 묶은 참고값이며, 테마 상승률/추천 순위가 아니다”라는 기준 설명을 추가.
- DB 백업 후 2026년 4월 영업일 수급 데이터를 수동 backfill. 4월 기준 `stock_investor_flow_daily=325`, `market_investor_flow_daily=286`, `investor_net_buy_top_daily=18893`행을 확보.
- `krx-flow-backfill-manual`의 skip-existing 기준을 날짜 단위에서 종목 코드 단위로 보정. 기본 화면이 6종목 기준으로 바뀐 뒤 빠져 있던 6번째 후보 종목별 수급 8건만 추가 호출해 `stock_investor_flow_daily=689`행까지 보강.
- 선택 종목 수급 안내 문구에 “종목별 수급은 화면 기본 노출 후보 중심으로 수집한다”는 범위 설명을 추가.
- `krx-flow-backfill-manual`에 `--stock-code` 반복 옵션과 `--candidate-limit 0` 명시 종목 전용 backfill 경로를 추가. 기본 6종목(`HD현대중공업`, `LG유플러스`, `LIG디펜스앤에어로스페이스`, `SK텔레콤`, `씨에스윈드`, `에이피알`)의 2026-04-01~2026-05-08 종목별 수급 누락분 150호출/1,950행을 보강해 `stock_investor_flow_daily=2,639`행까지 확대.
- 사용자용 `web-view` 선택 종목 상태의 `일별 수급량`과 `일별 시장 거래량` 조회 범위를 최근 5영업일에서 최근 20영업일로 확대. 5/8 기본 6종목은 4/9까지의 수급/거래량이 선택 종목 상태에 표시된다.
- 스크린샷에서 확인된 2026-05-04 선택 종목 상태 대상 상위 6종목(`삼성전자`, `삼성전기`, `BNK금융지주`, `LG에너지솔루션`, `키움증권`, `한온시스템`)의 2026-04-01~2026-05-08 종목별 수급 누락분 151호출/1,963행을 보강해 `stock_investor_flow_daily=4,602`행까지 확대.
- 사용자용 `web-view`의 선택 종목 영역을 좌우 배치로 변경. `선택 종목 상태`는 왼쪽 세로형 카드, `선택 종목 리포트 리스트`는 오른쪽 리스트 카드로 두고 각각 내부 스크롤 영역을 갖도록 조정.
- 선택 종목 영역의 폭을 재조정해 `선택 종목 상태`를 더 넓게, `선택 종목 리포트 리스트`를 더 좁게 표시. 기간별 수급량은 주차별 4개 카드가 한 줄에 들어가도록 막대 크기를 줄이고, 개인/외국인/기관별 `매수 | 매도` 수량을 함께 표시.
- 기간별 수급량 표기를 최근 4개 주차만 `과거 -> 최신` 순서로 표시하고, 투자자별 `매수/매도 우위`만 남기도록 정리. 일별 수급량 제목의 중복 `단위: 주` 문구와 화면상 `기관별` 탭은 제거.
- 선택 종목 영역 명칭을 `선택 종목` / `선택 종목 리포트`로 줄이고, 리포트 목록에 `의견없음 제외` 체크박스를 추가해 raw 저장값은 유지하면서 공유 화면에서는 의견 없는 리포트를 숨길 수 있게 조정.
- 내일 작업 메모로 `순환매 참고` 이미지 내 문구를 현재 업종/테마/종목 데이터와 매핑하는 검토 항목을 추가. 자동 판단 전 수동 alias table과 좌표맵 기준부터 확인하기로 정리.
- `data/operator_memos.md`의 상태 표기를 기존 표기 기준이 아니라 구현 증거, DB 조회, canonical docs, 에이전트 재평가 기준으로 재분류. 섹터 그래프, 국장 전체 테마 묶기, 수급 추적은 `[△]`로 낮추고, 순환매 이미지 문구 매핑은 미착수 `[ ]`로 정리.
- 사용자용 `web-view`에서 업종/테마 행 클릭 시 `public_category_id`와 `category_type`이 엇갈리면 다른 카테고리로 전환될 수 있던 경로를 차단. 클라이언트는 타입이 맞는 public id만 전송하고, 서버는 type mismatch 요청을 `400`으로 거부한다.
- DB 백업을 구간별로 생성한 뒤 Naver 리포트 `2026-01-02`~`2026-02-06`을 5영업일 단위로 backfill. 26영업일 전체가 채워졌고, 운영 DB의 리포트 범위는 `2026-01-02`~`2026-05-12`, `reports=3813`, `daily_stock_summaries=2453`이 됐다.
- KRX Data Marketplace 수급 데이터를 `2026-01-02`~`2026-03-31`까지 5영업일 단위로 추가 backfill. 시장 수급과 외국인 순매수 상위는 `2026-01-02`~`2026-05-08` 85영업일 기준으로 확장됐고, 종목별 수급은 후보 정책에 걸린 종목 중심으로 `stock_investor_flow_daily=6630`행까지 보강.
- `krx-flow-backfill-manual`에 `--report-mention-threshold` 옵션을 추가해 리포트 일일 요약의 언급 건수 기준으로 종목별 수급을 채울 수 있게 함. `mention_count >= 2` 기준으로 `2026-01-02`~`2026-05-08` 누락 208종목-일을 backfill해 해당 기준의 종목별 수급 coverage를 `426/426`으로 맞췄고, `stock_investor_flow_daily=9334`행까지 확대.
- `docs/codex/backtest-observation-plan.md`를 추가해 현재 확보된 2026년 리포트/KRX 가격·거래량/수급 데이터 기준으로 `mention_count >= 2` 후보의 리포트 후 `1/5/10/20영업일` 반응을 읽기 전용으로 산출하는 다음 단계를 정리. 목표가 괴리율/진행률, 수급 유무, 거래대금, 순매수 상위 포함 여부는 비교 근거로만 다루고 추천/점수/등급 표현은 금지로 고정.
- BO-1~BO-4 read-only 백테스트 관찰 산출 계층을 추가. `stock_monitor.analysis.backtest_observation`에서 `mention_count >= 2` 후보, 정확한 저장 거래일 기준 `1/5/10/20영업일` 반응, 목표가 괴리율/진행률, 같은 날짜 수급, 거래대금, 외국인 순매수 상위 포함 여부를 계산하며, DB 스키마 변경 없이 테스트로 고정.
- BO-5~BO-6으로 `GET /api/observation/backtest?date=YYYY-MM-DD` public-safe API와 사용자용 `web-view` 관찰 탭의 `리포트 후 흐름` 표를 추가. UI는 저장 데이터 기반 반응/목표가/수급/순매수 포함 여부를 보여주며 추천/점수/등급 판단은 계속 제외.
- BO-7 1차 QA로 `2026-05-11`, `2026-05-08`, `2026-05-07` 관찰 payload를 확인. 기준가가 목표가 범위 안이나 위에서 시작해 진행률이 음수/100% 초과로 보일 수 있는 케이스를 `progress_caution`으로 표시하고, 사용자 화면에는 `진행률 해석 주의` 문구를 추가.
- `docs/codex/scoring-draft-plan.md`를 추가해 점수화는 바로 구현하지 않고 feature availability audit, reaction distribution review, 내부 prototype, 별도 승인 순서로만 진행하도록 초안을 고정.
- SD-1 첫 구현으로 `observation-feature-audit` CLI를 추가. 저장된 `mention_count >= 2` 후보의 KRX 기준가, 목표가 관찰값, 수급, 외국인 순매수 상위, 거래대금, `D+1/5/10/20` 반응값 채움률만 read-only로 집계하며 점수/추천/등급은 생성하지 않는다.
- SD-2 첫 구현으로 `observation-reaction-distribution` CLI를 추가. 저장된 후보를 언급 건수 버킷, 목표가 관찰값 유무, 종목 수급 유무, `D+1/5/10/20` horizon별로 묶어 상승/하락/보합/결측/평균/min/max 반응률만 read-only로 집계한다.
- SD-3 첫 구현으로 `observation-feature-comparison` CLI를 추가. 언급 건수 버킷, 목표가 유무, 목표가 진행률 주의 여부, 종목 수급 유무, 외국인 순매수 상위 포함 여부, 거래대금 유무를 각각 독립 feature로 두고 반응 구간과 비교하되 최종 점수는 만들지 않는다.
- SD-4 첫 구현으로 `observation-weight-draft` CLI를 추가. feature별 평균 반응과 horizon 기준 평균의 차이를 내부용 `draft_weight`로 변환하되, 표본 부족은 `sample_too_small`으로 0 처리하고 종목별 점수/순위/추천/텔레그램 알림/사용자 화면 노출은 만들지 않는다.
- SD-5 첫 구현으로 `observation-hidden-prototype` CLI를 추가. SD-4 draft weight를 후보별 내부 `prototype_value`로 합산하되 출력 순위는 만들지 않고, 사용자 웹뷰/텔레그램/추천 문구에는 노출하지 않는다. 다음 보강은 학습 구간과 적용 구간 분리다.
- `observation-hidden-prototype`에 `--train-from-date`, `--train-to-date`를 추가해 학습 구간과 적용 구간을 분리. 최신 후보 확인 시 과거 구간으로 draft weight를 만들고 최근 날짜 후보에만 적용할 수 있게 했다.
- SD-4/SD-5 guardrail을 강화해 목표가 없음, 종목 수급 없음, 거래대금 없음은 `missing_is_unknown`으로 weight `0`, 목표가 진행률 주의 케이스는 `caution_separate_review`로 weight `0` 처리하도록 고정. 결측이 감점으로 굳어지는 경로를 차단했다.
- Naver 리포트 API/DOM 파서의 `source_id` canonicalization 회귀 테스트를 보강. 모바일 URL/query string, decorated `researchId`, `endUrl` fallback을 같은 canonical report id로 처리하는지 고정했다.
- 같은 `source_id`가 API와 DOM fallback에서 동시에 들어와도 SQLite 저장과 장중 알림 큐가 1건만 생성되는지 회귀 테스트를 추가했다.
- read-only 관찰 CLI parser smoke test를 추가해 `observation-feature-audit`와 train/apply 분리 옵션이 있는 `observation-hidden-prototype` 명령 인자 계약을 고정했다.
- `operator-status`에 `live_observation` 블록을 추가. Task Scheduler 메타데이터가 액세스 거부로 읽히지 않아도 같은 날의 notify/poll/KRX/Telegram command loop operation event를 요약해 실운영 근거를 확인할 수 있게 했다.
- `inspect-page --save-fixture PATH` 옵션과 Naver inspection fixture parser를 추가. live page snapshot을 JSON fixture로 저장하고, API row가 있으면 DOM fallback보다 우선 파싱하도록 고정해 parser drift 회귀 테스트를 쉽게 남길 수 있게 했다.
- 전일 요약 production fragment 실패 detail에 `message_hash`와 `ambiguous_send=true/false`를 추가. Telegram timeout-after-send처럼 실제 발송 성공 여부가 애매한 실패를 감사 로그에서 추적할 수 있게 했고, 중복 가능성 자체는 residual risk로 유지한다.
- SD-5 보강으로 `observation-hidden-holdout` CLI를 추가. 학습 구간에서 만든 내부 prototype 값을 별도 holdout 구간의 반응률 bucket으로 검증하되, 여전히 점수/순위/추천/텔레그램/사용자 화면 노출은 만들지 않는다.
- SD-5에 `--exclude-feature` pruning 옵션과 `observation-hidden-holdout-sweep` CLI를 추가. 여러 holdout window/horizon을 한 번에 비교할 수 있지만, 출력은 계속 내부 검증용이며 public 점수/추천/순위로 연결하지 않는다.
- `web-view-value-qa` CLI를 추가해 선택 날짜의 사용자용 daily/stock-detail DTO에서 `NaN/Infinity`, 표시용 `N/A` 노출, 주요 market reference 누락을 read-only로 점검할 수 있게 했다. `2026-05-11`, `2026-05-08`, `2026-05-07` 1차 점검은 issue/warning 0건.
- `operator-status`의 `live_observation`에 Telegram timeout trace 요약을 추가. 같은 날 `ambiguous_send=true` fragment 실패가 있으면 개수, 최신 fragment, run id, message hash를 확인할 수 있다.
- SD-5 guard를 추가 보강. 알 수 없는 `--exclude-feature` 값은 즉시 실패시키고, train/holdout 기간이 겹치면 `observation-hidden-holdout`과 sweep 모두 실행하지 않도록 차단했다.
- `web-view-value-qa`를 보강해 표시용 `NA`, `NULL`, `NONE`, `-`, 빈 문자열 누출도 잡고, 선택일이 최신 KRX 저장일보다 미래인 경우는 날짜 단위 `krx_snapshot_not_yet_available` warning으로 묶는다. 반대로 같은 날짜 KRX snapshot이 있는데 종목 `market_reference`가 없으면 issue로 실패한다.
- `operator-status` 텍스트 출력에도 Telegram timeout trace 한 줄을 추가해 JSON을 열지 않아도 ambiguous fragment failure 개수와 최신 run/fragment/hash를 확인할 수 있게 했다.
- elevated/local `operator-status --json --health-exit`로 Task Scheduler metadata를 재확인. `Notify`, `Poll`, `KrxDailyBackfill`, `TelegramCommands`, `Shutdown`은 healthy, `KrxFlowLoginReminder`는 의도된 disabled 상태로 확인됐고 health는 `ok`였다.
- KRX Open API `2026-05-13` snapshot dry-run을 네트워크 권한으로 확인했으나 stock/ETF/index/basic endpoint 모두 0건이었다. `web-view-value-qa`의 `2026-05-13` warning은 최신 저장일 `2026-05-12` 이후 데이터가 원천 미제공인 정상 경고로 분류했다.
- KRX Data Marketplace 수급을 `2026-05-11`~`2026-05-12` 범위로 수동 backfill. `mention_count >= 2` 리포트 종목과 leadership 후보 기준으로 34호출을 수행해 `stock_investor_flow_daily` 390행, `market_investor_flow_daily` 26행, `investor_net_buy_top_daily` 1,694행을 추가했고 warning은 0건이었다. 수급 최신일은 `2026-05-12`로 확장됐다.
- 전일자 Telegram 요약 고도화 TB-1~TB-4를 진행. `docs/codex/telegram-briefing-plan.md`를 추가하고, `send-test-notification`/`scheduled-notify`에 `--format summary|briefing` 옵션을 붙였다. 이 단계에서는 기본값을 기존 `summary`로 유지했고, `briefing`은 `국장 시작 전 리포트 브리핑`, `리포트 집중`, `주요 종목`, `확인 포인트` 구조로 dry-run 검증 가능하게 했다.
- TB-5 임시 운영 전환으로 `scheduled-notify` 기본 포맷을 `briefing`으로 변경. 며칠간 실제 Telegram 폰 화면 가독성을 관찰하기 위한 전환이며, `send-test-notification` 기본값은 기존 `summary`로 유지한다. 필요 시 `scheduled-notify --format summary`로 기존 포맷 발송도 가능하다.

## 주제별 요약

### 구조 / MVP
- `2026-04-26`: Python 기반 수집기, SQLite 저장, Telegram 알림, Windows Task Scheduler 운영 표면을 갖춘 실행 가능한 MVP 골격 완성.
- `2026-04-27`: 장중 알림, 전일 요약, 종목검색 응답 형식을 서로 비슷한 3줄 중심 구조로 정리.

### 스케줄 / 운영
- `2026-04-26`: `StockMonitor-Poll`, `StockMonitor-Notify`, `StockMonitor-TelegramCommands` 작업 스케줄러 등록.
- `2026-04-27`: Telegram 명령 확인 주기를 `08:00~19:00 / 1분 간격`으로 조정.
- `2026-04-27`: 알림/명령 작업을 숨김 창으로 실행하도록 바꿔 포커스 탈취 완화.
- `2026-04-27`: 기본 운영 시간을 `Notify 08:00`, `Poll 08:30~16:30`으로 재조정.
- `2026-04-28`: Telegram 명령 확인 시간을 `08:00~16:30`으로 줄이고, 평일 `16:40` 자동 종료 작업을 추가.
- `2026-05-01`: 휴장일에는 Telegram 명령 확인과 자동 종료도 내부에서 건너뛰도록 scheduled wrapper 추가.
- `2026-05-09`: `StockMonitor-KrxFlowLoginReminder` 작업과 wrapper를 추가해 `16:45`에 KRX 수급 검증용 원격 로그인 안내만 Telegram으로 보내도록 정리.
- `2026-05-09`: KRX 수급 검증 창과 충돌하지 않도록 `StockMonitor-Shutdown` 기본 시간을 `16:40`에서 `17:10`으로 조정.

### Telegram / 알림
- `2026-04-26`: 전일 요약 기본 발송량을 `7종목`으로 제한하고 `다음, 전부, 처음` 페이징 지원.
- `2026-04-26`: `/도움말`, `/명령어`, `/종목코드`, `/종목검색` 흐름 정리.
- `2026-04-27`: 수동 테스트 발송 채널과 실배치 채널을 분리해 테스트가 아침 실발송을 막지 않도록 수정.
- `2026-04-27`: 장중 신규가 없을 때도 `0건` 안내 메시지를 보내도록 추가.
- `2026-04-30`: Telegram `/메모` 명령으로 떠오른 아이디어를 로컬 메모 파일에 저장하도록 추가.
- `2026-04-30`: 전일자 요약은 기본 발송 시 전체 종목을 보내도록 변경.
- `2026-05-09`: Telegram `/체크 로그인` 명령을 추가해 KRX 원격 로그인 처리 완료를 접수하고, 실제 연결 판정은 16:50 dry-run으로 분리.
- `2026-05-09`: KRX 수동 로그인 검증은 Codex가 연 Chrome 확장 제어 탭 1개에서 로그인하도록 문구/운영 기준을 정리해 중복 탭 생성을 줄임.
- `2026-05-09`: KRX Data Marketplace 메인에서 `[12008]`, `[12009]`, `[12010]` 화면 이동과 주요 조회 조건을 검증하고, `[12009]` 종목 검색 위젯을 다음 blocker로 기록.

### 종목검색 / 조회 UX
- `2026-04-26`: `/종목검색`을 2-step 후보 선택형으로 보강.
- `2026-04-27`: 한글 6글자 종목명이 코드로 오인되던 문제 수정.
- `2026-04-27`: `/종목검색` 결과에 현재가와 섹터를 포함하도록 확장.

### 표시 형식 / 집계
- `2026-04-26`: 날짜 표기를 `26.04.24` 형식으로 단축.
- `2026-04-27`: 섹터를 종목 헤더에 반영.
- `2026-04-27`: 장중 알림은 동일 종목 2건 이상이면 종목별로 묶고 목표가는 범위로 요약.
- `2026-04-27`: 장중 단건은 제목까지 유지하고, 다건은 묶음형으로 분기.
- `2026-04-27`: 전일 요약에도 현재가를 반영.

### 안정화 / 예외 처리
- `2026-04-27`: 장중 페이징 상태가 끝난 뒤 자동 해제되도록 정리.
- `2026-04-27`: 한 페이지로 끝나는 장중 배치는 장중 컨텍스트를 남기지 않도록 수정.
- `2026-04-27`: 장중 컨텍스트가 전일 요약 페이징을 계속 가로채지 않도록 fallback 정리.
- `2026-04-27`: 한국어 종목명 검색 인코딩과 PowerShell UTF-8 실행 환경 보강.

## 날짜별 상세 이력

## 2026-05-10

### P2 테마/카테고리 히스토리 / ETF 웹뷰
- DB schema를 `5`로 올리고 `category_master`, `category_membership_snapshots`를 additive migration으로 추가. 기존 `stock_metadata`, `stock_theme_memberships`는 current-state fallback/cache로 유지.
- `category-catalog list/add/disable`, `refresh-theme --snapshot-date`, `refresh-industry --snapshot-date`, `refresh-themes --enabled --snapshot-date` 명령을 추가해 업종/테마 스냅샷 저장 경로를 마련.
- 사용자용 `web-view` 일일/카테고리 DTO를 snapshot-aware로 변경. 선택 날짜 이하의 가장 가까운 스냅샷을 쓰고, 없으면 `latest_mapping_fallback` 안내를 표시.
- `GET /api/etf-trend?date=YYYY-MM-DD&limit=5`와 화면의 `ETF 흐름` 섹션을 추가. 저장된 KRX ETF 스냅샷만 사용하며 실시간 호출, 점수, 추천은 포함하지 않음.
- Telegram read-only 보조 명령 `/상태`, `/오늘돌아?`, `/스케줄상태`, `/웹뷰주소`를 추가. 어떤 명령도 `admin-gui`를 열거나 scheduler/control write를 수행하지 않음.
- P2 실행 기준 문서 `docs/codex/p2-execution-plan.md`를 추가하고, KRX Flow Stage 6 scheduled ingest는 설계까지만 문서화. 실제 enable은 별도 승인 전까지 금지.
- P2 마감 하드닝으로 category snapshot 조회를 category key별 선택일 이하 최신 스냅샷 기준으로 수정. 일부 카테고리만 새 날짜로 갱신되어도 다른 카테고리가 숨지지 않도록 보강.
- `category_master.enabled=false`는 managed refresh 대상 제외와 user `web-view` 표시 제외 의미로 고정.
- `db-verify`에 category snapshot/catalog 품질 점검을 추가해 orphan snapshot은 실패로, empty/disabled snapshot 상태는 운영 확인 항목으로 표시.
- `krx-flow-login-reminder`에 한국 영업일/no-run/operation-profile/late-run guard를 추가하고, 스케줄러 등록 시 놓친 실행을 따라 실행하지 않도록 `StartWhenAvailable`을 끔.
- Telegram `/체크 로그인`도 `/메모`처럼 update id 기준 replay-safe side effect로 바꿔, Telegram 응답 실패 후 재처리되어도 `login-ack` 이벤트가 중복 기록되지 않도록 수정.
- 사용자용 `web-view`의 KRX/ETF/수급 하단 정보를 `시장 참고` 접힘 영역으로 묶어 공유 화면 과밀도를 낮춤.
- 사용자용 `web-view`가 날짜 변경 때 첫 종목/첫 카테고리 상세를 자동 호출하지 않고, 사용자가 행을 선택할 때만 상세/흐름 API를 호출하도록 조정.
- 네이버 리서치 DOM fallback 파서가 날짜/증권사 cell 위치 변경에 더 잘 버티도록 core field 추출을 보강하고, 후보 row fixture 테스트를 추가.
- `category-snapshot-from-cache --snapshot-date YYYY-MM-DD --type all` 명령을 추가해 네트워크 호출 없이 기존 `stock_metadata`, `stock_theme_memberships` 캐시를 dated category snapshot으로 승격할 수 있게 함.
- 운영 DB에 `2026-05-08` 기준 category snapshot을 적용해 `category_master` 11건, `category_membership_snapshots` 130건을 확보했고, `db-verify` category quality issues `0`을 확인.
- `category-snapshot-status --limit N [--json]` 명령을 추가해 요약 날짜별 dated snapshot/fallback 상태를 읽기 전용으로 확인할 수 있게 함.
- 운영 DB 기준 `2026-05-08`은 dated snapshot, 그 이전 요약 날짜는 `latest_mapping_fallback` 상태임을 확인. 현재 캐시를 과거 날짜에 일괄 승격하면 역사적 카테고리 왜곡 가능성이 있어 자동 적용하지 않음.
- `db-verify`에 category snapshot coverage 요약을 추가해 summary date 수, sector/theme dated 적용 수, fallback date 수를 같이 표시하도록 보강.
- 사용자용 `web-view` archive API/날짜 버튼에 category mapping 상태를 표시해 날짜 선택 전에도 `카테고리 스냅샷`/`카테고리 fallback`을 구분할 수 있도록 보강.
- `category-snapshot-status --mode all|dated|fallback`을 추가해 fallback 날짜만 바로 확인할 수 있도록 보강.
- 사용자용 `web-view` 날짜 아카이브에 `카테고리 스냅샷`, `카테고리 fallback` 필터를 추가하고, archive API에 `category_mapping_summary`를 추가.
- `category-snapshot-status` 텍스트/JSON에 전체 summary date, dated snapshot date, fallback date 카운트를 추가하고, 사용자용 웹뷰 날짜 영역에도 같은 요약 문구를 표시.
- `category-snapshot-status`에 `next_action`을 추가해 fallback 날짜가 있을 때 source-date snapshot 확보가 다음 조치이며 current cache 과거 일괄 승격은 명시 승인 전 금지임을 출력.
- 사용자용 `web-view` archive summary에 fallback 안내 문구를 추가해 공유 화면에서도 fallback의 의미를 설명.
- `category-snapshot-plan --limit N [--json]`을 추가해 fallback 후보 날짜, enabled catalog 수, 안전한 source-date snapshot 명령 템플릿을 DB 쓰기 없이 출력.
- `refresh-industries --enabled --snapshot-date YYYY-MM-DD`를 추가해 enabled sector catalog 기준으로 Naver industry snapshot을 일괄 갱신할 수 있게 함.
- `category-snapshot-plan`의 업종 템플릿을 단건 `refresh-industry`에서 batch `refresh-industries --enabled`로 교체.
- `refresh-industries --enabled`와 `refresh-themes --enabled`에 `--dry-run`을 추가해 실제 네트워크 호출/DB 쓰기 전에 대상 catalog와 호출 계획을 확인할 수 있게 함.
- `category-snapshot-plan` 템플릿에 dry-run 선행 명령을 추가.
- `refresh-industries --enabled`와 `refresh-themes --enabled`에 `--delay-seconds`를 추가하고, `category-snapshot-plan` 템플릿 기본 예시를 `--delay-seconds 3` 기준으로 갱신해 연속 호출 리스크를 줄임.
- `refresh-industries --enabled`와 `refresh-themes --enabled` 실제 batch 실행에 `--confirm`을 필수로 추가. `--dry-run` 없이 바로 실행하거나 `--confirm`을 빼면 네트워크 호출/DB 쓰기 전에 거부한다.
- 검증: `python -m pytest -q` 통과, `307 passed`.
- 사용자용 `web-view` 슬림화 1차 반영. 친구 화면에서 `공유 화면 기준`, `장중 흐름`, 관찰 후보, 카테고리 snapshot/fallback 필터를 숨기고, 날짜/리포트/업종·테마/시장 참고 중심으로 재정리.
- `web-view` 주요 표 영역에 bounded scroll panel을 추가해 일일 종목 요약, 업종/테마, 카테고리 상세/흐름, 시장 참고 표가 전체 페이지 길이를 과도하게 늘리지 않도록 보강.
- `/api/intraday`와 `public_contract` DTO는 유지해 GET-only/public-safe 회귀 검증은 계속 가능하게 두고, visible UI에서만 운영자성 문구와 장중 배치 로그를 제거.

### P1 사용자용 웹뷰 / 수급 트렌드
- 사용자용 `web-view` 날짜 선택 영역에 검색/필터 UI를 추가해 날짜 문자열이나 `N건` 기준으로 빠르게 아카이브를 좁혀볼 수 있도록 보강.
- `GET /api/flow-trend?date=YYYY-MM-DD`를 추가해 저장된 KRX Data Marketplace 수급 샘플만으로 최근 수급 흐름을 읽기 전용으로 반환하도록 구현. 실시간 KRX 호출, 점수, 추천은 포함하지 않음.
- 사용자용 `web-view`에 `수급 흐름` 섹션을 추가해 시장 수급과 외국인 순매수 상위 종목을 최근 저장 샘플 기준으로 표시.
- 일일 DTO에 `category_contract`를 추가해 업종/테마 매핑 기준을 화면과 API에서 명시.
- KRX Flow Stage 5를 완료 상태로 갱신. Stage 6 scheduled ingest 설계는 별도 승인 전까지 계속 비활성으로 유지.

### P0 운영 / 웹뷰 마감
- Windows Task Scheduler의 `267011` 값은 아직 실행된 적 없는 예약 작업 상태로 처리하도록 보강. `StockMonitor-KrxFlowLoginReminder`처럼 다음 실행 시간이 미래인 신규 작업이 health 실패로 과잉 분류되지 않도록 수정.
- `operator-status --health-exit` 기준 실제 스케줄러 상태가 `ok`로 판정되는지 권한 상승 조회로 확인.
- 사용자용 `web-view` 일일 DTO에 public contract 블록을 추가해 `읽기 전용`, `저장 데이터 기준`, `점수/추천 없음`, `관리자 제어 없음`을 API와 화면에서 명시.
- 사용자용 `web-view` 수급 DTO에 `stored_krx_data_market_sample`, `live_fetch=false`, `scoring=false` 메타데이터를 추가해 저장 샘플 read-only 경계를 명확히 표시.
- 사용자용 `web-view` 숫자 표시에서 잘못된 숫자 입력이나 `N/A`류 값이 `NaN`으로 보이지 않고 `-`로 표시되도록 보강.
- 로컬 HTTP 확인에서 `web-view` HTML이 public contract와 숫자 표시 guard를 포함하고, `/api/status` 같은 관리자 경로 문자열을 포함하지 않음을 확인.

### 검증
- `python -m pytest tests\test_operator_status.py -q` 통과: `15 passed`.
- `python -m pytest tests\test_web_view.py tests\test_operator_status.py -q` 통과: `25 passed`.
- 당시 `python -m stock_monitor db-verify` 통과: schema `4/4`, foreign key violations `0`, investor-flow quality issues `0`. 이후 P2 schema v5 반영 뒤 검증 기준은 `5/5`로 갱신됨.
- `python -m stock_monitor krx-flow-login-check --date 2026-05-08 --market STK` 통과: `[12008]` 13행 응답 확인, DB 쓰기 없음.

## 2026-05-09

### KRX 수급 소스 계획
- Chrome 확장 연결을 통해 로그인된 KRX Data Marketplace 화면을 확인하고 `기본 통계 > 주식 > 거래실적` 아래의 `[12008] 투자자별 거래실적`, `[12009] 투자자별 거래실적(개별종목)`, `[12010] 투자자별 순매수상위종목` 화면을 검증.
- `[12009] 투자자별 거래실적(개별종목)`에서 삼성전자 기준 투자자구분별 거래량/거래대금의 매도·매수·순매수 컬럼을 확인하고, 리포트 종목별 수급 P0 검증 후보로 승격.
- `docs/codex/krx-investor-flow-source-plan.md`를 추가해 KRX Data Marketplace 수급 화면의 우선순위, 수집 시간대, 후보 테이블, 구현 순서, guardrail을 정리.
- KRX Open API daily snapshot은 가격/거래량/거래대금 기준 데이터로 유지하고, 투자자별 수급은 `source='krx_data_market'` 기반 별도 계층으로 분리하기로 결정.
- KRX Data Marketplace 수급 후보의 요청 구조를 문서화. `[12008]`은 `MDCSTAT02201`, `[12009]` 기간합계는 `MDCSTAT02301`, `[12009]` 일별추이는 `MDCSTAT02302`, `[12010]`은 `MDCSTAT02401` 후보로 정리.
- `[12009]`는 6자리 종목코드가 아니라 `isuCd` 매핑이 필요할 가능성이 있어, 실제 수집 전 `stock_code -> isuCd` 매핑 확인과 dry-run 출력 검증을 선행 조건으로 고정.
- `krx-flow-dry-run` CLI를 추가해 KRX Data Marketplace `[12009]` 후보 요청을 DB 저장 없이 검증할 수 있도록 구성. 저장된 `krx_stock_metadata`에서 `stock_code -> standard_code/isuCd`를 찾거나 `--isu-cd`를 직접 넣는 방식으로만 호출한다.
- KRX Data Marketplace가 `LOGOUT` 응답을 반환하는 것을 확인하고, Open API `AUTH_KEY`와 분리된 선택적 로컬 로그인 설정(`STOCK_MONITOR_KRX_DATA_MARKET_ID/PASSWORD`)을 추가. 이 값은 dry-run/source validation 전용이며 문서/화면/텔레그램에 노출하지 않도록 고정.
- `krx-flow-dry-run`을 `--view stock|market|top` 구조로 확장해 `[12009]` 종목별 수급, `[12008]` 시장 전체 수급, `[12010]` 투자자별 순매수상위 dry-run을 모두 같은 명령에서 검증할 수 있도록 정리.
- KRX Data Marketplace 세션은 약 30분 지속 전제로 보고, 향후 수급 배치 5분 전 Telegram 로그인 요청 알림을 보내고 사용자가 Chrome에서 로그인해둔 세션을 우선 활용하는 운영 정책을 문서화. `LOGOUT` 응답 시 저장 없이 skip한다.
- `krx-flow-login-reminder` CLI를 추가해 KRX 수급 dry-run/수집 예정 5분 전 Telegram으로 수동 Chrome 로그인 요청을 보낼 수 있도록 구성. 실제 수급 저장/수집과는 분리된 reminder-only 명령이다.
- `[12009]` 화면 검증 기준을 내부 form 값보다 보이는 화면 상태 우선으로 보강. `개별종목을 검색해주세요`가 보이면 먼저 `닫기`를 누른 뒤 종목명 입력, `Enter`, `NNNNNN/종목명` 표시 확인, `조회` 순서로 진행하도록 정리.
- `krx-flow-dry-run --request-only` 옵션을 추가해 KRX Data Marketplace 로그인이나 네트워크 호출 없이 `stock_code -> isuCd -> request params` 변환을 확인할 수 있도록 보강. 운영 DB 기준 `005930`은 `KR7005930003`으로 정상 매핑됨을 확인.
- 과거 수급 데이터 범위를 결정. KRX Open API 가격/거래량 snapshot은 3개월 분석/6개월 보관으로 유지하고, KRX Data Marketplace `[12009]` 투자자별 수급은 전체 시장이나 모든 리포트 종목 crawling이 아니라 주도주/관찰 후보 종목-일자 키만 대상으로 시작하도록 고정. `[12008]` 시장 배경과 `[12010]` 순매수 상위는 live dry-run 검증 후 3개월 범위까지 확장 가능하다고 정리.
- `krx-flow-candidates --date YYYY-MM-DD` 명령을 추가해 `[12009]` 호출 전 주도주/관찰 후보를 로컬 데이터만으로 미리 추릴 수 있도록 구성. 필터링된 일일 요약, 섹터 집중, KRX 거래대금 상위, 등락률 신호를 이용하며 네트워크 호출/DB 쓰기는 하지 않는다.
- `[12009] 투자자별 거래실적(개별종목)` live 화면에서 `329180/HD현대중공업` 기준 투자자별 거래량/거래대금 매도·매수·순매수 테이블 렌더링을 확인하고, 화면 검증 결과와 raw 응답 미확인 위험을 분리해 문서화.
- KRX Data Marketplace 수급 응답 정규화 초안을 추가. `[12009]` 종목별 수급, `[12008]` 시장 수급, `[12010]` 순매수상위 후보 응답을 공통 모델로 파싱하되 `N/A`, 빈 문자열, `-` 값은 숫자 범위/랭킹을 왜곡하지 않도록 `None`으로 유지한다.
- SQLite schema v4로 `stock_investor_flow_daily`, `market_investor_flow_daily`, `investor_net_buy_top_daily` 테이블과 repository upsert/list 테스트를 추가. 테이블은 additive migration이며, 운영 DB scheduled ingest 적용은 raw endpoint 샘플과 단위 매핑 확인 전까지 보류한다.
- `db-verify`에 수급 테이블 품질 검사를 추가해 잘못된 종목코드, 누락 단위, 숫자 수급값 없는 행, 잘못된 순위가 들어오면 운영 검증에서 실패하도록 보강.
- `docs/codex/krx-investor-flow-schema.md`를 추가해 수급 테이블 계약, 단위 보존 정책, `db-verify` 품질 게이트, scheduled ingest 승격 조건을 문서화.
- 운영 DB가 schema `4/4` 상태임을 `db-verify`로 확인했고, 신규 수급 테이블 3종은 모두 `0건` 상태로 유지. 사후 백업 `data/backups/stock_monitor_{timestamp}_{tag}.db`를 생성하고 integrity `ok` 확인.
- `krx-flow-dry-run --sample-file <json>`을 추가해 Chrome/DevTools 등으로 저장한 KRX Data Marketplace raw JSON을 로그인·네트워크·DB 쓰기 없이 정규화 검증할 수 있도록 보강.
- `krx-flow-dry-run`에 `--volume-unit`, `--amount-unit`을 추가해 KRX 화면 캡처 당시 단위를 정규화 결과에 그대로 보존하도록 보강. 값 스케일링은 자동 추정하지 않는다.
- `krx-flow-dry-run --sample-manifest <json>`을 추가해 raw sample 파일, 화면 번호, 기준일, 종목/시장/투자자 조건, 단위를 sidecar manifest로 묶어 반복 검증할 수 있도록 정리.
- `krx-flow-dry-run --normalized-output <json>`을 추가해 sample/manifest 정규화 결과를 로컬 JSON 산출물로 저장할 수 있도록 보강. 저장 산출물은 검증용이며 SQLite에는 쓰지 않는다.
- `krx-flow-dry-run --strict-sample`을 추가해 raw row 0건, 정규화 0건, 핵심 수급 숫자 부재 같은 품질 경고가 있으면 exit code `2`로 실패하도록 보강.
- KRX sample manifest에 `expected_min_rows`, `expected_min_normalized_rows`, `expected_investors`를 추가해 필수 투자자 row 누락을 strict 검증에서 잡을 수 있도록 보강.
- `docs/codex/krx-flow-sample-capture-runbook.md`와 `data/krx_samples/templates/*.json`을 추가해 `[12008]`, `[12009]`, `[12010]` raw sample 캡처/manifest/strict 검증 절차를 고정.
- `krx-flow-dry-run --manifest-output <json>`을 추가해 CLI 조건에서 raw sample manifest 초안을 자동 생성할 수 있도록 보강.
- `krx-flow-sample-scaffold` 명령을 추가해 기준일과 후보 종목코드만으로 `[12009]`, `[12008]`, `[12010]` manifest 세트를 한 번에 생성하도록 보강.
- `krx-flow-sample-scaffold --from-candidates`를 추가해 로컬 leadership 후보 preview 결과를 바로 `[12009]` 수급 샘플 manifest 세트로 연결할 수 있도록 보강.
- `krx-flow-capture-checklist` 명령을 추가해 manifest 기준으로 캡처 화면, 조건, raw 파일명, 검증 명령을 작업표 형태로 출력하도록 구성.
- `krx-flow-sample-status` 명령을 추가해 `[12008]`, `[12009]`, `[12010]` manifest와 raw sample 파일 커버리지가 batch 검증 가능한 상태인지 빠르게 확인하고 다음 캡처 파일명을 보여주도록 구성.
- `krx-flow-validate-samples` 명령을 추가해 `data\krx_samples`의 여러 manifest를 한 번에 strict 검증하고, `--normalized-dir` 지정 시 manifest별 normalized artifact를 생성하도록 구성.
- `krx-flow-import-preview` 명령을 추가해 local manifest/raw sample 기준으로 어느 수급 테이블에 몇 행이 들어갈지 DB 쓰기 없이 계산할 수 있도록 구성.
- `krx-flow-import-samples --confirm --i-validated` 명령을 추가해 경고 없는 local sample만 수동으로 수급 테이블에 upsert할 수 있도록 구성. scheduled ingest는 계속 보류.
- 사용자용 `web-view`에 수동 import된 KRX 수급 데이터를 읽기 전용 참고값으로 노출. 일일 화면은 시장 수급과 순매수상위 참고를, 종목 상세는 종목별 투자자 수급 row를 보여주며 점수/추천/스케줄러 쓰기/인증정보 노출은 추가하지 않음.
- 사용자용 `web-view` 수급 DTO에 표시 라벨을 추가해 내부 market/investor 코드(`STK`, `foreign`)가 화면 기준 라벨(`KOSPI`, `외국인`)로 정규화되도록 보강하고, 외국인/기관/개인 우선 정렬을 적용.
- `2026-05-08` 기준 leadership 후보에서 KRX 수급 sample manifest 7개를 생성. `[12009]` 종목 5개, `[12008]` 시장 1개, `[12010]` 순매수상위 1개이며, raw sample 파일은 아직 비어 있어 batch validation은 대기 상태.
- 로그인된 KRX Data Marketplace visible grid 기준으로 `2026-05-08` 수급 샘플 7개를 캡처. `[12009]` 종목 5개, `[12008]` 시장 1개, `[12010]` 외국인 순매수상위 1개 모두 strict 검증 `quality=ok` 통과.
- 수급 샘플 import 전 `data/backups/stock_monitor_{timestamp}_{tag}.db` 백업을 생성하고 integrity `ok` 확인. 이후 수동 import로 `stock_investor_flow_daily 65건`, `market_investor_flow_daily 13건`, `investor_net_buy_top_daily 72건`을 저장.
- 수동 import 후 `db-verify`에서 schema `4/4`, foreign key violations `0`, investor-flow quality issues `0`을 확인하고, 사용자용 `web-view` API에서 `2026-05-08` 일일 수급 및 `329180` 종목 수급 노출을 확인.
- `krx-flow-compare-samples` 명령을 추가해 visible-grid 샘플과 향후 raw-network 샘플을 정규화 후 비교할 수 있도록 구성. 이 명령은 로그인/네트워크/DB 쓰기 없이 parity를 확인하며, scheduled ingest 승격 전 필수 게이트로 문서화.
- `krx-flow-raw-sample-scaffold` 명령을 추가해 visible-grid manifest 기준으로 raw-network manifest placeholder를 만들 수 있도록 구성. `data\krx_samples_raw`에 7개 manifest를 생성했으며 raw JSON 본문은 아직 비어 있어 status가 `sample=N`으로 표시되는 상태가 정상이다.
- Stage 1 raw-network capture 자동화를 점검. Chrome 확장 탭에서는 KRX 로그인 세션이 보이지만 현재 브라우저 자동화 표면은 raw network response body를 노출하지 않고, 비로그인 직접 POST는 KRX가 `LOGOUT`으로 거부함을 확인. `krx-flow-execution-stages.md`에 Stage 1 필수 파일과 blocker를 명시.
- 로컬 `.env`에 등록된 KRX Data Marketplace 로그인값으로 `2026-05-08` raw-network JSON 7개를 `data\krx_samples_raw`에 저장. raw sample status가 `ready_for_batch_validation: Y`가 되었고, strict raw validation 7/7 통과.
- `krx-flow-compare-samples --allow-right-extra-top-rows` 옵션을 추가. `[12010]` raw 응답은 846행, visible-grid는 72행으로 raw가 더 많지만 visible rows가 raw prefix와 일치하는 compatible superset으로 판정되도록 분리. `2026-05-08` Stage 1-3 통과.
- KRX 로그인 UI 자동화 재검토. wrapper iframe 경로보다 direct `login.jsp?site=mdc` 탭이 안정적으로 DOM 필드를 노출하며, 실제 세션 교체 로그인도 확인. 다만 브라우저 UI 로그인은 fallback/debug 경로로 두고, 표준 raw sample capture는 `.env` 기반 raw fetch로 유지하기로 정리.
- `2026-05-07` 기준 KRX 수급 raw-network 샘플 7개를 `data\krx_samples_raw_20260507`에 저장하고 strict raw validation 7/7 통과.
- 같은 날짜 visible-grid baseline 7개를 `data\krx_samples_visible_20260507`에 저장하고 strict validation 7/7 통과. `[12008]`은 ETF/ETN/ELW 추가항목을 해제한 KOSPI 기준으로 맞췄고, `[12010]`은 우선주 코드처럼 6자리 숫자가 아닌 코드도 누락하지 않도록 캡처를 보정.
- `krx-flow-compare-samples --left-manifest-dir data\krx_samples_visible_20260507 --right-manifest-dir data\krx_samples_raw_20260507 --allow-right-extra-top-rows` 통과. `2026-05-08`, `2026-05-07` 두 영업일 모두 raw/visible-grid parity가 확인되어 Stage 4 완료. scheduled ingest는 Stage 6 설계와 별도 승인 전까지 계속 비활성.
- `krx-flow-login-check --date YYYY-MM-DD --market STK` 명령을 추가해 `.env` 기반 KRX Data Marketplace raw 로그인과 대표 `[12008]` JSON endpoint를 DB 쓰기 없이 점검할 수 있도록 구성. 실제 `2026-05-07/STK` 점검에서 로그인 및 13행 응답 확인.
- KRX Data Marketplace `LOGOUT` payload, HTTP `LOGOUT`, 로그인 실패를 `KrxDataMarketAuthError`로 구분하도록 보강. CLI는 `missing_login_configuration`, `auth_rejected`, `fetch_failed`, `empty_response`를 나눠 표시하고 exit code `2`로 실패 처리.

### 운영 설정 / 감사
- `db-verify` CLI를 추가해 SQLite `integrity_check`, schema/migration 상태, table row count, 중복 `source_id`, orphan daily summary fragment를 한 번에 확인할 수 있도록 구성.
- `db-backup` CLI를 추가해 SQLite backup API 기반 일관성 백업을 `data/backups/stock_monitor_YYYYMMDD_HHMM_TAG.db` 형태로 생성하고, 기본적으로 백업 파일 integrity check를 수행.
- `db-backup-prune` CLI를 추가해 오래된 백업 삭제 대상을 `--dry-run`으로 확인하고, 실제 삭제는 `--confirm`이 있어야 진행되도록 보호.
- `db-cleanup` CLI를 추가해 오래된 KRX snapshot 정리 대상을 `--dry-run`으로 확인하고, 실제 삭제는 영향 row가 있을 때 `--confirm`이 있어야 진행되도록 보호.
- `db-cleanup` 삭제 대상은 `stock_market_daily`, `etf_daily_snapshots`, `market_index_daily`로 제한하고, `reports`, `daily_stock_summaries`, `delivery_log`, 전일 요약 delivery run/fragment는 보호 대상으로 명시.
- 첫 수동 백업 `data/backups/stock_monitor_{timestamp}_{tag}.db`를 생성하고 integrity check `ok` 확인.
- 운영 DB 기준 `python -m stock_monitor db-cleanup --dry-run --retention-days 183` 실행 결과 삭제 대상 `0건` 확인.
- `krx-backfill-missing` CLI를 추가해 3개월 흐름 확인용 KRX 누락 영업일/endpoint를 최신 영업일부터 찾아 `krx-fetch-snapshot` 경로로 순차 수집할 수 있도록 구성.
- 기본 `daily` backfill 대상은 ETF, KOSPI/KOSDAQ 주식 일별, KRX/KOSPI/KOSDAQ 지수 일별로 제한하고, 종목기본정보 endpoint는 명시 선택 시에만 포함되도록 분리.
- KRX backfill 실제 호출은 `--confirm`을 요구하고, 기본 처리 범위를 최신 `5`영업일로 제한하며, endpoint 사이에 기본 `3초` 대기를 두고, 5영업일 초과는 `--allow-large-batch` 없이는 거부하도록 보호.
- 운영 DB에 실제 1영업일 backfill을 수행해 `2026-05-08` KRX daily snapshot 6개 endpoint 저장과 DB integrity `ok`를 확인.
- 운영 DB에 두 번째 소량 backfill을 수행해 `2026-05-07`의 누락 KRX daily snapshot 5개 endpoint 저장과 DB integrity `ok`를 확인. 다음 누락 후보는 `2026-05-06`.
- 운영 DB에 세 번째 소량 backfill을 수행해 `2026-05-06` KRX daily snapshot 6개 endpoint 저장과 DB integrity `ok`를 확인. 사용자용 web-view daily snapshot에서 `2026-05-06`, `2026-05-07`, `2026-05-08`의 KRX context가 모두 사용 가능함을 확인.
- 운영 DB에 네 번째 소량 backfill을 수행해 `2026-05-04` KRX daily snapshot 6개 endpoint 저장과 DB integrity `ok`를 확인. 사용자용 web-view daily snapshot에서 `2026-05-04`까지 선택 날짜 KRX context가 사용 가능함을 확인.
- 운영 DB에 다섯 번째 소량 backfill을 수행해 `2026-04-30` KRX daily snapshot 6개 endpoint 저장과 DB integrity `ok`를 확인. 다음 누락 후보는 `2026-04-29`.
- 운영 DB에 여섯 번째/일곱 번째 소량 backfill을 수행해 `2026-04-29`, `2026-04-28` KRX daily snapshot 6개 endpoint씩 저장하고 DB integrity `ok`를 확인. 다음 누락 후보는 `2026-04-27`.
- `krx-backfill-missing` 실제 실행 조건을 `--confirm --i-backed-up`으로 강화해, `db-verify`와 `db-backup` 선행 확인 없이는 운영 DB backfill을 거부하도록 변경.
- `db-verify`에 `foreign_key_check`, 장중 batch/report orphan, KRX daily endpoint partial snapshot 감지를 추가해 운영 검증 범위를 확장.
- 운영 DB에 5영업일 단위 backfill을 반복 수행해 `2026-03-03`부터 `2026-05-08`까지 KRX daily snapshot 구간을 확보. 최종 다음 후보는 `2026-02-27`.
- `db-restore-smoke` CLI를 추가해 백업 파일을 임시 DB로 복사한 뒤 integrity/schema/table 검증을 수행하고, 운영 DB를 건드리지 않는 복원 smoke workflow를 구성.
- `db-vacuum` CLI를 추가해 월간 또는 대량 cleanup 이후 SQLite `VACUUM`을 `--dry-run`으로 먼저 확인하고, 실제 실행은 `--confirm`이 있어야 진행되도록 보호.
- `operation_profile` 정책을 scheduled wrapper에 연결. `desktop-validation`은 기존 동작, `mini-pc`는 scheduled shutdown skip, `manual-only`는 scheduled poll/notify/telegram/shutdown wrapper skip으로 고정.
- `admin-gui`에서 `operation_profile` 편집을 허용하고 감사 로그/운영 이벤트를 남기도록 변경.
- `scheduler-control restart --task telegram-commands --confirm`과 admin-gui `TelegramCommands` 재시작 버튼을 recovery control로 추가. `Shutdown` 재시작은 계속 제공하지 않음.
- 운영 DB 기준 `python -m stock_monitor krx-backfill-missing daily --lookback-days 90 --max-dates 5 --dry-run` 실행으로 최초 누락 계획을 확인.
- DB migration v3로 `app_settings`와 `admin_audit_log`를 추가해 raw `.env` 편집 없이 안전한 운영 설정을 저장하고 변경 이력을 남길 수 있도록 준비.
- `operator-settings list/set/history` CLI를 추가해 전일 요약 최소 건수, 목표가 필수 여부, Telegram 기본 표시 수, 운영 프로필을 조회/변경/감사할 수 있도록 구성.
- 설정 변경은 `--confirm`과 `--reason`을 요구하고, 값 범위 검증 실패는 감사 로그에 `validation_failed`로 남기며, 동일 값 재설정은 불필요한 감사 로그를 만들지 않도록 처리.
- DB 설정이 없으면 `.env` 또는 코드 기본값으로 fallback하고, DB에 저장된 값은 전일 요약 필터, Telegram paging 기본 표시 수, `operator-status` 출력에 반영되도록 연결.
- `operation_profile`은 설정/상태 노출까지 반영했고, 실제 스케줄러·종료 정책 전환은 다음 admin-gui control 작업으로 분리.
- `admin-gui`에 `안전 설정`과 `설정 변경 이력` 섹션을 추가해 전일 요약 최소 건수, 목표가 필수 여부, 기본 표시 수를 화면에서 확인/변경할 수 있도록 연결.
- `admin-gui` 설정 변경은 `변경` 확인문구와 변경 사유를 요구하고, 성공/검증 실패 모두 감사 로그 또는 운영 이벤트로 추적되도록 보강.
- `operation_profile`은 관리자 화면에서 표시하되, 종료/스케줄러 정책이 연결되기 전까지는 화면 편집을 막도록 고정.
- 과거 리포트 backfill보다 KRX 종목/ETF/지수 1개월 snapshot backfill을 우선하는 방향으로 메모와 로드맵을 갱신. 이 데이터는 추세/흐름 참고값으로만 쓰고 scoring/추천에는 사용하지 않음.
- 친구용 `web-view`가 관리자 전용 safe settings, `/api/settings`, admin audit log, 운영 프로필, 스케줄러/worker 상태를 노출하지 않도록 public-safe 회귀 테스트와 surface contract를 보강.

### Web View
- 사용자/친구용 화면 용어를 `사용자용 웹뷰`, `날짜 선택`, `관찰 후보`, `선택 날짜 KRX 시장 참고`처럼 사용자 기준으로 정리.
- 사용자용 웹뷰에 `선택 상태` 바, 선택 행 하이라이트, 종목/카테고리 상세 카드 포커스 이동을 추가해 클릭 후 어떤 영역이 갱신됐는지 명확하게 표시.
- `GET /api/daily/YYYY-MM-DD` 응답에 선택 날짜 기준 `krx_context`를 추가해 KOSPI/KOSDAQ 거래대금 상위, ETF 거래대금 상위, 주요 지수를 같은 날짜 기준으로 제공.
- 선택 날짜에 KRX 스냅샷이 없을 경우 최신 스냅샷으로 대체하지 않고 `available=false`와 안내 문구를 반환하도록 고정.
- 종목별 KRX 참고값에 거래량을 추가하고, ETF 참고값은 저장된 범위 내에서 NAV, 거래량, 거래대금, 기초지수명만 노출.
- 사용자 화면의 핵심 KRX 참고는 `/api/market` 최신값이 아니라 `/api/daily/YYYY-MM-DD`의 선택 날짜 `krx_context`를 우선 사용하도록 변경.
- 사용자용 웹뷰에 `KRX 최근 흐름` 섹션과 `krx_recent_flow` DTO를 추가해 선택 날짜 이전 최근 저장 스냅샷의 KOSPI/KOSDAQ/ETF 거래대금 1위를 점수 없이 보여주도록 보강.
- 사용자용 웹뷰의 `KRX 최근 흐름` 문구를 실제 동작에 맞게 “선택 날짜 포함” 기준으로 정리.
- 사용자용 웹뷰에서 내부 placeholder `N/A` 업종을 화면 표시용 `업종 미확인`으로 바꿔, 친구/사용자 화면에 내부값이 그대로 보이지 않도록 보강.
- 모바일에서 일일 종목 요약, 장중 흐름, 업종/테마, 카테고리, KRX 참고 표가 카드형 행으로 접히도록 보강.
- 종목 상세 조회에서는 목표가/의견이 없는 원본 리포트도 숨기지 않고 `목표가 -`, `의견 없음`으로 노출되도록 테스트를 고정.

### Telegram
- 종목검색 결과의 최근 리포트 목록에 리포트별 목표가와 의견을 함께 표시하도록 보강.

### 문서
- 진행표의 기존 영문 표현을 `사용자용 웹뷰`로 정리하고 완성도 목표를 80%로 갱신.
- `surface-contract`에 카테고리 상세/흐름 API와 선택 날짜 KRX 컨텍스트 원칙을 반영.
- `docs/codex/data-quality-checklist.md`를 추가해 raw/source, parsed/storage, aggregate, display 경계를 체크리스트로 고정.
- `AGENTS`, `decision-log`, `current-work`, `project-map`, `surface-contract`, `execution-roadmap`에 결측값/중복표시 검토 기준을 반영.
- 2026-05-09 기준 `100% 목표`를 현재 단계의 결정 완료 상태로 재정의하고, `execution-roadmap`에 오늘 목표표와 진행률을 반영.
- `current-work`의 오래된 web-view 미래형 문구를 GET-only 1차 구현 완료 및 V1 마감 품질 진행 기준으로 정정.
- Mini PC/외부공유 문서에 Docker 보류, Windows N100 직접 실행, Cloudflare Tunnel은 `web-view` 포트만 노출, `admin-gui`/DB/`.env`/Telegram/scheduler control 비노출 원칙을 명시.
- `operator_memos`에 Docker 보류와 Cloudflare Tunnel 공유 범위, web-view V1 마감 품질 기준을 추가 기록.

## 2026-05-08

### 문서
- KRX Open API 발급 신청 이후 값을 받을 로컬 전용 템플릿 `data/krx_api_intake.local.md`를 추가.
- KRX post-approval 필드 검증 문서 `docs/codex/krx-api-field-validation.md`를 추가.
- `.env.example`에 KRX placeholder (`STOCK_MONITOR_KRX_AUTH_KEY`, `STOCK_MONITOR_KRX_BASE_URL`, `STOCK_MONITOR_KRX_TIMEOUT_SECONDS`)를 추가.
- `current-work`, `project-map`, `execution-roadmap`, `etf-flow-source-study`에 KRX P2 범위 신청 완료와 세부 field capture 대기 상태를 반영.
- `data/API_Specification/*.docx` 8개 명세서를 확인해 KRX endpoint, request parameter, response field를 `data/krx_api_intake.local.md`와 `docs/codex/krx-api-field-validation.md`에 반영.
- KRX base URL placeholder를 명세서 기준 `https://data-dbg.krx.co.kr`로 조정.
- KRX 8개 endpoint를 `AUTH_KEY` header + `POST` + JSON body로 `basDd=20260507` dry-run 검증. ETF, 유가증권/코스닥 일별매매정보, 종목기본정보, KRX/KOSPI/KOSDAQ 지수 일별시세정보가 모두 응답함.
- KRX dry-run의 endpoint별 row count와 첫 row 샘플을 `data/krx_api_dry_run_samples.local.json`에 저장.
- 외부 접속 후보를 Tailscale(본인 원격관리)과 Cloudflare Tunnel(친구용 read-only `web-view` 공유)로 좁혀 `execution-roadmap`, `surface-contract`, `mini-pc-migration-handoff`, `operator_memos`에 기록.

### DB
- `schema_migrations` 테이블 기반 formal migration runner를 추가.
- 기존 `PRAGMA user_version=1` 기준 DB를 `baseline_schema` migration 기록으로 보정.
- `python -m stock_monitor db-migrate [--dry-run]` 명령을 추가해 향후 KRX/ETF/flow 테이블 추가 전 schema 상태를 확인/적용할 수 있도록 정리.
- migration v2 `krx_market_snapshots`를 추가해 `stock_market_daily`, `etf_daily_snapshots`, `krx_stock_metadata`, `market_index_daily` 테이블을 생성.
- 운영 DB에 migration v2를 적용해 `Applied migration versions: 1, 2`, `Pending migration versions: (none)` 상태 확인.

### KRX
- `python -m stock_monitor krx-dry-run <endpoint|all> --date YYYY-MM-DD [--json] [--show-first-row]` CLI를 추가.
- KRX endpoint 검증을 임시 PowerShell 호출이 아니라 반복 가능한 Python 명령으로 수행할 수 있도록 정리.
- 실제 `stock-kospi-daily` 호출로 `rows=948` 및 필드 목록 출력 확인.
- `python -m stock_monitor krx-fetch-snapshot <endpoint|all> --date YYYY-MM-DD [--dry-run]` CLI를 추가.
- KRX 응답 row를 endpoint별 snapshot 모델로 변환하고 SQLite snapshot 테이블에 upsert하는 1차 저장 경로를 추가.
- 주식/ETF 코드는 6자리 코드만 저장 대상으로 삼고, 지수 가격/등락 공백은 정상적인 `NULL` 값으로 허용하도록 보강.
- `stock-kospi-daily --date 2026-05-07` 실제 저장 결과 `stock_market_daily`에 KOSPI 923건 저장 확인.
- `krx-query-snapshot` CLI와 repository read/query 메서드를 추가해 저장된 KRX 주식/ETF/지수 snapshot을 날짜별로 조회할 수 있도록 보강.
- 저장된 `2026-05-07` KOSPI snapshot 조회 결과 거래대금 상위 종목 5건 출력 확인.
- `operator-status`와 `admin-gui` 상태 스냅샷에 최신 KRX snapshot 기준 KOSPI/KOSDAQ/ETF/시장지수 표를 추가.
- 관리자 화면에 KRX 시장 데이터 섹션을 추가해 저장된 KRX 데이터를 화면 후보 정보로 바로 확인할 수 있도록 연결.

### 관리자 화면 / 집계
- 섹터 요약이 같은 섹터명이라도 `sector_code` 차이 때문에 중복 행으로 갈라지던 문제를 수정.
- 테마 요약도 같은 테마명이 여러 코드로 들어오는 경우 관리자 표시 기준에서는 한 줄로 합쳐지도록 보정.
- 섹터/테마 요약의 종목 수는 종목코드 우선 distinct 기준으로 계산하도록 정리.
- 네이버 업종 페이지 기반 소속 종목을 명시적으로 갱신하는 `refresh-industry <industry_code>` CLI를 추가.
- 업종 갱신은 `stock_metadata`의 대표 업종/섹터 캐시로 저장하고, 테마는 기존처럼 다중 membership으로 분리 유지.

### Web View
- 사용자/친구용 읽기 전용 화면의 첫 골격인 `web-view` CLI를 추가.
- `web-view`는 `admin-gui`와 별도 서버/핸들러/DTO를 사용하며, `/api/status`나 스케줄러 제어 API를 노출하지 않도록 분리.
- 첫 API로 `GET /api/archive`를 추가해 최근 business date별 리포트 수와 요약 종목 수를 제공.
- `web-view`의 `POST/PUT/PATCH/DELETE` 요청은 405로 차단하도록 테스트를 추가.
- `GET /api/daily/YYYY-MM-DD`를 추가해 날짜별 종목 요약, 업종 요약, 테마 요약, 시장 분위기를 읽기 전용 DTO로 제공.
- `GET /api/market`를 추가해 최신 KRX snapshot 기준 KOSPI/KOSDAQ/ETF/시장지수 참고값을 사용자 화면에서 읽을 수 있도록 연결.
- `web-view` 첫 화면을 최근 날짜 선택, 일일 종목 요약, 시장 분위기, 업종/테마 요약, KRX 시장 참고 섹션으로 확장.
- `web-view` 일일 화면에 점수/추천이 아닌 관찰 조건 기반 `관심 후보` 블록을 추가.
- `GET /api/intraday?date=YYYY-MM-DD`를 추가해 사용자 화면에서 날짜별 장중 배치 흐름을 읽기 전용으로 확인할 수 있도록 연결.
- 장중 흐름은 시간, 사용자용 상태 라벨, 신규 리포트 수, 종목 수만 노출하고 Telegram message id, raw error, scheduler/worker 내부값은 제외.
- `web-view`의 KRX 시장 참고 섹션을 KOSPI, KOSDAQ, ETF, 주요 지수 카드로 분리해 저장 스냅샷 기준 관찰값을 더 명확히 표시.
- `GET /api/daily/YYYY-MM-DD`의 종목별 요약에 같은 영업일 KRX 종가, 등락률, 거래대금, 시장 구분을 관찰값으로 붙이도록 확장.
- 사용자 화면의 일일 종목 요약 표에 `KRX 기준` 열을 추가해 목표가/의견과 실제 저장 종가 참고값을 한 화면에서 볼 수 있도록 정리.
- `GET /api/daily/YYYY-MM-DD/stocks/STOCK_CODE`를 추가해 선택 종목의 당일 리포트 제목, 증권사, 발행시간, 목표가, 의견을 읽기 전용으로 조회할 수 있도록 확장.
- 사용자 화면에 `선택 종목 리포트` 영역을 추가하고, 일일 종목 요약 행 클릭 시 같은 날짜/종목코드 기준 상세 리포트를 표시하도록 연결.
- `web-view`에 `?date=YYYY-MM-DD` 직접 진입, 이전/다음 날짜 버튼, 선택 날짜 URL 갱신을 추가해 아카이브 이동성을 개선.
- `GET /api/category?date=YYYY-MM-DD&type=sector|theme&name=...`를 추가해 업종/테마별 종목 목록을 읽기 전용으로 조회할 수 있도록 확장.
- 사용자 화면의 업종/테마 요약 행을 클릭하면 `카테고리 상세` 영역에 해당 종목, 리포트 수, 증권사, 목표가, 의견, KRX 기준값을 표시하도록 연결.
- 날짜 의존 admin GUI 테스트가 주말/휴일 현재 날짜에 흔들리지 않도록 기준 시각을 고정.
- `GET /api/category-trend?type=sector|theme&name=...`를 추가해 업종/테마별 최근 날짜 리포트 수와 종목 수 흐름을 읽기 전용으로 조회할 수 있도록 확장.
- 사용자 화면에 `카테고리 흐름` 영역을 추가해 선택 업종/테마가 최근 날짜에 얼마나 반복 등장했는지 점수 없이 관찰값으로 표시.

### Telegram
- `/메모` 저장을 Telegram update id 기준으로 replay-safe 처리.
- 메모 파일 append 이후 Telegram 확인 응답이 실패해도 다음 재처리에서 같은 메모가 중복 저장되지 않고 `메모 완료` 응답만 재시도되도록 보강.

### 검증
- `python -m pytest tests\test_control.py tests\test_cli_commands.py tests\test_telegram_command_replay.py -q` 통과: `28 passed`.
- `python -m pytest tests\test_repository.py tests\test_cli_commands.py -q` 통과: `32 passed`.
- `python -m pytest tests\test_repository.py tests\test_cli_commands.py -q` 통과: `37 passed`.
- `python -m pytest tests\test_repository.py tests\test_operator_status.py tests\test_admin_gui.py -q` 통과: `52 passed`.
- `python -m pytest tests\test_repository.py tests\test_operator_status.py tests\test_admin_gui.py -q` 통과: `54 passed`.
- `python -m pytest tests\test_stock_theme_fetch.py tests\test_cli_commands.py tests\test_repository.py -q` 통과: `44 passed`.
- `python -m pytest tests\test_web_view.py tests\test_cli_commands.py tests\test_admin_gui.py -q` 통과: `35 passed`.
- `python -m pytest tests\test_web_view.py tests\test_cli_commands.py tests\test_admin_gui.py -q` 통과: `37 passed`.
- `python -m pytest -q` 전체 통과: `157 passed`.
- `python -m pytest -q` 전체 통과: `159 passed`.
- `python -m pytest -q` 전체 통과: `163 passed`.
- `python -m pytest -q` 전체 통과: `165 passed`.
- `python -m pytest -q` 전체 통과: `167 passed`.
- `python -m pytest tests\test_web_view.py tests\test_repository.py -q` 통과: `30 passed`.
- `python -m pytest -q` 전체 통과: `169 passed`.
- `python -m pytest tests\test_web_view.py tests\test_repository.py -q` 통과: `31 passed`.
- `python -m pytest -q` 전체 통과: `170 passed`.
- `python -m pytest tests\test_web_view.py tests\test_repository.py -q` 통과: `33 passed`.
- `python -m pytest -q` 전체 통과: `172 passed`.
- `python -m pytest tests\test_web_view.py -q` 통과: `6 passed`.
- `python -m pytest -q` 전체 통과: `172 passed`.
- `python -m pytest tests\test_web_view.py tests\test_repository.py -q` 통과: `36 passed`.
- `python -m pytest -q` 전체 통과: `175 passed`.
- `python -m pytest tests\test_web_view.py tests\test_repository.py -q` 통과: `39 passed`.
- `python -m pytest -q` 전체 통과: `178 passed`.
- 운영 DB에 `python -m stock_monitor db-migrate` 실행 후 `Applied migration versions: 1, 2`, `Pending migration versions: (none)` 확인.

## 2026-04-26

### 추가
- Windows Task Scheduler 등록 스크립트와 실행 래퍼를 기준으로 자동 운영 표면 구성.
- Telegram 요약 페이징 명령 추가:
  - `다음`
  - `전부`
  - `처음`
- slash alias 지원:
  - `/다음`
  - `/전부`
  - `/처음`
- 종목 관련 Telegram 명령 추가:
  - `/종목코드 종목명`
  - `/종목검색 종목코드`
- `/도움말`, `/명령어` 안내 응답 추가.

### 변경
- 전일 요약 메시지를 3줄 중심 블록 형태로 정리.
- 기본 발송 종목 수를 `7`로 제한.
- 증권사 표시는 길어질 때 `외 N곳` 형태로 축약.
- 날짜 표기를 짧은 형식으로 정리.

### 검증
- `pytest -q` 통과.
- Task Scheduler 작업 등록 확인.

## 2026-04-28

### 안정화
- `manual-poll`에서 신규 리포트를 저장한 뒤 장중 알림 발송 전에 전일/당일 요약을 먼저 재빌드하도록 조정.
- 장중 Telegram 발송이 실패하더라도 SQLite의 `daily_stock_summaries`가 오래된 상태로 남지 않도록 보강.
- Telegram 명령 처리 중 여러 update가 들어온 상태에서 중간 발송이 실패해도, 이미 성공 처리한 update는 재처리되지 않도록 control state 저장 시점을 세분화.
- 수동 CLI `lookup-stock-research`도 Telegram `/종목검색`과 동일하게 현재가/섹터 정보를 formatter에 전달하도록 정리.
- 신규 리포트가 없는 poll에서도 pending/failed 장중 batch를 먼저 재시도한 뒤, 정말 처리할 batch가 없을 때만 `0건` 알림을 보내도록 수정.
- 여러 장중 batch가 pending 상태일 때, 첫 번째 다중 페이지 batch의 이어보기 상태가 뒤 batch 처리로 지워지지 않도록 보강.
- 수동 테스트 요약 발송이 production 전일 요약 페이징 상태를 변경하지 않도록 분리.
- README와 AGENTS 문서를 현재 운영 스케줄 기준으로 정리.
- Telegram 명령 확인 시간을 `08:00~16:30`으로 조정.
- 평일 `16:40`에 60초 대기 후 컴퓨터를 종료하는 `StockMonitor-Shutdown` 작업을 추가.
- 종료 작업은 놓친 실행이 나중에 따라 실행되지 않도록 `StartWhenAvailable`을 끄고 등록.

### 검증
- `pytest -q` 통과: `53 passed`
- 요약 재빌드 순서, Telegram command replay 방지, CLI 종목조회 quote 전달, pending 장중 batch 재시도, 다중 batch 페이징 보존, 테스트 발송 상태 분리 테스트 추가.

## 2026-04-30

### 추가
- Telegram 응답대기에서 `/메모 내용`을 받으면 `data/operator_memos.md`에 시각과 함께 저장.
- 메모 저장 후 사용자에게는 `메모 완료`만 짧게 응답.
- `/명령어`, `/도움말` 안내에 `/메모` 사용법을 추가.

### 변경
- 전일자 요약 발송은 기본 `7종목` 제한 없이 전체 종목을 보내도록 변경.
- 장중 알림과 명시적 `--limit` 지정 동작은 기존 제한 방식을 유지.

### 검증
- `/메모` 파싱과 로컬 메모 저장 테스트 추가.
- 전일자 production 요약이 기본 전체 발송 상태를 저장하는 테스트 추가.
- `pytest -q` 통과: `56 passed`

## 2026-05-01

### 수정
- `scheduled-telegram-commands` 명령을 추가해 휴장일에는 Telegram 명령 확인을 실행하지 않도록 보강.
- `scheduled-telegram-command-loop` 명령을 추가해 `08:00`에 한 번만 숨김 worker를 띄우고 내부에서 1분마다 응답대기를 확인하도록 변경.
- `scheduled-shutdown` 명령과 `run_scheduled_shutdown.ps1`을 추가해 휴장일에는 자동 종료도 실행하지 않도록 보강.
- `StockMonitor-Shutdown` 작업이 `shutdown.exe`를 직접 실행하지 않고 Python 영업일 guard를 거치는 래퍼를 실행하도록 변경.
- `StockMonitor-TelegramCommands`가 더 이상 Task Scheduler에서 1분마다 새 창을 띄우지 않도록 반복 트리거를 단일 시작 트리거로 변경.

### 검증
- `2026-05-05` 휴장일 기준 `scheduled-telegram-command-loop` skip 확인.
- PowerShell 스케줄러 스크립트 파싱 확인.
- `pytest -q` 통과: `59 passed`

## 2026-05-05

### 문서
- `example/report_*.jpg` 레퍼런스를 장마감/웹뷰 정보 구조 참고자료로 분석.
- 시장 분위기 카드, 섹터/테마 로테이션, 강세/부진 리스트, 관심 후보 블록을 future web-view backlog에 기록.
- 점수/등급/conviction 표시는 충분한 데이터와 산식이 생긴 뒤 검토하기로 정리.
- 스케줄러 상태, run-now, 응답대기 상태, 로컬 메모, 데이터 freshness를 눈으로 확인하고 조정하는 로컬 관리자 프로그램 아이디어를 backlog에 추가.
- `/메모` 내역과 이미지 레퍼런스를 기준으로 구현 가능 여부, 난이도, 우선순위를 정리한 backlog priority table 추가.
- 관리자 프로그램 P0 항목에 달력형 휴일 override 관리와 하단 상태/로그 패널 요구를 추가.
- 운영 안정화, 관리자 프로그램, 백그라운드 실행, 섹터/테마, 웹뷰, 미래 분석을 순서대로 정리한 planned sequence 표 추가.
- 관리자/worker 구조에서는 CMD/PowerShell 창 노출을 줄이거나 제거하는 것을 목표로 하도록 decision log에 기록.
- `example/Cycle.jpg`를 미래 섹터/테마 순환매 사이클 뷰 참고자료로 기록하고 planned sequence에 반영.
- 관리자 프로그램과 웹뷰의 기본 디자인 기준을 KRDS(Korea Design System)로 정하고, 사용자 중심/포용성/일관성/간결성/이해 가능성/신뢰성 원칙과 컴포넌트·패턴 우선 적용 방침을 문서화.
- 기존 `/메모` 항목 중 계획에 반영한 항목을 `[O]`로 표시하고, 새 메모는 `[ ]` 상태로 저장되도록 변경.

## 2026-05-06

### 수정
- 전일자 전체 요약이 Telegram 단일 메시지 길이 제한에 걸릴 수 있어, production daily summary를 여러 메시지로 자동 분할 발송하도록 변경.
- 분할 메시지는 종목 블록 중간에서 자르지 않고 페이지 번호를 붙여 발송하도록 정리.
- 전일 요약 단건 제외를 준비하기 위해 `STOCK_MONITOR_DAILY_SUMMARY_MIN_MENTION_COUNT`와 `--min-mentions` 옵션 추가.
- 관리자 화면 기반으로 사용할 `operation_events` 테이블과 운영 이벤트 기록 기능 추가.
- DB freshness, 최근 발송, 최근 운영 이벤트, pending 장중 batch를 확인하는 `operator-status` CLI 추가.
- `STOCK_MONITOR_HOLIDAYS`가 기본 2026년 시장 휴장일을 대체하지 않고 추가 병합되도록 변경.
- 시장 휴장일과 개인/운영상 실행 제외일을 분리하기 위해 `STOCK_MONITOR_RUN_SUPPRESSED_DATES` 추가.
- Poll, Notify, Telegram command worker, Shutdown이 개인 실행 제외일에는 내부 가드에서 건너뛰도록 보강.
- `operator-status`에 Windows Task Scheduler 작업 상태, 다음 실행, 마지막 실행, 마지막 결과 표시 추가.
- `STOCK_MONITOR_TASK_PREFIX`를 추가해 스케줄러 작업명 prefix가 바뀌어도 상태 조회 기준을 맞출 수 있도록 보강.
- GUI 단계 진입 기준과 현재 준비도를 `docs/codex/archive/admin-gui-progress.md`에 정리. 현재 대표 문서는 `docs/codex/admin-gui-plan.md`.
- GUI 버튼의 1차 백엔드가 될 `scheduler-control` CLI 추가.
- `scheduler-control`은 `run-now`, `enable`, `disable`을 지원하며 실제 실행은 `--confirm`이 필요하고 `--dry-run`으로 미리 확인 가능.
- GUI 일시정지/달력 제어의 1차 백엔드가 될 `operator_controls` SQLite 테이블 추가.
- `operator-control pause/resume/status`와 DB 기반 실행 제외일 `add-no-run-date/remove-no-run-date/list-no-run-dates` 추가.
- 스케줄 실행 가드가 시장 휴장일, env 실행 제외일, DB 실행 제외일, 운영 일시정지를 구분해서 처리하도록 보강.
- CLI와 미래 GUI가 같은 상태 데이터를 쓰도록 `build_operator_status_snapshot()` 추가.
- 로컬 읽기 전용 관리자 화면 `admin-gui` 추가.
- `admin-gui`에서 상태 카드, 스케줄러 작업, 최근 리포트/요약, 최근 발송, 최근 운영 이벤트를 표시하도록 구성.
- `admin-gui`에 운영 일시정지/재개 버튼과 DB 실행 제외일 추가/삭제 UI 추가.
- 관리자 화면의 제어 동작은 스케줄러 작업을 직접 지우지 않고 `operator_controls` 기반 내부 실행 가드를 조정하도록 제한.
- `admin-gui` 스케줄러 표에 `Notify`, `Poll`, `TelegramCommands` 즉시 실행 버튼 추가.
- GUI 즉시 실행은 `실행` 직접 입력 확인을 요구하고, `Shutdown` 즉시 실행은 차단.
- `admin-gui` 스케줄러 표에 예약 작업 활성화/비활성화 버튼 추가.
- GUI 활성화/비활성화는 `변경` 직접 입력 확인을 요구하도록 보호.
- `admin-gui`에 월별 실행 제외 달력 UI 추가.
- 달력 날짜 클릭으로 DB 실행 제외일을 추가하거나 삭제할 수 있도록 연결.
- `admin-gui` 상단 설명을 현재 제어 기능에 맞게 수정.
- 기본 2026년 시장 휴장일을 달력에 별도 색상과 `휴장` 라벨로 표시.
- `admin-gui` 초기화가 `불러오는 중`에 멈추던 JavaScript escape 함수 문법 오류 수정.
- `admin-gui`에서 별도 운영 제어 섹션과 DB 실행 제외일 표를 제거하고, 실행 제외 달력을 중심으로 배치 재정리.
- 최근 리포트/요약과 최근 발송을 상단 영역으로 이동.
- 달력 날짜 좌측 상단 숫자를 키우고, 라벨 영역 높이를 고정해 일반일/휴장일/제외일의 날짜 위치가 흔들리지 않도록 변경.
- 제외 날짜 우클릭으로 사유를 입력하거나 수정할 수 있도록 변경하고, 더블클릭 사유 편집은 제거.
- 실행 제외일은 `제외(사유)` 형태로 달력에 표시.
- `StockMonitor-*` 작업명 아래에 한글 설명을 추가하고, `StockMonitor-Shutdown` 동작은 알약 형태의 `실행 차단` 표시만 남김.
- `StockMonitor-Shutdown` 즉시 실행은 계속 차단하되, 활성화/비활성화 버튼은 다시 표시.
- `admin-gui` 상태 조회가 매번 Windows Task Scheduler PowerShell 조회를 반복해 달력 조작 후 렌더링이 늦어질 수 있어, GUI 전용 스케줄러 상태 TTL 캐시를 추가.
- 스케줄러 run-now/enable/disable 동작 후에는 캐시를 무효화해 조작 결과가 다음 상태 조회에 반영되도록 정리.
- 느린 `/api/status` 응답이 뒤늦게 도착해 최신 화면을 덮지 않도록 프런트 refresh 순번 가드와 중복 interval 방지 추가.
- 같은 날짜를 빠르게 연속 클릭할 때 중복 no-run 이벤트가 쌓이지 않도록 날짜별 pending guard 추가.
- GUI POST 실패를 최근 운영 이벤트에 `failed`로 기록하고, 화면 상단에도 작업 실패 메시지를 노출.
- `STOCK_MONITOR_RUN_SUPPRESSED_DATES` 기반 env 실행 제외일을 달력에 `환경제외`로 표시해 실제 실행 가드와 화면 표시가 어긋나지 않도록 보강.
- 스케줄러 활성화/비활성화 API의 `enabled` 값을 boolean으로 엄격 검증하도록 수정.
- `Get-ScheduledTaskInfo` 실패가 전체 스케줄러 표 실패로 번지지 않도록 작업별 실패 행으로 격리.
- 전일 요약 발송 필터를 기본 `2건 이상`으로 강화해 단건 리포트 종목은 수집/저장은 하되 발송에서 제외.
- 전일 요약 발송 시 목표가가 없는 종목을 기본 제외하도록 `STOCK_MONITOR_DAILY_SUMMARY_REQUIRE_TARGET_PRICE` 설정과 `--include-no-target-price` 완화 옵션 추가.

### 확인
- `2026-05-04` 전일자 요약 기준 `53종목`이 `2개` 메시지로 분할되는 것 확인.
- `operator-status` 현재 DB 기준 출력 확인.
- 승격 실행 기준 `StockMonitor-Notify`, `StockMonitor-Poll`, `StockMonitor-TelegramCommands`, `StockMonitor-Shutdown` 스케줄러 상태 조회 확인.
- `scheduler-control run-now --task poll --dry-run` 출력 확인.
- `operator-control`로 테스트 실행 제외일 추가, 목록 확인, 제거까지 확인.
- `admin-gui` 로컬 서버와 `/api/status` 응답 smoke 확인.
- `admin-gui` 로컬 서버에서 `pause -> resume -> status` smoke 확인.
- `admin-gui` 로컬 서버에서 `Shutdown` 즉시 실행 차단과 run-now 버튼 렌더링 smoke 확인.
- `admin-gui` 로컬 서버에서 잘못된 활성화/비활성화 확인문구 차단과 버튼 렌더링 smoke 확인.
- `admin-gui` 로컬 서버에서 실행 제외 달력 렌더링 smoke 확인.
- `admin-gui` 로컬 서버에서 새 상단 문구, 시장 휴장일 표시, 기존 문구 제거 smoke 확인.
- 브라우저에서 `불러오는 중`이 현재 시각 기준 상태 표시로 갱신되는 것 확인.
- `admin-gui` 새 화면에서 운영 제어 섹션 제거, DB 실행 제외일 표 제거, 한글 작업명, Shutdown 실행 차단 표시 smoke 확인.
- 브라우저에서 최근 리포트/요약과 최근 발송이 상단 영역에 표시되는 것 확인.
- `admin-gui` 스케줄러 상태 캐시 재사용과 스케줄러 조작 후 캐시 무효화 테스트 추가.
- `admin-gui` POST 실패 이벤트 기록과 `enabled` boolean 검증 테스트 추가.
- 전일 요약 단건 제외 기본값과 목표가 없음 제외 테스트 추가.
- `pytest -q` 통과: `96 passed`

## 2026-05-07

### 수정
- `admin-gui` 좁은 화면/스크롤 상황에서 카드, 테이블, 달력이 콘텐츠 최소폭 때문에 가로로 밀리던 문제 수정.
- `body`, `main`, 카드, 테이블, 달력 grid/cell에 overflow/min-width 방어를 추가해 모바일 폭 기준 가로 overflow가 발생하지 않도록 보강.
- 달력 실행 제외 사유 라벨은 작은 칸에서 여러 줄로 터지지 않도록 한 줄 말줄임 처리.
- `data/operator_memos.md`의 진행 상태를 재분류해 웹뷰/분석성 항목은 `[△]`, 구현 완료 항목은 `[O]`로 정리.
- 종목별 섹터 메타데이터를 저장하는 `stock_metadata` 테이블 추가.
- Naver quote 조회로 얻은 종목명, 섹터 코드, 섹터명을 `stock_metadata`에 캐시하도록 연결.
- 날짜별 daily summary와 `stock_metadata`를 조인해 섹터별 종목 수와 리포트 수를 집계하는 repository 조회 추가.
- `operator-status`/`admin-gui` 상태 스냅샷에 종목 메타데이터 수와 최신 요약일 기준 섹터 롤업을 포함.
- `admin-gui`에 최근 요약일 기준 `섹터 요약` 표 추가.
- 섹터 롤업 메모 항목을 1차 완료 `[O]`로 갱신하고, 차트형 고도화는 웹뷰 후속으로 분리.
- 최신 요약일 기준 리포트 수, 종목 수, 활성 섹터 수, 최다 섹터, 다건 종목 수, 매수 의견 수를 계산하는 시장 분위기 스냅샷 추가.
- `admin-gui` 상단에 `시장 분위기` 카드 추가.
- 시장 분위기 메모 항목을 1차 완료 `[O]`로 갱신하고, 점수/예측형 산식은 데이터 축적 후 후속으로 분리.
- Naver mobile theme API 기반 테마 종목 매핑 수집기 추가.
- 테마별 종목 매핑을 저장하는 `stock_theme_memberships` 테이블과 날짜별 테마 롤업 조회 추가.
- `refresh-theme` CLI를 추가해 필요한 테마 코드를 명시적으로 갱신할 수 있도록 구성.
- `operator-status`/`admin-gui` 상태 스냅샷에 테마 매핑 수와 최신 요약일 기준 테마 롤업을 포함.
- `admin-gui`에 최근 요약일 기준 `테마 요약` 표 추가.
- `505` 테마를 실제 갱신해 `67`개 종목 매핑 저장 확인.
- 테마 메모 항목을 1차 완료 `[O]`로 갱신하고, 전체 테마 자동 탐색/정기 갱신은 후속으로 분리.

### 확인
- Playwright 모바일 폭 검증 기준 `overflowX=542`에서 `overflowX=0`으로 개선 확인.
- `admin-gui` CSS 회귀 방지 테스트 추가.
- 섹터 메타데이터 upsert, 섹터 롤업, quote 조회 캐시 테스트 추가.
- 시장 분위기 스냅샷과 GUI 카드 노출 테스트 추가.
- Playwright 모바일 폭 기준 시장 분위기 카드 추가 후에도 `overflowX=0` 유지 확인.
- 테마 수집 파서, page size 제한, 테마 롤업, GUI 테마 표 노출 테스트 추가.
- `refresh-theme 505 --page-size 50 --max-pages 3` 실제 실행 확인.
- `pytest -q` 통과: `102 passed`

### 문서
- 새 `/메모` 5건을 검토해 `data/operator_memos.md`에 계획 반영 상태 `[△]`로 정리.
- N100 미니 PC 이전 후 외부 접속은 가능하되, 제어 가능한 관리자 화면을 직접 공개하지 않고 읽기 전용 공유/web-view와 분리하는 방향으로 정리.
- 국내 시장 테마 묶음은 `refresh-theme` 1차 구현을 기반으로 다중 테마 코드 관리, 테마 롤업 강화, 웹뷰 표시 조정으로 확장하기로 계획.
- 순환매/수급 추적은 리포트 수만으로 판단하지 않고 별도 거래량·수급 데이터 소스가 확보된 뒤 섹터/테마 흐름과 결합하는 후순위 분석 항목으로 분리.
- ETF 정보는 개별 기업 리포트와 데이터 성격이 달라 별도 수집/표시 모델로 검토하기로 정리.
- `docs/codex/current-work.md`의 backlog priority table과 planned sequence에 관리자/공유 페이지 분리, 미니 PC 원격 접속, 테마 v2, ETF, 수급 추적 항목을 추가.
- 에이전트 리뷰를 반영해 `docs/codex/future-webview-operation-plan.md` 상세 계획 문서를 추가.
- 원격 노출 전 `admin-gui` 로컬 제어면 고정, read-only `web-view` 분리, production daily summary 분할 발송 재개 안전성, Notify catch-up guard, stock-code-first summary grouping, 테마/섹터 dated snapshot 필요성을 우선 위험으로 정리.
- 관리자 페이지 평가와 제어조건 확장 방향을 `docs/codex/archive/admin-gui-evaluation-plan.md`로 정리. 현재 대표 문서는 `docs/codex/admin-gui-plan.md`.
- 전일 요약 최소 건수, 목표가 필수 여부, 기본 표시 수 같은 safe knob은 GUI에 올릴 수 있지만 raw `.env` 편집은 피하고 DB-backed settings, restart-required metadata, admin audit log를 먼저 두는 방향으로 정리.
- `admin-gui` 확장 전 우선 조치로 loopback-only guard, server-side no-run date validation, scheduler access denied vs missing classification, Telegram worker heartbeat, operation profile/shutdown policy를 문서화.
- 현재 구현 상태, operator memo, 관리자 GUI 계획, future web-view 계획, 에이전트 리뷰를 통합한 `docs/codex/execution-roadmap.md` 문서를 추가.
- 통합 로드맵의 다음 구현 순서를 `운영 계약 동결 -> 전달/집계 안전성 -> 관리자 안전/관측성 -> safe settings -> read-only web-view -> theme v2 -> ETF/flow`로 정리.
- `docs/codex/current-work.md`의 다음 세션 작업을 통합 로드맵 기준의 P0 작업으로 갱신.
- 외부 공유 대상이 소수라는 전제를 반영해 보안 방향을 경량화하되, `admin-gui` 제어면과 read-only `web-view` 분리 원칙은 유지하도록 로드맵을 보정.
- 순환매 예시와 사용자 메모를 반영해 ETF/수급 항목을 먼 후순위가 아닌 source study 및 read-only 표시 설계 우선순위로 상향.
- reviewer, backend-developer, cli-developer 에이전트 평가를 반영해 `docs/codex/execution-roadmap.md`에 `Progress Snapshot` 진행률 표와 상위 리스크를 추가.
- 진행률을 단일 총점이 아니라 Telegram MVP, local operator console, read-only web-view, data expansion layer로 분리해 후속 작업 우선순위를 판단하기 쉽게 정리.
- `admin-gui`가 기본적으로 loopback host(`localhost`, `127.0.0.1`, `::1`)에만 바인딩되도록 가드를 추가하고, 예외 시 `--allow-non-loopback` 명시 플래그를 요구하도록 변경.
- 관리자 화면 loopback guard 반영에 맞춰 `README.md`와 `execution-roadmap.md`의 관리자 진행률/리스크 설명을 갱신.
- 전일 요약 집계를 `stock_code` 우선으로 변경해 같은 코드/다른 이름은 하나로 묶고, 같은 이름/다른 코드는 분리되도록 하드닝.
- 코드 없는 리포트는 같은 날짜/같은 종목명에 단일 코드 후보가 있을 때만 해당 코드 그룹에 흡수하고, 후보가 모호하면 기존 이름 그룹으로 유지.
- `scheduled-notify` 지연 실행 가드를 추가해 `08:30` 이후에는 기본 발송하지 않고 `late_notify` skip 이벤트를 남기도록 변경. 긴급 수동 우회용 `--allow-late` 옵션 추가.
- production 전일 요약에 `daily_summary_delivery_runs`, `daily_summary_delivery_fragments` 기반 fragment resume을 추가해 중간 실패 후 재실행 시 이미 성공한 fragment를 재전송하지 않도록 변경.
- production 발송 detail은 `source=scheduled`, 테스트 발송 detail은 `source=manual_test`로 정리하고, fragment 이벤트에는 `run_id`와 fragment 위치를 기록.
- 전일 요약 전달/집계 하드닝 반영에 맞춰 `README.md`, `docs/codex/current-work.md`, `docs/codex/execution-roadmap.md`를 갱신.
- `operator-control explain-date YYYY-MM-DD [--json]`을 추가해 특정 날짜가 실행 가능한지와 휴장일/운영 일시정지/env 제외/DB 제외 원인을 구조화해서 볼 수 있도록 변경.
- `worker_state` 테이블을 추가하고 `scheduled-telegram-command-loop`가 시작/성공/오류/정상 종료 heartbeat를 저장하도록 보강.
- `operator-status` JSON에 `worker_states.telegram_command_loop`와 `health` 블록을 추가하고, `--health-exit` 사용 시 `warn`/`fail` 상태를 exit code `3`으로 반환하도록 변경.
- 스케줄러 상태에 `status_class`, `status_reason`을 추가해 `healthy`, `running`, `disabled`, `missing`, `access_denied`, `failed`, `stale`, `unavailable`을 구분하도록 정리.
- Admin GUI의 `/api/status`도 같은 상태 스냅샷을 사용하므로 health, worker heartbeat, scheduler classification이 API에 함께 노출되도록 변경.
- 운영자용 `admin-gui`와 친구/사용자용 `web-view`를 별도 surface로 분리하기로 결정하고, 권한/API/데이터 계약을 `docs/codex/surface-contract.md`에 문서화.
- `web-view`는 `admin-gui` read-only 모드가 아니라 별도 GET-only 페이지/핸들러/DTO로 구현하고, admin 제어 API와 raw 상태 payload를 노출하지 않는 원칙을 문서화.
- Telegram `/관리자페이지 열기` 아이디어는 구현하지 않고 보류 기능으로 문서화. 대신 `/상태`, `/오늘돌아?`, `/스케줄상태`, `/웹뷰주소` 같은 read-only 운영 확인 명령 후보를 backlog에 추가.
- 다음 진행사항을 전일 요약 fragment resume 실운영 확인과 ETF/flow source study 착수로 정리.
- ETF/수급 source study 1차 문서 `docs/codex/etf-flow-source-study.md`를 추가.
- ETF/일별 시세와 주식 일별 가격·거래량·거래대금은 KRX Open API를 1차 후보로, 종목별 투자자 수급은 KIS Developers를 후보로 두고 실제 필드 검증 전에는 ingest를 시작하지 않도록 정리.
- ETF/수급 데이터는 회사 리포트 테이블에 섞지 않고 별도 daily snapshot 계층으로 저장한 뒤 read-only web-view에서만 조인하는 방향으로 로드맵을 갱신.
- 에이전트 전수조사 결과를 반영해 `scheduler-control run-now --task shutdown`을 차단하고, `run-now --task all`에서도 Shutdown 실행을 제외.
- `scheduled-notify`가 `08:00` 이전에 오발송되지 않도록 하한 가드를 추가하고, 기존 `08:30` 이후 late guard와 함께 운영 이벤트를 남기도록 보강.
- 전일 요약 `다음/전부/처음` paging이 발송 필터와 다른 원본 summary를 다시 노출하지 않도록 현재 min-mentions/target-price 필터를 재적용.
- 장중 pending batch를 정상 재전송한 뒤에도 `0건` 메시지가 추가로 나갈 수 있던 반환값 문제를 수정.
- 장중 리포트 묶음도 종목명 대신 종목코드 우선 기준을 사용해 같은 코드/다른 이름 표기 drift가 한 종목으로 묶이도록 보강.
- 실행 제외일 POST/CLI 추가 시 시장 휴장일이나 env 실행 제외일을 DB 실행 제외일로 중복 저장하지 않도록 서버 측 검증을 추가.
- 실행 제외일/운영 pause일에는 스케줄러 stale health가 false fail로 잡히지 않도록 scheduler classification을 보정.
- DB 하드닝 1차로 SQLite 연결마다 `PRAGMA foreign_keys=ON`을 적용하고, `PRAGMA user_version` 기반 schema version 표시를 추가.
- `reports` 중복 방지를 `source_id`와 legacy identity unique index plus `INSERT OR IGNORE` 중심으로 보강해 read-then-insert 경합 위험을 줄임.
- 전일 요약 fragment resume 시 실패 run을 pending으로 되돌릴 때 `finished_at`과 `last_error`가 남지 않도록 lifecycle 필드를 정리.
- Telegram command worker가 `error`에서 `ok/starting/stopped`로 회복될 때 이전 `last_error`가 계속 표시되지 않도록 worker_state upsert를 보정.
- 미니 PC 이전 초안 문서 `docs/codex/mini-pc-migration-handoff.md`를 추가해 압축/복원, `.env`, 스케줄러 재등록, 검증 명령, 새 Codex 세션 브리핑을 정리.

## 2026-04-27

### 스케줄 / 운영
- 월요일 아침 실제 배치를 점검해 `StockMonitor-Notify`, `StockMonitor-Poll`, `StockMonitor-TelegramCommands`가 정상 실행되는지 확인.
- Telegram 명령 확인 주기를 `08:00~19:00 / 1분 간격`으로 조정.
- Notify 시간을 `08:00`으로, Poll 시간을 `08:30~16:30`으로 재설정.
- 스케줄러 작업을 숨김 창으로 실행하도록 변경.

### 수정
- 주말 테스트 발송 이력이 실배치 중복 가드에 걸려 월요일 아침 요약이 스킵되던 문제 수정.
- 수동 테스트 발송은 `telegram_test`, 실배치는 `telegram` 채널로 분리.
- 기존 테스트 발송 이력도 실배치 채널에서 분리되도록 마이그레이션.
- `/종목검색 로킷헬스케어`처럼 한글 6글자 이름이 종목코드로 오인되던 문제 수정.
- 한국어 검색 query 인코딩을 UTF-8 기준으로 고정.

### 추가
- `/종목검색` 결과에 현재가와 섹터 추가.
- 전일 요약, 장중 알림, 종목검색 헤더를 `종목명(코드) | 현재가 | 섹터` 계열로 통일.
- 장중 신규가 없을 때 보내는 빈 알림 추가:
  - `장중 신규 리포트가 없습니다 (0건 | 시각)`
- 장중 알림 단건/다건 분기 정리:
  - 단건은 제목 유지
  - 다건은 종목 묶음 + 목표가 범위

### 변경
- 장중 알림도 기본 `7종목`까지만 먼저 보내고 `다음, 전부, 처음`으로 이어보기 지원.
- 동일 종목 다건은 종목 단위로 묶고 목표가를 최소~최대 범위로 요약.
- 전일 요약에도 현재가를 붙여 장중/검색 응답과 톤을 맞춤.

### 안정화
- 장중 페이징이 모두 끝난 뒤 장중 상태를 자동 해제하도록 수정.
- 한 페이지로 끝나는 장중 배치는 장중 페이징 상태를 남기지 않도록 수정.
- 장중 페이징이 더 이상 없을 때 `다음/전부/처음`이 전일 요약 흐름으로 자연스럽게 넘어가도록 fallback 정리.

### 검증
- `pytest -q` 통과: `47 passed`
- 실제 스케줄러 재등록 후 다음 실행 시간 확인.
- 월요일 아침 놓친 요약은 보정 발송까지 확인.

## 메모

- 이 문서는 실제 변경 사항 중심으로 유지합니다.
- 판단 이유와 운영 원칙은 [docs/codex/decision-log.md](/docs/codex/decision-log.md)에 남깁니다.
- 현재 상태와 다음 작업은 [docs/codex/current-work.md](/docs/codex/current-work.md)에서 이어갑니다.
