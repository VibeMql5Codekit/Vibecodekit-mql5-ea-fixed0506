"""tests/gates/phase-A/test_json_flags_smoke.py — `--json` envelope smoke tests.

Every CLI that opts into Wave-1 agent contracts MUST emit a valid
envelope (schema_version=1) when invoked with ``--json``. This test
exercises each of the 12 target CLIs end-to-end with minimal,
self-contained fixtures.

The intent is *not* to verify each CLI's correctness (other suites do
that). The intent is to verify the *envelope contract*: stdout is
parseable JSON, has the required keys, and the schema version is
stable. Drift here breaks every downstream agent integration.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _parse_envelope(buf: io.StringIO) -> dict:
    return json.loads(buf.getvalue())


def _assert_envelope_shape(envelope: dict, *, tool: str) -> None:
    """Pin the canonical envelope contract."""

    assert envelope.get("schema_version") == "1", envelope
    assert envelope.get("tool") == tool, envelope
    assert isinstance(envelope.get("ok"), bool), envelope
    assert isinstance(envelope.get("exit_code"), int), envelope
    assert isinstance(envelope.get("summary"), str), envelope
    assert isinstance(envelope.get("data"), dict), envelope
    assert isinstance(envelope.get("evidence"), list), envelope


def test_lint_json_envelope():
    from vibecodekit_mql5 import lint as lint_cli

    sample = REPO_ROOT / "scaffolds" / "grid" / "hedging" / "EAName.mq5"
    buf = io.StringIO()
    with redirect_stdout(buf):
        lint_cli.main([str(sample), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-lint")
    assert "finding_count" in env["data"]
    # Matrix coords are required for gates that fill the quality matrix.
    assert env["matrix"]["dim"] == "d_correctness"
    assert env["matrix"]["axis"] == "implement"


def test_trader_check_json_envelope():
    from vibecodekit_mql5 import trader_check

    sample = REPO_ROOT / "scaffolds" / "trend" / "netting" / "EAName.mq5"
    buf = io.StringIO()
    with redirect_stdout(buf):
        trader_check.main([str(sample), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-trader-check")
    assert env["matrix"]["dim"] == "d_risk"


def test_broker_safety_json_envelope(tmp_path: Path):
    from vibecodekit_mql5 import broker_safety

    sample = REPO_ROOT / "scaffolds" / "trend" / "netting" / "EAName.mq5"
    sym = tmp_path / "sym.json"
    sym.write_text(json.dumps({
        "filling_modes": ["FOK", "IOC", "RETURN"],
        "volume_min": 0.01,
        "volume_step": 0.01,
    }))
    buf = io.StringIO()
    with redirect_stdout(buf):
        broker_safety.main([str(sample), str(sym), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-broker-safety")
    assert env["matrix"]["dim"] == "d_broker_safety"


def test_backtest_json_envelope():
    from vibecodekit_mql5 import backtest

    report = REPO_ROOT / "tests" / "fixtures" / "tester_report_eurusd_h1.xml"
    buf = io.StringIO()
    with redirect_stdout(buf):
        backtest.main([
            "dummy.mq5", "dummy.set",
            "--period", "2024",
            "--report", str(report),
            "--json",
        ])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-backtest")
    assert env["matrix"]["dim"] == "d_robustness"
    assert env["matrix"]["axis"] == "backtest"


def test_walkforward_json_envelope():
    from vibecodekit_mql5 import walkforward

    is_xml = REPO_ROOT / "tests" / "fixtures" / "tester_report_eurusd_h1.xml"
    oos_xml = REPO_ROOT / "tests" / "fixtures" / "tester_report_usdjpy_h1.xml"
    buf = io.StringIO()
    with redirect_stdout(buf):
        walkforward.main([str(is_xml), str(oos_xml), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-walkforward")
    assert env["matrix"]["axis"] == "walk_forward"


def test_monte_carlo_json_envelope(tmp_path: Path):
    from vibecodekit_mql5 import monte_carlo

    csv = tmp_path / "returns.csv"
    csv.write_text("return\n" + "\n".join(f"{i % 5 - 2:.2f}" for i in range(60)))
    buf = io.StringIO()
    with redirect_stdout(buf):
        monte_carlo.main([str(csv), "--reported-dd", "999",
                          "--n-sims", "50", "--seed", "1", "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-monte-carlo")
    assert env["matrix"]["axis"] == "backtest"


def test_multibroker_json_envelope():
    from vibecodekit_mql5 import multibroker

    a = REPO_ROOT / "tests" / "fixtures" / "tester_report_eurusd_h1.xml"
    b = REPO_ROOT / "tests" / "fixtures" / "tester_report_usdjpy_h1.xml"
    buf = io.StringIO()
    with redirect_stdout(buf):
        multibroker.main(["--reports", f"{a},{b}", "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-multibroker")
    assert env["matrix"]["dim"] == "d_broker_safety"


def test_overfit_check_json_envelope():
    from vibecodekit_mql5 import overfit_check

    is_xml = REPO_ROOT / "tests" / "fixtures" / "tester_report_eurusd_h1.xml"
    oos_xml = REPO_ROOT / "tests" / "fixtures" / "tester_report_usdjpy_h1.xml"
    buf = io.StringIO()
    with redirect_stdout(buf):
        overfit_check.main([str(is_xml), str(oos_xml), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-overfit-check")


def test_mfe_mae_json_envelope(tmp_path: Path):
    from vibecodekit_mql5 import mfe_mae

    csv = tmp_path / "trades.csv"
    csv.write_text("mfe,mae,profit\n10,2,8\n5,3,2\n8,4,4\n")
    buf = io.StringIO()
    with redirect_stdout(buf):
        mfe_mae.main([str(csv), "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-mfe-mae")


def test_doctor_json_envelope(tmp_path: Path):
    """Doctor in soft mode must always emit a valid envelope."""

    from vibecodekit_mql5 import doctor

    buf = io.StringIO()
    with redirect_stdout(buf):
        # Run on repo root with --soft so Wine / terminal probes don't fail.
        doctor.main(["--repo-root", str(REPO_ROOT), "--soft", "--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-doctor")


def test_audit_json_envelope():
    from vibecodekit_mql5 import audit

    buf = io.StringIO()
    with redirect_stdout(buf):
        audit.main(["--json"])
    env = _parse_envelope(buf)
    _assert_envelope_shape(env, tool="mql5-audit")


def test_permission_json_envelope(tmp_path: Path):
    from vibecodekit_mql5.permission import orchestrator

    sample = REPO_ROOT / "scaffolds" / "trend" / "ma-cross" / "EAName.mq5"
    state_dir = tmp_path / "rri-state"
    state_dir.mkdir()
    # `mql5-permission` lives at module level and calls sys.argv directly via
    # argparse — we can pass argv by patching it, but `parse_args()` with no
    # args reads sys.argv. The cleanest way is to monkeypatch sys.argv.
    import sys
    saved = sys.argv
    sys.argv = ["mql5-permission", str(sample), "--mode", "personal",
                "--state-dir", str(state_dir), "--json"]
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                orchestrator.main()
            except SystemExit:
                # argparse / main may raise SystemExit; that's fine.
                pass
        env = _parse_envelope(buf)
    finally:
        sys.argv = saved
    _assert_envelope_shape(env, tool="mql5-permission")


@pytest.mark.parametrize("flag", ["--json"])
def test_lint_gate_report_artifact(flag, tmp_path: Path):
    """When --gate-report is provided, the same envelope must hit disk."""

    from vibecodekit_mql5 import lint as lint_cli

    sample = REPO_ROOT / "scaffolds" / "grid" / "hedging" / "EAName.mq5"
    out = tmp_path / "gate-report-lint.json"
    buf = io.StringIO()
    with redirect_stdout(buf):
        lint_cli.main([str(sample), flag, "--gate-report", str(out)])
    assert out.exists()
    on_disk = json.loads(out.read_text())
    _assert_envelope_shape(on_disk, tool="mql5-lint")
    # The matrix block is required so that `mql5-rri-matrix --collect`
    # can find a cell coordinate.
    assert on_disk["matrix"]["dim"] == "d_correctness"
