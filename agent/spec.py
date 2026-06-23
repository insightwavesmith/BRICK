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
from dataclasses import dataclass
from typing import Any, NamedTuple

from brick_protocol.support.connection.adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_FUGU_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ALLOWED_ADAPTER_REFS,
    MODEL_PROVIDER_BY_ADAPTER,
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_DEFAULT,
)
from brick_protocol.support.connection.adapter_model_casting import (
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
    # codex-fugu-local is the SAME codex executable, so its model id rides the
    # same ``-m`` flag (the Sakana provider/catalog is routed by the spec's
    # extra_config_overrides, not by the model flag).
    ADAPTER_CODEX_FUGU_LOCAL: "-m",
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

# The effort-capable adapters (codex + codex-fugu + claude). codex-fugu-local is
# the SAME codex executable, so it carries the SAME reasoning-effort dial as
# codex-local. Gemini-local carries no reasoning effort dial, so it is out of
# scope — a declared effort on it is out-of-scope.
EFFORT_SCOPE: frozenset[str] = frozenset(
    {ADAPTER_CODEX_LOCAL, ADAPTER_CODEX_FUGU_LOCAL, ADAPTER_CLAUDE_LOCAL}
)

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
    # codex-fugu-local: same codex executable -> same effort config-override shape.
    ADAPTER_CODEX_FUGU_LOCAL: lambda level: ("-c", "model_reasoning_effort=" + level),
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


# ---------------------------------------------------------------------------
# CASTING AUTHORING (E2/S1, moved from support/operator/assembly.py). The builder
# verbs ``agent()``/``brick()`` accept friendly ``**casting`` kwargs validated
# against ``CASTING_FIELDS`` names and project them to the node-layer
# ``selected_<base>`` bag. The validation+projection IS Agent-axis property (it is
# the WHO casting the plan declares), so it lives single-source on this axis; the
# Brick verb (``brick/spec.py:brick``) imports ``_build_casting_bag`` /
# ``_CASTING_KWARG_BY_NAME`` from here (brick -> agent, acyclic). Bodies are
# byte-identical to the prior ``assembly.py`` definitions; only the module home +
# the shared-coercer source change.
# ---------------------------------------------------------------------------
def _casting_ref_prefix(descriptor: Any) -> str:
    """The ref-prefix a casting dial's values carry (``adapter``/``model``/``effort``).

    Data-driven from ``CASTING_FIELDS``: a deferrable dial advertises its prefix
    via the ``<prefix>:`` of its ``default_ref`` sentinel (``model:default`` ->
    ``model``, ``effort:default`` -> ``effort``); the fail-closed adapter dial has
    no default sentinel, so its prefix is the base word (``adapter_ref`` ->
    ``adapter``). No per-dial literal here -- a new dial's prefix derives.
    """

    if descriptor.default_ref and ":" in descriptor.default_ref:
        return descriptor.default_ref.split(":", 1)[0]
    return descriptor.field_name.removeprefix("preferred_").removesuffix("_ref")


# Friendly builder kwarg name -> (selected_<base> node key, ref-prefix), derived
# once from the single-source CASTING_FIELDS. The kwarg name is the bare base word
# (``adapter``/``model``/``reasoning_effort``); ``agent()``/``brick()`` accept these
# generically so a NEW dial needs no new named kwarg (E2/§6 M15).
_CASTING_KWARG_BY_NAME: Mapping[str, tuple[str, str]] = {
    descriptor.field_name.removeprefix("preferred_").removesuffix("_ref"): (
        selected_key(descriptor),
        _casting_ref_prefix(descriptor),
    )
    for descriptor in CASTING_FIELDS
}


def _build_casting_bag(label: str, kwargs: Mapping[str, Any]) -> dict[str, str]:
    """Validate friendly casting kwargs and project to the ``selected_<base>`` bag.

    Generic over ``CASTING_FIELDS``: every admitted dial (adapter/model/effort/...)
    is read by its bare base-word kwarg, normalized to its ref-prefixed form, and
    stored under its node-layer ``selected_<base>`` key. An unknown kwarg raises.
    Byte-identical to the prior hand-named ``adapter``/``model`` normalization for
    those two dials.
    """

    bag: dict[str, str] = {}
    for name, raw_value in kwargs.items():
        mapping = _CASTING_KWARG_BY_NAME.get(name)
        if mapping is None:
            raise TypeError(f"{label} got unexpected casting argument: {name}")
        node_key, prefix = mapping
        value = _optional_bare_or_ref(name, raw_value)
        if value is None:
            continue
        bag[node_key] = _prefixed_ref(prefix, value)
    return bag


_ADMITTED_CASTING_PREFIXES: frozenset[str] = frozenset(
    f"{_casting_ref_prefix(descriptor)}:" for descriptor in CASTING_FIELDS
) | frozenset({"agent-object:"})


# ---------------------------------------------------------------------------
# SHARED COERCERS (E2/S1). Tiny value-shape helpers the casting authoring needs.
# Per the E2/S1 plan they STAY in ``support/operator/assembly.py`` (the graph
# wiring still uses them) AND are duplicated into the axis files that author a
# spec, so an axis module never imports the support builder. Byte-identical to the
# ``assembly.py`` definitions.
# ---------------------------------------------------------------------------
def _prefixed_ref(prefix: str, value: str) -> str:
    text = _non_empty_text(prefix, value)
    marker = f"{prefix}:"
    if text.startswith(marker):
        return text
    if ":" in text:
        raise ValueError(f"{prefix} must be bare or already {marker}-prefixed")
    return f"{marker}{text}"


def _optional_bare_or_ref(label: str, value: str | None) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    if ":" in text and not text.startswith(tuple(_ADMITTED_CASTING_PREFIXES)):
        raise ValueError(f"{label} must be bare text or an admitted ref")
    return text


def _bare_token(label: str, value: str) -> str:
    text = _non_empty_text(label, value)
    if ":" in text:
        raise ValueError(f"{label} must be a bare token")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _non_empty_text(label: str, value: Any) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"{label} must be non-empty text")
    return text


