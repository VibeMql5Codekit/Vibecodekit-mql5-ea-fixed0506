# Phase B Spec — Test & Validation

> ⚠️ **Internal / contributor document.** Sprint spec for this kit's own development — not user-facing. See [`README.md`](../README.md) and [`docs/QUICKSTART.md`](QUICKSTART.md) instead.

**Goal:** Strategy Tester wrapper + walk-forward + multi-broker stability + Trader-17 + VPS deploy.
**Duration:** 3 weeks.
**Tag on completion:** v0.2.0.
**Prereq:** v0.1.0.

## Files added in Phase B

```
Include/
├── CMfeMaeLogger.mqh                         # per-trade MFE/MAE CSV logger
└── CSpreadGuard.mqh                          # spread check before OrderSend

scripts/vibecodekit_mql5/
├── backtest.py                               # /mql5-backtest (XML parser)
├── walkforward.py                            # /mql5-walkforward (Forward 1/4)
├── monte_carlo.py                            # /mql5-monte-carlo (bootstrap)
├── overfit_check.py                          # /mql5-overfit-check
├── multibroker.py                            # /mql5-multibroker (orchestrator)
├── trader_check.py                           # /mql5-trader-check (17-point)
├── deploy_vps.py                             # /mql5-deploy-vps
├── mfe_mae.py                                # /mql5-mfe-mae (analyzer)
├── fitness.py                                # /mql5-fitness (5 templates)
└── broker_safety.py                          # Layer 7 standalone

tests/
├── gates/phase-B/
│   ├── test_phase_b_acceptance.py            # 6 e2e tests
│   ├── test_backtest_xml_parser.py           # 8 unit
│   ├── test_walkforward.py                   # 6 unit
│   ├── test_monte_carlo.py                   # 4 unit
│   ├── test_overfit.py                       # 3 unit
│   ├── test_multibroker.py                   # 5 unit
│   └── test_trader_check.py                  # 4 unit
└── fixtures/
    ├── tester_report_eurusd_h1.xml
    ├── tester_report_xauusd_h1_3d.xml
    └── tester_report_usdjpy_h1.xml
```

## 36 tests (acceptance gate)

### 6 e2e tests
1. `test_backtest_xml_parser_3_reports`
2. `test_walkforward_IS_OOS_extract`
3. `test_monte_carlo_DD_percentile`
4. `test_overfit_check_OOS_ratio`
5. `test_multibroker_rejects_hardcoded_EA`
6. `test_multibroker_passes_normalized_EA` (real demo accounts required)

### 30 unit tests
- 8 backtest (XML parser, ini gen, period parser)
- 6 walkforward (Forward 1/4 mode, IS/OOS extract)
- 4 monte_carlo (bootstrap, 50/75/95 percentile)
- 3 overfit (ratio compute, threshold)
- 5 multibroker (orchestrator, stability metrics, journal verify)
- 4 trader_check (17-point individual checks subset)

## Multi-broker test (test 5 e2e) — requires user secrets

Devin must request via secrets tool:
- `FXPRO_DEMO_LOGIN`, `FXPRO_DEMO_PASSWORD`, `FXPRO_DEMO_SERVER`
- `EXNESS_DEMO_LOGIN`, `EXNESS_DEMO_PASSWORD`, `EXNESS_DEMO_SERVER`
- `ICMARKETS_DEMO_LOGIN`, `ICMARKETS_DEMO_PASSWORD`, `ICMARKETS_DEMO_SERVER`

Multi-broker stability tolerance:
- PF stdev / mean ≤ 0.30
- Sharpe stdev ≤ 0.20
- DD diff (max - min) ≤ 5%

## Trader-17 checklist (must implement all 17)

See Plan v5 §8 for full list. `trader_check.py` returns dict:
```python
{
    "sl_set_every_trade": "PASS",
    "lot_risk_based": "PASS",
    "magic_reserved_unique": "PASS",
    ...  # 14 more
    "_summary": "15/17 PASS, 1 WARN, 1 N/A"
}
```

## Acceptance gate

- [ ] v0.1.0 merged
- [ ] 36/36 tests pass (Linux + Windows)
- [ ] Real multi-broker test passes with FxPro + Exness + ICMarkets
- [ ] audit clean
- [ ] All modules < 200 LOC
- [ ] `git tag v0.2.0` after merge
