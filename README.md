# Stock Monitor

네이버 증권 `리서치 > 종목분석 > 국내종목` 리포트를 장중 수집하고, Telegram 알림, 로컬 관리자 화면, 사용자용 읽기 전용 웹뷰로 국내 리포트와 KRX 시장 참고값을 확인하는 개인용 MVP입니다.

## 현재 운영 스케줄

- `StockMonitor-Notify`: 평일 `08:20` (공식 익영업일 `08:00` KRX Open API 발행 이후 `08:10` 보강을 전제로 전일자 briefing 발송)
- `StockMonitor-Poll`: 평일 `08:30~16:30`, 30분 간격
- `StockMonitor-KrxDailyBackfill`: 평일 `08:10`, 전영업일 또는 최근 누락 KRX Open API 일별 스냅샷 보강
- `StockMonitor-KrxMentionedFlowBackfill`: 평일 `16:00`, 당일 리포트 언급 종목만 최근 31일 `[12009]` 종목별 수급 보강. 기본 1회 최대 300콜, 최신일 우선
- `StockMonitor-TelegramCommands`: 평일 `08:00`에 숨김 루프 시작, `16:30`까지 1분 간격 확인. 휴장일에는 즉시 종료
- `StockMonitor-KrxFlowLoginReminder`: KRX 수급 검증용 로그인 안내 작업. 기본 운영에서는 비활성화하고, 수동 검증일에만 켬
- `StockMonitor-Shutdown`: 데스크톱 검증용 평일 `17:10` 종료 작업. 미니PC 상시운영 등록에서는 기본 제외

## 기본 실행

```powershell
python -m pip install -e .[dev]
python -m playwright install chromium
```

## 주요 명령

```powershell
python -m stock_monitor inspect-page --limit 5
python -m stock_monitor manual-poll --limit 20
python -m stock_monitor manual-poll --limit 20 --send-intraday-alert
python -m stock_monitor summarize-previous-business-day
python -m stock_monitor lookup-stock-code 삼성전자
python -m stock_monitor lookup-stock-research 005930
python -m stock_monitor send-test-notification --dry-run
python -m stock_monitor send-test-notification --dry-run --include-no-target-price
python -m stock_monitor operator-status
python -m stock_monitor operator-status --json --health-exit
python -m stock_monitor db-verify
python -m stock_monitor ops-readiness --recent-business-days 4 --stock-limit 20 --json
python -m stock_monitor db-backup --tag manual
python -m stock_monitor db-restore-smoke data\backups\stock_monitor_YYYYMMDD_HHMM_manual.db
python -m stock_monitor db-backup-prune --dry-run --keep 30
python -m stock_monitor db-cleanup --dry-run --retention-days 550
python -m stock_monitor db-vacuum --dry-run
python -m stock_monitor krx-backfill-missing daily --lookback-days 90 --max-dates 5 --dry-run
python -m stock_monitor krx-backfill-missing daily --lookback-days 90 --max-dates 5 --confirm --i-backed-up
python -m stock_monitor krx-openapi-availability-probe --date latest --endpoint daily --json
python -m stock_monitor scheduled-krx-mentioned-flow-backfill --dry-run
python -m stock_monitor admin-gui
python -m stock_monitor admin-gui --no-open
python -m stock_monitor admin-boundary-audit --json
python -m stock_monitor docs-hygiene-audit --json
python -m stock_monitor refresh-theme 505
python -m stock_monitor scheduler-control run-now --task poll --dry-run
python -m stock_monitor scheduler-control run-now --task poll --confirm
python -m stock_monitor scheduler-control restart --task telegram-commands --confirm
python -m stock_monitor scheduler-control disable --task shutdown --confirm
python -m stock_monitor scheduler-control enable --task shutdown --confirm
python -m stock_monitor operator-control status
python -m stock_monitor operator-control explain-date 2026-06-02
python -m stock_monitor operator-control explain-date 2026-06-02 --json
python -m stock_monitor operator-control pause --reason "manual maintenance"
python -m stock_monitor operator-control resume
python -m stock_monitor operator-control add-no-run-date 2026-06-02 --reason "personal off"
python -m stock_monitor operator-control remove-no-run-date 2026-06-02
python -m stock_monitor scheduled-poll --dry-run
python -m stock_monitor scheduled-notify --dry-run
python -m stock_monitor scheduled-notify --format summary --dry-run
python -m stock_monitor scheduled-notify --allow-late --dry-run
python -m stock_monitor scheduled-telegram-commands
python -m stock_monitor scheduled-telegram-command-loop --end-time 16:30 --interval-seconds 60
python -m stock_monitor scheduled-shutdown --dry-run
python -m stock_monitor process-telegram-commands
python -m stock_monitor process-intraday-alerts --dry-run
```

