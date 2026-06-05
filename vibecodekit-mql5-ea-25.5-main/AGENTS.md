# Agent Operating Guide

This file is the entrypoint for AI coding agents (Devin, Claude Code,
Codex, Cursor) working inside `vibecodekit-mql5-ea`. It tells you what
to read first, what to use, and what NOT to introduce.

> **Honest disclaimer.** `Trader-17`, the `8×8 quality matrix`, the
> `AP-1…AP-25` anti-pattern IDs, the 7-layer permission pipeline, the
> Wave-5.3 personas, and the Wave-6.1 Triangle-of-Power actors are
> **project-defined heuristics** designed by this kit. They are
> opinionated guardrails — not industry standards, not certifications,
> and not substitutes for live-account validation. Treat them as such.

## Project Snapshot

- **What it is:** a methodology kit for building production-grade MQL5
  Expert Advisors on MetaTrader 5. Router-free, fail-fast, deterministic.
- **Status:** shipped product, `v1.6.1`. 69 CLI commands (59 standalone +
  10 Wave-3 aliases delegating to 2 umbrellas: `mql5-review --lens` and
  `mql5-rri <subcommand>`), 4 MCP servers, 23 scaffold archetypes, 26
  anti-pattern detectors (25 numbered AP-1…AP-25 + 1 build-aware
  method-hiding) pinned by a 20-EA golden dataset under
  `tests/fixtures/ea-bugs/`, lightweight MQL5 AST parser POC under
  `scripts/vibecodekit_mql5/ast_parser/` retrofitting AP-1/2/7 behind
  `mql5-lint --use-ast`, in-process Python tick-bar simulator
  `mql5-bt-sim` emitting MT5-compatible XML for hermetic backtests,
  Wave-4.3 cell-coverage audit on the 8×8 RRI matrix
  (`python -m vibecodekit_mql5.rri.matrix --audit`) with gate-only
  verdicts, **Wave-5.1 deterministic step-output generators**
  (`mql5-vision-gen`, `mql5-blueprint-gen`, `mql5-tip-gen`) +
  **Wave-5.2 sentinel-content validator** hooked into Layer-5 via
  `mql5-permission-layer5 --enforce-activities`, **Wave-5.3 six
  paste-and-run persona prompts** under `docs/agent-prompts/`,
  **Wave-6.1 Triangle of Power governance layer** — three
  `docs/agent-prompts/actors/{chu-nha,chu-thau,tho-thi-cong}.md`
  prompts wrapping the six Wave-5.3 personas, two new emitter CLIs
  (`mql5-contract-gen`, `mql5-verify-report`), and a
  `mql5-permission-layer5 --enforce-sign-off` audit that pins the
  manual `APPROVED` / `CONFIRM` ritual on blueprint + contract,
  **Wave-6.2 Task Graph + Completion Report** emitters
  (`mql5-task-graph-gen` expands a signed contract into a per-TIP
  Mermaid DAG + `tasks/TIP-001..N.md` files; `mql5-completion-report`
  emits a per-TIP `STATUS / Files / Tests / Issues / Gate Reports`
  rollup the Contractor's `mql5-verify-report --completion-dir` picks
  up), **Wave-6.2b actor-to-actor escalation audit log**
  (`mql5-escalation --from <actor> --to <actor> --level {1,2,3}` raises
  an append-only record in `.mql5-audit/escalations.jsonl`;
  `mql5-escalation --list` / `--resolve <id>` query and close the log;
  `mql5-permission-layer5 --enforce-no-open-escalation` blocks TEAM /
  ENTERPRISE gates while any level-3 escalation is still OPEN),
  7-layer permission gate, 1494+ gate tests (1499 collected; 1 Wine-only
  MetaEditor compile probe and 4 platform-specific skips).
- **License:** MIT.

## Source Of Truth (read in this order)

