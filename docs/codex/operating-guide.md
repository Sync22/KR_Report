# Operating Guide

Current operating state, delivery sequence, roadmap, and work board.

## Included sections
- Current Work
- Work Todo Board
- Historical completion index

<!-- Merged from: docs/codex/operating-guide.md -->
## Current Work

### Snapshot (2026-09-28)

The repository is in live-market validation and operational hardening, not initial MVP construction. A read-only operator-status snapshot from this Windows work environment at 2026-09-28 09:01 KST showed `StockMonitor-TossCloseSnapshot` healthy, capture pending before 20:05, and no health warnings. This does not identify the environment as the designated main PC or mini PC, or verify today's close capture and Telegram delivery.

Current contracts describe the Naver report-to-summary/Telegram pipeline, the operator-only `admin-gui`, and a GET-only, stored-data-first `web-view`. Toss 20:00 snapshots own stored current market/ETF/flow context. The Main Top2 indicator card calls Toss directly after an explicit button press and calculates Newbby-set factual indicators locally; it never changes ordering or stores values in Stock Monitor. Existing KRX rows are historical analysis/recovery data only. See [AGENTS.md](../../AGENTS.md), [surface-guide.md](surface-guide.md), [data-governance.md](data-governance.md), [market-data-runbook.md](market-data-runbook.md), and [mini-pc-runbook.md](mini-pc-runbook.md).

### Local implementation status (2026-10-08)

1. Candidate and nested daily DTOs strip the internal numeric sort field and identify Toss-backed dates/scope as Toss. `TODO2-WV-CONTENT-QA` completed on 2026-09-28; see its recent-date and responsive smoke evidence below.
2. Local Toss capture reports required-domain coverage, marks incomplete events partial/empty, preserves explicit security classification, and excludes candidate-only rows from snapshot dates. Web-view and market-briefing freshness carry partial status/missing domains; operator status warns when a healthy Toss task lacks a due capture; mini-PC preflight includes that task and no longer requires retired KRX backfill tasks. A late skipped capture warns as missing, while suppression and a prior successful capture remain non-alerting. The focused regression set recorded on 2026-09-28 passed 470 tests. Real host/date validation remains in `TODO2-DATA-FRESHNESS-LIVE`.
3. Web-view first-load query work now bounds recent-date reads by source and reuses the already loaded Toss snapshot date. Authenticated browser/API timing remains pending in `TODO2-WV-FIRST-LOAD`.
4. The current working tree propagates Telegram send failures, records empty-alert delivery failures, and includes intraday failures in operator health. This is local code/test evidence only; no real Telegram send, scheduler run, or operating-DB validation was performed.
5. Retry policy for an accepted Telegram send whose response is lost remains undecided and unchanged; it is tracked in `TODO2-TG-LIVE-DRYRUN`.
6. Lunch/pre-close briefings lead with same-day Toss context and its ranking/query timestamps. The 08:20 pre-open briefing labels prior-day report content as `전일 리포트`, saved market/flow values as `이전 종가 비교`, and adds generic Toss market-wide context only for the current briefing date with date-valid ranking/index/flow timestamps. Naver KRX quote enrichment appears as current only when its trade date matches the briefing date. Toss ranking venue inclusion for NXT remains unverified and is not labeled NXT. Mood remains unchanged.
7. Stock-Newbby `chart-assistant` remains installed for user-requested operator chart review. Public Main's `차트 · 지표 확인` button requests up to 800 Toss adjusted daily candles (200 × 4 pages) only for the server-derived Top2 and selected date; Stock Monitor computes Newbby-set factual indicators and aligned chart series locally. It displays a 50/100/200-trading-day window (default 200), initially selects RSI 14 as the supplementary indicator, and shows candlesticks, SMA 20/60/120/200, volume, a selected RSI/MACD/OBV/ATR pane, Toss source/fetch time, actual bar date, page/cursor status, and unknown bar-finality status. The condition card states the explicit prior-20-bar high entry and prior-10-bar low exit reference criteria, explains that indicator and volume confirmation are also required, and retains the detailed values. Top2 evidence places live-flow reference date/query time in its header and target-range aggregate dates beside amounts below a separator under a bold title. The chart does not contact a Newbby server, store values in SQLite, change candidate order, or contact scheduler/Telegram. Unsupported fields remain unavailable; distinguish price reference lines from unavailable recognized channel/triangle shapes, and do not treat no recognized shape as opposite-direction evidence. Triangle intersections retain the straight-line extrapolation warning.
8. `operator-review` is a separate loopback-only GET panel (`127.0.0.1:8767`) for the selected-date Main candidate order, source dates, evidence, and information gaps. It opens Stock-Newbby charts only through an operator-clicked deep link; Newbby must already be running to fetch the linked symbol. Its SQLite connection is read-only. The public Main indicator route is a separate explicit-action exception documented in [surface-guide.md](surface-guide.md) and [data-governance.md](data-governance.md).
9. The public Main summary now surfaces the selected Main candidates' stored reasons and recorded information gaps, alongside existing date/source freshness. It adds no score, grade, or trading instruction.
10. Policy resolution (approved 2026-10-09, clarified 2026-10-10): the separate, reproducible adjusted-price condition projection is limited to server-derived selected-date Main Top2. Price triggers require unanimous RSI14, MACD, each full SMA/EMA/WMA stack, Bollinger20/Donchian20 middle, and OBV delta5 direction checks, plus volume ratio20 >= 1.2. Each MA family exposes numeric 20/60/120/200 values and its own stack state. ATR14 and individual HLC3 `peak=true` bins are context only; close location is described against the separate bins, and structure measurements remain separate. Component states replace any score or vote total. The flat-RSI neutral correction is recorded in root `calculationVersion=stock-monitor-indicator-v2`; existing indicator groups retain `TECHNICAL_VERSION=technical-v4`, and schemaVersion 1 shape is unchanged. See [surface-guide.md](surface-guide.md) for formulas, statuses, provenance, and side-effect limits. This is a policy decision, not evidence of empirical validation or reduced errors.

