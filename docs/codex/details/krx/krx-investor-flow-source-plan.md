# KRX Investor Flow Source Plan

## Purpose

This document fixes the source boundary for investor-flow data discovered on `data.krx.co.kr`.
It is a planning and validation note, not an ingest implementation.

The goal is to add source-backed supply/demand context without mixing it into the existing Naver report tables.

## Confirmed KRX Data Marketplace Screens

| Priority | Screen | Screen No. | Role |
| --- | --- | --- | --- |
| P0 | 투자자별 거래실적(개별종목) | `[12009]` | Core stock-level flow for reported stocks. |
| P1 | 투자자별 거래실적 | `[12008]` | Market-wide investor background. |
| P1 | 투자자별 순매수상위종목 | `[12010]` | Discovery/ranking view for strong net-buy names. |

Confirmed navigation:

```text
기본 통계 > 주식 > 거래실적
```

Confirmed menu IDs from Chrome-extension validation:

| Screen | Menu ID | Screen title | Navigation status |
| --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | `MDC0201020301` | `[12008] 투자자별 거래실적` | Main page -> menu navigation succeeds. |
| `[12009] 투자자별 거래실적(개별종목)` | `MDC0201020302` | `[12009] 투자자별 거래실적(개별종목)` | Main page -> menu navigation succeeds; stock-name direct input plus `Enter` resolves the selector. |
| `[12010] 투자자별 순매수상위종목` | `MDC0201020303` | `[12010] 투자자별 순매수상위종목` | Main page -> menu navigation succeeds. |

Validation notes:

- Directly opening BLD-like URLs such as `MDCSTAT02201` is not the screen route. Use the menu IDs above for browser validation.
- The internal request BLDs remain separate from the browser route IDs and are still candidates until payload/response tracing is complete.
- `[12008]` and `[12010]` expose a `조회` control with default conditions after menu navigation.
- `[12009]` blocks query without stock selection and shows `개별종목을 검색해주세요`.
- The stock field accepts direct stock-name typing. Typing `삼성전자` and pressing `Enter` resolves the selector to `005930/삼성전자`; after that, `조회` returns the investor-flow table.
- Keep the direct-input flow as the browser-validation path. Programmatic ingest still needs a stable `stock_code` to KRX issue-code mapping before scheduled collection.

Browser validation guard for `[12009]`:

1. Inspect the visible page state first, not only hidden/internal form values.
2. If `개별종목을 검색해주세요` is visible, click the visible `닫기` button before typing or querying again.
3. Type the stock name into `tboxisuCd_finder_stkisu0_0`.
4. Press `Enter` and wait until the visible input resolves to `NNNNNN/종목명`.
5. Click `조회` only after the visible selector is resolved.
6. Treat a reappearing `개별종목을 검색해주세요` message as selector failure and do not proceed to data collection.

Pseudo flow:

```text
if visible_text includes "개별종목을 검색해주세요":
  click visible "닫기"
type stock name
press Enter
wait for visible input matching "\d{6}/"
if not matched:
  stop as unresolved stock selector
click "조회"
```

Observed `[12009]` columns:

| Group | Columns |
| --- | --- |
| 투자자구분 | 금융투자, 보험, 투신, 사모, 은행, 기타금융, 연기금 등, 기관합계, 기타법인, 개인, 외국인, 기타외국인, 전체 |
| 거래량 | 매도, 매수, 순매수 |
| 거래대금 | 매도, 매수, 순매수 |

## Source Decision

| Source | Status | Use |
| --- | --- | --- |
| KRX Open API approved daily endpoints | Implemented for price/volume/turnover snapshots | Market reference and exact-date stock/ETF/index context. |
| KRX Data Marketplace `[12009]` | Stage 4 source validation complete for two business dates | First source candidate for stock-level investor flow. |
| KRX Data Marketplace `[12008]` | Stage 4 source validation complete for two business dates | Market-wide flow background after `[12009]`. |
| KRX Data Marketplace `[12010]` | Stage 4 source validation complete for two business dates | Net-buy ranking/reference after `[12009]`. |
| Naver internal stock trend API | Confirmed but unofficial | Fallback or comparison source only. |
| KIS Developers | Deferred candidate | Use only if KRX Data Marketplace proves unsuitable or unstable. |

