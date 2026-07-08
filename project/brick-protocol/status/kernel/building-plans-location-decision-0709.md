# ⑩c Building Plans Location Decision — 0709

Status: support/cleanup decision evidence only. This document does not move,
delete, rename, archive, implement, choose Link Movement, judge success/quality,
or make source truth. It closes the ⑩c cleanup decision for the current GOAL by
classifying `brick_protocol/brick/building_plans/` from live repo evidence.

## 0. Decision

```text
decision: KEEP for now
surface: brick_protocol/brick/building_plans/
classification: Brick-owned fixture/example Building Plan library, currently load-bearing
move_now: no
delete_now: no
archive_now: no
future_migration: only through a declared Building with reader/checker/admission/profile migration
```

Short version:

```text
Do not move building_plans under templates now.
The directory is small, but it is load-bearing fixture/example plan data used by
runner/onboarding docs and multiple checker/admission profiles. A simple git mv
would break current path contracts and checker fixtures.
```

## 1. Why this is not a simple cleanup move

Live repo contains exactly four files under the surface:

```text
brick_protocol/brick/building_plans/fixture-link-concern-replay-0.yaml
brick_protocol/brick/building_plans/fixture-link-route-replay-0.yaml
brick_protocol/brick/building_plans/fixture-retired-adapter-plan-0.yaml
brick_protocol/brick/building_plans/onboarding-example-0.yaml
```

These are not active project evidence. They are declared plan fixture/example
surfaces. However, they are not dead clutter either. They are referenced by
runner/onboarding support, package path admission, route/profile fixtures, and
checker kernels.

## 2. Observed current references

Reference scan over live repo found current load-bearing references including:

```text
brick_protocol/support/checkers/check_package_path_admission.py
  - admits/pins brick_protocol/brick/building_plans path family

brick_protocol/support/checkers/lib/building_plan_graph_check.py
  - run_building_plans_boundary_sweep expects brick_protocol/brick/building_plans

brick_protocol/support/checkers/check_profile.py
  - registers building_plans_boundary_sweep kernel check

brick_protocol/support/checkers/profiles/core.yaml
  - includes building_plans_boundary_sweep

brick_protocol/support/checkers/profiles/link_routing_behavioral.yaml
  - pins fixture-link-concern-replay-0.yaml
  - pins fixture-link-route-replay-0.yaml
  - pins fixture-retired-adapter-plan-0.yaml

brick_protocol/support/checkers/profiles/building_operator_driver0.yaml
  - pins onboarding-example-0.yaml

brick_protocol/support/operator/onboard.py
  - EXAMPLE_PLAN_REL = brick_protocol/brick/building_plans/onboarding-example-0.yaml

brick_protocol/support/operator/run.py
  - docs/reference text points to fixture-link-route-replay-0.yaml

brick_protocol/support/operator/coo_operating_chain.py
  - classifies plan_is_brick_owned by startswith brick_protocol/brick/building_plans/

brick_protocol/support/operator/orchestration_packet.py
  - fallback in-memory active_plan_ref uses brick_protocol/brick/building_plans/...

brick_protocol/support/docs/references/setup.md
brick_protocol/support/docs/references/quickstart.md
brick_protocol/support/docs/references/architecture-map.md
brick_protocol/support/docs/references/checker-profile-map.md
brick_protocol/brick/README.md
  - describe or use the surface as onboarding/checker example material
```

Proof limit: this is a 2026-07-09 KST reference scan, not a permanent dependency
graph. It is sufficient for the cleanup decision: current evidence contradicts a
simple move/delete.

## 3. File-by-file classification

| File | Classification | Current disposition |
|---|---|---|
| `fixture-link-concern-replay-0.yaml` | Link concern / reroute fixture plan; strict plan-boundary valid graph; exercises transition concern + route replay grammar | KEEP |
| `fixture-link-route-replay-0.yaml` | Declared boundary replay fixture plan used by auto-repair/replay and link-routing behavior checks | KEEP |
| `fixture-retired-adapter-plan-0.yaml` | Retired adapter boundary fixture; strict path rejects, lenient historical validation accepts | KEEP |
| `onboarding-example-0.yaml` | Harmless adapter:local onboarding example plan referenced by onboarding/quickstart docs | KEEP |

