# Web-View Evidence Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove live/stored ambiguity, save Toss close evidence for the full daily candidate universe, add source-consistent market-relative event reactions, and distinguish independent news candidates from report recaps.

**Status:** Implemented and verified on the development PC on 2026-08-23. The checkboxes below preserve the original execution sequence rather than acting as current progress state.

**Architecture:** Keep the public web-view GET-only and stored-data-first. Reuse the existing Toss quote/baseline, stock-flow, KRX historical, candidate-evidence, and linked-news paths; add no new runtime dependency or public score. Live Toss reads remain non-persistent references, while stored evidence and historical reaction calculations carry explicit source/date metadata.

**Tech Stack:** Python 3.10, SQLite, existing Toss OpenAPI client, existing HTML/JavaScript web-view, pytest.

**Spec:** `docs/codex/data-governance.md`, `docs/codex/candidate-evidence.md`, `docs/codex/news-intelligence.md`, and the approved 2026-08-23 goal sequence.

## Global Constraints

- Development PC only; do not deploy or alter the operating PC.
- `admin-gui` remains operator-only and `web-view` remains friend-facing GET-only.
- No public numeric score, investment grade, buy/sell wording, broker execution, or order routing.
- Toss stored rows own current market/stock references; KRX rows may be used only for explicitly labelled historical review.
- Live Toss quote/investor reads never affect candidate ordering and are never presented as stored evidence.
- Insane Search remains a positive conditional lab tool; operating-PC setup requires the audit gate in Task 4 and a separate decision.
- Do not add a dependency, new service, or new table where existing helpers/tables carry the required contract.

---

### Task 1: Separate Live Toss References From Stored Evidence

**Files:**
- Modify: `tests/test_web_view.py`
- Modify: `src/stock_monitor/cli.py`

**Interfaces:**
- Consumes: existing `/api/toss-priority-quotes`, `data_scope=web_view_priority_top_2_prices`, and stored stock-detail DTO.
- Produces: unambiguous public copy; no DTO or database change.

- [ ] **Step 1: Write failing HTML contract test**

```python
def test_web_view_html_labels_top_two_toss_flow_as_unstored_query_reference() -> None:
    html = cli_module._web_view_html()
    top_two = html.split("function renderTopTwoReviewCandidates(rows)", 1)[1]
    assert "Toss 조회 수급 참고(미저장)" in top_two
    assert "Toss 당일 수급" not in top_two
    assert "data-toss-investor-trading" in top_two
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest tests/test_web_view.py::test_web_view_html_labels_top_two_toss_flow_as_unstored_query_reference -q`

Expected: FAIL because the HTML still says `Toss 당일 수급`.

- [ ] **Step 3: Write failing stored-detail contract test**

```python
def test_web_view_stock_detail_missing_toss_flow_names_selected_date_stored_scope(tmp_path) -> None:
    config, repository = _config_and_repository(tmp_path)
    payload = cli_module.build_web_view_stock_detail_snapshot(
        config, repository, business_date=date(2026, 8, 21), stock_code="388210"
    )
    assert payload["investor_flow"]["data_scope"] == "stored_toss_close_priority_flow"
    assert payload["investor_flow"]["live_fetch"] is False
    assert "선택일 Toss 20:00 저장" in payload["investor_flow"]["notice"]
```

- [ ] **Step 4: Apply the minimum copy change**

Change only the Top2 live label/status strings and the stored-detail empty notices. Keep provider, route, caching, ordering, and source selection unchanged.

```javascript
<strong>Toss 조회 수급 참고(미저장):</strong>
```

```python
"선택일 Toss 20:00 저장 우선 후보 수급 데이터가 없습니다."
```

- [ ] **Step 5: Run GREEN tests**

Run: `python -m pytest tests/test_web_view.py -q`

Expected: all web-view tests pass.

---

### Task 2: Persist Toss Evidence For The Full Daily Candidate Universe

**Files:**
- Modify: `tests/test_cli_commands.py`
- Modify: `tests/test_web_view.py`
- Modify: `src/stock_monitor/cli.py`
- Modify: `docs/codex/toss-openapi-lab.md`

**Interfaces:**
- Consumes: `_candidate_evidence_stock_codes()`, `DailyStockSummary`, `TossPriorityQuoteProvider.get_quotes()`, `toss_priority_quote_baselines`, `stock_market_daily`, `stock_investor_flow_daily`, and `operation_events`.
- Produces: selected-date stored close baseline and investor flow for every valid six-digit code in that date's daily summaries; explicit target/saved/missing counts.