These code, test, and documentation changes are local only. No live host state or Telegram delivery is inferred from repository code or dated history.
## Work Todo Board

## Purpose

이 문서는 `02.Stock_Moniter`의 큰 작업축을 체크 가능한 형태로 모아둔 실행 보드다.

현재 활성 작업은 아래 `TODO2-*` 항목이다. 이전 `TODO-*` 체크리스트는 완료 이력이며 새 구현 지시가 아니다.

## Use Rules

- 체크박스는 큰 작업축 완료 여부만 표시한다.
- 세부 기능을 작은 체크박스로 쪼개지 않는다.
- 새 작업축은 기존 ID와 겹치지 않는 stable ID를 부여한다.
- 완료 판정은 `Done When` 기준을 만족하고, 검증 명령 또는 실제 화면/출력 확인이 끝났을 때만 한다.
- 운영 적용은 별도 승인 전까지 보드 완료 조건이 아니다. 개발 검증과 운영 싱크는 분리한다.

## Current Priority

| Order | Todo ID | Why Now |
| --- | --- | --- |
| 1 | TODO2-WV-FIRST-LOAD | Reduce cold first-entry work while preserving stored-data content and user-triggered detail requests. |
| 2 | TODO2-DATA-FRESHNESS-LIVE | Validate current Toss freshness and capture/health/freshness agreement on representative dates and the operating host. |
| 3 | TODO2-TG-LIVE-DRYRUN | Review paging/retry/outbox behavior; ambiguous-send retry changes await the policy choice. |
| 4 | TODO2-RT-PRUNE | Use the shared operating review to decide whether current evidence should move higher in the first-read path. |
| 5 | TODO2-NI-EVAL | Judge explanation usefulness on real stored samples without converting a small sample into a quality score. |

## Completed Work Record (Historical)

| Work ID | State | Current reference |
| --- | --- | --- |
| `TODO-WV`, `TODO-TG`, `TODO-NI`, `TODO-DATA`, `TODO-OPS`, `TODO-ADMIN`, `TODO-DOC` | Dev-side implementation slices were marked complete by 2026-06-05. This does not establish current host deployment or operating readiness. | [history.md](history.md), [surface-guide.md](surface-guide.md), [market-data-runbook.md](market-data-runbook.md) |

Detailed progress text and repeated verification outputs were removed from this live work board. Use dated history for operational evidence and inspect current source/tests for implementation state.
## Current TODO2 Task Definitions