1. `README.md` — feature inventory + quickstart.
2. `docs/QUICKSTART.md` — 10-minute clone-to-compile.
3. `docs/COMMANDS.md` — every CLI command (69) grouped by lifecycle stage.
4. `docs/USAGE-en.md` / `docs/USAGE-vi.md` — full per-command reference.
5. `docs/USER-GUIDE-en.md` / `docs/USER-GUIDE-vi.md` — step-by-step walkthroughs.
6. `docs/anti-patterns-AVOID.md` — architectural anti-patterns the kit avoids; technical detectors (25 numbered AP-1…AP-25 + 1 build-aware method-hiding = 26 total) live in `scripts/vibecodekit_mql5/lint.py` + `lint_best_practice.py` + `method_hiding_check.py`.
7. `docs/PLAN-v5.md` — historical plan + design principles (v5 ADD/DROP list).
8. `docs/phase-{0,A,B,C,D,E}-spec.md` — phase-by-phase delivery contract.
9. `docs/references/50-survey.md … 80-input-syntax.md` — 29 cheatsheets.
10. `docs/rri-personas/` + `docs/rri-templates/` — RRI methodology.
11. `docs/agent-prompts/` — six paste-and-run persona prompts (Wave 5.3,
    `strategy-architect.md`, `broker-engineer.md`, `risk-auditor.md`,
    `devops.md`, `perf-analyst.md`, `trader.md`). Use these to make an
    external LLM chat adopt exactly one role per step. Schema pinned
    by `tests/gates/phase-C/test_agent_prompts_schema.py`.
12. `docs/agent-prompts/actors/` — three Wave-6.1 actor prompts
    (`chu-nha.md` = Homeowner, `chu-thau.md` = Contractor,
    `tho-thi-cong.md` = Builder). These are the governance layer
    above the six Wave-5.3 personas; each persona has a
    `super_actor:` field binding it to its parent actor. Schema
    pinned by `tests/gates/phase-C/test_actor_prompts_schema.py`.

## What you may change directly

- New CLI commands under `scripts/vibecodekit_mql5/` with a matching
  `[project.scripts]` entry in `pyproject.toml` and tests under
  `tests/gates/phase-{0,A,B,C,D,E}/`.
- New Include headers in `Include/*.mqh` (must compile under MetaEditor
  build ≥ 5260 — see `mql5-method-hiding-check`).
- New scaffold archetypes under `scaffolds/<preset>/<stack>/` with an
  `EAName.mq5` template. `mql5-doctor` auto-discovers every
  `<preset>/<stack>` pair on disk via `discover_scaffolds()` — no
  code edit to `REQUIRED_SCAFFOLDS` is needed. Add a matching scaffold
  test under `tests/gates/phase-D/test_scaffold_*` and a
  `FLOW-vi.md` narrative for `mql5-ea-docs`.
- New anti-pattern detectors in `scripts/vibecodekit_mql5/lint.py` or
  `scripts/vibecodekit_mql5/lint_best_practice.py` with regression tests.
- Documentation under `docs/`.
- Docs templates under `docs/templates/` for the LLM-driven `.docx`
  ship pipeline (`mql5-docs-bundle` + `mql5-docs-assemble`) — these
  must stay **kit-light**: do not hardcode per-archetype chapter
  content. Variation is the LLM agent's job; the kit only emits the
  deterministic context payload.

## What you must NOT introduce

These are deliberately rejected. Adding any of them re-creates the
failure modes the kit was forked from `vibecodekit-handwritten` to fix:

- A master `/mql5` router, `query_loop.py`, `intent_router.py`, or
  `pipeline_router.py`. Every command is a flat `python -m
  vibecodekit_mql5.<name>` that stands alone.
- `OrderSend` without `CPipNormalizer`-aware pip math (broker JPY/XAU
  asymmetry breaks; see `Include/CPipNormalizer.mqh`).
- `OrderSendAsync` without `OnTradeTransaction` (AP-18 catches it).
- `WebRequest` inside `OnTick` / `OnTimer` (AP-17).
- Hardcoded magic numbers — use `CMagicRegistry.Reserve()` (Plan v5 §6
  reserves `70000–79999`).
- LLM hallucination of test results. Every "passes" claim must be
  traceable to a real Strategy Tester XML report.
- Skipping the 7-layer permission gate in TEAM / ENTERPRISE mode.
- Hardcoded per-EA chapter content inside `docs_bundle` /
  `docs_assemble`. The LLM-driven `.docx` pipeline is intentionally
  archetype-agnostic — chapter structure is decided adaptively by the
  external LLM agent based on `docs-context.json`. Per-archetype
  `STRATEGY.yaml` files, hardcoded 10-chapter templates, and embedded
  matplotlib chart generators are **out of scope** for this kit.
- An LLM API client inside the kit. `mql5-docs-bundle` emits a prompt
  and the operator's external agent (Devin / Claude / Cursor) does the
  authoring step. The kit never calls a model directly.

## Agent Contracts (Wave 1)

Twelve gates ship a stable `--json` envelope (`schema_version=1`) on
stdout — schema and helpers live in `scripts/vibecodekit_mql5/_agent_io.py`.
The same gates support `--gate-report <path>` to also persist the
envelope to disk; `python -m vibecodekit_mql5.rri.matrix --collect <dir>`
then auto-fills the 8×8 quality matrix from those artefacts. Of the 64
cells, only **6** are discriminatively auto-fillable from gate reports
— see Wave 4.3 below. `mql5-lint` and
`mql5-method-hiding-check` additionally accept `--format sarif` (SARIF
2.1.0). For machine-readable discovery of the full CLI surface, run
`mql5-manifest --emit > manifest.json`. The repo's checked-in
`manifest.json` is regenerated from `pyproject.toml` and pinned by
`tests/gates/phase-A/test_manifest_generation.py`.

For hermetic Phase-B testing on Linux without Wine, use
`mql5-fixture --type {backtest,walkforward,monte-carlo,multibroker}
--strategy {random,trend,mean-rev} --seed N --out <dir>` to generate
synthetic MT5 Strategy Tester XML / CSV / journal artefacts that the
backtest / walkforward / monte-carlo / multibroker parsers accept
unchanged. Tests for this loop live under
`tests/gates/phase-B/test_fixture_generator.py`.

## Agent Contracts (Wave 3)

Wave 3 consolidated the review/RRI CLI surface and added a hermetic
forge iteration loop:

* **Review umbrella** —
  `mql5-review --lens {eng,ceo,cso,investigate}` is the new canonical
  entry-point. `mql5-eng-review`, `mql5-ceo-review`, `mql5-cso`, and
  `mql5-investigate` keep working as thin aliases. Legacy
  `--persona/--step` single-persona dispatch is preserved.
* **RRI umbrella** — `mql5-rri {template,bt,rr,chart}` is the new
  canonical entry-point. `mql5-rri-bt`, `mql5-rri-rr`, `mql5-rri-chart`
  keep working as thin aliases. `mql5-rri` with no subcommand still
  prints the Step-2 template (legacy default).
* **EA-bug golden dataset** — `tests/fixtures/ea-bugs/ap_NN_*/EA.mq5`
  + `expected.json` pins the lint detector contract. The driver lives
  at `tests/gates/phase-A/test_ea_bugs_golden_dataset.py`.
* **`mql5-forge-loop`** — Wave-3 hermetic CI loop. Chains the Wave-2
  fixture generator into the Wave-1 backtest parser for N deterministic
  iterations. Emits a per-iter `forge-loop-report.json` + Wave-1
  envelope. No Wine, no MetaTester.

## Agent Contracts (Wave 2)

- `mql5-init` is a 5-question interactive bootstrap wizard that emits
  `ea-spec.yaml` (the same artefact `mql5-auto-build --spec` consumes).
  It exposes `--non-interactive`, `--from-answers <yaml>`,
  `--list-presets`, and the standard `--json` envelope. Use it as the
  one-shot newcomer entry-point; the `README.md` 30-second quickstart
  pipes its output into `mql5-auto-build --draft`.
- `--draft` is a kit-wide flag on `mql5-lint`, `mql5-trader-check`,
  `mql5-permission`, and `mql5-auto-build`. It downgrades every
  finding to a non-blocking warning and exits 0, but the JSON envelope
  still records `data.original_ok` so the chat-driven build loop can
  inspect what would have failed. Distinct from `mql5-doctor --soft`
  (which only relaxes *environment* probes). The two flags compose.

## Agent Contracts (Wave 5)

Wave 5 expands the role-based pipeline by giving step 3 / 4 / 5 of the
8-step RRI methodology proper generator tools (previously
template-renderers only) and by making layer-5 of the permission gate
content-aware:

