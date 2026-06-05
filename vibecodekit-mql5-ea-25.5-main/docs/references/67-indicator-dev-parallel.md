---
id: 67-indicator-dev-parallel
title: Indicator development workflow
tags: [indicator, dev, oncalculate]
applicable_phase: A
---

# Indicator development workflow

Indicator development runs parallel to EA development but **deploys
independently** — indicators compile to `.ex5` files dropped in
`MQL5/Indicators/`, EAs reference them at runtime via `iCustom()` (or
the typed helpers `iMACD`, `iSAR`, …). The two lifecycles share the
linter and the scaffold conventions, but their entry points differ.

## Scaffold

```bash
python -m vibecodekit_mql5.build indicator-only \
    --name MyIndicator --symbol EURUSD --tf H1
```

This renders `scaffolds/indicator-only/netting/EAName.mq5`, which is
intentionally signal-only — no `OrderSend`, no `CTrade`. It still
pulls in `CPipNormalizer` / `CRiskGuard` / `CMagicRegistry` so the
indicator can publish pip-normalised buffers and reuse the magic
registry for paired-EA workflows.

## `OnCalculate` contract

```mql5
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double  &open[],
                const double  &high[],
                const double  &low[],
                const double  &close[],
                const long    &tick_volume[],
                const long    &volume[],
                const int     &spread[])
  {
   // Always start from prev_calculated; never recompute the full history
   // unless prev_calculated == 0 (cold start / timeframe switch).
   int start = (prev_calculated == 0) ? 0 : prev_calculated - 1;
   for(int i = start; i < rates_total; ++i)
     {
      // … fill buffer[i] …
     }
   return rates_total;   // tell the platform how far we got
  }
```

Key invariants the linter implicitly enforces (via the EA-side
detectors that double-check on `iCustom` consumers):

- Return `rates_total` on success; returning `0` forces a full
  recalculation next tick — punishing for HFT consumers.
- Never call `Sleep`, `WebRequest`, or any blocking I/O inside
  `OnCalculate`. Move those to `OnTimer` and publish via a buffer.
- Indicator buffers are `SetIndexBuffer`'d in `OnInit`; do not
  resize at runtime.

## Linking from an EA

EAs reference custom indicators by file name relative to
`MQL5/Indicators/`:

```mql5
int h = iCustom(_Symbol, _Period, "MyIndicator", /* params… */);
if(h == INVALID_HANDLE)
   return INIT_FAILED;
CopyBuffer(h, /* index */ 0, /* shift */ 0, /* count */ 3, buf);
```

Release the handle in `OnDeinit` (`IndicatorRelease(h)`); leaking the
handle leaves the indicator computing forever on the chart.

## Parallel build lane

`indicator-only` is one preset of `mql5-build` (`PHASE_D_PRESETS` in
`scripts/vibecodekit_mql5/build.py`), rendered with the same
`{name, symbol, tf, magic}` template substitution as the EA scaffolds.
That keeps both lanes diff-able with the same `mql5-lint` — AP-3 /
AP-15 / AP-18 trigger on indicators too if they ever reach for the
trade APIs (which they should not).
