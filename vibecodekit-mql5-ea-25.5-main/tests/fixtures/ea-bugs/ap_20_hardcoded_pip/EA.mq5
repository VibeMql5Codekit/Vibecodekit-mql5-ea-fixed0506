//+--- ea-bugs fixture: AP-20 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
input double InpSL = 30;
void OnTick() {
    double sl_dist  = InpSL * 0.0001;  // BAD — assumes 5-digit
    double sl_price = SymbolInfoDouble(_Symbol, SYMBOL_BID) - sl_dist;
    trade.Buy(0.1, _Symbol, 0, sl_price, 0);
}
