"""Composition problem records (leaf module).

The two support-composition problem-record classes, extracted from
the pre-split composition module to break the compose<->validate cycle. Stdlib only; this module
imports no siblings so it can be imported first.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CompositionProblem:
    """One support composition problem attributed to a declared node."""

    code: str
    node_id: str
    detail: str


class CompositionError(ValueError):
    """Raised when compose_building collects one or more problems."""

    def __init__(self, problems: Sequence[CompositionProblem]) -> None:
        self.problems = tuple(problems)
        detail = "; ".join(
            f"{problem.code}@{problem.node_id}: {problem.detail}"
            for problem in self.problems
        )
        super().__init__(detail or "composition failed")
