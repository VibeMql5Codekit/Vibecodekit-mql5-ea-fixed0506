//+------------------------------------------------------------------+
//| Fixture: AP-3 Lot-fixed                                           |
//| /mql5-lint MUST detect this as ERROR.                             |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

CTrade trade;

void OnTick() {
    double lot = 0.01;  // BAD — hardcoded lot; AP-3 violation
    trade.Buy(lot, _Symbol, 0, 0, 1.20000);
}
