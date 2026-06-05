# Agent prompts — six personas + three actors, paste-and-run

> **Honest disclaimer.** The six personas, three actors, RRI step
> structure, and `super_actor`/`sub_personas`/`escalates_to` graph
> edges below are **project-defined heuristics** designed by this kit.
> They are opinionated workflow guardrails — not industry standards,
> not certifications, and not substitutes for trader judgement.

> **Wave 5.3 + Wave 6.1 + Wave 6.2 + Wave 6.2b.** This directory ships
> **six paste-and-run persona prompts** (Wave 5.3) + **three actor
> prompts** (Wave 6.1, under `actors/`) that turn a generic LLM chat
> (Claude Chat, ChatGPT, Cursor, Devin, …) into a focused, single-role
> assistant aligned with this kit's 8-step RRI methodology. Pair them
> with the Wave-5.1 deterministic generators (`mql5-vision-gen`,
> `mql5-blueprint-gen`, `mql5-tip-gen`), the Wave-5.2 sentinel-content
> validator, the Wave-6.1 contract/verify emitters
> (`mql5-contract-gen`, `mql5-verify-report`), the Wave-6.2
> task-graph / completion emitters (`mql5-task-graph-gen`,
> `mql5-completion-report`), and the Wave-6.2b escalation audit log
> (`mql5-escalation` + `mql5-permission-layer5 --enforce-no-open-escalation`)
> to get an honest **Homeowner / Contractor / Builder** role split
> (the Triangle of Power from VIBECODE Master v5.0) without inviting
> an LLM into the kit's hot path.

## Two layers — actors above personas (Wave 6.1)

The six Wave-5.3 personas are the **vocational layer** (specialist
skill: signal design, risk audit, MQL5 implementation, deploy, backtest,
end-user). Wave 6.1 introduces a **governance layer** above them — the
three actors of the Triangle of Power, mapping the metaphor used by
VIBECODE Master v5.0 (`Chủ nhà → Chủ thầu → Thợ thi công`).

| Actor (`actors/`) | Persona sub-roles (Wave 5.3) | Owns | Sign-off |
|---|---|---|---|
| [`chu-nha.md`](./actors/chu-nha.md) — Homeowner | `trader` | SCAN, VISION (decide), REFINE (decide) | APPROVED on blueprint, CONFIRM on contract |
| [`chu-thau.md`](./actors/chu-thau.md) — Contractor | `strategy-architect`, `risk-auditor` | VISION (design), BLUEPRINT, CONTRACT, TASK-GRAPH, VERIFY-REPORT, REFINE (propose) | Emits CHECKPOINT + CONFIRM blocks |
| [`tho-thi-cong.md`](./actors/tho-thi-cong.md) — Builder | `broker-engineer`, `devops`, `perf-analyst` | SCAN (execute), TIP execution, BUILD, VERIFY (run tools) | Emits Completion Reports + gate-reports |

Every Wave-5.3 persona frontmatter now carries a `super_actor:` field
binding it to one of the three actors. The schema test
(`tests/gates/phase-C/test_agent_prompts_schema.py`) verifies the
two-layer mapping is consistent (Contractor includes design specialists
only, Builder includes implementation specialists only, Homeowner is
the single human seat).

The kit deliberately does **not** call any LLM internally — every CLI
tool is deterministic. These prompts are for the operator's *external*
agent. They make the role split explicit so the human running the
session knows which persona is speaking at any given step.

## The six personas

| Prompt file | Persona | Review lens | Primary steps |
|---|---|---|---|
| [`strategy-architect.md`](./strategy-architect.md) | Strategy / quant author — owns the trading hypothesis | `ceo`, `investigate` | SCAN, RRI, VISION, REFINE |
| [`broker-engineer.md`](./broker-engineer.md) | Senior MQL5 implementer — owns the code | `eng` | BLUEPRINT, TIP, BUILD, VERIFY |
| [`risk-auditor.md`](./risk-auditor.md) | Compliance / risk officer — signs off on exposure | `cso` | RRI, BLUEPRINT, VERIFY |
| [`devops.md`](./devops.md) | Deploy / VPS / observability engineer | `eng` | BUILD, VERIFY, REFINE |
| [`perf-analyst.md`](./perf-analyst.md) | Backtest + tester analyst | `investigate` | VERIFY, REFINE |
| [`trader.md`](./trader.md) | End-user (the **owner** in homeowner / contractor / worker metaphor) | `ceo` | SCAN, VISION, VERIFY |

