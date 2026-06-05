"""Wave 6.2b — regression tests for ``rri.escalation`` + the layer-5
``--enforce-no-open-escalation`` hook.

Covers:

* Core ``Escalation`` record validation (actors, levels, reason).
* ``raise_escalation`` append semantics + deterministic ID allocation.
* ``resolve_escalation`` happy path + idempotency guard.
* ``load_log`` graceful handling of missing / empty / corrupt files.
* ``filter_records`` status + level filters.
* ``render_list`` stable output shape.
* CLI ``--list`` / ``--resolve`` / raise modes via ``subprocess``.
* ``--json`` envelope + ``--gate-report`` artefact write.
* Layer-5 integration: personal mode informational, team / enterprise
  block on OPEN level-3.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vibecodekit_mql5.permission import layer5_methodology
from vibecodekit_mql5.rri import escalation as esc


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_actors_constant_matches_wave6_1_actors() -> None:
    assert esc.ACTORS == ("chu-nha", "chu-thau", "tho-thi-cong")


def test_levels_constant_matches_design() -> None:
    assert esc.LEVELS == (1, 2, 3)


def test_default_log_path_is_under_dot_mql5_audit() -> None:
    assert esc.DEFAULT_LOG == Path(".mql5-audit/escalations.jsonl")


@pytest.mark.parametrize("from_a,to_a", [
    ("chu-nha", "chu-thau"),
    ("chu-thau", "tho-thi-cong"),
    ("tho-thi-cong", "chu-thau"),
])
def test_raise_escalation_happy_path_writes_record(
    tmp_path: Path, from_a: str, to_a: str,
) -> None:
    log = tmp_path / ".mql5-audit" / "escalations.jsonl"
    fixed = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    record = esc.raise_escalation(
        from_actor=from_a,
        to_actor=to_a,
        level=2,
        reason="missing fixture",
        artefact="tasks/TIP-007.md",
        log_path=log,
        _now=fixed,
    )
    assert record.id == "ESC-20260525-001"
    assert record.from_actor == from_a
    assert record.to_actor == to_a
    assert record.level == 2
    assert record.reason == "missing fixture"
    assert record.artefact == "tasks/TIP-007.md"
    assert record.status == "OPEN"
    assert record.resolved_at is None
    assert log.exists()
    payload = json.loads(log.read_text().strip())
    assert payload["id"] == "ESC-20260525-001"
    assert payload["from"] == from_a
    assert payload["to"] == to_a
    assert payload["level"] == 2


def test_raise_escalation_strips_artefact_to_none_when_blank(
    tmp_path: Path,
) -> None:
    log = tmp_path / "escalations.jsonl"
    rec = esc.raise_escalation(
        from_actor="chu-thau",
        to_actor="tho-thi-cong",
        level=1,
        reason="fyi",
        artefact="   ",
        log_path=log,
    )
    assert rec.artefact is None


def test_raise_escalation_rejects_same_actor(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    with pytest.raises(ValueError, match="differ"):
        esc.raise_escalation(
            from_actor="chu-thau",
            to_actor="chu-thau",
            level=2,
            reason="self-talk",
            log_path=log,
        )


def test_raise_escalation_rejects_bad_actor(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    with pytest.raises(ValueError, match="valid actor"):
        esc.raise_escalation(
            from_actor="banker",
            to_actor="chu-thau",
            level=2,
            reason="x",
            log_path=log,
        )


def test_raise_escalation_rejects_bad_level(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    with pytest.raises(ValueError, match="level"):
        esc.raise_escalation(
            from_actor="chu-thau",
            to_actor="tho-thi-cong",
            level=4,
            reason="x",
            log_path=log,
        )


def test_raise_escalation_rejects_blank_reason(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    with pytest.raises(ValueError, match="non-empty"):
        esc.raise_escalation(
            from_actor="chu-thau",
            to_actor="tho-thi-cong",
            level=2,
            reason="   ",
            log_path=log,
        )


def test_raise_escalation_assigns_sequential_ids_same_day(
    tmp_path: Path,
) -> None:
    log = tmp_path / "escalations.jsonl"
    fixed = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    rec1 = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="a", log_path=log, _now=fixed,
    )
    rec2 = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=2,
        reason="b", log_path=log, _now=fixed,
    )
    rec3 = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="c", log_path=log, _now=fixed,
    )
    assert rec1.id == "ESC-20260525-001"
    assert rec2.id == "ESC-20260525-002"
    assert rec3.id == "ESC-20260525-003"


def test_next_id_widens_past_999_without_collision(tmp_path: Path) -> None:
    """Regression: counter > 999 must widen to >=4 digits and stay unique.

    The original ``_ID_PATTERN = r"^ESC-(\\d{8})-(\\d{3})$"`` only matched
    exactly three digits, so once the counter rolled past 999 the resulting
    id (``ESC-YYYYMMDD-1000``) silently dropped out of the ``used`` set on
    the next allocation, looping the counter back to 1000 and minting a
    duplicate. The pattern was relaxed to ``\\d{3,}`` so this test pins
    the contract.
    """

    today = "20260525"
    pre_existing = [
        esc.Escalation(
            id=f"ESC-{today}-{n:03d}",
            from_actor="chu-thau",
            to_actor="tho-thi-cong",
            level=1,
            reason=f"seed {n}",
            raised_at="2026-05-25T00:00:00+00:00",
            raised_by="chu-thau",
        )
        for n in range(1, 1000)
    ]
    first_overflow = esc._next_id(pre_existing, today=today)
    assert first_overflow == f"ESC-{today}-1000"
    assert esc._ID_PATTERN.match(first_overflow), (
        "regression: 4-digit counter must match the id pattern so the next "
        "_next_id call does not loop back to the same number"
    )

    extended = pre_existing + [
        esc.Escalation(
            id=first_overflow,
            from_actor="chu-thau",
            to_actor="tho-thi-cong",
            level=1,
            reason="overflow seed",
            raised_at="2026-05-25T00:00:00+00:00",
            raised_by="chu-thau",
        )
    ]
    second_overflow = esc._next_id(extended, today=today)
    assert second_overflow == f"ESC-{today}-1001"
    assert second_overflow != first_overflow


def test_raise_escalation_widens_id_past_999_via_log(tmp_path: Path) -> None:
    """End-to-end sibling of ``test_next_id_widens_past_999_without_collision``.

    Goes through ``raise_escalation`` so we also pin that the log read/write
    round-trip preserves 4+ digit counters.
    """

    log = tmp_path / "escalations.jsonl"
    today = "20260525"
    seeded = [
        esc.Escalation(
            id=f"ESC-{today}-{n:03d}",
            from_actor="chu-thau",
            to_actor="tho-thi-cong",
            level=1,
            reason=f"seed {n}",
            raised_at="2026-05-25T00:00:00+00:00",
            raised_by="chu-thau",
        )
        for n in range(1, 1000)
    ]
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as fh:
        for rec in seeded:
            fh.write(json.dumps(rec.to_dict()) + "\n")

    now = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    overflow = esc.raise_escalation(
        from_actor="chu-thau",
        to_actor="tho-thi-cong",
        level=1,
        reason="post-overflow",
        log_path=log,
        _now=now,
    )
    assert overflow.id == f"ESC-{today}-1000"

    again = esc.raise_escalation(
        from_actor="chu-thau",
        to_actor="tho-thi-cong",
        level=2,
        reason="post-overflow second",
        log_path=log,
        _now=now,
    )
    assert again.id == f"ESC-{today}-1001"
    assert again.id != overflow.id


def test_raise_escalation_resets_counter_per_date(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    day1 = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 5, 26, 9, 0, 0, tzinfo=timezone.utc)
    r1 = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="a", log_path=log, _now=day1,
    )
    r2 = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=2,
        reason="b", log_path=log, _now=day2,
    )
    assert r1.id == "ESC-20260525-001"
    assert r2.id == "ESC-20260526-001"


def test_load_log_returns_empty_when_missing(tmp_path: Path) -> None:
    assert esc.load_log(tmp_path / "missing.jsonl") == []


def test_load_log_skips_blank_lines(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    fixed = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="x", log_path=log, _now=fixed,
    )
    log.write_text(log.read_text() + "\n\n", encoding="utf-8")
    records = esc.load_log(log)
    assert len(records) == 1


def test_load_log_raises_on_corrupt_line(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    log.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        esc.load_log(log)


def test_resolve_escalation_happy_path(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    raised_at = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    resolved_at = datetime(2026, 5, 25, 15, 0, 0, tzinfo=timezone.utc)
    raised = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="pip math broken", log_path=log, _now=raised_at,
    )
    resolved = esc.resolve_escalation(
        raised.id,
        resolved_by="chu-thau",
        resolution="added CPipNormalizer",
        log_path=log,
        _now=resolved_at,
    )
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_by == "chu-thau"
    assert resolved.resolution == "added CPipNormalizer"
    assert resolved.resolved_at == "2026-05-25T15:00:00Z"
    records = esc.load_log(log)
    assert len(records) == 1
    assert records[0].status == "RESOLVED"


def test_resolve_escalation_rejects_double_resolve(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    raised = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="x", log_path=log,
    )
    esc.resolve_escalation(raised.id, resolved_by="chu-thau", log_path=log)
    with pytest.raises(ValueError, match="already RESOLVED"):
        esc.resolve_escalation(raised.id, resolved_by="chu-thau", log_path=log)


def test_resolve_escalation_unknown_id_raises(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="x", log_path=log,
    )
    with pytest.raises(KeyError, match="not found"):
        esc.resolve_escalation(
            "ESC-19990101-999", resolved_by="chu-thau", log_path=log,
        )


def test_resolve_escalation_empty_log_raises(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    with pytest.raises(KeyError, match="not found"):
        esc.resolve_escalation(
            "ESC-19990101-001", resolved_by="chu-thau", log_path=log,
        )


def test_filter_records_status(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    a = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=2,
        reason="a", log_path=log,
    )
    b = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="b", log_path=log,
    )
    esc.resolve_escalation(a.id, resolved_by="tho-thi-cong", log_path=log)
    records = esc.load_log(log)
    open_only = esc.filter_records(records, status="OPEN")
    resolved_only = esc.filter_records(records, status="RESOLVED")
    everything = esc.filter_records(records, status="ALL")
    assert [r.id for r in open_only] == [b.id]
    assert [r.id for r in resolved_only] == [a.id]
    assert len(everything) == 2


def test_filter_records_level(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    r1 = esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="a", log_path=log,
    )
    r2 = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="b", log_path=log,
    )
    records = esc.load_log(log)
    only3 = esc.filter_records(records, status="ALL", level=3)
    only1 = esc.filter_records(records, status="ALL", level=1)
    assert [r.id for r in only3] == [r2.id]
    assert [r.id for r in only1] == [r1.id]


def test_filter_records_rejects_bad_status() -> None:
    with pytest.raises(ValueError, match="status"):
        esc.filter_records([], status="bogus")


def test_open_level3_count(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="chu-thau", to_actor="tho-thi-cong", level=1,
        reason="a", log_path=log,
    )
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="b", log_path=log,
    )
    r3 = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="c", log_path=log,
    )
    records = esc.load_log(log)
    assert esc.open_level3_count(records) == 2
    esc.resolve_escalation(r3.id, resolved_by="chu-thau", log_path=log)
    assert esc.open_level3_count(esc.load_log(log)) == 1


def test_render_list_empty() -> None:
    assert "no escalations" in esc.render_list([])


def test_render_list_shape(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    fixed = datetime(2026, 5, 25, 14, 30, 0, tzinfo=timezone.utc)
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="missing fixture", artefact="tasks/TIP-001.md",
        log_path=log, _now=fixed,
    )
    rendered = esc.render_list(esc.load_log(log))
    assert "[OPEN] ESC-20260525-001 L3 tho-thi-cong -> chu-thau" in rendered
    assert "raised_at=2026-05-25T14:30:00Z" in rendered
    assert "artefact=tasks/TIP-001.md" in rendered
    assert "reason=missing fixture" in rendered


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


def _cli(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vibecodekit_mql5.rri.escalation", *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_raise_writes_log_and_returns_id(tmp_path: Path) -> None:
    res = _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        "--level", "3",
        "--reason", "missing CPipNormalizer",
        "--artefact", "tasks/TIP-002.md",
    ], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    assert "raised ESC-" in res.stdout
    log = tmp_path / ".mql5-audit" / "escalations.jsonl"
    assert log.exists()
    record = json.loads(log.read_text().strip())
    assert record["from"] == "tho-thi-cong"
    assert record["level"] == 3


def test_cli_raise_missing_flags_returns_2(tmp_path: Path) -> None:
    res = _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        # missing --level and --reason
    ], cwd=tmp_path)
    assert res.returncode == 2
    assert "--level" in res.stderr
    assert "--reason" in res.stderr


def test_cli_raise_invalid_actor_returns_2(tmp_path: Path) -> None:
    res = _cli([
        "--from", "banker",
        "--to", "chu-thau",
        "--level", "2",
        "--reason", "x",
    ], cwd=tmp_path)
    assert res.returncode == 2
    assert "invalid choice" in res.stderr.lower() or "from" in res.stderr.lower()


def test_cli_list_default_status_open(tmp_path: Path) -> None:
    _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        "--level", "2",
        "--reason", "still open",
    ], cwd=tmp_path)
    res = _cli(["--list"], cwd=tmp_path)
    assert res.returncode == 0
    assert "OPEN" in res.stdout
    assert "still open" in res.stdout


def test_cli_list_json_envelope(tmp_path: Path) -> None:
    _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        "--level", "3",
        "--reason", "hard block",
    ], cwd=tmp_path)
    res = _cli(["--list", "--json"], cwd=tmp_path)
    assert res.returncode == 0
    env = json.loads(res.stdout)
    assert env["tool"] == "mql5-escalation"
    assert env["schema_version"] == "1"
    assert env["ok"] is True
    assert env["data"]["mode"] == "list"
    assert env["data"]["count"] == 1
    assert env["data"]["open_level3_count"] == 1
    assert env["data"]["records"][0]["level"] == 3
    assert "matrix" not in env  # emitter intentionally omits matrix coords


def test_cli_gate_report_writes_envelope(tmp_path: Path) -> None:
    gate = tmp_path / "reports" / "gate-report-escalation.json"
    res = _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        "--level", "1",
        "--reason", "fyi",
        "--gate-report", str(gate),
    ], cwd=tmp_path)
    assert res.returncode == 0
    assert gate.exists()
    env = json.loads(gate.read_text())
    assert env["tool"] == "mql5-escalation"
    assert env["data"]["mode"] == "raise"


def test_cli_resolve_marks_record(tmp_path: Path) -> None:
    raise_res = _cli([
        "--from", "tho-thi-cong",
        "--to", "chu-thau",
        "--level", "3",
        "--reason", "block",
    ], cwd=tmp_path)
    assert raise_res.returncode == 0
    raised_id = raise_res.stdout.strip().split()[-1]
    res = _cli([
        "--resolve", raised_id,
        "--resolved-by", "chu-thau",
        "--note", "fixed it",
    ], cwd=tmp_path)
    assert res.returncode == 0
    assert f"resolved {raised_id}" in res.stdout
    log = tmp_path / ".mql5-audit" / "escalations.jsonl"
    record = json.loads(log.read_text().strip())
    assert record["status"] == "RESOLVED"
    assert record["resolution"] == "fixed it"


def test_cli_resolve_unknown_id_returns_2(tmp_path: Path) -> None:
    (tmp_path / ".mql5-audit").mkdir()
    (tmp_path / ".mql5-audit" / "escalations.jsonl").write_text("", encoding="utf-8")
    res = _cli([
        "--resolve", "ESC-19990101-001",
        "--resolved-by", "chu-thau",
    ], cwd=tmp_path)
    assert res.returncode == 2
    assert "not found" in res.stderr


def test_cli_resolve_missing_resolved_by_returns_2(tmp_path: Path) -> None:
    res = _cli(["--resolve", "ESC-19990101-001"], cwd=tmp_path)
    assert res.returncode == 2
    assert "--resolved-by" in res.stderr


def test_console_script_resolves_after_install() -> None:
    """The console script ``mql5-escalation`` resolves to our main()."""

    import importlib
    import importlib.metadata as md

    eps = md.entry_points(group="console_scripts")
    matching = [e for e in eps if e.name == "mql5-escalation"]
    assert matching, "mql5-escalation console script not registered"
    ep = matching[0]
    module_name, _, attr = ep.value.partition(":")
    mod = importlib.import_module(module_name)
    assert getattr(mod, attr) is esc.main


# ---------------------------------------------------------------------------
# Layer-5 integration tests
# ---------------------------------------------------------------------------


def _make_step_state(state_dir: Path, *step_names: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    for step in step_names:
        (state_dir / f"{step}.done").write_text("ok", encoding="utf-8")


def test_layer5_personal_with_open_l3_is_informational(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="block", log_path=log,
    )
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "build", "verify")
    result = layer5_methodology.gate(
        state_dir,
        mode="personal",
        enforce_no_open_escalation=True,
        escalation_log=log,
    )
    assert result["ok"] is True
    assert result["escalation_open_level3_count"] == 1
    assert result["escalation_enforced"] is False


def test_layer5_team_blocks_on_open_l3(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="block", log_path=log,
    )
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "rri", "vision", "build", "verify", "refine")
    result = layer5_methodology.gate(
        state_dir,
        mode="team",
        enforce_no_open_escalation=True,
        escalation_log=log,
    )
    assert result["ok"] is False
    assert result["escalation_open_level3_count"] == 1
    assert result["escalation_enforced"] is True
    assert len(result["escalation_open_level3"]) == 1


def test_layer5_team_passes_when_l3_resolved(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    raised = esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="block", log_path=log,
    )
    esc.resolve_escalation(raised.id, resolved_by="chu-thau", log_path=log)
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "rri", "vision", "build", "verify", "refine")
    result = layer5_methodology.gate(
        state_dir,
        mode="team",
        enforce_no_open_escalation=True,
        escalation_log=log,
    )
    assert result["ok"] is True
    assert result["escalation_open_level3_count"] == 0


def test_layer5_team_ignores_open_l1_l2(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=1,
        reason="note", log_path=log,
    )
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=2,
        reason="warn", log_path=log,
    )
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "rri", "vision", "build", "verify", "refine")
    result = layer5_methodology.gate(
        state_dir,
        mode="team",
        enforce_no_open_escalation=True,
        escalation_log=log,
    )
    assert result["ok"] is True
    assert result["escalation_open_level3_count"] == 0


def test_layer5_enterprise_blocks_like_team(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="block", log_path=log,
    )
    state_dir = tmp_path / ".rri-state"
    _make_step_state(
        state_dir, "scan", "rri", "vision", "blueprint", "tip",
        "build", "verify", "refine",
    )
    result = layer5_methodology.gate(
        state_dir,
        mode="enterprise",
        enforce_no_open_escalation=True,
        escalation_log=log,
    )
    assert result["ok"] is False
    assert result["escalation_enforced"] is True


def test_layer5_missing_log_means_zero_open(tmp_path: Path) -> None:
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "rri", "vision", "build", "verify", "refine")
    result = layer5_methodology.gate(
        state_dir,
        mode="team",
        enforce_no_open_escalation=True,
        escalation_log=tmp_path / "no-such-log.jsonl",
    )
    assert result["ok"] is True
    assert result["escalation_open_level3_count"] == 0


def test_layer5_cli_team_blocks_with_open_l3(tmp_path: Path) -> None:
    log = tmp_path / "escalations.jsonl"
    esc.raise_escalation(
        from_actor="tho-thi-cong", to_actor="chu-thau", level=3,
        reason="block", log_path=log,
    )
    state_dir = tmp_path / ".rri-state"
    _make_step_state(state_dir, "scan", "rri", "vision", "build", "verify", "refine")
    res = subprocess.run(
        [
            sys.executable, "-m",
            "vibecodekit_mql5.permission.layer5_methodology",
            "--mode", "team",
            "--state-dir", str(state_dir),
            "--enforce-no-open-escalation",
            "--escalation-log", str(log),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1
    payload = json.loads(res.stdout)
    assert payload["ok"] is False
    assert payload["escalation_open_level3_count"] == 1
