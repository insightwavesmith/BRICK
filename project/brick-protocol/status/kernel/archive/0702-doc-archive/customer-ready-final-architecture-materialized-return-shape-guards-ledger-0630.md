# FINAL architecture — conservation ledger: materialized return-shape guard extraction (0630)

Status: DESIGN / not_proven. Conservation contract for the next case_runners.py
god-module shrink. No source mutation here; implementation runs through the
official Building route.

## Why this leaf

`support/checkers/lib/case_runners.py` is 8,842 LOC after six leaves. The next
safe cluster is the materialized return-shape guard set for graph/fan-in plans.
It checks that Brick return contracts remain brick-derived, that support does not
invent `concern_observations`, and that fan-in source/target return/carry fields
stay honest. This is support checker observation only: no Brick/Agent/Link
ownership, no Movement, no target selection, no success/quality judgment.

## Proposed module

```text
support/checkers/lib/materialized_return_shape_guards.py
```

Flat sibling only. `case_runners.py` imports/re-exports the moved names.

## Exact symbols to move (live spans, case_runners.py)

```text
_materialized_return_shape_fields       def @ 786
_brick_return_shape_fields              def @ 796
_materialized_brick_row_field           def @ 822
_materialized_brick_row_shape           def @ 830
_check_materialized_node_return_shapes  def @ 835
```

Measured span: lines 786-975 (~190 lines). Dependencies:

```text
Path
Mapping
Any
ProfileError
require_string_list
load_yaml_subset_file
```

No axis imports. The helper reads live `brick/templates/bricks/<kind>/return.yaml`
through the checker loader, which is support evidence over Brick-owned source.

## Current callers to preserve

These helpers are called by materialize-building-intent case checks inside
`case_runners.py`; import/re-export all five names in `case_runners.py` so the
existing call sites remain unchanged.

## Pins and registry

No profile/module_registry text pins for these helper names. Add one registry row
among the checker-lib siblings:

```yaml
  - module: support/checkers/lib/materialized_return_shape_guards.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (materialized fan-in return-shape guards; homes no crossing mechanics, imports no axis)
```

## Required implementation mechanics

1. Create `support/checkers/lib/materialized_return_shape_guards.py` with the
   dependencies above and the five bodies moved byte-identically.
2. Delete the five bodies from case_runners.py.
3. Add `from support.checkers.lib.materialized_return_shape_guards import (...)`
   for all five names.
4. Add the module_registry row.
5. Do not touch profiles, operator runtime, templates, Agent resources, customer
   docs, or other checker modules.

## Verification / mutation-RED

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/materialized_return_shape_guards.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison vs pre-move base for all five defs => missing=[] mismatched=[]
import smoke: all five names available from support.checkers.lib.case_runners
```

Mutation-RED in temp detached worktree:

```text
A. Make _materialized_return_shape_fields return [] => materialize_building_intent_case should RED.
B. Remove _check_materialized_node_return_shapes from case_runners.py import block => import/caller smoke should RED.
```

If sandbox cannot run probes, record not_proven in Building return and close via
operator gate in main.

## Expected conservation

- case_runners.py shrinks by roughly 175-185 LOC after re-export.
- Whole-repo LOC may slightly increase due to file header/imports; metric is
  god-module shrinkage with byte-identical behavior.
- No Brick/Agent/Link ownership moves. Support checker return-shape guard code only.

## Next Movement candidate

Official graph Building:

```text
Codex work(write=True, bounded support/checkers/lib + module_registry scope)
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
```
