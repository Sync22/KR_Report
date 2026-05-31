# Next Phase

## Purpose

This document defines the next execution phase from the current project state.

It is not a new product wishlist. It is the practical next set of work axes after the current Telegram/admin/web-view/KRX foundation.

## Current Baseline

`2026-05-29` read-only readiness is the current main-PC planning baseline. `next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json` reports `completion_ready=false` without DB writes, Telegram sends, scheduler registration, public scoring, or recommendation output. Latest stored report date remains `2026-05-15`. Market-briefing previews are ready for 5/5 recent dates and public-safe issue count is 0, but manual review sends are `0/3` and `market_briefing_phone_review_accepted=false`. KRX Open API daily snapshots are missing for 6 publishable business dates starting `2026-05-28`. `market-day-observation --date 2026-05-29 --json` is incomplete with all expected scheduled-run evidence missing after verify times. `web-view` Startup fallback is not configured because the current-user `StockMonitor-WebView.lnk` shortcut is missing and local `/health` is unavailable. External provider smoke is not recorded on this PC.

## Direction Reset

Recent review found that several memo ideas were implemented as safe data foundations while drifting away from the intended user experience. The next phase should favor compact daily-use output over more intermediate process.

| Principle | Next-phase Rule |
| --- | --- |
| Start rough, then refine | A useful daily briefing or compact web section can ship as `참고` before the analytics are perfect. |
| Separate intent completion from foundation completion | A table, DTO, or DB path is not enough to mark a memo done if the intended screen or briefing is still missing. |
| Compress the shared page | Friend-facing `web-view` should not expose the full validation pipeline or repeated defensive disclaimers. Keep raw evidence, risk wording, and operational details in admin/docs. |
| Separate trading advice from observation curation | This project does not provide `매수 추천`, `매도 추천`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, or `투자등급`, but it can recommend what to observe first. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `확인 후보`, `시장 분위기`, `수급 참고`, and `과열 참고` are valid product language. |
| Do not turn the current public limit into a permanent goal | The current public `web-view` and Telegram surfaces do not provide trading decisions because real-time data, source freshness, permission, failure handling, and execution safety are not ready. The long-term path can include an operator-only decision-support lane and later execution-lab after those gates are proven. |
| Keep broker/API work outside production | Do not add KIS, Toss Securities Open API, or any broker route to close current intraday gaps. Future Toss work should start only as a separated `broker-lab`/`execution-lab`/`toss-openapi-lab` path, beginning with docs and permission review, then read-only quote/account/balance probes. Once verified, intraday quote/turnover context may drive observation priority, but not trading execution. |
| Add closing-market briefing track | The next product axis includes a rough `16:00` market mood Telegram summary based on same-day reports, KRX market data, and available flow. |

## Observation Evidence Maturity Direction

The next candidate-evidence work should improve judgment quality, not visible label volume.

| Step | Goal | Implementation gate |
| --- | --- | --- |
| 1 | Make top candidates explainable by visible public evidence. | Public ordering must be justified by `why_notable` / `evidence_layers.primary`, not hidden diagnostics or support-only facts. |
| 2 | Strengthen current-regime context. | Use exact-date KRX, `[12009]` flow, and 52-week/1-year price-volume context as support; do not turn them into public scores. |
| 3 | Prepare future intraday lane separately. | Top-2 `우선 확인` 5-minute read-only probing belongs in lab/staging only after source burden and permission review; when proven stable, it should affect observation ordering and main-card emphasis. |
| 4 | Prepare an operator-only decision-support boundary only after real-time evidence is stable. | This is where trading-decision review may begin. It must not be collapsed into public `web-view`, Telegram alerts, or broker execution. |

Stop rule: do not add a new label, counter, card, or readiness field unless it clarifies a top-level evidence category, blocks misleading ordering, exposes a real missing-data gap, or keeps dense/mobile UI readable.

| Area | Baseline |
| --- | --- |
| MVP operation | Runnable. Scheduled poll/notify/Telegram worker paths exist and are under live validation. |
| Requirements anchor | `stock_research_monitor_mvp.md` now reflects the current product scope, not only the initial Telegram MVP memo. |
| Admin surface | `admin-gui` is local/operator-only and control-capable. |
| User surface | `web-view` is separate, GET-only, and friend-facing candidate. |
| Market data | KRX stock/ETF/index snapshots exist from `2024-11-08` through `2026-05-19` on the main-PC DB after the guarded `2026-05-20 09:17 KST` `2026-05-19` repair pass. Same-day `2026-05-20` remains missing/not_published in storage as expected because KRX Open API daily rows are officially published on the next Korean business day at `08:00` KST; it must not be treated as an intraday KRX OpenAPI source. |
| Investor flow | KRX Data Marketplace validation/import/display paths exist and stored rows cover through `2026-05-12`. The only approved automatic path is narrow: anchor-date report-mentioned stocks, `[12009]` only, recent 31-day window. Broad scheduled ingest stays disabled. |
| Access gate | Optional local entry-code gate exists for both `admin-gui` and `web-view`. |
| Analytics | Candidate evidence, target progress, read-only backtest observation, and internal scoring-draft CLIs exist. Public trading recommendations and scored investment decisions are blocked, while observation-candidate recommendation and evidence-based ordering are allowed. |

## Completion Baseline

| Scope | Completion | Practical Meaning |
| --- | ---: | --- |
| Domestic MVP on the current main PC excluding broad public sharing and US expansion | 85-90% | Code, DB, and read-only preview foundations are usable, but this PC is not closeout-ready. The active blockers are manual market-briefing review sends `0/3`, `market_briefing_phone_review_accepted=false`, KRX Open API daily snapshots missing for 6 publishable business dates starting `2026-05-28`, real `2026-05-29` market-day scheduled-run observation, external provider smoke for the final shared URL, and current-user `web-view` Startup fallback configuration. |
| Domestic MVP including public trading recommendation or public scored investment decisions | 75-80% | Public numeric scoring, investment grades, and trading calls are not ready. This is a separate non-goal from observation-candidate recommendation. |

| Axis | Completion | Next Work |
| --- | ---: | --- |
| Telegram / daily briefing | 80-85% | The market-briefing preview is public-safe for recent stored dates, but this main-PC DB has manual review sends `0/3` and `market_briefing_phone_review_accepted=false`; do not schedule or auto-send until those gates are closed. |
| Scheduler / operations | 75-80% | This main PC is still a desktop-validation host. `market-day-observation --date 2026-05-29 --json` is incomplete and shows missing evidence for TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill. Do not register new market-briefing or KRX probe scheduler tasks until read-only evidence and operator review justify it. |
| DB / KRX Open API baseline | 90-95% | `db-verify` is clean and snapshots cover through `2026-05-19`, but the current baseline reports 6 missing publishable KRX Open API daily snapshot dates starting `2026-05-28`. Keep the next-business-day `08:00` publication rule and do not treat KRX OpenAPI as real-time intraday data. |
| User web-view | 88-92% | Stored-data `time_slot_mood_card` and value QA are working, but external provider smoke is not closed on this PC and Startup fallback is not configured because the current-user shortcut is missing. |
| Admin GUI | 82% | Improve operator status/settings/log readability after live use. |
| KRX flow / ETF references | 88% | Expand only with guarded/manual policy until scheduled flow ingest is separately approved. |
| Observation curation / scoring draft | 84% | Stored evidence now drives a clearer `오늘의 관찰 후보` ordering and a top-2 `우선 확인` shortlist while keeping public numeric scores, grades, and trading calls blocked. |

