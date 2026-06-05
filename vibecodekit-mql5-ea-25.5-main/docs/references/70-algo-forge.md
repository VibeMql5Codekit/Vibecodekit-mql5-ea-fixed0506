---
id: 70-algo-forge
title: Algo Forge (build 5100+ Git platform)
tags: [forge, git, mcp]
applicable_phase: D
---

# Algo Forge (build 5100+ Git platform)

MetaQuotes shipped a built-in Git host (Algo Forge) in build 5100+ at
`forge.mql5.io`. The kit wraps it three ways: two Python CLI commands
(`mql5-forge-init`, `mql5-forge-pr`) and an MCP server
(`algo-forge-bridge`) for IDE / agent integration.

## Authentication

A REST API token is read from `$MQL5_FORGE_TOKEN` (preferred) or from
the `--token` CLI flag. The token is **never** logged and never written
to the generated artefacts. Treat it as a secret on par with broker
credentials.

```bash
export MQL5_FORGE_TOKEN="$(cat ~/.config/mql5-forge/token)"
```

## Workflow

```bash
# 1. Create a new repo on forge.mql5.io (returns its clone URL).
python -m vibecodekit_mql5.forge_init MyEA --description "MACD+SAR EURUSD H1"

# 2. After local commits + git push, open a PR head→base on Algo Forge.
python -m vibecodekit_mql5.forge_pr MyEA \
    --head devin/feature --base main \
    --title "Add MFE/MAE logger" --body "$(cat CHANGELOG.md)"
```

Both commands print a `ForgeReport` JSON document with `ok`, `status`,
`endpoint`, and the API response body so CI logs stay diffable.

## Mockable transport

`forge_init.py` / `forge_pr.py` accept a `transport` callable injected
by tests so the unit-test suite never hits the real Forge API. The
default transport is `urllib.request.urlopen` with a 15 s timeout.

`forge_pr.open_pr()` automatically **retries once** on HTTP 401 — this
covers the rare stale-OAuth-refresh race observed in production.

## MCP bridge — `algo-forge-bridge`

`mcp/algo-forge-bridge/server.py` exposes the same operations over the
MCP JSON-RPC 2.0 stdio protocol so agentic IDEs can drive Forge without
a separate CLI subshell. Tool names map 1:1 with the Python CLI:

| MCP tool | Equivalent CLI |
|---|---|
| `forge.repo.create` | `mql5-forge-init` |
| `forge.pr.open`     | `mql5-forge-pr` |
| `forge.pr.list`     | (Python-only helper in `forge_pr.py`) |

Use the MCP route from IDEs that already speak MCP (Cursor, Zed,
Claude Desktop, …); fall back to the Python CLI in plain shells.
