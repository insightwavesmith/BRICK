# Customer-Ready BRICK — Plan Audit & Work-Ready Roadmap — 0629

Status: support evidence only (operator review). This record is not source truth,
success judgment, quality judgment, or Movement authority. It records Claude's
operator audit of the weekend Codex P0-P8 plan against measured reality, and the
work-ready next steps. Verify live state from raw/evidence/checker, not from this doc.

Operator note: Claude is eligible for Smith/human re-admission after the weekend bench
window; this document recommends explicit re-admission now (ratified by Smith 0629 — see Decisions).

## Live boundary
- Live checkout: `/Users/smith/.brick/worktrees/struct-surgery-0623` (HEAD `515a7b2`, branch `struct-surgery-0623`; tracked diff clean; untracked evidence/debris present).
- Museum/frozen: `/Users/smith/projects/brick-protocol` (`0d698a0`).
- Plan source chain: `customer-ready-goal-current-definition-0627.md` → (Phase Plan §) → `customer-ready-p2..p6-*-0628.md`.
- ⚠️ Stale/historical: `customer-ready-goal-plan-2track-0626.md` and the C6-era `-0627` docs. Current graph packets live under `status/kernel/GOAL/`.

## Verdict: plan is SOUND, HONEST, adoptable (a few fixes, NOT a redesign)
- Goal unchanged: customer installs → connects LLMs → `make X` → official `brick build` route declares Brick/Agent/Link work → returns artifact + evidence. Final proof = self-dogfood through that same customer path.
- Independently audited: the weekend work does NOT overclaim. Every "FORWARD" slice is physically true; every "NOT-PROVEN" item is genuinely unproven and labeled as such.
- C6 "one-call launch verb" was DELIBERATELY retired (not a failure). Customer entry = `brick build --task/--preset/--graph`.

## Verified live state (run with REAL HOME — see Discipline)
- `check_profile.py --all` = GREEN, exit 0, **28 profiles, 0 RED** (real HOME).
- ⚠️ CORRECTION of an earlier operator alarm: a "--all RED" report was a FALSE measurement caused by `HOME=$(mktemp -d)`. The failing check `read-side-projection-boundary / intake_evidence_projection_case` GENERATES a building that needs real `~/.brick` HOME state; an empty temp HOME breaks it → false `agent_incomplete`. The code is GREEN.
- Landed (verified): P2 capability taxonomy; P4 resume fan-out (`4c18c94`, ancestor of HEAD); gemini-local revival (api-key, valid — OAuth-death does not apply); gemini-HTTP-API retired.
- One real multi-lane Building (`cr-v4-p3-full-design-first-graph-0629b`): 11 steps, **8 codex-local + 3 gemini-local real providers**, 0 adapter-error, link 24 forward / 0 reroute, final QA concern `binding:false` (stayed advisory through closure).
- Debris: **2058 untracked** building/evidence files (mostly stale C6 weekend-recast roots). Source tree (support/agent/brick) clean. Housekeeping, not a correctness blocker.

## Phase status
| Phase | What | Status |
|---|---|---|
| P0 freeze | evidence inventory gate | DONE |
| P1 adapter authority | gemini-local = NEED ∧ Agent-policy ∧ adapter-capability | DONE |
| P2 capability taxonomy | read / probe_write / source_write | DONE (landed) |
| **P3 Easy Building official route** | `make X` → `brick build` → evidence | **READY-NOW** — core; mechanical spine VERIFIED; NOT end-to-end proven |
| P4 resume fan-out | resume recovers declared parallelism | DONE |
| P5 first-run / onboarding | install/init/doctor/onboard truthful + FIRST_USE | BLOCKED (needs P3) |
| P6 godmodule cleanup | case_runners / kernel_checks / checker-diet | BLOCKED — off critical path |
| P7 fresh-machine proof | clone→install→onboard→build→verify | BLOCKED — **NO DOC** |
| P8 dogfood capstone | BRICK runs its own task via the customer path | BLOCKED — **NO DOC** = the goal |

