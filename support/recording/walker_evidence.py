"""Contract-derived emitters for dynamic-walker support evidence.

P-evidence-arch / ζ6. These emitters BUILD the reroute-adoption record, the HOLD
record, and the structured field-set observation by ITERATING the canonical
evidence-shape contract in ``support/recording/contracts.py`` -- they do not
hand-write the record dict. The dynamic walker CALLS these emitters; it no longer
inlines the record literals. Because the shape is iterated from the contract, an
emitter cannot silently drop a required field or add an undeclared one: the ζ6
checker derives the same expected shape from the contract and rejects drift.

These are SUPPORT RECORDING shapes only. They are NESTED evidence, NOT a new BAL
fact class, NOT a fourth axis. They carry NO Movement authority and make NO
success / quality / fault judgment. The structured field observation records
field SETS and set DELTAS as FACTS -- there is no failing_axis label, no
fault/failed/success verdict; attribution is the reader's inference.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.support.recording.contracts import (
    HOLD_RECORD_KIND,
    HOLD_RECORD_SCHEMA_VERSION,
    REROUTE_ADOPTION_RECORD_KIND,
    REROUTE_ADOPTION_RECORD_SCHEMA_VERSION,
    RESUME_OBSERVATION_KIND,
    RESUME_OBSERVATION_SCHEMA_VERSION,
    STRUCTURED_FIELD_OBSERVATION_KIND,
    STRUCTURED_FIELD_OBSERVATION_SCHEMA_VERSION,
    hold_record_field_specs,
    reroute_adoption_field_specs,
    resume_observation_field_specs,
    structured_field_observation_specs,
)


def _build_from_specs(
    specs: Any,
    values: Mapping[str, Any],
    *,
    record_label: str,
) -> dict[str, Any]:
    """Build a record dict by ITERATING the contract field-spec.

    Every REQUIRED field declared by the contract must be supplied in ``values``
    (a missing required value is an emitter defect, not silent drift). Only
    declared fields are emitted, so an undeclared key cannot be added by accident.
    OPTIONAL fields are emitted only when supplied.
    """

    declared = {spec.name for spec in specs}
    undeclared = set(values) - declared
    if undeclared:
        raise ValueError(
            f"{record_label}: values carry undeclared field(s) not in the "
            f"contract: {sorted(undeclared)}"
        )
    record: dict[str, Any] = {}
    for spec in specs:
        if spec.presence == "required":
            if spec.name not in values:
                raise ValueError(
                    f"{record_label}: contract-required field {spec.name!r} was "
                    "not supplied to the emitter"
                )
            record[spec.name] = values[spec.name]
        elif spec.name in values:
            record[spec.name] = values[spec.name]
    return record


def build_reroute_adoption_record(
    *,
    reroute_ref: str,
    adoption_sequence_number: int,
    cascade_depth: int,
    parent_reroute_ref: str,
    source_step_ref: str,
    source_brick_ref: str,
    source_transition_concern_ref: str,
    transition_concern_binding: bool,
    adopted_by: str,
    immediate_target_ref: str,
    target_brick: str,
    target_step_ref: str,
    replay_segment_refs: list[str],
    attempt_number: int,
    node_budget: int,
    budget_exhausted: bool,
    disposition_required: bool,
    proof_limits: list[str],
    not_proven: list[str],
    structured_field_observation: Mapping[str, Any] | None = None,
    carry_budget_evidence_ref: str = "",
    cohort_replay_segment_refs: list[str] | None = None,
    cohort_skipped_segment_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Emit an ADOPTED reroute-landing record from the contract field-spec."""

    values: dict[str, Any] = {
        "kind": REROUTE_ADOPTION_RECORD_KIND,
        "schema_version": REROUTE_ADOPTION_RECORD_SCHEMA_VERSION,
        "reroute_ref": reroute_ref,
        "adoption_sequence_number": adoption_sequence_number,
        "cascade_depth": cascade_depth,
        "parent_reroute_ref": parent_reroute_ref,
        "source_step_ref": source_step_ref,
        "source_brick_ref": source_brick_ref,
        "source_transition_concern_ref": source_transition_concern_ref,
        "transition_concern_binding": transition_concern_binding,
        "adopted_by": adopted_by,
        "immediate_target_ref": immediate_target_ref,
        "target_brick": target_brick,
        "target_step_ref": target_step_ref,
        "replay_segment_refs": replay_segment_refs,
        "attempt_number": attempt_number,
        "node_budget": node_budget,
        "budget_exhausted": budget_exhausted,
        "disposition_required": disposition_required,
        "proof_limits": proof_limits,
        "not_proven": not_proven,
    }
    if structured_field_observation is not None:
        values["structured_field_observation"] = dict(structured_field_observation)
    if carry_budget_evidence_ref:
        values["carry_budget_evidence_ref"] = carry_budget_evidence_ref
    if cohort_replay_segment_refs:
        values["cohort_replay_segment_refs"] = list(cohort_replay_segment_refs)
    if cohort_skipped_segment_refs:
        values["cohort_skipped_segment_refs"] = list(cohort_skipped_segment_refs)
    return _build_from_specs(
        reroute_adoption_field_specs(),
        values,
        record_label="reroute_adoption_record",
    )


