# TIER-A-3AXIS-CONFORMANCE-0 Task Source

## Objective

Deterministic (adapter:local) end-to-end automation conformance test that drives a
declared Building through the real engine, exercising all three axes (Brick / Agent /
Link) plus Link mechanics (forward, declared reroute, gate sufficiency, budget,
pause/resume, carry/transfer) and the full evidence shape, with declaration_provenance.

## First-Line Contract

```text
task.md -> caller/COO-declared graph plan -> run_building_plan(walker_mode='dynamic')
-> HOLD on budget exhaustion -> resume_building_plan(raise disposition) -> evidence root
```

## Brick / Agent / Link Boundary

Brick owns work contracts and required return shapes. Agent owns the closed AgentFact
(received_work, returned). Link owns Movement, target, declared gates, reroute budget,
pause/resume, carry, and transfer. Support records support evidence and authors no
Movement, route, success, or quality.

## Proof Limits

Deterministic adapter:local only. Not real-provider behavior, not source truth, not
success judgment, not quality judgment, not Movement authority.
