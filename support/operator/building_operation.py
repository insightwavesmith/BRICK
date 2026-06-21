"""Operator helper mechanics for Brick Protocol Building operation (THIN FACADE).

This module helps a COO/operator inspect a declared Building Plan, run an
allowlisted checker profile, summarize evidence roots, draft support-only
closure material, render declared plans, and record a native subagent dispatch.
It is not a runner, not a Movement chooser, not source truth, not success
judgment, not quality judgment, and not commit/push automation.

ELEGANT-REFACTOR P3d (engine blueprint 0531 §5 Opt 2 / detail-design §D-1): this
module was the LARGEST god-module (~4021 LOC) and mixed ~9 axis crossings
(frontier/ledger projection, evidence presence, compose_building plan assembly,
declared-plan rendering, COO operating-chain/closure projection, orchestration
packet, native-dispatch open/close) plus axis-internal reach in ONE file. Its
single-concern parts were lifted into collaborator modules under
``support/operator/`` (one concern per module, each a registered
module_registry.yaml row, G4) and this module is now the THIN READ-PROJECTION
FACADE: it re-exports every previously-public name so external importers
(driver.py / reporter.py observe_building_frontier; the checker lib case runners
compose_building / render_declared_step_template_plan / observe_building_frontier
/ CompositionError; mcp_projection's coo_operating_chain_packet reference) keep
importing the SAME names from the SAME path. It homes NO crossing mechanics any
more (owns_crossings lowered 9 -> 0); the agent/performance + link/movement +
link/transition axis imports moved into the native_dispatch / plan_rendering
collaborators that cross via the canonical contract (G3). The G6 ceiling
``bo-god-0`` records that current 0-crossing ceiling (a self-consistency check,
not a one-way ratchet — see check_axis_crossing_elegance G6 proof-limit).

Collaborator sublayer (each a registered module_registry.yaml row, G4):
  operator/building_operation_common.py  shared path/JSON/text + default refs
  operator/checker_runner.py             allowlisted checker-profile subprocess
  operator/evidence_status.py            evidence presence / mechanical analysis
  operator/frontier_observation.py       Building frontier observation
  operator/ledger_projection.py          project orchestration-ledger read + view
  operator/coo_operating_chain.py        COO operating-chain / operator-loop / closure
  operator/plan_rendering.py             declared-plan rendering from step templates
  operator/composition_*.py              compose_building Brick plan assembly family
  operator/orchestration_packet.py       coo_run_orchestration read packet
  operator/native_dispatch.py            POSITION-A native-dispatch open/close seam

It chooses no Movement and judges no success or quality.
"""

from __future__ import annotations

# Shared path/JSON/text helpers + default refs.
from brick_protocol.support.operator.building_operation_common import (
    REPO_ROOT,
    DEFAULT_BUILDINGS_ROOT,
    COMPACT_LINK_GATE_TOKENS,
    DEFAULT_LINK_GATE_REF,
    _repo_path,
    _rel,
    _clean_text,
    _read_json_mapping,
    _jsonl_records,
    _list_count,
    _text_sequence,
    _mapping_value,
)

# Allowlisted checker-profile subprocess invocation.
from brick_protocol.support.operator.checker_runner import (
    DEFAULT_CHECKER_PROFILE,
    FORBIDDEN_COMMAND_PARTS,
    BuildingPreflight,
    CheckerRun,
    open_preflight,
    checker_profile,
    run_checker_profile,
    _validate_checker_command,
    _normalize_repo_args,
    _excerpt,
)

# Evidence presence + mechanical analysis read projection.
from brick_protocol.support.operator.evidence_status import (
    REQUIRED_EVIDENCE_FILES,
    DECLARATION_EVIDENCE_FILES,
    DECLARATION_EVIDENCE_MARKER_FILES,
    FRONTIER_EVIDENCE_FILES,
    EvidenceStatus,
    BuildingEvidenceAnalysis,
    evidence_status,
    _evidence_required_files_for_root,
    _declaration_evidence_marker_present,
    _complete_marker_present,
    _frontier_marker_present,
    analyze_building_evidence,
    evidence_analysis_packet,
    building_index_packet,
    _line_count,
    _fact_count,
    _graph_counts,
    _mechanical_gap_flags,
)

