"""Confirmed-only Building Call lowering support.

GOAL ⑤g: lower a confirmed Building Call request into the existing
``materialize_building_intent`` input shape. This module does not launch, run,
choose Movement, choose a route target, or judge success / quality.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from brick_protocol.support.recording.contracts import require_positive_int


BUILDING_CALL_LOWERING_SCHEMA_VERSION = "building-call-lowering-v1"
BUILDING_CALL_DIRECT_ADMISSION_SCHEMA_VERSION = "building-call-direct-preset-admission-v1"
CONFIRMED_BUILDING_CALL_REQUEST_KIND = "confirmed_building_call_request_v1_1"
DIRECT_PRESET_TRIAGE_REQUEST_KIND = "building_call_direct_preset_triage_v1"
CONFIRMED_STATE = "confirmed"
HELD_FOR_COO_REVIEW_STATE = "held_for_coo_review"

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
    "BUILDING_CASE_TO_CHAIN_PRESET_REF",
    "DIRECT_PRESET_CASES",
    "ROSTER_VARIANT_STEP_SELECTIONS",
    "BuildingCallLoweringError",
    "building_call_direct_preset_admission_v1",
    "building_call_lowering_v1",
    "lower_building_call_request_v1_1",
    "validate_building_call_direct_preset_admission_request",
    "validate_building_call_lowering_request",
    "render_building_call_direct_preset_policy",
    "render_building_call_direct_preset_policy_json",
    "render_building_call_lowering_cases",
    "render_building_call_lowering_cases_json",
]