- [ ] **Step 1: Write failing full-cohort capture test**

Create three daily summaries where only two rank in the old Top2. Inject a fake provider which records every quote request and returns quotes/investor flow for all requested symbols.

```python
def test_toss_market_context_capture_persists_every_daily_summary_candidate(tmp_path, capsys) -> None:
    # seed 3 summaries and run _run_toss_market_context_capture(... fake provider ...)
    assert requested_symbols == {"005930", "000660", "035420"}
    assert {row.stock_code for row in repository.list_toss_priority_quote_baselines(...)} == requested_symbols
    assert payload["candidate_target_count"] == 3
    assert payload["candidate_missing_count"] == 0
```

- [ ] **Step 2: Run RED test**

Run: `python -m pytest tests/test_cli_commands.py::test_toss_market_context_capture_persists_every_daily_summary_candidate -q`

Expected: FAIL because capture currently uses `limit=2` and slices Top2.

- [ ] **Step 3: Reuse the canonical full summary cohort**

Replace Top2 candidate extraction in close capture and baseline collect with daily summaries plus `_candidate_evidence_stock_codes()`.

```python
candidate_summaries = repository.list_daily_summaries(business_date)
candidate_symbols = tuple(
    code for code in _candidate_evidence_stock_codes(candidate_summaries)
    if re.fullmatch(r"\d{6}", code)
)
```

Keep `market_context_priority_symbols = candidate_symbols[:2]` only for the existing Top2 market-context call.

- [ ] **Step 4: Fetch candidate quotes in endpoint-sized batches**

Reuse `provider.get_quotes()` and aggregate existing payload fields. Do not add a batching abstraction.

```python
quote_payloads = [
    provider.get_quotes(
        priority_date=business_date,
        symbols=candidate_symbols[start:start + 2],
        include_investor_trading=True,
    )
    for start in range(0, len(candidate_symbols), 2)
]
```

Save baselines and investor-flow rows using existing repository methods. Add sparse `stock_market_daily(source='toss_openapi')` close rows only for candidates not already present in enriched market Top20 rows so volume/turnover cannot be overwritten by `NULL`.

- [ ] **Step 5: Expose partial completeness without a migration**

```python
saved_codes = {row.stock_code for row in baseline_rows}
missing_codes = [code for code in candidate_symbols if code not in saved_codes]
payload.update({
    "candidate_target_count": len(candidate_symbols),
    "candidate_saved_count": len(saved_codes),
    "candidate_missing_count": len(missing_codes),
    "candidate_missing_symbols": missing_codes,
})
```

Scheduled operation status is `completed` only when market snapshots exist and no candidate is missing; otherwise use `partial` or `empty` and record counts in `operation_events.detail`.

- [ ] **Step 6: Write and satisfy candidate DTO source test**

Seed Toss-only close and flow rows and assert `missing_toss_stock_snapshot` and `missing_stock_flow` disappear. Change `_load_candidate_flow_context()` so `same_day_flow_by_code` reads exact-date `source='toss_openapi'`, while `flow_window_rows_by_code` keeps the existing explicitly historical `krx_data_market` window. Do not silently merge the two sources into one metric.

Run:

```powershell
python -m pytest tests/test_cli_commands.py -k "toss_market_context_capture or toss_priority_baseline" -q
python -m pytest tests/test_web_view.py -k "candidate_evidence or toss" -q
```

Expected: all selected tests pass.

---

### Task 3: Add Source-Consistent Market-Relative Event Reaction

**Files:**
- Modify: `tests/test_web_view.py`
- Modify: `src/stock_monitor/cli.py`
- Modify: `docs/codex/candidate-evidence.md`

**Interfaces:**
- Consumes: stored KRX historical stock/index rows, `_web_view_return_percent()`, existing candidate batch context, and stock-detail candidate journey renderer.
- Produces: `candidate_evidence.rows[].event_reaction`, historical-review only, with D0/D+1/D+5/D+20 stock, market, and excess returns.

- [ ] **Step 1: Write failing pure calculation tests**

