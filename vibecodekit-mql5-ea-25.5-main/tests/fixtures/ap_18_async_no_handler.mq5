//+------------------------------------------------------------------+
//| Fixture: AP-18 OrderSendAsync without OnTradeTransaction handler   |
//| /mql5-lint MUST detect this as ERROR.                             |
//+------------------------------------------------------------------+
void OnTick() {
    MqlTradeRequest req = {};
    MqlTradeResult res = {};
    req.action = TRADE_ACTION_DEAL;
    req.symbol = _Symbol;
    req.volume = 0.1;
    req.type = ORDER_TYPE_BUY;
    OrderSendAsync(req, res);  // BAD — async without OnTradeTransaction; AP-18
}

// MISSING: void OnTradeTransaction(const MqlTradeTransaction&, ...) handler
