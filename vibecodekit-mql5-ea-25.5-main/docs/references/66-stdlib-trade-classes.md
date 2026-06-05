---
id: 66-stdlib-trade-classes
title: stdlib CTrade / CPositionInfo deep dive
tags: [stdlib, trade]
applicable_phase: A
---

# stdlib CTrade / CPositionInfo deep dive

`CTrade` defaults:

- `SetExpertMagicNumber(magic)` — must match the EA's magic
- `SetDeviationInPoints(deviation)` — slippage in points
- `SetTypeFillingBySymbol(symbol)` — handles ECN/STP fill modes

`CPositionInfo` reads from the terminal's position cache — call
`SelectByTicket(ticket)` or `SelectByIndex(i)` before reading.  Do not
hold a `CPositionInfo` reference across ticks; re-select.