## 문서 기준

- 전체 문서 라우팅: `docs/codex/documentation-index.md`
- 현재 상태와 다음 작업: `docs/codex/current-work.md`
- 진행률과 P0/P1/P2 기준: `docs/codex/execution-roadmap.md`
- admin-gui와 web-view 경계: `docs/codex/surface-contract.md`
- KRX/ETF/수급 기준: `docs/codex/krx-market-data-runbook.md`
- 데이터 품질 규칙: `docs/codex/data-quality-checklist.md`

## Telegram 명령

- `/명령어`, `/도움말`
- `/메모 웹뷰에 섹터별 정리 추가`
- `/종목코드 삼성전자`
- `/종목검색 삼성전자`
- `/종목검색 005930`
- `/상태`
- `/오늘돌아?`
- `/스케줄상태`
- `/웹뷰주소`
- `다음`, `전부`, `처음`

위 명령은 현재 코드 파서와 봇 응답대기 기준으로 지원됩니다. Telegram 앱의 `/` 자동완성 명령어 메뉴 등록은 별도 BotFather 설정 또는 `setMyCommands` 연동이 필요하며, 아직 프로젝트 코드로 자동 관리하지 않습니다.

## 스케줄러 등록

미니PC 상시운영 기본 등록:

```powershell
$pythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe $pythonExe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe $pythonExe
```

가상환경을 쓰지 않는 경우에도 스케줄러에는 실제 사용할 Python 경로를 명시하는 쪽이 안전합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe "C:\path\to\python.exe"
```

데스크톱 검증처럼 `StockMonitor-Shutdown`까지 의도적으로 등록할 때만 일반 등록 스크립트를 사용합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_task_scheduler_tasks.ps1 -PythonExe $pythonExe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe $pythonExe -IncludeShutdown
```

