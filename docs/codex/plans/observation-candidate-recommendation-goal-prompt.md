# Observation Candidate Recommendation Goal Prompt

Use this prompt when starting the next implementation pass for stored-data based observation-candidate recommendation.

```text
/goal {PROJECT_ROOT} only.

AGENTS.md와 docs/codex/documentation-index.md를 먼저 읽고, 현재 canonical 문서 기준으로만 작업해줘.
이 폴더 밖의 다른 프로젝트나 과거 문서는 참조하지 마.

현재 위치는 미니PC다.
이 미니PC는 운영 기준이고, 메인PC로 넘길 변경 묶음은 handoff/mini_pc_changes/에 정리한다.

비밀값 주의:
.env, Telegram token, KRX key, access-code, password, cookie는 출력하지 마.
admin-gui는 외부 공유 금지.
web-view만 외부 공유 후보.
KRX Data Marketplace 자동 수집은 리포트 언급 종목 [12009] 최근 31일 보강만 허용한다.
broad ingest, 전체 종목 수집, [12008]/[12010] 자동 수집은 금지한다.

이번 목표:
저장된 리포트/KRX/수급 데이터 기준으로 web-view의 관찰 후보 추천 v1을 구현해줘.

제품 경계:
이 프로젝트는 매매 추천은 하지 않지만, 관찰 대상을 추천한다.
허용: 오늘의 관찰 후보, 우선 확인, 관찰 우선순위, 관심도 높은 흐름, 왜 눈에 띄는지, 리포트 집중, 수급 참고, 과열 참고, 시장 분위기, 확인 포인트.
금지: 매수 추천, 매도 추천, 지금 사라/팔아라, 진입가, 청산가, 익절가, 목표 수익률, 확신도, 투자등급, 오를 종목 단정, 자동 매매/전략 제안처럼 보이는 문구.

구현 요구:
1. 먼저 AGENTS.md, docs/codex/documentation-index.md, docs/codex/current-work.md, docs/codex/next-phase.md, docs/codex/surface-contract.md, docs/codex/data-quality-checklist.md를 읽어.
2. 현재 candidate_evidence와 observation_summary DTO/API/UI 구조를 확인해.
3. 내부 정렬 기준은 observation_priority 또는 evidence_density처럼 공개 숫자 점수로 보이지 않는 이름을 사용해.
4. v1 public surface에는 숫자 점수/등급을 노출하지 말고, 정렬된 목록과 근거 문장만 보여줘.
5. web-view에는 오늘의 관찰 후보, 우선 확인, 왜 눈에 띄는지, 부족한 정보가 보이게 해.
6. 부족한 데이터가 있으면 숨기지 말고 부족한 정보로 표시해.
7. admin-gui/control surface/secret/DB path/operator-only 상태는 web-view에 노출하지 마.
8. Telegram 발송/스케줄러 변경은 이번 목표에 포함하지 마. 먼저 web-view read-only 표시만 고도화해.

관찰 후보 v1에서 우선 검토할 근거:
- 리포트 집중 기준
- 브로커 폭은 내부 정렬/진단 참고로만 사용하고 public `왜 눈에 띄는지` 알약에는 노출하지 않음
- 목표가 변화
- 외국인/기관 5/10/20/31일 누적 수급
- 수급 전환 지속일
- 거래대금/거래량 증가율
- 20/60일 가격 위치
- 52주 위치
- 업종/테마 동반성
- 제외할 종목 조건

검증:
- rg로 금지 문구가 public web-view/Telegram copy에 새로 생기지 않았는지 확인
- python -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json
- python -m stock_monitor web-view-browser-smoke --date latest --json
- 관련 pytest 최소 실행

최종 보고:
1. 구현한 파일 목록
2. 관찰 후보 추천 v1의 정렬 기준 요약
3. public surface에 표시되는 문구 예시
4. 부족한 정보로 처리한 항목
5. 검증 명령과 결과
6. 메인PC로 넘길 handoff/mini_pc_changes/ 반영 필요 여부
```
