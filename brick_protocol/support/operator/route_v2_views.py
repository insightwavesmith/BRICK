"""Route V2 read-only projection helpers.

Route V2 is a sealed materialization view over existing Agent concern, Link
route policy, and caller-declared replay facts. This module does not create a
new route engine, does not choose Movement or route targets, does not judge
success/quality, and does not call the walker. It reads caller-supplied packets
and renders support evidence only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from brick_protocol.agent.return_fact import (
    TRANSITION_CONCERN_KINDS,
    is_non_reroute_transition_concern_kind,
    validate_transition_concern_evidence,
)
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.support.operator.route_materialization import (
    materialize_transition_concern_disposition,
)

ROUTE_V2_VIEW_SCHEMA = "route-v2-read-only-view/v1"
# Pure-dev D1 (beyond SHAPE A min slice): shared sealed classifier used by both
# the read-only view path and the walker observation path (SHAPE B helper).
# Still not Movement authority — classification evidence only.
ROUTE_V2_SHARED_CLASSIFIER_REF = "route_v2_shared_eligibility_v1"
GATE_LIFECYCLE_STATES: tuple[str, ...] = ("hold", "paused", "held_for_coo_review")
NON_REROUTE_ROUTE_V2_CONCERN_KINDS: tuple[str, ...] = tuple(
    sorted(kind for kind in TRANSITION_CONCERN_KINDS if is_non_reroute_transition_concern_kind(kind))
)
REROUTE_ELIGIBLE_ROUTE_V2_CONCERN_KINDS: tuple[str, ...] = tuple(
    sorted(kind for kind in TRANSITION_CONCERN_KINDS if not is_non_reroute_transition_concern_kind(kind))
)
DELTA_QA_FACT_FIELDS: tuple[str, ...] = (
    "made_changes",
    "changed_files",
    "diff_refs",
    "evidence_refs",
)
PROOF_LIMITS: tuple[str, ...] = (
    "support read-only projection evidence only",
    "not a new route engine",
    "not route_scope",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not walker integration",
)
NOT_PROVEN: tuple[str, ...] = (
    "semantic correctness of Agent concern evidence",
    "caller/COO disposition after this view",
    "future route_materialization behavior beyond the consumed inputs",
    "future walker integration behavior",
)
_FORBIDDEN_TOP_LEVEL_KEYS = frozenset(
    {
        "movement",
        "movement_choice",
        "route_target",
        "target_ref",
        "success",
        "failure",
        "quality",
        "approved",
        "good_enough",
        "auto_repair",
        "auto_replay",
        "walker_kernel",
        "walker_resume",
        "route_scope",
        "route_v2_engine",
    }
)


def classify_route_v2_concern_eligibility(concern_kind: str) -> dict[str, Any]:
    """Shared sealed classifier for Route V2 concern eligibility (SHAPE B slice).

    Beyond SHAPE A (advisory-only overlay): view rendering and walker observation
    both call this single helper so eligibility cannot drift between paths.
    Does **not** choose Movement, route_target, or walker control flow — Link
    still owns Movement. Support classification evidence only.
    """

    kind = _required_text(concern_kind, "concern_kind")
    if kind not in TRANSITION_CONCERN_KINDS:
        raise ValueError(f"concern_kind is not admitted: {kind}")
    non_reroute = is_non_reroute_transition_concern_kind(kind)
    return {
        "kind": "route_v2_shared_eligibility_classification",
        "classifier_ref": ROUTE_V2_SHARED_CLASSIFIER_REF,
        "shape": "shape_b_shared_helper",
        "concern_kind": kind,
        "non_reroute": non_reroute,
        "reroute_eligible": not non_reroute,
        "allowed_concern_kinds": sorted(TRANSITION_CONCERN_KINDS),
        "proof_limits": [
            "shared sealed concern eligibility classification only",
            "not Movement authority",
            "not route_target choice",
            "not walker control-flow authority",
            "not source truth",
            "not success judgment",
            "not quality judgment",
        ],
        "not_proven": [
            "semantic correctness of the Agent concern body",
            "caller/COO disposition after this classification",
        ],
    }


def render_route_v2_view(
    *,
    transition_concern_evidence: Mapping[str, Any],
    route_policy: Mapping[str, Any] | None = None,
    declared_route_replay_plan: Mapping[str, Any] | None = None,
    gate_state: str = "",
    movement_candidate: str = "",
    delta_qa_fact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Render one Route V2 support projection.

    The returned packet separates sealed concern-kind observation, route-policy
    eligibility observation, optional existing route materialization view,
    gate_state, movement_candidate, and factual delta-QA fields. It never
    authors Movement, target, success, quality, or a new route engine surface.
    """

    _reject_forbidden_keys(transition_concern_evidence, "transition_concern_evidence")
    concern = validate_transition_concern_evidence(transition_concern_evidence)
    concern_kind = _required_text(concern.get("concern_kind"), "concern_kind")
    gate_state_text = _optional_text(gate_state)
    movement_candidate_text = _optional_text(movement_candidate)
    if movement_candidate_text and movement_candidate_text not in MOVEMENT_LITERALS:
        raise ValueError("movement_candidate must be forward or reroute when supplied")
    if gate_state_text in MOVEMENT_LITERALS:
        raise ValueError("gate_state must not be a Movement literal")

    shared = classify_route_v2_concern_eligibility(concern_kind)
    route_policy_eligibility = _route_policy_eligibility(concern_kind, route_policy)
    materialization_view: Mapping[str, Any] | None = None
    if route_policy is not None and declared_route_replay_plan is not None:
        materialization_view = materialize_transition_concern_disposition(
            concern,
            route_policy,
            declared_route_replay_plan,
        )

    return {
        "schema": ROUTE_V2_VIEW_SCHEMA,
        "route_v2_shape": "shape_b_shared_helper",
        "shared_eligibility_classification": shared,
        "sealed_concern_kind_observation": {
            "concern_kind": concern_kind,
            "allowed_concern_kinds": sorted(TRANSITION_CONCERN_KINDS),
            "non_reroute": shared["non_reroute"],
            "reroute_eligible": shared["reroute_eligible"],
            "classifier_ref": ROUTE_V2_SHARED_CLASSIFIER_REF,
        },
        "route_policy_eligibility_observation": route_policy_eligibility,
        "materialization_view": materialization_view,
        "gate_state": gate_state_text,
        "movement_candidate": movement_candidate_text,
        "movement_candidate_proof_limit": (
            "support-projected candidate text only; Link still owns Movement"
            if movement_candidate_text
            else "no movement candidate supplied"
        ),
        "delta_qa_fact": _normalize_delta_qa_fact(delta_qa_fact),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def render_route_v2_view_json(**kwargs: Any) -> str:
    """Render deterministic JSON for one Route V2 view packet."""

    return json.dumps(render_route_v2_view(**kwargs), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def route_v2_policy_packet() -> dict[str, Any]:
    """Return the sealed Route V2 read-only policy as support evidence."""

    return {
        "schema": "route-v2-read-only-policy/v1",
        "allowed_concern_kinds": sorted(TRANSITION_CONCERN_KINDS),
        "non_reroute_concern_kinds": list(NON_REROUTE_ROUTE_V2_CONCERN_KINDS),
        "reroute_eligible_concern_kinds": list(REROUTE_ELIGIBLE_ROUTE_V2_CONCERN_KINDS),
        "movement_literals": list(MOVEMENT_LITERALS),
        "gate_lifecycle_states": list(GATE_LIFECYCLE_STATES),
        "delta_qa_fact_fields": list(DELTA_QA_FACT_FIELDS),
        "forbidden_surfaces": [
            "brick_protocol/support/operator/route_scope.py",
            "brick_protocol/support/operator/route_v2_engine.py",
            "brick_protocol/support/operator/walker_kernel.py",
            "brick_protocol/support/operator/walker_resume.py",
            "brick_protocol/link/**",
            "brick_protocol/agent/return_fact.py",
        ],
        "proof_limits": list(PROOF_LIMITS),
    }


def _route_policy_eligibility(
    concern_kind: str,
    route_policy: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if route_policy is None:
        return {
            "concern_kind": concern_kind,
            "route_policy_supplied": False,
            "eligible": not is_non_reroute_transition_concern_kind(concern_kind),
            "match_state": "not_evaluated",
            "reason": "route_policy not supplied",
        }
    _reject_forbidden_keys(route_policy, "route_policy")
    entries = route_policy.get("allowed_transition_concerns", ())
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        raise ValueError("route_policy.allowed_transition_concerns must be a sequence")
    matching = [entry for entry in entries if isinstance(entry, Mapping) and entry.get("concern_kind") == concern_kind]
    if is_non_reroute_transition_concern_kind(concern_kind):
        return {
            "concern_kind": concern_kind,
            "route_policy_supplied": True,
            "eligible": False,
            "match_state": "non_reroute_concern_kind",
            "reason": "verification_gap is non-reroute evidence",
        }
    if not matching:
        return {
            "concern_kind": concern_kind,
            "route_policy_supplied": True,
            "eligible": False,
            "match_state": "missing",
            "reason": "concern_kind not listed in route policy",
        }
    if len(matching) > 1:
        return {
            "concern_kind": concern_kind,
            "route_policy_supplied": True,
            "eligible": False,
            "match_state": "duplicate",
            "reason": "duplicate concern_kind rows in route policy",
        }
    return {
        "concern_kind": concern_kind,
        "route_policy_supplied": True,
        "eligible": True,
        "match_state": "matched",
        "requested_route_scope": _required_text(
            matching[0].get("requested_route_scope"),
            "allowed_transition_concerns[].requested_route_scope",
        ),
        "reason": "literal concern_kind match only",
    }


def _normalize_delta_qa_fact(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return {}
    _reject_forbidden_keys(value, "delta_qa_fact")
    return {
        "made_changes": bool(value.get("made_changes", False)),
        "changed_files": _string_list(value.get("changed_files", ()), "delta_qa_fact.changed_files"),
        "diff_refs": _string_list(value.get("diff_refs", ()), "delta_qa_fact.diff_refs"),
        "evidence_refs": _string_list(value.get("evidence_refs", ()), "delta_qa_fact.evidence_refs"),
    }


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a sequence of text")
    result = [_required_text(item, label) for item in value]
    return result


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("optional text values must be text")
    return value.strip()


def _reject_forbidden_keys(value: Mapping[str, Any], label: str) -> None:
    found = sorted(str(key) for key in value if str(key) in _FORBIDDEN_TOP_LEVEL_KEYS)
    if found:
        raise ValueError(f"{label} contains forbidden Route V2 view key(s): {', '.join(found)}")


__all__ = [
    "ROUTE_V2_VIEW_SCHEMA",
        "GATE_LIFECYCLE_STATES",
    "DELTA_QA_FACT_FIELDS",
    "PROOF_LIMITS",
    "NOT_PROVEN",
    "render_route_v2_view",
    "render_route_v2_view_json",
    "route_v2_policy_packet",
]
