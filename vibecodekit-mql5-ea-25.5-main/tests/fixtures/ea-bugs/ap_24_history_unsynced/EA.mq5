//+--- ea-bugs fixture: AP-24 ---+
//| digits-tested: 5, 3 |
MqlRates rates[];
void OnTick() {
    CopyRates(_Symbol, _Period, 0, 10, rates);  // BAD — no sync
}
