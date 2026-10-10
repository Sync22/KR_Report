# Candidate Evidence

Current candidate-evidence contract, evaluation state, and selected completed implementation records.

## 판단 구조 개선 — 확정 방향 및 착수 준비 (2026-09-19)

상태: **최소 구현 및 저장 사례 검증 완료 / 의도 일부 달성 (2026-09-19)**. 이후 사용자가 1차 구현과 의도 도달 여부 검증을 명시적으로 승인했다. 아래 준비 이력의 구현 대기 문구는 당시 기록이다. 참조 대화: `판단 구조 개선` (`6aae0602-20d0-83ee-956f-dc46cf694958`).

DTO update (`2026-09-27`): public candidate and nested daily projections now omit `value_profile.sort_value_signal`; Toss-backed date/scope labels use Toss names. Focused tests cover both response paths. Representative-date content and responsive UI QA remain under `TODO2-WV-CONTENT-QA`.

### 1차 구현 및 실제 판정 (2026-09-19)

운영 자료 검증 예약(사용자 확정 2026-09-19): 추석 전 **9/21·9/22·9/23 3영업일**, 매일 **16:40/20:40 KST**, 총 6회로 확정했다. 기존 5영업일 제안은 이 일정으로 대체한다. Codex heartbeat `top2-3`를 ACTIVE로 등록하고 저장 설정을 확인했다. 정규장 Top2와 실제 장후 재평가 대상의 원문/검토용 설명을 로컬 운영 평가 산출물로 비교한다. 공개 화면·Telegram 발송이나 순위 변경을 배포한 것은 아니다. 기존 운영 수집 시간은 유지한다. 최종 판단은 9/23 장후, 누락은 공개하고 자동 연장하지 않는다. 예약 등록은 실제 검증 실행 완료가 아니다.

추가 표본/운영 연결 판정(2026-09-19, v1.2): 이전 기간의 잔여 기사는 재인용이 많아 9/7~9/11 저장 자료에서 미사용 15개를 골랐다. `tests/fixtures/evidence_review_holdout.json`에 분류 전 기대값과 원문을 고정했다. 새 URL이어도 사건 독립성을 의미하지 않으며 같은 사건 재보도와 기존 엔진 증설 사건의 중첩 가능성이 있다. Codex 수동 라벨, 요약 구간 비교라는 제한은 이전 평가와 같다. ‘holdout’은 이번 수정 전만 해당하고, 결과를 보고 수정한 이후에는 개발 표본이다.

| 추가 15개 결과 | 기존 v1.1 | 한 유형 보정 v1.2 |
| --- | --- | --- |
| 기대 방향 일치 | 1 | 3 |
| 오탐 사례 | 3 | 1 |
| 기대 방향 누락 사례 | 13 | 12 |
| UNKNOWN만 남은 사례 | 10 | 10 |

조치 범위는 **성장 표현에 붙은 둔화/주춤/눈높이 저하** 하나다. 같은 구간의 ‘성장’을 SUPPORT로 오인하지 않고 악화 단서를 RISK로 표시한다. 별도 해외 성장 주장은 보존하며 ‘성장 둔화는 없었다’는 위험으로 승격하지 않는다. H05/H07의 잘못된 긍정 방향이 교정됐다. H06은 위험이 복원됐지만 할인점 개선의 긍정 해석은 놓쳐 여전히 불일치다. H14의 과거 상향→현재 하향 오인은 별개 유형으로 남겼다. 계약/증설/실패 등의 단어 사전을 추가 확장하지 않았다.

검증: 모델 테스트 33개 통과. 기존 20개 재실행은 일치 11/20, 오탐 0, 누락 9로 유지. 결과 `.tmp_evidence_holdout/before.json`, `after.json`, `original20.json`, `comparison.md`. 실행은 기존 평가 도구에 `--sample tests/fixtures/evidence_review_holdout.json`을 지정한다. 오탐/누락 사례는 서로 중복될 수 있다.

**운영 연결 권고: 보류.** 확인된 역방향 오류 감소는 유의미하지만 새 표본에서 전체 해석이 일반화되지 않았다. 3/15 일치는 자동 지지/위험 설명을 신뢰할 근거가 아니다. 새 표본 UNKNOWN 10개 중 기대 방향 없음은 1개뿐이므로 9개는 해석 실패다. 다음 결정은 정규식을 더 늘리기보다 원문 묶음만 운영 설명에 연결할지, 의미 해석 방식을 별도 소규모 비교할지 선택하는 것이다. 이번 작업에서는 어느 운영 경로에도 연결하지 않았다.

20개 표본 평가 후속(2026-09-19): 9/14~9/18 저장 기사/요약의 중복 제거 버전 38개에서 20개를 목적 표집했다. `tests/fixtures/evidence_review_sample.json`에 원문 요약·제목·종목·URL·입력 ID·유형·기대 SUPPORT/RISK를 고정했다. 기대값은 분류 실행 전에 Codex가 문맥을 읽고 작성했으며 독립 평가자 검수나 원문 사실 검증은 아니다. 같은 사건의 기사도 포함되므로 20개 독립 사건 표본이 아니다.

평가는 `scripts/lab/evaluate_evidence_sample.py --output <local-json>`로 재실행한다. 개별 기사 변환 함수에 제목 문맥을 주고 summary의 방향 집합만 검사한다. 전체 후보 선정/종목 목록 문맥 결합에 대한 end-to-end 평가가 아니다. UNKNOWN을 기대 방향의 대체 정답으로 인정하지 않고 오탐/누락을 별도 집계한다. 기대 방향 없는 계열사·인사·구독 안내 3개도 포함했다.

| 20개 표본 결과 | 수정 전 v1 | 수정 후 v1.1 |
| --- | --- | --- |
| 기대 방향 집합 일치 | 9 | 11 |
| 기대 방향 누락 사례 | 11 | 9 |
| 불필요한 방향 추가 사례 | 0 | 0 |
| 방향 없이 UNKNOWN만 남은 사례 | 9 | 9 |

확인된 반복 문제 중 **기존 완화 표현 사이의 조사** 한 유형만 수정했다. E06 ‘우려가 과도’, E08 ‘영향은 제한’의 SUPPORT가 기존 RISK와 함께 복원됐다. 추가한 부정 표현 검사에서는 ‘영향은 제한적이지 않다’를 SUPPORT로 승격하지 않았다. 새로운 의미 모델/사전 확대/운영 연결은 하지 않았다. 모델 회귀 28개 통과.

판정: 작은 수정의 표본 내 개선은 확인됐지만 9/20의 누락이 남아 해석 품질 합격으로 보지 않는다. UNKNOWN만 남은 9개 중 3개는 기대 방향 없음이며 나머지 6개는 해석 실패다. 수주·사업 기여도 같은 간접 호재, 대용 표현, 안전성 부정 설명이 여전히 누락된다. 오탐 0건은 작은 목적 표본의 관측값이지 일반 오탐률 0%가 아니다. 같은 표본으로 수정했으므로 별도 미사용 표본 검증은 남아 있다. 상세 20행 비교는 로컬 `.tmp_evidence_eval/comparison.md`, 전후 결과는 `before.json`/`after.json`이다. 추가 기능 확장 없이 여기서 이번 평가를 종료했다.

