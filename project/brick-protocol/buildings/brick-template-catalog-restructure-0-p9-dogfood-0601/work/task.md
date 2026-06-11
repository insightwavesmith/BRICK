# BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0 P8 Checker / FIRE Closure

Date: 2026-06-01

Status: P8 support-checker closure record. This record does not choose a
template, Building shape, chain preset, Movement, target, Agent identity,
success, quality, source truth, or P10 old-registry deletion.

## RED-First Observation

The direct P8 checker command initially failed:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_brick_template_catalog_restructure.py --repo . --mode p8-active
```

Observed failure shape:

```text
old registry.yaml step_templates were treated as active binding rows
split step-template rows under step_template_catalog.rows were not read
brick/templates/shapes/*.yaml catalog files were treated as physical templates
```

That RED observation was a support-checker bug, not a Brick catalog mutation
need.

Independent Codex subagent attack review later found two P8 proof-boundary gaps:

```text
old registry fallback was not explicitly FIRE-probed when split rows are absent
P7 declaration-packet validation was fixture-proven but not live-proven before P9
```

The checker was tightened after that review.

## P8 Checker Closure

Changed:

```text
support/checkers/check_brick_template_catalog_restructure.py
support/checkers/check_profile.py
support/checkers/profiles/brick_template_catalog_restructure.yaml
```

The checker now treats the split catalog as the P8 active source:

```text
brick/templates/shapes/catalog.yaml
brick/templates/shapes/shapes.yaml
brick/templates/shapes/step-templates.yaml
brick/templates/shapes/chain-presets.yaml
brick/templates/shapes/chain-presets-brick-protocol.yaml
```

`brick/templates/shapes/registry.yaml` remains present and compatibility-only
until P10. P8 does not delete it and does not use it as the active physical
binding source.

P8 active step rows are read from:

```text
step_template_catalog.rows
```

If split `step_template_catalog.rows` is absent, P8 rejects instead of falling
back to the old `registry.yaml` rows. The old registry remains compatibility
evidence only until P10.

Physical template discovery is limited to admitted physical work-template
locations and suffixes:

```text
brick/templates/design/*.yaml|*.json
brick/templates/do/*.yaml|*.json
brick/templates/review/*.yaml|*.json
brick/templates/closure/*.yaml|*.json
brick/templates/tasks/*.md
```

Shape catalog documents under `brick/templates/shapes/*.yaml` are not physical
work templates.

## Added Guards

P8 FIRE now includes guards for:

```text
common_dogfood_preset_overlap
dogfood_alias_conflict
dogfood_common_basis_missing
missing_active_split_step_template_rows
declaration_expanded_brick_template_ref_not_physical
```

The direct P8 command now reports:

```text
16 FIRE fixture(s) rejected
p7-marked declaration packets inspected: 0
```

Live validation now checks:

```text
common and Brick Protocol dogfood preset refs are disjoint
dogfood compat aliases do not collide with active preset refs
dogfood common_basis_ref points at a real common preset
P7-marked declaration packets with split-catalog binding fields keep
  expanded_brick_template_refs as physical Brick template paths only
```

This check is live for packets that already contain the P7 binding fields.
Before the P9 dogfood run, the current repository may contain zero live
P7-marked Building packets; historical unmarked packets are not retroactively
rewritten by P8.

## Narrowly Proven

```text
p8-active checker mode reads split step_template_catalog.rows.
p8-active rejects missing split step_template_catalog.rows instead of accepting
old registry fallback rows.
registry.yaml is not treated as the active binding source in P8.
shape catalog YAML files are not treated as physical work templates.
The brick-template-catalog-restructure profile invokes p8-active mode.
Synthetic RED-first FIRE fixtures cover the P8 checker problem codes.
```

## Not Proven

```text
semantic fitness of any physical Brick template
future Building run correctness
P10 safe deletion of brick/templates/shapes/registry.yaml
live persisted P7-marked declaration-packet coverage before P9 dogfood
complete historical old-registry reference classification
provider behavior or provider reliability
```

## Carry Forward

```text
P9 should carry this as checker support evidence only.
P10 still owns any human-gated registry.yaml deletion decision.
Future exporter work should continue treating common chain presets as the
shareable surface and Brick Protocol dogfood presets as local variants.
```

## Review / Model Evidence

```text
Claude Opus 4.8 xhigh final review:
  session_id: <redacted-session-id>
  verdict: APPROVE
  blockers: none
  carry_forward:
    P9 must produce and re-check a live P7-marked declaration packet.
    P10 still owns human-gated registry.yaml deletion safety.

The delegated review is support evidence only. Local RED-first observation,
checker FIRE fixtures, profile execution, compileall, and diff-check are also
support evidence only.
```

## Next Movement Recommendation

```text
forward to P9 proof-limit closure, carrying P10 registry deletion safety as
not_proven.
```
