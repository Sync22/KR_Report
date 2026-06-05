# Docs Role Reorganization Review Prompt

Use this prompt before moving or splitting files under `{PROJECT_ROOT}\docs`.

```text
{PROJECT_ROOT}만 기준으로 작업해줘.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 판단해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

목표:
docs 폴더 전체를 역할별 폴더로 나눌 수 있는지 검토하고, 실제 이동 전 안전한 재분류 계획을 작성해줘.

중요 경계:
- .env, Telegram token, KRX key, access-code는 출력하지 마.
- admin-gui는 외부 공유 금지.
- web-view만 외부 공유 후보.
- 추천/점수/등급/매수·매도 신호는 금지.
- KRX Data Marketplace 자동 수집은 리포트 언급 종목 [12009] 최근 31일 보강만 허용.
- broad ingest, 전체 종목 수집, [12008]/[12010] 자동 수집은 금지.

검토 기준:
1. docs/codex/documentation-index.md의 canonical 문서 목록을 먼저 기준으로 삼아.
2. current-work.md, next-phase.md, execution-roadmap.md처럼 자주 참조되는 문서는 이동 전 링크 영향도를 확인해.
3. 단순 history/detail 문서는 canonical 문서와 분리해도 되는지 확인해.
4. 문서 이동은 바로 하지 말고, 먼저 제안만 작성해.
5. 실제 이동이 필요하면 링크 수정 범위, 깨질 수 있는 참조, 검증 명령을 함께 제안해.

권장 역할 폴더 초안:
- docs/codex/details/krx/ : KRX/Data Marketplace 세부 근거, 캡처, 스키마 단계 문서
- docs/codex/contracts/ : canonical 정책 문서를 보조하는 세부 DTO/display/data-shape 계약
- docs/codex/plans/ : 현재 상태 anchor는 아니지만 여전히 유효한 세부 계획
- docs/codex/history/ : restore/change log 등 기록성 문서
- docs/codex/weekly-sync/ : 주간 sync guide/prompt 문서

주의:
current-work.md, next-phase.md, execution-roadmap.md, documentation-index.md, project-map.md, surface-contract.md, data-quality-checklist.md, data-source-policy.md, krx-market-data-runbook.md, mini-pc-migration-handoff.md 같은 canonical/운영 anchor는 경로를 유지하는 것을 기본값으로 삼아.

산출물:
1. 현재 docs 파일별 추천 역할 분류표
2. 이동하지 말아야 할 문서와 이유
3. 이동해도 되는 문서와 예상 새 경로
4. 링크 수정이 필요한 문서 목록
5. 실제 이동 전 확인 명령
6. 실제 이동 후 확인 명령
7. 주간 sync 프롬프트에서 바꿔야 할 경로가 있으면 수정 제안

주의:
문서 이동은 구현보다 링크 안정성이 중요하다. 실제 파일 이동은 내가 별도로 승인하기 전에는 하지 마.
```
