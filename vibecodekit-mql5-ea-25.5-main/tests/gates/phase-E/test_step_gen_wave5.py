"""Wave 5.1 — regression tests for the step-output generators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vibecodekit_mql5.step_gen import blueprint_gen, tip_gen, vision_gen


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


RRI_BODY = """\
# Step 2 / 8 — RRI (Requirements Matrix)
- Audit mode: `team`

## Constraints
- Risk per trade must stay below 0.5%
- News blackout must cover NFP windows
- Daily loss cap < 5%

## Answers
- [x] strategy-architect::strat-01
- [x] strategy-architect::strat-02
- [x] risk-auditor::risk-01
- [x] trader::trade-01
- [ ] devops::ops-01
"""


SPEC_BODY: dict = {
    "name": "TrendUnit",
    "preset": "trend",
    "stack": "netting",
    "symbol": "EURUSD",
    "timeframe": "H1",
    "mode": "team",
    "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 5.0},
    "signals": [{"kind": "macd"}, {"kind": "ema_cross"}],
    "filters": [{"kind": "time_window"}],
}


@pytest.fixture
def rri_file(tmp_path: Path) -> Path:
    p = tmp_path / "step-2-rri.md"
    p.write_text(RRI_BODY, encoding="utf-8")
    return p


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "ea-spec.yaml"
    p.write_text(yaml.safe_dump(SPEC_BODY, sort_keys=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# vision_gen
# ---------------------------------------------------------------------------


def test_vision_gen_parses_constraints(rri_file: Path) -> None:
    parsed = vision_gen.parse_rri(rri_file.read_text())
    assert parsed.mode == "team"
    assert parsed.constraints == (
        "Risk per trade must stay below 0.5%",
        "News blackout must cover NFP windows",
        "Daily loss cap < 5%",
    )
    assert parsed.checked_questions == 4
    # devops::ops-01 is unchecked so should not appear
    assert "devops" not in parsed.active_personas


def test_vision_gen_active_personas_sorted(rri_file: Path) -> None:
    parsed = vision_gen.parse_rri(rri_file.read_text())
    assert parsed.active_personas == (
        "risk-auditor", "strategy-architect", "trader",
    )


def test_vision_gen_accepts_uppercase_checkbox(tmp_path: Path) -> None:
    """Markdown task-list syntax is case-insensitive; `- [X]` must work."""
    rri = tmp_path / "step-2-rri.md"
    rri.write_text(
        "# Step 2 / 8 — RRI\n\n"
        "## Constraints\n- C1\n\n"
        "## Questions\n"
        "- [X] strategy-architect::strat-01 — uppercase X\n"
        "- [x] risk-auditor::risk-01 — lowercase x\n"
        "- [ ] devops::dev-01 — unchecked\n",
        encoding="utf-8",
    )
    parsed = vision_gen.parse_rri(rri.read_text())
    assert parsed.active_personas == ("risk-auditor", "strategy-architect")
    assert parsed.checked_questions == 2


def test_vision_gen_render_contains_constraints_and_personas(rri_file: Path) -> None:
    parsed = vision_gen.parse_rri(rri_file.read_text())
    out = vision_gen.render_vision(parsed, source=rri_file)
    assert "# Step 3 / 8 — VISION" in out
    assert "## Scope" in out
    assert "Risk per trade must stay below 0.5%" in out
    assert "## Active personas" in out
    assert "- risk-auditor" in out
    assert "## Activities" in out
    # Activities skeleton stays untouched so the operator must re-tick
    assert "- [ ] Define the minimum viable change set" in out
    assert "## Timeline" in out
    assert "## Risk register" in out


def test_vision_gen_cli_writes_file(tmp_path: Path, rri_file: Path) -> None:
    out = tmp_path / "step-3-vision.md"
    rc = vision_gen.main([str(rri_file), "--out", str(out)])
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "# Step 3 / 8 — VISION" in body


def test_vision_gen_cli_missing_input(tmp_path: Path) -> None:
    rc = vision_gen.main([str(tmp_path / "missing.md")])
    assert rc == 2


def test_vision_gen_cli_refuses_overwrite(tmp_path: Path, rri_file: Path) -> None:
    out = tmp_path / "step-3-vision.md"
    out.write_text("existing", encoding="utf-8")
    rc = vision_gen.main([str(rri_file), "--out", str(out)])
    assert rc == 2
    assert out.read_text() == "existing"


def test_vision_gen_cli_force_overwrite(tmp_path: Path, rri_file: Path) -> None:
    out = tmp_path / "step-3-vision.md"
    out.write_text("existing", encoding="utf-8")
    rc = vision_gen.main([str(rri_file), "--out", str(out), "--force"])
    assert rc == 0
    assert "# Step 3 / 8 — VISION" in out.read_text()


def test_vision_gen_json_envelope(rri_file: Path, capsys) -> None:
    rc = vision_gen.main([str(rri_file), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["tool"] == "mql5-vision-gen"
    assert payload["ok"] is True
    assert payload["data"]["mode"] == "team"
    assert payload["data"]["checked_questions"] == 4
    # Generators are emitters, not gate-report tools — they intentionally do
    # NOT carry matrix coordinates (would otherwise pin a non-gate-auto cell).
    assert "matrix" not in payload


def test_vision_gen_gate_report(tmp_path: Path, rri_file: Path) -> None:
    gr = tmp_path / "gate-report-vision-gen.json"
    rc = vision_gen.main([str(rri_file), "--gate-report", str(gr)])
    assert rc == 0
    assert gr.exists()
    data = json.loads(gr.read_text())
    assert data["tool"] == "mql5-vision-gen"
    assert data["ok"] is True


# ---------------------------------------------------------------------------
# blueprint_gen
# ---------------------------------------------------------------------------


def test_blueprint_gen_loads_spec(spec_file: Path) -> None:
    spec = blueprint_gen.load_spec(spec_file)
    assert spec.name == "TrendUnit"
    assert spec.preset == "trend"


def test_blueprint_gen_picks_preset_invariants(spec_file: Path) -> None:
    spec = blueprint_gen.load_spec(spec_file)
    facts = blueprint_gen.build_facts(spec)
    assert facts.invariants == blueprint_gen.PRESET_INVARIANTS["trend"]
    # AP-1 SL must appear in every trading preset
    assert any("AP-1" in inv for inv in facts.invariants)


def test_blueprint_gen_modules_include_pip_and_magic(spec_file: Path) -> None:
    spec = blueprint_gen.load_spec(spec_file)
    facts = blueprint_gen.build_facts(spec)
    names = " ".join(facts.modules)
    assert "CPipNormalizer" in names
    assert "CMagicRegistry" in names
    assert "CRiskGuard" in names


def test_blueprint_gen_async_state_machine() -> None:
    from vibecodekit_mql5.spec_schema import EaSpec
    spec = EaSpec(
        name="HftUnit", preset="hft-async", stack="netting",
        symbol="EURUSD", timeframe="M1", mode="team",
    )
    facts = blueprint_gen.build_facts(spec)
    joined = "\n".join(facts.state_machine)
    assert "OrderSendAsync" in joined
    assert "OnTradeTransaction" in joined


def test_blueprint_gen_fuses_vision_scope(tmp_path: Path, spec_file: Path) -> None:
    vision = tmp_path / "step-3-vision.md"
    vision.write_text(
        "# Step 3\n## Scope\n- Vision item A\n- Vision item B\n## Timeline\n- TODO\n",
        encoding="utf-8",
    )
    out = tmp_path / "step-4-blueprint.md"
    rc = blueprint_gen.main([str(spec_file), "--vision", str(vision), "--out", str(out)])
    assert rc == 0
    body = out.read_text()
    assert "Vision item A" in body
    assert "Vision item B" in body


def test_blueprint_gen_renders_invariants_as_checkboxes(spec_file: Path) -> None:
    spec = blueprint_gen.load_spec(spec_file)
    facts = blueprint_gen.build_facts(spec)
    rendered = blueprint_gen.render_blueprint(facts, source=spec_file)
    for inv in facts.invariants:
        assert f"- [ ] {inv}" in rendered


def test_blueprint_gen_cli_writes_file(tmp_path: Path, spec_file: Path) -> None:
    out = tmp_path / "step-4-blueprint.md"
    rc = blueprint_gen.main([str(spec_file), "--out", str(out)])
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "# Step 4 / 8 — BLUEPRINT" in body
    assert "trend" in body


def test_blueprint_gen_cli_missing_spec(tmp_path: Path) -> None:
    rc = blueprint_gen.main([str(tmp_path / "missing.yaml")])
    assert rc == 2


def test_blueprint_gen_cli_invalid_spec(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: only-name-no-other-fields\n", encoding="utf-8")
    rc = blueprint_gen.main([str(bad)])
    assert rc == 2


def test_blueprint_gen_json_envelope(spec_file: Path, capsys) -> None:
    rc = blueprint_gen.main([str(spec_file), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "mql5-blueprint-gen"
    assert payload["ok"] is True
    assert payload["data"]["preset"] == "trend"
    assert len(payload["data"]["invariants"]) >= 3


def test_blueprint_gen_covers_every_preset() -> None:
    from vibecodekit_mql5 import build as build_mod
    # Every preset registered in build.PRESETS must have invariants
    # so render_blueprint never silently falls back to stdlib.
    missing = [
        p for p in build_mod.PRESETS
        if p not in blueprint_gen.PRESET_INVARIANTS
    ]
    assert missing == [], f"presets missing invariants: {missing}"


# ---------------------------------------------------------------------------
# tip_gen
# ---------------------------------------------------------------------------


BLUEPRINT_SAMPLE = """\
# Step 4 / 8 — BLUEPRINT

