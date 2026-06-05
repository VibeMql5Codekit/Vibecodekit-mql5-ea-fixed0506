//+------------------------------------------------------------------+
//| Fixture: AP-15 Raw-OrderSend (skip CTrade)                         |
//| /mql5-lint MUST detect this as ERROR.                             |
//+------------------------------------------------------------------+
void OnTick() {
    MqlTradeRequest req = {};
    MqlTradeResult res = {};
    req.action = TRADE_ACTION_DEAL;
    req.symbol = _Symbol;
    req.volume = 0.1;
    req.type = ORDER_TYPE_BUY;
    OrderSend(req, res);  // BAD — direct OrderSend, not CTrade; AP-15
}
