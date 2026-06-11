"""Public AgentFact surface for Agent.return_fact."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
from typing import Any

TRANSITION_CONCERN_KINDS: frozenset[str] = frozenset(
    {
        "design_gap",
        "implementation_gap",
        "upstream_gap",
        "boundary_mismatch",
        "insufficient_input",
        "replay_needed",
        "verification_gap",
        "unknown",
    }
)
TRANSITION_CONCERN_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "concern_ref",
        "concern_kind",
        "reason_refs",
        "related_boundary_refs",
        "binding",
        "proof_limits",
        "not_proven",
    }
)
RETURNED_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "approved",
        "auth",
        "auth_value",
        "complete",
        "completed",
        "credential",
        "credential_body",
        "credential_value",
        "done",
        "fail",
        "failed",
        "failure",
        "movement",
        "movement_choice",
        "pa" + "ss",
        "quality",
        "quality_judgment",
        "quality_score",
        "raw_secret",
        "result",
        "route_target",
        "score",
        "secret",
        "session",
        "session_id",
        "setup_token",
        "setup_token_value",
        "status",
        "success",
        "success_judgment",
        "target",
        "target_ref",
        "verdict",
    }
)


def _required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _text_tuple(field_name: str, values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for index, value in enumerate(values):
        result.append(_required_text(f"{field_name}[{index}]", value))
    return tuple(result)


def validate_transition_concern_evidence(concern: "Mapping[str, Any]") -> dict:
    for key in concern:
        if not isinstance(key, str) or key not in TRANSITION_CONCERN_ALLOWED_KEYS:
            raise ValueError(f"transition_concern_evidence contains unadmitted key {key!r}")
    concern_ref = _required_text("transition_concern_evidence.concern_ref", concern.get("concern_ref"))
    if not concern_ref.startswith("transition-concern:"):
        raise ValueError("transition_concern_evidence.concern_ref must start with transition-concern:")
    concern_kind = _required_text("transition_concern_evidence.concern_kind", concern.get("concern_kind"))
    if concern_kind not in TRANSITION_CONCERN_KINDS:
        raise ValueError("transition_concern_evidence.concern_kind is not admitted")
    if concern.get("binding") is not False:
        raise ValueError("transition_concern_evidence.binding must be false")
    reason_refs = _text_tuple("transition_concern_evidence.reason_refs", concern.get("reason_refs"))
    if not reason_refs:
        raise ValueError("transition_concern_evidence.reason_refs must be non-empty")
    related_refs = _text_tuple(
        "transition_concern_evidence.related_boundary_refs",
        concern.get("related_boundary_refs", ()),
    )
    for ref in related_refs:
        if not ref.startswith(("brick:", "brick-", "brick-boundary:", "brick-instance:", "building-boundary:")):
            raise ValueError("transition_concern_evidence.related_boundary_refs must name Brick boundaries")
    return dict(concern)


@dataclass(frozen=True)
class AgentFact:
    """Agent records the received work and what was returned."""

    received_work: Any
    returned: Any


def make_agent_fact(
    *,
    received_work: Any = MISSING,
    returned: Any = MISSING,
) -> AgentFact:
    """Create an AgentFact when both public fact values are supplied."""

    missing_fields: list[str] = []
    if received_work is MISSING:
        missing_fields.append("received_work")
    if returned is MISSING:
        missing_fields.append("returned")
    if missing_fields:
        raise ValueError(
            "AgentFact requires public fact value(s): " + ", ".join(missing_fields)
        )
    return AgentFact(received_work=received_work, returned=returned)


AGENT_FACT_FIELDS: tuple[str, ...] = tuple(_f.name for _f in fields(AgentFact))


__all__ = (
    "AgentFact",
    "AGENT_FACT_FIELDS",
    "make_agent_fact",
    "TRANSITION_CONCERN_KINDS",
    "TRANSITION_CONCERN_ALLOWED_KEYS",
    "RETURNED_FORBIDDEN_KEYS",
    "validate_transition_concern_evidence",
)
