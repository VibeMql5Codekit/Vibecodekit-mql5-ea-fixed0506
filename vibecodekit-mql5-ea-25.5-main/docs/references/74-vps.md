---
id: 74-vps
title: MetaQuotes Native VPS
tags: [vps, deploy, trader-17]
applicable_phase: B
---

# MetaQuotes Native VPS

MetaQuotes' Virtual Hosting rents a co-located terminal that mirrors
your local broker login. The kit does **not** automate VPS
provisioning (it sits behind the broker's account portal, with no
public API), but it gates and documents every step you can automate
*before* migration.

## CLI — `mql5-deploy-vps`

```bash
python -m vibecodekit_mql5.deploy_vps MyEA.mq5 --out MIGRATE-VPS.md
```

`scripts/vibecodekit_mql5/deploy_vps.py` runs `trader_check.evaluate`
on the EA source, and **fails closed** unless the result reaches the
personal-mode threshold (≥ 15 / 17 PASS). On pass it emits a
`MIGRATE-VPS.md` runbook at the chosen output path.

| Exit code | Meaning |
|---|---|
| 0 | trader-check passed, runbook written |
| 1 | trader-check below threshold — VPS migration blocked |
| 2 | invocation error (missing file, etc.) |

## MIGRATE-VPS.md sections

The generated runbook covers the only steps a human can perform on the
broker terminal — there is no automation past the gate:

1. **Pre-flight** (local terminal): compile clean, run 90-day backtest,
   `mql5-multibroker` PASS on ≥ 3 demo brokers.
2. **Migration**: right-click chart → *Register a Virtual Server* →
   *Migration: Experts & indicators* → also migrate chart templates +
   tester cache.
3. **Verification**: open *VPS* in Navigator, confirm
   `Migrated successfully`. Open the VPS Journal and verify
   `[PipNorm]` printed the expected `digits / point / pip` triple for
   the live symbol.
4. **Rollback**: stop the VPS subscription → local chart resumes after
   re-attach; keep `Sets/default.set` for re-deploy.
5. **Trader-17 detail**: per-item PASS/FAIL/WARN/N/A from
   `trader_check.evaluate`, so the runbook captures the exact gating
   evidence at deploy time.

## Why a guide, not an API

The MetaQuotes VPS provisioning flow uses the broker account credential
plus an internal terminal RPC. There is no public REST endpoint to
script, so the kit's role is to *gate* (Trader-17), *generate
artefacts* (runbook + canary plan), and *observe* once the EA is on the
VPS via `mql5-canary` parsing the VPS journal. Anyone claiming "one-
click MT5 VPS deploy" is either logging into a different broker UI on
your behalf or is lying.
