"""Model-ref normalization + casting->CLI-arg projection.

Extracted VERBATIM from ``brick_protocol/support/connection/agent_adapter.py`` (E2 split,
extraction 4/7). PURE relocation -- no logic/name/signature change. The
``agent_adapter`` facade re-exports every symbol here (public AND
underscore-private) so late-bound ``agent_adapter.<sym>`` access never breaks.

This module imports siblings DIRECTLY (adapter_constants, adapter_validation)
and NEVER ``from support.connection.agent_adapter import ...`` at top level
(cycle). The spec carriers that still live in ``agent_adapter`` (``LocalCliSpec``,
``AgentAdapterRequest``, ``_local_cli_spec``) are reached
LAZILY in-function so the back-edge resolves only at call time. The external
``brick_protocol.*`` imports stay byte-identical (they are kept lazy/in-function
exactly as the prior agent_adapter-local code had them).
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

from .adapter_constants import (
    ADAPTER_LOCAL,
    ADAPTER_CHAT_SESSION,
    ADAPTER_GEMINI_LOCAL,
    MODEL_REF_DEFAULT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_GEMINI_DEFAULT,
    MODEL_PROVIDER_BY_ADAPTER,
)
from .adapter_validation import _reject_secret_text

if TYPE_CHECKING:
    from .agent_adapter import AgentAdapterRequest, LocalCliSpec

_RETIRED_ACTIVE_MODEL_REFS = frozenset()


# Lazy CASTING_FIELDS / NODE_CASTING_FIELDS access (E2/S6★). ``agent.spec``
# re-exports THIS module's brain catalog, so a top-level import of the casting
# field-set here would be circular. The request's generic per-dial casting
# accessor + normalize LOOP read the field-set through these cached lazy getters
# so the dataclass names no individual dial.
_CASTING_FIELDS_CACHE: tuple[Any, ...] | None = None
_NODE_CASTING_FIELDS_CACHE: frozenset[str] | None = None


def _casting_fields() -> tuple[Any, ...]:
    global _CASTING_FIELDS_CACHE
    if _CASTING_FIELDS_CACHE is None:
        from brick_protocol.agent.spec import CASTING_FIELDS

        _CASTING_FIELDS_CACHE = CASTING_FIELDS
    return _CASTING_FIELDS_CACHE


def _node_casting_fields() -> frozenset[str]:
    global _NODE_CASTING_FIELDS_CACHE
    if _NODE_CASTING_FIELDS_CACHE is None:
        from brick_protocol.agent.spec import NODE_CASTING_FIELDS

        _NODE_CASTING_FIELDS_CACHE = frozenset(NODE_CASTING_FIELDS)
    return _NODE_CASTING_FIELDS_CACHE


_NODE_CASTING_FIELDS_ORDERED_CACHE: tuple[str, ...] | None = None


def _node_casting_fields_ordered() -> tuple[str, ...]:
    """The ordered node-layer ``selected_<base>`` keys (load-bearing dial order).

    Used where the casting dials are SERIALIZED into a stable-order mapping (the
    work-envelope / prompt / returned-evidence) so a NEW dial joins the serialized
    bag with no edit at each seam."""

    global _NODE_CASTING_FIELDS_ORDERED_CACHE
    if _NODE_CASTING_FIELDS_ORDERED_CACHE is None:
        from brick_protocol.agent.spec import NODE_CASTING_FIELDS

        _NODE_CASTING_FIELDS_ORDERED_CACHE = tuple(NODE_CASTING_FIELDS)
    return _NODE_CASTING_FIELDS_ORDERED_CACHE


def project_model_ref_to_cli_arg(adapter_ref: str, selected_model_ref: str = "") -> str:
    """Project a selected_model_ref to the local CLI model argument.

    This is support projection only. It does not prove provider availability or
    model quality.
    """

    from .agent_adapter import _local_cli_spec

    if adapter_ref == ADAPTER_LOCAL:
        _normalize_selected_model_ref(adapter_ref, selected_model_ref)
        return ""
    if adapter_ref == ADAPTER_CHAT_SESSION:
        _normalize_selected_model_ref(adapter_ref, selected_model_ref)
        return ""
    spec = _local_cli_spec(adapter_ref)
    normalized = _normalize_selected_model_ref(adapter_ref, selected_model_ref)
    return _model_cli_arg_from_ref(normalized, spec)


def _adapter_model_spec(adapter_ref: str) -> "LocalCliSpec":
    """Return the model-selection spec carrier for an adapter ref.

    Active model selection is tied to admitted local CLI adapters.
    """
    from .agent_adapter import _local_cli_spec

    return _local_cli_spec(adapter_ref)


def _normalize_selected_model_ref(adapter_ref: str, selected_model_ref: str) -> str:
    if adapter_ref in {ADAPTER_LOCAL, ADAPTER_CHAT_SESSION}:
        if selected_model_ref and selected_model_ref != MODEL_REF_DEFAULT:
            raise ValueError(f"{adapter_ref} accepts only model:default")
        return MODEL_REF_DEFAULT
    spec = _adapter_model_spec(adapter_ref)
    if not selected_model_ref:
        return spec.default_model_ref
    if selected_model_ref == MODEL_REF_DEFAULT:
        return spec.default_model_ref
    # build-unify #12 D5 (표18 residual): reject an UNADMITTED provider model
    # alias LOUDLY at this normalization choke point (request construction /
    # read-only CLI-arg projection) instead of letting it survive to spawn. The
    # spawn-side loud resolution + --model passthrough already landed
    # (model-alias-loud-0706a); this closes the earlier window where an
    # alias-shaped id (e.g. a "sonnet" typo) slipped past _validate_model_ref_for
    # _adapter (prefix+charset only) and only died mid-walk at dispatch.
    # resolve_model_alias_ref validates the alias against the admitted catalog and
    # raises on an unknown one; we DISCARD its concrete expansion and return the
    # DECLARED ref so the declared-alias-vs-dispatched-model observability contract
    # (adapter usage meter model_alias_resolution) stays intact. The reverse import
    # edge is lazy (provider_registry imports this module at top level).
    from brick_protocol.support.operator.provider_registry import (  # noqa: PLC0415
        resolve_model_alias_ref,
    )

    resolve_model_alias_ref(adapter_ref, selected_model_ref)
    return selected_model_ref


def _validate_model_ref_for_adapter(adapter_ref: str, model_ref: str) -> None:
    provider = MODEL_PROVIDER_BY_ADAPTER.get(adapter_ref)
    if provider is None:
        raise ValueError("selected_model_ref is supported only for admitted local CLI adapters")
    expected_prefix = f"model:{provider}:"
    if not model_ref.startswith(expected_prefix):
        raise ValueError("selected_model_ref provider must match selected adapter")
    model_id = model_ref.removeprefix(expected_prefix)
    if not model_id:
        raise ValueError("selected_model_ref must include a model id")
    if model_ref in _RETIRED_ACTIVE_MODEL_REFS:
        raise ValueError("selected_model_ref model id is retired from active dispatch")
    _reject_secret_text("selected_model_ref", model_ref)
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", model_id):
        raise ValueError("selected_model_ref model id contains unsupported characters")


def _model_cli_arg(request: "AgentAdapterRequest", spec: "LocalCliSpec") -> str:
    return _model_cli_arg_from_ref(request.selected_model_ref or spec.default_model_ref, spec)


def _casting_cli_args(request: "AgentAdapterRequest", spec: "LocalCliSpec") -> tuple[str, ...]:
    """Project the casting dials to their spawn-time CLI args via CASTING_FIELDS.

    E2/S6 (mirror M6): the per-adapter CLI flag knowledge that was inlined twice
    (the codex ``-m`` / claude ``--model`` literals) is now DATA on each
    ``CastingField.cli_emit``. The spawn path LOOPS the field-set and concatenates
    each dial's emit; the adapter dial contributes nothing (``_no_cli_emit``), the
    model dial contributes ``(flag, model_arg)`` exactly as the deleted literals
    did. BYTE-IDENTICAL to the inline path: the per-dial spawn VALUE is the
    declared ``selected_*`` on the request, else — for the deferrable model dial
    (``default_ref is not None``) — the spec's ``default_model_ref`` (the same
    ``request.selected_model_ref or spec.default_model_ref`` the inline
    ``_model_cli_arg`` fed its projector); the fail-closed adapter dial
    (``default_ref is None``) falls back to the already-chosen ``spec.adapter_ref``
    and emits nothing. A provider mismatch raises identically (the projector
    inside ``cli_emit`` raises just as the inline ``_model_cli_arg`` did).

    Imported lazily to avoid an import cycle: ``agent.spec`` re-exports this
    module's brain catalog, so a top-level import here would be circular.
    """

    from brick_protocol.agent.spec import CASTING_FIELDS, selected_key

    args: list[str] = []
    for descriptor in CASTING_FIELDS:
        declared = getattr(request, selected_key(descriptor), "")
        # The per-dial deferrable spawn default is descriptor DATA now (replaces the
        # 2-dial ternary): adapter => spec.adapter_ref, model => spec.default_model_ref,
        # effort => its own sentinel (which cli_emit suppresses to no-arg). A NEW dial
        # supplies its own spawn_default with no edit here. Byte-identical for the two
        # existing dials.
        value = declared or descriptor.spawn_default(spec)
        args.extend(descriptor.cli_emit(value, spec.adapter_ref))
    return tuple(args)


def _model_cli_arg_from_ref(model_ref: str, spec: "LocalCliSpec") -> str:
    if model_ref in {MODEL_REF_DEFAULT, spec.default_model_ref}:
        if model_ref in {MODEL_REF_CODEX_DEFAULT, MODEL_REF_CLAUDE_INHERIT, MODEL_REF_DEFAULT}:
            return ""
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL and model_ref == MODEL_REF_GEMINI_DEFAULT:
        return ""
    provider = MODEL_PROVIDER_BY_ADAPTER.get(spec.adapter_ref)
    if provider is None:
        return ""
    expected_prefix = f"model:{provider}:"
    if not model_ref.startswith(expected_prefix):
        raise ValueError("selected_model_ref provider must match selected adapter")
    model_id = model_ref.removeprefix(expected_prefix)
    if model_id in {"default", "inherit"}:
        return ""
    return model_id
