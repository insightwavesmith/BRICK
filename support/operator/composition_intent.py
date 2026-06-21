"""Launch-path entrypoints (composition top layer).

The caller/COO-facing materialization entrypoints that turn a confirmed task
source + selected chain preset / step-template intent into declared Brick / Agent
/ Link rows. Extracted VERBATIM from composition.py (cluster
``composition_intent``); composition.py keeps a facade re-export so every existing
``from brick_protocol.support.operator.composition import X`` still resolves. This
module imports its siblings DIRECTLY and never imports composition.py at top level
(cycle); the one back-reference (``_chain_preset_requires_graph``, which still
lives in composition.py) is imported lazily in-function.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
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
    _clean_selected_adapter_ref,
    _declared_step_from_step_template,
    _is_caller_or_coo_declaration,
    _load_shape_registry,
    _validate_declared_plan_projection,
    render_declared_building_plan,
)
from brick_protocol.support.operator.composition_common import (
    _composition_optional_text,
    _composition_slug,
)
from brick_protocol.support.operator.composition_graph_emit import (
    _materializer_graph_plan,
)


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

    # Lazy sibling import (cycle-avoid): _chain_preset_requires_graph still
    # lives in composition.py, so it is imported in-function rather than at
    # module top level.
    from brick_protocol.support.operator.composition import _chain_preset_requires_graph

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