후속 보완(2026-09-19, `evidence-review-v1-context`): 종목 문맥을 이어받는 작은 변환만 추가했다. 제목의 종목/저장 alias 및 종목별 리포트 문맥을 다음 문장에 이어 주어 생략·‘동사’ 표현을 허용한다. 생략부호/기사 구분 뒤에는 문맥을 끊고, 현재 입력에서 이름이 확인된 다른 종목의 문장이나 복수 종목 비교는 귀속 미확인으로 남긴다. Top2 검색으로 공통 종목 문맥 목록이 바뀌지 않도록 공통/검색 각각에서 처리한다. 새로운 모델·수집·순위·운영 연결은 추가하지 않았다.

문구를 인정하지 못해도 내용을 버리지 않는다. 모든 미분류 구간을 UNKNOWN 원문과 사유로 보존하고, `direct/context/mixed/unresolved` 귀속 정보를 표시한다. ‘손실은 없다’는 위험 확정 대신 부정 표현 확인 대상으로 남긴다. 실제 자료에서 놓쳤던 ‘임상 부분 보류’, ‘임상 2·3상이 부분 보류’는 제한된 구문 변형으로 포착한다. 단어 사전을 광범위하게 늘리거나 모든 암시적 의미를 해석하는 시스템은 만들지 않았다.

검증: 모델 테스트 25개 통과(기존 13개+문맥/표현 관련 12개). 주어 생략/‘동사’/연속 문장 유지, 생략 뒤 종목 재등장, 알려진 다른 종목/복수 주체 보류, 미분류 우회 표현 보존, 부정 표현, 임상 보류 변형을 검사했다. 실제 9/15 입력 141행과 9/18 입력 70행을 재실행해 입력 제외 0건을 확인했다. 9/18 ‘성능 하락폭’은 UNKNOWN(subject_unresolved)으로 바뀌었고 9/15 임상 보류의 지지/위험 병존은 유지된다. 결과는 `.tmp_evidence_context/<date>/review.json`, `review.md`에 별도로 저장했다.

후속 판정: 확인된 오탐은 줄였고 종목명을 반복하지 않는 문맥을 보존했다. 그러나 알려지지 않은 회사로의 매끄러운 주제 전환, 긴 거리의 대명사 연결, 새로운 비유/우회 표현의 방향은 아직 자동 판별하지 못한다. 특히 ‘고객사 주문이 밀려 생산라인을 더 돌린다’ 같은 표현은 내용을 보존하지만 SUPPORT로 해석하지 못하는 한계가 테스트로 드러난다. 따라서 **내용 누락 방지는 보완됐지만 단어 해석 편향 자체가 해결됐다고 판정하지 않는다.** UNKNOWN 증가를 정확도 향상으로 세지 않으며, 운영 판단에 사용하지 않는다.

- 구현: `src/stock_monitor/news/evidence_review.py`. 읽기 전용 SQLite snapshot에서 reports/news/저장 수급을 읽어 JSON/Markdown 설명 비교를 생성한다. 입력 ID·내용 해시·관측 시각·구현 해시를 기록한다. 일자 최종 저장 자료를 읽으므로 과거 장중 순위 재현이 아니다.
- 기존 정규장 성공 poll-news 이벤트의 대상 코드를 검색 보충 대상으로 기록한다. 이것은 OLD 후보 존재 확인/fallback까지 재실행한 선정 결과가 아니다. NEW 순위는 구현하지 않았고, 전체 OLD/NEW 순위 비교는 미측정이다.
- 공통 근거에서 top2_search를 먼저 제외한다. 검색은 기록된 선정 종목의 설명에만 별도 추가한다. URL 동일성은 기사 중복, 동일 제목은 날짜 내 미확인 관계로만 묶는다. 검토자가 사건 ID·날짜·관계 근거를 명시한 입력만 사건 묶음으로 병합한다. 독립 근거로 자동 승격하지 않는다.
- SUPPORT/RISK/UNKNOWN은 제목·요약의 문자열 단서다. 부정 표현·다른 회사 언급을 의미적으로 해석하지 못한다. 미분류 자료도 혼합 묶음 안에서 UNKNOWN으로 남기며, 계보 unknown과 구분하고 감점하지 않는다.
- 실행: `.venv\Scripts\python.exe -m stock_monitor.news.evidence_review --db data/stock_monitor.db --date 2026-09-15 --output .tmp_evidence_review/2026-09-15` (9/18도 동일하게 실행). 결과는 로컬 `.tmp_evidence_review/<date>/review.json`, `review.md`; 운영 DB/Telegram/웹뷰에 연결하지 않았다.

| 실제 저장 사례 | 확인 결과 | 의도 판정 |
| --- | --- | --- |
| 9/15 HD현대중공업 329180 | 공통 12행→6묶음, 검색 17행→1기사. 파업/주가 하락 기사와 실적 기대 자료를 함께 볼 수 있음 | 반복 저장을 추가 확신으로 오인하지 않게 정리하는 효과 있음 |
| 9/15 SK바이오팜 326030 | 공통 14행→6묶음, 검색 66행→17기사. iM증권 리포트 69610와 이를 설명한 두 기사(저장 3행)를 수동 관계 검토 후 4행→1사건으로 병합 | 낙관적 해석과 임상 보류를 함께 보존. 임상 보류 해제/추가자료 확인 여부라는 질문을 도출할 수 있음 |
| 9/18 롯데이노베이트 286940 | 공통 3행→3묶음, 검색 16행→1기사. 요약의 다른 내용인 ‘성능 하락폭’을 RISK로 검출 | 자동 방향 추출 오탐. 유용한 반론 추출 성공으로 세지 않음 |
| 9/18 지엔씨에너지 119850 | 공통 3행→3묶음, 검색 보충 없음 | 설명 확장 개선 미입증. 자료 없음은 부정 근거가 아님 |

수동 사건 예제는 `.tmp_evidence_review/2026-09-15/reviewed-event.json` 및 `.md`에 별도 저장했다. 관계 근거는 같은 날짜의 iM증권 오파칼림 해석과 명시적 인용이며, 임상 사실을 독립 검증했다는 뜻이 아니다. 기본 실행이 이 사건을 자동 인식한 것으로 평가하지 않는다. 리포트는 Naver Research company page, 뉴스는 Naver `014/0005575753`, `001/0016310437`에서 확인했다. 정확한 URL/입력 ID는 로컬 산출물에 보존했다.

**판정:** 1차 구현으로 중복과 상반된 관점을 함께 검토하는 방식의 효용은 일부 확인했다. 다만 자동 사건 인식과 의미 기반 반론 추출은 합격하지 않았으며 운영 순위 변경 근거도 없다. 네 설명 중 두 사례에서 정리 효용을 확인했지만 소표본 관찰이므로 일반 합격률이나 정확도로 확대 해석하지 않는다. 자동화 확대보다 실제 종목에 해당하는 주장인지 구분하는 문제가 다음 판단 대상이다. 이 기록은 과거 결과이며 이후 설명 검토에 80% 보편 합격선을 요구하지 않는다.

