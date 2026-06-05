//+--- ea-bugs fixture: AP-8 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
void OnTick() {
    // BAD — no SYMBOL_SPREAD or CSpreadGuard check
    trade.Buy(0.1, _Symbol, 0, 0.95, 1.20);
}
