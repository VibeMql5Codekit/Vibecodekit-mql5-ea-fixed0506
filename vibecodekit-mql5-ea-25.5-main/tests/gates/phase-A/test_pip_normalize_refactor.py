"""Phase A — pip_normalize refactor unit tests (5 tests).

Each test feeds the refactor a tiny snippet exercising one hardcoded-pip
shape and asserts the substitution + (where applicable) the include/global/
init scaffolding got injected.
"""
from __future__ import annotations

from vibecodekit_mql5.pip_normalize import normalize_source


def _snippet(body: str) -> str:
    return (
        '#include <Trade\\Trade.mqh>\n'
        'CTrade trade;\n'
        'int OnInit() {\n'
        '    return INIT_SUCCEEDED;\n'
        '}\n'
        'void OnTick() {\n'
        f'{body}'
        '}\n'
    )


def test_refactor_5d_literal():
    src = _snippet("    double d = 30 * 0.0001;\n")
    res = normalize_source("inline.mq5", src)
    assert res.substitutions == 1
    assert "pip.Pips(30)" in res.new_text


def test_refactor_3d_literal():
    src = _snippet("    double d = 30 * 0.001;\n")
    res = normalize_source("inline.mq5", src)
    assert res.substitutions == 1
    assert "pip.Pips(30)" in res.new_text


def test_refactor_underscore_point():
    src = _snippet("    double d = sl * _Point;\n")
    res = normalize_source("inline.mq5", src)
    assert res.substitutions == 1
    assert "pip.Pips(sl)" in res.new_text


def test_refactor_point_func():
    src = _snippet("    double d = sl * Point();\n")
    res = normalize_source("inline.mq5", src)
    assert res.substitutions == 1
    assert "pip.Pips(sl)" in res.new_text


def test_refactor_injects_include_global_init():
    src = _snippet("    double d = 30 * 0.0001;\n")
    res = normalize_source("inline.mq5", src)
    assert res.added_include
    assert res.added_global
    assert res.added_init
    assert '#include "CPipNormalizer.mqh"' in res.new_text
    assert "CPipNormalizer pip;" in res.new_text
    assert "pip.Init(_Symbol);" in res.new_text
