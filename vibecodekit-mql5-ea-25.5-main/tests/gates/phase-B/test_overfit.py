"""Phase B — overfit_check ratio + threshold unit tests (3 tests)."""
from __future__ import annotations

from vibecodekit_mql5.overfit_check import evaluate, ratio, verdict


def test_ratio_zero_for_nonpositive_is():
    assert ratio(0.0, 0.5) == 0.0
    assert ratio(-0.1, 0.5) == 0.0


def test_verdict_thresholds():
    assert verdict(0.9) == "PASS"
    assert verdict(0.6) == "WARN"
    assert verdict(0.4) == "FAIL"


def test_evaluate_packs_inputs():
    r = evaluate(1.0, 0.8)
    assert r.is_sharpe == 1.0
    assert r.oos_sharpe == 0.8
    assert r.ratio == 0.8
    assert r.verdict == "PASS"
