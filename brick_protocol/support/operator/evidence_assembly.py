"""Evidence packet assembly for the Building operator walker (THIN FACADE).

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): this
module was a ~3287 LOC god-module that hand-assembled the support evidence for
every axis crossing (forward-path + adapter-error frontier + lifecycle/map/raw)
and reached into GateFact / plan_validation internals. Its per-crossing-family
emitters were lifted into single-concern collaborators under
``brick_protocol/support/recording/`` (one emitter per crossing family) and this module is now
the THIN WRITER FACADE: it keeps the three public writers as thin orchestrators
that call the emitter modules + re-exports every previously-public name so
external importers keep working identically. It chooses no Movement and judges
no success or quality.

Emitter sublayer (each a registered module_registry.yaml row, G4):
  recording/claims_common.py        leaf claim/step primitives (_claim_fact, ...)
  recording/claims_brick.py         Brick raw records + claim facts
  recording/claims_agent.py         Agent raw records + claim/receipt facts
  recording/claims_link.py          Link transfer/movement/sufficiency facts + gate bodies
  recording/claims_carry_budget.py  Carry + Carry-budget claim facts
  recording/claims_assembly.py      per-axis RawClaimTracePacket assembler
  recording/declaration_packets.py  declaration-provenance packets + plan snapshot
  recording/building_map_emit.py    Building Graph map packets
  recording/lifecycle_emit.py       lifecycle + capture-event packets
  recording/adapter_error_frontier.py  adapter-error agent-incomplete frontier writer
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from collections.abc import Mapping

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.plan_validation import (
    _reject_in_memory_composed_plan_ref,
    _task_source_ref_from_plan,
)
from brick_protocol.support.operator.primitives import (
    _merge_texts,
    _optional_text_or_none,
)
from brick_protocol.support.recording.building_map import (
    BuildingMapWriteResult,
    write_building_map,
)
from brick_protocol.support.recording.building_map_emit import (
    _accumulated_building_map_packet,
    agent_run_building_map_packet,
)
from brick_protocol.support.recording.capture import (
    BuildingLifecycleWriteResult,
    write_building_lifecycle,
)
from brick_protocol.support.recording.claims_assembly import _raw_claim_trace_packet
from brick_protocol.support.recording.claims_common import _step_output_observations
from brick_protocol.support.recording.declaration_packets import (
    _write_declaration_work_evidence,
)
from brick_protocol.support.recording.lifecycle_emit import (
    _accumulated_lifecycle_packet,
    _lifecycle_packet_from_mapping,
    agent_run_lifecycle_mapping,
)
from brick_protocol.support.recording.raw_claim_trace import write_raw_and_claim_trace
from brick_protocol.support.recording.spine_projection import (
    declaration_packets_present,
    project_declaration_spine,
)
from brick_protocol.support.recording.step_outputs import write_step_outputs

# Re-exported public names: the adapter-error frontier writer + its public result
# type live in the adapter_error_frontier emitter now; the facade re-exports them
# so external importers (run.py / building_operation.py) keep working identically.
from brick_protocol.support.recording.adapter_error_frontier import (  # noqa: F401
    AdapterErrorFrontierEvidenceWriteResult,
    ChatSessionParkFrontierEvidenceWriteResult,
    write_adapter_error_frontier_evidence,
    write_chat_session_park_frontier_evidence,
)


@dataclass(frozen=True)
class SingleBuildingEvidenceWriteResult:
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]


@dataclass(frozen=True)
class AccumulatedBuildingEvidenceWriteResult:
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]


def write_single_building_evidence(
    completion,
    *,
    output_root: Path | str,
    overwrite_existing: bool,
) -> SingleBuildingEvidenceWriteResult:
    lifecycle_packet = _lifecycle_packet_from_mapping(
        completion.lifecycle_packet_mapping,
        movement=completion.crossing_record.link_fact.movement,
    )
    lifecycle_write = write_building_lifecycle(
        lifecycle_packet,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
    )
    building_map_write = write_building_map(
        completion.building_map_packet,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
    )
    return SingleBuildingEvidenceWriteResult(
        lifecycle_write=lifecycle_write,
        building_map_write=building_map_write,
        written_files=lifecycle_write.written_files + building_map_write.written_files,
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=completion.building_map_packet,
        proof_limits=lifecycle_write.proof_limits,
    )


def write_accumulated_building_evidence(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    step_results: tuple[BuildingRunSupportResult, ...],
    output_root: Path | str,
    overwrite_existing: bool,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
    declaration_plan: Mapping[str, Any] | None = None,
    step_outputs_already_written: bool = False,
) -> AccumulatedBuildingEvidenceWriteResult:
    _reject_in_memory_composed_plan_ref(plan_ref)
    declared_plan = declaration_plan or plan
    task_source_ref = _task_source_ref_from_plan(plan)
    lifecycle_packet = _accumulated_lifecycle_packet(
        building_id,
        plan_ref,
        plan,
        step_results,
        proof_limits=proof_limits,
        graph_context=graph_context,
        task_source_ref=task_source_ref,
    )
    building_map_packet = _accumulated_building_map_packet(
        building_id,
        step_results,
        plan_ref=plan_ref,
        proof_limits=proof_limits,
        not_proven=_merge_texts(plan.get("not_proven"), *(r.not_proven for r in step_results)),
        graph_context=graph_context,
        task_source_ref=task_source_ref,
        declaration_plan=declared_plan,
    )
    execution_path = _optional_text_or_none(plan.get("execution_path"))
    if execution_path:
        # Record-only provenance marker mirrored into the graph-map projection so
        # the building-map also shows the Building was NOT produced by run.py's
        # walk. run.py's plan walk never declares execution_path.
        building_map_packet = dict(building_map_packet)
        building_map_packet["execution_path"] = execution_path
    lifecycle_write = write_building_lifecycle(
        lifecycle_packet,
        output_root=output_root,
        overwrite_existing=overwrite_existing or step_outputs_already_written,
    )
    declaration_written = _write_declaration_work_evidence(
        lifecycle_write.root,
        building_id=building_id,
        plan_ref=plan_ref,
        plan=plan,
        declaration_plan=declared_plan,
        graph_context=graph_context,
        task_source_ref=task_source_ref,
        proof_limits=proof_limits,
        not_proven=_merge_texts(plan.get("not_proven"), *(r.not_proven for r in step_results)),
    )
    if step_outputs_already_written:
        # Per-event step close owns step-output persistence. The accumulated
        # evidence batch must not touch those files again, even as a
        # same-content check, or the drain path quietly regains a batch writer.
        step_output_written = ()
    else:
        step_observations = _step_output_observations(
            building_id,
            step_results,
            task_source_ref=task_source_ref,
        )
        step_output_written = write_step_outputs(
            lifecycle_write.root,
            building_id,
            step_observations,
            proof_limits=proof_limits,
            existing_policy="replace",
        )
    raw_claim_written = write_raw_and_claim_trace(
        lifecycle_write.root,
        building_id,
        _raw_claim_trace_packet(
            building_id,
            step_results,
            plan=plan,
            proof_limits=proof_limits,
            graph_context=graph_context,
        ),
    )
    building_map_write = write_building_map(
        building_map_packet,
        output_root=output_root,
        overwrite_existing=overwrite_existing or step_outputs_already_written,
    )
    # U5.5 slice-2 BUILD-2: project the two BUILDING-SCOPE declaration events
    # (PresetExpansion + LinkLaunchPolicy) into the Evidence Spine via the
    # append-only writer. The declaration packets were already written to
    # work/ above (``_write_declaration_work_evidence``), so they exist on disk
    # here. INCREMENT-1 design decision (let it RAISE, but only for an eligible
    # building): the projector is called ONLY when BOTH declaration packets are
    # present on disk, so a build that legitimately lacks them is NOT forced into
    # a u5_5_live spine + a failing projection; when it IS eligible the projection
    # is allowed to RAISE (surface errors) rather than be swallowed best-effort —
    # an eligible build with an unprojectable spine is a real failure to see.
    # Capture the projected event bodies so the spine files are reported in
    # written_files (the prior code ignored the return and UNDER-REPORTED the
    # spine). A non-empty return is a REAL projection (the writer filled in
    # sequence_index / event_type per body); an idempotent no-op returns [] and
    # adds NOTHING. The spine file paths are built as Path objects anchored at the
    # building root, MATCHING the format of the existing written_files entries
    # (lifecycle_write.written_files / building_map_write.written_files are
    # building-root-anchored Path objects). For each returned body the projection
    # produced its event .json + paired .md (named <sequence_index:04d>-<event_type>),
    # and the writer (re)derived the spine.json / spine.jsonl / spine.md index.
    spine_written: tuple[Path, ...] = ()
    if declaration_packets_present(lifecycle_write.root):
        projected_bodies = project_declaration_spine(lifecycle_write.root)
        if projected_bodies:
            spine_dir = lifecycle_write.root / "evidence" / "spine"
            events_dir = spine_dir / "events"
            event_files: list[Path] = []
            for body in projected_bodies:
                stem = f"{int(body['sequence_index']):04d}-{body['event_type']}"
                event_files.append(events_dir / f"{stem}.json")
                event_files.append(events_dir / f"{stem}.md")
            spine_written = tuple(event_files) + (
                spine_dir / "spine.json",
                spine_dir / "spine.jsonl",
                spine_dir / "spine.md",
            )
    written_files = (
        lifecycle_write.written_files
        + declaration_written
        + step_output_written
        + raw_claim_written
        + building_map_write.written_files
        + spine_written
    )
    return AccumulatedBuildingEvidenceWriteResult(
        lifecycle_write=lifecycle_write,
        building_map_write=building_map_write,
        written_files=written_files,
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=building_map_packet,
        proof_limits=lifecycle_write.proof_limits,
    )
