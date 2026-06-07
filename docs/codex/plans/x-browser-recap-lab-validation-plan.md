# X Browser Recap Lab Validation Plan

## Purpose

Validate whether the existing no-login X browser recap probe is useful for operator-only recap experiments.

This plan does not implement a production X monitor. It keeps browser-based X access in the lab lane and uses it only to learn:

- whether public posts can be extracted consistently enough for recap review
- whether 30-minute or 1-hour recap windows are understandable
- whether stance labels such as `positive`, `negative`, `caution`, `neutral`, and `mixed` can be assigned without drifting into trading advice

The long-term production source candidate is the official X API, not browser scraping. Browser probe results must not be wired into production DB writes, Telegram automation, scheduler tasks, `admin-gui`, or public `web-view`.

## Current Baseline

The repository already has a lab command:

```powershell
python -m stock_monitor x-browser-recap-probe --handle HANDLE --date YYYY-MM-DD --limit 20 --scrolls 3 --format json
```

Current command properties:

- isolated no-login browser context
- no X API use
- no persistent browser profile
- no saved cookies
- no `.env` or secret reads
- no DB writes
- no Telegram sends
- no scheduler registration
- no `admin-gui` or `web-view` connection
- optional diagnostic screenshot directory only when explicitly passed
- profile URLs may include a `lang` query such as `?lang=ko`; this is preserved because no-login X rendering can differ by language URL

Workspace note:

- In the `_x_recap` workspace, the default `python -m stock_monitor` import may resolve to the previously installed `C:\Users\MING\Codex\02.Stock_Moniter` package.
- For this copied workspace, pin the current source tree before running lab commands:

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
```

Focused regression check:

```powershell
python -m pytest tests/test_cli_commands.py -k x_browser_recap -q
```

## Scope

Allowed in this lab validation:

- manually run `x-browser-recap-probe` for operator-specified public handles
- capture JSON output to terminal for immediate review
- optionally save local lab JSON snapshots under an operator-managed `data/lab/x_recap/` path for short-term comparison
- optionally save screenshots only for diagnosing login walls, empty renders, or blocked pages
- manually compare 30-minute and 1-hour recap windows
- build a text-only lab recap preview after extraction reliability is understood

Blocked in this lab validation:

- production SQLite writes
- production `reports`, `daily_stock_summaries`, or news intelligence tables
- Telegram sends or Telegram candidate alerts
- Windows Task Scheduler registration or unattended looping
- `admin-gui` controls or status cards
- public `web-view` projection
- broker API, order routing, or execution-lab connection
- public numeric scores, investment grades, buy/sell labels, target return, conviction, entry, exit, or take-profit wording
- use of a logged-in X browser profile, saved cookies, access tokens, or private/protected account content

## Tool Classification

| Tool | Class | Use |
| --- | --- | --- |
| Existing `x-browser-recap-probe` CLI | lab | Public no-login reachability and extraction checks. |
| Playwright runtime | lab | Headless rendering only through the existing probe. |
| Screenshot diagnostics | lab | Debug login wall, empty render, or page block states. |
| Official X API | production candidate, not part of this plan | Future approved source lane after API key, cost, policy, and rate-limit review. |
| Telegram | hold | No sends until extraction, recap quality, review gates, and replay safety are separately approved. |
| Scheduler | hold | No unattended loop until a production source and manual review gate exist. |
| `web-view` | hold | No public projection from lab browser output. |
| `admin-gui` | hold | No operations card until the lane becomes an approved operator workflow. |

## Probe Matrix

The first validation pass should use a small operator-supplied handle list.

Recommended bounds:

- handles: 2 to 5 public accounts
- dates: operator-selected calendar date; for market recaps, prefer the latest Korean market day plus one recent prior market day
- run slots: market open window, lunch window, near close window, and after close
- repeated runs: at least 3 runs per handle/date before interpreting extraction stability
- limit: 20 posts per run
- scrolls: 3 by default, then 1 and 5 for sensitivity checks if needed

Example manual commands:

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
python -m stock_monitor x-browser-recap-probe --profile-url 'https://x.com/HANDLE?lang=ko' --date 2026-06-07 --limit 20 --scrolls 3 --format json
python -m stock_monitor x-browser-recap-probe --profile-url 'https://x.com/HANDLE?lang=ko' --date 2026-06-07 --limit 20 --scrolls 3 --format text
python -m stock_monitor x-browser-recap-probe --profile-url 'https://x.com/HANDLE?lang=ko' --date 2026-06-07 --limit 20 --scrolls 3 --format json --screenshot-dir data/lab/x_recap/screenshots
```

Lab snapshots, if saved, should not be committed. They may contain third-party post text and should be treated as local review artifacts.

## Failure Taxonomy

Each run should be classified with the existing probe output first:

| State | Meaning | Next action |
| --- | --- | --- |
| `post_count > 0` | Public posts were extracted. | Review timestamp, URL, text quality, and date filter accuracy. |
| `login_required` | X rendered a login wall. | Keep as failed reachability evidence. Do not add login automation. |
| `blocked_or_unavailable` | Page rendered a block or temporary restriction. | Retry manually later; do not increase automation pressure. |
| `no_public_posts_found` | Page rendered but no parsable public posts matched. | Check handle, date, scroll count, and screenshot if available. |
| `playwright_unavailable` | Lab runtime is missing Playwright. | Fix local lab runtime only; no production change. |
| `browser_probe_failed` | Browser launch/navigation failed. | Record local error and retry manually. |

Do not convert missing posts into negative market evidence. Missing posts are source coverage failure only.

## Recap Semantics

The recap labels describe the author's stated market view, not whether the view is correct.

| Label | Meaning |
| --- | --- |
| `positive` | The post frames a market, sector, or stock condition as supportive or improving. |
| `negative` | The post frames downside, weakness, deterioration, or risk as dominant. |
| `caution` | The post emphasizes uncertainty, risk control, crowded positioning, unclear confirmation, or watch-only framing. |
| `neutral` | The post is descriptive, factual, or does not express a clear stance. |
| `mixed` | The post contains both supportive and cautionary views in the same recap window. |

Allowed recap language:

- `복기`
- `관찰`
- `시장 관점`
- `놓친 포인트`
- `확인 필요`
- `주의`
- `강화`
- `약화`
- `중립`

Blocked recap language:

- `매수 추천`
- `매도 추천`
- `매수 기회`
- `전략 제안`
- `진입가`
- `청산가`
- `익절가`
- `목표 수익률`
- `확신도`
- `투자등급`
- public numeric `점수`

## Validation Phases

### Phase 1: Reachability

Run the existing probe manually for the handle/date matrix.

Done when:

- each handle has at least 3 recorded run outcomes
- success and failure states are explainable
- no run reads secrets, uses a logged-in browser, writes DB rows, sends Telegram, or registers scheduler tasks

### Phase 2: Extraction Quality

Review successful JSON outputs.

Done when:

- extracted `published_at`, `published_date`, `url`, and `text` are present where X renders them
- duplicate posts are not repeated within one run
- the KST `--date` filter behaves as expected
- retweets, replies, or quote posts are either accepted as visible profile content or explicitly excluded in a later design

### Phase 3: Window Recap Preview

Manually group extracted posts into 30-minute and 1-hour windows.

Done when:

- a human can understand the author's main points from the compressed text
- each label is traceable to one or more source posts
- `positive` or `negative` labels do not become buy/sell advice
- empty windows are shown as `작성글 없음` or `수집 실패`, not as neutral market evidence

### Phase 4: Production Decision Gate

Decide whether to stop, continue lab-only, or design an official X API lane.

Browser probe may continue as lab tooling only.

Production discussion requires a separate design covering:

- official X API credentials and cost controls
- API rate limits and usage monitoring
- token storage and secret handling
- DB schema and dedupe policy
- retention policy for third-party post text
- Telegram replay safety
- scheduler windows and failure behavior
- operator-only wording and legal/product boundary

## Success Criteria

The lab pass is successful when:

- the probe can classify each target account as reachable, login-walled, blocked, or empty
- successful runs extract enough post text for a human recap on at least several sampled windows
- 30-minute versus 1-hour windows can be compared without changing production behavior
- stance labels are understandable and source-backed
- no output crosses into trading recommendation or public scoring
- focused tests continue to pass

The lab pass is not successful when:

- most target accounts hit login walls or blocking
- extracted post text is too incomplete for recap
- timestamps are missing often enough that windowing is unreliable
- recap labels cannot be assigned without guessing
- the workflow depends on logged-in browser state, cookies, or private account content

## Verification Commands

Run before and after any code changes to the existing probe:

```powershell
python -m pytest tests/test_cli_commands.py -k x_browser_recap -q
```

Run for manual lab evidence after the operator supplies handles:

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
python -m stock_monitor x-browser-recap-probe --profile-url 'https://x.com/HANDLE?lang=ko' --date YYYY-MM-DD --limit 20 --scrolls 3 --format json
```

Run with screenshots only when diagnosing source access:

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
python -m stock_monitor x-browser-recap-probe --profile-url 'https://x.com/HANDLE?lang=ko' --date YYYY-MM-DD --limit 20 --scrolls 3 --format json --screenshot-dir data/lab/x_recap/screenshots
```

## Residual Risks

- X can change rendering, require login, block automation, or hide public timelines at any time.
- Browser probing may be inconsistent across IP, time, account, region, or X rollout bucket.
- Screenshots and JSON outputs may contain third-party post text; keep them local and avoid committing them.
- Stance labels can overstate meaning if the source post is sarcastic, threaded, or context-dependent.
- This lane cannot support investment advice, public recommendations, or execution decisions.
- Production use should move to the official X API after a separate policy, cost, and security review.

## Current Next Step

Ask the operator for the initial handle list and target validation date.

Use this exact prompt:

```text
X no-login browser recap lab 검증을 시작하려면 공개 계정 handle 2~5개와 기준 날짜를 주세요.
예: @account1, @account2 / 2026-06-07
이번 단계는 DB 저장, Telegram 발송, scheduler 등록 없이 수동 probe 결과만 확인합니다.
```