* **`mql5-vision-gen <step-2-rri.md>`** — parses the Step-2 RRI artefact
  for `## Constraints` + `- [x] persona::q-id` lines and emits a
  ``step-3-vision.md`` skeleton with Scope / Active personas filled and
  Timeline / Risk register left as TODO. No LLM call.
* **`mql5-blueprint-gen <ea-spec.yaml>`** — emits a
  ``step-4-blueprint.md`` (module diagram + state machine + per-preset
  invariants table) deterministically keyed by the preset/stack pair.
  ``--vision <step-3-vision.md>`` fuses scope from the prior step.
* **`mql5-tip-gen <step-4-blueprint.md>`** — parses the Step-4 Invariants
  + Module-diagram blocks and emits a ``step-5-tip.md`` with a
  per-module table + invariant → module × test coverage matrix. Test
  names are pytest-compatible snake_case identifiers.
* **Sentinel-content validator** — ``mql5-permission-layer5
  --enforce-activities`` (or ``layer5_methodology.gate(...,
  enforce_activities=True)``) audits each step output for ticked
  ``## Activities`` checkboxes and fails the gate when the ratio is
  below the per-mode threshold (`personal` ≥ 50% / `team` ≥ 80% /
  `enterprise` 100%). Closes the "touch the sentinel without filling
  the template" loophole.

The Wave-5 generators emit the Wave-1 `--json` envelope and accept
`--gate-report <path>` like any other tool, BUT they intentionally OMIT
`matrix_dim/axis` so the W1.4 matrix collector does not bind them to a
non-`gate_auto` cell. They are emitters, not gates.

## Task Loop

For every coding task:

1. Read the relevant doc(s) from the source-of-truth list above.
2. Run `mql5-doctor` (or `mql5-doctor --soft` on docs-only environments
   without Wine) and confirm the kit imports cleanly.
3. Make the smallest change that satisfies the request. Match the
   surrounding code style.
4. Add or update tests in the matching `tests/gates/phase-*` folder.
5. Run lint + tests locally before pushing:
   ```bash
   ruff check scripts mcp
   python -m pytest tests/gates -q
   ```
6. When changing CLI behavior, update `docs/COMMANDS.md` and the
   matching USAGE section.
7. PR description must mention which anti-pattern detector(s) cover the
   change, if any.

## Build / Verify Pipeline (cheat sheet)

```bash
# Free text → ea-spec.yaml → scaffold + lint + compile + dashboard + docs
mql5-spec-from-prompt "build EA trend EURUSD H1 risk 0.5%" --out ea-spec.yaml
mql5-auto-build --spec ea-spec.yaml --out-dir build/FirstEA

# Verify-only (skip compile / gate on Linux without Wine):
mql5-auto-build --spec ea-spec.yaml --out-dir build/FirstEA --no-compile --no-gate

# Lint + Trader-17 + 7-layer permission gate:
mql5-lint FirstEA.mq5
mql5-trader-check FirstEA.mq5
mql5-permission --mode personal FirstEA.mq5
```

## Rule ID → documentation table

### Anti-patterns (AP-1…AP-25) — emitted by `mql5-lint`

The 8 critical detectors live in `scripts/vibecodekit_mql5/lint.py`; the
17 best-practice WARN detectors live in
`scripts/vibecodekit_mql5/lint_best_practice.py`; the build-aware
method-hiding detector lives in
`scripts/vibecodekit_mql5/method_hiding_check.py`.

