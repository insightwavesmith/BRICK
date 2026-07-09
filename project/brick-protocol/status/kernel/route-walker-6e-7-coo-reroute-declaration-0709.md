# COO Reroute Declaration — Route V2 ⑥e/⑦ Advisory Walker Building

Date: 2026-07-09 KST
Status: COO disposition record / support evidence only
Building: `route-walker-6e-7-advisory-view-0709`
Evidence root: `project/brick-protocol/buildings/route-walker-6e-7-advisory-view-0709`

## COO disposition

```text
Movement: reroute
```

## Reroute target

```text
route-walker-6e-7-advisory-view-0709-verification-qa-repair
```

Target boundary:

```text
verification / QA repair segment
```

## Reason

The implementation candidate exists, but the current evidence is not sufficient
for landing.

Observed blockers / gaps:

```text
1. The Building emitted all six step-output files, but the latest frontier still
   reports `intervention_required` / `link_paused`.
2. The latest intervention event names `required_disposition_owner` as
   `caller-or-coo`.
3. Code-attack QA evidence is too thin for a walker / Movement-boundary change.
4. Closure and evidence-integrity records leave focused-checker/temp-dir and
   full `check_profile.py --all` proof gaps.
5. Landing Route V2 walker integration without the repair segment would
   over-promote partial working-tree evidence into parent completion.
```

## Reroute scope

The reroute is not a full redesign and not a new Route V2 architecture.
It carries forward the current implementation candidate and repairs only the
verification/QA closure gaps.

Required repair work:

```text
1. Strengthen code-attack QA with concrete attack probes:
   - advisory observation must not affect walker control-flow;
   - no Movement / route_target authority may be derived from Route V2 view;
   - forbidden keys must stay rejected;
   - no silent route_policy default load;
   - reroute_adoption_record / hold_record contracts must remain unchanged.
2. Re-run focused verification in an environment with usable temp dirs:
   - python3 -m compileall -q brick_protocol
   - python3 brick_protocol/support/checkers/check_route_v2_views.py
   - python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_walker_advisory
   - python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
   - python3 brick_protocol/support/checkers/check_profile.py --profile link_routing_behavioral
   - python3 brick_protocol/support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
   - git diff --check
3. Run final clean sweep only after focused proof is green:
   - python3 brick_protocol/support/checkers/check_profile.py --all
4. Re-synthesize closure with explicit P1-P12 mapping.
5. Re-check forbidden paths before any landing:
   - no `brick_protocol/link/**` mutation;
   - no `brick_protocol/agent/**` mutation;
   - no `brick_protocol/agent/return_fact.py` mutation;
   - no `brick_protocol/support/operator/route_scope.py`;
   - no `brick_protocol/support/operator/route_v2_engine.py`;
   - no new concern kind;
   - no success/quality/Movement authority fields in support.
```

## Proof limits

This declaration is not source truth, not success judgment, not quality judgment,
and not implementation landing approval. It is a COO Movement disposition for the
current Building boundary.

