"""Phase E unit tests — every reference doc must have valid YAML frontmatter."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
REFS_DIR = REPO_ROOT / "docs" / "references"

REFS = sorted(p.name for p in REFS_DIR.glob("*.md"))

_RE_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_KEYS = {"id", "title", "tags", "applicable_phase"}


@pytest.mark.parametrize("name", REFS)
def test_reference_has_valid_frontmatter(name: str) -> None:
    text = (REFS_DIR / name).read_text(encoding="utf-8")
    m = _RE_FRONT.match(text)
    assert m, f"{name}: no YAML frontmatter at top"
    block = m.group(1)
    keys = {ln.split(":", 1)[0].strip()
            for ln in block.splitlines() if ":" in ln}
    missing = REQUIRED_KEYS - keys
    assert not missing, f"{name}: missing frontmatter keys {missing}"


def test_reference_count_matches_audit() -> None:
    # audit-plan-v5 lists 28 references (50-survey through 79-pip-norm);
    # v1.0.1 build-5320 audit adds ref 80-input-syntax = 29.
    assert len(REFS) == 29, f"expected 29 refs, got {len(REFS)}"


def test_docs_quickstart_and_commands_present() -> None:
    for f in ("QUICKSTART.md", "COMMANDS.md", "MIGRATE-VPS.md"):
        p = REPO_ROOT / "docs" / f
        assert p.exists(), f"missing {f}"
        assert p.read_text(encoding="utf-8").startswith("---\n"), f"{f}: no frontmatter"