| Rule | Severity | Description | See |
|---|---|---|---|
| AP-1 | ERROR | Trade opened without stop-loss | `docs/anti-patterns-AVOID.md`, `docs/references/79-pip-norm.md` |
| AP-3 | ERROR | Hardcoded `lot = 0.01` literal | `docs/anti-patterns-AVOID.md` |
| AP-5 | ERROR | More than 6 `input` declarations | `docs/anti-patterns-AVOID.md` |
| AP-15 | ERROR | Raw `OrderSend(` instead of `CTrade` | `docs/anti-patterns-AVOID.md` |
| AP-17 | ERROR | `WebRequest()` inside `OnTick` / `OnTimer` | `docs/anti-patterns-AVOID.md` |
| AP-18 | ERROR | `OrderSendAsync` without `OnTradeTransaction` | `docs/anti-patterns-AVOID.md` |
| AP-20 | ERROR | Hardcoded pip (`* 0.0001`, `* _Point`, `* Point()`) | `docs/references/79-pip-norm.md` |
| AP-21 | WARN  | `// digits-tested:` meta with only one broker class | `docs/references/79-pip-norm.md` |
| AP-2 | WARN | SL too tight (< spread + commission) | `docs/anti-patterns-AVOID.md` |
| AP-4 | WARN | Martingale without `max_orders` cap | `docs/anti-patterns-AVOID.md` |
| AP-6 | WARN | Optimizer-curve-fitted code smell | `docs/anti-patterns-AVOID.md` |
| AP-7 | WARN | Hardcoded magic number (use `CMagicRegistry`) | `docs/anti-patterns-AVOID.md` |
| AP-8 | WARN | No spread guard | `docs/anti-patterns-AVOID.md` |
| AP-9 | WARN | Multi-entry on same bar | `docs/anti-patterns-AVOID.md` |
| AP-10 | WARN | `OrderSend` without retcode / retry | `docs/anti-patterns-AVOID.md` |
| AP-11 | WARN | Mode-blind (no netting/hedging branch) | `docs/anti-patterns-AVOID.md` |
| AP-12 | WARN | Indicator-handle leak (no `IndicatorRelease`) | `docs/anti-patterns-AVOID.md` |
| AP-13 | WARN | Broker-coupled (hardcoded broker name string) | `docs/anti-patterns-AVOID.md` |
| AP-14 | WARN | No MFE / MAE logging | `docs/references/59-trader-checklist.md` |
| AP-16 | WARN | Reinventing stdlib include (`CTrade`, `CSymbolInfo`, …) | `docs/anti-patterns-AVOID.md` |
| AP-19 | WARN | ONNX usage without Strategy-Tester validation | `docs/anti-patterns-AVOID.md` |
| AP-22 | WARN | Signal placeholder — `OnTick` reaches no order call | `docs/anti-patterns-AVOID.md` |
| AP-23 | WARN | `CTrade` call without retcode check | `docs/anti-patterns-AVOID.md` |
| AP-24 | WARN | History not synchronized before read | `docs/anti-patterns-AVOID.md` |
| AP-25 | WARN | Raw `delete` without nullity guard | `docs/anti-patterns-AVOID.md` |

> **Honest note.** AP-5's "> 6 inputs = overfit" rule is a project
> default, not an industry threshold. Grid / portfolio / DCA EAs
> legitimately need more parameters. To override, edit the threshold in
> `scripts/vibecodekit_mql5/lint.py` via PR (the kit deliberately ships
> no per-file disable mechanism).

### Trader-17 checklist (T01–T17) — emitted by `mql5-trader-check`

See `docs/references/59-trader-checklist.md` for the full list. The
gate requires ≥ 15 / 17 PASS. Items that need external evidence
(walk-forward XML, Monte-Carlo report, multi-broker comparison, overfit
report, VPS deployment, news-session policy) report `N/A` on a fresh
scaffold and are not counted toward PASS until you supply that
evidence.

### Permission pipeline layers — emitted by `mql5-permission`

Layer order is L1 source-lint → L2 compile → L3 AP-lint → L4 checklist
(Trader-17) → L5 methodology (Wave-5.x activities + Wave-6.x sign-off)
→ L6 quality-matrix (8×8) → L7 broker-safety. `personal` runs `1, 2,
3, 4, 7`; `team` adds `5`; `enterprise` runs all `1–7`. See section
[Agent Contracts (Wave 1)](#agent-contracts-wave-1) for the JSON
envelope shape every layer emits.

## Reference numbers — honest empirical snapshot

When this kit's gates run against a **freshly scaffolded EA** (no
strategy written yet — `mql5-build stdlib --name SampleEA --symbol
EURUSD --tf H1`), the kit reports:

