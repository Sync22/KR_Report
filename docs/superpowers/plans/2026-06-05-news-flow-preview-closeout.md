# News Flow Preview Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current `news-flow-preview` branch from a working code slice into a documented, fixture-backed, verified, commit-ready feature that can be pushed after explicit user approval.

**Architecture:** Keep `news-flow-preview` as a separate operator-only fixture/source-preview lane under `stock_monitor.news.flow`. Do not connect it to `news-intelligence`, candidate evidence, DB writes, Telegram sends, scheduler tasks, `admin-gui`, or `web-view`. The feature must prove its contract through realistic fixture tests, explicit docs, focused CLI verification, and a clean selective git stage.

**Tech Stack:** Python 3.10, `pytest`, existing `stock_monitor` CLI, existing CodeGraph index, Markdown project contracts.

---

## Current Evidence

- Branch: `codex/news-flow-preview`.
- CodeGraph sees `src/stock_monitor/news/flow.py` and `build_news_flow_preview`.
- Existing implementation files:
  - `src/stock_monitor/news/flow.py`
  - `src/stock_monitor/news/__init__.py`
  - `src/stock_monitor/cli.py`
  - `tests/test_news_flow_preview.py`
  - `tests/test_cli_commands.py`
- Existing unrelated untracked files under `data/` must stay out of this commit unless the user separately approves them.
- Current feature boundary:
  - fixture input only
  - `live_fetch=false`
  - `writes_db=false`
  - `sends_telegram=false`
  - `registers_scheduler=false`
  - `connects_web_view=false`

## Commit Scope

Only these paths are in scope for the final commit:

- `src/stock_monitor/news/flow.py`
- `src/stock_monitor/news/__init__.py`
- `src/stock_monitor/cli.py`
- `tests/test_news_flow_preview.py`
- `tests/test_cli_commands.py`
- `tests/fixtures/news_flow_preview/market_flow_2026_06_01.json`
- `docs/codex/contracts/news-intelligence-contract.md`
- `docs/codex/surface-contract.md`
- `docs/superpowers/plans/2026-06-05-news-flow-preview-closeout.md`

Do not stage:

- `data/`
- `.env`
- DB files
- browser captures
- live-source outputs
- scheduler/task changes

---

### Task 1: Document the Separate `news-flow-preview` Contract

**Files:**
- Modify: `docs/codex/contracts/news-intelligence-contract.md`
- Modify: `docs/codex/surface-contract.md`

- [ ] **Step 1: Add a dedicated `News Flow Preview Lane` section**

Insert this section in `docs/codex/contracts/news-intelligence-contract.md` after the existing `Collection Boundary` section:

```markdown
## News Flow Preview Lane

`news-flow-preview` is a separate operator-only lane for reading the article flow from user-provided news source URLs. It is not a stock top-N enrichment feature, not candidate-evidence linkage, and not a recommendation engine.

Allowed in v1:

- Fixture-backed article flow parsing from an explicit `--source-url` allow-list.
- Article contract fields: `title`, `date`, `url`, `source`, and `summary`.
- Per-source diagnostics: requested URL, source name, parsed article count, and warnings for missing or out-of-scope sources.
- Whole-flow aggregation: repeated stock mentions, sector/theme flow, key issues, caution signals, market mood, text preview, JSON preview, and Telegram draft copy.

Blocked by default:

- Live fetch unless the operator explicitly approves a source-probe pass for the provided URLs.
- DB writes, scheduler registration, Telegram real sends, `admin-gui`, `web-view`, candidate-evidence mutation, public numeric scoring, buy/sell wording, broker execution, and order routing.
- Treating repeated mentions as recommendations, ranks, scores, grades, or trading signals.

Supported command:

- `python -m stock_monitor news-flow-preview --source-url URL [--source-url URL ...] --fixture PATH [--format text|json]`

The command must only include fixture sources whose `source_url` exactly matches one of the provided `--source-url` values. Fixture sources outside that allow-list are excluded and reported as warnings. Requested URLs missing from the fixture are also reported as warnings.

The Telegram draft is preview text only. It must include the source URL basis and say that it summarizes article flow without trading judgment. It must not send Telegram messages.
```

- [ ] **Step 2: Add a surface-boundary note**

