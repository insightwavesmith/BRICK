"""Link-owned Movement public fact surface.

This module keeps Movement under Link. GateFact evidence may be referenced as
sufficiency evidence, but Gate does not choose Movement.
"""

from __future__ import annotations

from dataclasses import dataclass


ADMITTED_MOVEMENT_FORWARD = {"movement": "forward"}
ADMITTED_MOVEMENT_REROUTE = {"movement": "reroute"}

MOVEMENT_LITERALS: tuple[str, ...] = (
    ADMITTED_MOVEMENT_FORWARD["movement"],
    ADMITTED_MOVEMENT_REROUTE["movement"],
)

GATEFACT_SUFFICIENCY_CRITERIA: tuple[str, ...] = (
    "sufficient",
    "insufficient",
    "missing_required_facts",
)


@dataclass(frozen=True)
class MovementFact:
    """Public Link fact carrying one admitted Movement literal."""

    movement: str
    reason: str = ""
    handoff_target_fact: str | None = None
    gatefact_reference: str | None = None
    transition_history_reference: str | None = None

    def __post_init__(self) -> None:
        if self.movement not in MOVEMENT_LITERALS:
            raise ValueError("movement must be one of the admitted English literals")


def make_movement_fact(
    movement: str,
    *,
    reason: str = "",
    handoff_target_fact: str | None = None,
    gatefact_reference: str | None = None,
    transition_history_reference: str | None = None,
) -> MovementFact:
    """Build a Link Movement fact without creating Gate or runtime authority."""

    return MovementFact(
        movement=movement,
        reason=reason,
        handoff_target_fact=handoff_target_fact,
        gatefact_reference=gatefact_reference,
        transition_history_reference=transition_history_reference,
    )


__all__ = [
    "GATEFACT_SUFFICIENCY_CRITERIA",
    "MOVEMENT_LITERALS",
    "MovementFact",
    "make_movement_fact",
]
