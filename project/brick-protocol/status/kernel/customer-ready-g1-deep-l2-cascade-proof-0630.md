# Customer-Ready G1 — deep L2 cascade replay proof — 0630

Status: support evidence only / operator measurement. Not source truth, not
success judgment, not quality judgment, and not Link Movement authority.

## Purpose

Close the explicit G1 evidence gap left by prior route-default measurements:

```text
Deep L2 cascade replay beyond the measured n2 single-reroute case remains
not_proven.
```

This proof measures the existing bounded Agent-proposed routing loop checker on
current main and verifies that its covered cases include nested different-node
cascade replay with cascade depths `[1, 2]`.

## Measurement base

```text
source checkout = /Users/smith/projects/BRICK
source branch = main
source HEAD before proof = 9a1b77c (plus tracked working-tree WIP outside this proof)
command = PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile bounded-agent-proposed-routing-loop
raw output = /Users/smith/.brick/tmp/g1-bounded-agent-proposed-routing-loop-0630.out
```

The profile run is support evidence only. It does not decide source truth,
success, quality, or Movement.

## Profile result

Observed:

```text
profile passed: bounded-agent-proposed-routing-loop
kernel_check=bounded_agent_proposed_routing_loop elapsed=31.1s
kernel_check=recording_checker_derived_contract elapsed=0.9s
106 declarative rule observation(s)
5346 kernel target(s) inspected
```

## Coverage check for deep L2 beyond n2

The profile declares the relevant kernel check:

```text
support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml
  - bounded_agent_proposed_routing_loop
  - recording_checker_derived_contract
```

The checker source includes the nested different-node cascade case:

```text
support/checkers/check_bounded_agent_proposed_routing_loop0.py
case label: b5-c7-nested-different-node
expected adopted landings: 2
held records: none allowed
node reroute landings: x=1 and y=1
expected cascade_depths: [1, 2]
frontier_kind must walk on: complete or closure_pending
```

The specific guard lines reject shallow or broken behavior:

```text
- expected 2 adopted landings
- nested different-node cascade prematurely HELD
- different nodes did not draw their own budgets
- cascade depths drifted
- frontier did not walk on
```

Because the profile passed, the nested different-node cascade replay case did
not hit any of those violations in the measured run.

## Narrowly proven

```text
- The bounded-agent-proposed-routing-loop profile passes on current main.
- The measured profile includes a nested different-node cascade replay case that
  requires two adopted reroute landings and cascade_depths [1, 2].
- The measured case did not prematurely HOLD and did not drift cascade depths.
- This is beyond the earlier n2 single-reroute measurement.
```

## Not proven / caveats

```text
- This is checker/profile support evidence, not source truth or Movement authority.
- It does not prove every possible deep cascade graph or every future route policy.
- It does not prove independent customer reading-comprehension of the
  no-link/materialized-forward/reroute distinction.
- The docs/skill sync and this proof are operator measurements, not a fresh
  customer study.
```

## Next Movement candidate

Forward G1 deep L2 cascade replay as narrowly proven. Remaining G1 caveat is
fresh customer comprehension of no-link/materialized-forward/reroute language;
if this must be closed before final release, run a bounded comprehension review
against the customer-facing docs/skills. Otherwise proceed to MCP ai-cli
diagnostic Building, then final closeout audit.
