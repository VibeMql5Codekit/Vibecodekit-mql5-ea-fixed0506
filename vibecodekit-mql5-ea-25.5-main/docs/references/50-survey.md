---
id: 50-survey
title: Kit overview
tags: [overview]
applicable_phase: E
---

# Kit overview

`vibecodekit-mql5-ea` is a methodology + tooling layer for shipping
production MQL5 Expert Advisors against MetaTrader 5.  It deliberately
does NOT try to be a one-stop trading framework — instead it stitches
together:

- a small library of `.mqh` includes (`CPipNormalizer`, `CRiskGuard`,
  `CMagicRegistry`, `CSpreadGuard`, `CMfeMaeLogger`, `COnnxLoader`,
  `CAsyncTradeManager`)
- ~30 Python commands surfaced under the `mql5-*` namespace
- 11 scaffold archetypes covering the realistic strategy space
  (trend, mean-reversion, breakout, grid, hedging, etc.)
- a 26-document reference shelf
- 3 MCP servers (metaeditor / mt5 / algo-forge) for chat-driven
  workflows
- a 7-layer permission pipeline + 64-cell quality matrix that scale
  from PERSONAL (5 layers) to ENTERPRISE (7 layers)

The kit is designed to be **installed alongside** an existing
MetaQuotes project, not replace it.  Most users start with
`/mql5-doctor` + `/mql5-install` and then graduate to the 8-step
methodology when they need audit trails.

See `docs/COMMANDS.md` for the full command catalog and
`docs/QUICKSTART.md` for a 10-minute onboarding path.
