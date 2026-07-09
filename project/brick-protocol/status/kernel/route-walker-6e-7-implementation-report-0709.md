# Route Walker 6e/7 Advisory View Implementation Report - 0709

Status: support evidence report. This file does not judge success or quality, does not choose Link Movement, and does not make source truth.

## Changed Files

```text
brick_protocol/support/operator/walker_kernel.py
brick_protocol/support/operator/walker_resume.py
brick_protocol/support/checkers/check_route_v2_views.py
brick_protocol/support/checkers/profiles/route_v2_walker_advisory.yaml
project/brick-protocol/status/kernel/route-walker-6e-7-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Deleted files: none.

Moved files: none.

## Implementation Observations

```text
walker_kernel.py:
  - adds support-only _route_v2_view_observation(...)
  - records dynamic_walker_evidence.route_v2_view_observations as a top-level sibling list
  - records binding=advisory and adopted_as_movement=false
  - records route_policy_input_state=declared|absent|blocked without default-loading a route policy
  - appends observations after existing concern observation / hold / adoption paths
  - leaves reroute_adoption_record and hold_record emitters unchanged

walker_resume.py:
  - carries already-written route_v2_view_observations back into the delegated forward walker
  - relies on kernel de-duplication to preserve recorded observations without duplicate replay rows

check_route_v2_views.py:
  - keeps sealed Route V2 view probes
  - adds live walker advisory evidence probes
  - compares reroute/HOLD records, frontier kind, and step order with advisory recording disabled vs enabled
```

## Commands Run

```text
python3 brick_protocol/support/checkers/check_route_v2_views.py
rc=0
observed: route_v2_views passed; includes advisory walker evidence and byte-identical control-flow comparison.

python3 -m compileall -q brick_protocol
rc=0

python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_walker_advisory
rc=1
observed: failed because project/brick-protocol/status/kernel/route-walker-6e-7-implementation-report-0709.md did not exist yet.

python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
rc=0
observed: profile passed; route_v2_views kernel check passed.

python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_walker_advisory
rc=0
observed: profile passed after report/GOAL files existed.

python3 brick_protocol/support/checkers/check_profile.py --profile link_routing_behavioral
rc=0
observed: profile passed.

python3 brick_protocol/support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
rc=1
observed: rejected evidence with cannot access local variable 'concern'; implementation bug in a gate-sequence HOLD branch.

python3 brick_protocol/support/checkers/check_bounded_agent_proposed_routing_loop0.py
rc=1
observed: standalone checker isolated the same undefined local variable.

python3 -m compileall -q brick_protocol
rc=0
observed: post-fix compile passed.

python3 brick_protocol/support/checkers/check_route_v2_views.py
rc=0
observed: post-fix focused checker passed.

python3 brick_protocol/support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
rc=0
observed: post-fix profile passed.

git diff --check
rc=0
observed: no whitespace errors.

python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_walker_advisory
rc=0
observed: final advisory profile passed.
```

## Checker Coverage Mapping

```text
P1 verification_gap remains non_reroute and no reroute:
  check_route_v2_views.py verification_gap live walker probe; vg_records must be empty and Route V2 view non_reroute=true.

P2 hold|paused|held_for_coo_review as movement_candidate rejected:
  check_route_v2_views.py gate/movement cross-over probes reject movement_candidate="paused".

P3 forward|reroute as gate_state rejected:
  check_route_v2_views.py gate/movement cross-over probes reject gate_state="forward" and gate_state="reroute".

P4 forbidden authority keys rejected:
  check_route_v2_views.py forbidden transition_concern_evidence keys reject movement, movement_choice, success, quality, route_target before walker evidence emission.

P5 forbidden route replay author_ref prefixes remain rejected:
  covered by existing route_materialization / route_v2_sealed_materialization profile coverage; no route replay plan authoring was added in this slice.

P6 dynamic_walker_evidence.route_v2_view_observations appears advisory:
  check_route_v2_views.py live walker probe requires kind=route_v2_view_observation, binding=advisory, adopted_as_movement=false.

P7 before/after control-flow comparison:
  check_route_v2_views.py monkeypatches the advisory append to no-op, reruns with append enabled, and compares reroute/HOLD records, frontier kind, and step order.

P8 resume replay preserves route_v2_view_observations:
  walker_resume.py carries existing route_v2_view_observations into declared_plan; check_route_v2_views.py pins that preservation text.

P9 route_policy input declared/proven or absent/blocked:
  walker_kernel.py records route_policy_input_state and does not load basic_qa_repair.yaml; live walker probe observes absent.

P10 reroute_adoption_record and hold_record field sets unchanged:
  implementation did not edit brick_protocol/support/recording/walker_evidence.py or recording contracts; P7 compares records before/after advisory append.

P11 no forbidden route_scope.py, route_v2_engine.py, link/**, agent/return_fact.py, new concern_kind:
  route_v2_walker_advisory profile pins forbidden paths absent and edits remain outside link/** and agent/**.

P12 no success/quality/Movement authority added to support:
  route_v2_view_observation proof_limits state not Movement authority; checker rejects authority keys and compares control flow.
```

## Not Proven

```text
- Semantic correctness of Agent-authored transition_concern_evidence.
- Future caller/COO disposition choices after a HOLD.
- Route V2 policy authoring beyond an explicitly supplied plan mapping.
- Full --all profile in this dirty implementation worktree.
```

## Remaining Delta

```text
Full --all profile was not run in this dirty implementation worktree.
This report records support evidence only; human/Link closure is outside this work Brick.
```