Insert this short paragraph in `docs/codex/surface-contract.md` after the existing operator-only news intelligence paragraph:

```markdown
`news-flow-preview` is also operator-only, but it is source-flow oriented rather than stock/candidate oriented. It accepts only operator-provided source URLs through a fixture contract, emits text/JSON preview plus a Telegram draft, and must remain disconnected from DB writes, Telegram real sends, scheduler tasks, `admin-gui`, and public `web-view` until a separate contract explicitly changes that boundary.
```

- [ ] **Step 3: Verify docs wording does not imply trading advice**

Run:

```powershell
rg -n "매수 추천|매도 추천|추천 종목|점수:|등급:|buy signal|sell signal|order routing|broker execution" docs\codex\contracts\news-intelligence-contract.md docs\codex\surface-contract.md
```

Expected:

- No new `news-flow-preview` section line should contain trading-call wording.
- Historical allowed/blocked wording elsewhere may appear only as boundary text.

---

### Task 2: Add a Realistic Synthetic Fixture File

**Files:**
- Create: `tests/fixtures/news_flow_preview/market_flow_2026_06_01.json`
- Modify: `tests/test_news_flow_preview.py`

- [ ] **Step 1: Create the fixture**

Create `tests/fixtures/news_flow_preview/market_flow_2026_06_01.json` with this exact shape:

```json
{
  "sources": [
    {
      "source_url": "https://example.test/market-flow",
      "source": "Market Desk",
      "articles": [
        {
          "title": "Samsung Electronics and SK Hynix rise on AI chip supply news",
          "date": "2026-06-01T09:10:00+09:00",
          "url": "https://news.example/a",
          "source": "Market Desk",
          "summary": "Semiconductor demand and HBM supply contracts kept AI chip names in focus."
        },
        {
          "title": "Samsung Electronics volatility caution after sharp move",
          "date": "2026-06-01T10:20:00+09:00",
          "url": "https://news.example/b",
          "source": "Market Desk",
          "summary": "Overheating and volatility risk were noted after the rally."
        }
      ]
    },
    {
      "source_url": "https://example.test/sector-flow",
      "source": "Sector Desk",
      "articles": [
        {
          "title": "SK Hynix expands AI memory investment",
          "date": "2026-06-01",
          "url": "https://news.example/c",
          "source": "Sector Desk",
          "summary": "Semiconductor capex and AI memory investment remained a market theme."
        },
        {
          "title": "Battery shares watch policy uncertainty",
          "date": "2026-06-01T11:30:00+09:00",
          "url": "https://news.example/d",
          "source": "Sector Desk",
          "summary": "Secondary battery names were cautious on subsidy and regulation uncertainty."
        }
      ]
    },
    {
      "source_url": "https://outside.example/not-requested",
      "source": "Outside Desk",
      "articles": [
        {
          "title": "Outside article should not enter the selected source flow",
          "date": "2026-06-01",
          "url": "https://news.example/outside",
          "source": "Outside Desk",
          "summary": "This source was not provided by the operator."
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Replace inline fixture construction in `tests/test_news_flow_preview.py`**

Use a helper that reads the fixture file:

```python
from pathlib import Path


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "news_flow_preview" / "market_flow_2026_06_01.json"


