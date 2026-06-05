# Phase D Spec — Tech 2024-2025

> ⚠️ **Internal / contributor document.** Sprint spec for this kit's own development — not user-facing. See [`README.md`](../README.md) and [`docs/QUICKSTART.md`](QUICKSTART.md) instead.

**Goal:** ONNX + HFT async + Algo Forge + LLM bridge + Cloud Network + Method-hiding linter.
**Duration:** 3-4 weeks.
**Tag on completion:** v0.5.0.
**Prereq:** v0.3.0.

## Files added in Phase D

```
Include/
├── COnnxLoader.mqh                           # ONNX inference wrapper
└── CAsyncTradeManager.mqh                    # OrderSendAsync helper

scripts/vibecodekit_mql5/
├── onnx_export.py                            # /mql5-onnx-export
├── onnx_embed.py                             # /mql5-onnx-embed
├── async_build.py                            # /mql5-async-build
├── forge_init.py                             # /mql5-forge-init
├── forge_pr.py                               # /mql5-forge-pr
├── llm_context.py                            # /mql5-llm-context
├── cloud_optimize.py                         # /mql5-cloud-optimize
└── method_hiding_check.py                    # /mql5-method-hiding-check

scaffolds/
├── ml-onnx/
│   ├── netting/                              # extend Phase A scaffold
│   ├── hedging/
│   └── python-bridge/
│       ├── python/
│       │   ├── train.py                      # PyTorch toy LSTM
│       │   ├── export_onnx.py
│       │   └── requirements.txt
│       └── (existing Phase A files)
├── hft-async/
│   └── netting/
│       ├── EAName.mq5                        # OrderSendAsync template
│       ├── Sets/default.set
│       └── README.md
├── service-llm-bridge/
│   ├── cloud-api/
│   ├── self-hosted-ollama/
│   └── embedded-onnx-llm/
├── trend/                                    # 13 strategy scaffolds × 3 stack
├── mean-reversion/
├── breakout/
├── hedging-multi/
├── news-trading/
├── arbitrage-stat/
├── scalping/
├── library/
├── indicator-only/
├── grid/
└── dca/

tests/gates/phase-D/
├── test_phase_d_acceptance.py                # 1 e2e
├── test_onnx.py                              # 5 unit
├── test_async_hft.py                         # 4 unit
├── test_algo_forge.py                        # 4 unit
├── test_llm_bridge.py                        # 6 unit
├── test_cloud_optimize.py                    # 3 unit
└── test_method_hiding.py                     # 3 unit
```

## 26 tests (acceptance gate)

### 1 e2e
- `test_onnx_pipeline_e2e` — PyTorch train (toy LSTM) → ONNX export → embed in EA → compile → tester run, < 10 min total

### 25 unit
- 5 ONNX (export, embed, validate, latency check, opset enforcement)
- 4 HFT (async build render, OnTradeTransaction detect, AP-18 detect, end-to-end async test)
- 4 Algo Forge (init, PR push, mock 401 retry, list repos)
- 6 LLM (3 patterns × 2: render + fallback rule)
- 3 Cloud Network (cost calc, budget cap, mode gate enforcement)
- 3 Method-hiding (build < 5260 warn, build ≥ 5260 error, explicit using directive ok)

## ONNX pipeline performance

- Train toy LSTM (1 feature: EURUSD M1 returns, 1000 bars) < 5 min on Devin VM
- Export ONNX < 30s
- Embed in EA + compile < 30s
- Tester run (1 month period) < 5 min on Wine

Total e2e budget: 10 min.

## Method-hiding linter logic

```python
def check_method_hiding(mq5_path: str, target_build: int = 5260) -> List[Issue]:
    """
    Detect: derived class method with same name as base class method,
    WITHOUT explicit `using BaseClass::method;` directive.
    
    Severity:
        target_build < 5260: WARN
        target_build >= 5260: ERROR
    """
    # Parse MQL5 inheritance via heuristic regex (full AST not feasible)
    # Cross-reference base class method names
    # Check for `using` directives
    ...
```

False positive tolerance: ≤ 30%. Allow opt-out via `// vck-mql5: hiding-ok` comment.

## LLM bridge fallback rule (mandatory)

Every LLM scaffold must implement timeout + fallback:
```cpp
string llm_response = "";
if (LLM_BRIDGE_TIMEOUT > 0) {
    llm_response = WebRequestWithTimeout(LLM_URL, payload, 5000); // 5s timeout
}
if (llm_response == "") {
    // Fallback to rule-based logic (Trader-17 #14, #16)
    return RuleBased_DecideTrade(...);
}
return Parse_LLM_Response(llm_response);
```

## Acceptance gate

- [ ] v0.3.0 merged
- [ ] 26/26 tests pass
- [ ] audit clean
- [ ] All modules < 200 LOC
- [ ] ONNX e2e completes in < 10 min on Linux Devin VM
- [ ] All 22 anti-patterns now in lint.py (8 critical + 13 best-practice + 1 method-hiding)
- [ ] 13 additional strategy scaffolds present (trend, mean-reversion, breakout, hedging-multi, news, arbitrage, scalping, library, indicator-only, grid, dca + ml-onnx + hft-async + service-llm-bridge × variants)
- [ ] `git tag v0.5.0` after merge
