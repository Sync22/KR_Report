# Experimental probes

This folder is for isolated probes only.

Current rule:

- Do not import these scripts from `src/stock_monitor`.
- Do not add experimental dependencies to `pyproject.toml`.
- Do not use this path from Task Scheduler scripts.
- Do not touch Naver main collection, Telegram, scheduler, or SQLite operation paths.

## Botasaurus legacy probe reference

Botasaurus is no longer the active maintained source-probe lane for this project. Keep the historical files here only as reference unless the user explicitly asks to restore Botasaurus work. The old local runtime `scripts\experimental\.venv-botasaurus` is not assumed to exist.

Historical runtime path:

```powershell
scripts\experimental\.venv-botasaurus
```

Install or verify with:

```powershell
scripts\experimental\.venv-botasaurus\Scripts\python.exe -m pip install -r scripts\experimental\requirements-botasaurus.txt
scripts\experimental\.venv-botasaurus\Scripts\python.exe scripts\experimental\probe_botasaurus_import.py
```

Historical bounded source probe:

```powershell
scripts\experimental\.venv-botasaurus\Scripts\python.exe scripts\experimental\botasaurus_source_probe.py
```

Do not use Botasaurus for new source probes by default. Use Scrapling unless there is an explicit restore request.

## Scrapling global source-probe runtime

Scrapling is installed globally as the preferred active source-probe tool:

```powershell
C:\Users\MING\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe
```

Start with Scrapling when a new or unstable source needs rendered-page extraction, browser-gated checks, or anti-bot-sensitive comparison. Keep probes bounded and record the target, command, observed result, and decision: `probe-only`, `fallback candidate`, or `later integration proposal`.

For CLI extraction commands, include `--ai-targeted`.

Safe first probe proposal for Naver stock news source discovery:

```powershell
C:\Users\MING\Codex\_tools\scrapling\.venv\Scripts\scrapling.exe extract fetch "https://stock.naver.com/news/mainnews" $env:TEMP\stock-monitor-naver-mainnews.md --ai-targeted --network-idle --wait 1500
```

After reading the temp output, delete it. Do not save provider responses into project data, do not connect Scrapling to DB writes, Telegram, Task Scheduler, `admin-gui`, or public `web-view`, and do not replace stable request/API paths unless a documented probe shows they are insufficient.

## Local Node tooling probes

`CodeGraph` and `codex-complexity-optimizer` were installed locally under:

```powershell
scripts\experimental\node_tooling
```

Useful report-only commands:

```powershell
scripts\experimental\node_tooling\node_modules\.bin\codegraph.cmd status .
scripts\experimental\node_tooling\node_modules\.bin\codegraph.cmd context "impact of changing candidate evidence ordering and backtest observation builders" -n 30 -c 4
python scripts\experimental\node_tooling\node_modules\codex-complexity-optimizer\complexity-optimizer\scripts\analyze_complexity.py src --format markdown
```

Notes:

- Keep node tooling local and ignored by git.
- Do not run the complexity optimizer installer against the real `CODEX_HOME`
  unless a deliberate skill install is wanted.
- Treat scanner output as leads; inspect code and run focused tests before any
  refactor.

## Kronos research-only environment

This lane is for offline experiments on stored KRX OHLCV only.

Hard boundary:

- Do not connect this to public score, recommendation, Telegram alert, or production automation.
- Do not fetch live market data from this path.
- Do not download model weights unless a separate research run explicitly asks for it.
- Use stored KRX OHLCV exports/snapshots only.

The local research virtual environment is:

```powershell
scripts\experimental\.venv-kronos
```

Historical install or verify commands:

```powershell
scripts\experimental\.venv-kronos\Scripts\python.exe -m pip install -r scripts\experimental\requirements-kronos.txt
scripts\experimental\.venv-kronos\Scripts\python.exe scripts\experimental\probe_kronos_import.py
```

Run a bounded stored-data backtest with:

```powershell
scripts\experimental\.venv-kronos\Scripts\python.exe scripts\experimental\kronos_backtest_experiment.py --from-date 2026-04-01 --to-date 2026-04-30 --horizon-days 10 --max-candidates 40 --lookback 120 --sample-count 1
```

Run the full stored 2026 report-candidate sweep in summary mode by changing
`--horizon-days` across `1`, `5`, `10`, and `20`:

```powershell
scripts\experimental\.venv-kronos\Scripts\python.exe scripts\experimental\kronos_backtest_experiment.py --from-date 2026-01-02 --to-date 2026-05-15 --horizon-days 10 --max-candidates 10000 --lookback 120 --sample-count 1 --summary-only
```

Notes:

- The first model run may download Hugging Face weights into `scripts/experimental/.hf-kronos`.
- The cache directory is local-only and ignored by git.
- Treat the output as an internal comparison artifact only; it must not become a public score, recommendation, Telegram alert, or scheduled production path.
- QuantDinger remains a Docker-based external research candidate. If Docker is not installed on this PC, record it as environment-required rather than wiring it into the project environment.
