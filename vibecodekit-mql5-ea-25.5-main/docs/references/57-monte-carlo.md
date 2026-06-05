---
id: 57-monte-carlo
title: Monte Carlo bootstrap
tags: [monte-carlo, robustness, drawdown]
applicable_phase: B
---

# Monte Carlo bootstrap

`scripts/vibecodekit_mql5/monte_carlo.py` bootstraps the realised
trade-return series to estimate the distribution of *possible*
max-drawdowns the same edge would have produced under a different
trade ordering. The 95th percentile of that distribution — not the
single observed DD — is the honest budget figure to report.

## Sampling strategy

Default: **shuffle without replacement** of the realised return series,
then walk the equity curve and record max DD per simulation.

- Preserves the trade-return *distribution* — wins, losses, fat-tail
  events are unchanged.
- Breaks the *autocorrelation* between adjacent trades — appropriate
  for trade-by-trade evaluation, **not** bar-by-bar where serial
  correlation matters (use a block bootstrap there).
- Default `n_sims = 1000` shuffles; bump via `--n-sims` for tighter
  percentile estimates on small trade counts.

## CLI

```bash
python -m vibecodekit_mql5.monte_carlo returns.csv --reported-dd 8.2
```

Input CSV is one trade-return number per row in account currency or
percent (the analysis is unit-agnostic). `--reported-dd` is the
single-run max DD from the Strategy Tester XML; the script compares
it against the simulated distribution.

## JSON report schema

```json
{
  "n_sims": 1000,
  "p50_dd": 6.8,
  "p75_dd": 9.4,
  "p95_dd": 12.7,
  "reported_dd": 8.2,
  "verdict": "PASS"
}
```

## Acceptance rule

| Condition | Verdict | Exit code |
|---|---|---|
| `p95_dd ≤ 1.5 × reported_dd`  | **PASS** | 0 |
| `p95_dd  > 1.5 × reported_dd` | **FAIL** | 1 |

A `FAIL` means the observed DD was on the lucky tail of the
distribution — the realistic worst-case under the same edge is more
than 50 % deeper than what the single backtest reported. Either size
down, add a circuit-breaker, or reject the strategy.

## Determinism

`--seed <int>` is honoured for reproducible CI; the CLI default is
`--seed 42`, so two runs over the same returns CSV emit byte-identical
JSON. Test gate `tests/gates/phase-B/test_monte_carlo.py` pins both the
verdict logic and the seeded percentile output.
