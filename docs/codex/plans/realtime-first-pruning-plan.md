# Realtime-First Pruning Plan

## Purpose

This plan recenters Stock Monitor around evidence that helps answer "what should I look at now?" without adding broad new source lanes or trading advice.

The change is information architecture and operating judgment first:

- Put current or intraday evidence first when it exists.
- Keep stored same-day report/news evidence close to the top candidate.
- Move previous-day KRX daily rows, investor flow, ETF, reaction windows, and backtest-style review below the first-read path.
- Keep public `web-view` and Telegram free of buy/sell calls, numeric scores, investment grades, entry/exit/target-return language, conviction labels, broker execution, and order routing.

## Current Finding

The existing implementation already has the right separation primitives:

| Axis | Current behavior | Pruning implication |
| --- | --- | --- |
| `web-view` daily API | `build_web_view_daily_snapshot` includes top-2 `priority_candidate_evidence`, `market_briefing`, `source_freshness_summary`, news summary, KRX context, flow, and rotation references. | Keep top-2 and freshness on main, but make the first screen less dominated by stored daily/KRX reference blocks. |
| Candidate evidence | `build_web_view_candidate_evidence_snapshot` ranks stored report, news, KRX, `[12009]`, Toss 20:00 baseline, target progress, and support/gap labels without public scores. | Keep as the primary candidate engine, but expose only the rank-driving current/stored-now reason in the first 10 seconds. |
| Backtest/reaction | `/api/observation/backtest` lazy-loads stored post-report reaction windows into the `관찰` tab. | Move lower or collapse as review-only. It is useful for learning, not for immediate market observation. |
| Market/KRX/flow | `시장` tab shows selected-date or latest stored KRX market/flow references and clearly labels stale/missing states. | Keep as fallback/detail. Do not let stale daily reference lead the story. |
| Toss/current quote | `/api/toss-priority-quotes` is top-2 only, read-only, no DB write, no arbitrary symbol query, no account/order data. | Promote as primary evidence only when configured and successfully fetched. Otherwise show it under `부족한 근거`. |
| Naver intraday reference | The main screen has Naver market-top/current quote style reference paths for top candidates, read-only and source-labelled. | Treat successful overlap/current quote as primary current evidence. Treat non-overlap as scope evidence, not a negative signal. |
| Telegram briefing | `market-briefing` builds candidate/news/source freshness around top-2 and can optionally include live candidate quotes. | Reorder copy so top candidates and current evidence appear before stored reference sections. |

## Evidence Classification

| Class | Evidence | Use | Surface placement |
| --- | --- | --- | --- |
| Primary evidence | Top-2 candidate identity and visible `why_notable` / `value_profile` reason | First answer to "what to check now" | `web-view` main first block, Telegram `오늘 볼 것` |
| Primary evidence | Same-day saved direct/caution news observation for the top-2 | Confirms, conflicts with, or weakens the report hypothesis | Main top-2 cards and Telegram `현재 근거` |
| Primary evidence | Approved top-2 current quote or turnover reference, including Toss current price or bounded Naver quote/market-top overlap | Currentness check, only with source/time/status | Main top-2 card and Telegram `현재 근거` |
| Primary evidence | Source freshness state for reports/news/current quote/KRX/flow | Prevents stale evidence from looking current | Compact inline status near top-2 |
| Fallback evidence | KRX Open API stock/ETF/index daily snapshots | Stored market reference, usually previous business day or selected date | `시장` tab, collapsed main reference, Telegram `전일 참고` |
| Fallback evidence | KRX `[12009]` stock investor flow for selected candidates | Support context when exact and selected-candidate scoped | Candidate detail and Telegram `전일 참고` or `현재 근거` only if exact/same candidate |
| Fallback evidence | KRX `[12008]` market flow and `[12010]` net-buy ranks | Market background and rank reference | `시장` detail, never top reason alone |
| Fallback evidence | ETF daily and rotation reference | Sector/theme support only | `순환매` tab, collapsed from main |
| Fallback evidence | Toss 20:00 stored baseline | End-of-day baseline, not intraday confirmation | Candidate detail, not top headline |
| Research/review only | Backtest observation, reaction windows, D+1/D+5/D+10/D+20 rows | Learn whether exposed evidence was useful later | `관찰` bottom or separate collapsed `복기/연구` block |
| Research/review only | Target-hit/max-progress and historical target reaction | Retrospective context | Stock detail or review block, not main top card |
| Research/review only | X recap lab and news search lane lab results | Lab feasibility and source quality review | Docs/lab branch only |
| Hold | Broad all-stock `[12009]`, `[12008]`, `[12010]` scheduled ingest | Not approved for production automation | Do not connect |
| Hold | Toss account, balance, order history/info, order endpoints | Broker/account/execution surface | Do not connect to public surface, scheduler, Telegram, DB write, or admin-gui |
| Hold | Public score, grade, trade call, entry/exit/take-profit/target-return/conviction | Changes product risk profile | Blocked |
| Hold | `x-browser-recap-lab` merge into main | Main is the redesign basis; lab branch is behind | Reference ideas only |

