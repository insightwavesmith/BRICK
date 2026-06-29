# FINAL architecture — conservation ledger: gate-evidence reader helper extraction (0630)

Status: DESIGN / not_proven. Conservation contract for the next case_runners.py
god-module shrink. No source mutation here; implementation runs through the
official Building route.

## Why this leaf

After three support-only helper extractions, `support/checkers/lib/case_runners.py`
is still 10,340 LOC. The next safe cluster is a tight gate-evidence reader set:
it reads persisted Building gate evidence (raw/link.jsonl + step-outputs) and
asserts presence/absence of `missing_required_facts`. It is pure support
observation: it owns no Brick/Agent/Link meaning, no Movement, no target, no
success/quality judgment.

## Proposed module

Create one flat sibling:

```text
support/checkers/lib/gate_evidence_readers.py
```

No new folder, no new module family. `case_runners.py` imports/re-exports the
moved names so existing call sites keep the same surface.

## Exact symbols to move (live spans, case_runners.py)

```text
_assert_no_missing_gate_facts        def @ 3423
_assert_missing_gate_fact_present    def @ 3434
_gate_evidence_paths                 def @ 3467
_json_records                        def @ 3473
_nested_values_for_key               def @ 3487
```

Measured span: lines 3423-3500 = ~78 lines (five defs). Dependencies are
stdlib + one support helper:

```text
json
Path
Mapping
Any
ProfileError
```

`_preset_slug`, `_case_slug`, `_split_ref_row` (3501-3521) are NOT moved: they are
broad helpers (`_case_slug` used 17x in case_runners) and are unrelated to gate
evidence. Keep them in place.

## Current callers to preserve

```text
_assert_no_missing_gate_facts:     5 call sites
_assert_missing_gate_fact_present: 2 call sites
_gate_evidence_paths:              internal + callers
_json_records:                     internal + callers
_nested_values_for_key:            5 call sites
```

Import/re-export all five names in case_runners.py.

## Pins and registry

No profile/module_registry TEXT pin for these names. One YAML COMMENT in
`building_skill_preset_agent_tool_hardening.yaml:1407` mentions
`_assert_no_missing_gate_facts` in prose only (not a `texts:` needle), so moving
the symbol is safe; the comment remains accurate because the symbol still exists
(now in the sibling, re-exported). Add one module_registry row directly after the
existing checker-lib sibling rows:

```yaml
  - module: support/checkers/lib/gate_evidence_readers.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (gate-evidence missing_required_facts readers; homes no crossing mechanics, imports no axis)
```

## Required implementation mechanics

1. Create `support/checkers/lib/gate_evidence_readers.py` with the imports above
   and the five function bodies moved byte-identically.
2. Delete the five bodies from case_runners.py.
3. Add `from support.checkers.lib.gate_evidence_readers import (...)` for all
   five names.
4. Add the module_registry row.
5. Do not touch profiles, operator runtime, templates, Agent resources, customer
   docs, or other checker modules.

## Verification / mutation-RED

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/gate_evidence_readers.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison vs pre-move base for all five defs => missing=[] mismatched=[]
import smoke: all five names available from support.checkers.lib.case_runners
```

Mutation-RED in a temp detached worktree:

```text
A. Make _assert_no_missing_gate_facts a no-op (return immediately) => preset/intake completion cases must still pass (it only RAISES on bad data), so instead break _nested_values_for_key to return () => the missing-fact HOLD assertions lose teeth and an intake-seam negative case must RED.
B. Remove _gate_evidence_paths from the case_runners.py import block => import/caller smoke must RED.
```

If a sandbox cannot run temp-dependent probes, record not_proven inside the
Building return and close them via operator gate in the main worktree.

## Expected conservation

- case_runners.py shrinks by ~70 LOC after the re-export block.
- Whole-repo LOC may slightly increase from the new file header; the metric is
  god-module shrinkage with byte-identical behavior.
- No Brick/Agent/Link ownership moves. Support gate-evidence reader code only.

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
