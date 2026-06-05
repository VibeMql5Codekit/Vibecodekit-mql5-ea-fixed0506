---
id: 76-llm-patterns
title: LLM bridge patterns
tags: [llm, ai]
applicable_phase: D
---

# LLM bridge patterns

3 patterns:

1. **cloud-api** — `WebRequest` → OpenAI/Anthropic/Gemini
2. **self-hosted-ollama** — `WebRequest` → `http://localhost:11434`
3. **embedded-onnx-llm** — Phi-3-mini ONNX in-process via
   `COnnxLoader`

Each scaffold ships a 5-second timeout + rule-based fallback so the EA
stays safe when the LLM is unreachable (Trader-17 #14 + #16).