## API vs Screen-Based Collection Rule

| Data | Collection mode | Reason |
| --- | --- | --- |
| KOSPI/KOSDAQ daily stock price, volume, turnover | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| ETF daily trading data | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| KRX/KOSPI/KOSDAQ index daily data | KRX Open API | Approved API specs exist and ingest/backfill is implemented. |
| Stock basic metadata | KRX Open API, explicit only | Approved API specs exist, but it should not replace sector/theme labels until field meaning is reviewed. |
| Stock-level investor flow | KRX Data Marketplace `[12009]` | Not present in the approved Open API specs; screen contract must be followed. |
| Market-wide investor flow | KRX Data Marketplace `[12008]` | Not present in the approved Open API specs; screen contract must be followed. |
| Investor net-buy ranking | KRX Data Marketplace `[12010]` | Not present in the approved Open API specs; screen contract must be followed. |

Rules:

1. Use KRX Open API whenever the approved API provides the needed data.
2. Use KRX Data Marketplace only for data absent from the approved Open API specs.
3. For screen-based data, preserve the screen conditions exactly: query type, stock selection, date range, market filter, investor category, share unit, and money unit.
4. Store `source='krx_open_api'` and `source='krx_data_market'` separately.
5. Do not implement scheduled screen-based ingestion until a dry-run command can print the exact normalized rows and source units.

## Collection Timing

| Environment | Recommended time | Reason |
| --- | --- | --- |
| Main desktop validation | `16:50` KST or later | KRX/Data Marketplace values may lag by about 20 minutes. |
| Future N100 always-on host | `18:30~19:30` KST | Safer after close and possible NXT-related timing noise. |

## Historical Range Decision

Use different windows for different data layers.

| Layer | Default analysis window | Storage target | Reason |
| --- | ---: | ---: | --- |
| KRX Open API stock/ETF/index daily snapshots | 3 months | 6 months | Price, volume, turnover, and index context are low-risk API data and already small enough in SQLite. |
| KRX Data Marketplace stock-level investor flow `[12009]` | 20 trading days first, then 3 months | 6 months after stable validation | Screen-backed source is more fragile and session-dependent, so collect only leadership candidates, not every report stock. |
| KRX Data Marketplace market-wide investor flow `[12008]` | 3 months | 6 months | Low request volume by market/date and useful as background context. |
| KRX Data Marketplace net-buy ranking `[12010]` | 3 months | 6 months | Useful discovery/reference data, but should remain descriptive. |
| Old Naver report backfill | Not a priority | Keep newly collected reports indefinitely for now | Historical reports before this project's collection start are lower value than price/flow context. |

Recommended investor-flow backfill shape:

1. Validate one live day first with `[12009]`, `[12008]`, and `[12010]`.
2. Backfill `[12009]` only for leadership-candidate or same-day report-mentioned stock/date pairs, not all listed stocks.
3. For follow-up analysis, add candidate date `D` and next business day `D+1` only after the same-day path is stable.
4. Start with the latest 10 business days or currently stored report dates, then expand to 3 months.
5. Do not expand to 6 months until response shape, units, retry behavior, duplicate handling, and candidate-selection rules are proven.

Current operating estimate as of `2026-05-09`:

| Existing data | Count |
| --- | ---: |
| Stored reports | 777 |
| Stored report business dates | 9 |
| Distinct report stock codes | 249 |
| Distinct report stock-date keys | 344 |
| Stored KRX Open API daily snapshot dates | 47 |

Implication: even report-related stock-date keys are only the upper bound.
`[12009]` stock-level flow should be narrower: collect only leadership candidates selected from report signal, price/turnover signal, sector/theme concentration, and `[12010]` net-buy ranking overlap.
It is not feasible or necessary to crawl all stocks or every report stock for every historical date.

## Leadership Candidate Policy

`[12009]` should answer "is this leading/interesting name receiving investor flow?" rather than "collect flow for every report row."

Candidate sources:

