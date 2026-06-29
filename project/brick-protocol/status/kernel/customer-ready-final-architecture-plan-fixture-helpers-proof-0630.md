# FINAL architecture — plan fixture helper extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-plan-fixture-helpers-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-plan-fixture-helpers-extraction-0630a.json`
- building_id: `final-plan-fixture-helpers-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `10bc7039efbac128d88b390c18c835420bcaed8e`
- Building sandbox commit: `c7daf7e74a9f27245213beae34fc0be021974a5a`
- landed main commit: `44be7fa` (`BRICK building output: final-plan-fixture-helpers-extraction-0630a`)
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-plan-fixture-helpers-extraction-0630a`

## Landed change

```text
support/checkers/lib/case_runners.py        | shrink
support/checkers/lib/plan_fixture_helpers.py| new flat checker-lib sibling
support/checkers/module_registry.yaml       | +1 support-only row
```

Moved byte-identical helpers:

```text
_gate_sequence_policy_link_row
_gate_sequence_policy_context
_compose_building_profile_plan
_graph_test_plan_from_linear
_validation_plan_for_declared_plan
_compose_building_expected_codes
_optional_positive_int
_compose_building_ok_callable
```

The new helper module also defines a local `_case_slug` helper to avoid importing
from the `case_runners.py` facade; this is outside the moved bodies and avoids a
support-to-facade cycle.

Live size after landing:

```text
case_runners.py: 10340 LOC
plan_fixture_helpers.py: 223 LOC
materialized_plan_observers.py: 210 LOC
preset_completion_fixture.py: 210 LOC
module_registry.yaml: 1922 LOC
```

## Operator verification after landing on main

Commands:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/plan_fixture_helpers.py
PYTHONPATH=support/import_identity:. python3 - <<'PY' ... import smoke for all eight re-exported names ... PY
python3 - <<'PY' ... AST source-segment byte-identical comparison against base 10bc703 ... PY
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed:

```text
git diff --check: green
compileall: green
import smoke: missing=[]; all eight names resolve from case_runners to plan_fixture_helpers
byte-identical comparison: missing=[] mismatched=[]
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: change _graph_test_plan_from_linear to return {}
Result: check_profile.py --all RC=1; adapter_capability_rehome_case path raised
        ValueError: Building plan must contain a non-empty steps list

Mutation B: remove _compose_building_ok_callable from the case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _compose_building_ok_callable
```

Narrow conclusion: the moved fixture helper path and the re-export seam are live,
not dead code.

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
- `case_runners.py` remains large at 10340 LOC; `kernel_checks.py`, `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