검증: 신규 모델 13개, scheduled guard/news 관련 23개, 기존 알림/linked-evidence 회귀 25개로 총 61개 통과. 같은 사건 2리포트+3뉴스, 다른 사건, 혼합 방향과 미분류 보존, Top2 격리, cutoff 차단, 입력 DB 불변 및 OLD 수급 조건을 검사했다. OLD sort_signal은 수급 지속만 4, 목표가 상승+수급 3, 하락+수급 2, 리포트 집중+수급 1로 고정 확인했다. 두 번째 +2는 삭제하지 않았다. 임시 경로 권한 문제는 새 workspace 임시 경로를 지정해 해결했다.

운영 조사/보정: 9/18 event 6524의 16:30:02.516073 실행이 종료 시각 16:30:00보다 늦어 skip됨을 재현했다. `_run_scheduled_poll`의 시간 비교만 분 단위로 맞춰 16:30분대 허용, 08:29/16:31 차단을 검증했다. 스케줄러/서비스 재등록이나 실제 수집 실행은 하지 않았다. Toss event 6526의 partial은 403810 아이엘로보틱스 종가·양쪽 수급 누락, 456010 아이씨티케이 양쪽 수급 누락으로 정확히 설명된다. 공급자 데이터 부재와 삼켜진 요청 오류는 현 저장 자료만으로 구별되지 않아 원인 해결로 표시하지 않는다. 시장 브리핑은 활성화하지 않았다.

목표는 관찰 후보를 압축하고, 근거의 관계·반대 근거·미확인 사항으로 사용자의 생각을 확장하는 것이다. 추가 소스나 기사 수 확대보다 운영 누락 원인 정리와 판단 설명 개선을 우선한다. 기존 Top2 검색의 목적 달성은 유지한다.

사용자 우선순위 보충(검수 후 Git 저장 요청): 이후 1차 구현은 기능적 완성도나 전체 단계 완주보다 **의도한 바에 도달하는지 확인하는 최소 구현**에 초점을 둔다. 실제 저장 사례에서 기존 설명과 근거 묶음 설명을 나란히 보고, 중복 기여가 드러나는지·반대 근거와 미확인이 보존되는지·새 확인 관점이 생기는지를 먼저 판단한다. 초기 결과가 유용하지 않으면 기능을 늘려 보완하지 않고 원인과 다음 선택을 제시한다. 이 설명 검토는 저장 사례로 바로 시작할 수 있으며, 더 넓은 표본은 향후 순위 정책이나 운영 확대를 검토할 때 보충한다. 소수 사례는 일반 품질이나 순위 개선의 근거로 확대 해석하지 않는다.

### 확정 계약

- 기존 선정 알고리즘과 정규장 Top2를 OLD 기준선으로 보존한다. 현재 Git 기준은 `da9a467a`이며 실제 착수 시 HEAD와 입력 계약을 다시 확인한다. NEW는 별도 로컬 비교 결과로 시작하며 운영 순위를 교체하지 않는다.
- OLD는 점수 함수만이 아니라 현재 선정 절차 전체다. 해당일 성공 `poll-news` 이벤트의 `target_stock_codes` 최대 2개 중 현재 후보에 존재하는 행을 우선하고, 유효한 정규장 행이 없으면 저장 근거 정렬의 eligible 최대 2개로 fallback한다. 순위 산술 비교와 이 cohort 보존 절차는 별도 결과로 기록한다. Top2는 최대 개수이며 후보가 0/1개면 억지로 채우지 않는다.
- 동일 사건의 재인용 자료는 Evidence Cluster로 묶되, 주제가 같다는 이유만으로 서로 다른 계약·발표를 합치지 않는다. 매칭이 불명확하면 억지로 병합하지 않고 미확인 관계로 남긴다.
- **기사 URL의 신규성, 사건 묶음의 구분, 근거의 독립성은 서로 다르다.** 9월 검색 평가의 26건은 고유 기사이고 계보는 unknown 19 / report_recap 7 / independent 0이었다. 참조 프롬프트의 ‘독립 기사 확보’는 ‘기존 수집 밖 참고 기사 확보’로 정정한다.
- SUPPORT / RISK / UNKNOWN을 별도로 보존한다. 같은 사건 안에도 지지·반대 주장이 공존할 수 있으므로 cluster에 단일 방향을 강제하지 않는다. 정보 부족 UNKNOWN과 출처 독립성 미확인은 별도 속성이다.
- 출처 종류와 계보, 근거 ID, 사건/주제 식별, 종목, 사건일·게시일·수집시각, 병합 사유, 검증 상태, 기존 관점 대비 신규성을 추적한다. 신뢰도·독립성은 근거 없이 숫자로 추정하지 않는다.
- Top2 추가 검색은 확인·반론·질문 확장용이다. 기사 수와 선택된 종목만 받은 추가 검색 정보는 공통 후보 순위 가산에 사용하지 않는다.
- NEW의 공통 후보 생성·eligibility·cluster 수·SUPPORT/RISK 존재 여부·정렬 feature를 만들기 **전에** `source_lane=top2_search`를 제외한다. 제외된 자료는 OLD가 선택한 Top2 설명에만 후결합한다. 단순 건수 비가산만으로 편향이 차단됐다고 주장하지 않는다. OLD에 같은 필터를 소급 적용해 기준선을 바꾸지는 않는다.
- 임의의 30/40/30 비율 모델, 공개 점수, 자동매매, 전체 CLI 재작성, 새 공급자·검색량 확대는 이번 단계에 포함하지 않는다.

### 최소 착수 순서와 산출물

| 단계 | 조사/구현 범위 | 검증 및 종료 조건 |
| --- | --- | --- |
| A 운영 원인 정리 | 16:30 경계, 9/18 Toss 후보 18개 중 2개 누락, success/partial/skipped 의미 추적 | 경계 직전/정각/직후 재현; 부분 수집을 완료로 위장하지 않고 누락 원인과 회복 가능성 기록 |
| B 근거 모델 | 기존 reports / linked news / 저장 수급을 읽는 순수 변환부터 설계 | 동일 사건 재보도와 서로 다른 사건 구분, 혼합 방향 보존, UNKNOWN 비감점 |
| C 최소 NEW | 수급 가산을 근거 축별로 설명하고, 확인된 중복 기여만 제거할 비교안을 별도 제안 | OLD 조건별 기여를 먼저 고정; 두 번째 +2 일괄 삭제 금지; 순위 규칙 선택 전에는 설명 비교만 |
| D 동시점 비교 | 같은 입력으로 OLD/NEW 후보·이유·차이 저장 | cutoff 이후 기사·20:00 수급의 장중 유입 금지, 입력 ID/버전/시각 기록, Top2 편향 방지 |
| E 관찰 판단 | 저장된 대표 사례부터 검토; 순위 정책 검토 시에만 여러 영업일 표본을 보충 | 사례별 효용·오류·미확인을 기록; 순위 반영은 별도 결정, 자동 승격 없음 |

