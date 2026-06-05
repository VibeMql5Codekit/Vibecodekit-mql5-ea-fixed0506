//+--- ea-bugs fixture: AP-15 ---+
//| digits-tested: 5, 3 |
void OnTick() {
    MqlTradeRequest req = {};
    MqlTradeResult  res = {};
    req.action = TRADE_ACTION_DEAL;
    req.symbol = _Symbol;
    req.volume = 0.1;
    req.type   = ORDER_TYPE_BUY;
    OrderSend(req, res);   // BAD — raw OrderSend
}
