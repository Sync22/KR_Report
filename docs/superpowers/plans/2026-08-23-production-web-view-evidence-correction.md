# Production Web-View Evidence Correction Plan

> Execute with `superpowers:test-driven-development` and verify with the existing web-view QA commands. No new schema, source, dependency, score, or recommendation.

**Goal:** Correct source semantics, remove repeated evidence, and make the stock detail read as a dated evidence ledger using data already present in the public DTOs.

**Authority:** `docs/superpowers/specs/2026-08-09-web-view-evidence-composition-design.md`, project `AGENTS.md`, and the 2026-08-23 production inspection of `https://report.kr-stock.site/`.

## Task 1: Lock the source/date contract with failing tests

**Files:**
- Modify: `tests/test_web_view.py`
- Test: `tests/test_web_view.py`

1. Change candidate-profile expectations from KRX to Toss stored data, including each row's actual `fetched_at`, because the queried snapshots use `source="toss_openapi"`.
2. Change HTML expectations so general market, ETF, and stock-detail labels identify Toss stored data; reserve `Toss 20:00` for the dedicated close baseline only.
3. Add expectations that collected-but-unmatched news is not rendered as current evidence and the stock context exposes one `근거 원장`.
4. Run the focused tests and confirm they fail for the intended old behavior.

## Task 2: Apply the minimum production correction

**Files:**
- Modify: `src/stock_monitor/cli.py`

1. Replace public KRX labels attached to Toss-backed stock/market/ETF data.
2. Replace the impossible public instruction to save news evidence from the GET-only web-view.
3. Render candidate news as current evidence only when direct, caution, or market-context counts are non-zero; treat a completed zero-match collection as a gap.
4. Filter the main news list to actionable candidate rows so zero-match candidates are summarized once.
5. Rename the selected-stock observation block to `근거 원장`, remove the duplicated status label, and label report/news/current/stored evidence roles.
6. Keep one target history list with hit/progress information; remove the second repeated target row list while retaining the current attainment summary.

## Task 3: Verify behavior and production-shaped rendering

**Files:**
- Modify only if a regression is exposed: `src/stock_monitor/cli_web_view_checks.py`

1. Run focused tests: `python -m pytest tests/test_web_view.py -q`.
2. Run `python -m stock_monitor web-view-value-qa --recent-business-days 1 --json`.
3. Run `python -m stock_monitor web-view-browser-smoke --viewports desktop,tablet,mobile --json`.
4. Run the existing external read-only smoke against the production URL if its command accepts the current access-code configuration; never print the code or cookies.
5. Ask agents to review source semantics, public-boundary safety, and over-engineering; apply only evidence-backed findings.
