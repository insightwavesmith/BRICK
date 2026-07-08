"""Draft-only validation helpers for Building Call authoring returns.

GOAL ⑤f: this module normalizes and validates the provider-neutral draft
packet returned by the Building Call Authoring Brick. It does not launch,
lower, run a Building, choose Movement, choose a route target, judge success,
or judge quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


AUTHORING_RETURN_SCHEMA_VERSION = "building-call-authoring-return-v1"

AUTHORING_STEP_REFS: tuple[str, ...] = (
    "STEP1_SCOPE",
    "STEP2_BUILDING_INTENSITY",
    "STEP3_STRUCTURE",
    "STEP4_PER_BRICK_INTENSITY",
    "STEP5_AGENT_CANDIDATES",
)

AUTHORING_STEP_SECTION_FIELDS: tuple[tuple[str, str], ...] = (
    ("scope_draft", "STEP1_SCOPE"),
    ("building_intensity_routing_draft", "STEP2_BUILDING_INTENSITY"),
    ("structure_draft", "STEP3_STRUCTURE"),
    ("per_brick_intensity_draft", "STEP4_PER_BRICK_INTENSITY"),
    ("agent_candidates_draft", "STEP5_AGENT_CANDIDATES"),
)

REQUIRED_AUTHORING_RETURN_FIELDS: tuple[str, ...] = (
    "observed_evidence",
    "five_step_order",
    "scope_draft",
    "building_intensity_routing_draft",
    "structure_draft",
    "per_brick_intensity_draft",
    "agent_candidates_draft",
    "launch_confirmation_state",
    "forbidden_exposure_scan",
    "remaining_delta",
    "not_proven",
)

FORBIDDEN_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "success",
    "failure",
    "approved",
    "quality",
    "good_enough",
    "movement_choice",
    "route_target",
    "lowering",
    "launch_authorization",
    "selected_adapter_ref",
    "selected_model_ref",
    "selected_reasoning_effort_ref",
)

FORBIDDEN_DRAFT_KEYS: tuple[str, ...] = (
    "selected_adapter_ref",
    "selected_model_ref",
    "selected_reasoning_effort_ref",
    "provider_ref",
    "model_ref",
    "adapter_ref",
    "runtime_profile",
    "route_materialization",
    "walker_kernel",
    "walker_resume",
    "chain_preset_ref",
)

FORBIDDEN_DRAFT_VALUE_PREFIXES: tuple[str, ...] = (
    "provider:",
    "model:",
    "adapter:",
)
FORBIDDEN_DRAFT_VALUE_MARKERS: tuple[str, ...] = tuple(
    prefix.casefold() for prefix in FORBIDDEN_DRAFT_VALUE_PREFIXES
)

LAUNCH_CONFIRMATION_ALLOWED_VALUES: tuple[str, ...] = (
    "not_confirmed",
    "needs_human_gate",
    "draft_only",
)


class BuildingCallAuthoringValidationError(ValueError):
    """Raised when a draft authoring return violates the ⑤f contract."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


