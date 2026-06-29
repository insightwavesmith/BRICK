# FINAL architecture — gate-evidence reader helper extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-gate-evidence-readers-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-gate-evidence-readers-extraction-0630a.json`
- building_id: `final-gate-evidence-readers-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `bd890f284ef498bc63a908d5c2f740f527a7c932`
- Building sandbox commit: `aacdae0aad8aa57d6735b62056bf9cfebd305f62`
- landed main commit: `8420cc8`
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-gate-evidence-readers-extraction-0630a`

## Landed change

```text
support/checkers/lib/case_runners.py         | shrink (10340 -> 10269 LOC)
support/checkers/lib/gate_evidence_readers.py| new flat checker-lib sibling (88 LOC)
support/checkers/module_registry.yaml        | +1 support-only row
```

Moved byte-identical helpers:

```text
_assert_no_missing_gate_facts
_assert_missing_gate_fact_present
_gate_evidence_paths
_json_records
_nested_values_for_key
```

Kept in case_runners.py (NOT moved, broad helpers):

```text
_preset_slug
_case_slug
_split_ref_row
```

## Operator verification after landing on main

```text
git diff --check: green
compileall: green
import smoke: missing=[]; all five names resolve from case_runners to gate_evidence_readers;
  _preset_slug/_case_slug/_split_ref_row confirmed still in case_runners
byte-identical comparison vs base bd890f2: missing=[] mismatched=[]
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: make _nested_values_for_key return () (strip the missing-fact reader's teeth)
Result: check_profile.py --all RC=1; building_intake_seam_case rejected:
        expected missing fact 'Link.route_decision_basis.human_review_refs' not recorded; observed []

Mutation B: remove _gate_evidence_paths from the case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _gate_evidence_paths
```

Narrow conclusion: the moved gate-evidence reader path and the re-export seam are
live, not dead code.

## Narrowly proven

- The implementation ran through official `brick build --graph` and reached `frontier_kind=complete`.
- Both QA lanes returned no Link-facing `transition_concern_evidence`.
- The five helper bodies moved byte-identically into a flat support checker-lib sibling.
- The broad `_preset_slug/_case_slug/_split_ref_row` helpers correctly stayed in case_runners.py.
- `case_runners.py` still exposes the five moved names for existing callers.
- The new module registry row owns no axis crossing and imports no axis.
- REAL HOME `check_profile.py --all` is green after landing.
- Mutation-RED proves both the helper path and import seam are load-bearing.

## Not proven / caveats

- This is the fourth god-module leaf, not full FINAL architecture completion.
- `case_runners.py` remains large at 10269 LOC; `kernel_checks.py` (11449 LOC), `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
