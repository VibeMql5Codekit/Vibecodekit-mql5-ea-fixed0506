//+------------------------------------------------------------------+
//| Fixture: AP-5 Optimizer-overfitted                                |
//| Has 8 input parameters intended for excessive optimization.        |
//| Companion .set file (manually generated) would have > 100k pass.   |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

input int InpFastMA   = 10;
input int InpSlowMA   = 30;
input int InpRsiPer   = 14;
input int InpRsiBuy   = 30;
input int InpRsiSell  = 70;
input int InpAtrPer   = 14;
input double InpAtrMul = 2.0;
input int InpStochPer = 14;
input double InpRiskPct = 0.5;  // 9 inputs > 6 threshold
