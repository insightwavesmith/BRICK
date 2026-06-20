"""Agent-owned casting single-source API (axis single-source API, E2/§2 AXIS B).

This is the Agent single-source API for the CASTING field-set — the WHO-dials a
plan declares for each step: which performer (``preferred_adapter_ref``) and
which brain (``preferred_model_ref``). It owns:

  * ``CASTING_FIELDS`` (moved from ``support/operator/primitives.py`` at E2/S6),
    UPGRADED so each ``CastingField`` carries its resolution policy AS DATA —
    ``fail_closed`` (adapter is constitutionally explicit-or-fail; model is
    deferrable), ``default_ref`` (the deferrable sentinel/default), ``scope``
    (the admitted value-set the per-dial validator checks against),
    ``inherits_source_of`` (model couples to the resolved adapter SOURCE) and
    ``cli_emit`` (the per-dial spawn-time CLI projection). One generic resolver +
    one generic per-dial validator + one generic spawn projector now read this
    data, so the constitutional asymmetry between the two dials is DATA, not two
    hand-written code paths.
  * ``NODE_CASTING_FIELDS`` — the plan-layer ``selected_<rest>`` projection of
    the SAME field-set (the ``selected_*`` twin of the Agent-source
    ``preferred_*`` names), so a new casting field is added in ONE place.

It defines plan-level casting vocabulary; it authors no Movement, chooses no
route, and judges no success or quality.

BRAIN CATALOG RE-EXPORT (E2/§2 AXIS B). The adapter/model brain catalog
(``ALLOWED_ADAPTER_REFS``, ``MODEL_PROVIDER_BY_ADAPTER``, ``MODEL_REF_DEFAULT``,
the local-adapter ref constants, ``project_model_ref_to_cli_arg``) is Agent-axis
property whose DATA still physically lives in ``support/connection/agent_adapter``
for now (a later step may move the data). This module re-exports the public names
through the axis API so the casting descriptors — and the support consumers — read
the catalog through the Agent axis. The descriptor ``scope`` frozensets and
``cli_emit`` projectors are built here over those re-exported names, byte-identical
to the prior support-local definitions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

from brick_protocol.support.connection.agent_adapter import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ALLOWED_ADAPTER_REFS,
    MODEL_PROVIDER_BY_ADAPTER,
    MODEL_REF_DEFAULT,
    project_model_ref_to_cli_arg,
)


# ---------------------------------------------------------------------------
# CASTING DESCRIPTOR (E2/S6). Each CastingField carries its full resolution
# POLICY as DATA. The two dials differ ONLY in this data — never in a separate
# code path:
#   * ``fail_closed``        adapter=True  (explicit-or-fail; support never
#                            defaults it — the constitutional asymmetry),
#                            model=False   (deferrable sentinel/default).
#   * ``default_ref``        the deferrable default ref (model:default); None for
#                            the fail-closed adapter dial (no adapter default).
#   * ``scope``              the admitted value-set the per-dial validator checks
#                            a declared value against.
#   * ``inherits_source_of`` the field_name whose resolved SOURCE this dial
#                            couples to (model couples to the adapter source so
#                            the role's preferred_model_ref is honored only when
#                            the adapter itself came from the role lane); None for
#                            the adapter dial (it sources independently).
#   * ``cli_emit``           the spawn-time CLI projection (value, adapter_ref) ->
#                            the exact argv tuple this dial contributes.
# ---------------------------------------------------------------------------
class CastingField(NamedTuple):
    field_name: str
    fail_closed: bool
    default_ref: str | None
    scope: frozenset[str]
    inherits_source_of: str | None
    cli_emit: Callable[[str, str], tuple[str, ...]]


def _no_cli_emit(_value: str, _adapter_ref: str) -> tuple[str, ...]:
    """The adapter dial contributes no model-arg of its own (byte-identical to
    the prior ``_no_cli_emit``: the adapter selection is the executable/mode, not
    a model CLI flag)."""

    return ()


# Per-adapter model CLI flag. PLAIN literal data (no support coupling): codex
# uses ``-m``, claude/gemini-local use ``--model``. Byte-identical to the inline
# literals at agent_adapter._invoke_local_cli (codex `-m`, claude `--model`) and
# to the prior support-local ``_MODEL_CLI_FLAG_BY_ADAPTER`` map.
_MODEL_CLI_FLAG_BY_ADAPTER: Mapping[str, str] = {
    ADAPTER_CODEX_LOCAL: "-m",
    ADAPTER_CLAUDE_LOCAL: "--model",
    ADAPTER_GEMINI_LOCAL: "--model",
}


def _model_cli_emit(value: str, adapter_ref: str) -> tuple[str, ...]:
    """Project the model dial to its spawn argv contribution.

    Byte-identical to the prior support ``_model_cli_emit`` AND to the inline
    spawn literals it replaces: project the model ref to its CLI arg (raising on a
    provider mismatch exactly as the inline ``_model_cli_arg`` path did), and emit
    ``(flag, model_arg)`` only when the arg is non-empty and the adapter carries a
    known flag — otherwise no arg (the model defaulted)."""

    model_arg = project_model_ref_to_cli_arg(adapter_ref, value)
    if not model_arg:
        return ()
    flag = _MODEL_CLI_FLAG_BY_ADAPTER.get(adapter_ref)
    if flag is None:
        return ()
    return (flag, model_arg)


# ---------------------------------------------------------------------------
# EFFORT DIAL DEFINITION (E2/S6★ — first validation case). The effort dial is a
# THIRD casting field. Per Smith's constitutional ruling it is MODEL-LIKE, not
# adapter-like: DEFERRABLE (fail_closed=False), with a default sentinel support
# never hard-fails on. These few constants + the cli_emit helper ARE the dial
# definition — adding them alongside the ONE CASTING_FIELDS row is allowed in the
# single source (the whole point of S6★: a new dial is ~one edit, not a 15-file
# cascade). The dial is added in ONE place; contracts/adapter/run-ladder/
# plan_rendering/cli/guard/AGENTS.md all DERIVE.
# ---------------------------------------------------------------------------
EFFORT_REF_DEFAULT = "effort:default"  # deferrable sentinel; emits no CLI arg.

# The effort-capable adapters (codex + claude). Gemini-local carries no reasoning
# effort dial, so it is out of scope — a declared effort on it is out-of-scope.
EFFORT_SCOPE: frozenset[str] = frozenset({ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL})

# Per-adapter effort CLI projection. codex takes a config override
# ``-c model_reasoning_effort=<level>``; claude takes ``--effort <level>``. PLAIN
# literal data — the per-adapter argv shape each effort-capable adapter expects.
_EFFORT_CLI_EMIT_BY_ADAPTER: Mapping[str, Callable[[str], tuple[str, ...]]] = {
    ADAPTER_CODEX_LOCAL: lambda level: ("-c", "model_reasoning_effort=" + level),
    ADAPTER_CLAUDE_LOCAL: lambda level: ("--effort", level),
}


def _effort_cli_emit(value: str, adapter_ref: str) -> tuple[str, ...]:
    """Project the effort dial to its spawn argv contribution.

    Deferrable, like the model dial: emit nothing for the default sentinel (the
    effort defaulted — let the adapter pick its own), and nothing for an adapter
    with no effort dial (out of ``EFFORT_SCOPE``). Otherwise emit the adapter's
    effort flag/arg shape (codex ``-c model_reasoning_effort=<level>``, claude
    ``--effort <level>``)."""

    if not value or value == EFFORT_REF_DEFAULT:
        return ()
    emit = _EFFORT_CLI_EMIT_BY_ADAPTER.get(adapter_ref)
    if emit is None:
        return ()
    return emit(value)


# The casting field-set. Member ORDER is load-bearing: the adapter dial resolves
# FIRST so the model dial (inherits_source_of="preferred_adapter_ref") can couple
# to the adapter's resolved source. ``scope`` for the adapter dial is the full
# admitted adapter-ref set; for the model dial it is the adapters that carry a
# model provider — byte-identical to the prior support-local definitions.
CASTING_FIELDS: tuple[CastingField, ...] = (
    CastingField(
        field_name="preferred_adapter_ref",
        fail_closed=True,
        default_ref=None,
        scope=ALLOWED_ADAPTER_REFS,
        inherits_source_of=None,
        cli_emit=_no_cli_emit,
    ),
    CastingField(
        field_name="preferred_model_ref",
        fail_closed=False,
        default_ref=MODEL_REF_DEFAULT,
        scope=frozenset(MODEL_PROVIDER_BY_ADAPTER),
        inherits_source_of="preferred_adapter_ref",
        cli_emit=_model_cli_emit,
    ),
    # S6★ FIRST VALIDATION CASE — the effort dial as ONE row. MODEL-LIKE:
    # deferrable (fail_closed=False), default sentinel ``effort:default`` that
    # support never hard-fails on, scope = the effort-capable adapters, and it
    # couples to the resolved adapter source exactly like the model dial.
    CastingField(
        field_name="preferred_reasoning_effort_ref",
        fail_closed=False,
        default_ref=EFFORT_REF_DEFAULT,
        scope=EFFORT_SCOPE,
        inherits_source_of="preferred_adapter_ref",
        cli_emit=_effort_cli_emit,
    ),
)


# Node-level casting projection: the plan-layer ``selected_*`` key names derived
# from the SAME ``CASTING_FIELDS`` table that names the Agent-source
# ``preferred_*`` side. The mapping is the established convention
# (``selected_<rest>`` for ``preferred_<rest>``, twin of
# check_assembly_equivalence._effective_step_ref): one source of truth for the
# casting field set drives both the Agent ``preferred_*`` projection and the
# node/plan ``selected_*`` carry, so a new casting field is added in ONE place.
NODE_CASTING_FIELDS: tuple[str, ...] = tuple(
    "selected_" + descriptor.field_name.removeprefix("preferred_")
    for descriptor in CASTING_FIELDS
)


def selected_key(descriptor: CastingField) -> str:
    """The plan-layer ``selected_<rest>`` key name for a casting descriptor.

    The single reader of the ``preferred_<rest>`` -> ``selected_<rest>``
    convention; callers loop ``CASTING_FIELDS`` and use this to address the
    node/plan side without re-stating the prefix rule."""

    return "selected_" + descriptor.field_name.removeprefix("preferred_")


def casting_bag(source: Mapping[str, Any]) -> dict[str, Any]:
    """Pull the present ``selected_*`` casting keys from ``source``, blind.

    Pure transport: support copies whichever casting keys the caller declared,
    with no inspection, default-injection, or validation of the carried values.
    A key absent from ``source`` is simply absent from the bag.
    """

    return {
        field_name: source[field_name]
        for field_name in NODE_CASTING_FIELDS
        if field_name in source
    }


def merge_casting_bags(
    step_bag: Mapping[str, Any],
    plan_bag: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge two casting bags with per-field step-OR-plan precedence.

    For each casting field the step value wins when truthy, else the plan value;
    this preserves the hand-named ``step.get(k) or plan.get(k)`` carry exactly,
    including the ``None`` result when the field is declared on neither side.
    """

    return {
        field_name: (step_bag.get(field_name) or plan_bag.get(field_name))
        for field_name in NODE_CASTING_FIELDS
    }


def stamp_casting(target: dict[str, Any], bag: Mapping[str, Any]) -> dict[str, Any]:
    """Stamp every node casting key onto ``target`` from ``bag``.

    Every ``selected_*`` field is written (``None`` when absent from ``bag``) so
    the stamped node carries the full casting key set, byte-identical to the
    prior explicit per-field assignment. ``target`` is mutated and returned.
    """

    for field_name in NODE_CASTING_FIELDS:
        target[field_name] = bag.get(field_name)
    return target
