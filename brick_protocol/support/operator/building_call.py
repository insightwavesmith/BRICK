"""Confirmed-only Building Call lowering support.

GOAL ⑤g: lower a confirmed Building Call request into the existing
``materialize_building_intent`` input shape. This module does not launch, run,
choose Movement, choose a route target, or judge success / quality.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.recording.contracts import require_positive_int
from brick_protocol.support.operator.building_call_authoring import (
    BuildingCallAuthoringValidationError,
    REQUIRED_AUTHORING_RETURN_FIELDS,
    normalize_building_call_authoring_return,
    operating_vocabulary_violations,
)
from brick_protocol.support.operator.draft_diff import diff_declarations
from brick_protocol.support.operator.graph_draft import (
    SIZING_ANSWER_ENUMS,
    SIZING_QUESTION_IDS,
    answer_fingerprint,
    draft_graph_declaration,
)
from brick_protocol.support.operator.provider_registry import (
    CASTING_REASONING_EFFORT_DEFAULT,
    CASTING_TIER_DECLARATIONS,
)


BUILDING_CALL_LOWERING_SCHEMA_VERSION = "building-call-lowering-v1"
BUILDING_CALL_DIRECT_ADMISSION_SCHEMA_VERSION = "building-call-direct-preset-admission-v1"
CONFIRMED_BUILDING_CALL_REQUEST_KIND = "confirmed_building_call_request_v1_1"
DIRECT_PRESET_TRIAGE_REQUEST_KIND = "building_call_direct_preset_triage_v1"
CONFIRMED_STATE = "confirmed"
HELD_FOR_COO_REVIEW_STATE = "held_for_coo_review"
ORDER_REVIEW_PACKET_SCHEMA_VERSION = "building-call-order-review-packet-v1"
ORDER_QUESTION_HOLD_SCHEMA_VERSION = "building-call-order-question-hold-v1"
ORDER_FORWARD_PACKET_SCHEMA_VERSION = "building-call-order-forward-packet-v1"
ORDER_RELOWER_PACKET_SCHEMA_VERSION = "building-call-order-relower-packet-v1"
ORDER_DIGEST_ALGORITHM = "sha256"
ORDER_QUESTION_HOLD_STATE = "held_for_authoring_questions"
_ORDER_CHAIN_PROOF_LIMITS: tuple[str, ...] = (
    "deterministic support lowering and review evidence only",
    "no Building execution",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)

BUILDING_CASE_TO_CHAIN_PRESET_REF: Mapping[str, str] = {
    "order_authoring": "building-chain-preset:building-call-authoring",
    "quick_check": "building-chain-preset:quick-check",
    "quick_fix": "building-chain-preset:fast-fix",
    "simple_delivery": "building-chain-preset:app-feature-basic",
    "standard_delivery": "building-chain-preset:app-feature-inspected",
    "governed_change": "building-chain-preset:governed-change-review",
    "design_contract": "building-chain-preset:design-contract-only",
    "research_report": "building-chain-preset:research-report",
}

DIRECT_PRESET_CASES: frozenset[str] = frozenset({"quick_check", "quick_fix"})
DIRECT_RED_FLAG_FIELDS: tuple[str, ...] = ("red_flags", "critical_red_flags")

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
        "building_map",
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
_STRUCTURE_PLAN_ALLOWED_KEYS = frozenset(
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
_FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "adapter_ref",
        "launch",
        "model",
        "model_ref",
        "run",
        "movement",
        "movement_choice",
        "provider",
        "provider_ref",
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


def freeze_building_call_order_v1(
    *,
    task_statement: str,
    sizing_answers: Mapping[str, Any],
    authoring_return: Mapping[str, Any],
    repo_root: Path | str,
    building_id: str,
    declared_by: str = "coo",
    author_ref: str = "coo:building-call-order",
) -> dict[str, Any]:
    """Freeze one reviewed-order candidate, or return a question HOLD.

    The Agent-authored STEP1-STEP5 return remains draft-only.  This deterministic
    support seam consumes the caller/COO's task plus the exact eight intake
    answers, refuses to lower while ``remaining_delta`` is non-empty, and uses
    the existing graph drafter as the sole structure conversion tool.  The
    resulting graph declaration deliberately carries no ``action`` key: the
    existing graph-decl stop default remains in force until a later explicit
    ``forward`` call.
    """

    task = _required_text("task_statement", task_statement)
    bid = _required_text("building_id", building_id)
    declaration_owner = _required_text("declared_by", declared_by)
    author = _required_text("author_ref", author_ref)
    answers = _normalize_order_intake_answers(sizing_answers)
    try:
        normalized_return = normalize_building_call_authoring_return(authoring_return)
    except BuildingCallAuthoringValidationError as exc:
        raise BuildingCallLoweringError(exc.violations) from exc
    authoring_fields = {
        field: _normalize_json_value(normalized_return[field])
        for field in REQUIRED_AUTHORING_RETURN_FIELDS
    }
    questions = _remaining_delta_questions(authoring_fields.get("remaining_delta"))
    if authoring_fields.get("launch_confirmation_state") == "needs_human_gate":
        questions.append(
            "The authoring return requires a human gate decision before deterministic lowering."
        )
    questions = list(dict.fromkeys(questions))
    if questions:
        return {
            "kind": ORDER_QUESTION_HOLD_SCHEMA_VERSION,
            "state": ORDER_QUESTION_HOLD_STATE,
            "task_statement": task,
            "building_id": bid,
            "declared_by": declaration_owner,
            "sizing_answers": answers,
            "answer_fingerprint": answer_fingerprint(answers),
            "authoring_return": authoring_fields,
            "questions": questions,
            "lowering_performed": False,
            "review_packet_created": False,
            "launch_authorized": False,
            "proof_limits": list(_ORDER_CHAIN_PROOF_LIMITS),
            "not_proven": [
                "semantic sufficiency of answers to the returned questions",
                "future Building execution behavior",
            ],
        }

    allowed_paths, forbidden_paths = _authoring_scope_paths(authoring_fields)
    drafted = draft_graph_declaration(
        task,
        answers,
        repo_root=repo_root,
        building_id=bid,
        allowed_paths=allowed_paths,
        forbidden_paths=forbidden_paths,
        declared_by=declaration_owner,
        author_ref=author,
    )
    precheck = _normalize_json_value(drafted.precheck)
    if precheck.get("composed_ok") is not True:
        evidence = str(precheck.get("reject_evidence") or "graph draft precheck rejected")
        raise BuildingCallLoweringError((f"order graph draft rejected: {evidence}",))

    frozen_order = _normalize_json_value(drafted.declaration)
    if "action" in frozen_order:
        raise BuildingCallLoweringError(
            ("frozen order must omit action so the existing stop default remains authoritative",)
        )
    casting_table = _declared_order_casting_table(frozen_order)
    basis = {
        "task_statement": task,
        "building_id": bid,
        "declared_by": declaration_owner,
        "author_ref": author,
        "sizing_answers": answers,
        "authoring_return": authoring_fields,
        "frozen_order": frozen_order,
        "declared_casting_table": casting_table,
    }
    digest = _order_digest(basis)
    warnings = _normalize_json_value(precheck.get("ungated_write_node_warnings") or [])
    checklist = [
        {
            "check_ref": "remaining-delta-empty",
            "observed": True,
            "requires_attention": False,
        },
        {
            "check_ref": "graph-precheck-composed",
            "observed": True,
            "requires_attention": False,
        },
        {
            "check_ref": "declared-casting-visible",
            "observed": bool(casting_table),
            "row_count": len(casting_table),
            "requires_attention": not bool(casting_table),
        },
        {
            "check_ref": "ungated-write-warning-review",
            "observed": warnings,
            "requires_attention": bool(warnings),
        },
        {
            "check_ref": "explicit-forward-required",
            "observed": False,
            "requires_attention": True,
        },
    ]
    return {
        "kind": ORDER_REVIEW_PACKET_SCHEMA_VERSION,
        "state": HELD_FOR_COO_REVIEW_STATE,
        "building_id": bid,
        "declared_by": declaration_owner,
        "answer_fingerprint": answer_fingerprint(answers),
        "frozen_order": frozen_order,
        "declared_casting_table": casting_table,
        "rationale": {
            "authoring_observed_evidence": _normalize_json_value(
                authoring_fields.get("observed_evidence") or []
            ),
            "authoring_intensity": _normalize_json_value(
                authoring_fields.get("building_intensity_routing_draft") or {}
            ),
            "graph_rule_rows": _normalize_json_value(drafted.rationale_rows),
            "graph_precheck": precheck,
        },
        "review_checklist": checklist,
        "frozen_order_basis": basis,
        "order_digest_algorithm": ORDER_DIGEST_ALGORITHM,
        "order_digest": digest,
        "lowering_performed": True,
        "forward_required": True,
        "launch_authorized": False,
        "forward_transport": "brick build --graph-decl <frozen-order-path> --forward",
        "proof_limits": list(_ORDER_CHAIN_PROOF_LIMITS),
        "not_proven": [
            "provider readiness at later dispatch",
            "semantic fitness of the authored order",
            "future Building execution behavior",
        ],
    }


def forward_frozen_building_call_order_v1(
    review_packet: Mapping[str, Any],
    *,
    repo_root: Path | str,
    review_action: str,
) -> dict[str, Any]:
    """Return the exact frozen graph only after an explicit, canonical forward.

    This helper does not run the Building.  It re-lowers from the human-editable
    source basis, proves the frozen JSON was not edited directly, and hands the
    exact declaration to the already-existing graph-decl dispatch path.
    """

    action = str(review_action or "").strip().lower()
    if action != "forward":
        raise BuildingCallLoweringError(
            ("review_action must be explicit forward; stop/blank cannot dispatch a frozen order",)
        )
    canonical = _recomputed_order_review_packet(review_packet, repo_root=repo_root)
    return {
        "kind": ORDER_FORWARD_PACKET_SCHEMA_VERSION,
        "state": "forwarded_to_existing_graph_dispatch",
        "building_id": canonical["building_id"],
        "review_action": "forward",
        "explicit_forward_observed": True,
        "order_digest_algorithm": ORDER_DIGEST_ALGORITHM,
        "order_digest": canonical["order_digest"],
        "graph_declaration": _normalize_json_value(canonical["frozen_order"]),
        "declared_casting_table": _normalize_json_value(
            canonical["declared_casting_table"]
        ),
        "dispatch_surface": "existing brick build --graph-decl --forward",
        "dispatch_candidate_ready": True,
        "execution_started": False,
        "proof_limits": list(_ORDER_CHAIN_PROOF_LIMITS),
        "not_proven": [
            "provider readiness at dispatch",
            "future Building execution behavior",
        ],
    }


def relower_building_call_order_v1(
    previous_review_packet: Mapping[str, Any],
    *,
    task_statement: str,
    sizing_answers: Mapping[str, Any],
    revised_authoring_return: Mapping[str, Any],
    repo_root: Path | str,
    building_id: str,
    declared_by: str = "coo",
    author_ref: str = "coo:building-call-order",
) -> dict[str, Any]:
    """Re-lower an edited human draft and expose the deterministic draft diff."""

    previous = _recomputed_order_review_packet(
        previous_review_packet,
        repo_root=repo_root,
    )
    revised = freeze_building_call_order_v1(
        task_statement=task_statement,
        sizing_answers=sizing_answers,
        authoring_return=revised_authoring_return,
        repo_root=repo_root,
        building_id=building_id,
        declared_by=declared_by,
        author_ref=author_ref,
    )
    if revised.get("kind") == ORDER_QUESTION_HOLD_SCHEMA_VERSION:
        return {
            "kind": ORDER_RELOWER_PACKET_SCHEMA_VERSION,
            "state": ORDER_QUESTION_HOLD_STATE,
            "previous_order_digest": previous["order_digest"],
            "review_packet": revised,
            "draft_diff": None,
            "lowering_performed": False,
            "launch_authorized": False,
            "proof_limits": list(_ORDER_CHAIN_PROOF_LIMITS),
        }
    before_basis = previous.get("frozen_order_basis")
    after_basis = revised.get("frozen_order_basis")
    if not isinstance(before_basis, Mapping) or not isinstance(after_basis, Mapping):
        raise BuildingCallLoweringError(("order review packet is missing a diffable basis",))
    measured_diff = diff_declarations(before_basis, after_basis)
    return {
        "kind": ORDER_RELOWER_PACKET_SCHEMA_VERSION,
        "state": HELD_FOR_COO_REVIEW_STATE,
        "previous_order_digest": previous["order_digest"],
        "new_order_digest": revised["order_digest"],
        "review_packet": revised,
        "draft_diff": measured_diff,
        "lowering_performed": True,
        "forward_required": True,
        "launch_authorized": False,
        "proof_limits": list(_ORDER_CHAIN_PROOF_LIMITS),
    }


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
    structure_plan = _request_structure_plan(request.get("structure_plan"))
    if structure_plan:
        building_map: dict[str, Any] = {
            "graph_topology": structure_plan["graph_topology"],
        }
        if structure_plan["node_reroute_budgets"]:
            building_map["node_reroute_budgets"] = structure_plan["node_reroute_budgets"]
        if structure_plan["nodes"]:
            building_map["nodes"] = structure_plan["nodes"]
        if structure_plan["coo_gate_edge"]:
            building_map["coo_gate_edge"] = structure_plan["coo_gate_edge"]
        intent["building_map"] = building_map

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


def building_call_direct_preset_admission_v1(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return direct-preset triage evidence and lower only fast-confirmed quick cases."""

    violations = validate_building_call_direct_preset_admission_request(request)
    if violations:
        raise BuildingCallLoweringError(violations)

    building_case = _required_text("building_case", request["building_case"])
    fast_confirm = request.get("fast_confirm") is True
    red_flags = _direct_red_flags(request.get("red_flags"), "red_flags")
    critical_red_flags = _direct_red_flags(request.get("critical_red_flags"), "critical_red_flags")
    direct_candidate = building_case in DIRECT_PRESET_CASES
    direct_admitted = (
        request.get("direct_preset_admission") is True
        and fast_confirm
        and direct_candidate
        and not red_flags
        and not critical_red_flags
    )

    if critical_red_flags or request.get("intensity") == "critical":
        routing_mode_evidence = "human_gate_first"
        admission_reason = "critical red flag or critical intensity requires human_gate_first triage evidence"
    elif red_flags:
        routing_mode_evidence = "order_authoring"
        admission_reason = "red flag present; default order_authoring triage evidence applies"
    elif not direct_candidate:
        routing_mode_evidence = "order_authoring"
        admission_reason = "only quick_fix and quick_check may use direct_preset triage evidence"
    elif request.get("direct_preset_admission") is not True:
        routing_mode_evidence = "order_authoring"
        admission_reason = "direct_preset_admission was not recorded"
    elif not fast_confirm:
        routing_mode_evidence = "order_authoring"
        admission_reason = "fast_confirm is required before direct lowering"
    else:
        routing_mode_evidence = "direct_preset"
        admission_reason = "quick direct candidate admitted with fast_confirm"

    evidence: dict[str, Any] = {
        "kind": BUILDING_CALL_DIRECT_ADMISSION_SCHEMA_VERSION,
        "request_kind": DIRECT_PRESET_TRIAGE_REQUEST_KIND,
        "building_case": building_case,
        "routing_mode_evidence": routing_mode_evidence,
        "direct_preset_admission": direct_admitted,
        "fast_confirm": fast_confirm,
        "admission_reason": admission_reason,
        "red_flag_count": len(red_flags),
        "critical_red_flag_count": len(critical_red_flags),
        "proof_limits": [
            "support triage evidence only",
            "direct_preset_admission is not launch authorization",
            "fast_confirm is required before direct lowering",
            "no Building launch",
            "no run_building_plan call",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of the caller-authored direct triage request",
            "provider readiness for later materialization",
            "future Building execution behavior",
        ],
    }
    if direct_admitted:
        evidence["lowered_intent"] = lower_building_call_request_v1_1(
            _confirmed_request_from_direct_triage(request, building_case)
        )["lowered_intent"]
        evidence["chain_preset_ref"] = BUILDING_CASE_TO_CHAIN_PRESET_REF[building_case]
    return evidence


