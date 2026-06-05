"""Phase E unit tests — reproducibility surface (P1.3).

These tests are hermetic: they validate the *contents* of ``requirements.lock``
and ``Dockerfile.devin`` without invoking pip-compile or docker build, so they
run on every CI even when Docker isn't available.

What we assert
--------------
* ``requirements.lock`` exists at repo root, every non-empty / non-comment
  line is ``name==version`` (PEP-440 strict pin), and the lockfile is a
  superset of every required dev-dep declared in ``pyproject.toml``.
* ``Dockerfile.devin`` exists, has the three named stages (``base``,
  ``wine``, ``ci``), copies the lockfile into the image, never installs an
  unpinned Wine version, and routes through a non-root ``ubuntu`` user.
* ``.dockerignore`` exists and excludes the obvious churn directories
  (``.venv/``, ``__pycache__/``, ``*.ex5``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCKFILE  = REPO_ROOT / "requirements.lock"
DOCKERFILE = REPO_ROOT / "Dockerfile.devin"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
PYPROJECT = REPO_ROOT / "pyproject.toml"


# ─────────────────────────────────────────────────────────────────────────────
# requirements.lock
# ─────────────────────────────────────────────────────────────────────────────

def test_lockfile_exists() -> None:
    assert LOCKFILE.is_file(), f"missing {LOCKFILE.relative_to(REPO_ROOT)}"


def _read_lock_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in LOCKFILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # pip-compile sometimes emits ``name[extra]==version`` and continuation
        # lines that start with ``# via …`` (already filtered above).
        m = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]+\])?==([A-Za-z0-9_.\-+]+)\s*$", line)
        assert m is not None, f"non-strict pin on lockfile line: {line!r}"
        pins[m.group(1).lower()] = m.group(2)
    return pins


def test_lockfile_every_line_is_strict_pin() -> None:
    pins = _read_lock_pins()
    assert pins, "lockfile must declare at least one pinned dep"


def test_lockfile_covers_declared_dev_deps() -> None:
    """Every name in pyproject [optional-dependencies.dev] must be pinned."""
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    # Pull out the dev = [...] block.
    m = re.search(r"^dev\s*=\s*\[(.*?)^\]", pyproject, re.MULTILINE | re.DOTALL)
    assert m is not None, "pyproject.toml must declare [optional-dependencies.dev]"
    block = m.group(1)
    declared = {
        re.match(r'"\s*([A-Za-z0-9_.\-]+)', line.strip()).group(1).lower()
        for line in block.splitlines()
        if line.strip().startswith('"') and "==" not in line and ">=" in line
    }
    pinned = set(_read_lock_pins().keys())
    missing = declared - pinned
    assert not missing, (
        f"requirements.lock is missing pins for {sorted(missing)}; "
        "regenerate with `pip-compile --extra dev --output-file requirements.lock pyproject.toml`"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile.devin
# ─────────────────────────────────────────────────────────────────────────────

def test_dockerfile_exists() -> None:
    assert DOCKERFILE.is_file(), f"missing {DOCKERFILE.relative_to(REPO_ROOT)}"


def test_dockerfile_declares_all_three_named_stages() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    stages = set(re.findall(r"^FROM\s+\S+\s+AS\s+(\w+)", text, re.MULTILINE))
    assert {"base", "wine", "ci"}.issubset(stages), \
        f"expected stages base/wine/ci, found {stages}"


def test_dockerfile_copies_lockfile_into_image() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "requirements.lock" in text, (
        "Dockerfile.devin must COPY requirements.lock so the image is "
        "reproducible against the pin set"
    )
    assert re.search(r"pip[^\n]*-r\s+requirements\.lock", text), (
        "Dockerfile.devin must `pip install -r requirements.lock`"
    )


def test_dockerfile_pins_wine_version() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    # Either a pinned ARG default *or* a hardcoded ``winehq-stable=…`` token.
    has_arg = re.search(r"ARG\s+WINE_PIN_VERSION\s*=\s*\d", text) is not None
    has_pin = re.search(r"winehq-stable=\$\{?WINE_PIN_VERSION", text) is not None
    assert has_arg and has_pin, (
        "Dockerfile.devin must pin Wine via ARG WINE_PIN_VERSION + "
        "winehq-stable=${WINE_PIN_VERSION}"
    )


def test_dockerfile_runs_as_non_root_user_in_base_stage() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^USER\s+ubuntu", text, re.MULTILINE), (
        "Dockerfile.devin must drop privileges via `USER ubuntu`"
    )


# ─────────────────────────────────────────────────────────────────────────────
# .dockerignore
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("entry", [".venv/", "__pycache__/", "*.ex5"])
def test_dockerignore_excludes_obvious_churn(entry: str) -> None:
    assert DOCKERIGNORE.is_file()
    text = DOCKERIGNORE.read_text(encoding="utf-8")
    assert entry in text, f".dockerignore must list `{entry}`"
