"""Phase C acceptance sentinel — referenced by `audit-plan-v5.py --post-phase=C`.

The actual unit tests live in the sibling ``test_*.py`` modules in this
directory; this file exists so the audit script's mandatory-file check
passes and acts as a marker that Phase C tests are wired up.
"""

from __future__ import annotations

from pathlib import Path

# Concrete sibling tests that together cover the 25 Phase C acceptance gates.
EXPECTED_TEST_MODULES: tuple[str, ...] = (
    "test_personas.py",
    "test_step_workflow.py",
    "test_matrix.py",
    "test_layers.py",
    "test_13_best_practice_ap.py",
)


def test_phase_c_test_modules_present() -> None:
    here = Path(__file__).parent
    missing = [name for name in EXPECTED_TEST_MODULES if not (here / name).exists()]
    assert not missing, f"Phase C test modules missing: {missing}"
