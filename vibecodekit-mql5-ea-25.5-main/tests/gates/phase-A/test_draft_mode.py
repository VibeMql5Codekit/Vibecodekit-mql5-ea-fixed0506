"""Tests for the W2.3 `--draft` flag across Wave-1 gates.

Draft mode downgrades every gate failure to a non-blocking warning so
the chat-driven build loop (`mql5-auto-build --spec ... --draft`) can
iterate on a half-finished EA without the pipeline slamming the door
on every commit. The semantics are deliberately distinct from
``mql5-doctor --soft`` (which only relaxes environment probes).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from vibecodekit_mql5 import _agent_io
from vibecodekit_mql5._agent_io import Envelope, apply_draft


REPO = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# Helper unit tests
# --------------------------------------------------------------------------

def test_apply_draft_noop_when_disabled():
    env = Envelope(tool="t", ok=False, exit_code=1, summary="x")
    out = apply_draft(env, draft=False)
    assert out is env
    assert out.ok is False
    assert out.exit_code == 1
    assert "draft" not in out.data


def test_apply_draft_downgrades_failing_envelope():
    env = Envelope(
        tool="t", ok=False, exit_code=1, summary="2 ERROR",
        matrix_status="FAIL",
    )
    apply_draft(env, draft=True)
    assert env.ok is True
    assert env.exit_code == 0
    assert env.data["draft"] is True
    assert env.data["original_ok"] is False
    assert env.data["original_exit_code"] == 1
    assert env.matrix_status == "WARN"
    assert env.data["original_matrix_status"] == "FAIL"
    assert "draft mode" in env.summary.lower()


def test_apply_draft_preserves_passing_envelope():
    env = Envelope(
        tool="t", ok=True, exit_code=0, summary="clean",
        matrix_status="PASS",
    )
    apply_draft(env, draft=True)
    # ok was already true; draft still leaves a marker so downstream
    # consumers can tell the gate ran in draft mode.
    assert env.ok is True
    assert env.exit_code == 0
    assert env.data["draft"] is True
    assert env.matrix_status == "PASS"


def test_add_draft_flag_registers_argument():
    import argparse
    p = argparse.ArgumentParser()
    _agent_io.add_draft_flag(p)
    args = p.parse_args([])
    assert args.draft is False
    args = p.parse_args(["--draft"])
    assert args.draft is True


# --------------------------------------------------------------------------
# Gate-level: lint downgrades a known AP-2 ERROR
# --------------------------------------------------------------------------

# A small synthetic EA that triggers an ERROR-level finding so the lint
# gate fails in non-draft mode. We use AP-7 (`Print(` reachable from
# OnTick without rate-limiting) — easiest to provoke deterministically.
_BAD_EA_SOURCE = """
//+------------------------------------------------------------------+
//| Synthetic EA used by the --draft test                            |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

void OnTick()
{
    // AP-1 trigger: OrderSend without a stop-loss argument.
    trade.Buy(0.1, _Symbol);
}
"""


def _write_bad_ea(tmp_path):
    p = tmp_path / "BadEA.mq5"
    p.write_text(_BAD_EA_SOURCE, encoding="utf-8")
    return p


def test_lint_draft_exits_zero_on_errors(tmp_path):
    ea = _write_bad_ea(tmp_path)
    # First: confirm non-draft mode actually fails.
    fail = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.lint", str(ea), "--json"],
        capture_output=True, text=True,
    )
    assert fail.returncode != 0, "test EA must be ERROR-level for the test to be meaningful"
    payload = json.loads(fail.stdout)
    assert payload["ok"] is False

    # Now: same input + --draft must exit 0 and mark draft=True.
    draft = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.lint",
         str(ea), "--json", "--draft"],
        capture_output=True, text=True,
    )
    assert draft.returncode == 0
    payload = json.loads(draft.stdout)
    assert payload["ok"] is True
    assert payload["exit_code"] == 0
    assert payload["data"]["draft"] is True
    assert payload["data"]["original_ok"] is False
    assert payload["matrix"]["status"] == "WARN"  # downgraded from FAIL


def test_lint_draft_with_clean_file_stays_pass(tmp_path):
    # Empty file → no findings → ok stays True; draft marker still appears.
    empty = tmp_path / "Empty.mq5"
    empty.write_text("#property strict\nvoid OnTick(){}\n", encoding="utf-8")
    res = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.lint",
         str(empty), "--json", "--draft"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["data"]["draft"] is True
    assert payload["matrix"]["status"] == "PASS"


# --------------------------------------------------------------------------
# Trader-check: stub a synthetic EA that fails the 15/17 threshold and
# verify --draft downgrades the verdict.
# --------------------------------------------------------------------------

_THIN_EA = """
#property strict
void OnTick(){}
"""


def test_trader_check_draft_exits_zero(tmp_path):
    ea = tmp_path / "Thin.mq5"
    ea.write_text(_THIN_EA, encoding="utf-8")

    fail = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.trader_check",
         str(ea), "--json"],
        capture_output=True, text=True,
    )
    assert fail.returncode != 0, fail.stdout
    payload = json.loads(fail.stdout)
    assert payload["ok"] is False

    draft = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.trader_check",
         str(ea), "--json", "--draft"],
        capture_output=True, text=True,
    )
    assert draft.returncode == 0
    payload = json.loads(draft.stdout)
    assert payload["ok"] is True
    assert payload["data"]["draft"] is True


# --------------------------------------------------------------------------
# Permission: top-level orchestrator must accept --draft as well.
# --------------------------------------------------------------------------

def test_permission_orchestrator_accepts_draft_flag():
    """Smoke: ``--help`` mentions ``--draft`` so the operator can discover
    the flag without grepping the source."""

    res = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.permission.orchestrator", "-h"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0
    assert "--draft" in res.stdout


# --------------------------------------------------------------------------
# Auto-build: --draft implies --no-compile --no-gate --no-docs
# --------------------------------------------------------------------------

def test_auto_build_help_advertises_draft():
    res = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.auto_build", "-h"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0
    assert "--draft" in res.stdout
    # argparse wraps long help strings and may break across `--no- compile`
    # at terminal width; strip every space before matching so the test
    # is robust against width-dependent rendering.
    flat = res.stdout.replace(" ", "").replace("\n", "")
    assert "--no-compile--no-gate--no-docs" in flat


def test_auto_build_draft_end_to_end(tmp_path):
    """Run the full pipeline on a minimal spec; --draft must exit 0
    even though we have no Wine + no MetaEditor + no permission gate.
    """

    spec = tmp_path / "ea-spec.yaml"
    spec.write_text(
        "name: DraftEA\n"
        "preset: trend\n"
        "stack: netting\n"
        "symbol: EURUSD\n"
        "timeframe: H1\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "build" / "DraftEA"
    res = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.auto_build",
         "--spec", str(spec), "--out-dir", str(out_dir), "--draft"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert res.returncode == 0, res.stderr
    # auto-build-report.json should be in the out_dir; verify it's there.
    assert (out_dir / "auto-build-report.json").is_file()
