# Manual X Recap Telegram Preview Plan

## Purpose

Define a manual browser analyst workflow for X account recaps and add a safe preview-only CLI that formats manually reviewed posts into Telegram-ready text.

This is not an automatic X monitor. It does not collect X in the background, send Telegram messages, register scheduler tasks, write SQLite rows, or expose anything through `admin-gui` or public `web-view`.

## Operating Mode

`manual browser analyst mode` means:

- the operator opens a logged-in browser session
- Codex reads only visible pages after the operator has logged in
- Codex may scroll, inspect visible text, and click long posts for detail
- Codex does not enter credentials, 2FA, cookies, tokens, or secrets
- Codex does not like, repost, follow, comment, DM, change settings, or save screenshots by default
- the operator explicitly asks for each recap session

Operator shortcut phrase:

```text
수동복기준비
```

When the operator says `수동복기준비`, interpret it as:

```text
X 수동 복기 준비해줘.
먼저 https://x.com/home 또는 대상 계정으로 이동해서 로그인 상태만 확인해줘.
로그인되어 있으면 멈추고 알려줘.
로그인 필요하면 로그인 화면까지만 열어줘. 로그인은 내가 직접 할게.
```

This shortcut is only preparation. It does not authorize reading posts, scrolling, clicking long posts, generating a recap, sending Telegram, or running any repeated automation.

Recommended behavioral bounds:

- one session is at most 10 to 15 minutes
- check 1 to 3 accounts per session
- wait 5 to 20 seconds between scrolls when practical
- wait 20 to 60 seconds after opening a long post when practical
- review at most 10 to 20 posts per session
- do not run automatic repeated polling

## Recap Slots

All times are KST.

| Slot | Range | Intended Telegram timing | Meaning |
| --- | --- | --- | --- |
| `preopen` | Previous day `20:00` to target day `08:00` | Around `08:00` to `08:20` | Overnight risk, macro, and event context before the Korean market opens. |
| `midday` | Target day `08:00` to `12:00` | Around `12:00` to `12:20` | Pre-open and morning-session view changes. |
| `close` | Target day `12:00` to `16:00` | Around `16:00` to `16:20` | Afternoon and close-prep view changes. |

Empty 30-minute windows do not need to be printed. If a recap has sparse posts, the operator may read it as a 1-hour-level summary even when the source grouping uses 30-minute buckets.

## Manual Input Contract

The preview command expects an operator-prepared JSON object. The preferred flat shape is:

```json
{
  "posts": [
    {
      "handle": "admi_alts",
      "published_at": "2026-06-07T20:10:00+09:00",
      "url": "https://x.com/admi_alts/status/1",
      "summary": "야간선물 급락 가능성을 열어두되 동반 투매보다 시나리오 대응을 강조.",
      "stance": "caution",
      "market_related": true,
      "is_reply": false,
      "is_repost": false
    }
  ],
  "questions": [
    "반도체 이벤트가 실제 시초가 방어로 이어지는지 확인"
  ]
}
```

Allowed post fields:

| Field | Meaning |
| --- | --- |
| `handle` | X handle without or with `@`; output normalizes to `@handle`. |
| `published_at` | ISO datetime. KST offset is preferred. |
| `url` | Source status URL for traceability. |
| `summary` | Operator-written recap sentence. Preferred over raw post text. |
| `text` | Fallback raw or compressed post text when `summary` is absent. |
| `stance` | `positive`, `negative`, `caution`, `neutral`, or `mixed`. |
| `market_related` | Set `false` to exclude non-market posts. |
| `is_reply` | Set `true` to exclude replies. |
| `is_repost` | Set `true` to exclude reposts. |

The command also accepts an account-grouped shape:

```json
{
  "accounts": [
    {
      "handle": "admi_alts",
      "posts": [
        {
          "published_at": "2026-06-07T20:10:00+09:00",
          "summary": "야간선물 급락 가능성을 열어두되 동반 투매보다 시나리오 대응을 강조.",
          "stance": "caution",
          "market_related": true
        }
      ]
    }
  ]
}
```

## Preview Command

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
python -m stock_monitor manual-x-recap-preview --input data/lab/x_recap/manual_posts.json --date 2026-06-08 --slot preopen --window-minutes 30 --format text
```

JSON output:

```powershell
$env:PYTHONPATH='C:\Users\MING\Codex\02.Stock_Moniter_x_recap\src'
python -m stock_monitor manual-x-recap-preview --input data/lab/x_recap/manual_posts.json --date 2026-06-08 --slot preopen --window-minutes 30 --format json
```

Command guarantees:

- `writes_db=false`
- `sends_telegram=false`
- `registers_scheduler=false`
- `connects_web_view=false`
- `read_only=true`

The command exits with `1` if the generated preview contains blocked public-safety terms.

## Output Shape

The text output is intended for operator review or manual Telegram copy:

```text
X 관찰 복기 · 장 시작 전 · 26.06.08
범위: 06.07 20:00~06.08 08:00 KST
방식: manual browser analyst / no automation

계정별 관점
@admi_alts
- 라벨: caution
- 야간선물 급락 가능성을 열어두되 동반 투매보다 시나리오 대응을 강조.

시간대별
20:00-20:30
- @admi_alts [caution] 야간선물 급락 가능성을 열어두되 동반 투매보다 시나리오 대응을 강조.

다음 확인 질문
- 반도체 이벤트가 실제 시초가 방어로 이어지는지 확인
```

## Wording Boundary

Allowed:

- `복기`
- `관찰`
- `시장 관점`
- `놓친 포인트`
- `확인 필요`
- `주의`
- `강화`
- `약화`
- `중립`
- `우선 확인`

Blocked:

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

## Deferred Work

Keep these out of the first implementation:

- direct Telegram send
- scheduler task
- automatic browser polling
- DB persistence
- public `web-view` projection
- account count beyond the operator's manual review capacity

The next safe step after preview is a separate `manual-x-recap-send` design where the operator explicitly approves one Telegram send after reviewing the generated text.

## Future Operator Control Surface

After the preview path is more complete, a click-based control surface is reasonable for operator use. Keep it out of the friend-facing `web-view`; that surface remains GET-only/read-only. The safer shape is an `admin-gui` or local operator-only page that can:

- select date, slot, account set, and window size
- load operator-prepared manual JSON
- render preview text and message safety issues
- require explicit approval before any future one-shot Telegram send

Do not add unattended polling, scheduler registration, or public recap projection as part of this control surface.