## Web-View Repositioning

### Main screen: raise

- `오늘 볼 것`: top-2 candidates with one-line observation reason.
- `현재 근거`: for each top-2, show same-day saved direct/caution news and current quote/turnover evidence only when it exists with source and checked time.
- `부족한 근거`: show missing current quote, missing news collection, stale KRX, and missing exact `[12009]` as gaps.
- Source freshness as a one-line compact strip near the top, not a full diagnostic card.

### Main screen: lower

- KRX daily index/turnover cards when they are not same-day/current.
- Broad market/flow summaries that do not name the top-2 candidate.
- ETF and rotation references.
- Target progress and historical reaction wording.

### Send to detail, collapsed, or tabs

- Full candidate list stays in `관찰`.
- Stock-level report rows, target trail, Toss 20:00 baseline, and saved news detail stay in `종목`.
- KRX daily market, `[12008]`, `[12009]`, `[12010]`, and flow trend stay in `시장`.
- ETF and category/rotation stay in `순환매`.
- Backtest/reaction windows move to a collapsed `복기/연구` section under `관찰` or below stock detail.

### Hold completely

- Public numeric score, investment grade, trade instruction, target return, conviction, broker/order wording.
- Broad live source probing or scheduler wiring.
- Production use of X recap, Naver search lane, or Toss account/order endpoints.

### Mobile 10-second first-read block

The first mobile viewport should answer only this:

1. `오늘 볼 것`: top-2 stock names and why they are visible.
2. `현재 근거`: news/current quote/turnover status for those two.
3. `부족한 근거`: one short gap line, for example `현재가 미확인 · 뉴스 수집 전 · KRX 전일 기준`.
4. `전일 참고`: one compact link or collapsed chip to KRX/flow detail.

Draft copy shape:

```text
오늘 볼 것
1. 종목A - 리포트 집중 + 직접 뉴스 근거
   현재 근거: 뉴스 2건, Toss 현재가 12:03 확인
   부족한 근거: [12009] 수급은 전일 기준
2. 종목B - 리포트 집중, 뉴스 근거 대기
   현재 근거: Naver 장중 거래대금 겹침 없음
   부족한 근거: 직접 뉴스 없음, KRX 전일 기준
```

## Telegram Briefing Repositioning

Target order:

1. `오늘 볼 것`
   - Top-2 names, codes, and one observation reason each.
2. `현재 근거`
   - Same-day saved news, current quote/turnover, checked time, source.
   - If no current evidence exists, say so here rather than silently falling back.
3. `전일 참고`
   - KRX daily index/turnover, `[12009]` flow, ETF only when concise and source-labelled.
4. `부족한 근거`
   - Missing current quote, stale/missing KRX, no saved news, no exact flow.
5. `복기/연구`
   - Reaction/backtest reminder or link-style note only, normally omitted from short messages.

Compression rule:

- Telegram should not lead with broad market/KRX if a top-2 current evidence row exists.
- If current evidence is absent, the message should say `현재 근거 부족` before showing `전일 참고`.
- Keep one line per candidate where possible. Avoid source diagnostics unless they change what the operator should check next.

Draft shape:

```text
오늘 볼 것
1. 종목A 000000 - 리포트 집중 + 직접 뉴스 근거
2. 종목B 111111 - 리포트 집중, 뉴스 확인 대기

현재 근거
- 종목A: 뉴스 2건 · Toss 현재가 12:03 확인
- 종목B: 현재가 미확인 · Naver 장중 겹침 없음

전일 참고
- KRX 지수/거래대금: 2026-MM-DD 저장 기준
- 수급: Top2 중 1개만 [12009] exact

부족한 근거
- 종목B 직접 뉴스 없음
- ETF/순환매는 상세 참고

복기/연구
- 리포트 후 흐름은 운영 검수표에만 기록
```

## 10-Business-Day Operating Review Checklist

Use one row per market day before marking the related TODO2 items complete.

Do not fabricate rows. Fill them only from same-day read-only previews and browser review.

