# Customer-Ready BRICK — Goal Phases Index — 0629

Status: support evidence only (operator index). Not source truth / success / Movement authority.
THE phase index: each phase → its detail doc. Goal-of-record (full spec) =
`customer-ready-goal-current-definition-0627.md`. Consolidation / audit / decisions / standard shapes
= `customer-ready-plan-audit-roadmap-0629.md`. Browse: the `GOAL/` folder carries P0–P8 symlinks to the detail docs below.

## Goal (one line)
A customer installs BRICK, connects their LLMs, says `make X`; an AGENT (COO) drives the official
`brick build` route (Brick / Agent / Link) and returns artifact + evidence. Final proof = self-dogfood
through that same customer path.

## GOAL PROMPT (operator discipline — must survive context compression)
```
GOAL: customer installs BRICK -> connects LLMs -> says `make X`. YOU (operator) drive the official
`brick build` route; Brick/Agent/Link declare the work, performers run it, evidence returns.
Final proof = BRICK self-dogfoods that same customer path.

YOU = OPERATOR / COO (never a worker lane):
- You JUDGE — define the dev decomposition from the design; disposition closure (forward/reroute).
  Judgment is yours, never auto-pilot.
- You do NOT become the worker. Implementation/QA/closure run through Building Agents.
- Claude/Codex/Gemini output = support evidence ONLY — never source truth / success / quality / Movement.

OFFICIAL ROUTE ONLY: implementation/QA/closure go through `brick build` -> cli/driver -> Builder ->
declared Building Plan -> run.py/walker -> evidence. No bypass (no direct build()/helper/hand-runner
calls; no operator-injected return-shape/ref/carry).

WHEN SOMETHING IS WRONG — think in AXES, not in modules:
 1. ASK WHICH AXIS first — Brick (work contract/template/plan/return-shape/graph) · Agent (performer/
    policy/capability/receipt/AgentFact) · Link (Movement/target/carry/gate/reroute).
    NOT "patch the nearest visible support noun."
 2. FIND YOUR OWN ERROR FIRST — is it your operating mistake or a contaminated measurement (wrong HOME/
    env), not a code defect? Re-measure in the REAL environment before calling it a bug.
 3. CHECK IT ALREADY EXISTS — the mechanism is probably already built; FIND it before adding anything.
 4. DERIVE THE REAL FIX — root cause; fix size = cause size. NO band-aid, NO module proliferation, NO
    feature-adding reflex. Prefer SIMPLIFY / DELETE over add — the complexity itself makes the holes.
 5. PER THE 3-AXIS CONSTITUTION — support records FACTS, judges nothing. Sufficiency + Movement = Link
    gate. Quality + success = human. Brick = WHAT, Agent = WHO/HOW, Link = Movement.

MEASURE, DON'T INFER. Execution results only, in the real environment. Verify your own output
adversarially before committing.
```

## Success judgment (how EVERY phase is judged)
Success is **MEASURED, never claimed.** A phase PASSES only when ALL of:
1. `check_profile.py --all` GREEN with the **REAL HOME** (never `HOME=$(mktemp -d)`), AND
2. the phase's PASS criteria below are met **end-to-end** (not slice-claims, not "the record says done"), AND
3. for a Building: `frontier_kind=="complete"` (read from `--json`) or `brick verify` exit 0 — **NOT** `brick build`'s exit 0 (that is intentional 3-axis and judges nothing), AND
4. the **COO (Claude) dispositions it forward** after adversarial self-verify.
Support records FACTS; the COO/human JUDGES. "CR record/audit" commits are not proof.

## Phases — progress in this ORDER (each → `GOAL/` symlink)
Execution order = critical path: **P3 (close) → P5 → P7 → P8 = GOAL.** P0/P1/P2/P4 DONE; P6 off-path (later). Each gated by its PASS.

### P0 freeze — DONE → `GOAL/P0-freeze.md`
PASS: evidence inventory frozen; old C6 evidence = HOLD; no stale-spine override. (Met.)

### P1 adapter authority — DONE → `GOAL/P1-adapter-authority.md`
PASS: gemini-local write only at NEED ∧ Agent-policy ∧ adapter-capability; empty tool_policy_refs fail closed. Measured: agent_axis_behavioral + resource_boundary green. (Met.)

### P2 capability taxonomy — DONE, one open gap → `GOAL/P2-capability-taxonomy.md`
PASS: read/probe_write/source_write declared (Brick) + admitted (Agent) + ENFORCED with teeth (reviewer-source-write mutation fires RED — verified). Measured: --all green + mutation-RED.
OPEN: the qa-lead leak (leader-lane review role escapes the reviewer ceiling) → closed only by the policy-split (reviewers → probe-write-scoped) = the FIRST dogfood.