def _fixture_payload() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")
```

- [ ] **Step 3: Run the fixture tests**

Run:

```powershell
python -m pytest tests/test_news_flow_preview.py -q
```

Expected:

- `3 passed`
- No DB files created.
- No network access required.

---

### Task 3: Strengthen Korean Flow Coverage

**Files:**
- Modify: `tests/test_news_flow_preview.py`
- Modify: `src/stock_monitor/news/flow.py`

- [ ] **Step 1: Add a failing Korean fixture-style test**

Add this test to `tests/test_news_flow_preview.py`:

```python
def test_news_flow_preview_detects_korean_theme_and_caution_terms() -> None:
    content = json.dumps(
        {
            "sources": [
                {
                    "source_url": "https://example.test/korean-flow",
                    "source": "국내시황",
                    "articles": [
                        {
                            "title": "삼성전자·SK하이닉스, HBM 공급 기대에 반도체 강세",
                            "date": "2026-06-01T09:30:00+09:00",
                            "url": "https://news.example/k1",
                            "source": "국내시황",
                            "summary": "AI 메모리 수요와 공급 계약 기대가 반도체 업종 흐름을 이끌었다.",
                        },
                        {
                            "title": "삼성전자 단기 급등 후 변동성 주의",
                            "date": "2026-06-01T10:00:00+09:00",
                            "url": "https://news.example/k2",
                            "source": "국내시황",
                            "summary": "과열 부담과 차익실현 가능성이 경계 신호로 언급됐다.",
                        },
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )

    preview = build_news_flow_preview(
        parse_news_flow_json(content, source_urls=("https://example.test/korean-flow",))
    ).to_dict()

    assert preview["repeated_stocks"][0]["name"] == "Samsung Electronics"
    assert any(theme["label"] == "Semiconductor/AI" for theme in preview["sector_themes"])
    assert any(signal["label"] == "Volatility/overheating" for signal in preview["caution_signals"])
    assert "매매 판단 없이" in preview["telegram_draft"]
```

- [ ] **Step 2: Run the Korean test to verify it fails if current rules are insufficient**

Run:

```powershell
python -m pytest tests/test_news_flow_preview.py::test_news_flow_preview_detects_korean_theme_and_caution_terms -q
```

Expected:

- If it already passes, keep the test as regression evidence.
- If it fails, update only `COMPANY_RULES`, `THEME_RULES`, `ISSUE_RULES`, or `CAUTION_RULES` in `src/stock_monitor/news/flow.py`.

- [ ] **Step 3: Keep rule changes narrow**

Allowed additions:

```python
("Samsung Electronics", ("Samsung Electronics", "삼성전자"))
("SK Hynix", ("SK Hynix", "Hynix", "SK하이닉스", "에스케이하이닉스"))
("Semiconductor/AI", ("semiconductor", "chip", "hbm", "memory", "ai", "반도체", "메모리"))
("Volatility/overheating", ("volatility", "overheating", "sharp move", "caution", "risk", "변동성", "과열", "주의", "차익실현"))
```

Do not add broad aliases such as plain `Samsung` or plain `Hyundai` because they can create false repeated-stock mentions.

- [ ] **Step 4: Run all news-flow tests**

Run:

```powershell
python -m pytest tests/test_news_flow_preview.py -q
```

Expected:

- `4 passed` after the new Korean test is added.

---

### Task 4: Add CLI Smoke Against the Repository Fixture

**Files:**
- Modify: `tests/test_cli_commands.py`

- [ ] **Step 1: Add a CLI smoke test using the repository fixture**

Add this test near the current `news-flow-preview` CLI tests:

```python
def test_news_flow_preview_cli_uses_repository_fixture(capsys) -> None:
    fixture = Path("tests/fixtures/news_flow_preview/market_flow_2026_06_01.json")

    exit_code = cli_module.main(
        [
            "news-flow-preview",
            "--source-url",
            "https://example.test/market-flow",
            "--source-url",
            "https://example.test/sector-flow",
            "--fixture",
            str(fixture),
            "--format",
            "text",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "News flow preview" in output
    assert "source URLs: 2" in output
    assert "telegram draft:" in output
    assert "writes_db: False" in output
    assert "sends_telegram: False" in output
    assert "registers_scheduler: False" in output
    assert "connects_web_view: False" in output
```

- [ ] **Step 2: Run CLI preview tests**

Run:

```powershell
python -m pytest tests/test_cli_commands.py -q -k news_flow_preview
```

Expected:

- The parser test, JSON output test, and repository fixture text smoke pass.
- No network calls, DB writes, Telegram sends, or scheduler registration happen.

---

### Task 5: Run Full Feature Verification

**Files:**
- No code changes unless verification finds a defect.

- [ ] **Step 1: Run focused regression tests**

Run:

```powershell
python -m pytest tests/test_news_intelligence.py tests/test_news_collectors.py tests/test_news_flow_preview.py tests/test_cli_commands.py -q -k "news_intelligence or news_flow_preview"
```

Expected:

- All selected tests pass.
- Existing `news-intelligence-preview` behavior remains intact.

- [ ] **Step 2: Run compile check**

Run:

```powershell
python -m compileall -q src tests
```

Expected:

- Exit code `0`.

- [ ] **Step 3: Run docs hygiene audit after docs edits**

Run:

```powershell
python -m stock_monitor docs-hygiene-audit --json
```

Expected:

- `ready=true`
- `issue_count=0`
- If the default DB schema guard blocks this read-only command, record the blocker and run the narrower docs wording grep from Task 1 as the fallback evidence.

- [ ] **Step 4: Run wording guard on code and tests**

Run:

```powershell
rg -n "추천 종목|매수 추천|매도 추천|점수:|등급:|buy signal|sell signal|order routing|broker execution" src\stock_monitor\news\flow.py tests\test_news_flow_preview.py tests\test_cli_commands.py
```

Expected:

- No matches except explicit negative assertions or boundary text.

- [ ] **Step 5: Confirm CodeGraph sees final symbols**

Run CodeGraph search for:

- `build_news_flow_preview`
- `parse_news_flow_json`
- `_run_news_flow_preview`

Expected:

- Symbols resolve to `src/stock_monitor/news/flow.py` and `src/stock_monitor/cli.py`.

---

### Task 6: Diff Review and Selective Stage Plan

**Files:**
- No code changes unless review finds an unintended edit.

- [ ] **Step 1: Review changed files**

Run:

```powershell
git diff --stat
git diff -- src\stock_monitor\news\flow.py src\stock_monitor\news\__init__.py src\stock_monitor\cli.py tests\test_news_flow_preview.py tests\test_cli_commands.py docs\codex\contracts\news-intelligence-contract.md docs\codex\surface-contract.md docs\superpowers\plans\2026-06-05-news-flow-preview-closeout.md
```

Expected:

- Only scoped feature, test, docs, and plan changes appear.
- No `data/` content appears in the diff because it is untracked and not staged.

- [ ] **Step 2: Confirm untracked separation**

Run:

```powershell
git status --short
git ls-files --others --exclude-standard
```

Expected:

- `data/` files remain untracked.
- `src/stock_monitor/news/flow.py`, `tests/test_news_flow_preview.py`, fixture file, and plan file are visible as new untracked files until explicitly staged.

- [ ] **Step 3: Stage only scoped files after explicit user approval**

Do not run this until the user says to commit/stage.

```powershell
git add -- `
  src/stock_monitor/news/flow.py `
  src/stock_monitor/news/__init__.py `
  src/stock_monitor/cli.py `
  tests/test_news_flow_preview.py `
  tests/test_cli_commands.py `
  tests/fixtures/news_flow_preview/market_flow_2026_06_01.json `
  docs/codex/contracts/news-intelligence-contract.md `
  docs/codex/surface-contract.md `
  docs/superpowers/plans/2026-06-05-news-flow-preview-closeout.md
```

Expected:

- `git diff --cached --stat` contains only the files listed above.
- `data/` remains unstaged.

---

### Task 7: Commit and Push Plan

**Files:**
- No file edits.

- [ ] **Step 1: Commit after staged diff is reviewed**

Do not run this until the user explicitly says to commit.

```powershell
git commit -m "feat: add news flow preview lane"
```

Expected:

- Commit succeeds on `codex/news-flow-preview`.
- Commit includes code, tests, fixture, docs, and plan.

- [ ] **Step 2: Push after commit and explicit user approval**

Do not run this until the user explicitly says to push.

```powershell
git push -u origin codex/news-flow-preview
```

Expected:

- Remote branch `origin/codex/news-flow-preview` exists.
- Local branch tracks the remote branch.

- [ ] **Step 3: Final report**

Report:

- changed paths
- verification commands and pass/fail results
- commit hash
- push remote/branch
- explicit note that `data/` was not staged
- remaining non-commit items, if any

---

## Completion Criteria

The branch is ready for commit/push only when all of the following are true:

- `news-flow-preview` remains separate from `news-intelligence`, candidate evidence, DB, Telegram sends, scheduler, `admin-gui`, and `web-view`.
- Source URL allow-list behavior is documented and tested.
- Fixture-backed parser/aggregator tests pass.
- CLI text/json preview tests pass.
- Korean theme/caution regression coverage exists.
- Docs state that repeated mentions are descriptive flow signals, not recommendations, scores, grades, or trading calls.
- `compileall` passes.
- Wording guard has no problematic hits.
- CodeGraph sees the final new symbols.
- `data/` remains unstaged.
- Commit and push are performed only after explicit user approval.
