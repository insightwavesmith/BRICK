"""compose_building Brick plan assembly (P3d concern module).

Assembles a declared Building Plan from a graph/template intent into Brick rows +
declared Link edges/gate refs, collecting CompositionProblems. It validates and
records; it authors no Movement, invents no route, and judges no success or
quality. Crosses to Link only via the canonical MovementFact/gate-ref contracts
through plan_rendering / building_operation_common. It may read closed axis
vocabularies for validation; it does not own those meanings."""

from __future__ import annotations

import difflib
import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import TRANSITION_CONCERN_KINDS
from brick_protocol.link.gate import (
    COO_GATE_REF,
    HUMAN_DISPOSITION_GATE_REFS,
    HUMAN_GATE_REF,
)
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.link.spec import translate_gate_concept
from brick_protocol.support.operator.building_operation_common import (
    COMPACT_LINK_GATE_TOKENS,
    DEFAULT_LINK_GATE_REF,
    REPO_ROOT,
    _clean_text,
    _mapping_value,
    _text_sequence,
)
from brick_protocol.support.operator.primitives import (
    INLINE_TASK_SOURCE_REF,
    INLINE_TASK_STATEMENT_MAX_BYTES,
    NODE_CASTING_FIELDS,
)
from brick_protocol.support.operator.project_declaration import load_project_declaration
from brick_protocol.support.recording.capture import buildings_root_for
from brick_protocol.support.operator.plan_rendering import (
    RETIRED_STEP_TEMPLATE_REFS,
    _clean_selected_adapter_ref,
    _declared_step_from_step_template,
    _is_caller_or_coo_declaration,
    _load_yaml_mapping,
    _load_shape_registry,
    _parse_compact_link_expression,
    _is_verdict_bearing_node,
    _resolve_agent_for_need,
    _resolve_casting_selection,
    _validate_declared_plan_projection,
    render_declared_building_plan,
)
from brick_protocol.support.operator.composition_problem import (
    CompositionError,
    CompositionProblem,
)
from brick_protocol.support.operator.composition_common import (
    ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT,
    _ROUTE_POLICY_PROVENANCE_VALUES,
    _composition_gate_sequence_ref,
    _composition_optional_text,
    _composition_shape_has_field,
    _composition_slug,
    _materializer_step_template_slug,
    _materializer_strip_field,
)
from brick_protocol.support.operator.composition_kinds import (
    _KIND_SYNONYMS,
    _STEP_TEMPLATE_PREFIX,
    _known_kinds,
    _materializer_step_alias,
    _materializer_step_template,
    _unknown_kind_hint,
)
from brick_protocol.support.operator.composition_route_policy import (  # noqa: F401  (facade re-export)
    REROUTE_DEFAULTS_PATH,
    _composition_direct_caller_provenance,
    _composition_node_field_with_provenance_fallback,
    _composition_node_reroute_budgets,
    _composition_resolve_route_policy_provenance,
    _composition_route_policy_provenance,
    _materializer_closure_policy,
    _materializer_constitutional_default_reroute_budget,
    _materializer_preset_closure_policy,
    _materializer_preset_reroute_budgets,
    _materializer_reroute_budget_cascade,
    _materializer_reroute_budgets,
)
from brick_protocol.support.operator.composition_gate_translation import (  # noqa: F401  (facade re-export)
    UNSUPPORTED_MATERIALIZER_TARGET_WORDS,
    _QA_ROLE_NEED,
    _materializer_gate_concept_provenance,
    _materializer_gate_concept_tokens,
    _materializer_human_gate_hold_policy,
    _materializer_profile_gate_translations,
    declared_portfolio_gate_translations,
    stamp_declared_portfolio_closure_gates,
)


GRAPH_CHAIN_TARGET_MARKERS = ("parallel", "fan_in")
# Composition-authorship vocabulary literal for LINEAR plans (single source;
# B4-REPAIR 0611). Stamped by render_declared_step_template_plan below (X1
# dogfood fix, 0610) AND imported by the native-dispatch close seam
# (support/operator/native_dispatch.py), which records a ONE-STEP caller-declared
# linear plan: the declared content (work_statement / agent binding / gate refs)
# is caller-supplied; support only wraps it in the fixed single-step shape, so
# its composition authorship class is the SAME caller/COO-declared linear one
# (execution_path="native-dispatch" already distinguishes the path).
# declaration_packets._composition_mode copies the top-level plan key into
# declaration_provenance; check_building_declaration_integrity gap 3 rejects an
# empty mode. Name-parity with the graph literal compose_building stamps
# ("caller_or_coo_declared_graph_composition").
LINEAR_COMPOSITION_MODE: str = "caller_or_coo_declared_linear_composition"
# GATE-CONCEPT TRANSLATION (operator-decided wiring, 0610): the materializer
# TRANSLATES the preset's DECLARED ``gate_concept_profile`` tokens into live
# ``declared_gate_refs`` on SPECIFIC rows (mechanical; provenance = the PRESET
# declared the label; no profile -> nothing stamped). The token -> ref map is
# the Link plan grammar, single-sourced in link/spec.py
# (``GATE_CONCEPT_TOKEN_GATE_REFS`` over link.gate.DECLARED_GATE_REFS; E2/S3):
# this support materializer IMPORTS the table + the ``translate_gate_concept``
# reader instead of re-stating either. MODE tokens (default-transition /
# fan-in-wait-all / portfolio-policy) have NO gate ref there on purpose: they are
# not Link gates (fan-in-wait-all = declared graph topology requirement,
# portfolio-policy = driver surface).
# PLACEMENT (operator design rule):
#   * strict-evidence -> link-gate:strict on every QA-row transition (a row
#     whose SOURCE step template declares performer_lane_need == reviewer).
#   * coo-review / human-review -> link-gate:coo / link-gate:human on the
#     FINAL transition row only (the Link row whose target is the closure
#     building boundary).
#   * human-review ALSO carries the canonical single-gate hold policy (below):
#     the EXISTING gate_sequence_policy machinery withholds Movement (HOLD,
#     required_disposition_owner=caller-or-coo) until the human disposition
#     fact (route_decision_basis.human_review_refs) exists. The gate never
#     judges quality/success; sufficiency stays computed by link/gate.py.
#     SCOPE (codex review, 0610): the ONLY hold surface ADDED BY THIS
#     TRANSLATION is the human-token policy. A pre-existing AUTHOR-declared
#     gate_sequence_policy in a preset (e.g. brick-protocol-engine-feature-hard's
#     design->work coo HOLD) is untouched and still holds on its own row.
#   * every stamped row ALSO records machine-readable provenance
#     (gate_concept_provenance: tokens + declared_by preset ref) -- recorded
#     ONLY when translation happened, mirroring the budget/closure-policy
#     provenance stamps below; support never invents provenance.
# (translate_gate_concept is imported from link/spec.py above — the Link single
# source over GATE_CONCEPT_TOKEN_GATE_REFS; support re-states neither.)
_CLOSURE_POLICY_REQUIRED_KINDS = (
    "implementation_gap",
    "verification_gap",
)
_CLOSURE_POLICY_TARGET_ACTIONS = ("target", "reroute")
_CLOSURE_POLICY_HOLD_ACTIONS = ("hold",)


