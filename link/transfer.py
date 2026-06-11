"""Link-owned transfer public fact surface.

TransferFact records caller-supplied public facts moving between boundaries.
It does not execute an Agent, call providers/tools, persist storage/wiki data,
judge success or quality, or choose Movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class TransferFact:
    """Public Link fact for transfer between Building boundaries."""

    source_boundary_ref: str
    target_boundary_ref: str
    public_fact_refs: tuple[str, ...] = field(default_factory=tuple)
    work_context_ref: str = ""
    required_public_facts: tuple[str, ...] = field(default_factory=tuple)
    transfer_gate_reference: str | None = None
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)
    evidence_reference: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_boundary_ref",
            _brick_boundary_ref("source_boundary_ref", self.source_boundary_ref),
        )
        object.__setattr__(
            self,
            "target_boundary_ref",
            _brick_boundary_ref("target_boundary_ref", self.target_boundary_ref),
        )
        object.__setattr__(
            self,
            "public_fact_refs",
            _text_tuple("public_fact_refs", self.public_fact_refs, require_any=True),
        )
        object.__setattr__(
            self,
            "work_context_ref",
            _required_text("work_context_ref", self.work_context_ref),
        )
        object.__setattr__(
            self,
            "required_public_facts",
            _text_tuple(
                "required_public_facts",
                self.required_public_facts,
                require_any=True,
            ),
        )
        object.__setattr__(
            self,
            "transfer_gate_reference",
            _optional_text_or_none(
                "transfer_gate_reference",
                self.transfer_gate_reference,
            ),
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


def make_transfer_fact(
    *,
    source_boundary_ref: str,
    target_boundary_ref: str,
    public_fact_refs: Iterable[str] | str,
    work_context_ref: str,
    required_public_facts: Iterable[str] | str,
    transfer_gate_reference: str | None = None,
    proof_limits: Iterable[str] | str,
    not_proven: Iterable[str] | str | None = (),
    evidence_reference: str,
) -> TransferFact:
    """Build a Link TransferFact without executing or judging the transfer."""

    return TransferFact(
        source_boundary_ref=source_boundary_ref,
        target_boundary_ref=target_boundary_ref,
        public_fact_refs=_text_tuple(
            "public_fact_refs",
            public_fact_refs,
            require_any=True,
        ),
        work_context_ref=work_context_ref,
        required_public_facts=_text_tuple(
            "required_public_facts",
            required_public_facts,
            require_any=True,
        ),
        transfer_gate_reference=transfer_gate_reference,
        proof_limits=_text_tuple("proof_limits", proof_limits, require_any=True),
        not_proven=_text_tuple("not_proven", not_proven),
        evidence_reference=evidence_reference,
    )


def _required_text(field_name: str, value: str) -> str:
    cleaned = _optional_text(field_name, value)
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _brick_boundary_ref(field_name: str, value: str) -> str:
    cleaned = _required_text(field_name, value)
    if cleaned.startswith(("brick:", "brick-", "building-boundary:")):
        return cleaned
    raise ValueError(f"{field_name} must reference a Brick boundary")


def _optional_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    return value.strip()


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
        cleaned = _required_text(f"{field_name}[{index}]", value)
        facts.append(cleaned)
    if require_any and not facts:
        raise ValueError(f"{field_name} must contain at least one text ref")
    return tuple(facts)


__all__ = [
    "TransferFact",
    "make_transfer_fact",
]
