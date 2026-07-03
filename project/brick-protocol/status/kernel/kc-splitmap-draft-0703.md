# kernel_checks.py 분할 지도 — v2 검증 완료 (0703)

Status: support evidence only. §4-1 Stage A 산출(kc-splitmap-0703a work4 수확) →
**v2(kc-splitmap-v2-0703b, 13-way fan 파티션)가 전 잎 경계·클로저·pin 검증 완료** —
17노드 전원 1라운드 완주, frontier=complete(COO forward, 0703 밤).

**파티션 무결성 확정(QA 독립 AST 재계수 + COO 스팟체크 일치)**: 모듈 최상위 이름 208개 중
204개가 정확히 1잎 배정, 이중배정 0, **고아 4개의 COO 처분**:
- `captured_output`(:619)·`patched_argv`(:627)·`call_main`(:646-660) → **facade 잔류 명시**
  (check_profile.py:129·:308이 직접 임포트·호출하는 러너 디스패치 유틸리티 3인방).
- `_gemini_api_classify_error_kind`(:3420-3443) → **사어(전 저장소 참조 0)** — 슬라이스 진행
  중 삭제 후보(삭제 커밋에서 --all green 확인).
주의: `_without_report_grain_env`(:637)는 고아가 아니다 — reporter 잎의 비연속 블록 배정
(사용처 :3865·:3916).