| Signal | Source | Candidate rule |
| --- | --- | --- |
| Report concentration | Naver reports / daily summaries | Multi-report names, target-bearing reports, or names in the day's concentrated sector/theme. |
| Price/turnover attention | KRX Open API daily snapshots | Names with high turnover, high volume, or strong same-day movement among currently observed stocks. |
| Investor ranking overlap | `[12010]` net-buy top | Names appearing in foreign/institution/individual net-buy top lists. |
| Market context | `[12008]` market investor flow | Use only as a background label, not as a stock selector by itself. |
| Manual watch | Operator search/memo | Optional one-off candidate, useful during validation. |

Initial candidate rule:

1. Build a daily candidate set from filtered daily summaries, not raw reports.
2. Add candidates that overlap with `[12010]` top net-buy lists after `[12010]` is validated.
3. Add high-turnover/high-volume names from KRX snapshots only when they appear in a report sector/theme or operator watch context.
4. Cap `[12009]` stock-level flow calls per day until the source is stable.
5. Store why each candidate was selected, for example `report_multi`, `target_present`, `sector_concentration`, `top_net_buy_overlap`, `operator_watch`.

Current implemented preview:

| Signal | Implemented in `krx-flow-candidates` |
| --- | --- |
| Filtered daily summary | Yes; uses effective minimum mention count and target-price-required settings. |
| Buy opinion | Yes. |
| Sector concentration | Yes; top sector rollups from stored Naver sector metadata. |
| KRX turnover rank | Yes; top 30 same-date KRX turnover snapshot. |
| KRX same-date movement | Yes; absolute change percent of at least 3%. |
| `[12010]` net-buy overlap | Not yet; add after `[12010]` live response is validated and stored. |
| Manual watch | Not yet; add after operator watchlist storage exists. |

Do not use these as candidates by default:

- every one-report stock
- every no-target-price stock
- every stock in a reported sector/theme
- every top-turnover stock in the full market
- every stock from `[12010]` without a report, sector/theme, or operator-watch reason

## Collection Priority And Guardrails

| Priority | Scope | Source | Collection rule | Why |
| --- | --- | --- | --- | --- |
| P0 | One stock/date smoke test | `[12009]` | Use `--request-only`, then live dry-run with one known stock such as `005930` | Confirms `stock_code -> isuCd -> params -> response rows`. |
| P0 | Leadership candidates for the current day | `[12009]` | After close, collect only stocks that passed the leadership candidate rule | Gives the highest signal with bounded requests. |
| P1 | Same leadership candidates on `D+1` | `[12009]` | Add only after same-day collection is stable | Supports the planned follow-up/interest observation without crawling broadly. |
| P1 | Market background by KOSPI/KOSDAQ | `[12008]` | One row set per market/date after close | Helps interpret whether flow was broad-market or stock-specific. |
| P1 | Top net-buy names by investor category | `[12010]` | Foreign/institution/individual, KOSPI/KOSDAQ, after close | Helps discover whether report names overlap with strong net-buy names. |
| P2 | 3-month scoped backfill | `[12009]`, `[12008]`, `[12010]` | Small batches only after backup/verify and live-day validation | Useful for web-view trend context; not required for Telegram MVP. |
| Blocked | Whole-market stock-level flow | `[12009]` | Do not run | Too many requests, fragile source, low immediate value. |

Operational cautions:

