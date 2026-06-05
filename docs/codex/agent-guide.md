# Agent Guide

## Purpose

This is the consolidated agent usage guide for `02.Stock_Moniter`.

Use this before spawning or assigning subagents. Older agent prompt/planning files remain as reference, but this file is the active routing guide.

2026-05-29 update: project-local `.codex/agents/` is intentionally absent. Use the global Codex agent/skill layer plus CodeGraph first. Role names below are ownership/routing vocabulary for prompts and reviews, not a request to recreate local TOML agents.

## Default Rule

For small and obvious single-surface edits, keep the work local.

For non-trivial work, prefer subagent use by default. Split the task into investigation, implementation, and review when that reduces risk or gives a clearer handoff.

Typical split:

| Work slice | Preferred routing |
| --- | --- |
| Investigation / source or code boundary | `explorer`, `debugger`, `market-data-engineer`, `sql-pro`, or the relevant UI/backend specialist |
| Implementation | `backend-developer`, `python-pro`, `cli-developer`, `web-ui-engineer`, `admin-ui-engineer`, `market-data-engineer`, or `test-engineer` |
| Review / risk check | `reviewer`, `security-hardening`, `sql-pro`, or `test-engineer` |

Do not keep agents open after their result is integrated. Close completed agents to avoid slot exhaustion.

## Role Routing

| Need | Preferred agent |
| --- | --- |
| Parser, summary, runtime Python contracts | `python-pro` |
| Fetch, parse, persist, notify pipeline | `backend-developer` |
| CLI, scheduler wrappers, shell-facing workflows | `cli-developer` |
| SQLite schema, migrations, dedupe, backup/restore | `sql-pro` |
| Regression tests and unattended-run checks | `test-engineer` |
| PR-style risk review | `reviewer` |
| Runtime/scheduler/Telegram failure isolation | `debugger` |
| KRX/KIS/ETF/flow source boundaries | `market-data-engineer` |
| Local operator UI | `admin-ui-engineer` |
| Shared GET-only user page | `web-ui-engineer` |
| Access gate, exposure boundary, public-safe route review | `security-hardening` |
| Roadmap, handoff, changelog, docs | `documentation-engineer` |

## Optional Global Skill

`$scrapling-official` is the preferred active source-probe skill for new browser-gated, rendered-page, anti-bot-sensitive, or future-source work.

If the old global skill `$botasaurus-stock-monitor` is present, treat it as legacy/archived reference only. Do not use it as an active maintained probe lane unless the user explicitly asks to restore it.

If the global skill `$scrapling-official` is installed, use it as an active source-probe lane for:

- rendered-page extraction where simple request or API paths return only an app shell
- browser-gated or anti-bot-sensitive source checks
- bounded source comparison before deciding whether a source should remain probe-only, become fallback, or be proposed for later integration

For Scrapling CLI extraction commands, include `--ai-targeted`. Use the configured shared Scrapling runtime path, represented in public docs as `{SCRAPLING_EXE}`. Do not wire Scrapling into production DB writes, Telegram automation, scheduler tasks, `admin-gui`, or public `web-view`. KRX/Data Marketplace should still prefer existing request/login/sample validation paths first; use Scrapling only for bounded source probing when those paths are insufficient or the source is new/unstable.

If the global skill `$kronos-market-forecast` is installed, use it only for:

- offline OHLCV forecast experiments on stored KRX data
- comparison against backtest-observation or candidate-evidence views
- hidden research work before any scoring policy discussion

Do not use it for public numeric scores, trading recommendations, Telegram alerts, scheduler decisions, or direct product-surface changes.

## CodeGraph MCP

`codegraph` is available for this project and already initialized under `{PROJECT_ROOT}\.codegraph`.
Treat it as a code-navigation backend for existing agents, not as a new product dependency.

Prefer it first when the task is about:

- fetch -> parse -> persist -> summarize -> notify ownership
- scheduler wrapper or CLI entry paths
- admin/web-view route ownership
- schema / migration impact
- deciding whether an experiment or source probe leaks into production behavior

Good pairings:

| Need | Preferred agent + CodeGraph use |
| --- | --- |
| runtime flow trace | `debugger` or `backend-developer` + callers/callees/impact |
| source/market-data boundary trace | `market-data-engineer` + callers/callees/impact |
| schema or replay risk | `sql-pro` + impact |
| exposure/public-safe review | `security-hardening` or `reviewer` + route/DTO impact |
| admin/web-view path ownership | `web-ui-engineer` or `admin-ui-engineer` + path narrowing |

