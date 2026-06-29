# FINAL architecture — conservation ledger: plan fixture helper extraction (0630)

Status: DESIGN / not_proven. This is the conservation contract for the next
case_runners.py god-module shrink. No source mutation is made by this record;
implementation must run through the official Building route.

## Why this leaf

After two support-only helper extractions, `support/checkers/lib/case_runners.py`
is still 10,527 LOC. The next safe cluster is a checker-only plan fixture/helper
set used by compose/building/gate-sequence/casting cases. It builds or normalizes
support checker fixture plans; it does not own Brick, Agent, Link, Movement,
target selection, success, or quality.

## Proposed module

Create one flat sibling:

```text
support/checkers/lib/plan_fixture_helpers.py
```

No new folder, no new module family. `case_runners.py` remains the caller/facade
and imports/re-exports every moved helper name so existing call sites keep the
same surface.

## Exact symbols to move (live spans, case_runners.py)

Move this contiguous cluster verbatim:

```text
_gate_sequence_policy_link_row       def @ 5390
_gate_sequence_policy_context        def @ 5395
_compose_building_profile_plan       def @ 5417
_graph_test_plan_from_linear         def @ 5433
_validation_plan_for_declared_plan   def @ 5553
_compose_building_expected_codes     def @ 5562
_optional_positive_int               def @ 5571
_compose_building_ok_callable        def @ 5580
```

Measured span: lines 5390-5586 = 197 lines. Dependencies:

```text
json
Path
Mapping
Sequence
Any
ProfileError
require_mapping
require_string
require_string_list
_case_slug
```

The new module should define a local `_case_slug` helper or accept it by import
only if that avoids circular imports. Preferred conservation choice: define the
same tiny local `_case_slug` body in the new helper module, because importing it
from `case_runners.py` would create a support-to-facade cycle. This is the only
non-byte-identical addition; the eight moved function bodies themselves remain
byte-identical except that `_graph_test_plan_from_linear` resolves `_case_slug`
from its new module global. Operator byte-identity comparison should therefore
compare the eight moved def bodies after accounting for identical source text,
not require surrounding helper definitions to match.

No axis imports. The function bodies contain local support/operator imports
(`compose_building`, `_linear_plan_from_graph_plan`) exactly as they do today;
those remain support mechanics and not ownership transfer.

## Current callers to preserve

Existing `case_runners.py` call sites:

```text
_gate_sequence_policy_link_row:     3912, 3936, 3966, 3998
_gate_sequence_policy_context:      3913, 3937
_compose_building_profile_plan:     3695, 3876
_graph_test_plan_from_linear:       5629, 5976, 9016, 10161
_validation_plan_for_declared_plan: 5996, 6058, 6109, 6908, 7004
_compose_building_expected_codes:   3870
_optional_positive_int:             1217, 3871
_compose_building_ok_callable:      3790
```

Import/re-export all eight names in `case_runners.py`.

## Pins and registry

Profile/module_registry scan found no text pins for these helper names. Existing
pins on `support/checkers/lib/case_runners.py` target other needles and must stay
there. Add one module_registry row directly after the current `case_runners.py`
helper siblings:

```yaml
  - module: support/checkers/lib/plan_fixture_helpers.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (checker-only plan fixture/helper builders; homes no crossing mechanics, imports no axis)
```

Existing rows keep their ownership fields unchanged.

## Required implementation mechanics

1. Create `support/checkers/lib/plan_fixture_helpers.py` with imports and a local
   `_case_slug` helper, then move the eight function bodies verbatim.
2. Delete the eight bodies from `case_runners.py`.
3. Add `from support.checkers.lib.plan_fixture_helpers import (...)` in
   `case_runners.py` for all eight moved names.
4. Add the module_registry row.
5. Do not touch profiles, operator runtime, templates, Agent resources, customer
   docs, or other checker modules.

## Verification / mutation-RED

Operator gates required after Building output lands:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/plan_fixture_helpers.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison against pre-move base for all eight moved defs => missing=[] mismatched=[]
import smoke: all eight names are available from support.checkers.lib.case_runners
```

Mutation-RED probes in a temporary detached worktree:

```text
A. Break _graph_test_plan_from_linear to return {} => --all or focused compose/casting cases must RED.
B. Remove _compose_building_ok_callable from the case_runners.py import block => import/caller smoke must RED.
```

If the sandbox cannot run temp-dependent probes, record not_proven inside the
Building return and close them via operator gate in the main worktree.

## Expected conservation

- `case_runners.py` shrinks by roughly 185-190 LOC after the re-export block.
- Whole-repo LOC may slightly increase due to new file header/imports/local
  `_case_slug`; the metric is god-module shrinkage with behavior-preserving
  helper relocation.
- No Brick/Agent/Link ownership moves. This is support checker fixture code only.

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