- Always run `db-verify` and `db-backup` before real investor-flow backfill.
- Use request previews before live calls:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
```

- Keep screen-backed calls in small batches. Start with 5 business dates or fewer, and sleep between calls.
- Treat `LOGOUT`, validation popups, missing stock selectors, or changed units as a hard stop for DB writes.
- Preserve raw units and normalized numeric values separately.
- Do not infer "주도 섹터" from investor flow alone. Show it as `수급 참고` until enough history and transparent rules exist.

## Login Session Operating Policy

Assumption from operator validation: KRX Data Marketplace login sessions are short-lived, roughly 30 minutes.

For scheduled investor-flow collection, do not rely on an old browser/login session.
The preferred source-validation model is local `.env` raw login: the process warms up KRX, posts the Data Marketplace login form with local credentials, then calls the representative JSON endpoint using an in-memory cookie jar.
This avoids browser-session fragility and does not persist cookies, headers, or credentials outside local `.env`.

Browser control policy:

- Prefer raw `.env` login for repeatable Data Marketplace JSON validation.
- Use the connected Chrome extension browser only for UI fallback/debug validation because it can use the operator's real Chrome login/session state.
- Use the Codex in-app browser only for simple read-only inspection, local UI checks, or fallback when Chrome extension control is unavailable.
- Do not mix browser surfaces during one validation run unless the operator explicitly asks for a fallback; otherwise session assumptions become ambiguous.

| Step | Timing | Action |
| --- | --- | --- |
| 1 | Before planned flow dry-run/collection | Run `krx-flow-login-check --date YYYY-MM-DD` to verify raw `.env` login and a representative `[12008]` JSON endpoint. |
| 2 | If login-check passes | Continue only with validation/dry-run work; do not treat this as scheduled ingest approval. |
| 3 | If login-check fails with `auth_rejected` or `LOGOUT` | Fall back to manual Chrome validation or notify the operator. Do not write investor-flow rows. |
| 4 | If browser fallback is used | Operator logs in on the single Chrome-extension-controlled KRX tab, then `/체크 로그인` records acknowledgement only. The next dry-run still decides the real connection verdict. |

Implementation boundary:

- Do not auto-store or expose Data Marketplace credentials through `admin-gui`, `web-view`, Telegram, or docs.
- Automatic raw login may use only the local `.env` keys and must not save cookies, headers, password dumps, or browser profile state.
- `StockMonitor-KrxFlowLoginReminder` is a reminder-only scheduler task, separate from actual flow collection. It sends Telegram only and should not use `--open-browser`.
- Actual source-backed flow ingestion must remain disabled until separate explicit approval.
- `/체크 로그인` must not be treated as proof that the Data Marketplace HTTP endpoint is authenticated. It means the operator completed the remote Chrome login step; the following dry-run decides whether the connection is really usable.
- To avoid duplicate tabs during manual validation, Codex should open one Chrome-extension-controlled KRX tab first, and the operator should log in on that same tab. Do not open another normal Chrome tab with `Start-Process` unless Chrome extension control is unavailable.

Raw login check:

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

Reminder command for browser fallback:

```powershell
python -m stock_monitor krx-flow-login-reminder --minutes-before 5 --planned-time 16:50
```

Dry-run:

```powershell
python -m stock_monitor krx-flow-login-reminder --minutes-before 5 --planned-time 16:50 --dry-run
```

Request preview without login/network:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
```

Use `--request-only` before live Data Marketplace calls to confirm that stored KRX metadata resolves the 6-digit stock code to the expected `isuCd` and request params.

Leadership candidate preview without login/network:

```powershell
python -m stock_monitor krx-flow-candidates --date 2026-05-08 --limit 10
```

Use `krx-flow-candidates` before `[12009]` calls. It reads local daily summaries, sector metadata, and KRX price/turnover snapshots, then prints the narrowed stock list and per-stock `--request-only` command.

## Observed `[12009]` Screen Conditions

Observed after logging in through the Chrome extension-connected KRX Data Marketplace tab.

| Condition | Observed value / behavior | Implementation note |
| --- | --- | --- |
| Screen no. | `[12009]` | `투자자별 거래실적(개별종목)` |
| Navigation | `기본 통계 > 주식 > 거래실적` | Keep this in source docs for future manual verification. |
| Query type | `기간합계`, `일별추이` radio options | Preserve the chosen query type in request params and saved metadata. |
| Stock selector | `주식 종목 검색`; typing a stock name and pressing `Enter` resolves to selected display example `005930/삼성전자` | Browser validation can use direct name input; fetch should use a stable code/ISIN param after request contract tracing, not display text alone. |
| Date range | `strtDd`, `endDd` inputs | Use KST business dates; for daily flow prefer one date at a time first. |
| Share unit | `주`, `천주`, `백만주` style selector | Store unit explicitly; prefer raw `주` if available. |
| Money unit | `원`, `천원`, `백만원`, `십억원` style selector | Store unit explicitly; prefer raw `원` if available. |
| Rows | investor-type rows | Preserve detailed investor rows and derive foreign/institution/individual summary separately. |

