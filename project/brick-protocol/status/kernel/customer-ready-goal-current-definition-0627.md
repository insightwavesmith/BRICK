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
C6 evidence may remain support evidence, but it is not the P3 product target.
P3 must not be reduced to "rematerialize C6 with weekend casting."

Target P3 shape:

```text
work
  -> codex-code-attack-qa
  -> gemini-axis-attack-qa
  -> closure
```

## Phase Plan

Phase plan documents are split one file per phase. They are symbolic support
links from this goal record, not source truth or Movement authority:

```text
P2: project/brick-protocol/status/kernel/customer-ready-p2-capability-taxonomy-plan-0628.md
P3: project/brick-protocol/status/kernel/customer-ready-p3-easy-building-official-route-plan-0628.md
P4: project/brick-protocol/status/kernel/customer-ready-p4-resume-fanout-plan-0628.md
P5: project/brick-protocol/status/kernel/customer-ready-p5-first-run-official-route-plan-0628.md
P6: project/brick-protocol/status/kernel/customer-ready-p6-cleanup-godmodule-plan-0628.md
```

## Execution Contract

Before doing work for P2-P6, the operator must read the linked phase plan for
that phase and treat it as the active support plan for scope, known gaps, exit
checks, and proof limits. The linked plan is not source truth; it is the required
operating packet to consult before touching code, checker, Brick template, Agent
resource, Link policy, documentation, or Building declaration.

Work routing:

```text
planning / attack review / inventory / operator reconciliation:
  may use direct inspection and native subagents.
  Codex must re-check subagent claims against files, diffs, raw evidence, and
  checker surfaces before adopting them.
  Subagents are closed after their result is collected.

P2 and later phase implementation discipline:
  After P2 work is underway, Codex does not act as the direct implementation
  worker for phase code/resource/checker changes. Codex operates the work:
  split the task to native subagents or, from P3 onward, to official Building
  Agents; collect their returned evidence; then independently re-check files,
  diffs, raw evidence, step-output, checker output, and phase-plan invariants.
  Codex's active context is reserved for judgment, reconciliation, and Movement
  reporting, not for becoming the worker lane.

implementation / QA / closure for customer-facing Building behavior:
  use the official Building route when a Building is the requested work form.
  From P3 onward, implementation / QA / closure must run only through the
  official Building route:
  brick build -> cli/driver -> Builder/materializer -> declared Building Plan
  -> run.py/graph walker -> raw/evidence/frontier/Slack.
  Do not bypass those surfaces with direct build(), internal helper calls,
  hand-built runner calls, or operator-authored return-shape/ref injection.

small operator review after a Building:
  may be direct, but must inspect raw, step-output, diff, checker output, and
  evidence root before reporting Movement.
```

Problem handling protocol:

```text
Evidence first:
Problem definition:
Brick question:
  Is the work contract, template, Building Plan, return shape, or graph/preset
  declaration wrong or incomplete?
Agent question:
  Did the performer, Agent Object, tool policy, adapter grant, receipt, or
  returned AgentFact lack the required facts/capability?
Link question:
  Did Movement, target, carry, gate sufficiency, fan-in/fan-out handoff,
  transition concern, or reroute/replay policy fail to carry the work?
Support surface:
  Which support file/tool/checker/adapter/reporter projected the issue?
Rejected one-axis shortcut:
  Do not patch "prompt", "checker", "adapter", "graph", or "docs" by name until
  Brick, Agent, and Link candidates have evidence or are explicitly missing.
Chosen repair surface:
Verification before Movement:
Movement:
  forward | reroute only. HOLD is lifecycle/frontier state, not Link Movement.
```

If any Brick / Agent / Link evidence row is missing, choose HOLD for closure and
name the exact evidence to collect. If implementation is still needed, route to
the next declared Brick boundary rather than ad hoc patching.

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

### P2 - Agent Casting, Preset Recast, And Capability Taxonomy

Remove active Claude dependency for the weekend path and recast Agent YAML,
presets, skills, and materialized plans to Codex/Gemini.

Current amendment:

```text
Codex QA = code-attack-qa
Gemini QA = axis-attack-qa
review / inspect are not QA substitutes
```

P2 also owns the capability taxonomy split. Do not keep reasoning in the old
binary "read/write" frame. Brick NEED, Agent max policy, and Adapter native grant
must separate these three classes:

```text
read:
  inspect repo/evidence/diff/raw/step-output.
  No file/content mutation.

probe_write / verification_write:
  write only disposable verification material:
  W1 work-area files, temp/cache, checker output, synthetic fixtures,
  negative-probe results, generated probe output.
  This is "write-capable read/verification", not product/source mutation.

source_write / artifact_write:
  write the actual requested artifact:
  source files, app code, docs/specs intended as deliverables, deployment
  artifacts, or any repo/product file the customer asked BRICK to create/change.
```

Three-axis placement:

```text
Brick:
  declares the needed class for the Brick kind / node.
  inspect/review = read.
  code-attack-qa / axis-attack-qa / evidence-integrity = probe_write when
  real checker/probe execution requires disposable writes.
  work / implementation / product-doc writing = source_write or artifact_write.

Agent:
  declares max admissible capability by tool policy.
  reviewer lanes may receive probe_write capability but must not source_write.
  worker/lead lanes may receive source_write only when the Brick declares that
  need and the Link road sends them to a work boundary.

Adapter:
  translates the semantic class to provider-native sandbox/tool projection.
  Gemini-local must have the same semantic classes as Codex-local where the CLI
  can technically support them.
  Gemini-api remains outside active write/probe-write path.
```

Required P2 implementation direction:

```text
- replace binary read/write language where it controls behavior
- add/keep checker coverage proving reviewer source mutation is RED
- allow QA/Inspector probe_write for real checkers/fixtures/temp outputs
- keep source_write/artifact_write for work/product Bricks only
- ordinary checker/profile sweeps must not live-call Gemini or any provider
- do not create new Movement, route authority, scheduler, queue, or source truth
```

Current partial implementation evidence:

```text
agent/tool_policies/read-write-scoped.yaml already names probe_write and
reviewer source_write prohibition.
code-attack-qa / axis-attack-qa / evidence-integrity Brick bodies already tell
reviewers to use disposable W1 probe writes and forbid source mutation.
The remaining P2 work is to make this a first-class capability class across
Brick declarations, Agent policy resolution, Adapter grant projection, and
focused negative checkers.
```

Exit requires generated active plans to show the dual QA lanes, Codex closure,
and the capability class of each lane without collapsing QA probe writes into
source_write.

### P3 - Easy Building / Official Route Surface

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

Canonical P3 inputs are official route inputs only:

```text
preset:
  stored map selected by name

graph:
  explicit caller/COO-declared map for this run
```

`--large` / `_p3_easy_large_*` is not canonical P3. If historical notes mention
large graph behavior, treat that as stale scaffold/support evidence. P3 must use
the official route to materialize a task-aware preset or graph.

Context-compression guard:

```text
If a future operator reads only a compressed summary, preserve this direction:
P3 is "make Building easy to declare and run" like the Claude workflow surface.
The operator must not collapse P3 into "hardcode one large graph", "call a model
directly", or "recast C6 to Codex/Gemini." The work is to make the official
route accept an easy task/sizing/design declaration and then materialize the
right preset or graph.
```

P3 reasoning ledger:

```text
User intent:
  "X 만들어줘" or "이거 커. 설계 먼저 하고 쪼개서 병렬로 굴려."

Correct operator reasoning:
  1. Treat the utterance as Building intake, not as a request to hand-write a
     plan or call a model directly.
  2. Decide the declared road from task evidence:
     simple work -> preset/task mode
     explicitly shaped work -> graph mode
     large / risky / split-worthy work -> design-first graph materialization
  3. For large work, first run design and design QA / axis inspection, then use
     the accepted decomposition to materialize parallel dev and QA lanes.
  4. Execute only through the official route:
     brick build / support.operator.cli build
     -> Builder/materializer
     -> declared Building Plan
     -> support/operator/run.py walker
     -> evidence root / reporter / Slack / frontier

Wrong compression recovery:
  If the summary says "large graph", read it as "fallback generator while P3 is
  being built", not as the completed P3 design.
  If the summary says "C6", read it as historical support evidence, not as the
  current P3 target.
  If the summary says "Codex/Gemini casting", read it as weekend performer
  availability, not as the customer-facing Easy Building goal.
```

P3 three-axis attribution:

```text
Brick:
  owns the declared work road, preset/graph grammar, Building Plan, and
  required return shapes.

Agent:
  owns who performs each Brick: design, dev, code-attack QA, axis/evidence QA,
  and closure. Adapter choice is capability connection only.

Link:
  owns Movement, handoff, fan-out/fan-in carrying, gate sufficiency, reroute
  concerns, and closure transition evidence.

Support:
  CLI, Builder/materializer, run.py, reporter, Slack, checkers, and model output
  only record/walk/project evidence. They do not choose the route or judge
  success/quality.
```

Run the customer launch path through official Building evidence. Weekend default
QA lanes:

```text
Codex work
Codex code-attack-qa
Gemini axis-attack-qa
Codex closure
```

P3 may close only with raw/evidence proof or remain HOLD with an exact
non-Claude blocker. Root-unification and Slack-visible evidence roots are
support slices inside P3, not the whole phase.

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

Build fluency belongs to P3 and first-run delivery belongs to P5. Do not create a
separate intermediate phase for this goal.

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
HOLD inside P3 until Easy Building behavior is proven through official route
evidence.
```

Next admissible move:

```text
REROUTE to the next declared P3 Easy Building slice when raw/evidence shows a
missing customer-facing declaration behavior.
```

Immediate operator sequence:

```text
1. Record this goal amendment.
2. Keep implementation/QA/closure on the official Building route only.
3. Use preset/task mode or graph mode as inputs to the same official route.
4. For large work, preserve design -> design QA -> closure plan confirmation
   before parallel dev lanes.
5. Judge FORWARD/HOLD from raw/evidence, not from model prose.
```

## Proof Limits

This record does not prove:

```text
P3 C6 closure
Gemini-local live provider success
fresh-machine install/onboard
P3 build fluency official-route implementation
P6 godmodule cleanup
P7/P8 customer-ready proof
```
