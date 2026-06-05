"""Phase E unit tests — canary observability."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from vibecodekit_mql5 import canary  # noqa: E402


def test_canary_no_alerts_on_clean_journal() -> None:
    lines = ["INFO ok"] * 20
    rep = canary.analyse_journal(lines, duration_s=600.0)
    assert rep.alerts == []


def test_canary_error_rate_alert() -> None:
    # 5 errors in 60s = 5/min → above 1.0/min threshold.
    lines = ["ERROR fail"] * 5
    rep = canary.analyse_journal(lines, duration_s=60.0)
    assert any("error_rate" in a for a in rep.alerts)


def test_canary_drawdown_alert() -> None:
    lines = ["INFO drawdown 6.5 %"]
    rep = canary.analyse_journal(lines, duration_s=60.0)
    assert any("drawdown" in a for a in rep.alerts)


def test_canary_duration_parser() -> None:
    assert canary._parse_duration("30m") == 1800.0
    assert canary._parse_duration("1h") == 3600.0
    assert canary._parse_duration("45s") == 45.0
