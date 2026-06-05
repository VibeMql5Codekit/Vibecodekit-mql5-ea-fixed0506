"""tests/gates/phase-A/test_manifest_generation.py — mql5-manifest CLI.

The manifest gives external agents a one-shot discovery surface for the
55+ kit CLIs. Two failure modes we want to nail down:

1. Every entry in `pyproject.toml [project.scripts]` appears in the
   emitted manifest (and vice versa — no phantom tools).
2. The boolean capability flags (`supports_json`, `supports_sarif`,
   `supports_gate_report`) match what the source code actually exposes.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_manifest_round_trip_matches_pyproject():
    from vibecodekit_mql5 import manifest as mfst

    scripts = mfst._load_pyproject_scripts()
    built = mfst.build_manifest()
    listed = {t["name"]: t for t in built["tools"]}
    assert set(scripts) == set(listed), (
        f"manifest names diverge from pyproject [project.scripts] "
        f"(missing={set(scripts) - set(listed)}, "
        f"extra={set(listed) - set(scripts)})"
    )


def test_manifest_schema_version():
    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    assert built["schema_version"] == "1"
    assert built["kit"] == "vibecodekit-mql5-ea"
    assert built["kit_version"]  # non-empty


@pytest.mark.parametrize("tool_name,flag", [
    ("mql5-lint", "supports_json"),
    ("mql5-lint", "supports_sarif"),
    ("mql5-lint", "supports_gate_report"),
    ("mql5-trader-check", "supports_json"),
    ("mql5-trader-check", "supports_gate_report"),
    ("mql5-fixture", "supports_json"),
    ("mql5-walkforward", "supports_json"),
    ("mql5-walkforward", "supports_gate_report"),
])
def test_manifest_capability_flags(tool_name: str, flag: str):
    """Smoke-test the heuristic — every flag set True must be reachable."""

    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    tool = next(t for t in built["tools"] if t["name"] == tool_name)
    assert tool[flag] is True, f"{tool_name}.{flag} expected True"


def test_manifest_cli_emit_to_stdout():
    from vibecodekit_mql5 import manifest as mfst

    buf = io.StringIO()
    with redirect_stdout(buf):
        mfst.main(["--emit"])
    parsed = json.loads(buf.getvalue())
    assert parsed["schema_version"] == "1"
    assert isinstance(parsed["tools"], list)
    assert len(parsed["tools"]) >= 55  # 55 baseline + manifest + fixture


def test_manifest_cli_emit_to_file(tmp_path: Path):
    from vibecodekit_mql5 import manifest as mfst

    out = tmp_path / "manifest.json"
    mfst.main(["--emit", "--output", str(out)])
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["kit"] == "vibecodekit-mql5-ea"


def test_manifest_validate_detects_drift(tmp_path: Path):
    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    # Drop one tool to simulate a stale manifest checked in to the repo.
    built["tools"] = [t for t in built["tools"] if t["name"] != "mql5-lint"]
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(built), encoding="utf-8")
    errs = mfst.validate_manifest(json.loads(path.read_text(encoding="utf-8")))
    assert any("mql5-lint" in e for e in errs), errs


def test_compile_does_not_falsely_advertise_envelope_json():
    """`mql5-compile` has a *legacy* ``--json`` flag that emits a raw
    ``CompileResult.to_dict()`` — not the Wave-1 ``Envelope`` schema.

    The manifest heuristic must not flag it as ``supports_json=true``
    or external agents would call it expecting the envelope and crash
    on the missing ``schema_version`` / ``ok`` keys. Pinning this
    behaviour here keeps the heuristic narrow.
    """

    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    compile_tool = next(t for t in built["tools"] if t["name"] == "mql5-compile")
    assert compile_tool["supports_json"] is False, (
        "mql5-compile has a legacy --json flag emitting CompileResult, "
        "not the Wave-1 Envelope. The manifest heuristic must stay narrow."
    )


def test_manifest_itself_advertises_no_envelope_flags():
    """`mql5-manifest`'s CLI exposes only --emit / --validate; the
    needle strings live in its source as data. Regression guard for
    the earlier self-reference false positive."""

    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    tool = next(t for t in built["tools"] if t["name"] == "mql5-manifest")
    assert tool["supports_json"] is False
    assert tool["supports_sarif"] is False
    assert tool["supports_gate_report"] is False


def test_init_does_advertise_envelope_json():
    """`mql5-init` is a new (W2.1) CLI that opts into the agent
    envelope via ``--json``; the manifest must surface that."""

    from vibecodekit_mql5 import manifest as mfst

    built = mfst.build_manifest()
    tool = next(t for t in built["tools"] if t["name"] == "mql5-init")
    assert tool["supports_json"] is True


def test_root_manifest_committed_is_in_sync():
    """The `manifest.json` committed at repo root MUST mirror the live build.

    If this fails, regenerate with `python -m vibecodekit_mql5.manifest
    --emit --output manifest.json` and commit the result.
    """

    from vibecodekit_mql5 import manifest as mfst

    root_manifest = REPO_ROOT / "manifest.json"
    assert root_manifest.exists(), "root manifest.json missing"
    on_disk = json.loads(root_manifest.read_text(encoding="utf-8"))
    live = mfst.build_manifest()
    # Compare just the tool *names* (descriptions can drift on minor docstring edits
    # without breaking the agent contract).
    assert {t["name"] for t in on_disk["tools"]} == {t["name"] for t in live["tools"]}
    # Wave 5.1 follow-up: pin kit_version so a forgotten `mql5-manifest --emit`
    # cannot ship a stale 1.x.y while VERSION / __version__ / pyproject have
    # moved on.
    assert on_disk["kit_version"] == live["kit_version"], (
        f"manifest.json kit_version={on_disk['kit_version']!r} is stale; "
        f"VERSION says {live['kit_version']!r}. Regenerate with "
        "`python -m vibecodekit_mql5.manifest --emit --output manifest.json`."
    )
