"""Link-owned carry public fact surface.

CarryFact preserves public fact references across boundaries without rewriting
their Brick / Agent / Link owner axis or proof limit. It does not execute,
persist, classify, judge, or choose Movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


SOURCE_OWNER_AXIS_LITERALS: tuple[str, ...] = ("Brick", "Agent", "Link")


@dataclass(frozen=True)
class CarryFact:
    """Public Link fact for carrying references without owner-axis rewrite."""

    carried_fact_refs: tuple[str, ...] = field(default_factory=tuple)
    source_owner_axis: str = ""
    target_boundary_ref: str = ""
    carry_gate_reference: str | None = None
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)
    evidence_reference: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "carried_fact_refs",
            _text_tuple("carried_fact_refs", self.carried_fact_refs, require_any=True),
        )
        object.__setattr__(
            self,
            "source_owner_axis",
            _owner_axis(self.source_owner_axis),
        )
        object.__setattr__(
            self,
            "target_boundary_ref",
            _brick_boundary_ref("target_boundary_ref", self.target_boundary_ref),
        )
        object.__setattr__(
            self,
            "carry_gate_reference",
            _optional_text_or_none("carry_gate_reference", self.carry_gate_reference),
        )
        object.__setattr__(
            self,
            "proof_limits",
            _text_tuple("proof_limits", self.proof_limits, require_any=True),
        )
        object.__setattr__(
            self,
            "not_proven",
            _text_tuple("not_proven", self.not_proven),
        )
        object.__setattr__(
            self,
            "evidence_reference",
            _required_text("evidence_reference", self.evidence_reference),
        )


def make_carry_fact(
    *,
    carried_fact_refs: Iterable[str] | str,
    source_owner_axis: str,
    target_boundary_ref: str,
    carry_gate_reference: str | None = None,
    proof_limits: Iterable[str] | str,
    not_proven: Iterable[str] | str | None = (),
    evidence_reference: str,
) -> CarryFact:
    """Build a Link CarryFact without changing ownership or proof limits."""

    return CarryFact(
        carried_fact_refs=_text_tuple(
            "carried_fact_refs",
            carried_fact_refs,
            require_any=True,
        ),
        source_owner_axis=source_owner_axis,
        target_boundary_ref=target_boundary_ref,
        carry_gate_reference=carry_gate_reference,
        proof_limits=_text_tuple("proof_limits", proof_limits, require_any=True),
        not_proven=_text_tuple("not_proven", not_proven),
        evidence_reference=evidence_reference,
    )


def _owner_axis(value: str) -> str:
    cleaned = _required_text("source_owner_axis", value)
    if cleaned not in SOURCE_OWNER_AXIS_LITERALS:
        allowed = ", ".join(SOURCE_OWNER_AXIS_LITERALS)
        raise ValueError(f"source_owner_axis must be one of: {allowed}")
    return cleaned


def _required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _brick_boundary_ref(field_name: str, value: str) -> str:
    cleaned = _required_text(field_name, value)
    if cleaned.startswith(("brick:", "brick-", "building-boundary:")):
        return cleaned
    raise ValueError(f"{field_name} must reference a Brick boundary")


def _optional_text_or_none(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(field_name, value)


def _text_tuple(
    field_name: str,
    values: Iterable[str] | str | None,
    *,
    require_any: bool = False,
) -> tuple[str, ...]:
    if values is None:
        values = ()
    if isinstance(values, str):
        values = (values,)

    facts: list[str] = []
    for index, value in enumerate(values):
        facts.append(_required_text(f"{field_name}[{index}]", value))
    if require_any and not facts:
        raise ValueError(f"{field_name} must contain at least one text ref")
    return tuple(facts)


__all__ = [
    "SOURCE_OWNER_AXIS_LITERALS",
    "CarryFact",
    "make_carry_fact",
]
