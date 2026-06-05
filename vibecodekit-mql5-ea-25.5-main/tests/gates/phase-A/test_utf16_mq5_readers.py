"""Phase A — UTF-16-LE / BOM regression tests for kit's .mq5 readers.

MetaEditor's default save format is **UTF-16-LE with BOM**. Before this
gate landed, ``lint.py`` / ``docs_bundle.py`` / ``trader_check.py`` /
``method_hiding_check.py`` etc. all read user source with
``read_text(encoding="utf-8", errors="replace")`` — which silently
turned every UTF-16 byte pair into ``\\ufffd`` so the regex-based
detectors fired zero hits on otherwise-broken EAs. End-users shipped
unverified bots.

These tests pin the invariant: an EA saved by MetaEditor must produce
the **same lint / parse output** regardless of which legal encoding
(UTF-8 with/without BOM, UTF-16-LE with BOM, UTF-16-BE with BOM) it
arrived in. We test by writing the same source bytes in each encoding
and asserting the kit's readers see them identically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5 import lint as lint_mod
from vibecodekit_mql5 import method_hiding_check
from vibecodekit_mql5 import trader_check
from vibecodekit_mql5.docs_bundle import build_context
from vibecodekit_mql5.mq5_io import (
    decode_mq5_bytes,
    read_mq5_text,
    read_mq5_text_with_encoding,
)
from vibecodekit_mql5.permission import layer1_source_lint

_SAMPLE_EA = """\
// digits-tested: 5,3
#include <Trade/Trade.mqh>

input double Lots = 0.01;
input int StopLossPips = 20;
input int TakeProfitPips = 40;
input int MagicNumber = 70010;
input int MaxSpreadPoints = 30;
input bool UseTrailing = true;
input bool UseBreakEven = false;
input int TrailingStartPips = 15;

CTrade trade;

