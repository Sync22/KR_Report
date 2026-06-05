# KRX Flow Sample Capture Runbook

This runbook fixes the manual capture process for KRX Data Marketplace investor-flow samples.
It is for validation only. Do not store credentials, cookies, tokens, or personal login payloads.

## Scope

| Screen | Purpose | Priority |
| --- | --- | --- |
| `[12009] 투자자별 거래실적(개별종목)` | Leadership-candidate stock-level investor flow | P0 |
| `[12008] 투자자별 거래실적` | Market-wide investor background | P1 |
| `[12010] 투자자별 순매수상위종목` | Net-buy ranking by investor category | P1 |

## Capture Steps

1. Run candidate preview for the target date.

```powershell
python -m stock_monitor krx-flow-candidates --date YYYY-MM-DD --limit 10
```

2. Confirm request params before touching KRX Data Marketplace.

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code STOCKCODE --request-only
python -m stock_monitor krx-flow-dry-run --view market --date YYYY-MM-DD --market STK --value amount --side net-buy --request-only
python -m stock_monitor krx-flow-dry-run --view top --date YYYY-MM-DD --market STK --investor foreign --request-only
```

3. Prefer raw `.env` login smoke-check before any live Data Marketplace validation.

```powershell
python -m stock_monitor krx-flow-login-check --date YYYY-MM-DD --market STK
```

This verifies login and the representative `[12008]` endpoint without DB writes.
If it fails with `LOGOUT` or `auth_rejected`, use Chrome only as fallback/debug.

4. If browser fallback is needed, open the operator Chrome session and log in to KRX Data Marketplace.

- Use the Chrome extension-connected browser when available.
- Keep only the JSON response body. Do not save headers, cookies, credentials, or screenshots containing account details.
- If `[12009]` shows `개별종목을 검색해주세요`, close the dialog, select the stock, confirm `STOCKCODE/종목명`, then query again.

5. Save raw JSON under `data/krx_samples`.

| Screen | Raw filename |
| --- | --- |
| `[12009]` | `12009_STOCKCODE_YYYYMMDD.local.json` |
| `[12008]` | `12008_market_YYYYMMDD.local.json` |
| `[12010]` | `12010_top_YYYYMMDD_INVESTOR.local.json` |

5. Generate or copy a manifest and fill the explicit conditions.

| Screen | Template |
| --- | --- |
| `[12009]` | `data/krx_samples/templates/12009_stock.manifest.template.json` |
| `[12008]` | `data/krx_samples/templates/12008_market.manifest.template.json` |
| `[12010]` | `data/krx_samples/templates/12010_top.manifest.template.json` |

Preferred capture-set scaffold command:

```powershell
python -m stock_monitor krx-flow-sample-scaffold --date YYYY-MM-DD --stock-code STOCKCODE --market STK --top-investor foreign
python -m stock_monitor krx-flow-sample-scaffold --date YYYY-MM-DD --from-candidates --candidate-limit 5 --market STK --top-investor foreign
```

This writes `[12009]` stock, `[12008]` market, and `[12010]` top-ranking manifest scaffolds together.
Use `--from-candidates` when local daily summary and KRX snapshot data already exist for the date.

Single-manifest scaffold command:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date YYYY-MM-DD --stock-code STOCKCODE --manifest-output data\krx_samples\12009_STOCKCODE_YYYYMMDD.manifest.local.json
```

6. Validate strictly and write a normalized artifact.

```powershell
python -m stock_monitor krx-flow-dry-run --date YYYY-MM-DD --sample-manifest data\krx_samples\MANIFEST.local.json --normalized-output data\krx_samples\NORMALIZED.local.json --strict-sample --show-first-row
```

7. After several manifests are captured, validate the batch before any ingest work.

```powershell
python -m stock_monitor krx-flow-capture-checklist --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized
python -m stock_monitor krx-flow-import-preview --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

`krx-flow-capture-checklist` converts manifests into an operator checklist: screen, condition, raw filename, manifest path, and validation command.
`krx-flow-sample-status` checks whether `[12008]`, `[12009]`, and `[12010]` manifests and sample files are present, then lists the next raw files to capture.
`krx-flow-validate-samples` performs no login, network call, or DB write. It fails if any manifest produces strict sample warnings unless `--allow-warnings` is explicit. Use `--normalized-dir` to write per-manifest normalized artifacts.
`krx-flow-import-preview` calculates the target SQLite investor-flow table row counts without writing rows.
`krx-flow-import-samples` writes rows only after explicit `--confirm --i-validated` and refuses samples with validation warnings.

## Visible Grid vs Raw Response Parity

The first imported `2026-05-08` sample set was captured from the logged-in visible grid DOM.
This is useful for user-facing validation, but scheduled ingest must not be enabled from visible-grid samples alone.

When raw-network response bodies are captured later, save them in a separate local directory such as `data\krx_samples_raw`.
Use the same manifest conditions and filenames whenever possible, then compare the normalized rows against the visible-grid baseline:

```powershell
python -m stock_monitor krx-flow-raw-sample-scaffold --source-manifest-dir data\krx_samples --output-dir data\krx_samples_raw
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples_raw
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples_raw --normalized-dir data\krx_samples_raw\normalized
python -m stock_monitor krx-flow-compare-samples --left-manifest-dir data\krx_samples --right-manifest-dir data\krx_samples_raw --allow-right-extra-top-rows
```

`krx-flow-raw-sample-scaffold` copies only manifest conditions from the visible-grid set and marks them as `capture_method=raw_network_response`.
It does not copy sample JSON files, so `krx-flow-sample-status` should report `sample=N` until raw response bodies are placed under `data\krx_samples_raw`.
`krx-flow-compare-samples` performs no login, network call, or DB write.
It compares normalized row values and ignores volatile fields such as fetch time/source.
Use `--allow-right-extra-top-rows` for `[12010]` because the visible grid can contain only rendered rows while the raw response contains the full ranked list. This option is valid only when visible rows match the raw rows as an ordered prefix.
If this command reports mismatches or missing manifests, keep broad scheduled ingest disabled and inspect the sample pair manually. The narrow same-day mentioned-stock `[12009]` task remains the only automatic exception.
For staged execution, treat raw body capture as `Stage 1`, strict raw validation as `Stage 2`, and visible-grid/raw parity comparison as `Stage 3` in [krx-flow-execution-stages.md](/docs/codex/details/krx/krx-flow-execution-stages.md).

## Promotion Criteria

| Check | Required |
| --- | --- |
| Raw response has rows | Yes |
| Normalized rows exist | Yes |
| Units are explicit | Yes |
| `[12009]`/`[12008]` includes expected investors | `외국인`, `기관합계`, `개인` |
| Normalized artifact has no quality warnings | Yes |
| Visible-grid and raw-network normalized rows match | Yes, before scheduled ingest |
| SQLite write performed | Manual local sample import only after `--confirm --i-validated`; broad scheduled ingest remains disabled except the narrow same-day mentioned-stock `[12009]` backfill task. |

## Current Blocker

Scheduled ingest remains blocked until real `[12008]`, `[12009]`, and `[12010]` raw response samples pass strict validation and parity comparison against the visible-grid samples.
