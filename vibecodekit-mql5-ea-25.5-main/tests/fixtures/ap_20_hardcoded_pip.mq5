//+------------------------------------------------------------------+
//| Fixture: AP-20 Hardcoded-pip-no-broker-normalization               |
//| /mql5-lint MUST detect this as ERROR.                             |
//| /mql5-pip-normalize MUST refactor this to use CPipNormalizer.      |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

CTrade trade;

input double InpSL = 30;  // "30 pips"

void OnTick() {
    double sl_distance = InpSL * 0.0001;  // BAD — assumes EURUSD 5d only; AP-20
    double sl_price = SymbolInfoDouble(_Symbol, SYMBOL_BID) - sl_distance;
    trade.Buy(0.1, _Symbol, 0, sl_price, 0);
}
