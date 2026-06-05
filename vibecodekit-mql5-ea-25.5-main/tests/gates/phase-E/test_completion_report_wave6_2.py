"""Wave 6.2 — schema + behaviour tests for ``mql5-completion-report``."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibecodekit_mql5.step_gen import completion_report as cr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_TIP_BODY = """\
---
tip_id: TIP-003
title: implement signal block on `EURUSD` / `H1`
status: PENDING
actor: tho-thi-cong
depends_on: [TIP-001, TIP-002]
invariant_refs:
  - 'Per-trade risk stays <= 0.5% of equity.'
  - 'The filter chain blackout-window blocks signals after 20:00.'
contract_sha256_prefix: 39811aafeac1
---

# TIP-003 — implement signal block

## Goal

implement signal block.
"""


@pytest.fixture()
def tip_file(tmp_path: Path) -> Path:
    p = tmp_path / "TIP-003.md"
    p.write_text(_TIP_BODY, encoding="utf-8")
    return p


def _envelope(
    path: Path,
    tool: str,
    *,
    ok: bool = True,
    matrix_status: str | None = None,
    summary: str = "",
    draft: bool = False,
) -> None:
    payload: dict = {
        "schema_version": "1",
        "tool": tool,
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "summary": summary or f"{tool} smoke",
        "data": {"draft": True} if draft else {},
        "evidence": [],
    }
    if matrix_status is not None:
        payload["matrix"] = {"status": matrix_status}
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def passing_gates(tmp_path: Path) -> Path:
    d = tmp_path / "gates-pass"
    d.mkdir()
    _envelope(d / "gate-report-lint.json", "mql5-lint")
    _envelope(d / "gate-report-trader.json", "mql5-trader-check")
    return d


@pytest.fixture()
def failing_gates(tmp_path: Path) -> Path:
    d = tmp_path / "gates-fail"
    d.mkdir()
    _envelope(d / "gate-report-lint.json", "mql5-lint")
    _envelope(
        d / "gate-report-mh.json",
        "mql5-method-hiding-check",
        ok=False,
        summary="1 hiding error in Include/Risk.mqh:42",
    )
    return d


@pytest.fixture()
def warn_gates(tmp_path: Path) -> Path:
    d = tmp_path / "gates-warn"
    d.mkdir()
    _envelope(d / "gate-report-lint.json", "mql5-lint", draft=True)
    return d


# ---------------------------------------------------------------------------
# parse_tip
# ---------------------------------------------------------------------------


def test_parse_tip_extracts_metadata(tip_file: Path) -> None:
    tip = cr.parse_tip(tip_file)
    assert tip.tip_id == "TIP-003"
    assert tip.title.startswith("implement signal")
    assert tip.depends_on == ("TIP-001", "TIP-002")
    assert len(tip.invariant_refs) == 2
    assert "Per-trade" in tip.invariant_refs[0]


def test_parse_tip_no_dependencies(tmp_path: Path) -> None:
    body = _TIP_BODY.replace(
        "depends_on: [TIP-001, TIP-002]", "depends_on: []"
    )
    p = tmp_path / "x.md"
    p.write_text(body, encoding="utf-8")
    assert cr.parse_tip(p).depends_on == ()


def test_parse_tip_missing_tip_id_raises(tmp_path: Path) -> None:
    p = tmp_path / "broken.md"
    p.write_text("---\ntitle: x\n---\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tip_id"):
        cr.parse_tip(p)


def test_parse_tip_empty_invariant_refs(tmp_path: Path) -> None:
    body = (
        "---\n"
        "tip_id: TIP-001\n"
        "title: scaffold\n"
        "depends_on: []\n"
        "invariant_refs:\n"
        "  []\n"
        "---\n"
    )
    p = tmp_path / "x.md"
    p.write_text(body, encoding="utf-8")
    tip = cr.parse_tip(p)
    assert tip.invariant_refs == ()


# ---------------------------------------------------------------------------
# load_evidence
# ---------------------------------------------------------------------------


def test_load_evidence_filters_non_envelopes(tmp_path: Path) -> None:
    d = tmp_path / "g"
    d.mkdir()
    _envelope(d / "ok.json", "mql5-lint")
    (d / "junk.json").write_text("not json")
    (d / "no-tool.json").write_text(json.dumps({"schema_version": "1"}))
    (d / "no-schema.json").write_text(json.dumps({"tool": "x"}))
    evidence = cr.load_evidence(d)
    assert len(evidence) == 1
    assert evidence[0].tool == "mql5-lint"


def test_load_evidence_status_passthrough(tmp_path: Path) -> None:
    d = tmp_path / "g"
    d.mkdir()
    _envelope(d / "a.json", "mql5-lint")
    _envelope(d / "b.json", "mql5-bt-sim", ok=False)
    _envelope(d / "c.json", "mql5-trader-check", draft=True)
    statuses = {e.tool: e.status for e in cr.load_evidence(d)}
    assert statuses["mql5-lint"] == "PASS"
    assert statuses["mql5-bt-sim"] == "FAIL"
    assert statuses["mql5-trader-check"] == "WARN"


def test_load_evidence_matrix_override(tmp_path: Path) -> None:
    d = tmp_path / "g"
    d.mkdir()
    _envelope(d / "x.json", "mql5-lint", ok=False, matrix_status="PASS")
    e = cr.load_evidence(d)
    assert e[0].status == "PASS"


def test_load_evidence_empty_dir(tmp_path: Path) -> None:
    assert cr.load_evidence(tmp_path / "missing") == []


# ---------------------------------------------------------------------------
# derive_status
# ---------------------------------------------------------------------------


def test_status_ready_when_all_pass(passing_gates: Path) -> None:
    evidence = tuple(cr.load_evidence(passing_gates))
    assert cr.derive_status(evidence, ()) == "READY"


def test_status_blocked_when_any_fail(failing_gates: Path) -> None:
    evidence = tuple(cr.load_evidence(failing_gates))
    assert cr.derive_status(evidence, ()) == "BLOCKED"


def test_status_blocked_when_issue_supplied(passing_gates: Path) -> None:
    evidence = tuple(cr.load_evidence(passing_gates))
    assert cr.derive_status(evidence, ("blocker note",)) == "BLOCKED"


def test_status_in_progress_when_warn(warn_gates: Path) -> None:
    evidence = tuple(cr.load_evidence(warn_gates))
    assert cr.derive_status(evidence, ()) == "IN_PROGRESS"


def test_status_in_progress_when_no_evidence() -> None:
    assert cr.derive_status((), ()) == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# build_facts + render_completion
# ---------------------------------------------------------------------------


def test_build_facts_populates_evidence(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file,
        passing_gates,
        files=("Include/x.mqh",),
        tests=("tests/test_x.py",),
        issues=(),
    )
    assert facts.status == "READY"
    assert len(facts.evidence) == 2
    assert facts.tip.tip_id == "TIP-003"


def test_render_includes_status_and_title(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file, passing_gates, files=(), tests=(), issues=()
    )
    body = cr.render_completion(facts, tip_path=tip_file)
    assert body.startswith("# Completion Report — TIP-003")
    assert "**STATUS:** READY" in body
    assert "implement signal" in body


def test_render_lists_files_and_tests(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file,
        passing_gates,
        files=("Include/Risk.mqh", "EA.mq5"),
        tests=("tests/test_risk.py",),
        issues=(),
    )
    body = cr.render_completion(facts, tip_path=tip_file)
    assert "- `Include/Risk.mqh`" in body
    assert "- `EA.mq5`" in body
    assert "- `tests/test_risk.py`" in body


def test_render_lists_issues_when_blocked(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file,
        passing_gates,
        files=(),
        tests=(),
        issues=("MetaEditor build mismatch", "broker rejects netting"),
    )
    body = cr.render_completion(facts, tip_path=tip_file)
    assert "**STATUS:** BLOCKED" in body
    assert "- MetaEditor build mismatch" in body
    assert "- broker rejects netting" in body


def test_render_gate_table_columns(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file, passing_gates, files=(), tests=(), issues=()
    )
    body = cr.render_completion(facts, tip_path=tip_file)
    assert "| Tool | Status | Summary | Path |" in body
    assert "`mql5-lint`" in body
    assert "`PASS`" in body


def test_render_invariants_section_present(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file, passing_gates, files=(), tests=(), issues=()
    )
    body = cr.render_completion(facts, tip_path=tip_file)
    assert "## Invariants Referenced" in body
    assert "Per-trade risk" in body


def test_render_is_deterministic(
    tip_file: Path, passing_gates: Path
) -> None:
    facts = cr.build_facts(
        tip_file, passing_gates, files=("a",), tests=("b",), issues=()
    )
    a = cr.render_completion(facts, tip_path=tip_file)
    b = cr.render_completion(facts, tip_path=tip_file)
    assert a == b


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "vibecodekit_mql5.step_gen.completion_report",
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_writes_completion_md(
    tip_file: Path, passing_gates: Path, tmp_path: Path
) -> None:
    out = tmp_path / "completion-003.md"
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--out",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    assert "**STATUS:** READY" in out.read_text(encoding="utf-8")


def test_cli_blocked_returns_exit_1(
    tip_file: Path, failing_gates: Path
) -> None:
    proc = _run_cli(
        ["--tip", str(tip_file), "--gate-reports", str(failing_gates)]
    )
    assert proc.returncode == 1
    assert "**STATUS:** BLOCKED" in proc.stdout


def test_cli_json_envelope(
    tip_file: Path, passing_gates: Path
) -> None:
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--json",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "1"
    assert payload["tool"] == "mql5-completion-report"
    assert payload["data"]["tip_id"] == "TIP-003"
    assert payload["data"]["status"] == "READY"
    assert len(payload["data"]["evidence"]) == 2


def test_cli_gate_report_writes_envelope(
    tip_file: Path, passing_gates: Path, tmp_path: Path
) -> None:
    gate = tmp_path / "gate.json"
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--gate-report",
            str(gate),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(gate.read_text(encoding="utf-8"))
    assert payload["tool"] == "mql5-completion-report"


def test_cli_refuses_overwrite(
    tip_file: Path, passing_gates: Path, tmp_path: Path
) -> None:
    out = tmp_path / "completion.md"
    out.write_text("existing", encoding="utf-8")
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--out",
            str(out),
        ]
    )
    assert proc.returncode == 2
    assert "use --force" in proc.stderr


def test_cli_force_overwrite(
    tip_file: Path, passing_gates: Path, tmp_path: Path
) -> None:
    out = tmp_path / "completion.md"
    out.write_text("existing", encoding="utf-8")
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--out",
            str(out),
            "--force",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert "STATUS:** READY" in out.read_text(encoding="utf-8")


def test_cli_missing_tip(tmp_path: Path) -> None:
    proc = _run_cli(["--tip", str(tmp_path / "nope.md")])
    assert proc.returncode == 2
    assert "not found" in proc.stderr


def test_cli_missing_gate_dir(tip_file: Path, tmp_path: Path) -> None:
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(tmp_path / "missing"),
        ]
    )
    assert proc.returncode == 2
    assert "directory not found" in proc.stderr


def test_cli_repeatable_flags(
    tip_file: Path, passing_gates: Path
) -> None:
    proc = _run_cli(
        [
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--file",
            "a.mqh",
            "--file",
            "b.mqh",
            "--test",
            "test_a.py",
            "--issue",
            "minor warning",
            "--json",
        ]
    )
    assert proc.returncode == 1  # issue triggers BLOCKED
    payload = json.loads(proc.stdout)
    assert payload["data"]["files"] == ["a.mqh", "b.mqh"]
    assert payload["data"]["tests"] == ["test_a.py"]
    assert payload["data"]["issues"] == ["minor warning"]
    assert payload["data"]["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# Console script entry
# ---------------------------------------------------------------------------


def test_console_script_registered(
    tip_file: Path, passing_gates: Path
) -> None:
    proc = subprocess.run(
        [
            "mql5-completion-report",
            "--tip",
            str(tip_file),
            "--gate-reports",
            str(passing_gates),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["tool"] == "mql5-completion-report"
