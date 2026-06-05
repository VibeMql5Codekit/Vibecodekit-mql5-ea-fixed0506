"""tests/gates/phase-C/test_matrix_collect.py — `mql5-rri-matrix --collect`.

Wave 1 §W1.4: gates emit ``gate-report-*.json`` envelopes containing a
``matrix`` block ``{dim, axis, status}``. The collector globs that
directory and fills the 8×8 quality matrix automatically — eliminating
the hand-curated JSON file that ``--inputs`` requires.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path


def _write_report(path: Path, *, tool: str, dim: str, axis: str,
                  status: str, summary: str = "") -> None:
    path.write_text(json.dumps({
        "schema_version": "1",
        "tool": tool,
        "ok": status == "PASS",
        "exit_code": 0 if status == "PASS" else 1,
        "summary": summary or f"{tool}: {status}",
        "data": {},
        "evidence": [],
        "matrix": {"dim": dim, "axis": axis, "status": status},
    }, indent=2), encoding="utf-8")


def test_collect_populates_named_cells(tmp_path: Path):
    from vibecodekit_mql5.rri import matrix as mtx

    _write_report(tmp_path / "gate-report-lint.json",
                  tool="mql5-lint", dim="d_correctness", axis="implement",
                  status="PASS")
    _write_report(tmp_path / "gate-report-walkforward.json",
                  tool="mql5-walkforward", dim="d_robustness", axis="walk_forward",
                  status="WARN")
    _write_report(tmp_path / "gate-report-multibroker.json",
                  tool="mql5-multibroker", dim="d_broker_safety", axis="multi_broker",
                  status="FAIL")

    matrix, evidence = mtx.populate_from_gate_reports(tmp_path)
    assert matrix.get("d_correctness", "implement").status == "PASS"
    assert matrix.get("d_robustness", "walk_forward").status == "WARN"
    assert matrix.get("d_broker_safety", "multi_broker").status == "FAIL"
    assert len(evidence) == 3


def test_collect_ignores_unknown_dims_and_files_without_matrix(tmp_path: Path):
    from vibecodekit_mql5.rri import matrix as mtx

    # File with bogus dim — must be ignored, not crash.
    _write_report(tmp_path / "gate-report-bogus.json",
                  tool="mql5-bogus", dim="d_made_up", axis="implement",
                  status="PASS")
    # File without matrix block — also ignored.
    (tmp_path / "gate-report-doctor.json").write_text(json.dumps({
        "schema_version": "1", "tool": "mql5-doctor", "ok": True,
        "exit_code": 0, "summary": "", "data": {}, "evidence": [],
    }), encoding="utf-8")
    # A non-matching filename — must NOT be glob-picked.
    (tmp_path / "scratch.json").write_text("{}", encoding="utf-8")

    matrix, evidence = mtx.populate_from_gate_reports(tmp_path)
    counts = matrix.counts()
    # Nothing should fill — all known-dim cells stay N/A.
    assert counts["PASS"] == 0
    assert counts["FAIL"] == 0
    assert evidence == []


def test_collect_cli_writes_html_and_evidence(tmp_path: Path):
    """Drive `mql5-rri-matrix --collect` via main() and inspect stdout JSON."""

    from vibecodekit_mql5.rri import matrix as mtx
    import sys

    gate_dir = tmp_path / "gates"
    gate_dir.mkdir()
    _write_report(gate_dir / "gate-report-lint.json",
                  tool="mql5-lint", dim="d_correctness", axis="implement",
                  status="PASS")
    _write_report(gate_dir / "gate-report-mb.json",
                  tool="mql5-multibroker", dim="d_broker_safety", axis="multi_broker",
                  status="PASS")

    html_out = tmp_path / "matrix.html"
    saved = sys.argv
    sys.argv = ["mql5-rri-matrix",
                "--collect", str(gate_dir),
                "--output", str(html_out)]
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                mtx.main()
            except SystemExit:
                pass
        payload = json.loads(buf.getvalue())
    finally:
        sys.argv = saved

    assert html_out.exists() and "<html" in html_out.read_text()
    assert payload["counts"]["PASS"] == 2
    # Evidence paths must be present so reviewers can trace each cell to
    # its originating gate-report.
    assert len(payload["evidence"]) == 2


def test_collect_overrides_summary_into_cell_note(tmp_path: Path):
    from vibecodekit_mql5.rri import matrix as mtx

    _write_report(tmp_path / "gate-report-lint.json",
                  tool="mql5-lint", dim="d_correctness", axis="implement",
                  status="PASS", summary="0 ERROR, 1 WARN")
    matrix, _ = mtx.populate_from_gate_reports(tmp_path)
    cell = matrix.get("d_correctness", "implement")
    assert "ERROR" in cell.note
