# Customer-Ready BRICK — Goal Plan (2-Track) — 0626

Live line: `/Users/smith/.brick/worktrees/struct-surgery-0623` = `main` @ `3d22955`.
(NOT `/Users/smith/projects/brick-protocol` — that is a separate frozen MUSEUM repo at `0d698a0`.)

## GOAL
A customer installs BRICK, connects their own LLMs, says "make X", BRICK assembles
multiple LLMs to do it and returns evidence — all **by themselves**. Proven by BRICK
**self-dogfooding** that same customer path. Autonomous to goal (Smith approves only
destructive/policy/big-cost).

## Landed today (all committed to main=3d22955, each --all green + independent gate)
- gemini repair (model 2.5→3.5-flash) · preset → 3-LLM (Fugu dropped) · #3 checker
  (step-output evidence-field-set parity) · gemini-local adapter removed (checker-first,
  atomic) · gemini-api LIVE (Smith replaced the key in ~/.brick/report.env) · worktrees 25→4.

## Corrections grounded this session (measured, not inferred)
- **"build exit 0 = false-success bug" was MY inference error — NOT a bug.** Measured: `_cmd_build`
  returns literal 0 by the 3-axis rule "support records facts, never judges success/quality"
  (AGENTS.md:57-67/173-175, rules-and-boundaries.md:115-139, cli.py PROOF_LIMITS, and the
  brick_cli_entrypoint checker bans success_judgment/quality_judgment tokens). `frontier_kind`
  is a support FACT (complete/hold/agent_incomplete/...); the completion VERDICT is Link
  (link/spec.py:862) + a human COO disposition. `brick verify` returns the checker exit code
  (non-zero on RED); `brick init` gates on build_error+verify-RED — but NOT on frontier_kind.
  → **No build fix. The DOGFOOD/automation must read `frontier_kind=="complete"` (from --json)
  or run `verify` for a gating code. Fact is published; the reader judges.**
- **gemini = locked for customers.** Customer standard = Codex + Claude (2-LLM). gemini = optional
  (API key only). gemini-CLI login is structurally dead (Google deprecated personal OAuth 2026-06-18).
- Discipline: MEASURE, do not infer. (Multiple inference errors this session: over-reach verdict,
  false-success "bug", museum-vs-live repo.)

## Mandatory Incident Rule — 3-Axis First

When a Building/phase shows unexpected behavior, the operator must stop before
patching and run this order:

1. Reframe the symptom as Brick / Agent / Link evidence, not as a support-file
   guess.
2. Inspect raw evidence first: `raw/`, `work/step-outputs/`, `link` claim
   traces, frontier, and declared plan.
3. Spawn at least 3 focused subagents for independent measurement:
   - Brick/work-contract/template/return-shape candidate.
   - Agent/returned-fact/adapter/tool-capability candidate.
   - Link/carry/gate/Movement/reroute/lifecycle candidate.
4. Do not implement, reroute, approve, or redesign until the subagent evidence
   and operator reconciliation identify the actual axis boundary.
5. If the cause is mixed or unresolved, record `HOLD / NOT_PROVEN` and preserve
   the evidence root. Do not patch the nearest noun (`prompt`, `checker`,
   `worktree`, `adapter`, `gate`) just because it is visible.

This rule is mandatory for P2/P3 and remains the default for later phases.

## Customer-Ready Goal v3 Compact Addendum - 0629

Live checkout remains `/Users/smith/.brick/worktrees/struct-surgery-0623`.
`/Users/smith/projects/brick-protocol` remains frozen/museum evidence.

Goal: a customer installs BRICK, connects LLMs, enters "make X", and BRICK
declares the work through Brick / Agent / Link, runs only the official Building
route, and returns artifact plus evidence. Final proof is a BRICK dogfood run
from that same customer entrypoint.