| Day | Date | Slot / checked time | Top2 candidates | Current evidence | Previous-day reference usefulness | News evidence state | Telegram readability | Web-view 10-second readability | Keep/lower/delete decision | Next-day check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 2 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 3 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 4 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 5 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 6 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 7 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 8 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 9 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |
| 10 |  | mood / lunch / preclose / HH:MM |  | none / partial / strong; news / quote / freshness gap | KRX daily/index: helped / distracted / neutral; flow: helped / distracted / neutral; ETF: helped / distracted / neutral | direct / caution / market-context / none / waiting / stale | pass / revise | pass / revise | keep / lower / hide |  |

Daily read-only routine:

```powershell
python -m stock_monitor candidate-evidence-readiness --recent-report-dates 1 --stock-limit 20 --json
python -m stock_monitor market-briefing-readiness --recent-report-dates 1 --json
python -m stock_monitor market-briefing --date YYYY-MM-DD --layout realtime-first --json
python -m stock_monitor market-briefing --date YYYY-MM-DD --layout realtime-first
python -m stock_monitor data-source-lane-audit --json
python -m stock_monitor web-view-value-qa --date YYYY-MM-DD --stock-limit 20 --json
```

Routine limits:

- These commands are read-only review inputs.
- Do not use `--send`, scheduler registration, DB migration, or production source expansion for this checklist.
- If a command cannot run on the current PC, record the command, failure reason, and the nearest read-only substitute.

Minimum daily note:

```text
YYYY-MM-DD
- Slot / checked time:
- Top2:
- Current evidence:
  - same-day news: direct / caution / market-context / none / waiting / stale
  - current quote/turnover: present / absent / unavailable, source/time:
  - source freshness gap:
- Previous-day reference:
  - KRX daily/index: helped / distracted / neutral, why:
  - flow: helped / distracted / neutral, why:
  - ETF: helped / distracted / neutral, why:
- Telegram realtime-first preview: pass / revise, note:
- Web-view first 10 seconds: pass / revise, note:
- Tomorrow: keep / lower / hide:
- Next-day check:
```

Judgment rules:

- If current evidence is repeatedly useful, keep or raise it as top-2 primary evidence.
- If previous-day KRX, flow, or ETF repeatedly distracts, lower it further from the main top block.
- If news evidence is repeatedly empty, improve the empty/waiting UX before expanding automated collection.
- If reaction/backtest rarely changes operating judgment, isolate it as research/review only.
- If realtime-first preview is hard to read, shorten wording before adding another data lane.

## TODO Board Reinterpretation

Existing TODO2 items should not close from one clean command run. They should close only after the 10-business-day review log shows stable product judgment.

| Todo ID | Reinterpreted completion gate |
| --- | --- |
| `TODO2-TG-LIVE-DRYRUN` | No-send previews must use the new order: `오늘 볼 것 -> 현재 근거 -> 전일 참고 -> 부족한 근거 -> 복기/연구`. Close only after several days show readable Telegram output and no real-send approval gaps. |
| `TODO2-WV-CONTENT-QA` | Web-view QA must judge whether the first mobile viewport answers the top-2/current-evidence/gap question in 10 seconds. Browser smoke alone is not completion. |
| `TODO2-DATA-FRESHNESS-LIVE` | Freshness is not just exact/stale/missing correctness. Close only when stale KRX/flow stops dominating primary copy and current-source gaps are explicit. |
| `TODO2-NI-EVAL` | News quality evaluation must record whether direct/caution/no-match states changed the top-2 reading. Close only after false-positive and no-match cases are classified over operating samples. |

New stable ID:

| Todo ID | Goal | Done when |
| --- | --- | --- |
| `TODO2-RT-PRUNE` | Reposition public `web-view` and Telegram around realtime/current evidence first, with stored daily/reaction/backtest lowered. | The 10-business-day log supports the new ordering, and focused web-view/Telegram tests confirm public-safe wording and no score/trading leak. |

## Smallest Implementation Sequence

1. Document this plan and TODO interpretation.
2. Run existing read-only smoke/tests to confirm no behavior changed.
3. Over 10 business days, fill the operating checklist from previews and browser review.
4. Only after the log shows repeated distraction from stored/fallback blocks, make the smallest UI/text edit:
   - Rename or compress `데이터 기준`.
   - Move broad KRX/flow cards below top-2 current evidence.
   - Collapse `리포트 후 흐름` under `복기/연구`.
   - Reorder Telegram sections.
5. Add focused tests only for the exact wording/order change.

Skipped for this plan:

- No DB writes.
- No schema migration.
- No Telegram real send.
- No scheduler registration or change.
- No admin-gui process action.
- No broker/order route.
- No `x-browser-recap-lab` merge.
