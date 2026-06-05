"""tests/gates/phase-A/test_agent_io_envelope.py — Envelope schema & helpers.

The Envelope wraps every kit CLI's `--json` output so external agents
(Devin / Claude Code / Cursor) can parse results without per-tool
parsers. This test pins down the schema so it doesn't drift.
"""

from __future__ import annotations

import json

from vibecodekit_mql5 import _agent_io


def test_envelope_minimal_to_dict():
    env = _agent_io.Envelope(
        tool="mql5-test", ok=True, exit_code=0, summary="ok",
    )
    d = env.to_dict()
    assert d["schema_version"] == "1"
    assert d["tool"] == "mql5-test"
    assert d["ok"] is True
    assert d["exit_code"] == 0
    assert d["summary"] == "ok"
    assert d["data"] == {}
    assert d["evidence"] == []
    assert "matrix" not in d  # only present when dim+axis are set


def test_envelope_with_matrix():
    env = _agent_io.Envelope(
        tool="mql5-walkforward",
        ok=True,
        exit_code=0,
        summary="ok",
        matrix_dim="d_robustness",
        matrix_axis="walk_forward",
        matrix_status="PASS",
    )
    d = env.to_dict()
    assert d["matrix"] == {
        "dim": "d_robustness",
        "axis": "walk_forward",
        "status": "PASS",
    }


def test_envelope_evidence_is_copied_not_aliased():
    src = ["a", "b"]
    env = _agent_io.Envelope(
        tool="t", ok=True, exit_code=0, summary="s", evidence=src,
    )
    d = env.to_dict()
    src.append("c")
    # Envelope must NOT share the original list — it would break repeat emissions.
    assert d["evidence"] == ["a", "b"]


def test_envelope_round_trip_json():
    env = _agent_io.Envelope(
        tool="mql5-lint", ok=False, exit_code=1,
        summary="2 ERROR findings",
        data={"finding_count": 2},
        evidence=["scaffolds/grid/hedging/EAName.mq5"],
        matrix_dim="d_correctness", matrix_axis="implement", matrix_status="FAIL",
    )
    d = env.to_dict()
    s = json.dumps(d)
    parsed = json.loads(s)
    assert parsed == d  # JSON round-trip preserves the dict exactly


def test_envelope_matrix_status_defaults_from_ok():
    env = _agent_io.Envelope(
        tool="t", ok=False, exit_code=1, summary="s",
        matrix_dim="d_correctness", matrix_axis="implement",
        matrix_status=None,
    )
    d = env.to_dict()
    assert d["matrix"]["status"] == "FAIL"
