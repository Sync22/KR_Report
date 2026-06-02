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
- Scheduler registration, scheduler execution, or unattended collection.
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
- `https://stock.naver.com/api/domestic/news/focus?sid=401&page=1&pageSize=20&date=YYYYMMDD` for `시황·전망`
- `https://stock.naver.com/api/domestic/news/focus?sid=402&page=1&pageSize=20&date=YYYYMMDD` for `기업·종목분석`

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

This command is manual and operator-only. It emits JSON to stdout, uses temporary files for Scrapling output, deletes those files after reading, and must not write live fetch results into the repository, SQLite, logs, scheduler state, Telegram, or public `web-view` by default. It also does not update `admin-gui` in v1; an `admin-gui` review surface is a future operator-only integration candidate, not a public-surface exception.

Saved operator observations may be reviewed with:

- `python -m stock_monitor news-intelligence-observations [--date YYYY-MM-DD] [--stock-code CODE] [--run-id RUN_ID]`
- `python -m stock_monitor news-intelligence-daily-brief --date YYYY-MM-DD [--format text|json]`

These readback commands are operator-only and read-only. They compare saved runs and evidence rows, emit operator summaries, and must not fetch live news, write DB rows, start schedulers, send Telegram, or expose raw operator payloads in public `web-view`.

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

`stock_impact` is an operator-only news impact assessment. It describes how news may change review priority; it is not a price target, investment grade, or buy/sell recommendation. Supported labels are `Strong Positive`, `Positive`, `Neutral`, `Caution`, `Negative`, and `Strong Negative`.

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

The report-linked analysis slice remains pure Python. The default `news-intelligence-preview` command must still emit JSON only and must not write DB rows, start schedulers, send Telegram, or expose anything in public `web-view`. It also does not update `admin-gui` in v1; future `admin-gui` use should be documented as an operator-only review surface before implementation. The only v1 DB write exception is the explicit operator-only `--save-observation` path described below.

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
- The default manual preview remains `writes_db=false`.
- Stored rows are operator-only observation/evaluation data and must not be copied raw into public `web-view`, Telegram, or scheduler surfaces. A thin public-safe `web-view` projection may be added later when it hides internal sentiment scores, impact scores, raw warnings, and operator-only recommendation-support fields. `admin-gui` remains private/operator-only and may later show fuller review rows after a separate operator-review contract.
- When KRX reference data comes from the nearest prior stored row, the preview/save payload must distinguish exact-date reference from stale fallback reference and warn rather than silently treating stale KRX data as same-day confirmation.
- The stored lane must not contain broker secrets, order intent, order-routing instructions, or public buy/sell calls.

## Public-Safe Web-View Projection Direction

News intelligence should not remain invisible after saved observations exist. The product direction is to surface an incomplete-but-clearly-labeled summary in `web-view` rather than waiting for perfect news judgment.

Allowed public-safe projection, stored-data only:

- Availability state: `news_observation_available=true|false`.
- Display labels derived from existing operator labels, such as `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, and `뉴스 근거 부족`.
- Compact counts such as direct-news count, caution count, and market-context count.
- KRX reference status as `exact`, `stale`, or `missing`.
- One to three article titles/sources when they are already stored in observation rows.
- A short public reason that explains what to check, not what to buy or sell.

Forbidden in public projection:

- `overall_sentiment`, article `sentiment_score`, numeric impact, conviction, target-return, investment grade, buy/sell, entry/exit, take-profit, one-pick, broker, or order-routing wording.
- Live Naver fetch from `web-view`.
- Triggering `--save-observation` from `web-view`.
- Scheduler, Telegram, admin control, or DB mutation from the public route.

Placement direction:

- The first visible slice should be a small stored-data block in the `메인` top-2 priority area or a compact row in the `관찰` tab.
- If there are no saved observations, the page should show a simple missing state such as `저장된 뉴스 관찰 없음` instead of hiding the feature entirely.
- Low coverage, indirect-only, or market-context-heavy results should still be visible as `참고` or `추가 확인 필요`; do not hard-block visibility solely because the analysis is imperfect.

Future Toss Securities Open API or another verified quote/turnover source may strengthen this projection by confirming market reaction freshness. That use remains read-only observation support and must not become broker execution, order routing, or public trading advice.

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
