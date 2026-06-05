"""Phase E unit test — the worked example must pass the kit's own gates.

This is the regression contract from the v1.0.1 audit (W1).  Before
this gate the shipping worked example failed AP-1 (no SL), AP-5
(10 inputs declared), AP-9 (no same-bar guard) and AP-21 (no
digits-tested tag), and only earned 5/17 Trader-17 PASSes — i.e. the
canonical "build EA with the kit" demo failed the kit.

Guarantees:
  * ``mql5-lint`` produces zero ``ERROR`` findings on EAName.mq5
    (warnings allowed; only the 8 critical detectors are gated).
  * ``mql5-trader-check`` returns ≥ 15 PASS items (personal-mode
    threshold) when evaluating the source.  We deliberately keep the
    bar at 15 — the public README advertises 15/17 — so future tweaks
    that drop us to 14 trip the test.
"""

from __future__ import annotations

from pathlib import Path

from vibecodekit_mql5 import lint, trader_check

REPO_ROOT = Path(__file__).resolve().parents[3]
EA_PATH = (
    REPO_ROOT / "examples" / "ea-wizard-macd-sar-eurusd-h1-portfolio" / "EAName.mq5"
)


def _lint_findings() -> list[lint.Finding]:
    src = EA_PATH.read_text(encoding="utf-8")
    return lint.lint_source(str(EA_PATH), src)


def test_worked_example_lint_produces_no_error_severity() -> None:
    findings = _lint_findings()
    errors = [f for f in findings if f.severity == "ERROR"]
    assert errors == [], (
        "Worked example must pass the kit's own critical AP detectors; "
        f"found {len(errors)}: "
        + ", ".join(f"{f.code}@{f.line}:{f.col}" for f in errors)
    )


def test_worked_example_trader_check_personal_mode_passes() -> None:
    src = EA_PATH.read_text(encoding="utf-8")
    result = trader_check.evaluate(src)
    pass_count = sum(
        1 for k, v in result.items() if not k.startswith("_") and v == "PASS"
    )
    fail_count = sum(
        1 for k, v in result.items() if not k.startswith("_") and v == "FAIL"
    )
    assert fail_count == 0, (
        f"Worked example must have zero Trader-17 FAILs: {result}"
    )
    assert pass_count >= 15, (
        f"Worked example must hit personal-mode threshold ≥15/17; "
        f"got {pass_count}/17 — {result.get('_summary')}"
    )
    assert trader_check.verdict(result, mode="personal") is True
