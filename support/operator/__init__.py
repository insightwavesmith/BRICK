"""Support-only operator helper surface for Building operation mechanics."""

from typing import Any


def build(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from brick_protocol.support.operator.onboard import build as _build

    return _build(*args, **kwargs)


__all__ = ["build"]
