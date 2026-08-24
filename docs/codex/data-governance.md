# Data Governance

Data quality, source ownership, rebaseline process, and baseline status.

## Included sections
- Data Quality Checklist
- Data Source Policy
- Data Rebaseline Plan
- KRX 18-Month Backfill Analysis

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
| Official/approved API | Prefer this path when the needed field is available. | KRX Open API daily stock/ETF/index snapshots. |
| Approved real-time reference | Use a bounded read-only projection with source and freshness labels; retain stored history separately. | Toss Securities Open API top-2 quote, KOSPI/KOSDAQ current price, provisional market flow, and Top20 market attention. |
| Screen-backed source | Use only when the approved API does not expose the needed data. | KRX Data Marketplace `[12009]` investor flow. |
| Screen condition | Preserve and store source conditions that change output values. | Query type, date range, stock code, share unit, money unit. |
| Source label | Store source identity separately from product display labels. | `krx_open_api` vs `krx_data_market`. |
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
- Before the same-day 20:05 capture run, show the Toss 20:00 close price/flow as `저장 예정`; after that run window, distinguish a missing capture from an unavailable source. Never backfill that label with a KRX value.
- Indirect or market-context rows may add context but must not overturn direct-evidence direction by themselves.
- The same article is counted once per candidate/date by its stored evidence key. A later completed collection with no new match must keep already stored same-date direct evidence visible and expose its later collection time separately.
- Web-view and Telegram candidate summaries must use the same selected candidate codes and the same deduplicated evidence set. A date-wide run list must not replace a candidate-linked summary with unrelated or older empty runs.
- The top-two cohort is selected once for a response. Main-card news, a completed web-view collection response, and the matching market-briefing candidate lines must keep that same code order; a third candidate belongs in the broader `관찰` surface, not the top-two summary.
- `종목별 [12009]` flow freshness must be calculated from the same stock-level rows shown in the detail lines. If selected candidates have different dates, show each row date and label the source as partial rather than presenting the newest row as the date of every item.
- `Naver 거래대금 상위` overlap and a bounded top-two Naver quote are separate intraday references. A non-overlap result does not erase the candidate's price, change, turnover, market status, or checked/trade time.
- KRX exact/stale/missing is freshness metadata, not price direction.
- KRX freshness must not replace a news label. When a completed collection has no direct or contextual match, say `매칭 뉴스 없음`; render KRX exact/stale/missing separately as source metadata.
- Intraday turnover/price confirms a time-bounded market reaction only when the candidate overlaps the fetched row and the display includes market status plus trade or checked time.
- A Toss 20:00 value is an end-of-day stored baseline. It is not a substitute for intraday confirmation or direct news evidence.
- Toss `configured`, current quote fetched, and 20:00 baseline stored are different states. Show `configured` only for credentials/live opt-in readiness, `current` only after that request returns a quote with its checked time, and the stored baseline only with its storage time.
- A target-price reach day is a retrospective result inside the stored post-report KRX window. Show its observed window and missing state; never present it as a promised outcome, probability, or future trading instruction.
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
- KRX owns market reference data.
- Industry/theme labels are a separate taxonomy layer and must stay explicitly labeled.

Do not mix report collection semantics with market-data semantics.

## Source Ownership

