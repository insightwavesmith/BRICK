# BRICK 6 P7 Product route surface - P7b paused evidence - 2026-07-01

## Scope

- Phase: P7 per revised P0..P9 goal mapping — Product route / P3 Easy Building surface.
- Building: `brick-6-p7-product-route-surface-0701b`.
- Graph declaration commit: `6698fea` plus fan-out declaration fix `728f41c`.
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p7-product-route-surface-0701b`.

## Graph shape correction

P7a used the official `brick build --graph` route but was effectively linear:

```text
design -> work -> code-qa -> axis-qa -> evidence-qa -> closure
```

P7b corrected the topology to real QA fan-out/fan-in:

```text
design -> work -> fan([code-qa, axis-qa, evidence-qa]) -> closure
```

Observed P7b adapter usage timestamps show the QA cohort started together after work:

```text
code-qa     2026-07-01T01:12:44Z
axis-qa     2026-07-01T01:12:44Z
evidence-qa 2026-07-01T01:12:45Z
```

After closure attempt 1, Link adopted the closure implementation-gap concern and rerouted to the work boundary once. The replay again used the declared fan-out/fan-in graph.

## Frontier

Final P7b result:

```text
frontier_kind = link_paused
customer_visible_frontier_state = not_ready
```

Reason: second closure returned `transition_concern_evidence`:

```text
concern_ref: transition-concern:brick-6-p7-product-route-surface-0701b-status-build-root-drift
concern_kind: implementation_gap
related_boundary_refs: [brick-instance:brick-6-p7-product-route-surface-0701b-work]
```

Link held at the work boundary because the work node reroute budget was exhausted:

```text
hold_reason: target_node_budget_exhausted
pending_target_ref: brick-6-p7-product-route-surface-0701b-work
required_disposition_owner: caller-or-coo
```

## Observed evidence

P7b work/QA/closure evidence supports these partial improvements inside the sandbox:

- README / quickstart / setup / launch-guide route wording moved toward public `brick init`, bare `brick`/`brick status`, `brick doctor`, `brick build`, and `brick build --graph`.
- Quickstart separates compact `graph_packet` usage through `brick build --graph` from internal `run_building_plan` full Building Plan internals.
- CLI plain error output was changed toward product-safe `category` / `kind` / evidence pointers / proof limits instead of raw `str(exc)` as the main operator line.
- `brick_cli_entrypoint` checker/profile was extended to pin public route docs and plain CLI error surface.
- Focused slice checks were reported by work/QA as green in parts: `brick_cli_entrypoint` profile, `py_compile` for changed Python, and `git diff --check`.

## Not proven / blockers

P7b is **not closed** and must not be adopted as final P7 evidence because:

1. Closure attempt 2 found `status-build-root-drift`:
   - status/no-args CLI evidence and build evidence-root routing may teach different default destinations.
2. Focused profile and `check_profile.py --all` agreement was not proven inside P7b closure:
   - closure recorded no usable temporary directory for profile execution;
   - earlier QA also observed an all-profile rejection in `read_side_projection_boundary/intake_evidence_projection_case`.
3. Direct mutation/FIRE proof for every new route/error-surface regression pin remains incomplete or only partially recorded.
4. Full Easy-Building dynamic design ergonomics (S6-F4) remains outside this slice and is still not proven.
5. P7b produced no adopted sandbox commit on main.

## Next Movement candidate

Do **not** restart broad P7 investigation. Continue with a bounded P7 follow-up Building that targets only the P7b closure gap:

```text
P7c candidate: status/build evidence-root alignment + P7 slice proof rerun
```

Recommended graph shape:

```text
design/status-root-scope
  -> work
  -> fan([code-attack-qa, axis-attack-qa, evidence-integrity])
  -> closure
```

Required P7c done condition:

- status/no-args CLI and build output agree on how the default evidence root/buildings root is explained to customers, or the difference is explicitly classified as support/internal with product-safe wording.
- focused `brick_cli_entrypoint` profile passes.
- `check_profile.py --all` passes in the current main environment, or any failure is proven unrelated with explicit not_proven/next-work classification.
- P7 slice route docs / graph-packet-vs-full-plan docs / CLI error taxonomy / bare brick status behavior remain green.
- Full Easy-Building dynamic design ergonomics remains explicitly not_proven for a later P7 slice unless separately implemented.

## Proof limits

- This status note is operator/status evidence only.
- P7b model/QA/checker outputs are support evidence only, not source truth, success judgment, quality judgment, or Movement authority.
- P7b partial improvements are not adopted to main.
