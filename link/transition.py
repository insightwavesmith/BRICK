"""Link-owned Transition public fact surface."""

from __future__ import annotations

from dataclasses import dataclass

from .movement import MOVEMENT_LITERALS

BUILDING_LIFECYCLE_STATES: frozenset[str] = frozenset({"waiting", "closed"})
DISPOSITION_ACTIONS: tuple[str, ...] = ("raise", "forward", "stop")
TRANSITION_LIFECYCLE_STATES: frozenset[str] = frozenset({"paused", "resumed"})
TRANSITION_LIFECYCLE_PROGRESS_STATES: frozenset[str] = frozenset({"in_progress"})
TRANSITION_LIFECYCLE_DISPOSITION_OWNERS: frozenset[str] = frozenset(
    {"caller", "coo", "caller-or-coo"}
)
TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES: tuple[str, ...] = (
    "human:",
    "coo:",
)
TRANSITION_LIFECYCLE_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "state",
        "progress_state",
        "paused_at_ref",
        "resumed_from_ref",
        "from_brick_ref",
        "pending_target_ref",
        "reason_refs",
        "required_disposition_owner",
        "disposition_action",
        "budget_increment",
        "proof_limits",
        "not_proven",
    }
)


@dataclass(frozen=True)
class TransitionFact:
    """Public Link fact carrying movement and handoff facts."""

    movement: str
    target_fact: str | None = None
    topology_fact: str | None = None
    merge_rule_fact: str | None = None
    handoff_reference: str | None = None
    not_proven: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.movement not in MOVEMENT_LITERALS:
            raise ValueError("movement must be one of the admitted English literals")


def make_transition_fact(
    movement: str,
    *,
    target_fact: str | None = None,
    topology_fact: str | None = None,
    merge_rule_fact: str | None = None,
    handoff_reference: str | None = None,
    not_proven: tuple[str, ...] = (),
) -> TransitionFact:
    """Build a Link Transition fact without executing the handoff."""

    return TransitionFact(
        movement=movement,
        target_fact=target_fact,
        topology_fact=topology_fact,
        merge_rule_fact=merge_rule_fact,
        handoff_reference=handoff_reference,
        not_proven=not_proven,
    )


__all__ = [
    "BUILDING_LIFECYCLE_STATES",
    "DISPOSITION_ACTIONS",
    "MOVEMENT_LITERALS",
    "TRANSITION_LIFECYCLE_ALLOWED_KEYS",
    "TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES",
    "TRANSITION_LIFECYCLE_DISPOSITION_OWNERS",
    "TRANSITION_LIFECYCLE_PROGRESS_STATES",
    "TRANSITION_LIFECYCLE_STATES",
    "TransitionFact",
    "make_transition_fact",
]
