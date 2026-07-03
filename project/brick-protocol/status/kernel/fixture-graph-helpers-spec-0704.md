# 공유 픽스처-그래프 헬퍼 통합 스펙 (0704 — sharedhelper-spec-0703a 수확)

Status: support evidence only. §4-2 선행 설계 조사 산출 — COO 수확·커밋(구현 슬라이스의 source_facts용).
**구현자 필독 경고(closure design_gap)**: 두 파일의 link-edge 빌더는 falsy gate 처리에서
갈라진다 — 통합 함수는 이 분기를 파라미터로 보존해야 하며, 순진한 단일화는 행동을 바꾼다.
구현은 아래 commit_sized_order 3단계(공유 모듈 신설→loop0 소비 전환→case_runners 소비 전환)를
각각 별 커밋·별 변이-RED로. kernel_checks.py 무접촉(§4-1 직렬과 충돌 0).

{
 "bounded_inputs": [
  "support/checkers/lib/case_runners.py has 9087 lines; support/checkers/check_bounded_agent_proposed_routing_loop0.py has 8116 lines.",
  "routing-loop0-clustermap-0702.md says loop0 C1 helper zone is extractable but case_runners sharing was not measured there: project/brick-protocol/status/kernel/routing-loop0-clustermap-0702.md:24 and :56-58.",
  "kc-splitmap-draft-0703.md concerns kernel_checks.py splitting; it says extracted checker-lib siblings are flat modules under support/checkers/lib and registry rows use owns_crossings [], consumes_crossings [], imports_axis [], forbidden_ownership [movement_author, target_selector, success_judge, quality_judge, route_invent]: project/brick-protocol/status/kernel/kc-splitmap-draft-0703.md:78."
 ],
 "families": [
  {
   "case_runners": "support/checkers/lib/case_runners.py:8081 _step_output_drain_proof_limits() returns the same five strings; used 6 call sites at :7505, :7567, :7657, :7711, :7857, :7865.",
   "common_machine": "Identical return body: support evidence only / not source truth / not success judgment / not quality judgment / not Movement authority.",
   "family": "proof_limits",
   "file_specific_variation": "Function name only.",
   "integration_assessment": "Integrate first; lowest behavior risk if local aliases preserve old names.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:115 _proof_limits() returns the exact five support-boundary strings; used 8 call sites at :137, :187, :258, :363, :477, :587, :967, :976."
  },
  {
   "case_runners": "support/checkers/lib/case_runners.py:7973 _graph_brick_step(step_ref, brick_ref, completion_edge_ref, source_facts=None, step_template_ref='') emits selected_adapter_ref 'adapter:local', rows from _brick_row at :8055 and _agent_row at :8073, and optional step_template_ref. _brick_row hard-codes step-output-drain work_statement and required_return_shape 'body_marker, source_fact_body_refs, carried_markers, not_proven'; _agent_row hard-codes agent-object:coo. _graph_brick_step has 25 call sites; _brick_row and _agent_row each have 2 helper call sites.",
   "common_machine": "Graph step dictionary with step_ref, completion_edge_ref, Brick row fields, and Agent row fields.",
   "family": "Brick and Agent row/step builders",
   "file_specific_variation": "selected_adapter_ref emission, source_facts default, work_statement, required_return_shape, step_template_ref, and agent_object_ref must stay caller-controlled.",
   "integration_assessment": "Integrate as parameterized primitives only; do not bake either file's defaults into the shared helper.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:67 _brick_step(step_ref, brick_ref, agent_ref, completion_edge_ref) emits step_ref, completion_edge_ref, Brick row, and Agent row; Brick row hard-codes work_statement 'Declared work for ...', required_return_shape 'observed_evidence, not_proven', source_facts ['AGENTS.md', 'support/operator/dynamic_walker.py']; Agent row takes caller-supplied agent_ref. 43 call sites."
  },
  {
   "case_runners": "support/checkers/lib/case_runners.py:7995 _graph_link_edge(edge_ref, source_step_ref, target_step_ref, target_ref, movement='forward', route_replay_plan=None, declared_gate_refs=None) covers forward/reroute, optional route_replay_plan, default declared_gate_refs, and blank target_step_ref as closed lifecycle with fixed reason. 38 call sites.",
   "common_machine": "Edge dict with edge_ref, source_step_ref, optional target_step_ref, and one Link row containing row_ref, movement, target_ref, declared_gate_refs, and optional route_replay_plan/building_lifecycle.",
   "family": "Link edge builders",
   "file_specific_variation": "loop0 separates wrappers and caller close reason; case_runners folds variants into one helper and fixes close reason.",
   "integration_assessment": "Integrate with a general helper accepting close_reason and nullable target_step_ref; keep thin loop0 aliases first to preserve emitted dictionaries.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:87 _fwd_edge(...) is forward-only with required target_step_ref; :98 _close_edge(...) omits target_step_ref and adds building_lifecycle closed with caller reason; :822 _reroute_edge(...) emits movement reroute plus route_replay_plan. Call sites: _fwd_edge 46, _close_edge 7, _reroute_edge 1."
  },
  {
   "case_runners": "support/checkers/lib/case_runners.py:7474 dispatches step-output-drain cases to builders at :7494, :7558, :7641, :7705, :7840; they build linear-to-graph, fan-in, QA reroute, source concern, and replay plans.",
   "common_machine": "Plan envelope fields: plan_ref, building_id, plan_shape graph, selected_adapter_ref adapter:local, proof_limits, not_proven, execution_order, brick_steps, link_edges, optional groups and node_reroute_budgets.",
   "family": "Graph plan builders",
   "file_specific_variation": "Topology and scenario intent differ materially.",
   "integration_assessment": "Exclude whole plan builders from first extraction; optional envelope helper only after primitive conversion is byte-preserving.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:125, :174, :243, :334, :431, :535, :944 build loop0-specific checker/fan/cohort/nested/replay graph plans with node_reroute_budgets, groups, sibling_independence, and route_replay_plan cases."
  },
  {
   "case_runners": "support/checkers/lib/case_runners.py:6743 _run_step_output_drain_plan monkeypatches evidence_assembly.write_step_outputs to count calls, runs timeout 10 with observed.callable, restores the monkeypatch, and returns result plus call count.",
   "common_machine": "run_building_plan with output_root, overwrite_existing=True, local_callables {'callable:local:agent-invoke0-smoke': callable}, adapter_cwd=repo, bounded timeout.",
   "family": "run_building_plan wrappers",
   "file_specific_variation": "case_runners owns write-count monkeypatch; loop0 owns frontier/reroute/carry-trace/fanout/resume/park behavior.",
   "integration_assessment": "Only a very small run-local-fixture core is integrable; keep wrappers local unless later tests prove no value loss.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:1102 _run uses TemporaryDirectory, run_building_plan timeout 30, observe_building_frontier, reroute records, and carry trace; :1132 _run_to_output_root takes caller output_root; :1159/:1178/:1216 wrap fanout pool and resume/park cases."
  },
  {
   "case_runners": "support/checkers/lib/case_runners.py:6855 _StepOutputDrainObserved and :6870 callable record source_fact_body_refs, carried markers, link_handoff_refs, optional concern fixtures, and body text at call.",
   "common_machine": "Adapter-local callable receives request and returns support evidence plus optional transition_concern_evidence.",
   "family": "callable factories / observed callables",
   "file_specific_variation": "Returned body contracts and side observations differ.",
   "integration_assessment": "Exclude from first extraction except possibly a later tiny transition-concern dictionary helper.",
   "loop0": "support/checkers/check_bounded_agent_proposed_routing_loop0.py:643-810 contains concern/adoption/rejection/adapter-error callable factories."
  }
 ],
 "section": "D1_measured_comparison"
}