## Phase A: Operational Closeout

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Live scheduled-run validation | Observe Notify, Poll, TelegramCommands, KRX login reminder, and Shutdown over real market days. | Failures are explainable through `live_observation`, operation events, worker heartbeat, scheduler classification, delivery logs, or Telegram `ambiguous_send` fragment traces. |
| DB health discipline | Keep `db-verify`, `db-backup`, restore-smoke, cleanup dry-run, and KRX backfill confirmation flow active. | No unverified bulk DB work. |
| Daily summary safety | Keep fragment resume and late-notify guard validated. | No duplicate production summary from routine retries. |
| Intraday outbox safety | Continue retry/outbox checks. | Failed intraday batch can resume or report status clearly. |
| Naver parser drift fixtures | Save real snapshots with `inspect-page --save-fixture PATH --require-parsed-reports` when Naver page/API shape looks suspicious, then recheck saved files with `naver-fixture-validate PATH`. | Parser drift can be reproduced from a stored fixture, and empty/drifted captures fail immediately instead of becoming a false baseline. |

## Phase B: User Web-View Closeout

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Product reset | Recenter the page on `날짜별 브리핑 -> 눈에 띄는 업종/종목 -> 선택 종목 근거 -> 필요한 시장 참고`. | The page can be understood without reading raw validation/process tables. |
| Search bar | Selected-date top-right stock search is implemented. Keep it stable; add cross-date search only if same-date lookup proves insufficient. | User can search by stock name/code without Telegram on the selected date. |
| Display cleanup | Keep reducing operator-facing wording and over-dense blocks. | Friend page reads as information view, not admin/debug page. |
| Top briefing alignment | Keep `오늘 읽을 요약` aligned with the Telegram briefing axes: report flow, index, turnover, flow, and notable stocks. | The shared page starts with a compact daily briefing instead of category/debug-heavy context. |
| Value QA | Continue checking selected dates with web-view value QA and browser review. | Units, missing values, sort direction, and section density are explainable. |
| Mobile QA | Verify calendar, daily summary, selected stock, report list, and market reference on narrow width. | No major overflow or broken tab behavior. |
| Public-safe regression | Maintain GET-only and no-admin-data tests. | `/api/status`, scheduler, settings, secrets, DB paths remain absent. |

Current implementation note (`2026-05-16`, updated `2026-05-18`): `web-view-browser-smoke` now provides a local read-only Playwright browser smoke check for the friend-facing `web-view`. It starts a temporary loopback-only server, checks desktop `1366x900`, tablet `768x1024`, large mobile `430x932`, and mobile `390x844` rendering, verifies required daily briefing/search/tab elements, clicks the observation tab, checks horizontal overflow, confirms `GET` JSON APIs for daily/candidate/stock-detail, confirms `POST /api/daily/YYYY-MM-DD` returns `405`, and confirms `/api/status` stays absent. When the access-code gate is enabled, the default smoke run uses a temporary non-existent access-code path only for this local server so no access-code value is requested or printed; use `--respect-access-code` only when deliberately testing the configured gate. Latest mini PC smoke over `2026-05-15` returned issue count `0`.

IA/performance note (`2026-05-18`, updated `2026-05-29`): the page now uses five task tabs. `메인` owns daily briefing and top-2 priority overview; `관찰` owns `오늘의 관찰 후보` plus read-only reaction rows; `종목` owns selected-stock context and reports; `시장` owns stored KRX market reference and recent investor-flow trend; `순환매` owns category/theme/ETF rotation context. Hidden tab payloads are lazy-loaded, and the daily DTO no longer embeds the heavier `candidate_evidence` payload. Candidate cards render only user-facing `왜 눈에 띄는지` and `부족한 정보`, while raw `quality_flags` remain a DTO/testing/admin concern.

Performance closeout note (`2026-05-19`): the public `web-view` no longer renders the operator-facing `주기 데이터 점검` block or ships `periodic_data_needs` in the daily DTO; the CLI audit path remains available for operation review. Public-safe GET JSON routes now have a short in-process 30-second cache, archive category mapping is batched across archive dates, and daily snapshot generation reuses recent KRX/flow date lookups plus the already-built market briefing for one-line comments. The latest mini PC measurement puts archive generation at about `10ms` for 100 dates after warmup and latest daily generation at about `0.8s~1.0s`, keeping the shared page closer to a compact briefing surface instead of a validation/process viewer.

Operator-memo closeout note (`2026-05-18`): the remaining domestic `[△]` memos now have user/ops-facing V1 output rather than CLI-only foundations. `국장 관찰 요약` renders sector/theme breadth as graph-like bars; `관찰` starts with a top-2 `우선 확인` shortlist; and `순환매` renders separate card rows for image-label evidence, `순환매 참고 종목`, `순환매 참고 ETF`, and missing information. The implementation stays stored-data-only and read-only for `web-view`; it does not add public scores, grades, buy/sell wording, scheduler changes, broad KRX ingest, automatic `[12008]`/`[12010]`, secrets, admin controls, or DB paths.

Main briefing refinement note (`2026-05-19`): `오늘 읽을 요약` now treats the three review slots as time-anchored reading moments: `장초반 / 09:15`, `점심 / 12:00`, and `장 마감 전 / 15:15`. The opening slot is anchored to the previous stored report date and shows only a narrow prior-day candidate read; this prevents the morning block from leaning on same-day reports before they exist. The former large `리포트 흐름` metric is now part of `한줄평`, while the remaining metric cards focus on index, turnover, and `[12009]` flow references.

Historical mini-PC closeout note (`2026-05-19 01:25 KST`): the phone-readability gate was closed on that mini-PC DB. `market-briefing-readiness --recent-report-dates 5 --json` reported preview-ready `5/5`, manual review sends `3/3`, `phone_review_accepted=true`, and `schedule_candidate_ready=true` for the guarded `16:10~16:45` window. Latest backup `stock_monitor_20260519_0114_before_krx_20260518_closeout.db` was restore-smoked successfully, and `db-verify` remained clean. Elevated scheduler verification reported `StockMonitor-KrxDailyBackfill`, `StockMonitor-Notify`, `StockMonitor-Poll`, `StockMonitor-KrxMentionedFlowBackfill`, `StockMonitor-TelegramCommands`, and `StockMonitor-WebViewHourlyRestart` registered/enabled/Ready; `StockMonitor-Shutdown` remained absent. This is trace evidence only; the current main-PC gate is described in the next note and still has manual review sends `0/3`.

Main-PC continuation note (`2026-05-29 22:24 KST`): the active goal is not complete. Read-only `next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json` reports `completion_ready=false`, latest report date `2026-05-15`, market-briefing manual review sends `0/3`, `phone_review_accepted=false`, and KRX daily snapshots missing for 6 publishable business dates starting `2026-05-28`. `market-briefing-readiness --recent-report-dates 5 --json` remains preview-ready for `5/5` dates with public-safe issue count `0`; it reports data warning count `2` from stored flow fallback on older preview dates, but the scheduling gate is blocked by manual review sends `0/3`. `krx-baseline-analysis --json` reports stock/ETF/index tables through `2026-05-19`; the next missing daily snapshot dates are `2026-05-28`, `2026-05-27`, `2026-05-26`, `2026-05-22`, and `2026-05-21`, each missing all six daily endpoints. `market-day-observation --date 2026-05-29 --json` is incomplete and marks TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill as missing after verify times. `web-view-startup-fallback-check --json` reports `configured=false`, missing current-user `StockMonitor-WebView.lnk`, and local `/health` status `0`. External provider smoke remains unrecorded on this PC. No Telegram send, scheduler registration/change, KRX snapshot write, broad ingest, public scoring, broker integration, order routing, or trading recommendation output was performed during this refresh.

Historical main-PC `2026-05-20` observations remain trace evidence for the official KRX next-business-day `08:00` publication rule and the successful `2026-05-19` guarded backfill. They are superseded for active closeout planning by the `2026-05-29` readiness snapshot above.

## Phase C: Candidate Evidence Foundation

| Work | Detail | Done Criteria |
| --- | --- | --- |
| `candidate_evidence` DTO/UI | Computed DTO/API exists and `web-view` has a separated `관찰` tab. | UI shows evidence, not score. |
| Exclusion rules | Apply valid stock code, missing target/opinion, insufficient flow coverage, and fallback category labels. | Bad/missing values do not improve a row. |
| Web-view preview | Review visible `오늘의 관찰 후보`, `눈에 띄는 종목`, and `리포트 후 흐름` rows across several dates. | The page recommends observation targets, not trades. |
| Observation compression | First pass implemented: show practical `오늘의 관찰 후보` / `우선 확인` / `확인 후보` rows first, including a top-2 `우선 확인` shortlist, with `왜 눈에 띄는지` and `부족한 정보` chips. | Useful candidates are not buried behind validation-only fields. |
| Report context discipline | Treat Naver reports as a necessary context layer for attention/explanation, not as a strong standalone predictor. | Stronger observation wording must be supported by KRX/flow/price-position evidence and should stay below trading recommendation or public score language. |
| Evidence hierarchy | Keep `rank-driving evidence`, `context-only support`, and `gap-only missing context` separated. | `[12010]` rank-only stays support-only; hidden diagnostics cannot drive public ordering unless the same public-safe primary reason is visible. |
| Future intraday probe boundary | If a stable broker/API or quote source becomes available, start with a read-only lab probe for only the top-2 `우선 확인` candidates at a coarse cadence such as 5 minutes. | Request load, source permission, failure behavior, and public wording are reviewed before any production DB write, Telegram, scheduler, or admin integration. Approved intraday references may affect `web-view` observation ordering, but never broker execution or public trading calls. |
| Target-price progress | Stored-data-only target gap/progress metrics are attached to `candidate_evidence`. | First max-progress and target-hit D+ validation fields are exposed as read-only `도달 참고`; multi-date interpretation review still waits. |
| Backtest observation | `관찰` tab shows read-only post-report reaction rows and initial multi-date QA is complete. | Broader feature availability audit is required before scoring experiments. |
| Telegram briefing | Scheduled morning summary temporarily defaults to `briefing`. | Several real phone-screen deliveries are reviewed before making the format permanent. |
| Offline review | Use several dates to manually inspect whether rows make sense. | Weighting discussion can start only after review. |

## Phase C2: Domestic Market Observation Summary

The `example/report_*.jpg` references show a useful information architecture. The project should implement the useful observation-candidate curation, but must not copy `BUY`, `SELL`, score, grade, entry, exit, take-profit, target return, or conviction wording into public surfaces.

Implement the equivalent as `국장 관찰 요약`, `오늘의 관찰 후보`, `우선 확인`, `왜 눈에 띄는지`, `과열 참고`, and `수급 참고`.

| Needed data | Purpose | Current state |
| --- | --- | --- |
| 52-week and 20/60-day price position | Show high-near, breakout, or overheated context without a trading call. | Implemented in `observation_summary.price_volume_reference.items[]` from stored KRX daily rows; 52-week display is shown only when enough stored history exists. |
| 5/20-day return | Separate normal strength from short-term surge. | Implemented in `observation_summary.price_volume_reference.items[]` from stored KRX daily rows. |
| 20-day average volume/turnover multiple | Detect unusual attention and liquidity expansion. | First 20-day volume multiple and compact turnover display are implemented in `observation_summary.price_volume_reference.items[]`. |
| 5/10/20/31-day investor-flow totals | Show whether foreign/institution/individual flow is persistent or one-day only. | `[12009]` rows exist; anchor-day 31-day catch-up should be complete before review. |
| Flow turn date and persistence count | Show whether flow recently flipped and how many days it persisted. | First derived metrics are implemented in `observation_summary.flow_reference.items[].persistence` and rendered as `순유입/순유출 전환 ...부터 N일` when stored `[12009]` rows prove it. Visible digest text suppresses one-day-only flips and renders the persistence phrase only from 2 consecutive stored business days. |
| Report intensity over 1/5 business days | Distinguish one-off reports from repeated attention. | First compact derived output is implemented in `observation_summary.report_concentration.items[].report_intensity` and rendered as factual `5영업일 N건 · M일 언급` text when it adds context. |
| Broker breadth and target-price changes | Separate repeated same-broker reports from broader coverage and target revision. | Broker breadth exists in the structured DTO, while the compact web-view `리포트 집중` row keeps the visible line to report count plus factual `목표가 저번 언급 대비 상향/하향/유지` text. |
| Sector/theme breadth | Show whether a stock is moving alone or with its group. | First stock-linked derived summary is implemented in `observation_summary.sector_breadth`; the web-view now displays sector/theme rollups as graph-like bars with report count, active stock count, and selected-day share. Continue reviewing fallback labels and same-date category coverage before stronger interpretation. |
| Observation reaction windows | Check how similar conditions behaved after D+1/D+5/D+10/D+20. | Backtest observation and feature-coverage review exist as read-only/internal-only audits; keep incomplete future windows visible as coverage gaps and keep public scoring blocked. |

Suggested first user-facing blocks:

