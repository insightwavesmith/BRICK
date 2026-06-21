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
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_DEFAULT,
    _validate_model_ref_for_adapter,
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
#   * ``validate``           the per-dial admission check (value, inherited_adapter_ref)
#                            -> raises on a bad value (model = the existing
#                            ``_validate_model_ref_for_adapter`` provider-match logic;
#                            effort = level-in-scope for an effort-capable adapter;
#                            adapter = membership is checked by the fail-closed loop,
#                            so its validate is a no-op).
#   * ``spawn_default``      the dial-OWN deferrable default when undeclared, read off
#                            the resolved ``LocalCliSpec`` (adapter => spec.adapter_ref;
#                            model => spec.default_model_ref; effort => its own sentinel,
#                            which ``cli_emit`` already suppresses to no-arg).
#   * ``native_config_emit`` the native-subagent config line(s) for a host config
#                            file (model => model line; effort => the host's
#                            reasoning-effort / effort line, scoped to ``EFFORT_SCOPE``;
#                            adapter => none).
# ---------------------------------------------------------------------------
class CastingField(NamedTuple):
    field_name: str
    fail_closed: bool
    default_ref: str | None
    scope: frozenset[str]
    inherits_source_of: str | None
    cli_emit: Callable[[str, str], tuple[str, ...]]
    validate: Callable[[str, str | None], None]
    spawn_default: Callable[[Any], str]
    native_config_emit: Callable[[str, str], tuple[str, ...]]


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
EFFORT_REF_PREFIX = "effort:"  # the effort dial's ref prefix (symmetric to model:).

# The effort-capable adapters (codex + claude). Gemini-local carries no reasoning
# effort dial, so it is out of scope — a declared effort on it is out-of-scope.
EFFORT_SCOPE: frozenset[str] = frozenset({ADAPTER_CODEX_LOCAL, ADAPTER_CLAUDE_LOCAL})

# The admitted reasoning-effort levels. A declared effort dial (bare ``low`` or
# the ref form ``effort:low``) must project to one of these levels for an adapter
# in ``EFFORT_SCOPE``.
EFFORT_LEVELS: frozenset[str] = frozenset(
    {"none", "minimal", "low", "medium", "high", "xhigh"}
)


def _effort_level(value: str) -> str:
    """Strip the dial's own ``effort:`` ref prefix to the bare level.

    Symmetric to the model dial's ``project_model_ref_to_cli_arg`` (which strips
    the ``model:<provider>:`` prefix): ``effort:low`` -> ``low``; a bare ``low``
    passes through unchanged.
    """

    return value.removeprefix(EFFORT_REF_PREFIX)


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
    # STRIP the dial's own ``effort:`` ref prefix before emitting, symmetric to the
    # model dial (which projects the ``model:<provider>:`` prefix off via
    # ``project_model_ref_to_cli_arg``): ``effort:low`` -> ``low`` so the codex
    # ``-c model_reasoning_effort=low`` / claude ``--effort low`` argv is the bare
    # level, never the ref-prefixed form.
    return emit(_effort_level(value))


# ---------------------------------------------------------------------------
# PER-DIAL VALIDATE HOOKS (value, inherited_adapter_ref) -> raises on bad value.
# Each dial ships its own admission check as DATA on its row, so the per-dial
# validation LOOP reads one hook instead of two hand-written code paths.
# ---------------------------------------------------------------------------
def _adapter_validate(_value: str, _inherited_adapter_ref: str | None) -> None:
    """The fail-closed adapter dial's membership is checked by the resolver/loop
    against the Agent Object's own ``adapter_refs`` (the constitutional asymmetry),
    so the adapter dial carries no value-shape validate of its own."""

    return None


