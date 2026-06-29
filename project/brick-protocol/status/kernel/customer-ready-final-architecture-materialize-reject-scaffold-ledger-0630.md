# FINAL architecture — conservation ledger: materialize-reject scaffold helper extraction (0630)

Status: DESIGN / not_proven. Conservation contract for the next case_runners.py
god-module shrink. No source mutation here; implementation must run through the
official Building route.

## Why this leaf

`support/checkers/lib/case_runners.py` is still 10,269 LOC after four leaves. The
next safe cluster is checker-only materialize-reject scaffold code used to mutate
a copied in-memory shape registry for negative probes. It never mutates the
on-disk catalog and owns no Brick/Agent/Link meaning, Movement, target selection,
success, or quality.

## Proposed module

```text
support/checkers/lib/materialize_reject_scaffold.py
```

Flat sibling only. `case_runners.py` imports/re-exports the moved names.

## Exact symbols to move (live spans, case_runners.py)

```text
_materialize_reject_strip_preset_keys  def @ 933
_materialize_reject_patch_preset_steps def @ 942
_stripped_chain_preset_keys            def @ 966
_patched_chain_preset_steps            def @ 1009
_StripProbe                            class @ 1041
```

Measured span: lines 933-1050 = about 118 lines. Dependencies:

```text
contextlib
Mapping
Sequence
Any
ProfileError
require_mapping
require_string_list
```

No axis imports. The helpers patch the materializer function's module globals
inside a context manager and restore them on exit; this behavior must remain
byte-identical.

## Current callers to preserve

```text
_materialize_reject_strip_preset_keys: 248, 1070
_materialize_reject_patch_preset_steps: 1071
_stripped_chain_preset_keys: 254, 1110
_patched_chain_preset_steps: 1077
_StripProbe: internal lazy truth object
```

Import/re-export all five names in `case_runners.py`.

## Pins and registry

Profile/module_registry scan found no text pins for these helper names. Add one
module_registry row among the existing checker-lib sibling rows:

```yaml
  - module: support/checkers/lib/materialize_reject_scaffold.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (materialize_building_intent negative-probe registry scaffold; homes no crossing mechanics, imports no axis)
```

## Required implementation mechanics

1. Create `support/checkers/lib/materialize_reject_scaffold.py` with the imports
   above and the five symbol bodies moved byte-identically.
2. Delete the five bodies from `case_runners.py`.
3. Add `from support.checkers.lib.materialize_reject_scaffold import (...)` for
   all five names.
4. Add the module_registry row.
5. Do not touch profiles, operator runtime, templates, Agent resources, customer
   docs, or other checker modules.

## Verification / mutation-RED

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/materialize_reject_scaffold.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison vs pre-move base for all moved defs/classes => missing=[] mismatched=[]
import smoke: all five names available from support.checkers.lib.case_runners
```

Mutation-RED in temp detached worktree:

```text
A. Break _stripped_chain_preset_keys so it never strips keys => materialize_building_intent_rejects must RED.
B. Remove _patched_chain_preset_steps from case_runners.py import block => import/caller smoke must RED.
```

If sandbox cannot run probes, record not_proven in the Building return and close
via operator gate in main.

## Expected conservation

- case_runners.py shrinks by roughly 110 LOC after re-export.
- Whole-repo LOC may slightly increase due to file header/imports; metric is
  god-module shrinkage with byte-identical behavior.
- No Brick/Agent/Link ownership moves. Support checker negative-probe scaffold only.

## Next Movement candidate

Official graph Building:

```text
Codex work(write=True, bounded support/checkers/lib + module_registry scope)
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
```
