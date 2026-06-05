//+--- ea-bugs fixture: AP-4 ---+
//| digits-tested: 5, 3 |
double lot = 0.01;
void OnTick() {
    if (false) {
        lot *= 2;          // BAD — no max_lot / lot_cap guard
    }
}
