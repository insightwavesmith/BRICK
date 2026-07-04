# §4-2 본대 splitmap — case_runners.py 분해 지도 (0704 — cr-splitmap-0704b 수확)

Status: support evidence only. 존 리더 8+소비자 스캐너 fan 파티션 조사의 합성 산출 —
COO 수확·커밋(원문: buildings/cr-splitmap-0704b design 반환). 추출 실행 전 지도이며
source truth·성공 판정·품질 판정·Movement 권한 아님. 슬라이스 발주는 이 지도 기준.

## D1 — 재계수 판정 (합성 독립 재계수)

115 definitions (113 top-level def + 2 class), exactly-once, double-count 0, omission 0 at partition basis; zone top-level sum = 113 = independent recount. No missed zone at the top-level partition. TWO nested-def reporting gaps found (see edge_cases): _budget_int@830 (zone1 under-reported, rides run_materialize_building_intent_case@748) and _open@4326 (zone4 reported nested=0, rides run_native_dispatch_close_case@4234). Nested total 15 = 2(zone1)+4(zone2)+1(zone4)+2(zone5)+3(zone6)+3(zone8).

파티션 기준: 정의 헤더(`^def `/`^class `)가 존 범위에서 시작하는 것만 파티션 단위 —
중첩 def는 부모와 동행(정확히-한-번 규칙). 115 정의 = 113 def + 2 class,
존 합계 17+9+5+14+6+25+26+11 = 113 정확 일치, 이중 0·누락 0.

## D3 — 추출 순서 제안 + 잎 모듈

Lowest-risk first, §4-2-exclusion-sensitive last: (1) adapter_capability_rehome [precedent]; (2) self-contained leaves: workflow_import, wiki_carry, auto_repair_replay, hook_registry_axis, write_scope_default_exclude, agent_packets, once_task_source, plan_expansion, child_building_candidate, fail_fixture_rejects, declared_step_template, adapter_model_selection, route_materialization, plan_validation_guard, onboard_seam, native_dispatch_close; (3) SHARED-infra modules (checker_temp_vessel, gemini_fixture, shared_slug_ref, _optional_non_negative_int) BEFORE their dependents (intake_project_vessel, intake_evidence_projection, preset_completion); (4) §4-2-sensitive carry/materialize/compose LAST: source_fact_body_carry, step_output_drain, materialize_building_intent, compose_BAL. graph_fixture_thin_aliases = MOVE-UNNECESSARY; plan_accessor = SPIN-EXCLUDED.

