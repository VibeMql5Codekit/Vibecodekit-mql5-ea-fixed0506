"""Phase E gate — natural-language → ``ea-spec.yaml`` parser (P2.2).

The Devin chat-driven build playbook calls ``mql5-spec-from-prompt`` with a
single English/Vietnamese sentence and feeds the resulting YAML straight
into ``mql5-auto-build``. These tests pin the parser's behaviour on the
prompt phrasings the playbook is expected to handle, and prove the output
round-trips through ``spec_schema.validate`` and the auto-build orchestrator.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vibecodekit_mql5 import build as build_mod
from vibecodekit_mql5 import spec_schema
from vibecodekit_mql5 import spec_from_prompt
from vibecodekit_mql5.spec_from_prompt import parse, to_yaml


# ─────────────────────────────────────────────────────────────────────────────
# Per-prompt smoke matrix — every entry must validate
# ─────────────────────────────────────────────────────────────────────────────

PROMPTS_VALID: tuple[tuple[str, dict[str, object]], ...] = (
    (
        "build EA trend EURUSD H1 risk 0.5%",
        {"preset": "trend", "stack": "netting", "symbol": "EURUSD",
         "timeframe": "H1"},
    ),
    (
        "scalping XAUUSD M5 risk 1% SL 30 TP 60 macd",
        {"preset": "scalping", "stack": "hedging", "symbol": "XAUUSD",
         "timeframe": "M5"},
    ),
    (
        "mean-reversion USDJPY H4 daily loss 5%",
        {"preset": "mean-reversion", "stack": "hedging", "symbol": "USDJPY",
         "timeframe": "H4"},
    ),
    (
        "breakout GBPUSD M15 SL 50 TP 100 sar or rsi",
        {"preset": "breakout", "stack": "netting", "symbol": "GBPUSD",
         "timeframe": "M15"},
    ),
    (
        "ml-onnx EURUSD H1 risk 0.3% python-bridge",
        {"preset": "ml-onnx", "stack": "python-bridge", "symbol": "EURUSD",
         "timeframe": "H1"},
    ),
    (
        "grid AUDUSD M30 hedging max positions 5",
        {"preset": "grid", "stack": "hedging", "symbol": "AUDUSD",
         "timeframe": "M30"},
    ),
    (
        "service llm bridge ollama",
        {"preset": "service-llm-bridge", "stack": "self-hosted-ollama"},
    ),
)


@pytest.mark.parametrize("prompt,expected", PROMPTS_VALID)
def test_parse_yields_schema_valid_spec(
    prompt: str, expected: dict[str, object],
) -> None:
    """Every PROMPTS_VALID entry must validate through ``spec_schema``."""
    result = parse(prompt)
    # Spot-check the headline fields the prompt forced.
    for key, want in expected.items():
        assert result.spec[key] == want, (
            f"prompt={prompt!r} field={key!r} got={result.spec[key]!r} "
            f"want={want!r}"
        )
    # Full schema validation must pass — no errors.
    spec_schema.validate(result.spec, valid_presets=build_mod.PRESETS)


# ─────────────────────────────────────────────────────────────────────────────
# Risk-block extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_per_trade_percent_extracted() -> None:
    result = parse("trend EURUSD H1 risk 0.75%")
    assert result.spec["risk"] == {"per_trade_pct": 0.75}


def test_risk_per_trade_alternate_phrasing() -> None:
    """Both ``risk 1%`` and ``1% risk`` capture the same value."""
    r1 = parse("trend EURUSD H1 1% risk")
    r2 = parse("trend EURUSD H1 risk 1%")
    assert r1.spec["risk"] == r2.spec["risk"] == {"per_trade_pct": 1.0}


def test_risk_sl_tp_pips_extracted() -> None:
    result = parse("scalping EURUSD M5 SL 25 TP 50")
    assert result.spec["risk"] == {"sl_pips": 25, "tp_pips": 50}


def test_risk_daily_loss_extracted() -> None:
    result = parse("trend EURUSD H1 daily loss 7.5%")
    assert result.spec["risk"] == {"daily_loss_pct": 7.5}


def test_risk_max_spread_extracted() -> None:
    result = parse("trend EURUSD H1 max spread 2 pips")
    assert result.spec["risk"] == {"max_spread_pips": 2.0}


def test_risk_max_positions_extracted() -> None:
    result = parse("grid AUDUSD M30 max positions 7")
    assert result.spec["risk"]["max_open_positions"] == 7


def test_risk_block_omitted_when_no_mention() -> None:
    result = parse("trend EURUSD H1")
    assert "risk" not in result.spec


# ─────────────────────────────────────────────────────────────────────────────
# Signals
# ─────────────────────────────────────────────────────────────────────────────

def test_signals_single_indicator_and_logic() -> None:
    result = parse("scalping EURUSD M5 macd")
    sigs = result.spec["signals"]
    assert isinstance(sigs, dict)
    assert sigs["logic"] == "AND"
    assert sigs["list"] == [{"kind": "macd"}]


def test_signals_multiple_indicators_or_logic() -> None:
    result = parse("breakout GBPUSD M15 sar or rsi or bbands")
    sigs = result.spec["signals"]
    assert isinstance(sigs, dict)
    assert sigs["logic"] == "OR"
    kinds = [entry["kind"] for entry in sigs["list"]]
    assert kinds == ["sar", "rsi", "bbands"]


def test_signals_deduplicated() -> None:
    """A repeated indicator keyword appears only once in the output list."""
    result = parse("trend EURUSD H1 macd macd")
    sigs = result.spec["signals"]
    assert isinstance(sigs, dict)
    assert sigs["list"] == [{"kind": "macd"}]


def test_signals_omitted_when_no_indicator() -> None:
    result = parse("trend EURUSD H1 risk 0.5%")
    assert "signals" not in result.spec


# ─────────────────────────────────────────────────────────────────────────────
# Preset + stack
# ─────────────────────────────────────────────────────────────────────────────

def test_preset_default_is_stdlib() -> None:
    result = parse("EURUSD H1 risk 0.5%")
    assert result.spec["preset"] == "stdlib"
    assert result.spec["stack"] == "netting"


def test_preset_keyword_overrides_default() -> None:
    result = parse("hft EURUSD M1")
    assert result.spec["preset"] == "hft-async"


def test_stack_clamped_to_preset_supported_values() -> None:
    """If the prompt's stack hint is incompatible, we fall back silently."""
    # ``breakout`` only supports ``netting`` — prompt asks for ``hedging``.
    result = parse("breakout GBPUSD M15 hedging")
    assert result.spec["preset"] == "breakout"
    assert result.spec["stack"] == "netting"
    spec_schema.validate(result.spec, valid_presets=build_mod.PRESETS)


