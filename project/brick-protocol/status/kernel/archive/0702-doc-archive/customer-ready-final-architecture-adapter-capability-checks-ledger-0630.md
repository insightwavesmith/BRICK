# FINAL architecture — conservation ledger: adapter-capability check helper extraction (0630)

Status: DESIGN / not_proven. Conservation contract for the next case_runners.py
god-module shrink. No source mutation here; implementation runs through the
official Building route.

## Why this leaf

`support/checkers/lib/case_runners.py` is still 10,158 LOC after five leaves. The
largest remaining cohesive cluster is the adapter-capability check helper set:
34 private helpers that the dispatcher `run_adapter_capability_rehome_case`
fans into per `case_kind`. They build adapter-capability request/plan fixtures
and assert recorded write-policy facts. They are pure support checker mechanics:
no Brick/Agent/Link ownership, no Movement, no target selection, no
success/quality judgment.

## Proposed module

```text
support/checkers/lib/adapter_capability_checks.py
```

Flat sibling only. The dispatcher `run_adapter_capability_rehome_case` STAYS in
case_runners.py (it is a `run_*` entry referenced via RULE_RUNNERS); only its 34
private helpers move. case_runners.py imports/re-exports the moved names so the
dispatcher and any other caller keep the same surface.

## Exact symbols to move (live spans, case_runners.py)

Contiguous span lines 5507-6858 (= 1352 lines), all 34 helpers between the
`run_adapter_capability_rehome_case` dispatcher (ends ~5506, NOT moved) and
`_once_task_source_packet` (starts 6859, NOT moved):

```text
_expect_adapter_capability_rejection
_adapter_capability_write_scope
_adapter_capability_request
_adapter_capability_plan
_check_adapter_capability_ok_all_four
_check_adapter_capability_claude_write_ok
_check_adapter_capability_missing_brick_scope
_assert_recorded_write_policy_fact
_check_adapter_capability_missing_agent_policy
_check_adapter_capability_missing_adapter_capability
_check_adapter_capability_observation_out_of_scope
_check_adapter_capability_poc_read_only_with_write_scope
_check_adapter_capability_legacy_identity_only
_check_adapter_capability_no_write_observation_without_scope
_check_adapter_capability_write_capable_leader_effective_write_gated_by_brick_scope
_native_grant_policy_resource
_native_grant_policy_resources
_check_adapter_capability_native_grant_roundtrip
_check_adapter_capability_native_grant_semantic_codex_gemini_parity
_check_adapter_capability_retired_gemini_api_no_write_or_probe
_check_adapter_capability_checker_sweep_blocks_live_provider_cli
_check_adapter_capability_native_grant_policy_only_fails_closed
_check_adapter_capability_native_grant_write_home_pin
_check_adapter_capability_native_grant_unknown_capability
_check_adapter_capability_write_capable_leader_read_only_brick_projection
_check_adapter_capability_write_capable_leader_write_needed_brick_projection
_check_adapter_capability_write_scope_on_read_only_brick_rejected
_check_adapter_capability_silent_write_grant_rejected_at_run_admission
_check_adapter_capability_explicit_write_need_marker_admitted_strict
_check_adapter_capability_legacy_write_need_marker_not_recognized
_check_adapter_capability_legacy_write_need_graph_row_key_rejected
_adapter_capability_single_step_packet
_check_adapter_capability_silent_write_grant_rejected_single_step
_check_adapter_capability_explicit_write_need_marker_single_step_proceeds
```

## Dependency audit (measured)

- Every one of the 34 symbols is referenced ONLY by the dispatcher
  (`run_adapter_capability_rehome_case`, outside=1) or purely within the cluster
  (outside=0). No OTHER case body uses them.
- The cluster calls NO case_runners-private helper that lives outside the cluster
  (measured: zero outside-cluster case_runners defs are called).
- All heavy dependencies (`agent_adapter`, `plan_validation`, `run`,
  `agent_resources`, `adapter_constants`, `plan_graph`, `write_observation`,
  `brick.comparison`, `recording.*`) are imported INSIDE the helper bodies as
  local imports; they do not need module-level imports in the new sibling.
- Module-level imports the new sibling needs:

```text
import json
import os
import tempfile
import copy
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from support.checkers.lib.yaml_subset import ProfileError
```

`require_write_need_marker` is a keyword-argument NAME passed to
`validate_declared_building_plan`, not an imported symbol.

## Current callers to preserve

The dispatcher `run_adapter_capability_rehome_case` (stays in case_runners.py)
calls all 34 names. case_runners.py must import/re-export the full set so the
dispatcher and RULE_RUNNERS behavior is byte-identical.

## Pins and registry

No profile/module_registry TEXT pin names any of the 34 helper symbols. (The
`agent_axis_behavioral` profile pins case-VALUE strings like `ok_all_four`,
`poc_read_only_adapter_with_write_scope`,
`legacy_adapter_identity_only_not_authority` on the case_runners.py path; those
are case_kind data values that stay in the dispatcher / profile and are NOT
function names, so they are unaffected by moving the helper bodies.) Add one
module_registry row among the checker-lib sibling rows:

```yaml
  - module: support/checkers/lib/adapter_capability_checks.py
    layer: checkers/lib
    role: checker-lib
    owns_crossings: []
    consumes_crossings: []
    imports_axis: []
    forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
    decomposition_target: ""
    pinned_by: pure-relocation sibling of case_runners (adapter_capability_rehome check helpers; homes no crossing mechanics, imports no axis at module level)
```

## Required implementation mechanics

1. Create `support/checkers/lib/adapter_capability_checks.py` with the
   module-level imports above and the 34 helper bodies moved byte-identically
   (their in-body local imports move verbatim with them).
2. Delete the 34 bodies from case_runners.py.
3. Add `from support.checkers.lib.adapter_capability_checks import (...)` in
   case_runners.py for all 34 names.
4. Add the module_registry row.
5. Do not move `run_adapter_capability_rehome_case`. Do not touch profiles,
   operator runtime, templates, Agent resources, customer docs, or other checker
   modules.

## Verification / mutation-RED

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/adapter_capability_checks.py
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
AST source-segment comparison vs pre-move base for all 34 defs => missing=[] mismatched=[]
import smoke: all 34 names available from support.checkers.lib.case_runners
```

Mutation-RED in temp detached worktree:

```text
A. Break _check_adapter_capability_ok_all_four (make it return without asserting) => adapter_capability_rehome_case must RED.
B. Remove _adapter_capability_request from the case_runners.py import block => import/dispatcher smoke must RED.
```

If sandbox cannot run probes, record not_proven in the Building return and close
via operator gate in main.

## Expected conservation

- case_runners.py shrinks by ~1340 LOC after the re-export block (the single
  largest leaf this session): roughly 10158 -> ~8830 LOC.
- Whole-repo LOC roughly flat (bodies relocate; small import/header overhead).
- No Brick/Agent/Link ownership moves. Support adapter-capability check code only.

## Next Movement candidate

Official graph Building:

```text
Codex work(write=True, bounded support/checkers/lib + module_registry scope)
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
```

Only land if frontier=complete, both QA lanes return no concern, and operator
REAL HOME gates pass.