삽입 위치는 기존 수집·저장 이후, candidate read-model 생성과 operator 비교 출력 사이로 잡는다. 소스 후보는 `cli.py`의 `_web_view_observation_candidate_profile`, `_web_view_candidate_value_profile`, `build_web_view_candidate_evidence_snapshot` 및 기존 `news/linked_evidence.py`다. 초기에는 운영 schema/API 변경 없이 읽기 전용 입력과 로컬 JSON/Markdown 결과를 우선한다. 필요한 함수만 추출하고 모듈을 미리 여러 개 만들지 않는다. 웹뷰 설명 연결은 로컬 비교 결과 확인 뒤 별도 단계다.

OLD/NEW는 같은 날짜뿐 아니라 같은 관측 cutoff와 후보 universe를 사용한다. 장중/장후를 별도 비교하고, 이미 선택된 Top2만 보강된 검색 자료는 설명 평가에만 사용한다. 이 제약 아래 NEW 순위 규칙을 명시할 수 없다면 설명 비교까지만 시행하고 순위 개선을 주장하지 않는다.

현재 `build_web_view_candidate_evidence_snapshot(..., now=...)`는 과거 as-of 입력을 재구성하는 API가 아니다. `now`만 과거로 지정해도 해당일 최종 저장 행이 차단되지 않는다. 순위 비교는 당시 존재했다고 증명 가능한 고정 입력이 있을 때만 시행한다. 각 run에 `input_as_of`, 입력 ID·내용/버전 식별값, 게시·수집·저장시각 및 사용한 선정 이벤트를 기록하고 OLD/NEW가 같은 입력을 읽게 한다. cutoff 이후 정보가 섞인 run은 무효다. 일자별 최종 집계나 덮어쓴 행의 과거 버전을 입증할 수 없으면 그 날짜는 장중 순위 비교에서 제외하고 설명 구조 비교로 구분한다. 20:00 종가는 같은 날짜 정규장 비교에 사용하지 않는다.

### 코드 대조 후 보완한 계약

- OLD 수급 산술: `(수급 지속 and 당일 수급)`은 `priority_signal +2`; 별도로 `(당일 수급 and 리포트 집중 외 why_notable 존재)`는 `sort_signal +2`다. 수급 지속 자체가 why_notable에 포함되므로 두 조건이 함께 성립할 수 있지만, 목표가 변화와 당일 수급만으로도 두 번째 조건이 성립한다. 이 중 어느 조합을 중복 기여로 볼지는 사례로 확인하며 정책 변경은 아직 확정하지 않는다.
- OLD gold 사례는 ① 수급 지속+당일 수급(그 외 근거 없음), ② 목표가 변화+당일 수급(지속 없음; 상승/하락 구분), ③ 리포트 집중+당일 수급(다른 근거 없음)으로 잡는다. `priority_signal`, `sort_signal`, 설명 밀도, 최종 정렬/선정 기여를 구분한다.
- 현재 `_web_view_candidate_value_profile`은 뉴스에 따라 표시 상태를 바꾸지만 `sort_value_signal=base_signal`을 유지한다. 뉴스가 +2/+2의 직접 발생원이라는 참조 예시는 현재 코드와 다르다. 뉴스의 후보 자격 영향 등 다른 경로는 별도 추적한다.
- 최소 모델은 사건 관계(same_event/different_event/unresolved), 주장 방향(SUPPORT/RISK/UNKNOWN), 기존 계보(independent/report_recap/unknown), 검증 상태를 분리한다. 명칭은 구현 시 기존 타입과 맞춘다. 출처 계보가 unknown인 SUPPORT 주장도 보존할 수 있지만 독립 사실로 승격하지 않는다. 검증 상태에는 확인 대상과 근거를 연결하고 제목 매칭 확인을 사건 사실 검증으로 표현하지 않는다.
- 사건 병합은 종목·구체적 사건 식별·시점·명시적 재인용 관계를 우선한다. URL 일치는 동일 기사 식별에 사용하고 광범위한 주제 일치는 자동 병합 근거로 쓰지 않는다. 확신할 식별 정보가 부족하면 unresolved로 둔다. 임베딩/LLM 군집화는 초기 범위에서 제외한다.

### 비례적인 평가 기준

- 결정적 회귀 사례: 같은 사건 2리포트+3뉴스 중복 기여 억제, 다른 사건 보존, SUPPORT/RISK 비상쇄, UNKNOWN 비감점, Top2 검색 건수 비가산, 기존 선정·저장·GET-only 경계 유지.
- 같은 공통 입력에 top2_search 행을 추가/제거해도 NEW의 후보 자격과 순위는 불변이어야 한다. 설명 payload만 달라질 수 있다. eligible 0/1개, SUPPORT 2개+RISK 1개 양쪽 보존, 동일 cutoff 이후 입력 차단도 검사한다.
- 수동 검토는 이미 저장된 대표 사례부터 시작한다. 각 설명을 `유용`, `중립`, `오해 소지`, `평가 불가`로 분류하고 원문 근거와 새 관점/반론 여부를 짧게 적는다. 일정 기간이나 비율은 설명 검토의 보편적 통과선으로 사용하지 않는다.
- 순위 정책 변경이나 운영 확대를 고려할 때는 여러 날짜와 종목의 표본을 추가하고 실제 분모·중복 사건·원문 검증 한계를 함께 공개한다. 잘못된 종목 귀속, 미확인 자료의 독립 승격, cutoff 이후 입력은 해당 비교의 중단 사유다. 소표본 비율만으로 일반 정확도를 주장하지 않는다.
- 잘못된 사건 병합으로 설명을 왜곡하거나, 미확인 자료를 독립 근거로 승격하거나, 미래 자료를 사용한 비교는 통과 처리하지 않는다. 오류를 고친 범위만 재검증한다.
- 후보 변경은 모두 사유를 추적 가능하게 하고, 표본 부족/차이 없음은 미측정 또는 개선 미입증으로 기록한다. 주가 수익률은 이번 합격 기준이 아니다.
- 실제 검증 시작일과 예약은 구현·오프라인 검사 완료 후 확정한다. 지금은 자동 검증을 등록하지 않는다.

### 남은 선택과 다음 착수 지시

시장 브리핑 09:15/12:00/15:15는 최근 수동 검토 발송 0/3으로 차단된 상태다. 사용할지 결정되기 전에는 활성화하거나 검토 요건을 우회하지 않는다. 이 결정은 A의 다른 원인 조사와 B 설계를 막지 않는다.

이번 재검수의 추천 착수 단위는 **A 원인 재현 + OLD 입력/기여 기록 + 근거 묶음 순수 변환/설명 비교**까지다. 사용자는 이후 진행 여부를 판단한다. NEW 순위 변경 규칙(두 번째 +2 처리 포함)은 OLD 사례를 본 뒤 정하고, 실제 관찰 실행은 입력 시점 재현 가능성과 오프라인 검사 후 결정한다. 이로써 설명 구조 작업을 위해 순위 정책까지 미리 확정할 필요가 없다.

검수 출처: 2026-09-19 기존 ChatGPT 협업 대화 `6a9b8669-9e4c-83e8-aa40-f991fd21e97d`, task `c2c_review_0919`. ChatGPT가 연결된 workspace/HEAD와 문서 diff, 현재 후보 함수를 읽어 제시한 네 가지 핵심 보완 및 OLD/최대 2개 정의를 Codex가 코드 대조 후 반영했다. 이는 준비 문서 검수이며 운영 품질 검증이나 구현 완료 판정이 아니다.