def normalize_building_call_authoring_return(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic draft packet after fail-closed validation."""

    violations = validate_building_call_authoring_return(payload)
    if violations:
        raise BuildingCallAuthoringValidationError(violations)
    normalized = {field: _normalize_value(payload[field]) for field in REQUIRED_AUTHORING_RETURN_FIELDS}
    normalized["kind"] = AUTHORING_RETURN_SCHEMA_VERSION
    normalized["proof_limits"] = [
        "draft-only Building Call authoring return validation",
        "not Building launch authorization",
        "not lowering",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]
    return normalized


def building_call_authoring_return_v1(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Provider-neutral helper for producing the admitted normalized return shape."""

    return normalize_building_call_authoring_return(payload)


def validate_building_call_authoring_return(payload: Mapping[str, Any]) -> list[str]:
    """Return validation violations for a draft-only authoring return packet."""

    violations: list[str] = []
    if not isinstance(payload, Mapping):
        return ["payload must be a mapping"]

    missing = [field for field in REQUIRED_AUTHORING_RETURN_FIELDS if field not in payload]
    if missing:
        violations.append(f"missing required field(s): {', '.join(missing)}")

    unexpected_forbidden = [field for field in FORBIDDEN_TOP_LEVEL_FIELDS if field in payload]
    if unexpected_forbidden:
        violations.append(f"forbidden top-level field(s): {', '.join(unexpected_forbidden)}")
    unexpected_unknown = [
        field
        for field in payload
        if field not in REQUIRED_AUTHORING_RETURN_FIELDS
        and field not in FORBIDDEN_TOP_LEVEL_FIELDS
    ]
    if unexpected_unknown:
        unknown_text = ", ".join(str(field) for field in unexpected_unknown)
        violations.append(f"unknown top-level field(s): {unknown_text}")

    _validate_five_step_order(payload.get("five_step_order"), violations)
    _validate_step_sections(payload, violations)
    _validate_launch_confirmation(payload.get("launch_confirmation_state"), violations)
    _scan_forbidden_exposure(payload, violations)
    return violations


def render_authoring_sequence_rule() -> dict[str, Any]:
    """Return the closed five-step authoring sequence as support evidence."""

    return {
        "kind": "building-call-authoring-sequence-v1",
        "step_refs": list(AUTHORING_STEP_REFS),
        "sequence_rule": "STEP1_SCOPE -> STEP2_BUILDING_INTENSITY -> STEP3_STRUCTURE -> STEP4_PER_BRICK_INTENSITY -> STEP5_AGENT_CANDIDATES",
        "draft_only": True,
        "proof_limits": [
            "support validation helper only",
            "not launch authorization",
            "not lowering",
            "not Movement authority",
        ],
    }


def render_building_call_authoring_return_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic JSON for a normalized authoring return packet."""

    return json.dumps(
        normalize_building_call_authoring_return(payload),
        ensure_ascii=False,
        sort_keys=True,
    )


def _validate_five_step_order(value: Any, violations: list[str]) -> None:
    observed = _step_refs_from_order(value)
    if observed != list(AUTHORING_STEP_REFS):
        violations.append(
            "five_step_order must be exactly "
            "STEP1_SCOPE -> STEP2_BUILDING_INTENSITY -> STEP3_STRUCTURE -> "
            "STEP4_PER_BRICK_INTENSITY -> STEP5_AGENT_CANDIDATES"
        )


def _step_refs_from_order(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, str):
            refs.append(item)
        elif isinstance(item, Mapping) and isinstance(item.get("step_ref"), str):
            refs.append(str(item["step_ref"]))
        else:
            refs.append("")
    return refs


def _validate_step_sections(payload: Mapping[str, Any], violations: list[str]) -> None:
    for field, expected_step_ref in AUTHORING_STEP_SECTION_FIELDS:
        section = payload.get(field)
        if not isinstance(section, Mapping):
            violations.append(f"{field} must be a mapping")
            continue
        observed_step_ref = section.get("step_ref")
        if observed_step_ref != expected_step_ref:
            violations.append(f"{field}.step_ref must be {expected_step_ref}")


def _validate_launch_confirmation(value: Any, violations: list[str]) -> None:
    if value not in LAUNCH_CONFIRMATION_ALLOWED_VALUES:
        allowed = ", ".join(LAUNCH_CONFIRMATION_ALLOWED_VALUES)
        violations.append(f"launch_confirmation_state must be one of: {allowed}")


def _scan_forbidden_exposure(payload: Mapping[str, Any], violations: list[str]) -> None:
    for field in REQUIRED_AUTHORING_RETURN_FIELDS:
        if field in payload:
            _scan_value(field, payload[field], violations)


def _scan_value(path: str, value: Any, violations: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if (
                key_text in FORBIDDEN_DRAFT_KEYS
                or key_text.casefold() in FORBIDDEN_DRAFT_KEYS
            ):
                violations.append(f"forbidden draft key: {child_path}")
            _scan_value(child_path, child, violations)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_value(f"{path}[{index}]", child, violations)
        return
    if isinstance(value, str) and any(
        marker in value.casefold() for marker in FORBIDDEN_DRAFT_VALUE_MARKERS
    ):
        violations.append(f"forbidden draft value marker at {path}")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_value(item) for item in value]
    return value


__all__ = [
    "AUTHORING_RETURN_SCHEMA_VERSION",
    "AUTHORING_STEP_REFS",
    "AUTHORING_STEP_SECTION_FIELDS",
    "REQUIRED_AUTHORING_RETURN_FIELDS",
    "FORBIDDEN_TOP_LEVEL_FIELDS",
    "FORBIDDEN_DRAFT_KEYS",
    "FORBIDDEN_DRAFT_VALUE_PREFIXES",
    "FORBIDDEN_DRAFT_VALUE_MARKERS",
    "BuildingCallAuthoringValidationError",
    "building_call_authoring_return_v1",
    "normalize_building_call_authoring_return",
    "validate_building_call_authoring_return",
    "render_authoring_sequence_rule",
    "render_building_call_authoring_return_json",
]
