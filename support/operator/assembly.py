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

from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS
from brick_protocol.agent.spec import (
    NODE_CASTING_FIELDS,
)
# AGENT-axis authoring carrier + verb, single-sourced on the Agent axis at E2/S2.
# Re-exported below (``__all__``) so existing callers — check_assembly_equivalence
# and the brick-task-author skill's ``from ...assembly import agent`` — keep
# resolving while the definition lives on its axis (assembly -> agent, acyclic).
from brick_protocol.agent.spec import (  # noqa: F401  (re-exported for callers)
    AgentSpec,
    agent,
)
# BRICK-axis authoring carrier + verb, single-sourced on the Brick axis at E2/S1.
# ``BrickSpec`` is also the node handle the retained graph-wiring tier below uses
# pervasively (EdgeSpec/GraphSpec/_coerce_node/_lower_node/...); ``brick()`` is
# called by ``_coerce_node``. Both are imported here (assembly -> brick, acyclic)
# and re-exported (``__all__``) so ``from ...assembly import brick`` keeps resolving.
from brick_protocol.brick.spec import (  # noqa: F401  (re-exported for callers)
    BrickSpec,
    brick,
    derived_worktree_write_scope,
)
from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_LINK_GATE_REF,
    REPO_ROOT,
)
from brick_protocol.link.spec import (
    ADOPTION_LITERALS,
    GATE_CONCEPT_TOKENS,
    GATE_REGISTRY,
    translate_gate_concept,
)
from brick_protocol.support.operator.composition_common import (
    _composition_slug,
)
from brick_protocol.support.operator.composition_compose import compose_building
from brick_protocol.support.operator.composition_gate_translation import (
    _materializer_human_gate_hold_policy,
)
from brick_protocol.support.operator.composition_intent import inline_task_source_carry
from brick_protocol.support.operator.composition_route_policy import (
    _materializer_apply_constitutional_default_reroute_budget,
    _materializer_constitutional_default_reroute_budget,
)
from brick_protocol.support.operator.plan_rendering import (
    _LOCAL_ADAPTER_REF,
    _is_verdict_bearing_node,
    _load_shape_registry,
)
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref


# _FORBIDDEN_BRICK_KWARGS moved to the BRICK axis (brick/spec.py) at E2/S1 — the
# forbidden-derived-field guard is part of the ``brick()`` authoring contract.
# _casting_ref_prefix / _CASTING_KWARG_BY_NAME / _build_casting_bag /
# _ADMITTED_CASTING_PREFIXES / _optional_bare_or_ref moved to the AGENT axis
# (agent/spec.py) at E2/S1 — casting authoring is Agent-axis property. The retained
# graph-wiring tier in this module no longer references any of them (their only
# callers were the relocated ``brick()``/``agent()`` verbs); the shared value-shape
# coercers they used (``_prefixed_ref``/``_bare_token``/``_non_empty_text``/
# ``_optional_text``/``_optional_bare_token``) STAY below for the graph wiring and
# are duplicated into the axis files so an axis module never imports this builder.
_DEFAULT_BOUNDARY_REF = "building-boundary:closed"
_PROPOSED_BUILDING_GRAPH_FILENAME = "proposed-building-graph.json"
# DERIVED_WORKTREE_WRITE_SCOPE default moved to the BRICK axis (brick/spec.py) at
# E2/S9 — the default write envelope a worktree-isolated build derives is
# Brick-axis property. ``derived_worktree_write_scope()`` returns a fresh deep
# copy (byte-identical to the prior ``copy.deepcopy(_DERIVED_WORKTREE_WRITE_SCOPE)``).


def _axis_enum(name: str, values: Any) -> type[Enum]:
    """Build a builder enum whose ``.value``s ARE the axis vocabulary (E2/S8 M15).

    The builder DERIVES ``Concern``/``Gate``/``Adoption`` from the owning axis
    vocab instead of re-stating literals: ``Concern`` from
    ``agent.return_fact.TRANSITION_CONCERN_KINDS``, ``Gate`` from
    ``link.spec.GATE_CONCEPT_TOKENS``, ``Adoption`` from
    ``link.spec.ADOPTION_LITERALS``. The friendly member NAME is the canonical
    ``value.upper()`` with dashes folded to underscores (``upstream_gap`` ->
    ``UPSTREAM_GAP``, ``strict-evidence`` -> ``STRICT_EVIDENCE``,
    ``binding`` -> ``BINDING``) -- byte-identical to the prior hand-written
    members -- so no axis token string is hardcoded here: add a token to the
    axis and the builder enum gains the member, drop one and it loses it. The
    members are ordered by ``.value`` for a stable, vocab-driven member order.
    """

    members = {
        str(value).upper().replace("-", "_"): str(value)
        for value in sorted(values)
    }
    return Enum(name, members)  # type: ignore[return-value]


Concern = _axis_enum("Concern", TRANSITION_CONCERN_KINDS)
Gate = _axis_enum("Gate", GATE_CONCEPT_TOKENS)
Adoption = _axis_enum("Adoption", ADOPTION_LITERALS)


class Authority(Enum):
    CALLER = "caller"
    COO = "coo"


# AgentSpec moved to the AGENT axis (agent/spec.py) and BrickSpec to the BRICK axis
# (brick/spec.py) at E2/S1-S2 — the per-lane/per-node authoring carriers belong to
# their axes. Both are imported at the top of this module and re-exported via
# ``__all__``; the retained graph-wiring tier below references the ``BrickSpec`` /
# ``AgentSpec`` names through those imports exactly as before (behavior-identical).
@dataclass(frozen=True, eq=False)
class EdgeSpec:
    source: BrickSpec
    target: BrickSpec
    movement: str = "forward"


