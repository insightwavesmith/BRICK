---
name: task_intake
description: Use when turning a Brick task source into non-binding Building design candidates.
---

# Task Intake Skill

Use this Agent resource when a Building designer needs help reading a task
source and preparing Building design candidates.

## Project Check First (프로젝트 체크 선행)

The project check comes BEFORE the task. The first intake question of a NEW
work conversation is not "what is the task" but:

```text
어느 프로젝트의 일인가? (which project vessel does this work belong to?)
```

A project is the vessel (그릇) the building's evidence accumulates in —
membership is the path (`project/<id>/buildings/`), declared on the confirmed
intent as `project_ref: project:<id>`.

```text
human names a vessel that exists and is declared
  -> carry it as the intent's project_ref; the output root derives through
     buildings_root_for (the single seam); an undeclared / charterless vessel
     is refused loudly at intake, before any run.
human names NO vessel, or names a vessel that does not exist
  -> guide to the project-creation skill FIRST (charter -> declaration ->
     vessel), then return to this intake. Do not invent a vessel silently.
```

The ref-less fallback to project #1 (`project/brick-protocol/`) is a
MECHANICAL compatibility default in support, not an intake answer: for a NEW
work conversation the skill still asks the project question and records the
human's answer (or the explicit decision to stay in project #1) instead of
defaulting silently.

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
project/brick-protocol/status/kernel/current-working-context.md
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

These candidate fields are non-binding Agent return evidence. The caller / COO
must declare `catalog_scope`, active `chain_preset_ref` or explicit
no-preset/manual fallback, and the active Building Plan or fully declared
intent before execution. `selected_shape_ref` is now an OPTIONAL tag — it no
longer has to match the preset or the caller / COO declared shape.

`candidate_agent_rows` is backed by the READ-ONLY support surface
`brick_protocol.support.connection.building_design_toolkit.render_agent_candidate_packet(role_need, write_need)`.
It records EVERY Agent whose CAPABILITY (lane + writer policy) matches the brick
NEED, plus a MECHANICAL match reason per row (lane + write scope only). It does
NOT pick among candidates, rank them, recommend one, or judge agent quality.
When the packet reports `ambiguous` (>= 2 candidates,
`required_disposition_owner: caller-or-coo`), the caller / COO chooses and then
declares a `default_agent` hint or an agent override; a single candidate still
auto-resolves through the matcher. This packet is the informed view BESIDE the
matcher's fail-closed >= 2 halt, never a replacement for it.

Preset suggestions come from the READ-ONLY, NON-BINDING support surface
`brick_protocol.support.connection.building_design_toolkit.render_preset_ranking_packet(selection_hint, catalog_scope=None)`.
Given the HUMAN-declared `selection_hint` it lists the matching chain presets
ranked by MECHANICAL hint-token overlap against each preset's own declared text
(NOT a quality judgment, NOT a recommendation-to-use). It is advisory only: the
COO chooses and declares the active preset. The run STILL requires an explicit
confirmed preset — `materialize_building_intent` hard-refuses a no/blank
`chain_preset_ref`, so the ranking NEVER auto-applies.

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

`task.md 확정` means the task source is confirmed as Brick-owned input evidence
only. It is not a Building run, source truth, success judgment, quality
judgment, Movement authority, target choice, or permission to jump directly to
`run_building_plan`.

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

Use follow-up questions when the answer reveals a gap. The follow-up must be
derived from the previous answer and must name the field it is trying to
extract.

Reference-derived interviewing principles:

```text
The Mom Test style: ask about the user's real situation, past/current behavior,
constraints, and workaround before asking about a solution.
Jobs-to-Be-Done style: extract the progress the user wants, the current
workaround, the pain, and what is blocking the switch.
Continuous discovery style: separate opportunity/problem evidence from
solution candidates.
Double Diamond style: discover and define before develop or deliver.
User interview style: ask open-ended questions and follow up to learn more.
```

Do not ask several task-intake questions in one message unless the user asks
for a questionnaire. Do not advance to shape, preset, or active plan until the
current interpretation has been confirmed or the remaining ambiguity is named.

## Rules

Do:

```text
ask the project check question ("어느 프로젝트의 일인가?") BEFORE the task questions
guide to the project-creation skill FIRST when no vessel is named or the named
  vessel does not exist; never invent a vessel silently
read the task source
interpret the user request before task intake questions
name missing or ambiguous fields
ask exactly one core intake question at a time
state the inferred task fields back to the user before asking the next question
ask answer-derived follow-up questions for gaps
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
name reroute_replay_scope_candidate as full replay of the affected declared
  segment unless a later freshness/work-packet Building proves partial reuse
name slack_payload_candidate and payload_delivery_scope_notes only as support
  delivery payload notes, not as route or Movement authority
name partial_qa_reuse_not_proven when the task asks to reuse prior QA outputs
name startup_path_candidate only as one of:
  A: brick_protocol.support.operator.composition.materialize_building_intent
  B: brick_protocol.support.operator.composition.render_declared_step_template_plan
  C: brick_protocol.support.operator.composition.compose_building
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
name honest report questions for observed_evidence, made_changes,
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
