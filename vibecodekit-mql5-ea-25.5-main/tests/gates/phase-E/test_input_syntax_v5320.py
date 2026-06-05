"""Phase E gate — ``input(name=...)`` attribute syntax doc (build 5320).

W7.4 from the v1.0.1 audit: the kit must document the new attribute
form so users targeting build 5320+ have a single source of truth
rather than forking the surface into a ``.set`` file.

This gate enforces the *documentation*, not a code generator —
scaffolds intentionally stay on the legacy form so they compile on
every supported build (4620 → 5572).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REF_80 = REPO_ROOT / "docs" / "references" / "80-input-syntax.md"


def test_ref_80_exists() -> None:
    assert REF_80.is_file(), "expected docs/references/80-input-syntax.md"


def test_ref_80_has_frontmatter_with_build_5320_tag() -> None:
    text = REF_80.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "ref 80 missing YAML frontmatter"
    block = m.group(1)
    assert "id: 80-input-syntax" in block
    assert "build5320" in block, (
        "ref 80 must tag itself with build5320 so the search/index "
        "tooling can group it with other build-5320 features"
    )
    assert "applicable_phase: A" in block, (
        "input declarations are Phase-A surface decisions"
    )


def test_ref_80_documents_attribute_form() -> None:
    text = REF_80.read_text(encoding="utf-8")
    # The 6 attributes the kit explicitly supports per the audit.
    for attr in ("name", "min", "max", "step", "tooltip", "optimisable"):
        assert attr in text, f"ref 80 must document {attr!r} attribute"


def test_ref_80_pins_build_5320_minimum() -> None:
    text = REF_80.read_text(encoding="utf-8")
    assert "5320" in text, "ref 80 must pin minimum build 5320"


def test_ref_80_shows_legacy_and_attribute_form_side_by_side() -> None:
    """A migration ref is only useful when both forms are in scope."""
    text = REF_80.read_text(encoding="utf-8").lower()
    # Legacy form looks like: input int InpFoo = ...;
    assert re.search(r"input\s+(int|double)\s+inp", text), (
        "ref 80 must show a legacy `input <type> InpX = …;` example"
    )
    # Attribute form looks like: input(name=...)  int InpFoo = ...;
    assert re.search(r"input\s*\(\s*name\s*=", text), (
        "ref 80 must show an `input(name=…)` example"
    )


def test_ref_80_respects_ap5_input_cap() -> None:
    """Plan v5 §6 / AP-5 caps optimiser surface at 6 inputs — the
    attribute-form ``optimisable=false`` knob does *not* exempt an
    input.  The audit asked us to make this explicit."""
    text = REF_80.read_text(encoding="utf-8")
    assert "AP-5" in text, (
        "ref 80 must call AP-5 by name so readers can't miss the cap"
    )


def test_kit_scaffolds_default_to_legacy_input_form() -> None:
    """Sanity: the *scaffolds* must keep compiling on build < 5320,
    so they default to the legacy syntax even though the docs cover
    the new attribute form."""
    scaffolds = (REPO_ROOT / "scaffolds").rglob("*.mq5")
    saw_at_least_one = False
    for path in scaffolds:
        saw_at_least_one = True
        text = path.read_text(encoding="utf-8")
        # We allow the docs to discuss `input(name=...)` but no scaffold
        # source may actually use it yet (forward-compat decision).
        assert not re.search(r"input\s*\(\s*name\s*=", text), (
            f"{path.relative_to(REPO_ROOT)}: scaffold uses build-5320 "
            "attribute form; keep scaffolds on the legacy form"
        )
    assert saw_at_least_one, "scaffolds directory unexpectedly empty"
