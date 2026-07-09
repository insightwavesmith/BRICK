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
    PURE_DEV_D1_BUILDING_ID,
    ROUTE_V2_SHARED_CLASSIFIER_REF,
    classify_route_v2_concern_eligibility,
    route_v2_policy_packet,
    render_route_v2_view,
)

_EXPECTED_PRODUCT_BUILDING_ID = "pure-dev-d1-r5-product-land-0709b"
_EXPECTED_SHARED_HELPER_SHAPE = "shape_b_shared_helper"


def _assert_product_classifier_shape(packet: dict[str, Any]) -> None:
    if packet.get("classifier_ref") != ROUTE_V2_SHARED_CLASSIFIER_REF:
        raise AssertionError("shared classifier_ref missing or drifted")
    if packet.get("shape") != _EXPECTED_SHARED_HELPER_SHAPE:
        raise AssertionError("shared classifier shape missing or drifted")
    if packet.get("pure_dev_d1_building_id") != _EXPECTED_PRODUCT_BUILDING_ID:
        raise AssertionError("shared classifier product building id missing or drifted")


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
    from brick_protocol.support.checkers import check_bounded_agent_proposed_routing_loop0 as walker_chk
    from brick_protocol.support.operator import walker_kernel

    policy = _load_yaml_minimal(repo / "brick_protocol/link/route_policies/basic_qa_repair.yaml")
    if PURE_DEV_D1_BUILDING_ID != _EXPECTED_PRODUCT_BUILDING_ID:
        raise AssertionError("Pure-dev D1 building stamp drifted")

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
    if impl_view.get("route_v2_shape") != "shape_b_shared_helper":
        raise AssertionError("Route V2 view missing SHAPE B shared-helper marker")
    shared = impl_view.get("shared_eligibility_classification")
    if not isinstance(shared, dict) or shared.get("classifier_ref") != ROUTE_V2_SHARED_CLASSIFIER_REF:
        raise AssertionError("Route V2 view missing shared eligibility classification")
    _assert_product_classifier_shape(shared)
    direct = classify_route_v2_concern_eligibility("implementation_gap")
    _assert_product_classifier_shape(direct)
    missing_building_id = dict(direct)
    missing_building_id.pop("pure_dev_d1_building_id")
    try:
        _assert_product_classifier_shape(missing_building_id)
    except AssertionError:
        pass
    else:
        raise AssertionError("shared classifier product building id RED probe did not fail")
    if direct.get("reroute_eligible") is not True or direct.get("non_reroute") is not False:
        raise AssertionError("shared classifier implementation_gap eligibility wrong")
    if impl_view["sealed_concern_kind_observation"].get("reroute_eligible") != direct.get(
        "reroute_eligible"
    ):
        raise AssertionError("view sealed observation drifted from shared classifier")
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

    forbidden_payload_keys = (
        {"movement": "reroute"},
        {"movement_choice": "reroute"},
        {"success": True},
        {"quality": "good"},
        {"route_target": "brick-work"},
    )
    for bad in forbidden_payload_keys:
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

    for bad_gate, bad_movement in (("reroute", ""), ("paused", "paused"), ("forward", "")):
        try:
            render_route_v2_view(
                transition_concern_evidence={
                    "concern_ref": "transition-concern:route-v2-view-gate-movement-bad",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": ["observation:bad-gate-movement"],
                    "related_boundary_refs": ["brick-work"],
                },
                gate_state=bad_gate,
                movement_candidate=bad_movement,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Route V2 view accepted gate/Movement cross-over "
                f"gate_state={bad_gate!r} movement_candidate={bad_movement!r}"
            )

    from brick_protocol.support.operator.import_identity import (
        mint_official_launch_token,
        reset_official_launch_token,
    )

    plan_adopt, target_adopt = walker_chk._checker_plan(
        "route-v2-walker-advisory-adopt",
        budget=2,
    )
    source_adopt = "brick-route-v2-walker-advisory-adopt-review"
    callable_adopt = walker_chk._multi_ref_concern_callable(
        source_adopt,
        [target_adopt],
        concern_kind="implementation_gap",
    )
    original_append = walker_kernel._append_route_v2_view_observation
    launch = mint_official_launch_token()
    try:
        try:
            walker_kernel._append_route_v2_view_observation = (
                lambda observations, observation: None
            )
            without_obs, without_frontier, without_records = walker_chk._run(
                plan_adopt,
                callable_adopt,
                repo,
            )
        finally:
            walker_kernel._append_route_v2_view_observation = original_append
        with_obs, with_frontier, with_records = walker_chk._run(
            plan_adopt,
            callable_adopt,
            repo,
        )
    finally:
        reset_official_launch_token(launch)
    if without_records != with_records:
        raise AssertionError("Route V2 advisory observation changed reroute/HOLD records")
    if without_frontier.get("frontier_kind") != with_frontier.get("frontier_kind"):
        raise AssertionError("Route V2 advisory observation changed frontier kind")
    without_steps = [item.preparation.step_rows.step_ref for item in without_obs.step_results]
    with_steps = [item.preparation.step_rows.step_ref for item in with_obs.step_results]
    if without_steps != with_steps:
        raise AssertionError("Route V2 advisory observation changed walker step order")
    with_evidence = getattr(with_obs, "_dynamic_walker_evidence", {})
    observations = with_evidence.get("route_v2_view_observations")
    if not isinstance(observations, list) or len(observations) != 1:
        raise AssertionError(
            "dynamic_walker_evidence.route_v2_view_observations missing or duplicated"
        )
    observation = observations[0]
    if observation.get("kind") != "route_v2_view_observation":
        raise AssertionError("Route V2 walker observation has wrong kind")
    if observation.get("binding") != "advisory":
        raise AssertionError("Route V2 walker observation must be advisory")
    if observation.get("adopted_as_movement") is not False:
        raise AssertionError("Route V2 walker observation must not be adopted as Movement")
    if observation.get("route_policy_input_state") != "absent":
        raise AssertionError("walker silently supplied a Route V2 route policy")
    if not str(observation.get("reroute_ref", "")).startswith("reroute-adoption:"):
        raise AssertionError("adopted Route V2 observation did not carry existing reroute_ref")

    plan_vg, _target_vg = walker_chk._checker_plan(
        "route-v2-walker-advisory-vg",
        budget=1,
    )
    source_vg = "brick-route-v2-walker-advisory-vg-review"
    launch_vg = mint_official_launch_token()
    try:
        vg_result, vg_frontier, vg_records = walker_chk._run(
            plan_vg,
            walker_chk._multi_ref_concern_callable(
                source_vg,
                ["building-boundary:route-v2-walker-advisory-vg"],
                concern_kind="verification_gap",
            ),
            repo,
        )
    finally:
        reset_official_launch_token(launch_vg)
    if vg_records:
        raise AssertionError("verification_gap Route V2 observation produced reroute/HOLD records")
    if vg_frontier.get("frontier_kind") not in {"complete", "closure_pending"}:
        raise AssertionError("verification_gap Route V2 observation did not walk on")
    vg_observations = getattr(vg_result, "_dynamic_walker_evidence", {}).get(
        "route_v2_view_observations"
    )
    if not isinstance(vg_observations, list) or len(vg_observations) != 1:
        raise AssertionError("verification_gap Route V2 walker observation missing")
    vg_view = vg_observations[0].get("route_v2_view", {})
    if vg_view.get("sealed_concern_kind_observation", {}).get("non_reroute") is not True:
        raise AssertionError("verification_gap Route V2 walker view lost non_reroute")

    if "route_v2_view_observations" not in (
        repo / "brick_protocol/support/operator/walker_resume.py"
    ).read_text(encoding="utf-8"):
        raise AssertionError("walker_resume.py does not preserve route_v2_view_observations")

    if observation.get("route_v2_shape") != "shape_b_shared_helper":
        raise AssertionError("walker route_v2 observation missing SHAPE B shared-helper marker")
    if observation.get("classifier_ref") != ROUTE_V2_SHARED_CLASSIFIER_REF:
        raise AssertionError("walker route_v2 observation missing shared classifier_ref")
    return (
        "route_v2_views passed: implementation_gap materialization view, verification_gap "
        "non-reroute view, gate/movement separation, delta-QA preservation, forbidden key "
        "probes, advisory walker evidence, SHAPE B shared classifier, and byte-identical "
        "control-flow comparison"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(_REPO_ROOT))
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    print(run(repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
