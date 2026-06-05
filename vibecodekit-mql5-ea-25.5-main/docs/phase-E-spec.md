# Phase E Spec — Polish & Ship v1.0.0

> ⚠️ **Internal / contributor document.** Sprint spec for this kit's own development — not user-facing. See [`README.md`](../README.md) and [`docs/QUICKSTART.md`](QUICKSTART.md) instead.

**Goal:** 26 references full + 3 MCP servers + worked example + canary + final commands.
**Duration:** 2-3 weeks.
**Tag on completion:** v1.0.0.
**Prereq:** v0.5.0.

## Files added in Phase E

```
mcp/
├── metaeditor-bridge/
│   ├── server.py                             # < 200 LOC, JSON-RPC 2.0
│   └── tools.py
├── mt5-bridge/
│   ├── server.py                             # READ-ONLY, NO trade methods
│   └── tools.py
└── algo-forge-bridge/
    ├── server.py
    └── tools.py

scripts/vibecodekit_mql5/
├── canary.py                                 # /mql5-canary
├── doctor.py                                 # /mql5-doctor
├── install.py                                # /mql5-install
├── audit.py                                  # /mql5-audit (run all 70 conformance)
├── ship.py                                   # /mql5-ship
├── refine.py                                 # /mql5-refine
├── survey.py                                 # /mql5-survey
├── scan.py                                   # /mql5-scan
├── rri.py                                    # /mql5-rri (template opener)
├── vision.py                                 # /mql5-vision
├── blueprint.py                              # /mql5-blueprint
├── tip.py                                    # /mql5-tip
└── second_opinion.py                         # /mql5-second-opinion

docs/references/
├── 50-survey.md
├── 51-platform-arch.md
├── 52-multi-symbol.md
├── 53-broker-modes.md
├── 54-stl-cheatsheet.md
├── 55-tester-stats.md
├── 56-walkforward.md
├── 57-monte-carlo.md
├── 58-overfit.md
├── 59-trader-checklist.md
├── 60-wizard-cexpert.md
├── 61-tester-metrics.md
├── 62-mfe-mae.md
├── 63-tester-config.md
├── 64-fitness-templates.md
├── 65-multi-broker.md
├── 66-stdlib-trade-classes.md
├── 67-indicator-dev-parallel.md
├── 70-algo-forge.md
├── 71-onnx-mql5.md
├── 72-matrix-vector.md
├── 73-cloud-network.md
├── 74-vps.md
├── 75-webrequest.md
├── 76-llm-patterns.md
├── 77-async-hft.md
├── 78-opencl.md
└── 79-pip-norm.md                            # FLAGSHIP doc

docs/
├── QUICKSTART.md
├── COMMANDS.md                                # ~30 commands catalog
└── MIGRATE-VPS.md

examples/
└── ea-wizard-macd-sar-eurusd-h1-portfolio/
    ├── EAName.mq5
    ├── eurusd-h1.set
    ├── README.md                             # full 8-step walkthrough
    └── results/
        ├── backtest.xml
        ├── multibroker.csv
        ├── canary.log
        └── matrix-64-cell.html

tests/gates/phase-E/
├── test_phase_e_acceptance.py                # 10 integration
├── test_mcp_servers.py                       # 4 unit
├── test_references_frontmatter.py            # 26 unit
├── test_worked_example.py                    # 1 unit (replay verification)
├── test_canary.py                            # 3 unit
└── test_doctor_install_audit.py              # 6 unit
```

## 40 tests (acceptance gate)

### 10 integration
1. `test_3_mcp_servers_handshake` — all 3 servers respond to MCP init
2. `test_metaeditor_bridge_compile` — compile via MCP works
3. `test_mt5_bridge_readonly_no_trade` — verify no order_send/order_close/position_modify in API
4. `test_mt5_bridge_15_tools_exposed`
5. `test_algo_forge_bridge_pr` (mock API)
6. `test_worked_example_e2e_4_to_6_hours_enterprise`
7. `test_canary_30min_observability`
8. `test_doctor_health_check`
9. `test_install_reconcile`
10. `test_audit_runs_all_70_conformance`

### 30 unit
- 4 MCP server (each + orchestrator)
- 26 references frontmatter validation (1 test per ref + 4 docs)

## 70 conformance tests (final gate)

`/mql5-audit` runs:
- 10 e2e (across all phases)
- 60 internal probes:
  - 15 module load/schema
  - 15 scaffold tree validity
  - 10 reference frontmatter
  - 10 methodology config
  - 10 governance (VERSION mirror, SBOM, license)

All 70 must pass for v1.0.0 ship.

## mt5-bridge READ-ONLY enforcement

CRITICAL: `mcp/mt5-bridge/server.py` and `tools.py` MUST NOT contain ANY of:
- `order_send`
- `order_close`
- `position_modify`
- `position_close`
- Any function that mutates broker state

Test `test_mt5_bridge_readonly_no_trade` greps the entire mcp/mt5-bridge/
directory for these keywords. Any hit = test FAIL.

## Worked example timing

Per Plan v5 §19:
- ENTERPRISE mode (full 8-step + 7-layer + 64-cell matrix): 4-6 hours
- TEAM mode (8-step + 5-layer + 32-cell): 2-3 hours
- PERSONAL mode (skip RRI, only build/lint/compile/backtest/multibroker/ship): 1-2 hours

`test_worked_example_e2e_4_to_6_hours_enterprise` runs replay and verifies time.

## ~30 commands final catalog

(All callable directly. NO master `/mql5` router.)

```
Discovery (4):    /mql5-scan, /mql5-survey, /mql5-doctor, /mql5-audit
Plan (4):         /mql5-rri, /mql5-vision, /mql5-blueprint, /mql5-tip
Build (8):        /mql5-build, /mql5-wizard, /mql5-pip-normalize, /mql5-async-build,
                  /mql5-onnx-export, /mql5-onnx-embed, /mql5-llm-context, /mql5-forge-init
Verify (10):      /mql5-compile, /mql5-lint, /mql5-method-hiding-check, /mql5-backtest,
                  /mql5-walkforward, /mql5-monte-carlo, /mql5-overfit-check, /mql5-multibroker,
                  /mql5-fitness, /mql5-mfe-mae
RRI (3):          /mql5-rri-bt, /mql5-rri-rr, /mql5-rri-chart
Review (5):       /mql5-review, /mql5-eng-review, /mql5-ceo-review, /mql5-cso, /mql5-investigate
Deploy (3):       /mql5-deploy-vps, /mql5-cloud-optimize, /mql5-canary
Ship (3):         /mql5-forge-pr, /mql5-ship, /mql5-refine
Other (3):        /mql5-broker-safety, /mql5-trader-check, /mql5-install
                  /mql5-second-opinion (optional)
```

Total: ~30 commands.

## Acceptance gate

- [ ] v0.5.0 merged
- [ ] 40/40 Phase E tests pass
- [ ] 70/70 conformance tests pass
- [ ] audit clean
- [ ] All modules < 200 LOC
- [ ] mt5-bridge MCP verified READ-ONLY (grep test passes)
- [ ] Worked example runs in 4-6 hours enterprise mode
- [ ] 26 references all have valid YAML frontmatter
- [ ] /mql5-doctor returns OK on fresh Devin VM
- [ ] All ~30 commands callable
- [ ] `git tag v1.0.0` after merge
- [ ] Repository ready for personal/enterprise use
