# Stock Monitor 임시·캐시·로그·DB 점검

- 점검일: 2026-10-01 (KST)
- 범위: `C:\Users\MING\Codex\02.Stock_Moniter` 및 이전 pytest 실행에서 확인된 여섯 개 `%TEMP%` 임시 폴더. `%TEMP%\pytest-of-MING`은 존재 여부만 확인.
- 결과: **실제 삭제 없음.** 프로젝트 파일·DB·서비스 설정도 수정하지 않음. 이 보고서와 별도 `.ps1` 초안만 새로 작성.
- CodeGraph: `.codegraph\codegraph.db`는 있으나 현재 사용할 수 있는 `codegraph` 명령/MCP가 없어 그래프 조회는 못 함. 이후 소스·문서의 경로 참조를 읽기 전용 검색.

## 판정 요약

| 분류 | 수량 / 결과 |
|---|---|
| 삭제 후보 | 격리 pytest 임시 디렉터리 6개, 합계 33,119,275 B |
| 검토 필요 | 운영 가능성이 있는 web-view 로그, restore-smoke DB, 리뷰 DB/산출물, 혼합 Playwright 자료, Telegram 상태 JSON, 원격 첨부 자료 |
| 유지 권장 | 운영 DB, DB 백업, CodeGraph 인덱스, 참조되는 운영/lab 로그, 정상 `__pycache__`, 가상환경 |
| 판단 불가 | `%TEMP%\pytest-of-MING` 내부, 출처가 불명확한 `debug.log` |

## 삭제 후보

여섯 폴더는 2026-10-01 새벽 테스트에서 지정한 pytest `--basetemp` 결과로 보인다. 각각 SQLite 테스트 DB, 테스트 상태 JSON, 테스트 실행 결과를 포함한다. 고유 경로에 대한 소스·설정 참조는 찾지 못했고, 실행 중인 Stock Monitor Python 프로세스 명령행에도 후보 경로가 없었다.

