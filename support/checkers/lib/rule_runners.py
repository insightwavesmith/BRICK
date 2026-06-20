"""Declarative profile rule runners + Building/route boundary validators.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition).
These are the path/text/yaml/json declarative rule runners and the Building
Plan / route-policy boundary validators the profile runner dispatches via
RULE_RUNNERS. Support checker mechanics only: validators that CONSUME the Link
MovementFact contract (MOVEMENT_LITERALS) to reject forbidden inline route
authority; they author no crossing and decide nothing.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import io
import json
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brick_protocol.link.movement import MOVEMENT_LITERALS

from support.checkers.lib.yaml_subset import (
    ProfileError,
    extract_path,
    json_path_exists,
    load_yaml_subset_file,
    parse_yaml_subset,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
    to_posix,
    to_repo_path,
)


def run_path_exists(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for relative in rule_items(profile, "path_exists"):
        count += 1
        if not to_repo_path(repo, require_string(relative, "path_exists item")).exists():
            raise ProfileError(f"path_exists rejected missing path: {relative}")
    return count


def run_path_absent(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for relative in rule_items(profile, "path_absent"):
        count += 1
        if to_repo_path(repo, require_string(relative, "path_absent item")).exists():
            raise ProfileError(f"path_absent rejected present path: {relative}")
    return count


def run_path_absent_glob(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for pattern in rule_items(profile, "path_absent_glob"):
        pattern = require_string(pattern, "path_absent_glob item")
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ProfileError(f"path_absent_glob escapes repo: {pattern}")
        matches = sorted(to_posix(path.relative_to(repo)) for path in repo.glob(pattern))
        count += 1
        if matches:
            raise ProfileError(f"path_absent_glob rejected {pattern}: {matches}")
    return count


def run_path_allowlist(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, "path_allowlist"):
        mapping = require_mapping(item, "path_allowlist item")
        root_rel = require_string(mapping.get("root"), "path_allowlist.root")
        allowed = set(require_string_list(mapping.get("paths"), "path_allowlist.paths"))
        root = to_repo_path(repo, root_rel)
        if not root.is_dir():
            raise ProfileError(f"path_allowlist root missing directory: {root_rel}")
        observed = {
            to_posix(path.relative_to(repo))
            for path in root.rglob("*")
            if path.is_file()
        }
        unexpected = sorted(observed - allowed)
        count += len(observed)
        if unexpected:
            raise ProfileError(f"path_allowlist rejected unexpected file(s): {unexpected}")
    return count


def text_rule(rule_name: str, repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, rule_name):
        mapping = require_mapping(item, f"{rule_name} item")
        relative = require_string(mapping.get("path"), f"{rule_name}.path")
        text = to_repo_path(repo, relative).read_text(encoding="utf-8")
        needles = mapping.get("texts", mapping.get("text"))
        if isinstance(needles, str):
            needle_list = [needles]
        else:
            needle_list = require_string_list(needles, f"{rule_name}.texts")
        for needle in needle_list:
            count += 1
            if rule_name == "text_contains" and needle not in text:
                raise ProfileError(f"text_contains rejected {relative}: missing {needle!r}")
            if rule_name == "text_absent" and needle in text:
                raise ProfileError(f"text_absent rejected {relative}: found {needle!r}")
    return count


def run_yaml_literal_set(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, "yaml_literal_set"):
        mapping = require_mapping(item, "yaml_literal_set item")
        relative = require_string(mapping.get("path"), "yaml_literal_set.path")
        key = require_string(mapping.get("key"), "yaml_literal_set.key")
        expected = set(require_string_list(mapping.get("values"), "yaml_literal_set.values"))
        parsed = parse_yaml_subset(to_repo_path(repo, relative).read_text(encoding="utf-8"))
        observed = {str(value) for value in extract_path(parsed, key)}
        count += 1
        if observed != expected:
            raise ProfileError(
                f"yaml_literal_set rejected {relative}:{key}: expected "
                f"{sorted(expected)}, observed {sorted(observed)}"
            )
    return count


def run_json_required_paths(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, "json_required_paths"):
        mapping = require_mapping(item, "json_required_paths item")
        relative = require_string(mapping.get("path"), "json_required_paths.path")
        required = require_string_list(mapping.get("required"), "json_required_paths.required")
        value = json.loads(to_repo_path(repo, relative).read_text(encoding="utf-8"))
        for dotted_path in required:
            count += 1
            if not json_path_exists(value, dotted_path):
                raise ProfileError(f"json_required_paths rejected {relative}: missing {dotted_path}")
    return count


def run_json_value_paths(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, "json_value_paths"):
        mapping = require_mapping(item, "json_value_paths item")
        relative = require_string(mapping.get("path"), "json_value_paths.path")
        key = require_string(mapping.get("key"), "json_value_paths.key")
        expected = set(require_string_list(mapping.get("values"), "json_value_paths.values"))
        value = json.loads(to_repo_path(repo, relative).read_text(encoding="utf-8"))
        observed = {str(found) for found in extract_path(value, key)}
        count += 1
        if not observed:
            raise ProfileError(f"json_value_paths rejected {relative}: no value at {key}")
        if not observed <= expected:
            raise ProfileError(
                f"json_value_paths rejected {relative}:{key}: observed "
                f"{sorted(observed)} not within expected {sorted(expected)}"
            )
    return count


def run_agent_resource_boundary(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "agent_resource_boundary")
    if not items:
        return 0
    from support.connection.agent_resources import render_agent_packet

    count = 0
    for item in items:
        mapping = require_mapping(item, "agent_resource_boundary item")
        role = require_string(mapping.get("role"), "agent_resource_boundary.role")
        packet = render_agent_packet(role, repo_root=repo)
        agent_object = require_mapping(packet.get("agent_object"), f"agent_resource_boundary:{role}.agent_object")
        if "lane" in mapping and agent_object.get("lane") != mapping["lane"]:
            raise ProfileError(
                f"agent_resource_boundary rejected {role}: lane expected {mapping['lane']!r}, "
                f"observed {agent_object.get('lane')!r}"
            )
        if (
            "preferred_adapter_ref" in mapping
            and agent_object.get("preferred_adapter_ref") != mapping["preferred_adapter_ref"]
        ):
            raise ProfileError(
                f"agent_resource_boundary rejected {role}: preferred_adapter_ref "
                f"expected {mapping['preferred_adapter_ref']!r}, "
                f"observed {agent_object.get('preferred_adapter_ref')!r}"
            )
        if (
            "preferred_model_ref" in mapping
            and agent_object.get("preferred_model_ref") != mapping["preferred_model_ref"]
        ):
            raise ProfileError(
                f"agent_resource_boundary rejected {role}: preferred_model_ref "
                f"expected {mapping['preferred_model_ref']!r}, "
                f"observed {agent_object.get('preferred_model_ref')!r}"
            )
        _validate_required_refs(agent_object, mapping, role)
        _validate_forbidden_refs(agent_object, mapping, role)
        if mapping.get("hooks_execution_opened") is False:
            selected = require_mapping(packet.get("hook_resources"), f"agent_resource_boundary:{role}.hook_resources").get("selected")
            if not isinstance(selected, list):
                raise ProfileError(f"agent_resource_boundary rejected {role}: hook resources missing")
            for hook in selected:
                hook_map = require_mapping(hook, f"agent_resource_boundary:{role}.hook")
                definition = require_mapping(
                    hook_map.get("definition"),
                    f"agent_resource_boundary:{role}.hook.definition",
                )
                if definition.get("execution_opened") is not False:
                    raise ProfileError(f"agent_resource_boundary rejected {role}: native hook execution opened")
        count += 1
    return count


def _validate_required_refs(
    agent_object: Mapping[str, Any],
    mapping: Mapping[str, Any],
    role: str,
) -> None:
    for field in ("hook_refs", "tool_policy_refs", "adapter_refs", "skill_refs", "prompt_refs"):
        key = f"required_{field}"
        if key not in mapping:
            continue
        observed = set(require_string_list(agent_object.get(field, []), f"agent_resource_boundary:{role}.{field}"))
        required = set(require_string_list(mapping.get(key), f"agent_resource_boundary.{key}"))
        missing = sorted(required - observed)
        if missing:
            raise ProfileError(f"agent_resource_boundary rejected {role}: missing {field}: {missing}")


def _validate_forbidden_refs(
    agent_object: Mapping[str, Any],
    mapping: Mapping[str, Any],
    role: str,
) -> None:
    for field in ("hook_refs", "tool_policy_refs", "adapter_refs", "skill_refs", "prompt_refs"):
        key = f"forbidden_{field}"
        if key not in mapping:
            continue
        observed = set(require_string_list(agent_object.get(field, []), f"agent_resource_boundary:{role}.{field}"))
        forbidden = set(require_string_list(mapping.get(key), f"agent_resource_boundary.{key}"))
        present = sorted(forbidden & observed)
        if present:
            raise ProfileError(f"agent_resource_boundary rejected {role}: forbidden {field}: {present}")


_RETIRED_REF_REJECT_FIELDS = ("tool_policy_refs", "hook_refs")


def run_agent_resource_retired_ref_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    """Negative probe: a RETIRED tool-policy/hook ref must REJECT loudly.

    WAVE-B rename (0610): agent_resources keeps _RETIRED_TOOL_POLICY_REFS /
    _RETIRED_HOOK_REFS maps so a retired name rejects naming the canonical
    replacement instead of falling through to a vague missing-file error.
    agent_resource_boundary only validates CURRENT objects, so deleting a
    retired-map entry would stay silently green. This probe calls the resolver
    guard DIRECTLY (same convention as the compose_building route-policy
    provenance probe) with a synthetic Agent Object carrying ONLY the retired
    ref. The retired refs + expected messages are pinned on the PROFILE side,
    NOT derived from the maps -- delete any retired-map entry and the
    rejection message changes (or vanishes), so this goes RED.
    """
    items = rule_items(profile, "agent_resource_retired_ref_rejects")
    if not items:
        return 0
    from support.connection.agent_resources import (
        AgentResourceError,
        _validate_agent_authority,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "agent_resource_retired_ref_rejects item")
        ref_field = require_string(
            mapping.get("ref_field"), "agent_resource_retired_ref_rejects.ref_field"
        )
        if ref_field not in _RETIRED_REF_REJECT_FIELDS:
            raise ProfileError(
                "agent_resource_retired_ref_rejects.ref_field must be one of "
                f"{list(_RETIRED_REF_REJECT_FIELDS)}, observed {ref_field!r}"
            )
        retired_ref = require_string(
            mapping.get("retired_ref"), "agent_resource_retired_ref_rejects.retired_ref"
        )
        expected_message = require_string(
            mapping.get("expected_message"),
            "agent_resource_retired_ref_rejects.expected_message",
        )
        agent_object: dict[str, Any] = {
            "lane": "worker",
            "hook_refs": [],
            "tool_policy_refs": [],
            "adapter_refs": [],
            ref_field: [retired_ref],
        }
        probe_path = repo / "agent" / "objects" / "retired-ref-probe.yaml"
        try:
            _validate_agent_authority("retired-ref-probe", agent_object, probe_path)
        except AgentResourceError as exc:
            if expected_message not in str(exc):
                raise ProfileError(
                    f"agent_resource_retired_ref_rejects rejected {retired_ref}: "
                    f"expected message {expected_message!r}, observed {str(exc)!r}"
                ) from exc
            count += 1
            continue
        raise ProfileError(
            f"agent_resource_retired_ref_rejects expected rejection but passed: {retired_ref}"
        )
    return count


def run_agent_preferred_adapter_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "agent_preferred_adapter_rejects")
    if not items:
        return 0
    from support.connection.agent_resources import (
        AgentResourceError,
        _validate_agent_authority,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "agent_preferred_adapter_rejects item")
        expected_message = require_string(
            mapping.get("expected_message"),
            "agent_preferred_adapter_rejects.expected_message",
        )
        agent_object = dict(
            require_mapping(
                mapping.get("agent_object"),
                "agent_preferred_adapter_rejects.agent_object",
            )
        )
        probe_path = repo / "agent" / "objects" / "preferred-adapter-probe.yaml"
        try:
            _validate_agent_authority(
                "preferred-adapter-probe",
                agent_object,
                probe_path,
            )
        except AgentResourceError as exc:
            if expected_message not in str(exc):
                raise ProfileError(
                    "agent_preferred_adapter_rejects rejected with unexpected "
                    f"message: expected {expected_message!r}, observed {str(exc)!r}"
                ) from exc
            count += 1
            continue
        raise ProfileError("agent_preferred_adapter_rejects expected rejection but passed")
    return count


def run_building_plan_boundary(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "building_plan_boundary")
    if not items:
        return 0
    count = 0
    admitted_agent_refs = _admitted_agent_object_refs(repo)
    for item in items:
        mapping = require_mapping(item, "building_plan_boundary item")
        relative = require_string(mapping.get("path"), "building_plan_boundary.path")
        allow_retired_write_adapter_refs = mapping.get("allow_retired_write_adapter_refs", False)
        if not isinstance(allow_retired_write_adapter_refs, bool):
            raise ProfileError(
                "building_plan_boundary.allow_retired_write_adapter_refs must be a boolean"
            )
        validate_building_plan_boundary(
            load_yaml_subset_file(repo, relative),
            relative,
            admitted_agent_refs,
            repo,
            allow_retired_write_adapter_refs=allow_retired_write_adapter_refs,
        )
        count += 1
    return count


def run_route_policy_boundary(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    for item in rule_items(profile, "route_policy_boundary"):
        mapping = require_mapping(item, "route_policy_boundary item")
        relative = require_string(mapping.get("path"), "route_policy_boundary.path")
        validate_route_policy_boundary(load_yaml_subset_file(repo, relative), relative)
        count += 1
    return count


def _admitted_agent_object_refs(repo: Path) -> set[str]:
    object_dir = repo / "agent" / "objects"
    if not object_dir.is_dir():
        raise ProfileError("agent/objects must exist")
    refs = {f"agent-object:{path.stem}" for path in object_dir.glob("*.yaml")}
    if not refs:
        raise ProfileError("agent/objects must contain admitted Agent Object resources")
    return refs


def validate_building_plan_boundary(
    plan: Mapping[str, Any],
    label: str,
    admitted_agent_refs: set[str] | None = None,
    repo: Path | None = None,
    *,
    allow_retired_write_adapter_refs: bool = False,
) -> None:
    if plan.get("owner_axis") != "Brick":
        raise ProfileError(f"{label}: owner_axis must be Brick")
    require_string(plan.get("plan_ref"), f"{label}: plan_ref")
    _reject_forbidden_nested_keys(plan, label, _BUILDING_PLAN_FORBIDDEN_KEYS)
    validation_plan = plan
    try:
        from support.operator.plan_validation import validate_declared_building_plan

        if plan.get("plan_shape") == "graph":
            from support.operator.plan_graph import _linear_plan_from_graph_plan

            validation_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        validate_declared_building_plan(
            validation_plan,
            repo_root=repo,
            allow_retired_write_adapter_refs=allow_retired_write_adapter_refs,
        )
    except ValueError as exc:
        raise ProfileError(f"{label}: {exc}") from exc
    steps = validation_plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ProfileError(f"{label}: steps must be a non-empty list")
    for index, raw_step in enumerate(steps):
        step = require_mapping(raw_step, f"{label}: steps[{index}]")
        require_string(step.get("step_ref"), f"{label}: steps[{index}].step_ref")
        rows = step.get("rows")
        if not isinstance(rows, list) or len(rows) != 3:
            raise ProfileError(f"{label}: steps[{index}].rows must contain exactly Brick/Agent/Link rows")
        row_maps = [require_mapping(row, f"{label}: steps[{index}].rows[]") for row in rows]
        axes = [row.get("axis") for row in row_maps]
        if axes != ["Brick", "Agent", "Link"]:
            raise ProfileError(f"{label}: steps[{index}].rows axis order must be Brick, Agent, Link")
        _validate_brick_row(row_maps[0], f"{label}: steps[{index}].Brick")
        _validate_agent_row(row_maps[1], f"{label}: steps[{index}].Agent", admitted_agent_refs)
        _validate_link_row(row_maps[2], f"{label}: steps[{index}].Link")


def _validate_brick_row(row: Mapping[str, Any], label: str) -> None:
    for key in ("brick_work_ref", "brick_instance_ref", "work_statement", "comparison_rule", "required_return_shape"):
        require_string(row.get(key), f"{label}.{key}")
    forbidden = set(row) & _BRICK_ROW_FORBIDDEN_INLINE_KEYS
    if forbidden:
        raise ProfileError(f"{label}: Brick row must not inline Agent/Link keys: {sorted(forbidden)}")


def _validate_agent_row(
    row: Mapping[str, Any],
    label: str,
    admitted_agent_refs: set[str] | None,
) -> None:
    allowed_refs = admitted_agent_refs or _ALLOWED_AGENT_OBJECT_REFS
    if row.get("agent_object_ref") not in allowed_refs:
        raise ProfileError(f"{label}: agent_object_ref must reference an admitted Agent Object")
    forbidden = set(row) & _AGENT_ROW_FORBIDDEN_INLINE_KEYS
    if forbidden:
        raise ProfileError(f"{label}: Agent row must not inline resource/provider config: {sorted(forbidden)}")


def _validate_link_row(row: Mapping[str, Any], label: str) -> None:
    movement = row.get("movement", row.get("movement_literal"))
    if movement not in MOVEMENT_LITERALS:
        raise ProfileError(f"{label}: movement must be forward or reroute")
    if "movement" in row and "movement_literal" in row:
        raise ProfileError(f"{label}: Link row must declare one Movement field")
    target_values = [
        str(row[key]).strip()
        for key in _LINK_TARGET_KEYS
        if isinstance(row.get(key), str) and str(row[key]).strip()
    ]
    if not target_values:
        raise ProfileError(f"{label}: Link row must declare a target")
    if row.get("route_replay_plan") and movement != "reroute":
        raise ProfileError(f"{label}: route_replay_plan requires movement reroute")


def validate_route_policy_boundary(policy: Mapping[str, Any], label: str) -> None:
    _reject_forbidden_nested_keys(policy, label, _ROUTE_POLICY_FORBIDDEN_KEYS)
    route_policy_ref = require_string(policy.get("route_policy_ref"), f"{label}: route_policy_ref")
    if not route_policy_ref.startswith("route-policy:"):
        raise ProfileError(f"{label}: route_policy_ref must start with route-policy:")
    if policy.get("owner_axis") != "Link":
        raise ProfileError(f"{label}: owner_axis must be Link")
    if policy.get("resource_kind") != "route_policy_contract":
        raise ProfileError(f"{label}: resource_kind must be route_policy_contract")
    if policy.get("fact_class_admission") != "not_admitted":
        raise ProfileError(f"{label}: fact_class_admission must remain not_admitted")
    if policy.get("movement_literal") != "reroute":
        raise ProfileError(f"{label}: movement_literal must be reroute")
    requests = policy.get("allowed_route_requests")
    if not isinstance(requests, list) or not requests:
        raise ProfileError(f"{label}: allowed_route_requests must be non-empty")
    observed_scopes: set[str] = set()
    for index, raw_request in enumerate(requests):
        request = require_mapping(raw_request, f"{label}: allowed_route_requests[{index}]")
        scope = require_string(
            request.get("requested_route_scope"),
            f"{label}: allowed_route_requests[{index}].requested_route_scope",
        )
        if scope not in _ALLOWED_ROUTE_REQUEST_SCOPES:
            raise ProfileError(f"{label}: unadmitted requested_route_scope: {scope}")
        observed_scopes.add(scope)
        route_path_ref = require_string(
            request.get("route_path_ref"),
            f"{label}: allowed_route_requests[{index}].route_path_ref",
        )
        if not route_path_ref.startswith("route-path:"):
            raise ProfileError(f"{label}: route_path_ref must start with route-path:")
        target_step = require_string(
            request.get("target_step"),
            f"{label}: allowed_route_requests[{index}].target_step",
        )
        if not target_step:
            raise ProfileError(f"{label}: target_step must be non-empty")
        replay_steps = request.get("replay_steps", [])
        if not isinstance(replay_steps, list) or not all(isinstance(item, str) for item in replay_steps):
            raise ProfileError(f"{label}: replay_steps must be a list of strings")
        replay_refs = request.get("replay_segment_refs", [])
        if not isinstance(replay_refs, list) or not all(isinstance(item, str) for item in replay_refs):
            raise ProfileError(f"{label}: replay_segment_refs must be a list of strings")
        if not isinstance(request.get("route_reason_refs_required"), bool):
            raise ProfileError(f"{label}: route_reason_refs_required must be boolean")
        if not isinstance(request.get("human_gate_required"), bool):
            raise ProfileError(f"{label}: human_gate_required must be boolean")
    missing = _ALLOWED_ROUTE_REQUEST_SCOPES - observed_scopes
    if missing:
        raise ProfileError(f"{label}: missing route request scopes: {sorted(missing)}")


def _reject_forbidden_nested_keys(value: Any, label: str, forbidden: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().replace("-", "_").lower()
            if normalized in forbidden:
                raise ProfileError(f"{label}: forbidden key {key}")
            _reject_forbidden_nested_keys(child, label, forbidden)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_nested_keys(child, label, forbidden)


_ALLOWED_AGENT_OBJECT_REFS = {
    "agent-object:coo",
    "agent-object:dev",
    "agent-object:qa",
}


_BRICK_ROW_FORBIDDEN_INLINE_KEYS = {
    "agent_object_ref",
    "prompt_refs",
    "skill_refs",
    "adapter_refs",
    "tool_policy_refs",
    "movement",
    "target_ref",
}


_AGENT_ROW_FORBIDDEN_INLINE_KEYS = {
    "prompt_refs",
    "skill_refs",
    "hook_refs",
    "tool_policy_refs",
    "discipline_refs",
    "adapter_refs",
    "provider",
    "provider_request",
    "write_scope",
}


_LINK_TARGET_KEYS = (
    "target_ref",
    "target",
    "target_boundary_ref",
    "next_boundary_ref",
    "next_brick_instance_ref",
)


_BUILDING_PLAN_FORBIDDEN_KEYS = {
    "condition",
    "conditions",
    "if",
    "else",
    "route_policy_match",
    "route_policy_result",
    "auto_repair",
    "auto_replay",
    "auto_child_building",
    "selected_shape_by_runner",
    "movement_choice",
    "movement_selector",
    "runtime_retry",
    "retry_policy",
    "runtime_chosen_target",
    "choose_movement",
    "support_chosen_movement",
    "default_gatefact",
    "semantic_quality_judgment",
    "quality_judgment",
    "success_judgment",
}


_ALLOWED_ROUTE_REQUEST_SCOPES = {"qa_only", "implementation_only", "design_gap"}


_ROUTE_POLICY_FORBIDDEN_KEYS = {
    "route_policy_fact",
    "routepolicyfact",
    "fact_class",
    "route_executor",
    "execute_route",
    "auto_repair",
    "auto_replay",
    "auto_child_building",
    "choose_movement",
    "support_chosen_movement",
    "movement_authority",
    "provider_endpoint",
    "agent_endpoint",
    "runtime_scheduler",
    "runtime_retry",
    "semantic_quality_judgment",
    "quality_judgment",
    "success_judgment",
}