def validate_building_call_direct_preset_admission_request(request: Mapping[str, Any]) -> list[str]:
    """Return fail-closed violations for direct-preset triage evidence."""

    if not isinstance(request, Mapping):
        return ["request must be a mapping"]
    violations: list[str] = []
    _scan_forbidden_request_keys(request, "request", violations)

    kind = request.get("kind")
    if kind != DIRECT_PRESET_TRIAGE_REQUEST_KIND:
        violations.append(f"kind must be {DIRECT_PRESET_TRIAGE_REQUEST_KIND}")

    building_case = _optional_text(request.get("building_case"))
    if building_case not in BUILDING_CASE_TO_CHAIN_PRESET_REF:
        allowed = ", ".join(sorted(BUILDING_CASE_TO_CHAIN_PRESET_REF))
        violations.append(f"building_case must be one of: {allowed}")

    intensity = request.get("intensity")
    if intensity not in {"easy", "normal", "complex", "critical"}:
        violations.append("intensity must be one of: easy, normal, complex, critical")

    direct_requested = request.get("direct_preset_admission") is True
    if direct_requested and building_case not in DIRECT_PRESET_CASES:
        violations.append("direct_preset_admission may be true only for quick_fix or quick_check")
    if direct_requested and request.get("fast_confirm") is not True:
        violations.append("fast_confirm is required before direct lowering")
    red_flags = _coerce_direct_red_flags(request.get("red_flags"), "red_flags", violations)
    critical_red_flags = _coerce_direct_red_flags(
        request.get("critical_red_flags"), "critical_red_flags", violations
    )
    if direct_requested and red_flags:
        violations.append("red flags require order_authoring triage evidence")
    if direct_requested and critical_red_flags:
        violations.append("critical red flags require human_gate_first triage evidence")

    if not (_optional_text(request.get("task_source_ref")) or _optional_text(request.get("task_statement"))):
        violations.append("request must declare task_source_ref or task_statement")

    _validate_roster_overrides(request.get("roster_overrides"), violations)
    return violations


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
    _validate_structure_plan(request.get("structure_plan"), violations)
    violations.extend(operating_vocabulary_violations(request))
    return violations


