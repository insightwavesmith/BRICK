"""compose_building graph plan assembler (composition concern submodule).

The compose engine -- ``compose_building`` plus the private node/edge/gate
assembly helpers it alone uses to lay out a caller/COO-declared graph Building
Plan (the F core).

Sibling helpers (``_chain_preset_requires_graph``,
``_chain_preset_requires_fan_in_groups``, ``_chain_preset_steps`` in
composition_common; ``_composition_brick_template_refs``,
``_composition_brick_spec_refs`` in composition_intent) are imported LAZILY
inside the functions that use them to avoid an import cycle.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.brick.spec import derived_worktree_write_scope
from brick_protocol.link.gate import HUMAN_DISPOSITION_GATE_REFS
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.support.operator.building_operation_common import (
    COMPACT_LINK_GATE_TOKENS,
    DEFAULT_LINK_GATE_REF,
    REPO_ROOT,
    _clean_text,
    _mapping_value,
    _text_sequence,
)
from brick_protocol.support.operator.primitives import NODE_CASTING_FIELDS
from brick_protocol.support.recording.contracts import require_positive_int
from brick_protocol.support.operator.plan_rendering import (
    RETIRED_STEP_TEMPLATE_REFS,
    _clean_selected_adapter_ref,
    _is_caller_or_coo_declaration,
    _is_verdict_bearing_node,
    _load_shape_registry,
    _parse_compact_link_expression,
    _resolve_agent_for_need,
    _resolve_casting_selection,
)
from brick_protocol.support.operator.composition_problem import (
    CompositionError,
    CompositionProblem,
)
from brick_protocol.support.operator.composition_common import (
    _composition_optional_text,
    _composition_slug,
)


def _sequence_value(label: str, value: Any) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{label} must be a sequence")
    return value


from brick_protocol.support.operator.composition_kinds import _unknown_kind_hint
from brick_protocol.support.operator.composition_route_policy import (
    _composition_direct_caller_provenance,
    _composition_node_reroute_budgets,
    _composition_route_policy_provenance,
)
from brick_protocol.support.operator.composition_graph_validate import (
    _composition_author_required_return_shape,
    _composition_edge_records_with_gate_sequence_policy,
    _composition_fan_in_target_steps,
    _composition_gate_sequence_policy_profile_problems,
    _composition_hard_graph_contract_problems,
    _composition_validator_problems,
)


def compose_building(
    nodes: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    selected_shape_ref: str = "",  # U5/D5: optional tag (parity with the linear path); blank -> no shape tag
    declared_by: str,
    groups: Sequence[Mapping[str, Any]] = (),
    chain_preset_ref: str = "",
    plan_ref: str = "",
    building_id: str = "",
    selected_adapter_ref: str = "adapter:local",
    selected_model_ref: str = "model:default",
    transition_concern_adoption: str = "",
    expansion_budget: Any | None = None,
    expansion_node_budgets: Mapping[str, Any] | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Assemble a caller/COO-declared graph Building Plan from node choices.

    This is support mechanics only. The caller/COO declares the selected shape,
    each node's step template / Brick fields, and each Link edge / gate token.
    The helper lays those declarations out as a Brick-owned ``plan_shape:
    graph`` plan, then reuses the existing graph and Link validators.
    """

    # Lazy sibling imports (cycle-avoid): these helpers live in composition_common
    # and composition_intent (shared with render_declared_step_template_plan), so
    # they are imported in-function rather than at module top level.
    from brick_protocol.support.operator.composition_common import (
        _chain_preset_requires_fan_in_groups,
        _chain_preset_requires_graph,
    )
    from brick_protocol.support.operator.composition_intent import (
        _composition_brick_spec_refs,
        _composition_brick_template_refs,
    )

    repo = Path(repo_root).resolve()
    registry = _load_shape_registry(repo)
    problems: list[CompositionProblem] = []

    # U5/D5: selected_shape_ref is now an OPTIONAL recorded tag, not a constraint
    # (parity with the linear path). The composition-level shape membership gate
    # was removed (shapes.yaml is non-load-bearing; graph structure comes from the
    # nodes/edges arguments). shape_ref is still extracted here for the plan tag
    # and for passing to the chain-preset helper. The registry stays loaded for
    # step_templates / chain_presets resolution. A present-but-non-string shape is a
    # MALFORMED declaration: fail closed (parity with the linear renderer's TypeError)
    # rather than silently erase it to a null tag.
    if selected_shape_ref is not None and not isinstance(selected_shape_ref, str):
        problems.append(
            CompositionProblem(
                "bad_declaration",
                "__composition__",
                "selected_shape_ref must be text when provided",
            )
        )
    shape_ref = _composition_optional_text(selected_shape_ref)
    declared_by_text = _composition_optional_text(declared_by)
    if not declared_by_text or not _is_caller_or_coo_declaration(declared_by_text):
        problems.append(
            CompositionProblem(
                "bad_declaration",
                "__composition__",
                "selection_rule: caller_or_coo_declared_only",
            )
        )
    plan_selected_adapter_ref = _clean_selected_adapter_ref(
        "selected_adapter_ref",
        selected_adapter_ref,
    )
    plan_selected_model_ref = _clean_text(
        "selected_model_ref",
        selected_model_ref,
    )

    (
        selected_chain_preset_ref,
        canonical_chain_preset_ref,
        chain_preset,
    ) = _composition_chain_preset(
        registry,
        chain_preset_ref,
        problems=problems,
    )

    node_items = _composition_node_items(nodes)
    if not node_items:
        problems.append(
            CompositionProblem(
                "empty_composition",
                "__composition__",
                "composition must declare at least one node",
            )
        )

    admitted_agent_refs = _composition_agent_object_refs(repo)
    step_templates = registry["step_templates"]
    node_records: list[dict[str, Any]] = []
    step_by_endpoint: dict[str, str] = {}
    brick_by_step: dict[str, str] = {}
    seen_node_ids: set[str] = set()
    seen_brick_refs: set[str] = set()
    for index, raw_node in enumerate(node_items):
        label = f"nodes[{index}]"
        if not isinstance(raw_node, Mapping):
            problems.append(
                CompositionProblem(
                    "missing_brick_fields",
                    label,
                    "node declaration must be an object",
                )
            )
            continue
        node_id = _composition_node_id(index, raw_node)
        # U5/D5: node-level shape_ref membership gate removed (shape is a pure
        # optional tag now; it never drove graph structure). node shape_ref is not
        # emitted into the plan, so the extraction is dropped as well.
        if node_id in seen_node_ids:
            problems.append(
                CompositionProblem(
                    "duplicate_brick_id",
                    node_id,
                    "node_id must be unique",
                )
            )
        seen_node_ids.add(node_id)
        step_template_ref = _composition_optional_text(raw_node.get("step_template_ref"))
        step_template = (
            step_templates.get(step_template_ref)
            if step_template_ref is not None
            else None
        )
        brick_row = _composition_brick_row(
            index, raw_node, node_id, problems, step_template
        )
        brick_ref = str(brick_row.get("brick_instance_ref") or "")
        if brick_ref in seen_brick_refs:
            problems.append(
                CompositionProblem(
                    "duplicate_brick_id",
                    node_id,
                    f"brick_instance_ref appears more than once: {brick_ref}",
                )
            )
        if brick_ref:
            seen_brick_refs.add(brick_ref)

        if step_template is None:
            if not step_template_ref:
                agent_object_ref = _composition_optional_text(raw_node.get("agent_object_ref")) or ""
            elif step_template_ref in RETIRED_STEP_TEMPLATE_REFS:
                # WAVE-B rename (0610): the retired step-template name rejects
                # LOUDLY on the graph path too, naming the canonical
                # replacement (parity with the linear + chain-preset paths);
                # it never falls through to the generic not-in-catalog error.
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        f"step_template_ref {step_template_ref} is retired: "
                        f"use {RETIRED_STEP_TEMPLATE_REFS[step_template_ref]}",
                    )
                )
                agent_object_ref = _composition_optional_text(raw_node.get("agent_object_ref")) or ""
            else:
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        f"step_template_ref {step_template_ref} must resolve in the "
                        f"Brick template catalog"
                        f"{_unknown_kind_hint(step_template_ref, registry)}",
                    )
                )
                agent_object_ref = _composition_optional_text(raw_node.get("agent_object_ref")) or ""
        else:
            _validate_composition_brick_spec_ref(raw_node, step_template, node_id, problems)
            # The template's agent_object_ref is the NEED<->CAPABILITY match
            # (default_agent hint applied at registry build). A node MAY override
            # it, but only with an agent that itself satisfies this kind's NEED
            # (role_need/write_need carried on the registry row); an override that
            # violates the NEED is rejected. No override = the matched default.
            agent_object_ref = step_template["agent_object_ref"]
            declared_agent_ref = _composition_optional_text(raw_node.get("agent_object_ref"))
            if declared_agent_ref and declared_agent_ref != agent_object_ref:
                if step_template.get("step_template_ref") == "building-step-template:development":
                    # development is CTO-only; role_need=leader has 5 candidates so a
                    # same-NEED override would divert the CTO assignment. Block it
                    # (parity with the linear path; codex U2-4 P2); keep cto-lead default.
                    problems.append(
                        CompositionProblem(
                            "unknown_step_template/agent",
                            node_id,
                            "development is CTO-only; agent override not allowed",
                        )
                    )
                else:
                    role_need = step_template.get("role_need")
                    write_need = step_template.get("write_need")
                    if not isinstance(role_need, str) or not role_need:
                        problems.append(
                            CompositionProblem(
                                "unknown_step_template/agent",
                                node_id,
                                "step template is missing role_need; cannot validate agent override",
                            )
                        )
                    else:
                        try:
                            agent_object_ref = _resolve_agent_for_need(
                                repo,
                                role_need,
                                bool(write_need),
                                declared_override=declared_agent_ref,
                            )
                        except ValueError as exc:
                            problems.append(
                                CompositionProblem(
                                    "unknown_step_template/agent",
                                    node_id,
                                    f"agent_object_ref override rejected: {exc}",
                                )
                            )
        if agent_object_ref and agent_object_ref not in admitted_agent_refs:
            problems.append(
                CompositionProblem(
                    "unknown_step_template/agent",
                    node_id,
                    f"agent_object_ref is not admitted: {agent_object_ref}",
                )
            )
        # Every casting dial's resolved ``selected_<base>`` value, keyed by the
        # SAME ``NODE_CASTING_FIELDS`` projection the node carries. Default to None
        # (absent agent / resolution error) for each field so the node always
        # carries the full key set. E2/S6★: the OUTPUT is generic over
        # CASTING_FIELDS just like the resolver INPUT, so a new dial (effort) is
        # stamped here with no per-dial code -- selected_reasoning_effort_ref now
        # rides along the same way selected_adapter_ref/selected_model_ref do.
        step_casting_selection: dict[str, str | None] = {
            field_name: None for field_name in NODE_CASTING_FIELDS
        }
        if agent_object_ref and agent_object_ref in admitted_agent_refs:
            try:
                step_casting_selection = _resolve_casting_selection(
                    repo,
                    raw_step=raw_node,
                    agent_object_ref=agent_object_ref,
                    plan_casting={
                        "selected_adapter_ref": plan_selected_adapter_ref,
                        "selected_model_ref": plan_selected_model_ref,
                    },
                    label=node_id,
                    is_verdict_bearing_node=_is_verdict_bearing_node(
                        raw_node,
                        step_template=step_template,
                    ),
                )
            except ValueError as exc:
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        str(exc),
                    )
                )

        node_record = {
            "node_id": node_id,
            "step_ref": _composition_step_ref(raw_node, node_id),
            "step_template_ref": step_template_ref or "",
            "brick_ref": brick_ref,
            "brick_row": brick_row,
            "agent_object_ref": agent_object_ref,
            "raw": raw_node,
            "requires_review_gate": bool(
                raw_node.get("requires_review_gate")
                or raw_node.get("review_gate_required")
            ),
            "completion_edge_ref": _composition_optional_text(
                raw_node.get("completion_edge_ref")
            ),
            "node_reroute_budget": raw_node.get("node_reroute_budget", raw_node.get("reroute_budget")),
            # FAIL-CLOSED ripple (Smith ruling): a route-policy value declared
            # DIRECTLY on the node passed to compose_building (no provenance) IS a
            # per-Building HUMAN declaration by the caller/COO -- stamp "per-building"
            # EXPLICITLY here so the value carries its origin. The resolver no longer
            # auto-labels absent provenance; absent must be made explicit at this
            # legitimate direct-caller intake, never defaulted inside the resolver.
            "node_reroute_budget_provenance": _composition_direct_caller_provenance(
                value=raw_node.get("node_reroute_budget", raw_node.get("reroute_budget")),
                provenance=raw_node.get("node_reroute_budget_provenance"),
            ),
            "closure_transition_target_policy": raw_node.get(
                "closure_transition_target_policy"
            ),
            "closure_transition_target_policy_provenance": _composition_direct_caller_provenance(
                value=raw_node.get("closure_transition_target_policy"),
                provenance=raw_node.get("closure_transition_target_policy_provenance"),
            ),
            # Stamp EVERY resolved casting dial generically (E2/S6★): loop the
            # single-source NODE_CASTING_FIELDS projection rather than naming
            # selected_adapter_ref/selected_model_ref by hand, so a new casting
            # dial (effort) lands on the node with no edit here.
            **{
                field_name: step_casting_selection.get(field_name)
                for field_name in NODE_CASTING_FIELDS
            },
        }
        node_records.append(node_record)
        for endpoint in (node_id, node_record["step_ref"], brick_ref):
            if endpoint:
                step_by_endpoint[endpoint] = node_record["step_ref"]
        if brick_ref:
            brick_by_step[node_record["step_ref"]] = brick_ref

    edge_records: list[dict[str, Any]] = []
    outgoing_by_step: dict[str, list[str]] = {}
    review_gate_seen_by_step: dict[str, bool] = {}
    for index, raw_edge in enumerate(edges if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)) else ()):
        label = f"edges[{index}]"
        if not isinstance(raw_edge, Mapping):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    label,
                    "edge declaration must be an object",
                )
            )
            continue
        raw_source = _composition_endpoint(raw_edge, "source")
        raw_target = _composition_endpoint(raw_edge, "target")
        source_step = step_by_endpoint.get(raw_source or "")
        target_step = step_by_endpoint.get(raw_target or "")
        node_id = source_step or raw_source or label
        if source_step is None:
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    node_id,
                    f"edge source does not resolve: {raw_source or '(blank)'}",
                )
            )
        if target_step is None and not _composition_terminal_target(raw_target):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    node_id,
                    f"edge target does not resolve: {raw_target or '(blank)'}",
                )
            )
        if source_step and target_step and source_step == target_step:
            problems.append(
                CompositionProblem(
                    "cycle/self_loop",
                    source_step,
                    "edge source and target resolve to the same node",
                )
            )

        target_ref = (
            brick_by_step[target_step]
            if target_step is not None
            else _composition_optional_text(raw_target) or ""
        )
        declared_gate_refs = _composition_declared_gate_refs(
            index,
            raw_edge,
            target_ref,
            source_step or node_id,
            problems,
        )
        movement = _composition_edge_movement(index, raw_edge, problems)
        if source_step:
            outgoing_by_step.setdefault(source_step, []).append(
                _composition_edge_ref(index, raw_edge, source_step, target_step or target_ref)
            )
            if any(ref in HUMAN_DISPOSITION_GATE_REFS for ref in declared_gate_refs):
                review_gate_seen_by_step[source_step] = True
        edge_records.append(
            {
                "edge_ref": _composition_edge_ref(index, raw_edge, source_step or label, target_step or target_ref),
                "source_step_ref": source_step or "",
                "target_step_ref": target_step or "",
                "target_ref": target_ref,
                "movement": movement,
                "declared_gate_refs": declared_gate_refs,
                "raw": raw_edge,
            }
        )

    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        problems.append(
            CompositionProblem(
                "unknown_endpoint",
                "__composition__",
                "edges must be an array of declared Link edges",
            )
        )

    for node_record in node_records:
        step_ref = node_record["step_ref"]
        if not outgoing_by_step.get(step_ref):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    step_ref,
                    "node must declare at least one outgoing Link edge or terminal boundary edge",
                )
            )
        if node_record["requires_review_gate"] and not review_gate_seen_by_step.get(step_ref):
            problems.append(
                CompositionProblem(
                    "missing_review_gate",
                    step_ref,
                    "node declares requires_review_gate but no outgoing human/coo gate",
                )
            )

    if groups and (
        not isinstance(groups, Sequence) or isinstance(groups, (str, bytes))
    ):
        problems.append(
            CompositionProblem(
                "execution_order/groups coherence",
                "__composition__",
                "groups must be an array of declared graph groups",
            )
        )

    if chain_preset is not None:
        expected_step_template_refs = _chain_preset_step_template_refs(chain_preset)
        observed_step_template_refs = [
            record["step_template_ref"]
            for record in node_records
            if record.get("step_template_ref")
        ]
        if expected_step_template_refs and Counter(
            expected_step_template_refs
        ) != Counter(observed_step_template_refs):
            problems.append(
                CompositionProblem(
                    "chain_preset_step_mismatch",
                    selected_chain_preset_ref or "__composition__",
                    "declared graph nodes must match the selected chain preset step templates",
                )
            )
        if _chain_preset_requires_fan_in_groups(chain_preset):
            group_roles = (
                {
                    str(group.get("group_role", "")).strip()
                    for group in groups
                    if isinstance(group, Mapping)
                }
                if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes))
                else set()
            )
            missing_roles = [role for role in ("fan_out", "fan_in") if role not in group_roles]
            if missing_roles:
                problems.append(
                    CompositionProblem(
                        "chain_preset_graph_groups_missing",
                        selected_chain_preset_ref or "__composition__",
                        "graph chain preset requires declared fan_out and fan_in groups",
                    )
                )
            problems.extend(
                _composition_gate_sequence_policy_profile_problems(
                    chain_preset=chain_preset,
                    node_records=node_records,
                    edge_records=edge_records,
                )
            )
            edge_records = list(
                _composition_edge_records_with_gate_sequence_policy(
                    chain_preset=chain_preset,
                    node_records=node_records,
                    edge_records=edge_records,
                )
            )

    for node_record in node_records:
        step_ref = node_record["step_ref"]
        if len(outgoing_by_step.get(step_ref, [])) > 1 and not node_record.get(
            "completion_edge_ref"
        ):
            problems.append(
                CompositionProblem(
                    "missing_completion_edge_ref",
                    step_ref,
                    "fan-out nodes must declare completion_edge_ref; support must not choose the first outgoing edge",
                )
            )

    # Fan-in SOURCES now keep the same templated Brick return shape as every other
    # templated node: required_return_shape materializes from
    # brick_protocol/brick/templates/bricks/<kind>/return.yaml. Support must not shrink that Brick
    # contract to control what Link carries; the carry seam uses the separate
    # carries_forward_fields subset stamped on the Brick row. The legacy validator
    # path still knows how to skip its old fan-in-source transition-concern guard via
    # shape_omitted_steps, so reuse that suppression set for source-position rows
    # whose Brick shape is intentionally template-owned rather than author-restated.
    fan_in_source_template_shape_steps: set[str] = set()
    fan_in_source_policy_steps: list[str] = []
    if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes)) and groups:
        records_by_step = {str(record.get("step_ref")): record for record in node_records}
        fan_in_targets = _composition_fan_in_target_steps(edge_records, groups)
        fan_in_source_steps: list[str] = []
        for _target_step_ref, source_step_refs in fan_in_targets.items():
            fan_in_source_steps.extend(source_step_refs)
        fan_in_source_policy_steps = list(dict.fromkeys(fan_in_source_steps))
        for step_ref in dict.fromkeys(fan_in_source_steps):
            record = records_by_step.get(step_ref)
            if record is None:
                continue
            if not _composition_author_required_return_shape(record):
                fan_in_source_template_shape_steps.add(step_ref)

    if chain_preset is not None and _chain_preset_requires_fan_in_groups(chain_preset):
        problems.extend(
            _composition_hard_graph_contract_problems(
                node_records=node_records,
                edge_records=edge_records,
                groups=groups,
                # Fan-in sources whose shape came from the Brick template keep that
                # full Brick-owned required_return_shape. Suppress only the old
                # support-position rule that treated transition_concern_evidence as
                # Link carry control; carries_forward_fields remains the carry filter.
                shape_omitted_steps=fan_in_source_template_shape_steps,
                transition_concern_adoption=transition_concern_adoption,
            )
        )

    if problems:
        raise CompositionError(problems)

    brick_steps: list[Mapping[str, Any]] = []
    for node_record in node_records:
        step_ref = node_record["step_ref"]
        completion_edge_ref = node_record["completion_edge_ref"] or outgoing_by_step[step_ref][0]
        brick_step: dict[str, Any] = {
            "step_ref": step_ref,
            "completion_edge_ref": completion_edge_ref,
            "rows": [
                node_record["brick_row"],
                {
                    "axis": "Agent",
                    "row_ref": f"agent-row:{step_ref}",
                    "agent_object_ref": node_record["agent_object_ref"],
                },
            ],
        }
        # Stamp EVERY resolved casting dial onto the brick_step generically
        # (E2/S6★): loop the single-source ``NODE_CASTING_FIELDS`` projection the
        # node_record already carries rather than hand-naming
        # selected_adapter_ref/selected_model_ref. A None value defers to the
        # plan-level casting (omitted from the step), byte-identical to the prior
        # two-field emission; a NEW casting dial (effort) now reaches brick_steps
        # with no edit here, so the assemble + compose paths agree.
        for field_name in NODE_CASTING_FIELDS:
            value = node_record.get(field_name)
            if value is not None:
                brick_step[field_name] = _clean_text(
                    f"{step_ref}.{field_name}",
                    value,
                )
        if node_record.get("step_template_ref"):
            brick_step["step_template_ref"] = _clean_text(
                f"{step_ref}.step_template_ref",
                node_record["step_template_ref"],
            )
        brick_steps.append(brick_step)

    link_edges = [
        _composition_link_edge(record)
        for record in edge_records
    ]
    expanded_step_template_refs = [
        record["step_template_ref"]
        for record in node_records
        if record.get("step_template_ref")
    ]
    plan: dict[str, Any] = {
        "plan_ref": plan_ref.strip() if plan_ref else "building-plan:composed-graph",
        "owner_axis": "Brick",
        "building_id": building_id.strip() if building_id else "composed-graph",
        "plan_shape": "graph",
        "composition_mode": "caller_or_coo_declared_graph_composition",
        "selected_adapter_ref": plan_selected_adapter_ref,
        "selected_model_ref": plan_selected_model_ref,
        "selected_shape_ref": shape_ref,
        "declared_by": declared_by_text,
        "selection_rule": "caller_or_coo_declared_only",
        "proof_limits": [
            "support evidence only",
            "compose_building assembles caller / COO declared node and edge choices only",
            "not automatic shape selection",
            "not automatic Agent selection",
            "not automatic gate selection",
            "not support-chosen target",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of selected shape",
            "future Building run correctness",
            "future Agent or provider quality",
        ],
        "execution_order": [record["step_ref"] for record in node_records],
        "brick_steps": brick_steps,
        "link_edges": link_edges,
        "preset_expansion": {
            "selected_shape_ref": shape_ref,
            "expanded_step_template_refs": expanded_step_template_refs,
            "expanded_brick_spec_refs": list(
                _composition_brick_spec_refs(registry, expanded_step_template_refs)
            ),
            "expanded_brick_template_refs": list(
                _composition_brick_template_refs(registry, expanded_step_template_refs)
            ),
            "agent_object_refs": [
                record["agent_object_ref"]
                for record in node_records
                if record.get("agent_object_ref")
            ],
            "selection_rule": "caller_or_coo_declared_only",
            "proof_limits": [
                "support records caller / COO declared graph composition only",
                "not automatic preset selection",
                "not automatic shape selection",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "semantic fitness of selected shape",
                "selected preset ref was not declared unless separately present",
            ],
        },
    }
    if selected_chain_preset_ref:
        plan["chain_preset_ref"] = selected_chain_preset_ref
        plan["preset_expansion"]["chain_preset_ref"] = selected_chain_preset_ref
        plan["preset_expansion"]["canonical_chain_preset_ref"] = canonical_chain_preset_ref
        if canonical_chain_preset_ref != selected_chain_preset_ref:
            plan["preset_expansion"]["compat_chain_preset_ref"] = selected_chain_preset_ref
        if chain_preset is not None:
            plan["preset_expansion"]["chain_preset_requires_graph"] = (
                _chain_preset_requires_graph(chain_preset)
            )
    if groups:
        plan["groups"] = [dict(group) for group in groups]
    if fan_in_source_policy_steps:
        plan["fan_in_source_transition_concern_adoption"] = {
            "policy": "advisory",
            "scope": "fan_in_sources",
            "source_step_refs": list(fan_in_source_policy_steps),
            "proof_limits": [
                "declared Link non-adoption policy for fan-in source Agent evidence",
                "fan-in closure remains the Link-facing transition concern source",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "semantic correctness of future source-lane concern evidence",
            ],
        }
    node_reroute_budgets = _composition_node_reroute_budgets(node_records)
    if node_reroute_budgets:
        plan["node_reroute_budgets"] = node_reroute_budgets
    route_policy_provenance = _composition_route_policy_provenance(node_records)
    if route_policy_provenance:
        plan["route_policy_provenance"] = route_policy_provenance
    if transition_concern_adoption:
        plan["transition_concern_adoption"] = transition_concern_adoption
    if expansion_budget is not None:
        try:
            plan["expansion_budget"] = require_positive_int(
                expansion_budget,
                "expansion_budget",
                allow_decimal_text=False,
            )
        except ValueError as exc:
            problems.append(
                CompositionProblem(
                    "invalid_expansion_budget",
                    "__composition__",
                    str(exc),
                )
            )
    if expansion_node_budgets is not None:
        if not isinstance(expansion_node_budgets, Mapping):
            problems.append(
                CompositionProblem(
                    "invalid_expansion_node_budgets",
                    "__composition__",
                    "expansion_node_budgets must be a mapping when supplied",
                )
            )
        else:
            plan["declared_expansion_node_budgets"] = dict(expansion_node_budgets)
    if problems:
        raise CompositionError(problems)

    post_problems = _composition_validator_problems(plan, repo)
    if post_problems:
        raise CompositionError(post_problems)
    return plan