@dataclass(frozen=True)
class GroupSpec:
    role: str
    members: tuple[EdgeSpec, ...]
    sibling_independence: tuple[str, ...] = ()


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


# The ``brick()`` authoring verb moved to the BRICK axis (brick/spec.py) and the
# ``agent()`` verb to the AGENT axis (agent/spec.py) at E2/S1-S2. Both are imported
# at the top of this module and re-exported via ``__all__`` so callers keep the
# ``from ...assembly import brick, agent`` import path. ``_coerce_node`` below still
# calls ``brick(...)`` through the imported name (behavior-identical).
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
    sibling_independence: Sequence[str] = (),
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
    sibling_refs = _sibling_independence_refs(
        "fan_in() sibling_independence",
        sibling_independence,
        sources=source_tuple,
    )

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
        groups=(GroupSpec("fan_in", edges, sibling_refs),),
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


# ---------------------------------------------------------------------------
# build()/fan() — the easy front-of-front-door construction surface (E2 CORE).
#
# This is PURE sugar over the existing chain()/fan_out()/fan_in()/converge()
# lower tier: a BRICK-FIRST node literal ``[kind, work]`` / ``[kind, work, opts]``
# lowers to ``brick(kind, work, **opts)`` (the kind's default step-template agent
# is resolved downstream by compose_building -- no explicit ``agent=`` needed),
# adjacency N->N+1 is a forward edge, and a nested ``fan([...])`` block fans the
# preceding item out to each branch and the following item is the convergence.
# It adds NO new resolution, engine concept, field, or checker-meaning.
# ---------------------------------------------------------------------------

# Friendly node-opts aliases -> canonical brick() kwarg. ``effort`` is the short
# spoken alias for the ``reasoning_effort`` casting dial; ``label`` for ``alias``.
_NODE_OPT_ALIASES: Mapping[str, str] = {
    "effort": "reasoning_effort",
    "label": "alias",
}
_NODE_OPT_ROUTE_KEY = "route"


@dataclass(frozen=True)
class _BackTarget:
    """A positional reroute target: the node ``count`` items up in the build list."""

    count: int


@dataclass(frozen=True)
class _SurfaceReroute:
    """A surface reroute mark whose target is a positional ``back(N)`` reference."""

    on: Concern
    back: _BackTarget
    budget: int


@dataclass(frozen=True)
class Fan:
    """A nested fan block marker for build(): the preceding item fans out to each
    branch and the following item is the fan-in convergence. Not a GraphSpec."""

    branches: tuple[BrickSpec, ...]
    sibling_independence: tuple[str, ...] = ()


def back(count: int) -> _BackTarget:
    """A positional reroute target: the node ``count`` items up in the build list."""

    if not isinstance(count, int) or count <= 0:
        raise ValueError("back() count must be a finite positive integer")
    return _BackTarget(count)


def _coerce_node(item: Any) -> BrickSpec:
    """Lower a BRICK-FIRST node literal (or pass a BrickSpec through unchanged).

    ``[kind, work]`` / ``[kind, work, opts]`` -> ``brick(kind, work, **opts)``.
    The opts dict carries only existing brick() vocabulary (write/returns/adapter/
    model/effort/label/alias); ``route`` is NOT a brick() field and is consumed by
    fan_in lowering, so it is stripped here and surfaced separately.
    """

    if isinstance(item, BrickSpec):
        return item
    if isinstance(item, Fan):
        raise TypeError("a Fan block cannot be coerced to a node; nest it as its own build() item")
    if not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
        raise TypeError("build()/fan() items must be [kind, work] / [kind, work, opts] or a BrickSpec")
    parts = tuple(item)
    if len(parts) not in (2, 3):
        raise TypeError("a node literal must be [kind, work] or [kind, work, opts]")
    kind, work = parts[0], parts[1]
    opts = parts[2] if len(parts) == 3 else {}
    if not isinstance(opts, Mapping):
        raise TypeError("node opts (slot 2) must be a mapping")
    brick_kwargs: dict[str, Any] = {}
    for raw_key, value in opts.items():
        if raw_key == _NODE_OPT_ROUTE_KEY:
            # route= is NOT a brick() field -- it is the convergence node's fan-in
            # reroute/hold marks, consumed by build() via _node_route_marks and
            # lowered onto the fan_in. Strip it from the brick() kwargs here.
            continue
        key = _NODE_OPT_ALIASES.get(raw_key, raw_key)
        brick_kwargs[key] = value
    return brick(kind, work, **brick_kwargs)


def _node_route_marks(item: Any) -> tuple[Any, ...]:
    """Extract the ``route`` opt (surface reroute()/hold() marks) from a node literal."""

    if isinstance(item, (BrickSpec, Fan)) or not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
        return ()
    parts = tuple(item)
    if len(parts) != 3 or not isinstance(parts[2], Mapping):
        return ()
    raw = parts[2].get(_NODE_OPT_ROUTE_KEY, ())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise TypeError("node route= must be a list of reroute()/hold() marks")
    return tuple(raw)