# Building frontier observation (the driver/reporter/case-runner import).
from brick_protocol.support.operator.frontier_observation import (
    observe_building_frontier,
    _latest_transition_lifecycle_record,
    _latest_building_lifecycle_state,
    _closed_boundary_observed,
    _is_closed_boundary_ref,
)

# Project orchestration-ledger read projection + read-only view.
from brick_protocol.support.operator.ledger_projection import (
    project_orchestration_ledger_packet,
    PROJECT_ORCHESTRATION_LEDGER_EXPORT,
    render_project_orchestration_ledger_view,
    _ledger_view_cell,
    _project_orchestration_ledger_row,
    _latest_mapping,
    _project_ledger_board_state,
    _project_ledger_next_action,
    _project_ledger_link_disposition,
    _project_ledger_last_evidence_at,
    _parse_evidence_timestamp,
)

# COO operating-chain / operator-loop / closure read projection.
from brick_protocol.support.operator.coo_operating_chain import (
    COO_OPERATING_CHAIN_REQUIRED_TASK_HEADINGS,
    COO_OPERATING_CHAIN_HONEST_REPORT_FIELDS,
    COO_OPERATING_CHAIN_DEEP_INTAKE_FIELDS,
    COO_OPERATING_CHAIN_FORBIDDEN_VERDICT_FIELDS,
    COO_OPERATING_CHAIN_MCP_RESOURCE_URI,
    COO_OPERATING_CHAIN_MCP_TOOL,
    TASK_SOURCE_TEMPLATE_REF,
    closure_draft,
    gap_note,
    operator_loop_packet,
    coo_operating_chain_packet,
    observe_task_source_placement,
    _safe_design_context,
    _safe_coo_agent_packet,
    _coo_operating_chain_mcp_observation,
    _forbidden_verdict_hits,
    _section_text,
    _coo_operating_chain_gap_notes,
    _operator_loop_gap_notes,
)

# Declared-plan rendering from step templates.
from brick_protocol.support.operator.plan_rendering import (
    SPLIT_SHAPE_CATALOG_PATH,
    CALLER_OR_COO_DECLARATION_MARKERS,
    render_declared_building_plan,
    _declared_step_from_step_template,
    _parse_compact_link_expression,
    _compact_target_ref,
    _lookup_declared_step_template,
    _load_shape_registry,
    _store_step_template,
    _is_caller_or_coo_declaration,
    _intent_uses_step_templates,
    _validate_declared_plan_projection,
    _render_declared_step,
)

# compose_building Brick plan assembly (the case-runner import surface).
from brick_protocol.support.operator.composition_problem import (
    CompositionProblem,
    CompositionError,
)
from brick_protocol.support.operator.composition_intent import (
    materialize_building_intent,
    render_declared_step_template_plan,
)
from brick_protocol.support.operator.composition_compose import (
    compose_building,
    _composition_node_items,
    _composition_node_id,
    _composition_step_ref,
    _composition_brick_row,
    _composition_default_brick_ref,
    _composition_endpoint,
    _composition_terminal_target,
    _composition_declared_gate_refs,
    _composition_gate_text,
    _composition_edge_ref,
    _composition_link_edge,
    _composition_agent_object_refs,
)
from brick_protocol.support.operator.composition_common import (
    _composition_slug,
    _composition_optional_text,
)
from brick_protocol.support.operator.composition_route_policy import (
    _composition_node_reroute_budgets,
)
from brick_protocol.support.operator.composition_graph_validate import (
    _composition_validator_problems,
    _composition_problem_from_validator,
)

# coo_run_orchestration read packet.
from brick_protocol.support.operator.orchestration_packet import (
    coo_run_orchestration_packet,
    _orchestration_gap_notes,
    _step_output_refs_from_building_map,
    _link_decision_refs_from_building_map,
)

