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
NO_FAN_IN_FIXTURE = FIXTURE_ROOT / "negative_structure_plan_no_fan_in.json"
HELD_FIXTURE = FIXTURE_ROOT / "negative_held_for_coo_review.json"
PROOF_LIMIT = (
    "proof limit: structure_plan fan barrier checker support evidence only; "
    "it proves only the confirmed request fixture shapes for single fan-in "
    "convergence, wait-all preservation, pairwise-disjoint branch write fences, "
    "held_for_coo_review consistency, and graph fan-barrier RED probing; not "
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

    no_fan_in = _load_fixture(repo, NO_FAN_IN_FIXTURE)
    _assert_rejected(no_fan_in, "exactly one convergence group", "no-fan-in fixture")

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
        inspected=6,
        output=(
            "structure_plan fan barrier passed: positive fixture lowered to a single wait-all "
            "fan-in; no-fan-in, wait-all, overlapping write-fence, held_for_coo_review, and "
            "graph fan-barrier mutations RED-fired. "
            + PROOF_LIMIT
        ),
    )
