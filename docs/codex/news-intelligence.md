# News Intelligence

Operator-only news intelligence and its future public-safe stored projection.

## Top2 확인 주제 연결 (2026-09-08)

- 기존 서버 선정 Top2에만 `research_focus`를 붙여 메인 카드 아래 `더 확인할 주제`와 `관련 뉴스 찾기` 링크를 표시한다. 종목 상세 버튼과 검색 링크는 별도 클릭 대상이다.
- 같은 날짜·종목의 저장 리포트 제목과 기존 뉴스 badge의 대표 원문 제목을 사용한다. Stage 1 핵심어가 있으면 Stage 2 검색어를 재사용하고, 없으면 `종목명 + 원문 제목`으로 명시적 fallback을 만든다. fallback은 Stage 2의 검증된 검색어라고 주장하지 않는다.
- 주제/검색어는 최대 3개, 중복 제거, 출처 종류와 원문 제목을 보존한다. 사용자 클릭 시에만 네이버 뉴스 검색을 연다. 웹뷰 GET에서 새 provider 수집이나 DB 쓰기는 발생하지 않는다.
- 기존 운영 briefing collector 결과에도 동일한 `research_focus`를 포함한다. 기존 종목명/코드 매칭, 5-lane 수집, 저장·scheduler·Telegram 발송 조건은 유지한다. 검색어를 종목 alias로 넣거나 자동 검색 실행으로 바꾸지 않는다.
- 확인 주제는 미확인 질문이다. 독립 뉴스 증거·positive/caution 판단·Top2 순위에 가산하지 않는다. Stage 3/4 평가기와 합성 fixture는 운영 판단에 연결하지 않는다.
- 최신 저장 리포트에서 기존 핵심어 규칙이 빈 결과를 낼 수 있어 제목 fallback이 필요하다. 실제 검색 품질 향상은 별도 실측 대상이다.
- 검증: `test_candidate_research`, 전체 `test_web_view`/`test_cli_commands`, `test_intraday_empty_notification`, keyword extractor/planner 회귀에서 600 passed (186.44s). 실제 2026-09-07 저장 Top2로 만든 격리 화면을 1440/390px에서 확인했고 확인 주제 2개 카드·검색 링크 3개·가로 넘침 없음·상세 버튼 안의 링크 0개를 확인했다. 외부 요청은 화면 검증 중 차단했다.
- 운영 반영: 기존 웹뷰 프로세스 소유권 확인 후 8780 웹뷰만 재시작, `/health` 200 확인. 인증 없는 `/`와 후보 API는 401을 유지하며, 인증 후 운영 화면의 브라우저 검증은 수행하지 않았다. 이미지 증거는 `data/reviews/top2-research-1440.png`, `data/reviews/top2-research-390.png`다.

## Keyword/query Stage 0–4 평가표 (2026-09-08)

평가 대상은 오프라인 키워드 추출·검색어 계획·결과 평가·캡처 입력 계층이다. 아래 기준을 먼저 고정하고 실행 결과를 기록한다. 통과는 해당 계약의 충족을 의미하며 실제 검색 품질 개선이나 투자 성과를 의미하지 않는다. 미측정 항목을 0점 또는 통과로 집계하지 않으며 종합 점수는 만들지 않는다.

| ID | 평가 항목 | 통과/판정 기준 | 결과 |
| --- | --- | --- | --- |
| E0 | 고정 corpus 계약 | 문서·gold·분류·상한 계약 테스트 전체 통과 | 통과 |
| E1 | 키워드 추출 | 12개 문서의 accepted/rejected 값·종류·순서가 gold와 정확히 일치 | 통과: 12/12 정확 일치 |
| E2 | 검색어 계획 | 12개 문서의 query·strategy·priority 정확 일치, 금지 검색어 0건 | 통과: 12/12 정확 일치, 금지 0건 |
| E3 | 합성 결과 평가 | 5개 대표 문서의 분모·중복·불확실·빈 결과·참조 커버리지 테스트 통과 | 통과: 아래 산술 결과 확인 |
| E4 | 캡처 입력 준비 | 출처 메타데이터·시간대·ID·순위·검색어 연결·판정 완결성·원문 보존 테스트 통과 | 통과: 실제 데이터가 아닌 inline 합성 입력으로 검증 |
| E5 | 인접 뉴스 기능 회귀 | news intelligence/quality guards/collectors/linked evidence 테스트 통과 | 통과: 지정 회귀 범위에서 실패 없음 |
| E6 | 실제 검색 결과 품질 | 실제 provider 캡처와 별도 판정 자료가 있어야 계산 가능 | 미측정: 실제 캡처 없음 |
| E7 | 검색어 개선 효과 | 동일 조건의 기존/신규 검색어 결과 및 독립 평가 자료 필요 | 미측정: 비교 자료 없음 |

