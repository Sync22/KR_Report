# Operating Guide

Current operating state, delivery sequence, roadmap, and work board.

## Included sections
- Current Work
- Next Phase
- Execution Roadmap
- Work Todo Board

<!-- Merged from: docs/codex/operating-guide.md -->
## Current Work

## Snapshot

The canonical web-view completion path is [Web-View Completion Direction](operating-guide.md#web-view-completion-direction). This status document records current work only; it does not restate display and evidence rules.

As of `2026-05-29`, `02.Stock_Moniter` is no longer a scaffold, but the current main PC is not closeout-ready.

It is a runnable local MVP with:

- Naver research report collection, parsing, dedupe, SQLite persistence, daily summary aggregation, Telegram notification, Telegram command handling, Windows Task Scheduler wrappers, `admin-gui`, and separate GET-only user `web-view`.
- Stored Naver report history now covers `2026-01-02` through `2026-05-15` for the current 2026 analysis baseline.
- KRX Open API market reference snapshots for stocks, ETFs, and indices from `2024-11-08` through `2026-05-19` on the current main-PC DB. The `2026-05-29` read-only baseline uses the official next-Korean-business-day `08:00` publication rule and reports 6 missing daily snapshot business dates, starting with latest publishable date `2026-05-28`.
- KRX Data Marketplace investor-flow validation paths for `[12008]`, `[12009]`, and `[12010]`, with manual sample/import/read-only display paths implemented. Automatic collection is limited to anchor-date report-mentioned stocks, `[12009]` only, recent 31-day backfill, with 1-second request pacing by default.
- A clear data-source policy: Naver owns reports, KRX owns market reference data, and 업종/테마 remain a separate taxonomy layer.

Current work is the main-PC next-phase continuation: KRX OpenAPI latest-date backfill evidence, stored-data `시황 예시` market-mood preview readiness, Task Scheduler/Startup fallback blockers, and market-briefing manual review gates. Historical mini-PC closeout evidence remains trace context, but it is not proof that the current main-PC gates are closed.

Implementation note (`2026-06-17 KST`, updated `2026-08-09 KST`): news intelligence has operator batch and bounded scheduled collection paths for market-briefing target stocks. `news-intelligence-briefing-collect` persists observations only with `--save-observation --confirm-save`; the enabled scheduled path uses its existing business-date/time/dedupe guards. Saved rows are visible through the `market-briefing` message and the public-safe `web-view` daily DTO. The web-view itself is GET-only and never invokes the collector or writes observation rows. Canonical evidence composition and tab ownership are defined in [surface-guide.md](surface-guide.md#canonical-evidence-composition-purpose).

Implementation note (`2026-06-24 KST`): the normal daily web-view route now returns the already-built top-two candidate evidence and defers the 관찰-only observation summary to `GET /api/observation-summary`. This removes the duplicate candidate build and unnecessary observation-summary SQLite work from the initial main-screen path. The 관찰 tab now requests its three stored-data blocks in parallel and renders the first eight comparison rows instead of a full repeated-card wall; detailed report, target, flow, and news context remains in the 종목 tab. Target-hit horizons now use the selected report date as the baseline, so `D+N` means the stored trading-day distance from that report's target range, not an older unrelated target report. The 시장 tab opens the latest stored KRX flow when selected-date KRX is pending, while the 순환매 overlay remains collapsed when there is no stored ETF reference to show.

Implementation note (`2026-06-30 KST`): structural refactoring is stopped at the current 82/100 level. Do not continue helper extraction, `cli.py` slicing, handler movement, snapshot-builder movement, or web-view package reshaping unless a concrete product-value blocker appears. The active product question is now whether the friend-facing daily view quickly answers what to check first, why it is first, which evidence is missing, and whether stored KRX/flow/news references are fresh enough.

Implementation note (`2026-08-12 KST`): the bounded Toss read-only lane on `main` provides server-derived latest-date Top2 current price and same-day provisional investor volume, plus latest-date `tradingAmount` Top20 market context and Top2 overlap. The Top20 projection is memory-cached and public-safe; the separate replay capture remains development-hold, requires explicit live/save confirmations, and is not registered by default. Poll retains its 30-minute report collection/dedupe cadence and the implemented Telegram delivery slots are `08:30`, then `09:30` through `15:30` KST. Treat operating-PC scheduler evidence as the authority for whether a particular day actually delivered; this document does not infer delivery from the code path alone.

Evidence Snapshot pre-implementation design (`2026-06-30 KST`): no DB schema change is approved yet. A future migration should store only the facts needed to audit exposed observation order: candidate identity (`business_date`, `stock_code`, `stock_name`, source report ids), exposure state (surface, visible order, top-candidate flag, visible labels, `why_notable`, `missing_information`), feature snapshot (target/opinion availability, KRX price/turnover/index freshness, `[12009]` flow freshness, news observation run id and collect time, missing/freshness flags), and outcome join keys for D+1/D+5/D+20 close/turnover/flow results. Do not store raw HTML, raw news bodies, secrets, operator-only diagnostics, hidden scoring values, or trading decision text. Rollback plan: introduce tables behind read-only builders first, keep web-view output sourced from existing DTOs, and drop the migration before any writes are scheduled if QA detects public-boundary drift.

Minimal real-time data strategy (`2026-06-30 KST`): do not pursue all-stock real-time coverage, broker/account integration, automation, or public scoring. The highest ROI read-only lane is limited to current top candidates: current price, current turnover, KOSPI/KOSDAQ index freshness, price reaction after matched news, and top-candidate flow freshness. Until a stable source is proven, public copy must continue to say stored/reference/freshness status explicitly and treat missing intraday data as a gap rather than negative evidence.

Realtime-first pruning direction (`2026-07-05 KST`): the next product pass is not a new data-lane build. It is an information-pruning pass that raises `오늘 볼 것`, same-day/current evidence, news/current quote/turnover status, and explicit missing-current-evidence labels above stored KRX/flow/ETF/backtest reference. Use [surface-guide.md](surface-guide.md) as the detailed checklist. KRX daily, `[12009]` flow, ETF, Toss 20:00 baseline, target progress, and reaction windows remain useful, but should read as fallback/detail/review unless they directly explain the current top-2 candidate.

KRX KIND market-action confirmation (`2026-08-23 KST`): the existing one-minute Telegram command worker also checks KIND's official `시장조치 > 서킷브레이커/사이드카` category during `09:00~15:30` KST on Korean business days. A new official acceptance number sends one factual operator Telegram once; `delivery_log` suppresses repeats across worker restarts. It does not estimate an event before publication, alter candidates, call Toss/KRX credentials, collect Naver news, write to the web-view, or make a trading recommendation. KIND fetch failure is isolated from Telegram command processing.

Realtime-first 9-business-day observation decision (`2026-07-16 KST`): the completed review supports a three-lane product direction, not a combined score. Naver reports remain the `web-view` candidate seed: they answer where analyst attention is gathering. Telegram carries a compact market-news and stock-news scan: it answers what happened. The opt-in bounded Toss `tradingAmount` Top20 reference answers where current market attention is gathering. The surfaces may show intersections, but no lane replaces another or silently changes the report Top2 order.

Intersection rule: `report + independent same-day news`, `report + Top20`, and `news + Top20` are visible relationships. An all-three overlap is a prominent `우선 확인` item; a news-and-Top20 overlap without a report stays a Telegram market-attention item and does not create a new `web-view` report candidate. A Top20 miss is `상위 거래대금 미포착`, never a negative score or reason to lower a report candidate. News must be deduplicated by canonical URL, publisher, normalized title, and time window; report recaps are not independent news.

Top20 retention decision: the promoted latest-date projection remains bounded and read-only. It must not register a new scheduler or connect an in-progress research engine to production surfaces. The development-hold `toss_market_context_snapshots` replay path is limited to explicit live/token-reissue/save confirmation and bounded fields: observation time, rank, stock code, trading amount, trading volume, source, and source checked time. It excludes account data, raw news bodies, hidden scores, and trading instructions; its opt-in capture wrapper remains unregistered by default.

Decision Journal status (`2026-07-01 KST`): v0 research is frozen. Do not continue tie-break research, feature validation, target-revision validation, or scoring validation as active product work. Use [decision-journal.md](decision-journal.md) for the daily operating flow and [decision-journal.md](decision-journal.md) before any `decision_journal_*` DB migration is considered.

News Search Lane lab hold (`2026-07-03 KST`): the Naver search lane remains a coverage-expansion candidate but is not approved for production. In the recent 3-business-day Top5 QA, strict-only filtering produced 22 selected titles with automatic labels `usable_digest=21` and `report_rehash=1`, while human review judged only about 8-10 as clearly usable. The lab-only `post-filter-v2` pass improved quality by removing one parser artifact, two false positives, and one duplicate topic, and by separating `report_rehash`, `esg_pr`, and `corporate_notice`; its final selected set was 18 titles with `usable_digest=11` (`61.1%`), `report_rehash=1`, `esg_pr=4`, and `corporate_notice=2`. This is still too close to the threshold and leaves policy/person indirect mentions, so the production search lane, post-filter-v3, political/person-name filtering, scheduler wiring, matching changes, and web-view output changes are on hold. News Evidence Digest UI, the existing 5-lane evidence path, and the manual Top-candidate collect path stay active. Reopen the search lane only if a clear rule can push false positives near zero, existing 5-lane coverage remains operationally insufficient over repeated days, or real usage shows News Digest is repeatedly empty without search coverage.

## Product Direction Reset

As of `2026-05-15`, the product direction is reset around practical daily use rather than adding more intermediate validation screens.

| Principle | Current Rule |
| --- | --- |
| Rough usable result first | Prefer a readable daily briefing or compact screen before adding more process, proof tables, or diagnostic layers. |
| Visible imperfect output | If a feature is meant to help daily judgment, prefer a small labeled `web-view` projection over keeping it CLI-only until perfect. Imperfect news intelligence should appear as `참고`, `뉴스 근거 부족`, or `추가 확인 필요`, not as hidden infrastructure. |
| Memo intent matters | Treat an operator memo as complete only when the original user-facing intent is satisfied. A backend foundation or partial data path is `기반 완료`, not necessarily `의도 완료`. |
| User surface is compressed | The friend-facing `web-view` should show daily briefing, notable categories/stocks, market reference, and evidence drilldown. Raw tables, repeated defensive disclaimers, operating explanations, and debugging context belong in `admin-gui` or docs. |
| Observation curation is allowed | This project can recommend observation targets through `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, and `왜 눈에 띄는지`. Keep public numeric scores, investment grades, and trading-call wording such as `매수 추천`, `매도 추천`, `진입가`, `청산가`, `익절가`, `목표 수익률`, and `확신도` blocked. |
| Public limit is not the final ambition | The current public `web-view` blocks trading-decision wording because the source and execution safety gates are not ready. The long-term product direction may add an operator-only decision-support or execution-lab lane after stable real-time data, source freshness, failure behavior, permissions, and order-safety boundaries are proven. |
| Broker/API work is separated | Do not force KIS or any other broker integration to fill intraday gaps. Toss Securities Open API is promoted only for bounded read-only Top2 current-price/same-day provisional investor-volume and latest-date Top20 market-context projections. Account, asset, order, execution, broad polling, and any unapproved surface remain lab/hold lanes. |
| Iterate from daily collection | Show rough observations from stored data first, then decide what is mature enough to refine after several market days. |
| Add closing-market context | A separate `16:00`-around `오늘의 시장 분위기` Telegram briefing is now a valid next product direction, using stored same-day reports, KRX market reference, and available investor-flow context. |

## Observation Quality Direction

2026-05-29 operator memo feedback: the next useful improvement is not to add more visible detail. The useful direction is to make the top observation candidates explainable from a small number of public, source-backed categories.

| Horizon | Direction | Boundary |
| --- | --- | --- |
| Now | Harden stored report, exact-date KRX, `[12009]` flow, and price/volume evidence so `오늘의 관찰 후보` explains why a stock is worth checking. | Stored-data only. Missing evidence is a gap, not negative evidence. |
| Medium | Use 52-week/1-year context as the practical current-regime frame for report + KRX + flow interpretation. | Three-year data remains offline validation context, not a reason to overrule the current regime by itself. |
| Future | If Toss Securities Open API or another stable source becomes available, start a separate lab/staging read-only lane for top-2 `우선 확인` candidates. Verified intraday values should strengthen or lower observation priority and main-card emphasis. | Read-only means no production DB writes, Telegram, scheduler, `admin-gui`, broker secrets, or order routing. It does not mean the signal can never affect observation ordering. |
| Later | Time-slot priority such as `09:15`, `12:00`, and `15:15` can be refined only after a stable intraday quote/turnover/index source is proven. If that evidence becomes strong enough, a separate operator-only lane may evaluate trading-decision support. | Public `web-view` wording stays observation-first until the operator/execution lane is explicitly designed, reviewed, and separated from friend-facing output. |

Implementation standard:

- A public top candidate must be explainable by visible `rank-driving evidence`, not hidden diagnostics.
- `[12010]` rank-only evidence is support context, not a primary reason.
- Adding support labels, counters, or deeper readiness vocabulary is not progress unless it improves top-level explanation, prevents misleading ordering, exposes a true evidence gap, or improves dense UI readability.
- Report context is necessary for attention/explanation, but stronger wording needs stored KRX, `[12009]` flow, and current-regime price/volume support.
- `관찰 추천` is allowed and should be clear. The blocked boundary is trading advice or execution, not prioritizing which candidate should be checked first.

Current completion baseline:

| Scope | Completion | Notes |
| --- | ---: | --- |
| Domestic MVP on the current main PC without broad public sharing or US market expansion | 85-90% | Code, DB, and read-only preview foundations are usable, but this PC is not closeout-ready. The `2026-05-29` read-only readiness blockers are market-briefing manual review sends `0/3`, `market_briefing_phone_review_accepted=false`, KRX Open API daily snapshots missing for 6 business dates starting `2026-05-28`, real `2026-05-29` scheduled-run evidence missing, final external provider smoke not recorded on this PC, and current-user `web-view` Startup fallback not configured. |
| Domestic MVP if public trading recommendation/scored investment decision is counted as required | Out of current scope | Public numeric scoring, investment grades, and trading calls remain blocked. This separate non-goal should not dilute the current observation-curation closeout percentage. |

Current axis estimates:

| Axis | Completion | Main Remaining Work |
| --- | ---: | --- |
| 리포트 수집/요약/Telegram | 80-85% | Stored previews are usable, but this main-PC DB has market-briefing manual review sends `0/3` and `market_briefing_phone_review_accepted=false`; no automatic closing-market send or scheduler registration yet. |
| Scheduler / 운영 안정성 | 75-80% | This main PC is still `operation_profile=desktop-validation`. Non-elevated scheduler checks return access denied, so Task Scheduler proof requires elevated local PowerShell. Existing desktop tasks must not be broadened and no KRX probe or market-briefing scheduler task is registered. |
| DB / schema / backup | 96% | `db-verify` is clean, latest backup exists and restore-smoked, and KRX daily snapshots cover through `2026-05-19`; current readiness still blocks on missing KRX Open API daily snapshots for 6 business dates starting `2026-05-28`. Keep verification green after future KRX and flow data changes. |
| 사용자용 web-view | 90-93% | Stored-data `time_slot_mood_card`, five-tab role split, and value QA are working, but current main-PC final provider smoke is not closed and the current-user Startup shortcut is missing, so local `/health` is not available through the fallback path. |
| admin-gui | 85% | Live-control UX validation and status/log/settings polish. Latest DB backup presence, db-verify/db-backup reminders, readable recent-event summaries, and read-only recovery guidance are now visible in the operator status surface. |
| KRX / 수급 / ETF | 88-91% | Latest stored Open API daily snapshots are current through `2026-05-19`, while the `2026-05-29` baseline reports 6 missing publishable daily snapshot dates starting `2026-05-28`. Continue with guarded backfill discipline; do not treat KRX OpenAPI as a real-time intraday source. |
| 관찰 후보 / 백테스트 / evidence | 84% | Observation-candidate ordering now has a public top-2 `우선 확인` block with reason text and missing-information labels. Public numeric scores and trading calls remain blocked and are not required for the current observation-curation closeout. |
| Documentation / roadmap | 90% | Keep roadmap/current-work/next-phase/changelog synchronized. |

Current main-PC readiness interpretation (`2026-05-29 22:24 KST`): read-only `next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json` reports `completion_ready=false`. The command explicitly reports `read_only=true`, `writes_database=false`, `sends_telegram=false`, `registers_scheduler=false`, `scoring=false`, and `recommendation=false`. Latest stored report date remains `2026-05-15` with 51 reports and 28 summary stocks. Candidate evidence is review-ready for 5/5 recent dates with QA issue dates 0, and market briefing previews are ready for 5/5 dates with public-safe issue count 0, but the phone-review gate remains open with manual review sends `0/3` and `market_briefing_phone_review_accepted=false`. `krx-baseline-analysis --json` reports stock/ETF/index snapshot tables through `2026-05-19` and missing daily snapshots for 6 business dates starting with `2026-05-28`, each missing all six daily endpoints. `market-day-observation --date 2026-05-29 --json` is `incomplete`: TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill evidence are all missing after their verify times. `web-view-startup-fallback-check --json` reports `configured=false`, missing current-user `StockMonitor-WebView.lnk`, and local `/health` status 0. External provider smoke is not recorded on this PC. Public numeric scoring, investment grades, trading calls, broker execution, and order routing remain separate non-goals rather than blockers for `오늘의 관찰 후보`.

Historical main-PC `2026-05-20` observations, including the `2026-05-19` KRX guarded backfill and same-day publication-window checks, remain useful trace evidence. They are superseded for active closeout planning by the `2026-05-29` readiness snapshot above.

Historical mini-PC implementation continuation (`2026-05-18 00:03 KST`): the remaining code-feasible next-phase gap was closed by expanding `candidate-evidence-readiness` so operators can review `observation_priority`, `why_notable`, and `missing_information` distributions across stored report dates. The then-latest 5-date audit reported review readiness `5/5`, QA issues `0`, all 97 visible rows as `우선 확인`, stored flow coverage for 97/97 visible rows, and `외국인 순매수 상위` as the only repeated missing-information category. Elevated `operator-status --json --health-exit` on that mini-PC state returned `health.level=ok`; the five expected mini-PC scheduler tasks were registered/enabled/Ready, and `StockMonitor-Shutdown` was absent. This is trace evidence only; use the current main-PC readiness interpretation above for active blockers.

Web-view IA/performance pass (`2026-05-18 KST`, updated `2026-05-29 KST`): the friend-facing `web-view` now separates the top tabs by user task. `메인` focuses on the daily briefing, top-2 `오늘의 우선순위`, `Naver 장중 참고` overlap placeholder, and compact observation summary. `관찰` holds the full `오늘의 관찰 후보`, 일일 종목 요약, and `리포트 후 흐름`. `종목` holds selected-stock context and reports. `시장` holds selected-date stored KRX/flow reference. `순환매` holds 업종/테마 상세, recent category trend, ETF trend, and the rotation overlay. Hidden tab data remains lazy-loaded where possible: `관찰` fetches `candidate-evidence` and backtest observation when opened, `시장` fetches recent flow trend when opened, and `순환매` fetches ETF/rotation data when opened. The daily API no longer embeds the heavier `candidate_evidence` payload; candidate rows are loaded through `/api/candidate-evidence`. Public candidate cards no longer render raw `quality_flags`; they keep user-facing `왜 눈에 띄는지` and `부족한 정보`. Browser smoke coverage now includes desktop, tablet, large mobile, and mobile viewports, and verifies the exact `메인`/`관찰`/`종목`/`시장`/`순환매` tab order plus representative panel visibility.

Follow-up performance pass (`2026-05-18 KST`): the market-briefing builder now reuses the same stored KRX reference date, market index rows, turnover leaders, and investor-flow rows inside one daily build instead of repeating equivalent repository lookups across line and summary builders. The candidate-evidence API also stopped returning the same row list under both `rows` and `candidates`; `rows` is the canonical public key. On the mini PC latest stored report date `2026-05-15`, measured `market_briefing` build time dropped from about `4.0s` to about `0.7s`, full daily payload build time from about `5.0s` to about `1.8s`, and `candidate-evidence?limit=20` response size from about `189KB` to about `95KB`.

Web-view speed closeout pass (`2026-05-19 KST`): the friend-facing `web-view` removed the operator/process-heavy `주기 데이터 점검` block from the public daily payload and HTML while keeping the `periodic-data-needs-audit` CLI/admin path available. Public JSON GET routes now use a conservative in-process 30-second cache so repeat refreshes do not rebuild the same stored-data DTOs, while external response headers remain `no-store`. Archive category mapping now batches snapshot-date lookup for all archive dates instead of calling the per-date helper, and daily snapshot generation reuses recent KRX/flow dates plus the prebuilt market briefing across the main briefing and one-line-comment builder. On the mini PC latest stored report date `2026-05-18`, measured archive payload generation is now about `10ms` for 100 dates after warmup, and full daily payload generation is about `0.8s~1.0s` while retaining public-safe boundaries.

Candidate-evidence batching pass (`2026-05-18 KST`): `build_web_view_candidate_evidence_snapshot` now preloads same-day flow, 5/10/20/31-day flow windows, report intensity, previous target revisions, market history, and target-progress baseline rows for all visible candidate stocks in grouped stored-data reads. The public DTO remains `rows`-only and keeps non-numeric `observation_priority`, `why_notable`, and `missing_information`; no public score, grade, trading action, admin state, secret, DB path, Telegram, scheduler, or KRX collection behavior was added. A query-budget regression test now covers multi-stock candidate evidence generation. On the mini PC latest stored report date `2026-05-15`, `candidate-evidence?limit=20` remained about `95KB` and measured build time dropped to about `0.3s`; full daily payload build time measured about `1.1s`.

Operator memo progress pass (`2026-05-18 KST`): `operator-memo-status` parses the local `data/operator_memos.md` backlog and reports all memo statuses as read-only JSON/text. The `2026-05-18` partial memos are now reflected on actual surfaces instead of stopping at CLI output: `web-view` shows stored-data `장초반`/`점심`/`장 마감 전` one-line comments in the main daily briefing, Telegram accepts `/한줄 [YYYY-MM-DD|latest]`, Telegram accepts `/사진 설명` plus either an attached image or the next image and stores it locally in `data/operator_photo_inbox/`, and `web-view` 시장 tab plus `operator-status` expose a read-only periodic-data needs block. `[12009]` remains limited to report-mentioned 31-day windows, `[12008]`/`[12010]` automation remains blocked, and real-time KOSPI/sidecar detection remains a later source/rate-limit review rather than a new fetch path.

Telegram operator task queue (`2026-05-19 KST`, updated `2026-05-21 KST`): Telegram accepts `/진행 ...` and bare `진행 ...` as operator task requests. General requests still store a local JSONL queue record in `data/operator_progress_requests.jsonl` and reply with a queued task id such as `P123`; they do not execute arbitrary shell commands, change scheduler state, or expose secrets. Health/run-diagnosis phrasing such as `건강상태`, `오늘리포트`, or `왜 안 돌` is handled immediately by a read-only `operator-status` snapshot response so the chat explains scheduler metadata access-denied noise, latest reports/summaries, and recent failed events instead of only queueing the request. A narrow allowlist now runs safe operator actions directly from Telegram (`오늘 리포트 수집`, `운영 점검`, `DB 검증`, `웹뷰 확인`, `해야 할 일 확인`) and returns a compact `작업/소요/결과` response; `오늘 리포트 수집` uses manual poll recovery without intraday Telegram sends. Codex-side work can still read queued requests through `operator-task-next --json` and record a compact completion report through `operator-task-complete --id P123 --status done|partial|blocked --progress N --summary ...`, optionally `--send`ing the completion summary back to Telegram. The queue is an operator-facing handoff lane, not a friend-facing `web-view` feature.

Operator memo closeout pass (`2026-05-18 KST`): the remaining non-open `[△]` memos were moved from foundation-only status to user/ops-facing V1 output. `web-view` now renders `국장 관찰 요약` sector/theme breadth as graph-like bars with report count, active stock count, and selected-day report share; the `관찰` tab shows a public `우선 확인 2개` block above the full candidate evidence list; and the `순환매` tab shows card-style evidence with separate `순환매 참고 종목`, `순환매 참고 ETF`, and missing-information rows. These changes do not add public numeric scores, grades, buy/sell wording, scheduler changes, KRX broad ingest, `[12008]`/`[12010]` automation, secrets, admin controls, or DB paths. At that closeout point, the only `[ ]` memo was US-market API source investigation, which remains intentionally excluded from the current domestic implementation closeout.

Operator memo intake (`2026-05-19 KST`): `/진행` queue check found no pending `data/operator_progress_requests.jsonl` request, but `data/operator_memos.md` received new open memo lines. These are treated as backlog intake, not completed implementation. External URLs are recorded as bookmarks only until a later approved review opens them and evaluates license, security, install burden, and fit with the current mini-PC operation.

| Memo | Category | Interpretation | Next handling | Status |
| --- | --- | --- | --- | --- |
| `26.05.19 10:36` time-slot briefing should be checked at the actual time, not prefilled | Product/web-view | Current `장초반`/`점심`/`장 마감 전` blocks are stored-data briefing blocks. The user wants time-near observation such as `09:15`, `12:00`, and `15:15` with same-day context where available and previous-day fallback only when that is the meaningful input. | Split the briefing model into `stored fallback` vs `time-slot observation`; add a read-only preview/check loop before any Telegram automation. Do not add live scraping unless source/rate-limit policy is reviewed. | Open, high priority |
| `26.05.19 15:30` QuantDinger bookmark | Research/backtest reference | Research comparison candidate, but not currently runnable on this PC because the required Docker environment is not available. | Keep isolated from production. Prepare the environment before any backtest comparison. Do not add public scoring, buy/sell recommendations, trading alerts, broker execution, or scheduler automation. | Open, environment required |
| `26.05.19 15:31` codex-complexity-optimizer bookmark | Developer tooling bookmark | Developer-tool candidate, not a quant backtest engine. Environment and output review are still required before use. | Use report-only first after setup; review output before code changes. Do not add as a stock-monitor runtime dependency. | Open, environment/review required |
| `26.05.19 15:33` X video bookmark | Visual/reference bookmark | Likely a UI/briefing/reference example sent for later interpretation. | Requires manual/browser review later; summarize into product guidance only after checking the content. | Open, research |
| `26.05.19 15:34` scrcpy release bookmark | Excluded operator tooling bookmark | Explicitly excluded from the current install/use declaration. | Do not install or wire into the project for now. Phone-readability checks can continue through existing manual review paths. | Excluded |
| `26.05.19 15:35` botasaurus bookmark | Source-probing/tooling bookmark | Import was verified historically, but Botasaurus is now archived reference-only rather than an active probe lane. | Use `scrapling-official` for new bounded KRX/Data Marketplace or future browser-gated source probes; never replace the main Naver/Telegram/SQLite pipeline or widen ingest. | Hold, reference-only |
| `26.05.19 15:38` single-file HTML QA checklist prompt | QA tooling prompt | Useful for manual feature acceptance checklists after a web-view change. The prompt includes a CDN confetti dependency, so it should stay local QA tooling, not production web-view UI. | Create a branded local QA checklist template later under a tooling/docs path if needed; keep it separate from friend-facing `web-view`. | Open, actionable |
| `26.05.19 15:41` git sync between mini PC and main PC | Source-management | High-value operational work. The mini PC is currently the live operating baseline, while the main PC should receive a clean change bundle and later become the main coding surface with a controlled mini-PC pull/update path. | Prepare a git/sync plan first: repo status, install availability, source-of-truth rule, backup-before-pull, conflict policy, and scheduled pull safety. Do not auto-pull on the mini PC until that policy is explicit. | Open, high priority |
| `26.05.19 22:31` codegraph bookmark | Developer tooling bookmark | Developer-tool candidate for codebase indexing/visualization, not a quant backtest engine. Environment and generated artifact policy must be checked before use. | Keep generated indexes/local MCP config outside production runtime behavior. Do not add scheduler automation or public-surface features. | Open, environment/review required |
| `26.05.08 00:00` US-market API source investigation | Deferred expansion | Still intentionally outside the current domestic closeout. | Keep as unstarted until domestic operation and sync workflow are stable. | Deferred |

Tooling probe result (`2026-05-19 KST`, policy updated `2026-06-03`): scraping/tool bookmarks were tested in isolated, read-only paths. Naver research collection still fits the existing Playwright/API parser path: `inspect-page --limit 5` reached `<naver company research URL>`, clicked the domestic tab, found 1 API page and 5 API report items. KRX Data Marketplace still fits the raw `.env` request path first: `[12009]` `--request-only` resolved 삼성전자 `005930 -> KR7005930003`, and `krx-flow-login-check --date 2026-05-08 --json` passed with `[12008]` row count `13` and expected investor-flow fields. Botasaurus import was verified historically and a browser probe loaded both Naver and KRX pages, but it is now archived/reference-only; use `scrapling-official` for new bounded browser-gated/source probes. CodeGraph was installed locally under `scripts/experimental/node_tooling`, indexed 54 Python files into 1,450 nodes and 5,570 edges, and produced useful context for `backtest_observation` impact review. `codex-complexity-optimizer` was also installed locally; its default installer attempts to write to `CODEX_HOME`, so use the bundled `analyze_complexity.py` scanner directly for report-only reviews. First `src` scan highlights `analysis/backtest_observation.py` repeated nested-loop/sort patterns and several `cli.py` query/sort-in-loop candidates; treat these as refactor leads, not automatic changes.

Web-view hourly restart pass (`2026-05-18 KST`): `scripts/restart_web_view.ps1` now stops any existing listener on the configured port and restarts the read-only `web-view` on loopback. `register_mini_pc_scheduler_tasks.ps1` registers `StockMonitor-WebViewHourlyRestart` by default with an hourly trigger starting at `00:05`, and `verify_task_scheduler_registration.ps1`, `mini-pc-preflight`, archive verification, and setup guidance all treat the restart script as part of the mini-PC operating bundle. On this mini PC, elevated registration verified six default tasks and a manual `schtasks /Run /TN StockMonitor-WebViewHourlyRestart` returned `Last Result=0` with `<loopback web-view URL>/health` returning `200 ok`.

Web-view briefing refinement (`2026-05-19 KST`): the main `오늘 읽을 요약` time blocks now use fixed review anchors `장초반 / 09:15`, `점심 / 12:00`, and `장 마감 전 / 15:15`. The opening block intentionally uses the previous stored report date as its candidate reference so the pre-open read does not pretend same-day reports are already available; midday and pre-close continue to use the selected report date with turnover and `[12009]` flow references. The old large `리포트 흐름` card was removed from the metric grid and tiered down into `한줄평`, leaving the visible grid focused on index, turnover, and investor-flow reference. This remains stored-data-only and does not add live Naver/real-time scraping, Telegram scheduling, scores, grades, or trading-call wording.

Main-PC market mood card pass (`2026-05-20 KST`): the `시황 예시` photo reference is now represented as a real stored-data preview contract rather than only a note. `market_briefing.time_slot_mood_card` is included in the daily `web-view` payload and in `market-briefing-readiness` date rows, with read-only/manual-review flags, compact sections for `지수`, `주요 종목`, `핵심 포인트`, and `확인 포인트`, plus source gaps for missing intraday KOSPI/KOSDAQ and stock quote sources. The friend-facing `오늘 읽을 요약` renders the card above the existing index/turnover/flow grid. On this main PC, `market-briefing-readiness --recent-report-dates 1 --json` for `2026-05-15` reports preview-ready with public-safe issue count `0`, but KRX index/turnover use the `2026-05-14` stored snapshot fallback and the phone review gate remains blocked at manual review sends `0/3`. `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json` and `web-view-browser-smoke --date latest --stock-limit 20 --json` both returned issue count `0`; warnings are limited to latest KRX snapshot availability after `2026-05-14`.

Main-PC KRX availability/backfill pass (`2026-05-20 01:00 KST`, updated `09:17 KST`): `db-verify` was clean, a fresh backup `<stock_monitor_backup.db>` was created, and `db-restore-smoke` verified it successfully; the same backup was restore-smoked again at `07:29 KST` after readiness briefly surfaced missing restore-smoke evidence. The first sandboxed KRX OpenAPI probe hit local socket restrictions, then the same command was rerun with real network access. `2026-05-15` and `2026-05-18` each returned rows from all six daily endpoints and were backfilled successfully; post-backfill `db-verify` stayed clean and recent missing daily snapshot count dropped from 4 dates to 2 dates. `2026-05-19` and same-day `2026-05-20` returned HTTP/API success but raw/parsed row count `0` for all six endpoints at the early window. Sandboxed probes at `02:28 KST` through `08:28 KST` hit local `WinError 10013` socket restrictions; those errors are recorded as environment evidence, not provider publication status. The unrestricted-network reruns through `07:28 KST` kept both targets `not_published`. At `08:28:38 KST`, `--date latest` (`2026-05-19`) changed to usable provider evidence: ETF/stock endpoints were `partial`, index endpoints were `available`, reference date was `2026-05-19`, raw rows totaled `4011`, and parsed rows totaled `3701`. At `09:16 KST`, backup `<stock_monitor_backup.db>` was created and restore-smoked; the first sandboxed live backfill hit `WinError 10013`, then the same bounded command was rerun with real network access and stored all six `2026-05-19` daily endpoints with `incomplete_endpoints=0`. Post-backfill `db-verify` stayed clean and `krx-baseline-analysis --json` now reports only `2026-05-20` missing. At `08:28:42 KST`, explicit `--date 2026-05-20` still remained `not_published` for all six daily endpoints. `next-phase-readiness.krx_openapi_availability_probe` groups the latest probe batch across all six endpoints instead of showing only the last recorded endpoint. The `krx-openapi-availability-probe --date latest --endpoint daily --json` path records endpoint availability in `operation_events` only, does not write snapshot tables, and is documented as a scheduler candidate rather than a registered task. On this main PC, elevated Task Scheduler verification with `-IncludeShutdown` confirms the machine is still a desktop-validation host: `StockMonitor-KrxDailyBackfill`, `StockMonitor-Notify`, `StockMonitor-Poll`, `StockMonitor-KrxMentionedFlowBackfill`, `StockMonitor-TelegramCommands`, and `StockMonitor-Shutdown` all exist but are disabled, and `StockMonitor-WebViewHourlyRestart` is missing. Non-elevated `operator-status --json --health-exit` and `verify_task_scheduler_registration.ps1` still report Task Scheduler metadata `access_denied`; `operator-status` at `08:05 KST` also reports stale `telegram_command_loop` worker state and no same-day Telegram command-loop evidence. At `01:44 KST`, the current-user `StockMonitor-WebView.lnk` Startup fallback shortcut was created for `<loopback web-view target>` without registering a scheduler task; `web-view-startup-fallback-check --json` still reports `configured=true`, `startup_shortcut_exists=true`, and remains blocked by real post-logon observation plus local `/health` status `0`.

Developer tooling pass (`2026-05-20 KST`): CodeGraph status reports the existing local index with 54 Python files, 1,450 nodes, and 5,570 edges, but it needs `codegraph sync` after the current edits. `complexity-optimizer` full-repo scan hit Python AST recursion limits, while the `src` scan completed and again points to `analysis/backtest_observation.py` nested loops/sort-in-loop plus several `cli.py` query/sort-in-loop sections as review leads. No production dependency, scheduler task, public surface, or refactor was added from those tools in this pass.

Historical closeout checks are trace evidence only. The retired `16:10~16:45` market-briefing path is not part of the current contract; see [the canonical slot definition](operating-guide.md#phase-d-closing-market-briefing-track) for the active schedule.

Additional verification (`2026-05-17 09:30 KST`): local external `web-view` readiness was re-run successfully with mini-PC profile, access-code enabled, latest backup present, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`. The remaining value-QA warning is unresolved stock code `351020` without KRX metadata mapping, not a public-surface blocker. Non-elevated Task Scheduler metadata access denied remains an expected permission limitation; use elevated local PowerShell for the scheduler registration proof.

Regression verification (`2026-05-17`): an earlier full local test suite passed with `551 passed`. At that time, `next-phase-readiness` still reported `completion_ready=false` until real market-day scheduler observation, operator phone-readability acceptance, and final provider URL smoke were complete; the provider URL smoke blocker was later closed for `<external web-view provider URL>`.

Mini PC readiness recheck (`2026-05-17 09:50 KST`): `verify_mini_pc_readiness.ps1` passed with `-RequireMiniPcProfile -RequireAccessCode -SkipPytest -SkipRestoreSmoke -SkipOperatorStatus`. It confirmed `db-verify` clean, `.env` presence without printing secrets, latest backup presence, `operation_profile=mini-pc`, access-code enabled, KRX Data Marketplace scope limited to report-mentioned `[12009]` recent 31-day backfill, web-view value QA issue count `0`, browser/mobile smoke issue count `0`, `POST` blocked with `405`, and `/api/status` absent with `404`. `operator-status` remains excluded from this non-elevated recheck because Task Scheduler metadata requires elevated local PowerShell.

Market-day observation usability (`2026-05-17 09:55 KST`): `market-day-observation --date 2026-05-18 --json` now exposes a top-level `next_due_check` plus per-task `verify_after_at` timestamps in KST. The current next check is `StockMonitor-TelegramCommands` at `2026-05-18T08:05:00+09:00`, followed by KRX daily backfill `08:20`, Notify `08:30`, Poll `09:00`, and mentioned-stock flow backfill `16:10`. The market-day-specific wrapper remains `verify_market_day_observation.ps1 -Date 2026-05-18`, followed by the same-date rerun command `python -m stock_monitor market-day-observation --date 2026-05-18 --json`, so the operator can rerun the exact audit at each due time while also checking operator health, scheduler registration, `db-verify`, and aggregate readiness in one elevated local PowerShell flow. The broader `next-phase-readiness.next_commands` list now places `verify_next_phase_closeout.ps1 -Date 2026-05-18` before that focused wrapper.

Next-phase closeout wrapper (`2026-05-17 18:55 KST`): `scripts/verify_next_phase_closeout.ps1` is now the one-command final closeout helper. It runs `db-verify --json`, `web-view-startup-fallback-check --json`, optional Startup fallback success recording through `-RecordStartupFallbackSuccess`, operator health, scheduler registration verification, `market-day-observation --json`, `observation-summary-audit --json`, `observation-reaction-distribution --json`, `candidate-evidence-readiness --json`, `market-briefing-readiness --json`, `web-view-value-qa --json`, `web-view-browser-smoke --json`, `external-web-view-sharing-plan --json`, `category-snapshot-status --json`, `category-snapshot-plan --json`, `rotation-mapping-audit --json`, `krx-baseline-analysis --json`, and `next-phase-readiness --json`. The reaction-distribution step is read-only/internal-only and derives the stored summary baseline when dates are omitted, so the wrapper does not hardcode the current report range. The web-view, category, rotation, and KRX baseline steps are also read-only and mirror the remaining next-command audits surfaced by aggregate readiness; `-Date` is reserved for market-day observation, while rotation mapping uses its own latest stored-date default. It is read-only by default: it does not send Telegram, register scheduler tasks, configure Cloudflare, fetch KRX live data, or expose `admin-gui`. The wrapper is now included in the migration archive required-entry list and appears in `next-phase-readiness.next_commands`.

Closeout verification refresh (`2026-05-17 20:11 KST`): local regression tests passed with `557 passed`, `db-verify --json` remained clean with integrity `ok`, schema `5/5`, FK violations `0`, investor-flow quality issue total `0`, and category quality issue total `0`. `observation-reaction-distribution --mention-threshold 2 --json` now derives the stored baseline `2026-01-02`~`2026-05-15` and reports 493 internal-only candidates without public numeric scoring or trading-recommendation output. `verify_next_phase_closeout.ps1 -Date 2026-05-18 -SkipOperatorStatus -SkipSchedulerRegistration` completed successfully and included the new reaction-distribution step. Elevated scheduler verification confirmed the five mini-PC tasks are registered and ready, while `StockMonitor-Shutdown` remains absent; elevated `operator-status --json --health-exit` returned health `ok`. `next-phase-readiness` still reports `completion_ready=false` because the remaining gates require operator phone-readability acceptance, a real `2026-05-18` market-day scheduled-run observation, and a post-logon/reboot Startup fallback success record.

Closeout wrapper expansion verification (`2026-05-17 20:22 KST`): `verify_next_phase_closeout.ps1 -Date 2026-05-18 -SkipOperatorStatus -SkipSchedulerRegistration` now also runs direct `category-snapshot-status`, `category-snapshot-plan`, `rotation-mapping-audit`, and `krx-baseline-analysis` read-only steps before aggregate readiness. The wrapper passed locally; `rotation-mapping-audit` intentionally uses its default latest stored date instead of the market-day observation `-Date`, so the audit remains anchored to `2026-05-15` until newer stored report/KRX evidence exists. Full regression tests passed again with `557 passed`.

Web-view closeout wrapper verification (`2026-05-17 20:37 KST`): `verify_next_phase_closeout.ps1 -Date 2026-05-18 -SkipOperatorStatus -SkipSchedulerRegistration` now also runs direct `web-view-value-qa --json`, `web-view-browser-smoke --json`, and `external-web-view-sharing-plan --json` before category/rotation/KRX baseline audits and aggregate readiness. The expanded wrapper passed locally, including the browser/mobile smoke path, without sending Telegram, registering tasks, configuring Cloudflare, fetching live KRX data, exposing `admin-gui`, or printing access-code/secrets. Full regression tests passed again with `557 passed`.

Continuation verification (`2026-05-17 10:12 KST`): `next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json` still reported `completion_ready=false` with the then-open blockers: operator phone readability acceptance, real `2026-05-18` market-day scheduled-run observation, and final external `web-view` provider/final URL setup while keeping `admin-gui` private. The provider blocker was later closed at `2026-05-17 17:46 KST`. `db-verify --json` remained clean with integrity `ok`, schema `5/5`, FK violations `0`, partial KRX daily snapshot dates `0`, investor-flow quality issues `0`, and category quality issues `0`. `verify_external_web_view_readiness.ps1` passed again with mini-PC profile, access-code enabled, latest backup present, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`; the only warning remained unresolved stock code `351020` without KRX metadata mapping. In the current non-elevated shell, `operator-status --json --health-exit` and `verify_task_scheduler_registration.ps1` still fail on Task Scheduler metadata access denied, which is a permission/elevation limitation and not evidence of missing registration.

External gate recheck (`2026-05-17 13:30 KST`): `verify_external_web_view_readiness.ps1` passed again before Cloudflare provider binding. It confirmed `.env` presence without printing secrets, mini-PC profile, access-code enabled, latest backup `<stock_monitor_backup.db>`, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`. The only warning remains unresolved stock code `351020` without KRX metadata mapping. Tunnel target remains `<loopback web-view URL>`; share only `web-view`, keep `admin-gui` private. The provider-smoke closeout was later recorded successfully against `<external web-view provider URL>`.

Regression and phone-review recheck (`2026-05-17 13:36 KST`): the full local regression suite passed with `551 passed in 162.58s`. `market-briefing-readiness --recent-report-dates 5 --json` remains read-only and reports preview-ready `5/5`, public-safe issue count `0`, manual review sends `3/3` for `2026-05-15`, `2026-05-14`, and `2026-05-13`, but `phone_review_accepted=false`; the only schedule blocker for the closing-market briefing candidate is still operator phone readability acceptance. At that time, `next-phase-readiness` also waited on real `2026-05-18` market-day scheduled-run observation and final external `web-view` provider smoke; the provider smoke was later closed.

Cloudflare Access smoke hardening (`2026-05-17`): `external-web-view-smoke` now treats a recognizable Cloudflare Access HTML/login page as access-gated for `/health`, root, read-only user JSON routes, and blocked admin/control routes. This keeps the final provider smoke compatible with Cloudflare Access before sharing, while still rejecting public admin/control payloads and arbitrary non-JSON API responses. The focused external-smoke tests passed, and the latest full local regression suite passed with `553 passed in 163.30s`.

External sharing plan clarity (`2026-05-17`): `next-phase-readiness.external_web_view_sharing.provider_smoke_checks` and `external-web-view-sharing-plan --json` now state that Cloudflare Access HTML/login pages are accepted as access-gated responses for the final provider smoke. This is descriptive only; it does not configure Cloudflare, relax `admin-gui` privacy, accept access-code values, or change the requirement that the final provider origin must pass `verify_cloudflare_web_view_tunnel.ps1` before sharing.

External smoke admin-marker hardening (`2026-05-17`): the Cloudflare Access HTML/login allowance now refuses to classify a response as access-gated if the same body also looks like `admin-gui`. Admin markers such as `Stock Monitor Admin` or scheduler/settings control routes take precedence, so a mispointed tunnel cannot pass merely because the page text mentions Cloudflare Access.

Elevated scheduler health recheck (`2026-05-17 17:02 KST`, superseded by official publication-window update): running `verify_task_scheduler_registration.ps1` and `operator-status --json --health-exit` from an elevated local shell confirmed the default mini-PC tasks were registered, enabled, and `Ready`. The KRX Open API daily task is now intended for a single `08:10` run after the officially confirmed next-business-day `08:00` publication window. `StockMonitor-Shutdown` remains absent, matching the always-on mini-PC default. `operator-status` health is `ok`; the remaining scheduled-run blocker is real market-day evidence after those tasks become due, not registration repair.

Cloudflare pre-provider local gate recheck (`2026-05-17 17:11 KST`): `access-code status` reports enabled, `external-web-view-sharing-plan --json` still fixes the only allowed tunnel target as `web-view` on `<loopback web-view URL>`, and `verify_external_web_view_readiness.ps1` passed again. The preflight confirmed mini-PC profile, `.env` presence without printing secrets, latest backup `<stock_monitor_backup.db>`, access-code enabled, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`. The remaining warning is still unresolved stock code `351020` without KRX metadata mapping, not a provider-sharing blocker. The external closeout blocker was later closed by `verify_cloudflare_web_view_tunnel.ps1` success against `<external web-view provider URL>`.

Local web-view target runtime (`2026-05-17 17:21 KST`): the actual friend-facing `web-view` process was started on `<loopback web-view target>` with `pythonw.exe` for Cloudflare-prep testing. `GET /health` returned `200 ok`, and unauthenticated `GET /` returned `401`, confirming the access-code gate is active on the loopback target. Keep the Cloudflare Tunnel target pointed only at `<loopback web-view URL>`; do not point any provider hostname at `admin-gui` or control routes.

Historical Cloudflare provider smoke success (`2026-05-17 17:46 KST`): final external verification for `<external web-view provider URL>` passed on the mini-PC state through `verify_cloudflare_web_view_tunnel.ps1` after rerunning the provider smoke with unrestricted network access. The first sandboxed attempt returned `status=0` for every external route, but the unrestricted run recorded `external-web-view/provider-smoke` success with issue count `0`, `13` HTTP checks, and `5` public JSON routes checked. Observed route behavior was `/health` `200`, unauthenticated user routes `401`, user-data write `POST /api/daily/2026-05-15` `405`, `/api/status` `401`, and scheduler/operator/settings control POST routes `405`. No access-code or secret value was accepted or printed. This is retained as provider-boundary trace evidence only; the current main-PC readiness output still treats final provider smoke as not recorded for this PC/runtime.

Web-view auto-start fallback (`2026-05-17 18:00 KST`): Task Scheduler registration for a new `StockMonitor-WebView` task was attempted but the current session received `Access is denied` from both `Register-ScheduledTask` and `schtasks.exe /Create`. To keep the Cloudflare target resilient after user logon, `scripts/create_web_view_startup_shortcut.ps1` was added and used to create the current-user Startup shortcut `StockMonitor-WebView.lnk`. The shortcut runs only `scripts/run_web_view.ps1` with `-HostAddress <loopback-host> -Port <web-view-port>`; it does not expose `admin-gui`. After the earlier manual process was stopped during scheduler registration attempts, `web-view` was restarted on `<loopback web-view target>`; local `/health` returned `200 ok`, and a read-only external smoke for `<external web-view provider URL>` returned issue count `0` with `/health` `200`, unauthenticated user routes `401`, user-data write `405`, and control POST routes `405`.

Startup fallback readiness gate (`2026-05-17 18:38 KST`): `web-view-startup-fallback-check --json` now audits the current-user Startup fallback without printing secrets. The current mini PC result is `configured=true`, `runner_script_exists=true`, `setup_script_exists=true`, `startup_shortcut_exists=true`, local target `<loopback web-view URL>`, local `/health` `200`, and issue count `0`. It remains `ready=false` until a deliberate post-logon/reboot observation is recorded with `python -m stock_monitor web-view-startup-fallback-check --record-success --json`. The command records only a non-secret operation event when the local health check passes; it does not start `admin-gui`, configure Cloudflare, or expose the access-code.

Closeout gate evidence (`2026-05-17 10:23 KST`): `next-phase-readiness` now exposes `completion_gates` for DB safety, market-briefing phone review, market-day scheduled-run observation, external `web-view` provider smoke, `web-view` Startup fallback observation, KRX daily snapshot baseline, and market holiday coverage. The final external provider command is `external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json`; default smoke remains read-only, while `--record-success` records a non-secret `operation_events` row only when issue count is `0` and the target is a non-loopback HTTPS provider origin. Localhost, loopback, HTTP, or URLs with path/query/fragment cannot record the closeout event. The recorded detail stores the URL origin only, selected business date, HTTP check count, and public JSON route count, so access-code values are not accepted or printed. Until that success event exists, `external_web_view_provider_smoke.ready=false` and the external sharing blocker stays active. The Cloudflare post-provider wrapper is `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL -PythonExe .\.venv\Scripts\python.exe`; it validates the provider origin, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless explicitly skipped, records the provider smoke success, and reruns `next-phase-readiness`. The external provider smoke completion gate now points to that wrapper as the preferred next command, the market-day scheduled-run observation gate points to the dated `verify_market_day_observation.ps1 -Date YYYY-MM-DD` wrapper, and the Startup fallback gate points to `web-view-startup-fallback-check --record-success --json` after a real post-logon/reboot check. `external-web-view-sharing-plan --json` now gives the operator a focused read-only sequence before Cloudflare/Tailscale setup. A later Cloudflare Access smoke hardening pass raised the full local regression count to `553 passed`.

## What We Are Actually Building Now

| Axis | Current Work |
| --- | --- |
| Personal Telegram MVP | Continue live validation of scheduled daily summary, intraday polling, command worker, paging, memo capture, fragment resume, and filtered output. |
| Local admin surface | Keep `admin-gui` as the operator-only control surface for scheduler state, run-now controls, no-run calendar, safe settings, audit logs, operation profile, DB backup/verify reminders, and safe recovery guidance. |
| Friend/user surface | Keep `web-view` as a separate public-safe information page for date-based reports, selected stock detail, market reference, ETF/flow context, rotation reference, and approved top-priority evidence actions. Normal reads stay GET; the news-observation collect action is the narrow access-gated write exception. |
| Market reference data | Use KRX stock/ETF/index snapshots as stored read-only context. Morning scheduled backfill targets the previous business day or earlier recent missing dates; larger rebaseline still requires bounded, backed-up manual backfill. |
| Investor flow | Keep KRX Data Marketplace investor-flow as stored `수급 참고`. The approved automatic path is narrow: `16:00` anchor-date mentioned stocks only, `[12009]` stock-level only, recent 31-day window, newest dates first, default 300-call cap, default 1-second request delay, skip existing rows. Broad market/top/all-stock scheduled ingest remains disabled. |
| Candidate evidence | First read-only `candidate_evidence` DTO/API exists and `web-view` has a separated `관찰` tab for evidence display. The visible tab copy is now framed as `오늘의 관찰 후보`, `눈에 띄는 종목`, and `리포트 후 흐름` so it reads as a compact observation-candidate recommendation surface rather than a validation table. It includes target-price gap/progress evidence, keeps KRX turnover references in compact 조/억 units, suppresses duplicate missing-flow/rank text in evidence chips, compresses D+1/D+5/D+10/D+20 into one `리포트 후 반응` column, limits the `리포트 후 흐름` table to 6 rows by default with `더 보기`, and must avoid public numeric score, grade, or trading-call wording. `candidate-evidence-readiness` now audits recent visible rows across dates without public scoring, including target-validation coverage, stored flow, foreign-rank coverage, quality flags, non-numeric observation-priority counts, `왜 눈에 띄는지` counts, `부족한 정보` counts, and value/public-safe QA. It is also surfaced directly in `next-phase-readiness.next_commands` so the multi-date target-progress review is not skipped during closeout. The latest mini PC audit over 5 report dates has review readiness 5/5 and QA issues 0; `2026-05-15` target validation is now available for 16 visible rows after the KRX Open API snapshot fill. |
| Target-price progress | Stored-data-only gap/progress metrics are attached to `candidate_evidence` as `target_price_progress`. The same DTO now includes stored-window `max_progress_to_min/max` and first target-hit D+ fields when the baseline is below the target range; this remains descriptive `도달 참고` and can support observation-candidate ordering, not public numeric scoring or trading recommendation. |
| Observation-candidate recommendation v1 | `candidate_evidence` rows now expose non-numeric `observation_priority`, `why_notable`, and `missing_information` for `web-view`. The public card heading is `오늘의 관찰 후보`, and each row shows `왜 눈에 띄는지` plus `부족한 정보`. Internal ordering uses evidence density from report concentration, broker breadth, target context, stored `[12009]` flow, turnover/price-volume context, and foreign-rank reference, but the numeric density is not exposed in public DTOs. |
| Report-context interpretation | Naver research reports are a context layer, not a strong standalone signal. Use reports to identify where attention and explanation are gathering, then combine them with stored KRX price/turnover/index, `[12009]` flow, and 52-week/1-year context before making an observation stronger. A longer 3-year research window is useful for offline validation, but it should not outweigh the current 52-week market regime when the recent index move has changed the baseline. Time-slot priority such as `09:15`, `12:00`, and `15:15` needs stable intraday quote/turnover/index APIs before the product can make stronger same-day ordering claims. If a stable real-time lane is later tested, the first safe probe should be read-only and limited to the current top-2 `우선 확인` candidates at a coarse cadence such as 5 minutes, only after request load, source terms, and failure behavior are reviewed. |
| Backtest observation | BO-1~BO-7 exists: `mention_count >= 2` candidates, `1/5/10/20영업일` reactions, target gap/progress, same-date flow, turnover, foreign net-buy top inclusion, public-safe API, first `관찰` tab rendering, and initial multi-date QA. Latest-date rows now distinguish `목표가 있음` from `KRX 기준가 대기` so missing market snapshots do not masquerade as missing target prices. `observation-reaction-distribution` now reports horizon-level completed/missing coverage and labels each D+ window as complete/partial/thin/no completed window before showing grouped reaction values, keeping incomplete reaction windows visible as data coverage rather than signal. The current 2026 baseline audit over `2026-01-02`~`2026-05-15` has 493 candidates with completed windows D+1 486, D+5 427, D+10 344, and D+20 296. |
| Scoring draft | Archived/hold. `research-notes.md` is historical research evidence only, not active product scope. SD-4/SD-5 hidden scoring commands remain callable for compatibility but are hidden from top-level CLI help and must not affect `web-view`, Telegram, daily briefing, ordering copy, roadmap progress, or investment decisions. |
| External access | Prepare lightweight access gate and Cloudflare/Tailscale decision path, but do not publicly expose `admin-gui`. |

## Recent Core Changes

| Area | Recent Change |
| --- | --- |
| Web-view layout | Split into date selector plus `메인`, `관찰`, `종목`, `시장`, and `순환매` tabs. The split is read-only and keeps operational controls out of the friend-facing screen. `메인` carries the daily briefing and top-2 priority overview, `관찰` carries full candidate evidence and report-after-flow rows, `종목` carries selected-stock context, `시장` carries stored KRX/flow reference, and `순환매` carries category/theme/ETF rotation context. |
| Selected stock detail | Split into `선택 종목` and `선택 종목 리포트`; KRX current price, weekly investor-flow `순유입/순유출`, daily flow, and daily volume live in the stock card. |
| Selected stock target trail | `web-view` selected-stock DTO now includes a read-only `target_price_trail` from stored reports. The stock context card shows recent target-price ranges by report date, report count, and previous-date up/down/flat reference labels without score, rank, or action wording; broker breadth remains an internal/readiness context, not a public candidate chip. |
| Candidate target validation | `candidate_evidence.rows[].target_price_progress` now exposes stored-window `validation_available`, `validation_window_days`, max progress, and lower/upper target-hit D+ fields. The `관찰` tab renders these as `도달 참고` only when stored validation is available. |
| Selected stock related context | `web-view` selected-stock DTO now includes read-only `related_context` from stored same-date 업종/테마 rollups plus `data/rotation_etf_candidates.json` 수동 ETF 매핑. The stock context card shows related 업종/테마 report breadth and exact selected-date stored ETF previews when mapped; it performs no live fetch, scoring, ranking, or recommendation. |
| Report list | Added an optional `의견없음 제외` toggle, but the default detail view now keeps `의견 없음` reports visible so missing source values remain available for evidence review. The report-only card hides non-report market context. Report DTOs now expose user-facing `target_price_display` and `opinion_display` so missing target/opinion values do not leak as raw `N/A`/`None` in the UI. |
| Investor-flow display | Recent 20-business-day stock flow and market volume are used for selected stocks where data exists. Weekly flow shows latest four week buckets from older to newer. |
| KRX history | Stock/ETF/index daily snapshots were expanded back to `2024-11-08` through guarded Open API batches. The stored 18-month analysis window through `2026-05-15` has `0` missing KRX business dates after the backed-up `2026-05-17 08:17 KST` retry. DB verification reports no KRX snapshot quality issues. |
| KRX daily retry backfill | Added `scheduled-krx-daily-backfill` and `StockMonitor-KrxDailyBackfill` contract for the `08:10` KST previous-business-day Open API snapshot fill after the official next-business-day `08:00` publication window. Dry-run/skip output now supports `--json` so weekend/holiday skips and missing-endpoint plans can be captured cleanly without parsing text logs; JSON mode is planning-only and live fetches still require the backed-up text/log path. |
| KRX flow | January-May market flow and foreign net-buy ranking data remain stored through the guarded manual baseline. Stock-level `[12009]` investor flow has also been filled for report-mentioned stocks only, using each stock's latest report anchor and recent 31-day window through the `2026-01-02`~`2026-05-15` report baseline. Coverage remains report/candidate-policy driven rather than full-market stock-level flow. A `2026-05-17 06:48 KST` dry-run for anchor `2026-05-15` returned `planned_call_count=0`, so there are no remaining latest-anchor `[12009]` calls for the current latest report date. |
| Mentioned-stock flow schedule | Added `scheduled-krx-mentioned-flow-backfill` and `StockMonitor-KrxMentionedFlowBackfill` for `16:00` KST. It anchors on the report-mentioned date and fills recent 31-day `[12009]` stock investor-flow rows only, with a default 300-call cap and 1-second request delay so large first runs resume over multiple executions without spiking KRX requests. In normal live operation the anchor is the current business day; after restore or prefilled report ingestion, use each stock's latest report-mentioned date or the latest report-mentioned business date batch target as the anchor and repeat until dry-run reports no remaining calls. Unmapped KRX metadata such as `351020`, `233990`, and `052960` is treated as `unresolved_stock_codes`, skipped before KRX requests, and logged without failing the whole Task Scheduler run. The current latest anchor has unresolved codes `351020`, `233990`, and `052960`, and all resolvable rows already exist. |
| Report backfill | Filled Naver reports for `2026-01-02` through `2026-02-06` in backed-up 5-business-day batches. Report coverage now starts at the first 2026 KRX trading day. |
| Backtest observation | Added `stock_monitor.analysis.backtest_observation`, `GET /api/observation/backtest`, and `관찰` tab `리포트 후 흐름` rendering. Initial BO-7 QA covered `2026-05-11`, `2026-05-08`, and `2026-05-07`, and target-progress caution labels were added. |
| Scoring draft | Historical only. Earlier SD-1~SD-5 scoring-draft commands remain as research trace evidence, but the lane is archived/hold and hidden scoring commands are no longer presented as active CLI work. `target_observation` remains allowed only as read-only stored-window context for the `관찰` tab, without public numeric score or trading-recommendation wording. |
| Parser/dedupe hardening | Added regression coverage for Naver API/DOM source-id canonicalization, same-source intraday queue dedupe, and read-only observation CLI parser dispatch. |
| P0 live-operation observation | `operator-status` now includes a `live_observation` block that summarizes same-day operation-event evidence even when Task Scheduler metadata is unavailable or access-denied. Future same-day components that are not due yet are shown as `pending`, not `missing`. KRX Open API backfill evidence now distinguishes `observed` from `attention`: `empty`/`partial` events and older `success` events that still leave the selected daily endpoints below row thresholds are surfaced as `attention(incomplete_snapshot)` and health warnings. Scheduler `access_denied` still keeps strict health at `fail` because same-day events do not prove task registration or next-run metadata. The optional `StockMonitor-KrxFlowLoginReminder` task is separated as a warning when metadata access is denied because normal operation keeps it disabled. |
| Naver parser drift fixtures | `inspect-page --save-fixture PATH` can save a live inspection snapshot for parser drift regression, and fixture parsing prefers API rows over DOM fallback rows. Use `--require-parsed-reports` on live validation days so an empty or drifted snapshot fails immediately instead of becoming a false baseline. Existing fixtures can be rechecked with `naver-fixture-validate PATH`. Live fixtures now include `data/naver_fixtures/naver_research_2026-05-14.json` and `data/naver_fixtures/naver_research_2026-05-15.json`, each with 20 parsed API reports. |
| Telegram timeout trace | Production daily summary fragment failures now record `message_hash` and `ambiguous_send=true/false` in delivery/event detail so timeout-after-send cases can be audited without pretending the residual duplicate risk is eliminated. The trace is visible in both JSON and text `operator-status` output, and ambiguous same-day failures raise `telegram.timeout_trace.ambiguous_send` in operator health warnings. |
| Telegram control state durability | Telegram command paging, intraday continuation, pending stock selection, and replay markers still use the local JSON control-state file, but writes now go through a temporary file and atomic replace so interrupted saves do not leave a partial JSON file. |
| Admin DB safety reminders | `operator-status` JSON/text and `admin-gui` now expose latest DB backup presence and remind the operator to run `db-verify` plus create a fresh `db-backup` before KRX/data-changing work. This is display-only guidance and does not expose `.env`, tokens, access-code, or admin controls to `web-view`. |
| Admin event readability | Recent operation events now include a `detail_display` summary. `admin-gui` and text `operator-status` prefer that display value for KRX backfill, KRX flow, scheduler, notify, and admin failure rows while keeping raw `detail` in JSON for local investigation. |
| Admin recovery guidance | `operator-status` now exposes `recovery_actions`, and `admin-gui` renders them as read-only safest-next-step guidance for scheduler metadata access, TelegramCommands recovery, KRX latest snapshot availability, and missing DB backup. This does not add broad recovery buttons; TelegramCommands restart remains the only broad GUI restart path. |
| Read-only CLI schema guard | Read-only diagnostics and closeout audits such as `operator-status`, `db-verify`, `next-phase-readiness`, web-view QA/smoke, and observation audits now verify that an existing DB is already on the current schema instead of running the schema initializer. Missing DB files still initialize for first setup, stale schemas fail with an explicit `db-migrate` instruction, and data-changing commands keep the normal initialize path. This reduces avoidable SQLite write-lock contention when operators run multiple health checks. |
| DB verify and cleanup dry-run | `db-verify` now has a shared payload builder used by both the CLI and `next-phase-readiness.db_safety.db_verify`, so the aggregate closeout snapshot exposes integrity, schema, FK, duplicate, orphan, partial KRX snapshot, investor-flow quality, and category quality readiness. `db-cleanup --dry-run` supports `--json` for machine-readable retention planning without DB writes, and `next-phase-readiness.db_safety.cleanup_dry_run` surfaces the same read-only retention plan. Latest mini PC verification at `2026-05-17` reports `db_verify.ready=true`, integrity `ok`, schema `5/5`, FK `0`, partial KRX snapshot dates `0`, investor-flow quality issues `0`, and category quality issues `0`. Latest cleanup dry-run with `--retention-days 550 --json` reported cutoff `business_date < 2024-11-13` and `11243` KRX snapshot rows as cleanup candidates (`stock_market_daily` 8107, `etf_daily_snapshots` 2761, `market_index_daily` 375), while protecting reports, summaries, and delivery state. Do not run live cleanup without a fresh backup and explicit `--confirm`. |
| SD-5 holdout | Historical only. The internal-only `observation-hidden-holdout` and `observation-hidden-holdout-sweep` paths remain read-only and callable for compatibility, but this lane is archived/hold and hidden from top-level help. Do not use it as active product work, public ordering evidence, Telegram copy, or roadmap progress. |
| Web-view value QA | Added `web-view-value-qa` read-only CLI to scan static web-view HTML plus archive, daily, stock-detail, candidate, backtest-observation, intraday, category detail, category trend, market, flow-trend, ETF-trend, rotation alias mapping, rotation ETF mapping, and rotation-overlay DTOs for invalid numeric values, display-facing missing marker leaks, display placeholder times, same-date market-reference gaps, category mapping fallback, public observation text leaks, old internal labels, blocked decision/disclaimer copy, forbidden admin/operator DTO keys, accidental admin/operator surface references, raw long won amounts in market-briefing turnover display fields, and old observation-table layout patterns such as separate `D+1/D+5/D+10/D+20` columns or 8-column validation tables. It fails when an active `data/rotation_image_aliases.json` alias points to a missing overlay coordinate, when an active `data/rotation_etf_candidates.json` ETF code is missing from the latest stored ETF snapshot, and when an active ETF mapping category has no overlay coordinate or active alias path. Static HTML checks catch known stale labels and blocked public numeric score/investment-grade/trading-decision wording before it reaches the friend-facing page, while canonical observation-candidate terms remain allowed. The CLI output and JSON payload include `scanned_surfaces` so operators can confirm the QA coverage without reading code. `--recent-business-days N` can scan the latest Korean business dates without manually listing `--date` values. Observation/candidate text blocks are checked for internal public-score/trading-recommendation wording, but source report titles are treated as original report text and are not rewritten by this guard. Friend-facing category notices now use `최신 저장 분류 기준` instead of internal category mapping wording. Latest mini PC QA at `2026-05-17 08:41 KST` over `2026-05-15`~`2026-05-12` returned issue count `0` and warning count `1`; the remaining warning is unresolved stock code `351020` with no KRX metadata mapping, not a latest-KRX snapshot availability issue. |
| Web-view browser smoke | Added `web-view-browser-smoke` read-only CLI for local Playwright desktop/mobile smoke QA. It starts a temporary `127.0.0.1` web-view server, checks required daily briefing/search/tab elements, verifies the observation tab is clickable, verifies the `장중 거래대금 확인` button and `Naver 장중 참고` overlap panel are visible where expected, detects major horizontal overflow, confirms daily/candidate/stock-detail APIs return JSON, confirms `POST /api/daily/YYYY-MM-DD` is blocked with `405`, and confirms `/api/status` remains absent with `404`. The default run bypasses the configured access-code gate only by replacing the smoke server's access-code path with a temporary non-existent file, so no access-code value is requested or printed. Latest mini PC run at `2026-05-17 06:46 KST` over `2026-05-15` returned 0 issues, desktop/mobile overflow `0px`, four view tabs, stock search present, `POST /api/daily/2026-05-15` blocked with `405`, and `/api/status` absent with `404`. |
| External web-view smoke | `external-web-view-sharing-plan` now prints the read-only Cloudflare/Tailscale sharing sequence as a focused operator plan, while `external-web-view-smoke` checks more than liveness and `/api/status`: the final URL must not look like `admin-gui`, public archive/daily/candidate/stock-detail/flow-trend/ETF-trend/category-trend JSON must not expose known operator/admin keys, user data POST must be blocked, and known admin scheduler/operator/settings POST routes must return `404`/`405` or an access-gate denial. Its JSON output lists `public_json_routes_checked` so operators can confirm what the final URL smoke covered. It accepts `401`/`403` from Cloudflare Access or the app entry-code gate, and also treats a recognizable Cloudflare Access HTML/login page as access-gated, without accepting or printing the access-code. Add `--record-success` only after the final provider URL is the intended shared HTTPS origin, for example `https://view.example.com` with no path/query/fragment; localhost, loopback, HTTP, and path/query/fragment URLs are rejected for success recording. A valid recorded success writes a non-secret provider-smoke operation event so `next-phase-readiness.external_web_view_provider_smoke` can clear the external sharing blocker. `verify_cloudflare_web_view_tunnel.ps1` is the preferred post-provider wrapper because it combines local readiness, final provider smoke recording, and readiness recheck. |
| Test/runtime isolation | `RuntimeConfig.from_env()` now reads `.env` into an internal merged config map instead of mutating `os.environ`. This prevents a test that reads the project `.env` from leaking the live `STOCK_MONITOR_DB_PATH` into later tmp-path tests. A one-time cleanup restored known pytest fixture rows from the latest clean backup and rebuilt the affected `2026-05-14` daily summaries. |
| Web-view daily briefing | The top `오늘 읽을 요약` block now follows the same product axes as the Telegram market briefing: report flow, KRX index reference, turnover reference, investor-flow reference, notable-stock chips, and short check points. The daily DTO exposes these as structured `market_briefing` blocks plus legacy line arrays, so the page no longer has to infer product meaning by parsing display text. It avoids leading with unstable category summaries, opinion-derived buy/sell signals, or operator/process wording. Turnover reference uses briefing-only compact display values such as `11.9조`/`7709억` while retaining raw `turnover` for evidence DTOs. |
| Web-view observation summary | Added the first Phase C3 `observation_summary` daily DTO and `국장 관찰 요약` web-view block. It is read-only and stored-data by default; the separate manual `장중 거래대금 확인` button may fetch same-day Naver `priceTop` as a labeled `Naver 장중 참고` overlap reference only for the current Korean business day. It compresses stored report concentration, `[12009]` 5/10/20/31-day stock flow windows, price/volume position, and sector/theme breadth into display-ready `오늘의 관찰 후보`, `시장 분위기`, `리포트 집중`, `수급 참고`, and `과열 참고` blocks. The `시장 분위기` card now carries the sector/theme breadth context directly instead of leaving `시장 폭` as a detached low-weight card. The `리포트 집중` rows now include stored 5-business-day report intensity fields so a same-day concentration can be separated from repeated recent attention, displayed only as factual `5영업일 N건 · M일 언급` text when it adds context. They also include stored target-price revision context from the previous target-bearing report date, rendered as factual `목표가 저번 언급 대비 상향/하향/유지` text. The `과열 참고` rows include 20/60-day and 52-week price position, 5/20-day return, compact turnover, and 20-day volume multiple from stored KRX daily rows; 52-week text is displayed only when enough stored history exists, and the web-view exposes an info hover for the value meanings. The `수급 참고` rows now include foreign/institution flow persistence and recent turn-date text such as `순유입 전환 05.07부터 2일` when stored `[12009]` rows prove it; visible digest text suppresses one-day-only flips and renders the persistence phrase only from 2 consecutive stored business days. `observation-summary-audit` now reports detailed stored-data coverage for report intensity, target revision, flow windows, flow persistence, price/volume, 52-week position, and sector breadth before operators rely on visible blocks. Added `observation-summary-preview` as a manual Telegram-style preview that reuses the same DTO fields and does not send or schedule anything. QA blocks public trading-decision phrases such as buy/sell signal, entry/exit price, take-profit, target return, and conviction wording while preserving source report text handling. Category breadth display strings now use public category labels so fallback `N/A` does not leak into the preview. Selected-stock 수급 direction labels use `순유입/순유출` instead of buy/sell wording. Latest audit over 10 recent report dates showed full flow/price coverage for most stored dates; `2026-05-15` has flow windows for 25 of 28 eligible stocks and price/volume coverage for 25 of 28 after the latest KRX Open API snapshot fill. |
| Next-phase audit CLI compatibility | The read-only closeout audits now accept the document/operator prompt wording as aliases: `observation-summary-audit --recent-report-dates`, `candidate-evidence-readiness --recent-report-dates --stock-limit`, and `market-briefing-readiness --recent-report-dates`. Existing `--limit` and `--recent-business-days` options remain supported; the JSON payloads also expose `recent_report_dates` where applicable. |
| Next-phase readiness | Historical compatibility only. `next-phase-readiness` remains callable for old closeout scripts and notes, but current operation should use the minimal command set: `db-verify`, `candidate-evidence-readiness`, `web-view-value-qa`, `web-view-browser-smoke`, `krx-baseline-analysis`, and `market-day-observation`. |
| Ops readiness | Historical compatibility only. `ops-readiness` overlaps with `db-verify`, KRX baseline checks, web-view QA, and API perf review, so it is hidden from top-level help and should not be introduced as active workflow. |
| Market-briefing manual review path | `market-briefing-readiness` and `next-phase-readiness` now print the next bounded manual review send commands for preview-ready dates, for example `market-briefing --date YYYY-MM-DD --limit 5 --send`. The readiness commands stay read-only; only the explicit `--send` command records a `telegram_market_briefing` delivery with `source=manual`, which is what clears the manual phone review count. Their JSON includes `requested_min_manual_reviews`, `enforced_min_manual_reviews`, and `phone_review_gate` with the required/recorded review counts, acceptance flag, and enforcement surfaces; the required count never drops below the default three sends enforced by settings and scheduled live send. `operator-settings set market_briefing_phone_review_accepted true` and the local `admin-gui` settings API now both enforce the default three recorded manual review sends before they can set the acceptance flag, so the schedule gate cannot be opened by a premature setting change alone. |
| Telegram briefing | Added `--format summary|briefing` for `send-test-notification` and `scheduled-notify`. `scheduled-notify` now defaults to `briefing` for temporary live Telegram readability checks, while `send-test-notification` keeps `summary` as its default. The intended production order is official KRX Open API previous-business-day publication at `08:00`, `08:10` backfill, then `08:20` previous-day briefing with the latest available stored KRX rows. |
| Requirements anchor | `stock_research_monitor_mvp.md` was updated from the initial MVP memo into the current product requirements anchor covering Telegram, scheduler, admin-gui, web-view, KRX market data, investor flow, observation, and non-goals. |
| Scheduler metadata verification | On the current main PC, non-elevated `operator-status --json --health-exit` and `verify_task_scheduler_registration.ps1` report Task Scheduler metadata `access_denied`; that is a permission/elevation limitation and not evidence that tasks should be registered or changed. A prior elevated check showed this PC is a desktop-validation host with expected desktop tasks disabled and `StockMonitor-WebViewHourlyRestart` missing. The recovery action now points to `the current main-PC Python executable`, not `.venv\Scripts\python.exe`. `StockMonitor-KrxFlowLoginReminder` remains optional unless a deliberate KRX validation day needs it. |
| KRX latest-date check | Latest stored stock/ETF/index snapshot is now `2026-05-19`. At `2026-05-20 08:28 KST`, `2026-05-19` availability changed to mixed `partial/available` across all 6 daily endpoints with reference date `2026-05-19`, raw rows `4011`, and parsed rows `3701`; at `09:17 KST`, a backed-up bounded retry stored those rows with `incomplete_endpoints=0`. Same-day `2026-05-20` remained `not_published` through later probes, which is now expected under the official next-business-day `08:00` publication rule. The same-day probe automation was deleted on `2026-05-20`. |
| Category/taxonomy | Schema v5 `category_master` and `category_membership_snapshots` exist; dated snapshots are preferred, fallback is labeled and treated as operational debt. `category-snapshot-status` now separates fully dated, sector-dated, theme-dated, partial, and fallback counts. `category-snapshot-plan` includes the follow-up `web-view-value-qa --date YYYY-MM-DD --stock-limit 20` command plus JSON `missing_snapshot_types`, `source_date_capture_allowed`, `capture_block_reasons`, and compact `plan_summary` counts so historical dates are not silently filled with current category membership and operators can see whether any current-source-date refresh is actually allowed. The same Phase E status is now included in `next-phase-readiness.category_snapshots`. It also separates refreshable sector catalog entries from non-refreshable display/manual labels; `sector` rows are batch-refreshable only when `source=naver_industry` or `source=naver_upjong`. On `2026-05-15`, 8 verified Naver PC upjong rows were added as separate `source=naver_industry` catalog entries (`가정용품`, `광고`, `방송과엔터테인먼트`, `상업서비스와공급품`, `섬유,의류,신발,호화품`, `손해보험`, `전문소매`, `전자제품`) and refreshed into a `2026-05-15` dated sector snapshot. On the `2026-05-17` mini PC check, `category-snapshot-status --mode fallback --limit 100 --json` reported 90 summary dates, 6 fully dated dates, 1 partial dated date, and 84 fallback dates; `category-snapshot-plan --limit 100 --json` blocked all 84 for source-date refresh because the current source date is later than those summary dates. `db-verify` no longer reports `sector_catalog_not_refreshable`; older fallback dates remain intentional source-date debt. |
| Rotation overlay | `example/Cycle.jpg` is served with SVG overlay circles from `data/rotation_overlay_coordinates.json`; it is descriptive only. The `순환매` tab opens the overlay panel automatically so the image and evidence chips are visible without an extra expand click. The API now also uses `data/rotation_image_aliases.json` as the first image-text alias layer, so user-facing labels like `우주항공` can map to current sector names and coordinate keys without rewriting the coordinate file. Highlighted sectors include read-only `candidate_stocks` previews from same-date report summaries and exact-date KRX stock rows. ETF previews are allowed only through operator-managed `data/rotation_etf_candidates.json`, currently seeded for semiconductor and broad IT examples; active ETF mappings must also be reachable through an overlay coordinate or active alias. Added `rotation-mapping-audit` as a read-only CLI to show Cycle coordinates, active aliases, ETF mappings, exact-date stored ETF evidence, same-date stock evidence counts, and mapping issues before operators rely on the rotation preview. Latest live audit for `2026-05-15` showed 9 coordinates, 9 active aliases, 2 active ETF mappings, and 0 issues/warnings. |
| Security/access | Optional shared entry-code gate exists for both `admin-gui` and `web-view`; `data/access_code.json` stores PBKDF2-SHA256 salt/hash when enabled. |
| Admin no-run validation | Admin/CLI no-run date adds reject market holidays, env no-run dates, and past business dates so DB overrides remain future/same-day scheduler controls rather than stale historical annotations. |
| Docs | `candidate-evidence-plan.md` and `target-price-progress-plan.md` define observation evidence before scoring/recommendation work. Target gap/progress plus first stored-window max-progress/hit-day DTO/UI is implemented as observation-only context. |

## Current Stable Boundaries

| Boundary | Rule |
| --- | --- |
| `admin-gui` | Control-capable, local/operator-only. Do not expose publicly. |
| `web-view` | Public-safe friend-facing candidate. Data/control routes are GET-only, with bounded top-2 Toss current-price and provisional investor-flow references plus manual same-day `Naver 장중 참고` turnover overlap. Saved news observations are projected read-only; collection stays in CLI/scheduler paths. No scheduler control, shutdown, DB path, Telegram token, settings, admin audit, account/order, arbitrary Toss symbol, raw operator news payload, or trading-call exposure. |
| Broker/API lab | Toss Securities OpenAPI is promoted for the bounded server-derived top-2 current-price reference in `web-view` and the scheduled `09:15`/`12:00`/`15:15` market-briefing Telegram slots. Account/balance/order-info/order history stay operator-only lab candidates; live trading hookup, broker execution, order routing, production DB writes, arbitrary-symbol fetch, and admin-gui linkage remain blocked. |
| Reports | Naver source of truth. |
| Price/volume/turnover/ETF/index | KRX Open API source of truth. |
| Investor flow | KRX Data Marketplace source; stored read-only context. Automatic collection is limited to anchor-date mentioned stocks through `StockMonitor-KrxMentionedFlowBackfill`; broad scheduled ingest remains disabled. |
| 업종/테마 | Taxonomy/display layer, not official KRX taxonomy. |
| Candidate/rotation | `오늘의 관찰 후보`, `우선 확인`, `후보`, `참고`, `근거`, and `왜 눈에 띄는지` are allowed. No public numeric score, investment grade, or trading-call wording. |
| News intelligence | Operator-only preview/save/readback/daily-brief exists as a report-linked evidence lane. The next product step is a stored-data-only, public-safe `web-view` projection that shows labels/counts/reasons without numeric sentiment, impact scores, buy/sell wording, broker execution, or live fetch. |

## Still Unstable Or Needs Observation

| Item | Why It Is Unstable |
| --- | --- |
| Live scheduler behavior | Historical mini-PC scheduler verification remains trace evidence only. On the current main PC, `market-day-observation --date 2026-05-29 --json` is incomplete and shows missing evidence for TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill after their verify times. Scheduler registration or changes still require separate operator action; this docs sync did not run scheduler changes. |
| 2027+ market holidays | Built-in holiday list covers 2024~2026 KRX closures; future years still need manual update or a new holiday-source workflow. `operator-status` now exposes `market_holiday_coverage` and raises `market_holidays.default_coverage_expiring` from October 2026 if no verified future-year holiday dates are configured. |
| KRX Data Marketplace scheduled ingest | Request/sample/import paths exist. Only the narrow anchor-date mentioned-stock `[12009]` 31-day 보강 path is scheduled; broad `[12008]`/`[12010]` or all-stock scheduled ingest is intentionally disabled. |
| KRX latest dates | KRX stock/ETF/index snapshot rows currently cover `2024-11-08` through `2026-05-19`; stock-level `[12009]` investor-flow rows cover through `2026-05-15`, while market-wide flow and `[12010]` rows cover through `2026-05-12`. The `2026-05-29` baseline reports 6 missing publishable KRX Open API daily snapshot dates starting `2026-05-28`. The next normal action is guarded daily backfill after DB verification/backup discipline, not same-day probe automation or real-time intraday interpretation. |
| KRX login reminder | The CLI and task remain available for deliberate validation days, but the scheduler task is disabled during normal operation to avoid unnecessary Telegram prompts. |
| Category snapshots | `2026-05-15` now has a source-date sector snapshot from verified Naver upjong rows. Some older dates still rely on the latest stored category classification; source-date snapshots should be added deliberately, not by silently copying current mappings backward. |
| Rotation image mapping | Overlay, active image aliases, audit output, and card-style stock/ETF reference slots exist. Remaining work is broader alias/ETF coverage and optional admin correction, not the first user-facing V1. |
| Candidate evidence | `메인` now compresses the top-2 `우선 확인` candidates as today’s priority, while `관찰` carries the full candidate evidence and `리포트 후 흐름`. Rows can be ordered as observation candidates, but public numeric scoring remains blocked. |
| Backtest observation | BO-1~BO-7 exists, but the QA sample is still small. KRX stock/ETF/index rows currently cover through `2026-05-15`, while investor-flow rows currently cover through `2026-05-12`; missing future reaction windows must stay unavailable, not negative. |
| Scoring draft | Archived/hold. Existing SD-1~SD-5 notes can be used only to understand past research. The current product should improve evidence coverage, missing-data labels, and outcome snapshots instead of adding or tuning scores. |
| External sharing | Access-code gate exists and historical mini-PC Cloudflare smoke for `<external web-view provider URL>` is retained as trace evidence, but current operation should rely on the smaller web-view QA/smoke path first. `external-web-view-sharing-plan` and `web-view-startup-fallback-check` remain callable compatibility/closeout commands, but they are hidden from top-level help and should not be treated as daily workflow. The connection sequence stays explicit: start only `web-view` on `<loopback web-view target>`, point the provider only to that target, keep `admin-gui` private, keep an allow-list/access gate enabled, and use external provider smoke only when an actual provider URL is being checked. |
| User page search | Top-right stock search exists for the selected date; broader cross-date search remains future work. |

## 2026-06-30 Simplification Decisions

### Hidden scoring lane

- Status: archived/hold, not active product scope.
- CLI: `observation-weight-draft`, `observation-hidden-prototype`, `observation-hidden-holdout`, and `observation-hidden-holdout-sweep` are hidden from top-level help. Direct invocation remains only for compatibility and historical internal research.
- Public boundary: no public numeric score, grade, buy/sell wording, Telegram trading alert, daily briefing score, or web-view ranking copy may depend on these commands.
- Current replacement focus: stored evidence quality, missing-data labels, top-candidate review order, and later evidence snapshots.

### Readiness/audit command classification

| Decision | Commands | Reason |
| --- | --- | --- |
| KEEP | `db-verify`, `candidate-evidence-readiness`, `web-view-value-qa`, `web-view-browser-smoke`, `krx-baseline-analysis`, `market-day-observation` | These protect data quality, public boundary, and live operation evidence. |
| KEEP but narrow | `market-briefing-readiness`, `external-web-view-smoke`, `db-restore-smoke`, `krx-flow-login-check`, `krx-flow-capture-checklist`, `audit-log` | Useful only for a specific operator task; do not present as daily product checks. |
| MERGE candidate | `next-phase-readiness`, `ops-readiness`, `docs-hygiene-audit`, `data-source-lane-audit`, `admin-boundary-audit`, repeated closeout wrappers | They overlap on status/readiness and should collapse into fewer operator checks. |
| DEPRECATE in docs/help | `observation-feature-audit`, `observation-summary-audit`, `periodic-data-needs-audit`, `external-web-view-sharing-plan`, `web-view-startup-fallback-check`, `rotation-mapping-audit`, plus the hidden scoring commands | These are historical, narrow, or redundant with the minimal operating set. Direct invocation remains for compatibility. |
| REMOVE today | None | Code deletion is unsafe before dependency and link checks across scheduler/docs/tests. |

### CLI split preparation

| Group | Move priority | First target file | Tests to carry | Rollback |
| --- | --- | --- | --- | --- |
| Web-view QA/smoke | First | `src/stock_monitor/cli_web_view_checks.py` | `web_view_value_qa`, `web_view_browser_smoke`, public DTO boundary tests | Move functions back into `cli.py`; parser dispatch stays unchanged. |
| DB verification/smoke | Second | `src/stock_monitor/cli_db_checks.py` | `db_verify`, `db_restore_smoke`, migration/rehearsal tests | Restore imports and functions to `cli.py`. |
| KRX baseline/login checks | Third | `src/stock_monitor/cli_krx_checks.py` | `krx_baseline_analysis`, `krx_flow_login_check`, KRX parser/source tests | Revert import boundary only. |
| Deprecated closeout/audit wrappers | Last | no move before deletion decision | compatibility parser tests only | Leave in `cli.py` until links/tests are retired. |

### Evidence snapshot design v0

No schema change in this session. A future snapshot should persist, per exposed candidate and business date:

- candidate identity: `business_date`, `stock_code`, `stock_name`, report count, source report ids, collection time.
- exposure state: exposed surface, visible order, top-2/top-candidate flag, visible labels, visible `why_notable`, visible `missing_information`.
- feature snapshot: target/opinion availability, exact-date KRX price/turnover/index freshness, `[12009]` flow availability, foreign-rank availability, news observation run id/time, stale/missing flags.
- public boundary: whether any numeric score, grade, buy/sell wording, recommendation wording, or operator-only detail was blocked.
- outcome join keys: D+1/D+5/D+20 close/turnover/flow result availability and later linked result rows.
- validation method: compare exposed candidate order against report-only baseline and measure whether visible evidence/missing labels predicted which candidates deserved manual review, not whether a hidden score was high.

## Next Larger Work Axes

| Axis | Direction |
| --- | --- |
| Candidate evidence | Review visible `관찰` rows across stored dates and keep bad/missing values from improving the row. The first `오늘의 관찰 후보` pass now shows a `우선 확인 2개` shortlist plus missing KRX, stock flow, target, opinion, foreign-rank, and price/volume context as `부족한 정보` instead of treating missing data as negative evidence. |
| Report + market evidence interpretation | Keep improving how report concentration is tied to KRX/flow evidence. The near-term product should answer "why this is worth observing today" from stored facts, not claim predictive strength. Stronger claims require both a longer clean research baseline and a stable intraday API lane; until then, the 52-week/1-year market context should remain the main practical frame. |
| Target-price progress | Review the stored-data-only `target_price_progress` DTO across several dates. First max-progress and target-hit D+ fields now exist as `도달 참고`; keep reviewing whether the labels stay understandable before any stronger interpretation is discussed. |
| Backtest observation | Continue multi-date QA and tighten missing-value labels if more misleading cases appear. |
| Scoring draft | Hold. Do not spend active product time on hidden scoring sweeps until evidence snapshots prove which non-scored facts actually changed review quality. |
| Rotation ETF/stock preview | Cycle image labels now map to 업종 aliases, stock candidates are shown as evidence previews, and ETF previews are available only for sectors listed in `data/rotation_etf_candidates.json`. The same 수동 ETF mapping is also reused in selected-stock related context when the selected stock belongs to a mapped stored 업종/테마 on the selected date. Keep this as `참고`, not ranking or recommendation. |
| User web-view reset | Rework the friend-facing screen around five clear roles: `메인` = today’s briefing and top-2 priority, `관찰` = full candidate evidence plus report-after-flow, `종목` = selected stock detail/report, `시장` = stored market/flow reference, `순환매` = category/theme/ETF rotation context. Remove or hide raw/process-heavy tables that do not help daily reading. |
| News observation visibility | Add a compact stored news-observation summary to `web-view` after saved observations exist. First placement should be the `메인` top-2 priority card or the `관찰` tab, with explicit empty/low-coverage states instead of waiting for perfect model quality. |
| Turnover display cleanup | User `web-view` market reference, recent KRX flow, ETF trend, and admin KRX top-turnover rows use compact 조/억 turnover display rather than long raw won values. |
| Market briefing slots | `market-briefing-readiness` remains the read-only pre-scheduling audit. The only scheduled execution path is `scheduled-market-briefing-slot` at `09:15`, `12:00`, and `15:15`; it retains business-day, delivery-dedupe, phone-review, and slot-window guards. |
| User web-view search | Selected-date stock search exists. Future work is broader cross-date search only if the current-date lookup proves insufficient. |
| Category source-date cleanup | Reduce fallback dates through explicit source-date refreshes with dry-run, delay, confirm, and DB backup discipline. |
| Mini PC/external sharing | Migration handoff now includes before-copy checks, post-restore checks, scheduler task names including KRX backfill tasks, required scheduler script-file checks, explicit scheduler Python path guidance, required project/canonical handoff file checks, `.env.example` archive inclusion for target-side `.env` creation, user web-view/rotation asset checks, non-secret Telegram/KRX environment presence checks, the read-only `mini-pc-preflight` CLI, the bundled `setup_mini_pc_environment.ps1` environment bootstrap that skips env/backup/restore-smoke during first setup because the archive excludes `.env` and `data/backups`, the mini-PC-specific `register_mini_pc_scheduler_tasks.ps1` wrapper that skips `StockMonitor-Shutdown`, the source-desktop cutover helper `disable_source_desktop_scheduler_tasks.ps1` to prevent duplicate automation after migration, the bundled `verify_mini_pc_readiness.ps1` check runner with optional `-SkipEnvRequirement`/`-SkipBackupRequirement` for first setup, optional `-SkipWebViewBrowserSmoke`, and env/latest-backup restore smoke for final readiness, the scheduler-registration-only `verify_task_scheduler_registration.ps1` check, the external-share-only `verify_external_web_view_readiness.ps1` gate with public value QA plus browser/mobile smoke, the default-safe `create_migration_archive.ps1` migration package script, archive SHA256 transfer verification, archive required-entry verification, archive entry-count logging, default log-file exclusion, `.env`/`data/access_code.json`/backup/restore-smoke/log/nested-zip sensitive-entry warning, access-code preflight, separate admin/web session cookies, HTTPS-proxy `Secure` access-cookie behavior, web-view loopback-by-default host guard, and Cloudflare/Tailscale boundaries. `mini-pc-preflight` now reports `operation_profile` and accepts `--require-mini-pc-profile`; this mini PC is set to `operation_profile=mini-pc` through audited safe settings so scheduled shutdown is app-guarded as well as scheduler-excluded. `verify_external_web_view_readiness.ps1` also requires the mini PC profile and runs `web-view-browser-smoke` before any web-view sharing gate can pass; the `2026-05-17 09:30 KST` run passed with access-code enabled, mini-PC profile, latest backup present, web-view value QA issue count `0`, browser/mobile smoke issue count `0`, `POST` blocked with `405`, and `/api/status` absent with `404`. Keep Docker deferred, use Windows direct execution, expose only `web-view` if Cloudflare Tunnel is later configured, and keep `admin-gui` private. |
| KRX 18-month baseline | Stock/ETF/index Open API snapshots remain complete through the latest stored date `2026-05-19`, but the current `krx-baseline-analysis --json` target window reaches latest publishable date `2026-05-28` and reports 6 missing business dates. Keep using `krx-baseline-analysis` after future guarded daily backfills or cleanup work to confirm coverage, source-lane boundaries, retry evidence, and retention assumptions. |
| Live operation validation | Keep reviewing Telegram delivery fragments, intraday outbox, worker heartbeat, Task Scheduler status classification, and DB health. |

Implementation continuation (`2026-05-17`, updated `2026-05-19`): `web-view-browser-smoke --date latest --json` now resolves `latest` to the latest stored report date, so goal prompts and closeout loops no longer need to pre-convert that value manually. The explicit ISO date form still works. The closing-market `market-briefing` / `market-briefing-readiness` flow now falls back to stored report-mentioned stock `[12009]` lines when market-wide investor-flow rows are unavailable for the selected date. This keeps the public wording as `수급 참고`, uses only stored rows, does not send Telegram or register scheduler tasks during readiness checks, and avoids treating missing market-wide flow as a warning when relevant stock-level flow exists. On the mini PC, `market-briefing-readiness --recent-report-dates 5 --json` now reports preview-ready `5/5`, public-safe issue count `0`, data warning count `0`, manual review sends `3/3`, and `phone_review_accepted=true`; no new Task Scheduler task is registered until the next market-day schedule is reviewed against existing poll/flow backfill behavior.

## Immediate References

- `docs/codex/operating-guide.md`: next execution phases.
- `docs/codex/mini-pc-runbook.md`: weekly main-PC and mini-PC sync guide; generated sync notes and archives should go in `handoff/mini_pc_changes/`.
- `docs/codex/architecture-guide.md`: proposed responsibility split.
- `docs/codex/candidate-evidence.md`: candidate evidence before scoring.
- `docs/codex/candidate-evidence.md`: exact CE-1 DTO and rotation alias boundary.
- `docs/codex/candidate-evidence.md`: target gap/progress and report backfill preview boundary.
- `docs/codex/research-notes.md`: read-only post-report reaction and observation-tab plan.
- `docs/codex/research-notes.md`: archived/hold research note; not active product scope.
- `docs/codex/research-notes.md`: optional morning briefing format for the previous-business-day Telegram summary.
- `docs/codex/surface-guide.md`: admin/web-view and external sharing boundary.
- `docs/codex/data-governance.md`: source ownership and naming.
- `docs/codex/market-data-runbook.md`: KRX/ETF/flow operating rules.
- `docs/codex/surface-guide.md`: rotation overlay limits and next improvements.



<!-- Merged from: docs/codex/operating-guide.md -->
## Next Phase

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
| Make useful work visible | If a data lane is intended to support daily operator/user judgment, the next step should be a small labeled `web-view` projection, not another hidden CLI-only guard, once stored data exists. |
| Separate intent completion from foundation completion | A table, DTO, or DB path is not enough to mark a memo done if the intended screen or briefing is still missing. |
| Compress the shared page | Friend-facing `web-view` should not expose the full validation pipeline or repeated defensive disclaimers. Keep raw evidence, risk wording, and operational details in admin/docs. |
| Separate trading advice from observation curation | This project does not provide `매수 추천`, `매도 추천`, `진입가`, `청산가`, `익절가`, `목표 수익률`, `확신도`, or `투자등급`, but it can recommend what to observe first. `오늘의 관찰 후보`, `우선 확인`, `관찰 우선순위`, `관심도 높은 흐름`, `왜 눈에 띄는지`, `확인 후보`, `시장 분위기`, `수급 참고`, and `과열 참고` are valid product language. |
| Do not turn the current public limit into a permanent goal | The current public `web-view` and Telegram surfaces do not provide trading decisions because real-time data, source freshness, permission, failure handling, and execution safety are not ready. The long-term path can include an operator-only decision-support lane and later execution-lab after those gates are proven. |
| Keep broker/API work outside production | Do not add KIS, Toss Securities Open API, or any broker route to close current intraday gaps. Future Toss work should start only as a separated `broker-lab`/`execution-lab`/`toss-openapi-lab` path, beginning with docs and permission review, then read-only quote/account/balance probes. Once verified, intraday quote/turnover context may drive observation priority, but not trading execution. |
| Add closing-market briefing track | The next product axis includes a rough `16:00` market mood Telegram summary based on same-day reports, KRX market data, and available flow. |

## Web-View Completion Direction

Treat a feature as product-complete only when a user can follow its evidence to the next useful screen without reconstructing the connection mentally.

| Start | Required continuation | Completion signal |
| --- | --- | --- |
| `메인` top-2 candidate | `관찰` evidence and selected `종목` detail | Candidate has a visible observation reason and a working detail path. |
| `관찰` candidate | `종목` context plus market/rotation links | Detail keeps the selected candidate's report/news/intraday/Toss context. |
| Report target range | Stored target trail and stored-window reach reference | The page separates target range, current stored reference, and retrospective reach days. |
| Direct or caution news | Candidate/stock public-safe projection | Counts, freshness, and titles are visible without raw operator impact fields. |
| Intraday/Toss reference | Candidate and selected-detail context | Current quote, intraday overlap, and 20:00 baseline remain distinct time layers. |

Stop rule: do not replace missing stored data with a new explanatory card. Link to the existing collection/storage lane or show the actual unavailable state.

## Realtime-First Pruning Direction

Use [surface-guide.md](surface-guide.md) for the detailed plan.

The next web-view and Telegram refinement should prune order and emphasis before adding new features:

| First-read order | Meaning |
| --- | --- |
| `오늘 볼 것` | Top-2 candidates and one visible observation reason. |
| `현재 근거` | Same-day saved news, approved current quote/turnover, checked time, and source state when available. |
| `전일 참고` | KRX daily, `[12009]` flow, ETF, and stored Toss baseline as labelled fallback/detail. |
| `부족한 근거` | Missing current quote, no saved news, stale KRX, missing exact stock flow. |
| `복기/연구` | Reaction windows, backtest, X recap lab, and long validation items. |

Closeout should come from a 10-business-day operating review log, not a single browser-smoke pass. Existing TODO2 live checks remain active, but their completion now depends on whether current evidence helps the first read and whether previous-day/reference evidence distracts from it.

## Observation Evidence Maturity Direction

The next candidate-evidence work should improve judgment quality, not visible label volume.

| Step | Goal | Implementation gate |
| --- | --- | --- |
| 1 | Make top candidates explainable by visible public evidence. | Public ordering must be justified by `why_notable` / `evidence_layers.primary`, not hidden diagnostics or support-only facts. |
| 2 | Strengthen current-regime context. | Use exact-date KRX, `[12009]` flow, and 52-week/1-year price-volume context as support; do not turn them into public scores. |
| 3 | Surface stored news observations visibly. | Saved news observations should feed a public-safe `web-view` summary label before they feed public candidate scoring. Empty, low-coverage, stale-KRX, and market-context-heavy states should be visible as caveats, not hidden. |
| 4 | Prepare future intraday lane separately. | Top-2 `우선 확인` 5-minute read-only probing belongs in lab/staging only after source burden and permission review; when proven stable, it should affect observation ordering and main-card emphasis. |
| 5 | Prepare an operator-only decision-support boundary only after real-time evidence is stable. | This is where trading-decision review may begin. It must not be collapsed into public `web-view`, Telegram alerts, or broker execution. |

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

IA/performance note (`2026-05-18`, updated `2026-06-04`): the page now uses five task tabs. `메인` owns daily briefing and top-2 priority overview; `관찰` owns `오늘의 관찰 후보` plus read-only reaction rows; `종목` owns selected-stock context, reports, and stock-level daily summary; `시장` owns stored KOSPI/KOSDAQ/index and investor-flow references; `순환매` owns category/theme/ETF rotation context. Hidden tab payloads are lazy-loaded, and the daily DTO no longer embeds the heavier `candidate_evidence` payload. Candidate cards render only user-facing `왜 눈에 띄는지` and `부족한 정보`, while raw `quality_flags` remain a DTO/testing/operator-review concern. ETF reference rows are intentionally not duplicated in the market tab because ETF evidence is reviewed in `순환매`.

Surface role note (`2026-06-04`): `admin-gui` has been trimmed back to operations/status/control content. Market mood, recent report/category rollups, KRX market reference tables, ETF rows, candidate evidence, and stored news evidence badges should stay out of the admin screen body. Public-safe stored-data projections belong in `web-view`; raw judgment review belongs in a future private `operator-review` surface.

Performance closeout note (`2026-05-19`): the public `web-view` no longer renders the operator-facing `주기 데이터 점검` block or ships `periodic_data_needs` in the daily DTO; the CLI audit path remains available for operation review. Public-safe GET JSON routes now have a short in-process 30-second cache, archive category mapping is batched across archive dates, and daily snapshot generation reuses recent KRX/flow date lookups plus the already-built market briefing for one-line comments. The latest mini PC measurement puts archive generation at about `10ms` for 100 dates after warmup and latest daily generation at about `0.8s~1.0s`, keeping the shared page closer to a compact briefing surface instead of a validation/process viewer.

Operator-memo closeout note (`2026-05-18`): the remaining domestic `[△]` memos now have user/ops-facing V1 output rather than CLI-only foundations. `국장 관찰 요약` renders sector/theme breadth as graph-like bars; `관찰` starts with a top-2 `우선 확인` shortlist; and `순환매` renders separate card rows for image-label evidence, `순환매 참고 종목`, `순환매 참고 ETF`, and missing information. The implementation stays stored-data-only and read-only for `web-view`; it does not add public scores, grades, buy/sell wording, scheduler changes, broad KRX ingest, automatic `[12008]`/`[12010]`, secrets, admin controls, or DB paths.

Main briefing refinement note (`2026-05-19`): `오늘 읽을 요약` now treats the three review slots as time-anchored reading moments: `장초반 / 09:15`, `점심 / 12:00`, and `장 마감 전 / 15:15`. The opening slot is anchored to the previous stored report date and shows only a narrow prior-day candidate read; this prevents the morning block from leaning on same-day reports before they exist. The former large `리포트 흐름` metric is now part of `한줄평`, while the remaining metric cards focus on index, turnover, and `[12009]` flow references.

Historical mini-PC closeout notes are trace evidence only. They do not define the current scheduled market-briefing path, which is the three-slot contract below.

Main-PC continuation note (`2026-05-29 22:24 KST`): the active goal is not complete. Read-only `next-phase-readiness --recent-report-dates 5 --stock-limit 20 --json` reports `completion_ready=false`, latest report date `2026-05-15`, market-briefing manual review sends `0/3`, `phone_review_accepted=false`, and KRX daily snapshots missing for 6 publishable business dates starting `2026-05-28`. `market-briefing-readiness --recent-report-dates 5 --json` remains preview-ready for `5/5` dates with public-safe issue count `0`; it reports data warning count `2` from stored flow fallback on older preview dates, but the scheduling gate is blocked by manual review sends `0/3`. `krx-baseline-analysis --json` reports stock/ETF/index tables through `2026-05-19`; the next missing daily snapshot dates are `2026-05-28`, `2026-05-27`, `2026-05-26`, `2026-05-22`, and `2026-05-21`, each missing all six daily endpoints. `market-day-observation --date 2026-05-29 --json` is incomplete and marks TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill as missing after verify times. `web-view-startup-fallback-check --json` reports `configured=false`, missing current-user `StockMonitor-WebView.lnk`, and local `/health` status `0`. External provider smoke remains unrecorded on this PC. No Telegram send, scheduler registration/change, KRX snapshot write, broad ingest, public scoring, broker integration, order routing, or trading recommendation output was performed during this refresh.

Historical main-PC `2026-05-20` observations remain trace evidence for the official KRX next-business-day `08:00` publication rule and the successful `2026-05-19` guarded backfill. They are superseded for active closeout planning by the `2026-05-29` readiness snapshot above.

## Phase C: Candidate Evidence Foundation

| Work | Detail | Done Criteria |
| --- | --- | --- |
| `candidate_evidence` DTO/UI | Computed DTO/API exists and `web-view` has a separated `관찰` tab. | UI shows evidence, not score. |
| Exclusion rules | Apply valid stock code, missing target/opinion, insufficient flow coverage, and fallback category labels. | Bad/missing values do not improve a row. |
| Web-view preview | Review visible `오늘의 관찰 후보`, `눈에 띄는 종목`, and `리포트 후 흐름` rows across several dates. | The page recommends observation targets, not trades. |
| Observation compression | First pass implemented: show practical `오늘의 관찰 후보` / `우선 확인` / `확인 후보` rows first, including a top-2 `우선 확인` shortlist, with `왜 눈에 띄는지` and `부족한 정보` chips. | Useful candidates are not buried behind validation-only fields. |
| News observation projection | Use saved `news_intelligence_runs` / `report_linked_news_evidence` rows to show compact public-safe news context in `메인` or `관찰`. | Show `뉴스로 후보 강화`, `주의 뉴스 확인`, `시장 맥락 참고`, `KRX 기준일 확인 필요`, or `뉴스 근거 부족`; do not show sentiment scores, numeric impact, buy/sell wording, live fetch, or DB write controls. |
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
| News intelligence | Add article-level news context for the operator-only recommendation-draft lane. | Manual/in-memory news input, dedupe, sentiment, event impact, top news, and operator summary JSON. | Default preview stays no-write; only explicit operator `--save-observation` may write operator-only observation rows. No scheduler, Telegram, public `web-view`, broker execution, or order routing in v1. |
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

External quant experiment note (`2026-05-19`, policy updated `2026-06-03`): local read-only observation CLIs remain the primary basis for candidate ordering. A bounded historical Kronos research run was added under `scripts/experimental/kronos_backtest_experiment.py` and executed only against stored KRX OHLCV and stored report candidates. A full stored-candidate sweep over `2026-01-02`~`2026-05-15` with `mention_count >= 2` produced mixed results: D+1 evaluated `475/493` with direction hit rate `0.4884`; D+5 evaluated `405/493` with hit rate `0.4864` and the negative-prediction bucket had higher actual return than the positive bucket; D+10 evaluated `333/493` with hit rate `0.5435`, positive-prediction bucket average actual return `6.2372%`, and negative-prediction bucket `3.5915%`; D+20 evaluated `293/493` with hit rate `0.5119`, but April D+20 remained weak and the model showed a broad negative-return bias. Kronos is not in the current active global baseline; keep these outputs as historical research-only references unless the lane is explicitly re-enabled. QuantDinger and other external comparison candidates remain setup/environment work until their required runtime is available; document them as environment-required, not as usable implementation dependencies. Botasaurus is archived/reference-only; use `scrapling-official` for new bounded source-validation/browser-probe work.

CLI compatibility note (`2026-05-17`): the read-only closeout audits now accept the report-date wording used in this document and operator prompts. `observation-summary-audit --recent-report-dates N`, `candidate-evidence-readiness --recent-report-dates N --stock-limit M`, and `market-briefing-readiness --recent-report-dates N` are aliases for the existing bounded audit options. `observation-reaction-distribution --json` can omit `--from-date/--to-date`; when omitted it derives the stored `daily_stock_summaries` baseline range and remains read-only/internal-only. The commands remain read-only and do not send Telegram or register scheduler tasks.

Historical mini-PC aggregate readiness note (`2026-05-17`): `next-phase-readiness` provides a read-only top-level closeout snapshot for this document. It aggregates latest report coverage, observation-summary coverage, internal-only observation-reaction coverage, candidate-evidence review readiness, closing-market briefing readiness, KRX baseline missing-snapshot status, DB safety, category snapshot cleanup status, rotation mapping readiness, market holiday coverage, remaining non-code dependencies, the next market-day observation plan, the actual scheduled-run observation audit, the external `web-view` sharing plan, and the current-user `web-view` Startup fallback state without live fetches, DB writes, Telegram sends, scheduler registration, public numeric scoring, trading-recommendation output, or tunnel/provider configuration. The mini-PC trace from `2026-05-17` is retained below for provenance, but it is not the active main-PC gate state. On that mini PC data, the latest report date was `2026-05-15` with 51 reports and 28 summary stocks; KRX Open API daily snapshots covered through `2026-05-15` with missing count `0`; `observation_reaction` covered the stored `2026-01-02`~`2026-05-15` summary baseline with 493 `mention_count >= 2` candidates, completed windows D+1 486/493, D+5 427/493, D+10 344/493, and D+20 296/493, and remained `internal_only=true` / `public_surface_ready=false`; candidate-evidence review was ready for 5/5 recent report dates with 0 QA issue dates; closing-market briefing preview was ready for 5/5 dates, manual Telegram review sends were recorded for 3/3 dates (`2026-05-15`, `2026-05-14`, `2026-05-13`), and `db_safety.latest_backup_restore_smoked=true` for latest backup `<stock_monitor_backup.db>`. Cloudflare provider smoke for `<external web-view provider URL>` was recorded there and `external_web_view_provider_smoke.ready=true`. Re-evaluate these gates with the current main-PC `next-phase-readiness` output before marking anything complete.

Startup fallback note (`2026-05-17`): `web-view-startup-fallback-check --json` verifies the current-user Startup shortcut, the canonical `scripts/run_web_view.ps1` runner, the shortcut setup script, and local `<loopback web-view URL>/health`. It is a local web-view availability gate, not a Cloudflare configuration command. Use `--record-success` only after confirming the logged-in Windows session started the read-only `web-view` through the Startup shortcut after logon/reboot; the recorded event stores only non-secret local target and health status evidence. The fallback starts after user logon, not as a pre-login service, and it must continue to target only `web-view`, never `admin-gui`.

Final closeout wrapper note (`2026-05-17`): `verify_next_phase_closeout.ps1 -Date YYYY-MM-DD` is the broad readiness wrapper for the final stretch and is now surfaced first in `next-phase-readiness.next_commands`. It runs `db-verify --json`, local `web-view` Startup fallback health, optional `-RecordStartupFallbackSuccess` recording after a real logon/reboot, operator health, Task Scheduler registration verification, the dated `market-day-observation --json`, direct `observation-summary-audit --json` feature-availability review, direct `observation-reaction-distribution --json` reaction-window coverage review, direct `candidate-evidence-readiness --json` target-progress review, direct `market-briefing-readiness --json` phone-readability/scheduling-gate review, direct `web-view-value-qa --json`, direct `web-view-browser-smoke --json`, direct `external-web-view-sharing-plan --json`, direct `category-snapshot-status --json` and `category-snapshot-plan --json` fallback/refreshability review, direct `rotation-mapping-audit --json` Cycle/ETF mapping review, direct `krx-baseline-analysis --json`, and aggregate `next-phase-readiness --json`. The wrapper's `-Date` is only for market-day observation; rotation mapping intentionally uses its own latest stored report/KRX date default. By default it is read-only and does not send Telegram, register tasks, configure Cloudflare, fetch live KRX data, expose `admin-gui`, or print access-code/secrets.

Market-day observation usability note (`2026-05-17`): `market-day-observation` and the nested `next-phase-readiness.market_day_observation_audit` now expose `next_due_check` and per-check `verify_after_at` timestamps so the next real scheduled-run observation can be followed without translating relative times. For the `2026-05-18` first mini-PC market day, the current sequence is TelegramCommands `08:05`, KRX daily backfill `08:20`, Notify `08:30`, Poll `09:00`, and KRX mentioned-stock flow backfill `16:10` KST. The market-day-specific wrapper remains `verify_market_day_observation.ps1 -Date YYYY-MM-DD`, followed by the same-date `market-day-observation --date YYYY-MM-DD --json` rerun command, making the due-time audit explicit. The wrapper runs operator health, scheduler registration verification, market-day observation, `db-verify`, and `next-phase-readiness` in one elevated local PowerShell flow. `next-phase-readiness.completion_gates` now also shows whether the market-day observation gate is ready and points to the same dated wrapper as the preferred focused action, while the broader `verify_next_phase_closeout.ps1` wrapper sits above it in `next_commands`.

External provider smoke closeout note (`2026-05-17`, historical mini-PC trace): final shared-URL verification has a durable closeout path and was closed on the mini PC for `<external web-view provider URL>`. `external-web-view-sharing-plan --json` prints the read-only Cloudflare/Tailscale operator sequence without configuring a provider, touching scheduler state, or exposing secrets. `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL` remains the preferred recheck wrapper after provider/runtime changes; it rejects HTTP, localhost/loopback, and path/query/fragment URLs, always checks `.env` presence, latest backup presence, the mini-PC profile, and enabled access-code gate, reruns full local external readiness unless skipped, runs `external-web-view-smoke --record-success`, and then reruns `next-phase-readiness`. `external-web-view-smoke` remains read-only by default, but `--record-success` records a non-secret `operation_events` success row only when `issue_count=0` and the URL is a non-loopback HTTPS provider origin. Localhost, loopback, HTTP, and URLs with path/query/fragment cannot close this gate. The record stores URL origin, selected business date, HTTP check count, and public JSON route count; it does not accept or print the access-code. On this main PC, the current `next-phase-readiness` still reports provider smoke as not recorded, so rerun the provider wrapper only after the final URL/runtime is intentionally prepared.

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
| Schedule candidate | `scheduled-market-briefing-slot` is the only scheduled CLI path, with `mood` (`09:15`), `lunch` (`12:00`), and `preclose` (`15:15`) business-day, no-run, repeat, and slot-window guards. | Do not register a Task Scheduler task until manual phone readability is acceptable and it does not compete with existing poll/flow backfill behavior. |

Current implementation note: `market-briefing-readiness` provides the read-only pre-scheduling audit. It exposes the phone-review gate, delivery and source fallback warnings, and the three slot windows through `schedule_candidate_window`; `scheduled-market-briefing-slot` rechecks those guards before send.

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

Current implementation note (`2026-05-17 18:00 KST`): `mini-pc-preflight` reports the effective `operation_profile` and can require `--require-mini-pc-profile` for final always-on readiness. On this mini PC, `operation_profile` has been set to `mini-pc` through audited `operator-settings`; elevated `verify_task_scheduler_registration.ps1` confirms the five default mini-PC tasks are registered/enabled and `StockMonitor-Shutdown` is absent. The verifier now distinguishes Task Scheduler metadata access-denied from genuinely missing task registration, so non-elevated shells do not imply scheduler repair. The external web-view readiness script also requires `--require-mini-pc-profile`; the latest local and provider checks passed with access-code enabled, latest backup present, value QA issue count `0`, browser/mobile smoke issue count `0`, `POST /api/daily/2026-05-15` blocked with `405`, `/api/status` gated or absent, and Cloudflare provider smoke issue count `0` for `<external web-view provider URL>`. Restore-smoke against backup `<stock_monitor_backup.db>` verifies the copied DB before removing it. Friend-facing sharing is now provider-smoked for the read-only `web-view`; keep `admin-gui` private and re-run the provider wrapper after Cloudflare, access policy, or local runtime changes.

KRX planning note (`2026-05-17`, updated `2026-05-20`): `scheduled-krx-daily-backfill --dry-run --json` now returns machine-readable skip output for weekends/holidays, and `krx-backfill-missing ... --dry-run --json` returns the missing-endpoint plan. JSON mode is planning-only for this lane so live KRX Open API fetches keep the backed-up text log and operation-event path. On the mini PC, `StockMonitor-KrxDailyBackfill` is intended to run at `08:10` KST on Korean business days, after the officially confirmed next-business-day `08:00` publication window, targeting only the previous business day or earlier missing daily stock/ETF/index snapshots.

Holiday coverage note (`2026-05-17`): `operator-status` now reports `market_holiday_coverage` with the built-in/default coverage end date and configured coverage end date. From October 2026 onward, it raises `market_holidays.default_coverage_expiring` unless verified future-year KRX holiday dates are configured.

Latest-day retry note (`2026-05-17 08:17 KST`, updated `2026-05-19 01:25 KST`): after backup `data/backups/<stock_monitor_backup.db>`, a bounded live `krx-backfill-missing daily --to-date 2026-05-15 --max-dates 1` retry filled all six daily Open API endpoints for `2026-05-15`: ETF 874 rows, stock 2701 rows, and index 127 rows, with `incomplete_endpoints=0`. A post-success backup `data/backups/<stock_monitor_backup.db>` was created and restore-smoked successfully. For `2026-05-18`, backup `data/backups/<stock_monitor_backup.db>` was created and a bounded live retry reached all six daily endpoints, but every endpoint returned `0` parsed rows and recorded `incomplete_endpoints=6`. The backup was restore-smoked successfully and DB verification remains clean. Retry later only after `db-verify`, a fresh backup if needed, and a bounded `krx-backfill-missing daily --to-date 2026-05-18 --max-dates 1`; do not fetch same-day `2026-05-19` pre-market rows.

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

Development branch rule: keep feature/lab branches small for isolated work, but merge review-ready visible slices back into `dev` so the current experimental product state can be inspected in one place before any operating-PC application.

1. Finish operational closeout checks while real market data continues to arrive.
2. Keep user `web-view` stock search and tab split stable, and use `GET /v2` as the first preview route for the clearer next web-view information architecture.
3. Review `candidate_evidence` visible rows across stored dates without scoring.
4. Review stored `target_price_progress` rows across several dates and keep wording as `괴리율/진행률`, `관찰 후보`, or `우선 확인`, not trading recommendation.
5. Build non-operational enhancement metrics first: report concentration, `[12009]` flow windows, price/volume position, sector breadth, and display-ready observation summary blocks.
6. Run feature availability and reaction-distribution audits before any scoring prototype.
7. Review the first hit-days/max-progress validation fields across several stored dates before any stronger interpretation is discussed.
8. Keep report-based conclusions framed by the current 52-week/1-year market regime; use 3-year data as an offline validation baseline, not as a reason to overrule recent market structure.
9. Add a stored-data-only news observation summary to `web-view` once saved observations exist; keep it visibly labeled even when coverage is low.
10. If the source burden is acceptable, evaluate a read-only 5-minute probe only for the top-2 `우선 확인` candidates before discussing broader intraday coverage.
11. Treat time-slot priority (`09:15`, `12:00`, `15:15`) as a future stage that requires stable intraday quote/turnover/index APIs before stronger same-day ordering claims.
12. Start Cycle image label alias mapping for rotation ETF/stock preview.
13. Prepare mini PC/external sharing only after the user page is stable.



<!-- Merged from: docs/codex/operating-guide.md -->
## Execution Roadmap

## Purpose

This is the consolidated working roadmap for `02.Stock_Moniter`.

It combines the current implementation state, operator memos, admin GUI review, user web-view planning, and subagent feedback. Use this as the first planning reference before starting the next implementation batch.

## Current Product Shape

The canonical web-view completion path is [Web-View Completion Direction](operating-guide.md#web-view-completion-direction), and the canonical evidence interpretation rules are [Evidence Direction Rule](data-governance.md#evidence-direction-rule). This roadmap tracks delivery state without duplicating either contract.

## Current Command Surface

New operating docs should use the minimal verification set first: `db-verify`, `candidate-evidence-readiness`, `web-view-value-qa`, `web-view-browser-smoke`, `krx-baseline-analysis`, and `market-day-observation`. Older aggregate closeout/audit commands such as `next-phase-readiness`, `ops-readiness`, `docs-hygiene-audit`, `data-source-lane-audit`, `external-web-view-sharing-plan`, `web-view-startup-fallback-check`, and `rotation-mapping-audit` remain historical/operator-compatibility commands and are hidden from top-level CLI help.

| Area | Status | Notes |
| --- | --- | --- |
| Documentation structure | Canonical map fixed | `documentation-index.md` now defines which docs are authoritative and which older files are detailed references. |
| Naver research collection | Working MVP | Domestic stock research page is collected and deduped locally. |
| Data source policy | Fixed | Naver owns reports, KRX owns market reference data, and 업종/테마 are treated as a separate taxonomy layer. |
| SQLite storage | Working MVP | Reports, summaries, delivery logs, sectors, themes, category snapshots, operator controls, safe app settings, admin audit log, worker heartbeat state, fragment resume state, FK enforcement, and schema migrations exist. |
| Telegram notifications | Working MVP | Daily summary, intraday alerts, paging, stock search, memo capture, read-only status helpers, fragment resume, and filtered paging are implemented. |
| Windows Task Scheduler | Working MVP | Notify, poll, command worker, KRX daily backfill, KRX mentioned-stock flow, and hourly web-view restart tasks are registered for mini PC operation; the desktop-validation shutdown path exists but `StockMonitor-Shutdown` is intentionally absent on the mini PC. Shutdown run-now is blocked from CLI/GUI control paths. |
| Daily summary filters | Done | Low-signal one-off and no-target-price reports can be filtered from notification output. |
| Intraday paging | Done | Intraday output is limited and controlled with `다음`, `전부`, and `처음`. |
| Admin GUI | First control pass | Local dashboard exists with scheduler cards, calendar, reports, deliveries, events, sector/theme/mood cards. |
| Sector rollup | First pass done | Sector summary can be displayed from stored report data. |
| Theme rollup | First pass done | Theme membership refresh exists and theme summaries are shown in admin. |
| Market mood | First pass done | Simple market mood summary exists. |
| 사용자용 web-view | V1 closeout | Separate GET-only `web-view` command/server exists with archive, daily summary, stock/category detail, intraday API, and market reference APIs; the visible shared page is slimmed to report/category/market reading rather than operator-style diagnostics. |
| News intelligence | Operator evidence lane with visible stored projection | Naver 5-lane manual preview, explicit single-stock `--save-observation`, guarded batch `news-intelligence-briefing-collect --save-observation --confirm-save`, readback, text summaries, candidate linkage evaluation, and daily brief exist. Saved observations now feed actual `market-briefing` and GET-only `web-view` stored projections without scheduler, Telegram auto-send, admin-gui, public live fetch, public score, or trading-call behavior. |
| ETF / flow analytics | Raised planning priority | KRX Open API snapshots exist for price/volume/turnover, and KRX Data Marketplace screens `[12008]`, `[12009]`, `[12010]` now have screen-backed request candidates. Scoring remains deferred. |
| US market data expansion | New memo | Investigate official/semi-official US market APIs later; no implementation yet. |

## Progress Snapshot

Snapshot date: `2026-05-29`

These percentages are planning estimates, not formal release metrics. They combine local project state with read-only readiness audits. Historical mini-PC closeout evidence remains useful trace evidence, but the current planning baseline is the main-PC `2026-05-29` readiness state.

## Current Completion Rebaseline

This is the current decision baseline for planning. It intentionally separates the runnable domestic MVP from future expansion items.

| Scope | Completion | Meaning |
| --- | ---: | --- |
| Current domestic MVP on the main PC, excluding broad public sharing and US market expansion | 85-90% | Code, DB, admin-gui, user `web-view`, KRX/Data Marketplace read-only references, parser drift fixtures, and observation/backtest foundations are usable, but the current PC is not closeout-ready. The `2026-05-29` read-only audit blocks on manual market-briefing review sends `0/3`, `phone_review_accepted=false`, KRX Open API daily snapshots missing for 6 publishable business dates starting `2026-05-28`, real scheduled-run evidence missing for `2026-05-29`, missing `web-view` Startup shortcut, and unrecorded external provider smoke. |
| Current domestic MVP, including public trading recommendation or scored investment decisions | Out of current scope | Public numeric score, investment grade, Telegram trading alert, and buy/sell wording are excluded from the current product. Archived hidden/internal scoring-draft CLIs are not a path to product completion. |

| Axis | Current Completion | Next Increase Condition |
| --- | ---: | --- |
| 리포트 수집/요약/Telegram | 80-85% | Stored previews are usable and market-briefing previews are public-safe for 5/5 recent dates, but the current main-PC manual review gate remains `0/3` and `phone_review_accepted=false`. |
| Scheduler / 운영 안정성 | 75-80% | Historical mini-PC scheduler verification is trace evidence only. On the current main PC, `market-day-observation --date 2026-05-29 --json` is incomplete and all expected scheduled-run evidence is missing after verify times. |
| DB / schema / backup / verification | 97% | Keep `db-verify`, backup, restore-smoke, cleanup guard, and KRX backfill discipline green after future bulk data changes. Read-only diagnostics now check current schema without running the schema initializer when the DB already exists, reducing avoidable SQLite write-lock contention during parallel health checks. `db-restore-smoke` now records a local operation event, and `next-phase-readiness.db_safety` blocks completion when the latest backup is missing, lacks a matching successful restore-smoke, or `db-verify` has failing checks. |
| 사용자용 web-view | 90-93% | Direction reset is underway and the five-tab GET-only user surface is the current target. Historical mini-PC provider smoke remains trace evidence; on the current main PC, external provider smoke is not recorded and the Startup shortcut is missing, so local fallback health is not proven. |
| News intelligence / report-linked evidence | 82-86% | Operator-only collection, judgment, save/readback, candidate linkage evaluation, daily brief, and guarded batch collection exist. Saved observations are now product-visible in `market-briefing` and `web-view` as public-safe labels/counts/reasons without sentiment scores, numeric impact, or trading calls. The remaining increase condition is real operator sample collection over current market days plus value QA/readability review, not enabling scheduler/public live fetch. |
| admin-gui | 85% | Validate controls in live operation and refine status/log/settings UX without exposing admin externally. DB backup/verify reminders, readable recent-event summaries, and read-only recovery guidance are now visible in the operator status surface. |
| KRX / 수급 / ETF | 88-91% | Open API daily snapshots are stored through `2026-05-19`, but the `2026-05-29` baseline reports 6 missing publishable daily snapshot dates starting `2026-05-28`. Expand investor-flow coverage only through guarded/manual or separately approved scheduled ingest. |
| 관찰 후보 추천 / 백테스트 / 점수화 초안 | 84% | Build `오늘의 관찰 후보` ordering from stored evidence; the public `관찰` tab now has a top-2 `우선 확인` block, while reaction windows stay read-only and public numeric scores, investment grades, and trading calls remain blocked. Future approved intraday references may affect observation ordering; later trading-decision support must be operator-only and separately gated. |
| Documentation / roadmap consistency | 90% | Keep this roadmap, `current-work`, `next-phase`, source policy, and changelog synchronized whenever implementation moves. |

Historical aggregate `next-phase-readiness` audit (`2026-05-29`):

| Check | Current Evidence |
| --- | --- |
| Overall practical completion | Current main-PC domestic MVP remains about `85-90%` excluding broad public sharing and US expansion. Public numeric scoring and trading recommendations are separate non-goals, not blockers for `오늘의 관찰 후보`. |
| Read-only audit scope | `next-phase-readiness`, `market-briefing-readiness`, `krx-baseline-analysis`, `web-view-startup-fallback-check`, and `market-day-observation` were run without DB writes, Telegram sends, scheduler registration, public scoring, or recommendation output. |
| Market-day observation usability | `market-day-observation --date 2026-05-29 --json` reports `status=incomplete` and `observed_enough_for_scheduler=false`; TelegramCommands, KRX daily backfill, Notify, Poll, and KRX mentioned-flow backfill evidence are all missing after verify times. |
| Continuation verification | `2026-05-29` checks reconfirm active blockers: manual market-briefing sends `0/3`, phone review not accepted, KRX daily snapshots missing from `2026-05-28` backward for 6 business dates, missing real scheduled-run evidence, missing Startup shortcut, and unrecorded external provider smoke. |
| Elevated scheduler health recheck | `2026-05-17 17:02 KST` elevated local `verify_task_scheduler_registration.ps1` and `operator-status --json --health-exit` passed. The five default mini-PC tasks are registered/enabled/`Ready` for `2026-05-18`, `operator-status.health.level=ok`, and `StockMonitor-Shutdown` remains absent. The remaining scheduler closeout item is real market-day observation after the tasks become due. |
| Cloudflare pre-provider local gate | `2026-05-17 17:11 KST` `access-code status`, `external-web-view-sharing-plan --json`, and `verify_external_web_view_readiness.ps1` reconfirmed that the only allowed tunnel target is `web-view` on `<loopback web-view URL>`, access-code is enabled, mini-PC profile is active, latest backup exists, value QA issue count is `0`, browser/mobile smoke issue count is `0`, `POST /api/daily/2026-05-15` returns `405`, and `/api/status` returns `404`. Provider binding and final HTTPS URL smoke were later completed for `<external web-view provider URL>`. |
| Cloudflare provider smoke | `2026-05-17 17:46 KST` final smoke for `<external web-view provider URL>` passed and recorded an `external-web-view/provider-smoke` success event. The unrestricted network run reported issue count `0`, `/health` `200`, unauthenticated user routes `401`, user-data write `405`, and scheduler/operator/settings control POST routes `405`; `next-phase-readiness.external_web_view_provider_smoke.ready=true`. |
| Expanded closeout wrapper | `2026-05-17 20:51 KST` elevated/local `verify_next_phase_closeout.ps1 -Date 2026-05-18` passed with operator and Task Scheduler checks included. It verified DB integrity/schema, local web-view health, operator health, five mini-PC scheduler tasks, value QA, browser/mobile smoke, external sharing plan, category/rotation/KRX baseline audits, and aggregate readiness. Remaining blockers are still non-code gates: phone-readability acceptance, first real `2026-05-18` market-day scheduled-run observation, and post-logon/reboot Startup fallback observation. |
| Closeout gate evidence | `next-phase-readiness` now exposes `completion_gates` and `external_web_view_provider_smoke`, while `external-web-view-sharing-plan --json` prints the focused read-only Cloudflare/Tailscale sequence before provider setup. The final provider command is `external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json`; it records a non-secret provider-smoke operation event only after zero issues against a non-loopback HTTPS provider origin with no path/query/fragment, giving the external sharing blocker a durable closeout signal. After Cloudflare Tunnel is configured, prefer `verify_cloudflare_web_view_tunnel.ps1 -Url https://YOUR-WEB-VIEW-URL` because it validates the provider origin, reruns local external readiness, records provider smoke success, and reruns readiness in one operator command. |
| Full regression suite | `2026-05-17` local run passed with `557 passed` after the closeout wrapper was expanded to cover reaction distribution, web-view QA/browser smoke, external sharing plan, category snapshot status/plan, rotation mapping audit, and KRX baseline analysis directly. |
| Latest report date | `2026-05-15`, 51 reports, 28 summary stocks |
| Observation reaction | Internal-only `observation_reaction` covers `2026-01-02`~`2026-05-15` with 493 `mention_count >= 2` candidates; completed windows are D+1 486/493, D+5 427/493, D+10 344/493, and D+20 296/493. It is not public-surface-ready for numeric scoring and does not produce public numeric scoring or trading-recommendation output. |
| Candidate evidence | Recent 5 report dates are review-ready `5/5`; QA issue dates `0` |
| Closing-market briefing | Preview-ready `5/5`; manual Telegram review sends recorded `3/3`; schedule gate remains closed until `market_briefing_phone_review_accepted=true` is set after operator readability acceptance |
| KRX latest-day baseline | Stock/ETF/index Open API rows are stored through `2026-05-19`; `krx-baseline-analysis --json` reports `missing_daily_snapshots.missing_business_dates=6`, starting with `2026-05-28`, and each listed date is missing all six daily endpoints. |
| Market holiday coverage | Built-in/configured coverage currently runs through `2026-12-31`; no renewal blocker is active yet, but `next-phase-readiness` will surface one from October 2026 if future KRX closure dates are not configured. |
| Completion blockers | Manual Telegram review sends `0/3`, phone review not accepted, KRX Open API daily snapshots missing for latest publishable dates, real market-day scheduler observation missing, external provider smoke unrecorded on this PC, and current-user `web-view` Startup shortcut missing. |

The manual Telegram phone review send gate has an explicit safe path: run `market-briefing-readiness --recent-report-dates 5` and use the printed `market-briefing --date YYYY-MM-DD --limit 5 --send` commands only for dates that are preview-ready and public-safe. On the current main PC, the `2026-05-29` read-only audit reports manual sends `0/3`; the mini-PC `2026-05-17` sends remain historical trace evidence only and do not close this PC's scheduling gate.

| Area | Progress | Current Meaning | Next Increase Condition |
| --- | ---: | --- | --- |
| MVP pipeline | 88% | Fetch, parse, dedupe, persist, summarize, notify, and admin status paths exist with recent operational hardening. `operator-status` now includes live operation-event evidence, labels not-yet-due same-day components as `pending`, and distinguishes KRX latest-date `attention(incomplete_snapshot)` from scheduler failure. `StockMonitor-KrxMentionedFlowBackfill` now skips unresolved KRX metadata codes before Data Marketplace requests instead of failing the whole run. | More live market-day validation, especially the next `StockMonitor-KrxMentionedFlowBackfill` execution after unresolved-code hardening and Telegram delivery traces. |
| Naver collection and SQLite storage | 86% | Core report collection is working; report dedupe is DB unique-index plus `INSERT OR IGNORE`, schema changes now have a migration runner, DOM/API parser fixture coverage includes mobile URL/query canonicalization, intraday queueing is regression-tested against same-`source_id` duplicates, and live `inspect-page` snapshots can be saved as parser drift fixtures. Saved live fixtures now cover `2026-05-14` and `2026-05-15`, both parsing 20 API reports. | Add more saved fixtures from real market pages. |
| DB/schema maturity | 99% | Main operational tables exist with fragment state, worker heartbeat, safe settings, admin audit log, FK enforcement, `PRAGMA user_version`, `schema_migrations`, stronger report uniqueness, KRX snapshot tables, additive investor-flow schema v4 tables, category snapshot schema v5, investor-flow/category quality checks in `db-verify`, deep DB verification, backup/restore-smoke commands, db-verify and restore-smoke evidence in readiness, KRX cleanup/VACUUM dry-run/confirm protection, and KRX missing-date backfill guardrails. | Do not enable broad investor-flow scheduled ingest until separate approval; keep the narrow `[12009]` mentioned-stock 31-day lane bounded. |
| Summary correctness | 83% | Target price range, opinion, count filters, current price, sector/theme, stock-code-first grouping, and filtered paging are usable. Same-broker latest opinion and tied-opinion priority are now explicitly regression-tested. | Continue live-data validation for parser drift and code-missing edge cases. |
| Telegram operations | 94% | Daily summary, temporary default morning briefing format for `scheduled-notify`, intraday alerts, paging, stock search, replay-safe memo/check side effects, fragment resume, early/late notify guard, production/test delivery separation, worker heartbeat, TelegramCommands restart recovery, timeout-after-send fragment trace detail, and atomic JSON control-state saves are implemented and checklist-tracked. Timeout trace is visible in JSON and text operator status. | Validate worker heartbeat, timeout trace usefulness, and Telegram briefing readability across several unattended market days. |
| Telegram command worker | 93% | Hidden 1-minute loop, command parsing, paging, search, replay-safe memo flows, atomic paging/selection state saves, heartbeat, stale-state reporting, and guarded scheduler restart recovery are working. | Validate restart behavior during real Task Scheduler operation. |
| Windows scheduler operation | 96% | Notify, Poll, TelegramCommands, KRX daily backfill, and KRX mentioned-stock flow backfill are registered/enabled on the mini PC. KRX login reminder has business-day/no-run/late-run guards and stays disabled/unregistered for normal operation. Scheduler health is classified, never-run future tasks are not over-reported as failures, Shutdown run-now is blocked, and elevated/local metadata confirmed the five default mini-PC tasks are available and waiting for their first `2026-05-18` scheduled run. The registration verifier now reports Task Scheduler metadata access-denied separately from real missing tasks. `StockMonitor-Shutdown` is absent as required for always-on mini-PC operation. | Keep validating stale thresholds and the next real run behavior over several unattended market days. |
| Admin GUI | 86% | Local dashboard and first control surface exist; loopback guard, backend no-run date validation including holiday/env/past-date rejection, first KRX market-data tables, safe-settings audit controls, operation profile editing, TelegramCommands restart recovery, DB backup/verify reminders, readable recent-event summaries, and read-only safest-next-step recovery guidance are in place. | Validate controls over live scheduler use and refine UX copy. |
| Admin control operations | 79% | Run-now, enable/disable, no-run calendar, events, operation profile, TelegramCommands restart recovery, and Shutdown run-now/restart guard exist. | Add broader recovery actions only after live validation. |
| Operator diagnostics | 93% | `operator-status`, operation events, explain-date, health exit, worker heartbeat, scheduler classification, never-run scheduled-task handling, same-day live evidence fallback, pending live components, KRX Open API `empty`/`partial`/`incomplete_snapshot` attention warnings, optional KRX login reminder warning separation, category snapshot refreshability warnings, market-holiday coverage expiry warnings, and read-only schema-current checks are implemented. Elevated/local scheduler metadata has been verified, and the `2026-05-15` KRX incomplete-snapshot warning was cleared by the backed-up successful latest-day fill. Non-elevated scheduler metadata `access_denied` is treated as a permission check, not registration repair evidence. | Tune thresholds with elevated scheduler metadata and live logs. |
| Safety and observability | 86% | Health is machine-checkable, key scheduler/worker/DB integrity states are guarded, safe settings changes are auditable, DB verify/backup/restore-smoke/cleanup guard commands exist, KRX backfill requires explicit backup confirmation, KRX Open API calls that return 0 stored rows no longer look like successful data loads, and limited GUI recovery exists. | Observe live scheduler behavior and add only proven recovery actions. |
| Documentation consistency | 100% | Canonical document map, KRX runbook, admin plan, agent guide, rotation overlay plan, memo status cleanup, and current-stage 100% definition are recorded. | Keep new planning changes in canonical docs instead of adding scattered `.md` files. |
| Mini PC operation/sharing readiness | 98% local / 97% external | Windows scheduler, local paths, health checks, KRX scheduler tasks, required scheduler script checks, explicit scheduler Python path guidance, required project/canonical handoff file checks, `.env.example` archive inclusion, user web-view/rotation asset checks, non-secret Telegram/KRX environment presence checks, before-copy/post-restore checks, read-only `mini-pc-preflight` CLI, bundled `setup_mini_pc_environment.ps1`, mini-PC-specific `register_mini_pc_scheduler_tasks.ps1` wrapper that skips `StockMonitor-Shutdown`, source-desktop cutover helper, `verify_mini_pc_readiness.ps1`, scheduler registration verifier, external-share-only `verify_external_web_view_readiness.ps1`, focused read-only `external-web-view-sharing-plan --json`, post-provider `verify_cloudflare_web_view_tunnel.ps1`, migration archive integrity checks, separate admin/web access sessions, web-view loopback-by-default host guard, HTTPS-proxy `Secure` access-cookie behavior, stronger final-URL `external-web-view-smoke` admin/control-route checks, current-user `StockMonitor-WebView.lnk` Startup fallback, migration handoff, Docker deferral, access-code preflight, and Cloudflare/Tailscale exposure boundaries are documented. Actual mini-PC restore, `.env` creation, access-code enablement, scheduler registration, local external-sharing gate verification, Cloudflare provider smoke for `<external web-view provider URL>`, domain purchase, and manual Telegram review sends are complete. | Real market-day scheduled-run observation, operator phone-readability acceptance, and logon/reboot observation of the web-view Startup fallback remain. |
| Sector/theme data | 99% | Sector rollup, explicit/batch Naver industry refresh, first Naver theme refresh, display-level duplicate cleanup, category master, dated category membership snapshot tables/CLI, per-category snapshot lookup, disabled-category hiding, cache-to-snapshot promotion, dated/fallback status inspection/filtering/counts, next-action guard, read-only snapshot planning, per-date missing snapshot type output, source-date capture guard, catalog source/refreshability display in text and JSON, current Naver upjong catalog discovery with existing-display-match flags, single upjong-code dry-run validation with next catalog-add command output, verified-source-only sector refreshability checks, batch dry-run previews, request-delay controls, `--confirm` protection for real batch refresh, and DB coverage reporting are available. On `2026-05-15`, 8 verified `source=naver_industry` rows were added separately from existing `naver_quote` labels and refreshed into a dated sector snapshot; `db-verify` no longer warns `sector_catalog_not_refreshable`. | Continue source-date snapshots for older fallback dates only when needed; do not relabel or overwrite existing `naver_quote` rows. |
| 사용자용 웹뷰 완성도 | 92% | Boundaries and APIs are strong, and the visible page has started moving back toward the attached-image style daily briefing. The top `오늘 읽을 요약` block now mirrors Telegram market-briefing axes through structured `market_briefing` fields instead of leading with unstable category summaries, opinion-derived buy/sell signals, or JS-parsed display text. `2026-05-15` now has a dated sector snapshot for key verified upjong rows, `web-view-value-qa` still reports 0 issues, and `web-view-browser-smoke` now verifies desktop/mobile rendering, observation-tab clickability, stock search, no major horizontal overflow, data-route write blocking, and `/api/status` absence. | Continue compressing selected-stock evidence and category/rotation sections, then rerun date-by-date value QA and browser smoke after visible changes. |
| Web-view API readiness | 97% | Archive, daily, stock detail, category detail, category trend, market, intraday, flow-trend, and ETF-trend DTO/APIs exist; archive APIs expose category mapping state and category snapshot/fallback counts for operator/debug use, while the visible archive UI keeps only simple date/report filtering. Daily DTO includes exact-date `krx_context`, recent `krx_recent_flow` with actual `reference_date`/`exact_date_available`, structured `market_briefing`, read-only `krx_investor_flow`, category contract, and public contract metadata; stock detail includes read-only investor-flow rows with stored-sample/no-live-fetch/no-scoring metadata, and still excludes admin/operator internals. `2026-05-08` category snapshots are populated, and fallback dates are inspectable through CLI/API rather than friend-facing filters. | Populate more dated category snapshots and keep public-safe regression tests active. |
| ETF/flow data | 100% | First source study is documented; KRX P1/P2 specs are parsed, daily stock/ETF/index snapshots are stored/queryable through `2026-05-15`, and the stored 18-month Open API target window is complete through that latest snapshot date. KRX Data Marketplace investor-flow request candidates are identified, `[12008]`/`[12009]`/`[12010]` dry-run CLI exists without DB writes, login reminder CLI exists, `krx-flow-candidates` previews leadership candidates, saved sample normalization/scaffold/status/validation/compare/import-preview/import paths exist, first visible-grid import set is stored, two business dates (`2026-05-08`, `2026-05-07`) have raw/visible-grid parity validation, schema contract and `db-verify` quality checks exist, investor-flow parser/schema v4 paths are tested, stored investor-flow rows cover through `2026-05-12`, and Stage 5 read-only trend display exists. | Keep only the approved narrow automatic `[12009]` anchor-date mentioned-stock 31-day 보강 path active; broad `[12008]`/`[12010]` or all-stock scheduled ingest requires separate approval. |
| ETF/flow product readiness | 91% | Display direction and source separation are documented; KRX stock/ETF/index snapshots can be shown as read-only reference cards, investor-flow dry-run plumbing exists, `[12009]` product scope is narrowed to leadership candidates, candidate preview output exists, sample manifest validation with expected investor coverage, capture-set and candidate-driven scaffold generation, capture checklist output, sample coverage status, batch validation, batch normalized artifact output, DB import preview, guarded manual import, first visible-grid import set, raw-network sample capture for two dates, visible-grid/raw parity gate for two dates, GET-only web-view investor-flow reference DTO/UI, stored flow rows through `2026-05-12`, stored-sample flow trend display, and `krx-baseline-analysis` source-lane comparison exist. Broad scheduled ingest remains disabled; the narrow `[12009]` mentioned-stock 보강 path is the only approved automatic lane. | Continue 18-month OpenAPI baseline; do not broaden Data Marketplace into whole-market stock flow without separate approval. |
| Backtest observation readiness | 92% | BO-1~BO-7 exists for `mention_count >= 2` candidates: exact-horizon `1/5/10/20영업일` reactions, target gap/progress, stored-window max progress, first target-hit D+ days, same-date flow, turnover, foreign net-buy top inclusion, public-safe API, first `관찰` tab table, and initial multi-date QA with target-progress caution labels. `next-phase-readiness.observation_reaction` now surfaces the full stored summary baseline `2026-01-02`~`2026-05-15`: 493 candidates, D+1 486/493, D+5 427/493, D+10 344/493, D+20 296/493. | Continue reading completed reaction windows only; do not treat missing D+20 as bad evidence. |
| Scoring draft readiness | Hold / archived | [research-notes.md](research-notes.md) is historical research evidence only. SD-4/SD-5 hidden scoring commands remain callable for compatibility but are hidden from top-level CLI help and must not drive product ordering, public copy, Telegram, daily briefing, roadmap progress, or investment decisions. | Spend next effort on evidence snapshots, missing-data labels, and backtest coverage instead of new scoring or score tuning. |
| US market data expansion | 3% | Operator memo exists to investigate US market APIs later. | Compare official/semi-official sources, cost, rate limits, and redistribution limits. |

KRX investor-flow execution should now follow [market-data-runbook.md](market-data-runbook.md).
Use stage numbers as the execution boundary; Stage 6 first design exists, but broad scheduled KRX Data Marketplace ingest remains disabled until separate approval. The narrow `[12009]` anchor-date mentioned-stock backfill lane is the only approved automatic exception.

P2 category/ETF execution is now summarized in this roadmap and [operating-guide.md](operating-guide.md).
The first P2 implementation pass is complete: schema v5 category snapshots, category catalog/refresh CLI, snapshot-aware web-view category DTOs, `GET /api/etf-trend`, and Telegram read-only status helpers exist.

Data source ownership and display naming are fixed in [data-governance.md](data-governance.md).
Use `업종`, `테마`, and `카테고리` in user-facing Korean copy; keep KRX labels for market reference data, not for the current category taxonomy.

Current broad estimate:

| Layer | Progress | Interpretation |
| --- | ---: | --- |
| Current main-PC domestic MVP aggregate | 85-90% | Current `2026-05-29` readiness baseline. Code, DB, Telegram/admin/web-view/KRX/backtest-observation foundations and strengthened guardrail coverage are usable, but closeout is blocked by manual market-briefing sends `0/3`, missing scheduled-run evidence, KRX daily snapshot gaps from `2026-05-28`, missing Startup shortcut, and unrecorded provider smoke. Excludes broad public sharing, US market expansion, and public-facing scoring. |
| Historical mini-PC closeout trace | 96-97% | Historical mini-PC restore/access-code/scheduler/provider-smoke/manual-send evidence remains useful trace context only. It does not close the active main-PC readiness gates. |
| Current domestic MVP with public scoring/recommendation expectation | Out of current scope | Public score, grade, recommendation, Telegram candidate alert, and buy/sell wording remain blocked. Archived hidden scoring-draft commands do not count toward product readiness. |
| Personal Telegram MVP | 80-85% | Usable for live validation with fragment resume, filtered paging, briefing format, early/late notify guard, production/test separation, worker heartbeat checklist, and timeout trace in place; current main-PC market-briefing phone review remains blocked at `0/3`. |
| Local operator console | 82% | Useful now; safe settings and operation profile are editable in `admin-gui`, audit logging exists, and TelegramCommands restart recovery is available. |
| 사용자용 웹뷰 | 90-93% | Separate GET-only shell and broad DTO/API coverage exist. Historical mini-PC provider smoke remains trace evidence, but the current main-PC provider smoke is unrecorded and the current-user Startup shortcut is missing. |
| Data expansion layer | 88-91% | Stock/ETF/index Open API baseline is stored through `2026-05-19`, but the current readiness baseline reports 6 missing publishable KRX daily snapshot dates starting `2026-05-28`. Investor-flow read-only plumbing exists; broader Data Marketplace lanes remain blocked without separate approval. |

## 2026-05-09 100% Target Board

`100%` means the current stage is decision-complete, not that all future analytics are finished.

| Track | From | Target | Done definition |
| --- | ---: | ---: | --- |
| Personal Telegram MVP | 84% | 88% | Fragment resume, production/test delivery separation, and worker heartbeat checks are explicitly tracked. |
| Scheduler / operation stability | 86% | 90% | Notify/Poll/TelegramCommands/Shutdown contracts and check order are documented. |
| Admin GUI | 66% | 82% | Safe settings, audit log, operation profile behavior, and first TelegramCommands recovery control are implemented through DB/CLI/admin-gui. |
| 사용자용 web-view | 80% | 94-96% | GET-only/read-only boundary, selection-state UX, missing-state policy, archive/mobile polish, selected-date KRX context, recent KRX flow, and public-safe DTO tests are fixed as the V1 closeout scope. |
| Data expansion layer | 47% | 86% | KRX/ETF/flow and sector/theme snapshot immediate/deferred items are separated; recent March-to-May KRX price/turnover backfill guard exists, KRX Data Marketplace `[12008]/[12009]/[12010]` dry-run commands are ready, and login reminder CLI is implemented for live validation. |
| Mini PC / external sharing readiness | 66% | 98% local / 97% external | Docker is deferred; preflight, bundled venv/install/readiness bootstrap, mini-PC scheduler wrapper with shutdown skipped, readiness check runner, scheduler registration verifier, external web-view readiness gate with value QA and browser/mobile smoke, final-URL smoke checks for admin root/control routes/operator JSON leaks, migration archive packaging with SHA256 sidecar, archive verification, explicit scheduler Python path guidance, separate admin/web access sessions, web-view loopback guard, HTTPS-proxy `Secure` access-cookie behavior, post-provider Cloudflare wrapper, current-user web-view Startup shortcut fallback, and Cloudflare/Tailscale boundaries are in place. Actual mini PC restore, access-code enablement, scheduler registration, domain purchase, local external-sharing readiness, provider binding, and final shared-URL smoke for `<external web-view provider URL>` now pass. |
| Documentation consistency | 75% | 100% | `current-work`, this roadmap, `surface-contract`, and mini PC handoff no longer conflict on current state. |

Documentation consolidation result:

| Area | Canonical document |
| --- | --- |
| Document routing | [documentation-index.md](documentation-index.md) |
| KRX/ETF/flow | [market-data-runbook.md](market-data-runbook.md) |
| Admin GUI | [surface-guide.md](surface-guide.md) |
| Agent usage | [architecture-guide.md](architecture-guide.md) |
| 순환매 SVG overlay | [surface-guide.md](surface-guide.md) |

Current-stage 100% excludes broad public sharing and US market expansion. The mini-PC restore and historical Cloudflare provider smoke are trace evidence only. For the current main-PC closeout, the remaining work is KRX daily snapshot catch-up, real market-day scheduled-run evidence, manual market-briefing phone review sends and acceptance, `web-view` Startup fallback configuration/observation, and external provider smoke while keeping `admin-gui` private.

Today-priority items:

| Priority | Item | Decision |
| --- | --- | --- |
| P0 | Documentation consistency | Must be completed before more implementation. |
| P0 | Scheduler / Telegram / live-validation gates | Must remain visible as operating checks. |
| P0 | `web-view` read-only boundary | Must stay fixed before any Cloudflare sharing. |
| P0 | Data-quality rules | Must be checked before parser, summary, Telegram, admin-gui, or web-view changes. |
| P0 | KRX Data Marketplace login check | Prefer `.env` raw login smoke-check via `krx-flow-login-check`; Chrome session is fallback/debug only. |
| Done / optional | KRX Data Marketplace session reminder CLI/scheduler | `krx-flow-login-reminder` sends a Telegram reminder about 5 minutes before planned flow work, skips on business-day/no-run/late-run guards, and `StockMonitor-KrxFlowLoginReminder` is registered separately from collection. Normal operation now uses the narrow `StockMonitor-KrxMentionedFlowBackfill` path, so keep the reminder task disabled unless a manual validation day needs it. |
| Done | Safe settings + audit model | DB/CLI and first admin-gui controls are implemented for low-risk settings. |
| Done | Operation profile | `desktop-validation`, `mini-pc`, and `manual-only` behavior is implemented and audited through safe settings; the mini PC is set to `mini-pc`. |
| Done / trace, current-PC open | Cloudflare Tunnel preparation | Domain purchase, local validation, access-code gate, provider binding, and final shared-URL smoke for `<external web-view provider URL>` are historical mini-PC trace evidence. On the current main PC, provider smoke is not recorded. Keep any provider pointed only to `web-view`; never expose `admin-gui`. |
| Done / P2-watch | Theme snapshot / ETF read-only expansion | Schema/CLI/API first pass is implemented; scheduled KRX Data Marketplace ingest remains design-only. |
| Deferred | Scoring, recommendations, flow-based interest alerts | Defer until enough source-backed history exists. |

Top risks:

1. Future holiday years still require manual maintenance until an external holiday source or yearly update workflow is added. `operator-status` now shows the built-in/configured holiday coverage end date and warns near default coverage expiry.
2. Scheduler metadata is now observable in elevated/local checks, but stale thresholds are conservative and still need tuning after several real market days.
3. `admin-gui` is control-capable; loopback enforcement exists, and only the separate GET-only `web-view` may be considered for future external sharing.
4. Telegram response timeout after an actual send can still duplicate a sent chat message. Fragment failure detail now includes `message_hash` and `ambiguous_send`, but this is audit visibility rather than full duplicate prevention.
5. ETF/flow can improve interpretation, but scoring before enough history would create false confidence.

## Operator Memo Status

| Memo / Idea | Status | Planning Note |
| --- | --- | --- |
| Sector graph and sector rollup | [O] | `web-view` `국장 관찰 요약` now renders sector/theme breadth as graph-like bars with report count, active stock count, selected-day share, and category drilldown. Historical fallback taxonomy remains labeled data debt. |
| Market mood snapshot | [O] | `web-view` has one-line comments and a sentence-style `시장 분위기`; `market-briefing`/`market-briefing-readiness` provide the Telegram-style preview/manual review loop. Task Scheduler registration remains gated by operator phone-readability acceptance. |
| Theme 505 / domestic theme grouping | [O] | `refresh-theme` first pass stores theme memberships. |
| Exclude single-report / no-target-price output | [O] | Notification filtering has been handled as an output policy. |
| Local admin program | [O] | Basic local admin surface exists. |
| N100 mini PC migration | [O] / trace | Restore, `.env` creation, access-code enablement, scheduler registration, local readiness gates, and Cloudflare provider smoke were completed on the mini PC and remain historical trace evidence. They do not close the current main-PC Startup fallback, provider smoke, or scheduled-run observation gates. |
| Admin/shared page split | [O] | Separate GET-only `web-view` first pass exists and does not expose admin status/control APIs. |
| External access candidates | [O] / watch | Keep the candidate set narrow: Tailscale for owner-only remote operation if still needed, Cloudflare Tunnel for friend-facing read-only `web-view` sharing. Historical mini-PC Cloudflare provider smoke for `<external web-view provider URL>` is retained as trace evidence; the current main-PC provider smoke is not recorded. Keep access-code/allow-list controls enabled and keep `admin-gui` private. |
| Theme v2 / dated theme history | [O] / watch | Stored theme rollups are now surfaced in the same market-width bars and category drilldown as sectors. Broader theme catalog/history coverage remains a data-quality watch item, not a missing V1 surface. |
| Rotation / flow tracking foundation | [O] | The `순환매` tab connects image aliases, report category evidence, stock candidates, ETF candidates, and missing information in user-facing cards without broad ingest or trading-call wording. |
| 순환매 SVG overlay | [O] / watch | Overlay, active aliases, evidence-backed highlights, and separated stock/ETF reference slots are visible. Continue optional alias/ETF coverage expansion through audits. |
| ETF tracking | [O] | Source study, KRX intake templates, snapshot tables, manual ingest, stored query paths, admin display, and `web-view` ETF trend exist; keep ETF data separate from company reports. |
| KRX historical snapshots | [O] / blocker | Prefer recent stock/ETF/index daily snapshot backfill over old report backfill. `2024-11-08` through `2026-05-19` are stored for daily stock/ETF/index endpoints, but `2026-05-29` readiness reports 6 missing publishable daily snapshot dates starting `2026-05-28`. Use for trend/reference context only, not scoring. |
| Candidate evidence / next-day candidates | [O] / watch | The computed DTO/API and visible `관찰` tab expose non-numeric `observation_priority`, `왜 눈에 띄는지`, `부족한 정보`, and a top-2 `우선 확인` shortlist. Continue market-day review, but public numeric scoring is a non-goal rather than a blocker. |
| Backtest observation / report reaction | [O] / watch | [backtest-observation-plan.md](research-notes.md) defines the read-only path. BO-1~BO-7 calculations/API/UI/initial QA exist; broader QA continues. |
| Scoring draft | Hold / archived | [research-notes.md](research-notes.md) records historical research only. Hidden scoring CLIs are not active product commands and remain blocked from public output, product ordering, Telegram, and roadmap progress. |
| US market API expansion | [ ] | New memo captured; investigate later after domestic operating base and mini PC path are stable. |
| 2026-05-19 GitHub/tool bookmarks | [△] | `scrcpy` is excluded. `QuantDinger` remains environment-blocked until Docker is available. `botasaurus` was import-verified historically and a browser probe loaded Naver/KRX pages, but it is now archived/reference-only; use `scrapling-official` for new bounded browser-gated/source probes. `codegraph` is locally installed and indexed 54 Python files, useful for impact review. `codex-complexity-optimizer` is locally installed as a report-only scanner; its first `src` scan flags `analysis/backtest_observation.py` and `cli.py` as the main refactor-review areas. None of these are production runtime dependencies, scheduler jobs, public `web-view` features, broker/trading automation, or broad ingest paths. |
| One-line market commentary practice | [O] | Stored-data `장초반`/`점심`/`장 마감 전` one-line drafts are visible in `web-view` and available through Telegram `/한줄`, without scheduler registration, live fetch, score, grade, or trading-decision wording. |
| Time-slot market mood card | [O] / watch | The `시황 예시` photo reference now has a real stored-data/manual-review card in `web-view` and `market-briefing-readiness`. It shows title/headline, index, notable stocks, core points, check points, and source gaps without live fetch, public scoring, recommendation, production integration, scheduler registration, or broad ingest. On the main PC it is preview-ready but still blocked from scheduling by manual Telegram review `0/3` and KRX latest snapshot fallback after `2026-05-14`. |
| Operator photo/reference intake | [O] | Telegram `/사진` stores operator images in `data/operator_photo_inbox/` with sidecar metadata for later implementation review. It does not upload or expose them through `web-view`. |
| Operator memo surface reflection | [O] | The 2026-05-18 partial memos now reach real surfaces: one-line comments appear in `web-view` and Telegram `/한줄`, Telegram `/사진` stores operator images in the local inbox, and periodic data needs appear in `web-view` market tab plus `operator-status`. |
| Periodic data needs audit | Historical / hidden | `periodic-data-needs-audit` remains callable as a compatibility audit, but current operation should use the smaller minimal verification set plus source-specific runbooks. |
| Holiday / manual no-run management | [O] / watch | Calendar control and explain-date exist. Admin/CLI no-run add paths reject market holidays, env no-run dates, and past dates so DB overrides stay meaningful. |
| Quiet background operation | [△] | Scheduler, hidden worker, heartbeat, and health output exist; live threshold tuning remains. |

## Key Decision: Build Order

The next phase should not start with more visual cards or speculative analytics. The implementation is now useful enough that the next risk is operational correctness.

Recommended build order from the current state:

1. Keep live-operation validation running and review fragment/worker/scheduler evidence after each market day.
2. Continue bounded KRX missing-date backfill only after `db-verify` and `db-backup`, using `--confirm --i-backed-up`.
3. Polish the existing GET-only user `web-view`: access-gate planning and public display labels.
4. Add theme v2 history model for better rotation context.
5. Draft KRX Data Marketplace Stage 6 broad scheduled-ingest design; do not enable broader `[12008]`/`[12010]` or all-stock scheduled ingest without separate approval.
6. Preserve scoring draft only as archived research; do not run or tune SD-5 as active product work.
7. Improve rotation/candidate evidence as non-scored observation context after enough source-backed history exists.

## Security Posture Adjustment

Expected users are limited to the owner and a small number of trusted external viewers. Security should stay lightweight, but the control boundary still matters.

Recommended posture:

| Surface | Exposure | Required Guard |
| --- | --- | --- |
| `admin-gui` | Local machine or private remote access only | Control buttons, scheduler actions, shutdown policy, and settings stay here. |
| shared `web-view` | Small trusted audience | Read-only pages only; no scheduler, shutdown, token, or settings controls. |
| public internet | Avoid by default | If needed later, use a private tunnel/VPN or simple access gate before adding features. |

Practical rule: do not spend effort on enterprise-grade auth yet, but never expose POST/control endpoints through the shared page.

External access candidates are intentionally limited for now:

| Candidate | Intended use | Status |
| --- | --- | --- |
| Tailscale | Owner-only remote access to the mini PC and local services. | Planning candidate; useful for personal remote operation, but less convenient for friends because they need onboarding. |
| Cloudflare Tunnel | Friend-facing URL candidate for the read-only `web-view` only. | Historical provider smoke passed for `<external web-view provider URL>`, but current main-PC provider smoke is not recorded. Keep any provider mapped only to `<loopback web-view target>` or the chosen `web-view` loopback port and do not share `admin-gui`. |

Avoid direct router port forwarding for this project unless a later security review explicitly changes the posture.

The detailed boundary is fixed in [surface-guide.md](surface-guide.md):
`admin-gui` is the operator control surface, while `web-view` is a separate shared read-only information surface.

## Phase 0: Operating Contract Freeze

Why this matters: older docs and early notes still contain historical times such as `07:00`, `08:00~15:00`, and `08:00~16:00`. The current operating contract is:

| Task | Current Contract |
| --- | --- |
| `StockMonitor-KrxDailyBackfill` | `08:10` KST on Korean business days, after the officially confirmed next-business-day `08:00` KRX Open API publication window; fills stock/ETF/index snapshots for the previous business day or earlier recent missing dates |
| `StockMonitor-Notify` | `08:20` KST on Korean business days; sends the previous-business-day briefing after the `08:10` KRX Open API fill attempt |
| `StockMonitor-Poll` | every 30 minutes from `08:30` to `16:30` KST on Korean business days |
| `StockMonitor-KrxMentionedFlowBackfill` | `16:00` KST on Korean business days; fills recent 31-day `[12009]` stock investor flow for stocks mentioned in that day's reports, newest dates first, default 300-call cap |
| `StockMonitor-KrxFlowLoginReminder` | Optional `16:45` KST validation reminder; currently disabled unless a manual KRX flow validation day needs it |
| `StockMonitor-TelegramCommands` | hidden worker from `08:00` to `16:30` KST on Korean business days |
| `StockMonitor-WebViewHourlyRestart` | hourly from `00:05` KST; restarts only the read-only loopback `web-view` target on `<loopback web-view target>` |
| `StockMonitor-Shutdown` | `17:10` KST during desktop live validation, guarded by business-day logic |

Work items:

- Approved Telegram delivery target: retain the `StockMonitor-Poll` 30-minute collection/dedupe trigger, but emit the compact intraday market-context briefing only at `08:30`, then `09:30` through `15:30` KST. The `08:30` briefing is report-first and does not require Toss data; later briefings may add available bounded Toss context. Do not register a new scheduler task for this change.
- Reconcile old operating-time references in docs, scripts, README, and GUI labels.
- Confirm scheduler triggers match the documented contract. Current elevated mini-PC verification should confirm the six default tasks are registered/enabled, including the `08:10` KRX Open API daily fill and hourly web-view restart.
- Define catch-up policy for missed daily summary delivery.
- Define exact meaning of `RUN_SUPPRESSED_DATES` versus market holidays.
- Keep the operation profile names stable: `desktop-validation`, `mini-pc`, and `manual-only`.

Done criteria:

- A future session can read one document and understand the current schedule without guessing.
- GUI, CLI, docs, and scheduler output use the same terms.

## Phase 1: Correctness And Delivery Hardening

Priority work:

| Priority | Item | Reason |
| --- | --- | --- |
| Done | Daily summary split-send fragment resume | Fragment-level send state exists and resumes unsent fragments. |
| Done | Notify time-window guard | Production scheduled notify sends only in the `08:00~08:30` window unless `--allow-late` is explicit. |
| Done | Stock-code-first summary grouping | Daily and intraday grouping prefer stock code where available. |
| Done | Separate scheduled/manual delivery labels | Manual tests use `telegram_test`; production scheduled sends use `telegram`. |
| Done / P2-watch | Telegram control state durability | Command paging and pending selections are still stored in JSON, but saves now use temp-file plus atomic replace to avoid partially written state after interruption. `/메모` and `/체크 로그인` side effects remain update-id replay-safe. SQLite-backed state can wait until real restart evidence says JSON is not enough. |

Candidate storage additions:

| Table | Purpose |
| --- | --- |
| `daily_summary_delivery_runs` | One row per business date and delivery attempt. |
| `daily_summary_delivery_fragments` | One row per Telegram fragment, with sent/skipped/error status. |

## Phase 2: Admin Safety And Observability

Priority work:

| Priority | Item | Reason |
| --- | --- | --- |
| Done | Loopback-only admin guard | Control-capable admin refuses non-loopback binding unless explicitly allowed. |
| Done | Server-side no-run date validation | Market holidays, env no-run dates, and past dates are rejected as redundant or ineffective DB no-run dates. |
| Done | Scheduler status classification | Access denied, disabled, missing, failed, running, stale, and unavailable states are distinct. |
| Done | `operator-status --json --health-exit` | Scheduler/admin automation can fail fast when core health is bad. |
| Done | `operator-control explain-date` | A date explains whether it is runnable and why. |
| Done | Telegram worker heartbeat | Admin/operator status shows whether command polling is alive. |
| Done | Telegram loop restart control | TelegramCommands restart recovery is available through CLI/admin-gui and remains the only broad restart action. |
| Done | Operation profile and shutdown policy | `mini-pc` disables scheduled shutdown behavior and `StockMonitor-Shutdown` is not registered on the mini PC. |
| Done | Migration/backup reminders | `operator-status` JSON/text and `admin-gui` show latest backup presence plus db-verify/db-backup reminders before risky DB/KRX work. |
| Done | Recent event readability | `operator-status` now adds `detail_display` summaries and `admin-gui` uses them so KRX, flow, scheduler, notify, and admin failure rows read as operator actions instead of raw key/value strings. |
| Done / P1-watch | Safe recovery guidance | `operator-status` now exposes `recovery_actions`, and `admin-gui` shows them as read-only safest-next-step guidance. New write/restart controls remain blocked except TelegramCommands restart until real live evidence proves a safe rollback path. |

Admin GUI should answer three questions first:

1. Is the system supposed to run today?
2. Did the scheduled work actually run?
3. If not, what is the most likely cause and safest recovery action?

## Phase 3: Safe Settings Model

Do not expose raw `.env` editing through the admin GUI.

DB/CLI first pass status: implemented. Schema migration v3 adds `app_settings` and `admin_audit_log`, `operator-settings list/set/history` provides the CLI interface, and admin-gui exposes guarded controls for the approved safe settings.

Recommended configuration layers:

| Layer | Contents | Editable From GUI |
| --- | --- | --- |
| `.env` | Telegram token, chat id, bootstrap paths, sensitive or restart-required values | No |
| `app_settings` | Safe operational knobs | Yes, through validated DB settings and guarded admin-gui controls |
| `worker_state` | Runtime heartbeat and status | Read-only or controlled actions only |

First safe knobs:

| Setting | Purpose |
| --- | --- |
| `daily_summary_min_mention_count` | Hide low-signal daily summary entries. |
| `daily_summary_require_target_price` | Hide entries with no target price. |
| `notification_default_limit` | Default visible item count for Telegram paging. |
| `operation_profile` | Switch between desktop validation, mini PC, and manual-only behavior. |

Required support tables:

| Table | Purpose |
| --- | --- |
| `app_settings` | Validated operator settings. Implemented in migration v3. |
| `admin_audit_log` | Who changed what, when, and from which interface. Implemented in migration v3. |
| `worker_state` | Last heartbeat and current status for poll, notify, and command workers. |

Excluded from GUI settings:

- Telegram bot token editing.
- Telegram chat id editing.
- Raw shell command editing.
- One-click shutdown.
- One-click disable all scheduled tasks.

## Phase 4: User Web-View V1

The user web-view is separate from the control-capable admin GUI.
This means a separate page, separate HTTP handler/router, separate GET-only API contract, and separate read-only DTOs.
It must not be implemented as a read-only mode on `admin-gui`.

Current command:

```powershell
python -m stock_monitor web-view --host <loopback-host> --port <web-view-port>
```

Current screens:

| Screen | Contents |
| --- | --- |
| Date archive | Daily report count, delivery state, sector/theme highlights, and previous/next navigation. |
| Daily review | Stock-level summary with target price range, opinion, current price, sector/theme, and stock detail drilldown. |
| Sector/theme rollup | Category report counts, representative stocks, category detail, and recent category trend. |
| Market mood | Report-flow tilt, target-price availability, active sectors, and observation-candidate hints without trading-action wording. |
| Intraday batches | Same-date intraday collection and delivery history. |
| KRX reference | Selected-date KOSPI/KOSDAQ/ETF/index cards and recent KRX flow reference. |

Current API shape is read-only:

- `GET /health`
- `GET /api/archive?limit=20`
- `GET /api/daily/YYYY-MM-DD`
- `GET /api/daily/YYYY-MM-DD/stocks/STOCK_CODE`
- `GET /api/intraday?date=YYYY-MM-DD`
- `GET /api/toss-priority-quotes?date=YYYY-MM-DD`
- `GET /api/toss-market-context?date=YYYY-MM-DD`
- `GET /api/category?date=YYYY-MM-DD&type=sector|theme&name=...`
- `GET /api/category-trend?type=sector|theme&name=...`
- `GET /api/etf-trend?date=YYYY-MM-DD&limit=5`
- `GET /api/market`

No POST/control endpoints in the shared web-view.

Do not reuse `build_operator_status_snapshot()` as the user API.
That snapshot is an operator/admin model containing scheduler, worker, and health internals.
Build and maintain date-bound read-only query models for archive/review pages instead.

## Phase 5: Category V2

Current sector/theme refresh is useful, but the model should mature before theme trend judgment is trusted.

Current additions:

| Data | Purpose |
| --- | --- |
| `category_master` | Stable display taxonomy for sectors/themes before web-view analytics depend on source-specific codes. |
| `category_membership_snapshots` | Dated sector/theme membership history to avoid silently mixing future mappings into past dates. |
| Theme coverage report | Shows which reported stocks have no theme mapping. |

Operational direction:

- Keep `refresh-theme <theme_code>` as a debug tool, with optional `--snapshot-date`.
- Keep `refresh-industry <industry_code>` as an explicit, slow operator-triggered refresh before any broad scheduled crawl, with optional `--snapshot-date`.
- Use `category-catalog` and `refresh-themes --enabled --snapshot-date SOURCE_DATE` only when the source date is the actual capture date. Do not label current theme membership as a historical source-date snapshot.
- Treat theme membership as slowly changing reference data.

## Phase 6: ETF And Flow Data

ETF and flow should be planned as separate data layers. Priority has been raised from distant backlog to source-study and read-only display planning because they are useful for interpreting sector/theme rotation.

ETF candidate fields:

- ETF code and name.
- Underlying index.
- Management company.
- Constituents or top holdings if source is stable.
- Daily NAV/price/volume if source is stable.

Flow candidate fields:

- Stock code.
- Trade date.
- Individual, foreign, institution net buy/sell.
- Volume and turnover.

Current flow source priority:

| Priority | Source | Use |
| --- | --- | --- |
| P0 | KRX Data Marketplace `[12009] 투자자별 거래실적(개별종목)` | Stock-level investor flow for leadership candidates. |
| P1 | KRX Data Marketplace `[12008] 투자자별 거래실적` | Market-wide investor background. |
| P1 | KRX Data Marketplace `[12010] 투자자별 순매수상위종목` | Top net-buy names by investor category. |
| Fallback | KIS Developers | Use only if KRX Data Marketplace cannot be made stable enough. |

Deferred analytics:

- Report day plus one-day flow check.
- Third-day interest alert.
- Sector/theme rotation view.
- Target price achievement rate and days-to-target.
- Scoring or grade systems.

Do not implement scoring until enough historical data exists to validate whether it adds signal.

Near-term display direction:

| View | Useful First Output |
| --- | --- |
| ETF reference | ETF code/name, category/theme/index, price change, volume, and linked representative stocks. |
| Flow snapshot | Stock-level foreign/institution/individual net buy and volume for leadership candidates. |
| Sector/theme rotation | Report activity plus flow direction shown side by side, without producing a score yet. |
| Daily review | "Reports appeared here, money appears to be moving here" shown as separated evidence layers. |

## Current Implementation Batch Status

| Step | Task | Status | Output |
| --- | --- | --- | --- |
| 1 | Reconcile operating contract references | Done | README/current-work/roadmap now describe the current operating contract. |
| 2 | Add explain-date | Done | `operator-control explain-date YYYY-MM-DD [--json]` explains runnable/skip causes. |
| 3 | Add operator-status health exit and Telegram worker heartbeat | Done | `worker_state`, `worker_states.telegram_command_loop`, and `--health-exit` exist. |
| 4 | Improve scheduler status classification | Done | Scheduler tasks now expose `status_class` and `status_reason`. |
| 5 | Live-validate fragment-resume daily delivery | In progress | Code/tests exist; real long-summary retry behavior still needs live observation. |
| 6 | Start ETF/flow source study | Stage 4 done | [market-data-runbook.md](market-data-runbook.md) fixes KRX-first and no-scoring boundaries. [market-data-runbook.md](market-data-runbook.md) tracks Open API field capture. [market-data-runbook.md](market-data-runbook.md) fixes Data Marketplace `[12008]`, `[12009]`, `[12010]` as screen-backed request candidates. `krx-flow-login-check` verifies raw `.env` login without DB writes, and Chrome login reminder remains fallback/debug only. |
| 7 | Document deferred Telegram admin-open idea | Done | `/관리자페이지 열기` is recorded as deferred; safer read-only Telegram status commands are implemented. |
| 8 | Operational hardening review fixes | Done | Shutdown run-now guard, notify early guard, filtered paging, intraday 0-count fix, and backend no-run validation are implemented. |
| 9 | DB hardening first pass | Done | `foreign_keys=ON`, schema version marker, report unique indexes, `INSERT OR IGNORE`, fragment resume cleanup, and worker error clearing exist. |
| 10 | Draft mini PC migration handoff | Done | [mini-pc-runbook.md](mini-pc-runbook.md) captures zip/restore/verify/new-Codex briefing. |
| 11 | Capture US market API expansion memo | Backlog | `data/operator_memos.md` records future investigation of official/semi-official US market APIs. |
| 12 | Web-view V1.1 intraday and KRX display pass | Done | `GET /api/intraday?date=YYYY-MM-DD` exposes public-safe intraday batch history, and the user page now splits KRX KOSPI/KOSDAQ/ETF/index reference cards. |
| 13 | Web-view same-date KRX stock reference pass | Done | `GET /api/daily/YYYY-MM-DD` stock rows can include same-business-date KRX close price, change percent, turnover, and market without scoring. |
| 14 | Web-view stock detail route pass | Done | `GET /api/daily/YYYY-MM-DD/stocks/STOCK_CODE` exposes same-date report detail and KRX reference data without admin/operator internals. |
| 15 | Web-view archive navigation pass | Done | The user page supports `?date=YYYY-MM-DD`, previous/next archive buttons, active date chips, and URL state updates without adding write/control APIs. |
| 16 | Web-view category detail pass | Done | `GET /api/category?date=YYYY-MM-DD&type=sector|theme&name=...` exposes category stock lists with same-date KRX references; sector/theme rows are clickable in the user page. |
| 17 | Web-view category trend pass | Done | `GET /api/category-trend?type=sector|theme&name=...` exposes recent category report/stock counts and the page shows category flow tables without scoring. |
| 18 | Web-view V1 closeout planning | Done | Selection-state UX, missing-state display, archive/mobile polish, GET-only tests, and public-safe DTO checks are fixed as the V1 closeout gate. |
| 19 | External sharing boundary planning | Done | Docker is deferred; Cloudflare Tunnel may target only `web-view` on localhost; Tailscale remains owner-management candidate; `admin-gui`, `.env`, DB, Telegram, scheduler controls remain private. |
| 20 | Safe settings/audit DB+CLI pass | Done | Migration v3 adds `app_settings` and `admin_audit_log`; `operator-settings list/set/history` validates and audits safe setting changes; effective settings feed daily summary filters, Telegram paging limit, and `operator-status`. |
| 21 | Safe settings admin-gui first pass | Done | `admin-gui` shows safe settings, allows guarded edits for daily summary min mentions, target-price-required, default display limit, and operation profile, and shows recent audit logs. |
| 22 | DB backup/verify first pass | Done | `db-verify` checks integrity/schema/counts/dedupe/orphan fragments. `db-backup` creates consistent SQLite backups with integrity check. `db-backup-prune` previews/deletes old backups with confirmation. |
| 23 | KRX cleanup guard first pass | Done | `db-cleanup --dry-run --retention-days 183` previews expired KRX snapshot rows, protects `reports` and delivery state, and requires `--confirm` before deleting affected KRX rows. |
| 24 | KRX missing-date backfill guard first pass | 18-month Open API target complete through latest stored date | `krx-backfill-missing daily --lookback-days 90 --dry-run` finds missing business-date/endpoint pairs from newest business dates first and reuses `krx-fetch-snapshot` for actual bounded fills. Real manual rebaseline calls require `--confirm --i-backed-up`, default to 5 business dates, sleep between endpoint requests, and reject larger batches without `--allow-large-batch`. `scheduled-krx-daily-backfill` is the narrow automatic path: it runs at `08:10` after the officially confirmed next-business-day `08:00` publication window, targets the previous business day or earlier recent missing dates, and does not fetch same-day rows. Stock/ETF/index snapshots currently cover `2024-11-08` through `2026-05-15`; investor-flow rows currently cover through `2026-05-12` after guarded manual backfill. |
| 25 | Restore smoke and profile/recovery pass | Done | `db-restore-smoke` verifies backup copies without touching production DB. `operation_profile` now controls scheduled wrappers, and TelegramCommands restart is available through CLI/admin-gui. |

Do not start ETF/flow scoring before source quality and enough history exist. ETF/flow source study can start after the operational health outputs behave correctly in live runs.

Next practical sequence, updated after the `2026-05-29` main-PC readiness refresh:

1. Re-run read-only readiness after any operator action and keep this roadmap/current-work/next-phase synchronized with the actual main-PC gate state.
2. Close KRX daily snapshot gaps through the guarded backfill path only after the usual DB verification/backup discipline; do not use same-day probes as intraday data.
3. Close the market-briefing phone-review gate through deliberate manual Telegram sends only when the operator explicitly approves sends.
4. Verify real market-day scheduled-run evidence from an elevated/local shell without changing scheduler registration.
5. Configure and observe only the GET-only `web-view` Startup fallback and external provider smoke; keep `admin-gui` private.
6. Continue candidate evidence and web-view polish as observation curation only; keep public scoring, investment grades, trading calls, broker execution, and order routing blocked.
7. For news intelligence, move from CLI-only readback to a compact stored-data `web-view` summary so the feature produces a visible daily result before deeper recommendation-support work.

## Testing Gates

| Area | Gate |
| --- | --- |
| Operating contract | Scheduler listing and docs agree on Notify, Poll, Commands, Shutdown times. |
| Admin boundary | Admin server rejects non-loopback bind unless explicitly allowed. |
| No-run dates | Market holiday, manual exclusion, and normal business day each return a clear reason. |
| Scheduler status | Disabled, missing, access denied, and healthy states are distinguishable in CLI and GUI. |
| Daily delivery | Fragmented Telegram delivery can resume without duplicate already-sent fragments. |
| Summary grouping | Same stock code aggregates even when names vary slightly. |
| Worker health | Telegram command worker heartbeat is visible and stale state is reported. |
| DB hardening | `reports` dedupe unique indexes, `foreign_keys=ON`, and schema version marker are covered by tests. |
| Safe settings | `operator-settings` validates value ranges, requires confirmation/reason, records audit rows, suppresses duplicate no-op audit spam, and feeds runtime effective settings. |
| DB backup/cleanup | `db-verify` passes before risky DB work, `db-backup` creates an integrity-checked backup, backup prune requires preview/confirmation, and `db-cleanup` only targets KRX snapshot tables with confirmation for actual deletion. |
| KRX API rate safety | Backfill must be reviewed with `--dry-run`, real calls require `--confirm`, default batches are capped at 5 business dates, endpoint requests sleep by default, and larger batches require explicit `--allow-large-batch`. |
| Web-view V1 | Shared web-view exposes read-only data only. |
| Data quality | Raw/source, parsed/storage, aggregate, and display contracts stay documented and preserved across Telegram, admin-gui, and web-view; missing markers are excluded from aggregate values but remain visible in detail views as missing states. |
| External sharing | Cloudflare Tunnel targets only `<loopback web-view target>` or the chosen `web-view` port; `admin-gui`, DB, `.env`, Telegram, and scheduler/control endpoints are not exposed. |
| Mini PC migration | Docker is not required for the current Windows N100 path; direct Python + Task Scheduler remains the target unless the host changes to Linux/VPS. |




<!-- Merged from: docs/codex/operating-guide.md -->
## Work Todo Board

## Purpose

이 문서는 `02.Stock_Moniter`의 큰 작업축을 체크 가능한 형태로 모아둔 실행 보드다.

사용자가 `TODO-WV 진행`, `TODO-TG 해줘`, `TODO-DATA Toss 먼저`처럼 항목 ID를 말하면,
해당 항목의 범위, 산출물, 검증 기준을 기준으로 바로 작업을 시작한다.

## Use Rules

- 체크박스는 큰 작업축 완료 여부만 표시한다.
- 세부 기능을 작은 체크박스로 쪼개지 않는다.
- 새 작업축은 기존 ID와 겹치지 않는 stable ID를 부여한다.
- 완료 판정은 `Done When` 기준을 만족하고, 검증 명령 또는 실제 화면/출력 확인이 끝났을 때만 한다.
- 운영 적용은 별도 승인 전까지 보드 완료 조건이 아니다. 개발 검증과 운영 싱크는 분리한다.

## Current Priority

| Order | Todo ID | Why Now |
| --- | --- | --- |
| 1 | TODO2-RT-PRUNE | The next product risk is not missing infrastructure; it is that stored/fallback/review evidence can obscure what to check now. |
| 2 | TODO2-TG-LIVE-DRYRUN | Telegram output is preview-verified; now judge no-send previews over operating days using realtime-first order before any live send. |
| 3 | TODO2-WV-CONTENT-QA | Web-view flow is fixture/browser-smoke verified; now judge whether the mobile first viewport answers top-2, current evidence, and evidence gaps within 10 seconds. |
| 4 | TODO2-DATA-FRESHNESS-LIVE | Freshness must stay honest across CLI, web-view, and Telegram while stale KRX/flow/ETF is lowered to fallback/detail. |
| 5 | TODO2-NI-EVAL | News quality needs operating-sample evidence before it can be trusted as a primary current-evidence lane. |

## Todo Board

### [x] TODO-WV: Web-View Visible Product Flow

**Goal:**
`web-view`를 검증용 화면이 아니라 날짜별 브리핑, 후보 근거, 종목 상세, 시장/순환매 참고가 한 흐름으로 읽히는 화면으로 만든다.

**User Command Examples:**
`TODO-WV 진행`, `웹뷰 보이는 결과물 이어서`, `후보 근거 화면 정리`

**Scope:**

- 메인: 날짜 브리핑, top priority, news observation summary, intraday reference 상태.
- 관찰: candidate evidence, news badge, empty/low-evidence 상태.
- 종목: 종목 검색, 저장 리포트가 없는 종목의 empty state, stock detail news context.
- 시장: KRX/index/flow stored reference.
- 순환매: ETF rotation evidence, category/ETF context.
- `/v2` preview는 기존 `/` 대체가 아니라 정보구조 실험/검토 route로 유지한다.

**Done When:**

- fixture/test DB 기준으로 실제 브라우저에서 주요 화면과 클릭 흐름이 확인된다.
- 후보 카드에서 왜 봐야 하는지 한 줄로 읽힌다.
- 뉴스 근거가 있거나 없어도 숨기지 않고 표시된다.
- DOM/DTO에 점수, 매수/매도, 주문/브로커 실행 표현이 새지 않는다.
- `tests/test_web_view.py` 관련 검증과 browser/smoke 계열 검증이 통과한다.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/news-intelligence.md`

**Completion Note:**
2026-06-05 dev commit `e48eeab`에서 개발 검증 기준으로 완료 처리했다. `dev-fixture-db --scenario visible-product-flow` fixture DB를 만들고, `web-view-value-qa`, `web-view-browser-smoke`, `tests/test_web_view.py`, 전체 pytest를 통과했다. 실제 브라우저 smoke에서 메인/관찰/종목/시장/순환매 탭, 종목 검색, 리포트 없는 종목 `Beta Memory / 000660`의 stock-detail empty state, GET-only/POST-block 경계를 확인했다. 운영 적용, 외부 provider smoke, Startup fallback 운영 관측은 `TODO-OPS` 범위로 남긴다.

### [x] TODO-TG: Telegram Market Briefing Output

**Goal:**
웹뷰의 stored evidence와 news observation을 활용해 장초/장중/장마감 복기용 Telegram briefing 문구를 실제 발송 가능한 형태로 만든다.

**User Command Examples:**
`TODO-TG 진행`, `시황 봇 문구 만들자`, `텔레그램 브리핑 이어서`

**Scope:**

- `국장 점심 브리핑`, `장마감 전 점검`, `오늘의 시장 분위기` 같은 time-slot 문구.
- 지수, 주요 종목, 리포트 흐름, news observation, KRX/ETF/flow reference 결합.
- 실제 발송 전 preview/read-only 출력.
- 수동 review send와 scheduled send gate 분리.
- Telegram command worker와 기존 daily notification 흐름을 깨지 않는다.

**Done When:**

- fixture 또는 저장 DB 기준 briefing text/json preview가 나온다.
- 같은 근거가 `web-view`와 Telegram에서 크게 엇갈리지 않는다.
- 문구가 관찰/복기 중심이며 거래 지시처럼 보이지 않는다.
- 수동 예문 발송 또는 발송 직전 preview 검증 경로가 명확하다.
- 운영 scheduler 자동 등록은 별도 승인 전까지 하지 않는다.

**Start By Reading:**

- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/surface-guide.md`

**Completion Note:**
2026-06-05 dev commit `e48eeab`에서 개발 검증 기준으로 완료 처리했다. fixture DB 기준 `market-briefing --slot mood|lunch|preclose`, `--json` read-only preview, public-safe issue count `0`, stored news evidence 포함, `market-briefing-readiness` preview 경로를 확인했다. Telegram 실발송, 수동 review send 카운트 적립, phone review acceptance, scheduler 자동 등록은 별도 승인 전까지 운영 범위로 남긴다.

### [x] TODO-NI: News Intelligence Evidence Layer

**Goal:**
news intelligence를 독립 뉴스 수집기가 아니라 report/KRX/candidate evidence를 보강하는 판단 근거 레이어로 완성한다.

**User Command Examples:**
`TODO-NI 진행`, `뉴스 관찰 근거 이어서`, `candidate news 연결 더 해줘`

**Scope:**

- Naver 5-lane preview, source mode, coverage, indirect/summary-only guard.
- `--save-observation` 저장 결과의 readback, daily brief, text summary.
- candidate linkage evaluation과 web-view public projection.
- exact/stale KRX reference 표시.
- 운영 저장은 제한된 종목/영업일 기준으로 별도 승인 후 수행한다.

**Done When:**

- 저장 observation을 날짜/종목별로 읽고 비교할 수 있다.
- candidate evidence와 news observation 연결 근거가 화면과 CLI 양쪽에서 보인다.
- direct, caution, market-context 성격이 서로 섞여 보이지 않는다.
- stale KRX reference가 운영자에게 숨겨지지 않는다.
- raw sentiment/impact/internal recommendation payload는 shared surface에 노출되지 않는다.

**Start By Reading:**

- `docs/codex/news-intelligence.md`
- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

**Progress Note:**
2026-06-05 dev commit `24cff27`에서 daily web-view의 news observation summary, candidate badge, stock detail, `/v2` rendering에 public-safe connection label/reason을 추가했다. `tests/test_web_view.py`, `tests/test_cli_commands.py`, fixture `web-view-value-qa`, `web-view-browser-smoke`, 전체 pytest가 통과했다. raw sentiment/impact/internal recommendation은 public payload에 노출하지 않았다. 남은 범위는 저장 observation readback, CLI 비교 출력, source-mode coverage 정리다.

**Completion Note:**
2026-06-05 dev commits `c8a4a67`/`2fe1d80`에서 저장 observation readback과 CLI 비교 출력을 완료했다. `news-intelligence-observations`는 저장 run 전체의 `source_mode_coverage`를 JSON으로 내보내며 source mode, source lane, direct/indirect/market-context 합계, match scope, KRX exact/stale/missing/none 상태, candidate-linkage label, operator recommendation-support label, read-only/operator-only 경계 플래그를 한 번에 비교할 수 있다. text 출력도 per-run evidence 앞에 같은 coverage 요약을 표시한다. `news-intelligence-daily-brief` JSON/text에도 표시 대상 saved-run 그룹 기준 coverage가 추가됐다. RED/GREEN 테스트, `python -m pytest tests\test_cli_commands.py tests\test_news_intelligence.py -q -k news_intelligence` (`29 passed`), 전체 CLI 테스트 (`323 passed`), temp DB CLI smoke에서 `source-mode coverage`, `source_modes: naver_5_lane_preview=2`, `labels: stale_krx_check_first=1, strengthen_existing_candidate=1`, KRX exact/stale 집계를 확인했다. public web-view raw sentiment/impact/internal recommendation 노출 금지는 기존 public projection 테스트로 유지했고 public route는 변경하지 않았다.

### [x] TODO-DATA: Market Data, ETF, And Source Freshness

**Goal:**
KRX/ETF/flow/Toss/X 같은 외부 데이터 축을 실제 동작 가능한 source lane으로 분리하고, freshness와 한계를 화면/문구에 드러낸다.

**User Command Examples:**
`TODO-DATA 진행`, `TODO-DATA Toss 먼저`, `ETF 쪽 실제 기능 확인`, `데이터 소스 정리`

**Aliases:**
`TODO-TOSS`, `TODO-ETF`, `TODO-X`는 모두 `TODO-DATA`의 하위 범위로 해석한다.

**Scope:**

- KRX Open API daily stock/ETF/index baseline과 next-business-day `08:00` publication rule.
- KRX Data Marketplace `[12009]` report-mentioned stock flow lane.
- ETF rotation evidence와 구성종목/source 가능성 검토.
- Toss OpenAPI: promoted bounded Top2 current-price/same-day provisional investor-volume and latest-date Top20 market-context projections; keep account/order, broad polling, and unapproved source expansion in the read-only lab/hold boundary.
- X/no-login recap lab: 로그인 없이 접근 가능한 공개 글/링크 요약 가능성.

**Done When:**

- 각 source lane이 production/lab/hold로 분리된다.
- 실제 동작 가능한 read-only probe와 불가능/보류 범위가 문서화된다.
- web-view/Telegram에 붙일 때 freshness 표시가 모호하지 않다.
- Toss promoted projections stay bounded, source-labelled, and score-free; X and unapproved Toss capabilities remain separate lab work.

**Start By Reading:**

- `docs/codex/data-governance.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/toss-openapi-lab.md`
- `docs/codex/toss-openapi-lab.md`

**Progress Note:**
2026-06-05 dev commits `80c9b98`/`f420bdc`에서 daily web-view API와 화면에 `source_freshness_summary`를 추가했다. 선택 날짜별 Naver reports, KRX Open API market/ETF, KRX Data Marketplace investor flow, Toss OpenAPI lab-hold 상태가 `exact`/`stale`/`missing`/`lab_hold`로 표시된다. 기본 DB는 schema가 오래되어 read-only QA가 migration 안내로 중단됐으므로, production/default DB를 쓰지 않고 temp fixture DB로 `web-view-value-qa`, `web-view-browser-smoke`, `tests/test_web_view.py`, `tests/test_cli_commands.py`, 전체 pytest를 통과시켰다. 남은 범위는 Toss/X lab feasibility, ETF 구성종목/source 검토, Telegram freshness 문구 연결이다.

**Progress Note:**
2026-06-05 dev commits `247a420`/`4838b22`에서 `market-briefing` Telegram preview에도 source freshness를 연결했다. text preview는 `데이터 기준` 섹션으로 Naver reports, KRX market, ETF daily, Investor flow, Toss OpenAPI 상태를 `exact`/`missing`/`lab-hold`와 기준일로 표시한다. JSON preview는 web-view와 같은 `source_freshness_summary`를 포함하고, Toss OpenAPI는 `lab_hold`, `live_fetch=false`, `affects_ordering=false`로 남긴다. RED/GREEN 테스트와 `python -m pytest tests\test_cli_commands.py -q -k market_briefing` (`16 passed`)를 확인했고, temp fixture DB smoke에서 message의 source freshness 줄과 JSON summary를 확인했다. 남은 범위는 Toss/X lab feasibility와 ETF 구성종목/source 검토다.

**Completion Note:**
2026-06-05 dev commits `65d41f4`/`d2c641e` completed the remaining source-lane boundary slice with the read-only `data-source-lane-audit` CLI. The command emits a concrete JSON/text audit with Naver reports, KRX stock/index/ETF daily, KRX investor flow, Toss OpenAPI, and X public recap classified as `production`, `production_limited`, `hold`, or `lab`. The output explicitly states `etf_daily | production | constituents=not_loaded`, `toss_openapi | hold | live_fetch=false | affects_ordering=false`, and `x_public_recap | lab | separate_lab_branch=true | login_dependency_allowed=false`; the JSON `done_when_coverage` confirms source lanes are classified, web-view freshness is connected, Telegram freshness is connected, Toss/X are not exaggerated, and ETF constituent status is explicit. Verified `python -m stock_monitor data-source-lane-audit`, `python -m stock_monitor data-source-lane-audit --json`, `python -m pytest tests\test_cli_commands.py -q -k data_source_lane_audit` (`3 passed`), `python -m pytest tests\test_cli_commands.py -q` (`326 passed`), and full `python -m pytest -q` (`732 passed`). No live fetch, DB write, Telegram send, scheduler registration, admin-gui connection, or web-view connection was added.

### [x] TODO-OPS: Operations, Sync, And Performance Closeout

**Goal:**
개발 결과를 dev에 모으고, 운영 적용은 묶음 단위로 싱크하면서 성능/버튼/GET-only/read-only 계약을 재관측한다.

**User Command Examples:**
`TODO-OPS 진행`, `운영 싱크 준비`, `N100 관측 결과 반영`

**Scope:**

- dev branch를 실험 결과 통합/검토 기준으로 유지.
- main/operating PC cherry-pick은 batch 단위로 적용.
- `/api/daily/{date}?intraday_market_top=1` 같은 cold/warm perf 재관측.
- archive/news count, candidate badge, stock detail click, `/v2` preview, ETF rotation smoke.
- 운영 관측 메모는 `docs/codex/operations/`에 두되 public docs에는 세부값을 노출하지 않는다.

**Done When:**

- dev와 운영 main의 적용 대상 차이가 subject 기준으로 설명된다.
- batch 적용 순서와 충돌 예상 파일이 정리된다.
- read-only smoke, GET-only contract, public wording scan이 통과한다.
- 운영 관측에서 나온 UI/perf 문제는 다음 개발 항목으로 환류된다.

**Start By Reading:**

- `docs/codex/mini-pc-runbook.md`
- `docs/codex/surface-guide.md`
- `docs/codex/architecture-guide.md`

**Progress Note:**
2026-06-05 dev commits `77a2321`/`02f13f7`에서 read-only `ops-sync-preview` CLI를 추가했다. 이 출력은 `origin/main..dev` commit subjects, changed file groups, conflict watch paths, `data/` untracked 분리, batch 제외 경로, 별도 승인 필요 작업, 검증 명령을 JSON/text로 보여준다. 기본 DB schema가 target보다 오래된 경우 stack trace 대신 `default_db_schema_not_current` blocker로 표시한다. fixture DB 기준 `web-view-value-qa` issue/warning `0`, `web-view-browser-smoke` issue `0`, `api-perf-summary` 읽기 성공, 전체 pytest `720 passed`를 확인했다. 남은 범위는 기본 DB migration 승인/처리 여부 결정, 실제 운영 적용 batch 검증, 운영 관측에서 나온 perf/UI 항목 환류다.

**Progress Note:**
2026-06-05 dev commits `4b4f2e2`/`6cc9973`에서 `ops-sync-preview --json`에 `operating_pc_handoff`를 추가했다. handoff prompt의 첫 줄은 운영/개발 경계 규칙에 맞춰 `운영 PC용`이며, 비교 범위, source sync readiness, `data/` untracked 제외 안내, 커밋 요약, 변경 파일 그룹, 충돌 주의 경로, 검증 명령, 현재 blocker, 별도 승인 전 금지 작업, 적용 batch 제외 항목을 한 번에 출력한다. 이 기능은 read-only이며 DB write, scheduler 변경, Telegram 실발송, admin-gui 프로세스 조작을 하지 않는다. `python -m pytest tests\test_cli_commands.py -q -k ops_sync_preview` (`3 passed`)와 실제 `ops-sync-preview --base origin/main --head dev --json` handoff prompt 생성을 확인했다. 기본 DB schema blocker와 실제 운영 PC batch 검증은 여전히 별도 승인/운영 세션 범위다.

**Progress Note:**
2026-06-05 dev commits `9524f56`/`1b1c0dc` improved default-DB stale-schema handling for OPS verification commands. When the default DB is still schema `5/7`, `db-verify --json` and `ops-readiness --json` now return structured JSON with `surface`, `ready=false`, `schema_status.status=migration_required`, `pending_versions=[6,7]`, `default_db_schema_not_current`, review commands, and separate-approval requirements instead of a stack trace. `api-perf-summary --json` now runs without requiring DB schema current because it only reads API performance logs; the current dev-PC log smoke returned `record_count=1980` and `endpoint_count=62`. Verified focused stale-schema tests (`2 passed`), actual default-DB CLI smoke for `db-verify --json`, `ops-readiness --json`, `api-perf-summary --json`, `ops-sync-preview --json`, full CLI tests (`328 passed`), and full `python -m pytest -q` (`734 passed`). Remaining scope is still explicit migration approval/handling for the default or operating PC DB and final operating-PC batch verification.

**Progress Note:**
2026-06-05 dev commits `01d27d1`/`ffddffb` added `schema_action_plan` to `ops-sync-preview --json` and the generated `operating_pc_handoff.prompt`. The handoff now separates pre-approval checks (`ops-sync-preview`, `db-migrate --dry-run`, `db-verify --json`) from post-approval commands (`db-backup --tag pre-schema-migration`, `db-migrate`, `db-verify --json`, `ops-readiness --json`) and repeats the forbidden-without-approval list including `schema migration on operating PC`. Actual default-DB smoke returned `source_sync_ready=false`, `schema_status=migration_required`, `approval_required=true`, `pre_approval_count=3`, `post_approval_count=4`, and prompt markers for `Schema action plan` and `post-approval`. Verified `python -m pytest tests\test_cli_commands.py -q -k ops_sync_preview` (`3 passed`), full CLI tests (`328 passed`), and full `python -m pytest -q` (`734 passed`). Remaining scope is the explicit approval decision and actual operating-PC batch verification.

**Progress Note:**
2026-06-05 dev commits `087cfcd`/`413ce3f` added `db-migration-rehearsal`, which uses a temporary SQLite backup copy to apply migrations and run verification without writing the source DB. Actual default-DB smoke with a `%TEMP%` work dir returned `ready=true`, `read_only_source=true`, `writes_source_db=false`, `copy_retained=false`, source schema `5/7` before and after, copy schema `5/7 -> 7/7`, `copy_verify_ready=true`, and `blocker_count=0`. Verified focused rehearsal tests (`2 passed`), full CLI tests (`330 passed`), and full `python -m pytest -q` (`736 passed`). Remaining scope is not technical rehearsal anymore; it is explicit approval for the real default/operating-PC DB migration and the actual operating-PC batch verification.

**Progress Note:**
2026-06-05 dev commits `345c4fb`/`5ba0a6c` connected `db-migration-rehearsal --json` back into `ops-sync-preview` as a pre-approval schema action. Actual `ops-sync-preview --json` smoke still exits `1` because the default DB schema is stale, but its `schema_action_plan.pre_approval_commands` now includes `ops-sync-preview`, `db-migrate --dry-run`, `db-migration-rehearsal --json`, and `db-verify --json`, and the operating-PC handoff prompt includes the rehearsal command. Verified focused ops-sync test (`1 passed`), full CLI tests (`330 passed`), and full `python -m pytest -q` (`736 passed`).

**Completion Note:**
2026-06-05 dev commits through `e25e17e` completed the dev-side operations closeout. `ops-sync-preview --json` now describes `origin/main..dev` by commit subject, changed file group, conflict-watch path, batch exclusions, and an `operating_pc_handoff.prompt` whose first line is `운영 PC용`. It also separates schema pre-approval commands from post-approval commands and includes `db-migration-rehearsal --json`. Default DB schema is still `5/7`, so actual DB migration remains blocked until explicit approval; however, `db-migration-rehearsal` proved a temp copy migrates `5/7 -> 7/7` with `copy_verify_ready=true` and `writes_source_db=false`. Final dev-side smoke used a `%TEMP%` visible-product-flow fixture: `web-view-value-qa --date 2026-05-08 --stock-limit 20 --json` returned issue/warning `0`, and `web-view-browser-smoke --date 2026-05-08 --stock-limit 20 --json` returned issue `0`, tab/click/search coverage across desktop/tablet/mobile, POST `405`, and `/api/status` `404`. `docs-hygiene-audit --json` scanned 9 public/canonical docs with issue `0`; `api-perf-summary --json` read the current dev log with `record_count=1980` and `endpoint_count=62`; full CLI tests and full pytest passed in the latest code pass (`330 passed`, `736 passed`). Real operating-PC DB migration, scheduler changes, Telegram real sends, admin-gui process operations, and production/operating DB writes remain outside this board and require separate explicit approval.

### [x] TODO-ADMIN: Admin / Web-View / Operator-Review Boundary

**Goal:**
admin-gui는 운영 상태/제어/복구/설정/audit만 담당하고, 판단 화면은 web-view projection 또는 future operator-review로 분리한다.

**User Command Examples:**
`TODO-ADMIN 진행`, `관리자 화면 정리`, `operator-review 경계 잡자`

**Scope:**

- admin-gui 메뉴와 payload에서 판단/후보/raw news review가 섞이지 않는지 확인.
- web-view는 shared read-only stored-data projection으로 유지.
- operator-review는 future private review surface로만 정의하고, 구현 전 route/access/test contract를 별도 수립.

**Done When:**

- admin-gui에 candidate evidence/raw news/internal judgment review가 screen body로 들어가지 않는다.
- web-view public projection 허용 범위가 문서와 테스트에서 일치한다.
- future operator-review가 admin-gui와 같은 것으로 오해되지 않는다.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/surface-guide.md`
- `tests/test_admin_gui.py`

**Completion Note:**
2026-06-05 dev commits `72312a3`/`3de33c4` added a read-only `admin-boundary-audit` CLI and tests. The audit emits a concrete JSON/text boundary report for `admin-gui`, `web-view`, and future `operator-review`: no live fetch, no DB write, no Telegram send, no scheduler registration, admin HTML judgment-review token count, public-content token count, operator status payload availability, web-view `/api/status` expected 404, and operator-review reserved/unimplemented state. Default DB remains untouched; when its schema is stale the command returns `default_db_schema_not_current` as a blocker instead of a stack trace. Fixture DB verification returned `ready=true`, zero admin HTML judgment-review matches, zero admin HTML public-content matches, zero operator status forbidden matches, and `operator_review.route_present_in_admin_html=false`. Verified with `python -m stock_monitor admin-boundary-audit --json`, fixture `admin-boundary-audit --json`, `python -m pytest tests\test_admin_gui.py tests\test_operator_status.py tests\test_cli_commands.py -q -k "admin_boundary_audit or admin_gui or operator_status"` (`65 passed`), and full `python -m pytest -q` (`723 passed`).

### [x] TODO-DOC: Public Documentation And Information Hygiene

**Goal:**
README, roadmap, contracts, changelog가 현재 main/dev 현실과 맞고, 공개 문서에 개인 경로, secret, 실행 가능한 민감 URL, 과한 운영 세부가 남지 않게 유지한다.

**User Command Examples:**
`TODO-DOC 진행`, `문서 현행화`, `README 다시 훑어봐`

**Scope:**

- README 공개용 설명 유지.
- canonical docs 간 상태/목표/완료율 충돌 제거.
- public docs hygiene test 유지.
- lab branch는 완료 기능처럼 쓰지 않고 roadmap/lab으로만 표현.
- 운영 관측 상세는 `docs/codex/operations/`에 두고 public docs에는 요약만 반영.

**Done When:**

- `documentation-index.md`가 새 문서/계약을 찾을 수 있게 갱신된다.
- README와 canonical docs가 서로 다른 완료율/방향을 말하지 않는다.
- 공개 문서 정보노출 회귀 테스트가 통과한다.
- Toss/Telegram/X lab 상태가 과장되지 않는다.

**Start By Reading:**

- `README.md`
- `docs/codex/documentation-index.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/operating-guide.md`

**Completion Note:**
2026-06-05 dev commits `3d549b3`/`d066886` added a read-only `docs-hygiene-audit` CLI and refreshed public/canonical docs. The audit scans README, the core canonical status/roadmap docs, `surface-guide.md`, `data-governance.md`, `data-governance.md`, and `news-intelligence.md` for local absolute user paths, real external provider URLs, secret-like assignments, and raw access-code examples while returning only redacted file/line/count metadata. `documentation-index.md`, roadmap, and core contract links were converted from local absolute workspace paths to relative links, historical external web-view provider URL mentions were replaced with placeholders, and README now lists `admin-boundary-audit --json` and `docs-hygiene-audit --json`. Verified `docs-hygiene-audit --json` returned `ready=true`, `scanned_file_count=9`, and `issue_count=0`; `tests/test_cli_commands.py -q -k docs_hygiene_audit` returned `4 passed`; `tests/test_cli_commands.py -q` returned `321 passed`.

## Second Todo Board

### [x] TODO2-OPS-REAL: Operating-PC Sync And Real Migration Handoff

**Goal:**
Turn the dev-verified closeout into a controlled operating-PC handoff without silently performing production DB writes, scheduler changes, Telegram real sends, or admin-gui process operations.

**Scope:**

- Generate and review the operating-PC prompt from `ops-sync-preview --json`.
- Confirm `dev` is pushed and identify the exact commit range to sync.
- Run pre-approval checks only: `ops-sync-preview`, `db-migrate --dry-run`, `db-migration-rehearsal --json`, and `db-verify --json`.
- Prepare the post-approval command sequence for DB backup, real migration, verification, and readiness.
- Keep `data/` and any local fixtures out of commits and sync batches unless explicitly approved.

**Done When:**

- The operating-PC handoff starts with `운영 PC용`.
- The handoff lists exact pre-approval and post-approval commands.
- The default/operating DB schema state is known before any real migration.
- Real DB write, scheduler registration/change, Telegram real send, and admin-gui process operation are still blocked unless separately approved.
- A post-sync verification checklist exists for the operating PC.

**Start By Reading:**

- `docs/codex/mini-pc-runbook.md`
- `docs/codex/surface-guide.md`
- `docs/codex/architecture-guide.md`
- `docs/codex/operating-guide.md`

**Progress Note:**
2026-06-05 operating-PC pre-approval sync reached dev commit `c99acb1` by fast-forwarding local `dev` to `origin/dev`. No real `db-migrate`, scheduler registration/change, Telegram real send, or admin-gui process operation was run. The operating shell had to use `.venv\Scripts\python.exe -m ...` because system `python -m ...` resolved to the Microsoft Store stub. Pre-approval checks are not ready yet: `ops-sync-preview --base origin/main --head dev --json` failed with `unexpected_untracked_files` for `scripts/experimental/probe_scrapling_import.py` and `scripts/experimental/requirements-scrapling.txt`; `db-migrate --dry-run` passed with schema `7/7` and no pending migrations; `db-verify --json` failed on a partial KRX daily snapshot for `2026-06-03` where `etf-daily=873` exists but stock/index endpoints are empty; `db-migration-rehearsal --json` wrote only a temp copy and failed because db-verify failed on that migrated copy. Next action is not schema migration; it is to resolve or explicitly approve the two operating-PC untracked experimental files and repair/rebaseline the partial KRX daily snapshot after backup/verify discipline.

**Progress Note:**
2026-06-05 second operating-PC read-only check fast-forwarded from `c99acb1` to `17e8835` and confirmed `dev == origin/dev` at `17e8835f220ac32a11d80b36172860ec6534cc8e`. `data/` stayed untouched. The two non-data untracked files were inspected without modification and confirmed as lab/probe artifacts: `scripts/experimental/probe_scrapling_import.py` prints Scrapling import/fetcher class availability, and `scripts/experimental/requirements-scrapling.txt` pins `scrapling[fetchers,shell]==0.4.8`; they remain `ops-sync-preview` blockers because they are outside `data/`. `db-migrate --dry-run` again reported schema `7/7` with no pending migrations. `db-migration-rehearsal --json` kept the source DB read-only and wrote only a temp copy, but stayed `ready=false` because copied DB verification failed. `db-verify --json` showed integrity `ok`, FK violations `0`, no pending migrations, and one data-quality blocker: partial KRX daily snapshot `2026-06-03` with `etf-daily=873` while `stock-kospi-daily`, `stock-kosdaq-daily`, `index-krx-daily`, `index-kospi-daily`, and `index-kosdaq-daily` are empty. Read-only operation-event evidence showed all six endpoints empty on `2026-06-04 08:10`, then only `etf-daily` success on `2026-06-05 08:10`. Next approved work should first decide the lab-file disposition, then run a backup-first bounded KRX repair/retry plan for `2026-06-03`; do not treat this as a schema migration.

**Progress Note:**
2026-06-05 operating-PC approved cleanup moved the two Scrapling lab/probe files out of the worktree into `..\_operating_local_hold\scripts_experimental_scrapling\` and left `data/` untouched. A backup `data\backups\<stock_monitor_backup.db>` was created with integrity `ok`. The bounded KRX retry was correctly limited to `2026-06-03` and five missing stock/index endpoints, but completed with `incomplete_endpoints=5` and stored `0` parsed rows, so `db-verify` still failed on the same partial snapshot. Fresh source review then identified `2026-06-03` as a KRX market holiday for the 2026 local elections; the practical fix is not further retry/cleanup, but updating the dev default holiday calendar and making `db-verify` ignore partial KRX snapshot rows on configured non-business days. This keeps the source DB data intact and avoids turning holiday endpoint emptiness into a false readiness blocker.

**Progress Note:**
2026-06-05 dev fix added `2026-06-03` and `2026-07-17` to the default 2026 KRX holiday calendar, passed configured holidays into the direct `db-verify` CLI path, and changed the partial KRX daily snapshot check to skip configured non-business days. Regression coverage now asserts those 2026 holidays are in `RuntimeConfig`, confirms `db-verify` still fails for a real business-day partial snapshot, confirms it allows the `2026-06-03` holiday ETF-only snapshot, and updates operator-control next-business-day output from `2026-06-03` to `2026-06-04`. Verified with focused tests and full `python -m pytest -q` (`737 passed`). Operating PC should sync this before rerunning `db-verify`; no extra KRX retry or cleanup is the next default action.

**Completion Note:**
2026-06-05 operating-PC sync and readiness finished at dev commit `2fa1efc`. The operating worktree is `dev...origin/dev`, tracked clean, with only `data/` untracked and untouched. `db-verify --json` is ready with integrity `ok`, schema `7/7`, no pending migrations, FK violations `0`, and quality issue totals `0`; `db-migration-rehearsal --json` returned `ready=true`; `ops-sync-preview --base origin/main --head dev --json` returned `source_sync_ready=true` with empty blockers. No additional KRX retry, cleanup/delete/import, real `db-migrate`, scheduler registration/change, Telegram real send, admin-gui process operation, broker/order routing, or secret output was performed.

### [ ] TODO2-RT-PRUNE: Realtime-First Public Surface Pruning

**Goal:**
Reorder public `web-view` and Telegram thinking around current observation evidence first, while lowering previous-day/stored/reference/reaction evidence to fallback/detail/review.

**Scope:**

- Use `오늘 볼 것 -> 현재 근거 -> 전일 참고 -> 부족한 근거 -> 복기/연구` as the shared ordering contract.
- Keep top-2 candidate identity, same-day saved news, current quote/turnover evidence, and source checked time in the first-read path when available.
- Keep KRX daily, `[12009]` flow, ETF, Toss 20:00 baseline, target progress, and reaction windows available but lower in visual/message priority unless they directly explain current top-2 evidence.
- Maintain the public boundary: no scores, grades, buy/sell calls, entry/exit/take-profit/target-return/conviction, broker execution, or order routing.
- Use the 10-business-day operating checklist in `docs/codex/surface-guide.md` before declaring the related TODO2 items complete.
- Use the daily read-only routine in that plan; do not treat one clean preview or smoke run as completion.

**Done When:**

- 10 business days have a review row covering Top2, current evidence, previous-day evidence usefulness, news state, Telegram readability, web-view readability, and next-day keep/lower decisions.
- Each review row records the command evidence used for the check, including any command that could not run and its read-only substitute.
- Telegram no-send previews read in the new order and still pass public-safe wording checks.
- The web-view first mobile viewport can be understood in about 10 seconds as top-2/current evidence/gaps.
- Stale KRX/flow/ETF and reaction/backtest evidence no longer dominate the first-read path.
- No production DB write, scheduler change, Telegram real send, admin-gui process action, or broker/order route is added for this TODO.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-TG-LIVE-DRYRUN: Telegram Real-Data No-Send Dry Run

**Goal:**
Use operating-like stored data to prove Telegram briefing payload quality, paging, retry, and outbox/readiness behavior before any real Telegram send is approved.

**Scope:**

- Run market briefing preview for the key slots against recent stored data.
- Compare text and JSON payloads for public-safe wording and evidence coverage.
- Check paging, retry, and outbox/readiness behavior through read-only or no-send paths.
- Confirm freshness lines for Naver/KRX/ETF/flow/Toss/X remain accurate and not overstated.
- Keep Telegram real send disabled until a separate explicit approval.

**Done When:**

- Mood/lunch/preclose previews render in the realtime-first order: `오늘 볼 것`, `현재 근거`, `전일 참고`, `부족한 근거`, `복기/연구`.
- Recent-data previews have no public trading call, numeric score, buy/sell signal, broker, or order-routing wording.
- Outbox/readiness state can be reviewed without sending.
- Retry/paging behavior has focused test or CLI evidence.
- Missing/stale source states are visible in the message instead of hidden.
- The final report includes 10-business-day readability evidence before live send approval.

**Start By Reading:**

- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/surface-guide.md`
- `docs/codex/news-intelligence.md`

### [ ] TODO2-WV-CONTENT-QA: Web-View Recent-Date Content QA

**Goal:**
Move beyond fixture smoke and verify that recent-date web-view content is usable, scan-friendly, and public-safe across desktop, tablet, and mobile.

**Scope:**

- Select several recent business dates from stored data.
- Run value QA and browser smoke for daily, watchlist/candidate, stock detail, market, and ETF rotation surfaces.
- Review empty states, stale source indicators, search behavior, and candidate/news evidence labels.
- Confirm public DTOs do not expose raw sentiment, internal recommendation payloads, numeric scores, buy/sell calls, broker execution, or order-routing language.
- Capture any content-quality defects as concrete follow-up items instead of broad redesign work.

**Done When:**

- Multiple recent dates have CLI/browser evidence and the 10-business-day checklist records first-read usefulness.
- Desktop/tablet/mobile smoke finds no blocking overlap or broken navigation.
- Public-safe wording scan passes.
- Empty/low-evidence states are understandable without operator context.
- Remaining defects are listed with date, surface, symptom, and suggested fix.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/news-intelligence.md`

### [ ] TODO2-DATA-FRESHNESS-LIVE: Live Source Freshness Verification

**Goal:**
Validate source freshness behavior on recent operating-like dates so KRX, ETF, investor-flow, Toss, and X states are displayed honestly.

**Scope:**

- Re-run `data-source-lane-audit --json` and compare with web-view/Telegram freshness output.
- Check KRX latest-date logic and next-business-day publication assumptions.
- Verify ETF/index data presence and keep ETF constituents marked clearly when not loaded.
- Treat the promoted bounded Toss Top2/Top20 projection as `production_limited`; keep account/order, broad polling, and other Toss endpoints on hold, and keep X as lab.
- Document source-specific stale/missing cases with commands and observed dates.

**Done When:**

- Source lanes remain classified as production, production_limited, lab, or hold.
- Freshness output is consistent across CLI, web-view, and Telegram preview.
- Stale or previous-day KRX/flow/ETF states are labelled as fallback/detail and do not lead the first-read path when current evidence exists.
- ETF constituent absence is explicit and not presented as loaded coverage.
- Promoted Toss projections may serve the bounded public GET-only `web-view` route and approved market-briefing context only; they do not connect to `admin-gui`, account/order endpoints, broad polling, or unapproved DB writes. X remains disconnected from production runtime paths.
- Any source gap has a dated evidence note and next action.

**Start By Reading:**

- `docs/codex/data-governance.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/toss-openapi-lab.md`
- `docs/codex/toss-openapi-lab.md`

### [ ] TODO2-NI-EVAL: News Evidence Quality Evaluation

**Goal:**
Evaluate whether the news-intelligence evidence layer is useful on real samples, not only structurally present.

**Scope:**

- Sample recent dates and mentioned stocks with stored observations.
- Review candidate linkage labels, source modes, direct/caution/market-context separation, and stale KRX cues.
- Identify duplicate, stale, weak, or misleading evidence cases.
- Confirm raw sentiment/impact/internal recommendation details remain out of public surfaces.
- Turn quality issues into focused tests or CLI/report improvements.

**Done When:**

- Sample cases have a reviewed evidence table or CLI output.
- False-positive, duplicate, stale, and weak-evidence cases are classified.
- The review records whether direct/caution/no-match news changed the current top-2 reading or only belonged in fallback/detail.
- At least one quality improvement is implemented if a repeated defect appears.
- Public projection remains recommendation-safe.
- Remaining evaluation gaps are tied to specific sample dates or source lanes.

**Start By Reading:**

- `docs/codex/news-intelligence.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-ADMIN-ACCESS: Admin/Web-View Access Boundary Verification

**Goal:**
Verify the admin-gui, web-view, and future operator-review boundary in an operating-like environment without manipulating production admin processes unless explicitly approved.

**Scope:**

- Run `admin-boundary-audit --json` against the available approved DB/environment.
- Confirm web-view remains GET-only and does not expose operator/admin payloads.
- Confirm admin-gui remains operator-only and does not become a public evidence review surface.
- Keep future operator-review reserved unless separately scoped.
- Prepare operating-PC access checks that do not include process control by default.

**Done When:**

- Boundary audit is clean or lists concrete blockers.
- Public web-view rejects unsafe methods and lacks admin/status/operator endpoints.
- Admin-gui surfaces do not expose public-facing recommendation/evidence review content incorrectly.
- Operator-review remains explicitly reserved/unimplemented.
- Any operating-PC process action is separated behind an explicit approval step.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/surface-guide.md`
- `tests/test_admin_gui.py`
- `tests/test_operator_status.py`

## Lab Branches To Keep Separate

| Branch / Lane | Todo Link | Current Rule |
| --- | --- | --- |
| `toss-openapi-readonly-lab` | `TODO-DATA` | Read-only docs/probe lane only until keys, permissions, and order-boundary review are complete. |
| `telegram-market-briefing-slots` | `TODO-TG` | Product text/slot refinement lane; merge into dev when it improves the shared briefing contract. |
| `x-browser-recap-lab` | `TODO-DATA` | No-login/public-access feasibility lane; do not depend on an authenticated browser session by default. |

## Default Prompt Template

Use this when starting a todo item:

```text
<project root> 범위에서 dev 브랜치 기준으로 진행해줘.

목표:
<TODO-ID>를 진행한다. docs/codex/operating-guide.md의 해당 항목을 기준으로,
새로운 작은 기준/guard를 늘리기보다 실제 화면/출력/동작으로 확인 가능한 결과를 만든다.

전제:
- 관련 canonical docs를 먼저 확인한다.
- 운영 DB write, scheduler 등록/변경, Telegram 실발송, broker/order-routing은 명시 승인 전까지 하지 않는다.
- lab branch 내용은 실제 dev/main 반영분과 구분한다.
- public/shared surface에는 점수, 매수/매도, 주문/브로커 실행 표현을 노출하지 않는다.
- 구현 후 최소 검증을 실행하고, 커밋/푸시는 별도 지시가 있으면 한 번에 처리한다.

보고:
- 진행한 TODO-ID
- 실제 산출물
- 검증 결과
- 아직 남은 범위
- 다음에 이어갈 명령 예시
- 한줄리뷰
```

## Operator Market Research Note Run

When the operator needs daily market context beside the existing Top2 snapshot, keep the flow local and manual:

```powershell
python -m stock_monitor market-research-note --snapshot data\reviews\realtime-first\YYYY-MM-DD_1500.json --market-flow data\reviews\market-research\YYYY-MM-DD_flow.json
```

This command reads local JSON and writes a local JSON/Markdown review note. It does not fetch a provider, write SQLite, send Telegram, register a scheduler, or connect a public surface. Treat `invalid_for_slot` as an operational timing exception, not as market evidence.

`market-research-note` remains a local manual review artifact. The weekday `StockMonitor-Poll` task is the separate operating lane: every 30-minute in-window poll rebuilds report summaries and then collects bounded news observations for the same Top2 candidate codes. The shared `scheduled_run_at` and codes are recorded as a `poll-news` operation event.
