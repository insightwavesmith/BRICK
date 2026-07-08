# Route V2 Sealed Materialization Architecture

Status: R0/R1 checker-first support note, 2026-07-08.

Route V2 is a sealed materialization view over existing Brick, Agent, and Link facts. It is not a new route engine and it does not open a new route scope module.

## Boundary

Route V2 consumes an Agent-authored `transition_concern_evidence` payload only as evidence inside the closed Agent return. The admitted concern kinds remain exactly:

```text
upstream_gap
boundary_mismatch
insufficient_input
replay_needed
unknown
design_gap
implementation_gap
verification_gap
```

`verification_gap` is non-reroute evidence. It may preserve verification uncertainty for a Link gate or later human disposition, but it must not become reroute eligibility by itself.

Link still owns Movement. The only active Movement literals remain `forward` and `reroute`. `hold`, `paused`, and `held_for_coo_review` are gate or lifecycle states and must not appear as Movement literals.

## Materialization Shape

Route V2 materialization is a support projection over already-declared rows:

```text
Agent concern evidence
-> sealed concern_kind observation
-> Link route-policy eligibility observation
-> existing route_materialization / route_replay_plan view
-> separated gate_state and movement_candidate fields
-> checker evidence before any walker integration
```

The projection may render factual delta-QA fields:

```text
made_changes
changed_files
diff_refs
evidence_refs
```

Those fields are factual observations only. They do not classify success, failure, quality, approval, or Movement.

## R0/R1 Fence

This slice intentionally stops before engine integration. It does not edit `brick_protocol/support/operator/route_materialization.py`, `brick_protocol/support/operator/walker_kernel.py`, `brick_protocol/support/operator/walker_resume.py`, `brick_protocol/link/**`, or `brick_protocol/agent/return_fact.py`.

The R1 checker profile pins:

- the sealed 8-kind concern vocabulary through `brick_protocol/agent/return_fact.py`;
- `verification_gap` as non-reroute and not reroute-eligible;
- `hold`, `paused`, and `held_for_coo_review` as gate/lifecycle states, not Movement;
- absence of `route_scope.py` and a new Route V2 route engine surface;
- delta-QA factual field preservation for `made_changes`, `changed_files`, `diff_refs`, and `evidence_refs`.

Proof limit: this document and the R1 profile are support evidence only. They do not approve walker integration, choose Movement, judge quality, or create source truth.
