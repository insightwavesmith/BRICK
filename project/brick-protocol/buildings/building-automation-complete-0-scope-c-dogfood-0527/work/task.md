# BUILDING-AUTOMATION-COMPLETE-0 Task Source Evidence

task_slice: TASK-SOURCE-EVIDENCE-PLACEMENT-0 / END-TO-END-AUTO-BUILDING-DOGFOOD-0
owner_axis: Brick
evidence_kind: task_source_instance

## Objective

Prove the current BUILDING-AUTOMATION-COMPLETE-0 dogfood path inside a Building
evidence root.

## First-Line Contract

This task must keep active task input under
`project/brick-protocol/buildings/<building-id>/work/task.md`, expand only
caller/COO-declared presets into Brick / Agent / Link rows, walk a declared
Building Plan, record QA route_request evidence, materialize a Link decision
packet from declared route_replay_plan evidence, replay existing Brick
boundaries as attempt-N, and avoid support-chosen Movement or runtime retry.

## Context / Why Now

The BUILDING-AUTOMATION-COMPLETE-0 design chain identified that the remaining
automation gap is not a new runtime loop. The needed proof is a declared road:
task evidence, preset/plan declaration, run, QA route_request, Link reroute
decision, repeated boundary attempts, and closure.

## Required Sources

- AGENTS.md
- project/brick-protocol/status/kernel/current-working-context.md
- support/docs/spec/brick-protocol-building-automation-complete-design-chain-0-0527.md
- brick/templates/shapes/registry.yaml
- brick/building_plans/building-automation-complete-0-scope-c-dogfood.yaml
- link/route_policies/basic_qa_repair.yaml
- support/operator/building_operation.py
- support/operator/route_materialization.py
- support/operator/auto_repair_replay.py
- support/operator/plan_validation.py
- support/recording/step_outputs.py

## Desired Output

- A Building evidence root with `work/task.md`.
- Step outputs for dev attempt 1, QA attempt 1, dev attempt 2, QA attempt 2,
  and closure.
- A QA `route-request.json` returned as non-binding Agent evidence.
- A Link decision packet evidence view over a materialized Link row.
- `route_replay_plan.max_attempts` validated as Link-owned declared carry.

## Brick / Agent / Link Boundary

Brick owns the task source, Building Plan, work contracts, and repeated Brick
boundaries.

Agent receives each Brick work packet and returns observations through the
closed `AgentFact(received_work, returned)` shape.

Link owns Movement, target, route_replay_plan, and max_attempts carried inside
that route_replay_plan. QA route_request is non-binding evidence only.

## Read Scope / Write Scope

Read scope:

- AGENTS.md
- project/brick-protocol/status/kernel/current-working-context.md
- support/docs/spec/
- brick/templates/shapes/registry.yaml
- brick/building_plans/
- link/route_policies/
- support/operator/
- support/recording/
- support/checkers/profiles/

Write scope:

- Existing support helpers needed for declared plan preflight and evidence
  observation.
- Existing checker profiles.
- This Building evidence root.

Must not write:

- New axis-root case/template/binding/dogfood folders.
- New support/operator modules.
- New support/checkers/check_*.py files.
- Provider-native projection config.

## Constraints / Out of Scope

Do not admit RoutePolicyFact. Do not create a scheduler, queue, retry runtime,
default GateFact, support-chosen route target, or Agent-selected Movement. Do
not classify success, failure, approval, or quality.

## Human / Review Gate

Routine Smith review does not stop this dogfood. If a new ownership conflict
appears, COO opens an ownership re-attribution phase before implementation.

## Honest Report Contract

Returned observations should use:

```text
observed_evidence
made_changes
blocked_or_missing_evidence
open_questions
not_proven
remaining_delta
review_needed
route_request_evidence
```

Returned observations must not include:

```text
success
failure
approved
good_enough
quality score
route_target
movement_choice
```

## Done Criteria

- `building_automation_complete_scope_c` profile passes.
- The Building root contains `work/task.md`.
- The Building root contains `route-request.json` for QA attempt 1.
- Replayed dev and QA attempts are recorded as attempt 2.
- No new `brick/tasks/*.md` active task instance is created.

## Risk

This dogfood proves declared automation mechanics, not semantic correctness of
future work or production runtime readiness.

## Proof Limits

This task source is Building input evidence only. It is not source truth,
success judgment, quality judgment, not Movement authority, provider
configuration, automatic shape selection, plan authoring, or route target
choice.
