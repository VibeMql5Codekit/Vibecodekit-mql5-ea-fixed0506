"""Wave-3 W3.B — EA-bug golden-dataset test runner.

Drives ``mql5-lint`` over every fixture under
``tests/fixtures/ea-bugs/`` and asserts that the codes pinned in each
fixture's ``expected.json`` actually fire (``must_contain``) and that
no code on the exclusion list fires (``must_not_contain``).

The dataset is the load-bearing contract for the linters; if a
detector regresses, the matching golden fixture catches it. See
:file:`tests/fixtures/ea-bugs/README.md` for the schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit_mql5 import lint as lint_mod


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "ea-bugs"


def _discover() -> list[tuple[str, Path]]:
    """Return ``(slug, folder)`` for every fixture folder on disk."""

    out: list[tuple[str, Path]] = []
    for folder in sorted(FIXTURE_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        if not (folder / "EA.mq5").exists():
            continue
        if not (folder / "expected.json").exists():
            continue
        out.append((folder.name, folder))
    return out


_FIXTURES = _discover()


def test_dataset_has_at_least_20_fixtures():
    """Wave-3 W3.B target: ship 20 EA-bug fixtures so every detector
    that's emitted by mql5-lint has at least one real EA pinning it.

    Don't lower this number when adding more — only raise it.
    """

    assert len(_FIXTURES) >= 20, (
        f"Wave-3 W3.B target is ≥20 fixtures, found {len(_FIXTURES)}. "
        f"Did a folder get deleted? See {FIXTURE_ROOT}/README.md."
    )


@pytest.mark.parametrize("slug,folder", _FIXTURES, ids=[s for s, _ in _FIXTURES])
def test_ea_bug_fixture_triggers_expected_findings(slug: str, folder: Path):
    """For each ea-bug fixture, the primary AP code(s) in
    ``expected.json#/must_contain`` MUST appear among the lint findings.
    Any code in ``must_not_contain`` MUST NOT appear.
    """

    spec = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    findings = lint_mod.lint_file(folder / "EA.mq5")
    codes = sorted({f.code for f in findings})

    for required in spec["must_contain"]:
        assert required in codes, (
            f"{slug}: required code {required!r} not found.\n"
            f"  expected.json: {spec}\n"
            f"  lint codes seen: {codes}"
        )

    for forbidden in spec.get("must_not_contain", []):
        assert forbidden not in codes, (
            f"{slug}: forbidden code {forbidden!r} unexpectedly fired.\n"
            f"  expected.json: {spec}\n"
            f"  lint codes seen: {codes}"
        )


def test_primary_code_is_in_must_contain():
    """Every fixture's primary_code must be listed in its must_contain.

    Guards against authoring drift — the docstring schema in the
    fixture README says primary_code is the canonical AP this fixture
    is supposed to prove; we therefore must assert on it.
    """

    for slug, folder in _FIXTURES:
        spec = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
        assert spec["primary_code"] in spec["must_contain"], (
            f"{slug}: primary_code {spec['primary_code']!r} missing from "
            f"must_contain {spec['must_contain']!r}"
        )


def test_every_ap_detector_covered_by_dataset():
    """Every AP code emitted by the lint detectors that the dataset
    targets must have at least one fixture as its ``primary_code``.

    The list below mirrors the detectors registered in
    :mod:`vibecodekit_mql5.lint` + :mod:`.lint_best_practice`, minus
    the four that need contextual artefacts our static fixtures
    cannot produce (AP-6 walk-forward meta, AP-9 multi-entry,
    AP-16 reinvent-stdlib, AP-19 ONNX, AP-22 signal-placeholder).
    """

    expected_primaries = {
        "AP-1", "AP-2", "AP-3", "AP-4", "AP-5",
        "AP-7", "AP-8", "AP-10", "AP-11", "AP-12",
        "AP-13", "AP-14", "AP-15", "AP-17", "AP-18",
        "AP-20", "AP-21", "AP-23", "AP-24", "AP-25",
    }

    have = {
        json.loads((folder / "expected.json").read_text(encoding="utf-8"))["primary_code"]
        for _, folder in _FIXTURES
    }
    missing = expected_primaries - have
    assert not missing, (
        f"ea-bugs dataset is missing primary fixtures for: "
        f"{sorted(missing)}"
    )
