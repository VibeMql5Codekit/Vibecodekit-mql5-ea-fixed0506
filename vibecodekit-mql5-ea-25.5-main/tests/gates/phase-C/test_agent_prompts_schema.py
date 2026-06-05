"""Pin the Wave-5.3 ``docs/agent-prompts/*.md`` contract.

Each persona prompt MUST exist, MUST start with a YAML frontmatter
block (``---`` … ``---``), and MUST declare the fields the operator
relies on when picking and routing a prompt:

  - persona
  - role
  - review_lens
  - owns_steps
  - contributes_steps
  - peers
  - inputs
  - outputs
  - forbidden

The set of persona slugs is locked against
``docs/rri-personas/<slug>.yaml`` — adding a new prompt without a
matching RRI catalogue (or vice versa) breaks the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_DIR = REPO_ROOT / "docs" / "agent-prompts"
PERSONA_DIR = REPO_ROOT / "docs" / "rri-personas"

EXPECTED_PERSONAS = {
    "strategy-architect",
    "broker-engineer",
    "risk-auditor",
    "devops",
    "perf-analyst",
    "trader",
}

REQUIRED_FIELDS = {
    "persona",
    "role",
    "review_lens",
    "owns_steps",
    "contributes_steps",
    "peers",
    "inputs",
    "outputs",
    "forbidden",
    # Wave 6.1 — mandatory binding to the Triangle of Power
    "super_actor",
}

ALLOWED_SUPER_ACTORS = {"chu-nha", "chu-thau", "tho-thi-cong"}

# Wave 6.1 — expected super_actor mapping per persona. Pinned here so
# the contractor/builder/owner split cannot drift silently. Updates to
# this map must be paired with an `actors/<slug>.md` change and a docs
# refresh in docs/agent-prompts/README.md.
EXPECTED_SUPER_ACTOR = {
    "strategy-architect": "chu-thau",
    "risk-auditor": "chu-thau",
    "broker-engineer": "tho-thi-cong",
    "devops": "tho-thi-cong",
    "perf-analyst": "tho-thi-cong",
    "trader": "chu-nha",
}

ALLOWED_STEPS = {
    "scan", "rri", "vision", "blueprint", "tip", "build", "verify", "refine",
}

ALLOWED_LENSES = {"eng", "ceo", "cso", "investigate"}

FRONTMATTER_RE = re.compile(
    r"\A---\n(?P<body>.*?)\n---\n",
    re.DOTALL,
)


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match is not None, f"{path.name}: missing YAML frontmatter"
    return yaml.safe_load(match.group("body"))


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_exists(slug: str) -> None:
    prompt = PROMPT_DIR / f"{slug}.md"
    assert prompt.exists(), f"docs/agent-prompts/{slug}.md missing"


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_has_required_fields(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    missing = REQUIRED_FIELDS - set(fm.keys())
    assert not missing, f"{slug}.md missing frontmatter fields: {sorted(missing)}"


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_persona_field_matches_filename(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    assert fm["persona"] == slug, (
        f"{slug}.md: frontmatter persona={fm['persona']!r} but filename says {slug!r}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_persona_has_matching_rri_yaml(slug: str) -> None:
    rri = PERSONA_DIR / f"{slug}.yaml"
    assert rri.exists(), (
        f"docs/agent-prompts/{slug}.md exists but docs/rri-personas/{slug}.yaml does not"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_steps_are_known(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    owns = set(fm["owns_steps"])
    contributes = set(fm["contributes_steps"])
    unknown_owns = owns - ALLOWED_STEPS
    unknown_contributes = contributes - ALLOWED_STEPS
    assert not unknown_owns, f"{slug}.md owns unknown steps: {unknown_owns}"
    assert not unknown_contributes, (
        f"{slug}.md contributes to unknown steps: {unknown_contributes}"
    )
    assert not (owns & contributes), (
        f"{slug}.md: a step cannot be both owned and contributed-to: "
        f"{owns & contributes}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_review_lens_is_known(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    raw = fm["review_lens"]
    # Accept a single lens or a comma-separated string.
    lenses = {tok.strip() for tok in str(raw).split(",")}
    unknown = lenses - ALLOWED_LENSES
    assert not unknown, f"{slug}.md has unknown review_lens token(s): {unknown}"


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_super_actor_is_known(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    super_actor = fm["super_actor"]
    assert super_actor in ALLOWED_SUPER_ACTORS, (
        f"{slug}.md has unknown super_actor: {super_actor!r}"
    )
    assert super_actor == EXPECTED_SUPER_ACTOR[slug], (
        f"{slug}.md super_actor={super_actor!r} but expected "
        f"{EXPECTED_SUPER_ACTOR[slug]!r}"
    )


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_peers_are_other_known_personas(slug: str) -> None:
    fm = _load_frontmatter(PROMPT_DIR / f"{slug}.md")
    peers = set(fm["peers"])
    unknown = peers - EXPECTED_PERSONAS
    assert not unknown, f"{slug}.md lists unknown peers: {unknown}"
    assert slug not in peers, f"{slug}.md lists itself as a peer"


@pytest.mark.parametrize("slug", sorted(EXPECTED_PERSONAS))
def test_agent_prompt_has_canonical_section_headers(slug: str) -> None:
    text = (PROMPT_DIR / f"{slug}.md").read_text(encoding="utf-8")
    # Every prompt is paste-and-run; make sure the operator-facing
    # navigation headers are present so they land where expected.
    for heading in (
        "## Operating principles",
        "## Step-by-step responsibilities",
        "## Handoff contracts",
        "## What you must refuse to do",
        "## How to use this prompt",
    ):
        assert heading in text, f"{slug}.md missing section: {heading!r}"


def test_agent_prompts_directory_has_readme() -> None:
    readme = PROMPT_DIR / "README.md"
    assert readme.exists(), "docs/agent-prompts/README.md missing"
    text = readme.read_text(encoding="utf-8")
    # Every persona must be linked from the README's table.
    for slug in EXPECTED_PERSONAS:
        assert f"`{slug}.md`" in text or f"./{slug}.md" in text, (
            f"docs/agent-prompts/README.md does not reference {slug}.md"
        )


def test_agent_prompts_directory_has_exactly_expected_files() -> None:
    md_files = {p.stem for p in PROMPT_DIR.glob("*.md") if p.stem != "README"}
    assert md_files == EXPECTED_PERSONAS, (
        f"Unexpected agent prompts on disk: extra={md_files - EXPECTED_PERSONAS}, "
        f"missing={EXPECTED_PERSONAS - md_files}"
    )
