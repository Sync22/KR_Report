# Weekly Mini PC Sync Prompt

아래 프롬프트를 미니PC 쪽 Codex 세션에 붙여 넣어 주간 변경 묶음을 만들 때 사용한다.

```text
{PROJECT_ROOT}만 기준으로 작업해줘.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 판단해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

이번 작업 목표는 “이번 주 미니PC에서 생긴 변경점을 본컴 소스와 맞추기 위한 sync 묶음으로 정리”하는 것이다.

먼저 handoff/mini_pc_changes/WEEKLY_SYNC_GUIDE.md를 읽고, 그 양식에 맞춰 아래 파일을 작성해줘.

작성 파일:
handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md

반드시 포함할 내용:
1. 일자별 변경 내역
2. 일자별 변경 파일
3. 예상했던 조치 후 나아진 점
4. 패치 후 생길 수 있을 법한 문제
5. 검증 결과
6. 본컴 반영 필요 파일
7. 본컴 반영 제외 파일

변경 파일 판단 기준:
- source/code/test/docs/script 변경만 포함
- 운영 DB, backup, .env, access-code, token/key/password/cookie는 제외
- DB 상태를 설명해야 하면 row count, 날짜 범위, backup 파일명, SHA256만 기록

가능하면 아래 명령으로 현재 상태를 확인해줘.

python -m pytest -q
python -m stock_monitor db-verify
python -m stock_monitor operator-status --json --health-exit
python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20

그 다음 mini-pc-sync-YYYY-MM-DD.md의 “본컴 반영 필요 파일” 목록 기준으로 source/code/test/docs/script 파일만 zip으로 묶어줘.

압축 파일명:
handoff/mini_pc_changes/mini_pc_sync_YYYY-MM-DD.zip

SHA256 파일명:
handoff/mini_pc_changes/mini_pc_sync_YYYY-MM-DD.zip.sha256

zip 포함 가능:
- AGENTS.md
- README.md
- CHANGELOG.md
- .env.example
- pyproject.toml
- docs/
- src/
- tests/
- scripts/
- example/Cycle.jpg
- data/rotation_*.json
- handoff/mini_pc_changes/mini-pc-sync-YYYY-MM-DD.md

zip 제외:
- .env
- data/access_code.json
- data/stock_monitor.db
- data/backups/
- data/restore-smoke/
- *.log
- .venv/
- .pytest_cache/
- Stock_Moniter_migration_*.zip
- Stock_Moniter_migration_*.zip.sha256
- Telegram token
- KRX key
- password
- cookie
- access-code material

주의:
- public numeric 점수/투자등급/매수·매도 신호/매매 추천이 섞인 변경은 별도 위험으로 표시해. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위` 같은 관찰 후보 추천 문구는 허용 경계 안에서 검토해.
- admin-gui 외부 노출, 0.0.0.0 바인딩, Cloudflare tunnel target 변경은 별도 위험으로 표시해.
- KRX Data Marketplace broad ingest 관련 변경은 별도 위험으로 표시해.
- 미니PC 운영 중 임시로 고친 내용이라도 본컴 반영 전 검토가 필요하므로 “왜 바꿨는지”를 반드시 적어.

최종 보고:
핵심 변경:
- 작성한 sync 문서
- 생성한 zip/sha256 경로

검증:
- 실행한 명령과 결과

남은 작업:
- 본컴에서 확인해야 할 diff/주의사항
```
