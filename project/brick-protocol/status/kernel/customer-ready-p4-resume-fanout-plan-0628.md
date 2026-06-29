# Customer-Ready P4 Resume Fan-Out Plan - 0628

Status: support evidence only. 0629 operator recheck: the focused P4 resume
fan-out invariant is closed-with-proof-limits; broad customer-ready proof remains
outside this phase.

This record is not source truth, success judgment, quality judgment, Movement
authority, or runtime/process proof. It records the operator plan for P4 after
read-only subagent measurement, two-agent attack review, and Codex operator
reconciliation. Subagent output is support evidence only.

## Phase

P4 - Resume surface repair.

## Operator Read

Current code has the core P4 repair: resume replay remains deterministic before
the held disposition is applied, and live continuation recovers the declared
fan-out pool after disposition.

Therefore P4 is not a new engine design. P4 is a focused resume invariant:
prove the behavior, preserve the public resume boundary, and keep the repair out
of scheduler / queue / retry / new Movement territory.

## Current Measurement

Measured live surfaces:

```text
support/operator/run.py
support/operator/walker_resume.py
support/operator/walker_resume_seed.py
support/operator/walker_kernel.py
support/operator/walker_frontier_driver.py
support/checkers/check_bounded_agent_proposed_routing_loop0.py
support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml
project/brick-protocol/status/kernel/customer-ready-p4-resume-fanout-repair-0627.md
project/brick-protocol/status/kernel/research-0626/resume-surface-design-0626.md
```

Current live code:

```text
resume_building_plan enters the existing Building root.
walker_resume reconstructs from the declared graph birth certificate.
ResumeSeed replays completed Agent returns from recorded evidence.
walker_kernel._active_dispatch_pool_size returns 1 only before disposition.
After disposition, the forward fan-out pool is used again.
fan-in joins still dispatch alone by design.
```

Stale evidence:

```text
0626 docs mention old walker_kernel line numbers and old serial-resume behavior.
Those coordinates are historical support only.
P4 repair/status records are local support evidence until admitted/tracked in
the target branch.
```

## 0629 Operator Recheck / Support Evidence

Fresh focused commands run in the live checkout:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_bounded_agent_proposed_routing_loop0.py --repo .
  => passed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml
  => passed
```

Narrowly proven as support evidence:

```text
- resume enters the same held Building root through resume_building_plan
- walker_resume reconstructs the declared graph from the birth certificate,
  not from a linearized snapshot
- ResumeSeed replays recorded pre-HOLD Agent returns instead of treating them as
  new live work
- walker_kernel._active_dispatch_pool_size is 1 before disposition and returns
  the declared fan-out pool after disposition
- the p4-resume-fanout fixture pauses at the first fan-in/COO gate, applies a
  human/COO forward disposition, then completes the second fan-out
- the resumed live fan-out continuation overlaps under pool=4
- deterministic frontier/drain order is preserved despite inverted completion
  order in the timed fixture
- malformed/stale resume disposition rows, unsupported targets, missing budget
  evidence, and path-shaped runtime handoff hazards fail closed under the same
  bounded routing profile
```

Three-axis read:

```text
Brick:
  resume preserves the original declared Building graph and fan topology.

Agent:
  recorded completed Agent returns are replay evidence; not-yet-run nodes after
  disposition are live Agent work.

Link:
  human/COO disposition controls lifecycle resumption. Movement remains forward
  / reroute only. HOLD remains lifecycle/frontier evidence.

Support:
  walker/resume/checker machinery walks and records the declared road. The
  ThreadPoolExecutor pool is an implementation detail and not scheduler
  authority.
```

## Attack Review Delta

Two independent attack reviews originally agreed P4 had the right repair surface
but was not closed. Current disposition:

```text
CLOSED FOCUSED SLICE:
- resumed live fan-out overlap is proven by p4-resume-fanout
- source and checker evidence pin _active_dispatch_pool_size behavior
- birth-certificate graph recovery is fail-closed when unavailable
- disposition vocabulary is read as lifecycle/action evidence; Link Movement
  remains forward/reroute only

REMAINING LIMITS:
- checker/profile pass is support evidence only
- real provider parallel execution is not proven
- fresh-machine resume behavior is not proven
- full process integrity across provider processes is not proven
- full customer-ready proof belongs to P7/P8
```

## Three-Axis Attribution

Brick:

```text
owns the declared graph/fan-out shape. Resume must continue the same Building
road, not create a new design.
```

Agent:

```text
completed pre-HOLD steps are recorded Agent returns and may be replayed serially.
not-yet-run post-disposition steps are live Agent work.
```

Link:

```text
owns forward/reroute disposition, paused/resumed lifecycle, pending target, and
frontier. Support must not choose Movement or target.
```

Support:

```text
walker/resume/checker machinery applies the declared road and records evidence.
ThreadPoolExecutor is an implementation detail, not scheduler authority.
```

## RED / Fail-Closed Coverage

Current coverage:

```text
- same Building root/id is preserved by resume_building_plan pathing
- declared graph topology comes from work/declared-building-plan.json birth
  certificate; missing/unreadable birth certificate fails closed
- held target is carried through the human/COO disposition row
- unsupported reroute targets fail closed
- stale same-target disposition rows are skipped/fail-closed for the current hold
- path-shaped runtime handoff reason_refs are contained to this Building ledger
- resumed live fan-out overlap has a timed RED probe that inverts completion
  order while preserving deterministic frontier order
- bounded_agent_proposed_routing_loop text_absent guards support-authored
  Movement/source authority leaks
```

## Implementation Plan

1. Checker-first proof - closed focused slice.

```text
support/checkers/check_bounded_agent_proposed_routing_loop0.py homes the live
P4 fixture. The profile executes it through the bounded_agent_proposed_routing
kernel check. Do not move this invariant into case_runners or kernel_checks as
the primary owner.
```

2. Profile hardening - sufficient for P4 focused closure.

```text
bounded_agent_proposed_routing_loop.yaml executes the standalone checker and
pins the dynamic walker / resume / authority leak surfaces. P4-specific runtime
behavior is proven by the checker execution, not by text pins alone.
```

3. Public documentation - current invariant.

```text
completed replay may be serial;
not-yet-run continuation restores declared fan-out/fan-in shape;
resume does not author a new Building design.
```

4. No forbidden expansion.

```text
Do not add a scheduler, queue, retry runtime, Movement literal, route selector,
or provider runtime.
Do not split _run_dynamic_graph_walker as part of P4.
```

## Exit Checks

```text
python3 support/checkers/check_bounded_agent_proposed_routing_loop0.py --repo .
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
python3 -m compileall -q support/operator support/checkers
git diff --check
```

Then, before P6 walker cleanup:

```text
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

## Movement

Recommendation:

```text
FORWARD from P4 focused resume fan-out repair to P5 customer first-run /
onboarding alignment.

Do not claim customer-ready completion. P4 is closed-with-proof-limits as a
resume invariant only.
```

## Not Proven

```text
real provider parallel execution
fresh-machine resume behavior
full process integrity across provider processes
full check_profile.py --all after current dirty edits
disposition vocabulary alignment in support docs
customer-ready proof
```
