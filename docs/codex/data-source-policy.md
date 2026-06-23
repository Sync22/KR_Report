# Data Source Policy

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
| Stock price, close, change, volume, turnover, market cap | KRX Open API | `stock_market_daily`, `krx_context`, stock detail DTOs | KRX is the preferred source. Do not replace with Naver quotes unless explicitly marked as temporary. |
| Stock master, market, listed shares, listing metadata | KRX Open API | `krx_stock_metadata` | KRX should become the canonical stock master. |
| ETF daily reference | KRX Open API | `etf_daily_snapshots`, `etf-trend` DTO | KRX only. Keep separate from company-report summaries. |
| Market index reference | KRX Open API | `market_index_daily` | KRX only. |
| Investor flow | KRX Data Marketplace | `stock_investor_flow_daily`, `market_investor_flow_daily`, `investor_net_buy_top_daily` | KRX Data Marketplace is the validation source. Scheduled ingest remains disabled until separate approval. |
| Intraday quote/turnover reference | Naver market-top overlap, bounded Naver top-two quote, and approved Toss Securities OpenAPI current-price reference | `web-view` top-2 priority DTOs and Toss baseline table when saved | Read-only observation support for the server-derived top-two `우선 확인`: market-top overlap and direct candidate quotes are shown separately with source/time. It may affect observation priority/main-card emphasis, but not trading-decision support, broker execution, or public trading calls. |
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
| `시장 참고` | KRX market reference | Price, volume, turnover, ETF, index, investor-flow reference. | Must be labeled as stored KRX data. |
| `장중 참고` | approved intraday source | Naver market-top overlap, bounded server-derived top-two Naver quote, and future quote/turnover/index references. | Must show source/freshness. Market-top non-overlap is a scope result, not an absent-price result. It may affect observation priority only as observation support. |
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
- Do not treat `read-only` as `ordering-disabled`. A verified source can affect `관찰 우선순위`. The approved exception to the default no-automation rule is the bounded `scheduled-market-briefing-slot` path at `09:15`, `12:00`, and `15:15`: after its delivery/time guards pass, it may collect and save news observations only for the server-derived current top two candidates, then project compact source-labelled results into that same Telegram briefing. It must not broaden the target universe, expose raw operator payloads, persist Toss/Naver quotes, emit a standalone alert, expose broker secrets, add a public score, create a trading call, or route an order.
- Do not treat the public trading-wording ban as a permanent ban on operator decision support. If real-time data later makes trading review viable, document it as a separate operator-only decision-support/execution-lab source lane before any public or execution behavior.