Additional live screen validation on `2026-05-09`:

| Screen | Validation | Result |
| --- | --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Chrome extension-connected KRX Data Marketplace tab, stock `329180/HD현대중공업`, date range `20260430~20260508`, query clicked after stock selector resolution | Visible table rendered investor rows with `거래량` and `거래대금` split into `매도`, `매수`, `순매수`. |
| `[12009]` stock selector | Numeric stock-code search worked when Korean text input through the extension was unreliable | Keep automated validation code tolerant of stock selector popup text such as `개별종목을 검색해주세요`; close it before retrying selection. |
| Raw HTTP response | Not captured in this validation pass | Parser aliases and DB migration remain a controlled draft until direct endpoint response samples are verified. |
| Saved raw sample path | `krx-flow-dry-run --sample-file <json>` | Normalizes a saved Data Marketplace JSON payload without login, network call, or DB write. Use this for DevTools/browser-captured samples before scheduled ingest. |
| Saved sample manifest | `krx-flow-dry-run --sample-manifest <json>` | Stores sample file, screen, date, stock/market/investor filters, and units together so validation can be repeated without relying on memory. |
| Manifest scaffold | `--manifest-output <json>` | Writes a local manifest scaffold from CLI conditions; no login, network call, or DB write. |
| Capture-set scaffold | `krx-flow-sample-scaffold --date YYYY-MM-DD --stock-code STOCKCODE` | Writes `[12009]`, `[12008]`, and `[12010]` manifest scaffolds together for a capture date. Use `--from-candidates` to populate `[12009]` stocks from local preview signals. |
| Capture checklist | `krx-flow-capture-checklist --manifest-dir data\krx_samples` | Prints screen, condition, raw filename, manifest path, and validation command for each manifest. |
| Normalized artifact | `--normalized-output <json>` | Writes normalized validation output to a local JSON artifact; still no DB write. |
| Strict sample validation | `--strict-sample` | Returns exit code `2` when raw rows or normalized rows are suspicious. Use before treating a sample as an ingest reference. |
| Sample coverage status | `krx-flow-sample-status --manifest-dir data\krx_samples` | Reports whether `[12008]`, `[12009]`, and `[12010]` manifests and raw files are present, including next capture filenames. No login, network call, or DB write. |
| Batch sample validation | `krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized` | Validates all local manifests with strict sample rules and can write normalized artifacts; still no login, network call, or DB write. |
| Import preview | `krx-flow-import-preview --manifest-dir data\krx_samples` | Computes target investor-flow table row counts from local manifests; still no DB write. |
| Guarded manual import | `krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated` | Upserts warning-free local samples into investor-flow tables. Scheduled ingest remains disabled. |
| Expected sample coverage | `expected_min_rows`, `expected_min_normalized_rows`, `expected_investors` | Manifest expectations for minimum coverage and required investor rows. |
| Unit override | `--volume-unit`, `--amount-unit` | Preserve the visible KRX screen unit in normalized rows; do not infer or scale values silently. |

## Request Contract Candidates

These are implementation candidates derived from KRX Data Marketplace screen observation and the public `pykrx` wrapper source.
They are not yet project-ingest contracts.
Before adding migrations or scheduled collection, verify them with a local dry-run command that prints request conditions, raw row counts, normalized rows, and units without DB writes.

