# P9-B1 six-family checker/profile + module-map reference record (0625)

Status: support evidence / status record only. This record is not source truth,
success judgment, quality judgment, or Movement authority.

Checkout: `struct-surgery-0623` @ `4c1958a` when measured.
Primary reference doc: `support/docs/references/checker-profile-map.md`.
Prior evidence carried forward: `project/brick-protocol/buildings/p9-checker-module-diet-followup-0625`.

## User-request coverage

| Requested item | Handling in this slice | Evidence surface |
| --- | --- | --- |
| 1. six-family checker/profile map complete | Mapped the 24 on-disk profile ids into six candidate families and separated profile ids from hosted kernel checks. | `support/docs/references/checker-profile-map.md` sections 0-2 |
| 2. module cleanup targets identified | Recorded module-family map and concrete review candidates: composition siblings, walker siblings, adapter siblings / `agent_adapter.py` facade. | reference doc section 3 |
| 3. god module / duplicate support family / stale surface / dead surface found | Corrected god-module claim, recorded duplicated baseline checks, stale fixture/example `brick/building_plans/`, and dead-check risk if fixture twins are deleted first. | reference doc sections 2-4, 7 |
| 4. delete/merge-now vs admission/checker-first separated | Split low-risk exact duplicate/phase-name cleanup from surfaces requiring admission/checker-first. | reference doc section 4 |
| 5. follow-on Buildings 3-6 with write scopes | Proposed B1-B5 sequence and chokepoint serialization rules. | reference doc sections 5-6 |

## Reproducible live measurements

```text
profiles on disk (support/checkers/profiles/*.yaml) = 24
presets (brick/templates/presets/*.md)              = 28
distinct kernel_checks referenced by profiles       = 54
module rows in support/checkers/module_registry.yaml = 140
rows carrying a live decomposition_target ceiling    = 2
legacy plans in brick/building_plans/                = 4
```

## Corrections made against prior candidate evidence

```text
- The prior "four god-modules DONE" phrasing was not reproducible here.
  Live registry ceiling rows are only check-profile-god-0 and rs-sink-ceiling-0.
- reporter_notification_projection is not a standalone profile; it is hosted in
  read_side_projection_boundary.yaml.
- brick/building_plans/ has 4 fixture/example files, not approximately 16 plans.
- Current counts are 24 profiles and 28 presets.
```

## Commands run for this slice

```bash
git rev-parse --short HEAD
git status --porcelain=v1
ls -1 support/checkers/profiles/*.yaml | wc -l
ls -1 brick/templates/presets/*.md | wc -l
find brick/building_plans -type f | wc -l
grep -nE "decomposition_target:" support/checkers/module_registry.yaml
grep -rln "reporter_notification_projection" support/checkers/profiles/
git diff --check
uv run python3 support/checkers/check_profile.py --profile structure_template_integrity
uv run python3 support/checkers/check_profile.py --profile read_side_projection_boundary
```

Observed outcomes:

```text
git diff --check: clean
structure_template_integrity: passed
read_side_projection_boundary: passed
```

## Narrowly proven

```text
- The reference doc exists and covers the five requested analysis buckets.
- The doc uses current on-disk counts for profiles, presets, module-registry rows,
  decomposition-target ceiling rows, and building_plans fixtures.
- The doc addition did not disturb the two targeted checker profiles above.
```

## not_proven

```text
- The six-family grouping is not an admitted taxonomy; it is candidate support evidence.
- The proposed B2-B5 follow-on Buildings are not executed here.
- No module, checker, or profile cleanup implementation is performed here.
- Targeted checker green does not prove source truth, success, quality, Movement
  authority, provider behavior, or complete checker consolidation.
```

## Next Movement candidate

```text
forward to commit this B1 reference/status slice, then choose either:
- P11 customer-entry/readiness reconciliation (disjoint docs/status scope), or
- P9 B2 profile split design/implementation (serialized because core.yaml is a chokepoint).
```