슬라이스 실행 시 각 잎의 검증된 최종 범위는 v2 합성 노드(work-14)의
verified_leaf_assignment_table_v2가 정본 — vessel:
project/brick-protocol/buildings/kc-splitmap-v2-0703b/. 아래 초안 수치와 다르면 v2가 이긴다.
{
 "D1_run_entrypoint_inventory": {
  "check_profile_import_surface": "support/checkers/check_profile.py:127-156 imports all current kernel_checks run_* names through support.checkers.lib.kernel_checks; existing extracted siblings are re-exported through this facade pattern.",
  "kernel_checks_py_lines": 11379,
  "run_count": 18,
  "runs": [
   "run_axis_vocab_drift support/checkers/lib/kernel_checks.py:595-615; imported check_profile.py:128; dispatch check_profile.py:333; profiles: core.yaml; direct private helpers: _axis_vocab_check_agent_adapter_refs, _axis_vocab_check_concern_kind_parity, _axis_vocab_check_docs, _axis_vocab_check_link_sources, _axis_vocab_check_transition_author_prefix_consumers, _axis_vocab_scan_exact_enum_redefinitions; transitive helper count: 19.",
   "run_building_map_graph kernel_checks.py:663-689; imported check_profile.py:130; dispatch check_profile.py:449; profiles: agent_axis_behavioral.yaml, building_automation.yaml, coo_operating_chain.yaml, core.yaml, link_routing_behavioral.yaml, native_dispatch_brick_backstop.yaml, read_side_projection_boundary.yaml, structure_template_integrity.yaml; private helpers: none observed.",
   "run_building_plans_boundary_sweep kernel_checks.py:717-816; imported check_profile.py:131; dispatch check_profile.py:672; profiles: core.yaml; private helpers: none observed.",
   "run_agent_adapter_return_shape kernel_checks.py:2758-3019; imported check_profile.py:132; dispatch check_profile.py:676; profiles: agent_axis_behavioral.yaml, building_skill_preset_agent_resource_boundary.yaml, building_skill_preset_agent_tool_hardening.yaml; direct helpers: _agent_adapter_request_instruction_packet_probe, _agent_effective_write_probe, _agent_instruction_packet_probe, _agent_read_tier_probe, _artifact_grounding_probe, _proof_obligation_pipeline_probe; transitive helper count: 11.",
   "run_reporter_notification_projection kernel_checks.py:4965-5211; imported check_profile.py:144; dispatch check_profile.py:743; profiles: read_side_projection_boundary.yaml; direct helpers: _assert_no_scheduler_constructs, _assert_reporter_agent_incomplete_event_mapping, _assert_reporter_auto_wiring, _assert_reporter_brick_grain_threading, _assert_reporter_dashboard_project_ref_guard, _assert_reporter_label_parity, _assert_reporter_message_shape, _assert_reporter_structure_diagram_branch_rendering, _minimal_operator_wake_target, _minimal_reporter_packet, _reporter_inbox_packet_shape_fold; transitive helper count: 15.",
   "run_building_result_summary kernel_checks.py:5214-5476; imported check_profile.py:134; dispatch check_profile.py:718; profiles: building_operator_driver0.yaml; helpers: _assert_no_forbidden_summary_key, _init_git_repo_with_wip_anchor, _write_json, _write_jsonl.",
   "run_adapter_error_frontier_manifest_consistency kernel_checks.py:5544-5698; imported check_profile.py:146; dispatch check_profile.py:756; profiles: building_automation.yaml; direct helpers: _adapter_error_manifest_link_frontier_record, _adapter_error_manifest_write_broken_fixture, _adapter_error_manifest_write_dynamic_reroute_fixture, _adapter_error_manifest_write_jsonl; transitive helper count: 7.",
   "run_adapter_error_path_hardening kernel_checks.py:5701-6087; imported check_profile.py:147; dispatch check_profile.py:757; profiles: building_automation.yaml; direct helpers: _adapter_error_hardening_graph_plan, _append_adapter_error_stop_disposition, _assert_adapter_error_diagnostics_preserved, _assert_adapter_error_frontier_report_root_admission, _assert_codex_ephemeral_env_dial, _persisted_adapter_error_hold_reason, _rewrite_adapter_error_hold_as_legacy_reason_refs, _write_adapter_error_frontier_direct, _write_adapter_error_frontier_fixture; transitive helper count: 11.",
   "run_raw_evidence_stream_scrub kernel_checks.py:6090-6200; imported check_profile.py:148; dispatch check_profile.py:758; profiles: raw_evidence_stream_scrub.yaml; private helpers: none observed.",
   "run_agent_output_text_preservation kernel_checks.py:6203-6374; imported check_profile.py:149; dispatch check_profile.py:759; profiles: agent_output_text_preservation.yaml; private helpers: none observed.",
   "run_chat_session_park_seam kernel_checks.py:7376-7735; imported check_profile.py:145; dispatch check_profile.py:755; profiles: building_automation.yaml; direct helper count: 21; transitive helper count: 29.",
   "run_dashboard_productization_projection kernel_checks.py:8903-8961; imported check_profile.py:155; dispatch check_profile.py:748; profiles: read_side_projection_boundary.yaml; direct helper count: 10; transitive helper count: 37.",
   "run_brick_cli_entrypoint_smoke kernel_checks.py:10327-10398; imported check_profile.py:156; dispatch check_profile.py:766; profiles: brick_cli_entrypoint.yaml; helpers: _assert_brick_cli_customer_task_intent, _assert_brick_cli_probe, _brick_cli_work_brick_rows.",
   "run_mcp_stdio_smoke kernel_checks.py:10401-10465; imported check_profile.py:150; dispatch check_profile.py:785; profiles: read_side_projection_boundary.yaml; private helpers: none observed.",
   "run_connect_config_launch kernel_checks.py:10522-10635; imported check_profile.py:151; dispatch check_profile.py:795; profiles: read_side_projection_boundary.yaml; helper: _parse_codex_mcp_config.",
   "run_codex_projection_native kernel_checks.py:10638-10840; imported check_profile.py:152; dispatch check_profile.py:820; profiles: read_side_projection_boundary.yaml; private helpers: none observed.",
   "run_claude_projection_native kernel_checks.py:10883-11112; imported check_profile.py:153; dispatch check_profile.py:808; profiles: read_side_projection_boundary.yaml; helper: _split_claude_frontmatter.",
   "run_agent_session_id_redaction kernel_checks.py:11354-11379; imported check_profile.py:154; dispatch check_profile.py:954; profiles: agent_axis_behavioral.yaml; direct helpers: _collect_session_id_offenders, _session_id_redaction_fire_probe; transitive helper count: 7."
  ],
  "shared_private_helpers": [
   "No private helper is directly called by two or more run_* entrypoints.",
   "Transitive shared helpers observed: _chat_session_park_graph_plan kernel_checks.py:9008-9097 used by run_adapter_error_path_hardening and run_chat_session_park_seam; _chat_session_probe_uuid_text kernel_checks.py:9307-9308 used by run_agent_session_id_redaction and run_chat_session_park_seam; _chat_session_probe_ulid_text kernel_checks.py:9311-9312 used by run_agent_session_id_redaction and run_chat_session_park_seam; _chat_session_write_temp_project_declaration kernel_checks.py:9233-9258 used by run_chat_session_park_seam and run_dashboard_productization_projection."
  ]
 }
}