def render_building_call_direct_preset_policy() -> dict[str, Any]:
    """Return the direct-preset admission policy as support evidence."""

    return {
        "kind": "building-call-direct-preset-policy-v1",
        "default_routing_mode_evidence": "order_authoring",
        "direct_preset_cases": sorted(DIRECT_PRESET_CASES),
        "direct_case_to_chain_preset_ref": {
            key: BUILDING_CASE_TO_CHAIN_PRESET_REF[key] for key in sorted(DIRECT_PRESET_CASES)
        },
        "fast_confirm_required": True,
        "red_flag_routing_mode_evidence": "order_authoring",
        "critical_red_flag_routing_mode_evidence": "human_gate_first",
        "proof_limits": [
            "support triage policy evidence only",
            "not launch authorization",
            "not Movement authority",
        ],
    }


def render_building_call_direct_preset_policy_json() -> str:
    """Return deterministic JSON for the direct-preset admission policy."""

    return json.dumps(render_building_call_direct_preset_policy(), ensure_ascii=False, sort_keys=True)


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


def _confirmed_request_from_direct_triage(
    request: Mapping[str, Any],
    building_case: str,
) -> dict[str, Any]:
    confirmed: dict[str, Any] = {
        field: _normalize_json_value(request[field])
        for field in sorted(_REQUEST_PASSTHROUGH_FIELDS)
        if field in request
    }
    confirmed.update(
        {
            "kind": CONFIRMED_BUILDING_CALL_REQUEST_KIND,
            "confirmation_state": CONFIRMED_STATE,
            "building_case": building_case,
        }
    )
    roster_variant = _optional_text(request.get("roster_variant"))
    if roster_variant:
        confirmed["roster_variant"] = roster_variant
    if "roster_overrides" in request:
        confirmed["roster_overrides"] = _normalize_json_value(request["roster_overrides"])
    return confirmed


