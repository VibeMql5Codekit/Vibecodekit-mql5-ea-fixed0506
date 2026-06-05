"""Wave-3 W3.C — closed forge backtest loop.

Pins the contract that ``mql5-forge-loop`` exposes:

1. Runs N iterations hermetically (no Wine, no MetaTester, no
   subprocess) by chaining the Wave-2 hermetic fixture generator into
   the Wave-1 ``mql5-backtest`` XML parser.
2. Emits one XML per iteration with a stable, deterministic name keyed
   to ``base_seed + iteration``.
3. Aggregates a ``forge-loop-report.json`` with per-iter metrics + a
   stability summary (PF mean/stdev, Sharpe mean, worst max-DD).
4. Honours optional ``--pf-floor``, ``--sharpe-floor``, and
   ``--max-dd-ceiling`` thresholds — any violation flips the run's
   exit code to 1 and lists the offending iteration in the report.
5. Exposes the same Wave-1 ``--json`` envelope + ``--gate-report``
   contract every other gate ships, so the matrix collector picks the
   result up unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from vibecodekit_mql5 import forge_loop as forge_loop_mod


def test_run_loop_emits_one_xml_per_iteration(tmp_path):
    report = forge_loop_mod.run_loop(
        iterations=3, base_seed=100, strategy="trend",
        symbol="EURUSD", tf="H1", trades=120, out=tmp_path,
    )
    assert len(report.iterations) == 3
    for i, it in enumerate(report.iterations):
        # Seed is deterministic in base+offset form.
        assert it.seed == 100 + i
        assert Path(it.xml_path).exists()
        assert Path(it.xml_path).suffix == ".xml"


def test_run_loop_metrics_are_parsed_from_xml(tmp_path):
    """Each iteration's PF/Sharpe/DD come from parsing the XML the
    fixture wrote — not from any hand-rolled stub. If the parser ever
    breaks, the loop must surface that, not silently emit zeros."""

    report = forge_loop_mod.run_loop(
        iterations=2, base_seed=200, strategy="trend",
        symbol="EURUSD", tf="H1", trades=150, out=tmp_path,
    )
    for it in report.iterations:
        # Trend strategy should produce a positive PF (it's the
        # happy-path generator) and a non-zero trade count.
        assert it.total_trades > 0, "no trades parsed from synthetic XML"
        assert it.profit_factor > 0.0


def test_run_loop_threshold_violations_flip_ok(tmp_path):
    """Setting an impossible pf_floor makes the report.ok flip to false
    and pins the iteration index in the violation list."""

    report = forge_loop_mod.run_loop(
        iterations=2, base_seed=10, strategy="random",
        symbol="EURUSD", tf="H1", trades=100, out=tmp_path,
        pf_floor=99.0,  # synthetic series will never beat this
    )
    assert report.ok is False
    assert len(report.threshold_violations) >= 1
    assert "profit_factor" in report.threshold_violations[0]


def test_run_loop_writes_summary_keys(tmp_path):
    report = forge_loop_mod.run_loop(
        iterations=4, base_seed=500, strategy="trend",
        symbol="EURUSD", tf="H1", trades=200, out=tmp_path,
    )
    summary = report.summary()
    expected_keys = {
        "iterations", "pf_mean", "pf_stdev", "sharpe_mean",
        "max_dd_pct_worst", "ok", "threshold_violations",
    }
    assert expected_keys <= summary.keys()
    assert summary["iterations"] == 4


def test_main_cli_writes_envelope_and_report(tmp_path):
    rc = forge_loop_mod.main([
        "--iterations", "2",
        "--strategy", "trend",
        "--base-seed", "777",
        "--symbol", "EURUSD",
        "--tf", "H1",
        "--trades", "100",
        "--out", str(tmp_path),
    ])
    assert rc == 0
    json_report = tmp_path / "forge-loop-report.json"
    assert json_report.exists(), "forge-loop-report.json was not written"
    body = json.loads(json_report.read_text(encoding="utf-8"))
    assert body["strategy"] == "trend"
    assert body["base_seed"] == 777
    assert len(body["iterations"]) == 2
    assert body["summary"]["iterations"] == 2


def test_main_cli_with_gate_report_writes_envelope(tmp_path):
    gate_path = tmp_path / "gate-report-forge.json"
    rc = forge_loop_mod.main([
        "--iterations", "1",
        "--strategy", "trend",
        "--base-seed", "1",
        "--out", str(tmp_path),
        "--gate-report", str(gate_path),
    ])
    assert rc == 0
    assert gate_path.exists()
    envelope = json.loads(gate_path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "1"
    assert envelope["tool"] == "mql5-forge-loop"
    assert envelope["ok"] is True


def test_main_cli_threshold_violation_exits_one(tmp_path):
    rc = forge_loop_mod.main([
        "--iterations", "2",
        "--strategy", "random",
        "--base-seed", "9999",
        "--pf-floor", "99",
        "--out", str(tmp_path),
    ])
    assert rc == 1


def test_main_cli_rejects_zero_iterations(tmp_path):
    rc = forge_loop_mod.main([
        "--iterations", "0",
        "--out", str(tmp_path),
    ])
    assert rc == 2


def test_loop_is_deterministic_for_same_base_seed(tmp_path):
    """Same base_seed + iteration count = byte-identical XML on disk."""

    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    forge_loop_mod.run_loop(
        iterations=2, base_seed=42, strategy="trend",
        symbol="EURUSD", tf="H1", trades=120, out=out_a,
    )
    forge_loop_mod.run_loop(
        iterations=2, base_seed=42, strategy="trend",
        symbol="EURUSD", tf="H1", trades=120, out=out_b,
    )
    for child in out_a.iterdir():
        if child.suffix != ".xml":
            continue
        twin = out_b / child.name
        assert twin.exists(), f"missing twin for {child}"
        assert child.read_bytes() == twin.read_bytes(), (
            f"forge-loop iteration not deterministic: {child.name}"
        )
