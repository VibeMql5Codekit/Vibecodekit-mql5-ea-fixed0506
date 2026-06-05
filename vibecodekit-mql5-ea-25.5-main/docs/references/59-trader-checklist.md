---
id: 59-trader-checklist
title: Trader-17 checklist deep dive
tags: [trader, checklist]
applicable_phase: B
---

# Trader-17 checklist deep dive

> **Honest disclaimer.** The Trader-17 checklist below is a
> **project-defined heuristic** designed by this kit. It is an
> opinionated guardrail for retail EA hygiene — not an industry
> standard, not a certification, and not a substitute for live-account
> validation. The 15/17 threshold is also a project choice.

The 17 trader-discipline checks live in
`scripts/vibecodekit_mql5/trader_check.py`.  Layer 4 of the permission
pipeline requires ≥ 15/17 to pass.  The 17 are:

1. Pip math normalised per symbol
2. SL is wider than spread + commission
3. Risk-per-trade ≤ account-level cap
4. Daily-loss kill-switch implemented
5. Max-positions cap enforced
6. Magic number unique
7. Spread guard implemented
8. Slippage parameter explicit
9. ECN/STP filling mode handled
10. Netting / hedging branch covered
11. Stop-out margin respected
12. Trading hours fence
13. News filter (optional but tracked)
14. WebRequest timeout fallback
15. ONNX inference timeout fallback
16. LLM-bridge fallback rule
17. MFE/MAE logging enabled