# ---------------------------------------------------------------------------
# AGENT-OBJECT SCHEMA (③ struct-surgery 0623, moved from
# support/connection/agent_resources.py:_AGENT_OBJECT_KEYS / _REF_FIELDS /
# _FORBIDDEN_AGENT_OBJECT_KEYS). The agent-OBJECT is the concrete WHO a lane casts
# materialized as a record: which prompts/skills/hooks/tool-policies/disciplines/
# adapters it binds, plus the casting dials. The set of keys an agent-object may
# carry (``allowed_keys``), the file-backed ref fields (``ref_fields``), and the
# keys it must NEVER carry (``forbidden_keys`` — provider connectors, credentials,
# session ids, success/failure/quality/movement authority) are Agent-axis property:
# they define the SHAPE of an Agent-axis record. They were sitting in a support
# connection file (and mirror-copied into support/operator/primitives.py +
# support/operator/native_dispatch.py) — definition belonging on the axis. This
# ONE schema owns them; support IMPORTS it to validate (load path + compose path)
# and to coerce/carry. The ``allowed_keys`` set DERIVES the casting key names from
# ``CASTING_FIELDS`` (the same single source), so a new casting dial flows into the
# admitted agent-object key-set with no edit here.
#
# The ``head_keys`` + ``ref_fields`` + ``forbidden_keys`` literal enumerations live
# ONLY here. ``ref_fields`` ORDER is load-bearing (the coercion loops it); it is a
# tuple. ``check_agent_object_schema_single_source`` REDs if these sets are defined
# anywhere but this schema; the registry-driven mirror guard
# (check_axis_field_set_single_source) REDs any literal copy under support/.
# ---------------------------------------------------------------------------
# The non-casting, non-ref head keys every agent-object carries.
_AGENT_OBJECT_HEAD_KEYS: tuple[str, ...] = (
    "object_ref",
    "name",
    "lane",
    "callable_performer_refs",
)
# The file-backed ref fields (prefix-resolved to prompt:/skill:/hook:/tool-policy:/
# discipline: / the admitted adapter vocabulary). ORDER is load-bearing: the
# coercion loops ``("callable_performer_refs", *ref_fields)`` to coerce each as a
# text array, byte-identical to the prior _REF_FIELDS / _AGENT_OBJECT_REF_FIELDS.
_AGENT_OBJECT_REF_FIELDS: tuple[str, ...] = (
    "prompt_refs",
    "skill_refs",
    "hook_refs",
    "tool_policy_refs",
    "discipline_refs",
    "adapter_refs",
)
# The keys an agent-object must NEVER carry: a provider connector / credential /
# session id (provider-coupling an Agent-axis record must never hold) or a
# success/failure/quality/movement-authority field (judgment an Agent record must
# never author). Byte-identical to the prior _FORBIDDEN_AGENT_OBJECT_KEYS /
# _NATIVE_DISPATCH_FORBIDDEN_AGENT_OBJECT_KEYS.
_AGENT_OBJECT_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "provider_connector_refs",
        "provider_request_body",
        "credential_body",
        "setup_token",
        "setup_token_value",
        "session_id",
        "provider_session_id",
        "agent_fact_shape",
        "agentfact_shape",
        "success",
        "failure",
        "quality",
        "movement_choice",
        "choose_movement",
        "default_gatefact",
        "default_gate_fact",
    }
)


class AgentObjectSchema(NamedTuple):
    """The single-source agent-OBJECT key/ref/forbidden schema (Agent axis).

    ``allowed_keys`` is the full admitted key-set (head keys + the casting dial
    names derived from ``CASTING_FIELDS`` + the ref fields); ``ref_fields`` is the
    order-bearing tuple of file-backed ref fields; ``forbidden_keys`` is the set an
    agent-object must never carry. The load path (agent_resources._load_agent_object)
    and the compose path (``agent()`` below) both validate against this ONE schema.
    """

    head_keys: tuple[str, ...]
    ref_fields: tuple[str, ...]
    forbidden_keys: frozenset[str]
    allowed_keys: frozenset[str]


