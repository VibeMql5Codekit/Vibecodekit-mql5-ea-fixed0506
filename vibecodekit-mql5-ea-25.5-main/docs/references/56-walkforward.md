---
id: 56-walkforward
title: Walk-forward methodology
tags: [walkforward, robustness]
applicable_phase: B
---

# Walk-forward methodology

Walk-forward partitions the test window into chunks and
re-optimises on each in-sample (IS) slice, then evaluates on the
adjacent out-of-sample (OOS) slice.  The kit uses MT5's built-in
*Forward 1/4* mode: 75% IS, 25% OOS, no re-optimisation per fold.

`scripts/vibecodekit_mql5/walkforward.py` consumes two MT5-emitted
XML reports (IS and OOS) and computes:

- Sharpe IS / Sharpe OOS / correlation
- profit factor IS / OOS / ratio
- per-fold equity curve overlap

`overfit_check.py` (reference 58) reads the same XML pair and emits a
single OOS/IS robustness ratio.
