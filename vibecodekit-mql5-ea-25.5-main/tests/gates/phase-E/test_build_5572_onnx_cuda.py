"""Phase E gate — ONNX CUDA execution-provider plumbing (build 5572).

W7.1 from the v1.0.1 audit: the kit must surface the build 5572
``OnnxSetExecutionProviders`` knob end-to-end — CLI flag on
``mql5-onnx-export``, JSON-report field for the downstream embed step,
and matching MQL5 wiring on ``COnnxLoader``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit_mql5 import onnx_export

REPO_ROOT = Path(__file__).resolve().parents[3]
LOADER_MQH = REPO_ROOT / "Include" / "COnnxLoader.mqh"
REF_71 = REPO_ROOT / "docs" / "references" / "71-onnx-mql5.md"


# ─── _parse_providers ───────────────────────────────────────────────────────

def test_default_providers_is_cpu_only() -> None:
    assert onnx_export.DEFAULT_PROVIDERS == ("cpu",)
    assert onnx_export._parse_providers("") == ["cpu"]


def test_parse_providers_accepts_cuda() -> None:
    assert onnx_export._parse_providers("cuda") == ["cuda"]


def test_parse_providers_preserves_order_and_dedups() -> None:
    assert onnx_export._parse_providers("cuda,cpu") == ["cuda", "cpu"]
    assert onnx_export._parse_providers("cuda,cuda,cpu") == ["cuda", "cpu"]
    assert onnx_export._parse_providers("CUDA, cpu") == ["cuda", "cpu"]


def test_parse_providers_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown ONNX execution provider"):
        onnx_export._parse_providers("tpu")
    with pytest.raises(ValueError):
        onnx_export._parse_providers("cuda,vulkan")


# ─── ExportReport payload ───────────────────────────────────────────────────

def test_export_report_carries_providers_in_json() -> None:
    """The downstream embed step needs the provider list in the JSON
    contract.  Regression: pre-build-5572 the field didn't exist and
    embed silently produced CPU-only Init calls."""
    rep = onnx_export.ExportReport(
        ok=True, onnx_path="/tmp/m.onnx", opset=14,
        providers=["cuda", "cpu"],
    )
    parsed = json.loads(rep.as_json())
    assert parsed["providers"] == ["cuda", "cpu"]


def test_export_report_default_providers_field() -> None:
    rep = onnx_export.ExportReport(ok=True, onnx_path="x.onnx", opset=14)
    assert rep.providers == ["cpu"]


# ─── CLI surface ────────────────────────────────────────────────────────────

def test_cli_rejects_unknown_provider(tmp_path: Path, capsys) -> None:
    fake = tmp_path / "missing.pt"
    fake.write_bytes(b"not-a-model")
    rc = onnx_export.main([str(fake), "--output", str(tmp_path / "o.onnx"),
                           "--providers", "tpu"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown ONNX execution provider" in err


# ─── MQL5 side (COnnxLoader.mqh) ────────────────────────────────────────────

def test_onnx_loader_has_provider_member_and_signature() -> None:
    """Build 5572 wiring on the MQL5 side: optional 2nd arg + Provider()
    accessor + ApplyProvider helper.  We assert text presence rather
    than compile because the worked-example compile gate is separate."""
    src = LOADER_MQH.read_text(encoding="utf-8")
    assert 'm_provider' in src,                        "missing m_provider field"
    assert 'ApplyProvider' in src,                     "missing ApplyProvider()"
    assert 'OnnxSetExecutionProviders' in src,         "missing build-5572 call"
    assert 'InitFromResource(const string resource_name' in src
    assert 'const string provider = ""' in src,       "signature lost default"
    assert 'Provider(void)' in src,                    "missing getter"


def test_onnx_loader_falls_back_to_cpu_on_older_builds() -> None:
    """The kit promises CUDA is best-effort; older builds must not
    break Init.  Guard symbol must be checked, not assumed present."""
    src = LOADER_MQH.read_text(encoding="utf-8")
    assert "#ifdef ONNX_HAS_SET_EXECUTION_PROVIDERS" in src
    assert "#else" in src
    # Fallback log must mention falling back to CPU.
    assert "cpu" in src.lower() and "fall" in src.lower()


# ─── Reference doc bump (71-onnx-mql5.md) ───────────────────────────────────

def test_ref_71_documents_build_5572_cuda() -> None:
    text = REF_71.read_text(encoding="utf-8")
    assert "5572" in text,                       "ref must mention build 5572"
    assert "OnnxSetExecutionProviders" in text,  "ref must name the new API"
    assert "--providers" in text,                "ref must mention CLI flag"
    assert "cuda" in text.lower(),               "ref must mention CUDA EP"