수정본 재검수: 같은 task의 iteration 1에서 ChatGPT가 문서와 diff를 다시 읽고 `DONE — preparation review sufficient / implementation not authorized`로 판정했다. 남은 수급 보너스/NEW 순위 정책은 의도적으로 미확정이며, 준비 문서의 중대한 결함으로 보지 않았다. Codex의 `git diff --check`도 통과했다. 사용자의 이후 진행 판단을 기다리는 상태다.

다음 구현 지시가 오면: 현 상태 확인 → A 재현과 최소 보정 → B/C 결정적 로컬 모델 및 검사 → D 비교 산출물 → E 실제 일정 확정 순서로 진행한다. 운영 데이터 쓰기·서비스/예약 변경·외부 발송은 당시 승인 범위에 맞춘다. 이번 준비 작업에서는 구현과 배포를 시작하지 않았다.

## Current Evidence Ownership (2026-09-27)

- Naver daily summaries seed candidate rows. Toss 20:00 stored snapshots own current market, ETF, and flow references.
- The close capture requests quote/flow references for every valid daily-summary candidate in batches of at most two symbols. The public priority projection remains Top2; capture coverage and displayed priority count are separate.
- A candidate close reference is complete only when its stored close baseline and required foreigner/institution flow values are present. Overall capture health also depends on indices, market flow, Top20 classification, and source metadata; those checks are tracked in `TODO2-DATA-FRESHNESS-LIVE`.
- Live Top2 quote/flow lookups are separate, timestamped context and do not rewrite the stored 20:00 baseline or change the report-derived Top2 cohort.
- Existing KRX stock/index/flow rows support historical review only. They do not fill missing current Toss values or count as a current candidate gap. Historical event reaction is labeled `과거 반응(KRX)` and never changes current ordering.
- Public DTO projection now removes the internal numeric sort key and labels current Toss references accurately. Remaining multi-date/content QA is tracked in `TODO2-WV-CONTENT-QA`.
- Older CE-1 sections below remain design history where they describe KRX as a current selected-date source or Top2 as the persistence universe; do not use them as current source instructions.

## Top2 Weight And News Scope — User Decision (2026-09-29)

Status: **the user selected A for both items; current selector and news behavior remain unchanged**.

- The current selector is implemented in `cli.py`; it is not a document-only design. Candidates require at least two reports, a matched-news record, or stored stock flow, then sort by fixed internal signals, evidence density, report count, broker count, and stored turnover. The public result remains at most two rows.
- The signal constants are hardcoded in Python, not managed through operator settings. The current source applies `+2` for persistent flow with stock flow, `+1` for upward target revision, `+1` for at least two reports, and a separate `+2` stock-flow condition. `sort_value_signal` currently mirrors `sort_signal`; neither is a news-derived numeric value. Tests protect the current baseline, but do not validate that the weights improve later outcomes.
- Scheduled news collection targets the selected Top2. Saved news may satisfy candidate eligibility and change evidence labels; it does not add a continuous score. In a regular session, the latest successful `poll-news` cohort is preferred while those symbols remain candidates.
- Top2 news is a two-stock, candidate-biased sample. It can explain those candidates, but does not establish market-wide sector attention. The main sector/theme rollups come from report categories, not an aggregation of Top2 news.
- The earlier 180-minute intraday chart was removed. The Main Top2 chart/indicator panel uses adjusted daily candles ending on the selected business date, with 50/100/200-trading-day display windows (default 200) and month boundaries; RSI 14 is initially selected. It shows factual SMA overlays and one selected supplementary indicator without changing candidate eligibility/order or news weighting; see [Toss OpenAPI Lab](toss-openapi-lab.md).

### Selected A/B options

#### Top2 weighting policy

| Choice | Direction | Benefit | Cost / limitation | State |
|---|---|---|---|---|
| **A — selected** | Keep the current fixed heuristic as the baseline; compare its selections across representative dates before any later weight change. | Preserves explainability and gives a measured baseline without adding settings. | Weights stay hardcoded; evaluation takes multiple dates and outcomes. | Selected by user; formula unchanged. |
| **B** | Make weights operator-configurable now. | Makes later tuning easier and allows controlled operator experiments. | Adds a settings surface and rollback burden before evidence shows which signals help; increases overfit risk. | Not selected. |

#### News scope

| Choice | Direction | Benefit | Cost / limitation | State |
|---|---|---|---|---|
| **A — selected** | Keep news as candidate-level Top2 evidence only; do not infer market-wide sector attention or add numeric news weights. | Matches the bounded collector and current source/lineage confidence. | Cannot answer which sector has the broadest market attention. | Selected by user; behavior unchanged. |
| **B** | Add a broader news universe, sector mapping, independent-source/recap lineage rules, and an explicit comparison denominator before making sector-level summaries. | Could support a defensible sector-attention view if coverage and classification are reliable. | Requires broader collection, taxonomy maintenance, coverage QA, and bias controls; two Top2 stocks alone are insufficient. | Not selected. |

The selected A options confirm existing behavior. They do not approve a ranking formula change, new scoring surface, or wider news collector. The daily chart remains factual price/volume context only.

## Included sections
- Candidate Evidence Contract
- Candidate Evidence Plan
- Candidate Evidence Batching (completed record)
- Target Price Progress Plan
- Operator Memo Progress (completed record)
- Operator Memo Surface Reflection (completed record)

<!-- Merged from: docs/codex/candidate-evidence.md -->
## Candidate Evidence Contract

## Purpose

This document fixes the first implementable read-only `candidate_evidence` DTO boundary and the first rotation image alias-mapping step.

It approves observation-candidate evidence and future observation-candidate recommendation, but it does not approve public numeric scoring, investment ranking weights, trading recommendations, or final ETF/stock picks.

Use this when changing the computed `관찰 후보 근거` API/DTO or planning its future UI.

## Source And Persistence Boundary

The candidate DTO is computed from existing report and market records. It does not fetch, write, or create a candidate table.

| Layer | Current source | Persistence/query path | Use |
| --- | --- | --- | --- |
| Report summary/detail | Naver Research | `daily_stock_summaries`, `reports` | Candidate seed and report explanation. |
| Stored stock market reference | Toss OpenAPI | `stock_market_daily`, `source="toss_openapi"` | Exact-date stored price/change/volume/turnover. |
| Stored stock flow | Toss OpenAPI | `stock_investor_flow_daily`, `source="toss_openapi"` | Exact-date flow when stored. Close capture covers all valid daily-summary candidates in bounded batches; public priority remains Top2. |
| Current live quote/flow | Toss OpenAPI | Top2 request path | Separate timestamped context; not persisted as the 20:00 baseline and does not alter ordering. |
| Stored market flow | Toss OpenAPI | `market_investor_flow_daily`, Toss market context | Top-level provisional market context. |
| Legacy KRX market/flow/rank | Existing KRX tables | Historical windows only | Retrospective review; not current fallback or candidate completeness. |
| Category / ETF | Dated category snapshots / Toss OpenAPI ETF rows | Existing category and ETF repositories | Separate context; show only when rows exist for requested source/date. |

