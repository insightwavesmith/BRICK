"""Composition graph/plan validators: the cohesive validation cluster that builds
CompositionProblem (collected by compose_building).

Extracted verbatim from composition.py (module-separation). PURE relocation: no
logic/name/signature/order change. Imports siblings directly (no top-level import
of composition.py, which would cycle). The plan_graph / plan_validation imports
stay LAZY inside the validator functions (they pull from the heavier graph/plan
layer and would re-introduce an import cycle if hoisted).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS
from brick_protocol.support.operator.composition_problem import CompositionProblem
from brick_protocol.support.operator.composition_common import (
    _composition_gate_sequence_ref,
    _composition_optional_text,
    _composition_shape_has_field,
)
from brick_protocol.support.operator.composition_route_policy import (
    _composition_node_reroute_budgets,
)


_CLOSURE_POLICY_REQUIRED_KINDS = (
    "implementation_gap",
    "verification_gap",
)
_CLOSURE_POLICY_TARGET_ACTIONS = ("target", "reroute")
_CLOSURE_POLICY_HOLD_ACTIONS = ("hold",)


def _composition_graph_incoming_counts(
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, int]:
    """Count incoming Link edges per declared graph node (mechanical position fact).

    The position of a node in the author/COO-declared graph is read off the
    declared Link edges -- support does not choose it. A node with zero incoming
    edges is a FIRST-position (root) node; this is the same incoming-edge count
    that plan_graph._validate_graph_plan_topology uses to find graph roots, read
    here from the already-resolved compose edge_records (target_step_ref). Edges
    whose target is a terminal building boundary carry an empty target_step_ref
    and are intentionally not counted as incoming to any node.
    """
    counts: dict[str, int] = {
        str(record.get("step_ref", "")).strip(): 0
        for record in node_records
        if str(record.get("step_ref", "")).strip()
    }
    for edge in edge_records:
        target = str(edge.get("target_step_ref", "")).strip()
        if target in counts:
            counts[target] += 1
    return counts


def _composition_hard_graph_contract_problems(
    *,
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    shape_omitted_steps: frozenset[str] | set[str] = frozenset(),
) -> tuple[CompositionProblem, ...]:
    problems: list[CompositionProblem] = []
    records_by_step = {str(record.get("step_ref")): record for record in node_records}
    records_by_endpoint = _composition_records_by_endpoint(node_records)
    budgets = _composition_node_reroute_budgets(node_records)
    fan_in_targets = _composition_fan_in_target_steps(edge_records, groups)
    # POSITION classifier (mechanical, position-driven -- NOT brick-kind-driven):
    # the transition-concern lane is Link-facing or observations-only depending on
    # the node's POSITION in the author-declared graph, which is read off the
    # declared Link edges (the caller/COO authored that structure). The four
    # positions and their concern-lane rule:
    #   * fan-in TARGET (closure-synthesis, incoming from a fan-in group): Link-facing
    #     transition_concern_evidence REQUIRED (closure_transition_concern_shape_missing
    #     when absent) + closure_transition_target_policy validated -- handled in the
    #     fan_in_targets loop below.
    #   * fan-in SOURCE (a parallel lane feeding a fan-in target): concern lane is
    #     OBSERVATIONS-ONLY -- it must NOT carry Link-facing transition_concern_evidence
    #     (qa_transition_concern_shape) -- handled in the per-source loop below.
    #   * FIRST-position (incoming == 0, no upstream Brick): a Link-facing concern has
    #     no upstream Brick to reroute to, so it cannot be Link-routed at all -- handled
    #     by the first-position loop after this one.
    #   * linear (in a graph, not a fan-in member, has an upstream): concern lane ON --
    #     the brick's declared transition_concern_evidence routes to the direct next
    #     Link; no extra rule (the linear/document-centric path already carries it).
    incoming_counts = _composition_graph_incoming_counts(node_records, edge_records)
    fan_in_source_steps: set[str] = set()
    for _target_step_ref, _source_step_refs in fan_in_targets.items():
        fan_in_source_steps.update(_source_step_refs)
    fan_in_target_steps = set(fan_in_targets)
    for target_step_ref, source_step_refs in fan_in_targets.items():
        target_record = records_by_step.get(target_step_ref)
        if target_record is None:
            continue
        target_shape = _composition_required_return_shape(target_record)
        # When the author OMITTED required_return_shape on this fan-in target, the
        # shape carries only the template default (not the author's intent); the
        # clear missing_brick_fields(fan-in lane) problem already covers it, so do
        # not ALSO emit the confusing template-default-driven transition-concern
        # codes for it (design CHANGE 3: clear message INSTEAD of the confusing one).
        if target_step_ref not in shape_omitted_steps:
            if not _composition_shape_has_field(target_shape, "transition_concern_evidence"):
                problems.append(
                    CompositionProblem(
                        "closure_transition_concern_shape_missing",
                        target_step_ref,
                        "fan-in closure-synthesis must be the only Link-facing transition concern source",
                        )
                    )
            if _composition_shape_has_field(target_shape, "transition_concern_evidence"):
                problems.extend(
                    _composition_closure_policy_problems(
                        closure_record=target_record,
                        records_by_endpoint=records_by_endpoint,
                        budgets=budgets,
                    )
                )
        if _composition_step_output_source_facts(target_record):
            problems.append(
                CompositionProblem(
                    "fan_in_source_fact_disk_dependency",
                    target_step_ref,
                    "fan-in closure must receive sibling step outputs through "
                    "source_fact_bodies packet carry, not disk step-output source_facts",
                )
            )
        for source_step_ref in source_step_refs:
            source_record = records_by_step.get(source_step_ref)
            if source_record is None:
                continue
            if source_step_ref in shape_omitted_steps:
                continue
            source_shape = _composition_required_return_shape(source_record)
            if _composition_shape_has_field(source_shape, "transition_concern_evidence"):
                problems.append(
                    CompositionProblem(
                        "qa_transition_concern_shape",
                        source_step_ref,
                        "fan-in QA lanes return their own Brick fields without "
                        "Link-facing transition_concern_evidence; closure-synthesis is "
                        "the single Link-facing transition_concern_evidence source",
                    )
                )
    # FIRST-position rule (NEW, position-driven): a node with no incoming Link edge
    # (incoming == 0) is a graph root. A Link-facing transition_concern_evidence is a
    # send-back/reroute signal that needs an upstream Brick to route to (or a declared
    # closure_transition_target_policy that can HOLD it for a human, which only the
    # fan-in TARGET node carries). A first-position node has neither an upstream Brick
    # nor that per-node concern-disposition policy, so a Link-facing concern here has
    # no valid Link target -- it could only be dispositioned by a HUMAN, and there is
    # no per-node first-position concern-disposition field for support to honor. So a
    # first-position node that declares Link-facing transition_concern_evidence is
    # rejected here (the mechanical position fact: "no upstream route for a root
    # concern"); support invents no auto-human-route mechanism. Fan-in members are
    # excluded (a fan-in source/target has an incoming edge, so incoming > 0 already;
    # the guard below is belt-and-suspenders against a malformed fan-in group).
    for step_ref, record in records_by_step.items():
        if not step_ref:
            continue
        if step_ref in shape_omitted_steps:
            continue
        if step_ref in fan_in_source_steps or step_ref in fan_in_target_steps:
            continue
        if incoming_counts.get(step_ref, 0) != 0:
            continue
        shape = _composition_required_return_shape(record)
        if _composition_shape_has_field(shape, "transition_concern_evidence"):
            problems.append(
                CompositionProblem(
                    "first_position_transition_concern_shape",
                    step_ref,
                    "first-position (root) node has no upstream Brick to route a "
                    "Link-facing transition_concern_evidence to; a root concern must be "
                    "observations-only (human-routed), not Link-facing",
                )
            )
    return tuple(problems)


def _composition_gate_sequence_policy_profile_problems(
    *,
    chain_preset: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> tuple[CompositionProblem, ...]:
    raw_profile = chain_preset.get("gate_sequence_policy", ())
    if raw_profile in (None, ()):
        return ()
    if not isinstance(raw_profile, Sequence) or isinstance(raw_profile, (str, bytes)):
        return (
            CompositionProblem(
                "gate_sequence_policy_invalid",
                "__composition__",
                "gate_sequence_policy must be an array of declared Link gate sequence profiles",
            ),
        )

    problems: list[CompositionProblem] = []
    for index, raw_profile_item in enumerate(raw_profile):
        if not isinstance(raw_profile_item, Mapping):
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_invalid",
                    f"gate_sequence_policy[{index}]",
                    "gate_sequence_policy item must be an object",
                )
            )
            continue
        source_template = _composition_optional_text(
            raw_profile_item.get("source_step_template_ref")
        ) or ""
        target_template = _composition_optional_text(
            raw_profile_item.get("target_step_template_ref")
        ) or ""
        sequence = _composition_gate_sequence_profile_steps(raw_profile_item)
        if not sequence:
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_invalid",
                    f"gate_sequence_policy[{index}]",
                    "gate_sequence_policy profile must declare a non-empty sequence",
                )
            )
            continue
        profile_gate_refs = _composition_gate_sequence_refs(sequence)
        matching_edges = _composition_edges_between_templates(
            edge_records=edge_records,
            node_records=node_records,
            source_template=source_template,
            target_template=target_template,
        )
        if not matching_edges:
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_edge_missing",
                    f"{source_template}->{target_template}",
                    "chain preset gate sequence policy requires a declared edge between those step templates",
                )
            )
            continue
        for edge in matching_edges:
            declared_refs = tuple(str(ref) for ref in edge.get("declared_gate_refs", ()))
            missing_refs = [ref for ref in profile_gate_refs if ref not in declared_refs]
            if missing_refs:
                problems.append(
                    CompositionProblem(
                        "gate_sequence_policy_gate_ref_missing",
                        str(edge.get("edge_ref", "")),
                        "gate_sequence_policy gate_ref(s) must be present in declared_gate_refs: "
                        + ", ".join(missing_refs),
                    )
                )
    return tuple(problems)


def _composition_edges_between_templates(
    *,
    edge_records: Sequence[Mapping[str, Any]],
    node_records: Sequence[Mapping[str, Any]],
    source_template: str,
    target_template: str,
) -> tuple[Mapping[str, Any], ...]:
    records_by_step = {str(record.get("step_ref", "")).strip(): record for record in node_records}
    matches: list[Mapping[str, Any]] = []
    for edge in edge_records:
        source = records_by_step.get(str(edge.get("source_step_ref", "")).strip())
        target = records_by_step.get(str(edge.get("target_step_ref", "")).strip())
        if source is None or target is None:
            continue
        if source.get("step_template_ref") == source_template and target.get("step_template_ref") == target_template:
            matches.append(edge)
    return tuple(matches)


def _composition_edge_records_with_gate_sequence_policy(
    *,
    chain_preset: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    raw_profile = chain_preset.get("gate_sequence_policy", ())
    if not isinstance(raw_profile, Sequence) or isinstance(raw_profile, (str, bytes)):
        return tuple(edge_records)
    patched = [dict(record) for record in edge_records]
    for raw_profile_item in raw_profile:
        if not isinstance(raw_profile_item, Mapping):
            continue
        source_template = _composition_optional_text(
            raw_profile_item.get("source_step_template_ref")
        ) or ""
        target_template = _composition_optional_text(
            raw_profile_item.get("target_step_template_ref")
        ) or ""
        sequence = _composition_gate_sequence_profile_steps(raw_profile_item)
        if not sequence:
            continue
        matches = _composition_edges_between_templates(
            edge_records=edge_records,
            node_records=node_records,
            source_template=source_template,
            target_template=target_template,
        )
        match_refs = {str(edge.get("edge_ref", "")).strip() for edge in matches}
        for record in patched:
            raw = record.get("raw")
            if str(record.get("edge_ref", "")).strip() not in match_refs:
                continue
            if isinstance(raw, Mapping) and raw.get("gate_sequence_policy") is not None:
                continue
            record["gate_sequence_policy"] = [
                _composition_gate_sequence_link_step(item) for item in sequence
            ]
    return tuple(patched)


def _composition_gate_sequence_profile_steps(
    profile: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    raw_steps = profile.get("sequence", profile.get("steps", ()))
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
        return ()
    return tuple(item for item in raw_steps if isinstance(item, Mapping))


def _composition_gate_sequence_refs(
    sequence: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    refs: list[str] = []
    for step in sequence:
        ref = _composition_gate_sequence_ref(step)
        if ref:
            refs.append(ref)
    return tuple(refs)


def _composition_gate_sequence_link_step(step: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(step)
    gate_ref = _composition_gate_sequence_ref(step)
    normalized.pop("declared_link_gate", None)
    if gate_ref:
        normalized["gate_ref"] = gate_ref
    return normalized


def _composition_closure_policy_problems(
    *,
    closure_record: Mapping[str, Any],
    records_by_endpoint: Mapping[str, Mapping[str, Any]],
    budgets: Mapping[str, int],
) -> tuple[CompositionProblem, ...]:
    step_ref = str(closure_record.get("step_ref", "")).strip() or "__closure__"
    raw_policy = closure_record.get("closure_transition_target_policy")
    if not isinstance(raw_policy, Mapping):
        return (
            CompositionProblem(
                "closure_transition_target_policy_missing",
                step_ref,
                "fan-in closure with transition_concern_evidence requires caller / COO "
                "declared closure_transition_target_policy",
            ),
        )

    problems: list[CompositionProblem] = []
    for raw_key in raw_policy:
        concern_kind = str(raw_key).strip()
        if concern_kind not in TRANSITION_CONCERN_KINDS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unknown_concern_kind",
                    step_ref,
                    f"closure_transition_target_policy concern_kind is not admitted: {concern_kind}",
                )
            )
    for concern_kind in _CLOSURE_POLICY_REQUIRED_KINDS:
        raw_row = raw_policy.get(concern_kind)
        if not isinstance(raw_row, Mapping):
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_missing",
                    step_ref,
                    f"closure_transition_target_policy must declare {concern_kind}",
                )
            )
            continue
        action = _composition_policy_action(raw_row)
        target_ref = _composition_policy_target_ref(raw_row)
        if concern_kind == "implementation_gap" and action not in _CLOSURE_POLICY_TARGET_ACTIONS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_missing",
                    step_ref,
                    "implementation_gap must declare an explicit budgeted target",
                )
            )
            continue
        if action in _CLOSURE_POLICY_HOLD_ACTIONS:
            if target_ref:
                problems.append(
                    CompositionProblem(
                        "closure_transition_target_policy_invalid",
                        step_ref,
                        f"{concern_kind} HOLD policy must not also declare target_ref",
                    )
                )
            continue
        if action not in _CLOSURE_POLICY_TARGET_ACTIONS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_invalid",
                    step_ref,
                    f"{concern_kind} policy action must be hold or target",
                )
            )
            continue
        target_record = records_by_endpoint.get(target_ref)
        if target_record is None:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unknown_target",
                    step_ref,
                    f"{concern_kind} target_ref does not resolve to an existing Brick node: {target_ref or '(blank)'}",
                )
            )
            continue
        target_brick_ref = str(target_record.get("brick_ref", "")).strip()
        if target_brick_ref not in budgets:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unbudgeted_target",
                    step_ref,
                    f"{concern_kind} target_ref must name a node with node_reroute_budget: {target_ref}",
                )
            )
    return tuple(problems)


def _composition_records_by_endpoint(
    node_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Mapping[str, Any]]:
    endpoints: dict[str, Mapping[str, Any]] = {}
    for record in node_records:
        for key in ("node_id", "step_ref", "brick_ref"):
            value = str(record.get(key, "")).strip()
            if value:
                endpoints[value] = record
    return endpoints


def _composition_policy_action(policy_row: Mapping[str, Any]) -> str:
    for key in ("action", "disposition", "disposition_action"):
        value = _composition_optional_text(policy_row.get(key))
        if value:
            return value.lower()
    # FAIL CLOSED: do NOT infer a Movement action from the mere presence of a
    # target_ref. When no explicit action/disposition is declared, the action is
    # ABSENT -- support records that absence (returns "") and the consumer rejects
    # the target-without-action row ("policy action must be hold or target").
    return ""


def _composition_policy_target_ref(policy_row: Mapping[str, Any]) -> str:
    for key in ("target_ref", "target", "target_node_id", "target_step_ref", "target_brick_ref"):
        value = _composition_optional_text(policy_row.get(key))
        if value:
            return value
    return ""


def _composition_fan_in_target_steps(
    edge_records: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
) -> Mapping[str, tuple[str, ...]]:
    edge_by_ref = {str(record.get("edge_ref")): record for record in edge_records}
    targets: dict[str, list[str]] = {}
    for group in groups:
        if not isinstance(group, Mapping) or str(group.get("group_role", "")).strip() != "fan_in":
            continue
        raw_refs = group.get("member_refs", ())
        if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
            continue
        for edge_ref in raw_refs:
            record = edge_by_ref.get(str(edge_ref))
            if not record:
                continue
            target = str(record.get("target_step_ref", "")).strip()
            source = str(record.get("source_step_ref", "")).strip()
            if target and source:
                targets.setdefault(target, []).append(source)
    return {target: tuple(dict.fromkeys(sources)) for target, sources in targets.items()}


def _composition_required_return_shape(record: Mapping[str, Any]) -> str:
    brick_row = record.get("brick_row")
    if not isinstance(brick_row, Mapping):
        return ""
    return str(brick_row.get("required_return_shape", "")).lower()


def _composition_author_required_return_shape(record: Mapping[str, Any]) -> str:
    """The AUTHOR-declared required_return_shape for a node (NOT the U2-3 default).

    Mirrors _composition_brick_row's brick extraction (node.brick mapping, else
    the node itself) and returns the author's raw required_return_shape text. This
    is read from raw_node so a fan-in member that omitted the field is detected
    even though brick_row already carries the template default.
    """
    raw_node = record.get("raw")
    if not isinstance(raw_node, Mapping):
        return ""
    raw_brick = raw_node.get("brick")
    brick = raw_brick if isinstance(raw_brick, Mapping) else raw_node
    return _composition_optional_text(brick.get("required_return_shape")) or ""


def _composition_step_output_source_facts(record: Mapping[str, Any]) -> tuple[str, ...]:
    brick_row = record.get("brick_row")
    if not isinstance(brick_row, Mapping):
        return ()
    raw = brick_row.get("source_facts", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(
        str(item)
        for item in raw
        if "step-output" in str(item) or "step-outputs" in str(item)
    )


def _composition_validator_problems(
    plan: Mapping[str, Any],
    repo: Path,
) -> tuple[CompositionProblem, ...]:
    problems: list[CompositionProblem] = []
    try:
        from support.operator.plan_graph import _linear_plan_from_graph_plan  # noqa: PLC0415
        from support.operator.plan_validation import validate_declared_building_plan  # noqa: PLC0415

        linear_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        validate_declared_building_plan(linear_plan, repo_root=repo)
    except (TypeError, ValueError) as exc:
        problems.append(_composition_problem_from_validator(str(exc)))
    return tuple(problems)


def _composition_problem_from_validator(message: str) -> CompositionProblem:
    lowered = message.lower()
    if "gate_sequence_policy" in lowered and "budget" in lowered:
        code = "gate_sequence_policy_unbudgeted_target"
    elif "gate_sequence_policy" in lowered and "next_gate_ref" in lowered:
        code = "gate_sequence_policy_next_gate_ref"
    elif "gate_sequence_policy" in lowered and "forbidden authority key" in lowered:
        code = "gate_sequence_policy_authority_leak"
    elif "gate_sequence_policy" in lowered:
        code = "gate_sequence_policy_invalid"
    elif "declared_gate_refs must start" in lowered:
        code = "gate_ref_ordering"
    elif "gate" in lowered and ("unadmitted" in lowered or "unknown" in lowered):
        code = "bad_gate_token"
    elif "cycle" in lowered:
        code = "cycle/self_loop"
    elif "duplicate" in lowered or "appears more than once" in lowered:
        code = "duplicate_brick_id"
    elif "does not resolve" in lowered or "without target_step_ref" in lowered:
        code = "unknown_endpoint"
    elif "brick row" in lowered and ("must" in lowered or "missing" in lowered):
        code = "missing_brick_fields"
    elif "execution_order" in lowered or "fan_out" in lowered or "fan_in" in lowered or "group" in lowered or "completion_edge_ref" in lowered:
        code = "execution_order/groups coherence"
    else:
        code = "execution_order/groups coherence"
    return CompositionProblem(code, "__validators__", message)
