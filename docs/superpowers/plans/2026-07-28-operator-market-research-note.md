# Operator Market Research Note Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one operator-only, read-only daily market-research note that places the existing realtime-first candidate snapshot beside an explicitly supplied market-flow result.

**Architecture:** Add a small pure-Python formatter that consumes already-produced JSON documents: a realtime-first snapshot and, optionally, a news-flow source-probe result. A CLI wrapper validates those inputs and writes JSON/Markdown review artifacts under `data/reviews/market-research`; it never fetches, writes SQLite, sends Telegram, registers a scheduler, or exposes a web route.

**Tech Stack:** Python 3.10 standard library, existing `stock_monitor` CLI, pytest.

## Global Constraints

- `admin-gui` stays operator-only; `web-view` stays GET-only and receives no data or route from this feature.
- No public score, grade, buy/sell wording, entry/exit wording, broker behavior, or automatic candidate re-ranking.
- Inputs are existing local JSON artifacts only. This command must not fetch a provider or invoke Scrapling.
- Output is an operator review artifact only; it must not write SQLite, Telegram, or public-view data. It may run as the local-only follow-up inside the existing 15:15 `MarketBriefingPreclose` scheduler task; do not create another scheduler task.
- Preserve missing and stale evidence as missing/stale. Do not treat it as negative market evidence.
- A realtime snapshot generated later than its requested slot is labelled `invalid_for_slot`; it remains readable but is not a comparable 15:00 observation.

---

## File Structure

- Create: `src/stock_monitor/market_research.py` — input validation, slot-validity classification, and JSON/Markdown note construction.
- Modify: `src/stock_monitor/cli.py` — `market-research-note` parser and read-only artifact wrapper.
- Create: `tests/test_market_research.py` — pure builder and boundary tests.
- Modify: `tests/test_cli_commands.py` — parser and artifact-write contract tests.
- Modify: `docs/codex/news-intelligence.md` — document the operator-only local-note boundary and the manual hand-off from `news-flow-source-probe`.
- Modify: `docs/codex/operating-guide.md` — add the daily manual operating command and its interpretation rule.

### Task 1: Build the pure local-note contract

**Files:**
- Create: `src/stock_monitor/market_research.py`
- Test: `tests/test_market_research.py`

**Consumes:** A decoded realtime-first snapshot dictionary and an optional decoded `news-flow-source-probe` dictionary.

**Produces:** `build_market_research_note(snapshot, market_flow=None) -> dict[str, object]` and `format_market_research_note_markdown(note) -> str`.

- [ ] **Step 1: Write the failing valid-input test**

```python
def test_build_market_research_note_keeps_candidate_and_market_flow_separate() -> None:
    note = build_market_research_note(_snapshot(), _market_flow())

    assert note["operator_only"] is True
    assert note["writes_db"] is False
    assert note["candidate_evidence"]["top2"][0]["stock_code"] == "005930"
    assert note["market_context"]["status"] == "available"
    assert note["market_context"]["source_urls"] == ["https://stock.naver.com/news/mainnews"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_market_research.py::test_build_market_research_note_keeps_candidate_and_market_flow_separate -q`

Expected: FAIL because `stock_monitor.market_research` does not exist.

- [ ] **Step 3: Add the minimal builder**

```python
def build_market_research_note(
    snapshot: dict[str, object],
    market_flow: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = _require_mapping(snapshot, "metadata")
    return {
        "surface": "market-research-note",
        "operator_only": True,
        "public_safe": False,
        "live_fetch": False,
        "writes_db": False,
        "sends_telegram": False,
        "registers_scheduler": False,
        "connects_web_view": False,
        "snapshot": _snapshot_context(metadata),
        "candidate_evidence": {"top2": _mapping_list(snapshot.get("top2"))},
        "market_context": _market_context(market_flow),
    }
```

`_snapshot_context` must parse `generated_at_kst`, `date`, and `snapshot_time_kst`. It returns `slot_status="valid"` only when the generated KST date equals the target date and the generated time is no later than 15 minutes after the requested slot; otherwise it returns `slot_status="invalid_for_slot"` with the concrete reason `late_generation`, `date_mismatch`, or `invalid_metadata`.

`_market_context(None)` returns `{"status": "not_supplied", "source_urls": [], "summary": None}`. A supplied document is accepted only when `surface == "news-flow-source-probe"` and `operator_only is True`; otherwise raise `ValueError("market flow must be an operator-only news-flow source probe")`.

- [ ] **Step 4: Add the stale/missing and invalid-slot tests**

```python
def test_build_market_research_note_marks_late_snapshot_invalid_for_slot() -> None:
    snapshot = _snapshot(generated_at_kst="2026-07-20T23:09:00+09:00")

    note = build_market_research_note(snapshot)

    assert note["snapshot"]["slot_status"] == "invalid_for_slot"
    assert note["snapshot"]["slot_reason"] == "late_generation"
    assert note["candidate_evidence"]["top2"] == snapshot["top2"]


def test_build_market_research_note_rejects_non_operator_market_flow() -> None:
    with pytest.raises(ValueError, match="operator-only news-flow source probe"):
        build_market_research_note(_snapshot(), {"surface": "other", "operator_only": False})
```

- [ ] **Step 5: Implement the formatter and run the focused tests**

The Markdown formatter must render these headings only: `Snapshot slot`, `Candidate evidence`, `Market context`, and `Boundary`. It must show `not supplied`, `missing`, and `stale` verbatim rather than inventing a market state.