| Domain | Primary Source | Current Tables / DTOs | Policy |
| --- | --- | --- | --- |
| Research reports | Naver Research | `reports`, `daily_stock_summaries` | Keep Naver as the report source. |
| Report title, broker, target price, opinion | Naver Research | `reports`, summary/detail DTOs | Keep source facts from Naver; parse for aggregation, preserve detail. |
| Intraday new-report detection | Naver Research | `intraday_alert_batches`, `intraday_alert_batch_reports` | Keep Naver as the detection source. |
| Stock code search / name candidates | Current Naver search flow; KRX migration candidate | Telegram stock lookup DTOs | Can migrate to KRX stock master later, but not urgent. |
| Stock price, close, change, volume, turnover, market cap | KRX Open API | `stock_market_daily`, `krx_context`, stock detail DTOs | KRX is the confirmed daily-history source. Bounded Toss current prices may lead the current top-two display but do not overwrite KRX history. |
| Stock master, market, listed shares, listing metadata | KRX Open API | `krx_stock_metadata` | KRX should become the canonical stock master. |
| ETF daily reference | KRX Open API | `etf_daily_snapshots`, `etf-trend` DTO | KRX only. Keep separate from company-report summaries. |
| Market index reference | Toss Securities OpenAPI current indicator price; KRX Open API fallback/history | `web-view` Toss market context; `market_index_daily` | Toss KOSPI/KOSDAQ values lead same-day market display. KRX remains the confirmed daily archive/fallback. |
| Investor flow | Toss aggregate market flow for current context; KRX Data Marketplace for stock history/validation | Toss market context; `stock_investor_flow_daily`, `market_investor_flow_daily`, `investor_net_buy_top_daily` | Toss same-day KOSPI/KOSDAQ amounts are provisional and show `updatedAt`. KRX `[12009]` remains stock-level history; `[12010]` is internal/history only and has no public projection. |
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
| `시장 참고` | Toss current context + KRX confirmed history | Toss current index/market flow/Top20 leads the market tab; KRX price, volume, turnover, ETF, and historical flow are fallback/reference. | Must show source/freshness and label same-day Toss aggregate flow as provisional. |
| `장중 참고` | approved intraday source | Bounded Toss top-two quote, market index/flow/Top20, and Naver market-top overlap. | Must show source/freshness. Market-top non-overlap is a scope result, not an absent-price result. It may affect observation priority only as observation support. |
| `리포트 요약` | Naver report summary | Report count, broker, target price, opinion summary. | Must not imply KRX ownership. |

Avoid these in user-facing copy unless explaining internals:

| Avoid | Use Instead | Reason |
| --- | --- | --- |
| `섹터` | `업종` | Korean UI should use one concise label. |
| `sector/theme` | `업종/테마` | English internal keys should not leak into the user page. |
| `분류` alone | `업종`, `테마`, or `카테고리` | Too vague for click targets and table headings. |
| `KRX 업종/테마` | `업종/테마 기준` with source note | Current category labels are not KRX-owned. |

## Display Labels

When the page combines report data with KRX data, label them as separate evidence:

| Surface | Label Pattern |
| --- | --- |
| Daily report rows | `리포트 요약` + `KRX 시장 참고` |
| Stock detail | `종목명 종목코드 | KRX 현재가 · 등락률 · 시장` |
| Category rows | `업종 요약`, `테마 요약`, `업종/테마 상세` |
| Investor flow | `수급 참고`; may support `관찰 후보 추천`, but not `수급 판단`, `매수 추천`, or `매도 추천` |
| Future intraday reference | `장중 참고`; may support `우선 확인` order or main-card emphasis after approval, but not `매수 추천`, `매도 추천`, or execution wording |
| Missing category | `업종 미확인` or `테마 미확인` |

## Migration Direction

Move non-report market information toward KRX in this order:

1. Keep stock/ETF/index price, volume, turnover, and market cap on KRX.
2. Prefer KRX stock master for stock code, market, listing metadata, and future search normalization.
3. Keep Naver quote usage only as a tactical fallback until a KRX-backed replacement is implemented.
4. Keep industry/theme taxonomy on the existing category snapshot path until a better verified taxonomy source exists.
5. Never backfill historical category snapshots by silently copying today's mapping into old dates without explicit approval.

## Guardrails

- Do not overwrite Naver report facts with KRX market facts.
- Do not overwrite KRX market facts with Naver quote values.
- Do not call category labels official KRX taxonomy unless the source is verified.
- Do not mix missing numeric markers such as `N/A`, `-`, or blank strings into ranges, ranks, or counts.
- Do not add public numeric scoring, trading recommendation, or buy/sell judgment from these source labels alone. They may support observation-candidate ordering only when combined with other stored evidence and cautious copy.
- Do not treat `read-only` as `ordering-disabled`. A verified source can affect `관찰 우선순위`. The approved exception to the default no-automation rule retains the existing 30-minute Poll collection/dedupe trigger but delivers the bounded Telegram market-context briefing only at `08:30`, then `09:30` through `15:30` KST after its business-day and delivery-window guards pass. `08:30` is report-first; later slots may collect and save news observations only for the server-derived current top two candidates and add compact source-labelled Toss context when available. It must not broaden the target universe, expose raw operator payloads, persist Toss/Naver quotes, emit a standalone alert, expose broker secrets, add a public score, create a trading call, or route an order.
- Do not treat the public trading-wording ban as a permanent ban on operator decision support. If real-time data later makes trading review viable, document it as a separate operator-only decision-support/execution-lab source lane before any public or execution behavior.