{
 "explicit_exclusions": [
  "Do not integrate whole graph plan builders in the first slice.",
  "Do not integrate callable factories / _StepOutputDrainObserved in the first slice.",
  "Do not move _axis_row and _brick_ref_by_step; they are case_runners-local inspection helpers at :8032 and :8042 with no loop0 counterpart in the measured family.",
  "Do not touch support/checkers/lib/kernel_checks.py in this slice; kc-splitmap status is separate and kernel_checks split work has its own v2 partition evidence."
 ],
 "functions": [
  {
   "absorbs": "loop0 _proof_limits at :115 and case_runners _step_output_drain_proof_limits at :8081.",
   "defaults": "No parameters.",
   "estimated_consumer_changes": "case_runners 6 call sites plus optional local alias; loop0 8 call sites plus optional local alias.",
   "signature": "fixture_proof_limits() -> list[str]"
  },
  {
   "absorbs": "loop0 inline Brick row in _brick_step at :67-84 and case_runners _brick_row at :8055.",
   "defaults": "source_facts defaults to [] only when caller passes None; work_statement and required_return_shape must be explicit to prevent cross-file default drift.",
   "estimated_consumer_changes": "case_runners 2 helper-internal call sites; loop0 conversion through fixture_graph_brick_step affects 43 step call sites indirectly.",
   "signature": "fixture_brick_row(step_ref: str, brick_ref: str, *, work_statement: str, required_return_shape: str, source_facts: Sequence[str] | None = None, comparison_rule: str = 'Observe support evidence only; do not choose Movement or judge quality.') -> Mapping[str, Any]"
  },
  {
   "absorbs": "loop0 inline Agent row at :83 and case_runners _agent_row at :8073.",
   "defaults": "No agent default in shared helper; case_runners may keep local _agent_row alias with agent-object:coo.",
   "estimated_consumer_changes": "case_runners 2 helper-internal call sites; loop0 conversion through fixture_graph_brick_step affects 43 step call sites indirectly.",
   "signature": "fixture_agent_row(step_ref: str, *, agent_object_ref: str) -> Mapping[str, Any]"
  },
  {
   "absorbs": "loop0 _brick_step at :67 and case_runners _graph_brick_step at :7973.",
   "defaults": "selected_adapter_ref None omits the field for loop0 byte preservation; 'adapter:local' reproduces case_runners. step_template_ref empty omits field.",
   "estimated_consumer_changes": "case_runners 25 graph step call sites can stay behind local alias first; loop0 43 call sites can stay behind local alias first.",
   "signature": "fixture_graph_brick_step(step_ref: str, brick_ref: str, completion_edge_ref: str, *, agent_object_ref: str, work_statement: str, required_return_shape: str, source_facts: Sequence[str] | None = None, selected_adapter_ref: str | None = None, step_template_ref: str = '') -> Mapping[str, Any]"
  },
  {
   "absorbs": "loop0 _fwd_edge :87, _close_edge :98, _reroute_edge :822, and case_runners _graph_link_edge :7995.",
   "defaults": "declared_gate_refs None expands to ['link-gate:default-transition']; target_step_ref empty omits target_step_ref; close_reason must be supplied for loop0 close alias and defaults to case_runners fixed reason only in a case_runners alias, not the shared primitive.",
   "estimated_consumer_changes": "case_runners 38 edge call sites can stay behind local alias first; loop0 46 forward, 7 close, and 1 reroute call sites can stay behind local aliases first.",
   "signature": "fixture_graph_link_edge(edge_ref: str, source_step_ref: str, target_ref: str, *, target_step_ref: str = '', movement: str = 'forward', route_replay_plan: Mapping[str, Any] | None = None, declared_gate_refs: Sequence[str] | None = None, close_reason: str | None = None) -> Mapping[str, Any]"
  },
  {
   "absorbs": "Only common plan shell shape, not scenario topology.",
   "defaults": "Omit optional groups/node_reroute_budgets when None to preserve current dictionaries.",
   "estimated_consumer_changes": "Second slice only; affects multiple plan builders but should not be part of the first primitive extraction.",
   "signature": "fixture_graph_plan_envelope(*, plan_ref: str, building_id: str, execution_order: Sequence[str], brick_steps: Sequence[Mapping[str, Any]], link_edges: Sequence[Mapping[str, Any]], proof_limits: Sequence[str] | None = None, not_proven: Sequence[str] | None = None, groups: Sequence[Mapping[str, Any]] | None = None, node_reroute_budgets: Mapping[str, int] | None = None, selected_adapter_ref: str = 'adapter:local') -> Mapping[str, Any]"
  },
  {
   "absorbs": "Only the shared run_building_plan call core from loop0 :1102/:1132 and case_runners :6743.",
   "defaults": "No timeout default in shared helper; callers pass 30 for loop0 and 10 for case_runners.",
   "estimated_consumer_changes": "Optional later slice; loop0 wrapper call sites remain 32+ and case_runners _run_step_output_drain_plan remains because local side observations differ.",
   "signature": "run_local_fixture_plan(plan: Mapping[str, Any], callable_, repo: Path, *, output_root: Path, adapter_timeout_seconds: int) -> Any"
  }
 ],
 "name_basis": "The helpers are fixture graph primitives, not checker assertions or axis-owned graph meaning; the name avoids claiming Link/Brick ownership and matches existing flat checker-lib sibling convention in module_registry.yaml:577 and :667-745.",
 "proposed_module": "support/checkers/lib/fixture_graph_helpers.py",
 "registry_row_needed": "Add one module_registry.yaml row matching checker-lib siblings: layer checkers/lib, role checker-lib, owns_crossings [], consumes_crossings [], imports_axis [], forbidden_ownership [movement_author, target_selector, success_judge, quality_judge, route_invent], decomposition_target '', pinned_by bounded_agent_proposed_routing_loop plus route_materialization / compose_building fixture graph helper consumers.",
 "section": "D2_integration_spec"
}

