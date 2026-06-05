"""Phase D method-hiding linter unit tests — 3 cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5 import method_hiding_check as mhc

SAMPLE_HIDING = """\
class Base
  {
public:
   virtual void Run(int x) {}
   virtual int  Compute(double v) { return 0; }
  };

class Derived : public Base
  {
public:
   void Run(int x) {}              // hides Base::Run
   int  Compute(double v) { return 1; }  // hides Base::Compute
  };
"""

SAMPLE_USING_OK = """\
class Base { public: virtual void Run(int x) {} };

class Derived : public Base
  {
public:
   using Base::Run;
   void Run(int x) {}
  };
"""

SAMPLE_PRAGMA_OK = """\
class Base { public: virtual void Run(int x) {} };

class Derived : public Base
  {
public:
   // vck-mql5: hiding-ok
   void Run(int x) {}
  };
"""


def test_build_below_5260_warns(tmp_path: Path) -> None:
    p = tmp_path / "h.mq5"
    p.write_text(SAMPLE_HIDING, encoding="utf-8")
    rep = mhc.check_method_hiding(p, target_build=5200)
    assert rep.ok            # WARN does not fail the gate
    assert rep.issues, "expected issues to be flagged"
    assert all(i.severity == "WARN" for i in rep.issues)


def test_build_at_or_above_5260_errors(tmp_path: Path) -> None:
    p = tmp_path / "h.mq5"
    p.write_text(SAMPLE_HIDING, encoding="utf-8")
    rep = mhc.check_method_hiding(p, target_build=5260)
    assert not rep.ok
    assert rep.issues
    assert any(i.severity == "ERROR" for i in rep.issues)
    assert any(i.method in {"Run", "Compute"} for i in rep.issues)


@pytest.mark.parametrize("sample", [SAMPLE_USING_OK, SAMPLE_PRAGMA_OK])
def test_explicit_opt_out_clears_lint(tmp_path: Path, sample: str) -> None:
    p = tmp_path / "ok.mq5"
    p.write_text(sample, encoding="utf-8")
    rep = mhc.check_method_hiding(p, target_build=5260)
    assert rep.ok
    assert not rep.issues