## How to use an actor prompt (Wave 6.1)

The Homeowner is **the human running the session** — read
`actors/chu-nha.md` once as training, then play yourself. The other two
are LLM seats:

1. Open **Claude Chat / GPT-4 / Cursor Ask** and paste `actors/chu-thau.md`
   verbatim into the system message slot. This LLM instance is now the
   Contractor and is bound by `forbidden_tools` (no `mql5-auto-build`,
   no `mql5-compile`, etc.).
2. Open **Claude Code / Devin Implementation / Cursor Edit** and paste
   `actors/tho-thi-cong.md` verbatim into the system message slot. This
   LLM instance is now the Builder and is bound by `forbidden_tools`
   (no `mql5-vision-gen`, no `mql5-blueprint-gen`, etc.).
3. As Homeowner, you copy-paste artefacts between the two seats:
   - SCAN Report + ea-spec.yaml + RRI answers → Contractor seat
   - `tasks/TIP-NNN.md` → Builder seat (one TIP at a time, follow the
     `task-graph.md` DAG roots-first)
   - `completions/completion-NNN.md` → Contractor seat (BLOCKED rows
     trigger escalation back to the Contractor)
   - Verify Report + REFINE options → you decide.
4. At Step 4 you reply `APPROVED by <name> at <YYYY-MM-DD>` at the
   bottom of `step-4-blueprint.md`. At Step 4.5 you reply
   `CONFIRM by <name> at <YYYY-MM-DD>` at the bottom of `contract.md`.
   The sign-off sentinel (`mql5-permission --layer 5 --enforce-sign-off`)
   will FAIL if either line is missing.
5. After Step 4.5 the Contractor runs `mql5-task-graph-gen
   contract.md --out-dir .` to expand the contract into per-TIP files
   plus a Mermaid DAG (Wave 6.2). Pick TIPs roots-first using
   `task-graph.md` so dependencies are always satisfied before the
   Builder starts.
6. When the Builder finishes a TIP, they run `mql5-completion-report
   --tip tasks/TIP-NNN.md --gate-reports reports/TIP-NNN/ --out
   completions/completion-NNN.md --file ... --test ... [--issue ...]`
   to emit a per-TIP STATUS / Files / Tests / Issues / Gate Reports
   rollup (Wave 6.2). The Contractor's `mql5-verify-report
   --completion-dir completions/` picks the resulting files up at
   Step 7.
7. If any actor needs input from another to proceed, they raise an
   escalation with `mql5-escalation --from <actor> --to <actor>
   --level {1,2,3} --reason <text> [--artefact <path>]` (Wave 6.2b).
   Level 3 escalations block TEAM / ENTERPRISE gates while OPEN — the
   Homeowner enables the hook by adding `--enforce-no-open-escalation`
   to the layer-5 gate. The receiving actor closes the loop with
   `mql5-escalation --resolve <id> --resolved-by <actor> [--note <text>]`.
   The append-only log lives at `.mql5-audit/escalations.jsonl` so the
   audit trail composes with normal git workflows.

## How to use a persona prompt (Wave 5.3, still valid)

The six persona prompts remain useful for **finer-grained sub-role
switching inside one actor seat** — e.g., the Contractor LLM can re-prime
itself with `risk-auditor.md` for a compliance review then swap to
`strategy-architect.md` for a signal refinement. Use them like this:

1. Pick the persona you want the LLM to adopt for the next session
   (or for the next handoff segment of a longer task).
2. Open the matching `.md` file and copy **the whole file** —
   frontmatter included.
3. Paste it as the **system / opening message** in your LLM chat.
4. Provide the input artefacts listed under `inputs:` (e.g. paste the
   `step-2-rri.md` content for the architect, the `ea-spec.yaml` for
   the engineer, etc.).
5. Ask the agent to do exactly one thing the persona owns at the
   current step (see "Step-by-step responsibilities" inside each
   prompt). When the persona has finished, switch prompts before
   moving to the next step — do not let one persona impersonate
   another.

## How these prompts relate to the kit's CLI surface

* The Wave-5.1 generators (`mql5-vision-gen`, `mql5-blueprint-gen`,
  `mql5-tip-gen`) emit *deterministic* step outputs from the prior
  step's artefact — they are the **scaffolding** that the persona's
  LLM then refines (filling in narrative, prioritising invariants,
  selecting modules, writing rationales). The persona never replaces
  the generator; it edits the generator's output.
* The Wave-5.2 sentinel-content validator (`mql5-permission-layer5
  --enforce-activities`) is the kit's enforcement layer. A persona is
  not "done" with a step until the matching `step-N-<name>.md` has
  enough ticked `## Activities` checkboxes to pass the per-mode
  threshold (`personal ≥ 50%`, `team ≥ 80%`, `enterprise = 100%`).