E1/E2는 구현 시 사용한 고정 사례에 대한 적합성 평가다. 미관측 문서 일반화 성능은 평가하지 않는다. E3의 합성 수치는 산술 검증용이며 provider 성능 추정치가 아니다. E4의 `capture_evaluable`은 판정 ID의 완결성만 뜻하며 판정 의미와 참조 집합 검증은 Stage 3 평가기가 담당한다. 메타데이터 검증은 실제 provider 출처 인증이 아니다.

실행 결과: 아래 9개 테스트 파일을 실행해 **121 passed in 2.09s**, 종료 코드 **0**을 확인했다. 별도 메모리 내 실행으로 Stage 0 문서 → Stage 1 추출 → Stage 2 계획을 gold와 대조하고, Stage 3 평가기의 문서별 결과를 직접 산출했다. 코드·gold·운영 DB·스케줄러·Telegram은 변경하지 않았다.

### 합성 fixture 산술 평가 결과

입력: `tests/fixtures/query_result_evaluation/result_facts.json` 및 분리된 `judgments.json`. 5개 문서 중 4개에 검색 결과가 있으며, 총 5개 검색어 배치·11개 raw 결과다. 모든 계획 검색어를 캡처한 데이터가 아니므로 전체 검색 품질로 확대 해석하지 않는다.

| 합성 사례 | raw 결과 | 중복 제거 결과 | 중복률 | 노이즈율 | precision proxy | 참조 집합 커버리지 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 삼성전자 HBM (`news_samsung_hbm_supply_01`) | 2 | 2 | 0/2 | 0/2 | 2/2 | 2/2 |
| 한화 폴란드 계약 (`news_hanwha_poland_contract_01`) | 4 | 3 | 1/4 | 1/4 | 2/3 | 2/2 |
| NAVER AI (`report_naver_ai_acronym_01`) | 3 | 3 | 0/3 | 1/3 | 1/2 | 1/2 |
| HD 조선 (`report_hd_shipbuilding_cycle_01`) | 2 | 2 | 0/2 | 0/2 | 2/2 | 2/3 |
| 일반 시장 코멘트 (`report_generic_market_comment_01`) | 0 | 0 | 미정의 | 미정의 | 미정의 | 미정의 |

NAVER 사례의 불확실 판정 1건은 precision 분모에서 제외한다. 빈 결과의 비율은 `None`이며 0%가 아니다. 참조 커버리지는 고정 참조 집합 대비 값이며 인터넷 전체 recall이 아니다. 표의 분수는 반올림 오해를 피하기 위한 표시이며 실제 함수는 float 또는 None을 반환한다.

캡처를 주지 않은 Stage 4 통제 실행은 `status=no_capture`, capture/result/judged/unjudged/evaluable-document count 모두 0을 반환했다. 이는 데이터 미제공 상태를 구분하는 테스트이며 실제 provider를 조회하거나 전수 조사한 결과가 아니다. 현재 이 평가에는 실제 캡처를 투입하지 않았으므로 E6/E7은 미측정으로 남긴다.

**판정:** 고정 사례 적합성·합성 산술·오프라인 입력 준비는 통과했다. 실제 검색 품질과 검색어 개선 효과의 평가 완료를 뜻하지 않는다. 다음 실측에는 출처·시각·검색어가 보존된 실제 캡처와 별도 판정 자료가 필요하며, 개선 효과 비교에는 같은 조건에서 수집한 기존/신규 검색어 결과가 추가로 필요하다.

