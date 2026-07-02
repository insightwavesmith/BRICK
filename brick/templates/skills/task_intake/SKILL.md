---
name: task_intake
description: Use when turning a Brick task source into non-binding Building design candidates.
---

# Task Intake Skill

Use this Agent resource to read a task source and prepare non-binding Building
design candidates.

## Project Check First (프로젝트 체크 선행)

The project check comes BEFORE the task. The first intake question of a NEW
work conversation is not "what is the task" but:

```text
어느 프로젝트의 일인가? (which project vessel does this work belong to?)
```

A project is the vessel (그릇) the building's evidence accumulates in. Its
membership path is `project/<id>/buildings/`, carried on confirmed intent as
`project_ref: project:<id>`.

```text
human names a vessel that exists and is declared
  -> carry it as the intent's project_ref; the output root derives through
     buildings_root_for (the single seam); an undeclared / charterless vessel
     is refused loudly at intake, before any run.
human names NO vessel, or names a vessel that does not exist
  -> guide to the project-creation skill FIRST (charter -> declaration ->
     vessel), then return to this intake. Do not invent a vessel silently.
```

The ref-less project #1 fallback (`project/brick-protocol/`) is a support
compatibility default, not an intake answer. For NEW work, still ask and record
the project choice or the explicit decision to stay in project #1.

## Composition-First Intake Rule

Task intake must not pre-bake every request into a fixed
`work -> QA -> closure` or "launch -> Agent work -> QA -> closure ->
disposition" pipeline. That line is one possible graph shape, not the intake
default.

Extract enough task evidence to let the COO compose:

```text
LLM(s) = brain
Brick KIND(s) = hands
Graph = nervous system
```

Returned candidates name needed Brick KINDs, fan-out/fan-in points,
verification lenses, synthesis points, and LLM / adapter casting evidence. They
do not choose Link Movement, route targets, success, or quality.

If the task cannot yet be expressed as LLM + Brick KIND + Graph, record the
missing field or skill-chain gap and hand shape work to
`skill:building-sizing-method` / `skill:building-coordination`. Do not fall back
to the stale fixed pipeline.

## Inputs

Read only declared refs:

```text
brick/templates/tasks/source-template.md
brick/templates/shapes/catalog.yaml
brick/templates/shapes/shapes.yaml
brick/templates/bricks/plan/brick.md
brick/templates/bricks/design/brick.md
brick/templates/bricks/development/brick.md
brick/templates/bricks/work/brick.md
brick/templates/bricks/review/brick.md
brick/templates/bricks/inspect/brick.md
brick/templates/bricks/code-attack-qa/brick.md
brick/templates/bricks/axis-attack-qa/brick.md
brick/templates/bricks/evidence-integrity/brick.md
brick/templates/bricks/closure/brick.md
brick/templates/presets/fast-fix.md
brick/templates/presets/design-build-parallel.md
brick/templates/presets/high-risk-change-inspected.md
brick/templates/presets/governed-change-review.md
brick/templates/presets/app-feature-basic.md
brick/templates/presets/app-feature-inspected.md
brick/templates/presets/docs-simple-review.md
brick/templates/presets/portfolio-sequence.md
brick/templates/presets/brick-protocol-engine-feature-hard.md
brick/templates/presets/brick-protocol-constitution-change.md
brick/templates/presets/brick-protocol-dashboard-dev-basic.md
brick/templates/presets/brick-protocol-dashboard-dev-inspected.md
brick/templates/presets/brick-protocol-portfolio-driver.md
brick/templates/presets/brick-protocol-post-d-cleanup.md
brick/templates/building-design-contract.yaml
AGENTS.md
project/brick-protocol/PROGRESS.md
active phase spec or support record
```

## Returned Shape

Return through `AgentFact(received_work, returned)` with:

```text
task_source_observations
missing_fields
user_request_interpretation
first_line_contract_candidate
deep_intake_question_tree
extraction_targets
follow_up_questions
field_gap_questions
extracted_task_fields
task_md_candidate
task_source_draft
task_md_confirmation_state
candidate_shapes
candidate_chain_presets
candidate_catalog_scope
canonical_chain_preset_ref_candidate
compat_chain_preset_ref_notes
selected_shape_ref_candidate
preset_vs_manual_candidate
preset_vs_manual_case_analysis
route_family_candidate
candidate_route_family
route_family_case_analysis
route_family_ladder_notes
manual_graph_candidate
graph_movement_case_analysis
graph_movement_case_candidates
fan_out_candidate
fan_in_first_candidate
fan_in_frontier_candidate
fan_in_policy_candidate
closure_synthesis_policy_candidate
reroute_replay_candidate
reroute_replay_readiness_questions
reroute_replay_scope_candidate
transition_concern_evidence_questions
qa_lane_observations_candidate
hard_fan_in_qa_policy_candidate
declared_boundary_candidate_refs
route_policy_candidate_refs
route_replay_plan_candidate_refs
slack_payload_candidate
payload_delivery_scope_notes
partial_qa_reuse_not_proven
startup_path_candidate
no_preset_fallback
candidate_brick_rows
candidate_agent_rows
candidate_link_rows
honest_report_questions
boundary_questions
read_scope_notes
human_gate_questions
write_scope_notes
missing_evidence_questions
review_gate_questions
not_proven_candidates
remaining_delta_candidates
evidence_refs
proof_limits
not_proven
```

