# Data Quality Checklist

## Purpose

This checklist prevents future changes from mixing raw source values, aggregate values, and presentation values.
Use it before changing parser, summary, Telegram, admin-gui, or web-view behavior.

## Core Rule

Missing or non-actionable source values are not data points.

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
| Approved real-time reference | Keep in a separate read-only lane until source burden, permissions, freshness, and failure behavior are verified. | Future Toss Securities Open API quote/turnover reference for top-2 `우선 확인`. |
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
Check docs/codex/data-quality-checklist.md before proposing or implementing changes.
Verify raw/source, parsed/storage, aggregate, and display semantics separately.
Call out any N/A/NULL/duplicate-display risk explicitly.
```

## Required Test Pattern

New changes touching data interpretation should include at least one of:

- parser test with `N/A`, `NA`, `NULL`, `NONE`, `-`, or blank input
- summary test where missing target/opinion does not affect range or dominant label
- formatter/web-view test where detail still exposes missing fields as `목표가 -` / `의견 없음`
- duplicate-display test or explicit assertion that summary/detail roles are separated
