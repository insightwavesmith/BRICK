"""COO/operator-loop/closure read projection (P3d concern module).

Drafts support-only closure material and the COO operating-chain / operator-loop
packets a human/COO fills. It records gap notes and forbidden-verdict hits; it
authors no verdict, chooses no Movement or target, and judges no success or
quality. Reaches no axis (reads design/agent context via the support.connection
toolkit, not an axis import)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from support.connection.agent_resources import AgentResourceError, render_agent_packet
from support.connection.building_design_toolkit import (
    BuildingDesignToolkitError,
    render_building_design_context,
)

from brick_protocol.support.operator.building_operation_common import (
    REPO_ROOT,
    _clean_text,
    _rel,
    _repo_path,
)
from brick_protocol.support.operator.checker_runner import (
    CheckerRun,
    open_preflight,
)
from brick_protocol.support.operator.evidence_status import (
    BuildingEvidenceAnalysis,
    EvidenceStatus,
    analyze_building_evidence,
    evidence_status,
)


COO_OPERATING_CHAIN_REQUIRED_TASK_HEADINGS: tuple[str, ...] = (
    "## Objective",
    "## First-Line Contract",
    "## Context / Why Now",
    "## Deep Intake Result",
    "## Required Sources",
    "## Desired Output",
    "## Brick / Agent / Link Boundary",
    "## Read Scope / Write Scope",
    "## Constraints / Out of Scope",
    "## Human / Review Gate",
    "## Honest Report Contract",
    "## Done Criteria",
    "## Risk",
    "## Proof Limits",
)


COO_OPERATING_CHAIN_HONEST_REPORT_FIELDS: tuple[str, ...] = (
    "observed_evidence",
    "made_changes",
    "blocked_or_missing_evidence",
    "open_questions",
    "not_proven",
    "remaining_delta",
    "review_needed",
    "transition_concern_evidence",
)


COO_OPERATING_CHAIN_DEEP_INTAKE_FIELDS: tuple[str, ...] = (
    "Trigger Event:",
    "User Context:",
    "Desired Information / Outcome:",
    "Current Workaround:",
    "Pain Points:",
    "Blocked Decisions:",
    "Primary Signals:",
    "Status Vocabulary:",
    "Required Actions:",
    "Forbidden Actions:",
)


COO_OPERATING_CHAIN_FORBIDDEN_VERDICT_FIELDS: tuple[str, ...] = (
    "success",
    "failure",
    "approved",
    "completed",
    "good_enough",
    "quality score",
    "route_target",
    "movement_choice",
    "target_ref",
)


COO_OPERATING_CHAIN_MCP_RESOURCE_URI = "brick-protocol://coo/operating-chain/context"


COO_OPERATING_CHAIN_MCP_TOOL = "brick_protocol_render_coo_operating_chain_context"


TASK_SOURCE_TEMPLATE_REF = "brick/templates/tasks/source-template.md"


def closure_draft(
    *,
    observed_evidence: Sequence[str],
    checker_runs: Sequence[CheckerRun] = (),
    evidence: EvidenceStatus | None = None,
    task_source_ref: str = "",
    plan_ref: str = "",
    step_output_refs: Sequence[str] = (),
    link_decision_refs: Sequence[str] = (),
    remaining_delta: Sequence[str] = (),
) -> Mapping[str, Any]:
    """Create a support-only closure draft for a human/COO to fill."""

    packet: dict[str, Any] = {
        "observed_evidence": [str(item) for item in observed_evidence],
        "checker_observations": [
            {
                "command": list(item.command),
                "return_code": item.return_code,
                "stdout_excerpt": item.stdout_excerpt,
                "stderr_excerpt": item.stderr_excerpt,
            }
            for item in checker_runs
        ],
        "evidence_status": None
        if evidence is None
        else {
            "building_root": evidence.building_root,
            "present_files": list(evidence.present_files),
            "missing_files": list(evidence.missing_files),
        },
        "coo_must_fill": [
            "narrowly_proven",
            "not_proven",
            "held",
            "COO Movement",
        ],
        "proof_limits": [
            "closure draft support evidence only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }
    if task_source_ref:
        packet["task_source_ref"] = _clean_text("task_source_ref", task_source_ref)
    if plan_ref:
        packet["plan_ref"] = _clean_text("plan_ref", plan_ref)
    if step_output_refs:
        packet["step_output_refs"] = [str(item) for item in step_output_refs]
    if link_decision_refs:
        packet["link_decision_refs"] = [str(item) for item in link_decision_refs]
    if remaining_delta:
        packet["remaining_delta"] = [str(item) for item in remaining_delta]
    return packet


def gap_note(
    *,
    issue: str,
    evidence_refs: Sequence[str],
    suggested_repair_building_ref: str = "",
) -> Mapping[str, Any]:
    """Create a support-only gap note without choosing Movement."""

    issue_text = _clean_text("issue", issue)
    refs = tuple(_clean_text("evidence_refs", item) for item in evidence_refs)
    if not issue_text or not refs:
        raise ValueError("gap notes require issue text and at least one evidence ref")
    return {
        "issue": issue_text,
        "evidence_refs": list(refs),
        "suggested_repair_building_ref": suggested_repair_building_ref,
        "proof_limits": [
            "gap note support evidence only",
            "repair target remains COO/Link boundary decision",
        ],
        "not_proven": [
            "root cause",
            "repair correctness",
            "Movement authority",
        ],
    }


def operator_loop_packet(
    *,
    plan_path: str | Path,
    building_root: str | Path,
    repo_root: Path | str = REPO_ROOT,
    building_id: str = "",
    checker_runs: Sequence[CheckerRun] = (),
    suggested_repair_building_ref: str = "",
    packet_ref: str = "building-operator-loop:building-operator-loop-0",
) -> Mapping[str, Any]:
    """Package support observations for one open/run/verify/close loop.

    This helper does not call ``support/operator/run.py``. The declared
    Building run must already be represented by the supplied evidence root.
    """

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    observed_building_id = building_id or root.name
    preflight = open_preflight(
        plan_path,
        repo_root=repo,
        building_id=observed_building_id,
        buildings_root=root.parent,
    )
    status = evidence_status(root, repo_root=repo)
    analysis = analyze_building_evidence(root, repo_root=repo)
    mechanical_gap_notes = _operator_loop_gap_notes(
        analysis,
        suggested_repair_building_ref=suggested_repair_building_ref,
    )
    closure = closure_draft(
        observed_evidence=(
            f"Building Plan observed: {preflight.plan_path}",
            f"Building evidence root observed: {status.building_root}",
            "runner surface remains brick_protocol.support.operator.run.run_building_plan",
            "operator helper packaged support evidence only",
        ),
        checker_runs=checker_runs,
        evidence=status,
    )
    return {
        "kind": "building_operator_loop_packet",
        "schema_version": "building-operator-loop-0",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "phases": [
            "open_preflight",
            "declared_run_observation",
            "evidence_check",
            "checker_observations",
            "closure_draft",
            "gap_notes",
        ],
        "open_preflight": {
            "plan_path": preflight.plan_path,
            "plan_exists": preflight.plan_exists,
            "evidence_root": preflight.evidence_root,
            "evidence_root_exists": preflight.evidence_root_exists,
            "proof_limits": list(preflight.proof_limits),
            "not_proven": list(preflight.not_proven),
        },
        "declared_run_observation": {
            "runner_surface": "brick_protocol.support.operator.run.run_building_plan",
            "building_root": status.building_root,
            "proof_limits": [
                "runner invocation is observed through evidence root only",
                "operator helper does not call the runner",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
        },
        "evidence_analysis": analysis.to_packet(),
        "checker_observations": [
            {
                "command": list(item.command),
                "return_code": item.return_code,
                "stdout_excerpt": item.stdout_excerpt,
                "stderr_excerpt": item.stderr_excerpt,
                "proof_limits": list(item.proof_limits),
            }
            for item in checker_runs
        ],
        "closure_draft": closure,
        "gap_notes": mechanical_gap_notes,
        "coo_must_fill": [
            "narrowly_proven",
            "not_proven",
            "held",
            "next Link-boundary decision",
        ],
        "proof_limits": [
            "operator loop support packet only",
            "not a runner",
            "not a route chooser",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "future Building correctness",
            "operator judgment correctness",
            "semantic correctness of evidence",
            "repair correctness",
            "provider quality",
        ],
    }


def coo_operating_chain_packet(
    *,
    task_source_ref: str | Path,
    selected_shape_ref: str = "",
    declared_by: str,
    active_plan_ref: str | Path,
    repo_root: Path | str = REPO_ROOT,
    building_root: str | Path | None = None,
    packet_ref: str = "coo-operating-chain:coo-operating-chain-0",
) -> Mapping[str, Any]:
    """Package support observations for COO task intake through closure.

    This helper only observes declared task / design / plan / evidence surfaces.
    It does not write task files, infer shape, author Building Plans, call the
    runner, choose Movement, choose route targets, or judge success/quality.
    """

    repo = Path(repo_root).resolve()
    # U5.1 fix: match the composer's fail-closed contract (composition.py). An
    # omitted/blank shape is OK (-> "" tag below); a PRESENT non-string value is a
    # MALFORMED declaration and must be REJECTED, not silently coerced to a repr.
    if selected_shape_ref is not None and not isinstance(selected_shape_ref, str):
        raise TypeError("selected_shape_ref must be text when provided")
    task_path = _repo_path(repo, task_source_ref)
    plan_path = _repo_path(repo, active_plan_ref)
    task_text = task_path.read_text(encoding="utf-8") if task_path.is_file() else ""
    task_placement = observe_task_source_placement(task_path, repo_root=repo)
    design_context = _safe_design_context(repo)
    coo_packet = _safe_coo_agent_packet(repo)
    shape_refs = tuple(str(item) for item in design_context.get("shape_refs", ()) if isinstance(item, str))
    skill_refs = tuple(
        str(item)
        for item in (
            coo_packet.get("agent_object", {}).get("skill_refs", ())
            if isinstance(coo_packet.get("agent_object"), Mapping)
            else ()
        )
        if isinstance(item, str)
    )
    missing_headings = tuple(
        heading for heading in COO_OPERATING_CHAIN_REQUIRED_TASK_HEADINGS if heading not in task_text
    )
    missing_honest_fields = tuple(
        field for field in COO_OPERATING_CHAIN_HONEST_REPORT_FIELDS if field not in task_text
    )
    missing_deep_intake_fields = tuple(
        field for field in COO_OPERATING_CHAIN_DEEP_INTAKE_FIELDS if field not in task_text
    )
    forbidden_verdict_hits = _forbidden_verdict_hits(task_text)
    mcp_observation = _coo_operating_chain_mcp_observation(repo)
    evidence_observation: Mapping[str, Any] | None = None
    if building_root is not None and str(building_root).strip():
        status = evidence_status(building_root, repo_root=repo)
        analysis = analyze_building_evidence(building_root, repo_root=repo)
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
    closure = closure_draft(
        observed_evidence=(
            f"Task source observed: {_rel(repo, task_path)}",
            f"Active plan observed: {_rel(repo, plan_path)}",
            "COO operating chain helper packaged support observations only",
            "MCP/toolkit context remains read-only support projection",
        ),
        evidence=None if evidence_observation is None else evidence_status(building_root, repo_root=repo),
        task_source_ref=_rel(repo, task_path),
        plan_ref=_rel(repo, plan_path),
    )
    return {
        "kind": "coo_operating_chain_packet",
        "schema_version": "coo-operating-chain-0",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "task_source_observation": {
            "task_source_ref": _rel(repo, task_path),
            "exists": task_path.is_file(),
            "placement": task_placement,
            "required_headings": list(COO_OPERATING_CHAIN_REQUIRED_TASK_HEADINGS),
            "missing_headings": list(missing_headings),
            "has_first_line_contract": "## First-Line Contract" in task_text,
            "has_deep_intake_result": "## Deep Intake Result" in task_text,
            "has_honest_report_contract": "## Honest Report Contract" in task_text,
            "has_brick_agent_link_boundary": "## Brick / Agent / Link Boundary" in task_text,
            "has_read_write_scope": "## Read Scope / Write Scope" in task_text,
            "deep_intake_fields": list(COO_OPERATING_CHAIN_DEEP_INTAKE_FIELDS),
            "missing_deep_intake_fields": list(missing_deep_intake_fields),
            "honest_report_fields": list(COO_OPERATING_CHAIN_HONEST_REPORT_FIELDS),
            "missing_honest_report_fields": list(missing_honest_fields),
            "forbidden_verdict_hits": list(forbidden_verdict_hits),
        },
        "design_context_observation": {
            "kind": design_context.get("kind", ""),
            "selection_rule": design_context.get("selection_rule", ""),
            "shape_refs": list(shape_refs),
            "toolkit_ref": "support/connection/building_design_toolkit.py::render_building_design_context",
            "proof_limits": design_context.get("proof_limits", []),
            "not_proven": design_context.get("not_proven", []),
        },
        "mcp_context_observation": mcp_observation,
        "coo_agent_resource_observation": {
            "agent_object_ref": coo_packet.get("agent_object", {}).get("object_ref", "")
            if isinstance(coo_packet.get("agent_object"), Mapping)
            else "",
            "skill_refs": list(skill_refs),
            "has_task_intake_skill": "skill:task_intake" in skill_refs,
            "proof_limits": coo_packet.get("proof_limits", []),
            "not_proven": coo_packet.get("not_proven", []),
        },
        "task_intake_observation": {
            "skill_ref": "skill:task_intake",
            "candidate_only": True,
            "must_not_declare_shape": True,
            "must_not_declare_plan": True,
            "must_not_choose_movement": True,
        },
        "shape_declaration_observation": {
            "selected_shape_ref": (selected_shape_ref or "").strip(),
            "declared_by": _clean_text("declared_by", declared_by),
            "selected_shape_in_registry": selected_shape_ref in shape_refs,
            "selection_rule": "caller_or_coo_declared_only",
        },
        "active_plan_observation": {
            "active_plan_ref": _rel(repo, plan_path),
            "exists": plan_path.is_file(),
            "plan_is_brick_owned": _rel(repo, plan_path).startswith("brick/building_plans/"),
        },
        "building_evidence_observation": evidence_observation,
        "closure_packet": closure,
        "mechanical_gap_notes": _coo_operating_chain_gap_notes(
            task_path=task_path,
            plan_path=plan_path,
            missing_headings=missing_headings,
            missing_honest_fields=missing_honest_fields,
            missing_deep_intake_fields=missing_deep_intake_fields,
            forbidden_verdict_hits=forbidden_verdict_hits,
            has_task_intake_skill="skill:task_intake" in skill_refs,
            mcp_observation=mcp_observation,
            repo=repo,
        ),
        "proof_limits": [
            "COO operating chain packet is support evidence only",
            "not task authoring",
            "not automatic shape selection",
            "not Building Plan authoring",
            "not runner invocation",
            "not route target choice",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of future task sources",
            "semantic fitness of selected shape",
            "future Building Plan correctness",
            "future Agent or provider quality",
            "future reviewer Movement decision correctness",
        ],
    }


def observe_task_source_placement(
    task_source_ref: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Classify task-source placement without granting task text authority."""

    repo = Path(repo_root).resolve()
    task_path = _repo_path(repo, task_source_ref)
    rel_path = _rel(repo, task_path)
    path_parts = Path(rel_path).parts
    is_building_task = (
        len(path_parts) >= 6
        and path_parts[:3] == ("project", "brick-protocol", "buildings")
        and path_parts[-2:] == ("work", "task.md")
    )
    is_template = rel_path == TASK_SOURCE_TEMPLATE_REF
    is_historical_brick_task = (
        path_parts[:2] == ("brick", "tasks")
        and rel_path.endswith(".md")
        and not is_template
    )
    if is_building_task:
        placement = "building_evidence_task"
    elif is_template:
        placement = "durable_template"
    elif is_historical_brick_task:
        placement = "historical_brick_tasks_instance"
    else:
        placement = "other"
    return {
        "task_source_ref": rel_path,
        "exists": task_path.is_file(),
        "placement": placement,
        "preferred_active_instance": is_building_task,
        "durable_template": is_template,
        "historical_brick_tasks_instance": is_historical_brick_task,
        "proof_limits": [
            "task source placement observation only",
            "not task authoring",
            "not plan authoring",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of task text",
            "Building Plan correctness",
            "future Agent return quality",
        ],
    }


