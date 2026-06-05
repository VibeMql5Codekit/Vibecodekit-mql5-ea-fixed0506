---
id: 64-fitness-templates
title: OnTester custom fitness templates
tags: [fitness, ontester]
applicable_phase: B
---

# OnTester custom fitness templates

The kit ships 5 fitness templates under `fitness.py`:

1. `sharpe` — `STAT_SHARPE_RATIO` gated by trade count
2. `walkforward` — robustness-gated single-pass Sharpe
3. `recovery` — `STAT_RECOVERY_FACTOR`
4. `payoff` — `STAT_EXPECTED_PAYOFF`
5. `custom` — user-supplied expression

`walkforward` does **not** fabricate `STAT_SHARPE_RATIO_OOS` — the IS↔OOS
correlation is computed externally by `walkforward.py` against two
emitted XML reports.  See PR #7.
