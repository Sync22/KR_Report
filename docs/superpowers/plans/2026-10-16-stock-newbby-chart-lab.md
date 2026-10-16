# Stock-Newbby Chart Lab Implementation Plan

> **For agentic workers:** The Chart Lab slice is implemented and verified on the development PC. Remaining limitations are listed in the handoff section; do not mark the broader Stock-Newbby parity goal complete until they are resolved or explicitly accepted.

**Goal:** Port Stock-Newbby's chart review, strategy, structure, pattern-history, monitor, and Codex-assistant workflows into a separate local Chart Lab tab.

**Architecture:** Reuse the existing Chart Explorer provider/data contract and add isolated pure TypeScript engines plus local-only monitor state. Keep the Main Top2 calculator and the operating Stock Monitor SQLite, Python writer, scheduler, Telegram, and order/broker paths untouched.

**Tech Stack:** Next.js App Router, TypeScript, Node.js Route Handlers, native browser SVG/UI, Node test runner, local JSON monitor state.

**Spec:** User request in the 2026-10-16 conversation; upstream references at `https://github.com/gmparkingplace/Stock-Newbby` and `docs/FEATURES.md`.

## Global Constraints

- Chart Lab is a local test surface; mutating controls require a loopback request with same-origin validation.
- Stock Monitor's operating SQLite database remains read-only from Next.js; monitor state is isolated from it.
- Do not connect broker/account/order APIs or automatic execution.
- Preserve source, requested/actual bar time, adjustment, finality, missing data, and historical-versus-current judgment.
- Keep existing Main Top2 rules and output unchanged.
- Retain Apache-2.0 notices for upstream-derived code and identify modified files.

## Review Focus

- Historical calculations must not use future bars; pin with selected-bar cutoff fixtures.
- Incomplete or unknown-finality data must not be reported as confirmed; pin with missing/provisional fixtures.
- 4-hour session gaps and invalid bars must not be treated as continuous; pin with session/gap fixtures.
- Monitor APIs must reject remote, cross-origin, oversized, and malformed mutations; pin with route tests.
- Restarted monitor state must remain isolated from Stock Monitor SQLite and recover from malformed local JSON; pin with store tests.

---

### Task 1: Chart Lab boundary and local monitor storage

**Files:**
- Modify: `AGENTS.md`, `docs/codex/data-governance.md`, `docs/codex/surface-guide.md`, `docs/codex/documentation-index.md`
- Create: `web/src/server/chart-lab-local.ts`, `web/src/server/chart-lab-store.ts`
- Test: `web/test/chart-lab-local.test.mjs`

**Interfaces:**
- `isChartLabLocalRequest(request: Request, mutation?: boolean): boolean`
- `readChartLabState()` / `writeChartLabState(state)` use a separate bounded JSON state file; never open `stock_monitor.db` for writes.

- [x] Write tests for loopback/same-origin checks and safe state read/write behavior.
- [x] Verify RED, then implement the smallest local-only guard and atomic JSON persistence.
- [x] Update canonical docs to distinguish the experimental Chart Lab from public web-view contracts.
- [x] Run focused tests and `git diff --check`.

### Task 2: Strategy and low-structure engines

**Files:**
- Create: `web/src/domain/chart-lab/indicators.ts`, `entry.ts`, `low-structure.ts`, `analysis.ts`
- Test: `web/test/chart-lab-entry.test.mjs`, `web/test/chart-lab-low-structure.test.mjs`
- Reference: upstream `entry-model.js`, `low-structure-rules.js`, `low-structure-model.js`, and their tests.

**Interfaces:**
- `evaluateEntry(frame, options)` returns per-strategy A/B/C/F raw signal, readiness, phase, historical cutoff, and current review state.
- `evaluateLowStructures(bars, options)` returns R/H structure status, evidence bars, invalidation, and expiry without a score or order action.

- [x] Write tests for A/B/C/F signals, three-bar continuation, historical cutoff, R/H confirmation, gaps, and unknown finality.
- [x] Verify RED, port the exact upstream rules with source/version attribution, then verify GREEN.

### Task 3: Pattern and event history

**Files:**
- Create: `web/src/domain/chart-lab/patterns.ts`, `web/src/domain/chart-lab/events.ts`, `web/src/server/chart-lab-monitor.ts`, `web/src/server/chart-lab-store.ts`
- Test: `web/test/chart-lab-patterns.test.mjs`, `web/test/chart-lab-events.test.mjs`, `web/test/chart-lab-monitor.test.mjs`, `web/test/chart-lab-store.test.mjs`
- Reference: upstream pattern math, flag/triangle detectors, and immutable event snapshot contracts.

**Interfaces:**
- `detectChartLabPatterns(bars, timeframe)` returns bounded current/historical flag, triangle, and support/resistance structures with basis indices and rule version.
- `ChartLabMonitorService` appends immutable source-labelled event snapshots when a pattern is first seen or changes state.