| Block | Allowed wording | Inputs |
| --- | --- | --- |
| Market mood | `시장 분위기`, `강세/약세`, `거래대금 참고` | KRX index, turnover leaders, ETF/sector movement. |
| Report concentration | `리포트 집중`, `확인 후보` | mention count and target availability; broker breadth remains internal/readiness context, not a public chip. |
| Flow reference | `수급 참고`, `외국인/기관 누적 순매수`, `수급 전환` | `[12009]` 5/10/20/31-day summaries. |
| Overheat reference | `과열 참고`, `고점 근접`, `거래량 급증` | 52-week/20-day position, short return, volume multiple. |
| Next review candidates | `오늘의 관찰 후보`, `다음 영업일 확인 후보`, `우선 확인` | Report concentration plus market/flow/volume evidence, no public numeric score or buy/sell wording. |

After the next market-day `[12009]` catch-up completes, run a feature availability audit over the latest report-mentioned anchor date and several prior dates. The goal is to decide which evidence is strong enough for `오늘의 관찰 후보` ordering, and which missing data should be shown as `부족한 정보`. Current mini PC dry-run for anchor `2026-05-18` at `2026-05-19 01:14 KST` returned `planned_call_count=300`, `raw_call_count=467`, `truncated=true`, and unresolved code count `0`; live calls were not run at 01:xx because the normal mentioned-stock flow task is due at `16:00`. Keep the next live run bounded to 300 calls, `[12009]` only, report-mentioned stocks only, and 31-day windows only.

## Phase C3: Non-Operational Product Enhancement

This section is the backlog for improving the product value after mini PC operation is stable. It is intentionally separate from scheduler, restore, backup, and host-management work.

The goal is to turn stored reports, KRX market data, ETF context, and `[12009]` flow into cleaner observation summaries and observation-candidate recommendations. The output should look like a compact market/report digest, not a trading system. Public surfaces may use observation language such as `국장 관찰 요약`, `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `확인 후보`, `과열 참고`, `수급 참고`, `시장 분위기`, and `눈에 띄는`. Do not introduce public numeric score, investment grade, buy/sell instruction, entry, exit, take-profit, target return, conviction, or target-action wording.

### Enhancement Axes

| Axis | What to improve | First useful output | Guard |
| --- | --- | --- | --- |
| Report concentration | Convert raw report counts into concentration signals and internal breadth diagnostics. | Same-date and 5-business-day report concentration by stock, internal broker breadth, target-price revision direction, and repeated-coverage labels. The first 5-business-day intensity and target-revision fields are implemented as stored factual context. | Do not treat more reports as automatically better; broker breadth stays internal/readiness-only. |
| Flow reference | Summarize recent `[12009]` rows into readable windows. | 5/10/20/31-business-day foreign, institution, and individual net flow totals; flow persistence count; latest flow turn date. | Use only report-mentioned stocks and stored rows. Keep wording as `수급 참고`. |
| Price and volume context | Add simple market-position facts around mentioned stocks. | 20/60-day price position, 52-week position, 5/20-day return, turnover and volume multiple versus recent average are exposed in `price_volume_reference`. | Mark overheat as context, not a sell signal. |
| Market mood | Compress KRX index, turnover leaders, ETF movement, and report concentration into a daily note. | `시장 분위기` block for Telegram and web-view with 3-5 short facts. | Missing latest KRX snapshot should be labeled as unavailable, not negative. |
| Sector/theme breadth | Explain whether attention is stock-only or group-wide. | Sector/theme rollup with report count, active stock count, turnover/flow hints, and related ETF preview where mapped. | Category fallback dates must be labeled; do not silently backfill current categories into history. |
| Observation reaction | Compare similar stored conditions against D+1/D+5/D+10/D+20 outcomes. | Read-only reaction bands and feature availability notes for internal review. | Can inform observation ordering, but no public numeric scoring or trading call until holdout stability is proven. |
| Web-view readability | Move from data tables to digest-first sections. | Top daily briefing, notable report groups, selected-stock detail, flow/volume chips, compact evidence drilldown. | Keep `admin-gui` details and operational checks out of `web-view`. |
| Telegram readability | Make the morning and potential closing briefings phone-readable. | Short sections with stable labels and compact numbers. | No noisy tables or repeated defensive disclaimers. |

### Derived Data Candidates

These are safe derived metrics because they describe stored facts rather than issuing a decision.

| Derived item | Input | Display idea |
| --- | --- | --- |
| Report concentration scorecard | `reports`, `daily_stock_summaries` | `리포트 집중`, `반복 언급`; broker breadth stays internal/readiness-only, not a public chip |
| Target-price revision trail | historical report target prices by stock/broker/date | `목표가 상향/하향 참고`, `최근 조정 여부` |
| Flow window summary | `stock_investor_flow_daily` `[12009]` rows | `외국인 20일 누적`, `기관 10일 누적`, `수급 전환일` |
| Flow persistence | consecutive positive/negative net flow days by investor type | `연속 순매수`, `최근 전환` |
| Price position | `stock_market_daily` rows | `20일 고점 근접`, `52주 위치`, `최근 반등/과열 참고` |
| Volume/turnover expansion | `stock_market_daily` volume and turnover averages | `거래대금 확대`, `평균 대비 거래량` |
| Sector breadth | category snapshots plus same-date summaries | `업종 내 동반 언급`, `그룹 확산 여부` |
| Reaction-window facts | backtest observation rows | `D+5 반응 참고`, `유사 조건 표본 수` |

### Implementation Order

1. Add read-only derived-metric builders for report concentration, flow windows, price/volume position, and sector breadth.
2. Add CLI audits that report feature coverage by date before exposing new fields in `web-view`.
3. Add an internal `observation_priority` or `evidence_density` ordering basis, but do not expose a public numeric score in v1. First pass uses non-numeric `observation_priority` labels and keeps the density number out of public DTOs.
4. Extend the daily DTO with compact `observation_summary` blocks and `오늘의 관찰 후보` rows that are display-ready and public-safe. First pass adds `why_notable` and `missing_information` to candidate rows.
5. Render the blocks in `web-view` as digest sections, keeping detailed rows expandable and showing `왜 눈에 띄는지`.
6. When a candidate is weak because data is missing, show `부족한 정보` rather than lowering it as if missing data were negative evidence. First pass shows missing KRX, stock flow, target, opinion, foreign-rank, and price/volume context explicitly.
7. Add Telegram preview output using the same DTO fields, then manually review several dates before scheduling any new briefing.
8. Run `web-view-value-qa` and browser/mobile review after each visible block is added.
9. Only after enough completed reaction windows exist, compare derived metrics against outcomes internally. Keep public output free of numeric score, grade, and trading-call wording.

Current implementation note (`2026-05-16`): steps 1-5 now have a first production-safe slice. The daily `web-view` DTO exposes `observation_summary` with read-only report concentration, 5-business-day report intensity, target-price revision context, `[12009]` 5/10/20/31-day flow windows, foreign/institution flow persistence and turn-date hints, 20/60-day and 52-week price position, 5/20-day return, 20-day volume multiple, and sector/theme breadth. One-day-only flow flips stay in the DTO but are suppressed from digest text so the phone/web preview focuses on 2+ day persistence. `observation-summary-audit` now reports detailed recent-date coverage for report intensity, target revision, flow windows, flow persistence, price/volume, 52-week position, and sector breadth before visual reliance. The first visible `국장 관찰 요약` block is live in `web-view` and is suitable for observation-candidate recommendation while remaining free of public numeric scoring and trading-recommendation wording. `observation-summary-preview` prints a manual Telegram-style preview from the same DTO fields, but it does not send, schedule, or register a new briefing. Selected-stock detail now also exposes stored 업종/테마 related context and 수동 ETF mapping hints from exact selected-date stored ETF rows where mapped. Candidate evidence target progress now includes read-only stored-window max-progress and target-hit D+ fields as `도달 참고`. Several real dates still need manual phone readability review before any scheduling discussion.

### Done Criteria

| Milestone | Done when |
| --- | --- |
| Data coverage understood | A CLI can show, for the latest 5-10 report dates, which derived metrics are available and which are missing. |
| First digest visible | `web-view` shows market mood, report concentration, flow reference, and overheat reference without exposing raw validation tables first. |
| Selected-stock context useful | Selecting a stock shows report trail, target-price movement, flow windows, price/volume context, and related sector/ETF hints. |
| Public-safe language enforced | QA allows observation-candidate wording, and fails if public surfaces contain trading recommendation, public numeric score, investment grade, buy/sell, entry/exit, take-profit, or conviction wording. |
| Reaction review grounded | Internal reaction review includes sample counts and missing-window labels, so thin data is not mistaken for signal. |

Current status (`2026-05-17`): the first four milestones are implemented for `web-view`, and a manual Telegram preview exists for review. Public-safe language enforcement was extended for English trading-action phrases and passed current QA. Selected-stock context now has report trail, target-price trail, flow windows, price/volume detail, and related 업종/ETF hints from stored rollups plus 수동 ETF mappings. Candidate evidence now shows target max-progress/hit-day facts only as read-only `도달 참고`. `observation-reaction-distribution` now includes horizon-level coverage summaries and missing-window labels so D+1/D+5/D+10/D+20 thin data is visible before interpretation. The latest 2026 baseline audit over `2026-01-02`~`2026-05-15` still has 493 candidates, with completed windows of D+1 486/493, D+5 427/493, D+10 344/493, and D+20 296/493. Reaction review remains internal-only and should wait for more completed windows.

Browser QA note (`2026-05-17 09:30 KST`): `web-view-browser-smoke --json` is now part of the visible `web-view` closeout loop after `web-view-value-qa`. On the mini PC it verified `2026-05-15` with desktop/mobile overflow `0px`, four view tabs, stock search present, observation tab clickable, data route POST blocked with `405`, and admin `/api/status` absent with `404`. The local external-sharing preflight was re-run successfully with mini-PC profile, access-code enabled, latest backup present, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`. After the latest-day KRX fill, `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json` returned issue count `0` and warning count `1`; the remaining warning is unresolved stock code `351020` with no KRX metadata mapping, not a latest-KRX snapshot availability issue or public-surface blocker. The final provider URL smoke now also checks that the root page does not look like `admin-gui`, known admin scheduler/operator/settings POST routes are unavailable or access-gated, and public archive/daily/candidate/stock-detail/flow-trend/ETF-trend/category-trend JSON does not expose known operator/admin keys.

