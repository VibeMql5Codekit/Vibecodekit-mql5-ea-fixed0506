"""Phase B — backtest XML parser + tester.ini gen + period parser (8 tests)."""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5.backtest import (
    parse_xml_report,
    parse_xml_report_file,
    parse_period,
    render_tester_ini,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


# ── XML parser ──────────────────────────────────────────────────────────────

def test_parse_xml_full_eurusd():
    r = parse_xml_report_file(FIXTURES / "tester_report_eurusd_h1.xml")
    assert r.symbol == "EURUSD"
    assert r.period == "H1"
    assert r.profit_factor == 1.78
    assert r.sharpe == 0.42
    assert r.total_trades == 342
    assert r.mfe_correlation == 0.65


def test_parse_xml_minimal_usdjpy():
    """USDJPY fixture has only a subset of fields; missing ones default to 0."""
    r = parse_xml_report_file(FIXTURES / "tester_report_usdjpy_h1.xml")
    assert r.symbol == "USDJPY"
    assert r.profit_factor == 1.61
    assert r.broker_digits == 3
    assert r.expected_payoff == 0.0    # not in fixture
    assert r.lr_correlation == 0.0     # not in fixture


def test_parse_xml_xauusd_3d():
    r = parse_xml_report_file(FIXTURES / "tester_report_xauusd_h1_3d.xml")
    assert r.symbol == "XAUUSD"
    assert r.broker_digits == 3
    assert r.max_drawdown_pct == 8.5


def test_parse_xml_handles_malformed_floats():
    """Non-numeric values must not crash the parser."""
    bad = (
        '<?xml version="1.0"?>\n'
        '<TesterReport><Symbol>X</Symbol>'
        '<Statistics><ProfitFactor>NOT_A_NUMBER</ProfitFactor></Statistics>'
        '</TesterReport>'
    )
    r = parse_xml_report(bad)
    assert r.symbol == "X"
    assert r.profit_factor == 0.0


# ── tester.ini generator ────────────────────────────────────────────────────

def test_render_tester_ini_contains_required_keys():
    ini = render_tester_ini(
        ea_path="Z:\\ea.ex5", set_path="Z:\\set.set",
        symbol="EURUSD", period="H1",
        from_date="2023.01.01", to_date="2024.12.31",
    )
    for k in ("[Tester]", "Expert=Z:\\ea.ex5", "Symbol=EURUSD",
              "FromDate=2023.01.01", "ToDate=2024.12.31",
              "Report=tester.xml", "ShutdownTerminal=1"):
        assert k in ini, f"missing {k!r} in tester.ini:\n{ini}"


def test_render_tester_ini_forward_mode_param():
    ini = render_tester_ini(
        ea_path="x", set_path="y", symbol="EURUSD", period="H1",
        from_date="2023.01.01", to_date="2024.12.31",
        forward_mode=3,
    )
    assert "ForwardMode=3" in ini


# ── period parser ──────────────────────────────────────────────────────────

def test_parse_period_accepts_dotted_and_compact():
    assert parse_period("2023.01.01-2024.12.31") == ("2023.01.01", "2024.12.31")
    assert parse_period("20230101-20241231")     == ("2023.01.01", "2024.12.31")


def test_parse_period_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_period("not-a-range")
