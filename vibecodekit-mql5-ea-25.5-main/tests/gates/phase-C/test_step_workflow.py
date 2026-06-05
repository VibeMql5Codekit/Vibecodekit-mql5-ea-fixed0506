"""Tests for vibecodekit_mql5.rri.step_workflow — 4 unit tests covering the
8-step engine, transitions, mode-dependent required steps, and template
files."""

from __future__ import annotations

import pytest

from vibecodekit_mql5.rri import step_workflow as sw


def test_8_steps_in_canonical_order():
    assert sw.STEPS == (
        "scan", "rri", "vision", "blueprint", "tip", "build", "verify", "refine",
    )
    assert [sw.STEP_NUMBERS[s] for s in sw.STEPS] == list(range(1, 9))


@pytest.mark.parametrize("a,b,expected", [
    ("scan", "rri", True),         # forward 1 → 2
    ("rri", "vision", True),       # forward 2 → 3
    ("verify", "refine", True),    # forward 7 → 8
    ("refine", "rri", True),       # the only legal backward jump
    ("scan", "verify", False),     # skipping ahead
    ("verify", "scan", False),     # arbitrary backward
    ("scan", "scan", False),       # self-loop
    ("not-a-step", "rri", False),  # unknown source
])
def test_is_valid_transition(a, b, expected):
    assert sw.is_valid_transition(a, b) is expected


def test_required_steps_per_mode():
    assert sw.required_steps("personal") == ("scan", "build", "verify")
    assert sw.required_steps("team") == (
        "scan", "rri", "vision", "build", "verify", "refine",
    )
    assert sw.required_steps("enterprise") == sw.STEPS
    with pytest.raises(ValueError):
        sw.required_steps("nope")


def test_workflow_complete_sentinels(tmp_path):
    # No sentinels → not complete in any mode that requires any step.
    assert not sw.is_workflow_complete(tmp_path, "personal")
    # Drop the 3 personal-mode sentinels → complete in personal but not enterprise.
    for s in sw.required_steps("personal"):
        (tmp_path / f"{s}.done").touch()
    assert sw.is_workflow_complete(tmp_path, "personal")
    assert not sw.is_workflow_complete(tmp_path, "enterprise")
    # All 8 sentinels → complete in enterprise.
    for s in sw.STEPS:
        (tmp_path / f"{s}.done").touch()
    assert sw.is_workflow_complete(tmp_path, "enterprise")
    # Templates render (smoke check on one).
    body = sw.render_template("verify")
    assert "Step 7 / 8 — VERIFY" in body
