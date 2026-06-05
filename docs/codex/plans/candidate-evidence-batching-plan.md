# Candidate Evidence Batching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `web-view` observation candidate latency by batching stored-data lookups inside `build_web_view_candidate_evidence_snapshot` without changing public wording, trading boundaries, or KRX ingest scope.

**Architecture:** Keep the public DTO shape stable around `rows`, `why_notable`, `missing_information`, and non-numeric `observation_priority`. Add an internal per-date candidate context that preloads report intensity, target revision, same-date flow, flow windows, price/volume history, target-progress baseline rows, and validation market series for all candidate stock codes. Existing single-stock helper logic remains the formatting/reference contract, but candidate snapshot construction should read from the preloaded context instead of opening repeated per-stock queries.

**Tech Stack:** Python, SQLite repository access, pytest, existing `stock_monitor.cli` web-view DTO builders.

---

## Scope

In scope:

- Optimize stored read-only candidate evidence generation.
- Keep `web-view` GET-only/read-only.
- Keep `rows` as the canonical candidate-evidence response key.
- Keep `admin-gui`, secrets, DB path, scheduler state, and operator-only data out of `web-view`.
- Preserve observation wording and block public score/grade/trading-call wording.

Out of scope:

- No KRX network calls.
- No broad ingest or all-stock collection.
- No `[12008]`/`[12010]` automation.
- No Telegram or scheduler changes.
- No public numeric score, grade, buy/sell, entry/exit, take-profit, target-return, or conviction copy.

## Files

- Modify: `src/stock_monitor/cli.py`
  - Add internal candidate evidence batching helpers.
  - Update `build_web_view_candidate_evidence_snapshot` to use the preloaded context.
- Modify: `tests/test_web_view.py`
  - Add a regression test that counts repository connection openings while building candidate evidence for multiple stocks.
  - Preserve existing public DTO assertions.
- Modify: `docs/codex/current-work.md`
  - Record the batching result and measured mini PC impact.
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`
  - Add the source-sync note for the batching pass.

## Tasks

### Task 1: Add RED Query-Budget Test

**Files:**

- Modify: `tests/test_web_view.py`

- [x] **Step 1: Write the failing test**

Add a focused test near the candidate-evidence tests:

```python
def test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    reports = []
    market_rows = []
    flow_rows = []
    for index, code in enumerate(("005930", "000660", "035420"), start=1):
        stock_name = f"테스트{index}"
        reports.append(Report(... two same-date reports with target_price_value ...))
        market_rows.append(StockMarketDailySnapshot(... business_date=business_date, stock_code=code ...))
        flow_rows.append(StockInvestorFlowDaily(... business_date=business_date, stock_code=code, investor_type="외국인" ...))
    repository.insert_reports(reports)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(market_rows)
    repository.upsert_stock_investor_flow_daily(flow_rows)
    connect_count = 0
    original_connect = repository.connect

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(repository, "connect", counting_connect)
    payload = cli_module.build_web_view_candidate_evidence_snapshot(config, repository, business_date=business_date, limit=3)

    assert [row["stock_code"] for row in payload["rows"]] == ["005930", "000660", "035420"]
    assert connect_count <= 14
```

Use real model constructors already imported in the file. The current implementation should exceed the budget because it repeatedly opens connections per stock.

- [x] **Step 2: Run the RED test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py::test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks -q
```

Expected: fail on `connect_count <= 14`.

### Task 2: Add Candidate Evidence Batch Context

**Files:**

- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Add internal helper functions**

Add helpers that load grouped stored data:

```python
def _build_candidate_evidence_batch_context(repository, *, business_date, summaries, holiday_overrides):
    stock_codes = [summary.stock_code for summary in summaries if summary.stock_code]
    return {
        "same_day_flow_by_code": _load_candidate_same_day_flow_by_code(repository, business_date, stock_codes),
        "flow_window_rows_by_code": _load_candidate_flow_window_rows_by_code(repository, business_date, stock_codes),
        "market_history_by_code": _load_candidate_market_history_by_code(repository, business_date, stock_codes),
        "first_target_date_by_code": _load_candidate_first_target_dates_by_code(repository, business_date, stock_codes),
        "previous_target_by_code": _load_candidate_previous_target_by_code(repository, business_date, stock_codes),
        "report_intensity_by_code": _load_candidate_report_intensity_by_code(repository, business_date, summaries, holiday_overrides),
    }
```

