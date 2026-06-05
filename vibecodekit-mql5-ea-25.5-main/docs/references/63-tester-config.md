---
id: 63-tester-config
title: tester.ini configuration
tags: [tester, config]
applicable_phase: B
---

# tester.ini configuration

`tester.ini` controls every Strategy Tester run.  Key keys:

- `Expert` — EA name (without `.ex5`)
- `Symbol`, `Period`
- `FromDate`, `ToDate`
- `ForwardMode` (0 = none, 1 = 1/2, 2 = 1/3, 3 = 1/4, 4 = custom)
- `Model` (0 = every tick, 1 = 1-min OHLC, 2 = open prices, 3 = math
  calc, 4 = every tick based on real ticks)
- `Optimization` (0 = none, 1 = slow complete, 2 = Cloud Network,
  3 = fast genetic)
- `OptimizationCriterion` — enum 0..6 (see `cloud_optimize.py`)

`backtest.py` emits a tester.ini matching the kit's defaults — see
`render_tester_ini()` in `scripts/vibecodekit_mql5/backtest.py`. The
emitted ini always sets `ShutdownTerminal=1` and `ReplaceReport=1` so
a headless driver can poll the report file deterministically.

## Driving the tester end-to-end — `tester_run.py`

`scripts/vibecodekit_mql5/tester_run.py` is the W8 driver that
actually invokes `terminal64.exe` (Wine on Linux, native on Windows)
with the rendered ini, then parses the XML report. It is exposed as
the `mql5-tester-run` console script.

```bash
mql5-tester-run MyEA.ex5 default.set \
    --symbol EURUSD --period 2024.01.01-2024.12.31 --tf H1 \
    --report ./tester.xml --timeout 600
```

Resolution order for the terminal binary:

1. `--terminal /abs/path/terminal64.exe` on the CLI.
2. `$MQL5_TERMINAL_PATH` environment variable.
3. `$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe`
   on Linux (Wine).
4. `C:\Program Files\MetaTrader 5\terminal64.exe` and the (x86)
   variant on Windows.

When nothing is found the driver exits with code 3 and prints the full
probe list so the operator can see exactly which paths were tried.

Exit-code matrix (`tester_run.main`):

| Code | Meaning |
|------|---------|
| 0    | XML parsed; JSON `BacktestResult` printed to stdout |
| 1    | XML exists but does not parse |
| 2    | invocation error (bad args / period) |
| 3    | `terminal64.exe` not found |
| 4    | terminal launched but did not produce the report within timeout |

Pass `--print-ini-only` to render the `tester.ini` and exit without
launching the terminal — useful in CI for snapshot-testing the ini
contents.