## Genuinely missing for true end-to-end customer-ready
1. `make X` → graph translation is OPERATOR/COO-skill-driven (`brick-task-author` + `building-sizing-method` skills), NOT autonomous support route selection. Works only if the customer's main AI runs these skills as COO.
2. Explicit Link closure-origin adoption FACT not projected (replay visible; `policy_action_trace.facts=[]`).
3. Live provider reliability + semantic graph quality (single runs only, not reliability).
4. P7 fresh-machine + P8 dogfood = the ONLY true end-to-end proofs — NOT STARTED, NO DOCS.

## 3 corrections (fixes, not redesign)
1. **P3 boundary too wide** — 11 stacked 0629 slices = over-claim-by-accumulation risk → narrow + close cleanly.
2. **P7/P8 have no phase docs** → write them with concrete PASS criteria before reaching them.
3. **Measurement discipline** → always real HOME (below).

## Decisions (ratified by Smith, 0629)
- **(a) Claude re-admit = YES** — Claude re-enters as a **second-eye support-evidence performer ONLY**: NOT source truth / Movement / success / quality authority. (Matches the 3-axis boundary: Claude/Gemini/Codex outputs are support evidence; Movement/quality/success judgment is not theirs.) Re-admission is Smith's explicit decision, not automatic.
- **(b) Direction = bounded end-to-end dogfood probe** — NO more P3 micro-slice churn. Conditions:
  - Name it **"P8 dogfood forcing probe" / "P3→P8 bounded dogfood probe"** — do NOT call it "P8 complete."
  - Write minimal **P7/P8 PASS criteria** doc FIRST (this audit flags P7/P8 "NO DOC" as the blocker).
  - The dogfood result is a **gap extractor, not a success verdict.** Each failure becomes the next P3/P5/P7 repair surface.

## Immediate sequence + Movement (ratified 0629)
1. Apply the 3 wording fixes above → commit this doc (`Record customer-ready roadmap audit and dogfood decision gates`).
2. Write minimal **P7/P8 PASS criteria** doc.
3. Declare the bounded dogfood graph/Building.
4. Run it via the **official `brick build`** route.
5. Treat the result as a gap extractor; route each surfaced gap to its P3/P5/P7 repair.

**Movement:** FORWARD to the bounded dogfood probe; broad customer-ready stays **HOLD / NOT PROVEN**.

