---
id: 71-onnx-mql5
title: ONNX in MQL5 (build 4620+ → 5572 CUDA)
tags: [onnx, ml, cuda, gpu]
applicable_phase: D
---

# ONNX in MQL5 (build 4620+ → 5572 CUDA)

`#resource "model.onnx"` embeds the ONNX model into the
`.ex5`; `OnnxCreateFromBuffer` loads it at runtime; `OnnxRun` drives
inference.  Required opset ≥ 14 (see `onnx_export.py`).  Latency
budget per the kit: p95 ≤ 1 ms per tick (see AP-19).

## Build history

| Build | Released | What it added |
|---|---|---|
| 4620 | Oct 2024 | `OnnxCreate`, `OnnxCreateFromBuffer`, `OnnxRun`, `OnnxRelease`. |
| 5260 | Jul 2025 | Implicit `float32` ↔ `double` casts on input/output buffers. |
| **5572** | **Jan 2026** | **`OnnxSetExecutionProviders(handle, providers[])`** — pick a non-CPU execution provider (CUDA, DirectML, …) at runtime. |

## Picking a provider

The exporter records the *intended* provider list so the deploy path
stays declarative — you tell `onnx_export` once whether the model was
profiled against CPU or CUDA, and `COnnxLoader` honours that on every
`InitFromResource()` call.

```
# CPU-only (default; works on every build).
python -m vibecodekit_mql5.onnx_export model.onnx
# → {"providers": ["cpu"], ...}

# CUDA-preferred (requires MT5 build ≥ 5572 + a CUDA-capable ONNX
# Runtime on the host).
python -m vibecodekit_mql5.onnx_export model.onnx --providers cuda
# → {"providers": ["cuda"], ...}

# CUDA-with-CPU-fallback. The MQL5 runtime walks the list in order.
python -m vibecodekit_mql5.onnx_export model.onnx --providers cuda,cpu
```

On the MQL5 side `COnnxLoader.InitFromResource(name, provider)` takes
the provider id as a second string argument and silently falls back to
CPU on older builds — Plan v5 §13 treats CUDA as best-effort
acceleration, never a correctness requirement, so an EA built against
build 5572 still runs on build 5260:

```mql5
COnnxLoader onnx;
if(!onnx.InitFromResource("model.onnx", "cuda"))
   return INIT_FAILED;
Print("running on ", onnx.Provider());     // "cuda" or "cpu"
```

When you compile against a recent MetaEditor that has the
`OnnxSetExecutionProviders` symbol, define
`ONNX_HAS_SET_EXECUTION_PROVIDERS` in your project to enable the real
call; otherwise `COnnxLoader` keeps the CPU path active.

## Anti-pattern hooks

- **AP-19** (`onnx_run_in_ontick_no_budget`): even on CUDA you still
  need the p95 ≤ 1 ms guard — GPU launch latency dominates short
  sequences and can wreck tick throughput.
- **AP-?** *(planned)*: `--providers cuda` without a paired
  `ONNX_HAS_SET_EXECUTION_PROVIDERS` define on the EA side is a silent
  CPU downgrade; the linter will warn in a future build.