재실행 명령 (프로젝트 루트, 매 실행 고유한 `--basetemp` 사용):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp_stage04_evaluation_20260908 tests/test_keyword_search_expansion_contract.py tests/test_core_keyword_extractor.py tests/test_core_keyword_query_planner.py tests/test_query_result_evaluation.py tests/test_query_result_capture.py tests/test_news_intelligence.py tests/test_news_quality_guards.py tests/test_news_collectors.py tests/test_news_linked_evidence.py
```

## Current Lineage Contract (2026-08-23)

- Stored article evidence carries `canonical_url`, `lineage_type`, and `lineage_reason`. Existing rows migrated from schema v9 default to `unknown` / `legacy_row_unverified` without losing the article row.
- `lineage_type` is `independent`, `report_recap`, or `unknown`. URL/title similarity may automatically identify recaps, but it may not automatically promote an item to independent evidence.
- Only explicitly verified `independent` evidence may strengthen a candidate or produce an actionable public badge. `report_recap` and `unknown` stay reference-only even if an older relevance or impact classifier would have promoted them.
- This is evidence provenance, not a numeric score, investment grade, recommendation, or trading instruction.

## 2026-07-29 Daily Evidence Accumulation Plan

### Goal

Make same-day Top2 news evidence useful across the stored-data web-view and the existing 09:15, 12:00, and 15:15 market-briefing Telegram slots. A later empty collection must not hide a directly matched article collected earlier that day.

### Delivery

- Aggregate unique same-day evidence across all saved collection runs for each candidate.
- Expose only public-safe counts, a compact article title, collection-run count, latest collection time/status, and whether earlier daily evidence remains after a latest no-match run.
- Use that same stored projection in the web-view and the existing slot briefing builder; do not add a scheduler task, a send path, live fetch, or a new database write path.
- Rename the Top2 residual-data line to `추가 확인` so the presence of a direct news item is not described as overall insufficient evidence.

### Verification

- A direct morning observation followed by a later empty run still renders `뉴스로 후보 강화`, `collection_run_count=3`, `latest_collection_status=no_match`, and `daily_evidence_retained=true`.
- The market-briefing text identifies the section as daily accumulated news and carries the last collection state from the same shared summary.
- Existing 09:15/12:00/15:15 scheduling, delivery dedupe, and public-safe message QA remain unchanged.

## Included sections
- News Intelligence Contract

<!-- Merged from: docs/codex/news-intelligence.md -->
## News Intelligence Contract

## Purpose

This contract defines the first operator-only news intelligence module for KR_Report / Stock Monitor.

The module may generate sentiment scores, event impact labels, and an operator summary, but only inside an operator-only recommendation-draft lane. It does not approve public numeric scores, investment grades, trading calls, Telegram candidate alerts, broker execution, or order routing.

## Scope

Allowed in v1:

- Manual or in-memory article input supplied by a caller or test fixture.
- Date-mode Naver stock-news collection boundaries for operator-only preview work.
- Fixture-backed parser tests for Naver stock-news pages.
- Deduplication by URL, normalized title, and similar titles.
- Article-level concise summary, sentiment label, sentiment score, keywords, event types, impact label, and impact explanation.
- Stock-level operator JSON with sentiment distribution, top five news items, important events, and operator summary.
- Future analyzer injection so an LLM-backed analyzer can be added later behind the same contract.

Blocked by default in v1:

- Automatic live news crawling or provider smoke.
- SQLite writes or migrations unless the operator explicitly passes `--save-observation` for the operator-only observation tables.
- Generic scheduler registration, unbounded unattended collection, or source-wide crawling. The bounded `scheduled-poll` Top2 collection exception is documented below.
- Telegram send or Telegram candidate alerts.
- Direct public `web-view` exposure of raw/operator-only payloads. A later public-safe, stored-data-only projection is allowed when this contract and `surface-guide.md` define the exact fields.
- Broker secrets, broker execution, order routing, or order suggestions.
- Public buy/sell, one-pick, investment-grade, target-return, conviction, entry, or exit wording.

## Collection Boundary

The v1 source lane is Naver stock news, but collection stays operator-only and disconnected from production surfaces.

Supported source lanes:

- `https://stock.naver.com/news/flashnews`
- `https://stock.naver.com/news/mainnews`
- `https://stock.naver.com/news/ranknews`
- `https://stock.naver.com/api/<domestic-news-path>/news/focus?sid=401&page=1&pageSize=20&date=YYYYMMDD` for `시황·전망`
- `https://stock.naver.com/api/<domestic-news-path>/news/focus?sid=402&page=1&pageSize=20&date=YYYYMMDD` for `기업·종목분석`

The default collection mode is date mode, not latest mode. The default target date is Asia/Seoul today. Latest-mode views may hide older same-day items, so v1 request specs should represent a full target-date collection intent per source lane.

The collector boundary is:

- `NewsCollector` protocol for article collection.
- `ManualNewsCollector` for in-memory and fixture-driven use.
- `NaverStockNewsCollector` for Naver stock-news source boundaries.
- Transport and parser separation: tests validate Markdown page parsing and focus API JSON parsing with fixtures; live transport is injected manually and must not run automatically.
- `/news/section` rendered Markdown is a source-probe or active-tab fallback only. The two supported section lanes must use the focus API `sid` values above.
- Stock matching by company name, stock name, stock code, and caller-supplied aliases after per-source deduplication.