## P3 design direction — sealed + fluent launch (sharpened 0629)
The user of build-launch is the AGENT (a customer's main AI acting as COO), NOT a hand-coding human. The friction metric is the AGENT's own struggle: this session EVERY building launch (gemini-revival, walker, C1, C6) needed a /tmp launcher — `assemble(graph,task)` → `composed_plan` dict → manual `git worktree add` → `output_root=vessel` → `run_building_plan(adapter_cwd=…)` → manual `git merge` — dodging the 4 footguns + copying the skill recipe. That lived friction IS the P3 gap.

Change = two-pronged:
1. **SEAL** — keep ONE official launch route; block all others (run_building_intake / assemble+run_building_plan / launch_assembled_building / direct build()). A non-official launch call errors "use the official route." (Extends the existing `driver_public_intake_seal`.)
2. **FLUENT** — that one route is as easy as firing a workflow: the agent DRAWS (`build`/`fan`, the existing pipeline/parallel mirror) and fires ONCE; the route SWALLOWS worktree creation, output_root=vessel, evidence collection, report, and the merge-candidate. No footguns, no recipe copy.

```
today:  /tmp launcher → assemble(graph,task) → composed_plan dict → git worktree add →
        output_root=vessel → run_building_plan(adapter_cwd=…) → verify → git merge
target: fire(build([design, work, fan([code-qa, axis-qa]), closure]), "make X")  → done.
        (the official route's fluent FRONT — NOT a side verb; C6-as-side-verb was correctly retired
         BECAUSE the ease belongs in the official route, not a parallel verb)
```

Metric (no guessing): the AGENT can launch a building in ONE fluent call with ZERO footgun ritual. The disappearance of this session's launch ritual IS the PASS. This is exactly the bounded dogfood forcing probe: "make X → draw → fire → evidence" run by the agent in one shot; any ritual that still intrudes = the next repair surface.

Same problem as the narrowing below: many footgun-laden launch surfaces = the same complexity disease as the 8 agent lanes — collapse to one.

## Open findings to continue (recorded 0629, not yet acted)
- **qa-lead source_write LEAK** (verified live, source_write=True): qa-lead is a `leader` lane, so the reviewer-no-mutation ceiling (keyed on `lane=='reviewer'`) does NOT apply → qa-lead CAN source_write. The Brick NEED (review=read) saves the *effective*, but the Agent-axis guard is missing (defense-in-depth gap). The enforcement DOES have teeth for true reviewer lanes (mutation fires RED, verified). Secondary: the brick `capability_class` label is advisory/unenforced (real guard is the lane ceiling); enforcement is prompt-projection-level, not filesystem-level (known; OS sandbox deferred to hosting). Candidate first dogfood: tie review-named leader lanes to no-source-write + pin it — OR close by DELETION (below).
- **Agent/Brick NARROWING in progress** (delete unused → fewer holes; Smith's "complexity makes problems"): `development` kind = 0 preset uses (delete candidate). cto-lead/pm-lead likely unused (objects are cast by kind→lane→object, NOT named in presets — confirm via casting map, workflow `wwlpznpmz`). Collapse lanes/kinds/policies to the minimal set that still covers every preset shape; the qa-lead hole may close by DELETION rather than a new checker. The tool-policy design ("everyone shares read-write-scoped; reviewers demoted by a hook") is itself the leak source — a dedicated probe_write-only policy may be simpler + safer.
- **Measurement hygiene (P7)**: `intake_evidence_projection_case` is non-hermetic (needs real HOME) → false-REDs in fresh/CI env. Fix during P7.

## Critical path to dogfood
`P3 (close) → [Claude re-admit] → P5 first-run → P7 fresh-machine (write doc first) → P8 dogfood = GOAL.`
P4 = done. P6 (engine cleanup) is OFF the critical path (later).

## Measurement discipline (load-bearing — applies to every phase)
- **ALWAYS run checkers / `--all` with the REAL HOME** (`/Users/smith`). NEVER `HOME=$(mktemp -d)` — it false-REDs HOME-dependent checks. Invocation: `cd <live> && PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all`.
- focused-profile green ≠ phase done. Gate = full `--all` green (real HOME) PLUS the phase's own exit criteria met end-to-end.
- Treat "CR record/audit" commits skeptically — verify the claim, don't take the record as the proof.
- Latent hygiene: `intake_evidence_projection_case` is non-hermetic (needs real HOME) → will false-RED in CI/fresh-machine → fix as part of **P7**.

## Why "so many failures" (context)
Most recent "failures" are noise, not code bugs: ① mis-measurement (the false-RED) · ② live-LLM provider flakiness (gemini timeouts, codex intervention-required) · ③ solo-autonomous churn (C6 13 recasts — no second eye) · ④ non-hermetic checks (env-dependent). BRICK is a STRICT gate → it surfaces every wobble loudly; high failure-visibility is partly by design. Engine/code is sound.

## Pointers
- Goal-of-record: `customer-ready-goal-current-definition-0627.md`
- Phase docs: `customer-ready-p2-capability-taxonomy-plan-0628.md` · `customer-ready-p3-easy-building-official-route-plan-0628.md` (core, 936 lines) · `customer-ready-p4-resume-fanout-plan-0628.md` · `customer-ready-p5-first-run-official-route-plan-0628.md` · `customer-ready-p6-cleanup-godmodule-plan-0628.md`
- Stale-doc trap: four `-0627` sub-docs (c6-qa-semantics-recast, launch-frontier-honesty, gemini-local-hold, brick-provider-env-precedence) describe the SUPERSEDED C6-era HOLD chain — historical, not current.