def fan(branches: Sequence[Any], *, sibling_independence: Sequence[str] = ()) -> Fan:
    """A nested fan block: the preceding build() item fans out to each branch and
    the following item is the fan-in convergence. Branches lower like build items."""

    for branch in branches:
        if _node_route_marks(branch):
            raise TypeError("route= is a fan-in opt; declare it on the convergence node, not a fan branch")
    coerced = tuple(_coerce_node(branch) for branch in branches)
    if not coerced:
        raise TypeError("fan() requires at least one branch")
    sibling_refs = _sibling_independence_refs(
        "fan() sibling_independence",
        sibling_independence,
        sources=coerced,
    )
    return Fan(coerced, sibling_refs)


def _with_fields(spec: BrickSpec, *, alias: str | None = None, returns: str | None = None) -> BrickSpec:
    """Return a copy of ``spec`` with ``alias``/``returns`` filled (frozen rebuild).

    Used by the EASY tier (``build()``) to mint an auto-id or auto-derive a fan
    branch's return shape BEFORE lowering. An already-declared value is never
    overwritten -- the operator's explicit ``alias=``/``returns=`` wins -- so this
    only fills the gap that lets the easy inputs flow through the strict LOWER tier.
    """

    if alias is None and returns is None:
        return spec
    return BrickSpec(
        kind=spec.kind,
        work=spec.work,
        alias=spec.alias if spec.alias else alias,
        write=spec.write,
        returns=spec.returns if spec.returns else returns,
        agent=spec.agent,
        gates=spec.gates,
        casting=spec.casting,
        source_facts=spec.source_facts,
        node_write_scope=spec.node_write_scope,
        proof_obligations=spec.proof_obligations,
    )


def _auto_fan_branch_returns(spec: BrickSpec, registry: Mapping[str, Any]) -> BrickSpec:
    """AUTO-RETURNS: a fan branch carrying a kind whose Brick template supplies
    ``required_return_shape`` does not force the operator to restate ``returns=``.

    ``fan_in()`` (the LOWER tier) requires every source to declare ``returns=``.
    The EASY tier fills the branch's ``returns`` from the SAME template-full shape
    that composition materializes, so Link carry filtering stays separate from the
    Brick return contract. An explicit ``returns=`` is left untouched (back-compat).
    """

    if _optional_text(spec.returns):
        return spec
    step_template = registry.get("step_templates", {}).get(f"building-step-template:{spec.kind}")
    shape = ""
    if isinstance(step_template, Mapping):
        shape = str(step_template.get("required_return_shape", "")).strip()
    if not shape:
        return spec
    return _with_fields(spec, returns=shape)


def _auto_id_repeated_kinds(coerced_nodes: Sequence[BrickSpec | Fan]) -> list[BrickSpec | Fan]:
    """AUTO-ID: mint a stable alias for nodes that share a kind so the operator
    needs NO ``alias=``.

    ``_node_ids()`` (the LOWER tier) raises when two nodes share a kind without an
    alias. Here the EASY tier assigns a stable per-kind suffix (``kind``,
    ``kind-2``, ``kind-3``, ...) in declaration order across the WHOLE node set
    (top-level spine + every fan branch), so the operator declares no alias. A
    node that ALREADY carries an alias/label keeps it (the optional ``label``/``as``
    override) and does not consume an auto-suffix slot. The LOWER tier and its
    strictness are untouched -- only the spec handed to it gains the alias.
    """

    flat: list[BrickSpec] = []
    for node in coerced_nodes:
        if isinstance(node, Fan):
            flat.extend(node.branches)
        else:
            flat.append(node)
    kind_counts = Counter(spec.kind for spec in flat)
    repeated = {kind for kind, count in kind_counts.items() if count > 1}
    if not repeated:
        return list(coerced_nodes)

    minted: dict[int, BrickSpec] = {}
    seen_per_kind: Counter[str] = Counter()
    for spec in flat:
        if spec.kind not in repeated or spec.alias:
            continue
        seen_per_kind[spec.kind] += 1
        suffix = spec.kind if seen_per_kind[spec.kind] == 1 else f"{spec.kind}-{seen_per_kind[spec.kind]}"
        minted[id(spec)] = _with_fields(spec, alias=suffix)

    if not minted:
        return list(coerced_nodes)

    rewritten: list[BrickSpec | Fan] = []
    for node in coerced_nodes:
        if isinstance(node, Fan):
            rewritten.append(
                Fan(
                    tuple(minted.get(id(branch), branch) for branch in node.branches),
                    node.sibling_independence,
                )
            )
        else:
            rewritten.append(minted.get(id(node), node))
    return rewritten