Scrapling is the preferred active source-probe tool for rendered Naver source inspection and manual operator preview collection. The allowed v1 command is:

- `python -m stock_monitor news-intelligence-preview --stock-name NAME [--stock-code CODE] [--alias ALIAS] [--date YYYY-MM-DD]`
- `python -m stock_monitor news-intelligence-briefing-collect --date YYYY-MM-DD [--limit N] [--stock-code CODE ...] [--save-observation --confirm-save]`
- `python -m stock_monitor news-intelligence-collect-top-candidates --date latest --candidate-limit 10 --top-n 5 --dry-run --json`
- `python -m stock_monitor news-intelligence-collect-top-candidates --date latest --candidate-limit 10 --top-n 5 --confirm-collect --json`

These commands are manual and operator-only. They emit JSON/text to stdout, use temporary files for Scrapling output, delete those files after reading, and must not write live fetch results into the repository, SQLite, logs, scheduler state, Telegram, or public `web-view` by default. `news-intelligence-briefing-collect` selects target stocks from stored daily summaries, or an in-memory rebuild from stored reports when summaries are absent. It may save rows only when both `--save-observation` and `--confirm-save` are present. `news-intelligence-collect-top-candidates` selects Top N rows from the stored candidate evidence snapshot and reuses the same briefing collector; `--dry-run` is read-only and `--confirm-collect` is the explicit operator write guard. The enabled bounded scheduler path may reuse the same collector under its existing guards. The web-view reads only the resulting public-safe stored projection and does not invoke the collector. It also does not update `admin-gui` in v1; a future private `operator-review` surface is the review UI candidate, not an `admin-gui` expansion.

Scrapling executable resolution is explicit:

- Prefer `--scrapling-exe "%USERPROFILE%\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe"` on the operating PC when the command reports `missing Scrapling executable`.
- Alternatively set `SCRAPLING_EXE` to the same executable path before running the command.
- The manual command does not search broad tool folders by itself. The bounded `scheduled-poll` reuses the project canonical runtime at `<workspace-parent>\_tools\scrapling\.venv\Scripts\scrapling.exe` when `SCRAPLING_EXE` is not set.

Saved operator observations may be reviewed with:

- `python -m stock_monitor news-intelligence-observations [--date YYYY-MM-DD] [--stock-code CODE] [--run-id RUN_ID]`
- `python -m stock_monitor news-intelligence-daily-brief --date YYYY-MM-DD [--format text|json]`
- `python -m stock_monitor news-evidence-coverage-audit --recent-business-days 10 --candidate-limit 10 --json`
- `python -m stock_monitor news-evidence-run-scope-audit --recent-business-days 10 --candidate-limit 10 --json`
- `python -m stock_monitor news-no-match-diagnosis --date latest --candidate-limit 10 --top-n 5 --json`

These readback and audit commands are operator-only and read-only. They compare saved runs and evidence rows, emit operator summaries, and must not fetch live news, write DB rows, start schedulers, send Telegram, or expose raw operator payloads in public `web-view`.

### Naver Search Lane Lab Status

The Naver search lane is archived/hold as of `2026-07-03 KST`. It is not a production source lane and must not be connected to DB writes, matching logic, web-view output, scheduler automation, or News Evidence Digest projection.

Lab result summary:

- Strict-only QA over recent 3 business days / Top5 candidates selected 22 titles. Automatic labels were `usable_digest=21` and `report_rehash=1`, but human review judged only about 8-10 titles as clearly digest-safe.
- `post-filter-v2` reduced selected titles to 18, removed one parser artifact, two false positives, and one duplicate topic, and separated weak labels as `report_rehash=1`, `esg_pr=4`, and `corporate_notice=2`.
- Final `post-filter-v2` usable ratio was `11/18 = 61.1%`, which barely clears the numeric threshold but still fails the false-positive quality gate.
- Remaining risk: political/policy/person indirect mentions can still look like stock evidence, and search results can mix report rehash, PR, and unrelated lifestyle/news fragments into a Digest candidate list.

Hold decision:

- Do not add a production search lane.
- Do not implement `post-filter-v3`, political/person-name filters, or additional search-lane lab CLIs unless the lane is explicitly reopened.
- Keep News Evidence Digest UI, existing 5-lane evidence, and the manual Top-candidate collect path as the active operating path.

### Insane Search Sidecar Shadow Run (2026-08-24)

The archived Naver search lane remains a production hold. A separate 12:00 and
15:00 KST, five-business-day lab may assess Insane Search only through an append-only
manifest at `docs/codex/operations/insane-search-shadow.jsonl`.

