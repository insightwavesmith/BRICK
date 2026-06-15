#!/usr/bin/env python3
"""Check BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0 dynamic walker invariants.

This checker is support evidence only. It does not choose Movement, author a
route, judge success or quality, schedule, retry, or call providers. It runs the
admitted dynamic graph walker (support/operator/dynamic_walker.py) over adapter:
local fixtures (NO codex/claude/gemini) and asserts the bounded-routing-loop
invariants the amendment locks:

- the reroute budget is per-TARGET-Brick (node), Link-assigned, SHARED across all
  reroute-landings on that node (outer AND nested); a nested landing draws the
  same node budget (no fresh per-event budget);
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
import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _repo_root_from_arg(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_import_path(repo: Path) -> None:
    import_identity = repo / "support" / "import_identity"
    for entry in (str(import_identity), str(repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


# ---- adapter:local fixture builders (no providers) ----

def _brick_step(step_ref: str, brick_ref: str, agent_ref: str, completion_edge_ref: str) -> Mapping[str, Any]:
    return {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{step_ref}",
                "brick_work_ref": f"work:{step_ref}",
                "brick_instance_ref": brick_ref,
                "work_statement": f"Declared work for {step_ref}.",
                "comparison_rule": "Observe support evidence only; do not choose Movement or judge quality.",
                "required_return_shape": "observed_evidence, not_proven",
                "source_facts": ["AGENTS.md", "support/operator/dynamic_walker.py"],
            },
            {"axis": "Agent", "row_ref": f"agent-row:{step_ref}", "agent_object_ref": agent_ref},
        ],
    }


def _fwd_edge(edge_ref: str, src: str, tgt_step: str, tgt_brick: str, gate: list[str] | None = None) -> Mapping[str, Any]:
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{edge_ref}",
        "movement": "forward",
        "target_ref": tgt_brick,
    }
    if gate is not None:
        link_row["declared_gate_refs"] = gate
    return {"edge_ref": edge_ref, "source_step_ref": src, "target_step_ref": tgt_step, "rows": [link_row]}


def _close_edge(edge_ref: str, src: str, reason: str, boundary: str) -> Mapping[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source_step_ref": src,
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{edge_ref}",
                "movement": "forward",
                "building_lifecycle": {"state": "closed", "reason": reason},
                "target_ref": boundary,
            }
        ],
    }


def _proof_limits() -> list[str]:
    return [
        "support evidence only",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]


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


def _multi_ref_concern_callable(source_brick: str, related_boundary_refs: list[str]):
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
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": list(related_boundary_refs),
            }
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
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{edge_ref}",
        "movement": "reroute",
        "target_ref": tgt_brick,
        "route_replay_plan": dict(route_replay_plan),
    }
    if gate is not None:
        link_row["declared_gate_refs"] = gate
    return {"edge_ref": edge_ref, "source_step_ref": src, "target_step_ref": tgt_step, "rows": [link_row]}


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
            rows[0].pop("declared_gate_refs", None)
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

    with tempfile.TemporaryDirectory(prefix="bp-bapr-loop0-") as tmp:
        result = run_building_plan(
            plan,
            output_root=Path(tmp),
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
    with (building_root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def check(repo: Path) -> list[str]:
    _ensure_import_path(repo)
    violations: list[str] = []

    # G5-1: run_building_plan has no walker_mode parameter and always enters the
    # dynamic graph walker.
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.operator.building_operation import observe_building_frontier

    auto_prefix = "bapr-loop0-g5-1-auto-graph"
    auto_graph_plan, auto_graph_target = _checker_plan(auto_prefix, budget=2)
    with tempfile.TemporaryDirectory(prefix="bp-bapr-g5-1-auto-") as tmp:
        auto_graph_result = run_building_plan(
            auto_graph_plan,
            output_root=Path(tmp),
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
        _reroute_callable(b2_b, {"brick-bapr-loop0-hold-review", b2_b}),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-b4-g5-") as tmp:
        res_g5 = run_building_plan(
            plan_g5,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-b4-g6-") as tmp:
        res_g6 = run_building_plan(
            plan_g6,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-b4-g7-forward-") as tmp:
        fake_repo = Path(tmp) / "repo"
        output_root_g7_forward = fake_repo / "project" / "brick-protocol" / "buildings"
        output_root_g7_forward.mkdir(parents=True)
        res_g7_forward = run_building_plan(
            plan_g7_forward,
            output_root=output_root_g7_forward,
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _reroute_callable(
                    b2_g7_forward,
                    {"brick-bapr-loop0-b4-forward-disposition-review", b2_g7_forward},
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
                    {"brick-bapr-loop0-b4-forward-disposition-review", b2_g7_forward},
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-b4-g7-") as tmp:
        callable_g7 = _reroute_callable(
            b2_g7,
            {"brick-bapr-loop0-b4-raise-resume-review", b2_g7},
        )
        res_g7 = run_building_plan(
            plan_g7,
            output_root=Path(tmp),
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

    # Invariant C: nested reroute landing on the SAME node draws the SAME shared
    # budget (no fresh budget) and the cascade is bounded.
    plan_c, b2_c = _checker_plan("bapr-loop0-nested", budget=2)
    res_c, fr_c, rec_c = _run(
        plan_c,
        _reroute_callable(b2_c, {"brick-bapr-loop0-nested-review", b2_c}),
        repo,
    )
    adopted_c = [r for r in rec_c if not r.get("disposition_required")]
    held_c = [r for r in rec_c if r.get("disposition_required")]
    if not all(r.get("target_brick") == b2_c for r in rec_c):
        violations.append("nested-case: a landing targeted a node other than the shared-budget node")
    if not any(r.get("cascade_depth", 0) >= 2 for r in adopted_c):
        violations.append("nested-case: no nested (cascade_depth>=2) landing observed")
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
    res_c3, fr_c3, rec_c3 = _run(
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

    with tempfile.TemporaryDirectory(prefix="bp-onboard-approve-fire-") as tmp:
        sandbox = Path(tmp).resolve()
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
            with tempfile.TemporaryDirectory(prefix="bp-onboard-approve-red-") as tmp_red:
                return run_approve_entry(Path(tmp_red) / "building", repo_root=repo)
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
    with tempfile.TemporaryDirectory(prefix="bp-onboard-approve-budget-red-") as tmp_budget_red:
        budget_red_oa = run_approve_entry(
            Path(tmp_budget_red) / "building",
            action="forward",
            budget_increment=1,
            repo_root=repo,
        )
    if budget_red_oa.get("error_kind") != "invalid_budget_increment":
        violations.append("onboard-approve-fire: forward + budget_increment was not rejected")
    complete_oa = _approve_with_frontier({"frontier_kind": "complete"})
    if complete_oa.get("ok") is not True or complete_oa.get("disposition_written") is not False:
        violations.append("onboard-approve-fire: complete frontier was not treated as no-op")

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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-knot4-resume-nonreroute-") as tmp_nr:
        res_nr_resume = run_building_plan(
            plan_nr_resume,
            output_root=Path(tmp_nr),
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
    res_invalid, fr_invalid, rec_invalid = _run(
        plan_invalid,
        _invalid_concern_callable("brick-bapr-loop0-invalid-concern-review", b2_invalid),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-adapter-frontier-") as tmp:
        tmp_path = Path(tmp)
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
                f"knot3-cohort-d ({label}): sibling appears in BOTH replay and skipped "
                f"(replay={xv_replay}, skipped={xv_skipped})"
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-knot3-cohort-e-") as tmp_e:
        # join proposes a reroute onto lane-a on every call: the FIRST landing
        # adopts (budget 1 consumed) and triggers the cohort LIVE (lane-b
        # re-verified, lane-c vouched-skipped, join re-runs); the SECOND proposal
        # HOLDs on budget exhaustion. A HUMAN forward disposition then resumes.
        callable_e = _reroute_callable(lane_a_e, {join_e})
        res_e = run_building_plan(
            plan_cohort_e,
            output_root=Path(tmp_e),
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
        (the re-walk landing) proposes reroute->lane-a on its 2nd call so the
        landing HOLDs on budget exhaustion BEFORE the cohort runs. The re-run join
        on resume (its 2nd call) is CLEAN so the building can complete."""

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
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                    "related_boundary_refs": [lane_a_f],
                }
            return returned

        return _callable

    with tempfile.TemporaryDirectory(prefix="bp-bapr-knot3-cohort-f-") as tmp_f:
        callable_f = _hold_before_cohort_callable()
        res_f = run_building_plan(
            plan_cohort_f,
            output_root=Path(tmp_f),
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
        lane-a (the re-walk landing) proposes reroute -> lane-a on its 2nd call so
        the landing HOLDs on budget exhaustion BEFORE the cohort + joins run."""

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
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                    "related_boundary_refs": [lane_a_g],
                }
            return returned

        return _callable

    with tempfile.TemporaryDirectory(prefix="bp-bapr-knot3-cohort-g-") as tmp_g:
        callable_g = _nested_hold_before_cohort_callable()
        res_g = run_building_plan(
            plan_nested_g,
            output_root=Path(tmp_g),
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
        cb = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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
            cb = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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
        cb = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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

    # GAP 3: the resumed lifecycle must stamp the EXACT held occurrence (not a later
    # same-step_ref occurrence a raise re-adoption creates).
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap3-") as tmp:
        pfx = "bapr-loop0-fc-gap3"
        b2_3 = f"brick-{pfx}-build"
        def _setup3():
            calls = {}
            def _c(request):
                ref = request.brick_instance_ref
                calls[ref] = calls.get(ref, 0) + 1
                r = {"observed_evidence": [f"o {ref}"], "not_proven": ["x"]}
                if ref == b2_3 and calls[ref] <= 2:
                    r["transition_concern_evidence"] = {
                        "concern_ref": f"transition-concern:{ref}", "concern_kind": "implementation_gap",
                        "binding": False, "reason_refs": [f"brick-comparison:{ref}"],
                        "related_boundary_refs": [b2_3]}
                return r
            return _c
        def _live3(request):
            return {"observed_evidence": [f"o {request.brick_instance_ref}"], "not_proven": ["x"]}
        res3, _ = _build_held_fc(pfx, tmp, _setup3(), budget=1)
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
            if sr3.preparation.step_rows.step_ref != f"{pfx}-build":
                continue
            lr3 = sr3.preparation.step_rows.link_row
            tl3 = lr3.get("transition_lifecycle") if isinstance(lr3, Mapping) else None
            occ3.append((idx3, tl3.get("state") if isinstance(tl3, Mapping) else None))
        resumed_idx3 = [i for i, s in occ3 if s == "resumed"]
        if len(occ3) < 3:
            violations.append(f"fc-gap3: expected >=3 build occurrences after raise (got {occ3})")
        elif not resumed_idx3:
            violations.append(f"fc-gap3: no resumed-lifecycle stamp found ({occ3})")
        else:
            held_idx3 = occ3[1][0]   # cascade1 = the HELD occurrence
            last_idx3 = occ3[-1][0]  # cascade2 = the deeper raise re-adoption
            if resumed_idx3[0] == last_idx3 and last_idx3 != held_idx3:
                violations.append(
                    "fc-gap3: resumed lifecycle stamped the LATER same-step_ref occurrence "
                    f"(index {resumed_idx3[0]}) not the held one (index {held_idx3})")
            elif resumed_idx3[0] != held_idx3:
                violations.append(f"fc-gap3: resumed stamp on wrong occurrence (stamped {resumed_idx3}, held {held_idx3})")

    # GAP 4: a missing OR malformed re-attached budget map must FAIL CLOSED (the
    # building engaged the reroute budget mechanism).
    for gap4_mode in ("missing", "malformed"):
        with tempfile.TemporaryDirectory(prefix=f"bp-bapr-fc-gap4-{gap4_mode}-") as tmp:
            pfx = f"bapr-loop0-fc-gap4-{gap4_mode}"
            cb = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap4b-pause-") as tmp:
        pfx = "bapr-loop0-fc-gap4b-pause"
        plan4b, b2_4b = _checker_plan(pfx, budget=1)
        plan4b = _with_link_edge_gate(
            plan4b,
            f"edge:{pfx}-review-to-close",
            ["link-gate:default-transition", "link-gate:human"],
        )
        cb4b = _reroute_callable(b2_4b, {f"brick-{pfx}-review"})
        res4b = run_building_plan(
            plan4b, output_root=Path(tmp), overwrite_existing=True,
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
        cb4be = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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

    # GAP 5: a replayed step that DECLARED a gate_sequence_policy but has NO recorded
    # gate decision must FAIL CLOSED (not silently treated as no-action).
    with tempfile.TemporaryDirectory(prefix="bp-bapr-fc-gap5-") as tmp:
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
        cb5 = _reroute_callable(b2_5, {f"brick-{pfx}-review", b2_5})
        res5 = run_building_plan(
            plan5, output_root=Path(tmp), overwrite_existing=True,
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
        cb = _reroute_callable(f"brick-{pfx}-build", {f"brick-{pfx}-review", f"brick-{pfx}-build"})
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

    # ------------------------------------------------------------------
    # MAIL-REPAIR (Smith rulings 0611, B1/B2/B3): runtime rows ride the mail.
    # Ported b5b probe (measured RED 0611: in a gate-adopted dynamic reroute,
    # runtime concern.reason_refs markers arrived in 0/10 redo-worker inputs
    # while declared refs arrived in all) as an EXECUTED case family:
    #   mail-1  runtime marker ARRIVES in every redo input (and ONLY there),
    #           provenance recorded as data, packet carries ADDRESSES ONLY,
    #           receipt (B2) records the delivered addresses as fact.
    #   mail-2  broken ledger address (B1) -> HOLD loudly, nothing adopted.
    #   mail-3  declared-only plan: mailbox byte-identical to the declared
    #           assembler output; NO runtime_handoffs key (regression guard).
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

        with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-oracle-") as oracle_tmp:
            oracle_root = Path(oracle_tmp)
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
        "reason_refs",
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

    def _mail_capture_callable(source_brick: str, extra_reason_refs: list[str]):
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

    # mail-1: runtime marker arrival + provenance + addresses-only + receipt.
    plan_m1, refs_m1 = _mail_plan()
    captures_m1, callable_m1 = _mail_capture_callable(
        refs_m1["source"], [mail_runtime_marker]
    )
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-1-") as tmp:
        res_m1 = run_building_plan(
            plan_m1,
            output_root=Path(tmp),
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
                if set(entry) != _mail_entry_allowed_keys:
                    violations.append(
                        f"mail-1: runtime handoff entry keys drifted in [{i}]: {sorted(entry)} "
                        "(ADDRESSES ONLY: refs + provenance, no body/free-text fields)"
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-2-") as tmp:
        res_m2 = run_building_plan(
            plan_m2,
            output_root=Path(tmp),
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

    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-3-") as tmp:
        run_building_plan(
            plan_m3,
            output_root=Path(tmp),
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
            if json.dumps(capture["link_handoff_refs"], sort_keys=True) != json.dumps(
                declared_mailbox, sort_keys=True
            ):
                violations.append(
                    f"mail-3: declared-only mailbox [{i}] drifted from the declared "
                    "assembler output (byte-identity regression)"
                )
            if "runtime_handoffs" in capture["link_handoff_refs"]:
                violations.append(
                    f"mail-3: declared-only mailbox [{i}] grew a runtime_handoffs key"
                )

    # mail-4 (B3 lane 2): a raise-resume's human/COO disposition row reason_refs
    # ride to the re-adopted redo landing, stamped as a resume_disposition entry
    # with raw/link.jsonl provenance.
    mail_disposition_marker = "observation:mail-repair-disposition-reason-rides"
    plan_m4, b2_m4 = _checker_plan("bapr-mail-4-resume", budget=1)
    callable_m4 = _reroute_callable(
        b2_m4, {"brick-bapr-mail-4-resume-review", b2_m4}
    )
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-4-") as tmp:
        res_m4 = run_building_plan(
            plan_m4,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5a-") as tmp:
        smuggle_m5 = Path(tmp) / "other-building" / "raw" / "secret.json"
        smuggle_m5.parent.mkdir(parents=True)
        smuggle_m5.write_text("{}", encoding="utf-8")
        res_m5a = run_building_plan(
            plan_m5a,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5b-") as tmp:
        res_m5b = run_building_plan(
            plan_m5b,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5c-") as tmp:
        res_m5c = run_building_plan(
            plan_m5c,
            output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5d-") as tmp:
        smuggle_m5d = Path(tmp) / "other-building" / "raw" / "secret.json"
        smuggle_m5d.parent.mkdir(parents=True)
        smuggle_m5d.write_text("{}", encoding="utf-8")
        res_m5d = run_building_plan(
            plan_m5d,
            output_root=Path(tmp),
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
        with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5e-") as tmp:
            res_m5e = run_building_plan(
                plan_m5e,
                output_root=Path(tmp),
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5e-in-") as tmp:
        res_m5e_in = run_building_plan(
            plan_m5e_in,
            output_root=Path(tmp),
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

    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5f-") as tmp:
        building_m5f = Path(tmp) / "building"
        (building_m5f / "work").mkdir(parents=True)
        outside_m5f = Path(tmp) / "outside"
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
            real_building_m5f = Path(tmp) / "building-real"
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
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-5g-") as tmp:
        building_m5g = Path(tmp) / "building"
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
    callable_m6 = _reroute_callable(b2_m6, {"brick-bapr-mail-6-stale-review", b2_m6})
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-6-") as tmp:
        res_m6 = run_building_plan(
            plan_m6,
            output_root=Path(tmp),
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
    # seq N when the redo landing re-proposes its own node; the human authors
    # FORWARD; the resumed walk forwards past that occurrence WITHOUT a
    # sequence increment, and the DECLARED same-node step then re-holds the
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
        b2_m7, {"brick-bapr-mail-7-collide-design", b2_m7}
    )
    with tempfile.TemporaryDirectory(prefix="bp-bapr-mail-7-") as tmp:
        res_m7 = run_building_plan(
            plan_m7,
            output_root=Path(tmp),
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
                # fc-gap6/mail-6; re-walking THIS self-rerouting building after
                # a forward is a separate engine surface: a forwarded concern
                # occurrence is re-evaluated on replay, so the continued walk
                # re-holds at the OLD occurrence before reaching this one --
                # see the operator report 0611. Data: selection-level proof.)
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
        "exhaustion (disposition_required), shared the node budget across a nested "
        "landing, walked B3 fan-out/fan-in serially over adapter:local evidence, "
        "paused on a held fan-in source, kept no-disposition resume paused, rejected "
        "support-authored disposition, resumed a budget HOLD from human/COO raise "
        "+ budget_increment, covered B5 full-chain replay / human-gate pause / "
        "nested different-node budget / no-target walk-on / monotonic "
        "no-judgment records / invalid-concern paused frontier over adapter:local "
        "deterministic fixtures, proved onboard approve C-2 adapter_cwd/timeout "
        "forwarding + coo forward disposition handoff + fail-closed RED cases, persisted "
        "node_reroute_budgets and route_replay_plan.max_attempts as Link Carry "
        "budget evidence, delivered the MAIL-REPAIR (0611) runtime mail (mail-1 "
        "gate-adopted concern reason_refs arrive in every redo input with recorded "
        "provenance + AgentReceipt received_handoff_refs; mail-2 broken ledger "
        "address HOLDs loudly; mail-3 declared-only mailbox byte-identical to the "
        "declared assembler; mail-4 raise-resume disposition reason_refs ride to "
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
        "truth, success judgment, quality judgment, Movement authority, parallel "
        "execution, or full process integrity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
