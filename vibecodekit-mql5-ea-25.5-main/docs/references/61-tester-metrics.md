---
id: 61-tester-metrics
title: 14 canonical tester metrics
tags: [tester, metrics]
applicable_phase: B
---

# 14 canonical tester metrics

Plan v5 §B canonical 14 metrics surfaced by `backtest.py`:

1. NetProfit
2. ProfitFactor
3. RecoveryFactor
4. SharpeRatio
5. BalanceDDPercent
6. EquityDDPercent
7. Trades
8. WinRate
9. AverageWin
10. AverageLoss
11. ExpectedPayoff
12. LRCorrelation
13. ZScore
14. ConsecutiveLossesMax

`backtest.py` parses each from the MT5 XML report and exposes them as
attributes on `BacktestReport`.
