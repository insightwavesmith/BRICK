# Checker profile diet B2a copy-stage record (0625)

Status: support evidence / implementation record. Not source truth, not success
judgment, not quality judgment, and not Movement authority.

## Scope

B2a is a safe staging slice of the checker/profile diet work. It creates three
concern-coherent profile copies from the existing
`building_skill_preset_agent_tool_hardening.yaml` profile and registers them in
`core.yaml` path_allowlist. It intentionally does not thin or delete the
original profile; that remains for B2b after assertion-conservation review.

## Changed files

```text
support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml
support/checkers/profiles/building_skill_preset_builder_composition.yaml
support/checkers/profiles/building_skill_preset_intake_adapter_gate.yaml
support/checkers/profiles/core.yaml
```

## Building evidence

```text
project/brick-protocol/buildings/checker-profile-diet-b2a-copy-stage-0625
```

The Building work step returned and wrote the profile changes. The QA step
stalled in the Claude adapter after the work return and was interrupted by the
COO by building/session ownership, not raw PID force-kill. Therefore the
Building evidence is partial and does not itself close QA/closure.

## Direct verification after QA stall

Commands run from `struct-surgery-0623`:

```bash
git diff --check
uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_resource_boundary
uv run python3 support/checkers/check_profile.py --profile building_skill_preset_builder_composition
uv run python3 support/checkers/check_profile.py --profile building_skill_preset_intake_adapter_gate
uv run python3 support/checkers/check_profile.py --profile core
uv run python3 support/checkers/check_profile.py --self-test
```

Observed results:

```text
git diff --check: clean
building_skill_preset_agent_resource_boundary: passed
building_skill_preset_builder_composition: passed
building_skill_preset_intake_adapter_gate: passed
core: passed
self-test: passed
```

## Narrowly proven

```text
- The three new staged profile files are syntactically admitted checker-profile/v1 files.
- Their targeted profile runs pass in this checkout.
- core.yaml path_allowlist includes the new files and core profile passes.
- checker profile self-test still passes duplicate-key and registry-closure checks.
```

## not_proven

```text
- B2b thinning/deleting of the original hardening profile is not done.
- Assertion-conservation across original + staged copies is not fully proven by
  mutation-RED; no mutation probe was committed.
- Full --all is not run in this slice.
- The official B2a Building did not complete QA/closure because the QA adapter
  stalled; direct checks above are support evidence only.
- Source truth, success, quality, Movement authority, and complete checker
  consolidation remain not proven.
```

## Next proposed work boundary

```text
B2b: thin the original building_skill_preset_agent_tool_hardening.yaml only
after line-level assertion-conservation inventory proves every original pin and
case section is present in exactly one staged sub-profile or intentionally left
in the original shell.
```
