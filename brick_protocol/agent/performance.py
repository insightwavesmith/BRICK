"""Public performer surface for Agent.performance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# The native-dispatch performance mode is an Agent-axis vocabulary word: it
# names the performer lane in which the MAIN AGENT dispatches a subagent
# natively (engine is the ABSENCE of a Movement label). Support imports this
# word; it does not own it.
NATIVE_DISPATCH_PERFORMANCE_MODE = "native-dispatch"


@dataclass(frozen=True)
class AgentPerformerFact:
    """Agent records an admitted performer lane and callable references."""

    name: str
    lane: str
    callable_performers: tuple[str, ...] = ()


def make_agent_performer_fact(
    *,
    name: str,
    lane: str,
    callable_performers: Iterable[str] | None = None,
) -> AgentPerformerFact:
    """Create an Agent performer fact from public Agent values."""

    return AgentPerformerFact(
        name=name,
        lane=lane,
        callable_performers=tuple(callable_performers or ()),
    )


__all__ = (
    "NATIVE_DISPATCH_PERFORMANCE_MODE",
    "AgentPerformerFact",
    "make_agent_performer_fact",
)
