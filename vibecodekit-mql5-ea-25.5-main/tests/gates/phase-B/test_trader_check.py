"""Phase B — trader_check 17-point checklist subset unit tests (4 tests)."""
from __future__ import annotations

from vibecodekit_mql5.trader_check import CHECKS, evaluate, verdict


_GOOD_EA = """\
// digits-tested: 5, 3
#include <CPipNormalizer.mqh>
#include <CRiskGuard.mqh>
#include <CMagicRegistry.mqh>
#include <CMfeMaeLogger.mqh>
#include <CSpreadGuard.mqh>

input double InpLot = 0.10;
input long   InpMagic = 70042;
input double InpDailyLossMaxPct = 1.0;
input double MaxSpread = 3.0;

CPipNormalizer  pip;
CRiskGuard      risk;       // DailyLoss capped via CRiskGuard.
CMagicRegistry  reg;
CMfeMaeLogger   mfe;

int OnInit()
  {
   pip.Init(_Symbol);
   reg.Reserve(InpMagic, "ea");
   double sl = pip.Pips(30);
   Print("[PipNorm] digits=", _Digits);
   // @trader17:multi_broker_tested=PASS
   // @trader17:walkforward_passed=PASS
   // @trader17:monte_carlo_validated=PASS
   // @trader17:overfit_checked=PASS
   // @trader17:news_session_guarded=PASS
   // @trader17:external_dependency_fallback=PASS
   // @trader17:vps_deployed=PASS
   // @trader17:llm_fallback_defined=PASS
   return INIT_SUCCEEDED;
  }
"""

_BAD_EA = """\
input double InpLot = 0.01;
void OnTick()
  {
   double sl = 30 * 0.0001;
   trade.Buy(0.01);   // no SL
  }
"""


def test_checks_list_is_seventeen():
    assert len(CHECKS) == 17


def test_evaluate_good_ea_passes_threshold():
    r = evaluate(_GOOD_EA)
    assert verdict(r, mode="personal") is True
    assert r["sl_set_every_trade"] == "PASS"
    assert r["pip_normalized_via_kit"] == "PASS"
    assert r["pip_normalized_across_brokers"] == "PASS"


def test_evaluate_bad_ea_fails_on_sl_and_pip():
    r = evaluate(_BAD_EA)
    assert r["sl_set_every_trade"] == "FAIL"
    assert r["pip_normalized_via_kit"] == "FAIL"
    assert verdict(r, mode="personal") is False


def test_summary_counts_present():
    r = evaluate(_GOOD_EA)
    assert "_summary" in r
    assert "PASS" in r["_summary"]
