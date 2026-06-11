"""Declaration-provenance evidence packets.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
declared-Building intake / preset-expansion / declared-plan / link-launch-policy
provenance packets + the declaration-provenance observation that
``support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern emitter. P1/P12 BUILDING-DECLARATION-INTEGRITY:
``_write_declaration_work_evidence`` records the declaration chain (task source +
the four provenance packets) so a reviewer can confirm exactly which declared
plan was walked; the per-plan helpers (composition_mode / plan_shape /
selected_preset_ref / step+brick spec+return template refs / link-launch rows) read the
declared plan only. Records evidence copies; authors no Movement or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.plan_graph import _graph_declared_edges
from brick_protocol.support.operator.plan_rendering import _load_shape_registry
from brick_protocol.support.operator.plan_validation import (
    _movement_and_target_from_link_row,
)
from brick_protocol.support.operator.primitives import (
    INLINE_TASK_SOURCE_REF,
    _REPO_ROOT,
    _merge_texts,
    _optional_text_or_none,
    _text_tuple,
)

_DECLARATION_EVIDENCE_REFS: tuple[str, ...] = (
    "work/task.md",
    "work/building-intake.json",
    "work/preset-expansion.json",
    "work/declared-building-plan.json",
    "work/link-launch-policy.json",
)

_DECLARATION_PROOF_LIMITS: tuple[str, ...] = (
    "support declaration provenance evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)

# FQ-2 declared-plan purity (codex review P2): the Building birth-certificate
# ``work/declared-building-plan.json`` records ONLY the declared launch
# declaration. The walker threads its RUNTIME state onto the plan dict before the
# accumulated write (support/operator/walker_kernel.py / walker_resume.py inject
# ``dynamic_walker_evidence`` -- whose body holds node_reroute_budgets /
# node_reroute_landings / reroute_adoption_records / held / hold / walker_mode /
# resume_observations / fan_in_wait_all_observations -- and a previously-persisted
# plan can round-trip a top-level ``node_reroute_budgets`` into the declared
# launch declaration). That runtime belongs in
# evidence-manifest.plan_snapshot.plan_rows_copy (kept) / frontier / traces, NOT
# in the declared-plan copy. These TOP-LEVEL keys are stripped from
# ``declared_plan_copy`` before the canonical copy + hash are taken so the
# birth-certificate stays pure; the runtime walker evidence is unaffected
# everywhere else (the evidence-manifest snapshot still records it verbatim).
_DECLARED_PLAN_RUNTIME_KEYS: frozenset[str] = frozenset(
    {
        "dynamic_walker_evidence",
        "node_reroute_budgets",
        "node_reroute_landings",
        "reroute_adoption_records",
        "fan_in_wait_all_observations",
        "resume_observations",
        "held",
        "hold",
        "walker_mode",
    }
)


def _pure_declared_plan_copy(plan: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-ready copy of the declared plan with runtime walker state stripped.

    Keeps every DECLARED launch key (building_id, plan_ref, composition_mode,
    declared_by, owner_axis, selected_*_ref, steps/brick_steps, link_edges,
    graph_context_ref, task_source_ref, preset_expansion, proof_limits,
    not_proven, ...); drops only the top-level runtime keys the walker threads
    onto the plan (``_DECLARED_PLAN_RUNTIME_KEYS``). The nested runtime fields
    (reroute_adoption_records / held / hold / budget_exhausted / landing / ...)
    live ONLY under ``dynamic_walker_evidence``, so removing that top-level key
    removes them in one pass.
    """

    return {
        str(key): _json_ready(value)
        for key, value in plan.items()
        if str(key) not in _DECLARED_PLAN_RUNTIME_KEYS
    }