* The four review lenses (`mql5-review --lens
  {eng,ceo,cso,investigate}`) map onto the personas as shown in the
  table above. Use the lens after the persona's step is done to
  cross-check.

## Forbidden in every persona

These rules from `AGENTS.md` are baked into every prompt — the persona
is told not to do these things, even if the operator asks. Removing
them re-creates the failure modes the kit was forked to fix.

- Do **not** propose a master router, `query_loop.py`,
  `intent_router.py`, or `pipeline_router.py`. Every command is a
  flat `python -m vibecodekit_mql5.<name>`.
- Do **not** propose adding an LLM client inside the kit. The kit is
  deterministic; LLM authorship happens externally.
- Do **not** propose `OrderSend` without `CPipNormalizer`, async
  sends without `OnTradeTransaction`, `WebRequest` inside
  `OnTick/OnTimer`, or hardcoded magic numbers.
- Do **not** claim a test passed without a real Strategy Tester XML
  report or `mql5-bt-sim` artefact to back it.
- Do **not** skip the 7-layer permission gate in `team` or
  `enterprise` mode.

## Frontmatter schema

Every prompt file starts with a YAML block exposing machine-readable
metadata. The schema is intentionally minimal so a script can list,
filter, or cross-check the prompts without parsing prose:

```yaml
persona: <slug matching docs/rri-personas/*.yaml>
role: <one-line role description>
review_lens: <eng|ceo|cso|investigate>      # primary lens
owns_steps: [<step slug>, …]                 # steps this persona drives
contributes_steps: [<step slug>, …]          # steps this persona supports
peers: [<persona slug>, …]                   # other personas to coordinate with
inputs: [<artefact path>, …]                 # what must be on the desk
outputs: [<artefact path>, …]                # what the persona produces
forbidden:                                   # role-specific don'ts
  - <free-text bullet>
```

The schema is pinned by
`tests/gates/phase-C/test_agent_prompts_schema.py`. Adding a new
persona prompt requires extending the test's allow-list.

---

## Tiếng Việt — chia vai trò "chủ nhà / thầu / thợ"

Sáu prompt này là phần **vai trò người** của Wave 5.3, đi kèm các
generator deterministic của Wave 5.1 (máy điền sẵn step output) và
sentinel validator của Wave 5.2 (máy kiểm tra checkbox).

Mỗi prompt biến một LLM chat (Claude Chat, ChatGPT, Cursor, Devin,…)
thành đúng một vai cụ thể trong 8-bước RRI:

| File prompt | Vai trò | Lens review | Step chính |
|---|---|---|---|
| `strategy-architect.md` | Kiến trúc sư chiến lược (quant) — chủ giả thuyết giao dịch | `ceo`, `investigate` | SCAN, RRI, VISION, REFINE |
| `broker-engineer.md` | Kỹ sư MQL5 — chủ code | `eng` | BLUEPRINT, TIP, BUILD, VERIFY |
| `risk-auditor.md` | Compliance / risk officer — ký duyệt rủi ro | `cso` | RRI, BLUEPRINT, VERIFY |
| `devops.md` | Kỹ sư deploy / VPS / observability | `eng` | BUILD, VERIFY, REFINE |
| `perf-analyst.md` | Phân tích backtest + tester | `investigate` | VERIFY, REFINE |
| `trader.md` | End-user — "chủ nhà" trong ẩn dụ chủ-nhà/thầu/thợ | `ceo` | SCAN, VISION, VERIFY |

Cách dùng: chọn 1 prompt, **copy toàn bộ file** (cả frontmatter), paste
làm system / opening message trong LLM chat, đính kèm các artefact ở
mục `inputs:`, rồi yêu cầu agent làm đúng một việc thuộc vai đó. Khi
xong, **đổi prompt** trước khi sang step mới — không để một persona
giả mạo persona khác.

Kit **không** gọi LLM nào trong CLI. Persona là chuyện của agent
ngoài; CLI vẫn deterministic 100%.