Current candidate evidence review note (`2026-05-16`): `candidate-evidence-readiness` now provides a read-only multi-date audit for the visible `관찰` rows before manual interpretation. It reuses the `web-view` candidate DTO, runs value/public-safe QA over each date, counts target-progress validation, stored flow, foreign-rank coverage, quality flags, non-numeric observation-priority distribution, `왜 눈에 띄는지` distribution, and `부족한 정보` distribution, and keeps interpretation explicitly blocked for public numeric score and trading recommendation. `next-phase-readiness.next_commands` now includes `candidate-evidence-readiness --recent-report-dates 5 --stock-limit 20 --json` so the stored target-progress review across recent report dates remains part of the closeout loop. The current mini PC audit over the latest 5 report dates has review readiness `5/5` and QA issues `0`; after the `2026-05-15` KRX Open API fill, latest visible target validation is available for 16 rows and stock-flow context for 20 rows. Foreign-rank coverage remains sparse and should be treated as missing context, not negative evidence.

External quant experiment note (`2026-05-19`): local read-only observation CLIs remain the primary basis for candidate ordering. A bounded Kronos research run was added under `scripts/experimental/kronos_backtest_experiment.py` and executed only against stored KRX OHLCV and stored report candidates. A full stored-candidate sweep over `2026-01-02`~`2026-05-15` with `mention_count >= 2` produced mixed results: D+1 evaluated `475/493` with direction hit rate `0.4884`; D+5 evaluated `405/493` with hit rate `0.4864` and the negative-prediction bucket had higher actual return than the positive bucket; D+10 evaluated `333/493` with hit rate `0.5435`, positive-prediction bucket average actual return `6.2372%`, and negative-prediction bucket `3.5915%`; D+20 evaluated `293/493` with hit rate `0.5119`, but April D+20 remained weak and the model showed a broad negative-return bias. Kronos can stay as a research-only comparison lane, with D+10 the only currently interesting horizon, but it should not drive Telegram/web-view ordering, scheduling, public scoring, or recommendation logic. QuantDinger and other external comparison candidates remain setup/environment work until their required runtime is available; document them as environment-required, not as usable implementation dependencies. Botasaurus is import-verified but remains source-validation/browser-probe tooling, not a quant backtest engine.

CLI compatibility note (`2026-05-17`): the read-only closeout audits now accept the report-date wording used in this document and operator prompts. `observation-summary-audit --recent-report-dates N`, `candidate-evidence-readiness --recent-report-dates N --stock-limit M`, and `market-briefing-readiness --recent-report-dates N` are aliases for the existing bounded audit options. `observation-reaction-distribution --json` can omit `--from-date/--to-date`; when omitted it derives the stored `daily_stock_summaries` baseline range and remains read-only/internal-only. The commands remain read-only and do not send Telegram or register scheduler tasks.

