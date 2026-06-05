"""Phase-E gate: auto-build pipeline emits docs_bundle + docs_assemble.

The ``ship-docx`` PR wired :mod:`docs_bundle` + :mod:`docs_assemble`
into ``mql5-auto-build``'s ``_finalize`` step. These tests pin the
informational nature of those stages — they must populate the report
without ever flipping the pipeline verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit_mql5 import auto_build, auto_build_docs_ship_stage
from vibecodekit_mql5 import compile as compile_mod


MINIMAL_SPEC = {
    "name": "DocsBundleEA",
    "preset": "trend",
    "stack": "netting",
    "symbol": "EURUSD",
    "timeframe": "H1",
    "mode": "personal",
}


def _patch_compile_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_compile(_path, **_kwargs):
        return compile_mod.CompileResult(
            success=True,
            errors=[],
            warnings=[],
            ex5_path=str(_path.with_suffix(".ex5")),
        )

    monkeypatch.setattr(compile_mod, "compile_mq5", _fake_compile)


def test_pipeline_emits_docs_bundle_artefacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_compile_success(monkeypatch)
    out_dir = tmp_path / "build"

    report = auto_build.run_pipeline(
        dict(MINIMAL_SPEC),
        out_dir,
        skip_compile=False,
        skip_gate=True,
        skip_dashboard=True,
        skip_docs=False,
        ea_spec=auto_build.validate_spec(MINIMAL_SPEC),
    )

    bundle = report.docs_bundle or {}
    assert bundle.get("ok") is True, bundle
    assert (out_dir / "docs-context.json").is_file()
    assert (out_dir / "docs-prompt.md").is_file()


def test_pipeline_skips_assemble_when_guide_md_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Assemble stage records a structured skip when the LLM step hasn't run.

    The kit-light pattern hands the actual LLM authoring step off to the
    operator's agent. Until ``guide.md`` materialises in the build dir,
    the assemble stage should report a soft skip with a hint — never
    fail the pipeline.
    """
    _patch_compile_success(monkeypatch)
    out_dir = tmp_path / "build"

    report = auto_build.run_pipeline(
        dict(MINIMAL_SPEC),
        out_dir,
        skip_compile=False,
        skip_gate=True,
        skip_dashboard=True,
        skip_docs=False,
        ea_spec=auto_build.validate_spec(MINIMAL_SPEC),
    )

    assemble = report.docs_assemble or {}
    assert assemble.get("skipped") is True
    assert "guide.md" in (assemble.get("reason") or "")
    # Pipeline still reports green — assemble is informational.
    assert report.ok is True


def test_assemble_helper_renders_existing_guide(tmp_path: Path) -> None:
    """The ``_maybe_assemble_docs`` helper turns a guide.md into a .docx.

    The full pipeline rebuilds the project dir on ``force=True`` and
    wipes any pre-existing ``guide.md``, so we exercise the assemble
    helper directly with a guide already on disk — that's the path the
    standalone ``mql5-docs-assemble`` CLI walks too.
    """
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    (out_dir / "guide.md").write_text(
        "# DocsBundleEA v1.0.0 — Hướng dẫn sử dụng\n\n"
        "[[TOC]]\n\n"
        "# Chương 1 — Tổng quan\nEA trend EURUSD H1.\n\n"
        "# Chương 2 — Tham số\nInpRiskMoney mặc định 100 USD.\n\n"
        "# Chương 3 — Cài đặt\n1. Drag EA vào chart\n2. Bật AutoTrading\n\n"
        "# Chương 4 — Backtest\nPeriod H1, Symbol EURUSD.\n\n"
        "# Chương 5 — Risk\nDrawdown tối đa: 10%.\n",
        encoding="utf-8",
    )
    report = auto_build.PipelineReport(spec=dict(MINIMAL_SPEC), out_dir=str(out_dir))
    auto_build_docs_ship_stage.attach_docs_assemble(
        report, out_dir, ea_name="DocsBundleEA", skip=False
    )

    assemble = report.docs_assemble or {}
    assert assemble.get("ok") is True, assemble
    assert (out_dir / "DocsBundleEA.docs.docx").is_file()
    assert assemble["chapters"] == 5


def test_pipeline_skips_bundle_on_no_docs_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_compile_success(monkeypatch)
    out_dir = tmp_path / "build"

    report = auto_build.run_pipeline(
        dict(MINIMAL_SPEC),
        out_dir,
        skip_compile=False,
        skip_gate=True,
        skip_dashboard=True,
        skip_docs=True,
        ea_spec=auto_build.validate_spec(MINIMAL_SPEC),
    )

    assert (report.docs_bundle or {}).get("skipped") is True
    assert (report.docs_assemble or {}).get("skipped") is True
    assert not (out_dir / "docs-context.json").exists()


def test_pipeline_report_serialises_with_new_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_compile_success(monkeypatch)
    out_dir = tmp_path / "build"

    report = auto_build.run_pipeline(
        dict(MINIMAL_SPEC),
        out_dir,
        skip_compile=False,
        skip_gate=True,
        skip_dashboard=True,
        skip_docs=False,
        ea_spec=auto_build.validate_spec(MINIMAL_SPEC),
    )
    payload = json.loads(json.dumps(report.to_dict()))

    assert "docs_bundle" in payload
    assert "docs_assemble" in payload
    # The on-disk auto-build-report.json must reflect the same shape so
    # downstream consumers (LLM agents that re-load the report later)
    # can rely on the new fields being present.
    on_disk = json.loads((out_dir / "auto-build-report.json").read_text(encoding="utf-8"))
    assert "docs_bundle" in on_disk
    assert "docs_assemble" in on_disk


def test_package_classifies_new_docs_artifacts(tmp_path: Path) -> None:
    """The ship.zip groups must place LLM artefacts in `repro`."""
    from vibecodekit_mql5 import package as package_mod

    out = tmp_path / "EA"
    out.mkdir()
    (out / "docs-context.json").write_text("{}", encoding="utf-8")
    (out / "docs-prompt.md").write_text("prompt", encoding="utf-8")
    (out / "guide.md").write_text("# T", encoding="utf-8")
    (out / "EA.docs.docx").write_bytes(b"PK\x03\x04")

    artifacts = package_mod.collect_artifacts(out)
    by_path = {a.path: a for a in artifacts}

    assert by_path["docs-context.json"].group == "repro"
    assert by_path["docs-context.json"].kind == "docs-context"
    assert by_path["docs-prompt.md"].group == "repro"
    assert by_path["docs-prompt.md"].kind == "docs-prompt"
    assert by_path["guide.md"].group == "repro"
    assert by_path["guide.md"].kind == "docs-guide-md"
    # The Word deliverable stays in `review` via the existing
    # ``.docs.`` rule — pin that path too so this PR can't silently
    # demote the primary user-facing artifact.
    assert by_path["EA.docs.docx"].group == "review"