| 전체 경로 | 종류·크기 | 생성 → 수정 (KST) | 최근 사용 / 참조 / 실행 프로세스 | 분류·이유 |
|---|---|---|---|---|
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-0712dfd8eaa84b68b9b88cf0c940cb39` | 디렉터리; 1,720,765 B; 파일 5, 하위 디렉터리 8 | 2026-10-01 01:38:55 → 01:38:57 | 당일 새벽 pytest 산출물. 고유 경로 참조 없음. Python 명령행 경로 일치 없음. 열린 핸들은 확인 불가 | **삭제 후보** — 테스트 전용 경로. 잠금 확인 및 사람의 최종 확인 후에만 대상 |
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-6aed5d02457e4bd5b6a6b23afaf60d3e` | 디렉터리; 430,080 B; 파일 1, 하위 디렉터리 2 | 2026-10-01 01:40:53 → 01:40:53 | 위와 같음 | **삭제 후보** — 위와 같음 |
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-655a03a29eaf4690848fde0c639f44c9` | 디렉터리; 22,365,050 B; 파일 55, 하위 디렉터리 104 | 2026-10-01 01:41:42 → 01:41:57 | 테스트 출력과 임시 DB 포함. 고유 경로 참조·Python 명령행 일치 없음. 열린 핸들은 확인 불가 | **삭제 후보** — 테스트 전용 경로. 잠금 확인 및 사람의 최종 확인 후에만 대상 |
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-64757b1b7df34ea89cbb2401d86296dd` | 디렉터리; 3,871,610 B; 파일 11, 하위 디렉터리 18 | 2026-10-01 01:43:01 → 01:43:03 | 당일 새벽 pytest 산출물. 고유 경로 참조 없음. Python 명령행 경로 일치 없음. 열린 핸들은 확인 불가 | **삭제 후보** — 테스트 전용 경로. 잠금 확인 및 사람의 최종 확인 후에만 대상 |
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-659286aa98564ff0b4b3e8fed36c801d` | 디렉터리; 430,080 B; 파일 1, 하위 디렉터리 2 | 2026-10-01 01:45:24 → 01:45:24 | 위와 같음 | **삭제 후보** — 위와 같음 |
| `C:\Users\MING\AppData\Local\Temp\pytest-codex-stock-monitor-01894eddd1a2464390fc7b07cfb47534` | 디렉터리; 4,301,690 B; 파일 12, 하위 디렉터리 20 | 2026-10-01 01:46:08 → 01:46:11 | 위와 같음 | **삭제 후보** — 위와 같음 |

## DB 및 리뷰 산출물

| 전체 경로 | 종류·크기 | 생성 → 수정 (KST) | 참조·실행 사용 흔적 | 분류·이유 |
|---|---|---|---|---|
| `C:\Users\MING\Codex\02.Stock_Moniter\data\stock_monitor.db` | 운영 SQLite DB; 573,718,528 B | 2026-05-20 22:28:43 → 2026-10-01 10:22:07 | `src\stock_monitor\config.py` 기본 경로, CLI 및 운영 문서 참조. 프로젝트 `.venv`의 Telegram 명령 루프와 web-view Python 프로세스 실행 중 | **유지 권장** — 오늘 갱신된 운영 데이터 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\backups` | 디렉터리; 23개 파일, 합계 10,131,706,399 B. SQLite 백업 22개와 JSON 1개 | 생성 2026-05-20 22:28:44 → 폴더 수정 2026-09-08 07:12:47. DB 수정 범위 2026-05-16~2026-07-27 | readiness 스크립트와 runbook에서 `stock_monitor_*.db`를 복구 점검 대상으로 사용. 백업 이름은 restore, recovery, replay, repair 등의 시점을 표시 | **유지 권장** — 복구 지점이며 보존 기준 미확인 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\backups\telegram_stale_batch_20260908_071247.json` | JSON; 543 B | 2026-09-08 07:12:47 → 07:12:47 | Telegram 상태 관련 파일로 보임. Telegram 명령 루프 실행 중; 파일 핸들은 확인 불가 | **검토 필요** — 운영 상태 여부 미확인 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\restore-smoke\restore_smoke_20260602_113101.db` | SQLite; 472,162,304 B | 2026-06-02 11:31:01 → 11:30:07 | restore-smoke 검증 산출물. 운영 준비 점검 및 복구 문서에서 해당 절차를 참조 | **검토 필요** — 최신 검증 증거인지 확인 전 보류 |
| `C:\Users\MING\Codex\02.Stock_Moniter\.codegraph\codegraph.db` | 로컬 탐색 인덱스 DB; 15,175,680 B | 2026-05-20 22:28:24 → 2026-09-30 20:52:33 | 프로젝트 지침에 CodeGraph 인덱스 참조 | **유지 권장** — 운영 DB가 아님 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909` | 디렉터리; 31개 파일, 1,143,584,585 B | 2026-09-09 10:47:22 → 2026-09-14 20:42:25 | 뉴스 인텔리전스 문서가 이 리뷰의 테스트 결과와 날짜별 기록을 직접 인용 | **유지 권장** — 리뷰·검증 증거 포함 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\temporary-160026.db` | SQLite; 569,974,784 B | 2026-09-09 16:00:26 → 16:02:38 | 정확한 파일 참조는 없으나 상위 리뷰 자료가 문서에서 인용됨 | **검토 필요** — 리뷰 복사본일 가능성, 보존 여부 미확인 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\temporary-160403.db` | SQLite; 570,003,456 B | 2026-09-09 16:04:03 → 16:04:10 | 위와 같음 | **검토 필요** |

리뷰 디렉터리에는 위 두 DB 외에도 아래 7개의 테스트 DB가 있다. 각 파일은 417,792 B이며 2026-09-10 22:51:11~22:51:51에 생성·수정됐다. 고유 파일 경로의 운영 참조는 찾지 못했지만 상위 리뷰 증거와 함께 보존 여부를 확인해야 하므로 **검토 필요**로 분류했다.

- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose-trigger\test_toss_market_context_captu0\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose-trigger\test_toss_market_context_captu1\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose-trigger\test_toss_market_context_captu2\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose\test_collect_save_and_stored_p0\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose\test_toss_market_context_captu0\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose\test_toss_market_context_captu1\data\stock_monitor.db`
- `C:\Users\MING\Codex\02.Stock_Moniter\data\reviews\top2-search-20260909\test-afterclose\test_web_view_candidate_eviden0\data\stock_monitor.db`

## 로그·캐시·가상환경

