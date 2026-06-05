//+--- ea-bugs fixture: AP-5 ---+
//| digits-tested: 5, 3 |
input int    InpFastMA  = 10;
input int    InpSlowMA  = 30;
input int    InpRsiPer  = 14;
input int    InpRsiBuy  = 30;
input int    InpRsiSell = 70;
input int    InpAtrPer  = 14;
input double InpAtrMul  = 2.0;   // 7th — BAD
input double InpRiskPct = 0.5;
void OnTick() {}