Codex operator role: Codex is COO/operator, not source truth, success judgment,
quality judgment, or Movement authority. Codex may inspect raw, step-output,
diff, checker, evidence root, and model review as separated support evidence.
Unexpected behavior always starts with Brick / Agent / Link attribution before a
support file, prompt, checker, adapter, or runtime is named as the repair surface.

Route rule: planning, inventory, and attack review may run direct/subagent and
then be rechecked by Codex. From P3 onward, implementation / QA / closure
Building work must use only the official route:

```text
brick build
-> support.operator.cli / driver
-> Builder / materializer
-> declared Building Plan
-> support.operator.run / graph walker
-> evidence root / frontier / reporter / Slack
```

The operator must not manually inject `required_return_shape`, `brick.md`,
`return.yaml`, `brick_template_refs`, or carry fields into graph nodes. Brick
templates and the Builder materialize those fields.

P2 capability taxonomy: Brick NEED, Agent max policy, and Adapter native grant
must distinguish `read`, `probe_write`, and `source_write` /
`artifact_write`. QA / Inspector lanes may write checker/temp/fixture/probe
outputs only; source or product artifact mutation by QA is RED/HOLD.

P3 Easy Building: P3 is not "run C6 with Codex/Gemini" and not a hardcoded
`--large` topology. P3 is the product surface where the operator can say
"this is big; design first, split it, and run lanes", then BRICK declares either
a task-aware preset or graph_packet through the official route.

P3 hard fan-in invariant: source QA / Inspector / evidence lanes in a hard
fan-in cohort may return local `transition_concern_evidence`, but Link must not
adopt, reroute, or lifecycle-HOLD from those source-lane concerns before
closure-synthesis. Fan-in internal edges remain `forward`; closure-synthesis is
the only Link-facing transition concern source. Closure-origin concerns remain
adoptable under declared Link policy and declared budget.

Measured 0629 blocker: live dynamic fan-in measurement showed a QA source-lane
concern was consumed before closure. Without declared budget it paused; with
budget it rerouted to work before closure.

0629 operator recheck: this specific hard fan-in blocker is now
repaired/proven as support evidence by focused profiles:
`building_skill_preset_agent_tool_hardening`, `brick_cli_entrypoint`,
`driver_public_intake_seal`, and `bounded_agent_proposed_routing_loop`.
An official `brick build` preset_task smoke also completed at:

```text
/Users/smith/.brick/project/brick-protocol/buildings/
cr-v4-p3-official-route-smoke-0629a
```

This moves the old hard fan-in blocker to FORWARD for the next P3 proof slice.
It does not close the whole P3 phase.

Required P3 probes: (1) hard fan-in QA source concern does not create pre-closure
adoption / reroute / HOLD; (2) closure-origin concern still adopts / reroutes /
HOLDs under declared policy. Both are support evidence only.

Transition concern refs: `evidence_used` may carry repo/file paths.
`transition_concern_evidence.reason_refs` must carry observation ids or
ledger-safe refs such as `observation:<id>` / step-output refs. Repo paths in
Link-facing `reason_refs` are RED/HOLD.

## Consolidated phase status (0626 — current)

### Track A — Engine (sequential)
- **A1 live closure proof**: ✓ READ-path proven (4-parallel-root design building → frontier=complete, claude). □ WRITE-path = an A-dev split building (codex byte-identical) still to run (overlaps A2).
- **A2 god-module cleanup**: ✓ decision table + quality-verified ([[godmodule-decomposition-decision-table-0626]]). ✓ **walker_kernel split LANDED `f0b4679`** (3803→2159 + 5 leaves walker_carry/frontier_driver/report_events/resume_seed/runtime_mail; byte-identical, _run_dynamic_graph_walker unsplit; verified by a 4-dimension adversarial workflow + 3 in-building QA lanes, 0 breaks). □ kernel_checks + checker-diet have FALSE premises → re-investigate before acting. □ case_runners next (re-derive coords). FINDING: resume UNCONDITIONALLY serializes fan QA (walker_kernel.py:2555 clobbers the pool; env override is a no-op on resume — measured) → resume-surface #3 has a concrete fix location.
- **A3 arch review (E+G)**: dedup / proliferation / stale docs / checkers beyond the god-modules.