No file is approved for deletion or archive in this ⑩c decision.

## 4. Three-axis attribution

```text
Brick evidence:
  The files are Brick-owned Building Plan declarations / fixtures. They encode
  work structure, declared Brick rows, required return shapes, and example plan
  shape. Their current physical location under brick/building_plans is part of
  multiple validation contracts.

Agent evidence:
  The plans name Agent Object refs as performer rows, but they do not own Agent
  source behavior. Moving the directory would not be an Agent-axis cleanup; it
  would be a Brick fixture/path migration with support/checker fallout.

Link evidence:
  The fixture plans intentionally exercise Link Movement, declared_gate_refs,
  route_replay_plan, route decision basis, and lifecycle rows. They are used to
  keep Link routing boundaries checkable. Moving them without updating route and
  graph checkers would weaken Link evidence.

Support surface:
  support/checkers, support/operator/onboard.py, support/operator/run.py, docs,
  and profile YAMLs consume or describe this path. These support refs make the
  current path load-bearing, but they do not convert the directory into support
  ownership.

Rejected shortcut:
  Do not treat "building_plans looks like a template" as proof that it belongs
  under templates. Current evidence says the path is an admitted Brick-owned
  fixture library and is wired into checker/admission contracts.
```

## 5. Why not move under templates now

A future product cleanup could decide to rename or rehome the surface, for
example toward a clearer fixture/example naming scheme. But that is a migration,
not a cleanup shortcut.

A safe migration would need to update at least:

```text
- package path admission rules
- building_plans_boundary_sweep path expectations
- profile YAML path refs
- onboarding example path refs
- quickstart/setup docs
- coo_operating_chain plan_is_brick_owned classification
- orchestration_packet fallback active_plan_ref wording
- any checker-profile maps or reference docs that pin the current path
```

Until that work is declared and proven, the current path remains the safer and
more honest location.

## 6. Future migration preconditions

If Smith later wants a rehome/rename, open a declared Building with this scope:

```text
candidate_building: cleanup-10c-building-plans-path-migration
route_family: governed-change-review or high-risk-change-inspected
write_scope_candidates:
  - brick_protocol/brick/building_plans/** or new target path
  - brick_protocol/support/checkers/check_package_path_admission.py
  - brick_protocol/support/checkers/lib/building_plan_graph_check.py
  - brick_protocol/support/checkers/profiles/*.yaml
  - brick_protocol/support/operator/onboard.py
  - brick_protocol/support/operator/coo_operating_chain.py
  - brick_protocol/support/operator/orchestration_packet.py
  - brick_protocol/support/docs/references/*.md
  - brick_protocol/brick/README.md
  - project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Required migration proof:

```text
- changed_files, moved_files, deleted_files explicit
- old path absence/presence policy explicit
- new path admission/checker coverage
- focused building_plans_boundary_sweep proof
- focused package_path_admission proof
- affected profile proof, especially core, link_routing_behavioral, building_operator_driver0
- python3 -m compileall -q brick_protocol
- python3 brick_protocol/support/checkers/check_profile.py --profile core
- python3 brick_protocol/support/checkers/check_profile.py --profile link_routing_behavioral
- python3 brick_protocol/support/checkers/check_profile.py --profile building_operator_driver0
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
```

## 7. ⑩c disposition

```text
phase: ⑩c building_plans location decision
status: closed as KEEP for now
changed_files: this support decision doc + GOAL status only
moved_files: none
deleted_files: none
next cleanup candidates:
  - ⑩f customer UX layer design
  - ⑩g dogfood vessel separation human-gate packet/design
  - cleanup-10e-order-chain-consistency-0709a if skill-chain drift repair is chosen
```

## 8. Not proven

```text
- This document does not prove that building_plans is the permanent ideal product
  name or location.
- This document does not implement a migration.
- This document does not prove no future archive/supersede work will be useful.
- This document does not close ⑩f customer UX or ⑩g dogfood vessel separation.
- This document does not judge success/quality or choose Link Movement.
```

## 9. Movement language

This document authors no Link Movement. Operationally, the cleanup track may
continue on the current declared road:

```text
next_movement_candidate: forward
reason: ⑩c decision is evidence-only KEEP; no reroute target is opened by this doc.
```
