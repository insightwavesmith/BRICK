"""Execute declared repair/replay Building Plans after literal route materialization.

This helper executes only a caller-supplied repair/replay Building Plan after
checking that the materialized Link row candidate points at that plan. It does
not choose Movement, invent route targets, or judge work quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.operator.plan_graph import _linear_plan_from_graph_plan
from support.operator.plan_validation import validate_declared_building_plan
from support.operator.route_materialization import materialize_route_transition
from support.operator.run import run_building_plan


PROOF_LIMITS = (
    "support evidence only",
    "predeclared repair/replay plan execution only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN = (
    "semantic correctness of repair work",
    "semantic correctness of QA replay",
    "Link decision packet as BAL fact",
    "automatic child Building generation",
)


def prepare_declared_auto_repair_replay_case(case: Mapping[str, Any], repo: Path | str) -> dict[str, Any]:
    """Validate a declared auto repair/replay case without executing it."""

    repo_path = Path(repo).resolve()
    policy = _load_mapping(repo_path, _require_text(case.get("route_policy_path"), "route_policy_path"))
    route_request = _mapping(case.get("route_request"), "route_request")
    declared_route_replay_plan = _mapping(
        case.get("declared_route_replay_plan"),
        "declared_route_replay_plan",
    )
    materialized = materialize_route_transition(route_request, policy, declared_route_replay_plan)
    if materialized.get("materialization_state") != "materialized":
        raise ValueError("auto repair/replay requires a materialized route transition")
    plan_rel = _require_text(case.get("repair_replay_plan_path"), "repair_replay_plan_path")
    plan = _load_mapping(repo_path, plan_rel)
    # P11b RUNTIME task_source_ref ENFORCEMENT: this caller already resolves the
    # repo root, so thread it to reject a declared-but-missing task_source_ref at
    # run time, matching the checker boundary.
    validate_declared_building_plan(_validation_plan(plan), repo_root=repo_path)
    plan_steps = _plan_step_refs_and_brick_instance_refs(plan)
    plan_bricks = [entry["brick_instance_ref"] for entry in plan_steps]
    target_ref = _require_text(materialized.get("target_ref"), "materialized.target_ref")
    replay_refs = materialized["link_row"]["route_replay_plan"]["replay_segment_refs"]
    declared_boundary_replay = case.get("declared_boundary_replay")
    if declared_boundary_replay is None:
        if not plan_bricks or plan_bricks[0] != target_ref:
            raise ValueError("repair/replay plan first Brick must match materialized target_ref")
        boundary_replay_packet: Mapping[str, Any] = {}
    else:
        boundary_replay_packet = _validate_declared_boundary_replay(
            _mapping(declared_boundary_replay, "declared_boundary_replay"),
            materialized["link_decision_packet"],
            plan_steps,
        )
        if boundary_replay_packet.get("materialization_state") == "disposition_required":
            return {
                "case_ref": _require_text(
                    case.get("auto_repair_replay_case_ref"),
                    "auto_repair_replay_case_ref",
                ),
                "route_policy_ref": materialized["route_policy_ref"],
                "route_path_ref": materialized["route_path_ref"],
                "repair_replay_plan_path": plan_rel,
                "repair_replay_building_id": _require_text(
                    plan.get("building_id"), "repair_replay_plan.building_id"
                ),
                "materialized": False,
                "materialization_state": "disposition_required",
                "materialization_reason": dict(boundary_replay_packet).get(
                    "materialization_reason", "max_attempts_exhausted"
                ),
                "required_disposition_owner": "caller-or-coo",
                "declared_boundary_replay": dict(boundary_replay_packet),
                "link_decision_packet_ref": _require_text(
                    materialized["link_decision_packet"].get("link_decision_packet_ref"),
                    "link_decision_packet.link_decision_packet_ref",
                ),
                "proof_limits": list(PROOF_LIMITS),
                "not_proven": list(NOT_PROVEN),
            }
    missing_replay_refs = [ref for ref in replay_refs if ref not in plan_bricks]
    if missing_replay_refs:
        raise ValueError(f"repair/replay plan missing replay segment Brick refs: {missing_replay_refs}")
    return {
        "case_ref": _require_text(case.get("auto_repair_replay_case_ref"), "auto_repair_replay_case_ref"),
        "route_policy_ref": materialized["route_policy_ref"],
        "route_path_ref": materialized["route_path_ref"],
        "movement": materialized["movement"],
        "target_ref": target_ref,
        "repair_replay_plan_path": plan_rel,
        "repair_replay_building_id": _require_text(plan.get("building_id"), "repair_replay_plan.building_id"),
        "replay_segment_refs": replay_refs,
        "plan_brick_instance_refs": plan_bricks,
        "plan_step_attempts": [_public_plan_step(entry) for entry in plan_steps],
        "materialized_link_row": materialized["link_row"],
        "link_decision_packet": materialized["link_decision_packet"],
        "declared_boundary_replay": dict(boundary_replay_packet),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def run_declared_auto_repair_replay_case(
    case_path: Path | str | Mapping[str, Any],
    *,
    repo: Path | str,
    output_root: Path | str,
    overwrite_existing: bool = True,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Run a declared repair/replay Building Plan after route boundary checks."""

    repo_path = Path(repo).resolve()
    if isinstance(case_path, Mapping):
        case = case_path
    else:
        case_rel = _relative_path_text(case_path)
        case = _load_mapping(repo_path, case_rel)
    prepared = prepare_declared_auto_repair_replay_case(case, repo_path)
    result = run_building_plan(
        repo_path / prepared["repair_replay_plan_path"],
        output_root=Path(output_root),
        overwrite_existing=overwrite_existing,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
    )
    return {
        **prepared,
        "executed": True,
        "building_id": result.building_id,
        "plan_ref": result.plan_ref,
        "step_count": len(result.step_results),
        "written_files": [str(path) for path in result.written_files],
        "capture_event_types": list(result.capture_event_types),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _load_mapping(repo: Path, relative: str) -> Mapping[str, Any]:
    path = repo / relative
    if path.is_absolute() and not str(path).startswith(str(repo)):
        raise ValueError("case path must stay inside repo")
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("YAML route case files require PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, Mapping):
        raise ValueError(f"{relative} must contain a mapping")
    return value


def _plan_step_refs_and_brick_instance_refs(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    use_boundary_attempt_ref = plan.get("plan_shape") == "graph"
    step_plan = _linear_repair_replay_plan(plan) if use_boundary_attempt_ref else plan
    steps = _steps_list(step_plan)
    refs: list[dict[str, Any]] = []
    step_counts: dict[str, int] = {}
    for index, step in enumerate(steps):
        step_map = _mapping(step, f"steps[{index}]")
        step_ref = _require_text(step_map.get("step_ref"), f"steps[{index}].step_ref")
        rows = step_map.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"steps[{index}].rows must be a list")
        brick_rows = [
            row
            for row in rows
            if isinstance(row, Mapping) and row.get("axis") == "Brick"
        ]
        if len(brick_rows) != 1:
            raise ValueError(f"steps[{index}] must contain exactly one Brick row")
        attempt_group_ref = (
            _attempt_group_ref(step_ref, brick_rows[0])
            if use_boundary_attempt_ref
            else step_ref
        )
        step_counts[attempt_group_ref] = step_counts.get(attempt_group_ref, 0) + 1
        refs.append(
            {
                "step_ref": step_ref,
                "_attempt_group_ref": attempt_group_ref,
                "attempt_index": step_counts[attempt_group_ref],
                "brick_instance_ref": _require_text(
                    brick_rows[0].get("brick_instance_ref"),
                    f"steps[{index}].brick_instance_ref",
                ),
            }
        )
    return refs


def _linear_repair_replay_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    linear_plan, _graph_context = _linear_plan_from_graph_plan(plan)
    return linear_plan


def _validation_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("plan_shape") == "graph":
        return _linear_repair_replay_plan(plan)
    return plan


def _attempt_group_ref(step_ref: str, brick_row: Mapping[str, Any]) -> str:
    boundary_ref = brick_row.get("boundary_ref")
    if isinstance(boundary_ref, str) and boundary_ref.strip():
        return boundary_ref.strip()
    return step_ref


def _steps_list(plan: Mapping[str, Any]) -> list[Any]:
    steps = plan.get("steps")
    if not isinstance(steps, list):
        raise ValueError("repair/replay plan must contain steps")
    return steps


def _validate_declared_boundary_replay(
    declaration: Mapping[str, Any],
    link_decision_packet: Mapping[str, Any],
    plan_steps: list[dict[str, Any]],
) -> Mapping[str, Any]:
    target_step_ref = _require_text(
        declaration.get("target_step_ref"),
        "declared_boundary_replay.target_step_ref",
    )
    replay_step_refs = _string_list(
        declaration.get("replay_step_refs", ()),
        "declared_boundary_replay.replay_step_refs",
    )

    route_plan = _mapping(
        link_decision_packet.get("route_replay_plan"),
        "link_decision_packet.route_replay_plan",
    )
    max_attempt = _positive_int(route_plan.get("max_attempts"), "route_replay_plan.max_attempts")
    counts: dict[str, int] = {}
    for entry in plan_steps:
        step_ref = _require_text(entry.get("step_ref"), "plan_step.step_ref")
        attempt_group_ref = _require_text(
            entry.get("_attempt_group_ref", step_ref),
            "plan_step.attempt_group_ref",
        )
        counts[attempt_group_ref] = counts.get(attempt_group_ref, 0) + 1
        if counts[attempt_group_ref] > max_attempt:
            return _max_attempts_disposition_required(
                step_ref=step_ref,
                max_attempt=max_attempt,
                observed_attempts=counts[attempt_group_ref],
                link_decision_packet=link_decision_packet,
            )

    target_entry = _entry_for_brick_ref(
        plan_steps,
        _require_text(route_plan.get("immediate_target_ref"), "route_replay_plan.immediate_target_ref"),
    )
    if target_entry["step_ref"] != target_step_ref:
        raise ValueError("declared_boundary_replay target_step_ref must match immediate target step_ref")
    if target_entry["attempt_index"] < 2:
        raise ValueError("declared_boundary_replay target must be a repeated declared boundary")

    source_entries = [
        _entry_for_brick_ref(plan_steps, ref)
        for ref in _string_list(route_plan.get("source_brick_refs", ()), "route_replay_plan.source_brick_refs")
    ]
    if not any(
        _same_attempt_group(entry, target_entry)
        and entry["attempt_index"] < target_entry["attempt_index"]
        for entry in source_entries
    ):
        raise ValueError("declared_boundary_replay target must replay a prior declared boundary")

    replay_packets: list[dict[str, Any]] = []
    affected_entries = [
        _entry_for_brick_ref(plan_steps, ref)
        for ref in _string_list(
            route_plan.get("affected_downstream_refs", ()),
            "route_replay_plan.affected_downstream_refs",
        )
    ]
    for replay_ref in _string_list(
        route_plan.get("replay_segment_refs", ()),
        "route_replay_plan.replay_segment_refs",
    ):
        replay_entry = _entry_for_brick_ref(plan_steps, replay_ref)
        if replay_entry["step_ref"] not in replay_step_refs:
            raise ValueError("declared_boundary_replay replay step_ref was not declared")
        if replay_entry["attempt_index"] < 2:
            raise ValueError("declared_boundary_replay replay segment must be a repeated declared boundary")
        if not any(
            _same_attempt_group(entry, replay_entry)
            and entry["attempt_index"] < replay_entry["attempt_index"]
            for entry in affected_entries
        ):
            raise ValueError("declared_boundary_replay replay segment must replay an affected downstream boundary")
        replay_packets.append(_public_plan_step(replay_entry))

    return {
        "resource_kind": "declared_boundary_replay_preflight",
        "max_attempt": max_attempt,
        "target": _public_plan_step(target_entry),
        "replay_segments": replay_packets,
        "link_decision_packet_ref": link_decision_packet["link_decision_packet_ref"],
        "proof_limits": [
            *PROOF_LIMITS,
            "replay is represented by repeated declared boundary attempts",
            "not a hidden runtime loop",
        ],
        "not_proven": list(NOT_PROVEN),
    }


def _max_attempts_disposition_required(
    *,
    step_ref: str,
    max_attempt: int,
    observed_attempts: int,
    link_decision_packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Emit disposition-required evidence when declared replay exhausts max_attempts.

    Support does not choose a Movement or target on exhaustion. It records that a
    caller/COO disposition is required, mirroring the unmatched-concern disposition
    in route_materialization. No link_row / target_ref / transition_lifecycle /
    Movement is materialized here.
    """

    return {
        "resource_kind": "declared_boundary_replay_preflight",
        "materialized": False,
        "materialization_state": "disposition_required",
        "materialization_reason": "max_attempts_exhausted",
        "disposition_boundary": (
            "no Link transition lifecycle or target is materialized "
            "without caller/COO disposition"
        ),
        "exhausted_step_ref": step_ref,
        "max_attempt": max_attempt,
        "observed_attempts": observed_attempts,
        "link_decision_packet_ref": _require_text(
            link_decision_packet.get("link_decision_packet_ref"),
            "link_decision_packet.link_decision_packet_ref",
        ),
        "required_disposition_owner": "caller-or-coo",
        "proof_limits": [
            *PROOF_LIMITS,
            "replay is represented by repeated declared boundary attempts",
            "not a hidden runtime loop",
        ],
        "not_proven": list(NOT_PROVEN),
    }


def _entry_for_brick_ref(plan_steps: list[dict[str, Any]], brick_ref: str) -> dict[str, Any]:
    matches = [entry for entry in plan_steps if entry["brick_instance_ref"] == brick_ref]
    if len(matches) != 1:
        raise ValueError(f"declared replay Brick ref must appear exactly once in plan: {brick_ref}")
    return matches[0]


def _same_attempt_group(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_group = left.get("_attempt_group_ref") or left.get("step_ref")
    right_group = right.get("_attempt_group_ref") or right.get("step_ref")
    return left_group == right_group


def _public_plan_step(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "step_ref": _require_text(entry.get("step_ref"), "plan_step.step_ref"),
        "attempt_index": entry["attempt_index"],
        "brick_instance_ref": _require_text(
            entry.get("brick_instance_ref"),
            "plan_step.brick_instance_ref",
        ),
    }


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(f"{label} must be a positive integer")


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return [item.strip() for item in value]


def _relative_path_text(path: Path | str) -> str:
    text = str(path)
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("case path must be a repo-relative path")
    return text


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()