def build(items: Sequence[Any]) -> GraphSpec:
    """Compile a top-to-bottom build list to one GraphSpec over existing primitives.

    Item N->N+1 is a forward edge; a ``fan([...])`` block fans the PRECEDING item
    out to each branch and the FOLLOWING item is the fan-in convergence. When the
    first item is ``fan([...])``, its branches are parallel roots and the following
    item is their fan-in convergence. The last item is terminal. A convergence
    node's ``route`` opt becomes reroute()/hold() on the fan_in. The result is
    exactly the GraphSpec the hand-written chain()/fan_out()/fan_in()/converge()
    tier emits.

    The EASY tier auto-mints a stable alias for repeated kinds and auto-derives a
    fan branch's ``returns`` from its kind's Brick template, so the operator writes
    NO ``alias=`` and NO ``returns=``. Explicit ``alias=``/``label``/``returns=``
    still win (back-compat); the strict LOWER tier is unchanged.
    """

    sequence = tuple(items)
    if not sequence:
        raise TypeError("build() requires at least one item")
    if isinstance(sequence[-1], Fan):
        raise TypeError("build() cannot end with a fan() block; a fan needs a following convergence")

    # First pass: coerce every node literal, remembering the linear spine of
    # plain BrickSpec items so back(N) positional reroutes can resolve.
    parts: list[GraphSpec] = []
    fan_in_terminal: BrickSpec | None = None
    items_list = list(sequence)
    coerced_nodes: list[BrickSpec | Fan] = [
        item if isinstance(item, Fan) else _coerce_node(item) for item in items_list
    ]
    # EASY-tier sugar, applied BEFORE lowering so the strict LOWER tier
    # (fan_in/_node_ids) sees fully-formed specs:
    #   * AUTO-RETURNS: fill each fan branch's returns from its kind's template.
    #   * AUTO-ID: mint a stable alias for repeated kinds (whole-graph scope).
    registry = _load_shape_registry(REPO_ROOT)
    coerced_nodes = [
        Fan(
            tuple(_auto_fan_branch_returns(branch, registry) for branch in node.branches),
            node.sibling_independence,
        )
        if isinstance(node, Fan)
        else node
        for node in coerced_nodes
    ]
    coerced_nodes = _auto_id_repeated_kinds(coerced_nodes)
    linear: list[BrickSpec] = [n for n in coerced_nodes if isinstance(n, BrickSpec)]

    def _resolve_back(source_position: int, target: _BackTarget) -> BrickSpec:
        # Resolve N items up over the linear spine of plain nodes preceding here.
        spine_index = sum(1 for n in coerced_nodes[:source_position] if not isinstance(n, Fan))
        target_index = spine_index - target.count
        if target_index < 0:
            raise ValueError(f"back({target.count}) reaches before the start of the build list")
        return linear[target_index]

    # A node id that is a fan-in convergence: it already has its incoming edges
    # from the fan_in, so when it is visited as a plain node it must only emit its
    # OWN outgoing forward edge -- never a duplicate incoming one.
    last_real: BrickSpec | None = None
    position = 0
    while position < len(coerced_nodes):
        node = coerced_nodes[position]
        if isinstance(node, Fan):
            source = last_real
            following_position = position + 1
            if following_position >= len(coerced_nodes) or isinstance(coerced_nodes[following_position], Fan):
                raise TypeError("a fan() block needs a following convergence node")
            convergence = coerced_nodes[following_position]
            assert isinstance(convergence, BrickSpec)
            route_marks = _lower_surface_route(
                _node_route_marks(items_list[following_position]),
                source_position=following_position,
                resolve_back=_resolve_back,
            )
            if source is not None:
                parts.append(fan_out(source, node.branches))
            parts.append(
                fan_in(
                    node.branches,
                    convergence,
                    route=route_marks,
                    sibling_independence=node.sibling_independence,
                )
            )
            fan_in_terminal = convergence
            # Consume ONLY the fan; the convergence is visited next as a plain node
            # so its outgoing forward edge (to any node following it) is emitted.
            # It already owns its incoming fan_in edges. Clear last_real so the
            # convergence does not get a spurious leading edge from this source.
            last_real = None
            position += 1
            continue
        # A plain node. Its forward edge to a following plain node is the adjacency
        # edge; a following fan block is handled in the branch above. A convergence
        # node reached here only emits this outgoing edge (its incoming edges were
        # already emitted by fan_in), which is exactly right.
        next_position = position + 1
        if next_position < len(coerced_nodes) and not isinstance(coerced_nodes[next_position], Fan):
            nxt = coerced_nodes[next_position]
            assert isinstance(nxt, BrickSpec)
            parts.append(edge(node, nxt))
        last_real = node
        position += 1

    terminal = linear[-1]
    if fan_in_terminal is not None and terminal is fan_in_terminal:
        return converge(*parts, terminal=terminal)
    if fan_in_terminal is not None:
        # Mixed: at least one fan block plus a linear tail/spine. converge()
        # requires the terminal to be a fan-in target; when the build ends on a
        # linear node we still converge the parts and re-home the terminal.
        return converge(*parts, terminal=terminal) if any(
            t is terminal for part in parts for t in part.fan_in_targets
        ) else _converge_linear_tail(parts, terminal)
    # Pure linear build: one chain over the spine (byte-identical to chain(spine)).
    return chain(linear)


def _converge_linear_tail(parts: Sequence[GraphSpec], terminal: BrickSpec) -> GraphSpec:
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
    return GraphSpec(
        nodes=_unique_nodes((*nodes, terminal)),
        edges=_unique_edges(edges),
        groups=tuple(groups),
        terminal=terminal,
        fan_in_targets=_unique_nodes(fan_in_targets),
        fan_in_routes=tuple(fan_in_routes),
    )


def _lower_surface_route(
    marks: Sequence[Any],
    *,
    source_position: int,
    resolve_back: Any,
) -> tuple[RerouteMark | HoldMark, ...]:
    lowered: list[RerouteMark | HoldMark] = []
    for mark in marks:
        if isinstance(mark, _SurfaceReroute):
            target = resolve_back(source_position, mark.back)
            lowered.append(reroute(mark.on, to=target, budget=mark.budget))
        elif isinstance(mark, RerouteMark):
            lowered.append(mark)
        elif isinstance(mark, HoldMark):
            lowered.append(mark)
        else:
            raise TypeError("route= entries must be reroute()/hold() marks")
    return tuple(lowered)


