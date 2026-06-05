---
id: 53-broker-modes
title: Broker modes (netting / hedging / account types)
tags: [broker, netting, hedging]
applicable_phase: A
---

# Broker modes (netting / hedging / account types)

Brokers expose one of two **account modes**:

- **Netting** (most ECN/STP brokers) — at most one position per symbol,
  opposite-direction orders close instead of stacking.
- **Hedging** (most retail FX brokers) — many positions per symbol,
  closed individually by ticket.

The kit ships netting and hedging variants for every scaffold that
needs trade routing.  Use `AccountInfoInteger(ACCOUNT_MARGIN_MODE) ==
ACCOUNT_MARGIN_MODE_RETAIL_HEDGING` to branch at runtime when an EA
must support both.
