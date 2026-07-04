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
import os
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
    "work/declared-building-plan.rev-*.json",
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

_DECLARED_PLAN_REVISION_PREFIX = "declared-building-plan.rev-"
_DECLARED_PLAN_REVISION_SUFFIX = ".json"
_DECLARED_PLAN_REVISION_HOLDS = "declared-building-plan.revision-holds.jsonl"
_EXPANSION_APPROVAL_REF = "link-gate:expansion-approval"
_EXPANSION_APPROVAL_HOLD_WHITELIST = frozenset(
    {
        "human_or_coo_gate_pause",
        "proposed_candidate_not_in_declared_set",
        "no_declared_candidate_proposed",
    }
)

_DECLARED_PLAN_REVISION_READER_DISPOSITION_ROWS: tuple[Mapping[str, str], ...] = (
    {
        "path": "support/operator/walker_resume.py",
        "reader": "_declared_graph_plan_from_birth_certificate",
        "disposition": "converted",
        "reason": "execution/resume graph plan read uses latest_valid_declared_plan",
    },
    {
        "path": "support/recording/spine_projection.py",
        "reader": "_declared_plan_steps/_declared_link_edges/_declared_execution_order",
        "disposition": "converted",
        "reason": "spine ORPHAN-SKIP cannot defer; projector reads latest valid revision packet",
    },
    {
        "path": "support/checkers/check_evidence_spine_projection.py",
        "reader": "_declared_plan_step_refs revision fixture",
        "disposition": "converted",
        "reason": "checker reuses projector readers and pins a rev-introduced step_ref fixture",
    },
    {
        "path": "support/operator/evidence_assembly.py",
        "reader": "_write_declaration_work_evidence caller",
        "disposition": "base_preserved_by_callee",
        "reason": "shared declaration writer preserves existing declared-building-plan.json",
    },
    {
        "path": "support/recording/adapter_error_frontier.py",
        "reader": "_write_declaration_work_evidence caller",
        "disposition": "base_preserved_by_callee",
        "reason": "adapter-error re-entry writes through the idempotent shared declaration writer",
    },
    {
        "path": "support/operator/walker_carry.py",
        "reader": "_write_declaration_work_evidence caller",
        "disposition": "base_preserved_by_callee",
        "reason": "carry re-materialization writes through the idempotent shared declaration writer",
    },
    {
        "path": "support/operator/run.py",
        "reader": "chat-session parked resume declared plan read",
        "disposition": "deferred_write_scope_forbidden",
        "reason": "this Brick write_scope forbids support/operator/run.py mutation",
    },
    {
        "path": "support/operator/reporter.py",
        "reader": "_declared_plan_for_building/_declared_plan_packet",
        "disposition": "deferred_output_contract",
        "reason": "report packet output-contract change belongs to a later declared reader-fanout slice",
    },
    {
        "path": "support/operator/onboard.py",
        "reader": "summary declared_plan_copy read",
        "disposition": "deferred_output_contract",
        "reason": "onboard summary output-contract change belongs to a later declared reader-fanout slice",
    },
    {
        "path": "support/operator/cli.py",
        "reader": "summary declared_plan_copy read",
        "disposition": "deferred_output_contract",
        "reason": "CLI summary output-contract change belongs to a later declared reader-fanout slice",
    },
    {
        "path": "support/operator/driver.py",
        "reader": "portfolio declared plan path readers",
        "disposition": "deferred_different_surface",
        "reason": "driver reads caller-declared candidate plan files, not Building-root rev packets in this slice",
    },
    {
        "path": "support/operator/native_dispatch.py",
        "reader": "fixture/projection declared-plan comments",
        "disposition": "deferred_no_active_reader_change",
        "reason": "observed surface does not consume Building-root rev packets for S2 execution/projection",
    },
    {
        "path": "support/operator/evidence_status.py",
        "reader": "declared-building-plan marker list",
        "disposition": "base_marker_preserved",
        "reason": "status marker intentionally remains on the immutable base birth-certificate",
    },
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


def declared_plan_revision_reader_disposition_rows() -> tuple[Mapping[str, str], ...]:
    """Return D6 reader disposition evidence for the rev-packet landing slice.

    The rows are support evidence only. They do not decide Movement, source truth,
    success, quality, or whether a deferred reader must be adopted later.
    """

    return _DECLARED_PLAN_REVISION_READER_DISPOSITION_ROWS


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
        text = _canonical_json_text(packet)
        if filename == "declared-building-plan.json" and path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == text:
                written.append(path)
                continue
            # Re-materialization may re-enter an already-preserved Building root
            # through adapter-error/carry surfaces. Preserve the original
            # birth-certificate and let the caller record the new runtime evidence
            # elsewhere; support must not clobber the base declaration.
            written.append(path)
            continue
        else:
            path.write_text(text, encoding="utf-8")
        written.append(path)
    return tuple(written)


def write_declared_plan_revision(
    root: Path | str,
    expanded_plan: Mapping[str, Any],
    expansion_metadata: Mapping[str, Any],
    approval_evidence_ref: str,
) -> Path:
    """Append a declared-plan revision packet after author-time pre-verification.

    Support records the already-approved expanded declaration as a new
    ``work/declared-building-plan.rev-N.json`` file. It does not choose Movement,
    select a target, or alter the base birth-certificate.
    """

    building_root = Path(root)
    work_dir = building_root / "work"
    base_packet = _load_declared_plan_packet(work_dir / "declared-building-plan.json")
    previous_packet = latest_valid_declared_plan_packet(building_root)
    previous_plan = _declared_plan_from_packet(previous_packet)
    raw_expanded_plan = _json_ready(expanded_plan)
    plan_copy = _pure_declared_plan_copy(expanded_plan)
    expansion_fragment = _mapping_copy(expansion_metadata.get("expansion_fragment"))
    if not expansion_fragment:
        expansion_fragment = _expansion_fragment_from_metadata(expansion_metadata)
    expansion_node_budgets = _positive_int_mapping(
        "expansion_node_budgets",
        expansion_metadata.get("expansion_node_budgets"),
    )

    _preverify_declared_plan_revision(
        building_root=building_root,
        base_plan=_declared_plan_from_packet(base_packet),
        previous_plan=previous_plan,
        expanded_plan=raw_expanded_plan,
        expansion_metadata=expansion_metadata,
        expansion_fragment=expansion_fragment,
        expansion_node_budgets=expansion_node_budgets,
        approval_evidence_ref=approval_evidence_ref,
    )

    canonical = _canonical_plan_hash_text(plan_copy)
    packet = {
        "kind": "declared_building_plan_provenance",
        "building_id": _plan_text(plan_copy, "building_id") or str(base_packet.get("building_id") or ""),
        "plan_ref": _plan_text(plan_copy, "plan_ref") or str(base_packet.get("plan_ref") or ""),
        "plan_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "plan_hash_algorithm": "sha256",
        "plan_hash_basis": (
            "canonical sorted-key JSON of the pure declared-building-plan copy "
            "(runtime walker state excluded)"
        ),
        "declared_plan_copy": plan_copy,
        "extends_plan_hash": _required_text(
            "expansion_metadata.extends_plan_hash",
            expansion_metadata.get("extends_plan_hash"),
        ),
        "extends_plan_hash_algorithm": str(
            expansion_metadata.get("extends_plan_hash_algorithm") or "sha256"
        ),
        "extends_plan_hash_basis": str(
            expansion_metadata.get("extends_plan_hash_basis")
            or "canonical sorted-key JSON of the pure declared-building-plan copy (runtime walker state excluded)"
        ),
        "expansion_fragment": expansion_fragment,
        "expansion_node_budgets": expansion_node_budgets,
        "approval_evidence_ref": approval_evidence_ref,
        "proof_limits": list(_DECLARATION_PROOF_LIMITS),
        "not_proven": [
            "declared plan semantic correctness",
            "future Agent or provider behavior",
        ],
    }
    rev_path = work_dir / f"{_DECLARED_PLAN_REVISION_PREFIX}{_next_revision_number(work_dir)}{_DECLARED_PLAN_REVISION_SUFFIX}"
    _write_exclusive_json_packet(rev_path, packet)
    return rev_path


def latest_valid_declared_plan(root: Path | str) -> Mapping[str, Any]:
    """Return the latest declared plan whose revision chain verifies."""

    return _declared_plan_from_packet(latest_valid_declared_plan_packet(Path(root)))


def latest_valid_declared_plan_packet(root: Path | str) -> Mapping[str, Any]:
    """Return the base or latest valid revision packet for a Building root.

    A torn newest revision is treated as an incomplete append attempt: readers
    retreat to the prior verified packet instead of hard-failing and dropping the
    whole birth-certificate read path. Strict validation remains the checker's
    job; this helper is the read-side "latest usable" surface.
    """

    work_dir = Path(root) / "work"
    base_packet = _load_declared_plan_packet(work_dir / "declared-building-plan.json")
    packets = [base_packet]
    expected_parent_hash = str(base_packet.get("plan_hash") or "")
    for rev_path in _revision_paths(work_dir):
        try:
            packet = _load_declared_plan_packet(rev_path)
        except ValueError as exc:
            _record_declared_plan_revision_hold(work_dir, rev_path, expected_parent_hash, str(exc))
            continue
        observed_parent_hash = str(packet.get("extends_plan_hash") or "")
        if observed_parent_hash != expected_parent_hash:
            _record_declared_plan_revision_hold(
                work_dir,
                rev_path,
                expected_parent_hash,
                "extends_plan_hash does not match the previous valid plan_hash",
            )
            continue
        packets.append(packet)
        expected_parent_hash = str(packet.get("plan_hash") or "")
    return packets[-1]


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
    canonical = _canonical_plan_hash_text(plan_copy)
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


def _preverify_declared_plan_revision(
    *,
    building_root: Path,
    base_plan: Mapping[str, Any],
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
    expansion_metadata: Mapping[str, Any],
    expansion_fragment: Mapping[str, Any],
    expansion_node_budgets: Mapping[str, int],
    approval_evidence_ref: str,
) -> None:
    previous_hash = _declared_plan_hash(previous_plan)
    extends_hash = _required_text(
        "expansion_metadata.extends_plan_hash",
        expansion_metadata.get("extends_plan_hash"),
    )
    if extends_hash != previous_hash:
        raise ValueError(
            "expansion_metadata.extends_plan_hash must match the current latest "
            "declared plan hash"
        )
    if "expansion_node_budgets" in expanded_plan:
        raise ValueError("expanded plan body must not carry expansion_node_budgets")
    _verify_approval_record(building_root, approval_evidence_ref, expansion_metadata)
    _verify_expansion_budget_available(base_plan, building_root)
    _verify_add_only_revision(previous_plan, expanded_plan)
    _verify_immutable_budget_fields(base_plan, previous_plan, expanded_plan)
    _verify_expansion_node_budgets(
        previous_plan,
        expanded_plan,
        expansion_node_budgets=expansion_node_budgets,
    )
    _verify_expansion_fragment_keys(expansion_fragment)


def _verify_approval_record(
    building_root: Path,
    approval_evidence_ref: str,
    expansion_metadata: Mapping[str, Any],
) -> None:
    ref = _required_text("approval_evidence_ref", approval_evidence_ref)
    expected_hold_ref = _approval_hold_identity(expansion_metadata)
    approval_path = building_root / "work" / "expansion-approvals.jsonl"
    if not approval_path.is_file():
        raise ValueError("work/expansion-approvals.jsonl approval evidence is required")
    for index, line in enumerate(approval_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{approval_path}:{index}: approval row is not valid JSON") from exc
        if not isinstance(row, Mapping):
            raise ValueError(f"{approval_path}:{index}: approval row is not a JSON object")
        row_ref = _optional_text_or_none(row.get("approval_evidence_ref")) or _optional_text_or_none(
            row.get("evidence_ref")
        )
        if row_ref != ref:
            continue
        gate_ref = _optional_text_or_none(row.get("gate_ref")) or _optional_text_or_none(
            row.get("declared_gate_ref")
        )
        if gate_ref != _EXPANSION_APPROVAL_REF:
            raise ValueError(
                f"{approval_path}:{index}: approval row must carry gate_ref "
                f"{_EXPANSION_APPROVAL_REF!r}"
            )
        hold_class = _optional_text_or_none(row.get("hold_class"))
        if hold_class and hold_class not in _EXPANSION_APPROVAL_HOLD_WHITELIST:
            raise ValueError(f"{approval_path}:{index}: hold_class {hold_class!r} is not whitelisted")
        row_hold_ref = _approval_row_hold_identity(row)
        if row_hold_ref != expected_hold_ref:
            raise ValueError(
                f"{approval_path}:{index}: approval row hold identity must echo "
                "expansion_metadata.hold_paused_at_ref"
            )
        _verify_approval_not_consumed(building_root, ref)
        return
    raise ValueError(f"approval_evidence_ref {ref!r} was not found in work/expansion-approvals.jsonl")


def _verify_approval_not_consumed(building_root: Path, approval_evidence_ref: str) -> None:
    for packet in _valid_revision_chain_packets(building_root)[1:]:
        prior_ref = _optional_text_or_none(packet.get("approval_evidence_ref"))
        if prior_ref == approval_evidence_ref:
            raise ValueError(
                f"approval_evidence_ref {approval_evidence_ref!r} already authorized "
                "a declared plan revision"
            )


def _approval_hold_identity(expansion_metadata: Mapping[str, Any]) -> str:
    return _required_text(
        "expansion_metadata.hold_paused_at_ref",
        expansion_metadata.get("hold_paused_at_ref")
        or expansion_metadata.get("paused_at_ref")
        or expansion_metadata.get("resumed_from_ref"),
    )


def _approval_row_hold_identity(row: Mapping[str, Any]) -> str | None:
    return (
        _optional_text_or_none(row.get("hold_paused_at_ref"))
        or _optional_text_or_none(row.get("paused_at_ref"))
        or _optional_text_or_none(row.get("resumed_from_ref"))
    )


def _verify_expansion_budget_available(base_plan: Mapping[str, Any], building_root: Path) -> None:
    budget = base_plan.get("expansion_budget", 0)
    if not isinstance(budget, int) or budget <= 0:
        raise ValueError("base declared plan expansion_budget must be a positive integer")
    used = max(0, len(_valid_revision_chain_packets(building_root)) - 1)
    if used >= budget:
        raise ValueError("base declared plan expansion_budget is exhausted")


def _verify_add_only_revision(
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
) -> None:
    for key in ("brick_steps", "steps"):
        if key in previous_plan or key in expanded_plan:
            _verify_append_only_list(key, previous_plan.get(key), expanded_plan.get(key), "step_ref")
    if "link_edges" in previous_plan or "link_edges" in expanded_plan:
        _verify_append_only_list(
            "link_edges",
            previous_plan.get("link_edges"),
            expanded_plan.get("link_edges"),
            "edge_ref",
        )
    _verify_execution_order_append_only(previous_plan, expanded_plan)
    _verify_groups_append_only(previous_plan, expanded_plan)


def _verify_append_only_list(key: str, previous: Any, expanded: Any, ref_key: str) -> None:
    previous_list = previous if isinstance(previous, list) else []
    expanded_list = expanded if isinstance(expanded, list) else []
    previous_by_ref = _mapping_list_by_ref(key, previous_list, ref_key)
    expanded_by_ref = _mapping_list_by_ref(key, expanded_list, ref_key)
    missing = sorted(set(previous_by_ref) - set(expanded_by_ref))
    if missing:
        raise ValueError(f"{key} revision deleted existing {ref_key}(s): " + ", ".join(missing))
    changed = sorted(
        ref
        for ref, item in previous_by_ref.items()
        if expanded_by_ref.get(ref) != item
    )
    if changed:
        raise ValueError(f"{key} revision changed existing {ref_key}(s): " + ", ".join(changed))


def _verify_execution_order_append_only(
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
) -> None:
    previous = previous_plan.get("execution_order") or []
    expanded = expanded_plan.get("execution_order") or []
    if not isinstance(previous, list) or not isinstance(expanded, list):
        raise ValueError("execution_order must be a list when present")
    if expanded[: len(previous)] != previous:
        raise ValueError("execution_order revision must append after the previous order")


def _verify_groups_append_only(
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
) -> None:
    previous_groups = previous_plan.get("groups") or []
    expanded_groups = expanded_plan.get("groups") or []
    if not isinstance(previous_groups, list) or not isinstance(expanded_groups, list):
        raise ValueError("groups must be a list when present")
    previous_by_id = _mapping_list_by_ref("groups", previous_groups, "group_id")
    expanded_by_id = _mapping_list_by_ref("groups", expanded_groups, "group_id")
    for group_id, previous_group in previous_by_id.items():
        expanded_group = expanded_by_id.get(group_id)
        if expanded_group is None:
            raise ValueError(f"groups revision deleted existing group_id: {group_id}")
        previous_members = previous_group.get("member_refs") or []
        expanded_members = expanded_group.get("member_refs") or []
        if not isinstance(previous_members, list) or not isinstance(expanded_members, list):
            raise ValueError(f"groups[{group_id}].member_refs must be a list")
        if expanded_members[: len(previous_members)] != previous_members:
            raise ValueError(f"groups[{group_id}].member_refs must append without changing existing refs")
        comparable_previous = dict(previous_group)
        comparable_expanded = dict(expanded_group)
        comparable_previous["member_refs"] = []
        comparable_expanded["member_refs"] = []
        if comparable_previous != comparable_expanded:
            raise ValueError(f"groups revision changed existing group_id metadata: {group_id}")


def _verify_immutable_budget_fields(
    base_plan: Mapping[str, Any],
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
) -> None:
    if "node_reroute_budgets" in expanded_plan:
        raise ValueError("revision expanded plan must not carry node_reroute_budgets")
    key = "expansion_budget"
    if expanded_plan.get(key) != previous_plan.get(key):
        raise ValueError(f"revision must not change existing {key}")
    if previous_plan.get(key) != base_plan.get(key):
        raise ValueError(f"prior revision already changed base {key}")


def _verify_expansion_node_budgets(
    previous_plan: Mapping[str, Any],
    expanded_plan: Mapping[str, Any],
    *,
    expansion_node_budgets: Mapping[str, int],
) -> None:
    previous_refs = _plan_step_refs(previous_plan)
    expanded_refs = _plan_step_refs(expanded_plan)
    new_refs = expanded_refs - previous_refs
    unknown = sorted(set(expansion_node_budgets) - new_refs)
    if unknown:
        raise ValueError("expansion_node_budgets must reference only new step_ref values: " + ", ".join(unknown))
    missing = sorted(new_refs - set(expansion_node_budgets))
    if missing:
        raise ValueError("expansion_node_budgets must cover every new step_ref: " + ", ".join(missing))


def _verify_expansion_fragment_keys(expansion_fragment: Mapping[str, Any]) -> None:
    allowed = {"brick_steps", "link_edges", "execution_order", "groups", "expansion_node_budgets"}
    unknown = sorted(str(key) for key in expansion_fragment if str(key) not in allowed)
    if unknown:
        raise ValueError("expansion_fragment contains unknown key(s): " + ", ".join(unknown))


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


def _declared_plan_hash(plan: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_plan_hash_text(_pure_declared_plan_copy(plan)).encode("utf-8")).hexdigest()


def _canonical_plan_hash_text(plan_copy: Mapping[str, Any]) -> str:
    return json.dumps(
        _json_ready(plan_copy),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _load_declared_plan_packet(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{path}: declared plan packet is not readable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: declared plan packet is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: declared plan packet is not a JSON object")
    if value.get("kind") != "declared_building_plan_provenance":
        raise ValueError(f"{path}: declared plan packet kind is not declared_building_plan_provenance")
    _validate_packet_plan_hash(path, value)
    return value


def _declared_plan_from_packet(packet: Mapping[str, Any]) -> Mapping[str, Any]:
    plan = packet.get("declared_plan_copy")
    if not isinstance(plan, Mapping):
        raise ValueError("declared plan packet declared_plan_copy is not a JSON object")
    return plan


def _validate_packet_plan_hash(path: Path, packet: Mapping[str, Any]) -> None:
    plan = packet.get("declared_plan_copy")
    if not isinstance(plan, Mapping):
        raise ValueError(f"{path}: declared_plan_copy is not a JSON object")
    expected = str(packet.get("plan_hash") or "")
    observed = _declared_plan_hash(plan)
    if not expected:
        raise ValueError(f"{path}: plan_hash is missing")
    if expected != observed:
        raise ValueError(f"{path}: plan_hash does not match declared_plan_copy")


def _revision_paths(work_dir: Path) -> tuple[Path, ...]:
    paths: list[tuple[int, Path]] = []
    for path in work_dir.glob(f"{_DECLARED_PLAN_REVISION_PREFIX}*{_DECLARED_PLAN_REVISION_SUFFIX}"):
        number = _revision_number(path)
        if number is not None:
            paths.append((number, path))
    return tuple(path for _number, path in sorted(paths))


def _valid_revision_chain_packets(root: Path | str) -> tuple[Mapping[str, Any], ...]:
    work_dir = Path(root) / "work"
    base_packet = _load_declared_plan_packet(work_dir / "declared-building-plan.json")
    packets: list[Mapping[str, Any]] = [base_packet]
    expected_parent_hash = str(base_packet.get("plan_hash") or "")
    for rev_path in _revision_paths(work_dir):
        try:
            packet = _load_declared_plan_packet(rev_path)
        except ValueError:
            continue
        if str(packet.get("extends_plan_hash") or "") != expected_parent_hash:
            continue
        packets.append(packet)
        expected_parent_hash = str(packet.get("plan_hash") or "")
    return tuple(packets)


def _record_declared_plan_revision_hold(
    work_dir: Path,
    rev_path: Path,
    expected_parent_hash: str,
    reason: str,
) -> None:
    hold_path = work_dir / _DECLARED_PLAN_REVISION_HOLDS
    record = {
        "kind": "declared_plan_revision_hold",
        "state": "paused",
        "progress_state": "in_progress",
        "revision_path": rev_path.relative_to(work_dir).as_posix(),
        "retreated_to_parent_plan_hash": expected_parent_hash,
        "reason": reason,
        "proof_limits": list(_DECLARATION_PROOF_LIMITS),
    }
    text = _canonical_json_text(record)
    if hold_path.exists():
        existing = hold_path.read_text(encoding="utf-8").splitlines()
        if text in existing:
            return
    with hold_path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _revision_number(path: Path) -> int | None:
    name = path.name
    if not name.startswith(_DECLARED_PLAN_REVISION_PREFIX) or not name.endswith(
        _DECLARED_PLAN_REVISION_SUFFIX
    ):
        return None
    raw = name[len(_DECLARED_PLAN_REVISION_PREFIX) : -len(_DECLARED_PLAN_REVISION_SUFFIX)]
    if not raw.isdigit():
        return None
    number = int(raw)
    return number if number >= 1 else None


def _next_revision_number(work_dir: Path) -> int:
    revisions = [_revision_number(path) for path in _revision_paths(work_dir)]
    numbers = [number for number in revisions if number is not None]
    return (max(numbers) + 1) if numbers else 1


def _write_exclusive_json_packet(path: Path, packet: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(_canonical_json_text(packet), encoding="utf-8")
    try:
        os.link(tmp, path)
    except FileExistsError as exc:
        raise ValueError(f"{path}: declared plan revision already exists") from exc
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _required_text(name: str, value: Any) -> str:
    text = _optional_text_or_none(value)
    if not text:
        raise ValueError(f"{name} must be a non-empty string")
    return text


def _positive_int_mapping(name: str, value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    result: dict[str, int] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{name} keys must be non-empty strings")
        if not isinstance(item, int) or item <= 0:
            raise ValueError(f"{name}.{key} must be a positive integer")
        result[key] = item
    return result


def _expansion_fragment_from_metadata(expansion_metadata: Mapping[str, Any]) -> dict[str, Any]:
    fragment = expansion_metadata.get("expansion_fragment")
    return _mapping_copy(fragment)


def _mapping_list_by_ref(name: str, values: Any, ref_key: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise ValueError(f"{name} must be a list when present")
    result: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise ValueError(f"{name}[{index}] must be a JSON object")
        ref = _required_text(f"{name}[{index}].{ref_key}", item.get(ref_key))
        if ref in result:
            raise ValueError(f"{name} contains duplicate {ref_key}: {ref}")
        result[ref] = _json_ready(item)
    return result


def _plan_step_refs(plan: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for step in _plan_step_mappings(plan):
        step_ref = _optional_text_or_none(step.get("step_ref"))
        if step_ref:
            refs.add(step_ref)
    return refs


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
