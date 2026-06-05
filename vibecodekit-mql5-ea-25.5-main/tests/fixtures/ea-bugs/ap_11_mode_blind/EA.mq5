//+--- ea-bugs fixture: AP-11 ---+
//| digits-tested: 5, 3 |
void OnTick() {
    // BAD — no ACCOUNT_MARGIN_MODE / SYMBOL_TRADE_MODE interrogation
    if (PositionSelect(_Symbol)) {
        Print("position open");
    }
}
