"""Draft-only validation helpers for Building Call authoring returns.

GOAL ⑤f: this module normalizes and validates the provider-neutral draft
packet returned by the Building Call Authoring Brick. It does not launch,
lower, run a Building, choose Movement, choose a route target, judge success,
or judge quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
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
HELD_FOR_COO_REVIEW_STATE = "held_for_coo_review"
OPERATING_VOCABULARY_SCHEMA = "brick-operating-vocabulary/v1"
OPERATING_VOCABULARY_PATH = (
    Path(__file__).resolve().parents[2]
    / "brick"
    / "templates"
    / "operating-vocabulary-v1.yaml"
)

STRUCTURE_PLAN_DRAFT_ALLOWED_KEYS = frozenset(
    {
        "nodes",
        "edges",
        "coo_gate_edge",
        "fan_out_groups",
        "fan_in_groups",
        "reroute_budgets",
        "node_reroute_budgets",
        "terminal",
    }
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
    violations.extend(operating_vocabulary_violations(payload))
    return violations


def load_operating_vocabulary(path: Path | str | None = None) -> Mapping[str, Any]:
    """Load the Smith-approved v1 declaration vocabulary from its Brick source.

    The file deliberately uses the JSON subset of YAML so product code can read
    it deterministically without introducing a second YAML interpretation seam.
    """

    source = Path(path).resolve() if path is not None else OPERATING_VOCABULARY_PATH
    try:
        loaded = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildingCallAuthoringValidationError(
            (f"operating vocabulary is unreadable: {source}",)
        ) from exc
    if not isinstance(loaded, Mapping) or loaded.get("schema") != OPERATING_VOCABULARY_SCHEMA:
        raise BuildingCallAuthoringValidationError(
            (f"operating vocabulary schema must be {OPERATING_VOCABULARY_SCHEMA}",)
        )
    for field in ("agent_lanes", "brick_kinds", "chain_presets"):
        values = loaded.get(field)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(item, str) and item.strip() for item in values)
            or len(values) != len(set(values))
        ):
            raise BuildingCallAuthoringValidationError(
                (f"operating vocabulary {field} must be a non-empty unique string list",)
            )
    return loaded


def operating_vocabulary_violations(payload: Mapping[str, Any]) -> list[str]:
    """Reject authoring/lowering refs outside the active v1 vocabulary.

    Only explicit vocabulary-bearing fields are inspected.  Free-text task and
    rationale bodies remain prose and cannot silently create a runnable kind,
    lane, or preset.
    """

    vocabulary = load_operating_vocabulary()
    allowed_lanes = set(vocabulary["agent_lanes"])
    allowed_kinds = set(vocabulary["brick_kinds"])
    allowed_presets = set(vocabulary["chain_presets"])
    violations: list[str] = []

    def _scan(path: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                key = str(raw_key)
                child_path = f"{path}.{key}" if path else key
                if isinstance(child, str):
                    token = child.strip()
                    if key in {"brick_kind", "brick_kind_ref"}:
                        token = token.removeprefix("brick-kind:")
                        if token not in allowed_kinds:
                            violations.append(
                                f"operating vocabulary v1 rejects Brick kind at {child_path}: {child}"
                            )
                    elif key == "step_template_ref" and token.startswith(
                        "building-step-template:"
                    ):
                        kind = token.removeprefix("building-step-template:")
                        if kind not in allowed_kinds:
                            violations.append(
                                f"operating vocabulary v1 rejects step kind at {child_path}: {child}"
                            )
                    elif key in {"agent_lane", "agent_lane_ref", "agent_object_ref"}:
                        lane = token.removeprefix("agent-object:").removeprefix("agent-lane:")
                        if lane not in allowed_lanes:
                            violations.append(
                                f"operating vocabulary v1 rejects Agent lane at {child_path}: {child}"
                            )
                    elif key in {"chain_preset", "chain_preset_ref"}:
                        preset = token.removeprefix("building-chain-preset:")
                        if preset not in allowed_presets:
                            violations.append(
                                f"operating vocabulary v1 rejects chain preset at {child_path}: {child}"
                            )
                _scan(child_path, child)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, child in enumerate(value):
                _scan(f"{path}[{index}]", child)

    _scan("payload", payload)
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
        if field == "structure_draft":
            _validate_structure_plan_draft(section.get("structure_plan_draft"), violations)


def _validate_structure_plan_draft(value: Any, violations: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping):
        violations.append("structure_draft.structure_plan_draft must be a mapping when supplied")
        return
    extra = sorted(str(key) for key in value if str(key) not in STRUCTURE_PLAN_DRAFT_ALLOWED_KEYS)
    if extra:
        violations.append(
            "structure_draft.structure_plan_draft may declare only nodes, edges, coo_gate_edge, "
            "fan_out_groups, fan_in_groups, terminal, reroute_budgets, node_reroute_budgets; "
            "observed "
            + ", ".join(extra)
        )
    fan_out_groups = value.get("fan_out_groups")
    has_fan_out = (
        isinstance(fan_out_groups, Sequence)
        and not isinstance(fan_out_groups, (str, bytes, bytearray))
        and bool(fan_out_groups)
    )
    if has_fan_out:
        _validate_structure_plan_draft_coo_gate(value.get("coo_gate_edge"), violations)


def _validate_structure_plan_draft_coo_gate(value: Any, violations: list[str]) -> None:
    if not isinstance(value, Mapping):
        violations.append(
            "structure_draft.structure_plan_draft fan_out_groups require coo_gate_edge"
        )
        return
    if not isinstance(value.get("to"), str) or not value.get("to", "").strip():
        violations.append("structure_draft.structure_plan_draft.coo_gate_edge requires to")
    if value.get("state") != HELD_FOR_COO_REVIEW_STATE:
        violations.append(
            "structure_draft.structure_plan_draft.coo_gate_edge.state must be held_for_coo_review"
        )


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
    "OPERATING_VOCABULARY_PATH",
    "OPERATING_VOCABULARY_SCHEMA",
    "load_operating_vocabulary",
    "operating_vocabulary_violations",
]
