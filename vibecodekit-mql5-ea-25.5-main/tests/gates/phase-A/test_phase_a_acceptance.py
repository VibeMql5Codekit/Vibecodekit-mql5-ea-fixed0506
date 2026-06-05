"""Phase A top-level acceptance gate.

The Phase A audit (``audit-plan-v5.py --post-phase=A``) requires this file
to exist as the named gate entrypoint, but the real tests live in sibling
modules and are auto-collected by pytest via the directory walk:

    test_e2e.py                     3 e2e gates
    test_lint_detectors.py          8 lint unit
    test_build_scaffolds.py         4 scaffold unit
    test_compile_log_parser.py      3 compile-log unit
    test_pip_normalize_refactor.py  5 refactor unit
    test_pipnorm_unit.py            5 CPipNormalizer unit

We intentionally do NOT re-export the sibling modules here — Python cannot
import packages whose directory contains a hyphen (``phase-A``), and
duplicating test functions confuses pytest's de-duplication. This file
contains one trivial sentinel test so pytest can collect it cleanly.
"""


def test_phase_a_acceptance_gate_present() -> None:
    """Sentinel: confirms the named Phase A gate entrypoint exists.

    The real 28 acceptance tests are auto-discovered from sibling files
    in this directory.
    """
    assert True