def build_hold_record(
    *,
    reroute_ref: str,
    adoption_sequence_number: int,
    cascade_depth: int,
    parent_reroute_ref: str,
    source_step_ref: str,
    source_brick_ref: str,
    source_transition_concern_ref: str,
    transition_concern_binding: bool,
    immediate_target_ref: str,
    target_brick: str,
    pending_target_ref: str,
    attempt_number: int,
    node_budget: int,
    budget_exhausted: bool,
    disposition_required: bool,
    hold_reason: str,
    required_disposition_owner: str,
    transition_lifecycle_state: str,
    proof_limits: list[str],
    not_proven: list[str],
    structured_field_observation: Mapping[str, Any] | None = None,
    carry_budget_evidence_ref: str = "",
) -> dict[str, Any]:
    """Emit a HOLD record (not adopted; disposition_required) from the contract.

    Support HALTS and RECORDS. It does NOT decide raise/forward/stop -- the
    human/COO authors the disposition as a Link row at the budget boundary.
    """

    values: dict[str, Any] = {
        "kind": HOLD_RECORD_KIND,
        "schema_version": HOLD_RECORD_SCHEMA_VERSION,
        "reroute_ref": reroute_ref,
        "adoption_sequence_number": adoption_sequence_number,
        "cascade_depth": cascade_depth,
        "parent_reroute_ref": parent_reroute_ref,
        "source_step_ref": source_step_ref,
        "source_brick_ref": source_brick_ref,
        "source_transition_concern_ref": source_transition_concern_ref,
        "transition_concern_binding": transition_concern_binding,
        "immediate_target_ref": immediate_target_ref,
        "target_brick": target_brick,
        "pending_target_ref": pending_target_ref,
        "attempt_number": attempt_number,
        "node_budget": node_budget,
        "budget_exhausted": budget_exhausted,
        "disposition_required": disposition_required,
        "hold_reason": hold_reason,
        "required_disposition_owner": required_disposition_owner,
        "transition_lifecycle_state": transition_lifecycle_state,
        "proof_limits": proof_limits,
        "not_proven": not_proven,
    }
    if structured_field_observation is not None:
        values["structured_field_observation"] = dict(structured_field_observation)
    if carry_budget_evidence_ref:
        values["carry_budget_evidence_ref"] = carry_budget_evidence_ref
    return _build_from_specs(
        hold_record_field_specs(),
        values,
        record_label="hold_record",
    )


def build_resume_observation(
    *,
    resumed_from: str,
    paused_at_ref: str,
    pending_target_ref: str,
    disposition_action: str,
    applied: str,
    budget_increment: int,
    node_budget: int,
    node_landings: int,
    proof_limits: list[str],
    not_proven: list[str],
    disposition_row_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit a resume-after-HOLD observation from the contract field-spec.

    The human/COO-authored disposition is already declared on a Link
    transition_lifecycle row. This support record only records what was replayed
    and applied; it does not choose raise, forward, stop, or a budget amount.

    FIX 3 (0611): ``disposition_row_provenance`` (optional, data only) persists
    the SELECTED disposition row's discriminator -- the generation-unique hold
    identity + the row's own raw_ref (+ the pre-resume-snapshot match index) --
    so the selection stays replayable AFTER the resume rewrites raw/link.jsonl
    (the transient in-memory seed alone would dangle).
    """

    values: dict[str, Any] = {
        "kind": RESUME_OBSERVATION_KIND,
        "schema_version": RESUME_OBSERVATION_SCHEMA_VERSION,
        "resumed_from": resumed_from,
        "paused_at_ref": paused_at_ref,
        "pending_target_ref": pending_target_ref,
        "disposition_action": disposition_action,
        "applied": applied,
        "budget_increment": budget_increment,
        "node_budget": node_budget,
        "node_landings": node_landings,
        "proof_limits": proof_limits,
        "not_proven": not_proven,
    }
    if disposition_row_provenance:
        values["disposition_row_provenance"] = dict(disposition_row_provenance)
    return _build_from_specs(
        resume_observation_field_specs(),
        values,
        record_label="dynamic_walker_resume_observation",
    )


def build_structured_field_observation(
    *,
    brick_required_fields: list[str],
    observed_fields: list[str],
    gate_required_fields: list[str],
) -> dict[str, Any]:
    """Emit a structured field-set observation (no judgment) from the contract.

    Records the field SETS (what Brick declared, what Agent returned, what the
    gate required) and the set DELTAS as FACTS. NO failing_axis label, NO
    fault/failed/success verdict -- attribution is the reader's inference. The
    deltas are computed mechanically (set difference), not judged.
    """

    brick_set = _ordered_unique(brick_required_fields)
    observed_set = _ordered_unique(observed_fields)
    gate_set = _ordered_unique(gate_required_fields)
    demanded = list(brick_set) + [name for name in gate_set if name not in brick_set]
    missing_from_observed = [name for name in demanded if name not in observed_set]
    demanded_beyond_brick = [name for name in gate_set if name not in brick_set]
    values: dict[str, Any] = {
        "kind": STRUCTURED_FIELD_OBSERVATION_KIND,
        "schema_version": STRUCTURED_FIELD_OBSERVATION_SCHEMA_VERSION,
        "brick_required_fields": list(brick_set),
        "observed_fields": list(observed_set),
        "gate_required_fields": list(gate_set),
        "missing_from_observed": missing_from_observed,
        "demanded_beyond_brick": demanded_beyond_brick,
    }
    return _build_from_specs(
        structured_field_observation_specs(),
        values,
        record_label="structured_field_observation",
    )


def _ordered_unique(values: Any) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if not isinstance(values, (list, tuple)):
        return ordered
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered
