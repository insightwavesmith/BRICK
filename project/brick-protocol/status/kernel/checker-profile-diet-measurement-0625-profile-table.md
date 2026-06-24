# Checker/Profile Diet Measurement Table (P2)

Generated at: 2026-06-25T08:16:49

## Scope

- This is a support measurement artifact for `checker-profile-diet-measurement-0625`.
- It implements the measurement Building remaining delta: complete `profile -> kernel_checks -> runner -> proof_limit` table for all current profiles plus `KERNEL_DISPATCH`.
- It is not source truth, not success judgment, not quality judgment, and not Movement authority.
- Bucket labels are **candidate** diet labels only; they are not admitted taxonomy until a later Building or Smith disposition adopts them.

## Evidence refs

- Measurement Building root: `project/brick-protocol/buildings/checker-profile-diet-measurement-0625`
- Closure step: `project/brick-protocol/buildings/checker-profile-diet-measurement-0625/work/step-outputs/checker-profile-diet-measurement-0625-closure-attempt-1/step-output.json`
- Runner facade: `support/checkers/check_profile.py`
- Profile directory: `support/checkers/profiles/`

## Summary counts

- Profile YAML count: 24
- `RULE_RUNNERS` count: 50
- `KERNEL_DISPATCH` count: 62
- Candidate profile buckets: `{"core-invariant-candidate": 10, "dogfood-candidate": 7, "historical-or-oversized-candidate": 1, "live-heavy-or-provider-candidate": 6}`
- Candidate kernel buckets: `{"core-invariant-candidate": 14, "dogfood-candidate": 7, "live-heavy-or-provider-candidate": 23, "unclassified-candidate": 18}`

## Profile table

| profile_id | file:line | candidate bucket | kernel_checks | rule runners with counts | profile proof_limits | selector refs observed |
|---|---:|---|---|---|---|---|
| `adapter-usage-meter` | `support/checkers/profiles/adapter_usage_meter.yaml:2` | core-invariant-candidate | `adapter_usage_meter` | `path_exists`:7, `text_contains`:3 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>measurement only; carries no cap | support/checkers/check_adapter_usage_meter.py<br>support/checkers/profiles/adapter_usage_meter.yaml |
| `agent-axis-behavioral` | `support/checkers/profiles/agent_axis_behavioral.yaml:2` | live-heavy-or-provider-candidate | `package_path_admission`, `axis_contract_projection`, `building_lifecycle_path_shape`, `building_map_graph`, `provider_preflight`, `agent_adapter_return_shape`, `gemini_api_adapter`, `design_ai_text_seams`, `codex_connect_stall_classification`, `agent_session_id_redaction`, `casting_node_carry` | `adapter_capability_rehome_case`:23, `adapter_model_selection_case`:5, `adapter_model_selection_rejects`:4, `hook_registry_axis_case`:4, `path_absent`:6, `path_exists`:33, `text_absent`:6, `text_contains`:41, `write_scope_default_exclude_case`:7 | support evidence only<br>capability fixtures are support checker evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>projection sync context is not app reload proof<br>machinery boundary only; live freshness authority remains separate support observation<br>selected_model_ref is model selection grammar, not model availability proof | support/checkers/profiles/agent_axis_behavioral.yaml |
| `agent-object-schema-single-source` | `support/checkers/profiles/agent_object_schema_single_source.yaml:2` | core-invariant-candidate | `agent_object_schema_single_source` | `path_exists`:6, `text_contains`:5 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/agent_object_schema_single_source.yaml |
| `assembly-equivalence` | `support/checkers/profiles/assembly_equivalence.yaml:2` | dogfood-candidate | `assembly_equivalence` | `path_exists`:3 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>assembly.py is present; assembly.py LHS equivalence is actively checked (P(assemble) == P(hand-built))<br>build()/fan() front-end equivalence is actively checked (build/fan lowered nodes/edges/groups are BYTE-IDENTICAL to the hand-built chain/fan_out/fan_in/converge tier) | support/checkers/check_assembly_equivalence.py<br>support/checkers/profiles/assembly_equivalence.yaml |
| `bounded-agent-proposed-routing-loop` | `support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml:2` | dogfood-candidate | `package_path_admission`, `bounded_agent_proposed_routing_loop`, `recording_checker_derived_contract` | `path_exists`:5, `text_absent`:4, `text_contains`:16 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml |
| `brick-cli-entrypoint` | `support/checkers/profiles/brick_cli_entrypoint.yaml:2` | live-heavy-or-provider-candidate | `brick_cli_entrypoint_smoke`, `first_use_wizard` | `path_exists`:5, `text_absent`:1, `text_contains`:4 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/profiles/brick_cli_entrypoint.yaml |
| `building-automation` | `support/checkers/profiles/building_automation.yaml:2` | dogfood-candidate | `building_lifecycle_path_shape`, `building_map_graph`, `chat_session_park_seam`, `adapter_error_frontier_manifest_consistency`, `adapter_error_path_hardening` | `path_absent`:3, `path_absent_glob`:2, `path_exists`:8, `text_absent`:1, `text_contains`:15 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | brick/building_plans/fixture-link-route-replay-0.yaml<br>support/checkers/lib/case_runners.py<br>support/checkers/profiles/building_automation.yaml<br>support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml<br>support/checkers/profiles/link_routing_behavioral.yaml |
| `building-operator-driver0` | `support/checkers/profiles/building_operator_driver0.yaml:2` | live-heavy-or-provider-candidate | `building_operator_driver0`, `onboard_smoke` | `onboard_seam_case`:1, `path_exists`:5, `step_output_drain_case`:3, `text_absent`:1, `text_contains`:4 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not real-provider proof<br>not concurrency proof | support/checkers/profiles/building_operator_driver0.yaml |
| `building-skill-preset-agent-tool-hardening` | `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:2` | historical-or-oversized-candidate | `package_path_admission`, `axis_contract_projection`, `agent_adapter_return_shape` | `adapter_gate_shape_union_case`:1, `agent_candidate_packet_case`:3, `agent_preferred_adapter_rejects`:4, `agent_resource_boundary`:8, `agent_resource_retired_ref_rejects`:4, `building_intake_seam_case`:3, `compose_building_case`:4, `compose_building_rejects`:27, `declared_step_template_plan_case`:8, `declared_step_template_plan_rejects`:8, `gate_sequence_policy_case`:1, `intake_project_vessel_case`:1, `json_required_paths`:2, `materialize_building_intent_case`:13, `materialize_building_intent_rejects`:11, `path_absent`:3, `path_exists`:29, `preset_building_completion_case`:1, `preset_ranking_packet_case`:2, `run_once_task_source_admission_case`:1, `source_fact_body_carry_case`:5, `step_output_drain_case`:3, `step_output_drain_rejects`:4, `text_absent`:2, `text_contains`:24, `wiki_carry_truncation_survival_case`:1 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml |
| `chained-carry-dependency` | `support/checkers/profiles/chained_carry_dependency.yaml:2` | core-invariant-candidate | `chained_carry_dependency` | `path_exists`:4, `text_contains`:2 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/chained_carry_dependency.yaml |
| `charter-injection` | `support/checkers/profiles/charter_injection.yaml:2` | core-invariant-candidate | `charter_injection` | `path_exists`:9, `text_contains`:5 | support evidence only<br>charter injection is a soft work-packet seam, not enforcement<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/module_registry.yaml<br>support/checkers/profiles/charter_injection.yaml |
| `cli-runner-stdin-devnull` | `support/checkers/profiles/cli_runner_stdin_devnull.yaml:2` | core-invariant-candidate | `cli_runner_stdin_devnull` | `path_exists`:3, `text_contains`:2 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/cli_runner_stdin_devnull.yaml |
| `coo-operating-chain` | `support/checkers/profiles/coo_operating_chain.yaml:2` | dogfood-candidate | `package_path_admission`, `axis_contract_projection`, `building_lifecycle_path_shape`, `building_map_graph` | `path_absent`:2, `path_exists`:26, `text_absent`:6, `text_contains`:14 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/profiles/coo_operating_chain.yaml<br>support/connection/mcp_projection.py<br>support/operator/coo_operating_chain.py |
| `core` | `support/checkers/profiles/core.yaml:2` | core-invariant-candidate | `axis_vocab_drift`, `package_path_admission`, `axis_contract_projection`, `declared_verifier_exists`, `axis_field_enum_parity`, `agentfact_single_home`, `building_root_anchor`, `catalog_reader_sync`, `agent_resource_resolution`, `axis_field_set_single_source`, `builder_consumes_axis_api`, `support_no_axis_judgment`, `bricks_spec_completeness`, `building_lifecycle_path_shape`, `building_map_graph`, `project_declaration`, `building_declaration_integrity`, `building_plans_boundary_sweep`, `axis_crossing_elegance`, `link_gate_measurement_separation`, `fan_out_sibling_evidence_independence`, `evidence_spine`, `evidence_spine_projection` | `path_absent`:3, `path_absent_glob`:3, `path_allowlist`:1, `path_exists`:27, `text_absent`:1, `text_contains`:2, `yaml_literal_set`:1 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | agent/disciplines/closed-agentfact.md<br>agent/prompts/coo.md<br>agent/return_fact.py<br>agent/skills/building-coordination/SKILL.md<br>agent/skills/make-a-brick/SKILL.md<br>agent/skills/project-creation/SKILL.md<br>...(+35) |
| `driver-public-intake-seal` | `support/checkers/profiles/driver_public_intake_seal.yaml:2` | core-invariant-candidate | `driver_public_intake_seal` | `path_exists`:3, `text_absent`:1, `text_contains`:2 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/driver_public_intake_seal.yaml |
| `gate-registry-single-source` | `support/checkers/profiles/gate_registry_single_source.yaml:2` | core-invariant-candidate | `gate_registry_single_source` | `path_exists`:5, `text_contains`:4 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/gate_registry_single_source.yaml |
| `link-routing-behavioral` | `support/checkers/profiles/link_routing_behavioral.yaml:2` | dogfood-candidate | `package_path_admission`, `axis_contract_projection`, `building_lifecycle_path_shape`, `building_map_graph` | `auto_repair_replay_case`:2, `building_lifecycle_case`:2, `building_lifecycle_rejects`:3, `declared_step_template_plan_case`:2, `fail_fixture_rejects`:4, `link_route_evidence_case`:1, `path_absent`:10, `path_absent_glob`:1, `path_exists`:27, `route_materialization_case`:1, `route_policy_boundary`:1, `text_absent`:6, `text_contains`:24, `transition_concern_disposition_case`:3 | support evidence only<br>transition concern is non-binding Agent evidence<br>Link disposition is Link row evidence<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>Link-owned declared policy only<br>Link decision packet is an evidence view<br>declared boundary replay uses repeated step_refs | support/checkers/profiles/link_routing_behavioral.yaml |
| `mcp-dispatch-wire` | `support/checkers/profiles/mcp_dispatch_wire.yaml:2` | live-heavy-or-provider-candidate | `mcp_dispatch_wire` | `path_exists`:4, `text_contains`:2 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/mcp_dispatch_wire.yaml |
| `native-dispatch-brick-backstop` | `support/checkers/profiles/native_dispatch_brick_backstop.yaml:2` | dogfood-candidate | `package_path_admission`, `building_lifecycle_path_shape`, `building_map_graph` | `native_dispatch_close_case`:1, `path_absent`:4, `path_exists`:4, `text_absent`:1, `text_contains`:5, `workflow_import_case`:1 | support evidence only<br>native-dispatch backstop checks evidence SHAPE, not semantic correctness<br>the COMPUTED gate verdict value (sufficient / missing_required_facts) is the Link rule output, not asserted by this profile<br>the optional Claude Pre/PostToolUse hook is Claude Code config, not the Brick engine<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority | support/checkers/profiles/native_dispatch_brick_backstop.yaml |
| `read-side-projection-boundary` | `support/checkers/profiles/read_side_projection_boundary.yaml:2` | live-heavy-or-provider-candidate | `package_path_admission`, `axis_contract_projection`, `building_lifecycle_path_shape`, `building_map_graph`, `reporter_notification_projection`, `dashboard_productization_projection`, `mcp_stdio_smoke`, `connect_config_launch`, `codex_projection_native`, `claude_projection_native`, `install_script_lint`, `release_export_exclusion`, `product_no_smith_residue` | `intake_evidence_projection_case`:1, `path_absent`:16, `path_absent_glob`:2, `path_exists`:27, `text_absent`:8, `text_contains`:25 | support evidence only<br>read-side view backstop checks renderer SHAPE and boundary text, not semantic correctness<br>the rendered view is a static projection over already-written evidence, not a runtime<br>not source truth<br>not source-truth write-back / edit surface<br>not a dashboard runtime / server / scheduler<br>not a provider-liveness proof<br>generated_at and rows[].last_evidence_at are recency/observation fields (snapshot build time and newest recorded evidence timestamp), not process liveness<br>not success judgment<br>not quality judgment<br>not Movement authority<br>profile pass is not source truth<br>four support-only report sinks only<br>not route input | support/checkers/profiles/read_side_projection_boundary.yaml |
| `report-env-autoload` | `support/checkers/profiles/report_env_autoload.yaml:2` | live-heavy-or-provider-candidate | `report_env_autoload` | `path_exists`:4, `text_contains`:4 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/check_report_env_autoload.py<br>support/checkers/profiles/report_env_autoload.yaml |
| `return-field-merge-set-parity` | `support/checkers/profiles/return_field_merge_set_parity.yaml:2` | core-invariant-candidate | `return_field_merge_set_parity` | `path_exists`:4, `text_contains`:3 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not provider proof | support/checkers/profiles/return_field_merge_set_parity.yaml |
| `structure-template-integrity` | `support/checkers/profiles/structure_template_integrity.yaml:2` | dogfood-candidate | `package_path_admission`, `brick_template_catalog_restructure`, `axis_contract_projection`, `building_lifecycle_path_shape`, `building_map_graph`, `pin_estate_integrity` | `child_building_candidate_case`:1, `fail_fixture_rejects`:4, `path_absent`:3, `path_exists`:30, `route_policy_boundary`:1, `text_absent`:2, `text_contains`:19 | support evidence only<br>synthetic FIRE fixtures are guard evidence only<br>P10 checker mode enforces split catalog binding shape and old registry absence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>rejects structural boundary violations only | support/checkers/module_registry.yaml<br>support/checkers/profiles/structure_template_integrity.yaml |
| `tier-a-three-axis-conformance` | `support/checkers/profiles/tier_a_three_axis_conformance.yaml:2` | core-invariant-candidate | `tier_a_three_axis_conformance` | `path_exists`:1, `text_absent`:1, `text_contains`:1 | support evidence only<br>not source truth<br>not success judgment<br>not quality judgment<br>not Movement authority<br>not real-provider proof | support/checkers/profiles/tier_a_three_axis_conformance.yaml |

## KERNEL_DISPATCH table

| kernel_check id | runner function | source file:line | candidate bucket |
|---|---|---:|---|
| `adapter_error_frontier_manifest_consistency` | `run_adapter_error_frontier_manifest_consistency` | `support/checkers/lib/kernel_checks.py:5570` | live-heavy-or-provider-candidate |
| `adapter_error_path_hardening` | `run_adapter_error_path_hardening` | `support/checkers/lib/kernel_checks.py:5661` | live-heavy-or-provider-candidate |
| `adapter_usage_meter` | `_CallMainKernel(check_id='adapter_usage_meter', module_name='support.checkers.check_adapter_usage_meter', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `agent_adapter_return_shape` | `run_agent_adapter_return_shape` | `support/checkers/lib/kernel_checks.py:2355` | core-invariant-candidate |
| `agent_object_schema_single_source` | `_CallMainKernel(check_id='agent_object_schema_single_source', module_name='support.checkers.check_agent_object_schema_single_source', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `agent_resource_resolution` | `_CallMainKernel(check_id='agent_resource_resolution', module_name='support.checkers.check_agent_resource_resolution', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `agent_session_id_redaction` | `run_agent_session_id_redaction` | `support/checkers/lib/kernel_checks.py:9849` | live-heavy-or-provider-candidate |
| `agentfact_single_home` | `_CallMainKernel(check_id='agentfact_single_home', module_name='support.checkers.check_agentfact_single_home', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `assembly_equivalence` | `_CallMainKernel(check_id='assembly_equivalence', module_name='support.checkers.check_assembly_equivalence', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `axis_contract_projection` | `_CallMainKernel(check_id='axis_contract_projection', module_name='support.checkers.check_axis_contract_projection', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `axis_crossing_elegance` | `_CallMainKernel(check_id='axis_crossing_elegance', module_name='support.checkers.check_axis_crossing_elegance', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `axis_field_enum_parity` | `_CallMainKernel(check_id='axis_field_enum_parity', module_name='support.checkers.check_axis_field_enum_parity', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `axis_field_set_single_source` | `_CallMainKernel(check_id='axis_field_set_single_source', module_name='support.checkers.check_axis_field_set_single_source', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `axis_vocab_drift` | `run_axis_vocab_drift` | `support/checkers/lib/kernel_checks.py:583` | core-invariant-candidate |
| `bounded_agent_proposed_routing_loop` | `_CallMainKernel(check_id='bounded_agent_proposed_routing_loop', module_name='support.checkers.check_bounded_agent_proposed_routing_loop0', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `brick_cli_entrypoint_smoke` | `run_brick_cli_entrypoint_smoke` | `support/checkers/lib/kernel_checks.py:8828` | live-heavy-or-provider-candidate |
| `brick_template_catalog_restructure` | `_CallMainKernel(check_id='brick_template_catalog_restructure', module_name='support.checkers.check_brick_template_catalog_restructure', argv=('--repo', <object object at 0x105570cb0>, '--mode', 'p10-delete'))` | `not_proven:?` | unclassified-candidate |
| `bricks_spec_completeness` | `_CallMainKernel(check_id='bricks_spec_completeness', module_name='support.checkers.check_bricks_spec_completeness', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `builder_consumes_axis_api` | `_CallMainKernel(check_id='builder_consumes_axis_api', module_name='support.checkers.check_builder_consumes_axis_api', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `building_declaration_integrity` | `_CallMainKernel(check_id='building_declaration_integrity', module_name='support.checkers.check_building_declaration_integrity', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | dogfood-candidate |
| `building_lifecycle_path_shape` | `_CallMainKernel(check_id='building_lifecycle_path_shape', module_name='support.checkers.check_building_lifecycle_path_shape', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | dogfood-candidate |
| `building_map_graph` | `run_building_map_graph` | `support/checkers/lib/kernel_checks.py:651` | dogfood-candidate |
| `building_operator_driver0` | `_CallMainKernel(check_id='building_operator_driver0', module_name='support.checkers.check_building_operator_driver0', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | dogfood-candidate |
| `building_plans_boundary_sweep` | `run_building_plans_boundary_sweep` | `support/checkers/lib/kernel_checks.py:711` | live-heavy-or-provider-candidate |
| `building_root_anchor` | `_CallMainKernel(check_id='building_root_anchor', module_name='support.checkers.check_building_root_anchor', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | dogfood-candidate |
| `casting_node_carry` | `run_casting_node_carry` | `support/checkers/lib/case_runners.py:5766` | dogfood-candidate |
| `catalog_reader_sync` | `_CallMainKernel(check_id='catalog_reader_sync', module_name='support.checkers.check_catalog_reader_sync', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `chained_carry_dependency` | `_CallMainKernel(check_id='chained_carry_dependency', module_name='support.checkers.check_chained_carry_dependency', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `charter_injection` | `_CallMainKernel(check_id='charter_injection', module_name='support.checkers.check_charter_injection', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `chat_session_park_seam` | `run_chat_session_park_seam` | `support/checkers/lib/kernel_checks.py:6577` | live-heavy-or-provider-candidate |
| `claude_projection_native` | `run_claude_projection_native` | `support/checkers/lib/kernel_checks.py:9378` | live-heavy-or-provider-candidate |
| `cli_runner_stdin_devnull` | `_CallMainKernel(check_id='cli_runner_stdin_devnull', module_name='support.checkers.check_cli_runner_stdin_devnull', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | live-heavy-or-provider-candidate |
| `codex_connect_stall_classification` | `run_codex_connect_stall_classification` | `support/checkers/lib/kernel_checks.py:2981` | live-heavy-or-provider-candidate |
| `codex_projection_native` | `run_codex_projection_native` | `support/checkers/lib/kernel_checks.py:9133` | live-heavy-or-provider-candidate |
| `connect_config_launch` | `run_connect_config_launch` | `support/checkers/lib/kernel_checks.py:9017` | live-heavy-or-provider-candidate |
| `dashboard_productization_projection` | `run_dashboard_productization_projection` | `support/checkers/lib/kernel_checks.py:7998` | live-heavy-or-provider-candidate |
| `declared_verifier_exists` | `_CallMainKernel(check_id='declared_verifier_exists', module_name='support.checkers.check_declared_verifier_exists', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `design_ai_text_seams` | `run_design_ai_text_seams` | `support/checkers/lib/kernel_checks.py:2662` | live-heavy-or-provider-candidate |
| `driver_public_intake_seal` | `_CallMainKernel(check_id='driver_public_intake_seal', module_name='support.checkers.check_driver_public_intake_seal', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | dogfood-candidate |
| `evidence_spine` | `_CallMainKernel(check_id='evidence_spine', module_name='support.checkers.check_evidence_spine', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `evidence_spine_projection` | `_CallMainKernel(check_id='evidence_spine_projection', module_name='support.checkers.check_evidence_spine_projection', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `fan_out_sibling_evidence_independence` | `_CallMainKernel(check_id='fan_out_sibling_evidence_independence', module_name='support.checkers.check_fan_out_sibling_evidence_independence', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `first_use_wizard` | `_CallMainKernel(check_id='first_use_wizard', module_name='support.checkers.check_first_use_wizard', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | live-heavy-or-provider-candidate |
| `gate_registry_single_source` | `_CallMainKernel(check_id='gate_registry_single_source', module_name='support.checkers.check_gate_registry_single_source', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `gemini_api_adapter` | `run_gemini_api_adapter` | `support/checkers/lib/kernel_checks.py:3341` | live-heavy-or-provider-candidate |
| `install_script_lint` | `run_install_script_lint` | `support/checkers/lib/kernel_checks.py:3740` | live-heavy-or-provider-candidate |
| `link_gate_measurement_separation` | `_CallMainKernel(check_id='link_gate_measurement_separation', module_name='support.checkers.check_link_gate_measurement_separation', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `mcp_dispatch_wire` | `_CallMainKernel(check_id='mcp_dispatch_wire', module_name='support.checkers.check_mcp_dispatch_wire', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | live-heavy-or-provider-candidate |
| `mcp_stdio_smoke` | `run_mcp_stdio_smoke` | `support/checkers/lib/kernel_checks.py:8896` | live-heavy-or-provider-candidate |
| `onboard_smoke` | `run_onboard_smoke` | `support/checkers/lib/kernel_checks.py:3580` | live-heavy-or-provider-candidate |
| `package_path_admission` | `_run_package_path_admission` | `support/checkers/check_profile.py:294` | unclassified-candidate |
| `pin_estate_integrity` | `_CallMainKernel(check_id='pin_estate_integrity', module_name='support.checkers.check_pin_estate_integrity', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `product_no_smith_residue` | `run_product_no_smith_residue` | `support/checkers/lib/kernel_checks.py:4007` | live-heavy-or-provider-candidate |
| `project_declaration` | `_CallMainKernel(check_id='project_declaration', module_name='support.checkers.check_project_declaration', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `provider_preflight` | `run_provider_preflight` | `support/checkers/lib/kernel_checks.py:2563` | live-heavy-or-provider-candidate |
| `recording_checker_derived_contract` | `_CallMainKernel(check_id='recording_checker_derived_contract', module_name='support.checkers.check_recording_checker_derived_contract', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `release_export_exclusion` | `run_release_export_exclusion` | `support/checkers/lib/kernel_checks.py:3872` | live-heavy-or-provider-candidate |
| `report_env_autoload` | `_CallMainKernel(check_id='report_env_autoload', module_name='support.checkers.check_report_env_autoload', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | unclassified-candidate |
| `reporter_notification_projection` | `run_reporter_notification_projection` | `support/checkers/lib/kernel_checks.py:5328` | live-heavy-or-provider-candidate |
| `return_field_merge_set_parity` | `_CallMainKernel(check_id='return_field_merge_set_parity', module_name='support.checkers.check_return_field_merge_set_parity', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `support_no_axis_judgment` | `_CallMainKernel(check_id='support_no_axis_judgment', module_name='support.checkers.check_support_no_axis_judgment', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |
| `tier_a_three_axis_conformance` | `_CallMainKernel(check_id='tier_a_three_axis_conformance', module_name='support.checkers.check_tier_a_three_axis_conformance', argv=('--repo', <object object at 0x105570cb0>))` | `not_proven:?` | core-invariant-candidate |

## RULE_RUNNERS table

| rule key | runner function | source file:line |
|---|---|---:|
| `adapter_capability_rehome_case` | `run_adapter_capability_rehome_case` | `support/checkers/lib/case_runners.py:5880` |
| `adapter_gate_shape_union_case` | `run_adapter_gate_shape_union_case` | `support/checkers/lib/case_runners.py:1248` |
| `adapter_model_selection_case` | `run_adapter_model_selection_case` | `support/checkers/lib/case_runners.py:46` |
| `adapter_model_selection_rejects` | `run_adapter_model_selection_rejects` | `support/checkers/lib/case_runners.py:75` |
| `agent_candidate_packet_case` | `run_agent_candidate_packet_case` | `support/checkers/lib/case_runners.py:2539` |
| `agent_preferred_adapter_rejects` | `run_agent_preferred_adapter_rejects` | `support/checkers/lib/rule_runners.py:314` |
| `agent_resource_boundary` | `run_agent_resource_boundary` | `support/checkers/lib/rule_runners.py:167` |
| `agent_resource_retired_ref_rejects` | `run_agent_resource_retired_ref_rejects` | `support/checkers/lib/rule_runners.py:250` |
| `auto_repair_replay_case` | `run_auto_repair_replay_case` | `support/checkers/lib/case_runners.py:9148` |
| `building_intake_seam_case` | `run_building_intake_seam_case` | `support/checkers/lib/case_runners.py:1422` |
| `building_lifecycle_case` | `run_building_lifecycle_case` | `support/checkers/lib/case_runners.py:4087` |
| `building_lifecycle_rejects` | `run_building_lifecycle_rejects` | `support/checkers/lib/case_runners.py:4112` |
| `building_plan_boundary` | `run_building_plan_boundary` | `support/checkers/lib/rule_runners.py:355` |
| `child_building_candidate_case` | `run_child_building_candidate_case` | `support/checkers/lib/case_runners.py:9186` |
| `compose_building_case` | `run_compose_building_case` | `support/checkers/lib/case_runners.py:3763` |
| `compose_building_rejects` | `run_compose_building_rejects` | `support/checkers/lib/case_runners.py:3994` |
| `declared_step_template_plan_case` | `run_declared_step_template_plan_case` | `support/checkers/lib/case_runners.py:3682` |
| `declared_step_template_plan_rejects` | `run_declared_step_template_plan_rejects` | `support/checkers/lib/case_runners.py:3738` |
| `fail_fixture_rejects` | `run_fail_fixture_rejects` | `support/checkers/lib/case_runners.py:9213` |
| `gate_sequence_policy_case` | `run_gate_sequence_policy_case` | `support/checkers/lib/case_runners.py:4034` |
| `gate_sequence_policy_rejects` | `run_gate_sequence_policy_rejects` | `support/checkers/lib/case_runners.py:4057` |
| `hook_registry_axis_case` | `run_hook_registry_axis_case` | `support/checkers/lib/case_runners.py:7274` |
| `intake_evidence_projection_case` | `run_intake_evidence_projection_case` | `support/checkers/lib/case_runners.py:9342` |
| `intake_project_vessel_case` | `run_intake_project_vessel_case` | `support/checkers/lib/case_runners.py:1967` |
| `json_required_paths` | `run_json_required_paths` | `support/checkers/lib/rule_runners.py:133` |
| `json_value_paths` | `run_json_value_paths` | `support/checkers/lib/rule_runners.py:147` |
| `link_route_evidence_case` | `run_link_route_evidence_case` | `support/checkers/lib/case_runners.py:9864` |
| `materialize_building_intent_case` | `run_materialize_building_intent_case` | `support/checkers/lib/case_runners.py:190` |
| `materialize_building_intent_rejects` | `run_materialize_building_intent_rejects` | `support/checkers/lib/case_runners.py:945` |
| `native_dispatch_close_case` | `run_native_dispatch_close_case` | `support/checkers/lib/case_runners.py:4150` |
| `onboard_seam_case` | `run_onboard_seam_case` | `support/checkers/lib/case_runners.py:2299` |
| `path_absent` | `run_path_absent` | `support/checkers/lib/rule_runners.py:52` |
| `path_absent_glob` | `run_path_absent_glob` | `support/checkers/lib/rule_runners.py:61` |
| `path_allowlist` | `run_path_allowlist` | `support/checkers/lib/rule_runners.py:74` |
| `path_exists` | `run_path_exists` | `support/checkers/lib/rule_runners.py:43` |
| `preset_building_completion_case` | `run_preset_building_completion_case` | `support/checkers/lib/case_runners.py:1078` |
| `preset_ranking_packet_case` | `run_preset_ranking_packet_case` | `support/checkers/lib/case_runners.py:2762` |
| `route_materialization_case` | `run_route_materialization_case` | `support/checkers/lib/case_runners.py:101` |
| `route_policy_boundary` | `run_route_policy_boundary` | `support/checkers/lib/rule_runners.py:380` |
| `run_once_task_source_admission_case` | `run_once_task_source_admission_case` | `support/checkers/lib/case_runners.py:7093` |
| `source_fact_body_carry_case` | `run_source_fact_body_carry_case` | `support/checkers/lib/case_runners.py:7479` |
| `step_output_drain_case` | `run_step_output_drain_case` | `support/checkers/lib/case_runners.py:7978` |
| `step_output_drain_rejects` | `run_step_output_drain_rejects` | `support/checkers/lib/case_runners.py:8082` |
| `text_absent` | `<lambda>` | `support/checkers/check_profile.py:224` |
| `text_contains` | `<lambda>` | `support/checkers/check_profile.py:223` |
| `transition_concern_disposition_case` | `run_transition_concern_disposition_case` | `support/checkers/lib/case_runners.py:137` |
| `wiki_carry_truncation_survival_case` | `run_wiki_carry_truncation_survival_case` | `support/checkers/lib/case_runners.py:7807` |
| `workflow_import_case` | `run_workflow_import_case` | `support/checkers/lib/case_runners.py:4950` |
| `write_scope_default_exclude_case` | `run_write_scope_default_exclude_case` | `support/checkers/lib/case_runners.py:7308` |
| `yaml_literal_set` | `run_yaml_literal_set` | `support/checkers/lib/rule_runners.py:115` |

## Candidate diet interpretation

1. Keep a small `core` lane for cheap axis/source-truth invariants and profile self-consistency.
2. Move/provider-bound or real environment seams (`onboard`, `mcp`, `cli`, provider preflight, Slack/dashboard delivery) into an explicit live-heavy/dogfood lane.
3. Treat Building evidence and checker green as support evidence only; do not let profile names imply quality/success approval.
4. Before deleting or renaming any profile, run a stronger selector scan over CI/scripts/docs; literal scan here is only preliminary.

## Bounded replay commands

```bash
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile core
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile link_routing_behavioral
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
# Avoid --all for diet measurement unless intentionally running live-heavy/dogfood lanes.
```

## Not proven

- Candidate buckets are heuristic and not an admitted taxonomy.
- Literal profile selector refs are not a complete CI/operator/docs usage proof.
- Runtime cost was not measured in this artifact; it classifies risk from profile/check names and source snippets only.
- No profile was deleted, renamed, or split here.