def _composition_chain_preset(
    registry: Mapping[str, Any],
    raw_chain_preset_ref: Any,
    *,
    problems: list[CompositionProblem],
) -> tuple[str, str, Mapping[str, Any] | None]:
    chain_preset_ref = _composition_optional_text(raw_chain_preset_ref)
    if raw_chain_preset_ref not in (None, "") and chain_preset_ref is None:
        problems.append(
            CompositionProblem(
                "unknown_chain_preset",
                "__composition__",
                "chain_preset_ref must be non-empty text when supplied",
            )
        )
        return "", "", None
    if not chain_preset_ref:
        return "", "", None
    chain_presets = registry.get("chain_presets", {})
    chain_preset_aliases = registry.get("chain_preset_aliases", {})
    if not isinstance(chain_presets, Mapping):
        return chain_preset_ref, chain_preset_ref, None
    preset = chain_presets.get(chain_preset_ref)
    if not isinstance(preset, Mapping):
        problems.append(
            CompositionProblem(
                "unknown_chain_preset",
                chain_preset_ref,
                "chain_preset_ref must be present in the Brick template catalog",
            )
        )
        return chain_preset_ref, chain_preset_ref, None
    canonical_ref = chain_preset_ref
    if isinstance(chain_preset_aliases, Mapping):
        alias_target = chain_preset_aliases.get(chain_preset_ref)
        if isinstance(alias_target, str) and alias_target.strip():
            canonical_ref = alias_target.strip()
    # U5/D5: the preset<->caller selected_shape_ref match constraint was removed
    # (shape is now an optional tag, not authority; parity with the linear path).
    # Preset existence, alias/canonical resolution, and the graph requirement
    # (enforced by the caller via _chain_preset_requires_graph) all remain.
    return chain_preset_ref, canonical_ref, preset


