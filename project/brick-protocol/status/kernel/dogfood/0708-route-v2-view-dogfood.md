# GOAL ⑥ Route V2 read-only view dogfood — 0708

Status: support evidence only. This dogfood record is not source truth, not a
success or quality judgment, not Movement authority, and not walker integration
approval.

## Purpose

Prove the landed Route V2 read-only view builder can render representative route
evidence without changing Route V2 HOLD surfaces.

Dogfood target:

```text
brick_protocol.support.operator.route_v2_views.render_route_v2_view
```

Allowed surface for this record:

```text
project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md
```

Forbidden / not touched by this dogfood:

```text
brick_protocol/support/operator/route_materialization.py
brick_protocol/support/operator/walker_kernel.py
brick_protocol/support/operator/walker_resume.py
brick_protocol/link/**
brick_protocol/agent/return_fact.py
brick_protocol/support/operator/route_scope.py
brick_protocol/support/operator/route_v2_engine.py
```

## Observed dogfood cases

### Case A — implementation_gap

Input facts:

```text
transition_concern_evidence.concern_kind = implementation_gap
route_policy = brick_protocol/link/route_policies/basic_qa_repair.yaml
declared_route_replay_plan.route_replay_ref = route-replay:route-v2-dogfood-implementation-gap
gate_state = paused
movement_candidate = reroute
delta_qa_fact.made_changes = true
delta_qa_fact.changed_files = [brick_protocol/support/operator/route_v2_views.py]
delta_qa_fact.diff_refs = [observation:route-v2-dogfood-diff]
delta_qa_fact.evidence_refs = [observation:route-v2-dogfood-render]
```

Observed output summary:

```text
sealed_concern_kind_observation.concern_kind = implementation_gap
route_policy_eligibility_observation.eligible = true
route_policy_eligibility_observation.requested_route_scope = implementation_only
materialization_view.materialized = true
materialization_view.link_row.movement = reroute
gate_state = paused
movement_candidate = reroute
delta_qa_fact preserved exactly as factual fields
```

Interpretation: implementation_gap can be rendered as a read-only support view
over the existing route policy and existing route materialization helper. The
view preserves a movement_candidate but does not author a top-level Movement.

### Case B — verification_gap

Input facts:

```text
transition_concern_evidence.concern_kind = verification_gap
route_policy = brick_protocol/link/route_policies/basic_qa_repair.yaml
gate_state = held_for_coo_review
movement_candidate = empty
delta_qa_fact.made_changes = false
delta_qa_fact.changed_files = []
delta_qa_fact.diff_refs = []
delta_qa_fact.evidence_refs = [observation:route-v2-dogfood-verification-gap]
```

Observed output summary:

```text
sealed_concern_kind_observation.concern_kind = verification_gap
sealed_concern_kind_observation.non_reroute = true
route_policy_eligibility_observation.eligible = false
route_policy_eligibility_observation.match_state = non_reroute_concern_kind
materialization_view = null
gate_state = held_for_coo_review
movement_candidate = empty
delta_qa_fact preserved exactly as factual fields
```

Interpretation: verification_gap remains non-reroute evidence and is not
materialized into a reroute view.

### Case C — forbidden top-level keys

Probed forbidden keys in transition_concern_evidence:

```text
success
quality
movement
movement_choice
route_target
```

Observed: each probe raised ValueError before rendering. This preserves the
Route V2 boundary that support evidence must not carry success, quality,
Movement, or route target authority in the rendered view input.

## Three-axis attribution

```text
Brick evidence:
  Route V2 work contract says this slice is a read-only view over sealed concern
  kinds, route-policy eligibility, materialization view, gate_state /
  movement_candidate separation, and delta-QA factual fields.

Agent evidence:
  The consumed Agent-facing fact is transition_concern_evidence with sealed
  concern_kind validation. The dogfood does not change Agent Object or
  AgentFact shape.

Link evidence:
  Movement literals remain forward | reroute. gate_state remains lifecycle /
  review state. route_policy eligibility and route_replay_plan are consumed as
  evidence; this dogfood does not choose Movement or target.

Support surface:
  route_v2_views.render_route_v2_view plus the existing
  route_materialization.materialize_transition_concern_disposition view.

Rejected shortcut:
  Do not treat successful render as walker integration readiness or as approval
  to edit walker_kernel, walker_resume, link resources, Agent return facts, or a
  new route_v2_engine / route_scope surface.
```

## Narrow proof

Narrowly proven by this dogfood:

```text
- implementation_gap renders route-policy eligibility and existing materialization view.
- verification_gap remains non-reroute and not eligible for reroute materialization.
- gate_state and movement_candidate stay separate.
- made_changes, changed_files, diff_refs, and evidence_refs are preserved as factual delta-QA fields.
- forbidden success / quality / Movement / route_target keys are rejected.
```

Not proven:

```text
- semantic correctness of any future Agent concern evidence.
- source truth, success, or quality of future Route V2 work.
- walker_kernel / walker_resume integration behavior.
- route_materialization extension beyond the existing consumed helper behavior.
- automatic repair / replay execution.
```

Next gate candidate:

```text
FORWARD candidate for preparing a human-gate packet for ⑥d / ⑥e.
Do not start walker integration until Smith/human gate confirms the packet.
```