def _sibling_independence_refs(
    label: str,
    values: Sequence[str],
    *,
    sources: Sequence[BrickSpec],
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence of fan-in source refs")
    refs: list[str] = []
    source_labels: set[str] = set()
    kind_counts = Counter(source.kind for source in sources)
    for source in sources:
        if source.alias:
            source_labels.add(source.alias)
        elif kind_counts[source.kind] == 1:
            source_labels.add(source.kind)
    for index, value in enumerate(values):
        text = _non_empty_text(f"{label}[{index}]", value)
        if text not in source_labels:
            raise ValueError(f"{label}[{index}] must resolve to a fan-in source ref")
        refs.append(text)
    return tuple(refs)


def _resolved_sibling_independence_refs(
    refs: Sequence[str],
    *,
    sources: Sequence[BrickSpec],
    node_id_by_handle: Mapping[BrickSpec, str],
) -> tuple[str, ...]:
    kind_counts = Counter(source.kind for source in sources)
    source_by_ref: dict[str, BrickSpec] = {}
    for source in sources:
        if source.alias:
            source_by_ref[source.alias] = source
        elif kind_counts[source.kind] == 1:
            source_by_ref[source.kind] = source
    resolved: list[str] = []
    for ref in refs:
        source = source_by_ref.get(ref)
        if source is None:
            raise ValueError(f"sibling_independence ref does not resolve to a fan-in source: {ref}")
        resolved.append(node_id_by_handle[source])
    return tuple(resolved)


def reroute(on: Concern, to: BrickSpec | _BackTarget, *, budget: int) -> RerouteMark | _SurfaceReroute:
    if not isinstance(on, Concern):
        raise TypeError("reroute() on must be a Concern")
    if not isinstance(budget, int) or budget <= 0:
        raise ValueError("reroute() budget must be a finite positive integer")
    if isinstance(to, _BackTarget):
        # Surface form: the target is a positional back(N) reference resolved at
        # build() time against the linear spine. Lowers to a real RerouteMark then.
        return _SurfaceReroute(on=on, back=to, budget=budget)
    _require_bricks("reroute target", (to,))
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
        selected_adapter_ref=selected_adapter_ref,
        repo=repo,
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


def fire(
    graph: GraphSpec | ComposedGraph,
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
    output_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, Any] | None = None,
    command_runner: Any | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Any | None = None,
) -> Any:
    """Fire a drawn graph through the official customer graph route.

    ``fire()`` is the P3 thin sugar over the already-admitted graph route:
    caller/COO draws a ``GraphSpec`` (or passes an already ``assemble()``-d
    ``ComposedGraph``), and this helper delegates to
    ``driver.run_customer_graph_building_in_sandbox``. It does not persist a
    caller-authored JSON packet, create a runner, choose Movement, invent route
    targets, or judge success/quality.
    """

    repo = Path(repo_root).resolve()
    if isinstance(graph, GraphSpec):
        composed = assemble(
            graph,
            declared_by=declared_by,
            authority=authority,
            task=task,
            task_source_ref=task_source_ref,
            building_id=building_id,
            adapter=adapter,
            model=model,
            gates=gates,
            adoption=adoption,
            shape=shape,
            repo_root=repo,
            write_scope=write_scope,
        )
    elif isinstance(graph, ComposedGraph):
        composed = graph
    else:
        raise TypeError("fire() graph must be a GraphSpec or ComposedGraph")

    if not str(composed.task_statement or "").strip():
        raise ValueError("fire() requires an inline task or task_source_ref carried by assemble()")

    from brick_protocol.support.operator.driver import (  # noqa: PLC0415
        run_customer_graph_building_in_sandbox,
    )

    return run_customer_graph_building_in_sandbox(
        composed,
        customer_repo_root=repo,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_timeout_seconds=adapter_timeout_seconds,
        proof_limits=proof_limits,
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
            extra_refs.append(translate_gate_concept("strict-evidence"))
            provenance_tokens.append("strict-evidence")
        if final_transition:
            for token in ("coo-review", "human-review"):
                if token in tokens:
                    extra_refs.append(translate_gate_concept(token))
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
        if translate_gate_concept("human-review") in extra_refs:
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
    selected_adapter_ref: str,
    repo: Path,
    registry: Mapping[str, Any],
    gates: Sequence[Gate | str],
    write_scope: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    building_slug = _composition_slug(building_id)
    nodes = _unique_nodes((*graph.nodes, graph.terminal) if graph.terminal else graph.nodes)
    node_id_by_handle = _node_ids(nodes, building_slug)
    fan_in_sources = _fan_in_source_handles(graph.groups)
    default_reroute_budget = _materializer_constitutional_default_reroute_budget(repo)

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
        _reject_local_verdict_adapter(
            node,
            spec=spec,
            registry=registry,
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

    _auto_declare_chained_carry(
        graph,
        node_id_by_handle=node_id_by_handle,
        mutable_nodes_by_handle=mutable_nodes_by_handle,
    )

    lowered_groups = _lower_groups(
        graph.groups,
        edge_refs=edge_refs,
        building_slug=building_slug,
        node_id_by_handle=node_id_by_handle,
    )

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

    for node in lowered_nodes:
        _materializer_apply_constitutional_default_reroute_budget(
            node,
            default_budget=default_reroute_budget,
        )

    nodes_by_id = {str(node["node_id"]): node for node in lowered_nodes}
    lowered_edges = stamp_profile_gates(
        lowered_edges,
        nodes_by_id,
        gates,
        registry=registry,
        declared_by_origin=declared_by,
    )
    lowered_edges = _stamp_node_gate_sequence_policies(
        lowered_edges,
        nodes,
        mutable_nodes_by_handle=mutable_nodes_by_handle,
        edge_refs=edge_refs,
    )
    return lowered_nodes, lowered_edges, lowered_groups


def _stamp_node_gate_sequence_policies(
    edges: Sequence[Mapping[str, Any]],
    nodes: Sequence[BrickSpec],
    *,
    mutable_nodes_by_handle: Mapping[BrickSpec, dict[str, Any]],
    edge_refs: Mapping[EdgeSpec, str],
) -> list[Mapping[str, Any]]:
    outgoing_by_handle: dict[BrickSpec, list[str]] = defaultdict(list)
    for edge_spec, edge_ref in edge_refs.items():
        outgoing_by_handle[edge_spec.source].append(edge_ref)
    edge_by_ref = {str(edge.get("edge_ref", "")).strip(): dict(edge) for edge in edges}

    for spec in nodes:
        if not spec.gates:
            continue
        refs = outgoing_by_handle.get(spec, [])
        if len(refs) != 1:
            label = spec.alias or spec.kind
            raise ValueError(
                f"brick gates for {label!r} require exactly one outgoing completion edge; "
                f"observed {len(refs)}. Declare the gate_sequence_policy explicitly to disambiguate."
            )
        edge_ref = refs[0]
        edge = edge_by_ref.get(edge_ref)
        if edge is None:
            raise ValueError(f"brick gates for {spec.alias or spec.kind!r} did not resolve an outgoing edge")
        source_node = mutable_nodes_by_handle.get(spec)
        if source_node is not None and source_node.get("node_reroute_budget") is None:
            source_node["node_reroute_budget"] = 1
        edge_by_ref[edge_ref] = _merge_node_gate_sequence_policy(edge, spec.gates)

    return [edge_by_ref.get(str(edge.get("edge_ref", "")).strip(), dict(edge)) for edge in edges]


def _merge_node_gate_sequence_policy(
    edge: Mapping[str, Any],
    gate_tokens: Sequence[Gate | str],
) -> Mapping[str, Any]:
    requested_refs = [_node_gate_ref(token) for token in gate_tokens]
    if not requested_refs:
        return edge
    merged_gate_refs = _merge_gate_refs(edge.get("declared_gate_refs"), requested_refs)
    existing_policy = edge.get("gate_sequence_policy")
    if isinstance(existing_policy, Sequence) and not isinstance(existing_policy, (str, bytes)):
        existing_entries = [
            dict(item)
            for item in existing_policy
            if isinstance(item, Mapping) and str(item.get("gate_ref", "")).strip()
        ]
    elif existing_policy is None:
        existing_entries = []
    else:
        raise ValueError("gate_sequence_policy must be an ordered array")

    existing_refs = [
        str(entry.get("gate_ref", "")).strip()
        for entry in existing_entries
        if str(entry.get("gate_ref", "")).strip()
    ]
    sequence_refs = _ordered_node_gate_refs(
        merged_gate_refs,
        existing_refs,
        requested_refs,
    )
    entry_by_ref = {str(entry.get("gate_ref", "")).strip(): dict(entry) for entry in existing_entries}
    entries: list[Mapping[str, Any]] = []
    for index, gate_ref in enumerate(sequence_refs):
        next_gate_ref = sequence_refs[index + 1] if index + 1 < len(sequence_refs) else None
        entries.append(
            _node_gate_sequence_entry(
                gate_ref,
                next_gate_ref=next_gate_ref,
                existing=entry_by_ref.get(gate_ref),
            )
        )

    patched = dict(edge)
    patched["declared_gate_refs"] = merged_gate_refs
    patched["gate_sequence_policy"] = entries
    return patched


def _merge_gate_refs(raw_refs: Any, requested_refs: Sequence[str]) -> list[str]:
    refs = [
        str(ref).strip()
        for ref in (raw_refs if isinstance(raw_refs, Sequence) and not isinstance(raw_refs, (str, bytes)) else ())
        if str(ref).strip()
    ]
    if DEFAULT_LINK_GATE_REF not in refs:
        refs.insert(0, DEFAULT_LINK_GATE_REF)
    for gate_ref in requested_refs:
        if gate_ref not in refs:
            refs.append(gate_ref)
    return refs


def _ordered_node_gate_refs(
    merged_gate_refs: Sequence[str],
    existing_refs: Sequence[str],
    requested_refs: Sequence[str],
) -> list[str]:
    ordered: list[str] = [DEFAULT_LINK_GATE_REF]
    for gate_ref in merged_gate_refs:
        if gate_ref and gate_ref not in ordered:
            ordered.append(gate_ref)
    for gate_ref in existing_refs:
        if gate_ref not in ordered:
            ordered.append(gate_ref)
    for gate_ref in requested_refs:
        if gate_ref not in ordered:
            ordered.append(gate_ref)
    return ordered


def _node_gate_ref(token: Gate | str) -> str:
    value = _gate_value(token)
    if value not in {"coo-review", "human-review"}:
        raise ValueError("brick() gates accepts only human-review or coo-review for node completion edges")
    return translate_gate_concept(value)


def _node_gate_sequence_entry(
    gate_ref: str,
    *,
    next_gate_ref: str | None,
    existing: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if gate_ref == DEFAULT_LINK_GATE_REF:
        return {
            "gate_ref": DEFAULT_LINK_GATE_REF,
            "on_missing_required_facts": {
                "action": "reroute",
                "reason_refs": ["observation:default-transition-missing-required-facts"],
                "required_target_budget": True,
                "target_basis": "source_brick",
            },
            "on_sufficient": (
                {"action": "next", "next_gate_ref": next_gate_ref}
                if next_gate_ref
                else {"action": "forward"}
            ),
        }
    if gate_ref == translate_gate_concept("coo-review"):
        owner = "coo"
        reason_ref = "observation:coo-gate-missing-required-facts"
    elif gate_ref == translate_gate_concept("human-review"):
        owner = "caller-or-coo"
        reason_ref = "observation:human-gate-disposition-missing"
    else:
        registry_row = next((row for row in GATE_REGISTRY if row.ref == gate_ref), None)
        if registry_row is not None and registry_row.disposition == "plain":
            gate_name = gate_ref.split(":", 1)[-1].replace("_", "-")
            return {
                "gate_ref": gate_ref,
                "on_missing_required_facts": {
                    "action": "reroute",
                    "reason_refs": [f"observation:{gate_name}-gate-missing-required-facts"],
                    "required_target_budget": True,
                    "target_basis": "source_brick",
                },
                "on_sufficient": (
                    {"action": "next", "next_gate_ref": next_gate_ref}
                    if next_gate_ref
                    else {"action": "forward"}
                ),
            }
        if existing is None:
            raise ValueError(f"gate_sequence_policy cannot synthesize unsupported gate_ref: {gate_ref}")
        return dict(existing)
    return {
        "gate_ref": gate_ref,
        "on_missing_required_facts": {
            "action": "HOLD",
            "pending_target_basis": "target_brick",
            "reason_refs": [reason_ref],
            "required_disposition_owner": owner,
        },
        "on_sufficient": (
            {"action": "next", "next_gate_ref": next_gate_ref}
            if next_gate_ref
            else {"action": "forward"}
        ),
    }


def _auto_declare_chained_carry(
    graph: GraphSpec,
    *,
    node_id_by_handle: Mapping[BrickSpec, str],
    mutable_nodes_by_handle: Mapping[BrickSpec, dict[str, Any]],
) -> None:
    """AUTO-CARRY: turn a chained (adjacent) forward edge into a DECLARED data
    carry so the upstream node's step-output reaches the downstream prompt.

    A ``chain``/``build`` edge is a Link MOVEMENT edge (run order), not a data
    edge: by itself it carries no upstream output into the downstream worker's
    prompt. Here the EASY tier DERIVES the carry from the chain structure -- for
    each forward edge ``upstream -> downstream`` it declares the upstream node's
    step-output manifest ref as a ``source_fact`` on the downstream node, so the
    EXISTING carry executor (``run._adapter_source_fact_bodies`` /
    ``walker_kernel`` step-output match) delivers the upstream output downstream.
    The operator declares NOTHING.

    The manifest ref is generated by the SAME ``_step_output_manifest_ref`` the
    walker uses to label completed step-outputs, so the declared carry matches
    exactly what the walker carries at run time (attempt-1 forward flow).

    Boundaries respected (additive / idempotent; never breaks an explicit carry):
      * FAN-IN convergence targets are SKIPPED -- the walker already auto-carries
        every fan-in source's step-output to its convergence target (via
        ``fan_in_sources_by_target``); declaring it again is redundant.
      * An upstream node feeding a fan-in target as a SOURCE still gets its own
        upstream chained carry (it is a normal forward target of whatever
        precedes it); only the convergence node is skipped here.
      * A node that ALREADY declares a ``source_facts`` carrying this upstream
        manifest ref is left unchanged (the explicit operator/preset carry wins).
      * Reverse/non-forward edges carry nothing.
    """

    fan_in_target_handles = set(graph.fan_in_targets)
    for edge_spec in graph.edges:
        if edge_spec.movement != "forward":
            continue
        if edge_spec.target in fan_in_target_handles:
            continue
        upstream_node_id = node_id_by_handle.get(edge_spec.source)
        downstream_node = mutable_nodes_by_handle.get(edge_spec.target)
        if not upstream_node_id or downstream_node is None:
            continue
        carry_ref = _step_output_manifest_ref(upstream_node_id, 1)
        existing = downstream_node.get("source_facts")
        declared = list(existing) if isinstance(existing, list) else []
        if carry_ref in declared:
            continue
        declared.append(carry_ref)
        downstream_node["source_facts"] = declared


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
        node["required_return_shape"] = source_shape
    if spec.agent is not None:
        node["agent_object_ref"] = _prefixed_ref("agent-object", spec.agent.role)
    # Stamp EVERY declared casting dial generically (E2/§6 M15): loop the
    # single-source NODE_CASTING_FIELDS projection, node-casting overriding the
    # lane's, so a new dial (effort) flows from the builder onto the lowered node
    # with NO per-dial code. The bag values are already ref-prefixed. An omitted
    # dial is simply absent here; compose_building's resolver fills its default
    # (e.g. selected_reasoning_effort_ref=effort:default) so the assemble +
    # compose paths agree. Byte-identical to the prior adapter+model stamping for
    # those two dials.
    lane_casting = spec.agent.casting if spec.agent is not None else {}
    for field_name in NODE_CASTING_FIELDS:
        value = spec.casting.get(field_name) or (lane_casting.get(field_name) if lane_casting else None)
        if value:
            node[field_name] = value
    if spec.source_facts:
        node["source_facts"] = list(spec.source_facts)
    if spec.proof_obligations:
        node["proof_obligations"] = [dict(item) for item in spec.proof_obligations]
    template_write_need = isinstance(step_template, Mapping) and bool(step_template.get("write_need"))
    if spec.node_write_scope is not None and not template_write_need:
        raise ValueError("node_write_scope requires a step template with write_need")
    if spec.write and template_write_need:
        graph_scope = _validated_write_scope(write_scope)
        if spec.node_write_scope is not None:
            node_scope = _validated_write_scope(spec.node_write_scope)
            _validate_node_write_scope_subset(node_scope, graph_scope)
            node["write_scope"] = node_scope
        else:
            node["write_scope"] = graph_scope
        node["requires_brick_write_scope"] = True
    return node


def _reject_local_verdict_adapter(
    node: Mapping[str, Any],
    *,
    spec: BrickSpec,
    registry: Mapping[str, Any],
) -> None:
    effective_adapter_ref = str(node.get("selected_adapter_ref") or "").strip()
    if effective_adapter_ref != _LOCAL_ADAPTER_REF:
        return
    if not _is_verdict_bearing_node(node, registry=registry):
        return
    node_id = str(node.get("node_id", "")).strip() or spec.kind
    raise ValueError(f"verdict-bearing node {node_id} needs an explicit non-local adapter")


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
    node_id_by_handle: Mapping[BrickSpec, str],
) -> list[Mapping[str, Any]]:
    role_counts: Counter[str] = Counter()
    lowered: list[Mapping[str, Any]] = []
    for group in groups:
        role_counts[group.role] += 1
        member_refs = [edge_refs[member] for member in group.members]
        group_row = {
            "group_id": f"group-{building_slug}-{group.role.replace('_', '-')}-{role_counts[group.role]}",
            "group_role": group.role,
            "member_ref_kind": "link_edge",
            "member_refs": member_refs,
        }
        if group.sibling_independence:
            group_row["sibling_independence"] = list(
                _resolved_sibling_independence_refs(
                    group.sibling_independence,
                    sources=tuple(member.source for member in group.members),
                    node_id_by_handle=node_id_by_handle,
                )
            )
        lowered.append(group_row)
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
        if not shape:
            raise ValueError(f"fan-in source missing required_return_shape: {source_id}")

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
    if value is None:
        return derived_worktree_write_scope()
    if not isinstance(value, Mapping):
        raise ValueError("write_scope must be a mapping")
    allowed = value.get("allowed_paths")
    forbidden = value.get("forbidden_paths")
    if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes)):
        raise ValueError("write_scope.allowed_paths must be a non-empty array")
    if not [str(path).strip() for path in allowed if str(path).strip()]:
        raise ValueError("write_scope.allowed_paths must be non-empty")
    if not isinstance(forbidden, Sequence) or isinstance(forbidden, (str, bytes)):
        raise ValueError("write_scope.forbidden_paths must be an array")
    allowed_paths = [str(path).strip() for path in allowed if str(path).strip()]
    forbidden_paths = [str(path).strip() for path in forbidden if str(path).strip()]
    for path in (*allowed_paths, *forbidden_paths):
        _normalized_write_path(path)
    return {
        "allowed_paths": allowed_paths,
        "forbidden_paths": forbidden_paths,
    }


