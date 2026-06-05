---
id: 80-input-syntax
title: input attribute syntax (build 5320+)
tags: [input, optimizer, build5320]
applicable_phase: A
---

# input attribute syntax (build 5320+)

Build 5320 (Sep 2025) extended MQL5's `input` declaration so each
input can carry **attributes** that the Strategy Tester / Optimiser
consume directly — display name, min/max/step bounds, group label,
tooltip — without a separate `.set` file dance.

## Legacy form (every build)

```mql5
input int    InpSlPips         = 30;
input double InpRiskPerTradePct = 0.5;
```

The optimiser surfaces these by variable name; bounds and steps live
in the `.set` file alongside the EA.

## Attribute form (build 5320+)

```mql5
input group "Risk"
input(name="Stop-loss (pips)", min=10, max=200, step=5,
      tooltip="Distance to protective SL in pips, pip-normalised")
   int InpSlPips = 30;

input(name="Risk %", min=0.1, max=2.0, step=0.1, optimisable=true)
   double InpRiskPerTradePct = 0.5;
```

| Attribute | Type | Used by | Default if omitted |
|---|---|---|---|
| `name`        | `string` | Tester / Optimiser UI label | the variable identifier |
| `min`         | scalar   | optimiser range start       | platform default per type |
| `max`         | scalar   | optimiser range end         | platform default per type |
| `step`        | scalar   | optimiser step              | platform default per type |
| `tooltip`     | `string` | hover text in the Optimiser | "" |
| `optimisable` | `bool`   | include in optimisation     | `true` for scalars |
| `group`       | (via `input group "X"` line) | UI section header | "" |

## When to use which

| Situation | Recommendation |
|---|---|
| EA must compile on build < 5320 | Legacy form + `.set` |
| EA targets only build ≥ 5320     | Attribute form — single source of truth |
| `.set` file already exists and is version-controlled | Legacy form — don't fork the surface |
| Worked-example demo (this kit's `examples/`)         | Legacy form — maximises compatibility |

The kit's scaffolds default to the **legacy form** so any EA they
generate compiles on every build the kit supports (4620 → 5572).
The attribute form is recommended for *new* projects that are
willing to pin a minimum build of 5320.

## Anti-pattern hooks

- **AP-5** (`overfit_optimizer_surface_too_wide`): the 6-input cap is
  unchanged — attribute-form `optimisable=false` does *not* exempt an
  input, because the cap is about visual / mental complexity for the
  human looking at the Optimiser tab, not about what the optimiser
  is allowed to vary.
- **AP-?** *(planned)*: attribute form with `min > max` or `step <= 0`
  is a silent no-op on build 5320; the linter will flag both.
