"""compose_building Brick plan assembly (P3d concern module).

Assembles a declared Building Plan from a graph/template intent into Brick rows +
declared Link edges/gate refs, collecting CompositionProblems. It validates and
records; it authors no Movement, invents no route, and judges no success or
quality. Crosses to Link only via the canonical MovementFact/gate-ref contracts
through plan_rendering / building_operation_common. It may read closed axis
vocabularies for validation; it does not own those meanings."""

from __future__ import annotations

import difflib
import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS  # noqa: F401  (facade re-export)
from brick_protocol.link.gate import (
    COO_GATE_REF,
    HUMAN_DISPOSITION_GATE_REFS,
    HUMAN_GATE_REF,
)
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.link.spec import translate_gate_concept
from brick_protocol.support.operator.building_operation_common import (
    COMPACT_LINK_GATE_TOKENS,
    DEFAULT_LINK_GATE_REF,
    REPO_ROOT,
    _clean_text,
    _mapping_value,
    _text_sequence,
)
from brick_protocol.support.operator.primitives import (
    INLINE_TASK_SOURCE_REF,
    INLINE_TASK_STATEMENT_MAX_BYTES,
    NODE_CASTING_FIELDS,
)
from brick_protocol.support.operator.project_declaration import load_project_declaration
from brick_protocol.support.recording.capture import buildings_root_for
from brick_protocol.support.operator.plan_rendering import (
    RETIRED_STEP_TEMPLATE_REFS,
    _clean_selected_adapter_ref,
    _declared_step_from_step_template,
    _is_caller_or_coo_declaration,
    _load_yaml_mapping,
    _load_shape_registry,
    _parse_compact_link_expression,
    _is_verdict_bearing_node,
    _resolve_agent_for_need,
    _resolve_casting_selection,
    _validate_declared_plan_projection,
    render_declared_building_plan,
)
from brick_protocol.support.operator.composition_problem import (
    CompositionError,
    CompositionProblem,
)
from brick_protocol.support.operator.composition_common import (
    ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT,
    _ROUTE_POLICY_PROVENANCE_VALUES,
    _composition_gate_sequence_ref,
    _composition_optional_text,
    _composition_shape_has_field,
    _composition_slug,
    _materializer_step_template_slug,
    _materializer_strip_field,
)
from brick_protocol.support.operator.composition_kinds import (
    _KIND_SYNONYMS,
    _STEP_TEMPLATE_PREFIX,
    _known_kinds,
    _materializer_step_alias,
    _materializer_step_template,
    _unknown_kind_hint,
)
from brick_protocol.support.operator.composition_route_policy import (  # noqa: F401  (facade re-export)
    REROUTE_DEFAULTS_PATH,
    _composition_direct_caller_provenance,
    _composition_node_field_with_provenance_fallback,
    _composition_node_reroute_budgets,
    _composition_resolve_route_policy_provenance,
    _composition_route_policy_provenance,
    _materializer_closure_policy,
    _materializer_constitutional_default_reroute_budget,
    _materializer_preset_closure_policy,
    _materializer_preset_reroute_budgets,
    _materializer_reroute_budget_cascade,
    _materializer_reroute_budgets,
)
from brick_protocol.support.operator.composition_gate_translation import (  # noqa: F401  (facade re-export)
    UNSUPPORTED_MATERIALIZER_TARGET_WORDS,
    _QA_ROLE_NEED,
    _materializer_gate_concept_provenance,
    _materializer_gate_concept_tokens,
    _materializer_human_gate_hold_policy,
    _materializer_profile_gate_translations,
    declared_portfolio_gate_translations,
    stamp_declared_portfolio_closure_gates,
)
from brick_protocol.support.operator.composition_graph_validate import (  # noqa: F401  (facade re-export)
    _CLOSURE_POLICY_HOLD_ACTIONS,
    _CLOSURE_POLICY_REQUIRED_KINDS,
    _CLOSURE_POLICY_TARGET_ACTIONS,
    _composition_author_required_return_shape,
    _composition_closure_policy_problems,
    _composition_edge_records_with_gate_sequence_policy,
    _composition_edges_between_templates,
    _composition_fan_in_target_steps,
    _composition_gate_sequence_link_step,
    _composition_gate_sequence_policy_profile_problems,
    _composition_gate_sequence_profile_steps,
    _composition_gate_sequence_refs,
    _composition_graph_incoming_counts,
    _composition_hard_graph_contract_problems,
    _composition_policy_action,
    _composition_policy_target_ref,
    _composition_problem_from_validator,
    _composition_records_by_endpoint,
    _composition_required_return_shape,
    _composition_step_output_source_facts,
    _composition_validator_problems,
)


