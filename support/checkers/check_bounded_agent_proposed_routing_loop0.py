#!/usr/bin/env python3
"""Check BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0 dynamic walker invariants.

This checker is support evidence only. It does not choose Movement, author a
route, judge success or quality, schedule, retry, or call providers. It runs the
admitted dynamic graph walker (support/operator/dynamic_walker.py) over adapter:
local fixtures (NO codex/claude/gemini) and asserts the bounded-routing-loop
invariants the amendment locks:

- the reroute budget is per-TARGET-Brick (node), Link-assigned, SHARED across
  multiple non-self reroute-landings on that node (no fresh per-event budget);
- a reroute target must resolve to an EXISTING node (support never invents one);
- max_attempts / per-node budget is REQUIRED and POSITIVE (no absent/zero budget);
- budget is consumed per REROUTE-LANDING, not per forward-replay-execution;
- on budget exhaustion the walk HOLDs (transition_lifecycle.state=paused,
  required_disposition_owner=caller-or-coo) -- support HALTS and RECORDS and does
  NOT decide raise/forward/stop (ζ7);
- ζ7 source guard: the dynamic walker module authors NO route/Movement (no
  support: route author_ref), AgentFact stays closed, transition_concern stays
  nested in the closed returned shape with binding:false.
- B3 fan-out / fan-in is walked serially over adapter:local evidence only:
  fan-out reaches all declared branch nodes once, fan-in wait_all runs the join
  only after all incoming sources returned, and a held source surfaces through an
  existing paused Link frontier rather than closure.
- B5 fills the minimal-complete dynamic-walker smoke matrix gaps over
  adapter:local deterministic fixtures only: full-chain replay, human gate pause
  on reroute, nested different-node budget room, non-existent target walk-on,
  and monotonic/no-judgment reroute evidence.
- malformed transition_concern_evidence never becomes a late writer crash or
  adopted Movement; it surfaces as a paused frontier.

Pass => exit 0. Reject => exit 1. The standalone checker walks the loop for real;
the bounded_agent_proposed_routing_loop profile pins the source invariants.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

from support.checkers.lib.checker_temp_vessel import checker_temp_path

from support.checkers.lib.fixture_graph_helpers import (
    fixture_graph_brick_step,
    fixture_graph_link_edge,
    fixture_proof_limits,
)


def _repo_root_from_arg(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_import_path(repo: Path) -> None:
    ensure_checker_imports(repo)


# ---- adapter:local fixture builders (no providers) ----

def _brick_step(step_ref: str, brick_ref: str, agent_ref: str, completion_edge_ref: str) -> Mapping[str, Any]:
    return fixture_graph_brick_step(
        step_ref,
        brick_ref,
        completion_edge_ref,
        agent_object_ref=agent_ref,
        work_statement=f"Declared work for {step_ref}.",
        required_return_shape="observed_evidence, not_proven",
        source_facts=["AGENTS.md", "support/operator/dynamic_walker.py"],
    )


def _fwd_edge(edge_ref: str, src: str, tgt_step: str, tgt_brick: str, gate: list[str] | None = None) -> Mapping[str, Any]:
    return fixture_graph_link_edge(
        edge_ref,
        src,
        tgt_brick,
        target_step_ref=tgt_step,
        declared_gate_refs=gate,
        falsy_declared_gate_refs_use_default=True,
    )


def _close_edge(edge_ref: str, src: str, reason: str, boundary: str) -> Mapping[str, Any]:
    return fixture_graph_link_edge(
        edge_ref,
        src,
        boundary,
        close_reason=reason,
        falsy_declared_gate_refs_use_default=True,
    )


def _proof_limits() -> list[str]:
    return fixture_proof_limits()


def _checker_plan(prefix: str, budget: int) -> tuple[Mapping[str, Any], str]:
    b1 = f"brick-{prefix}-design"
    b2 = f"brick-{prefix}-build"
    b3 = f"brick-{prefix}-review"
    b4 = f"brick-{prefix}-close"
    default_gate = ["link-gate:default-transition"]
    plan = {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0530",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["semantic correctness of the agent-proposed reroute"],
        "execution_order": [f"{prefix}-design", f"{prefix}-build", f"{prefix}-review", f"{prefix}-close"],
        "brick_steps": [
            _brick_step(f"{prefix}-design", b1, "agent-object:coo", f"edge:{prefix}-design-to-build"),
            _brick_step(f"{prefix}-build", b2, "agent-object:dev", f"edge:{prefix}-build-to-review"),
            _brick_step(f"{prefix}-review", b3, "agent-object:qa", f"edge:{prefix}-review-to-close"),
            _brick_step(f"{prefix}-close", b4, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-design-to-build", f"{prefix}-design", f"{prefix}-build", b2),
            _fwd_edge(f"edge:{prefix}-build-to-review", f"{prefix}-build", f"{prefix}-review", b3, gate=default_gate),
            _fwd_edge(f"edge:{prefix}-review-to-close", f"{prefix}-review", f"{prefix}-close", b4, gate=default_gate),
            _close_edge(f"edge:{prefix}-close-to-boundary", f"{prefix}-close", f"{prefix} closed", f"building-boundary:{prefix}-closed"),
        ],
        "node_reroute_budgets": {b2: budget},
    }
    return plan, b2


def _expansion_resume_base_plan(prefix: str) -> tuple[dict[str, Any], str, str, str]:
    plan, target = _checker_plan(prefix, budget=1)
    changed = copy.deepcopy(plan)
    changed["expansion_budget"] = 1
    review_brick = f"brick-{prefix}-review"
    new_step_ref = f"{prefix}-expansion"
    new_brick_ref = f"brick-{new_step_ref}"
    return changed, target, review_brick, new_brick_ref


def _expanded_plan_with_resume_node(
    plan: Mapping[str, Any],
    *,
    prefix: str,
    new_step_ref: str,
    new_brick_ref: str,
) -> tuple[dict[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    changed = copy.deepcopy(plan)
    close_step_ref = f"{prefix}-close"
    close_brick_ref = f"brick-{close_step_ref}"
    edge_ref = f"edge:{prefix}-expansion-to-close"
    brick_step = _brick_step(
        new_step_ref,
        new_brick_ref,
        "agent-object:dev",
        edge_ref,
    )
    link_edge = _fwd_edge(edge_ref, new_step_ref, close_step_ref, close_brick_ref)
    changed["brick_steps"].append(brick_step)
    changed["link_edges"].append(link_edge)
    changed["execution_order"].append(new_step_ref)
    fragment = {
        "brick_steps": [brick_step],
        "link_edges": [link_edge],
        "execution_order": [new_step_ref],
        "groups": [],
        "expansion_node_budgets": {new_step_ref: 1},
    }
    return changed, fragment, {"expansion_node_budgets": {new_step_ref: 1}}


def _expanded_fan_in_plan_with_revision_source(
    plan: Mapping[str, Any],
    *,
    prefix: str,
    new_step_ref: str,
    new_brick_ref: str,
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    changed = copy.deepcopy(plan)
    join_step_ref = f"{prefix}-join"
    join_brick_ref = f"brick-{join_step_ref}"
    root_to_new_ref = f"edge:{prefix}-root-to-c"
    new_to_join_ref = f"edge:{prefix}-c-to-join"
    brick_step = _brick_step(
        new_step_ref,
        new_brick_ref,
        "agent-object:qa",
        new_to_join_ref,
    )
    root_edge = _fwd_edge(
        root_to_new_ref,
        f"{prefix}-root",
        new_step_ref,
        new_brick_ref,
    )
    join_edge = _fwd_edge(
        new_to_join_ref,
        new_step_ref,
        join_step_ref,
        join_brick_ref,
    )
    changed["brick_steps"].append(brick_step)
    changed["link_edges"].extend([root_edge, join_edge])
    changed["execution_order"].append(new_step_ref)
    for group in changed.get("groups", []):
        if not isinstance(group, dict):
            continue
        if group.get("group_role") == "fan_out":
            group.setdefault("member_refs", []).append(root_to_new_ref)
        if group.get("group_role") == "fan_in":
            group.setdefault("member_refs", []).append(new_to_join_ref)
    fragment = {
        "brick_steps": [brick_step],
        "link_edges": [root_edge, join_edge],
        "execution_order": [new_step_ref],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out",
                "added_member_refs": [root_to_new_ref],
            },
            {
                "group_id": f"group:{prefix}-fan-in",
                "added_member_refs": [new_to_join_ref],
            },
        ],
    }
    return changed, fragment


def _plan_with_build_source_fact(
    plan: Mapping[str, Any],
    *,
    build_step_ref: str,
    source_fact_ref: str,
) -> Mapping[str, Any]:
    changed = copy.deepcopy(plan)
    for step in changed.get("brick_steps", []):
        if not isinstance(step, dict) or step.get("step_ref") != build_step_ref:
            continue
        for row in step.get("rows", []):
            if isinstance(row, dict) and row.get("axis") == "Brick":
                row["source_facts"] = [source_fact_ref]
                return changed
    raise ValueError(f"build step not found for source_fact mutation: {build_step_ref}")


def _fan_plan(prefix: str, *, held_source: bool = False) -> Mapping[str, Any]:
    root = f"brick-{prefix}-root"
    lane_a = f"brick-{prefix}-lane-a"
    lane_b = f"brick-{prefix}-lane-b"
    join = f"brick-{prefix}-join"
    close = f"brick-{prefix}-close"
    b_gate = ["link-gate:default-transition", "link-gate:human"] if held_source else None
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0530",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["parallel runtime execution"],
        "execution_order": [
            f"{prefix}-root",
            f"{prefix}-lane-a",
            f"{prefix}-lane-b",
            f"{prefix}-join",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _brick_step(f"{prefix}-root", root, "agent-object:coo", f"edge:{prefix}-root-to-a"),
            _brick_step(f"{prefix}-lane-a", lane_a, "agent-object:qa", f"edge:{prefix}-a-to-join"),
            _brick_step(f"{prefix}-lane-b", lane_b, "agent-object:qa", f"edge:{prefix}-b-to-join"),
            _brick_step(f"{prefix}-join", join, "agent-object:coo", f"edge:{prefix}-join-to-close"),
            _brick_step(f"{prefix}-close", close, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-root-to-a", f"{prefix}-root", f"{prefix}-lane-a", lane_a),
            _fwd_edge(f"edge:{prefix}-root-to-b", f"{prefix}-root", f"{prefix}-lane-b", lane_b),
            _fwd_edge(f"edge:{prefix}-a-to-join", f"{prefix}-lane-a", f"{prefix}-join", join),
            _fwd_edge(
                f"edge:{prefix}-b-to-join",
                f"{prefix}-lane-b",
                f"{prefix}-join",
                join,
                gate=b_gate,
            ),
            _fwd_edge(f"edge:{prefix}-join-to-close", f"{prefix}-join", f"{prefix}-close", close),
            _close_edge(
                f"edge:{prefix}-close-to-boundary",
                f"{prefix}-close",
                f"{prefix} closed",
                f"building-boundary:{prefix}-closed",
            ),
        ],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-root-to-a", f"edge:{prefix}-root-to-b"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            {
                "group_id": f"group:{prefix}-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-a-to-join", f"edge:{prefix}-b-to-join"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["synthesis quality"],
            },
        ],
    }


def _two_stage_fan_plan(prefix: str) -> Mapping[str, Any]:
    root = f"brick-{prefix}-root"
    lane_a = f"brick-{prefix}-lane-a"
    lane_b = f"brick-{prefix}-lane-b"
    join1 = f"brick-{prefix}-join1"
    lane_c = f"brick-{prefix}-lane-c"
    lane_d = f"brick-{prefix}-lane-d"
    join2 = f"brick-{prefix}-join2"
    close = f"brick-{prefix}-close"
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0627",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["parallel runtime execution"],
        "execution_order": [
            f"{prefix}-root",
            f"{prefix}-lane-a",
            f"{prefix}-lane-b",
            f"{prefix}-join1",
            f"{prefix}-lane-c",
            f"{prefix}-lane-d",
            f"{prefix}-join2",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _brick_step(f"{prefix}-root", root, "agent-object:coo", f"edge:{prefix}-root-to-a"),
            _brick_step(f"{prefix}-lane-a", lane_a, "agent-object:qa", f"edge:{prefix}-a-to-join1"),
            _brick_step(f"{prefix}-lane-b", lane_b, "agent-object:qa", f"edge:{prefix}-b-to-join1"),
            _brick_step(f"{prefix}-join1", join1, "agent-object:coo", f"edge:{prefix}-join1-to-c"),
            _brick_step(f"{prefix}-lane-c", lane_c, "agent-object:qa", f"edge:{prefix}-c-to-join2"),
            _brick_step(f"{prefix}-lane-d", lane_d, "agent-object:qa", f"edge:{prefix}-d-to-join2"),
            _brick_step(f"{prefix}-join2", join2, "agent-object:coo", f"edge:{prefix}-join2-to-close"),
            _brick_step(f"{prefix}-close", close, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-root-to-a", f"{prefix}-root", f"{prefix}-lane-a", lane_a),
            _fwd_edge(f"edge:{prefix}-root-to-b", f"{prefix}-root", f"{prefix}-lane-b", lane_b),
            _fwd_edge(f"edge:{prefix}-a-to-join1", f"{prefix}-lane-a", f"{prefix}-join1", join1),
            _fwd_edge(f"edge:{prefix}-b-to-join1", f"{prefix}-lane-b", f"{prefix}-join1", join1),
            _fwd_edge(f"edge:{prefix}-join1-to-c", f"{prefix}-join1", f"{prefix}-lane-c", lane_c),
            _fwd_edge(f"edge:{prefix}-join1-to-d", f"{prefix}-join1", f"{prefix}-lane-d", lane_d),
            _fwd_edge(f"edge:{prefix}-c-to-join2", f"{prefix}-lane-c", f"{prefix}-join2", join2),
            _fwd_edge(f"edge:{prefix}-d-to-join2", f"{prefix}-lane-d", f"{prefix}-join2", join2),
            _fwd_edge(f"edge:{prefix}-join2-to-close", f"{prefix}-join2", f"{prefix}-close", close),
            _close_edge(
                f"edge:{prefix}-close-to-boundary",
                f"{prefix}-close",
                f"{prefix} closed",
                f"building-boundary:{prefix}-closed",
            ),
        ],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out-1",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-root-to-a", f"edge:{prefix}-root-to-b"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            {
                "group_id": f"group:{prefix}-fan-in-1",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-a-to-join1", f"edge:{prefix}-b-to-join1"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["synthesis quality"],
            },
            {
                "group_id": f"group:{prefix}-fan-out-2",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-join1-to-c", f"edge:{prefix}-join1-to-d"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            {
                "group_id": f"group:{prefix}-fan-in-2",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [f"edge:{prefix}-c-to-join2", f"edge:{prefix}-d-to-join2"],
                "proof_limits": ["support topology label only"],
                "not_proven": ["synthesis quality"],
            },
        ],
    }


def _fan3_plan(
    prefix: str,
    *,
    held_source: bool = False,
    parked_source: bool = False,
) -> Mapping[str, Any]:
    root = f"brick-{prefix}-root"
    lane_a = f"brick-{prefix}-lane-a"
    lane_b = f"brick-{prefix}-lane-b"
    lane_c = f"brick-{prefix}-lane-c"
    join = f"brick-{prefix}-join"
    close = f"brick-{prefix}-close"
    b_gate = ["link-gate:default-transition", "link-gate:human"] if held_source else None
    lane_b_step = dict(
        _brick_step(
            f"{prefix}-lane-b",
            lane_b,
            "agent-object:dev" if parked_source else "agent-object:qa",
            f"edge:{prefix}-b-to-join",
        )
    )
    if parked_source:
        lane_b_step["selected_adapter_ref"] = "adapter:chat-session"
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0618",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["parallel runtime execution"],
        "execution_order": [
            f"{prefix}-root",
            f"{prefix}-lane-a",
            f"{prefix}-lane-c",
            f"{prefix}-lane-b",
            f"{prefix}-join",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _brick_step(f"{prefix}-root", root, "agent-object:coo", f"edge:{prefix}-root-to-a"),
            _brick_step(f"{prefix}-lane-a", lane_a, "agent-object:qa", f"edge:{prefix}-a-to-join"),
            _brick_step(f"{prefix}-lane-c", lane_c, "agent-object:qa", f"edge:{prefix}-c-to-join"),
            lane_b_step,
            _brick_step(f"{prefix}-join", join, "agent-object:coo", f"edge:{prefix}-join-to-close"),
            _brick_step(f"{prefix}-close", close, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-root-to-a", f"{prefix}-root", f"{prefix}-lane-a", lane_a),
            _fwd_edge(f"edge:{prefix}-root-to-c", f"{prefix}-root", f"{prefix}-lane-c", lane_c),
            _fwd_edge(f"edge:{prefix}-root-to-b", f"{prefix}-root", f"{prefix}-lane-b", lane_b),
            _fwd_edge(f"edge:{prefix}-a-to-join", f"{prefix}-lane-a", f"{prefix}-join", join),
            _fwd_edge(f"edge:{prefix}-c-to-join", f"{prefix}-lane-c", f"{prefix}-join", join),
            _fwd_edge(
                f"edge:{prefix}-b-to-join",
                f"{prefix}-lane-b",
                f"{prefix}-join",
                join,
                gate=b_gate,
            ),
            _fwd_edge(f"edge:{prefix}-join-to-close", f"{prefix}-join", f"{prefix}-close", close),
            _close_edge(
                f"edge:{prefix}-close-to-boundary",
                f"{prefix}-close",
                f"{prefix} closed",
                f"building-boundary:{prefix}-closed",
            ),
        ],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    f"edge:{prefix}-root-to-a",
                    f"edge:{prefix}-root-to-c",
                    f"edge:{prefix}-root-to-b",
                ],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            {
                "group_id": f"group:{prefix}-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    f"edge:{prefix}-a-to-join",
                    f"edge:{prefix}-c-to-join",
                    f"edge:{prefix}-b-to-join",
                ],
                "proof_limits": ["support topology label only"],
                "not_proven": ["synthesis quality"],
            },
        ],
    }


def _cohort_fan_plan(
    prefix: str,
    *,
    sibling_independence: list[str] | None = None,
) -> Mapping[str, Any]:
    """A 3-source fan-in graph where the JOIN reroutes back to lane-a (source1).

    root fans out to lane-a / lane-b / lane-c; all three fan in to join; join ->
    close. ALL three sources PASS first (depth 0); THEN the join's agent raises a
    non-binding concern naming lane-a's Brick. The join's completion edge
    (join-to-close) carries the default gate, so that concern is auto-adopted
    within lane-a's node budget -- the reroute target is the agent's proposal, not
    the edge target. When the reroute LANDS on lane-a (a fan-in SOURCE), cohort
    re-verification must re-walk lane-b and lane-c (the siblings: a fix in lane-a
    can stale their prior PASS) unless a HUMAN sibling_independence vouch on the
    fan-in group names them. The vouch is declared verbatim on the fan-in group
    (support reads it; never decides independence).
    """

    root = f"brick-{prefix}-root"
    lane_a = f"brick-{prefix}-lane-a"
    lane_b = f"brick-{prefix}-lane-b"
    lane_c = f"brick-{prefix}-lane-c"
    join = f"brick-{prefix}-join"
    close = f"brick-{prefix}-close"
    default_gate = ["link-gate:default-transition"]
    fan_in_group: dict[str, Any] = {
        "group_id": f"group:{prefix}-fan-in",
        "group_role": "fan_in",
        "member_ref_kind": "link_edge",
        "member_refs": [
            f"edge:{prefix}-a-to-join",
            f"edge:{prefix}-b-to-join",
            f"edge:{prefix}-c-to-join",
        ],
        "proof_limits": ["support topology label only"],
        "not_proven": ["synthesis quality"],
    }
    if sibling_independence is not None:
        fan_in_group["sibling_independence"] = list(sibling_independence)
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0530",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["parallel runtime execution"],
        "execution_order": [
            f"{prefix}-root",
            f"{prefix}-lane-a",
            f"{prefix}-lane-b",
            f"{prefix}-lane-c",
            f"{prefix}-join",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _brick_step(f"{prefix}-root", root, "agent-object:coo", f"edge:{prefix}-root-to-a"),
            _brick_step(f"{prefix}-lane-a", lane_a, "agent-object:qa", f"edge:{prefix}-a-to-join"),
            _brick_step(f"{prefix}-lane-b", lane_b, "agent-object:qa", f"edge:{prefix}-b-to-join"),
            _brick_step(f"{prefix}-lane-c", lane_c, "agent-object:qa", f"edge:{prefix}-c-to-join"),
            _brick_step(f"{prefix}-join", join, "agent-object:coo", f"edge:{prefix}-join-to-close"),
            _brick_step(f"{prefix}-close", close, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-root-to-a", f"{prefix}-root", f"{prefix}-lane-a", lane_a),
            _fwd_edge(f"edge:{prefix}-root-to-b", f"{prefix}-root", f"{prefix}-lane-b", lane_b),
            _fwd_edge(f"edge:{prefix}-root-to-c", f"{prefix}-root", f"{prefix}-lane-c", lane_c),
            _fwd_edge(f"edge:{prefix}-a-to-join", f"{prefix}-lane-a", f"{prefix}-join", join),
            _fwd_edge(f"edge:{prefix}-b-to-join", f"{prefix}-lane-b", f"{prefix}-join", join),
            _fwd_edge(f"edge:{prefix}-c-to-join", f"{prefix}-lane-c", f"{prefix}-join", join),
            _fwd_edge(
                f"edge:{prefix}-join-to-close",
                f"{prefix}-join",
                f"{prefix}-close",
                close,
                gate=default_gate,
            ),
            _close_edge(
                f"edge:{prefix}-close-to-boundary",
                f"{prefix}-close",
                f"{prefix} closed",
                f"building-boundary:{prefix}-closed",
            ),
        ],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    f"edge:{prefix}-root-to-a",
                    f"edge:{prefix}-root-to-b",
                    f"edge:{prefix}-root-to-c",
                ],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            fan_in_group,
        ],
        "node_reroute_budgets": {lane_a: 1},
    }


def _nested_fan_plan(
    prefix: str,
    *,
    sibling_independence: list[str] | None = None,
) -> Mapping[str, Any]:
    """A NESTED fan-in graph: lane-a -> j1 (inner join), j1 -> j2 (outer join).

        root -(fan-out)-> lane-a  --\\
        root -(fan-out)-> lane-b  ---> j1  (inner fan-in of lane-a + lane-b)
        root -(fan-out)-> other2  -----------\\
                                  j1 ---------> j2  (outer fan-in of j1 + other2)
                                  j2 -> close

    lane-a is an INNER fan-in source feeding j1; j1 is itself a fan-in SOURCE
    feeding j2 (the nested / successor join). A reroute that LANDS on lane-a must
    re-verify the inner cohort (lane-b) AND re-run BOTH j1 (the direct join) and j2
    (the downstream nested join). Used by FIX #2 to drive the HOLD-before-cohort
    corner where the resume reconstruction would re-run j1 but SILENTLY SKIP j2.
    """

    root = f"brick-{prefix}-root"
    lane_a = f"brick-{prefix}-lane-a"
    lane_b = f"brick-{prefix}-lane-b"
    other2 = f"brick-{prefix}-other2"
    j1 = f"brick-{prefix}-j1"
    j2 = f"brick-{prefix}-j2"
    close = f"brick-{prefix}-close"
    default_gate = ["link-gate:default-transition"]
    inner_fan_in: dict[str, Any] = {
        "group_id": f"group:{prefix}-fan-in-1",
        "group_role": "fan_in",
        "member_ref_kind": "link_edge",
        "member_refs": [f"edge:{prefix}-a-to-j1", f"edge:{prefix}-b-to-j1"],
        "proof_limits": ["support topology label only"],
        "not_proven": ["synthesis quality"],
    }
    if sibling_independence is not None:
        inner_fan_in["sibling_independence"] = list(sibling_independence)
    outer_fan_in: dict[str, Any] = {
        "group_id": f"group:{prefix}-fan-in-2",
        "group_role": "fan_in",
        "member_ref_kind": "link_edge",
        "member_refs": [f"edge:{prefix}-j1-to-j2", f"edge:{prefix}-other2-to-j2"],
        "proof_limits": ["support topology label only"],
        "not_proven": ["synthesis quality"],
    }
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0609",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["parallel runtime execution"],
        "execution_order": [
            f"{prefix}-root",
            f"{prefix}-lane-a",
            f"{prefix}-lane-b",
            f"{prefix}-other2",
            f"{prefix}-j1",
            f"{prefix}-j2",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _brick_step(f"{prefix}-root", root, "agent-object:coo", f"edge:{prefix}-root-to-a"),
            _brick_step(f"{prefix}-lane-a", lane_a, "agent-object:qa", f"edge:{prefix}-a-to-j1"),
            _brick_step(f"{prefix}-lane-b", lane_b, "agent-object:qa", f"edge:{prefix}-b-to-j1"),
            _brick_step(f"{prefix}-other2", other2, "agent-object:qa", f"edge:{prefix}-other2-to-j2"),
            _brick_step(f"{prefix}-j1", j1, "agent-object:coo", f"edge:{prefix}-j1-to-j2"),
            _brick_step(f"{prefix}-j2", j2, "agent-object:coo", f"edge:{prefix}-j2-to-close"),
            _brick_step(f"{prefix}-close", close, "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{prefix}-root-to-a", f"{prefix}-root", f"{prefix}-lane-a", lane_a),
            _fwd_edge(f"edge:{prefix}-root-to-b", f"{prefix}-root", f"{prefix}-lane-b", lane_b),
            _fwd_edge(f"edge:{prefix}-root-to-other2", f"{prefix}-root", f"{prefix}-other2", other2),
            _fwd_edge(f"edge:{prefix}-a-to-j1", f"{prefix}-lane-a", f"{prefix}-j1", j1),
            _fwd_edge(f"edge:{prefix}-b-to-j1", f"{prefix}-lane-b", f"{prefix}-j1", j1),
            _fwd_edge(f"edge:{prefix}-j1-to-j2", f"{prefix}-j1", f"{prefix}-j2", j2, gate=default_gate),
            _fwd_edge(f"edge:{prefix}-other2-to-j2", f"{prefix}-other2", f"{prefix}-j2", j2),
            _fwd_edge(f"edge:{prefix}-j2-to-close", f"{prefix}-j2", f"{prefix}-close", close, gate=default_gate),
            _close_edge(
                f"edge:{prefix}-close-to-boundary",
                f"{prefix}-close",
                f"{prefix} closed",
                f"building-boundary:{prefix}-closed",
            ),
        ],
        "groups": [
            {
                "group_id": f"group:{prefix}-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    f"edge:{prefix}-root-to-a",
                    f"edge:{prefix}-root-to-b",
                    f"edge:{prefix}-root-to-other2",
                ],
                "proof_limits": ["support topology label only"],
                "not_proven": ["parallel runtime execution"],
            },
            inner_fan_in,
            outer_fan_in,
        ],
        "node_reroute_budgets": {lane_a: 1},
    }


def _reroute_once_callable(source_brick: str, target_brick: str):
    """Propose a reroute to target_brick ONLY on the FIRST call to source_brick.

    On the re-walk (second call) source_brick returns clean, so the cascade is
    bounded to one landing. Used to drive a reroute that lands on a fan-in source
    exactly once (cohort re-verification trigger).
    """

    seen: dict[str, int] = {}

    def _callable(request: Any) -> Mapping[str, Any]:
        seen[request.brick_instance_ref] = seen.get(request.brick_instance_ref, 0) + 1
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["parallel runtime execution"],
        }
        if request.brick_instance_ref == source_brick and seen[source_brick] == 1:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [target_brick],
            }
        return returned

    return _callable


def _fan_callable(*, held_brick: str | None = None, reroute_target: str | None = None):
    def _callable(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["parallel runtime execution"],
        }
        if held_brick and request.brick_instance_ref == held_brick and reroute_target:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [reroute_target],
            }
        return returned

    return _callable


def _reroute_callable(target_brick: str, propose_from: set[str]):
    def _callable(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }
        if request.brick_instance_ref in propose_from:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [target_brick],
            }
        return returned

    return _callable


def _reroute_callable_by_source(
    source_to_target: Mapping[str, str],
    *,
    min_call_count: Mapping[str, int] | None = None,
):
    seen: dict[str, int] = {}
    thresholds = dict(min_call_count or {})

    def _callable(request: Any) -> Mapping[str, Any]:
        seen[request.brick_instance_ref] = seen.get(request.brick_instance_ref, 0) + 1
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }
        target = source_to_target.get(request.brick_instance_ref)
        if target and seen[request.brick_instance_ref] >= thresholds.get(request.brick_instance_ref, 1):
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [target],
            }
        return returned

    return _callable


def _multi_ref_concern_callable(
    source_brick: str,
    related_boundary_refs: list[str],
    *,
    concern_kind: str = "implementation_gap",
):
    """Emit a VALID non-binding concern naming an explicit LIST of boundary refs.

    Used to drive the no-single-owner classifier seams through the real walker:
      - two resolving refs   -> ambiguous (multiple_reroute_addresses_no_single_owner)
      - empty list           -> none      (no_resolving_reroute_address)
      - one resolving + one garbage (brick- prefixed but undeclared) -> none
        (unresolvable_reroute_address: the co-occurring garbage is NOT silently
        dropped to single delivery -- it HOLDs so a human sees the bad address)
      - one building-boundary: sentinel + one undeclared brick ref (mixed) -> none

    The refs are passed verbatim, so an empty list exercises the present-concern /
    empty-related_boundary_refs path (still a valid concern: related_boundary_refs
    defaults to () in agent/return_fact.validate_transition_concern_evidence).
    """

    def _callable(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }
        if request.brick_instance_ref == source_brick:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": concern_kind,
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": list(related_boundary_refs),
            }
        return returned

    return _callable


def _raw_transition_concern_callable(source_brick: str, concern_value: Any):
    def _callable(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }
        if request.brick_instance_ref == source_brick:
            returned["transition_concern_evidence"] = concern_value
        return returned

    return _callable


def _invalid_concern_callable(source_brick: str, target_brick: str):
    def _callable(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }
        if request.brick_instance_ref == source_brick:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "verification_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [target_brick],
                "observation": "extra key is intentionally not admitted",
            }
        return returned

    return _callable


def _adapter_error_callable(failing_brick: str):
    def _callable(request: Any) -> Mapping[str, Any]:
        if request.brick_instance_ref == failing_brick:
            raise RuntimeError("intentional checker adapter interruption")
        return {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }

    return _callable


def _reroute_edge(
    edge_ref: str,
    src: str,
    tgt_step: str,
    tgt_brick: str,
    *,
    route_replay_plan: Mapping[str, Any],
    gate: list[str] | None = None,
) -> Mapping[str, Any]:
    return fixture_graph_link_edge(
        edge_ref,
        src,
        tgt_brick,
        target_step_ref=tgt_step,
        movement="reroute",
        route_replay_plan=route_replay_plan,
        declared_gate_refs=gate,
        falsy_declared_gate_refs_use_default=True,
    )


def _with_link_edge_gate(plan: Mapping[str, Any], edge_ref: str, gate: list[str]) -> Mapping[str, Any]:
    changed = copy.deepcopy(plan)
    for edge in changed.get("link_edges", []):
        if isinstance(edge, dict) and edge.get("edge_ref") == edge_ref:
            rows = edge.get("rows")
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                rows[0]["declared_gate_refs"] = list(gate)
                return changed
    raise ValueError(f"edge_ref not found for gate mutation: {edge_ref}")


def _with_link_edge_gate_sequence_policy(
    plan: Mapping[str, Any],
    edge_ref: str,
    *,
    declared_gate_refs: list[str],
    gate_sequence_policy: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Stamp a declared gate-sequence policy onto a FORWARD edge's Link row.

    The forward edge stays movement:"forward" (no reroute, no concern). The
    gate-sequence policy lets a caller/COO declare what loop control does when a
    declared gate is missing_required_facts vs sufficient -- used here to declare a
    pure forward gate-BLOCK (action:"HOLD") with no reroute/concern at all.
    """

    changed = copy.deepcopy(plan)
    for edge in changed.get("link_edges", []):
        if isinstance(edge, dict) and edge.get("edge_ref") == edge_ref:
            rows = edge.get("rows")
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                rows[0]["declared_gate_refs"] = list(declared_gate_refs)
                rows[0]["gate_sequence_policy"] = copy.deepcopy(gate_sequence_policy)
                return changed
    raise ValueError(f"edge_ref not found for gate-sequence-policy mutation: {edge_ref}")


def _onboard_approve_fire_plan(prefix: str) -> tuple[Mapping[str, Any], str]:
    plan, pending_target = _checker_plan(prefix, budget=1)
    changed = copy.deepcopy(plan)
    for edge in changed.get("link_edges", []):
        if not isinstance(edge, dict):
            continue
        rows = edge.get("rows")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            rows[0].pop("gate_sequence_policy", None)
    changed = _with_link_edge_gate_sequence_policy(
        changed,
        f"edge:{prefix}-design-to-build",
        declared_gate_refs=["link-gate:default-transition", "link-gate:coo"],
        gate_sequence_policy=[
            {
                "gate_ref": "link-gate:default-transition",
                "on_missing_required_facts": {
                    "action": "hold",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [f"observation:{prefix}-default-transition-missing"],
                    "required_disposition_owner": "caller-or-coo",
                },
                "on_sufficient": {"action": "next", "next_gate_ref": "link-gate:coo"},
            },
            {
                "gate_ref": "link-gate:coo",
                "on_missing_required_facts": {
                    "action": "hold",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [f"observation:{prefix}-coo-review-required"],
                    "required_disposition_owner": "caller-or-coo",
                },
                "on_sufficient": {"action": "forward"},
            }
        ],
    )
    return changed, pending_target


def _raw_link_rows(root: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    path = root / "raw" / "link.jsonl"
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, Mapping):
            rows.append(value)
    return rows


def _link_row_lifecycle_value(row: Mapping[str, Any], flat_key: str, nested_key: str) -> str:
    value = row.get(flat_key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    nested = row.get("transition_lifecycle")
    if isinstance(nested, Mapping):
        nested_value = nested.get(nested_key)
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value.strip()
    return ""


def _full_chain_replay_plan() -> tuple[Mapping[str, Any], Mapping[str, str]]:
    prefix = "bapr-loop0-b5-c3"
    step_refs = {
        "a1": f"{prefix}-a1",
        "b1": f"{prefix}-b1",
        "c1": f"{prefix}-c1",
        "a2": f"{prefix}-a2",
        "b2": f"{prefix}-b2",
        "c2": f"{prefix}-c2",
        "d2": f"{prefix}-d2",
    }
    bricks = {name: f"brick-{step}" for name, step in step_refs.items()}
    default_gate = ["link-gate:default-transition"]
    route_plan = {
        "route_replay_ref": "route-replay:bapr-loop0-b5-c3-full-chain",
        "author_ref": "coo:bapr-loop0-b5-c3",
        "authoring_basis_refs": ["observation:bapr-loop0-b5-c3-chain-needs-replay"],
        "immediate_target_ref": bricks["a2"],
        "source_brick_refs": [bricks["c1"]],
        "route_reason_refs": ["observation:bapr-loop0-b5-c3-chain-needs-replay"],
        "affected_downstream_refs": [bricks["d2"]],
        "replay_segment_refs": [bricks["b2"], bricks["c2"]],
        "max_attempts": 1,
        "proof_limits": _proof_limits(),
        "not_proven": ["semantic correctness of the replay scope"],
    }
    plan = {
        "plan_ref": "building-plan:bapr-loop0-b5-c3",
        "owner_axis": "Brick",
        "building_id": "bapr-loop0-b5-c3-0530",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["semantic correctness of the replay scope"],
        "execution_order": [
            step_refs["a1"],
            step_refs["b1"],
            step_refs["c1"],
            step_refs["a2"],
            step_refs["b2"],
            step_refs["c2"],
            step_refs["d2"],
        ],
        "brick_steps": [
            _brick_step(step_refs["a1"], bricks["a1"], "agent-object:coo", "edge:bapr-loop0-b5-c3-a1-to-b1"),
            _brick_step(step_refs["b1"], bricks["b1"], "agent-object:dev", "edge:bapr-loop0-b5-c3-b1-to-c1"),
            _brick_step(step_refs["c1"], bricks["c1"], "agent-object:qa", "edge:bapr-loop0-b5-c3-c1-to-a2"),
            _brick_step(step_refs["a2"], bricks["a2"], "agent-object:coo", "edge:bapr-loop0-b5-c3-a2-to-b2"),
            _brick_step(step_refs["b2"], bricks["b2"], "agent-object:dev", "edge:bapr-loop0-b5-c3-b2-to-c2"),
            _brick_step(step_refs["c2"], bricks["c2"], "agent-object:qa", "edge:bapr-loop0-b5-c3-c2-to-d2"),
            _brick_step(step_refs["d2"], bricks["d2"], "agent-object:coo", "edge:bapr-loop0-b5-c3-d2-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge("edge:bapr-loop0-b5-c3-a1-to-b1", step_refs["a1"], step_refs["b1"], bricks["b1"]),
            _fwd_edge("edge:bapr-loop0-b5-c3-b1-to-c1", step_refs["b1"], step_refs["c1"], bricks["c1"]),
            _reroute_edge(
                "edge:bapr-loop0-b5-c3-c1-to-a2",
                step_refs["c1"],
                step_refs["a2"],
                bricks["a2"],
                route_replay_plan=route_plan,
                gate=default_gate,
            ),
            _fwd_edge("edge:bapr-loop0-b5-c3-a2-to-b2", step_refs["a2"], step_refs["b2"], bricks["b2"]),
            _fwd_edge("edge:bapr-loop0-b5-c3-b2-to-c2", step_refs["b2"], step_refs["c2"], bricks["c2"]),
            _fwd_edge("edge:bapr-loop0-b5-c3-c2-to-d2", step_refs["c2"], step_refs["d2"], bricks["d2"]),
            _close_edge(
                "edge:bapr-loop0-b5-c3-d2-to-boundary",
                step_refs["d2"],
                "bapr-loop0-b5-c3 closed",
                "building-boundary:bapr-loop0-b5-c3-closed",
            ),
        ],
        "node_reroute_budgets": {
            bricks["a2"]: 1,
            bricks["b2"]: 1,
            bricks["c2"]: 1,
        },
    }
    refs = {
        "source": bricks["c1"],
        "target": bricks["a2"],
        "replay_1": bricks["b2"],
        "replay_2": bricks["c2"],
        "target_step": step_refs["a2"],
        "replay_1_step": step_refs["b2"],
        "replay_2_step": step_refs["c2"],
        "route_replay_ref": route_plan["route_replay_ref"],
    }
    return plan, refs


def _step_bricks(result: Any) -> list[str]:
    return [r.preparation.brick_instance_ref for r in result.step_results]


def _adopted_records(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [r for r in records if not r.get("disposition_required")]


def _held_records(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [r for r in records if r.get("disposition_required")]


_STRUCTURED_FIELD_OBSERVATION_KEYS = {
    "kind",
    "schema_version",
    "brick_required_fields",
    "observed_fields",
    "gate_required_fields",
    "missing_from_observed",
    "demanded_beyond_brick",
}

_FORBIDDEN_JUDGMENT_LABEL_VALUES = {
    "missing_required_facts",
    "forward",
    "hold",
    "stop",
    "reroute",
}

_FORBIDDEN_JUDGMENT_KEYS = {
    "failing_axis",
    "fault",
    "failed",
    "failure",
    "success",
    "missing_required_facts",
}


def _walk_mapping(value: Any):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mapping(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mapping(child)


def _forbidden_judgment_label_findings(record: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for mapping in _walk_mapping(record):
        for key, value in mapping.items():
            key_text = str(key)
            normalized_key = key_text.lower().strip()
            if normalized_key in _FORBIDDEN_JUDGMENT_KEYS:
                findings.append(f"forbidden judgment key {key_text}")
            if "judgment" in normalized_key or normalized_key.endswith("label"):
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, str) and item.lower().strip() in _FORBIDDEN_JUDGMENT_LABEL_VALUES:
                        findings.append(f"forbidden judgment label {key_text}={item}")
    return findings


def _run(plan: Mapping[str, Any], callable_, repo: Path):
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier

    with checker_temp_path("bp-bapr-loop0-") as tmp:
        result = run_building_plan(
            plan,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        frontier = observe_building_frontier(result.lifecycle_write.root, repo_root=repo)
        records = list(getattr(result, "_dynamic_walker_reroute_records", ()))
        object.__setattr__(
            result,
            "_checker_carry_trace_facts",
            tuple(_carry_trace_facts_from_root(result.lifecycle_write.root)),
        )
        return result, frontier, records


def _run_with_retained_root(plan: Mapping[str, Any], callable_, repo: Path):
    tmp = tempfile.TemporaryDirectory(prefix="bp-bapr-loop0-retained-")
    result, frontier, records = _run_to_output_root(plan, callable_, repo, Path(tmp.name))
    object.__setattr__(result, "_checker_tempdir", tmp)
    return result, frontier, records


def _run_to_output_root(
    plan: Mapping[str, Any],
    callable_,
    repo: Path,
    output_root: Path,
):
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier

    result = run_building_plan(
        plan,
        output_root=output_root,
        overwrite_existing=True,
        local_callables={"callable:local:agent-invoke0-smoke": callable_},
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )
    frontier = observe_building_frontier(result.lifecycle_write.root, repo_root=repo)
    records = list(getattr(result, "_dynamic_walker_reroute_records", ()))
    object.__setattr__(
        result,
        "_checker_carry_trace_facts",
        tuple(_carry_trace_facts_from_root(result.lifecycle_write.root)),
    )
    return result, frontier, records


def _run_with_fanout_pool(
    plan: Mapping[str, Any],
    callable_,
    repo: Path,
    output_root: Path,
    *,
    pool_size: int,
):
    original = os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE")
    os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = str(pool_size)
    try:
        return _run_to_output_root(plan, callable_, repo, output_root)
    finally:
        if original is None:
            os.environ.pop("BRICK_FANOUT_DISPATCH_POOL_SIZE", None)
        else:
            os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = original


def _run_frontier_root_with_fanout_pool(
    plan: Mapping[str, Any],
    callable_,
    repo: Path,
    output_root: Path,
    *,
    pool_size: int,
):
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.run import (
        ChatSessionParkFrontierEvidenceWritten,
        run_building_plan,
    )

    original = os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE")
    os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = str(pool_size)
    try:
        try:
            result = run_building_plan(
                plan,
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": callable_},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
            root = result.lifecycle_write.root
            return root, observe_building_frontier(root, repo_root=repo)
        except ChatSessionParkFrontierEvidenceWritten as parked:
            root = parked.building_root
            return root, observe_building_frontier(root, repo_root=repo)
    finally:
        if original is None:
            os.environ.pop("BRICK_FANOUT_DISPATCH_POOL_SIZE", None)
        else:
            os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = original


def _resume_with_fanout_pool(
    building_root: Path,
    callable_,
    repo: Path,
    *,
    pool_size: int,
):
    from brick_protocol.support.operator.run import resume_building_plan

    original = os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE")
    os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = str(pool_size)
    try:
        return resume_building_plan(
            building_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
    finally:
        if original is None:
            os.environ.pop("BRICK_FANOUT_DISPATCH_POOL_SIZE", None)
        else:
            os.environ["BRICK_FANOUT_DISPATCH_POOL_SIZE"] = original


def _step_output_recorded(root: Path, step_ref: str) -> bool:
    return (root / "work" / "step-outputs" / f"{step_ref}-attempt-1" / "step-output.json").is_file()


def _step_output_path(root: Path, step_ref: str, attempt: int) -> Path:
    return root / "work" / "step-outputs" / f"{step_ref}-attempt-{attempt}" / "step-output.json"


def _assert_revision_fan_in_wait_all_observed(
    *,
    label: str,
    root: Path,
    step_bricks: Sequence[str],
    prefix: str,
    new_step_ref: str,
    mutate_expected_required_sources: bool = False,
) -> list[str]:
    join_step_ref = f"{prefix}-join"
    new_brick_ref = f"brick-{new_step_ref}"
    join_brick_ref = f"brick-{join_step_ref}"
    required_sources = [
        f"{prefix}-lane-a",
        f"{prefix}-lane-b",
        new_step_ref,
    ]
    if mutate_expected_required_sources:
        required_sources = required_sources[:-1]
    violations: list[str] = []
    if not _step_output_path(root, new_step_ref, 1).is_file():
        violations.append(f"{label}: revision-added fan-in source did not run live")
    if new_brick_ref not in step_bricks:
        violations.append(f"{label}: resumed step list does not include revision source")
    if join_brick_ref not in step_bricks:
        violations.append(f"{label}: resumed step list does not include fan-in join")
    if new_brick_ref in step_bricks and join_brick_ref in step_bricks:
        if step_bricks.index(join_brick_ref) < step_bricks.index(new_brick_ref):
            violations.append(
                f"{label}: fan-in join ran before revision-added source completed"
            )
    if mutate_expected_required_sources and new_brick_ref in step_bricks:
        mutated_step_bricks = [brick for brick in step_bricks if brick != new_brick_ref]
        if join_brick_ref in mutated_step_bricks:
            violations.append(
                f"{label}: early-completion expectation omitted the revision-added source"
            )
    from brick_protocol.support.operator.walker_resume import (
        _read_written_dynamic_plan,
    )
    from brick_protocol.support.operator.plan_graph import (
        _graph_fan_in_sources_by_target_step_ref,
        _linear_plan_from_graph_plan,
    )
    from brick_protocol.support.recording.declaration_packets import (
        latest_valid_declared_plan,
    )

    _plan_after, evidence_after = _read_written_dynamic_plan(root)
    latest_plan = latest_valid_declared_plan(root)
    _linear_plan, graph_context = _linear_plan_from_graph_plan(latest_plan)
    graph_required = list(
        _graph_fan_in_sources_by_target_step_ref(graph_context).get(join_step_ref, ())
    )
    if graph_required != required_sources:
        violations.append(
            f"{label}: revised graph fan-in sources drifted "
            f"(expected={required_sources} observed={graph_required})"
        )
    observations = [
        item
        for item in evidence_after.get("fan_in_wait_all_observations", [])
        if isinstance(item, Mapping)
        and item.get("target_step_ref") == join_step_ref
    ]
    if observations:
        observed_required = list(observations[-1].get("required_source_step_refs", []))
        if observed_required != required_sources:
            violations.append(
                f"{label}: fan-in wait-all required sources drifted "
                f"(expected={required_sources} observed={observed_required})"
            )
        if new_step_ref not in list(observations[-1].get("observed_source_step_refs", [])):
            violations.append(
                f"{label}: revision-added source missing from observed fan-in sources"
            )
    return violations


def _f1_assert_surviving_sibling_outputs(
    *,
    mode: str,
    root: Path,
    prefix: str,
) -> list[str]:
    violations: list[str] = []
    for lane in ("lane-a", "lane-c"):
        step_ref = f"{prefix}-{lane}"
        if not _step_output_recorded(root, step_ref):
            violations.append(
                f"f1-{mode}: survivor {step_ref} did not persist step-output.json"
            )
    return violations


def _f1_assert_frontier_stopped_before_closure(
    *,
    mode: str,
    frontier: Mapping[str, Any],
) -> list[str]:
    frontier_kind = frontier.get("frontier_kind")
    if frontier_kind in {"complete", "closure_pending"}:
        return [f"f1-{mode}: sibling interruption surfaced as forbidden frontier={frontier_kind}"]
    return []


_P6C_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)
_P6C_VOLATILE_TIME_KEYS = {
    "generatedAtTime",
    "recorded_at",
    "time",
}


def _p6c_normalize_text(text: str, root: Path) -> str:
    normalized = text
    replacements = [
        (str(root.resolve()), "<BUILDING_ROOT>"),
        (str(root.parent.resolve()), "<OUTPUT_ROOT>"),
    ]
    for source, target in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(source, target)
    return _P6C_TIMESTAMP_RE.sub("<TIMESTAMP>", normalized)


def _p6c_normalize_json(value: Any, root: Path, *, key_name: str = "") -> Any:
    if key_name in _P6C_VOLATILE_TIME_KEYS and isinstance(value, str):
        return "<TIMESTAMP>"
    if isinstance(value, Mapping):
        return {
            str(key): _p6c_normalize_json(child, root, key_name=str(key))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_p6c_normalize_json(child, root) for child in value]
    if isinstance(value, str):
        return _p6c_normalize_text(value, root)
    return value


def _p6c_normalized_evidence_files(root: Path) -> dict[str, str]:
    selected: list[Path] = [root / "evidence" / "evidence-manifest.json"]
    selected.extend(path for path in sorted((root / "evidence" / "spine").rglob("*")) if path.is_file())
    selected.append(root / "work" / "building-map.json")
    normalized: dict[str, str] = {}
    for path in selected:
        if not path.is_file():
            raise AssertionError(f"P6-C evidence file missing: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            value = json.loads(text)
            normalized[relative] = json.dumps(
                _p6c_normalize_json(value, root),
                sort_keys=True,
                separators=(",", ":"),
            )
        elif path.suffix == ".jsonl":
            rows = [
                json.dumps(
                    _p6c_normalize_json(json.loads(line), root),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for line in text.splitlines()
                if line.strip()
            ]
            normalized[relative] = "\n".join(rows)
        else:
            normalized[relative] = _p6c_normalize_text(text, root)
    return normalized


def _event_handshake_fan_callable(*, slow_lane: str, fast_lane: str):
    """Build a fan-out callable whose arrival order is EVENT-driven, not timed.

    D3 evidence-shape redesign (벽시계 상한 금지 / 숫자 조정 금지): the previous
    fixture leaned on relative sleep durations to make the FAST lane finish
    BEFORE the SLOW lane -- an arrival-order inversion relative to
    declared/frontier order -- so the drain's re-sort into frontier order was
    observably load-bearing. A wall-clock race is flaky under CI load and drifts
    when the numbers are "adjusted". This twin proves the SAME two structural
    facts with ``threading.Event`` handshakes and NO duration literal:

      * concurrency (max_active >= 2): the slow lane BLOCKS until the fast lane
        has STARTED, which is only reachable if both lanes are in-flight at once
        (a pool=1 serial drain can never satisfy it, so pool=1 must NOT block --
        see the deadlock guard below).
      * arrival inversion: the slow lane additionally BLOCKS until the fast lane
        has COMPLETED, so the fast lane's completion is GUARANTEED to be recorded
        before the slow lane's -- structurally, not by winning a timing race.

    ``handshake_engaged`` is recorded True only when BOTH events were observed by
    the concurrent (pool>1) run; a pool=1 caller returns without waiting so the
    serial drain never deadlocks. Support evidence only; the callable authors no
    Movement, success, or quality.
    """

    lock = threading.Lock()
    state = {
        "active": 0,
        "max_active": 0,
        "completion_order": [],
        "handshake_engaged": False,
    }
    fast_started = threading.Event()
    fast_completed = threading.Event()
    slow_started = threading.Event()

    def _callable(request: Any) -> Mapping[str, Any]:
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        try:
            # Deterministic pool discriminator: a pool>1 run engages the event
            # handshake (guaranteeing concurrency + arrival inversion structurally);
            # a serial pool=1 drain skips it so it can NEVER deadlock waiting on a
            # fast lane that has not been dispatched yet. Reading the declared pool
            # size is race-free, unlike sampling the live active count.
            try:
                pool_size = int(os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE", "1"))
            except ValueError:
                pool_size = 1
            concurrent = pool_size > 1
            if request.brick_instance_ref == fast_lane:
                # FAST lane: announce start, then (concurrent only) BLOCK until the
                # SLOW lane has also started before completing. This keeps BOTH
                # lanes in-flight at once (max_active>=2, structural concurrency)
                # while still COMPLETING before the slow lane (arrival inversion,
                # since the slow lane waits on this lane's completion below).
                fast_started.set()
                if concurrent:
                    slow_started.wait()
                return {
                    "observed_evidence": [f"obs {request.brick_instance_ref}"],
                    "not_proven": ["semantic correctness", "provider behavior"],
                }
            if request.brick_instance_ref == slow_lane:
                # SLOW lane: announce start (releasing the fast lane), then BLOCK
                # until the fast lane has COMPLETED. Only the concurrent (pool>1)
                # run engages the handshake; a serial pool=1 drain skips the waits
                # so it can never deadlock waiting on a fast lane not yet dispatched.
                slow_started.set()
                if concurrent:
                    fast_started.wait()
                    fast_completed.wait()
                    engaged_started = fast_started.is_set()
                    engaged_completed = fast_completed.is_set()
                    if engaged_started and engaged_completed:
                        with lock:
                            state["handshake_engaged"] = True
                return {
                    "observed_evidence": [f"obs {request.brick_instance_ref}"],
                    "not_proven": ["semantic correctness", "provider behavior"],
                }
            return {
                "observed_evidence": [f"obs {request.brick_instance_ref}"],
                "not_proven": ["semantic correctness", "provider behavior"],
            }
        finally:
            with lock:
                state["completion_order"].append(request.brick_instance_ref)
                state["active"] -= 1
            if request.brick_instance_ref == fast_lane:
                fast_completed.set()

    def _stats() -> Mapping[str, Any]:
        with lock:
            return {
                "max_active": int(state["max_active"]),
                "completion_order": list(state["completion_order"]),
                "handshake_engaged": bool(state["handshake_engaged"]),
            }

    setattr(_callable, "stats", _stats)
    return _callable


def _p6c_timed_fan_callable(*, prefix: str):
    # D3: the p6c fan fixture's lane-b (fast) must arrive before lane-a (slow) to
    # invert declared/frontier order. Event handshake, no duration literal.
    return _event_handshake_fan_callable(
        slow_lane=f"brick-{prefix}-lane-a",
        fast_lane=f"brick-{prefix}-lane-b",
    )


def _p4_two_stage_timed_callable(*, prefix: str):
    # D3: the p4 resume fan fixture's lane-d (fast) must arrive before lane-c
    # (slow). Event handshake, no duration literal.
    return _event_handshake_fan_callable(
        slow_lane=f"brick-{prefix}-lane-c",
        fast_lane=f"brick-{prefix}-lane-d",
    )


def _carry_trace_facts(result: Any) -> list[Mapping[str, Any]]:
    cached = getattr(result, "_checker_carry_trace_facts", None)
    if isinstance(cached, tuple):
        return [fact for fact in cached if isinstance(fact, Mapping)]
    return _carry_trace_facts_from_root(result.lifecycle_write.root)


def _carry_trace_facts_from_root(root: Path) -> list[Mapping[str, Any]]:
    path = root / "evidence" / "claim_trace" / "link" / "carry_trace.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    facts = value.get("facts", [])
    return [fact for fact in facts if isinstance(fact, Mapping)]


def _carry_budget_fact_bodies(result: Any) -> list[Mapping[str, Any]]:
    bodies: list[Mapping[str, Any]] = []
    for fact in _carry_trace_facts(result):
        body = fact.get("fact")
        if isinstance(body, Mapping) and body.get("trace_role") == "carry_budget_observation":
            bodies.append(body)
    return bodies


def _node_budget_trace_violations(
    bodies: Sequence[Mapping[str, Any]],
    *,
    target: str,
    expected_budget: int,
    expected_landings: int,
    require_exhausted: bool,
) -> list[str]:
    matches = [
        body
        for body in bodies
        if body.get("budget_kind") == "node_reroute_budget"
        and body.get("target_boundary_ref") == target
    ]
    if not matches:
        return ["carry-budget: missing node_reroute_budget observation"]
    body = matches[0]
    violations: list[str] = []
    if body.get("declared_budget") != expected_budget:
        violations.append(f"carry-budget: declared_budget drifted ({body.get('declared_budget')})")
    if body.get("observed_reroute_landings") != expected_landings:
        violations.append(
            "carry-budget: observed_reroute_landings drifted "
            f"({body.get('observed_reroute_landings')})"
        )
    if require_exhausted and body.get("budget_exhausted") is not True:
        violations.append("carry-budget: budget exhaustion was not recorded in carry_trace")
    if require_exhausted and body.get("disposition_required") is not True:
        violations.append("carry-budget: disposition_required was not recorded in carry_trace")
    if not body.get("carry_budget_evidence_ref"):
        violations.append("carry-budget: carry_budget_evidence_ref missing")
    return violations


def _current_hold_paused_at_ref(building_root: Path) -> str | None:
    """The CURRENT hold's identity (``link-transition:<reroute>``) or None.

    FIX 2 (0611): a disposition row must be ADDRESSED to the hold it disposes.
    This mirrors what a real human/COO author does: read the held record from
    the written evidence and echo its identity into the row.
    """

    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
    from brick_protocol.support.operator.walker_resume import _read_written_dynamic_plan

    try:
        _plan, evidence = _read_written_dynamic_plan(building_root)
    except (OSError, ValueError):
        return None
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping) or not evidence.get("held"):
        return None
    return _hold_paused_at_ref(hold)


_COMPLIANT_RE_INSTRUCTION = (
    "Done endline: continue the bounded routing fixture and return the declared "
    "checker evidence before DONE. Proof must be executable in the receiving "
    "lane. Repairs outside the receiving lane's scope are COO gate items, not "
    "re-dispatch."
)


def _append_disposition_row(
    building_root: Path,
    *,
    building_id: str,
    pending_target_ref: str,
    action: str,
    author_ref: str = "human:smith",
    budget_increment: int | None = None,
    reason_refs: list[str] | None = None,
    resumed_from_ref: str | None = None,
) -> None:
    # FIX 2 (0611): address THE CURRENT hold by default (identity match is now
    # required by walker_resume._read_disposition_row). ``resumed_from_ref``
    # stays overridable so cases can author a WRONG-hold row deliberately.
    if resumed_from_ref is None:
        resumed_from_ref = (
            _current_hold_paused_at_ref(building_root)
            or f"link-transition:disposition-{action}"
        )
    row: dict[str, Any] = {
        "raw_ref": f"raw:link:disposition:{action}",
        "building_id": building_id,
        "step_ref": f"human-disposition-{action}",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_resumed_from_ref": resumed_from_ref,
        "transition_lifecycle_pending_target_ref": pending_target_ref,
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": action,
        "transition_author_ref": author_ref,
    }
    if budget_increment is not None:
        row["transition_lifecycle_budget_increment"] = budget_increment
    if reason_refs is not None:
        # MAIL-REPAIR (0611): reason_refs is an ADMITTED transition_lifecycle key
        # (link/transition.TRANSITION_LIFECYCLE_ALLOWED_KEYS); the disposition
        # row's reason ADDRESSES are truck-eligible runtime mail (B3 lane 2).
        row["transition_lifecycle_reason_refs"] = list(reason_refs)
    if action == "reroute":
        row["transition_lifecycle_re_instruction"] = _COMPLIANT_RE_INSTRUCTION
    with (building_root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def check(repo: Path) -> list[str]:
    _ensure_import_path(repo)
    violations: list[str] = []

    # G5-1: run_building_plan has no walker_mode parameter and always enters the
    # dynamic graph walker.
    from brick_protocol.link.transition import DISPOSITION_ACTIONS
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.plan_validation import validate_declared_building_plan

    if (
        len(DISPOSITION_ACTIONS) != 4
        or DISPOSITION_ACTIONS[:3] != ("raise", "forward", "stop")
        or "reroute" not in DISPOSITION_ACTIONS
    ):
        violations.append(
            "human-reroute-disposition: DISPOSITION_ACTIONS must pin "
            "raise/forward/stop/reroute exactly"
        )

    gate_plan_green = {
        "plan_ref": "building-plan:bapr-loop0-declared-gate-green",
        "owner_axis": "Brick",
        "selected_adapter_ref": "adapter:local",
        "steps": [
            {
                "step_ref": "bapr-loop0-declared-gate-green-step",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:bapr-loop0-declared-gate-green",
                        "brick_instance_ref": "brick-bapr-loop0-declared-gate-green-source",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:bapr-loop0-declared-gate-green",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": "link-row:bapr-loop0-declared-gate-green",
                        "movement": "forward",
                        "target_ref": "brick-bapr-loop0-declared-gate-green-target",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    },
                ],
            }
        ],
    }
    try:
        validate_declared_building_plan(gate_plan_green, repo_root=repo)
    except ValueError as exc:
        violations.append(
            "declared-gate-refs: explicit link-gate:default-transition was rejected "
            f"({exc})"
        )
    gate_plan_red = copy.deepcopy(gate_plan_green)
    first_link_row = gate_plan_red["steps"][0]["rows"][2]
    if isinstance(first_link_row, dict):
        first_link_row.pop("declared_gate_refs", None)
    try:
        validate_declared_building_plan(gate_plan_red, repo_root=repo)
    except ValueError as exc:
        if "declared_gate_refs" not in str(exc):
            violations.append(
                "declared-gate-refs: missing declared_gate_refs produced wrong error "
                f"({exc})"
            )
    else:
        violations.append(
            "declared-gate-refs: active post-expansion Link row missing "
            "declared_gate_refs was not rejected"
        )

    auto_prefix = "bapr-loop0-g5-1-auto-graph"
    auto_graph_plan, auto_graph_target = _checker_plan(auto_prefix, budget=2)
    with checker_temp_path("bp-bapr-g5-1-auto-") as tmp:
        auto_graph_result = run_building_plan(
            auto_graph_plan,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    auto_graph_target,
                    {f"brick-{auto_prefix}-review"},
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        auto_graph_frontier = observe_building_frontier(
            auto_graph_result.lifecycle_write.root,
            repo_root=repo,
        )
        auto_graph_evidence = getattr(auto_graph_result, "_dynamic_walker_evidence", {})
        if not isinstance(auto_graph_evidence, Mapping) or auto_graph_evidence.get("walker_mode") != "dynamic":
            violations.append("g5-1: graph plan did not record dynamic walker evidence")
        if not tuple(getattr(auto_graph_result, "_dynamic_walker_reroute_records", ())):
            violations.append("g5-1: graph plan did not record dynamic reroute evidence")
        if auto_graph_frontier["frontier_kind"] not in {"complete", "closure_pending"}:
            violations.append(
                "g5-1: graph plan did not reach a dynamic terminal frontier "
                f"(frontier={auto_graph_frontier['frontier_kind']})"
            )

    # Invariant A: budget available -> agent-proposed reroute ADOPTED, target is an
    # existing node, budget consumed per landing, building proceeds.
    plan_a, b2_a = _checker_plan("bapr-loop0-adopt", budget=2)
    res_a, fr_a, rec_a = _run(plan_a, _reroute_callable(b2_a, {f"brick-bapr-loop0-adopt-review"}), repo)
    adopted_a = [r for r in rec_a if not r.get("disposition_required")]
    if not adopted_a:
        violations.append("adopt-case: agent-proposed reroute was not adopted under available budget")
    else:
        a0 = adopted_a[0]
        if a0.get("target_brick") != b2_a:
            violations.append("adopt-case: adopted target is not the agent-proposed existing node")
        if a0.get("attempt_number") != 1 or a0.get("node_budget") != 2:
            violations.append("adopt-case: per-node attempt/budget accounting wrong")
        if a0.get("transition_concern_binding") is not False:
            violations.append("adopt-case: adoption did not carry a non-binding (binding:false) concern")
    if fr_a["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(f"adopt-case: building did not proceed (frontier={fr_a['frontier_kind']})")
    bricks_a = [r.preparation.brick_instance_ref for r in res_a.step_results]
    if bricks_a.count(b2_a) < 2:
        violations.append("adopt-case: target node was not re-executed at runtime")

    # Invariant B: budget exhaustion -> HOLD (paused frontier, disposition_required,
    # support records but does not decide raise/forward/stop).
    plan_b, b2_b = _checker_plan("bapr-loop0-hold", budget=1)
    res_b, fr_b, rec_b = _run(
        plan_b,
        _reroute_callable(
            b2_b,
            {"brick-bapr-loop0-hold-design", "brick-bapr-loop0-hold-review"},
        ),
        repo,
    )
    held_b = [r for r in rec_b if r.get("disposition_required")]
    if fr_b["frontier_kind"] != "link_paused":
        violations.append(f"hold-case: exhaustion did not HOLD (frontier={fr_b['frontier_kind']})")
    if not held_b or not held_b[0].get("budget_exhausted"):
        violations.append("hold-case: no budget_exhausted HOLD record emitted")
    if held_b and held_b[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append("hold-case: HOLD did not require caller-or-coo disposition")
    carry_b = _carry_budget_fact_bodies(res_b)
    violations.extend(
        "hold-case: " + violation
        for violation in _node_budget_trace_violations(
            carry_b,
            target=b2_b,
            expected_budget=1,
            expected_landings=1,
            require_exhausted=True,
        )
    )
    if held_b:
        carry_ref_b = held_b[0].get("carry_budget_evidence_ref")
        if not carry_ref_b:
            violations.append("hold-case: HOLD record did not expose carry_budget_evidence_ref")
        elif not any(body.get("carry_budget_evidence_ref") == carry_ref_b for body in carry_b):
            violations.append("hold-case: HOLD carry_budget_evidence_ref did not resolve in carry_trace")
        lifecycle_b = fr_b.get("latest_transition_lifecycle", {})
        reason_refs = lifecycle_b.get("transition_lifecycle_reason_refs", [])
        if carry_ref_b and carry_ref_b in reason_refs:
            violations.append("hold-case: frontier reason_refs carried a support Carry evidence locator")
        if any(str(ref).startswith("evidence/") for ref in reason_refs):
            violations.append("hold-case: frontier reason_refs carried an evidence-file locator")
        lifecycle_carry_ref = lifecycle_b.get("transition_lifecycle_carry_budget_evidence_ref")
        if carry_ref_b and lifecycle_carry_ref != carry_ref_b:
            violations.append("hold-case: frontier did not expose the separate Carry budget evidence ref")
    negative_probe = _node_budget_trace_violations(
        [{"trace_role": "absence_placeholder"}],
        target=b2_b,
        expected_budget=1,
        expected_landings=1,
        require_exhausted=True,
    )
    if not negative_probe:
        violations.append("hold-case negative probe: all-placeholder carry_trace was not rejected")

    # B4 negative guard G5: a held Building with NO human/COO disposition row must
    # stay paused. resume_building_plan may raise a clear error, but it must not
    # silently forward or raise.
    from brick_protocol.support.operator.run import run_building_plan, resume_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier

    plan_g5, b2_g5 = _checker_plan("bapr-loop0-b4-no-disposition", budget=1)
    plan_g5 = dict(plan_g5)
    plan_g5.pop("node_reroute_budgets", None)
    with checker_temp_path("bp-bapr-b4-g5-") as tmp:
        res_g5 = run_building_plan(
            plan_g5,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    b2_g5,
                    {"brick-bapr-loop0-b4-no-disposition-review"},
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_g5 = res_g5.lifecycle_write.root
        before_g5 = observe_building_frontier(root_g5, repo_root=repo)
        try:
            resume_building_plan(
                root_g5,
                local_callables={
                    "callable:local:agent-invoke0-smoke": _reroute_callable(
                        b2_g5,
                        {"brick-bapr-loop0-b4-no-disposition-review"},
                    )
                },
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except ValueError:
            pass
        else:
            violations.append("b4-g5: resume without a disposition row did not reject")
        after_g5 = observe_building_frontier(root_g5, repo_root=repo)
        if before_g5["frontier_kind"] != "link_paused" or after_g5["frontier_kind"] != "link_paused":
            violations.append(
                "b4-g5: no-disposition resume did not stay link_paused "
                f"(before={before_g5['frontier_kind']} after={after_g5['frontier_kind']})"
            )

    # B4 negative guard G6: disposition_action is accepted only from human:/coo:
    # authored rows. support:/agent: rows are rejected by the resume reader.
    plan_g6, b2_g6 = _checker_plan("bapr-loop0-b4-bad-author", budget=1)
    plan_g6 = dict(plan_g6)
    plan_g6.pop("node_reroute_budgets", None)
    with checker_temp_path("bp-bapr-b4-g6-") as tmp:
        res_g6 = run_building_plan(
            plan_g6,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    b2_g6,
                    {"brick-bapr-loop0-b4-bad-author-review"},
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_g6 = res_g6.lifecycle_write.root
        _append_disposition_row(
            root_g6,
            building_id=res_g6.building_id,
            pending_target_ref=b2_g6,
            action="forward",
            author_ref="support:bad-author",
        )
        try:
            resume_building_plan(
                root_g6,
                local_callables={
                    "callable:local:agent-invoke0-smoke": _reroute_callable(
                        b2_g6,
                        {"brick-bapr-loop0-b4-bad-author-review"},
                    )
                },
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except ValueError:
            pass
        else:
            violations.append("b4-g6: support-authored disposition row was not rejected")

    # B4 positive guard: a human/COO forward disposition must not emit a
    # dangling observation ref in the regenerated movement claim trace.
    from support.checkers import check_building_lifecycle_path_shape

    plan_g7_forward, b2_g7_forward = _checker_plan("bapr-loop0-b4-forward-disposition", budget=1)
    with checker_temp_path("bp-bapr-b4-g7-forward-") as tmp:
        fake_repo = tmp / "repo"
        output_root_g7_forward = fake_repo / "project" / "brick-protocol" / "buildings"
        output_root_g7_forward.mkdir(parents=True)
        res_g7_forward = run_building_plan(
            plan_g7_forward,
            output_root=output_root_g7_forward,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    b2_g7_forward,
                    {
                        "brick-bapr-loop0-b4-forward-disposition-design",
                        "brick-bapr-loop0-b4-forward-disposition-review",
                    },
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_g7_forward = res_g7_forward.lifecycle_write.root
        before_g7_forward = observe_building_frontier(root_g7_forward, repo_root=repo)
        if before_g7_forward["frontier_kind"] != "link_paused":
            violations.append(
                "b4-g7-forward: forward-disposition fixture did not start paused "
                f"({before_g7_forward['frontier_kind']})"
            )
        _append_disposition_row(
            root_g7_forward,
            building_id=res_g7_forward.building_id,
            pending_target_ref=b2_g7_forward,
            action="forward",
            author_ref="coo:checker",
        )
        resume_building_plan(
            root_g7_forward,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    b2_g7_forward,
                    {
                        "brick-bapr-loop0-b4-forward-disposition-design",
                        "brick-bapr-loop0-b4-forward-disposition-review",
                    },
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        if check_building_lifecycle_path_shape.main(["--repo", str(fake_repo)]) != 0:
            violations.append(
                "b4-g7-forward: forward disposition emitted unresolved public fact refs "
                "in Building lifecycle evidence"
            )

    # B4 positive guard G7: a human/COO raise disposition with a finite
    # budget_increment resumes from a budget HOLD without route-reason refs
    # carrying support evidence locators. If the deterministic fixture re-HOLDs,
    # the later pause must explain the bounded-budget disposition semantics.
    plan_g7, b2_g7 = _checker_plan("bapr-loop0-b4-raise-resume", budget=1)
    with checker_temp_path("bp-bapr-b4-g7-") as tmp:
        callable_g7 = _reroute_callable(
            b2_g7,
            {
                "brick-bapr-loop0-b4-raise-resume-design",
                "brick-bapr-loop0-b4-raise-resume-review",
            },
        )
        res_g7 = run_building_plan(
            plan_g7,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_g7},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_g7 = res_g7.lifecycle_write.root
        before_g7 = observe_building_frontier(root_g7, repo_root=repo)
        if before_g7["frontier_kind"] != "link_paused":
            violations.append(
                "b4-g7: setup did not produce a budget HOLD before raise resume "
                f"(frontier={before_g7['frontier_kind']})"
            )
        _append_disposition_row(
            root_g7,
            building_id=res_g7.building_id,
            pending_target_ref=b2_g7,
            action="raise",
            author_ref="coo:smith",
            budget_increment=1,
        )
        try:
            resumed_g7 = resume_building_plan(
                root_g7,
                local_callables={"callable:local:agent-invoke0-smoke": callable_g7},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except ValueError as exc:
            violations.append(f"b4-g7: raise disposition resume crashed: {exc}")
        else:
            after_g7 = observe_building_frontier(
                resumed_g7.lifecycle_write.root,
                repo_root=repo,
            )
            lifecycle_g7 = after_g7.get("latest_transition_lifecycle", {})
            reason_refs_g7 = lifecycle_g7.get("transition_lifecycle_reason_refs", [])
            if any(str(ref).startswith("evidence/") for ref in reason_refs_g7):
                violations.append("b4-g7: resumed lifecycle reason_refs carried an evidence-file locator")
            carry_ref_g7 = lifecycle_g7.get("transition_lifecycle_carry_budget_evidence_ref")
            if not carry_ref_g7:
                violations.append("b4-g7: resumed/held lifecycle did not expose separate Carry budget evidence ref")
            elif not any(
                body.get("carry_budget_evidence_ref") == carry_ref_g7
                for body in _carry_budget_fact_bodies(resumed_g7)
            ):
                violations.append("b4-g7: lifecycle Carry budget evidence ref did not resolve in carry_trace")
            if after_g7["frontier_kind"] == "link_paused" and (
                "observation:reroute-hold-reason-target_node_budget_exhausted"
                not in reason_refs_g7
            ):
                violations.append(
                    "b4-g7: later pause after raise did not record bounded-budget exhaustion semantics"
                )

    # Invariant C: multiple non-self reroute landings on the SAME node draw the
    # SAME shared budget (no fresh budget) and the cascade is bounded. Self-reroute
    # is covered separately by CLOSURE-SELFREROUTE-GUARD-0616 below.
    plan_c, b2_c = _checker_plan("bapr-loop0-nested", budget=2)
    res_c, fr_c, rec_c = _run(
        plan_c,
        _reroute_callable(
            b2_c,
            {
                "brick-bapr-loop0-nested-design",
                "brick-bapr-loop0-nested-review",
                "brick-bapr-loop0-nested-close",
            },
        ),
        repo,
    )
    adopted_c = [r for r in rec_c if not r.get("disposition_required")]
    held_c = [r for r in rec_c if r.get("disposition_required")]
    if not all(r.get("target_brick") == b2_c for r in rec_c):
        violations.append("nested-case: a landing targeted a node other than the shared-budget node")
    if len(adopted_c) != 2:
        violations.append("nested-case: shared budget of 2 admitted other than 2 landings (no fresh budget)")
    if not held_c or not held_c[0].get("budget_exhausted"):
        violations.append("nested-case: nested cascade did not terminate at the shared budget (HOLD)")

    # Invariant D: target-existence + positive-budget guards on the module surface.
    from brick_protocol.support.operator.dynamic_walker import _node_reroute_budgets

    try:
        _node_reroute_budgets({"node_reroute_budgets": {"brick-not-a-node": 1}}, declared_bricks={"brick-real"})
    except ValueError:
        pass
    else:
        violations.append("guard: budget keyed to a non-existent node was not rejected")
    try:
        _node_reroute_budgets({"node_reroute_budgets": {"brick-real": 0}}, declared_bricks={"brick-real"})
    except ValueError:
        pass
    else:
        violations.append("guard: non-positive per-node budget was not rejected")

    # Invariant D expansion-resume probe: an approved revision carries
    # expansion_node_budgets by new step_ref, while resume must reattach a
    # Brick-ref keyed budget for the walker. This fixture reaches a budget HOLD,
    # lands rev-1 with one new node, then resumes by rerouting to that new node.
    from brick_protocol.support.recording.declaration_packets import (
        _declared_plan_hash,
        latest_valid_declared_plan,
        write_declared_plan_revision,
    )

    prefix_exp = "bapr-loop0-expansion-resume"
    plan_exp, old_target_exp, review_brick_exp, new_brick_exp = _expansion_resume_base_plan(prefix_exp)
    new_step_exp = new_brick_exp.removeprefix("brick-")
    with checker_temp_path("bp-bapr-expansion-resume-") as tmp:
        callable_exp = _reroute_callable(
            old_target_exp,
            {f"brick-{prefix_exp}-design", review_brick_exp},
        )
        res_exp = run_building_plan(
            plan_exp,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_exp},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_exp = res_exp.lifecycle_write.root
        before_exp = observe_building_frontier(root_exp, repo_root=repo)
        if before_exp["frontier_kind"] != "link_paused":
            violations.append(
                "expansion-resume: setup did not produce a budget HOLD before rev-1 "
                f"(frontier={before_exp['frontier_kind']})"
            )
        hold_ref_exp = _current_hold_paused_at_ref(root_exp) or "hold:expansion-resume"
        approval_ref_exp = "approval:bapr-loop0-expansion-resume"
        approval_row_exp = {
            "approval_evidence_ref": approval_ref_exp,
            "gate_ref": "link-gate:expansion-approval",
            "hold_class": "proposed_candidate_not_in_declared_set",
            "hold_paused_at_ref": hold_ref_exp,
        }
        with (root_exp / "work" / "expansion-approvals.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(approval_row_exp, separators=(",", ":")) + "\n")
        parent_plan_exp = latest_valid_declared_plan(root_exp)
        expanded_plan_exp, fragment_exp, budget_meta_exp = _expanded_plan_with_resume_node(
            parent_plan_exp,
            prefix=prefix_exp,
            new_step_ref=new_step_exp,
            new_brick_ref=new_brick_exp,
        )
        metadata_exp = {
            "extends_plan_hash": _declared_plan_hash(parent_plan_exp),
            "extends_plan_hash_algorithm": "sha256",
            "extends_plan_hash_basis": (
                "canonical sorted-key JSON of the pure declared-building-plan copy "
                "(runtime walker state excluded)"
            ),
            "expansion_fragment": fragment_exp,
            "expansion_node_budgets": budget_meta_exp["expansion_node_budgets"],
            "hold_paused_at_ref": hold_ref_exp,
        }
        birth_path_exp = root_exp / "work" / "declared-building-plan.json"
        birth_hash_before_exp = hashlib.sha256(
            birth_path_exp.read_bytes()
        ).hexdigest()
        try:
            rev_path_exp = write_declared_plan_revision(
                root_exp,
                expanded_plan_exp,
                metadata_exp,
                approval_ref_exp,
            )
        except ValueError as exc:
            violations.append(f"expansion-resume: rev-1 write rejected: {exc}")
        else:
            if rev_path_exp.name != "declared-building-plan.rev-1.json":
                violations.append(
                    "expansion-resume: revision writer did not create rev-1 "
                    f"({rev_path_exp.name})"
                )
            birth_hash_after_exp = hashlib.sha256(
                birth_path_exp.read_bytes()
            ).hexdigest()
            if birth_hash_after_exp != birth_hash_before_exp:
                violations.append("expansion-resume: base birth-certificate hash changed")
            _append_disposition_row(
                root_exp,
                building_id=res_exp.building_id,
                pending_target_ref=new_brick_exp,
                action="reroute",
                author_ref="coo:checker",
            )
            try:
                resumed_exp = resume_building_plan(
                    root_exp,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _reroute_callable(
                            old_target_exp,
                            {f"brick-{prefix_exp}-design", review_brick_exp},
                        )
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                violations.append(f"expansion-resume: resume onto rev-1 node crashed: {exc}")
            else:
                after_exp = observe_building_frontier(
                    resumed_exp.lifecycle_write.root,
                    repo_root=repo,
                )
                if after_exp["frontier_kind"] != "complete":
                    violations.append(
                        "expansion-resume: reroute onto revision node did not complete "
                        f"(frontier={after_exp['frontier_kind']})"
                    )
                if not _step_output_path(
                    resumed_exp.lifecycle_write.root,
                    new_step_exp,
                    1,
                ).is_file():
                    violations.append("expansion-resume: new revision node did not run live")
                from brick_protocol.support.operator.walker_resume import (
                    _read_written_dynamic_plan,
                )

                _plan_after_exp, evidence_after_exp = _read_written_dynamic_plan(
                    resumed_exp.lifecycle_write.root
                )
                budgets_after_exp = evidence_after_exp.get("node_reroute_budgets")
                landings_after_exp = evidence_after_exp.get("node_reroute_landings")
                if not (
                    isinstance(budgets_after_exp, Mapping)
                    and budgets_after_exp.get(new_brick_exp) == 1
                    and isinstance(landings_after_exp, Mapping)
                    and landings_after_exp.get(new_brick_exp) == 1
                ):
                    violations.append(
                        "expansion-resume: revision node reroute did not consume "
                        "the expansion_node_budgets value"
                    )
                resumed_records_exp = list(
                    getattr(resumed_exp, "_dynamic_walker_reroute_records", ())
                )
                if any(
                    record.get("target_brick") == new_brick_exp
                    and record.get("disposition_required")
                    and record.get("hold_reason") == "target_node_has_no_link_assigned_budget"
                    for record in resumed_records_exp
                ):
                    violations.append(
                        "expansion-resume: revision node still held for missing Link budget"
                    )

    # T10-S4 carry-forward: when rev-1 adds a NEW source to an existing fan-in
    # group, resume must read the revised member_refs at runtime and wait for
    # that source before running the convergence node.
    prefix_fan_exp = "bapr-loop0-expansion-fanin"
    plan_fan_exp = dict(_fan_plan(prefix_fan_exp, held_source=True))
    plan_fan_exp["expansion_budget"] = 1
    new_step_fan_exp = f"{prefix_fan_exp}-lane-c"
    new_brick_fan_exp = f"brick-{new_step_fan_exp}"
    with checker_temp_path("bp-bapr-expansion-fanin-") as tmp:
        res_fan_exp = run_building_plan(
            plan_fan_exp,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _fan_callable(
                    held_brick=f"brick-{prefix_fan_exp}-lane-b",
                    reroute_target=f"brick-{prefix_fan_exp}-join",
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_fan_exp = res_fan_exp.lifecycle_write.root
        before_fan_exp = observe_building_frontier(root_fan_exp, repo_root=repo)
        if before_fan_exp["frontier_kind"] != "link_paused":
            violations.append(
                "expansion-fanin: setup did not pause before fan-in join "
                f"(frontier={before_fan_exp['frontier_kind']})"
            )
        hold_ref_fan_exp = _current_hold_paused_at_ref(root_fan_exp) or "hold:expansion-fanin"
        approval_ref_fan_exp = "approval:bapr-loop0-expansion-fanin"
        with (root_fan_exp / "work" / "expansion-approvals.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "approval_evidence_ref": approval_ref_fan_exp,
                        "gate_ref": "link-gate:expansion-approval",
                        "hold_class": "proposed_candidate_not_in_declared_set",
                        "hold_paused_at_ref": hold_ref_fan_exp,
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
        parent_plan_fan_exp = latest_valid_declared_plan(root_fan_exp)
        expanded_plan_fan_exp, fragment_fan_exp = _expanded_fan_in_plan_with_revision_source(
            parent_plan_fan_exp,
            prefix=prefix_fan_exp,
            new_step_ref=new_step_fan_exp,
            new_brick_ref=new_brick_fan_exp,
        )
        try:
            write_declared_plan_revision(
                root_fan_exp,
                expanded_plan_fan_exp,
                {
                    "extends_plan_hash": _declared_plan_hash(parent_plan_fan_exp),
                    "extends_plan_hash_algorithm": "sha256",
                    "extends_plan_hash_basis": (
                        "canonical sorted-key JSON of the pure declared-building-plan "
                        "copy (runtime walker state excluded)"
                    ),
                    "expansion_fragment": fragment_fan_exp,
                    "expansion_node_budgets": {new_step_fan_exp: 1},
                    "hold_paused_at_ref": hold_ref_fan_exp,
                },
                approval_ref_fan_exp,
            )
        except ValueError as exc:
            violations.append(f"expansion-fanin: rev-1 write rejected: {exc}")
        else:
            _append_disposition_row(
                root_fan_exp,
                building_id=res_fan_exp.building_id,
                pending_target_ref=f"brick-{prefix_fan_exp}-join",
                action="forward",
                author_ref="coo:checker",
            )
            try:
                resumed_fan_exp = resume_building_plan(
                    root_fan_exp,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _fan_callable(
                            held_brick=f"brick-{prefix_fan_exp}-lane-b",
                            reroute_target=f"brick-{prefix_fan_exp}-join",
                        )
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                violations.append(f"expansion-fanin: resume over rev-1 crashed: {exc}")
            else:
                after_fan_exp = observe_building_frontier(
                    resumed_fan_exp.lifecycle_write.root,
                    repo_root=repo,
                )
                if after_fan_exp["frontier_kind"] != "complete":
                    violations.append(
                        "expansion-fanin: resumed fan-in revision did not complete "
                        f"(frontier={after_fan_exp['frontier_kind']})"
                    )
                positive_fan_exp = _assert_revision_fan_in_wait_all_observed(
                    label="expansion-fanin",
                    root=resumed_fan_exp.lifecycle_write.root,
                    step_bricks=_step_bricks(resumed_fan_exp),
                    prefix=prefix_fan_exp,
                    new_step_ref=new_step_fan_exp,
                )
                violations.extend(positive_fan_exp)
                mutated_fan_exp = _assert_revision_fan_in_wait_all_observed(
                    label="expansion-fanin-red",
                    root=resumed_fan_exp.lifecycle_write.root,
                    step_bricks=_step_bricks(resumed_fan_exp),
                    prefix=prefix_fan_exp,
                    new_step_ref=new_step_fan_exp,
                    mutate_expected_required_sources=True,
                )
                if not any(
                    "required sources drifted" in item
                    or "early-completion expectation" in item
                    or "revised graph fan-in sources drifted" in item
                    for item in mutated_fan_exp
                ):
                    violations.append(
                        "expansion-fanin-red: expectation mutation that drops the "
                        "revision-added source did not RED"
                    )

    # D2 RED: inject the live early-completion defect the positive fixture is
    # meant to catch. The walker sees a fan-in source map with the rev-added
    # source omitted, so the cohort replay/wait-all path can complete without
    # re-running that source. The checker must report that as RED.
    prefix_fan_exp_red = "bapr-loop0-expansion-fanin-live-red"
    plan_fan_exp_red = dict(_fan_plan(prefix_fan_exp_red, held_source=True))
    plan_fan_exp_red["expansion_budget"] = 1
    new_step_fan_exp_red = f"{prefix_fan_exp_red}-lane-c"
    new_brick_fan_exp_red = f"brick-{new_step_fan_exp_red}"
    join_step_fan_exp_red = f"{prefix_fan_exp_red}-join"
    with checker_temp_path("bp-bapr-expansion-fanin-red-") as tmp:
        res_fan_exp_red = run_building_plan(
            plan_fan_exp_red,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _fan_callable(
                    held_brick=f"brick-{prefix_fan_exp_red}-lane-b",
                    reroute_target=f"brick-{prefix_fan_exp_red}-join",
                )
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_fan_exp_red = res_fan_exp_red.lifecycle_write.root
        hold_ref_fan_exp_red = (
            _current_hold_paused_at_ref(root_fan_exp_red) or "hold:expansion-fanin-red"
        )
        approval_ref_fan_exp_red = "approval:bapr-loop0-expansion-fanin-live-red"
        with (root_fan_exp_red / "work" / "expansion-approvals.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "approval_evidence_ref": approval_ref_fan_exp_red,
                        "gate_ref": "link-gate:expansion-approval",
                        "hold_class": "proposed_candidate_not_in_declared_set",
                        "hold_paused_at_ref": hold_ref_fan_exp_red,
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
        parent_plan_fan_exp_red = latest_valid_declared_plan(root_fan_exp_red)
        expanded_plan_fan_exp_red, fragment_fan_exp_red = _expanded_fan_in_plan_with_revision_source(
            parent_plan_fan_exp_red,
            prefix=prefix_fan_exp_red,
            new_step_ref=new_step_fan_exp_red,
            new_brick_ref=new_brick_fan_exp_red,
        )
        try:
            write_declared_plan_revision(
                root_fan_exp_red,
                expanded_plan_fan_exp_red,
                {
                    "extends_plan_hash": _declared_plan_hash(parent_plan_fan_exp_red),
                    "extends_plan_hash_algorithm": "sha256",
                    "extends_plan_hash_basis": (
                        "canonical sorted-key JSON of the pure declared-building-plan "
                        "copy (runtime walker state excluded)"
                    ),
                    "expansion_fragment": fragment_fan_exp_red,
                    "expansion_node_budgets": {new_step_fan_exp_red: 1},
                    "hold_paused_at_ref": hold_ref_fan_exp_red,
                },
                approval_ref_fan_exp_red,
            )
        except ValueError as exc:
            violations.append(f"expansion-fanin-live-red: rev-1 write rejected: {exc}")
        else:
            _append_disposition_row(
                root_fan_exp_red,
                building_id=res_fan_exp_red.building_id,
                pending_target_ref=f"brick-{prefix_fan_exp_red}-join",
                action="forward",
                author_ref="coo:checker",
            )
            from brick_protocol.support.operator import walker_fan_in as walker_fan_in_module
            from brick_protocol.support.operator import walker_kernel as walker_kernel_module
            from brick_protocol.support.operator import walker_resume as walker_resume_module

            original_kernel_sources = walker_kernel_module._graph_fan_in_sources_by_target_step_ref
            original_fan_in_sources = walker_fan_in_module._graph_fan_in_sources_by_target_step_ref
            original_kernel_linear_plan = walker_kernel_module._linear_plan_from_graph_plan
            original_resume_linear_plan = walker_resume_module._linear_plan_from_graph_plan
            original_kernel_successors = (
                walker_kernel_module._graph_successor_step_refs_by_source_step_ref
            )

            def _drop_revision_source(original):
                def _patched(graph_context):
                    sources_by_target = dict(original(graph_context))
                    sources = tuple(
                        source
                        for source in sources_by_target.get(join_step_fan_exp_red, ())
                        if source != new_step_fan_exp_red
                    )
                    sources_by_target[join_step_fan_exp_red] = sources
                    return sources_by_target

                return _patched

            def _move_revision_source_after_join(original):
                def _patched(plan):
                    linear_plan, graph_context = original(plan)
                    if not isinstance(linear_plan, Mapping):
                        return linear_plan, graph_context
                    changed_linear_plan = dict(linear_plan)
                    changed_steps = list(changed_linear_plan.get("steps", []))
                    def _item_step_ref(item):
                        if isinstance(item, Mapping):
                            return item.get("step_ref")
                        return item

                    new_index = next(
                        (
                            index
                            for index, item in enumerate(changed_steps)
                            if _item_step_ref(item) == new_step_fan_exp_red
                        ),
                        None,
                    )
                    join_index = next(
                        (
                            index
                            for index, item in enumerate(changed_steps)
                            if _item_step_ref(item) == join_step_fan_exp_red
                        ),
                        None,
                    )
                    if new_index is not None and join_index is not None and new_index < join_index:
                        new_item = changed_steps.pop(new_index)
                        join_index = next(
                            (
                                index
                                for index, item in enumerate(changed_steps)
                                if _item_step_ref(item) == join_step_fan_exp_red
                            ),
                            join_index,
                        )
                        changed_steps.insert(join_index + 1, new_item)
                        changed_linear_plan["steps"] = changed_steps
                    return changed_linear_plan, graph_context

                return _patched

            def _drop_revision_successor(original):
                def _patched(graph_context):
                    successors_by_source = {
                        source: tuple(successors)
                        for source, successors in original(graph_context).items()
                    }
                    root_step_ref = f"{prefix_fan_exp_red}-root"
                    successors_by_source[root_step_ref] = tuple(
                        successor
                        for successor in successors_by_source.get(root_step_ref, ())
                        if successor != new_step_fan_exp_red
                    )
                    successors_by_source.pop(new_step_fan_exp_red, None)
                    return successors_by_source

                return _patched

            walker_kernel_module._graph_fan_in_sources_by_target_step_ref = _drop_revision_source(
                original_kernel_sources
            )
            walker_fan_in_module._graph_fan_in_sources_by_target_step_ref = _drop_revision_source(
                original_fan_in_sources
            )
            walker_kernel_module._linear_plan_from_graph_plan = _move_revision_source_after_join(
                original_kernel_linear_plan
            )
            walker_resume_module._linear_plan_from_graph_plan = _move_revision_source_after_join(
                original_resume_linear_plan
            )
            walker_kernel_module._graph_successor_step_refs_by_source_step_ref = (
                _drop_revision_successor(original_kernel_successors)
            )
            resumed_fan_exp_red = None
            try:
                resumed_fan_exp_red = resume_building_plan(
                    root_fan_exp_red,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _fan_callable(
                            held_brick=f"brick-{prefix_fan_exp_red}-lane-b",
                            reroute_target=f"brick-{prefix_fan_exp_red}-join",
                        )
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                violations.append(f"expansion-fanin-live-red: resume crashed: {exc}")
            finally:
                walker_kernel_module._graph_fan_in_sources_by_target_step_ref = original_kernel_sources
                walker_fan_in_module._graph_fan_in_sources_by_target_step_ref = original_fan_in_sources
                walker_kernel_module._linear_plan_from_graph_plan = original_kernel_linear_plan
                walker_resume_module._linear_plan_from_graph_plan = original_resume_linear_plan
                walker_kernel_module._graph_successor_step_refs_by_source_step_ref = (
                    original_kernel_successors
                )
            if resumed_fan_exp_red is not None:
                live_red_fan_exp = _assert_revision_fan_in_wait_all_observed(
                    label="expansion-fanin-live-red",
                    root=resumed_fan_exp_red.lifecycle_write.root,
                    step_bricks=_step_bricks(resumed_fan_exp_red),
                    prefix=prefix_fan_exp_red,
                    new_step_ref=new_step_fan_exp_red,
                )
                if not any(
                    "revision-added fan-in source did not run live" in item
                    or "resumed step list does not include revision source" in item
                    or "fan-in join ran before revision-added source completed" in item
                    for item in live_red_fan_exp
                ):
                    violations.append(
                        "expansion-fanin-live-red: live source-map mutation did not RED"
                    )

    # Compose-time route-policy field consumers: the checker exercises the REAL
    # support functions that read default budgets, closure target policy, and
    # provenance. These are observation guards only; they author no routes.
    from brick_protocol.support.operator.composition_route_policy import (
        _composition_route_policy_provenance,
        _materializer_closure_policy,
        _materializer_reroute_budget_cascade,
    )

    declared_budgets, budget_provenance, default_budget = _materializer_reroute_budget_cascade(
        {"node_reroute_budgets": {"work": 3}},
        repo=repo,
        override_reroute_budgets={"qa": 2},
    )
    if declared_budgets != {"work": 3, "qa": 2}:
        violations.append(
            "route-policy-fields: preset/per-building budget cascade drifted "
            f"({declared_budgets})"
        )
    if budget_provenance != {"work": "preset-default", "qa": "per-building"}:
        violations.append(
            "route-policy-fields: budget provenance matrix drifted "
            f"({budget_provenance})"
        )
    if default_budget is not None:
        violations.append(
            "route-policy-fields: preset budgets should suppress yaml default load "
            f"(default_budget={default_budget})"
        )
    with checker_temp_path("bp-bapr-route-policy-yaml-absent-") as tmp:
        try:
            _materializer_reroute_budget_cascade(
                {},
                repo=tmp,
                override_reroute_budgets=None,
            )
        except ValueError as exc:
            if "Brick reroute defaults file is missing" not in str(exc):
                violations.append(
                    "route-policy-yaml-absent-red: missing reroute defaults raised "
                    f"the wrong error ({exc})"
                )
        else:
            violations.append(
                "route-policy-yaml-absent-red: absent preset budgets did not "
                "declare missing yaml by failing closed"
            )
    resolved_policy = _materializer_closure_policy(
        {
            "implementation_gap": {
                "action": "reroute",
                "target_step_template_ref": "brick/templates/bricks/work/brick.md",
            }
        },
        building_slug="route-policy-field-real",
    )
    if resolved_policy != {
        "implementation_gap": {
            "action": "reroute",
            "target_ref": "route-policy-field-real-brick-templates-bricks-work-brick-md",
        }
    }:
        violations.append(
            "route-policy-fields: closure target policy did not resolve the "
            f"declared template target ({resolved_policy})"
        )
    provenance = _composition_route_policy_provenance(
        [
            {
                "node_id": "route-policy-field-real-work",
                "node_reroute_budget": 2,
                "node_reroute_budget_provenance": "per-building",
                "closure_transition_target_policy": resolved_policy,
                "closure_transition_target_policy_provenance": "preset-default",
            }
        ]
    )
    by_node = provenance.get("by_node", {}) if isinstance(provenance, Mapping) else {}
    if by_node.get("route-policy-field-real-work") != {
        "node_reroute_budget": "per-building",
        "closure_transition_target_policy": "preset-default",
    }:
        violations.append(
            "route-policy-fields: provenance observation did not record the real "
            f"policy field owners ({provenance})"
        )
    try:
        _composition_route_policy_provenance(
            [{"node_id": "route-policy-field-real-red", "node_reroute_budget": 1}]
        )
    except ValueError as exc:
        if "non-HUMAN provenance" not in str(exc):
            violations.append(
                "route-policy-fields-red: missing budget provenance raised the "
                f"wrong error ({exc})"
            )
    else:
        violations.append(
            "route-policy-fields-red: missing route-policy provenance was not "
            "rejected fail-closed"
        )

    # Invariant E: B3 fan-out / fan-in happy path is a serial adapter:local walk:
    # root fans to both lanes, join runs only after both sources, and link_edge_id
    # values remain unique.
    plan_fan = _fan_plan("bapr-loop0-b3-happy")
    res_fan, fr_fan, _ = _run(plan_fan, _fan_callable(), repo)
    bricks_fan = [r.preparation.brick_instance_ref for r in res_fan.step_results]
    expected_once = [
        "brick-bapr-loop0-b3-happy-root",
        "brick-bapr-loop0-b3-happy-lane-a",
        "brick-bapr-loop0-b3-happy-lane-b",
        "brick-bapr-loop0-b3-happy-join",
        "brick-bapr-loop0-b3-happy-close",
    ]
    if bricks_fan != expected_once:
        violations.append(f"b3-happy: fan walk order/once semantics drifted: {bricks_fan}")
    else:
        join_index = bricks_fan.index("brick-bapr-loop0-b3-happy-join")
        if join_index <= bricks_fan.index("brick-bapr-loop0-b3-happy-lane-a") or join_index <= bricks_fan.index(
            "brick-bapr-loop0-b3-happy-lane-b"
        ):
            violations.append("b3-happy: join ran before all fan-in sources returned")
    link_edge_ids = [
        edge.get("link_edge_id")
        for edge in res_fan.building_map_packet.get("link_edges", [])
        if isinstance(edge, Mapping)
    ]
    if len(link_edge_ids) != len(set(link_edge_ids)):
        violations.append("b3-happy: duplicate link_edge_id emitted")
    if fr_fan["frontier_kind"] != "complete":
        violations.append(f"b3-happy: frontier did not close after join+closure (frontier={fr_fan['frontier_kind']})")

    # P6-C: independent fan-out branches may dispatch concurrently only when the
    # caller opts into pool>N. The drain remains deterministic: pool=1 and pool=4
    # produce byte-equal normalized evidence-manifest/spine/building-map packets,
    # while the timed fixture proves wall-clock completion order was inverted.
    p6c_prefix = "bapr-loop0-p6c-byte-fanout"
    p6c_plan = _fan_plan(p6c_prefix)
    with checker_temp_path("bp-bapr-p6c-byte-fanout-") as tmp_root:
        pool1_callable = _p6c_timed_fan_callable(prefix=p6c_prefix)
        pool4_callable = _p6c_timed_fan_callable(prefix=p6c_prefix)
        res_p6c_1, fr_p6c_1, _ = _run_with_fanout_pool(
            p6c_plan,
            pool1_callable,
            repo,
            tmp_root / "pool1",
            pool_size=1,
        )
        res_p6c_4, fr_p6c_4, _ = _run_with_fanout_pool(
            p6c_plan,
            pool4_callable,
            repo,
            tmp_root / "pool4",
            pool_size=4,
        )
        if fr_p6c_1["frontier_kind"] != "complete" or fr_p6c_4["frontier_kind"] != "complete":
            violations.append(
                "p6c-byte-fanout: pool=1/pool=4 did not both complete "
                f"(pool1={fr_p6c_1['frontier_kind']} pool4={fr_p6c_4['frontier_kind']})"
            )
        normalized_p6c_1 = _p6c_normalized_evidence_files(res_p6c_1.lifecycle_write.root)
        normalized_p6c_4 = _p6c_normalized_evidence_files(res_p6c_4.lifecycle_write.root)
        if normalized_p6c_1 != normalized_p6c_4:
            differing = sorted(
                set(normalized_p6c_1).symmetric_difference(normalized_p6c_4)
                or {
                    key
                    for key in normalized_p6c_1
                    if normalized_p6c_1.get(key) != normalized_p6c_4.get(key)
                }
            )
            violations.append(
                "p6c-byte-fanout: normalized evidence-manifest/spine/building-map "
                f"differs between pool=1 and pool=4 (first={differing[:3]})"
            )
        stats_p6c_1 = pool1_callable.stats()
        stats_p6c_4 = pool4_callable.stats()
        if stats_p6c_1.get("max_active") != 1:
            violations.append(
                "p6c-byte-fanout: pool=1 observed concurrent callable execution "
                f"({stats_p6c_1})"
            )
        if int(stats_p6c_4.get("max_active", 0)) < 2:
            violations.append(
                "p6c-byte-fanout: pool=4 did not overlap independent fan-out branches "
                f"({stats_p6c_4})"
            )
        lane_a_p6c = f"brick-{p6c_prefix}-lane-a"
        lane_b_p6c = f"brick-{p6c_prefix}-lane-b"
        bricks_p6c_4 = _step_bricks(res_p6c_4)
        completion_order_p6c_4 = list(stats_p6c_4.get("completion_order", []))
        if bricks_p6c_4.index(lane_a_p6c) > bricks_p6c_4.index(lane_b_p6c):
            violations.append(
                "p6c-byte-fanout: deterministic drain applied pool=4 outcomes in "
                f"non-frontier order ({bricks_p6c_4})"
            )
        if completion_order_p6c_4.index(lane_b_p6c) > completion_order_p6c_4.index(lane_a_p6c):
            violations.append(
                "p6c-byte-fanout-red: timed fixture failed to invert wall-clock "
                f"arrival order ({completion_order_p6c_4})"
            )
        if not stats_p6c_4.get("handshake_engaged"):
            violations.append(
                "p6c-byte-fanout-red: inversion handshake removed -- arrival-order "
                f"inversion no longer guaranteed ({stats_p6c_4})"
            )
        if (
            completion_order_p6c_4.index(lane_b_p6c)
            < completion_order_p6c_4.index(lane_a_p6c)
            and bricks_p6c_4.index(lane_a_p6c) < bricks_p6c_4.index(lane_b_p6c)
        ):
            pass
        else:
            violations.append(
                "p6c-byte-fanout-red: arrival-order drain would not be detected by "
                "this fixture"
            )

    # P4: resume must replay completed pre-HOLD evidence serially, then recover
    # declared fan-out parallelism for the live continuation. The first run
    # completes the first fan-out/fan-in and pauses at join1's COO gate before
    # the second fan-out is scheduled; after the human/COO forward disposition,
    # lane-c and lane-d are genuinely continued work and should overlap under
    # pool=4.
    p4_prefix = "bapr-loop0-p4-resume-fanout"
    p4_plan = _with_link_edge_gate_sequence_policy(
        _two_stage_fan_plan(p4_prefix),
        f"edge:{p4_prefix}-join1-to-c",
        declared_gate_refs=["link-gate:default-transition", "link-gate:coo"],
        gate_sequence_policy=[
            {
                "gate_ref": "link-gate:default-transition",
                "on_sufficient": {"action": "next", "next_gate_ref": "link-gate:coo"},
                "on_missing_required_facts": {
                    "action": "hold",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [f"observation:{p4_prefix}-default-transition-missing"],
                    "required_disposition_owner": "caller-or-coo",
                },
            },
            {
                "gate_ref": "link-gate:coo",
                "on_missing_required_facts": {
                    "action": "hold",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [f"observation:{p4_prefix}-coo-review-required"],
                    "required_disposition_owner": "caller-or-coo",
                },
                "on_sufficient": {"action": "forward"},
            },
        ],
    )
    with checker_temp_path("bp-bapr-p4-resume-fanout-") as tmp_root:
        setup_callable_p4 = _p4_two_stage_timed_callable(prefix=p4_prefix)
        resume_callable_p4 = _p4_two_stage_timed_callable(prefix=p4_prefix)
        res_p4, fr_p4, _ = _run_with_fanout_pool(
            p4_plan,
            setup_callable_p4,
            repo,
            tmp_root,
            pool_size=4,
        )
        if fr_p4["frontier_kind"] != "link_paused":
            violations.append(
                "p4-resume-fanout: setup did not pause at the mid-fan join1 gate "
                f"(frontier={fr_p4['frontier_kind']})"
            )
        root_p4 = res_p4.lifecycle_write.root
        hold_p4 = (
            res_p4._dynamic_walker_evidence.get("hold", {})
            if isinstance(getattr(res_p4, "_dynamic_walker_evidence", {}), Mapping)
            else {}
        )
        _append_disposition_row(
            root_p4,
            building_id=res_p4.building_id,
            pending_target_ref=hold_p4.get("pending_target_ref") or f"brick-{p4_prefix}-lane-c",
            action="forward",
            author_ref="human:smith",
        )
        try:
            resumed_p4 = _resume_with_fanout_pool(
                root_p4,
                resume_callable_p4,
                repo,
                pool_size=4,
            )
            fr_resumed_p4 = observe_building_frontier(
                resumed_p4.lifecycle_write.root,
                repo_root=repo,
            )
        except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
            violations.append(f"p4-resume-fanout: resume crashed: {exc}")
        else:
            if fr_resumed_p4["frontier_kind"] != "complete":
                violations.append(
                    "p4-resume-fanout: resumed continuation did not complete "
                    f"(frontier={fr_resumed_p4['frontier_kind']})"
                )
            stats_p4 = resume_callable_p4.stats()
            if int(stats_p4.get("max_active", 0)) < 2:
                violations.append(
                    "p4-resume-fanout: resumed live fan-out continuation did not "
                    f"overlap under pool=4 ({stats_p4})"
                )
            lane_c_p4 = f"brick-{p4_prefix}-lane-c"
            lane_d_p4 = f"brick-{p4_prefix}-lane-d"
            bricks_p4 = _step_bricks(resumed_p4)
            completion_order_p4 = list(stats_p4.get("completion_order", []))
            if lane_c_p4 in bricks_p4 and lane_d_p4 in bricks_p4:
                if bricks_p4.index(lane_c_p4) > bricks_p4.index(lane_d_p4):
                    violations.append(
                        "p4-resume-fanout: deterministic drain applied resumed "
                        f"fan-out in non-frontier order ({bricks_p4})"
                    )
            else:
                violations.append(
                    "p4-resume-fanout: resumed step list did not include both fan "
                    f"lanes ({bricks_p4})"
                )
            if lane_c_p4 in completion_order_p4 and lane_d_p4 in completion_order_p4:
                if completion_order_p4.index(lane_d_p4) > completion_order_p4.index(lane_c_p4):
                    violations.append(
                        "p4-resume-fanout-red: timed fixture failed to invert "
                        f"resume arrival order ({completion_order_p4})"
                    )
                if not stats_p4.get("handshake_engaged"):
                    violations.append(
                        "p4-resume-fanout-red: inversion handshake removed -- resume "
                        f"arrival-order inversion no longer guaranteed ({stats_p4})"
                    )
            else:
                violations.append(
                    "p4-resume-fanout: resume callable did not observe both fan "
                    f"lanes ({completion_order_p4})"
                )

    # P6-C shared fan-in reroute fixture: pool>N must not reorder the
    # multi-attempt reroute into a fan-in source or stale the shared join evidence.
    shared_prefix = "bapr-loop0-p6c-shared-fanin-reroute"
    shared_plan = _cohort_fan_plan(shared_prefix)
    shared_lane_a = f"brick-{shared_prefix}-lane-a"
    shared_join = f"brick-{shared_prefix}-join"
    with checker_temp_path("bp-bapr-p6c-shared-fanin-") as tmp_root:
        shared_pool1_callable = _fan_callable(
            held_brick=shared_join,
            reroute_target=shared_lane_a,
        )
        shared_pool4_callable = _fan_callable(
            held_brick=shared_join,
            reroute_target=shared_lane_a,
        )
        res_shared_1, fr_shared_1, _ = _run_with_fanout_pool(
            shared_plan,
            shared_pool1_callable,
            repo,
            tmp_root / "pool1",
            pool_size=1,
        )
        res_shared_4, fr_shared_4, _ = _run_with_fanout_pool(
            shared_plan,
            shared_pool4_callable,
            repo,
            tmp_root / "pool4",
            pool_size=4,
        )
        if fr_shared_1["frontier_kind"] != "link_paused" or fr_shared_4["frontier_kind"] != "link_paused":
            violations.append(
                "p6c-shared-fanin-reroute: pool=1/pool=4 did not both reach the "
                "same bounded reroute HOLD "
                f"(pool1={fr_shared_1['frontier_kind']} pool4={fr_shared_4['frontier_kind']})"
            )
        normalized_shared_1 = _p6c_normalized_evidence_files(
            res_shared_1.lifecycle_write.root
        )
        normalized_shared_4 = _p6c_normalized_evidence_files(
            res_shared_4.lifecycle_write.root
        )
        if normalized_shared_1 != normalized_shared_4:
            differing = sorted(
                set(normalized_shared_1).symmetric_difference(normalized_shared_4)
                or {
                    key
                    for key in normalized_shared_1
                    if normalized_shared_1.get(key) != normalized_shared_4.get(key)
                }
            )
            violations.append(
                "p6c-shared-fanin-reroute: normalized evidence-manifest/spine/"
                "building-map differs between pool=1 and pool=4 "
                f"(first={differing[:3]})"
            )

    # F1: if one concurrently dispatched fan-out sibling errors, parks, or HOLDs,
    # the completed sibling branches must survive in written evidence before the
    # frontier is observed. The failing/held/parked lane is ordered after lane-a
    # and lane-c, so pool=1 is the deterministic survivor baseline.
    f1_cases = [
        (
            "error",
            "bapr-loop0-f1-error-survivors",
            _fan3_plan("bapr-loop0-f1-error-survivors"),
            _adapter_error_callable("brick-bapr-loop0-f1-error-survivors-lane-b"),
        ),
        (
            "hold",
            "bapr-loop0-f1-hold-survivors",
            _fan3_plan("bapr-loop0-f1-hold-survivors", held_source=True),
            _fan_callable(
                held_brick="brick-bapr-loop0-f1-hold-survivors-lane-b",
                reroute_target="brick-bapr-loop0-f1-hold-survivors-join",
            ),
        ),
        (
            "park",
            "bapr-loop0-f1-park-survivors",
            _fan3_plan("bapr-loop0-f1-park-survivors", parked_source=True),
            _fan_callable(),
        ),
    ]
    for mode, prefix, plan_f1, callable_f1 in f1_cases:
        with tempfile.TemporaryDirectory(prefix=f"bp-bapr-f1-{mode}-") as tmp_f1:
            tmp_root = Path(tmp_f1)
            root_pool1, frontier_pool1 = _run_frontier_root_with_fanout_pool(
                plan_f1,
                callable_f1,
                repo,
                tmp_root / "pool1",
                pool_size=1,
            )
            root_pool4, frontier_pool4 = _run_frontier_root_with_fanout_pool(
                plan_f1,
                callable_f1,
                repo,
                tmp_root / "pool4",
                pool_size=4,
            )
            violations.extend(
                _f1_assert_surviving_sibling_outputs(
                    mode=f"{mode}-pool1",
                    root=root_pool1,
                    prefix=prefix,
                )
            )
            violations.extend(
                _f1_assert_surviving_sibling_outputs(
                    mode=f"{mode}-pool4",
                    root=root_pool4,
                    prefix=prefix,
                )
            )
            violations.extend(
                _f1_assert_frontier_stopped_before_closure(
                    mode=f"{mode}-pool1",
                    frontier=frontier_pool1,
                )
            )
            violations.extend(
                _f1_assert_frontier_stopped_before_closure(
                    mode=f"{mode}-pool4",
                    frontier=frontier_pool4,
                )
            )
            normalized_pool1 = _p6c_normalized_evidence_files(root_pool1)
            normalized_pool4 = _p6c_normalized_evidence_files(root_pool4)
            if normalized_pool1 != normalized_pool4:
                differing = sorted(
                    set(normalized_pool1).symmetric_difference(normalized_pool4)
                    or {
                        key
                        for key in normalized_pool1
                        if normalized_pool1.get(key) != normalized_pool4.get(key)
                    }
                )
                violations.append(
                    f"f1-{mode}: normalized pool=1/pool=4 evidence differs "
                    f"after sibling interruption (first={differing[:3]})"
                )

    # Invariant F: a held fan-in source never lets the join/closure make the
    # Building look complete. It must surface through an existing frontier kind.
    plan_held = _fan_plan("bapr-loop0-b3-held", held_source=True)
    res_held, fr_held, _ = _run(
        plan_held,
        _fan_callable(
            held_brick="brick-bapr-loop0-b3-held-lane-b",
            reroute_target="brick-bapr-loop0-b3-held-join",
        ),
        repo,
    )
    held_bricks = [r.preparation.brick_instance_ref for r in res_held.step_results]
    if "brick-bapr-loop0-b3-held-join" in held_bricks:
        violations.append("b3-held: fan-in join executed even though one source was held")
    if fr_held["frontier_kind"] not in {"link_paused", "evidence_incomplete"}:
        violations.append(
            f"b3-held: held fan-in source surfaced as forbidden frontier={fr_held['frontier_kind']}"
        )
    if fr_held["frontier_kind"] in {"complete", "closure_pending"}:
        violations.append("b3-held: held fan-in source allowed a complete/closure_pending frontier")
    held_evidence = getattr(res_held, "_dynamic_walker_evidence", {})
    wait_observations = []
    if isinstance(held_evidence, Mapping):
        raw_wait = held_evidence.get("fan_in_wait_all_observations", [])
        if isinstance(raw_wait, list):
            wait_observations = [item for item in raw_wait if isinstance(item, Mapping)]
    if not any("bapr-loop0-b3-held-lane-b" in item.get("missing_source_step_refs", []) for item in wait_observations):
        violations.append("b3-held: missing held source was not recorded in fan_in wait_all evidence")

    # Invariant G: malformed fan graph topology rejects at plan_graph admission.
    from brick_protocol.support.operator.plan_graph import _linear_plan_from_graph_plan

    cycle_plan = copy.deepcopy(plan_fan)
    cycle_plan["link_edges"].append(
        _fwd_edge(
            "edge:bapr-loop0-b3-happy-join-to-a-cycle",
            "bapr-loop0-b3-happy-join",
            "bapr-loop0-b3-happy-lane-a",
            "brick-bapr-loop0-b3-happy-lane-a",
        )
    )
    try:
        _linear_plan_from_graph_plan(cycle_plan)
    except ValueError as exc:
        if "cycle" not in str(exc):
            violations.append(f"b3-cycle: rejected with unclear error: {exc}")
    else:
        violations.append("b3-cycle: cycle graph was not rejected at admission")

    no_root_plan = copy.deepcopy(plan_fan)
    no_root_plan["link_edges"].append(
        _fwd_edge(
            "edge:bapr-loop0-b3-happy-close-to-root",
            "bapr-loop0-b3-happy-close",
            "bapr-loop0-b3-happy-root",
            "brick-bapr-loop0-b3-happy-root",
        )
    )
    try:
        _linear_plan_from_graph_plan(no_root_plan)
    except ValueError as exc:
        if "root" not in str(exc):
            violations.append(f"b3-no-root: rejected with unclear error: {exc}")
    else:
        violations.append("b3-no-root: no-root graph was not rejected at admission")

    # Invariant H: no-fan graph seed remains the full execution_order control path.
    plan_serial, _ = _checker_plan("bapr-loop0-b3-serial-control", budget=1)
    res_serial, _, _ = _run(plan_serial, _reroute_callable("brick-unused", set()), repo)
    serial_step_refs = [r.preparation.step_rows.step_ref for r in res_serial.step_results]
    if serial_step_refs != list(plan_serial["execution_order"]):
        violations.append(f"b3-serial-control: no-fan execution_order drifted: {serial_step_refs}")

    # B5 Invariant C3: FULL-CHAIN REPLAY. The source completion edge declares
    # route_replay_plan.replay_segment_refs over downstream nodes. The target
    # reroute landing consumes only the target budget; replay-scope executions
    # do not consume their own node budgets.
    plan_c3, c3_refs = _full_chain_replay_plan()
    res_c3, fr_c3, rec_c3 = _run_with_retained_root(
        plan_c3,
        _reroute_callable(c3_refs["target"], {c3_refs["source"]}),
        repo,
    )
    adopted_c3 = _adopted_records(rec_c3)
    bricks_c3 = _step_bricks(res_c3)
    evidence_c3 = getattr(res_c3, "_dynamic_walker_evidence", {})
    landings_c3 = (
        evidence_c3.get("node_reroute_landings", {})
        if isinstance(evidence_c3, Mapping)
        else {}
    )
    if len(adopted_c3) != 1:
        violations.append(f"b5-c3-full-chain-replay: expected 1 adopted reroute, got {len(adopted_c3)}")
    else:
        replay_refs = adopted_c3[0].get("replay_segment_refs")
        expected_replay_refs = [c3_refs["replay_1_step"], c3_refs["replay_2_step"]]
        if replay_refs != expected_replay_refs:
            violations.append(
                "b5-c3-full-chain-replay: adopted record replay_segment_refs drifted "
                f"(got={replay_refs}, expected={expected_replay_refs})"
            )
    try:
        source_index_c3 = bricks_c3.index(c3_refs["source"])
        replay_window_c3 = bricks_c3[source_index_c3 + 1 : source_index_c3 + 4]
    except ValueError:
        replay_window_c3 = []
    expected_window_c3 = [c3_refs["target"], c3_refs["replay_1"], c3_refs["replay_2"]]
    if replay_window_c3 != expected_window_c3:
        violations.append(
            "b5-c3-full-chain-replay: target + replay scope did not execute in declared order "
            f"(got={replay_window_c3}, expected={expected_window_c3})"
        )
    for brick in expected_window_c3:
        if bricks_c3.count(brick) != 2:
            violations.append(
                f"b5-c3-full-chain-replay: {brick} did not re-execute exactly once "
                f"(count={bricks_c3.count(brick)})"
            )
    step_refs_c3 = [r.preparation.step_rows.step_ref for r in res_c3.step_results]
    expected_reentry_steps_c3 = [
        c3_refs["target_step"],
        c3_refs["replay_1_step"],
        c3_refs["replay_2_step"],
    ]
    try:
        source_step_index_c3 = step_refs_c3.index("bapr-loop0-b5-c3-c1")
        reentry_step_window_c3 = step_refs_c3[source_step_index_c3 + 1 : source_step_index_c3 + 4]
    except ValueError:
        reentry_step_window_c3 = []
    if reentry_step_window_c3 != expected_reentry_steps_c3:
        violations.append(
            "b5-c3-reentry-step-evidence: re-entry steps did not execute in the "
            "declared target+replay order "
            f"(got={reentry_step_window_c3}, expected={expected_reentry_steps_c3})"
        )
    root_c3 = res_c3.lifecycle_write.root
    manifest_path_c3 = root_c3 / "evidence" / "evidence-manifest.json"
    manifest_c3 = (
        json.loads(manifest_path_c3.read_text(encoding="utf-8"))
        if manifest_path_c3.is_file()
        else {}
    )
    manifest_step_outputs_c3 = set(manifest_c3.get("step_output_refs", []))
    for step_ref in expected_reentry_steps_c3:
        redo_path = _step_output_path(root_c3, step_ref, 2)
        redo_ref = redo_path.relative_to(root_c3).as_posix()
        if not redo_path.is_file():
            violations.append(
                "b5-c3-reentry-step-evidence: missing redo step-output "
                f"for {step_ref} at {redo_ref}"
            )
            continue
        if redo_ref not in manifest_step_outputs_c3:
            violations.append(
                "b5-c3-reentry-step-evidence: evidence manifest missing redo "
                f"step-output ref {redo_ref}"
            )
        if _step_output_path(root_c3, step_ref, 3).exists():
            violations.append(
                "b5-c3-reentry-step-evidence-red: replay step executed more "
                f"than once after re-entry ({step_ref})"
            )
    if landings_c3.get(c3_refs["target"]) != 1:
        violations.append(
            "b5-c3-full-chain-replay: target node reroute landing budget was not consumed once "
            f"(node_landings={landings_c3})"
        )
    for replay_node in (c3_refs["replay_1"], c3_refs["replay_2"]):
        if landings_c3.get(replay_node) != 0:
            violations.append(
                "b5-c3-full-chain-replay: replay-segment node consumed reroute budget during "
                f"forward replay ({replay_node}={landings_c3.get(replay_node)})"
            )
    if fr_c3["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(f"b5-c3-full-chain-replay: replay walk did not complete (frontier={fr_c3['frontier_kind']})")
    carry_c3 = _carry_budget_fact_bodies(res_c3)
    if not any(
        body.get("budget_kind") == "route_replay_max_attempts"
        and body.get("route_replay_ref") == c3_refs["route_replay_ref"]
        and body.get("declared_budget") == 1
        and body.get("observed_total_execution_count_by_boundary", {}).get(c3_refs["target"]) == 2
        and body.get("observed_replay_execution_count_by_boundary", {}).get(c3_refs["target"]) == 1
        for body in carry_c3
    ):
        violations.append("b5-c3-full-chain-replay: route_replay_plan.max_attempts was not recorded as Carry budget evidence")
    if any("observed_attempt_count_by_boundary" in body for body in carry_c3):
        violations.append("b5-c3-full-chain-replay: ambiguous observed_attempt_count_by_boundary is still emitted")

    # BUG3 / Lane3 regression: a per-lane reroute from closure back to a work
    # node must re-supply that work node's declared step-output source_fact even
    # when the source fact was written at the original cascade depth. The RED
    # failure was a crash before the reroute Movement and redo completion refs
    # were recorded.
    prefix_bug3 = "bapr-loop0-bug3-cascade-carry"
    plan_bug3, build_bug3 = _checker_plan(prefix_bug3, budget=1)
    design_step_bug3 = f"{prefix_bug3}-design"
    build_step_bug3 = f"{prefix_bug3}-build"
    close_bug3 = f"brick-{prefix_bug3}-close"
    source_ref_bug3 = (
        f"work/step-outputs/{design_step_bug3}-attempt-1/step-output.json"
    )
    redo_ref_bug3 = (
        f"work/step-outputs/{build_step_bug3}-attempt-2/step-output.json"
    )
    plan_bug3 = _plan_with_build_source_fact(
        plan_bug3,
        build_step_ref=build_step_bug3,
        source_fact_ref=source_ref_bug3,
    )
    with checker_temp_path("bp-bapr-bug3-") as tmp:
        res_bug3, fr_bug3, rec_bug3 = _run_to_output_root(
            plan_bug3,
            _reroute_callable(build_bug3, {close_bug3}),
            repo,
            tmp,
        )
        root_bug3 = res_bug3.lifecycle_write.root
        if fr_bug3["frontier_kind"] not in {"complete", "closure_pending"}:
            violations.append(
                "bug3-cascade-carry: reroute redo did not cleanly complete "
                f"(frontier={fr_bug3['frontier_kind']})"
            )
        adopted_bug3 = _adopted_records(rec_bug3)
        if len(adopted_bug3) != 1:
            violations.append(
                "bug3-cascade-carry: expected exactly one adopted reroute "
                f"(got={len(adopted_bug3)})"
            )
        if not any(row.get("movement") == "reroute" for row in _raw_link_rows(root_bug3)):
            violations.append(
                "bug3-cascade-carry: raw/link.jsonl did not record a reroute Movement"
            )
        manifest_bug3 = json.loads(
            (root_bug3 / "evidence" / "evidence-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        if redo_ref_bug3 not in manifest_bug3.get("step_output_refs", []):
            violations.append(
                "bug3-cascade-carry: evidence manifest is missing the work redo "
                f"step-output ref {redo_ref_bug3}"
            )
        evidence_bug3 = getattr(res_bug3, "_dynamic_walker_evidence", {})
        observations_bug3 = (
            evidence_bug3.get("source_fact_body_carry_observations", [])
            if isinstance(evidence_bug3, Mapping)
            else []
        )
        if not any(
            obs.get("target_step_ref") == build_step_bug3
            and obs.get("cascade_depth") == 1
            and source_ref_bug3 in obs.get("carried_step_output_refs", [])
            and not obs.get("body_absent")
            for obs in observations_bug3
            if isinstance(obs, Mapping)
        ):
            violations.append(
                "bug3-cascade-carry: redo work node did not record cross-cascade "
                "source_fact carry observation"
            )

    # B5 Invariant C5: HUMAN-GATE-ON-REROUTE PAUSE. Same serial shape as the
    # default-gate adoption probe, but the source completion edge declares a
    # human gate. Budget is available, so HOLD must be gate placement, not
    # budget exhaustion.
    plan_c5, b2_c5 = _checker_plan("bapr-loop0-b5-c5-human-gate", budget=1)
    plan_c5 = _with_link_edge_gate(
        plan_c5,
        "edge:bapr-loop0-b5-c5-human-gate-review-to-close",
        ["link-gate:default-transition", "link-gate:human"],
    )
    res_c5, fr_c5, rec_c5 = _run(
        plan_c5,
        _reroute_callable(b2_c5, {"brick-bapr-loop0-b5-c5-human-gate-review"}),
        repo,
    )
    adopted_c5 = _adopted_records(rec_c5)
    held_c5 = _held_records(rec_c5)
    evidence_c5 = getattr(res_c5, "_dynamic_walker_evidence", {})
    landings_c5 = (
        evidence_c5.get("node_reroute_landings", {})
        if isinstance(evidence_c5, Mapping)
        else {}
    )
    if adopted_c5:
        violations.append("b5-c5-human-gate-pause: human-gated reroute adopted a landing")
    if len(held_c5) != 1:
        violations.append(f"b5-c5-human-gate-pause: expected 1 HOLD record, got {len(held_c5)}")
    else:
        hold_c5 = held_c5[0]
        if hold_c5.get("hold_reason") != "human_or_coo_gate_pause":
            violations.append(f"b5-c5-human-gate-pause: wrong hold_reason={hold_c5.get('hold_reason')}")
        if hold_c5.get("budget_exhausted") is not False:
            violations.append("b5-c5-human-gate-pause: HOLD incorrectly marked budget_exhausted")
        if hold_c5.get("pending_target_ref") != b2_c5:
            violations.append("b5-c5-human-gate-pause: HOLD pending target was not the proposed node")
    if fr_c5["frontier_kind"] != "link_paused":
        violations.append(f"b5-c5-human-gate-pause: frontier was not link_paused (frontier={fr_c5['frontier_kind']})")
    if landings_c5.get(b2_c5) != 0:
        violations.append(f"b5-c5-human-gate-pause: adopted landing counter moved under human gate ({landings_c5})")

    # ONBOARD APPROVE FIRE (C-2): the CLI support wrapper writes the canonical
    # coo:/human: forward disposition for a link_paused Building, forwards
    # adapter_cwd/adapter_timeout_seconds into the existing resume verb, then the
    # resumed local walk advances beyond the held frontier. Providers are not called.
    from brick_protocol.support.operator import onboard as onboard_module
    from brick_protocol.support.operator import run as run_module
    from brick_protocol.support.operator.onboard import run_approve_entry

    def _smoke_required_return(request):
        return {
            "observed_evidence": [f"observed {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness", "real provider behavior"],
        }

    with checker_temp_path("bp-onboard-approve-fire-") as tmp:
        sandbox = tmp.resolve()
        pfx = "onboard-approve-fire"
        plan_oa, pending_oa = _onboard_approve_fire_plan(pfx)
        res_oa = run_building_plan(
            plan_oa,
            output_root=sandbox,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _smoke_required_return},
            adapter_cwd=sandbox,
            adapter_timeout_seconds=30,
        )
        root_oa = res_oa.lifecycle_write.root
        before_oa = observe_building_frontier(root_oa, repo_root=repo)
        lifecycle_oa = before_oa.get("latest_transition_lifecycle")
        if not isinstance(lifecycle_oa, Mapping):
            lifecycle_oa = {}
        paused_at_oa = str(
            lifecycle_oa.get("transition_lifecycle_paused_at_ref")
            or lifecycle_oa.get("paused_at_ref")
            or ""
        )
        if before_oa["frontier_kind"] != "link_paused":
            violations.append(
                "onboard-approve-fire: setup did not produce link_paused "
                f"(frontier={before_oa['frontier_kind']})"
            )
        if str(
            lifecycle_oa.get("transition_lifecycle_pending_target_ref")
            or lifecycle_oa.get("pending_target_ref")
            or ""
        ) != pending_oa:
            violations.append("onboard-approve-fire: setup HOLD pending target drifted")
        reason_refs_oa = lifecycle_oa.get("transition_lifecycle_reason_refs") or lifecycle_oa.get("reason_refs") or []
        if not any("link-gate:coo" in str(reason_ref) for reason_ref in reason_refs_oa):
            violations.append("onboard-approve-fire: setup HOLD did not record link-gate:coo")
        resume_calls_oa: list[Mapping[str, Any]] = []
        original_resume_oa = run_module.resume_building_plan

        def _spy_resume(building_root, **kwargs):
            root = Path(building_root)
            pre_resume_rows = _raw_link_rows(root)
            resume_calls_oa.append(
                {
                    "building_root": root,
                    "kwargs": dict(kwargs),
                    "pre_resume_last_row": pre_resume_rows[-1] if pre_resume_rows else {},
                }
            )
            return original_resume_oa(building_root, **kwargs)

        run_module.resume_building_plan = _spy_resume
        try:
            approve_oa = run_approve_entry(
                root_oa,
                action="forward",
                author_ref="coo:smith",
                adapter_cwd=sandbox,
                adapter_timeout_seconds=17,
                repo_root=repo,
            )
        finally:
            run_module.resume_building_plan = original_resume_oa
        if approve_oa.get("ok") is not True:
            violations.append(
                "onboard-approve-fire: run_approve_entry did not return ok "
                f"({approve_oa.get('error_kind')}: {approve_oa.get('error_message')})"
            )
        if not resume_calls_oa:
            violations.append("onboard-approve-fire: resume_building_plan was not called")
        else:
            resume_call_oa = resume_calls_oa[-1]
            kwargs_oa = dict(resume_call_oa.get("kwargs", {}))
            if Path(kwargs_oa.get("adapter_cwd")).resolve() != sandbox:
                violations.append("onboard-approve-fire: adapter_cwd was not forwarded to resume_building_plan")
            if kwargs_oa.get("adapter_timeout_seconds") != 17:
                violations.append("onboard-approve-fire: adapter_timeout_seconds was not forwarded")
            pre_resume_last_oa = resume_call_oa.get("pre_resume_last_row")
            if not isinstance(pre_resume_last_oa, Mapping):
                pre_resume_last_oa = {}
            if _link_row_lifecycle_value(
                pre_resume_last_oa,
                "transition_lifecycle_disposition_action",
                "disposition_action",
            ) != "forward":
                violations.append("onboard-approve-fire: pre-resume raw/link last row was not a forward disposition")
            if str(
                pre_resume_last_oa.get("transition_author_ref")
                or pre_resume_last_oa.get("author_ref")
                or ""
            ) != "coo:smith":
                violations.append("onboard-approve-fire: pre-resume raw/link last row author was not coo:smith")
            if _link_row_lifecycle_value(
                pre_resume_last_oa,
                "transition_lifecycle_resumed_from_ref",
                "resumed_from_ref",
            ) != paused_at_oa:
                violations.append("onboard-approve-fire: pre-resume disposition row did not address the held paused_at_ref")
        after_oa = observe_building_frontier(root_oa, repo_root=repo)
        if after_oa["frontier_kind"] == "link_paused":
            after_lifecycle_oa = after_oa.get("latest_transition_lifecycle")
            if not isinstance(after_lifecycle_oa, Mapping):
                after_lifecycle_oa = {}
            after_paused_at_oa = str(
                after_lifecycle_oa.get("transition_lifecycle_paused_at_ref")
                or after_lifecycle_oa.get("paused_at_ref")
                or ""
            )
            if after_paused_at_oa == paused_at_oa:
                violations.append("onboard-approve-fire: approve did not advance beyond the original HOLD")
        elif after_oa["frontier_kind"] not in {"complete", "closure_pending", "agent_incomplete"}:
            violations.append(
                "onboard-approve-fire: unexpected post-approve frontier "
                f"({after_oa['frontier_kind']})"
            )

    def _approve_with_frontier(frontier: Mapping[str, Any]) -> Mapping[str, Any]:
        original_observe = onboard_module.observe_building_frontier
        onboard_module.observe_building_frontier = lambda *_args, **_kwargs: dict(frontier)
        try:
            with checker_temp_path("bp-onboard-approve-red-") as tmp_red:
                building_root_red = tmp_red / "building"
                (building_root_red / "raw").mkdir(parents=True)
                (building_root_red / "work").mkdir()
                adapter_cwd_red = tmp_red / "adapter-cwd"
                adapter_cwd_red.mkdir()
                return run_approve_entry(
                    building_root_red,
                    action="forward",
                    author_ref="coo:smith",
                    adapter_cwd=adapter_cwd_red,
                    repo_root=repo,
                )
        finally:
            onboard_module.observe_building_frontier = original_observe

    parked_oa = _approve_with_frontier({"frontier_kind": "chat_session_parked"})
    if parked_oa.get("error_kind") != "chat_session_parked_not_resumable":
        violations.append("onboard-approve-fire: chat_session_parked was not rejected")
    missing_pending_oa = _approve_with_frontier(
        {
            "frontier_kind": "link_paused",
            "latest_transition_lifecycle": {
                "transition_lifecycle_paused_at_ref": "link-transition:onboard-approve-red"
            },
        }
    )
    if missing_pending_oa.get("error_kind") != "missing_pending_target_ref":
        violations.append("onboard-approve-fire: empty pending_target_ref did not fail closed")
    with checker_temp_path("bp-onboard-approve-budget-red-") as tmp_budget_red:
        budget_red_oa = run_approve_entry(
            tmp_budget_red / "building",
            action="forward",
            author_ref="coo:smith",
            adapter_cwd=tmp_budget_red / "adapter-cwd",
            budget_increment=1,
            repo_root=repo,
        )
    if budget_red_oa.get("error_kind") != "invalid_budget_increment":
        violations.append("onboard-approve-fire: forward + budget_increment was not rejected")
    complete_oa = _approve_with_frontier({"frontier_kind": "complete"})
    if complete_oa.get("ok") is not True or complete_oa.get("disposition_written") is not False:
        violations.append("onboard-approve-fire: complete frontier was not treated as no-op")

    # HUMAN REROUTE DISPOSITION FIRE (FIX-B-HUMAN-REROUTE-TARGET-0616):
    # an ambiguous HOLD names 2+ declared Brick nodes, so support must not pick one.
    # A later human/COO-authored disposition_action="reroute" may name exactly one
    # declared, non-source Brick node; resume then reuses the existing reroute
    # adoption/replay machinery to land there. Bad human targets fail closed.
    from brick_protocol.support.operator.run import resume_building_plan

    human_prefix = "bapr-loop0-human-reroute"
    plan_hr, build_hr = _checker_plan(human_prefix, budget=1)
    design_hr = f"brick-{human_prefix}-design"
    review_hr = f"brick-{human_prefix}-review"
    plan_hr = copy.deepcopy(plan_hr)
    plan_hr["node_reroute_budgets"] = {build_hr: 1, design_hr: 1}
    callable_hr = _multi_ref_concern_callable(review_hr, [build_hr, design_hr])
    with checker_temp_path("bp-human-reroute-fire-") as tmp_hr:
        sandbox_hr = tmp_hr.resolve()
        res_hr = run_building_plan(
            plan_hr,
            output_root=sandbox_hr,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_hr},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_hr = res_hr.lifecycle_write.root
        before_hr = observe_building_frontier(root_hr, repo_root=repo)
        held_hr = _held_records(list(getattr(res_hr, "_dynamic_walker_reroute_records", ())))
        if before_hr["frontier_kind"] != "link_paused":
            violations.append(
                "human-reroute-disposition: ambiguous setup did not pause "
                f"(frontier={before_hr['frontier_kind']})"
            )
        if not held_hr or held_hr[-1].get("hold_reason") != "multiple_reroute_addresses_no_single_owner":
            violations.append("human-reroute-disposition: setup did not record ambiguous HOLD")
        _append_disposition_row(
            root_hr,
            building_id=res_hr.building_id,
            pending_target_ref=design_hr,
            action="reroute",
            author_ref="coo:smith",
        )
        resumed_hr = resume_building_plan(
            root_hr,
            local_callables={"callable:local:agent-invoke0-smoke": callable_hr},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        records_hr = list(getattr(resumed_hr, "_dynamic_walker_reroute_records", ()))
        adopted_hr = _adopted_records(records_hr)
        if not any(record.get("target_brick") == design_hr for record in adopted_hr):
            violations.append(
                "human-reroute-disposition: human-chosen design target was not "
                "adopted as a reroute landing"
            )
        if _step_bricks(resumed_hr).count(design_hr) < 2:
            violations.append(
                "human-reroute-disposition: chosen design target was not replayed "
                f"(bricks={_step_bricks(resumed_hr)})"
            )
        evidence_hr = getattr(resumed_hr, "_dynamic_walker_evidence", {})
        observations_hr = (
            evidence_hr.get("resume_observations", [])
            if isinstance(evidence_hr, Mapping)
            else []
        )
        if not any(
            isinstance(observation, Mapping)
            and observation.get("disposition_action") == "reroute"
            and observation.get("pending_target_ref") == design_hr
            for observation in observations_hr
        ):
            violations.append(
                "human-reroute-disposition: resume observation did not carry "
                "the human reroute target"
            )

    bad_prefix = "bapr-loop0-human-reroute-red"
    bad_plan, bad_build = _checker_plan(bad_prefix, budget=1)
    bad_review = f"brick-{bad_prefix}-review"
    bad_plan = copy.deepcopy(bad_plan)
    bad_plan["node_reroute_budgets"] = {
        bad_build: 1,
        f"brick-{bad_prefix}-design": 1,
    }
    bad_callable = _multi_ref_concern_callable(
        bad_review,
        [bad_build, f"brick-{bad_prefix}-design"],
    )
    with checker_temp_path("bp-human-reroute-red-") as tmp_bad:
        sandbox_bad = tmp_bad.resolve()
        res_bad = run_building_plan(
            bad_plan,
            output_root=sandbox_bad,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": bad_callable},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_bad = res_bad.lifecycle_write.root
        bad_targets = (
            (bad_review, "self"),
            (f"building-boundary:{bad_prefix}-closed", "boundary"),
            (f"brick-{bad_prefix}-missing", "undeclared"),
        )
        for bad_target, label in bad_targets:
            _append_disposition_row(
                root_bad,
                building_id=res_bad.building_id,
                pending_target_ref=bad_target,
                action="reroute",
                author_ref="coo:smith",
            )
            try:
                resume_building_plan(
                    root_bad,
                    local_callables={"callable:local:agent-invoke0-smoke": bad_callable},
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError:
                pass
            else:
                violations.append(
                    "human-reroute-disposition: bad reroute target did not reject "
                    f"({label}: {bad_target})"
                )
    missing_target_oa = run_approve_entry(
        Path(tempfile.gettempdir()) / "bp-onboard-reroute-missing",
        action="reroute",
        author_ref="coo:smith",
        adapter_cwd=Path(tempfile.gettempdir()) / "bp-onboard-reroute-adapter-cwd",
        repo_root=repo,
    )
    if missing_target_oa.get("error_kind") != "missing_reroute_target_ref":
        violations.append(
            "human-reroute-disposition: onboard approve reroute without target "
            "did not fail closed"
        )

    # Invariant: FORWARD GATE-BLOCK IS BUDGET-FREE (gate-block <-> reroute
    # decoupling). A declared gate_sequence_policy on a FORWARD edge whose gate is
    # missing_required_facts yields gate_sequence_decision.action == "hold" with NO
    # reroute and NO agent-proposed concern. That hold branch may READ the target
    # node's reroute budget / node_landings but MUST NOT increment them: a forward
    # gate-block does not consume a reroute landing. node_landings[target] is
    # incremented ONLY on a reroute LANDING (walker_kernel.py:765 / :968), never on
    # a hold. This case PINS that decoupling so a future change that increments the
    # landing counter on a forward hold goes RED. declared_gate_refs must start with
    # link-gate:default-transition; the trailing link-gate:human has no
    # human_review_refs present, so it is deterministically missing_required_facts
    # and the forward block fires on every run regardless of the agent return shape.
    plan_block, b2_block = _checker_plan("bapr-loop0-forward-gate-block", budget=2)
    block_source_edge = "edge:bapr-loop0-forward-gate-block-design-to-build"
    plan_block = _with_link_edge_gate_sequence_policy(
        plan_block,
        block_source_edge,
        declared_gate_refs=["link-gate:default-transition", "link-gate:human"],
        gate_sequence_policy=[
            {
                "gate_ref": "link-gate:default-transition",
                "on_missing_required_facts": {
                    "action": "HOLD",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [
                        "observation:bapr-loop0-forward-gate-block-default-transition-missing"
                    ],
                    "required_disposition_owner": "caller-or-coo",
                },
                "on_sufficient": {"action": "next", "next_gate_ref": "link-gate:human"},
            },
            {
                "gate_ref": "link-gate:human",
                "on_missing_required_facts": {
                    "action": "HOLD",
                    "pending_target_basis": "target_brick",
                    "reason_refs": [
                        "observation:bapr-loop0-forward-gate-block-human-gate-missing"
                    ],
                    "required_disposition_owner": "caller-or-coo",
                },
                "on_sufficient": {"action": "forward"},
            },
        ],
    )
    # Clean callable: NO transition_concern_evidence is ever proposed, so the only
    # reason this walk can hold is the forward gate-block (not a reroute path).
    res_block, fr_block, rec_block = _run(
        plan_block,
        _reroute_callable("brick-unused", set()),
        repo,
    )
    adopted_block = _adopted_records(rec_block)
    held_block = _held_records(rec_block)
    evidence_block = getattr(res_block, "_dynamic_walker_evidence", {})
    landings_block = (
        evidence_block.get("node_reroute_landings", {})
        if isinstance(evidence_block, Mapping)
        else {}
    )
    if adopted_block:
        violations.append(
            "forward-gate-block-budget-free: a reroute landing was adopted on a pure "
            f"forward gate-block ({len(adopted_block)} adopted)"
        )
    if len(held_block) != 1:
        violations.append(
            f"forward-gate-block-budget-free: expected exactly 1 HOLD record, got {len(held_block)}"
        )
    else:
        hold_block = held_block[0]
        if not str(hold_block.get("hold_reason", "")).startswith(
            "gate_sequence_missing_required_facts:"
        ):
            violations.append(
                "forward-gate-block-budget-free: HOLD was not the declared forward gate-block "
                f"(hold_reason={hold_block.get('hold_reason')})"
            )
        if hold_block.get("budget_exhausted") is not False:
            violations.append(
                "forward-gate-block-budget-free: forward gate-block HOLD was marked budget_exhausted"
            )
        # attempt_number reads node_landings[target] at hold time; a forward block
        # must leave it at 0 (no landing consumed).
        if hold_block.get("attempt_number") != 0:
            violations.append(
                "forward-gate-block-budget-free: forward gate-block HOLD recorded a non-zero "
                f"reroute-landing attempt_number ({hold_block.get('attempt_number')})"
            )
    if fr_block["frontier_kind"] != "link_paused":
        violations.append(
            f"forward-gate-block-budget-free: frontier was not link_paused (frontier={fr_block['frontier_kind']})"
        )
    # THE PIN: the target node's reroute landing counter must be UNCHANGED (no
    # increment) and no reroute budget was consumed by the forward gate-block.
    if landings_block.get(b2_block, 0) != 0:
        violations.append(
            "forward-gate-block-budget-free: forward gate-block consumed/incremented the target "
            f"node reroute budget (node_landings={landings_block})"
        )
    if any(count != 0 for count in landings_block.values()):
        violations.append(
            "forward-gate-block-budget-free: a forward gate-block moved some node's reroute-landing "
            f"counter (node_landings={landings_block})"
        )

    # B5 Invariant C7: NESTED-DIFFERENT-NODE NEW ROOM. Nested routing helps only
    # because each different target node draws from its own Link-assigned budget.
    plan_c7, x_c7 = _checker_plan("bapr-loop0-b5-c7-different-node", budget=1)
    y_c7 = "brick-bapr-loop0-b5-c7-different-node-design"
    plan_c7 = copy.deepcopy(plan_c7)
    plan_c7["node_reroute_budgets"] = {x_c7: 1, y_c7: 1}
    res_c7, fr_c7, rec_c7 = _run(
        plan_c7,
        _reroute_callable_by_source(
            {
                "brick-bapr-loop0-b5-c7-different-node-review": x_c7,
                x_c7: y_c7,
            },
            min_call_count={x_c7: 2},
        ),
        repo,
    )
    adopted_c7 = _adopted_records(rec_c7)
    held_c7 = _held_records(rec_c7)
    evidence_c7 = getattr(res_c7, "_dynamic_walker_evidence", {})
    landings_c7 = (
        evidence_c7.get("node_reroute_landings", {})
        if isinstance(evidence_c7, Mapping)
        else {}
    )
    cascade_depths_c7 = [r.get("cascade_depth") for r in adopted_c7]
    if len(adopted_c7) != 2:
        violations.append(f"b5-c7-nested-different-node: expected 2 adopted landings, got {len(adopted_c7)}")
    if held_c7:
        violations.append("b5-c7-nested-different-node: nested different-node cascade prematurely HELD")
    if landings_c7.get(x_c7) != 1 or landings_c7.get(y_c7) != 1:
        violations.append(
            "b5-c7-nested-different-node: different nodes did not draw their own budgets "
            f"(node_landings={landings_c7})"
        )
    if cascade_depths_c7 != [1, 2]:
        violations.append(f"b5-c7-nested-different-node: cascade depths drifted ({cascade_depths_c7})")
    if fr_c7["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(f"b5-c7-nested-different-node: frontier did not walk on ({fr_c7['frontier_kind']})")

    # KNOT-4 resolver FIRE (b): NO RESOLVING ADDRESS -> HOLD, NOT silent walk-on.
    # A non-binding concern naming only a non-existent Brick node resolves to ZERO
    # existing nodes while a concern IS present. Support must NOT invent a node AND
    # must NOT silently drop the unaddressable concern: it HOLDs
    # (no_resolving_reroute_address, disposition_required, paused frontier). This
    # SUPERSEDES the prior C8 "silent walk-on" assertion, which encoded the
    # knot-4 bug (an unaddressable concern was dropped). Established Phase-3 design:
    # _classify_reroute_target returns kind='none' for a single non-resolving
    # brick-targeting ref -> walker_kernel HOLD (no_resolving_reroute_address).
    plan_c8, _ = _checker_plan("bapr-loop0-b5-c8-no-target", budget=1)
    res_c8, fr_c8, rec_c8 = _run(
        plan_c8,
        _reroute_callable_by_source(
            {"brick-bapr-loop0-b5-c8-no-target-review": "brick-bapr-loop0-b5-c8-not-declared"}
        ),
        repo,
    )
    adopted_c8 = _adopted_records(rec_c8)
    held_c8 = _held_records(rec_c8)
    evidence_c8 = getattr(res_c8, "_dynamic_walker_evidence", {})
    landings_c8 = (
        evidence_c8.get("node_reroute_landings", {})
        if isinstance(evidence_c8, Mapping)
        else {}
    )
    if adopted_c8:
        violations.append("b5-c8-no-resolving-address: an unaddressable concern was adopted")
    if len(held_c8) != 1:
        violations.append(f"b5-c8-no-resolving-address: expected 1 HOLD record, got {len(held_c8)}")
    elif held_c8[0].get("hold_reason") != "no_resolving_reroute_address":
        violations.append(
            "b5-c8-no-resolving-address: wrong hold_reason="
            f"{held_c8[0].get('hold_reason')}"
        )
    elif held_c8[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append("b5-c8-no-resolving-address: HOLD did not require caller-or-coo disposition")
    if fr_c8["frontier_kind"] != "link_paused":
        violations.append(
            "b5-c8-no-resolving-address: unaddressable concern did not pause "
            f"(frontier={fr_c8['frontier_kind']})"
        )
    if any(count != 0 for count in landings_c8.values()):
        violations.append(
            "b5-c8-no-resolving-address: HOLD moved a node reroute-landing counter "
            f"(node_landings={landings_c8})"
        )
    c8_bricks = _step_bricks(res_c8)
    if c8_bricks.count("brick-bapr-loop0-b5-c8-no-target-review") != 1:
        violations.append(
            "b5-c8-no-resolving-address: HOLD re-executed a target instead of pausing "
            f"(count={c8_bricks.count('brick-bapr-loop0-b5-c8-no-target-review')})"
        )

    # KNOT-4 resolver FIRE (a): TWO RESOLVING ADDRESSES -> HOLD, NOT pick-first.
    # An Agent names two refs that BOTH resolve to declared nodes (a seam with no
    # single owner). The machine must NOT adopt the first: it HOLDs
    # (multiple_reroute_addresses_no_single_owner) and leaves both target node
    # reroute-landing counters UNCHANGED.
    plan_amb, _ = _checker_plan("bapr-loop0-knot4-ambiguous", budget=2)
    amb_first = "brick-bapr-loop0-knot4-ambiguous-build"
    amb_second = "brick-bapr-loop0-knot4-ambiguous-design"
    plan_amb = copy.deepcopy(plan_amb)
    plan_amb["node_reroute_budgets"] = {amb_first: 2, amb_second: 2}
    res_amb, fr_amb, rec_amb = _run(
        plan_amb,
        _multi_ref_concern_callable(
            "brick-bapr-loop0-knot4-ambiguous-review",
            [amb_first, amb_second],
        ),
        repo,
    )
    adopted_amb = _adopted_records(rec_amb)
    held_amb = _held_records(rec_amb)
    evidence_amb = getattr(res_amb, "_dynamic_walker_evidence", {})
    landings_amb = (
        evidence_amb.get("node_reroute_landings", {})
        if isinstance(evidence_amb, Mapping)
        else {}
    )
    if adopted_amb:
        violations.append(
            "knot4-ambiguous: the machine adopted a reroute target despite two resolving "
            f"addresses (no single owner) -- {adopted_amb}"
        )
    if len(held_amb) != 1:
        violations.append(f"knot4-ambiguous: expected 1 HOLD record, got {len(held_amb)}")
    elif held_amb[0].get("hold_reason") != "multiple_reroute_addresses_no_single_owner":
        violations.append(
            "knot4-ambiguous: wrong hold_reason="
            f"{held_amb[0].get('hold_reason')}"
        )
    elif held_amb[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append("knot4-ambiguous: HOLD did not require caller-or-coo disposition")
    if fr_amb["frontier_kind"] != "link_paused":
        violations.append(
            f"knot4-ambiguous: ambiguous addresses did not pause (frontier={fr_amb['frontier_kind']})"
        )
    # BUDGET-FREE PIN: neither candidate node's reroute-landing counter moved.
    if landings_amb.get(amb_first, 0) != 0 or landings_amb.get(amb_second, 0) != 0:
        violations.append(
            "knot4-ambiguous: HOLD consumed/incremented a candidate node reroute-landing "
            f"counter (node_landings={landings_amb})"
        )
    if any(count != 0 for count in landings_amb.values()):
        violations.append(
            f"knot4-ambiguous: HOLD moved some node reroute-landing counter ({landings_amb})"
        )
    # The first-named node must NOT have been re-executed (no silent pick-first).
    amb_bricks = _step_bricks(res_amb)
    if amb_bricks.count(amb_first) != 1:
        violations.append(
            "knot4-ambiguous: first-named node was re-executed (silent pick-first) "
            f"(count={amb_bricks.count(amb_first)})"
        )

    # KNOT-4 resolver FIRE (b-empty): EMPTY related_boundary_refs WITH a concern
    # present -> HOLD (no_resolving_reroute_address), NOT silent walk-on. Distinct
    # from C8 (which names a garbage ref): here the list is literally empty.
    plan_empty, _ = _checker_plan("bapr-loop0-knot4-empty", budget=1)
    res_empty, fr_empty, rec_empty = _run(
        plan_empty,
        _multi_ref_concern_callable("brick-bapr-loop0-knot4-empty-review", []),
        repo,
    )
    held_empty = _held_records(rec_empty)
    evidence_empty = getattr(res_empty, "_dynamic_walker_evidence", {})
    landings_empty = (
        evidence_empty.get("node_reroute_landings", {})
        if isinstance(evidence_empty, Mapping)
        else {}
    )
    if _adopted_records(rec_empty):
        violations.append("knot4-empty: a concern with empty related_boundary_refs was adopted")
    if len(held_empty) != 1:
        violations.append(f"knot4-empty: expected 1 HOLD record, got {len(held_empty)}")
    elif held_empty[0].get("hold_reason") != "no_resolving_reroute_address":
        violations.append(f"knot4-empty: wrong hold_reason={held_empty[0].get('hold_reason')}")
    if fr_empty["frontier_kind"] != "link_paused":
        violations.append(
            f"knot4-empty: empty-refs concern did not pause (frontier={fr_empty['frontier_kind']})"
        )
    if any(count != 0 for count in landings_empty.values()):
        violations.append(
            f"knot4-empty: HOLD moved a node reroute-landing counter ({landings_empty})"
        )

    # B1 advisory concern adoption FIRE: a caller/COO-declared graph plan can mark
    # transition concerns as advisory. Under that exact literal, even an otherwise
    # HOLD-worthy non-binding concern with EMPTY related_boundary_refs is recorded
    # in the Agent return and WALKs FORWARD. Removing the field is the paired RED
    # branch: the same concern must still HOLD as knot4-empty does above.
    plan_adv, _ = _checker_plan("bapr-loop0-b1-advisory-empty", budget=1)
    plan_adv = copy.deepcopy(plan_adv)
    plan_adv.pop("node_reroute_budgets", None)
    plan_adv["transition_concern_adoption"] = "advisory"
    res_adv, fr_adv, rec_adv = _run(
        plan_adv,
        _multi_ref_concern_callable("brick-bapr-loop0-b1-advisory-empty-review", []),
        repo,
    )
    if rec_adv:
        violations.append(
            "b1-advisory-empty: advisory empty-ref concern produced reroute/HOLD records "
            f"(must walk on): {rec_adv}"
        )
    if fr_adv["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "b1-advisory-empty: advisory empty-ref concern did not walk on "
            f"(frontier={fr_adv['frontier_kind']}; expected complete/closure_pending)"
        )
    evidence_adv = getattr(res_adv, "_dynamic_walker_evidence", {})
    if isinstance(evidence_adv, Mapping) and evidence_adv.get("held"):
        violations.append("b1-advisory-empty: advisory concern was recorded as held")
    landings_adv = (
        evidence_adv.get("node_reroute_landings", {})
        if isinstance(evidence_adv, Mapping)
        else {}
    )
    if any(count != 0 for count in landings_adv.values()):
        violations.append(
            "b1-advisory-empty: advisory walk-on moved a node reroute-landing counter "
            f"({landings_adv})"
        )
    adv_step_refs = [r.preparation.step_rows.step_ref for r in res_adv.step_results]
    if adv_step_refs != list(plan_adv["execution_order"]):
        violations.append(
            "b1-advisory-empty: advisory walk-on altered the declared execution_order "
            f"({adv_step_refs})"
        )

    plan_adv_red, _ = _checker_plan("bapr-loop0-b1-advisory-red-empty", budget=1)
    plan_adv_red = copy.deepcopy(plan_adv_red)
    plan_adv_red.pop("node_reroute_budgets", None)
    res_adv_red, fr_adv_red, rec_adv_red = _run(
        plan_adv_red,
        _multi_ref_concern_callable("brick-bapr-loop0-b1-advisory-red-empty-review", []),
        repo,
    )
    held_adv_red = _held_records(rec_adv_red)
    if _adopted_records(rec_adv_red):
        violations.append("b1-advisory-red-empty: no-advisory empty-ref concern was adopted")
    if len(held_adv_red) != 1:
        violations.append(
            f"b1-advisory-red-empty: expected 1 HOLD record without advisory, got {len(held_adv_red)}"
        )
    elif held_adv_red[0].get("hold_reason") != "no_resolving_reroute_address":
        violations.append(
            "b1-advisory-red-empty: wrong hold_reason without advisory="
            f"{held_adv_red[0].get('hold_reason')}"
        )
    if fr_adv_red["frontier_kind"] != "link_paused":
        violations.append(
            "b1-advisory-red-empty: removing advisory did not restore HOLD behavior "
            f"(frontier={fr_adv_red['frontier_kind']})"
        )

    # CLOSURE-SELFREROUTE-GUARD-0616 FIRE (a): omitted/null/false/empty-string
    # transition_concern_evidence is not a reroute proposal. Each variant must
    # walk the declared order to closure and produce no reroute/HOLD records.
    empty_concern_variants: list[tuple[str, Any | None]] = [
        ("omitted", None),
        ("null", None),
        ("false", False),
        ("empty-string", ""),
    ]
    for variant_label, concern_value in empty_concern_variants:
        plan_empty_variant, _ = _checker_plan(
            f"bapr-loop0-selfreroute-empty-{variant_label}",
            budget=1,
        )
        source_empty_variant = (
            f"brick-bapr-loop0-selfreroute-empty-{variant_label}-review"
        )
        callable_empty_variant = (
            _reroute_callable("brick-unused", set())
            if variant_label == "omitted"
            else _raw_transition_concern_callable(source_empty_variant, concern_value)
        )
        res_empty_variant, fr_empty_variant, rec_empty_variant = _run(
            plan_empty_variant,
            callable_empty_variant,
            repo,
        )
        if rec_empty_variant:
            violations.append(
                "selfreroute-empty: empty concern variant produced reroute/HOLD "
                f"records ({variant_label}: {rec_empty_variant})"
            )
        if fr_empty_variant["frontier_kind"] not in {"complete", "closure_pending"}:
            violations.append(
                "selfreroute-empty: empty concern variant did not walk on "
                f"({variant_label}: frontier={fr_empty_variant['frontier_kind']})"
            )
        empty_variant_step_refs = [
            r.preparation.step_rows.step_ref for r in res_empty_variant.step_results
        ]
        if empty_variant_step_refs != list(plan_empty_variant["execution_order"]):
            violations.append(
                "selfreroute-empty: empty concern variant altered declared order "
                f"({variant_label}: {empty_variant_step_refs})"
            )

    # CR.P2c: {} is not a no-concern encoding. It is a present but malformed
    # transition_concern_evidence mapping and must fail closed into the existing
    # invalid-concern HOLD path instead of creating a target or silently walking.
    plan_empty_mapping, _ = _checker_plan("bapr-loop0-empty-mapping-concern", budget=1)
    source_empty_mapping = "brick-bapr-loop0-empty-mapping-concern-review"
    res_empty_mapping, fr_empty_mapping, rec_empty_mapping = _run(
        plan_empty_mapping,
        _raw_transition_concern_callable(source_empty_mapping, {}),
        repo,
    )
    held_empty_mapping = _held_records(rec_empty_mapping)
    if fr_empty_mapping["frontier_kind"] != "link_paused":
        violations.append(
            "selfreroute-empty: empty mapping transition_concern_evidence did not pause "
            f"(frontier={fr_empty_mapping['frontier_kind']})"
        )
    if len(held_empty_mapping) != 1:
        violations.append(
            "selfreroute-empty: expected 1 HOLD record for empty mapping concern, "
            f"got {len(held_empty_mapping)}"
        )
    elif held_empty_mapping[0].get("hold_reason") != "invalid_transition_concern_evidence":
        violations.append(
            "selfreroute-empty: empty mapping wrong hold_reason="
            f"{held_empty_mapping[0].get('hold_reason')}"
        )
    empty_mapping_bricks = _step_bricks(res_empty_mapping)
    if empty_mapping_bricks.count("brick-bapr-loop0-empty-mapping-concern-build") != 1:
        violations.append(
            "selfreroute-empty: empty mapping concern caused an adopted target re-execution "
            f"(count={empty_mapping_bricks.count('brick-bapr-loop0-empty-mapping-concern-build')})"
        )

    # CLOSURE-SELFREROUTE-GUARD-0616 FIRE (b/d): if an Agent concern resolves
    # ONLY to the same Brick node that raised it, the walker must treat it as
    # non_reroute and walk on.
    from brick_protocol.support.operator.walker_transition_concern import (
        _classify_reroute_target,
    )

    self_source = "brick-bapr-loop0-knot4-self-reroute-review"
    self_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [self_source],
        },
        declared_bricks={self_source, "brick-bapr-loop0-knot4-self-reroute-build"},
        source_brick_ref=self_source,
    )
    if self_classification.kind != "non_reroute":
        violations.append(
            "knot4-self-reroute: direct classifier did not mark self-target as "
            f"non_reroute ({self_classification})"
        )
    plan_self, _ = _checker_plan("bapr-loop0-knot4-self-reroute", budget=1)
    res_self, fr_self, rec_self = _run(
        plan_self,
        _multi_ref_concern_callable(self_source, [self_source]),
        repo,
    )
    if rec_self:
        violations.append(
            "knot4-self-reroute: self-target concern produced reroute/HOLD records "
            f"(must walk on): {rec_self}"
        )
    if fr_self["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "knot4-self-reroute: self-target concern did not walk on "
            f"(frontier={fr_self['frontier_kind']}; expected complete/closure_pending)"
        )
    evidence_self = getattr(res_self, "_dynamic_walker_evidence", {})
    if isinstance(evidence_self, Mapping) and evidence_self.get("held"):
        violations.append("knot4-self-reroute: self-target concern was recorded as held")
    landings_self = (
        evidence_self.get("node_reroute_landings", {})
        if isinstance(evidence_self, Mapping)
        else {}
    )
    if any(count != 0 for count in landings_self.values()):
        violations.append(
            "knot4-self-reroute: walk-on moved a node reroute-landing counter "
            f"({landings_self})"
        )
    self_bricks = _step_bricks(res_self)
    if self_bricks.count(self_source) != 1:
        violations.append(
            "knot4-self-reroute: source node was re-executed instead of walking on "
            f"(count={self_bricks.count(self_source)})"
        )
    self_step_refs = [r.preparation.step_rows.step_ref for r in res_self.step_results]
    if self_step_refs != list(plan_self["execution_order"]):
        violations.append(
            "knot4-self-reroute: self-reroute walk-on altered the declared "
            f"execution_order ({self_step_refs})"
        )
    self_returned_concern = any(
        isinstance(getattr(step_result.adapter_result, "returned_value", None), Mapping)
        and isinstance(
            getattr(step_result.adapter_result, "returned_value", {}).get(
                "transition_concern_evidence"
            ),
            Mapping,
        )
        for step_result in res_self.step_results
        if step_result.preparation.brick_instance_ref == self_source
    )
    if not self_returned_concern:
        violations.append(
            "knot4-self-reroute: self-target concern was not present in the Agent "
            "returned evidence"
        )

    # FIX-A-STRIP-SELF-THEN-CLASSIFY-0616 FIRE: classification must first remove
    # the source Brick node, then classify the remaining resolving nodes. This is
    # brick-kind agnostic: closure/QA/review source names take the same path.
    strip_source = "brick-bapr-loop0-knot4-strip-self-single-review"
    strip_single_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [
                strip_source,
                "brick-bapr-loop0-knot4-strip-self-single-build",
            ],
        },
        declared_bricks={
            strip_source,
            "brick-bapr-loop0-knot4-strip-self-single-build",
        },
        source_brick_ref=strip_source,
    )
    if (
        strip_single_classification.kind != "single"
        or strip_single_classification.target
        != "brick-bapr-loop0-knot4-strip-self-single-build"
    ):
        violations.append(
            "knot4-strip-self-single: source+sibling did not classify as single "
            f"after stripping self ({strip_single_classification})"
        )
    empty_source_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [
                strip_source,
                "brick-bapr-loop0-knot4-strip-self-single-build",
            ],
        },
        declared_bricks={
            strip_source,
            "brick-bapr-loop0-knot4-strip-self-single-build",
        },
        source_brick_ref="",
    )
    if empty_source_classification.kind != "ambiguous":
        violations.append(
            "knot4-strip-self-empty-source-control: empty source_brick_ref did not "
            f"leave the multi-ref classification ambiguous ({empty_source_classification})"
        )
    for source_kind in ("closure", "qa"):
        kind_source = f"brick-bapr-loop0-knot4-strip-self-{source_kind}"
        kind_sibling = f"{kind_source}-sibling"
        kind_classification = _classify_reroute_target(
            {"related_boundary_refs": [kind_source, kind_sibling]},
            declared_bricks={kind_source, kind_sibling},
            source_brick_ref=kind_source,
        )
        if (
            kind_classification.kind != "single"
            or kind_classification.target != kind_sibling
        ):
            violations.append(
                "knot4-strip-self-kind-agnostic: source kind "
                f"{source_kind} did not use the same strip-self classification "
                f"({kind_classification})"
            )

    from brick_protocol.agent.return_fact import validate_transition_concern_evidence

    prefix_target = "brick-bapr-loop0-knot4-prefixed-target-build"
    prefix_source = "brick-bapr-loop0-knot4-prefixed-target-review"
    prefixed_ref_cases = {
        "brick-colon-full": f"brick:{prefix_target}",
        "brick-colon-short": "brick:bapr-loop0-knot4-prefixed-target-build",
        "brick-instance": f"brick-instance:{prefix_target}",
        "brick-boundary": f"brick-boundary:{prefix_target}",
    }
    for case_label, prefixed_ref in prefixed_ref_cases.items():
        prefix_classification = _classify_reroute_target(
            {"related_boundary_refs": [prefixed_ref]},
            declared_bricks={prefix_source, prefix_target},
            source_brick_ref=prefix_source,
        )
        if (
            prefix_classification.kind != "single"
            or prefix_classification.target != prefix_target
        ):
            violations.append(
                "knot4-prefixed-target: admitted Brick-node prefix "
                f"{case_label} did not resolve to the declared node "
                f"({prefix_classification})"
            )
        try:
            validate_transition_concern_evidence(
                {
                    "concern_ref": f"transition-concern:{prefix_source}-{case_label}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{prefix_source}"],
                    "related_boundary_refs": [prefixed_ref],
                }
            )
        except ValueError as exc:
            message = str(exc)
            if prefixed_ref not in message or "related_boundary_refs" not in message:
                violations.append(
                    "knot4-prefixed-target: new-authoring rejection message for "
                    f"{case_label} omitted the bad ref or rule ({exc})"
                )
        else:
            violations.append(
                "knot4-prefixed-target: new Agent-return intake accepted old "
                f"prefixed related_boundary_refs form {prefixed_ref!r}"
            )
    prefixed_self_classification = _classify_reroute_target(
        {"related_boundary_refs": [f"brick:{prefix_source}"]},
        declared_bricks={prefix_source, prefix_target},
        source_brick_ref=prefix_source,
    )
    if prefixed_self_classification.kind != "non_reroute":
        violations.append(
            "knot4-prefixed-target: prefixed self-ref did not stay non_reroute "
            f"({prefixed_self_classification})"
        )
    prefixed_garbage_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [
                f"brick:{prefix_target}",
                "brick:brick-bapr-loop0-knot4-prefixed-target-garbage",
            ],
        },
        declared_bricks={prefix_source, prefix_target},
        source_brick_ref=prefix_source,
    )
    if (
        prefixed_garbage_classification.kind != "none"
        or prefixed_garbage_classification.hold_reason
        != "unresolvable_reroute_address"
    ):
        violations.append(
            "knot4-prefixed-target: prefixed resolving+garbage refs did not HOLD "
            f"on the unresolved address ({prefixed_garbage_classification})"
        )

    plan_prefixed, b2_prefixed = _checker_plan(
        "bapr-loop0-knot4-prefixed-target",
        budget=1,
    )
    source_prefixed = "brick-bapr-loop0-knot4-prefixed-target-review"
    res_prefixed, fr_prefixed, rec_prefixed = _run(
        plan_prefixed,
        _multi_ref_concern_callable(source_prefixed, [f"brick:{b2_prefixed}"]),
        repo,
    )
    adopted_prefixed = _adopted_records(rec_prefixed)
    held_prefixed = _held_records(rec_prefixed)
    if adopted_prefixed:
        violations.append(
            "knot4-prefixed-target: newly authored brick:<declared-node> was "
            f"adopted instead of rejected at intake ({adopted_prefixed})"
        )
    if len(held_prefixed) != 1:
        violations.append(
            "knot4-prefixed-target: expected one invalid-concern HOLD for newly "
            f"authored brick:<declared-node>, got {len(held_prefixed)} ({rec_prefixed})"
        )
    elif held_prefixed[0].get("hold_reason") != "invalid_transition_concern_evidence":
        violations.append(
            "knot4-prefixed-target: newly authored brick:<declared-node> held "
            f"with wrong reason {held_prefixed[0].get('hold_reason')}"
        )
    if fr_prefixed["frontier_kind"] != "link_paused":
        violations.append(
            "knot4-prefixed-target: invalid newly authored prefixed reroute did not pause "
            f"(frontier={fr_prefixed['frontier_kind']})"
        )
    prefixed_bricks = _step_bricks(res_prefixed)
    if prefixed_bricks.count(b2_prefixed) != 1:
        violations.append(
            "knot4-prefixed-target: target Brick was re-executed after invalid prefixed reroute "
            f"(count={prefixed_bricks.count(b2_prefixed)})"
        )

    plan_strip_single, b2_strip_single = _checker_plan(
        "bapr-loop0-knot4-strip-self-single",
        budget=1,
    )
    res_strip_single, fr_strip_single, rec_strip_single = _run(
        plan_strip_single,
        _multi_ref_concern_callable(strip_source, [strip_source, b2_strip_single]),
        repo,
    )
    adopted_strip_single = _adopted_records(rec_strip_single)
    held_strip_single = _held_records(rec_strip_single)
    if len(adopted_strip_single) != 1:
        violations.append(
            "knot4-strip-self-single: source+sibling did not adopt exactly one "
            f"reroute after stripping self ({rec_strip_single})"
        )
    elif adopted_strip_single[0].get("target_brick") != b2_strip_single:
        violations.append(
            "knot4-strip-self-single: adopted target was not the remaining sibling "
            f"({adopted_strip_single[0].get('target_brick')})"
        )
    if held_strip_single:
        violations.append(
            "knot4-strip-self-single: source+sibling paused instead of rerouting to "
            f"the only remaining sibling ({held_strip_single})"
        )
    if fr_strip_single["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "knot4-strip-self-single: source+sibling reroute did not proceed "
            f"(frontier={fr_strip_single['frontier_kind']})"
        )
    strip_single_bricks = _step_bricks(res_strip_single)
    if strip_single_bricks.count(b2_strip_single) < 2:
        violations.append(
            "knot4-strip-self-single: remaining sibling was not re-executed "
            f"(count={strip_single_bricks.count(b2_strip_single)})"
        )

    strip_amb_source = "brick-bapr-loop0-knot4-strip-self-ambiguous-review"
    strip_amb_first = "brick-bapr-loop0-knot4-strip-self-ambiguous-build"
    strip_amb_second = "brick-bapr-loop0-knot4-strip-self-ambiguous-design"
    strip_amb_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [
                strip_amb_source,
                strip_amb_first,
                strip_amb_second,
            ],
        },
        declared_bricks={strip_amb_source, strip_amb_first, strip_amb_second},
        source_brick_ref=strip_amb_source,
    )
    if strip_amb_classification.kind != "ambiguous":
        violations.append(
            "knot4-strip-self-ambiguous: source+two-siblings did not remain "
            f"ambiguous after stripping self ({strip_amb_classification})"
        )
    no_source_amb_classification = _classify_reroute_target(
        {"related_boundary_refs": [strip_amb_first, strip_amb_second]},
        declared_bricks={strip_amb_source, strip_amb_first, strip_amb_second},
        source_brick_ref=strip_amb_source,
    )
    if no_source_amb_classification.kind != "ambiguous":
        violations.append(
            "knot4-strip-self-no-source-two-siblings: two siblings without self "
            f"did not stay ambiguous ({no_source_amb_classification})"
        )
    plan_strip_amb, _ = _checker_plan(
        "bapr-loop0-knot4-strip-self-ambiguous",
        budget=1,
    )
    plan_strip_amb = copy.deepcopy(plan_strip_amb)
    plan_strip_amb["node_reroute_budgets"] = {
        strip_amb_first: 1,
        strip_amb_second: 1,
    }
    res_strip_amb, fr_strip_amb, rec_strip_amb = _run(
        plan_strip_amb,
        _multi_ref_concern_callable(
            strip_amb_source,
            [strip_amb_source, strip_amb_first, strip_amb_second],
        ),
        repo,
    )
    adopted_strip_amb = _adopted_records(rec_strip_amb)
    held_strip_amb = _held_records(rec_strip_amb)
    evidence_strip_amb = getattr(res_strip_amb, "_dynamic_walker_evidence", {})
    landings_strip_amb = (
        evidence_strip_amb.get("node_reroute_landings", {})
        if isinstance(evidence_strip_amb, Mapping)
        else {}
    )
    if adopted_strip_amb:
        violations.append(
            "knot4-strip-self-ambiguous: source+two-siblings adopted a target "
            f"instead of HOLDing ({adopted_strip_amb})"
        )
    if len(held_strip_amb) != 1:
        violations.append(
            f"knot4-strip-self-ambiguous: expected 1 HOLD record, got {len(held_strip_amb)}"
        )
    elif (
        held_strip_amb[0].get("hold_reason")
        != "multiple_reroute_addresses_no_single_owner"
    ):
        violations.append(
            "knot4-strip-self-ambiguous: wrong hold_reason="
            f"{held_strip_amb[0].get('hold_reason')}"
        )
    elif held_strip_amb[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append(
            "knot4-strip-self-ambiguous: HOLD did not require caller-or-coo disposition"
        )
    if fr_strip_amb["frontier_kind"] != "link_paused":
        violations.append(
            "knot4-strip-self-ambiguous: true multi-sibling concern did not pause "
            f"(frontier={fr_strip_amb['frontier_kind']})"
        )
    if any(count != 0 for count in landings_strip_amb.values()):
        violations.append(
            "knot4-strip-self-ambiguous: HOLD moved a node reroute-landing counter "
            f"({landings_strip_amb})"
        )

    # KNOT-4 resolver FIRE (non-reroute sentinel): a non-binding concern whose
    # related_boundary_refs is NON-EMPTY and names ONLY building-boundary:
    # sentinel(s) (NO Brick-targeting ref) is an EXPLICIT non-reroute concern: the
    # Agent raised a concern WITHOUT proposing a reroute address. building-boundary:
    # is an admitted non-brick-node prefix (agent/return_fact.py). The walk must
    # WALK ON (carry forward to closure) -- NOT HOLD on an absent reroute address.
    # The legacy engine walked on for this; the no_resolving_reroute_address HOLD
    # would WRONGLY pause it (this drove brick-protocol-engine-feature-hard to
    # link_paused in --all). This is a PERMANENT regression guard: revert the
    # non_reroute carve-out in _classify_reroute_target / walker_kernel and this
    # goes RED (the walk HOLDs no_resolving_reroute_address instead of completing).
    plan_nr, _ = _checker_plan("bapr-loop0-knot4-non-reroute-sentinel", budget=1)
    res_nr, fr_nr, rec_nr = _run(
        plan_nr,
        _multi_ref_concern_callable(
            "brick-bapr-loop0-knot4-non-reroute-sentinel-review",
            ["building-boundary:bapr-loop0-knot4-non-reroute-sentinel-no-reroute"],
        ),
        repo,
    )
    if rec_nr:
        violations.append(
            "knot4-non-reroute-sentinel: a non-reroute (building-boundary:-only) "
            f"concern produced reroute/HOLD records (must walk on): {rec_nr}"
        )
    if fr_nr["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "knot4-non-reroute-sentinel: explicit non-reroute concern did not walk on "
            f"(frontier={fr_nr['frontier_kind']}; expected complete/closure_pending, NOT link_paused)"
        )
    evidence_nr = getattr(res_nr, "_dynamic_walker_evidence", {})
    if isinstance(evidence_nr, Mapping) and evidence_nr.get("held"):
        violations.append(
            "knot4-non-reroute-sentinel: non-reroute concern was recorded as held"
        )
    landings_nr = (
        evidence_nr.get("node_reroute_landings", {})
        if isinstance(evidence_nr, Mapping)
        else {}
    )
    if any(count != 0 for count in landings_nr.values()):
        violations.append(
            "knot4-non-reroute-sentinel: walk-on moved a node reroute-landing counter "
            f"({landings_nr})"
        )
    nr_bricks = _step_bricks(res_nr)
    if nr_bricks.count("brick-bapr-loop0-knot4-non-reroute-sentinel-review") != 1:
        violations.append(
            "knot4-non-reroute-sentinel: source node was re-executed instead of walking on "
            f"(count={nr_bricks.count('brick-bapr-loop0-knot4-non-reroute-sentinel-review')})"
        )
    nr_step_refs = [r.preparation.step_rows.step_ref for r in res_nr.step_results]
    if nr_step_refs != list(plan_nr["execution_order"]):
        violations.append(
            "knot4-non-reroute-sentinel: non-reroute walk-on altered the declared "
            f"execution_order ({nr_step_refs})"
        )

    # QA concern-emission policy FIRE: verification_gap is non-reroute evidence.
    # A verification/runtime/provider gap must not become an automatic reroute just
    # because it carries a Brick-node address. The validator must reject that shape
    # before the route classifier can adopt the otherwise-resolving target. The
    # companion sentinel case proves verification_gap still has a non-reroute
    # evidence channel and the policy is not a blanket concern ban.
    address_rule_phrase = "work/step-outputs"
    boundary_rule_phrase = "related_boundary_refs"
    valid_address_ref = "work/step-outputs/concern-attempt-1/step-output.json"
    valid_boundary_refs = {
        "bare brick target": "brick-bapr-loop0-address-contract-ok-build",
        "building-boundary sentinel": "building-boundary:bapr-loop0-address-contract-ok",
    }
    for label_boundary, ref_boundary in valid_boundary_refs.items():
        try:
            validate_transition_concern_evidence(
                {
                    "concern_ref": f"transition-concern:bapr-loop0-address-contract-ok-{label_boundary.replace(' ', '-')}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [valid_address_ref, "observation:address-contract-ok"],
                    "related_boundary_refs": [ref_boundary],
                }
            )
        except ValueError as exc:
            violations.append(
                "address-contract-intake: valid related_boundary_refs form "
                f"{label_boundary} was rejected ({exc})"
            )
    # Machine-authored proof-obligation concerns (walker_transition_concern.py
    # _observe path) MUST round-trip the SAME strict grammar as Agent-authored
    # concerns — there is NO normalization shim: the producer emits the bare
    # declared-node ref (or the building-boundary: sentinel when the instance
    # ref is not a bare brick- node), and intake validates it unchanged.
    machine_proof_concern = {
        "concern_ref": (
            "transition-concern:proof-obligation:"
            "bapr-loop0-address-contract-machine:"
            "bapr-loop0-address-contract-machine-build"
        ),
        "concern_kind": "implementation_gap",
        "binding": False,
        "reason_refs": [
            "brick-comparison:bapr-loop0-address-contract-machine:"
            "bapr-loop0-address-contract-machine-build"
        ],
        "related_boundary_refs": [
            "brick-bapr-loop0-address-contract-machine-build"
        ],
    }
    try:
        checked_machine = validate_transition_concern_evidence(machine_proof_concern)
    except ValueError as exc:
        violations.append(
            "address-contract-intake: machine-authored proof-obligation concern "
            f"with a bare brick- related_boundary_ref was rejected ({exc})"
        )
    else:
        if checked_machine.get("related_boundary_refs") != (
            machine_proof_concern["related_boundary_refs"]
        ):
            violations.append(
                "address-contract-intake: machine-authored proof-obligation "
                "related_boundary_refs were altered by intake "
                f"({checked_machine.get('related_boundary_refs')!r}); intake must "
                "validate without normalizing"
            )
    fresh_prefix_bypass_refs = {
        "fresh proof-obligation with matching comparison evidence": (
            "transition-concern:proof-obligation:ANY-NEW-BUILDING:ANY-NEW-STEP",
            "brick:brick-ANY-NEW-STEP",
            ["brick-comparison:ANY-NEW-BUILDING:ANY-NEW-STEP"],
        ),
        "fresh proof-obligation arbitrary target without comparison evidence": (
            "transition-concern:proof-obligation:ANY-NEW-BUILDING:ANY-NEW-STEP",
            "brick:attacker-declared-target",
            ["observation:fresh-prefix-boundary-contract"],
        ),
        "fresh proof-obligation matching step without comparison evidence": (
            "transition-concern:proof-obligation:ANY-NEW-BUILDING:ANY-NEW-STEP",
            "brick:ANY-NEW-STEP",
            ["observation:fresh-prefix-boundary-contract"],
        ),
        "fresh proof-obligation matching building without comparison evidence": (
            "transition-concern:proof-obligation:ANY-NEW-BUILDING:ANY-NEW-STEP",
            "brick:ANY-NEW-BUILDING-some-target",
            ["observation:fresh-prefix-boundary-contract"],
        ),
        "fresh mail-old-shape arbitrary target": (
            "transition-concern:mail-old-shape:any-new-label",
            "brick:attacker-declared-target",
            ["observation:fresh-prefix-boundary-contract"],
        ),
        "fresh exact short mail-old-shape arbitrary target": (
            "transition-concern:mail-old-shape:short",
            "brick:attacker-declared-target",
            ["observation:fresh-prefix-boundary-contract"],
        ),
        "fresh exact attempt mail-old-shape arbitrary target": (
            "transition-concern:mail-old-shape:attempt-1",
            "brick:attacker-declared-target",
            ["observation:fresh-prefix-boundary-contract"],
        ),
    }
    for label_boundary, (
        concern_ref,
        ref_boundary,
        reason_refs,
    ) in fresh_prefix_bypass_refs.items():
        try:
            validate_transition_concern_evidence(
                {
                    "concern_ref": concern_ref,
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": reason_refs,
                    "related_boundary_refs": [ref_boundary],
                }
            )
        except ValueError as exc:
            message = str(exc)
            if ref_boundary not in message or boundary_rule_phrase not in message:
                violations.append(
                    f"address-contract-intake: {label_boundary} rejected with an "
                    f"unhelpful message ({exc})"
                )
        else:
            violations.append(
                f"address-contract-intake: {label_boundary} accepted old-shape "
                "related_boundary_refs without replay/machine-authored context"
            )
    invalid_address_refs = {
        "fragment-bearing step-output ref": (
            "work/step-outputs/concern-attempt-1/step-output.json#observed"
        ),
        "bare file:line citation": "agent/return_fact.py:128",
        "non-step-output slash path": "raw/link.jsonl",
    }
    for label_addr, ref_addr in invalid_address_refs.items():
        try:
            validate_transition_concern_evidence(
                {
                    "concern_ref": f"transition-concern:bapr-loop0-address-contract-{label_addr.replace(' ', '-')}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [ref_addr],
                    "related_boundary_refs": [
                        f"brick-bapr-loop0-address-contract-{label_addr.replace(' ', '-')}-build"
                    ],
                }
            )
        except ValueError as exc:
            message = str(exc)
            if ref_addr not in message or address_rule_phrase not in message:
                violations.append(
                    f"address-contract-intake: {label_addr} rejected with an "
                    f"unhelpful message ({exc})"
                )
        else:
            violations.append(
                f"address-contract-intake: {label_addr} was accepted; malformed "
                "reason_refs must fail at new Agent-return intake"
            )
    invalid_boundary_refs = {
        "descriptive prose": "work node that made the bug",
        "bare file:line citation": "agent/return_fact.py:128",
        "slash path": "brick/templates/bricks/work/return.yaml",
        "colon numeric brick ref": "brick-foo:128",
        "colon text brick ref": "brick-foo:bar",
        "empty brick ref": "brick-",
        "empty building-boundary ref": "building-boundary:",
        "legacy brick-colon prefix": "brick:brick-foo",
        "legacy brick-instance prefix": "brick-instance:brick-foo",
        "legacy brick-boundary prefix": "brick-boundary:brick-foo",
    }
    for label_boundary, ref_boundary in invalid_boundary_refs.items():
        try:
            validate_transition_concern_evidence(
                {
                    "concern_ref": f"transition-concern:bapr-loop0-boundary-contract-{label_boundary.replace(' ', '-')}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": ["observation:boundary-contract"],
                    "related_boundary_refs": [ref_boundary],
                }
            )
        except ValueError as exc:
            message = str(exc)
            if ref_boundary not in message or boundary_rule_phrase not in message:
                violations.append(
                    f"address-contract-intake: {label_boundary} related_boundary_ref "
                    f"rejected with an unhelpful message ({exc})"
                )
        else:
            violations.append(
                f"address-contract-intake: {label_boundary} was accepted; malformed "
                "related_boundary_refs must fail at new Agent-return intake"
            )

    plan_vg_target, b2_vg_target = _checker_plan(
        "bapr-loop0-qa-verification-gap-brick-target",
        budget=1,
    )
    source_vg_target = "brick-bapr-loop0-qa-verification-gap-brick-target-review"
    pre_policy_classification = _classify_reroute_target(
        {"related_boundary_refs": [b2_vg_target]},
        declared_bricks={source_vg_target, b2_vg_target},
        source_brick_ref=source_vg_target,
    )
    if (
        pre_policy_classification.kind != "single"
        or pre_policy_classification.target != b2_vg_target
    ):
        violations.append(
            "qa-verification-gap-brick-target: pre-policy classifier control did not "
            f"show the old auto-reroute path ({pre_policy_classification})"
        )
    try:
        validate_transition_concern_evidence(
            {
                "concern_ref": f"transition-concern:{source_vg_target}",
                "concern_kind": "verification_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{source_vg_target}"],
                "related_boundary_refs": [b2_vg_target],
            }
        )
    except ValueError as exc:
        if "verification_gap must not name a reroute-capable Brick boundary" not in str(exc):
            violations.append(
                "qa-verification-gap-brick-target: validator rejected with the wrong "
                f"reason ({exc})"
            )
    else:
        violations.append(
            "qa-verification-gap-brick-target: validator accepted a verification_gap "
            "with a Brick-node reroute address"
        )
    res_vg_target, fr_vg_target, rec_vg_target = _run(
        plan_vg_target,
        _multi_ref_concern_callable(
            source_vg_target,
            [b2_vg_target],
            concern_kind="verification_gap",
        ),
        repo,
    )
    adopted_vg_target = _adopted_records(rec_vg_target)
    held_vg_target = _held_records(rec_vg_target)
    if adopted_vg_target:
        violations.append(
            "qa-verification-gap-brick-target: verification_gap Brick target was "
            f"adopted as a reroute ({adopted_vg_target})"
        )
    if fr_vg_target["frontier_kind"] != "link_paused":
        violations.append(
            "qa-verification-gap-brick-target: invalid verification_gap target did "
            f"not pause (frontier={fr_vg_target['frontier_kind']})"
        )
    if len(held_vg_target) != 1:
        violations.append(
            "qa-verification-gap-brick-target: expected 1 invalid-concern HOLD, "
            f"got {len(held_vg_target)}"
        )
    elif held_vg_target[0].get("hold_reason") != "invalid_transition_concern_evidence":
        violations.append(
            "qa-verification-gap-brick-target: wrong hold_reason="
            f"{held_vg_target[0].get('hold_reason')}"
        )
    vg_target_bricks = _step_bricks(res_vg_target)
    if vg_target_bricks.count(b2_vg_target) != 1:
        violations.append(
            "qa-verification-gap-brick-target: verification_gap caused target "
            f"re-execution (count={vg_target_bricks.count(b2_vg_target)})"
        )

    plan_vg_sentinel, _ = _checker_plan(
        "bapr-loop0-qa-verification-gap-sentinel",
        budget=1,
    )
    source_vg_sentinel = "brick-bapr-loop0-qa-verification-gap-sentinel-review"
    try:
        validate_transition_concern_evidence(
            {
                "concern_ref": f"transition-concern:{source_vg_sentinel}",
                "concern_kind": "verification_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{source_vg_sentinel}"],
                "related_boundary_refs": [
                    "building-boundary:bapr-loop0-qa-verification-gap-sentinel-no-reroute"
                ],
            }
        )
    except ValueError as exc:
        violations.append(
            "qa-verification-gap-sentinel: validator rejected the non-reroute "
            f"sentinel channel ({exc})"
        )
    res_vg_sentinel, fr_vg_sentinel, rec_vg_sentinel = _run(
        plan_vg_sentinel,
        _multi_ref_concern_callable(
            source_vg_sentinel,
            ["building-boundary:bapr-loop0-qa-verification-gap-sentinel-no-reroute"],
            concern_kind="verification_gap",
        ),
        repo,
    )
    if rec_vg_sentinel:
        violations.append(
            "qa-verification-gap-sentinel: non-reroute verification_gap produced "
            f"reroute/HOLD records ({rec_vg_sentinel})"
        )
    if fr_vg_sentinel["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "qa-verification-gap-sentinel: non-reroute verification_gap did not "
            f"walk on (frontier={fr_vg_sentinel['frontier_kind']})"
        )
    vg_sentinel_step_refs = [
        r.preparation.step_rows.step_ref for r in res_vg_sentinel.step_results
    ]
    if vg_sentinel_step_refs != list(plan_vg_sentinel["execution_order"]):
        violations.append(
            "qa-verification-gap-sentinel: non-reroute verification_gap altered "
            f"declared execution_order ({vg_sentinel_step_refs})"
        )

    plan_vg_empty, _ = _checker_plan(
        "bapr-loop0-qa-verification-gap-empty",
        budget=1,
    )
    source_vg_empty = "brick-bapr-loop0-qa-verification-gap-empty-review"
    try:
        validate_transition_concern_evidence(
            {
                "concern_ref": f"transition-concern:{source_vg_empty}",
                "concern_kind": "verification_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{source_vg_empty}"],
                "related_boundary_refs": [],
            }
        )
    except ValueError as exc:
        violations.append(
            "qa-verification-gap-empty: validator rejected the empty non-reroute "
            f"channel ({exc})"
        )
    res_vg_empty, fr_vg_empty, rec_vg_empty = _run(
        plan_vg_empty,
        _multi_ref_concern_callable(
            source_vg_empty,
            [],
            concern_kind="verification_gap",
        ),
        repo,
    )
    if rec_vg_empty:
        violations.append(
            "qa-verification-gap-empty: empty non-reroute verification_gap produced "
            f"reroute/HOLD records ({rec_vg_empty})"
        )
    if fr_vg_empty["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "qa-verification-gap-empty: empty non-reroute verification_gap did not "
            f"walk on (frontier={fr_vg_empty['frontier_kind']})"
        )
    vg_empty_step_refs = [
        r.preparation.step_rows.step_ref for r in res_vg_empty.step_results
    ]
    if vg_empty_step_refs != list(plan_vg_empty["execution_order"]):
        violations.append(
            "qa-verification-gap-empty: empty non-reroute verification_gap altered "
            f"declared execution_order ({vg_empty_step_refs})"
        )

    # FIX A -- KNOT-4 resolver FIRE (non-reroute MIXED): the sentinel-only fixture
    # above does NOT catch an all(...)->any(...) mutation at
    # walker_transition_concern.py:121 (with an ALL-sentinel list, all() and any()
    # agree). This sibling MIXES one building-boundary: sentinel with one UNDECLARED
    # brick-targeting ref. The carve-out requires EVERY ref to be a
    # building-boundary: sentinel (all(...)), so a mixed list is NOT a non-reroute
    # concern: it has a brick-targeting ref that fails to resolve -> kind='none' ->
    # HOLD (no_resolving_reroute_address). If the carve-out's all(...) is mutated to
    # any(...), the mixed list would WRONGLY classify as non_reroute (walk on) and
    # this case goes RED. PERMANENT mutation guard for the carve-out predicate.
    plan_mixed, _ = _checker_plan("bapr-loop0-knot4-non-reroute-mixed", budget=1)
    res_mixed, fr_mixed, rec_mixed = _run(
        plan_mixed,
        _multi_ref_concern_callable(
            "brick-bapr-loop0-knot4-non-reroute-mixed-review",
            [
                "building-boundary:bapr-loop0-knot4-non-reroute-mixed-no-reroute",
                "brick-bapr-loop0-knot4-non-reroute-mixed-not-declared",
            ],
        ),
        repo,
    )
    adopted_mixed = _adopted_records(rec_mixed)
    held_mixed = _held_records(rec_mixed)
    evidence_mixed = getattr(res_mixed, "_dynamic_walker_evidence", {})
    landings_mixed = (
        evidence_mixed.get("node_reroute_landings", {})
        if isinstance(evidence_mixed, Mapping)
        else {}
    )
    if adopted_mixed:
        violations.append("knot4-non-reroute-mixed: a mixed sentinel+garbage concern was adopted")
    if len(held_mixed) != 1:
        violations.append(
            f"knot4-non-reroute-mixed: expected 1 HOLD record, got {len(held_mixed)} "
            "(an all->any mutation of the non_reroute carve-out would WALK ON here instead)"
        )
    elif held_mixed[0].get("hold_reason") != "no_resolving_reroute_address":
        violations.append(
            "knot4-non-reroute-mixed: wrong hold_reason="
            f"{held_mixed[0].get('hold_reason')}"
        )
    elif held_mixed[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append("knot4-non-reroute-mixed: HOLD did not require caller-or-coo disposition")
    if fr_mixed["frontier_kind"] != "link_paused":
        violations.append(
            "knot4-non-reroute-mixed: mixed sentinel+garbage concern did not pause "
            f"(frontier={fr_mixed['frontier_kind']}; an all->any carve-out mutation would complete here)"
        )
    if any(count != 0 for count in landings_mixed.values()):
        violations.append(
            "knot4-non-reroute-mixed: HOLD moved a node reroute-landing counter "
            f"({landings_mixed})"
        )
    mixed_bricks = _step_bricks(res_mixed)
    if mixed_bricks.count("brick-bapr-loop0-knot4-non-reroute-mixed-review") != 1:
        violations.append(
            "knot4-non-reroute-mixed: source node was re-executed instead of pausing "
            f"(count={mixed_bricks.count('brick-bapr-loop0-knot4-non-reroute-mixed-review')})"
        )

    # KNOT-4 resolver FIRE (c): ONE RESOLVING + ONE GARBAGE -> HOLD, NOT silent
    # single deliver. STRICT (Smith ruling): a brick-targeting ref that is NAMED
    # but does NOT resolve to a declared node AND is NOT a building-boundary:
    # sentinel is a garbage/typo/stale address. Today, when one valid ref also
    # resolves, the garbage is silently DROPPED and the walk delivers ``single``.
    # That silent drop is the bug: a co-occurring unresolvable brick-targeting
    # address must HOLD (unresolvable_reroute_address, caller-or-coo, paused
    # frontier, NO node reroute-landing) so a human sees the bad address. This
    # SUPERSEDES the prior single-deliver assertion. Revert the unresolvable->HOLD
    # logic in _classify_reroute_target and this goes RED (the walk silently
    # delivers single instead of holding).
    plan_c_single, b2_c_single = _checker_plan("bapr-loop0-knot4-one-good-one-garbage", budget=2)
    res_single, fr_single, rec_single = _run(
        plan_c_single,
        _multi_ref_concern_callable(
            "brick-bapr-loop0-knot4-one-good-one-garbage-review",
            [b2_c_single, "brick-bapr-loop0-knot4-garbage-not-declared"],
        ),
        repo,
    )
    adopted_single = _adopted_records(rec_single)
    held_single = _held_records(rec_single)
    evidence_single = getattr(res_single, "_dynamic_walker_evidence", {})
    landings_single = (
        evidence_single.get("node_reroute_landings", {})
        if isinstance(evidence_single, Mapping)
        else {}
    )
    if adopted_single:
        violations.append(
            "knot4-one-good-one-garbage: a resolving+garbage concern was adopted (single "
            "deliver) instead of HOLDing on the co-occurring unresolvable address "
            f"({adopted_single})"
        )
    if len(held_single) != 1:
        violations.append(
            f"knot4-one-good-one-garbage: expected 1 HOLD record, got {len(held_single)}"
        )
    elif held_single[0].get("hold_reason") != "unresolvable_reroute_address":
        violations.append(
            "knot4-one-good-one-garbage: wrong hold_reason="
            f"{held_single[0].get('hold_reason')}"
        )
    elif held_single[0].get("required_disposition_owner") != "caller-or-coo":
        violations.append(
            "knot4-one-good-one-garbage: HOLD did not require caller-or-coo disposition"
        )
    if fr_single["frontier_kind"] != "link_paused":
        violations.append(
            "knot4-one-good-one-garbage: co-occurring unresolvable address did not pause "
            f"(frontier={fr_single['frontier_kind']})"
        )
    if any(count != 0 for count in landings_single.values()):
        violations.append(
            "knot4-one-good-one-garbage: HOLD moved a node reroute-landing counter "
            f"({landings_single})"
        )
    single_bricks = _step_bricks(res_single)
    if single_bricks.count(b2_c_single) != 1:
        violations.append(
            "knot4-one-good-one-garbage: resolving node was re-executed (silent single "
            f"deliver) instead of pausing (count={single_bricks.count(b2_c_single)})"
        )

    # KNOT-4 resolver FIRE (c): another-node target with budget remains a true
    # reroute. The self-reroute guard must not soften or skip this path.
    plan_other, b2_other = _checker_plan("bapr-loop0-knot4-other-target-control", budget=1)
    source_other = "brick-bapr-loop0-knot4-other-target-control-review"
    other_classification = _classify_reroute_target(
        {
            "related_boundary_refs": [b2_other],
        },
        declared_bricks={source_other, b2_other},
        source_brick_ref=source_other,
    )
    if other_classification.kind != "single" or other_classification.target != b2_other:
        violations.append(
            "knot4-other-target-control: direct classifier softened a true "
            f"reroute ({other_classification})"
        )
    res_other, fr_other, rec_other = _run(
        plan_other,
        _multi_ref_concern_callable(source_other, [b2_other]),
        repo,
    )
    adopted_other = _adopted_records(rec_other)
    held_other = _held_records(rec_other)
    if len(adopted_other) != 1:
        violations.append(
            "knot4-other-target-control: expected one adopted true reroute, "
            f"got {len(adopted_other)} ({rec_other})"
        )
    elif adopted_other[0].get("target_brick") != b2_other:
        violations.append(
            "knot4-other-target-control: adopted target drifted "
            f"({adopted_other[0].get('target_brick')})"
        )
    if held_other:
        violations.append(
            "knot4-other-target-control: true reroute unexpectedly paused "
            f"({held_other})"
        )
    if fr_other["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            "knot4-other-target-control: true reroute did not proceed "
            f"(frontier={fr_other['frontier_kind']})"
        )
    other_bricks = _step_bricks(res_other)
    if other_bricks.count(b2_other) < 2:
        violations.append(
            "knot4-other-target-control: true target was not re-executed "
            f"(count={other_bricks.count(b2_other)})"
        )

    # KNOT-4 resolver FIRE (d): NO CONCERN AT ALL -> walk on unchanged (no HOLD,
    # no record, declared execution_order preserved).
    plan_none, _ = _checker_plan("bapr-loop0-knot4-no-concern", budget=1)
    res_none, fr_none, rec_none = _run(plan_none, _reroute_callable("brick-unused", set()), repo)
    if rec_none:
        violations.append(f"knot4-no-concern: a walk with no concern produced reroute records ({rec_none})")
    if fr_none["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(f"knot4-no-concern: no-concern walk did not complete ({fr_none['frontier_kind']})")
    none_step_refs = [r.preparation.step_rows.step_ref for r in res_none.step_results]
    if none_step_refs != list(plan_none["execution_order"]):
        violations.append(f"knot4-no-concern: no-concern walk altered order ({none_step_refs})")

    # KNOT-4 RESUME PARITY FIRE (FIX #1): the RESUME continued-step path must HOLD on
    # ambiguous/none/unresolvable concerns EXACTLY like the FORWARD dynamic-walk
    # (knot4-ambiguous / knot4-empty / knot4-one-good-one-garbage above). Before the
    # fix, _continue_resume_queue consumed the _proposed_target_brick str|None
    # compatibility shape and had NO else -> a resumed CONTINUED step raising a
    # non-single concern was SILENTLY DROPPED (the walk completed to close). Setup:
    # build's outgoing edge carries a HUMAN gate, so build's own agent-proposed
    # reroute PAUSEs (budget-free, build runs once -> no body-carry re-walk noise). A
    # human FORWARD disposition resumes; the residual continues from `review`, a
    # CONTINUED step that never ran in the forward run. `review` then raises the
    # non-single concern -> resume MUST HOLD (not silently complete).
    # SELF-FIRE: revert the FIX #1 else-HOLD branch in walker_resume.py and resume
    # SILENTLY completes through close -> these cases go RED.
    from brick_protocol.support.operator.run import run_building_plan, resume_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier

    def _resume_continued_concern_callable(
        *, pause_source_brick: str, continued_brick: str, related_boundary_refs: list[str]
    ):
        """pause_source_brick proposes a reroute (its HUMAN-gated edge PAUSEs the
        walk); continued_brick (a NOT-yet-run step) raises a concern naming
        related_boundary_refs verbatim once it runs on resume."""

        def _callable(request: Any) -> Mapping[str, Any]:
            ref = request.brick_instance_ref
            returned: dict[str, Any] = {
                "observed_evidence": [f"obs {ref}"],
                "not_proven": ["semantic correctness"],
            }
            if ref == pause_source_brick:
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{ref}"],
                    "related_boundary_refs": [continued_brick],
                }
            elif ref == continued_brick:
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{ref}"],
                    "related_boundary_refs": list(related_boundary_refs),
                }
            return returned

        return _callable

    # (label, related_boundary_refs builder, expected resume hold_reason)
    _resume_parity_cases = [
        (
            "ambiguous",
            lambda design, build, garbage: [design, build],  # two resolving
            "multiple_reroute_addresses_no_single_owner",
        ),
        (
            "empty",
            lambda design, build, garbage: [],  # present concern, no refs
            "no_resolving_reroute_address",
        ),
        (
            "garbage",
            lambda design, build, garbage: [build, garbage],  # valid + co-occurring garbage
            "unresolvable_reroute_address",
        ),
    ]
    for label, refs_for, expected_reason in _resume_parity_cases:
        prefix = f"bapr-loop0-knot4-resume-{label}"
        plan_rp, build_rp = _checker_plan(prefix, budget=1)
        design_rp = f"brick-{prefix}-design"
        review_rp = f"brick-{prefix}-review"
        close_rp = f"brick-{prefix}-close"
        garbage_rp = f"brick-{prefix}-garbage-not-declared"
        # HUMAN gate on build's outgoing edge -> build's reroute PAUSEs (budget-free).
        plan_rp = _with_link_edge_gate(
            plan_rp,
            f"edge:{prefix}-build-to-review",
            ["link-gate:default-transition", "link-gate:human"],
        )
        callable_rp = _resume_continued_concern_callable(
            pause_source_brick=build_rp,
            continued_brick=review_rp,
            related_boundary_refs=refs_for(design_rp, build_rp, garbage_rp),
        )
        with tempfile.TemporaryDirectory(prefix=f"bp-bapr-knot4-resume-{label}-") as tmp_rp:
            res_rp = run_building_plan(
                plan_rp,
                output_root=Path(tmp_rp),
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": callable_rp},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
            root_rp = res_rp.lifecycle_write.root
            before_rp = observe_building_frontier(root_rp, repo_root=repo)
            bricks_run_rp = _step_bricks(res_rp)
            if before_rp["frontier_kind"] != "link_paused":
                violations.append(
                    f"knot4-resume-{label}: setup did not PAUSE on build's human gate "
                    f"(frontier={before_rp['frontier_kind']})"
                )
            if review_rp in bricks_run_rp:
                violations.append(
                    f"knot4-resume-{label}: setup invalid -- review ran in the forward run "
                    "(must be a CONTINUED step on resume)"
                )
            hold_rp = (
                res_rp._dynamic_walker_evidence.get("hold", {})
                if isinstance(getattr(res_rp, "_dynamic_walker_evidence", {}), Mapping)
                else {}
            )
            _append_disposition_row(
                root_rp,
                building_id=res_rp.building_id,
                pending_target_ref=hold_rp.get("pending_target_ref") or review_rp,
                action="forward",
                author_ref="coo:smith",
            )
            try:
                resumed_rp = resume_building_plan(
                    root_rp,
                    local_callables={"callable:local:agent-invoke0-smoke": callable_rp},
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
                violations.append(f"knot4-resume-{label}: resume crashed: {exc}")
                continue
            after_rp = observe_building_frontier(resumed_rp.lifecycle_write.root, repo_root=repo)
            bricks_rp = _step_bricks(resumed_rp)
            evidence_rp = getattr(resumed_rp, "_dynamic_walker_evidence", {})
            if not isinstance(evidence_rp, Mapping):
                evidence_rp = {}
            hold_after_rp = (
                evidence_rp.get("hold", {})
                if isinstance(evidence_rp.get("hold"), Mapping)
                else {}
            )
            # THE FIX #1 GUARD: a resumed CONTINUED step raising a non-single concern
            # must HOLD, never silently complete. Reverting the else-HOLD turns this RED.
            if after_rp["frontier_kind"] != "link_paused":
                violations.append(
                    f"knot4-resume-{label} (FIX #1): a resumed CONTINUED step's non-single "
                    "concern was SILENTLY DROPPED -- resume did not HOLD "
                    f"(frontier={after_rp['frontier_kind']}, bricks={bricks_rp})"
                )
            if hold_after_rp.get("hold_reason") != expected_reason:
                violations.append(
                    f"knot4-resume-{label} (FIX #1): wrong/absent resume hold_reason="
                    f"{hold_after_rp.get('hold_reason')} (expected {expected_reason})"
                )
            if hold_after_rp.get("required_disposition_owner") != "caller-or-coo":
                violations.append(
                    f"knot4-resume-{label} (FIX #1): resume HOLD did not require caller-or-coo "
                    f"disposition (owner={hold_after_rp.get('required_disposition_owner')})"
                )
            if close_rp in bricks_rp:
                violations.append(
                    f"knot4-resume-{label} (FIX #1): resume walked past the dropped concern to "
                    f"close (bricks={bricks_rp})"
                )
            # BUDGET-FREE: the non-single HOLD must not touch any node landing counter.
            landings_rp = evidence_rp.get("node_reroute_landings", {})
            if landings_rp.get(build_rp, 0) != 0:
                violations.append(
                    f"knot4-resume-{label} (FIX #1): non-single HOLD moved a node landing "
                    f"counter ({landings_rp})"
                )

    # KNOT-4 RESUME PARITY FIRE (FIX #1, non_reroute walk-on): a resumed CONTINUED
    # step raising an EXPLICIT non_reroute concern (building-boundary: sentinel only)
    # must WALK ON, not HOLD -- parity with the forward kernel non_reroute carve-out.
    # Guards the fix against over-HOLDing.
    prefix_nr = "bapr-loop0-knot4-resume-nonreroute"
    plan_nr_resume, build_nr_resume = _checker_plan(prefix_nr, budget=1)
    review_nr_resume = f"brick-{prefix_nr}-review"
    close_nr_resume = f"brick-{prefix_nr}-close"
    plan_nr_resume = _with_link_edge_gate(
        plan_nr_resume,
        f"edge:{prefix_nr}-build-to-review",
        ["link-gate:default-transition", "link-gate:human"],
    )
    callable_nr_resume = _resume_continued_concern_callable(
        pause_source_brick=build_nr_resume,
        continued_brick=review_nr_resume,
        related_boundary_refs=[f"building-boundary:{prefix_nr}-no-reroute"],
    )
    with checker_temp_path("bp-bapr-knot4-resume-nonreroute-") as tmp_nr:
        res_nr_resume = run_building_plan(
            plan_nr_resume,
            output_root=tmp_nr,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_nr_resume},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_nr_resume = res_nr_resume.lifecycle_write.root
        before_nr_resume = observe_building_frontier(root_nr_resume, repo_root=repo)
        if before_nr_resume["frontier_kind"] != "link_paused":
            violations.append(
                "knot4-resume-nonreroute: setup did not PAUSE on build's human gate "
                f"(frontier={before_nr_resume['frontier_kind']})"
            )
        hold_nr_resume = (
            res_nr_resume._dynamic_walker_evidence.get("hold", {})
            if isinstance(getattr(res_nr_resume, "_dynamic_walker_evidence", {}), Mapping)
            else {}
        )
        _append_disposition_row(
            root_nr_resume,
            building_id=res_nr_resume.building_id,
            pending_target_ref=hold_nr_resume.get("pending_target_ref") or review_nr_resume,
            action="forward",
            author_ref="coo:smith",
        )
        try:
            resumed_nr = resume_building_plan(
                root_nr_resume,
                local_callables={"callable:local:agent-invoke0-smoke": callable_nr_resume},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
            violations.append(f"knot4-resume-nonreroute: resume crashed: {exc}")
        else:
            after_nr = observe_building_frontier(resumed_nr.lifecycle_write.root, repo_root=repo)
            bricks_nr = _step_bricks(resumed_nr)
            if after_nr["frontier_kind"] not in {"complete", "closure_pending"}:
                violations.append(
                    "knot4-resume-nonreroute: an explicit non_reroute concern did not WALK ON "
                    f"on resume (frontier={after_nr['frontier_kind']}, bricks={bricks_nr})"
                )
            if close_nr_resume not in bricks_nr:
                violations.append(
                    "knot4-resume-nonreroute: non_reroute walk-on did not reach close "
                    f"(bricks={bricks_nr})"
                )

    # Live regression from REPORTER-NOTIFICATION-PROJECTION-0: a malformed
    # transition_concern_evidence with an extra key must not be adopted by the
    # dynamic walker and must not crash step-output recording.
    plan_invalid, b2_invalid = _checker_plan("bapr-loop0-invalid-concern", budget=1)
    source_invalid = "brick-bapr-loop0-invalid-concern-review"
    res_invalid, fr_invalid, rec_invalid = _run(
        plan_invalid,
        _invalid_concern_callable(source_invalid, b2_invalid),
        repo,
    )
    held_invalid = _held_records(rec_invalid)
    if fr_invalid["frontier_kind"] != "link_paused":
        violations.append(
            "invalid-concern: malformed transition_concern_evidence did not pause "
            f"(frontier={fr_invalid['frontier_kind']})"
        )
    if len(held_invalid) != 1:
        violations.append(f"invalid-concern: expected 1 HOLD record, got {len(held_invalid)}")
    elif held_invalid[0].get("hold_reason") != "invalid_transition_concern_evidence":
        violations.append(
            "invalid-concern: wrong hold_reason="
            f"{held_invalid[0].get('hold_reason')}"
        )
    elif any(
        held_invalid[0].get(field) != source_invalid
        for field in ("immediate_target_ref", "target_brick", "pending_target_ref")
    ):
        violations.append(
            "invalid-concern: malformed concern copied proposed target into HOLD target fields "
            f"({held_invalid[0]})"
        )
    invalid_bricks = _step_bricks(res_invalid)
    if invalid_bricks.count(b2_invalid) != 1:
        violations.append(
            "invalid-concern: malformed concern caused an adopted target re-execution "
            f"(count={invalid_bricks.count(b2_invalid)})"
        )

    # Live regression from REPORTER-NOTIFICATION-PROJECTION-0: if an adapter
    # interrupts before AgentFact exists, the dynamic walker must write an
    # adapter-error frontier instead of crashing without a Building root.
    plan_adapter, _ = _checker_plan("bapr-loop0-adapter-frontier", budget=1)
    failing_brick = "brick-bapr-loop0-adapter-frontier-review"
    with checker_temp_path("bp-bapr-adapter-frontier-") as tmp_path:
        # B2: the dynamic adapter interruption now RETURNS a clean held result
        # (typed AdapterFrontierEvidenceWritten caught by run_building_plan) instead
        # of crashing with a bare RuntimeError. The adapter-error frontier must still
        # be written + held (asserted below via observe_building_frontier).
        try:
            run_building_plan(
                plan_adapter,
                output_root=tmp_path,
                overwrite_existing=True,
                local_callables={
                    "callable:local:agent-invoke0-smoke": _adapter_error_callable(
                        failing_brick
                    )
                },
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except RuntimeError as exc:
            violations.append(
                "adapter-frontier: adapter interruption must end in a clean held "
                f"result, not a bare RuntimeError ({exc!r})"
            )
        adapter_root = tmp_path / str(plan_adapter["building_id"])
        if not adapter_root.exists():
            violations.append("adapter-frontier: no Building root was written")
        else:
            frontier_adapter = observe_building_frontier(adapter_root, repo_root=repo)
            if frontier_adapter["frontier_kind"] != "agent_incomplete":
                violations.append(
                    "adapter-frontier: adapter interruption did not surface agent_incomplete "
                    f"(frontier={frontier_adapter['frontier_kind']})"
                )
            if not (adapter_root / "raw" / "adapter-error.jsonl").exists():
                violations.append("adapter-frontier: raw adapter-error record was not written")

    # B5 Invariant C10: SEQUENCE-MONOTONIC + NO-JUDGMENT. Reuse the C7
    # two-landing graph and assert strictly increasing adoption sequence numbers
    # plus the structured field-observation evidence contract.
    sequence_c10 = [r.get("adoption_sequence_number") for r in rec_c7]
    if sequence_c10 != [1, 2]:
        violations.append(f"b5-c10-sequence-no-judgment: adoption_sequence_number drifted ({sequence_c10})")
    for index, record in enumerate(rec_c7, start=1):
        observation = record.get("structured_field_observation")
        if not isinstance(observation, Mapping):
            violations.append(f"b5-c10-sequence-no-judgment: record {index} missing structured_field_observation")
            continue
        observation_keys = set(observation)
        if observation_keys != _STRUCTURED_FIELD_OBSERVATION_KEYS:
            violations.append(
                "b5-c10-sequence-no-judgment: structured_field_observation key set drifted "
                f"(record={index}, keys={sorted(observation_keys)})"
            )
        findings = _forbidden_judgment_label_findings(record)
        for finding in findings:
            violations.append(f"b5-c10-sequence-no-judgment: record {index} {finding}")

    # KNOT-3 COHORT FIRE (a): 3-source fan-in, reroute LANDS on source1 (lane-a) ->
    # sources 2 AND 3 (lane-b, lane-c) are BOTH re-walked as forward replay
    # (cohort re-verification: a fix in one lane can stale a sibling's prior PASS;
    # Brick has no data-dependency graph, so re-verify the whole cohort). The
    # cohort replays are BUDGET-FREE: node_landings touched ONLY for the actual
    # landing (lane-a), never for the budget-free cohort siblings. Revert the
    # cohort-expansion splice in walker_kernel -> lane-b/lane-c are NOT re-walked
    # and this goes RED.
    plan_cohort_a = _cohort_fan_plan("bapr-loop0-knot3-cohort-a")
    lane_a_a = "brick-bapr-loop0-knot3-cohort-a-lane-a"
    lane_b_a = "brick-bapr-loop0-knot3-cohort-a-lane-b"
    lane_c_a = "brick-bapr-loop0-knot3-cohort-a-lane-c"
    join_a = "brick-bapr-loop0-knot3-cohort-a-join"
    res_coa, fr_coa, rec_coa = _run(
        plan_cohort_a,
        _reroute_once_callable(join_a, lane_a_a),
        repo,
    )
    bricks_coa = _step_bricks(res_coa)
    evidence_coa = getattr(res_coa, "_dynamic_walker_evidence", {})
    landings_coa = (
        evidence_coa.get("node_reroute_landings", {})
        if isinstance(evidence_coa, Mapping)
        else {}
    )
    cohort_recs_coa = (
        evidence_coa.get("fan_in_cohort_records", [])
        if isinstance(evidence_coa, Mapping)
        else []
    )
    if bricks_coa.count(lane_a_a) != 2:
        violations.append(
            "knot3-cohort-a: reroute target lane-a did not re-execute exactly once "
            f"(count={bricks_coa.count(lane_a_a)})"
        )
    if bricks_coa.count(lane_b_a) != 2:
        violations.append(
            "knot3-cohort-a: sibling lane-b was NOT re-verified by the cohort "
            f"(count={bricks_coa.count(lane_b_a)}; expected 2)"
        )
    if bricks_coa.count(lane_c_a) != 2:
        violations.append(
            "knot3-cohort-a: sibling lane-c was NOT re-verified by the cohort "
            f"(count={bricks_coa.count(lane_c_a)}; expected 2)"
        )
    # BUDGET-FREE PIN: only lane-a (the actual landing) consumed a reroute landing.
    if landings_coa.get(lane_a_a) != 1:
        violations.append(
            "knot3-cohort-a: actual landing did not consume exactly 1 reroute budget "
            f"(node_landings={landings_coa})"
        )
    if landings_coa.get(lane_b_a, 0) != 0 or landings_coa.get(lane_c_a, 0) != 0:
        violations.append(
            "knot3-cohort-a: a cohort sibling re-walk consumed reroute budget (must be "
            f"forward-replay budget-free) (node_landings={landings_coa})"
        )
    # Cohort records: both siblings recorded as re_verified, none skipped.
    coa_reverified = {
        r.get("sibling_source_step_ref")
        for r in cohort_recs_coa
        if isinstance(r, Mapping) and r.get("disposition") == "re_verified"
    }
    if {
        "bapr-loop0-knot3-cohort-a-lane-b",
        "bapr-loop0-knot3-cohort-a-lane-c",
    } - coa_reverified:
        violations.append(
            "knot3-cohort-a: cohort records did not record both siblings as re_verified "
            f"({sorted(coa_reverified)})"
        )
    if any(
        isinstance(r, Mapping) and r.get("disposition") == "skipped"
        for r in cohort_recs_coa
    ):
        violations.append("knot3-cohort-a: a sibling was skipped with no sibling_independence vouch")
    if fr_coa["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            f"knot3-cohort-a: cohort re-verification did not walk on (frontier={fr_coa['frontier_kind']})"
        )

    # KNOT-3 COHORT FIRE (b): same shape + a HUMAN sibling_independence vouch on
    # lane-c -> lane-b re-walked, lane-c SKIPPED, and the skip is RECORDED with the
    # vouch ref. Support READS the vouch; it does not decide independence.
    plan_cohort_b = _cohort_fan_plan(
        "bapr-loop0-knot3-cohort-b",
        sibling_independence=["bapr-loop0-knot3-cohort-b-lane-c"],
    )
    lane_a_b = "brick-bapr-loop0-knot3-cohort-b-lane-a"
    lane_b_b = "brick-bapr-loop0-knot3-cohort-b-lane-b"
    lane_c_b = "brick-bapr-loop0-knot3-cohort-b-lane-c"
    join_b = "brick-bapr-loop0-knot3-cohort-b-join"
    res_cob, fr_cob, rec_cob = _run(
        plan_cohort_b,
        _reroute_once_callable(join_b, lane_a_b),
        repo,
    )
    bricks_cob = _step_bricks(res_cob)
    evidence_cob = getattr(res_cob, "_dynamic_walker_evidence", {})
    cohort_recs_cob = (
        evidence_cob.get("fan_in_cohort_records", [])
        if isinstance(evidence_cob, Mapping)
        else []
    )
    if bricks_cob.count(lane_b_b) != 2:
        violations.append(
            "knot3-cohort-b: vouched-sibling case re-walked lane-b incorrectly "
            f"(count={bricks_cob.count(lane_b_b)}; expected 2)"
        )
    if bricks_cob.count(lane_c_b) != 1:
        violations.append(
            "knot3-cohort-b: lane-c had a sibling_independence vouch but was STILL re-walked "
            f"(count={bricks_cob.count(lane_c_b)}; expected 1 = skipped)"
        )
    skip_recs_cob = [
        r
        for r in cohort_recs_cob
        if isinstance(r, Mapping) and r.get("disposition") == "skipped"
    ]
    if len(skip_recs_cob) != 1:
        violations.append(
            f"knot3-cohort-b: expected exactly 1 recorded sibling skip, got {len(skip_recs_cob)}"
        )
    else:
        skip = skip_recs_cob[0]
        if skip.get("sibling_source_step_ref") != "bapr-loop0-knot3-cohort-b-lane-c":
            violations.append(
                "knot3-cohort-b: skip record names the wrong sibling "
                f"({skip.get('sibling_source_step_ref')})"
            )
        if skip.get("sibling_independence_vouch_ref") != "bapr-loop0-knot3-cohort-b-lane-c":
            violations.append(
                "knot3-cohort-b: skip record did not carry the auditable sibling_independence "
                f"vouch ref ({skip.get('sibling_independence_vouch_ref')})"
            )
    if not any(
        isinstance(r, Mapping)
        and r.get("disposition") == "re_verified"
        and r.get("sibling_source_step_ref") == "bapr-loop0-knot3-cohort-b-lane-b"
        for r in cohort_recs_cob
    ):
        violations.append("knot3-cohort-b: lane-b was not recorded as re_verified")
    if fr_cob["frontier_kind"] not in {"complete", "closure_pending"}:
        violations.append(
            f"knot3-cohort-b: vouched cohort did not walk on (frontier={fr_cob['frontier_kind']})"
        )

    # KNOT-3 COHORT FIRE (c): NO vouch -> NO sibling skipped (conservative default).
    # This is the same assertion shape as (a) but framed as the explicit default:
    # an absent sibling_independence declaration must NEVER produce a skip.
    plan_cohort_c = _cohort_fan_plan("bapr-loop0-knot3-cohort-c")
    lane_a_c = "brick-bapr-loop0-knot3-cohort-c-lane-a"
    lane_b_c = "brick-bapr-loop0-knot3-cohort-c-lane-b"
    lane_c_c = "brick-bapr-loop0-knot3-cohort-c-lane-c"
    join_c = "brick-bapr-loop0-knot3-cohort-c-join"
    res_coc, fr_coc, _ = _run(
        plan_cohort_c,
        _reroute_once_callable(join_c, lane_a_c),
        repo,
    )
    bricks_coc = _step_bricks(res_coc)
    evidence_coc = getattr(res_coc, "_dynamic_walker_evidence", {})
    cohort_recs_coc = (
        evidence_coc.get("fan_in_cohort_records", [])
        if isinstance(evidence_coc, Mapping)
        else []
    )
    if any(
        isinstance(r, Mapping) and r.get("disposition") == "skipped"
        for r in cohort_recs_coc
    ):
        violations.append(
            "knot3-cohort-c: a sibling was skipped despite NO sibling_independence vouch "
            "(conservative default violated)"
        )
    if bricks_coc.count(lane_b_c) != 2 or bricks_coc.count(lane_c_c) != 2:
        violations.append(
            "knot3-cohort-c: conservative default did not re-verify all siblings "
            f"(lane-b={bricks_coc.count(lane_b_c)}, lane-c={bricks_coc.count(lane_c_c)})"
        )

    # KNOT-3 COHORT FIRE (d) MULTI-TARGET CROSS-VOUCH (catches P0 axis leak):
    # the SAME sibling SOURCE node belongs to TWO fan-in targets, and the human
    # vouched sibling_independence for it on ONE target only. The vouch is PER
    # fan-in target; absent vouch on the OTHER shared target => that sibling MUST
    # be re-verified (conservative). RE-VERIFY WINS: a sibling is skipped ONLY if
    # vouched-skip on EVERY shared target. A direct unit-level FIRE on
    # _fan_in_cohort_replay_plan with a two-target graph_context (the real walker
    # cannot express one node fanning into two joins via a single
    # completion_edge_ref, so the plan-level surface is exercised directly, same
    # as the operator P0 probe). Before the P0 fix, the SINGLE global seen_siblings
    # set carries the t1 vouch onto t2 and the sibling is skipped globally -> RED.
    from brick_protocol.support.operator.walker_fan_in import (
        _fan_in_cohort_replay_plan,
    )

    # X and sibling b are BOTH fan-in sources of t1 AND t2; vouch names b on t1
    # only. The reroute LANDS on X. Axis law: t2 has no vouch => b re-verified.
    cross_vouch_edges = [
        {"edge_ref": "xv-e1", "edge_role": "fan_in", "source_step_ref": "xv-X", "target_step_ref": "xv-t1"},
        {"edge_ref": "xv-e2", "edge_role": "fan_in", "source_step_ref": "xv-b", "target_step_ref": "xv-t1"},
        {"edge_ref": "xv-e3", "edge_role": "fan_in", "source_step_ref": "xv-X", "target_step_ref": "xv-t2"},
        {"edge_ref": "xv-e4", "edge_role": "fan_in", "source_step_ref": "xv-b", "target_step_ref": "xv-t2"},
    ]
    cross_vouch_step_ref_by_brick = {
        "brick-xv-X": "xv-X",
        "brick-xv-b": "xv-b",
        "brick-xv-t1": "xv-t1",
        "brick-xv-t2": "xv-t2",
    }

    def _run_cross_vouch(groups: list[Mapping[str, Any]]):
        gc = {"declared_edges": cross_vouch_edges, "groups": groups}
        return _fan_in_cohort_replay_plan(
            target_step_ref="xv-X",
            graph_context=gc,
            step_ref_by_brick=cross_vouch_step_ref_by_brick,
            already_scoped_step_refs=["xv-X"],
        )

    # Order 1: the VOUCHED target (t1) declared FIRST -> tests that the first
    # target's vouch does not poison the second target's (no-vouch) re-verify.
    xv_replay_1, xv_skipped_1, xv_records_1 = _run_cross_vouch(
        [
            {"group_role": "fan_in", "member_refs": ["xv-e1", "xv-e2"], "sibling_independence": ["xv-b"]},
            {"group_role": "fan_in", "member_refs": ["xv-e3", "xv-e4"], "sibling_independence": []},
        ]
    )
    # Order 2: the NO-VOUCH target (t2) declared FIRST -> symmetric guard.
    xv_replay_2, xv_skipped_2, xv_records_2 = _run_cross_vouch(
        [
            {"group_role": "fan_in", "member_refs": ["xv-e3", "xv-e4"], "sibling_independence": []},
            {"group_role": "fan_in", "member_refs": ["xv-e1", "xv-e2"], "sibling_independence": ["xv-b"]},
        ]
    )
    for label, xv_replay, xv_skipped, xv_records in (
        ("t1-vouched-first", xv_replay_1, xv_skipped_1, xv_records_1),
        ("t2-novouch-first", xv_replay_2, xv_skipped_2, xv_records_2),
    ):
        if "xv-b" not in xv_replay:
            violations.append(
                f"knot3-cohort-d ({label}): sibling shared by a NO-VOUCH fan-in target "
                f"was NOT re-verified (cross-vouch axis leak); replay={xv_replay}"
            )
        if "xv-b" in xv_skipped:
            violations.append(
                f"knot3-cohort-d ({label}): sibling was SKIPPED globally though a shared "
                f"target had no sibling_independence vouch; skipped={xv_skipped}"
            )
        # RE-VERIFY WINS: a sibling must never appear in BOTH lists.
        if set(xv_replay) & set(xv_skipped):
            violations.append(
                f"knot3-cohort-d ({label}): sibling appeared in BOTH replay and skip "
                f"lists; replay={xv_replay}, skipped={xv_skipped}"
            )
        # The final per-sibling disposition for b must be re_verified, and there
        # must be no 'skipped' disposition for b anywhere (truthful records).
        b_dispositions = {
            r.get("disposition")
            for r in xv_records
            if isinstance(r, Mapping) and r.get("sibling_source_step_ref") == "xv-b"
        }
        if "skipped" in b_dispositions:
            violations.append(
                f"knot3-cohort-d ({label}): a cohort record marks the cross-vouched "
                f"sibling as skipped (dispositions={sorted(d for d in b_dispositions if d)})"
            )
        if "re_verified" not in b_dispositions:
            violations.append(
                f"knot3-cohort-d ({label}): no re_verified record for the cross-vouched "
                f"sibling (dispositions={sorted(d for d in b_dispositions if d)})"
            )

    # KNOT-3 COHORT FIRE (e) REPLAY-SCOPE TRIGGER: the reroute may honestly land
    # on the work node that produced the concern, while the declared replay_scope
    # walks through the lane QA node that is the actual fan-in source. The cohort
    # reverify trigger must inspect that replay_scope chain, not only the landing.
    replay_scope_edges = [
        {
            "edge_ref": "rs-e1",
            "edge_role": "fan_in",
            "source_step_ref": "rs-docs-lane-qa",
            "target_step_ref": "rs-join",
        },
        {
            "edge_ref": "rs-e2",
            "edge_role": "fan_in",
            "source_step_ref": "rs-checker-lane-qa",
            "target_step_ref": "rs-join",
        },
    ]
    replay_scope_step_ref_by_brick = {
        "brick-rs-work-docs": "rs-work-docs",
        "brick-rs-docs-lane-qa": "rs-docs-lane-qa",
        "brick-rs-checker-lane-qa": "rs-checker-lane-qa",
        "brick-rs-join": "rs-join",
    }
    replay_scope_gc = {
        "declared_edges": replay_scope_edges,
        "groups": [
            {
                "group_role": "fan_in",
                "member_refs": ["rs-e1", "rs-e2"],
                "sibling_independence": [],
            }
        ],
    }
    rs_replay, rs_skipped, rs_records = _fan_in_cohort_replay_plan(
        target_step_ref="rs-work-docs",
        graph_context=replay_scope_gc,
        step_ref_by_brick=replay_scope_step_ref_by_brick,
        already_scoped_step_refs=["rs-work-docs", "rs-docs-lane-qa"],
    )
    if "rs-checker-lane-qa" not in rs_replay:
        violations.append(
            "knot3-cohort-e: reroute landing one hop above a fan-in source did "
            "not re-verify the unvouched sibling in the replay_scope cohort; "
            f"replay={rs_replay}, skipped={rs_skipped}, records={rs_records}"
        )
    if "rs-docs-lane-qa" in rs_replay:
        violations.append(
            "knot3-cohort-e: replay_scope trigger re-appended the already scoped "
            f"fan-in source; replay={rs_replay}"
        )
    if not any(
        isinstance(record, Mapping)
        and record.get("cohort_trigger_step_ref") == "rs-docs-lane-qa"
        and record.get("reroute_landing_step_ref") == "rs-work-docs"
        for record in rs_records
    ):
        violations.append(
            "knot3-cohort-e: cohort records do not distinguish the reroute landing "
            "from the replay_scope fan-in trigger"
        )

    replay_scope_vouched_gc = {
        "declared_edges": replay_scope_edges,
        "groups": [
            {
                "group_role": "fan_in",
                "member_refs": ["rs-e1", "rs-e2"],
                "sibling_independence": ["rs-checker-lane-qa"],
            }
        ],
    }
    rs_vouch_replay, rs_vouch_skipped, rs_vouch_records = _fan_in_cohort_replay_plan(
        target_step_ref="rs-work-docs",
        graph_context=replay_scope_vouched_gc,
        step_ref_by_brick=replay_scope_step_ref_by_brick,
        already_scoped_step_refs=["rs-work-docs", "rs-docs-lane-qa"],
    )
    if "rs-checker-lane-qa" in rs_vouch_replay:
        violations.append(
            "knot3-cohort-e-vouch: sibling_independence vouch did not skip the "
            f"replay_scope-triggered sibling; replay={rs_vouch_replay}"
        )
    if "rs-checker-lane-qa" not in rs_vouch_skipped:
        violations.append(
            "knot3-cohort-e-vouch: vouched sibling was not carried as skipped; "
            f"skipped={rs_vouch_skipped}, records={rs_vouch_records}"
        )

    # KNOT-3 COHORT FIRE (e) ALREADY-LIVE COHORT / BODY-CARRY RESUME (NOT the
    # silent-skip guard): a reroute that lands on a fan-in SOURCE runs the cohort
    # LIVE (lane-b re-verified, lane-c vouched-skipped, join re-run) and the SECOND
    # proposal then HOLDs on budget exhaustion; a HUMAN forward disposition RESUMES.
    # lane-a has budget 1; the join proposes a reroute onto lane-a (a fan-in source)
    # on EVERY call, so the FIRST landing adopts (budget consumed, cohort runs LIVE)
    # and the SECOND proposal HOLDs on exhaustion.
    #
    # WHAT cohort-e GENUINELY GUARDS (and goes RED for):
    #   - the FORWARD walk re-runs the ALREADY-LIVE cohort: lane-a + unvouched
    #     sibling lane-b + the shared fan-in target join each run >= 2, while the
    #     vouched sibling lane-c runs exactly once (skipped). The resume must
    #     reproduce this (it delegates to the forward walk, which rebuilds the cohort
    #     from the DECLARED graph topology) and carry the vouched-skipped sibling's
    #     PRIOR pass body forward, all BUDGET-FREE (no sibling consumes budget).
    #   - the FORWARD walk PERSISTS the cohort plan on the adoption record
    #     (cohort_replay_segment_refs / cohort_skipped_segment_refs) as evidence.
    #
    # WHAT cohort-e is NOT: it is NOT the silent-skip / HOLD-before-cohort guard.
    # The pending-cohort silent-skip corner (a cohort that exists ONLY in the
    # persisted adoption record because the LANDING HELD before the cohort ran live)
    # is guarded by cohort-f (direct shared join) and cohort-g (nested join). Those
    # are the load-bearing C silent-skip guards.
    #
    # PERSIST-vs-CONSUME NOTE: under the delegation-rewrite resume, the persisted
    # cohort_replay_segment_refs / cohort_skipped_segment_refs are NOT read back by
    # the resume path -- the forward walk rebuilds the cohort from the declared graph
    # topology. So the persisted-fields assertion below is a FORWARD-WALK evidence
    # check (the SAME persist cohort-f also pins), NOT proof that resume reconstructs
    # FROM those fields. Do not claim it as the silent-skip guard.
    plan_cohort_e = _cohort_fan_plan(
        "bapr-loop0-knot3-cohort-e",
        sibling_independence=["bapr-loop0-knot3-cohort-e-lane-c"],
    )
    lane_a_e = "brick-bapr-loop0-knot3-cohort-e-lane-a"
    lane_b_e = "brick-bapr-loop0-knot3-cohort-e-lane-b"
    lane_c_e = "brick-bapr-loop0-knot3-cohort-e-lane-c"
    join_e = "brick-bapr-loop0-knot3-cohort-e-join"
    with checker_temp_path("bp-bapr-knot3-cohort-e-") as tmp_e:
        # join proposes a reroute onto lane-a on every call: the FIRST landing
        # adopts (budget 1 consumed) and triggers the cohort LIVE (lane-b
        # re-verified, lane-c vouched-skipped, join re-runs); the SECOND proposal
        # HOLDs on budget exhaustion. A HUMAN forward disposition then resumes.
        callable_e = _reroute_callable(lane_a_e, {join_e})
        res_e = run_building_plan(
            plan_cohort_e,
            output_root=tmp_e,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_e},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_e = res_e.lifecycle_write.root
        before_e = observe_building_frontier(root_e, repo_root=repo)
        if before_e["frontier_kind"] != "link_paused":
            violations.append(
                "knot3-cohort-e: cohort reroute-on-fan-in-source did not HOLD before "
                f"resume (frontier={before_e['frontier_kind']})"
            )
        # FORWARD-WALK EVIDENCE (not a resume-rebuild claim): the cohort-triggering
        # landing's adoption record records its cohort plan
        # (cohort_replay_segment_refs / cohort_skipped_segment_refs) as FACTS. This
        # is a forward-walk persist check -- the SAME persist cohort-f also pins. It
        # does NOT prove resume rebuilds FROM these fields (the delegation resume
        # rebuilds the cohort from the declared graph topology and does NOT read them
        # back). The genuine resume reconstruction is asserted below (already-live
        # cohort re-walk + body-carry); the silent-skip corner is cohort-f/g.
        adoption_recs_e = [
            r
            for r in (
                getattr(res_e, "_dynamic_walker_evidence", {}).get(
                    "reroute_adoption_records", []
                )
                if isinstance(getattr(res_e, "_dynamic_walker_evidence", {}), Mapping)
                else []
            )
            if isinstance(r, Mapping) and not r.get("disposition_required")
        ]
        if not any(
            "bapr-loop0-knot3-cohort-e-lane-b"
            in (r.get("cohort_replay_segment_refs") or [])
            and "bapr-loop0-knot3-cohort-e-lane-c"
            in (r.get("cohort_skipped_segment_refs") or [])
            for r in adoption_recs_e
        ):
            violations.append(
                "knot3-cohort-e: the cohort-triggering adoption record did not record "
                "its cohort plan (cohort_replay_segment_refs/cohort_skipped_segment_refs) "
                f"as forward-walk evidence (records={adoption_recs_e})"
            )
        # Resume via a HUMAN forward disposition (does NOT add a landing -> stays
        # budget-free; isolates the reconstruction of the PRIOR landing's cohort).
        _append_disposition_row(
            root_e,
            building_id=res_e.building_id,
            pending_target_ref=lane_a_e,
            action="forward",
            author_ref="coo:smith",
        )
        try:
            resumed_e = resume_building_plan(
                root_e,
                local_callables={"callable:local:agent-invoke0-smoke": callable_e},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
            violations.append(f"knot3-cohort-e: cohort resume crashed: {exc}")
        else:
            after_e = observe_building_frontier(resumed_e.lifecycle_write.root, repo_root=repo)
            bricks_e = _step_bricks(resumed_e)
            evidence_e = getattr(resumed_e, "_dynamic_walker_evidence", {})
            if not isinstance(evidence_e, Mapping):
                evidence_e = {}
            landings_e = evidence_e.get("node_reroute_landings", {})
            # GENUINE GUARD (already-live cohort re-walk): the prior landing's cohort
            # -- which ran LIVE before the HOLD -- must be re-walked on resume (the
            # delegation resume rebuilds it from the declared graph topology). The
            # reroute-depth re-verification re-walks lane-a (landing) + lane-b
            # (unvouched sibling) + the shared fan-in target join, while the vouched
            # lane-c is skipped (runs exactly once at depth 0). A resume that DROPS
            # the already-live cohort fails these counts -> RED.
            if bricks_e.count(lane_a_e) < 2:
                violations.append(
                    "knot3-cohort-e (P1b): resume DROPPED the cohort -- landing lane-a "
                    f"was not re-walked (count={bricks_e.count(lane_a_e)})"
                )
            if bricks_e.count(lane_b_e) < 2:
                violations.append(
                    "knot3-cohort-e (P1b): resume DROPPED the cohort -- unvouched sibling "
                    f"lane-b was not re-verified (count={bricks_e.count(lane_b_e)})"
                )
            if bricks_e.count(join_e) < 2:
                violations.append(
                    "knot3-cohort-e (P1b): resume DROPPED the cohort -- the shared fan-in "
                    f"target join was not re-run (count={bricks_e.count(join_e)})"
                )
            if bricks_e.count(lane_c_e) != 1:
                violations.append(
                    "knot3-cohort-e: vouched sibling lane-c was re-walked on resume "
                    f"(count={bricks_e.count(lane_c_e)}; expected 1 = skipped)"
                )
            # The resume must reach a clean terminal frontier (cohort reconstructed
            # AND walked on past the forwarded gate).
            if after_e["frontier_kind"] not in {"complete", "closure_pending"}:
                violations.append(
                    "knot3-cohort-e (P1b): cohort resume did not walk on "
                    f"(frontier={after_e['frontier_kind']})"
                )
            if bricks_e[-1] != "brick-bapr-loop0-knot3-cohort-e-close":
                violations.append(
                    "knot3-cohort-e (P1b): resume did not reach the close node last "
                    f"(last={bricks_e[-1]})"
                )
            # BUDGET-FREE: the forward disposition adds NO landing; only the single
            # original cohort-triggering landing consumed budget (lane-a == 1), and
            # no cohort sibling ever consumed budget.
            if landings_e.get(lane_a_e) != 1:
                violations.append(
                    "knot3-cohort-e: forward-resumed cohort changed the landing count "
                    f"(node_landings={landings_e}; expected lane-a == 1)"
                )
            if landings_e.get(lane_b_e, 0) != 0 or landings_e.get(lane_c_e, 0) != 0:
                violations.append(
                    "knot3-cohort-e: a cohort sibling consumed reroute budget on resume "
                    f"(must be budget-free; node_landings={landings_e})"
                )

    # KNOT-3 COHORT FIRE (f) HOLD-BEFORE-COHORT (catches FIX C silent-skip): a
    # reroute is ADOPTED onto a fan-in SOURCE (cohort spliced: re-verify sibling +
    # re-run shared join), but the LANDING itself HOLDs on budget exhaustion BEFORE
    # the cohort/join run -- so the cohort NEVER ran live and exists ONLY in the
    # persisted adoption record's cohort_*_segment_refs. On resume the pending
    # cohort + its shared fan-in target must be rebuilt from the declared-plan
    # birth-certificate fan topology (graph_context is the linearized-snapshot None).
    # Unlike cohort-e (which resumes AFTER the cohort already ran live), here the
    # cohort is rebuilt PURELY by the resume reconstruction.
    #
    # ACCEPT EITHER outcome, never a silent skip:
    #   (a) FULL C: resume re-verifies the cohort + RE-RUNS the shared join +
    #       completes (join re-run >= 2, unvouched sibling re-verified >= 2, vouched
    #       sibling skipped == 1).
    #   (b) SAFE FLOOR: resume HOLDs with hold_reason
    #       cohort_resume_reconstruction_incomplete (Priority 1).
    # VIOLATION (the silent skip FIX C kills): the building COMPLETES but the shared
    # fan-in join was NOT re-run over the re-verified cohort (join count < 2) -- the
    # cohort was silently dropped and a stale join carried to close.
    #
    # SELF-FIRE PROOF: disabling the FIX C floor+reconstruct (so resume walks past
    # the pending cohort) turns THIS case RED with the "silently skipped pending
    # cohort" violation below; restoring it returns to green.
    plan_cohort_f = _cohort_fan_plan(
        "bapr-loop0-knot3-cohort-f",
        sibling_independence=["bapr-loop0-knot3-cohort-f-lane-c"],
    )
    lane_a_f = "brick-bapr-loop0-knot3-cohort-f-lane-a"
    lane_b_f = "brick-bapr-loop0-knot3-cohort-f-lane-b"
    lane_c_f = "brick-bapr-loop0-knot3-cohort-f-lane-c"
    join_f = "brick-bapr-loop0-knot3-cohort-f-join"
    close_f = "brick-bapr-loop0-knot3-cohort-f-close"

    def _hold_before_cohort_callable():
        """join proposes reroute->lane-a on its 1st call (cohort spliced); lane-a
        (the re-walk landing) proposes reroute->lane-b on its 2nd call. lane-b has
        no Link-assigned reroute budget in this fixture, so the landing HOLDs
        BEFORE the cohort runs without relying on self-reroute. The re-run join on
        resume (its 2nd call) is CLEAN so the building can complete."""

        seen: dict[str, int] = {}

        def _callable(request: Any) -> Mapping[str, Any]:
            seen[request.brick_instance_ref] = seen.get(request.brick_instance_ref, 0) + 1
            returned: dict[str, Any] = {
                "observed_evidence": [f"obs {request.brick_instance_ref}"],
                "not_proven": ["semantic correctness"],
            }
            propose = (
                (request.brick_instance_ref == join_f and seen[join_f] == 1)
                or (request.brick_instance_ref == lane_a_f and seen[lane_a_f] >= 2)
            )
            if propose:
                target_ref = lane_a_f if request.brick_instance_ref == join_f else lane_b_f
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                    "related_boundary_refs": [target_ref],
                }
            return returned

        return _callable

    with checker_temp_path("bp-bapr-knot3-cohort-f-") as tmp_f:
        callable_f = _hold_before_cohort_callable()
        res_f = run_building_plan(
            plan_cohort_f,
            output_root=tmp_f,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_f},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_f = res_f.lifecycle_write.root
        before_f = observe_building_frontier(root_f, repo_root=repo)
        bricks_run_f = _step_bricks(res_f)
        evidence_run_f = getattr(res_f, "_dynamic_walker_evidence", {})
        if not isinstance(evidence_run_f, Mapping):
            evidence_run_f = {}
        if before_f["frontier_kind"] != "link_paused":
            violations.append(
                "knot3-cohort-f: HOLD-before-cohort run did not HOLD at the landing "
                f"(frontier={before_f['frontier_kind']})"
            )
        # The HOLD must be on the LANDING (lane-a), and the cohort must NOT have run
        # live (join ran exactly once at depth 0). This is the corner: the cohort
        # exists only in the persisted adoption record, not in the recorded steps.
        if bricks_run_f.count(join_f) != 1:
            violations.append(
                "knot3-cohort-f: setup invalid -- the cohort ran live before the HOLD "
                f"(join count={bricks_run_f.count(join_f)}, expected 1)"
            )
        adoption_recs_f = [
            r
            for r in evidence_run_f.get("reroute_adoption_records", [])
            if isinstance(r, Mapping) and not r.get("disposition_required")
        ]
        if not any(
            "bapr-loop0-knot3-cohort-f-lane-b"
            in (r.get("cohort_replay_segment_refs") or [])
            and "bapr-loop0-knot3-cohort-f-lane-c"
            in (r.get("cohort_skipped_segment_refs") or [])
            for r in adoption_recs_f
        ):
            violations.append(
                "knot3-cohort-f: the cohort-triggering adoption record did not persist "
                f"the pending cohort plan (records={adoption_recs_f})"
            )
        # Resume via a HUMAN forward disposition (budget-free; isolates the pending
        # cohort reconstruction).
        hold_pending_f = (
            evidence_run_f.get("hold", {}).get("pending_target_ref")
            if isinstance(evidence_run_f.get("hold"), Mapping)
            else None
        ) or lane_a_f
        _append_disposition_row(
            root_f,
            building_id=res_f.building_id,
            pending_target_ref=hold_pending_f,
            action="forward",
            author_ref="coo:smith",
        )
        try:
            resumed_f = resume_building_plan(
                root_f,
                local_callables={"callable:local:agent-invoke0-smoke": callable_f},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
            violations.append(f"knot3-cohort-f: HOLD-before-cohort resume crashed: {exc}")
        else:
            after_f = observe_building_frontier(resumed_f.lifecycle_write.root, repo_root=repo)
            bricks_f = _step_bricks(resumed_f)
            evidence_f = getattr(resumed_f, "_dynamic_walker_evidence", {})
            if not isinstance(evidence_f, Mapping):
                evidence_f = {}
            hold_reason_f = (
                evidence_f.get("hold", {}).get("hold_reason")
                if isinstance(evidence_f.get("hold"), Mapping)
                else None
            )
            join_reran_f = bricks_f.count(join_f) >= 2
            outcome_full_c = (
                after_f["frontier_kind"] in {"complete", "closure_pending"}
                and join_reran_f
                and bricks_f.count(lane_b_f) >= 2
                and bricks_f.count(lane_c_f) == 1
            )
            outcome_safe_floor = (
                after_f["frontier_kind"] == "link_paused"
                and hold_reason_f == "cohort_resume_reconstruction_incomplete"
            )
            # THE FIX-C GUARD: the building must NEVER complete while the shared
            # fan-in join was silently skipped (not re-run over the re-verified
            # cohort). This is the exact silent-skip FIX C removes; removing the
            # floor/reconstruct turns THIS into a violation (self-FIRE proof).
            if after_f["frontier_kind"] in {"complete", "closure_pending"} and not join_reran_f:
                violations.append(
                    "knot3-cohort-f (FIX C): resume SILENTLY SKIPPED the pending cohort "
                    "-- the building completed but the shared fan-in join was NOT re-run "
                    f"over the re-verified cohort (join count={bricks_f.count(join_f)}, "
                    f"frontier={after_f['frontier_kind']}, bricks={bricks_f})"
                )
            elif not (outcome_full_c or outcome_safe_floor):
                violations.append(
                    "knot3-cohort-f: HOLD-before-cohort resume reached neither the full "
                    "reconstruct completion NOR the safe-floor HOLD "
                    f"(frontier={after_f['frontier_kind']}, hold_reason={hold_reason_f}, "
                    f"join count={bricks_f.count(join_f)}, lane-b count={bricks_f.count(lane_b_f)}, "
                    f"lane-c count={bricks_f.count(lane_c_f)})"
                )
            # If the FULL reconstruct path was taken, the vouched sibling must NOT be
            # re-walked (lane-c skipped == 1) and the close must be reached last.
            if outcome_full_c:
                if bricks_f.count(lane_c_f) != 1:
                    violations.append(
                        "knot3-cohort-f: full reconstruct re-walked the vouched sibling "
                        f"lane-c (count={bricks_f.count(lane_c_f)}; expected 1 = skipped)"
                    )
                if bricks_f[-1] != close_f:
                    violations.append(
                        "knot3-cohort-f: full reconstruct did not reach the close node last "
                        f"(last={bricks_f[-1]})"
                    )
                landings_f = evidence_f.get("node_reroute_landings", {})
                if landings_f.get(lane_b_f, 0) != 0 or landings_f.get(lane_c_f, 0) != 0:
                    violations.append(
                        "knot3-cohort-f: a cohort sibling consumed reroute budget on resume "
                        f"(must be budget-free; node_landings={landings_f})"
                    )

    # KNOT-3 COHORT FIRE (g) NESTED FAN-IN HOLD-BEFORE-COHORT (catches FIX #2
    # nested silent-skip): a reroute is ADOPTED onto lane-a, an INNER fan-in source
    # whose direct join j1 is ITSELF a fan-in SOURCE feeding a downstream nested
    # join j2 (lane-a -> j1, j1 -> j2). The LANDING HOLDs on budget exhaustion
    # BEFORE the cohort/joins run, so the inner cohort + j1 + j2 exist only in the
    # persisted adoption record. On resume the reconstruction re-appends only the
    # DIRECT join j1; the live fan-out splice that would re-run the NESTED successor
    # j2 is gated on the linearized-snapshot graph_context (None), so without the
    # FIX #2 floor j2 is SILENTLY SKIPPED (the building completes carrying a STALE
    # j2 that never saw the re-verified cohort).
    #
    # ACCEPT EITHER outcome, never a silent skip:
    #   (a) FULL reconstruct: resume re-runs the cohort + BOTH j1 AND j2 + completes
    #       (j1 count >= 2 AND j2 count >= 2).
    #   (b) SAFE FLOOR (the shipped FIX #2 conservative answer): resume HOLDs with
    #       hold_reason cohort_resume_reconstruction_incomplete (Priority 1).
    # VIOLATION (the silent skip FIX #2 kills): the building COMPLETES but the
    # NESTED join j2 was NOT re-run over the re-verified cohort (j2 count < 2).
    #
    # SELF-FIRE PROOF: disabling the FIX #2 nested floor (so resume walks past the
    # nested successor) turns THIS case RED with the "nested join silently skipped"
    # violation; restoring it returns to green.
    plan_nested_g = _nested_fan_plan(
        "bapr-loop0-knot3-cohort-g",
        sibling_independence=["bapr-loop0-knot3-cohort-g-lane-b"],
    )
    lane_a_g = "brick-bapr-loop0-knot3-cohort-g-lane-a"
    lane_b_g = "brick-bapr-loop0-knot3-cohort-g-lane-b"
    j1_g = "brick-bapr-loop0-knot3-cohort-g-j1"
    j2_g = "brick-bapr-loop0-knot3-cohort-g-j2"
    close_g = "brick-bapr-loop0-knot3-cohort-g-close"

    def _nested_hold_before_cohort_callable():
        """j1 proposes reroute -> lane-a on its 1st call (inner cohort spliced);
        lane-a (the re-walk landing) proposes reroute -> lane-b on its 2nd call.
        lane-b has no Link-assigned reroute budget in this fixture, so the landing
        HOLDs BEFORE the cohort + joins run without relying on self-reroute."""

        seen: dict[str, int] = {}

        def _callable(request: Any) -> Mapping[str, Any]:
            seen[request.brick_instance_ref] = seen.get(request.brick_instance_ref, 0) + 1
            returned: dict[str, Any] = {
                "observed_evidence": [f"obs {request.brick_instance_ref}"],
                "not_proven": ["semantic correctness"],
            }
            propose = (
                (request.brick_instance_ref == j1_g and seen[j1_g] == 1)
                or (request.brick_instance_ref == lane_a_g and seen[lane_a_g] >= 2)
            )
            if propose:
                target_ref = lane_a_g if request.brick_instance_ref == j1_g else lane_b_g
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                    "related_boundary_refs": [target_ref],
                }
            return returned

        return _callable

    with checker_temp_path("bp-bapr-knot3-cohort-g-") as tmp_g:
        callable_g = _nested_hold_before_cohort_callable()
        res_g = run_building_plan(
            plan_nested_g,
            output_root=tmp_g,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_g},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_g = res_g.lifecycle_write.root
        before_g = observe_building_frontier(root_g, repo_root=repo)
        bricks_run_g = _step_bricks(res_g)
        evidence_run_g = getattr(res_g, "_dynamic_walker_evidence", {})
        if not isinstance(evidence_run_g, Mapping):
            evidence_run_g = {}
        if before_g["frontier_kind"] != "link_paused":
            violations.append(
                "knot3-cohort-g: nested HOLD-before-cohort run did not HOLD at the landing "
                f"(frontier={before_g['frontier_kind']})"
            )
        # The cohort must NOT have run live: j1 ran exactly once (it triggered the
        # reroute) and j2 ran ZERO times (the HOLD precedes the inner cohort/joins).
        if bricks_run_g.count(j1_g) != 1:
            violations.append(
                "knot3-cohort-g: setup invalid -- inner join j1 did not run exactly once "
                f"before the HOLD (j1 count={bricks_run_g.count(j1_g)})"
            )
        if bricks_run_g.count(j2_g) != 0:
            violations.append(
                "knot3-cohort-g: setup invalid -- nested join j2 ran before the HOLD "
                f"(j2 count={bricks_run_g.count(j2_g)})"
            )
        hold_pending_g = (
            evidence_run_g.get("hold", {}).get("pending_target_ref")
            if isinstance(evidence_run_g.get("hold"), Mapping)
            else None
        ) or lane_a_g
        _append_disposition_row(
            root_g,
            building_id=res_g.building_id,
            pending_target_ref=hold_pending_g,
            action="forward",
            author_ref="coo:smith",
        )
        try:
            resumed_g = resume_building_plan(
                root_g,
                local_callables={"callable:local:agent-invoke0-smoke": callable_g},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except Exception as exc:  # noqa: BLE001 - surface resume crash as a violation
            violations.append(f"knot3-cohort-g: nested HOLD-before-cohort resume crashed: {exc}")
        else:
            after_g = observe_building_frontier(resumed_g.lifecycle_write.root, repo_root=repo)
            bricks_g = _step_bricks(resumed_g)
            evidence_g = getattr(resumed_g, "_dynamic_walker_evidence", {})
            if not isinstance(evidence_g, Mapping):
                evidence_g = {}
            hold_reason_g = (
                evidence_g.get("hold", {}).get("hold_reason")
                if isinstance(evidence_g.get("hold"), Mapping)
                else None
            )
            j1_reran_g = bricks_g.count(j1_g) >= 2
            j2_reran_g = bricks_g.count(j2_g) >= 2
            outcome_full = (
                after_g["frontier_kind"] in {"complete", "closure_pending"}
                and j1_reran_g
                and j2_reran_g
            )
            # SAFE-FLOOR HOLD: resume HOLDs for a human rather than completing with a
            # skipped nested join. Two faithful HOLD reasons are accepted:
            #   - fan_in_wait_all_missing_source: the FORWARD-WALK-NATIVE HOLD. Resume
            #     now DELEGATES to the forward walk (resume rehydrates forward state +
            #     replays recorded returns, then continues the SAME forward loop). The
            #     forward walk re-verifies lane-a's DIRECT cohort + re-runs the direct
            #     join j1 at the cohort depth, then schedules the nested join j2 -- but
            #     j2's OTHER source (other2) only ran at depth 0, so j2's fan-in wait-all
            #     is missing a source at the cohort depth and the forward walk HOLDs. A
            #     fresh never-paused run with this topology HOLDs IDENTICALLY (verified):
            #     this is the forward engine's own answer, not a silent skip -- j2 never
            #     runs over a stale cohort; a human dispositions it. STRICTLY MORE
            #     FAITHFUL than the legacy resume-specific synthetic floor below.
            #   - cohort_resume_reconstruction_incomplete: the legacy resume-engine
            #     synthetic floor reason (kept so the case stays green if the engine
            #     ever re-introduces a bespoke nested floor).
            outcome_floor = after_g["frontier_kind"] == "link_paused" and hold_reason_g in {
                "fan_in_wait_all_missing_source",
                "cohort_resume_reconstruction_incomplete",
            }
            # THE FIX #2 GUARD: the building must NEVER complete while the NESTED
            # successor join j2 was silently skipped (not re-run over the re-verified
            # cohort). Breaking the delegation (so resume walks past the pending nested
            # cohort to close without re-running j2) turns THIS into a violation.
            if after_g["frontier_kind"] in {"complete", "closure_pending"} and not j2_reran_g:
                violations.append(
                    "knot3-cohort-g (FIX #2): resume SILENTLY SKIPPED the NESTED join -- the "
                    "building completed but the downstream nested join j2 was NOT re-run over "
                    f"the re-verified cohort (j2 count={bricks_g.count(j2_g)}, "
                    f"j1 count={bricks_g.count(j1_g)}, frontier={after_g['frontier_kind']}, "
                    f"bricks={bricks_g})"
                )
            elif not (outcome_full or outcome_floor):
                violations.append(
                    "knot3-cohort-g: nested HOLD-before-cohort resume reached neither the full "
                    "reconstruct completion NOR the safe-floor HOLD "
                    f"(frontier={after_g['frontier_kind']}, hold_reason={hold_reason_g}, "
                    f"j1 count={bricks_g.count(j1_g)}, j2 count={bricks_g.count(j2_g)})"
                )
            if outcome_floor:
                # The floor HOLD must require a human/COO disposition (caller-or-coo).
                owner_g = (
                    evidence_g.get("hold", {}).get("required_disposition_owner")
                    if isinstance(evidence_g.get("hold"), Mapping)
                    else None
                )
                if owner_g != "caller-or-coo":
                    violations.append(
                        "knot3-cohort-g (FIX #2): nested floor HOLD did not require caller-or-coo "
                        f"disposition (owner={owner_g})"
                    )

    # ============================================================================
    # RESUME FAIL-CLOSED GUARDS (gaps 1-6): the graph-driven resume rewrite ("C")
    # delegates to the forward walker over recorded evidence. For COHERENT evidence
    # it is faithful, but degenerate (MISSING/MALFORMED) evidence must FAIL CLOSED
    # ("확신 없으면 멈춰라"), never silently proceed. Each case injects degenerate
    # evidence into a written held Building and asserts resume raises/HOLDs rather
    # than silently re-running live / completing / stamping the wrong occurrence.
    # SELF-FIRE: reverting the corresponding guard in walker_kernel.py /
    # walker_resume.py turns each case RED.
    # ============================================================================
    from brick_protocol.support.operator.run import run_building_plan, resume_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.walker_resume import (
        _read_written_dynamic_plan,
        _resume_observations,
    )

    def _build_held_fc(prefix: str, tmp: str, callable_, *, budget: int = 1):
        plan_fc, b2_fc = _checker_plan(prefix, budget=budget)
        res_fc = run_building_plan(
            plan_fc, output_root=Path(tmp), overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_},
            adapter_cwd=repo, adapter_timeout_seconds=30,
        )
        return res_fc, b2_fc

    def _read_evidence_plan(root_fc: Path):
        mp = root_fc / "evidence" / "evidence-manifest.json"
        manifest_fc = json.loads(mp.read_text(encoding="utf-8"))
        plan_fc = json.loads(manifest_fc["plan_snapshot"]["plan_rows_copy"])
        return mp, manifest_fc, plan_fc

    def _write_evidence_plan(mp: Path, manifest_fc, plan_fc):
        manifest_fc["plan_snapshot"]["plan_rows_copy"] = json.dumps(plan_fc)
        mp.write_text(json.dumps(manifest_fc), encoding="utf-8")

    # GAP 1: a MISSING pre-HOLD recorded return must FAIL CLOSED, not run live.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap1-") as tmp:
        pfx = "bapr-loop0-fc-gap1"
        cb = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res1, b2_1 = _build_held_fc(pfx, tmp, cb, budget=1)
        root1 = res1.lifecycle_write.root
        if observe_building_frontier(root1, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap1: setup did not HOLD")
        # Drop the pre-HOLD recorded return for `design` (its step-output dir stays).
        ar = root1 / "raw" / "agent-return.jsonl"
        lines = [l for l in ar.read_text(encoding="utf-8").splitlines() if l.strip()]
        kept = [l for l in lines if json.loads(l).get("step_ref") != f"{pfx}-design"]
        if len(kept) != len(lines) - 1:
            violations.append("fc-gap1: setup could not drop exactly one design return")
        ar.write_text("\n".join(kept) + "\n", encoding="utf-8")
        _append_disposition_row(root1, building_id=res1.building_id,
                                pending_target_ref=b2_1, action="forward", author_ref="coo:smith")
        live_calls_1 = []
        def _sentinel1(request):
            live_calls_1.append(request.brick_instance_ref)
            return {"observed_evidence": [f"obs {request.brick_instance_ref}"], "not_proven": ["x"]}
        try:
            resume_building_plan(root1, local_callables={"callable:local:agent-invoke0-smoke": _sentinel1},
                                 adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError:
            pass
        else:
            violations.append("fc-gap1: a missing pre-HOLD recorded return did not fail closed (no raise)")
        if f"brick-{pfx}-design" in live_calls_1:
            violations.append("fc-gap1: a pre-HOLD step was RUN LIVE on resume (silent-proceed on corrupt evidence)")

    # GAP 1b (B1): a MALFORMED / NON-OBJECT / HOLEY pre-HOLD step-output.json must
    # FAIL CLOSED, not silently lower the completed-step frontier and re-run the
    # pre-HOLD step LIVE. CURRENT (pre-fix) behaviour: _completed_step_frontier and
    # _step_output_field_matches SKIP a malformed / non-object step-output, lowering
    # the frontier; combined with a dropped raw return the kernel treats a COMPLETED
    # step as a continued step and re-calls the provider -- hiding corrupt evidence.
    # SELF-FIRE: reverting the fail-closed raises in walker_resume.py turns the
    # malformed / non-object sub-cases RED (no raise + design ran live). The holey
    # sub-case is already guarded by the attempt_index check; it is kept so the case
    # covers the full corruption surface the review named.
    def _corrupt_design_step_output(rt: Path, step_pfx: str, corruption: str) -> bool:
        for p1b in (rt / "work" / "step-outputs").glob("*/step-output.json"):
            v1b = json.loads(p1b.read_text(encoding="utf-8"))
            if v1b.get("step_ref") != f"{step_pfx}-design":
                continue
            if corruption == "malformed":
                p1b.write_text("{not valid json", encoding="utf-8")
            elif corruption == "nonobject":
                p1b.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            elif corruption == "holey":
                v1b.pop("attempt_index", None)
                p1b.write_text(json.dumps(v1b), encoding="utf-8")
            else:  # pragma: no cover - guarded by the loop below
                raise AssertionError(corruption)
            return True
        return False

    for corruption_1b in ("malformed", "nonobject", "holey"):
        with tempfile.TemporaryDirectory(prefix=f"bp-bapr-fc-gap1b-{corruption_1b}-") as tmp:
            pfx = f"bapr-loop0-fc-gap1b-{corruption_1b}"
            cb = _reroute_callable(
                f"brick-{pfx}-build",
                {f"brick-{pfx}-design", f"brick-{pfx}-review"},
            )
            res1b, b2_1b = _build_held_fc(pfx, tmp, cb, budget=1)
            root1b = res1b.lifecycle_write.root
            if observe_building_frontier(root1b, repo_root=repo)["frontier_kind"] != "link_paused":
                violations.append(f"fc-gap1b-{corruption_1b}: setup did not HOLD")
            # Drop the pre-HOLD `design` raw return so a lowered frontier => live re-run.
            ar1b = root1b / "raw" / "agent-return.jsonl"
            lines1b = [l for l in ar1b.read_text(encoding="utf-8").splitlines() if l.strip()]
            kept1b = [l for l in lines1b if json.loads(l).get("step_ref") != f"{pfx}-design"]
            ar1b.write_text("\n".join(kept1b) + "\n", encoding="utf-8")
            if not _corrupt_design_step_output(root1b, pfx, corruption_1b):
                violations.append(f"fc-gap1b-{corruption_1b}: setup could not find design step-output")
            _append_disposition_row(root1b, building_id=res1b.building_id,
                                    pending_target_ref=b2_1b, action="forward", author_ref="coo:smith")
            live_calls_1b = []
            def _sentinel1b(request):
                live_calls_1b.append(request.brick_instance_ref)
                return {"observed_evidence": [f"obs {request.brick_instance_ref}"], "not_proven": ["x"]}
            try:
                resume_building_plan(root1b, local_callables={"callable:local:agent-invoke0-smoke": _sentinel1b},
                                     adapter_cwd=repo, adapter_timeout_seconds=30)
            except ValueError:
                pass
            else:
                violations.append(
                    f"fc-gap1b-{corruption_1b}: a {corruption_1b} pre-HOLD step-output did not "
                    "fail closed (silent-proceed on corrupt evidence)")
            if f"brick-{pfx}-design" in live_calls_1b:
                violations.append(
                    f"fc-gap1b-{corruption_1b}: a pre-HOLD step was RUN LIVE on resume "
                    "(corrupt step-output lowered the frontier into a live re-run)")

    # GAP 2: a resume whose disposition was NEVER APPLIED must FAIL CLOSED.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap2-") as tmp:
        pfx = "bapr-loop0-fc-gap2"
        cb = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res2, b2_2 = _build_held_fc(pfx, tmp, cb, budget=1)
        root2 = res2.lifecycle_write.root
        mp2, man2, plan2 = _read_evidence_plan(root2)
        plan2["dynamic_walker_evidence"]["hold"]["source_step_ref"] = f"{pfx}-NONEXISTENT"
        _write_evidence_plan(mp2, man2, plan2)
        _append_disposition_row(root2, building_id=res2.building_id,
                                pending_target_ref=b2_2, action="forward", author_ref="coo:smith")
        try:
            resumed2 = resume_building_plan(root2, local_callables={"callable:local:agent-invoke0-smoke": cb},
                                            adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError:
            pass
        else:
            fr2 = observe_building_frontier(resumed2.lifecycle_write.root, repo_root=repo)
            violations.append(
                "fc-gap2: a resume that never applied its disposition (held occurrence "
                f"unreachable) did not fail closed (frontier={fr2['frontier_kind']})"
            )

    # GAP 3: the resumed lifecycle must stamp the EXACT held occurrence. The
    # setup uses non-self reroute proposals (design/review -> build); self-reroute
    # is a walk-on concern under CLOSURE-SELFREROUTE-GUARD-0616.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap3-") as tmp:
        pfx = "bapr-loop0-fc-gap3"
        b2_3 = f"brick-{pfx}-build"
        held_step_ref_3 = f"{pfx}-review"
        setup3 = _reroute_callable(
            b2_3,
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        def _live3(request):
            return {"observed_evidence": [f"o {request.brick_instance_ref}"], "not_proven": ["x"]}
        res3, _ = _build_held_fc(pfx, tmp, setup3, budget=1)
        root3 = res3.lifecycle_write.root
        if observe_building_frontier(root3, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap3: setup did not HOLD")
        _append_disposition_row(root3, building_id=res3.building_id, pending_target_ref=b2_3,
                                action="raise", author_ref="coo:smith", budget_increment=1)
        resumed3 = resume_building_plan(root3, local_callables={"callable:local:agent-invoke0-smoke": _live3},
                                        adapter_cwd=repo, adapter_timeout_seconds=30)
        if observe_building_frontier(resumed3.lifecycle_write.root, repo_root=repo)["frontier_kind"] != "complete":
            violations.append("fc-gap3: raise re-adoption did not complete (setup invalid)")
        occ3 = []
        for idx3, sr3 in enumerate(resumed3.step_results):
            if sr3.preparation.step_rows.step_ref != held_step_ref_3:
                continue
            lr3 = sr3.preparation.step_rows.link_row
            tl3 = lr3.get("transition_lifecycle") if isinstance(lr3, Mapping) else None
            occ3.append((idx3, tl3.get("state") if isinstance(tl3, Mapping) else None))
        resumed_idx3 = [i for i, s in occ3 if s == "resumed"]
        if len(occ3) != 1:
            violations.append(f"fc-gap3: expected exactly one held review occurrence (got {occ3})")
        elif not resumed_idx3:
            violations.append(f"fc-gap3: no resumed-lifecycle stamp found ({occ3})")
        else:
            held_idx3 = occ3[0][0]
            if resumed_idx3[0] != held_idx3:
                violations.append(f"fc-gap3: resumed stamp on wrong occurrence (stamped {resumed_idx3}, held {held_idx3})")

    # GAP 4: a missing OR malformed re-attached budget map must FAIL CLOSED (the
    # building engaged the reroute budget mechanism).
    for gap4_mode in ("missing", "malformed"):
        with tempfile.TemporaryDirectory(prefix=f"bp-bapr-fc-gap4-{gap4_mode}-") as tmp:
            pfx = f"bapr-loop0-fc-gap4-{gap4_mode}"
            cb = _reroute_callable(
                f"brick-{pfx}-build",
                {f"brick-{pfx}-design", f"brick-{pfx}-review"},
            )
            res4, b2_4 = _build_held_fc(pfx, tmp, cb, budget=1)
            root4 = res4.lifecycle_write.root
            mp4, man4, plan4 = _read_evidence_plan(root4)
            ev4 = plan4["dynamic_walker_evidence"]
            if gap4_mode == "missing":
                ev4.pop("node_reroute_budgets", None)
            else:
                ev4["node_reroute_budgets"] = "not-a-mapping"
            _write_evidence_plan(mp4, man4, plan4)
            _append_disposition_row(root4, building_id=res4.building_id,
                                    pending_target_ref=b2_4, action="forward", author_ref="coo:smith")
            try:
                resume_building_plan(root4, local_callables={"callable:local:agent-invoke0-smoke": cb},
                                     adapter_cwd=repo, adapter_timeout_seconds=30)
            except ValueError as exc4:
                # The raise must be the SPECIFIC budget guard (not a downstream
                # divergence guard masking the missing/malformed budget), so this case
                # pins the gap-4 guard exactly: reverting it turns this RED.
                if "budget" not in str(exc4):
                    violations.append(
                        f"fc-gap4-{gap4_mode}: resume failed closed but NOT with the budget "
                        f"guard (message did not mention budget: {exc4})")
            else:
                violations.append(
                    f"fc-gap4-{gap4_mode}: a {gap4_mode} re-attached budget map was silently "
                    "omitted (resume did not fail closed)")

    # GAP 4b (B2): a `raise` disposition on a NON-budget-exhaustion HOLD (a human/COO
    # gate pause: budget_exhausted=False, hold_reason=human_or_coo_gate_pause,
    # node_landings=0 but a POSITIVE node_budget) must FAIL CLOSED. CURRENT (pre-fix)
    # behaviour: the resume raise path bumps node_budget[target] by budget_increment
    # on ANY hold -- so a raise on a gate pause MANUFACTURES a budget value over a
    # base that was never recovered (diverges from the Link-declared base). A raise is
    # admitted ONLY on a budget-exhaustion HOLD; on a gate pause the human uses
    # forward/stop. SELF-FIRE: reverting the _require_budget_exhaustion_raise check in
    # walker_resume.py makes the human-gate raise proceed (no raise) -> RED. The
    # POSITIVE sub-case (a real budget-exhaustion raise) must STAY GREEN so the fix
    # does not break the legitimate b4-g7/knot raise path.
    with checker_temp_path("bp-bapr-fc-gap4b-pause-") as tmp:
        pfx = "bapr-loop0-fc-gap4b-pause"
        plan4b, b2_4b = _checker_plan(pfx, budget=1)
        plan4b = _with_link_edge_gate(
            plan4b,
            f"edge:{pfx}-review-to-close",
            ["link-gate:default-transition", "link-gate:human"],
        )
        cb4b = _reroute_callable(b2_4b, {f"brick-{pfx}-review"})
        res4b = run_building_plan(
            plan4b, output_root=tmp, overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": cb4b},
            adapter_cwd=repo, adapter_timeout_seconds=30)
        root4b = res4b.lifecycle_write.root
        if observe_building_frontier(root4b, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap4b-pause: setup did not HOLD on a human gate pause")
        # Sanity: the held record is a NON-budget-exhaustion gate pause.
        mp4b, _man4b, plan_ev4b = _read_evidence_plan(root4b)
        hold4b = plan_ev4b["dynamic_walker_evidence"].get("hold", {})
        if hold4b.get("budget_exhausted") is not False or hold4b.get("hold_reason") != "human_or_coo_gate_pause":
            violations.append(
                f"fc-gap4b-pause: setup HOLD was not a human-gate pause (hold={hold4b})")
        _append_disposition_row(root4b, building_id=res4b.building_id,
                                pending_target_ref=b2_4b, action="raise",
                                author_ref="coo:smith", budget_increment=1)
        try:
            resumed4b = resume_building_plan(
                root4b, local_callables={"callable:local:agent-invoke0-smoke": cb4b},
                adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError:
            pass
        else:
            fr4b = observe_building_frontier(resumed4b.lifecycle_write.root, repo_root=repo)
            violations.append(
                "fc-gap4b-pause: a raise on a NON-budget-exhaustion (human-gate) HOLD "
                f"manufactured a budget and proceeded (frontier={fr4b['frontier_kind']}); "
                "must fail closed")

    # GAP 4b POSITIVE: a raise on a REAL budget-exhaustion HOLD must STILL resume
    # (the B2 admission must not break the legitimate raise path).
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap4b-exh-") as tmp:
        pfx = "bapr-loop0-fc-gap4b-exh"
        cb4be = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res4be, b2_4be = _build_held_fc(pfx, tmp, cb4be, budget=1)
        root4be = res4be.lifecycle_write.root
        if observe_building_frontier(root4be, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap4b-exh: setup did not produce a budget-exhaustion HOLD")
        _append_disposition_row(root4be, building_id=res4be.building_id,
                                pending_target_ref=b2_4be, action="raise",
                                author_ref="coo:smith", budget_increment=1)
        try:
            resume_building_plan(
                root4be, local_callables={"callable:local:agent-invoke0-smoke": cb4be},
                adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError as exc4be:
            violations.append(
                f"fc-gap4b-exh: a legitimate budget-exhaustion raise was wrongly rejected "
                f"by the B2 admission check ({exc4be})")

    # fc-15: a budget-exhaustion raise whose persisted evidence carries an EMPTY
    # node_reroute_budgets map bridges the human/COO-authored budget_increment into
    # the resume seed before the EMPTY guard; non-raise empty maps still fail above.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-15-raise-budget-bridge-") as tmp:
        pfx = "bapr-loop0-fc-15-raise-budget-bridge"
        cb15 = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res15, b2_15 = _build_held_fc(pfx, tmp, cb15, budget=1)
        root15 = res15.lifecycle_write.root
        if observe_building_frontier(root15, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-15-raise-budget-bridge: setup did not produce a budget-exhaustion HOLD")
        mp15, man15, plan15 = _read_evidence_plan(root15)
        ev15 = plan15["dynamic_walker_evidence"]
        hold15 = ev15.get("hold", {})
        base_budget15 = hold15.get("node_budget") if isinstance(hold15, Mapping) else None
        ev15["node_reroute_budgets"] = {}
        _write_evidence_plan(mp15, man15, plan15)
        _append_disposition_row(root15, building_id=res15.building_id,
                                pending_target_ref=b2_15, action="raise",
                                author_ref="coo:smith", budget_increment=2)
        try:
            resumed15 = resume_building_plan(
                root15, local_callables={"callable:local:agent-invoke0-smoke": cb15},
                adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError as exc15:
            violations.append(
                "fc-15-raise-budget-bridge: EMPTY node_reroute_budgets blocked a "
                f"budget-exhaustion raise instead of consuming budget_increment ({exc15})")
        else:
            fr15 = observe_building_frontier(resumed15.lifecycle_write.root, repo_root=repo)
            if fr15["frontier_kind"] not in {"complete", "closure_pending", "link_paused"}:
                violations.append(
                    "fc-15-raise-budget-bridge: resumed route reached an unexpected "
                    f"frontier ({fr15['frontier_kind']})")
            _plan15_after, evidence15_after = _read_written_dynamic_plan(resumed15.lifecycle_write.root)
            budgets15_after = evidence15_after.get("node_reroute_budgets")
            if isinstance(base_budget15, int) and not isinstance(base_budget15, bool) and isinstance(budgets15_after, Mapping):
                expected15 = base_budget15 + 2
                if budgets15_after.get(b2_15) != expected15:
                    violations.append(
                        "fc-15-raise-budget-bridge: bridged budget did not preserve "
                        f"the exhausted base plus increment (got {budgets15_after.get(b2_15)!r}, "
                        f"expected {expected15})")

    # fc-19: run_approve_entry refuses budget-incoherent dispositions before
    # raw/link mutation, accepts the EMPTY-map budget-exhaustion recovery path
    # that resume accepts, and never calls resume_building_plan on a refusal.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-19-ledger-cleanliness-") as tmp:
        sandbox19 = Path(tmp)
        pfx = "bapr-loop0-fc-19-ledger-cleanliness"
        plan19, b2_19 = _checker_plan(pfx, budget=1)
        plan19 = _with_link_edge_gate(
            plan19,
            f"edge:{pfx}-review-to-close",
            ["link-gate:default-transition", "link-gate:human"],
        )
        cb19 = _reroute_callable(b2_19, {f"brick-{pfx}-review"})
        res19 = run_building_plan(
            plan19, output_root=Path(tmp), overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": cb19},
            adapter_cwd=repo, adapter_timeout_seconds=30)
        root19 = res19.lifecycle_write.root
        if observe_building_frontier(root19, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-19-ledger-cleanliness: setup did not HOLD on a human gate pause")
        adapter_cwd19 = sandbox19 / "adapter-cwd"
        adapter_cwd19.mkdir(parents=True, exist_ok=True)
        link19 = root19 / "raw" / "link.jsonl"
        link19_before = link19.read_bytes()
        resume_calls19: list[Path] = []
        original_resume19 = run_module.resume_building_plan

        def _spy_resume_refused19(building_root, **kwargs):
            resume_calls19.append(Path(building_root))
            return original_resume19(building_root, **kwargs)

        run_module.resume_building_plan = _spy_resume_refused19
        try:
            malformed19 = run_approve_entry(
                root19,
                action="raise",
                author_ref="coo:smith",
                budget_increment="malformed",  # type: ignore[arg-type]
                adapter_cwd=adapter_cwd19,
                adapter_timeout_seconds=30,
                repo_root=repo,
            )
            rejected19 = run_approve_entry(
                root19,
                action="raise",
                author_ref="coo:smith",
                budget_increment=1,
                adapter_cwd=adapter_cwd19,
                adapter_timeout_seconds=30,
                repo_root=repo,
            )
        finally:
            run_module.resume_building_plan = original_resume19
        if malformed19.get("error_kind") != "invalid_budget_increment":
            violations.append(
                "fc-19-ledger-cleanliness: malformed raise did not return "
                f"invalid_budget_increment ({malformed19.get('error_kind')})"
            )
        if rejected19.get("error_kind") != "invalid_disposition_for_hold":
            violations.append(
                "fc-19-ledger-cleanliness: non-budget raise did not return "
                f"invalid_disposition_for_hold ({rejected19.get('error_kind')})"
            )
        if malformed19.get("disposition_written") is not False or rejected19.get("disposition_written") is not False:
            violations.append("fc-19-ledger-cleanliness: refused raise reported disposition_written")
        if link19.read_bytes() != link19_before:
            violations.append("fc-19-ledger-cleanliness: refused raise changed raw/link bytes")
        if resume_calls19:
            violations.append("fc-19-ledger-cleanliness: refused raise called resume_building_plan")
        _plan19_after_bad, evidence19_after_bad = _read_written_dynamic_plan(root19)
        if not evidence19_after_bad.get("held"):
            violations.append("fc-19-ledger-cleanliness: rejected raise cleared held evidence")
        if _resume_observations(evidence19_after_bad):
            violations.append("fc-19-ledger-cleanliness: rejected raise left an applied resume observation")
        original_resume19f = run_module.resume_building_plan

        def _resume_with_local_callables19(building_root, **kwargs):
            kwargs["local_callables"] = {"callable:local:agent-invoke0-smoke": cb19}
            return original_resume19f(building_root, **kwargs)

        run_module.resume_building_plan = _resume_with_local_callables19
        try:
            forward19 = run_approve_entry(
                root19,
                action="forward",
                author_ref="coo:smith",
                adapter_cwd=adapter_cwd19,
                adapter_timeout_seconds=30,
                repo_root=repo,
            )
        finally:
            run_module.resume_building_plan = original_resume19f
        if forward19.get("ok") is not True:
            violations.append(
                "fc-19-ledger-cleanliness: later forward disposition was blocked "
                f"after a rejected raise ({forward19.get('error_kind')}: "
                f"{forward19.get('error_message')})")
        else:
            fr19 = observe_building_frontier(root19, repo_root=repo)
            if fr19["frontier_kind"] not in {"complete", "closure_pending"}:
                violations.append(
                    "fc-19-ledger-cleanliness: later forward disposition did not "
                    f"resume to a terminal frontier (frontier={fr19['frontier_kind']})")

    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-19-budget-target-red-") as tmp:
        sandbox19b = Path(tmp)
        pfx = "bapr-loop0-fc-19-budget-target-red"
        cb19b = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res19b, b2_19b = _build_held_fc(pfx, tmp, cb19b, budget=1)
        root19b = res19b.lifecycle_write.root
        mp19b, man19b, plan19b = _read_evidence_plan(root19b)
        plan19b["dynamic_walker_evidence"]["node_reroute_budgets"] = {
            f"brick-{pfx}-other": 1
        }
        _write_evidence_plan(mp19b, man19b, plan19b)
        adapter_cwd19b = sandbox19b / "adapter-cwd"
        adapter_cwd19b.mkdir(parents=True, exist_ok=True)
        link19b = root19b / "raw" / "link.jsonl"
        link19b_before = link19b.read_bytes()
        resume_calls19b: list[Path] = []
        original_resume19b = run_module.resume_building_plan

        def _spy_resume_refused19b(building_root, **kwargs):
            resume_calls19b.append(Path(building_root))
            return original_resume19b(building_root, **kwargs)

        run_module.resume_building_plan = _spy_resume_refused19b
        try:
            rejected19b = run_approve_entry(
                root19b,
                action="raise",
                author_ref="coo:smith",
                budget_increment=1,
                adapter_cwd=adapter_cwd19b,
                adapter_timeout_seconds=30,
                repo_root=repo,
            )
        finally:
            run_module.resume_building_plan = original_resume19b
        if rejected19b.get("error_kind") != "resume_budget_precheck_refused":
            violations.append(
                "fc-19-budget-target-red: no-budget target raise did not return "
                f"resume_budget_precheck_refused ({rejected19b.get('error_kind')})"
            )
        if rejected19b.get("disposition_written") is not False:
            violations.append("fc-19-budget-target-red: refused raise reported disposition_written")
        if link19b.read_bytes() != link19b_before:
            violations.append("fc-19-budget-target-red: refused raise changed raw/link bytes")
        if resume_calls19b:
            violations.append("fc-19-budget-target-red: refused raise called resume_building_plan")

    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-19-empty-map-accept-") as tmp:
        sandbox19c = Path(tmp)
        pfx = "bapr-loop0-fc-19-empty-map-accept"
        cb19c = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res19c, _b2_19c = _build_held_fc(pfx, tmp, cb19c, budget=1)
        root19c = res19c.lifecycle_write.root
        mp19c, man19c, plan19c = _read_evidence_plan(root19c)
        plan19c["dynamic_walker_evidence"]["node_reroute_budgets"] = {}
        _write_evidence_plan(mp19c, man19c, plan19c)
        adapter_cwd19c = sandbox19c / "adapter-cwd"
        adapter_cwd19c.mkdir(parents=True, exist_ok=True)
        resume_calls19c: list[Path] = []
        original_resume19c = run_module.resume_building_plan

        def _resume_with_local_callables19c(building_root, **kwargs):
            resume_calls19c.append(Path(building_root))
            kwargs["local_callables"] = {"callable:local:agent-invoke0-smoke": cb19c}
            return original_resume19c(building_root, **kwargs)

        run_module.resume_building_plan = _resume_with_local_callables19c
        try:
            accepted19c = run_approve_entry(
                root19c,
                action="raise",
                author_ref="coo:smith",
                budget_increment=2,
                adapter_cwd=adapter_cwd19c,
                adapter_timeout_seconds=30,
                repo_root=repo,
            )
        finally:
            run_module.resume_building_plan = original_resume19c
        if accepted19c.get("disposition_written") is not True:
            violations.append("fc-19-empty-map-accept: recovery raise did not write disposition")
        if accepted19c.get("error_kind"):
            violations.append(
                "fc-19-empty-map-accept: recovery raise was refused "
                f"({accepted19c.get('error_kind')}: {accepted19c.get('error_message')})"
            )
        if not resume_calls19c:
            violations.append("fc-19-empty-map-accept: recovery raise did not call resume_building_plan")

    # fc-21: step-output frontier > raw returns fails before replay adoption with
    # one explicit reason; the healthy route still resumes under the same fixture.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-21-pre-integrity-") as tmp:
        pfx = "bapr-loop0-fc-21-pre-integrity"
        cb21 = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res21, b2_21 = _build_held_fc(pfx, tmp, cb21, budget=1)
        root21 = res21.lifecycle_write.root
        _append_disposition_row(root21, building_id=res21.building_id,
                                pending_target_ref=b2_21, action="forward", author_ref="coo:smith")
        try:
            healthy21 = resume_building_plan(
                root21, local_callables={"callable:local:agent-invoke0-smoke": cb21},
                adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError as exc21h:
            violations.append(f"fc-21-pre-integrity-parity: healthy resume was rejected ({exc21h})")
        else:
            fr21h = observe_building_frontier(healthy21.lifecycle_write.root, repo_root=repo)
            if fr21h["frontier_kind"] not in {"complete", "closure_pending", "link_paused"}:
                violations.append(
                    "fc-21-pre-integrity-parity: healthy resume reached unexpected "
                    f"frontier ({fr21h['frontier_kind']})")

    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-21-pre-integrity-red-") as tmp:
        pfx = "bapr-loop0-fc-21-pre-integrity-red"
        cb21r = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res21r, b2_21r = _build_held_fc(pfx, tmp, cb21r, budget=1)
        root21r = res21r.lifecycle_write.root
        ar21r = root21r / "raw" / "agent-return.jsonl"
        lines21r = [l for l in ar21r.read_text(encoding="utf-8").splitlines() if l.strip()]
        kept21r = [l for l in lines21r if json.loads(l).get("step_ref") != f"{pfx}-design"]
        ar21r.write_text("\n".join(kept21r) + "\n", encoding="utf-8")
        _append_disposition_row(root21r, building_id=res21r.building_id,
                                pending_target_ref=b2_21r, action="forward", author_ref="coo:smith")
        live_calls_21r = []
        def _sentinel21r(request):
            live_calls_21r.append(request.brick_instance_ref)
            return {"observed_evidence": [f"obs {request.brick_instance_ref}"], "not_proven": ["x"]}
        try:
            resume_building_plan(root21r, local_callables={"callable:local:agent-invoke0-smoke": _sentinel21r},
                                 adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError as exc21r:
            msg21r = str(exc21r)
            if "step-output frontier is ahead of raw/agent-return.jsonl" not in msg21r:
                violations.append(
                    "fc-21-pre-integrity-red: corrupt route failed with the wrong "
                    f"reason ({exc21r})")
        else:
            violations.append("fc-21-pre-integrity-red: corrupt route did not fail before replay adoption")
        if f"brick-{pfx}-design" in live_calls_21r:
            violations.append("fc-21-pre-integrity-red: corrupt pre-HOLD step ran live")

    # GAP 5: a replayed step that DECLARED a gate_sequence_policy but has NO recorded
    # gate decision must FAIL CLOSED (not silently treated as no-action).
    with checker_temp_path("bp-bapr-fc-gap5-") as tmp:
        pfx = "bapr-loop0-fc-gap5"
        plan5, b2_5 = _checker_plan(pfx, budget=1)
        plan5 = _with_link_edge_gate_sequence_policy(
            plan5, f"edge:{pfx}-design-to-build",
            declared_gate_refs=["link-gate:default-transition"],
            gate_sequence_policy=[{
                "gate_ref": "link-gate:default-transition",
                "on_missing_required_facts": {
                    "action": "HOLD", "pending_target_basis": "target_brick",
                    "reason_refs": [f"observation:{pfx}-missing"],
                    "required_disposition_owner": "caller-or-coo"},
                "on_sufficient": {"action": "forward"}}])
        cb5 = _reroute_callable(b2_5, {f"brick-{pfx}-design", f"brick-{pfx}-review"})
        res5 = run_building_plan(
            plan5, output_root=tmp, overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": cb5},
            adapter_cwd=repo, adapter_timeout_seconds=30)
        root5 = res5.lifecycle_write.root
        if observe_building_frontier(root5, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap5: setup did not HOLD")
        # Delete design's recorded gate decision (it declared a policy + recorded one).
        deleted5 = False
        for p5 in (root5 / "work" / "step-outputs").glob("*/step-output.json"):
            v5 = json.loads(p5.read_text(encoding="utf-8"))
            if v5.get("step_ref") == f"{pfx}-design":
                if v5.get("gate_sequence_decision_record") is None:
                    violations.append("fc-gap5: design did not record a gate decision (setup invalid)")
                v5.pop("gate_sequence_decision_record", None)
                p5.write_text(json.dumps(v5), encoding="utf-8")
                deleted5 = True
        if not deleted5:
            violations.append("fc-gap5: could not find design step-output to corrupt")
        _append_disposition_row(root5, building_id=res5.building_id,
                                pending_target_ref=b2_5, action="forward", author_ref="coo:smith")
        try:
            resume_building_plan(root5, local_callables={"callable:local:agent-invoke0-smoke": cb5},
                                 adapter_cwd=repo, adapter_timeout_seconds=30)
        except ValueError:
            pass
        else:
            violations.append(
                "fc-gap5: a replayed policy step with NO recorded gate decision was silently "
                "treated as no-action (resume did not fail closed)")

    # GAP 6: replayed step outputs must PRESERVE the original recorded_at.
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap6-") as tmp:
        pfx = "bapr-loop0-fc-gap6"
        cb = _reroute_callable(
            f"brick-{pfx}-build",
            {f"brick-{pfx}-design", f"brick-{pfx}-review"},
        )
        res6, b2_6 = _build_held_fc(pfx, tmp, cb, budget=1)
        root6 = res6.lifecycle_write.root
        if observe_building_frontier(root6, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("fc-gap6: setup did not HOLD")
        def _recorded_at_map(rt: Path):
            out6 = {}
            for p6 in (rt / "work" / "step-outputs").glob("*/step-output.json"):
                v6 = json.loads(p6.read_text(encoding="utf-8"))
                out6[(v6.get("step_ref"), v6.get("attempt_index"))] = v6.get("recorded_at")
            return out6
        before6 = _recorded_at_map(root6)
        _append_disposition_row(root6, building_id=res6.building_id,
                                pending_target_ref=b2_6, action="forward", author_ref="coo:smith")
        resumed6 = resume_building_plan(root6, local_callables={"callable:local:agent-invoke0-smoke": cb},
                                        adapter_cwd=repo, adapter_timeout_seconds=30)
        after6 = _recorded_at_map(resumed6.lifecycle_write.root)
        for key6 in [(f"{pfx}-design", 1), (f"{pfx}-build", 1), (f"{pfx}-build", 2)]:
            o6, n6 = before6.get(key6), after6.get(key6)
            if o6 and n6 and o6 != n6:
                violations.append(
                    f"fc-gap6: replayed step {key6} got a FRESH recorded_at ({n6}) instead of "
                    f"preserving the original ({o6})")

    # PROOF-F4 (0703): a declared proof rc mismatch must create a formal
    # implementation_gap transition concern, the walker must adopt it through the
    # normal reroute path, and the same declared Brick must be redispatched. The
    # second attempt flips the observed proof command green so this fixture covers
    # mismatch -> concern -> adoption -> redispatch without exhausting budget.
    with checker_temp_path("bp-bapr-proof-f4-") as tmp:
        pfx = "bapr-loop0-proof-f4"
        plan_pf4, build_pf4 = _checker_plan(pfx, budget=1)
        marker_pf4 = tmp / "proof-state.txt"
        proof_cmd_pf4 = (
            "python3 -c \"from pathlib import Path; import sys; "
            f"sys.exit(0 if Path({str(marker_pf4)!r}).read_text(encoding='utf-8') == 'green' else 1)\""
        )
        plan_pf4 = copy.deepcopy(plan_pf4)
        for step_pf4 in plan_pf4["brick_steps"]:
            if step_pf4.get("step_ref") != f"{pfx}-build":
                continue
            for row_pf4 in step_pf4.get("rows", []):
                if isinstance(row_pf4, dict) and row_pf4.get("axis") == "Brick":
                    row_pf4["proof_obligations"] = [
                        {"command": proof_cmd_pf4, "expect_rc": 0}
                    ]
        calls_pf4: dict[str, int] = {}

        def _proof_f4_callable(request: Any) -> Mapping[str, Any]:
            calls_pf4[request.brick_instance_ref] = (
                calls_pf4.get(request.brick_instance_ref, 0) + 1
            )
            if request.brick_instance_ref == build_pf4:
                state_pf4 = "green" if calls_pf4[request.brick_instance_ref] >= 2 else "red"
                marker_pf4.write_text(state_pf4, encoding="utf-8")
            return {
                "observed_evidence": [f"proof-f4 obs {request.brick_instance_ref}"],
                "not_proven": ["semantic correctness"],
            }

        res_pf4 = run_building_plan(
            plan_pf4,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _proof_f4_callable},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        adopted_pf4 = _adopted_records(
            list(getattr(res_pf4, "_dynamic_walker_reroute_records", ()))
        )
        if calls_pf4.get(build_pf4) != 2:
            violations.append(
                "proof-f4: proof mismatch did not redispatch the same declared Brick "
                f"(build call count {calls_pf4.get(build_pf4)!r})"
            )
        if len(adopted_pf4) != 1:
            violations.append(
                f"proof-f4: expected one adopted proof reroute, got {len(adopted_pf4)}"
            )
        elif (
            adopted_pf4[0].get("source_brick_ref") != build_pf4
            or adopted_pf4[0].get("target_brick") != build_pf4
            or adopted_pf4[0].get("source_transition_concern_ref", "").startswith(
                "transition-concern:proof-obligation:"
            )
            is not True
        ):
            violations.append(
                "proof-f4: adopted reroute did not preserve the machine-authored "
                f"proof concern source/target ({adopted_pf4[0]!r})"
            )
        frontier_pf4 = observe_building_frontier(
            res_pf4.lifecycle_write.root,
            repo_root=repo,
        )
        if frontier_pf4.get("frontier_kind") != "complete":
            violations.append(
                f"proof-f4: rerouted proof fixture did not complete ({frontier_pf4!r})"
            )

    # ------------------------------------------------------------------
    # MAIL-REPAIR (Smith rulings 0611, B1/B2/B3): runtime rows ride the mail.
    # Ported b5b probe (measured RED 0611: in a gate-adopted dynamic reroute,
    # runtime concern.reason_refs markers arrived in 0/10 redo-worker inputs
    # while declared refs arrived in all) as an EXECUTED case family:
    #   mail-1  runtime marker ARRIVES in every redo input (and ONLY there),
    #           provenance recorded as data, packet carries recorded refs and
    #           compact summary fields only, receipt (B2) records the delivered
    #           addresses as fact.
    #   mail-2  broken ledger address (B1) -> HOLD loudly, nothing adopted.
    #   mail-3  declared-only plan: declared routing mailbox body remains
    #           byte-identical after normalizing support-only step-output handoff
    #           metadata; NO runtime_handoffs key (regression guard).
    #   mail-4  raise-resume: THIS resume's disposition row reason_refs ride
    #           to the re-adopted redo landing (B3 lane 2).
    # ------------------------------------------------------------------
    from brick_protocol.support.operator.plan_validation import (
        _incoming_link_handoff_refs as _declared_mailbox_assembler,
    )
    from brick_protocol.support.operator.walker_hold import (
        _hold_paused_at_ref as _hold_identity_ref,
    )
    from brick_protocol.support.operator.walker_resume import (
        _read_disposition_row as _live_read_disposition_row,
        _read_written_dynamic_plan as _mail_plan_evidence,
    )
    from brick_protocol.support.recording.step_outputs import (
        _step_output_manifest_ref as _mail_manifest_ref,
    )

    def _mail_disposition_selection_replay(
        ledger_snapshot: str,
        hold_record: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        """Replay the disposition selection by CALLING THE LIVE FUNCTION.

        codex re-review also-check b (0611): this oracle previously
        REIMPLEMENTED the selection predicate (file-order rows carrying a
        disposition_action whose pending_target_ref AND hold identity match the
        current hold; the selected row is the LAST match), which could silently
        diverge from production. It now materializes the pre-resume ledger
        snapshot as raw/link.jsonl under a throwaway root and invokes
        ``walker_resume._read_disposition_row`` -- the SAME function the resume
        verb runs -- so the test predicate CANNOT diverge from the live rule.
        Returns the selected disposition mapping (carrying
        ``selected_row_provenance``) or None when nothing matches.
        """

        with checker_temp_path("bp-bapr-mail-oracle-") as oracle_root:
            (oracle_root / "raw").mkdir(parents=True)
            (oracle_root / "raw" / "link.jsonl").write_text(
                ledger_snapshot, encoding="utf-8"
            )
            return _live_read_disposition_row(oracle_root, hold_record)

    _mail_provenance_keys = (
        "disposition_row_paused_at_ref",
        "disposition_row_raw_ref",
        "disposition_row_same_hold_index",
    )

    mail_runtime_marker = "observation:mail-repair-runtime-marker-rides"
    mail_declared_marker = "observation:mail-repair-declared-lane-reason"
    _mail_entry_allowed_keys = {
        "from_step_ref",
        "from_brick_instance_ref",
        "row_kind",
        "row_ref",
        "concern_doc_ref",
        "reason_refs",
        "undelivered_citation_refs",
        "recorded_summary_fields",
        "provenance",
        "reroute_ref",
    }

    def _mail_plan() -> tuple[Mapping[str, Any], Mapping[str, str]]:
        plan, refs = _full_chain_replay_plan()
        plan = json.loads(json.dumps(plan))
        for edge in plan["link_edges"]:
            for row in edge["rows"]:
                if row.get("movement") == "reroute":
                    row["route_replay_plan"]["route_reason_refs"] = [
                        *row["route_replay_plan"]["route_reason_refs"],
                        mail_declared_marker,
                    ]
        return plan, refs

    def _mail_capture_callable(
        source_brick: str,
        extra_reason_refs: list[str],
        extra_returned: Mapping[str, Any] | None = None,
    ):
        captures: list[dict[str, Any]] = []

        def _callable(request: Any) -> Mapping[str, Any]:
            captures.append(
                {
                    "brick_instance_ref": request.brick_instance_ref,
                    "link_handoff_refs": json.loads(
                        json.dumps(request.link_handoff_refs, default=str)
                    ),
                }
            )
            returned: dict[str, Any] = {
                "observed_evidence": [f"mail obs {request.brick_instance_ref}"],
                "not_proven": ["semantic correctness"],
            }
            if extra_returned:
                returned.update(dict(extra_returned))
            if request.brick_instance_ref == source_brick:
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [
                        f"brick-comparison:{request.brick_instance_ref}",
                        *extra_reason_refs,
                    ],
                    "related_boundary_refs": ["brick-bapr-loop0-b5-c3-a2"],
                }
            return returned

        return captures, _callable

    handoff_absolute_path_markers = ("/Users", "/home", "scratchpad", "/private/tmp")

    def _assert_no_absolute_path_handoff_markers(
        label: str,
        captures: Sequence[Mapping[str, Any]],
    ) -> None:
        for i, capture in enumerate(captures):
            payload = json.dumps(capture.get("link_handoff_refs", {}), default=str)
            leaked = [marker for marker in handoff_absolute_path_markers if marker in payload]
            if leaked:
                violations.append(
                    f"{label}: agent input [{i}] link_handoff_refs leaked "
                    f"absolute/session-local path markers {leaked}"
                )

    # mail-1: runtime marker arrival + provenance + addresses-only + receipt.
    plan_m1, refs_m1 = _mail_plan()
    captures_m1, callable_m1 = _mail_capture_callable(
        refs_m1["source"], [mail_runtime_marker]
    )
    with checker_temp_path("bp-bapr-mail-1-") as tmp:
        res_m1 = run_building_plan(
            plan_m1,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m1},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m1 = res_m1.lifecycle_write.root
        rec_m1 = list(getattr(res_m1, "_dynamic_walker_reroute_records", ()))
        if len(_adopted_records(rec_m1)) != 1:
            violations.append(
                f"mail-1: expected exactly 1 adopted reroute, got {len(_adopted_records(rec_m1))}"
            )
        sequence_m1 = [c["brick_instance_ref"] for c in captures_m1]
        expected_sequence_m1 = [
            "brick-bapr-loop0-b5-c3-a1",
            "brick-bapr-loop0-b5-c3-b1",
            "brick-bapr-loop0-b5-c3-c1",
            "brick-bapr-loop0-b5-c3-a2",
            "brick-bapr-loop0-b5-c3-b2",
            "brick-bapr-loop0-b5-c3-c2",
            "brick-bapr-loop0-b5-c3-a2",
            "brick-bapr-loop0-b5-c3-b2",
            "brick-bapr-loop0-b5-c3-c2",
            "brick-bapr-loop0-b5-c3-d2",
        ]
        if sequence_m1 != expected_sequence_m1:
            violations.append(f"mail-1: unexpected execution sequence {sequence_m1}")
        else:
            redo_indices = (3, 4, 5)
            other_indices = (0, 1, 2, 6, 7, 8, 9)
            for i in redo_indices:
                mailbox = captures_m1[i]["link_handoff_refs"]
                mailbox_json = json.dumps(mailbox, ensure_ascii=False)
                entries = mailbox.get("runtime_handoffs")
                if not isinstance(entries, list) or len(entries) != 1:
                    violations.append(
                        f"mail-1: redo input [{i}] did not carry exactly one runtime handoff entry"
                    )
                    continue
                entry = entries[0]
                if entry.get("row_kind") != "transition_concern":
                    violations.append(f"mail-1: redo input [{i}] runtime row_kind drifted")
                if mail_runtime_marker not in entry.get("reason_refs", []):
                    violations.append(
                        f"mail-1: runtime reason_ref marker did NOT arrive in redo input [{i}]"
                    )
                if mail_declared_marker not in mailbox_json:
                    violations.append(
                        f"mail-1: declared route_replay marker REGRESSED out of redo input [{i}]"
                    )
                if not set(entry).issubset(_mail_entry_allowed_keys):
                    violations.append(
                        f"mail-1: runtime handoff entry keys drifted in [{i}]: {sorted(entry)} "
                        "(expected recorded refs, quarantined citation refs, summary fields, and provenance only)"
                    )
                if "concern_doc_ref" not in entry:
                    violations.append(
                        f"mail-1: redo input [{i}] does not carry the guaranteed concern_doc_ref"
                    )
                summary_fields = entry.get("recorded_summary_fields")
                if not isinstance(summary_fields, Mapping) or "observed_evidence" not in summary_fields:
                    violations.append(
                        f"mail-1: redo input [{i}] does not carry recorded observed_evidence summary"
                    )
                provenance = entry.get("provenance")
                if not isinstance(provenance, Mapping):
                    violations.append(f"mail-1: redo input [{i}] runtime entry has NO provenance")
                else:
                    recorded_in = str(provenance.get("recorded_in") or "")
                    recorded_path = root_m1 / recorded_in
                    if provenance.get("row_kind") != "transition_concern":
                        violations.append(f"mail-1: provenance row_kind drifted in [{i}]")
                    if not recorded_in or not recorded_path.is_file():
                        violations.append(
                            f"mail-1: provenance recorded_in does not resolve in the ledger [{i}]"
                        )
                    elif mail_runtime_marker not in recorded_path.read_text(encoding="utf-8"):
                        violations.append(
                            f"mail-1: recorded ledger row does not carry the delivered address [{i}] "
                            "(delivery must read the recorded fact)"
                        )
            for i in other_indices:
                mailbox = captures_m1[i]["link_handoff_refs"]
                if "runtime_handoffs" in mailbox:
                    violations.append(
                        f"mail-1: non-redo input [{i}] carried runtime_handoffs (B3 narrow violated)"
                    )
                if mail_runtime_marker in json.dumps(mailbox, ensure_ascii=False):
                    violations.append(
                        f"mail-1: runtime marker leaked into non-redo input [{i}]"
                    )
            # B2 receipt: the redo step's AgentReceipt records the delivered
            # addresses as fact -- in the prepared ReceiptFact AND in the written
            # capture evidence (agent_received facts carry received_handoff_refs).
            redo_receipt = res_m1.step_results[3].preparation.receipt_fact
            if mail_runtime_marker not in redo_receipt.received_handoff_refs:
                violations.append(
                    "mail-1: redo step ReceiptFact.received_handoff_refs does not carry the "
                    "delivered runtime address (B2)"
                )
            declared_receipt = res_m1.step_results[6].preparation.receipt_fact
            if mail_declared_marker not in declared_receipt.received_handoff_refs:
                violations.append(
                    "mail-1: declared-pass ReceiptFact.received_handoff_refs does not carry the "
                    "declared address (B2)"
                )
            if mail_runtime_marker in declared_receipt.received_handoff_refs:
                violations.append(
                    "mail-1: runtime address leaked into the declared-pass receipt (B3 narrow)"
                )
            receipt_event_hit = False
            events_path = root_m1 / "capture" / "events.jsonl"
            for line in events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                data = event.get("data") if isinstance(event.get("data"), Mapping) else event
                if "agent-received" not in str(data.get("event_id", "")):
                    continue
                refs_recorded = data.get("received_handoff_refs")
                if isinstance(refs_recorded, list) and mail_runtime_marker in refs_recorded:
                    receipt_event_hit = True
                    break
            if not receipt_event_hit:
                violations.append(
                    "mail-1: written agent_received capture event does not record the delivered "
                    "runtime address (B2 receipt evidence)"
                )

    # mail-2 (B1): an address claiming a ledger residence with NO document is a
    # broken ticket -> HOLD loudly via the existing hold machinery; nothing rides,
    # nothing is adopted, no budget is consumed.
    plan_m2, refs_m2 = _mail_plan()
    captures_m2, callable_m2 = _mail_capture_callable(
        refs_m2["source"],
        ["work/step-outputs/mail-repair-missing-attempt-1/step-output.json"],
    )
    with checker_temp_path("bp-bapr-mail-2-") as tmp:
        res_m2 = run_building_plan(
            plan_m2,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m2},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        rec_m2 = list(getattr(res_m2, "_dynamic_walker_reroute_records", ()))
        held_m2 = _held_records(rec_m2)
        fr_m2 = observe_building_frontier(res_m2.lifecycle_write.root, repo_root=repo)
        if _adopted_records(rec_m2):
            violations.append("mail-2: a broken-address reroute was ADOPTED (silent delivery)")
        if len(held_m2) != 1 or not str(held_m2[0].get("hold_reason", "")).startswith(
            "runtime_handoff_address_unresolved_in_ledger"
        ):
            violations.append(
                "mail-2: broken ledger address did not HOLD with the loud "
                f"runtime_handoff_address_unresolved_in_ledger reason ({[r.get('hold_reason') for r in held_m2]})"
            )
        if fr_m2["frontier_kind"] != "link_paused":
            violations.append(
                f"mail-2: broken-address HOLD frontier was not link_paused ({fr_m2['frontier_kind']})"
            )
        if len(res_m2.step_results) != 3:
            violations.append(
                "mail-2: walk did not stop at the broken-address boundary "
                f"({len(res_m2.step_results)} steps executed)"
            )
        if any(mail_runtime_marker in json.dumps(c["link_handoff_refs"]) for c in captures_m2):
            violations.append("mail-2: a broken-mail packet was still delivered to an agent input")

    # mail-3 (regression guard): a declared-only plan's mailbox is BYTE-IDENTICAL
    # to the declared assembler output -- the widening adds NOTHING when no
    # runtime row is eligible.
    plan_m3, _refs_m3 = _mail_plan()
    captures_m3, _unused_callable = _mail_capture_callable("brick-none", [])

    def _clean_callable_m3(request: Any) -> Mapping[str, Any]:
        captures_m3.append(
            {
                "brick_instance_ref": request.brick_instance_ref,
                "link_handoff_refs": json.loads(
                    json.dumps(request.link_handoff_refs, default=str)
                ),
            }
        )
        return {
            "observed_evidence": [f"mail declared-only obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }

    with checker_temp_path("bp-bapr-mail-3-") as tmp:
        run_building_plan(
            plan_m3,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _clean_callable_m3},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
    linear_m3, _graph_context_m3 = _linear_plan_from_graph_plan(plan_m3)
    linear_steps_m3 = list(linear_m3["steps"])
    if len(captures_m3) != len(linear_steps_m3):
        violations.append(
            f"mail-3: declared-only walk executed {len(captures_m3)} steps, "
            f"expected {len(linear_steps_m3)}"
        )
    else:
        for i, capture in enumerate(captures_m3):
            declared_mailbox = json.loads(
                json.dumps(
                    _declared_mailbox_assembler(linear_steps_m3, i), default=str
                )
            )
            observed_mailbox = json.loads(
                json.dumps(capture["link_handoff_refs"], default=str)
            )
            for entry in observed_mailbox.get("incoming", []):
                if isinstance(entry, dict):
                    entry.pop("building_root_path", None)
                    entry.pop("building_root_ref", None)
                    entry.pop("from_step_output_ref", None)
                    entry.pop("proof_limits", None)
            if json.dumps(observed_mailbox, sort_keys=True) != json.dumps(
                declared_mailbox, sort_keys=True
            ):
                violations.append(
                    f"mail-3: declared-only mailbox [{i}] drifted from the declared "
                    "routing body after support metadata normalization (byte-identity regression)"
                )
            if "runtime_handoffs" in capture["link_handoff_refs"]:
                violations.append(
                    f"mail-3: declared-only mailbox [{i}] grew a runtime_handoffs key"
                )

    # mail-3a (absolute-path-0): completed upstream step-output addresses may
    # ride to the next Agent input, but session-local building roots must not.
    # The scratchpad temp prefix would leak through the old building_root_path
    # stamp; the repaired support stamp omits temp roots entirely.
    plan_m3a, _refs_m3a = _mail_plan()
    captures_m3a, callable_m3a = _mail_capture_callable("brick-none", [])
    with checker_temp_path("scratchpad-bp-bapr-mail-3a-") as tmp:
        run_building_plan(
            plan_m3a,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m3a},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
    _assert_no_absolute_path_handoff_markers("mail-3a", captures_m3a)

    # mail-4 (B3 lane 2): a raise-resume's human/COO disposition row reason_refs
    # ride to the re-adopted redo landing, stamped as a resume_disposition entry
    # with raw/link.jsonl provenance.
    mail_disposition_marker = "observation:mail-repair-disposition-reason-rides"
    plan_m4, b2_m4 = _checker_plan("bapr-mail-4-resume", budget=1)
    callable_m4 = _reroute_callable(
        b2_m4,
        {"brick-bapr-mail-4-resume-design", "brick-bapr-mail-4-resume-review"},
    )
    with checker_temp_path("bp-bapr-mail-4-") as tmp:
        res_m4 = run_building_plan(
            plan_m4,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m4},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m4 = res_m4.lifecycle_write.root
        if observe_building_frontier(root_m4, repo_root=repo)["frontier_kind"] != "link_paused":
            violations.append("mail-4: setup did not produce a budget HOLD before raise resume")
        # FIX 2/3 (0611): the CURRENT hold's identity, read from the written
        # evidence BEFORE resume, and the pre-resume ledger snapshot the
        # provenance discriminator must replay against.
        _plan_evidence_m4, evidence_m4 = _mail_plan_evidence(root_m4)
        hold_identity_m4 = (
            _hold_identity_ref(evidence_m4["hold"]) if evidence_m4.get("held") else ""
        )
        _append_disposition_row(
            root_m4,
            building_id=res_m4.building_id,
            pending_target_ref=b2_m4,
            action="raise",
            author_ref="coo:smith",
            budget_increment=1,
            reason_refs=[mail_disposition_marker],
        )
        ledger_snapshot_m4 = (root_m4 / "raw" / "link.jsonl").read_text(encoding="utf-8")
        resume_captures_m4: list[dict[str, Any]] = []

        def _resume_capture_callable_m4(request: Any) -> Mapping[str, Any]:
            resume_captures_m4.append(
                {
                    "brick_instance_ref": request.brick_instance_ref,
                    "link_handoff_refs": json.loads(
                        json.dumps(request.link_handoff_refs, default=str)
                    ),
                }
            )
            return callable_m4(request)

        hold_record_m4 = dict(evidence_m4.get("hold") or {})
        try:
            resume_building_plan(
                root_m4,
                local_callables={
                    "callable:local:agent-invoke0-smoke": _resume_capture_callable_m4
                },
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except ValueError as exc:
            violations.append(f"mail-4: raise resume crashed: {exc}")
        else:
            disposition_entries = [
                entry
                for capture in resume_captures_m4
                if capture["brick_instance_ref"] == b2_m4
                for entry in capture["link_handoff_refs"].get("runtime_handoffs", [])
                if entry.get("row_kind") == "resume_disposition"
            ]
            if not disposition_entries:
                violations.append(
                    "mail-4: the resume disposition row's mail did NOT ride to the "
                    "re-adopted redo landing"
                )
            else:
                entry_m4 = disposition_entries[0]
                if mail_disposition_marker not in entry_m4.get("reason_refs", []):
                    violations.append(
                        "mail-4: disposition reason_ref address did not arrive in the redo input"
                    )
                provenance_m4 = entry_m4.get("provenance")
                if not isinstance(provenance_m4, Mapping) or provenance_m4.get(
                    "recorded_in"
                ) != "raw/link.jsonl":
                    violations.append(
                        "mail-4: resume_disposition entry provenance does not cite raw/link.jsonl"
                    )
                elif provenance_m4.get("author_ref") != "coo:smith":
                    violations.append(
                        "mail-4: resume_disposition provenance does not carry the human/COO author"
                    )
                else:
                    # FIX 3 (0611): the provenance names the SPECIFIC selected
                    # row, not just the file -- hold identity + row raw_ref +
                    # 1-based same-hold index -- and replaying the selection
                    # rule over the pre-resume ledger lands on the SAME row.
                    if provenance_m4.get("disposition_row_paused_at_ref") != hold_identity_m4:
                        violations.append(
                            "mail-4: provenance disposition_row_paused_at_ref does not "
                            "carry the current hold identity (replay provenance ambiguous)"
                        )
                    # FIX 3 (0611, persisted): the provenance must survive in
                    # the WRITTEN resume observation -- the transient ResumeSeed
                    # dies with the process and raw/link.jsonl is REWRITTEN on
                    # resume, so only the persisted observation keeps the
                    # selection replayable later. Read it back from the
                    # rewritten evidence, not from the in-memory seed.
                    _plan_after_m4, evidence_after_m4 = _mail_plan_evidence(root_m4)
                    persisted_obs_m4 = [
                        obs
                        for obs in evidence_after_m4.get("resume_observations", [])
                        if isinstance(obs, Mapping)
                    ]
                    persisted_prov_m4 = (
                        persisted_obs_m4[-1].get("disposition_row_provenance")
                        if persisted_obs_m4
                        else None
                    )
                    if not isinstance(persisted_prov_m4, Mapping):
                        violations.append(
                            "mail-4: the PERSISTED resume observation does not carry "
                            "disposition_row_provenance (replay provenance dies with "
                            "the transient seed)"
                        )
                    elif any(
                        persisted_prov_m4.get(key) != provenance_m4.get(key)
                        for key in _mail_provenance_keys
                    ):
                        violations.append(
                            "mail-4: persisted disposition_row_provenance drifted from "
                            "the delivered runtime-mail provenance"
                        )
                    else:
                        # Replay the selection rule via the LIVE function over
                        # the pre-resume ledger snapshot, keyed by the PERSISTED
                        # discriminator: it must land on the SAME row.
                        oracle_m4 = _mail_disposition_selection_replay(
                            ledger_snapshot_m4, hold_record_m4
                        )
                        oracle_prov_m4 = (
                            oracle_m4.get("selected_row_provenance")
                            if isinstance(oracle_m4, Mapping)
                            else None
                        )
                        if (
                            not isinstance(oracle_prov_m4, Mapping)
                            or any(
                                oracle_prov_m4.get(key) != persisted_prov_m4.get(key)
                                for key in _mail_provenance_keys
                            )
                            or mail_disposition_marker
                            not in list(oracle_m4.get("reason_refs", []))
                        ):
                            violations.append(
                                "mail-4: replaying the recorded selection rule (live "
                                "_read_disposition_row over the pre-resume snapshot) did "
                                "not land on the SAME raw/link.jsonl row deterministically"
                            )

    # mail-5 (FIX 1, 0611 path traversal / cross-building smuggling): a
    # step-output-form address may name ONLY this Building's work/step-outputs/
    # ledger subtree. The old existence-only probe passed a ``..``-escaping ref
    # whose target exists OUTSIDE the building root (verified: it resolves
    # outside) and honored absolute-path refs as building-relative. Both must
    # HOLD loudly (runtime_handoff_address_unresolved_in_ledger, fail-closed);
    # an in-subtree resolving ref must still ride (no over-tightening).
    source_step_m5 = "bapr-loop0-b5-c3-c1"
    in_subtree_ref_m5 = _mail_manifest_ref(source_step_m5, 1)

    # mail-5a: ..-escape to an EXISTING file outside the building root.
    plan_m5a, refs_m5a = _mail_plan()
    escape_ref_m5 = "work/step-outputs/../../../other-building/raw/secret.json"
    captures_m5a, callable_m5a = _mail_capture_callable(
        refs_m5a["source"], [escape_ref_m5]
    )
    with checker_temp_path("bp-bapr-mail-5a-") as tmp:
        smuggle_m5 = tmp / "other-building" / "raw" / "secret.json"
        smuggle_m5.parent.mkdir(parents=True)
        smuggle_m5.write_text("{}", encoding="utf-8")
        res_m5a = run_building_plan(
            plan_m5a,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m5a},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m5a = res_m5a.lifecycle_write.root
        if not (root_m5a / escape_ref_m5).is_file():
            violations.append(
                "mail-5a: setup lost the outside-the-building smuggle target (the "
                "old existence-only probe must see it for this pin to bite)"
            )
        rec_m5a = list(getattr(res_m5a, "_dynamic_walker_reroute_records", ()))
        held_m5a = _held_records(rec_m5a)
        if _adopted_records(rec_m5a):
            violations.append(
                "mail-5a: a ..-escaping ledger address was ADOPTED "
                "(cross-building smuggling delivered)"
            )
        if len(held_m5a) != 1 or not str(held_m5a[0].get("hold_reason", "")).startswith(
            "runtime_handoff_address_unresolved_in_ledger"
        ):
            violations.append(
                "mail-5a: ..-escaping address did not HOLD with the loud "
                "runtime_handoff_address_unresolved_in_ledger reason "
                f"({[r.get('hold_reason') for r in held_m5a]})"
            )
        if any(
            escape_ref_m5 in json.dumps(c["link_handoff_refs"]) for c in captures_m5a
        ):
            violations.append(
                "mail-5a: an escaping address was still delivered to an agent input"
            )

    # mail-5b: an absolute-path ref must not be honored as building-relative
    # (the old probe stripped to the marker and would have let it RIDE because
    # the in-ledger tail exists).
    plan_m5b, refs_m5b = _mail_plan()
    absolute_ref_m5 = "/" + in_subtree_ref_m5
    captures_m5b, callable_m5b = _mail_capture_callable(
        refs_m5b["source"], [absolute_ref_m5]
    )
    with checker_temp_path("bp-bapr-mail-5b-") as tmp:
        res_m5b = run_building_plan(
            plan_m5b,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m5b},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m5b = res_m5b.lifecycle_write.root
        if not (root_m5b / in_subtree_ref_m5).is_file():
            violations.append(
                "mail-5b: setup lost the in-ledger tail document (the old probe "
                "would have ridden on it; this pin needs it present)"
            )
        rec_m5b = list(getattr(res_m5b, "_dynamic_walker_reroute_records", ()))
        held_m5b = _held_records(rec_m5b)
        if _adopted_records(rec_m5b):
            violations.append(
                "mail-5b: an absolute-path address was ADOPTED (honored as "
                "building-relative)"
            )
        if len(held_m5b) != 1 or not str(held_m5b[0].get("hold_reason", "")).startswith(
            "runtime_handoff_address_unresolved_in_ledger"
        ):
            violations.append(
                "mail-5b: absolute-path address did not HOLD with the loud "
                "runtime_handoff_address_unresolved_in_ledger reason "
                f"({[r.get('hold_reason') for r in held_m5b]})"
            )
        if any(
            absolute_ref_m5 in json.dumps(c["link_handoff_refs"]) for c in captures_m5b
        ):
            violations.append(
                "mail-5b: an absolute-path address was still delivered to an agent input"
            )

    # mail-5c: an in-subtree resolving ledger address still rides (the
    # containment guard must not over-tighten the legitimate delivery).
    plan_m5c, refs_m5c = _mail_plan()
    captures_m5c, callable_m5c = _mail_capture_callable(
        refs_m5c["source"], [in_subtree_ref_m5]
    )
    with checker_temp_path("bp-bapr-mail-5c-") as tmp:
        res_m5c = run_building_plan(
            plan_m5c,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m5c},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        rec_m5c = list(getattr(res_m5c, "_dynamic_walker_reroute_records", ()))
        if len(_adopted_records(rec_m5c)) != 1:
            violations.append(
                "mail-5c: an in-subtree resolving ledger address blocked adoption "
                "(containment over-tightened)"
            )
        if not any(
            in_subtree_ref_m5 in entry.get("reason_refs", [])
            for c in captures_m5c
            for entry in c["link_handoff_refs"].get("runtime_handoffs", [])
        ):
            violations.append(
                "mail-5c: an in-subtree resolving address did not ride to the redo input"
            )

    # mail-5d (FIX 1b, 0611 case-bypass): the step-output FORM must be detected
    # case-INSENSITIVELY. On a case-insensitive filesystem (macOS default)
    # ``Work/Step-Outputs/../../...`` addresses the same bytes as the lowercase
    # form, but the exact-case membership test did not recognize it as
    # step-output-form, so it slipped through as an OPAQUE ref and was DELIVERED
    # -- escaping the FIX 1 containment guard entirely (operator-verified
    # 0611: _runtime_handoff_unresolved_address returned "" = delivered). A
    # case-varied escaping ref must HOLD loudly; mail-5c above pins that the
    # legit lowercase in-subtree ref still rides (no over-tightening).
    plan_m5d, refs_m5d = _mail_plan()
    case_escape_ref_m5 = "Work/Step-Outputs/../../../other-building/raw/secret.json"
    captures_m5d, callable_m5d = _mail_capture_callable(
        refs_m5d["source"], [case_escape_ref_m5]
    )
    with checker_temp_path("bp-bapr-mail-5d-") as tmp:
        smuggle_m5d = tmp / "other-building" / "raw" / "secret.json"
        smuggle_m5d.parent.mkdir(parents=True)
        smuggle_m5d.write_text("{}", encoding="utf-8")
        res_m5d = run_building_plan(
            plan_m5d,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m5d},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        rec_m5d = list(getattr(res_m5d, "_dynamic_walker_reroute_records", ()))
        held_m5d = _held_records(rec_m5d)
        if _adopted_records(rec_m5d):
            violations.append(
                "mail-5d: a CASE-VARIED ..-escaping ledger address was ADOPTED "
                "(case-bypass: cross-building smuggling delivered)"
            )
        if len(held_m5d) != 1 or not str(held_m5d[0].get("hold_reason", "")).startswith(
            "runtime_handoff_address_unresolved_in_ledger"
        ):
            violations.append(
                "mail-5d: case-varied ..-escaping address did not HOLD with the loud "
                "runtime_handoff_address_unresolved_in_ledger reason "
                f"({[r.get('hold_reason') for r in held_m5d]})"
            )
        if any(
            case_escape_ref_m5 in json.dumps(c["link_handoff_refs"]) for c in captures_m5d
        ):
            violations.append(
                "mail-5d: a case-varied escaping address was still delivered to an "
                "agent input"
            )

    # mail-5e (FIX 1c, 0611 spelling-independence -- codex round-3 STILL-OPEN):
    # the step-output FORM must be decided by WHERE the ref RESOLVES, not by a
    # CONTIGUOUS ``work/step-outputs/`` marker spelling. Prior rounds
    # whack-a-moled spellings (FIX 1 exact-case, FIX 1b casefolded); a ref that
    # resolves THROUGH the subtree and climbs out but is SPELLED
    # non-contiguously (``work/./step-outputs/../..``, ``work//step-outputs/
    # ../..``) bypassed detection entirely, fell through as an "opaque" ref,
    # and was DELIVERED (operator-verified 0611: returned "" for both
    # variants). Both must HOLD loudly; a deliberately weird-but-contained
    # spelling (``work/./step-outputs/<slug>/step-output.json``) that resolves
    # INSIDE must still ride (containment, not spelling, is the rule -- no
    # over-tightening).
    for variant_tag_m5e, escape_ref_m5e in (
        ("dot-segment", "work/./step-outputs/../../escape/x.json"),
        ("doubled-separator", "work//step-outputs/../../escape/x.json"),
    ):
        plan_m5e, refs_m5e = _mail_plan()
        captures_m5e, callable_m5e = _mail_capture_callable(
            refs_m5e["source"], [escape_ref_m5e]
        )
        with checker_temp_path("bp-bapr-mail-5e-") as tmp:
            res_m5e = run_building_plan(
                plan_m5e,
                output_root=tmp,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": callable_m5e},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
            rec_m5e = list(getattr(res_m5e, "_dynamic_walker_reroute_records", ()))
            held_m5e = _held_records(rec_m5e)
            if _adopted_records(rec_m5e):
                violations.append(
                    f"mail-5e ({variant_tag_m5e}): a non-contiguously spelled "
                    "..-escaping ledger address was ADOPTED (spelling bypass: the "
                    "ref resolves out of work/step-outputs but the contiguous-"
                    "marker detection never saw it)"
                )
            if len(held_m5e) != 1 or not str(
                held_m5e[0].get("hold_reason", "")
            ).startswith("runtime_handoff_address_unresolved_in_ledger"):
                violations.append(
                    f"mail-5e ({variant_tag_m5e}): non-contiguously spelled "
                    "..-escaping address did not HOLD with the loud "
                    "runtime_handoff_address_unresolved_in_ledger reason "
                    f"({[r.get('hold_reason') for r in held_m5e]})"
                )
            if any(
                escape_ref_m5e in json.dumps(c["link_handoff_refs"])
                for c in captures_m5e
            ):
                violations.append(
                    f"mail-5e ({variant_tag_m5e}): a non-contiguously spelled "
                    "escaping address was still delivered to an agent input"
                )

    # mail-5e contained-spelling guard: the SAME non-contiguous spelling that
    # resolves INSIDE the subtree still rides (mirrors mail-5c; pins that the
    # fix is containment-by-resolution, not a new spelling blacklist).
    dotted_in_subtree_ref_m5e = in_subtree_ref_m5.replace(
        "work/step-outputs/", "work/./step-outputs/", 1
    )
    plan_m5e_in, refs_m5e_in = _mail_plan()
    captures_m5e_in, callable_m5e_in = _mail_capture_callable(
        refs_m5e_in["source"], [dotted_in_subtree_ref_m5e]
    )
    with checker_temp_path("bp-bapr-mail-5e-in-") as tmp:
        res_m5e_in = run_building_plan(
            plan_m5e_in,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m5e_in},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        rec_m5e_in = list(getattr(res_m5e_in, "_dynamic_walker_reroute_records", ()))
        if len(_adopted_records(rec_m5e_in)) != 1:
            violations.append(
                "mail-5e (contained spelling): a dot-segment in-subtree resolving "
                "ledger address blocked adoption (containment over-tightened into "
                "a spelling blacklist)"
            )
        if not any(
            dotted_in_subtree_ref_m5e in entry.get("reason_refs", [])
            for c in captures_m5e_in
            for entry in c["link_handoff_refs"].get("runtime_handoffs", [])
        ):
            violations.append(
                "mail-5e (contained spelling): a dot-segment in-subtree resolving "
                "address did not ride to the redo input"
            )

    # mail-5f (FIX 1d, 0611 trusted-intermediate symlink -- codex round-4 NEW
    # High): the containment root must NOT be derived by FOLLOWING A SYMLINK.
    # The prior round resolve()d <building_root>/work/step-outputs FIRST and
    # trusted that resolved inode as the containment root (samestat ancestry),
    # so when work/step-outputs ITSELF was a symlink to an OUTSIDE dir the
    # symlink TARGET became the trusted root and ``work/step-outputs/x.json``
    # was DELIVERED while resolving outside the building (operator-reproduced
    # 0611: _runtime_handoff_unresolved_address returned ""). This pin drives
    # the SAME live resolver the dynamic walker runs (mail-5a/5b/5d/5e prove
    # through the full run that a non-empty return HOLDs loudly with
    # runtime_handoff_address_unresolved_in_ledger; this pin proves the
    # symlinked-ledger-root class returns non-empty), because a full-run
    # fixture cannot hold a symlinked ledger root: the engine itself writes
    # real step-output dirs there mid-run. The symlink is built with
    # os.symlink inside a throwaway tempdir and removed in finally -- the
    # repo tree never carries it.
    from brick_protocol.support.operator.walker_kernel import (
        _runtime_handoff_unresolved_address as _mail_live_resolver,
    )

    with checker_temp_path("bp-bapr-mail-5f-") as tmp:
        building_m5f = tmp / "building"
        (building_m5f / "work").mkdir(parents=True)
        outside_m5f = tmp / "outside"
        outside_m5f.mkdir()
        (outside_m5f / "x.json").write_text("{}", encoding="utf-8")
        ledger_symlink_m5f = building_m5f / "work" / "step-outputs"
        os.symlink(outside_m5f, ledger_symlink_m5f)
        try:
            symlinked_ref_m5f = "work/step-outputs/x.json"
            resolved_m5f = (building_m5f / symlinked_ref_m5f).resolve()
            if not resolved_m5f.is_file() or str(resolved_m5f).startswith(
                str(building_m5f.resolve()) + os.sep
            ):
                violations.append(
                    "mail-5f: setup lost the symlinked ledger root (the ref must "
                    "resolve to an EXISTING file OUTSIDE the building for this "
                    "pin to bite)"
                )
            if _mail_live_resolver(building_m5f, [symlinked_ref_m5f]) == "":
                violations.append(
                    "mail-5f: work/step-outputs IS a symlink to an outside dir, "
                    "yet work/step-outputs/x.json was DELIVERED (the resolved "
                    "ledger subtree was trusted as the containment root -- "
                    "trusted-intermediate symlink class open)"
                )
            # Same probe, real directory: the legit form still delivers (the
            # repair is root-anchored containment, not a symlink blacklist).
            real_building_m5f = tmp / "building-real"
            slug_dir_m5f = (
                real_building_m5f / "work" / "step-outputs" / "doc-attempt-1"
            )
            slug_dir_m5f.mkdir(parents=True)
            (slug_dir_m5f / "step-output.json").write_text("{}", encoding="utf-8")
            legit_ref_m5f = "work/step-outputs/doc-attempt-1/step-output.json"
            if _mail_live_resolver(real_building_m5f, [legit_ref_m5f]) != "":
                violations.append(
                    "mail-5f: a real-directory in-subtree document no longer "
                    "resolves (root-anchored containment over-tightened)"
                )
        finally:
            ledger_symlink_m5f.unlink(missing_ok=True)

    # mail-5g (PIN-COMPLETENESS, 0611 operator sabotage finding): the SECOND
    # escape branch of _step_output_address_escapes_ledger had no pin. The
    # function rejects on TWO distinct branches: (i) candidate resolves
    # OUTSIDE the building root (relative_to raises -> True; pinned by
    # mail-5f) and (ii) candidate resolves INSIDE the building root but its
    # post-resolve relative path does not start with ("work", "step-outputs")
    # -- the FINAL ``return (len(parts) <= 2 or parts[:2] != ...)`` line. The
    # operator sabotaged that final return to ``return False`` and the full
    # checker stayed EXIT 0: the in-building-detour delivery (work/
    # step-outputs symlinked to a SIBLING in-building dir) was caught by no
    # mail case. The live code is correct (operator matrix verified); this
    # pin makes a future regression of that line RED. Same tempdir/os.symlink
    # /finally discipline as mail-5f -- the repo tree never carries a symlink.
    with checker_temp_path("bp-bapr-mail-5g-") as tmp:
        building_m5g = tmp / "building"
        (building_m5g / "work").mkdir(parents=True)
        elsewhere_m5g = building_m5g / "elsewhere"
        elsewhere_m5g.mkdir()
        (elsewhere_m5g / "doc-attempt-1").mkdir()
        (elsewhere_m5g / "doc-attempt-1" / "x.json").write_text(
            "{}", encoding="utf-8"
        )
        ledger_symlink_m5g = building_m5g / "work" / "step-outputs"
        os.symlink(elsewhere_m5g, ledger_symlink_m5g)
        try:
            detour_ref_m5g = "work/step-outputs/doc-attempt-1/x.json"
            resolved_m5g = (building_m5g / detour_ref_m5g).resolve()
            real_root_m5g = building_m5g.resolve()
            in_root_m5g = str(resolved_m5g).startswith(
                str(real_root_m5g) + os.sep
            )
            in_ledger_m5g = str(resolved_m5g).startswith(
                str(real_root_m5g / "work" / "step-outputs") + os.sep
            )
            if not resolved_m5g.is_file() or not in_root_m5g or in_ledger_m5g:
                violations.append(
                    "mail-5g: setup lost the in-building detour (the ref must "
                    "resolve to an EXISTING file INSIDE the building root but "
                    "OUTSIDE work/step-outputs for this pin to bite)"
                )
            if _mail_live_resolver(building_m5g, [detour_ref_m5g]) == "":
                violations.append(
                    "mail-5g: work/step-outputs IS a symlink to a SIBLING "
                    "in-building dir, yet work/step-outputs/doc-attempt-1/"
                    "x.json was DELIVERED (an in-root resolution was trusted "
                    "without the work/step-outputs lexical-prefix guard -- "
                    "the final containment return of "
                    "_step_output_address_escapes_ledger regressed)"
                )
        finally:
            ledger_symlink_m5g.unlink(missing_ok=True)

    # mail-8 (0703 reason_refs address contract): slash-containing runtime
    # handoff refs are ledger document addresses, not citations. The live
    # resolver must HOLD (non-empty unresolved address) for fragment-bearing
    # step-output refs, bare file:line citations, and non-step-output slash
    # paths; standard step-output document paths, step-output manifest refs,
    # and slashless opaque observation tokens still resolve.
    with checker_temp_path("bp-bapr-mail-8-") as tmp:
        building_m8 = tmp / "building"
        step_dir_m8 = building_m8 / "work" / "step-outputs" / "doc-attempt-1"
        step_dir_m8.mkdir(parents=True)
        (step_dir_m8 / "step-output.json").write_text("{}", encoding="utf-8")
        (building_m8 / "brick").mkdir()
        (building_m8 / "brick" / "work.py").write_text("# citation\n", encoding="utf-8")
        illegal_refs_m8 = {
            "fragment-bearing step-output ref": "work/step-outputs/doc-attempt-1/step-output.json#observed",
            "bare file:line citation": "brick/work.py:1",
            "non-step-output slash path": "raw/link.jsonl",
        }
        for label_m8, ref_m8 in illegal_refs_m8.items():
            unresolved_m8 = _mail_live_resolver(building_m8, [ref_m8])
            if unresolved_m8 == "":
                violations.append(
                    f"mail-8: {label_m8} was DELIVERED as a runtime handoff "
                    "reason_ref; slash-containing refs must be existing "
                    "work/step-outputs documents with no #fragment"
                )
            elif unresolved_m8 != ref_m8:
                violations.append(
                    f"mail-8: {label_m8} held the wrong unresolved address; "
                    f"got {unresolved_m8!r}, wanted {ref_m8!r}"
                )
        legal_refs_m8 = {
            "step-output document path": "work/step-outputs/doc-attempt-1/step-output.json",
            "step-output manifest ref": "step-output:doc:attempt-1",
            "slashless opaque observation token": "observation:mail-8-runtime-marker",
        }
        for label_m8, ref_m8 in legal_refs_m8.items():
            unresolved_m8 = _mail_live_resolver(building_m8, [ref_m8])
            if unresolved_m8 != "":
                violations.append(
                    f"mail-8: {label_m8} no longer resolves; got unresolved "
                    f"address {unresolved_m8!r}"
                )

    # mail-8b / mail-9 (0703 D2+D3): newly authored malformed reason_refs are
    # rejected at Agent-return intake, but old recorded rows may already carry
    # citation-shaped refs. Runtime mail must not reverse-resolve or deliver
    # those citations, and must not HOLD the whole reroute when the concern row
    # itself is known. It delivers the guaranteed concern_doc_ref plus any
    # resolvable address refs, records broken citations separately, and carries
    # the already-recorded compact summary fields from the paired step-output.
    from brick_protocol.support.operator.walker_runtime_mail import (
        _runtime_concern_handoff_from_ledger as _live_concern_mail_from_ledger,
    )

    with checker_temp_path("bp-bapr-mail-8b-") as tmp:
        building_m8b = tmp / "building"
        source_step_m8b = "mail-old-shape"
        source_brick_m8b = "brick-mail-old-shape-source"
        source_dir_m8b = (
            building_m8b / "work" / "step-outputs" / f"{source_step_m8b}-attempt-1"
        )
        source_dir_m8b.mkdir(parents=True)
        supporting_ref_m8b = "work/step-outputs/supporting-attempt-1/step-output.json"
        supporting_file_m8b = building_m8b / supporting_ref_m8b
        supporting_file_m8b.parent.mkdir(parents=True)
        supporting_file_m8b.write_text("{}", encoding="utf-8")
        broken_citation_m8b = "raw/link.jsonl"
        concern_ref_m8b = "transition-concern:mail-old-shape-source"
        source_step_ref_m8b = (
            f"work/step-outputs/{source_step_m8b}-attempt-1/step-output.json"
        )
        returned_m8b = {
            "observed_evidence": ["old recorded observation"],
            "negative_probe_observations": ["old recorded negative probe"],
            "failing_or_missing_probes": ["old recorded missing probe"],
            "custom_compact_summary": {"note": "unlisted summary field still rides"},
            "transition_concern_evidence": {
                "concern_ref": concern_ref_m8b,
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [supporting_ref_m8b, broken_citation_m8b],
                "related_boundary_refs": ["brick:mail-old-shape-target"],
            },
            "not_proven": ["semantic correctness"],
        }
        (source_dir_m8b / "step-output.json").write_text(
            json.dumps({"returned": returned_m8b}, ensure_ascii=False),
            encoding="utf-8",
        )
        (source_dir_m8b / "transition-concern.json").write_text(
            json.dumps(
                {
                    "transition_concern_ref": "transition-concern:mail-old-shape:attempt-1",
                    "step_output_ref": source_step_ref_m8b,
                    "transition_concern_returned": returned_m8b[
                        "transition_concern_evidence"
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        entry_m8b, hold_m8b = _live_concern_mail_from_ledger(
            building_root=building_m8b,
            source_step_ref=source_step_m8b,
            source_brick_ref=source_brick_m8b,
            source_attempt_index=1,
            adopted_concern=returned_m8b["transition_concern_evidence"],
        )
        if hold_m8b or not isinstance(entry_m8b, Mapping):
            violations.append(
                "mail-8b: old-shape citation row caused a whole-reroute HOLD "
                f"instead of quarantining the citation ({hold_m8b})"
            )
        else:
            expected_concern_doc_m8b = (
                f"work/step-outputs/{source_step_m8b}-attempt-1/transition-concern.json"
            )
            if entry_m8b.get("concern_doc_ref") != expected_concern_doc_m8b:
                violations.append(
                    "mail-8b: concern_doc_ref was not guaranteed in runtime mail "
                    f"({entry_m8b.get('concern_doc_ref')!r})"
                )
            if entry_m8b.get("reason_refs") != [supporting_ref_m8b]:
                violations.append(
                    "mail-8b: runtime mail did not keep only resolvable reason_refs "
                    f"({entry_m8b.get('reason_refs')!r})"
                )
            if entry_m8b.get("undelivered_citation_refs") != [broken_citation_m8b]:
                violations.append(
                    "mail-8b: broken citation was not recorded separately "
                    f"({entry_m8b.get('undelivered_citation_refs')!r})"
                )
            if broken_citation_m8b in json.dumps(
                entry_m8b.get("reason_refs", []), ensure_ascii=False
            ):
                violations.append("mail-8b: broken citation was still delivered")
            summaries_m8b = entry_m8b.get("recorded_summary_fields")
            if not isinstance(summaries_m8b, Mapping):
                violations.append("mail-9: recorded summary fields did not ride")
            else:
                for key_m8b in (
                    "observed_evidence",
                    "negative_probe_observations",
                    "failing_or_missing_probes",
                    "not_proven",
                ):
                    if key_m8b not in summaries_m8b:
                        violations.append(
                            f"mail-9: recorded summary field {key_m8b!r} did not ride"
                        )
                if "custom_compact_summary" not in summaries_m8b:
                    violations.append(
                        "mail-9: unlisted recorded compact summary field did not ride"
                    )
                if "transition_concern_evidence" in summaries_m8b:
                    violations.append(
                        "mail-9: paper1 transition_concern_evidence schema was merged "
                        "into paper2 summary fields"
                    )

    # mail-6 (FIX 2 eligibility creep + FIX 3 replay provenance, 0611): ONLY a
    # disposition row addressed to THE CURRENT hold is THIS resume's row. After
    # a first raise-resume of the same target, the ledger carries same-target
    # disposition-shaped rows (the recorded resumed lifecycle of the OLD
    # resume); a second resume must SKIP them -- with no row for the current
    # hold it fails closed loudly; with one, only its addresses board and the
    # delivered provenance discriminator replays to that exact row.
    mail6_stale_marker = "observation:mail-repair-stale-from-old-resume"
    mail6_new_marker = "observation:mail-repair-current-hold-disposition"
    plan_m6, b2_m6 = _checker_plan("bapr-mail-6-stale", budget=1)
    callable_m6 = _reroute_callable(
        b2_m6,
        {
            "brick-bapr-mail-6-stale-design",
            "brick-bapr-mail-6-stale-review",
            "brick-bapr-mail-6-stale-close",
        },
    )
    with checker_temp_path("bp-bapr-mail-6-") as tmp:
        res_m6 = run_building_plan(
            plan_m6,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m6},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m6 = res_m6.lifecycle_write.root
        _plan_evidence_m6, evidence_m6 = _mail_plan_evidence(root_m6)
        if not evidence_m6.get("held"):
            violations.append("mail-6: setup did not produce the FIRST budget HOLD")
        hold_a_identity_m6 = (
            _hold_identity_ref(evidence_m6["hold"]) if evidence_m6.get("held") else ""
        )
        _append_disposition_row(
            root_m6,
            building_id=res_m6.building_id,
            pending_target_ref=b2_m6,
            action="raise",
            author_ref="coo:smith",
            budget_increment=1,
            reason_refs=[mail6_stale_marker],
        )
        try:
            resume_building_plan(
                root_m6,
                local_callables={"callable:local:agent-invoke0-smoke": callable_m6},
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        except ValueError as exc:
            violations.append(f"mail-6: first raise resume crashed: {exc}")
        _plan_evidence2_m6, evidence2_m6 = _mail_plan_evidence(root_m6)
        if not evidence2_m6.get("held"):
            violations.append(
                "mail-6: setup did not reach a SECOND hold of the same target "
                "after the first resume"
            )
        else:
            hold_b_identity_m6 = _hold_identity_ref(evidence2_m6["hold"])
            if hold_b_identity_m6 == hold_a_identity_m6:
                violations.append(
                    "mail-6: setup invalid -- the second hold's identity did not "
                    "differ from the first"
                )
            # FIX 2 (0611, raise-generation attempt axis): landings ACCUMULATE
            # across raise generations, so the walk-1 hold has attempt N and the
            # walk-2 hold for the same target has attempt N+1 -- and the hold
            # identity must EMBED that attempt_number (the disposition row
            # echoes the identity string, so matching requires the attempt to
            # match too). Pin both: the accumulation AND the embedding.
            attempt_a_m6 = evidence_m6["hold"].get("attempt_number") if evidence_m6.get("held") else None
            attempt_b_m6 = evidence2_m6["hold"].get("attempt_number")
            if (
                not isinstance(attempt_a_m6, int)
                or not isinstance(attempt_b_m6, int)
                or attempt_b_m6 != attempt_a_m6 + 1
            ):
                violations.append(
                    "mail-6: raise-generation attempt_number did not accumulate "
                    f"(walk-1 hold attempt={attempt_a_m6!r}, walk-2 hold "
                    f"attempt={attempt_b_m6!r}; expected N and N+1)"
                )
            if (
                f"-attempt-{attempt_a_m6}" not in hold_a_identity_m6
                or f"-attempt-{attempt_b_m6}" not in hold_b_identity_m6
            ):
                violations.append(
                    "mail-6: the hold identity does not embed attempt_number "
                    "(FIX 2: the disposition row must echo the attempt; a stale "
                    "attempt-N row must not be able to match an attempt-N+1 hold)"
                )
            # (i) operator repro now BLOCKED: the ledger still carries
            # same-target disposition-shaped rows from the OLD resume (the
            # stamped resumed-lifecycle row survives the rewrite), and we ALSO
            # write an EXPLICIT human-authored STALE row addressed to the OLD
            # hold's attempt-N identity. With NO row addressed to the CURRENT
            # (attempt-N+1) hold the resume must fail closed -- the stale
            # attempt-N row must NOT be selected.
            _append_disposition_row(
                root_m6,
                building_id=res_m6.building_id,
                pending_target_ref=b2_m6,
                action="raise",
                author_ref="coo:smith",
                budget_increment=1,
                reason_refs=[mail6_stale_marker],
                resumed_from_ref=hold_a_identity_m6,
            )
            stale_resume_blocked_m6 = False
            try:
                resume_building_plan(
                    root_m6,
                    local_callables={"callable:local:agent-invoke0-smoke": callable_m6},
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                if "no human/COO disposition row found" in str(exc):
                    stale_resume_blocked_m6 = True
                else:
                    violations.append(
                        f"mail-6: stale-row resume failed with an unexpected error: {exc}"
                    )
            if not stale_resume_blocked_m6:
                violations.append(
                    "mail-6: a resume with only STALE same-target rows did not fail "
                    "closed (a previous resume's row was accepted as THIS resume's)"
                )
            # (ii) a row addressed to the CURRENT hold boards -- and ONLY it.
            _append_disposition_row(
                root_m6,
                building_id=res_m6.building_id,
                pending_target_ref=b2_m6,
                action="raise",
                author_ref="coo:smith",
                budget_increment=1,
                reason_refs=[mail6_new_marker],
            )
            ledger_snapshot_m6 = (root_m6 / "raw" / "link.jsonl").read_text(
                encoding="utf-8"
            )
            resume_captures_m6: list[dict[str, Any]] = []

            def _resume_capture_callable_m6(request: Any) -> Mapping[str, Any]:
                resume_captures_m6.append(
                    {
                        "brick_instance_ref": request.brick_instance_ref,
                        "link_handoff_refs": json.loads(
                            json.dumps(request.link_handoff_refs, default=str)
                        ),
                    }
                )
                return callable_m6(request)

            try:
                resume_building_plan(
                    root_m6,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _resume_capture_callable_m6
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                violations.append(f"mail-6: current-hold raise resume crashed: {exc}")
            else:
                disposition_entries_m6 = [
                    entry
                    for capture in resume_captures_m6
                    if capture["brick_instance_ref"] == b2_m6
                    for entry in capture["link_handoff_refs"].get("runtime_handoffs", [])
                    if entry.get("row_kind") == "resume_disposition"
                ]
                if not disposition_entries_m6:
                    violations.append(
                        "mail-6: the CURRENT hold's disposition mail did not ride to "
                        "the re-adopted redo landing"
                    )
                else:
                    entry_m6 = disposition_entries_m6[0]
                    if mail6_new_marker not in entry_m6.get("reason_refs", []):
                        violations.append(
                            "mail-6: the CURRENT hold's disposition address did not arrive"
                        )
                    if mail6_stale_marker in entry_m6.get("reason_refs", []):
                        violations.append(
                            "mail-6: a STALE previous-resume address boarded the mail "
                            "(THIS-resume-only violated)"
                        )
                    provenance_m6 = entry_m6.get("provenance")
                    provenance_m6 = (
                        provenance_m6 if isinstance(provenance_m6, Mapping) else {}
                    )
                    if (
                        provenance_m6.get("disposition_row_paused_at_ref")
                        != hold_b_identity_m6
                    ):
                        violations.append(
                            "mail-6: provenance does not carry the CURRENT hold identity"
                        )
                    # FIX 3 (0611): replay via the LIVE selection function over
                    # the pre-resume snapshot; it must land on the row carrying
                    # the CURRENT marker, and the discriminator it reports must
                    # equal BOTH the delivered provenance and the provenance
                    # PERSISTED in the written resume observation.
                    oracle_m6 = _mail_disposition_selection_replay(
                        ledger_snapshot_m6, dict(evidence2_m6["hold"])
                    )
                    oracle_prov_m6 = (
                        oracle_m6.get("selected_row_provenance")
                        if isinstance(oracle_m6, Mapping)
                        else None
                    )
                    if (
                        not isinstance(oracle_prov_m6, Mapping)
                        or any(
                            oracle_prov_m6.get(key) != provenance_m6.get(key)
                            for key in _mail_provenance_keys
                        )
                        or mail6_new_marker not in list(oracle_m6.get("reason_refs", []))
                    ):
                        violations.append(
                            "mail-6: replaying the recorded selection rule (live "
                            "_read_disposition_row over the pre-resume snapshot) did "
                            "not land on the SAME recorded row deterministically"
                        )
                    _plan_after_m6, evidence_after_m6 = _mail_plan_evidence(root_m6)
                    persisted_obs_m6 = [
                        obs
                        for obs in evidence_after_m6.get("resume_observations", [])
                        if isinstance(obs, Mapping)
                    ]
                    persisted_prov_m6 = (
                        persisted_obs_m6[-1].get("disposition_row_provenance")
                        if persisted_obs_m6
                        else None
                    )
                    if not isinstance(persisted_prov_m6, Mapping) or any(
                        persisted_prov_m6.get(key) != provenance_m6.get(key)
                        for key in _mail_provenance_keys
                    ):
                        violations.append(
                            "mail-6: the PERSISTED resume observation does not carry "
                            "the selected row's disposition_row_provenance"
                        )
                if any(
                    mail6_stale_marker in json.dumps(c["link_handoff_refs"])
                    for c in resume_captures_m6
                ):
                    violations.append(
                        "mail-6: the stale marker leaked into a resume agent input"
                    )

    # mail-7 (FIX 2, 0611 hold-identity collision -- codex re-review BLOCKER,
    # END-TO-END collision construction on the real engine): the
    # adoption_sequence_number RESETS to 0 on every walk, so a FORWARD
    # disposition chain constructs two holds for the SAME target at the SAME
    # sequence position in different walk generations: walk-1 budget-holds at
    # seq N when a non-target source exhausts the target budget; the human authors
    # FORWARD; the resumed walk forwards past that occurrence WITHOUT a
    # sequence increment, and a later declared non-target source then re-holds the
    # same exhausted target at seq N again. Operator-reproduced 0611 on the
    # real engine: under the bare reroute_ref identity the colliding pair also
    # shares attempt_number (no adoption between them -- landings unchanged),
    # and the STALE stamped forward row of resume-1 (which survives in the
    # REWRITTEN raw/link.jsonl) was SELECTED as the current hold's disposition
    # with NO new human row: a prior generation's human decision silently
    # boarded the current hold. The fixed identity embeds the held occurrence
    # (source_step_ref + cascade_depth + attempt_number), which discriminates
    # the pair (depth 1 vs 0); the stale row must now select NOTHING and the
    # resume must fail closed LOUDLY.
    plan_m7, b2_m7 = _checker_plan("bapr-mail-7-collide", budget=1)
    callable_m7 = _reroute_callable(
        b2_m7,
        {
            "brick-bapr-mail-7-collide-design",
            "brick-bapr-mail-7-collide-review",
            "brick-bapr-mail-7-collide-close",
        },
    )
    with checker_temp_path("bp-bapr-mail-7-") as tmp:
        res_m7 = run_building_plan(
            plan_m7,
            output_root=tmp,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": callable_m7},
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root_m7 = res_m7.lifecycle_write.root
        _plan_evidence_m7, evidence_m7 = _mail_plan_evidence(root_m7)
        if not evidence_m7.get("held"):
            violations.append("mail-7: setup did not produce the FIRST budget HOLD")
        else:
            hold_a_m7 = dict(evidence_m7["hold"])
            _append_disposition_row(
                root_m7,
                building_id=res_m7.building_id,
                pending_target_ref=b2_m7,
                action="forward",
                author_ref="coo:smith",
            )
            try:
                resume_building_plan(
                    root_m7,
                    local_callables={"callable:local:agent-invoke0-smoke": callable_m7},
                    adapter_cwd=repo,
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                violations.append(f"mail-7: forward resume crashed: {exc}")
            _plan_evidence2_m7, evidence2_m7 = _mail_plan_evidence(root_m7)
            if not evidence2_m7.get("held"):
                violations.append(
                    "mail-7: setup did not reach the SECOND same-target hold after "
                    "the forward resume"
                )
            else:
                hold_b_m7 = dict(evidence2_m7["hold"])
                # Setup-validity pins: this case exists to construct the EXACT
                # collision the bare identity could not survive -- same
                # sequence position, same target, same attempt_number across
                # generations. If the engine ever stops producing it, this
                # case must say so instead of silently degenerating.
                if (
                    hold_b_m7.get("adoption_sequence_number")
                    != hold_a_m7.get("adoption_sequence_number")
                    or hold_b_m7.get("target_brick") != hold_a_m7.get("target_brick")
                    or hold_b_m7.get("attempt_number") != hold_a_m7.get("attempt_number")
                ):
                    violations.append(
                        "mail-7: setup no longer constructs the cross-generation "
                        "collision (same seq + same target + same attempt expected; "
                        f"got seq {hold_a_m7.get('adoption_sequence_number')!r}/"
                        f"{hold_b_m7.get('adoption_sequence_number')!r}, attempt "
                        f"{hold_a_m7.get('attempt_number')!r}/"
                        f"{hold_b_m7.get('attempt_number')!r})"
                    )
                if _hold_identity_ref(hold_a_m7) == _hold_identity_ref(hold_b_m7):
                    violations.append(
                        "mail-7: the two same-seq cross-generation holds share ONE "
                        "identity (FIX 2 regressed: the identity does not embed the "
                        "held occurrence; a stale prior-resume row can match the "
                        "current hold)"
                    )
                # (i) the STALE stamped forward row of resume-1 (still in the
                # rewritten ledger, addressed to hold-A's identity) must select
                # NOTHING for hold-B -- first at the live selection function...
                stale_selected_m7 = _live_read_disposition_row(root_m7, hold_b_m7)
                if stale_selected_m7 is not None:
                    violations.append(
                        "mail-7: _read_disposition_row SELECTED the stale prior-"
                        "generation forward row for the current hold (hold-identity "
                        "collision: a previous resume's human decision boarded)"
                    )
                # ...and end-to-end: the resume verb must fail closed LOUDLY.
                stale_resume_blocked_m7 = False
                try:
                    resume_building_plan(
                        root_m7,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": callable_m7
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=30,
                    )
                except ValueError as exc:
                    if "no human/COO disposition row found" in str(exc):
                        stale_resume_blocked_m7 = True
                    else:
                        violations.append(
                            "mail-7: stale-row resume failed with an unexpected "
                            f"error: {exc}"
                        )
                if not stale_resume_blocked_m7:
                    violations.append(
                        "mail-7: a resume over ONLY a stale prior-generation row did "
                        "not fail closed (the stale disposition was applied to the "
                        "current hold)"
                    )
                # (ii) GOOD PATH at the selection seam: a fresh human row
                # addressed to the CURRENT hold's identity is selected -- the
                # guard discriminates generations, it does not block resumes.
                # (The full forward-generation walk continuation is pinned by
                # fc-gap6/mail-6; this case is selection-level proof over the
                # cross-generation same-target collision.)
                mail7_new_marker = "observation:mail-repair-current-generation-row"
                _append_disposition_row(
                    root_m7,
                    building_id=res_m7.building_id,
                    pending_target_ref=b2_m7,
                    action="forward",
                    author_ref="coo:smith",
                    reason_refs=[mail7_new_marker],
                )
                good_selected_m7 = _live_read_disposition_row(root_m7, hold_b_m7)
                if (
                    good_selected_m7 is None
                    or mail7_new_marker not in list(good_selected_m7.get("reason_refs", []))
                    or good_selected_m7.get("selected_row_provenance", {}).get(
                        "disposition_row_paused_at_ref"
                    )
                    != _hold_identity_ref(hold_b_m7)
                ):
                    violations.append(
                        "mail-7: a fresh row addressed to the CURRENT hold identity "
                        "was not selected (over-tightened: the generation guard "
                        "blocks legitimate dispositions)"
                    )

    # Invariant I (ζ7 source guard): the dynamic walker authors no route/Movement.
    walker_src = (repo / "support" / "operator" / "dynamic_walker.py").read_text(encoding="utf-8")
    if "support authors no route or Movement" not in walker_src:
        violations.append("zeta7: dynamic_walker.py is missing the support-authors-no-route boundary statement")
    for forbidden in ('author_ref = "support:', "author_ref = 'support:"):
        if forbidden in walker_src:
            violations.append("zeta7: dynamic_walker.py authors a support: route author_ref")

    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0 "
            "dynamic walker invariants; it does not prove source truth, Movement, "
            "success, or quality."
        )
    )
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = _repo_root_from_arg(args.repo)
    try:
        violations = check(repo)
    except Exception as exc:  # noqa: BLE001 - surface any walk failure as a rejection
        print(f"bounded agent-proposed routing loop checker rejected: {exc}", file=sys.stderr)
        return 1
    if violations:
        print("bounded agent-proposed routing loop checker rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "proof limit: support evidence only; this checker does not prove "
            "source truth, Movement authority, success, or quality.",
            file=sys.stderr,
        )
        return 1
    print(
        "bounded agent-proposed routing loop passed: dynamic walker adopted a "
        "gate-adopted agent-proposed reroute within the per-node budget, HELD on "
        "exhaustion (disposition_required), shared the node budget across multiple "
        "non-self same-target landings, walked B3 fan-out/fan-in serially over adapter:local evidence, "
        "paused on a held fan-in source, kept no-disposition resume paused, rejected "
        "support-authored disposition, resumed a budget HOLD from human/COO raise "
        "+ budget_increment, covered B5 full-chain replay / human-gate pause / "
        "nested different-node budget / no-target walk-on / monotonic "
        "no-judgment records / self-reroute walk-on / invalid-concern paused "
        "frontier over adapter:local "
        "deterministic fixtures, proved P6-C pool=1 vs pool=4 normalized "
        "evidence parity for independent fan-out and shared fan-in reroute "
        "fixtures with an arrival-order RED probe, proved P4 resume replay stays "
        "serial until the held disposition and then recovers live fan-out "
        "parallelism, proved onboard approve C-2 adapter_cwd/timeout "
        "forwarding + coo forward disposition handoff + fail-closed RED cases, persisted "
        "human/COO reroute disposition target selection from an ambiguous HOLD "
        "(declared non-source target replays; self/boundary/undeclared targets reject), "
        "node_reroute_budgets and route_replay_plan.max_attempts as Link Carry "
        "budget evidence, delivered the MAIL-REPAIR (0611) runtime mail (mail-1 "
        "gate-adopted concern reason_refs arrive in every redo input with recorded "
        "provenance, guaranteed concern_doc_ref, compact recorded summaries, and "
        "AgentReceipt received_handoff_refs; mail-2 broken ledger "
        "address HOLDs loudly; mail-3 declared-only mailbox keeps the declared "
        "routing body byte-identical after normalizing support-only step-output metadata; mail-4 raise-resume disposition reason_refs ride to "
        "the re-adopted landing with row-specific replay provenance PERSISTED "
        "in the written resume observation (the live _read_disposition_row "
        "replay oracle lands on the same row); mail-5 "
        "step-output addresses stay contained in THIS Building's "
        "work/step-outputs subtree -- ..-escaping, absolute, case-varied "
        "(mail-5d case-bypass), non-contiguously spelled (mail-5e "
        "containment-by-resolution, spelling-independent), AND "
        "symlinked-ledger-root (mail-5f trusted-intermediate symlink: "
        "containment anchored on the resolved BUILDING root, never a resolved "
        "ledger subtree; mail-5g in-building detour: an in-root resolution "
        "OUTSIDE work/step-outputs stays unresolved) forms HOLD while a "
        "weird-but-contained spelling still rides; "
        "mail-8 rejects malformed new reason_ref address syntax while mail-8b/mail-9 "
        "quarantine old recorded citation refs without delivering them and carry "
        "recorded paper2 summary fields beside paper1; "
        "mail-6 only the CURRENT hold's disposition row boards, stale "
        "previous-resume rows incl. an explicit stale attempt-N row are "
        "skipped fail-closed and the hold identity embeds the accumulating "
        "attempt_number; mail-7 a cross-generation same-seq/same-attempt hold "
        "collision (forward chain) no longer lets a stale prior-generation row "
        "board -- the occurrence-qualified identity discriminates and the "
        "resume fails closed loudly), and authored no route or Movement."
    )
    print(
        "proof limit: support evidence only; checker pass does not prove source "
        "truth, success judgment, quality judgment, Movement authority, real "
        "provider parallel execution, or full process integrity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
