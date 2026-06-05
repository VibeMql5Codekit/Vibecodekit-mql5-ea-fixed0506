//+------------------------------------------------------------------+
//| Fixture: AP-1 No-SL                                               |
//| /mql5-lint MUST detect this as ERROR.                             |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

CTrade trade;

void OnTick() {
    // BAD — no SL set; AP-1 violation
    trade.Buy(0.1, _Symbol);
}
