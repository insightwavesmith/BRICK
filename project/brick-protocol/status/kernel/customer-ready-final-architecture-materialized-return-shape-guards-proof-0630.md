# FINAL architecture — materialized return-shape guard extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-materialized-return-shape-guards-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-materialized-return-shape-guards-extraction-0630a.json`
- building_id: `final-materialized-return-shape-guards-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `9177749c6ddabca2ca6188bfb7f1c24de3af98c6`
- Building sandbox commit: `b9a94498e83dcf38015a58a0ad529ce4ed27464b`
- landed main commit: `5a06a1f`
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-materialized-return-shape-guards-extraction-0630a`

## Landed change

```text
support/checkers/lib/case_runners.py                    | shrink (8842 -> 8659 LOC)
support/checkers/lib/materialized_return_shape_guards.py | new flat checker-lib sibling (203 LOC)
support/checkers/module_registry.yaml                   | +1 support-only row
```

Moved byte-identical helpers:

```text
_materialized_return_shape_fields
_brick_return_shape_fields
_materialized_brick_row_field
_materialized_brick_row_shape
_check_materialized_node_return_shapes
```

## Operator verification after landing on main

```text
git diff --check: green
compileall: green
import smoke: missing=[]; all five names resolve from case_runners to materialized_return_shape_guards
byte-identical comparison vs base 9177749: missing=[] mismatched=[]
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: make _materialized_return_shape_fields return []
Result: check_profile.py --all RC=1; materialize_building_intent_case rejected:
        fan-in SOURCE node ... required_return_shape is not brick-derived;
        expected full brick return.yaml shape [...], observed []

Mutation B: remove _check_materialized_node_return_shapes from case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _check_materialized_node_return_shapes
```

Narrow conclusion: the moved return-shape guard path and re-export seam are live,
not dead code.

## Narrowly proven

- Official `brick build --graph` route reached `frontier_kind=complete`.
- Code-QA raised a sandbox `verification_gap`, but main operator gate closed it:
  REAL HOME `check_profile.py --all` is green after landing.
- The five moved helper bodies are byte-identical in a flat support checker-lib sibling.
- The new module registry row owns no axis crossing and imports no axis.
- Mutation-RED proves both the return-shape guard and import seam are load-bearing.

## Not proven / caveats

- This is the seventh god-module leaf, not full FINAL architecture completion.
- `case_runners.py` is now 8659 LOC (down from 10907 at session start); `kernel_checks.py` (11449 LOC), `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
