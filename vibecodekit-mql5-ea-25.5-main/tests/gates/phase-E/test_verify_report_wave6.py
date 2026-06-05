"""Wave 6.1 — regression tests for ``mql5-verify-report``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit_mql5.step_gen import verify_report


def _write_envelope(
    path: Path,
    *,
    tool: str,
    ok: bool = True,
    summary: str = "",
    matrix_status: str | None = None,
    draft: bool = False,
) -> None:
    payload: dict = {
        "schema_version": "1",
        "tool": tool,
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "summary": summary,
        "data": {"draft": draft} if draft else {},
        "evidence": [],
    }
    if matrix_status is not None:
        payload["matrix"] = {"status": matrix_status}
    path.write_text(json.dumps(payload), encoding="utf-8")


BLUEPRINT_BODY = """\
# Step 4 / 8 — BLUEPRINT

## Invariants
- Risk per trade stays below 0.5% of equity
- News blackout window covers high-impact events
- Daily loss cap below 5% pauses the EA

## Notes
Some prose without invariants.
"""


@pytest.fixture
def gate_dir(tmp_path: Path) -> Path:
    d = tmp_path / "gates"
    d.mkdir()
    return d


@pytest.fixture
def tip_dir(tmp_path: Path) -> Path:
    d = tmp_path / "tasks"
    d.mkdir()
    return d


@pytest.fixture
def completion_dir(tmp_path: Path) -> Path:
    d = tmp_path / "completions"
    d.mkdir()
    return d


@pytest.fixture
def blueprint_file(tmp_path: Path) -> Path:
    p = tmp_path / "step-4-blueprint.md"
    p.write_text(BLUEPRINT_BODY, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_gate_reports
# ---------------------------------------------------------------------------


def test_load_gate_reports_skips_non_envelope_files(gate_dir: Path) -> None:
    (gate_dir / "not-a-report.json").write_text(
        json.dumps({"hello": "world"}), encoding="utf-8"
    )
    (gate_dir / "no-schema.json").write_text(
        json.dumps({"tool": "mql5-lint", "ok": True}), encoding="utf-8"
    )
    reports = verify_report.load_gate_reports(gate_dir)
    assert reports == []


def test_load_gate_reports_handles_invalid_json(gate_dir: Path) -> None:
    (gate_dir / "broken.json").write_text("not json", encoding="utf-8")
    reports = verify_report.load_gate_reports(gate_dir)
    assert reports == []


def test_load_gate_reports_returns_sorted(gate_dir: Path) -> None:
    _write_envelope(gate_dir / "gate-report-z.json", tool="mql5-lint")
    _write_envelope(gate_dir / "gate-report-a.json", tool="mql5-backtest")
    reports = verify_report.load_gate_reports(gate_dir)
    assert [r.path.name for r in reports] == ["gate-report-a.json", "gate-report-z.json"]


def test_derive_status_uses_matrix_status() -> None:
    payload = {"ok": True, "matrix": {"status": "FAIL"}}
    assert verify_report._derive_status(payload) == "FAIL"


def test_derive_status_uses_draft_flag() -> None:
    payload = {"ok": True, "data": {"draft": True}}
    assert verify_report._derive_status(payload) == "WARN"


def test_derive_status_falls_back_to_ok() -> None:
    assert verify_report._derive_status({"ok": True}) == "PASS"
    assert verify_report._derive_status({"ok": False}) == "FAIL"


# ---------------------------------------------------------------------------
# Invariant extraction + TIP mapping
# ---------------------------------------------------------------------------


def test_extract_invariants_from_blueprint(blueprint_file: Path) -> None:
    invariants = verify_report.extract_invariants(blueprint_file.read_text())
    assert invariants == [
        "Risk per trade stays below 0.5% of equity",
        "News blackout window covers high-impact events",
        "Daily loss cap below 5% pauses the EA",
    ]


def test_extract_invariants_empty_when_no_section(tmp_path: Path) -> None:
    p = tmp_path / "step-4-blueprint.md"
    p.write_text("# Blueprint\n\nNo invariants here.\n", encoding="utf-8")
    assert verify_report.extract_invariants(p.read_text()) == []


def test_map_invariants_to_tips_matches_keywords(
    blueprint_file: Path, tip_dir: Path
) -> None:
    # Carefully crafted bodies — only the salient keywords from each
    # invariant appear in exactly one TIP body, so coverage is unambiguous.
    (tip_dir / "TIP-001.md").write_text(
        "Implement equity-percentage risk guard.\n",
        encoding="utf-8",
    )
    (tip_dir / "TIP-002.md").write_text(
        "Implement blackout window using economic calendar API.\n",
        encoding="utf-8",
    )
    invariants = verify_report.extract_invariants(blueprint_file.read_text())
    coverage = verify_report.map_invariants_to_tips(invariants, tip_dir)
    assert "TIP-001.md" in coverage[invariants[0]]
    assert "TIP-002.md" in coverage[invariants[1]]
    # third invariant ("Daily loss cap below 5%") has no matching TIP
    assert coverage[invariants[2]] == []


# ---------------------------------------------------------------------------
# Completion report scraping
# ---------------------------------------------------------------------------


def test_scrape_completions_reads_status_and_suggestions(
    completion_dir: Path,
) -> None:
    (completion_dir / "completion-001.md").write_text(
        "# Completion 001\n"
        "**STATUS:** PASS\n\n"
        "## Suggestions\n"
        "- Tighten the spread guard at session open\n"
        "- Use larger lookback for the trend filter\n",
        encoding="utf-8",
    )
    (completion_dir / "completion-002.md").write_text(
        "# Completion 002\n"
        "**STATUS:** FAIL\n",
        encoding="utf-8",
    )
    facts = verify_report.scrape_completions(completion_dir)
    assert len(facts.files) == 2
    statuses = dict(facts.statuses)
    assert statuses["completion-001.md"] == "PASS"
    assert statuses["completion-002.md"] == "FAIL"
    assert facts.suggestion_count == 2


# ---------------------------------------------------------------------------
# build_facts + derive_overall_status
# ---------------------------------------------------------------------------


def test_overall_status_ready_when_no_failures_no_warnings() -> None:
    assert verify_report.derive_overall_status(0, 0, 0) == "READY"


def test_overall_status_needs_fixes_with_warnings() -> None:
    assert verify_report.derive_overall_status(0, 1, 0) == "NEEDS_FIXES"


def test_overall_status_needs_fixes_with_uncovered_invariants() -> None:
    assert verify_report.derive_overall_status(0, 0, 1) == "NEEDS_FIXES"


def test_overall_status_major_issues_on_failure() -> None:
    assert verify_report.derive_overall_status(1, 0, 0) == "MAJOR_ISSUES"
    assert verify_report.derive_overall_status(1, 5, 5) == "MAJOR_ISSUES"


def test_build_facts_buckets_reports_by_tool(gate_dir: Path) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint", ok=True)
    _write_envelope(gate_dir / "g2.json", tool="mql5-backtest", ok=True)
    _write_envelope(gate_dir / "g3.json", tool="mql5-unknown-tool", ok=True)
    reports = verify_report.load_gate_reports(gate_dir)
    facts = verify_report.build_facts(reports)
    assert any(r.tool == "mql5-lint" for r in facts.tech_health)
    assert any(r.tool == "mql5-backtest" for r in facts.scenarios)
    assert any(r.tool == "mql5-unknown-tool" for r in facts.other)


def test_render_report_includes_required_sections(gate_dir: Path) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint")
    reports = verify_report.load_gate_reports(gate_dir)
    facts = verify_report.build_facts(reports)
    out = verify_report.render_report(facts)
    for section in (
        "## OVERALL STATUS",
        "## REQ COVERAGE",
        "## SCENARIO RESULTS",
        "## TECH HEALTH",
        "## CRITICAL ISSUES",
        "## REFINE OPTIONS",
    ):
        assert section in out


def test_render_report_emits_major_issues_when_failure_present(
    gate_dir: Path,
) -> None:
    _write_envelope(
        gate_dir / "g1.json", tool="mql5-lint", ok=False, summary="2 errors"
    )
    reports = verify_report.load_gate_reports(gate_dir)
    facts = verify_report.build_facts(reports)
    assert facts.overall_status == "MAJOR_ISSUES"
    out = verify_report.render_report(facts)
    assert "MAJOR_ISSUES" in out
    assert "DO NOT SHIP" in out


def test_render_report_emits_ready_when_all_pass(gate_dir: Path) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint", ok=True)
    _write_envelope(gate_dir / "g2.json", tool="mql5-backtest", ok=True)
    reports = verify_report.load_gate_reports(gate_dir)
    facts = verify_report.build_facts(reports)
    assert facts.overall_status == "READY"
    out = verify_report.render_report(facts)
    assert "READY" in out
    assert "Ship as-is" in out


# ---------------------------------------------------------------------------
# CLI / Envelope
# ---------------------------------------------------------------------------


def test_cli_emits_report_to_file(tmp_path: Path, gate_dir: Path) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint")
    out = tmp_path / "verify-report.md"
    rc = verify_report.main(
        ["--gate-reports", str(gate_dir), "--out", str(out)]
    )
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "OVERALL STATUS" in body


def test_cli_rejects_missing_gate_dir(tmp_path: Path) -> None:
    rc = verify_report.main(["--gate-reports", str(tmp_path / "missing")])
    assert rc == 2


def test_cli_emits_json_envelope(
    tmp_path: Path,
    gate_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint", ok=False)
    rc = verify_report.main(
        [
            "--gate-reports",
            str(gate_dir),
            "--out",
            str(tmp_path / "verify-report.md"),
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "1"
    assert payload["tool"] == "mql5-verify-report"
    assert payload["ok"] is True
    assert payload["data"]["overall_status"] == "MAJOR_ISSUES"
    assert payload["data"]["failures"] == ["mql5-lint"]


def test_cli_with_blueprint_and_tip_dir_populates_coverage(
    tmp_path: Path,
    gate_dir: Path,
    blueprint_file: Path,
    tip_dir: Path,
) -> None:
    _write_envelope(gate_dir / "g1.json", tool="mql5-lint", ok=True)
    (tip_dir / "TIP-001.md").write_text("risk guard implementation", encoding="utf-8")
    out = tmp_path / "verify-report.md"
    rc = verify_report.main(
        [
            "--gate-reports",
            str(gate_dir),
            "--blueprint",
            str(blueprint_file),
            "--tip-dir",
            str(tip_dir),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "REQ COVERAGE" in body
    assert "Risk per trade" in body
