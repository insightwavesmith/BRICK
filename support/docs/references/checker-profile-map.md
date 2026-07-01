# Checker / profile six-family map + module-family map (verified reference)

Status: support evidence / reference doc only. This file is NOT source truth,
success judgment, quality judgment, or Movement authority. It records the
verified six-family taxonomy for the on-disk checker profiles plus the
support module-family map, so future authors do not re-fold profiles or
re-bloat modules. The profile count is a measured checkout fact, not a
constitutional constant. It admits no taxonomy and changes no checker, profile, or
module code.

Lane: struct-surgery-0623 worktree @ HEAD 4c1958a.
Origin: lands the P9 follow-up HOLD deliverable
(p9-checker-module-diet-followup-0625), correcting facts that prior candidate
evidence carried but could not reproduce (see "Corrections" below).

## 0. Reproducible measurement (this checkout)

```text
profiles on disk (support/checkers/profiles/*.yaml) = measure with `find support/checkers/profiles -maxdepth 1 -name '*.yaml' | wc -l` (30 observed on 2026-07-01)
presets (brick/templates/presets/*.md)              = measure with `find brick/templates/presets -maxdepth 1 -name '*.md' | wc -l` (28 observed on 2026-07-01)
distinct kernel_checks referenced by profiles       = measure from the profile YAMLs (66 observed on 2026-07-01)
module rows in support/checkers/module_registry.yaml = 162
rows carrying a live decomposition_target ceiling    = 2
legacy plans in brick/building_plans/                = 4 (NOT ~16)
```

Profile -> kernel_checks count (verbatim from kernel_checks: blocks):

```text
core                                            23
read_side_projection_boundary                   14
agent_axis_behavioral                           11
structure_template_integrity                     6
building_automation                              5
coo_operating_chain                              4
link_routing_behavioral                          4
bounded_agent_proposed_routing_loop              3   (checks: package_path_admission,
                                                        bounded_agent_proposed_routing_loop,
                                                        recording_checker_derived_contract --
                                                        NOT only package_path_admission)
building_skill_preset_agent_resource_boundary    3
building_skill_preset_agent_tool_hardening       3
building_skill_preset_intake_adapter_gate        3
native_dispatch_brick_backstop                   3
brick_cli_entrypoint                             2
building_operator_driver0                        2
building_skill_preset_builder_composition        2
adapter_usage_meter                              1
agent_object_schema_single_source                1
assembly_equivalence                             1
chained_carry_dependency                         1
charter_injection                                1
cli_runner_stdin_devnull                         1
driver_public_intake_seal                        1
gate_registry_single_source                      1
graph_topology_fan_barrier                       1
mcp_dispatch_wire                                1
raw_evidence_stream_scrub                        1
report_env_autoload                              1
return_field_merge_set_parity                    1
step_output_evidence_field_set_parity            1
tier_a_three_axis_conformance                    1
```

## 1. Six-family checker/profile map

Family membership is keyed by what the profile's checks PROTECT, not by file
name. A profile may carry checks of more than one family (that overlap is
itself a diet finding; see section 2). Each entry is a real on-disk profile id.

### F1 admission (does the declared thing exist / resolve?)

```text
core (partial: package_path_admission, declared_verifier_exists,
      agent_resource_resolution, catalog_reader_sync, project_declaration,
      building_declaration_integrity, building_root_anchor)
brick_cli_entrypoint        (brick_cli_entrypoint_smoke, first_use_wizard)
driver_public_intake_seal
charter_injection
```

### F2 boundary / single-source (axis purity, no support judgment, no drift)

```text
core (partial: axis_vocab_drift, axis_contract_projection,
      axis_field_enum_parity, axis_field_set_single_source,
      agentfact_single_home, builder_consumes_axis_api,
      support_no_axis_judgment, axis_crossing_elegance,
      link_gate_measurement_separation)
agent_object_schema_single_source
gate_registry_single_source
return_field_merge_set_parity
assembly_equivalence
```

### F3 deterministic fixture behavioral (graph/lifecycle/route over fixtures)

```text
core (partial: bricks_spec_completeness, building_lifecycle_path_shape,
      building_map_graph, building_plans_boundary_sweep,
      fan_out_sibling_evidence_independence, evidence_spine,
      evidence_spine_projection)
structure_template_integrity   (brick_template_catalog_restructure + graph pins)
building_automation            (chat_session_park_seam,
                                adapter_error_frontier_manifest_consistency,
                                adapter_error_path_hardening)
bounded_agent_proposed_routing_loop
link_routing_behavioral
chained_carry_dependency
native_dispatch_brick_backstop
```

