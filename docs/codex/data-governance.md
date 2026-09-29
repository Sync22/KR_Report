# Data Governance

Data quality, source ownership, rebaseline process, and baseline status.

## Included sections
- Data Quality Checklist
- Data Source Policy
- Historical KRX boundary


<!-- Merged from: docs/codex/data-governance.md -->
## Data Quality Checklist

## Purpose

This checklist prevents future changes from mixing raw source values, aggregate values, and presentation values.
Use it before changing parser, summary, Telegram, admin-gui, or web-view behavior.

## Core Rule

Missing or non-actionable source values are not data points.

Current operating ownership: web-view market, ETF, and investor-flow snapshots are written from the bounded Toss `20:00` close capture. Existing KRX rows are retained historical data only; they must not be selected as a current-display fallback.

They can be preserved for detail review, but they must not distort aggregate calculations, rankings, ranges, or representative labels.

A completed news collection with no matched article is a coverage result, not negative evidence. Show `매칭 뉴스 없음` clearly, but do not lower a report/market-supported observation candidate solely because the bounded collection returned zero matches. Direct positive or direct caution evidence may change observation ordering; an empty match must not cause the top-two cohort to churn into newly uncollected rows.

## Product-Intent Rule

Data quality is not the same as product usefulness.

For user-facing work, first decide whether the value helps a daily briefing, notable-stock view, market mood summary, rotation reference, or observation-priority decision. If it only explains pipeline correctness, keep it in `admin-gui`, CLI output, tests, or docs instead of adding it to the shared `web-view`.

