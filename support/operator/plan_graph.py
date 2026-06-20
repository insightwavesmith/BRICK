"""Declared Building Plan graph projection helpers.

This module only projects caller-declared graph plans into declared step order.
It does not choose Movement, targets, routes, or replay segments.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import (
    casting_bag,
    merge_casting_bags,
    stamp_casting,
    _step_fact_ref,
    _require_mapping_value,
    _optional_text_value,
    _optional_text_from_mapping,
    _normalize_key,
    _merge_texts,
    _ROUTE_REPLAY_PLAN_KEY,
    _LINK_ROW_ALLOWED_KEYS,
    _BRICK_ROW_ALLOWED_KEYS,
    _AGENT_ROW_ALLOWED_KEYS,
    _GRAPH_PLAN_ALLOWED_GROUP_ROLES,
    _GRAPH_PLAN_FORBIDDEN_GROUP_WORDS,
    _GRAPH_PLAN_FORBIDDEN_KEYS,
    _require_only_keys,
    _required_text,
    _resource_slug,
    _text_tuple,
)
from brick_protocol.support.operator.plan_validation import (
    _validate_transition_authoring_for_link_row,
    _validate_route_decision_basis_for_link_row,
    _validate_route_replay_plan_for_link_row,
    _validate_gate_sequence_policy_for_link_row,
    _validate_transition_lifecycle_for_link_row,
    _validate_building_lifecycle_for_link_row,
    _reject_forbidden_route_endpoint,
    _non_empty_text_list_tuple,
    _movement_and_target_from_link_row,
)

def _linear_plan_from_graph_plan(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Project a declared graph plan into declared execution steps.

    The projection is mechanical: support walks `execution_order` exactly and
    records declared non-completion edges as graph/evidence refs.
    """

    _reject_graph_forbidden("graph_plan", plan)
    plan_ref = _optional_text_from_mapping(plan, "plan_ref") or "building-plan:anonymous"
    brick_steps = _graph_brick_steps_by_ref(plan)
    link_edges = _graph_link_edges_by_ref(plan)
    execution_order = _graph_execution_order(plan, brick_steps)
    groups = _graph_declared_groups(plan, link_edges)
    _validate_graph_plan_topology(brick_steps, link_edges, groups)

    linear_steps: list[Mapping[str, Any]] = []
    completion_edge_refs: set[str] = set()
    for index, step_ref in enumerate(execution_order):
        brick_step = brick_steps[step_ref]
        completion_edge_ref = _required_text(
            f"brick_steps.{step_ref}.completion_edge_ref",
            brick_step.get("completion_edge_ref"),
        )
        completion_edge = link_edges.get(completion_edge_ref)
        if completion_edge is None:
            raise ValueError(f"completion_edge_ref does not resolve: {completion_edge_ref}")
        if completion_edge["source_step_ref"] != step_ref:
            raise ValueError("completion_edge_ref must reference an edge sourced from the same Brick step")
        completion_edge_refs.add(completion_edge_ref)
        rows = list(_graph_brick_agent_rows(brick_step)) + [dict(completion_edge["link_row"])]
        linear_step: dict[str, Any] = {"step_ref": step_ref}
        stamp_casting(
            linear_step,
            merge_casting_bags(casting_bag(brick_step), casting_bag(plan)),
        )
        linear_step.update(
            {
                "rows": rows,
                "caller_supplied_link_facts": completion_edge.get("caller_supplied_link_facts"),
                "proof_limits": brick_step.get("proof_limits") or plan.get("proof_limits"),
                "not_proven": _merge_texts(plan.get("not_proven"), brick_step.get("not_proven")),
            }
        )
        linear_steps.append(linear_step)

    for edge in link_edges.values():
        if edge["edge_ref"] not in completion_edge_refs and _ROUTE_REPLAY_PLAN_KEY in edge["link_row"]:
            raise ValueError("graph route_replay_plan is admitted only on completion Link edges")

    declared_edges = [
        {
            "edge_ref": edge["edge_ref"],
            "source_step_ref": edge["source_step_ref"],
            "target_step_ref": edge.get("target_step_ref", ""),
            "source_brick_instance_ref": _graph_step_brick_ref(brick_steps[edge["source_step_ref"]]),
            "target_brick_instance_ref": edge["target_brick_instance_ref"],
            "edge_role": _graph_edge_role(edge["edge_ref"], groups),
            "link_row": dict(edge["link_row"]),
            "is_completion_edge": edge["edge_ref"] in completion_edge_refs,
        }
        for edge in link_edges.values()
    ]
    graph_context = {
        "declared_edges": declared_edges,
        "completion_edge_refs": sorted(completion_edge_refs),
        "groups": groups,
    }
    linear_plan = {
        key: value
        for key, value in plan.items()
        if key not in {"plan_shape", "execution_order", "brick_steps", "link_edges", "groups"}
    }
    linear_plan["plan_ref"] = plan_ref
    linear_plan["steps"] = linear_steps
    linear_plan["graph_context_ref"] = "support-projection:declared-graph-topology"
    return linear_plan, graph_context

