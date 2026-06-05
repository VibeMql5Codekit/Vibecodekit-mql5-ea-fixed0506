---
id: 58-overfit
title: Overfit detection (OOS / IS Sharpe ratio)
tags: [overfit, robustness, walk-forward]
applicable_phase: B
---

# Overfit detection (OOS / IS Sharpe ratio)

`scripts/vibecodekit_mql5/overfit_check.py` parses two Strategy Tester
XML reports (in-sample + out-of-sample) and returns the
Sharpe-quality-retention ratio:

```
ratio = Sharpe_OOS / Sharpe_IS
```

A retention ratio close to 1.0 means OOS performance kept up with IS;
a ratio close to 0 means the IS fit dominated and the strategy is
unlikely to generalise.

## Threshold matrix

| Ratio range | Verdict | Exit code | Interpretation |
|---|---|---|---|
| `ratio ≥ 0.7`            | **PASS** | 0 | OOS retains ≥ 70 % of IS Sharpe — production-grade |
| `0.5 ≤ ratio < 0.7`      | **WARN** | 0 | acceptable for personal / paper; add walk-forward stress before scaling |
| `ratio < 0.5`            | **FAIL** | 1 | suspected overfit — reject or refit with fewer DoF |
| `Sharpe_IS ≤ 0`          | **FAIL** | 1 | IS itself is not profitable — ratio meaningless |

Thresholds are defined as `PASS_THRESHOLD = 0.7` and
`WARN_THRESHOLD = 0.5` in `overfit_check.py`. Bump them in a fork only
if you have a sample-size justification.

## CLI

```bash
python -m vibecodekit_mql5.overfit_check is.xml oos.xml
```

`is.xml` and `oos.xml` must be Strategy Tester reports parseable by
`backtest.parse_xml_report_file`. The script prints a `OverfitResult`
JSON document:

```json
{
  "is_sharpe": 1.62,
  "oos_sharpe": 1.21,
  "ratio": 0.747,
  "verdict": "PASS"
}
```

## Pairing with walk-forward

Use `mql5-walkforward` to *partition* the period into IS / OOS windows
(reproducibly), then feed the two resulting XML files into
`mql5-overfit-check`. The pipeline is:

```bash
python -m vibecodekit_mql5.walkforward is.xml oos.xml          # split metrics
python -m vibecodekit_mql5.overfit_check is.xml oos.xml        # Sharpe ratio
python -m vibecodekit_mql5.monte_carlo  returns.csv ...        # DD bootstrap
```

The three together cover the standard three-axis robustness audit
(temporal stability + return-distribution stability + drawdown
distribution stability) the kit's Trader-17 checklist expects.

## Test gate

`tests/gates/phase-B/test_overfit.py` exercises every threshold band
plus the `Sharpe_IS ≤ 0` fallback so the verdict logic is locked in
against regressions.