### P3 Easy Building official route — CORE, READY-NOW → `GOAL/P3-easy-building.md`
PASS: a customer `make X` runs **end-to-end** via the ONE official route (sealed: only `brick build`; fluent: the COO draws + fires once, plumbing swallowed) → `frontier=complete` + evidence. **Metric = the COO launches a real building in ONE fluent call with ZERO footgun ritual** (the launch-ritual disappearance IS the pass). Not slice-claims.

### P4 resume fan-out — DONE → `GOAL/P4-resume-fanout.md`
PASS: resume recovers declared fan-out parallelism after forward disposition; replay deterministic. Measured: bounded_agent_proposed_routing_loop green + timed fixture. (Met.)

### P5 first-run / onboarding — BLOCKED (needs P3) → `GOAL/P5-first-run.md`
PASS: install/init/doctor/onboard truthful for the available-LLM customer; gemini readiness honest; FIRST_USE delivered; a real-provider first task runs → evidence; no hidden machine-local dep.

### P6 cleanup / godmodule — BLOCKED, off critical path → `GOAL/P6-cleanup.md`
PASS: each god-module split **byte-identical** (behavior unchanged) — `--all` green oracle + mutation-RED + net-negative LOC. Includes the dead-pair sweep (development + cto-lead) landing --all green.

### P7 fresh-machine — BLOCKED → `GOAL/P7-fresh-machine.md`
PASS: clone → install → onboard → build → verify on a clean machine, **documented steps ONLY**, `frontier=complete`, ZERO undocumented manual steps, NO hidden machine-local dep (incl. fixing the non-hermetic `intake_evidence_projection_case`).

### P8 dogfood capstone = GOAL — BLOCKED → `GOAL/P8-dogfood.md`
PASS: BRICK runs ONE real task through the customer entrypoint → `frontier=complete` + raw/spine consistent + artifact real + operator-readable. (Single run = first proof, NOT reliability.) **This is the GOAL.**

## Building patterns (how each item runs)
**개발 큰것 (BIG) — TWO buildings, the COO (Claude) judges between:**
```
빌딩1: design (Fugu Ultra ∥ Claude → 종합)    → [COO reads design, DEFINES N parallel devs + what each]
빌딩2: fan([dev(Codex) → qa(Codex+Claude+Gemini)] × N) → closure → [COO disposition: forward / reroute]
```
The design→dev decomposition (how many, what) is a COO JUDGMENT (not automatic) — so design is cut as its own building.

**개발 작은것 (SMALL) — ONE building:**
```
design → dev → qa → closure → COO 보고
```

Both run via the official `brick build` route (P3 sealed-fluent). Capability layers stay clean:
read (design/closure) · probe_write (qa) · source_write (dev).

## P3 casting-pick (workflow-style performer selection)
When the COO launches workflow-style, it can PICK the performer per node — Fugu / Gemini / Claude / Codex —
not only the default cast.
- **Default cast (ratified 0629)**:
  - design = **Fugu Ultra** (`adapter:codex-fugu-local` + `model:sakana:fugu-ultra`) — small work uses Fugu Ultra alone; **개발 큰것 adds Claude** (design = Fugu Ultra ∥ Claude).
  - work/dev = **Codex** (codex-local).
  - **QA default = Claude** (base single reviewer); the 3-axis review (Codex + Claude + Gemini) is attached via **per-node adapter refs when declaring the graph** — not a fixed default.
  - closure = COO (Claude) / Codex.

**Per-node casting recipe (ALREADY in the official route — measured 0629, NO build needed):**
- Graph packet (`brick build --graph`): each node declares `selected_adapter_ref` + `selected_model_ref`. e.g. design → `adapter:codex-fugu-local` + `model:sakana:fugu-ultra`; a QA node → `adapter:codex-local` / `claude-local` / `gemini-local`. (Proven: four-llm-standard-graph already casts work=codex, axis-qa=gemini, closure=codex per node.)
- Assemble: `brick(kind, work, adapter="codex-fugu-local")` per node → flows to `selected_adapter_ref`.
- So multi-LLM (3-axis QA, Fugu Ultra design, +Claude for 개발 큰것) is attached per-node at graph-author time — no new code.
- PENDING (small re-wire, after the current dogfood, touches agent/objects): role-yaml DEFAULTS → design default = Fugu Ultra, QA default = Claude. (The weekend cast Codex/Gemini is still wired; that is why the current dogfood ran Codex+Gemini.)
- **Override (경우의 수)**: the COO picks per node — especially 개발 큰것, where the design's needs drive the casting.
- This belongs to P3's "sealed + fluent" launch = draw the shape + pick the cast + fire once; the official route swallows the plumbing.

## Stale — do NOT use as current
- `customer-ready-goal-plan-2track-0626.md` (old 2-track framing)
- the 11 `customer-ready-*-0627.md` sub-docs (C6-era HOLD chain — historical, superseded by the 0629 rechecks)
- `GOAL/` folder's old `00-…`–`06-…` symlinks (0626) — refreshed to P0–P8 here. The `GOAL/*.json` graph packets are current (keep).
