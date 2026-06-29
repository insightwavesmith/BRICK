# Customer-Ready P3 Easy Building Official Route Plan - 0628

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, Movement
authority, or route invention. It records the operator plan for the P3 product
surface after read-only subagent measurement, two-agent attack review, and Codex
operator reconciliation. Subagent output is support evidence only.

## Phase

P3 - Easy Building.

## Operator Correction

P3 is not "run C6 with Codex/Gemini." C6 is historical/support evidence.

P3 is the customer-facing surface where the user can say:

```text
make X
this is big; design first, split it, and run lanes
```

BRICK must then declare the work through the official Building route. The
operator must not hand-write return shapes, manually inject Brick refs, or
invent a hardcoded large route.

## Official Route Invariant

The only public run route for P3 is:

```text
brick build
-> support.operator.cli build
-> driver customer sandbox/intake seam
-> Builder/materializer
-> declared Building Plan
-> support/operator/run.py or graph walker
-> Building evidence root / reporter / frontier
```

Admitted public input modes:

```text
preset_task
graph_packet
```

Non-canonical:

```text
--large
_p3_easy_large_*
hardcoded lane_return / shortened required_return_shape injection
manual operator-supplied brick_instruction_body / brick_template_refs
```

Historical note: any old `--large` wording was a scaffold and is no longer the
canonical P3 design. Large work must be expressed through official task/preset
or graph materialization.

## 0629 Hard Fan-In Measurement Correction

This correction is part of P3 before the customer Easy Building surface can
close. It is not a new engine, scheduler, queue, retry runtime, Movement literal,
or route selector.

Measured live behavior:

```text
Fixture shape:
  live_dynamic_fan_in_n3

Injected observation:
  QA source lane returned transition_concern_evidence before closure.

Observed without node reroute budget:
  frontier = link_paused
  reason = target_node_has_no_link_assigned_budget
  sequence reached QA source lanes before closure.

Observed with node reroute budget:
  default-transition adopted the QA source-lane concern.
  run rerouted to work before closure-synthesis.
```

Three-axis attribution:

```text
Brick:
  the graph is structurally fan-out / fan-in and the Brick return templates may
  expose transition_concern_evidence.

Agent:
  QA / Inspector / evidence lanes may report local concerns as Agent return
  evidence, but they do not own Movement, target, quality, or success.

Link:
  hard fan-in source-lane concerns must not become Link-facing adoption input
  before closure-synthesis. Fan-in internal edges are forward. Closure-synthesis
  is the only Link-facing transition concern source for the cohort.

Support:
  walker, runtime mail, composition, and checkers walk / record the declared
  road. They do not invent a route or fix the meaning by shrinking return
  shapes.
```

Chosen repair surface:

```text
P3 needs a declared hard-fan-in policy and checker proof. The repair must make
source-lane transition concerns local/observational until closure-synthesis,
while preserving closure-origin concern adoption under declared Link policy.
```

Forbidden shortcuts:

```text
- do not remove transition_concern_evidence globally
- do not shrink required_return_shape to "observed_evidence, not_proven"
- do not make QA lanes unable to report local concerns
- do not add hold / pause as a Link Movement
- do not add a scheduler, queue, retry runtime, or hidden target selector
- do not treat runtime_mail path-resolution failure as the root cause by itself
```

Reason refs contract:

```text
evidence_used:
  may contain repo/file paths and direct evidence locations

transition_concern_evidence.reason_refs:
  must contain observation ids or ledger-safe refs, for example observation:<id>
  or step-output refs

Link-facing reason_refs containing repo paths:
  RED/HOLD when they reach runtime mail or transition adoption
```

## Required User-Facing Shape

Simple task:

```text
task intake
-> selected task-first preset
-> work
-> Codex code QA
-> Gemini axis/evidence QA where declared
-> Codex closure
```

Large / risky / split-worthy task:

```text
task intake
-> design
-> design QA / axis inspection
-> closure: execution plan confirmation
-> parallel dev lanes
-> each lane: dev -> QA
-> fan-in integration / summary
-> Codex final code/regression QA
-> Gemini-local final axis/evidence QA
-> Codex closure
```

This is a graph/preset declaration problem, not a new engine, scheduler, queue,
retry runtime, Movement literal, or provider-specific law.

## Three-Axis Attribution

Brick:

```text
owns presets, graph grammar, Building Plan rows, Brick template refs, brick.md
instruction bodies, required return shape, and return.yaml materialization.
```

Agent:

```text
owns performer identity and returned facts for design, dev, QA, inspection, and
closure. Adapter selection is a capability connection only.
```

Link:

