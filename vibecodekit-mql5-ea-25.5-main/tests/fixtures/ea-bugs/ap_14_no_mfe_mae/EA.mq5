//+--- ea-bugs fixture: AP-14 ---+
//| digits-tested: 5, 3 |
#include <Trade\Trade.mqh>
CTrade trade;
void OnTick() {
    // BAD — no MFE/MAE logger included
    trade.Buy(0.1, _Symbol, 0, 0.95, 1.20);
    if (trade.ResultRetcode() == TRADE_RETCODE_DONE) {}
}
