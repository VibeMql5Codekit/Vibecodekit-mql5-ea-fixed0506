---
id: 52-multi-symbol
title: Multi-symbol patterns
tags: [multi-symbol, portfolio]
applicable_phase: A
---

# Multi-symbol patterns

A multi-symbol EA either:

1. Iterates a list of symbols inside one `OnTick` (the *portfolio
   basket* scaffold), or
2. Uses one MagicNumber per symbol/strategy pair and reads each via
   `iTime(symbol, _Period, 0)` to detect new bars per symbol.

Both patterns must use `CPipNormalizer` per symbol — different
instruments have different `Digits`, `Point`, and contract sizes.  Use
`MqlTick` history (`SymbolInfoTick`) when you need a tick-level loop
without `OnTick` firing for every symbol.

See `scaffolds/portfolio-basket/` for the canonical implementation.