def _validate_node_write_scope_subset(
    node_scope: Mapping[str, Any],
    graph_scope: Mapping[str, Any],
) -> None:
    graph_allowed = tuple(str(path).strip() for path in graph_scope.get("allowed_paths", ()) if str(path).strip())
    graph_forbidden = tuple(str(path).strip() for path in graph_scope.get("forbidden_paths", ()) if str(path).strip())
    node_allowed = tuple(str(path).strip() for path in node_scope.get("allowed_paths", ()) if str(path).strip())
    node_forbidden = tuple(str(path).strip() for path in node_scope.get("forbidden_paths", ()) if str(path).strip())
    for path in node_allowed:
        if not any(_write_path_covered_by(path, allowed) for allowed in graph_allowed):
            raise ValueError("node_write_scope.allowed_paths must be a proven subset of assemble() write_scope")
    for path in graph_forbidden:
        if path not in node_forbidden:
            raise ValueError("node_write_scope.forbidden_paths must preserve assemble() write_scope forbidden_paths")


def _write_path_covered_by(path: str, allowed: str) -> bool:
    clean_path = _normalized_write_path(path)
    clean_allowed = _normalized_write_path(allowed)
    if clean_allowed in {".", "**", "./**"}:
        return True
    if clean_path == clean_allowed:
        return True
    if clean_allowed.endswith("/**"):
        prefix = clean_allowed[:-3].rstrip("/")
        return clean_path == prefix or clean_path.startswith(prefix + "/")
    return False


def _normalized_write_path(path: str) -> str:
    text = str(path).strip().replace("\\", "/")
    if text.startswith("/"):
        raise ValueError("write_scope paths must be repo-relative")
    while text.startswith("./"):
        text = text[2:]
    parts = tuple(part for part in text.rstrip("/").split("/") if part and part != ".")
    if any(part == ".." for part in parts):
        raise ValueError("write_scope paths must not escape the repo root")
    return "/".join(parts) or "."


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


# _optional_bare_or_ref moved to the AGENT axis (agent/spec.py) at E2/S1 with the
# casting authoring it serves (its only caller was ``_build_casting_bag``). The
# coercers below (``_bare_token``/``_optional_bare_token``/``_optional_text``/
# ``_non_empty_text``/``_prefixed_ref``) STAY: the retained graph-wiring tier uses
# them, and they are duplicated into the axis files so an axis never imports here.
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
    "Fan",
    "Gate",
    "GraphSpec",
    "agent",
    "assemble",
    "back",
    "brick",
    "build",
    "chain",
    "converge",
    "edge",
    "fan",
    "fire",
    "fan_in",
    "fan_out",
    "hold",
    "lower_route",
    "persist_proposed_building_graph",
    "reroute",
    "stamp_profile_gates",
]
