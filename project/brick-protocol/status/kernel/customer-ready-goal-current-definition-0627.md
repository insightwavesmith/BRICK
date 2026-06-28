# Customer-Ready BRICK Goal - Current Definition - 0627

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, or Movement
authority. It records the current operator definition of the customer-ready goal
after the weekend Codex/Gemini takeover and the QA semantics amendment.

## Live Boundary

Live development checkout:

```text
/Users/smith/.brick/worktrees/struct-surgery-0623
```

Museum / frozen reference checkout:

```text
/Users/smith/projects/brick-protocol
```

Current evidence must be read from the live checkout raw/evidence/checker state.
Claude, Gemini, Codex reviews, checker green, reporter packets, and this status
record are support evidence only.

## Goal

A customer can install BRICK, connect their own LLMs, enter:

```text
make X
```

BRICK then declares the work through Brick / Agent / Link, assigns available LLM
performers, runs the Building, and returns the artifact plus evidence.

Final proof is a BRICK self-dogfood run through that same customer path:

```text
customer entrypoint -> Building -> evidence -> operator-readable result
```

## Codex Operator Position

Codex is the Brick operator for this weekend handoff.

Codex does:

```text
- separate Brick, Agent, and Link evidence before choosing a repair surface
- inspect raw/evidence/checker output directly
- patch support or axis files when it moves the stated goal closer
- prefer official Building routes from P3 onward
- treat Gemini only as a Building Agent step for Gemini evidence
- keep closure on Codex unless the caller/COO explicitly declares otherwise
```

Codex does not:

```text
- invent Link Movement, targets, routes, or gates
- turn checker green into success or quality judgment
- treat model review as source truth
- treat support, adapters, runners, or reports as a fourth axis
```

## Active Weekend Casting

Weekend active casting:

```text
work/dev lane:
  adapter:codex-local
  building-step-template:work

Codex QA lane:
  adapter:codex-local
  building-step-template:code-attack-qa

Gemini QA lane:
  adapter:gemini-local
  building-step-template:axis-attack-qa

closure lane:
  adapter:codex-local
  building-step-template:closure

Gemini API lane:
  packet/read review only
  no write lane
```

Claude is not retired. Claude is outside the weekend active performer pool only
because of token capacity and may return as a declared override/active candidate
after Monday 2026-06-29.

## QA Semantics Amendment

`QA` is not a generic role label.

Current lens definitions:

```text
code-attack-qa:
  code correctness, regression, and negative-probe attack

axis-attack-qa:
  Brick / Agent / Link boundary and support-authority leakage attack

evidence-integrity:
  persisted evidence root, proof-limit, stale-source, and checker-overclaim attack

review:
  read-only return/evidence review
  not code QA

inspect:
  read-only structure, policy, and axis inspection
  not code QA
```

Any active C6 plan materialized before this amendment is stale for QA semantics.
P3 must rematerialize from the updated `four-llm-standard-graph` before launch.

Target P3 shape:

```text
work
  -> codex-code-attack-qa
  -> gemini-axis-attack-qa
  -> closure
```

## Phase Plan

### P0 - Freeze And Evidence Inventory

Freeze the live worktree, C6 evidence roots, raw frontier, dirty files, and stale
spine caveat before integration.

Movement:

```text
old C6 evidence = HOLD
stale spine does not override raw evidence
```

### P1 - Adapter Authority Repair

Gemini-local may be observed-write capable only at the effective-write
intersection:

```text
Brick write_scope NEED
AND Agent policy read-write-scoped
AND observed-write adapter capability
```

`adapter:gemini-api` remains read/review only. Missing or empty
`tool_policy_refs` fail closed.

### P2 - Agent Casting And Preset Recast

Remove active Claude dependency for the weekend path and recast Agent YAML,
presets, skills, and materialized plans to Codex/Gemini.

Current amendment:

```text
Codex QA = code-attack-qa
Gemini QA = axis-attack-qa
review / inspect are not QA substitutes
```

Exit requires generated active plans to show the dual QA lanes and Codex closure.

### P3 - Easy Building / C6 Launch Surface

Current core phase.

P3 is not "run C6 with Codex/Gemini" as the product meaning. P3 is the
customer-facing Easy Building surface:

```text
user says "make X"
or "this is big; design first, split it, and run lanes"
-> COO/task intake records the work
-> sizing/design judges whether the work is simple, large, risky, or split-worthy
-> official Building route declares the selected road
-> Building runs with evidence
```