## Module diagram
```
  TrendUnit.mq5 — entry-point (OnInit/OnTick/OnDeinit)
  Include/CPipNormalizer.mqh — broker pip math
  Include/CMagicRegistry.mqh — magic number issuance
  Include/CRiskGuard.mqh — equity + daily-loss enforcement
```

## Invariants
- [ ] Stop-loss set on every OrderSend (AP-1)
- [ ] Pip math via CPipNormalizer for JPY/XAU symmetry
- [ ] Magic number reserved via CMagicRegistry (70000-79999)

## Activities
- [ ] List each module to add / modify; assign owner
"""


def test_tip_gen_extracts_invariants() -> None:
    facts = tip_gen.build_facts(BLUEPRINT_SAMPLE)
    assert facts.invariants == (
        "Stop-loss set on every OrderSend (AP-1)",
        "Pip math via CPipNormalizer for JPY/XAU symmetry",
        "Magic number reserved via CMagicRegistry (70000-79999)",
    )
    assert len(facts.modules) == 4


def test_tip_gen_module_assignment_uses_keywords() -> None:
    facts = tip_gen.build_facts(BLUEPRINT_SAMPLE)
    cov = facts.coverage
    # AP-1 stop-loss → CRiskGuard
    sl_inv = "Stop-loss set on every OrderSend (AP-1)"
    assert any("CRiskGuard" in m for m in cov[sl_inv])
    # Pip math → CPipNormalizer
    pip_inv = "Pip math via CPipNormalizer for JPY/XAU symmetry"
    assert any("CPipNormalizer" in m for m in cov[pip_inv])
    # Magic → CMagicRegistry
    magic_inv = "Magic number reserved via CMagicRegistry (70000-79999)"
    assert any("CMagicRegistry" in m for m in cov[magic_inv])


def test_tip_gen_renders_table(tmp_path: Path) -> None:
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_SAMPLE, encoding="utf-8")
    out = tmp_path / "step-5-tip.md"
    rc = tip_gen.main([str(bp), "--out", str(out)])
    assert rc == 0
    body = out.read_text()
    assert "# Step 5 / 8 — TIP" in body
    assert "| Module |" in body
    assert "| `Include/CPipNormalizer.mqh` |" in body
    assert "`test_stop_loss_set_on_every_ordersend_ap_1`" in body


def test_tip_gen_test_names_are_pytest_compatible() -> None:
    facts = tip_gen.build_facts(BLUEPRINT_SAMPLE)
    body = tip_gen.render_tip(facts)
    # Test names must be snake_case identifiers (no spaces, no punctuation)
    import re
    matches = re.findall(r"`(test_[a-z0-9_]+)`", body)
    assert matches
    for name in matches:
        assert name.isidentifier(), f"non-identifier test name: {name}"


def test_tip_gen_empty_blueprint(tmp_path: Path) -> None:
    bp = tmp_path / "empty.md"
    bp.write_text("# Step 4\n\nNo content\n", encoding="utf-8")
    rc = tip_gen.main([str(bp)])
    assert rc == 0


def test_tip_gen_cli_missing_input(tmp_path: Path) -> None:
    rc = tip_gen.main([str(tmp_path / "missing.md")])
    assert rc == 2


def test_tip_gen_json_envelope(tmp_path: Path, capsys) -> None:
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_SAMPLE, encoding="utf-8")
    rc = tip_gen.main([str(bp), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "mql5-tip-gen"
    assert payload["ok"] is True
    assert len(payload["data"]["invariants"]) == 3
    assert len(payload["data"]["modules"]) == 4


# ---------------------------------------------------------------------------
# End-to-end chain
# ---------------------------------------------------------------------------


def test_chain_vision_to_blueprint_to_tip(tmp_path: Path, rri_file: Path, spec_file: Path) -> None:
    vision_out = tmp_path / "step-3-vision.md"
    blueprint_out = tmp_path / "step-4-blueprint.md"
    tip_out = tmp_path / "step-5-tip.md"

    assert vision_gen.main([str(rri_file), "--out", str(vision_out)]) == 0
    assert blueprint_gen.main([
        str(spec_file),
        "--vision", str(vision_out),
        "--out", str(blueprint_out),
    ]) == 0
    assert tip_gen.main([str(blueprint_out), "--out", str(tip_out)]) == 0

    tip_body = tip_out.read_text()
    assert "AP-1" in tip_body
    assert "CPipNormalizer" in tip_body
    assert "CMagicRegistry" in tip_body
