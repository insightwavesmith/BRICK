"""Plan fixture helpers for behavioral profile case runners.

Checker support only: these helpers build or normalize test plans used by
profile cases. They do not author runtime Movement or own axis meaning.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
)


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"


def _gate_sequence_policy_link_row(case: Mapping[str, Any]) -> Mapping[str, Any]:
    raw_link_row = case.get("link_row", case)
    return require_mapping(raw_link_row, "gate_sequence_policy link_row")


def _gate_sequence_policy_context(case: Mapping[str, Any]) -> dict[str, Any]:
    declared_refs_raw = case.get("declared_brick_refs")
    declared_refs = None
    if declared_refs_raw is not None:
        declared_refs = frozenset(
            require_string_list(declared_refs_raw, "gate_sequence_policy.declared_brick_refs")
        )
    raw_budgets = case.get("node_reroute_budgets")
    node_reroute_budgets = None
    if raw_budgets is not None:
        node_reroute_budgets = require_mapping(
            raw_budgets,
            "gate_sequence_policy.node_reroute_budgets",
        )
    return {
        "source_brick_ref": str(case.get("source_brick_ref", "") or ""),
        "target_brick_ref": str(case.get("target_brick_ref", "") or ""),
        "declared_brick_refs": declared_refs,
        "node_reroute_budgets": node_reroute_budgets,
    }


def _compose_building_profile_plan(case: Mapping[str, Any], repo: Path) -> Mapping[str, Any]:
    from support.operator.building_operation import compose_building

    return compose_building(
        case.get("nodes", []),
        case.get("edges", []),
        selected_shape_ref=case.get("selected_shape_ref", ""),
        declared_by=require_string(case.get("declared_by"), "compose_building.declared_by"),
        groups=case.get("groups", []),
        chain_preset_ref=str(case.get("chain_preset_ref", "") or ""),
        plan_ref=str(case.get("plan_ref", "") or ""),
        building_id=str(case.get("building_id", "") or ""),
        repo_root=repo,
    )


def _graph_test_plan_from_linear(linear_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    """Convert a checker-only forward linear plan into a graph plan via compose_building."""

    from support.operator.composition_compose import compose_building

    if linear_plan.get("plan_shape") != "linear":
        raise ProfileError("_graph_test_plan_from_linear requires plan_shape: linear")
    raw_steps = linear_plan.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
        raise ProfileError("_graph_test_plan_from_linear requires a non-empty steps list")

    nodes: list[Mapping[str, Any]] = []
    edges: list[Mapping[str, Any]] = []
    endpoint_refs: set[str] = set()
    building_id = str(linear_plan.get("building_id") or "checker-linear-to-graph")
    prepared_steps: list[tuple[str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise ProfileError(f"_graph_test_plan_from_linear steps[{index}] must be a mapping")
        step_ref = require_string(raw_step.get("step_ref"), f"steps[{index}].step_ref")
        rows = raw_step.get("rows")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise ProfileError(f"_graph_test_plan_from_linear steps[{index}].rows must be a sequence")
        by_axis = {
            str(row.get("axis")): row
            for row in rows
            if isinstance(row, Mapping) and row.get("axis") in {"Brick", "Agent", "Link"}
        }
        missing_axes = {"Brick", "Agent", "Link"} - set(by_axis)
        if missing_axes:
            raise ProfileError(
                f"_graph_test_plan_from_linear steps[{index}] missing row axis/axes: "
                + ", ".join(sorted(missing_axes))
            )
        brick_row = dict(by_axis["Brick"])
        agent_row = dict(by_axis["Agent"])
        link_row = dict(by_axis["Link"])
        prepared_steps.append((step_ref, raw_step, brick_row, agent_row, link_row))
        endpoint_refs.add(step_ref)
        brick_ref = str(brick_row.get("brick_instance_ref") or "").strip()
        if brick_ref:
            endpoint_refs.add(brick_ref)

    for index, (step_ref, raw_step, brick_row, _agent_row, link_row) in enumerate(prepared_steps):
        node: dict[str, Any] = {
            "node_id": step_ref,
            "step_ref": step_ref,
            "step_template_ref": raw_step.get("step_template_ref", "building-step-template:work"),
        }
        for key in ("selected_adapter_ref", "selected_model_ref"):
            if key in raw_step:
                node[key] = raw_step[key]
        for key, value in brick_row.items():
            if key != "axis":
                if key == "source_facts" and not value:
                    continue
                node[key] = json.loads(json.dumps(value))
        nodes.append(node)

        declared_target_ref = require_string(
            link_row.get("target_ref", link_row.get("next_brick_instance_ref")),
            f"steps[{index}].Link.target_ref",
        )
        if declared_target_ref in endpoint_refs:
            target_ref = declared_target_ref
        elif index == len(prepared_steps) - 1:
            target_ref = (
                declared_target_ref
                if declared_target_ref.startswith(("building-boundary:", "building-boundary-"))
                else f"building-boundary:{_case_slug(building_id)}-closed"
            )
        else:
            target_ref = declared_target_ref
        edge: dict[str, Any] = {
            "edge_ref": f"edge:{step_ref}-to-{_case_slug(target_ref)}",
            "source_step_ref": step_ref,
            "target_ref": target_ref,
            "movement": require_string(link_row.get("movement"), f"steps[{index}].Link.movement"),
            "row_ref": link_row.get("row_ref", f"link-row:{step_ref}"),
        }
        for key in (
            "declared_gate_refs",
            "gate_sequence_policy",
            "gate_concept_provenance",
            "route_replay_plan",
            "route_decision_basis",
            "transition_authoring",
            "transition_lifecycle",
            "building_lifecycle",
        ):
            if key in link_row:
                edge[key] = json.loads(json.dumps(link_row[key]))
        edges.append(edge)

    graph_plan = dict(
        compose_building(
            nodes,
            edges,
            declared_by=str(linear_plan.get("declared_by") or "coo"),
            plan_ref=str(linear_plan.get("plan_ref") or ""),
            building_id=building_id,
            selected_adapter_ref=str(linear_plan.get("selected_adapter_ref") or "adapter:local"),
            selected_model_ref=str(linear_plan.get("selected_model_ref") or "model:default"),
            selected_shape_ref=str(linear_plan.get("selected_shape_ref") or ""),
            chain_preset_ref=str(linear_plan.get("chain_preset_ref") or ""),
        )
    )
    for key in (
        "task_source_ref",
        "task_statement",
        "report_event_policy",
        "route_decision_basis",
        "proof_limits",
        "not_proven",
    ):
        if key in linear_plan:
            graph_plan[key] = json.loads(json.dumps(linear_plan[key]))
    return graph_plan


def _validation_plan_for_declared_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("plan_shape") == "graph":
        from support.operator.plan_graph import _linear_plan_from_graph_plan

        validation_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        return validation_plan
    return plan


def _compose_building_expected_codes(mapping: Mapping[str, Any]) -> list[str]:
    if "expected_code" in mapping:
        return [require_string(mapping.get("expected_code"), "compose_building_rejects.expected_code")]
    return require_string_list(
        mapping.get("expected_codes", []),
        "compose_building_rejects.expected_codes",
    )


def _optional_positive_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text.isdecimal() or int(text) <= 0:
        raise ProfileError(f"{label} must be a positive integer")
    return int(text)


def _compose_building_ok_callable(request: Any) -> Mapping[str, Any]:
    return {
        "observed_evidence": [f"adapter:local observed {request.brick_instance_ref}"],
        "not_proven": ["semantic correctness"],
    }
