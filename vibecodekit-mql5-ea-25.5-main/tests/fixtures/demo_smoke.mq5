//+------------------------------------------------------------------+
//| Demo smoke test — Phase 0 verification                            |
//| Compiles successfully with MetaEditor (any build).                |
//+------------------------------------------------------------------+
#property version   "1.00"
#property strict
#property description "Phase 0 bootstrap smoke fixture"

void OnInit()  { Print("vibecodekit-mql5-ea bootstrap OK"); }
void OnTick()  { /* no-op */ }
void OnDeinit(const int reason) { /* no-op */ }
