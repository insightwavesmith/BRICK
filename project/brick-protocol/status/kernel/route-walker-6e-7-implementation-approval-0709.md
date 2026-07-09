# Route V2 ⑥e / ⑦ Walker Integration Implementation Approval — 0709

Status: support evidence only. This records Smith's human-gate decision to open
the Route V2 ⑥e/⑦ walker integration implementation as a declared Building. It
does not implement code, does not run the Building, does not choose Link
Movement, does not judge success/quality, and does not make source-truth claims.

## 0. Decision

Smith approved the COO-recommended conditional implementation gate:

```text
Approved option: conditional approval — SHAPE A only
Approval text: "그대로 진행"
Recorded interpretation:
  1. Open a declared Building for Route V2 ⑥e/⑦ walker integration.
  2. Scope is limited to SHAPE A: read-only advisory Route V2 view observation.
  3. Implementation must run through declared Building / worktree sandbox.
  4. No direct COO source implementation is approved.
  5. No walker control-flow, Movement, route-target, Link, AgentFact, or concern
     vocabulary authority change is approved.
```

Source request:

```text
project/brick-protocol/status/kernel/route-walker-6e-7-implementation-building-request-0709.md
```

Source design lineage:

```text
project/brick-protocol/status/kernel/route-v2-6e-walker-integration-design-0709.md
project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md
```

## 1. Approved Building opening

```text
building_candidate: route-walker-6e-7-advisory-view-0709
approved_to_open_declared_building: true
catalog_scope: brick_protocol_dogfood
recommended_chain_preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
route_family_candidate: preset_guided_graph
worktree_required: true
live_checkout_run_building_intake: forbidden
implementation_gate_state: approved_for_declared_building_only
```

Approved work contract:

```text
Add a read-only, advisory Route V2 view observation beside dynamic walker
 evidence, without changing walker control flow, Movement choice, route target
selection, reroute/hold record contract, AgentFact shape, Link resources, or
concern_kind vocabulary.
```

Expected support-evidence shape remains:

```text
dynamic_walker_evidence["route_v2_view_observations"] = [
  {
    "kind": "route_v2_view_observation",
    "binding": "advisory",
    "adopted_as_movement": False,
    "route_policy_input_state": "declared|absent|blocked",
    "route_v2_view": "<render_route_v2_view packet>"
  }
]
```

## 2. Still forbidden

This approval does not allow:

```text
- walker control-flow changes based on Route V2 view output
- support-chosen Movement
- support-chosen route_target
- verification_gap reroute eligibility
- new concern_kind
- new brick_protocol/support/operator/route_scope.py
- new brick_protocol/support/operator/route_v2_engine.py
- brick_protocol/link/** changes
- brick_protocol/agent/return_fact.py changes
- success/quality/approved/good_enough/movement_choice/route_target authority fields
- runtime scheduler/queue/retry ownership
- credentials, secrets, provider/session bodies in repo evidence
```

## 3. Required proof before landing

The Building must preserve the request's P1-P12 proof plan, including:

```text
- verification_gap remains non-reroute
- hold/paused/held_for_coo_review remain lifecycle/gate states, not Movement
- forbidden authority keys are rejected
- route_v2_view_observations is advisory and adopted_as_movement=false
- before/after walker control-flow decisions remain identical
- resume preserves or reads back the advisory observation without recompute drift
- no silent default route_policy load
- reroute_adoption_record and hold_record field sets remain unchanged unless a
  separate explicit contract/checker extension is opened
- no forbidden new surfaces or Link/Agent mutations
```

Required focused commands are inherited from the request:

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

## 4. Three-axis attribution

```text
Brick:
  The approved work is an implementation Building over a declared support runtime
  observation seam. The Brick contract is SHAPE A only.

Agent:
  Performers are chosen by the declared Building's Agent rows. This approval does
  not select provider/model identity as authority and does not change AgentFact.

Link:
  Link Movement remains forward/reroute only and is not chosen by Route V2 support
  evidence. This approval supplies no Movement and no route target.

Support:
  walker_kernel/walker_resume/checkers may record and verify advisory evidence
  only. Support must not become source truth, success/quality judgment, Movement
  authority, or a route engine.
```

## 5. Not proven

```text
- No implementation Building has run yet.
- No code/checker/report change is landed by this approval.
- No route_v2_view_observations behavior is proven yet.
- No resume parity is proven yet.
- No ⑦ route/walker integration is landed yet.
- Parent GOAL remains open until the declared Building lands or returns a repair.
```

## 6. Movement language

```text
gate_state: approved_for_declared_building_only
movement_candidate: none supplied by this approval
```