Historical mini-PC aggregate readiness note (`2026-05-17`): `next-phase-readiness` provides a read-only top-level closeout snapshot for this document. It aggregates latest report coverage, observation-summary coverage, internal-only observation-reaction coverage, candidate-evidence review readiness, closing-market briefing readiness, KRX baseline missing-snapshot status, DB safety, category snapshot cleanup status, rotation mapping readiness, market holiday coverage, remaining non-code dependencies, the next market-day observation plan, the actual scheduled-run observation audit, the external `web-view` sharing plan, and the current-user `web-view` Startup fallback state without live fetches, DB writes, Telegram sends, scheduler registration, public numeric scoring, trading-recommendation output, or tunnel/provider configuration. The mini-PC trace from `2026-05-17` is retained below for provenance, but it is not the active main-PC gate state. On that mini PC data, the latest report date was `2026-05-15` with 51 reports and 28 summary stocks; KRX Open API daily snapshots covered through `2026-05-15` with missing count `0`; `observation_reaction` covered the stored `2026-01-02`~`2026-05-15` summary baseline with 493 `mention_count >= 2` candidates, completed windows D+1 486/493, D+5 427/493, D+10 344/493, and D+20 296/493, and remained `internal_only=true` / `public_surface_ready=false`; candidate-evidence review was ready for 5/5 recent report dates with 0 QA issue dates; closing-market briefing preview was ready for 5/5 dates, manual Telegram review sends were recorded for 3/3 dates (`2026-05-15`, `2026-05-14`, `2026-05-13`), and `db_safety.latest_backup_restore_smoked=true` for latest backup `stock_monitor_20260517_0818_after_krx_20260515_success.db`. Cloudflare provider smoke for `https://report.kr-stock.site` was recorded there and `external_web_view_provider_smoke.ready=true`. Re-evaluate these gates with the current main-PC `next-phase-readiness` output before marking anything complete.

Startup fallback note (`2026-05-17`): `web-view-startup-fallback-check --json` verifies the current-user Startup shortcut, the canonical `scripts/run_web_view.ps1` runner, the shortcut setup script, and local `http://127.0.0.1:8780/health`. It is a local web-view availability gate, not a Cloudflare configuration command. Use `--record-success` only after confirming the logged-in Windows session started the read-only `web-view` through the Startup shortcut after logon/reboot; the recorded event stores only non-secret local target and health status evidence. The fallback starts after user logon, not as a pre-login service, and it must continue to target only `web-view`, never `admin-gui`.

Final closeout wrapper note (`2026-05-17`): `verify_next_phase_closeout.ps1 -Date YYYY-MM-DD` is the broad readiness wrapper for the final stretch and is now surfaced first in `next-phase-readiness.next_commands`. It runs `db-verify --json`, local `web-view` Startup fallback health, optional `-RecordStartupFallbackSuccess` recording after a real logon/reboot, operator health, Task Scheduler registration verification, the dated `market-day-observation --json`, direct `observation-summary-audit --json` feature-availability review, direct `observation-reaction-distribution --json` reaction-window coverage review, direct `candidate-evidence-readiness --json` target-progress review, direct `market-briefing-readiness --json` phone-readability/scheduling-gate review, direct `web-view-value-qa --json`, direct `web-view-browser-smoke --json`, direct `external-web-view-sharing-plan --json`, direct `category-snapshot-status --json` and `category-snapshot-plan --json` fallback/refreshability review, direct `rotation-mapping-audit --json` Cycle/ETF mapping review, direct `krx-baseline-analysis --json`, and aggregate `next-phase-readiness --json`. The wrapper's `-Date` is only for market-day observation; rotation mapping intentionally uses its own latest stored report/KRX date default. By default it is read-only and does not send Telegram, register tasks, configure Cloudflare, fetch live KRX data, expose `admin-gui`, or print access-code/secrets.

Market-day observation usability note (`2026-05-17`): `market-day-observation` and the nested `next-phase-readiness.market_day_observation_audit` now expose `next_due_check` and per-check `verify_after_at` timestamps so the next real scheduled-run observation can be followed without translating relative times. For the `2026-05-18` first mini-PC market day, the current sequence is TelegramCommands `08:05`, KRX daily backfill `08:20`, Notify `08:30`, Poll `09:00`, and KRX mentioned-stock flow backfill `16:10` KST. The market-day-specific wrapper remains `verify_market_day_observation.ps1 -Date YYYY-MM-DD`, followed by the same-date `market-day-observation --date YYYY-MM-DD --json` rerun command, making the due-time audit explicit. The wrapper runs operator health, scheduler registration verification, market-day observation, `db-verify`, and `next-phase-readiness` in one elevated local PowerShell flow. `next-phase-readiness.completion_gates` now also shows whether the market-day observation gate is ready and points to the same dated wrapper as the preferred focused action, while the broader `verify_next_phase_closeout.ps1` wrapper sits above it in `next_commands`.

External provider smoke closeout note (`2026-05-17`, historical mini-PC trace): final shared-URL verification has a durable closeout path and was closed on the mini PC for `https://report.kr-stock.site`. `external-web-view-sharing-plan --json` prints the read-only Cloudflare/Tailscale operator sequence without configuring a provider, touching scheduler state, or exposing secrets. `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL` remains the preferred recheck wrapper after provider/runtime changes; it rejects HTTP, localhost/loopback, and path/query/fragment URLs, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless skipped, runs `external-web-view-smoke --record-success`, and then reruns `next-phase-readiness`. `external-web-view-smoke` remains read-only by default, but `--record-success` records a non-secret `operation_events` success row only when `issue_count=0` and the URL is a non-loopback HTTPS provider origin. Localhost, loopback, HTTP, and URLs with path/query/fragment cannot close this gate. The record stores URL origin, selected business date, HTTP check count, and public JSON route count; it does not accept or print the access-code. On this main PC, the current `next-phase-readiness` still reports provider smoke as not recorded, so rerun the provider wrapper only after the final URL/runtime is intentionally prepared.

Manual review note (`2026-05-17`): `market-briefing-readiness` and `next-phase-readiness` now print bounded `market-briefing --date YYYY-MM-DD --limit 5 --send` commands for preview-ready dates that still need phone readability review. The readiness commands themselves remain read-only; the suggested `--send` commands are deliberate manual review sends and are counted only when the `telegram_market_briefing` delivery log records `source=manual`. Both readiness JSON payloads include `requested_min_manual_reviews`, `enforced_min_manual_reviews`, and `phone_review_gate`, which report required/recorded manual review sends and whether CLI settings, local `admin-gui` settings API, and scheduled live send all enforce the gate. Even if a caller passes a lower `--min-manual-reviews`, the readiness gate reports at least the enforced default three sends because that is what settings and scheduled live send require. Both `operator-settings set market_briefing_phone_review_accepted true` and the local `admin-gui` settings API now refuse to set the acceptance flag until the default three manual review sends are recorded, so a typo or premature setting change cannot open the scheduling gate by itself.

### Explicitly Out Of Scope

| Out of scope | Reason |
| --- | --- |
| Broad all-stock `[12009]` ingest | The approved flow lane is report-mentioned stocks only. |
| Automatic `[12008]` or `[12010]` collection | These remain manual/sample/read-only reference lanes unless separately approved. |
| Public numeric score, investment grade, or trading recommendation | Current data is for observation-candidate recommendation and evidence summaries, not investment decision output. |
| Trading action copy | Buy/sell/entry/exit/take-profit language changes the product risk profile. |
| Admin control exposure | Product enhancement targets `web-view` and Telegram digest value; `admin-gui` remains private. |