```text
owns fan-out/fan-in handoff, carries_forward_fields, gates, Movement, frontier,
reroute eligibility, and closure transition concerns.
```

Support:

```text
CLI, driver, composition, design toolkit, reporter, Slack, and checkers walk and
record the declared road. They do not invent route targets or judge quality.
```

## Current Measurement

Already measured in the live checkout:

```text
support/operator/cli.py routes task and graph through driver customer seams.
support/operator/driver.py exposes run_customer_building_in_sandbox and
run_customer_graph_building_in_sandbox.
support/operator/composition_graph_emit.py leaves templated required_return_shape
blank so compose_building materializes from return.yaml.
support/operator/composition_compose.py stamps brick_instruction_body,
brick_template_refs, required_return_shape, and carries_forward_fields.
support/checkers/profiles/brick_cli_entrypoint.yaml now treats --large as
non-canonical.
```

## 0629 Operator Recheck / Support Evidence

The previous P3 blocker was rechecked from current code, checker profiles, and
one customer-like official route smoke. This is support evidence only, not
source truth, quality judgment, success judgment, or Movement authority.

Observed P3 support evidence:

```text
Official route smoke:
  command:
    .venv/bin/brick build --non-interactive --json
      --task "P3 official route smoke: verify brick build preset_task path
      records evidence without using --large or a third route."
      --adapter adapter:local
      --building-id cr-v4-p3-official-route-smoke-0629a
      --output-root /Users/smith/.brick/project/brick-protocol/buildings
      --overwrite-existing --timeout 120

  evidence_root:
    /Users/smith/.brick/project/brick-protocol/buildings/
    cr-v4-p3-official-route-smoke-0629a

  build_input_mode: preset_task
  plan_shape: graph
  walker_mode: dynamic
  frontier_kind: complete
  materialized lanes:
    design = adapter:codex-local
    review = adapter:gemini-local
    closure = adapter:codex-local
  reporter evidence:
    local-inbox delivered
    slack delivered with provider_response_status_class=slack_ok_true

Full design-first graph official route:
  command:
    .venv/bin/brick build --non-interactive --json
      --graph project/brick-protocol/status/kernel/GOAL/
      cr-v4-p3-full-design-first-graph-0629b.json
      --output-root /Users/smith/.brick/project/brick-protocol/buildings
      --overwrite-existing --timeout 900

  evidence_root:
    /Users/smith/.brick/project/brick-protocol/buildings/
    cr-v4-p3-full-design-first-graph-0629b

  build_input_mode: graph_packet
  plan_shape: graph
  walker_mode: dynamic
  frontier_kind: complete
  customer_visible_not_ready: false
  materialized shape:
    design
    Gemini design-axis QA
    Codex plan confirmation closure
    parallel Codex work lanes A/B
    lane QA: Codex code QA + Gemini axis QA
    fan-in integration closure
    final QA: Codex code QA + Gemini axis QA
    Codex final closure

  hard fan-in observation:
    p3-full-final-code-qa returned transition_concern_evidence.
    p3-full-final-code-qa row carried transition_concern_adoption=advisory.
    raw/link.jsonl remained forward through p3-full-final-closure.
    The concern was recorded as Agent evidence, not pre-closure Link adoption.

Easy declaration skill chain:
  agent/skills/building-sizing-method/SKILL.md sizes the graph shape.
  agent/skills/brick-task-author/SKILL.md submits only official build input:
    preset_task via brick build --task/--preset
    graph_packet via brick build --graph
  The same wording is preserved in brick/templates/skills for projection.
  The chain says "this is big; design first, split it, and run the lanes in
  parallel" and maps it to the P3 design-first fan-out/fan-in shape without
  introducing --large or a separate runner.
```

Checker/profile evidence run on 0629:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile building_skill_preset_agent_tool_hardening

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py --profile brick_cli_entrypoint

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py --profile driver_public_intake_seal

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile bounded_agent_proposed_routing_loop
```

Observed result: all four profiles exited 0.

Narrowly proven as support evidence:

```text
- public CLI build surface admits preset_task and graph_packet, not --large
- hidden _p3_easy_large graph helper remains absent/fail-closed under the
  inspected checker
- driver public intake seal does not expose launch_assembled_building as a
  customer route
- customer graph template-owned override rejection is present on the graph
  sandbox wrapper
- hard fan-in source-position QA/Inspector/evidence lanes can return local
  transition_concern_evidence without pre-closure Link adoption / reroute / HOLD
- closure-synthesis remains the Link-facing transition concern source in hard
  fan-in
- adopted transition_concern reason_refs that are absolute paths, escaping
  work/step-outputs paths, or spelling-bypass path forms HOLD loudly through
  runtime_handoff_address_unresolved_in_ledger and are not delivered to Agent
  input
