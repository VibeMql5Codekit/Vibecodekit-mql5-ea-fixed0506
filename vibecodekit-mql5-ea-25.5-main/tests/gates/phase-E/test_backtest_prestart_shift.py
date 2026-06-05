"""Phase E gate — backtest tester-log parser (build 5260 pre-start shift).

W7.5 from the v1.0.1 audit: when MetaTester ≥ build 5260 has no
history on the requested ``FromDate`` it silently advances the start
date and prints the new value to the journal.  The kit's walk-forward
window logic must see that shift; otherwise the OOS / IS split drifts
by an unknown number of days and AP-7 (look-ahead) tracking breaks.
"""

from __future__ import annotations

from vibecodekit_mql5.backtest import (
    BacktestResult,
    apply_tester_log,
    parse_tester_log,
)

# ─── line-shape acceptance ─────────────────────────────────────────────────

_PLAIN = (
    "2025.07.14 12:00:00.123  start time changed to 2024.01.03\n"
    "2025.07.14 12:00:00.456  testing finished\n"
)
_TESTING_PREFIX = (
    "2025.07.14 12:00:00.123  testing start time changed to 2024.01.03\n"
)
_TESTGEN_PREFIX = (
    "2025.07.14 12:00:00.123  TestGenerator: start time changed to 2024.01.03\n"
)
_NO_SHIFT = (
    "2025.07.14 12:00:00.123  EURUSD,H1: history synchronized\n"
    "2025.07.14 12:00:00.456  testing finished\n"
)


def test_parse_plain_form() -> None:
    assert parse_tester_log(_PLAIN) == ("2024.01.03", 0)


def test_parse_testing_prefix_form() -> None:
    assert parse_tester_log(_TESTING_PREFIX) == ("2024.01.03", 0)


def test_parse_testgenerator_prefix_form() -> None:
    """MetaTester sometimes prefixes the diagnostic with the subsystem
    name.  Regression: a v0.9 parser was too literal and ignored these
    lines entirely, blowing the walk-forward window."""
    assert parse_tester_log(_TESTGEN_PREFIX) == ("2024.01.03", 0)


def test_parse_no_shift_returns_empty() -> None:
    assert parse_tester_log(_NO_SHIFT) == ("", 0)


def test_parse_is_case_insensitive() -> None:
    assert parse_tester_log("START TIME CHANGED TO 2024.06.30") == (
        "2024.06.30", 0,
    )


# ─── apply_tester_log + day-delta math ─────────────────────────────────────

def test_apply_shift_computes_day_delta() -> None:
    r = BacktestResult()
    apply_tester_log(r, _PLAIN, requested_from="2024.01.01")
    assert r.actual_from_date == "2024.01.03"
    assert r.prestart_shift_days == 2


def test_apply_shift_zero_when_requested_matches_actual() -> None:
    r = BacktestResult()
    apply_tester_log(r, _PLAIN, requested_from="2024.01.03")
    assert r.actual_from_date == "2024.01.03"
    assert r.prestart_shift_days == 0


def test_apply_shift_handles_bad_requested_from() -> None:
    """Malformed ``requested_from`` must not raise — the XML is still
    valid, and the kit's report-merger downstream tolerates a 0 delta."""
    r = BacktestResult()
    apply_tester_log(r, _PLAIN, requested_from="not-a-date")
    assert r.actual_from_date == "2024.01.03"
    assert r.prestart_shift_days == 0


def test_apply_shift_is_a_noop_when_log_has_no_shift() -> None:
    r = BacktestResult()
    apply_tester_log(r, _NO_SHIFT, requested_from="2024.01.01")
    assert r.actual_from_date == ""
    assert r.prestart_shift_days == 0


def test_apply_shift_returns_same_instance_for_chaining() -> None:
    r = BacktestResult()
    out = apply_tester_log(r, _PLAIN, requested_from="2024.01.01")
    assert out is r


# ─── BacktestResult schema ─────────────────────────────────────────────────

def test_result_json_includes_new_fields() -> None:
    """The two new fields must serialize so the downstream walk-forward
    consumer (Phase F gate) can read them out of the JSON report."""
    r = BacktestResult()
    apply_tester_log(r, _PLAIN, requested_from="2024.01.01")
    d = r.to_dict()
    assert d["actual_from_date"] == "2024.01.03"
    assert d["prestart_shift_days"] == 2


def test_result_defaults_keep_old_consumers_working() -> None:
    """Old fixtures that don't touch the new fields must still produce
    a stable JSON shape (empty string + zero int)."""
    r = BacktestResult()
    d = r.to_dict()
    assert d["actual_from_date"] == ""
    assert d["prestart_shift_days"] == 0
