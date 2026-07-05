"""Support-only helpers for declared portfolio projection guidance.

This module renders read-side fields over already-computed portfolio frontier
facts. It does not choose Movement, route targets, sufficiency, success, or
quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def portfolio_hold_guidance(frontier: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return additive guidance fields for a held portfolio frontier.

    The caller supplies the observed frontier. This helper only projects which
    disposition labels are not useful for the observed hold reason plus terse
    reroute guidance for a human/COO-authored reroute disposition.
    """

    frontier_kind = str(frontier.get("frontier_kind") or "")
    if frontier_kind != "link_paused":
        return {}
    reason = str(frontier.get("frontier_reason") or "")
    allowed = _allowed_disposition_actions(frontier)
    not_resumable_by = _not_resumable_by(reason, allowed)
    guidance: dict[str, Any] = {}
    if not_resumable_by:
        guidance["not_resumable_by"] = not_resumable_by
    if "reroute" in allowed:
        guidance["reroute_guidance"] = (
            "Use reroute only with a caller/COO-authored target from the declared "
            "portfolio candidate set and a re_instruction for the rerun boundary."
        )
    if guidance:
        guidance["proof_limits"] = [
            "support portfolio projection guidance only",
            "derived from already-observed frontier fields",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not route target choice",
        ]
    return guidance


def portfolio_projection_with_hold_guidance(
    projection: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Return a projection copy with additive hold guidance under frontier."""

    result = dict(projection)
    frontier = result.get("frontier")
    if not isinstance(frontier, Mapping):
        return result
    guidance = portfolio_hold_guidance(frontier)
    if not guidance:
        return result
    decorated_frontier = dict(frontier)
    decorated_frontier.update(guidance)
    result["frontier"] = decorated_frontier
    return result


def write_portfolio_projection_with_hold_guidance(
    projection_path: Path | str,
    *,
    output_path: Path | str | None = None,
    overwrite_existing: bool = True,
) -> Path:
    """Write an additive hold-guidance projection beside an existing projection."""

    source = Path(projection_path)
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"portfolio projection must be a JSON object: {source}")
    decorated = portfolio_projection_with_hold_guidance(value)
    target = (
        Path(output_path)
        if output_path is not None
        else source.with_name("portfolio-projection-hold-guidance.json")
    )
    if target.exists() and not overwrite_existing:
        raise ValueError(f"portfolio hold-guidance projection already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(decorated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def _allowed_disposition_actions(frontier: Mapping[str, Any]) -> tuple[str, ...]:
    surface = frontier.get("disposition_action_surface")
    if not isinstance(surface, Mapping):
        return ()
    values = surface.get("allowed_values")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return ()
    return tuple(str(item) for item in values if str(item))


def _not_resumable_by(reason: str, allowed: tuple[str, ...]) -> list[str]:
    if reason == "portfolio_transition_budget_exhausted":
        return [action for action in ("forward",) if action in allowed]
    if reason in {
        "multi_candidate_requires_declared_policy",
        "proposed_candidate_not_in_declared_set",
        "portfolio_candidate_repeat_rejected",
        "no_adopted_next_building",
    }:
        return [action for action in ("forward", "raise") if action in allowed]
    return []


__all__ = [
    "portfolio_hold_guidance",
    "portfolio_projection_with_hold_guidance",
    "write_portfolio_projection_with_hold_guidance",
]
