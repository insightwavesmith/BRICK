"""Support-only operator helper surface for Building operation mechanics."""

from typing import Any


def build(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from brick_protocol.support.operator.onboard import build as _build

    return _build(*args, **kwargs)


def launch_assembled_building(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Launch an ``assemble()``-d ComposedGraph with no forced human gate.

    Thin re-export of ``onboard.launch_assembled_building`` (the assemble-path
    twin of the goal-path ``build``): it persists the composed plan, derives the
    durable root from a vessel ``project_ref`` through ``buildings_root_for``, and
    runs inside the worktree sandbox — so the operator only declares graph shape.
    """

    from brick_protocol.support.operator.onboard import (
        launch_assembled_building as _launch,
    )

    return _launch(*args, **kwargs)


__all__ = ["build", "launch_assembled_building"]