def _write_declaration_work_evidence(
    root: Path,
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    declaration_plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> tuple[Path, ...]:
    _task_source_hash_observation(declaration_plan, task_source_ref)
    work_dir = root / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    task_path = work_dir / "task.md"
    task_path.write_text(
        _task_markdown_evidence(
            task_source_ref,
            inline_statement=_inline_task_statement(declaration_plan, plan),
        ),
        encoding="utf-8",
    )
    written.append(task_path)

    packets = {
        "building-intake.json": _building_intake_packet(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
            graph_context=graph_context,
            task_source_ref=task_source_ref,
            proof_limits=proof_limits,
            not_proven=not_proven,
        ),
        "preset-expansion.json": _preset_expansion_packet(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
            proof_limits=proof_limits,
            not_proven=not_proven,
        ),
        "declared-building-plan.json": _declared_building_plan_packet(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=declaration_plan,
        ),
        "link-launch-policy.json": _link_launch_policy_packet(
            building_id=building_id,
            plan_ref=plan_ref,
            plan=plan,
            declaration_plan=declaration_plan,
            graph_context=graph_context,
            proof_limits=proof_limits,
            not_proven=not_proven,
        ),
    }
    for filename, packet in packets.items():
        path = work_dir / filename
        path.write_text(_canonical_json_text(packet), encoding="utf-8")
        written.append(path)
    return tuple(written)


def _inline_task_statement(*plans: Mapping[str, Any] | None) -> str | None:
    """First non-empty inline ``task_statement`` carried by a plan, or None.

    TASK-BY-TEXT (0611, codex FIX-A): the inline task body rides ON the
    declared plan (next to the ``task-source:inline-statement`` sentinel
    ``task_source_ref``); the evidence writer reads it from the plan copy --
    there is NO file form of an inline statement anywhere.
    """

    for plan in plans:
        if not isinstance(plan, Mapping):
            continue
        statement = plan.get("task_statement")
        if isinstance(statement, str) and statement.strip():
            return statement
    return None


def _task_markdown_evidence(
    task_source_ref: str | None,
    *,
    inline_statement: str | None = None,
) -> str:
    if task_source_ref == INLINE_TASK_SOURCE_REF and inline_statement is not None:
        # Inline flow: land the spoken statement VERBATIM (the materializer
        # already normalized it to a single trailing newline; keep the guard
        # so a hand-written plan body still lands newline-terminated).
        return (
            inline_statement
            if inline_statement.endswith("\n")
            else inline_statement + "\n"
        )
    if task_source_ref:
        source = _REPO_ROOT / task_source_ref
        if task_source_ref != INLINE_TASK_SOURCE_REF and source.is_file():
            text = source.read_text(encoding="utf-8")
            return text if text.endswith("\n") else text + "\n"
        return (
            "# Building Task Source Evidence\n\n"
            f"Declared task_source_ref was not readable at evidence-write time: {task_source_ref}\n\n"
            "proof_limits:\n"
            "- support evidence only\n"
            "- not source truth\n"
            "- not Movement authority\n\n"
            "not_proven:\n"
            "- declared task source body\n"
        )
    return (
        "# Building Task Source Evidence\n\n"
        "No task_source_ref was declared on the walked Building Plan.\n\n"
        "proof_limits:\n"
        "- support evidence only\n"
        "- not source truth\n"
        "- not Movement authority\n\n"
        "not_proven:\n"
        "- external task source body\n"
    )


def _task_source_hash_observation(
    plan: Mapping[str, Any],
    task_source_ref: str | None,
) -> Mapping[str, str]:
    declared_hash = _plan_text(plan, "task_source_hash")
    declared_algorithm = _plan_text(plan, "task_source_hash_algorithm")
    declared_basis = _plan_text(plan, "task_source_hash_basis")
    if not task_source_ref:
        return {
            "task_source_hash": "",
            "task_source_hash_algorithm": declared_algorithm,
            "task_source_hash_basis": declared_basis,
            "task_source_hash_state": "not_declared",
        }
    if task_source_ref == INLINE_TASK_SOURCE_REF:
        # Inline flow: the hash source is the statement body carried ON the
        # plan, never a file. Missing body mirrors the file flow's
        # source_unreadable observation (run admission already rejects it).
        inline_statement = _inline_task_statement(plan)
        if inline_statement is None:
            return {
                "task_source_hash": declared_hash,
                "task_source_hash_algorithm": declared_algorithm,
                "task_source_hash_basis": declared_basis,
                "task_source_hash_state": "source_unreadable",
            }
        observed_hash = hashlib.sha256(inline_statement.encode("utf-8")).hexdigest()
        if declared_hash and declared_hash != observed_hash:
            raise ValueError(
                "task_source_hash mismatch: materialized task_statement body differs "
                "from evidence-write task_statement body"
            )
        return {
            "task_source_hash": declared_hash or observed_hash,
            "task_source_hash_algorithm": declared_algorithm or "sha256",
            "task_source_hash_basis": declared_basis
            or "utf-8 inline task_statement body at evidence-write time",
            "task_source_hash_state": "matched" if declared_hash else "observed_at_evidence_write",
        }
    source = _REPO_ROOT / task_source_ref
    if not source.is_file():
        return {
            "task_source_hash": declared_hash,
            "task_source_hash_algorithm": declared_algorithm,
            "task_source_hash_basis": declared_basis,
            "task_source_hash_state": "source_unreadable",
        }
    observed_hash = hashlib.sha256(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    if declared_hash and declared_hash != observed_hash:
        raise ValueError(
            "task_source_hash mismatch: materialized task_source_ref body differs "
            "from evidence-write task_source_ref body"
        )
    return {
        "task_source_hash": declared_hash or observed_hash,
        "task_source_hash_algorithm": declared_algorithm or "sha256",
        "task_source_hash_basis": declared_basis or "utf-8 task_source_ref body at evidence-write time",
        "task_source_hash_state": "matched" if declared_hash else "observed_at_evidence_write",
    }


def _building_intake_packet(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    observed_not_proven = _declaration_not_proven(
        plan,
        task_source_ref=task_source_ref,
        graph_context=graph_context,
        not_proven=not_proven,
    )
    task_hash = _task_source_hash_observation(plan, task_source_ref)
    return {
        "kind": "building_intake_provenance",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "declared_by": _plan_text(plan, "declared_by"),
        "composition_mode": _composition_mode(plan),
        "task_source_ref": task_source_ref or "",
        **task_hash,
        "plan_shape": _plan_shape(plan, graph_context),
        "selected_shape_ref": _plan_text(plan, "selected_shape_ref"),
        "selected_preset_ref": _selected_preset_ref(plan),
        "selected_adapter_ref": _plan_text(plan, "selected_adapter_ref"),
        "selected_model_ref": _plan_text(plan, "selected_model_ref"),
        "declaration_evidence_refs": list(_DECLARATION_EVIDENCE_REFS),
        "proof_limits": list(_merge_texts(_DECLARATION_PROOF_LIMITS, proof_limits)),
        "not_proven": list(observed_not_proven),
    }


def _preset_expansion_packet(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    step_template_refs = _step_template_refs(plan)
    catalog_binding = _catalog_expansion_binding(plan, step_template_refs)
    agent_bindings = _agent_binding_declarations(plan)
    brick_spec_refs = _physical_brick_spec_refs(plan, catalog_binding)
    non_physical_spec_refs = _non_physical_brick_spec_refs(plan)
    brick_template_refs = _physical_brick_template_refs(plan, catalog_binding)
    non_physical_plan_refs = _non_physical_brick_template_refs(plan)
    missing: list[str] = []
    if not _selected_preset_ref(plan):
        missing.append("selected preset ref was not exposed by the plan")
    if not step_template_refs:
        missing.append("step template refs were not exposed by the plan")
    if not brick_spec_refs:
        missing.append("Brick spec refs were not exposed by the plan")
    if not brick_template_refs:
        missing.append("Brick template refs were not exposed by the plan")
    if non_physical_spec_refs:
        missing.append(
            "non-physical Brick spec refs were present and not copied: "
            + ", ".join(non_physical_spec_refs)
        )
    if non_physical_plan_refs:
        missing.append(
            "non-physical Brick template refs were present and not copied: "
            + ", ".join(non_physical_plan_refs)
        )
    return {
        "kind": "preset_expansion_provenance",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "composition_mode": _composition_mode(plan),
        "selected_shape_ref": _plan_text(plan, "selected_shape_ref"),
        "selected_preset_ref": _selected_preset_ref(plan),
        "chain_preset_ref": _plan_text(plan, "chain_preset_ref"),
        "shape_catalog_ref": catalog_binding["shape_catalog_ref"],
        "chain_preset_catalog_source": catalog_binding["chain_preset_catalog_source"],
        "canonical_chain_preset_ref": catalog_binding["canonical_chain_preset_ref"],
        "compat_chain_preset_ref": catalog_binding["compat_chain_preset_ref"],
        "chain_preset_catalog_scope": catalog_binding["chain_preset_catalog_scope"],
        "common_basis_ref": catalog_binding["common_basis_ref"],
        "expanded_step_template_refs": list(step_template_refs),
        "expanded_brick_spec_refs": list(brick_spec_refs),
        "expanded_brick_template_refs": list(brick_template_refs),
        "agent_binding_declarations": list(agent_bindings),
        "proof_limits": list(_merge_texts(_DECLARATION_PROOF_LIMITS, proof_limits)),
        "not_proven": list(_merge_texts(not_proven, missing, catalog_binding["not_proven"])),
    }


def _declared_building_plan_packet(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
) -> Mapping[str, Any]:
    # FQ-2: the birth-certificate copy is PURE -- runtime walker state threaded
    # onto the plan is stripped (see _pure_declared_plan_copy). The hash covers
    # the pure declared copy so the stored hash is re-derivable from the recorded
    # declared_plan_copy.
    plan_copy = _pure_declared_plan_copy(plan)
    canonical = json.dumps(
        plan_copy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "kind": "declared_building_plan_provenance",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "plan_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "plan_hash_algorithm": "sha256",
        "plan_hash_basis": (
            "canonical sorted-key JSON of the pure declared-building-plan copy "
            "(runtime walker state excluded)"
        ),
        "declared_plan_copy": plan_copy,
        "proof_limits": list(_DECLARATION_PROOF_LIMITS),
        "not_proven": [
            "declared plan semantic correctness",
            "future Agent or provider behavior",
        ],
    }


def _link_launch_policy_packet(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    declaration_plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    launch_rows = _link_launch_rows(declaration_plan, graph_context)
    plan_budget_source = declaration_plan if "node_reroute_budgets" in declaration_plan else plan
    return {
        "kind": "link_launch_policy_provenance",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "plan_shape": _plan_shape(declaration_plan, graph_context),
        "selected_shape_ref": _plan_text(declaration_plan, "selected_shape_ref"),
        "declared_gate_refs": list(_unique_texts(*(row["declared_gate_refs"] for row in launch_rows))),
        "node_reroute_budgets": _mapping_copy(plan_budget_source.get("node_reroute_budgets")),
        "max_attempts_by_boundary": _mapping_copy(
            declaration_plan.get("max_attempts_by_boundary")
            if "max_attempts_by_boundary" in declaration_plan
            else plan.get("max_attempts_by_boundary")
        ),
        "launch_rows": launch_rows,
        "proof_limits": list(
            _merge_texts(
                _DECLARATION_PROOF_LIMITS,
                proof_limits,
                ("P3 records launch parameters only; P4 owns Carry budget evidence",),
            )
        ),
        "not_proven": list(
            _merge_texts(
                not_proven,
                ()
                if launch_rows
                else ("declared Link launch rows were not exposed by the plan",),
            )
        ),
    }


def _declaration_provenance_observation(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> Mapping[str, Any]:
    return {
        "building_id": building_id,
        "plan_ref": plan_ref,
        "composition_mode": _composition_mode(plan),
        "declared_by": _plan_text(plan, "declared_by"),
        "task_source_ref": task_source_ref or "",
        "plan_shape": _plan_shape(plan, graph_context),
        "selected_shape_ref": _plan_text(plan, "selected_shape_ref"),
        "selected_preset_ref": _selected_preset_ref(plan),
        "expanded_step_template_refs": list(_step_template_refs(plan)),
        "expanded_brick_spec_refs": list(_brick_spec_refs(plan)),
        "expanded_brick_template_refs": list(_brick_template_refs(plan)),
        "declared_gate_refs": list(
            _unique_texts(*(row["declared_gate_refs"] for row in _link_launch_rows(plan, graph_context)))
        ),
        "declaration_evidence_refs": list(_DECLARATION_EVIDENCE_REFS),
        "proof_limits": list(_merge_texts(_DECLARATION_PROOF_LIMITS, proof_limits)),
        "not_proven": list(
            _declaration_not_proven(
                plan,
                task_source_ref=task_source_ref,
                graph_context=graph_context,
                not_proven=not_proven,
            )
        ),
    }


def _declaration_not_proven(
    plan: Mapping[str, Any],
    *,
    task_source_ref: str | None,
    graph_context: Mapping[str, Any] | None,
    not_proven: tuple[str, ...],
) -> tuple[str, ...]:
    missing: list[str] = []
    if not task_source_ref:
        missing.append("task_source_ref was not declared")
    if not _plan_text(plan, "declared_by"):
        missing.append("declared_by was not exposed by the plan")
    if not _plan_shape(plan, graph_context):
        missing.append("plan_shape was not exposed by the plan")
    # U5/D5: selected_shape_ref is now an OPTIONAL recorded tag, not a required
    # declaration field; its absence is no longer a not_proven gap. When present it
    # is still recorded as a tag (see the *_packet helpers above).
    if not _selected_preset_ref(plan):
        missing.append("selected preset ref was not exposed by the plan")
    if not _step_template_refs(plan):
        missing.append("step template refs were not exposed by the plan")
    return _merge_texts(not_proven, missing)


def _plan_text(plan: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = _optional_text_or_none(plan.get(key))
        if text:
            return text
    provenance = plan.get("declaration_provenance")
    if isinstance(provenance, Mapping):
        for key in keys:
            text = _optional_text_or_none(provenance.get(key))
            if text:
                return text
    return ""


def _composition_mode(plan: Mapping[str, Any]) -> str:
    return _plan_text(plan, "composition_mode") or (
        "declared-graph" if _optional_text_or_none(plan.get("plan_shape")) == "graph" else ""
    )


def _plan_shape(plan: Mapping[str, Any], graph_context: Mapping[str, Any] | None) -> str:
    return _plan_text(plan, "plan_shape") or ("graph" if graph_context else "")


def _selected_preset_ref(plan: Mapping[str, Any]) -> str:
    return _plan_text(plan, "selected_preset_ref", "chain_preset_ref", "preset_ref")


def _step_template_refs(plan: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for container_key in ("preset_expansion", "step_template_expansion", "declaration_provenance"):
        container = plan.get(container_key)
        if isinstance(container, Mapping):
            refs.extend(
                _text_tuple(
                    f"{container_key}.expanded_step_template_refs",
                    container.get("expanded_step_template_refs", ()),
                )
            )
            refs.extend(
                _text_tuple(
                    f"{container_key}.step_template_refs",
                    container.get("step_template_refs", ()),
                )
            )
    for step in _plan_step_mappings(plan):
        text = _optional_text_or_none(step.get("step_template_ref"))
        if text:
            refs.append(text)
    return _unique_texts(refs)


def _brick_template_refs(plan: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for container_key in ("preset_expansion", "step_template_expansion", "declaration_provenance"):
        container = plan.get(container_key)
        if isinstance(container, Mapping):
            refs.extend(
                _text_tuple(
                    f"{container_key}.expanded_brick_template_refs",
                    container.get("expanded_brick_template_refs", ()),
                )
            )
            refs.extend(
                _text_tuple(
                    f"{container_key}.brick_template_refs",
                    container.get("brick_template_refs", ()),
                )
            )
    return _unique_texts(refs)


def _brick_spec_refs(plan: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for container_key in ("preset_expansion", "step_template_expansion", "declaration_provenance"):
        container = plan.get(container_key)
        if isinstance(container, Mapping):
            refs.extend(
                _text_tuple(
                    f"{container_key}.expanded_brick_spec_refs",
                    container.get("expanded_brick_spec_refs", ()),
                )
            )
            refs.extend(
                _text_tuple(
                    f"{container_key}.brick_spec_refs",
                    container.get("brick_spec_refs", ()),
                )
            )
    return _unique_texts(refs)


def _physical_brick_spec_refs(
    plan: Mapping[str, Any],
    catalog_binding: Mapping[str, Any],
) -> tuple[str, ...]:
    refs: list[str] = []
    refs.extend(
        _text_tuple(
            "catalog_binding.expanded_brick_spec_refs",
            catalog_binding.get("expanded_brick_spec_refs", ()),
        )
    )
    refs.extend(
        ref
        for ref in _brick_spec_refs(plan)
        if _is_physical_brick_spec_ref(ref)
    )
    return _unique_texts(refs)


def _non_physical_brick_spec_refs(plan: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(ref for ref in _brick_spec_refs(plan) if not _is_physical_brick_spec_ref(ref))


def _physical_brick_template_refs(
    plan: Mapping[str, Any],
    catalog_binding: Mapping[str, Any],
) -> tuple[str, ...]:
    refs: list[str] = []
    refs.extend(
        _text_tuple(
            "catalog_binding.expanded_brick_template_refs",
            catalog_binding.get("expanded_brick_template_refs", ()),
        )
    )
    refs.extend(
        ref
        for ref in _brick_template_refs(plan)
        if _is_physical_brick_template_ref(ref)
    )
    return _unique_texts(refs)


def _non_physical_brick_template_refs(plan: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        ref for ref in _brick_template_refs(plan) if not _is_physical_brick_template_ref(ref)
    )


def _catalog_expansion_binding(
    plan: Mapping[str, Any],
    step_template_refs: tuple[str, ...],
) -> Mapping[str, Any]:
    binding: dict[str, Any] = {
        "shape_catalog_ref": "",
        "chain_preset_catalog_source": "",
        "canonical_chain_preset_ref": "",
        "compat_chain_preset_ref": "",
        "chain_preset_catalog_scope": "",
        "common_basis_ref": "",
        "expanded_brick_spec_refs": (),
        "expanded_brick_template_refs": (),
        "not_proven": (),
    }
    try:
        registry = _load_shape_registry(_REPO_ROOT)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        binding["not_proven"] = (
            f"split Brick template catalog was not readable for declaration binding: {exc}",
        )
        return binding

    registry_ref = _optional_text_or_none(registry.get("registry_ref")) or ""
    binding["shape_catalog_ref"] = registry_ref
    chain_binding = _chain_preset_catalog_binding(plan, registry)
    binding.update(chain_binding)

    step_templates = registry.get("step_templates")
    if not isinstance(step_templates, Mapping):
        binding["not_proven"] = ("shape catalog step_templates were not readable",)
        return binding

    spec_refs: list[str] = []
    refs: list[str] = []
    missing: list[str] = []
    for step_template_ref in step_template_refs:
        step_template = step_templates.get(step_template_ref)
        if not isinstance(step_template, Mapping):
            missing.append(f"step template {step_template_ref} was not found in the split catalog")
            continue
        raw_spec_ref = _optional_text_or_none(step_template.get("brick_spec_ref"))
        if raw_spec_ref and _is_physical_brick_spec_ref(raw_spec_ref):
            spec_refs.append(raw_spec_ref)
        else:
            missing.append(f"step template {step_template_ref} has no physical brick_spec_ref")
        raw_refs = step_template.get("brick_template_refs", ())
        physical_refs = tuple(
            ref
            for ref in _text_tuple(
                f"step_templates[{step_template_ref}].brick_template_refs",
                raw_refs,
            )
            if _is_physical_brick_template_ref(ref)
        )
        if not physical_refs:
            missing.append(f"step template {step_template_ref} has no physical brick_template_refs")
        refs.extend(physical_refs)

    binding["expanded_brick_spec_refs"] = _unique_texts(spec_refs)
    binding["expanded_brick_template_refs"] = _unique_texts(refs)
    binding["not_proven"] = _merge_texts(
        binding["not_proven"],
        chain_binding.get("not_proven", ()),
        missing,
    )
    return binding


def _is_physical_brick_spec_ref(ref: str) -> bool:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        return False
    if (
        len(path.parts) != 5
        or path.parts[0] != "brick"
        or path.parts[1] != "templates"
        or path.parts[2] != "bricks"
        or not path.parts[3]
        or path.parts[4] != "brick.md"
    ):
        return False
    return (_REPO_ROOT / path).is_file()


def _is_physical_brick_template_ref(ref: str) -> bool:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        return False
    if len(path.parts) < 3 or path.parts[0] != "brick" or path.parts[1] != "templates":
        return False
    return (_REPO_ROOT / path).is_file()


def _chain_preset_catalog_binding(
    plan: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> Mapping[str, Any]:
    declared_ref = _plan_text(plan, "chain_preset_ref") or _selected_preset_ref(plan)
    if not declared_ref:
        return {
            "chain_preset_catalog_source": "",
            "canonical_chain_preset_ref": "",
            "compat_chain_preset_ref": "",
            "chain_preset_catalog_scope": "",
            "common_basis_ref": "",
            "not_proven": (),
        }

    aliases = registry.get("chain_preset_aliases")
    aliases = aliases if isinstance(aliases, Mapping) else {}
    canonical_ref = _optional_text_or_none(aliases.get(declared_ref)) or declared_ref
    compat_ref = declared_ref if canonical_ref != declared_ref else ""

    chain_presets = registry.get("chain_presets")
    common_presets = registry.get("common_chain_presets")
    dogfood_presets = registry.get("dogfood_chain_presets")
    chain_presets = chain_presets if isinstance(chain_presets, Mapping) else {}
    common_presets = common_presets if isinstance(common_presets, Mapping) else {}
    dogfood_presets = dogfood_presets if isinstance(dogfood_presets, Mapping) else {}

    source = ""
    if canonical_ref in common_presets:
        source = "common_chain_presets"
        preset = common_presets[canonical_ref]
    elif canonical_ref in dogfood_presets:
        source = "dogfood_chain_presets"
        preset = dogfood_presets[canonical_ref]
    else:
        source = "chain_presets" if canonical_ref in chain_presets else ""
        preset = chain_presets.get(canonical_ref, {})

    preset_mapping = preset if isinstance(preset, Mapping) else {}
    return {
        "chain_preset_catalog_source": source,
        "canonical_chain_preset_ref": canonical_ref if source else "",
        "compat_chain_preset_ref": compat_ref,
        "chain_preset_catalog_scope": _optional_text_or_none(preset_mapping.get("catalog_scope")) or "",
        "common_basis_ref": _optional_text_or_none(preset_mapping.get("common_basis_ref")) or "",
        "not_proven": ()
        if source
        else (f"declared chain preset {declared_ref} was not found in the split catalog",),
    }


def _agent_binding_declarations(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    bindings: list[Mapping[str, Any]] = []
    for step in _plan_step_mappings(plan):
        step_ref = _optional_text_or_none(step.get("step_ref")) or ""
        for row in _step_rows(step):
            if row.get("axis") != "Agent":
                continue
            bindings.append(
                {
                    "step_ref": step_ref,
                    "agent_object_ref": _optional_text_or_none(row.get("agent_object_ref")) or "",
                    "row_ref": _optional_text_or_none(row.get("row_ref")) or "",
                }
            )
    return tuple(bindings)


def _link_launch_rows(
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    if graph_context:
        for edge in _graph_declared_edges(graph_context):
            link_row = edge.get("link_row")
            if isinstance(link_row, Mapping):
                rows.append(
                    _link_launch_row_packet(
                        link_row,
                        step_ref=_optional_text_or_none(edge.get("source_step_ref")) or "",
                        edge_ref=_optional_text_or_none(edge.get("edge_ref")) or "",
                    )
                )
    elif _optional_text_or_none(plan.get("plan_shape")) == "graph":
        for edge in plan.get("link_edges", ()):
            if not isinstance(edge, Mapping):
                continue
            edge_rows = edge.get("rows")
            if not isinstance(edge_rows, list) or not edge_rows:
                continue
            link_row = edge_rows[0]
            if isinstance(link_row, Mapping):
                rows.append(
                    _link_launch_row_packet(
                        link_row,
                        step_ref=_optional_text_or_none(edge.get("source_step_ref")) or "",
                        edge_ref=_optional_text_or_none(edge.get("edge_ref")) or "",
                    )
                )
    else:
        for step in _plan_step_mappings(plan):
            step_ref = _optional_text_or_none(step.get("step_ref")) or ""
            for row in _step_rows(step):
                if row.get("axis") == "Link":
                    rows.append(_link_launch_row_packet(row, step_ref=step_ref, edge_ref=""))
    return tuple(rows)


def _link_launch_row_packet(
    link_row: Mapping[str, Any],
    *,
    step_ref: str,
    edge_ref: str,
) -> Mapping[str, Any]:
    try:
        movement, target = _movement_and_target_from_link_row(link_row)
    except (TypeError, ValueError):
        movement, target = "", ""
    route_plan = link_row.get("route_replay_plan")
    route_packet = _mapping_copy(route_plan)
    packet: dict[str, Any] = {
        "step_ref": step_ref,
        "edge_ref": edge_ref,
        "movement": movement,
        "target_ref": target,
        "declared_gate_refs": list(
            _text_tuple("link_row.declared_gate_refs", link_row.get("declared_gate_refs", ()))
        ),
        "route_replay_plan": route_packet,
    }
    if isinstance(route_packet, Mapping) and "max_attempts" in route_packet:
        packet["max_attempts"] = route_packet["max_attempts"]
    return packet


def _plan_step_mappings(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    values = plan.get("steps")
    if not isinstance(values, list):
        values = plan.get("brick_steps")
    if not isinstance(values, list):
        return ()
    return tuple(item for item in values if isinstance(item, Mapping))


def _step_rows(step: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return ()
    return tuple(row for row in rows if isinstance(row, Mapping))


def _mapping_copy(value: Any) -> dict[str, Any]:
    return _json_ready(value) if isinstance(value, Mapping) else {}


def _unique_texts(*values: Any) -> tuple[str, ...]:
    texts: list[str] = []
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                texts.append(stripped)
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            for item in value:
                if isinstance(item, str) and item.strip():
                    texts.append(item.strip())
    return tuple(dict.fromkeys(texts))


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(child) for child in value]
    if isinstance(value, list):
        return [_json_ready(child) for child in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _canonical_json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _plan_snapshot(plan_ref: str, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Build an EVIDENCE COPY of the declared Building Plan that was walked.

    P12 BUILDING-PLAN-DURABILITY: the Building evidence root records a content
    hash plus a canonical body copy of the declared plan so a future reviewer can
    confirm exactly which declared plan was walked. This is an evidence copy only
    -- support RECORDS it; the Brick-owned plan under brick/building_plans/ stays
    the source. The body is serialized as a single canonical (sorted-key) JSON
    string so the recorded copy carries no nested keys/values that could read as
    an authority claim, and the sha256 is taken over that exact canonical string
    so the hash is deterministic and re-derivable from the recorded copy.
    """

    plan_rows_copy = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    plan_hash = hashlib.sha256(plan_rows_copy.encode("utf-8")).hexdigest()
    return {
        "plan_ref": plan_ref,
        "plan_hash": plan_hash,
        "plan_hash_algorithm": "sha256",
        "plan_hash_basis": "canonical sorted-key JSON of the declared plan body",
        "plan_rows_copy": plan_rows_copy,
        "proof_limits": ["evidence copy only", "not source truth"],
    }
