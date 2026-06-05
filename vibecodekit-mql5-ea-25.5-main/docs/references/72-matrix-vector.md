---
id: 72-matrix-vector
title: Matrix / vector first-class types
tags: [matrix, vector, blas, openblas, lapack]
applicable_phase: D
---

# Matrix / vector first-class types

Build 3300+ added `matrix` and `vector` as first-class types
with BLAS-backed operations: `MatMul`, `Inv`, `Det`, eigen
decomposition, etc.  Use them for portfolio math (covariance,
optimisation) instead of hand-rolled arrays.

## Build 5260 — OpenBLAS Matrix Balance (Jul 2025)

Build 5260 wired five LAPACK-style balancing routines into the
`matrix` type, fronted by `MatrixBalance` and accessible through
the OpenBLAS path that already powers `MatrixEig`.  Balancing
permutes + diagonally rescales a matrix so its eigenvalues sit on a
similar magnitude scale, which sharply improves the numerical
accuracy of every downstream eigen / SVD call — exactly the case
that wrecked the kit's portfolio-basket covariance fits on
high-condition-number matrices pre-5260.

| MQL5 method | LAPACK driver | Use case |
|---|---|---|
| `matrix::Balance(MATRIX_BALANCE_PERMUTE)` | `xGEBAL P` | Permute rows/cols to isolate diagonal blocks. |
| `matrix::Balance(MATRIX_BALANCE_SCALE)`   | `xGEBAL S` | Diagonal rescale only — keep ordering. |
| `matrix::Balance(MATRIX_BALANCE_BOTH)`    | `xGEBAL B` | Default: permute **and** rescale (recommended). |
| `matrix::BalancePermute()` *(getter)*     | n/a        | Returns the permutation vector applied by the last `Balance`. |
| `matrix::BalanceScale()` *(getter)*       | n/a        | Returns the diagonal scaling vector applied by the last `Balance`. |

Use the result *before* calling `Eig` / `EigVals` / `Schur` on any
matrix whose condition number you can't bound a priori — typical
case in the kit is a >20-asset covariance matrix sampled across
mixed liquidity tiers, where unbalanced eigen decomposition can
silently lose 3-4 digits of precision.

```mql5
matrix C = PortfolioCovariance(returns);   // d×d, d up to ~50
C.Balance(MATRIX_BALANCE_BOTH);            // build 5260+
vector eigs;
matrix vecs;
C.Eig(eigs, vecs);                          // numerics now stable
```

## Pre-5260 fallback

On older builds the kit's `scripts/vibecodekit_mql5/portfolio_math.py`
shells the same balance routine through `numpy.linalg` (LAPACK
`*gebal` family) before round-tripping the matrix through `OnnxRun`,
so the algorithm is identical and only the runtime location moves.

## Anti-pattern hooks

- **AP-?** *(planned)*: `matrix::Eig` on a >10×10 matrix without a
  preceding `Balance` call is flagged as a numerical-precision risk
  on build ≥ 5260.  The detector is intentionally off on older builds
  because the API doesn't exist there.