Keep helper names internal and local to `cli.py` because this is a web-view DTO optimization, not a repository-wide contract yet.

- [x] **Step 2: Add cached variants of existing single-stock computations**

Add variants that accept preloaded rows:

```python
def _web_view_stock_flow_window_item_from_rows(summary, *, business_date, rows):
    ...

def _web_view_price_volume_position_item_from_rows(summary, *, rows):
    ...

def _web_view_target_price_progress_from_context(summary, market_reference, *, baseline_date, baseline_market, market_series):
    ...
```

Keep output dictionaries byte-for-byte compatible with the existing helper outputs where possible.

### Task 3: Wire Builder To Context

**Files:**

- Modify: `src/stock_monitor/cli.py`

- [x] **Step 1: Build context once**

Inside `build_web_view_candidate_evidence_snapshot`, after `market_refs` and rank rows are prepared, build the batch context once for all summaries.

- [x] **Step 2: Replace per-stock reads**

For each summary:

- use `same_day_flow_by_code[stock_code]` instead of `repository.list_stock_investor_flow_daily(...)`
- use cached report intensity and target revision
- use cached flow window rows for `flow_window_reference`
- use cached market history rows for price/volume reference
- use cached baseline date/baseline market/market series for target progress

- [x] **Step 3: Preserve public DTO**

Keep these fields stable:

- `rows`
- `observation_priority`
- `why_notable`
- `missing_information`
- `report_summary`
- `target_price_progress`
- `flow_window_reference`
- `price_volume_reference`

Do not restore the removed `candidates` duplicate response key.

### Task 4: Verify And Document

**Files:**

- Modify: `docs/codex/current-work.md`
- Modify: `handoff/mini_pc_changes/mini-pc-sync-2026-05-18-web-view-ia-performance.md`

- [x] **Step 1: Run focused tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py::test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks tests\test_web_view.py::test_web_view_candidate_evidence_marks_missing_information_without_public_score tests\test_web_view.py::test_web_view_server_serves_get_only_archive -q
```

Expected: all pass.

- [x] **Step 2: Run relevant regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_web_view.py tests\test_cli_commands.py -q
```

Expected: all pass.

- [x] **Step 3: Run QA/smoke**

```powershell
.venv\Scripts\python.exe -m stock_monitor web-view-value-qa --recent-business-days 4 --stock-limit 20 --json
.venv\Scripts\python.exe -m stock_monitor web-view-browser-smoke --date latest --json
```

Expected: `issue_count=0`.

- [x] **Step 4: Measure**

Run a local timing probe for latest report date and record:

- candidate evidence bytes
- candidate evidence elapsed time
- daily payload elapsed time if affected

- [x] **Step 5: Restart runtime**

Restart only the local `web-view` runtime on `{LOCAL_WEB_VIEW_TARGET}`, then verify:

```powershell
Invoke-WebRequest -UseBasicParsing {LOCAL_WEB_VIEW_TARGET}/health
.venv\Scripts\python.exe -m stock_monitor external-web-view-smoke --url https://web-view.example.invalid --date 2026-05-15 --json
```

Expected: local health `200`, external smoke `issue_count=0`.

## Self-Review

- No new public trading language is introduced.
- No network collection path is changed.
- No scheduler or Telegram path is changed.
- The plan is a single implementation unit: candidate-evidence read performance.
- The test proves behavior through real repository calls and should fail before batching.

## Result

- RED result before implementation: `connect_count == 33`, above the query budget.
- GREEN result after implementation: `test_web_view_candidate_evidence_batches_stored_context_for_multiple_stocks` passed and the full relevant regression passed with `278 passed`.
- Latest mini PC measurement for `2026-05-15`: daily payload about `49KB` / `1.1s`, `candidate-evidence?limit=20` about `95KB` / `0.3s`.
- `web-view-value-qa --recent-business-days 4 --stock-limit 20 --json`: `issue_count=0`; warnings were expected stored-data coverage notes for `2026-05-18` KRX snapshot availability and stock code `351020` KRX metadata.
- `web-view-browser-smoke --date latest --json`: `issue_count=0` across desktop, tablet, large mobile, and mobile.
- Local runtime was restarted on `{LOCAL_WEB_VIEW_TARGET}` with PID `9016`; `/health` returned `200`.
- `external-web-view-smoke --url https://web-view.example.invalid --date 2026-05-15 --json`: `issue_count=0`.
