"""Link-owned Gate public fact surface.

GateFact records sufficiency against public facts at Link stages. It does not
choose Movement, destination, route, rollback, retry, hold, or next target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


GATE_STAGE_LITERALS: tuple[str, ...] = ("transfer", "carry", "movement")
GATE_SUFFICIENCY_LITERALS: tuple[str, ...] = (
    "sufficient",
    "insufficient",
    "missing_required_facts",
)
DECLARED_GATE_REFS: tuple[str, ...] = (
    "link-gate:default-transition",
    "link-gate:strict",
    "link-gate:human",
    "link-gate:coo",
)
HUMAN_DISPOSITION_GATE_REFS: frozenset[str] = frozenset(
    {DECLARED_GATE_REFS[2], DECLARED_GATE_REFS[3]}
)
AUTO_ADOPT_GATE_REFS: frozenset[str] = frozenset({DECLARED_GATE_REFS[0]})
HUMAN_GATE_REF: str = DECLARED_GATE_REFS[2]
COO_GATE_REF: str = DECLARED_GATE_REFS[3]

_GATE_REQUIRED_RETURN_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("link-gate:default-transition", ("observed_evidence", "not_proven")),
    ("link-gate:strict", ("blocked_or_missing_evidence", "remaining_delta", "proof_limits")),
)
_GATE_REQUIRED_RETURN_FIELD_MAP = dict(_GATE_REQUIRED_RETURN_FIELDS)


@dataclass(frozen=True)
class GateFact:
    """Public Link sufficiency fact for one Gate check stage."""

    stage: str
    sufficiency: str
    checked_public_fact: str = ""
    required_public_facts: tuple[str, ...] = ()
    missing_required_facts: tuple[str, ...] = ()
    reason: str = ""
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stage",
            _literal("stage", self.stage, GATE_STAGE_LITERALS),
        )
        object.__setattr__(
            self,
            "sufficiency",
            _literal("sufficiency", self.sufficiency, GATE_SUFFICIENCY_LITERALS),
        )
        object.__setattr__(
            self,
            "checked_public_fact",
            _optional_text("checked_public_fact", self.checked_public_fact),
        )
        object.__setattr__(
            self,
            "required_public_facts",
            _text_tuple("required_public_facts", self.required_public_facts),
        )
        object.__setattr__(
            self,
            "missing_required_facts",
            _text_tuple("missing_required_facts", self.missing_required_facts),
        )
        object.__setattr__(self, "reason", _optional_text("reason", self.reason))
        object.__setattr__(
            self,
            "evidence_reference",
            _optional_text_or_none("evidence_reference", self.evidence_reference),
        )


def make_gate_fact(
    stage: str,
    sufficiency: str,
    *,
    checked_public_fact: str = "",
    required_public_facts: Iterable[str] | str | None = (),
    missing_required_facts: Iterable[str] | str | None = (),
    reason: str = "",
    evidence_reference: str | None = None,
) -> GateFact:
    """Build a Link Gate sufficiency fact without Movement authority."""

    return GateFact(
        stage=stage,
        sufficiency=sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=_text_tuple(
            "required_public_facts",
            required_public_facts,
        ),
        missing_required_facts=_text_tuple(
            "missing_required_facts",
            missing_required_facts,
        ),
        reason=reason,
        evidence_reference=evidence_reference,
    )


def gate_required_return_fields(
    gate_refs: Iterable[str],
    base_required_fields: Iterable[str] = (),
) -> tuple[str, ...]:
    """Required Agent return fields implied by declared gate refs.

    base_required_fields (the Brick required_return_shape fields, ζ1) come
    first; each declared gate ref appends its gate-meaning fields in the fixed
    order below. Order preserved, duplicates removed. This is the gate->
    required-fields mapping owned by Link.
    """
    fields = list(base_required_fields)
    refs = tuple(gate_refs)
    for ref, extra in _GATE_REQUIRED_RETURN_FIELDS:
        if ref in refs:
            fields.extend(extra)
    return tuple(dict.fromkeys(fields))


def gate_ref_required_return_fields(
    gate_ref: str,
    base_required_fields: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return the Agent-return fields required by one declared Link gate.

    In an ordered gate sequence, default-transition checks the Brick-declared
    return shape plus its honest-report fields. Later gates check only their own
    incremental evidence channels, so strict evidence can fail after
    default-transition has passed.
    """

    ref = _literal("gate_ref", gate_ref, DECLARED_GATE_REFS)
    base = _text_tuple("base_required_fields", base_required_fields)
    extra = _GATE_REQUIRED_RETURN_FIELD_MAP.get(ref, ())
    if ref == "link-gate:default-transition":
        return tuple(dict.fromkeys((*base, *extra)))
    return tuple(dict.fromkeys(extra))