def _build_agent_object_schema() -> AgentObjectSchema:
    """Assemble the agent-object schema, deriving the casting key names from the
    single-source ``CASTING_FIELDS`` so a new dial joins the admitted key-set with
    no edit. ``allowed_keys`` = head keys + casting field names + ref fields,
    byte-identical to the prior ``_AGENT_OBJECT_KEYS`` membership."""

    casting_names = tuple(descriptor.field_name for descriptor in CASTING_FIELDS)
    allowed_keys = frozenset(
        (*_AGENT_OBJECT_HEAD_KEYS, *casting_names, *_AGENT_OBJECT_REF_FIELDS)
    )
    return AgentObjectSchema(
        head_keys=_AGENT_OBJECT_HEAD_KEYS,
        ref_fields=_AGENT_OBJECT_REF_FIELDS,
        forbidden_keys=_AGENT_OBJECT_FORBIDDEN_KEYS,
        allowed_keys=allowed_keys,
    )


# The ONE agent-object schema. Support imports this (never a hand copy) to validate
# the load path + the compose path and to coerce the ref fields.
AGENT_OBJECT_SCHEMA: AgentObjectSchema = _build_agent_object_schema()


# ---------------------------------------------------------------------------
# AGENT AUTHORING (E2/S2, moved from support/operator/assembly.py). The Agent
# (lane) carrier and its authoring verb live on the Agent axis: an ``AgentSpec``
# is the WHO a lane casts (role + the generic ``selected_<base>`` casting bag),
# and ``agent()`` is the friendly verb that builds it — validating the bare
# ``role`` token and projecting the ``**casting`` dials through the single-source
# ``_build_casting_bag`` above. Bodies are byte-identical to the prior
# ``assembly.py`` definitions; only the module home + the shared-coercer source
# change. ``assembly.py`` re-exports ``AgentSpec``/``agent`` so existing callers
# keep resolving.
#
# ROLE-YAML FORM ONLY. ``agent("dev")`` NAMES a pre-authored role yaml, resolved at
# lower time to ``agent-object:dev`` -> agent/objects/dev.yaml; the only authoring
# inputs are the bare ``role`` token and the ``**casting`` dials. (A short-lived
# inline COMPOSE form that built the agent-object dict in-process was deleted at
# ③ struct-surgery 0623: it had ZERO downstream readers — node lowering reads only
# ``role`` + ``casting`` and re-resolves the role yaml from disk — so the composed
# object was silently dropped. The ONE ``AGENT_OBJECT_SCHEMA`` it validated against
# survives and is still used by the role-yaml load path in
# support/connection/agent_resources.py.)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, eq=False)
class AgentSpec:
    role: str
    # Generic per-lane casting carry (E2/§6 M15): a bag keyed by the node-layer
    # ``selected_<base>`` names (``NODE_CASTING_FIELDS``), values already
    # ref-prefixed. The builder NEVER names a dial here -- ``agent()`` builds the
    # bag once from ``CASTING_FIELDS``, so a new dial (effort) is carried with no
    # field edit.
    casting: Mapping[str, str] = ()  # type: ignore[assignment]


def agent(role: str, **kwargs: Any) -> AgentSpec:
    """Author an Agent lane spec.

    ``agent("dev")`` NAMES a pre-authored role yaml: the lower step resolves
    ``agent-object:<role>`` -> the role yaml. Optional ``**casting`` dials
    (``adapter=``/``model=``/``reasoning_effort=``, the ``CASTING_FIELDS`` base
    words) are validated + projected to the ``selected_<base>`` bag by
    ``_build_casting_bag``. Any other keyword raises a clear ``unexpected casting
    argument`` (``_build_casting_bag`` rejects every name not in
    ``_CASTING_KWARG_BY_NAME``).
    """

    clean_role = _bare_token("role", role)
    casting = _build_casting_bag("agent()", kwargs)
    return AgentSpec(role=clean_role, casting=casting)


def validate_agent_object_keys(label: str, agent_object: Mapping[str, Any]) -> None:
    """Validate an agent-object's KEY-SET against the single-source schema.

    Shared by the compose path (``agent()`` above) AND the support load path
    (agent_resources._load_agent_object imports this). Rejects an unknown key (not
    in ``AGENT_OBJECT_SCHEMA.allowed_keys``) and a forbidden key (in
    ``AGENT_OBJECT_SCHEMA.forbidden_keys``). Value-shape / authority / resolution
    checks stay with their respective callers; this is the ONE key-set gate.
    """

    keys = set(agent_object)
    unknown = sorted(keys - AGENT_OBJECT_SCHEMA.allowed_keys)
    if unknown:
        raise ValueError(f"{label}: unknown Agent Object keys: {', '.join(unknown)}")
    forbidden = sorted(keys & AGENT_OBJECT_SCHEMA.forbidden_keys)
    if forbidden:
        raise ValueError(f"{label}: forbidden Agent Object keys: {', '.join(forbidden)}")
