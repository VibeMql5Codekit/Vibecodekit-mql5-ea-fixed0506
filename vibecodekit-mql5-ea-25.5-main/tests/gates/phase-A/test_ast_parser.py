"""Wave 3.D — MQL5 AST parser POC, byte-identical detector parity.

The lightweight MQL5 structure scanner under
``scripts/vibecodekit_mql5/ast_parser/`` retrofits AP-1 (no-SL), AP-2
(SL-too-tight) and AP-7 (hardcoded magic) from regex onto an AST.

Contract pinned here:

* ``--use-ast`` produces byte-identical :class:`Finding` lists to the
  regex pipeline on every fixture in the EA-bug golden dataset (20
  fixtures, AP-1 / AP-2 / AP-7 codes).
* The same byte-identity holds on every scaffold ``EAName.mq5``
  template shipped in ``scaffolds/`` (23 fixtures).
* The tokeniser strips comments + tracks ``(line, col)`` accurately
  (a pinned unit test prevents regressions in column tracking).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit_mql5.ast_parser import (
    AST_RETROFIT_CODES,
    lint_source_ast,
    scan_structure,
    tokenize,
)
from vibecodekit_mql5.lint import lint_source

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ea-bugs"
SCAFFOLDS_ROOT = REPO_ROOT / "scaffolds"


def _ea_bug_fixtures() -> list[Path]:
    return sorted(
        folder / "EA.mq5"
        for folder in FIXTURE_ROOT.iterdir()
        if folder.is_dir() and (folder / "EA.mq5").exists()
    )


def _scaffold_eas() -> list[Path]:
    return sorted(SCAFFOLDS_ROOT.rglob("EAName.mq5"))


# ─── tokeniser ────────────────────────────────────────────────────────────────

def test_tokenize_strips_block_and_line_comments() -> None:
    src = """\
// leading line comment
/* block
   comment */ int x = 1;
"""
    tokens = [t for t in tokenize(src) if t.kind != "EOF"]
    kinds = [t.kind for t in tokens]
    assert "KEYWORD" in kinds  # `int`
    assert all(t.kind not in {"COMMENT_LINE", "COMMENT_BLOCK"} for t in tokens)


def test_tokenize_tracks_column_after_multiline_skip() -> None:
    src = "/*\n*/x"
    tokens = tokenize(src)
    # `x` should be reported at line 2, col 3 (after `*/`).
    assert tokens[0].kind == "IDENT"
    assert tokens[0].text == "x"
    assert (tokens[0].line, tokens[0].col) == (2, 3)


def test_tokenize_preproc_kept_as_single_token() -> None:
    src = "#include <Trade/Trade.mqh>\nvoid OnTick() {}\n"
    tokens = tokenize(src)
    assert tokens[0].kind == "PREPROC"
    assert tokens[0].text.startswith("#include")


def test_tokenize_keywords_distinguished_from_idents() -> None:
    src = "input int sl_pips = 3;\n"
    tokens = [t for t in tokenize(src) if t.kind != "EOF"]
    assert tokens[0].kind == "KEYWORD"
    assert tokens[0].text == "input"
    assert tokens[1].kind == "KEYWORD"
    assert tokens[1].text == "int"
    assert tokens[2].kind == "IDENT"
    assert tokens[2].text == "sl_pips"


# ─── scanner ──────────────────────────────────────────────────────────────────

def test_scan_structure_captures_input_decl() -> None:
    src = "input int sl_pips = 3;\n"
    result = scan_structure(src)
    assert len(result.var_decls) == 1
    decl = result.var_decls[0]
    assert decl.qualifiers == ("input",)
    assert decl.type_name == "int"
    assert decl.name == "sl_pips"
    assert decl.init_text == "3"
    assert decl.init_kind == "INT"


def test_scan_structure_captures_method_call() -> None:
    src = """\
