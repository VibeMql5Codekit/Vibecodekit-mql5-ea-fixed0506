"""Phase D ONNX unit tests — 5 cases.

Covers:
1. opset enforcement (>=14)
2. validate() reports missing-file error gracefully
3. export_torch() returns informative error when PyTorch missing
4. embed_onnx() injects #resource + #include in idempotent fashion
5. embed_onnx() guards against missing .mq5 source
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from vibecodekit_mql5 import onnx_embed, onnx_export

HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_opset_below_minimum_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        onnx_export._check_opset(13)


def test_validate_missing_file(tmp_path: Path) -> None:
    rep = onnx_export.validate(tmp_path / "nope.onnx")
    assert not rep.ok
    # validate() may bail out at the onnx-import stage on machines without
    # ONNX installed; either path is a real failure, just confirm we got
    # a non-empty error explaining it.
    assert rep.error


def test_export_torch_no_torch_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate torch missing even if installed.
    monkeypatch.setitem(sys.modules, "torch", None)
    rep = onnx_export.export_torch(tmp_path / "x.pt", tmp_path / "x.onnx", opset=14)
    assert not rep.ok
    assert "PyTorch missing" in rep.error or "missing" in rep.error.lower()


def test_embed_onnx_idempotent(tmp_path: Path) -> None:
    mq5 = tmp_path / "EA.mq5"
    mq5.write_text(
        '#property strict\n\nint OnInit() { return INIT_SUCCEEDED; }\n',
        encoding="utf-8",
    )
    onnx = tmp_path / "model.onnx"
    onnx.write_bytes(b"\x00")
    r1 = onnx_embed.embed_onnx(mq5, onnx)
    r2 = onnx_embed.embed_onnx(mq5, onnx)  # second pass must be a no-op
    body = mq5.read_text()
    assert body.count('#resource "model.onnx"') == 1
    assert body.count('#include "COnnxLoader.mqh"') == 1
    assert r1.added_resource and not r2.added_resource


def test_embed_onnx_missing_source(tmp_path: Path) -> None:
    rep = onnx_embed.embed_onnx(tmp_path / "missing.mq5", tmp_path / "m.onnx")
    assert not rep.ok
    assert any("missing" in note for note in rep.notes)
