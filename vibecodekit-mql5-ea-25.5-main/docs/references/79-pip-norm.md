---
id: 79-pip-norm
title: Cross-broker pip normalisation (FLAGSHIP)
tags: [pip, broker]
applicable_phase: A
---

# Cross-broker pip normalisation (FLAGSHIP)

The single most important reference in the kit.  Different
brokers quote the same currency pair with different `Digits` (5 vs 4,
3 vs 2 for JPY pairs) and different contract sizes.  A "20 pip" SL on
broker A is a 20-point SL on broker B; a strategy that hard-codes
pips drifts catastrophically across brokers.

`CPipNormalizer.mqh` provides the canonical conversion:

```
double pip_size = SymbolInfoInteger(symbol, SYMBOL_DIGITS) == 5
                   || SymbolInfoInteger(symbol, SYMBOL_DIGITS) == 3
                   ? 10 * SymbolInfoDouble(symbol, SYMBOL_POINT)
                   : SymbolInfoDouble(symbol, SYMBOL_POINT);
```

Every kit scaffold's `OnInit` must call `pip.Init(_Symbol)` before
issuing any order.  Lint rule AP-1 enforces this.
