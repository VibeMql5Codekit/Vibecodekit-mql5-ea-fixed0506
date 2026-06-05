---
id: 51-platform-arch
title: MetaTrader 5 platform architecture
tags: [platform, architecture]
applicable_phase: A
---

# MetaTrader 5 platform architecture

MetaTrader 5 splits responsibilities across three processes:

- **Terminal** (`terminal64.exe`) — connects to the broker server,
  paints charts, runs EAs/scripts/indicators, owns Market Watch and the
  Strategy Tester.
- **MetaEditor** (`metaeditor64.exe`) — compiles `.mq5`/`.mqh` into
  `.ex5` and emits build logs.  The kit calls it via Wine on Linux.
- **Broker server** — hosts orders, history, ticks.  The terminal
  reconnects + re-syncs after each disconnect.

EAs are sandboxed: `WebRequest` URLs must be whitelisted in
`Tools → Options → Expert Advisors`, file I/O is restricted to
`MQL5/Files/`, and DLLs require an explicit allow.  The kit never
relies on DLLs because they break Cloud Network optimisation.

The Strategy Tester runs EAs in a separate process and can spin up
**agents** locally or on the MQL5 Cloud Network — these are addressed
in references 73 (Cloud Network) and 74 (VPS).
