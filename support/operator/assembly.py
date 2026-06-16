"""Front-door structural assembly for caller/COO-declared Building graphs.

This module is support mechanics only. It lowers handle-based graph declarations
to ``compose_building`` inputs, records no provider state, chooses no Movement,
and judges no success or quality.
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_LINK_GATE_REF,
    REPO_ROOT,
)
from brick_protocol.support.operator.composition import (
    GATE_CONCEPT_TOKEN_GATE_REFS,
    _composition_slug,
    _load_shape_registry,
    _materializer_human_gate_hold_policy,
    _materializer_strip_field,
    compose_building,
    inline_task_source_carry,
)


_FORBIDDEN_BRICK_KWARGS = frozenset(
    {
        "node_id",
        "step_template_ref",
        "brick_instance_ref",
        "row_ref",
        "brick_work_ref",
        "step_ref",
        "completion_edge_ref",
        "fan_in_source",
        "fan_in_target",
        "closure_transition_target_policy",
        "node_reroute_budget",
        "required_return_shape",
        "write_scope",
        "target_step_template_ref",
        "comparison_rule",
    }
)
_TRANSITION_CONCERN_FIELD = "transition_concern_evidence"
_DEFAULT_BOUNDARY_REF = "building-boundary:closed"
_PROPOSED_BUILDING_GRAPH_FILENAME = "proposed-building-graph.json"


class Concern(Enum):
    UPSTREAM_GAP = "upstream_gap"
    BOUNDARY_MISMATCH = "boundary_mismatch"
    INSUFFICIENT_INPUT = "insufficient_input"
    REPLAY_NEEDED = "replay_needed"
    UNKNOWN = "unknown"
    DESIGN_GAP = "design_gap"
    IMPLEMENTATION_GAP = "implementation_gap"
    VERIFICATION_GAP = "verification_gap"


class Gate(Enum):
    STRICT_EVIDENCE = "strict-evidence"
    COO_REVIEW = "coo-review"
    HUMAN_REVIEW = "human-review"
    FAN_IN_WAIT_ALL = "fan-in-wait-all"
    DEFAULT_TRANSITION = "default-transition"


class Adoption(Enum):
    BINDING = "binding"
    ADVISORY = "advisory"


class Authority(Enum):
    CALLER = "caller"
    COO = "coo"


@dataclass(frozen=True, eq=False)
class AgentSpec:
    role: str
    adapter: str | None = None
    model: str | None = None


@dataclass(frozen=True, eq=False)
class BrickSpec:
    kind: str
    work: str
    alias: str | None = None
    write: bool = False
    returns: str | None = None
    agent: AgentSpec | None = None
    adapter: str | None = None
    model: str | None = None
    source_facts: tuple[str, ...] = ()


@dataclass(frozen=True, eq=False)
class EdgeSpec:
    source: BrickSpec
    target: BrickSpec
    movement: str = "forward"


@dataclass(frozen=True)
class GroupSpec:
    role: str
    members: tuple[EdgeSpec, ...]


@dataclass(frozen=True)
class RerouteMark:
    on: Concern
    to: BrickSpec
    budget: int


@dataclass(frozen=True)
class HoldMark:
    on: Concern


@dataclass(frozen=True)
class FanInRoute:
    converge_on: BrickSpec
    marks: tuple[RerouteMark | HoldMark, ...]


@dataclass(frozen=True)
class GraphSpec:
    nodes: tuple[BrickSpec, ...]
    edges: tuple[EdgeSpec, ...]
    groups: tuple[GroupSpec, ...] = ()
    terminal: BrickSpec | None = None
    fan_in_targets: tuple[BrickSpec, ...] = ()
    fan_in_routes: tuple[FanInRoute, ...] = ()


@dataclass(frozen=True)
class ComposedGraph:
    nodes: tuple[Mapping[str, Any], ...]
    edges: tuple[Mapping[str, Any], ...]
    groups: tuple[Mapping[str, Any], ...]
    composed_plan: Mapping[str, Any]
    building_id: str
    declared_by: str
    selected_adapter_ref: str
    selected_model_ref: str
    selected_shape_ref: str
    transition_concern_adoption: str
    task_statement: str = ""

    def as_compose_args(
        self,
    ) -> tuple[tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]]:
        return (
            copy.deepcopy(self.nodes),
            copy.deepcopy(self.edges),
            copy.deepcopy(self.groups),
        )

    def as_intake_args(self) -> Mapping[str, Any]:
        args: dict[str, Any] = {
            "nodes": copy.deepcopy(self.nodes),
            "edges": copy.deepcopy(self.edges),
            "groups": copy.deepcopy(self.groups),
            "declared_by": self.declared_by,
            "building_id": self.building_id,
            "selected_adapter_ref": self.selected_adapter_ref,
            "selected_model_ref": self.selected_model_ref,
            "selected_shape_ref": self.selected_shape_ref,
            "transition_concern_adoption": self.transition_concern_adoption,
            "chain_preset_ref": "",
        }
        if self.task_statement:
            args["task_statement"] = self.task_statement
        return args


def brick(
    kind: str,
    work: str,
    *,
    alias: str | None = None,
    write: bool = False,
    returns: str | None = None,
    agent: AgentSpec | None = None,
    adapter: str | None = None,
    model: str | None = None,
    source_facts: Sequence[str] | None = None,
    **kwargs: Any,
) -> BrickSpec:
    if kwargs:
        forbidden = sorted(key for key in kwargs if key in _FORBIDDEN_BRICK_KWARGS)
        if forbidden:
            raise TypeError(
                "brick() derives these fields; do not declare them: "
                + ", ".join(forbidden)
            )
        raise TypeError("brick() got unexpected keyword argument(s): " + ", ".join(sorted(kwargs)))
    clean_kind = _bare_token("kind", kind)
    clean_work = _non_empty_text("work", work)
    clean_alias = _optional_bare_token("alias", alias)
    return BrickSpec(
        kind=clean_kind,
        work=clean_work,
        alias=clean_alias,
        write=bool(write),
        returns=_optional_text(returns),
        agent=agent,
        adapter=_optional_bare_or_ref("adapter", adapter),
        model=_optional_bare_or_ref("model", model),
        source_facts=tuple(str(item).strip() for item in (source_facts or ()) if str(item).strip()),
    )


def agent(role: str, *, adapter: str | None = None, model: str | None = None) -> AgentSpec:
    return AgentSpec(
        role=_bare_token("role", role),
        adapter=_optional_bare_or_ref("adapter", adapter),
        model=_optional_bare_or_ref("model", model),
    )


def chain(specs: Sequence[BrickSpec]) -> GraphSpec:
    ordered = tuple(specs)
    if not ordered:
        raise TypeError("chain() requires at least one brick")
    _require_bricks("chain", ordered)
    edges = tuple(EdgeSpec(source, target) for source, target in zip(ordered, ordered[1:]))
    return GraphSpec(nodes=_unique_nodes(ordered), edges=edges, terminal=ordered[-1])


def fan_out(source: BrickSpec, branches: Sequence[BrickSpec]) -> GraphSpec:
    _require_bricks("fan_out source", (source,))
    branch_tuple = tuple(branches)
    if not branch_tuple:
        raise TypeError("fan_out() requires at least one branch")
    _require_bricks("fan_out branches", branch_tuple)
    edges = tuple(EdgeSpec(source, branch) for branch in branch_tuple)
    return GraphSpec(
        nodes=_unique_nodes((source, *branch_tuple)),
        edges=edges,
        groups=(GroupSpec("fan_out", edges),),
    )


def fan_in(
    sources: Sequence[BrickSpec],
    converge_on: BrickSpec,
    *,
    route: Sequence[RerouteMark | HoldMark] = (),
) -> GraphSpec:
    source_tuple = tuple(sources)
    if not source_tuple:
        raise TypeError("fan_in() requires at least one source")
    _require_bricks("fan_in sources", source_tuple)
    _require_bricks("fan_in converge_on", (converge_on,))
    if any(source is converge_on for source in source_tuple):
        raise ValueError("fan_in() converge_on cannot also be a source")
    for source in source_tuple:
        if not _optional_text(source.returns):
            raise TypeError("fan_in() sources must declare returns=")

    marks = tuple(route)
    for mark in marks:
        if isinstance(mark, RerouteMark):
            if mark.to is converge_on:
                raise ValueError("self-reroute is not admitted for a fan-in convergence node")
        elif not isinstance(mark, HoldMark):
            raise TypeError("fan_in() route entries must be reroute() or hold() marks")

    edges = tuple(EdgeSpec(source, converge_on) for source in source_tuple)
    return GraphSpec(
        nodes=_unique_nodes((*source_tuple, converge_on)),
        edges=edges,
        groups=(GroupSpec("fan_in", edges),),
        terminal=converge_on,
        fan_in_targets=(converge_on,),
        fan_in_routes=(FanInRoute(converge_on, marks),),
    )


def edge(src: BrickSpec, dst: BrickSpec) -> GraphSpec:
    _require_bricks("edge endpoints", (src, dst))
    forward_edge = EdgeSpec(src, dst)
    return GraphSpec(nodes=_unique_nodes((src, dst)), edges=(forward_edge,), terminal=dst)


def converge(*parts: GraphSpec, terminal: BrickSpec) -> GraphSpec:
    if not parts:
        raise TypeError("converge() requires at least one graph part")
    for part in parts:
        if not isinstance(part, GraphSpec):
            raise TypeError("converge() parts must be GraphSpec values")
    _require_bricks("converge terminal", (terminal,))

    nodes: list[BrickSpec] = []
    edges: list[EdgeSpec] = []
    groups: list[GroupSpec] = []
    fan_in_targets: list[BrickSpec] = []
    fan_in_routes: list[FanInRoute] = []
    for part in parts:
        nodes.extend(part.nodes)
        edges.extend(part.edges)
        groups.extend(part.groups)
        fan_in_targets.extend(part.fan_in_targets)
        fan_in_routes.extend(part.fan_in_routes)

    if not any(target is terminal for target in fan_in_targets):
        raise ValueError("converge() terminal must be a fan_in() convergence target")

    return GraphSpec(
        nodes=_unique_nodes((*nodes, terminal)),
        edges=_unique_edges(edges),
        groups=tuple(groups),
        terminal=terminal,
        fan_in_targets=_unique_nodes(fan_in_targets),
        fan_in_routes=tuple(fan_in_routes),
    )


def reroute(on: Concern, to: BrickSpec, *, budget: int) -> RerouteMark:
    if not isinstance(on, Concern):
        raise TypeError("reroute() on must be a Concern")
    _require_bricks("reroute target", (to,))
    if not isinstance(budget, int) or budget <= 0:
        raise ValueError("reroute() budget must be a finite positive integer")
    return RerouteMark(on=on, to=to, budget=budget)


def hold(on: Concern) -> HoldMark:
    if not isinstance(on, Concern):
        raise TypeError("hold() on must be a Concern")
    return HoldMark(on=on)


def assemble(
    graph: GraphSpec,
    *,
    declared_by: str,
    authority: Authority = Authority.CALLER,
    task: str | None = None,
    task_source_ref: str | None = None,
    building_id: str | None = None,
    adapter: str = "local",
    model: str = "default",
    gates: Sequence[Gate | str] = (),
    adoption: Adoption | str = Adoption.BINDING,
    shape: str | None = None,
    repo_root: Path | str = REPO_ROOT,
    write_scope: Mapping[str, Any] | None = None,
) -> ComposedGraph:
    if not isinstance(graph, GraphSpec):
        raise TypeError("assemble() graph must be a GraphSpec")
    if graph.terminal is None:
        raise ValueError("assemble() graph must declare a terminal brick")

    repo = Path(repo_root).resolve()
    registry = _load_shape_registry(repo)
    task_body = _task_body(repo, task=task, task_source_ref=task_source_ref)
    resolved_building_id = _front_door_building_id(
        building_id=building_id,
        task=task_body,
        task_source_ref=task_source_ref,
    )
    declared_by_text = _declared_by(declared_by, authority)
    selected_adapter_ref = _prefixed_ref("adapter", adapter)
    selected_model_ref = _prefixed_ref("model", model)
    selected_shape_ref = _prefixed_ref("building-shape", shape) if shape else ""
    concern_adoption = _adoption_value(adoption)

    lowered_nodes, lowered_edges, lowered_groups = _lower_graph(
        graph,
        building_id=resolved_building_id,
        declared_by=declared_by_text,
        registry=registry,
        gates=gates,
        write_scope=write_scope,
    )
    _validate_interim_fan_in_contract(lowered_nodes, lowered_edges, lowered_groups)

    composed_plan = compose_building(
        lowered_nodes,
        lowered_edges,
        groups=lowered_groups,
        selected_shape_ref=selected_shape_ref,
        declared_by=declared_by_text,
        chain_preset_ref="",
        building_id=resolved_building_id,
        selected_adapter_ref=selected_adapter_ref,
        selected_model_ref=selected_model_ref,
        transition_concern_adoption=concern_adoption,
        repo_root=repo,
    )
    frozen_plan = _frozen_composed_plan(composed_plan, task_body)

    return ComposedGraph(
        nodes=tuple(copy.deepcopy(lowered_nodes)),
        edges=tuple(copy.deepcopy(lowered_edges)),
        groups=tuple(copy.deepcopy(lowered_groups)),
        composed_plan=frozen_plan,
        building_id=resolved_building_id,
        declared_by=declared_by_text,
        selected_adapter_ref=selected_adapter_ref,
        selected_model_ref=selected_model_ref,
        selected_shape_ref=selected_shape_ref,
        transition_concern_adoption=concern_adoption,
        task_statement=task_body or "",
    )


def persist_proposed_building_graph(
    composed: ComposedGraph,
    output_root: Path | str,
    *,
    goal_id: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist the validated composed-plan snapshot produced at propose time.

    The written JSON is the frozen run input for the pre-run approval seam. It is
    support evidence only: this helper records no provider state, chooses no
    Movement, and judges no success or quality.
    """

    if not isinstance(composed, ComposedGraph):
        raise TypeError("persist_proposed_building_graph() requires a ComposedGraph")
    root = Path(output_root).expanduser().resolve()
    raw_goal_id = _optional_text(goal_id) or composed.building_id
    proposal_dir = root / _composition_slug(raw_goal_id)
    proposal_path = proposal_dir / _PROPOSED_BUILDING_GRAPH_FILENAME
    if proposal_path.exists() and not overwrite:
        raise FileExistsError(f"proposed Building graph already exists: {proposal_path}")
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(
        json.dumps(composed.composed_plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return proposal_path


def _frozen_composed_plan(
    composed_plan: Mapping[str, Any],
    task_body: str | None,
) -> Mapping[str, Any]:
    plan = copy.deepcopy(composed_plan)
    if task_body is None:
        return plan
    carry = inline_task_source_carry(task_body, chain_preset_ref="")
    plan["task_source_ref"] = carry["task_source_ref"]
    plan["task_statement"] = carry["task_statement"]
    plan["task_source_hash"] = carry["task_source_hash"]
    plan["task_source_hash_algorithm"] = carry["task_source_hash_algorithm"]
    plan["task_source_hash_basis"] = carry["task_source_hash_basis"]
    return plan


def stamp_profile_gates(
    edges: Sequence[Mapping[str, Any]],
    nodes_by_id: Mapping[str, Mapping[str, Any]],
    gate_tokens: Sequence[Gate | str],
    *,
    registry: Mapping[str, Any],
    declared_by_origin: str,
) -> list[Mapping[str, Any]]:
    tokens = {_gate_value(token) for token in gate_tokens}
    step_templates = registry.get("step_templates", {})
    stamped: list[Mapping[str, Any]] = []
    for raw_edge in edges:
        edge_row = dict(raw_edge)
        source_node = nodes_by_id.get(str(edge_row.get("source", "")).strip(), {})
        template_ref = str(source_node.get("step_template_ref", "")).strip()
        source_template = step_templates.get(template_ref, {})
        qa_row = str(source_template.get("role_need", "")).strip() == "reviewer"
        target = str(edge_row.get("target", "")).strip()
        final_transition = target.startswith(("building-boundary:", "building-boundary-"))
        extra_refs: list[str] = []
        provenance_tokens: list[str] = []
        if qa_row and "strict-evidence" in tokens:
            extra_refs.append(GATE_CONCEPT_TOKEN_GATE_REFS["strict-evidence"])
            provenance_tokens.append("strict-evidence")
        if final_transition:
            for token in ("coo-review", "human-review"):
                if token in tokens:
                    extra_refs.append(GATE_CONCEPT_TOKEN_GATE_REFS[token])
                    provenance_tokens.append(token)
        refs = [DEFAULT_LINK_GATE_REF]
        for ref in extra_refs:
            if ref not in refs:
                refs.append(ref)
        edge_row["declared_gate_refs"] = refs
        if provenance_tokens:
            edge_row["gate_concept_provenance"] = {
                "tokens": provenance_tokens,
                "declared_by": declared_by_origin,
            }
        if GATE_CONCEPT_TOKEN_GATE_REFS["human-review"] in extra_refs:
            edge_row["gate_sequence_policy"] = _materializer_human_gate_hold_policy()
        stamped.append(edge_row)
    return stamped


def lower_route(
    converge_node: Mapping[str, Any],
    route_marks: Sequence[RerouteMark | HoldMark],
    *,
    nodes_by_handle: Mapping[BrickSpec, Mapping[str, Any]],
    node_id_by_handle: Mapping[BrickSpec, str],
) -> None:
    policy: dict[str, Mapping[str, Any]] = {}
    converge_id = str(converge_node.get("node_id", "")).strip()
    for mark in route_marks:
        if isinstance(mark, RerouteMark):
            target_id = node_id_by_handle.get(mark.to)
            if not target_id:
                raise ValueError("reroute target is not present in the graph")
            if target_id == converge_id:
                raise ValueError("self-reroute is not admitted for a fan-in convergence node")
            target_node = nodes_by_handle[mark.to]
            existing = target_node.get("node_reroute_budget")
            if existing is not None and int(existing) != mark.budget:
                raise ValueError(f"conflicting reroute budgets for {target_id}")
            target_node["node_reroute_budget"] = mark.budget  # type: ignore[index]
            policy[mark.on.value] = {"action": "target", "target_ref": target_id}
        elif isinstance(mark, HoldMark):
            policy[mark.on.value] = {"action": "hold"}
        else:
            raise TypeError("route marks must be reroute() or hold() values")
    if policy:
        converge_node["closure_transition_target_policy"] = policy  # type: ignore[index]


def _lower_graph(
    graph: GraphSpec,
    *,
    building_id: str,
    declared_by: str,
    registry: Mapping[str, Any],
    gates: Sequence[Gate | str],
    write_scope: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    building_slug = _composition_slug(building_id)
    nodes = _unique_nodes((*graph.nodes, graph.terminal) if graph.terminal else graph.nodes)
    node_id_by_handle = _node_ids(nodes, building_slug)
    fan_in_sources = _fan_in_source_handles(graph.groups)

    lowered_nodes: list[dict[str, Any]] = []
    mutable_nodes_by_handle: dict[BrickSpec, dict[str, Any]] = {}
    for spec in nodes:
        node = _lower_node(
            spec,
            node_id=node_id_by_handle[spec],
            registry=registry,
            fan_in_source=spec in fan_in_sources,
            write_scope=write_scope,
        )
        lowered_nodes.append(node)
        mutable_nodes_by_handle[spec] = node

    lowered_edges, edge_refs = _lower_edges(
        graph.edges,
        terminal=graph.terminal,
        node_id_by_handle=node_id_by_handle,
    )
    outgoing_by_handle: dict[BrickSpec, list[str]] = defaultdict(list)
    for edge_spec in graph.edges:
        outgoing_by_handle[edge_spec.source].append(edge_refs[edge_spec])
    if graph.terminal is not None:
        outgoing_by_handle[graph.terminal].append(_boundary_edge_ref(node_id_by_handle[graph.terminal]))
    for spec, refs in outgoing_by_handle.items():
        if len(refs) > 1:
            mutable_nodes_by_handle[spec]["completion_edge_ref"] = refs[0]

    lowered_groups = _lower_groups(graph.groups, edge_refs=edge_refs, building_slug=building_slug)

    for fan_in_route in graph.fan_in_routes:
        converge_node = mutable_nodes_by_handle.get(fan_in_route.converge_on)
        if converge_node is None:
            raise ValueError("fan-in route convergence node is not present in the graph")
        lower_route(
            converge_node,
            fan_in_route.marks,
            nodes_by_handle=mutable_nodes_by_handle,
            node_id_by_handle=node_id_by_handle,
        )

    nodes_by_id = {str(node["node_id"]): node for node in lowered_nodes}
    lowered_edges = stamp_profile_gates(
        lowered_edges,
        nodes_by_id,
        gates,
        registry=registry,
        declared_by_origin=declared_by,
    )
    return lowered_nodes, lowered_edges, lowered_groups


def _lower_node(
    spec: BrickSpec,
    *,
    node_id: str,
    registry: Mapping[str, Any],
    fan_in_source: bool,
    write_scope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    step_template_ref = f"building-step-template:{spec.kind}"
    node: dict[str, Any] = {
        "node_id": node_id,
        "step_template_ref": step_template_ref,
        "work_statement": spec.work,
    }
    step_template = registry.get("step_templates", {}).get(step_template_ref)
    if fan_in_source:
        source_shape = ""
        if isinstance(step_template, Mapping):
            source_shape = str(step_template.get("required_return_shape", "")).strip()
        if not source_shape:
            source_shape = str(spec.returns or "").strip()
        node["required_return_shape"] = _materializer_strip_field(
            source_shape,
            _TRANSITION_CONCERN_FIELD,
        )
    if spec.agent is not None:
        node["agent_object_ref"] = _prefixed_ref("agent-object", spec.agent.role)
    adapter_ref = spec.adapter or (spec.agent.adapter if spec.agent else None)
    model_ref = spec.model or (spec.agent.model if spec.agent else None)
    if adapter_ref:
        node["selected_adapter_ref"] = _prefixed_ref("adapter", adapter_ref)
    if model_ref:
        node["selected_model_ref"] = _prefixed_ref("model", model_ref)
    if spec.source_facts:
        node["source_facts"] = list(spec.source_facts)
    if spec.write and isinstance(step_template, Mapping) and bool(step_template.get("write_need")):
        node["write_scope"] = _validated_write_scope(write_scope)
        node["requires_brick_write_scope"] = True
    return node


def _lower_edges(
    edge_specs: Sequence[EdgeSpec],
    *,
    terminal: BrickSpec | None,
    node_id_by_handle: Mapping[BrickSpec, str],
) -> tuple[list[Mapping[str, Any]], Mapping[EdgeSpec, str]]:
    edge_ref_counts: Counter[str] = Counter()
    edge_refs: dict[EdgeSpec, str] = {}
    lowered: list[Mapping[str, Any]] = []
    for edge_spec in edge_specs:
        source_id = node_id_by_handle[edge_spec.source]
        target_id = node_id_by_handle[edge_spec.target]
        base_ref = f"edge:{source_id}-to-{target_id}"
        edge_ref = _unique_edge_ref(base_ref, edge_ref_counts)
        edge_refs[edge_spec] = edge_ref
        lowered.append(
            {
                "edge_ref": edge_ref,
                "source": source_id,
                "target": target_id,
                "movement": edge_spec.movement,
            }
        )
    if terminal is not None:
        terminal_id = node_id_by_handle[terminal]
        lowered.append(
            {
                "edge_ref": _boundary_edge_ref(terminal_id),
                "source": terminal_id,
                "target": _DEFAULT_BOUNDARY_REF,
                "movement": "forward",
            }
        )
    return lowered, edge_refs


def _lower_groups(
    groups: Sequence[GroupSpec],
    *,
    edge_refs: Mapping[EdgeSpec, str],
    building_slug: str,
) -> list[Mapping[str, Any]]:
    role_counts: Counter[str] = Counter()
    lowered: list[Mapping[str, Any]] = []
    for group in groups:
        role_counts[group.role] += 1
        member_refs = [edge_refs[member] for member in group.members]
        lowered.append(
            {
                "group_id": f"group-{building_slug}-{group.role.replace('_', '-')}-{role_counts[group.role]}",
                "group_role": group.role,
                "member_ref_kind": "link_edge",
                "member_refs": member_refs,
            }
        )
    return lowered


def _validate_interim_fan_in_contract(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
) -> None:
    node_by_id = {str(node.get("node_id", "")).strip(): node for node in nodes}
    edge_by_ref = {str(edge.get("edge_ref", "")).strip(): edge for edge in edges}
    fan_in_source_ids: set[str] = set()
    for group in groups:
        if str(group.get("group_role", "")).strip() != "fan_in":
            continue
        member_refs = group.get("member_refs", ())
        if not isinstance(member_refs, Sequence) or isinstance(member_refs, (str, bytes)):
            raise ValueError("fan_in group member_refs must be an array")
        for member_ref in member_refs:
            edge_record = edge_by_ref.get(str(member_ref).strip())
            if edge_record is None:
                raise ValueError(f"fan_in group member does not resolve: {member_ref}")
            fan_in_source_ids.add(str(edge_record.get("source", "")).strip())

    for source_id in fan_in_source_ids:
        shape = str(node_by_id.get(source_id, {}).get("required_return_shape", "")).lower()
        if _TRANSITION_CONCERN_FIELD in shape:
            raise ValueError(f"fan-in source still carries {_TRANSITION_CONCERN_FIELD}: {source_id}")

    for node_id, node in node_by_id.items():
        policy = node.get("closure_transition_target_policy")
        if not isinstance(policy, Mapping):
            continue
        for concern_kind, row in policy.items():
            if not isinstance(row, Mapping):
                raise ValueError(f"closure policy row must be an object: {node_id}.{concern_kind}")
            action = str(row.get("action", "")).strip()
            if action == "hold":
                if row.get("target_ref"):
                    raise ValueError(f"hold policy must not carry target_ref: {node_id}.{concern_kind}")
                continue
            if action not in {"target", "reroute"}:
                raise ValueError(f"closure policy action must be hold or target: {node_id}.{concern_kind}")
            target_ref = str(row.get("target_ref", "")).strip()
            if not target_ref or target_ref not in node_by_id:
                raise ValueError(f"closure policy target_ref does not resolve: {node_id}.{concern_kind}")
            if target_ref == node_id:
                raise ValueError(f"closure policy target_ref self-reroutes: {node_id}.{concern_kind}")
            budget = node_by_id[target_ref].get("node_reroute_budget")
            if not isinstance(budget, int) or budget <= 0:
                raise ValueError(f"closure policy target_ref is not budgeted: {target_ref}")


def _node_ids(nodes: Sequence[BrickSpec], building_slug: str) -> Mapping[BrickSpec, str]:
    kind_counts = Counter(node.kind for node in nodes)
    seen_slugs: dict[str, BrickSpec] = {}
    ids: dict[BrickSpec, str] = {}
    for node in nodes:
        if kind_counts[node.kind] > 1 and not node.alias:
            raise TypeError(f"brick kind {node.kind!r} repeats; declare alias=")
        slug = _composition_slug(node.alias or node.kind)
        if slug in seen_slugs and seen_slugs[slug] is not node:
            raise TypeError(f"brick alias/kind slug duplicates another node: {slug}")
        seen_slugs[slug] = node
        ids[node] = f"{building_slug}-{slug}"
    return ids


def _fan_in_source_handles(groups: Sequence[GroupSpec]) -> set[BrickSpec]:
    sources: set[BrickSpec] = set()
    for group in groups:
        if group.role != "fan_in":
            continue
        for member in group.members:
            sources.add(member.source)
    return sources


def _front_door_building_id(
    *,
    building_id: str | None,
    task: str | None,
    task_source_ref: str | None,
) -> str:
    declared = _optional_text(building_id)
    if declared:
        return declared
    body = _optional_text(task) or _optional_text(task_source_ref)
    if not body:
        raise ValueError("assemble() requires building_id or task/task_source_ref for stable id derivation")
    carry = inline_task_source_carry(body, chain_preset_ref="")
    return str(carry["default_building_id"])


def _task_body(repo: Path, *, task: str | None, task_source_ref: str | None) -> str | None:
    if task is not None:
        return _non_empty_text("task", task)
    ref = _optional_text(task_source_ref)
    if not ref:
        return None
    path = Path(ref)
    if not path.is_absolute():
        path = repo / ref
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ref


def _declared_by(value: str, authority: Authority) -> str:
    if not isinstance(authority, Authority):
        raise TypeError("authority must be an Authority")
    name = _non_empty_text("declared_by", value).replace("_", "-").lower()
    if ":" in name:
        raise ValueError("declared_by must be bare text or dash-prefixed caller/coo text; colon is not admitted")
    if name.startswith(("caller-", "coo-")):
        return name
    return f"{authority.value}-{name}"


def _adoption_value(value: Adoption | str) -> str:
    if isinstance(value, Adoption):
        return "advisory" if value is Adoption.ADVISORY else ""
    text = _non_empty_text("adoption", value)
    if text == Adoption.BINDING.value:
        return ""
    if text == Adoption.ADVISORY.value:
        return "advisory"
    raise ValueError("adoption must be binding or advisory")


def _validated_write_scope(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("write=True requires assemble(write_scope=...)")
    allowed = value.get("allowed_paths")
    forbidden = value.get("forbidden_paths")
    if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes)):
        raise ValueError("write_scope.allowed_paths must be a non-empty array")
    if not [str(path).strip() for path in allowed if str(path).strip()]:
        raise ValueError("write_scope.allowed_paths must be non-empty")
    if not isinstance(forbidden, Sequence) or isinstance(forbidden, (str, bytes)):
        raise ValueError("write_scope.forbidden_paths must be an array")
    return {
        "allowed_paths": [str(path).strip() for path in allowed if str(path).strip()],
        "forbidden_paths": [str(path).strip() for path in forbidden if str(path).strip()],
    }


def _gate_value(value: Gate | str) -> str:
    if isinstance(value, Gate):
        return value.value
    text = _non_empty_text("gate", value)
    admitted = {gate.value for gate in Gate}
    if text not in admitted:
        raise ValueError(f"gate is not admitted: {text}")
    return text


def _prefixed_ref(prefix: str, value: str) -> str:
    text = _non_empty_text(prefix, value)
    marker = f"{prefix}:"
    if text.startswith(marker):
        return text
    if ":" in text:
        raise ValueError(f"{prefix} must be bare or already {marker}-prefixed")
    return f"{marker}{text}"


def _optional_bare_or_ref(label: str, value: str | None) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    if ":" in text and not text.startswith(("adapter:", "model:", "agent-object:")):
        raise ValueError(f"{label} must be bare text or an admitted ref")
    return text


def _bare_token(label: str, value: str) -> str:
    text = _non_empty_text(label, value)
    if ":" in text:
        raise ValueError(f"{label} must be a bare token")
    return text


def _optional_bare_token(label: str, value: str | None) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    if ":" in text:
        raise ValueError(f"{label} must be a bare token")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _non_empty_text(label: str, value: Any) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"{label} must be non-empty text")
    return text


def _require_bricks(label: str, values: Sequence[BrickSpec]) -> None:
    if any(not isinstance(value, BrickSpec) for value in values):
        raise TypeError(f"{label} must contain BrickSpec values")


def _unique_nodes(values: Sequence[BrickSpec]) -> tuple[BrickSpec, ...]:
    seen: set[int] = set()
    unique: list[BrickSpec] = []
    for value in values:
        if value is None:
            continue
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
    return tuple(unique)


def _unique_edges(values: Sequence[EdgeSpec]) -> tuple[EdgeSpec, ...]:
    seen: set[int] = set()
    unique: list[EdgeSpec] = []
    for value in values:
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
    return tuple(unique)


def _unique_edge_ref(base_ref: str, counts: Counter[str]) -> str:
    counts[base_ref] += 1
    if counts[base_ref] == 1:
        return base_ref
    return f"{base_ref}-{counts[base_ref]}"


def _boundary_edge_ref(node_id: str) -> str:
    return f"edge:{node_id}-to-boundary-closed"


__all__ = [
    "Adoption",
    "AgentSpec",
    "Authority",
    "BrickSpec",
    "ComposedGraph",
    "Concern",
    "Gate",
    "GraphSpec",
    "agent",
    "assemble",
    "brick",
    "chain",
    "converge",
    "edge",
    "fan_in",
    "fan_out",
    "hold",
    "lower_route",
    "persist_proposed_building_graph",
    "reroute",
    "stamp_profile_gates",
]
