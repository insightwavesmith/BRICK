"""Structure-plan fan-in/fan-out barrier checker.

This checker is support evidence only. It inspects caller-authored
``structure_plan`` fixtures for the confirmed Building Call lowering surface.
It does not choose Movement, route targets, success, quality, or sufficiency.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.graph_topology_fan_barrier import (
    fan_barrier_violations,
)
from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError
from brick_protocol.support.operator.building_call import (
    BuildingCallLoweringError,
    building_call_lowering_v1,
    validate_building_call_lowering_request,
)


CHECK_ID = "structure_plan_fan_barrier"
FIXTURE_ROOT = Path("brick_protocol/support/checkers/fixtures/building_call_lowering")
POSITIVE_FIXTURE = FIXTURE_ROOT / "positive_structure_plan_request.json"
MULTIPLE_FAN_OUT_FIXTURE = FIXTURE_ROOT / "positive_structure_plan_multiple_fan_out_groups.json"
FAN_OUT_WITH_COO_GATE_FIXTURE = FIXTURE_ROOT / "positive_structure_plan_fan_out_with_coo_gate.json"
NO_FAN_IN_FIXTURE = FIXTURE_ROOT / "negative_structure_plan_no_fan_in.json"
FAN_OUT_MISSING_COO_GATE_FIXTURE = (
    FIXTURE_ROOT / "negative_structure_plan_fan_out_missing_coo_gate.json"
)
MULTIPLE_FAN_OUT_MISSING_SOURCE_FIXTURE = (
    FIXTURE_ROOT / "negative_structure_plan_multiple_fan_out_missing_source.json"
)
DUPLICATE_BRANCH_SOURCE_FIXTURE = FIXTURE_ROOT / "negative_structure_plan_duplicate_branch_source.json"
HELD_FIXTURE = FIXTURE_ROOT / "negative_held_for_coo_review.json"
PROOF_LIMIT = (
    "proof limit: structure_plan fan barrier checker support evidence only; "
    "it proves only the confirmed request fixture shapes for single fan-in "
    "convergence, wait-all preservation, pairwise-disjoint branch write fences, "
    "duplicate branch/source rejection, multiple fan-out convergence, "
    "coo_gate_edge cap-hold consistency, held_for_coo_review consistency, and "
    "graph fan-barrier RED probing; not "
    "source truth, success judgment, quality judgment, Movement authority, "
    "provider behavior, or complete graph topology correctness."
)


def _load_fixture(repo: Path, relative_path: Path) -> Mapping[str, Any]:
    path = repo / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileError(f"structure_plan fan barrier fixture read failed: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"structure_plan fan barrier fixture JSON parse failed: {path}:{exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"structure_plan fan barrier fixture must be a JSON object: {path}")
    return value


def _lowered_topology(request: Mapping[str, Any]) -> Mapping[str, Any]:
    lowered = building_call_lowering_v1(request)
    intent = lowered.get("lowered_intent")
    if not isinstance(intent, Mapping):
        raise ProfileError("structure_plan fan barrier rejected: lowered_intent missing")
    building_map = intent.get("building_map")
    if not isinstance(building_map, Mapping):
        raise ProfileError("structure_plan fan barrier rejected: building_map missing")
    topology = building_map.get("graph_topology")
    if not isinstance(topology, Mapping):
        raise ProfileError("structure_plan fan barrier rejected: graph_topology missing")
    return topology


def _assert_rejected(request: Mapping[str, Any], expected_text: str, label: str) -> None:
    violations = validate_building_call_lowering_request(request)
    if not any(expected_text in violation for violation in violations):
        raise ProfileError(
            f"structure_plan fan barrier rejected evidence: {label} did not trip {expected_text!r}"
        )
    try:
        building_call_lowering_v1(request)
    except BuildingCallLoweringError:
        return
    raise ProfileError(f"structure_plan fan barrier rejected evidence: {label} normalized")


def _duplicate_branch_source_violations(request: Mapping[str, Any]) -> list[str]:
    structure_plan = request.get("structure_plan")
    if not isinstance(structure_plan, Mapping):
        raise ProfileError("structure_plan fan barrier duplicate fixture lost structure_plan")

    violations: list[str] = []
    fan_out_groups = structure_plan.get("fan_out_groups")
    if isinstance(fan_out_groups, list):
        for index, group in enumerate(fan_out_groups):
            if not isinstance(group, Mapping):
                continue
            branches = group.get("branches")
            if isinstance(branches, list):
                seen: set[str] = set()
                for branch in branches:
                    if not isinstance(branch, str):
                        continue
                    if branch in seen:
                        violations.append(
                            "duplicate branch/source: "
                            f"fan_out_groups[{index}].branches repeats {branch!r}"
                        )
                    seen.add(branch)

    fan_in_groups = structure_plan.get("fan_in_groups")
    if isinstance(fan_in_groups, list):
        for index, group in enumerate(fan_in_groups):
            if not isinstance(group, Mapping):
                continue
            sources = group.get("sources")
            if isinstance(sources, list):
                seen = set()
                for source in sources:
                    if not isinstance(source, str):
                        continue
                    if source in seen:
                        violations.append(
                            "duplicate branch/source: "
                            f"fan_in_groups[{index}].sources repeats {source!r}"
                        )
                    seen.add(source)

    return violations


def _assert_no_duplicate_branch_source(request: Mapping[str, Any], label: str) -> None:
    violations = _duplicate_branch_source_violations(request)
    if violations:
        raise ProfileError(
            f"structure_plan fan barrier rejected: {label} carries "
            + "; ".join(violations)
        )


def _assert_duplicate_branch_source_rejected(request: Mapping[str, Any]) -> None:
    try:
        _assert_no_duplicate_branch_source(request, "duplicate branch/source fixture")
    except ProfileError as exc:
        if "duplicate branch/source" in str(exc):
            return
        raise
    else:
        raise ProfileError(
            "structure_plan fan barrier rejected evidence: duplicate branch/source fixture "
            "did not carry a duplicate"
        )


def _topology_as_barrier_packet(topology: Mapping[str, Any]) -> dict[str, Any]:
    edges = []
    for index, edge in enumerate(topology.get("edges", [])):
        if not isinstance(edge, Mapping):
            continue
        source = edge.get("from")
        target = edge.get("to")
        if isinstance(source, str) and isinstance(target, str):
            edges.append({"edge_ref": f"edge-{index}", "source": source, "target": target})

    groups = []
    for index, group in enumerate(topology.get("fan_in_groups", [])):
        if not isinstance(group, Mapping):
            continue
        converge_on = group.get("converge_on")
        sources = group.get("sources")
        if not isinstance(converge_on, str) or not isinstance(sources, list):
            continue
        member_refs = []
        for edge_index, edge in enumerate(edges):
            if edge.get("target") == converge_on and edge.get("source") in sources:
                member_refs.append(f"edge-{edge_index}")
        groups.append(
            {
                "group_id": f"fan-in-{index}",
                "group_role": "fan_in",
                "member_refs": member_refs,
                "fan_in_target_ref": converge_on,
            }
        )
    return {"edges": edges, "groups": groups}


def run_structure_plan_fan_barrier(repo: Path) -> KernelResult:
    positive = _load_fixture(repo, POSITIVE_FIXTURE)
    _assert_no_duplicate_branch_source(positive, "positive fixture")
    topology = _lowered_topology(positive)
    fan_in_groups = topology.get("fan_in_groups")
    if not isinstance(fan_in_groups, list) or len(fan_in_groups) != 1:
        raise ProfileError("structure_plan fan barrier rejected: positive fixture lost single fan-in")
    fan_in = fan_in_groups[0]
    if not isinstance(fan_in, Mapping) or fan_in.get("wait_all") is False:
        raise ProfileError("structure_plan fan barrier rejected: positive fixture lost wait-all")

    barrier_packet = _topology_as_barrier_packet(topology)
    if fan_barrier_violations(barrier_packet):
        raise ProfileError("structure_plan fan barrier rejected: positive fixture failed graph barrier oracle")

    multiple_fan_out = _load_fixture(repo, MULTIPLE_FAN_OUT_FIXTURE)
    _assert_no_duplicate_branch_source(multiple_fan_out, "multiple fan-out fixture")
    multiple_topology = _lowered_topology(multiple_fan_out)
    multiple_fan_out_groups = multiple_topology.get("fan_out_groups")
    multiple_fan_in_groups = multiple_topology.get("fan_in_groups")
    if not isinstance(multiple_fan_out_groups, list) or len(multiple_fan_out_groups) != 2:
        raise ProfileError(
            "structure_plan fan barrier rejected: multiple fan-out fixture lost two fan-out groups"
        )
    if not isinstance(multiple_fan_in_groups, list) or len(multiple_fan_in_groups) != 1:
        raise ProfileError(
            "structure_plan fan barrier rejected: multiple fan-out fixture lost single fan-in"
        )
    multiple_barrier_packet = _topology_as_barrier_packet(multiple_topology)
    if fan_barrier_violations(multiple_barrier_packet):
        raise ProfileError(
            "structure_plan fan barrier rejected: multiple fan-out fixture failed graph barrier oracle"
        )

    fan_out_with_coo_gate = _load_fixture(repo, FAN_OUT_WITH_COO_GATE_FIXTURE)
    coo_gate_topology = _lowered_topology(fan_out_with_coo_gate)
    if not isinstance(coo_gate_topology.get("fan_out_groups"), list):
        raise ProfileError("structure_plan fan barrier rejected: coo gate fixture lost fan-out")
    lowered_with_gate = building_call_lowering_v1(fan_out_with_coo_gate)
    intent_with_gate = lowered_with_gate.get("lowered_intent")
    if not isinstance(intent_with_gate, Mapping):
        raise ProfileError("structure_plan fan barrier rejected: coo gate fixture lost intent")
    building_map_with_gate = intent_with_gate.get("building_map")
    if not isinstance(building_map_with_gate, Mapping):
        raise ProfileError("structure_plan fan barrier rejected: coo gate fixture lost building_map")
    coo_gate_edge = building_map_with_gate.get("coo_gate_edge")
    if not isinstance(coo_gate_edge, Mapping) or coo_gate_edge.get("state") != "held_for_coo_review":
        raise ProfileError("structure_plan fan barrier rejected: coo gate fixture lost held state")

    no_fan_in = _load_fixture(repo, NO_FAN_IN_FIXTURE)
    _assert_rejected(no_fan_in, "exactly one convergence group", "no-fan-in fixture")

    fan_out_missing_coo_gate = _load_fixture(repo, FAN_OUT_MISSING_COO_GATE_FIXTURE)
    _assert_rejected(
        fan_out_missing_coo_gate,
        "fan_out_groups require coo_gate_edge",
        "fan-out missing coo gate fixture",
    )

    multiple_fan_out_missing_source = _load_fixture(repo, MULTIPLE_FAN_OUT_MISSING_SOURCE_FIXTURE)
    _assert_rejected(
        multiple_fan_out_missing_source,
        "exactly match the single fan-in sources",
        "multiple fan-out missing-source fixture",
    )

    duplicate_branch_source = _load_fixture(repo, DUPLICATE_BRANCH_SOURCE_FIXTURE)
    _assert_duplicate_branch_source_rejected(duplicate_branch_source)

    wait_all_probe = json.loads(json.dumps(positive))
    wait_all_probe["structure_plan"]["fan_in_groups"][0]["wait_all"] = False
    _assert_rejected(wait_all_probe, "must preserve wait-all", "wait-all mutation")

    overlapping_write_probe = json.loads(json.dumps(positive))
    overlapping_write_probe["structure_plan"]["nodes"]["axis-lens"]["write_scope"]["allowed_paths"] = [
        "tmp/code/subdir"
    ]
    _assert_rejected(
        overlapping_write_probe,
        "pairwise disjoint",
        "overlapping branch write-fence mutation",
    )

    held = _load_fixture(repo, HELD_FIXTURE)
    held_structure_probe = json.loads(json.dumps(positive))
    held_structure_probe["gate_state"] = held.get("gate_state", "held_for_coo_review")
    _assert_rejected(
        held_structure_probe,
        "held_for_coo_review requests must not be lowered",
        "held_for_coo_review structure_plan mutation",
    )

    wrong_coo_gate_probe = json.loads(json.dumps(positive))
    wrong_coo_gate_probe["structure_plan"]["coo_gate_edge"]["state"] = "draft"
    _assert_rejected(
        wrong_coo_gate_probe,
        "coo_gate_edge.state must be held_for_coo_review",
        "wrong coo gate state mutation",
    )

    multi_target_packet = json.loads(json.dumps(barrier_packet))
    multi_target_packet["edges"].extend(
        [
            {"edge_ref": "edge-extra-0", "source": "code-lens", "target": "alternate-closure"},
            {"edge_ref": "edge-extra-1", "source": "axis-lens", "target": "alternate-closure"},
            {"edge_ref": "edge-extra-2", "source": "evidence-lens", "target": "alternate-closure"},
        ]
    )
    multi_target_packet["groups"].append(
        {
            "group_id": "fan-in-extra",
            "group_role": "fan_in",
            "member_refs": ["edge-extra-0", "edge-extra-1", "edge-extra-2"],
            "fan_in_target_ref": "alternate-closure",
        }
    )
    if not fan_barrier_violations(multi_target_packet):
        raise ProfileError("structure_plan fan barrier rejected evidence: graph fan-barrier RED did not fire")

    return KernelResult(
        check_id=CHECK_ID,
        inspected=12,
        output=(
            "structure_plan fan barrier passed: positive fixture lowered to a single "
            "wait-all fan-in; multiple fan-out fixture lowered to one convergence; "
            "fan-out with coo gate fixture preserved held_for_coo_review; no-fan-in, "
            "fan-out missing coo gate, multiple fan-out missing-source, duplicate "
            "branch/source, wait-all, overlapping write-fence, held_for_coo_review, "
            "wrong coo gate state, and graph fan-barrier mutations RED-fired. "
            + PROOF_LIMIT
        ),
    )