def evaluate_declared_gate_ref(
    *,
    gate_ref: str,
    base_required_return_fields: Iterable[str] = (),
    missing_return_fields: Iterable[str] = (),
    human_review_present: bool = False,
    override_present: bool = False,
    checked_public_fact: str = "",
    evidence_reference: str | None = None,
) -> GateFact:
    """Evaluate one declared Link gate into one GateFact.

    This is fact-only sufficiency. It does not choose Movement, target, route,
    hold state, success, or quality.
    """

    ref = _literal("gate_ref", gate_ref, DECLARED_GATE_REFS)
    required_return_fields = gate_ref_required_return_fields(
        ref,
        base_required_return_fields,
    )
    missing_return_field_set = set(
        _text_tuple("missing_return_fields", missing_return_fields)
    )
    required_public_facts: list[str] = []
    missing: list[str] = []
    if required_return_fields:
        required_public_facts.extend(
            (
                "BrickComparisonFact.required_return_shape_evidence",
                "BrickComparisonFact.comparison_evidence",
            )
        )
    for field_name in required_return_fields:
        public_fact = (
            "BrickComparisonFact.comparison_evidence.returned_field."
            f"{field_name}"
        )
        required_public_facts.append(public_fact)
        if field_name in missing_return_field_set:
            missing.append(public_fact)
    if ref == "link-gate:human":
        required_public_facts.append("Link.route_decision_basis.human_review_refs")
        if not human_review_present:
            missing.append("Link.route_decision_basis.human_review_refs")
    if ref == "link-gate:coo":
        required_public_facts.append("Link.route_decision_basis.override_refs")
        if not override_present:
            missing.append("Link.route_decision_basis.override_refs")

    sufficiency = "missing_required_facts" if missing else "sufficient"
    return make_gate_fact(
        "movement",
        sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=tuple(dict.fromkeys(required_public_facts)),
        missing_required_facts=tuple(dict.fromkeys(missing)),
        reason=(
            f"declared Link gate evaluation for {ref}; sufficiency fact only"
        ),
        evidence_reference=evidence_reference,
    )


def evaluate_declared_gate_refs(
    *,
    gate_refs: Iterable[str],
    base_required_return_fields: Iterable[str] = (),
    missing_return_fields: Iterable[str] = (),
    human_review_present: bool = False,
    override_present: bool = False,
    checked_public_fact: str = "",
    evidence_reference: str | None = None,
) -> tuple[tuple[str, GateFact], ...]:
    """Evaluate declared gates in caller-declared order."""

    refs = _text_tuple("gate_refs", gate_refs)
    return tuple(
        (
            ref,
            evaluate_declared_gate_ref(
                gate_ref=ref,
                base_required_return_fields=base_required_return_fields,
                missing_return_fields=missing_return_fields,
                human_review_present=human_review_present,
                override_present=override_present,
                checked_public_fact=checked_public_fact,
                evidence_reference=evidence_reference,
            ),
        )
        for ref in refs
    )


def derive_movement_gate_fact_from_gate_results(
    gate_results: Iterable[tuple[str, GateFact]],
    *,
    checked_public_fact: str = "",
    evidence_reference: str | None = None,
) -> GateFact | None:
    """Derive the combined movement GateFact from per-gate GateFacts."""

    results = tuple(gate_results)
    if not results:
        return None
    required: list[str] = []
    missing: list[str] = []
    gate_refs: list[str] = []
    for gate_ref, gate_fact in results:
        gate_refs.append(_literal("gate_ref", gate_ref, DECLARED_GATE_REFS))
        required.extend(gate_fact.required_public_facts)
        missing.extend(gate_fact.missing_required_facts)
    sufficiency = "missing_required_facts" if missing else "sufficient"
    return make_gate_fact(
        "movement",
        sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=tuple(dict.fromkeys(required)),
        missing_required_facts=tuple(dict.fromkeys(missing)),
        reason=(
            "combined movement gate derived from ordered per-gate GateFact "
            "results: "
            + ", ".join(gate_refs)
        ),
        evidence_reference=evidence_reference,
    )


