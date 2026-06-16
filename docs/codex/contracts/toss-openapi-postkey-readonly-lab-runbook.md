# Toss OpenAPI Post-Key Read-Only Lab Runbook

## Purpose

This runbook covers the first bounded Toss Securities OpenAPI validation after
client credentials have been issued.

It does not approve account, asset, order-info, order-history, order creation,
order modification, order cancellation, production DB writes, scheduler,
Telegram, `admin-gui`, or any `web-view` integration in main.

The active implementation remains a manual lab CLI:

```text
python -m stock_monitor toss-openapi-readonly-probe
```

The command is no-network by default. A live request requires all three gates:

1. `--live`
2. local `.env.toss-openapi` value `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`
3. `--confirm-token-reissue`

The third gate exists because official documentation says issuing a new token
invalidates the client's previously issued token.

## Official Basis

Verified on `2026-06-12` against:

- <https://developers.tossinvest.com/docs>
- <https://openapi.tossinvest.com/openapi-docs/latest/openapi.json>

Current official spec snapshot:

| Item | Value |
| --- | --- |
| OpenAPI version | `1.1.1` |
| Paths | `20` |
| Operations | `21` |
| Schemas | `53` |

## Local Key Input

Do not paste credentials into chat, source files, commands, screenshots, logs,
or test fixtures.

Add only the real values to the local ignored `.env.toss-openapi` file. Use
[.env.toss-openapi.example]({PROJECT_ROOT}/.env.toss-openapi.example) as the
field template:

```dotenv
STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID=
STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET=
STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=false
STOCK_MONITOR_TOSS_OPENAPI_BASE_URL=https://openapi.tossinvest.com
STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS=15
```

The general project `.env` is not the Toss credential input path.

Start with `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=false`. Change it to
`true` only for an explicitly reviewed manual probe, then return it to `false`
after the probe.

No Toss account sequence field is prepared yet. Account-context APIs remain
outside this lab profile.

## Allowed Endpoints

| CLI endpoint | Official operation | Required argument | Limit |
| --- | --- | --- | --- |
| `stocks` | `GET /api/v1/stocks` | one or two `--symbol` values | Reference only |
| `market-calendar-kr` | `GET /api/v1/market-calendar/KR` | optional `--date` | Calendar comparison only |
| `prices` | `GET /api/v1/prices` | one or two `--symbol` values | Intraday reference only |

The CLI has no account, asset, order-info, order-history, or order endpoint
selector.

## Plan-Only Checks

These commands do not read `.env`, issue a token, or call Toss:

```powershell
python -m stock_monitor toss-openapi-readonly-probe --endpoint stocks --symbol 005930 --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint market-calendar-kr --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint prices --symbol 005930 --json
```

Review that each output says:

- `mode=plan`
- `live_fetch=false`
- credentials are not read
- `writes_db=false`
- `sends_telegram=false`
- `registers_scheduler=false`
- `connects_admin_gui=false`
- `connects_web_view=false`

## First Live Validation

Run only after reviewing the plan and local `.env.toss-openapi` fields:

```powershell
python -m stock_monitor toss-openapi-readonly-probe --endpoint stocks --symbol 005930 --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint market-calendar-kr --live --confirm-token-reissue --json
python -m stock_monitor toss-openapi-readonly-probe --endpoint prices --symbol 005930 --live --confirm-token-reissue --json
```

Use one command at a time. Every live command issues a new token and can
invalidate a previously issued token.

The live output may include the selected market-reference result and rate-limit
headers. It must not contain client credentials or the access token.

## Safety Properties

- Credentials and live opt-in are accepted only from the dedicated local
  `.env.toss-openapi` file; process environment values do not activate it.
- Live credentials may be sent only to `https://openapi.tossinvest.com`.
- HTTP redirects are rejected before credentials or Bearer tokens can be
  forwarded to another origin.
- The default command does not read secrets or use network access.
- The direct client runner repeats the live-enable and token-reissue gates.
- The low-level token helper repeats the same live-enable and token-reissue
  gates.
