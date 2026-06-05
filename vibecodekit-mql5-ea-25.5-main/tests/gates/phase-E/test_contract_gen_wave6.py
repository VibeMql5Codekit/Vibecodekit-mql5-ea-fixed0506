"""Wave 6.1 — regression tests for ``mql5-contract-gen``."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from vibecodekit_mql5.step_gen import contract_gen


BLUEPRINT_BODY = """\
# Step 4 / 8 — BLUEPRINT (Architecture Skeleton)
- Name: `TrendUnit`
- Preset: `trend`
- Stack: `netting`

## Invariants
- [ ] Risk per trade stays at or below 0.5% of equity
- [ ] News blackout window covers high-impact events
- [ ] Daily loss cap below 5% pauses the EA for the day
- [ ] Magic numbers reserved through `CMagicRegistry`

## Module diagram
```
Include/CPipNormalizer.mqh
Include/CMagicRegistry.mqh
Include/Strategies/Trend.mqh
```

## State machine
```
OnInit → Subscribe → OnTick (sync) → OnDeinit
```

## Notes
Some prose the contract should not parse.
"""


APPROVED_BLUEPRINT = BLUEPRINT_BODY + "\nAPPROVED by Alice at 2026-05-25\n"


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
def blueprint_file(tmp_path: Path) -> Path:
    p = tmp_path / "step-4-blueprint.md"
    p.write_text(BLUEPRINT_BODY, encoding="utf-8")
    return p


@pytest.fixture
def approved_blueprint_file(tmp_path: Path) -> Path:
    p = tmp_path / "step-4-blueprint.md"
    p.write_text(APPROVED_BLUEPRINT, encoding="utf-8")
    return p


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "ea-spec.yaml"
    p.write_text(yaml.safe_dump(SPEC_BODY, sort_keys=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parse_blueprint
# ---------------------------------------------------------------------------


def test_parse_blueprint_extracts_invariants(blueprint_file: Path) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    assert bp.invariants == (
        "Risk per trade stays at or below 0.5% of equity",
        "News blackout window covers high-impact events",
        "Daily loss cap below 5% pauses the EA for the day",
        "Magic numbers reserved through `CMagicRegistry`",
    )


def test_parse_blueprint_extracts_modules_and_state_machine(blueprint_file: Path) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    assert any("CPipNormalizer.mqh" in mod for mod in bp.modules)
    assert any("CMagicRegistry.mqh" in mod for mod in bp.modules)
    # State machine block parses too.
    assert any("OnInit" in line for line in bp.state_machine)


def test_parse_blueprint_detects_approved(approved_blueprint_file: Path) -> None:
    bp = contract_gen.parse_blueprint(approved_blueprint_file.read_text())
    assert bp.has_approved is True


def test_parse_blueprint_detects_missing_approved(blueprint_file: Path) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    assert bp.has_approved is False


def test_parse_blueprint_hash_strips_approved_line() -> None:
    bp_a = contract_gen.parse_blueprint(BLUEPRINT_BODY)
    bp_b = contract_gen.parse_blueprint(APPROVED_BLUEPRINT)
    # Hash must be identical because the canonical body strips the
    # APPROVED line.
    assert bp_a.blueprint_sha256 == bp_b.blueprint_sha256


def test_parse_blueprint_hash_changes_when_body_changes() -> None:
    body_a = BLUEPRINT_BODY
    body_b = BLUEPRINT_BODY.replace("Risk per trade", "Risk per trades")
    bp_a = contract_gen.parse_blueprint(body_a)
    bp_b = contract_gen.parse_blueprint(body_b)
    assert bp_a.blueprint_sha256 != bp_b.blueprint_sha256


# ---------------------------------------------------------------------------
# build_facts / render_contract
# ---------------------------------------------------------------------------


def test_build_facts_uses_preset_deliverables(blueprint_file: Path, spec_file: Path) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    assert facts.deliverables == contract_gen.PRESET_DELIVERABLES["trend"]
    assert facts.exclusions == contract_gen.PRESET_EXCLUSIONS["trend"]


def test_render_contract_includes_required_sections(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    out = contract_gen.render_contract(
        facts, blueprint_path=blueprint_file, spec_path=spec_file
    )
    for section in (
        "## Inputs",
        "## EA identity",
        "## DELIVERABLES",
        "## EXCLUSIONS",
        "## TECH STACK",
        "## INVARIANTS",
        "## TASK GRAPH SUMMARY",
        "## ACCEPTANCE OVERVIEW",
        "## CONFIRM",
    ):
        assert section in out, f"missing section: {section!r}"


def test_render_contract_includes_blueprint_invariants_verbatim(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    out = contract_gen.render_contract(facts)
    for inv in bp.invariants:
        assert inv in out


def test_render_contract_warns_when_blueprint_not_approved(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    out = contract_gen.render_contract(facts, blueprint_path=blueprint_file)
    assert "WARNING" in out
    assert "APPROVED" in out


def test_render_contract_no_warning_when_blueprint_approved(
    approved_blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(approved_blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    out = contract_gen.render_contract(
        facts, blueprint_path=approved_blueprint_file
    )
    assert "WARNING" not in out


def test_render_contract_includes_confirm_block(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    out = contract_gen.render_contract(facts)
    assert "CONFIRM by <your name> at <YYYY-MM-DD>" in out


def test_render_contract_is_deterministic(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    a = contract_gen.render_contract(
        facts, blueprint_path=blueprint_file, spec_path=spec_file
    )
    b = contract_gen.render_contract(
        facts, blueprint_path=blueprint_file, spec_path=spec_file
    )
    assert a == b


def test_render_contract_emits_task_summary_lines(
    blueprint_file: Path, spec_file: Path
) -> None:
    bp = contract_gen.parse_blueprint(blueprint_file.read_text())
    spec = contract_gen.load_spec(spec_file)
    facts = contract_gen.build_facts(spec, bp)
    # 3 base tasks + 2 signals + 1 filter + 1 backtest + 1 permission = 8 lines
    assert len(facts.task_summary) == 8
    out = contract_gen.render_contract(facts)
    # Every task entry references a TIP id and the EA name.
    for entry in facts.task_summary:
        assert re.search(r"TIP-\d{3}", entry)
    assert "TrendUnit" in out


# ---------------------------------------------------------------------------
# CLI / Envelope
# ---------------------------------------------------------------------------


def test_cli_emits_contract_to_file(
    tmp_path: Path, blueprint_file: Path, spec_file: Path
) -> None:
    out = tmp_path / "contract.md"
    rc = contract_gen.main(
        [
            str(blueprint_file),
            "--ea-spec",
            str(spec_file),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "## DELIVERABLES" in body
    assert "## CONFIRM" in body


def test_cli_rejects_missing_blueprint(tmp_path: Path, spec_file: Path) -> None:
    rc = contract_gen.main(
        [
            str(tmp_path / "missing.md"),
            "--ea-spec",
            str(spec_file),
        ]
    )
    assert rc == 2


def test_cli_requires_ea_spec(blueprint_file: Path, tmp_path: Path) -> None:
    rc = contract_gen.main([str(blueprint_file)])
    assert rc == 2


def test_cli_refuses_to_overwrite(
    tmp_path: Path, blueprint_file: Path, spec_file: Path
) -> None:
    out = tmp_path / "contract.md"
    out.write_text("existing", encoding="utf-8")
    rc = contract_gen.main(
        [
            str(blueprint_file),
            "--ea-spec",
            str(spec_file),
            "--out",
            str(out),
        ]
    )
    assert rc == 2
    # --force overrides
    rc = contract_gen.main(
        [
            str(blueprint_file),
            "--ea-spec",
            str(spec_file),
            "--out",
            str(out),
            "--force",
        ]
    )
    assert rc == 0
    assert out.read_text(encoding="utf-8") != "existing"


def test_cli_emits_json_envelope(
    tmp_path: Path, blueprint_file: Path, spec_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = contract_gen.main(
        [
            str(blueprint_file),
            "--ea-spec",
            str(spec_file),
            "--out",
            str(tmp_path / "contract.md"),
            "--json",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["schema_version"] == "1"
    assert payload["tool"] == "mql5-contract-gen"
    assert payload["ok"] is True
    assert payload["data"]["preset"] == "trend"
    assert payload["data"]["stack"] == "netting"
    assert payload["data"]["blueprint_approved"] is False
    assert len(payload["data"]["deliverables"]) > 0
    assert len(payload["data"]["task_summary"]) > 0


def test_cli_writes_gate_report(
    tmp_path: Path, blueprint_file: Path, spec_file: Path
) -> None:
    gate = tmp_path / "gate-report-contract.json"
    rc = contract_gen.main(
        [
            str(blueprint_file),
            "--ea-spec",
            str(spec_file),
            "--out",
            str(tmp_path / "contract.md"),
            "--gate-report",
            str(gate),
        ]
    )
    assert rc == 0
    payload = json.loads(gate.read_text(encoding="utf-8"))
    assert payload["tool"] == "mql5-contract-gen"
    assert payload["data"]["preset"] == "trend"