{
 "commit_sized_order": [
  "1. Add support/checkers/lib/fixture_graph_helpers.py with fixture_proof_limits, fixture_brick_row, fixture_agent_row, fixture_graph_brick_step, and fixture_graph_link_edge only; add module_registry.yaml row. No consumers changed in this commit.",
  "2. Convert loop0 local helpers into thin aliases/wrappers over the shared module: _proof_limits, _brick_step, _fwd_edge, _close_edge, _reroute_edge. Keep emitted dictionaries byte-equivalent, especially omitted selected_adapter_ref and caller close reason.",
  "3. Convert case_runners local helpers into thin aliases/wrappers over the shared module: _step_output_drain_proof_limits, _brick_row, _agent_row, _graph_brick_step, _graph_link_edge. Keep selected_adapter_ref adapter:local, fixed close reason, optional step_template_ref, and blank target_step_ref behavior.",
  "4. Only after probes and profile runs, consider fixture_graph_plan_envelope. Do not include run_local_fixture_plan until a separate wrapper-value review says the monkeypatch/frontier/fanout behavior remains explicit."
 ],
 "kernel_checks_conflict_check": "The proposed slice creates support/checkers/lib/fixture_graph_helpers.py and converts support/checkers/check_bounded_agent_proposed_routing_loop0.py plus support/checkers/lib/case_runners.py consumers only. kc-splitmap-draft-0703.md is about support/checkers/lib/kernel_checks.py split leaves; no kernel_checks.py edit is needed for this helper slice.",
 "mutation_red_probe_points": [
  "For fixture_proof_limits, mutate one returned string and expect bounded_agent_proposed_routing_loop and step-output-drain profile coverage to detect changed support proof-limit text.",
  "For fixture_graph_brick_step, probe loop0 byte preservation by comparing _brick_step('s','b','agent-object:qa','e') before/after: no selected_adapter_ref field, source_facts remain ['AGENTS.md','support/operator/dynamic_walker.py'], required_return_shape remains 'observed_evidence, not_proven'.",
  "For case_runners _graph_brick_step, compare before/after: selected_adapter_ref remains adapter:local, _agent_row remains agent-object:coo, step_template_ref is omitted when empty and present when non-empty.",
  "For fixture_graph_link_edge, probe loop0 close edge: target_step_ref remains omitted, building_lifecycle reason remains caller-supplied; probe case_runners blank target_step_ref: reason remains 'checker live step-output drain close'.",
  "For reroute edge, probe route_replay_plan is copied into Link row and movement remains reroute only where existing callers pass reroute."
 ],
 "risk_list": [
  "High drift risk if shared helper supplies default work_statement, required_return_shape, or agent_object_ref; make these explicit or keep local aliases.",
  "High drift risk if selected_adapter_ref is always emitted; loop0 currently omits it in _brick_step.",
  "Medium drift risk if close reason is centralized; loop0 and case_runners intentionally differ.",
  "Medium risk from broad consumer churn: prefer local alias conversion first, then call-site cleanup later.",
  "Low conflict risk with §4-1 kernel_checks split if kernel_checks.py is untouched."
 ],
 "section": "D3_implementation_order_input"
}

## closure 경고(design_gap): transition-concern:fixture-graph-link-edge-gate-falsy-divergence-0703
reason_refs : ["observation:fwd-edge-reroute-edge-gate-or-default-vs-case-runners-is-not-none"]
not_proven : ["whether a future implementer would actually make this mistake", "runtime behavior of a shared module that does not yet exist"]