- The low-level GET helper also requires explicit live enablement.
- The endpoint allowlist is immutable and revalidated immediately before GET.
- Query parameters are revalidated immediately before GET.
- Successful live responses must match the endpoint-level result container
  shape and contain only official allowlisted response fields. Available
  rate-limit headers are captured but are not assumed to be mandatory.
- Symbols are limited to two per probe.
- Results are printed only; no DB write path exists.
- No retry loop, scheduler task, Telegram send, admin route, or public route is
  connected.
- Account and order endpoint groups remain blocked.

## Stop Conditions

Stop the probe sequence and keep `LIVE_ENABLED=false` when:

- token issuance returns `400`, `401`, `403`, or `429`
- the response shape differs from the official spec
- rate-limit behavior is unexpected or returns `429`
- the key appears to include permissions beyond the reviewed market-reference
  scope
- any output contains a credential, token, account identifier, or order context

Do not continue to account or order APIs after a market-reference error.

## First Live Validation Evidence

Completed manually on `2026-06-12` with one-symbol read-only requests only.
No account header, account/asset/order endpoint, DB write, scheduler, Telegram,
`admin-gui`, or `web-view` connection was used.

| Check | Result |
| --- | --- |
| OAuth token issuance | Succeeded; token remained memory-only |
| `stocks` / `005930` | Succeeded; `STOCK` limit header reported `5` |
| `market-calendar/KR` | Succeeded; `MARKET_INFO` limit header reported `3` |
| `prices` / `005930` after KR market close | Succeeded; provider timestamp remained at the final after-market time |
| Historical separate-lab US probe | `AAPL` was used only for early provider validation; the main manual profile now accepts six-digit Korean stock codes only. |
| `MARKET_DATA` limit header | Reported `10`; requests were paced below the limit |
| Post-check state | Local `LIVE_ENABLED` returned to `false` |

This proves that the bounded `prices` probe can observe changing live market
values during an active market session. It does not approve continuous polling,
storage, account access, or execution. The only approved projection is the
main `web-view` top-2 priority current-price reference described below.

## Promoted Web-View Priority Quote Projection

The former lab preview was promoted to the main GET-only `web-view` in a
bounded form.

The normal `web-view` command can show Toss current-price references directly
in the existing top-two `우선 확인` rows when `.env.toss-openapi` has
credentials and `STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED=true`:

```powershell
python -m stock_monitor web-view --host 127.0.0.1 --port 8792 --no-open
```

- No extra Toss-specific CLI flag is required; `.env.toss-openapi` is the opt-in boundary.
- Uses the existing `web-view` host/access boundary plus server-derived
  top-2 symbols; it does not accept arbitrary public symbols.
- Adds the reference only to priority rows on the web-view.
- Fetches current prices only for the latest stored business date's top-two
  six-digit Korean stock codes. Historical dates do not call Toss.
- Recomputes and verifies the latest stored date's top-two priority codes on
  the server before calling Toss; arbitrary symbols are rejected.
- Fetches only when priority rows load or the operator manually refreshes them.
- Issues one memory-only token lazily on the first quote request. A `401`
  response permits one token reissue and one repeated GET for the server
  lifetime; no provider-specific error-code spelling or other automatic retry
  loop is assumed.
- Merges concurrent identical date/symbol requests so they produce one
  MARKET_DATA call.
- Reuses the same date/symbol response for 30 seconds. When Toss is
  unavailable, a successful response no older than 5 minutes may be returned
  with `cache=stale` and `stale_reason=upstream_unavailable`.
- Labels the value as `Toss 현재가`; it is not the selected historical date's price.
- Reuses the existing `데이터 기준` section to show `ready/current/disabled` and cache
  state after a successful quote response; it does not add a separate Toss screen.
- The normal `web-view` command exposes only the bounded top-2 quote reference route.
- Exposes no account, order, DB write, scheduler, Telegram, or admin control.
- It is public-safe only as current-price reference beside server-derived priority candidates.

## Verification Commands

```powershell
python -m pytest tests/test_toss_openapi.py tests/test_config.py -q
python -m pytest tests/test_cli_commands.py -q -k "data_source_lane_audit or toss_openapi_readonly_probe"
python -m pytest tests/test_web_view.py -q -k "toss_priority or toss_ready"
python -m stock_monitor data-source-lane-audit --json
```