def _safe_design_context(repo: Path) -> Mapping[str, Any]:
    try:
        return render_building_design_context(repo_root=repo)
    except BuildingDesignToolkitError as exc:
        return {
            "kind": "building-design-context-error",
            "error": str(exc),
            "shape_refs": [],
            "proof_limits": ["support observation only"],
            "not_proven": ["design context render"],
        }


def _safe_coo_agent_packet(repo: Path) -> Mapping[str, Any]:
    try:
        return render_agent_packet("coo", repo_root=repo)
    except AgentResourceError as exc:
        return {
            "kind": "agent-resource-packet-error",
            "error": str(exc),
            "agent_object": {},
            "proof_limits": ["support observation only"],
            "not_proven": ["COO Agent resource render"],
        }


def _coo_operating_chain_mcp_observation(repo: Path) -> Mapping[str, Any]:
    try:
        from support.connection.mcp_projection import (  # noqa: PLC0415
            mcp_projection_resources,
            mcp_projection_tools,
        )

        resources = mcp_projection_resources(repo_root=repo).get("resources", [])
        tools = mcp_projection_tools().get("tools", [])
    except Exception as exc:  # pragma: no cover - defensive support observation
        return {
            "resource_uri": COO_OPERATING_CHAIN_MCP_RESOURCE_URI,
            "tool_name": COO_OPERATING_CHAIN_MCP_TOOL,
            "resource_present": False,
            "tool_present": False,
            "error": str(exc),
            "proof_limits": ["MCP observation support evidence only"],
        }
    return {
        "resource_uri": COO_OPERATING_CHAIN_MCP_RESOURCE_URI,
        "tool_name": COO_OPERATING_CHAIN_MCP_TOOL,
        "resource_present": any(
            isinstance(item, Mapping) and item.get("uri") == COO_OPERATING_CHAIN_MCP_RESOURCE_URI
            for item in resources
        ),
        "tool_present": any(
            isinstance(item, Mapping) and item.get("name") == COO_OPERATING_CHAIN_MCP_TOOL
            for item in tools
        ),
        "proof_limits": ["MCP observation support evidence only"],
    }


