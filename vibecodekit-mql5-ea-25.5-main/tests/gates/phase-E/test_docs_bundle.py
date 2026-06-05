"""Phase-E gate: ``mql5-docs-bundle`` deterministic context+prompt emission.

The bundle command is the kit's hand-off to an external LLM agent for
the Pattern-A `.docx` ship pipeline. These tests pin the deterministic
shape of the JSON payload, confirm the LLM prompt carries the
non-negotiable instructions, and check that the scaffold flow narrative
and input-semantics library land in the payload when present.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from vibecodekit_mql5 import docs_bundle


REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD_SPEC_TEMPLATE = """\
name: BundleTestEA
preset: trend
stack: netting
symbol: EURUSD
timeframe: H1
"""


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    spec = tmp_path / "ea-spec.yaml"
    spec.write_text(SCAFFOLD_SPEC_TEMPLATE, encoding="utf-8")
    mq5_src = REPO_ROOT / "scaffolds" / "trend" / "netting" / "EAName.mq5"
    if not mq5_src.is_file():
        pytest.skip("trend/netting scaffold missing — kit not fully unpacked")
    mq5 = tmp_path / "BundleTestEA.mq5"
    mq5.write_text(mq5_src.read_text(encoding="utf-8"), encoding="utf-8")
    return spec, mq5


def test_bundle_emits_context_and_prompt(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"

    result = docs_bundle.write_bundle(spec, mq5, out)

    assert result.ok is True
    assert (out / "docs-context.json").is_file()
    assert (out / "docs-prompt.md").is_file()
    assert result.context_path.endswith("docs-context.json")
    assert result.prompt_path.endswith("docs-prompt.md")


def test_context_schema_complete(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"

    docs_bundle.write_bundle(spec, mq5, out)
    ctx = json.loads((out / "docs-context.json").read_text(encoding="utf-8"))

    required_top_keys = {
        "ea",
        "market",
        "account",
        "spec",
        "scaffold",
        "inputs",
        "flow_narrative",
        "lint_findings",
        "build_metrics",
        "reference_doc_structure",
    }
    assert required_top_keys.issubset(ctx.keys())
    assert ctx["ea"]["name"] == "BundleTestEA"
    assert ctx["market"]["symbol"] == "EURUSD"
    assert ctx["market"]["timeframe"] == "H1"
    assert ctx["scaffold"]["archetype_label"] == "trend/netting"
    assert "CPipNormalizer" in ctx["scaffold"]["includes_used"]


def test_prompt_contains_non_negotiable_instructions(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"
    docs_bundle.write_bundle(spec, mq5, out)
    prompt = (out / "docs-prompt.md").read_text(encoding="utf-8")

    assert "guide.md" in prompt
    assert "ADAPTIVE" in prompt
    # The kit is Vietnamese-first by project convention — pin that.
    assert "tiếng Việt" in prompt or "Tiếng Việt" in prompt
    assert "[[TOC]]" in prompt


def test_flow_narrative_populated_from_scaffold(tmp_path: Path) -> None:
    flow_path = REPO_ROOT / "scaffolds" / "trend" / "netting" / "FLOW-vi.md"
    if not flow_path.is_file():
        pytest.skip("trend/netting FLOW-vi.md missing")
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"

    result = docs_bundle.write_bundle(spec, mq5, out)
    ctx = json.loads((out / "docs-context.json").read_text(encoding="utf-8"))

    assert result.has_flow_narrative is True
    assert len(ctx["flow_narrative"]) > 100


def test_input_semantics_enrichment(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"

    result = docs_bundle.write_bundle(spec, mq5, out)
    ctx = json.loads((out / "docs-context.json").read_text(encoding="utf-8"))

    enriched = [inp for inp in ctx["inputs"] if inp.get("semantics")]
    assert len(enriched) >= 1, "at least one input should match docs/input-semantics.yaml"
    assert result.inputs_enriched == len(enriched)
    sem = enriched[0]["semantics"]
    assert "meaning_vi" in sem and sem["meaning_vi"]


def test_includes_used_detection(tmp_path: Path) -> None:
    spec = tmp_path / "ea-spec.yaml"
    spec.write_text(SCAFFOLD_SPEC_TEMPLATE, encoding="utf-8")
    mq5 = tmp_path / "EA.mq5"
    mq5.write_text(
        '#include "CPipNormalizer.mqh"\n'
        '#include "subdir/CRiskGuard.mqh"\n'
        "input double InpFoo = 1.0;\n",
        encoding="utf-8",
    )

    docs_bundle.write_bundle(spec, mq5, tmp_path / "build")
    ctx = json.loads((tmp_path / "build" / "docs-context.json").read_text(encoding="utf-8"))

    assert ctx["scaffold"]["includes_used"] == ["CPipNormalizer", "CRiskGuard"]


def test_build_report_metrics_pulled_when_present(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    report = {
        "stages": [
            {"name": "compile", "ok": True, "errors": [], "warnings": []},
            {
                "name": "lint",
                "ok": True,
                "findings": [
                    {"code": "AP-1", "ok": True},
                    {"code": "AP-2", "ok": False, "severity": "ERROR", "line": 12, "message": "boom"},
                ],
            },
        ],
    }
    report_path = tmp_path / "auto-build-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    docs_bundle.write_bundle(spec, mq5, tmp_path / "build", build_report_path=report_path)
    ctx = json.loads((tmp_path / "build" / "docs-context.json").read_text(encoding="utf-8"))

    assert ctx["build_metrics"]["compile_ok"] is True
    assert ctx["build_metrics"]["anti_patterns_passed"] == 1
    assert ctx["build_metrics"]["anti_patterns_failed"] == 1
    assert len(ctx["lint_findings"]) == 2
    assert ctx["lint_findings"][1]["code"] == "AP-2"


def test_main_cli_exits_zero_and_prints_result(tmp_path: Path, capsys) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    out = tmp_path / "build"
    rc = docs_bundle.main(
        [
            str(spec),
            str(mq5),
            "--out",
            str(out),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["context_path"].endswith("docs-context.json")


def test_main_cli_returns_error_for_missing_mq5(tmp_path: Path) -> None:
    spec = tmp_path / "ea-spec.yaml"
    spec.write_text(SCAFFOLD_SPEC_TEMPLATE, encoding="utf-8")
    rc = docs_bundle.main(
        [
            str(spec),
            str(tmp_path / "does-not-exist.mq5"),
            "--out",
            str(tmp_path / "build"),
        ]
    )
    assert rc == 2


def test_bundle_result_is_json_serialisable(tmp_path: Path) -> None:
    spec, mq5 = _write_inputs(tmp_path)
    result = docs_bundle.write_bundle(spec, mq5, tmp_path / "build")
    # The CLI dumps `asdict(result)` — exercise that path to keep the
    # dataclass and CLI in sync.
    payload = asdict(result)
    json.dumps(payload, ensure_ascii=False)
