---
id: 75-webrequest
title: WebRequest patterns
tags: [webrequest, http, ap-17]
applicable_phase: D
---

# WebRequest patterns

`WebRequest` is synchronous — the call blocks the EA's thread until
the HTTP response arrives. Inside `OnTick` that blocks the *next* tick
too, freezing the EA for the broker's tick interval × the response
latency. The kit treats this as a hard failure.

## Anti-pattern hook — AP-17

`scripts/vibecodekit_mql5/lint.py:detect_ap17` parses the EA source,
extracts the body of `OnTick` and `OnTimer`, and raises an `ERROR` if
`WebRequest(` appears inside either:

```
EAName.mq5:88:5: ERROR AP-17: WebRequest in OnTick blocks the tick — move to OnInit/timer task
```

The detector intentionally catches `OnTimer` as well, because
`EventSetTimer` is commonly used as a "WebRequest shelter" that turns
out to also block — `OnTimer` shares the EA thread with `OnTick`.

## Where to put `WebRequest`

| Location | OK? | Notes |
|---|---|---|
| `OnInit`                | ✓ | One-shot config fetch is fine; treat as part of startup. |
| Dedicated background **Service** (build 5320+) | ✓ | See `scaffolds/service/standalone/`. The Service runs on its own thread with no `OnTick` contract. |
| `OnTick`                | ✗ | Blocked by AP-17. |
| `OnTimer`               | ✗ | Same thread as `OnTick`. Blocked by AP-17. |
| Indicator `OnCalculate` | ✗ | Same thread as the chart. Move to a paired Service. |

The Service scaffold (`build 5320+`) is the canonical home for
long-running HTTP polling, LLM bridges, and webhook publishing — see
`scaffolds/service/standalone/EAName.mq5` for the
`while(!IsStopped()) { … }` loop pattern.

## Host whitelisting

MetaTrader 5 refuses `WebRequest` unless the destination host is
listed in **Tools → Options → Expert Advisors → Allow WebRequest for
listed URL**. Ship the EA with a short README block telling the user
exactly which URLs to add — do not silently fail at runtime when the
list is empty.

## Secret handling

The API key is a secret. The kit's convention is:

- Never hardcode it into the `.mq5` source — the source ships to
  Algo Forge / CodeBase and is publicly indexable.
- Read it from a file under the terminal's data path
  (`TerminalInfoString(TERMINAL_DATA_PATH)`) in `OnInit`, or pull it
  from a paired Service that owns the HTTP call.
- Strip it from `Print()` / `Comment()` output; logs go through the
  Journal which third parties can see during a CodeBase audit.

## Timeout

`WebRequest` accepts a `timeout` argument in milliseconds — default
ranges from 5–30 s depending on build. Always pass an explicit
timeout (≤ 5000 ms for Service polling, ≤ 2000 ms for any in-EA call
that you have already moved off `OnTick`). A missing timeout makes
hung HTTPS handshakes unrecoverable without a terminal restart.
