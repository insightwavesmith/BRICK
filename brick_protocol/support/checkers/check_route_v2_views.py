#!/usr/bin/env python3
"""Checker for Route V2 read-only view builder."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.operator.route_v2_views import (  # noqa: E402
    route_v2_policy_packet,
    render_route_v2_view,
)


def _load_yaml_minimal(path: Path) -> dict[str, Any]:
    # The checked route policy is intentionally simple; keep this checker narrow
    # and avoid introducing a new dependency.
    import yaml  # type: ignore[import-not-found]

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"YAML root is not a mapping: {path}")
    return data


def run(repo: Path) -> str:
    from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS

    policy = _load_yaml_minimal(repo / "brick_protocol/link/route_policies/basic_qa_repair.yaml")
    impl_view = render_route_v2_view(
        transition_concern_evidence={
            "concern_ref": "transition-concern:route-v2-view-implementation-gap",
            "concern_kind": "implementation_gap",
            "binding": False,
            "reason_refs": ["observation:route-v2-view-implementation-gap"],
            "related_boundary_refs": ["brick-work"],
        },
        route_policy=policy,
        declared_route_replay_plan={
            "route_replay_ref": "route-replay:route-v2-view-implementation-gap",
            "author_ref": "coo:route-v2-view-checker",
            "authoring_basis_refs": ["observation:route-v2-view-checker"],
            "immediate_target_ref": "brick-work",
            "source_brick_refs": ["brick-qa"],
            "affected_downstream_refs": ["brick-qa"],
            "replay_segment_refs": ["brick-work", "brick-qa"],
            "max_attempts": 1,
        },
        gate_state="paused",
        movement_candidate="reroute",
        delta_qa_fact={
            "made_changes": True,
            "changed_files": ["brick_protocol/support/operator/route_v2_views.py"],
            "diff_refs": ["observation:route-v2-view-diff"],
            "evidence_refs": ["observation:route-v2-view-checker"],
        },
    )
    if impl_view["sealed_concern_kind_observation"]["concern_kind"] != "implementation_gap":
        raise AssertionError("implementation_gap concern kind not preserved")
    if impl_view["route_policy_eligibility_observation"].get("requested_route_scope") != "implementation_only":
        raise AssertionError("implementation_gap did not match implementation_only route scope")
    if impl_view["materialization_view"].get("materialized") is not True:
        raise AssertionError("existing route materialization view did not materialize implementation_gap")
    if impl_view["movement_candidate"] != "reroute" or impl_view["gate_state"] != "paused":
        raise AssertionError("gate_state and movement_candidate not preserved separately")
    if "movement" in impl_view:
        raise AssertionError("Route V2 view must not author a movement field")

    verification_view = render_route_v2_view(
        transition_concern_evidence={
            "concern_ref": "transition-concern:route-v2-view-verification-gap",
            "concern_kind": "verification_gap",
            "binding": False,
            "reason_refs": ["observation:route-v2-view-verification-gap"],
            "related_boundary_refs": ["building-boundary:verification-gap"],
        },
        route_policy=policy,
        gate_state="held_for_coo_review",
        movement_candidate="",
    )
    if verification_view["sealed_concern_kind_observation"]["non_reroute"] is not True:
        raise AssertionError("verification_gap must be observed as non_reroute")
    if verification_view["route_policy_eligibility_observation"]["eligible"] is not False:
        raise AssertionError("verification_gap must not be reroute eligible")
    if verification_view["materialization_view"] is not None:
        raise AssertionError("verification_gap view without replay plan should not materialize")

    policy_packet = route_v2_policy_packet()
    if sorted(policy_packet["allowed_concern_kinds"]) != sorted(TRANSITION_CONCERN_KINDS):
        raise AssertionError("policy packet concern kinds drifted from Agent source")
    if "brick_protocol/support/operator/walker_kernel.py" not in policy_packet["forbidden_surfaces"]:
        raise AssertionError("policy packet lost walker forbidden surface")

    for bad in (
        {"movement": "reroute"},
        {"success": True},
        {"route_target": "brick-work"},
    ):
        payload = {
            "concern_ref": "transition-concern:route-v2-view-bad",
            "concern_kind": "implementation_gap",
            "binding": False,
            "reason_refs": ["observation:bad"],
            **bad,
        }
        try:
            render_route_v2_view(transition_concern_evidence=payload)
        except ValueError:
            pass
        else:
            raise AssertionError(f"forbidden payload key accepted: {bad}")

    return "route_v2_views passed: implementation_gap materialization view, verification_gap non-reroute view, gate/movement separation, delta-QA preservation, and forbidden key probes inspected"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(_REPO_ROOT))
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    print(run(repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
