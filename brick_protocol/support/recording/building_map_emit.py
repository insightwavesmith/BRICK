"""Building Graph map packet emitter.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
accumulated-Building graph-map packet, the single-Agent-run graph-map packet,
and the adapter-error-frontier graph-map packet that
``brick_protocol/support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern emitter. A2: building-map rows are CONTRACT-DERIVED -- the
per-axis rows (brick_instances / agent_bindings / link_edges) are built by
``brick_protocol/support/recording/operator_evidence.py`` iterating the per-axis field-spec in
``brick_protocol/support/recording/contracts.py``; this emitter supplies the per-step payload
only. Authors no Movement, target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    MinimalCrossingRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.plan_graph import (
    _graph_completion_edges_by_step_ref,
    _graph_extra_link_edges,
    _graph_groups,
)
from brick_protocol.support.operator.plan_validation import (
    _route_replay_edge_metadata,
    _route_replay_single_edge_fields,
)
from brick_protocol.support.operator.primitives import (
    _GRAPH_PROFILE,
    _agent_run_not_proven,
    _default_brick_work_ref,
    _merge_texts,
    _proof_limits_tuple,
    _raw_ref,
    _required_text,
    _step_fact_ref,
    _text_tuple,
)
from brick_protocol.support.recording.claims_common import (
    _adapter_error_attempt_from_ref,
    _chat_session_park_attempt_from_ref,
    _step_output_adapter_error_ref,
    _step_output_parked_ref,
    _step_output_manifest_ref,
    _step_result_attempts,
)
from brick_protocol.support.recording.declaration_packets import (
    _declaration_provenance_observation,
)
from brick_protocol.support.recording.operator_evidence import (
    FRONTIER_OBSERVATION_CHAT_SESSION_PARKED_KIND,
    build_agent_binding_row,
    build_brick_instance_row,
    build_frontier_observation,
    build_link_edge_row,
)


def _accumulated_building_map_packet(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan_ref: str = "building-plan:anonymous",
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
    task_source_ref: str | None = None,
    declaration_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    brick_instances: list[dict[str, Any]] = []
    agent_bindings: list[dict[str, Any]] = []
    link_edges: list[dict[str, Any]] = []
    # δ-c: index brick instances by id so a brick first emitted as a terminal
    # next_brick_instance_ref (empty agent_binding_refs) can be UPGRADED in place
    # when a later step actually performs it as its brick_instance_ref. Without
    # this, a chained multi-step building leaves intermediate performer bricks
    # with agent_binding_refs=[] even though a real binding points at them.
    bricks_by_id: dict[str, dict[str, Any]] = {}
    route_edge_metadata = _route_replay_edge_metadata(step_results)
    completion_edges = _graph_completion_edges_by_step_ref(graph_context)
    step_attempts = _step_result_attempts(step_results)
    # When the dynamic walker re-executes a node on an adopted reroute, step_results
    # holds multiple entries with the same step_ref, so completion_edges (keyed by
    # step_ref only) hands back the SAME declared edge_ref each time. Count how many
    # times each base link_edge_id has already been emitted in THIS loop so later
    # re-executions get a deterministic ::attempt-N suffix and stay unique. The first
    # emission keeps the bare edge_ref (byte-identical; non-reroute buildings see no
    # churn). The _step_fact_ref fallback already carries `index` and is unique on its
    # own, so it never collides.
    emitted_edge_id_counts: Counter[str] = Counter()
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        step_ref = prepared.step_rows.step_ref
        step_output_ref = _step_output_manifest_ref(step_ref, step_attempts[index - 1])
        completion_edge = completion_edges.get(step_ref, {})
        binding_ref = _step_fact_ref("binding", index, step_ref)
        agent_fact_ref = _step_fact_ref("agent-fact", index, step_ref)
        comparison_ref = _step_fact_ref("brick-comparison", index, step_ref)
        movement_ref = _step_fact_ref("movement-fact", index, step_ref)
        raw_refs = [_raw_ref("brick", index), _raw_ref("agent", index), _raw_ref("link", index)]
        # A2: building-map rows are CONTRACT-DERIVED. brick_instances come from the
        # BRICK backbone, agent_bindings from AGENT, link_edges from LINK; each row
        # is built by brick_protocol/support/recording/operator_evidence.py iterating the per-axis
        # field-spec in brick_protocol/support/recording/contracts.py.
        performer_brick = bricks_by_id.get(prepared.brick_instance_ref)
        if performer_brick is None:
            performer_brick = build_brick_instance_row(
                brick_instance_id=prepared.brick_instance_ref,
                brick_work_ref=prepared.step_rows.brick_row.get(
                    "brick_work_ref", _default_brick_work_ref(prepared.brick_instance_ref)
                ),
                attempt_index=index,
                agent_binding_refs=[binding_ref],
                raw_refs=raw_refs,
                proof_limits=list(proof_limits),
                not_proven=list(not_proven),
            )
            brick_instances.append(performer_brick)
            bricks_by_id[prepared.brick_instance_ref] = performer_brick
        else:
            # This brick was first emitted as a prior step's next boundary node
            # (no performer); wire the performer binding + a real work ref into
            # it now that an actual step performs it.
            if binding_ref not in performer_brick["agent_binding_refs"]:
                performer_brick["agent_binding_refs"].append(binding_ref)
            performer_brick["brick_work_ref"] = prepared.step_rows.brick_row.get(
                "brick_work_ref", _default_brick_work_ref(prepared.brick_instance_ref)
            )
        if prepared.next_brick_instance_ref not in bricks_by_id:
            next_brick = build_brick_instance_row(
                brick_instance_id=prepared.next_brick_instance_ref,
                brick_work_ref=prepared.step_rows.link_row.get(
                    "next_boundary_ref",
                    _default_brick_work_ref(prepared.next_brick_instance_ref),
                ),
                attempt_index=index,
                agent_binding_refs=[],
                raw_refs=raw_refs,
                proof_limits=list(proof_limits),
                not_proven=list(not_proven),
            )
            brick_instances.append(next_brick)
            bricks_by_id[prepared.next_brick_instance_ref] = next_brick
        agent_bindings.append(
            build_agent_binding_row(
                agent_binding_id=binding_ref,
                brick_instance_ref=prepared.brick_instance_ref,
                agent_performer_ref=f"agent-performer:{prepared.agent_object.object_ref}",
                binding_role="primary",
                produced_public_fact_refs=[agent_fact_ref],
                step_output_ref=step_output_ref,
                raw_refs=[_raw_ref("agent", index)],
                proof_limits=list(proof_limits),
                not_proven=list(not_proven),
            )
        )
        edge_metadata = route_edge_metadata.get(
            (prepared.brick_instance_ref, prepared.next_brick_instance_ref),
            {},
        )
        base_link_edge_id = completion_edge.get("edge_ref") or _step_fact_ref(
            "edge", index, step_ref
        )
        emitted_edge_id_counts[base_link_edge_id] += 1
        edge_repeat_ordinal = emitted_edge_id_counts[base_link_edge_id]
        link_edge_id = (
            base_link_edge_id
            if edge_repeat_ordinal == 1
            else f"{base_link_edge_id}::attempt-{edge_repeat_ordinal}"
        )
        edge = build_link_edge_row(
            link_edge_id=link_edge_id,
            edge_role=completion_edge.get("edge_role") or edge_metadata.get("edge_role", "primary_flow"),
            source_brick_instance_ref=prepared.brick_instance_ref,
            target_brick_instance_ref=prepared.next_brick_instance_ref,
            input_public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
            public_fact_refs=[agent_fact_ref, comparison_ref, movement_ref],
            movement_fact_ref=movement_ref,
            transition_fact_ref=_step_fact_ref("transition-fact", index, step_ref),
            step_output_ref=step_output_ref,
            edge_metadata=edge_metadata,
        )
        link_edges.append(edge)
    link_edges.extend(
        _graph_extra_link_edges(
            graph_context,
            step_results,
            proof_limits=proof_limits,
            not_proven=not_proven,
        )
    )
    packet = {
        "kind": "building_graph_map",
        "building_id": building_id,
        "profile": _GRAPH_PROFILE,
        "brick_instances": brick_instances,
        "agent_bindings": agent_bindings,
        "link_edges": link_edges,
        "groups": _graph_groups(graph_context, proof_limits=proof_limits, not_proven=not_proven),
        "raw_refs": [
            ref
            for index in range(1, len(step_results) + 1)
            for ref in (_raw_ref("brick", index), _raw_ref("agent", index), _raw_ref("link", index))
        ],
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    if declaration_plan is not None:
        packet["declaration_provenance"] = _declaration_provenance_observation(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
            graph_context=graph_context,
            task_source_ref=task_source_ref,
            proof_limits=proof_limits,
            not_proven=not_proven,
        )
    if task_source_ref:
        packet["task_source_ref"] = task_source_ref
    return packet


def agent_run_building_map_packet(
    prepared: AgentRunPreparationRecord,
    crossing_record: MinimalCrossingRecord,
    *,
    proof_limits: Iterable[str] | str | None = None,
    not_proven: Iterable[str] | str | None = None,
) -> dict[str, Any]:
    """Create a conservative graph-map packet from one prepared Agent run."""

    if not isinstance(prepared, AgentRunPreparationRecord):
        raise TypeError("prepared must be AgentRunPreparationRecord")
    if not isinstance(crossing_record, MinimalCrossingRecord):
        raise TypeError("crossing_record must be MinimalCrossingRecord")
    checked_proof_limits = _proof_limits_tuple(proof_limits or prepared.proof_limits)
    checked_not_proven = _text_tuple("not_proven", not_proven or _agent_run_not_proven())
    binding_ref = f"binding:{prepared.building_id}:{prepared.agent_object.object_ref}"
    agent_public_ref = f"agent-performer:{prepared.agent_object.object_ref}"
    agent_fact_ref = f"agent-fact:{prepared.building_id}:{prepared.agent_object.object_ref}"
    edge_ref = f"edge:{prepared.brick_instance_ref}:{prepared.next_brick_instance_ref}"
    public_fact_refs = _text_tuple(
        "public_fact_refs",
        prepared.step_rows.link_row.get("public_fact_refs")
        or (
            agent_fact_ref,
            f"brick-comparison:{prepared.building_id}",
            f"link-fact:{prepared.building_id}",
        ),
    )
    route_edge_fields = _route_replay_single_edge_fields(
        prepared.step_rows.link_row,
        source_ref=prepared.brick_instance_ref,
        target_ref=prepared.next_brick_instance_ref,
    )
    return {
        "kind": "building_graph_map",
        "building_id": prepared.building_id,
        "profile": _GRAPH_PROFILE,
        "brick_instances": [
            {
                "brick_instance_id": prepared.brick_instance_ref,
                "brick_work_ref": _required_text(
                    "step_rows.brick_row.brick_work_ref",
                    prepared.step_rows.brick_row.get("brick_work_ref", "work/building-work.json"),
                ),
                "attempt_index": 1,
                "agent_binding_refs": [binding_ref],
                "raw_refs": list(prepared.raw_refs),
                "proof_limits": list(checked_proof_limits),
                "not_proven": list(checked_not_proven),
            },
            {
                "brick_instance_id": prepared.next_brick_instance_ref,
                "brick_work_ref": _required_text(
                    "step_rows.link_row.next_boundary_ref",
                    prepared.step_rows.link_row.get("next_boundary_ref", "next-brick-boundary"),
                ),
                "attempt_index": 1,
                "agent_binding_refs": [],
                "raw_refs": list(prepared.raw_refs),
                "proof_limits": list(checked_proof_limits),
                "not_proven": list(checked_not_proven),
            },
        ],
        "agent_bindings": [
            {
                "agent_binding_id": binding_ref,
                "brick_instance_ref": prepared.brick_instance_ref,
                "agent_performer_ref": agent_public_ref,
                "binding_role": "primary",
                "produced_public_fact_refs": [agent_fact_ref],
                "raw_refs": list(prepared.raw_refs),
                "proof_limits": list(checked_proof_limits),
                "not_proven": list(checked_not_proven),
            }
        ],
        "link_edges": [
            {
                "link_edge_id": edge_ref,
                "edge_role": route_edge_fields.get("edge_role", "primary_flow"),
                "source_brick_instance_ref": prepared.brick_instance_ref,
                "target_brick_instance_ref": prepared.next_brick_instance_ref,
                "input_public_fact_refs": list(public_fact_refs),
                "public_fact_refs": list(public_fact_refs),
                "movement_fact_ref": f"movement-fact:{prepared.building_id}",
                "transition_fact_ref": f"transition-fact:{prepared.building_id}",
                **route_edge_fields,
            }
        ],
        "groups": [],
        "raw_refs": list(prepared.raw_refs),
        "proof_limits": list(checked_proof_limits),
        "not_proven": list(checked_not_proven),
    }


def _adapter_error_frontier_building_map_packet(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: Any,
    *,
    plan_ref: str = "building-plan:anonymous",
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    declaration_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frontier_graph_context = _frontier_realized_graph_context(
        graph_context,
        completed_step_results,
    )
    if completed_step_results:
        packet = dict(
            _accumulated_building_map_packet(
                building_id,
                completed_step_results,
                proof_limits=proof_limits,
                not_proven=_merge_texts(
                    *(result.not_proven for result in completed_step_results),
                    observation.not_proven,
                ),
                graph_context=frontier_graph_context,
                task_source_ref=task_source_ref,
            )
        )
        brick_instances = list(packet.get("brick_instances", []))
        agent_bindings = list(packet.get("agent_bindings", []))
        link_edges = list(packet.get("link_edges", []))
        raw_refs = list(packet.get("raw_refs", []))
        groups = list(packet.get("groups", []))
    else:
        brick_instances = []
        agent_bindings = []
        link_edges = []
        groups = []
        raw_refs = []
    failed_index = len(completed_step_results) + 1
    binding_ref = _step_fact_ref("binding", failed_index, failed_preparation.step_rows.step_ref)
    for ref in (
        _raw_ref("brick", failed_index),
        _raw_ref("agent-received", failed_index),
        observation.raw_ref,
        _raw_ref("link-frontier", failed_index),
    ):
        if ref not in raw_refs:
            raw_refs.append(ref)
    failed_brick = next(
        (
            item
            for item in brick_instances
            if isinstance(item, dict)
            and item.get("brick_instance_id") == failed_preparation.brick_instance_ref
        ),
        None,
    )
    failed_brick_raw_refs = [
        _raw_ref("brick", failed_index),
        _raw_ref("agent-received", failed_index),
    ]
    if failed_brick is None:
        brick_instances.append(
            {
                "brick_instance_id": failed_preparation.brick_instance_ref,
                "brick_work_ref": failed_preparation.step_rows.brick_row.get(
                    "brick_work_ref",
                    "work/building-work.json",
                ),
                "attempt_index": failed_index,
                "agent_binding_refs": [binding_ref],
                "raw_refs": failed_brick_raw_refs,
                "proof_limits": list(proof_limits),
                "not_proven": list(observation.not_proven),
            }
        )
    else:
        refs = failed_brick.get("agent_binding_refs")
        if not isinstance(refs, list):
            refs = []
            failed_brick["agent_binding_refs"] = refs
        if binding_ref not in refs:
            refs.append(binding_ref)
        failed_brick["brick_work_ref"] = failed_preparation.step_rows.brick_row.get(
            "brick_work_ref",
            "work/building-work.json",
        )
        raw_ref_values = failed_brick.get("raw_refs")
        if not isinstance(raw_ref_values, list):
            raw_ref_values = []
            failed_brick["raw_refs"] = raw_ref_values
        for ref in failed_brick_raw_refs:
            if ref not in raw_ref_values:
                raw_ref_values.append(ref)
    agent_bindings.append(
        {
            "agent_binding_id": binding_ref,
            "brick_instance_ref": failed_preparation.brick_instance_ref,
            "agent_performer_ref": f"agent-performer:{failed_preparation.agent_object.object_ref}",
            "binding_role": "primary",
            "raw_refs": [_raw_ref("agent-received", failed_index), observation.raw_ref],
            "step_output_ref": _step_output_adapter_error_ref(
                failed_preparation.step_rows.step_ref,
                _adapter_error_attempt_from_ref(observation.adapter_error_ref),
            ),
            "proof_limits": list(proof_limits),
            "not_proven": list(observation.not_proven),
        }
    )
    packet = {
        "kind": "building_graph_map",
        "building_id": building_id,
        "profile": _GRAPH_PROFILE,
        "brick_instances": brick_instances,
        "agent_bindings": agent_bindings,
        "link_edges": link_edges,
        "groups": groups,
        "raw_refs": raw_refs,
        "proof_limits": list(proof_limits),
        "not_proven": list(observation.not_proven),
        # A2: the agent-incomplete frontier observation is CONTRACT-DERIVED (built
        # by brick_protocol/support/recording/operator_evidence.py from the frontier-observation
        # field-spec in brick_protocol/support/recording/contracts.py).
        "frontier_observation": build_frontier_observation(
            adapter_error_ref=observation.adapter_error_ref,
        ),
    }
    if task_source_ref:
        packet["task_source_ref"] = task_source_ref
    if declaration_plan is not None:
        packet["declaration_provenance"] = _declaration_provenance_observation(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
            graph_context=graph_context,
            task_source_ref=task_source_ref,
            proof_limits=proof_limits,
            not_proven=tuple(observation.not_proven),
        )
    return packet


def _chat_session_park_frontier_building_map_packet(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: Any,
    *,
    plan_ref: str = "building-plan:anonymous",
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    declaration_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frontier_graph_context = _frontier_realized_graph_context(
        graph_context,
        completed_step_results,
    )
    if completed_step_results:
        packet = dict(
            _accumulated_building_map_packet(
                building_id,
                completed_step_results,
                proof_limits=proof_limits,
                not_proven=_merge_texts(
                    *(result.not_proven for result in completed_step_results),
                    observation.not_proven,
                ),
                graph_context=frontier_graph_context,
                task_source_ref=task_source_ref,
            )
        )
        brick_instances = list(packet.get("brick_instances", []))
        agent_bindings = list(packet.get("agent_bindings", []))
        link_edges = list(packet.get("link_edges", []))
        raw_refs = list(packet.get("raw_refs", []))
        groups = list(packet.get("groups", []))
    else:
        brick_instances = []
        agent_bindings = []
        link_edges = []
        groups = []
        raw_refs = []
    failed_index = len(completed_step_results) + 1
    binding_ref = _step_fact_ref("binding", failed_index, failed_preparation.step_rows.step_ref)
    for ref in (
        _raw_ref("brick", failed_index),
        _raw_ref("agent-received", failed_index),
        observation.raw_ref,
        _raw_ref("link-frontier", failed_index),
    ):
        if ref not in raw_refs:
            raw_refs.append(ref)
    failed_brick = next(
        (
            item
            for item in brick_instances
            if isinstance(item, dict)
            and item.get("brick_instance_id") == failed_preparation.brick_instance_ref
        ),
        None,
    )
    failed_brick_raw_refs = [
        _raw_ref("brick", failed_index),
        _raw_ref("agent-received", failed_index),
    ]
    if failed_brick is None:
        brick_instances.append(
            {
                "brick_instance_id": failed_preparation.brick_instance_ref,
                "brick_work_ref": failed_preparation.step_rows.brick_row.get(
                    "brick_work_ref",
                    "work/building-work.json",
                ),
                "attempt_index": failed_index,
                "agent_binding_refs": [binding_ref],
                "raw_refs": failed_brick_raw_refs,
                "proof_limits": list(proof_limits),
                "not_proven": list(observation.not_proven),
            }
        )
    else:
        refs = failed_brick.get("agent_binding_refs")
        if not isinstance(refs, list):
            refs = []
            failed_brick["agent_binding_refs"] = refs
        if binding_ref not in refs:
            refs.append(binding_ref)
        failed_brick["brick_work_ref"] = failed_preparation.step_rows.brick_row.get(
            "brick_work_ref",
            "work/building-work.json",
        )
        raw_ref_values = failed_brick.get("raw_refs")
        if not isinstance(raw_ref_values, list):
            raw_ref_values = []
            failed_brick["raw_refs"] = raw_ref_values
        for ref in failed_brick_raw_refs:
            if ref not in raw_ref_values:
                raw_ref_values.append(ref)
    agent_bindings.append(
        {
            "agent_binding_id": binding_ref,
            "brick_instance_ref": failed_preparation.brick_instance_ref,
            "agent_performer_ref": f"agent-performer:{failed_preparation.agent_object.object_ref}",
            "binding_role": "primary",
            "raw_refs": [_raw_ref("agent-received", failed_index), observation.raw_ref],
            "step_output_ref": _step_output_parked_ref(
                failed_preparation.step_rows.step_ref,
                _chat_session_park_attempt_from_ref(observation.parked_ref),
            ),
            "proof_limits": list(proof_limits),
            "not_proven": list(observation.not_proven),
        }
    )
    packet = {
        "kind": "building_graph_map",
        "building_id": building_id,
        "profile": _GRAPH_PROFILE,
        "brick_instances": brick_instances,
        "agent_bindings": agent_bindings,
        "link_edges": link_edges,
        "groups": groups,
        "raw_refs": raw_refs,
        "proof_limits": list(proof_limits),
        "not_proven": list(observation.not_proven),
        "frontier_observation": build_frontier_observation(
            parked_ref=observation.parked_ref,
            frontier_kind=FRONTIER_OBSERVATION_CHAT_SESSION_PARKED_KIND,
        ),
    }
    if task_source_ref:
        packet["task_source_ref"] = task_source_ref
    if declaration_plan is not None:
        packet["declaration_provenance"] = _declaration_provenance_observation(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
            graph_context=graph_context,
            task_source_ref=task_source_ref,
            proof_limits=proof_limits,
            not_proven=tuple(observation.not_proven),
        )
    return packet


def _frontier_realized_graph_context(
    graph_context: Mapping[str, Any] | None,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
) -> Mapping[str, Any] | None:
    if not graph_context:
        return None
    completed_step_refs = {
        result.preparation.step_rows.step_ref for result in completed_step_results
    }
    declared_edges = graph_context.get("declared_edges")
    if not isinstance(declared_edges, list):
        return {"declared_edges": [], "completion_edge_refs": [], "groups": []}
    realized_edges = [
        dict(edge)
        for edge in declared_edges
        if isinstance(edge, Mapping)
        and edge.get("is_completion_edge") is True
        and edge.get("source_step_ref") in completed_step_refs
    ]
    completion_edge_refs = [
        str(edge.get("edge_ref"))
        for edge in realized_edges
        if isinstance(edge.get("edge_ref"), str) and edge.get("edge_ref")
    ]
    return {
        "declared_edges": realized_edges,
        "completion_edge_refs": sorted(completion_edge_refs),
        "groups": [],
    }
