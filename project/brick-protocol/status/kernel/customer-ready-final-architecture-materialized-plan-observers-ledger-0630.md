# FINAL architecture — conservation ledger: materialized plan observer helper extraction (0630)

Status: DESIGN / not_proven. This is the conservation contract for the next safe
case_runners.py god-module shrink. No source mutation is made by this record.
Implementation must run through the official Building route.

## Why this leaf

After the first leaf extraction, `support/checkers/lib/case_runners.py` is still
10,714 LOC. The next safe cluster is a support-only observer set for materialized
Building Plans and Link rows. It reads already-materialized support packets and
raises `ProfileError` on mismatches; it does not own Brick, Agent, Link,
Movement, target selection, success, or quality.

## Proposed module

Create one flat sibling:

```text
support/checkers/lib/materialized_plan_observers.py
```

No new folder, no new module family. `case_runners.py` remains the facade/caller
and imports/re-exports the helper names needed by existing callers.

## Exact symbols to move (live spans, case_runners.py)

Move this contiguous cluster verbatim:

```text
_link_rows_list_field                         def @ 3502
_materialized_step_values                     def @ 3526
_link_rows_in_declared_order                  def @ 3539
_link_rows_provenance_tokens                  def @ 3557
_link_rows_provenance_declared_by             def @ 3592
_observed_link_row_values                     def @ 3616
_check_materialize_building_declaration_evidence def @ 3628
_check_declaration_ref_expectations           def @ 3667
```

Measured contiguous span: lines 3502-3698 = 197 lines. Dependencies are limited
to stdlib/support checker helpers:

```text
json
Path
Mapping
Any
ProfileError
require_string_list
```

No axis imports. No runtime/provider/credential imports.

## Current callers to preserve

Existing `case_runners.py` call sites:

```text
_link_rows_list_field:                         lines 417, 433
_materialized_step_values:                     line 339
_link_rows_in_declared_order:                  internal to moved helpers
_link_rows_provenance_tokens:                  line 451
_link_rows_provenance_declared_by:             line 466
_observed_link_row_values:                     lines 372, 3908
_check_materialize_building_declaration_evidence: line 524
_check_declaration_ref_expectations:           lines 3659 (internal), 4028
```

Because `_check_declaration_ref_expectations` is used later by compose-building
cases, `case_runners.py` must import/re-export all moved names (or at least every
externally-called moved name). Simpler conservation rule: import/re-export the
full moved set.

## Pins and registry

Profile/module_registry scan found no text pins for these helper names. Existing
pins on `support/checkers/lib/case_runners.py` target other needles and must stay
in that file. Add one module_registry row directly after the `case_runners.py` row:

```yaml
  - module: support/checkers/lib/materialized_plan_observers.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (materialized Building Plan / Link row observer helpers; homes no crossing mechanics, imports no axis)
```

Existing `case_runners.py` row stays; owns/consumes/imports remain `[]`.

## Required implementation mechanics

1. Create `support/checkers/lib/materialized_plan_observers.py` with the imports
   above and the eight bodies moved byte-identically.
2. Delete the eight bodies from `case_runners.py`.
3. Add a `from support.checkers.lib.materialized_plan_observers import (...)`
   block to `case_runners.py` for all eight moved symbols.
4. Add the module registry row.
5. Do not touch profiles, kernel checks, operator runtime, templates, Agent
   resources, or customer docs.

## Verification / mutation-RED

Operator gates required after Building output lands:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/materialized_plan_observers.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison against pre-move base for all eight moved defs => missing=[] mismatched=[]
import smoke: all eight names are available from support.checkers.lib.case_runners
```

Mutation-RED probes in a temporary detached worktree:

```text
A. Break _link_rows_in_declared_order to return [] => --all or focused materialize/compose cases must RED.
B. Remove _check_declaration_ref_expectations from the case_runners.py import block => import/caller smoke must RED.
```

If a sandbox cannot run temp-dependent probes, record not_proven inside the
Building return and close them via operator gate in the main worktree.

## Expected conservation

- `case_runners.py` shrinks by roughly 185-190 LOC after adding the re-export block.
- Whole-repo LOC may slightly increase due to new file header/imports; the metric
  is god-module shrinkage with byte-identical behavior.
- No Brick/Agent/Link ownership moves. This is support checker observer code only.

## Next Movement candidate

Declare and fire one official graph Building:

```text
Codex work(write=True, bounded support/checkers/lib + module_registry scope)
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
```

Only land if frontier=complete, both QA lanes return no concern, and operator
REAL HOME gates pass.