def test_stack_kept_when_compatible() -> None:
    result = parse("stdlib EURUSD H1 python-bridge")
    assert result.spec["preset"] == "stdlib"
    assert result.spec["stack"] == "python-bridge"


# ─────────────────────────────────────────────────────────────────────────────
# Symbol + timeframe + name
# ─────────────────────────────────────────────────────────────────────────────

def test_symbol_slash_form_recognised() -> None:
    result = parse("trend EUR/USD H1")
    assert result.spec["symbol"] == "EURUSD"


def test_symbol_indices_and_metals() -> None:
    assert parse("scalping XAUUSD M5").spec["symbol"] == "XAUUSD"
    assert parse("scalping US30 M5").spec["symbol"] == "US30"
    assert parse("scalping NAS100 M5").spec["symbol"] == "NAS100"


def test_symbol_default_is_eurusd() -> None:
    result = parse("trend H1")
    assert result.spec["symbol"] == "EURUSD"


def test_timeframe_default_is_h1() -> None:
    result = parse("trend EURUSD")
    assert result.spec["timeframe"] == "H1"


def test_name_extracted_from_named_phrase() -> None:
    assert parse("stdlib named MyEA").spec["name"] == "MyEA"
    assert parse("trend EURUSD H1 called Alpha").spec["name"] == "Alpha"


def test_name_synthesised_when_not_named() -> None:
    """Auto-name is preset+symbol+timeframe with hyphens stripped."""
    name = parse("mean-reversion USDJPY H4").spec["name"]
    assert name == "MeanReversionUSDJPYH4"


# ─────────────────────────────────────────────────────────────────────────────
# Empty / degenerate prompts
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_prompt_yields_default_spec() -> None:
    result = parse("")
    assert result.defaulted == ["everything"]
    spec_schema.validate(result.spec, valid_presets=build_mod.PRESETS)


def test_whitespace_prompt_treated_as_empty() -> None:
    result = parse("   \n\t  ")
    assert result.defaulted == ["everything"]


# ─────────────────────────────────────────────────────────────────────────────
# YAML emitter round-trip
# ─────────────────────────────────────────────────────────────────────────────

def test_yaml_round_trip_preserves_spec() -> None:
    """Emit YAML, parse with the schema-loader, get the same spec back."""
    pytest.importorskip("yaml")
    import yaml  # type: ignore[import-untyped]

    original = parse(
        "scalping XAUUSD M5 risk 0.5% SL 30 TP 60 macd or rsi"
    ).spec
    loaded = yaml.safe_load(to_yaml(original))
    assert loaded == original


