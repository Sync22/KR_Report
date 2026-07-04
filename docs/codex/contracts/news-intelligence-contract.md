# News Intelligence Contract

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
- Generic scheduler registration, unbounded unattended collection, or source-wide crawling. The bounded `scheduled-market-briefing-slot` exception is documented below.
- Telegram send or Telegram candidate alerts.
- Direct public `web-view` exposure of raw/operator-only payloads. A later public-safe, stored-data-only projection is allowed when this contract and `surface-contract.md` define the exact fields.
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

These commands are manual and operator-only. They emit JSON/text to stdout, use temporary files for Scrapling output, delete those files after reading, and must not write live fetch results into the repository, SQLite, logs, scheduler state, Telegram, or public `web-view` by default. `news-intelligence-briefing-collect` selects target stocks from stored daily summaries, or an in-memory rebuild from stored reports when summaries are absent. It may save rows only when both `--save-observation` and `--confirm-save` are present. `news-intelligence-collect-top-candidates` selects Top N rows from the stored candidate evidence snapshot and reuses the same briefing collector; `--dry-run` is read-only and `--confirm-collect` is the explicit operator write guard. The web-view may call this same batch collector only through the access-gated `POST /api/news-observations/collect` operator action, which is limited to selected-date top priority candidates and returns only the public-safe stored summary after saving. It also does not update `admin-gui` in v1; a future private `operator-review` surface is the review UI candidate, not an `admin-gui` expansion.

Scrapling executable resolution is explicit:

- Prefer `--scrapling-exe "%USERPROFILE%\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe"` on the operating PC when the command reports `missing Scrapling executable`.
- Alternatively set `SCRAPLING_EXE` to the same executable path before running the command.
- The command does not search broad tool folders by itself. Missing Scrapling is an operator environment issue, not a Daily workflow failure.

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
10. Use `market-briefing` as a stored-data, public-safe visibility check after observations already exist. `web-view` may either show the stored projection or, when access-gated and operator-triggered, run `POST /api/news-observations/collect` to create the missing saved observation rows for the selected date/top candidates before re-rendering the same public-safe projection.

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
- Unbounded live Naver fetch from `web-view`. The only approved live-fetch/write path is the access-gated `POST /api/news-observations/collect` operator action, which calls the existing briefing collector with explicit save/confirm behavior for selected-date top candidates.
- Any other `--save-observation` trigger from `web-view`.
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
