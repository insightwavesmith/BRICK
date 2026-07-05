"""Pure declared graph-plan expansion assembly.

This module prepares a whole merged graph Building Plan from an original plan,
an expansion fragment, and a completed-frontier observation. It does not walk a
Building, record evidence, choose Movement, select targets, or mutate runtime
state.

Expansion fragment schema, intended as the single source for the later revision
packet surface:

```text
{
  "brick_steps": [<new graph brick step>, ...],
  "link_edges": [<new graph link edge>, ...],
  "execution_order": [<new step_ref>, ...],
  "groups": [{"group_id": ..., "member_refs": [<additional edge_ref>, ...]}, ...],
  "expansion_node_budgets": {"<new step_ref>": <positive int>, ...}
}
```

The returned ``expanded_plan`` is the complete merged plan, not a delta. The
returned ``expansion_metadata`` carries ``extends_plan_hash`` and
``expansion_node_budgets`` outside the plan body so a revision packet can
preserve genealogy and new-node budgets without making the plan hash
self-referential.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.plan_graph import (
    _graph_brick_steps_by_ref,
    _graph_declared_groups,
    _graph_execution_order,
    _graph_link_edges_by_ref,
    _validate_graph_plan_topology,
)
from brick_protocol.support.recording.contracts import require_positive_int
from support.recording.declaration_packets import _pure_declared_plan_copy

_EXPANSION_FRAGMENT_KEYS = frozenset(
    {
        "brick_steps",
        "link_edges",
        "execution_order",
        "groups",
        "expansion_node_budgets",
    }
)
_MERGED_LIST_KEYS = frozenset({"brick_steps", "link_edges", "execution_order", "groups"})


def assemble_expanded_graph_plan(
    original_plan: Mapping[str, Any],
    expansion_fragment: Mapping[str, Any],
    completed_frontier: Iterable[str],
) -> Mapping[str, Any]:
    """Return a whole merged graph plan plus separate expansion metadata.

    Validation is intentionally local to this pure expansion surface: it rejects
    duplicate step refs, cycles, fan-in edges omitted from fan-in groups, and
    expansion edges that target already-completed frontier nodes.
    """

    if original_plan.get("plan_shape") != "graph":
        raise ValueError("plan expansion requires original plan_shape: graph")
    _reject_unknown_fragment_keys(expansion_fragment)

    original_steps = _graph_brick_steps_by_ref(original_plan)
    original_step_refs = frozenset(original_steps)
    new_steps = _required_mapping_list(expansion_fragment, "brick_steps")
    new_step_refs = tuple(_required_text(f"brick_steps[{index}].step_ref", step.get("step_ref")) for index, step in enumerate(new_steps))
    duplicate_new_refs = sorted(ref for ref, count in Counter(new_step_refs).items() if count > 1)
    if duplicate_new_refs:
        raise ValueError("duplicate expansion step_ref: " + ", ".join(duplicate_new_refs))
    overlaps = sorted(original_step_refs.intersection(new_step_refs))
    if overlaps:
        raise ValueError("expansion step_ref already exists in original plan: " + ", ".join(overlaps))

    merged_plan = _merged_graph_plan(original_plan, expansion_fragment)
    brick_steps = _graph_brick_steps_by_ref(merged_plan)
    link_edges = _graph_link_edges_by_ref(merged_plan)
    _graph_execution_order(merged_plan, brick_steps)
    groups = _graph_declared_groups(merged_plan, link_edges)

    _reject_upstream_insertions(link_edges, expansion_fragment, completed_frontier)
    _validate_fan_in_membership(link_edges, groups)
    _validate_expansion_node_budgets(expansion_fragment, frozenset(new_step_refs))
    _validate_graph_plan_topology(brick_steps, link_edges, groups)

    return {
        "expanded_plan": merged_plan,
        "expansion_metadata": {
            "extends_plan_hash": _declared_plan_hash(original_plan),
            "extends_plan_hash_algorithm": "sha256",
            "extends_plan_hash_basis": (
                "canonical sorted-key JSON of the pure declared-building-plan copy "
                "(runtime walker state excluded)"
            ),
            "expansion_node_budgets": dict(expansion_fragment.get("expansion_node_budgets") or {}),
        },
        "proof_limits": [
            "plan_expansion is pure support assembly only",
            "not a walker, recorder, Movement authority, route selector, source truth, success judgment, or quality judgment",
        ],
    }


def _merged_graph_plan(
    original_plan: Mapping[str, Any],
    expansion_fragment: Mapping[str, Any],
) -> dict[str, Any]:
    merged = {str(key): _json_ready(value) for key, value in original_plan.items()}
    for key in _MERGED_LIST_KEYS:
        merged[key] = list(original_plan.get(key) or []) + list(expansion_fragment.get(key) or [])
    if "expansion_node_budgets" in merged:
        raise ValueError("expanded plan body must not carry expansion_node_budgets")
    return merged


def _reject_unknown_fragment_keys(expansion_fragment: Mapping[str, Any]) -> None:
    unknown = sorted(str(key) for key in expansion_fragment if str(key) not in _EXPANSION_FRAGMENT_KEYS)
    if unknown:
        raise ValueError("expansion fragment contains unknown key(s): " + ", ".join(unknown))


def _reject_upstream_insertions(
    link_edges: Mapping[str, Mapping[str, Any]],
    expansion_fragment: Mapping[str, Any],
    completed_frontier: Iterable[str],
) -> None:
    completed = frozenset(str(ref) for ref in completed_frontier)
    new_edge_refs = {
        _required_text(f"link_edges[{index}].edge_ref", edge.get("edge_ref"))
        for index, edge in enumerate(_required_mapping_list(expansion_fragment, "link_edges"))
    }
    blocked = sorted(
        edge_ref
        for edge_ref in new_edge_refs
        if str(link_edges[edge_ref].get("target_step_ref") or "") in completed
    )
    if blocked:
        raise ValueError("expansion must not target completed frontier step(s): " + ", ".join(blocked))


def _validate_fan_in_membership(
    link_edges: Mapping[str, Mapping[str, Any]],
    groups: Iterable[Mapping[str, Any]],
) -> None:
    incoming_by_target: dict[str, set[str]] = {}
    for edge_ref, edge in link_edges.items():
        target = str(edge.get("target_step_ref") or "")
        if not target:
            continue
        incoming_by_target.setdefault(target, set()).add(edge_ref)

    fan_in_members_by_target: dict[str, set[str]] = {}
    for group in groups:
        if group.get("group_role") != "fan_in":
            continue
        member_refs = group.get("member_refs") or []
        targets = {
            str(link_edges[str(ref)].get("target_step_ref") or "")
            for ref in member_refs
            if str(ref) in link_edges and str(link_edges[str(ref)].get("target_step_ref") or "")
        }
        if len(targets) != 1:
            continue
        target = next(iter(targets))
        fan_in_members_by_target.setdefault(target, set()).update(str(ref) for ref in member_refs)

    missing: list[str] = []
    for target, incoming in sorted(incoming_by_target.items()):
        if len(incoming) < 2:
            continue
        covered = fan_in_members_by_target.get(target, set())
        missing.extend(f"{target}:{edge_ref}" for edge_ref in sorted(incoming - covered))
    if missing:
        raise ValueError("fan-in incoming edges must be declared in groups.member_refs: " + ", ".join(missing))


def _validate_expansion_node_budgets(
    expansion_fragment: Mapping[str, Any],
    new_step_refs: frozenset[str],
) -> None:
    budgets = expansion_fragment.get("expansion_node_budgets") or {}
    if not isinstance(budgets, Mapping):
        raise ValueError("expansion_node_budgets must be a mapping when supplied")
    unknown = sorted(str(key) for key in budgets if str(key) not in new_step_refs)
    if unknown:
        raise ValueError("expansion_node_budgets keys must reference new step_ref values: " + ", ".join(unknown))
    bad_values = []
    for key, value in budgets.items():
        try:
            require_positive_int(value, f"expansion_node_budgets.{key}", allow_decimal_text=False)
        except ValueError:
            bad_values.append(str(key))
    bad_values = sorted(bad_values)
    if bad_values:
        raise ValueError("expansion_node_budgets values must be positive integers: " + ", ".join(bad_values))


def _declared_plan_hash(plan: Mapping[str, Any]) -> str:
    plan_copy = _pure_declared_plan_copy(plan)
    canonical = json.dumps(plan_copy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _required_mapping_list(source: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    values = source.get(key) or []
    if not isinstance(values, list):
        raise ValueError(f"expansion fragment {key} must be a list")
    result: list[Mapping[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError(f"expansion fragment {key}[{index}] must be a mapping")
        result.append(value)
    return tuple(result)


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _json_ready(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))