## Phase D: Rotation / ETF Candidate Preview

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Cycle image text mapping | Extract or manually list labels from `example/Cycle.jpg`. | Alias candidates exist. |
| 업종 alias table | Map image labels to current user-facing 업종 labels. | Overlay/category matching is explainable. |
| 업종 to ETF mapping | Create operator-managed ETF candidate mapping or verified source-backed mapping. | ETF candidates are not guessed silently. |
| Rotation preview | Show ETF/stock candidates with report, turnover, flow, and ETF evidence separated. | The `순환매` tab now shows card-style `순환매 참고 종목` and `순환매 참고 ETF` slots, plus missing-information rows when mappings or stored ETF snapshots are absent. May use `오늘의 관찰 후보`, `후보`, or `참고`, but not trading-recommendation wording. |

Current implementation note (`2026-05-17`): `rotation-mapping-audit` now provides a read-only audit for `example/Cycle.jpg` coordinates, active image aliases, operator-managed ETF mappings, exact-date stored ETF evidence, and same-date stock evidence counts. It reuses the same mapping files as `web-view` and returns issues when an active alias has no coordinate, an ETF mapping is unreachable, or a mapped ETF lacks a stored latest KRX ETF snapshot. `next-phase-readiness.rotation_mapping` now includes the same Phase D summary and adds `rotation-mapping-audit --date YYYY-MM-DD --json` to `next_commands`. The current mini PC readiness output for latest report date `2026-05-15` reports 9 coordinates, 9 active aliases, 2 active ETF mappings, and issue/warning count 0/0.

## Phase D2: Closing-Market Briefing

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Message draft | First `market-briefing` CLI format exists. | Contains index direction, report concentration, notable stocks, flow reference, and check points without trading-recommendation wording. |
| Stored-data builder | First stored-data builder exists for same-day reports, KRX index snapshots, KRX turnover leaders, and available investor flow. | Missing flow/market data is omitted or labeled, not treated as negative. |
| Time-slot market mood card | Use the `시황 예시` operator photo as a reference for compact copy shape: title, index direction, notable stocks, core points, and check points. | Same-day live wording such as lunch/pre-close index and stock percentage moves requires a verified intraday index/stock quote source. Until then, keep output clearly stored-data-based and avoid pretending it is real-time. |
| Test send | Send manually first before scheduling. | Phone readability is acceptable over several market days. |
| Schedule candidate | `scheduled-market-briefing` CLI exists with business-day, no-run, repeat, and `16:10~16:45` time-window guards so it does not start at the same minute as the `16:00` flow backfill. | Do not register a Task Scheduler task until manual phone readability is acceptable and it does not compete with existing poll/flow backfill behavior. |

Current implementation note (`2026-05-17`, updated `2026-05-19`): `market-briefing-readiness` provides a read-only pre-scheduling audit. It inspects recent report dates, builds the stored-data closing briefing preview without sending Telegram, checks public-safe message issues, reports KRX snapshot/flow fallback warnings, and keeps `schedule_candidate_ready=false` until enough manual Telegram review sends are recorded and `market_briefing_phone_review_accepted=true` is set by the operator. Its JSON now includes `phone_review_gate` so the recorded-send count, acceptance flag, and enforcement surfaces are visible without reading docs. The acceptance setting itself requires the default three recorded manual review sends before it can be changed to true through either `operator-settings` or the local `admin-gui` settings API, and `scheduled-market-briefing` live send repeats the same recorded-review guard even if a legacy DB already has the acceptance flag set. The current mini PC audit over the latest 5 report dates has `preview_ready=5/5`, public-safe issue count `0`, manual Telegram review sends `3/3`, and `phone_review_accepted=true`, so the phone-readability gate is closed. `scheduled-market-briefing` is guarded to run no earlier than `16:10`, leaving the `16:00` KRX mentioned-stock flow backfill window first; both `market-briefing-readiness` and `next-phase-readiness` expose this as `schedule_candidate_window`. Do not register a new closing-market Task Scheduler task until the next market-day schedule is reviewed against existing poll/flow backfill behavior.

Continuation note (`2026-05-17`): closing-market briefing flow reference now uses market-wide investor-flow rows when available, and otherwise falls back to stored report-mentioned stock `[12009]` summaries for the selected report date. The fallback is still read-only, stored-data-only, and displayed as `수급 참고`; it is not a broad ingest path and does not use `[12008]` or `[12010]` automation. The latest mini PC readiness run over 5 report dates has data warning count `0` after this fallback, while the scheduling gate still waits for operator phone readability acceptance.

Operator photo reference note (`2026-05-19`): `data/operator_photo_inbox/telegram_227700602_20260519_133608.jpg` is tagged `시황 예시` and shows the desired compact market-mood copy pattern: `국장 점심 브리핑`, a one-line market headline, `지수`, `주요 종목`, `핵심 포인트`, and a final caution/check section. To implement this faithfully, the project needs explicit source decisions for intraday KOSPI/KOSDAQ values, intraday stock price/percent-change rows, and the rule for choosing notable stocks such as large caps, turnover leaders, report-mentioned names, or watchlist representatives. Public wording should use `확인 포인트`, `관찰 포인트`, `리스크 참고`, or `무리한 해석 주의`; avoid `전략 제안`, `저가 매수`, or other trading-action copy on shared surfaces.

Main-PC implementation note (`2026-05-20`): the first `시황 예시` implementation is now a stored-data/manual-review card, not a live lunch/pre-close quote product. The daily `web-view` payload exposes `market_briefing.time_slot_mood_card` with explicit `read_only=true`, `live_fetch=false`, `scoring=false`, `recommendation=false`, `production_integration=false`, and `manual_review_candidate=true`. The card renders in `오늘 읽을 요약` and `market-briefing-readiness` includes the same contract per date, including source-gap rows for unconfigured intraday index/stock quote sources and fallback KRX reference dates. On the main PC, `2026-05-15` and `2026-05-18` KRX daily snapshots were filled after `db-verify`, backup, restore-smoke, and OpenAPI availability probe evidence. The `2026-05-20 01:00~08:28 KST` unrestricted-network probes now show `2026-05-19` provider rows are available/partial but same-day `2026-05-20` is still `not_published`; this turn kept the probe path evidence-only and did not write snapshot tables. Latest report date `2026-05-15` is preview-ready and public-safe, but manual Telegram review remains `0/3`, so scheduling stays blocked. At `01:44 KST`, the main-PC current-user `StockMonitor-WebView.lnk` Startup shortcut was created for the read-only `web-view` loopback target without Task Scheduler registration. At `02:05 KST`, `next-phase-readiness`, market-day observation audit, completion gate, and external web-view sharing/provider command generation were corrected to show the main PC's actual Python path when `.venv\Scripts\python.exe` is absent. The remaining fallback gate is still post-logon observation through `web-view-startup-fallback-check --record-success --json`; detached hidden starts from the Codex session did not leave local `/health` available, while foreground startup does hold open.