- runtime/reroute recording contract profile remains green, including the
  bounded agent-proposed routing loop evidence
- one real `brick build` preset_task smoke created a complete evidence root and
  reporter/Slack delivery observations
- one real `brick build --graph` full design-first official Building completed
  through Codex/Gemini design QA, parallel work lanes, lane QA, integration,
  final dual QA, and Codex closure
- the full graph run observed a QA transition concern without pre-closure HOLD
  or reroute; the concern stayed advisory/local until closure
- the COO/task-author skill chain preserves the easy declaration path:
  building-sizing-method produces the shape; brick-task-author submits
  preset_task or graph_packet to the single official build route
```

Three-axis reading:

```text
Brick:
  route grammar and template-owned return/carry materialization are protected by
  composition / driver / CLI checker evidence.

Agent:
  source-lane QA/Inspector/evidence returns remain local observations in hard
  fan-in. Their returned facts do not choose Movement or target.

Link:
  fan-in internal edges remain forward. Closure-synthesis is the Link-facing
  concern source; Movement remains forward/reroute only.

Support:
  CLI, driver, walker, checker, reporter, and Slack remain evidence/recording
  surfaces. The smoke proves the official route can record evidence; it does not
  prove provider quality or customer-ready completion.
```

0629 movement recommendation:

```text
FORWARD from the old P3 hard fan-in blocker to the next P3 proof slice.
Do not call the whole P3 customer-ready phase complete yet.
```

Remaining risk:

```text
fresh customer comprehension remains not proven.
live provider reliability remains not proven.
semantic quality of generated graph choices remains not proven.
fully automatic natural-language graph generation without COO/operator
declaration remains not proven.
P7/P8 fresh-machine and dogfood capstone remain not proven.
```

## Attack Review Delta

Two independent attack reviews originally found P3 was not route-sealed. The
0629 operator recheck closes the focused route/template/hidden-helper slices as
support evidence, but the broad large-work proof remains open:

```text
HIGH:
- the full large/risky design-first graph is not yet proven by a live preset or
  fixture.

CLOSED FOCUSED SLICE:
- public graph_packet template authority is checked: authored
  required_return_shape / carries_forward_fields are rejected for ordinary P3.
- hidden _p3_easy_large_graph_packet / --large is absent or fail-closed under
  the inspected customer CLI checker.
- launch_assembled_building remains present but is classified and checked as an
  internal/non-customer helper; it is not public-exported as a customer route.
- hard fan-in QA source-lane transition_concern_evidence is local until closure
  when the graph/materializer stamps transition_concern_adoption=advisory on
  fan-in source nodes and the graph projection preserves that marker into the
  walker step.
- adopted transition_concern reason_refs path escape attempts HOLD loudly and
  are not delivered to Agent input.
```

Therefore P3 broad closure remains HOLD. The current plan has moved past the
old route-seal blockers and is now waiting on full large/risky official graph
proof, not another --large or return-shape repair.

0629b update: the full large/risky design-first official graph proof slice is
now closed as support evidence by `cr-v4-p3-full-design-first-graph-0629b`.
P3 broad closure still remains HOLD until the easy task-to-graph declaration
surface, customer comprehension, live-provider limits, and later fresh-machine /
dogfood proof are bounded.

0629c update: the easy declaration guidance slice is now checker-proven as
support evidence through `coo_operating_chain` and
`building_skill_preset_builder_composition`. The proven surface is
operator/COO-declared sizing plus official `brick build --task/--preset` or
`brick build --graph`, not autonomous natural-language route selection by
support.

## 0629 Hard Fan-In Runtime Repair Evidence

Measured bug:

```text
composition/materialization stamped the source-lane hard fan-in policy, but
plan_graph projection dropped transition_concern_adoption before the dynamic
walker saw the step. Runtime then treated QA source-lane concern evidence as
ordinary Link adoption input and paused/rerouted before closure.
```

Repair:

```text
composition_compose.py:
  stamps transition_concern_adoption=advisory on fan-in source nodes whose
  return shape is template-owned.

plan_graph.py:
  preserves step-local transition_concern_adoption when projecting graph plans
  into walker linear steps.

walker_kernel.py:
  treats advisory transition_concern_evidence as local Agent evidence and walks
  declared fan edges forward.

case_runners/profile:
  negative probe proves a source QA concern does not produce pre-closure HOLD or
  reroute, and closure receives all QA source step-output refs.
