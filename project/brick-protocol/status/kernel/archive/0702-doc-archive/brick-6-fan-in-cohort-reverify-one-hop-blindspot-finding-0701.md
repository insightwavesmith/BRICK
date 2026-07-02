# Fan-in cohort re-verify has a one-hop blind spot — finding (0701)

Status: operator-discovered finding, support/evidence-integrity only. Not
source truth, success judgment, quality judgment, or Movement authority.
Routed as a P8 (ship-safety / evidence-integrity) candidate item.

## How this was found

While reviewing why P7d2 (`brick-6-p7-easy-building-ergonomics-0701e`) ended
`link_paused` after `work-docs` rerouted and `docs-lane-qa` cleanly
re-verified, Smith asked directly: is "re-verify the whole fan-in cohort"
the default policy, and if so why didn't it fire for the sibling
`checker-lane-qa`?

## Root cause (source-confirmed)

`support/operator/walker_fan_in.py:270-316`, `_fan_in_cohort_replay_plan`,
is the conservative safety net: when a reroute lands on a node X that IS a
declared fan-in source, and no `sibling_independence` vouch names a
sibling, the whole fan-in cohort is re-verified as forward replay
(budget-free). The docstring is explicit: "Absent vouch => re-verify ALL
(conservative)."

But the trigger check is narrow:

```python
cohort_targets = [
    fan_in_target
    for fan_in_target, sources in sources_by_target.items()
    if target_step_ref in sources
]
if not cohort_targets:
    return [], [], []
```

`target_step_ref` is the reroute LANDING node (from the adopted concern's
`related_boundary_refs`). This only matches if the landing node is ITSELF
listed as a `member_refs` source of some declared `fan_in` group. In P7d2,
the closure's `boundary_mismatch` concern honestly named `work-docs` (the
actual producer of the mis-attributed `changed_files`) — but `work-docs` is
one hop upstream of the real fan-in source `docs-lane-qa` (edge:
`work-docs -> docs-lane-qa`, 1:1, not itself a fan-in member). So
`cohort_targets` came back empty and the conservative "re-verify all
siblings" safety net never activated at all — not even to re-verify the
lane whose own downstream QA reran.

## Why this is structural, not a one-off

QA/closure Agents are correctly instructed to name the node where they
actually observed a defect (the real producer of bad output), not the QA
node that merely reported it — this is the honest-evidence discipline
Smith confirmed earlier in this same investigation (rejecting an
alternative fix that would have coached an Agent to name a different,
"safer" target). But that honest reporting habit means a `boundary_mismatch`
/ `implementation_gap` concern will routinely name a work node one hop
upstream of the declared fan-in source, not the fan-in source itself. The
cohort-reverify safety net's narrow trigger (exact membership match on the
landing node) will therefore routinely miss activating, in exactly the
cases where a reroute is most likely to make a sibling's prior pass stale.

## What this does NOT prove

- Does not prove `sibling_independence` vouching itself is broken — it
  works correctly when consulted; the problem is upstream, in whether the
  cohort-reverify code path is entered at all.
- Does not prove every fan-in-adjacent reroute is affected — only reroutes
  whose landing node is exactly one (or more) hops upstream of a declared
  fan-in source, which appears to be the common case for work-node
  concerns.

## Recommended P8 scope addition (evidence-integrity / Link correctness)

Extend `_fan_in_cohort_replay_plan`'s trigger condition (or its caller in
`walker_kernel.py:2036-2075`) to walk the reroute's own `replay_scope`
(the declared forward-replay chain from the landing node) and check EACH
step in that chain for fan-in-source membership, not only the landing node
itself. If any node in the replay chain is a fan-in source, the existing
cohort-reverify-or-vouch logic should apply against that node, not be
skipped. Add a checker-first negative probe: a reroute landing one hop
above a fan-in source, with a stale sibling and no `sibling_independence`
vouch, must currently be provable as a false-negative (cohort skipped
uncaught) before the fix, and RED after the fix confirms the cohort is
caught.

## Workaround used in this session

P7d3 (`brick-6-p7-easy-building-ergonomics-0701f`) sidesteps this blind spot
by declaring `sibling_independence` up front on the `lane-qa-fanin` group,
naming both `docs-lane-qa` and `checker-lane-qa` as mutually independent —
an honest, COO-declared fact based on their fully disjoint `write_scope`
`allowed_paths`. This does not depend on the cohort-reverify trigger firing
at all, so it is unaffected by this blind spot, but it does not fix the
blind spot itself for future graphs.

## Proof limits

- No source mutation performed to investigate; read-only source and
  walker_fan_in.py inspection only.
- Not yet scoped as a Building; recorded here so it is not lost before P8.
