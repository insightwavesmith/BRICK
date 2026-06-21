"""coo_run_orchestration read packet (P3d concern module).

Assembles the COO run-orchestration packet (declared plan projection + evidence
analysis + closure draft + gap notes) over already-written evidence. It chooses
no Movement or target and judges no success or quality. Reaches no axis (composes
the other read-projection collaborators)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_BUILDINGS_ROOT,
    REPO_ROOT,
    _clean_text,
    _rel,
    _repo_path,
)
from brick_protocol.support.operator.composition_intent import render_declared_step_template_plan
from brick_protocol.support.operator.coo_operating_chain import (
    closure_draft,
    coo_operating_chain_packet,
)
from brick_protocol.support.operator.evidence_status import (
    analyze_building_evidence,
    evidence_status,
)
from brick_protocol.support.operator.plan_rendering import (
    _intent_uses_step_templates,
    _is_caller_or_coo_declaration,
    _validate_declared_plan_projection,
    render_declared_building_plan,
)


def coo_run_orchestration_packet(
    *,
    task_source_ref: str | Path,
    selected_shape_ref: str = "",
    declared_by: str,
    active_plan_ref: str | Path | None = None,
    declared_plan_intent: Mapping[str, Any] | None = None,
    building_root: str | Path | None = None,
    run_declared_plan: bool = False,
    repo_root: Path | str = REPO_ROOT,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, Any] | None = None,
    command_runner: Any | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    packet_ref: str = "coo-run-orchestration:coo-run-orchestration-0",
) -> Mapping[str, Any]:
    """Operate a declared COO task/plan/run/evidence loop as support evidence.

    This helper may call ``support/operator/run.py`` only when the caller gives
    a declared plan path or fully declared plan intent. It does not derive a
    plan from task text, choose Movement, infer targets, or judge the run.
    """

    repo = Path(repo_root).resolve()
    task_path = _repo_path(repo, task_source_ref)
    declared_by_text = _clean_text("declared_by", declared_by)
    if not _is_caller_or_coo_declaration(declared_by_text):
        raise ValueError("declared_by must record caller / COO declaration")
    # U5.1 fix: match the composer's fail-closed contract (composition.py
    # render_declared_step_template_plan + compose_building). An omitted/blank shape is
    # OK (-> "" tag below); a PRESENT non-string value (list / dict / int) is a MALFORMED
    # declaration and must be REJECTED here, not silently coerced to its Python repr.
    if selected_shape_ref is not None and not isinstance(selected_shape_ref, str):
        raise TypeError("selected_shape_ref must be text when provided")
    if active_plan_ref is not None and declared_plan_intent is not None:
        raise ValueError("declare either active_plan_ref or declared_plan_intent, not both")
    if active_plan_ref is None and declared_plan_intent is None:
        raise ValueError("COO run orchestration requires a declared plan path or fully declared intent")

    rendered_plan: Mapping[str, Any] | None = None
    plan_input: Mapping[str, Any] | Path
    plan_observation: dict[str, Any]
    if declared_plan_intent is not None:
        if declared_plan_intent.get("steps") and _intent_uses_step_templates(declared_plan_intent):
            # U5/D5: selected_shape_ref is an optional tag and the caller/COO outer
            # declaration is authoritative. Mirror the non-step-template branch below:
            # render, then stamp the outer shape so the plan's provenance ALWAYS
            # matches the orchestration packet — whether the intent omitted, matched,
            # or conflicted with the outer shape (the conflict case otherwise let the
            # packet report one shape while the runner walked a plan tagged another).
            rendered_plan = render_declared_step_template_plan(declared_plan_intent, repo_root=repo)
            rendered_plan = dict(rendered_plan)
            rendered_plan["selected_shape_ref"] = (selected_shape_ref or "").strip()
        else:
            rendered_plan = render_declared_building_plan(declared_plan_intent)
            rendered_plan = dict(rendered_plan)
            rendered_plan["selected_shape_ref"] = (selected_shape_ref or "").strip()
            rendered_plan["declared_by"] = declared_by_text
            _validate_declared_plan_projection(rendered_plan)
        plan_input = rendered_plan
        active_plan_label = str(rendered_plan.get("plan_ref", "declared-plan:intent"))
        plan_observation = {
            "active_plan_ref": active_plan_label,
            "source": "fully_declared_intent",
            "exists": True,
            "rendered_in_memory": True,
        }
    else:
        plan_path = _repo_path(repo, active_plan_ref or "")
        plan_input = plan_path
        active_plan_label = _rel(repo, plan_path)
        plan_observation = {
            "active_plan_ref": active_plan_label,
            "source": "declared_plan_path",
            "exists": plan_path.is_file(),
            "rendered_in_memory": False,
        }
        if run_declared_plan and not plan_path.is_file():
            raise ValueError("run_declared_plan requires active_plan_ref to exist")

    run_observation: Mapping[str, Any] | None = None
    observed_building_root = building_root
    step_output_refs: tuple[str, ...] = ()
    link_decision_refs: tuple[str, ...] = ()
    if run_declared_plan:
        from support.operator.run import run_building_plan  # noqa: PLC0415

        result = run_building_plan(
            plan_input,
            output_root=output_root,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
        )
        output_root_path = _repo_path(repo, output_root)
        observed_building_root = output_root_path / result.building_id
        step_output_refs = _step_output_refs_from_building_map(result.building_map_packet)
        link_decision_refs = _link_decision_refs_from_building_map(result.building_map_packet)
        run_observation = {
            "runner_surface": "brick_protocol.support.operator.run.run_building_plan",
            "invoked": True,
            "building_id": result.building_id,
            "plan_ref": result.plan_ref,
            "written_files": [_rel(repo, path) for path in result.written_files],
            "capture_event_types": list(result.capture_event_types),
            "step_output_refs": list(step_output_refs),
            "link_decision_refs": list(link_decision_refs),
            "proof_limits": [
                "declared runner invocation support observation only",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": list(result.not_proven),
        }
    else:
        run_observation = {
            "runner_surface": "brick_protocol.support.operator.run.run_building_plan",
            "invoked": False,
            "proof_limits": [
                "orchestration packet did not invoke the runner",
                "declared plan observation only",
            ],
        }

    evidence_observation: Mapping[str, Any] | None = None
    if observed_building_root is not None and str(observed_building_root).strip():
        status = evidence_status(observed_building_root, repo_root=repo)
        analysis = analyze_building_evidence(observed_building_root, repo_root=repo)
        evidence_observation = {
            "status": {
                "building_root": status.building_root,
                "present_files": list(status.present_files),
                "missing_files": list(status.missing_files),
                "proof_limits": list(status.proof_limits),
                "not_proven": list(status.not_proven),
            },
            "analysis": analysis.to_packet(),
        }

    chain = coo_operating_chain_packet(
        task_source_ref=task_path,
        selected_shape_ref=selected_shape_ref,
        declared_by=declared_by_text,
        active_plan_ref=active_plan_label if active_plan_ref is not None else "brick/building_plans/in-memory-declared-plan.yaml",
        repo_root=repo,
        building_root=observed_building_root,
    )
    return {
        "kind": "coo_run_orchestration_packet",
        "schema_version": "coo-run-orchestration-0",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "task_source_observation": chain["task_source_observation"],
        "shape_declaration_observation": chain["shape_declaration_observation"],
        "active_plan_observation": plan_observation,
        "rendered_plan_observation": None
        if rendered_plan is None
        else {
            "plan_ref": rendered_plan.get("plan_ref", ""),
            "building_id": rendered_plan.get("building_id", ""),
            "step_count": len(rendered_plan.get("steps", ())),
            "ordinary_bal_rows": True,
        },
        "run_observation": run_observation,
        "building_evidence_observation": evidence_observation,
        "closure_packet": closure_draft(
            observed_evidence=(
                f"Task source observed: {_rel(repo, task_path)}",
                f"Declared plan observed: {active_plan_label}",
                "run_building_plan invoked only when run_declared_plan is true",
                "evidence analysis remains mechanical support projection",
            ),
            evidence=None if observed_building_root is None else evidence_status(observed_building_root, repo_root=repo),
            task_source_ref=_rel(repo, task_path),
            plan_ref=active_plan_label,
            step_output_refs=step_output_refs,
            link_decision_refs=link_decision_refs,
        ),
        "mechanical_gap_notes": _orchestration_gap_notes(
            chain["mechanical_gap_notes"],
            rendered_plan_observed=rendered_plan is not None,
        ),
        "proof_limits": [
            "COO run orchestration packet is support evidence only",
            "not task authoring",
            "not automatic shape selection",
            "not Building Plan authoring from task text",
            "not route target choice",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of task source",
            "semantic fitness of selected shape, chain preset, or step template",
            "Agent or provider quality",
            "future reviewer Movement decision correctness",
            "production runtime readiness",
        ],
    }


def _orchestration_gap_notes(
    notes: Sequence[Mapping[str, Any]],
    *,
    rendered_plan_observed: bool,
) -> list[Mapping[str, Any]]:
    if not rendered_plan_observed:
        return list(notes)
    return [
        note
        for note in notes
        if note.get("issue") != "Active Building Plan is missing"
    ]


def _step_output_refs_from_building_map(packet: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for binding in packet.get("agent_bindings", ()):
        if isinstance(binding, Mapping):
            ref = binding.get("step_output_ref")
            if isinstance(ref, str) and ref.strip() and ref.strip() not in refs:
                refs.append(ref.strip())
    return tuple(refs)


def _link_decision_refs_from_building_map(packet: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for edge in packet.get("link_edges", ()):
        if not isinstance(edge, Mapping):
            continue
        for key in ("movement_fact_ref", "transition_fact_ref"):
            ref = edge.get(key)
            if isinstance(ref, str) and ref.strip() and ref.strip() not in refs:
                refs.append(ref.strip())
    return tuple(refs)
