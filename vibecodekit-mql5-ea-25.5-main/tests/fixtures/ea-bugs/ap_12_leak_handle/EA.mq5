//+--- ea-bugs fixture: AP-12 ---+
//| digits-tested: 5, 3 |
int atr_handle = INVALID_HANDLE;
void OnInit() {
    atr_handle = iATR(_Symbol, _Period, 14);  // BAD — no Release
}
void OnTick() {}
