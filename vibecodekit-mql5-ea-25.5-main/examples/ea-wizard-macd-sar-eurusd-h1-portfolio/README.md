---
id: worked-example
title: Worked example — MACD+SAR EURUSD H1 wizard-composable portfolio
applicable_phase: E
mode: enterprise
turnaround_hours: 4
---

# Worked example — MACD+SAR EURUSD H1 wizard-composable portfolio

Full Plan v5 §19 8-step walk-through.  Enterprise-mode turnaround on a
fresh Devin VM (Wine 8.0.2 + MetaEditor build 5260+): **4 hours**.

## Step 1 — SCAN

```
$ python -m vibecodekit_mql5.scan ~/projects/eurusd-portfolio
```

Result: empty project tree.  Time: 5 minutes.

## Step 2 — RRI

```
$ python -m vibecodekit_mql5.rri.step_workflow --mode enterprise
```

Walked 6 personas × 25 questions = 150 questions (ENTERPRISE).
Answered in 90 minutes.  Outputs `docs/rri-report.md`.

## Step 3 — VISION

Filled `docs/rri-templates/step-3-vision.md.tmpl`:

- **Hypothesis**: MACD-signal-cross gated by Parabolic-SAR
  flip captures H1 trend continuation on EURUSD with R:R ≥ 1.5.
- **Scope**: single symbol, single timeframe, netting account.
- **Out of scope**: hedging, multi-symbol, news filter.

## Step 4 — BLUEPRINT

`docs/rri-templates/step-4-blueprint.md.tmpl` filled:

- **Signal**: MACD(12,26,9) + SAR(0.02, 0.2) — fixed at vetted values,
  not exposed to the optimiser (AP-5 cap = 6 inputs total).
- **Inputs (6)**: `InpMagic`, `InpRiskPerTradePct`, `InpDailyLossPct`,
  `InpMaxPositions`, `InpMaxSpreadPips`, `InpSlPips`.
- **Sizing**: `CPipNormalizer.LotForRisk(risk_money, InpSlPips)` with
  0.5% risk-per-trade.
- **Risk**: 2% daily-loss cap + 1 max-position + 5% drawdown freeze.
- **Guard**: `CSpreadGuard` 3-pip cap.
- **Session filter**: weekend gap + NFP window (first-Fri 13:30–14:30).
- **Stop-loss**: 40-pip protective stop on every entry (AP-1).
- **Observability**: `CMfeMaeLogger` per trade + `PrintFormat` on
  every entry (Trader-17 `journal_observable`).

## Step 5 — TIP

8 TIPs identified (cross-referenced against `docs/anti-patterns-AVOID.md`):

1. AP-1: pip-normalise via `CPipNormalizer.Init(_Symbol)` (✅ wired)
2. AP-3: no while-loop on `IsTesting()` (✅ N/A)
3. AP-5: SL set every trade (✅ wired via CTrade)
4. AP-12: indicator handles released in `OnDeinit` (✅ wired)
5. AP-15: trade.SetExpertMagicNumber called (✅ wired)
6. AP-17: no WebRequest in OnTick (✅ N/A)
7. AP-18: no OrderSendAsync without handler (✅ N/A)
8. AP-21: no method-hiding (✅ checked by `method_hiding_check`)

## Step 6 — BUILD

```
$ python -m vibecodekit_mql5.build wizard-composable \
    --stack netting --name MacdSarEurUsdH1 \
    --symbol EURUSD --tf H1
```

Generates `EAName.mq5` (see this directory).  Magic number is derived
deterministically from `--name` (see `build._magic_for`).  Time: 5
minutes.

## Step 7 — VERIFY (multi-stage 9 commands)

```bash
python -m vibecodekit_mql5.compile EAName.mq5
python -m vibecodekit_mql5.lint EAName.mq5
python -m vibecodekit_mql5.method_hiding_check EAName.mq5 --build 5260
python -m vibecodekit_mql5.backtest --ea MacdSarEurUsdH1 --symbol EURUSD --period H1
python -m vibecodekit_mql5.walkforward --is is.xml --oos oos.xml
python -m vibecodekit_mql5.monte_carlo --report results/backtest.xml --sims 1000
python -m vibecodekit_mql5.overfit_check --is is.xml --oos oos.xml
python -m vibecodekit_mql5.multibroker --ea MacdSarEurUsdH1
python -m vibecodekit_mql5.trader_check EAName.mq5 --mode enterprise
```

All 9 must return exit 0.  Time: ~2 hours wall (most of it backtest +
walk-forward + Monte Carlo).

## Step 8 — REFINE + ship

```
$ python -m vibecodekit_mql5.refine --diff <(git diff main..HEAD)
$ python -m vibecodekit_mql5.ship --tag v1.0.1
```

`refine` classifies the diff as `patch` (logic-bounded change to one
EA file).  `ship` tags + pushes.  Time: 5 minutes.

## Turnaround summary

| Step | Wall time |
|------|-----------|
| 1. SCAN        | 5 min  |
| 2. RRI         | 1.5 h  |
| 3. VISION      | 15 min |
| 4. BLUEPRINT   | 30 min |
| 5. TIP         | 20 min |
| 6. BUILD       | 5 min  |
| 7. VERIFY      | 2 h    |
| 8. REFINE+SHIP | 5 min  |
| **Total**      | **~4 hours** |

PERSONAL mode skips Steps 2-5 + Layers 5-6, completing in ~1.5 hours.
TEAM mode runs an abbreviated Step 2 (72 questions) + Layers 1-5,7 in
~2.5 hours.

## Artefacts

See `results/` for the generated artefacts (backtest XML, multibroker
CSV, canary log, 64-cell matrix HTML).
