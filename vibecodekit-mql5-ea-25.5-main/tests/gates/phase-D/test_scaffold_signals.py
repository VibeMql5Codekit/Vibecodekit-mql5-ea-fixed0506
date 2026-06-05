"""Phase D — W9 scaffold signal-logic regression.

The five strategy archetypes (trend, mean-reversion, breakout, scalping,
hft-async) MUST ship with reachable ``trade.Buy`` / ``trade.Sell`` (or
``Send*Async``) calls in their ``OnTick`` bodies. This was previously
TODO — see audit W9. The presence of a real call is the contract
``mql5-lint`` checks with AP-22; this gate locks that in.

The remaining 18 scaffolds are deliberately infra-only (library /
indicator-only / stdlib / service / portfolio-basket / news-trading /
grid / dca / hedging-multi / arbitrage-stat / ml-onnx / wizard-composable /
3× service-llm-bridge), so they continue to emit a *visible WARN AP-22*
that asks the operator to wire signal logic before shipping. That WARN
must never become an ERROR — Plan v5 §7 mandates all best-practice
findings are advisory.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5 import lint
from vibecodekit_mql5.build import BuildRequest, build

REPO = Path(__file__).resolve().parents[3]

# Each entry: (preset, stack, marker substring that proves a real signal helper).
STRATEGY_SCAFFOLDS: list[tuple[str, str, str]] = [
    ("trend",          "netting", "IsBuySignal(fast, slow)"),
    ("mean-reversion", "hedging", "IsBuySignal(rsi)"),
    ("breakout",       "netting", "IsBuySignal(close, hh)"),
    ("scalping",       "hedging", "IsBuySignal(open1, close1)"),
    ("hft-async",      "netting", "IsBuySignal(prev_ask, ask)"),
]


def _render(preset: str, stack: str, tmp_path: Path) -> Path:
    out = tmp_path / f"{preset}_{stack}"
    req = BuildRequest(
        preset=preset,
        name="SignalEA",
        symbol="EURUSD",
        tf="H1",
        stack=stack,
        out_dir=out,
        scaffolds_root=REPO / "scaffolds",
        include_root=REPO / "Include",
    )
    build(req)
    mq5 = out / "SignalEA.mq5"
    assert mq5.is_file()
    return mq5


@pytest.mark.parametrize("preset,stack,marker", STRATEGY_SCAFFOLDS)
def test_strategy_scaffold_ships_real_signal_logic(
    preset: str, stack: str, marker: str, tmp_path: Path
) -> None:
    """Render the strategy archetype and assert it contains a real
    IsBuySignal/IsSellSignal helper plus a reachable order-placing call.
    """
    mq5 = _render(preset, stack, tmp_path)
    text = mq5.read_text(encoding="utf-8")
    assert marker in text, (
        f"{preset}/{stack} must call its IsBuySignal helper; "
        f"marker {marker!r} not found in rendered file"
    )
    has_trade = "trade.Buy(" in text or "trade.Sell(" in text
    has_async = "SendBuyAsync(" in text or "SendSellAsync(" in text
    assert has_trade or has_async, (
        f"{preset}/{stack} must reach trade.Buy/Sell or *Async — "
        "signal logic is the W9 contract"
    )


@pytest.mark.parametrize("preset,stack,_marker", STRATEGY_SCAFFOLDS)
def test_strategy_scaffold_no_ap22_warning(
    preset: str, stack: str, _marker: str, tmp_path: Path
) -> None:
    """The five strategy scaffolds must NOT trigger AP-22 (placeholder-
    signal warning) — they ship with real signal logic by design.
    """
    mq5 = _render(preset, stack, tmp_path)
    findings = lint.lint_file(mq5)
    ap22 = [f for f in findings if f.code == "AP-22"]
    assert ap22 == [], (
        f"{preset}/{stack} unexpectedly triggers AP-22: {ap22}"
    )


def test_strategy_scaffold_uses_sinput_for_strategy_knobs(tmp_path: Path) -> None:
    """Strategy knobs (EMA periods, RSI thresholds, Donchian lookback,
    ATR period, tick-rate gate) must use ``sinput`` so the optimizer
    leaves them fixed by default and AP-5 (>6 optimizable inputs) stays
    clean.
    """
    sinput_markers = {
        "trend":          ("InpEmaFastPeriod",   "InpEmaSlowPeriod"),
        "mean-reversion": ("InpRsiPeriod",       "InpRsiOversold"),
        "breakout":       ("InpLookbackBars",    None),
        "scalping":       ("InpMaxSpreadPoints", "InpAtrPeriod"),
        "hft-async":      ("InpMinTicksPerSec",  "InpMaxPendingAsync"),
    }
    stack_for = {p: s for p, s, _ in STRATEGY_SCAFFOLDS}
    for preset, names in sinput_markers.items():
        mq5 = _render(preset, stack_for[preset], tmp_path)
        text = mq5.read_text(encoding="utf-8")
        for name in names:
            if name is None:
                continue
            # Match either `sinput int InpX` or `sinput double InpX`.
            assert any(
                line.lstrip().startswith("sinput ") and name in line
                for line in text.splitlines()
            ), f"{preset}: {name} must be declared as sinput"


def test_placeholder_scaffold_still_triggers_ap22(tmp_path: Path) -> None:
    """Spot-check an unfinished placeholder scaffold (news-trading)
    still flags AP-22 — the WARN is the kit's mechanism for telling
    the operator a strategy is missing.
    """
    mq5 = _render("news-trading", "netting", tmp_path)
    findings = lint.lint_file(mq5)
    ap22 = [f for f in findings if f.code == "AP-22"]
    assert len(ap22) == 1, f"news-trading must WARN AP-22 once; got {ap22}"
    assert ap22[0].severity == "WARN"