def evaluate_declared_movement_gate(
    *,
    gate_refs: Iterable[str],
    required_return_fields: Iterable[str],
    missing_return_fields: Iterable[str],
    observed_match_kind: str,
    human_review_present: bool,
    override_present: bool,
    base_required_return_fields: Iterable[str] | None = None,
    checked_public_fact: str = "",
    evidence_reference: str | None = None,
) -> "GateFact | None":
    """Link-owned movement-gate sufficiency rule over Brick comparison facts.

    The combined GateFact is derived from ordered per-gate GateFacts. The
    ``observed_match_kind`` parameter is retained for API compatibility; per-gate
    sufficiency is driven by missing public facts for that gate.
    """
    refs = tuple(gate_refs)
    if not refs:
        return None
    base = (
        required_return_fields
        if base_required_return_fields is None
        else base_required_return_fields
    )
    per_gate = evaluate_declared_gate_refs(
        gate_refs=refs,
        base_required_return_fields=base,
        missing_return_fields=missing_return_fields,
        human_review_present=human_review_present,
        override_present=override_present,
        checked_public_fact=checked_public_fact,
        evidence_reference=evidence_reference,
    )
    return derive_movement_gate_fact_from_gate_results(
        per_gate,
        checked_public_fact=checked_public_fact,
        evidence_reference=evidence_reference,
    )


def make_transfer_gate_fact(
    sufficiency: str,
    *,
    checked_public_fact: str = "",
    required_public_facts: Iterable[str] | str | None = (),
    missing_required_facts: Iterable[str] | str | None = (),
    reason: str = "",
    evidence_reference: str | None = None,
) -> GateFact:
    """Build a transfer-stage GateFact."""

    return make_gate_fact(
        "transfer",
        sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=required_public_facts,
        missing_required_facts=missing_required_facts,
        reason=reason,
        evidence_reference=evidence_reference,
    )


def make_carry_gate_fact(
    sufficiency: str,
    *,
    checked_public_fact: str = "",
    required_public_facts: Iterable[str] | str | None = (),
    missing_required_facts: Iterable[str] | str | None = (),
    reason: str = "",
    evidence_reference: str | None = None,
) -> GateFact:
    """Build a carry-stage GateFact."""

    return make_gate_fact(
        "carry",
        sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=required_public_facts,
        missing_required_facts=missing_required_facts,
        reason=reason,
        evidence_reference=evidence_reference,
    )


def make_movement_gate_fact(
    sufficiency: str,
    *,
    checked_public_fact: str = "",
    required_public_facts: Iterable[str] | str | None = (),
    missing_required_facts: Iterable[str] | str | None = (),
    reason: str = "",
    evidence_reference: str | None = None,
) -> GateFact:
    """Build a movement-stage GateFact."""

    return make_gate_fact(
        "movement",
        sufficiency,
        checked_public_fact=checked_public_fact,
        required_public_facts=required_public_facts,
        missing_required_facts=missing_required_facts,
        reason=reason,
        evidence_reference=evidence_reference,
    )


def _literal(field_name: str, value: str, admitted: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    cleaned = value.strip()
    if cleaned not in admitted:
        raise ValueError(f"{field_name} must be one of the admitted literals")
    return cleaned


def _optional_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    return value.strip()


def _optional_text_or_none(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _optional_text(field_name, value)


def _text_tuple(
    field_name: str,
    values: Iterable[str] | str | None,
) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)

    facts: list[str] = []
    for index, value in enumerate(values):
        cleaned = _optional_text(f"{field_name}[{index}]", value)
        if not cleaned:
            raise ValueError(f"{field_name}[{index}] must not be blank")
        facts.append(cleaned)
    return tuple(facts)


__all__ = [
    "GATE_STAGE_LITERALS",
    "GATE_SUFFICIENCY_LITERALS",
    "DECLARED_GATE_REFS",
    "HUMAN_DISPOSITION_GATE_REFS",
    "AUTO_ADOPT_GATE_REFS",
    "HUMAN_GATE_REF",
    "COO_GATE_REF",
    "GateFact",
    "make_gate_fact",
    "gate_required_return_fields",
    "gate_ref_required_return_fields",
    "evaluate_declared_gate_ref",
    "evaluate_declared_gate_refs",
    "derive_movement_gate_fact_from_gate_results",
    "evaluate_declared_movement_gate",
    "make_transfer_gate_fact",
    "make_carry_gate_fact",
    "make_movement_gate_fact",
]