### [x] TODO2-OPS-REAL: Operating-PC Sync And Real Migration Handoff

Completed on 2026-06-05 as a dev-side sync/readiness preparation. It did not perform an operating-PC migration, scheduler change, Telegram send, or admin process action. See [history.md](history.md#operating-pc-sync-and-readiness-closeout-2026-06-05); that dated result is not current host evidence.
### [ ] TODO2-RT-PRUNE: Realtime-First Public Surface Pruning

**Goal:**
Reorder public `web-view` and Telegram thinking around current observation evidence first, while lowering previous-day/stored/reference/reaction evidence to fallback/detail/review.

**Scope:**

- Use `오늘 볼 것 -> 현재 근거 -> 전일 참고 -> 부족한 근거 -> 복기/연구` as the shared ordering contract.
- Keep top-2 candidate identity, same-day saved news, current quote/turnover evidence, and source checked time in the first-read path when available.
- Keep KRX daily and `[12009]` rows only for historical review. Current market cards use Toss 20:00 stored context; any bounded intraday Toss reference remains separately source-labelled.
- Maintain the public boundary: no scores, grades, generic buy/sell calls, entry/exit price advice, take-profit/target-return/conviction, broker execution, or order routing. The sole wording exception is the exact separate Main Top2 threshold-condition status contract approved 2026-10-09 and documented in [surface-guide.md](surface-guide.md).
- Reuse the checklist in `docs/codex/surface-guide.md` when judging live operating stability; it does not block local fixes or focused tests.
- Use the daily read-only routine in that plan; do not treat one clean preview or smoke run as completion.

**Done When:**

- Focused local changes have representative-date evidence and targeted tests; the shared operating review log is used to decide whether a changed first-read order is stable in operation.
- Each review row records the command evidence used for the check, including any command that could not run and its read-only substitute.
- Telegram no-send previews read in the new order and still pass public-safe wording checks.
- A reviewer can identify the top-2 candidate, current evidence, and gaps at a glance; “about 10 seconds” is a usability prompt, not a timed pass/fail gate.
- Stale KRX/flow/ETF and reaction/backtest evidence no longer dominate the first-read path.
- No production DB write, scheduler change, Telegram real send, admin-gui process action, or broker/order route is added for this TODO.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-WV-FIRST-LOAD: Web-View First-Entry Performance

**Goal:**
Make the first stored-data view responsive without changing candidate ordering, market data, or public API boundaries.

**Implementation update (2026-09-30):** Recent Toss-market and investor-flow dates now use bounded per-source queries, and the daily snapshot reuses its already loaded Toss date. Missing market context no longer auto-opens the ETF reference details. On the same local 2026-09-29 data, the direct daily-snapshot builder profile went from 6.36s before the change to 1.16s after restart (5.20s / 82% lower). The latest 2026-09-30 builder took 0.89–0.91s across three unprofiled reads. Market dates matched the old UNION query for limits 1, 3, 5, and 20; flow dates matched at limits 1, 3, and 5 for both sources. The service restarted and `/health` returned `200 ok`. Authenticated HTTP timing remains pending: direct API access returned `401` at the access-code gate, and the existing cold-miss logs (4.48–21.92s) do not identify request origin.

**Done When:**

- A fresh browser entry preserves archive, daily, Top2, and missing-state values while optional ETF/rotation requests remain tied to user expansion.
- The bounded Top2 current-quote GET after a cohort change is measured separately; it does not persist values or change candidate membership/order. Top2 candles and Top20 market context remain explicit user actions.
- Cold and warm `/api/archive` and `/api/daily/{date}` timings from the updated local web-view confirm the improvement without errors or automatic optional ETF/rotation requests.
- Existing GET-only and public-safe boundaries remain intact.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/data-governance.md`

### [ ] TODO2-TG-LIVE-DRYRUN: Telegram Real-Data No-Send Dry Run

**Implementation update (2026-10-01, working-tree only):** Regular and hourly Telegram send failures now produce a nonzero CLI result; empty-alert failures write a failed `delivery_log` row and `intraday/empty-send` operation event; operator health surfaces the latest intraday send status. Ten focused tests passed. No real Telegram send, scheduler change, operating-DB write, deployment, or ambiguous-response retry change was made. The accepted-send/lost-response policy below remains pending.

**Goal:**
Use operating-like stored data to prove Telegram briefing payload quality, paging, retry, and outbox/readiness behavior before any real Telegram send is approved.

**Scope:**

- Run market briefing preview for the key slots against representative recent stored data.
- Compare text and JSON payloads for public-safe wording and evidence coverage.
- Check paging, retry, and outbox/readiness behavior through read-only or no-send paths.
- Simulate a send accepted with a lost response and decide whether ambiguous fragments are held for operator review or resent at-least-once.
- Blocking decision before retry changes: choose between duplicate-avoidance (`unknown`/operator review) and at-least-once resend for ambiguous outcomes.
- Confirm Naver/Toss freshness and ETF/flow coverage are accurate; label legacy KRX explicitly historical and X as lab.
- Keep Telegram real send disabled until a separate explicit approval.

**Done When:**

- Mood/lunch/preclose previews render in the realtime-first order: `오늘 볼 것`, `현재 근거`, `전일 참고`, `부족한 근거`, `복기/연구`.
- Recent-data previews have no generic public trading call, numeric score, broker, or order-routing wording; the separate all-confirmation Main Top2 condition statuses approved 2026-10-09 and clarified 2026-10-10 are governed by [surface-guide.md](surface-guide.md).
- Outbox/readiness state can be reviewed without sending.
- Retry/paging behavior has focused test or CLI evidence.
- The selected ambiguous-send policy has a fixture test; do not claim exactly-once delivery from local retry state alone.
- Missing/stale source states are visible in the message instead of hidden.
- No-send preview quality is verified on representative stored dates. The shared operating log informs a later live-send proposal; it does not itself authorize sending.

**Start By Reading:**

- `docs/codex/operating-guide.md`
- `docs/codex/data-governance.md`
- `docs/codex/surface-guide.md`
- `docs/codex/news-intelligence.md`

### [x] TODO2-WV-CONTENT-QA: Web-View Recent-Date Content QA

**Goal:**
Move beyond fixture smoke and verify that recent-date web-view content is usable, scan-friendly, and public-safe across desktop, tablet, and mobile.

**Completed (2026-09-28):** `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json` scanned 2026-09-28, 2026-09-23, 2026-09-22, and 2026-09-21 with 0 issues; its one warning was the expected not-yet-due 2026-09-28 Toss 20:00 capture. Browser smoke passed for 2026-09-21, 22, 23, and latest 2026-09-28: 0 issues, correct five-tab flow, no horizontal overflow at desktop/tablet/large-mobile/mobile, GET APIs 200, POST 405, and `/api/status` 404. Manual first-read review of 9/21–23 found candidate reasons, evidence, missing states, and source/date labels understandable; no content fix was evidenced. The internal sort field remained absent and candidate order unchanged.

**Current navigation note (2026-10-01):** The current implementation has three top-level tabs (`메인`, `관찰`, `종목`); market and rotation/ETF references are nested or collapsed panels. The five-tab wording above remains the dated 2026-09-28 smoke record, not current navigation.

**Scope:**

- Select several recent business dates from stored data.
- Run value QA and browser smoke for daily, watchlist/candidate, stock detail, market, and ETF rotation surfaces.
- Review empty states, stale source indicators, search behavior, and candidate/news evidence labels.
- Confirm public DTOs do not expose raw sentiment, internal recommendation payloads, numeric scores, buy/sell calls, broker execution, or order-routing language; reconcile documented `rank_reference` with the current public projection.
- Recursively check candidate and daily JSON payloads for `sort_value_signal` and any Toss-backed fields still labeled `krx_reference_date` / `value_context.krx`; keep internal selection order unchanged.
- Capture any content-quality defects as concrete follow-up items instead of broad redesign work.

**Done When:**

- Multiple representative recent dates have CLI/browser evidence and first-read usefulness is recorded. The shared operating log is reused rather than requiring a separate 10-day sample for every TODO.
- Desktop/tablet/mobile smoke finds no blocking overlap or broken navigation.
- Public-safe wording scan passes.
- Internal numeric sort fields are absent, Toss-backed values use accurate source/date labels, and internal candidate order is unchanged.
- Empty/low-evidence states are understandable without operator context.
- Remaining defects are listed with date, surface, symptom, and suggested fix.

**Start By Reading:**

- `docs/codex/surface-guide.md`
- `docs/codex/operating-guide.md`
- `docs/codex/candidate-evidence.md`
- `docs/codex/news-intelligence.md`

### [ ] TODO2-DATA-FRESHNESS-LIVE: Live Source Freshness Verification

**Goal:**
Validate current Toss freshness and stored ETF/flow coverage on representative dates; label historical KRX and X/lab data separately.

**Implementation update (2026-09-28):** local capture coverage, metadata classification, snapshot-date ownership, and operator-health propagation are implemented. Operator status now queries the Toss close task and treats an overdue skipped capture as missing; web-view and market-briefing freshness share partial-capture status and missing domains. A read-only 2026-09-28 sample showed reports exact for 9/28, Toss market stale at 9/23, ETF missing, and investor flow stale at 9/17 in both stored-data views. The latest stored 9/23 capture event was `completed` with `candidate_missing=0`, so these states reflect age/coverage for the 9/28 candidates rather than a failed 9/23 capture. The no-send market-briefing preview separately labeled its Top2 Toss quote current at 08:49; web-view remained stored-only (`configured`, no live fetch). At 09:01, the Toss close task was healthy and capture was pending before 20:05. This TODO remains open until after-close capture evidence and additional operating dates are checked.

**Scope:**

- Re-run `data-source-lane-audit --json` and compare with web-view/Telegram freshness output.
- Verify that Toss capture completeness and the date used by the web-view agree; candidate-only rows must not advance the market snapshot date.
- Check that KOSPI/KOSDAQ indices, market flow, Top20 stock/ETF classification, and quote/flow references for all valid daily-summary close-reassessment candidates have explicit missing-state coverage; the public priority projection remains Top2.
- Carry incomplete `stock_metadata_available` and source component gaps into `partial` capture status instead of classifying unknown securities as stocks.
- Confirm `operator-status`/health surfaces failed or partial `poll-news` and `toss-market-context` events after their due windows.
- Keep KRX latest-date/publication rules only for historical analysis and recovery; do not use KRX as a current-view fallback.
- Verify ETF/index data presence and keep ETF constituents marked clearly when not loaded.
- Treat the promoted bounded Toss Top2/Top20 projection as `production_limited`; keep account/order, broad polling, and other Toss endpoints on hold, and keep X as lab.
- Document source-specific stale/missing cases with commands and observed dates.

**Done When:**

- Source lanes remain classified as production, production_limited, lab, or hold.
- Freshness output is consistent across CLI, web-view, and Telegram preview.
- Partial Toss capture does not appear as a complete current snapshot or a clean operator-health state.
- Historical KRX/flow data is explicitly historical-only. Missing or stale Toss data remains visible and is never filled from KRX.
- ETF constituent absence is explicit and not presented as loaded coverage.
- Promoted Toss projections may serve the bounded public GET-only `web-view` route and approved market-briefing context only; they do not connect to `admin-gui`, account/order endpoints, broad polling, or unapproved DB writes. X remains disconnected from production runtime paths.
- Any source gap has a dated evidence note and next action.

**Start By Reading:**

- `docs/codex/data-governance.md`
- `docs/codex/market-data-runbook.md`
- `docs/codex/toss-openapi-lab.md`

### [ ] TODO2-NI-EVAL: News Evidence Quality Evaluation

**Goal:**
Evaluate whether the news-intelligence evidence layer is useful on real samples, not only structurally present.

**Scope:**

- Sample recent dates and mentioned stocks with stored observations.
- Review candidate linkage labels, source modes, direct/caution/market-context separation, and stale or mislabeled source cues.
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
- `tests/test_admin_gui.py`
- `tests/test_operator_status.py`

## Lab Branches To Keep Separate

| Branch / Lane | Todo Link | Current Rule |
| --- | --- | --- |
| `toss-openapi-readonly-lab` | `TODO-DATA` | Applies to account/order and other unapproved Toss endpoints. The approved bounded 20:00/Top2/Top20 lanes follow [market-data-runbook.md](market-data-runbook.md). |
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
