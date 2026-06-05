//+--- ea-bugs fixture: AP-10 ---+
//| digits-tested: 5, 3 |
void OnTick() {
    MqlTradeRequest req = {};
    MqlTradeResult  res = {};
    OrderSend(req, res);   // BAD — no retcode inspection
}