These fields are non-binding Agent return evidence. Caller / COO must declare
`catalog_scope`, active `chain_preset_ref` or `no_preset_fallback`, and the
active plan or intent before execution. `selected_shape_ref` is optional and no
longer has to match the preset or declared shape.

`candidate_agent_rows` may be informed by the read-only
`render_agent_candidate_packet(role_need, write_need)` support surface. It lists
capability matches and mechanical reasons only; it does not rank, recommend,
pick among candidates, or judge quality. Ambiguous packets still require caller
/ COO declaration.

Preset suggestions may be informed by read-only
`render_preset_ranking_packet(selection_hint, catalog_scope=None)`. Ranking is
mechanical hint-token overlap, advisory only, and never auto-applies; the run
still needs an explicit confirmed preset.

Return the operating-chain fields in this order:

```text
사용자 요청 해석
-> task intake 질문
-> task.md 후보
-> task.md 확정
-> catalog_scope 후보
-> preset vs manual 후보
-> route_family_case_analysis
-> graph_movement_case_analysis
-> fan_in_first_candidate
-> startup path 후보
```

For P3 work, this feeds the existing `brick-task-author` chain: confirmed task
source -> compact graph candidate (`build` / `fan`) -> operator-facing
`build()`. Raw graph packet CLI handoff is retired.

`task.md 확정` means Brick-owned input evidence only; it is not a run, source
truth, success or quality judgment, Movement authority, target choice, or
permission to jump from `task.md` directly to `run_building_plan`.

`route_family_candidate`, `candidate_route_family`, and
`graph_movement_case_analysis` are also
non-binding. They describe which declared grammar may fit the task; they do not
choose Link Movement, target, replay scope, or success.

## Conversational Intake Loop

Task intake must run as an interview loop, not as a checklist dump.

Use one core question at a time:

```text
1. Pick the next highest-value extraction target.
2. Ask exactly one core question.
3. Wait for the user's answer.
4. Extract candidate task fields from that answer.
5. State the interpretation back to the user.
6. Ask "이 뜻 맞나?" or an equivalent confirmation.
7. Only after confirmation or correction, ask the next question.
```

Use answer-derived follow-up questions when an answer reveals a gap; name the
field being extracted. Interview from real situation, behavior, constraints,
workaround, desired progress, pain, and blocked decisions before solution
shape.

Do not ask several task-intake questions in one message unless the user asks
for a questionnaire. Do not advance to shape, preset, or active plan until the
current interpretation has been confirmed or the remaining ambiguity is named.

## Rules

Do:

```text
ask the project check question ("어느 프로젝트의 일인가?") BEFORE task questions
guide to project-creation FIRST when no vessel is named or the named vessel
  does not exist; never invent one silently
read the task source
interpret the user request before task intake questions
name missing or ambiguous fields
ask exactly one core intake question at a time
state the inferred task fields back to the user before asking the next question
ask answer-derived follow-up questions for gaps
extract LLM / Brick KIND / Graph composition evidence before route candidates
mark a missing field or skill-chain gap when the task cannot yet be expressed
  as LLM(s) + Brick KIND(s) + Graph
draft a non-binding first_line_contract_candidate
draft a non-binding deep_intake_question_tree
name extraction_targets for Trigger Event, User Context, Desired Information,
  Current Workaround, Pain Points, Blocked Decisions, Primary Signals, Status
  Vocabulary, Required Actions, and Forbidden Actions
name follow_up_questions and field_gap_questions for missing extracted values
draft extracted_task_fields and task_source_draft as candidate evidence only
draft task_md_candidate as candidate evidence only
mark task_md_confirmation_state before catalog scope candidates
name candidate_catalog_scope as `common` or `brick_protocol_dogfood`
name candidate_chain_presets from the chosen catalog scope
note that `brick_protocol_dogfood` presets are local Brick Protocol development
  candidates, not common export
resolve alias / compatibility input to canonical_chain_preset_ref_candidate
preserve compat_chain_preset_ref_notes as compatibility evidence only
draft selected_shape_ref_candidate as an OPTIONAL tag — it no longer has to
  match the preset or the caller / COO declared shape (membership not enforced)
name route_family_candidate / candidate_route_family only as one of:
  existing_declared_plan
  linear_chain_preset
  preset_guided_graph
  full_manual_graph
  declared_portfolio
  declared_repair_replay
name preset_vs_manual_candidate and preset_vs_manual_case_analysis before
  route_family_case_analysis
name route_family_case_analysis before choosing graph, portfolio, repair/replay
  grammar, or a startup path
name route_family_ladder_notes before any startup path candidate
name manual_graph_candidate when the task needs declared nodes and edges
  instead of a linear chain preset
name graph_movement_case_analysis and graph_movement_case_candidates when the
  task or preset implies fan-out, fan-in, parallel QA, repair, or replay:
  all_forward
  single_reroute_concern
  same_target_duplicate_reroute_concerns
  conflicting_reroute_targets
  insufficient_evidence_hold
  reroute_to_work_full_replay
name no-link / materialized-forward distinction for G1 route-default policy:
  compact users do not author Link rows; support materializes forward rows by
  default; reroute/HOLD requires concern evidence plus declared/adopted policy
name fan_out_candidate when one Brick boundary declares multiple outgoing lanes
name fan_in_first_candidate and fan_in_policy_candidate as fan-in-first when
  all declared QA bodies and verification lanes must be collected before
  closure-synthesis
name fan_in_frontier_candidate when branch returns are still missing
name closure_synthesis_policy_candidate as synthesis Brick only, not final
  success or Movement authority
name reroute_replay_candidate and reroute_replay_readiness_questions before
  claiming a repair/replay path can run
name transition_concern_evidence_questions for possible non-binding Agent
  transition concerns only when the Brick return shape declares
  `transition_concern_evidence`
name hard_fan_in_qa_policy_candidate when the task implies hard fan-in QA:
  QA lanes return their own Brick fields without Link-facing
  `transition_concern_evidence`, and closure-synthesis alone
  returns Link-facing `transition_concern_evidence`
name qa_lane_observations_candidate for hard fan-in QA lane returns
name declared_boundary_candidate_refs, route_policy_candidate_refs, and
  route_replay_plan_candidate_refs as questions or candidates only
name reroute_replay_scope_candidate as full affected-segment replay unless a
  later freshness/work-packet Building proves partial reuse
name slack_payload_candidate and payload_delivery_scope_notes only as support
  delivery payload notes, not as route or Movement authority
name partial_qa_reuse_not_proven when the task asks to reuse prior QA outputs
name startup_path_candidate only as one of:
  A: brick_protocol.support.operator.composition_intent.materialize_building_intent
  B: brick_protocol.support.operator.composition_intent.render_declared_step_template_plan
  C: brick_protocol.support.operator.composition_compose.compose_building
  D: brick_protocol.support.operator.run.run_building_plan
  E: brick_protocol.support.operator.driver.run_declared_portfolio
  F: brick_protocol.support.operator.auto_repair_replay.run_declared_auto_repair_replay_case
name no_preset_fallback when no chain preset should drive the work
name declaration / evidence refs when present:
  work/task.md
  work/building-intake.json
  work/preset-expansion.json
  work/declared-building-plan.json
  work/link-launch-policy.json
draft Brick / Agent / Link rows as candidates
name honest_report_questions for observed_evidence, made_changes,
  blocked_or_missing_evidence, open_questions, not_proven, remaining_delta,
  review_needed, and transition_concern_evidence
name Brick / Agent / Link boundary questions
name read scope and write scope notes
name human gate questions
name missing evidence questions
name proof limits and not_proven
```

Do not:

```text
invent or silently create a project vessel
silently default a NEW work conversation into project #1 without asking
declare active `chain_preset_ref`
declare active `route_family_candidate`
declare active `candidate_route_family`
declare catalog_scope, shape, preset, graph, route family, startup path, or plan
  candidates as source truth
declare the active shape
declare the active Building Plan
choose Link Movement
choose route targets
choose graph Movement cases as final disposition
default every task to a fixed work -> QA -> closure pipeline
hide a missing LLM / Brick KIND / Graph composition by using the stale fixed
  pipeline
jump from `task.md` directly to `run_building_plan`
skip graph movement case analysis when fan-out/fan-in/replay is implied
turn `slack_payload_candidate` into route, success, quality, or Movement proof
turn Slack dogfood payload into the goal or success proof
center Claude master-sequence or engine details before task intake and route ladder
materialize preset expansion
materialize task.md
write `project/brick-protocol/buildings/<building-id>/work/task.md`
ask a batch checklist of intake questions by default
advance from intake to shape/preset/active plan without confirmation
turn transition_concern_evidence into Link Movement
let hard fan-in QA lanes return Link-facing transition_concern_evidence
turn fan-in QA lane observations into Movement, target choice, success, or quality proof
match route policies
materialize repair or replay steps
present `target_word` as Link Movement
present `selected_preset_ref` as canonical proof
present closure_synthesis_policy_candidate as final close or quality approval
claim partial QA reuse is valid without consumed_input_refs / freshness evidence
claim CLI startup
present native_dispatch or building_operation as the runner
return success/failure/approved/good_enough/quality verdicts
judge source truth
judge success
judge quality
store credentials or session bodies
call providers
write files
```

## Proof Limits

This skill is an Agent resource. It is not source truth, success judgment,
quality judgment, Movement authority, provider-native projection, or automatic
Building Plan authoring.