{
 "D2_profile_pin_conflicts": {
  "method": "Parsed support/checkers/profiles/*.yaml with support.checkers.lib.yaml_subset.parse_yaml_subset and matched text_contains entries for path support/checkers/lib/kernel_checks.py against lines inside private helper function ranges.",
  "pin_rows": [
   "agent_axis_behavioral.yaml:text_contains[38]:'gemini-local read-write-scoped request did not enter read tier' -> kernel_checks.py:1809 inside _agent_read_tier_probe:1426-2289; move with agent_adapter_return_shape_check.py.",
   "agent_axis_behavioral.yaml:text_contains[38]:'gemini-local non-zero adapter error omitted' -> kernel_checks.py:2277 inside _agent_read_tier_probe:1426-2289; move with agent_adapter_return_shape_check.py.",
   "agent_axis_behavioral.yaml:text_contains[38]:'gemini-client-error-probe.json' -> kernel_checks.py:2211 inside _agent_read_tier_probe:1426-2289; move with agent_adapter_return_shape_check.py.",
   "brick_cli_entrypoint.yaml:text_contains[5]:10 strings all hit _assert_brick_cli_customer_task_intent:9762-10303 at lines 9775, 9812, 9816, 9817, 10210, 10216, 10223, 10232, 10282, 10290; move with brick_cli_entrypoint_check.py.",
   "building_automation.yaml:text_contains[15]:chat-session helper-name pins hit _chat_session_assert_undeclared_adapter_rejects:9126, _chat_session_assert_envelope_session_key_rejects:9315, _chat_session_assert_key_scan_fire:9339, _chat_session_value_only_session_rejector:9364/9386/9389/9393, _chat_session_probe_uuid_text:9307, _chat_session_probe_ulid_text:9311, _chat_session_mutate_envelope_uuid:9673/9676, _chat_session_mutate_park_as_adapter_error:9680, _chat_session_delete_work_envelope:9688; move with chat_session_park_check.py except probe strings also appear in session_id_redaction helper lines 11268-11269.",
   "raw_evidence_stream_scrub.yaml:text_contains[2] strings hit helper fixture bodies outside run_raw_evidence_stream_scrub: brick-work.jsonl at 7127/7169/7229/7262 and agent-return.jsonl at 7131/7170/7233/7263 in adapter-error manifest fixtures; additional hits in dashboard/chat-session helpers at 8660, 8683, 8687, 8722, 8776, 9486, 9487, 9499. These pins must be split or duplicated with the functions they actually pin, not blindly moved with run_raw_evidence_stream_scrub."
  ]
 }
}

{
 "D3_axis_vocab_self_allowlist": {
  "current_locations": [
   "_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST at support/checkers/lib/kernel_checks.py:120; consumed by exact enum scan at lines 304-327, specifically movement allowlist check at line 317.",
   "_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST at support/checkers/lib/kernel_checks.py:131; consumed by line 322.",
   "_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST at support/checkers/lib/kernel_checks.py:139; consumed by line 327."
  ],
  "split_disposition": "Move all three allowlists with the axis-vocab scanner into axis_vocab_drift_check.py. They are private constants used only by the axis-vocab helper cluster and should not remain as shared kernel facade state."
 }
}