<!-- Merged from: docs/codex/data-governance.md -->
## Data Rebaseline Plan

## Purpose

This document explains why and how the project will refresh non-report data before moving to the future mini PC.

The goal is not to erase the MVP history.
The goal is to separate:

- early validation data used to prove KRX/API/screen behavior
- operating reference data that should move to the mini PC

## Decision

Keep report and delivery data as the durable project history.

Rebuild or extend market-reference data as needed because it is reproducible from approved sources.

| Data Area | Mini PC Migration Policy | Reason |
| --- | --- | --- |
| `reports` | Keep | Naver report rows are source history and dedupe evidence. |
| `daily_stock_summaries` | Keep, rebuildable | Derived from reports; useful for current web-view/archive continuity. |
| delivery/run/fragment logs | Keep | Needed to explain Telegram send state and replay safety. |
| operation events | Keep | Useful for migration/debug history unless noise becomes a problem later. |
| KRX stock/ETF/index daily snapshots | Rebuild/extend by date | Reproducible reference data; safe to upsert missing dates. |
| KRX stock master | Refresh latest before migration | Good candidate to become stock master/search reference. |
| KRX investor-flow rows | Keep current validated samples; extend only through staged flow process | Broad scheduled ingest remains disabled. The narrow anchor-date report-mentioned `[12009]` recent 31-day backfill is the only automatic exception. |
| 업종/테마 snapshots | Rebuild/extend slowly by source date | Current taxonomy is not KRX-owned and should not be silently copied backward. |

## Current Baseline

As of `2026-05-15`:

| Area | State |
| --- | --- |
| DB integrity | `db-verify` passes. |
| Schema | `5/5`, no pending migrations. |
| KRX daily snapshot range | `2024-11-08` through `2026-05-14` for stock/ETF/index daily endpoints. |
| Next KRX daily backfill candidate | `2026-05-15` only, pending normal latest-day Open API publication. |
| Category snapshot status | 90 summary dates, 6 sector-dated dates, 7 theme-dated dates, 84 fallback dates. |
| Investor-flow validation | Stage 4 complete for two dates; Stage 5 read-only display exists; broad scheduled ingest disabled. The narrow anchor-date report-mentioned `[12009]` recent 31-day backfill is the only automatic exception. |

## Rebaseline Strategy

Use the scheduled `08:10` KRX daily backfill for the newest previous-business-day gap, after the officially confirmed next-business-day `08:00` publication window.
Use the manual rolling rebaseline process only for repairs or future migration checks.

The current operator-approved execution order is:

1. KRX daily market-reference latest-day check and repair-only rebaseline.
2. Category snapshot fallback reduction.
3. User `web-view` display polish.
4. 순환매 SVG overlay first pass.
5. Detailed-doc archive cleanup.

Do not run destructive deletes as part of the normal rebaseline.
Use upsert/backfill first.
Only cleanup after the mini PC copy is verified and only if there is a specific reason.

### Standard Loop

Run this loop repeatedly:

```powershell
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag pre-krx-rebaseline
python -m stock_monitor krx-backfill-missing daily --lookback-days 183 --max-dates 10 --dry-run --allow-large-batch
python -m stock_monitor krx-backfill-missing daily --lookback-days 183 --max-dates 10 --confirm --i-backed-up --allow-large-batch
python -m stock_monitor db-verify
```

Stop when the dry-run no longer shows missing KRX daily endpoints inside the intended retention window.
The current 18-month Open API baseline is complete through `2026-05-14`; `2026-05-15` is expected to appear only after KRX publishes the latest business-day rows.

### Why `--allow-large-batch`

The default real-call guard is 5 dates.
For the rebaseline window, 10 business dates is acceptable only after:

- `db-verify` passes
- `db-backup` is created
- dry-run output is reviewed
- KRX request delay remains non-zero

## Category Rebaseline

Category data is different from KRX daily market data.

It is taxonomy data, not market-reference data.
Current source is Naver industry/theme plus operator-managed snapshots.

Current limitation:

- Existing sector catalog rows from `naver_quote` are display/cache metadata, not verified Naver `upjong` API codes.
- `refresh-industries --enabled` refreshes only sector catalog rows with `source=naver_industry` or `source=naver_upjong`.
- `naver_quote`, `operator`, and other custom sector catalog sources are not treated as Naver `upjong` API codes until separately verified.
- Theme `505` can be refreshed as a Naver theme snapshot, but broader historical category accuracy still needs a verified source-date taxonomy plan.

