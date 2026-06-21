"""Link-owned plan-level declarable grammar (axis single-source API, E2/§2 AXIS C).

This is the Link single-source API (E2 design §2 AXIS C). The plan-level Link
grammar a builder DECLARES is Link-axis property, not support mechanics. It owns:

  * the gate-concept translation table + ``translate_gate_concept`` (E2/S3);
  * ``LINK_ROW_ALLOWED_KEYS`` + every Link sub-envelope SCHEMA as DATA, each a
    ``LinkEnvelope`` descriptor (allowed-keys, forbidden-keys, author-prefix
    grammar, state literals, the evidence field-spec) — E2/S4 (mirror M12);
  * the Link authority forbidden-ref-prefix vocabularies — E2/S4 (mirror M13).

It defines plan-level Link vocabulary; it authors no Movement, invents no route,
and judges no success or quality.

AXIS DEPENDENCY DIRECTION (why ``validate_link_envelope`` takes a context). The
per-envelope DATA (allowed/forbidden key-sets, prefixes, state literals, the
evidence field-spec) is the single-source mirror this module owns. The field
COERCERS (``required_text``/``text_tuple``/``positive_int``) and the few
field-specific cross-cut RULES (target-match, append-only distinctness, declared
Brick membership, paused/resumed state branches, disposition-action rules) are
support-validation mechanics that depend on the support validator's own helper
web; the axis must NOT import support. So the generic driver here runs the
UNIFORM envelope skeleton (presence guard -> mapping -> authority-key rejection
-> allowed-key admission -> field-specific body) over the descriptor DATA and
delegates the coercers + the field-specific body through an injected
``LinkEnvelopeContext``. The error TEXT every checker/profile pins is produced
verbatim (same messages, same symbols re-exported from the support validator),
so accept/reject is byte-for-byte what the per-envelope validators produced.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

from brick_protocol.link.gate import DECLARED_GATE_REFS
from brick_protocol.link.transition import (
    TRANSITION_LIFECYCLE_ALLOWED_KEYS,
)


# ---------------------------------------------------------------------------
# GATE-CONCEPT TRANSLATION (Link plan grammar; E2/S3). A preset DECLARES a
# ``gate_concept_profile`` of concept tokens; the materializer TRANSLATES each
# token into a live ``declared_gate_ref`` on a specific row. The token -> ref map
# is single-sourced here over the Link-owned gate vocabulary
# (``DECLARED_GATE_REFS``: [0]=default-transition, [1]=strict, [2]=human,
# [3]=coo). MODE tokens (default-transition / fan-in-wait-all / portfolio-policy)
# have NO gate ref here on purpose: they are not Link gates (fan-in-wait-all =
# declared graph topology requirement, portfolio-policy = driver surface).
# ---------------------------------------------------------------------------
GATE_CONCEPT_TOKEN_GATE_REFS: Mapping[str, str] = {
    "strict-evidence": DECLARED_GATE_REFS[1],
    "coo-review": DECLARED_GATE_REFS[3],
    "human-review": DECLARED_GATE_REFS[2],
}


def translate_gate_concept(token: str) -> str:
    """Translate ONE gate-concept token to its live ``declared_gate_ref``.

    The single Link-owned reader of ``GATE_CONCEPT_TOKEN_GATE_REFS``. Raises
    ``KeyError`` for a non-translating token (MODE tokens or unknown labels never
    reach this helper: the materializer guards on membership before calling).
    Returns the byte-identical ref the prior inline ``GATE_CONCEPT_TOKEN_GATE_REFS[token]``
    subscripts produced.
    """

    return GATE_CONCEPT_TOKEN_GATE_REFS[token]


# MODE gate-concept tokens (E2/S8): builder-declarable gate concepts that carry
# NO live gate ref (they are not Link gates). ``default-transition`` is the
# concept word of the Link-owned default gate ref ``DECLARED_GATE_REFS[0]``
# (``link-gate:default-transition``) -- derived from its suffix so the token
# cannot drift from the gate vocab. ``fan-in-wait-all`` is a declared graph
# topology requirement (see the GATE_CONCEPT_TOKEN_GATE_REFS comment); it has no
# gate ref, so it is named once HERE on the Link axis -- the single source the
# builder ``Gate`` enum derives from rather than re-stating literals.
GATE_CONCEPT_MODE_TOKENS: tuple[str, ...] = (
    DECLARED_GATE_REFS[0].split(":", 1)[1],
    "fan-in-wait-all",
)

# The full builder-declarable gate-concept token vocabulary (E2/S8): the
# translatable tokens (single-sourced in GATE_CONCEPT_TOKEN_GATE_REFS) plus the
# MODE tokens. The friendly ``Gate`` enum in the builder DERIVES its ``.value``s
# from this set (no hardcoded gate-token strings in the builder).
GATE_CONCEPT_TOKENS: frozenset[str] = (
    frozenset(GATE_CONCEPT_TOKEN_GATE_REFS) | frozenset(GATE_CONCEPT_MODE_TOKENS)
)

# Transition-concern adoption vocabulary (E2/S8): the two adoption literals a
# builder declares for ``transition_concern_adoption``. ``binding`` is the
# default (the ref-less plan flow); ``advisory`` downgrades the concern's
# closure authority (read in walker_kernel.py / composition.py). Single-sourced
# HERE on the Link axis (adoption is Link-movement property), so the builder
# ``Adoption`` enum derives its ``.value``s rather than re-stating literals.
ADOPTION_LITERALS: tuple[str, ...] = ("binding", "advisory")


# ---------------------------------------------------------------------------
# LINK ROW + ENVELOPE KEYS (moved from support/operator/primitives.py at E2/S4).
# The plan-layer Link row admits exactly these keys; each sub-envelope key names
# the row field its descriptor governs.
# ---------------------------------------------------------------------------
LINK_ROW_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "axis",
        "row_ref",
        "declared_gate_refs",
        "gate_sequence_policy",
        # Machine-readable provenance for TRANSLATED gate stamps (gate wiring
        # 0610): the materializer records {tokens, declared_by} on a Link row
        # whose declared_gate_refs were stamped from the preset's
        # gate_concept_profile -- ONLY when translation happened. The key is
        # ADMITTED here; its VALUE discipline (non-empty tokens + declaring
        # ref, fail-closed) is owned by
        # plan_validation._validate_gate_concept_provenance_for_link_row.
        "gate_concept_provenance",
        "link_contract_ref",
        "next_brick_instance_ref",
        "next_boundary_ref",
        "movement",
        "movement_literal",
        "target",
        "target_ref",
        "target_boundary_ref",
        "route_replay_plan",
        "route_decision_basis",
        "transition_authoring",
        "transition_lifecycle",
        "building_lifecycle",
        "public_fact_refs",
        "raw_refs",
    }
)

ROUTE_REPLAY_PLAN_KEY = "route_replay_plan"
DECLARED_GATE_REFS_KEY = "declared_gate_refs"
ROUTE_DECISION_BASIS_KEY = "route_decision_basis"
GATE_SEQUENCE_POLICY_KEY = "gate_sequence_policy"
TRANSITION_AUTHORING_KEY = "transition_authoring"
TRANSITION_LIFECYCLE_KEY = "transition_lifecycle"
BUILDING_LIFECYCLE_KEY = "building_lifecycle"


# ---------------------------------------------------------------------------
# FORBIDDEN-REF-PREFIX VOCABULARIES (E2/S4 mirror M13). The support validator
# duplicated forbidden-prefix tuples across five sites. They are NOT one tuple:
# there are THREE DISTINCT vocabularies (verified member-by-member at the live
# tree). Single-sourcing them here de-duplicates the IDENTICAL pair
# (route-reason == route-endpoint) while preserving each distinct vocabulary
# byte-for-byte — collapsing the three into one would change accept/reject.
#
#   * ROUTE_AUTHOR / ROUTE_REPLAY_SEGMENT_BASE: 19 members; has scheduler:/support:,
#     NOT mutation:/state:/agent:. The author-tuple form (with ":") and the
#     bare-word segment form (without ":") share these 19 members.
#   * ROUTE_REASON_ENDPOINT: 19 members; has mutation:/state:, NOT
#     scheduler:/support:/agent:. Used by route-reason refs AND route endpoints.
#   * DECISION_REF: 21 members; the author set + agent:/agent-object:.
# ---------------------------------------------------------------------------
LINK_FORBIDDEN_REF_SEGMENTS: frozenset[str] = frozenset(
    {
        "adapter",
        "agent",
        "auth",
        "credential",
        "env",
        "external_secret",
        "hook",
        "keychain",
        "provider",
        "queue",
        "retry",
        "rollback",
        "runtime",
        "scheduler",
        "secret",
        "session",
        "setup-token",
        "setup_token",
        "support",
        "tool",
    }
)
LINK_FORBIDDEN_REF_PREFIXES_AUTHOR: tuple[str, ...] = (
    "adapter:",
    "auth:",
    "credential:",
    "env:",
    "external_secret:",
    "hook:",
    "keychain:",
    "provider:",
    "queue:",
    "retry:",
    "rollback:",
    "runtime:",
    "scheduler:",
    "secret:",
    "session:",
    "setup-token:",
    "setup_token:",
    "support:",
    "tool:",
)
LINK_FORBIDDEN_REF_PREFIXES_ROUTE_REASON: tuple[str, ...] = (
    "adapter:",
    "auth:",
    "credential:",
    "env:",
    "external_secret:",
    "hook:",
    "keychain:",
    "mutation:",
    "provider:",
    "queue:",
    "retry:",
    "rollback:",
    "runtime:",
    "secret:",
    "session:",
    "setup-token:",
    "setup_token:",
    "state:",
    "tool:",
)
# Route endpoint refs reject the same vocabulary as route-reason refs (the two
# tuples were byte-identical at the live tree); single source = one constant.
LINK_FORBIDDEN_REF_PREFIXES_ROUTE_ENDPOINT: tuple[
    str, ...
] = LINK_FORBIDDEN_REF_PREFIXES_ROUTE_REASON
LINK_FORBIDDEN_REF_PREFIXES_DECISION: tuple[str, ...] = (
    "adapter:",
    "agent:",
    "agent-object:",
    "auth:",
    "credential:",
    "env:",
    "external_secret:",
    "hook:",
    "keychain:",
    "provider:",
    "queue:",
    "retry:",
    "rollback:",
    "runtime:",
    "scheduler:",
    "secret:",
    "session:",
    "setup-token:",
    "setup_token:",
    "support:",
    "tool:",
)
ROUTE_REPLAY_ALLOWED_AUTHOR_PREFIXES: tuple[str, ...] = (
    "human:",
    "coo:",
    "link-planning-brick:",
    "template:",
)
ROUTE_REASON_ALLOWED_PUBLIC_FACT_PREFIXES: tuple[str, ...] = (
    "agent-fact:",
    "brick-comparison:",
    "brick-work:",
    "carry-fact:",
    "human-review:",
    "movement-fact:",
    "observation:",
    "override:",
    "review-observation:",
    "sufficiency-fact-",
    "transition-concern:",
    "transfer-fact:",
)
ROUTE_REPLAY_ENDPOINT_LIST_KEYS: tuple[str, ...] = (
    "source_brick_refs",
    "affected_downstream_refs",
    "replay_segment_refs",
)


# ---------------------------------------------------------------------------
# SUB-ENVELOPE ALLOWED-KEY / FORBIDDEN-KEY / VALUE-MARKER SCHEMAS (moved from
# support/operator/primitives.py at E2/S4 mirror M12). Each is the member-set the
# support validator's _require_only_keys / authority-rejection loops read.
# ---------------------------------------------------------------------------
ROUTE_REPLAY_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "route_replay_ref",
        "author_ref",
        "authoring_basis_refs",
        "immediate_target_ref",
        "source_brick_refs",
        "route_reason_refs",
        "affected_downstream_refs",
        "replay_segment_refs",
        "max_attempts",
        "proof_limits",
        "not_proven",
    }
)
ROUTE_REPLAY_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "chosen_route_target",
        "chosen_replay_segment",
        "completed",
        "current_block",
        "current_state",
        "destination_choice",
        "engine_loop",
        "failed",
        "mutable_state",
        "mutate",
        "mutated_instance_ref",
        "mutates_instance_ref",
        "mutation",
        "pending",
        "queue",
        "queued",
        "retry",
        "retry_policy",
        "rollback",
        "rollback_executor",
        "route_choice",
        "route_target_choice",
        "runtime",
        "runtime_owner",
        "scheduler",
        "scheduler_owner",
        "selected_route_target",
        "selected_replay_segment",
        "state",
        "status",
        "support_chosen_replay_segment",
        "support_chosen_route_target",
        "targets",
    }
)
ROUTE_REPLAY_FORBIDDEN_VALUE_MARKERS: tuple[str, ...] = (
    "chosen replay",
    "chosen route",
    "current block",
    "current state",
    "engine loop",
    "mutable state",
    "mutation",
    "pending",
    "queue:",
    "queued",
    "retry:",
    "rollback:",
    "runtime:",
    "runtime owner",
    "scheduler:",
    "scheduler owner",
    "selected replay",
    "selected route",
    "state mutation",
    "support chosen",
)
TRANSITION_AUTHORING_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "transition_authoring_ref",
        "author_ref",
        "authoring_basis_refs",
        "transition_reason_refs",
        "proof_limits",
        "not_proven",
    }
)
ROUTE_DECISION_BASIS_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "adopted_transition_concern_refs",
        "not_adopted_transition_concern_refs",
        "override_refs",
        "reviewer_observation_refs",
        "human_review_refs",
        "proof_limits",
        "not_proven",
    }
)
BUILDING_LIFECYCLE_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "state",
        "reason",
        "proof_limits",
        "not_proven",
    }
)


# ---------------------------------------------------------------------------
# EVIDENCE FIELD-SPEC (E2/S4 mirror M12 third read). Each per-envelope evidence
# extractor reads the SAME schema a third time to flatten the envelope into named
# evidence fields. The shape is uniform under this spec: required-text fields,
# optional-text fields, an optional positive-int field, optional list fields —
# each as a (source_key, output_key) pair, applied in order. ``out_prefix``
# carries the per-envelope output-name rule (e.g. ``transition_lifecycle_``).
# ---------------------------------------------------------------------------
# Emit-step kinds. The evidence spec is an ORDERED list of steps; the generic
# applier walks them in declared order so the output dict's key order is
# byte-identical to each original extractor body (dict order is observable).
_REQ_TEXT = "required_text"  # always emitted, REQUIRED non-blank text
_OPT_TEXT = "optional_text"  # emitted as required text only when src present
_OPT_INT = "optional_int"    # emitted as positive int only when src present
_OPT_LIST = "optional_list"  # emitted as a text-tuple list only when src present


class _Step(NamedTuple):
    kind: str
    src: str
    out: str


def _steps(kind: str, keys: tuple[str, ...], *, prefix: str = "", rename: Mapping[str, str] | None = None) -> tuple[_Step, ...]:
    rename = rename or {}
    return tuple(
        _Step(kind, key, rename.get(key, prefix + key)) for key in keys
    )


# Back-compat thin record so callers reading ``.steps`` get the ordered spec.
class LinkEvidenceSpec(NamedTuple):
    steps: tuple[_Step, ...]


class LinkEnvelope(NamedTuple):
    """A Link sub-envelope SCHEMA, carried purely as DATA.

    ``name`` is the row field this envelope governs; ``allowed_keys`` is the
    admitted key-set; ``evidence`` is the flatten spec. The support validator
    reads these to run the uniform envelope skeleton + evidence flatten;
    field-specific cross-cut rules stay with the support validator (injected as
    the body callback) so error text stays byte-identical.
    """

    name: str
    allowed_keys: frozenset[str]
    evidence: LinkEvidenceSpec


LINK_ENVELOPES: Mapping[str, LinkEnvelope] = {
    # route_replay extractor body order: required_text(3) -> list(7) -> int(1).
    ROUTE_REPLAY_PLAN_KEY: LinkEnvelope(
        name=ROUTE_REPLAY_PLAN_KEY,
        allowed_keys=ROUTE_REPLAY_ALLOWED_KEYS,
        evidence=LinkEvidenceSpec(
            steps=(
                *_steps(_REQ_TEXT, ("route_replay_ref", "author_ref", "immediate_target_ref")),
                *_steps(
                    _OPT_LIST,
                    (
                        "authoring_basis_refs",
                        "source_brick_refs",
                        "route_reason_refs",
                        "affected_downstream_refs",
                        "replay_segment_refs",
                        "proof_limits",
                        "not_proven",
                    ),
                ),
                *_steps(_OPT_INT, ("max_attempts",)),
            ),
        ),
    ),
    # transition_authoring body order: required_text(2) -> list(4).
    TRANSITION_AUTHORING_KEY: LinkEnvelope(
        name=TRANSITION_AUTHORING_KEY,
        allowed_keys=TRANSITION_AUTHORING_ALLOWED_KEYS,
        evidence=LinkEvidenceSpec(
            steps=(
                *_steps(
                    _REQ_TEXT,
                    ("transition_authoring_ref", "author_ref"),
                    rename={
                        "transition_authoring_ref": "transition_authoring_ref",
                        "author_ref": "transition_author_ref",
                    },
                ),
                *_steps(
                    _OPT_LIST,
                    ("authoring_basis_refs", "transition_reason_refs", "proof_limits", "not_proven"),
                    prefix="transition_",
                ),
            ),
        ),
    ),
    # route_decision_basis body order: list(7) only.
    ROUTE_DECISION_BASIS_KEY: LinkEnvelope(
        name=ROUTE_DECISION_BASIS_KEY,
        allowed_keys=ROUTE_DECISION_BASIS_ALLOWED_KEYS,
        evidence=LinkEvidenceSpec(
            steps=_steps(
                _OPT_LIST,
                (
                    "adopted_transition_concern_refs",
                    "not_adopted_transition_concern_refs",
                    "override_refs",
                    "reviewer_observation_refs",
                    "human_review_refs",
                    "proof_limits",
                    "not_proven",
                ),
                prefix="route_decision_",
            ),
        ),
    ),
    # transition_lifecycle body order: required_text(2) -> text(6) -> int(1) -> list(3).
    TRANSITION_LIFECYCLE_KEY: LinkEnvelope(
        name=TRANSITION_LIFECYCLE_KEY,
        allowed_keys=TRANSITION_LIFECYCLE_ALLOWED_KEYS,
        evidence=LinkEvidenceSpec(
            steps=(
                *_steps(
                    _REQ_TEXT,
                    ("state", "progress_state"),
                    prefix="transition_lifecycle_",
                ),
                *_steps(
                    _OPT_TEXT,
                    (
                        "paused_at_ref",
                        "resumed_from_ref",
                        "from_brick_ref",
                        "pending_target_ref",
                        "required_disposition_owner",
                        "disposition_action",
                    ),
                    prefix="transition_lifecycle_",
                ),
                *_steps(_OPT_INT, ("budget_increment",), prefix="transition_lifecycle_"),
                *_steps(
                    _OPT_LIST,
                    ("reason_refs", "proof_limits", "not_proven"),
                    prefix="transition_lifecycle_",
                ),
            ),
        ),
    ),
    # building_lifecycle body order: required_text(1) -> text(1) -> list(2).
    BUILDING_LIFECYCLE_KEY: LinkEnvelope(
        name=BUILDING_LIFECYCLE_KEY,
        allowed_keys=BUILDING_LIFECYCLE_ALLOWED_KEYS,
        evidence=LinkEvidenceSpec(
            steps=(
                *_steps(_REQ_TEXT, ("state",), prefix="building_lifecycle_"),
                *_steps(_OPT_TEXT, ("reason",), prefix="building_lifecycle_"),
                *_steps(_OPT_LIST, ("proof_limits", "not_proven"), prefix="building_lifecycle_"),
            ),
        ),
    ),
}


class LinkEnvelopeContext(NamedTuple):
    """Injected support-validation COERCERS the generic driver delegates to.

    The DATA (key-sets, prefixes, evidence spec) is Link-axis property; these
    coercers are support-validation helpers that depend on the support
    validator's helper web (and must not be pulled into the axis). Passing them
    in keeps accept/reject + error text byte-for-byte identical to the
    per-envelope validators/extractors while the schema lives single-source here.
    """

    mapping: Callable[[str, Any], Mapping[str, Any]]
    required_text: Callable[[str, Any], str]
    text_tuple: Callable[[str, Any], tuple[str, ...]]
    positive_int: Callable[[str, Any], int]


def validate_link_envelope(
    name: str,
    link_row: Mapping[str, Any],
    ctx: LinkEnvelopeContext,
    body: Callable[[Mapping[str, Any]], None],
    *,
    none_is_value_error: bool = True,
) -> None:
    """Run the UNIFORM Link sub-envelope opening, then delegate to ``body``.

    Reproduces, byte-for-byte, the shared opening every per-envelope validator
    ran: presence guard (absent key -> no-op), then mapping coercion. Two
    envelopes families differ ONLY in how an explicit ``None`` value is reported,
    and that difference is preserved as DATA via ``none_is_value_error``:

      * the four envelopes that resolved their payload through a
        ``_<env>_from_link_row`` helper reported a None value as
        ``ValueError("<name> must be a mapping")`` (``none_is_value_error=True``);
      * ``building_lifecycle`` resolved via the bare ``_mapping`` coercer, so a
        None value flows into the ctx mapping coercer and reports as the coercer's
        ``TypeError("<name> must be a mapping")`` (``none_is_value_error=False``).

    A non-mapping (non-None) value always flows into the ctx mapping coercer
    (``TypeError``). The rest — authority-key rejection, allowed-key admission,
    and the field-specific rules — is the body, kept in the support validator in
    its ORIGINAL per-envelope order (authority-rejection vs allowed-key admission
    ordering differs between envelopes, so it is NOT hoisted here). ``name`` must
    be a registered envelope key; ``body`` receives the coerced payload mapping.
    """

    envelope = LINK_ENVELOPES[name]
    if envelope.name not in link_row:
        return
    value = link_row.get(envelope.name)
    if value is None and none_is_value_error:
        raise ValueError(f"{envelope.name} must be a mapping")
    payload = ctx.mapping(envelope.name, value)
    body(payload)


def link_envelope_evidence_fields(
    name: str,
    link_row: Mapping[str, Any],
    ctx: LinkEnvelopeContext,
) -> dict[str, Any]:
    """Flatten ONE Link sub-envelope into named evidence fields via its spec.

    Reproduces the per-envelope evidence extractor byte-for-byte: an absent
    envelope -> ``{}``; otherwise required-text fields first (in declared order),
    then optional positive-int, then optional-text, then optional-list — each
    emitted only when present, under the spec's output-name rule. The emit ORDER
    per spec matches each original extractor (see LINK_ENVELOPES specs).
    """

    envelope = LINK_ENVELOPES[name]
    value = link_row.get(envelope.name)
    if value is None:
        return {}
    payload = ctx.mapping(envelope.name, value)
    fields: dict[str, Any] = {}
    for kind, src, out in envelope.evidence.steps:
        if kind == _REQ_TEXT:
            fields[out] = ctx.required_text(f"{envelope.name}.{src}", payload.get(src))
            continue
        if src not in payload:
            continue
        if kind == _OPT_TEXT:
            fields[out] = ctx.required_text(f"{envelope.name}.{src}", payload.get(src))
        elif kind == _OPT_LIST:
            fields[out] = list(ctx.text_tuple(f"{envelope.name}.{src}", payload.get(src)))
        elif kind == _OPT_INT:
            fields[out] = ctx.positive_int(f"{envelope.name}.{src}", payload.get(src))
    return fields
