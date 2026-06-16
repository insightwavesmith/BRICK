#!/usr/bin/env python3
"""Guard structural equivalence for future assembly.py lowering.

This checker is support evidence only. It compares compose_building outputs
through a canonical structural projection over hand-built graph fixtures. It
does not choose Movement, judge source truth, judge success or quality, or
claim semantic correctness of a Building.
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.operator.composition import CompositionError, compose_building


DEFAULT_GATE = "link-gate:default-transition"
STRICT_GATE = "link-gate:strict"
DECLARED_BY = "coo-heart-phase0-checker"
SELECTED_ADAPTER = "adapter:codex-local"
SOURCE_RETURN_SHAPE = "observed_evidence, not_proven"
BOUNDARY_PREFIXES = ("building-boundary:", "building-boundary-")
PROOF_LIMIT = (
    "proof limit: assembly equivalence checker support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement "
    "authority, assembly.py LHS equivalence while assembly.py is absent, or "
    "closure policy validity beyond structural discrimination."
)


class AssemblyEquivalenceError(ValueError):
    """Raised when the structural-equivalence guard does not bite."""


@dataclass(frozen=True)
class Fixture:
    name: str
    nodes: tuple[Mapping[str, Any], ...]
    edges: tuple[Mapping[str, Any], ...]
    groups: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class Projection:
    node_kinds: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]
    groups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    closure_policies: tuple[tuple[str, str, str, str | None, int | None], ...]
    gates: tuple[tuple[str, str, tuple[str, ...]], ...]
    agents: tuple[tuple[str, str], ...]
    fan_in_source_return_has_concern: tuple[tuple[str, bool], ...]


def _write_scope() -> Mapping[str, Any]:
    return {
        "allowed_paths": ["support/checkers/**"],
        "forbidden_paths": [
            ".git/**",
            "*.pem",
            "*.key",
            "AGENTS.md",
            "agent/**",
            "brick/**",
            "link/**",
            "support/operator/**",
        ],
    }


def _node(node_id: str, kind: str, **extra: Any) -> Mapping[str, Any]:
    node = {
        "node_id": node_id,
        "step_template_ref": f"building-step-template:{kind}",
        "work_statement": f"checker fixture work for {node_id}",
    }
    node.update(extra)
    return node


def _edge(
    edge_ref: str,
    source: str,
    target: str,
    *,
    gates: Sequence[str] | None = None,
    movement: str = "forward",
) -> Mapping[str, Any]:
    edge = {
        "edge_ref": edge_ref,
        "source": source,
        "target": target,
        "movement": movement,
    }
    if gates is not None:
        edge["declared_gate_refs"] = list(gates)
    return edge


def _group(group_id: str, role: str, member_refs: Sequence[str]) -> Mapping[str, Any]:
    return {
        "group_id": group_id,
        "group_role": role,
        "member_ref_kind": "link_edge",
        "member_refs": list(member_refs),
    }


def _closure_policy(target_ref: str) -> Mapping[str, Any]:
    return {
        "implementation_gap": {"action": "target", "target_ref": target_ref},
        "verification_gap": {"action": "hold"},
    }


def _fixtures() -> tuple[Fixture, ...]:
    default = (DEFAULT_GATE,)
    strict = (DEFAULT_GATE, STRICT_GATE)
    write = _write_scope()

    fast_fix = Fixture(
        name="fast-fix",
        nodes=(
            _node(
                "fast-fix-work",
                "work",
                write_scope=write,
                requires_brick_write_scope=True,
            ),
            _node("fast-fix-qa", "axis-attack-qa"),
            _node("fast-fix-closure", "closure"),
        ),
        edges=(
            _edge("edge:fast-work-qa", "fast-fix-work", "fast-fix-qa", gates=default),
            _edge("edge:fast-qa-closure", "fast-fix-qa", "fast-fix-closure", gates=strict),
            _edge(
                "edge:fast-closure-boundary",
                "fast-fix-closure",
                "building-boundary:closed",
                gates=default,
            ),
        ),
    )

    engine_hard = Fixture(
        name="engine-feature-hard",
        nodes=(
            _node(
                "hard-development",
                "development",
                completion_edge_ref="edge:hard-dev-code",
                node_reroute_budget=5,
            ),
            _node("hard-code", "code-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node("hard-axis", "axis-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node("hard-evidence", "evidence-integrity", required_return_shape=SOURCE_RETURN_SHAPE),
            _node(
                "hard-closure",
                "closure",
                closure_transition_target_policy=_closure_policy("hard-development"),
            ),
        ),
        edges=(
            _edge("edge:hard-dev-code", "hard-development", "hard-code", gates=default),
            _edge("edge:hard-dev-axis", "hard-development", "hard-axis", gates=default),
            _edge("edge:hard-dev-evidence", "hard-development", "hard-evidence", gates=default),
            _edge("edge:hard-code-closure", "hard-code", "hard-closure", gates=strict),
            _edge("edge:hard-axis-closure", "hard-axis", "hard-closure", gates=strict),
            _edge("edge:hard-evidence-closure", "hard-evidence", "hard-closure", gates=strict),
            _edge(
                "edge:hard-closure-boundary",
                "hard-closure",
                "building-boundary:closed",
                gates=default,
            ),
        ),
        groups=(
            _group(
                "group-hard-fanout",
                "fan_out",
                ("edge:hard-dev-code", "edge:hard-dev-axis", "edge:hard-dev-evidence"),
            ),
            _group(
                "group-hard-fanin",
                "fan_in",
                ("edge:hard-code-closure", "edge:hard-axis-closure", "edge:hard-evidence-closure"),
            ),
        ),
    )

    two_fan_in = Fixture(
        name="two-fan-in-graph",
        nodes=(
            _node(
                "two-inspect",
                "inspect",
                completion_edge_ref="edge:two-inspect-code-a",
                node_reroute_budget=1,
            ),
            _node("two-code-a", "code-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node("two-code-b", "code-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node("two-axis-a", "axis-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node("two-axis-b", "axis-attack-qa", required_return_shape=SOURCE_RETURN_SHAPE),
            _node(
                "two-mid",
                "closure",
                closure_transition_target_policy=_closure_policy("two-inspect"),
            ),
            _node(
                "two-final",
                "closure",
                closure_transition_target_policy=_closure_policy("two-inspect"),
            ),
        ),
        edges=(
            _edge("edge:two-inspect-code-a", "two-inspect", "two-code-a", gates=default),
            _edge("edge:two-inspect-code-b", "two-inspect", "two-code-b", gates=default),
            _edge("edge:two-inspect-axis-a", "two-inspect", "two-axis-a", gates=default),
            _edge("edge:two-inspect-axis-b", "two-inspect", "two-axis-b", gates=default),
            _edge("edge:two-code-a-mid", "two-code-a", "two-mid", gates=strict),
            _edge("edge:two-code-b-mid", "two-code-b", "two-mid", gates=strict),
            _edge("edge:two-mid-final", "two-mid", "two-final", gates=default),
            _edge("edge:two-axis-a-final", "two-axis-a", "two-final", gates=strict),
            _edge("edge:two-axis-b-final", "two-axis-b", "two-final", gates=strict),
            _edge("edge:two-final-boundary", "two-final", "building-boundary:closed", gates=default),
        ),
        groups=(
            _group(
                "group-two-fanout",
                "fan_out",
                (
                    "edge:two-inspect-code-a",
                    "edge:two-inspect-code-b",
                    "edge:two-inspect-axis-a",
                    "edge:two-inspect-axis-b",
                ),
            ),
            _group(
                "group-two-fanin-mid",
                "fan_in",
                ("edge:two-code-a-mid", "edge:two-code-b-mid"),
            ),
            _group(
                "group-two-fanin-final",
                "fan_in",
                ("edge:two-axis-a-final", "edge:two-axis-b-final"),
            ),
        ),
    )

    return (fast_fix, engine_hard, two_fan_in)


def _kind(step_template_ref: str) -> str:
    return str(step_template_ref).split(":", 1)[-1].strip()


def _link_row(edge: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = edge.get("rows")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)) and rows:
        row = rows[0]
        if isinstance(row, Mapping):
            return row
    return {}


def _brick_row(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)) and rows:
        row = rows[0]
        if isinstance(row, Mapping):
            return row
    return {}


def _agent_row(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)) and len(rows) > 1:
        row = rows[1]
        if isinstance(row, Mapping):
            return row
    return {}


def _boundary_label(target_ref: str) -> str:
    text = str(target_ref).strip()
    suffix = text.split(":", 1)[-1] if ":" in text else text.rsplit("-", 1)[-1]
    return f"BOUNDARY({suffix or 'unknown'})"


def _topological_steps(
    plan: Mapping[str, Any],
    step_kind: Mapping[str, str],
) -> tuple[str, ...]:
    steps = [str(step) for step in plan.get("execution_order", ()) if str(step) in step_kind]
    order_index = {step: index for index, step in enumerate(steps)}
    incoming = {step: 0 for step in steps}
    outgoing: dict[str, list[str]] = {step: [] for step in steps}
    for edge in plan.get("link_edges", ()):
        if not isinstance(edge, Mapping):
            continue
        source = str(edge.get("source_step_ref", "")).strip()
        target = str(edge.get("target_step_ref", "")).strip()
        if source in outgoing and target in incoming:
            outgoing[source].append(target)
            incoming[target] += 1

    ready = sorted(
        [step for step, count in incoming.items() if count == 0],
        key=lambda step: (step_kind[step], order_index[step]),
    )
    result: list[str] = []
    while ready:
        step = ready.pop(0)
        result.append(step)
        for target in outgoing.get(step, ()):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
        ready.sort(key=lambda item: (step_kind[item], order_index[item]))
    if len(result) != len(steps):
        return tuple(steps)
    return tuple(result)


def _canonical_labels(
    plan: Mapping[str, Any],
) -> tuple[Mapping[str, str], Mapping[str, str], tuple[str, ...]]:
    step_kind: dict[str, str] = {}
    for step in plan.get("brick_steps", ()):
        if not isinstance(step, Mapping):
            continue
        step_ref = str(step.get("step_ref", "")).strip()
        if step_ref:
            step_kind[step_ref] = _kind(str(step.get("step_template_ref", "")))

    topo = _topological_steps(plan, step_kind)
    counts = Counter(step_kind.values())
    seen: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}
    for step_ref in topo:
        kind = step_kind[step_ref]
        if counts[kind] == 1:
            labels[step_ref] = kind
            continue
        seen[kind] += 1
        labels[step_ref] = f"{kind}#{seen[kind]}"

    endpoint_to_label: dict[str, str] = {}
    for step in plan.get("brick_steps", ()):
        if not isinstance(step, Mapping):
            continue
        step_ref = str(step.get("step_ref", "")).strip()
        label = labels.get(step_ref)
        if not label:
            continue
        endpoint_to_label[step_ref] = label
        brick_ref = str(_brick_row(step).get("brick_instance_ref", "")).strip()
        if brick_ref:
            endpoint_to_label[brick_ref] = label
    return labels, endpoint_to_label, tuple(labels[step] for step in topo)


def _projection(plan: Mapping[str, Any], fixture: Fixture) -> Projection:
    labels, endpoint_to_label, node_kinds = _canonical_labels(plan)
    for raw_node in fixture.nodes:
        if not isinstance(raw_node, Mapping):
            continue
        raw_ref = str(raw_node.get("step_ref") or raw_node.get("node_id") or "").strip()
        label = endpoint_to_label.get(raw_ref)
        if label:
            endpoint_to_label[raw_ref] = label

    edge_by_ref: dict[str, tuple[str, str, str, tuple[str, ...], int]] = {}
    edges: list[tuple[str, str, str]] = []
    gates: list[tuple[str, str, tuple[str, ...]]] = []
    for index, edge in enumerate(plan.get("link_edges", ())):
        if not isinstance(edge, Mapping):
            continue
        source_step = str(edge.get("source_step_ref", "")).strip()
        source = labels.get(source_step, source_step)
        target_step = str(edge.get("target_step_ref", "")).strip()
        if target_step:
            target = labels.get(target_step, target_step)
        else:
            target = _boundary_label(str(_link_row(edge).get("target_ref", "")))
        movement = str(_link_row(edge).get("movement", "")).strip()
        gate_refs = tuple(sorted(set(str(ref) for ref in _link_row(edge).get("declared_gate_refs", ()))))
        edge_ref = str(edge.get("edge_ref", "")).strip()
        edge_by_ref[edge_ref] = (source, target, movement, gate_refs, index)
        edges.append((source, target, movement))
        gates.append((source, target, gate_refs))

    group_projection: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    fan_in_source_labels: set[str] = set()
    for group in plan.get("groups", ()):
        if not isinstance(group, Mapping):
            continue
        role = str(group.get("group_role", "")).strip()
        members: list[tuple[str, str]] = []
        raw_refs = group.get("member_refs", ())
        if isinstance(raw_refs, Sequence) and not isinstance(raw_refs, (str, bytes)):
            for raw_ref in raw_refs:
                edge_record = edge_by_ref.get(str(raw_ref).strip())
                if not edge_record:
                    continue
                source, target, _movement, _gates, _index = edge_record
                members.append((source, target))
                if role == "fan_in":
                    fan_in_source_labels.add(source)
        group_projection.append((role, tuple(sorted(members))))

    shape_by_label: dict[str, str] = {}
    agent_by_label: dict[str, str] = {}
    budget_by_label: dict[str, int] = {}
    raw_node_by_label: dict[str, Mapping[str, Any]] = {}
    for step in plan.get("brick_steps", ()):
        if not isinstance(step, Mapping):
            continue
        step_ref = str(step.get("step_ref", "")).strip()
        label = labels.get(step_ref)
        if not label:
            continue
        shape_by_label[label] = str(_brick_row(step).get("required_return_shape", "")).lower()
        agent_by_label[label] = str(_agent_row(step).get("agent_object_ref", "")).strip()
    for raw_node in fixture.nodes:
        if not isinstance(raw_node, Mapping):
            continue
        raw_ref = str(raw_node.get("step_ref") or raw_node.get("node_id") or "").strip()
        label = endpoint_to_label.get(raw_ref)
        if not label:
            continue
        raw_node_by_label[label] = raw_node
        raw_budget = raw_node.get("node_reroute_budget", raw_node.get("reroute_budget"))
        if isinstance(raw_budget, int) and raw_budget > 0:
            budget_by_label[label] = raw_budget
        elif isinstance(raw_budget, str) and raw_budget.strip().isdecimal():
            value = int(raw_budget)
            if value > 0:
                budget_by_label[label] = value

    closure_projection: list[tuple[str, str, str, str | None, int | None]] = []
    for closure_label, raw_node in raw_node_by_label.items():
        raw_policy = raw_node.get("closure_transition_target_policy")
        if not isinstance(raw_policy, Mapping):
            continue
        for concern_kind, row in sorted(raw_policy.items()):
            if not isinstance(row, Mapping):
                continue
            action = str(row.get("action", "")).strip()
            target_label: str | None = None
            raw_target = str(row.get("target_ref") or row.get("target_step_template_ref") or "").strip()
            if raw_target:
                target_label = endpoint_to_label.get(raw_target)
                if target_label is None:
                    target_kind = _kind(raw_target)
                    matches = [label for label, raw in raw_node_by_label.items() if _kind(str(raw.get("step_template_ref", ""))) == target_kind]
                    if len(matches) == 1:
                        target_label = matches[0]
            closure_projection.append(
                (
                    closure_label,
                    str(concern_kind).strip(),
                    action,
                    target_label,
                    budget_by_label.get(target_label or ""),
                )
            )

    return Projection(
        node_kinds=node_kinds,
        edges=tuple(sorted(edges)),
        groups=tuple(sorted(group_projection)),
        closure_policies=tuple(sorted(closure_projection)),
        gates=tuple(sorted(gates)),
        agents=tuple(sorted(agent_by_label.items())),
        fan_in_source_return_has_concern=tuple(
            sorted(
                (
                    label,
                    "transition_concern_evidence" in shape_by_label.get(label, ""),
                )
                for label in fan_in_source_labels
            )
        ),
    )


def _compose_fixture(repo: Path, fixture: Fixture, *, building_id: str | None = None) -> Mapping[str, Any]:
    try:
        return compose_building(
            fixture.nodes,
            fixture.edges,
            groups=fixture.groups,
            declared_by=DECLARED_BY,
            repo_root=repo,
            building_id=building_id or f"heart-phase0-{fixture.name}",
            selected_adapter_ref=SELECTED_ADAPTER,
        )
    except CompositionError as exc:
        raise AssemblyEquivalenceError(f"{fixture.name} compose_building rejected: {exc}") from exc


def _with_renamed_refs(fixture: Fixture) -> Fixture:
    mapping: dict[str, str] = {}
    for index, node in enumerate(fixture.nodes, start=1):
        old = str(node.get("node_id", "")).strip()
        mapping[old] = f"renamed-node-{index}"
    edge_mapping: dict[str, str] = {}
    for index, edge in enumerate(fixture.edges, start=1):
        old = str(edge.get("edge_ref", "")).strip()
        edge_mapping[old] = f"edge:renamed-{index}"

    nodes: list[Mapping[str, Any]] = []
    for node in copy.deepcopy(fixture.nodes):
        node = dict(node)
        old_id = str(node.get("node_id", "")).strip()
        if old_id:
            node["node_id"] = mapping[old_id]
        completion = str(node.get("completion_edge_ref", "")).strip()
        if completion in edge_mapping:
            node["completion_edge_ref"] = edge_mapping[completion]
        policy = node.get("closure_transition_target_policy")
        if isinstance(policy, Mapping):
            patched_policy: dict[str, Any] = {}
            for concern, row in policy.items():
                patched_row = dict(row) if isinstance(row, Mapping) else row
                if isinstance(patched_row, dict):
                    target_ref = str(patched_row.get("target_ref", "")).strip()
                    if target_ref in mapping:
                        patched_row["target_ref"] = mapping[target_ref]
                patched_policy[str(concern)] = patched_row
            node["closure_transition_target_policy"] = patched_policy
        nodes.append(node)

    edges: list[Mapping[str, Any]] = []
    for edge in copy.deepcopy(fixture.edges):
        edge = dict(edge)
        edge_ref = str(edge.get("edge_ref", "")).strip()
        if edge_ref in edge_mapping:
            edge["edge_ref"] = edge_mapping[edge_ref]
        source = str(edge.get("source", "")).strip()
        if source in mapping:
            edge["source"] = mapping[source]
        target = str(edge.get("target", "")).strip()
        if target in mapping:
            edge["target"] = mapping[target]
        edges.append(edge)

    groups: list[Mapping[str, Any]] = []
    for index, group in enumerate(copy.deepcopy(fixture.groups), start=1):
        group = dict(group)
        group["group_id"] = f"renamed-group-{index}"
        member_refs = group.get("member_refs", ())
        if isinstance(member_refs, Sequence) and not isinstance(member_refs, (str, bytes)):
            group["member_refs"] = [edge_mapping.get(str(ref), str(ref)) for ref in member_refs]
        groups.append(group)

    return Fixture(
        name=f"{fixture.name}-renamed",
        nodes=tuple(nodes),
        edges=tuple(edges),
        groups=tuple(groups),
    )


def _mutated_wrong_gate(fixture: Fixture) -> Fixture:
    edges = [dict(edge) for edge in copy.deepcopy(fixture.edges)]
    for edge in edges:
        if edge.get("edge_ref") == "edge:two-code-a-mid":
            edge["declared_gate_refs"] = [DEFAULT_GATE]
        if edge.get("edge_ref") == "edge:two-mid-final":
            edge["declared_gate_refs"] = [DEFAULT_GATE, STRICT_GATE]
    return Fixture(f"{fixture.name}-wrong-gate", fixture.nodes, tuple(edges), fixture.groups)


def _mutated_closure_flip(fixture: Fixture) -> Fixture:
    nodes = [dict(node) for node in copy.deepcopy(fixture.nodes)]
    for node in nodes:
        if node.get("node_id") == "two-mid":
            node["closure_transition_target_policy"] = {
                "implementation_gap": {"action": "hold"},
                "verification_gap": {"action": "target", "target_ref": "two-inspect"},
            }
    return Fixture(f"{fixture.name}-closure-flip", tuple(nodes), fixture.edges, fixture.groups)


def _mutated_missing_fan_in_group(fixture: Fixture) -> Fixture:
    groups = [
        group
        for group in copy.deepcopy(fixture.groups)
        if group.get("group_id") != "group-two-fanin-final"
    ]
    return Fixture(f"{fixture.name}-missing-fanin-group", fixture.nodes, fixture.edges, tuple(groups))


def _assert_projection_equal(left: Projection, right: Projection, label: str) -> None:
    if left != right:
        raise AssemblyEquivalenceError(f"{label}: expected structural projections to match")


def _assert_projection_differs(left: Projection, right: Projection, label: str) -> None:
    if left == right:
        raise AssemblyEquivalenceError(f"{label}: structural projection did not discriminate")


def _assembly_lhs_status(repo: Path) -> str:
    assembly_path = repo / "support" / "operator" / "assembly.py"
    if not assembly_path.is_file():
        return "advisory-skip: support/operator/assembly.py absent; LHS assembly equivalence deferred for Phase 1."
    raise AssemblyEquivalenceError(
        "support/operator/assembly.py is present; LHS assembly equivalence is now required "
        "and this Phase 0 checker must be wired to that front door before --all can pass."
    )


def run(repo: Path) -> list[str]:
    outputs: list[str] = []
    fixtures = {fixture.name: fixture for fixture in _fixtures()}
    projections: dict[str, Projection] = {}
    for fixture in fixtures.values():
        plan = _compose_fixture(repo, fixture)
        projection = _projection(plan, fixture)
        if any(has_concern for _label, has_concern in projection.fan_in_source_return_has_concern):
            raise AssemblyEquivalenceError(
                f"{fixture.name}: fan-in source required_return_shape still carries transition_concern_evidence"
            )
        projections[fixture.name] = projection
        outputs.append(
            "fixture accepted: "
            f"{fixture.name} nodes={len(plan.get('brick_steps', ()))}, "
            f"edges={len(plan.get('link_edges', ()))}, groups={len(plan.get('groups', ())) or 0}"
        )

    two = fixtures["two-fan-in-graph"]
    two_plan = _compose_fixture(repo, two)
    if len(two_plan.get("brick_steps", ())) != 7 or len(two_plan.get("groups", ())) != 3:
        raise AssemblyEquivalenceError("two-fan-in-graph fixture did not compose to 7 nodes and 3 groups")

    renamed = _with_renamed_refs(two)
    renamed_plan = _compose_fixture(repo, renamed, building_id="heart-phase0-renamed")
    _assert_projection_equal(
        projections["two-fan-in-graph"],
        _projection(renamed_plan, renamed),
        "renamed two-fan-in structural-equivalence green case",
    )
    outputs.append("discrimination green: renamed two-fan-in pair P(LHS)==P(RHS).")

    for mutation in (
        _mutated_wrong_gate(two),
        _mutated_closure_flip(two),
        _mutated_missing_fan_in_group(two),
    ):
        mutated_plan = _compose_fixture(repo, mutation, building_id=f"heart-phase0-{mutation.name}")
        _assert_projection_differs(
            projections["two-fan-in-graph"],
            _projection(mutated_plan, mutation),
            mutation.name,
        )
        outputs.append(f"discrimination RED observed: {mutation.name} changed P(plan).")

    outputs.append(_assembly_lhs_status(repo))
    outputs.append(PROOF_LIMIT)
    return outputs


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for structural equivalence of future assembly.py "
            "lowering against hand-built compose_building fixtures."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = run(repo)
    except AssemblyEquivalenceError as exc:
        print("assembly equivalence rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