Use this sequence for fallback summary dates:

```powershell
python -m stock_monitor category-snapshot-status --limit 30
python -m stock_monitor category-snapshot-plan --limit 30
python -m stock_monitor refresh-industry UPJONG_CODE --snapshot-date SOURCE_DATE --dry-run
python -m stock_monitor category-catalog add sector UPJONG_CODE --name "업종명" --source naver_industry
python -m stock_monitor refresh-industries --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3
python -m stock_monitor refresh-themes --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3
```

Rules:

- Fill source-date snapshots only.
- Check `category-snapshot-plan` `plan_summary` first. If `source_date_capture_allowed_count` is `0`, do not run refresh commands for older fallback dates just to reduce the fallback count.
- Do not bulk-promote today's cache backward without explicit approval.
- Do not run `refresh-industries` or `refresh-themes` with an old `snapshot-date` just to reduce fallback counts. `category-snapshot-plan` now emits refresh commands only when the target date is the current source date; older dates should remain labeled as latest stored category classification unless separately verified.
- Do not use `naver_quote` sector keys as Naver `upjong` API keys.
- Do not use `operator` or custom sector catalog keys for batch refresh unless they are re-added with a verified Naver source label.
- Validate any newly proposed Naver upjong code with `refresh-industry UPJONG_CODE --dry-run` before adding it to the enabled sector catalog or running a confirmed snapshot refresh. The dry-run output prints the next `category-catalog add sector ... --source naver_industry` command when the code returns a usable industry name and membership count.
- Keep user-facing labels as `업종`, `테마`, and `카테고리`.
- Do not call current category data `KRX 업종/테마`.

## KRX Stock Master Refresh

Before mini PC migration, refresh latest KRX stock master separately from daily snapshots:

```powershell
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date YYYY-MM-DD --dry-run
python -m stock_monitor krx-fetch-snapshot stock-kosdaq-basic --date YYYY-MM-DD --dry-run
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date YYYY-MM-DD
python -m stock_monitor krx-fetch-snapshot stock-kosdaq-basic --date YYYY-MM-DD
```

Use the most recent confirmed KRX business date.

## Migration Explanation For Future Codex Sessions

If a future mini PC session asks why data looks this way:

- Reports were kept because they are original Naver research collection history.
- KRX daily market data was expanded later in bounded batches because it is reproducible reference data.
- Category snapshots were not blindly backfilled because industry/theme membership is a taxonomy layer and historical labels can drift.
- Broad investor-flow scheduled ingest was intentionally not enabled. Current flow rows came from validated staged samples/manual import plus the narrow anchor-date report-mentioned `[12009]` recent 31-day automatic backfill lane.

## Completion Criteria

The rebaseline is ready for migration when:

- `db-verify` passes.
- KRX daily snapshots cover the intended 18-month observation window. Current status: covered from `2024-11-08` through `2026-05-14`; `2026-05-15` is the normal latest-day pending candidate.
- The latest KRX stock master is refreshed.
- Category fallback dates are either filled with source-date snapshots or explicitly accepted as fallback.
- A final `db-backup --tag pre-mini-pc-migrate` exists.
- `docs/codex/mini-pc-runbook.md` points to this plan.


<!-- Merged from: docs/codex/data-governance.md -->
## KRX 18-Month Backfill Analysis

## Purpose

This document tracks the current 18-month KRX historical baseline work.

The goal is not to enable scoring, recommendations, or automated KRX Data Marketplace ingest. The goal is to build enough stored KRX market context for observation and future backtest work while keeping collection lanes, request volume, and DB safety explicit.

## Current Decision

| Lane | Use | Decision | Reason |
| --- | --- | --- | --- |
| KRX OpenAPI | Stock/ETF/index daily price, volume, turnover snapshots | Primary 18-month backfill lane | Approved API source, stable request shape, no browser session dependency. |
| KRX Data Marketplace | Investor flow `[12008]`, `[12009]`, `[12010]` | Manual/raw-login lane; broad scheduled ingest disabled; narrow `[12009]` same-day mentioned-stock 31-day backfill is the only automatic exception | Useful for flow reference, but login/session-dependent and higher operational risk. |
| Scrapling/browser probe | Browser-gated source/session diagnostics | Probe only | Preferred active tool for new rendered-page, browser-gated, anti-bot-sensitive, or source-comparison checks. |
| Naver report collector | Research reports | Keep separate | Report source remains Naver; do not use KRX for report history. |

