"""Plan expansion behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.fixture_graph_helpers import (
    fixture_graph_brick_step,
    fixture_graph_link_edge,
    fixture_proof_limits,
)
from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)


def run_plan_expansion_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "plan_expansion_case")
    if not items:
        return 0
    from support.operator.plan_expansion import assemble_expanded_graph_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "plan_expansion_case item")
        case, relative = _plan_expansion_json_case_document(repo, mapping)
        scenario = require_string(case.get("case_kind"), f"{relative}.case_kind")
        original, fragment, completed_frontier = _plan_expansion_fixture(scenario)
        expect_reject = bool(mapping.get("expect_reject", False))
        try:
            prepared = assemble_expanded_graph_plan(original, fragment, completed_frontier)
        except ValueError:
            if expect_reject:
                count += 1
                continue
            raise
        if expect_reject:
            raise ProfileError(f"plan_expansion_case expected rejection but passed: {relative}")

        expected = require_mapping(mapping.get("expected", {}), "plan_expansion_case.expected")
        expanded = require_mapping(prepared.get("expanded_plan"), "plan_expansion_case expanded_plan")
        metadata = require_mapping(prepared.get("expansion_metadata"), "plan_expansion_case expansion_metadata")
        for step_ref in require_string_list(
            expected.get("step_refs", []),
            "plan_expansion_case.expected.step_refs",
        ):
            if step_ref not in {str(step.get("step_ref")) for step in expanded.get("brick_steps") or []}:
                raise ProfileError(f"plan_expansion_case rejected {relative}: missing step_ref {step_ref!r}")
        for key in ("extends_plan_hash", "expansion_node_budgets"):
            if key not in metadata:
                raise ProfileError(f"plan_expansion_case rejected {relative}: metadata missing {key}")
        if "expansion_node_budgets" in expanded:
            raise ProfileError(f"plan_expansion_case rejected {relative}: expanded_plan carried expansion_node_budgets")
        expected_budget = expected.get("expansion_node_budgets")
        if isinstance(expected_budget, Mapping):
            expected_budget = {str(key): int(value) for key, value in expected_budget.items()}
        if expected_budget is not None and metadata.get("expansion_node_budgets") != expected_budget:
            raise ProfileError(
                f"plan_expansion_case rejected {relative}: expansion_node_budgets "
                f"expected {expected_budget!r}, observed {metadata.get('expansion_node_budgets')!r}"
            )
        if not isinstance(metadata.get("extends_plan_hash"), str) or not metadata["extends_plan_hash"]:
            raise ProfileError(f"plan_expansion_case rejected {relative}: extends_plan_hash was blank")
        count += 1
    return count


def _plan_expansion_json_case_document(
    repo: Path,
    mapping: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    relative = require_string(mapping.get("path"), "plan_expansion_case.path")
    path = repo / relative
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ProfileError(f"plan_expansion_case fixture must be a JSON object: {relative}")
    return document, relative


def _plan_expansion_fixture(case_kind: str) -> tuple[Mapping[str, Any], Mapping[str, Any], tuple[str, ...]]:
    original = _plan_expansion_original_plan()
    fragment = _plan_expansion_valid_fragment()
    completed_frontier = ("step:a", "step:b")
    if case_kind == "valid_merge":
        return original, fragment, completed_frontier
    if case_kind == "cycle":
        cyclic = dict(fragment)
        cyclic["link_edges"] = list(fragment["link_edges"]) + [
            fixture_graph_link_edge(
                "edge:d-to-c",
                "step:d",
                "brick:expansion-c",
                target_step_ref="step:c",
            )
        ]
        return original, cyclic, completed_frontier
    if case_kind == "missing_fan_in_member":
        missing = dict(fragment)
        missing["groups"] = [
            {
                "group_id": "group:expansion-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": ["edge:a-to-d"],
            }
        ]
        return original, missing, completed_frontier
    if case_kind == "upstream_target":
        upstream = dict(fragment)
        upstream["link_edges"] = [
            fixture_graph_link_edge(
                "edge:b-to-c",
                "step:b",
                "brick:expansion-c",
                target_step_ref="step:c",
            ),
            fixture_graph_link_edge(
                "edge:c-to-a",
                "step:c",
                "brick:seed-a",
                target_step_ref="step:a",
            ),
        ]
        upstream["groups"] = []
        return original, upstream, completed_frontier
    if case_kind == "duplicate_step_ref":
        duplicate = dict(fragment)
        duplicate["brick_steps"] = [
            fixture_graph_brick_step(
                "step:b",
                "brick:duplicate-b",
                "edge:b-duplicate-to-boundary",
                agent_object_ref="agent-object:coo",
                work_statement="Duplicate expansion step for checker rejection.",
                required_return_shape="observed_evidence, not_proven",
            )
        ]
        duplicate["link_edges"] = [
            fixture_graph_link_edge(
                "edge:b-duplicate-to-boundary",
                "step:b",
                "building-boundary:plan-expansion",
                close_reason="checker duplicate close",
            )
        ]
        duplicate["execution_order"] = ["step:b"]
        duplicate["groups"] = []
        duplicate["expansion_node_budgets"] = {"step:b": 1}
        return original, duplicate, completed_frontier
    raise ProfileError(f"unknown plan_expansion_case case_kind: {case_kind}")


def _plan_expansion_original_plan() -> Mapping[str, Any]:
    return {
        "plan_shape": "graph",
        "plan_ref": "building-plan:plan-expansion-original",
        "brick_steps": [
            fixture_graph_brick_step(
                "step:a",
                "brick:seed-a",
                "edge:a-to-b",
                agent_object_ref="agent-object:coo",
                work_statement="Seed A for plan expansion checker.",
                required_return_shape="observed_evidence, not_proven",
            ),
            fixture_graph_brick_step(
                "step:b",
                "brick:seed-b",
                "edge:b-to-boundary",
                agent_object_ref="agent-object:coo",
                work_statement="Seed B for plan expansion checker.",
                required_return_shape="observed_evidence, not_proven",
            ),
        ],
        "link_edges": [
            fixture_graph_link_edge(
                "edge:a-to-b",
                "step:a",
                "brick:seed-b",
                target_step_ref="step:b",
            ),
            fixture_graph_link_edge(
                "edge:b-to-boundary",
                "step:b",
                "building-boundary:plan-expansion",
                close_reason="checker original close",
            ),
        ],
        "execution_order": ["step:a", "step:b"],
        "groups": [],
        "proof_limits": fixture_proof_limits(),
    }


def _plan_expansion_valid_fragment() -> Mapping[str, Any]:
    return {
        "brick_steps": [
            fixture_graph_brick_step(
                "step:c",
                "brick:expansion-c",
                "edge:c-to-d",
                agent_object_ref="agent-object:coo",
                work_statement="Expansion C for plan expansion checker.",
                required_return_shape="observed_evidence, not_proven",
            ),
            fixture_graph_brick_step(
                "step:d",
                "brick:expansion-d",
                "edge:d-to-boundary",
                agent_object_ref="agent-object:coo",
                work_statement="Expansion D for plan expansion checker.",
                required_return_shape="observed_evidence, not_proven",
            ),
        ],
        "link_edges": [
            fixture_graph_link_edge(
                "edge:b-to-c",
                "step:b",
                "brick:expansion-c",
                target_step_ref="step:c",
            ),
            fixture_graph_link_edge(
                "edge:a-to-d",
                "step:a",
                "brick:expansion-d",
                target_step_ref="step:d",
            ),
            fixture_graph_link_edge(
                "edge:c-to-d",
                "step:c",
                "brick:expansion-d",
                target_step_ref="step:d",
            ),
            fixture_graph_link_edge(
                "edge:d-to-boundary",
                "step:d",
                "building-boundary:plan-expansion",
                close_reason="checker expanded close",
            ),
        ],
        "execution_order": ["step:c", "step:d"],
        "groups": [
            {
                "group_id": "group:expansion-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": ["edge:a-to-d", "edge:c-to-d"],
            }
        ],
        "expansion_node_budgets": {"step:c": 2, "step:d": 3},
    }
