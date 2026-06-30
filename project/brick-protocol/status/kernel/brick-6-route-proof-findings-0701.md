# BRICK 6 Route-Proof Findings — 0701

Status: support evidence for P1 route/adoption diagnosis; not P1 completion, not source truth, not success/quality judgment, not Movement authority.

## Objective context

The active BRICK 6-surface audit repair goal requires P0~P8 to close through official `build()` / `brick build` declared graph Buildings. P1 is raw evidence secret/PII scrub. During P1c/P1d, Smith flagged that route/reroute did not appear to fire after QA/closure concerns.

## Observed evidence

- `brick-6-p1-raw-evidence-scrub-0701c` completed frontier but closure returned `implementation_gap` with `related_boundary_refs: ["brick:brick-6-p1-raw-evidence-scrub-0701c-work"]`; all raw Link movements were `forward`; graph carried top-level `transition_concern_adoption: advisory`.
- `brick-6-p1-raw-evidence-scrub-0701d` completed frontier; closure returned non-reroute `verification_gap`; route not firing there was not a defect proof.
- `brick-6-route-proof-closure-implementation-gap-0701a` returned closure-origin `implementation_gap` with `brick:<work-node>` ref and no top-level advisory. It produced `frontier_kind=link_paused`, not silent forward. HOLD reason was `no_resolving_reroute_address` because the classifier did not resolve the `brick:`-prefixed node ref.
- `brick-6-route-proof-closure-implementation-gap-0701b` used a plain declared work node id. It recorded a `reroute` row targeting the work node, but paused because `transition_concern_evidence.reason_refs` included external Building evidence paths that MAIL-REPAIR could not resolve in the current ledger.
- `brick-6-route-proof-closure-implementation-gap-0701c` used a plain declared work node id and current-ledger-local `reason_refs`. It completed frontier, recorded one `reroute` movement to the work node, ran `work-attempt-2`, reran QA attempt 2 fan-in, and closure attempt 2 returned no further transition concern.

## Narrowly proven

- The dynamic walker can process closure-origin `implementation_gap` as reroute when the graph omits top-level advisory, the target ref resolves to a declared work node, the target has reroute budget, and runtime handoff reason refs resolve in the current Building ledger.
- P1c's forward-only behavior is explained by graph declaration / authoring surface: top-level `transition_concern_adoption: advisory` suppressed closure-origin concern adoption.
- QA fan-in source concerns can remain local/advisory while closure remains the Link-facing concern source.
- `brick:`-prefixed related boundary refs are admitted by Agent return validation but were not observed to resolve in `support/operator/walker_transition_concern.py` against declared node ids during 0701a.
- Runtime handoff `reason_refs` must be current-ledger-resolvable; external absolute Building paths in adopted transition concern reason refs cause HOLD rather than replay.

## Not proven

- P1 raw evidence scrub is not complete.
- `check_profile.py --all` green is not proven.
- P1d sandbox commit adoption is not proven.
- Product/customer readiness is not proven.
- The durable prevention guard is not yet implemented.
- Whether the correct durable repair is only prompt/template guidance, only classifier normalization, only graph authoring validation, or a combination is not yet proven by a repair Building.

## Brick / Agent / Link attribution

### Brick candidate

The Building graph declaration in P1c was overbroad: top-level advisory made all transition concerns advisory, including closure-origin `implementation_gap`. Hard fan-in source-lane advisory should be scoped through `fan_in_source_transition_concern_adoption`, not global adoption.

### Agent candidate

Agents did emit transition concern evidence. The issue was not “no concern returned.” However, agent-facing examples/guidance currently encourage `brick:<work-node>` style refs, while live classifier behavior required plain declared node ids in 0701c.

### Link candidate

Link/dynamic walker adoption works under the 0701c conditions, but the Link classifier / accepted-address contract is inconsistent with Agent validation examples for `brick:`-prefixed Brick refs. MAIL-REPAIR correctly HOLDs unresolved reason refs, but closure guidance should prevent external current-ledger-unresolvable reason refs in adopted concerns.

## Next Movement candidate

Declare and run a bounded repair Building for route concern address/guidance/guard hardening:

1. Preserve admitted top-level `transition_concern_adoption=advisory` feature for explicit opt-in cases.
2. Prevent hard fan-in closure graphs from accidentally applying top-level advisory where scoped fan-in source advisory is intended.
3. Align Agent-facing related_boundary_refs guidance with Link classifier behavior, preferably by making admitted `brick:`/`brick-instance:`/`brick-boundary:` refs resolve to declared Brick node ids or by explicitly documenting/validating the plain declared node id contract.
4. Add/adjust checker coverage so P1c-like silent-forward and 0701a-like prefix mismatch cannot recur.
5. Add/adjust guidance so adopted transition concern `reason_refs` are current-ledger-local addresses, while external evidence remains observed evidence only.

