# FINAL architecture — materialize-reject scaffold extraction proof (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Building route

- ledger: `customer-ready-final-architecture-materialize-reject-scaffold-ledger-0630.md`
- graph packet: `project/brick-protocol/status/kernel/GOAL/final-materialize-reject-scaffold-extraction-0630a.json`
- building_id: `final-materialize-reject-scaffold-extraction-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex work -> Codex code-attack QA + Gemini axis-attack QA fan-in -> Codex closure
- base_sha: `07b99b2fc2421625e7518518bfda6db0a107bdf6`
- Building sandbox commit: `ad93931f84f6078f48bc8e8c6ece40c1c132df6f`
- landed main commit: `5f749c6`
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-materialize-reject-scaffold-extraction-0630a`

## Landed change

```text
support/checkers/lib/case_runners.py              | shrink (10269 -> 10158 LOC)
support/checkers/lib/materialize_reject_scaffold.py | new flat checker-lib sibling (135 LOC)
support/checkers/module_registry.yaml             | +1 support-only row
```

Moved byte-identical symbols:

```text
_materialize_reject_strip_preset_keys
_materialize_reject_patch_preset_steps
_stripped_chain_preset_keys
_patched_chain_preset_steps
_StripProbe
```

## Operator verification after landing on main

```text
git diff --check: green
compileall: green
import smoke: missing=[]; all five names resolve from case_runners to materialize_reject_scaffold
byte-identical comparison vs base 07b99b2: missing=[] mismatched=[]
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

## Mutation-RED probes

Executed in a temporary detached worktree, then removed.

```text
Mutation A: break _stripped_chain_preset_keys so requested keys are not stripped
Result: check_profile.py --all RC=1; materialize_building_intent_case rejected:
        node_reroute_budgets expected {...5...}, observed {...1...}

Mutation B: remove _patched_chain_preset_steps from case_runners.py re-export block
Result: import smoke RC=1; AssertionError missing _patched_chain_preset_steps
```

Narrow conclusion: the moved negative-probe scaffold path and re-export seam are
live, not dead code.

## Narrowly proven

- Official `brick build --graph` route reached `frontier_kind=complete`.
- Both QA lanes returned no Link-facing `transition_concern_evidence`.
- The five moved symbol bodies are byte-identical in a flat support checker-lib sibling.
- The new module registry row owns no axis crossing and imports no axis.
- REAL HOME `check_profile.py --all` is green after landing.
- Mutation-RED proves the scaffold and import seam are load-bearing.

## Not proven / caveats

- This is the fifth god-module leaf, not full FINAL architecture completion.
- `case_runners.py` remains large at 10158 LOC; `kernel_checks.py`, `walker_kernel.py`, `run.py`, and giant profiles remain future conservation-ledger-first work.
- Provider reliability, future Building correctness, source truth, success judgment, quality judgment, and Movement authority remain outside this proof.

## Next target candidate

Continue FINAL architecture cleanup with another conservation-ledger-first leaf,
or push main and rerun P7 fresh-clone against current origin once Smith explicitly OKs external publication.
