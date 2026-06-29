# Customer-Ready FINAL Architecture — Casting Node Carry Leaf Ledger — 0630

Status: DESIGN / not_proven. Conservation contract for the next `case_runners.py`
leaf extraction. Support evidence only; not source truth, success judgment,
quality judgment, or Link Movement authority.

## Why this leaf

`support/checkers/lib/case_runners.py` is 8,659 LOC after seven landed leaves.
The next safe cluster is the `casting_node_carry` behavioral kernel check: it
is a self-contained graph->linear casting projection probe plus its base graph
fixture helper.

## Boundary

Flat sibling only. `case_runners.py` imports/re-exports the moved names so the
public checker import surface stays byte-compatible for `support/checkers/check_profile.py`.
No new folder, no new module family, no checker semantics change.

## Exact symbols to move (live spans, `case_runners.py`)

| symbol | current span | lines | sha256 of exact body |
|---|---:|---:|---|
| `_casting_node_carry_base_graph_plan` | 5071-5113 | 43 | `10d68c388bd8e87e2639b1f6a7d538c5a5f745a36018fc86120febf4a47ff0ba` |
| `run_casting_node_carry` | 5116-5227 | 112 | `5f33f50a50aad5e2aee87e5cc12ffeb8036fdfdc827a7df0f2cacbbf1de14233` |

## Target file

Create:

```text
support/checkers/lib/casting_node_carry_check.py
```

Import/re-export both names from `support/checkers/lib/case_runners.py`.
The new sibling may import existing checker-lib utilities already used by the
moved bodies (`KernelResult`, `ProfileError`, `_graph_test_plan_from_linear`,
`Mapping`, `Any`, `Path`) but must not import Brick/Agent/Link axis modules at
module import time.

## Module registry row

Add exactly one row:

```yaml
  - module: support/checkers/lib/casting_node_carry_check.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (casting_node_carry graph->linear casting projection kernel check; homes no crossing mechanics, imports no axis at module level)
```

## Conservation requirements

1. Move the two function bodies byte-identically except import qualification if
   absolutely required.
2. Delete the two bodies from `case_runners.py`.
3. `case_runners.py` must re-export both names.
4. `support/checkers/check_profile.py` must not need import changes.
5. Add only the new flat sibling row to `support/checkers/module_registry.yaml`.
6. Do not split `kernel_checks.py`, `walker_kernel.py`, `run.py`, profiles, or
   create any new folder/module family in this Building.

## Required verification

```bash
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/casting_node_carry_check.py
PYTHONPATH=support/import_identity:. python3 - <<'PY'
from support.checkers.lib.case_runners import run_casting_node_carry, _casting_node_carry_base_graph_plan
print(run_casting_node_carry.__module__)
print(_casting_node_carry_base_graph_plan.__module__)
PY
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/agent_axis_behavioral.yaml
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
git diff --check
```

## Mutation-RED probes

A. Remove `run_casting_node_carry` from the `case_runners.py` re-export import
   block => `support/checkers/check_profile.py` import should RED.
B. Change `support.operator.primitives.stamp_casting` or the projected-step
   assertion so one `NODE_CASTING_FIELDS` member is not carried =>
   `casting_node_carry` kernel check should RED. If sandbox limitations prevent
   executing B, record it as not_proven; do not fake it.

## Expected proof shape

- New file exists with exactly the two moved bodies.
- `case_runners.py` shrinks by roughly 150 LOC after re-export.
- All import callers still resolve from `support.checkers.lib.case_runners`.
- `agent_axis_behavioral` and REAL HOME `--all` are GREEN.

## Next Movement candidate

Official graph Building:

```text
project/brick-protocol/status/kernel/GOAL/final-casting-node-carry-extraction-0630a.json
```
