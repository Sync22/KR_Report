# Weekly Mini PC Sync Guide

미니PC에서 생긴 코드/문서/테스트 변경을 본컴 소스 기준으로 주간 동기화하기 위한 행동지침입니다.

## 목적

- 미니PC는 실운영 기준이다.
- 본컴은 소스 정리, 검토, 백업, 다음 개발 기준이다.
- 미니PC 변경은 주 1회 또는 큰 수정 후 본컴으로 가져와 검토 반영한다.
- 운영 데이터와 비밀값은 코드 동기화 대상이 아니다.
- 이 채팅/작업 위치가 미니PC일 때 `handoff/mini_pc_changes/`는 본컴으로 넘길 변경 묶음을 정리하는 outbound 위치다.

## 미니PC에서 매주 작성할 파일

권장 파일명:

```text
mini-pc-sync-YYYY-MM-DD.md
```

권장 위치:

```text
handoff/mini_pc_changes/
```

## 작성 양식

```markdown
# Mini PC Sync - YYYY-MM-DD

## 1. 요약

- 이번 주 변경 목적:
- 운영 중 발견한 문제:
- 최종 상태:

## 2. 일자별 변경 내역

| 날짜 | 변경 내용 | 이유 |
| --- | --- | --- |
| YYYY-MM-DD |  |  |

## 3. 일자별 변경 파일

| 날짜 | 파일 | 변경 성격 |
| --- | --- | --- |
| YYYY-MM-DD | `src/...` | 코드 / 테스트 / 문서 / 스크립트 |

## 4. 예상했던 조치 후 나아진 점

| 조치 | 기대 효과 | 실제 확인 |
| --- | --- | --- |
|  |  |  |

## 5. 패치 후 생길 수 있을 법한 문제

| 위험 | 영향 | 확인/완화 방법 |
| --- | --- | --- |
|  |  |  |

## 6. 검증 결과

| 명령 | 결과 |
| --- | --- |
| `python -m pytest -q` |  |
| `python -m stock_monitor db-verify` |  |
| `python -m stock_monitor operator-status --json --health-exit` |  |
| `python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20` |  |

## 7. 본컴 반영 필요 파일

```text
AGENTS.md
README.md
CHANGELOG.md
docs/codex/...
src/stock_monitor/...
tests/...
scripts/...
```

## 8. 본컴 반영 제외

```text
.env
data/access_code.json
data/stock_monitor.db
data/backups/*.db
.venv/
.pytest_cache/
Stock_Moniter_migration_*.zip
Stock_Moniter_migration_*.zip.sha256
```

## 9. 특이사항

- access-code, Telegram token, KRX key, password, cookie, DB backup 원본은 기록하지 않는다.
- DB 상태를 전달해야 하면 row count, 날짜 범위, backup 파일명, SHA256만 기록한다.
```

## 압축 파일 기준

미니PC에서 본컴으로 가져올 zip은 source/code/test/docs/script 변경만 포함합니다.

포함 가능:

- `AGENTS.md`
- `README.md`
- `CHANGELOG.md`
- `.env.example`
- `pyproject.toml`
- `docs/`
- `src/`
- `tests/`
- `scripts/`
- `example/Cycle.jpg`
- `data/rotation_*.json`
- `handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md`

제외:

- `.env`
- `data/access_code.json`
- `data/stock_monitor.db`
- `data/backups/`
- `data/restore-smoke/`
- `*.log`
- `.venv/`
- `.pytest_cache/`
- `Stock_Moniter_migration_*.zip`
- `Stock_Moniter_migration_*.zip.sha256`
- Telegram/KRX/access-code/password/cookie 같은 비밀값

## 본컴에서 받을 때 처리 순서

1. `handoff/mini_pc_changes/`에 zip과 sync markdown을 둔다.
2. 압축을 임시 폴더에 푼다.
3. 파일별 diff를 확인한다.
4. 실제 본문 파일에 선택 반영한다.
5. focused tests를 먼저 돌린다.
6. 전체 `python -m pytest -q`를 돌린다.
7. canonical 문서와 `CHANGELOG.md`를 현행화한다.
8. 필요하면 본컴에서 다시 미니PC 반영용 patch zip을 만든다.

## 판단 기준

- 미니PC 운영 중 수정된 내용이 항상 정답은 아니다. 본컴 반영 전 테스트와 canonical 문서 기준으로 검토한다.
- DB/운영 데이터는 source sync가 아니라 별도 backup/restore 정책으로 다룬다.
- 외부공유, access-code, admin-gui 노출, KRX broad ingest, public numeric 점수화, 투자등급, 매수·매도 신호, 매매 추천 관련 변경은 본컴 반영 전 별도 검토가 필요하다. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위` 같은 관찰 후보 추천 문구는 canonical 허용 경계에 맞는지 확인한다.
