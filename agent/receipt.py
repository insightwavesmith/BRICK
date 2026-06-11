"""Public receipt surface for Agent.receipt."""

from __future__ import annotations

from dataclasses import MISSING, dataclass
from typing import Any


@dataclass(frozen=True)
class ReceiptFact:
    """Agent records the work it received without redefining AgentFact."""

    received_work: Any
    received_at_reference: str | None = None
    evidence_reference: str | None = None


def make_receipt_fact(
    *,
    received_work: Any = MISSING,
    received_at_reference: str | None = None,
    evidence_reference: str | None = None,
) -> ReceiptFact:
    """Create a receipt fact when the received work value is supplied."""

    if received_work is MISSING:
        raise ValueError("ReceiptFact requires public fact value: received_work")
    return ReceiptFact(
        received_work=received_work,
        received_at_reference=received_at_reference,
        evidence_reference=evidence_reference,
    )


__all__ = ("ReceiptFact", "make_receipt_fact")
