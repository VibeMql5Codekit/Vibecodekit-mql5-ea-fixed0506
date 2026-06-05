# Phase 0 Spec — Bootstrap

> ⚠️ **Internal / contributor document.** Sprint spec for this kit's own development — not user-facing. See [`README.md`](../README.md) and [`docs/QUICKSTART.md`](QUICKSTART.md) instead.

**Goal:** Set up infrastructure (Wine + MetaEditor + CI) before any feature work.
**Duration:** 1 week.
**Tag on completion:** v0.0.1.

## Files added in Phase 0 (exhaustive list)

```
.github/
└── workflows/
    └── ci.yml                                # GitHub Actions Linux + Windows runners

scripts/
├── setup-wine-metaeditor.sh                  # Wine + MetaEditor installer for Linux
└── audit-plan-v5.py                          # anti-drift audit (pre/post phase)

tests/
├── gates/
│   └── phase-0/
│       ├── __init__.py
│       └── test_phase_0_smoke.py             # 5 smoke tests
└── fixtures/
    └── demo_smoke.mq5                        # minimal .mq5 for compile smoke
```

**No other files** are added in Phase 0. No `Include/`, no `scaffolds/`,
no `scripts/build.py`, etc.

## 5 smoke tests (acceptance gate)

| # | Test | Pass criteria |
|---|------|---------------|
| 1 | `test_wine_version_8_or_above` | `wine --version` returns >= 8.0 |
| 2 | `test_metaeditor_compile_demo_mq5` | `wine metaeditor64.exe /compile:demo_smoke.mq5` returns 0 errors |
| 3 | `test_xvfb_headless_works` | `xvfb-run -a echo OK` returns 0 |
| 4 | `test_python_venv_pytest` | `.venv/bin/pytest --version` returns 7.x+ |
| 5 | `test_ci_workflow_yaml_valid` | `.github/workflows/ci.yml` validates against GitHub Actions schema |

## CI workflow requirements

- Linux runner: ubuntu-latest, Wine + MetaEditor smoke tests
- Windows runner: windows-latest, native MetaEditor smoke tests
- Both must pass before merge

## Audit script requirements

`scripts/audit-plan-v5.py` skeleton:
```python
"""Anti-drift audit for vibecodekit-mql5-ea Plan v5 implementation."""
import argparse, sys
from pathlib import Path
from typing import List

FORBIDDEN_FILES = [...]  # see anti-patterns-AVOID.md
FORBIDDEN_PATTERNS = [...]
PHASE_FILES = {
    "0": ["scripts/setup-wine-metaeditor.sh", ".github/workflows/ci.yml", ...],
    "A": ["Include/CPipNormalizer.mqh", "scripts/build.py", ...],
    # ... B-E
}

def audit_pre_phase(phase: str) -> bool: ...
def audit_post_phase(phase: str) -> bool: ...

if __name__ == "__main__":
    ...
```

## Out of scope for Phase 0

- ANY content from Phase A-E (see respective spec files)
- VCK-HU dead code (see anti-patterns-AVOID.md)

## Acceptance gate

Merge PR0 only when:
- [ ] All 5 smoke tests pass on Linux runner
- [ ] All 5 smoke tests pass on Windows runner
- [ ] `python scripts/audit-plan-v5.py --post-phase=0` returns exit 0
- [ ] No files outside this spec's exhaustive list
- [ ] `git tag v0.0.1` after merge