```python
def test_web_view_event_reaction_calculates_same_source_market_excess() -> None:
    reaction = cli_module._web_view_event_reaction_from_rows(
        event_date=date(2026, 8, 21),
        stock_rows=krx_stock_rows,
        index_rows=krx_kosdaq_rows,
    )
    assert reaction["source"] == "krx"
    assert reaction["items"]["D+1"]["stock_return_percent"] == 10.0
    assert reaction["items"]["D+1"]["market_return_percent"] == 2.0
    assert reaction["items"]["D+1"]["excess_return_percent"] == 8.0
```

Add separate tests for KOSPI/KOSDAQ selection, missing horizon, and source mismatch. A missing benchmark keeps stock return but sets market/excess to `None` with `market_unavailable_reason`; it never assumes zero.

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest tests/test_web_view.py -k "event_reaction" -q`

Expected: FAIL because the helper and DTO do not exist.

- [ ] **Step 3: Implement a small pure helper**

The helper must require identical stock/index `source`, match benchmark rows on the exact stock horizon date, and return only completed horizons.

```python
excess = (
    round(stock_return - market_return, 2)
    if stock_return is not None and market_return is not None
    else None
)
```

Use `KOSPI` for KOSPI-family stock rows and `KOSDAQ` for KOSDAQ-family rows. Label the DTO `historical_review=True`, `affects_ordering=False`, and `source='krx'`.

- [ ] **Step 4: Add event reaction to candidate batch context**

Load KRX index rows once for the event/future window, derive per-candidate reactions from the already loaded KRX stock history, and attach the DTO before row slicing. Do not alter candidate sorting.

- [ ] **Step 5: Render one compact line in the existing stock evidence ledger**

Add no new dashboard/card. `renderStockCandidateJourney()` displays completed values such as:

```text
과거 반응(KRX): D0 -6.7% · 시장대비 -4.6%p / D+1 확인 대기
```

The copy must say `과거 반응(KRX)` and never `전망`, `신호`, or `추천`.

- [ ] **Step 6: Run GREEN tests**

Run: `python -m pytest tests/test_web_view.py -q`

Expected: all web-view tests pass.

---

### Task 4: Classify News Independence And Gate Insane Search Expansion

**Files:**
- Modify: `tests/test_news_linked_evidence.py`
- Modify: `tests/test_repository.py`
- Modify: `tests/test_web_view.py`
- Modify: `src/stock_monitor/news/linked_evidence.py`
- Modify: `src/stock_monitor/models.py`
- Modify: `src/stock_monitor/db/schema.py`
- Modify: `src/stock_monitor/db/repository.py`
- Modify: `src/stock_monitor/cli.py`
- Modify: `docs/codex/news-intelligence.md`

**Interfaces:**
- Consumes: matched article publisher/title/summary/URL, linked-news evidence, existing report-rehash markers, and stored public news projection.
- Produces: persisted `canonical_url`, `lineage_type`, and `lineage_reason`; public labels `독립 근거 후보`, `리포트 파생`, `독립성 미확인`; fail-closed candidate value behavior.

- [ ] **Step 1: Write failing lineage classifier tests**

```python
def test_report_recap_never_strengthens_report_candidate() -> None:
    item = _analyzed("[리포트 브리핑] 삼성전자 목표가 상향", "증권사 리포트 요약", url="https://example.test/a")
    item = replace(item, lineage_type="report_recap", lineage_reason="report_recap_marker")
    row = build_report_linked_news_evidence([item], _context(related_report_count=1))[0]
    assert row.operator_recommendation == "keep_as_report_recap"

def test_unknown_lineage_never_promotes_news_only_candidate() -> None:
    item = replace(_analyzed(...), lineage_type="unknown", lineage_reason="provenance_unverified")
    row = build_report_linked_news_evidence([item], _context())[0]
    assert row.operator_recommendation == "hold_until_independence_verified"
