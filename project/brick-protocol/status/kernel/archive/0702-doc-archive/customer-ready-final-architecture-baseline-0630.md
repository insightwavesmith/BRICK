# Customer-Ready FINAL Architecture Baseline — 0630

Status: support evidence only. Not source truth / success / quality / Movement authority.

## Why this exists

The active goal requires FINAL architecture cleanup after P8 and release pruning:
Brick/Agent/Link boundary re-measurement plus godmodule decomposition under
conservation ledger + mutation-RED + byte-identical + net-negative LOC.

Before any source split, the stale P6 coordinates had to be re-derived from the
current checkout.

## Building run

Read-only baseline Building:

- building id: `final-architecture-baseline-20260629T185325Z`
- route: official `brick build --graph`
- shape: Codex inspect -> Codex code-attack QA + Gemini axis QA -> Codex closure
- frontier: `link_paused`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/final-architecture-baseline-20260629T185325Z`

The pause is valid: closure raised a non-binding `upstream_gap` because inspect
and code QA disagreed on a `module_registry` decomposition-count metric. This
blocked implementation and forced a corrected baseline measurement.

## Corrected live measurements

Measured after the paused Building, directly against the live checkout:

```text
support/checkers/lib/kernel_checks.py        11432 LOC
support/checkers/lib/case_runners.py        10907 LOC
support/operator/walker_kernel.py            2306 LOC
support/operator/run.py                      2240 LOC
support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
                                              4221 LOC
support/checkers/module_registry.yaml        1892 LOC

support/operator/*.py excluding __init__        61 files
support/checkers/lib/*.py                        4 files
support/checkers/profiles/*.yaml                28 profiles
module_registry module rows                    146 rows
check_profile.KERNEL_DISPATCH                   63 keys
check_profile.RULE_RUNNERS                      50 keys
```

Corrected decomposition metric:

```text
module_registry non-empty decomposition_target rows = 2
module_registry decomposition_ceilings table rows   = 2
literal text hits of "decomposition"               = 154 (comments + empty rows included)
```

Therefore the inspect Agent's "10 decomposition ceiling rows" was a metric-definition
error. Code QA's count of 2 non-empty decomposition targets / 2 ceiling rows is the
correct implementation-relevant metric.

## Current architectural conclusion

Implementation is still HOLD. The first safe work is not a broad split; it is a
conservation-ledger design for a narrow `case_runners.py` helper leaf extraction.

Candidate first split (not yet implemented):

```text
support/checkers/lib/case_runners.py
  -> extract one flat sibling helper module under support/checkers/lib/*.py
  -> preserve RULE_RUNNERS keyset and profile behavior byte-identically
  -> add module_registry row and forbidden-ownership echo
  -> mutation-RED per moved label/assertion before thinning/deletion
```

Do NOT start with:

```text
kernel_checks split
walker/run split
profile thinning/deletion
broad checker diet
new module family/folder hierarchy
```

## Proof required before implementation can move

A design/conservation-ledger Building must name, before code mutation:

- exact helper symbols to move from `case_runners.py`
- affected `RULE_RUNNERS` labels
- profile path/text/json pins that reference moved bodies
- private helper/probe text pins
- module_registry row(s)
- mutation-RED probe(s) for each moved label/assertion
- expected byte-identical behavior and net-negative LOC claim

Then a bounded work Building may implement one flat helper extraction, followed by:

```text
git diff --check
compileall relevant support/checkers files
targeted affected profiles
check_profile.py --self-test
check_profile.py --all (REAL HOME)
mutation-RED probes for moved labels/assertions
```

## Not proven

- safe source split
- byte-identical moved behavior
- mutation-RED coverage
- net-negative LOC
- safe deletion/thinning of any existing profile/module
- FINAL architecture cleanup completion
