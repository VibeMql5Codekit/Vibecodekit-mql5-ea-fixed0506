---
id: 73-cloud-network
title: Cloud Network optimisation
tags: [cloud, optimization, tester]
applicable_phase: D
---

# Cloud Network optimisation

`Optimization=2` in `tester.ini` routes the optimisation pass across
the MetaQuotes Cloud Network — anonymous, geo-distributed agents that
run a copy of MT5 and return results. Pricing per docs.mql5.com
(2024-10): **0.001 USD per agent-second**.

## CLI — `mql5-cloud-optimize`

```bash
python -m vibecodekit_mql5.cloud_optimize MyEA \
    --mode enterprise --passes 5000 --seconds-per-pass 4 \
    --budget-usd 25.0 --output-ini tester.ini
```

The positional `ea` is the EA name (no path, no extension); the cost
report prints to stdout regardless, and `--output-ini` is only honoured
if the budget gate passes.

`scripts/vibecodekit_mql5/cloud_optimize.py` computes
`estimated_cost = passes × seconds_per_pass × 0.001 USD` and refuses
to emit `tester.ini` if the cost exceeds `--budget-usd`. It also
respects the mode gate:

| Mode | Cloud allowed? | Default budget | Override |
|---|---|---|---|
| `personal`   | ❌ REJECT             | $0    | not allowed — local-only |
| `team`       | ✓ default cap $5    | $5    | `--budget-usd` may raise |
| `enterprise` | ✓ default cap $50   | $50   | `--budget-usd` required (no implicit ceiling) |

The PERSONAL gate is a hard refusal — paid Cloud time and a free
single-developer workflow are mutually exclusive in Plan v5 §13.

## tester.ini template (emitted)

`tester.ini` follows the format MetaTerminal expects (capitalised
keys, no spaces around `=`):

```ini
Optimization=2                  ; 2 = Cloud Network
OptimizationCriterion=0         ; 0 = Balance max (configurable)
Symbol=EURUSD
Period=H1
FromDate=2024.01.01
ToDate=2024.12.31
Expert=MyEA
Model=1                         ; 1 = 1-minute OHLC
ExecutionMode=0                 ; 0 = retail-broker friendly
Visual=0
```

`OptimizationCriterion` accepts the standard 0–6 MT5 enum (Balance
max, Profit Factor max, Expected Payoff max, Drawdown min, Recovery
max, Sharpe max, Custom OnTester); `cloud_optimize.py` defaults to 0
(Balance max).

## Cost report (JSON)

Every successful emit also prints a `CostReport`:

```json
{
  "ok": true,
  "mode": "enterprise",
  "budget_usd": 25.0,
  "estimated_cost_usd": 20.0,
  "estimated_seconds": 20000,
  "passes": 5000
}
```

`ok: false` reports the breach reason in `error` so CI can fail with a
specific message rather than a generic non-zero exit.

## Region note

The Cloud Network does not let you pin agents to a region; the
estimator therefore does not model latency-sensitive criteria. For
latency-sensitive HFT optimisations use a single co-located VPS
instead — see `74-vps.md`.
