//+--- ea-bugs fixture: AP-1 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
void OnTick() {
    trade.Buy(0.1, _Symbol);  // BAD — no SL
}
