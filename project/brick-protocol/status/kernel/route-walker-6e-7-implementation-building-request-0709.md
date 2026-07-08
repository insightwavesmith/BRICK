# Route V2 ⑥e / ⑦ Walker Integration Implementation Building Request — 0709

Status: implementation Building request candidate / COO order packet. This packet
does not implement code, does not run a Building, does not choose Link Movement,
does not judge success/quality, and does not make source truth. It turns the
already-landed ⑥e design into an actionable declared-Building request, while
preserving the implementation HOLD until Smith explicitly approves opening the
Building.

## 0. Source design and live evidence

```text
design: project/brick-protocol/status/kernel/route-v2-6e-walker-integration-design-0709.md
human-gate lineage:
  project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
  project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
  project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md
GOAL: project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Live code seams observed:

```text
walker transition concern path:
  brick_protocol/support/operator/walker_transition_concern.py
    _transition_concern_observation_from_step_result(...)
    _classify_reroute_target(...)

walker evidence snapshot path:
  brick_protocol/support/operator/walker_kernel.py
    process_one_node(...)
    write_plan["dynamic_walker_evidence"] = {...}

closed reroute/hold recording contract:
  brick_protocol/support/recording/walker_evidence.py
    build_reroute_adoption_record(...)
    build_hold_record(...)

Route V2 read-only view:
  brick_protocol/support/operator/route_v2_views.py
    render_route_v2_view(...)
    route_v2_policy_packet(...)
```

Live-code corrections already recorded in the ⑥e design:

```text
- route_policy is not currently a direct walker input; ⑥e must use declared/proven
  input or record route_policy_input_state=absent/blocked.
- reroute_adoption_record and hold_record are contract-derived closed shapes;
  Route V2 evidence should be a top-level dynamic_walker_evidence sibling list,
  not an undeclared nested field.