Future source probes remain outside this DTO and require their own source/failure review before affecting a product surface.
## First Implementable DTO

CE-1 is a read-only snapshot builder, not a new table.

Current builder shape:

```text
build_web_view_candidate_evidence_snapshot(config, repository, business_date, limit=20) -> dict
```

| Field | Current contract |
| --- | --- |
| `surface`, `read_only`, `business_date`, `available`, `scoring`, `notice` | Fixed read-only web-view metadata; `scoring=false`. |
| `data_scope` | Current literal is `stored_report_toss_evidence`: Naver report summaries with current stored Toss market references. Historical KRX evidence remains a separate retrospective layer. |
| `market_flow_context` | Toss market-level flow stored for the requested date; provisional values retain provider time. |
| `market_reference.*` | Exact-date `stock_market_daily` rows with source `toss_openapi`; missing Toss rows remain missing, with no KRX fallback. |
| `stock_flow_reference.*` | Exact-date Toss stock-flow rows when stored; preserve source date and units. |
| `rank_reference` | Historical/operator context only. Current public projection omits it; do not expose it without a separate DTO decision. |
| `why_notable`, `missing_information`, `evidence_layers.*` | Compact source-backed public labels; no internal sort vocabulary. |
| `value_profile` | Public-safe observation state based on report/news and current Toss references. Historical KRX reaction stays in a separately labeled review surface. |
| `intraday_reference` | Top2-only live reference, source timestamped and separate from stored 20:00 rows. |
| `quality_flags`, `evidence_notes` | Internal/readiness diagnostics only; never rely on frontend filtering to keep them private. |

## Internal Sort And Operator Diagnostics

- Keep internal sort values and operator diagnostics separate from public labels. Remove `value_profile.sort_value_signal` from every public response while preserving internal selection behavior.
- Classify candidate evidence as report/news/Toss-backed rank-driving evidence, context-only support, or missing context before it can affect public ordering.
- Stored Toss market/flow may support the displayed observation rationale when its date/source label is visible. Historical KRX price/flow/rank context is retrospective only and must not drive current ordering.
- Missing Toss values are visible gaps, not negative stock evidence. Missing KRX history is not a current candidate gap.
- Historical `[12010]` rank rows are operator/historical context, not current public candidate fields and not ranking inputs.
- News evidence may affect observation emphasis only through public-safe labels/counts. A completed collection with no matched article remains `매칭 뉴스 없음`.
- Readiness commands may report internal signal counts separately from public label counts. Legacy diagnostics named `missing_krx_reference` or `rank_without_stock_flow` are not current Toss-completeness rules and should be renamed or explicitly scoped as historical.

## Exact Repository Fields To Use

CE-1 uses current summary/report rows and source-filtered Toss market rows. Check repository implementation before changing field ownership.

- Seed rows: `repository.list_daily_summaries(business_date)`; use business date, stock code/name, mention count, broker display, target range, and dominant opinion.
- Report detail: `repository.list_reports_for_business_date(business_date)`; use broker, target/opinion, publication time, and source URL for explanation/detail only. `daily_stock_summaries` remains the aggregate owner.
- Stored stock market: `repository.list_stock_market_daily_for_codes(business_date, stock_codes, source="toss_openapi")`; missing exact-date Toss rows remain nullable and do not fall back to KRX.
- Stored stock flow: read `stock_investor_flow_daily` for the requested date and `source="toss_openapi"`; preserve investor type, net-buy volume/amount, and source units.
- Market flow: read `market_investor_flow_daily` from Toss and keep it in top-level `market_flow_context`, not repeated on each stock.
- Historical `[12009]`/`[12010]` rows belong to retrospective or operator review only; they are not current candidate ranking inputs or public DTO fields.

## CE-1 Exclusion And Quality Rules

| Rule | Meaning |
| --- | --- |
| Missing stock code | Exclude the row because it has no stable identity. |
| Missing target/opinion | Preserve detail visibility; do not add a positive evidence label. |
| Missing exact-date Toss market/flow rows | Keep fields nullable, mark the Toss gap, and do not substitute KRX history. |
| Missing historical KRX context | It is a history-coverage note, not a current observation-candidate defect. |
| Category fallback | Keep category context separate; never attach current taxonomy silently to an older date. |
| Internal score/sort diagnostics | Exclude them from public DTOs; projection cleanup must not alter internal ordering. |
## Why Category Is Not In The First Stock Row

Current repository coverage is strong for:

- date-aware category rollups
- category detail by category name/display name

Current repository coverage is not yet direct for:

- one stock -> one dated sector display lookup row for CE-1

Because snapshot semantics matter, CE-1 should not reach back to current `stock_metadata.sector_name` as a shortcut.

Safe rule:

1. Keep stock `candidate_evidence` rows category-free in CE-1.
2. Keep category/rotation as a separate descriptive layer.
3. Add a dedicated read-only repository helper for dated stock->category membership later if needed.

## First Rotation Image Alias-Mapping Step

Current state:

- `data/rotation_overlay_coordinates.json` is keyed by current category `display_name`
- `build_web_view_rotation_overlay_snapshot(...)` matches rollup `display_name` directly to that coordinate key
- the overlay `label` field is display text only, not a canonical join key

The first alias step must therefore be a separate artifact, not a coordinate-file rewrite.

Suggested future artifact:

```text
data/rotation_image_aliases.json
```

Suggested row shape:

| Field | Meaning |
| --- | --- |
| `rotation_label` | Human-reviewed text label from `example/Cycle.jpg` |
| `category_type` | Start with `sector` only |
| `category_display_name` | Current dated rollup/display name to match in repository output |
| `coordinate_display_name` | Existing key in `rotation_overlay_coordinates.json` |
| `mapping_basis` | `manual_alias` |
| `status` | `active`, `unmatched`, or `review_needed` |
| `note` | Optional operator memo |

Guardrails:

- Do not overload `coordinates[].label` as the alias source of truth.
- Do not map directly from image label to ETF code in this step.
- Do not mix theme aliases into the sector overlay until taxonomy coverage is stronger.

## Historical CE-1 Next-Step Draft

This pre-implementation checklist is superseded by the completed CE-1/visible evidence path and the current source contract at the top of this file. It is retained for rationale only; do not use its KRX-current source wording or CE-2 action as a current blocker.

## Migration And Schema Implications

Current recommendation:

- no new SQLite table
- no schema version bump
- no live DB edits

If later work requires a stored artifact, add it through the migration runner only after the runner exists.
Until then, keep:

- `candidate_evidence` as a computed DTO only
- rotation alias mapping as a flat local JSON artifact

## Backtest-Period Guidance

Use two separate review windows.

### DTO/manual review window

Use `2026-05-04` through `2026-05-08` first.

Reason:

- exact-date web-view KRX context is already validated for these dates
- market-flow visibility is already part of the stored read-only paths
- stock-level `[12009]` data exists for observed candidate names during this period

This window is good for row-shape review and missing-data flag review.
It is not good enough for scoring conclusions.

### Future scoring/backtest window

Do not start score or hit-rate backtests on `2026-01-02` through `2026-05-08` as one uniform dataset.

Reason:

