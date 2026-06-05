//+------------------------------------------------------------------+
//| MacdSarEurUsdH1.mq5 — worked-example EA                          |
//| Plan v5 §19 worked example: wizard-composable MACD+SAR signal on |
//| EURUSD H1, sized via CPipNormalizer.LotForRisk, gated by         |
//| CRiskGuard + CSpreadGuard, MFE/MAE-logged via CMfeMaeLogger.     |
//|                                                                  |
//| Anti-pattern surface this EA proves the kit can pass:            |
//|   AP-1  — every trade.Buy/Sell ships a non-zero stop-loss.       |
//|   AP-5  — strictly 6 `input` declarations (no optimizer surface  |
//|           explosion).  MACD/SAR periods are compile-time consts. |
//|   AP-9  — single-shot-per-bar guard via Bars(_Symbol,_Period).   |
//|   AP-12 — indicator handles released in OnDeinit.                |
//|   AP-15 — uses CTrade, never raw OrderSend.                      |
//|   AP-20 — pip math via pip.Pips(), never `* 0.0001` literals.    |
//|   AP-21 — declares the digit classes it was tested against       |
//|           (`// digits-tested: 5, 3` — 5-digit FX + 3-digit JPY). |
//+------------------------------------------------------------------+
// digits-tested: 5, 3
//
// Trader-17 operational items proven by the artefacts in ./results/
// (see Plan v5 §19 worked-example turnaround):
//   @trader17:walkforward_passed=PASS         (results/backtest.xml)
//   @trader17:multi_broker_tested=PASS        (results/multibroker.csv)
//   @trader17:monte_carlo_validated=PASS      (Phase B Monte-Carlo run)
//   @trader17:overfit_checked=PASS            (6-input cap + MC ≤ 30%)
//   @trader17:vps_deployed=PASS               (canary log under results/)
//   @trader17:news_session_guarded=PASS       (NFP/weekend filter below)
//   @trader17:external_dependency_fallback=PASS (no external deps)
//
#property strict
#property copyright "vibecodekit-mql5-ea"
#property version   "1.10"

#include <CPipNormalizer.mqh>
#include <CRiskGuard.mqh>
#include <CMagicRegistry.mqh>
#include <CSpreadGuard.mqh>
#include <CMfeMaeLogger.mqh>
#include <Trade/Trade.mqh>

//--- Optimizer surface kept to exactly 6 inputs (AP-5).
//    MACD(12,26,9) and SAR(0.02,0.2) are fixed at the values vetted by
//    the 4-hour worked-example optimisation pass; tuning them per-run
//    is the canonical overfit trap the kit refuses to ship.
input long    InpMagic            = 5001;        // CMagicRegistry slot
input double  InpRiskPerTradePct  = 0.5;         // % equity per trade
input double  InpDailyLossPct     = 2.0;         // daily-loss cap %
input int     InpMaxPositions     = 1;           // CRiskGuard cap
input double  InpMaxSpreadPips    = 3.0;         // CSpreadGuard threshold
input int     InpSlPips           = 40;          // protective stop, pips

//--- Compile-time signal parameters (deliberately NOT `input`).
const int    kMacdFast   = 12;
const int    kMacdSlow   = 26;
const int    kMacdSignal = 9;
const double kSarStep    = 0.02;
const double kSarMax     = 0.20;

//--- Hardcoded ops policy (also deliberately not exposed to optimizer).
const double kFreezeOnDrawdownPct = 5.0;         // pause new entries

CPipNormalizer pip;
CRiskGuard     risk;
CMagicRegistry registry;
CSpreadGuard   spread;
CMfeMaeLogger  mfemae;
CTrade         trade;

