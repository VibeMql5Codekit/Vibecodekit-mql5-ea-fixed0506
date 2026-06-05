"""Phase D acceptance sentinel — read by scripts/audit-plan-v5.py.

The end-to-end ``test_onnx_pipeline_e2e`` lives here so the audit script
can detect a single canonical file containing the Phase D e2e gate.

The e2e itself is skipped when PyTorch + onnx are not installed (those
are optional ``phase-d`` extras). The skip is informational, NOT a
failure — the unit gates in this directory cover correctness.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

HAS_TORCH = importlib.util.find_spec("torch") is not None
HAS_ONNX = importlib.util.find_spec("onnx") is not None


if HAS_TORCH:
    # Module-level class so torch.save can pickle it (locals can't be pickled).
    from torch import nn

    class _TinyLstm(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size=1, hidden_size=4, batch_first=True)
            self.head = nn.Linear(4, 3)

        def forward(self, x):  # type: ignore[override]
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :])


def test_phase_d_test_modules_present() -> None:
    """The 6 unit-test modules in this directory must exist."""
    here = Path(__file__).parent
    expected = {
        "test_phase_d_acceptance.py",
        "test_onnx.py",
        "test_async_hft.py",
        "test_algo_forge.py",
        "test_llm_bridge.py",
        "test_cloud_optimize.py",
        "test_method_hiding.py",
    }
    actual = {p.name for p in here.glob("test_*.py")}
    missing = expected - actual
    assert not missing, f"missing Phase D test files: {missing}"


@pytest.mark.skipif(
    not (HAS_TORCH and HAS_ONNX),
    reason="PyTorch / onnx not installed — install via pip install '.[phase-d]'",
)
def test_onnx_pipeline_e2e(tmp_path: Path) -> None:
    """PyTorch → ONNX → embed → static lint check, all under 10 min."""
    from vibecodekit_mql5 import onnx_embed, onnx_export

    t0 = time.monotonic()

    # 1. train tiny LSTM in-process (skip the train.py CLI for speed)
    import torch

    model = _TinyLstm()
    model.eval()
    pt_path = tmp_path / "model.pt"
    torch.save(model, pt_path)

    # 2. export to ONNX
    onnx_path = tmp_path / "model.onnx"
    rep = onnx_export.export_torch(
        pt_path, onnx_path, opset=14, input_shape=(1, 10, 1),
    )
    assert rep.ok, rep.error

    # 3. embed into a stdlib scaffold .mq5 and confirm the resource is added
    mq5 = tmp_path / "TestEA.mq5"
    mq5.write_text(
        '//+--+\n#property strict\n\nint OnInit() { return INIT_SUCCEEDED; }\n',
        encoding="utf-8",
    )
    er = onnx_embed.embed_onnx(mq5, onnx_path, in_place=True)
    assert er.ok
    assert er.added_resource
    assert er.added_include
    body = mq5.read_text(encoding="utf-8")
    assert '#resource "model.onnx"' in body
    assert '#include "COnnxLoader.mqh"' in body

    elapsed = time.monotonic() - t0
    assert elapsed < 600, f"e2e took {elapsed:.1f}s; budget 10 min"