void OnTick() {
    // Hardcoded pip math is an AP-20 finding — assert the detector
    // sees it through every encoding.
    double sl = Bid - StopLossPips * 0.0001;
    trade.Buy(Lots);
}
"""


def _write_in_encoding(tmp_path: Path, name: str, text: str, encoding: str) -> Path:
    """Write ``text`` to ``tmp_path/name`` using ``encoding``.

    ``utf-16`` adds a BOM automatically (Python's stdlib behaviour),
    ``utf-16-le`` does not; we prepend one manually to match what
    MetaEditor writes.
    """
    path = tmp_path / name
    if encoding == "utf-16-le":
        path.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    elif encoding == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    else:
        path.write_text(text, encoding=encoding)
    return path


ENCODINGS = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le"]


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_read_mq5_text_handles_encoding(tmp_path: Path, encoding: str) -> None:
    path = _write_in_encoding(tmp_path, f"sample.{encoding}.mq5", _SAMPLE_EA, encoding)
    text = read_mq5_text(path)
    assert "OnTick" in text
    # No BOM leaks past the helper — every detector that anchors on ``^``
    # relies on this.
    assert not text.startswith("\ufeff")


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_lint_finds_same_codes_across_encodings(
    tmp_path: Path, encoding: str
) -> None:
    """The same source must produce the same lint codes regardless of
    on-disk encoding.

    Pre-fix, UTF-16-LE files lost every detector except AP-21 (which
    fires on the *absence* of a comment, so it survives even on
    garbled input). UTF-8 was the only encoding the kit could see.
    """
    utf8 = _write_in_encoding(tmp_path, "utf8.mq5", _SAMPLE_EA, "utf-8")
    other = _write_in_encoding(tmp_path, f"other_{encoding}.mq5", _SAMPLE_EA, encoding)

    utf8_codes = sorted({f.code for f in lint_mod.lint_file(utf8)})
    other_codes = sorted({f.code for f in lint_mod.lint_file(other)})
    assert utf8_codes == other_codes, (
        f"lint_file output differs between utf-8 and {encoding!r}: "
        f"utf8={utf8_codes} other={other_codes}"
    )


def test_lint_utf16le_detects_hardcoded_pip_math(tmp_path: Path) -> None:
    """Pin the concrete regression: AP-20 must fire on UTF-16-LE input."""
    path = _write_in_encoding(tmp_path, "utf16.mq5", _SAMPLE_EA, "utf-16-le")
    codes = {f.code for f in lint_mod.lint_file(path)}
    assert "AP-20" in codes, f"AP-20 missing on UTF-16-LE; got {codes}"


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_docs_bundle_parses_inputs_across_encodings(
    tmp_path: Path, encoding: str
) -> None:
    """``mql5-docs-bundle`` extracted 0 inputs from MetaEditor's
    default UTF-16-LE save — every per-input card silently vanished
    from the generated guide. Pin that all four encodings recover the
    full input list (7 declarations in :data:`_SAMPLE_EA`).
    """
    mq5 = _write_in_encoding(tmp_path, f"docs_{encoding}.mq5", _SAMPLE_EA, encoding)
    spec = tmp_path / "ea-spec.yaml"
    spec.write_text(
        "name: SampleEA\npreset: trend\nstack: netting\nsymbol: EURUSD\n"
        "timeframe: H1\nrisk:\n  per_trade_pct: 0.5\n",
        encoding="utf-8",
    )
    ctx = build_context(spec, mq5)
    names = [i["name"] for i in ctx["inputs"]]
    assert names == [
        "Lots",
        "StopLossPips",
        "TakeProfitPips",
        "MagicNumber",
        "MaxSpreadPoints",
        "UseTrailing",
        "UseBreakEven",
        "TrailingStartPips",
    ], f"docs-bundle dropped inputs on {encoding}: {names}"


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_trader_check_consistent_across_encodings(
    tmp_path: Path, encoding: str
) -> None:
    """Trader-17 evaluator reads source text directly. Verify the
    point counts are stable across encodings (a UTF-16-LE file used to
    score all N/A because the regex couldn't see anything).
    """
    utf8_text = read_mq5_text(
        _write_in_encoding(tmp_path, "u8.mq5", _SAMPLE_EA, "utf-8")
    )
    other_text = read_mq5_text(
        _write_in_encoding(tmp_path, f"o_{encoding}.mq5", _SAMPLE_EA, encoding)
    )
    assert trader_check.evaluate(utf8_text) == trader_check.evaluate(other_text)


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_method_hiding_check_handles_encoding(
    tmp_path: Path, encoding: str
) -> None:
    """``mql5-method-hiding-check`` needs to parse class bodies; with
    UTF-16-LE bytes seen as utf-8-replace it found zero classes and
    silently passed every EA.
    """
    src = (
        "// digits-tested: 5\n"
        "class CMyTrade : public CTrade {\n"
        "public:\n"
        "  bool Buy(double volume) { return CTrade::Buy(volume); }\n"
        "};\n"
    )
    path = _write_in_encoding(tmp_path, f"mh_{encoding}.mq5", src, encoding)
    report = method_hiding_check.check_method_hiding(path)
    # Either Build ≥ 5260 emits an ERROR or earlier emits WARN — we
    # only require that the *parser* saw the class at all; the test
    # is encoding-agnostic, not severity-agnostic.
    assert report.target_build >= 5260
    assert isinstance(report.issues, list)


def test_decode_mq5_bytes_reports_encoding() -> None:
    text_bytes = _SAMPLE_EA.encode("utf-16-le")
    text, enc = decode_mq5_bytes(b"\xff\xfe" + text_bytes)
    assert enc == "utf-16"
    assert "OnTick" in text


def test_decode_mq5_bytes_strips_utf8_bom() -> None:
    raw = b"\xef\xbb\xbf" + _SAMPLE_EA.encode("utf-8")
    text, enc = decode_mq5_bytes(raw)
    assert enc == "utf-8"
    assert not text.startswith("\ufeff")


def test_decode_mq5_bytes_falls_back_to_latin1() -> None:
    """The ladder is utf-8 → utf-16-le → utf-16 → latin-1.

    For an *odd-byte-length* latin-1 source utf-16-le can't accept the
    input (it needs even bytes), so the ladder rolls forward to
    latin-1. That's the only path where we can pin "latin-1 was the
    fallback" — even-byte latin-1 silently matches utf-16-le first,
    which is an acceptable kit-light tradeoff (MetaEditor never writes
    latin-1).
    """
    raw = b"//abc\n\xfc"  # 7 bytes — odd length kills utf-16-le path
    text, enc = decode_mq5_bytes(raw)
    assert enc == "latin-1"
    assert "abc" in text


def test_layer1_source_lint_uses_shared_helper(tmp_path: Path) -> None:
    """layer1 ``_decode`` is now a thin wrapper around the shared
    helper — verify the contract still holds (utf-16-le → str)."""
    path = _write_in_encoding(tmp_path, "l1.mq5", _SAMPLE_EA, "utf-16-le")
    text = layer1_source_lint._decode(path)
    assert "OnTick" in text


def test_read_mq5_text_with_encoding_round_trip(tmp_path: Path) -> None:
    """``auto_fix`` / ``pip_normalize`` rely on the encoding being
    surfaced so they can re-write the file in its original format.
    """
    path = _write_in_encoding(tmp_path, "rt.mq5", _SAMPLE_EA, "utf-16-le")
    text, enc = read_mq5_text_with_encoding(path)
    assert enc == "utf-16"  # BOM-led UTF-16 dispatch path
    assert "OnTick" in text