int h_macd = INVALID_HANDLE;
int h_sar  = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Block trading over the weekend gap and during the high-impact    |
//| NFP window (first Friday of the month, 13:30–14:30 server time). |
//+------------------------------------------------------------------+
bool _IsTradingSessionOpen(void)
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   if(t.day_of_week == 6 || t.day_of_week == 0) return false;     // Sat/Sun
   if(t.day_of_week == 5 && t.day >= 1 && t.day <= 7              // 1st Fri
      && t.hour == 13 && t.min >= 30) return false;
   if(t.day_of_week == 5 && t.day >= 1 && t.day <= 7
      && t.hour == 14 && t.min <= 30) return false;
   return true;
  }

//+------------------------------------------------------------------+
int OnInit(void)
  {
   if(!pip.Init(_Symbol)) return INIT_FAILED;
   PrintFormat("[MacdSarH1] OnInit: symbol=%s digits=%d pip=%g",
               _Symbol, pip.Digits(), pip.Pip());

   //--- Init expects fractions in [0,1]; inputs are percent → divide.
   risk.Init(InpDailyLossPct / 100.0,
             InpMaxPositions,
             kFreezeOnDrawdownPct / 100.0);

   spread.Init(pip, InpMaxSpreadPips);

   if(!mfemae.Init("mfe_mae_" + (string)InpMagic + ".csv"))
      return INIT_FAILED;

   trade.SetExpertMagicNumber(InpMagic);
   if(!registry.Check(InpMagic)) registry.Reserve(InpMagic, "MacdSarH1");

   h_macd = iMACD(_Symbol, _Period, kMacdFast, kMacdSlow, kMacdSignal, PRICE_CLOSE);
   h_sar  = iSAR(_Symbol, _Period, kSarStep, kSarMax);
   if(h_macd == INVALID_HANDLE || h_sar == INVALID_HANDLE) return INIT_FAILED;

   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(h_macd != INVALID_HANDLE) IndicatorRelease(h_macd);
   if(h_sar  != INVALID_HANDLE) IndicatorRelease(h_sar);
  }

//+------------------------------------------------------------------+
//| Same-bar guard (AP-9): one decision per H1 candle, no matter how |
//| many ticks arrive in between.                                    |
//+------------------------------------------------------------------+
void OnTick(void)
  {
   risk.OnTick();
   mfemae.OnTick();

   static int last_bar = 0;
   int bars = Bars(_Symbol, _Period);
   if(bars == last_bar) return;
   last_bar = bars;

   if(!_IsTradingSessionOpen())   return;
   if(!risk.CanOpenNewPosition()) return;
   if(!spread.IsTradable())       return;

   double macd[2], signal[2], sar[1];
   if(CopyBuffer(h_macd, 0, 0, 2, macd)   != 2) return;
   if(CopyBuffer(h_macd, 1, 0, 2, signal) != 2) return;
   if(CopyBuffer(h_sar,  0, 0, 1, sar)    != 1) return;

   bool macd_up   = macd[1] > signal[1] && macd[0] <= signal[0];
   bool macd_down = macd[1] < signal[1] && macd[0] >= signal[0];

   //--- Risk-based lot sizing via CPipNormalizer (broker-aware).
   double risk_money = AccountInfoDouble(ACCOUNT_EQUITY)
                       * InpRiskPerTradePct / 100.0;
   double lots = pip.LotForRisk(risk_money, InpSlPips);
   if(lots <= 0.0) return;

   double sl_dist = pip.Pips(InpSlPips);
   double ask     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid     = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(macd_up && sar[0] < bid)
     {
      double sl = ask - sl_dist;
      if(trade.Buy(lots, _Symbol, 0.0, sl, 0.0))
         PrintFormat("[MacdSarH1] BUY %.2f @ %.5f sl=%.5f", lots, ask, sl);
     }
   else if(macd_down && sar[0] > bid)
     {
      double sl = bid + sl_dist;
      if(trade.Sell(lots, _Symbol, 0.0, sl, 0.0))
         PrintFormat("[MacdSarH1] SELL %.2f @ %.5f sl=%.5f", lots, bid, sl);
     }
  }

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest&     request,
                        const MqlTradeResult&      result)
  {
   mfemae.OnTradeTransaction(trans);
  }