| Gate | Result on bare scaffold |
|---|---|
| `mql5-lint` | `0 ERROR, 1 WARN` (AP-22 placeholder OnTick) |
| `mql5-trader-check` | `6 / 17 PASS, 3 WARN, 8 N/A, 0 FAIL` → **FAIL** (gate ≥ 15) |
| `mql5-permission --mode personal` | **FAIL** at layer 2 (compile, when no Wine) |
| `mql5-permission --mode team` | **FAIL** at layer 2 (fail-fast: L3–L7 not run) |
| `mql5-permission --mode enterprise` | **FAIL** at layer 2 (fail-fast: L3–L7 not run) |
| `mql5-matrix` (no `--collect`) | `0 / 64 PASS` — CLI floor, not a measurement |
| `python -m vibecodekit_mql5.rri.matrix --audit` | `6 gate-auto + 50 rri-broadcast + 8 manual = 64` |

A bare scaffold is **expected to fail** the permission gate — the gate
has teeth and demands real evidence (working strategy + walk-forward +
multi-broker + Monte Carlo + overfit check) before passing. See
[`docs/reference-ea/REPORT.md`](docs/reference-ea/REPORT.md) for the
raw outputs and the regenerator script.

## Environment

- Python ≥ 3.10, `pip install -e .` (now pulls `pyyaml` by default; install
  `.[dev]` for `pytest` + `ruff`).
- Wine 8.0.2 + MetaEditor: `./scripts/setup-wine-metaeditor.sh` on Linux.
  Not required for lint / docs / unit tests.
- `MetaTrader5` Python package: Windows / Wine only. The `mt5-bridge`
  MCP server falls back to deterministic stubs on Linux without it.

---

## Tiếng Việt — tóm tắt cho agent

- `vibecodekit-mql5-ea` là kit xây EA MQL5 production-grade, `v1.6.1`,
  69 lệnh CLI (59 standalone + 10 alias Wave-3 quy về 2 umbrella:
  `mql5-review --lens` và `mql5-rri <subcommand>`), 4 MCP server, 23
  scaffold, 26 AP detector (25 đánh số AP-1…AP-25 + 1 method-hiding theo
  build) găm bởi 20-EA golden dataset, AST parser POC (`ast_parser/`,
  bật bằng `mql5-lint --use-ast`) + Python tick-bar simulator
  (`mql5-bt-sim`), audit cell-coverage cho ma trận RRI 8×8
  (`python -m vibecodekit_mql5.rri.matrix --audit`, Wave 4.3 — 6 cell
  gate-auto + verdict gate-only riêng), **Wave-5.1 bộ sinh step output
  deterministic** (`mql5-vision-gen` / `mql5-blueprint-gen` /
  `mql5-tip-gen`) + **Wave-5.2 sentinel content validator** gắn vào
  Layer-5 (`mql5-permission-layer5 --enforce-activities`), **Wave-5.3
  6 prompt persona** + **Wave-6.1 Tam giác quyền lực** (3 actor +
  `mql5-contract-gen` + `mql5-verify-report` + `--enforce-sign-off`)
  + **Wave-6.2 Task Graph + Completion Report** (`mql5-task-graph-gen`
  + `mql5-completion-report`) + **Wave-6.2b log escalation actor-to-actor**
  (`mql5-escalation --from … --to … --level {1,2,3}` ghi
  `.mql5-audit/escalations.jsonl`; `mql5-permission-layer5
  --enforce-no-open-escalation` chặn gate TEAM/ENTERPRISE khi còn L3 OPEN),
  1494+ gate test (1499 collected; 1 probe MetaEditor compile cần Wine
  và 4 skip phụ thuộc nền tảng).
- Bắt đầu từ `README.md` → `docs/QUICKSTART.md` → `docs/COMMANDS.md`.
  Tham khảo song ngữ ở `docs/USAGE-vi.md` + `docs/USER-GUIDE-vi.md`.
- Mọi lệnh đứng độc lập (`python -m vibecodekit_mql5.<name>`). **Không**
  thêm master router, `query_loop`, `intent_router`, `pipeline_router`.
- Mọi EA bắt buộc dùng `CPipNormalizer` (broker math) + `CMagicRegistry`
  (magic 70000-79999) + stop-loss mỗi lệnh + 7-layer permission gate.
- Trước khi commit: `ruff check scripts mcp` + `pytest tests/gates -q`.
  Trên môi trường không có Wine, dùng `mql5-doctor --soft`.
