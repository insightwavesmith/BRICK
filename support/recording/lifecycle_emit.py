"""Building lifecycle + capture-event packet emitter.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
accumulated-Building lifecycle packet, the single-Agent-run lifecycle mapping,
the per-step accumulated capture event, the accumulated raw manifest, and the
mapping->BuildingLifecyclePacket / CaptureEvent converters that
``support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern emitter. A2: the lifecycle capture events are
CONTRACT-DERIVED -- ``support/recording/operator_evidence.py`` builds each event
from the capture-event field-spec in ``support/recording/contracts.py``; this
emitter supplies the per-event payload only. Authors no Movement or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    MinimalCrossingRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.plan_graph import _graph_link_raw_refs
from brick_protocol.support.operator.plan_validation import (
    _building_lifecycle_evidence_fields,
    _route_decision_basis_evidence_fields,
    _route_replay_capture_fields,
    _transition_authoring_evidence_fields,
    _transition_lifecycle_evidence_fields,
)
from brick_protocol.support.operator.primitives import (
    _agent_run_not_proven,
    _event_raw_ref,
    _mapping,
    _merge_texts,
    _optional_text_or_none,
    _proof_limits_tuple,
    _raw_ref,
    _require_mapping_value,
    _required_text,
    _resource_slug,
    _text_tuple,
)
from brick_protocol.support.recording.capture import (
    BuildingLifecyclePacket,
    CaptureEvent,
)
from brick_protocol.support.recording.claims_common import (
    _manifest_not_proven,
    _step_output_manifest_refs,
)
from brick_protocol.support.recording.operator_evidence import build_capture_events
from brick_protocol.support.recording.declaration_packets import (
    _DECLARATION_EVIDENCE_REFS,
    _plan_snapshot,
)


def _accumulated_lifecycle_packet(
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
    task_source_ref: str | None = None,
) -> BuildingLifecyclePacket:
    if not step_results:
        raise ValueError("accumulated Building plan requires at least one step")
    first_work = step_results[0].preparation.brick_work
    not_proven = _merge_texts(plan.get("not_proven"), *(result.not_proven for result in step_results))
    events: list[CaptureEvent] = []
    for index, result in enumerate(step_results, start=1):
        step_ref = result.preparation.step_rows.step_ref
        lifecycle = _lifecycle_packet_from_mapping(
            result.completion.lifecycle_packet_mapping,
            movement=result.completion.crossing_record.link_fact.movement,
        )
        for event in lifecycle.capture_events:
            events.append(_accumulated_capture_event(event, index, step_ref, building_id))
    raw_manifest = _accumulated_raw_manifest(
        building_id,
        step_results,
        graph_context,
    )
    building_work = {
        "work_statement": first_work.work_statement,
        "comparison_rule": first_work.comparison_rule,
        "required_return_shape": first_work.required_return_shape,
        "source_facts": list(_merge_texts(first_work.source_facts, plan.get("raw_refs"))),
        "building_id": building_id,
        "plan_ref": plan_ref,
        "step_refs": [result.preparation.step_rows.step_ref for result in step_results],
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    evidence_manifest = {
        "building_id": building_id,
        "plan_ref": plan_ref,
        "raw_manifest_ref": "raw/raw-manifest.json",
        "raw_stream_refs": [
            "raw/brick-work.jsonl",
            "raw/agent-return.jsonl",
            "raw/link.jsonl",
        ],
        "claim_trace_refs": [
            "evidence/claim_trace/brick/work_contract.json",
            "evidence/claim_trace/agent/returned_claims.json",
            "evidence/claim_trace/link/transfer_trace.json",
            "evidence/claim_trace/link/carry_trace.json",
            "evidence/claim_trace/link/sufficiency_trace.json",
            "evidence/claim_trace/link/movement_trace.json",
        ],
        "step_output_refs": _step_output_manifest_refs(step_results),
        "building_map_ref": "work/building-map.json",
        "declaration_evidence_refs": list(_DECLARATION_EVIDENCE_REFS),
        "plan_snapshot": _plan_snapshot(plan_ref, plan),
        "proof_limits": list(proof_limits),
        "not_proven": list(_manifest_not_proven(not_proven)),
    }
    if task_source_ref:
        building_work["task_source_ref"] = task_source_ref
        evidence_manifest["task_source_ref"] = task_source_ref
    execution_path = _optional_text_or_none(plan.get("execution_path"))
    if execution_path:
        # Record-only provenance marker (not a fact, not a Movement). run.py's
        # plan walk never declares execution_path, so its evidence is unchanged;
        # POSITION-A native dispatch declares execution_path="native-dispatch" so
        # the evidence shows the Building was NOT produced by run.py's walk.
        building_work["execution_path"] = execution_path
        evidence_manifest["execution_path"] = execution_path
    return BuildingLifecyclePacket(
        building_id=building_id,
        building_work=building_work,
        capture_events=tuple(events),
        raw_manifest=raw_manifest,
        evidence_manifest=evidence_manifest,
        proof_limits=proof_limits,
    )


def _accumulated_capture_event(
    event: CaptureEvent,
    step_index: int,
    step_ref: str,
    building_id: str,
) -> CaptureEvent:
    prefix = _resource_slug("step_ref", step_ref.replace(":", "-"))
    facts = dict(event.facts)
    facts["step_ref"] = step_ref
    return CaptureEvent(
        event_id=f"{step_index:02d}-{prefix}-{event.event_id}",
        event_type=event.event_type,
        role_in_event=event.role_in_event,
        axis_attribution=event.axis_attribution,
        raw_ref=_event_raw_ref(event.event_type, step_index),
        not_proven=event.not_proven,
        source_truth=False,
        actor_ref=event.actor_ref,
        building_ref=building_id if event.event_type == "building_opened" else event.building_ref,
        brick_ref=event.brick_ref,
        public_fact_refs=event.public_fact_refs,
        receipt_text=event.receipt_text,
        facts=facts,
    )


def _accumulated_raw_manifest(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    graph_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    graph_raw_refs = _graph_link_raw_refs(graph_context)
    return {
        "building_id": building_id,
        "raw_refs": [
            ref
            for index in range(1, len(step_results) + 1)
            for ref in (_raw_ref("brick", index), _raw_ref("agent", index), _raw_ref("link", index))
        ]
        + graph_raw_refs,
        "entries": [
            {
                "path": "raw/brick-work.jsonl",
                "source": "support/operator/run.py run_building_plan declared Brick rows",
                "content_shape": "jsonl Brick work rows",
                "proof_limit": "support evidence only",
                "axis_owner": "Brick",
                "record_role": "primary",
                "raw_refs": [_raw_ref("brick", index) for index in range(1, len(step_results) + 1)],
            },
            {
                "path": "raw/agent-return.jsonl",
                "source": "support/operator/run.py run_building_plan closed AgentFact returns",
                "content_shape": "jsonl Agent returned payload refs",
                "proof_limit": "support evidence only",
                "axis_owner": "Agent",
                "record_role": "primary",
                "raw_refs": [_raw_ref("agent", index) for index in range(1, len(step_results) + 1)],
            },
            {
                "path": "raw/link.jsonl",
                "source": "support/operator/run.py run_building_plan declared Link rows",
                "content_shape": "jsonl Link Movement and transition refs",
                "proof_limit": "support evidence only",
                "axis_owner": "Link",
                "record_role": "primary",
                "raw_refs": [_raw_ref("link", index) for index in range(1, len(step_results) + 1)]
                + graph_raw_refs,
            },
        ],
    }


def agent_run_lifecycle_mapping(
    prepared: AgentRunPreparationRecord,
    crossing_record: MinimalCrossingRecord,
    *,
    building_map_packet: Mapping[str, Any],
    proof_limits: Iterable[str] | str | None = None,
    not_proven: Iterable[str] | str | None = None,
) -> dict[str, Any]:
    """Create a mapping convertible to BuildingLifecyclePacket/CaptureEvent."""

    if not isinstance(prepared, AgentRunPreparationRecord):
        raise TypeError("prepared must be AgentRunPreparationRecord")
    if not isinstance(crossing_record, MinimalCrossingRecord):
        raise TypeError("crossing_record must be MinimalCrossingRecord")
    _require_mapping_value("building_map_packet", building_map_packet)
    checked_proof_limits = _proof_limits_tuple(proof_limits or prepared.proof_limits)
    checked_not_proven = _text_tuple("not_proven", not_proven or _agent_run_not_proven())
    agent_public_ref = f"agent-performer:{prepared.agent_object.object_ref}"
    agent_fact_ref = f"agent-fact:{prepared.building_id}:{prepared.agent_object.object_ref}"
    comparison_ref = f"brick-comparison:{prepared.building_id}"
    link_public_ref = f"link-fact:{prepared.building_id}"
    transition_ref = f"transition-fact:{prepared.building_id}"
    raw_ref = prepared.raw_refs[0] if prepared.raw_refs else f"raw:{prepared.building_id}:agent-run"
    route_replay_facts = _route_replay_capture_fields(prepared.step_rows.link_row)
    route_decision_facts = _route_decision_basis_evidence_fields(prepared.step_rows.link_row)
    transition_authoring_facts = _transition_authoring_evidence_fields(prepared.step_rows.link_row)
    transition_lifecycle_facts = _transition_lifecycle_evidence_fields(prepared.step_rows.link_row)
    building_lifecycle_facts = _building_lifecycle_evidence_fields(prepared.step_rows.link_row)
    return {
        "building_id": prepared.building_id,
        "building_work": {
            "work_statement": prepared.brick_work.work_statement,
            "comparison_rule": prepared.brick_work.comparison_rule,
            "required_return_shape": prepared.brick_work.required_return_shape,
            "source_facts": list(prepared.brick_work.source_facts),
        },
        # A2: the 8 lifecycle capture events are CONTRACT-DERIVED. The emitter in
        # support/recording/operator_evidence.py builds each event by iterating the
        # capture-event field-spec (header order + per-event payload order) in
        # support/recording/contracts.py; the event_id / role_in_event /
        # axis_attribution literals come from the contract, and the per-event
        # payload (derived from the relevant axis) is supplied here.
        "capture_events": build_capture_events(
            raw_ref=raw_ref,
            not_proven=list(checked_not_proven),
            payloads={
                "building_opened": {
                    "building_ref": prepared.building_id,
                    "facts": {
                        "work_ref": prepared.step_rows.brick_row.get(
                            "brick_work_ref",
                            "work/building-work.json",
                        )
                    },
                },
                "brick_opened": {
                    "brick_ref": prepared.brick_instance_ref,
                    "facts": {
                        "work_statement": prepared.brick_work.work_statement,
                        "comparison_rule": prepared.brick_work.comparison_rule,
                        "required_return_shape": prepared.brick_work.required_return_shape,
                        "source_facts": list(prepared.brick_work.source_facts),
                    },
                },
                "agent_received": {
                    "actor_ref": agent_public_ref,
                    "brick_ref": prepared.brick_instance_ref,
                    "public_fact_refs": [
                        f"receipt:{prepared.building_id}:{prepared.agent_object.object_ref}"
                    ],
                    # MAIL-REPAIR (Smith ruling B2, 0611): the receipt event
                    # records the delivered handoff ADDRESSES as fact ("received").
                    # Stamped ONLY when addresses were delivered (additive; a
                    # no-handoff step's event is byte-stable). Addresses only.
                    "facts": {
                        "received_work_ref": prepared.step_rows.brick_row.get(
                            "brick_work_ref",
                            "work/building-work.json",
                        ),
                        **(
                            {
                                "received_handoff_refs": list(
                                    prepared.receipt_fact.received_handoff_refs
                                )
                            }
                            if prepared.receipt_fact.received_handoff_refs
                            else {}
                        ),
                    },
                },
                "agent_returned": {
                    "actor_ref": agent_public_ref,
                    "brick_ref": prepared.brick_instance_ref,
                    "public_fact_refs": [agent_fact_ref],
                    "receipt_text": "adapter returned value recorded in closed AgentFact shape",
                    "facts": {
                        "received_work_ref": prepared.step_rows.brick_row.get(
                            "brick_work_ref",
                            "work/building-work.json",
                        )
                    },
                },
                "brick_compared": {
                    "brick_ref": prepared.brick_instance_ref,
                    "public_fact_refs": [comparison_ref, agent_fact_ref],
                    "facts": {
                        "expected_work_ref": prepared.step_rows.brick_row.get(
                            "brick_work_ref",
                            "work/building-work.json",
                        ),
                        "observed_return_ref": agent_fact_ref,
                        "comparison_rule_ref": prepared.brick_work.comparison_rule
                        or "comparison-rule:not-supplied",
                        "unknown": True,
                    },
                },
                "link_transfer": {
                    "public_fact_refs": [link_public_ref, transition_ref],
                    "facts": {
                        "from_ref": prepared.brick_instance_ref,
                        "to_ref": prepared.next_brick_instance_ref,
                        "transferred_fact_refs": [agent_fact_ref, comparison_ref],
                    },
                },
                "link_carry": {
                    "public_fact_refs": [link_public_ref, transition_ref],
                    "facts": {
                        "from_ref": prepared.brick_instance_ref,
                        "to_ref": prepared.next_brick_instance_ref,
                        "carried_fact_refs": [agent_fact_ref, comparison_ref],
                    },
                },
                "link_movement": {
                    "public_fact_refs": [link_public_ref, transition_ref],
                    "receipt_text": "caller-supplied Link facts were recorded without support choice",
                    "facts": {
                        "reason_ref": "caller-supplied-link-facts",
                        **route_replay_facts,
                        **route_decision_facts,
                        **transition_authoring_facts,
                        **transition_lifecycle_facts,
                        **building_lifecycle_facts,
                    },
                },
            },
        ),
        "raw_manifest": {
            "raw_refs": list(prepared.raw_refs) or [raw_ref],
            "entries": [{"raw_ref": raw_ref, "raw_refs": list(prepared.raw_refs) or [raw_ref]}],
        },
        "evidence_manifest": {
            "building_map_ref": "work/building-map.json",
            "building_map_kind": building_map_packet.get("kind"),
            "agent_fact_refs": [agent_fact_ref],
            "proof_limits": list(checked_proof_limits),
            "not_proven": list(checked_not_proven),
        },
        "proof_limits": list(checked_proof_limits),
    }


def _lifecycle_packet_from_mapping(
    mapping: Mapping[str, Any],
    *,
    movement: str,
) -> BuildingLifecyclePacket:
    events_value = mapping.get("capture_events")
    if not isinstance(events_value, list):
        raise TypeError("lifecycle mapping capture_events must be a list")
    capture_events = tuple(
        _capture_event_from_mapping(item, movement)
        for item in events_value
    )
    return BuildingLifecyclePacket(
        building_id=_required_text("lifecycle.building_id", mapping.get("building_id")),
        building_work=_mapping("lifecycle.building_work", mapping.get("building_work")),
        capture_events=capture_events,
        raw_manifest=_mapping("lifecycle.raw_manifest", mapping.get("raw_manifest")),
        evidence_manifest=_mapping(
            "lifecycle.evidence_manifest",
            mapping.get("evidence_manifest"),
        ),
        proof_limits=_text_tuple("lifecycle.proof_limits", mapping.get("proof_limits")),
    )


def _capture_event_from_mapping(value: Any, movement: str) -> CaptureEvent:
    event = _mapping("capture_event", value)
    facts = dict(_mapping("capture_event.facts", event.get("facts", {})))
    if event.get("event_type") == "link_movement":
        facts.setdefault("movement", movement)
    return CaptureEvent(
        event_id=_required_text("capture_event.event_id", event.get("event_id")),
        event_type=_required_text("capture_event.event_type", event.get("event_type")),
        role_in_event=_required_text("capture_event.role_in_event", event.get("role_in_event")),
        axis_attribution=_required_text(
            "capture_event.axis_attribution",
            event.get("axis_attribution"),
        ),
        raw_ref=_required_text("capture_event.raw_ref", event.get("raw_ref")),
        not_proven=_text_tuple("capture_event.not_proven", event.get("not_proven")),
        source_truth=bool(event.get("source_truth", False)),
        actor_ref=_optional_text_or_none(event.get("actor_ref")),
        building_ref=_optional_text_or_none(event.get("building_ref")),
        brick_ref=_optional_text_or_none(event.get("brick_ref")),
        public_fact_refs=_text_tuple("capture_event.public_fact_refs", event.get("public_fact_refs")),
        receipt_text=_optional_text_or_none(event.get("receipt_text")),
        facts=facts,
    )
