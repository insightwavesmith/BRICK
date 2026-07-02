# FINAL architecture — adapter-capability check helper extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-adapter-capability-checks-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-adapter-capability-checks-extraction-0630a.json`
- building_id: `final-adapter-capability-checks-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 1200`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `f5b16692015b94977df885362d46a75aeae77ef0`
- Building sandbox commit: `4527e958958409c10774bf93631f397639ee760a`
- landed main commit: `6470794`
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-adapter-capability-checks-extraction-0630a`

## Landed change (largest single leaf this session)

```text
support/checkers/lib/case_runners.py             | shrink (10158 -> 8842 LOC)
support/checkers/lib/adapter_capability_checks.py | new flat checker-lib sibling (1375 LOC)
support/checkers/module_registry.yaml            | +1 support-only row
```

34 adapter-capability check helpers moved byte-identically; the dispatcher
`run_adapter_capability_rehome_case` STAYED in case_runners.py and resolves all
34 names through the re-export.

## Operator verification after landing on main

```text
git diff --check: green
compileall: green
moved_count: 34; byte-identical comparison vs base f5b1669: missing_in_old=[] mismatched=[]
re-export smoke: reexport_missing=[]; dispatcher present in case_runners (run_adapter_capability_rehome_case)
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in temporary detached worktrees, then removed.

```text
Mutation B: remove _adapter_capability_request from the case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _adapter_capability_request

Mutation 2: set _adapter_capability_request tool_policy_refs default to ()
Result: check_profile.py --all RC=1; adapter_capability_rehome_case rejected
        native-grant-semantic-codex-gemini-parity: adapter:codex-local read-only
        Brick lost declared semantic capability vocabulary; observed None
```

Honest caveat (pre-existing checker strength, NOT a regression from this move):

```text
Mutation A: neuter _check_adapter_capability_ok_all_four to a no-op return
Result: check_profile.py --all RC=0 (still green)
```

`_check_adapter_capability_ok_all_four` is an assertion-only positive helper
(it raises only on bad observed data), so neutering it does not flip a clean run.
This is a pre-existing observation about that single positive case's
independent teeth, not introduced by the relocation: the move is byte-identical
(verified) and the stronger fixture-builder mutation (Mutation 2) and re-export
mutation (Mutation B) both fire RED, proving the moved cluster and its seam are
live on the dispatch path. A future checker-strength Building could add an
independent negative twin for the `ok_all_four` positive case; recorded here as a
candidate, not silently expanded.

## Narrowly proven

- Official `brick build --graph` route reached `frontier_kind=complete`.
- Both QA lanes returned no Link-facing `transition_concern_evidence`.
- 34 moved helper bodies are byte-identical in a flat support checker-lib sibling.
- The dispatcher stayed in case_runners.py; all 34 names re-export cleanly.
- The new module registry row owns no axis crossing and imports no axis at module level.
- REAL HOME `check_profile.py --all` is green after landing.
- Mutation-RED (B + 2) proves the moved cluster and import seam are load-bearing.

## Not proven / caveats

- This is the sixth god-module leaf, not full FINAL architecture completion.
- `case_runners.py` is now 8842 LOC (down from 10907 at session start); `kernel_checks.py` (11449 LOC), `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- The `ok_all_four` positive-case checker-strength gap noted above.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf
(case_runners remaining clusters, or begin kernel_checks.py),
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
