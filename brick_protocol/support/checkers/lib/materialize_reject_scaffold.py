"""Materialize-building reject probe scaffolding.

Support checker helpers only. These wrappers mutate in-memory registry copies
for negative probes and restore the materializer globals after each case.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping, Sequence
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string_list,
)


def _materialize_reject_strip_preset_keys(mapping: Mapping[str, Any]) -> tuple[str, ...]:
    raw = mapping.get("strip_preset_keys")
    if raw is None:
        return ()
    return tuple(
        require_string_list(raw, "materialize_building_intent_rejects.strip_preset_keys")
    )


def _materialize_reject_patch_preset_steps(mapping: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = mapping.get("patch_chain_preset_steps")
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ProfileError(
            "materialize_building_intent_rejects.patch_chain_preset_steps must be a list"
        )
    steps: list[Mapping[str, Any]] = []
    for index, raw_step in enumerate(raw):
        steps.append(
            require_mapping(
                raw_step,
                f"materialize_building_intent_rejects.patch_chain_preset_steps[{index}]",
            )
        )
    if not steps:
        raise ProfileError(
            "materialize_building_intent_rejects.patch_chain_preset_steps must not be empty"
        )
    return tuple(steps)


@contextlib.contextmanager
def _stripped_chain_preset_keys(materialize_fn, preset_ref: str, keys):
    """Temporarily wrap the materializer's registry loader to drop preset keys.

    Patches ``_load_shape_registry`` in the GLOBALS of the actual
    ``materialize_building_intent`` function (so it works regardless of which
    package alias resolved the function) to return a registry where the named
    preset has the given keys removed. A COPY is stored; the on-disk catalog file
    is never mutated. Yields a probe truthy iff the preset_ref was found and
    stripped. The original loader symbol is always restored on exit. This is
    read-only checker scaffolding that exercises the materializer's fail-closed
    path; it authors nothing.
    """
    globals_ns = materialize_fn.__globals__
    if "_load_shape_registry" not in globals_ns:
        raise ProfileError(
            "materialize_building_intent_rejects strip scaffold cannot find "
            "_load_shape_registry in the materializer's module globals"
        )
    original_loader = globals_ns["_load_shape_registry"]
    found = False

    def _wrapped(repo_root):
        nonlocal found
        registry = dict(original_loader(repo_root))
        chain_presets = registry.get("chain_presets")
        if isinstance(chain_presets, Mapping) and preset_ref in chain_presets:
            preset = dict(chain_presets[preset_ref])
            for key in keys:
                preset.pop(key, None)
            patched = dict(chain_presets)
            patched[preset_ref] = preset
            registry["chain_presets"] = patched
            found = True
        return registry

    globals_ns["_load_shape_registry"] = _wrapped
    try:
        yield _StripProbe(lambda: found)
    finally:
        globals_ns["_load_shape_registry"] = original_loader


@contextlib.contextmanager
def _patched_chain_preset_steps(materialize_fn, preset_ref: str, steps: Sequence[Mapping[str, Any]]):
    """Temporarily replace one resolved chain preset's steps for a RED probe."""

    globals_ns = materialize_fn.__globals__
    if "_load_shape_registry" not in globals_ns:
        raise ProfileError(
            "materialize_building_intent_rejects patch scaffold cannot find "
            "_load_shape_registry in the materializer's module globals"
        )
    original_loader = globals_ns["_load_shape_registry"]
    found = False

    def _wrapped(repo_root):
        nonlocal found
        registry = dict(original_loader(repo_root))
        chain_presets = registry.get("chain_presets")
        if isinstance(chain_presets, Mapping) and preset_ref in chain_presets:
            preset = dict(chain_presets[preset_ref])
            preset["steps"] = [dict(step) for step in steps]
            patched = dict(chain_presets)
            patched[preset_ref] = preset
            registry["chain_presets"] = patched
            found = True
        return registry

    globals_ns["_load_shape_registry"] = _wrapped
    try:
        yield _StripProbe(lambda: found)
    finally:
        globals_ns["_load_shape_registry"] = original_loader


class _StripProbe:
    """Truthy iff the strip target preset_ref was found (evaluated lazily)."""

    def __init__(self, resolver) -> None:
        self._resolver = resolver

    def __bool__(self) -> bool:
        return bool(self._resolver())