- KRX stock/ETF/index snapshots are broad for that period
- stock-level `[12009]` flow coverage is still candidate-selective and manually backfilled
- dated per-stock category membership is not yet exposed as a stable read-only join

Minimum future rule for scoring/backtest:

1. use only a contiguous window with complete daily summary coverage
2. require exact-date KRX stock snapshots for all evaluated dates
3. require explicit coverage rules for `[12009]` stock flow across the evaluated universe
4. keep the first quantitative window at least `40` to `60` Korean business days

Until those conditions are met, treat `2026-04-01` through `2026-05-08` as an offline evidence review window only.

## Future Ownership

Future scoring/backtest work should be owned by:

- `market-data-engineer`: primary owner for feature boundary, source coverage, and no-leakage evidence design
- `sql-pro`: coverage checks, replay-safe dataset extraction, and later migration-runner alignment
- `test-engineer`: fixture windows, regression tests, and backtest harness safety
- `reviewer`: leakage review, trading-recommendation-boundary review, and policy challenge

Secondary roles after the score boundary is approved:

- `python-pro`: scoring/backtest implementation details
- `web-ui-engineer`: read-only score display only after policy approval


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Historical Candidate Evidence Plan (Superseded)

This initial CE-1 staging plan is retained for rationale only. Current source and DTO rules are in `Current Evidence Ownership` and `Candidate Evidence Contract` above; its KRX-as-current fields, stages, and next actions are not pending work.

## Purpose

This document defines the safe path from current report/flow/reference data to future `관찰 후보 추천` views.

It approves observation-candidate recommendation and priority ordering, but it does not approve trading recommendations, public numeric scoring, investment grades, or buy/sell judgment.

The exact CE-1 DTO and alias-mapping contract is fixed in [candidate-evidence.md](candidate-evidence.md).

Current rule:

Use the candidate-specific observation wording in [surface-guide.md](surface-guide.md). This plan does not duplicate the full public wording/access contract; source ownership is defined in `Current Evidence Ownership` above.

## Requested Ideas

| Memo | Intended Outcome | Current Decision |
| --- | --- | --- |
| 리포트와 수급을 통해 다음날 기준 2종목 정도를 추천하고자 한다면 어떤 가중치가 필요한지 | Next-day observation-candidate shortlist | Build `candidate_evidence` first, then expose it as observation-candidate recommendation with no trading-call wording. |
| 순환매 기준 표기가 완성된 이후 해당 순환매쪽 ETF와 종목을 각 1개씩 뽑아낼 수 있는지 | Rotation-linked ETF and stock candidate preview | Build sector/ETF/stock evidence preview first. No final single pick yet. |

## Work That Can Start Now

| Work | Why It Is Safe Now | Output |
| --- | --- | --- |
| Maintain the candidate DTO | CE-1 builder/API and the public `관찰` view exist; changes follow the source contract above. | Focused source/value QA, no new score layer. |
| Review explanation usefulness | Uses saved examples and does not change ranking policy. | Per-case usefulness/error notes in `TODO2-NI-EVAL`. |
| Continue rotation mapping only where needed | Existing alias and ETF maps are operator-managed and source-dated. | Missing mappings stay explicit; no one-pick claim. |

## Work That Must Wait

| Work | Blocker |
| --- | --- |
| Weighted score | Needs enough history and an agreed policy for weights. |
| Public trading recommendation or scored investment decision | Out of scope; observation-candidate recommendation can proceed without this. |
| Rotation ETF/stock one-pick | Needs alias map, ETF mapping, and evidence coverage first. |
| Telegram candidate alert | Needs user-facing preview stability and false-positive review first. |
| Auto buy/sell wording | Out of scope. |

## Candidate Evidence Fields

The following is the original CE-1 field proposal. Where it names KRX as a selected-date/current source, the `Current Evidence Ownership` section above supersedes it.

First pass should produce a read-only row per stock/date.

| Field | Source Layer | Display Rule |
| --- | --- | --- |
| `business_date` | App business date | Required. |
| `stock_code`, `stock_name` | Report summary / KRX stock master | Required. |
| `category_display_name` | Category snapshot | Optional; label fallback if not dated. |
| `report_count` | Naver reports | Count only stored reports. |
| `broker_count` | Naver reports | Count unique brokers. |
| `target_price_range` | Parsed report target prices | Exclude missing values from range. |
| `opinion_summary` | Parsed report opinions | Preserve `의견 없음` as display-only detail. |
| `price_change_percent` | KRX stock daily | Observation only. |
| `turnover` | KRX stock daily | Observation only. |
| `volume` | KRX stock daily | Observation only. |
| `foreign_net`, `institution_net`, `individual_net` | KRX Data Marketplace `[12009]` | Observation only; retain units. |
| `market_flow_context` | KRX Data Marketplace `[12008]` | Market background only. |
| `net_buy_rank_context` | KRX Data Marketplace `[12010]` | Ranking context only. |
| `evidence_notes` | Derived display text | Explain facts without scoring. |

## Exclusion Rules

| Rule | Reason |
| --- | --- |
| Exclude stocks with no valid stock code from candidate preview. | KRX joins and flow lookup become unreliable. |
| Keep report rows with missing target/opinion in detail, but do not let them improve evidence strength. | Missing values should not boost a candidate. |
| Do not rank by report count alone. | Report activity without price/flow context can mislead. |
| Do not rank by investor flow alone. | 수급 is a supporting signal, not a thesis. |
| Mark category fallback explicitly. | Today's category mapping must not silently explain old dates. |
| Mark insufficient KRX flow coverage. | Absence of flow data is not neutral evidence. |

## Rotation ETF / Stock Candidate Preview

This is a separate preview from the stock candidate evidence table.

| Step | Needed Data | Status |
| --- | --- | --- |
| 1 | Cycle image text labels | Need manual extraction or OCR review. |
| 2 | Alias from image label to 업종 display name | Not started. |
| 3 | 업종 coordinate map | First pass exists for some categories. |
| 4 | 업종 -> ETF candidates | Needs operator-managed mapping or verified source. |
| 5 | 업종 -> stock candidates | Can derive from report/category/KRX data after alias is stable. |
| 6 | Evidence preview | Can show report count, turnover, flow, ETF trend separately. |
| 7 | One ETF + one stock final pick | Deferred until history and policy are stronger. |

## Proposed Implementation Stages

| Stage | Goal | Completion Criteria |
| --- | --- | --- |
| CE-0 | Document policy and field contract | This document exists and is linked from roadmap/current-work. |
| CE-1 | Add read-only candidate evidence builder | Repository/DTO returns separated evidence rows for a date. Implemented as computed `web-view` DTO/API. |
| CE-2 | Add web-view preview table | User page shows `오늘의 관찰 후보` and `관찰 후보 근거`, not trading recommendations. |
| CE-3 | Add rotation alias table draft | Manual image-label-to-category mapping exists as `data/rotation_image_aliases.json` draft. |
| CE-4 | Add ETF/category mapping draft | Operator-managed ETF candidates per 업종 exist. |
| CE-5 | Add rotation candidate preview | Shows ETF/stock candidates by rotation label with evidence. |
| CE-6 | Evaluate simple weights offline | Only after enough history and manual review. |