### F4 runtime smoke (deterministic/mocked; no live credentials)

```text
agent_axis_behavioral          (provider_preflight + graph pins)
cli_runner_stdin_devnull
mcp_dispatch_wire
report_env_autoload
adapter_usage_meter
building_operator_driver0      (onboard_smoke)
```

### F5 customer / tier-A conformance proof

```text
tier_a_three_axis_conformance
building_operator_driver0      (driver intake)
coo_operating_chain
```

### F6 reporter / dashboard / product projection (read-side, never judge)

```text
read_side_projection_boundary  (HOSTS reporter_notification_projection,
                                dashboard_productization_projection,
                                codex_projection_native, claude_projection_native,
                                install_script_lint, release_export_exclusion,
                                product_no_smith_residue, connect_config_launch,
                                mcp_stdio_smoke)
coo_operating_chain            (closure read projection)
report_env_autoload            (sink env, also F4)
```

## 2. Overlap finding (the real diet target)

Four kernel checks are duplicated across many profiles. This is the largest
concrete diet signal -- not god-modules.

```text
package_path_admission        in 12 profiles
axis_contract_projection      in 10 profiles
building_lifecycle_path_shape in 9 profiles
building_map_graph            in 8 profiles
```
(re-measured 2026-07-01: `package_path_admission` and `axis_contract_projection`
moved up from the prior 9/7 counts as newer profiles adopted the baseline
preamble; `building_lifecycle_path_shape` moved 8 -> 9; `building_map_graph`
is unchanged at 8.)

These four are effectively a shared "every behavioral profile re-asserts the
admission + graph baseline" preamble. A diet move (deferred, needs admission)
is to factor them into one shared baseline the behavioral profiles import,
rather than restating the list per profile. NOT done here -- recorded only.

## 3. Module-family map (support/operator, one folder)

Grounded in support/docs/references/architecture-map.md +
support/checkers/module_registry.yaml. Five declared families:

```text
builder   materialize a declared plan:
          plan_rendering / composition* / plan_graph / route_materialization
engine    walk the declared plan, record evidence:
          run / dynamic_walker / walker_* / gate_sequence / native_dispatch
operator  entry points + read observation:
          driver / onboard / building_operation / coo_operating_chain /
          frontier_observation / evidence_status / dashboard_export
read-side observe + project written evidence, never judge:
          ledger_projection / progress_projection / dashboard_export /
          report_sinks / reporter
vessel    project vessel declaration + creation verb:
          project_declaration / project_creation
```

The authoritative module census stays support/checkers/module_registry.yaml
(162 module rows). This map is shared vocabulary only.

### 3a. God-module status -- CORRECTED

The registry's own ownership measure shows NO live god-module remaining. Only
two rows carry a decomposition_target ceiling:

```text
check-profile-god-0   ceiling 0  (historical; thin checker facade,
                                  owns_crossings shrank 11 -> 0, self-consistency only)
rs-sink-ceiling-0     ceiling 1  (report_sinks.py: live 4-sink dispatch seam;
                                  a 5th sink requires report_bus split first)
```

The earlier candidate claim of "four god-modules already DONE
(building_operation/evidence_assembly/dynamic_walker/check_profile)" is NOT
reproducible from this checkout: only check-profile-god-0 survives as a
(historical) decomposition_target row; the other three carry no ceiling row at
all. So the cleanup angle is facade/family hygiene, not god-module splitting.

### 3b. Oversized / sibling families (review candidates, NOT auto-delete)

```text
support/operator/composition_*.py   = 9 modules
support/operator/walker_*.py        = 9 modules
support/connection/adapter_*.py     = 7 sibling modules behind a
                                      ~1230-line agent_adapter.py facade
```

Each was a deliberate decomposition. Any re-merge must be justified against the
G2 (owns<=1) elegance target, not raw line/file count.

### 3c. Stale / legacy surfaces -- CORRECTED

```text
brick/building_plans/ holds 4 files, all fixture/example, NOT ~16 legacy plans:
  fixture-link-concern-replay-0.yaml
  fixture-link-route-replay-0.yaml
  fixture-retired-adapter-plan-0.yaml
  onboarding-example-0.yaml
```

