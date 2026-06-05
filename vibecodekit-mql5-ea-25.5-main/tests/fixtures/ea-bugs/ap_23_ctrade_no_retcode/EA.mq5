//+--- ea-bugs fixture: AP-23 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
void OnTick() {
    trade.Buy(0.1, _Symbol, 0, 0.95, 1.20);  // BAD — no retcode
    Print("traded");
}
