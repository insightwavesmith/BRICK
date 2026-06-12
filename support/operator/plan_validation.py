"""Building Plan row and Link declaration validation helpers.

This module validates declared Brick / Agent / Link rows and caller-supplied
Link facts. It never chooses Movement or targets.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from brick_protocol.brick.comparison import BrickComparisonFact
from brick_protocol.brick.work import parse_required_return_shape
from brick_protocol.link.carry import make_carry_fact
from brick_protocol.link.gate import gate_required_return_fields, make_gate_fact
from brick_protocol.link.movement import (
    MOVEMENT_LITERALS,
    MovementFact,
    make_movement_fact,
)
from brick_protocol.link.transfer import make_transfer_fact
from brick_protocol.link.transition import (
    BUILDING_LIFECYCLE_STATES as _BUILDING_LIFECYCLE_STATES,
    DISPOSITION_ACTIONS as _DISPOSITION_ACTIONS,
    TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES as _TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES,
    TransitionFact,
    make_transition_fact,
)
from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
    MinimalCrossingRecord,
)
from brick_protocol.support.operator.primitives import (
    INLINE_TASK_SOURCE_REF,
    _BUILDING_LIFECYCLE_ALLOWED_KEYS,
    _BUILDING_LIFECYCLE_KEY,
    _DECLARED_GATE_REFS,
    _DECLARED_GATE_REFS_KEY,
    _GATE_SEQUENCE_POLICY_KEY,
    _RETURN_FORBIDDEN_KEYS,
    _ROUTE_DECISION_BASIS_ALLOWED_KEYS,
    _ROUTE_DECISION_BASIS_KEY,
    _ROUTE_REASON_ALLOWED_PUBLIC_FACT_PREFIXES,
    _ROUTE_REPLAY_ALLOWED_AUTHOR_PREFIXES,
    _ROUTE_REPLAY_ALLOWED_KEYS,
    _ROUTE_REPLAY_FORBIDDEN_KEYS,
    _ROUTE_REPLAY_FORBIDDEN_VALUE_MARKERS,
    _ROUTE_REPLAY_PLAN_KEY,
    _SESSION_CONTINUITY_REQUEST_FIELDS,
    _TRANSITION_AUTHORING_ALLOWED_KEYS,
    _TRANSITION_AUTHORING_KEY,
    _TRANSITION_LIFECYCLE_ALLOWED_KEYS,
    _TRANSITION_LIFECYCLE_DISPOSITION_OWNERS,
    _TRANSITION_LIFECYCLE_KEY,
    _TRANSITION_LIFECYCLE_PROGRESS_STATES,
    _TRANSITION_LIFECYCLE_STATES,
    evidence_list_has_repository_artifact_ref,
    _looks_like_agent_endpoint,
    _mapping,
    _merge_texts,
    _normalize_key,
    _optional_text,
    _optional_text_from_mapping,
    _optional_text_or_none,
    _optional_text_value,
    _path_segment,
    _require_mapping_value,
    _require_only_keys,
    _required_text,
    _resource_slug,
    _text_tuple,
    _validate_no_payload_forbidden,
)
from brick_protocol.support.connection.agent_adapter import _OBSERVED_WRITE_ADAPTER_REFS

_ARTIFACT_GROUNDING_REVIEW_FIELD = "evidence_used"
_ARTIFACT_GROUNDING_DESIGN_FIELD = "evidence_refs"
_ARTIFACT_GROUNDING_REVIEW_FACT = "evidence_used.repository_artifact_ref"
_ARTIFACT_GROUNDING_DESIGN_FACT = "evidence_refs.repository_artifact_ref"

_GATE_SEQUENCE_STEP_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "gate_ref",
        "on_missing_required_facts",
        "on_sufficient",
        "proof_limits",
        "not_proven",
    }
)
_GATE_SEQUENCE_ACTION_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "action",
        "target_basis",
        "target_ref",
        "required_target_budget",
        "required_disposition_owner",
        "pending_target_basis",
        "pending_target_ref",
        "next_gate_ref",
        "reason_refs",
        "proof_limits",
        "not_proven",
    }
)
_GATE_SEQUENCE_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "chosen_target",
        "movement",
        "movement_choice",
        "quality",
        "route_choice",
        "success",
        "target",
        "targets",
        "verdict",
    }
)
_GATE_SEQUENCE_TARGET_BASIS = frozenset({"source_brick", "target_brick"})
_CODEX_LOCAL_ADAPTER_REF = "adapter:codex-local"
_RETIRED_WRITE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
    }
)


def _plan_building_id(plan: Mapping[str, Any], plan_ref: str) -> str:
    explicit = _optional_text_from_mapping(plan, "building_id")
    if explicit:
        return _path_segment("building_id", explicit)
    slug_source = plan_ref.removeprefix("building-plan:")
    return _path_segment("building_id", _resource_slug("plan_ref", slug_source))

def _step_fixture_from_plan_step(
    plan: Mapping[str, Any],
    step: Mapping[str, Any],
    index: int,
    *,
    building_id: str | None = None,
    incoming_link_handoff_refs: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Building Plan step must contain exactly three rows")
    movement, target = _declared_movement_and_target(step)
    step_ref = _optional_text_from_mapping(step, "step_ref") or f"step-{index + 1:02d}"
    plan_ref = _optional_text_from_mapping(plan, "plan_ref") or "building-plan:anonymous"
    step_building_id = building_id or _optional_text_from_mapping(step, "building_id")
    if step_building_id is None:
        step_building_id = (
            f"{_path_segment('plan_ref', plan_ref.removeprefix('building-plan:'))}-{index + 1:02d}"
        )
    if "selected_adapter_ref" in step:
        selected_adapter_value = step.get("selected_adapter_ref")
    else:
        selected_adapter_value = plan.get("selected_adapter_ref")
    if selected_adapter_value is None:
        raise ValueError("Building Plan step or plan must declare selected_adapter_ref")
    selected_adapter_ref = _required_text("selected_adapter_ref", selected_adapter_value)
    selected_model_ref = step.get("selected_model_ref") or plan.get("selected_model_ref")
    task_source_ref = _task_source_ref_from_plan(plan)
    fixture_rows = _step_rows_with_declared_next_target(rows, target)
    caller_link_facts = _step_caller_supplied_link_facts(
        step,
        movement=movement,
        target=target,
        plan_ref=plan_ref,
        step_ref=step_ref,
        not_proven=_merge_texts(plan.get("not_proven"), step.get("not_proven")),
    )
    step_fixture: dict[str, Any] = {
        "building_id": step_building_id,
        "step_ref": step_ref,
        "step_index": index + 1,
        "step_rows": {
            "step_ref": step_ref,
            "rows": fixture_rows,
            "proof_limits": step.get("proof_limits") or plan.get("proof_limits"),
        },
        "selected_adapter_ref": selected_adapter_ref,
        "selected_model_ref": selected_model_ref or "",
        "caller_supplied_link_facts": caller_link_facts,
        "raw_refs": _merge_texts(plan.get("raw_refs"), step.get("raw_refs")),
        "link_handoff_refs": incoming_link_handoff_refs or {},
        "proof_limits": step.get("proof_limits") or plan.get("proof_limits"),
        "not_proven": _merge_texts(plan.get("not_proven"), step.get("not_proven")),
    }
    if task_source_ref is not None:
        step_fixture["task_source_ref"] = task_source_ref
        if task_source_ref == INLINE_TASK_SOURCE_REF:
            # TASK-BY-TEXT (0611): the inline statement rides the plan, not a
            # file -- thread it onto the step fixture so the adapter request's
            # source-fact body carry can deliver the task body to the Agent
            # (parity with the file flow, where _source_fact_bodies reads the
            # declared file). _task_source_ref_from_plan above already
            # rejected a sentinel ref without a non-empty statement body.
            step_fixture["task_statement"] = plan.get("task_statement")
    if "agent_objects" in plan:
        step_fixture["agent_objects"] = plan["agent_objects"]
    if "agent_objects" in step:
        step_fixture["agent_objects"] = step["agent_objects"]
    for key in _SESSION_CONTINUITY_REQUEST_FIELDS:
        value = step.get(key) if key in step else plan.get(key)
        if value is not None:
            step_fixture[key] = value
    return step_fixture

def _step_caller_supplied_link_facts(
    step: Mapping[str, Any],
    *,
    movement: str,
    target: str,
    plan_ref: str,
    step_ref: str,
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    supplied = step.get("caller_supplied_link_facts")
    if supplied is None:
        supplied_mapping: Mapping[str, Any] = {}
    else:
        supplied_mapping = _mapping("step.caller_supplied_link_facts", supplied)
    movement_fact = _declared_step_movement_fact(
        supplied_mapping.get("movement_fact"),
        movement=movement,
        target=target,
        plan_ref=plan_ref,
        step_ref=step_ref,
    )
    transition_fact = _declared_step_transition_fact(
        supplied_mapping.get("transition_fact"),
        movement=movement,
        target=target,
        step_ref=step_ref,
        not_proven=not_proven,
    )
    caller_facts: dict[str, Any] = {
        "movement_fact": movement_fact,
        "transition_fact": transition_fact,
    }
    for key in ("gate_facts", "transfer_fact", "carry_fact"):
        if key in supplied_mapping:
            caller_facts[key] = supplied_mapping[key]
    return caller_facts

def _incoming_link_handoff_refs(
    steps: list[Any],
    index: int,
) -> Mapping[str, Any]:
    current_step = _require_mapping_value(f"steps[{index}]", steps[index])
    current_brick = _brick_instance_ref_from_step(current_step)
    incoming: list[Mapping[str, Any]] = []
    route_replay_handoffs: list[Mapping[str, Any]] = []
    for prior_index, prior_value in enumerate(steps[:index]):
        prior_step = _require_mapping_value(f"steps[{prior_index}]", prior_value)
        movement, target = _declared_movement_and_target(prior_step)
        prior_link = _link_row_from_step(prior_step)
        prior_step_ref = _optional_text_from_mapping(prior_step, "step_ref") or f"step-{prior_index + 1:02d}"
        if target == current_brick:
            handoff: dict[str, Any] = {
                "from_step_ref": prior_step_ref,
                "from_brick_instance_ref": _brick_instance_ref_from_step(prior_step),
                "link_row_ref": _required_text("Link row row_ref", prior_link.get("row_ref")),
                "movement": movement,
                "target_ref": target,
                "public_fact_refs": list(
                    _text_tuple("Link row public_fact_refs", prior_link.get("public_fact_refs", ()))
                ),
            }
            route_plan = _route_replay_plan_from_link_row(prior_link)
            if route_plan is not None:
                handoff["route_replay_plan"] = _route_replay_handoff_body(route_plan)
            incoming.append(handoff)
        route_plan = _route_replay_plan_from_link_row(prior_link)
        if route_plan is not None and _route_replay_plan_targets_brick(route_plan, current_brick):
            route_replay_handoffs.append(
                {
                    "from_step_ref": prior_step_ref,
                    "from_brick_instance_ref": _brick_instance_ref_from_step(prior_step),
                    "link_row_ref": _required_text("Link row row_ref", prior_link.get("row_ref")),
                    **_route_replay_handoff_body(route_plan),
                }
            )
    if not incoming and not route_replay_handoffs:
        return {}
    handoff_refs: dict[str, Any] = {"target_brick_instance_ref": current_brick}
    if incoming:
        handoff_refs["incoming"] = incoming
    if route_replay_handoffs:
        handoff_refs["route_replay_handoffs"] = route_replay_handoffs
    return handoff_refs

def _route_replay_plan_targets_brick(route_plan: Mapping[str, Any], brick_ref: str) -> bool:
    immediate = _optional_text_value(route_plan.get("immediate_target_ref"))
    replay_refs = _text_tuple("route_replay_plan.replay_segment_refs", route_plan.get("replay_segment_refs", ()))
    return brick_ref == immediate or brick_ref in replay_refs

def _route_replay_handoff_body(route_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    body: dict[str, Any] = {
        "route_replay_ref": _required_text(
            "route_replay_plan.route_replay_ref",
            route_plan.get("route_replay_ref"),
        ),
        "author_ref": _required_text(
            "route_replay_plan.author_ref",
            route_plan.get("author_ref"),
        ),
        "authoring_basis_refs": list(
            _text_tuple(
                "route_replay_plan.authoring_basis_refs",
                route_plan.get("authoring_basis_refs"),
            )
        ),
        "immediate_target_ref": _required_text(
            "route_replay_plan.immediate_target_ref",
            route_plan.get("immediate_target_ref"),
        ),
        "route_reason_refs": list(
            _text_tuple("route_replay_plan.route_reason_refs", route_plan.get("route_reason_refs"))
        ),
        "affected_downstream_refs": list(
            _text_tuple(
                "route_replay_plan.affected_downstream_refs",
                route_plan.get("affected_downstream_refs"),
            )
        ),
        "replay_segment_refs": list(
            _text_tuple("route_replay_plan.replay_segment_refs", route_plan.get("replay_segment_refs"))
        ),
    }
    if "max_attempts" in route_plan:
        body["max_attempts"] = _positive_int("route_replay_plan.max_attempts", route_plan.get("max_attempts"))
    return body

def _brick_instance_ref_from_step(step: Mapping[str, Any]) -> str:
    brick_row = _brick_row_from_step(step)
    return _required_text("Brick row brick_instance_ref", brick_row.get("brick_instance_ref"))

def _brick_row_from_step(step: Mapping[str, Any]) -> Mapping[str, Any]:
    return _axis_row_from_step(step, "Brick")

def _link_row_from_step(step: Mapping[str, Any]) -> Mapping[str, Any]:
    return _axis_row_from_step(step, "Link")

def _axis_row_from_step(step: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        raise ValueError("Building Plan step must contain rows")
    for index, row_value in enumerate(rows):
        row = _require_mapping_value(f"step.rows[{index}]", row_value)
        if _required_text("step row axis", row.get("axis")) == axis:
            return row
    raise ValueError(f"Building Plan step missing {axis} row")

def _declared_step_movement_fact(
    supplied: Any,
    *,
    movement: str,
    target: str,
    plan_ref: str,
    step_ref: str,
) -> Mapping[str, Any]:
    if supplied is None:
        return {
            "movement": movement,
            "reason": f"declared by {plan_ref} {step_ref}",
            "handoff_target_fact": target,
        }
    supplied_mapping = dict(_mapping("movement_fact", supplied))
    supplied_movement = _optional_text_value(supplied_mapping.get("movement"))
    if supplied_movement is not None and supplied_movement != movement:
        raise ValueError("caller-supplied movement_fact must match the Link row Movement")
    supplied_target = _optional_text_value(supplied_mapping.get("handoff_target_fact"))
    if supplied_target is not None and supplied_target != target:
        raise ValueError("caller-supplied movement_fact must match the Link row target")
    supplied_mapping["movement"] = movement
    supplied_mapping.setdefault("reason", f"declared by {plan_ref} {step_ref}")
    supplied_mapping.setdefault("handoff_target_fact", target)
    return supplied_mapping

def _declared_step_transition_fact(
    supplied: Any,
    *,
    movement: str,
    target: str,
    step_ref: str,
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    if supplied is None:
        return {
            "movement": movement,
            "target_fact": target,
            "handoff_reference": step_ref,
            "not_proven": not_proven,
        }
    supplied_mapping = dict(_mapping("transition_fact", supplied))
    supplied_movement = _optional_text_value(supplied_mapping.get("movement"))
    if supplied_movement is not None and supplied_movement != movement:
        raise ValueError("caller-supplied transition_fact must match the Link row Movement")
    supplied_target = _optional_text_value(supplied_mapping.get("target_fact"))
    if supplied_target is not None and supplied_target != target:
        raise ValueError("caller-supplied transition_fact must match the Link row target")
    supplied_mapping["movement"] = movement
    supplied_mapping.setdefault("target_fact", target)
    supplied_mapping.setdefault("handoff_reference", step_ref)
    supplied_mapping.setdefault("not_proven", not_proven)
    return supplied_mapping

def _step_rows_with_declared_next_target(
    rows: list[Any],
    target: str,
) -> list[Mapping[str, Any]]:
    fixture_rows: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        row_mapping = _require_mapping_value(f"rows[{index}]", row)
        copied = dict(row_mapping)
        if copied.get("axis") == "Link" and "next_brick_instance_ref" not in copied:
            copied["next_brick_instance_ref"] = target
        fixture_rows.append(copied)
    return fixture_rows

def _caller_link_facts(packet: Mapping[str, Any]) -> dict[str, Any]:
    facts = _mapping("caller_supplied_link_facts", packet.get("caller_supplied_link_facts"))
    movement_fact_data = _mapping(
        "caller_supplied_link_facts.movement_fact",
        facts.get("movement_fact"),
    )
    transition_fact_data = _mapping(
        "caller_supplied_link_facts.transition_fact",
        facts.get("transition_fact"),
    )
    link_fact = make_movement_fact(
        _required_text("movement_fact.movement", movement_fact_data.get("movement")),
        reason=_optional_text(movement_fact_data.get("reason")),
        handoff_target_fact=_optional_text_or_none(
            movement_fact_data.get("handoff_target_fact")
        ),
        gatefact_reference=_optional_text_or_none(movement_fact_data.get("gatefact_reference")),
        transition_history_reference=_optional_text_or_none(
            movement_fact_data.get("transition_history_reference")
        ),
    )
    transition_fact = make_transition_fact(
        _required_text("transition_fact.movement", transition_fact_data.get("movement")),
        target_fact=_optional_text_or_none(transition_fact_data.get("target_fact")),
        topology_fact=_optional_text_or_none(transition_fact_data.get("topology_fact")),
        merge_rule_fact=_optional_text_or_none(transition_fact_data.get("merge_rule_fact")),
        handoff_reference=_optional_text_or_none(transition_fact_data.get("handoff_reference")),
        not_proven=_text_tuple(
            "transition_fact.not_proven",
            transition_fact_data.get("not_proven"),
        ),
    )
    built: dict[str, Any] = {
        "link_fact": link_fact,
        "transition_fact": transition_fact,
        "transfer_gate_fact": None,
        "carry_gate_fact": None,
        "movement_gate_fact": None,
        "transfer_fact": None,
        "carry_fact": None,
    }
    gate_facts = facts.get("gate_facts")
    if gate_facts is not None:
        gate_mapping = _mapping("caller_supplied_link_facts.gate_facts", gate_facts)
        for field_name, stage_name in (
            ("transfer_gate_fact", "transfer"),
            ("carry_gate_fact", "carry"),
            ("movement_gate_fact", "movement"),
        ):
            if field_name in gate_mapping:
                built[field_name] = _gate_fact(field_name, stage_name, gate_mapping[field_name])
    if facts.get("transfer_fact") is not None:
        built["transfer_fact"] = _transfer_fact(facts["transfer_fact"])
    if facts.get("carry_fact") is not None:
        built["carry_fact"] = _carry_fact(facts["carry_fact"])
    return built

def _gate_fact(label: str, stage: str, value: Any) -> Any:
    item = _mapping(label, value)
    return make_gate_fact(
        stage,
        _required_text(f"{label}.sufficiency", item.get("sufficiency")),
        checked_public_fact=_optional_text(item.get("checked_public_fact")),
        required_public_facts=_text_tuple(
            f"{label}.required_public_facts",
            item.get("required_public_facts"),
        ),
        missing_required_facts=_text_tuple(
            f"{label}.missing_required_facts",
            item.get("missing_required_facts"),
        ),
        reason=_optional_text(item.get("reason")),
        evidence_reference=_optional_text_or_none(item.get("evidence_reference")),
    )

def _transfer_fact(value: Any) -> Any:
    item = _mapping("transfer_fact", value)
    return make_transfer_fact(
        source_boundary_ref=_required_text(
            "transfer_fact.source_boundary_ref",
            item.get("source_boundary_ref"),
        ),
        target_boundary_ref=_required_text(
            "transfer_fact.target_boundary_ref",
            item.get("target_boundary_ref"),
        ),
        public_fact_refs=_text_tuple("transfer_fact.public_fact_refs", item.get("public_fact_refs")),
        work_context_ref=_required_text("transfer_fact.work_context_ref", item.get("work_context_ref")),
        required_public_facts=_text_tuple(
            "transfer_fact.required_public_facts",
            item.get("required_public_facts"),
        ),
        transfer_gate_reference=_optional_text_or_none(item.get("transfer_gate_reference")),
        proof_limits=_text_tuple("transfer_fact.proof_limits", item.get("proof_limits")),
        not_proven=_text_tuple("transfer_fact.not_proven", item.get("not_proven")),
        evidence_reference=_required_text("transfer_fact.evidence_reference", item.get("evidence_reference")),
    )

def _carry_fact(value: Any) -> Any:
    item = _mapping("carry_fact", value)
    return make_carry_fact(
        carried_fact_refs=_text_tuple("carry_fact.carried_fact_refs", item.get("carried_fact_refs")),
        source_owner_axis=_required_text("carry_fact.source_owner_axis", item.get("source_owner_axis")),
        target_boundary_ref=_required_text("carry_fact.target_boundary_ref", item.get("target_boundary_ref")),
        carry_gate_reference=_optional_text_or_none(item.get("carry_gate_reference")),
        proof_limits=_text_tuple("carry_fact.proof_limits", item.get("proof_limits")),
        not_proven=_text_tuple("carry_fact.not_proven", item.get("not_proven")),
        evidence_reference=_required_text("carry_fact.evidence_reference", item.get("evidence_reference")),
    )

def _comparison_fact_from_observation(
    prepared: AgentRunPreparationRecord,
    value: BrickComparisonFact | Mapping[str, Any] | None,
    *,
    returned_value: Any | None = None,
) -> BrickComparisonFact:
    if value is None:
        comparison = BrickComparisonFact.from_returned_value(
            work_reference=prepared.brick_work.work_statement,
            required_fields=_required_agent_return_fields_for_brick_handoff(prepared),
            returned_value=returned_value,
            comparison_rule=prepared.brick_work.comparison_rule,
            required_return_shape_evidence=prepared.brick_work.required_return_shape,
            forbidden_shortcut_evidence=(
                "support/run did not classify Agent return",
                "support/run did not judge success or quality",
                "support/run used caller-supplied Link facts",
            ),
        )
    elif isinstance(value, BrickComparisonFact):
        comparison = value
    else:
        mapping = _require_mapping_value("comparison_observation", value)
        _validate_no_payload_forbidden("comparison_observation", mapping, _RETURN_FORBIDDEN_KEYS)
        comparison = BrickComparisonFact.from_parts(
            work_reference=_optional_text_value(mapping.get("work_reference"))
            or prepared.brick_work.work_statement,
            comparison_evidence=_text_tuple(
                "comparison_observation.comparison_evidence",
                mapping.get(
                    "comparison_evidence",
                    "adapter returned value is available for Brick comparison observation",
                ),
            ),
            observed_match_kind=_optional_text_value(mapping.get("observed_match_kind"))
            or "unknown",
            comparison_rule=_optional_text_value(mapping.get("comparison_rule"))
            or prepared.brick_work.comparison_rule,
            required_return_shape_evidence=_optional_text_value(
                mapping.get("required_return_shape_evidence")
            )
            or prepared.brick_work.required_return_shape,
            forbidden_shortcut_evidence=_text_tuple(
                "comparison_observation.forbidden_shortcut_evidence",
                mapping.get(
                    "forbidden_shortcut_evidence",
                    (
                        "support/run did not classify Agent return",
                        "support/run did not judge success or quality",
                    ),
                ),
            ),
        )
    return _comparison_with_artifact_grounding(prepared, comparison, returned_value)


def _comparison_with_artifact_grounding(
    prepared: AgentRunPreparationRecord,
    comparison: BrickComparisonFact,
    returned_value: Any | None,
) -> BrickComparisonFact:
    evidence_field = _artifact_grounding_evidence_field(prepared)
    if not evidence_field:
        return comparison
    grounding_field = (
        _ARTIFACT_GROUNDING_DESIGN_FACT
        if evidence_field == _ARTIFACT_GROUNDING_DESIGN_FIELD
        else _ARTIFACT_GROUNDING_REVIEW_FACT
    )
    has_grounding = _returned_field_has_repo_artifact_ref(returned_value, evidence_field)
    required_fields = tuple(dict.fromkeys((*comparison.required_return_fields(), grounding_field)))
    missing_fields = list(comparison.missing_return_fields())
    if has_grounding:
        missing_fields = [field for field in missing_fields if field != grounding_field]
    elif grounding_field not in missing_fields:
        missing_fields.append(grounding_field)
    comparison_evidence = _replace_comparison_evidence_fields(
        comparison.comparison_evidence,
        prefix="required_return_fields:",
        fields=required_fields,
    )
    comparison_evidence = _replace_comparison_evidence_fields(
        comparison_evidence,
        prefix="missing_return_fields:",
        fields=tuple(dict.fromkeys(missing_fields)),
    )
    comparison_evidence = (
        *comparison_evidence,
        (
            f"artifact_grounding: {evidence_field} includes inspected repository artifact reference"
            if has_grounding
            else f"artifact_grounding_missing: {evidence_field} lacks inspected repository artifact reference"
        ),
    )
    return BrickComparisonFact.from_parts(
        work_reference=comparison.work_reference,
        comparison_evidence=comparison_evidence,
        observed_match_kind="missing" if missing_fields else comparison.observed_match_kind,
        comparison_rule=comparison.comparison_rule,
        required_return_shape_evidence=comparison.required_return_shape_evidence,
        forbidden_shortcut_evidence=comparison.forbidden_shortcut_evidence,
    )


def _artifact_grounding_evidence_field(prepared: AgentRunPreparationRecord) -> str:
    fields = set(parse_required_return_shape(prepared.brick_work.required_return_shape))
    review_shapes = (
        {"attacked_work", _ARTIFACT_GROUNDING_REVIEW_FIELD},
        {"attacked_scope", _ARTIFACT_GROUNDING_REVIEW_FIELD},
        {"evidence_scope", _ARTIFACT_GROUNDING_REVIEW_FIELD},
        {"checked_work", _ARTIFACT_GROUNDING_REVIEW_FIELD},
    )
    if any(shape.issubset(fields) for shape in review_shapes):
        return _ARTIFACT_GROUNDING_REVIEW_FIELD
    if {"design_summary", _ARTIFACT_GROUNDING_DESIGN_FIELD}.issubset(fields):
        return _ARTIFACT_GROUNDING_DESIGN_FIELD
    return ""


def _returned_field_has_repo_artifact_ref(returned_value: Any | None, field_name: str) -> bool:
    if not isinstance(returned_value, Mapping):
        return False
    return evidence_list_has_repository_artifact_ref(returned_value.get(field_name))


def _replace_comparison_evidence_fields(
    comparison_evidence: tuple[str, ...],
    *,
    prefix: str,
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    replacement = f"{prefix} " + (", ".join(fields) if fields else "none")
    replaced = False
    lines: list[str] = []
    for line in comparison_evidence:
        if line.startswith(prefix):
            if not replaced:
                lines.append(replacement)
                replaced = True
            continue
        lines.append(line)
    if not replaced:
        lines.append(replacement)
    return tuple(lines)


def _required_agent_return_fields_for_brick_handoff(
    prepared: AgentRunPreparationRecord,
) -> tuple[str, ...]:
    base = _required_return_shape_fields(prepared.brick_work.required_return_shape)
    gate_refs = _text_tuple(
        "declared_gate_refs",
        prepared.step_rows.link_row.get(_DECLARED_GATE_REFS_KEY, ()),
    )
    return gate_required_return_fields(gate_refs, base)

def _required_return_shape_fields(value: Any) -> tuple[str, ...]:
    return parse_required_return_shape(value)

def _agent_run_handoff_packet(
    prepared: AgentRunPreparationRecord,
    crossing_record: MinimalCrossingRecord,
    not_proven: tuple[str, ...],
    proof_limits: tuple[str, ...],
) -> dict[str, Any]:
    packet = {
        "kind": "agent_run_link_handoff_packet",
        "building_id": prepared.building_id,
        "brick_boundary_refs": [
            prepared.brick_instance_ref,
            prepared.next_brick_instance_ref,
        ],
        "public_fact_refs": [
            f"agent-fact:{prepared.building_id}:{prepared.agent_object.object_ref}",
            f"brick-comparison:{prepared.building_id}",
            f"link-fact:{prepared.building_id}",
            f"transition-fact:{prepared.building_id}",
        ],
        "agent_fact_fields": ["received_work", "returned"],
        "link_fact_supplied_by_caller": isinstance(crossing_record.link_fact, MovementFact),
        "transition_fact_supplied_by_caller": isinstance(
            crossing_record.transition_fact,
            TransitionFact,
        ),
        "raw_refs": list(prepared.raw_refs),
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    _validate_handoff_packet(packet)
    return packet

def _validate_handoff_packet(packet: Mapping[str, Any]) -> None:
    boundaries = packet.get("brick_boundary_refs")
    if not isinstance(boundaries, list) or len(boundaries) != 2:
        raise ValueError("handoff packet requires two Brick boundary refs")
    for index, boundary in enumerate(boundaries):
        if not isinstance(boundary, str) or not boundary.strip():
            raise ValueError(f"handoff packet brick_boundary_refs[{index}] must be text")
        if _looks_like_agent_endpoint(boundary):
            raise ValueError("Link handoff packet must not use Agent endpoint refs")

def _declared_plan_brick_refs(steps: list[Any]) -> frozenset[str]:
    refs: set[str] = set()
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        rows = step.get("rows")
        if not isinstance(rows, list):
            continue
        for row_index, row_value in enumerate(rows):
            row = _require_mapping_value(f"steps[{step_index}].rows[{row_index}]", row_value)
            if row.get("axis") != "Brick":
                continue
            for key in ("brick_instance_ref", "boundary_ref"):
                value = row.get(key)
                if value is not None:
                    refs.add(_required_text(f"steps[{step_index}].Brick.{key}", value))
    return frozenset(refs)

def _declared_plan_link_edges(steps: list[Any]) -> frozenset[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        brick_row = _declared_brick_row(step)
        link_row = _declared_link_row(step)
        source = _declared_brick_source_ref(brick_row)
        target = _declared_graph_target_from_link_row(link_row)
        edges.add((source, target))
    return frozenset(edges)

def _validate_declared_plan_route_replay_edges(
    steps: list[Any],
    declared_link_edges: frozenset[tuple[str, str]],
) -> None:
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        brick_row = _declared_brick_row(step)
        link_row = _declared_link_row(step)
        movement, target = _movement_and_target_from_link_row(link_row)
        source = _declared_brick_source_ref(brick_row)
        _validate_route_replay_plan_for_link_row(link_row, movement=movement, target=target)
        _validate_declared_gate_refs_for_link_row(link_row)
        _validate_gate_concept_provenance_for_link_row(link_row)
        _validate_gate_sequence_policy_for_link_row(
            link_row,
            source_brick_ref=source,
            target_brick_ref=target,
        )
        _validate_route_decision_basis_for_link_row(link_row)
        _validate_transition_authoring_for_link_row(link_row)
        _validate_transition_lifecycle_for_link_row(link_row)
        _validate_building_lifecycle_for_link_row(link_row)
        route_plan = _route_replay_plan_from_link_row(link_row)
        if route_plan is None:
            continue
        immediate_target = _required_text(
            "route_replay_plan.immediate_target_ref",
            route_plan.get("immediate_target_ref"),
        )
        if (source, immediate_target) not in declared_link_edges:
            raise ValueError(
                "route_replay_plan reroute edge must be declared by a Building Plan Link row"
            )
        replay_refs = _text_tuple(
            "route_replay_plan.replay_segment_refs",
            route_plan.get("replay_segment_refs"),
        )
        replay_chain = (immediate_target, *replay_refs)
        missing = [
            (source_ref, target_ref)
            for source_ref, target_ref in zip(replay_chain, replay_chain[1:])
            if (source_ref, target_ref) not in declared_link_edges
        ]
        if missing:
            pairs = ", ".join(f"{source_ref}->{target_ref}" for source_ref, target_ref in missing)
            raise ValueError(
                "route_replay_plan replay segment edges must be declared by Building Plan "
                f"Link rows: {pairs}"
            )


def validate_declared_building_plan(
    plan: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
    allow_retired_write_adapter_refs: bool = False,
    require_write_need_marker: bool = False,
) -> None:
    """Validate declared Building Plan Link/preflight rules before walking.

    This is support preflight only. It does not choose Movement, target, route,
    retry, or quality; it checks that the caller-declared road is structurally
    walkable under the active Link and attempt constraints.

    When ``repo_root`` is supplied, a declared, format-valid ``task_source_ref``
    is also resolved against the repo root and rejected if the file does not
    exist. Support only VALIDATES the declared task source path; it never
    authors or infers the task itself.

    ``allow_retired_write_adapter_refs`` is only for structural validation of
    closed historical Building records. Active render/intake/request paths must
    keep the default false value.

    ``require_write_need_marker`` is the LIVE RUN ADMISSION strictness knob (no
    SILENT write grant): when true, a brick row carrying a write_scope MUST also
    carry an explicit positive write NEED declaration
    (``requires_brick_write_scope: true``) or the plan is rejected. The retired
    legacy ``write_need`` spelling is NOT recognized as a NEED declaration (L
    legacy cut, 0610): a row carrying only ``write_need`` counts as having NO
    declared NEED, so under the strict knob it is rejected loudly. Default false
    preserves the historical read sweep over preserved evidence (historical
    plans carry no marker and are read, not re-admitted).
    """

    plan_ref = _optional_text_from_mapping(plan, "plan_ref") or "building-plan:anonymous"
    _reject_in_memory_composed_plan_ref(plan_ref)
    _task_source_ref_from_plan(plan, repo_root=repo_root)
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Building plan must contain a non-empty steps list")
    declared_brick_refs = _declared_plan_brick_refs(steps)
    declared_link_edges = _declared_plan_link_edges(steps)
    _validate_declared_route_replay_attempt_limits(plan, steps)
    _validate_declared_plan_route_replay_edges(steps, declared_link_edges)
    _validate_declared_plan_gate_sequence_policies(
        plan,
        steps,
        declared_brick_refs=declared_brick_refs,
    )
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        _validate_declared_step_link(step, declared_brick_refs=declared_brick_refs)
        _validate_declared_step_write_scope(
            step,
            selected_adapter_ref=_declared_selected_adapter_ref(plan, step),
            allow_retired_write_adapter_refs=allow_retired_write_adapter_refs,
            require_write_need_marker=require_write_need_marker,
        )

def _validate_declared_plan_gate_sequence_policies(
    plan: Mapping[str, Any],
    steps: list[Any],
    *,
    declared_brick_refs: frozenset[str],
) -> None:
    raw_budgets = plan.get("node_reroute_budgets", {})
    if raw_budgets is None:
        raw_budgets = {}
    if not isinstance(raw_budgets, Mapping):
        raise ValueError("node_reroute_budgets must be a mapping when supplied")
    node_reroute_budgets: dict[str, int] = {}
    for raw_ref, raw_budget in raw_budgets.items():
        brick_ref = _required_text("node_reroute_budgets key", raw_ref)
        _validate_gate_sequence_declared_target(
            brick_ref,
            declared_brick_refs=declared_brick_refs,
            field_name=f"node_reroute_budgets.{brick_ref}",
        )
        node_reroute_budgets[brick_ref] = _positive_int(
            f"node_reroute_budgets.{brick_ref}",
            raw_budget,
        )

    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        brick_row = _declared_brick_row(step)
        link_row = _declared_link_row(step)
        source = _declared_brick_source_ref(brick_row)
        target = _declared_graph_target_from_link_row(link_row)
        _validate_gate_sequence_policy_for_link_row(
            link_row,
            source_brick_ref=source,
            target_brick_ref=target,
            declared_brick_refs=declared_brick_refs,
            node_reroute_budgets=node_reroute_budgets,
        )

def _reject_in_memory_composed_plan_ref(plan_ref: str) -> None:
    """Reject ephemeral composed plan refs before support walks or writes."""

    checked = _required_text("plan_ref", plan_ref)
    if ":in-memory-composed" in checked:
        raise ValueError(
            "Building Plan plan_ref must be persisted before walking; "
            "':in-memory-composed' is ephemeral support composition evidence only"
        )

def _task_source_ref_from_plan(
    plan: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
) -> str | None:
    raw_value = plan.get("task_source_ref")
    if raw_value is None:
        if plan.get("task_statement") is not None:
            # Fail-closed: an inline statement may ride ONLY behind the
            # recorded sentinel ref -- a statement with no (or a file)
            # task_source_ref is a smuggled second task source.
            raise ValueError(
                "plan task_statement is admitted only with task_source_ref "
                f"{INLINE_TASK_SOURCE_REF!r}"
            )
        return None
    value = _optional_text_value(raw_value)
    if value is None:
        if plan.get("task_statement") is not None:
            raise ValueError(
                "plan task_statement is admitted only with task_source_ref "
                f"{INLINE_TASK_SOURCE_REF!r}"
            )
        return None
    normalized = value.replace("\\", "/").strip()
    if normalized == INLINE_TASK_SOURCE_REF:
        # TASK-BY-TEXT (0611, codex FIX-A): the sentinel ref is admitted ONLY
        # when the plan actually CARRIES the statement body -- the plan is the
        # task carrier (work/task.md verbatim source + replay source); a
        # sentinel without a body is a broken declared road, reject loudly.
        statement = plan.get("task_statement")
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError(
                f"task_source_ref {INLINE_TASK_SOURCE_REF!r} requires the plan "
                "to carry a non-empty task_statement body"
            )
        return normalized
    if plan.get("task_statement") is not None:
        raise ValueError(
            "plan task_statement is admitted only with task_source_ref "
            f"{INLINE_TASK_SOURCE_REF!r}"
        )
    if Path(normalized).is_absolute() or normalized.startswith(("/", "~")):
        raise ValueError("task_source_ref must be a repo-relative path")
    if "://" in normalized:
        raise ValueError("task_source_ref must be a repo-relative path, not a URI")
    parts = tuple(part for part in normalized.split("/") if part)
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError("task_source_ref must be a safe repo-relative path")
    if ":" in parts[0]:
        raise ValueError("task_source_ref must be a repo-relative path, not a drive or URI")
    if len(parts) >= 2 and parts[:2] == ("brick", "tasks"):
        raise ValueError("task_source_ref must not point at brick/tasks active task instances")
    resolved_ref = "/".join(parts)
    if repo_root is not None:
        # Support only VALIDATES that the declared task source exists; it does
        # not author or infer the task. A declared-but-missing task_source_ref
        # is a broken declared road, so reject it.
        if not (Path(repo_root) / resolved_ref).is_file():
            raise ValueError(
                f"task_source_ref declared file does not exist: {resolved_ref}"
            )
    return resolved_ref


def _declared_selected_adapter_ref(plan: Mapping[str, Any], step: Mapping[str, Any]) -> str | None:
    if "selected_adapter_ref" in step:
        raw_value = step.get("selected_adapter_ref")
    else:
        raw_value = plan.get("selected_adapter_ref")
    return _optional_text_value(raw_value)


# SINGLE SOURCE for the strict no-SILENT-write-grant rejection prose: the live
# run admission surfaces (run_building_plan linear admission, the dynamic
# walker/resume admission, and run_building_once single-step admission) must all
# reject with EXACTLY this text, so it lives here once instead of drifting as
# copy-pasted literals across call sites.
_SILENT_WRITE_GRANT_REJECTION = (
    "write_scope requires an explicit Brick write NEED declaration "
    "(requires_brick_write_scope: true); silent write grants are not admitted"
)


def _declared_brick_write_need(brick_row: Mapping[str, Any]) -> bool | None:
    """Return the Brick row's declared write NEED, or None when not recorded.

    The NEED marker (``requires_brick_write_scope`` -- the ONLY recognized
    spelling; the legacy ``write_need`` synonym is retired and deliberately NOT
    read here, L legacy cut 0610) is OPTIONAL on a declared plan brick row --
    historical records and externally authored plans may omit it, so an absent
    marker returns None (the prior behavior, no inverse-guard rejection). A row
    carrying only the retired ``write_need`` key therefore has NO declared NEED:
    strict run admission rejects its write_scope loudly
    (``_SILENT_WRITE_GRANT_REJECTION``) and the row-key whitelist
    (``primitives._BRICK_ROW_ALLOWED_KEYS``) rejects the key itself as
    unadmitted. When the canonical marker is present it must be a clean bool
    or yes/no literal; anything else is a malformed declared road and is
    rejected fail-closed.
    """

    if "requires_brick_write_scope" in brick_row:
        value = brick_row.get("requires_brick_write_scope")
        label = "Brick row requires_brick_write_scope"
    else:
        return None
    if value is True or value is False:
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "yes":
            return True
        if text == "no":
            return False
    raise ValueError(f"{label} must be a bool or yes/no (got {value!r})")


def _validate_brick_row_write_need_for_scope(
    brick_row: Mapping[str, Any],
    *,
    require_write_need_marker: bool,
) -> None:
    """Row-level write-NEED admission shared by EVERY live admission surface.

    Inverse guard: a write_scope only exists to serve a Brick's declared write
    NEED. When the Brick row records its NEED (requires_brick_write_scope) and
    that NEED is explicitly NO, a present write_scope is an axis leak -- it would
    let the run-time provider projection open write on a step that declared no
    write NEED (the same leak effective_write forbids). Reject it. The marker is
    OPTIONAL on the declared plan, so a brick row that omits it keeps the prior
    behavior (historical records carry no marker); composition is the
    authoritative layer that records the NEED and rejects the mismatch at
    materialization. A write-needed step carries BOTH the NEED and the
    write_scope, so it is never rejected here.

    STRICT RUN ADMISSION (no SILENT write grant): at the live run admission
    boundary a write_scope is admissible ONLY when the brick row EXPLICITLY
    declares its write NEED. An absent marker is tolerated solely by the
    default (historical read sweep) mode; with the knob on, the NEED must be
    DECLARED, never inferred from scope presence (Agent capability alone must
    never suffice to open workspace write). The strict rejection text is the
    module-level ``_SILENT_WRITE_GRANT_REJECTION`` so all admission surfaces
    (plan walker, dynamic walker/resume, run_building_once) reject identically.
    """

    raw_write_scope = brick_row.get("write_scope")
    declared_write_need = _declared_brick_write_need(brick_row)
    if declared_write_need is False and raw_write_scope is not None:
        raise ValueError(
            "write_scope present on a read-only Brick: a write_scope requires the "
            "Brick to declare a write NEED (requires_brick_write_scope)"
        )
    if raw_write_scope is None:
        return
    if require_write_need_marker and declared_write_need is not True:
        raise ValueError(_SILENT_WRITE_GRANT_REJECTION)


def _validate_declared_step_write_scope(
    step: Mapping[str, Any],
    *,
    selected_adapter_ref: str | None,
    allow_retired_write_adapter_refs: bool = False,
    require_write_need_marker: bool = False,
) -> None:
    brick_row = _brick_row_from_step(step)
    raw_write_scope = brick_row.get("write_scope")
    if selected_adapter_ref in _RETIRED_WRITE_ADAPTER_REFS:
        if not allow_retired_write_adapter_refs:
            raise ValueError(
                f"{selected_adapter_ref} is retired and not admitted as an active adapter"
            )
        retired_write_adapter_ref = True
    else:
        retired_write_adapter_ref = False
    _validate_brick_row_write_need_for_scope(
        brick_row,
        require_write_need_marker=require_write_need_marker,
    )
    if raw_write_scope is None:
        return
    if (
        selected_adapter_ref not in _OBSERVED_WRITE_ADAPTER_REFS
        and not retired_write_adapter_ref
    ):
        raise ValueError(
            "missing_adapter_write_capability: Brick row write_scope requires an "
            "observed-write selected adapter ref"
        )
    write_scope = _mapping("Brick row write_scope", raw_write_scope)
    allowed_paths = write_scope.get("allowed_paths")
    if not isinstance(allowed_paths, list) or not allowed_paths:
        raise ValueError("Brick row write_scope.allowed_paths must be a non-empty list")
    for index, item in enumerate(allowed_paths):
        _required_text(f"Brick row write_scope.allowed_paths[{index}]", item)
    forbidden_paths = write_scope.get("forbidden_paths")
    if not isinstance(forbidden_paths, list):
        raise TypeError("Brick row write_scope.forbidden_paths must be a list")
    for index, item in enumerate(forbidden_paths):
        _required_text(f"Brick row write_scope.forbidden_paths[{index}]", item)


def _validate_declared_route_replay_attempt_limits(plan: Mapping[str, Any], steps: list[Any]) -> None:
    if "max_attempt" in plan or "max_attempts" in plan:
        raise ValueError("max_attempts belongs inside Link route_replay_plan, not Building Plan top-level")
    entries_by_brick_ref: dict[str, dict[str, Any]] = {}
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        step_ref = _required_text(f"steps[{step_index}].step_ref", step.get("step_ref"))
        brick_ref = _brick_instance_ref_from_step(step)
        if brick_ref in entries_by_brick_ref:
            raise ValueError(f"Building plan Brick ref appears more than once: {brick_ref}")
        entries_by_brick_ref[brick_ref] = {
            "step_ref": step_ref,
            "step_index": step_index,
        }
    for step_index, step_value in enumerate(steps):
        step = _require_mapping_value(f"steps[{step_index}]", step_value)
        link_row = _declared_link_row(step)
        route_plan = _route_replay_plan_from_link_row(link_row)
        if route_plan is None or "max_attempts" not in route_plan:
            continue
        max_attempts = _positive_int("route_replay_plan.max_attempts", route_plan.get("max_attempts"))
        counted_refs = [
            _required_text(
                "route_replay_plan.immediate_target_ref",
                route_plan.get("immediate_target_ref"),
            ),
            *_text_tuple("route_replay_plan.replay_segment_refs", route_plan.get("replay_segment_refs")),
        ]
        counted_step_refs = [
            entries_by_brick_ref[brick_ref]["step_ref"]
            for brick_ref in counted_refs
            if brick_ref in entries_by_brick_ref
        ]
        for counted_step_ref in set(counted_step_refs):
            observed_attempts = sum(
                1 for entry in entries_by_brick_ref.values() if entry["step_ref"] == counted_step_ref
            )
            if observed_attempts > max_attempts:
                raise ValueError(
                    f"route_replay_plan max_attempts exceeded for step_ref {counted_step_ref}"
                )

def _positive_int(label: str, value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(f"{label} must be a positive integer")

def _validate_declared_step_link(
    step: Mapping[str, Any],
    *,
    declared_brick_refs: frozenset[str] | None = None,
) -> None:
    movement, target = _declared_movement_and_target(step)
    link_row = _declared_link_row(step)
    _validate_route_replay_plan_for_link_row(
        link_row,
        movement=movement,
        target=target,
        declared_brick_refs=declared_brick_refs,
    )
    _validate_declared_gate_refs_for_link_row(link_row)
    _validate_gate_concept_provenance_for_link_row(link_row)
    _validate_gate_sequence_policy_for_link_row(
        link_row,
        source_brick_ref=_declared_brick_source_ref(_declared_brick_row(step)),
        target_brick_ref=target,
        declared_brick_refs=declared_brick_refs,
    )
    _validate_route_decision_basis_for_link_row(link_row)
    _validate_transition_authoring_for_link_row(link_row)
    _validate_transition_lifecycle_for_link_row(link_row)

def _declared_movement_and_target(step: Mapping[str, Any]) -> tuple[str, str]:
    return _movement_and_target_from_link_row(_declared_link_row(step))

def _declared_brick_row(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Building plan step must contain Brick, Agent, Link rows")
    brick_rows = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("axis") == "Brick"
    ]
    if len(brick_rows) != 1:
        raise ValueError("Building plan step must contain exactly one Brick row")
    return brick_rows[0]

def _declared_link_row(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("Building plan step must contain Brick, Agent, Link rows")
    link_rows = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("axis") == "Link"
    ]
    if len(link_rows) != 1:
        raise ValueError("Building plan step must contain exactly one Link row")
    return link_rows[0]

def _movement_and_target_from_link_row(link_row: Mapping[str, Any]) -> tuple[str, str]:
    movement_values = [
        _optional_text_or_none(link_row.get(key))
        for key in ("movement", "movement_literal")
    ]
    movement_values = [value for value in movement_values if value]
    if len(movement_values) != 1:
        raise ValueError("Building plan Link row must declare exactly one Movement")
    # codex review 4 P2-1: preflight previously checked only that EXACTLY ONE
    # movement was declared, not that it is an ACTIVE Link Movement. So a plan
    # declaring return/hold/stop/pass/sideways passed preflight (a false-green;
    # runtime MovementFact rejects it, but the declared-plan surface should not
    # call it valid). Enforce membership against the single source of truth,
    # link/movement.py MOVEMENT_LITERALS (forward/reroute), at preflight.
    if movement_values[0] not in MOVEMENT_LITERALS:
        raise ValueError(
            "Building plan Link row Movement must be one of "
            f"{list(MOVEMENT_LITERALS)} (the active Link Movement vocabulary); "
            f"got {movement_values[0]!r}"
        )
    target_values = [
        _optional_text_or_none(link_row.get(key))
        for key in ("target", "target_ref", "target_boundary_ref")
    ]
    target_values = [value for value in target_values if value]
    if len(target_values) != 1:
        raise ValueError("Building plan Link row must declare exactly one target")
    return movement_values[0], target_values[0]

def _validate_declared_gate_refs_for_link_row(link_row: Mapping[str, Any]) -> None:
    if _DECLARED_GATE_REFS_KEY not in link_row:
        return
    refs = _text_list_tuple("declared_gate_refs", link_row.get(_DECLARED_GATE_REFS_KEY))
    if not refs:
        raise ValueError("declared_gate_refs must be a non-empty list when supplied")
    if len(refs) != len(set(refs)):
        raise ValueError("declared_gate_refs must not contain duplicate refs")
    if refs[0] != "link-gate:default-transition":
        raise ValueError("declared_gate_refs must start with link-gate:default-transition")
    allowed = set(_DECLARED_GATE_REFS)
    unknown = sorted(ref for ref in refs if ref not in allowed)
    if unknown:
        raise ValueError("declared_gate_refs contains unadmitted gate refs: " + ", ".join(unknown))

_GATE_CONCEPT_PROVENANCE_KEY = "gate_concept_provenance"
_GATE_CONCEPT_PROVENANCE_ALLOWED_KEYS: frozenset[str] = frozenset(
    {"tokens", "declared_by"}
)

def _validate_gate_concept_provenance_for_link_row(link_row: Mapping[str, Any]) -> None:
    """Fail-closed shape check for the translated-gate provenance stamp (0610).

    gate_concept_provenance records WHICH preset-declared gate_concept_profile
    tokens were TRANSLATED onto this Link row and WHICH chain preset declared
    them. It is meaningful only next to a translated (beyond-default) gate
    stamp, so a provenance mapping on a default-only row is rejected: support
    must not invent provenance for gates nothing declared.
    """

    if _GATE_CONCEPT_PROVENANCE_KEY not in link_row:
        return
    provenance = _require_mapping_value(
        _GATE_CONCEPT_PROVENANCE_KEY,
        link_row.get(_GATE_CONCEPT_PROVENANCE_KEY),
    )
    _require_only_keys(
        _GATE_CONCEPT_PROVENANCE_KEY,
        provenance,
        _GATE_CONCEPT_PROVENANCE_ALLOWED_KEYS,
    )
    tokens = _text_list_tuple(
        f"{_GATE_CONCEPT_PROVENANCE_KEY}.tokens",
        provenance.get("tokens"),
    )
    if not tokens:
        raise ValueError("gate_concept_provenance.tokens must be a non-empty list")
    _required_text(
        f"{_GATE_CONCEPT_PROVENANCE_KEY}.declared_by",
        provenance.get("declared_by"),
    )
    declared_refs = _text_list_tuple(
        "declared_gate_refs",
        link_row.get(_DECLARED_GATE_REFS_KEY, []),
    )
    if not [ref for ref in declared_refs if ref != "link-gate:default-transition"]:
        raise ValueError(
            "gate_concept_provenance requires translated declared_gate_refs beyond "
            "link-gate:default-transition (provenance without a translated gate "
            "stamp is invented)"
        )

def _validate_gate_sequence_policy_for_link_row(
    link_row: Mapping[str, Any],
    *,
    source_brick_ref: str = "",
    target_brick_ref: str = "",
    declared_brick_refs: frozenset[str] | None = None,
    node_reroute_budgets: Mapping[str, int] | None = None,
) -> None:
    if _GATE_SEQUENCE_POLICY_KEY not in link_row:
        return
    policy = _gate_sequence_policy_from_link_row(link_row)
    if not isinstance(policy, list) or not policy:
        raise ValueError("gate_sequence_policy must be a non-empty ordered list")
    _reject_gate_sequence_authority_keys("gate_sequence_policy", policy)
    declared_refs = _text_tuple(
        "declared_gate_refs",
        link_row.get(_DECLARED_GATE_REFS_KEY, ()),
    )
    if not declared_refs:
        raise ValueError("gate_sequence_policy requires declared_gate_refs")

    gate_refs: list[str] = []
    action_rows: list[tuple[int, str, Mapping[str, Any], Mapping[str, Any]]] = []
    for index, raw_step in enumerate(policy):
        step = _mapping(f"gate_sequence_policy[{index}]", raw_step)
        _require_only_keys(
            f"gate_sequence_policy[{index}]",
            step,
            _GATE_SEQUENCE_STEP_ALLOWED_KEYS,
        )
        gate_ref = _required_text(
            f"gate_sequence_policy[{index}].gate_ref",
            step.get("gate_ref"),
        )
        if gate_ref not in _DECLARED_GATE_REFS:
            raise ValueError(f"gate_sequence_policy gate_ref is unadmitted: {gate_ref}")
        if gate_ref not in declared_refs:
            raise ValueError("gate_sequence_policy gate_ref must be present in declared_gate_refs")
        if gate_ref in gate_refs:
            raise ValueError("gate_sequence_policy must not duplicate gate_ref")
        gate_refs.append(gate_ref)
        missing_action = _gate_sequence_action_row(
            step,
            key="on_missing_required_facts",
            label=f"gate_sequence_policy[{index}].on_missing_required_facts",
        )
        sufficient_action = _gate_sequence_action_row(
            step,
            key="on_sufficient",
            label=f"gate_sequence_policy[{index}].on_sufficient",
        )
        action_rows.append((index, gate_ref, missing_action, sufficient_action))
        _text_tuple(
            f"gate_sequence_policy[{index}].proof_limits",
            step.get("proof_limits", ()),
        )
        _text_tuple(
            f"gate_sequence_policy[{index}].not_proven",
            step.get("not_proven", ()),
        )

    for index, gate_ref, missing_action, sufficient_action in action_rows:
        _validate_gate_sequence_action(
            missing_action,
            action_key="on_missing_required_facts",
            policy_index=index,
            gate_ref=gate_ref,
            gate_refs=tuple(gate_refs),
            source_brick_ref=source_brick_ref,
            target_brick_ref=target_brick_ref,
            declared_brick_refs=declared_brick_refs,
            node_reroute_budgets=node_reroute_budgets,
        )
        _validate_gate_sequence_action(
            sufficient_action,
            action_key="on_sufficient",
            policy_index=index,
            gate_ref=gate_ref,
            gate_refs=tuple(gate_refs),
            source_brick_ref=source_brick_ref,
            target_brick_ref=target_brick_ref,
            declared_brick_refs=declared_brick_refs,
            node_reroute_budgets=node_reroute_budgets,
        )

def _gate_sequence_policy_from_link_row(link_row: Mapping[str, Any]) -> list[Any] | None:
    value = link_row.get(_GATE_SEQUENCE_POLICY_KEY)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("gate_sequence_policy must be a non-empty ordered list")
    return value

def _gate_sequence_action_row(
    step: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> Mapping[str, Any]:
    raw = step.get(key)
    if raw is None:
        raise ValueError(f"{label} must be declared")
    action = _mapping(label, raw)
    _require_only_keys(label, action, _GATE_SEQUENCE_ACTION_ALLOWED_KEYS)
    _required_text(f"{label}.action", action.get("action"))
    for ref in _text_tuple(f"{label}.reason_refs", action.get("reason_refs", ())):
        _reject_forbidden_route_reason_ref(f"{label}.reason_refs", ref)
    _text_tuple(f"{label}.proof_limits", action.get("proof_limits", ()))
    _text_tuple(f"{label}.not_proven", action.get("not_proven", ()))
    return action

def _validate_gate_sequence_action(
    action_row: Mapping[str, Any],
    *,
    action_key: str,
    policy_index: int,
    gate_ref: str,
    gate_refs: tuple[str, ...],
    source_brick_ref: str,
    target_brick_ref: str,
    declared_brick_refs: frozenset[str] | None,
    node_reroute_budgets: Mapping[str, int] | None,
) -> None:
    action = _gate_sequence_action_literal(
        f"gate_sequence_policy[{policy_index}].{action_key}.action",
        action_row.get("action"),
    )
    if action_key == "on_missing_required_facts":
        if action not in {"reroute", "hold"}:
            raise ValueError(
                "gate_sequence_policy on_missing_required_facts action must be reroute or HOLD"
            )
    else:
        if action not in {"next", "forward"}:
            raise ValueError("gate_sequence_policy on_sufficient action must be next or forward")
        if action == "forward" and policy_index < len(gate_refs) - 1:
            raise ValueError("gate_sequence_policy forward action requires a terminal gate")

    next_gate_ref = _optional_text_value(action_row.get("next_gate_ref"))
    if next_gate_ref:
        if next_gate_ref not in gate_refs:
            raise ValueError("gate_sequence_policy next_gate_ref must be in the sequence")
        if gate_refs.index(next_gate_ref) <= policy_index:
            raise ValueError("gate_sequence_policy next_gate_ref must point to a later gate")
    if action == "next":
        if not next_gate_ref:
            raise ValueError("gate_sequence_policy next action requires next_gate_ref")
        if policy_index >= len(gate_refs) - 1:
            raise ValueError("gate_sequence_policy next action requires a later gate")
        if next_gate_ref and gate_refs[policy_index + 1] != next_gate_ref:
            raise ValueError("gate_sequence_policy next_gate_ref must point to the next ordered gate")

    if action == "reroute":
        target_ref = _gate_sequence_target_ref(
            action_row,
            source_brick_ref=source_brick_ref,
            target_brick_ref=target_brick_ref,
            basis_key="target_basis",
            ref_key="target_ref",
            label=f"gate_sequence_policy[{policy_index}].{action_key}",
        )
        _validate_gate_sequence_declared_target(
            target_ref,
            declared_brick_refs=declared_brick_refs,
            field_name=f"gate_sequence_policy[{policy_index}].{action_key}.target",
        )
        if node_reroute_budgets is not None:
            if target_ref not in node_reroute_budgets:
                raise ValueError(
                    "gate_sequence_policy reroute target requires finite node_reroute_budget"
                )
            _positive_int(
                f"node_reroute_budgets.{target_ref}",
                node_reroute_budgets[target_ref],
            )
        if action_row.get("required_target_budget") is not True:
            raise ValueError("gate_sequence_policy reroute action requires required_target_budget: true")

    if action == "hold":
        owner = _required_text(
            f"gate_sequence_policy[{policy_index}].{action_key}.required_disposition_owner",
            action_row.get("required_disposition_owner"),
        )
        if owner not in _TRANSITION_LIFECYCLE_DISPOSITION_OWNERS:
            raise ValueError(
                "gate_sequence_policy required_disposition_owner must be caller, coo, or caller-or-coo"
            )
        if (
            _optional_text_value(action_row.get("pending_target_basis")) is None
            and _optional_text_value(action_row.get("pending_target_ref")) is None
        ):
            raise ValueError(
                "gate_sequence_policy HOLD action requires pending_target_basis or pending_target_ref"
            )
        pending_ref = _gate_sequence_target_ref(
            action_row,
            source_brick_ref=source_brick_ref,
            target_brick_ref=target_brick_ref,
            basis_key="pending_target_basis",
            ref_key="pending_target_ref",
            label=f"gate_sequence_policy[{policy_index}].{action_key}",
        )
        _validate_gate_sequence_declared_target(
            pending_ref,
            declared_brick_refs=declared_brick_refs,
            field_name=f"gate_sequence_policy[{policy_index}].{action_key}.pending_target",
        )

def _gate_sequence_action_literal(field_name: str, value: Any) -> str:
    raw = _required_text(field_name, value)
    if raw.upper() == "HOLD":
        return "hold"
    action = raw.lower()
    if action not in {"forward", "hold", "next", "reroute"}:
        raise ValueError("gate_sequence_policy action is not admitted")
    return action

def _gate_sequence_target_ref(
    action_row: Mapping[str, Any],
    *,
    source_brick_ref: str,
    target_brick_ref: str,
    basis_key: str,
    ref_key: str,
    label: str,
    default_basis: str = "",
) -> str:
    basis = _optional_text_value(action_row.get(basis_key)) or default_basis
    explicit_ref = _optional_text_value(action_row.get(ref_key))
    if basis and explicit_ref:
        raise ValueError(f"{label} must declare either {basis_key} or {ref_key}, not both")
    if explicit_ref:
        return explicit_ref
    if basis not in _GATE_SEQUENCE_TARGET_BASIS:
        raise ValueError(f"{label}.{basis_key} must be source_brick or target_brick")
    if basis == "source_brick":
        return _required_text(f"{label}.source_brick_ref", source_brick_ref)
    return _required_text(f"{label}.target_brick_ref", target_brick_ref)

def _validate_gate_sequence_declared_target(
    target_ref: str,
    *,
    declared_brick_refs: frozenset[str] | None,
    field_name: str,
) -> None:
    _require_brick_route_ref(field_name, target_ref)
    if declared_brick_refs is not None and target_ref not in declared_brick_refs:
        raise ValueError("gate_sequence_policy target must be a declared Brick node")

def _reject_gate_sequence_authority_keys(name: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError(f"{name} contains non-text or blank key")
            key = _normalize_key(raw_key)
            if key in _GATE_SEQUENCE_FORBIDDEN_KEYS:
                raise ValueError(f"{name} contains forbidden authority key {raw_key!r}")
            if key in {"proof_limits", "not_proven"}:
                continue
            _reject_gate_sequence_authority_keys(f"{name}.{raw_key}", child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_gate_sequence_authority_keys(f"{name}[{index}]", child)
    elif isinstance(value, str):
        _reject_route_replay_authority_value(name, value)

def _declared_gate_evidence_fields(link_row: Mapping[str, Any]) -> Mapping[str, Any]:
    refs = _text_tuple("declared_gate_refs", link_row.get(_DECLARED_GATE_REFS_KEY, ()))
    if not refs:
        return {}
    return {"declared_gate_refs": list(refs)}

def _declared_brick_source_ref(brick_row: Mapping[str, Any]) -> str:
    return _required_text(
        "Brick row brick_instance_ref",
        brick_row.get("brick_instance_ref") or brick_row.get("boundary_ref"),
    )

def _declared_graph_target_from_link_row(link_row: Mapping[str, Any]) -> str:
    return _required_text(
        "Link row next_brick_instance_ref",
        link_row.get("next_brick_instance_ref") or _movement_and_target_from_link_row(link_row)[1],
    )

def _validate_route_replay_plan_for_link_row(
    link_row: Mapping[str, Any],
    *,
    movement: str,
    target: str,
    declared_brick_refs: frozenset[str] | None = None,
) -> None:
    if _ROUTE_REPLAY_PLAN_KEY not in link_row:
        return
    if movement != "reroute":
        raise ValueError("route_replay_plan is admitted only for movement: reroute")
    route_plan = _route_replay_plan_from_link_row(link_row)
    if route_plan is None:
        raise ValueError("route_replay_plan must be a mapping")
    _reject_route_replay_authority_keys("route_replay_plan", route_plan)
    _require_only_keys(
        "route_replay_plan",
        route_plan,
        _ROUTE_REPLAY_ALLOWED_KEYS,
    )

    route_replay_ref = _required_text(
        "route_replay_plan.route_replay_ref",
        route_plan.get("route_replay_ref"),
    )
    if not route_replay_ref.startswith("route-replay:"):
        raise ValueError("route_replay_plan.route_replay_ref must start with route-replay:")
    author_ref = _required_text(
        "route_replay_plan.author_ref",
        route_plan.get("author_ref"),
    )
    _validate_route_replay_author_ref(author_ref)
    authoring_basis_refs = _non_empty_text_list_tuple(
        "route_replay_plan.authoring_basis_refs",
        route_plan.get("authoring_basis_refs"),
    )
    immediate_target = _required_text(
        "route_replay_plan.immediate_target_ref",
        route_plan.get("immediate_target_ref"),
    )
    if immediate_target != target:
        raise ValueError("route_replay_plan.immediate_target_ref must match the Link row target_ref")
    _require_brick_route_ref("route_replay_plan.immediate_target_ref", immediate_target)

    source_refs = _non_empty_text_list_tuple(
        "route_replay_plan.source_brick_refs",
        route_plan.get("source_brick_refs"),
    )
    route_reason_refs = _non_empty_text_list_tuple(
        "route_replay_plan.route_reason_refs",
        route_plan.get("route_reason_refs"),
    )
    affected_refs = _non_empty_text_list_tuple(
        "route_replay_plan.affected_downstream_refs",
        route_plan.get("affected_downstream_refs"),
    )
    replay_refs = _text_tuple(
        "route_replay_plan.replay_segment_refs",
        route_plan.get("replay_segment_refs"),
    )

    for field_name, refs in (
        ("route_replay_plan.source_brick_refs", source_refs),
        ("route_replay_plan.affected_downstream_refs", affected_refs),
        ("route_replay_plan.replay_segment_refs", replay_refs),
    ):
        for ref in refs:
            _require_brick_route_ref(field_name, ref)
    for ref in route_reason_refs:
        _reject_forbidden_route_reason_ref("route_replay_plan.route_reason_refs", ref)
    for ref in authoring_basis_refs:
        _reject_forbidden_route_reason_ref("route_replay_plan.authoring_basis_refs", ref)

    if immediate_target in source_refs:
        raise ValueError("route_replay_plan must not reuse a prior source attempt as the immediate target")
    endpoint_refs = (immediate_target, *source_refs, *affected_refs, *replay_refs)
    if len(endpoint_refs) != len(set(endpoint_refs)):
        raise ValueError("route_replay_plan endpoint refs must be distinct append-only attempts")
    if declared_brick_refs is not None:
        missing = sorted(ref for ref in endpoint_refs if ref not in declared_brick_refs)
        if missing:
            raise ValueError(
                "route_replay_plan endpoint refs must be declared Brick rows: "
                + ", ".join(missing)
            )

def _validate_transition_authoring_for_link_row(link_row: Mapping[str, Any]) -> None:
    if _TRANSITION_AUTHORING_KEY not in link_row:
        return
    authoring = _transition_authoring_from_link_row(link_row)
    if authoring is None:
        raise ValueError("transition_authoring must be a mapping")
    _reject_route_replay_authority_keys("transition_authoring", authoring)
    _require_only_keys(
        "transition_authoring",
        authoring,
        _TRANSITION_AUTHORING_ALLOWED_KEYS,
    )
    authoring_ref = _required_text(
        "transition_authoring.transition_authoring_ref",
        authoring.get("transition_authoring_ref"),
    )
    if not authoring_ref.startswith("link-authoring:"):
        raise ValueError("transition_authoring.transition_authoring_ref must start with link-authoring:")
    author_ref = _required_text(
        "transition_authoring.author_ref",
        authoring.get("author_ref"),
    )
    _validate_route_replay_author_ref(author_ref)
    basis_refs = _non_empty_text_list_tuple(
        "transition_authoring.authoring_basis_refs",
        authoring.get("authoring_basis_refs"),
    )
    for ref in basis_refs:
        _reject_forbidden_route_reason_ref("transition_authoring.authoring_basis_refs", ref)
    if "transition_reason_refs" in authoring:
        reason_refs = _non_empty_text_list_tuple(
            "transition_authoring.transition_reason_refs",
            authoring.get("transition_reason_refs"),
        )
        for ref in reason_refs:
            _reject_forbidden_route_reason_ref("transition_authoring.transition_reason_refs", ref)

def _validate_route_decision_basis_for_link_row(link_row: Mapping[str, Any]) -> None:
    if _ROUTE_DECISION_BASIS_KEY not in link_row:
        return
    basis = _route_decision_basis_from_link_row(link_row)
    if basis is None:
        raise ValueError("route_decision_basis must be a mapping")
    _reject_route_replay_authority_keys("route_decision_basis", basis)
    _require_only_keys(
        "route_decision_basis",
        basis,
        _ROUTE_DECISION_BASIS_ALLOWED_KEYS,
    )
    for key in ("adopted_transition_concern_refs", "not_adopted_transition_concern_refs"):
        for ref in _text_list_tuple(f"route_decision_basis.{key}", basis.get(key, [])):
            _require_prefixed_decision_ref(
                f"route_decision_basis.{key}",
                ref,
                ("transition-concern:",),
            )
    for ref in _text_list_tuple(
        "route_decision_basis.reviewer_observation_refs",
        basis.get("reviewer_observation_refs", []),
    ):
        _require_prefixed_decision_ref(
            "route_decision_basis.reviewer_observation_refs",
            ref,
            ("review-observation:", "reviewer-observation:", "observation:"),
        )
    for ref in _text_list_tuple(
        "route_decision_basis.human_review_refs",
        basis.get("human_review_refs", []),
    ):
        _require_prefixed_decision_ref(
            "route_decision_basis.human_review_refs",
            ref,
            ("human-review:",),
        )
    for ref in _text_list_tuple(
        "route_decision_basis.override_refs",
        basis.get("override_refs", []),
    ):
        _require_prefixed_decision_ref(
            "route_decision_basis.override_refs",
            ref,
            ("human-review:", "human:", "coo:", "override:"),
        )
    _text_tuple("route_decision_basis.proof_limits", basis.get("proof_limits", ()))
    _text_tuple("route_decision_basis.not_proven", basis.get("not_proven", ()))

def _validate_transition_lifecycle_for_link_row(link_row: Mapping[str, Any]) -> None:
    if _TRANSITION_LIFECYCLE_KEY not in link_row:
        return
    lifecycle = _transition_lifecycle_from_link_row(link_row)
    if lifecycle is None:
        raise ValueError("transition_lifecycle must be a mapping")
    _require_only_keys("transition_lifecycle", lifecycle, _TRANSITION_LIFECYCLE_ALLOWED_KEYS)
    _reject_transition_lifecycle_authority_values("transition_lifecycle", lifecycle)
    _validate_transition_lifecycle_disposition_action(link_row, lifecycle)
    state = _required_text("transition_lifecycle.state", lifecycle.get("state"))
    if state not in _TRANSITION_LIFECYCLE_STATES:
        raise ValueError("transition_lifecycle.state must be paused or resumed")
    progress_state = _required_text(
        "transition_lifecycle.progress_state",
        lifecycle.get("progress_state"),
    )
    if progress_state not in _TRANSITION_LIFECYCLE_PROGRESS_STATES:
        raise ValueError("transition_lifecycle.progress_state must be in_progress")
    if state == "paused":
        _require_prefixed_decision_ref(
            "transition_lifecycle.paused_at_ref",
            _required_text("transition_lifecycle.paused_at_ref", lifecycle.get("paused_at_ref")),
            ("link-transition:",),
        )
        _require_brick_route_ref(
            "transition_lifecycle.from_brick_ref",
            _required_text("transition_lifecycle.from_brick_ref", lifecycle.get("from_brick_ref")),
        )
        _require_brick_route_ref(
            "transition_lifecycle.pending_target_ref",
            _required_text("transition_lifecycle.pending_target_ref", lifecycle.get("pending_target_ref")),
        )
        _required_transition_lifecycle_owner(lifecycle)
        reason_refs = _non_empty_text_list_tuple(
            "transition_lifecycle.reason_refs",
            lifecycle.get("reason_refs"),
        )
        for ref in reason_refs:
            _reject_forbidden_route_reason_ref("transition_lifecycle.reason_refs", ref)
    else:
        _require_prefixed_decision_ref(
            "transition_lifecycle.resumed_from_ref",
            _required_text("transition_lifecycle.resumed_from_ref", lifecycle.get("resumed_from_ref")),
            ("link-transition:",),
        )
        if lifecycle.get("paused_at_ref") is not None:
            _require_prefixed_decision_ref(
                "transition_lifecycle.paused_at_ref",
                _required_text("transition_lifecycle.paused_at_ref", lifecycle.get("paused_at_ref")),
                ("link-transition:",),
            )
        if lifecycle.get("from_brick_ref") is not None:
            _require_brick_route_ref(
                "transition_lifecycle.from_brick_ref",
                _required_text("transition_lifecycle.from_brick_ref", lifecycle.get("from_brick_ref")),
            )
        if lifecycle.get("pending_target_ref") is not None:
            _require_brick_route_ref(
                "transition_lifecycle.pending_target_ref",
                _required_text("transition_lifecycle.pending_target_ref", lifecycle.get("pending_target_ref")),
            )
        if lifecycle.get("required_disposition_owner") is not None:
            _required_transition_lifecycle_owner(lifecycle)
        for ref in _text_list_tuple("transition_lifecycle.reason_refs", lifecycle.get("reason_refs", [])):
            _reject_forbidden_route_reason_ref("transition_lifecycle.reason_refs", ref)
    _text_tuple("transition_lifecycle.proof_limits", lifecycle.get("proof_limits", ()))
    _text_tuple("transition_lifecycle.not_proven", lifecycle.get("not_proven", ()))

def _validate_transition_lifecycle_disposition_action(
    link_row: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
) -> None:
    action_value = lifecycle.get("disposition_action")
    budget_value = lifecycle.get("budget_increment")
    if action_value is None:
        if budget_value is not None:
            raise ValueError(
                "transition_lifecycle.budget_increment is admitted only with disposition_action: raise"
            )
        return
    action = _required_text(
        "transition_lifecycle.disposition_action",
        action_value,
    )
    if action not in _DISPOSITION_ACTIONS:
        raise ValueError(
            "transition_lifecycle.disposition_action must be raise, forward, or stop"
        )
    author_ref = _transition_lifecycle_disposition_author_ref(link_row)
    if not author_ref.startswith(_TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES):
        raise ValueError(
            "transition_lifecycle.disposition_action requires transition_authoring.author_ref "
            "starting with human: or coo:"
        )
    if action == "raise":
        _positive_int("transition_lifecycle.budget_increment", budget_value)
    elif budget_value is not None:
        raise ValueError(
            "transition_lifecycle.budget_increment is admitted only with disposition_action: raise"
        )

def _transition_lifecycle_disposition_author_ref(link_row: Mapping[str, Any]) -> str:
    authoring = _transition_authoring_from_link_row(link_row)
    if authoring is None:
        return ""
    author_ref = _required_text(
        "transition_authoring.author_ref",
        authoring.get("author_ref"),
    )
    _validate_route_replay_author_ref(author_ref)
    return author_ref

def _positive_int(field_name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite positive integer")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(f"{field_name} must be a finite positive integer")

def _validate_building_lifecycle_for_link_row(link_row: Mapping[str, Any]) -> None:
    if _BUILDING_LIFECYCLE_KEY not in link_row:
        return
    lifecycle = _mapping("building_lifecycle", link_row.get(_BUILDING_LIFECYCLE_KEY))
    _require_only_keys("building_lifecycle", lifecycle, _BUILDING_LIFECYCLE_ALLOWED_KEYS)
    state = _required_text("building_lifecycle.state", lifecycle.get("state"))
    if state not in _BUILDING_LIFECYCLE_STATES:
        raise ValueError("building_lifecycle.state must be waiting or closed")
    _optional_text_value(lifecycle.get("reason"))
    _text_tuple("building_lifecycle.proof_limits", lifecycle.get("proof_limits", ()))
    _text_tuple("building_lifecycle.not_proven", lifecycle.get("not_proven", ()))

def _building_lifecycle_state(link_row: Mapping[str, Any]) -> str:
    lifecycle = link_row.get(_BUILDING_LIFECYCLE_KEY)
    if lifecycle is None:
        return ""
    mapping = _mapping("building_lifecycle", lifecycle)
    return _optional_text_value(mapping.get("state")) or ""

def _validate_route_replay_author_ref(value: str) -> None:
    lowered = value.strip().lower()
    if not lowered.startswith(_ROUTE_REPLAY_ALLOWED_AUTHOR_PREFIXES):
        raise ValueError(
            "route_replay_plan.author_ref must start with human:, coo:, "
            "link-planning-brick:, or template:"
        )
    forbidden_prefixes = (
        "adapter:",
        "auth:",
        "credential:",
        "env:",
        "external_secret:",
        "hook:",
        "keychain:",
        "provider:",
        "queue:",
        "retry:",
        "rollback:",
        "runtime:",
        "scheduler:",
        "secret:",
        "session:",
        "setup-token:",
        "setup_token:",
        "support:",
        "tool:",
    )
    author_payload = lowered.split(":", 1)[1] if ":" in lowered else lowered
    if not author_payload:
        raise ValueError("route_replay_plan.author_ref must include an author id")
    if (
        _looks_like_agent_endpoint(lowered)
        or _looks_like_agent_endpoint(author_payload)
        or author_payload.startswith(forbidden_prefixes)
        or _contains_forbidden_ref_segment(author_payload)
        or "support/run" in lowered
        or "support:" in lowered
        or "support/" in lowered
    ):
        raise ValueError("route_replay_plan.author_ref must not name support, Agent, provider, session, tool, hook, or credential refs")

def _reject_forbidden_route_reason_ref(field_name: str, value: str) -> None:
    lowered = value.strip().lower()
    forbidden_prefixes = (
        "adapter:",
        "auth:",
        "credential:",
        "env:",
        "external_secret:",
        "hook:",
        "keychain:",
        "mutation:",
        "provider:",
        "queue:",
        "retry:",
        "rollback:",
        "runtime:",
        "secret:",
        "session:",
        "setup-token:",
        "setup_token:",
        "state:",
        "tool:",
    )
    is_agent_fact_public_ref = lowered.startswith("agent-fact:")
    if (
        not lowered.startswith(_ROUTE_REASON_ALLOWED_PUBLIC_FACT_PREFIXES)
        or (not is_agent_fact_public_ref and _looks_like_agent_endpoint(lowered))
        or lowered.startswith(forbidden_prefixes)
        or _contains_forbidden_ref_segment(lowered, allow_agent_fact=is_agent_fact_public_ref)
    ):
        raise ValueError(f"{field_name} must not use Agent/provider/adapter/session/tool/hook/credential refs")

def _contains_forbidden_ref_segment(value: str, *, allow_agent_fact: bool = False) -> bool:
    segments = [segment for segment in value.replace("/", ":").split(":") if segment]
    forbidden = {
        "adapter",
        "agent",
        "auth",
        "credential",
        "env",
        "external_secret",
        "hook",
        "keychain",
        "provider",
        "queue",
        "retry",
        "rollback",
        "runtime",
        "scheduler",
        "secret",
        "session",
        "setup-token",
        "setup_token",
        "support",
        "tool",
    }
    return any(
        segment in forbidden
        or (segment.startswith("agent-") and not (allow_agent_fact and segment == "agent-fact"))
        for segment in segments
    )

def _route_replay_plan_from_link_row(link_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = link_row.get(_ROUTE_REPLAY_PLAN_KEY)
    if value is None:
        return None
    return _mapping("route_replay_plan", value)

def _transition_authoring_from_link_row(link_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = link_row.get(_TRANSITION_AUTHORING_KEY)
    if value is None:
        return None
    return _mapping("transition_authoring", value)

def _route_decision_basis_from_link_row(link_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = link_row.get(_ROUTE_DECISION_BASIS_KEY)
    if value is None:
        return None
    return _mapping("route_decision_basis", value)

def _transition_lifecycle_from_link_row(link_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = link_row.get(_TRANSITION_LIFECYCLE_KEY)
    if value is None:
        return None
    return _mapping("transition_lifecycle", value)

def _reject_route_replay_authority_keys(name: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError(f"{name} contains non-text or blank key")
            key = _normalize_key(raw_key)
            if key in _ROUTE_REPLAY_FORBIDDEN_KEYS:
                raise ValueError(f"{name} contains forbidden route/replay authority key {raw_key!r}")
            if key in {"proof_limits", "not_proven"}:
                continue
            _reject_route_replay_authority_keys(f"{name}.{raw_key}", child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_route_replay_authority_keys(f"{name}[{index}]", child)
    elif isinstance(value, str):
        _reject_route_replay_authority_value(name, value)

def _reject_route_replay_authority_value(name: str, value: str) -> None:
    lowered = value.strip().lower()
    if any(marker in lowered for marker in _ROUTE_REPLAY_FORBIDDEN_VALUE_MARKERS):
        raise ValueError(f"{name} contains forbidden route/replay authority value")

def _reject_transition_lifecycle_authority_values(name: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = _normalize_key(raw_key) if isinstance(raw_key, str) else ""
            if key in {"proof_limits", "not_proven"}:
                continue
            _reject_transition_lifecycle_authority_values(f"{name}.{raw_key}", child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_transition_lifecycle_authority_values(f"{name}[{index}]", child)
    elif isinstance(value, str):
        _reject_route_replay_authority_value(name, value)

def _require_prefixed_decision_ref(
    field_name: str,
    value: str,
    allowed_prefixes: tuple[str, ...],
) -> None:
    text = _required_text(field_name, value)
    lowered = text.lower()
    forbidden_prefixes = (
        "adapter:",
        "agent:",
        "agent-object:",
        "auth:",
        "credential:",
        "env:",
        "external_secret:",
        "hook:",
        "keychain:",
        "provider:",
        "queue:",
        "retry:",
        "rollback:",
        "runtime:",
        "scheduler:",
        "secret:",
        "session:",
        "setup-token:",
        "setup_token:",
        "support:",
        "tool:",
    )
    if not lowered.startswith(allowed_prefixes) or lowered.startswith(forbidden_prefixes):
        raise ValueError(f"{field_name} must use admitted Link decision evidence refs")
    if _looks_like_agent_endpoint(lowered) or _contains_forbidden_ref_segment(lowered):
        raise ValueError(f"{field_name} must not use Agent/provider/support/runtime refs")

def _required_transition_lifecycle_owner(lifecycle: Mapping[str, Any]) -> str:
    owner = _required_text(
        "transition_lifecycle.required_disposition_owner",
        lifecycle.get("required_disposition_owner"),
    )
    if owner not in _TRANSITION_LIFECYCLE_DISPOSITION_OWNERS:
        raise ValueError(
            "transition_lifecycle.required_disposition_owner must be caller, coo, or caller-or-coo"
        )
    return owner

def _non_empty_text_tuple(field_name: str, values: Iterable[str] | str | None) -> tuple[str, ...]:
    result = _text_tuple(field_name, values)
    if not result:
        raise ValueError(f"{field_name} must be non-empty")
    return result

def _text_list_tuple(field_name: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list of text refs")
    return tuple(_required_text(f"{field_name}[{index}]", value) for index, value in enumerate(values))

def _non_empty_text_list_tuple(field_name: str, values: Any) -> tuple[str, ...]:
    result = _text_list_tuple(field_name, values)
    if not result:
        raise ValueError(f"{field_name} must be non-empty")
    return result

def _require_brick_route_ref(field_name: str, value: str) -> None:
    _reject_forbidden_route_endpoint(field_name, value)
    if not _is_brick_boundary_or_instance_ref(value):
        raise ValueError(f"{field_name} must be a Brick boundary or Brick instance ref")

def _is_brick_boundary_or_instance_ref(value: str) -> bool:
    text = value.strip()
    return text.startswith(
        (
            "brick:",
            "brick-",
            "brick-boundary:",
            "brick-instance:",
            "building-boundary:",
            "building-boundary-",
        )
    )

def _reject_forbidden_route_endpoint(field_name: str, value: str) -> None:
    lowered = value.strip().lower()
    forbidden_prefixes = (
        "adapter:",
        "auth:",
        "credential:",
        "env:",
        "external_secret:",
        "hook:",
        "keychain:",
        "mutation:",
        "provider:",
        "queue:",
        "retry:",
        "rollback:",
        "runtime:",
        "secret:",
        "session:",
        "setup-token:",
        "setup_token:",
        "state:",
        "tool:",
    )
    if _looks_like_agent_endpoint(value) or lowered.startswith(forbidden_prefixes):
        raise ValueError(f"{field_name} must not use Agent/provider/adapter/session/tool/hook/credential refs")

def _route_replay_evidence_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    route_plan = _route_replay_plan_from_link_row(link_row)
    if route_plan is None:
        return {}
    fields: dict[str, Any] = {
        "route_replay_ref": _required_text(
            "route_replay_plan.route_replay_ref",
            route_plan.get("route_replay_ref"),
        ),
        "author_ref": _required_text(
            "route_replay_plan.author_ref",
            route_plan.get("author_ref"),
        ),
        "immediate_target_ref": _required_text(
            "route_replay_plan.immediate_target_ref",
            route_plan.get("immediate_target_ref"),
        ),
    }
    for key in (
        "authoring_basis_refs",
        "source_brick_refs",
        "route_reason_refs",
        "affected_downstream_refs",
        "replay_segment_refs",
        "proof_limits",
        "not_proven",
    ):
        if key in route_plan:
            fields[key] = list(_text_tuple(f"route_replay_plan.{key}", route_plan.get(key)))
    if "max_attempts" in route_plan:
        fields["max_attempts"] = _positive_int(
            "route_replay_plan.max_attempts",
            route_plan.get("max_attempts"),
        )
    return fields

def _route_replay_capture_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    fields = _route_replay_evidence_fields(link_row)
    if "proof_limits" in fields:
        fields["route_replay_proof_limits"] = fields.pop("proof_limits")
    if "not_proven" in fields:
        fields["route_replay_not_proven"] = fields.pop("not_proven")
    return fields

def _transition_authoring_evidence_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    authoring = _transition_authoring_from_link_row(link_row)
    if authoring is None:
        return {}
    fields: dict[str, Any] = {
        "transition_authoring_ref": _required_text(
            "transition_authoring.transition_authoring_ref",
            authoring.get("transition_authoring_ref"),
        ),
        "transition_author_ref": _required_text(
            "transition_authoring.author_ref",
            authoring.get("author_ref"),
        ),
    }
    for key in (
        "authoring_basis_refs",
        "transition_reason_refs",
        "proof_limits",
        "not_proven",
    ):
        if key in authoring:
            fields[f"transition_{key}"] = list(
                _text_tuple(f"transition_authoring.{key}", authoring.get(key))
            )
    return fields

def _route_decision_basis_evidence_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    basis = _route_decision_basis_from_link_row(link_row)
    if basis is None:
        return {}
    fields: dict[str, Any] = {}
    for key in (
        "adopted_transition_concern_refs",
        "not_adopted_transition_concern_refs",
        "override_refs",
        "reviewer_observation_refs",
        "human_review_refs",
        "proof_limits",
        "not_proven",
    ):
        if key in basis:
            fields[f"route_decision_{key}"] = list(
                _text_tuple(f"route_decision_basis.{key}", basis.get(key))
            )
    return fields

def _transition_lifecycle_evidence_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    lifecycle = _transition_lifecycle_from_link_row(link_row)
    if lifecycle is None:
        return {}
    fields: dict[str, Any] = {
        "transition_lifecycle_state": _required_text(
            "transition_lifecycle.state",
            lifecycle.get("state"),
        ),
        "transition_lifecycle_progress_state": _required_text(
            "transition_lifecycle.progress_state",
            lifecycle.get("progress_state"),
        ),
    }
    for key in (
        "paused_at_ref",
        "resumed_from_ref",
        "from_brick_ref",
        "pending_target_ref",
        "required_disposition_owner",
        "disposition_action",
    ):
        if key in lifecycle:
            fields[f"transition_lifecycle_{key}"] = _required_text(
                f"transition_lifecycle.{key}",
                lifecycle.get(key),
            )
    if "budget_increment" in lifecycle:
        fields["transition_lifecycle_budget_increment"] = _positive_int(
            "transition_lifecycle.budget_increment",
            lifecycle.get("budget_increment"),
        )
    for key in ("reason_refs", "proof_limits", "not_proven"):
        if key in lifecycle:
            fields[f"transition_lifecycle_{key}"] = list(
                _text_tuple(f"transition_lifecycle.{key}", lifecycle.get(key))
            )
    return fields

def _building_lifecycle_from_link_row(link_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = link_row.get(_BUILDING_LIFECYCLE_KEY)
    if value is None:
        return None
    return _mapping("building_lifecycle", value)

def _building_lifecycle_evidence_fields(link_row: Mapping[str, Any]) -> dict[str, Any]:
    lifecycle = _building_lifecycle_from_link_row(link_row)
    if lifecycle is None:
        return {}
    fields: dict[str, Any] = {
        "building_lifecycle_state": _required_text(
            "building_lifecycle.state",
            lifecycle.get("state"),
        ),
    }
    if "reason" in lifecycle:
        fields["building_lifecycle_reason"] = _required_text(
            "building_lifecycle.reason",
            lifecycle.get("reason"),
        )
    for key in ("proof_limits", "not_proven"):
        if key in lifecycle:
            fields[f"building_lifecycle_{key}"] = list(
                _text_tuple(f"building_lifecycle.{key}", lifecycle.get(key))
            )
    return fields

def _route_replay_single_edge_fields(
    link_row: Mapping[str, Any],
    *,
    source_ref: str,
    target_ref: str,
) -> dict[str, Any]:
    route_plan = _route_replay_plan_from_link_row(link_row)
    if route_plan is None:
        return {}
    immediate_target = _required_text(
        "route_replay_plan.immediate_target_ref",
        route_plan.get("immediate_target_ref"),
    )
    if target_ref != immediate_target:
        return {}
    fields = _route_replay_evidence_fields(link_row)
    fields["edge_role"] = "reroute"
    fields["source_brick_instance_ref"] = source_ref
    fields["target_brick_instance_ref"] = target_ref
    return fields

def _route_replay_edge_metadata(
    step_results: tuple[BuildingRunSupportResult, ...],
) -> dict[tuple[str, str], dict[str, Any]]:
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for result in step_results:
        prepared = result.preparation
        route_plan = _route_replay_plan_from_link_row(prepared.step_rows.link_row)
        if route_plan is None:
            continue
        route_fields = _route_replay_evidence_fields(prepared.step_rows.link_row)
        immediate_target = _required_text(
            "route_replay_plan.immediate_target_ref",
            route_plan.get("immediate_target_ref"),
        )
        _put_route_edge_metadata(
            metadata,
            (prepared.brick_instance_ref, immediate_target),
            {"edge_role": "reroute", **route_fields},
        )
        replay_chain = [immediate_target, *route_fields.get("replay_segment_refs", [])]
        for index, (source_ref, target_ref) in enumerate(zip(replay_chain, replay_chain[1:]), start=1):
            _put_route_edge_metadata(
                metadata,
                (source_ref, target_ref),
                {
                    "edge_role": "replay_segment",
                    "route_replay_ref": route_fields["route_replay_ref"],
                    "replay_segment_index": index,
                },
            )
    return metadata

def _put_route_edge_metadata(
    metadata: dict[tuple[str, str], dict[str, Any]],
    key: tuple[str, str],
    value: dict[str, Any],
) -> None:
    existing = metadata.get(key)
    if existing is not None and existing != value:
        raise ValueError("route_replay_plan creates conflicting edge metadata")
    metadata[key] = value
