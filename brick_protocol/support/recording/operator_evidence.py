"""Contract-derived emitters for accumulated-Building operator evidence.

P-evidence-arch increment 2 / ζ6. These emitters BUILD the lifecycle capture
events, the per-step building-map rows (brick_instances / agent_bindings /
link_edges), and the frontier observation by ITERATING the canonical evidence-
shape contract in ``brick_protocol/support/recording/contracts.py`` -- they do not hand-write the
record dicts. ``brick_protocol/support/operator/evidence_assembly.py`` CALLS these emitters; it
no longer inlines the record literals. Because the shape is iterated from the
contract, an emitter cannot silently drop a contract-required field or add an
undeclared one: the ζ6 checker derives the same expected shape from the contract
and rejects drift.

AXIS BOUNDARY SEPARATION: this module imports ONLY
``brick_protocol.support.recording.contracts``. It imports NO Brick, Agent, Link,
or operator axis module. Each axis field-set is derived from ITS axis contract
backbone (brick_instances from Brick, agent_bindings from Agent, link_edges from
Link; each of the 8 capture events from the relevant axis).

These are SUPPORT RECORDING shapes only. They are NOT a new BAL fact class, NOT a
fourth axis. They carry NO Movement authority and make NO success / quality /
fault judgment. ``axis_attribution`` is a FACT label of which axis an event
observes -- it is not a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.support.recording.contracts import (
    CAPTURE_EVENT_AXIS_ATTRIBUTION,
    CAPTURE_EVENT_ID,
    CAPTURE_EVENT_ROLE,
    CAPTURE_EVENT_TYPES,
    FRONTIER_OBSERVATION_AGENT_INCOMPLETE_KIND,
    FRONTIER_OBSERVATION_CHAT_SESSION_PARKED_KIND,
    FRONTIER_OBSERVATION_PROOF_LIMITS,
    building_map_agent_binding_specs,
    building_map_brick_instance_specs,
    building_map_link_edge_specs,
    capture_event_field_specs,
    frontier_observation_specs,
)


def _build_from_specs(
    specs: Any,
    values: Mapping[str, Any],
    *,
    record_label: str,
) -> dict[str, Any]:
    """Build a record dict by ITERATING the contract field-spec, in spec order.

    Every REQUIRED field declared by the contract must be supplied in ``values``
    (a missing required value is an emitter defect, not silent drift). Only declared
    fields are emitted, so an undeclared key cannot be added by accident. OPTIONAL
    fields are emitted only when supplied. The emitted key order follows the spec
    order so the on-disk shape is byte-identical to the prior inline literal.
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


# ---------------------------------------------------------------------------
# Capture-event lifecycle emitters (the 8 events, one helper per axis backbone)
# ---------------------------------------------------------------------------


