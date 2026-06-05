---
id: 78-opencl
title: OpenCL (GPU compute)
tags: [opencl, gpu, build3300]
applicable_phase: D
---

# OpenCL (GPU compute)

Build 3300+ exposes OpenCL as a first-class compute path via
`CLContextCreate`, `CLProgramCreate`, `CLKernelCreate`,
`CLBufferCreate`, `CLExecute`. Use it for matrix-heavy operations
(neural-net training, covariance matrices, Monte-Carlo simulations)
where the CPU `matrix` type hits a wall. Inference of pre-trained
models stays on the ONNX path (`71-onnx-mql5.md`) since `OnnxRun` has
its own GPU EP on build 5572+.

## Minimal end-to-end

```mql5
const string kSrc =
"__kernel void axpy(const float a, __global const float* x,"
"                   __global float* y, const int n) {"
"  int i = get_global_id(0); if (i < n) y[i] = a*x[i] + y[i]; }";

int ctx = CLContextCreate(CL_USE_GPU_ONLY);
if(ctx == INVALID_HANDLE) return INIT_FAILED;

int prog = CLProgramCreate(ctx, kSrc);
int kern = CLKernelCreate(prog, "axpy");

const int n = ArraySize(x);
int buf_x = CLBufferCreate(ctx, n * sizeof(float), CL_MEM_READ_ONLY);
int buf_y = CLBufferCreate(ctx, n * sizeof(float), CL_MEM_READ_WRITE);
CLBufferWrite(buf_x, x);
CLBufferWrite(buf_y, y);

CLSetKernelArg(kern, 0, /*float*/  2.5f);
CLSetKernelArgMem(kern, 1, buf_x);
CLSetKernelArgMem(kern, 2, buf_y);
CLSetKernelArg(kern, 3, /*int*/   n);

uint global_size[1] = { (uint)n };
CLExecute(kern, 1, global_size);
CLBufferRead(buf_y, y);

CLBufferFree(buf_x); CLBufferFree(buf_y);
CLKernelFree(kern); CLProgramFree(prog); CLContextFree(ctx);
```

## Fallback strategy

There is no single "OpenCL or CPU" toggle — code each kernel with a
CPU path behind it and select at `OnInit`:

```mql5
bool gpu_ok = false;
if(CLContextCreate(CL_USE_GPU_ONLY) != INVALID_HANDLE) gpu_ok = true;
```

The kit's convention is to expose `--use-gpu` only as an EA input
(never as an optimiser dimension) so a CPU fallback never inflates
the optimiser surface.

## Build 5260 note

Build 5260 widened the OpenBLAS path behind `matrix` and `vector`
(see `72-matrix-vector.md` for Matrix Balance + Schur). For most
linear-algebra workloads the OpenBLAS path now beats a hand-rolled
OpenCL kernel — measure before reaching for OpenCL on small inputs
(< 1k × 1k).

## When NOT to use OpenCL

- Per-tick inference of a small (≤ 1 MB) ONNX model — host-to-device
  copy dominates kernel time; stay on `OnnxRun` CPU EP.
- Anything that must run on the MQL5 Cloud Network — Cloud agents
  do not advertise GPU; the optimisation will silently fall back to
  CPU and your cost estimate will be wrong.
- Indicators in `OnCalculate` — the GPU launch latency exceeds the
  inter-tick budget for most timeframes < M5.
