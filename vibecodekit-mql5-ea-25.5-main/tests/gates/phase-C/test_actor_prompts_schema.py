"""Pin the Wave-6.1 ``docs/agent-prompts/actors/*.md`` contract.

Each actor prompt MUST exist, MUST start with a YAML frontmatter block,
and MUST declare the fields the kit relies on to enforce the Triangle of
Power split:

* ``actor`` — slug matching the filename (``chu-nha``, ``chu-thau``,
  ``tho-thi-cong``).
* ``display_name`` — operator-facing label including bilingual hint.
* ``sub_personas`` — list of Wave-5.3 persona slugs the actor wraps.
* ``owns_steps`` / ``contributes_steps`` / ``forbidden_steps``.
* ``escalates_to`` / ``delegates_to`` — graph edges in the Triangle.
* ``forbidden_tools`` — CLI commands the actor MUST NOT run.
* ``allowed_tools`` — CLI commands the actor MAY run (informational; not
  enforced at runtime, but the kit's docs cross-reference this list).

The expected actors / sub-persona mapping is locked here so the layered
governance (Wave 6.1) cannot drift silently from the Wave-5.3 persona
schema.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTOR_DIR = REPO_ROOT / "docs" / "agent-prompts" / "actors"
PERSONA_DIR = REPO_ROOT / "docs" / "agent-prompts"

EXPECTED_ACTORS = {"chu-nha", "chu-thau", "tho-thi-cong"}

# Locked sub-persona membership. Adding a new Wave-5.3 persona MUST be
# paired with an update here AND in test_agent_prompts_schema's
# EXPECTED_SUPER_ACTOR mapping.
EXPECTED_SUB_PERSONAS = {
    "chu-nha": {"trader"},
    "chu-thau": {"strategy-architect", "risk-auditor"},
    "tho-thi-cong": {"broker-engineer", "devops", "perf-analyst"},
}

REQUIRED_FIELDS = {
    "actor",
    "display_name",
    "sub_personas",
    "owns_steps",
    "contributes_steps",
    "forbidden_steps",
    "escalates_to",
    "delegates_to",
    "allowed_tools",
    "forbidden_tools",
    "inputs",
    "outputs",
}

ALLOWED_STEPS = {
    "scan", "rri", "vision", "blueprint", "tip", "build", "verify", "refine",
    # Wave 6.1 extra "synthetic" steps the Contractor owns between
    # blueprint and tip.
    "contract", "task-graph",
}

FRONTMATTER_RE = re.compile(
    r"\A---\n(?P<body>.*?)\n---\n",
    re.DOTALL,
)

# Triangle of Power escalation / delegation graph.
EXPECTED_GRAPH_EDGES = {
    "chu-nha": {"escalates_to": None, "delegates_to": "chu-thau"},
    "chu-thau": {"escalates_to": "chu-nha", "delegates_to": "tho-thi-cong"},
    "tho-thi-cong": {"escalates_to": "chu-thau", "delegates_to": None},
}


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match is not None, f"{path.name}: missing YAML frontmatter"
    return yaml.safe_load(match.group("body"))


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_prompt_exists(slug: str) -> None:
    prompt = ACTOR_DIR / f"{slug}.md"
    assert prompt.is_file(), f"docs/agent-prompts/actors/{slug}.md missing"


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_prompt_has_required_fields(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    missing = REQUIRED_FIELDS - set(fm.keys())
    assert not missing, (
        f"actors/{slug}.md missing frontmatter fields: {sorted(missing)}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_field_matches_filename(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    assert fm["actor"] == slug, (
        f"actors/{slug}.md: frontmatter actor={fm['actor']!r} "
        f"but filename says {slug!r}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_sub_personas_match_locked_set(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    declared = set(fm["sub_personas"])
    assert declared == EXPECTED_SUB_PERSONAS[slug], (
        f"actors/{slug}.md sub_personas={sorted(declared)} but "
        f"expected {sorted(EXPECTED_SUB_PERSONAS[slug])}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_sub_personas_have_matching_persona_files(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    for persona in fm["sub_personas"]:
        path = PERSONA_DIR / f"{persona}.md"
        assert path.is_file(), (
            f"actors/{slug}.md lists sub_persona {persona!r} "
            f"but {path.relative_to(REPO_ROOT)} is missing"
        )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_steps_are_known(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    for field in ("owns_steps", "contributes_steps", "forbidden_steps"):
        steps = set(fm[field])
        unknown = steps - ALLOWED_STEPS
        assert not unknown, (
            f"actors/{slug}.md.{field} has unknown step(s): {unknown}"
        )
    owns = set(fm["owns_steps"])
    contributes = set(fm["contributes_steps"])
    forbidden = set(fm["forbidden_steps"])
    assert not (owns & forbidden), (
        f"actors/{slug}.md cannot both own AND forbid a step: "
        f"{owns & forbidden}"
    )
    assert not (contributes & forbidden), (
        f"actors/{slug}.md cannot both contribute-to AND forbid a step: "
        f"{contributes & forbidden}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_graph_edges(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    expected = EXPECTED_GRAPH_EDGES[slug]
    assert fm["escalates_to"] == expected["escalates_to"], (
        f"actors/{slug}.md escalates_to={fm['escalates_to']!r} but "
        f"expected {expected['escalates_to']!r}"
    )
    assert fm["delegates_to"] == expected["delegates_to"], (
        f"actors/{slug}.md delegates_to={fm['delegates_to']!r} but "
        f"expected {expected['delegates_to']!r}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_ACTORS))
def test_actor_forbidden_tools_form_string_list(slug: str) -> None:
    fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
    tools = fm["forbidden_tools"]
    assert isinstance(tools, list), (
        f"actors/{slug}.md forbidden_tools is not a list"
    )
    for tool in tools:
        assert isinstance(tool, str), (
            f"actors/{slug}.md forbidden_tools contains non-string: {tool!r}"
        )
        assert tool.startswith("mql5-"), (
            f"actors/{slug}.md forbidden_tools entry {tool!r} should be "
            "an mql5-* CLI command"
        )


def test_actor_forbidden_tools_partition_is_consistent() -> None:
    """An mql5-* command cannot be forbidden for BOTH chu-thau AND tho-thi-cong.

    Wave 6.1 design: every kit CLI belongs to exactly one of (Contractor
    only, Builder only, both). Forbidding the same tool for both
    Contractor and Builder would leave no actor able to run it — that is
    only legitimate for tools that solely belong to chu-nha (currently
    none in the kit; mql5-init is shared with the Builder).
    """

    forbidden_by_actor: dict[str, set[str]] = {}
    for slug in EXPECTED_ACTORS:
        fm = _load_frontmatter(ACTOR_DIR / f"{slug}.md")
        forbidden_by_actor[slug] = set(fm["forbidden_tools"])
    overlap = (
        forbidden_by_actor["chu-thau"]
        & forbidden_by_actor["tho-thi-cong"]
    )
    assert not overlap, (
        f"chu-thau AND tho-thi-cong both forbid the same tool(s): "
        f"{sorted(overlap)}"
    )


def test_actors_directory_has_no_unexpected_files() -> None:
    if not ACTOR_DIR.is_dir():
        pytest.fail(f"{ACTOR_DIR} does not exist")
    actual = {p.stem for p in ACTOR_DIR.glob("*.md")}
    assert actual == EXPECTED_ACTORS, (
        f"actors/ directory: expected {sorted(EXPECTED_ACTORS)}, "
        f"got {sorted(actual)}"
    )
