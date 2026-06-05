"""Tests for the W2.1 `mql5-init` 5-question bootstrap wizard."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibecodekit_mql5 import build as build_mod
from vibecodekit_mql5 import init as init_mod
from vibecodekit_mql5.init import (
    Answers,
    _normalise_preset,
    _normalise_symbol,
    _normalise_timeframe,
    _sanitise_name,
    collect_interactive,
    load_answers_file,
    main,
)


# --------------------------------------------------------------------------
# Pure-function helpers
# --------------------------------------------------------------------------

def test_sanitise_name_strips_invalid_chars():
    assert _sanitise_name("My EA-1.0!") == "MyEA-10!".replace("-", "").replace("!", "")
    # Trailing/leading whitespace and dots collapsed.
    assert _sanitise_name(" hello world ") == "helloworld"
    # Empty input falls back to default.
    assert _sanitise_name("") == "MyEA"
    # Digit-leading names get an EA_ prefix so MetaEditor accepts them.
    assert _sanitise_name("123abc").startswith("EA_")


@pytest.mark.parametrize("raw,expected", [
    ("mean-rev", "mean-reversion"),
    ("MeanRev", "mean-reversion"),
    ("scalp", "scalping"),
    ("hft", "hft-async"),
    ("ML", "ml-onnx"),
    ("onnx", "ml-onnx"),
    ("trend", "trend"),
])
def test_normalise_preset_aliases(raw, expected):
    assert _normalise_preset(raw) == expected


def test_normalise_symbol_uppercases():
    assert _normalise_symbol("eurusd") == "EURUSD"
    assert _normalise_symbol("  xauusd ") == "XAUUSD"


def test_normalise_timeframe_strips_suffix():
    assert _normalise_timeframe("h1") == "H1"
    assert _normalise_timeframe("m15") == "M15"
    # Bare "MN" is upgraded to "MN1" so it round-trips through MT5.
    assert _normalise_timeframe("mn") == "MN1"


def test_normalise_timeframe_preserves_canonical_mn1():
    """Regression: ``.replace("MN", "MN1")`` used to corrupt ``MN1`` into
    ``MN11`` by matching the embedded ``MN`` substring. Both lower- and
    upper-case inputs must round-trip cleanly to ``MN1``."""

    assert _normalise_timeframe("MN1") == "MN1"
    assert _normalise_timeframe("mn1") == "MN1"
    assert _normalise_timeframe(" MN1 ") == "MN1"


def test_normalise_timeframe_canonical_day_and_week_pass_through():
    """``D1`` and ``W1`` must survive normalisation untouched."""

    assert _normalise_timeframe("d1") == "D1"
    assert _normalise_timeframe("W1") == "W1"


# --------------------------------------------------------------------------
# Wizard wiring
# --------------------------------------------------------------------------

def test_collect_interactive_uses_defaults_on_empty_input():
    """Pressing Enter on every prompt yields the documented defaults."""

    stdin = io.StringIO("\n\n\n\n\n")
    stderr = io.StringIO()
    ans = collect_interactive(stream_in=stdin, stream_out=stderr)
    assert ans.name == "MyEA"
    assert ans.preset == "trend"
    assert ans.stack == "netting"
    assert ans.symbol == "EURUSD"
    assert ans.timeframe == "H1"
    assert ans.risk_per_trade_pct == 0.5
    # Spec round-trips through the real validator.
    spec = ans.to_spec()
    from vibecodekit_mql5 import spec_schema
    spec_schema.validate(spec, valid_presets=build_mod.PRESETS)


def test_collect_interactive_typed_answers():
    """Typed answers override the defaults and survive normalisation."""

    stdin = io.StringIO(
        "Scalper-1\n"           # 1) name (gets sanitised)
        "scalp\n"               # 2) preset (alias → scalping)
        "hedging\n"             # 3) stack
        "XAUUSD M15\n"          # 4) symbol+tf
        "0.25\n"                # 5) risk
    )
    stderr = io.StringIO()
    ans = collect_interactive(stream_in=stdin, stream_out=stderr)
    assert ans.name == "Scalper-1".replace("-", "")
    assert ans.preset == "scalping"
    assert ans.stack == "hedging"
    assert ans.symbol == "XAUUSD"
    assert ans.timeframe == "M15"
    assert ans.risk_per_trade_pct == 0.25


def test_collect_interactive_invalid_stack_falls_back():
    """An invalid stack for the chosen preset retries once then defaults."""

    stdin = io.StringIO(
        "MyEA\n"
        "trend\n"
        "python-bridge\n"       # invalid for trend → retried
        "also-bad\n"            # still invalid → default (first allowed)
        "EURUSD H1\n"
        "0.5\n"
    )
    stderr = io.StringIO()
    ans = collect_interactive(stream_in=stdin, stream_out=stderr)
    assert ans.stack in build_mod.PRESETS[ans.preset]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_main_non_interactive_to_stdout(capsys):
    rc = main(["--non-interactive"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "name: MyEA" in out
    assert "preset: trend" in out
    assert "stack: netting" in out


def test_main_non_interactive_writes_file(tmp_path):
    out = tmp_path / "ea-spec.yaml"
    rc = main(["--non-interactive", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "preset: trend" in text


def test_main_from_answers(tmp_path):
    answers = tmp_path / "answers.yaml"
    answers.write_text(
        "name: SmokeTest\n"
        "preset: mean-rev\n"
        "stack: hedging\n"
        "symbol: usdjpy\n"
        "timeframe: m15\n"
        "risk: 0.75\n",
        encoding="utf-8",
    )
    out = tmp_path / "spec.yaml"
    rc = main(["--from-answers", str(answers), "--out", str(out)])
    assert rc == 0
    spec = out.read_text(encoding="utf-8")
    assert "name: SmokeTest" in spec
    assert "preset: mean-reversion" in spec
    assert "stack: hedging" in spec
    assert "symbol: USDJPY" in spec
    assert "timeframe: M15" in spec


def test_main_list_presets(capsys):
    rc = main(["--list-presets"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "trend" in out
    assert "stacks:" in out


def test_main_emit_json(tmp_path, capsys):
    out = tmp_path / "spec.yaml"
    rc = main(["--non-interactive", "--out", str(out), "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["schema_version"] == "1"
    assert payload["tool"] == "mql5-init"
    assert payload["ok"] is True
    assert payload["data"]["answers"]["preset"] == "trend"


def test_main_emit_json_without_out_is_pure_json(capsys):
    """Regression: when --json is supplied without --out, stdout MUST
    contain a single parseable JSON document (and nothing else). The
    previous implementation also wrote the YAML pretty-print before the
    envelope, producing output that was unparseable as either YAML or
    JSON. The spec is still recoverable via ``payload['data']['spec']``.
    """

    rc = main(["--non-interactive", "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    # Must parse as a single JSON object end-to-end (no trailing YAML).
    payload = json.loads(captured)
    assert payload["schema_version"] == "1"
    assert payload["tool"] == "mql5-init"
    assert payload["ok"] is True
    # The wizard answers + the full spec are embedded in the envelope so
    # nothing is lost by suppressing the stdout YAML write.
    assert payload["data"]["answers"]["preset"] == "trend"
    assert payload["data"]["spec"]["preset"] == "trend"
    assert payload["data"]["spec"]["risk"]["per_trade_pct"] == 0.5
    # And the YAML pretty-print MUST NOT leak alongside.
    assert "preset: trend" not in captured


def test_load_answers_file_handles_comments(tmp_path):
    p = tmp_path / "answers.yaml"
    p.write_text(
        "# leading comment\n"
        'name: "MyEA"  # inline comment\n'
        "preset: scalping\n"
        "stack: hedging\n",
        encoding="utf-8",
    )
    ans = load_answers_file(p)
    assert ans.name == "MyEA"
    assert ans.preset == "scalping"
    assert ans.stack == "hedging"


# --------------------------------------------------------------------------
# Invocation as `python -m vibecodekit_mql5.init`
# --------------------------------------------------------------------------

def test_module_invocation(tmp_path):
    """The wizard must work via `python -m vibecodekit_mql5.init`."""

    out = tmp_path / "spec.yaml"
    result = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.init",
         "--non-interactive", "--out", str(out)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    assert "preset: trend" in out.read_text(encoding="utf-8")


def test_module_exposes_defaults_dict():
    """Public DEFAULTS contract — used by external scripts to build TOML."""

    assert init_mod.DEFAULTS["preset"] == "trend"
    assert init_mod.DEFAULTS["timeframe"] == "H1"


def test_answers_to_spec_passes_validator():
    """Custom Answers always produce a schema-valid spec."""

    from vibecodekit_mql5 import spec_schema
    ans = Answers(
        name="Custom",
        preset="ml-onnx",
        stack="python-bridge",
        symbol="EURUSD",
        timeframe="H4",
        risk_per_trade_pct=1.0,
    )
    spec = ans.to_spec()
    spec_schema.validate(spec, valid_presets=build_mod.PRESETS)
    # PRESETS is the dict consulted by the validator; ensure the wizard's
    # allowed stacks come from the same place.
    assert ans.stack in build_mod.PRESETS[ans.preset]


def test_path_resolved_via_pyproject():
    """`mql5-init` must be registered in pyproject so pip-install
    `pip install -e .` creates the entry-point script."""

    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'mql5-init = "vibecodekit_mql5.init:main"' in text
