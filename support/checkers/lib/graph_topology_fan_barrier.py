"""Graph topology fan-in/fan-out barrier checker.

This checker is support evidence only. It inspects declared graph packet
topology and rejects the narrow no-barrier shortcut where the same exact source
cohort is fanned in to multiple targets. It does not choose Movement, targets,
routes, success, quality, or sufficiency.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import KernelResult, ProfileError


CHECK_ID = "graph_topology_fan_barrier"
NEGATIVE_FIXTURE = Path(
    "project/brick-protocol/status/kernel/GOAL/"
    "brick-6-p7-easy-building-ergonomics-0701d.json"
)
POSITIVE_FIXTURE = Path(
    "project/brick-protocol/status/kernel/GOAL/"
    "brick-6-p7-easy-building-ergonomics-0701f.json"
)
PROOF_LIMIT = (
    "proof limit: graph topology fan barrier checker support evidence only; "
    "it proves only the exact same-source-cohort multi-target fan-in barrier "
    "shape over declared graph packets, not source truth, success judgment, "
    "quality judgment, Movement authority, provider behavior, or complete "
    "graph topology correctness."
)


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _edge_ref(edge: Mapping[str, Any]) -> str:
    return _text(edge.get("edge_ref") or edge.get("link_edge_id"))


def _edge_source(edge: Mapping[str, Any]) -> str:
    return _text(
        edge.get("source")
        or edge.get("source_step_ref")
        or edge.get("source_brick_instance_ref")
    )


def _edge_target(edge: Mapping[str, Any]) -> str:
    return _text(
        edge.get("target")
        or edge.get("target_step_ref")
        or edge.get("target_brick_instance_ref")
    )


def _graph_edges(packet: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw_edges = packet.get("edges", packet.get("link_edges", []))
    if not isinstance(raw_edges, list):
        raise ProfileError("graph fan barrier rejected: graph edges/link_edges must be a list")
    edges: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(raw_edges):
        if not isinstance(item, Mapping):
            raise ProfileError(
                f"graph fan barrier rejected: edge[{index}] must be a mapping"
            )
        ref = _edge_ref(item)
        if not ref:
            raise ProfileError(
                f"graph fan barrier rejected: edge[{index}] requires edge_ref/link_edge_id"
            )
        if ref in edges:
            raise ProfileError(f"graph fan barrier rejected: duplicate edge ref {ref!r}")
        edges[ref] = item
    return edges


def _fan_in_groups(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_groups = packet.get("groups", [])
    if raw_groups is None:
        return []
    if not isinstance(raw_groups, list):
        raise ProfileError("graph fan barrier rejected: graph groups must be a list")
    groups: list[Mapping[str, Any]] = []
    for index, item in enumerate(raw_groups):
        if not isinstance(item, Mapping):
            raise ProfileError(
                f"graph fan barrier rejected: group[{index}] must be a mapping"
            )
        if item.get("group_role") == "fan_in":
            groups.append(item)
    return groups


def _fan_in_signature(
    group: Mapping[str, Any],
    edges_by_ref: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[str, ...], str]:
    group_id = _text(group.get("group_id")) or "<unknown>"
    member_refs = group.get("member_refs")
    if not isinstance(member_refs, list) or len(member_refs) < 2:
        raise ProfileError(
            f"graph fan barrier rejected: fan_in group {group_id!r} requires "
            "at least two member_refs"
        )

    sources: set[str] = set()
    targets: set[str] = set()
    for member in member_refs:
        if not isinstance(member, str) or not member:
            raise ProfileError(
                f"graph fan barrier rejected: fan_in group {group_id!r} has "
                f"invalid member ref {member!r}"
            )
        edge = edges_by_ref.get(member)
        if edge is None:
            raise ProfileError(
                f"graph fan barrier rejected: fan_in group {group_id!r} member "
                f"does not resolve: {member!r}"
            )
        source = _edge_source(edge)
        target = _edge_target(edge)
        if not source or not target:
            raise ProfileError(
                f"graph fan barrier rejected: fan_in group {group_id!r} member "
                f"{member!r} requires source and target"
            )
        sources.add(source)
        targets.add(target)

    declared_target = _text(group.get("fan_in_target_ref"))
    if declared_target:
        targets.add(declared_target)
    if len(sources) < 2 or len(targets) != 1:
        raise ProfileError(
            f"graph fan barrier rejected: fan_in group {group_id!r} must have "
            "multiple sources and exactly one target"
        )
    return tuple(sorted(sources)), next(iter(targets))


def fan_barrier_violations(packet: Mapping[str, Any]) -> list[str]:
    """Return same-source-cohort multi-target fan-in violations."""

    edges_by_ref = _graph_edges(packet)
    targets_by_source_cohort: dict[tuple[str, ...], dict[str, list[str]]] = {}
    for group in _fan_in_groups(packet):
        group_id = _text(group.get("group_id")) or "<unknown>"
        sources, target = _fan_in_signature(group, edges_by_ref)
        targets_by_source_cohort.setdefault(sources, {}).setdefault(target, []).append(
            group_id
        )

    violations: list[str] = []
    for sources, targets in sorted(targets_by_source_cohort.items()):
        if len(targets) <= 1:
            continue
        group_ids = [group_id for ids in targets.values() for group_id in ids]
        violations.append(
            "graph fan barrier: fan_in source cohort converges into multiple "
            "targets without a single barrier Brick; sources="
            f"{list(sources)!r}, targets={sorted(targets)!r}, groups={group_ids!r}"
        )
    return violations


def _load_fixture(repo: Path, relative_path: Path) -> Mapping[str, Any]:
    path = repo / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileError(f"graph fan barrier fixture read failed: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"graph fan barrier fixture JSON parse failed: {path}:{exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"graph fan barrier fixture must be a JSON object: {path}")
    return value


def run_graph_topology_fan_barrier(repo: Path) -> KernelResult:
    negative = _load_fixture(repo, NEGATIVE_FIXTURE)
    negative_violations = fan_barrier_violations(negative)
    if not negative_violations:
        raise ProfileError(
            "kernel check graph_topology_fan_barrier rejected evidence: "
            "negative fixture was not rejected; the no-barrier fan-in/fan-out "
            "shortcut is still accepted"
        )

    positive = _load_fixture(repo, POSITIVE_FIXTURE)
    positive_violations = fan_barrier_violations(positive)
    if positive_violations:
        detail = "\n".join(f"- {violation}" for violation in positive_violations)
        raise ProfileError(
            "kernel check graph_topology_fan_barrier rejected evidence: "
            f"positive barrier fixture was rejected:\n{detail}"
        )

    return KernelResult(
        check_id=CHECK_ID,
        inspected=2,
        output=(
            "graph topology fan barrier passed: negative no-barrier fixture "
            "RED-fired and positive explicit-barrier fixture was accepted. "
            + PROOF_LIMIT
        ),
    )
