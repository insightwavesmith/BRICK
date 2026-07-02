#!/usr/bin/env python3
"""Guard structural equivalence for assembly.py authoring DSL lowering.

This checker is support evidence only. compose_building() is the permanent
canonical plan materializer; assemble() lowers to it internally as an authoring
DSL, not a rival or future-replacement engine. The checker compares outputs
through a canonical structural projection over hand-built graph fixtures. It
does not choose Movement, judge source truth, judge success or quality, or claim
semantic correctness of a Building.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
for _path in (str(_REPO_ROOT), str(_IMPORT_IDENTITY_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from brick_protocol.support.operator.assembly import (
    Authority,
    Concern,
    Gate,
    agent,
    assemble,
    back,
    brick,
    build,
    chain,
    converge,
    edge as assembly_edge,
    fan,
    fan_in,
    fan_out,
    hold,
    persist_proposed_building_graph,
    reroute,
)
from brick_protocol.support.connection.agent_resources import resolve_agent_object
from brick_protocol.support.operator.composition_problem import CompositionError
from brick_protocol.support.operator.composition_compose import compose_building
from brick_protocol.support.operator.plan_rendering import _resolve_agent_for_need
from brick_protocol.support.operator.primitives import CASTING_FIELDS


DEFAULT_GATE = "link-gate:default-transition"
STRICT_GATE = "link-gate:strict"
COO_GATE = "link-gate:coo"
HUMAN_GATE = "link-gate:human"
GOAL_PROPOSAL_FILENAME = "proposed-building-graph.json"
DECLARED_BY = "coo-heart-phase0-checker"
SELECTED_ADAPTER = "adapter:codex-local"
TINY_RETURN_SHAPE = "observed_evidence, not_proven"
CODE_ATTACK_RETURN_SHAPE = (
    "observed_evidence, attacked_work, checked_sources, regression_risks, "
    "negative_probe_observations, failing_or_missing_probes, boundary_violations, "
    "transition_concern_evidence, evidence_used, not_proven"
)
AXIS_ATTACK_RETURN_SHAPE = (
    "observed_evidence, attacked_scope, brick_axis_findings, agent_axis_findings, "
    "link_axis_findings, support_leak_findings, projection_authority_findings, "
    "transition_concern_evidence, evidence_used, not_proven"
)
EVIDENCE_INTEGRITY_RETURN_SHAPE = (
    "observed_evidence, evidence_scope, persisted_evidence_roots, proof_limit_findings, "
    "stale_source_risks, checker_overclaim_risks, missing_evidence, evidence_used, not_proven"
)
BOUNDARY_PREFIXES = ("building-boundary:", "building-boundary-")
PROOF_LIMIT = (
    "proof limit: assembly equivalence checker support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement "
    "authority, live Building execution, provider behavior, or closure policy "
    "semantic validity beyond structural discrimination."
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
            _node("hard-code", "code-attack-qa"),
            _node("hard-axis", "axis-attack-qa"),
            _node("hard-evidence", "evidence-integrity"),
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
            _node("two-code-a", "code-attack-qa"),
            _node("two-code-b", "code-attack-qa"),
            _node("two-axis-a", "axis-attack-qa"),
            _node("two-axis-b", "axis-attack-qa"),
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
            _edge("edge:two-inspect-code-a", "two-inspect", "two-code-a", gates=strict),
            _edge("edge:two-inspect-code-b", "two-inspect", "two-code-b", gates=strict),
            _edge("edge:two-inspect-axis-a", "two-inspect", "two-axis-a", gates=strict),
            _edge("edge:two-inspect-axis-b", "two-inspect", "two-axis-b", gates=strict),
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


def _step_for_kind(plan: Mapping[str, Any], kind: str) -> Mapping[str, Any]:
    matches = [
        step
        for step in plan.get("brick_steps", ())
        if isinstance(step, Mapping)
        and _kind(str(step.get("step_template_ref", ""))) == kind
    ]
    if len(matches) != 1:
        raise AssemblyEquivalenceError(f"expected exactly one {kind} step, observed {len(matches)}")
    return matches[0]


def _effective_step_adapter(plan: Mapping[str, Any], step: Mapping[str, Any]) -> str:
    return str(step.get("selected_adapter_ref") or plan.get("selected_adapter_ref") or "").strip()


def _effective_step_model(plan: Mapping[str, Any], step: Mapping[str, Any]) -> str:
    return str(step.get("selected_model_ref") or plan.get("selected_model_ref") or "").strip()


def _effective_step_ref(
    plan: Mapping[str, Any],
    step: Mapping[str, Any],
    field_name: str,
) -> str:
    if not field_name.startswith("preferred_"):
        raise AssemblyEquivalenceError(f"unknown Agent Object preferred field: {field_name}")
    selected_key = f"selected_{field_name.removeprefix('preferred_')}"
    return str(step.get(selected_key) or plan.get(selected_key) or "").strip()


def _preferred_ref(repo: Path, agent_object_ref: str, field_name: str) -> str:
    resolution = resolve_agent_object(agent_object_ref, repo_root=repo)
    agent_object = resolution.get("agent_object")
    if not isinstance(agent_object, Mapping):
        raise AssemblyEquivalenceError(f"{agent_object_ref} did not resolve an Agent Object")
    preferred = str(agent_object.get(field_name) or "").strip()
    if not preferred:
        # Constitution: only the fail-closed dial (adapter) is hard-required on a
        # role. A deferrable dial (model/effort, fail_closed=False) is OPTIONAL —
        # an omitted role preference defers to the dial's descriptor default, so
        # a role need not declare every casting field (no 8-role hand-sync).
        descriptor = next(
            (d for d in CASTING_FIELDS if d.field_name == field_name), None
        )
        if descriptor is not None and not descriptor.fail_closed and descriptor.default_ref:
            return descriptor.default_ref
        raise AssemblyEquivalenceError(f"{agent_object_ref} has no {field_name}")
    return preferred


def _preference_label(field_name: str) -> str:
    return field_name.removeprefix("preferred_").removesuffix("_ref")


def _assert_step_resolves_preference(
    repo: Path,
    plan: Mapping[str, Any],
    step: Mapping[str, Any],
    agent_object_ref: str,
    *,
    scenario: str,
    field_name: str,
) -> None:
    observed = _effective_step_ref(plan, step, field_name)
    expected = _preferred_ref(repo, agent_object_ref, field_name)
    label = _preference_label(field_name)
    if observed != expected:
        raise AssemblyEquivalenceError(
            f"{scenario} omitted {label} did not resolve the Agent Object preference: "
            f"observed {observed}, expected {expected}"
        )


def _repo_with_agent_preferred_model_omitted(repo: Path, role: str, root: Path) -> Path:
    """Create a temp repo projection with one Agent Object model preference omitted."""

    probe_repo = root / "repo"
    probe_repo.mkdir()
    for name in ("AGENTS.md", "brick", "link", "support", "project"):
        source = repo / name
        if source.exists():
            (probe_repo / name).symlink_to(source, target_is_directory=source.is_dir())

    source_agent = repo / "agent"
    probe_agent = probe_repo / "agent"
    probe_agent.mkdir()
    for child in sorted(source_agent.iterdir()):
        if child.name == "objects":
            continue
        (probe_agent / child.name).symlink_to(child, target_is_directory=child.is_dir())

    source_objects = source_agent / "objects"
    probe_objects = probe_agent / "objects"
    probe_objects.mkdir()
    for source in sorted(source_objects.glob("*.yaml")):
        target = probe_objects / source.name
        if source.stem == role:
            agent_object = json.loads(source.read_text(encoding="utf-8"))
            agent_object.pop("preferred_model_ref", None)
            target.write_text(json.dumps(agent_object, indent=2) + "\n", encoding="utf-8")
        else:
            target.symlink_to(source)
    return probe_repo


def _with_temp_home(root: Path):
    class _TempHome:
        def __enter__(self) -> Path:
            self._old_home = os.environ.get("HOME")
            self.home = root / "home"
            self.home.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(self.home)
            return self.home

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            if self._old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = self._old_home

    return _TempHome()


def _with_fixture_gemini_api_key():
    class _FixtureGeminiKey:
        def __enter__(self) -> None:
            from brick_protocol.support.connection.agent_adapter import _GEMINI_API_KEY_ENV_VARS

            self._names = tuple(_GEMINI_API_KEY_ENV_VARS)
            self._saved = {name: os.environ.get(name) for name in self._names}
            for name in self._names:
                os.environ.pop(name, None)
            os.environ["GEMINI_API_KEY"] = "checker-fixture-key"

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            for name in self._names:
                os.environ.pop(name, None)
                if self._saved[name] is not None:
                    os.environ[name] = self._saved[name]

    return _FixtureGeminiKey()


def _output_last_message_path(args: Sequence[str]) -> str | None:
    args = list(args)
    for index, value in enumerate(args):
        if value == "--output-last-message" and index + 1 < len(args):
            return args[index + 1]
    return None


def _is_gemini_json_invocation(args: Sequence[str]) -> bool:
    args = tuple(str(arg) for arg in args)
    for index, value in enumerate(args):
        if value == "--output-format" and index + 1 < len(args):
            return args[index + 1] == "json" and "-p" in args
    return False


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


def _assembly_lhs(repo: Path, fixture_name: str) -> tuple[Mapping[str, Any], Fixture]:
    graph = _assembly_graph(fixture_name)
    composed = assemble(
        graph,
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task=f"assembly equivalence task for {fixture_name}",
        building_id=f"heart-phase1-{fixture_name}",
        adapter="codex-local",
        gates=_assembly_gates(fixture_name),
        shape="design-needed" if fixture_name == "two-fan-in-graph" else None,
        repo_root=repo,
        write_scope=_write_scope(),
    )
    nodes, edges, groups = composed.as_compose_args()
    lhs_fixture = Fixture(
        name=f"{fixture_name}-assembly-lhs",
        nodes=tuple(nodes),
        edges=tuple(edges),
        groups=tuple(groups),
    )
    try:
        plan = compose_building(
            nodes,
            edges,
            groups=groups,
            declared_by=composed.declared_by,
            repo_root=repo,
            building_id=composed.building_id,
            selected_adapter_ref=composed.selected_adapter_ref,
            selected_model_ref=composed.selected_model_ref,
            selected_shape_ref=composed.selected_shape_ref,
            transition_concern_adoption=composed.transition_concern_adoption,
        )
    except CompositionError as exc:
        raise AssemblyEquivalenceError(f"{fixture_name} assembly LHS compose_building rejected: {exc}") from exc
    return plan, lhs_fixture


def _assembly_gates(fixture_name: str) -> tuple[Gate, ...]:
    if fixture_name in {"fast-fix", "engine-feature-hard", "two-fan-in-graph"}:
        return (Gate.STRICT_EVIDENCE, Gate.FAN_IN_WAIT_ALL) if fixture_name == "two-fan-in-graph" else (Gate.STRICT_EVIDENCE,)
    raise AssemblyEquivalenceError(f"no assembly gate fixture for {fixture_name}")


def _assembly_graph(fixture_name: str):
    if fixture_name == "fast-fix":
        work = brick("work", "checker fixture work for fast-fix-work", write=True)
        qa = brick("axis-attack-qa", "checker fixture work for fast-fix-qa")
        close = brick("closure", "checker fixture work for fast-fix-closure")
        return chain([work, qa, close])

    if fixture_name == "engine-feature-hard":
        dev = brick("development", "checker fixture work for hard-development")
        code = brick("code-attack-qa", "checker fixture work for hard-code", returns=CODE_ATTACK_RETURN_SHAPE)
        axis = brick("axis-attack-qa", "checker fixture work for hard-axis", returns=AXIS_ATTACK_RETURN_SHAPE)
        evidence = brick(
            "evidence-integrity",
            "checker fixture work for hard-evidence",
            returns=EVIDENCE_INTEGRITY_RETURN_SHAPE,
        )
        close = brick("closure", "checker fixture work for hard-closure")
        sources = [code, axis, evidence]
        return converge(
            fan_out(dev, sources),
            fan_in(
                sources,
                close,
                route=[
                    reroute(Concern.IMPLEMENTATION_GAP, to=dev, budget=5),
                    hold(Concern.VERIFICATION_GAP),
                ],
            ),
            terminal=close,
        )

    if fixture_name == "two-fan-in-graph":
        inspect = brick("inspect", "checker fixture work for two-inspect")
        code_a = brick(
            "code-attack-qa",
            "checker fixture work for two-code-a",
            alias="code-lens-a",
            returns=CODE_ATTACK_RETURN_SHAPE,
        )
        code_b = brick(
            "code-attack-qa",
            "checker fixture work for two-code-b",
            alias="code-lens-b",
            returns=CODE_ATTACK_RETURN_SHAPE,
        )
        axis_a = brick(
            "axis-attack-qa",
            "checker fixture work for two-axis-a",
            alias="axis-lens-a",
            returns=AXIS_ATTACK_RETURN_SHAPE,
        )
        axis_b = brick(
            "axis-attack-qa",
            "checker fixture work for two-axis-b",
            alias="axis-lens-b",
            returns=AXIS_ATTACK_RETURN_SHAPE,
        )
        mid = brick("closure", "checker fixture work for two-mid", alias="mid")
        final = brick("closure", "checker fixture work for two-final", alias="final")
        route = [
            reroute(Concern.IMPLEMENTATION_GAP, to=inspect, budget=1),
            hold(Concern.VERIFICATION_GAP),
        ]
        return converge(
            fan_out(inspect, [code_a, code_b, axis_a, axis_b]),
            fan_in([code_a, code_b], mid, route=route),
            assembly_edge(mid, final),
            fan_in([axis_a, axis_b], final, route=route),
            terminal=final,
        )

    raise AssemblyEquivalenceError(f"no assembly graph fixture for {fixture_name}")


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


def _assert_raises(label: str, exc_type: type[BaseException], fn: Any) -> str:
    try:
        fn()
    except exc_type:
        return f"construction RED observed: {label} raised {exc_type.__name__}."
    except Exception as exc:
        raise AssemblyEquivalenceError(
            f"{label}: expected {exc_type.__name__}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise AssemblyEquivalenceError(f"{label}: expected {exc_type.__name__} but no exception was raised")


def _tiny_work_qa_return_shape_red(repo: Path) -> str:
    nodes = (
        _node(
            "tiny-work",
            "work",
            write_scope=_write_scope(),
            requires_brick_write_scope=True,
            required_return_shape=TINY_RETURN_SHAPE,
        ),
        _node("tiny-qa", "code-attack-qa", required_return_shape=TINY_RETURN_SHAPE),
        _node("tiny-close", "closure"),
    )
    edges = (
        _edge("edge:tiny-work-qa", "tiny-work", "tiny-qa", gates=(DEFAULT_GATE,)),
        _edge("edge:tiny-qa-close", "tiny-qa", "tiny-close", gates=(STRICT_GATE,)),
        _edge("edge:tiny-close-boundary", "tiny-close", "building-boundary:closed", gates=(DEFAULT_GATE,)),
    )
    try:
        compose_building(
            nodes,
            edges,
            declared_by=DECLARED_BY,
            repo_root=repo,
            building_id="heart-phase0-tiny-return-shape-red",
            selected_adapter_ref=SELECTED_ADAPTER,
        )
    except CompositionError:
        return "discrimination RED observed: direct work/QA return-shape narrowing to observed_evidence, not_proven was rejected."
    raise AssemblyEquivalenceError(
        "direct work/QA return-shape narrowing to observed_evidence, not_proven was accepted"
    )


def _construction_red_outputs(repo: Path) -> tuple[str, ...]:
    def self_reroute_probe() -> None:
        source = brick("code-attack-qa", "source", returns=CODE_ATTACK_RETURN_SHAPE)
        close = brick("closure", "close")
        fan_in(
            [source],
            close,
            route=[reroute(Concern.IMPLEMENTATION_GAP, to=close, budget=1)],
        )

    def missing_returns_probe() -> None:
        source = brick("code-attack-qa", "source")
        close = brick("closure", "close")
        fan_in([source], close)

    def bad_terminal_probe() -> None:
        first = brick("inspect", "inspect")
        second = brick("closure", "close")
        converge(chain([first, second]), terminal=second)

    def declared_by_colon_probe() -> None:
        close = brick("closure", "close")
        assemble(
            chain([close]),
            declared_by="coo:smith",
            authority=Authority.COO,
            task="bad declared by probe",
            repo_root=repo,
        )

    def forbidden_input_probe() -> None:
        brick("work", "work", node_id="caller-owned-node")

    coo_probe = assemble(
        chain([brick("closure", "close")]),
        declared_by="smith",
        authority=Authority.COO,
        task="good declared by probe",
        adapter="codex-local",
        repo_root=repo,
    )
    if coo_probe.declared_by != "coo-smith":
        raise AssemblyEquivalenceError("declared_by smith + COO did not lower to coo-smith")

    return (
        _assert_raises("self-reroute", ValueError, self_reroute_probe),
        _assert_raises("fan-in source missing returns", TypeError, missing_returns_probe),
        _assert_raises("converge terminal not a fan-in target", ValueError, bad_terminal_probe),
        "construction green observed: declared_by smith + COO lowered to coo-smith.",
        _assert_raises("declared_by colon form", ValueError, declared_by_colon_probe),
        _assert_raises("forbidden derived brick input", TypeError, forbidden_input_probe),
    )


def _write_scope_derivation_fire(repo: Path) -> tuple[str, ...]:
    derived = assemble(
        chain([brick("work", "write scope is derived from the worktree boundary", write=True)]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="derived write scope probe",
        building_id="heart-phase0-derived-write-scope",
        adapter="codex-local",
        repo_root=repo,
    )
    work_step = _step_for_kind(derived.composed_plan, "work")
    brick_row = _brick_row(work_step)
    write_scope = brick_row.get("write_scope")
    if not isinstance(write_scope, Mapping):
        raise AssemblyEquivalenceError("derived write_scope was not recorded on the work Brick row")
    if write_scope.get("allowed_paths") != ["."]:
        raise AssemblyEquivalenceError(f"derived write_scope.allowed_paths escaped worktree boundary: {write_scope!r}")
    if write_scope.get("forbidden_paths") != [".git/**"]:
        raise AssemblyEquivalenceError(f"derived write_scope.forbidden_paths changed: {write_scope!r}")
    if brick_row.get("requires_brick_write_scope") is not True:
        raise AssemblyEquivalenceError("derived write_scope did not preserve requires_brick_write_scope=True")

    def malformed_write_scope_probe() -> None:
        assemble(
            chain([brick("work", "malformed write scope remains rejected", write=True)]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="malformed write scope probe",
            building_id="heart-phase0-malformed-write-scope",
            adapter="codex-local",
            repo_root=repo,
            write_scope={"allowed_paths": [], "forbidden_paths": []},
        )

    def parent_escape_write_scope_probe() -> None:
        assemble(
            chain(
                [
                    brick("development", "graph write scope parent escape setup"),
                    brick("work", "graph write scope parent escape is rejected", write=True),
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="parent escape write scope probe",
            building_id="heart-phase0-parent-escape-write-scope",
            adapter="codex-local",
            repo_root=repo,
            write_scope={"allowed_paths": [".."], "forbidden_paths": [".git/**"]},
        )

    def absolute_escape_write_scope_probe() -> None:
        assemble(
            chain(
                [
                    brick("development", "graph write scope absolute escape setup"),
                    brick("work", "graph write scope absolute escape is rejected", write=True),
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="absolute escape write scope probe",
            building_id="heart-phase0-absolute-escape-write-scope",
            adapter="codex-local",
            repo_root=repo,
            write_scope={"allowed_paths": ["/etc/passwd"], "forbidden_paths": [".git/**"]},
        )

    return (
        "construction green observed: write=True omitted write_scope derived worktree-bounded allowed_paths ['.'].",
        _assert_raises("malformed explicit write_scope", ValueError, malformed_write_scope_probe),
        _assert_raises("parent-escape explicit write_scope", ValueError, parent_escape_write_scope_probe),
        _assert_raises("absolute explicit write_scope", ValueError, absolute_escape_write_scope_probe),
    )


def _graph_write_scope_default_fire(repo: Path) -> tuple[str, ...]:
    explicit_scope = {
        "allowed_paths": ["support/checkers/**"],
        "forbidden_paths": [".git/**"],
    }
    default_plan = compose_building(
        nodes=(
            _node("graph-default-work", "work"),
        ),
        edges=(
            _edge(
                "edge:graph-default-work-boundary",
                "graph-default-work",
                "building-boundary:closed",
            ),
        ),
        declared_by=DECLARED_BY,
        building_id="heart-phase0-graph-default-write-scope",
        repo_root=repo,
    )
    default_row = _brick_row(default_plan["brick_steps"][0])
    default_scope = default_row.get("write_scope")
    if not isinstance(default_scope, Mapping):
        raise AssemblyEquivalenceError("graph compose omitted write_scope did not derive a scope for write-needed work")
    if default_scope.get("allowed_paths") != ["."]:
        raise AssemblyEquivalenceError(f"graph compose derived write_scope.allowed_paths changed: {default_scope!r}")
    if default_scope.get("forbidden_paths") != [".git/**"]:
        raise AssemblyEquivalenceError(f"graph compose derived write_scope.forbidden_paths changed: {default_scope!r}")
    if default_row.get("requires_brick_write_scope") is not True:
        raise AssemblyEquivalenceError("graph compose derived write_scope did not stamp requires_brick_write_scope=True")

    override_plan = compose_building(
        nodes=(
            _node(
                "graph-override-work",
                "work",
                write_scope=explicit_scope,
                requires_brick_write_scope=True,
            ),
        ),
        edges=(
            _edge(
                "edge:graph-override-work-boundary",
                "graph-override-work",
                "building-boundary:closed",
            ),
        ),
        declared_by=DECLARED_BY,
        building_id="heart-phase0-graph-override-write-scope",
        repo_root=repo,
    )
    override_scope = _brick_row(override_plan["brick_steps"][0]).get("write_scope")
    if override_scope != explicit_scope:
        raise AssemblyEquivalenceError(f"graph compose explicit write_scope did not override default: {override_scope!r}")

    return (
        "composition RED/GREEN observed: graph write-needed omitted write_scope derives worktree default.",
        "composition green observed: graph explicit node write_scope overrides derived default.",
    )


def _sibling_independence_dsl_fire(repo: Path) -> tuple[str, ...]:
    code = brick("code-attack-qa", "sibling independence code lens", returns=CODE_ATTACK_RETURN_SHAPE)
    axis = brick("axis-attack-qa", "sibling independence axis lens", returns=AXIS_ATTACK_RETURN_SHAPE)
    close = brick("closure", "sibling independence closure")
    composed = assemble(
        converge(
            fan_in([code, axis], close, sibling_independence=["code-attack-qa"]),
            terminal=close,
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="sibling independence DSL probe",
        building_id="heart-phase0-sibling-independence-dsl",
        adapter="codex-local",
        gates=(Gate.STRICT_EVIDENCE,),
        repo_root=repo,
        write_scope=_write_scope(),
    )
    _nodes, _edges, groups = composed.as_compose_args()
    observed = [group for group in groups if group.get("group_role") == "fan_in"]
    if len(observed) != 1:
        raise AssemblyEquivalenceError(f"sibling_independence probe expected one fan_in group, observed {len(observed)}")
    expected_ref = "heart-phase0-sibling-independence-dsl-code-attack-qa"
    if observed[0].get("sibling_independence") != [expected_ref]:
        raise AssemblyEquivalenceError(
            "sibling_independence did not lower to the fan_in source node ref: "
            f"{observed[0].get('sibling_independence')!r}"
        )

    build_composed = assemble(
        build(
            [
                ["development", "sibling independence build source"],
                fan(
                    [
                        ["code-attack-qa", "sibling independence build code lens"],
                        ["axis-attack-qa", "sibling independence build axis lens"],
                    ],
                    sibling_independence=["code-attack-qa"],
                ),
                ["closure", "sibling independence build closure"],
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="sibling independence build/fan probe",
        building_id="heart-phase0-sibling-independence-build",
        adapter="codex-local",
        gates=(Gate.STRICT_EVIDENCE,),
        repo_root=repo,
        write_scope=_write_scope(),
    )
    _build_nodes, _build_edges, build_groups = build_composed.as_compose_args()
    build_observed = [group for group in build_groups if group.get("group_role") == "fan_in"]
    if len(build_observed) != 1:
        raise AssemblyEquivalenceError(
            f"build()/fan() sibling_independence probe expected one fan_in group, observed {len(build_observed)}"
        )
    build_expected_ref = "heart-phase0-sibling-independence-build-code-attack-qa"
    if build_observed[0].get("sibling_independence") != [build_expected_ref]:
        raise AssemblyEquivalenceError(
            "build()/fan() sibling_independence did not survive easy-tier Fan rewrites: "
            f"{build_observed[0].get('sibling_independence')!r}"
        )

    def empty_ref_probe() -> None:
        fan_in([code, axis], close, sibling_independence=[" "])

    def non_source_ref_probe() -> None:
        fan_in([code, axis], close, sibling_independence=["closure"])

    return (
        "construction green observed: fan_in sibling_independence lowered to a fan_in source node ref.",
        "construction green observed: build()/fan() sibling_independence survived easy-tier Fan rewrites.",
        _assert_raises("empty sibling_independence ref", ValueError, empty_ref_probe),
        _assert_raises("non-source sibling_independence ref", ValueError, non_source_ref_probe),
    )


def _node_write_scope_fire(repo: Path) -> tuple[str, ...]:
    graph_scope = {
        "allowed_paths": ["support/checkers/**", "support/operator/**"],
        "forbidden_paths": [".git/**", "support/operator/secret-*"],
    }
    node_scope = {
        "allowed_paths": ["support/checkers/check_assembly_equivalence.py"],
        "forbidden_paths": [".git/**", "support/operator/secret-*"],
    }
    composed = assemble(
        chain(
            [
                brick(
                    "work",
                    "node write scope narrowing work",
                    write=True,
                    node_write_scope=node_scope,
                )
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="node write scope DSL probe",
        building_id="heart-phase0-node-write-scope-dsl",
        adapter="codex-local",
        repo_root=repo,
        write_scope=graph_scope,
    )
    work_row = _brick_row(_step_for_kind(composed.composed_plan, "work"))
    if work_row.get("write_scope") != node_scope:
        raise AssemblyEquivalenceError(f"node_write_scope did not stamp the Brick row: {work_row.get('write_scope')!r}")
    if work_row.get("requires_brick_write_scope") is not True:
        raise AssemblyEquivalenceError("node_write_scope did not preserve requires_brick_write_scope=True")

    def read_only_probe() -> None:
        brick("work", "node scope requires write true", node_write_scope=node_scope)

    def no_template_need_probe() -> None:
        assemble(
            chain([brick("development", "development has no write need", write=True, node_write_scope=node_scope)]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node write scope no template need probe",
            building_id="heart-phase0-node-write-scope-no-template-need",
            adapter="codex-local",
            repo_root=repo,
            write_scope=graph_scope,
        )

    def malformed_probe() -> None:
        assemble(
            chain([brick("work", "malformed node scope", write=True, node_write_scope={"allowed_paths": []})]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node write scope malformed probe",
            building_id="heart-phase0-node-write-scope-malformed",
            adapter="codex-local",
            repo_root=repo,
            write_scope=graph_scope,
        )

    def widening_probe() -> None:
        assemble(
            chain(
                [
                    brick(
                        "work",
                        "node scope must not widen graph scope",
                        write=True,
                        node_write_scope={
                            "allowed_paths": ["brick/spec.py"],
                            "forbidden_paths": [".git/**", "support/operator/secret-*"],
                        },
                    )
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node write scope widening probe",
            building_id="heart-phase0-node-write-scope-widening",
            adapter="codex-local",
            repo_root=repo,
            write_scope=graph_scope,
        )

    def default_scope_widening_probe() -> None:
        assemble(
            chain(
                [
                    brick(
                        "work",
                        "node scope must not widen omitted graph scope",
                        write=True,
                        node_write_scope={
                            "allowed_paths": [".."],
                            "forbidden_paths": [".git/**"],
                        },
                    )
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node write scope default graph widening probe",
            building_id="heart-phase0-node-write-scope-default-widening",
            adapter="codex-local",
            repo_root=repo,
        )

    return (
        "construction green observed: node_write_scope narrowed a write-needed Brick row.",
        _assert_raises("node_write_scope on write=False brick", ValueError, read_only_probe),
        _assert_raises("node_write_scope on template without write_need", ValueError, no_template_need_probe),
        _assert_raises("malformed node_write_scope", ValueError, malformed_probe),
        _assert_raises("node_write_scope wider than graph write_scope", ValueError, widening_probe),
        _assert_raises(
            "node_write_scope wider than omitted graph write_scope default",
            ValueError,
            default_scope_widening_probe,
        ),
    )


def _gate_sequence_policy_for_edge(
    plan: Mapping[str, Any],
    *,
    source_kind: str,
    target_kind: str,
) -> tuple[Mapping[str, Any], ...]:
    labels, _endpoint_to_label, _node_kinds = _canonical_labels(plan)
    for edge in plan.get("link_edges", ()):
        if not isinstance(edge, Mapping):
            continue
        source_label = labels.get(str(edge.get("source_step_ref", "")).strip())
        target_label = labels.get(str(edge.get("target_step_ref", "")).strip())
        if source_label != source_kind or target_label != target_kind:
            continue
        policy = _link_row(edge).get("gate_sequence_policy")
        if not isinstance(policy, Sequence) or isinstance(policy, (str, bytes)):
            raise AssemblyEquivalenceError(
                f"{source_kind}->{target_kind} did not carry a gate_sequence_policy"
            )
        return tuple(item for item in policy if isinstance(item, Mapping))
    raise AssemblyEquivalenceError(f"{source_kind}->{target_kind} edge was not present")


def _declared_gate_refs_for_edge(
    plan: Mapping[str, Any],
    *,
    source_kind: str,
    target_kind: str,
) -> tuple[str, ...]:
    labels, _endpoint_to_label, _node_kinds = _canonical_labels(plan)
    for edge in plan.get("link_edges", ()):
        if not isinstance(edge, Mapping):
            continue
        source_label = labels.get(str(edge.get("source_step_ref", "")).strip())
        target_label = labels.get(str(edge.get("target_step_ref", "")).strip())
        if source_label != source_kind or target_label != target_kind:
            continue
        declared_refs = _link_row(edge).get("declared_gate_refs")
        if not isinstance(declared_refs, Sequence) or isinstance(declared_refs, (str, bytes)):
            raise AssemblyEquivalenceError(f"{source_kind}->{target_kind} did not carry declared_gate_refs")
        return tuple(str(item).strip() for item in declared_refs)
    raise AssemblyEquivalenceError(f"{source_kind}->{target_kind} edge was not present")


def _assert_gate_sequence_policy_equivalent_to_engine_preset(
    policy: Sequence[Mapping[str, Any]],
    *,
    expected_gate_ref: str,
    expected_owner: str,
) -> None:
    expected_reason = (
        "observation:coo-gate-missing-required-facts"
        if expected_gate_ref == COO_GATE
        else "observation:human-gate-disposition-missing"
    )
    expected = (
        {
            "gate_ref": DEFAULT_GATE,
            "on_missing_required_facts": {
                "action": "reroute",
                "reason_refs": ["observation:default-transition-missing-required-facts"],
                "required_target_budget": True,
                "target_basis": "source_brick",
            },
            "on_sufficient": {
                "action": "next",
                "next_gate_ref": expected_gate_ref,
            },
        },
        {
            "gate_ref": expected_gate_ref,
            "on_missing_required_facts": {
                "action": "HOLD",
                "pending_target_basis": "target_brick",
                "reason_refs": [expected_reason],
                "required_disposition_owner": expected_owner,
            },
            "on_sufficient": {"action": "forward"},
        },
    )
    if tuple(policy) != expected:
        raise AssemblyEquivalenceError(
            "node gates policy did not match the engine-feature-hard gate_sequence_policy shape: "
            f"{tuple(policy)!r}"
        )


def _node_gates_fire(repo: Path) -> tuple[str, ...]:
    composed = assemble(
        build(
            [
                brick("design", "node-level COO gate design", gates=("coo-review",)),
                brick("work", "node-level COO gate work", write=True),
                brick("closure", "node-level COO gate closure"),
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="node gate sequence DSL probe",
        building_id="heart-phase0-node-gates-dsl",
        adapter="codex-local",
        repo_root=repo,
    )
    policy = _gate_sequence_policy_for_edge(
        composed.composed_plan,
        source_kind="design",
        target_kind="work",
    )
    _assert_gate_sequence_policy_equivalent_to_engine_preset(
        policy,
        expected_gate_ref=COO_GATE,
        expected_owner="coo",
    )

    human_composed = assemble(
        build(
            [
                brick("design", "node-level human gate design", gates=(Gate.HUMAN_REVIEW,)),
                brick("work", "node-level human gate work", write=True),
                brick("closure", "node-level human gate closure"),
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="node human gate sequence DSL probe",
        building_id="heart-phase0-node-human-gates-dsl",
        adapter="codex-local",
        repo_root=repo,
    )
    human_policy = _gate_sequence_policy_for_edge(
        human_composed.composed_plan,
        source_kind="design",
        target_kind="work",
    )
    _assert_gate_sequence_policy_equivalent_to_engine_preset(
        human_policy,
        expected_gate_ref=HUMAN_GATE,
        expected_owner="caller-or-coo",
    )

    strict_and_coo_composed = assemble(
        chain(
            [
                brick(
                    "code-attack-qa",
                    "graph strict plus node coo source",
                    returns=CODE_ATTACK_RETURN_SHAPE,
                    gates=("coo-review",),
                ),
                brick("closure", "graph strict plus node coo closure"),
            ]
        ),
        gates=(Gate.STRICT_EVIDENCE,),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="node coo gate must preserve graph strict sequence probe",
        building_id="heart-phase0-node-coo-preserves-strict",
        adapter="codex-local",
        repo_root=repo,
    )
    strict_and_coo_policy = _gate_sequence_policy_for_edge(
        strict_and_coo_composed.composed_plan,
        source_kind="code-attack-qa",
        target_kind="closure",
    )
    strict_and_coo_refs = tuple(
        str(item.get("gate_ref", "")).strip()
        for item in strict_and_coo_policy
        if isinstance(item, Mapping)
    )
    if strict_and_coo_refs != (DEFAULT_GATE, STRICT_GATE, COO_GATE):
        raise AssemblyEquivalenceError(
            "node coo gate merge did not preserve every declared gate in gate_sequence_policy: "
            f"{strict_and_coo_refs!r}"
        )

    def no_outgoing_probe() -> None:
        assemble(
            build([brick("closure", "terminal node gate has no completion edge", gates=("coo-review",))]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node gate zero outgoing probe",
            building_id="heart-phase0-node-gates-zero-outgoing",
            adapter="codex-local",
            repo_root=repo,
        )

    def ambiguous_outgoing_probe() -> None:
        design = brick("design", "fan-out node gate is ambiguous", gates=("coo-review",))
        code = brick("code-attack-qa", "ambiguous code lens", returns=CODE_ATTACK_RETURN_SHAPE)
        axis = brick("axis-attack-qa", "ambiguous axis lens", returns=AXIS_ATTACK_RETURN_SHAPE)
        close = brick("closure", "ambiguous close")
        assemble(
            converge(
                fan_out(design, [code, axis]),
                fan_in([code, axis], close),
                terminal=close,
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node gate multi outgoing probe",
            building_id="heart-phase0-node-gates-multi-outgoing",
            adapter="codex-local",
            repo_root=repo,
        )

    def unknown_gate_probe() -> None:
        assemble(
            build(
                [
                    brick("design", "unknown node gate", gates=("unknown-review",)),
                    brick("work", "unknown node gate work", write=True),
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="node gate unknown token probe",
            building_id="heart-phase0-node-gates-unknown",
            adapter="codex-local",
            repo_root=repo,
        )

    return (
        "construction green observed: brick(..., gates=('coo-review',)) stamped design->work gate_sequence_policy equivalent to engine-feature-hard.",
        "construction green observed: brick(..., gates=(Gate.HUMAN_REVIEW,)) stamped a default-transition-first human hold sequence.",
        "construction green observed: graph strict-evidence plus node coo-review preserved strict in gate_sequence_policy.",
        _assert_raises("node gates on terminal node", ValueError, no_outgoing_probe),
        _assert_raises("node gates on fan-out node", ValueError, ambiguous_outgoing_probe),
        _assert_raises("unknown node gate token", ValueError, unknown_gate_probe),
    )


def _role_derivation_fire(repo: Path) -> tuple[str, ...]:
    work_default = assemble(
        chain([brick("work", "omitted agent resolves from kind", write=True)]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="role from kind single candidate probe",
        building_id="heart-phase0-role-from-kind",
        adapter="codex-local",
        repo_root=repo,
    )
    work_agent_ref = str(_agent_row(_step_for_kind(work_default.composed_plan, "work")).get("agent_object_ref", ""))
    if work_agent_ref != "agent-object:dev":
        raise AssemblyEquivalenceError(f"work kind omitted agent did not resolve dev: {work_agent_ref}")

    def ambiguous_need_probe() -> None:
        _resolve_agent_for_need(repo, "leader", False)

    def development_override_probe() -> None:
        assemble(
            chain([brick("development", "development stays CTO-only", agent=agent("coo"))]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="development CTO-only probe",
            building_id="heart-phase0-development-cto-only",
            adapter="codex-local",
            repo_root=repo,
        )

    return (
        "construction green observed: omitted work agent resolved from kind to agent-object:dev.",
        _assert_raises("ambiguous leader NEED without hint", ValueError, ambiguous_need_probe),
        _assert_raises("development CTO-only override", CompositionError, development_override_probe),
    )


def _verdict_adapter_guard_fire(repo: Path) -> tuple[str, ...]:
    def explicit_local_closure_probe() -> None:
        assemble(
            chain(
                [
                    brick("work", "local smoke work remains admissible"),
                    brick("closure", "explicit local closure must stay rejected", adapter="local"),
                ]
            ),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="explicit verdict local adapter guard probe",
            building_id="heart-phase0-explicit-verdict-local-guard",
            repo_root=repo,
        )

    def explicit_local_reviewer_probe() -> None:
        assemble(
            chain([brick("axis-attack-qa", "explicit local reviewer stays rejected", adapter="local")]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="explicit reviewer local adapter guard probe",
            building_id="heart-phase0-explicit-reviewer-local-guard",
            repo_root=repo,
        )

    default_closure = assemble(
        chain(
            [
                brick("work", "default local work remains admissible"),
                brick("closure", "omitted closure adapter defaults non-local"),
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="verdict omitted adapter default probe",
        building_id="heart-phase0-verdict-default-non-local",
        repo_root=repo,
    )
    closure_step = _step_for_kind(default_closure.composed_plan, "closure")
    closure_agent = str(_agent_row(closure_step).get("agent_object_ref", "")).strip()
    if closure_agent != "agent-object:coo":
        raise AssemblyEquivalenceError(f"closure omitted agent did not resolve coo: {closure_agent}")
    for descriptor in CASTING_FIELDS:
        _assert_step_resolves_preference(
            repo,
            default_closure.composed_plan,
            closure_step,
            closure_agent,
            scenario="closure",
            field_name=descriptor.field_name,
        )

    default_reviewer = assemble(
        chain([brick("axis-attack-qa", "omitted reviewer adapter defaults non-local")]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="reviewer omitted adapter default probe",
        building_id="heart-phase0-reviewer-default-non-local",
        repo_root=repo,
    )
    reviewer_step = _step_for_kind(default_reviewer.composed_plan, "axis-attack-qa")
    reviewer_agent = str(_agent_row(reviewer_step).get("agent_object_ref", "")).strip()
    for descriptor in CASTING_FIELDS:
        _assert_step_resolves_preference(
            repo,
            default_reviewer.composed_plan,
            reviewer_step,
            reviewer_agent,
            scenario="reviewer",
            field_name=descriptor.field_name,
        )

    local_smoke = assemble(
        chain([brick("work", "non-verdict local smoke remains admissible")]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="non-verdict local adapter smoke probe",
        building_id="heart-phase0-non-verdict-local-smoke",
        repo_root=repo,
    )
    if local_smoke.selected_adapter_ref != "adapter:local":
        raise AssemblyEquivalenceError("non-verdict local smoke did not preserve adapter:local")
    work_step = _step_for_kind(local_smoke.composed_plan, "work")
    work_agent = str(_agent_row(work_step).get("agent_object_ref", "")).strip()
    for descriptor in CASTING_FIELDS:
        _assert_step_resolves_preference(
            repo,
            local_smoke.composed_plan,
            work_step,
            work_agent,
            scenario="non-verdict omitted work",
            field_name=descriptor.field_name,
        )

    explicit_model = assemble(
        chain([brick("work", "explicit step model must beat role preference", model="model:codex:gpt-explicit")]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="explicit step model preference precedence probe",
        building_id="heart-phase1a-explicit-model-precedence",
        repo_root=repo,
    )
    explicit_model_step = _step_for_kind(explicit_model.composed_plan, "work")
    explicit_observed_model = _effective_step_model(explicit_model.composed_plan, explicit_model_step)
    if explicit_observed_model != "model:codex:gpt-explicit":
        raise AssemblyEquivalenceError(
            "explicit step model did not override the Agent Object preference: "
            f"observed {explicit_observed_model}"
        )

    with tempfile.TemporaryDirectory(prefix="bp-preferred-model-omitted-") as tmp_raw:
        omitted_repo = _repo_with_agent_preferred_model_omitted(repo, "coo", Path(tmp_raw))
        omitted_preference = assemble(
            chain([brick("closure", "omitted role model keeps existing adapter default stamp")]),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="omitted preferred model fallback probe",
            building_id="heart-phase1a-omitted-preferred-model",
            repo_root=omitted_repo,
        )
    omitted_step = _step_for_kind(omitted_preference.composed_plan, "closure")
    omitted_model = _effective_step_model(omitted_preference.composed_plan, omitted_step)
    if omitted_model != "model:default":
        raise AssemblyEquivalenceError(
            "role without preferred_model_ref did not preserve existing model default: "
            f"observed {omitted_model}"
        )

    parity_assembly = assemble(
        chain([brick("closure", "assembly and direct compose adapter parity")]),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="assemble direct compose adapter parity probe",
        building_id="heart-phase0-assemble-compose-adapter-parity",
        repo_root=repo,
    )
    parity_nodes, parity_edges, parity_groups = parity_assembly.as_compose_args()
    try:
        parity_direct = compose_building(
            parity_nodes,
            parity_edges,
            groups=parity_groups,
            declared_by=parity_assembly.declared_by,
            repo_root=repo,
            building_id=parity_assembly.building_id,
            selected_adapter_ref=parity_assembly.selected_adapter_ref,
            selected_model_ref=parity_assembly.selected_model_ref,
            selected_shape_ref=parity_assembly.selected_shape_ref,
            transition_concern_adoption=parity_assembly.transition_concern_adoption,
        )
    except CompositionError as exc:
        raise AssemblyEquivalenceError(f"adapter parity direct compose rejected: {exc}") from exc
    parity_assembly_step = _step_for_kind(parity_assembly.composed_plan, "closure")
    parity_direct_step = _step_for_kind(parity_direct, "closure")
    parity_assembly_adapter = _effective_step_adapter(
        parity_assembly.composed_plan,
        parity_assembly_step,
    )
    parity_direct_adapter = _effective_step_adapter(parity_direct, parity_direct_step)
    if parity_assembly_adapter != parity_direct_adapter:
        raise AssemblyEquivalenceError(
            "assemble and direct compose selected different closure adapters: "
            f"assemble {parity_assembly_adapter}, direct {parity_direct_adapter}"
        )

    explicit_adapter = assemble(
        chain(
            [
                brick("work", "explicit non-local work"),
                brick("closure", "explicit non-local closure"),
            ]
        ),
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task="verdict non-local adapter guard probe",
        building_id="heart-phase0-verdict-non-local-guard",
        adapter="codex-local",
        repo_root=repo,
    )
    if explicit_adapter.selected_adapter_ref != "adapter:codex-local":
        raise AssemblyEquivalenceError("explicit non-local adapter was not preserved")

    return (
        "construction green observed: omitted closure adapter resolved the Agent Object preference.",
        "construction green observed: omitted reviewer adapter resolved the Agent Object preference.",
        _assert_raises("explicit closure local adapter", ValueError, explicit_local_closure_probe),
        _assert_raises("explicit reviewer local adapter", ValueError, explicit_local_reviewer_probe),
        "construction green observed: non-verdict omitted work adapter resolved through the shared preference seam.",
        "construction green observed: omitted model nodes resolved Agent Object preferred_model_ref through the shared seam.",
        "construction green observed: explicit step selected_model_ref beat Agent Object preferred_model_ref.",
        "construction green observed: role without preferred_model_ref preserved existing model:default fallback.",
        "construction green observed: assemble and direct compose selected the same verdict adapter.",
        "construction green observed: explicit non-local adapter preserved for verdict node.",
    )


def _approval_runner():
    """Deterministic codex-local stand-in for frozen proposal FIRE runs."""

    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        payload = {
            "assignment_summary": ["assigned the deterministic proposal check"],
            "worker_brick_boundaries": ["brick-boundary:proposal-fire"],
            "write_scope_requirements": ["no live provider write in checker"],
            "risk_boundaries": ["support evidence only"],
            "required_verification": ["checker FIRE"],
            "received_work_ref": "work:proposal-fire",
            "made_changes": True,
            "changed_files": [],
            "commands_run": ["deterministic checker runner"],
            "blocked_or_missing_evidence": [],
            "handoff_refs": ["handoff:proposal-fire"],
            "inspected_scope": "frozen proposal approval seam",
            "matched_facts": ["proposal was frozen before approval"],
            "missing_facts": [],
            "mismatched_facts": [],
            "boundary_findings": [],
            "observed_evidence": ["walked frozen proposal with deterministic runner"],
            "attacked_work": ["frozen proposal approval seam"],
            "checked_sources": ["support/operator/assembly.py", "support/operator/onboard.py"],
            "regression_risks": [],
            "negative_probe_observations": ["raise and tampered proposal rejected"],
            "failing_or_missing_probes": [],
            "boundary_violations": [],
            "attacked_scope": "pre-run approval support seam",
            "brick_axis_findings": ["Building Plan remains the frozen Brick-owned road"],
            "agent_axis_findings": ["AgentFact return stays closed"],
            "link_axis_findings": ["approval action is caller/human supplied"],
            "support_leak_findings": [],
            "projection_authority_findings": [],
            "evidence_used": ["support/operator/onboard.py", "support/operator/assembly.py"],
            "narrowly_proven": ["the frozen proposal path was executed by run_building_plan"],
            "remaining_delta": ["live Smith approval dogfood is outside this checker"],
            "parent_goal_delta_status": {
                "matched_delta_refs": ["delta:frozen-plan-forward"],
                "closed_delta_refs": [],
                "open_delta_refs": [],
                "missing_delta_refs": [],
                "unknown_delta_refs": [],
                "evidence_refs": ["checker:assembly-equivalence"],
            },
            "next_target_candidates": ["candidate:operator-dogfood"],
            "deferred_smith_review_queue": [],
            "transition_concern_evidence": "",
            "not_proven": ["semantic correctness of real provider work"],
        }
        assistant_text = json.dumps(payload, sort_keys=True)
        output_path = _output_last_message_path(call)
        if output_path is not None:
            Path(output_path).write_text(assistant_text, encoding="utf-8")
            stdout = (
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 12,
                            "cached_input_tokens": 3,
                            "output_tokens": 4,
                            "reasoning_output_tokens": 5,
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        elif _is_gemini_json_invocation(call):
            stdout = json.dumps(
                {
                    "response": assistant_text,
                    "stats": {"tools": {"byName": {}}},
                },
                sort_keys=True,
            )
        else:
            stdout = assistant_text
        return LocalCliCompleted(call, 0, stdout, "")

    return _runner


def _approval_simple_graph():
    inspect = brick("inspect", "inspect frozen proposal before approval")
    close = brick("closure", "close frozen proposal approval evidence")
    return chain([inspect, close])


def _assert_no_building_root(root: Path, building_id: str, label: str) -> None:
    if (root / building_id).exists():
        raise AssemblyEquivalenceError(f"{label}: unexpected Building root was written")


def _proposal_approval_fire(repo: Path) -> tuple[str, ...]:
    from brick_protocol.support.operator.onboard import (
        build,
        render_proposal_for_human,
        run_goal_approve_entry,
    )

    outputs: list[str] = []
    with tempfile.TemporaryDirectory(prefix="bp-heart-p5-") as tmp_raw, _with_fixture_gemini_api_key():
        tmp = Path(tmp_raw)
        probe_repo = tmp / "not-a-git-repo"
        probe_repo.mkdir()
        proposal_root = tmp / "proposals"
        run_root = tmp / "runs"
        stop_root = tmp / "stops"

        simple = assemble(
            _approval_simple_graph(),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="frozen proposal approval checker task",
            building_id="heart-phase5-simple-approval",
            adapter="codex-local",
            repo_root=repo,
        )
        proposal_path = persist_proposed_building_graph(
            simple,
            proposal_root,
            overwrite=True,
        )
        loaded = json.loads(proposal_path.read_text(encoding="utf-8"))
        if loaded.get("building_id") != simple.building_id:
            raise AssemblyEquivalenceError("proposal snapshot did not preserve building_id")
        if not loaded.get("task_statement") or not loaded.get("task_source_ref"):
            raise AssemblyEquivalenceError("proposal snapshot did not carry inline task source")
        _assert_no_building_root(run_root, simple.building_id, "unapproved proposal")
        outputs.append("proposal green: snapshot persisted without running a Building root.")

        stop = run_goal_approve_entry(
            proposal_path,
            action="stop",
            author_ref="coo:smith",
            output_root=stop_root,
            repo_root=probe_repo,
        )
        if stop.get("ran") is not False or not stop.get("ok"):
            raise AssemblyEquivalenceError(f"stop approval did not return ran False: {stop!r}")
        _assert_no_building_root(stop_root, simple.building_id, "stop approval")
        outputs.append("proposal green: stop approval ran nothing and wrote no Building root.")

        raise_result = run_goal_approve_entry(
            proposal_path,
            action="raise",
            author_ref="coo:smith",
            output_root=run_root,
            repo_root=probe_repo,
        )
        if raise_result.get("ran") is not False or raise_result.get("error_kind") != "invalid_goal_approve_action":
            raise AssemblyEquivalenceError(f"raise approval was not rejected: {raise_result!r}")
        _assert_no_building_root(run_root, simple.building_id, "raise rejection")
        outputs.append("proposal RED observed: pre-run raise action rejected.")

        tampered = json.loads(json.dumps(loaded))
        tampered.pop("task_statement", None)
        tampered_result = run_goal_approve_entry(
            tampered,
            action="forward",
            author_ref="coo:smith",
            output_root=run_root,
            repo_root=probe_repo,
            command_runner=_approval_runner(),
        )
        if tampered_result.get("ran") is not False or not tampered_result.get("error_kind"):
            raise AssemblyEquivalenceError(f"tampered proposal was not rejected: {tampered_result!r}")
        _assert_no_building_root(run_root, simple.building_id, "tampered rejection")
        outputs.append("proposal RED observed: missing task_statement snapshot rejected before run.")

        default_root_graph = assemble(
            _approval_simple_graph(),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="default-root frozen approval checker task",
            building_id="heart-phase5-default-root-approval",
            adapter="codex-local",
            repo_root=repo,
        )
        default_path = persist_proposed_building_graph(
            default_root_graph,
            tmp / "default-proposals",
            overwrite=True,
        )
        default_forward = run_goal_approve_entry(
            default_path,
            action="forward",
            author_ref="coo:smith",
            repo_root=probe_repo,
            command_runner=_approval_runner(),
            adapter_timeout_seconds=30,
        )
        if (
            not default_forward.get("ran")
            or default_forward.get("frontier_kind") != "complete"
            or not default_forward.get("proposal_root_reused")
        ):
            raise AssemblyEquivalenceError(
                f"default-root forward approval did not reuse proposal root: {default_forward!r}"
            )
        outputs.append("proposal green: default approval reused pre-run-only proposal root.")

        forward = run_goal_approve_entry(
            proposal_path,
            action="forward",
            author_ref="coo:smith",
            output_root=run_root,
            repo_root=probe_repo,
            overwrite_existing=True,
            command_runner=_approval_runner(),
            adapter_timeout_seconds=30,
        )
        if not forward.get("ran") or forward.get("frontier_kind") != "complete":
            raise AssemblyEquivalenceError(f"forward approval did not complete: {forward!r}")
        if Path(str(forward.get("plan_path"))).resolve() != proposal_path.resolve():
            raise AssemblyEquivalenceError("forward approval did not run the frozen proposal path")
        outputs.append("proposal green: forward approval ran frozen plan to complete frontier.")

        multi = assemble(
            _assembly_graph("two-fan-in-graph"),
            declared_by=DECLARED_BY,
            authority=Authority.COO,
            task="two fan-in proposal approval checker task",
            building_id="heart-phase5-two-fanin-approval",
            adapter="codex-local",
            gates=(Gate.STRICT_EVIDENCE, Gate.FAN_IN_WAIT_ALL),
            shape="design-needed",
            repo_root=repo,
            write_scope=_write_scope(),
        )
        multi_path = persist_proposed_building_graph(
            multi,
            proposal_root,
            overwrite=True,
        )
        rendered = render_proposal_for_human(multi_path)
        if "합류점 2개" not in rendered:
            raise AssemblyEquivalenceError("proposal renderer did not show 합류점 2개")
        multi_forward = run_goal_approve_entry(
            multi_path,
            action="forward",
            author_ref="human:smith",
            output_root=tmp / "multi-runs",
            repo_root=probe_repo,
            overwrite_existing=True,
            command_runner=_approval_runner(),
            adapter_timeout_seconds=30,
        )
        if not multi_forward.get("ran") or multi_forward.get("frontier_kind") != "complete":
            raise AssemblyEquivalenceError(
                f"multi-fan-in forward approval did not complete: {multi_forward!r}"
            )
        outputs.append("proposal green: multi-fan-in render showed 합류점 2개 and ran frozen plan.")

        with _with_temp_home(tmp / "build-invalid-author"):
            invalid_author = build(
                _approval_simple_graph(),
                goal="build invalid author checker task",
                declared_by=DECLARED_BY,
                author_ref="smith",
                action="forward",
                command_runner=_approval_runner(),
                adapter_timeout_seconds=30,
            )
        invalid_approval = invalid_author.get("approval_result")
        if not isinstance(invalid_approval, Mapping):
            raise AssemblyEquivalenceError(f"build invalid author returned no approval result: {invalid_author!r}")
        if invalid_approval.get("ran") is not False or invalid_approval.get("error_kind") != "invalid_author_ref":
            raise AssemblyEquivalenceError(f"build forward without coo:/human: author was not rejected: {invalid_author!r}")
        outputs.append("build RED observed: forward without coo:/human: author_ref rejected.")

        with _with_temp_home(tmp / "build-stop"):
            stopped = build(
                _approval_simple_graph(),
                goal="build stop checker task",
                declared_by=DECLARED_BY,
                author_ref="coo:smith",
                action="stop",
                command_runner=_approval_runner(),
                adapter_timeout_seconds=30,
            )
        stop_approval = stopped.get("approval_result")
        if not isinstance(stop_approval, Mapping):
            raise AssemblyEquivalenceError(f"build stop returned no approval result: {stopped!r}")
        if stop_approval.get("ran") is not False or not stop_approval.get("ok"):
            raise AssemblyEquivalenceError(f"build stop did not halt before running: {stopped!r}")
        stop_proposal = Path(str(stopped.get("proposal_ref", "")))
        try:
            stop_entries = [entry.name for entry in stop_proposal.parent.iterdir()]
        except FileNotFoundError as exc:
            raise AssemblyEquivalenceError(f"build stop proposal directory missing: {stop_proposal}") from exc
        if stop_entries != [GOAL_PROPOSAL_FILENAME]:
            raise AssemblyEquivalenceError(f"build stop wrote more than the proposal snapshot: {stop_entries!r}")
        outputs.append("build green: stop approval wrote only the frozen proposal and ran nothing.")

        explicit_scope = {
            "allowed_paths": ["support/checkers/**"],
            "forbidden_paths": [".git/**"],
        }
        explicit_graph = chain(
            [
                brick("design", "explicit build pass-through design"),
                brick("work", "explicit build pass-through work", write=True),
                brick(
                    "code-attack-qa",
                    "explicit build pass-through code attack",
                    returns=CODE_ATTACK_RETURN_SHAPE,
                ),
                brick("closure", "explicit build pass-through closure"),
            ]
        )
        explicit_root = tmp / "build-explicit-root"
        with _with_temp_home(tmp / "build-explicit-home"):
            explicit = build(
                explicit_graph,
                goal="build explicit pass-through checker task",
                declared_by=DECLARED_BY,
                author_ref="coo:smith",
                action="stop",
                output_root=explicit_root,
                write_scope=explicit_scope,
                gates=(Gate.STRICT_EVIDENCE,),
                command_runner=_approval_runner(),
                adapter_timeout_seconds=30,
            )
        explicit_approval = explicit.get("approval_result")
        if not isinstance(explicit_approval, Mapping):
            raise AssemblyEquivalenceError(f"build explicit pass-through returned no approval result: {explicit!r}")
        if explicit_approval.get("ran") is not False or not explicit_approval.get("ok"):
            raise AssemblyEquivalenceError(f"build explicit pass-through did not stop cleanly: {explicit!r}")
        explicit_proposal = Path(str(explicit.get("proposal_ref", ""))).resolve()
        if explicit_proposal.parent.parent != explicit_root.resolve():
            raise AssemblyEquivalenceError(f"build output_root was not used as proposal root: {explicit_proposal}")
        explicit_plan = json.loads(explicit_proposal.read_text(encoding="utf-8"))
        explicit_work_row = _brick_row(_step_for_kind(explicit_plan, "work"))
        if explicit_work_row.get("write_scope") != explicit_scope:
            raise AssemblyEquivalenceError(
                "build write_scope pass-through did not preserve caller declaration: "
                f"{explicit_work_row.get('write_scope')!r}"
            )
        explicit_gate_refs = _declared_gate_refs_for_edge(
            explicit_plan,
            source_kind="code-attack-qa",
            target_kind="closure",
        )
        if explicit_gate_refs != (DEFAULT_GATE, STRICT_GATE):
            raise AssemblyEquivalenceError(f"build gates pass-through did not preserve strict gate: {explicit_gate_refs!r}")
        outputs.append("build green: output_root/write_scope/gates pass-through preserved caller declarations.")

        import brick_protocol.support.operator.assembly as assembly_module  # noqa: PLC0415

        real_assemble = assembly_module.assemble

        def mutant_assemble(*args: Any, **kwargs: Any) -> Any:
            mutant_kwargs = dict(kwargs)
            mutant_kwargs.pop("write_scope", None)
            mutant_kwargs.pop("gates", None)
            return real_assemble(*args, **mutant_kwargs)

        assembly_module.assemble = mutant_assemble
        try:
            with _with_temp_home(tmp / "build-mutant-home"):
                mutant = build(
                    explicit_graph,
                    goal="build severed pass-through mutation checker task",
                    declared_by=DECLARED_BY,
                    author_ref="coo:smith",
                    action="stop",
                    output_root=tmp / "build-mutant-root",
                    write_scope=explicit_scope,
                    gates=(Gate.STRICT_EVIDENCE,),
                    command_runner=_approval_runner(),
                    adapter_timeout_seconds=30,
                )
            mutant_plan = json.loads(Path(str(mutant.get("proposal_ref", ""))).read_text(encoding="utf-8"))
            mutant_scope = _brick_row(_step_for_kind(mutant_plan, "work")).get("write_scope")
            mutant_gate_refs = _declared_gate_refs_for_edge(
                mutant_plan,
                source_kind="code-attack-qa",
                target_kind="closure",
            )
            if mutant_scope == explicit_scope or mutant_gate_refs == (DEFAULT_GATE, STRICT_GATE):
                raise AssemblyEquivalenceError(
                    "build mutation-RED did not discriminate severed write_scope/gates pass-through"
                )
        finally:
            assembly_module.assemble = real_assemble
        outputs.append("build mutation-RED observed: severed write_scope/gates wiring changed the frozen proposal.")

        zero_supply_graph = chain(
            [
                brick("work", "zero-supply write work", write=True),
                brick("closure", "zero-supply closure"),
            ]
        )
        with _with_temp_home(tmp / "build-forward"):
            forward_build = build(
                zero_supply_graph,
                goal="build zero-supply forward checker task",
                declared_by=DECLARED_BY,
                author_ref="human:smith",
                action="forward",
                command_runner=_approval_runner(),
                adapter_timeout_seconds=30,
            )
        forward_approval = forward_build.get("approval_result")
        if not isinstance(forward_approval, Mapping):
            raise AssemblyEquivalenceError(f"build forward returned no approval result: {forward_build!r}")
        if not forward_approval.get("ran") or forward_approval.get("frontier_kind") != "complete":
            raise AssemblyEquivalenceError(f"build forward did not complete deterministic run: {forward_build!r}")
        evidence_root = Path(str(forward_approval.get("evidence_root", ""))).resolve()
        if not evidence_root.exists():
            raise AssemblyEquivalenceError(f"build forward evidence root missing: {evidence_root}")
        worktree_text = str(forward_approval.get("worktree_path") or "").strip()
        if worktree_text:
            worktree_path = Path(worktree_text).resolve()
            try:
                evidence_inside_worktree = evidence_root.is_relative_to(worktree_path)
            except AttributeError:  # pragma: no cover - py<3.9 fallback
                evidence_inside_worktree = str(evidence_root).startswith(str(worktree_path) + "/")
            if evidence_inside_worktree:
                raise AssemblyEquivalenceError(
                    f"build forward evidence root lived inside disposable worktree: {evidence_root}"
                )
        outputs.append("build green: zero-supply graph ran forward with durable evidence outside worktree.")

    return tuple(outputs)


def _build_fan_graphs(fixture_name: str):
    """The same structural graph as ``_assembly_graph`` but declared through the
    easy build()/fan() front-end. Returns None when the graph is not a single
    linear-plus-fan spine that the build() list form expresses."""

    if fixture_name == "fast-fix":
        return build(
            [
                ["work", "checker fixture work for fast-fix-work", {"write": True}],
                ["axis-attack-qa", "checker fixture work for fast-fix-qa"],
                ["closure", "checker fixture work for fast-fix-closure"],
            ]
        )

    if fixture_name == "engine-feature-hard":
        return build(
            [
                ["development", "checker fixture work for hard-development"],
                fan(
                    [
                        ["code-attack-qa", "checker fixture work for hard-code"],
                        ["axis-attack-qa", "checker fixture work for hard-axis"],
                        [
                            "evidence-integrity",
                            "checker fixture work for hard-evidence",
                        ],
                    ]
                ),
                [
                    "closure",
                    "checker fixture work for hard-closure",
                    {
                        "route": [
                            reroute(Concern.IMPLEMENTATION_GAP, to=back(1), budget=5),
                            hold(Concern.VERIFICATION_GAP),
                        ]
                    },
                ],
            ]
        )

    # two-fan-in-graph has split convergences (inspect fans to four lenses that
    # rejoin at two different closures) -- not a single build() spine.
    return None


def _mandated_example_graphs(repo: Path):
    """The plan's mandated example, BOTH ways:
    기획(inspect) -> 개발(development, write) -> QA[code-attack-qa: codex ∥ gemini] -> 종합(closure).
    """

    insp_work = "기획: inspect the change boundary"
    dev_work = "개발: implement the bounded change"
    codex_work = "QA code lens (codex)"
    gemini_work = "QA code lens (gemini)"
    close_work = "종합: synthesize closure"

    via_build = build(
        [
            ["inspect", insp_work],
            ["development", dev_work, {"write": True}],
            fan(
                [
                    [
                        "code-attack-qa",
                        codex_work,
                        {"adapter": "codex-local", "label": "code-codex"},
                    ],
                    [
                        "code-attack-qa",
                        gemini_work,
                        {"adapter": "gemini-local", "label": "code-gemini"},
                    ],
                ]
            ),
            ["closure", close_work],
        ]
    )

    inspect = brick("inspect", insp_work)
    dev = brick("development", dev_work, write=True)
    code_codex = brick(
        "code-attack-qa",
        codex_work,
        adapter="codex-local",
        returns=CODE_ATTACK_RETURN_SHAPE,
        alias="code-codex",
    )
    code_gemini = brick(
        "code-attack-qa",
        gemini_work,
        adapter="gemini-local",
        returns=CODE_ATTACK_RETURN_SHAPE,
        alias="code-gemini",
    )
    close = brick("closure", close_work)
    via_hand = converge(
        assembly_edge(inspect, dev),
        fan_out(dev, [code_codex, code_gemini]),
        fan_in([code_codex, code_gemini], close),
        terminal=close,
    )
    return via_build, via_hand


def _fan_first_example_graphs(repo: Path):
    """Parallel-first workflow: build([fan([a, b, c]), converge])."""

    code_work = "fan-first code attack lens"
    axis_work = "fan-first axis attack lens"
    evidence_work = "fan-first evidence integrity lens"
    close_work = "fan-first convergence closure"

    via_build = build(
        [
            fan(
                [
                    ["code-attack-qa", code_work],
                    ["axis-attack-qa", axis_work],
                    ["evidence-integrity", evidence_work],
                ]
            ),
            ["closure", close_work],
        ]
    )

    code = brick("code-attack-qa", code_work, returns=CODE_ATTACK_RETURN_SHAPE)
    axis = brick("axis-attack-qa", axis_work, returns=AXIS_ATTACK_RETURN_SHAPE)
    evidence = brick("evidence-integrity", evidence_work, returns=EVIDENCE_INTEGRITY_RETURN_SHAPE)
    close = brick("closure", close_work)
    via_hand = converge(
        fan_in([code, axis, evidence], close),
        terminal=close,
    )
    return via_build, via_hand


def _lower_args(repo: Path, graph, *, fixture_name: str, building_id: str, gates):
    composed = assemble(
        graph,
        declared_by=DECLARED_BY,
        authority=Authority.COO,
        task=f"build/fan equivalence task for {fixture_name}",
        building_id=building_id,
        adapter="codex-local",
        gates=gates,
        repo_root=repo,
        write_scope=_write_scope(),
    )
    return composed.as_compose_args()


def _assert_byte_identical(repo: Path, lhs, rhs, *, fixture_name: str, gates) -> None:
    # Both sides lower under the SAME building_id so node/edge ids are derived
    # identically -- any difference is then a STRUCTURAL difference, the thing the
    # equivalence pin guards. (The building_id only prefixes ids; it carries no
    # structure.)
    shared_id = f"heart-buildfan-{fixture_name}"
    lhs_nodes, lhs_edges, lhs_groups = _lower_args(
        repo, lhs, fixture_name=f"{fixture_name}-buildfan", building_id=shared_id, gates=gates
    )
    rhs_nodes, rhs_edges, rhs_groups = _lower_args(
        repo, rhs, fixture_name=f"{fixture_name}-hand", building_id=shared_id, gates=gates
    )
    if lhs_nodes != rhs_nodes:
        raise AssemblyEquivalenceError(
            f"{fixture_name}: build/fan lowered NODES differ from hand-built chain/fan_out/fan_in/converge"
        )
    if lhs_edges != rhs_edges:
        raise AssemblyEquivalenceError(
            f"{fixture_name}: build/fan lowered EDGES differ from hand-built chain/fan_out/fan_in/converge"
        )
    if lhs_groups != rhs_groups:
        raise AssemblyEquivalenceError(
            f"{fixture_name}: build/fan lowered GROUPS differ from hand-built chain/fan_out/fan_in/converge"
        )


def _build_fan_equivalence_fire(repo: Path) -> tuple[str, ...]:
    outputs: list[str] = []

    # 1) The plan's MANDATED example, both ways, asserted byte-identical.
    via_build, via_hand = _mandated_example_graphs(repo)
    _assert_byte_identical(
        repo,
        via_build,
        via_hand,
        fixture_name="mandated-example",
        gates=(Gate.STRICT_EVIDENCE,),
    )
    outputs.append(
        "build/fan green: mandated inspect->development(write)->QA[codex||gemini]->closure "
        "lowered byte-identical via build/fan and via hand-built chain/fan_out/fan_in/converge."
    )

    # 1b) Fan-first build() is multi-root sugar over fan_in([roots], converge).
    via_build, via_hand = _fan_first_example_graphs(repo)
    _assert_byte_identical(
        repo,
        via_build,
        via_hand,
        fixture_name="fan-first-example",
        gates=(Gate.STRICT_EVIDENCE,),
    )
    outputs.append(
        "build/fan green: fan-first build([fan([a,b,c]), converge]) lowered byte-identical "
        "to hand-built multi-root fan_in."
    )

    # 2) Existing single-spine fixtures, both ways, byte-identical.
    for fixture_name in ("fast-fix", "engine-feature-hard"):
        build_graph = _build_fan_graphs(fixture_name)
        hand_graph = _assembly_graph(fixture_name)
        _assert_byte_identical(
            repo,
            build_graph,
            hand_graph,
            fixture_name=fixture_name,
            gates=_assembly_gates(fixture_name),
        )
        outputs.append(
            f"build/fan green: {fixture_name} lowered byte-identical via build/fan and via hand-built tier."
        )

    return tuple(outputs)


def run(repo: Path) -> list[str]:
    outputs: list[str] = []
    fixtures = {fixture.name: fixture for fixture in _fixtures()}
    projections: dict[str, Projection] = {}
    for fixture in fixtures.values():
        plan = _compose_fixture(repo, fixture)
        projection = _projection(plan, fixture)
        if projection.fan_in_source_return_has_concern and not any(
            has_concern for _label, has_concern in projection.fan_in_source_return_has_concern
        ):
            raise AssemblyEquivalenceError(
                f"{fixture.name}: fan-in source required_return_shape did not preserve template transition_concern_evidence"
            )
        projections[fixture.name] = projection
        outputs.append(
            "fixture accepted: "
            f"{fixture.name} nodes={len(plan.get('brick_steps', ()))}, "
            f"edges={len(plan.get('link_edges', ()))}, groups={len(plan.get('groups', ())) or 0}"
        )
        lhs_plan, lhs_fixture = _assembly_lhs(repo, fixture.name)
        lhs_projection = _projection(lhs_plan, lhs_fixture)
        if lhs_projection.fan_in_source_return_has_concern and not any(
            has_concern for _label, has_concern in lhs_projection.fan_in_source_return_has_concern
        ):
            raise AssemblyEquivalenceError(
                f"{fixture.name}: assembly LHS fan-in source required_return_shape did not preserve template transition_concern_evidence"
            )
        _assert_projection_equal(
            lhs_projection,
            projection,
            f"{fixture.name} assembly LHS vs hand-built RHS",
        )
        outputs.append(f"assembly LHS green: {fixture.name} P(assemble)==P(hand-built).")

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

    outputs.extend(_build_fan_equivalence_fire(repo))
    outputs.extend(_sibling_independence_dsl_fire(repo))
    outputs.extend(_node_write_scope_fire(repo))
    outputs.extend(_node_gates_fire(repo))
    outputs.extend(_write_scope_derivation_fire(repo))
    outputs.extend(_graph_write_scope_default_fire(repo))
    outputs.extend(_proposal_approval_fire(repo))
    outputs.append(_tiny_work_qa_return_shape_red(repo))
    outputs.append(PROOF_LIMIT)
    return outputs


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for assembly.py authoring DSL lowering into "
            "the permanent canonical compose_building() plan materializer."
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
