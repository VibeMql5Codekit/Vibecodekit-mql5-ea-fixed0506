"""Wave 3.E — Python in-process backtest engine.

The ``mql5-bt-sim`` CLI generates synthetic OHLC bars, runs a built-in
strategy (sma-cross / mean-rev / breakout / random), and emits an XML
report in the same schema as MetaTrader 5's Strategy Tester output.

Contract pinned here:

* Output XML parses cleanly via :func:`mql5_backtest.parse_xml_report_file`
  with PF / Sharpe / MaxDD / TotalTrades populated.
* Same ``(strategy, seed, bars)`` triple → byte-identical XML on
  re-run (deterministic).
* Different seeds → different trade counts (sensitivity sanity).
* The ``sma-cross`` strategy under default trending-drift bars
  produces a profitable backtest (PF > 1) at the seed we pin.
* The CLI ``--json`` envelope advertises ``ok=true`` and includes the
  computed metrics.
* Reproducibility under repeated CLI invocation (filesystem round-trip).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibecodekit_mql5 import backtest as backtest_mod
from vibecodekit_mql5 import bt_engine


def test_simulate_returns_consistent_triple() -> None:
    series, trades, xml = bt_engine.simulate(
        strategy="sma-cross", seed=42, bars=300
    )
    assert series.label == "sma-cross"
    assert series.total_trades == len(trades)
    assert series.total_trades == len(series.returns)
    assert xml.startswith('<?xml version="1.0" encoding="UTF-16" ?>')
    assert "<TesterReport>" in xml
    assert "<Statistics>" in xml


def test_simulate_is_deterministic_for_same_seed() -> None:
    s1, t1, x1 = bt_engine.simulate(strategy="sma-cross", seed=42, bars=300)
    s2, t2, x2 = bt_engine.simulate(strategy="sma-cross", seed=42, bars=300)
    assert s1.returns == s2.returns
    assert t1 == t2
    assert x1 == x2


def test_different_seeds_produce_different_trade_streams() -> None:
    _, t_a, _ = bt_engine.simulate(strategy="sma-cross", seed=42, bars=300)
    _, t_b, _ = bt_engine.simulate(strategy="sma-cross", seed=99, bars=300)
    # Trade lists almost certainly differ — pin a coarse inequality.
    assert t_a != t_b


@pytest.mark.parametrize("strategy", ["sma-cross", "mean-rev", "breakout", "random"])
def test_emitted_xml_parses_via_mt5_parser_unchanged(
    tmp_path: Path, strategy: str
) -> None:
    """The emitted XML must round-trip through the production parser."""
    out = tmp_path / f"bt-{strategy}.xml"
    rc = bt_engine.main([
        "--strategy", strategy,
        "--bars", "400",
        "--seed", "42",
        "--out", str(out),
    ])
    assert rc == 0
    assert out.is_file()
    result = backtest_mod.parse_xml_report_file(out)
    # The XML schema fields the parser cares about must all populate.
    assert result.symbol == "EURUSD"
    assert result.period == "H1"
    assert result.total_trades >= 0
    # Statistics section was present + parsed.
    assert isinstance(result.profit_factor, float)
    assert isinstance(result.sharpe, float)
    assert isinstance(result.max_drawdown_pct, float)


def test_sma_cross_strategy_has_positive_edge_under_drift() -> None:
    """The default bar synth gives ``sma-cross`` an up-drift; under
    seed=42 it must produce a profitable backtest (PF > 1.0)."""
    series, _, _ = bt_engine.simulate(strategy="sma-cross", seed=42, bars=500)
    assert series.total_trades > 0
    assert series.profit_factor > 1.0


def test_breakout_strategy_engages_under_trending_bars() -> None:
    """``breakout`` should also fire trades on the trending-drift bars."""
    _, trades, _ = bt_engine.simulate(strategy="breakout", seed=42, bars=500)
    assert len(trades) > 0


def test_random_strategy_no_edge() -> None:
    """Sanity: the dumb-baseline ``random`` strategy is a coin-flip;
    its PF on average sits near 1.0. We pin only that it runs and
    produces a non-empty trade series so the CI evidence-trail
    captures the dud-strategy case too.
    """
    series, trades, _ = bt_engine.simulate(strategy="random", seed=42, bars=600)
    assert len(trades) > 0
    assert isinstance(series.profit_factor, float)


def test_cli_emit_json_envelope_smoke(tmp_path: Path) -> None:
    """``mql5-bt-sim --json`` produces a valid envelope on stdout."""
    out = tmp_path / "bt.xml"
    proc = subprocess.run(
        [
            sys.executable, "-m", "vibecodekit_mql5.bt_engine",
            "--strategy", "sma-cross",
            "--bars", "300",
            "--seed", "42",
            "--out", str(out),
            "--json",
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["tool"] == "mql5-bt-sim"
    assert envelope["ok"] is True
    assert envelope["exit_code"] == 0
    data = envelope["data"]
    assert data["strategy"] == "sma-cross"
    assert data["seed"] == 42
    assert data["bars"] == 300
    assert data["trade_count"] >= 0
    assert data["xml_path"] == str(out)
    assert out.is_file()


def test_cli_gate_report_written(tmp_path: Path) -> None:
    """``--gate-report`` writes the envelope to the supplied path."""
    out = tmp_path / "bt.xml"
    report = tmp_path / "bt-gate.json"
    rc = bt_engine.main([
        "--strategy", "sma-cross",
        "--bars", "300",
        "--seed", "42",
        "--out", str(out),
        "--gate-report", str(report),
    ])
    assert rc == 0
    assert report.is_file()
    envelope = json.loads(report.read_text(encoding="utf-8"))
    assert envelope["tool"] == "mql5-bt-sim"


def test_returns_csv_optional_emission(tmp_path: Path) -> None:
    """``--returns-csv`` emits a parallel CSV alongside the XML."""
    out_xml = tmp_path / "bt.xml"
    out_csv = tmp_path / "bt.csv"
    rc = bt_engine.main([
        "--strategy", "mean-rev",
        "--bars", "300",
        "--seed", "42",
        "--out", str(out_xml),
        "--returns-csv", str(out_csv),
    ])
    assert rc == 0
    text = out_csv.read_text(encoding="utf-8")
    # First line is the header; remaining lines are per-trade returns.
    lines = text.strip().splitlines()
    assert lines[0] == "return"
    assert len(lines) >= 2  # header + ≥1 trade


def test_cli_writes_xml_byte_identical_across_runs(tmp_path: Path) -> None:
    """Re-running the CLI with the same args produces byte-identical XML."""
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    args = ["--strategy", "sma-cross", "--bars", "300", "--seed", "7"]
    rc_a = bt_engine.main(args + ["--out", str(a)])
    rc_b = bt_engine.main(args + ["--out", str(b)])
    assert rc_a == rc_b == 0
    assert a.read_bytes() == b.read_bytes()