## Phase E: Category Snapshot Cleanup

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Fallback inspection | Use `category-snapshot-status` and `category-snapshot-plan`. | Fallback dates are known. |
| Source-date refresh | Use dry-run, delay, confirm, and backed-up DB before network refresh. | More dates use dated snapshots. |
| Naming consistency | Keep `업종`, `테마`, `카테고리` labels stable. | No `KRX 업종/테마` mislabeling. |

Current implementation note (`2026-05-17`): `category-snapshot-status --mode fallback --limit 100 --json` shows 90 summary dates, 6 fully dated dates, 1 partial dated date, and 84 fallback dates, while separating sector/theme/partial dated counts in the summary. `category-snapshot-plan --limit 100 --json` remains read-only and includes a compact `plan_summary` with current-source-date allowed/blocked counts, missing/blocked snapshot type counts, block-reason counts, and dated dry-run refresh command count. `next-phase-readiness.category_snapshots` now carries the same Phase E status in the aggregate closeout snapshot, including fallback 84/90, allowed current-source-date refresh count 0, blocked count 84, affected missing snapshot type counts, and the exact status/plan commands. On this mini PC run, all 84 fallback dates are blocked for source-date refresh because the current source date is `2026-05-17` and the fallback summary dates are older; they should stay labeled as latest stored category classification unless separately verified.

DB cleanup note (`2026-05-17`): `db-cleanup --dry-run --retention-days 550 --json` now provides a read-only machine-readable retention plan. The current dry-run reports cutoff `business_date < 2024-11-13`, total cleanup candidates `11243`, and protected report/summary/delivery tables. Live cleanup still requires a fresh backup and explicit confirmation.

## Phase F: Mini PC / Sharing Prep

| Work | Detail | Done Criteria |
| --- | --- | --- |
| Access code enablement | Run `access-code set` on the eventual host before sharing. | Both surfaces require code when the hash file exists. |
| Cloudflare/Tailscale decision | Tailscale for owner access, Cloudflare Tunnel for friend-facing `web-view` only. | No direct public admin exposure. |
| Operation profile | Confirm future `mini-pc` profile behavior, especially shutdown policy. | Always-on host does not accidentally shut down. |

Current implementation note (`2026-05-17 18:00 KST`): `mini-pc-preflight` reports the effective `operation_profile` and can require `--require-mini-pc-profile` for final always-on readiness. On this mini PC, `operation_profile` has been set to `mini-pc` through audited `operator-settings`; elevated `verify_task_scheduler_registration.ps1` confirms the five default mini-PC tasks are registered/enabled and `StockMonitor-Shutdown` is absent. The verifier now distinguishes Task Scheduler metadata access-denied from genuinely missing task registration, so non-elevated shells do not imply scheduler repair. The external web-view readiness script also requires `--require-mini-pc-profile`; the latest local and provider checks passed with access-code enabled, latest backup present, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, `/api/status` gated or absent, and Cloudflare provider smoke issue count `0` for `https://report.kr-stock.site`. Restore-smoke against backup `stock_monitor_20260517_0818_after_krx_20260515_success.db` verifies the copied DB before removing it. Friend-facing sharing is now provider-smoked for the read-only `web-view`; keep `admin-gui` private and re-run the provider wrapper after Cloudflare, access policy, or local runtime changes.

KRX planning note (`2026-05-17`, updated `2026-05-20`): `scheduled-krx-daily-backfill --dry-run --json` now returns machine-readable skip output for weekends/holidays, and `krx-backfill-missing ... --dry-run --json` returns the missing-endpoint plan. JSON mode is planning-only for this lane so live KRX Open API fetches keep the backed-up text log and operation-event path. On the mini PC, `StockMonitor-KrxDailyBackfill` is intended to run at `08:10` KST on Korean business days, after the officially confirmed next-business-day `08:00` publication window, targeting only the previous business day or earlier missing daily stock/ETF/index snapshots.

Holiday coverage note (`2026-05-17`): `operator-status` now reports `market_holiday_coverage` with the built-in/default coverage end date and configured coverage end date. From October 2026 onward, it raises `market_holidays.default_coverage_expiring` unless verified future-year KRX holiday dates are configured.

Latest-day retry note (`2026-05-17 08:17 KST`, updated `2026-05-19 01:25 KST`): after backup `data/backups/stock_monitor_20260517_0815_before_krx_20260515_retry_5.db`, a bounded live `krx-backfill-missing daily --to-date 2026-05-15 --max-dates 1` retry filled all six daily Open API endpoints for `2026-05-15`: ETF 874 rows, stock 2701 rows, and index 127 rows, with `incomplete_endpoints=0`. A post-success backup `data/backups/stock_monitor_20260517_0818_after_krx_20260515_success.db` was created and restore-smoked successfully. For `2026-05-18`, backup `data/backups/stock_monitor_20260519_0114_before_krx_20260518_closeout.db` was created and a bounded live retry reached all six daily endpoints, but every endpoint returned `0` parsed rows and recorded `incomplete_endpoints=6`. The backup was restore-smoked successfully and DB verification remains clean. Retry later only after `db-verify`, a fresh backup if needed, and a bounded `krx-backfill-missing daily --to-date 2026-05-18 --max-dates 1`; do not fetch same-day `2026-05-19` pre-market rows.

## Explicit Non-Goals For The Next Phase

| Non-goal | Reason |
| --- | --- |
| Broad KRX Data Marketplace scheduled ingest | Needs separate approval after more validation. The narrow `[12009]` anchor-day mentioned-stock 31-day backfill lane is the only approved automatic path. |
| Public numeric score, investment grade, or buy/sell signal | Candidate evidence can order observation targets, but it is not mature enough for investment decision output. |
| Public admin GUI exposure | Control surface risk is too high. |
| Production broker/API integration | The current closeout should improve stored-data observation quality, not connect KIS/Toss or any broker to production, Telegram, scheduler, admin-gui, public web-view, or DB write paths. |
| Docker migration | Windows direct execution remains simpler for N100. |
| US market expansion | Domestic operation and sharing path should stabilize first. |

## Suggested Execution Order

1. Finish operational closeout checks while real market data continues to arrive.
2. Keep user `web-view` stock search and tab split stable.
3. Review `candidate_evidence` visible rows across stored dates without scoring.
4. Review stored `target_price_progress` rows across several dates and keep wording as `괴리율/진행률`, `관찰 후보`, or `우선 확인`, not trading recommendation.
5. Build non-operational enhancement metrics first: report concentration, `[12009]` flow windows, price/volume position, sector breadth, and display-ready observation summary blocks.
6. Run feature availability and reaction-distribution audits before any scoring prototype.
7. Review the first hit-days/max-progress validation fields across several stored dates before any stronger interpretation is discussed.
8. Start Cycle image label alias mapping for rotation ETF/stock preview.
9. Prepare mini PC/external sharing only after the user page is stable.

