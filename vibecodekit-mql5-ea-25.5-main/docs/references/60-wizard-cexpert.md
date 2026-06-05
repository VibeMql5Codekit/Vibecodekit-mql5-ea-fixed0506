---
id: 60-wizard-cexpert
title: MQL5 Wizard + CExpert composables
tags: [wizard, stdlib]
applicable_phase: A
---

# MQL5 Wizard + CExpert composables

MetaEditor's Wizard generates an EA skeleton that derives from
`CExpert`.  `CExpert` composes:

- `CExpertSignal` — entry decision
- `CExpertMoney`  — position sizing
- `CExpertTrailing` — trailing-stop logic

The kit's `wizard-composable` scaffold replaces the default signals
with the kit's `CPipNormalizer`-aware trade routine while keeping the
`CExpert` lifecycle (so users get the wizard's protections for free).
