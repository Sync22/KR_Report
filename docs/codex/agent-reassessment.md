# Agent Reassessment

2026-05-29 decision: keep project-local `.codex/agents/` absent. The role names below remain useful ownership vocabulary, but the default execution layer is now global agents/skills plus CodeGraph. Do not recreate or bulk-restore the old local TOML agent set unless repeated Stock Monitor work proves one exact missing role.

## Current work axes

| Axis | Current state | Primary local evidence |
| --- | --- | --- |
| Live operation validation | Runnable MVP is in live-market validation and operational hardening mode. | `AGENTS.md`, `current-work.md` |
| Telegram MVP | Scheduled daily summary, intraday alert, paging, memo capture, status helpers, and fragment resume exist. | `current-work.md`, `execution-roadmap.md` |
| Admin GUI | `admin-gui` is a local control-capable operator surface. | `current-work.md`, `module-ownership.md` |
| User web-view | Separate GET-only read-only `web-view` exists for friend/user information display. | `current-work.md`, `surface-contract.md` |
| KRX market reference | Stock/ETF/index snapshots exist and are treated as read-only market context. | `current-work.md`, `data-source-policy.md` |
| KRX investor flow | Data Marketplace validation/import/display paths exist, but scheduled ingest is disabled. | `current-work.md`, `krx-market-data-runbook.md` |
| Category/taxonomy | 업종/테마 are a separate taxonomy layer with category snapshots and fallback debt. | `current-work.md`, `data-source-policy.md` |
| Candidate evidence | Read-only evidence rows can support observation-candidate recommendation; no public numeric scoring or trading recommendation. | `candidate-evidence-plan.md`, `next-phase.md` |
| Future operator decision lane | Not built. Possible only after stable real-time data, source freshness, failure behavior, permission, and order-safety gates are proven. | `current-work.md`, `next-phase.md`, `surface-contract.md` |
| External sharing | Optional entry-code gate exists; Cloudflare/Tailscale not configured. | `current-work.md`, `surface-contract.md` |

## Next-phase axes