- The runner copies the operating DB into a temporary SQLite file before it
  calls the existing candidate-evidence builder; it never migrates or writes
  the operating DB.
- It freezes the builder's candidate rank and sort tuple at the cutoff, keeps
  stored evidence as the baseline, and records only public article metadata,
  canonical URLs, access metadata, and fail-closed lineage labels.
- Manifest v3 freezes the web-view `selected` state separately from the
  full Top10 observation pool and records one search trace per searched
  candidate even when no article link is returned. An all-failed search pass
  returns a failed process status instead of appearing successful to Task Scheduler.
- Pre-contract v1/v2 runs remain append-only audit records but do not count toward
  the ten-run acceptance sample. Candidate metrics distinguish run observations
  from unique `business_date + stock_code` pairs.
- `independent` is never inferred from an unknown or recap result. A missing
  publish time is excluded from point-in-time recovery and remains explicitly
  retrospective/unverified.
- The runner does not connect to scheduler state, Telegram, web-view,
  admin-gui, or candidate ordering. Its JSONL is a lab artifact, not a source
  of production truth.

Run with the project venv and an already-isolated Insane Search runtime:

```powershell
.venv\Scripts\python.exe scripts\lab\run_insane_search_shadow.py `
  --engine-python <isolated-insane-python> `
  --engine-root <insane-search-engine-root>
```

After ten completed lines across five business days:

```powershell
.venv\Scripts\python.exe scripts\lab\run_insane_search_shadow.py --aggregate
```

Reopen conditions:

- A clear deterministic rule set can reduce manual false positives to near zero.
- Existing 5-lane evidence coverage remains operationally insufficient over repeated operating days.
- Real use shows News Evidence Digest is repeatedly empty and materially less useful without search-lane coverage.

Operator workflow:

1. Run `news-intelligence-preview` without `--save-observation` to inspect live collection coverage and operator-only judgment fields.
2. When the operator explicitly wants to keep a single-stock result, rerun with `--save-observation`; this is an operator-only write path for news observations.
3. For market-briefing target stocks, run `news-intelligence-briefing-collect --save-observation --confirm-save` to persist observations for multiple stored-summary stocks in one manual pass. The enabled scheduled market-briefing slot may perform the same save internally for its server-derived current top two after delivery/time guards have passed.
4. For News Evidence Digest coverage validation, run `news-intelligence-collect-top-candidates --date latest --candidate-limit 10 --top-n 5 --dry-run --json` after the Daily candidate snapshot exists.
5. If the target list is correct and Scrapling is available, run `news-intelligence-collect-top-candidates --date latest --candidate-limit 10 --top-n 5 --confirm-collect --scrapling-exe "%USERPROFILE%\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe" --json`. A failed collect records only the error for the operator; it must not fail the Daily workflow.
6. After confirm collect, rerun `news-evidence-coverage-audit --recent-business-days 10 --candidate-limit 10 --json` and `news-evidence-run-scope-audit --recent-business-days 10 --candidate-limit 10 --json` to compare coverage, run target overlap, and failure reasons.
7. If same-date Top candidates have runs but still no digest, run `news-no-match-diagnosis --date latest --candidate-limit 10 --top-n 5 --json` to separate source coverage, date-window, alias, parser, and unknown gaps using stored rows only.
8. Use `news-intelligence-observations --format text|json` to inspect saved run/evidence details by date, stock code, or run id.
9. Use `news-intelligence-daily-brief --format text|json` to group saved runs by date and candidate-linkage label.
10. Use `market-briefing` and `web-view` as stored-data, public-safe visibility checks after observations already exist. Missing observations are collected through the explicit CLI or enabled bounded scheduler path, not from the page.

The preview command is intentionally incomplete as a day-level collector:

- `page_limit=1`
- `full_day_complete=false`
- `coverage_note="v1 preview fetches first visible/API page per source lane"`

Per-source preview diagnostics must include `fetched`, `fetch_error`, `parsed_count`, and `matched_count`. Overall diagnostics must include `parsed_count`, `deduped_count`, and `matched_count`. Matched articles must include `source_lane`, `matched_alias`, `match_reason`, `match_scope`, `relevance`, and `relevance_reason`.

Supported relevance labels:

- `direct`: the stock appears in the title or title+summary and the article is primarily stock-specific.
- `indirect`: the stock appears only in the summary/body.
- `market_context`: the article is mainly index, ETF, sector, flow, or broad market context even when the stock is mentioned.

Supported match scopes:

- `title`
- `summary`
- `both`

Partial source failures are allowed and should be represented in `sources[*].fetch_error` plus `warnings`. The command should exit non-zero only when Scrapling is unavailable or no articles can be parsed from any source lane.

