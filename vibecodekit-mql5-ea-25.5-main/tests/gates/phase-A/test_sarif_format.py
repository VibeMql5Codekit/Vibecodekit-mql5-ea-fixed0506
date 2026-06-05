"""tests/gates/phase-A/test_sarif_format.py — SARIF 2.1.0 output validation.

`mql5-lint --format sarif` and `mql5-method-hiding-check --format sarif`
emit SARIF 2.1.0 log documents so the kit plugs into Cursor / VS Code /
GitHub code-scanning without per-tool adapters.

These tests pin the structural shape (schema version, run.tool.driver.rules,
result location coordinates). We don't run a full SARIF validator here —
that would require an external dependency — but we do check that every
required field per OASIS SARIF 2.1.0 §3 is present and well-typed.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _parse(buf: io.StringIO) -> dict:
    return json.loads(buf.getvalue())


def _assert_sarif_skeleton(sarif: dict) -> None:
    assert sarif.get("version") == "2.1.0", sarif
    assert "$schema" in sarif, sarif
    runs = sarif.get("runs")
    assert isinstance(runs, list) and len(runs) == 1, sarif
    run = runs[0]
    tool = run.get("tool")
    assert isinstance(tool, dict), run
    driver = tool.get("driver")
    assert isinstance(driver, dict), tool
    assert isinstance(driver.get("name"), str), driver
    assert isinstance(driver.get("rules"), list), driver
    for rule in driver["rules"]:
        assert isinstance(rule.get("id"), str), rule
        assert isinstance(rule.get("shortDescription"), dict), rule
        assert isinstance(rule.get("defaultConfiguration"), dict), rule
        assert rule["defaultConfiguration"]["level"] in {"error", "warning",
                                                          "note", "none"}, rule
    assert isinstance(run.get("results"), list), run


def test_lint_sarif_skeleton():
    from vibecodekit_mql5 import lint as lint_cli

    sample = REPO_ROOT / "scaffolds" / "grid" / "hedging" / "EAName.mq5"
    buf = io.StringIO()
    with redirect_stdout(buf):
        lint_cli.main([str(sample), "--format", "sarif"])
    sarif = _parse(buf)
    _assert_sarif_skeleton(sarif)
    rule_ids = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
    # The 8 critical AP rules MUST be advertised even when not triggered.
    assert "no-sl" in rule_ids
    assert "lot-hardcoded" in rule_ids
    assert "hardcoded-pip" in rule_ids


def test_lint_sarif_finding_locations_have_line_column(tmp_path: Path):
    """SARIF results.locations[].physicalLocation MUST carry line+column."""

    from vibecodekit_mql5 import lint as lint_cli

    # Craft a tiny .mq5 that intentionally trips AP-1 + AP-3.
    bad = tmp_path / "bad.mq5"
    bad.write_text(
        "#property version \"1.0\"\n"
        "double lot = 0.01;\n"  # AP-3
        "CTrade trade;\n"
        "void OnTick() {\n"
        "    trade.Buy(lot, _Symbol);\n"  # AP-1
        "}\n"
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        lint_cli.main([str(bad), "--format", "sarif"])
    sarif = _parse(buf)
    _assert_sarif_skeleton(sarif)
    results = sarif["runs"][0]["results"]
    assert results, "expected at least one finding"
    for r in results:
        loc = r["locations"][0]["physicalLocation"]
        assert "artifactLocation" in loc
        region = loc["region"]
        assert isinstance(region["startLine"], int) and region["startLine"] >= 1
        assert isinstance(region["startColumn"], int) and region["startColumn"] >= 1


def test_method_hiding_sarif_skeleton(tmp_path: Path):
    from vibecodekit_mql5 import method_hiding_check

    # Synthesise a tiny .mq5 with two classes, derived hides base method.
    mq5 = tmp_path / "hiding.mq5"
    mq5.write_text(
        "class Base {\n"
        "  public:\n"
        "    void Action() {}\n"
        "};\n"
        "class Derived : public Base {\n"
        "  public:\n"
        "    void Action() {}\n"
        "};\n"
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        method_hiding_check.main([str(mq5), "--format", "sarif"])
    sarif = _parse(buf)
    _assert_sarif_skeleton(sarif)
    rule_ids = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
    assert "mql5-method-hiding" in rule_ids
