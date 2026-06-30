# Customer-Ready G1 — No-link / route-default docs + skill sync — 0630

Status: support evidence only / operator maintenance. Not source truth, not
success judgment, not quality judgment, and not Link Movement authority.

## Why this slice exists

The live G1 measurement (`customer-ready-closeout-g1g2g3-status-0630.md`) proved
that the engine can run a fan-in QA concern through Link reroute and work replay
on current main. The remaining G1 gap was not engine repair; it was policy and
operator/customer guidance:

```text
user/COO does not author Link rows at the compact surface
support materializes Link rows
materialized default Movement is forward
reroute/HOLD requires concern evidence plus declared/adopted route policy
all-forward graph completion is NOT route-default proof
```

This slice syncs that distinction into the building-running skill chain so future
Buildings do not repeat the prior mistake: treating explicit all-forward graph
packets or compact default-forward edges as proof of route/HOLD defaults.

## Changed surfaces

```text
agent/skills/brick-task-author/SKILL.md
brick/templates/skills/brick-task-author/SKILL.md
agent/skills/building-sizing-method/SKILL.md
brick/templates/skills/building-sizing-method/SKILL.md
agent/skills/building-coordination/SKILL.md
agent/skills/task_intake/SKILL.md
```

## What changed

- `brick-task-author` now has an explicit G1 no-link / route-default section:
  user does not write Link rows; support materializes them; default is forward;
  reroute/HOLD needs concern evidence plus declared/adopted policy.
- `building-sizing-method` now sizes rework risk as a Link-policy dimension, not
  as a hidden automatic route default.
- `building-coordination` now states that graph movement cases are analysis
  inputs and that hard fan-in QA lanes return observations while closure is the
  Link-facing concern source.
- `task_intake` now requires candidates to name the no-link / materialized-forward
  distinction and forbids treating all-forward graphs as route-default proof.

## Three-axis attribution

```text
Brick evidence: task/graph authoring guidance and sizing rules define how work is
  composed into Brick nodes and convergence.
Agent evidence: skills guide the performer/operator's returned candidate fields;
  they do not make Agent output a route choice.
Link evidence: Movement remains forward/reroute; reroute/HOLD basis comes from
  declared route policy or adopted closure concern, not from QA lanes or support.
Support surface: docs/skills only; support materializes/records and does not own
  Movement, target selection, success, or quality.
```

Rejected shortcut:

```text
Do not solve this by changing engine default movement to reroute. That would make
normal continuation unsafe and would confuse Movement with policy. The required
fix here is clarity: no-link authoring != hidden route default.
```

## Verification

Commands to run for this slice:

```bash
git diff --check
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/read_side_projection_boundary.yaml
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

## Narrowly proven

- The customer/operator skill chain now records the G1 distinction in the places
  used for task authoring, building sizing, coordination, and task intake.
- The mirrored template skill copies for `brick-task-author` and
  `building-sizing-method` were updated with the same policy text.

## Not proven / remaining G1 work

```text
- Deep L2 cascade replay beyond the measured n2 QA-reroute-to-work case remains
  not_proven.
- A fresh customer reading-comprehension test of these docs/skills is not proven.
- This was direct operator maintenance, not a Building-produced patch. It is
  recorded as an exception because the slice is documentation/skill sync only;
  the next implementation slice should return to Building-first operation.
```

## Next Movement candidate

Forward this G1 policy-doc slice after verification, keep the full closeout goal
active, then proceed to either:

```text
G2 customer release comprehension / fresh-export check
G3 next FINAL architecture leaf, likely kernel_checks.py based on live LOC
```