def _chain_preset_step_template_refs(preset: Mapping[str, Any]) -> tuple[str, ...]:
    # Lazy sibling import (cycle-avoid): _chain_preset_steps lives in
    # composition_common.
    from brick_protocol.support.operator.composition_common import _chain_preset_steps

    refs: list[str] = []
    for raw_step in _chain_preset_steps(preset):
        ref = raw_step.get("step_template_ref")
        if isinstance(ref, str) and ref.strip():
            refs.append(ref.strip())
    return tuple(refs)


def _validate_composition_brick_spec_ref(
    raw_node: Mapping[str, Any],
    step_template: Mapping[str, Any],
    node_id: str,
    problems: list[CompositionProblem],
) -> None:
    supplied = raw_node.get("brick_spec_ref")
    if supplied is None:
        return
    declared = _composition_optional_text(supplied)
    expected = step_template.get("brick_spec_ref")
    if declared != expected:
        problems.append(
            CompositionProblem(
                "unknown_step_template/agent",
                node_id,
                "brick_spec_ref must match the registered single-Brick spec",
            )
        )


def _composition_node_items(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        items: list[Any] = []
        for key, raw_node in value.items():
            if isinstance(raw_node, Mapping):
                merged = dict(raw_node)
                merged.setdefault("node_id", str(key))
                items.append(merged)
            else:
                items.append(raw_node)
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return ()


def _composition_node_id(index: int, raw_node: Mapping[str, Any]) -> str:
    for key in ("node_id", "brick_id", "step_ref"):
        value = _composition_optional_text(raw_node.get(key))
        if value:
            return value
    return f"nodes[{index}]"


def _composition_step_ref(raw_node: Mapping[str, Any], node_id: str) -> str:
    return _composition_optional_text(raw_node.get("step_ref")) or node_id


def _composition_brick_row(
    index: int,
    raw_node: Mapping[str, Any],
    node_id: str,
    problems: list[CompositionProblem],
    step_template: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    raw_brick = raw_node.get("brick")
    brick = raw_brick if isinstance(raw_brick, Mapping) else raw_node
    # Builder auto-fill: a node that names a resolvable step_template need only
    # supply work_statement. comparison_rule then defaults to the template's
    # brick_contract and required_return_shape to the standard base shape; an
    # author-supplied value still overrides (Smith: override-allowed). Without a
    # step_template all three stay author-required (unchanged behavior).
    template_comparison_rule = (
        _composition_optional_text(step_template.get("brick_contract"))
        if isinstance(step_template, Mapping)
        else None
    )
    # The kind's REAL declared return shape, derived from its primary
    # return_template (carried on the step_template registry row by
    # plan_rendering). When a node omits required_return_shape and a step_template
    # resolves, this is the default the gate then requires -- the kind's real
    # fields, not the 2-field literal. Author-supplied value still wins below.
    template_required_return_shape = (
        _composition_optional_text(step_template.get("required_return_shape"))
        if isinstance(step_template, Mapping)
        else None
    )
    if template_comparison_rule:
        required_author_fields = ("work_statement",)
    else:
        required_author_fields = (
            "work_statement",
            "comparison_rule",
            "required_return_shape",
        )
    missing = [
        field
        for field in required_author_fields
        if not _composition_optional_text(brick.get(field))
    ]
    if missing:
        problems.append(
            CompositionProblem(
                "missing_brick_fields",
                node_id,
                "missing Brick field(s): " + ", ".join(missing),
            )
        )
    step_ref = _composition_step_ref(raw_node, node_id)
    brick_ref = _composition_optional_text(brick.get("brick_instance_ref"))
    if not brick_ref:
        brick_ref = _composition_default_brick_ref(node_id)
    row: dict[str, Any] = {
        "axis": "Brick",
        "row_ref": _composition_optional_text(brick.get("row_ref")) or f"brick-row:{step_ref}",
        "brick_work_ref": _composition_optional_text(brick.get("brick_work_ref")) or f"work:{_composition_slug(node_id)}",
        "brick_instance_ref": brick_ref,
        "work_statement": _composition_optional_text(brick.get("work_statement")) or f"missing work statement for {node_id}",
        "comparison_rule": _composition_optional_text(brick.get("comparison_rule")) or template_comparison_rule or f"missing comparison rule for {node_id}",
        # Author value wins; else the kind's real return shape (when a
        # step_template resolves). A no-template node without an authored shape is
        # already rejected above; keep a loud marker only so the diagnostic row can
        # be assembled before CompositionError is raised.
        "required_return_shape": _composition_optional_text(brick.get("required_return_shape")) or template_required_return_shape or f"missing required return shape for {node_id}",
    }
    # Did the AUTHOR override required_return_shape? If so, the template's
    # carries_forward_fields (a subset of the TEMPLATE's shape) is NOT a valid
    # subset of the author's shape, so it must NOT be defaulted onto the row (that
    # would FILTER OUT fields the author's custom shape carries -- a starvation).
    # The carry-set default below is gated on this: it rides the SAME source as
    # required_return_shape (template-shape => template-carry; author-shape =>
    # author-carry-only).
    author_overrode_return_shape = bool(
        _composition_optional_text(brick.get("required_return_shape"))
    )
    # ⑤ STATIC INSTRUCTION BODY: stamp the kind's brick.md ## body (carried on the
    # step_template registry row by plan_rendering) onto the brick_row, beside
    # required_return_shape so the how-to travels with the shape it describes. The
    # request builder (run._adapter_request_from_prepared) threads it to the agent
    # prompt. Absent step_template (no-template branch) -> no body (empty at run
    # time), matching the no-template required_return_shape fallback above.
    template_instruction_body = (
        step_template.get("brick_instruction_body")
        if isinstance(step_template, Mapping)
        else None
    )
    if template_instruction_body:
        row["brick_instruction_body"] = str(template_instruction_body)
    # CARRIES-FORWARD SET: stamp the kind's carries_forward_fields (the HANDOFF
    # subset, carried on the step_template registry row by plan_rendering) onto the
    # brick_row beside required_return_shape -- the SAME surface the walker carry
    # seam reads to FILTER an UPSTREAM step's forwarded summary down to its handoff
    # fields. The forward-set must be a SUBSET of the row's required_return_shape, so
    # it rides the SAME source as that shape:
    #   * an AUTHOR-supplied carries_forward_fields always wins (the author owns the
    #     subset of whatever shape they declared);
    #   * else the TEMPLATE default applies ONLY when the row's required_return_shape
    #     is ALSO the template's (i.e. the author did NOT override the shape) -- so a
    #     node with a CUSTOM required_return_shape gets NO template carry-set (no
    #     filter, full carry), never one that would drop its custom fields;
    #   * else empty (no filter -> full carry, backward-safe).
    # Stamped only when non-empty so a kind with no declared carry-set leaves the
    # row key absent and the seam falls back to the full-summary carry.
    template_carries_forward = (
        _composition_optional_text(step_template.get("carries_forward_fields"))
        if isinstance(step_template, Mapping)
        else None
    )
    author_carries_forward = _composition_optional_text(brick.get("carries_forward_fields"))
    carries_forward = author_carries_forward or (
        "" if author_overrode_return_shape else (template_carries_forward or "")
    )
    if carries_forward:
        row["carries_forward_fields"] = carries_forward
    template_capability_class = (
        _composition_optional_text(step_template.get("capability_class"))
        if isinstance(step_template, Mapping)
        else None
    )
    author_capability_class = _composition_optional_text(brick.get("capability_class"))
    capability_class = author_capability_class or (template_capability_class or "")
    if capability_class:
        row["capability_class"] = capability_class
    source_facts = brick.get("source_facts")
    if source_facts is not None:
        row["source_facts"] = list(_text_sequence(f"nodes[{index}].source_facts", source_facts))
    proof_obligations = brick.get("proof_obligations")
    if proof_obligations is not None:
        row["proof_obligations"] = [
            dict(_mapping_value(f"nodes[{index}].proof_obligations[]", item))
            for item in _sequence_value(
                f"nodes[{index}].proof_obligations",
                proof_obligations,
            )
        ]
    raw_write_scope = brick.get("write_scope")
    template_write_need = bool(
        step_template.get("write_need")
        if isinstance(step_template, Mapping)
        else False
    )
    if raw_write_scope is not None:
        row["write_scope"] = dict(_mapping_value(f"nodes[{index}].write_scope", raw_write_scope))
    elif template_write_need:
        row["write_scope"] = derived_worktree_write_scope()
    # Carry the EXPLICIT write NEED marker (requires_brick_write_scope) from the
    # node declaration onto the plan Brick row VERBATIM; when the Brick template
    # itself declares a write NEED, stamp that template-owned need if the node did
    # not restate it. Value validation (bool / yes / no, fail-closed on anything
    # else) stays owned by brick.spec.declared_brick_write_need; this is transport
    # only. The legacy ``write_need`` spelling is RETIRED (L legacy cut, 0610): it
    # is REJECTED LOUDLY here instead of being carried or silently dropped
    # (composition keeps no node-key whitelist, so without this rejection a legacy
    # node marker would vanish without a trace).
    if "requires_brick_write_scope" in brick:
        row["requires_brick_write_scope"] = brick.get("requires_brick_write_scope")
    elif template_write_need:
        row["requires_brick_write_scope"] = True
    elif "write_need" in brick:
        problems.append(
            CompositionProblem(
                "legacy_write_need_key",
                node_id,
                f"nodes[{index}] carries the retired legacy key 'write_need'; "
                "declare the Brick write NEED as 'requires_brick_write_scope' "
                "(legacy spelling is not admitted)",
            )
        )
    return row


def _composition_default_brick_ref(node_id: str) -> str:
    if node_id.startswith(("brick-", "brick:", "brick-instance:", "brick-boundary:")):
        return node_id
    return f"brick-{_composition_slug(node_id)}"


def _composition_endpoint(edge: Mapping[str, Any], endpoint: str) -> str:
    keys = (
        ("source", "source_node_id", "source_step_ref", "source_ref", "from", "from_node")
        if endpoint == "source"
        else ("target", "target_node_id", "target_step_ref", "target_ref", "to", "to_node")
    )
    for key in keys:
        value = _composition_optional_text(edge.get(key))
        if value:
            return value
    return ""


def _composition_terminal_target(value: str) -> bool:
    return bool(value and value.startswith(("building-boundary:", "building-boundary-")))


def _composition_declared_gate_refs(
    index: int,
    edge: Mapping[str, Any],
    target_ref: str,
    node_id: str,
    problems: list[CompositionProblem],
) -> tuple[str, ...]:
    raw_refs = edge.get("declared_gate_refs")
    admitted_refs = {DEFAULT_LINK_GATE_REF, *COMPACT_LINK_GATE_TOKENS.values()}
    if raw_refs is not None:
        if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
            problems.append(
                CompositionProblem(
                    "bad_gate_token",
                    node_id,
                    "declared_gate_refs must be an array of admitted Link gate refs",
                )
            )
            return (DEFAULT_LINK_GATE_REF,)
        refs = tuple(str(ref).strip() for ref in raw_refs if str(ref).strip())
        if not refs or refs[0] != DEFAULT_LINK_GATE_REF:
            problems.append(
                CompositionProblem(
                    "gate_ref_ordering",
                    node_id,
                    "declared_gate_refs must start with link-gate:default-transition",
                )
            )
        unknown = sorted(ref for ref in refs if ref not in admitted_refs)
        if unknown:
            problems.append(
                CompositionProblem(
                    "bad_gate_token",
                    node_id,
                    "declared_gate_refs contains unadmitted gate ref(s): " + ", ".join(unknown),
                )
            )
        return refs or (DEFAULT_LINK_GATE_REF,)

    raw_gate = edge.get("gate", edge.get("gate_token", edge.get("gates", "")))
    gate_text = _composition_gate_text(raw_gate)
    target_text = target_ref or "brick-invalid-target"
    expression = target_text if not gate_text else f"{gate_text} -> {target_text}"
    try:
        parsed = _parse_compact_link_expression(index, expression)
    except ValueError as exc:
        problems.append(
            CompositionProblem(
                "bad_gate_token",
                node_id,
                str(exc),
            )
        )
        return (DEFAULT_LINK_GATE_REF,)
    return tuple(parsed["declared_gate_refs"])


def _composition_gate_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "+".join(_composition_gate_text(item) for item in value if _composition_gate_text(item))
    text = str(value).strip()
    if text == DEFAULT_LINK_GATE_REF:
        return ""
    for token, gate_ref in COMPACT_LINK_GATE_TOKENS.items():
        if text == gate_ref:
            return token
    return text


def _composition_edge_ref(index: int, edge: Mapping[str, Any], source: str, target: str) -> str:
    declared = _composition_optional_text(edge.get("edge_ref"))
    if declared:
        return declared
    return f"edge:{_composition_slug(source)}-to-{_composition_slug(target or str(index + 1))}"


def _composition_edge_movement(
    index: int,
    edge: Mapping[str, Any],
    problems: list[CompositionProblem],
) -> str:
    movement = _composition_optional_text(edge.get("movement"))
    if not movement:
        problems.append(
            CompositionProblem(
                "missing_movement",
                _composition_edge_ref(index, edge, "edge", str(index + 1)),
                "edge must declare Link movement; support must not choose Movement",
            )
        )
        return ""
    if movement not in MOVEMENT_LITERALS:
        problems.append(
            CompositionProblem(
                "unknown_movement",
                _composition_edge_ref(index, edge, "edge", str(index + 1)),
                f"edge movement must be one of {list(MOVEMENT_LITERALS)}",
            )
        )
    return movement


def _composition_link_edge(record: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = record["raw"]
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": _composition_optional_text(raw.get("row_ref")) or f"link-row:{record['edge_ref']}",
        "movement": record["movement"],
        "target_ref": record["target_ref"],
        "declared_gate_refs": list(record["declared_gate_refs"]),
    }
    for key in (
        "gate_sequence_policy",
        # A1 (0610): translated-gate provenance rides the declared edge like the
        # other Link-owned objects (mapping carry below); absent -> not stamped.
        "gate_concept_provenance",
        "route_replay_plan",
        "route_decision_basis",
        "transition_authoring",
        "transition_lifecycle",
        "building_lifecycle",
    ):
        value = record.get(key, raw.get(key))
        if value is not None:
            if key == "gate_sequence_policy":
                if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                    link_row[key] = value
                else:
                    link_row[key] = [
                        dict(_mapping_value(f"link_edges.{record['edge_ref']}.{key}[{index}]", item))
                        for index, item in enumerate(value)
                    ]
                continue
            link_row[key] = dict(_mapping_value(f"link_edges.{record['edge_ref']}.{key}", raw.get(key)))
    edge: dict[str, Any] = {
        "edge_ref": record["edge_ref"],
        "source_step_ref": record["source_step_ref"],
        "rows": [link_row],
    }
    if record["target_step_ref"]:
        edge["target_step_ref"] = record["target_step_ref"]
    return edge


def _composition_agent_object_refs(repo: Path) -> frozenset[str]:
    object_dir = repo / "brick_protocol" / "agent" / "objects"
    return frozenset(f"agent-object:{path.stem}" for path in object_dir.glob("*.yaml"))