GRAPH_CHAIN_TARGET_MARKERS = ("parallel", "fan_in")
# GATE-CONCEPT TRANSLATION (operator-decided wiring, 0610): the materializer
# TRANSLATES the preset's DECLARED ``gate_concept_profile`` tokens into live
# ``declared_gate_refs`` on SPECIFIC rows (mechanical; provenance = the PRESET
# declared the label; no profile -> nothing stamped). The token -> ref map is
# the Link plan grammar, single-sourced in link/spec.py
# (``GATE_CONCEPT_TOKEN_GATE_REFS`` over link.gate.DECLARED_GATE_REFS; E2/S3):
# this support materializer IMPORTS the table + the ``translate_gate_concept``
# reader instead of re-stating either. MODE tokens (default-transition /
# fan-in-wait-all / portfolio-policy) have NO gate ref there on purpose: they are
# not Link gates (fan-in-wait-all = declared graph topology requirement,
# portfolio-policy = driver surface).
# PLACEMENT (operator design rule):
#   * strict-evidence -> link-gate:strict on every QA-row transition (a row
#     whose SOURCE step template declares performer_lane_need == reviewer).
#   * coo-review / human-review -> link-gate:coo / link-gate:human on the
#     FINAL transition row only (the Link row whose target is the closure
#     building boundary).
#   * human-review ALSO carries the canonical single-gate hold policy (below):
#     the EXISTING gate_sequence_policy machinery withholds Movement (HOLD,
#     required_disposition_owner=caller-or-coo) until the human disposition
#     fact (route_decision_basis.human_review_refs) exists. The gate never
#     judges quality/success; sufficiency stays computed by link/gate.py.
#     SCOPE (codex review, 0610): the ONLY hold surface ADDED BY THIS
#     TRANSLATION is the human-token policy. A pre-existing AUTHOR-declared
#     gate_sequence_policy in a preset (e.g. brick-protocol-engine-feature-hard's
#     design->work coo HOLD) is untouched and still holds on its own row.
#   * every stamped row ALSO records machine-readable provenance
#     (gate_concept_provenance: tokens + declared_by preset ref) -- recorded
#     ONLY when translation happened, mirroring the budget/closure-policy
#     provenance stamps below; support never invents provenance.
# (translate_gate_concept is imported from link/spec.py above — the Link single
# source over GATE_CONCEPT_TOKEN_GATE_REFS; support re-states neither.)


from brick_protocol.support.operator.composition_intent import (  # noqa: F401  (facade re-export)
    LINEAR_COMPOSITION_MODE,
    _STEP_SELECTION_OVERRIDE_KEYS,
    _composition_brick_spec_refs,
    _composition_brick_template_refs,
    _materializer_default_building_id,
    _materializer_inline_building_id,
    _materializer_markdown_section,
    _materializer_preset_step_with_selection_override,
    _materializer_project_ref,
    _materializer_reject_unused_step_selection_overrides,
    _materializer_source_facts,
    _materializer_step_selection_overrides,
    _materializer_task_path,
    _materializer_task_source,
    _materializer_task_source_hash_basis,
    _materializer_task_summary,
    _materializer_write_scope,
    inline_task_source_carry,
    materialize_building_intent,
    render_declared_step_template_plan,
)


from brick_protocol.support.operator.composition_graph_emit import (  # noqa: F401  (facade re-export)
    _materializer_apply_route_decision_basis,
    _materializer_declared_graph_declaration,
    _materializer_declared_graph_topology,
    _materializer_gate_sequence_refs_for_edge,
    _materializer_graph_declaration,
    _materializer_graph_edge,
    _materializer_graph_fan_out_index,
    _materializer_graph_node,
    _materializer_graph_plan,
    _materializer_graph_required_return_shape,
    _materializer_link_row_has_gate_ref,
    _materializer_route_decision_basis,
    _materializer_sequential_graph_declaration,
    _materializer_topology_node_handle,
    _materializer_topology_string_list,
)


from brick_protocol.support.operator.composition_compose import (  # noqa: F401  (facade re-export)
    compose_building,
    _composition_chain_preset,
    _chain_preset_step_template_refs,
    _validate_composition_brick_spec_ref,
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
    _composition_edge_movement,
    _composition_link_edge,
    _composition_agent_object_refs,
)
def _chain_preset_requires_graph(preset: Mapping[str, Any]) -> bool:
    if "node_reroute_budgets" in preset:
        return True
    return _chain_preset_requires_fan_in_groups(preset)


def _chain_preset_requires_fan_in_groups(preset: Mapping[str, Any]) -> bool:
    # E1 FULL-LEGO: an explicit graph_topology that DECLARES fan_in_groups needs
    # the same graph-group + hard-graph-contract validation the positional
    # parallel/fan-in markers trigger (the emitted plan must pass the SAME
    # compose_building validators). Absent the key -> unchanged.
    topology = preset.get("graph_topology")
    if isinstance(topology, Mapping):
        fan_in_groups = topology.get("fan_in_groups")
        if (
            isinstance(fan_in_groups, Sequence)
            and not isinstance(fan_in_groups, (str, bytes))
            and fan_in_groups
        ):
            return True
    for raw_step in _chain_preset_steps(preset):
        target_word = str(raw_step.get("target_word", "")).strip().lower()
        if any(marker in target_word for marker in GRAPH_CHAIN_TARGET_MARKERS):
            return True
    gate_concepts = preset.get("gate_concept_profile", ())
    if isinstance(gate_concepts, Sequence) and not isinstance(gate_concepts, (str, bytes)):
        return any("fan-in" in str(item).lower() for item in gate_concepts)
    return False


def _validate_declared_brick_spec_ref(
    raw_step: Mapping[str, Any],
    step_template: Mapping[str, Any],
    *,
    label: str,
) -> None:
    supplied = raw_step.get("brick_spec_ref")
    if supplied is None:
        return
    declared = _clean_text(f"{label}.brick_spec_ref", supplied)
    expected = step_template.get("brick_spec_ref")
    if declared != expected:
        raise ValueError(f"{label}.brick_spec_ref must match the registered single-Brick spec")


def _chain_preset_steps(preset: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    steps = preset.get("steps", ())
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        return ()
    return tuple(step for step in steps if isinstance(step, Mapping))