def _model_validate(value: str, inherited_adapter_ref: str | None) -> None:
    """Validate the model dial against the adapter it inherits its SOURCE from.

    Byte-identical to the prior inline block: the deferrable model dial requires
    its ``inherits_source_of`` (adapter) dial to be present AND to carry an
    admitted model provider, then validates the model ref against it via the
    existing ``_validate_model_ref_for_adapter`` (provider-prefix + id-shape +
    secret-rejection) logic."""

    if inherited_adapter_ref is None:
        raise ValueError("preferred_model_ref requires preferred_adapter_ref")
    if MODEL_PROVIDER_BY_ADAPTER.get(inherited_adapter_ref) is None:
        raise ValueError(
            "preferred_model_ref requires preferred_adapter_ref with admitted model provider"
        )
    _validate_model_ref_for_adapter(inherited_adapter_ref, value)


def _effort_validate(value: str, inherited_adapter_ref: str | None) -> None:
    """Validate the effort dial: a bare/level or ``effort:<level>`` ref whose
    level is admitted, for an adapter in ``EFFORT_SCOPE``.

    Deferrable like the model dial: it couples to the adapter SOURCE it inherits.
    The adapter must be present, must be effort-capable (in ``EFFORT_SCOPE``), and
    the projected level (``effort:`` prefix stripped) must be an admitted level."""

    if inherited_adapter_ref is None:
        raise ValueError("preferred_reasoning_effort_ref requires preferred_adapter_ref")
    if inherited_adapter_ref not in EFFORT_SCOPE:
        raise ValueError(
            "preferred_reasoning_effort_ref requires an effort-capable adapter "
            f"(one of {sorted(EFFORT_SCOPE)})"
        )
    level = _effort_level(value)
    if level not in EFFORT_LEVELS:
        raise ValueError(
            f"preferred_reasoning_effort_ref level must be one of {sorted(EFFORT_LEVELS)}: {value}"
        )


# ---------------------------------------------------------------------------
# PER-DIAL spawn_default(spec) HOOKS -> the dial-OWN deferrable default when the
# dial is undeclared, read off the resolved LocalCliSpec. Replaces the 2-dial
# ternary at the spawn seam.
# ---------------------------------------------------------------------------
def _adapter_spawn_default(spec: Any) -> str:
    """The adapter dial's spawn fallback is the already-chosen spec adapter ref."""

    return spec.adapter_ref


def _model_spawn_default(spec: Any) -> str:
    """The model dial's spawn fallback is the spec's default model ref (the same
    ``request.selected_model_ref or spec.default_model_ref`` the inline projector
    fed before)."""

    return spec.default_model_ref


def _effort_spawn_default(_spec: Any) -> str:
    """The effort dial's spawn fallback is its own deferrable sentinel, which
    ``_effort_cli_emit`` already suppresses to a no-arg (let the adapter pick)."""

    return EFFORT_REF_DEFAULT


# ---------------------------------------------------------------------------
# PER-DIAL native_config_emit(value, target) HOOKS -> the native-subagent config
# line(s) for a host config file. ``target`` is the host token ("codex"/"claude");
# ``value`` is the agent's preferred_<base> (or "" when undeclared). The model
# dial preserves the prior host defaults BYTE-IDENTICALLY (no admitted Agent
# Object pins a model id today): codex omits the ``model`` line, claude emits
# ``model: "inherit"``. The effort dial emits a reasoning-effort line ONLY when a
# concrete level is declared for an effort-capable host.
# ---------------------------------------------------------------------------
NATIVE_TARGET_CODEX = "codex"
NATIVE_TARGET_CLAUDE = "claude"

# host token -> the adapter ref that host's native subagent config corresponds to.
_NATIVE_TARGET_ADAPTER: Mapping[str, str] = {
    NATIVE_TARGET_CODEX: ADAPTER_CODEX_LOCAL,
    NATIVE_TARGET_CLAUDE: ADAPTER_CLAUDE_LOCAL,
}


def _adapter_native_config_emit(_value: str, _target: str) -> tuple[str, ...]:
    """The adapter selection is the host/mode itself, not a native config line."""

    return ()