```

## 1. Building identity

```text
building_candidate: route-walker-6e-7-advisory-view-0709
catalog_scope: brick_protocol_dogfood
recommended_chain_preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
route_family_candidate: preset_guided_graph
startup_path_candidate: run_building_intake after task_source_ref + chain_preset_ref are confirmed
worktree_required: true
live_checkout_run_building_intake: forbidden
human_gate_state: requires_explicit_smith_approval_before_launch
```

Why this preset:

```text
This is high-risk support runtime/checker work touching walker_kernel.py and
walker_resume.py behavior, with Link/Movement boundary risk. It needs design ->
work -> code attack QA -> axis attack QA -> evidence integrity -> closure.
It is not a quick_fix or direct_preset candidate.
```

Direct preset admission:

```text
direct_preset: rejected
reason: walker runtime seam, route/Movement boundary, resume parity, checker
coverage, possible recording-contract impact.
```

## 2. Work contract

Implement SHAPE A from the ⑥e design:

```text
Add a read-only, advisory Route V2 view observation beside dynamic walker
evidence, without changing walker control flow, Movement choice, route target
selection, reroute/hold record contract, AgentFact shape, Link resources, or
concern_kind vocabulary.
```

Expected persistent shape:

```text
dynamic_walker_evidence["route_v2_view_observations"] = [
  {
    "kind": "route_v2_view_observation",
    "binding": "advisory",
    "adopted_as_movement": False,
    "reroute_ref": "<existing reroute/hold ref if any>",
    "source_step_ref": "<existing step ref>",
    "source_transition_concern_ref": "<existing concern ref>",
    "route_policy_input_state": "declared|absent|blocked",
    "route_v2_view": <render_route_v2_view packet>
  }
]
```

The observation is support evidence only. It must not feed:

```text
- gate_sequence_decision
- _classify_reroute_target
- frontier_driver queue control
- node_reroute_budget / node_landings
- resume disposition choice
- Link Movement / target selection
```

## 3. Allowed / forbidden scope

Allowed candidate write scope:

```text
brick_protocol/support/operator/walker_kernel.py
brick_protocol/support/operator/walker_resume.py
brick_protocol/support/checkers/**
brick_protocol/support/checkers/profiles/**
project/brick-protocol/status/kernel/route-walker-6e-7-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Conditional write scope (only if proven necessary):

```text
brick_protocol/support/operator/route_v2_views.py
brick_protocol/support/operator/route_materialization.py
brick_protocol/support/recording/contracts.py
brick_protocol/support/recording/walker_evidence.py
```

These are not part of the recommended path. Touch them only if the Building
proves SHAPE A cannot be implemented as a top-level dynamic_walker_evidence
observation list without a contract extension.

Forbidden scope:

```text
brick_protocol/link/**
brick_protocol/agent/return_fact.py
brick_protocol/agent/**
new brick_protocol/support/operator/route_scope.py
new brick_protocol/support/operator/route_v2_engine.py
new concern_kind
success/quality/approved/good_enough/movement_choice/route_target authority fields
runtime scheduler/queue/retry ownership
project/brick-protocol/status/inbox/**
credentials, secrets, provider/session bodies
```

## 4. Required checker / proof plan

A ⑥e/⑦ implementation Building is not accepted by diff alone. It must prove:

```text
P1. verification_gap remains non_reroute in walker classification AND Route V2 view;
    no reroute occurs for verification_gap.
P2. hold|paused|held_for_coo_review as movement_candidate is rejected.
P3. forward|reroute as gate_state is rejected.
P4. forbidden authority keys (success/quality/movement/movement_choice/route_target)
    are rejected before Route V2 view render or walker evidence emission.
P5. forbidden route replay plan author_ref prefixes (support/Agent/provider/session/
    tool/hook/credential/token) remain rejected.
P6. dynamic_walker_evidence.route_v2_view_observations appears as advisory with
    adopted_as_movement=false.
P7. A before/after control-flow comparison proves walker reroute/hold decisions
    are byte-identical with and without the advisory observation.
P8. resume replay reads back or preserves route_v2_view_observations without
    recompute drift; resumed Movement matches recorded Movement.
P9. route_policy input is declared/proven, or route_policy_input_state records
    absent/blocked with no silent default load of basic_qa_repair.yaml.
P10. reroute_adoption_record and hold_record field sets remain unchanged unless
     recording contracts + checkers are explicitly updated.
P11. No route_scope.py, route_v2_engine.py, link/** mutation, agent/return_fact.py
     mutation, or new concern_kind appears.
P12. No success/quality/Movement authority is added to support.
```

Required focused commands before landing:

```text
python3 -m compileall -q brick_protocol
python3 brick_protocol/support/checkers/check_route_v2_views.py
python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
python3 brick_protocol/support/checkers/check_profile.py --profile link_routing_behavioral
python3 brick_protocol/support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
python3 brick_protocol/support/checkers/check_profile.py --profile <new-or-extended-route-walker-profile>
# clean detached worktree when landing code/resource changes:
python3 brick_protocol/support/checkers/check_profile.py --all
git diff --check
```

If the Building chooses to extend `core` coverage, it must still include focused
route/walker proof mapping P1-P12 to concrete commands/evidence.

## 5. Brick / Agent / Link rows candidate

Candidate route shape:

```text
Design Brick:
  return: precise implementation seam, files to touch, checker plan, edge cases,
  reading_scope_map. Must preserve SHAPE A.

Work Brick:
  return: changed_files, made_changes, commands_run, observed_evidence,
  blocked_or_missing_evidence, not_proven.

Code-attack QA Brick:
  return: attempts to make observation control flow binding, to silently default
  route_policy, to mutate record contracts accidentally, or to bypass forbidden keys.

Axis-attack QA Brick:
  return: Brick/Agent/Link attribution check; proves support did not author
  Movement/source truth/success/quality and did not mutate Link/Agent surfaces.

Evidence-integrity Brick:
  return: proof matrix P1-P12 -> command/evidence; clean worktree proof; no
  untracked inbox/building pollution in landing evidence.

Closure Brick:
  return: narrowly_proven, not_proven, remaining_delta, next_target_candidates,
  transition_concern_evidence if any.
```

Agent candidate notes:

```text
Use preset Agent rows. Do not expose model/provider in Brick rows. If Agent
selection is ambiguous, COO/Smith declaration chooses; support must not rank by
quality.
```

Link candidate notes:

```text
All default movement rows are forward unless an admitted closure/QA concern later
requires Link/COO reroute. This request itself supplies no Movement.
```

## 6. Edge cases the Building must handle

```text
- verification_gap with empty refs -> non_reroute observation, no reroute.
- verification_gap with replay plan supplied -> still non-reroute / no materialized reroute.
- implementation_gap with declared policy absent -> observation records absent/blocked, no default load.
- implementation_gap with declared policy present -> view materializes only as evidence, not control flow.
- gate_state="paused" and movement_candidate="reroute" stay separate.
- gate_state="reroute" raises / is rejected.
- movement_candidate="paused" raises / is rejected.
- forbidden keys in delta_qa_fact / transition concern / route policy are rejected.
- resumed run preserves the recorded advisory observation and does not recompute into drift.
```

## 7. GOAL landing requirements

Implementation Building must update:

```text
project/brick-protocol/status/kernel/route-walker-6e-7-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Report must include:

```text
- changed_files
- deleted_files: none or explicit list
- moved_files: none or explicit list
- commands_run with rc
- checker coverage mapping P1-P12 -> command/evidence
- not_proven
- remaining_delta
- whether ⑥e/⑦ can be considered landed or needs repair
```

## 8. Not proven by this request

```text
- No walker implementation is complete.
- No checker has been added for route_v2_view_observations.
- No resume parity is proven.
- No ⑦ route/walker integration is landed.
- No automatic repair/replay execution is approved.
- This request still needs Smith approval before launch.
```

## 9. Movement language

This request authors no Link Movement. It is a COO Building-order packet:

```text
gate_state: held_for_smith_implementation_approval
movement_candidate: none supplied by this packet
```
