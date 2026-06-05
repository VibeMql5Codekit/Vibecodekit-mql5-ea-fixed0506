"""Phase D — full scaffold matrix lint regression.

Renders **every** (preset, stack) pair declared in `build.PRESETS`, then
asserts each rendered .mq5 lints clean (no ERROR findings). This is the
direct regression of the v1.0.2 deep-test demo, which exposed several
MQL5-specific compile bugs in the LLM bridge scaffolds:

  - `WHOLECHAR_NULL` doesn't exist (correct: `-1` for "until terminator")
  - `OnnxCreateFromBuffer(NULL, 0, 0)` wrong arg count (correct: 2 args)
  - `input` / `output` are reserved MQL5 keywords; can't be used as
    variable names inside a function body
  - cloud-api / ollama had 7-8 `input` declarations (tripped AP-5);
    HTTP-deployment knobs are now `sinput` (excluded from optimizer)
  - `#resource "phi3_mini.onnx"` referenced a file not shipped (now
    ships as a 128-byte stub)

These tests do NOT require Wine / MetaEditor — they verify lint clean
+ static text patterns. The full compile matrix (Wine) is exercised
manually via the demo script and not part of CI to keep CI fast and
platform-portable.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vibecodekit_mql5 import lint
from vibecodekit_mql5.build import PRESETS, BuildRequest, build

REPO = Path(__file__).resolve().parents[3]


def _all_preset_stack_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for preset, stacks in PRESETS.items():
        for stack in stacks:
            pairs.append((preset, stack))
    return pairs


@pytest.mark.parametrize("preset,stack", _all_preset_stack_pairs())
def test_every_scaffold_lints_clean(preset: str, stack: str, tmp_path: Path) -> None:
    """Render preset/stack to a tmp dir; assert lint exits 0
    (no ERROR-severity findings).
    """
    out = tmp_path / f"{preset}_{stack}"
    req = BuildRequest(
        preset=preset,
        name="LintMatrixEA",
        symbol="EURUSD",
        tf="H1",
        stack=stack,
        out_dir=out,
        scaffolds_root=REPO / "scaffolds",
        include_root=REPO / "Include",
    )
    build(req)
    mq5 = out / "LintMatrixEA.mq5"
    assert mq5.is_file(), f"render produced no .mq5 for {preset}/{stack}"
    rc = lint.main([str(mq5)])
    assert rc == 0, (
        f"lint must be clean for scaffold {preset}/{stack}; "
        f"rendered at {mq5}"
    )


def test_llm_cloud_api_uses_sinput_for_deployment_knobs() -> None:
    """The cloud-api LLM bridge ships 7 inputs total — the 7th
    (`InpLlmTimeoutMs`) MUST be declared `sinput` (excluded from the
    optimizer) so AP-5 (>6 optimizable inputs) stays clean. Regression
    for the v1.0.2 deep-test demo.
    """
    text = (REPO / "scaffolds/service-llm-bridge/cloud-api/EAName.mq5").read_text()
    assert "sinput int   InpLlmTimeoutMs" in text


def test_llm_ollama_uses_sinput_for_deployment_knobs() -> None:
    """The ollama bridge ships 8 inputs total — the model name + timeout
    MUST be `sinput` (deployment config, not optimizer targets). Regression
    for the v1.0.2 deep-test demo.
    """
    text = (REPO / "scaffolds/service-llm-bridge/self-hosted-ollama/EAName.mq5").read_text()
    assert "sinput string InpModel" in text
    assert "sinput int    InpLlmTimeoutMs" in text


def test_llm_bridges_dont_use_invented_constants() -> None:
    """`WHOLECHAR_NULL` is not a real MQL5 constant — it was a stray
    placeholder that crept into the cloud-api + ollama scaffolds and
    broke compile. Regression: this token must never reappear in any
    scaffold or shipped Include.
    """
    forbidden = re.compile(r"\bWHOLECHAR_NULL\b")
    for path in (REPO / "scaffolds").rglob("*.mq[5h]"):
        body = path.read_text(encoding="utf-8")
        assert not forbidden.search(body), (
            f"{path} contains the invented constant WHOLECHAR_NULL; "
            f"use -1 as the count argument to StringToCharArray instead."
        )
    for path in (REPO / "Include").glob("*.mqh"):
        body = path.read_text(encoding="utf-8")
        assert not forbidden.search(body)


def test_onnx_loader_uses_correct_OnnxCreateFromBuffer_signature() -> None:
    """OnnxCreateFromBuffer takes 2 args: `(const uchar &buffer[], ulong flags)`.
    The original scaffold passed 3 args and triggered MetaEditor error 199
    (wrong parameters count). Regression: only allow either
      - no call at all, or
      - a 2-arg call with a uchar buffer + flags.
    """
    body = (REPO / "Include/COnnxLoader.mqh").read_text(encoding="utf-8")
    # Match all OnnxCreateFromBuffer(...) call sites and parse their arg
    # counts. The simplest robust check: split on commas inside parens.
    pat = re.compile(r"OnnxCreateFromBuffer\s*\(([^)]*)\)")
    for m in pat.finditer(body):
        args_text = m.group(1).strip()
        if not args_text:
            continue
        # Split on commas at top level (no nested parens in this scaffold).
        n_args = args_text.count(",") + 1
        assert n_args == 2, (
            f"OnnxCreateFromBuffer must be called with exactly 2 args "
            f"(buffer, flags); got {n_args} in: {m.group(0)}"
        )


def test_embedded_onnx_scaffold_ships_stub_model() -> None:
    """The embedded-onnx-llm scaffold uses `#resource "phi3_mini.onnx"`,
    so the scaffold MUST ship a stub `phi3_mini.onnx` alongside the .mq5
    or MetaEditor compile fails with error 310 (resource file not found).
    """
    stub = REPO / "scaffolds/service-llm-bridge/embedded-onnx-llm/phi3_mini.onnx"
    assert stub.is_file(), f"missing stub ONNX model at {stub}"
    assert stub.stat().st_size > 0, "stub must be non-empty for #resource to work"


def test_build_copies_binary_scaffold_assets_unchanged(tmp_path: Path) -> None:
    """The build command historically read every file as UTF-8 text +
    re-wrote it after template substitution. That corrupts binary
    files like `.onnx` model stubs. Regression: build must copy known
    binary suffixes (`.onnx`, `.png`, etc.) byte-for-byte.
    """
    out = tmp_path / "EmbeddedOnnxCopyTest"
    req = BuildRequest(
        preset="service-llm-bridge",
        name="EmbeddedOnnxCopyTest",
        symbol="EURUSD",
        tf="H1",
        stack="embedded-onnx-llm",
        out_dir=out,
        scaffolds_root=REPO / "scaffolds",
        include_root=REPO / "Include",
    )
    build(req)

    src_stub = REPO / "scaffolds/service-llm-bridge/embedded-onnx-llm/phi3_mini.onnx"
    dst_stub = out / "phi3_mini.onnx"
    assert dst_stub.is_file(), f"build did not copy {src_stub} to {dst_stub}"
    assert dst_stub.read_bytes() == src_stub.read_bytes(), (
        "build corrupted the binary stub during copy — must be byte-for-byte"
    )


def test_embedded_onnx_bridge_does_not_use_reserved_keywords() -> None:
    """`input` and `output` are reserved MQL5 keywords (used at the file
    top level to declare optimizer-visible parameters). They must NOT
    appear as variable names inside function bodies. Regression for the
    embedded-onnx-llm SuggestOrFallback() bug.
    """
    body = (
        REPO / "scaffolds/service-llm-bridge/embedded-onnx-llm/LlmEmbeddedOnnxLlmBridge.mqh"
    ).read_text(encoding="utf-8")
    # Forbidden: `float input[`, `float output[`, etc. (the local-buffer
    # declaration pattern that originally broke compile).
    forbidden = re.compile(
        r"\b(?:float|int|double|long|uchar|short)\s+(?:input|output)\s*\["
    )
    m = forbidden.search(body)
    assert m is None, (
        f"reserved MQL5 keyword used as variable name in scaffold: "
        f"{m.group(0) if m else '?'}"
    )


@pytest.mark.parametrize(
    "bridge",
    [
        "scaffolds/service-llm-bridge/cloud-api/LlmCloudApiBridge.mqh",
        "scaffolds/service-llm-bridge/self-hosted-ollama/LlmSelfHostedOllamaBridge.mqh",
    ],
)
def test_webrequest_payload_uses_StringLen_not_minus_one(bridge: str) -> None:
    """Per MQL5 docs, StringToCharArray with count=-1 copies the trailing
    null terminator into the output array. When that array is passed to
    WebRequest, the request body ends with a stray \\0 byte and strict
    JSON parsers (Python json.loads(), Go json.Unmarshal()) reject the
    payload with a "trailing data" / "invalid character after top-level
    value" error. Regression: the LLM bridge scaffolds must use
    StringLen(payload) as the explicit count so the request body is
    exactly the JSON bytes, with no trailing null.
    """
    body = (REPO / bridge).read_text(encoding="utf-8")
    # Find every StringToCharArray(...) call. Each call must have its
    # count argument set to StringLen(...). -1 / WHOLE_ARRAY / similar
    # whole-string sentinels are banned because they all copy the
    # terminator.
    pat = re.compile(r"StringToCharArray\s*\(([^)]*)\)")
    matches = list(pat.finditer(body))
    assert matches, f"expected at least one StringToCharArray call in {bridge}"
    for m in matches:
        call = m.group(0)
        args = [a.strip() for a in m.group(1).split(",")]
        # Signature: (text, array, start=0, count=-1, codepage=CP_ACP).
        assert len(args) >= 4, (
            f"StringToCharArray in {bridge} must pass an explicit count "
            f"arg; got: {call}"
        )
        count_arg = args[3]
        assert count_arg != "-1", (
            f"{bridge}: StringToCharArray must NOT use count=-1 for "
            f"a WebRequest body (the trailing \\0 breaks strict JSON "
            f"parsers); use StringLen(payload) instead. Found: {call}"
        )
        assert "StringLen(" in count_arg, (
            f"{bridge}: StringToCharArray count must be StringLen(...) "
            f"to exclude the trailing null terminator; got: {count_arg!r}"
        )
