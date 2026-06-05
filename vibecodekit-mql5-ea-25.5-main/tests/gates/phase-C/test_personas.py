"""Tests for vibecodekit_mql5.rri.personas — 4 unit tests covering load,
mode filtering, schema, and total counts."""

from __future__ import annotations

import pytest

from vibecodekit_mql5.rri import personas


def test_load_all_6_personas():
    loaded = personas.load_all()
    assert tuple(loaded.keys()) == personas.PERSONA_IDS
    for pid, persona in loaded.items():
        assert persona.persona == pid
        assert len(persona.questions) == 25, f"{pid}: expected 25 Q, got {len(persona.questions)}"


@pytest.mark.parametrize("mode,expected_total", [
    ("personal", 30),     # 5 critical × 6 personas
    ("team", 72),         # 12 (critical+high) × 6
    ("enterprise", 150),  # 25 × 6
])
def test_total_for_mode(mode, expected_total):
    assert personas.total_for_mode(mode) == expected_total


def test_question_schema_validates_priority_and_modes():
    for pid in personas.PERSONA_IDS:
        persona = personas.load_persona(pid)
        for q in persona.questions:
            assert q.priority in {"critical", "high", "standard"}
            assert q.applicable_modes, f"{q.id}: no applicable_modes"
            assert all(m in personas.MODES for m in q.applicable_modes)
            assert q.id.startswith(pid.split("-")[0]) or "-" in q.id


def test_iter_questions_yields_persona_question_pairs_in_order():
    seen_personas = []
    count = 0
    for pid, q in personas.iter_questions("personal"):
        if pid not in seen_personas:
            seen_personas.append(pid)
        count += 1
        assert "personal" in q.applicable_modes
    assert seen_personas == list(personas.PERSONA_IDS)
    assert count == 30
