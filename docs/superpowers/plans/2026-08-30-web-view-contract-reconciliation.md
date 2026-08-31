# Web-view Contract Reconciliation Plan

## Goal

현재 `main`의 저장 데이터와 API 계약을 기준으로 메인·관찰·종목·시장·순환매 화면의 과선언, 중복, 끊긴 탐색을 제거한다. 새 데이터 수집 경로나 점수 체계는 만들지 않는다.

## Success Criteria

- ETF 저장 행이 없으면 source freshness와 ETF 추세가 `available`로 표시되지 않는다.
- Toss 시장 문맥은 payload에 이미 있는 종목명, 지수 등락률, 개인·외국인·기관 수급을 빠짐없이 표시한다.
- 순환매 업종 카드를 선택하면 기존 업종 상세 API가 열리고, 종목 화면의 관련 업종 이동은 실제 관련 분류가 있을 때만 노출된다.
- Top2 밖 후보는 예약 뉴스 수집 대상이 아닌 상태를 `뉴스 근거 수집 전`으로 오인시키지 않는다.
- 종목 상세의 저장 가격 이력과 현재가 문구가 실제 Toss/KRX 소스 계약과 일치하며 같은 값을 불필요하게 반복하지 않는다.
- 현재 canonical 문서에서 신규 화면 기준값은 Toss, KRX는 과거 복기용이라는 계약이 일치한다.
- 관련 pytest, web-view value QA, browser smoke, 실제 브라우저 확인을 통과한다.

## Task 1: Market and ETF truthfulness

1. `tests/test_web_view.py`에 ETF 행이 없는 저장일의 freshness/trend 실패 테스트를 추가한다.
2. 같은 테스트 파일에 Toss 시장 문맥이 이름·등락률·개인 수급 필드를 소비하는 계약을 고정한다.
3. `_build_web_view_source_freshness_summary`에는 실제 ETF reference date를 별도로 전달한다.
4. `build_web_view_etf_trend_snapshot`은 ETF 행이 있는 날짜만 추세 항목으로 인정한다.
5. 기존 `/api/toss-market-context` payload 필드를 재사용해 웹 렌더러를 보완한다.

## Task 2: Restore existing category navigation

1. 기존 순환매 highlight와 category detail API의 필드 계약을 테스트로 고정한다.
2. 순환매 카드에 기존 `data-public-category-id` 탐색 계약을 연결한다.
3. 종목 상세의 관련 업종 버튼은 실제 `related_context`가 있을 때 첫 관련 분류로 이동하게 한다.
4. 호출되지 않는 `categoryRow` helper는 제거한다.

## Task 3: Remove misleading and duplicated copy

1. Top2 밖 관찰 후보의 뉴스 상태를 예약 수집 범위 밖으로 구분한다.
2. 종목 상세의 `선택일 이후 저장 KRX 이력`을 실제 혼합 저장소 계약에 맞게 고친다.
3. 조회 현재가가 있을 때 `현재가 ... 확인 전` 같은 모순을 제거하고, 관련 분류가 없으면 이동 버튼을 숨긴다.
4. `data-governance.md`, `candidate-evidence.md`, `operating-guide.md`의 현재 소스 계약만 현행화한다. 과거 결정 기록은 삭제하지 않는다.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_view.py -q -p no:cacheprovider --basetemp .tmp_pytest_webview_contract
.venv\Scripts\python.exe -m stock_monitor web-view-value-qa --recent-business-days 3 --stock-limit 10 --json
.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json
git diff --check
git status --short --branch
```

마지막으로 웹뷰를 재시작하고 gate-disabled 로컬 검증 또는 제공된 입장 코드로 실제 5개 탭을 확인한다.