def _scan_forbidden_request_keys(value: Any, path: str, violations: list[str]) -> None:
    if isinstance(value, Mapping):
        forbidden = sorted(str(key) for key in value if str(key) in _FORBIDDEN_REQUEST_KEYS)
        if forbidden:
            violations.append(f"forbidden request field(s) at {path}: {', '.join(forbidden)}")
        for key, child in value.items():
            _scan_forbidden_request_keys(child, f"{path}.{key}", violations)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_forbidden_request_keys(child, f"{path}[{index}]", violations)


def _request_roster_overrides(value: Any) -> dict[str, Mapping[str, str]]:
    violations: list[str] = []
    overrides = _coerce_roster_overrides(value, violations)
    if violations:
        raise BuildingCallLoweringError(violations)
    return overrides


def _request_structure_plan(value: Any) -> dict[str, Any]:
    violations: list[str] = []
    plan = _coerce_structure_plan(value, violations)
    if violations:
        raise BuildingCallLoweringError(violations)
    return plan


def _validate_structure_plan(value: Any, violations: list[str]) -> None:
    _coerce_structure_plan(value, violations)


def _coerce_structure_plan(value: Any, violations: list[str]) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        violations.append("structure_plan must be a mapping when supplied")
        return {}

    _scan_forbidden_request_keys(value, "structure_plan", violations)
    extra = sorted(str(key) for key in value if str(key) not in _STRUCTURE_PLAN_ALLOWED_KEYS)
    if extra:
        violations.append(
            "structure_plan may declare only nodes, edges, coo_gate_edge, fan_out_groups, "
            "fan_in_groups, terminal, reroute_budgets, node_reroute_budgets; observed "
            + ", ".join(extra)
        )

    edges = _coerce_structure_edges(value.get("edges"), violations)
    fan_out_groups = _coerce_structure_fan_out_groups(value.get("fan_out_groups"), violations)
    fan_in_groups = _coerce_structure_fan_in_groups(value.get("fan_in_groups"), violations)
    terminal = _optional_text(value.get("terminal"))
    nodes = _coerce_structure_nodes(value.get("nodes"), violations)
    coo_gate_edge = _coerce_structure_optional_mapping(
        value.get("coo_gate_edge"), "structure_plan.coo_gate_edge", violations
    )
    _validate_structure_coo_gate_edge(fan_out_groups, coo_gate_edge, violations)
    budgets = _coerce_structure_budgets(
        value.get("node_reroute_budgets", value.get("reroute_budgets")),
        violations,
    )

    if edges and fan_out_groups and fan_in_groups:
        _validate_structure_fan_invariants(
            edges=edges,
            fan_out_groups=fan_out_groups,
            fan_in_groups=fan_in_groups,
            nodes=nodes,
            violations=violations,
        )
    if not edges:
        violations.append("structure_plan.edges must be a non-empty array")
    if not fan_out_groups:
        violations.append("structure_plan.fan_out_groups must be a non-empty array")
    if len(fan_in_groups) != 1:
        violations.append("structure_plan.fan_in_groups must declare exactly one convergence group")
    if not terminal and fan_in_groups:
        terminal = fan_in_groups[0].get("converge_on")

    graph_topology: dict[str, Any] = {
        "edges": edges,
        "fan_out_groups": fan_out_groups,
        "fan_in_groups": fan_in_groups,
    }
    if terminal:
        graph_topology["terminal"] = terminal
    return {
        "graph_topology": _normalize_json_value(graph_topology),
        "node_reroute_budgets": _normalize_json_value(budgets),
        "nodes": _normalize_json_value(nodes),
        "coo_gate_edge": _normalize_json_value(coo_gate_edge),
    }