```

Current focused support evidence:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
  => passed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml
  => passed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/building_operator_driver0.yaml
  => passed

PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q support/operator support/checkers
  => passed

git diff --check -- support/operator/walker_kernel.py \
  support/operator/composition_compose.py support/operator/plan_graph.py \
  support/checkers/lib/case_runners.py \
  support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
  => passed
```

## 0629 Reason Refs Runtime Safety Evidence

Measured route:

```text
Agent returns transition_concern_evidence.
The concern is adopted under declared Link policy / budget.
Runtime mail reads the recorded transition-concern row from the Building ledger.
Path-shaped reason_refs may ride only when they resolve inside the same
Building root's work/step-outputs subtree.
```

Existing checker proof:

```text
support/checkers/check_bounded_agent_proposed_routing_loop0.py mail-5:
  - work/step-outputs/../../../other-building/raw/secret.json => HOLD
  - /work/step-outputs/... absolute path => HOLD
  - Work/Step-Outputs/../../../other-building/raw/secret.json => HOLD
  - work/./step-outputs/../../escape/x.json => HOLD
  - work//step-outputs/../../escape/x.json => HOLD
  - real in-subtree work/step-outputs/.../step-output.json still rides

All HOLD cases require hold_reason beginning with:
  runtime_handoff_address_unresolved_in_ledger

The checker also verifies the rejected refs are not delivered through
link_handoff_refs to Agent input.
```

Current focused support evidence:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/driver_public_intake_seal.yaml
  => passed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml
  => passed
```

## Implementation Plan

1. Route seal - focused evidence closed.

```text
Checker proves official public modes are only preset_task and graph_packet.
Any --large or hidden large helper is absent, deprecated, or fail-closed.
Assembly helpers such as launch_assembled_building must be closed to customer
use, reclassified as internal/non-customer support, or routed through the same
official customer seam before they can remain admitted.

Current evidence:
  brick_cli_entrypoint profile green
  driver_public_intake_seal profile green
```

2. Template authority seal - focused evidence closed for ordinary P3 graph_packet.

```text
For every templated node, materialize:
- brick_template_refs from brick/templates/bricks/<kind>/brick.md
- brick_instruction_body from brick.md
- required_return_shape from return.yaml
- carries_forward_fields from the template for ordinary P3

Operator declarations may choose kind/road; ordinary P3 graph_packet input must
not re-author these fields. If an expert fully-declared graph path keeps author
overrides, it must be a separate admitted path with a separate checker and not
the customer Easy Building route.

Current evidence:
  brick_cli_entrypoint profile rejects customer graph_packet authored
  required_return_shape / carries_forward_fields.
```

3. Easy declaration surface.

```text
Update the Building authoring guidance/skill surfaces so the operator can say:
"this is big; design first, split it, and run lanes"

The surface should produce official graph_packet or preset_task input, not a
separate runner.

Current evidence:
  coo_operating_chain profile green
  building_skill_preset_builder_composition profile green
  README / quickstart / launch-guide / setup wording updated by official
  Building cr-v4-p3-customer-wording-route-0629a.
  Customer docs now describe one public execution surface, `brick build`, with
  preset_task (`--task` / `--preset`) and graph_packet (`--graph`) input modes.
```

4. Large-work materialization.

```text
Design-first graph is built after design evidence is available.
Do not hardcode a universal "large" topology.
Sizing is task-aware and operator/COO declared; support does not choose route.
```

5. QA / closure lanes.

```text
Codex code/regression QA and Gemini-local axis/evidence QA are separate lanes.
QA lanes may inspect/probe but must not source mutate.
Codex closure records evidence and unresolved deltas.
Hard fan-in QA / Inspector / evidence lanes may return local concerns, but those
concerns are not Link-facing until closure-synthesis. Closure-synthesis alone
may emit the Link-facing transition_concern_evidence for the hard fan-in cohort.
```

## Exit Checks

```text
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile driver_public_intake_seal
python3 -m compileall -q support/operator support/connection support/checkers
git diff --check
```

P3 closure still needs focused proof for:

```text
closure-origin transition_concern_evidence remains adoptable under declared
policy and budget inside that full graph
fresh customer comprehension beyond wording evidence
live provider reliability limits
semantic quality limits for generated graph choices
```

## Movement

Recommendation:

```text
FORWARD from the old hard fan-in and customer wording slices to the next P3
proof slice.

HOLD broad customer-ready claims until fresh customer comprehension, provider
reliability limits, and P7/P8 proof remain bounded and explicit.
```

## Not Proven

```text
fresh customer comprehension
live provider completion
Slack delivery reliability
semantic quality of generated graph choices
fresh-machine official route
autonomous natural-language route selection by support
P7/P8 customer-ready proof
```
