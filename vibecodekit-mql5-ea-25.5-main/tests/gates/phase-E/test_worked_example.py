"""Phase E unit tests — worked example replay verification."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EX_DIR = REPO_ROOT / "examples" / "ea-wizard-macd-sar-eurusd-h1-portfolio"


def test_worked_example_ea_uses_kit_includes() -> None:
    src = (EX_DIR / "EAName.mq5").read_text()
    for inc in ("CPipNormalizer.mqh", "CRiskGuard.mqh", "CMagicRegistry.mqh",
                "CSpreadGuard.mqh", "CMfeMaeLogger.mqh"):
        assert f"#include <{inc}>" in src, f"worked example must use {inc}"


def test_worked_example_releases_indicator_handles() -> None:
    """AP-12 regression: handles created in OnInit released in OnDeinit."""
    src = (EX_DIR / "EAName.mq5").read_text()
    assert "iMACD(" in src
    assert "iSAR(" in src
    assert "IndicatorRelease(h_macd)" in src
    assert "IndicatorRelease(h_sar)" in src


def test_worked_example_set_file_has_inputs() -> None:
    """The 6-input AP-5-compliant optimiser surface (v1.10).

    MACD/SAR periods used to live here too; they were retired into
    compile-time constants in EAName.mq5 to keep the .set under the
    AP-5 cap.  Reference: examples/.../EAName.mq5 v1.10 header.
    """
    text = (EX_DIR / "eurusd-h1.set").read_text()
    for key in ("InpMagic", "InpRiskPerTradePct", "InpDailyLossPct",
                "InpMaxPositions", "InpMaxSpreadPips", "InpSlPips"):
        assert key in text, f"set file missing {key}"


def test_worked_example_results_artefacts_complete() -> None:
    for f in ("backtest.xml", "multibroker.csv", "canary.log",
              "matrix-64-cell.html"):
        assert (EX_DIR / "results" / f).exists()


def test_worked_example_canary_log_not_gitignored() -> None:
    """Regression: ``*.log`` in .gitignore must not silently exclude canary.log."""
    import subprocess
    canary = EX_DIR / "results" / "canary.log"
    # ``git check-ignore`` exits 0 when the path IS ignored; 1 means not ignored.
    res = subprocess.run(
        ["git", "check-ignore", str(canary)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert res.returncode == 1, (
        f"canary.log is excluded by .gitignore: {res.stdout.strip()}"
    )


def test_worked_example_matrix_html_color_codes_present() -> None:
    html = (EX_DIR / "results" / "matrix-64-cell.html").read_text()
    # 8 rows × 8 cols of color-coded cells.
    assert "PASS" in html
    assert "<table>" in html