| Product Layer | Allowed User Wording | Keep Out Of User Surface |
| --- | --- | --- |
| Rough daily briefing | `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `시장 분위기`, `눈에 띄는`, `확인 후보`, `수급 참고`, `확인 포인트` | `매수 추천`, `매도 추천`, `점수`, `등급`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, `매수 기회`, `전략 제안` |
| Evidence drilldown | Compact source-backed reasons and missing-state labels | Full validation chains, scheduler state, raw manifests, debug-only flags |
| Admin/operator | Raw process state and diagnostics when useful | Secrets, tokens, uncontrolled external exposure |

Wording QA is context-based, not a raw keyword ban. User-facing briefings may say things like `시황 해설`, `추천 판단 아님`, `점수 없이 저장 근거만 확인`, `등급 없음`, `리포트 의견 참고`, and `뉴스 근거` when they clarify limits or evidence. Keep blocking explicit trading-call wording such as `매수 추천`, `매도 추천`, `추천 종목`, `매수 기회`, `전략 제안`, `진입가`, `청산가`, numeric score labels like `점수: 92`, and grade labels like `등급: A`.

User-facing visual summaries such as sector/theme breadth bars, top-2 observation candidates, and rotation ETF/stock reference slots are allowed only when the underlying values are stored facts. Missing category mappings, ETF snapshots, KRX rows, or flow rows must be shown as `부족한 정보` or equivalent empty-state text, not converted into negative evidence or hidden success.

Observation recommendation is allowed. Do not weaken it into vague copy when the evidence supports a clear `우선 확인` ordering. The blocked boundary is trading advice, public numeric scoring, broker execution, or automated strategy wording. If a future approved real-time source is added, its values may strengthen or weaken observation priority, but the source/freshness and read-only limits must be explicit.

Do not describe the current public wording limits as a permanent product ceiling. They are public-surface limits for the stored-data/current-readiness phase. If stable real-time data later supports trading-decision review, that belongs in an operator-only decision-support or execution-lab lane with separate quality, audit, permission, and safety rules.

## Required Boundary Check

| Boundary | Rule | Example |
| --- | --- | --- |
| Raw/source value | Preserve enough detail to explain the source row. | A report with no target price still appears in stock detail. |
| Parsed/storage value | Store missing numeric values as `NULL`, not `0`. | KRX `N/A`, `NA`, `NULL`, `NONE`, `-`, and blank numeric fields become `None`. |
| Aggregate value | Exclude missing values from calculations. | Target price range uses only parsed numeric target prices. |
| Representative label | Exclude missing labels from representative voting. | Dominant opinion ignores `N/A`; use `N/A` only when no valid opinion exists. |
| Display value | Show missing values clearly without pretending they are data. | Telegram/web detail shows `목표가 -` and `의견 없음`. |

## Source Access Boundary

| Source type | Rule | Example |
| --- | --- | --- |
| Historical API records | Keep existing records for historical analysis; normal refresh is disabled. | Existing KRX Open API stock/ETF/index rows. |
| Current stored reference | Use the bounded Toss 20:00 close snapshot with source and capture/freshness labels. | Toss market indices/flow and Top20 stock/ETF references; valid daily-summary candidates also receive close-reassessment references. |
| Historical screen-backed data | Existing samples remain available for historical review; no normal scheduled ingest. | KRX Data Marketplace `[12009]` investor-flow rows. |
| Screen condition | Preserve and store source conditions that change output values. | Query type, date range, stock code, share unit, money unit. |
| Source label | Store source identity separately from product display labels. | `toss_openapi`, `krx_open_api`, and `krx_data_market` remain distinct. |
| Fallback source | Keep fallback data clearly marked and do not mix it with primary source rows. | Naver internal trend API used only for comparison/fallback. |

## Pre-Implementation Checklist

Before implementing a data or display change, verify:

| Check | Required Question |
| --- | --- |
| Source semantics | Is this a real value, a missing marker, or a source-specific placeholder? |
| Parser behavior | Does the parser normalize known missing markers before DB write? |
| DB meaning | Does `NULL` mean unknown/missing, and is `0` reserved for a real zero? |
| Aggregation | Are missing values excluded from min/max/count/ranking/mode unless explicitly intended? |
| Detail visibility | Can the operator or user still see that a source row had missing data? |
| Duplicate display | Is the same semantic value repeated in summary and detail, or should one layer link/drill down instead? |
| Surface boundary | Is this value safe for Telegram/web-view, or should it stay in admin/operator diagnostics? |
| Recommendation boundary | Does this value justify observation priority, or is it drifting into trading advice, public score, or broker execution? |
| Future decision boundary | Is this still public observation copy, or is it a separately approved operator-only decision-support/execution-lab feature? |
| Source access | Is this value from an official API, a screen-backed source, or a fallback source? |
| Source condition | Are units, date range, query type, and market filters captured with the row? |
| Test coverage | Is there at least one regression test for missing/duplicate/edge source values? |

## Identity And Date Checklist

| Item | Rule | Risk If Ignored |
| --- | --- | --- |
| Report identity | Use `source_id` or `identity_key` for dedupe. Do not dedupe by visible stock/title/broker strings. | Missed reports or duplicate reports when display text drifts. |
| Display identity | Display labels such as stock name, broker name, and category name are user-facing labels, not durable keys. | Future grouping may silently merge unrelated source rows. |
| Business date | Use `business_date` for archive, summary, Telegram, and web-view grouping. | Reports can be bucketed by poll time instead of market date. |
| Published time | Use `published_at` as source report time, not as the archival grouping key. | Late-night/holiday reports can land in the wrong summary. |
| Collected time | Use `collected_at` only for operational timing and retry/debug context. | Operational timing can leak into product-level date logic. |

## Duplicate And Grouping Checklist

| Item | Rule |
| --- | --- |
| Same-broker repeated reports | Summary display may collapse broker names as `broker_name(count)`, but detail views must keep report-level rows. |
| Same-broker target price | Same-broker representative target price uses the maximum parsed numeric value. Missing target values do not participate. |
| Same-broker opinion | Same-broker representative opinion uses the latest report, but `N/A` is not allowed to dominate valid opinions. |
| `broker_display` | Treat as display-only derived text. Do not parse it later as canonical broker data. |
| Sector/theme dedupe | Visible category-name dedupe is presentation-level. Do not treat it as canonical taxonomy history. |
| Summary/detail split | Summary rows explain the aggregate. Detail rows explain the underlying source reports. Do not make one replace the other. |

## Current Missing-Value Policy

| Field Type | Storage / Aggregate | Display |
| --- | --- | --- |
| Report target price missing | `target_price_value = NULL`; excluded from target range | `목표가 -` in detail/search |
| Report opinion missing | `opinion_normalized = N/A`; excluded from dominant opinion vote | `의견 없음` |
| KRX numeric missing | `NULL`; excluded from numeric interpretation | `-` or empty-state text |
| Naver report missing marker | Normalize known source placeholders before aggregation when parser sees them | Preserve missing state in detail/search output |
| Stock identity missing | Do not use as a reliable grouping key | Exclude row or mark as 확인필요 in operator-only diagnostics |
| Sector/theme missing | Do not infer a category | Show mapping limitation or omit from category rollup |

## Summary vs Detail Rule

| Surface | Behavior |
| --- | --- |
| Daily/Intraday summary | Show only aggregate values that survive missing-value filtering. |
| Stock detail / stock search | Show each source report, including missing target/opinion as `목표가 -` and `의견 없음`. |
| Admin/operator diagnostics | May show raw/failure context when useful, but must avoid secrets and keep source labels clear. |
| User web-view | Show observation values, missing states, and source-labelled candidate assessments. A directional label must be reproducible from direct evidence and distinguish supporting, cautionary, conflicting, and missing evidence; it must not be a hidden score or unsupported certainty. |

## Evidence Direction Rule

`리포트 가설`, `직접 뉴스`, `보조/시장맥락 뉴스`, `장중 반응`, `Toss 20:00 저장 기준값`, and `KRX 기준일` are separate evidence layers. Do not let one layer silently replace another.

- Direct positive and direct caution news may produce `상승 근거 우세`, `하방 위험 우세`, or `직접 근거 상충` only when their respective counts are visible.
- Candidate matching (`direct` / `indirect` / `market_context`) and source lineage (`independent` / `report_recap` / `unknown`) are separate axes. Lineage metadata must not erase a stored candidate match.
- The current automatic collection path may produce `report_recap` or `unknown`; therefore `independent` must not be a web-view availability gate. Show a recap as `리포트 재인용 매칭`, and do not count it again as separate independent support.
- Show `매칭 뉴스 없음` only when the deduplicated candidate evidence set is empty.
- Main `Top2` is a maximum, not a quota. A single-report row with no matched news, stored Toss baseline, or stock-flow evidence remains in the observation pool but is not forced into the main priority cohort.
- Compare report target revisions only with the same broker's earlier report. A date-level range comparison must be labeled as a date aggregate and must not be presented as every broker raising or lowering its target.
- Before the same-day 20:05 capture run, show the Toss 20:00 close price/flow as `저장 예정`; after that run window, distinguish a missing capture from an unavailable source. Never backfill that label with a KRX value.
- Indirect or market-context rows may add context but must not overturn direct-evidence direction by themselves.
- The same article is counted once per candidate/date by its stored evidence key. A later completed collection with no new match must keep already stored same-date direct evidence visible and expose its later collection time separately.
- Web-view and Telegram candidate summaries must use the same selected candidate codes and the same deduplicated evidence set. A date-wide run list must not replace a candidate-linked summary with unrelated or older empty runs.
- The top-two cohort is selected once for a response. Main-card news, a completed web-view collection response, and the matching market-briefing candidate lines must keep that same code order; a third candidate belongs in the broader `관찰` surface, not the top-two summary.
- Existing KRX `[12009]` flow is historical-only. Any historical flow detail must use the same stock-level rows and show each row date; current stored market flow comes from Toss.
- `Naver 거래대금 상위` overlap and a bounded top-two Naver quote are separate intraday references. A non-overlap result does not erase the candidate's price, change, turnover, market status, or checked/trade time.
- Historical KRX exact/stale/missing describes the selected analysis date only; it is not current-market freshness or price direction.
- Historical KRX status must not replace a news label. When a completed collection has no direct or contextual match, say `매칭 뉴스 없음`; expose legacy KRX metadata only in its historical-analysis context.
- Intraday turnover/price confirms a time-bounded market reaction only when the candidate overlaps the fetched row and the display includes market status plus trade or checked time.
- A Toss 20:00 value is an end-of-day stored baseline. It is not a substitute for intraday confirmation or direct news evidence.
- Toss `configured`, current quote fetched, and 20:00 baseline stored are different states. Show `configured` only for credentials/live opt-in readiness, `current` only after that request returns a quote with its checked time, and the stored baseline only with its storage time.
- A target-price reach day is a retrospective result in a stored historical KRX window. Show the observed window and missing state; never present it as a promised outcome, probability, or future trading instruction.
- If the layers conflict or lack direct evidence, display `추가 확인` or `직접 근거 부족`; do not manufacture a stronger conclusion.

Time-series validation belongs after these layers are stored consistently across multiple dates. It should test whether a declared evidence state improves later observation outcomes versus the report-only baseline; it must not be used to retrofit a single-day label.

## Agent Review Checklist

When using subagents for parser, summary, notification, web-view, or DB work, include this instruction:

```text
Check docs/codex/data-governance.md before proposing or implementing changes.
Verify raw/source, parsed/storage, aggregate, and display semantics separately.
Call out any N/A/NULL/duplicate-display risk explicitly.
```

## Required Test Pattern

New changes touching data interpretation should include at least one of:

- parser test with `N/A`, `NA`, `NULL`, `NONE`, `-`, or blank input
- summary test where missing target/opinion does not affect range or dominant label
- formatter/web-view test where detail still exposes missing fields as `목표가 -` / `의견 없음`
- duplicate-display test or explicit assertion that summary/detail roles are separated


<!-- Merged from: docs/codex/data-governance.md -->
## Data Source Policy

## Purpose

This document fixes which source owns each data domain and how category names should be displayed.

Short rule:

- Naver owns research reports.
- Toss OpenAPI owns current and newly stored web-view market reference data.
- Existing KRX rows are retained for historical review only.
- Industry/theme labels are a separate taxonomy layer and must stay explicitly labeled.

Do not mix report collection semantics with market-data semantics.

## Source Ownership

| Domain | Primary Source | Current Tables / DTOs | Policy |
| --- | --- | --- | --- |
| Research reports | Naver Research | `reports`, `daily_stock_summaries` | Keep Naver as the report source. |
| Report title, broker, target price, opinion | Naver Research | `reports`, summary/detail DTOs | Keep source facts from Naver; parse for aggregation, preserve detail. |
| Intraday new-report detection | Naver Research | `intraday_alert_batches`, `intraday_alert_batch_reports` | Keep Naver as the detection source. |
| Stock code search / name candidates | Stored metadata plus the latest eligible daily Toss `stocks/all` cache; Naver autocomplete fallback | `toss_stock_universe_cache`, Telegram and web-view stock lookup DTOs | Lookup reads the stored snapshot and never calls Toss per query. Preserve its source business date; do not require a renewed KRX master feed. |
| Stock price, close, change, volume, turnover | Toss OpenAPI | `stock_market_daily`, Toss current quote DTOs, stock detail DTOs | Toss current queries and stored market snapshots own new web-view values. Existing KRX rows remain historical review data and must not be relabeled as current Toss values. |
| Stock master, market, listing metadata | Toss `stocks/all` for fixed KR markets, cached by the 20:05 capture | `toss_stock_universe_cache`, `stock_metadata`, provider metadata DTOs | Keep listing/search fields and security type separate from report taxonomy. Existing KRX metadata is frozen history, not an active dependency. |
| ETF daily reference | Toss OpenAPI | `etf_daily_snapshots`, `etf-trend` DTO | Availability requires actual stored Toss ETF rows. A stock or index snapshot date alone must not imply ETF availability. |
| Market index reference | Toss OpenAPI | `web-view` Toss market context; `market_index_daily` | Toss KOSPI/KOSDAQ values and stored snapshots lead current display. Existing KRX rows are historical review only. |
| Investor flow | Toss OpenAPI | Toss market context; `stock_investor_flow_daily`, `market_investor_flow_daily` | Toss same-day values are provisional and retain their provider timestamp. Existing KRX flow rows may be shown only as explicitly labeled historical review data. |
| Intraday quote/turnover reference | Toss Securities OpenAPI current-price reference, Naver market-top overlap, and Naver top-two fallback quote | `web-view` top-2 priority DTOs and Toss baseline table when saved | Toss is the primary current-price reference for the server-derived top-two `우선 확인`; Naver top-two quotes run only when Toss is unavailable or incomplete. Naver market-top overlap remains a separate user-triggered turnover reference. None may affect trading-decision support, broker execution, or public trading calls. |
| Industry / theme labels | Naver industry/theme pages plus operator-managed snapshots | `stock_metadata`, `stock_theme_memberships`, `category_master`, `category_membership_snapshots` | Keep as taxonomy data, not market reference data. Do not call it KRX-owned until a verified KRX taxonomy source exists. |

## Category Refreshability

Category catalog rows are not all refresh commands.

| Category Type | Refreshable Source | Non-Refreshable Source | Rule |
| --- | --- | --- | --- |
| `sector` / `업종` | `naver_industry`, `naver_upjong` | `naver_quote`, `operator`, custom labels | Batch refresh is allowed only after `refresh-industry CODE --dry-run` proves the key is a Naver upjong-compatible code. |
| `theme` / `테마` | enabled Naver theme catalog rows | disabled rows | Theme refresh can use enabled theme catalog rows, but still requires dry-run before confirmed batch execution. |

Do not treat a display label, current quote category, or manually entered grouping key as a source API key.

## Naming Rules

Use these names in user-facing Korean copy:

| User-Facing Name | Internal Name | Meaning | Notes |
| --- | --- | --- | --- |
| `업종` | `sector` | One representative industry-style grouping for a stock. | Prefer this over `섹터` in user-facing UI. |
| `테마` | `theme` | A many-to-many theme grouping. | A stock can belong to multiple themes. |
| `카테고리` | `category` | Generic umbrella for 업종 + 테마. | Use only when one UI/API handles both. |
| `시장 참고` | Stored Toss 20:00 context | Toss index/market flow/Top20 references lead current display. Existing KRX price, volume, turnover, ETF, and flow rows are historical review only; never current fallback. | Show source/capture freshness and label same-day Toss aggregate flow provisional. |
| `장중 참고` | approved intraday source | Bounded Toss top-two quote, market index/flow/Top20, and Naver market-top overlap. | Must show source/freshness. Market-top non-overlap is a scope result, not an absent-price result. It may affect observation priority only as observation support. |
| `리포트 요약` | Naver report summary | Report count, broker, target price, opinion summary. | Keep separate from market-source ownership. |

Avoid these in user-facing copy unless explaining internals:

| Avoid | Use Instead | Reason |
| --- | --- | --- |
| `섹터` | `업종` | Korean UI should use one concise label. |
| `sector/theme` | `업종/테마` | English internal keys should not leak into the user page. |
| `분류` alone | `업종`, `테마`, or `카테고리` | Too vague for click targets and table headings. |
| `KRX 업종/테마` | `업종/테마 기준` with source note | Current category labels are not KRX-owned. |

## Display Labels

Keep report evidence and current stored market context as separate layers. Current market cards use stored Toss references; historical KRX rows are shown only on explicitly historical review paths.

| Surface | Label Pattern |
| --- | --- |
| Daily report rows | `리포트 요약` |
| Current market/detail | `Toss 20:00 시장 참고` with source and capture time |
| Historical KRX analysis | `KRX 과거 참고` with the selected date |
| Investor flow | `수급 참고`; distinguish Toss current stored flow from historical KRX samples |
| Missing current source | Explicit missing/stale state; never substitute a KRX historical row |
| Category rows | `업종 요약`, `테마 요약`, `업종/테마 상세` |

## Current Source Direction

The historical plan to move current market references to KRX is superseded. Stored Toss 20:00 snapshots own current web-view market, ETF, and flow references. Existing KRX rows remain historical analysis/recovery data and are not a current fallback or scheduled refresh source. Current capture operations are documented in [market-data-runbook.md](market-data-runbook.md).

## Guardrails

- Keep Naver report facts, stored Toss market snapshots, and historical KRX rows in separate source layers.
- Do not relabel historical KRX or Naver reference values as current Toss snapshots.
- The GET-only web-view reads stored data; collection and persistence belong to explicitly bounded scheduled/operator paths.
- Preserve missing numeric markers and source-specific timestamps; do not turn missing values into zero or success.
- Do not expose public numeric scoring, investment grades, trading calls, broker execution, or order routing.
- Keep operator-only diagnostics off the friend-facing web-view.
- Future operator decision support requires its own source, audit, permission, and safety contract; it does not change public-surface limits.
## Historical KRX Boundary

The 2026 KRX rebaseline/backfill plans are superseded as current-source guidance. Existing KRX market and investor-flow rows remain available for past-date analysis; normal KRX scheduled refresh has been removed, and KRX must not fill missing current Toss values.

- Current capture operations: [market-data-runbook.md](market-data-runbook.md).
- Current scheduler registration: [mini-pc-runbook.md](mini-pc-runbook.md).
- Historical execution evidence: [history.md](history.md).
- Category snapshots remain source-dated; do not copy present-day category mappings into historical dates.

Any new KRX data repair/import requires a separately scoped and approved operation. Do not recreate scheduled KRX ingestion from this historical record.