def _forbidden_verdict_hits(text: str) -> tuple[str, ...]:
    text = _section_text(text, "## Honest Report Contract")
    hits: set[str] = set()
    skip_fenced_block = False
    previous_context = ""
    for line in text.splitlines():
        lowered = line.lower()
        if lowered.strip().startswith("```"):
            if skip_fenced_block:
                skip_fenced_block = False
            else:
                skip_fenced_block = any(
                    marker in previous_context
                    for marker in (
                        "forbidden verdict",
                        "must not include",
                        "must not return",
                        "do not include",
                        "do not return",
                    )
                )
            previous_context = lowered
            continue
        if skip_fenced_block:
            previous_context = lowered
            continue
        if any(
            marker in lowered
            for marker in (
                "forbidden",
                "do not",
                "must not",
                "must never",
                "not return",
                "not include",
                "should not",
                "not source truth",
                "proof limit",
                "judgment",
            )
        ):
            previous_context = lowered
            continue
        for field in COO_OPERATING_CHAIN_FORBIDDEN_VERDICT_FIELDS:
            if field.lower() in lowered:
                hits.add(field)
        if lowered.strip():
            previous_context = lowered
    return tuple(sorted(hits))


def _section_text(text: str, heading: str) -> str:
    lines = text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start_index = index + 1
            break
    if start_index is None:
        return ""
    collected: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith("## ") and stripped != heading:
            break
        collected.append(line)
    return "\n".join(collected)


