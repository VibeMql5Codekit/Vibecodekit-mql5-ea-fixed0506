"""Phase D Cloud Network unit tests — 3 cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5 import cloud_optimize


def test_personal_mode_rejected() -> None:
    rep = cloud_optimize.plan(
        "personal", passes=1000, seconds_per_pass=60, budget_usd=10.0,
    )
    assert not rep.ok
    assert "PERSONAL" in rep.error or "personal" in rep.error


def test_enterprise_requires_explicit_budget() -> None:
    rep = cloud_optimize.plan(
        "enterprise", passes=10, seconds_per_pass=60, budget_usd=None,
    )
    assert not rep.ok
    assert "budget" in rep.error.lower()


@pytest.mark.parametrize("budget,expect_ok", [(1.0, True), (0.05, False)])
def test_team_budget_cap(budget: float, expect_ok: bool, tmp_path: Path) -> None:
    # 10 passes × 60s × $0.001/s = $0.60 estimated cost.
    rep = cloud_optimize.plan(
        "team", passes=10, seconds_per_pass=60, budget_usd=budget,
    )
    assert rep.ok is expect_ok
    if rep.ok:
        out = tmp_path / "tester.ini"
        cloud_optimize.write_tester_ini(
            out, ea="MyEA", symbol="EURUSD", period="H1", passes=10,
        )
        text = out.read_text()
        assert "Optimization=2" in text


def test_tester_ini_uses_criterion_enum_not_pass_count(tmp_path: Path) -> None:
    """Regression: OptimizationCriterion is a 0..6 enum, not the passes count."""
    out = tmp_path / "tester.ini"
    cloud_optimize.write_tester_ini(
        out, ea="MyEA", symbol="EURUSD", period="H1", passes=1000,
    )
    text = out.read_text()
    # default criterion (0=Balance max) must be written, not 1000
    assert "OptimizationCriterion=0\n" in text
    assert "OptimizationCriterion=1000" not in text
    # passes is preserved in a comment header for the operator
    assert "Planned passes: 1000" in text


def test_tester_ini_rejects_invalid_criterion(tmp_path: Path) -> None:
    out = tmp_path / "tester.ini"
    with pytest.raises(ValueError, match="optimization_criterion"):
        cloud_optimize.write_tester_ini(
            out, ea="MyEA", symbol="EURUSD", period="H1", passes=10,
            optimization_criterion=99,
        )


@pytest.mark.parametrize("criterion", [0, 1, 2, 3, 4, 5, 6])
def test_tester_ini_accepts_each_valid_criterion(
    criterion: int, tmp_path: Path,
) -> None:
    out = tmp_path / "tester.ini"
    cloud_optimize.write_tester_ini(
        out, ea="MyEA", symbol="EURUSD", period="H1", passes=10,
        optimization_criterion=criterion,
    )
    assert f"OptimizationCriterion={criterion}\n" in out.read_text()