def test_yaml_emitter_stable_output() -> None:
    """Calling to_yaml twice on the same spec produces identical text."""
    spec = parse("trend EURUSD H1 risk 0.5% macd").spec
    assert to_yaml(spec) == to_yaml(spec)


def test_yaml_emitter_field_order() -> None:
    """Headline fields appear in a stable, documented order."""
    text = to_yaml(parse("scalping XAUUSD M5 risk 1% macd").spec)
    # ``name`` first, ``preset`` second, ``risk`` after the headline block
    # so a hand-edited file still reads top-to-bottom.
    name_idx   = text.find("name:")
    preset_idx = text.find("preset:")
    stack_idx  = text.find("stack:")
    risk_idx   = text.find("risk:")
    signal_idx = text.find("signals:")
    assert 0 <= name_idx < preset_idx < stack_idx < risk_idx < signal_idx


# ─────────────────────────────────────────────────────────────────────────────
# CLI integration
# ─────────────────────────────────────────────────────────────────────────────

def test_cli_writes_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    rc = spec_from_prompt.main(["trend EURUSD H1 risk 0.5%"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "preset: trend" in captured.out


def test_cli_writes_to_out_file(tmp_path: Path) -> None:
    out = tmp_path / "ea-spec.yaml"
    rc = spec_from_prompt.main(["trend EURUSD H1 risk 0.5%", "--out", str(out)])
    assert rc == 0
    assert "preset: trend" in out.read_text()


def test_cli_strict_flag_errors_on_default_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """``--strict`` exits non-zero if a mandatory field came from defaults."""
    # Prompt with no symbol/timeframe/preset hint → strict should reject.
    rc = spec_from_prompt.main(["risk 0.5%", "--strict"])
    assert rc == 1


def test_cli_strict_flag_passes_when_prompt_full(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """``--strict`` accepts a prompt that names every required field."""
    rc = spec_from_prompt.main([
        "trend EURUSD H1 risk 0.5% named MyEA", "--strict",
    ])
    assert rc == 0


def test_cli_explain_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    rc = spec_from_prompt.main(["trend EURUSD H1", "--explain"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "inferred:" in captured.err


def test_console_script_entry_point_resolves() -> None:
    """The ``mql5-spec-from-prompt`` console script must be installed."""
    result = subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.spec_from_prompt",
         "trend EURUSD H1 risk 0.5%"],
        capture_output=True,
        text=True,
        check=False,
    )
    # The module file has no __main__ guard returning early; we just want
    # to confirm it imports and is invokable as a module.
    assert result.returncode in (0, 2)  # 2 = argparse usage exit


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end: prompt → YAML → auto_build orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def test_prompt_yaml_drives_auto_build_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing the loop: feed the parser output to the auto-build pipeline."""
    pytest.importorskip("yaml")
    # Reuse the auto_build test's compile stub so we don't need Wine.
    from vibecodekit_mql5 import compile as compile_mod
    from vibecodekit_mql5 import auto_build
    from vibecodekit_mql5.permission import orchestrator as orch_mod

    def _fake_compile(path, **_kwargs):
        from vibecodekit_mql5.compile import CompileResult
        ex5 = Path(str(path)).with_suffix(".ex5")
        ex5.write_bytes(b"stub")
        return CompileResult(success=True, ex5_path=str(ex5))

    def _fake_orchestrator_run(_args):
        from vibecodekit_mql5.permission.orchestrator import OrchestratorReport
        return OrchestratorReport(
            mode="personal", ok=True, layers=[
                {"name": "layer1_lint", "ok": True, "reason": "stub"},
            ],
        )

    monkeypatch.setattr(compile_mod, "compile_mq5", _fake_compile)
    monkeypatch.setattr(orch_mod, "run", _fake_orchestrator_run)

    parsed_spec = parse(
        "stdlib named E2EProbe symbol EURUSD H1 risk 0.5% SL 30 TP 60"
    ).spec
    ea_spec = spec_schema.validate(parsed_spec, valid_presets=build_mod.PRESETS)

    out_dir = tmp_path / "build"
    report = auto_build.run_pipeline(
        spec=parsed_spec,
        out_dir=out_dir,
        force=True,
        skip_compile=False,
        skip_gate=False,
        ea_spec=ea_spec,
    )
    stage_names = {s.name for s in report.stages}
    assert report.ok is True
    assert {"build", "lint"} <= stage_names
    assert all(s.ok for s in report.stages if s.name in ("build", "lint"))
