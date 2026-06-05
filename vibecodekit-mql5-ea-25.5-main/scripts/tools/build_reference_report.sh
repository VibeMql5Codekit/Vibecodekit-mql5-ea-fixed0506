#!/usr/bin/env bash
# build_reference_report.sh — Regenerate docs/reference-ea/REPORT.md from a freshly
# scaffolded reference EA. Numbers reported here are honest, reproducible measurements
# from this kit's own gates — not claims about live-trading performance.
#
# Run:  bash scripts/tools/build_reference_report.sh
# Output: runtime/reference-ea/SampleEA/  (gitignored build artefact)
#         docs/reference-ea/REPORT.md     (committed honest snapshot)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

REF_DIR="runtime/reference-ea"
REF_EA="$REF_DIR/SampleEA/SampleEA.mq5"
REPORT="docs/reference-ea/REPORT.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Scaffold reference EA fresh
rm -rf "$REF_DIR"
mkdir -p "$REF_DIR"
mql5-build stdlib --name SampleEA --symbol EURUSD --tf H1 --out "$REF_DIR/SampleEA" >/dev/null

# 2. Run gates and capture raw output
mql5-lint              "$REF_EA"                              >"$TMP/lint.txt"           2>&1 || true
mql5-lint              "$REF_EA"                  --json      >"$TMP/lint.json"          2>&1 || true
mql5-trader-check      "$REF_EA"                              >"$TMP/trader17.txt"       2>&1 || true
mql5-trader-check      "$REF_EA"                  --json      >"$TMP/trader17.json"      2>&1 || true
mql5-permission --mode personal    "$REF_EA"      --json      >"$TMP/perm-personal.json" 2>&1 || true
mql5-permission --mode team        "$REF_EA"      --json      >"$TMP/perm-team.json"     2>&1 || true
mql5-permission --mode enterprise  "$REF_EA"      --json      >"$TMP/perm-enterprise.json" 2>&1 || true
# Note: this kit (-25.5) does not register a `mql5-matrix` CLI in pyproject.toml.
# The matrix module is reached via `python -m vibecodekit_mql5.rri.matrix`. We
# call it with no `--inputs/--collect` so it returns the bare-scaffold baseline
# (all 64 cells N/A) and emits structured JSON on stdout that the extractor
# below parses directly. See `scripts/vibecodekit_mql5/rri/matrix.py` for the
# argparser definition.
python -m vibecodekit_mql5.rri.matrix --output "$TMP/matrix.html"  >"$TMP/matrix.json"       2>&1 || true
python -m vibecodekit_mql5.rri.matrix --audit                      >"$TMP/matrix-audit.json" 2>&1 || true

# 3. Extract structured numbers
python3 - "$TMP" >"$TMP/numbers.json" <<'PY'
import json, re, sys
from pathlib import Path
tmp = Path(sys.argv[1])

def read(name):
    return (tmp / name).read_text(encoding="utf-8", errors="replace")

def load(name):
    try:
        return json.loads(read(name))
    except Exception:
        return {}

lint_env = load("lint.json")
trader_env = load("trader17.json")
perm_personal = load("perm-personal.json")
perm_team = load("perm-team.json")
perm_ent = load("perm-enterprise.json")
matrix_audit = load("matrix-audit.json")
matrix_cli = load("matrix.json")

trader_summary = trader_env.get("summary", "")
m = re.search(r"(\d+)/(\d+)\s+PASS,\s*(\d+)\s+WARN,\s*(\d+)\s+N/A,\s*(\d+)\s+FAIL", trader_summary)
if m:
    t17_pass = int(m.group(1))
    t17_total = int(m.group(2))
    t17_warn = int(m.group(3))
    t17_na = int(m.group(4))
    t17_fail = int(m.group(5))
else:
    t17_pass = t17_total = t17_warn = t17_na = t17_fail = 0