```

Verified `independent` retains the existing direct-positive behavior. `direct` relevance alone is insufficient.

- [ ] **Step 2: Run RED tests**

Run: `python -m pytest tests/test_news_linked_evidence.py -q`

Expected: FAIL because lineage fields and fail-closed branches do not exist.

- [ ] **Step 3: Add the smallest lineage contract**

Extend `ReportLinkedNewsInput`, `ReportLinkedNewsEvidence`, and persisted record with:

```python
canonical_url: str
lineage_type: str  # independent | report_recap | unknown
lineage_reason: str
```

Classification order:

1. Explicit report recap markers → `report_recap`.
2. Explicitly verified provenance supplied by a later audit/import boundary → `independent`.
3. Every automatically collected article without verified upstream provenance → `unknown`, even if it is direct and describes a business event.

The current collector must automatically produce only `report_recap` or `unknown`. It must not infer `independent` from positive wording, event types, publisher name, or lack of recap markers.

`report_recap` and `unknown` return before positive strengthen/promote branches.

- [ ] **Step 4: Persist through schema v10**

Add migration columns with safe defaults:

```sql
ALTER TABLE report_linked_news_evidence ADD COLUMN canonical_url TEXT;
ALTER TABLE report_linked_news_evidence ADD COLUMN lineage_type TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE report_linked_news_evidence ADD COLUMN lineage_reason TEXT NOT NULL DEFAULT 'legacy_row_unverified';
```

Do not infer/backfill old rows as independent. Add repository round-trip and migration tests.

- [ ] **Step 5: Project conservative public labels**

Public news badge/digest may count verified `independent` separately. `report_recap` and `unknown` remain visible context but must not create direct independent counts or strengthen ordering. Render the three labels without exposing operator recommendations.

- [ ] **Step 6: Record the Insane Search operating-PC gate**

Document development-PC audit requirements:

- 20 business days of Top2 plus positive/recap/irrelevant controls.
- Recap-to-independent false promotion: 0.
- Independent precision: at least 95%.
- Verified existing-lane miss recovery: at least 20%.
- Re-run agreement: at least 90%.
- Provenance/trace completeness and production side effects: 100% / 0.

Passing the gate permits only an isolated, read-only lab setup on the operating PC. DB, scheduler, Telegram, candidate ordering, public web-view fetches, and trading behavior remain a separate decision.

- [ ] **Step 7: Run GREEN tests**

Run:

```powershell
python -m pytest tests/test_news_linked_evidence.py tests/test_repository.py -q
python -m pytest tests/test_web_view.py -k "news or candidate" -q
```

Expected: all selected tests pass and legacy rows remain `unknown`.

---

### Task 5: Documentation And Completion Verification

**Files:**
- Modify: `docs/codex/data-governance.md`
- Modify: `docs/codex/candidate-evidence.md`
- Modify: `docs/codex/news-intelligence.md`
- Modify: `docs/codex/toss-openapi-lab.md`

**Interfaces:**
- Consumes: implemented DTO/source contracts and audit gate.
- Produces: canonical documentation and fresh verification evidence.

- [ ] **Step 1: Update canonical contracts**

Document:

- live Toss reference versus selected-date stored evidence labels;
- full daily-summary candidate cohort capture and partial status;
- KRX historical-only event reaction with same-source benchmark;
- news relevance versus independence lineage;
- Insane Search development/operating-PC lab boundary.

- [ ] **Step 2: Run focused verification**

```powershell
python -m py_compile src\stock_monitor\cli.py src\stock_monitor\news\linked_evidence.py src\stock_monitor\db\repository.py
python -m pytest tests\test_web_view.py tests\test_toss_openapi.py tests\test_backtest_observation.py tests\test_news_linked_evidence.py tests\test_repository.py -q
python -m pytest tests\test_cli_commands.py -k "toss_market_context_capture or toss_priority_baseline or news_intelligence" -q
```

- [ ] **Step 3: Run product-surface verification**

```powershell
python -m stock_monitor web-view-value-qa --recent-business-days 5 --json
python -m stock_monitor web-view-browser-smoke --date latest --json
rg -n "매수 추천|매도 추천|진입가|청산가|투자등급|candidate_score" src\stock_monitor\cli.py
```

- [ ] **Step 4: Review the complete diff**

Run:

```powershell
git status --short
git diff --check
git diff --stat
git diff
```

Confirm only planned files changed, no secret/output/database artifact is present, and no deployment or operating-PC state changed.

## Self-Review

- The plan covers all four approved stages in order.
- Task 1 changes meaning, not data behavior.
- Task 2 uses the full summary cohort and existing persistence tables; no new schema is added for capture manifests.
- Task 3 never mixes stock and benchmark sources and does not alter ordering.
- Task 4 treats relevance and independence as separate axes, defaults legacy data to unknown, and does not make Insane Search a production dependency.
- The plan adds no dependency, public score, recommendation, broker action, deployment, or operating-PC mutation.
