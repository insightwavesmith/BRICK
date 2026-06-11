"""HOLD construction + paused-lifecycle injection for the dynamic walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
HOLD RerouteAdoptionRecord builder, the paused transition_lifecycle injection
(so observe_building_frontier reports link_paused / disposition_required), the
resumed-lifecycle builder, and the held-source replay/relifecycle were lifted out
of the dynamic_walker god-module into this single-concern collaborator.

On budget exhaustion or a human/coo gate, support HALTS and RECORDS a HOLD with
required_disposition_owner=caller-or-coo. It does NOT decide raise/forward/stop --
the human/COO authors that as a Link row at the budget boundary (ζ7).

Support mechanics only. Homes NO axis crossing (the HOLD record is built from the
recording contract field-spec). Judges no success or quality; chooses no Movement.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import _optional_text_value
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
    NOT_PROVEN,
    PROOF_LIMITS,
    RESUME_NOT_PROVEN,
)
from brick_protocol.support.operator.walker_reroute_budget import (
    _carry_budget_evidence_ref,
    _positive_int,
)
from brick_protocol.support.operator.walker_step_fixture import (
    _structured_field_observation_for_step,
)
from brick_protocol.support.recording.walker_evidence import build_hold_record


def _build_hold(
    *,
    building_id: str,
    plan_ref: str,
    source_step_ref: str,
    source_brick_ref: str,
    target_brick: str,
    concern: Mapping[str, Any],
    cascade_depth: int,
    parent_reroute_ref: str,
    adoption_sequence_number: int,
    node_budget: int,
    attempt_number: int,
    budget_exhausted: bool,
    hold_reason: str,
    required_disposition_owner: str = "caller-or-coo",
    step: Mapping[str, Any],
    step_result: BuildingRunSupportResult,
) -> Mapping[str, Any]:
    """Build a HOLD RerouteAdoptionRecord (not adopted; disposition_required).

    CONTRACT-DERIVED emission (ζ6): the record is built FROM the recording
    contract field-spec via support/recording/walker_evidence.build_hold_record
    -- no inline dict literal. Support HALTS and RECORDS. It does NOT decide
    raise/forward/stop -- the human/COO authors that as a Link row at the budget
    boundary (ζ7).
    """

    return build_hold_record(
        reroute_ref=(
            f"reroute-hold:{building_id}:{adoption_sequence_number:02d}:"
            f"{target_brick.replace(':', '-')}"
        ),
        adoption_sequence_number=adoption_sequence_number,
        cascade_depth=cascade_depth,
        parent_reroute_ref=parent_reroute_ref,
        source_step_ref=source_step_ref,
        source_brick_ref=source_brick_ref,
        source_transition_concern_ref=_optional_text_value(concern.get("concern_ref")) or "",
        transition_concern_binding=False,
        immediate_target_ref=target_brick,
        target_brick=target_brick,
        pending_target_ref=target_brick,
        attempt_number=attempt_number,
        node_budget=node_budget,
        budget_exhausted=budget_exhausted,
        disposition_required=True,
        hold_reason=hold_reason,
        required_disposition_owner=required_disposition_owner,
        transition_lifecycle_state="paused",
        proof_limits=list(PROOF_LIMITS),
        not_proven=list(NOT_PROVEN),
        # Structured field-set observation (no judgment): the field SETS at this
        # HOLD boundary as FACTS + set deltas. NO failing_axis / fault / success.
        structured_field_observation=_structured_field_observation_for_step(
            step, step_result
        ),
        carry_budget_evidence_ref=_carry_budget_evidence_ref(
            building_id,
            target_brick,
        ),
    )


def _hold_paused_at_ref(hold_record: Mapping[str, Any]) -> str:
    reroute_ref = _optional_text_value(hold_record.get("reroute_ref")) or "reroute-hold:unknown"
    return "link-transition:" + reroute_ref.replace(":", "-")


def _resumed_lifecycle_from_hold(
    hold_record: Mapping[str, Any],
    *,
    paused_at_ref: str,
    disposition_action: str,
    budget_increment: Any,
) -> Mapping[str, Any]:
    lifecycle: dict[str, Any] = {
        "state": "resumed",
        "progress_state": "in_progress",
        "paused_at_ref": paused_at_ref,
        "resumed_from_ref": paused_at_ref,
        "from_brick_ref": _optional_text_value(hold_record.get("source_brick_ref")) or "brick-unknown",
        "pending_target_ref": _optional_text_value(hold_record.get("pending_target_ref"))
        or _optional_text_value(hold_record.get("target_brick"))
        or "brick-unknown",
        "required_disposition_owner": _optional_text_value(
            hold_record.get("required_disposition_owner")
        )
        or "caller-or-coo",
        "disposition_action": disposition_action,
        "reason_refs": [
            str(hold_record.get("source_transition_concern_ref") or "transition-concern:hold"),
            f"observation:reroute-hold-reason-{hold_record.get('hold_reason', 'budget_exhausted')}",
        ],
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(RESUME_NOT_PROVEN),
    }
    if budget_increment is not None:
        lifecycle["budget_increment"] = _positive_int(
            budget_increment,
            "transition_lifecycle.budget_increment",
        )
    return lifecycle


def _replace_held_source_with_lifecycle(
    step_results: list[BuildingRunSupportResult],
    *,
    hold_record: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    building_lifecycle: Mapping[str, Any] | None,
    boundary_ref: str | None,
    author_ref: str,
    replay_step,
    checked_proof_limits: tuple[str, ...],
) -> list[BuildingRunSupportResult]:
    source_step_ref = _optional_text_value(hold_record.get("source_step_ref")) or ""
    target_index = len(step_results) - 1
    for index in range(len(step_results) - 1, -1, -1):
        if step_results[index].preparation.step_rows.step_ref == source_step_ref:
            target_index = index
            break
    source_result = step_results[target_index]
    prepared = source_result.preparation
    rows = [
        dict(prepared.step_rows.brick_row),
        dict(prepared.step_rows.agent_row),
        dict(prepared.step_rows.link_row),
    ]
    link_row = rows[2]
    link_row["transition_lifecycle"] = dict(lifecycle)
    link_row["transition_authoring"] = {
        "transition_authoring_ref": (
            "link-authoring:resume-disposition:"
            + prepared.building_id
            + ":"
            + prepared.step_rows.step_ref
        ),
        "author_ref": author_ref,
        "authoring_basis_refs": list(lifecycle.get("reason_refs", ()))
        or ["transition-concern:hold"],
    }
    if building_lifecycle is not None:
        link_row["building_lifecycle"] = dict(building_lifecycle)
    if boundary_ref is not None:
        link_row["target_ref"] = boundary_ref
        link_row["next_brick_instance_ref"] = boundary_ref
    fixture = {
        "building_id": prepared.building_id,
        "selected_adapter_ref": source_result.adapter_result.request.adapter_ref,
        "selected_model_ref": source_result.adapter_result.request.selected_model_ref,
        "step_rows": {
            "step_ref": prepared.step_rows.step_ref,
            "rows": rows,
        },
        "caller_supplied_link_facts": _caller_supplied_link_facts_for_replay(
            prepared.step_rows.step_ref,
            link_row,
        ),
    }
    replayed = replay_step(
        fixture,
        returned_value=source_result.adapter_result.returned_value,
        recorded_at=source_result.recorded_at,
        proof_limits=checked_proof_limits,
    )
    # U5.5 RESUME-GATE-RECORD: this lifecycle re-replay re-runs replay_step for the
    # held SOURCE step without its recorded gate record, so it would drop the
    # gate-sequence decision that the FIRST replay (_replay_recorded_step_results)
    # already RECONSTRUCTED from the step's AT-TIME record. Carry that already-read
    # decision forward via a partial replace so the held source step's gate facts
    # are not lost. This READS the prior reconstructed decision — no recompute.
    if source_result.gate_sequence_decision is not None:
        replayed = dataclasses.replace(
            replayed,
            gate_sequence_decision=source_result.gate_sequence_decision,
        )
    new_results = list(step_results)
    new_results[target_index] = replayed
    return new_results


def _caller_supplied_link_facts_for_replay(
    step_ref: str,
    link_row: Mapping[str, Any],
) -> Mapping[str, Any]:
    movement = _optional_text_value(link_row.get("movement")) or "forward"
    target = (
        _optional_text_value(link_row.get("next_brick_instance_ref"))
        or _optional_text_value(link_row.get("target_ref"))
        or _optional_text_value(link_row.get("target"))
        or "building-boundary:unknown"
    )
    return {
        "movement_fact": {
            "movement": movement,
            "reason": "recorded Link row replay for resume_building_plan",
            "handoff_target_fact": target,
        },
        "transition_fact": {
            "movement": movement,
            "target_fact": target,
            "handoff_reference": step_ref,
            "not_proven": list(RESUME_NOT_PROVEN),
        },
    }


def _inject_hold_paused_link(
    step_results: list[BuildingRunSupportResult],
    hold_record: Mapping[str, Any],
) -> list[BuildingRunSupportResult]:
    """Inject a paused transition_lifecycle onto the HOLD source step's Link row.

    The paused Link record makes observe_building_frontier report frontier_kind
    == link_paused (disposition_required = a human/Link gate). The lifecycle
    carries pending_target_ref + required_disposition_owner=caller-or-coo + the
    cascade lineage, so the frontier surfaces the disposition the human/COO must
    author. Support never resumes/forwards/stops on its own.
    """

    if not step_results:
        return step_results
    source_step_ref = hold_record.get("source_step_ref")
    target_index = len(step_results) - 1
    for index in range(len(step_results) - 1, -1, -1):
        if step_results[index].preparation.step_rows.step_ref == source_step_ref:
            target_index = index
            break
    source_result = step_results[target_index]
    lifecycle = {
        "state": "paused",
        "progress_state": "in_progress",
        "paused_at_ref": _hold_paused_at_ref(hold_record),
        "from_brick_ref": _optional_text_value(hold_record.get("source_brick_ref")) or "brick-unknown",
        "pending_target_ref": _optional_text_value(hold_record.get("pending_target_ref"))
        or _optional_text_value(hold_record.get("target_brick"))
        or "brick-unknown",
        "required_disposition_owner": _optional_text_value(
            hold_record.get("required_disposition_owner")
        )
        or "caller-or-coo",
        "reason_refs": [
            str(hold_record.get("source_transition_concern_ref") or "transition-concern:hold"),
            f"observation:reroute-hold-reason-{hold_record.get('hold_reason', 'budget_exhausted')}",
        ],
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    patched = _step_result_with_paused_lifecycle(source_result, lifecycle)
    new_results = list(step_results)
    new_results[target_index] = patched
    return new_results


def _inject_fan_in_paused_link(
    step_results: list[BuildingRunSupportResult],
    hold_record: Mapping[str, Any],
) -> list[BuildingRunSupportResult]:
    """Surface a fan-in wait_all hold through the existing link_paused frontier."""

    if not step_results:
        return step_results
    source_step_ref = hold_record.get("pause_source_step_ref")
    target_index = len(step_results) - 1
    for index in range(len(step_results) - 1, -1, -1):
        if step_results[index].preparation.step_rows.step_ref == source_step_ref:
            target_index = index
            break
    source_result = step_results[target_index]
    observation = hold_record.get("fan_in_wait_all_observation")
    missing_sources: list[str] = []
    if isinstance(observation, Mapping):
        missing_sources = [
            str(ref)
            for ref in observation.get("missing_source_step_refs", [])
            if str(ref)
        ]
    lifecycle = {
        "state": "paused",
        "progress_state": "in_progress",
        "paused_at_ref": _hold_paused_at_ref(hold_record),
        "from_brick_ref": _optional_text_value(hold_record.get("source_brick_ref"))
        or source_result.preparation.brick_instance_ref,
        "pending_target_ref": _optional_text_value(hold_record.get("pending_target_ref"))
        or _optional_text_value(hold_record.get("target_brick"))
        or "brick-unknown",
        "required_disposition_owner": "caller-or-coo",
        "reason_refs": [
            f"fan-in-wait-all:{hold_record.get('target_step_ref', 'unknown')}",
            *[f"fan-in-missing-source:{source}" for source in missing_sources],
        ],
        "proof_limits": list(FAN_TOPOLOGY_PROOF_LIMITS),
        "not_proven": list(FAN_TOPOLOGY_NOT_PROVEN),
    }
    patched = _step_result_with_paused_lifecycle(source_result, lifecycle)
    new_results = list(step_results)
    new_results[target_index] = patched
    return new_results


def _step_result_with_paused_lifecycle(
    step_result: BuildingRunSupportResult,
    lifecycle: Mapping[str, Any],
) -> BuildingRunSupportResult:
    prepared = step_result.preparation
    step_rows = prepared.step_rows
    link_row = dict(step_rows.link_row)
    link_row["transition_lifecycle"] = dict(lifecycle)
    new_step_rows = dataclasses.replace(step_rows, link_row=link_row)
    new_prepared = dataclasses.replace(prepared, step_rows=new_step_rows)
    return dataclasses.replace(step_result, preparation=new_prepared)
