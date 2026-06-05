"""Phase B — multibroker stability metrics + journal verify (5 tests)."""
from __future__ import annotations

from pathlib import Path

from vibecodekit_mql5.backtest import BacktestResult
from vibecodekit_mql5.multibroker import (
    DD_DIFF_MAX,
    PF_CV_MAX,
    SHARPE_STDEV_MAX,
    evaluate,
)


def _mk(pf: float, sharpe: float, dd: float) -> BacktestResult:
    r = BacktestResult()
    r.profit_factor = pf
    r.sharpe = sharpe
    r.max_drawdown_pct = dd
    return r


def test_stability_passes_for_consistent_brokers():
    reports = [_mk(1.78, 0.42, 8.0),
               _mk(1.75, 0.40, 8.5),
               _mk(1.80, 0.43, 8.2)]
    r = evaluate(reports)
    assert r.verdict == "PASS"
    assert r.pf_cv <= PF_CV_MAX
    assert r.sharpe_stdev <= SHARPE_STDEV_MAX
    assert r.dd_diff <= DD_DIFF_MAX


def test_stability_fails_on_high_pf_variance():
    reports = [_mk(0.5, 0.42, 8.0),
               _mk(2.0, 0.40, 8.5),
               _mk(3.5, 0.43, 8.2)]
    r = evaluate(reports)
    assert r.verdict == "FAIL"
    assert any("PF CV" in d for d in r.details)


def test_stability_fails_on_high_dd_diff():
    reports = [_mk(1.7, 0.42, 4.0),
               _mk(1.7, 0.40, 12.0),
               _mk(1.7, 0.43, 8.2)]
    r = evaluate(reports)
    assert r.verdict == "FAIL"
    assert any("DD diff" in d for d in r.details)


def test_journal_pipnorm_presence(tmp_path: Path):
    j1 = tmp_path / "j1.log"
    j2 = tmp_path / "j2.log"
    j3 = tmp_path / "j3.log"
    j1.write_text("[PipNorm] digits=5 point=0.00001 pip=0.0001\nOnInit OK")
    j2.write_text("[PipNorm] digits=3 point=0.001 pip=0.01")
    j3.write_text("OnInit OK — no normalizer call in this run")
    reports = [_mk(1.7, 0.42, 8.0)] * 3
    r = evaluate(reports, journals=[str(j1), str(j2), str(j3)])
    assert r.pipnorm_log_seen == [str(j1), str(j2)]
    assert r.verdict == "FAIL"  # missing in j3


def test_stability_metrics_dict_serializable():
    reports = [_mk(1.7, 0.42, 8.0), _mk(1.7, 0.42, 8.0)]
    d = evaluate(reports).to_dict()
    assert d["verdict"] == "PASS"
    assert "pf_cv" in d and "dd_diff" in d