## Skill And Agent Comparison

| Tool/agent | Best use | Not for | Current P2 decision |
| --- | --- | --- | --- |
| `scrapling-official` skill | Short-lived rendered-page/browser-gated source probes, session/blocking diagnostics, source comparison | Main Naver collector, Telegram, SQLite operation, KRX OpenAPI daily snapshots | Preferred active probe tool; Botasaurus is legacy/reference-only unless explicitly restored. |
| `market-data-engineer` | KRX/KIS/ETF/flow source fields, request limits, source-boundary decisions | UI polish or scheduler recovery implementation | Used for lane comparison and backfill limit review. |
| `sql-pro` | DB retention, backup, row growth, migration/cleanup risk | Source semantics or browser probing | Used for 18-month DB safety and retention review. |
| `reviewer` | Business-day rules, stale docs, regression risk | Bulk data collection | Used for holiday expansion and documentation drift review. |

## Backfill Policy

| Rule | Value |
| --- | --- |
| Scope | KRX OpenAPI stock/ETF/index daily snapshots only |
| Lookback | `550` days |
| Live batch size | `5` business dates |
| Delay | `3` seconds between endpoint requests |
| Backup | Before broad work and every 10 business dates or major boundary |
| Verify | `db-verify` after each live batch |
| Cleanup retention | `550` days while observation/backtest work is active |
| Partial endpoint guard | Very small nonzero endpoint row counts are treated as incomplete and re-planned for repair |
| Holiday guard | Built-in `2024~2026` KRX closure dates plus `STOCK_MONITOR_HOLIDAYS` additions |

## Current Stored Coverage

As of the latest verified baseline check:

| Table group | Range | Business dates | Rows |
| --- | --- | ---: | ---: |
| `reports` | `2026-01-02` ~ `2026-05-15` | 90 | 4,046 |
| `daily_stock_summaries` | `2026-01-02` ~ `2026-05-15` | 90 | 2,570 |
| `stock_market_daily` | `2024-11-08` ~ `2026-05-14` | 367 | 999,768 |
| `etf_daily_snapshots` | `2024-11-08` ~ `2026-05-14` | 367 | 331,347 |
| `market_index_daily` | `2024-11-08` ~ `2026-05-14` | 367 | 45,875 |
| `stock_investor_flow_daily` | `2026-01-05` ~ `2026-05-12` | 75 | 9,724 |
| `market_investor_flow_daily` | `2026-01-02` ~ `2026-05-12` | 87 | 1,131 |
| `investor_net_buy_top_daily` | `2026-01-02` ~ `2026-05-12` | 87 | 74,872 |

## Current Backfill Progress

| Item | Value |
| --- | --- |
| Analysis window | `2024-11-12` ~ `2026-05-15` |
| Business dates in window | 366 |
| Loaded KRX OpenAPI daily dates | 367 |
| Missing KRX OpenAPI daily dates | `2026-05-15` only, pending latest-day publication |
| Current earliest stock/ETF/index date | `2024-11-08` |
| Next dry-run candidate batch | `2026-05-15` after KRX Open API rows are available |

## Repeatable Commands

```powershell
python -m stock_monitor krx-baseline-analysis --lookback-days 550 --max-missing-dates 5
python -m stock_monitor db-verify
python -m stock_monitor db-backup --tag before_krx_18m_batch_YYYYMMDD_YYYYMMDD
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --dry-run
python -m stock_monitor krx-backfill-missing daily --lookback-days 550 --to-date YYYY-MM-DD --max-dates 5 --sleep-seconds 3 --confirm --i-backed-up
python -m stock_monitor db-cleanup --dry-run --retention-days 550
```

## P2 Completion Criteria

| Criterion | Status |
| --- | --- |
| Tool/agent/source comparison recorded | Done |
| 2024~2026 holiday guard in code/tests | Done |
| Repeatable baseline analysis command | Done |
| Partial nonzero KRX endpoint guard | Done |
| OpenAPI 18-month backfill completed through latest stored date | Done |
| Data Marketplace 18-month broad flow collection | Deferred; requires separate request-volume decision. The narrow `[12009]` same-day mentioned-stock 31-day path is the only approved automatic exception. |
| Public scoring/recommendation | Blocked |