def _build_capture_event(
    event_type: str,
    *,
    raw_ref: str,
    not_proven: list[str],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one capture event from the contract field-spec for ``event_type``.

    The header (event_id, event_type, role_in_event, axis_attribution) literals are
    read from the contract; ``raw_ref`` / ``not_proven`` and the per-event payload
    fields are supplied by the caller. The spec ORDER is the canonical key order.
    """

    values: dict[str, Any] = {
        "event_id": CAPTURE_EVENT_ID[event_type],
        "event_type": event_type,
        "role_in_event": CAPTURE_EVENT_ROLE[event_type],
        "axis_attribution": CAPTURE_EVENT_AXIS_ATTRIBUTION[event_type],
        "raw_ref": raw_ref,
        "not_proven": list(not_proven),
    }
    values.update(payload)
    return _build_from_specs(
        capture_event_field_specs(event_type),
        values,
        record_label=f"capture_event:{event_type}",
    )


def build_capture_events(
    *,
    raw_ref: str,
    not_proven: list[str],
    payloads: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit the 8 lifecycle capture events, in canonical order, from the contract.

    ``payloads`` maps event_type -> the per-event payload fields (building_ref /
    brick_ref / actor_ref / public_fact_refs / receipt_text / facts) the caller
    derived from the relevant axis. The header (event_id, role, axis_attribution)
    comes from the contract. The event order is ``CAPTURE_EVENT_TYPES``.
    """

    missing = [event_type for event_type in CAPTURE_EVENT_TYPES if event_type not in payloads]
    if missing:
        raise ValueError(f"build_capture_events: missing payload(s) for {missing}")
    return [
        _build_capture_event(
            event_type,
            raw_ref=raw_ref,
            not_proven=not_proven,
            payload=payloads[event_type],
        )
        for event_type in CAPTURE_EVENT_TYPES
    ]


# ---------------------------------------------------------------------------
# Building-map per-step row emitters (Brick / Agent / Link axis backbones)
# ---------------------------------------------------------------------------


def build_brick_instance_row(
    *,
    brick_instance_id: str,
    brick_work_ref: str,
    attempt_index: int,
    agent_binding_refs: list[str],
    raw_refs: list[Any],
    proof_limits: list[str],
    not_proven: list[str],
) -> dict[str, Any]:
    """Emit a building-map brick_instance row from the BRICK contract backbone."""

    values: dict[str, Any] = {
        "brick_instance_id": brick_instance_id,
        "brick_work_ref": brick_work_ref,
        "attempt_index": attempt_index,
        "agent_binding_refs": agent_binding_refs,
        "raw_refs": raw_refs,
        "proof_limits": proof_limits,
        "not_proven": not_proven,
    }
    return _build_from_specs(
        building_map_brick_instance_specs(),
        values,
        record_label="building_map.brick_instance",
    )


def build_agent_binding_row(
    *,
    agent_binding_id: str,
    brick_instance_ref: str,
    agent_performer_ref: str,
    binding_role: str,
    produced_public_fact_refs: list[str],
    step_output_ref: str,
    raw_refs: list[Any],
    proof_limits: list[str],
    not_proven: list[str],
) -> dict[str, Any]:
    """Emit a building-map agent_binding row from the AGENT contract backbone."""

    values: dict[str, Any] = {
        "agent_binding_id": agent_binding_id,
        "brick_instance_ref": brick_instance_ref,
        "agent_performer_ref": agent_performer_ref,
        "binding_role": binding_role,
        "produced_public_fact_refs": produced_public_fact_refs,
        "step_output_ref": step_output_ref,
        "raw_refs": raw_refs,
        "proof_limits": proof_limits,
        "not_proven": not_proven,
    }
    return _build_from_specs(
        building_map_agent_binding_specs(),
        values,
        record_label="building_map.agent_binding",
    )


def build_link_edge_row(
    *,
    link_edge_id: str,
    edge_role: str,
    source_brick_instance_ref: str,
    target_brick_instance_ref: str,
    input_public_fact_refs: list[str],
    public_fact_refs: list[str],
    movement_fact_ref: str,
    transition_fact_ref: str,
    step_output_ref: str,
    edge_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit a building-map link_edge row from the LINK contract backbone.

    ``edge_metadata`` overlays the route-replay layer's extra edge fields after the
    base contract fields, matching the prior ``edge.update(edge_metadata)`` order.
    """

    values: dict[str, Any] = {
        "link_edge_id": link_edge_id,
        "edge_role": edge_role,
        "source_brick_instance_ref": source_brick_instance_ref,
        "target_brick_instance_ref": target_brick_instance_ref,
        "input_public_fact_refs": input_public_fact_refs,
        "public_fact_refs": public_fact_refs,
        "movement_fact_ref": movement_fact_ref,
        "transition_fact_ref": transition_fact_ref,
        "step_output_ref": step_output_ref,
    }
    record = _build_from_specs(
        building_map_link_edge_specs(),
        values,
        record_label="building_map.link_edge",
    )
    if edge_metadata:
        record.update(edge_metadata)
    return record


# ---------------------------------------------------------------------------
# Frontier observation emitter (agent-incomplete frontier)
# ---------------------------------------------------------------------------


def build_frontier_observation(
    *,
    adapter_error_ref: str = "",
    parked_ref: str = "",
    frontier_kind: str = FRONTIER_OBSERVATION_AGENT_INCOMPLETE_KIND,
) -> dict[str, Any]:
    """Emit a stopped frontier observation from the contract.

    Records WHERE the Building stopped plus the supporting stop ref and proof
    limits. It is a FACT, NOT a verdict.
    """

    if frontier_kind not in {
        FRONTIER_OBSERVATION_AGENT_INCOMPLETE_KIND,
        FRONTIER_OBSERVATION_CHAT_SESSION_PARKED_KIND,
    }:
        raise ValueError(f"frontier_kind is not admitted for frontier observation: {frontier_kind}")
    if bool(adapter_error_ref) == bool(parked_ref):
        raise ValueError("frontier observation requires exactly one stop ref")
    values: dict[str, Any] = {
        "frontier_kind": frontier_kind,
        "proof_limits": list(FRONTIER_OBSERVATION_PROOF_LIMITS),
    }
    if adapter_error_ref:
        values["adapter_error_ref"] = adapter_error_ref
    if parked_ref:
        values["parked_ref"] = parked_ref
    return _build_from_specs(
        frontier_observation_specs(),
        values,
        record_label="frontier_observation",
    )
