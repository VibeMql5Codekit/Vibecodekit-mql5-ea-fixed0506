"""Wave-3 W3.A — CLI consolidation pins.

Verifies that the Wave-3 umbrella entry-points (``mql5-review --lens X``
and ``mql5-rri <kind>``) produce **byte-identical** output to the
legacy specialised CLIs they replaced. The legacy console scripts
(``mql5-eng-review``, ``mql5-ceo-review``, ``mql5-cso``,
``mql5-investigate``, ``mql5-rri-bt``, ``mql5-rri-rr``,
``mql5-rri-chart``) are now 1-line aliases that forward to the
umbrellas, so:

  * Anyone with existing scripts targeting the legacy names sees no
    change.
  * The umbrella's ``--help`` is the single source of truth for the
    consolidated surface.

Each test exercises BOTH paths and diffs the resulting artefact.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def _run(argv: list[str], cwd: Path) -> tuple[str, int]:
    """Run ``python -m <argv>`` from ``cwd`` and return (stdout, returncode)."""

    proc = subprocess.run(
        [sys.executable, "-m", *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout, proc.returncode


# ---------------------------------------------------------------------------
# Review consolidation (4 lenses)
# ---------------------------------------------------------------------------

LENSES = [
    ("eng", "vibecodekit_mql5.review.eng_review", "eng-review.md"),
    ("ceo", "vibecodekit_mql5.review.ceo_review", "ceo-review.md"),
    ("cso", "vibecodekit_mql5.review.cso", "cso-review.md"),
    ("investigate", "vibecodekit_mql5.review.investigate", "investigate.md"),
]


def test_review_lens_alias_outputs_match_umbrella(tmp_path):
    """For each of the 4 lenses, the markdown body emitted by the
    legacy alias CLI is byte-identical to the body emitted by the new
    umbrella ``mql5-review --lens X``."""

    for lens_id, legacy_module, _default_name in LENSES:
        u_dir = tmp_path / f"{lens_id}-umbrella"
        a_dir = tmp_path / f"{lens_id}-alias"
        u_dir.mkdir()
        a_dir.mkdir()
        umbrella_out = u_dir / "out.md"
        alias_out = a_dir / "out.md"

        u_stdout, u_rc = _run(
            ["vibecodekit_mql5.review.review",
             "--lens", lens_id, "--mode", "team",
             "--output", str(umbrella_out)],
            cwd=u_dir,
        )
        a_stdout, a_rc = _run(
            [legacy_module, "--mode", "team", "--output", str(alias_out)],
            cwd=a_dir,
        )
        assert u_rc == 0, f"umbrella --lens {lens_id} failed: {u_stdout!r}"
        assert a_rc == 0, f"alias {legacy_module} failed: {a_stdout!r}"

        # Markdown bodies must be byte-identical.
        assert umbrella_out.read_text(encoding="utf-8") == \
               alias_out.read_text(encoding="utf-8"), \
               f"output diverged for lens {lens_id!r}"

        # Both must emit a valid JSON envelope describing the lens.
        u_payload = json.loads(u_stdout)
        a_payload = json.loads(a_stdout)
        # Umbrella includes ``lens`` key; alias preserves legacy shape.
        assert u_payload["lens"] == lens_id
        assert u_payload["personas"] == a_payload["personas"]
        assert u_payload["mode"] == a_payload["mode"] == "team"


def test_review_legacy_single_persona_still_works(tmp_path):
    """The pre-Wave-3 ``mql5-review --persona X --step Y`` path must
    still work — Wave-3 only adds ``--lens``, it doesn't remove the
    single-persona dispatch path."""

    out = tmp_path / "single.md"
    stdout, rc = _run(
        ["vibecodekit_mql5.review.review",
         "--persona", "trader", "--step", "verify",
         "--mode", "personal", "--output", str(out)],
        cwd=tmp_path,
    )
    assert rc == 0
    payload = json.loads(stdout)
    # No ``lens`` key when running in single-persona mode.
    assert "lens" not in payload
    assert payload["persona"] == "trader"
    assert payload["step"] == "verify"
    body = out.read_text(encoding="utf-8")
    assert "persona: trader" in body
    assert "step: verify" in body


# ---------------------------------------------------------------------------
# RRI consolidation (3 matrix kinds + template default)
# ---------------------------------------------------------------------------

def test_rri_template_default_when_no_subcommand(tmp_path):
    """``mql5-rri`` with no args MUST keep emitting the Step-2 template
    on stdout — that's the contract documented in pre-Wave-3 CLI."""

    stdout, rc = _run(["vibecodekit_mql5.rri"], cwd=tmp_path)
    assert rc == 0
    # The template file ships with the repo; first heading is stable.
    assert "Step 2" in stdout and "RRI" in stdout


def test_rri_template_explicit_subcommand_matches_default(tmp_path):
    """``mql5-rri template`` (explicit) is byte-equal to the default."""

    default_out, default_rc = _run(["vibecodekit_mql5.rri"], cwd=tmp_path)
    explicit_out, explicit_rc = _run(
        ["vibecodekit_mql5.rri", "template"], cwd=tmp_path,
    )
    assert default_rc == 0 and explicit_rc == 0
    assert default_out == explicit_out


def _backtest_metrics_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "bt.json"
    p.write_text(json.dumps({
        "profit_factor": 1.5,
        "sharpe": 0.8,
        "max_dd_pct": 20,
        "total_trades": 100,
        "journal_lines": 50,
        "pip_norm_log": True,
    }), encoding="utf-8")
    return p


def _chart_metrics_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "chart.json"
    p.write_text(json.dumps({
        "compile_errors": 0,
        "journal_lines": 32,
        "ontick_latency_us": 250,
    }), encoding="utf-8")
    return p


