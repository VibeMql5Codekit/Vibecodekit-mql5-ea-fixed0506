"""Tests for vibecodekit_mql5.rri.matrix — 3 unit tests covering 64-cell
populate, HTML render, and threshold gating."""

from __future__ import annotations

import re

from vibecodekit_mql5.rri import matrix as mx


def test_64_cells_populate_and_count():
    m = mx.MatrixReport()
    mx.populate_full(m, "PASS")
    counts = m.counts()
    assert counts["PASS"] == 64
    assert counts["WARN"] == 0
    assert counts["FAIL"] == 0
    assert counts["N/A"] == 0
    # Down-grade two cells; counts shift accordingly.
    m.set("d_risk", "design", "WARN")
    m.set("d_perf", "live_canary", "FAIL")
    counts = m.counts()
    assert counts["PASS"] == 62
    assert counts["WARN"] == 1
    assert counts["FAIL"] == 1


def test_html_render_contains_status_cells():
    m = mx.MatrixReport()
    mx.populate_full(m, "PASS")
    m.set("d_correctness", "design", "FAIL", note="missing review")
    html = mx.render_html(m)
    assert "<table" in html
    assert "PASS" in html
    assert "FAIL" in html
    # Every dim + axis label appears in the header / row labels.
    for dim in mx.DIMS:
        assert dim in html
    for axis in mx.AXES:
        assert axis in html
    # Tooltip carries the note for the FAIL cell.
    assert re.search(r'title="missing review"', html)


def test_personal_and_enterprise_thresholds():
    m = mx.MatrixReport()
    mx.populate_full(m, "PASS")
    assert m.passes_personal() and m.passes_enterprise()

    # 7 WARNs → still personal-OK (≤8) but not enterprise (>4).
    cells = [(d, a) for d in mx.DIMS for a in mx.AXES][:7]
    for d, a in cells:
        m.set(d, a, "WARN")
    assert m.passes_personal()
    assert not m.passes_enterprise()

    # 1 FAIL anywhere → both fail.
    m.set("d_risk", "backtest", "FAIL")
    assert not m.passes_personal()
    assert not m.passes_enterprise()
