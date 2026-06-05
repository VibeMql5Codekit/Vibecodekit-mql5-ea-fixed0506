---
id: 65-multi-broker
title: Multi-broker stability protocol
tags: [multi-broker, stability]
applicable_phase: B
---

# Multi-broker stability protocol

`multibroker.py` orchestrates the same EA across N broker
demos and emits a stability score:

- per-broker Sharpe variance
- pip-norm drift detection
- spread+commission cost-of-slippage delta

Used by Layer 7 of the permission pipeline (broker-safety).
