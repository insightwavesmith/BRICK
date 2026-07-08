"""Literal route request matching and route Link row materialization.

This support helper is evidence plumbing only. It does not choose Movement,
judge quality, execute repair, schedule retry, or call providers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.link.spec import (
    ROUTE_REPLAY_ALLOWED_AUTHOR_PREFIXES as ALLOWED_AUTHOR_PREFIXES,
)
from brick_protocol.support.recording.contracts import require_positive_int


PROOF_LIMITS = (
    "support evidence only",
    "literal match only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN = (
    "semantic correctness of QA route requests",
    "semantic correctness of declared route replay plans",
    "Link decision packet as BAL fact",
    "automatic repair/replay execution",
    "automatic child Building generation",
)
# ALLOWED_AUTHOR_PREFIXES is the Link author vocabulary, single-sourced at
# brick_protocol/link/spec.py (E2/S4) and imported above (byte-identical tuple, same order).
FORBIDDEN_AUTHOR_PREFIXES = (
    "support:",
    "run.py:",
    "runner:",
    "adapter:",
    "agent:",
    "agent-object:",
    "provider:",
    "session:",
    "tool:",
    "hook:",
    "credential:",
    "secret:",
    "token:",
)
FORBIDDEN_KEYS = {
    "route_policy_fact",
    "routepolicyfact",
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
TRANSITION_CONCERN_ALLOWED_KEYS = {
    "concern_ref",
    "concern_kind",
    "reason_refs",
    "related_boundary_refs",
    "binding",
    "proof_limits",
    "not_proven",
}


def materialize_transition_concern_disposition(
    transition_concern: Mapping[str, Any],
    route_policy: Mapping[str, Any],
    declared_route_replay_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize a Link reroute row from non-binding Agent concern evidence."""

    _reject_forbidden_keys(transition_concern, "transition_concern")
    _require_only_keys("transition_concern", transition_concern, TRANSITION_CONCERN_ALLOWED_KEYS)
    concern_ref = _require_prefixed_text(
        transition_concern.get("concern_ref"),
        "transition_concern.concern_ref",
        "transition-concern:",
    )
    concern_kind = _require_text(
        transition_concern.get("concern_kind"),
        "transition_concern.concern_kind",
    )
    if bool(transition_concern.get("binding", False)):
        raise ValueError("transition_concern.binding must be false")
    reason_refs = _string_list(
        transition_concern.get("reason_refs", ()),
        "transition_concern.reason_refs",
    )
    requested_route_scope = _route_scope_for_transition_concern(concern_kind, route_policy)
    if not requested_route_scope:
        return {
            "route_policy_ref": _require_text(route_policy.get("route_policy_ref"), "route_policy_ref"),
            "source_transition_concern_ref": concern_ref,
            "concern_kind": concern_kind,
            "match_state": "missing",
            "materialized": False,
            "materialization_state": "disposition_required",
            "materialization_reason": "transition_concern_kind_not_listed",
            "disposition_boundary": (
                "no Link transition lifecycle or target is materialized "
                "without caller/COO disposition"
            ),
            "related_boundary_refs": _string_list(
                transition_concern.get("related_boundary_refs", ()),
                "transition_concern.related_boundary_refs",
            ),
            "reason_refs": [concern_ref, *reason_refs],
            "required_disposition_owner": "caller-or-coo",
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
    route_request = {
        "request_ref": f"route-request-from-concern:{concern_ref.removeprefix('transition-concern:')}",
        "requested_route_scope": requested_route_scope,
        "reason_refs": [concern_ref, *reason_refs],
        "binding": False,
    }
    materialized = materialize_route_transition(
        route_request,
        route_policy,
        declared_route_replay_plan,
    )
    if materialized.get("materialized") is True:
        packet = dict(materialized["link_decision_packet"])
        packet.update(
            {
                "source_transition_concern_ref": concern_ref,
                "transition_concern_binding": False,
                "materialized_link_row": dict(materialized["link_row"]),
            }
        )
        materialized = {
            **materialized,
            "source_transition_concern_ref": concern_ref,
            "transition_concern_binding": False,
            "link_decision_packet": packet,
        }
    return materialized


def match_route_request(
    route_request: Mapping[str, Any],
    route_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Return literal match evidence for a route request and policy resource."""

    _reject_forbidden_keys(route_request, "route_request")
    _reject_forbidden_keys(route_policy, "route_policy")
    policy_ref = _require_text(route_policy.get("route_policy_ref"), "route_policy_ref")
    if route_policy.get("owner_axis") != "Link":
        raise ValueError("route_policy owner_axis must be Link")
    if route_policy.get("resource_kind") != "route_policy_contract":
        raise ValueError("route_policy resource_kind must be route_policy_contract")
    if route_policy.get("fact_class_admission") != "not_admitted":
        raise ValueError("route_policy fact_class_admission must remain not_admitted")
    if route_policy.get("movement_literal") != "reroute":
        raise ValueError("route_policy movement_literal must be reroute")
    request_ref = _require_text(route_request.get("request_ref"), "route_request.request_ref")
    requested_scope = _require_text(
        route_request.get("requested_route_scope"),
        "route_request.requested_route_scope",
    )
    reason_refs = _string_list(route_request.get("reason_refs", ()), "route_request.reason_refs")
    entries = _mapping_list(route_policy.get("allowed_route_requests"), "allowed_route_requests")
    matches = [
        entry
        for entry in entries
        if entry.get("requested_route_scope") == requested_scope
    ]
    if not matches:
        return _match_evidence(
            policy_ref=policy_ref,
            request_ref=request_ref,
            requested_scope=requested_scope,
            match_state="missing",
            route_path_ref="",
            mismatch_reason="requested_route_scope_not_listed",
        )
    if len(matches) > 1:
        return _match_evidence(
            policy_ref=policy_ref,
            request_ref=request_ref,
            requested_scope=requested_scope,
            match_state="mismatched",
            route_path_ref="",
            mismatch_reason="duplicate_requested_route_scope",
        )
    entry = matches[0]
    if entry.get("route_reason_refs_required") is True and not reason_refs:
        return _match_evidence(
            policy_ref=policy_ref,
            request_ref=request_ref,
            requested_scope=requested_scope,
            match_state="missing",
            route_path_ref="",
            mismatch_reason="route_reason_refs_missing",
        )
    route_path_ref = _require_prefixed_text(
        entry.get("route_path_ref"),
        "allowed_route_requests[].route_path_ref",
        "route-path:",
    )
    return _match_evidence(
        policy_ref=policy_ref,
        request_ref=request_ref,
        requested_scope=requested_scope,
        match_state="matched",
        route_path_ref=route_path_ref,
        mismatch_reason="",
        target_step=_require_text(entry.get("target_step"), "allowed_route_requests[].target_step"),
        replay_steps=_string_list(entry.get("replay_steps", ()), "allowed_route_requests[].replay_steps"),
        human_gate_required=bool(entry.get("human_gate_required", False)),
        policy_replay_segment_refs=_string_list(
            entry.get("replay_segment_refs", ()),
            "allowed_route_requests[].replay_segment_refs",
        ),
    )


def _route_scope_for_transition_concern(
    concern_kind: str,
    route_policy: Mapping[str, Any],
) -> str:
    entries = route_policy.get("allowed_transition_concerns", ())
    if not isinstance(entries, list):
        raise ValueError("route_policy.allowed_transition_concerns must be a list when supplied")
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("concern_kind") == concern_kind
    ]
    if not matches:
        return ""
    if len(matches) > 1:
        raise ValueError("route_policy.allowed_transition_concerns contains duplicate concern_kind")
    return _require_text(matches[0].get("requested_route_scope"), "allowed_transition_concerns[].requested_route_scope")


def _require_only_keys(label: str, value: Mapping[str, Any], allowed: set[str]) -> None:
    unexpected = sorted(str(key) for key in value if key not in allowed)
    if unexpected:
        raise ValueError(f"{label} contains unadmitted key(s): {unexpected}")


def materialize_route_transition(
    route_request: Mapping[str, Any],
    route_policy: Mapping[str, Any],
    declared_route_replay_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize a reroute Link row candidate from a caller-declared replay plan."""

    match = match_route_request(route_request, route_policy)
    if match["match_state"] != "matched":
        return {
            **match,
            "materialized": False,
            "materialization_state": "not_materialized",
            "materialization_reason": match.get("mismatch_reason", "not_matched"),
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
    _reject_forbidden_keys(declared_route_replay_plan, "declared_route_replay_plan")
    route_replay_ref = _require_prefixed_text(
        declared_route_replay_plan.get("route_replay_ref"),
        "route_replay_ref",
        "route-replay:",
    )
    author_ref = _require_text(declared_route_replay_plan.get("author_ref"), "author_ref")
    _validate_author_ref(author_ref)
    immediate_target_ref = _require_brick_ref(
        declared_route_replay_plan.get("immediate_target_ref"),
        "immediate_target_ref",
    )
    source_brick_refs = _brick_ref_list(
        declared_route_replay_plan.get("source_brick_refs", ()),
        "source_brick_refs",
    )
    affected_downstream_refs = _brick_ref_list(
        declared_route_replay_plan.get("affected_downstream_refs", ()),
        "affected_downstream_refs",
    )
    replay_segment_refs = _brick_ref_list(
        declared_route_replay_plan.get("replay_segment_refs", ()),
        "replay_segment_refs",
    )
    max_attempts = declared_route_replay_plan.get("max_attempts")
    authoring_basis_refs = _string_list(
        declared_route_replay_plan.get("authoring_basis_refs", ()),
        "authoring_basis_refs",
    )
    reason_refs = _string_list(route_request.get("reason_refs", ()), "route_request.reason_refs")
    route_replay_plan = {
        "route_replay_ref": route_replay_ref,
        "author_ref": author_ref,
        "authoring_basis_refs": _dedupe_texts(
            [
                *authoring_basis_refs,
            ]
        ),
        "immediate_target_ref": immediate_target_ref,
        "source_brick_refs": source_brick_refs,
        "route_reason_refs": reason_refs,
        "affected_downstream_refs": affected_downstream_refs,
        "replay_segment_refs": replay_segment_refs,
    }
    if max_attempts is not None:
        route_replay_plan["max_attempts"] = _positive_int(max_attempts, "max_attempts")
    link_row = {
        "axis": "Link",
        "movement": "reroute",
        "target_ref": immediate_target_ref,
        "next_brick_instance_ref": immediate_target_ref,
        "route_replay_plan": route_replay_plan,
    }
    link_decision_packet = _link_decision_packet(
        route_request=route_request,
        match=match,
        link_row=link_row,
    )
    return {
        **match,
        "materialized": True,
        "materialization_state": "materialized",
        "movement": "reroute",
        "target_ref": immediate_target_ref,
        "link_row": link_row,
        "link_decision_packet": link_decision_packet,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _link_decision_packet(
    *,
    route_request: Mapping[str, Any],
    match: Mapping[str, Any],
    link_row: Mapping[str, Any],
) -> dict[str, Any]:
    route_plan_value = link_row.get("route_replay_plan")
    if not isinstance(route_plan_value, Mapping):
        raise ValueError("link_row.route_replay_plan must be a mapping")
    route_plan = dict(route_plan_value)
    return {
        "link_decision_packet_ref": f"link-decision-packet:{route_plan['route_replay_ref'].removeprefix('route-replay:')}",
        "owner_axis": "Link",
        "resource_kind": "link_decision_packet",
        "fact_class_admission": "not_admitted",
        "evidence_view_of": "materialized_link_row",
        "source_request_ref": match["request_ref"],
        "route_policy_ref": match["route_policy_ref"],
        "route_path_ref": match["route_path_ref"],
        "route_request_binding": bool(route_request.get("binding", False)),
        "movement": link_row["movement"],
        "target_ref": link_row["target_ref"],
        "route_replay_plan": route_plan,
        "materialized_link_row": dict(link_row),
        "proof_limits": [
            *PROOF_LIMITS,
            "link_decision_packet is an evidence view of an existing Link row",
            "not a new BAL fact class",
        ],
        "not_proven": list(NOT_PROVEN),
    }


def _match_evidence(
    *,
    policy_ref: str,
    request_ref: str,
    requested_scope: str,
    match_state: str,
    route_path_ref: str,
    mismatch_reason: str,
    target_step: str = "",
    replay_steps: list[str] | None = None,
    human_gate_required: bool = False,
    policy_replay_segment_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "route_policy_ref": policy_ref,
        "request_ref": request_ref,
        "requested_route_scope": requested_scope,
        "match_state": match_state,
        "route_path_ref": route_path_ref,
        "target_step": target_step,
        "replay_steps": list(replay_steps or ()),
        "mismatch_reason": mismatch_reason,
        "human_gate_required": human_gate_required,
        "policy_replay_segment_refs": list(policy_replay_segment_refs or ()),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{label} must be a list of mappings")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _require_prefixed_text(value: Any, label: str, prefix: str) -> str:
    text = _require_text(value, label)
    if not text.startswith(prefix):
        raise ValueError(f"{label} must start with {prefix}")
    return text


def _require_brick_ref(value: Any, label: str) -> str:
    return _require_prefixed_text(value, label, "brick-")


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return [item.strip() for item in value]


def _brick_ref_list(value: Any, label: str) -> list[str]:
    refs = _string_list(value, label)
    for ref in refs:
        if not ref.startswith("brick-"):
            raise ValueError(f"{label} items must start with brick-")
    return refs


def _positive_int(value: Any, label: str) -> int:
    return require_positive_int(value, label)


def _dedupe_texts(values: list[str]) -> list[str]:
    observed: list[str] = []
    for value in values:
        if value and value not in observed:
            observed.append(value)
    return observed


def _validate_author_ref(author_ref: str) -> None:
    if author_ref.startswith(FORBIDDEN_AUTHOR_PREFIXES):
        raise ValueError("author_ref must not name support, Agent, provider, session, tool, hook, credential, or token refs")
    if not author_ref.startswith(ALLOWED_AUTHOR_PREFIXES):
        raise ValueError("author_ref must start with human:, coo:, link-planning-brick:, or template:")


def _reject_forbidden_keys(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).replace("-", "_").lower()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"{label} contains forbidden key {key}")
            _reject_forbidden_keys(child, label)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_keys(child, label)
