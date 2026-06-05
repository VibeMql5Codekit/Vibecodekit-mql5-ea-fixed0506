"""Phase D LLM bridge unit tests — 6 cases (3 patterns × 2 axes).

Each scaffold is validated for:
- presence of the bridge include header + class name match
- presence of a rule-based fallback path (Trader-17 #14, #16)

The python-side wirer ``llm_context.wire_llm`` is also exercised for
each pattern.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5 import llm_context

REPO = Path(__file__).resolve().parents[3]
SCAFFOLDS = REPO / "scaffolds" / "service-llm-bridge"


@pytest.mark.parametrize(
    "pattern,header_cls",
    [
        ("cloud-api",          "LlmCloudApiBridge"),
        ("self-hosted-ollama", "LlmSelfHostedOllamaBridge"),
        ("embedded-onnx-llm",  "LlmEmbeddedOnnxLlmBridge"),
    ],
)
def test_scaffold_ships_with_fallback(pattern: str, header_cls: str) -> None:
    base = SCAFFOLDS / pattern
    assert (base / "EAName.mq5").exists()
    header = base / f"{header_cls}.mqh"
    assert header.exists(), f"missing header {header}"
    body = header.read_text(encoding="utf-8")
    assert "fallback" in body.lower() or "_fallback" in body, \
        "every LLM bridge must implement a rule-based fallback"


@pytest.mark.parametrize(
    "pattern,expected_init_args",
    [
        ("cloud-api",          "_Symbol, _Period, 5000"),
        ("self-hosted-ollama", "_Symbol, _Period, 5000"),
        ("embedded-onnx-llm",  "NULL, _Symbol, _Period"),
    ],
)
def test_wire_llm_inserts_include(
    pattern: str, expected_init_args: str, tmp_path: Path,
) -> None:
    mq5 = tmp_path / "EA.mq5"
    mq5.write_text(
        '#property strict\n\nint OnInit() { return INIT_SUCCEEDED; }\n',
        encoding="utf-8",
    )
    rep = llm_context.wire_llm(mq5, pattern)
    assert rep.ok
    body = mq5.read_text()
    expected_cls = llm_context._pattern_class(pattern)
    assert f'#include "{expected_cls}.mqh"' in body
    assert f"{expected_cls} llm;" in body
    # Regression: every bridge's Init() takes mandatory args; an argument-less
    # ``llm.Init()`` call won't compile against the new signatures.
    assert "llm.Init()" not in body
    assert f"llm.Init({expected_init_args})" in body


# --- regression tests for the Phase D review findings -----------------

@pytest.mark.parametrize(
    "header_path",
    [
        "cloud-api/LlmCloudApiBridge.mqh",
        "embedded-onnx-llm/LlmEmbeddedOnnxLlmBridge.mqh",
    ],
)
def test_ma_fallback_reads_value_via_copybuffer(header_path: str) -> None:
    """``iMA()`` returns a handle in MQL5 — the fallback must read with CopyBuffer."""
    body = (SCAFFOLDS / header_path).read_text(encoding="utf-8")
    # the bug looked like: ``double ma_fast = iMA(...);`` — comparing handles.
    assert "double ma_fast = iMA" not in body
    assert "double ma_slow = iMA" not in body
    # the fix: handles cached as members + CopyBuffer in fallback.
    assert "CopyBuffer" in body
    assert "IndicatorRelease" in body
    assert "m_h_fast" in body
    assert "m_h_slow" in body


def test_ollama_rsi_fallback_reads_value_via_copybuffer() -> None:
    body = (SCAFFOLDS / "self-hosted-ollama" /
            "LlmSelfHostedOllamaBridge.mqh").read_text(encoding="utf-8")
    assert "double rsi = iRSI" not in body
    assert "const double rsi = iRSI" not in body
    assert "CopyBuffer" in body
    assert "IndicatorRelease" in body
    assert "m_h_rsi" in body


def test_cloud_api_scaffold_sets_and_kills_timer() -> None:
    """The cloud-api scaffold must call EventSetTimer/EventKillTimer so that
    its ``OnTimer`` handler — the AP-17-compliant LLM call site — actually
    fires.  Without these calls the LLM logic is dead code."""
    body = (SCAFFOLDS / "cloud-api" / "EAName.mq5").read_text(encoding="utf-8")
    assert "EventSetTimer(" in body
    assert "EventKillTimer(" in body


def test_cloud_api_ontimer_has_void_return_type() -> None:
    """In MQL5 the OnTimer prototype is ``void OnTimer(void)``.  Declaring it
    as ``int`` prevents MetaTrader from dispatching timer events."""
    body = (SCAFFOLDS / "cloud-api" / "EAName.mq5").read_text(encoding="utf-8")
    assert "int OnTimer(void)" not in body
    assert "void OnTimer(void)" in body


def test_trend_scaffold_uses_ma_handles_not_values() -> None:
    mq5 = REPO / "scaffolds" / "trend" / "netting" / "EAName.mq5"
    body = mq5.read_text(encoding="utf-8")
    # bug pattern: assigning iMA's handle return to a double
    assert "double fast = iMA" not in body
    assert "double slow = iMA" not in body
    # fix: integer handles + CopyBuffer
    assert "h_fast = iMA" in body
    assert "h_slow = iMA" in body
    assert "CopyBuffer" in body