def _rr_inputs_fixture(tmp_path: Path) -> dict[str, Path]:
    tc = tmp_path / "tc.json"
    wf = tmp_path / "wf.json"
    mc = tmp_path / "mc.json"
    of = tmp_path / "of.json"
    tc.write_text(json.dumps({"pass_count": 17}), encoding="utf-8")
    wf.write_text(json.dumps({"oos_is_correlation": 0.55}), encoding="utf-8")
    mc.write_text(json.dumps({"dd_p95_over_reported": 1.2}), encoding="utf-8")
    of.write_text(json.dumps({"oos_is_sharpe_ratio": 0.8}), encoding="utf-8")
    return {"tc": tc, "wf": wf, "mc": mc, "of": of}


def test_rri_bt_umbrella_matches_legacy_alias(tmp_path):
    """``mql5-rri bt`` produces the same HTML + JSON payload as the
    legacy ``mql5-rri-bt`` alias."""

    bt_json = _backtest_metrics_fixture(tmp_path)
    u_out = tmp_path / "u.html"
    a_out = tmp_path / "a.html"

    u_stdout, u_rc = _run(
        ["vibecodekit_mql5.rri", "bt",
         "--metrics", str(bt_json), "--output", str(u_out)],
        cwd=tmp_path,
    )
    a_stdout, a_rc = _run(
        ["vibecodekit_mql5.rri.rri_bt",
         "--metrics", str(bt_json), "--output", str(a_out)],
        cwd=tmp_path,
    )
    assert u_rc == 0 and a_rc == 0
    assert u_out.read_text(encoding="utf-8") == a_out.read_text(encoding="utf-8")

    u_payload = json.loads(u_stdout)
    a_payload = json.loads(a_stdout)
    assert u_payload["kind"] == "bt"
    assert u_payload["personas"] == a_payload["personas"]
    assert u_payload["matrix_counts"] == a_payload["matrix_counts"]


def test_rri_chart_umbrella_matches_legacy_alias(tmp_path):
    chart_json = _chart_metrics_fixture(tmp_path)
    u_out = tmp_path / "u.html"
    a_out = tmp_path / "a.html"
    u_stdout, u_rc = _run(
        ["vibecodekit_mql5.rri", "chart",
         "--metrics", str(chart_json), "--output", str(u_out)],
        cwd=tmp_path,
    )
    a_stdout, a_rc = _run(
        ["vibecodekit_mql5.rri.rri_chart",
         "--metrics", str(chart_json), "--output", str(a_out)],
        cwd=tmp_path,
    )
    assert u_rc == 0 and a_rc == 0
    assert u_out.read_text(encoding="utf-8") == a_out.read_text(encoding="utf-8")
    u_payload = json.loads(u_stdout)
    assert u_payload["kind"] == "chart"
    assert u_payload["personas"] == json.loads(a_stdout)["personas"]


def test_rri_rr_umbrella_matches_legacy_alias(tmp_path):
    inputs = _rr_inputs_fixture(tmp_path)
    u_out = tmp_path / "u.html"
    a_out = tmp_path / "a.html"

    u_stdout, u_rc = _run(
        ["vibecodekit_mql5.rri", "rr",
         "--trader-check", str(inputs["tc"]),
         "--walkforward", str(inputs["wf"]),
         "--monte-carlo", str(inputs["mc"]),
         "--overfit", str(inputs["of"]),
         "--output", str(u_out)],
        cwd=tmp_path,
    )
    a_stdout, a_rc = _run(
        ["vibecodekit_mql5.rri.rri_rr",
         "--trader-check", str(inputs["tc"]),
         "--walkforward", str(inputs["wf"]),
         "--monte-carlo", str(inputs["mc"]),
         "--overfit", str(inputs["of"]),
         "--output", str(a_out)],
        cwd=tmp_path,
    )
    assert u_rc == 0 and a_rc == 0
    assert u_out.read_text(encoding="utf-8") == a_out.read_text(encoding="utf-8")
    u_payload = json.loads(u_stdout)
    assert u_payload["kind"] == "rr"


def test_rri_unknown_subcommand_errors(tmp_path):
    """argparse should reject unknown subcommands cleanly (non-zero exit)."""

    _stdout, rc = _run(["vibecodekit_mql5.rri", "nope"], cwd=tmp_path)
    assert rc != 0


def test_review_unknown_lens_errors(tmp_path):
    """``mql5-review --lens bogus`` rejected by argparse choices=."""

    _stdout, rc = _run(
        ["vibecodekit_mql5.review.review", "--lens", "bogus"],
        cwd=tmp_path,
    )
    assert rc != 0


# ---------------------------------------------------------------------------
# Lens metadata pin — guards against accidental persona/step drift.
# ---------------------------------------------------------------------------

def test_lens_metadata_pinned():
    """The four lens definitions are exposed through the public
    :data:`vibecodekit_mql5.review.review.LENSES` table. Their personas
    and step bundles are the contract every external doc relies on and
    must not silently drift."""

    from vibecodekit_mql5.review.review import LENSES

    assert LENSES["eng"].personas == ("broker-engineer", "devops")
    assert LENSES["eng"].steps == ("build", "verify")

    assert LENSES["ceo"].personas == ("trader", "strategy-architect")
    assert LENSES["ceo"].steps == ("vision", "refine")

    assert LENSES["cso"].personas == ("risk-auditor",)
    assert LENSES["cso"].steps == ("rri", "verify")

    assert LENSES["investigate"].personas == (
        "perf-analyst", "strategy-architect",
    )
    assert LENSES["investigate"].steps == ("scan", "rri")
    # Investigate lens uniquely appends a Hypotheses worksheet.
    assert "Hypotheses" in LENSES["investigate"].extra_section