| 전체 경로 | 종류·크기·날짜 | 참조·실행 사용 흔적 | 분류·이유 |
|---|---|---|---|
| `C:\Users\MING\Codex\02.Stock_Moniter\logs\api_perf.log` | 로그; 1,875,114 B; 수정 2026-09-30 11:15:09 | `web_perf.py` 및 CLI의 기본 로그 경로 | **유지 권장** — 운영 성능 진단 자료 |
| `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\realtime-first-review-snapshot.log` | 로그; 26,804 B; 수정 2026-09-30 15:00:12 | `scripts\run_realtime_first_review_snapshot.ps1`가 기록 | **유지 권장** — 최근 실행 이력 |
| `C:\Users\MING\Codex\02.Stock_Moniter\docs\codex\operations\insane-search-shadow-task.log` | 로그; 14,147 B; 수정 2026-09-04 15:02:21 | lab 예약 스크립트가 기록. 관련 예약 작업 2개가 Ready 상태 | **유지 권장** — 예약 lab 실행 기록 |
| `C:\Users\MING\Codex\02.Stock_Moniter\logs\web_view_stderr.log`; `C:\Users\MING\Codex\02.Stock_Moniter\logs\web_view_stdout.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\codex_webview_8781.err.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\codex_webview_8781.out.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_20260517_171603.err.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_20260517_171603.out.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_debug.err.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_debug.out.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_manual_restart.err.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_manual_restart.out.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_restart.err.log`; `C:\Users\MING\Codex\02.Stock_Moniter\data\logs\web_view_restart.out.log` | 로그 12개, 모두 0 B. 생성일은 2026-05-20~2026-06-18, 최종 수정은 2026-05-16~2026-06-20 | 정확한 파일 경로 참조는 못 찾음. 현재 web-view 프로세스 2개와 재시작 예약 작업이 있음. 열린 핸들은 확인 불가 | **검토 필요** — 실행 중 web-view와의 관계 배제 불가 |
| `C:\Users\MING\Codex\02.Stock_Moniter\debug.log` | 로그; 612 B; 수정 2026-06-05 16:13:36 | 코드·설정·프로세스의 정확한 경로 참조 없음. 내용과 생성 경위는 확인하지 않음 | **판단 불가** — 파일명과 날짜만으로 용도 확정 불가 |
| `C:\Users\MING\Codex\02.Stock_Moniter\.playwright-mcp` | 디렉터리; 121개 파일, 576,006 B. console 로그 26개, 합계 20,135 B; 최신 로그 수정 2026-08-31 | `.gitignore`에서 로컬 Playwright 자료로 제외. 나머지 파일 95개의 성격은 혼합 | **검토 필요** — 로그 내용·나머지 파일 보존 가치 미확인 |
| `C:\Users\MING\Codex\02.Stock_Moniter\scripts\lab\__pycache__` | 1개 파일; 30,233 B; 수정 2026-09-04 | Python 자동 생성 | **유지 권장** — 정상 캐시 |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\__pycache__` | 14개 파일; 2,065,392 B; 수정 2026-10-01 02:05:17 | 실행 코드의 Python 자동 생성 캐시 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\analysis\__pycache__` | 2개 파일; 48,841 B; 수정 2026-05-20 22:49:52 | Python 자동 생성 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\db\__pycache__` | 3개 파일; 227,776 B; 수정 2026-09-30 08:45:13 | Python 자동 생성 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\fetch\__pycache__` | 9개 파일; 147,100 B; 수정 2026-09-29 23:32:20 | Python 자동 생성 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\news\__pycache__` | 17개 파일; 168,470 B; 수정 2026-09-19 22:48:06 | Python 자동 생성 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\src\stock_monitor\notify\__pycache__` | 4개 파일; 48,981 B; 수정 2026-09-29 14:53:48 | Python 자동 생성 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\tests\__pycache__` | 53개 파일; 5,661,954 B; 수정 2026-10-01 01:22:51 | 테스트용 Python 자동 생성 | **유지 권장** — 정상 캐시를 통째로 삭제하지 않음 |
| `C:\Users\MING\Codex\02.Stock_Moniter\.venv` | 가상환경 디렉터리; 전체 용량·최종 수정 시각 미측정; 생성 2026-05-21 | 현재 프로젝트 Python 프로세스가 사용 중 | **유지 권장** |
| `C:\Users\MING\Codex\02.Stock_Moniter\scripts\experimental\.venv-scrapling` | 가상환경 디렉터리; 295,552,137 B; 생성·수정 2026-06-02 | 실험용 브라우저 소스 점검 환경 | **유지 권장** — 가상환경은 일괄 삭제하지 않음 |
| `C:\Users\MING\Codex\02.Stock_Moniter\.codex-remote-attachments` | 디렉터리; 18개 파일, 1,468,783 B; 생성·수정 2026-06-19 | 코드 참조 없음. 첨부 자료 용도·소유 불명 | **검토 필요** |

8개 `__pycache__` 디렉터리의 합계는 8,398,747 B입니다. 정상 Python 캐시이므로 삭제 후보로 잡지 않았습니다.

## 기타 확인 및 한계

- `%TEMP%\pytest-of-MING`은 존재합니다. 이번에는 요청대로 존재 여부만 확인했습니다. 이전 파일 열거가 ACL 오류로 막혀 내부 파일·크기·날짜는 **판단 불가**이며 삭제 후보가 아닙니다.
- 프로젝트 경로의 `.pytest_cache`, `.tmp_pytest_webview_contract`, `tests\.tmp_provider_pytest_20260929`, `tests\_tmp_webview`, `pytest-of-MING`, `src\stock_monitor.egg-info`, `tests\__pycache__\test_admin_gui.cpython-312-pytest-8.4.2.pyc`는 없습니다.
- 가상환경을 제외한 프로젝트 파일 검색에서는 `.sqlite`, `.sqlite3`, `.bak`, `.old`, `.tmp` 파일을 찾지 못했습니다. `data\reviews` 아래의 `temporary-*.db`는 별도 검토 대상으로 기록했습니다.
- 실행 중인 Stock Monitor Python 프로세스는 4개였습니다. 프로젝트 `.venv`에서 Telegram 명령 루프와 web-view가 각각 실행 중이고, 나머지 2개는 Codex 번들 Python 런타임입니다. `StockMonitor-TelegramCommands` 작업은 Running, `StockMonitor-WebViewHourlyRestart`는 Ready였습니다. 이름이 일치하는 Windows 서비스는 없었습니다.
- `openfiles /query`는 종료 코드 1이었고 `handle.exe`는 없어서 열린 파일 핸들을 확인하지 못했습니다. 원인은 확정하지 못했습니다. 이 때문에 어떤 프로세스도 해당 파일을 열고 있지 않다고 단정하지 않습니다.
- 실제 실행 검증: PowerShell 7.6.5에서 `.ps1`을 dry-run으로 실행했고 여섯 경로 모두 `DRY-RUN` 및 `독점 읽기 확인 통과`를 출력했습니다. Windows PowerShell `powershell.exe`로 같은 파일을 실행하면 `running scripts is disabled on this system` 오류로 **스크립트 본문 실행 전에** 차단됩니다. 실행 정책 변경이나 우회는 하지 않았습니다.
- CMD 초안 검증 중 `폴더\NUL` 확인식의 오판과 반복 서브루틴 복귀 오류를 발견해 고쳤습니다. 최종본은 고정 경로별 분기로 바꿨고, `cmd.exe /d /c`에서 여섯 대상 모두 `N`으로 취소해 마지막 `pause`까지 확인했습니다. 여섯 폴더가 그대로 존재하는 것도 재확인했습니다. 실제 `Y`+`DELETE` 삭제 경로는 실행하지 않았습니다. GUI 파일 연결을 이용한 더블클릭 자체는 이 세션에서 직접 누르지는 않았습니다.
- 파일의 최종 접근 시각은 판단에 사용하지 않았습니다. Windows 접근 시각 갱신은 비활성화될 수 있어, 수정 시각·소스 참조·프로세스 스냅샷으로 최근 사용 가능성을 판단했습니다.
- 확인 명령은 읽기 전용이었습니다. **삭제 명령은 실행하지 않았으므로 Codex 정책의 삭제 허용/차단 여부는 이번 점검에서 시험하지 않았습니다.**

## 삭제 전 사람 확인 목록

- [ ] 여섯 후보 경로가 아직 동일한 pytest 임시 결과인지 확인
- [ ] 현재 pytest·IDE·터미널이 해당 경로를 사용하지 않는지 확인
- [ ] 아래 스크립트를 재실행해 모든 후보가 `DRY-RUN`이고 `검토` 항목이 없는지 확인
- [ ] 테스트 재현 자료로 보존해야 할 결과가 없는지 확인
- [ ] 실제 삭제를 선택한다면 주석 처리된 삭제 블록을 본인이 직접 해제하고 대상 경로를 다시 확인

PowerShell 초안은 [`artifact_cleanup_dry_run_2026-10-01.ps1`](artifact_cleanup_dry_run_2026-10-01.ps1)에 있습니다. CMD 초안 [`artifact_cleanup_dry_run_2026-10-01.cmd`](artifact_cleanup_dry_run_2026-10-01.cmd)는 PowerShell을 호출하지 않으며, 각 경로를 열거한 뒤 `Y`와 정확한 `DELETE` 확인을 받아 해당 경로만 삭제합니다. 경로 확인과 파일 목록 실패 시 건너뛰고, 마지막에는 오류가 있어도 `pause`합니다. CMD에서 프로세스·열린 핸들은 확인하지 못하고, 실제 삭제 동작은 아직 실행하지 않았습니다.
