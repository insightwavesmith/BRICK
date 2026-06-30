# BRICK 6 P3 return-shape / Link carry closure evidence - 2026-07-01

## Scope

- Phase: P3 - Brick return-shape truth and Link carry filtering.
- Repo: `/Users/smith/projects/BRICK`.
- Base before Building: `6c73411`.
- Declaration commit: `8ff588f` (`P3: declare return-shape carry repair graph`).
- Adopted sandbox commit: `51becfa` (`BRICK building output: brick-6-p3-return-shape-link-carry-0701a`).
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p3-return-shape-link-carry-0701a`.
- Build route: official `brick build` / `support/operator/cli.py build --graph` declared graph.

## Graph shape

The graph intentionally did not use a preset-only route because P3 needed a non-preset multi-adapter design fan-out/fan-in shape:

```text
intake-split
  -> fan([design-codex, design-claude])
  -> design-synthesis
  -> design-qa
  -> work
  -> fan([code-qa, axis-qa, evidence-qa])
  -> closure
  -> boundary
```

Materialized adapters observed in `/tmp/brick_p3_return_shape_0701a.json`:

- Codex: intake-split, design-codex, design-synthesis, work, code-qa, closure.
- Claude: design-claude, evidence-qa.
- Gemini: design-qa, axis-qa.

The earlier all-Codex behavior was not a runner default; it came from prior graph declarations selecting `adapter:codex-local` on every node.

## Observed evidence

- Build result: `frontier_kind=complete`, `customer_visible_frontier_state=frontier_complete`.
- Build result commit: `e00834a2fb7a81724aa4e9c6692fd011909e8d34`, adopted to main as `51becfa`.
- Changed files are limited to P3 scope:
  - `support/operator/assembly.py`
  - `support/operator/driver.py`
  - `support/checkers/check_assembly_equivalence.py`
  - `support/checkers/check_building_operator_driver0.py`
  - `support/checkers/lib/preset_completion_fixture.py`
- Declared plan evidence shows fan-in source Brick rows now preserve full template return shape:
  - `code-qa.required_return_shape` includes `transition_concern_evidence`.
  - `axis-qa.required_return_shape` includes `transition_concern_evidence`.
  - `evidence-qa.required_return_shape` remains the full `evidence-integrity/return.yaml` shape.
- Declared plan evidence also shows Link carry filtering remains separate:
  - `code-qa.carries_forward_fields = attacked_work,failing_or_missing_probes,regression_risks,boundary_violations`.
  - `axis-qa.carries_forward_fields = attacked_scope,brick_axis_findings,agent_axis_findings,link_axis_findings,support_leak_findings,projection_authority_findings`.
  - `evidence-qa.carries_forward_fields = persisted_evidence_roots,proof_limit_findings,stale_source_risks,missing_evidence,checker_overclaim_risks`.
- `fan_in_source_transition_concern_adoption` is present as scoped advisory source-lane policy; top-level `transition_concern_adoption=advisory` was not used.

## Verification commands

Run against a detached verification worktree at sandbox commit `e00834a` before adoption:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m py_compile support/operator/assembly.py support/operator/driver.py support/checkers/check_building_operator_driver0.py support/checkers/check_assembly_equivalence.py support/checkers/lib/preset_completion_fixture.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/assembly_equivalence.yaml
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/building_operator_driver0.yaml
git diff --check HEAD~1..HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed result: all commands exited 0. The full profile ended with profile passes including `read-side-projection-boundary`, `core`, `assembly-equivalence`, `building-operator-driver0`, and other registered profiles.

## Narrowly proven

- The old P3 shrink path where fan-in source Brick return shape could become `observed_evidence, not_proven` is now covered by RED probes.
- The easy assembly/fan path no longer strips `transition_concern_evidence` from fan-in source Brick return shape.
- Customer/operator graph packet `required_return_shape` injection is rejected unless the fan-in source value is template-equivalent.
- Link carry filtering is represented through `carries_forward_fields` and scoped fan-in source advisory policy, not by shrinking the Brick return contract.
- Focused P3 profiles and `check_profile.py --all` passed on the adopted sandbox commit in a clean detached verification worktree.

## Not proven / proof limits

- This does not prove P4-P8, fresh-machine customer install, real-provider repeated reliability, release/dashboard/CI hardening, or final customer-ready closeout.
- Checker/profile green is support evidence only; it is not source truth, success judgment, quality judgment, or Movement authority.
- Closure returned a non-reroute `verification_gap` concern before the separate detached verification closed the `check_profile.py --all` and `building_operator_driver0` evidence gaps. The closure concern remains useful evidence of what was missing at closure time.
- Semantic completeness for every future custom graph authoring pattern remains not proven.

## Next Movement candidate

Proceed to P4: AgentFact top-level forbidden keys before persistence, unless Smith/COO asks for a P3 replay focused only on live carry projection evidence.
