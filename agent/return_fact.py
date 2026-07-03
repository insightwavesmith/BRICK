"""Public AgentFact surface for Agent.return_fact."""

from __future__ import annotations

import re
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
NON_REROUTE_CONCERN_KINDS: frozenset[str] = frozenset({"verification_gap"})
REROUTE_ELIGIBLE_CONCERN_KINDS: frozenset[str] = (
    TRANSITION_CONCERN_KINDS - NON_REROUTE_CONCERN_KINDS
)
TRANSITION_CONCERN_REROUTE_REF_PREFIXES: tuple[str, ...] = (
    "brick:",
    "brick-",
    "brick-boundary:",
    "brick-instance:",
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
TRANSITION_CONCERN_REASON_REF_ADDRESS_RULE = (
    "transition_concern_evidence.reason_refs with '/' must be work/step-outputs/... "
    "ledger addresses with no #fragment; bare file:line citations are not admitted"
)
TOP_LEVEL_VERDICT_KEYS: frozenset[str] = frozenset(
    {
        "approved",
        "complete",
        "completed",
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
        "result",
        "route_target",
        "score",
        "status",
        "success",
        "success_judgment",
        "target",
        "target_ref",
        "verdict",
    }
)
ALWAYS_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "auth",
        "auth_value",
        "credential",
        "credential_body",
        "credential_value",
        "raw_secret",
        "secret",
        "session",
        "session_id",
        "setup_token",
        "setup_token_value",
    }
)
# Compatibility surface for older recursive support payload guards. Verdict and
# Movement words are top-level-only; recursive users should receive only the
# credential/session key family.
RETURNED_FORBIDDEN_KEYS: frozenset[str] = ALWAYS_SECRET_KEYS


def is_non_reroute_transition_concern_kind(concern_kind: Any) -> bool:
    """Return whether an admitted transition concern kind proposes no reroute."""

    return isinstance(concern_kind, str) and concern_kind in NON_REROUTE_CONCERN_KINDS


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


def _normalize_return_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _validate_returned_top_level_keys(returned: Any) -> None:
    if not isinstance(returned, Mapping):
        return
    for raw_key in returned:
        key = _normalize_return_key(raw_key)
        if key in ALWAYS_SECRET_KEYS or key in TOP_LEVEL_VERDICT_KEYS:
            raise ValueError(f"AgentFact returned contains forbidden key {raw_key!r}")


def _is_step_outputs_address_form(ref: str) -> bool:
    parts = [
        part.casefold()
        for part in ref.replace("\\", "/").split("/")
        if part and part != "."
    ]
    return len(parts) >= 3 and parts[:2] == ["work", "step-outputs"]


def _validate_transition_concern_reason_ref(ref: str) -> None:
    if "#" in ref:
        raise ValueError(
            f"{TRANSITION_CONCERN_REASON_REF_ADDRESS_RULE}; invalid ref {ref!r}"
        )
    if re.search(r"(?:/|\\|^[^:]+\.[A-Za-z0-9]+):[0-9]+$", ref):
        raise ValueError(
            f"{TRANSITION_CONCERN_REASON_REF_ADDRESS_RULE}; invalid ref {ref!r}"
        )
    if "/" in ref.replace("\\", "/") and not _is_step_outputs_address_form(ref):
        raise ValueError(
            f"{TRANSITION_CONCERN_REASON_REF_ADDRESS_RULE}; invalid ref {ref!r}"
        )


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
    for ref in reason_refs:
        _validate_transition_concern_reason_ref(ref)
    related_refs = _text_tuple(
        "transition_concern_evidence.related_boundary_refs",
        concern.get("related_boundary_refs", ()),
    )
    for ref in related_refs:
        if not ref.startswith((*TRANSITION_CONCERN_REROUTE_REF_PREFIXES, "building-boundary:")):
            raise ValueError("transition_concern_evidence.related_boundary_refs must name Brick boundaries")
        if concern_kind in NON_REROUTE_CONCERN_KINDS and ref.startswith(
            TRANSITION_CONCERN_REROUTE_REF_PREFIXES
        ):
            raise ValueError(
                "transition_concern_evidence.verification_gap must not name a reroute-capable Brick boundary"
            )
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
    _validate_returned_top_level_keys(returned)
    return AgentFact(received_work=received_work, returned=returned)


AGENT_FACT_FIELDS: tuple[str, ...] = tuple(_f.name for _f in fields(AgentFact))


__all__ = (
    "AgentFact",
    "AGENT_FACT_FIELDS",
    "make_agent_fact",
    "TRANSITION_CONCERN_KINDS",
    "NON_REROUTE_CONCERN_KINDS",
    "REROUTE_ELIGIBLE_CONCERN_KINDS",
    "TRANSITION_CONCERN_REROUTE_REF_PREFIXES",
    "TRANSITION_CONCERN_ALLOWED_KEYS",
    "TOP_LEVEL_VERDICT_KEYS",
    "ALWAYS_SECRET_KEYS",
    "RETURNED_FORBIDDEN_KEYS",
    "is_non_reroute_transition_concern_kind",
    "validate_transition_concern_evidence",
)