- [x] Write fixtures for ascending/descending/symmetrical triangles, flags, S/R events, invalid bars, and historical cutoffs.
- [x] Verify RED, port the applicable calculations, and ensure event data is local Chart Lab state only.

### Task 4: Chart Lab controls and visual projection

**Files:**
- Modify: `web/src/components/client/chart-explorer.tsx`, `web/src/app/globals.css`
- Create if needed: `web/src/components/client/chart-lab-panels.tsx`
- Test: `web/test/chart-explorer.test.mjs` and targeted component/API tests.

- [x] Add selectable strategy family/settings, current versus historical review, pattern history navigation, full moving-average/Bollinger/Donchian overlays, and aligned indicator toggles.
- [x] Keep values, source, actual basis bar, provisional/finality, and missing states visible.
- [x] Verify at desktop and mobile viewport sizes; do not change Main Top2 projection.

### Task 5: Local daily pattern monitor

**Files:**
- Create: `web/src/app/api/chart-lab/analysis/route.ts`, `web/src/app/api/chart-lab/monitor/route.ts`
- Modify: `web/src/components/client/chart-explorer.tsx`, `web/src/components/client/chart-lab-monitor-panel.tsx`
- Test: `web/test/chart-lab-analysis-route.test.mjs`, `web/test/chart-lab-monitor-route.test.mjs`

- [x] Add bounded watch/focus groups (20 symbols / 3 focus symbols), status/start/pause controls, separate regular/focus poll intervals, persisted event history, and failure backoff.
- [x] Verify remote/cross-origin/oversized monitor POST rejection and start/pause behavior against an isolated test store.
- [ ] Compare operating Stock Monitor DB metadata before/after real monitor polling; the monitor was left stopped, so this remains unverified.
- [x] Keep monitor stopped unless explicitly started by the user.

### Task 6: Codex chart-assistant workflow

**Files:**
- Modify: `.agents/skills/chart-assistant/SKILL.md` and its existing helper scripts.
- Test: `.agents/skills/chart-assistant/tests/test_chart_assistant_analysis.py`, `test_chart_assistant_control.py`, and the existing snapshot test.

- [x] Add commands for chart view/inspection, indicators, patterns/events, monitor status/start/pause, and offline R/H review.
- [x] Preserve source/date/finality and historical status in every response; require explicit user intent for start/pause.
- [x] Do not add an LLM API provider, secret, broker, order, or automatic action.

### Task 7: Verification and handoff

**Files:**
- Update canonical docs and `docs/codex/history.md` with confirmed status only.

- [x] Run the focused H4 continuity tests, `npm run typecheck`, `npm run build`, and `git diff --check`.
- [ ] Resolve the five current full-suite Python/Next indicator-parity failures before treating the web suite as green.
- [x] Verify Chart Lab in the 3010 browser, including zoom/pan, historical cutoff, strategy and pattern states, monitor controls, and mobile layout.
- [x] Verify the local H4 API against Samsung Electronics and SK Hynix on the development PC.
- [ ] Compare operating DB metadata before/after monitor use and report any unverified upstream capability explicitly.

## Current Status (2026-10-16)

- Tasks 1–6: implemented on the development PC. The local monitor remains stopped; no monitor start request was sent to the live preview.
- Fresh verification on 2026-10-16: H4-focused tests 21/21 passed, `npm run typecheck`, `npm run build`, and `git diff --check` passed. `npm test` passed 150/150 with the project `.venv` Python 3.12.10 on `PATH`. The machine's unqualified `python` is Python 3.10.11, so invoking the suite without the project venv makes its Python 3.12 exact-float oracle tests fail; use the venv interpreter for repeatable local results.
- The rebuilt Next preview was restarted on the fixed `127.0.0.1:3010` port and returned health 200. Live local H4 GETs for `000660` and `005930`, date `2026-10-08`, both returned 200 with Yahoo 1-hour source, `session_continuity_status=verified`, Toss stock-master mapping, 140/140 recent bars carrying integer `missingBarsBefore`, and six skipped buckets across one positive-gap bar. Both preserve `bar_status=unknown`; R/H remains `unconfirmed` (`자료 확인 필요`). The public `/api/chart-explorer` route still returns `symbol_mapping_unavailable` for the same six-digit/date case, as its selected-date mapping rule requires.
- H4 uses a 120-bar R/H analysis window and recent 140-bar session context. Normal complete KRX hourly days use the fixed regular-session window; Toss KRX calendar reads identify irregular or missing sessions. The calculated gap metadata is local Chart Lab calculation data and is not added to the public chart DTO.
- Remaining upstream mismatch: when Toss is configured, Stock-Newbby uses paginated Toss 1-minute data for H4. This Next Chart Lab still uses Yahoo 1-hour candles; the minute-history cache and collection path are not implemented.
- Not performed: no monitor start or operating-DB metadata comparison. No operating-PC tests, Python DB writes, scheduler, Telegram, or orders were invoked. No commit or push was made.
