# FINAL architecture — first case_runners.py leaf extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- graph packet: `project/brick-protocol/status/kernel/GOAL/final-case-runners-leaf-extraction-0630a.json`
- building_id: `final-case-runners-leaf-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex `work` -> Codex `code-attack-qa` + Gemini `axis-attack-qa` fan-in -> Codex `closure`
- base_sha: `e0244589b251e2cd397efb11ac35eac5bc296ff7`
- Building sandbox commit: `d5bf125a8b23b32d5b11cd031d58aadb5af24d8c`
- landed main commit: `abcd439` (`BRICK building output: final-case-runners-leaf-extraction-0630a`)
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-case-runners-leaf-extraction-0630a`

## Independent conservation requirements re-derived and checked

Required before source move:

1. exact symbols: `_preset_completion_command_runner`, `_preset_completion_prompt_from_cli_args`, `_is_gemini_json_invocation`, `_output_last_message_path`, `_deterministic_completion_list`, `_return_labels_from_cli_prompt`.
2. dependency closure: two constants also had to move or be imported/re-exported: `_PRESET_COMPLETION_LIST_RETURN_FIELDS`, `_PRESET_COMPLETION_REPO_ARTIFACT_FIELDS`. This was a necessary handling beyond the first ledger wording because the moved runner and deterministic list helper depend on them, and `case_runners.py` still has one caller needing `_PRESET_COMPLETION_LIST_RETURN_FIELDS`.
3. affected RULE_RUNNERS labels: none directly; all callers remain inside `run_*_case` functions and resolve through `case_runners.py` re-export.
4. profile pin survival: no moved function/constant name is profile-pinned; existing `case_runners.py` path pins target other needles and remain in place.
5. module registry: exactly one new flat sibling row for `support/checkers/lib/preset_completion_fixture.py`, with `layer: checkers/lib`, `role: checker-lib`, empty `owns_crossings`, `consumes_crossings`, and `imports_axis`, and the existing forbidden ownership set.
6. graph declaration edge case: fan-out source nodes require `completion_edge_ref`; first launch failed closed with `missing_completion_edge_ref@final-case-runners-leaf-work`, then graph packet was repaired. This prevents support from choosing an outgoing edge by position.
7. verification: byte-identical AST source segments, import smoke, compileall, `check_profile.py --all`, and mutation-RED probes.

## Landed changes

```text
support/checkers/lib/case_runners.py              | 211 +---------------------
support/checkers/lib/preset_completion_fixture.py | 210 +++++++++++++++++++++
support/checkers/module_registry.yaml             |  10 +
```

Net result: `case_runners.py` shrank by roughly 202 body lines while one flat
checker-lib sibling was added. This is god-module shrinkage, not whole-repo LOC
golf.

## Operator verification after landing on main

Commands run on main after cherry-picking the Building output:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/case_runners.py support/checkers/lib/preset_completion_fixture.py
PYTHONPATH=support/import_identity:. python3 - <<'PY' ... import smoke for six re-exported names ... PY
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
python3 - <<'PY' ... AST source-segment byte-identical comparison against base e024458 ... PY
```

Observed results:

```text
git diff --check: green
compileall: green
import smoke: {'missing': [], 'count': 6}
check_profile.py --all: exit 0, 28 profiles passed
byte-identical function comparison: {'missing': [], 'mismatched': []}
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: change _is_gemini_json_invocation to always return False
Result: check_profile.py --all RC=1; adapter_gate_shape_union_case rejected evidence
        frontier_kind expected 'complete', observed 'agent_incomplete'

Mutation B: remove _preset_completion_command_runner from the case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _preset_completion_command_runner
```

Narrow conclusion: the moved fixture helper code and the re-export seam are live,
not dead code.

## Narrowly proven

- The implementation ran through the official `brick build --graph` customer route.
- The graph was composition-first for this task: implementation work + two distinct QA lenses + closure synthesis.
- The Building frontier reached `complete` with 4 Agent returns and 9 Link rows, all declared `forward`.
- The landed code keeps the six declared helper function bodies byte-identical to the base commit.
- The additional two constants were moved/re-exported as necessary dependency closure, with no profile pin hit.
- The new module registry row is support/checker-lib scoped and owns no axis crossing.
- Real HOME `check_profile.py --all` is green after landing.
- Mutation-RED proves the moved helper path and re-export seam are load-bearing.

## Not proven / caveats

- This is the first small `case_runners.py` leaf extraction, not full god-module cleanup.
- Whole-repo architecture minimization, kernel_checks split, walker/run split, profile thinning, and safe deletion of other candidates remain not proven.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or widen the durable product Smith-residue checker as a release guard. Do not start
with kernel_checks, walker/run, broad profile deletion, or a new module family.
