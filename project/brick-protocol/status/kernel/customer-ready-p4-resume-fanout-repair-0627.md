# Customer-Ready P4 Resume Fan-Out Repair - 0627

This record is support evidence only. It is not source truth, success judgment,
quality judgment, or Movement authority.

## Phase

P4 - Resume Surface Repair.

## Live Checkout

- Worktree: `/Users/smith/.brick/worktrees/struct-surgery-0623`
- Base HEAD while editing: `137f0e8e62e7d7fc5ff0255cc00b0ba68e724929`
- P3 state before this repair: HOLD on live `adapter:gemini-local`
  provider/auth rejection (`API_KEY_INVALID` / HTTP 400).

## Purpose

Repair the resume behavior that forced every resumed graph walk to
`dispatch_pool_size = 1`, which serialized not-yet-run fan-out continuation even
when the Building declared fan-out parallelism.

## Changed Surfaces

- `support/operator/walker_kernel.py`
- `support/operator/walker_frontier_driver.py`
- `support/checkers/check_bounded_agent_proposed_routing_loop0.py`

## Behavior

Previous behavior:

- Forward graph walk with fan groups used the declared or auto fan-out pool.
- Any resume seed forced the whole resumed walk to serial pool size 1.
- Completed replay and live continuation were not separated for dispatch.

New behavior:

- Completed pre-HOLD resume replay stays serial until the current held
  disposition has been applied.
- After the held disposition is applied, live continuation recovers the same
  declared fan-out dispatch pool as the forward path.
- Non-fan graphs still run serially.
- Explicit `fanout_dispatch_pool_size` / `BRICK_FANOUT_DISPATCH_POOL_SIZE`
  continues to control the declared pool.
- No new scheduler, queue, retry runtime, Movement literal, or route authority is
  introduced.

## Checker Evidence

Focused checker:

```text
python3 support/checkers/check_bounded_agent_proposed_routing_loop0.py --repo .
```

Result:

```text
passed
```

Focused profile:

```text
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
```

Result:

```text
profile passed: bounded-agent-proposed-routing-loop
```

Additional mechanical checks:

```text
python3 -m compileall -q support/operator support/checkers
git diff --check
```

Result:

```text
passed
```

## P4 Invariant Added

The checker now includes a two-stage fan graph:

1. Forward run completes the first fan-out/fan-in.
2. The run pauses at the mid-fan `join1` gate before the second fan-out.
3. Resume replays completed pre-HOLD evidence serially.
4. After human/COO forward disposition, the second live fan-out overlaps under
   pool 4.
5. The resumed output still drains in deterministic frontier order.

This directly covers the P4 requirement: resume from mid-fan evidence,
continuation parallelism, and route/frontier preservation.

## Three-Axis Attribution

Brick candidate:

The declared graph already carries fan-out/fan-in topology and declared pool
shape. The work contract did not require a new Building design.

Agent candidate:

Completed Agent returns before the HOLD remain replay evidence. Not-yet-run
post-disposition steps are live Agent work and should use the forward fan-out
dispatch behavior.

Link candidate:

Link still owns Movement and disposition. The repair does not author a route,
choose Movement, or invent a target. It only changes support walker dispatch
after the caller/COO disposition has already been applied.

Support surface:

The repair belongs in the dynamic walker support surface, where dispatch pool
selection is applied.

Rejected one-axis shortcut:

This was not treated as an Agent prompt, Link Movement, or new scheduler
problem. It was the support walker applying one serial resume guard too broadly.

Movement:

P4 focused repair = FORWARD as support evidence.
Global customer-ready movement remains HOLD until P3 Gemini Building QA and C6
closure are proven.

## Not Proven

- Gemini Building QA for C6.
- Codex closure after Gemini QA.
- Fresh-machine resume behavior.
- Full `check_profile.py --all` over stale untracked Building evidence.
- Customer-ready proof.