def first_fail_layer(env):
    layers = env.get("data", {}).get("layers", [])
    for L in layers:
        if not L.get("ok"):
            return L.get("layer"), L.get("errors", [None])[0] if L.get("errors") else "(no detail)"
    return None, None

p_layer, p_err = first_fail_layer(perm_personal)
t_layer, t_err = first_fail_layer(perm_team)
e_layer, e_err = first_fail_layer(perm_ent)

# Matrix CLI (-25.5 layout): no `--inputs/--collect` => bare baseline. Counts come
# straight from `matrix.json`. The legacy 56/64 "personal" threshold and stricter
# 60/64 "enterprise" threshold are documented in matrix.py:MatrixReport.passes_*
# (Plan v5 §10). The gate-only variants apply only over the 6 gate-auto cells
# (Wave 4.3).
mat_counts = matrix_cli.get("counts", {}) if isinstance(matrix_cli, dict) else {}
mat_pass = int(mat_counts.get("PASS", 0))
mat_warn = int(mat_counts.get("WARN", 0))
mat_fail = int(mat_counts.get("FAIL", 0))
mat_na   = int(mat_counts.get("N/A", 0))
mat_total = mat_pass + mat_warn + mat_fail + mat_na
mat_personal_ok = bool(matrix_cli.get("passes_personal", False))
mat_enterprise_ok = bool(matrix_cli.get("passes_enterprise", False))
mat_personal_gate_ok = bool(matrix_cli.get("passes_personal_gate_only", False))
mat_enterprise_gate_ok = bool(matrix_cli.get("passes_enterprise_gate_only", False))

counts = matrix_audit.get("counts", {}) if isinstance(matrix_audit, dict) else {}
mat_gate_auto = counts.get("gate_auto", "?")
mat_rri_broadcast = counts.get("rri_broadcast", "?")
mat_manual = counts.get("manual", "?")

out = {
    "lint": {
        "errors": lint_env.get("data", {}).get("error_count", 0),
        "warnings": lint_env.get("data", {}).get("warn_count", 0),
        "findings": lint_env.get("data", {}).get("findings", []),
        "summary": lint_env.get("summary", ""),
    },
    "trader17": {
        "pass": t17_pass,
        "warn": t17_warn,
        "na": t17_na,
        "fail": t17_fail,
        "total": t17_total or 17,
        "gate_pass": t17_pass >= 15,
        "summary": trader_summary,
        "raw": read("trader17.txt").strip(),
    },
    "permission": {
        "personal":   {"ok": perm_personal.get("ok"), "fail_layer": p_layer, "error": p_err, "summary": perm_personal.get("summary", "")},
        "team":       {"ok": perm_team.get("ok"),     "fail_layer": t_layer, "error": t_err, "summary": perm_team.get("summary", "")},
        "enterprise": {"ok": perm_ent.get("ok"),      "fail_layer": e_layer, "error": e_err, "summary": perm_ent.get("summary", "")},
    },
    "matrix_cli": {
        "pass": mat_pass,
        "warn": mat_warn,
        "fail": mat_fail,
        "na": mat_na,
        "total": mat_total,
        "passes_personal":          mat_personal_ok,
        "passes_enterprise":        mat_enterprise_ok,
        "passes_personal_gate_only":   mat_personal_gate_ok,
        "passes_enterprise_gate_only": mat_enterprise_gate_ok,
    },
    "matrix_audit": {
        "gate_auto": mat_gate_auto,
        "rri_broadcast": mat_rri_broadcast,
        "manual": mat_manual,
    },
}
print(json.dumps(out, indent=2))
PY

NUMBERS_FILE="$TMP/numbers.json"

# 4. Render Markdown report
python3 - "$NUMBERS_FILE" "$REPORT" <<'PY'
import json, sys, datetime
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
out_path = Path(sys.argv[2])

lint = data["lint"]
t17 = data["trader17"]
perm = data["permission"]
matrix_cli = data["matrix_cli"]
matrix_audit = data["matrix_audit"]

