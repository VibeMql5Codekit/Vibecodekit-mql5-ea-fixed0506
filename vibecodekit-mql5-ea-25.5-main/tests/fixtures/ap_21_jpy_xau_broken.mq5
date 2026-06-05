//+------------------------------------------------------------------+
//| Fixture: AP-21 JPY-XAU-digits-assumption-broken                    |
//| /mql5-lint MUST detect this as WARN (single-class testing only).   |
//| Meta tag below indicates EA tested only on 1 broker class.         |
//+------------------------------------------------------------------+
// digits-tested: 5  (only EURUSD 5d, missing 3d/2d coverage; AP-21)

#include <Trade\Trade.mqh>

CTrade trade;

void OnTick() {
    trade.Buy(0.1, _Symbol, 0, 0, 0);
}