### D3_leaf_partition_exactly_once
[
 {
  "co_move_consts": "case_runners.py:146-181 module constants",
  "count": 10,
  "def_anchors": [
   "184",
   "209",
   "224",
   "264",
   "281",
   "330",
   "353",
   "385",
   "425",
   "471"
  ],
  "leaf": "checker_temp_vessel (SHARED infra, not a case-runner leaf)",
  "nested": [
   "474"
  ],
  "note": "self-test entries imported at check_profile:87,88; _with_temp_vessel_repo@385 & _temp_vessel_cleanup_or_reject@353 consumed cross-family by intake_project_vessel + intake_evidence_projection — land as shared module FIRST."
 },
 {
  "count": 2,
  "def_anchors": [
   "604",
   "633"
  ],
  "leaf": "adapter_model_selection",
  "rule_keys": [
   "adapter_model_selection_case",
   "adapter_model_selection_rejects"
  ]
 },
 {
  "count": 2,
  "def_anchors": [
   "659",
   "695"
  ],
  "leaf": "route_materialization",
  "rule_keys": [
   "route_materialization_case",
   "transition_concern_disposition_case"
  ]
 },
 {
  "co_move_consts": "_ROUTE_POLICY_PROVENANCE_VALUES@1099-1103",
  "count": 4,
  "def_anchors": [
   "748",
   "1088",
   "1106",
   " 1263"
  ],
  "leaf": "materialize_building_intent (→Batch4 materialize_engine)",
  "nested": [
   "830"
  ],
  "rule_keys": [
   "materialize_building_intent_case",
   "materialize_building_intent_rejects"
  ]
 },
 {
  "count": 5,
  "def_anchors": [
   "1396",
   "3486",
   "3498",
   "3536",
   "3709"
  ],
  "leaf": "preset_completion_portfolio",
  "note": "_preset_slug@3709 rides here; depends on shared _case_slug@3713",
  "rule_keys": [
   "preset_building_completion_case"
  ]
 },
 {
  "count": 1,
  "def_anchors": [
   "1543"
  ],
  "leaf": "gemini_fixture (SHARED util)",
  "note": "6 cross-zone call-sites; land as shared util"
 },
 {
  "count": 4,
  "def_anchors": [
   "1561",
   "1589",
   "1750",
   "1763"
  ],
  "leaf": "intake_adapter_gate",
  "nested": [
   "1687",
   "1896",
   "1925",
   "1936"
  ],
  "rule_keys": [
   "adapter_gate_shape_union_case",
   "building_intake_seam_case"
  ]
 },
 {
  "count": 2,
  "def_anchors": [
   "2308",
   "2317"
  ],
  "leaf": "intake_project_vessel",
  "note": "depends on checker_temp_vessel infra",
  "rule_keys": [
   "intake_project_vessel_case"
  ]
 },
 {
  "count": 1,
  "def_anchors": [
   "2708"
  ],
  "leaf": "onboard_seam",
  "rule_keys": [
   "onboard_seam_case"
  ]
 },
 {
  "co_move_consts": [
   "_AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS@2924",
   "_PRESET_RANKING_FORBIDDEN_PICK_FIELDS@3232"
  ],
  "count": 2,
  "def_anchors": [
   "2952",
   "3257"
  ],

### D3_partition_total_check
"Sum of leaf top-level counts = 113 (verified), classes 2 (once_task_source@5935, step_output_drain@6862), nested 15 all ride parents. Exactly-once holds; no def is in two leaves, none dropped."

### D4_batch_correspondence
"checker-diet-order-plan-0704.md:29-34 batches are §4-4 profile-LABEL groups by engine layer; this §4-2 runner split is a DIFFERENT axis (file-level non-colliding per :19). Correspondence by engine-layer family: Batch1 agent_packets↔{agent_packets, child_building_candidate}; Batch2 declared_step_template↔declared_step_template; Batch3 carry_engine↔{source_fact_body_carry, step_output_drain}; Batch4 materialize_engine↔materialize_building_intent; Batch5 compose_BAL↔compose_BAL. This is a cross-axis family correspondence, NOT a verified 1:1 label→runner map (see not_proven)."

## 불변식 (슬라이스 게이트 — §4-1 표준)

[
 "Definition ledger: 113 top-level def + 2 class = 115, each assigned to exactly one leaf; nested defs ride their enclosing top-level def; double-count 0, omission 0.",
 "Pure move only — no behavior change: ast.dump of each moved def identical before/after.",
 "Every check_profile import name and every RULE_RUNNERS key resolves after the move (re-export shim in case_runners preserves the public surface).",
 "fixture_graph_helpers self-check remains green (graph_fixture_thin_aliases stay put).",
 "`--all` EXIT 0 preserved after each slice (green carry); live inbox fixture count unchanged.",
 "Module-const co-move: each frozenset/const consumed only by one runner moves WITH that runner (else import breaks)."
]

## 경계 사례 (중첩 def 동행·존-경계 걸침)

[
 "Nested-def reporting gap: zone1 under-counted (_budget_int@830, inside run_materialize_building_intent_case@748) and zone4 reported nested=0 but _open@4326 exists (inside run_native_dispatch_close_case@4234). Both are deeper-than-4-space indent, missed by `^    def ` greps. They do NOT change the partition but MUST travel with their parent leaf.",
 "Body-span-crosses-zone-boundary (partition-safe, but the family slice must carry the full body): _check_materialized_route_policy_provenance@1106 (→zone2), run_intake_project_vessel_case@2317 (→zone3), _preset_completion_intent@3498 (→zone4), run_native_dispatch_close_case@4234 (→zone5), run_once_task_source_admission_case@5786 (→zone6), _check_step_output_drain_expected@6946 (→zone7), _plan_expansion_fixture@8178 (→zone8).",
 "Cross-family SHARED helpers (must land in a shared module or stay in case_runners as shared core, extracted BEFORE dependents): _case_slug@3713, _fixture_gemini_api_key@1543, checker_temp_vessel infra (_with_temp_vessel_repo@385, _temp_vessel_cleanup_or_reject@353, _write_temp_vessel_sentinel@264 …), _optional_non_negative_int@6350.",
 "MOVE-UNNECESSARY: _graph_brick_step@7980, _graph_link_edge@8001, _brick_row@8046, _agent_row@8061 (fixture_graph_helpers self-checks against them).",
 "SPIN-EXCLUDED per work_statement: _axis_row@8023, _brick_ref_by_step@8033.",
 "run_casting_node_carry is a re-export (defined in casting_node_carry_check.py), imported at check_profile:90 but NOT in RULE_RUNNERS — dispatched kernel-style; keep the re-export row.",
 "Two classes (_OnceTaskSourceSentinelReached@5935, _StepOutputDrainObserved@6862 with methods @6871/@6877) ride their family leaf, not counted as defs."
]

## 소비자 표면

{
 "consumer_surface": "check_profile.py (40-symbol import :86-127; 39 RULE_RUNNERS keys :240-292; dispatch :1224), fixture_graph_helpers.py (:158-270 self-check), module_registry.yaml (:587), profile YAMLs keyed by rule-name, and run_casting_node_carry re-export hub (case_runners re-exports from casting_node_carry_check.py; dispatched kernel-style, NOT in RULE_RUNNERS).",
 "counting_basis": "Partition unit = a definition whose header (`^def ` or `^class `) starts within the zone's line range. Nested defs (`^\\s+def `, indent>0) are NOT partition units — each rides the top-level def/class that encloses it. This is the exactly-once rule; grep `^def |^    def `=117 is nested-inclusive and is NOT the partition basis.",
 "file": "support/checkers/lib/case_runners.py (9302 lines, wc-equivalent range end :9080 last top-level def)",
 "measured_totals": {
  "four_space_nested": 4,
  "nested_def_any_indent": 15,
  "private_helpers": 76,
  "public_run_case_runners_defined_here": 37,
  "top_level_class": 2,
  "top_level_def": 113,
  "top_level_definitions": 115
 },
 "zone_top_level_sum_reconciliation": {
  "classes_both_in_zone6": [
   "case_runners.py:5935",
   "case_runners.py:6862"
  ],
  "matches_independent_recount": true,
  "sum": 113,
  "zone1[1,1170]": 17,
  "zone2[1171,2340]": 9,
  "zone3[2341,3510]": 5,
  "zone4[3511,4680]": 14,
  "zone5[4681,5850]": 6,
  "zone6[5851,7020]": 25,
  "zone7[7021,8190]": 26,
  "zone8[8191,9302]": 11
 }
}

## not_proven (정직 선언)

[
 "brain surface behavior",
 "credential validity",
 "tool or hook execution",
 "runtime or scheduler behavior",
 "quality of returned work",
 "That any listed def 'has teeth' (behavioral/mutation-RED coverage) — I measured location/count/caller-wiring/consumer-surface only; per-leaf RED witness is Batch-0 work, not performed (repo-mutation + extraction-execution forbidden; map only).",
 "AST purity / slice viability — no extraction was executed, so pure-move AST equivalence and `--all` green after extraction are proposals, not measured results.",
 "D4 §4-4-Batch↔leaf mapping is a cross-axis engine-layer family correspondence, not a verified 1:1 label→runner map; the 87-label profile axis and the 113-def runner axis are distinct.",
 "run_casting_node_carry's exact re-export chain and casting_node_carry_check.py internals were not re-read here (grounded only via check_profile:90 import + module_registry:605).",
 "The two nested-def gaps' full body extents were located by header line only; their enclosing-parent assignment is inferred from indentation + surrounding top-level def, not from a full-body AST parse.",
 "Whether _optional_non_negative_int@6350 / _case_slug@3713 / temp-ves