# The model refs that mean "no concrete model is pinned" — the generic sentinel
# plus each effort-capable host's own DEFAULT model ref. Every admitted Agent
# Object carries one of these, so the native model line collapses to the host
# default exactly as the prior per-adapter-refs helpers did (byte-identical).
_MODEL_NATIVE_DEFAULT_REFS: frozenset[str] = frozenset(
    {MODEL_REF_DEFAULT, MODEL_REF_CODEX_DEFAULT, MODEL_REF_CLAUDE_INHERIT}
)


def _model_native_config_emit(value: str, target: str) -> tuple[str, ...]:
    """Project the model dial to its native subagent config line.

    BYTE-IDENTICAL to the prior ``_codex_model_key_for_adapter_refs`` /
    ``_claude_model_key_for_adapter_refs`` defaults: no admitted Agent Object
    pins a concrete (non-default) model id, so any default/inherit ``value`` (the
    generic ``model:default`` OR the host's own default ref like
    ``model:codex:default`` / ``model:claude:inherit``) keeps the historical host
    default — codex OMITS the ``model`` key (empty tuple), claude emits
    ``model: "inherit"``. A concrete pinned model id (none today) would emit the
    host's model line carrying that id."""

    pinned = bool(value) and value not in _MODEL_NATIVE_DEFAULT_REFS
    if target == NATIVE_TARGET_CODEX:
        # codex inherits its CLI default (no key) unless a concrete codex model id
        # is pinned; none is, so this honestly omits today rather than inventing one.
        if not pinned:
            return ()
        return ("model = " + _toml_basic_string_for_native(value),)
    if target == NATIVE_TARGET_CLAUDE:
        if not pinned:
            return ("model: " + _claude_yaml_quote_for_native("inherit"),)
        return ("model: " + _claude_yaml_quote_for_native(value),)
    return ()


def _effort_native_config_emit(value: str, target: str) -> tuple[str, ...]:
    """Project the effort dial to its native subagent config line.

    Scoped to ``EFFORT_SCOPE`` (codex/claude). Deferrable: an absent/empty/default
    value emits nothing (inherit the host default). A concrete level emits the
    host's reasoning-effort line — codex ``model_reasoning_effort = "<level>"``,
    claude ``effort: "<level>"`` — with the dial's own ``effort:`` prefix stripped."""

    if not value or value == EFFORT_REF_DEFAULT:
        return ()
    if _NATIVE_TARGET_ADAPTER.get(target) not in EFFORT_SCOPE:
        return ()
    level = _effort_level(value)
    if target == NATIVE_TARGET_CODEX:
        return ("model_reasoning_effort = " + _toml_basic_string_for_native(level),)
    if target == NATIVE_TARGET_CLAUDE:
        return ("effort: " + _claude_yaml_quote_for_native(level),)
    return ()


def _toml_basic_string_for_native(value: str) -> str:
    """Encode a TOML basic (double-quoted) string for a native config line.

    Self-contained mirror of the support renderer's ``_toml_basic_string`` so the
    Agent-axis descriptor owns its own value-projection without importing support."""

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _claude_yaml_quote_for_native(value: str) -> str:
    """Double-quote a short single-line YAML frontmatter scalar for a native line.

    Self-contained mirror of the support renderer's ``_claude_yaml_quote``."""

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
        validate=_adapter_validate,
        spawn_default=_adapter_spawn_default,
        native_config_emit=_adapter_native_config_emit,
    ),
    CastingField(
        field_name="preferred_model_ref",
        fail_closed=False,
        default_ref=MODEL_REF_DEFAULT,
        scope=frozenset(MODEL_PROVIDER_BY_ADAPTER),
        inherits_source_of="preferred_adapter_ref",
        cli_emit=_model_cli_emit,
        validate=_model_validate,
        spawn_default=_model_spawn_default,
        native_config_emit=_model_native_config_emit,
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
        validate=_effort_validate,
        spawn_default=_effort_spawn_default,
        native_config_emit=_effort_native_config_emit,
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