def materialize_building_intent(
    intent: Mapping[str, Any],
    *,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Materialize a confirmed task source + selected chain preset.

    The caller/COO declares the task source, preset, write scope, adapter, and
    model. This support helper only expands the already-selected preset into
    declared rows for the existing linear render or graph composition helper.
    """

    if not isinstance(intent, Mapping):
        raise TypeError("intent must be an object")
    repo = Path(repo_root).resolve()
    declared_by = _clean_text("declared_by", intent.get("declared_by", ""))
    if not _is_caller_or_coo_declaration(declared_by):
        raise ValueError("declared_by must record caller / COO declaration")
    # AXIS fail-close (mechanism-vs-policy): the Agent performer's ADAPTER is a
    # human/COO NEED<->CAPABILITY declaration. An OMITTED or BLANK selected_adapter_ref
    # must HARD-FAIL here, once, at the entry -- support does NOT default the adapter
    # (a concrete adapter choice would be support deciding the Agent's performer).
    # NOTE: selected_model_ref is NOT fail-closed: model:default is a SENTINEL meaning
    # "let the already-declared adapter pick its own default model" (see
    # agent_adapter._normalize_selected_model_ref -> spec.default_model_ref), not a
    # concrete model choice, so deferring the model to the declared adapter is allowed.
    raw_selected_adapter_ref = intent.get("selected_adapter_ref", "")
    if not (isinstance(raw_selected_adapter_ref, str) and raw_selected_adapter_ref.strip()):
        raise ValueError(
            "selected_adapter_ref must be declared in the confirmed intent; support "
            "does not default the adapter (Agent adapter is a human/COO NEED-to-CAPABILITY "
            "declaration)"
        )
    selected_adapter_ref = _clean_text("selected_adapter_ref", raw_selected_adapter_ref)
    # PROJECT-0 S3-A (0611): OPTIONAL intent.project_ref ('project:<id>') —
    # staged adoption per project-0-design-0611 §2 step 1. Validated HERE,
    # fail-closed, BEFORE any plan is rendered or run: the ref form goes
    # through buildings_root_for (THE single project_ref -> buildings-root
    # derivation seam; no path logic is duplicated here), and the referenced
    # vessel must exist AND round-trip load_project_declaration — an
    # undeclared / charterless vessel is refused loudly at intake, not
    # discovered later by checkers. When present the ref is stamped on the
    # rendered plan as DATA (a recorded declaration fact, like
    # gate_concept_provenance) — no judgment fields, no Movement semantics;
    # the building's membership stays the PATH (design §1: 소속 = 경로가 1차
    # 사실; building packets gain NO new required field). When ABSENT nothing
    # is stamped and the ref-less project #1 default applies downstream
    # (run_building_intake routes it through the SAME seam) — support never
    # invents a project declaration the caller did not make.
    project_ref = _materializer_project_ref(intent)
    # TASK-BY-TEXT (0611, codex FIX-A): EITHER task_source_ref (file flow) OR
    # task_statement (inline text, human flow), fail-closed. The inline flow
    # writes NO file anywhere: the statement body is carried ON the rendered
    # plan (``task_statement``) and the recorded task_source_ref becomes the
    # INLINE_TASK_SOURCE_REF sentinel token.
    task_source_ref, task_body, inline_statement = _materializer_task_source(intent, repo)
    task_source_hash = hashlib.sha256(task_body.encode("utf-8")).hexdigest()
    chain_preset_ref = _clean_text("chain_preset_ref", intent.get("chain_preset_ref", ""))
    raw_building_id = intent.get("building_id", "")
    if raw_building_id in (None, ""):
        if inline_statement is not None:
            # FIX-IDEMPOTENCY (0611): the inline default id is a STABLE hash of
            # (statement body + chain preset) -- retrying the SAME statement +
            # preset re-derives the SAME building_id, so the second intake
            # collides loudly with the existing declared-plan/evidence root
            # ("declared Building plan already exists") instead of silently
            # duplicating roots. A path-stem slug would collide across
            # DIFFERENT statements (the sentinel token has one stem), so the
            # body itself must feed the id.
            building_id = _materializer_inline_building_id(task_body, chain_preset_ref)
        else:
            building_id = _materializer_default_building_id(task_source_ref, chain_preset_ref)
    else:
        building_id = _clean_text("building_id", raw_building_id)

    registry = _load_shape_registry(repo)
    chain_presets = registry.get("chain_presets", {})
    if not isinstance(chain_presets, Mapping):
        raise ValueError("shape registry chain_presets must be a mapping")
    preset = chain_presets.get(chain_preset_ref)
    if not isinstance(preset, Mapping):
        raise ValueError("chain_preset_ref must be present in the Brick template catalog")
    source_facts = _materializer_source_facts(intent, task_source_ref)
    write_scope = _materializer_write_scope(intent)
    task_summary = _materializer_task_summary(task_body, task_source_ref)
    step_selection_overrides = _materializer_step_selection_overrides(intent)
    rendered = _materializer_graph_plan(
        intent,
        preset,
        registry,
        repo=repo,
        building_id=building_id,
        declared_by=declared_by,
        chain_preset_ref=chain_preset_ref,
        task_summary=task_summary,
        task_source_ref=task_source_ref,
        source_facts=source_facts,
        write_scope=write_scope,
        step_selection_overrides=step_selection_overrides,
    )
    rendered["task_source_hash"] = task_source_hash
    rendered["task_source_hash_algorithm"] = "sha256"
    rendered["task_source_hash_basis"] = _materializer_task_source_hash_basis(inline_statement)
    if inline_statement is not None:
        # The plan IS the carrier: the evidence writer lands this body
        # verbatim as work/task.md and a replay of the persisted plan file
        # reproduces it (no external file to lose).
        rendered["task_statement"] = inline_statement
    if project_ref is not None:
        # PROJECT-0 S3-A: recorded declaration fact only (no judgment).
        rendered["project_ref"] = project_ref
    rendered["materialization_rule"] = "caller_or_coo_declared_task_source_plus_graph_chain_preset"
    return rendered


def inline_task_source_carry(
    task_statement: Any,
    *,
    chain_preset_ref: str = "",
) -> Mapping[str, Any]:
    """Author the INLINE task-source evidence carry for a pre-composed graph.

    H2a (direct-graph intake). ``compose_building`` assembles a ``plan_shape:
    graph`` plan but OMITS the task-source/evidence carry that
    ``materialize_building_intent`` authors on the preset path. When a caller
    runs an AI-composed graph (no preset), the SAME required carry must be
    reattached so the evidence spine is INDISTINGUISHABLE in validity from a
    preset-intake run.

    This helper REUSES the materializer's own authoring primitives -- the
    SINGLE source of the inline body normalization, the sha256 over that body,
    the hash basis token, and the STABLE id derive -- so the carry is identical
    to the inline preset path's, byte for byte, and idempotent: the same
    statement re-derives the same body, hash, and ``default_building_id``. It
    authors NO Movement, target, success, or quality and changes nothing about
    ``materialize_building_intent`` / ``compose_building`` behavior; it only
    EXPOSES the carry the materializer already builds inline so the driver does
    not duplicate (or drift from) it.

    Returns a mapping with the REQUIRED inline carry fields:

    * ``task_source_ref`` = ``INLINE_TASK_SOURCE_REF`` sentinel
    * ``task_statement`` = the normalized body (single trailing newline) -- the
      exact bytes the evidence writer lands as ``work/task.md`` and the source
      for re-hashing at evidence-write time (declaration_packets.py)
    * ``task_source_hash`` = sha256 over that body, ``task_source_hash_algorithm``
      ``sha256``, ``task_source_hash_basis`` the inline basis token
    * ``default_building_id`` = the STABLE inline id derive (sha256 of body +
      preset), so a caller that did not declare its own ``building_id`` gets the
      idempotent default the preset path would have used.

    Fail-closed exactly like the materializer (same single owner): empty /
    whitespace / non-text statement -> reject; a statement over
    ``INLINE_TASK_STATEMENT_MAX_BYTES`` -> reject with the file-flow pointer.
    A declared ``task_source_ref`` is NOT accepted here (this is the inline
    seam only): ``_materializer_task_source`` rejects the EITHER/OR ambiguity.
    """

    chain_preset_text = _clean_text("chain_preset_ref", chain_preset_ref) if chain_preset_ref else ""
    # REUSE the single fail-closed owner of inline-body normalization + the
    # EITHER/OR / empty / size rejects. repo is unused on the inline branch
    # (no file is read), so a bare cwd is a safe placeholder.
    task_source_ref, task_body, inline_statement = _materializer_task_source(
        {"task_statement": task_statement}, Path.cwd()
    )
    if inline_statement is None:  # defensive: the helper is the inline seam only
        raise ValueError("inline_task_source_carry requires a non-empty task_statement")
    return {
        "task_source_ref": task_source_ref,
        "task_statement": inline_statement,
        "task_source_hash": hashlib.sha256(task_body.encode("utf-8")).hexdigest(),
        "task_source_hash_algorithm": "sha256",
        "task_source_hash_basis": _materializer_task_source_hash_basis(inline_statement),
        "default_building_id": _materializer_inline_building_id(task_body, chain_preset_text),
    }


def render_declared_step_template_plan(
    intent: Mapping[str, Any],
    *,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Render declared step-template intent into ordinary BAL rows.

    The caller/COO must declare the selected chain preset or shape, step
    template row, target, and Brick work fields. Chain presets are selection
    candidates in the shape registry; execution still renders to ordinary
    Brick / Agent / Link rows.
    """

    if not isinstance(intent, Mapping):
        raise TypeError("intent must be an object")
    repo = Path(repo_root).resolve()
    # U5/D5: selected_shape_ref is an OPTIONAL tag (parity with compose_building) —
    # omitted/blank is allowed (-> None); a present value is recorded verbatim as the
    # tag below. A present-but-non-string value is a MALFORMED declaration and is
    # rejected (not silently erased), preserving the original _clean_text type contract.
    raw_selected_shape_ref = intent.get("selected_shape_ref")
    if raw_selected_shape_ref is not None and not isinstance(raw_selected_shape_ref, str):
        raise TypeError("selected_shape_ref must be text when provided")
    selected_shape_ref = _composition_optional_text(raw_selected_shape_ref)
    declared_by = _clean_text("declared_by", intent.get("declared_by", ""))
    if not _is_caller_or_coo_declaration(declared_by):
        raise ValueError("declared_by must record caller / COO declaration")
    # U5/D5: selected_shape_ref is now an OPTIONAL recorded tag, not a constraint.
    # The shape membership ValueError was removed (shapes.yaml is non-load-bearing;
    # the loader only extracts shape_refs for a now-dropped set check). The registry
    # is still loaded for step_templates / chain_presets resolution below.
    registry = _load_shape_registry(repo)
    plan_selected_adapter_ref = _clean_selected_adapter_ref(
        "selected_adapter_ref",
        intent.get("selected_adapter_ref", "adapter:local"),
    )
    plan_selected_model_ref = _clean_text(
        "selected_model_ref",
        intent.get("selected_model_ref", "model:default"),
    )

    raw_chain_preset_ref = intent.get("chain_preset_ref", "")
    if not isinstance(raw_chain_preset_ref, str):
        raise TypeError("chain_preset_ref must be text")
    chain_preset_ref = raw_chain_preset_ref.strip()
    if chain_preset_ref:
        chain_presets = registry.get("chain_presets", {})
        preset = chain_presets.get(chain_preset_ref)
        if preset is None:
            raise ValueError("chain_preset_ref must be present in the shape registry")
        # U5/D5: the preset<->caller selected_shape_ref match constraint was removed
        # (shape is now an optional tag, not authority). The chain_preset_ref EXISTENCE
        # check above and the graph requirement below remain enforced.
        if _chain_preset_requires_graph(preset):
            raise ValueError(
                "chain_preset_ref requires explicit graph composition via compose_building"
            )

    raw_steps = intent.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
        raise ValueError("intent.steps must be a non-empty array")
    declared_steps: list[Mapping[str, Any]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise TypeError(f"intent.steps[{index}] must be an object")
        declared_steps.append(
            _declared_step_from_step_template(
                index,
                raw_step,
                registry["step_templates"],
                repo,
                plan_casting={
                    "selected_adapter_ref": plan_selected_adapter_ref,
                    "selected_model_ref": plan_selected_model_ref,
                },
            )
        )

    rendered = render_declared_building_plan(
        {
            "plan_ref": intent.get("plan_ref", ""),
            "building_id": intent.get("building_id", ""),
            "task_source_ref": intent.get("task_source_ref", ""),
            # TASK-BY-TEXT (0611): pass through unchanged; the renderer carries
            # a non-None statement verbatim and validation enforces coupling.
            "task_statement": intent.get("task_statement"),
            "selected_adapter_ref": plan_selected_adapter_ref,
            "selected_model_ref": plan_selected_model_ref,
            "plan_shape": intent.get("plan_shape"),
            "proof_limits": intent.get("proof_limits")
            or [
                "support evidence only",
                "step template expansion renders caller / COO declared rows only",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": intent.get("not_proven")
            or [
                "semantic fitness of selected chain preset or step template",
                "future Building run correctness",
                "future Agent or provider quality",
            ],
            "steps": declared_steps,
        }
    )
    rendered["selected_shape_ref"] = selected_shape_ref
    rendered["declared_by"] = declared_by
    # Composition-origin stamp (X1 dogfood fix, 0610): the LINEAR declared path
    # records its true composition authorship, name-parity with the graph
    # literal compose_building stamps ("caller_or_coo_declared_graph_composition").
    # This function only renders caller/COO-declared step-template plans
    # (declared_by is fail-closed above; graph-requiring presets are rejected
    # above), so every output IS a caller/COO-declared linear composition.
    # declaration_packets._composition_mode reads this top-level key into
    # declaration_provenance; check_building_declaration_integrity gap 3
    # (non-empty) and gap 1 (one-off COO marker) both admit it unchanged --
    # empty/missing modes still reject.
    rendered["composition_mode"] = LINEAR_COMPOSITION_MODE
    if chain_preset_ref:
        rendered["chain_preset_ref"] = chain_preset_ref
    expanded_step_template_refs = [
        step["step_template_ref"]
        for step in rendered.get("steps", [])
        if isinstance(step, Mapping) and step.get("step_template_ref")
    ]
    rendered["step_template_expansion"] = {
        "registry_ref": registry["registry_ref"],
        "selection_rule": "caller_or_coo_declared_only",
        "expansion_rule": "step templates expand only after caller / COO selected chain, shape, and target refs",
        "expanded_step_template_refs": expanded_step_template_refs,
        "expanded_brick_spec_refs": list(
            _composition_brick_spec_refs(registry, expanded_step_template_refs)
        ),
        "expanded_brick_template_refs": list(
            _composition_brick_template_refs(registry, expanded_step_template_refs)
        ),
        "proof_limits": [
            "step template expansion support rendering only",
            "not automatic shape selection",
            "not target inference",
            "not Movement choice",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of selected chain preset or step template",
            "future Building run correctness",
            "future Agent or provider quality",
        ],
    }
    _validate_declared_plan_projection(rendered)
    return rendered


def _composition_brick_template_refs(
    registry: Mapping[str, Any],
    step_template_refs: Sequence[str],
) -> tuple[str, ...]:
    step_templates = registry.get("step_templates", {})
    if not isinstance(step_templates, Mapping):
        return ()
    refs: list[str] = []
    for step_template_ref in step_template_refs:
        step_template = step_templates.get(step_template_ref)
        if not isinstance(step_template, Mapping):
            continue
        raw_refs = step_template.get("brick_template_refs", ())
        if isinstance(raw_refs, Sequence) and not isinstance(raw_refs, (str, bytes)):
            refs.extend(str(ref) for ref in raw_refs if str(ref).strip())
    return tuple(dict.fromkeys(refs))


def _composition_brick_spec_refs(
    registry: Mapping[str, Any],
    step_template_refs: Sequence[str],
) -> tuple[str, ...]:
    step_templates = registry.get("step_templates", {})
    if not isinstance(step_templates, Mapping):
        return ()
    refs: list[str] = []
    for step_template_ref in step_template_refs:
        step_template = step_templates.get(step_template_ref)
        if not isinstance(step_template, Mapping):
            continue
        ref = step_template.get("brick_spec_ref")
        if isinstance(ref, str) and ref.strip():
            refs.append(ref.strip())
    return tuple(dict.fromkeys(refs))


def _materializer_project_ref(intent: Mapping[str, Any]) -> str | None:
    """PROJECT-0 S3-A: resolve + fail-close the OPTIONAL intent.project_ref.

    Returns the declared ``project:<id>`` ref, or None when the intent declares
    none (staged adoption — the ref-less flow keeps today's project #1 default
    downstream). Fail-closed when present, all BEFORE any render or run:

    * malformed ref -> the ValueError raised by ``buildings_root_for`` itself
      (THE single project_ref -> buildings-root derivation seam; this helper
      derives no path of its own);
    * vessel directory absent -> loud reject naming the project-creation verb
      (a vessel is declared first, never invented by intake);
    * vessel present but undeclared / charterless -> the verbatim rejection of
      ``load_project_declaration`` (the S1 single-source validator: missing
      project.json, missing charter README.md, empty direction, ... all speak
      with the loader's own voice).

    The vessel is checked WHERE buildings will actually land: against the
    seam-derived, REPO_ROOT-anchored vessel directory (path is the first-class
    membership fact), not against the caller's repo_root parameter.
    """

    # 'output_root' is a driver PARAMETER, never an intent fact. Without this
    # reject a caller writing output_root INTO the intent mapping would be
    # silently ignored (no code reads that key) and the building would land
    # under project_ref / the default root instead — a silent-swallow the
    # no-silence rule forbids (operator gate finding, 0611).
    if intent.get("output_root") is not None:
        raise ValueError(
            "intent must not carry an 'output_root' key — output_root is a "
            "driver parameter, never an intent fact; declare EITHER "
            "intent.project_ref OR pass output_root to the driver call"
        )
    raw_project_ref = intent.get("project_ref")
    if raw_project_ref is None:
        return None
    if not isinstance(raw_project_ref, str) or not raw_project_ref.strip():
        raise ValueError("project_ref must be non-empty text like 'project:<id>' when declared")
    project_ref = raw_project_ref.strip()
    vessel_buildings_root = buildings_root_for(project_ref)  # form fail-close, THE seam
    vessel_dir = vessel_buildings_root.parent
    project_id = vessel_dir.name
    if not vessel_dir.is_dir():
        raise ValueError(
            f"project_ref {project_ref!r} names no existing vessel: {vessel_dir} "
            "does not exist — declare the project first (project-creation skill / "
            "support.operator.project_creation.create_project); intake never "
            "invents a vessel"
        )
    # Undeclared / charterless vessel -> the S1 loader rejects loudly here,
    # BEFORE any run (not discovered later by checkers).
    load_project_declaration(vessel_dir.parent.parent, project_id)
    return project_ref


def _materializer_task_source(
    intent: Mapping[str, Any],
    repo: Path,
) -> tuple[str, str, str | None]:
    """Resolve the confirmed intent's task source: file ref OR inline statement.

    Returns ``(task_source_ref, task_body, inline_statement)``:

    * file flow (existing): ``task_source_ref`` is the declared safe
      repo-relative existing file; ``task_body`` is its verbatim body;
      ``inline_statement`` is None.
    * inline flow (TASK-BY-TEXT 0611, codex FIX-A): the intent declares
      ``task_statement`` (non-empty text) INSTEAD of ``task_source_ref``; the
      returned ref is the ``INLINE_TASK_SOURCE_REF`` sentinel and
      ``task_body`` == ``inline_statement`` is the statement normalized to a
      single trailing newline (the exact bytes the evidence writer lands as
      work/task.md, so the recorded sha256 is re-derivable from work/task.md).

    Fail-closed: BOTH declared -> reject (two task sources are ambiguous);
    empty/whitespace/non-text statement -> reject; a statement over
    ``INLINE_TASK_STATEMENT_MAX_BYTES`` UTF-8 bytes -> reject with a clear
    pointer to the file flow. NEITHER declared keeps the existing non-empty
    task_source_ref reject. Support never authors or infers the task.
    """

    raw_statement = intent.get("task_statement")
    declared_source_ref = str(intent.get("task_source_ref") or "").strip()
    if raw_statement is None:
        task_source_ref = _clean_text("task_source_ref", intent.get("task_source_ref", ""))
        task_path = _materializer_task_path(repo, task_source_ref)
        return task_source_ref, task_path.read_text(encoding="utf-8"), None
    if not isinstance(raw_statement, str) or not raw_statement.strip():
        raise ValueError("task_statement must be non-empty text")
    if declared_source_ref:
        raise ValueError(
            "declare EITHER task_source_ref OR task_statement, not both "
            "(fail-closed: two task sources are ambiguous)"
        )
    statement_bytes = len(raw_statement.encode("utf-8"))
    if statement_bytes > INLINE_TASK_STATEMENT_MAX_BYTES:
        raise ValueError(
            "task_statement exceeds the inline limit of "
            f"{INLINE_TASK_STATEMENT_MAX_BYTES} UTF-8 bytes (observed "
            f"{statement_bytes}); land the task as a repo file and declare "
            "task_source_ref instead"
        )
    statement_body = raw_statement if raw_statement.endswith("\n") else raw_statement + "\n"
    return INLINE_TASK_SOURCE_REF, statement_body, statement_body


def _materializer_task_source_hash_basis(inline_statement: str | None) -> str:
    if inline_statement is not None:
        return "utf-8 inline task_statement body at materialization time"
    return "utf-8 task_source_ref body at materialization time"


def _materializer_inline_building_id(task_body: str, chain_preset_ref: str) -> str:
    """Stable inline default id: sha256(statement body + preset), not random.

    FIX-IDEMPOTENCY (0611): the same statement + preset retried derives the
    SAME id, so a retry collides loudly with the already-written declared plan
    / Building root instead of duplicating roots. The digest covers the
    NORMALIZED statement body (single trailing newline) and the preset ref,
    NUL-separated so a body/preset boundary shift cannot alias.
    """

    digest = hashlib.sha256(
        f"{task_body}\x00{chain_preset_ref}".encode("utf-8")
    ).hexdigest()[:12]
    preset_slug = _composition_slug(chain_preset_ref.split(":", 1)[-1])
    return f"task-statement-{digest}-{preset_slug}"


def _materializer_task_path(repo: Path, task_source_ref: str) -> Path:
    raw_path = Path(task_source_ref)
    if raw_path.is_absolute() or ".." in raw_path.parts or "://" in task_source_ref:
        raise ValueError("task_source_ref must be a safe repo-relative path")
    task_path = (repo / raw_path).resolve()
    try:
        task_path.relative_to(repo)
    except ValueError as exc:
        raise ValueError("task_source_ref must stay inside the repo") from exc
    if not task_path.is_file():
        raise ValueError(f"task_source_ref declared file does not exist: {task_source_ref}")
    return task_path


def _materializer_default_building_id(task_source_ref: str, chain_preset_ref: str) -> str:
    task_slug = _composition_slug(Path(task_source_ref).stem or task_source_ref)
    preset_tail = chain_preset_ref.split(":", 1)[-1]
    preset_slug = _composition_slug(preset_tail)
    return f"{task_slug}-{preset_slug}"


def _materializer_source_facts(intent: Mapping[str, Any], task_source_ref: str) -> list[str]:
    raw_source_facts = intent.get("source_facts")
    if raw_source_facts is not None:
        return list(_text_sequence("source_facts", raw_source_facts))
    return [task_source_ref]


def _materializer_write_scope(intent: Mapping[str, Any]) -> Mapping[str, Any] | None:
    raw_write_scope = intent.get("write_scope")
    if raw_write_scope is None:
        options = intent.get("options")
        if isinstance(options, Mapping):
            raw_write_scope = options.get("write_scope")
    if raw_write_scope is None:
        return None
    return dict(_mapping_value("write_scope", raw_write_scope))


# The per-template override row admits the override-map KEY (``step_template_ref``)
# plus the node-level ``selected_*`` casting keys. The casting half is NOT
# re-enumerated here: it derives from the single-source ``NODE_CASTING_FIELDS``
# projection (primitives.py, the ``selected_<rest>`` twin of ``CASTING_FIELDS``),
# so a new casting field is admitted as an override with ZERO edit here. Only the
# non-casting map-key ``step_template_ref`` is named locally.
_STEP_SELECTION_OVERRIDE_KEYS = frozenset(
    {"step_template_ref", *NODE_CASTING_FIELDS}
)


def _materializer_step_selection_overrides(
    intent: Mapping[str, Any],
) -> Mapping[str, Mapping[str, Any]]:
    """Read caller-declared per-template provider/model overrides.

    The preferred input shape is a mapping keyed by step_template_ref. The list
    form is also admitted for checker profiles and simple authoring surfaces
    that avoid colon-bearing mapping keys.
    """

    raw = intent.get("step_selection_overrides")
    if raw is None:
        return {}
    overrides: dict[str, Mapping[str, Any]] = {}

    def _store(raw_ref: Any, raw_row: Any, label: str) -> None:
        step_template_ref = _clean_text(f"{label}.step_template_ref", raw_ref)
        row = dict(_mapping_value(label, raw_row))
        extra = sorted(set(row) - _STEP_SELECTION_OVERRIDE_KEYS)
        if extra:
            raise ValueError(
                "step_selection_overrides may declare only step_template_ref, "
                f"selected_adapter_ref, and selected_model_ref; observed {extra}"
            )
        declared_ref = row.get("step_template_ref")
        if declared_ref is not None and _clean_text(
            f"{label}.step_template_ref",
            declared_ref,
        ) != step_template_ref:
            raise ValueError("step_selection_overrides step_template_ref key must match row")
        # The "declare at least one casting dial" guard LOOPS the single-source
        # NODE_CASTING_FIELDS (E2/S6★) instead of naming adapter/model by hand, so a
        # NEW dial (effort) is an admissible override with no edit here. Byte-identical
        # to the prior adapter/model check (those are the first two members).
        if not any(field_name in row for field_name in NODE_CASTING_FIELDS):
            raise ValueError(
                "step_selection_overrides row must declare at least one casting dial: "
                + ", ".join(NODE_CASTING_FIELDS)
            )
        if step_template_ref in overrides:
            raise ValueError(
                "step_selection_overrides must declare at most one row for "
                f"{step_template_ref}"
            )
        overrides[step_template_ref] = {
            key: value for key, value in row.items() if key != "step_template_ref"
        }

    if isinstance(raw, Mapping):
        for raw_ref, raw_row in raw.items():
            _store(raw_ref, raw_row, f"step_selection_overrides.{raw_ref}")
        return overrides
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for index, raw_row in enumerate(raw):
            row = _mapping_value(f"step_selection_overrides[{index}]", raw_row)
            _store(
                row.get("step_template_ref"),
                row,
                f"step_selection_overrides[{index}]",
            )
        return overrides
    raise ValueError("step_selection_overrides must be a mapping or an array")


def _materializer_reject_unused_step_selection_overrides(
    steps: Sequence[Mapping[str, Any]],
    overrides: Mapping[str, Mapping[str, Any]],
) -> None:
    if not overrides:
        return
    declared_step_refs = {
        _clean_text(
            "chain preset step_template_ref",
            step.get("step_template_ref", ""),
        )
        for step in steps
        if isinstance(step, Mapping)
    }
    missing = sorted(set(overrides) - declared_step_refs)
    if missing:
        raise ValueError(
            "step_selection_overrides references step_template_ref not in selected "
            f"preset: {missing}"
        )


def _materializer_preset_step_with_selection_override(
    raw_preset_step: Mapping[str, Any],
    step_template_ref: str,
    overrides: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    override = overrides.get(step_template_ref)
    if not override:
        return raw_preset_step
    merged = dict(raw_preset_step)
    # Merge EVERY overridden casting dial generically (E2/S6★): loop the single-source
    # NODE_CASTING_FIELDS rather than naming adapter/model, so a NEW dial (effort)
    # merges onto the preset step with no edit. Byte-identical for adapter/model.
    for key in NODE_CASTING_FIELDS:
        if key in override:
            merged[key] = override[key]
    return merged


def _materializer_task_summary(task_body: str, task_source_ref: str) -> str:
    for heading in ("## First-Line Contract", "## Objective", "## Desired Output"):
        section = _materializer_markdown_section(task_body, heading)
        if section:
            return section
    first_lines = [line.strip() for line in task_body.splitlines() if line.strip()]
    if first_lines:
        return first_lines[0]
    return f"Declared task source {task_source_ref}"


def _materializer_markdown_section(task_body: str, heading: str) -> str:
    lines = task_body.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading) + 1
    except StopIteration:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped and not stripped.startswith("```"):
            collected.append(stripped)
    return " ".join(collected).strip()[:240]


from brick_protocol.support.operator.composition_graph_emit import (  # noqa: F401  (facade re-export)
    _materializer_apply_route_decision_basis,
    _materializer_declared_graph_declaration,
    _materializer_declared_graph_topology,
    _materializer_gate_sequence_refs_for_edge,
    _materializer_graph_declaration,
    _materializer_graph_edge,
    _materializer_graph_fan_out_index,
    _materializer_graph_node,
    _materializer_graph_plan,
    _materializer_graph_required_return_shape,
    _materializer_link_row_has_gate_ref,
    _materializer_route_decision_basis,
    _materializer_sequential_graph_declaration,
    _materializer_topology_node_handle,
    _materializer_topology_string_list,
)


def compose_building(
    nodes: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    selected_shape_ref: str = "",  # U5/D5: optional tag (parity with the linear path); blank -> no shape tag
    declared_by: str,
    groups: Sequence[Mapping[str, Any]] = (),
    chain_preset_ref: str = "",
    plan_ref: str = "",
    building_id: str = "",
    selected_adapter_ref: str = "adapter:local",
    selected_model_ref: str = "model:default",
    transition_concern_adoption: str = "",
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Assemble a caller/COO-declared graph Building Plan from node choices.

    This is support mechanics only. The caller/COO declares the selected shape,
    each node's step template / Brick fields, and each Link edge / gate token.
    The helper lays those declarations out as a Brick-owned ``plan_shape:
    graph`` plan, then reuses the existing graph and Link validators.
    """

    repo = Path(repo_root).resolve()
    registry = _load_shape_registry(repo)
    problems: list[CompositionProblem] = []

    # U5/D5: selected_shape_ref is now an OPTIONAL recorded tag, not a constraint
    # (parity with the linear path). The composition-level shape membership gate
    # was removed (shapes.yaml is non-load-bearing; graph structure comes from the
    # nodes/edges arguments). shape_ref is still extracted here for the plan tag
    # and for passing to the chain-preset helper. The registry stays loaded for
    # step_templates / chain_presets resolution. A present-but-non-string shape is a
    # MALFORMED declaration: fail closed (parity with the linear renderer's TypeError)
    # rather than silently erase it to a null tag.
    if selected_shape_ref is not None and not isinstance(selected_shape_ref, str):
        problems.append(
            CompositionProblem(
                "bad_declaration",
                "__composition__",
                "selected_shape_ref must be text when provided",
            )
        )
    shape_ref = _composition_optional_text(selected_shape_ref)
    declared_by_text = _composition_optional_text(declared_by)
    if not declared_by_text or not _is_caller_or_coo_declaration(declared_by_text):
        problems.append(
            CompositionProblem(
                "bad_declaration",
                "__composition__",
                "selection_rule: caller_or_coo_declared_only",
            )
        )
    plan_selected_adapter_ref = _clean_selected_adapter_ref(
        "selected_adapter_ref",
        selected_adapter_ref,
    )
    plan_selected_model_ref = _clean_text(
        "selected_model_ref",
        selected_model_ref,
    )

    (
        selected_chain_preset_ref,
        canonical_chain_preset_ref,
        chain_preset,
    ) = _composition_chain_preset(
        registry,
        chain_preset_ref,
        problems=problems,
    )

    node_items = _composition_node_items(nodes)
    if not node_items:
        problems.append(
            CompositionProblem(
                "empty_composition",
                "__composition__",
                "composition must declare at least one node",
            )
        )

    admitted_agent_refs = _composition_agent_object_refs(repo)
    step_templates = registry["step_templates"]
    node_records: list[dict[str, Any]] = []
    step_by_endpoint: dict[str, str] = {}
    brick_by_step: dict[str, str] = {}
    seen_node_ids: set[str] = set()
    seen_brick_refs: set[str] = set()
    for index, raw_node in enumerate(node_items):
        label = f"nodes[{index}]"
        if not isinstance(raw_node, Mapping):
            problems.append(
                CompositionProblem(
                    "missing_brick_fields",
                    label,
                    "node declaration must be an object",
                )
            )
            continue
        node_id = _composition_node_id(index, raw_node)
        # U5/D5: node-level shape_ref membership gate removed (shape is a pure
        # optional tag now; it never drove graph structure). node shape_ref is not
        # emitted into the plan, so the extraction is dropped as well.
        if node_id in seen_node_ids:
            problems.append(
                CompositionProblem(
                    "duplicate_brick_id",
                    node_id,
                    "node_id must be unique",
                )
            )
        seen_node_ids.add(node_id)
        step_template_ref = _composition_optional_text(raw_node.get("step_template_ref"))
        step_template = (
            step_templates.get(step_template_ref)
            if step_template_ref is not None
            else None
        )
        brick_row = _composition_brick_row(
            index, raw_node, node_id, problems, step_template
        )
        brick_ref = str(brick_row.get("brick_instance_ref") or "")
        if brick_ref in seen_brick_refs:
            problems.append(
                CompositionProblem(
                    "duplicate_brick_id",
                    node_id,
                    f"brick_instance_ref appears more than once: {brick_ref}",
                )
            )
        if brick_ref:
            seen_brick_refs.add(brick_ref)

        if step_template is None:
            if step_template_ref in RETIRED_STEP_TEMPLATE_REFS:
                # WAVE-B rename (0610): the retired step-template name rejects
                # LOUDLY on the graph path too, naming the canonical
                # replacement (parity with the linear + chain-preset paths);
                # it never falls through to the generic not-in-catalog error.
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        f"step_template_ref {step_template_ref} is retired: "
                        f"use {RETIRED_STEP_TEMPLATE_REFS[step_template_ref]}",
                    )
                )
            else:
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        f"step_template_ref {step_template_ref} must resolve in the "
                        f"Brick template catalog"
                        f"{_unknown_kind_hint(step_template_ref, registry)}",
                    )
                )
            agent_object_ref = _composition_optional_text(raw_node.get("agent_object_ref")) or ""
        else:
            _validate_composition_brick_spec_ref(raw_node, step_template, node_id, problems)
            # The template's agent_object_ref is the NEED<->CAPABILITY match
            # (default_agent hint applied at registry build). A node MAY override
            # it, but only with an agent that itself satisfies this kind's NEED
            # (role_need/write_need carried on the registry row); an override that
            # violates the NEED is rejected. No override = the matched default.
            agent_object_ref = step_template["agent_object_ref"]
            declared_agent_ref = _composition_optional_text(raw_node.get("agent_object_ref"))
            if declared_agent_ref and declared_agent_ref != agent_object_ref:
                if step_template.get("step_template_ref") == "building-step-template:development":
                    # development is CTO-only; role_need=leader has 5 candidates so a
                    # same-NEED override would divert the CTO assignment. Block it
                    # (parity with the linear path; codex U2-4 P2); keep cto-lead default.
                    problems.append(
                        CompositionProblem(
                            "unknown_step_template/agent",
                            node_id,
                            "development is CTO-only; agent override not allowed",
                        )
                    )
                else:
                    role_need = step_template.get("role_need")
                    write_need = step_template.get("write_need")
                    if not isinstance(role_need, str) or not role_need:
                        problems.append(
                            CompositionProblem(
                                "unknown_step_template/agent",
                                node_id,
                                "step template is missing role_need; cannot validate agent override",
                            )
                        )
                    else:
                        try:
                            agent_object_ref = _resolve_agent_for_need(
                                repo,
                                role_need,
                                bool(write_need),
                                declared_override=declared_agent_ref,
                            )
                        except ValueError as exc:
                            problems.append(
                                CompositionProblem(
                                    "unknown_step_template/agent",
                                    node_id,
                                    f"agent_object_ref override rejected: {exc}",
                                )
                            )
        if agent_object_ref and agent_object_ref not in admitted_agent_refs:
            problems.append(
                CompositionProblem(
                    "unknown_step_template/agent",
                    node_id,
                    f"agent_object_ref is not admitted: {agent_object_ref}",
                )
            )
        # Every casting dial's resolved ``selected_<base>`` value, keyed by the
        # SAME ``NODE_CASTING_FIELDS`` projection the node carries. Default to None
        # (absent agent / resolution error) for each field so the node always
        # carries the full key set. E2/S6★: the OUTPUT is generic over
        # CASTING_FIELDS just like the resolver INPUT, so a new dial (effort) is
        # stamped here with no per-dial code -- selected_reasoning_effort_ref now
        # rides along the same way selected_adapter_ref/selected_model_ref do.
        step_casting_selection: dict[str, str | None] = {
            field_name: None for field_name in NODE_CASTING_FIELDS
        }
        if agent_object_ref and agent_object_ref in admitted_agent_refs:
            try:
                step_casting_selection = _resolve_casting_selection(
                    repo,
                    raw_step=raw_node,
                    agent_object_ref=agent_object_ref,
                    plan_casting={
                        "selected_adapter_ref": plan_selected_adapter_ref,
                        "selected_model_ref": plan_selected_model_ref,
                    },
                    label=node_id,
                    is_verdict_bearing_node=_is_verdict_bearing_node(
                        raw_node,
                        step_template=step_template,
                    ),
                )
            except ValueError as exc:
                problems.append(
                    CompositionProblem(
                        "unknown_step_template/agent",
                        node_id,
                        str(exc),
                    )
                )

        node_record = {
            "node_id": node_id,
            "step_ref": _composition_step_ref(raw_node, node_id),
            "step_template_ref": step_template_ref or "",
            "brick_ref": brick_ref,
            "brick_row": brick_row,
            "agent_object_ref": agent_object_ref,
            "raw": raw_node,
            "requires_review_gate": bool(
                raw_node.get("requires_review_gate")
                or raw_node.get("review_gate_required")
            ),
            "completion_edge_ref": _composition_optional_text(
                raw_node.get("completion_edge_ref")
            ),
            "node_reroute_budget": raw_node.get("node_reroute_budget", raw_node.get("reroute_budget")),
            # FAIL-CLOSED ripple (Smith ruling): a route-policy value declared
            # DIRECTLY on the node passed to compose_building (no provenance) IS a
            # per-Building HUMAN declaration by the caller/COO -- stamp "per-building"
            # EXPLICITLY here so the value carries its origin. The resolver no longer
            # auto-labels absent provenance; absent must be made explicit at this
            # legitimate direct-caller intake, never defaulted inside the resolver.
            "node_reroute_budget_provenance": _composition_direct_caller_provenance(
                value=raw_node.get("node_reroute_budget", raw_node.get("reroute_budget")),
                provenance=raw_node.get("node_reroute_budget_provenance"),
            ),
            "closure_transition_target_policy": raw_node.get(
                "closure_transition_target_policy"
            ),
            "closure_transition_target_policy_provenance": _composition_direct_caller_provenance(
                value=raw_node.get("closure_transition_target_policy"),
                provenance=raw_node.get("closure_transition_target_policy_provenance"),
            ),
            # Stamp EVERY resolved casting dial generically (E2/S6★): loop the
            # single-source NODE_CASTING_FIELDS projection rather than naming
            # selected_adapter_ref/selected_model_ref by hand, so a new casting
            # dial (effort) lands on the node with no edit here.
            **{
                field_name: step_casting_selection.get(field_name)
                for field_name in NODE_CASTING_FIELDS
            },
        }
        node_records.append(node_record)
        for endpoint in (node_id, node_record["step_ref"], brick_ref):
            if endpoint:
                step_by_endpoint[endpoint] = node_record["step_ref"]
        if brick_ref:
            brick_by_step[node_record["step_ref"]] = brick_ref

    edge_records: list[dict[str, Any]] = []
    outgoing_by_step: dict[str, list[str]] = {}
    review_gate_seen_by_step: dict[str, bool] = {}
    for index, raw_edge in enumerate(edges if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)) else ()):
        label = f"edges[{index}]"
        if not isinstance(raw_edge, Mapping):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    label,
                    "edge declaration must be an object",
                )
            )
            continue
        raw_source = _composition_endpoint(raw_edge, "source")
        raw_target = _composition_endpoint(raw_edge, "target")
        source_step = step_by_endpoint.get(raw_source or "")
        target_step = step_by_endpoint.get(raw_target or "")
        node_id = source_step or raw_source or label
        if source_step is None:
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    node_id,
                    f"edge source does not resolve: {raw_source or '(blank)'}",
                )
            )
        if target_step is None and not _composition_terminal_target(raw_target):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    node_id,
                    f"edge target does not resolve: {raw_target or '(blank)'}",
                )
            )
        if source_step and target_step and source_step == target_step:
            problems.append(
                CompositionProblem(
                    "cycle/self_loop",
                    source_step,
                    "edge source and target resolve to the same node",
                )
            )

        target_ref = (
            brick_by_step[target_step]
            if target_step is not None
            else _composition_optional_text(raw_target) or ""
        )
        declared_gate_refs = _composition_declared_gate_refs(
            index,
            raw_edge,
            target_ref,
            source_step or node_id,
            problems,
        )
        movement = _composition_edge_movement(index, raw_edge, problems)
        if source_step:
            outgoing_by_step.setdefault(source_step, []).append(
                _composition_edge_ref(index, raw_edge, source_step, target_step or target_ref)
            )
            if any(ref in HUMAN_DISPOSITION_GATE_REFS for ref in declared_gate_refs):
                review_gate_seen_by_step[source_step] = True
        edge_records.append(
            {
                "edge_ref": _composition_edge_ref(index, raw_edge, source_step or label, target_step or target_ref),
                "source_step_ref": source_step or "",
                "target_step_ref": target_step or "",
                "target_ref": target_ref,
                "movement": movement,
                "declared_gate_refs": declared_gate_refs,
                "raw": raw_edge,
            }
        )

    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        problems.append(
            CompositionProblem(
                "unknown_endpoint",
                "__composition__",
                "edges must be an array of declared Link edges",
            )
        )

    for node_record in node_records:
        step_ref = node_record["step_ref"]
        if not outgoing_by_step.get(step_ref):
            problems.append(
                CompositionProblem(
                    "unknown_endpoint",
                    step_ref,
                    "node must declare at least one outgoing Link edge or terminal boundary edge",
                )
            )
        if node_record["requires_review_gate"] and not review_gate_seen_by_step.get(step_ref):
            problems.append(
                CompositionProblem(
                    "missing_review_gate",
                    step_ref,
                    "node declares requires_review_gate but no outgoing human/coo gate",
                )
            )

    if groups and (
        not isinstance(groups, Sequence) or isinstance(groups, (str, bytes))
    ):
        problems.append(
            CompositionProblem(
                "execution_order/groups coherence",
                "__composition__",
                "groups must be an array of declared graph groups",
            )
        )

    if chain_preset is not None:
        expected_step_template_refs = _chain_preset_step_template_refs(chain_preset)
        observed_step_template_refs = [
            record["step_template_ref"]
            for record in node_records
            if record.get("step_template_ref")
        ]
        if expected_step_template_refs and Counter(
            expected_step_template_refs
        ) != Counter(observed_step_template_refs):
            problems.append(
                CompositionProblem(
                    "chain_preset_step_mismatch",
                    selected_chain_preset_ref or "__composition__",
                    "declared graph nodes must match the selected chain preset step templates",
                )
            )
        if _chain_preset_requires_fan_in_groups(chain_preset):
            group_roles = (
                {
                    str(group.get("group_role", "")).strip()
                    for group in groups
                    if isinstance(group, Mapping)
                }
                if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes))
                else set()
            )
            missing_roles = [role for role in ("fan_out", "fan_in") if role not in group_roles]
            if missing_roles:
                problems.append(
                    CompositionProblem(
                        "chain_preset_graph_groups_missing",
                        selected_chain_preset_ref or "__composition__",
                        "graph chain preset requires declared fan_out and fan_in groups",
                    )
                )
            problems.extend(
                _composition_gate_sequence_policy_profile_problems(
                    chain_preset=chain_preset,
                    node_records=node_records,
                    edge_records=edge_records,
                )
            )
            edge_records = list(
                _composition_edge_records_with_gate_sequence_policy(
                    chain_preset=chain_preset,
                    node_records=node_records,
                    edge_records=edge_records,
                )
            )

    for node_record in node_records:
        step_ref = node_record["step_ref"]
        if len(outgoing_by_step.get(step_ref, [])) > 1 and not node_record.get(
            "completion_edge_ref"
        ):
            problems.append(
                CompositionProblem(
                    "missing_completion_edge_ref",
                    step_ref,
                    "fan-out nodes must declare completion_edge_ref; support must not choose the first outgoing edge",
                )
            )

    # P1-1 fan-in required_return_shape is AUTHOR-REQUIRED for fan-in SOURCES only.
    # Phase 1 split the two halves that used to be lumped together here:
    #   * fan-in SOURCE (QA lanes): the U2-3 omit-default (kind PRIMARY return_template
    #     shape) is still WRONG for a source, because a fan-in QA source must NOT carry
    #     transition_concern_evidence yet its LINEAR-position return.yaml legitimately
    #     declares it. So a SOURCE that omits required_return_shape still yields a clear
    #     missing_brick_fields problem here (authoring time) -- behavior UNCHANGED.
    #   * fan-in TARGET (closure): RESOLVED. The closure Brick return.yaml now DECLARES
    #     transition_concern_evidence in its primary required_return_shape, so the
    #     closure target derives its shape from the registry default (the brick
    #     return.yaml) exactly like the linear path -- support no longer requires the
    #     author to re-state it and no longer hardcodes it. The downstream
    #     closure_transition_concern_shape_missing check (in
    #     _composition_hard_graph_contract_problems) then validates that the
    #     registry-derived target shape actually carries transition_concern_evidence,
    #     reading the brick (not a deleted support literal).
    # Non-fan-in nodes keep the U2-3 omit-default.
    fan_in_shape_omitted_steps: set[str] = set()
    if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes)) and groups:
        records_by_step = {str(record.get("step_ref")): record for record in node_records}
        fan_in_targets = _composition_fan_in_target_steps(edge_records, groups)
        fan_in_source_steps: list[str] = []
        for _target_step_ref, source_step_refs in fan_in_targets.items():
            fan_in_source_steps.extend(source_step_refs)
        for step_ref in dict.fromkeys(fan_in_source_steps):
            record = records_by_step.get(step_ref)
            if record is None:
                continue
            if not _composition_author_required_return_shape(record):
                fan_in_shape_omitted_steps.add(step_ref)
                problems.append(
                    CompositionProblem(
                        "missing_brick_fields",
                        record.get("node_id") or step_ref,
                        "missing Brick field(s): required_return_shape (fan-in lane)",
                    )
                )

    if chain_preset is not None and _chain_preset_requires_fan_in_groups(chain_preset):
        problems.extend(
            _composition_hard_graph_contract_problems(
                node_records=node_records,
                edge_records=edge_records,
                groups=groups,
                # A fan-in member that OMITTED required_return_shape already has a
                # clear missing_brick_fields(fan-in lane) problem; suppress the
                # confusing template-default-driven transition-concern codes for it
                # so the author sees the clear message INSTEAD (design CHANGE 3).
                shape_omitted_steps=fan_in_shape_omitted_steps,
            )
        )

    if problems:
        raise CompositionError(problems)

    brick_steps: list[Mapping[str, Any]] = []
    for node_record in node_records:
        step_ref = node_record["step_ref"]
        completion_edge_ref = node_record["completion_edge_ref"] or outgoing_by_step[step_ref][0]
        brick_step: dict[str, Any] = {
            "step_ref": step_ref,
            "completion_edge_ref": completion_edge_ref,
            "rows": [
                node_record["brick_row"],
                {
                    "axis": "Agent",
                    "row_ref": f"agent-row:{step_ref}",
                    "agent_object_ref": node_record["agent_object_ref"],
                },
            ],
        }
        # Stamp EVERY resolved casting dial onto the brick_step generically
        # (E2/S6★): loop the single-source ``NODE_CASTING_FIELDS`` projection the
        # node_record already carries rather than hand-naming
        # selected_adapter_ref/selected_model_ref. A None value defers to the
        # plan-level casting (omitted from the step), byte-identical to the prior
        # two-field emission; a NEW casting dial (effort) now reaches brick_steps
        # with no edit here, so the assemble + compose paths agree.
        for field_name in NODE_CASTING_FIELDS:
            value = node_record.get(field_name)
            if value is not None:
                brick_step[field_name] = _clean_text(
                    f"{step_ref}.{field_name}",
                    value,
                )
        if node_record.get("step_template_ref"):
            brick_step["step_template_ref"] = _clean_text(
                f"{step_ref}.step_template_ref",
                node_record["step_template_ref"],
            )
        brick_steps.append(brick_step)

    link_edges = [
        _composition_link_edge(record)
        for record in edge_records
    ]
    expanded_step_template_refs = [
        record["step_template_ref"]
        for record in node_records
        if record.get("step_template_ref")
    ]
    plan: dict[str, Any] = {
        "plan_ref": plan_ref.strip() if plan_ref else "building-plan:composed-graph",
        "owner_axis": "Brick",
        "building_id": building_id.strip() if building_id else "composed-graph",
        "plan_shape": "graph",
        "composition_mode": "caller_or_coo_declared_graph_composition",
        "selected_adapter_ref": plan_selected_adapter_ref,
        "selected_model_ref": plan_selected_model_ref,
        "selected_shape_ref": shape_ref,
        "declared_by": declared_by_text,
        "selection_rule": "caller_or_coo_declared_only",
        "proof_limits": [
            "support evidence only",
            "compose_building assembles caller / COO declared node and edge choices only",
            "not automatic shape selection",
            "not automatic Agent selection",
            "not automatic gate selection",
            "not support-chosen target",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of selected shape",
            "future Building run correctness",
            "future Agent or provider quality",
        ],
        "execution_order": [record["step_ref"] for record in node_records],
        "brick_steps": brick_steps,
        "link_edges": link_edges,
        "preset_expansion": {
            "selected_shape_ref": shape_ref,
            "expanded_step_template_refs": expanded_step_template_refs,
            "expanded_brick_spec_refs": list(
                _composition_brick_spec_refs(registry, expanded_step_template_refs)
            ),
            "expanded_brick_template_refs": list(
                _composition_brick_template_refs(registry, expanded_step_template_refs)
            ),
            "agent_object_refs": [
                record["agent_object_ref"]
                for record in node_records
                if record.get("agent_object_ref")
            ],
            "selection_rule": "caller_or_coo_declared_only",
            "proof_limits": [
                "support records caller / COO declared graph composition only",
                "not automatic preset selection",
                "not automatic shape selection",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "semantic fitness of selected shape",
                "selected preset ref was not declared unless separately present",
            ],
        },
    }
    if selected_chain_preset_ref:
        plan["chain_preset_ref"] = selected_chain_preset_ref
        plan["preset_expansion"]["chain_preset_ref"] = selected_chain_preset_ref
        plan["preset_expansion"]["canonical_chain_preset_ref"] = canonical_chain_preset_ref
        if canonical_chain_preset_ref != selected_chain_preset_ref:
            plan["preset_expansion"]["compat_chain_preset_ref"] = selected_chain_preset_ref
        if chain_preset is not None:
            plan["preset_expansion"]["chain_preset_requires_graph"] = (
                _chain_preset_requires_graph(chain_preset)
            )
    if groups:
        plan["groups"] = [dict(group) for group in groups]
    node_reroute_budgets = _composition_node_reroute_budgets(node_records)
    if node_reroute_budgets:
        plan["node_reroute_budgets"] = node_reroute_budgets
    route_policy_provenance = _composition_route_policy_provenance(node_records)
    if route_policy_provenance:
        plan["route_policy_provenance"] = route_policy_provenance
    if transition_concern_adoption:
        plan["transition_concern_adoption"] = transition_concern_adoption

    post_problems = _composition_validator_problems(plan, repo)
    if post_problems:
        raise CompositionError(post_problems)
    return plan


def _composition_chain_preset(
    registry: Mapping[str, Any],
    raw_chain_preset_ref: Any,
    *,
    problems: list[CompositionProblem],
) -> tuple[str, str, Mapping[str, Any] | None]:
    chain_preset_ref = _composition_optional_text(raw_chain_preset_ref)
    if raw_chain_preset_ref not in (None, "") and chain_preset_ref is None:
        problems.append(
            CompositionProblem(
                "unknown_chain_preset",
                "__composition__",
                "chain_preset_ref must be non-empty text when supplied",
            )
        )
        return "", "", None
    if not chain_preset_ref:
        return "", "", None
    chain_presets = registry.get("chain_presets", {})
    chain_preset_aliases = registry.get("chain_preset_aliases", {})
    if not isinstance(chain_presets, Mapping):
        return chain_preset_ref, chain_preset_ref, None
    preset = chain_presets.get(chain_preset_ref)
    if not isinstance(preset, Mapping):
        problems.append(
            CompositionProblem(
                "unknown_chain_preset",
                chain_preset_ref,
                "chain_preset_ref must be present in the Brick template catalog",
            )
        )
        return chain_preset_ref, chain_preset_ref, None
    canonical_ref = chain_preset_ref
    if isinstance(chain_preset_aliases, Mapping):
        alias_target = chain_preset_aliases.get(chain_preset_ref)
        if isinstance(alias_target, str) and alias_target.strip():
            canonical_ref = alias_target.strip()
    # U5/D5: the preset<->caller selected_shape_ref match constraint was removed
    # (shape is now an optional tag, not authority; parity with the linear path).
    # Preset existence, alias/canonical resolution, and the graph requirement
    # (enforced by the caller via _chain_preset_requires_graph) all remain.
    return chain_preset_ref, canonical_ref, preset


def _chain_preset_requires_graph(preset: Mapping[str, Any]) -> bool:
    if "node_reroute_budgets" in preset:
        return True
    return _chain_preset_requires_fan_in_groups(preset)


def _chain_preset_requires_fan_in_groups(preset: Mapping[str, Any]) -> bool:
    # E1 FULL-LEGO: an explicit graph_topology that DECLARES fan_in_groups needs
    # the same graph-group + hard-graph-contract validation the positional
    # parallel/fan-in markers trigger (the emitted plan must pass the SAME
    # compose_building validators). Absent the key -> unchanged.
    topology = preset.get("graph_topology")
    if isinstance(topology, Mapping):
        fan_in_groups = topology.get("fan_in_groups")
        if (
            isinstance(fan_in_groups, Sequence)
            and not isinstance(fan_in_groups, (str, bytes))
            and fan_in_groups
        ):
            return True
    for raw_step in _chain_preset_steps(preset):
        target_word = str(raw_step.get("target_word", "")).strip().lower()
        if any(marker in target_word for marker in GRAPH_CHAIN_TARGET_MARKERS):
            return True
    gate_concepts = preset.get("gate_concept_profile", ())
    if isinstance(gate_concepts, Sequence) and not isinstance(gate_concepts, (str, bytes)):
        return any("fan-in" in str(item).lower() for item in gate_concepts)
    return False


def _chain_preset_step_template_refs(preset: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for raw_step in _chain_preset_steps(preset):
        ref = raw_step.get("step_template_ref")
        if isinstance(ref, str) and ref.strip():
            refs.append(ref.strip())
    return tuple(refs)


def _validate_declared_brick_spec_ref(
    raw_step: Mapping[str, Any],
    step_template: Mapping[str, Any],
    *,
    label: str,
) -> None:
    supplied = raw_step.get("brick_spec_ref")
    if supplied is None:
        return
    declared = _clean_text(f"{label}.brick_spec_ref", supplied)
    expected = step_template.get("brick_spec_ref")
    if declared != expected:
        raise ValueError(f"{label}.brick_spec_ref must match the registered single-Brick spec")


def _validate_composition_brick_spec_ref(
    raw_node: Mapping[str, Any],
    step_template: Mapping[str, Any],
    node_id: str,
    problems: list[CompositionProblem],
) -> None:
    supplied = raw_node.get("brick_spec_ref")
    if supplied is None:
        return
    declared = _composition_optional_text(supplied)
    expected = step_template.get("brick_spec_ref")
    if declared != expected:
        problems.append(
            CompositionProblem(
                "unknown_step_template/agent",
                node_id,
                "brick_spec_ref must match the registered single-Brick spec",
            )
        )


def _chain_preset_steps(preset: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    steps = preset.get("steps", ())
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        return ()
    return tuple(step for step in steps if isinstance(step, Mapping))


def _composition_node_items(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        items: list[Any] = []
        for key, raw_node in value.items():
            if isinstance(raw_node, Mapping):
                merged = dict(raw_node)
                merged.setdefault("node_id", str(key))
                items.append(merged)
            else:
                items.append(raw_node)
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return ()


def _composition_node_id(index: int, raw_node: Mapping[str, Any]) -> str:
    for key in ("node_id", "brick_id", "step_ref"):
        value = _composition_optional_text(raw_node.get(key))
        if value:
            return value
    return f"nodes[{index}]"


def _composition_step_ref(raw_node: Mapping[str, Any], node_id: str) -> str:
    return _composition_optional_text(raw_node.get("step_ref")) or node_id


def _composition_brick_row(
    index: int,
    raw_node: Mapping[str, Any],
    node_id: str,
    problems: list[CompositionProblem],
    step_template: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    raw_brick = raw_node.get("brick")
    brick = raw_brick if isinstance(raw_brick, Mapping) else raw_node
    # Builder auto-fill: a node that names a resolvable step_template need only
    # supply work_statement. comparison_rule then defaults to the template's
    # brick_contract and required_return_shape to the standard base shape; an
    # author-supplied value still overrides (Smith: override-allowed). Without a
    # step_template all three stay author-required (unchanged behavior).
    template_comparison_rule = (
        _composition_optional_text(step_template.get("brick_contract"))
        if isinstance(step_template, Mapping)
        else None
    )
    # The kind's REAL declared return shape, derived from its primary
    # return_template (carried on the step_template registry row by
    # plan_rendering). When a node omits required_return_shape and a step_template
    # resolves, this is the default the gate then requires -- the kind's real
    # fields, not the 2-field literal. Author-supplied value still wins below.
    template_required_return_shape = (
        _composition_optional_text(step_template.get("required_return_shape"))
        if isinstance(step_template, Mapping)
        else None
    )
    if template_comparison_rule:
        required_author_fields = ("work_statement",)
    else:
        required_author_fields = (
            "work_statement",
            "comparison_rule",
            "required_return_shape",
        )
    missing = [
        field
        for field in required_author_fields
        if not _composition_optional_text(brick.get(field))
    ]
    if missing:
        problems.append(
            CompositionProblem(
                "missing_brick_fields",
                node_id,
                "missing Brick field(s): " + ", ".join(missing),
            )
        )
    step_ref = _composition_step_ref(raw_node, node_id)
    brick_ref = _composition_optional_text(brick.get("brick_instance_ref"))
    if not brick_ref:
        brick_ref = _composition_default_brick_ref(node_id)
    row: dict[str, Any] = {
        "axis": "Brick",
        "row_ref": _composition_optional_text(brick.get("row_ref")) or f"brick-row:{step_ref}",
        "brick_work_ref": _composition_optional_text(brick.get("brick_work_ref")) or f"work:{_composition_slug(node_id)}",
        "brick_instance_ref": brick_ref,
        "work_statement": _composition_optional_text(brick.get("work_statement")) or f"missing work statement for {node_id}",
        "comparison_rule": _composition_optional_text(brick.get("comparison_rule")) or template_comparison_rule or f"missing comparison rule for {node_id}",
        # Author value wins; else the kind's real return shape (when a
        # step_template resolves); else, only with NO step_template, the
        # last-resort literal (no-template branch preserved unchanged).
        "required_return_shape": _composition_optional_text(brick.get("required_return_shape")) or template_required_return_shape or "observed_evidence, not_proven",
    }
    source_facts = brick.get("source_facts")
    if source_facts is not None:
        row["source_facts"] = list(_text_sequence(f"nodes[{index}].source_facts", source_facts))
    raw_write_scope = brick.get("write_scope")
    if raw_write_scope is not None:
        row["write_scope"] = dict(_mapping_value(f"nodes[{index}].write_scope", raw_write_scope))
    # Carry the EXPLICIT write NEED marker (requires_brick_write_scope) from the
    # node declaration onto the plan Brick row VERBATIM. Without this carry the
    # graph materializer's stamp would be silently dropped here and strict run
    # admission (require_write_need_marker) would reject every freshly composed
    # write-needed graph plan. Value validation (bool / yes / no, fail-closed on
    # anything else) stays owned by brick.spec.declared_brick_write_need;
    # this is transport only. The legacy ``write_need`` spelling is RETIRED
    # (L legacy cut, 0610): it is REJECTED LOUDLY here instead of being carried
    # or silently dropped (composition keeps no node-key whitelist, so without
    # this rejection a legacy node marker would vanish without a trace).
    if "requires_brick_write_scope" in brick:
        row["requires_brick_write_scope"] = brick.get("requires_brick_write_scope")
    elif "write_need" in brick:
        problems.append(
            CompositionProblem(
                "legacy_write_need_key",
                node_id,
                f"nodes[{index}] carries the retired legacy key 'write_need'; "
                "declare the Brick write NEED as 'requires_brick_write_scope' "
                "(legacy spelling is not admitted)",
            )
        )
    return row


def _composition_default_brick_ref(node_id: str) -> str:
    if node_id.startswith(("brick-", "brick:", "brick-instance:", "brick-boundary:")):
        return node_id
    return f"brick-{_composition_slug(node_id)}"


def _composition_endpoint(edge: Mapping[str, Any], endpoint: str) -> str:
    keys = (
        ("source", "source_node_id", "source_step_ref", "source_ref", "from", "from_node")
        if endpoint == "source"
        else ("target", "target_node_id", "target_step_ref", "target_ref", "to", "to_node")
    )
    for key in keys:
        value = _composition_optional_text(edge.get(key))
        if value:
            return value
    return ""


def _composition_terminal_target(value: str) -> bool:
    return bool(value and value.startswith(("building-boundary:", "building-boundary-")))


def _composition_declared_gate_refs(
    index: int,
    edge: Mapping[str, Any],
    target_ref: str,
    node_id: str,
    problems: list[CompositionProblem],
) -> tuple[str, ...]:
    raw_refs = edge.get("declared_gate_refs")
    admitted_refs = {DEFAULT_LINK_GATE_REF, *COMPACT_LINK_GATE_TOKENS.values()}
    if raw_refs is not None:
        if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
            problems.append(
                CompositionProblem(
                    "bad_gate_token",
                    node_id,
                    "declared_gate_refs must be an array of admitted Link gate refs",
                )
            )
            return (DEFAULT_LINK_GATE_REF,)
        refs = tuple(str(ref).strip() for ref in raw_refs if str(ref).strip())
        if not refs or refs[0] != DEFAULT_LINK_GATE_REF:
            problems.append(
                CompositionProblem(
                    "gate_ref_ordering",
                    node_id,
                    "declared_gate_refs must start with link-gate:default-transition",
                )
            )
        unknown = sorted(ref for ref in refs if ref not in admitted_refs)
        if unknown:
            problems.append(
                CompositionProblem(
                    "bad_gate_token",
                    node_id,
                    "declared_gate_refs contains unadmitted gate ref(s): " + ", ".join(unknown),
                )
            )
        return refs or (DEFAULT_LINK_GATE_REF,)

    raw_gate = edge.get("gate", edge.get("gate_token", edge.get("gates", "")))
    gate_text = _composition_gate_text(raw_gate)
    target_text = target_ref or "brick-invalid-target"
    expression = target_text if not gate_text else f"{gate_text} -> {target_text}"
    try:
        parsed = _parse_compact_link_expression(index, expression)
    except ValueError as exc:
        problems.append(
            CompositionProblem(
                "bad_gate_token",
                node_id,
                str(exc),
            )
        )
        return (DEFAULT_LINK_GATE_REF,)
    return tuple(parsed["declared_gate_refs"])


def _composition_gate_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "+".join(_composition_gate_text(item) for item in value if _composition_gate_text(item))
    text = str(value).strip()
    if text == DEFAULT_LINK_GATE_REF:
        return ""
    for token, gate_ref in COMPACT_LINK_GATE_TOKENS.items():
        if text == gate_ref:
            return token
    return text


def _composition_edge_ref(index: int, edge: Mapping[str, Any], source: str, target: str) -> str:
    declared = _composition_optional_text(edge.get("edge_ref"))
    if declared:
        return declared
    return f"edge:{_composition_slug(source)}-to-{_composition_slug(target or str(index + 1))}"


def _composition_edge_movement(
    index: int,
    edge: Mapping[str, Any],
    problems: list[CompositionProblem],
) -> str:
    movement = _composition_optional_text(edge.get("movement"))
    if not movement:
        problems.append(
            CompositionProblem(
                "missing_movement",
                _composition_edge_ref(index, edge, "edge", str(index + 1)),
                "edge must declare Link movement; support must not choose Movement",
            )
        )
        return ""
    if movement not in MOVEMENT_LITERALS:
        problems.append(
            CompositionProblem(
                "unknown_movement",
                _composition_edge_ref(index, edge, "edge", str(index + 1)),
                f"edge movement must be one of {list(MOVEMENT_LITERALS)}",
            )
        )
    return movement


def _composition_link_edge(record: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = record["raw"]
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": _composition_optional_text(raw.get("row_ref")) or f"link-row:{record['edge_ref']}",
        "movement": record["movement"],
        "target_ref": record["target_ref"],
        "declared_gate_refs": list(record["declared_gate_refs"]),
    }
    for key in (
        "gate_sequence_policy",
        # A1 (0610): translated-gate provenance rides the declared edge like the
        # other Link-owned objects (mapping carry below); absent -> not stamped.
        "gate_concept_provenance",
        "route_replay_plan",
        "route_decision_basis",
        "transition_authoring",
        "transition_lifecycle",
        "building_lifecycle",
    ):
        value = record.get(key, raw.get(key))
        if value is not None:
            if key == "gate_sequence_policy":
                if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                    link_row[key] = value
                else:
                    link_row[key] = [
                        dict(_mapping_value(f"link_edges.{record['edge_ref']}.{key}[{index}]", item))
                        for index, item in enumerate(value)
                    ]
                continue
            link_row[key] = dict(_mapping_value(f"link_edges.{record['edge_ref']}.{key}", raw.get(key)))
    edge: dict[str, Any] = {
        "edge_ref": record["edge_ref"],
        "source_step_ref": record["source_step_ref"],
        "rows": [link_row],
    }
    if record["target_step_ref"]:
        edge["target_step_ref"] = record["target_step_ref"]
    return edge


def _composition_graph_incoming_counts(
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, int]:
    """Count incoming Link edges per declared graph node (mechanical position fact).

    The position of a node in the author/COO-declared graph is read off the
    declared Link edges -- support does not choose it. A node with zero incoming
    edges is a FIRST-position (root) node; this is the same incoming-edge count
    that plan_graph._validate_graph_plan_topology uses to find graph roots, read
    here from the already-resolved compose edge_records (target_step_ref). Edges
    whose target is a terminal building boundary carry an empty target_step_ref
    and are intentionally not counted as incoming to any node.
    """
    counts: dict[str, int] = {
        str(record.get("step_ref", "")).strip(): 0
        for record in node_records
        if str(record.get("step_ref", "")).strip()
    }
    for edge in edge_records:
        target = str(edge.get("target_step_ref", "")).strip()
        if target in counts:
            counts[target] += 1
    return counts


def _composition_hard_graph_contract_problems(
    *,
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    shape_omitted_steps: frozenset[str] | set[str] = frozenset(),
) -> tuple[CompositionProblem, ...]:
    problems: list[CompositionProblem] = []
    records_by_step = {str(record.get("step_ref")): record for record in node_records}
    records_by_endpoint = _composition_records_by_endpoint(node_records)
    budgets = _composition_node_reroute_budgets(node_records)
    fan_in_targets = _composition_fan_in_target_steps(edge_records, groups)
    # POSITION classifier (mechanical, position-driven -- NOT brick-kind-driven):
    # the transition-concern lane is Link-facing or observations-only depending on
    # the node's POSITION in the author-declared graph, which is read off the
    # declared Link edges (the caller/COO authored that structure). The four
    # positions and their concern-lane rule:
    #   * fan-in TARGET (closure-synthesis, incoming from a fan-in group): Link-facing
    #     transition_concern_evidence REQUIRED (closure_transition_concern_shape_missing
    #     when absent) + closure_transition_target_policy validated -- handled in the
    #     fan_in_targets loop below.
    #   * fan-in SOURCE (a parallel lane feeding a fan-in target): concern lane is
    #     OBSERVATIONS-ONLY -- it must NOT carry Link-facing transition_concern_evidence
    #     (qa_transition_concern_shape) -- handled in the per-source loop below.
    #   * FIRST-position (incoming == 0, no upstream Brick): a Link-facing concern has
    #     no upstream Brick to reroute to, so it cannot be Link-routed at all -- handled
    #     by the first-position loop after this one.
    #   * linear (in a graph, not a fan-in member, has an upstream): concern lane ON --
    #     the brick's declared transition_concern_evidence routes to the direct next
    #     Link; no extra rule (the linear/document-centric path already carries it).
    incoming_counts = _composition_graph_incoming_counts(node_records, edge_records)
    fan_in_source_steps: set[str] = set()
    for _target_step_ref, _source_step_refs in fan_in_targets.items():
        fan_in_source_steps.update(_source_step_refs)
    fan_in_target_steps = set(fan_in_targets)
    for target_step_ref, source_step_refs in fan_in_targets.items():
        target_record = records_by_step.get(target_step_ref)
        if target_record is None:
            continue
        target_shape = _composition_required_return_shape(target_record)
        # When the author OMITTED required_return_shape on this fan-in target, the
        # shape carries only the template default (not the author's intent); the
        # clear missing_brick_fields(fan-in lane) problem already covers it, so do
        # not ALSO emit the confusing template-default-driven transition-concern
        # codes for it (design CHANGE 3: clear message INSTEAD of the confusing one).
        if target_step_ref not in shape_omitted_steps:
            if not _composition_shape_has_field(target_shape, "transition_concern_evidence"):
                problems.append(
                    CompositionProblem(
                        "closure_transition_concern_shape_missing",
                        target_step_ref,
                        "fan-in closure-synthesis must be the only Link-facing transition concern source",
                        )
                    )
            if _composition_shape_has_field(target_shape, "transition_concern_evidence"):
                problems.extend(
                    _composition_closure_policy_problems(
                        closure_record=target_record,
                        records_by_endpoint=records_by_endpoint,
                        budgets=budgets,
                    )
                )
        if _composition_step_output_source_facts(target_record):
            problems.append(
                CompositionProblem(
                    "fan_in_source_fact_disk_dependency",
                    target_step_ref,
                    "fan-in closure must receive sibling step outputs through "
                    "source_fact_bodies packet carry, not disk step-output source_facts",
                )
            )
        for source_step_ref in source_step_refs:
            source_record = records_by_step.get(source_step_ref)
            if source_record is None:
                continue
            if source_step_ref in shape_omitted_steps:
                continue
            source_shape = _composition_required_return_shape(source_record)
            if _composition_shape_has_field(source_shape, "transition_concern_evidence"):
                problems.append(
                    CompositionProblem(
                        "qa_transition_concern_shape",
                        source_step_ref,
                        "fan-in QA lanes return their own Brick fields without "
                        "Link-facing transition_concern_evidence; closure-synthesis is "
                        "the single Link-facing transition_concern_evidence source",
                    )
                )
    # FIRST-position rule (NEW, position-driven): a node with no incoming Link edge
    # (incoming == 0) is a graph root. A Link-facing transition_concern_evidence is a
    # send-back/reroute signal that needs an upstream Brick to route to (or a declared
    # closure_transition_target_policy that can HOLD it for a human, which only the
    # fan-in TARGET node carries). A first-position node has neither an upstream Brick
    # nor that per-node concern-disposition policy, so a Link-facing concern here has
    # no valid Link target -- it could only be dispositioned by a HUMAN, and there is
    # no per-node first-position concern-disposition field for support to honor. So a
    # first-position node that declares Link-facing transition_concern_evidence is
    # rejected here (the mechanical position fact: "no upstream route for a root
    # concern"); support invents no auto-human-route mechanism. Fan-in members are
    # excluded (a fan-in source/target has an incoming edge, so incoming > 0 already;
    # the guard below is belt-and-suspenders against a malformed fan-in group).
    for step_ref, record in records_by_step.items():
        if not step_ref:
            continue
        if step_ref in shape_omitted_steps:
            continue
        if step_ref in fan_in_source_steps or step_ref in fan_in_target_steps:
            continue
        if incoming_counts.get(step_ref, 0) != 0:
            continue
        shape = _composition_required_return_shape(record)
        if _composition_shape_has_field(shape, "transition_concern_evidence"):
            problems.append(
                CompositionProblem(
                    "first_position_transition_concern_shape",
                    step_ref,
                    "first-position (root) node has no upstream Brick to route a "
                    "Link-facing transition_concern_evidence to; a root concern must be "
                    "observations-only (human-routed), not Link-facing",
                )
            )
    return tuple(problems)


def _composition_gate_sequence_policy_profile_problems(
    *,
    chain_preset: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> tuple[CompositionProblem, ...]:
    raw_profile = chain_preset.get("gate_sequence_policy", ())
    if raw_profile in (None, ()):
        return ()
    if not isinstance(raw_profile, Sequence) or isinstance(raw_profile, (str, bytes)):
        return (
            CompositionProblem(
                "gate_sequence_policy_invalid",
                "__composition__",
                "gate_sequence_policy must be an array of declared Link gate sequence profiles",
            ),
        )

    problems: list[CompositionProblem] = []
    for index, raw_profile_item in enumerate(raw_profile):
        if not isinstance(raw_profile_item, Mapping):
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_invalid",
                    f"gate_sequence_policy[{index}]",
                    "gate_sequence_policy item must be an object",
                )
            )
            continue
        source_template = _composition_optional_text(
            raw_profile_item.get("source_step_template_ref")
        ) or ""
        target_template = _composition_optional_text(
            raw_profile_item.get("target_step_template_ref")
        ) or ""
        sequence = _composition_gate_sequence_profile_steps(raw_profile_item)
        if not sequence:
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_invalid",
                    f"gate_sequence_policy[{index}]",
                    "gate_sequence_policy profile must declare a non-empty sequence",
                )
            )
            continue
        profile_gate_refs = _composition_gate_sequence_refs(sequence)
        matching_edges = _composition_edges_between_templates(
            edge_records=edge_records,
            node_records=node_records,
            source_template=source_template,
            target_template=target_template,
        )
        if not matching_edges:
            problems.append(
                CompositionProblem(
                    "gate_sequence_policy_edge_missing",
                    f"{source_template}->{target_template}",
                    "chain preset gate sequence policy requires a declared edge between those step templates",
                )
            )
            continue
        for edge in matching_edges:
            declared_refs = tuple(str(ref) for ref in edge.get("declared_gate_refs", ()))
            missing_refs = [ref for ref in profile_gate_refs if ref not in declared_refs]
            if missing_refs:
                problems.append(
                    CompositionProblem(
                        "gate_sequence_policy_gate_ref_missing",
                        str(edge.get("edge_ref", "")),
                        "gate_sequence_policy gate_ref(s) must be present in declared_gate_refs: "
                        + ", ".join(missing_refs),
                    )
                )
    return tuple(problems)


def _composition_edges_between_templates(
    *,
    edge_records: Sequence[Mapping[str, Any]],
    node_records: Sequence[Mapping[str, Any]],
    source_template: str,
    target_template: str,
) -> tuple[Mapping[str, Any], ...]:
    records_by_step = {str(record.get("step_ref", "")).strip(): record for record in node_records}
    matches: list[Mapping[str, Any]] = []
    for edge in edge_records:
        source = records_by_step.get(str(edge.get("source_step_ref", "")).strip())
        target = records_by_step.get(str(edge.get("target_step_ref", "")).strip())
        if source is None or target is None:
            continue
        if source.get("step_template_ref") == source_template and target.get("step_template_ref") == target_template:
            matches.append(edge)
    return tuple(matches)


def _composition_edge_records_with_gate_sequence_policy(
    *,
    chain_preset: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
    edge_records: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    raw_profile = chain_preset.get("gate_sequence_policy", ())
    if not isinstance(raw_profile, Sequence) or isinstance(raw_profile, (str, bytes)):
        return tuple(edge_records)
    patched = [dict(record) for record in edge_records]
    for raw_profile_item in raw_profile:
        if not isinstance(raw_profile_item, Mapping):
            continue
        source_template = _composition_optional_text(
            raw_profile_item.get("source_step_template_ref")
        ) or ""
        target_template = _composition_optional_text(
            raw_profile_item.get("target_step_template_ref")
        ) or ""
        sequence = _composition_gate_sequence_profile_steps(raw_profile_item)
        if not sequence:
            continue
        matches = _composition_edges_between_templates(
            edge_records=edge_records,
            node_records=node_records,
            source_template=source_template,
            target_template=target_template,
        )
        match_refs = {str(edge.get("edge_ref", "")).strip() for edge in matches}
        for record in patched:
            raw = record.get("raw")
            if str(record.get("edge_ref", "")).strip() not in match_refs:
                continue
            if isinstance(raw, Mapping) and raw.get("gate_sequence_policy") is not None:
                continue
            record["gate_sequence_policy"] = [
                _composition_gate_sequence_link_step(item) for item in sequence
            ]
    return tuple(patched)


def _composition_gate_sequence_profile_steps(
    profile: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    raw_steps = profile.get("sequence", profile.get("steps", ()))
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
        return ()
    return tuple(item for item in raw_steps if isinstance(item, Mapping))


def _composition_gate_sequence_refs(
    sequence: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    refs: list[str] = []
    for step in sequence:
        ref = _composition_gate_sequence_ref(step)
        if ref:
            refs.append(ref)
    return tuple(refs)


def _composition_gate_sequence_link_step(step: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(step)
    gate_ref = _composition_gate_sequence_ref(step)
    normalized.pop("declared_link_gate", None)
    if gate_ref:
        normalized["gate_ref"] = gate_ref
    return normalized


def _composition_closure_policy_problems(
    *,
    closure_record: Mapping[str, Any],
    records_by_endpoint: Mapping[str, Mapping[str, Any]],
    budgets: Mapping[str, int],
) -> tuple[CompositionProblem, ...]:
    step_ref = str(closure_record.get("step_ref", "")).strip() or "__closure__"
    raw_policy = closure_record.get("closure_transition_target_policy")
    if not isinstance(raw_policy, Mapping):
        return (
            CompositionProblem(
                "closure_transition_target_policy_missing",
                step_ref,
                "fan-in closure with transition_concern_evidence requires caller / COO "
                "declared closure_transition_target_policy",
            ),
        )

    problems: list[CompositionProblem] = []
    for raw_key in raw_policy:
        concern_kind = str(raw_key).strip()
        if concern_kind not in TRANSITION_CONCERN_KINDS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unknown_concern_kind",
                    step_ref,
                    f"closure_transition_target_policy concern_kind is not admitted: {concern_kind}",
                )
            )
    for concern_kind in _CLOSURE_POLICY_REQUIRED_KINDS:
        raw_row = raw_policy.get(concern_kind)
        if not isinstance(raw_row, Mapping):
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_missing",
                    step_ref,
                    f"closure_transition_target_policy must declare {concern_kind}",
                )
            )
            continue
        action = _composition_policy_action(raw_row)
        target_ref = _composition_policy_target_ref(raw_row)
        if concern_kind == "implementation_gap" and action not in _CLOSURE_POLICY_TARGET_ACTIONS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_missing",
                    step_ref,
                    "implementation_gap must declare an explicit budgeted target",
                )
            )
            continue
        if action in _CLOSURE_POLICY_HOLD_ACTIONS:
            if target_ref:
                problems.append(
                    CompositionProblem(
                        "closure_transition_target_policy_invalid",
                        step_ref,
                        f"{concern_kind} HOLD policy must not also declare target_ref",
                    )
                )
            continue
        if action not in _CLOSURE_POLICY_TARGET_ACTIONS:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_invalid",
                    step_ref,
                    f"{concern_kind} policy action must be hold or target",
                )
            )
            continue
        target_record = records_by_endpoint.get(target_ref)
        if target_record is None:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unknown_target",
                    step_ref,
                    f"{concern_kind} target_ref does not resolve to an existing Brick node: {target_ref or '(blank)'}",
                )
            )
            continue
        target_brick_ref = str(target_record.get("brick_ref", "")).strip()
        if target_brick_ref not in budgets:
            problems.append(
                CompositionProblem(
                    "closure_transition_target_policy_unbudgeted_target",
                    step_ref,
                    f"{concern_kind} target_ref must name a node with node_reroute_budget: {target_ref}",
                )
            )
    return tuple(problems)


def _composition_records_by_endpoint(
    node_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Mapping[str, Any]]:
    endpoints: dict[str, Mapping[str, Any]] = {}
    for record in node_records:
        for key in ("node_id", "step_ref", "brick_ref"):
            value = str(record.get(key, "")).strip()
            if value:
                endpoints[value] = record
    return endpoints


def _composition_policy_action(policy_row: Mapping[str, Any]) -> str:
    for key in ("action", "disposition", "disposition_action"):
        value = _composition_optional_text(policy_row.get(key))
        if value:
            return value.lower()
    # FAIL CLOSED: do NOT infer a Movement action from the mere presence of a
    # target_ref. When no explicit action/disposition is declared, the action is
    # ABSENT -- support records that absence (returns "") and the consumer rejects
    # the target-without-action row ("policy action must be hold or target").
    return ""


def _composition_policy_target_ref(policy_row: Mapping[str, Any]) -> str:
    for key in ("target_ref", "target", "target_node_id", "target_step_ref", "target_brick_ref"):
        value = _composition_optional_text(policy_row.get(key))
        if value:
            return value
    return ""


def _composition_fan_in_target_steps(
    edge_records: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
) -> Mapping[str, tuple[str, ...]]:
    edge_by_ref = {str(record.get("edge_ref")): record for record in edge_records}
    targets: dict[str, list[str]] = {}
    for group in groups:
        if not isinstance(group, Mapping) or str(group.get("group_role", "")).strip() != "fan_in":
            continue
        raw_refs = group.get("member_refs", ())
        if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
            continue
        for edge_ref in raw_refs:
            record = edge_by_ref.get(str(edge_ref))
            if not record:
                continue
            target = str(record.get("target_step_ref", "")).strip()
            source = str(record.get("source_step_ref", "")).strip()
            if target and source:
                targets.setdefault(target, []).append(source)
    return {target: tuple(dict.fromkeys(sources)) for target, sources in targets.items()}


def _composition_required_return_shape(record: Mapping[str, Any]) -> str:
    brick_row = record.get("brick_row")
    if not isinstance(brick_row, Mapping):
        return ""
    return str(brick_row.get("required_return_shape", "")).lower()


def _composition_author_required_return_shape(record: Mapping[str, Any]) -> str:
    """The AUTHOR-declared required_return_shape for a node (NOT the U2-3 default).

    Mirrors _composition_brick_row's brick extraction (node.brick mapping, else
    the node itself) and returns the author's raw required_return_shape text. This
    is read from raw_node so a fan-in member that omitted the field is detected
    even though brick_row already carries the template default.
    """
    raw_node = record.get("raw")
    if not isinstance(raw_node, Mapping):
        return ""
    raw_brick = raw_node.get("brick")
    brick = raw_brick if isinstance(raw_brick, Mapping) else raw_node
    return _composition_optional_text(brick.get("required_return_shape")) or ""


def _composition_step_output_source_facts(record: Mapping[str, Any]) -> tuple[str, ...]:
    brick_row = record.get("brick_row")
    if not isinstance(brick_row, Mapping):
        return ()
    raw = brick_row.get("source_facts", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(
        str(item)
        for item in raw
        if "step-output" in str(item) or "step-outputs" in str(item)
    )


def _composition_validator_problems(
    plan: Mapping[str, Any],
    repo: Path,
) -> tuple[CompositionProblem, ...]:
    problems: list[CompositionProblem] = []
    try:
        from support.operator.plan_graph import _linear_plan_from_graph_plan  # noqa: PLC0415
        from support.operator.plan_validation import validate_declared_building_plan  # noqa: PLC0415

        linear_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        validate_declared_building_plan(linear_plan, repo_root=repo)
    except (TypeError, ValueError) as exc:
        problems.append(_composition_problem_from_validator(str(exc)))
    return tuple(problems)


def _composition_problem_from_validator(message: str) -> CompositionProblem:
    lowered = message.lower()
    if "gate_sequence_policy" in lowered and "budget" in lowered:
        code = "gate_sequence_policy_unbudgeted_target"
    elif "gate_sequence_policy" in lowered and "next_gate_ref" in lowered:
        code = "gate_sequence_policy_next_gate_ref"
    elif "gate_sequence_policy" in lowered and "forbidden authority key" in lowered:
        code = "gate_sequence_policy_authority_leak"
    elif "gate_sequence_policy" in lowered:
        code = "gate_sequence_policy_invalid"
    elif "declared_gate_refs must start" in lowered:
        code = "gate_ref_ordering"
    elif "gate" in lowered and ("unadmitted" in lowered or "unknown" in lowered):
        code = "bad_gate_token"
    elif "cycle" in lowered:
        code = "cycle/self_loop"
    elif "duplicate" in lowered or "appears more than once" in lowered:
        code = "duplicate_brick_id"
    elif "does not resolve" in lowered or "without target_step_ref" in lowered:
        code = "unknown_endpoint"
    elif "brick row" in lowered and ("must" in lowered or "missing" in lowered):
        code = "missing_brick_fields"
    elif "execution_order" in lowered or "fan_out" in lowered or "fan_in" in lowered or "group" in lowered or "completion_edge_ref" in lowered:
        code = "execution_order/groups coherence"
    else:
        code = "execution_order/groups coherence"
    return CompositionProblem(code, "__validators__", message)


def _composition_agent_object_refs(repo: Path) -> frozenset[str]:
    object_dir = repo / "agent" / "objects"
    return frozenset(f"agent-object:{path.stem}" for path in object_dir.glob("*.yaml"))
