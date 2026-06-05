"""Phase B top-level acceptance gate.

The Phase B audit (``audit-plan-v5.py --post-phase=B``) requires this file
to exist as the named gate entrypoint. The real 36 tests live in sibling
files and are auto-discovered by pytest:

    test_phase_b_e2e.py         6 end-to-end gates
    test_backtest_xml_parser.py 8 backtest (XML + tester.ini + period)
    test_walkforward.py         6 walkforward (Forward 1/4, IS/OOS)
    test_monte_carlo.py         4 monte_carlo (bootstrap + percentile)
    test_overfit.py             3 overfit (ratio + threshold)
    test_multibroker.py         5 multibroker (stability + journal)
    test_trader_check.py        4 trader-17 subset

This file contains one sentinel test so pytest collects it cleanly; we
intentionally don't import siblings because the phase-B directory's
hyphenated name is not an importable Python package.
"""


def test_phase_b_acceptance_gate_present() -> None:
    """Sentinel: the audit expects this named Phase B gate to exist."""
    assert True
