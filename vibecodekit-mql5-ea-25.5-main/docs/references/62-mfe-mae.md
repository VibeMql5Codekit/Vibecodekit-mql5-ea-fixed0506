---
id: 62-mfe-mae
title: MFE / MAE per-trade
tags: [mfe, mae, observability]
applicable_phase: B
---

# MFE / MAE per-trade

Maximum Favourable Excursion (MFE) is the highest unrealised profit
during a trade; Maximum Adverse Excursion (MAE) is the deepest
unrealised loss. The ratio `MFE / |MAE|` approximates the
"left-on-the-table" coefficient — values consistently > 2 typically
signal a too-tight take-profit (or a chronic late exit).

## Runtime — `CMfeMaeLogger.mqh`

`Include/CMfeMaeLogger.mqh` snapshots MFE/MAE on every tick for every
open position keyed by ticket, then writes one CSV row per trade close.
The file lands under `FILE_COMMON` so a VPS migration carries it
across automatically.

Usage in an EA:

```mql5
#include <CMfeMaeLogger.mqh>

CMfeMaeLogger mfemae;

int OnInit(void)
  { return mfemae.Init("mfe_mae_" + (string)InpMagic + ".csv") ? INIT_SUCCEEDED : INIT_FAILED; }

void OnTick(void)              { mfemae.OnTick(); }
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &req,
                        const MqlTradeResult  &res)
  { mfemae.OnTradeTransaction(trans); }
```

## CSV schema

The header is written exactly once on file creation; subsequent EA
restarts append without rewriting:

```
deal_id,open_time,close_time,magic,type,profit,mfe,mae
```

| Field | Type | Notes |
|---|---|---|
| `deal_id`    | `ulong`  | `HistoryDealGetInteger(..., DEAL_TICKET)` of the closing deal |
| `open_time`  | ISO-8601 | server time of the entry deal |
| `close_time` | ISO-8601 | server time of the exit deal |
| `magic`      | `ulong`  | EA magic number — split-by-EA in downstream analysis |
| `type`       | `string` | `BUY` / `SELL` |
| `profit`     | `double` | realised PnL in account currency |
| `mfe`        | `double` | best unrealised profit reached while open (account currency) |
| `mae`        | `double` | worst unrealised loss reached while open (account currency) |

## Analyzer — `mql5-mfe-mae`

`scripts/vibecodekit_mql5/mfe_mae.py` reads the CSV and emits Pearson
correlation of MFE vs realised profit and MAE vs realised profit:

```bash
python -m vibecodekit_mql5.mfe_mae Common/Files/mfe_mae_5001.csv
```

```json
{
  "n_trades": 142,
  "mean_mfe": 18.4,
  "mean_mae": -7.2,
  "mfe_profit_corr": 0.71,
  "mae_profit_corr": -0.34
}
```

- A high `mfe_profit_corr` (≥ 0.7) means TP is well-calibrated.
- A near-zero `mae_profit_corr` means SL is rarely the binding
  constraint — fine for trend EAs, suspect for mean-reversion.