def _coerce_structure_edges(value: Any, violations: list[str]) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_edge in enumerate(value):
        if not isinstance(raw_edge, Mapping):
            violations.append(f"structure_plan.edges[{index}] must be a mapping")
            continue
        extra = sorted(str(key) for key in raw_edge if str(key) not in {"from", "to"})
        if extra:
            violations.append(
                f"structure_plan.edges[{index}] may declare only from/to; observed {', '.join(extra)}"
            )
        source = _optional_text(raw_edge.get("from"))
        target = _optional_text(raw_edge.get("to"))
        if not source or not target:
            violations.append(f"structure_plan.edges[{index}] requires from and to")
            continue
        if source == target:
            violations.append(f"structure_plan.edges[{index}] must not be a self-loop")
            continue
        pair = (source, target)
        if pair in seen:
            violations.append(f"structure_plan.edges[{index}] duplicates {source!r}->{target!r}")
            continue
        seen.add(pair)
        edges.append({"from": source, "to": target})
    return edges


def _coerce_structure_fan_out_groups(value: Any, violations: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    groups: list[dict[str, Any]] = []
    for index, raw_group in enumerate(value):
        if not isinstance(raw_group, Mapping):
            violations.append(f"structure_plan.fan_out_groups[{index}] must be a mapping")
            continue
        extra = sorted(str(key) for key in raw_group if str(key) not in {"from", "branches"})
        if extra:
            violations.append(
                f"structure_plan.fan_out_groups[{index}] may declare only from/branches; observed {', '.join(extra)}"
            )
        source = _optional_text(raw_group.get("from"))
        branches = _text_list(raw_group.get("branches"))
        if not source or len(branches) < 2:
            violations.append(
                f"structure_plan.fan_out_groups[{index}] requires from and at least two branches"
            )
            continue
        groups.append({"from": source, "branches": branches})
    return groups


def _coerce_structure_fan_in_groups(value: Any, violations: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    groups: list[dict[str, Any]] = []
    for index, raw_group in enumerate(value):
        if not isinstance(raw_group, Mapping):
            violations.append(f"structure_plan.fan_in_groups[{index}] must be a mapping")
            continue
        extra = sorted(
            str(key)
            for key in raw_group
            if str(key)
            not in {"converge_on", "sources", "closure_transition_target_policy", "wait_all"}
        )
        if extra:
            violations.append(
                f"structure_plan.fan_in_groups[{index}] may declare only converge_on/sources/"
                f"closure_transition_target_policy/wait_all; observed {', '.join(extra)}"
            )
        converge_on = _optional_text(raw_group.get("converge_on"))
        sources = _text_list(raw_group.get("sources"))
        if not converge_on or len(sources) < 2:
            violations.append(
                f"structure_plan.fan_in_groups[{index}] requires converge_on and at least two sources"
            )
            continue
        if raw_group.get("wait_all") is False:
            violations.append(f"structure_plan.fan_in_groups[{index}] must preserve wait-all")
        group: dict[str, Any] = {"converge_on": converge_on, "sources": sources}
        if "closure_transition_target_policy" in raw_group:
            policy = raw_group.get("closure_transition_target_policy")
            if not isinstance(policy, Mapping):
                violations.append(
                    f"structure_plan.fan_in_groups[{index}].closure_transition_target_policy must be a mapping"
                )
            else:
                group["closure_transition_target_policy"] = _normalize_json_value(policy)
        groups.append(group)
    return groups


def _coerce_structure_nodes(value: Any, violations: list[str]) -> dict[str, Mapping[str, Any]]:
    if value is None:
        return {}
    nodes: dict[str, Mapping[str, Any]] = {}
    if isinstance(value, Mapping):
        iterable = value.items()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        iterable = ((item.get("ref") if isinstance(item, Mapping) else None, item) for item in value)
    else:
        violations.append("structure_plan.nodes must be a mapping or an array")
        return {}
    for raw_ref, raw_node in iterable:
        ref = _optional_text(raw_ref)
        if not ref:
            violations.append("structure_plan.nodes entries require a non-empty ref")
            continue
        if not isinstance(raw_node, Mapping):
            violations.append(f"structure_plan.nodes[{ref}] must be a mapping")
            continue
        nodes[ref] = raw_node
    return nodes


def _coerce_structure_optional_mapping(
    value: Any, label: str, violations: list[str]
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        violations.append(f"{label} must be a mapping when supplied")
        return {}
    return dict(value)


def _validate_structure_coo_gate_edge(
    fan_out_groups: Sequence[Mapping[str, Any]],
    coo_gate_edge: Mapping[str, Any],
    violations: list[str],
) -> None:
    if not fan_out_groups:
        return
    if not coo_gate_edge:
        violations.append("structure_plan fan_out_groups require coo_gate_edge")
        return
    target = _optional_text(coo_gate_edge.get("to"))
    if not target:
        violations.append("structure_plan.coo_gate_edge requires to")
    if coo_gate_edge.get("state") != HELD_FOR_COO_REVIEW_STATE:
        violations.append("structure_plan.coo_gate_edge.state must be held_for_coo_review")


def _coerce_structure_budgets(value: Any, violations: list[str]) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        violations.append("structure_plan.reroute_budgets must be a mapping when supplied")
        return {}
    budgets: dict[str, int] = {}
    for raw_ref, raw_budget in value.items():
        ref = _optional_text(raw_ref)
        if not ref:
            violations.append("structure_plan.reroute_budgets keys must be non-empty text")
            continue
        try:
            budgets[ref] = require_positive_int(
                raw_budget,
                f"structure_plan.reroute_budgets[{ref}]",
                allow_decimal_text=False,
            )
        except ValueError as exc:
            violations.append(str(exc))
    return budgets


def _validate_structure_fan_invariants(
    *,
    edges: Sequence[Mapping[str, str]],
    fan_out_groups: Sequence[Mapping[str, Any]],
    fan_in_groups: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
    violations: list[str],
) -> None:
    edge_pairs = {(edge["from"], edge["to"]) for edge in edges}
    if len(fan_in_groups) != 1:
        return
    fan_in = fan_in_groups[0]
    converge_on = str(fan_in["converge_on"])
    sources = tuple(str(source) for source in fan_in["sources"])
    for source in sources:
        if (source, converge_on) not in edge_pairs:
            violations.append(
                "structure_plan fan_in_groups source->converge_on must be a declared edge: "
                f"{source} -> {converge_on}"
            )
    fan_out_branches: set[str] = set()
    for group in fan_out_groups:
        source = str(group["from"])
        for branch in group["branches"]:
            branch_text = str(branch)
            fan_out_branches.add(branch_text)
            if (source, branch_text) not in edge_pairs:
                violations.append(
                    "structure_plan fan_out_groups from->branch must be a declared edge: "
                    f"{source} -> {branch_text}"
                )
    if set(sources) != fan_out_branches:
        violations.append(
            "structure_plan fan-out branches must exactly match the single fan-in sources"
        )
    _validate_structure_write_fences(sources, nodes, violations)


def _validate_structure_write_fences(
    branches: Sequence[str],
    nodes: Mapping[str, Mapping[str, Any]],
    violations: list[str],
) -> None:
    allowed_by_branch: dict[str, tuple[str, ...]] = {}
    for branch in branches:
        raw_scope = nodes.get(branch, {}).get("write_scope")
        if raw_scope is None:
            allowed_by_branch[branch] = ()
            continue
        if not isinstance(raw_scope, Mapping):
            violations.append(f"structure_plan.nodes[{branch}].write_scope must be a mapping")
            continue
        allowed = _text_list(raw_scope.get("allowed_paths"))
        allowed_by_branch[branch] = tuple(_normalize_scope_path(path) for path in allowed)
    for index, left in enumerate(branches):
        for right in branches[index + 1 :]:
            overlap = _first_scope_overlap(
                allowed_by_branch.get(left, ()),
                allowed_by_branch.get(right, ()),
            )
            if overlap:
                violations.append(
                    "structure_plan fan-out branch write fences must be pairwise disjoint: "
                    f"{left} and {right} overlap at {overlap}"
                )


def _normalize_scope_path(value: str) -> str:
    return value.strip().strip("/")


def _first_scope_overlap(left: Sequence[str], right: Sequence[str]) -> str:
    for left_path in left:
        if not left_path:
            continue
        for right_path in right:
            if not right_path:
                continue
            if (
                left_path == right_path
                or left_path.startswith(right_path + "/")
                or right_path.startswith(left_path + "/")
            ):
                return left_path if len(left_path) >= len(right_path) else right_path
    return ""


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


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def _direct_red_flags(value: Any, label: str) -> list[str]:
    violations: list[str] = []
    flags = _coerce_direct_red_flags(value, label, violations)
    if violations:
        raise BuildingCallLoweringError(violations)
    return flags


def _coerce_direct_red_flags(value: Any, label: str, violations: list[str]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        flags: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                violations.append(f"{label}[{index}] must be text")
                continue
            text = item.strip()
            if text:
                flags.append(text)
        return flags
    violations.append(f"{label} must be text or an array of text")
    return []


def _normalize_order_intake_answers(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise BuildingCallLoweringError(("sizing_answers must be an object",))
    violations: list[str] = []
    missing = [question for question in SIZING_QUESTION_IDS if question not in value]
    unexpected = sorted(str(key) for key in value if str(key) not in SIZING_QUESTION_IDS)
    if missing:
        violations.append("sizing_answers missing required question(s): " + ", ".join(missing))
    if unexpected:
        violations.append(
            "sizing_answers must contain exactly the eight v1 questions; unexpected: "
            + ", ".join(unexpected)
        )
    normalized: dict[str, str] = {}
    for question in SIZING_QUESTION_IDS:
        raw = value.get(question)
        if not isinstance(raw, str):
            violations.append(f"sizing_answers.{question} must be text")
            continue
        answer = raw.strip().lower()
        allowed = SIZING_ANSWER_ENUMS[question]
        if answer not in allowed:
            violations.append(
                f"sizing_answers.{question} must be one of: {', '.join(allowed)}"
            )
            continue
        normalized[question] = answer
    if violations:
        raise BuildingCallLoweringError(violations)
    return normalized


def _remaining_delta_questions(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BuildingCallLoweringError(
            ("remaining_delta must be an array of explicit question strings",)
        )
    questions: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise BuildingCallLoweringError(
                (f"remaining_delta[{index}] must be a non-empty question string",)
            )
        questions.append(item.strip())
    return questions


def _authoring_scope_paths(
    authoring_return: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    scope = authoring_return.get("scope_draft")
    if not isinstance(scope, Mapping):
        raise BuildingCallLoweringError(("scope_draft must be a mapping",))
    allowed = _order_text_sequence(
        "scope_draft.allowed_path_candidates",
        scope.get("allowed_path_candidates"),
    )
    forbidden = _order_text_sequence(
        "scope_draft.forbidden_path_candidates",
        scope.get("forbidden_path_candidates"),
    )
    return allowed, forbidden or [".git/**"]


def _order_text_sequence(label: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BuildingCallLoweringError((f"{label} must be an array of text",))
    rows: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise BuildingCallLoweringError((f"{label}[{index}] must be non-empty text",))
        rows.append(item.strip())
    return rows


def _declared_order_casting_table(
    graph_declaration: Mapping[str, Any],
) -> list[dict[str, str]]:
    nodes = graph_declaration.get("nodes")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes, bytearray)):
        raise BuildingCallLoweringError(("frozen order nodes must be an array",))
    table: list[dict[str, str]] = []

    def append_row(entry: Mapping[str, Any], node_ref: str) -> None:
        tier_ref = str(entry.get("casting_tier_ref") or "").strip()
        lens_ref = str(entry.get("casting_lens_ref") or "").strip()
        declaration = CASTING_TIER_DECLARATIONS.get(tier_ref)
        rows = declaration.get("adapter_ladder") if isinstance(declaration, Mapping) else None
        if (
            not isinstance(rows, Sequence)
            or isinstance(rows, (str, bytes, bytearray))
            or len(rows) != 1
            or not isinstance(rows[0], Mapping)
        ):
            raise BuildingCallLoweringError(
                (
                    f"{node_ref}: {tier_ref or 'missing casting tier'} must declare exactly "
                    "one frozen performer row; environment-driven ladder selection is forbidden",
                )
            )
        row = rows[0]
        adapter_ref = str(row.get("adapter_ref") or "").strip()
        model_ref = str(row.get("model_ref") or "").strip()
        effort_ref = str(
            row.get("selected_reasoning_effort_ref") or CASTING_REASONING_EFFORT_DEFAULT
        ).strip()
        if not adapter_ref or not model_ref or not lens_ref:
            raise BuildingCallLoweringError(
                (f"{node_ref}: frozen casting requires adapter/model/effort and lens",)
            )
        table.append(
            {
                "node_ref": node_ref,
                "brick_kind": str(entry.get("kind") or "").strip(),
                "casting_tier_ref": tier_ref,
                "casting_lens_ref": lens_ref,
                "selected_adapter_ref": adapter_ref,
                "selected_model_ref": model_ref,
                "selected_reasoning_effort_ref": effort_ref,
                "selection_basis": "single declared casting-tier row; readiness not consulted",
            }
        )

    for node_index, raw_node in enumerate(nodes):
        if not isinstance(raw_node, Mapping):
            raise BuildingCallLoweringError((f"frozen order nodes[{node_index}] must be an object",))
        fan = raw_node.get("fan")
        if fan is None:
            append_row(raw_node, f"nodes[{node_index}]")
            continue
        if not isinstance(fan, Mapping):
            raise BuildingCallLoweringError((f"frozen order nodes[{node_index}].fan must be an object",))
        branches = fan.get("branches")
        if not isinstance(branches, Sequence) or isinstance(
            branches, (str, bytes, bytearray)
        ):
            raise BuildingCallLoweringError(
                (f"frozen order nodes[{node_index}].fan.branches must be an array",)
            )
        for branch_index, branch in enumerate(branches):
            if not isinstance(branch, Mapping):
                raise BuildingCallLoweringError(
                    (
                        f"frozen order nodes[{node_index}].fan.branches[{branch_index}] "
                        "must be an object",
                    )
                )
            append_row(
                branch,
                f"nodes[{node_index}].fan.branches[{branch_index}]",
            )
    if not table:
        raise BuildingCallLoweringError(("frozen order must expose at least one casting row",))
    return table


def _order_digest(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _normalize_json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _recomputed_order_review_packet(
    review_packet: Mapping[str, Any],
    *,
    repo_root: Path | str,
) -> dict[str, Any]:
    if not isinstance(review_packet, Mapping):
        raise BuildingCallLoweringError(("order review packet must be an object",))
    if review_packet.get("kind") != ORDER_REVIEW_PACKET_SCHEMA_VERSION:
        raise BuildingCallLoweringError(
            (f"order review packet kind must be {ORDER_REVIEW_PACKET_SCHEMA_VERSION}",)
        )
    if review_packet.get("state") != HELD_FOR_COO_REVIEW_STATE:
        raise BuildingCallLoweringError(("order review packet must be held_for_coo_review",))
    if review_packet.get("order_digest_algorithm") != ORDER_DIGEST_ALGORITHM:
        raise BuildingCallLoweringError(("order review packet digest algorithm must be sha256",))
    basis = review_packet.get("frozen_order_basis")
    if not isinstance(basis, Mapping):
        raise BuildingCallLoweringError(("order review packet is missing frozen_order_basis",))
    answers = basis.get("sizing_answers")
    authoring_return = basis.get("authoring_return")
    if not isinstance(answers, Mapping) or not isinstance(authoring_return, Mapping):
        raise BuildingCallLoweringError(
            ("order review packet basis must carry sizing_answers and authoring_return",)
        )
    canonical = freeze_building_call_order_v1(
        task_statement=str(basis.get("task_statement") or ""),
        sizing_answers=answers,
        authoring_return=authoring_return,
        repo_root=repo_root,
        building_id=str(basis.get("building_id") or ""),
        declared_by=str(basis.get("declared_by") or ""),
        author_ref=str(basis.get("author_ref") or ""),
    )
    if canonical.get("kind") != ORDER_REVIEW_PACKET_SCHEMA_VERSION:
        raise BuildingCallLoweringError(
            ("edited source now requires question HOLD; it must be re-lowered before forward",)
        )
    if canonical.get("frozen_order_basis") != _normalize_json_value(basis):
        raise BuildingCallLoweringError(
            ("frozen order was edited directly or its declarations changed; re-lower the draft",)
        )
    if canonical.get("order_digest") != review_packet.get("order_digest"):
        raise BuildingCallLoweringError(
            ("frozen order digest mismatch; edit the human draft and re-lower instead",)
        )
    for field in ("frozen_order", "declared_casting_table"):
        if canonical.get(field) != review_packet.get(field):
            raise BuildingCallLoweringError(
                (f"order review packet {field} drifted; direct frozen JSON edits are forbidden",)
            )
    return canonical


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item) for item in value]
    return value


__all__ = [
    "BUILDING_CALL_LOWERING_SCHEMA_VERSION",
    "BUILDING_CALL_DIRECT_ADMISSION_SCHEMA_VERSION",
    "CONFIRMED_BUILDING_CALL_REQUEST_KIND",
    "DIRECT_PRESET_TRIAGE_REQUEST_KIND",
    "ORDER_REVIEW_PACKET_SCHEMA_VERSION",
    "ORDER_QUESTION_HOLD_SCHEMA_VERSION",
    "ORDER_FORWARD_PACKET_SCHEMA_VERSION",
    "ORDER_RELOWER_PACKET_SCHEMA_VERSION",
    "BUILDING_CASE_TO_CHAIN_PRESET_REF",
    "DIRECT_PRESET_CASES",
    "ROSTER_VARIANT_STEP_SELECTIONS",
    "BuildingCallLoweringError",
    "building_call_direct_preset_admission_v1",
    "building_call_lowering_v1",
    "freeze_building_call_order_v1",
    "forward_frozen_building_call_order_v1",
    "relower_building_call_order_v1",
    "lower_building_call_request_v1_1",
    "validate_building_call_direct_preset_admission_request",
    "validate_building_call_lowering_request",
    "render_building_call_direct_preset_policy",
    "render_building_call_direct_preset_policy_json",
    "render_building_call_lowering_cases",
    "render_building_call_lowering_cases_json",
]