| Axis | Needed work | Likely owner set |
| --- | --- | --- |
| Operational closeout | Scheduler/worker/delivery/DB health observation across market days. | `debugger`, `cli-developer`, `reviewer`, `test-engineer` |
| User web-view closeout | Stock search bar, mobile QA, display cleanup, public-safe regression. | `web-ui-engineer`, `test-engineer`, `security-hardening` |
| Candidate evidence foundation | Read-only DTO combining report/KRX/flow/category facts without score. | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` |
| Future operator-only decision support | Boundary design only after real-time source proof. | `market-data-engineer`, `security-hardening`, `reviewer`, `sql-pro`, `test-engineer` |
| Rotation / ETF candidate preview | Cycle image alias mapping, 업종-to-ETF candidates, preview only. | `market-data-engineer`, `web-ui-engineer`, `admin-ui-engineer` |
| Category snapshot cleanup | Reduce fallback dates through explicit source-date refresh and safe DB workflow. | `market-data-engineer`, `sql-pro`, `backend-developer`, `test-engineer` |
| Mini PC / external sharing prep | Access gate, Cloudflare/Tailscale boundary, operation profile, no public admin. | `security-hardening`, `documentation-engineer`, `cli-developer`, `reviewer` |

## Role Vocabulary To Keep

| Role | Keep reason | Use when |
| --- | --- | --- |
| `backend-developer` | Still needed for production behavior across fetch, parse, store, summarize, notify. | End-to-end backend behavior changes after the boundary is known. |
| `python-pro` | Still useful for Python runtime contracts, parsing, typing, and implementation seams. | Runtime/typing/parser bugs or Python module refactors. |
| `cli-developer` | Required for scheduler wrappers, operator commands, safe flags, and automation-facing UX. | CLI command, exit-code, Task Scheduler wrapper, or shell workflow changes. |
| `sql-pro` | Needed as read-only reviewer for schema/query/dedupe/migration correctness. | DB contract review before repository or migration work. |
| `reviewer` | Needed for PR-style risk review around business days, dedupe, delivery, and missing tests. | Before/after high-risk changes or when user asks for a review. |
| `debugger` | Needed for unattended-run, scheduler, worker heartbeat, and runtime-state failures. | When observed behavior differs from expected scheduled behavior. |
| `test-engineer` | Needed because replay, paging, outbox, scheduler, and DTO boundaries are regression-sensitive. | Add or repair focused tests after behavior changes. |
| `admin-ui-engineer` | Still distinct from web-view because `admin-gui` is control-capable. | Operator-facing GUI/status/control work. |
| `web-ui-engineer` | Still distinct from admin because `web-view` is friend-facing and GET-only. | User page layout, public DTO rendering, archive/search/detail UX. |
| `documentation-engineer` | Needed because current state is document-heavy and easy to drift. | Roadmap/current-work/handoff/surface-contract sync. |
| `market-data-engineer` | Strongly needed for KRX/ETF/flow, category snapshots, and candidate evidence. | Source/field/schema boundary and market-data expansion. |
| `security-hardening` | Now justified by access-code gate and future external sharing. | Entry-code gate, public-safe DTO, GET-only/admin boundary checks. |

## Add

No new local agent is required immediately.

| Potential new agent | Decision | Reason |
| --- | --- | --- |
| `candidate-analytics-engineer` | Do not add now. | Candidate evidence can be covered by `market-data-engineer` + `sql-pro` + `web-ui-engineer` + `reviewer`. Adding a scoring/analytics role too early would encourage premature trading-recommendation logic. |
| `deployment-engineer` | Do not add now. | Mini PC and Cloudflare/Tailscale are still preparation work. `security-hardening`, `cli-developer`, and `documentation-engineer` cover the current scope. |
| `data-visualization-engineer` | Do not add now. | Rotation overlay and web-view visuals are covered by `web-ui-engineer`; calibration can use `admin-ui-engineer`. |

## Merge or restore

No project-local agent should be restored now.

| Agents | Assessment | Action |
| --- | --- | --- |
| `backend-developer` / `python-pro` | Overlap exists around implementation, but boundary is manageable: backend owns product behavior, python-pro owns runtime/module contracts. | Keep both as routing vocabulary; choose one primary per task. |
| `admin-ui-engineer` / `web-ui-engineer` | Intentional split. Admin is control-capable; web-view is public-safe read-only. | Keep both as routing vocabulary; do not merge the surfaces. |
| `market-data-engineer` / `sql-pro` | Overlap on schema planning, but market-data owns source semantics and sql-pro owns DB correctness. | Keep both as routing vocabulary; use sql-pro as review/contract specialist. |
| `reviewer` / `test-engineer` | Overlap on risk, but reviewer finds issues and test-engineer codifies regressions. | Keep both as routing vocabulary. |
| `documentation-engineer` / `reviewer` | Overlap on correctness, but documentation-engineer owns doc drift while reviewer owns behavioral risk. | Keep both as routing vocabulary. |
| `security-hardening` / `reviewer` | Overlap on risk review, but security-hardening is specifically exposure/public-surface focused. | Keep both as routing vocabulary due to access gate and future sharing. |

## Why

The old local agent set was broad but the role boundaries are justified by the project shape.

The project is no longer only a scraper. It now has independent operating axes:

- unattended scheduled operation
- replay-safe Telegram delivery
- SQLite schema and migration safety
- local control-capable admin UI
- separate friend-facing read-only web-view
- KRX market and investor-flow data expansion
- category/taxonomy history
- candidate-evidence planning
- external-sharing preparation

The main risk is not missing an agent. The main risk is assigning the wrong agent to a task and blurring boundaries:

- Do not let `web-ui-engineer` add control behavior to `web-view`.
- Do not let `admin-ui-engineer` turn admin into a friend-facing surface.
- Do not let `market-data-engineer` move from evidence to public numeric scoring or public trading recommendation without reviewer approval. Observation-candidate recommendation remains a web-view/product copy boundary. Future trading-decision support, if pursued, is operator-only and needs a separate execution-lab/source-safety contract.
- Do not let `backend-developer` make DB-shape changes without sql/repository review.
- Do not let `security-hardening` become broad enterprise-auth work; keep it focused on local exposure risk.

When work is multi-step, cross-module, high-risk, or needs separate review, use these boundaries with the global layer and CodeGraph to split investigation, implementation, and review. Do not spawn agents for small, low-risk, single-surface edits.

## Skills versus agents

This project now has two installed project-specific global skills:

- `botasaurus-stock-monitor`
- `kronos-market-forecast`

They are useful, but they are not replacements for repository ownership review.

| Capability | Skill fit | Agent fit | Decision |
| --- | --- | --- | --- |
| KRX Open API stock/ETF/index backfill | No special skill needed. | `market-data-engineer`, `backend-developer`, `sql-pro` | Keep using the existing Open API CLI/repository path. |
| KRX Data Marketplace browser/session probing | `botasaurus-stock-monitor` is appropriate for a bounded detection/session probe. | `market-data-engineer`, `debugger` define what success means and whether it should influence the product. | Use Botasaurus only for probes, not production ingest. |
| KRX investor-flow import/display | No skill by default. | `market-data-engineer`, `sql-pro`, `web-ui-engineer`, `reviewer` | Use the normal DB/DTO/UI path. |
| Stored OHLCV forecasting experiment | `kronos-market-forecast` is appropriate for research-only stored KRX OHLCV experiments. | `market-data-engineer`, `reviewer`, `test-engineer` judge whether results are meaningful. | Keep Kronos output offline and hidden. |
| Web-view visual verification | `browser-use:browser` is appropriate for local UI inspection when it can access the page. | `web-ui-engineer`, `security-hardening` implement and review public-safe UI behavior. | Browser verifies; agents own changes. |
| Telegram/scheduler/SQLite safety | No project skill should handle this. | `cli-developer`, `debugger`, `sql-pro`, `test-engineer`, `reviewer` | Keep in local code/review workflow. |
| Public numeric score / trading recommendation | No skill should directly produce product behavior. | `reviewer`, `market-data-engineer`, `sql-pro` must approve data/holdout policy first. | Still blocked from public surfaces; observation-candidate recommendation is allowed separately. Future operator-only decision support is a separate lane, not a skill shortcut. |

The reason this comparison was not previously prominent is that the data targets overlapped: both skills and agents can touch "market data" in a broad sense. The actual boundary is narrower:

- Botasaurus answers browser/source-access questions.
- Kronos answers offline forecast-experiment questions.
- Local agents answer product correctness, DB safety, UI boundaries, Telegram operations, and documentation consistency.

## Suggested prompt examples

### User web-view search

```text
Use web-ui-engineer to add the top-right stock search flow to the GET-only web-view.
Keep admin-gui separate, do not add write/control routes, and add public-safe regression tests.
```

### Candidate evidence DTO

```text
Use market-data-engineer and sql-pro to design the first read-only candidate_evidence DTO.
Use only stored Naver report summaries, KRX market snapshots, stored investor-flow rows, and category snapshots.
Do not add public numeric scoring, trading-recommendation wording, Telegram alerts, or final picks. Observation-candidate wording such as `오늘의 관찰 후보` is allowed only after the UI boundary is checked.
```

### Candidate evidence UI

```text
Use web-ui-engineer to render candidate_evidence as 관찰 후보 근거 in web-view.
Keep evidence separated by report, price/turnover, investor flow, and category context.
Allow `오늘의 관찰 후보`, `우선 확인`, and `관찰 우선순위`; block public numeric 점수, 투자등급, 매수/매도 추천, and buy/sell wording.
```

### KRX Data Marketplace scheduled ingest design

```text
Use market-data-engineer and debugger to draft Stage 6 scheduled-ingest design for KRX Data Marketplace flow.
Focus on login/session checks, LOGOUT skip behavior, retry, operation events, backup/verify prerequisites, and disabled-by-default scheduling.
Do not enable the scheduler.
```

### DB migration or repository change

```text
Use sql-pro to review the proposed schema/repository change first, then use backend-developer or python-pro for implementation.
Preserve migration-runner discipline, foreign keys, idempotent upserts, and db-verify coverage.
```

### Admin GUI operation control

```text
Use admin-ui-engineer to improve the local admin-gui operator flow.
Keep it loopback/operator-only, preserve confirmation text for risky controls, and do not expose admin behavior through web-view.
```

### External sharing hardening

```text
Use security-hardening to review access-code gate behavior and web-view public-safe responses before Cloudflare Tunnel setup.
Confirm admin-gui, scheduler controls, settings, DB paths, .env, Telegram token/chat id, and audit logs are not exposed.
```

### Live scheduler issue

```text
Use debugger to isolate the scheduled-run failure.
Compare expected task window, operator profile, business-day guard, worker heartbeat, operation events, and delivery/outbox state.
Return confirmed evidence separately from hypotheses.
```

### Documentation drift

```text
Use documentation-engineer to reconcile AGENTS.md, current-work, next-phase, module-ownership, and execution-roadmap with current implementation.
Do not add a new planning document unless the content cannot fit an existing canonical doc.
```

## External reference assessment

External references reviewed on `2026-05-11`:

- `Vibe-Trading`
- `spec-kit`
- `lightweight-charts`

### What to take

- `Vibe-Trading`
  - Reinforces keeping security/public-surface boundaries explicit before broader sharing.
  - Confirms the value of dedicated source/tool/domain roles rather than one generic implementation agent.
- `spec-kit`
  - Reinforces the existing document-first flow around `current-work`, `next-phase`, `module-ownership`, `surface-contract`, and `candidate-evidence-plan`.
- `lightweight-charts`
  - Useful as a future implementation library candidate if `web-view` later needs interactive market charts.

### What not to take now

- `Vibe-Trading` trading-strategy, backtest, portfolio, swarm-finance roles
  - Too broad and too domain-specific for the current Stock Monitor scope.
- `spec-kit` as a new dedicated agent
  - Current `documentation-engineer` plus existing docs already cover the immediate need.
- `lightweight-charts`-driven chart agent
  - The next-phase docs emphasize search, candidate evidence, public-safe DTOs, and sharing boundaries before charts.

## Final keep / add / merge-remove

### Keep

- `backend-developer`
- `python-pro`
- `cli-developer`
- `sql-pro`
- `reviewer`
- `debugger`
- `test-engineer`
- `admin-ui-engineer`
- `web-ui-engineer`
- `documentation-engineer`
- `market-data-engineer`
- `security-hardening`

### Add

- none now

### Merge or remove

- none now

The external references did not justify another immediate local agent beyond the already-added `security-hardening`.
