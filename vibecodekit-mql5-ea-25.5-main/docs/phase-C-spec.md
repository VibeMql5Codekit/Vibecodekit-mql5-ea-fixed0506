# Phase C Spec — Methodology

> ⚠️ **Internal / contributor document.** Sprint spec for this kit's own development — not user-facing. See [`README.md`](../README.md) and [`docs/QUICKSTART.md`](QUICKSTART.md) instead.

**Goal:** RRI 6 personas + 8-step + 8x8 matrix + 7-layer permission + 13 best-practice AP.
**Duration:** 3 weeks.
**Tag on completion:** v0.3.0.
**Prereq:** v0.2.0.

## Files added in Phase C

```
scripts/vibecodekit_mql5/
├── rri/
│   ├── __init__.py
│   ├── personas.py                           # 6 personas loader
│   ├── step_workflow.py                      # 8-step state machine
│   ├── matrix.py                             # 8 dim × 8 axis populator + HTML
│   ├── rri_bt.py                             # /mql5-rri-bt
│   ├── rri_rr.py                             # /mql5-rri-rr
│   └── rri_chart.py                          # /mql5-rri-chart (optional)
├── permission/
│   ├── __init__.py
│   ├── layer1_source_lint.py                 # pre-commit hook
│   ├── layer2_compile.py                     # MetaEditor 0 errors
│   ├── layer3_ap_lint.py                     # 8 critical AP
│   ├── layer4_checklist.py                   # Trader-17 ≥ 15/17
│   ├── layer5_methodology.py                 # RRI 8-step done
│   ├── layer6_quality_matrix.py              # 64-cell ≥ 56 PASS
│   ├── layer7_broker_safety.py               # multi-broker + pip-norm
│   └── orchestrator.py                       # run all layers fail-fast
├── review/
│   ├── review.py                             # /mql5-review
│   ├── eng_review.py                         # /mql5-eng-review
│   ├── ceo_review.py                         # /mql5-ceo-review
│   ├── cso.py                                # /mql5-cso
│   └── investigate.py                        # /mql5-investigate
└── (extend lint.py with 13 best-practice AP-2,4,6-14,16,19)

docs/
├── rri-personas/
│   ├── trader.yaml                           # 25 questions
│   ├── risk-auditor.yaml
│   ├── broker-engineer.yaml
│   ├── strategy-architect.yaml
│   ├── devops.yaml
│   └── perf-analyst.yaml
└── rri-templates/
    ├── step-1-scan.md.tmpl
    ├── step-2-rri.md.tmpl
    ├── step-3-vision.md.tmpl
    ├── step-4-blueprint.md.tmpl
    ├── step-5-tip.md.tmpl
    ├── step-6-build.md.tmpl
    ├── step-7-verify.md.tmpl
    └── step-8-refine.md.tmpl

tests/gates/phase-C/
├── test_phase_c_acceptance.py                # 0 e2e (methodology = no e2e)
├── test_personas.py                          # 4 unit
├── test_step_workflow.py                     # 4 unit
├── test_matrix.py                            # 3 unit
├── test_layers.py                            # 9 unit (each layer + orchestrator)
└── test_13_best_practice_ap.py               # 5 unit (sample of 13 AP)
```

## 25 unit tests (acceptance gate)

- 4 persona tests: load 6 personas, count Q × mode, validate YAML schema
- 4 step workflow: 8 steps, transitions, 7 valid + invalid scenarios, mode-dependent
- 3 matrix: 64 cells, HTML render, threshold (≥56 PASS for ENTERPRISE)
- 9 layer tests: each of 7 layers + orchestrator + fail-fast
- 5 best-practice AP (sample): AP-2 SL-too-tight, AP-7 hardcoded-magic, AP-13 broker-coupled, AP-14 no-MFE-MAE, AP-16 reinvent-stdlib

## 6 RRI personas (each has 25 questions YAML file)

```yaml
# docs/rri-personas/trader.yaml
persona: trader
description: End-user trader using the EA
questions:
  - id: trader-01
    text: "What's my max acceptable drawdown?"
    priority: critical
    applicable_steps: [rri, vision, verify]
    applicable_modes: [personal, team, enterprise]
  - id: trader-02
    text: "..."
  # ... 23 more
```

Mode question count:
- PERSONAL: 5 questions/persona × 6 personas = 30 total
- TEAM: 12 questions/persona × 6 = 72 total
- ENTERPRISE: 25 questions/persona × 6 = 450 total

## 7-layer permission (each layer < 150 LOC, standalone)

| Layer | File | Threshold | Required for mode |
|-------|------|-----------|-------------------|
| 1 | `layer1_source_lint.py` | format + syntax pass | All |
| 2 | `layer2_compile.py` | 0 errors | All |
| 3 | `layer3_ap_lint.py` | 8 critical AP pass | All |
| 4 | `layer4_checklist.py` | ≥ 15/17 | All |
| 5 | `layer5_methodology.py` | RRI step 1-7 done | Team, Enterprise |
| 6 | `layer6_quality_matrix.py` | ≥ 56/64 | Enterprise |
| 7 | `layer7_broker_safety.py` | multi-broker + pip-norm | All |

Orchestrator (`orchestrator.py`):
- PERSONAL: layers 1, 2, 3, 4, 7
- TEAM: layers 1-5, 7
- ENTERPRISE: layers 1-7

## Acceptance gate

- [ ] v0.2.0 merged
- [ ] 25/25 tests pass
- [ ] audit clean
- [ ] All modules < 200 LOC
- [ ] 6 persona YAML files present (each with 25 questions)
- [ ] 7 layer scripts work standalone + orchestrated
- [ ] 64-cell matrix generates valid HTML report
- [ ] 13 best-practice AP added to lint.py (warn-only)
- [ ] `git tag v0.3.0` after merge