| Screen | Query | Candidate BLD | Candidate params | Notes |
| --- | --- | --- | --- | --- |
| `[12008] 투자자별 거래실적` | 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02201` | `strtDd`, `endDd`, `mktId`, `etf`, `etn`, `elw` | Market-wide investor background. |
| `[12009] 투자자별 거래실적(개별종목)` | 기간합계 | `dbms/MDC/STAT/standard/MDCSTAT02301` | `strtDd`, `endDd`, `isuCd` | First target for report-stock investor flow. |
| `[12009] 투자자별 거래실적(개별종목)` | 일별추이 | `dbms/MDC/STAT/standard/MDCSTAT02302` | `strtDd`, `endDd`, `isuCd`, `trdVolVal`, `askBid` | Useful after period aggregate is stable. |
| `[12010] 투자자별 순매수상위종목` | 순매수상위 | `dbms/MDC/STAT/standard/MDCSTAT02401` | `strtDd`, `endDd`, `mktId`, `invstTpCd` | Ranking/reference source by investor category. |

Observed control fields from Chrome-extension validation:

| Screen | Observed controls | Immediate status |
| --- | --- | --- |
| `[12008]` | `inqTpCd`, `mktId`, disabled `segTpCd`, optional `etf`/`etn`/`elw`, `strtDd`, `endDd`, `share`, `money`, `search` | Default search button is reachable. |
| `[12009]` | `inqTpCd`, stock search input `tboxisuCd_finder_stkisu0_0`, `strtDd`, `endDd`, `share`, `money`, `search` | Direct stock-name input plus `Enter` resolves to `005930/삼성전자`; missing stock still shows validation dialog. |
| `[12010]` | `mktId`, disabled `segTpCd`, `invstTpCd`, `strtDd`, `endDd`, `share`, `money`, `search` | Default search button is reachable. |

Candidate parameter meanings:

| Param | Meaning | Candidate values |
| --- | --- | --- |
| `mktId` | Market filter | `STK`, `KSQ`, `ALL` |
| `trdVolVal` | Trend value type | `1` 거래량, `2` 거래대금 |
| `askBid` | Sell/buy/net-buy selector | `1` 매도, `2` 매수, `3` 순매수 |
| `invstTpCd` | Investor category for `[12010]` | `1000` 금융투자, `2000` 보험, `3000` 투신, `3100` 사모, `4000` 은행, `5000` 기타금융, `6000` 연기금, `7050` 기관합계, `7100` 기타법인, `8000` 개인, `9000` 외국인, `9001` 기타외국인, `9999` 전체 |

Important implementation risk:

- `[12009]` candidate params use `isuCd`, which appears to be an ISIN-style issue code rather than the 6-digit stock code.
- Do not call `[12009]` directly from `stock_code` until a 6-digit code to `isuCd` mapping is confirmed from approved KRX metadata or a Data Marketplace lookup response.
- If the dry-run cannot reproduce the screen output without session-specific or hidden browser state, keep this as a manual validation source and do not add scheduled ingestion.
- For UI login fallback, prefer the direct `login.jsp?site=mdc` page over the wrapper iframe page. Browser UI login is for validation/debug only; the `.env` raw fetch path is the standard sample-capture path while credentials remain local-only.
- Do not automate Chrome saved-password, PIN, Windows Hello, or other OS/native security prompts. These remain manual operator actions.

## Initial Data Model Candidates

Migration v4 now contains these tables with repository upsert/list tests.
The operating DB may have the additive tables, but scheduled ingestion must remain disabled until separate explicit approval.

```text
stock_investor_flow_daily(
  business_date,
  stock_code,
  investor_type,
  sell_volume,
  buy_volume,
  net_buy_volume,
  sell_amount,
  buy_amount,
  net_buy_amount,
  volume_unit,
  amount_unit,
  source,
  fetched_at,
  primary key (business_date, stock_code, investor_type, source)
)

market_investor_flow_daily(
  business_date,
  market,
  investor_type,
  sell_volume,
  buy_volume,
  net_buy_volume,
  sell_amount,
  buy_amount,
  net_buy_amount,
  volume_unit,
  amount_unit,
  source,
  fetched_at,
  primary key (business_date, market, investor_type, source)
)