`StockMonitor-KrxFlowLoginReminder`는 기본 등록 대상이 아닙니다.
수동 검증일에 로그인 안내가 필요할 때만 명시적으로 포함합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe $pythonExe -IncludeKrxFlowReminder
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_task_scheduler_registration.ps1 -PythonExe $pythonExe -IncludeKrxFlowReminder
```

## 환경변수

실제 값은 `.env`에 둡니다. `.env.example`을 참고하세요.

- `STOCK_MONITOR_TELEGRAM_BOT_TOKEN`
- `STOCK_MONITOR_TELEGRAM_CHAT_ID`
- `STOCK_MONITOR_DB_PATH`
- `STOCK_MONITOR_HOLIDAYS`
- `STOCK_MONITOR_RUN_SUPPRESSED_DATES` (시장 휴장일은 아니지만 내 PC에서 스케줄 실행만 쉬고 싶은 날짜)
- `STOCK_MONITOR_POLL_START_TIME`
- `STOCK_MONITOR_POLL_END_TIME`
- `STOCK_MONITOR_TASK_PREFIX` (Task Scheduler 작업명 prefix, 기본 `StockMonitor`)
- `STOCK_MONITOR_NOTIFICATION_DEFAULT_LIMIT` (장중/페이징 기본 표시 수)
- `STOCK_MONITOR_DAILY_SUMMARY_MIN_MENTION_COUNT` (전일 요약 최소 리포트 건수)
- `STOCK_MONITOR_DAILY_SUMMARY_REQUIRE_TARGET_PRICE` (전일 요약 발송 시 목표가 없는 종목 제외 여부)
- `STOCK_MONITOR_ACCESS_CODE_PATH` (admin-gui/web-view 1차 입장코드 hash 파일 경로)
- `STOCK_MONITOR_KRX_AUTH_KEY` (`08:10` KRX Open API 일별 스냅샷 보강용)
- `STOCK_MONITOR_KRX_DATA_MARKET_ID` / `STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD` (승인된 `[12009]` 당일 언급 종목 수급 보강용, broad ingest 금지)

## 운영 메모

- Telegram 테스트 발송은 실배치 중복 방지 채널과 분리되어 있습니다.
- 장중 신규 리포트가 없으면 `0건` 안내 메시지를 보냅니다.
- `operator-status`는 DB freshness, health 판정, 스케줄러 작업 상태, Telegram command worker heartbeat, 최근 발송, pending 장중 batch, 운영 이벤트를 보여주는 관리자 화면의 1차 기반입니다.
- `operator-status --json --health-exit`은 health가 `warn` 또는 `fail`이면 exit code `3`을 반환하므로 외부 자동화에서 상태 실패를 감지할 수 있습니다.
- `ops-readiness --recent-business-days 4 --stock-limit 20 --json`은 DB verify, 최신 KRX snapshot, KRX OpenAPI probe 최신 슬롯, web-view value QA, API 성능 로그를 한 번에 묶어 보는 운영용 읽기 전용 요약입니다.
- Task Scheduler 메타데이터가 `access_denied`이면 당일 실행 이벤트가 관측되어도 strict health는 `fail`로 유지합니다. 당일 `live_observation`은 실행 흔적을 보조로 보여줄 뿐, 작업 등록/다음 실행 예약 검증을 대체하지 않습니다.
- 단, `StockMonitor-KrxFlowLoginReminder`는 정상 운영에서 꺼두는 검증용 optional task이므로 metadata `access_denied`는 core scheduler fail이 아니라 warning으로 분리합니다.
- `live_observation`에서 아직 예정 시간이 오지 않은 작업은 `missing`이 아니라 `pending`으로 표시합니다. 예를 들어 `StockMonitor-KrxMentionedFlowBackfill`은 `16:30` 전까지 이벤트가 없어도 `pending`으로 봅니다.
- `db-verify`는 SQLite `integrity_check`, schema version, migration 상태, 주요 table row count, 중복 `source_id`, orphan delivery fragment, KRX/수급/category 품질 상태를 확인합니다.
- `db-backup`은 SQLite backup API로 `data/backups/stock_monitor_YYYYMMDD_HHMM_TAG.db` 백업을 만들고 기본적으로 백업 파일 integrity check를 수행합니다.
- `db-restore-smoke`는 백업 파일을 `data/restore-smoke` 아래 임시 DB로 복사한 뒤 integrity/schema/table 검증을 수행하고, 기본적으로 복사본을 삭제합니다. 운영 DB는 건드리지 않습니다.
- `db-backup-prune`은 오래된 백업 삭제 전 `--dry-run`으로 미리 확인하고, 실제 삭제에는 `--confirm`이 필요합니다.
- `db-cleanup`은 KRX snapshot 3종(`stock_market_daily`, `etf_daily_snapshots`, `market_index_daily`)만 정리 대상으로 삼고, `reports`와 delivery 상태는 보호합니다. 18개월 관찰/백테스트 기준을 유지하는 동안은 `--retention-days 550`을 사용하고, 실제 삭제 전 `--dry-run`으로 확인하며, 삭제 대상이 있으면 `--confirm`이 필요합니다.
- `db-vacuum`은 월 1회 또는 대량 cleanup 이후 SQLite 파일을 정리하는 명령입니다. 실제 실행은 `--confirm`이 필요하고, 평소에는 `--dry-run`으로 회수 가능 공간만 확인합니다.
- `krx-backfill-missing daily`는 3개월 기본 흐름 확인용으로 누락된 KRX 일별 endpoint만 최신 영업일부터 찾아 순차 수집합니다. 기본 `daily` 대상은 ETF, KOSPI/KOSDAQ 주식 일별, KRX/KOSPI/KOSDAQ 지수 일별이며 종목기본정보는 제외합니다.
- KRX backfill 실제 호출은 `--confirm --i-backed-up`이 필요합니다. `--i-backed-up`은 `db-verify`와 `db-backup`을 먼저 끝냈다는 운영 확인 플래그입니다. 기본은 최신 `5`영업일까지만 처리합니다. `--max-dates 5` 초과는 `--allow-large-batch`가 있어야 하며, 기본 endpoint 호출 간격은 `3초`입니다.
- DB 운영 기준은 현재 관찰/백테스트 구간 확장을 위해 KRX stock/ETF/index snapshot 18개월 보존, 웹뷰 기본 흐름 3개월 이상 조회, 주 1회 cleanup dry-run, 월 1회 또는 대량 삭제 후 `db-vacuum --dry-run` 확인입니다. 실제 VACUUM은 `--confirm`으로만 수행합니다. `reports`와 delivery 상태는 삭제하지 않는 원본/감사 데이터로 봅니다.
- `operator-control explain-date YYYY-MM-DD`는 해당 날짜가 실행 가능한지, 휴장일/운영 일시정지/env 제외/DB 제외 중 어떤 이유로 막히는지 설명합니다.
- `admin-gui`는 로컬 전용 관리자 화면입니다. 기본 주소는 `http://127.0.0.1:8765/`입니다.
- `admin-gui`는 기본적으로 `localhost`, `127.0.0.1`, `::1` 같은 loopback host만 허용합니다. 사설망에서 예외적으로 외부 바인딩이 필요할 때만 `--allow-non-loopback`을 명시합니다.
- `web-view`도 기본적으로 loopback host만 허용합니다. 친구 공유는 `web-view --host 127.0.0.1 --port 8780`을 유지하고 Cloudflare Tunnel이 해당 로컬 포트만 바라보게 하는 방식을 우선합니다.
- `access-code set`은 `admin-gui`와 `web-view` 공통 1차 입장코드를 켭니다. 코드는 평문 저장하지 않고 `data/access_code.json`에 PBKDF2-SHA256 salt/hash로 저장합니다. 상태 확인은 `access-code status`, 해제는 `access-code clear --confirm`입니다. `admin-gui`와 `web-view`는 서로 다른 세션 쿠키 이름을 쓰며, 입장 세션 쿠키는 `HttpOnly`, `SameSite=Lax`이고 Cloudflare Tunnel 같은 HTTPS 프록시 헤더가 있으면 `Secure`가 붙습니다.
- `admin-gui`에는 최신 요약일 기준 시장 분위기 카드가 있어 리포트 수, 종목 수, 활성 섹터, 최다 섹터, 다건 종목, 매수 의견 수를 확인할 수 있습니다.
- `admin-gui`는 운영자용 로컬 제어 콘솔입니다. 친구/외부 사용자용 정보 화면은 별도 `web-view`로 만들며, `admin-gui`의 read-only 모드로 대체하지 않습니다.
- `web-view`는 GET-only 정보 페이지로 두고 스케줄러, shutdown, 실행 제외일, `.env`, Telegram 설정 같은 제어/운영 정보는 노출하지 않습니다. 기본 로딩은 저장 데이터 기준이며, 예외적으로 사용자가 현재 영업일에 직접 누르는 `장중 거래대금 확인` 버튼만 Naver `priceTop`을 `Naver 장중 참고`로 조회합니다. 이 live reference는 DB 저장, Telegram 발송, 스케줄러 변경, KRX 공식 저장값 대체를 하지 않습니다.
- `admin-gui`에는 월별 실행 제외 달력이 있으며 날짜 클릭으로 DB 실행 제외일을 추가/삭제할 수 있습니다.
- `admin-gui`에는 최근 요약일 기준 섹터 요약 표가 있어 섹터별 종목 수와 리포트 수를 확인할 수 있습니다.
- `admin-gui`에는 최근 요약일 기준 테마 요약 표도 있어 `refresh-theme`로 저장한 테마 매핑과 daily summary가 겹치는 종목을 확인할 수 있습니다.
- `refresh-theme 505 --snapshot-date YYYY-MM-DD`는 Naver mobile theme API에서 해당 테마의 종목 매핑을 가져와 SQLite에 저장합니다. `category_master.enabled=false`인 카테고리는 관리 대상/웹뷰 표시에서 제외됩니다.
- `refresh-industries --enabled --snapshot-date YYYY-MM-DD`는 enabled sector catalog 중 `source=naver_industry` 또는 `source=naver_upjong`으로 검증된 row만 Naver industry 매핑 일괄 갱신 대상으로 봅니다. `source=naver_quote` row는 현재 화면 표시/cache용 분류라 업종 API code로 간주하지 않고 건너뛰며, 이 상태에서 sector fallback 날짜가 남아 있으면 `db-verify`와 `operator-status`가 `sector_catalog_not_refreshable` 경고를 냅니다. 실행 전 `--dry-run`으로 대상과 호출 수를 먼저 확인하고, 실제 실행은 `--confirm`과 `--delay-seconds`를 함께 사용합니다. 현재 Naver PC 업종 화면은 `upjong/{industry-code}` API를 사용하므로, 신규 후보는 `category-catalog discover-industries --limit N`으로 찾고, 개별 후보는 `refresh-industry CODE --dry-run`으로 검증한 뒤 출력되는 `category-catalog add sector CODE --source naver_industry` 명령으로 catalog에 등록합니다. Discovery 출력은 기존 sector catalog와 같은 표시명인지 `existing=Y(key/source)`로 보여주므로, 기존 `naver_quote` row를 덮어쓰거나 relabel하지 말고 검증된 `naver_industry` row를 별도로 추가할지 판단합니다. 예: `refresh-industry 307 --dry-run`은 `전자제품` 업종 preview를 반환합니다.
- `refresh-themes --enabled --snapshot-date YYYY-MM-DD`도 batch 실행 전 `--dry-run` 검토가 우선이며, 실제 네트워크/DB 쓰기는 `--confirm`이 있어야 진행됩니다.
- `category-snapshot-from-cache --snapshot-date YYYY-MM-DD --type all`은 추가 네트워크 호출 없이 기존 `stock_metadata`, `stock_theme_memberships` 캐시를 날짜별 `category_master`/`category_membership_snapshots`로 승격합니다.
- `category-snapshot-status --limit 20 --mode all|dated|fallback`은 요약 날짜별로 dated category snapshot을 쓰는지, 아니면 `latest_mapping_fallback`으로 내려가는지 읽기 전용으로 확인합니다.
- `category-snapshot-plan --limit 20`은 fallback 날짜와 다음 source-date snapshot 확보 명령 템플릿을 읽기 전용으로 보여줍니다. 실제 수집이나 DB 쓰기는 하지 않습니다.
- 달력에서 제외된 날짜를 우클릭하면 실행 제외 사유를 입력/수정할 수 있고, 화면에는 `제외(사유)`로 표시됩니다.
- 운영 일시정지/재개 API는 남아 있지만, GUI에서는 날짜 기반 실행 제외 달력을 중심으로 운영합니다.
- `admin-gui` 달력은 기본 시장 휴장일을 별도 색상으로 표시합니다. 현재 기본 holiday set은 2024~2026 KRX 휴장일을 포함합니다. 시장 휴장일은 이미 내부 영업일 가드가 쉬는 날로 처리하므로 별도 DB 실행 제외일 추가가 필요 없습니다.
- `admin-gui`에서는 `Notify`, `Poll`, `TelegramCommands` 작업을 즉시 실행할 수 있습니다. `Shutdown` 즉시 실행은 GUI에서 차단합니다.
- `admin-gui`와 `scheduler-control`은 `TelegramCommands` 작업 재시작을 recovery control로 제공합니다. 재시작은 `재시작` 확인 문구 또는 CLI `--confirm`이 필요하며, `Shutdown` 재시작은 제공하지 않습니다.
- `admin-gui`에서는 예약 작업 활성화/비활성화도 할 수 있습니다. `Shutdown`은 즉시 실행만 차단하고, 활성화/비활성화는 가능합니다. 즉시 실행은 `실행`, 활성화/비활성화는 `변경`을 직접 입력해야 동작합니다.
- Windows 권한 때문에 스케줄러 작업이 `확인 불가`로 보이면 스케줄러 제어 버튼은 사용할 수 없습니다. 운영 일시정지/재개와 실행 제외일 관리는 SQLite 기반이라 일반 실행에서도 동작합니다.
- `operator-status`의 스케줄러 정보는 Windows 예약 작업 자체의 메타데이터이고, `worker_states.telegram_command_loop`는 `StockMonitor-TelegramCommands` 내부 1분 루프 heartbeat입니다.
- 스케줄러 작업 상태는 Windows 권한에 따라 `액세스 거부`로 보일 수 있습니다. 실제 GUI 단계에서는 권한/실행 방식을 별도로 정리해야 합니다.
- `scheduler-control`은 GUI 버튼의 1차 백엔드입니다. 실제 실행/활성화/비활성화는 `--confirm`이 있어야 동작하고, 먼저 `--dry-run`으로 확인할 수 있습니다.
- `operator-control`은 GUI 달력/일시정지 버튼의 1차 백엔드입니다. 스케줄러 작업을 직접 지우지 않고 SQLite의 운영 제어 상태로 내부 실행 가드를 걸어둡니다.
- `operation_profile`은 `desktop-validation`, `mini-pc`, `manual-only` 중 하나입니다. `mini-pc`는 scheduled shutdown만 건너뛰고, `manual-only`는 scheduled poll/notify/telegram/shutdown wrapper를 건너뜁니다.
- `mini-pc-preflight`는 미니피시 이전 전 DB, 백업, 스케줄러 스크립트, canonical 문서/자산, Telegram/KRX 환경변수 존재 여부를 secret 출력 없이 확인합니다. `scripts/setup_mini_pc_environment.ps1`는 새 Windows PC에서 `.venv` 생성, dev editable install, Playwright Chromium 설치, readiness 점검을 한 번에 실행합니다. 이 setup 단계는 archive가 `.env`와 `data/backups`를 제외하는 점을 고려해 env 요구, 백업 요구, restore-smoke를 기본 스킵하고, 스케줄러 등록 전이므로 `operator-status` 검사도 기본 스킵합니다. setup 후 `.env`를 대상 PC에서 직접 작성하고 `db-backup --tag post-restore`로 새 백업을 만든 다음 `verify_mini_pc_readiness.ps1`의 전체 검증을 실행하고, 스케줄러 등록 후 `verify_task_scheduler_registration.ps1`와 `operator-status --health-exit`로 확인합니다. Windows 실행 정책에 막히면 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_mini_pc_environment.ps1` 형식으로 실행합니다. `scripts/register_mini_pc_scheduler_tasks.ps1`는 상시운영 미니PC용 스케줄러를 등록하면서 `StockMonitor-Shutdown`을 기본 제외합니다. 미니PC 검증 후 기존 데스크톱은 `scripts/disable_source_desktop_scheduler_tasks.ps1 -DryRun`으로 미리 보고 `-ConfirmDisable`로 비활성화해 두 호스트가 동시에 발송/수집하지 않게 합니다. `scripts/verify_mini_pc_readiness.ps1`는 `pytest`, `db-verify`, 최신 백업 `db-restore-smoke`, `mini-pc-preflight`, `web-view-value-qa`, `operator-status`를 묶어 실행합니다. `-SkipEnvRequirement`나 `-SkipBackupRequirement`를 주면 초기 setup처럼 env/백업 요구를 건너뜁니다. `scripts/verify_task_scheduler_registration.ps1`는 스케줄러 등록 후 필수 작업명, 실행 스크립트, Python 경로 포함 여부를 확인합니다. `scripts/verify_external_web_view_readiness.ps1`는 외부공유 직전 `access-code`, 백업/env, public-safe web-view 값 QA, 터널 대상 `127.0.0.1:8780` 원칙을 함께 확인하고, access-code가 꺼져 있으면 stack trace 없이 `access-code set/status` 다음 조치를 출력한 뒤 실패합니다. `scripts/create_migration_archive.ps1`는 기본적으로 `.env`, `data/access_code.json`, `data/backups`, 기존 `Stock_Moniter_migration_*.zip`/`.sha256`, 캐시/로그/실험용 venv를 제외하고 이관용 zip과 SHA256 sidecar를 만듭니다. 복사 후 `scripts/verify_migration_archive.ps1 -ArchivePath <zip> -FailOnSensitiveEntries`로 무결성, 필수 프로젝트 파일 포함 여부, 민감/불필요 항목(`.env`, `data/access_code.json`, `data/backups`, `data/restore-smoke`, 로그, 중첩 migration zip) 포함 여부를 확인합니다.
- 미니PC 기본 모드의 `verify_task_scheduler_registration.ps1`는 기존 `StockMonitor-Shutdown` 작업이 남아 있으면 실패합니다. 상시운영 미니PC에서는 이 실패가 정상적인 안전장치이며, 데스크톱 검증용으로 확인할 때만 `-IncludeShutdown`을 붙입니다.
- 전일 요약 발송은 기본적으로 `2건 이상`이고 `목표가가 있는` 종목만 보냅니다. 수집과 DB 저장은 그대로 유지합니다.
- `scheduled-notify`의 기본 Telegram 포맷은 당분간 `briefing`입니다. 기본 등록 시간은 `08:20`으로, 공식 익영업일 `08:00` KRX Open API 발행 이후 `08:10` 전영업일 보강 결과를 함께 사용할 수 있게 둡니다. 기존 전일자 목록형 포맷은 `--format summary`로 강제할 수 있습니다. `send-test-notification` 기본값은 기존 `summary`입니다.
- `scheduled-notify`는 `08:30` 이후 지연 실행되면 기본적으로 발송하지 않고 skip 이벤트만 남깁니다. 긴급 수동 발송이 필요할 때만 `--allow-late`를 명시합니다.
- production 전일 요약은 분할 메시지별 발송 상태를 저장하므로 중간 실패 후 재실행하면 이미 성공한 조각은 다시 보내지 않습니다.
- 전일 요약 집계는 `stock_code`를 우선 기준으로 묶고, 코드가 없는 리포트는 같은 날짜/같은 종목명에 단일 코드 후보가 있을 때만 해당 그룹에 흡수합니다.
- 단건 종목까지 보고 싶으면 `STOCK_MONITOR_DAILY_SUMMARY_MIN_MENTION_COUNT=1` 또는 `--min-mentions 1`을 사용합니다.
- 목표가 없는 종목까지 보고 싶으면 `STOCK_MONITOR_DAILY_SUMMARY_REQUIRE_TARGET_PRICE=false` 또는 `--include-no-target-price`를 사용합니다.
- `/메모`로 새로 저장되는 아이디어는 `- [ ]`로 남기고, 진행 중/백로그 반영은 `- [△]`, 구현 완료는 `- [O]`로 표시합니다.
- `StockMonitor-Shutdown`은 데스크톱 검증용 종료 작업입니다. 미니PC 상시운영에서는 `register_mini_pc_scheduler_tasks.ps1`를 사용해 기본 제외합니다.
- 예정된 종료 60초 대기 중 취소가 필요하면 `shutdown /a`를 실행합니다.
- 2024~2026년 KRX 시장 휴장일은 기본값에 포함되어 있고, `STOCK_MONITOR_HOLIDAYS`는 기본값에 추가 병합됩니다.
- 임시로 내 컴퓨터에서만 실행을 쉬고 싶은 날짜는 `STOCK_MONITOR_RUN_SUPPRESSED_DATES`에 넣습니다. 이 값은 리포트 영업일 계산에는 쓰지 않고 스케줄 실행 가드에만 사용합니다.
- 실행 중인 Telegram command loop는 시작 시점의 `.env`를 들고 있으므로, 날짜 설정을 바꾼 직후에는 작업을 재시작하는 편이 안전합니다.
- 향후 N100 같은 상시 Windows 미니 PC로 옮길 수 있도록 `.env`, SQLite, Task Scheduler 중심 구조를 유지합니다.