These are load-bearing as checker fixtures (core: building_plans_boundary_sweep,
plan-boundary pins). Deletion requires fixture twins first. The "~16 legacy
hand-declared plans" figure from prior candidate evidence does not match this
tree (the bulk was already retired).

## 4. delete/merge-NOW vs needs-admission/checker-FIRST

```text
delete/merge-NOW (low risk, only if still present on canonical tree):
  - exact-duplicate path_exists pins across profiles
  - phase-name-only renames already executed

needs-admission / checker-FIRST (deleting first yields a silent green = dead check):
  - anything pinned by strict plan-boundary over brick/building_plans/
  - the 4-way duplicated baseline checks (section 2) -> need a shared-baseline
    admission before removing per-profile restatements
  - report_sinks.py sink set (rs-sink-ceiling-0) -> report_bus split first
  - composition_* / walker_* / adapter_* re-merges -> G2 elegance admission first
```

## 5. Write-scope chokepoints (force serialization of follow-on Buildings)

```text
support/checkers/profiles/core.yaml          shared by every profile add/move/split
support/checkers/module_registry.yaml        shared by every module add/delete/rename
support/checkers/lib/case_runners.py         multi-profile-pinned checker lib
support/checkers/lib/kernel_checks.py         multi-profile-pinned checker lib
support/checkers/lib/rule_runners.py         multi-profile-pinned checker lib
```

Any two Buildings touching the same chokepoint must serialize.

## 6. Proposed follow-on Buildings (3-6, sequenceable) -- proposals only

```text
B1  THIS doc (reference map)                          parallel-safe, lands first
B2  split building_skill_preset_agent_tool_hardening  touches core.yaml -> seq before B3
B3  re-separate deterministic provider runtime-smoke  touches core.yaml -> seq after B2
B4  module-cleanup admission gate (fixture twins)     must precede B5
B5  stale-surface retire + module_registry cleanup    serialize on module_registry.yaml
```

These are non-binding proposed work boundaries, not Movement, route, target,
or sufficiency. Caller/COO declares any of them as actual Buildings.

## 7. Corrections to prior candidate evidence (reproducibility log)

```text
- "four god-modules DONE"            -> only check-profile-god-0 ceiling row survives;
                                        other three carry no decomposition_target.
- reporter_notification_projection   -> NOT a standalone profile; it is a kernel
                                        check HOSTED in read_side_projection_boundary.yaml.
- "~16 legacy building_plans"        -> 4 fixture/example files only.
- profile count                      -> measured checkout fact, not a fixed doc constant; 30 observed on 2026-07-01 (this doc previously said 29; 6 profiles had been added since the last measurement, e.g. building_skill_preset_agent_resource_boundary, building_skill_preset_builder_composition, building_skill_preset_intake_adapter_gate, graph_topology_fan_barrier, raw_evidence_stream_scrub, step_output_evidence_field_set_parity).
- preset count                       -> measured checkout fact, not a fixed doc constant; 28 observed on 2026-07-01 (unchanged).
- distinct kernel_checks in profiles -> measured checkout fact; 66 observed on 2026-07-01 (this doc previously said 64; recount of section 0's table also fixed several individual profile counts that undercounted checks listed after inline `#` comments, e.g. agent_axis_behavioral 5 -> 11, bounded_agent_proposed_routing_loop 1 -> 3).
- module rows in module_registry.yaml -> measured checkout fact; 162 observed on 2026-07-01 (this doc previously said 140).
- bounded_agent_proposed_routing_loop coverage -> the live profile
  (support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml)
  declares THREE kernel_checks -- package_path_admission,
  bounded_agent_proposed_routing_loop, and recording_checker_derived_contract
  -- not only package_path_admission as this doc previously claimed.
```

## 8. not_proven

```text
- Semantic fitness of the six-family grouping (it is a candidate taxonomy
  recorded as support evidence; not an admitted taxonomy).
- That any proposed B2-B5 split keeps every prior assertion (needs --self-test
  per split Building).
- That delete-NOW items are still present on the canonical tree at delete time.
- Whether the 4-way duplicated baseline should be factored or left explicit
  (a deliberate-redundancy vs DRY judgment for a future admission Building).
- Coverage completeness: this maps the measured profiles' declared kernel_checks
  blocks for the referenced checkout; it does not prove the checks themselves
  are correct, exhaustive, or unchanged in future checkouts.
```
