"""Per-target-node reroute budget + Carry-budget evidence refs (dynamic walker).

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
Link-assigned per-TARGET-node reroute budget reader, the resume-time budget /
landing reconstruction, the disposition-action validation, and the Carry-budget
evidence ref builders were lifted out of the dynamic_walker god-module into this
single-concern collaborator.

The reroute budget is OWNED and ASSIGNED by Link, keyed by the TARGET Brick node
ref and SHARED across all reroute-landings on that node. This module READS the
declared budget map and validates the human/COO disposition_action against the
canonical transition-lifecycle contract; it authors no budget, no Movement, and
no disposition.

Support mechanics only. Homes NO axis crossing (it consumes the canonical
transition-lifecycle DISPOSITION_ACTIONS contract of brick_protocol/link/transition.py). Judges
no success or quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.link.transition import (
    DISPOSITION_ACTIONS as _DISPOSITION_ACTIONS,
)
from brick_protocol.support.operator.primitives import (
    _optional_text_value,
    _resource_slug,
)
from brick_protocol.support.recording.contracts import require_positive_int

# A reroute target read from a non-binding transition_concern is one of the
# concern's related_boundary_refs that names a Brick instance/boundary.
_BRICK_REF_PREFIXES: tuple[str, ...] = (
    "brick-",
    "brick:",
    "brick-instance:",
    "brick-boundary:",
)

CARRY_BUDGET_TRACE_PATH = "evidence/claim_trace/link/carry_trace.json"


def _carry_budget_fact_ref(building_id: str, target_brick: str) -> str:
    return (
        "carry-budget:"
        + _resource_slug("building_id", building_id.replace(":", "-"))
        + ":node:"
        + _resource_slug("target_brick", target_brick.replace(":", "-"))
    )


def _carry_budget_evidence_ref(building_id: str, target_brick: str) -> str:
    return CARRY_BUDGET_TRACE_PATH + "#" + _carry_budget_fact_ref(building_id, target_brick)


def _node_reroute_budgets(
    plan: Mapping[str, Any],
    *,
    declared_bricks: set[str],
) -> dict[str, int]:
    """Read the Link-assigned per-TARGET-node reroute budget map.

    The budget is OWNED and ASSIGNED by Link (not held by the Brick). It is
    keyed by the TARGET Brick node ref and is SHARED across all reroute-landings
    on that node. Every key must resolve to an EXISTING node; every value must be
    a positive integer (no optional / absent / fresh-per-event budget).
    """

    raw = plan.get("node_reroute_budgets")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("node_reroute_budgets must be a mapping of brick node ref -> positive int")
    budgets: dict[str, int] = {}
    for key, value in raw.items():
        brick_ref = _optional_text_value(key)
        if not brick_ref:
            raise ValueError("node_reroute_budgets keys must be non-empty brick node refs")
        if not brick_ref.startswith(_BRICK_REF_PREFIXES):
            raise ValueError(
                "node_reroute_budgets key must name a Brick node ref: " + brick_ref
            )
        if brick_ref not in declared_bricks:
            raise ValueError(
                "node_reroute_budgets target must resolve to an existing node: " + brick_ref
            )
        budget = require_positive_int(value, f"node_reroute_budgets[{brick_ref}]")
        budgets[brick_ref] = budget
    return budgets


def _positive_int(value: Any, label: str) -> int:
    return require_positive_int(value, label)


def _mapping_value(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _jsonl_records(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.exists():
        return ()
    records: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, Mapping):
            records.append(value)
    return tuple(records)


def _resume_budget_map(
    evidence: Mapping[str, Any],
    *,
    declared_bricks: set[str],
) -> dict[str, int]:
    raw = _mapping_value(
        "dynamic_walker_evidence.node_reroute_budgets",
        evidence.get("node_reroute_budgets"),
    )
    return _node_reroute_budgets(
        {"node_reroute_budgets": raw},
        declared_bricks=declared_bricks,
    )


def _resume_landing_map(
    evidence: Mapping[str, Any],
    *,
    node_budget: Mapping[str, int],
) -> dict[str, int]:
    raw = _mapping_value(
        "dynamic_walker_evidence.node_reroute_landings",
        evidence.get("node_reroute_landings"),
    )
    landings: dict[str, int] = {}
    for brick_ref in node_budget:
        value = raw.get(brick_ref, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("node_reroute_landings values must be finite non-negative integers")
        landings[brick_ref] = value
    return landings


def _required_disposition_action(disposition: Mapping[str, Any]) -> str:
    action = _optional_text_value(disposition.get("disposition_action")) or ""
    if action not in _DISPOSITION_ACTIONS:
        raise ValueError(
            "disposition_action must be one of "
            + _disposition_actions_error_text()
        )
    if action == "raise":
        require_positive_int(
            disposition.get("budget_increment"),
            "transition_lifecycle.budget_increment",
        )
    elif disposition.get("budget_increment") is not None:
        raise ValueError("budget_increment is admitted only for disposition_action=raise")
    return action


def _disposition_actions_error_text() -> str:
    return ", ".join(_DISPOSITION_ACTIONS[:-1]) + f", or {_DISPOSITION_ACTIONS[-1]}"