def _graph_brick_steps_by_ref(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = plan.get("brick_steps")
    if not isinstance(values, list) or not values:
        raise ValueError("graph Building Plan requires non-empty brick_steps")
    steps: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(values):
        step = _require_mapping_value(f"brick_steps[{index}]", value)
        _reject_graph_forbidden(f"brick_steps[{index}]", step)
        step_ref = _required_text(f"brick_steps[{index}].step_ref", step.get("step_ref"))
        if step_ref in steps:
            raise ValueError(f"duplicate graph brick step_ref: {step_ref}")
        _graph_brick_agent_rows(step)
        steps[step_ref] = step
    return steps

def _graph_brick_agent_rows(step: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    rows = step.get("rows")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("graph brick_steps rows must contain exactly Brick and Agent rows")
    row_maps = tuple(_require_mapping_value("graph brick step row", row) for row in rows)
    axes = [row.get("axis") for row in row_maps]
    if axes != ["Brick", "Agent"]:
        raise ValueError("graph brick_steps rows axes must be exactly Brick, Agent")
    _require_only_keys("Graph Brick row", row_maps[0], _BRICK_ROW_ALLOWED_KEYS)
    _require_only_keys("Graph Agent row", row_maps[1], _AGENT_ROW_ALLOWED_KEYS)
    if not row_maps[1].get("agent_object_ref"):
        raise ValueError("graph Agent row must reference one Agent Object")
    return row_maps[0], row_maps[1]

def _graph_link_edges_by_ref(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = plan.get("link_edges")
    if not isinstance(values, list) or not values:
        raise ValueError("graph Building Plan requires non-empty link_edges")
    brick_steps = _graph_brick_steps_by_ref(plan)
    declared_brick_refs = frozenset(_graph_step_brick_ref(step) for step in brick_steps.values())
    raw_node_reroute_budgets = plan.get("node_reroute_budgets", {})
    if raw_node_reroute_budgets is None:
        raw_node_reroute_budgets = {}
    if not isinstance(raw_node_reroute_budgets, Mapping):
        raise ValueError("node_reroute_budgets must be a mapping when supplied")
    edges: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(values):
        edge = dict(_require_mapping_value(f"link_edges[{index}]", value))
        _reject_graph_forbidden(f"link_edges[{index}]", edge)
        edge_ref = _required_text(f"link_edges[{index}].edge_ref", edge.get("edge_ref"))
        if edge_ref in edges:
            raise ValueError(f"duplicate graph link edge_ref: {edge_ref}")
        source_step_ref = _required_text(
            f"link_edges[{index}].source_step_ref",
            edge.get("source_step_ref"),
        )
        if source_step_ref not in brick_steps:
            raise ValueError(f"graph link edge source_step_ref does not resolve: {source_step_ref}")
        target_step_ref = _optional_text_value(edge.get("target_step_ref"))
        rows = edge.get("rows")
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError("graph link_edges rows must contain exactly one Link row")
        link_row = dict(_require_mapping_value(f"link_edges[{index}].rows[0]", rows[0]))
        if link_row.get("axis") != "Link":
            raise ValueError("graph link_edges row axis must be Link")
        _require_only_keys("Graph Link row", link_row, _LINK_ROW_ALLOWED_KEYS)
        movement, target = _movement_and_target_from_link_row(link_row)
        if target_step_ref is not None:
            if target_step_ref not in brick_steps:
                raise ValueError(f"graph link edge target_step_ref does not resolve: {target_step_ref}")
            target_brick_ref = _graph_step_brick_ref(brick_steps[target_step_ref])
            if target != target_brick_ref:
                raise ValueError("graph Link row target must match target_step_ref Brick instance")
        else:
            target_brick_ref = target
            if not target.startswith(("building-boundary:", "building-boundary-")):
                raise ValueError("graph terminal Link edge without target_step_ref must target building-boundary")
        link_row.setdefault("next_brick_instance_ref", target_brick_ref)
        source_brick_ref = _graph_step_brick_ref(brick_steps[source_step_ref])
        _reject_forbidden_route_endpoint("graph link edge source", source_brick_ref)
        _reject_forbidden_route_endpoint("graph link edge target", target_brick_ref)
        _validate_route_replay_plan_for_link_row(
            link_row,
            movement=movement,
            target=target,
            declared_brick_refs=declared_brick_refs,
        )
        _validate_gate_sequence_policy_for_link_row(
            link_row,
            source_brick_ref=source_brick_ref,
            target_brick_ref=target_brick_ref,
            declared_brick_refs=declared_brick_refs,
            node_reroute_budgets=raw_node_reroute_budgets,
        )
        _validate_route_decision_basis_for_link_row(link_row)
        _validate_transition_authoring_for_link_row(link_row)
        _validate_transition_lifecycle_for_link_row(link_row)
        _validate_building_lifecycle_for_link_row(link_row)
        edge["edge_ref"] = edge_ref
        edge["source_step_ref"] = source_step_ref
        edge["target_step_ref"] = target_step_ref or ""
        edge["target_brick_instance_ref"] = target_brick_ref
        edge["link_row"] = link_row
        edge["movement"] = movement
        edges[edge_ref] = edge
    return edges

def _graph_execution_order(
    plan: Mapping[str, Any],
    brick_steps: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    values = plan.get("execution_order")
    if not isinstance(values, list) or not values:
        raise ValueError("graph Building Plan requires non-empty execution_order")
    order = tuple(_required_text(f"execution_order[{index}]", value) for index, value in enumerate(values))
    if set(order) != set(brick_steps) or len(order) != len(brick_steps):
        raise ValueError("execution_order must contain every graph Brick step exactly once")
    return order

def _graph_declared_groups(
    plan: Mapping[str, Any],
    link_edges: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    values = plan.get("groups", [])
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("graph Building Plan groups must be a list")
    groups: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        group = _require_mapping_value(f"groups[{index}]", value)
        _reject_graph_forbidden(f"groups[{index}]", group)
        group_id = _required_text(f"groups[{index}].group_id", group.get("group_id"))
        if group_id in seen:
            raise ValueError(f"duplicate graph group_id: {group_id}")
        seen.add(group_id)
        group_role = _required_text(f"groups[{index}].group_role", group.get("group_role"))
        if group_role not in _GRAPH_PLAN_ALLOWED_GROUP_ROLES:
            raise ValueError(f"graph group_role is not admitted: {group_role}")
        member_kind = _required_text(
            f"groups[{index}].member_ref_kind",
            group.get("member_ref_kind"),
        )
        if member_kind != "link_edge":
            raise ValueError("graph groups currently require member_ref_kind: link_edge")
        member_refs = _non_empty_text_list_tuple(f"groups[{index}].member_refs", group.get("member_refs"))
        missing = [ref for ref in member_refs if ref not in link_edges]
        if missing:
            raise ValueError("graph group member_refs must resolve to link_edges: " + ", ".join(missing))
        for text in (group_id, group_role, *member_refs):
            lowered = text.lower()
            if any(word in lowered for word in _GRAPH_PLAN_FORBIDDEN_GROUP_WORDS):
                raise ValueError("graph group text must not contain judgment or Movement authority wording")
        # sibling_independence: a HUMAN-declared (plan/preset/intent) per-fan-in
        # vouch naming sibling SOURCE refs that are safe to SKIP from cohort
        # re-verification when a reroute lands back on one of this fan-in's
        # sources. Support READS this declaration; it NEVER synthesizes
        # independence. Absent => re-verify ALL siblings (conservative). The
        # refs are projected verbatim (step refs or brick refs); the walker
        # resolves them against declared nodes at cohort-expansion time.
        sibling_independence = list(
            _text_tuple(
                f"groups[{index}].sibling_independence",
                group.get("sibling_independence", ()),
            )
        )
        for text in sibling_independence:
            lowered = text.lower()
            if any(word in lowered for word in _GRAPH_PLAN_FORBIDDEN_GROUP_WORDS):
                raise ValueError(
                    "graph group sibling_independence text must not contain judgment "
                    "or Movement authority wording"
                )
        groups.append(
            {
                "group_id": group_id,
                "group_role": group_role,
                "member_ref_kind": member_kind,
                "member_refs": list(member_refs),
                "sibling_independence": sibling_independence,
                "raw_refs": list(_text_tuple("group.raw_refs", group.get("raw_refs", ()))),
                "proof_limits": list(_text_tuple("group.proof_limits", group.get("proof_limits", ()))),
                "not_proven": list(_text_tuple("group.not_proven", group.get("not_proven", ()))),
            }
        )
    return tuple(groups)

def _graph_step_brick_ref(step: Mapping[str, Any]) -> str:
    brick_row, _ = _graph_brick_agent_rows(step)
    return _required_text("graph Brick row brick_instance_ref", brick_row.get("brick_instance_ref"))

def _graph_edge_role(edge_ref: str, groups: Iterable[Mapping[str, Any]]) -> str:
    for group in groups:
        refs = group.get("member_refs", [])
        if isinstance(refs, list) and edge_ref in refs:
            role = group.get("group_role")
            if isinstance(role, str) and role in _GRAPH_PLAN_ALLOWED_GROUP_ROLES:
                return role
    return "primary_flow"

def _validate_graph_plan_topology(
    brick_steps: Mapping[str, Mapping[str, Any]],
    link_edges: Mapping[str, Mapping[str, Any]],
    groups: Iterable[Mapping[str, Any]],
) -> None:
    """Reject malformed declared graph topology at plan admission.

    This is shape validation only. It does not choose Movement, select a route,
    judge success/quality, or infer runtime scheduling.
    """

    directed_edges = tuple(
        (
            _required_text("link_edges.source_step_ref", edge.get("source_step_ref")),
            _required_text("link_edges.target_step_ref", edge.get("target_step_ref")),
        )
        for edge in link_edges.values()
        if _optional_text_value(edge.get("target_step_ref"))
    )
    incoming_counts = {step_ref: 0 for step_ref in brick_steps}
    outgoing_by_source: dict[str, list[str]] = {step_ref: [] for step_ref in brick_steps}
    for source, target in directed_edges:
        incoming_counts[target] += 1
        outgoing_by_source[source].append(target)
    roots = [step_ref for step_ref in brick_steps if incoming_counts[step_ref] == 0]
    if not roots:
        raise ValueError("graph plan must declare at least one root Brick step with no incoming Link edge")

    remaining_incoming = dict(incoming_counts)
    ready = list(roots)
    visited: list[str] = []
    while ready:
        step_ref = ready.pop(0)
        visited.append(step_ref)
        for target in outgoing_by_source.get(step_ref, []):
            remaining_incoming[target] -= 1
            if remaining_incoming[target] == 0:
                ready.append(target)
    if len(visited) != len(brick_steps):
        cyclic = sorted(step_ref for step_ref, count in remaining_incoming.items() if count > 0)
        raise ValueError(
            "graph plan contains a cycle among declared Link edges: " + ", ".join(cyclic)
        )

    for group in groups:
        role = group.get("group_role")
        if role not in {"fan_out", "fan_in"}:
            continue
        group_id = _required_text("groups.group_id", group.get("group_id"))
        member_refs = group.get("member_refs", [])
        if not isinstance(member_refs, list):
            raise ValueError("graph group member_refs must be a list")
        sources: set[str] = set()
        targets: set[str] = set()
        for edge_ref in member_refs:
            edge = link_edges.get(str(edge_ref))
            if edge is None:
                continue
            source = _optional_text_value(edge.get("source_step_ref"))
            target = _optional_text_value(edge.get("target_step_ref"))
            if source:
                sources.add(source)
            if target:
                targets.add(target)
        if role == "fan_out" and not (len(sources) == 1 and len(targets) >= 2):
            raise ValueError(
                f"graph fan_out group must declare exactly one source and at least two targets: {group_id}"
            )
        if role == "fan_in" and not (len(targets) == 1 and len(sources) >= 2):
            raise ValueError(
                f"graph fan_in group must declare exactly one target and at least two sources: {group_id}"
            )

def _reject_graph_forbidden(name: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError(f"{name} contains non-text or blank key")
            if _normalize_key(raw_key) in _GRAPH_PLAN_FORBIDDEN_KEYS:
                raise ValueError(f"{name} contains forbidden graph-run key {raw_key!r}")
            _reject_graph_forbidden(f"{name}.{raw_key}", child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_graph_forbidden(f"{name}[{index}]", child)

def _graph_completion_edges_by_step_ref(
    graph_context: Mapping[str, Any] | None,
) -> dict[str, Mapping[str, Any]]:
    if not graph_context:
        return {}
    edges = graph_context.get("declared_edges", [])
    if not isinstance(edges, list):
        return {}
    return {
        str(edge["source_step_ref"]): edge
        for edge in edges
        if isinstance(edge, Mapping) and edge.get("is_completion_edge") is True
    }

def _graph_extra_link_edges(
    graph_context: Mapping[str, Any] | None,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    if not graph_context:
        return []
    step_agent_refs = {
        result.preparation.step_rows.step_ref: _step_fact_ref(
            "agent-fact",
            index,
            result.preparation.step_rows.step_ref,
        )
        for index, result in enumerate(step_results, start=1)
    }
    edges: list[Mapping[str, Any]] = []
    for index, edge in enumerate(_graph_declared_edges(graph_context), start=1):
        if edge.get("is_completion_edge") is True:
            continue
        edge_ref = _required_text("declared_edges.edge_ref", edge.get("edge_ref"))
        source_step_ref = _required_text("declared_edges.source_step_ref", edge.get("source_step_ref"))
        public_refs = [step_agent_refs.get(source_step_ref, _graph_movement_fact_ref(edge_ref))]
        public_refs.append(_graph_movement_fact_ref(edge_ref))
        edges.append(
            {
                "link_edge_id": edge_ref,
                "edge_role": _optional_text_value(edge.get("edge_role")) or "primary_flow",
                "source_brick_instance_ref": _required_text(
                    "declared_edges.source_brick_instance_ref",
                    edge.get("source_brick_instance_ref"),
                ),
                "target_brick_instance_ref": _required_text(
                    "declared_edges.target_brick_instance_ref",
                    edge.get("target_brick_instance_ref"),
                ),
                "input_public_fact_refs": list(dict.fromkeys(public_refs)),
                "public_fact_refs": list(dict.fromkeys(public_refs)),
                "movement_fact_ref": _graph_movement_fact_ref(edge_ref),
                "transition_fact_ref": _graph_transition_fact_ref(edge_ref),
                "raw_refs": [_graph_link_raw_ref(index, edge_ref)],
                "proof_limits": list(proof_limits),
                "not_proven": list(not_proven),
            }
        )
    return edges

def _graph_groups(
    graph_context: Mapping[str, Any] | None,
    *,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    if not graph_context:
        return []
    groups: list[Mapping[str, Any]] = []
    for group in graph_context.get("groups", []):
        if not isinstance(group, Mapping):
            continue
        merged = dict(group)
        merged["proof_limits"] = list(_merge_texts(group.get("proof_limits"), proof_limits))
        merged["not_proven"] = list(_merge_texts(group.get("not_proven"), not_proven))
        groups.append(merged)
    return groups

def _graph_declared_edges(graph_context: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    if not graph_context:
        return ()
    value = graph_context.get("declared_edges", ())
    if not isinstance(value, list):
        return ()
    return tuple(edge for edge in value if isinstance(edge, Mapping))

def _graph_fan_out_targets_by_source_step_ref(
    graph_context: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    targets_by_source: dict[str, list[str]] = {}
    for edge in _graph_declared_edges(graph_context):
        if edge.get("edge_role") != "fan_out":
            continue
        source = _optional_text_value(edge.get("source_step_ref"))
        target = _optional_text_value(edge.get("target_step_ref"))
        if not source or not target:
            continue
        targets = targets_by_source.setdefault(source, [])
        if target not in targets:
            targets.append(target)
    return {source: tuple(targets) for source, targets in targets_by_source.items()}

def _graph_fan_in_sources_by_target_step_ref(
    graph_context: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    sources_by_target: dict[str, list[str]] = {}
    for edge in _graph_declared_edges(graph_context):
        if edge.get("edge_role") != "fan_in":
            continue
        source = _optional_text_value(edge.get("source_step_ref"))
        target = _optional_text_value(edge.get("target_step_ref"))
        if not source or not target:
            continue
        sources = sources_by_target.setdefault(target, [])
        if source not in sources:
            sources.append(source)
    return {target: tuple(sources) for target, sources in sources_by_target.items()}

def _graph_fan_in_sibling_independence_by_target_step_ref(
    graph_context: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Map each fan-in TARGET step_ref to its declared sibling_independence vouch.

    The vouch is the human-declared per-fan-in list of sibling SOURCE refs safe
    to SKIP from cohort re-verification. Keyed by the fan-in target step_ref so a
    reroute that lands on one of that target's sources can read the vouch. Support
    READS this declaration; it never decides independence.
    """

    if not graph_context:
        return {}
    groups = graph_context.get("groups", ())
    if not isinstance(groups, (list, tuple)):
        return {}
    sources_by_target = _graph_fan_in_sources_by_target_step_ref(graph_context)
    edges_by_ref = {
        _optional_text_value(edge.get("edge_ref")): edge
        for edge in _graph_declared_edges(graph_context)
        if _optional_text_value(edge.get("edge_ref"))
    }
    vouch_by_target: dict[str, list[str]] = {}
    for group in groups:
        if not isinstance(group, Mapping) or group.get("group_role") != "fan_in":
            continue
        vouch = group.get("sibling_independence", ())
        if not isinstance(vouch, (list, tuple)) or not vouch:
            continue
        targets = {
            _optional_text_value(edges_by_ref[ref].get("target_step_ref"))
            for ref in group.get("member_refs", [])
            if ref in edges_by_ref
        }
        targets.discard("")
        if not targets:
            # Fall back to the topology-derived target for this fan-in's sources.
            member_sources = {
                _optional_text_value(edges_by_ref[ref].get("source_step_ref"))
                for ref in group.get("member_refs", [])
                if ref in edges_by_ref
            }
            member_sources.discard("")
            targets = {
                target
                for target, sources in sources_by_target.items()
                if member_sources & set(sources)
            }
        for target in targets:
            bucket = vouch_by_target.setdefault(target, [])
            for ref in vouch:
                text = _optional_text_value(ref)
                if text and text not in bucket:
                    bucket.append(text)
    return {target: tuple(refs) for target, refs in vouch_by_target.items()}


def _graph_link_raw_refs(graph_context: Mapping[str, Any] | None) -> list[str]:
    return [
        _graph_link_raw_ref(index, _required_text("declared_edges.edge_ref", edge.get("edge_ref")))
        for index, edge in enumerate(_graph_declared_edges(graph_context), start=1)
    ]

def _graph_link_raw_ref(index: int, edge_ref: str) -> str:
    return f"raw:link-graph:{index:02d}:{_resource_slug('edge_ref', edge_ref.replace(':', '-'))}"

def _graph_movement_fact_ref(edge_ref: str) -> str:
    return f"movement-fact:graph-edge:{_resource_slug('edge_ref', edge_ref.replace(':', '-'))}"

def _graph_transition_fact_ref(edge_ref: str) -> str:
    return f"transition-fact:graph-edge:{_resource_slug('edge_ref', edge_ref.replace(':', '-'))}"
