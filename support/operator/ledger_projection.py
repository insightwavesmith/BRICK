"""Project orchestration-ledger read projection + view (P3d concern module).

Reads already-written Building evidence into a dashboard-readable export and a
read-only markdown view. Not a dashboard runtime, not source truth, not a
scheduler; chooses no Movement and judges no success or quality. Reaches no
axis.

PROJECT-0 S4-A (multi-project): the ledger discovers EVERY declared project
vessel by loading ``project/<id>/project.json`` THROUGH
``load_project_declaration`` (the single S1 validator — never a raw glob+parse)
and projects each vessel's declared label/direction onto its rows. Building
membership stays a PATH fact (which vessel the evidence root physically lives
in); each vessel's buildings root derives through ``buildings_root_for``, THE
single project_ref -> buildings-root seam. No vessel path literal lives here:
project #1 is just one declared vessel among N.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_BUILDINGS_ROOT,
    REPO_ROOT,
    _clean_text,
    _jsonl_records,
    _read_json_mapping,
    _rel,
    _repo_path,
    _text_sequence,
)
from brick_protocol.support.operator.evidence_status import analyze_building_evidence
from brick_protocol.support.operator.frontier_observation import observe_building_frontier
from brick_protocol.support.operator.project_declaration import (
    ProjectDeclaration,
    load_project_declaration,
)
from brick_protocol.support.recording.capture import buildings_root_for


def discover_project_vessels(
    repo_root: Path | str = REPO_ROOT,
) -> tuple[ProjectDeclaration, ...]:
    """Every declared project vessel, loaded THROUGH the S1 declaration loader.

    PROJECT-0 S4-A: vessel discovery reads ``project/<id>/project.json`` via
    ``load_project_declaration`` only (the loader is the single validator; this
    module never raw-glob-and-parses a declaration). Fail-closed: a directory
    under ``project/`` that does not load as a declared vessel raises the
    loader's own rejection — an undeclared vessel is never silently skipped
    (the same no-silence posture the project_declaration kernel check enforces).
    """

    repo = Path(repo_root).resolve()
    project_root = repo / "project"
    if not project_root.is_dir():
        return ()
    declarations: list[ProjectDeclaration] = []
    for vessel_dir in sorted(project_root.iterdir()):
        if vessel_dir.is_dir():
            declarations.append(load_project_declaration(repo, vessel_dir.name))
    return tuple(declarations)


def _vessel_buildings_root(repo: Path, declaration: ProjectDeclaration) -> Path:
    """The vessel's buildings root, derived through THE single seam.

    ``buildings_root_for`` is REPO_ROOT-anchored; re-rooting its repo-relative
    tail under ``repo`` keeps the seam the only derivation while still serving
    callers that point at a different checkout/fixture tree.
    """

    return repo / buildings_root_for(declaration.project_ref).relative_to(REPO_ROOT)


def project_orchestration_ledger_packet(
    *,
    repo_root: Path | str = REPO_ROOT,
    participant_ref: str = "participant:smith",
    participant_label: str = "Smith",
    workspace_ref: str = "workspace:brick-protocol-local",
    home_project_ref: str | None = None,
    packet_ref: str = "project-orchestration-ledger:project-orchestration-ledger-0",
) -> Mapping[str, Any]:
    """Render ALL declared project vessels as one dashboard-readable export.

    This support view reads already-written Building evidence. It does not
    store source truth, create a dashboard runtime, choose Movement, infer
    route targets, or judge project success/quality.

    ``projects`` is the authoritative multi-vessel list (label/direction
    projected from each vessel's declared project.json). The single ``project``
    block is the legacy export-home slot: the vessel whose status/ directory
    homes a written copy of this packet (``home_project_ref``); when no home is
    declared it echoes the first declared vessel so the slot stays present for
    existing readers. The declared ``direction`` is the vessel's parent-goal
    slot (design §1: the closure parent_goal connection) — projected, never
    judged.
    """

    repo = Path(repo_root).resolve()
    participant = {
        "participant_ref": _clean_text("participant_ref", participant_ref),
        "participant_label": _clean_text("participant_label", participant_label),
        "workspace_ref": _clean_text("workspace_ref", workspace_ref),
    }
    vessels = discover_project_vessels(repo)
    if not vessels:
        raise ValueError(
            "no declared project vessel found — a project must declare its "
            "charter and direction (project.json) before the ledger can project it"
        )
    rows: list[Mapping[str, Any]] = []
    vessel_summaries: list[Mapping[str, Any]] = []
    project_blocks: dict[str, Mapping[str, str]] = {}
    for declaration in vessels:
        project = {
            "project_ref": declaration.project_ref,
            "project_label": declaration.label,
            # The declared direction IS the vessel's parent-goal slot
            # (project-0-design-0611 §1) — connected here, not judged.
            "project_direction": declaration.direction,
        }
        project_blocks[declaration.project_ref] = project
        root = _vessel_buildings_root(repo, declaration)
        vessel_rows = [
            _project_orchestration_ledger_row(
                repo,
                building_root,
                participant=participant,
                project=project,
            )
            for building_root in (
                sorted(path for path in root.iterdir() if path.is_dir())
                if root.is_dir()
                else ()
            )
        ]
        vessel_counters: dict[str, int] = {}
        for row in vessel_rows:
            board_state = str(row.get("board_state", "unknown"))
            vessel_counters[board_state] = vessel_counters.get(board_state, 0) + 1
        vessel_summaries.append(
            {
                **project,
                "declaration_ref": f"project/{declaration.project_id}/project.json",
                "buildings_root": _rel(repo, root),
                "row_count": len(vessel_rows),
                "state_counters": vessel_counters,
            }
        )
        rows.extend(vessel_rows)
    if home_project_ref is not None and home_project_ref not in project_blocks:
        raise ValueError(
            f"home_project_ref {home_project_ref!r} names no declared vessel — "
            f"declared: {', '.join(sorted(project_blocks))}"
        )
    home_block = project_blocks[
        home_project_ref if home_project_ref is not None else vessels[0].project_ref
    ]
    counters: dict[str, int] = {}
    for row in rows:
        board_state = str(row.get("board_state", "unknown"))
        counters[board_state] = counters.get(board_state, 0) + 1
    return {
        "kind": "project_orchestration_ledger",
        "schema_version": "project-orchestration-ledger-0",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": dict(home_block),
        "projects": vessel_summaries,
        "participants": [participant],
        "row_count": len(rows),
        "state_counters": counters,
        "rows": rows,
        "projection_targets": [
            "project operating ledger/export",
            "future dashboard projection reader input",
            "future participant aggregate import",
        ],
        "proof_limits": [
            "support projection only",
            "reads existing Building evidence roots only",
            "not source truth",
            "not project ledger owner",
            "not dashboard runtime",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not process liveness proof",
            "latest_movement is raw observed Link evidence only",
            "generated_at is the snapshot build time, not a liveness/freshness guarantee of any process",
            "last_evidence_at is the newest recorded Link evidence timestamp for that Building, not a process heartbeat",
            "project membership is the Building root's path fact; label/direction are projected from each vessel's declared project.json",
            "the single 'project' block is the export home-vessel slot; 'projects' is the authoritative multi-vessel list",
        ],
        "not_proven": [
            "semantic correctness of Building work",
            "whether a provider process is currently alive",
            "complete inventory outside the declared project vessels",
            "cross-participant synchronization",
            "shared project collaboration behavior",
            "dashboard UI readiness",
            "that generated_at reflects current process liveness rather than snapshot build time",
            "that last_evidence_at reflects provider liveness rather than newest recorded evidence",
        ],
    }


LEDGER_EXPORT_FILENAME = "project-orchestration-ledger.json"


def project_orchestration_ledger_export_path(project_ref: str) -> Path:
    """Per-vessel export home: ``<vessel>/status/<filename>``, seam-derived.

    PROJECT-0 S4-A: the export location derives from the vessel's buildings
    root through ``buildings_root_for`` (THE single seam) — no vessel path
    literal. Each declared vessel may home its own written copy of the packet.
    """

    return buildings_root_for(project_ref).parent / "status" / LEDGER_EXPORT_FILENAME


# Legacy ref-less alias: the default export home is the ref-less default
# vessel's status sibling — derived from DEFAULT_BUILDINGS_ROOT (itself
# seam-derived in capture.py), so no vessel path literal survives here either.
PROJECT_ORCHESTRATION_LEDGER_EXPORT = (
    (DEFAULT_BUILDINGS_ROOT.parent / "status" / LEDGER_EXPORT_FILENAME)
    .relative_to(REPO_ROOT)
    .as_posix()
)


def render_project_orchestration_ledger_view(
    *,
    packet: Mapping[str, Any] | None = None,
    export_path: Path | str | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> str:
    """Render the project orchestration ledger as a READ-ONLY human-readable view.

    This is the P15 DASHBOARD-READ-SIDE-VIEW consumer of the EXISTING ledger.
    It consumes an already-built packet/export and projects a deterministic
    markdown VIEW: per project/Building row -> current Brick ref, current Agent
    ref, Link latest movement/target/gate/disposition, frontier_kind/board_state,
    and evidence refs. It returns a string only.

    Precedence: a supplied ``packet`` is read first; otherwise an ``export_path``
    JSON is read; otherwise the live ``project_orchestration_ledger_packet`` is
    built over every declared project vessel. Either way this is a static view
    over already-written Building evidence.

    This view is not a dashboard runtime/server, not a scheduler, not source
    truth, does not write source truth back, does not choose Movement, does not
    infer route targets, does not judge success/quality, and does not prove that
    any provider process is currently alive. ``latest_movement`` is raw observed
    Link evidence only.
    """

    repo = Path(repo_root).resolve()
    if packet is not None:
        ledger: Mapping[str, Any] = packet
    elif export_path is not None:
        ledger = _read_json_mapping(_repo_path(repo, export_path))
        if not ledger:
            raise ValueError("export_path must be an existing project ledger export")
    else:
        ledger = project_orchestration_ledger_packet(repo_root=repo)

    project = ledger.get("project") if isinstance(ledger.get("project"), Mapping) else {}
    participants = ledger.get("participants")
    rows = ledger.get("rows")
    rows = list(rows) if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)) else []
    state_counters = (
        ledger.get("state_counters")
        if isinstance(ledger.get("state_counters"), Mapping)
        else {}
    )
    proof_limits = _text_sequence("proof_limits", ledger.get("proof_limits"))
    not_proven = _text_sequence("not_proven", ledger.get("not_proven"))

    lines: list[str] = []
    lines.append("# Project Orchestration Ledger View")
    lines.append("")
    lines.append(
        "READ-ONLY support projection over already-written Building evidence. "
        "This view is not a dashboard runtime, not a server, not source truth, "
        "not editable, and not a provider-liveness proof."
    )
    lines.append("")
    lines.append("## Projects (declared vessels)")
    vessel_summaries = ledger.get("projects")
    if isinstance(vessel_summaries, Sequence) and not isinstance(
        vessel_summaries, (str, bytes)
    ):
        for vessel in vessel_summaries:
            if not isinstance(vessel, Mapping):
                continue
            lines.append(
                f"- {vessel.get('project_ref', '')} ({vessel.get('project_label', '')})"
                f" — direction: {vessel.get('project_direction', '')}"
                f" — buildings_root: {vessel.get('buildings_root', '')}"
                f" — rows: {vessel.get('row_count', '')}"
            )
    if project:
        lines.append(
            "- export home vessel: "
            f"{project.get('project_ref', '')} ({project.get('project_label', '')})"
        )
    lines.append(f"- packet_ref: {ledger.get('packet_ref', '')}")
    lines.append(f"- row_count: {ledger.get('row_count', len(rows))}")
    if isinstance(participants, Sequence) and not isinstance(participants, (str, bytes)):
        for participant in participants:
            if isinstance(participant, Mapping):
                lines.append(
                    "- participant: "
                    f"{participant.get('participant_ref', '')} "
                    f"({participant.get('participant_label', '')})"
                )
    lines.append("")
    lines.append("## Board State Counters")
    if state_counters:
        for board_state in sorted(state_counters):
            lines.append(f"- {board_state}: {state_counters[board_state]}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Rows (current Brick / Agent / Link frontier)")
    lines.append("")
    header = (
        "| Building | Project | Current Brick | Current Agent | Link movement | "
        "Link target | Frontier | Board state | Evidence (building-map) |"
    )
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines.append(header)
    lines.append(divider)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        evidence_refs = (
            row.get("evidence_refs") if isinstance(row.get("evidence_refs"), Mapping) else {}
        )
        lines.append(
            "| "
            + " | ".join(
                _ledger_view_cell(value)
                for value in (
                    row.get("building_id") or row.get("building_ref"),
                    row.get("project_ref"),
                    row.get("current_brick_ref"),
                    row.get("current_agent_ref"),
                    row.get("latest_movement"),
                    row.get("current_link_target_ref"),
                    row.get("frontier_kind"),
                    row.get("board_state"),
                    evidence_refs.get("building_map"),
                )
            )
            + " |"
        )
    lines.append("")
    lines.append("## Row Detail")
    lines.append("")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        evidence_refs = (
            row.get("evidence_refs") if isinstance(row.get("evidence_refs"), Mapping) else {}
        )
        lines.append(f"### {row.get('building_ref') or row.get('building_id') or '(unknown)'}")
        lines.append(f"- project_ref: {_ledger_view_cell(row.get('project_ref'))}")
        lines.append(f"- current_brick_ref: {_ledger_view_cell(row.get('current_brick_ref'))}")
        lines.append(f"- current_agent_ref: {_ledger_view_cell(row.get('current_agent_ref'))}")
        lines.append(
            "- link latest_movement: "
            f"{_ledger_view_cell(row.get('latest_movement'))} "
            f"-> target {_ledger_view_cell(row.get('current_link_target_ref'))}"
        )
        lines.append(
            "- frontier_kind / board_state: "
            f"{_ledger_view_cell(row.get('frontier_kind'))} / "
            f"{_ledger_view_cell(row.get('board_state'))}"
        )
        lines.append(
            f"- frontier_reason: {_ledger_view_cell(row.get('frontier_reason'))}"
        )
        lines.append(
            f"- next_action_observation: {_ledger_view_cell(row.get('next_action_observation'))}"
        )
        lines.append("- evidence_refs:")
        if evidence_refs:
            for ref_key in sorted(evidence_refs):
                lines.append(f"  - {ref_key}: {_ledger_view_cell(evidence_refs[ref_key])}")
        else:
            lines.append("  - (none)")
        lines.append("")
    lines.append("## proof_limits")
    for limit in proof_limits:
        lines.append(f"- {limit}")
    lines.append("- read-only view: exposes no source-truth-edit surface")
    lines.append("")
    lines.append("## not_proven")
    for item in not_proven:
        lines.append(f"- {item}")
    if "whether a provider process is currently alive" not in not_proven:
        lines.append("- whether a provider process is currently alive")
    lines.append("")
    return "\n".join(lines)


def _ledger_view_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("|", "\\|").replace("\n", " ").strip()
    return text if text else "-"


def _project_orchestration_ledger_row(
    repo: Path,
    building_root: Path,
    *,
    participant: Mapping[str, str],
    project: Mapping[str, str],
) -> Mapping[str, Any]:
    analysis = analyze_building_evidence(building_root, repo_root=repo)
    frontier = observe_building_frontier(building_root, repo_root=repo)
    building_map = _read_json_mapping(building_root / "work" / "building-map.json")
    building_work = _read_json_mapping(building_root / "work" / "building-work.json")
    latest_binding = _latest_mapping(building_map.get("agent_bindings"))
    latest_edge = _latest_mapping(building_map.get("link_edges"))
    link_records = _jsonl_records(building_root / "raw" / "link.jsonl")
    latest_link = _latest_mapping(link_records)
    frontier_kind = str(frontier.get("frontier_kind") or "unknown")
    board_state = _project_ledger_board_state(frontier_kind)
    link_disposition = _project_ledger_link_disposition(frontier.get("latest_transition_lifecycle"))
    last_evidence_at = _project_ledger_last_evidence_at(link_records)
    return {
        "participant_ref": participant["participant_ref"],
        "participant_label": participant["participant_label"],
        "workspace_ref": participant["workspace_ref"],
        "project_ref": project["project_ref"],
        "project_label": project["project_label"],
        "project_direction": project["project_direction"],
        "building_ref": f"building:{building_root.name}",
        "building_id": building_root.name,
        "building_root": analysis.building_root,
        "plan_ref": str(building_work.get("plan_ref") or ""),
        "task_source_ref": str(building_work.get("task_source_ref") or building_map.get("task_source_ref") or ""),
        "current_step_ref": str(latest_link.get("step_ref") or latest_edge.get("step_output_ref") or ""),
        "current_brick_ref": str(
            latest_link.get("source_brick_instance_ref")
            or latest_edge.get("source_brick_instance_ref")
            or latest_binding.get("brick_instance_ref")
            or ""
        ),
        "current_agent_ref": str(latest_binding.get("agent_performer_ref") or ""),
        "current_link_target_ref": str(
            latest_link.get("target_brick_instance_ref")
            or latest_edge.get("target_brick_instance_ref")
            or ""
        ),
        "latest_movement": str(latest_link.get("movement") or ""),
        "link_disposition": link_disposition,
        "frontier_kind": frontier_kind,
        "frontier_reason": str(frontier.get("frontier_reason") or ""),
        "board_state": board_state,
        "next_action_observation": _project_ledger_next_action(frontier_kind),
        "missing_required_file_count": len(analysis.missing_files),
        "mechanical_gap_flags": list(analysis.mechanical_gap_flags),
        "last_evidence_at": last_evidence_at,
        "evidence_refs": {
            "building_map": _rel(repo, building_root / "work" / "building-map.json"),
            "building_work": _rel(repo, building_root / "work" / "building-work.json"),
            "evidence_manifest": _rel(repo, building_root / "evidence" / "evidence-manifest.json"),
            "raw_link": _rel(repo, building_root / "raw" / "link.jsonl"),
            "latest_step_output": str(latest_binding.get("step_output_ref") or ""),
        },
        "proof_limits": [
            "row is support projection over existing evidence only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not process liveness proof",
            "latest_movement is raw observed Link evidence only",
            "last_evidence_at is the newest recorded Link evidence timestamp, not a process heartbeat / not provider liveness",
            "link_disposition is a compact projection of observed transition_lifecycle evidence, not a Link decision or Movement",
        ],
        "not_proven": list(
            dict.fromkeys(
                [
                    *analysis.not_proven,
                    *frontier.get("not_proven", ()),
                    "semantic correctness of project membership",
                    "that last_evidence_at reflects provider liveness rather than newest recorded evidence",
                ]
            )
        ),
    }


def _latest_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in reversed(value):
            if isinstance(item, Mapping):
                return item
    return {}


def _project_ledger_board_state(frontier_kind: str) -> str:
    if frontier_kind == "complete":
        return "closed"
    if frontier_kind == "human_review_waiting":
        return "waiting_review"
    if frontier_kind == "chat_session_parked":
        return "waiting_review"
    if frontier_kind == "link_paused":
        return "link_paused"
    if frontier_kind == "evidence_incomplete":
        return "evidence_incomplete"
    if frontier_kind in {"agent_incomplete", "closure_pending"}:
        return "observed_running"
    return "unknown"


def _project_ledger_next_action(frontier_kind: str) -> str:
    if frontier_kind == "complete":
        return "read closure evidence and remaining_delta"
    if frontier_kind == "human_review_waiting":
        return "caller or COO review disposition is needed"
    if frontier_kind == "chat_session_parked":
        return "caller/COO disposition evidence or chat-session pickup is needed"
    if frontier_kind == "link_paused":
        return "caller or COO Link disposition evidence is needed"
    if frontier_kind == "agent_incomplete":
        return "observe returned Agent evidence or a later declared lifecycle record"
    if frontier_kind == "evidence_incomplete":
        return "inspect missing evidence files before projection use"
    if frontier_kind == "closure_pending":
        return "closure Brick or remaining_delta review may be needed"
    return "inspect Building evidence root"


def _project_ledger_link_disposition(latest_lifecycle: Any) -> Mapping[str, Any]:
    """Compact projection of the frontier's latest_transition_lifecycle.

    Every row carries this block with the same four keys so the field is
    structurally present (null when no paused/resumed transition_lifecycle
    record is observed). This is a plain dict projection of already-observed
    support evidence refs, not a Link decision, not a fact, not a Movement.
    """

    record = latest_lifecycle if isinstance(latest_lifecycle, Mapping) else {}

    def _ref(key: str) -> Any:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    return {
        "required_disposition_owner": _ref(
            "transition_lifecycle_required_disposition_owner"
        ),
        "paused_at_ref": _ref("transition_lifecycle_paused_at_ref"),
        "pending_target_ref": _ref("transition_lifecycle_pending_target_ref"),
        "progress_state": _ref("transition_lifecycle_progress_state"),
    }


def _project_ledger_last_evidence_at(
    link_records: Sequence[Mapping[str, Any]],
) -> str | None:
    """Newest recorded timestamp across observed Link evidence records.

    Returns the MAX of recorded_at / generatedAtTime / time across the
    Building's raw/link.jsonl records (the Link evidence stream this row
    already projects). Null when the Building has zero timestamped records.
    This is the newest recorded evidence timestamp, not a process heartbeat,
    not provider liveness, and not a Movement.
    """

    best_parsed: datetime | None = None
    best_raw: str | None = None
    for record in link_records:
        if not isinstance(record, Mapping):
            continue
        for key in ("recorded_at", "generatedAtTime", "time"):
            raw = record.get(key)
            parsed = _parse_evidence_timestamp(raw)
            if parsed is None:
                continue
            if best_parsed is None or parsed > best_parsed:
                best_parsed = parsed
                best_raw = raw.strip()
    return best_raw


def _parse_evidence_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
