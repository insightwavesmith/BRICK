"""Confirmed-only Building Call lowering support.

GOAL ⑤g: lower a confirmed Building Call request into the existing
``materialize_building_intent`` input shape. This module does not launch, run,
choose Movement, choose a route target, or judge success / quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


BUILDING_CALL_LOWERING_SCHEMA_VERSION = "building-call-lowering-v1"
CONFIRMED_BUILDING_CALL_REQUEST_KIND = "confirmed_building_call_request_v1_1"
CONFIRMED_STATE = "confirmed"
HELD_FOR_COO_REVIEW_STATE = "held_for_coo_review"

BUILDING_CASE_TO_CHAIN_PRESET_REF: Mapping[str, str] = {
    "order_authoring": "building-chain-preset:building-call-authoring",
    "simple_delivery": "building-chain-preset:app-feature-basic",
    "standard_delivery": "building-chain-preset:app-feature-inspected",
    "governed_change": "building-chain-preset:governed-change-review",
    "design_contract": "building-chain-preset:design-contract-only",
    "research_report": "building-chain-preset:research-report",
}

ROSTER_VARIANT_STEP_SELECTIONS: Mapping[str, Mapping[str, Mapping[str, str]]] = {
    "default": {},
    "deep_work": {
        "building-step-template:work": {
            "casting_tier_ref": "casting-tier:deep",
            "casting_lens_ref": "casting-lens:implementation",
        },
    },
    "standard_review": {
        "building-step-template:review": {
            "casting_tier_ref": "casting-tier:standard",
            "casting_lens_ref": "casting-lens:review",
        },
    },
    "light_review": {
        "building-step-template:review": {
            "casting_tier_ref": "casting-tier:light",
            "casting_lens_ref": "casting-lens:review",
        },
    },
    "deep_design": {
        "building-step-template:design": {
            "casting_tier_ref": "casting-tier:deep",
            "casting_lens_ref": "casting-lens:deep-design",
        },
    },
}

_LOWERED_INTENT_ALLOWED_KEYS = frozenset(
    {
        "declared_by",
        "task_source_ref",
        "task_statement",
        "building_id",
        "project_ref",
        "chain_preset_ref",
        "selected_adapter_ref",
        "selected_model_ref",
        "write_scope",
        "step_selection_overrides",
    }
)
_REQUEST_PASSTHROUGH_FIELDS = frozenset(
    {"declared_by", "task_source_ref", "task_statement", "building_id", "project_ref", "write_scope"}
)
_OVERRIDE_ALLOWED_KEYS = frozenset({"step_template_ref", "casting_tier_ref", "casting_lens_ref"})
_FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "launch",
        "run",
        "movement",
        "movement_choice",
        "route_target",
        "success",
        "quality",
        "selected_adapter_ref",
        "selected_model_ref",
        "selected_reasoning_effort_ref",
    }
)


class BuildingCallLoweringError(ValueError):
    """Raised when a Building Call request is not admitted for lowering."""

    def __init__(self, violations: Sequence[str]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


def lower_building_call_request_v1_1(request: Mapping[str, Any]) -> dict[str, Any]:
    """Lower one confirmed Building Call request to a materializer intent packet."""

    violations = validate_building_call_lowering_request(request)
    if violations:
        raise BuildingCallLoweringError(violations)

    building_case = _required_text("building_case", request["building_case"])
    chain_preset_ref = BUILDING_CASE_TO_CHAIN_PRESET_REF[building_case]
    roster_variant = _optional_text(request.get("roster_variant")) or "default"
    step_selection_overrides = _merge_step_selection_overrides(
        ROSTER_VARIANT_STEP_SELECTIONS[roster_variant],
        _request_roster_overrides(request.get("roster_overrides")),
    )

    intent: dict[str, Any] = {
        field: _normalize_json_value(request[field])
        for field in sorted(_REQUEST_PASSTHROUGH_FIELDS)
        if field in request
    }
    intent["chain_preset_ref"] = chain_preset_ref
    # The existing materializer requires the plan-level adapter declaration.
    # Lowering supplies the neutral local adapter floor; concrete per-step
    # casting remains provider-neutral tier/lens authoring rows.
    intent["selected_adapter_ref"] = "adapter:local"
    intent["selected_model_ref"] = "model:default"
    if step_selection_overrides:
        intent["step_selection_overrides"] = step_selection_overrides

    return {
        "kind": BUILDING_CALL_LOWERING_SCHEMA_VERSION,
        "request_kind": CONFIRMED_BUILDING_CALL_REQUEST_KIND,
        "lowered_intent": intent,
        "building_case": building_case,
        "chain_preset_ref": chain_preset_ref,
        "selected_casting_provenance": {
            "roster_variant": roster_variant,
            "roster_override_count": len(_request_roster_overrides(request.get("roster_overrides"))),
            "step_template_refs": sorted(step_selection_overrides),
            "casting_fields": ["casting_tier_ref", "casting_lens_ref"],
        },
        "proof_limits": [
            "support lowering evidence only",
            "confirmed request to existing materialize_building_intent input shape only",
            "no Building launch",
            "no run_building_plan call",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of the caller-authored request",
            "provider readiness for later materialization",
            "future Building execution behavior",
        ],
    }


def building_call_lowering_v1(request: Mapping[str, Any]) -> dict[str, Any]:
    """Public helper for the admitted ⑤g lowering surface."""

    return lower_building_call_request_v1_1(request)


def validate_building_call_lowering_request(request: Mapping[str, Any]) -> list[str]:
    """Return fail-closed lowering violations without launching any work."""

    if not isinstance(request, Mapping):
        return ["request must be a mapping"]
    violations: list[str] = []

    forbidden = sorted(key for key in request if str(key) in _FORBIDDEN_REQUEST_KEYS)
    if forbidden:
        violations.append(f"forbidden request field(s): {', '.join(forbidden)}")

    kind = request.get("kind")
    if kind != CONFIRMED_BUILDING_CALL_REQUEST_KIND:
        violations.append(f"kind must be {CONFIRMED_BUILDING_CALL_REQUEST_KIND}")

    confirmation_state = request.get("confirmation_state")
    if confirmation_state != CONFIRMED_STATE:
        violations.append("confirmation_state must be confirmed")

    gate_state = request.get("gate_state")
    lifecycle_state = request.get("lifecycle_state")
    if gate_state == HELD_FOR_COO_REVIEW_STATE or lifecycle_state == HELD_FOR_COO_REVIEW_STATE:
        violations.append("held_for_coo_review requests must not be lowered")

    building_case = _optional_text(request.get("building_case"))
    if building_case not in BUILDING_CASE_TO_CHAIN_PRESET_REF:
        allowed = ", ".join(sorted(BUILDING_CASE_TO_CHAIN_PRESET_REF))
        violations.append(f"building_case must be one of: {allowed}")

    roster_variant = _optional_text(request.get("roster_variant")) or "default"
    if roster_variant not in ROSTER_VARIANT_STEP_SELECTIONS:
        allowed = ", ".join(sorted(ROSTER_VARIANT_STEP_SELECTIONS))
        violations.append(f"roster_variant must be one of: {allowed}")

    if not (_optional_text(request.get("task_source_ref")) or _optional_text(request.get("task_statement"))):
        violations.append("request must declare task_source_ref or task_statement")

    _validate_roster_overrides(request.get("roster_overrides"), violations)
    return violations


def render_building_call_lowering_cases() -> dict[str, Any]:
    """Return the admitted case and roster map as support evidence."""

    return {
        "kind": "building-call-lowering-cases-v1",
        "building_case_to_chain_preset_ref": dict(sorted(BUILDING_CASE_TO_CHAIN_PRESET_REF.items())),
        "roster_variant_step_selection": {
            key: _normalize_json_value(value)
            for key, value in sorted(ROSTER_VARIANT_STEP_SELECTIONS.items())
        },
        "proof_limits": [
            "support lowering case table only",
            "not automatic preset selection from task text",
            "not launch authorization",
            "not Movement authority",
        ],
    }


def render_building_call_lowering_cases_json() -> str:
    """Return deterministic JSON for the lowering case table."""

    return json.dumps(render_building_call_lowering_cases(), ensure_ascii=False, sort_keys=True)


def _request_roster_overrides(value: Any) -> dict[str, Mapping[str, str]]:
    violations: list[str] = []
    overrides = _coerce_roster_overrides(value, violations)
    if violations:
        raise BuildingCallLoweringError(violations)
    return overrides


def _validate_roster_overrides(value: Any, violations: list[str]) -> None:
    _coerce_roster_overrides(value, violations)


def _coerce_roster_overrides(value: Any, violations: list[str]) -> dict[str, Mapping[str, str]]:
    if value is None:
        return {}
    overrides: dict[str, Mapping[str, str]] = {}

    def store(raw_ref: Any, raw_row: Any, label: str) -> None:
        step_template_ref = _optional_text(raw_ref)
        if not step_template_ref or not step_template_ref.startswith("building-step-template:"):
            violations.append(f"{label}.step_template_ref must be a building-step-template ref")
            return
        if not isinstance(raw_row, Mapping):
            violations.append(f"{label} must be a mapping")
            return
        extra = sorted(str(key) for key in raw_row if str(key) not in _OVERRIDE_ALLOWED_KEYS)
        if extra:
            violations.append(
                f"{label} may declare only step_template_ref, casting_tier_ref, casting_lens_ref; "
                f"observed {', '.join(extra)}"
            )
        row: dict[str, str] = {}
        tier = _optional_text(raw_row.get("casting_tier_ref"))
        lens = _optional_text(raw_row.get("casting_lens_ref"))
        if lens and not tier:
            violations.append(f"{label}.casting_lens_ref requires casting_tier_ref")
        if tier:
            if not tier.startswith("casting-tier:"):
                violations.append(f"{label}.casting_tier_ref must be a casting-tier ref")
            row["casting_tier_ref"] = tier
        if lens:
            if not lens.startswith("casting-lens:"):
                violations.append(f"{label}.casting_lens_ref must be a casting-lens ref")
            row["casting_lens_ref"] = lens
        if not row:
            violations.append(f"{label} must declare casting_tier_ref or casting_lens_ref")
        if step_template_ref in overrides:
            violations.append(f"duplicate roster override for {step_template_ref}")
        else:
            overrides[step_template_ref] = row

    if isinstance(value, Mapping):
        for raw_ref, raw_row in value.items():
            store(raw_ref, raw_row, f"roster_overrides.{raw_ref}")
        return overrides
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, raw_row in enumerate(value):
            if not isinstance(raw_row, Mapping):
                violations.append(f"roster_overrides[{index}] must be a mapping")
                continue
            store(raw_row.get("step_template_ref"), raw_row, f"roster_overrides[{index}]")
        return overrides
    violations.append("roster_overrides must be a mapping or an array")
    return {}


def _merge_step_selection_overrides(
    base: Mapping[str, Mapping[str, str]],
    overrides: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    merged = {key: dict(value) for key, value in base.items()}
    for key, value in overrides.items():
        merged[key] = dict(value)
    return {key: merged[key] for key in sorted(merged)}


def _required_text(label: str, value: Any) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"{label} must be non-empty text")
    return text


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item) for item in value]
    return value


__all__ = [
    "BUILDING_CALL_LOWERING_SCHEMA_VERSION",
    "CONFIRMED_BUILDING_CALL_REQUEST_KIND",
    "BUILDING_CASE_TO_CHAIN_PRESET_REF",
    "ROSTER_VARIANT_STEP_SELECTIONS",
    "BuildingCallLoweringError",
    "building_call_lowering_v1",
    "lower_building_call_request_v1_1",
    "validate_building_call_lowering_request",
    "render_building_call_lowering_cases",
    "render_building_call_lowering_cases_json",
]
