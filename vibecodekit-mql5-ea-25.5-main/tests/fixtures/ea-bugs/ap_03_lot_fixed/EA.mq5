//+--- ea-bugs fixture: AP-3 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
void OnTick() {
    double lot = 0.01;     // BAD — hardcoded
    trade.Buy(lot, _Symbol, 0, 0.95, 1.20);
}