The current `--large` surface is only an early fallback/default graph generator.
It is preset-like, but it is not the final P3 goal:

```text
preset:
  stored map selected by name

graph:
  explicit caller/COO-declared map for this run

large:
  convenience generator for a default "big work" graph
  task intake -> design -> design-axis QA -> plan closure
  -> parallel dev lanes -> lane QA -> fan-in
  -> final Codex code QA + Gemini axis/evidence QA -> Codex closure

target P3:
  task-aware Easy Building
  COO/Builder chooses simple preset, large fallback, or custom graph from the
  observed task/design evidence
```

Do not treat `large` as source truth, quality judgment, Movement authority, or
the completed product surface. `large` is admissible only as a scaffold while
P3 learns how to draw the Building road from the task.

Context-compression guard:

```text
If a future operator reads only a compressed summary, preserve this direction:
P3 is "make Building easy to declare and run" like the Claude workflow surface.
The operator must not collapse P3 into "hardcode one large graph" or "recast
C6 to Codex/Gemini." The work is to make the official route accept an easy
task/sizing/design declaration and then materialize the right preset or graph.
```

Run the customer launch path through official Building evidence with the current
weekend QA lanes:

```text
Codex work
Codex code-attack-qa
Gemini axis-attack-qa
Codex closure
```

P3 may close only with raw/evidence proof or remain HOLD with an exact
non-Claude blocker. Root-unification, Slack-visible evidence roots, and
`--large` graph behavior are support slices inside P3, not the whole phase.

### P4 - Resume Surface Repair

Resume must continue the same declared Building, not create a new Building
design. Completed replay may be serial; not-yet-run continuation must recover
declared fan-out behavior.

No new scheduler, queue, retry runtime, route authority, or Movement literal.

### P5 - Onboarding And Customer First Run

Make install/init/doctor/onboard truthful for the current Codex/Gemini customer
path:

```text
install/init/doctor/onboard
Gemini readiness honesty
real-provider first task
write_scope honesty
FIRST_USE delivery
```

### P5.5 - Build Fluency Surface

Make Building declaration and launch as fluent as the Claude workflow harness.

Target authoring shape:

```python
qa = parallel([
    brick("code-attack-qa", "..."),
    brick("axis-attack-qa", "..."),
])

run(build([design, impl, qa, done]))
```

Scope:

```text
build([...]) as pipeline
parallel([...]) / fan-first support
auto alias and auto return lowering
honest write=
one-call run(build(...))
per-node gate=
```

Constraint:

```text
closed Brick kind set stays closed
no naked prompt / agent / checker node
```

### P6 - Engine Cleanup / Godmodule Decomposition

Reduce structural drag after the customer path is alive.

Targets:

```text
case_runners
kernel_checks
checker-diet
remaining godmodule cleanup
```

Current operator read:

```text
case_runners = next candidate; re-derive current coordinates first
kernel_checks = re-investigate before acting
checker-diet = conservation inventory + mutation-RED required before deletion
```

### P7 - Fresh-Machine Proof

Prove the customer path on a clean/fresh machine shape:

```text
clone
install
onboard
connect available Codex/Gemini/Claude
build
inspect evidence
verify no hidden machine-local dependency
```

### P8 - Dogfood Capstone

BRICK uses the customer entrypoint to run its own next meaningful work.

Required shape:

```text
one real task
Codex work
Codex code-attack-qa
Gemini axis-attack-qa
Codex closure
evidence returned
raw/spine consistency checked
```

## Immediate Next Movement

Current global Movement:

```text
HOLD at P3 until new Codex/Gemini QA Building evidence exists.
```

Next admissible move:

```text
REROUTE / rematerialize P3 C6 with the updated QA semantics,
then run official Building evidence and inspect raw/evidence.
```

Immediate operator sequence:

```text
1. Record this goal amendment.
2. Commit the QA/preset amendment as a narrow P2/P3 recast-support change.
3. Rematerialize P3 C6 from updated four-llm-standard-graph.
4. Run the official Building route.
5. Judge FORWARD/HOLD from raw/evidence, not from model prose.
```

## Proof Limits

This record does not prove:

```text
P3 C6 closure
Gemini-local live provider success
fresh-machine install/onboard
Build Fluency P5.5 implementation
P6 godmodule cleanup
P7/P8 customer-ready proof
```
