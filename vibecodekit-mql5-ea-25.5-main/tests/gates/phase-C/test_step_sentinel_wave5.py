"""Wave 5.2 — step-output activity-checkbox validator + layer-5 hook."""

from __future__ import annotations

from pathlib import Path

from vibecodekit_mql5.permission import layer5_methodology as layer5
from vibecodekit_mql5.rri import step_sentinel as ss


# ---------------------------------------------------------------------------
# audit_step_output
# ---------------------------------------------------------------------------


VISION_FULLY_TICKED = """\
# Step 3 / 8 — VISION

## Activities
- [x] Define the minimum viable change set
- [x] Estimate effort by file
- [x] Enumerate risks
"""

VISION_PARTIAL = """\
# Step 3 / 8 — VISION

## Activities
- [x] Define the minimum viable change set
- [ ] Estimate effort by file
- [ ] Enumerate risks
"""

VISION_EMPTY = """\
# Step 3 / 8 — VISION

Skeleton with no activities section yet.
"""


def _write_step(state_dir: Path, step_num: int, step_name: str, body: str) -> Path:
    p = state_dir / f"step-{step_num}-{step_name}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def test_audit_full_tick_passes_at_100_threshold(tmp_path: Path) -> None:
    _write_step(tmp_path, 3, "vision", VISION_FULLY_TICKED)
    audit = ss.audit_step_output("vision", state_dir=tmp_path)
    assert audit.total == 3
    assert audit.ticked == 3
    assert audit.ratio == 1.0
    assert audit.untouched == ()
    assert ss.passes_threshold(audit, 1.0) is True


def test_audit_partial_tick_fails_at_80_passes_at_30(tmp_path: Path) -> None:
    _write_step(tmp_path, 3, "vision", VISION_PARTIAL)
    audit = ss.audit_step_output("vision", state_dir=tmp_path)
    assert audit.total == 3
    assert audit.ticked == 1
    assert round(audit.ratio, 4) == 0.3333
    assert "Estimate effort by file" in audit.untouched
    assert ss.passes_threshold(audit, 0.8) is False
    assert ss.passes_threshold(audit, 0.3) is True


def test_audit_empty_activities_passes(tmp_path: Path) -> None:
    """No activities means no enforcement target — passes every threshold."""
    _write_step(tmp_path, 3, "vision", VISION_EMPTY)
    audit = ss.audit_step_output("vision", state_dir=tmp_path)
    assert audit.total == 0
    assert audit.ticked == 0
    assert ss.passes_threshold(audit, 1.0) is True


def test_audit_missing_file_is_noop(tmp_path: Path) -> None:
    """A missing step output passes (legacy sentinel-only check still applies)."""
    audit = ss.audit_step_output("vision", state_dir=tmp_path)
    assert audit.total == 0
    assert audit.output_path is None or not audit.output_path.is_file()
    assert ss.passes_threshold(audit, 1.0) is True


def test_audit_uses_explicit_output_path(tmp_path: Path) -> None:
    p = tmp_path / "elsewhere.md"
    p.write_text(VISION_FULLY_TICKED, encoding="utf-8")
    audit = ss.audit_step_output("vision", output_path=p)
    assert audit.output_path == p
    assert audit.ticked == 3


def test_audit_only_activities_section_counted(tmp_path: Path) -> None:
    """Checkboxes outside ## Activities must not count."""
    body = """\
# Step 4
## Invariants
- [ ] AP-1 SL set
- [ ] AP-7 magic registered

## Activities
- [x] One done
- [ ] One pending
"""
    _write_step(tmp_path, 4, "blueprint", body)
    audit = ss.audit_step_output("blueprint", state_dir=tmp_path)
    assert audit.total == 2
    assert audit.ticked == 1


# ---------------------------------------------------------------------------
# layer-5 integration
# ---------------------------------------------------------------------------


def _touch_all_sentinels(state_dir: Path, steps: tuple[str, ...]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    for s in steps:
        (state_dir / f"{s}.done").touch()


def test_layer5_personal_default_skips(tmp_path: Path) -> None:
    """Personal mode w/ default flags still trivially passes."""
    result = layer5.gate(tmp_path / "missing", "personal")
    assert result["ok"] is True
    assert result.get("skipped") is True


def test_layer5_team_full_tick_passes(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    required = ("scan", "rri", "vision", "build", "verify", "refine")
    _touch_all_sentinels(state, required)
    _write_step(state, 3, "vision", VISION_FULLY_TICKED)
    result = layer5.gate(state, "team", enforce_activities=True)
    assert result["ok"] is True
    assert result["activity_under_threshold"] == []


def test_layer5_team_partial_tick_fails(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    required = ("scan", "rri", "vision", "build", "verify", "refine")
    _touch_all_sentinels(state, required)
    _write_step(state, 3, "vision", VISION_PARTIAL)
    result = layer5.gate(state, "team", enforce_activities=True)
    assert result["ok"] is False
    assert "vision" in result["activity_under_threshold"]
    # The ratio + untouched list must surface for the operator.
    vision_audit = next(a for a in result["activity_audits"] if a["step"] == "vision")
    assert vision_audit["ticked"] == 1
    assert vision_audit["total_activities"] == 3
    assert "Estimate effort by file" in vision_audit["untouched"]


def test_layer5_threshold_override(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    required = ("scan", "rri", "vision", "build", "verify", "refine")
    _touch_all_sentinels(state, required)
    _write_step(state, 3, "vision", VISION_PARTIAL)
    # Lenient threshold lets the partial-tick through.
    lenient = layer5.gate(
        state, "team",
        enforce_activities=True,
        activity_threshold=0.3,
    )
    assert lenient["ok"] is True
    # Strict threshold flags it.
    strict = layer5.gate(
        state, "team",
        enforce_activities=True,
        activity_threshold=1.0,
    )
    assert strict["ok"] is False


def test_layer5_personal_with_enforce_runs_audit(tmp_path: Path) -> None:
    """Personal mode + enforce-activities runs the audit instead of short-circuiting."""
    state = tmp_path / ".rri-state"
    required = ("scan", "build", "verify")
    _touch_all_sentinels(state, required)
    result = layer5.gate(state, "personal", enforce_activities=True)
    # No companion files = no activities = passes default threshold trivially
    assert result["ok"] is True
    assert "skipped" not in result
    assert result["activity_threshold"] == ss.DEFAULT_THRESHOLDS["personal"]


def test_layer5_default_thresholds_progression() -> None:
    """Threshold should strictly increase from personal → team → enterprise."""
    assert (
        ss.DEFAULT_THRESHOLDS["personal"]
        < ss.DEFAULT_THRESHOLDS["team"]
        <= ss.DEFAULT_THRESHOLDS["enterprise"]
    )
    assert ss.DEFAULT_THRESHOLDS["enterprise"] == 1.0