# POSITION-A native-dispatch open/close recording seam.
from brick_protocol.support.operator.native_dispatch import (
    NATIVE_DISPATCH_EXECUTION_PATH,
    NATIVE_DISPATCH_DEFAULT_GATE_REFS,
    NATIVE_DISPATCH_PROOF_LIMITS,
    _NATIVE_DISPATCH_FORBIDDEN_AGENT_OBJECT_KEYS,
    NativeDispatchBrickHandle,
    open_native_dispatch_brick,
    close_native_dispatch_brick,
    set_brick_context,
    clear_brick_context,
    read_brick_context,
    native_dispatch_child_building_id,
    NATIVE_DISPATCH_HARNESS_CONTENT_KEYS,
    returned_value_from_harness_payload,
    _native_dispatch_step_fixture,
    _native_dispatch_agent_object,
    _validate_native_dispatch_agent_object,
    _optional_text_array,
    _native_dispatch_proof_limits,
    _manifest_native_not_proven,
    _empty_lifecycle_write,
    _empty_map_write,
    _write_native_dispatch_task,
)

# P3d-FIX (codex P2): the pre-decomposition module had NO __all__, so
# `from building_operation import *` exposed all 28 public top-level names. A
# 10-name __all__ silently narrowed that star-import surface (direct imports
# were preserved, but the "0 public names dropped" claim was star-import-false).
# Restore the full 28-name surface so star-import is behavior-identical; every
# name resolves from the facade re-exports above.
__all__ = [
    "BuildingEvidenceAnalysis",
    "BuildingPreflight",
    "CheckerRun",
    "CompositionError",
    "CompositionProblem",
    "EvidenceStatus",
    "NativeDispatchBrickHandle",
    "analyze_building_evidence",
    "building_index_packet",
    "checker_profile",
    "close_native_dispatch_brick",
    "closure_draft",
    "compose_building",
    "coo_operating_chain_packet",
    "coo_run_orchestration_packet",
    "evidence_analysis_packet",
    "evidence_status",
    "gap_note",
    "observe_building_frontier",
    "observe_task_source_placement",
    "open_native_dispatch_brick",
    "set_brick_context",
    "clear_brick_context",
    "read_brick_context",
    "native_dispatch_child_building_id",
    # B4-REPAIR (0611): harness tool-result envelope -> returned value boundary
    # the close hooks call (tolerant envelope, closed return record unchanged).
    "NATIVE_DISPATCH_HARNESS_CONTENT_KEYS",
    "returned_value_from_harness_payload",
    "open_preflight",
    "operator_loop_packet",
    "project_orchestration_ledger_packet",
    "materialize_building_intent",
    "render_declared_building_plan",
    "render_declared_step_template_plan",
    "render_project_orchestration_ledger_view",
    "run_checker_profile",
    # CLOSE-1/F1: base (6a58dd2) building_operation.py had 51 public top-level
    # names; the post-decompose __all__ kept only the 28 functions/classes and
    # dropped these 23 public CONSTANTS, silently narrowing `import *`. Restored
    # so the star-import surface matches base (all re-export from split modules).
    "CALLER_OR_COO_DECLARATION_MARKERS",
    "COMPACT_LINK_GATE_TOKENS",
    "COO_OPERATING_CHAIN_DEEP_INTAKE_FIELDS",
    "COO_OPERATING_CHAIN_FORBIDDEN_VERDICT_FIELDS",
    "COO_OPERATING_CHAIN_HONEST_REPORT_FIELDS",
    "COO_OPERATING_CHAIN_MCP_RESOURCE_URI",
    "COO_OPERATING_CHAIN_MCP_TOOL",
    "COO_OPERATING_CHAIN_REQUIRED_TASK_HEADINGS",
    "DECLARATION_EVIDENCE_FILES",
    "DECLARATION_EVIDENCE_MARKER_FILES",
    "DEFAULT_BUILDINGS_ROOT",
    "DEFAULT_CHECKER_PROFILE",
    "DEFAULT_LINK_GATE_REF",
    "FORBIDDEN_COMMAND_PARTS",
    "FRONTIER_EVIDENCE_FILES",
    "NATIVE_DISPATCH_DEFAULT_GATE_REFS",
    "NATIVE_DISPATCH_EXECUTION_PATH",
    "NATIVE_DISPATCH_PROOF_LIMITS",
    "PROJECT_ORCHESTRATION_LEDGER_EXPORT",
    "REPO_ROOT",
    "REQUIRED_EVIDENCE_FILES",
    "SPLIT_SHAPE_CATALOG_PATH",
    "TASK_SOURCE_TEMPLATE_REF",
]
