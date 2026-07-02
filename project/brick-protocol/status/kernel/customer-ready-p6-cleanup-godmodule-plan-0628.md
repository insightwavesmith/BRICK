# Customer-Ready P6 Cleanup / Godmodule Plan - 0628

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, Movement
authority, or deletion authority. It records the P6 operator plan after three
read-only subagent measurements, two-agent attack review, and Codex operator
reconciliation. Subagent output is support evidence only.

## Phase

P6 - engine cleanup / godmodule decomposition.

## Operator Read

P6 starts only after the customer path is alive enough that cleanup will not
hide product failures. The cleanup target is structural drag, not protocol
meaning.

Do not split `_run_dynamic_graph_walker` until P4 resume preservation is proven
with focused checker evidence and full regression acceptance.

## Current Measurement

Measured live checkout at current dirty `b8b1108` working tree:

```text
support/checkers/lib/kernel_checks.py        11460 LOC
support/checkers/lib/case_runners.py        10238 LOC
support/operator/walker_kernel.py            2178 LOC
support/operator/run.py                      2240 LOC
support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
                                              4163 LOC
support/checkers/module_registry.yaml        1892 LOC
```

Registry/census measurement:

```text
support/operator/*.py excluding __init__: 61 files, 61 registry rows
support/checkers/lib/*.py: 4 files, 4 registry rows
module_registry.yaml: 146 module rows
profile count: 28 live profiles
```

Existing research:

```text
project/brick-protocol/status/kernel/archive/0702-doc-archive/research-0626/godmodule-decision-merged-0626.md
project/brick-protocol/status/kernel/archive/0702-doc-archive/research-0626/godmodule-decomposition-decision-table-0626.md
project/brick-protocol/status/kernel/checker-profile-diet-*.md
```

Staleness:

```text
Old godmodule docs cite stale LOC and line coordinates for kernel_checks and
walker_kernel.
walker_kernel first split has already landed.
case_runners remains monolithic.
kernel_checks remains monolithic and has a changed dispatch surface.
checker-diet still has 97-label conservation risk; current split copies cover
only 12 labels.
profile text_contains pins still point at private helpers/probe text inside
kernel_checks.py; public run_* facade conservation is not enough for a split.
```

## Attack Review Delta

Two independent attack reviews agreed P6 is a HOLD for implementation and a
FORWARD only for read-only re-derivation/conservation ledger work:

```text
- old kernel_checks coordinates are non-authoritative after current dirty edits
  and new gemini_local_only_adapter dispatch surface
- checker-diet deletion cannot rely on path_allowlist; that rule rejects
  unexpected observed files, not missing allowlisted files
- every moved label and every moved non-label assertion needs mutation-RED or an
  admitted retirement reason
- new checker-lib modules must be flat support/checkers/lib/*.py siblings unless
  a separate path admission change is made
- profile text pins, private helper imports, module_registry rows, forbidden
  ownership echoes, and dirty diffs must all be in the conservation ledger
```

## Three-Axis Attribution

Brick:

```text
P6 changes support/checker structure. It must not change Brick work contracts,
Brick return shapes, presets, or Building meaning except through separately
declared work.
```

Agent:

```text
P6 must not change Agent identity, tool authority, adapter meaning, or returned
fact semantics while moving checker/support code.
```

Link:

```text
P6 must preserve Movement literals, gate sufficiency, carry, frontier, reroute,
and transition lifecycle semantics.
```

Support:

```text
module split, checker diet, registry rows, imports, profile labels, and negative
probes are support mechanics. Support must not become source truth.
```

## Implementation Order

1. Baseline and conservation ledger.

```text
Freeze current dirty/clean baseline.
Generate machine-readable inventories:
- module registry rows
- check_profile KERNEL_DISPATCH keys
- RULE_RUNNERS keys
- all profile labels
- all non-label assertions: path/text/json/proof_limits/not_proven blocks
- profile text_contains pins and private helper/probe text pins
- proof_limits / not_proven blocks
- private helper imports
- profile path allowlist
- planned mutation-RED per moved label/assertion
```

2. Checker-diet guard.

```text
Keep building_skill_preset_agent_tool_hardening.yaml until all 97 labels and
non-label assertions are either moved exactly once or explicitly retired with
reason.
Current split copies preserve only 12 labels; deletion is HOLD.
Use yaml_subset loader, not PyYAML, for inventory.
Do not rely on path_allowlist as a deletion oracle; it does not prove missing
allowlisted files are unsafe.
Require mutation-RED per moved label/assertion before thinning or deletion.
```

3. case_runners split first.

```text
Re-derive current coordinates.
Extract shared helper leaf first:
_graph_test_plan_from_linear
_preset_completion_command_runner
other cross-imported fixture/common helpers

Then move behavior clusters by symbol, not line range.
Keep RULE_RUNNERS keyset byte-stable.
Choose facade vs direct importer update as an explicit sub-decision before edit.
New checker-lib modules must be flat support/checkers/lib/*.py siblings unless
a separate MAG/path-admission change is explicitly admitted.
```

4. kernel_checks reinvestigation.

```text
Do not act from 0626 line spans.
Re-derive current run_* domains and current KERNEL_DISPATCH.
Relocate self-allowlists only with the enum/literal checks they pin.
Each new lib module needs module_registry row and forbidden ownership echo.
Inventory and rehome profile text pins and private helper/probe body pins; a
public run_* re-export facade is not sufficient conservation by itself.
```

5. walker surfaces.

```text
Treat existing walker leaf split as landed support evidence.
Do not split _run_dynamic_graph_walker now.
Any future walker split needs P4 focused proof plus a WalkerState-gated plan.
```

6. Verification ladder.

```text
check_profile.py --self-test
label-ledger equivalence
non-label assertion ledger equivalence
profile text pin ledger equivalence
mutation-RED per moved label/assertion
targeted split profiles
original hardening profile
focused P4 resume profile if walker surfaces touched
python3 -m compileall -q support/operator support/checkers
git diff --check
check_profile.py --all
```

## Exit Criteria

P6 may move forward only when:

```text
module_registry rows match new files
new checker-lib files obey admitted flat path shape or carry a separate path
admission change
forbidden ownership echoes remain present
KERNEL_DISPATCH and RULE_RUNNERS semantics are conserved
profile labels, non-label assertions, text pins, and private helper imports are
conserved or explicitly retired
mutation-RED probes cover moved labels/assertions
negative probes still fire
check_profile.py --all is green in the target checkout
no Brick/Agent/Link meaning changed
```

## Movement

Recommendation:

```text
FORWARD only to read-only re-derivation / conservation-ledger work, then a
narrow implementation Building for the chosen target.
HOLD on deletion, broad cleanup, kernel_checks split, or _run_dynamic_graph_walker
split until their conservation gates are proven.
```

## Not Proven

```text
safe deletion of checker profiles
byte-identical relocation
dirty checker diffs conservation
kernel_checks current split map
profile text pin conservation
mutation-RED per moved label/assertion
full check_profile.py --all after current dirty edits
future support-authority leak absence
```
