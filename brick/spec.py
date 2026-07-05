"""Brick-owned declarable contract single-source API (axis single-source API, E2/§2 AXIS A).

This is the Brick single-source API for what a builder DECLARES as a valid task —
the WHAT-face of the Brick axis. The clean part already existed on this axis
(``brick/work.py`` ``BrickWork`` + ``parse_required_return_shape``); this module
adds the *declarable* surface that previously had no Brick-axis home and sat in
support files (one of them named for a DIFFERENT axis). It owns:

  * ``BRICK_ROW_ALLOWED_KEYS`` — the admitted Brick-row key-set a plan may carry
    (moved from ``support/operator/primitives.py`` at E2/S9).
  * ``WriteScope`` value object — the Brick-declared write envelope SHAPE
    (``allowed_paths`` / ``forbidden_paths``) + its ``clean`` / ``validate``
    discipline (moved from ``support/connection/agent_adapter.py`` at E2/S9 — a
    Brick-axis value object that had been sitting in a support file named for the
    AGENT axis, an axis leak the design flags). The path-safety RULES (forbidden
    write paths, bare-directory rejection, forbidden segments) are Brick-axis
    property; the few support-mechanic COERCERS they need (deep JSON clean, raw
    credential/session rejection) are INJECTED via ``WriteScopeContext`` so the
    axis never imports support and accept/reject + error text stay byte-identical.
  * ``DERIVED_WORKTREE_WRITE_SCOPE`` — the default worktree write envelope (moved
    from ``support/operator/assembly.py`` at E2/S9).
  * the write-NEED value interpreter (``declared_brick_write_need`` /
    ``validate_brick_row_write_need_for_scope`` + ``SILENT_WRITE_GRANT_REJECTION``)
    — J5 relocated here as the Brick contract-field interpreter (the
    ``requires_brick_write_scope`` marker is a Brick contract field; its bool /
    yes / no value discipline is Brick-axis judgment, moved from
    ``support/operator/plan_validation.py`` at E2/S9).

It re-exports ``BrickWork`` / ``parse_required_return_shape`` so a consumer has a
single Brick import surface. It defines plan-level Brick vocabulary; it authors no
Movement, chooses no route, and judges no success or quality.

AXIS DEPENDENCY DIRECTION (why ``WriteScope.clean`` / ``.validate`` take a context).
The SHAPE + the path-safety RULES (which paths a Brick may declare for write) are
the single-source mirror this module owns. The COERCERS they delegate to — the
deep JSON cleaner and the raw-credential / raw-session text rejector — depend on
the support connection layer's secret-pattern web; the axis must NOT import
support. So ``WriteScope`` runs the Brick-owned structural rules and delegates
those two coercers through an injected ``WriteScopeContext``. The error TEXT every
checker/profile pins is produced verbatim, so accept/reject is byte-for-byte what
the prior ``agent_adapter`` helpers produced.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

# Single Brick import surface (E2/§2 AXIS A): re-export the already-clean Brick
# work facts so a consumer reaches the whole Brick declarable surface through one
# module. These names are re-exports (NOT re-definitions); the single source stays
# brick/work.py + brick/comparison.py.
from brick_protocol.brick.work import (  # noqa: F401  (re-exported for callers)
    BrickWork,
    parse_required_return_shape,
)
from brick_protocol.brick.building import (  # noqa: F401  (re-exported for callers)
    BuildingWork,
)
from brick_protocol.brick.comparison import (  # noqa: F401  (re-exported for callers)
    BrickComparisonFact,
)

# CASTING AUTHORING from the AGENT axis (E2/S1). The Brick verb ``brick()`` partitions
# its trailing ``**kwargs`` into casting dials and projects them to the node-layer
# ``selected_<base>`` bag. Casting is AGENT-axis property, so the verb imports the
# casting kwarg map + bag builder from ``agent/spec.py`` (brick -> agent is acyclic;
# agent/spec.py imports nothing from brick). These are re-imports, not re-definitions.
from brick_protocol.agent.spec import (
    _CASTING_KWARG_BY_NAME,
    _build_casting_bag,
    _expand_llm_alias,
)

if TYPE_CHECKING:
    # ``AgentSpec`` is only a type annotation here (the ``agent=`` field/parameter).
    # Under ``from __future__ import annotations`` (PEP 563) annotations are strings
    # and never evaluated at runtime, so the import stays type-checker-only and adds
    # no runtime brick -> agent coupling beyond the casting helpers above.
    from brick_protocol.agent.spec import AgentSpec


# ---------------------------------------------------------------------------
# BRICK-ROW ALLOWED KEYS (E2/S9). The admitted key-set a declared Brick row may
# carry. Moved from support/operator/primitives.py: the set of keys a builder is
# allowed to DECLARE on a Brick row is Brick-axis property, not support mechanics.
# Members are byte-identical to the prior primitives._BRICK_ROW_ALLOWED_KEYS.
# ---------------------------------------------------------------------------
BRICK_ROW_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "axis",
        "row_ref",
        "brick_work_ref",
        "brick_instance_ref",
        "boundary_ref",
        "work_statement",
        "comparison_rule",
        "required_return_shape",
        # STATIC kind-md how-to body (⑤ instruction-ref delivery). The brick.md
        # ## body — the agent-readable static instruction layer — rides as a Brick-
        # row data column BESIDE required_return_shape so the how-to travels with
        # the shape it describes. It is a Brick-axis property (the instruction the
        # agent reads), carried by support into the prompt at
        # adapter_grant_policy._build_prompt (key ``brick_instruction_body``) and
        # guarded body<->return aligned by check_bricks_spec_completeness.
        "brick_instruction_body",
        # CARRIES-FORWARD SET (the HANDOFF subset of required_return_shape). The
        # kind's carries_forward_fields rides as a Brick-row data column BESIDE
        # required_return_shape so the "쪽지" the next worker needs travels with the
        # shape it subsets. It is a Brick-axis property (the return-shape DATA that
        # declares which fields forward); support READS it off the row to FILTER the
        # carried upstream summary at the walker carry seam, and never judges it.
        # Comma-joined field-list text, parsed by brick.work.parse_carries_forward_fields.
        "carries_forward_fields",
        "source_facts",
        "raw_refs",
        "write_scope",
        # Declarable proof commands support may observe after an Agent return.
        # Brick owns the declared obligation shape; support records only facts.
        "proof_obligations",
        # Non-authoritative capability taxonomy label. This is Brick-owned
        # declaration/support data for the work need (read / probe_write /
        # source_write / artifact_write). It must not choose Movement, target,
        # success, quality, or provider identity.
        "capability_class",
        # EXPLICIT Brick write NEED marker: composition stamps
        # requires_brick_write_scope: true next to write_scope so strict run
        # admission (require_write_need_marker) can demand a DECLARED need instead
        # of inferring it from scope presence. The key is ADMITTED here; its VALUE
        # discipline (bool / yes / no, fail-closed) is owned by
        # ``declared_brick_write_need`` below. The legacy ``write_need`` synonym is
        # RETIRED (L legacy cut, 0610): it is no longer an admitted row key, so a
        # row carrying it fails the unadmitted-key rejection loudly instead of
        # being read or silently ignored.
        "requires_brick_write_scope",
    }
)


# ---------------------------------------------------------------------------
# WORKTREE WRITE-SCOPE DEFAULT (E2/S9). The default write envelope a worktree-
# isolated build derives when a Brick declares a write NEED but no explicit scope.
# Moved from support/operator/assembly.py; byte-identical to the prior literal.
# Consumers must deep-copy before mutating (callers used copy.deepcopy).
# ---------------------------------------------------------------------------
DERIVED_WORKTREE_WRITE_SCOPE: Mapping[str, Any] = {
    "allowed_paths": ["."],
    "forbidden_paths": [".git/**"],
}


def derived_worktree_write_scope() -> dict[str, Any]:
    """Return a fresh deep copy of the default worktree write envelope.

    The prior call site did ``copy.deepcopy(_DERIVED_WORKTREE_WRITE_SCOPE)``; this
    helper preserves that (a mutable, independent copy per caller) so the shared
    default is never aliased into a plan.
    """

    return copy.deepcopy(dict(DERIVED_WORKTREE_WRITE_SCOPE))


# ---------------------------------------------------------------------------
# WriteScope VALUE OBJECT (E2/S9, mirror + axis-leak fix). The Brick-declared
# write envelope SHAPE + clean/validate discipline. Moved from
# support/connection/agent_adapter.py (a support file named for the AGENT axis):
# WriteScope is Brick-axis property — it is the WHAT a Brick is allowed to touch.
#
# The path-safety RULES below are Brick-axis property and live here. The two
# support-mechanic COERCERS (deep JSON clean, raw credential/session rejection)
# are INJECTED via WriteScopeContext so the axis never imports support; passing
# them in keeps accept/reject + error text byte-for-byte identical to the prior
# _clean_write_scope / _validate_write_scope helpers.
# ---------------------------------------------------------------------------
_FORBIDDEN_WRITE_PATH_SEGMENTS: frozenset[str] = frozenset(
    {"auth", "credential", "credentials", "secret", "secrets", "token", "tokens"}
)


class WriteScopeContext(NamedTuple):
    """Injected support COERCERS the Brick WriteScope discipline delegates to.

    The SHAPE + path-safety RULES are Brick-axis property; these two coercers
    depend on the support connection layer's secret-pattern web (and must not be
    pulled into the axis). Passing them in keeps accept/reject + error text
    byte-for-byte identical to the prior ``agent_adapter`` helpers while the
    value object lives single-source here.

      * ``clean_json`` — the deep JSON cleaner (``_clean_json_value``): cleans a
        nested mapping/list/text payload and rejects raw secrets inside it.
      * ``reject_secret_text`` — the raw credential/session text rejector
        (``_reject_secret_text``).
    """

    clean_json: Callable[[str, Any], Any]
    reject_secret_text: Callable[[str, str], None]


def _path_has_forbidden_write_segment(path: str) -> bool:
    segments = [
        segment
        for segment in path.replace("\\", "/").replace(".", "/").replace("-", "/").replace("_", "/").split("/")
        if segment
    ]
    for segment in segments:
        if segment in _FORBIDDEN_WRITE_PATH_SEGMENTS:
            return True
    return False


class WriteScope:
    """Brick-declared write envelope value object (E2/§2 AXIS A).

    ``clean`` normalizes a raw declared ``write_scope`` payload into a plain
    mapping (or ``{}`` for an absent scope); ``validate`` enforces the Brick
    write-envelope shape + path-safety. Both delegate the two support-mechanic
    coercers through the injected ``WriteScopeContext``. The methods are static:
    WriteScope is a namespace for the Brick write-envelope discipline (the scope
    payload itself stays a plain ``Mapping`` threaded verbatim through support),
    so the byte-identical behavior of the prior module-level helpers is preserved.
    """

    SHAPE_KEYS: frozenset[str] = frozenset({"allowed_paths", "forbidden_paths"})

    @staticmethod
    def clean(value: Any, ctx: WriteScopeContext) -> Mapping[str, Any]:
        """Normalize a raw declared write_scope into a clean mapping.

        Byte-identical to the prior ``agent_adapter._clean_write_scope``: ``None``
        -> ``{}``; a non-mapping -> ``TypeError``; otherwise deep-clean via the
        injected JSON cleaner and require the result to be a mapping.
        """

        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("write_scope must be a mapping")
        cleaned = ctx.clean_json("write_scope", value)
        if not isinstance(cleaned, Mapping):
            raise TypeError("write_scope must clean to a mapping")
        return cleaned

    @staticmethod
    def validate(label: str, value: Mapping[str, Any], ctx: WriteScopeContext) -> None:
        """Enforce the Brick write-envelope shape + path-safety.

        Byte-identical to the prior ``agent_adapter._validate_write_scope``:
        ``allowed_paths`` is a non-empty list of non-empty path strings, each
        rejected if it names a forbidden write target or a bare directory;
        ``forbidden_paths`` is a list of non-empty path strings (secret-text +
        bare-dir rejected); ``commit_allowed`` / ``push_allowed`` must never be
        true.
        """

        allowed = value.get("allowed_paths")
        if not isinstance(allowed, list) or not allowed:
            raise ValueError(f"{label}.allowed_paths must be a non-empty list")
        for index, item in enumerate(allowed):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{label}.allowed_paths[{index}] must be non-empty text")
            WriteScope._reject_forbidden_write_path(f"{label}.allowed_paths[{index}]", item, ctx)
            WriteScope._reject_bare_dir_write_path(f"{label}.allowed_paths[{index}]", item)

        forbidden = value.get("forbidden_paths")
        if not isinstance(forbidden, list):
            raise TypeError(f"{label}.forbidden_paths must be a list")
        for index, item in enumerate(forbidden):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{label}.forbidden_paths[{index}] must be non-empty text")
            ctx.reject_secret_text(f"{label}.forbidden_paths[{index}]", item)
            WriteScope._reject_bare_dir_write_path(f"{label}.forbidden_paths[{index}]", item)

        for key in ("commit_allowed", "push_allowed"):
            if value.get(key) is True:
                raise ValueError(f"{label}.{key} must not be true")

    @staticmethod
    def _reject_forbidden_write_path(label: str, value: str, ctx: WriteScopeContext) -> None:
        text = value.strip().replace("\\", "/")
        lowered = text.lower()
        ctx.reject_secret_text(label, text)
        if (
            lowered == ".git"
            or lowered.startswith(".git/")
            or lowered.startswith("/")
            or lowered.startswith("../")
            or "/../" in lowered
            or lowered in {".env", "env"}
            or lowered.endswith((".pem", ".key"))
            or _path_has_forbidden_write_segment(lowered)
        ):
            raise ValueError(f"{label} is not admitted for write_scope")

    @staticmethod
    def _reject_bare_dir_write_path(label: str, value: str) -> None:
        """Fail closed on a bare-directory write_scope entry.

        ``brick/comparison.py:_path_matches_scope`` (the Brick-axis written-vs-scope
        comparison) matches a changed file against an entry via ``fnmatch`` OR
        exact-path equality (``path == pattern.rstrip("/")``). A bare directory with
        no glob char (e.g. ``"support/"``) therefore matches ONLY the literal
        directory entry, never any nested file: it passes construction here but then
        every nested file is RECORDED as ``observed_paths_outside_declared_scope`` at
        comparison time (a recorded fact for the merge-review gate, no longer a
        building HOLD). Reject it at construction so the author fixes the declaration
        instead of producing misleading out-of-scope evidence on every nested file.
        Exact-file entries (``AGENTS.md``, ``brick/work.py``) and glob entries
        (``support/*``, ``support/**``) are unaffected.
        """

        text = value.strip().replace("\\", "/")
        if text.endswith("/") and "*" not in text:
            raise ValueError(
                f"{label} is a bare directory ({value!r}) that matches no nested "
                f"files at write_observation time; use a glob such as "
                f"'{text.rstrip('/')}/*' or '{text.rstrip('/')}/**' instead"
            )


# ---------------------------------------------------------------------------
# WRITE-NEED VALUE INTERPRETER (E2/S9, J5). The ``requires_brick_write_scope``
# marker is a BRICK contract field; its bool / yes / no value discipline + the
# row-level inverse/strict admission rule are Brick-axis judgment, moved from
# support/operator/plan_validation.py. Support re-imports these names (a re-import
# is not a re-definition); accept/reject + error text are byte-identical.
# ---------------------------------------------------------------------------

# SINGLE SOURCE for the strict no-SILENT-write-grant rejection prose: the live
# run admission surfaces (run_building_plan linear admission, the dynamic
# walker/resume admission, and run_building_once single-step admission) must all
# reject with EXACTLY this text, so it lives here once instead of drifting as
# copy-pasted literals across call sites.
SILENT_WRITE_GRANT_REJECTION = (
    "write_scope requires an explicit Brick write NEED declaration "
    "(requires_brick_write_scope: true); silent write grants are not admitted"
)


def declared_brick_write_need(brick_row: Mapping[str, Any]) -> bool | None:
    """Return the Brick row's declared write NEED, or None when not recorded.

    The NEED marker (``requires_brick_write_scope`` -- the ONLY recognized
    spelling; the legacy ``write_need`` synonym is retired and deliberately NOT
    read here, L legacy cut 0610) is OPTIONAL on a declared plan brick row --
    historical records and externally authored plans may omit it, so an absent
    marker returns None (the prior behavior, no inverse-guard rejection). A row
    carrying only the retired ``write_need`` key therefore has NO declared NEED:
    strict run admission rejects its write_scope loudly
    (``SILENT_WRITE_GRANT_REJECTION``) and the row-key whitelist
    (``BRICK_ROW_ALLOWED_KEYS``) rejects the key itself as unadmitted. When the
    canonical marker is present it must be a clean bool or yes/no literal;
    anything else is a malformed declared road and is rejected fail-closed.
    """

    if "requires_brick_write_scope" in brick_row:
        value = brick_row.get("requires_brick_write_scope")
        label = "Brick row requires_brick_write_scope"
    else:
        return None
    if value is True or value is False:
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "yes":
            return True
        if text == "no":
            return False
    raise ValueError(f"{label} must be a bool or yes/no (got {value!r})")


def validate_brick_row_write_need_for_scope(
    brick_row: Mapping[str, Any],
    *,
    require_write_need_marker: bool,
) -> None:
    """Row-level write-NEED admission shared by EVERY live admission surface.

    Inverse guard: a write_scope only exists to serve a Brick's declared write
    NEED. When the Brick row records its NEED (requires_brick_write_scope) and
    that NEED is explicitly NO, a present write_scope is an axis leak -- it would
    let the run-time provider projection open write on a step that declared no
    write NEED (the same leak effective_write forbids). Reject it. The marker is
    OPTIONAL on the declared plan, so a brick row that omits it keeps the prior
    behavior (historical records carry no marker); composition is the
    authoritative layer that records the NEED and rejects the mismatch at
    materialization. A write-needed step carries BOTH the NEED and the
    write_scope, so it is never rejected here.

    STRICT RUN ADMISSION (no SILENT write grant): at the live run admission
    boundary a write_scope is admissible ONLY when the brick row EXPLICITLY
    declares its write NEED. An absent marker is tolerated solely by the
    default (historical read sweep) mode; with the knob on, the NEED must be
    DECLARED, never inferred from scope presence (Agent capability alone must
    never suffice to open workspace write). The strict rejection text is the
    module-level ``SILENT_WRITE_GRANT_REJECTION`` so all admission surfaces
    (plan walker, dynamic walker/resume, run_building_once) reject identically.
    """

    raw_write_scope = brick_row.get("write_scope")
    declared_write_need = declared_brick_write_need(brick_row)
    if declared_write_need is False and raw_write_scope is not None:
        raise ValueError(
            "write_scope present on a read-only Brick: a write_scope requires the "
            "Brick to declare a write NEED (requires_brick_write_scope)"
        )
    if raw_write_scope is None:
        return
    if require_write_need_marker and declared_write_need is not True:
        raise ValueError(SILENT_WRITE_GRANT_REJECTION)


# ---------------------------------------------------------------------------
# ARTIFACT-GROUNDING COMPLETENESS VERDICT (J10, E2/S10). For a Brick return whose
# required shape includes a grounding-bearing field (a review's ``evidence_used``
# / a design's ``evidence_refs``), the question "is the return COMPLETE, given
# that the grounding field must carry an inspected-repository artifact reference?"
# is a BRICK-return completeness judgment. It previously sat inside support
# (plan_validation._comparison_with_artifact_grounding), which downgraded the
# Brick comparison fact's ``observed_match_kind`` to "missing" — a Brick
# completeness verdict made in a support file (the design's "judge-in-support"
# erosion path). The split (design §4 J10):
#   * the FACT — whether the returned grounding field actually carries an
#     inspected-repository artifact reference (``has_grounding``), plus which
#     evidence/grounding fields apply — is computed in SUPPORT (it reads the
#     returned value + the prepared brick_work shape). Support gathers them.
#   * the VERDICT — given that fact, recompute the missing-field set (drop the
#     grounding field when grounded, add it when not), DOWNGRADE the match kind to
#     "missing" when anything is missing, and re-stamp the required/missing/grounding
#     evidence lines — is THIS Brick decision.
# Behavior-identical: the missing-field recomputation, the "missing"-downgrade
# rule, and the evidence-line rewriting reproduce the prior support code verbatim,
# so the produced BrickComparisonFact is byte-for-byte unchanged (pinned by the
# comparison/grounding cases). It authors no Movement and judges no Agent quality;
# it reports whether the Brick RETURN meets its declared grounding-bearing shape.
# ---------------------------------------------------------------------------


class ArtifactGroundingFacts(NamedTuple):
    """Support-computed grounding facts the Brick completeness verdict reads."""

    evidence_field: str
    grounding_field: str
    has_grounding: bool
    required_fields: tuple[str, ...]


def apply_artifact_grounding_completeness(
    comparison: BrickComparisonFact,
    facts: ArtifactGroundingFacts,
) -> BrickComparisonFact:
    """Apply the Brick-return grounding-completeness verdict to a comparison fact.

    Reproduces the prior support ladder verbatim: when the returned grounding
    field carries an inspected-repository artifact reference the grounding field is
    dropped from the missing set, otherwise it is added; the required/missing
    evidence lines are re-stamped and an ``artifact_grounding[_missing]`` line is
    appended; the match kind is downgraded to "missing" iff any field is missing.
    """

    missing_fields = list(comparison.missing_return_fields())
    if facts.has_grounding:
        missing_fields = [
            field_name for field_name in missing_fields if field_name != facts.grounding_field
        ]
    elif facts.grounding_field not in missing_fields:
        missing_fields.append(facts.grounding_field)
    comparison_evidence = _replace_comparison_evidence_fields(
        comparison.comparison_evidence,
        prefix="required_return_fields:",
        fields=facts.required_fields,
    )
    comparison_evidence = _replace_comparison_evidence_fields(
        comparison_evidence,
        prefix="missing_return_fields:",
        fields=tuple(dict.fromkeys(missing_fields)),
    )
    comparison_evidence = (
        *comparison_evidence,
        (
            f"artifact_grounding: {facts.evidence_field} includes inspected repository artifact reference"
            if facts.has_grounding
            else f"artifact_grounding_missing: {facts.evidence_field} lacks inspected repository artifact reference"
        ),
    )
    return BrickComparisonFact.from_parts(
        work_reference=comparison.work_reference,
        comparison_evidence=comparison_evidence,
        observed_match_kind="missing" if missing_fields else comparison.observed_match_kind,
        comparison_rule=comparison.comparison_rule,
        required_return_shape_evidence=comparison.required_return_shape_evidence,
        forbidden_shortcut_evidence=comparison.forbidden_shortcut_evidence,
    )


def _replace_comparison_evidence_fields(
    comparison_evidence: tuple[str, ...],
    *,
    prefix: str,
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    """Replace (or append) the first ``prefix`` evidence line with ``fields``.

    Behavior-identical to the prior support helper: the first line starting with
    ``prefix`` is rewritten to ``"<prefix> <comma-joined fields or 'none'>"`` and
    later duplicates of that prefix are dropped; when no such line exists the new
    line is appended.
    """

    replacement = f"{prefix} " + (", ".join(fields) if fields else "none")
    replaced = False
    lines: list[str] = []
    for line in comparison_evidence:
        if line.startswith(prefix):
            if not replaced:
                lines.append(replacement)
                replaced = True
            continue
        lines.append(line)
    if not replaced:
        lines.append(replacement)
    return tuple(lines)


# ---------------------------------------------------------------------------
# BRICK AUTHORING CONTRACT (E2/S1, moved from support/operator/assembly.py). The
# ``brick()`` verb + its ``BrickSpec`` carrier + the forbidden-kwarg guard are the
# Brick-axis declarable surface: WHAT a builder declares as one node of a task
# (``kind``/``work`` plus the derived/optional fields). Casting authoring is AGENT
# property and is imported from ``agent/spec.py`` (``_build_casting_bag`` /
# ``_CASTING_KWARG_BY_NAME``); the few tiny value-shape COERCERS the verb needs are
# duplicated below (they also stay in assembly.py for the graph wiring) so this
# axis module never imports the support builder. Bodies are byte-identical to the
# prior ``assembly.py`` definitions; only the module home + the casting/coercer
# source change.
# ---------------------------------------------------------------------------
_FORBIDDEN_BRICK_KWARGS = frozenset(
    {
        "node_id",
        "step_template_ref",
        "brick_instance_ref",
        "row_ref",
        "brick_work_ref",
        "step_ref",
        "completion_edge_ref",
        "fan_in_source",
        "fan_in_target",
        "closure_transition_target_policy",
        "node_reroute_budget",
        "required_return_shape",
        "write_scope",
        "target_step_template_ref",
        "comparison_rule",
    }
)


@dataclass(frozen=True, eq=False)
class BrickSpec:
    kind: str
    work: str
    alias: str | None = None
    write: bool = False
    returns: str | None = None
    agent: AgentSpec | None = None
    gates: tuple[Any, ...] = ()
    # Generic per-node casting carry (E2/§6 M15), keyed by ``selected_<base>``;
    # see AgentSpec.casting. The node's own casting overrides the lane's.
    casting: Mapping[str, str] = ()  # type: ignore[assignment]
    source_facts: tuple[str, ...] = ()
    node_write_scope: Mapping[str, Any] | None = None
    proof_obligations: tuple[Mapping[str, Any], ...] = ()


def brick(
    kind: str,
    work: str,
    *,
    llm: str | None = None,
    alias: str | None = None,
    write: bool = False,
    returns: str | None = None,
    agent: AgentSpec | None = None,
    gates: Sequence[Any] = (),
    source_facts: Sequence[str] | None = None,
    node_write_scope: Mapping[str, Any] | None = None,
    proof_obligations: Sequence[Mapping[str, Any]] | None = None,
    **kwargs: Any,
) -> BrickSpec:
    # Partition trailing kwargs into casting dials (adapter/model/effort/... ,
    # generic over CASTING_FIELDS) vs forbidden/unknown. A new dial flows through
    # _CASTING_KWARG_BY_NAME with no signature edit (E2/§6 M15).
    casting_kwargs = {key: value for key, value in kwargs.items() if key in _CASTING_KWARG_BY_NAME}
    leftover = {key: value for key, value in kwargs.items() if key not in _CASTING_KWARG_BY_NAME}
    if leftover:
        forbidden = sorted(key for key in leftover if key in _FORBIDDEN_BRICK_KWARGS)
        if forbidden:
            raise TypeError(
                "brick() derives these fields; do not declare them: "
                + ", ".join(forbidden)
            )
        raise TypeError("brick() got unexpected keyword argument(s): " + ", ".join(sorted(leftover)))
    clean_kind = _bare_token("kind", kind)
    clean_work = _non_empty_text("work", work)
    clean_alias = _optional_bare_token("alias", alias)
    if node_write_scope is not None and not write:
        raise ValueError("node_write_scope requires write=True")
    if isinstance(gates, (str, bytes)) or not isinstance(gates, Sequence):
        raise TypeError("brick() gates must be a sequence")
    if llm is not None and casting_kwargs:
        raise ValueError(
            "brick() llm= cannot be combined with explicit casting keys: "
            + ", ".join(sorted(casting_kwargs))
        )
    casting_kwargs = _expand_llm_alias("brick()", llm, casting_kwargs)
    return BrickSpec(
        kind=clean_kind,
        work=clean_work,
        alias=clean_alias,
        write=bool(write),
        returns=_optional_text(returns),
        agent=agent,
        gates=tuple(gates),
        casting=_build_casting_bag("brick()", casting_kwargs),
        source_facts=tuple(str(item).strip() for item in (source_facts or ()) if str(item).strip()),
        node_write_scope=node_write_scope,
        proof_obligations=_proof_obligations_tuple(proof_obligations),
    )


def _proof_obligations_tuple(
    value: Sequence[Mapping[str, Any]] | None,
) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("brick() proof_obligations must be a sequence")
    obligations: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"proof_obligations[{index}] must be a mapping")
        kind = _optional_text(item.get("kind")) or "command"
        command = _non_empty_text(f"proof_obligations[{index}].command", item.get("command"))
        if kind == "mutation_red":
            obligations.append({"kind": kind, "command": command})
            continue
        if kind != "command":
            raise ValueError(
                f"proof_obligations[{index}].kind must be command or mutation_red"
            )
        expect_rc = item.get("expect_rc", 0)
        if isinstance(expect_rc, bool) or not isinstance(expect_rc, int):
            raise TypeError(f"proof_obligations[{index}].expect_rc must be an integer")
        obligations.append({"command": command, "expect_rc": expect_rc})
    return tuple(obligations)


# ---------------------------------------------------------------------------
# SHARED COERCERS (E2/S1). Tiny value-shape helpers ``brick()`` needs. Per the
# E2/S1 plan they STAY in ``support/operator/assembly.py`` (the graph wiring still
# uses them) AND are duplicated into the axis files that author a spec, so an axis
# module never imports the support builder. Byte-identical to the ``assembly.py``
# definitions.
# ---------------------------------------------------------------------------
def _bare_token(label: str, value: str) -> str:
    text = _non_empty_text(label, value)
    if ":" in text:
        raise ValueError(f"{label} must be a bare token")
    return text


def _optional_bare_token(label: str, value: str | None) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
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
