"""Wave 6.1 — regression tests for layer-5 ``--enforce-sign-off`` mode.

Covers both the standalone ``rri.sign_off`` audit module AND the
extended ``permission.layer5_methodology.gate`` integration.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


from vibecodekit_mql5.permission import layer5_methodology
from vibecodekit_mql5.rri import sign_off as so


BLUEPRINT_OK = """\
# Step 4 / 8 — BLUEPRINT

## Invariants
- Stop loss every order
- Magic numbers reserved

APPROVED by Alice at 2026-05-25
"""


BLUEPRINT_NO_SIGN = """\
# Step 4 / 8 — BLUEPRINT

## Invariants
- Stop loss every order
"""


CONTRACT_OK = """\
# Contract

## DELIVERABLES
- Compiled `.ex5`

CONFIRM by Alice at 2026-05-25
"""


CONTRACT_NO_SIGN = """\
# Contract

## DELIVERABLES
- Compiled `.ex5`
"""


# ---------------------------------------------------------------------------
# sign_off module
# ---------------------------------------------------------------------------


def test_audit_artefact_blueprint_signed(tmp_path: Path) -> None:
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_OK, encoding="utf-8")
    audit = so.audit_artefact(
        artefact="blueprint",
        path=bp,
        pattern=so.APPROVED_PATTERN,
        candidates=so.DEFAULT_BLUEPRINT_NAMES,
        search_dirs=(tmp_path,),
    )
    assert audit.found is True
    assert audit.signer == "Alice"
    assert audit.signed_at == "2026-05-25"
    assert audit.canonical_sha256 is not None


def test_audit_artefact_blueprint_missing_signature(tmp_path: Path) -> None:
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_NO_SIGN, encoding="utf-8")
    audit = so.audit_artefact(
        artefact="blueprint",
        path=bp,
        pattern=so.APPROVED_PATTERN,
        candidates=so.DEFAULT_BLUEPRINT_NAMES,
        search_dirs=(tmp_path,),
    )
    assert audit.found is False
    assert audit.signer is None
    assert "lacks a sign-off line" in (audit.error or "")
    # We can still compute a canonical hash so the operator can compare
    # before/after editing.
    assert audit.canonical_sha256 is not None


def test_audit_artefact_blueprint_not_found(tmp_path: Path) -> None:
    audit = so.audit_artefact(
        artefact="blueprint",
        path=None,
        pattern=so.APPROVED_PATTERN,
        candidates=so.DEFAULT_BLUEPRINT_NAMES,
        search_dirs=(tmp_path,),
    )
    assert audit.found is False
    assert audit.path is None
    assert audit.canonical_sha256 is None
    assert "not found" in (audit.error or "")


def test_audit_artefact_canonical_hash_strips_signature(tmp_path: Path) -> None:
    """Same body, signed vs. unsigned, must produce the same hash.

    This is the property the sign-off sentinel relies on so re-signing
    after a body edit fails.
    """
    body_unsigned = BLUEPRINT_NO_SIGN
    body_signed = body_unsigned + "\nAPPROVED by Carol at 2026-06-01\n"
    bp_a = tmp_path / "a.md"
    bp_b = tmp_path / "b.md"
    bp_a.write_text(body_unsigned, encoding="utf-8")
    bp_b.write_text(body_signed, encoding="utf-8")
    a = so.audit_artefact(
        artefact="blueprint",
        path=bp_a,
        pattern=so.APPROVED_PATTERN,
        candidates=(),
        search_dirs=(),
    )
    b = so.audit_artefact(
        artefact="blueprint",
        path=bp_b,
        pattern=so.APPROVED_PATTERN,
        candidates=(),
        search_dirs=(),
    )
    assert a.canonical_sha256 == b.canonical_sha256


def test_audit_sign_off_both_signed(tmp_path: Path) -> None:
    (tmp_path / "step-4-blueprint.md").write_text(BLUEPRINT_OK, encoding="utf-8")
    (tmp_path / "contract.md").write_text(CONTRACT_OK, encoding="utf-8")
    ok, audits = so.audit_sign_off(
        blueprint_path=tmp_path / "step-4-blueprint.md",
        contract_path=tmp_path / "contract.md",
        require_contract=True,
    )
    assert ok is True
    assert len(audits) == 2
    assert all(a.found for a in audits)


def test_audit_sign_off_missing_contract_fails_team(tmp_path: Path) -> None:
    (tmp_path / "step-4-blueprint.md").write_text(BLUEPRINT_OK, encoding="utf-8")
    (tmp_path / "contract.md").write_text(CONTRACT_NO_SIGN, encoding="utf-8")
    ok, audits = so.audit_sign_off(
        blueprint_path=tmp_path / "step-4-blueprint.md",
        contract_path=tmp_path / "contract.md",
        require_contract=True,
    )
    assert ok is False
    assert audits[0].found is True
    assert audits[1].found is False


def test_audit_sign_off_contract_optional_in_personal_mode(tmp_path: Path) -> None:
    (tmp_path / "step-4-blueprint.md").write_text(BLUEPRINT_OK, encoding="utf-8")
    # No contract file at all.
    ok, audits = so.audit_sign_off(
        blueprint_path=tmp_path / "step-4-blueprint.md",
        contract_path=None,
        require_contract=False,
    )
    assert ok is True
    # When contract is optional and missing, only blueprint audit is returned.
    assert len(audits) == 1
    assert audits[0].artefact == "blueprint"


# ---------------------------------------------------------------------------
# layer5_methodology.gate integration
# ---------------------------------------------------------------------------


def _setup_sentinels(state_dir: Path, mode: str) -> None:
    """Touch all required step sentinels for a given mode."""

    from vibecodekit_mql5.rri import step_workflow as sw

    state_dir.mkdir(parents=True, exist_ok=True)
    for step in sw.required_steps(mode):
        (state_dir / f"{step}.done").touch()


def test_layer5_gate_sign_off_passes_team(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "team")
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_OK, encoding="utf-8")
    contract = tmp_path / "contract.md"
    contract.write_text(CONTRACT_OK, encoding="utf-8")
    result = layer5_methodology.gate(
        state,
        "team",
        enforce_sign_off=True,
        blueprint_path=bp,
        contract_path=contract,
    )
    assert result["ok"] is True
    assert result["sign_off_ok"] is True
    assert result["sign_off_required_contract"] is True


def test_layer5_gate_sign_off_fails_when_contract_unsigned(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "team")
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_OK, encoding="utf-8")
    contract = tmp_path / "contract.md"
    contract.write_text(CONTRACT_NO_SIGN, encoding="utf-8")
    result = layer5_methodology.gate(
        state,
        "team",
        enforce_sign_off=True,
        blueprint_path=bp,
        contract_path=contract,
    )
    assert result["ok"] is False
    assert result["sign_off_ok"] is False


def test_layer5_gate_sign_off_personal_only_needs_blueprint(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "personal")
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_OK, encoding="utf-8")
    # No contract on disk.
    result = layer5_methodology.gate(
        state,
        "personal",
        enforce_sign_off=True,
        blueprint_path=bp,
    )
    assert result["ok"] is True
    assert result["sign_off_ok"] is True
    assert result["sign_off_required_contract"] is False


def test_layer5_gate_sign_off_personal_fails_when_blueprint_unsigned(
    tmp_path: Path,
) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "personal")
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_NO_SIGN, encoding="utf-8")
    result = layer5_methodology.gate(
        state,
        "personal",
        enforce_sign_off=True,
        blueprint_path=bp,
    )
    assert result["ok"] is False
    assert result["sign_off_ok"] is False


def test_layer5_gate_skips_sign_off_when_flag_off(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "personal")
    result = layer5_methodology.gate(state, "personal")
    assert result["ok"] is True
    assert "sign_off_audits" not in result


def test_layer5_cli_enforce_sign_off_emits_json(tmp_path: Path) -> None:
    state = tmp_path / ".rri-state"
    _setup_sentinels(state, "team")
    bp = tmp_path / "step-4-blueprint.md"
    bp.write_text(BLUEPRINT_OK, encoding="utf-8")
    contract = tmp_path / "contract.md"
    contract.write_text(CONTRACT_OK, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vibecodekit_mql5.permission.layer5_methodology",
            "--state-dir",
            str(state),
            "--mode",
            "team",
            "--enforce-sign-off",
            "--blueprint",
            str(bp),
            "--contract",
            str(contract),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["sign_off_ok"] is True
    assert len(payload["sign_off_audits"]) == 2