## News Flow Preview Lane

`news-flow-preview` is a separate operator-only lane for reading the article flow from user-provided news source URLs. It is not a stock top-N enrichment feature, not candidate-evidence linkage, and not a recommendation engine.

Allowed in v1:

- Fixture-backed article flow parsing from an explicit `--source-url` allow-list.
- Explicit operator-approved live source-probe from the supported Naver source URLs listed in this contract.
- Article contract fields: `title`, `date`, `url`, `source`, and `summary`.
- Per-source diagnostics: requested URL, source name, parsed article count, and warnings for missing or out-of-scope sources.
- Whole-flow aggregation: repeated stock mentions, sector/theme flow, key issues, caution signals, market mood, text preview, JSON preview, and Telegram draft copy.
- Preview-only `market-briefing` source-flow section injection from the same fixture contract.

Blocked by default:

- Live fetch unless the operator explicitly approves a source-probe pass for the provided URLs.
- DB writes, scheduler registration, Telegram real sends, `admin-gui`, `web-view`, candidate-evidence mutation, public numeric scoring, buy/sell wording, broker execution, and order routing.
- Treating repeated mentions as recommendations, ranks, scores, grades, or trading signals.

Supported command:

- `python -m stock_monitor news-flow-preview --source-url URL [--source-url URL ...] --fixture PATH [--format text|json]`
- `python -m stock_monitor news-flow-source-probe --source-url URL [--source-url URL ...] [--date YYYY-MM-DD] [--format text|json]`
- `python -m stock_monitor market-briefing --slot mood|lunch|preclose --news-flow-source-url URL [--news-flow-source-url URL ...] --news-flow-fixture PATH`

The command must only include fixture sources whose `source_url` exactly matches one of the provided `--source-url` values. Fixture sources outside that allow-list are excluded and reported as warnings. Requested URLs missing from the fixture are also reported as warnings.

`news-flow-source-probe` is a manual live probe only. It may fetch only the supported Naver source URLs for the selected date, emits text/JSON diagnostics to stdout, and must not write DB rows, create fixture files, send Telegram messages, register schedulers, or connect to `admin-gui`/`web-view`.

The Telegram draft and `market-briefing` source-flow section are preview text only. They must include the source URL basis and summarize article flow without trading judgment. The source-flow fixture options must be rejected with `--send` and must not send Telegram messages.

## Output Contract

The JSON report must include:

- `stock`
- `stock_code`
- `operator_only=true`
- `public_safe=false`
- `live_provider=null`
- `connected_surfaces=[]`
- `overall_sentiment`
- `sentiment_distribution`
- `important_events`
- `top_news`
- `operator_summary`

The manual preview wrapper must also include contract flags:

- `surface="news-intelligence-preview"`
- `operator_only=true`
- `public_safe=false`
- `live_fetch=true`
- `writes_db=false`
- `sends_telegram=false`
- `registers_scheduler=false`
- `connects_web_view=false`

`overall_sentiment` and article `sentiment_score` are internal operator values on the `-100..100` scale. They are not public scores and must not be copied into public `web-view` or Telegram output without a later policy change.

`stock_impact` is an operator-only news impact assessment. It describes how news may change review priority; it is not a price target, investment grade, or broker/order instruction. Supported labels are `Strong Positive`, `Positive`, `Neutral`, `Caution`, `Negative`, and `Strong Negative`. Public surfaces must not copy the raw label, but may derive a source-labelled direction from direct evidence only: `상승 근거 우세`, `하방 위험 우세`, `직접 근거 상충`, `직접 근거 중립`, or `직접 근거 부족`.

Supported sentiment labels are `Positive`, `Neutral`, `Negative`, `Caution`, and `Mixed`.

## Event Types

Supported event labels:

- `Earnings`
- `Contract`
- `Investment`
- `Regulation`
- `Lawsuit`
- `Management`
- `M&A`
- `Product Launch`
- `Analyst Target`
- `Price Move`
- `Supply/Demand`
- `Industry Cycle`
- `Risk/Caution`

The deterministic v1 analyzer is Korean-rule based. It should treat price jumps, analyst target changes, supply/demand crowding, ETF/index context, and caution wording separately instead of flattening everything into positive/neutral/negative.

## Report-Linked Evidence Lane

News intelligence is not an isolated news table. Its operator value comes from linking news judgment to the existing report pipeline:

- `target_date + stock_code` is the primary join key.
- `reports.source_id` and `reports.identity_key` may be stored as related report references.
- `daily_stock_summaries` provides same-day report density and broker/opinion context.
- KRX stock snapshots provide same-day price, volume, turnover, and market-reference presence.
- KRX investor-flow rows provide stored flow context when available.
- Candidate-evidence priority may be used as operator-only context, but news evidence must not be copied into public candidate DTOs without a separate public-safe contract.

The report-linked analysis slice remains pure Python. The default `news-intelligence-preview` command must still emit JSON only and must not write DB rows, start schedulers, send Telegram, or expose anything in public `web-view`. It also does not update `admin-gui` in v1; future private UI review should be documented as an `operator-review` surface before implementation. The only v1 DB write exception is the explicit operator-only `--save-observation` path described below.

Supported operator-only evidence cases:

- `report_direct_positive_news`: a same-day report context is reinforced by direct positive stock news.
- `report_with_caution_news`: report context exists, but news adds caution, mixed tone, or risk wording.
- `no_report_strong_direct_news`: no same-day report exists, but direct strong news may deserve an operator review candidate.
- `report_heavy_market_context_only`: reports are present, but matched news is mostly index/ETF/sector context.
- `price_move_with_krx_turnover`: price-move news is backed by stored KRX turnover reference.
- `price_move_without_krx_reference`: price-move news exists but stored KRX reference is missing, so the market reaction remains unverified.
- `news_only_caution`: no report context exists and the news is mainly caution/risk.
- `weak_news_duplicate_context`: repeated market-context news should be downranked as weak direct evidence.

These cases may use operator recommendation labels such as `strengthen_report_candidate`, `review_with_caution`, or `promote_news_only_candidate`. They are recommendation-support labels for the operator lane, not public buy/sell instructions, investment grades, broker execution, or order-routing signals.

## Operator Observation Save Boundary

The manual preview command may persist report-linked news observations for quality review only when the operator passes `--save-observation`. This is not enabled by default.

Allowed storage tables:

- `news_intelligence_runs`: one operator preview/evaluation run.
- `report_linked_news_evidence`: article-level report-linked evidence rows for that run.

The readback command may derive review-only summaries from these rows, including direct/indirect/market-context counts, evidence-case counts, operator recommendation-support counts, and KRX exact/stale/missing reference status. These summaries are operator comparison aids for deciding whether candidate-evidence integration is ready; they are not public DTOs.

The stored lane may include:

- `run_id`, `target_date`, `stock_name`, `stock_code`, aliases, source mode, coverage counts, warning summaries, and the operator summary snapshot.
- Related report references, daily summary presence, candidate priority presence, KRX reference presence, KRX turnover, investor-flow presence, source lane, article fields, match diagnostics, relevance, sentiment, event types, stock impact, evidence case, and operator recommendation-support labels.

Storage guardrails:

- DB writes require the explicit operator save option `--save-observation`.
- Batch market-briefing collection requires both `--save-observation` and `--confirm-save`; without both flags it is a preview/no-write command.
- Top-candidate collection requires `--confirm-collect`; without it, `--dry-run` or the missing-confirm path must not write DB rows.
- The default manual preview remains `writes_db=false`.
- When live collection succeeds but no article matches the target stock, the batch collector may still save an empty observation run with `matched_count=0` and `saved_evidence_count=0`. This records that collection actually ran, so `web-view` can show `뉴스 수집 완료` / `매칭 뉴스 없음` instead of pretending the feature has not run.
- Stored rows are operator-only observation/evaluation data and must not be copied raw into public `web-view`, Telegram, or scheduler surfaces. The current `market-briefing` and `web-view` projections are allowed only as thin summaries that hide internal sentiment scores, impact scores, raw warnings, and operator-only recommendation-support fields. The access-gated web-view collect action may save the rows needed for that projection; the bounded scheduled market-briefing slot may do the same for its current top two before composing its compact Telegram projection. Neither path may expose the raw collector payload. `admin-gui` remains operations/status/control only; fuller review rows belong in a future `operator-review` surface after a separate contract.
- When KRX reference data comes from the nearest prior stored row, the preview/save payload must distinguish exact-date reference from stale fallback reference and warn rather than silently treating stale KRX data as same-day confirmation.
- The stored lane must not contain broker secrets, order intent, order-routing instructions, or public buy/sell calls.

## Public-Safe Web-View Projection Direction

News intelligence should not remain invisible after saved observations exist. The product direction is to surface an incomplete-but-clearly-labeled summary in `web-view` rather than waiting for perfect news judgment.

Allowed public-safe projection:

- Availability state: `news_observation_available=true|false`.
- Display labels derived from existing operator labels, such as `뉴스 근거 수집 전`, `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, and `추가 확인 필요`.
- Compact counts such as direct-news count, caution count, and market-context count.
- KRX reference status as `exact`, `stale`, or `missing`.
- One to three article titles/sources when they are already stored in observation rows.
- A short public reason that explains what to check, not what to buy or sell.

Current visible slice:

- Archive calendar dates may show `news_observation_count` from saved observation evidence rows.
- Daily overview may include `news_observation_summary` with `available`, `display_label`, `reason`, `connection_note`, compact counts, KRX status, `top_titles`, and stock-level `items`.
- Candidate evidence rows may include a compact `news_observation_badge` for the same stock code or same stock name.
- Stock detail may include `news_observation_detail` with the same compact public-safe counts, KRX status, and top titles.
- Daily summary items with a valid stock code may link to the stock detail view so the operator can move from the main summary to the stock-level evidence without exposing raw operator payloads.

Public projection must preserve evidence direction rather than suppress it into a generic badge. A derived direction is allowed only when it includes direct supporting/caution counts, keeps indirect and market-context rows separate, and shows KRX freshness as metadata rather than direction.

Forbidden in public projection:

- `overall_sentiment`, article `sentiment_score`, numeric impact, hidden conviction score, target-return, investment-grade shorthand, broker, or order-routing wording. An attributed source opinion and a reproducible derived evidence direction are allowed; neither may conceal contrary direct evidence or become an unsupported action instruction.
- Live Naver fetch or any `--save-observation` trigger from `web-view`.
- Scheduler, Telegram, admin control, broker/account/order mutation, or arbitrary DB mutation from the public route.

Placement direction:

- The first visible slice is a small stored-data block in the `메인` summary area plus compact badges in candidate/stock detail surfaces.
- If there are no saved observations, the page should show an actionable state such as `뉴스 근거 수집 전` plus the collect action instead of hiding the feature entirely.
- Low coverage, indirect-only, or market-context-heavy results should still be visible as `참고` or `추가 확인 필요`; do not hard-block visibility solely because the analysis is imperfect.

Future Toss Securities Open API or another verified quote/turnover source may strengthen this projection by confirming market reaction freshness. That use remains read-only observation support and must not become broker execution, order routing, or public trading advice.

## Deferred Operating Data Check

Operating real-data validation is separate from the fixture visible-flow work. For the next business-day check, use a small approved stock set and keep the order:

1. Verify canonical Scrapling runtime and DB health.
2. Run no-write `news-intelligence-preview` first.
3. If the operator explicitly approves, run `--save-observation` for only the selected stocks.
4. Read back with `news-intelligence-observations` and `news-intelligence-daily-brief`.
5. Open `web-view` and confirm archive count, daily summary, candidate badge, and stock detail projection.
6. Do not connect the result to broker/execution or order routing. The only production automation exception is the bounded scheduled market-briefing collection and compact projection described above; it is limited to the server-derived top two and the existing slot guards.

## Integration Boundary

The v1 module is a pure Python library under `stock_monitor.news`.

It must not import or call:

- `stock_monitor.cli`
- `stock_monitor.db`
- `stock_monitor.notify`
- web-view route builders
- scheduler scripts

The safe first integration points are the manual/operator CLI preview, explicit `--save-observation`, and read-only observation readback/daily brief commands above. The next visible product step is a stored-data-only public-safe web-view projection, not raw operator payload exposure.

## LLM Extension Point

Future LLM-based analysis should implement the same analyzer protocol and return the same structured model. The deterministic analyzer remains the offline fallback and test oracle.

## Operator Market Research Note

`market-research-note` is a separate operator-only local-review lane. It does not alter the news-intelligence collector, candidate priority, SQLite, Telegram, scheduler, `admin-gui`, or `web-view`.

It consumes an existing realtime-first snapshot JSON and may consume a manually captured `news-flow-source-probe --format json` response. The source probe remains a separately initiated live probe; the note command itself performs no fetch.

```powershell
New-Item -ItemType Directory -Force data\reviews\market-research | Out-Null
python -m stock_monitor news-flow-source-probe --source-url <approved-naver-url> --date 2026-07-28 --format json > data\reviews\market-research\2026-07-28_flow.json
python -m stock_monitor market-research-note --snapshot data\reviews\realtime-first\2026-07-28_1500.json --market-flow data\reviews\market-research\2026-07-28_flow.json
```

The resulting JSON/Markdown files are local operator review artifacts only. A snapshot generated more than 15 minutes after its requested KST slot is labelled `invalid_for_slot`; it remains readable but must not be compared as a normal 15:00 observation.
