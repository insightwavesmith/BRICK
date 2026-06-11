"""Prepare child Building Plan candidates from declared remaining_delta evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROOF_LIMITS = (
    "support evidence only",
    "candidate generation only",
    "not active plan declaration",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN = (
    "semantic correctness of generated candidate plan",
    "future child Building execution",
)


def prepare_child_building_candidate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a declared child Building candidate generation case."""

    case_ref = _require_text(case.get("child_generation_case_ref"), "child_generation_case_ref")
    parent_goal_ref = _require_text(case.get("parent_goal_ref"), "parent_goal_ref")
    remaining_delta = _string_list(case.get("remaining_delta"), "remaining_delta")
    selected_delta_ref = _require_text(case.get("selected_delta_ref"), "selected_delta_ref")
    if selected_delta_ref not in remaining_delta:
        raise ValueError("selected_delta_ref must be carried in remaining_delta")
    candidate_plan = _mapping(case.get("candidate_plan"), "candidate_plan")
    if candidate_plan.get("owner_axis") != "Brick":
        raise ValueError("candidate_plan owner_axis must be Brick")
    if candidate_plan.get("parent_goal_ref") != parent_goal_ref:
        raise ValueError("candidate_plan must carry parent_goal_ref")
    if selected_delta_ref not in _string_list(candidate_plan.get("next_target_candidates"), "candidate_plan.next_target_candidates"):
        raise ValueError("candidate_plan next_target_candidates must include selected_delta_ref")
    steps = candidate_plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("candidate_plan must include steps")
    return {
        "case_ref": case_ref,
        "parent_goal_ref": parent_goal_ref,
        "selected_delta_ref": selected_delta_ref,
        "candidate_plan_ref": _require_text(candidate_plan.get("plan_ref"), "candidate_plan.plan_ref"),
        "candidate_building_id": _require_text(candidate_plan.get("building_id"), "candidate_plan.building_id"),
        "candidate_plan": candidate_plan,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def generate_child_building_candidate(
    case_path: Path | str | Mapping[str, Any],
    *,
    repo: Path | str,
    overwrite_existing: bool = True,
) -> dict[str, Any]:
    """Return a declared child Building candidate plan without writing axis files."""

    repo_path = Path(repo).resolve()
    if isinstance(case_path, Mapping):
        case = case_path
    else:
        case = _load_mapping(repo_path / _require_relative_path(case_path, "case_path"))
    prepared = prepare_child_building_candidate_case(case)
    return {
        **prepared,
        "written": False,
    }


def _load_mapping(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("YAML child generation files require PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a mapping")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return [item.strip() for item in value]


def _require_relative_path(
    value: Any,
    label: str,
    *,
    required_prefix: str | None = None,
) -> str:
    text = _require_text(value, label)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a repo-relative path")
    if required_prefix is not None and not text.startswith(required_prefix):
        raise ValueError(f"{label} must start with {required_prefix}")
    return text
