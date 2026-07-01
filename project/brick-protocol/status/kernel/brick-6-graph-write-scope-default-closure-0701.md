# Task #8 closure evidence — write_scope default-on-omission fix (0701)

Status: support evidence for task #8 (finding doc
`brick-6-graph-route-missing-default-write-scope-finding-0701.md`). Not
source truth, success judgment, quality judgment, or Movement authority.

## Attempt history (Building launches, not code attempts)

| Attempt | Result | Disposition |
|---|---|---|
| 1st (`--timeout 900`) | `frontier_kind=agent_incomplete`, work step's codex hit the full 900s timeout while genuinely alive (confirmed via BRICK's own stall-watchdog telemetry: `timeout_reap_reason=timeout`, not `stall` -- NOT a recurrence of the 0619 connect-stall bug) | not adopted, retried with larger budget |
| 2nd/3rd (`--timeout 1800`) | `input_rejected` both times -- 2nd was a COO launch mistake (missing `cd BRICK`, ran in the frozen museum worktree), 3rd was `driver.py`'s "declared Building plan already exists" guard firing because `--overwrite-existing` was omitted on a same-building_id retry | not adopted, both COO process errors, not Building/code defects |
| **4th (`--timeout 1800 --overwrite-existing`)** | `frontier_kind=complete` | **adopted** (this document) |

These launch-method lessons are now consolidated in memory as
`brick-build-launch-playbook-0701`.

## 4th attempt observed evidence

- Declaration commit: `990cccd`.
- Sandbox output commit: `e1d80099db79d7b743dc5d812d2ea01aa4403916`.
- Adopted to main as: `6c3c73e`.
- Changed files: `support/operator/composition_compose.py`,
  `support/checkers/check_assembly_equivalence.py`,
  `support/checkers/check_building_operator_driver0.py`,
  `support/checkers/lib/adapter_capability_checks.py`,
  `support/checkers/lib/case_runners.py`,
  `support/checkers/lib/casting_node_carry_check.py`,
  `support/checkers/lib/kernel_checks.py`,
  `support/checkers/lib/plan_fixture_helpers.py`.
- Fix: `composition_compose.py` now imports and applies
  `brick_protocol.brick.spec.derived_worktree_write_scope()` as the default
  whenever a step_template declares a write need and the graph node supplied
  no explicit `write_scope` -- reused, not duplicated, matching
  `assembly.py`'s existing correct behavior. An explicit node-level
  `write_scope` still overrides the default (unchanged).
- New checker-first probe: `check_assembly_equivalence.py::_graph_write_scope_default_fire()`
  -- asserts a write-needed node with no `write_scope` now derives
  `{"allowed_paths": ["."], "forbidden_paths": [".git/**"]}` and
  `requires_brick_write_scope=True`; asserts an explicit narrower
  `write_scope` on another node still overrides the default unchanged.
  Wired into the profile's `run()` so it executes on every sweep.

## Independent verification performed before adoption (Claude, detached worktree)

Verification hit two false failures before a clean pass, both caused by
stray untracked files left in the shared `/tmp/verify-write-scope-default`
detached worktree by unrelated processes (my own improperly-managed
background job debris, and a concurrently-running research workflow that
wrote an output file into the same path) -- `package_path_admission`
correctly rejected both as unexpected paths. Neither was a defect in the
sandbox commit. After removing the stray files:

```text
py_compile (all 8 changed files): PASS
check_profile.py --profile assembly_equivalence.yaml: PASS
  "graph compose omitted write_scope now derives worktree default" (RED/GREEN observed)
  "graph compose explicit write_scope still overrides default"
git diff --check: PASS
check_profile.py --all: DIRECT_EXIT=0, 30/30 profiles passed to completion,
  including pin_estate_integrity ("0 history-doc pin block(s)") and
  tier-a-three-axis-conformance (last profile in the sweep)
Re-verified again after cherry-pick onto current main: py_compile PASS,
  focused profile PASS (kernel_check=assembly_equivalence, 3.2s), git diff --check PASS
```

## Narrowly proven

- A write-needed Brick node reaching `brick build --graph` with no explicit
  `write_scope` now receives the same worktree-minus-`.git` default that
  `assembly.py`'s onboard-wizard path already applied, instead of silently
  resolving to zero effective write capability.
- An explicit node-level `write_scope` still overrides the default
  (regression-guarded).

## Not proven

- The graph_topology_fan_barrier checker's admission-time wiring (Global
  Operating Rule 8's other half) -- still a separate follow-on, not touched
  by this Building.
- Whether the whole-worktree-minus-`.git` default is the ideal default for
  every future Brick kind (only that it is not worse than silent zero-write).
- P8 ship safety, P9 dynamic customer replay, fresh-machine install,
  real-provider reliability, customer comprehension.
- Task #9 (dual plan-materialization producer reconciliation) remains
  entirely open and untouched by this Building, per Global Operating Rule 9.

## Next Movement candidate

Task #8 is closed. Proceed to tasks #6/#7 (already declared as one combined
Building, `brick-6-fanout-latency-and-fanin-cohort-fix-0701a.json`, held
until #8 landed on main to avoid two concurrent code-mutating Buildings),
then task #9, then P8.