def _coo_operating_chain_gap_notes(
    *,
    task_path: Path,
    plan_path: Path,
    missing_headings: Sequence[str],
    missing_honest_fields: Sequence[str],
    missing_deep_intake_fields: Sequence[str],
    forbidden_verdict_hits: Sequence[str],
    has_task_intake_skill: bool,
    mcp_observation: Mapping[str, Any],
    repo: Path,
) -> list[Mapping[str, Any]]:
    notes: list[Mapping[str, Any]] = []
    if not task_path.is_file():
        notes.append(gap_note(issue="COO task source is missing", evidence_refs=(_rel(repo, task_path),)))
    if missing_headings:
        notes.append(
            gap_note(
                issue="COO task source is missing required heading(s): " + ", ".join(missing_headings),
                evidence_refs=(_rel(repo, task_path),),
            )
        )
    if missing_honest_fields:
        notes.append(
            gap_note(
                issue="Honest report contract is missing field(s): " + ", ".join(missing_honest_fields),
                evidence_refs=(_rel(repo, task_path),),
            )
        )
    if missing_deep_intake_fields:
        notes.append(
            gap_note(
                issue="Deep intake result is missing field(s): " + ", ".join(missing_deep_intake_fields),
                evidence_refs=(_rel(repo, task_path),),
            )
        )
    if forbidden_verdict_hits:
        notes.append(
            gap_note(
                issue="Task source contains forbidden verdict field(s): " + ", ".join(forbidden_verdict_hits),
                evidence_refs=(_rel(repo, task_path),),
            )
        )
    if not has_task_intake_skill:
        notes.append(gap_note(issue="COO Agent Object does not reference skill:task_intake", evidence_refs=("agent/objects/coo.yaml",)))
    if not bool(mcp_observation.get("resource_present")) or not bool(mcp_observation.get("tool_present")):
        notes.append(gap_note(issue="COO operating chain MCP context is not fully exposed", evidence_refs=("support/connection/mcp_projection.py",)))
    if not plan_path.is_file():
        notes.append(gap_note(issue="Active Building Plan is missing", evidence_refs=(_rel(repo, plan_path),)))
    return notes


def _operator_loop_gap_notes(
    analysis: BuildingEvidenceAnalysis,
    *,
    suggested_repair_building_ref: str,
) -> list[Mapping[str, Any]]:
    if not analysis.mechanical_gap_flags:
        return []
    return [
        gap_note(
            issue=(
                "Mechanical Building evidence gap observed: "
                + ", ".join(analysis.mechanical_gap_flags)
            ),
            evidence_refs=(analysis.building_root,),
            suggested_repair_building_ref=suggested_repair_building_ref,
        )
    ]