Do not overuse it for:

- known single-file edits
- obvious doc wording changes
- tiny local test updates with fully known scope

After using `codegraph`, still read the real file contents before editing or making a final claim.

## Skill vs Agent Comparison

Skills and agents are not interchangeable.

Use a skill when the task needs a specialized workflow or tool lane. Use an agent when the task needs role-based investigation, implementation, or review inside this project.

| Task type | Prefer skill | Prefer agent | Why |
| --- | --- | --- | --- |
| KRX Open API stock/ETF/index daily data | none | `market-data-engineer`, `backend-developer`, `sql-pro` | The approved Open API path already exists in the main codebase. No browser or anti-detect probe is needed. |
| KRX Data Marketplace login/session/source probing | Existing request/login/sample validation first; `scrapling-official` only for bounded browser/source probes when needed | `market-data-engineer`, `debugger` | Scrapling is the active probe tool, but source semantics and production boundary still need project agents. Botasaurus is legacy reference only unless explicitly restored. |
| KRX investor-flow schema/import/display | none by default | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` | The data should flow through existing repository/schema/web-view contracts, not through a separate probe lane. |
| Future real-time quote/turnover lane | source-specific skill or `scrapling-official` only for bounded reachability probes | `market-data-engineer`, `web-ui-engineer`, `security-hardening`, `reviewer`, `test-engineer` | Read-only lab/staging first. After approval, values may affect observation priority and `우선 확인`, but not broker execution, public scores, or trading calls. |
| Future operator decision/execution lane | source/broker skills only after explicit approval | `market-data-engineer`, `security-hardening`, `reviewer`, `sql-pro`, `test-engineer`, `cli-developer` | Do not treat current public wording limits as a permanent goal. Trading-decision support is possible only as a separate operator-only/execution-lab path after real-time source, audit, permission, and order-safety gates. |
| Naver report collection/parser | none by default; `scrapling-official` only for bounded source discovery | `backend-developer`, `python-pro`, `test-engineer` | Main Naver pipeline is production code; Scrapling probes must not replace stable request/API paths without documented evidence. |
| Telegram/scheduler/SQLite operation | none | `cli-developer`, `debugger`, `test-engineer`, `reviewer` | Operational behavior needs CLI/DB/replay safety, not a browser skill. |
| User `web-view` / admin UI | `browser-use:browser` only for local visual verification | `web-ui-engineer`, `admin-ui-engineer`, `security-hardening` | Browser skill can verify UI, but implementation/review should stay with UI/security agents. |
| OHLCV forecast experiment | `kronos-market-forecast` | `market-data-engineer`, `reviewer` | Kronos is research-only and may compare against stored KRX data; it must not feed public scoring directly. |
| Public numeric scoring / trading recommendation | none for production | `reviewer`, `market-data-engineer`, `sql-pro`, `test-engineer` | Still blocked. Skills can support experiments only; public score requires data/holdout policy first. Observation-candidate recommendation remains a product/UI task, not a trading recommendation. |
| Documentation/roadmap/handoff | `superpowers:writing-plans` for large implementation plans | `documentation-engineer` | The skill structures plans; the agent keeps local docs consistent. |

Practical rule:

- If the question is "can this source be reached or probed?", consider a skill.
- If the question is "should this become product behavior?", use agents and repository tests.
- If the result would touch Telegram, scheduler, SQLite, `admin-gui`, or `web-view`, do not let a skill bypass the normal implementation/review path.

## Required Context For Agents

Always include:

- Scope is only `{PROJECT_ROOT}`.
- Read `AGENTS.md`.
- Check [data-quality-checklist.md](/docs/codex/data-quality-checklist.md) before data-display or parsing work.
- Preserve `admin-gui` vs `web-view` boundary from [surface-contract.md](/docs/codex/surface-contract.md).
- Do not enable KRX Data Marketplace scheduled ingest without explicit approval.

## Closure Rule

After each agent task:

1. Integrate or record the result.
2. Close the agent if no follow-up is needed.
3. Update roadmap or changelog only if the result changes project state.

## Avoid

- Multiple agents reviewing the same stale issue without new code context.
- Agents holding slots after final response.
- Agent tasks that ask broad questions instead of producing a concrete patch, finding, or decision.