{
 "D4_split_map": {
  "existing_sibling_convention": "Observed existing extracted checker-lib siblings are flat modules under support/checkers/lib: no_smith_residue_check.py 165L, provider_preflight_check.py 202L, onboard_smoke_check.py 262L, install_release_export_lint_check.py 453L, design_ai_text_seams_check.py 334L, codex_connect_stall_classification_check.py 378L, gemini_local_only_adapter_check.py 228L, graph_topology_fan_barrier.py 213L. module_registry.yaml:667-745 records kernel_checks.py plus these siblings with owns_crossings: [], consumes_crossings: [], imports_axis: [], forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent].",
  "import_surface_proposal": "Keep support/checkers/lib/kernel_checks.py as facade/re-export during extraction. Evidence: check_profile.py:127 imports from kernel_checks.py and already includes extracted sibling functions at lines 133,135-143. Direct check_profile import rewiring would touch broad dispatch/import surface and is not needed per existing pattern.",
  "per_leaf_registry_requirement": "Each new support/checkers/lib/<domain>_check.py needs one module_registry.yaml row matching existing sibling rows: layer checkers/lib, role checker-lib, owns_crossings [], consumes_crossings [], imports_axis [], forbidden_ownership [movement_author, target_selector, success_judge, quality_judge, route_invent], decomposition_target empty, and a pinned_by note naming the moved kernel check(s).",
  "proposed_leaves": [
   "axis_vocab_drift_check.py: run_axis_vocab_drift plus _AXIS_VOCAB_* constants/helpers lines 57-615; estimated extraction about 560 LOC; first slice because isolated and profile-pinned only by core.yaml.",
   "building_plan_graph_check.py: run_building_map_graph and run_building_plans_boundary_sweep lines 663-816; estimated 155 LOC; shallow dependency slice.",
   "agent_adapter_return_shape_check.py: run_agent_adapter_return_shape plus helpers 819-3417; estimated 2600 LOC; profile body pins in agent_axis_behavioral.yaml must move.",
   "reporter_notification_projection_check.py: reporter helpers 637, 692-714, 3492-5211; estimated 1770 LOC; read_side_projection_boundary.yaml pins remain with this leaf.",
   "building_result_summary_check.py: run_building_result_summary plus helpers 5479-5541; estimated 330 LOC.",
   "adapter_error_check.py: run_adapter_error_frontier_manifest_consistency, run_adapter_error_path_hardening, helpers 6377-7373, plus shared use of _chat_session_park_graph_plan unless that helper is first factored into chat_session_support_check.py; estimated 1000 LOC excluding shared chat-session helper.",
   "raw_evidence_stream_scrub_check.py: run_raw_evidence_stream_scrub lines 6090-6200; estimated 115 LOC; do not move unrelated raw_evidence_stream_scrub.yaml pins that actually target adapter-error/dashboard/chat-session fixture helpers.",
   "agent_output_text_preservation_check.py: run_agent_output_text_preservation lines 6203-6374; estimated 175 LOC.",
   "chat_session_park_check.py: run_chat_session_park_seam plus helpers 8964-9724; estimated 760 LOC; owns building_automation.yaml chat-session helper pins; shared helper concerns with adapter_error, dashboard, and session_id_redaction must be handled before or during this slice.",
   "dashboard_productization_projection_check.py: run_dashboard_productization_projection plus dashboard helpers 7770-8900 and shared _chat_session_write_temp_project_declaration; estimated 1135 LOC excluding shared helper.",
   "brick_cli_entrypoint_check.py: run_brick_cli_entrypoint_smoke plus helpers 9733-10324; estimated 670 LOC; owns brick_cli_entrypoint.yaml private-helper pins.",
   "mcp_connect_projection_check.py: run_mcp_stdio_smoke, run_connect_config_launch, run_codex_projection_native, run_claude_projection_native, _parse_codex_mcp_config, _split_claude_frontmatter; estimated 600 LOC.",
   "agent_session_id_redaction_check.py: run_agent_session_id_redaction plus helpers 11205-11351 and possibly duplicate/import _chat_session_probe_uuid_text/_chat_session_probe_ulid_text; estimated 180 LOC."
  ],
  "shared_helper_disposition": "For transitive shared helpers, prefer one explicit support leaf only when the helper is genuinely domain-neutral. _chat_session_park_graph_plan and _chat_session_write_temp_project_declaration are chat-session/domain fixtures; leave them in chat_session_park_check.py and import from that leaf, or extract a small chat_session_probe_helpers.py only if checker policy admits another helper leaf. _chat_session_probe_uuid_text and _chat_session_probe_ulid_text are tiny stable probe constants; duplicate with a comment or move to a small support helper only if duplication is rejected by local style.",
  "slice_order": [
   "1 axis_vocab_drift_check.py, because it is isolated and carries D3 allowlists.",
   "2 building_plan_graph_check.py, because both runs have no private helper closure.",
   "3 raw_evidence_stream_scrub_check.py and agent_output_text_preservation_check.py, because each run has no private helper closure.",
   "4 building_result_summary_check.py, because helper closure is small and local.",
   "5 brick_cli_entrypoint_check.py, because all D2 pins are confined to one helper cluster.",
   "6 mcp_connect_projection_check.py, because it is late-file and mostly self-contained.",
   "7 agent_session_id_redaction_check.py, after deciding duplicate/import handling for the two chat-session probe helpers.",
   "8 chat_session_park_check.py, before dashboard and adapter-error if shared helpers are centralized there.",
   "9 dashboard_productization_projection_check.py, after chat-session shared-helper disposition.",
   "10 adapter_error_check.py, after chat-session shared-helper disposition.",
   "11 agent_adapter_return_shape_check.py, last among large slices because it is the largest single extraction and carries profile body pins."
  ]
 }
}