### Track B — Shell (parallel, engine-independent)
- **B1 launch = as fluent as a workflow** (= [[build-fluency-roadmap-0626]], concrete C1→C8 ladder):
  C1 (FIRST) build() fan-first/multi-root (engine already supports — [[single-entry-multiroot-finding-0626]]; only build() blocks) · C2 standalone parallel([...]) · C3 auto-returns/alias to lower tier · C4 reject unknown kind at authoring · C5 write= honest · C6 run() one-call + frontier-honest exit (the real false-success fix) · C7 per-node gate= · C8 (Smith's call, constitutional) agent free-pick. KEEP: kind = closed 10-set ("no naked node").
- **B2 onboarding** = register→auto→custom + COO auto-deliver (GAP2) + verify speed + advisory measure.

### Cross-cutting — casting (which LLM for which role)
- Multi-LLM comparison RUNNING (codex/gemini vs claude, same design task) → feeds C8 + B2 auto-assign.
- Early finding: gemini-api is HTTP (no filesystem) → likely a text-reviewer, not a file-investigator. Verifying.

### Converge → goal
- Z1 fresh-machine proof (clone→install→login→build→verify once). Z2 dogfood = goal.

### Why this session mattered
B-1 vague → concrete C1-C8. A2 undecided → decision table + quality ranking (intuition overturned: walker_kernel first, not kernel_checks). "정직 1층(false-success)" retired (design correct → absorbed into C6 launcher). Casting abstract → live multi-LLM comparison. Live-proven: true multi-root building to frontier=complete.

---

## THE PLAN — two parallel tracks converging at dogfooding

### Track A — Engine (sequential; touches engine internals)
1. **Live closure proof.** gemini-api is live → run the standard building
   (Codex write → Claude + Gemini-api review → COO closure) end-to-end to `frontier_kind=complete`.
   First time real providers run start→finish.
2. **Arch cleanup + full review (E + G merged).**
   - god-modules large (kernel_checks 9808 / case_runners 10219 / walker_kernel 3803 LOC),
     registry has no decomposition target → DECIDE: actually split (fresh G2-elegance admission +
     checker-first, byte-identical, write-scope-serialized) vs facade-hygiene only (a doc re-scoped
     E to facade-hygiene; "four god-modules done" was false).
   - checker-diet: the 195KB original profile CANNOT be deleted yet — the 3 staged split profiles
     conserve only 12 of 97 original assertion labels. Need a line-level conservation inventory +
     mutation-RED before deleting.

### Track B — Shell / customer-facing (parallel; engine-independent → can run NOW via Codex)
1. **Launch ergonomics — custom draw→fire as easy as a workflow.** The building DSL is already the
   mirror of workflow primitives (`build`=pipeline, `fan`=parallel) — the EASY *drawing* tier exists.
   The friction is only the LAUNCH RITUAL: the 4 footguns (composed_plan dict / output_root=vessel /
   worktree ownership / assembly.build≠onboard.build), the museum-vs-live trap, and the
   copy-paste-the-skill recipe. `launch_assembled_building()` (onboard.py:1728-1910) already absorbs
   the 4 footguns — surface it as the easy DEFAULT so "draw a graph → one fire() call → running", no
   ritual. **This is NOT just the preset CLI.** The CUSTOM self-drawn graph must be workflow-easy too,
   because the goal is the main AI drawing the right shape for EACH task on the fly (presets alone
   cannot cover every shape). My current "copy the skill recipe + dodge the 4 footguns" ritual every
   dogfood launch IS the evidence it is not easy yet. Two faces, one easy entry: (a) custom draw→fire
   (the emphasis), (b) preset/named build.
2. **Customer onboarding — core = register → auto → custom:**
   - **Register (login):** Codex + Claude login → an available-adapter registry (in login order).
     gemini = optional key (not registered = locked). Already-logged-in → skip.
   - **Auto (assign to each agent):** each role's adapter = chosen from the available registry
     (capability-matched / first-logged). This is what makes a Claude-only customer work — adapt
     to what they have, instead of the hardcoded `preferred_adapter_ref` (dev=codex) breaking.
   - **Custom (override):** operator tells the main agent (COO) to override per-role.
   - plus: **COO auto-delivery (GAP2)** — MCP initialize does NOT deliver the operating-chain to a
     cold session; make it auto-delivered. · **verify speed** (building_operator_driver0 = 190-217s).
     · **advisory-ok** ("steps not wired but init shows ok") — MEASURE whether intentional degrade
     or a real defect before calling it a bug.

### Converge → GOAL
3. **fresh-machine proof:** clone → install → login → build → verify on a real clean machine, once.
   = the "customer is really self-sufficient" stamp (only ever run on our already-set-up machine).
4. **Dogfood capstone = GOAL:** BRICK builds itself through the customer path; success judged by
   `frontier_kind`/`verify` (per the corrected design), not build's exit code.

## Parked (later, not urgent)
- Runtime adapter resilience (retry on transient / fallback on token-死). gemini-lock + 2 reliable
  providers reduce urgency.

## Adapter permission model (Smith's 3-layer, for reference)
adapter = full power · agent yaml adapter_refs = admitted ceiling (read/write floor) · brick =
recommends capability · effective = adapter-capability ∩ yaml-permission ∩ brick-need. The leak fixed
by Track B-2: selection must also intersect AVAILABILITY (the register step), not just admitted.

## Findings / Research (0626) — symlinked under `GOAL/` for direct reference
- [research-0626/godmodule-decomposition-decision-table-0626.md](research-0626/godmodule-decomposition-decision-table-0626.md) — **A2 answered**: split-vs-facade per god-module (3/4 split, checker-diet facade impossible) + quality-verified trust scores. **Start = walker_kernel (5/5/5); kernel_checks + checker-diet need re-investigation (false premises caught by verify).**
- [research-0626/build-fluency-roadmap-0626.md](research-0626/build-fluency-roadmap-0626.md) — **Track B-1 detailed**: make build() as fluent as a workflow. C1(fan-first)→C8(agent-pick). Target shape + kept difference (kind=closed=no-naked-node).
- [research-0626/single-entry-multiroot-finding-0626.md](research-0626/single-entry-multiroot-finding-0626.md) — engine supports multi-root (≥1 root, proven); single-entry is build() convenience only → feeds C1/C2.
- [research-0626/build-exit-zero-3axis-finding-0626.md](research-0626/build-exit-zero-3axis-finding-0626.md) — brick build exit 0 = intentional 3-axis design (NOT a bug); honest exit belongs in the C6 launcher, not build CLI. "정직 1층" retired.
- [research-0626/resume-surface-design-0626.md](research-0626/resume-surface-design-0626.md) — **resume surface design (Smith's model + judgment)**: resume = one clean surface (forward/reroute/stop) that resumes the held building AS DECLARED (behavior-preserving). ~80% exists as `run_approve_entry`; gaps = not cleanly surfaced + serializes parallel fans. Track B-1 operate-half.
- Live empirical investigation (Area 1/2/3): [customer-ready-brick-live-empirical-investigation-2026-06-26.md](customer-ready-brick-live-empirical-investigation-2026-06-26.md)
- Live multi-root design building output: `buildings/godmodule-design-0626/`

**Live-proven this round**: true 4-parallel-root building ran to frontier=complete (A1 read-path), claude design + closure, read-only. Build-fluency + multi-root findings convert Track B-1 from "vague" to a concrete C1→C8 ladder.

## Next step
Track A-1 (live closure proof) OR Track B (onboarding, Codex-delegatable in parallel). Concrete near-term: **C1 (fan-first build() fix)** is the smallest Track B-1 win; **walker_kernel A-dev split** is the safest A2 first target.
