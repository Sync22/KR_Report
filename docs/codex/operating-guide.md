# Operating Guide

Current operating state, delivery sequence, roadmap, and work board.

## Included sections
- Current Work
- Work Todo Board
- Historical completion index

<!-- Merged from: docs/codex/operating-guide.md -->
## Current Work

### Snapshot (2026-09-28)

The repository is in live-market validation and operational hardening, not initial MVP construction. This is repository-level status only; current main-PC/mini-PC scheduler registration, database freshness, and delivery are not verified here.

Current contracts describe Naver report collection and summaries, Telegram paging/commands, operator-only `admin-gui`, GET-only stored-data `web-view`, and Toss 20:00 as the current stored web-view market/ETF/flow baseline. Existing KRX rows are historical analysis/recovery data only. See [AGENTS.md](../../AGENTS.md), [surface-guide.md](surface-guide.md), [data-governance.md](data-governance.md), [market-data-runbook.md](market-data-runbook.md), and [mini-pc-runbook.md](mini-pc-runbook.md).

### Local implementation status (2026-09-28)

1. Candidate and nested daily DTOs now strip the internal numeric sort field and identify Toss-backed dates/scope as Toss. Representative-date content and responsive UI QA remain in `TODO2-WV-CONTENT-QA`.
2. Local Toss capture now reports required-domain coverage, marks incomplete capture events partial/empty, preserves explicit security classification, derives snapshot dates without candidate-only quotes, exposes partial state in GET market freshness, and warns on failed/partial events or missing due events when a healthy Toss task is registered on a non-suppressed business day. Fixture verification is in progress; real host/date validation remains in `TODO2-DATA-FRESHNESS-LIVE`.
3. Telegram retry behavior still needs an explicit policy for an accepted send with a lost response; tracked in `TODO2-TG-LIVE-DRYRUN`.

These are review findings and planned work, not implementation authorization. No live host state is inferred from repository code or dated history.
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
| 1 | TODO2-WV-CONTENT-QA | Close the public DTO numeric-sort leak, then review recent-date content on representative desktop/mobile views. |
| 2 | TODO2-DATA-FRESHNESS-LIVE | Align Toss capture completeness, authoritative snapshot date, operator health, and freshness labels. |
| 3 | TODO2-TG-LIVE-DRYRUN | Review paging/retry/outbox behavior, including ambiguous send outcomes, in no-send/fake-transport paths. |
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
- Maintain the public boundary: no scores, grades, buy/sell calls, entry/exit/take-profit/target-return/conviction, broker execution, or order routing.
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

### [ ] TODO2-TG-LIVE-DRYRUN: Telegram Real-Data No-Send Dry Run

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
- Recent-data previews have no public trading call, numeric score, buy/sell signal, broker, or order-routing wording.
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

### [ ] TODO2-WV-CONTENT-QA: Web-View Recent-Date Content QA

**Goal:**
Move beyond fixture smoke and verify that recent-date web-view content is usable, scan-friendly, and public-safe across desktop, tablet, and mobile.

**Implementation update (2026-09-28):** public candidate and nested daily DTOs strip `sort_value_signal`; current stored value context uses Toss source/date labels. The task stays open for representative-date and responsive content QA.

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

**Implementation update (2026-09-28):** local capture coverage, metadata classification, snapshot-date ownership, and operator-health propagation are implemented. This TODO remains open until representative stored dates and actual operating-host events are checked.

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
