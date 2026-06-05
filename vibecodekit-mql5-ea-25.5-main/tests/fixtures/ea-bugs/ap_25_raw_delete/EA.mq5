//+--- ea-bugs fixture: AP-25 ---+
//| digits-tested: 5, 3 |
class CMyObj { public: int x; };
CMyObj *ptr = NULL;
void OnDeinit(const int reason) {
    delete ptr;   // BAD — no CheckPointer guard
}
void OnTick() {}
