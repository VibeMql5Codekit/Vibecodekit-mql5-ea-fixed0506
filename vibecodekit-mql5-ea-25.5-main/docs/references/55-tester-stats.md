---
id: 55-tester-stats
title: Strategy Tester core statistics
tags: [tester, statistics]
applicable_phase: B
---

# Strategy Tester core statistics

`TesterStatistics(ENUM_STATISTICS)` exposes 50+ metrics during
`OnTester`.  The kit's canonical set (see reference 61 for the full
14):

- `STAT_INITIAL_DEPOSIT`, `STAT_PROFIT`, `STAT_BALANCE_DD_PERCENT`
- `STAT_PROFIT_FACTOR`, `STAT_RECOVERY_FACTOR`
- `STAT_TRADES`, `STAT_PROFIT_TRADES`, `STAT_LOSS_TRADES`
- `STAT_SHARPE_RATIO`

Not all are populated for every run mode; `STAT_SHARPE_RATIO_OOS` does
not exist (see fitness templates / reference 64).