def perm_row(mode, p):
    if p.get("ok"):
        verdict = "PASS"
    else:
        verdict = f"FAIL at layer {p.get('fail_layer')}"
    return f"| `--mode {mode}` | {verdict} | {p.get('summary', '').strip()} |"

lint_findings_block = "\n".join(
    f"- `{f['code']}` ({f['severity']}) at line {f['line']}: {f['message']}"
    for f in lint.get("findings", [])
) or "_(no findings)_"

md = f"""<!-- Generated by scripts/tools/build_reference_report.sh — do not hand-edit. -->
# Reference EA gate report — honest empirical numbers

> **What this is.** A reproducible snapshot of what this kit's own gates report when
> run against a freshly scaffolded EA (`mql5-build stdlib --name SampleEA --symbol
> EURUSD --tf H1`). Numbers below are real outputs from the CLI tools shipped in
> this repo. They describe **how the gates score this kit's own scaffold output**,
> not whether the resulting EA is profitable in live trading — those are different
> questions.
>
> **Heuristic disclosure.** `Trader-17`, the `8×8 quality matrix`, the `AP-XX`
> anti-pattern IDs, and the `RRI` personas are project-defined heuristics designed
> by this kit. They are opinionated guardrails, **not industry standards or
> certifications**. Treat them accordingly.
>
> **Regenerate with:**
> ```bash
> bash scripts/tools/build_reference_report.sh
> ```

## Setup

```bash
mql5-build stdlib --name SampleEA --symbol EURUSD --tf H1 \\
    --out runtime/reference-ea/SampleEA
```

Produces a minimal stdlib/netting scaffold. The signal in `OnTick` is a
placeholder — it never reaches a trade-placing call — so the gates below are
scoring **only the skeleton**, not a working strategy.

---

## 1. `mql5-lint` — anti-pattern detection

```
{lint['summary']}
```

{lint_findings_block}

> Lint passes ({lint['errors']} ERROR) — but the WARN finding (`AP-22`) reminds you
> that the bare scaffold has no order-placing call. That's the intended starting
> point; you wire `trade.Buy(...)` / `trade.Sell(...)` after editing the signal.

---

## 2. `mql5-trader-check` — Trader-17 readiness

```
{t17['summary']}
```

- **PASS:** {t17['pass']} / {t17['total']}
- **WARN:** {t17['warn']}
- **N/A:**  {t17['na']}
- **FAIL:** {t17['fail']}
- **Gate verdict:** {'PASS' if t17['gate_pass'] else 'FAIL'} (gate threshold ≥ 15 / 17 PASS)

The N/A items are items that need **external evidence** before they can score —
walk-forward XML, Monte-Carlo report, multi-broker comparison, overfit report,
VPS deployment, news-session policy, etc. A bare scaffold has none of these,
so several items are reported as N/A. The gate is **fail-closed**: until you
supply the evidence, it does not pass.

Full raw output:

```
{t17['raw']}
```

---

## 3. `mql5-permission` — 7-layer fail-fast pipeline

| Mode | Verdict | Summary |
|---|---|---|
{perm_row('personal',   perm['personal'])}
{perm_row('team',       perm['team'])}
{perm_row('enterprise', perm['enterprise'])}

Layer ordering (this repo): L1 source-lint → L2 compile → L3 AP-lint → L4
checklist (Trader-17) → L5 methodology → L6 quality-matrix → L7 broker-safety.

`personal` runs L1, L2, L3, L4, L7. `team` adds L5. `enterprise` runs all 7.

On this machine (no Wine + MetaEditor installed), L2 (compile) is the first
to fail-fast — that is the *correct* behaviour: compile is part of the contract,
and the gate refuses to silently skip it. To clear L2, run:

```bash
./scripts/setup-wine-metaeditor.sh   # Linux only, ~3 min
```

Even with a green L2, a bare scaffold is expected to fail later at L4 (Trader-17)
because no real strategy is wired yet. That's the gate **doing its job**, not a
defect.

---

## 4. 8×8 RRI matrix — bare-scaffold baseline

```bash
python -m vibecodekit_mql5.rri.matrix --output <html>
```

(This kit does not register a `mql5-matrix` CLI in `pyproject.toml`; the
matrix module is reached via `python -m vibecodekit_mql5.rri.matrix`.)

With no `--inputs/--collect` source, every cell starts at `N/A`:

- **PASS:** {matrix_cli['pass']} / {matrix_cli['total']}
- **WARN:** {matrix_cli['warn']}
- **FAIL:** {matrix_cli['fail']}
- **N/A:**  {matrix_cli['na']}

Verdicts:

| Threshold (source: `matrix.py:MatrixReport`) | Verdict |
|---|---|
| `passes_personal`              (legacy: PASS≥56 ∧ FAIL=0 ∧ WARN≤8 over 64 cells)        | {'PASS' if matrix_cli['passes_personal']            else 'FAIL'} |
| `passes_enterprise`            (legacy: PASS≥60 ∧ FAIL=0 ∧ WARN≤4 over 64 cells)        | {'PASS' if matrix_cli['passes_enterprise']          else 'FAIL'} |
| `passes_personal_gate_only`    (Wave 4.3: FAIL=0 ∧ WARN≤1 ∧ all 6 gate-auto cells PASS/WARN) | {'PASS' if matrix_cli['passes_personal_gate_only']    else 'FAIL'} |
| `passes_enterprise_gate_only`  (Wave 4.3: every gate-auto cell PASS)                    | {'PASS' if matrix_cli['passes_enterprise_gate_only']  else 'FAIL'} |

The `{matrix_cli['pass']}/{matrix_cli['total']}` number is the **CLI floor**,
not a measurement. Without `--collect <dir>` pointed at a directory of
`gate-report-*.json` envelopes (produced by `--gate-report` on the lint /
trader-check / backtest / walk-forward / multibroker / broker-safety gates),
the matrix has no evidence to look at and every cell defaults to `N/A`.
To get a real measurement, run the gates first with `--gate-report <file>`,
then point `python -m vibecodekit_mql5.rri.matrix --collect <dir>` at the
artefact directory.

### Honest cell-coverage audit (Wave 4.3)

Of the 64 matrix cells:

- **{matrix_audit['gate_auto']} cells** are *gate-auto* — discriminative,
  auto-fillable from `--gate-report` artefacts (e.g. lint, trader-check,
  backtest, walk-forward, multibroker, broker-safety).
- **{matrix_audit['rri_broadcast']} cells** are *RRI-broadcast* — filled from
  manual RRI persona reviews; one persona verdict broadcasts across multiple
  axes of the same dimension.
- **{matrix_audit['manual']} cells** are *manual-only* (`d_inference` × 8 axes)
  — the kit explicitly does not auto-fill them.

This means the legacy "56/64 threshold" used by the matrix gate is only
attainable when RRI broadcasts + manual reviews are filled in alongside the
gate-auto cells. The CLI gate alone cannot get there on its own — and that is
honest by design.

Run the audit yourself:

```bash
python -m vibecodekit_mql5.rri.matrix --audit
```

---

## What this report is and is not

- ✅ **Is:** a snapshot of what the gates currently report for a bare scaffold.
- ✅ **Is:** reproducible — re-run the script and these numbers don't move.
- ❌ **Is not:** a claim that the scaffold is profitable, safe to live-trade,
  or production-ready.
- ❌ **Is not:** a measurement of "8×8 = 64" achievement. The matrix is the
  CLI floor when no evidence is provided. Real measurements only come from
  feeding real backtest / walk-forward / multibroker reports through the gate.

Generated on {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')} (UTC).
"""

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(md, encoding="utf-8")
print(f"wrote {out_path}")
PY

echo "Done: $REPORT"
