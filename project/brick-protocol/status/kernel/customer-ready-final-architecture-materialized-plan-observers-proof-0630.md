# FINAL architecture — materialized plan observer helper extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-materialized-plan-observers-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-materialized-plan-observers-extraction-0630a.json`
- building_id: `final-materialized-plan-observers-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `08cdb224a434048f86728ac792df4907cb4923b8`
- Building sandbox commit: `2b59378b6d3d44a9e0e8504e7380711e85283d02`
- landed main commit: `c24667e` (`BRICK building output: final-materialized-plan-observers-extraction-0630a`)
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-materialized-plan-observers-extraction-0630a`

## Landed change

```text
support/checkers/lib/case_runners.py                  | shrink
support/checkers/lib/materialized_plan_observers.py   | new flat checker-lib sibling
support/checkers/module_registry.yaml                 | +1 support-only row
```

Moved byte-identical helpers:

```text
_link_rows_list_field
_materialized_step_values
_link_rows_in_declared_order
_link_rows_provenance_tokens
_link_rows_provenance_declared_by
_observed_link_row_values
_check_materialize_building_declaration_evidence
_check_declaration_ref_expectations
```

Live size after landing:

```text
case_runners.py: 10527 LOC
materialized_plan_observers.py: 210 LOC
preset_completion_fixture.py: 210 LOC
module_registry.yaml: 1912 LOC
```

## Operator verification after landing on main

Commands:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/materialized_plan_observers.py
PYTHONPATH=support/import_identity:. python3 - <<'PY' ... import smoke for all eight re-exported names ... PY
PYTHONPATH=support/import_identity:. python3 - <<'PY' ... AST source-segment byte-identical comparison against base 08cdb224 ... PY
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed:

```text
git diff --check: green
compileall: green
import smoke: missing=[]; all eight names resolve from case_runners to materialized_plan_observers
byte-identical comparison: missing=[] mismatched=[]
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: change _link_rows_in_declared_order to return []
Result: check_profile.py --all RC=1; materialize_building_intent_case rejected
        gate_concept_provenance_by_row expected [[], [], [], [], []], observed []

Mutation B: remove _check_declaration_ref_expectations from the case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _check_declaration_ref_expectations
```

Narrow conclusion: the moved observer code and the re-export seam are live, not
dead code.

## Narrowly proven

- The implementation ran through official `brick build --graph` and reached `frontier_kind=complete`.
- Both QA lanes returned no Link-facing `transition_concern_evidence`.
- The eight helper bodies moved byte-identically into a flat support checker-lib sibling.
- `case_runners.py` still exposes the old private helper names for existing callers.
- The new module registry row owns no axis crossing and imports no axis.
- REAL HOME `check_profile.py --all` is green after landing.
- Mutation-RED proves both the helper path and import seam are load-bearing.

## Not proven / caveats

- This is one more god-module leaf, not full FINAL architecture completion.
- `case_runners.py` remains large at 10527 LOC; `kernel_checks.py`, `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
