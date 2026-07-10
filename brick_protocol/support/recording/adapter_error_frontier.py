"""Adapter-error agent-incomplete frontier evidence writer.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
adapter-error frontier writer and its lifecycle / capture / raw-manifest /
evidence-manifest / trace-packet builders that
``brick_protocol/support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern writer. When the adapter raises before the Agent returns a
closed AgentFact, this records an ``agent_incomplete`` frontier: the Agent
receipt is observed, no AgentFact / Link transition is created, and the human
decides next. It composes the per-crossing-family emitters (claims_brick /
claims_agent / claims_link), the claim-trace assembler, the building-map and
lifecycle emitters, and the recording packet writers. Authors no Movement,
target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest
from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.plan_graph import _graph_link_raw_refs
from brick_protocol.support.operator.plan_validation import _task_source_ref_from_plan
from brick_protocol.support.operator.primitives import (
    _merge_texts,
    _raw_ref,
    _reject_session_like_text,
    _resource_slug,
    _step_fact_ref,
    _text_tuple,
)
from brick_protocol.support.connection.secret_text import contains_raw_secret_text
from brick_protocol.support.recording.building_map import (
    BuildingMapWriteResult,
    write_building_map,
)
from brick_protocol.support.recording.building_map_emit import (
    _adapter_error_frontier_building_map_packet,
    _chat_session_park_frontier_building_map_packet,
)
from brick_protocol.support.recording.capture import (
    BuildingLifecyclePacket,
    BuildingLifecycleWriteResult,
    CaptureEvent,
    graph_ready_timestamp,
    write_building_lifecycle,
)
from brick_protocol.support.recording.claims_agent import (
    _adapter_error_agent_received_raw_records,
    _adapter_error_agent_receipt_claim_fact,
    _chat_session_park_agent_received_raw_records,
    _chat_session_park_agent_receipt_claim_fact,
)
from brick_protocol.support.recording.claims_assembly import _raw_claim_trace_packet
from brick_protocol.support.recording.claims_brick import (
    _adapter_error_brick_claim_fact,
    _adapter_error_brick_raw_record,
    _brick_claim_facts,
    _brick_raw_records,
)
from brick_protocol.support.recording.claims_common import (
    _adapter_error_attempt_from_ref,
    _chat_session_park_attempt_from_ref,
    _manifest_not_proven,
    _step_output_adapter_error_ref,
    _step_output_parked_ref,
    _step_output_work_envelope_ref,
    _step_output_manifest_refs,
    _step_output_observations,
)
from brick_protocol.support.recording.claims_link import (
    _adapter_error_link_frontier_claim_fact,
    _adapter_error_link_frontier_raw_record,
    _chat_session_park_link_frontier_claim_fact,
    _chat_session_park_link_frontier_raw_record,
    _link_raw_records,
)
from brick_protocol.support.recording.contracts import (
    AdapterErrorFrontierTracePacket,
    AdapterErrorObservation,
    ChatSessionParkFrontierTracePacket,
    ChatSessionParkObservation,
)
from brick_protocol.support.recording.declaration_packets import (
    _plan_snapshot,
    _write_declaration_work_evidence,
)
from brick_protocol.support.recording.lifecycle_emit import (
    _accumulated_capture_event,
    _accumulated_raw_manifest,
    _dynamic_reroute_raw_refs,
    _lifecycle_packet_from_mapping,
)
from brick_protocol.support.recording.raw_claim_trace import (
    write_adapter_error_frontier_raw_and_claim_trace,
    write_chat_session_park_frontier_raw_and_claim_trace,
    write_raw_and_claim_trace,
)
from brick_protocol.support.recording.step_outputs import (
    write_adapter_error_outputs,
    write_chat_session_park_outputs,
    write_step_outputs,
)


@dataclass(frozen=True)
class AdapterErrorFrontierEvidenceWriteResult:
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]


@dataclass(frozen=True)
class ChatSessionParkFrontierEvidenceWriteResult:
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]


def write_adapter_error_frontier_evidence(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    adapter_request: Any,
    adapter_error: Mapping[str, Any],
    output_root: Path | str,
    overwrite_existing: bool,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
    frontier_transition_lifecycle: Mapping[str, Any] | None = None,
    declaration_plan: Mapping[str, Any] | None = None,
) -> AdapterErrorFrontierEvidenceWriteResult:
    declared_plan = declaration_plan or plan
    task_source_ref = _task_source_ref_from_plan(plan)
    frontier_graph_context = _realized_frontier_graph_context(
        graph_context,
        completed_step_results,
    )
    failed_step_index = len(completed_step_results) + 1
    failed_attempt_index = _frontier_attempt_index(
        completed_step_results,
        failed_preparation.step_rows.step_ref,
    )
    observation = _adapter_error_observation(
        building_id,
        failed_preparation,
        adapter_request=adapter_request,
        adapter_error=adapter_error,
        step_index=failed_step_index,
        attempt_index=failed_attempt_index,
        task_source_ref=task_source_ref,
        proof_limits=proof_limits,
    )
    lifecycle_packet = _adapter_error_frontier_lifecycle_packet(
        building_id,
        plan_ref,
        plan,
        completed_step_results,
        failed_preparation,
        observation,
        proof_limits=proof_limits,
        graph_context=frontier_graph_context,
        task_source_ref=task_source_ref,
    )
    building_map_packet = _adapter_error_frontier_building_map_packet(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan_ref=plan_ref,
        proof_limits=proof_limits,
        graph_context=frontier_graph_context,
        task_source_ref=task_source_ref,
        declaration_plan=declared_plan,
    )
    existing_root_state = _adapter_error_existing_root_state(
        Path(output_root) / building_id,
        building_id=building_id,
    )
    if existing_root_state == "not_directory":
        raise NotADirectoryError(
            "adapter-error frontier root exists but is not a directory; "
            "existing_root_state=not_directory"
        )
    if existing_root_state == "root_exists_without_frontier" or (
        existing_root_state == "partial_write_risk" and not completed_step_results
    ):
        written_files = _write_adapter_error_root_state_marker(
            Path(output_root) / building_id,
            building_id=building_id,
            observation=observation,
            root_state=existing_root_state,
            proof_limits=proof_limits,
        )
        marker_path = written_files[0]
        return AdapterErrorFrontierEvidenceWriteResult(
            lifecycle_write=BuildingLifecycleWriteResult(
                root=Path(output_root) / building_id,
                written_files=written_files,
                proof_limits=_merge_texts(
                    proof_limits,
                    (
                        "adapter-error root-state marker only; lifecycle frontier not overwritten",
                        "operator/COO must inspect preserved root contents",
                    ),
                ),
            ),
            building_map_write=BuildingMapWriteResult(
                root=Path(output_root) / building_id,
                path=marker_path,
                written_files=(),
            ),
            written_files=written_files,
            capture_event_types=(),
            building_map_packet={
                "building_id": building_id,
                "frontier_kind": existing_root_state,
                "root_state_marker": marker_path.name,
                "source_truth": False,
                "proof_limits": [
                    "support observation only",
                    "not source truth",
                    "not success judgment",
                    "not quality judgment",
                    "not Movement authority",
                ],
            },
            proof_limits=_merge_texts(
                proof_limits,
                (
                    "adapter-error root-state marker only; lifecycle frontier not overwritten",
                    "operator/COO must inspect preserved root contents",
                ),
            ),
        )
    effective_overwrite_existing = (
        overwrite_existing
        or existing_root_state == "declaration_chain_only"
    )
    lifecycle_write = write_building_lifecycle(
        lifecycle_packet,
        output_root=output_root,
        overwrite_existing=effective_overwrite_existing,
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
        not_proven=_manifest_not_proven(()),
    )
    complete_step_written = ()
    complete_raw_written = ()
    if completed_step_results:
        complete_step_written = write_step_outputs(
            lifecycle_write.root,
            building_id,
            _step_output_observations(
                building_id,
                completed_step_results,
                task_source_ref=task_source_ref,
            ),
            proof_limits=proof_limits,
        )
        complete_raw_written = write_raw_and_claim_trace(
            lifecycle_write.root,
            building_id,
            _raw_claim_trace_packet(
                building_id,
                completed_step_results,
                plan=plan,
                proof_limits=proof_limits,
                graph_context=frontier_graph_context,
            ),
        )
    adapter_step_written = write_adapter_error_outputs(
        lifecycle_write.root,
        building_id,
        (observation,),
        proof_limits=proof_limits,
    )
    frontier_raw_written = write_adapter_error_frontier_raw_and_claim_trace(
        lifecycle_write.root,
        building_id,
        _adapter_error_frontier_trace_packet(
            building_id,
            completed_step_results,
            failed_preparation,
            observation,
            plan=plan,
            proof_limits=proof_limits,
            graph_context=frontier_graph_context,
            frontier_transition_lifecycle=frontier_transition_lifecycle,
        ),
    )
    building_map_write = write_building_map(
        building_map_packet,
        output_root=output_root,
        overwrite_existing=effective_overwrite_existing,
    )
    written_files = (
        lifecycle_write.written_files
        + declaration_written
        + complete_step_written
        + adapter_step_written
        + complete_raw_written
        + frontier_raw_written
        + building_map_write.written_files
    )
    return AdapterErrorFrontierEvidenceWriteResult(
        lifecycle_write=lifecycle_write,
        building_map_write=building_map_write,
        written_files=written_files,
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=building_map_packet,
        proof_limits=lifecycle_write.proof_limits,
    )


def write_chat_session_park_frontier_evidence(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    adapter_request: AgentAdapterRequest,
    output_root: Path | str,
    overwrite_existing: bool,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
    frontier_transition_lifecycle: Mapping[str, Any] | None = None,
    declaration_plan: Mapping[str, Any] | None = None,
) -> ChatSessionParkFrontierEvidenceWriteResult:
    declared_plan = declaration_plan or plan
    task_source_ref = _task_source_ref_from_plan(plan)
    frontier_graph_context = _realized_frontier_graph_context(
        graph_context,
        completed_step_results,
    )
    failed_step_index = len(completed_step_results) + 1
    failed_attempt_index = _frontier_attempt_index(
        completed_step_results,
        failed_preparation.step_rows.step_ref,
    )
    work_envelope = _agent_adapter_request_work_envelope(adapter_request)
    observation = _chat_session_park_observation(
        building_id,
        failed_preparation,
        adapter_request=adapter_request,
        work_envelope=work_envelope,
        step_index=failed_step_index,
        attempt_index=failed_attempt_index,
        task_source_ref=task_source_ref,
        proof_limits=proof_limits,
    )
    lifecycle_packet = _chat_session_park_frontier_lifecycle_packet(
        building_id,
        plan_ref,
        plan,
        completed_step_results,
        failed_preparation,
        observation,
        proof_limits=proof_limits,
        graph_context=frontier_graph_context,
        task_source_ref=task_source_ref,
    )
    building_map_packet = _chat_session_park_frontier_building_map_packet(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan_ref=plan_ref,
        proof_limits=proof_limits,
        graph_context=frontier_graph_context,
        task_source_ref=task_source_ref,
        declaration_plan=declared_plan,
    )
    effective_overwrite_existing = (
        overwrite_existing
        or _root_holds_only_declaration_chain_artifacts(
            Path(output_root) / building_id,
            building_id=building_id,
        )
    )
    lifecycle_write = write_building_lifecycle(
        lifecycle_packet,
        output_root=output_root,
        overwrite_existing=effective_overwrite_existing,
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
        not_proven=_manifest_not_proven(()),
    )
    complete_step_written = ()
    complete_raw_written = ()
    if completed_step_results:
        complete_step_written = write_step_outputs(
            lifecycle_write.root,
            building_id,
            _step_output_observations(
                building_id,
                completed_step_results,
                task_source_ref=task_source_ref,
            ),
            proof_limits=proof_limits,
        )
        complete_raw_written = write_raw_and_claim_trace(
            lifecycle_write.root,
            building_id,
            _raw_claim_trace_packet(
                building_id,
                completed_step_results,
                plan=plan,
                proof_limits=proof_limits,
                graph_context=frontier_graph_context,
            ),
        )
    park_step_written = write_chat_session_park_outputs(
        lifecycle_write.root,
        building_id,
        (observation,),
        proof_limits=proof_limits,
    )
    frontier_raw_written = write_chat_session_park_frontier_raw_and_claim_trace(
        lifecycle_write.root,
        building_id,
        _chat_session_park_frontier_trace_packet(
            building_id,
            completed_step_results,
            failed_preparation,
            observation,
            plan=plan,
            proof_limits=proof_limits,
            graph_context=frontier_graph_context,
            frontier_transition_lifecycle=frontier_transition_lifecycle,
        ),
    )
    building_map_write = write_building_map(
        building_map_packet,
        output_root=output_root,
        overwrite_existing=effective_overwrite_existing,
    )
    written_files = (
        lifecycle_write.written_files
        + declaration_written
        + complete_step_written
        + park_step_written
        + complete_raw_written
        + frontier_raw_written
        + building_map_write.written_files
    )
    return ChatSessionParkFrontierEvidenceWriteResult(
        lifecycle_write=lifecycle_write,
        building_map_write=building_map_write,
        written_files=written_files,
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=building_map_packet,
        proof_limits=lifecycle_write.proof_limits,
    )


_DECLARATION_CHAIN_ROOT_ARTIFACTS: frozenset[Path] = frozenset(
    {
        Path("declared-building-plan.json"),
        Path("raw/report-delivery.jsonl"),
        Path("raw/report-thread.jsonl"),
        Path("raw/adapter-error.jsonl"),
        Path("work/task.md"),
        Path("work/building-intake.json"),
        Path("work/preset-expansion.json"),
        Path("work/proposed-building-graph.json"),
        Path("work/declared-building-plan.json"),
        Path("work/link-launch-policy.json"),
    }
)
_DECLARATION_CHAIN_PARENT_DIRS: frozenset[Path] = frozenset(
    {Path("raw"), Path("work")}
)
_DECLARATION_CHAIN_PLAN_ARTIFACTS: frozenset[Path] = frozenset(
    {
        Path("declared-building-plan.json"),
        Path("work/proposed-building-graph.json"),
        Path("work/declared-building-plan.json"),
    }
)
_DECLARATION_CHAIN_JSON_ARTIFACTS: frozenset[Path] = frozenset(
    path for path in _DECLARATION_CHAIN_ROOT_ARTIFACTS if path.suffix == ".json"
)
_DECLARATION_CHAIN_JSONL_ARTIFACTS: frozenset[Path] = frozenset(
    {
        Path("raw/report-delivery.jsonl"),
        Path("raw/report-thread.jsonl"),
        Path("raw/adapter-error.jsonl"),
    }
)
_DECLARATION_CHAIN_JSONL_KINDS: Mapping[Path, str] = {
    Path("raw/report-delivery.jsonl"): "report_delivery_observation",
    Path("raw/report-thread.jsonl"): "report_slack_thread_parent_observation",
    Path("raw/adapter-error.jsonl"): "adapter_error_record",
}
_ADAPTER_ERROR_PARTIAL_WRITE_RISK_MARKER = "adapter-error-frontier-partial-write-risk.json"
_ADAPTER_ERROR_ROOT_STATE_MARKER = "adapter-error-frontier-root-state.json"
_REPORT_EVENT_SUFFIXES: frozenset[str] = frozenset(
    {
        "building-started-event",
        "brick-received-event",
        "brick-returned-event",
        "gate-passed-event",
        "intervention-required-event",
    }
)
_LEGACY_REPORT_SUFFIXES: frozenset[str] = frozenset(
    {
        "building-started",
        "brick-received",
        "brick-returned",
        "gate-passed",
        "intervention-required",
    }
)
_REPORT_VESSEL_SOURCE_PREFIXES: tuple[str, ...] = ("brick-protocol-",)
_REPORT_EVENT_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}(?:-\d{1,6})?(?:Z|-\d{2}-\d{2})?"
)


def _adapter_error_existing_root_state(root: Path, *, building_id: str) -> str:
    """Classify the pre-frontier root without choosing Movement or judging quality.

    The run/walker preflight admits only the single intake plan artifact before
    any adapter call. This frontier writer runs after an adapter interruption,
    where report/declaration support files may already exist; it therefore uses
    the wider declaration-chain predicate below. Anything else is preserved and
    marked as partial-write risk instead of being overwritten.
    """

    if root.is_symlink() or not root.exists():
        return "absent"
    if not root.is_dir():
        return "not_directory"
    if _root_holds_only_declaration_chain_artifacts(root, building_id=building_id):
        return "declaration_chain_only"
    if not any(root.iterdir()):
        return "root_exists_without_frontier"
    return "partial_write_risk"


def _root_holds_only_declaration_chain_artifacts(root: Path, *, building_id: str) -> bool:
    """Admit a non-symlink root only when declaration files name this Building.

    PROOF LIMIT: local-concurrency TOCTOU root/work swaps after this check are out of scope.
    """

    if root.is_symlink() or not root.exists() or not root.is_dir():
        return False
    saw_file = False
    saw_plan_artifact = False
    expected_building_id = building_id.strip()
    for entry in root.rglob("*"):
        relative = entry.relative_to(root)
        if entry.is_symlink():
            return False
        if entry.is_dir():
            if relative not in _DECLARATION_CHAIN_PARENT_DIRS:
                return False
            continue
        if not entry.is_file():
            return False
        if relative not in _DECLARATION_CHAIN_ROOT_ARTIFACTS:
            return False
        if relative in _DECLARATION_CHAIN_JSON_ARTIFACTS:
            try:
                packet = json.loads(entry.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return False
            if not isinstance(packet, Mapping):
                return False
            packet_building_id = packet.get("building_id")
            if relative in _DECLARATION_CHAIN_PLAN_ARTIFACTS:
                if not isinstance(packet_building_id, str):
                    return False
                if not packet_building_id.strip():
                    return False
                if packet_building_id.strip() != expected_building_id:
                    return False
            elif packet_building_id is not None:
                if not isinstance(packet_building_id, str):
                    return False
                if packet_building_id.strip() != expected_building_id:
                    return False
        if relative in _DECLARATION_CHAIN_JSONL_ARTIFACTS and not _declaration_chain_jsonl_valid(
            entry,
            expected_kind=_DECLARATION_CHAIN_JSONL_KINDS[relative],
            expected_building_id=expected_building_id,
        ):
            return False
        if relative in _DECLARATION_CHAIN_PLAN_ARTIFACTS:
            saw_plan_artifact = True
        saw_file = True
    return saw_file and saw_plan_artifact


def _declaration_chain_jsonl_valid(
    path: Path,
    *,
    expected_kind: str,
    expected_building_id: str,
) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    if not lines:
        return False
    saw_record = False
    for line in lines:
        if not line.strip():
            continue
        try:
            packet = json.loads(line)
        except json.JSONDecodeError:
            return False
        if not isinstance(packet, Mapping):
            return False
        if packet.get("kind") != expected_kind:
            return False
        packet_building_id = packet.get("building_id")
        if packet_building_id is not None:
            if not isinstance(packet_building_id, str):
                return False
            if packet_building_id.strip() != expected_building_id:
                return False
        else:
            report_id = packet.get("report_id")
            if not isinstance(
                report_id, str
            ) or not _declaration_chain_report_id_matches_building(
                report_id,
                expected_building_id=expected_building_id,
            ):
                return False
        if packet.get("source_truth") is not False:
            return False
        saw_record = True
    return saw_record


def _declaration_chain_report_id_matches_building(
    report_id: str,
    *,
    expected_building_id: str,
) -> bool:
    """Accept same-Building report ids without substring collisions.

    Reporter ids are either legacy ``<building_id>-<kind>`` or the admitted
    live vessel form ``brick-protocol-<building_id>-<kind>``. Some historical
    fixtures use ``report:<building_id>:<kind>``. Each form compares the parsed
    source id exactly; no arbitrary prefix/suffix source id is admitted.
    """

    expected = expected_building_id.strip()
    if not expected:
        return False
    text = report_id.strip()
    if text.startswith("report:"):
        rest = text[len("report:") :]
        source_id, separator, _kind = rest.partition(":")
        return bool(separator) and source_id == expected
    return _report_id_source_id(text) in _allowed_report_source_ids(expected)


def _allowed_report_source_ids(expected_building_id: str) -> frozenset[str]:
    return frozenset(
        (expected_building_id,)
        + tuple(
            f"{prefix}{expected_building_id}"
            for prefix in _REPORT_VESSEL_SOURCE_PREFIXES
        )
    )


def _report_id_source_id(report_id: str) -> str:
    event_candidates: list[tuple[int, str]] = []
    for suffix in _REPORT_EVENT_SUFFIXES:
        marker = f"-{suffix}-"
        source_id, separator, timestamp = report_id.rpartition(marker)
        if not separator or not source_id:
            continue
        if _REPORT_EVENT_TIMESTAMP_RE.fullmatch(timestamp):
            event_candidates.append((len(source_id), source_id))
    if event_candidates:
        return max(event_candidates, key=lambda candidate: candidate[0])[1]
    for suffix in _LEGACY_REPORT_SUFFIXES:
        marker = f"-{suffix}"
        if report_id.endswith(marker):
            return report_id[: -len(marker)]
    return ""


def _write_adapter_error_root_state_marker(
    root: Path,
    *,
    building_id: str,
    observation: AdapterErrorObservation,
    root_state: str,
    proof_limits: tuple[str, ...],
) -> tuple[Path, ...]:
    if root_state not in {"partial_write_risk", "root_exists_without_frontier"}:
        raise ValueError("unsupported adapter-error root state marker")
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise FileExistsError(
            "adapter-error root-state marker requires an existing non-symlink root"
        )
    marker_name = (
        _ADAPTER_ERROR_PARTIAL_WRITE_RISK_MARKER
        if root_state == "partial_write_risk"
        else _ADAPTER_ERROR_ROOT_STATE_MARKER
    )
    path = root / marker_name
    if path.is_symlink() or path.is_dir():
        raise FileExistsError(
            "adapter-error root-state marker path is not a regular file"
        )
    frontier_kind = (
        "partial_write_risk"
        if root_state == "partial_write_risk"
        else "root_exists_without_frontier"
    )
    root_state_detail = (
        "root_exists_with_non_declaration_artifacts"
        if root_state == "partial_write_risk"
        else "root_exists_empty_without_frontier"
    )
    packet = {
        "kind": "adapter_error_frontier_root_state_observation",
        "schema_version": "adapter-error-frontier-root-state-0",
        "building_id": building_id,
        "frontier_kind": frontier_kind,
        "root_state": root_state_detail,
        "full_frontier_written": False,
        "preserved_existing_root": True,
        "step_ref": observation.step_ref,
        "adapter_error_ref": observation.adapter_error_ref,
        "error_kind": observation.error_kind,
        "exception_type": observation.exception_type,
        "recorded_at": graph_ready_timestamp(),
        "source_truth": False,
        "proof_limits": list(
            _merge_texts(
                proof_limits,
                (
                    "support observation only",
                    "records adapter-error root state before AgentFact",
                    "preserves existing root contents",
                    "not source truth",
                    "not success judgment",
                    "not quality judgment",
                    "not Movement authority",
                ),
            )
        ),
        "not_proven": list(
            _merge_texts(
                observation.not_proven,
                (
                    "complete lifecycle frontier for this interruption",
                    "semantic meaning of preserved root state",
                    "caller/COO disposition after root-state observation",
                ),
            )
        ),
    }
    path.write_text(
        json.dumps(packet, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return (path,)


def _write_adapter_error_partial_write_risk_marker(
    root: Path,
    *,
    building_id: str,
    observation: AdapterErrorObservation,
    proof_limits: tuple[str, ...],
) -> tuple[Path, ...]:
    return _write_adapter_error_root_state_marker(
        root,
        building_id=building_id,
        observation=observation,
        root_state="partial_write_risk",
        proof_limits=proof_limits,
    )


def _realized_frontier_graph_context(
    graph_context: Mapping[str, Any] | None,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
) -> Mapping[str, Any] | None:
    """Keep adapter-error frontier graph refs limited to walked step crossings."""

    if not graph_context:
        return None
    completed_step_refs = {
        result.preparation.step_rows.step_ref for result in completed_step_results
    }
    declared_edges = graph_context.get("declared_edges")
    if not isinstance(declared_edges, list):
        return {"declared_edges": [], "completion_edge_refs": [], "groups": []}
    realized_edges = [
        dict(edge)
        for edge in declared_edges
        if isinstance(edge, Mapping)
        and edge.get("is_completion_edge") is True
        and edge.get("source_step_ref") in completed_step_refs
    ]
    completion_edge_refs = [
        str(edge.get("edge_ref"))
        for edge in realized_edges
        if isinstance(edge.get("edge_ref"), str) and edge.get("edge_ref")
    ]
    return {
        "declared_edges": realized_edges,
        "completion_edge_refs": sorted(completion_edge_refs),
        "groups": [],
    }


def _adapter_error_observation(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    *,
    adapter_request: Any,
    adapter_error: Mapping[str, Any],
    step_index: int,
    attempt_index: int,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
) -> AdapterErrorObservation:
    step_ref = prepared.step_rows.step_ref
    return AdapterErrorObservation(
        building_id=building_id,
        step_ref=step_ref,
        brick_instance_ref=prepared.brick_instance_ref,
        next_brick_instance_ref=prepared.next_brick_instance_ref,
        agent_object_ref=prepared.agent_object.object_ref,
        adapter_ref=str(getattr(adapter_request, "adapter_ref", "")),
        selected_model_ref=str(getattr(adapter_request, "selected_model_ref", "")),
        input_packet_ref=str(getattr(adapter_request, "input_packet_ref", "")),
        output_packet_ref=str(getattr(adapter_request, "output_packet_ref", "")),
        error_kind=str(adapter_error.get("error_kind", "adapter_exception")),
        exception_type=str(adapter_error.get("exception_type", "Exception")),
        message_excerpt=str(adapter_error.get("message_excerpt", "")),
        received_work_ref=_step_fact_ref("brick-work", step_index, step_ref),
        adapter_error_ref=f"adapter-error:{_resource_slug('step_ref', step_ref.replace(':', '-'))}:attempt-{attempt_index}",
        raw_ref=_raw_ref("adapter-error", step_index),
        task_source_ref=task_source_ref or "",
        diagnostic_excerpts=_adapter_error_diagnostic_excerpts(adapter_error),
        proof_limits=_merge_texts(proof_limits, adapter_error.get("proof_limits")),
        not_proven=_manifest_not_proven(
            _merge_texts(prepared.not_proven, adapter_error.get("not_proven"))
        ),
    )


_ADAPTER_ERROR_DIAGNOSTIC_KEYS = frozenset(
    {
        "timeout_reap_reason",
        "timeout_stdout_excerpt",
        "timeout_stderr_excerpt",
    }
)


def _adapter_error_diagnostic_excerpts(adapter_error: Mapping[str, Any]) -> Mapping[str, str]:
    diagnostics: dict[str, str] = {}
    for key in sorted(_ADAPTER_ERROR_DIAGNOSTIC_KEYS):
        value = adapter_error.get(key)
        if value in (None, ""):
            continue
        text = str(value)
        if contains_raw_secret_text(text):
            raise ValueError(f"adapter-error diagnostic {key} contains raw credential-looking text")
        diagnostics[key] = text
    return diagnostics


def _agent_adapter_request_work_envelope(
    adapter_request: AgentAdapterRequest,
) -> Mapping[str, Any]:
    if not isinstance(adapter_request, AgentAdapterRequest):
        raise TypeError("adapter_request must be AgentAdapterRequest")
    envelope: dict[str, Any] = {}
    for field in fields(AgentAdapterRequest):
        envelope[field.name] = _json_safe_envelope_value(getattr(adapter_request, field.name))
    expected_keys = {field.name for field in fields(AgentAdapterRequest)}
    if set(envelope) != expected_keys:
        raise ValueError("work envelope must contain exactly AgentAdapterRequest fields")
    _reject_session_like_text("work_envelope", envelope)
    return envelope


def _json_safe_envelope_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_envelope_value(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_json_safe_envelope_value(child) for child in value]
    if isinstance(value, list):
        return [_json_safe_envelope_value(child) for child in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError("work envelope contains non-JSON value")


def _chat_session_park_observation(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    *,
    adapter_request: AgentAdapterRequest,
    work_envelope: Mapping[str, Any],
    step_index: int,
    attempt_index: int,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
) -> ChatSessionParkObservation:
    step_ref = prepared.step_rows.step_ref
    parked_ref = (
        f"chat-session-parked:{_resource_slug('step_ref', step_ref.replace(':', '-'))}"
        f":attempt-{attempt_index}"
    )
    return ChatSessionParkObservation(
        building_id=building_id,
        step_ref=step_ref,
        brick_instance_ref=prepared.brick_instance_ref,
        next_brick_instance_ref=prepared.next_brick_instance_ref,
        agent_object_ref=prepared.agent_object.object_ref,
        adapter_ref=adapter_request.adapter_ref,
        selected_model_ref=adapter_request.selected_model_ref,
        input_packet_ref=adapter_request.input_packet_ref,
        output_packet_ref=adapter_request.output_packet_ref,
        received_work_ref=_step_fact_ref("brick-work", step_index, step_ref),
        parked_ref=parked_ref,
        work_envelope_ref=_step_output_work_envelope_ref(step_ref, attempt_index),
        raw_ref=_raw_ref("chat-session-park", step_index),
        work_envelope=work_envelope,
        task_source_ref=task_source_ref or "",
        proof_limits=_merge_texts(
            proof_limits,
            (
                "chat-session park frontier support evidence only",
                "not Agent returned payload",
                "not AgentFact",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ),
        ),
        not_proven=_manifest_not_proven(
            _merge_texts(
                prepared.not_proven,
                (
                    "chat session pickup behavior",
                    "future submit or resume behavior",
                    "semantic correctness of parked work",
                    "caller/COO disposition after parked frontier observation",
                ),
            )
        ),
    )


def _frontier_attempt_index(
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    step_ref: str,
) -> int:
    return 1 + sum(
        1 for result in completed_step_results if result.preparation.step_rows.step_ref == step_ref
    )


def _adapter_error_frontier_lifecycle_packet(
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
    *,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
) -> BuildingLifecyclePacket:
    first_work = (
        completed_step_results[0].preparation.brick_work
        if completed_step_results
        else failed_preparation.brick_work
    )
    not_proven = _merge_texts(
        plan.get("not_proven"),
        *(result.not_proven for result in completed_step_results),
        failed_preparation.not_proven,
        observation.not_proven,
    )
    events: list[CaptureEvent] = []
    for index, result in enumerate(completed_step_results, start=1):
        lifecycle = _lifecycle_packet_from_mapping(
            result.completion.lifecycle_packet_mapping,
            movement=result.completion.crossing_record.link_fact.movement,
        )
        step_ref = result.preparation.step_rows.step_ref
        for event in lifecycle.capture_events:
            events.append(_accumulated_capture_event(event, index, step_ref, building_id))
    events.extend(
        _adapter_error_frontier_capture_events(
            building_id,
            failed_preparation,
            observation,
            include_building_opened=not completed_step_results,
            step_index=len(completed_step_results) + 1,
        )
    )
    building_work = {
        "work_statement": first_work.work_statement,
        "comparison_rule": first_work.comparison_rule,
        "required_return_shape": first_work.required_return_shape,
        "source_facts": list(_merge_texts(first_work.source_facts, plan.get("raw_refs"))),
        "building_id": building_id,
        "plan_ref": plan_ref,
        "step_refs": [
            *(result.preparation.step_rows.step_ref for result in completed_step_results),
            failed_preparation.step_rows.step_ref,
        ],
        "frontier_observation": "Agent receipt observed before returned AgentFact",
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    raw_manifest = _adapter_error_frontier_raw_manifest(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan,
        graph_context,
    )
    evidence_manifest = _adapter_error_frontier_evidence_manifest(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan_ref=plan_ref,
        plan=plan,
        proof_limits=proof_limits,
        not_proven=not_proven,
    )
    if task_source_ref:
        building_work["task_source_ref"] = task_source_ref
        evidence_manifest["task_source_ref"] = task_source_ref
    return BuildingLifecyclePacket(
        building_id=building_id,
        building_work=building_work,
        capture_events=tuple(events),
        raw_manifest=raw_manifest,
        evidence_manifest=evidence_manifest,
        proof_limits=proof_limits,
    )


def _chat_session_park_frontier_lifecycle_packet(
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
    *,
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
) -> BuildingLifecyclePacket:
    first_work = (
        completed_step_results[0].preparation.brick_work
        if completed_step_results
        else failed_preparation.brick_work
    )
    not_proven = _merge_texts(
        plan.get("not_proven"),
        *(result.not_proven for result in completed_step_results),
        failed_preparation.not_proven,
        observation.not_proven,
    )
    events: list[CaptureEvent] = []
    for index, result in enumerate(completed_step_results, start=1):
        lifecycle = _lifecycle_packet_from_mapping(
            result.completion.lifecycle_packet_mapping,
            movement=result.completion.crossing_record.link_fact.movement,
        )
        step_ref = result.preparation.step_rows.step_ref
        for event in lifecycle.capture_events:
            events.append(_accumulated_capture_event(event, index, step_ref, building_id))
    events.extend(
        _chat_session_park_frontier_capture_events(
            building_id,
            failed_preparation,
            observation,
            include_building_opened=not completed_step_results,
            step_index=len(completed_step_results) + 1,
        )
    )
    building_work = {
        "work_statement": first_work.work_statement,
        "comparison_rule": first_work.comparison_rule,
        "required_return_shape": first_work.required_return_shape,
        "source_facts": list(_merge_texts(first_work.source_facts, plan.get("raw_refs"))),
        "building_id": building_id,
        "plan_ref": plan_ref,
        "step_refs": [
            *(result.preparation.step_rows.step_ref for result in completed_step_results),
            failed_preparation.step_rows.step_ref,
        ],
        "frontier_observation": "Chat-session work envelope parked before AgentFact",
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    raw_manifest = _chat_session_park_frontier_raw_manifest(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan,
        graph_context,
    )
    evidence_manifest = _chat_session_park_frontier_evidence_manifest(
        building_id,
        completed_step_results,
        failed_preparation,
        observation,
        plan_ref=plan_ref,
        plan=plan,
        proof_limits=proof_limits,
        not_proven=not_proven,
    )
    if task_source_ref:
        building_work["task_source_ref"] = task_source_ref
        evidence_manifest["task_source_ref"] = task_source_ref
    return BuildingLifecyclePacket(
        building_id=building_id,
        building_work=building_work,
        capture_events=tuple(events),
        raw_manifest=raw_manifest,
        evidence_manifest=evidence_manifest,
        proof_limits=proof_limits,
    )


def _adapter_error_frontier_capture_events(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
    *,
    include_building_opened: bool,
    step_index: int,
) -> tuple[CaptureEvent, ...]:
    step_ref = prepared.step_rows.step_ref
    slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    events: list[CaptureEvent] = []
    if include_building_opened:
        events.append(
            CaptureEvent(
                event_id=f"{step_index:02d}-{slug}-building-opened",
                event_type="building_opened",
                role_in_event="operator",
                axis_attribution="Support residue",
                raw_ref=_raw_ref("brick", step_index),
                not_proven=observation.not_proven,
                building_ref=building_id,
                receipt_text="Declared Building evidence root opened before adapter exception observation",
                facts={
                    "work_ref": "work/building-work.json",
                    "step_ref": step_ref,
                },
            )
        )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-brick-opened",
            event_type="brick_opened",
            role_in_event="operator",
            axis_attribution="Brick",
            raw_ref=_raw_ref("brick", step_index),
            not_proven=observation.not_proven,
            brick_ref=prepared.brick_instance_ref,
            receipt_text="Declared Brick work was opened for Agent receipt",
            facts={
                "work_statement": prepared.brick_work.work_statement,
                "comparison_rule": prepared.brick_work.comparison_rule,
                "required_return_shape": prepared.brick_work.required_return_shape,
                "source_facts": list(prepared.brick_work.source_facts),
            },
        )
    )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-agent-received",
            event_type="agent_received",
            role_in_event="performer",
            axis_attribution="Agent",
            raw_ref=_raw_ref("agent-received", step_index),
            not_proven=observation.not_proven,
            actor_ref=prepared.agent_object.object_ref,
            receipt_text="Agent received declared work before adapter exception observation",
            facts={
                "received_work_ref": observation.received_work_ref,
                "adapter_ref": observation.adapter_ref,
                "input_packet_ref": observation.input_packet_ref,
            },
        )
    )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-adapter-exception",
            event_type="support_note",
            role_in_event="support_writer",
            axis_attribution="Support residue",
            raw_ref=_raw_ref("adapter-error", step_index),
            not_proven=observation.not_proven,
            receipt_text="Adapter exception observed before Agent returned payload",
            facts={
                "adapter_error_ref": observation.adapter_error_ref,
                "error_kind": observation.error_kind,
                "exception_type": observation.exception_type,
            },
        )
    )
    return tuple(events)


def _chat_session_park_frontier_capture_events(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
    *,
    include_building_opened: bool,
    step_index: int,
) -> tuple[CaptureEvent, ...]:
    step_ref = prepared.step_rows.step_ref
    slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    events: list[CaptureEvent] = []
    if include_building_opened:
        events.append(
            CaptureEvent(
                event_id=f"{step_index:02d}-{slug}-building-opened",
                event_type="building_opened",
                role_in_event="operator",
                axis_attribution="Support residue",
                raw_ref=_raw_ref("brick", step_index),
                not_proven=observation.not_proven,
                building_ref=building_id,
                receipt_text="Declared Building evidence root opened before chat-session park observation",
                facts={
                    "work_ref": "work/building-work.json",
                    "step_ref": step_ref,
                },
            )
        )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-brick-opened",
            event_type="brick_opened",
            role_in_event="operator",
            axis_attribution="Brick",
            raw_ref=_raw_ref("brick", step_index),
            not_proven=observation.not_proven,
            brick_ref=prepared.brick_instance_ref,
            receipt_text="Declared Brick work was opened for Agent receipt",
            facts={
                "work_statement": prepared.brick_work.work_statement,
                "comparison_rule": prepared.brick_work.comparison_rule,
                "required_return_shape": prepared.brick_work.required_return_shape,
                "source_facts": list(prepared.brick_work.source_facts),
            },
        )
    )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-agent-received",
            event_type="agent_received",
            role_in_event="performer",
            axis_attribution="Agent",
            raw_ref=_raw_ref("agent-received", step_index),
            not_proven=observation.not_proven,
            actor_ref=prepared.agent_object.object_ref,
            receipt_text="Agent received declared work before chat-session park observation",
            facts={
                "received_work_ref": observation.received_work_ref,
                "adapter_ref": observation.adapter_ref,
                "input_packet_ref": observation.input_packet_ref,
                "work_envelope_ref": observation.work_envelope_ref,
            },
        )
    )
    events.append(
        CaptureEvent(
            event_id=f"{step_index:02d}-{slug}-chat-session-parked",
            event_type="support_note",
            role_in_event="support_writer",
            axis_attribution="Support residue",
            raw_ref=_raw_ref("chat-session-park", step_index),
            not_proven=observation.not_proven,
            receipt_text="Chat-session adapter parked work envelope before Agent returned payload",
            facts={
                "parked_ref": observation.parked_ref,
                "work_envelope_ref": observation.work_envelope_ref,
            },
        )
    )
    return tuple(events)


def _adapter_error_frontier_raw_manifest(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    complete_manifest = (
        _accumulated_raw_manifest(
            building_id,
            completed_step_results,
            graph_context,
            plan=plan,
        )
        if completed_step_results
        else {"building_id": building_id, "raw_refs": [], "entries": []}
    )
    entries = [dict(entry) for entry in complete_manifest.get("entries", []) if isinstance(entry, Mapping)]
    raw_refs = list(_text_tuple("raw_refs", complete_manifest.get("raw_refs", ())))
    failed_index = len(completed_step_results) + 1
    frontier_raw_refs = [
        _raw_ref("brick", failed_index),
        *(_raw_ref("agent-received", index) for index in range(1, failed_index + 1)),
        observation.raw_ref,
        _raw_ref("link-frontier", failed_index),
    ]
    for ref in frontier_raw_refs:
        if ref not in raw_refs:
            raw_refs.append(ref)
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/brick-work.jsonl",
        source="brick_protocol/support/operator/run.py declared Brick rows before adapter exception observation",
        content_shape="jsonl Brick work rows",
        axis_owner="Brick",
        raw_refs=[_raw_ref("brick", index) for index in range(1, failed_index + 1)],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/agent-received.jsonl",
        source="brick_protocol/support/operator/run.py Agent receipt observations before returned AgentFact",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=[_raw_ref("agent-received", index) for index in range(1, failed_index + 1)],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/adapter-error.jsonl",
        source="brick_protocol/support/operator/run.py adapter exception observation",
        content_shape="jsonl adapter exception observation rows",
        axis_owner="Agent",
        raw_refs=[observation.raw_ref],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="brick_protocol/support/operator/run.py declared Link rows and frontier absence observations",
        content_shape="jsonl Link transition rows and frontier absence rows",
        axis_owner="Link",
        raw_refs=[
            *(_raw_ref("link", index) for index in range(1, len(completed_step_results) + 1)),
            *_dynamic_reroute_raw_refs(plan),
            _raw_ref("link-frontier", failed_index),
            *_graph_link_raw_refs(graph_context),
        ],
    )
    return {
        "building_id": building_id,
        "raw_refs": raw_refs,
        "entries": entries,
    }


def _chat_session_park_frontier_raw_manifest(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    complete_manifest = (
        _accumulated_raw_manifest(
            building_id,
            completed_step_results,
            graph_context,
            plan=plan,
        )
        if completed_step_results
        else {"building_id": building_id, "raw_refs": [], "entries": []}
    )
    entries = [dict(entry) for entry in complete_manifest.get("entries", []) if isinstance(entry, Mapping)]
    raw_refs = list(_text_tuple("raw_refs", complete_manifest.get("raw_refs", ())))
    failed_index = len(completed_step_results) + 1
    frontier_raw_refs = [
        _raw_ref("brick", failed_index),
        *(_raw_ref("agent-received", index) for index in range(1, failed_index + 1)),
        observation.raw_ref,
        _raw_ref("link-frontier", failed_index),
    ]
    for ref in frontier_raw_refs:
        if ref not in raw_refs:
            raw_refs.append(ref)
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/brick-work.jsonl",
        source="brick_protocol/support/operator/run.py declared Brick rows before chat-session park observation",
        content_shape="jsonl Brick work rows",
        axis_owner="Brick",
        raw_refs=[_raw_ref("brick", index) for index in range(1, failed_index + 1)],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/agent-received.jsonl",
        source="brick_protocol/support/operator/run.py Agent receipt observations before returned AgentFact",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=[_raw_ref("agent-received", index) for index in range(1, failed_index + 1)],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/chat-session-park.jsonl",
        source="brick_protocol/support/operator/run.py chat-session park observation",
        content_shape="jsonl chat-session park observation rows",
        axis_owner="Agent",
        raw_refs=[observation.raw_ref],
    )
    _merge_or_append_raw_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="brick_protocol/support/operator/run.py declared Link rows and frontier absence observations",
        content_shape="jsonl Link transition rows and frontier absence rows",
        axis_owner="Link",
        raw_refs=[
            *(_raw_ref("link", index) for index in range(1, len(completed_step_results) + 1)),
            *_dynamic_reroute_raw_refs(plan),
            _raw_ref("link-frontier", failed_index),
            *_graph_link_raw_refs(graph_context),
        ],
    )
    return {
        "building_id": building_id,
        "raw_refs": raw_refs,
        "entries": entries,
    }


def _merge_or_append_raw_manifest_entry(
    entries: list[dict[str, Any]],
    *,
    path: str,
    source: str,
    content_shape: str,
    axis_owner: str,
    raw_refs,
) -> None:
    cleaned_refs = [ref for ref in dict.fromkeys(raw_refs) if ref]
    for entry in entries:
        if entry.get("path") == path:
            entry["source"] = source
            entry["content_shape"] = content_shape
            entry["axis_owner"] = axis_owner
            entry["raw_refs"] = cleaned_refs
            entry.setdefault("proof_limit", "support evidence only")
            entry.setdefault("record_role", "primary")
            return
    entries.append(
        {
            "path": path,
            "source": source,
            "content_shape": content_shape,
            "proof_limit": "support evidence only",
            "axis_owner": axis_owner,
            "record_role": "primary",
            "raw_refs": cleaned_refs,
        }
    )


def _adapter_error_frontier_evidence_manifest(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
    *,
    plan_ref: str,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> dict[str, Any]:
    step_output_refs = _step_output_manifest_refs(completed_step_results)
    step_output_refs.append(
        _step_output_adapter_error_ref(
            failed_preparation.step_rows.step_ref,
            _adapter_error_attempt_from_ref(observation.adapter_error_ref),
        )
    )
    raw_stream_refs = [
        "raw/brick-work.jsonl",
        "raw/agent-received.jsonl",
        "raw/adapter-error.jsonl",
        "raw/link.jsonl",
    ]
    claim_trace_refs = [
        "evidence/claim_trace/brick/work_contract.json",
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ]
    if completed_step_results:
        raw_stream_refs.insert(1, "raw/agent-return.jsonl")
        claim_trace_refs.extend(
            [
                "evidence/claim_trace/agent/returned_claims.json",
                "evidence/claim_trace/link/transfer_trace.json",
                "evidence/claim_trace/link/carry_trace.json",
                "evidence/claim_trace/link/sufficiency_trace.json",
                "evidence/claim_trace/link/movement_trace.json",
            ]
        )
    return {
        "building_id": building_id,
        "raw_manifest_ref": "raw/raw-manifest.json",
        "raw_stream_refs": raw_stream_refs,
        "claim_trace_refs": claim_trace_refs,
        "step_output_refs": step_output_refs,
        "building_map_ref": "work/building-map.json",
        "plan_snapshot": _plan_snapshot(plan_ref, plan),
        "frontier_observation": "Agent receipt observed before returned AgentFact",
        "proof_limits": list(proof_limits),
        "not_proven": list(_manifest_not_proven(not_proven)),
    }


def _chat_session_park_frontier_evidence_manifest(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
    *,
    plan_ref: str,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
) -> dict[str, Any]:
    step_output_refs = _step_output_manifest_refs(completed_step_results)
    attempt_index = _chat_session_park_attempt_from_ref(observation.parked_ref)
    step_output_refs.extend(
        [
            _step_output_work_envelope_ref(
                failed_preparation.step_rows.step_ref,
                attempt_index,
            ),
            _step_output_parked_ref(
                failed_preparation.step_rows.step_ref,
                attempt_index,
            ),
        ]
    )
    raw_stream_refs = [
        "raw/brick-work.jsonl",
        "raw/agent-received.jsonl",
        "raw/chat-session-park.jsonl",
        "raw/link.jsonl",
    ]
    claim_trace_refs = [
        "evidence/claim_trace/brick/work_contract.json",
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ]
    if completed_step_results:
        raw_stream_refs.insert(1, "raw/agent-return.jsonl")
        claim_trace_refs.extend(
            [
                "evidence/claim_trace/agent/returned_claims.json",
                "evidence/claim_trace/link/transfer_trace.json",
                "evidence/claim_trace/link/carry_trace.json",
                "evidence/claim_trace/link/sufficiency_trace.json",
                "evidence/claim_trace/link/movement_trace.json",
            ]
        )
    return {
        "building_id": building_id,
        "raw_manifest_ref": "raw/raw-manifest.json",
        "raw_stream_refs": raw_stream_refs,
        "claim_trace_refs": claim_trace_refs,
        "step_output_refs": step_output_refs,
        "building_map_ref": "work/building-map.json",
        "plan_snapshot": _plan_snapshot(plan_ref, plan),
        "frontier_observation": "Chat-session work envelope parked before AgentFact",
        "proof_limits": list(proof_limits),
        "not_proven": list(_manifest_not_proven(not_proven)),
    }


def _adapter_error_frontier_trace_packet(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    frontier_transition_lifecycle: Mapping[str, Any] | None = None,
) -> AdapterErrorFrontierTracePacket:
    failed_index = len(completed_step_results) + 1
    return AdapterErrorFrontierTracePacket(
        brick_raw_records=(
            *_brick_raw_records(building_id, completed_step_results),
            _adapter_error_brick_raw_record(building_id, failed_preparation, failed_index),
        ),
        agent_received_raw_records=tuple(
            _adapter_error_agent_received_raw_records(
                building_id,
                completed_step_results,
                failed_preparation,
                observation,
            )
        ),
        adapter_error_raw_records=(
            _adapter_error_raw_record(building_id, failed_preparation, observation),
        ),
        link_raw_records=(
            *_link_raw_records(
                building_id,
                completed_step_results,
                plan=plan,
                graph_context=graph_context,
            ),
            _adapter_error_link_frontier_raw_record(
                building_id,
                failed_preparation,
                observation,
                failed_index,
                transition_lifecycle=frontier_transition_lifecycle,
            ),
        ),
        brick_claim_facts=(
            *_brick_claim_facts(completed_step_results, proof_limits=proof_limits),
            _adapter_error_brick_claim_fact(failed_preparation, failed_index, proof_limits),
        ),
        agent_receipt_claim_facts=(
            _adapter_error_agent_receipt_claim_fact(
                failed_preparation,
                observation,
                failed_index,
                proof_limits,
            ),
        ),
        link_frontier_claim_facts=(
            _adapter_error_link_frontier_claim_fact(
                failed_preparation,
                observation,
                failed_index,
                proof_limits,
            ),
        ),
    )


def _chat_session_park_frontier_trace_packet(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    frontier_transition_lifecycle: Mapping[str, Any] | None = None,
) -> ChatSessionParkFrontierTracePacket:
    failed_index = len(completed_step_results) + 1
    return ChatSessionParkFrontierTracePacket(
        brick_raw_records=(
            *_brick_raw_records(building_id, completed_step_results),
            _adapter_error_brick_raw_record(building_id, failed_preparation, failed_index),
        ),
        agent_received_raw_records=tuple(
            _chat_session_park_agent_received_raw_records(
                building_id,
                completed_step_results,
                failed_preparation,
                observation,
            )
        ),
        park_raw_records=(
            _chat_session_park_raw_record(building_id, failed_preparation, observation),
        ),
        link_raw_records=(
            *_link_raw_records(
                building_id,
                completed_step_results,
                plan=plan,
                graph_context=graph_context,
            ),
            _chat_session_park_link_frontier_raw_record(
                building_id,
                failed_preparation,
                observation,
                failed_index,
                transition_lifecycle=frontier_transition_lifecycle,
            ),
        ),
        brick_claim_facts=(
            *_brick_claim_facts(completed_step_results, proof_limits=proof_limits),
            _adapter_error_brick_claim_fact(failed_preparation, failed_index, proof_limits),
        ),
        agent_receipt_claim_facts=(
            _chat_session_park_agent_receipt_claim_fact(
                failed_preparation,
                observation,
                failed_index,
                proof_limits,
            ),
        ),
        link_frontier_claim_facts=(
            _chat_session_park_link_frontier_claim_fact(
                failed_preparation,
                observation,
                failed_index,
                proof_limits,
            ),
        ),
    )


def _adapter_error_raw_record(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: AdapterErrorObservation,
) -> Mapping[str, Any]:
    return {
        "raw_ref": observation.raw_ref,
        "raw_refs": [observation.raw_ref],
        "building_id": building_id,
        "step_ref": prepared.step_rows.step_ref,
        "brick_instance_ref": prepared.brick_instance_ref,
        "agent_object_ref": observation.agent_object_ref,
        "adapter_ref": observation.adapter_ref,
        "selected_model_ref": observation.selected_model_ref,
        "adapter_error_ref": observation.adapter_error_ref,
        "error_kind": observation.error_kind,
        "exception_type": observation.exception_type,
        "message_excerpt": observation.message_excerpt,
        **dict(observation.diagnostic_excerpts),
        "agent_fact_created": False,
    }


def _chat_session_park_raw_record(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: ChatSessionParkObservation,
) -> Mapping[str, Any]:
    return {
        "kind": "chat_session_park_record",
        "schema_version": "chat-session-park-record-0",
        "raw_ref": observation.raw_ref,
        "raw_refs": [observation.raw_ref],
        "building_id": building_id,
        "step_ref": prepared.step_rows.step_ref,
        "brick_instance_ref": prepared.brick_instance_ref,
        "agent_object_ref": observation.agent_object_ref,
        "adapter_ref": observation.adapter_ref,
        "selected_model_ref": observation.selected_model_ref,
        "parked_ref": observation.parked_ref,
        "work_envelope_ref": observation.work_envelope_ref,
        "park_reason": "chat-session adapter parks declared work before provider invocation",
        "support_record_role": "waiting-for-chat-session-submission",
    }