investor_net_buy_top_daily(
  business_date,
  market,
  investor_type,
  rank,
  stock_code,
  stock_name,
  net_buy_volume,
  net_buy_amount,
  source,
  fetched_at,
  primary key (business_date, market, investor_type, rank, source)
)
```

## Implementation Order

| Order | Work | Output |
| ---: | --- | --- |
| 1 | Trace `[12009]` request contract | Done as candidate: `MDCSTAT02301` period aggregate and `MDCSTAT02302` trend. |
| 2 | Add dry-run fetch for one stock/date | `krx-flow-dry-run` added; no DB writes; `--request-only` validates `stock_code -> isuCd -> params` without login/network. |
| 3 | Add migration for investor-flow tables | Done as additive schema v4 with repository upsert/list tests and `db-verify` quality checks; operating tables are empty until ingest is explicitly added. |
| 4 | Fetch report-stock flow only | Start with stocks that appeared in Naver reports; avoid broad all-stock crawling. |
| 5 | Trace `[12008]` and `[12010]` | Stage 4 live/raw parity is complete for two business dates; scheduled ingest still requires separate Stage 6 design. |
| 6 | Add read-only web-view cards | Done for manually imported rows: daily context exposes market flow and net-buy top references, and stock detail exposes stock-level investor rows. Labels remain descriptive only. |
| 7 | Review several weeks | Decide later whether rotation/interest alerts are defensible. |

## Guardrails

- Keep these tables separate from `reports`, `daily_stock_summaries`, and KRX Open API snapshot tables.
- Store `source='krx_data_market'` for Data Marketplace-derived rows.
- Do not call this public numeric scoring, trading recommendation, or confirmed rotation. It may support observation-candidate ordering only with other stored evidence.
- Display as `수급 참고`, `외국인 순매수`, `기관 순매수`, or `후속 확인 필요`.
- `web-view` may show manually imported investor-flow rows as read-only reference data, but must not expose Data Marketplace credentials, raw request internals, scheduler state, DB paths, or control endpoints.
- Do not crawl the whole market first; start with leadership candidates plus market/top-ranking screens.
- Run collection after the data delay window, not immediately at the regular market close.
- Preserve source units because KRX screens can switch between shares/thousand shares and KRW/thousand/million/billion KRW.
- If a screen condition cannot be reproduced programmatically, stop at manual validation and do not silently approximate it.
- Use [krx-flow-sample-capture-runbook.md](/docs/codex/details/krx/krx-flow-sample-capture-runbook.md) and `data/krx_samples/templates/*.json` before promoting any raw sample to an ingest reference.
- Use [krx-investor-flow-schema.md](/docs/codex/details/krx/krx-investor-flow-schema.md) as the table contract and `db-verify` quality gate reference before enabling any scheduled ingest.

Dry-run commands:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view market --date 2026-05-08 --market STK --value amount --side net-buy --show-first-row
python -m stock_monitor krx-flow-dry-run --view top --date 2026-05-08 --market STK --investor foreign --show-first-row
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --request-only
python -m stock_monitor krx-flow-candidates --date 2026-05-08 --limit 10
```

If `krx_stock_metadata` has no `standard_code` for the stock, either fetch basic metadata first or pass `--isu-cd` explicitly:

```powershell
python -m stock_monitor krx-fetch-snapshot stock-kospi-basic --date 2026-05-08
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --show-first-row
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --sample-file data\krx_samples\12009_005930_20260508.local.json --volume-unit 주 --amount-unit 원 --show-first-row
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --stock-code 005930 --market STK --top-investor foreign
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --from-candidates --candidate-limit 5 --market STK --top-investor foreign
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 005930 --manifest-output data\krx_samples\12009_005930_20260508.manifest.local.json
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --normalized-output data\krx_samples\12009_005930_20260508.normalized.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_005930_20260508.manifest.local.json --normalized-output data\krx_samples\12009_005930_20260508.normalized.local.json --strict-sample --show-first-row
python -m stock_monitor krx-flow-capture-checklist --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized
python -m stock_monitor krx-flow-import-preview --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

KRX Data Marketplace can return `LOGOUT` without a logged-in session.
For dry-run validation only, credentials may be provided through local `.env` keys:

```env
STOCK_MONITOR_KRX_DATA_MARKET_ID=
STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD=
```

Keep these separate from `STOCK_MONITOR_KRX_AUTH_KEY`.
Do not print them, store them in docs, or expose them through `admin-gui` or `web-view`.