Run: `python -m pytest tests/test_market_research.py -q`

Expected: PASS.

### Task 2: Add the read-only CLI artifact wrapper

**Files:**
- Modify: `src/stock_monitor/cli.py`
- Modify: `tests/test_cli_commands.py`

**Consumes:** `--snapshot PATH` and optional `--market-flow PATH` JSON files.

**Produces:** `data/reviews/market-research/YYYY-MM-DD_1500.json` and `.md`, with paths printed to stdout.

- [ ] **Step 1: Write the failing parser and artifact tests**

```python
def test_market_research_note_parser_requires_snapshot() -> None:
    parser = cli_module.build_parser()
    args = parser.parse_args([
        "market-research-note",
        "--snapshot", "data/reviews/realtime-first/2026-07-28_1500.json",
    ])

    assert args.command == "market-research-note"
    assert args.market_flow is None
    assert args.output_dir == Path("data/reviews/market-research")


def test_market_research_note_writes_only_local_review_artifacts(tmp_path, capsys) -> None:
    exit_code = _run_market_research_note(
        snapshot_path=_write_snapshot(tmp_path),
        market_flow_path=None,
        output_dir=tmp_path / "reviews",
    )

    assert exit_code == 0
    assert (tmp_path / "reviews" / "2026-07-28_1500.json").exists()
    assert "writes_db: false" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cli_commands.py -k market_research_note -q`

Expected: FAIL because the parser and wrapper do not exist.

- [ ] **Step 3: Add the parser and wrapper**

```python
market_research_parser = subparsers.add_parser(
    "market-research-note",
    help="Write an operator-only read-only market research note from local review JSON.",
)
market_research_parser.add_argument("--snapshot", type=Path, required=True)
market_research_parser.add_argument("--market-flow", type=Path)
market_research_parser.add_argument("--output-dir", type=Path, default=Path("data/reviews/market-research"))
```

The wrapper must use `Path.read_text(encoding="utf-8")` and `json.loads`. It must return exit code 1 with a concise error if either input is missing, malformed JSON, or rejected by `build_market_research_note`. It must not initialize a repository, load runtime configuration, or invoke any provider.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_cli_commands.py -k market_research_note -q`

Expected: PASS.

- [ ] **Step 5: Run the existing regression boundary tests**

Run: `python -m pytest tests/test_news_flow_preview.py tests/test_cli_commands.py -k "news_flow or realtime_first or market_research_note" -q`

Expected: PASS.

### Task 3: Document and manually validate the operator workflow

**Files:**
- Modify: `docs/codex/news-intelligence.md`
- Modify: `docs/codex/operating-guide.md`

**Consumes:** Existing realtime-first snapshot JSON and an optional manually captured `news-flow-source-probe --format json` response.

**Produces:** A documented two-command operator workflow with explicit local-only boundary.

- [ ] **Step 1: Add the canonical workflow**

Document these commands, using a date-specific filename:

```powershell
python -m stock_monitor news-flow-source-probe --source-url <approved-naver-url> --date 2026-07-28 --format json > data\reviews\market-research\2026-07-28_flow.json
python -m stock_monitor market-research-note --snapshot data\reviews\realtime-first\2026-07-28_1500.json --market-flow data\reviews\market-research\2026-07-28_flow.json
```

The docs must state that the first command is a manual source probe and the second command performs no live fetch. The artifacts are operator review material only, not a DB source or public projection.

- [ ] **Step 2: Run the manual local-only smoke check**

Run the second command against a fixture-created snapshot and optional fixture-created market-flow JSON. Inspect the generated JSON for:

```json
{
  "operator_only": true,
  "public_safe": false,
  "live_fetch": false,
  "writes_db": false,
  "sends_telegram": false,
  "registers_scheduler": false,
  "connects_web_view": false
}
```

- [ ] **Step 3: Run the full focused verification set**

Run:

```powershell
python -m pytest tests/test_market_research.py tests/test_news_flow_preview.py tests/test_cli_commands.py -k "market_research_note or news_flow or realtime_first" -q
git diff --check
```

Expected: tests pass and `git diff --check` has no output.

- [ ] **Step 4: Commit the focused change**

```powershell
git add src/stock_monitor/market_research.py src/stock_monitor/cli.py tests/test_market_research.py tests/test_cli_commands.py docs/codex/news-intelligence.md docs/codex/operating-guide.md
git commit -m "feat: add read-only market research note"
```

## Self-Review

- Spec coverage: Tasks 1-2 provide the separate market-context artifact and enforce its operator-only/read-only contract. Task 3 documents the manual source-probe hand-off and validates that no production surface receives it.
- Scope: no new data source, DB schema, scheduler task, Telegram path, candidate-rank mutation, or web route is introduced.
- Consistency: the CLI reads only local JSON; `news-flow-source-probe` remains the separately initiated source-probe command.
- No placeholders: all task interfaces, output path, failure behavior, and test commands are explicit.

## Approved Scheduler Extension

The operator approved concurrent operating validation after this plan was written. `run_scheduled_market_briefing_slot.ps1` now runs the existing preclose briefing first, then writes a `15:15` realtime-first snapshot and `market-research-note` from that local snapshot. The original independent `15:00` snapshot remains unchanged. This extension does not add a scheduler task, live fetch to the note command, SQLite writes, Telegram sends, or public-surface integration.