## UI Copy Rules

Public candidate wording is owned by [surface-guide.md](surface-guide.md). Keep this plan focused on evidence content and do not duplicate the full shared phrase list here.

## Next Action

`CE-1` and the visible candidate-evidence section now exist. The remaining current task is offline explanation usefulness review under `TODO2-NI-EVAL`; it does not authorize rank changes or public numeric scoring. Rotation alias/ETF mapping remains a separate preview task.


<!-- Merged from: docs/codex/candidate-evidence.md -->
## Candidate Evidence Batching (Completed Record)

Status: complete. This is a concise implementation record, not an active task list.

- Batched stored candidate context for valid daily-summary symbols so the builder reuses preloaded report, target-revision, flow-window, market-history, and target-progress data.
- Internal selection order and public DTO wording remained unchanged; the change added no live collection, scheduler, or Telegram path.
- Historical verification: the query-budget RED count was 33; the focused batched regression passed within a 278-test relevant set; value QA and browser smoke each reported zero issues.
- Historical mini-PC measurement for `2026-05-15`: daily payload about `49KB/1.1s`, candidate evidence (`limit=20`) about `95KB/0.3s`. These are dated measurements, not a current performance guarantee.

## Target Price Progress Contract and Completion Record

Status: the first stored target-gap/progress DTO path is implemented. Counts and coverage values below are dated backfill records; use current runbooks and live evidence for present coverage.

This document fixes the P1-prep boundary for target-price based observation.

It can support observation-candidate recommendation, but it does not approve public numeric scoring, investment grades, buy/sell judgment, or automatic historical report backfill.

## Purpose

The user-facing `web-view` now has separate tabs for:

- `메인`: date-based report summary and selected-stock detail
- `관찰`: stored evidence rows from reports, KRX market reference, and investor flow
- `ETF`: stored ETF trend reference
- `순환매`: descriptive cycle-image overlay

Target-price progress belongs to the `관찰` direction, not the current main report list.

## Metrics

| Metric | Formula | Use |
| --- | --- | --- |
| Target gap | `(target_price - current_price) / current_price` | Shows remaining upside/downside to the report target. |
| Target progress | `(current_price - baseline_price) / (target_price - baseline_price)` | Shows how much of the move from first observed report price to target has been reached. |
| Max progress | Maximum progress after the report date | Later backtest/validation metric. |
| Hit days | First business-day count until target is reached | Later factual validation metric. |

## Baseline Rule

| Item | Decision |
| --- | --- |
| Baseline date | First stored report date for the stock within the observation window. |
| Baseline price | KRX close price on that report date. |
| Target price | Valid numeric target only. Missing markers such as `N/A`, `-`, or empty values are excluded from calculations. |
| Multiple reports | Use min/max target range for display. Metric calculation can use representative target only after a separate policy decision. |
| Display wording | `진행률`, `괴리율`, `도달 여부`, `관찰 후보`, and `우선 확인` are allowed. Do not use public numeric `점수`, `투자등급`, `매수 후보`, or buy/sell decision wording. |

## Historical Data Coverage

Target progress uses stored KRX closes only for retrospective report-window analysis; it does not change the current Toss 20:00 market baseline. Report backfill was completed through 2026-05-12 for the 2026 YTD window. Those counts are a dated completion record, not evidence of current host coverage.

Any future report-history repair must use a scoped dry run and the current CLI's backup/confirmation safeguards. Automatic backfill is not implied by this completed plan.
## P1 Boundary

| Step | Status | Boundary |
| --- | --- | --- |
| P1-prep | Done | Web-view tab split, visible observation evidence, preview/report backfill guard. |
| P1 metric DTO | Done | `candidate_evidence.rows[].target_price_progress` now exposes stored-data-only target gap/progress in the `관찰` tab. |
| P1 backfill | Done for 2026 YTD baseline | `2026-01-02` through `2026-05-12` now has stored reports for all 87 covered business dates. Continue future backfill in small backed-up batches only. |
| P2+ validation | First read-only pass done | `target_observation` now exposes stored-window max progress and first target-hit D+ days when the baseline is below the target range. Longer-history interpretation remains observational only. |

## First Metric DTO Result

`target_price_progress` is now attached to each `candidate_evidence` row.

| Field group | Meaning |
| --- | --- |
| `available`, `gap_available`, `progress_available` | Whether each calculation has enough stored report/KRX price data. |
| `baseline_date`, `baseline_price` | First stored target-price report date for the stock and the KRX close price on that date. |
| `current_date`, `current_price` | Selected business date and the stored KRX close price for that date. |
| `target_price_min`, `target_price_max` | Valid numeric target-price range from the daily summary. |
| `target_gap_min_percent`, `target_gap_max_percent` | Current price gap to the target range. |
| `progress_to_min_percent`, `progress_to_max_percent` | Progress from baseline price toward the target range. |
| `validation_available`, `validation_window_days` | Whether stored future KRX rows are enough to show factual validation and how many later trading rows were inspected. |
| `max_progress_to_min_percent`, `max_progress_to_max_percent` | Maximum observed progress toward the target range inside the stored window. |
| `hit_min_horizon_days`, `hit_max_horizon_days` | First D+ trading-day index where the close reached the lower/upper target. |
| `validation_notice` | Why the validation is available or skipped, such as `stored_window_only` or `baseline_inside_target_range`. |

Display wording remains limited to `괴리` and `진행`.
This is evidence for review and observation-candidate ordering only. It is not a public numeric score, investment grade, or buy/sell signal.

## Historical Report Backfill Completion (2026-05)

- Guarded report-history backfill completed through `2026-05-12` for `87/87` 2026 business dates in the reviewed window.
- At completion, the development DB reported `3,813` report rows, `2,453` daily summaries, and `db-verify` passed.
- Per-batch counts and timings were removed from this active contract; the figures above are dated development evidence, not current operating coverage.

## Operator Memo Progress (Completed Record)

Status: complete. The former step-by-step plan is replaced by this result summary.

- Implemented `operator-memo-status`, `market-commentary-practice`, `operator-photo-inbox-status`, and `periodic-data-needs-audit`.
- Verification at completion covered focused CLI/control/Telegram replay/web-view tests plus value QA and browser smoke.
- The photo path stores operator-submitted images in the local inbox; no scheduler registration, broad KRX ingest, public score, or trading copy was added.
- Historical memo counts and test totals are not current operating status.

## Operator Memo Surface Reflection (Completed Record)

Status: complete. The checked tasks below are retained as implementation history.

- One-line market commentary is available through the stored-data web-view and Telegram `/한줄` command.
- Periodic data-needs status is available in the web-view and `operator-status`.
- The `/사진` path stores operator-submitted images locally; it does not expose them through the web-view.
- The active surface/access contract remains in `surface-guide.md`; this summary is not a separate policy source.

## Historical Candidate Evidence Goal Prompt

The former `/goal` prompt targeted the initial CE-1 implementation and selected-date KRX evidence. It is superseded by the implemented DTO/UI and the current source contract above; do not use it to start new work. Current public and data boundaries live in `AGENTS.md`, `surface-guide.md`, and `data-governance.md`.