void OnTick() {
    trade.Buy(0.1, _Symbol);
}
"""
    result = scan_structure(src)
    calls = result.method_calls
    assert len(calls) == 1
    call = calls[0]
    assert call.obj_name == "trade"
    assert call.method_name == "Buy"
    assert call.args == ("0.1", "_Symbol")
    # Position must point at the object identifier (`t` in `trade`).
    assert call.obj_line == 2
    assert call.obj_col == 5


def test_scan_structure_detects_csafetrade_manager_instance() -> None:
    src = "CSafeTradeManager safe;\n"
    result = scan_structure(src)
    assert "safe" in result.safe_trade_objects


def test_scan_structure_uses_magic_registry_flag() -> None:
    src = "int magic = CMagicRegistry::Reserve(70001);\n"
    result = scan_structure(src)
    assert result.uses_magic_registry is True


# ─── byte-identical parity (golden EA-bug dataset, 20 fixtures) ─────────────

@pytest.mark.parametrize(
    "fixture",
    _ea_bug_fixtures(),
    ids=lambda p: p.parent.name,
)
def test_ast_matches_regex_on_ea_bug_fixture(fixture: Path) -> None:
    """Findings from AST + remaining regex must equal pure-regex output."""
    raw = fixture.read_text(encoding="utf-8")
    regex_findings = lint_source(str(fixture), raw)
    ast_findings = lint_source_ast(str(fixture), raw)
    assert ast_findings == regex_findings


@pytest.mark.parametrize(
    "fixture",
    _ea_bug_fixtures(),
    ids=lambda p: p.parent.name,
)
def test_ast_target_codes_match_regex(fixture: Path) -> None:
    """Filter both pipelines to AP-1/2/7 only — byte-identical."""
    raw = fixture.read_text(encoding="utf-8")
    regex_targeted = [
        f for f in lint_source(str(fixture), raw)
        if f.code in AST_RETROFIT_CODES
    ]
    ast_targeted = [
        f for f in lint_source_ast(str(fixture), raw)
        if f.code in AST_RETROFIT_CODES
    ]
    assert ast_targeted == regex_targeted


# ─── byte-identical parity on scaffold templates (23 fixtures) ──────────────

@pytest.mark.parametrize(
    "scaffold",
    _scaffold_eas(),
    ids=lambda p: f"{p.parent.parent.name}/{p.parent.name}",
)
def test_ast_matches_regex_on_scaffold(scaffold: Path) -> None:
    """The 3 retrofitted detectors must match on every scaffold template too."""
    raw = scaffold.read_text(encoding="utf-8", errors="replace")
    regex_targeted = [
        f for f in lint_source(str(scaffold), raw)
        if f.code in AST_RETROFIT_CODES
    ]
    ast_targeted = [
        f for f in lint_source_ast(str(scaffold), raw)
        if f.code in AST_RETROFIT_CODES
    ]
    assert ast_targeted == regex_targeted


# ─── opt-in flag wiring ──────────────────────────────────────────────────────

def test_ast_retrofit_codes_constant() -> None:
    """Sanity: the 3 codes we claim to retrofit are exactly AP-1/2/7."""
    assert AST_RETROFIT_CODES == frozenset({"AP-1", "AP-2", "AP-7"})


def test_use_ast_cli_flag_smoke(tmp_path: Path) -> None:
    """``mql5-lint --use-ast`` accepts the flag and runs to completion."""
    from vibecodekit_mql5.lint import main

    ea = tmp_path / "EA.mq5"
    ea.write_text(
        "//+--- ea-bugs fixture: AP-1 ---+\n"
        "//| digits-tested: 5, 3 |\n"
        "#include <Trade\\Trade.mqh>\n"
        "CTrade trade;\n"
        "void OnTick() {\n"
        "    trade.Buy(0.1, _Symbol);\n"
        "}\n",
        encoding="utf-8",
    )
    rc_regex = main([str(ea)])
    rc_ast = main([str(ea), "--use-ast"])
    assert rc_regex == rc_ast


def test_ast_idempotent_matches_regex_on_empty_source() -> None:
    """Empty / whitespace-only sources produce identical findings on
    both pipelines. (The regex AP-21 detector fires WARN on missing
    ``// digits-tested:`` tag; the AST path must match that exactly.)
    """
    assert lint_source_ast("noop.mq5", "") == lint_source("noop.mq5", "")
    assert lint_source_ast("noop.mq5", "\n\n  \n") == lint_source(
        "noop.mq5", "\n\n  \n"
    )
