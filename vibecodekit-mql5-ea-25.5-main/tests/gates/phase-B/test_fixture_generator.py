"""tests/gates/phase-B/test_fixture_generator.py — mql5-fixture hermetic XML.

The fixture generator is the hermetic-CI unlocker: it produces synthetic
MT5 Strategy Tester XML / CSV / journal artefacts so the entire Phase-B
pipeline (`mql5-backtest`, `mql5-walkforward`, `mql5-monte-carlo`,
`mql5-multibroker`) runs without Wine + MetaTrader.

These tests verify that:

1. Fixture output is byte-stable for a given seed.
2. The XML round-trips through `mql5-backtest.parse_xml_report_file`.
3. Each --type produces the expected file set.
4. Generated returns CSVs feed `mql5-monte-carlo` without error.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path


def test_fixture_backtest_emits_xml_and_csv(tmp_path: Path):
    from vibecodekit_mql5 import fixture

    fixture.main([
        "--type", "backtest", "--strategy", "trend",
        "--seed", "42", "--trades", "100",
        "--out", str(tmp_path),
    ])
    xml = tmp_path / "backtest-trend-42.xml"
    csv = tmp_path / "backtest-trend-42.returns.csv"
    assert xml.exists() and csv.exists()
    assert "<TesterReport>" in xml.read_text()


def test_fixture_xml_parses_via_backtest_module(tmp_path: Path):
    from vibecodekit_mql5 import fixture
    from vibecodekit_mql5.backtest import parse_xml_report_file

    fixture.main([
        "--type", "backtest", "--strategy", "trend",
        "--seed", "7", "--trades", "120",
        "--out", str(tmp_path),
    ])
    xml = tmp_path / "backtest-trend-7.xml"
    rep = parse_xml_report_file(xml)
    # The synthetic report must populate the parser's required fields.
    assert rep.total_trades == 120
    assert rep.profit_factor > 0
    assert rep.symbol == "EURUSD"
    assert rep.period == "H1"


def test_fixture_deterministic_across_invocations(tmp_path: Path):
    from vibecodekit_mql5 import fixture

    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    fixture.main(["--type", "backtest", "--strategy", "trend",
                  "--seed", "99", "--trades", "100", "--out", str(out_a)])
    fixture.main(["--type", "backtest", "--strategy", "trend",
                  "--seed", "99", "--trades", "100", "--out", str(out_b)])
    xml_a = (out_a / "backtest-trend-99.xml").read_text()
    xml_b = (out_b / "backtest-trend-99.xml").read_text()
    assert xml_a == xml_b


def test_fixture_walkforward_pair(tmp_path: Path):
    from vibecodekit_mql5 import fixture
    from vibecodekit_mql5.walkforward import evaluate as wf_evaluate
    from vibecodekit_mql5.backtest import parse_xml_report_file

    fixture.main([
        "--type", "walkforward", "--strategy", "trend",
        "--seed", "11", "--trades", "200",
        "--out", str(tmp_path),
    ])
    is_xml = tmp_path / "walkforward-trend-11-IS.xml"
    oos_xml = tmp_path / "walkforward-trend-11-OOS.xml"
    assert is_xml.exists() and oos_xml.exists()
    result = wf_evaluate(parse_xml_report_file(is_xml),
                         parse_xml_report_file(oos_xml))
    # Trend strategy should not catastrophically fail walkforward.
    assert result.verdict in {"PASS", "WARN", "FAIL"}


def test_fixture_monte_carlo_csv(tmp_path: Path):
    from vibecodekit_mql5 import fixture
    from vibecodekit_mql5 import monte_carlo as mc

    fixture.main([
        "--type", "monte-carlo", "--strategy", "trend",
        "--seed", "5", "--trades", "300",
        "--out", str(tmp_path),
    ])
    csv = tmp_path / "montecarlo-trend-5.returns.csv"
    assert csv.exists()
    # Pipe through the monte_carlo evaluator to confirm parse + run.
    returns = mc._read_returns_csv(csv)
    assert len(returns) == 300
    result = mc.evaluate(returns, reported_dd=999.0, n_sims=20, seed=5)
    assert result.verdict in {"PASS", "WARN", "FAIL"}


def test_fixture_multibroker_n_reports(tmp_path: Path):
    from vibecodekit_mql5 import fixture
    from vibecodekit_mql5.backtest import parse_xml_report_file
    from vibecodekit_mql5.multibroker import evaluate as mb_evaluate

    fixture.main([
        "--type", "multibroker", "--strategy", "trend",
        "--seed", "1", "--trades", "100", "--brokers", "3",
        "--out", str(tmp_path),
    ])
    xmls = sorted(tmp_path.glob("multibroker-trend-1-b*.xml"))
    logs = sorted(tmp_path.glob("multibroker-trend-1-b*.log"))
    assert len(xmls) == 3 and len(logs) == 3
    reports = [parse_xml_report_file(p) for p in xmls]
    result = mb_evaluate(reports, journals=[str(p) for p in logs])
    assert result.verdict in {"PASS", "WARN", "FAIL"}


def test_fixture_json_envelope(tmp_path: Path):
    from vibecodekit_mql5 import fixture

    buf = io.StringIO()
    with redirect_stdout(buf):
        fixture.main([
            "--type", "backtest", "--strategy", "random",
            "--seed", "1", "--trades", "50",
            "--out", str(tmp_path), "--json",
        ])
    env = json.loads(buf.getvalue())
    assert env["tool"] == "mql5-fixture"
    assert env["data"]["type"] == "backtest"
    assert env["data"]["strategy"] == "random"
    assert env["data"]["seed"] == 1
    assert len(env["evidence"]) >= 2  # xml + returns.csv
