"""Regression tests for ``vibecodekit_mql5.fitness`` templates.

Specifically guards against the Devin-Review-reported bug where the
``walkforward`` template emitted ``TesterStatistics(STAT_SHARPE_RATIO)``
twice (for both `sharpe_is` and `sharpe_oos`), collapsing the advertised
0.75/0.25 composite to plain Sharpe.

The accurate IS/OOS walk-forward composite is produced externally by the
Python ``mql5-walkforward`` orchestrator, which compares two separate
backtest XML reports. The in-tester ``walkforward`` template therefore
becomes a defensible single-pass robustness Sharpe instead.
"""
from __future__ import annotations

import re

from vibecodekit_mql5 import fitness


# ── all 5 templates are present ───────────────────────────────────────────

def test_list_templates_contains_all_five():
    names = fitness.list_templates()
    assert set(names) == {"sharpe", "sortino", "profit-dd",
                          "expectancy", "walkforward"}


# ── walk-forward template no longer fabricates STAT_SHARPE_RATIO_OOS ──────

def test_walkforward_template_does_not_pretend_oos_exists():
    body = fitness.get("walkforward")
    # The buggy version called TesterStatistics(STAT_SHARPE_RATIO) twice
    # to seed `sharpe_is` and `sharpe_oos`. That fabricated an OOS stat
    # the platform doesn't actually expose; the composite then collapsed
    # to plain Sharpe (`0.75 + 0.25 = 1.0`). Guard the regression.
    assert "sharpe_oos" not in body
    assert "0.75" not in body
    assert "0.25" not in body
    # And the in-tester surrogate must still gate on min-trades + DD.
    assert "STAT_TRADES" in body
    assert "STAT_BALANCEDD_PERCENT" in body


# ── every template returns a syntactically plausible C++ snippet ──────────

def test_every_template_returns_double_and_uses_TesterStatistics():
    for name in fitness.list_templates():
        body = fitness.get(name)
        assert "TesterStatistics(" in body, f"{name}: no TesterStatistics call"
        assert "return " in body, f"{name}: no return statement"


# ── CLI emits one name per line when invoked without arg ──────────────────

def test_main_lists_templates(capsys):
    rc = fitness.main([])
    captured = capsys.readouterr().out.strip().splitlines()
    assert rc == 0
    assert set(captured) == set(fitness.list_templates())


def test_main_unknown_template_returns_2(capsys):
    rc = fitness.main(["does-not-exist"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown template" in err


def test_main_known_template_prints_body(capsys):
    rc = fitness.main(["sharpe"])
    out = capsys.readouterr().out
    assert rc == 0
    # body should contain at least one TesterStatistics call
    assert re.search(r"TesterStatistics\s*\(", out)
