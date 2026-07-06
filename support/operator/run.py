"""Single public Building run surface for SIMPLE-RUN-0.

This support surface walks caller-declared Building rows and caller-supplied
Link facts. It records support evidence, but it does not choose Movement,
create undeclared GateFacts, judge success or quality, store secrets, or
own Brick / Agent / Link meaning.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import secrets
import subprocess

from datetime import datetime, timezone

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.link.carry import CarryFact
from brick_protocol.link.transfer import TransferFact

from brick_protocol.agent.performance import make_agent_performer_fact
from brick_protocol.agent.receipt import make_receipt_fact
from brick_protocol.agent.return_fact import AgentFact, make_agent_fact
from brick_protocol.brick.comparison import BrickComparisonFact
from brick_protocol.brick.work import BrickWork, parse_required_return_shape
from brick_protocol.link.gate import (
    GateFact,
    evaluate_declared_movement_gate,
    gate_required_return_fields,
    make_gate_fact,
)
from brick_protocol.link.movement import MovementFact
from brick_protocol.link.spec import LINK_ROW_ALLOWED_KEYS as _LINK_ROW_ALLOWED_KEYS
from brick_protocol.link.transition import TransitionFact
from brick_protocol.support.connection.adapter_constants import (
    ADAPTER_CHAT_SESSION,
)
from brick_protocol.support.connection.adapter_subprocess import (
    _timeout_expired_partial_output,
    _timeout_expired_reap_reason,
)
from brick_protocol.support.connection.adapter_validation import (
    safe_source_fact_body,
)
from brick_protocol.support.connection.agent_adapter import (
    AgentAdapterRequest,
    AgentAdapterParked,
    AgentAdapterResult,
    AgentBrainCallable,
    CommandRunner,
    connect_agent_brain,
)
from brick_protocol.support.connection.agent_resources import (
    render_agent_instruction_packet,
    validate_agent_refs,
)
from brick_protocol.support.operator.contracts import (
    AgentObjectContractData,
    AgentRunCompletionRecord,
    AgentRunPreparationRecord,
    BuildingPlanSupportResult,
    BuildingRunSupportResult,
    MinimalCrossingRecord,
    ThreeAxisStepRows,
)
from brick_protocol.support.operator.evidence_assembly import (
    _lifecycle_packet_from_mapping,
    agent_run_building_map_packet,
    agent_run_lifecycle_mapping,
    write_accumulated_building_evidence,
    write_adapter_error_frontier_evidence,
    write_chat_session_park_frontier_evidence,
    write_single_building_evidence,
)
from brick_protocol.support.operator.gate_sequence import (
    GateSequenceDecision,
    gate_sequence_decision_from_record,
    gate_sequence_decision_to_record,
    run_gate_sequence_policy,
)
from brick_protocol.support.operator.frontier_observation import observe_building_frontier
from brick_protocol.support.operator.runtime_env import load_report_env_into_process
from brick_protocol.support.operator.reporter import (
    building_event_kind_from_frontier,
    emit_building_event_for_policy,
    report_event_policy_from_plan,
)
from brick_protocol.support.operator.dynamic_walker import (
    _resume_dynamic_graph_walker,
    _run_dynamic_graph_walker,
)
from brick_protocol.support.operator.walker_kernel import (
    ResumeSeed,
    replay_gate_compute_live_record,
)
from brick_protocol.support.operator.walker_resume import (
    _building_engaged_reroute_budgets,
    _completed_step_frontier,
    _declared_graph_plan_from_birth_certificate,
    _read_written_dynamic_plan,
    _recorded_agent_returns,
    _resume_observations,
)
from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
from brick_protocol.support.operator.walker_frontier import (
    _chat_session_park_hold_record,
    _chat_session_park_paused_lifecycle,
)
from brick_protocol.support.operator.plan_validation import (
    _agent_run_handoff_packet,
    _artifact_grounding_required_return_fields,
    _caller_link_facts,
    _comparison_fact_from_observation,
    _incoming_link_handoff_refs,
    _movement_and_target_from_link_row,
    _plan_building_id,
    _step_fixture_from_plan_step,
    _validate_brick_row_write_need_for_scope,
    _validate_building_lifecycle_for_link_row,
    _validate_declared_gate_refs_for_link_row,
    _validate_gate_sequence_policy_for_link_row,
    _validate_route_decision_basis_for_link_row,
    validate_declared_building_plan,
    _validate_route_replay_plan_for_link_row,
    _task_source_ref_from_plan,
    _validate_transition_authoring_for_link_row,
    _validate_transition_lifecycle_for_link_row,
)
from brick_protocol.support.operator.primitives import (
    CASTING_FIELDS,
    NODE_CASTING_FIELDS,
    INLINE_TASK_SOURCE_REF,
    _AGENT_OBJECT_ALLOWED_KEYS,
    _AGENT_ROW_ALLOWED_KEYS,
    _AGENT_OBJECT_REF_FIELDS,
    _BRICK_ROW_ALLOWED_KEYS,
    _DEFAULT_AGENT_OBJECT_ROOT,
    _DECLARED_GATE_REFS_KEY,
    _FORBIDDEN_PAYLOAD_KEYS,
    _REPO_ROOT,
    _RETURN_FORBIDDEN_KEYS,
    _agent_run_not_proven,
    _first_text,
    _json_resource_mapping,
    _mapping,
    _merge_texts,
    _optional_fact,
    _optional_text_from_mapping,
    _optional_text_value,
    _path_segment,
    _proof_limits_tuple,
    _raw_ref,
    _require_fact,
    _require_mapping_value,
    _require_only_keys,
    _required_text,
    _reject_session_like_text,
    _resource_slug,
    _step_fact_ref,
    _text_tuple,
    _validate_no_payload_forbidden,
)
from brick_protocol.support.operator.write_observation import (
    _adapter_result_with_write_observation,
    _write_adapter_observation_before,
    _write_scope_from_brick_row,
)
from brick_protocol.support.operator.worktree_sandbox import (
    WorktreeSandboxError,
    anchor_wip_worktree_snapshot,
)
from brick_protocol.support.operator.proof_observation import (
    _adapter_result_with_proof_observation,
    _proof_obligations_from_brick_row,
)
from brick_protocol.support.recording.building_map import BuildingMapWriteResult
from brick_protocol.support.recording.capture import (
    BuildingLifecycleWriteResult,
    DEFAULT_BUILDINGS_ROOT,
    buildings_root_for,
    graph_ready_json_object,
    graph_ready_timestamp,
    project_ref_for_building_root,
)
from brick_protocol.support.recording.adapter_usage_meter import (
    write_adapter_usage_meter,
)
from brick_protocol.support.recording.contracts import StepOutputObservation
from brick_protocol.support.recording.step_outputs import (
    _step_output_dir_ref,
    write_step_output,
)


class AdapterFrontierEvidenceWritten(RuntimeError):
    """Raised after support writes frontier evidence for an adapter exception.

    The dynamic-walker surface raises this TYPED signal (mirroring the linear
    surface + chat-session-park) after the adapter-error frontier is written, and
    the public callers (``run_building_plan`` / ``resume_building_plan``) CATCH it
    and RETURN the already-held, resumable Building as a held
    ``BuildingPlanSupportResult``. The dynamic surface additionally carries the
    completed step results + the frontier evidence-write result so the caller can
    assemble that held result without re-reading disk; the linear surface (which
    has no multi-step accumulation) leaves those at their defaults.
    """

    def __init__(
        self,
        message: str,
        *,
        building_id: str,
        building_root: Path,
        written_files: tuple[Path, ...],
        plan_ref: str = "",
        completed_step_results: tuple[BuildingRunSupportResult, ...] = (),
        evidence_write: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.building_id = building_id
        self.building_root = building_root
        self.written_files = written_files
        self.plan_ref = plan_ref
        self.completed_step_results = completed_step_results
        self.evidence_write = evidence_write


class ChatSessionParkFrontierEvidenceWritten(RuntimeError):
    """Raised after support writes frontier evidence for a parked chat session."""

    def __init__(
        self,
        message: str,
        *,
        building_id: str,
        building_root: Path,
        written_files: tuple[Path, ...],
    ) -> None:
        super().__init__(message)
        self.building_id = building_id
        self.building_root = building_root
        self.written_files = written_files


class _AdapterRunInterrupted(RuntimeError):
    def __init__(
        self,
        *,
        prepared: AgentRunPreparationRecord,
        adapter_request: AgentAdapterRequest,
        adapter_error: Mapping[str, Any],
    ) -> None:
        super().__init__("adapter exception observed before AgentFact returned")
        self.prepared = prepared
        self.adapter_request = adapter_request
        self.adapter_error = adapter_error


class _AdapterRunParked(RuntimeError):
    def __init__(
        self,
        *,
        prepared: AgentRunPreparationRecord,
        adapter_request: AgentAdapterRequest,
        parked: AgentAdapterParked,
    ) -> None:
        super().__init__("chat-session adapter parked work before AgentFact returned")
        self.prepared = prepared
        self.adapter_request = adapter_request
        self.parked = parked


# E2/S11 GOD-MODULE SPLIT: the self-contained chat-session step subsystem
# (claim/submit/release + frontier-history preservation) was lifted VERBATIM
# into support/operator/run_chat_session.py. Re-imported here so every
# existing call site in run.py (and external run_module.* access) is unchanged.
from brick_protocol.support.operator.run_chat_session import (
    _chat_session_park_frontier_transition_lifecycle,
    _CHAT_SESSION_TOKEN_RE,
    _CHAT_SESSION_TOKEN_WORDS,
    claim_chat_session_envelope,
    submit_chat_session_return,
    release_chat_session_claim,
    _claim_chat_session_envelope_locked,
    _release_chat_session_claim_locked,
    _with_chat_session_claim_lock,
    _chat_session_step_output_dir,
    _chat_session_attempt_index_from_step_dir,
    _active_chat_session_claim,
    _mint_chat_session_claim_token,
    _validate_chat_session_claim_token,
    _validate_chat_session_submission_return,
    _reject_chat_session_session_text,
    _read_chat_session_optional_json,
    _read_chat_session_json_object,
    _write_json_atomic,
    _write_json_exclusive,
    _append_chat_session_raw_record,
    _chat_session_frontier_history_snapshot,
    _adapter_error_frontier_history_snapshot,
    _preserve_chat_session_frontier_history_after_resume,
    _preserve_adapter_error_frontier_history_after_resume,
    _preserve_chat_session_link_frontier_records,
    _chat_session_jsonl_objects,
    _chat_session_raw_refs_from_jsonl,
    _chat_session_raw_refs_for_manifest_entry,
    _chat_session_raw_refs_from_value,
    _merge_chat_session_manifest_entry,
    _chat_session_building_id,
)


def run_building_once(
    fixture: Mapping[str, Any] | str | Path,
    *,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingRunSupportResult:
    """Run one declared Building step and write support projections."""

    packet = _fixture_mapping(fixture)
    _validate_no_payload_forbidden("fixture", packet, _FORBIDDEN_PAYLOAD_KEYS)
    # ENGINE SEAM (#56, MAJOR-6 codex review 0619): run_building_once is a PUBLIC
    # building-execution entry that emits report events (terminal events below) but
    # is NOT dispatched through run_building_plan, so it must cross the loader on
    # its own. Auto-load the allowlisted slack/dashboard creds and THREAD them as
    # report_env into the sink gating + delivery. Report keys are returned for
    # threading and are NOT injected into os.environ (no child leak); only the
    # provider key (GEMINI/GOOGLE) lands in os.environ for the gemini adapter.
    # When the caller already supplied report_env, still cross the loader so the
    # provider key reaches os.environ, but the caller's mapping wins for threading.
    # EMPTY == AUTO-LOAD (footgun fix): treat an EMPTY mapping ({}) the same as
    # None and auto-load. A caller who passes {} means "use the default creds",
    # NOT "deliberately blank the env" -- so an empty mapping must NEVER silently
    # win the sink-gating and close the Slack/dashboard gate (the old `is None`
    # check let {} take the else branch, dropping every env-gated sink with no
    # error -> "Slack is broken" misdiagnosis). `not report_env` is True for both
    # None and {}; a NON-EMPTY custom env is still respected for threading.
    if not report_env:
        report_env = load_report_env_into_process()
    else:
        load_report_env_into_process()
    report_event_policy = report_event_policy_from_plan(packet)
    # FIX-C (codex review 0611) TASK-SOURCE ADMISSION on the SINGLE-STEP
    # surface, parity with run_building_plan strictness (P11b): a declared
    # task_source_ref that is a repo path and does not resolve to an existing
    # file is a broken declared road and must reject LOUDLY here -- before
    # preparation / provider invocation -- instead of the prior behavior where
    # _source_fact_bodies silently skipped the missing file (the declared task
    # body just vanished from the prompt and evidence). Packets without
    # task_source_ref -> no check; the inline sentinel requires its carried
    # task_statement body (same validator, same rejects as the plan walker).
    _task_source_ref_from_plan(packet, repo_root=_REPO_ROOT)
    link_facts = _caller_link_facts(packet)
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else packet.get("proof_limits")
    )
    prepared = prepare_agent_run_from_step_rows(packet, proof_limits=checked_proof_limits)
    # LIVE RUN ADMISSION on the SINGLE-STEP surface is STRICT about write grants,
    # parity with run_building_plan and the dynamic walker/resume: a brick row
    # carrying write_scope must EXPLICITLY declare its write NEED
    # (requires_brick_write_scope: true). This fires BEFORE the scope leaves
    # toward AgentAdapterRequest (_adapter_request_from_prepared /
    # _write_scope_from_brick_row) and before any provider invocation, so a
    # smuggled scope on a fixture packet can never silently open workspace write.
    _validate_brick_row_write_need_for_scope(
        prepared.step_rows.brick_row,
        require_write_need_marker=True,
    )
    # CHARTER-INJECT (0618): derive the vessel project_ref from this single-step
    # building's root (output_root + building_id) so its README charter is
    # injected into the role packet, parity with the plan walker. A
    # default-root / legacy building -> None (no charter, no crash).
    single_step_project_ref = project_ref_for_building_root(
        Path(output_root) / prepared.building_id,
        repo_root=_REPO_ROOT,
    )
    adapter_request = _adapter_request_from_prepared(
        packet,
        prepared,
        project_ref=single_step_project_ref,
    )
    try:
        adapter_result = _adapter_result_or_interrupt(
            prepared,
            adapter_request,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
        )
    except _AdapterRunParked as parked:
        evidence_write = write_chat_session_park_frontier_evidence(
            building_id=prepared.building_id,
            plan_ref=_optional_text_value(packet.get("plan_ref")) or "building-plan:single-step",
            plan=packet,
            completed_step_results=(),
            failed_preparation=parked.prepared,
            adapter_request=parked.adapter_request,
            output_root=output_root,
            overwrite_existing=overwrite_existing,
            proof_limits=checked_proof_limits,
            frontier_transition_lifecycle=_chat_session_park_frontier_transition_lifecycle(
                building_id=prepared.building_id,
                completed_step_results=(),
                failed_preparation=parked.prepared,
            ),
        )
        if report_event_policy:
            terminal_event_kind = building_event_kind_from_frontier(
                evidence_write.lifecycle_write.root,
                repo_root=_REPO_ROOT,
            )
            _emit_building_event_best_effort(
                report_event_policy,
                event_kind=terminal_event_kind,
                building_id=prepared.building_id,
                building_root=evidence_write.lifecycle_write.root,
                current_brick_ref=parked.prepared.brick_instance_ref,
                report_env=report_env,
                report_slack_sender=report_slack_sender,
                overwrite_existing=overwrite_existing,
            )
        raise ChatSessionParkFrontierEvidenceWritten(
            "chat-session park frontier evidence written before AgentFact returned",
            building_id=prepared.building_id,
            building_root=evidence_write.lifecycle_write.root,
            written_files=evidence_write.written_files,
        ) from parked
    except _AdapterRunInterrupted as interrupted:
        evidence_write = write_adapter_error_frontier_evidence(
            building_id=prepared.building_id,
            plan_ref=_optional_text_value(packet.get("plan_ref")) or "building-plan:single-step",
            plan=packet,
            completed_step_results=(),
            failed_preparation=interrupted.prepared,
            adapter_request=interrupted.adapter_request,
            adapter_error=interrupted.adapter_error,
            output_root=output_root,
            overwrite_existing=overwrite_existing,
            proof_limits=checked_proof_limits,
        )
        raise AdapterFrontierEvidenceWritten(
            "adapter exception frontier evidence written before AgentFact returned",
            building_id=prepared.building_id,
            building_root=evidence_write.lifecycle_write.root,
            written_files=evidence_write.written_files,
        ) from interrupted
    completion = complete_agent_run_from_prepared(
        prepared,
        returned_value=adapter_result.returned_value,
        adapter_result=adapter_result,
        comparison_observation=packet.get("comparison_observation"),
        proof_limits=_merge_texts(checked_proof_limits, adapter_result.proof_limits),
        **link_facts,
    )
    evidence_write = write_single_building_evidence(
        completion,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
    )
    result = BuildingRunSupportResult(
        building_id=prepared.building_id,
        preparation=prepared,
        adapter_result=adapter_result,
        completion=completion,
        lifecycle_write=evidence_write.lifecycle_write,
        building_map_write=evidence_write.building_map_write,
        written_files=evidence_write.written_files,
        capture_event_types=evidence_write.capture_event_types,
        building_map_packet=evidence_write.building_map_packet,
        proof_limits=_merge_texts(
            checked_proof_limits,
            adapter_result.proof_limits,
            completion.proof_limits,
            evidence_write.proof_limits,
        ),
        not_proven=_merge_texts(
            packet.get("not_proven"),
            adapter_result.not_proven,
            completion.not_proven,
        ),
    )
    if report_event_policy:
        terminal_event_kind = building_event_kind_from_frontier(
            evidence_write.lifecycle_write.root,
            repo_root=_REPO_ROOT,
        )
        terminal_event = _emit_building_event_best_effort(
            report_event_policy,
            event_kind=terminal_event_kind,
            building_id=prepared.building_id,
            building_root=evidence_write.lifecycle_write.root,
            current_brick_ref=prepared.brick_instance_ref,
            last_completed_step_ref=prepared.step_rows.step_ref,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            overwrite_existing=overwrite_existing,
        )
        if terminal_event is not None:
            object.__setattr__(result, "_report_event_observations", (terminal_event,))
    return result


def _held_result_from_adapter_frontier_signal(
    signal: AdapterFrontierEvidenceWritten,
) -> BuildingPlanSupportResult:
    """Assemble the held ``BuildingPlanSupportResult`` for a caught adapter signal.

    When the dynamic walker hits an adapter exception/timeout it writes the
    adapter-error frontier (a resumable hold) and raises the TYPED
    ``AdapterFrontierEvidenceWritten`` carrying the completed step results + the
    frontier evidence-write result. Rather than crash, the public callers return
    THIS held result: the building is already held + resumable on disk
    (hold_reason=adapter_error_frontier, paused lifecycle, disposition_required).
    The frontier write itself is byte-identical -- this only repackages the
    already-written evidence as the public return shape.
    """

    evidence_write = signal.evidence_write
    if evidence_write is None:
        raise signal
    step_results = signal.completed_step_results
    return BuildingPlanSupportResult(
        building_id=signal.building_id,
        plan_ref=signal.plan_ref,
        step_results=step_results,
        lifecycle_write=evidence_write.lifecycle_write,
        building_map_write=evidence_write.building_map_write,
        written_files=evidence_write.written_files,
        capture_event_types=evidence_write.capture_event_types,
        building_map_packet=evidence_write.building_map_packet,
        proof_limits=_merge_texts(
            evidence_write.proof_limits,
            *(r.proof_limits for r in step_results),
        ),
        not_proven=_merge_texts(*(r.not_proven for r in step_results)),
    )


def _with_close_wip_anchor(
    result: BuildingPlanSupportResult,
    *,
    adapter_cwd: Path | str | None,
) -> BuildingPlanSupportResult:
    """Return ``result`` with a close-time WIP anchor ref when dirty work exists.

    The anchor is a support preservation mechanic for direct ``adapter_cwd`` runs.
    It records bytes under ``refs/brick/wip/<building_id>``; it does not decide
    Movement, completion, success, or quality.
    """

    if result.anchored_ref:
        return result
    if adapter_cwd is None:
        return result
    cwd = Path(adapter_cwd)
    try:
        anchored = anchor_wip_worktree_snapshot(
            cwd,
            result.building_id,
            message=(
                f"BRICK WIP anchor: {result.building_id}\n\n"
                "source=run_building_plan_close\n"
                f"evidence_root={result.lifecycle_write.root}\n"
            ),
        )
    except (OSError, WorktreeSandboxError):
        anchored = None
    if anchored is None:
        return result
    stamped = dataclasses.replace(result, anchored_ref=anchored[0])
    # dataclasses.replace mints a NEW frozen instance — carry the in-memory
    # side channels the dynamic walker attached via object.__setattr__, or the
    # anchor stamp silently strips reroute records / walker evidence / report
    # observations from every anchored result (0706 live-sweep catch:
    # bounded_agent P4 AttributeError on _dynamic_walker_evidence).
    for side_channel in (
        "_dynamic_walker_reroute_records",
        "_dynamic_walker_evidence",
        "_report_event_observations",
    ):
        if hasattr(result, side_channel):
            object.__setattr__(stamped, side_channel, getattr(result, side_channel))
    return stamped


def run_building_plan(
    plan: Mapping[str, Any] | str | Path,
    *,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingPlanSupportResult:
    """Walk one declared graph Building plan through the dynamic graph walker.

    The public single-Building entrypoint always dispatches to
    ``_run_dynamic_graph_walker``. Non-graph packets are rejected by the dynamic
    walker admission guard in ``support/operator/walker_kernel.py``.
    """

    packet = _fixture_mapping(plan)
    _validate_no_payload_forbidden("plan", packet, _FORBIDDEN_PAYLOAD_KEYS)
    # ENGINE SEAM (#56): auto-load the allowlisted slack/dashboard/provider creds
    # from ~/.brick/report.env (+ ~/.brick/credentials.env), regardless of how the
    # operator launched. Idempotent, env-precedence-respecting, 0600-gated (TOCTOU-
    # safe fd-tied), never echoes a value, no-ops when the files are absent.
    # INJECTION SCOPE (MAJOR-5, narrowed): the report keys are RETURNED for
    # threading into the report-sink gating + delivery (NOT injected into
    # os.environ, so no child-subprocess leak); only the provider key
    # (GEMINI/GOOGLE) is injected into os.environ for the gemini adapter. The
    # returned report_env is threaded to the walker below, so the env-gated sinks
    # always see the creds through the threaded mapping (never the global env).
    # EMPTY == AUTO-LOAD (footgun fix): an EMPTY mapping ({}) is treated like None
    # and auto-loads, so a caller passing {} ("use defaults") can never silently
    # win the threading and close the env-gated Slack/dashboard sinks. A NON-EMPTY
    # custom env is still respected. `not report_env` is True for both None and {}.
    if not report_env:
        report_env = load_report_env_into_process()
    else:
        load_report_env_into_process()
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else packet.get("proof_limits")
    )
    try:
        result = _run_dynamic_graph_walker(
            packet,
            output_root=output_root,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            checked_proof_limits=checked_proof_limits,
            run_step=_run_building_step_without_writing,
            record_step_output=_write_step_output_on_step_close,
            write_accumulated=write_accumulated_building_evidence,
            write_adapter_error_frontier=write_adapter_error_frontier_evidence,
            write_chat_session_park_frontier=write_chat_session_park_frontier_evidence,
            chat_session_park_frontier_exception=ChatSessionParkFrontierEvidenceWritten,
            adapter_frontier_exception=AdapterFrontierEvidenceWritten,
            repo_root=_REPO_ROOT,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
        )
        return _with_close_wip_anchor(result, adapter_cwd=adapter_cwd)
    except AdapterFrontierEvidenceWritten as adapter_frontier:
        # The adapter raised/timed out before an AgentFact existed; the dynamic
        # walker has already written the resumable adapter-error frontier (hold).
        # Return that already-held Building as a clean held result instead of
        # crashing -- a flaky adapter call ends recoverable, not fatal.
        return _with_close_wip_anchor(
            _held_result_from_adapter_frontier_signal(adapter_frontier),
            adapter_cwd=adapter_cwd,
        )


def resume_building_plan(
    building_root: Path | str,
    *,
    overwrite_existing: bool = True,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingPlanSupportResult:
    """Resume a held dynamic Building from written evidence and a disposition row.

    This is a separate resume verb, not ``walker_mode``. It rehydrates completed
    steps from recorded step outputs / raw Agent returns so completed Agent work is
    not called again, then lets the admitted dynamic graph walker continue from the
    declared human/COO disposition.

    Proof limit: a chat-session parked Building is intentionally not resumable by
    this generic disposition surface; S2/S3 submit/claim owns that resume authority.
    """

    root = Path(building_root)
    # ENGINE SEAM (#56): resume passes through here for held->disposition walks, so
    # auto-load the env-gated report creds on the resume path too (same discipline
    # as run_building_plan: allowlist, 0600 gate TOCTOU-safe, env precedence, no
    # value echo, absent-file no-op). INJECTION SCOPE (MAJOR-5, narrowed): report
    # keys are RETURNED for threading (not injected into os.environ -> no child
    # leak); only the provider key lands in os.environ. The threaded report_env
    # flows to the resumed walker so its sinks read the threaded mapping.
    # EMPTY == AUTO-LOAD (footgun fix): an EMPTY mapping ({}) is treated like None
    # and auto-loads, so a caller passing {} ("use defaults") can never silently
    # win the threading and close the env-gated Slack/dashboard sinks. A NON-EMPTY
    # custom env is still respected. `not report_env` is True for both None and {}.
    if not report_env:
        report_env = load_report_env_into_process()
    else:
        load_report_env_into_process()
    checked_proof_limits = _proof_limits_tuple(proof_limits)
    adapter_cwd_refusal = _unsafe_resume_adapter_cwd(adapter_cwd, repo_root=_REPO_ROOT)
    if adapter_cwd_refusal and local_callables is None and command_runner is None:
        raise ValueError(adapter_cwd_refusal)
    frontier = observe_building_frontier(root, repo_root=_REPO_ROOT)
    if frontier.get("frontier_kind") == "chat_session_parked":
        return _with_close_wip_anchor(
            _resume_chat_session_parked_building_plan(
                root,
                overwrite_existing=overwrite_existing,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=adapter_cwd,
                adapter_timeout_seconds=adapter_timeout_seconds,
                checked_proof_limits=checked_proof_limits,
                report_env=report_env,
                report_slack_sender=report_slack_sender,
            ),
            adapter_cwd=adapter_cwd,
        )
    frontier_history = _adapter_error_frontier_history_snapshot(root)
    try:
        result = _resume_dynamic_graph_walker(
            root,
            output_root=root.parent,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            checked_proof_limits=checked_proof_limits,
            run_step=_run_building_step_without_writing,
            replay_step=_replay_building_step_from_returned,
            record_step_output=_write_step_output_on_step_close,
            write_accumulated=write_accumulated_building_evidence,
            write_adapter_error_frontier=write_adapter_error_frontier_evidence,
            write_chat_session_park_frontier=write_chat_session_park_frontier_evidence,
            chat_session_park_frontier_exception=ChatSessionParkFrontierEvidenceWritten,
            repo_root=_REPO_ROOT,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
        )
    except AdapterFrontierEvidenceWritten as adapter_frontier:
        # A resumed walk can hit a FRESH adapter exception/timeout (the held step's
        # provider call after disposition). The forward walk has already written the
        # adapter-error frontier; return that clean held result instead of crashing,
        # and still preserve the prior adapter-error frontier history exactly as the
        # normal-return path does.
        result = _held_result_from_adapter_frontier_signal(adapter_frontier)
    _preserve_adapter_error_frontier_history_after_resume(root, frontier_history)
    return _with_close_wip_anchor(result, adapter_cwd=adapter_cwd)


def _unsafe_resume_adapter_cwd(
    adapter_cwd: Path | str | None,
    *,
    repo_root: Path | str,
) -> str:
    """Return a refusal reason when resumed live work would target the live repo.

    The generic resume API remains usable for deterministic replay tests; public
    provider-style resume refuses this reason before any post-HOLD adapter
    dispatch can write there.
    """

    if adapter_cwd is None:
        return ""
    try:
        candidate = Path(adapter_cwd).expanduser().resolve()
        repo = Path(repo_root).expanduser().resolve()
    except OSError as exc:
        return f"invalid_adapter_cwd: adapter_cwd could not be resolved: {type(exc).__name__}: {exc}"
    if candidate == repo or _path_is_relative_to(candidate, repo):
        return (
            "adapter_cwd_refused_live_repo: resume_building_plan refuses "
            "adapter_cwd inside the live repo/customer tree; resume through a "
            "sandboxed customer wrapper or pass an isolated adapter_cwd"
        )
    return ""


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resume_chat_session_parked_building_plan(
    root: Path,
    *,
    overwrite_existing: bool,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingPlanSupportResult:
    plan, evidence = _read_written_dynamic_plan(root)
    if not evidence.get("held"):
        raise ValueError("chat-session parked resume requires held dynamic_walker_evidence")
    hold_record = _require_mapping_value("dynamic_walker_evidence.hold", evidence.get("hold"))
    if _optional_text_value(hold_record.get("hold_reason")) != "chat_session_park_frontier":
        raise ValueError("chat-session parked resume requires chat_session_park_frontier hold")
    declared_plan = _declared_graph_plan_from_birth_certificate(root)
    if declared_plan is None:
        raise ValueError(
            "chat-session parked resume requires a graph declared-building-plan "
            "birth-certificate; linear chat-session replay is not admitted"
        )
    declared_plan = dict(declared_plan)
    recorded_budgets = evidence.get("node_reroute_budgets")
    if recorded_budgets is None:
        if _building_engaged_reroute_budgets(evidence):
            raise ValueError("chat-session parked resume evidence is missing node_reroute_budgets")
    elif not isinstance(recorded_budgets, Mapping):
        raise ValueError("chat-session parked resume node_reroute_budgets must be a mapping")
    else:
        for node_ref, value in recorded_budgets.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    "chat-session parked resume node_reroute_budgets has malformed "
                    f"budget for {node_ref!r}: {value!r}"
                )
        if recorded_budgets:
            declared_plan["node_reroute_budgets"] = dict(recorded_budgets)

    submitted = _validated_chat_session_resume_submission(root, hold_record)
    recorded_returns = _recorded_agent_returns(root)
    replay_returns: dict[str, list[Any]] = {}
    gate_records: dict[str, list[Any]] = {}
    replay_recorded_at: dict[str, list[str]] = {}
    for item in recorded_returns:
        step = _optional_text_value(item.get("step_ref")) or ""
        replay_returns.setdefault(step, []).append(item.get("returned"))
        gate_records.setdefault(step, []).append(item.get("gate_sequence_decision_record"))
        replay_recorded_at.setdefault(step, []).append(
            _optional_text_value(item.get("recorded_at")) or ""
        )

    parked_step_ref = submitted["step_ref"]
    replay_returns.setdefault(parked_step_ref, []).append(submitted["returned"])
    gate_records.setdefault(parked_step_ref, []).append(replay_gate_compute_live_record())
    replay_recorded_at.setdefault(parked_step_ref, []).append(submitted["recorded_at"])

    expected_replay_counts = _completed_step_frontier(root)
    expected_replay_counts[parked_step_ref] = max(
        int(expected_replay_counts.get(parked_step_ref, 0)),
        len(replay_returns[parked_step_ref]),
    )

    pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
    seed = ResumeSeed(
        replay_returns=replay_returns,
        gate_records=gate_records,
        replay_step=_replay_building_step_from_returned,
        budget_delta={},
        disposition_action="forward",
        held_source_step_ref=parked_step_ref,
        held_cascade_depth=int(hold_record.get("cascade_depth", 0)),
        pending_target_ref=pending_target,
        author_ref="",
        paused_at_ref=_hold_paused_at_ref(hold_record),
        hold_record=hold_record,
        existing_resume_observations=tuple(_resume_observations(evidence)),
        expected_replay_counts=dict(expected_replay_counts),
        replay_recorded_at=replay_recorded_at,
        skip_lifecycle_stamp=True,
        resume_authority_ref=submitted["claim_ref"],
    )
    frontier_history = _chat_session_frontier_history_snapshot(root)
    try:
        result = _run_dynamic_graph_walker(
            declared_plan,
            output_root=root.parent,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            checked_proof_limits=checked_proof_limits,
            run_step=_run_building_step_without_writing,
            record_step_output=_write_step_output_on_step_close,
            write_accumulated=write_accumulated_building_evidence,
            write_adapter_error_frontier=write_adapter_error_frontier_evidence,
            write_chat_session_park_frontier=write_chat_session_park_frontier_evidence,
            chat_session_park_frontier_exception=ChatSessionParkFrontierEvidenceWritten,
            adapter_frontier_exception=AdapterFrontierEvidenceWritten,
            repo_root=_REPO_ROOT,
            resume_seed=seed,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
        )
    except AdapterFrontierEvidenceWritten as adapter_frontier:
        # A submitted chat-session work item can itself hit an adapter exception on
        # its post-submit provider call; the forward walk wrote the adapter-error
        # frontier, so return that clean held result instead of crashing.
        result = _held_result_from_adapter_frontier_signal(adapter_frontier)
    _preserve_chat_session_frontier_history_after_resume(root, frontier_history)
    return result


def _validated_chat_session_resume_submission(
    root: Path,
    hold_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    step_ref = _required_text("hold.source_step_ref", hold_record.get("source_step_ref"))
    attempt_number = hold_record.get("attempt_number")
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int) or attempt_number < 1:
        raise ValueError("chat-session hold record carries invalid attempt_number")
    step_dir = _chat_session_step_output_dir(
        root,
        step_ref=step_ref,
        attempt_index=attempt_number,
    )
    claim = _active_chat_session_claim(step_dir)
    if not (step_dir / "submission.json").is_file():
        raise ValueError("parked building resume requires chat-session submission")
    submission = _read_chat_session_json_object(step_dir / "submission.json")
    if submission.get("kind") != "chat_session_submission_record":
        raise ValueError("chat-session submission.json has wrong kind")
    claim_token = _validate_chat_session_claim_token(claim.get("claim_token"))
    submission_token = _validate_chat_session_claim_token(submission.get("claim_token"))
    if submission_token != claim_token:
        raise ValueError("chat-session resume rejected token mismatch")
    returned = _validate_chat_session_submission_return(
        root,
        step_dir,
        _require_mapping_value("chat_session_submission.returned", submission.get("returned")),
    )
    return {
        "step_ref": step_ref,
        "returned": returned,
        "recorded_at": _optional_text_value(submission.get("recorded_at"))
        or graph_ready_timestamp(),
        "claim_ref": _required_text("claim.claim_ref", claim.get("claim_ref")),
    }


def _run_building_step_without_writing(
    fixture: Mapping[str, Any],
    *,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    proof_limits: Iterable[str] | str | None,
) -> BuildingRunSupportResult:
    """Run one declared step and keep the evidence in memory for accumulation."""

    packet = _fixture_mapping(fixture)
    _validate_no_payload_forbidden("fixture", packet, _FORBIDDEN_PAYLOAD_KEYS)
    link_facts = _caller_link_facts(packet)
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else packet.get("proof_limits")
    )
    prepared = prepare_agent_run_from_step_rows(packet, proof_limits=checked_proof_limits)
    adapter_request = _adapter_request_from_prepared(packet, prepared)
    adapter_result = _adapter_result_or_interrupt(
        prepared,
        adapter_request,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
    )
    completion = complete_agent_run_from_prepared(
        prepared,
        returned_value=adapter_result.returned_value,
        adapter_result=adapter_result,
        comparison_observation=packet.get("comparison_observation"),
        proof_limits=_merge_texts(checked_proof_limits, adapter_result.proof_limits),
        **link_facts,
    )
    lifecycle_packet = _lifecycle_packet_from_mapping(
        completion.lifecycle_packet_mapping,
        movement=completion.crossing_record.link_fact.movement,
    )
    empty_lifecycle_write = BuildingLifecycleWriteResult(
        root=Path(),
        written_files=(),
        proof_limits=lifecycle_packet.proof_limits,
    )
    empty_map_write = BuildingMapWriteResult(root=Path(), path=Path(), written_files=())
    return BuildingRunSupportResult(
        building_id=prepared.building_id,
        preparation=prepared,
        adapter_result=adapter_result,
        completion=completion,
        lifecycle_write=empty_lifecycle_write,
        building_map_write=empty_map_write,
        written_files=(),
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=completion.building_map_packet,
        proof_limits=_merge_texts(
            checked_proof_limits,
            adapter_result.proof_limits,
            completion.proof_limits,
        ),
        not_proven=_merge_texts(
            packet.get("not_proven"),
            adapter_result.not_proven,
            completion.not_proven,
        ),
    )


def _replay_building_step_from_returned(
    fixture: Mapping[str, Any],
    *,
    returned_value: Any,
    recorded_at: str = "",
    gate_sequence_decision_record: Mapping[str, Any] | None = None,
    proof_limits: Iterable[str] | str | None,
) -> BuildingRunSupportResult:
    """Rebuild one completed step from recorded Agent returned evidence.

    This helper deliberately does not call ``connect_agent_brain``. It recreates
    the same support dataclasses the accumulated writer expects from the written
    returned payload.

    U5.5 RESUME-GATE-RECORD: when a ``gate_sequence_decision_record`` is supplied
    (the step recorded one AT-TIME), the rebuilt result carries the RECONSTRUCTED
    gate-sequence decision so the claim-trace seam can RE-RECORD the gate facts. It
    READS the recorded decision back — it NEVER calls ``run_gate_sequence_policy``
    (no recompute / no re-derive on the replay path).
    """

    packet = _fixture_mapping(fixture)
    _validate_no_payload_forbidden("fixture", packet, _FORBIDDEN_PAYLOAD_KEYS)
    link_facts = _caller_link_facts(packet)
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else packet.get("proof_limits")
    )
    prepared = prepare_agent_run_from_step_rows(packet, proof_limits=checked_proof_limits)
    adapter_request = _adapter_request_from_prepared(packet, prepared)
    adapter_result = AgentAdapterResult(
        request=adapter_request,
        returned_value=returned_value,
        proof_limits=checked_proof_limits,
        not_proven=_agent_run_not_proven(),
    )
    completion = complete_agent_run_from_prepared(
        prepared,
        returned_value=returned_value,
        adapter_result=adapter_result,
        comparison_observation=packet.get("comparison_observation"),
        proof_limits=checked_proof_limits,
        **link_facts,
    )
    lifecycle_packet = _lifecycle_packet_from_mapping(
        completion.lifecycle_packet_mapping,
        movement=completion.crossing_record.link_fact.movement,
    )
    empty_lifecycle_write = BuildingLifecycleWriteResult(
        root=Path(),
        written_files=(),
        proof_limits=lifecycle_packet.proof_limits,
    )
    empty_map_write = BuildingMapWriteResult(root=Path(), path=Path(), written_files=())
    # U5.5 RESUME-GATE-RECORD: READ the recorded AT-TIME gate-sequence decision back
    # (fail-closed on a malformed record). None when the step declared no policy.
    if (
        isinstance(gate_sequence_decision_record, Mapping)
        and gate_sequence_decision_record.get("support_replay_gate")
        == "__brick_protocol_compute_live_gate_at_reentry__"
    ):
        replayed_gate_decision = None
    else:
        replayed_gate_decision = (
            gate_sequence_decision_from_record(gate_sequence_decision_record)
            if gate_sequence_decision_record is not None
            else None
        )
    return BuildingRunSupportResult(
        building_id=prepared.building_id,
        preparation=prepared,
        adapter_result=adapter_result,
        completion=completion,
        lifecycle_write=empty_lifecycle_write,
        building_map_write=empty_map_write,
        written_files=(),
        capture_event_types=tuple(event.event_type for event in lifecycle_packet.capture_events),
        building_map_packet=completion.building_map_packet,
        proof_limits=_merge_texts(
            checked_proof_limits,
            adapter_result.proof_limits,
            completion.proof_limits,
        ),
        not_proven=_merge_texts(
            packet.get("not_proven"),
            adapter_result.not_proven,
            completion.not_proven,
        ),
        recorded_at=recorded_at,
        gate_sequence_decision=replayed_gate_decision,
    )


# run_building_intake (support/operator/driver.py) writes its materialized
# INPUT plan to <building_root>/declared-building-plan.json and then
# immediately walks it; without an admission for exactly that artifact, the
# first defaults use always self-collided here (FileExistsError). The
# admission is fail-closed and EXACT: a pre-existing root is admitted IFF it
# holds ONLY regular non-symlink file(s) named in this set -- any other name,
# any subdirectory, any symlink, or an EMPTY root still rejects. (The run's
# own work/declared-building-plan.json declaration packet lives under work/
# and is a different file.) This PRE-ADAPTER predicate intentionally remains
# narrower than support.recording.adapter_error_frontier's POST-ADAPTER
# declaration-chain/root-state handling, which may preserve report/declaration
# artifacts or mark partial roots after an adapter interruption. Parity copy
# lives in walker_kernel.py.
_PREEXISTING_ROOT_INTAKE_ARTIFACTS: frozenset[str] = frozenset(
    {"declared-building-plan.json"}
)


def _root_holds_only_intake_plan_artifact(root: Path) -> bool:
    entries = list(root.iterdir())
    if not entries:
        return False
    for entry in entries:
        if entry.name not in _PREEXISTING_ROOT_INTAKE_ARTIFACTS:
            return False
        if entry.is_symlink() or not entry.is_file():
            return False
    return True


def _preflight_step_output_building_root(
    output_root: Path | str,
    building_id: str,
    *,
    overwrite_existing: bool,
) -> Path:
    root = Path(output_root) / building_id
    if root.exists():
        if not root.is_dir():
            raise NotADirectoryError(f"Building lifecycle root is not a directory: {root}")
        if not overwrite_existing and not _root_holds_only_intake_plan_artifact(root):
            raise FileExistsError(
                "Building lifecycle root already exists; choose a new building_id "
                "or pass overwrite_existing=True"
            )
    return root


def _emit_building_event_best_effort(
    policy: Mapping[str, Any] | None,
    *,
    event_kind: str,
    building_id: str,
    building_root: Path | str,
    current_brick_ref: str = "",
    last_completed_step_ref: str = "",
    overwrite_existing: bool,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
    event_context: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    if not event_kind:
        return None
    try:
        return emit_building_event_for_policy(
            policy,
            event_kind=event_kind,
            building_id=building_id,
            building_root=building_root,
            current_brick_ref=current_brick_ref,
            last_completed_step_ref=last_completed_step_ref,
            repo_root=_report_repo_root_for_building_root(building_root),
            overwrite_existing=overwrite_existing,
            slack_env=report_env,
            slack_sender=report_slack_sender,
            dashboard_env=report_env,
            event_context=event_context,
        )
    except Exception as exc:  # noqa: BLE001 - notification must never break evidence write.
        return {
            "report_event_observation": "delivery_exception_observed",
            "event_kind": event_kind,
            "building_id": building_id,
            "delivery_status_class": "exception_observed",
            "provider_response_status_class": exc.__class__.__name__,
            "reason": str(exc),
            "source_truth": False,
            "proof_limits": [
                "support notification observation only",
                "notification exception was not allowed to break Building evidence write",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "event delivery reliability",
                "reader noticed event notification",
            ],
        }


def _report_repo_root_for_building_root(building_root: Path | str) -> Path:
    root = Path(building_root).resolve()
    try:
        root.relative_to(_REPO_ROOT)
        return _REPO_ROOT
    except ValueError:
        pass
    parts = root.parts
    for index, part in enumerate(parts):
        if part == "project" and index + 2 < len(parts) and parts[index + 2] == "buildings":
            return Path(*parts[:index]) if index else Path(".").resolve()
    if root.parent.name == "buildings":
        return root.parent.parent
    return root.parent


def _write_step_output_on_step_close(
    *,
    building_root: Path,
    building_id: str,
    step_result: BuildingRunSupportResult,
    completed_step_results: Sequence[BuildingRunSupportResult],
    proof_limits: tuple[str, ...],
    task_source_ref: str | None,
    overwrite_existing: bool,
) -> BuildingRunSupportResult:
    if not step_result.recorded_at:
        step_result = dataclasses.replace(
            step_result,
            recorded_at=_per_step_recorded_at(),
        )
    step_ref = step_result.preparation.step_rows.step_ref
    step_index = len(completed_step_results) + 1
    attempt_index = _step_attempt_index(completed_step_results, step_ref)
    write_step_output(
        building_root,
        building_id,
        _step_output_observation_from_result(
            building_id,
            step_result,
            step_index=step_index,
            task_source_ref=task_source_ref,
        ),
        attempt_index=attempt_index,
        proof_limits=proof_limits,
        recorded_at=step_result.recorded_at,
        existing_policy="replace" if overwrite_existing else "same_content_or_error",
    )
    # TrackA-A1 METER (SUPPORT FACT only): record this step's adapter token usage
    # in the raw/adapter-usage.jsonl meter journal. The count rides the adapter
    # result's adapter_usage SIDE-CHANNEL -- it never touched AgentFact.returned or
    # any Link field. Absent/empty usage (no codex --json turn.completed, or a
    # non-usage adapter) writes NO meter row at all -- the step is simply skipped;
    # the meter only records steps that actually emitted usage. MEASUREMENT ONLY;
    # no cap is applied.
    _write_adapter_usage_meter_on_step_close(
        building_root=building_root,
        building_id=building_id,
        step_result=step_result,
        step_ref=step_ref,
        attempt_index=attempt_index,
    )
    return step_result


def _write_adapter_usage_meter_on_step_close(
    *,
    building_root: Path,
    building_id: str,
    step_result: BuildingRunSupportResult,
    step_ref: str,
    attempt_index: int,
) -> None:
    adapter_result = step_result.adapter_result
    request = adapter_result.request
    # TrackA-A1 REGRESSION FIX (no null-usage noise): write a meter row ONLY when
    # usage is actually present -- a non-empty Mapping. Non-usage adapters
    # (claude-local / adapter:local, and an older codex with no
    # --json) surface adapter_usage=None, and an empty Mapping carries no counter;
    # neither should generate a usage_present=False row. The meter stays tight:
    # only adapters that actually emitted usage write to raw/adapter-usage.jsonl.
    # (claude/gemini usage plug is a SEPARATE later task #58 -- not added here.)
    adapter_usage = adapter_result.adapter_usage
    if not isinstance(adapter_usage, Mapping) or not adapter_usage:
        return
    # PURE APPEND-ONLY: the writer appends ONE new record line to the END of
    # raw/adapter-usage.jsonl and never reads, re-parses, reorders, or rewrites any
    # pre-existing line. There is no read+separate+rewrite path to preserve raw
    # evidence -- the bytes already on disk are never touched in the first place.
    # The token meter records the MODEL dial only (the brain whose tokens are
    # metered); ``request.selected_model_ref`` is now the GENERIC casting accessor
    # (__getattr__ over the casting bag), so this reads the model dial through the
    # same single-source path as every other reader. Effort/adapter are not token
    # data, so the append-only meter record shape stays byte-stable.
    write_adapter_usage_meter(
        building_root,
        building_id,
        step_ref=step_ref,
        adapter_ref=request.adapter_ref,
        selected_model_ref=request.selected_model_ref,
        attempt_index=attempt_index,
        adapter_usage=adapter_usage,
    )


def _step_output_observation_from_result(
    building_id: str,
    result: BuildingRunSupportResult,
    *,
    step_index: int,
    task_source_ref: str | None,
) -> StepOutputObservation:
    step_ref = result.preparation.step_rows.step_ref
    return StepOutputObservation(
        building_id=building_id,
        step_ref=step_ref,
        brick_instance_ref=result.preparation.brick_instance_ref,
        agent_object_ref=result.preparation.agent_object.object_ref,
        returned=result.adapter_result.returned_value,
        received_work_ref=_step_fact_ref("brick-work", step_index, step_ref),
        returned_fact_ref=_step_fact_ref("agent-fact", step_index, step_ref),
        raw_ref=_raw_ref("agent", step_index),
        task_source_ref=task_source_ref or "",
        not_proven=result.not_proven,
        recorded_at=result.recorded_at,
        gate_sequence_decision_record=gate_sequence_decision_to_record(
            result.gate_sequence_decision
        ),
    )


def _step_attempt_index(
    completed_step_results: Sequence[BuildingRunSupportResult],
    step_ref: str,
) -> int:
    return 1 + sum(
        1
        for result in completed_step_results
        if result.preparation.step_rows.step_ref == step_ref
    )


def _adapter_result_or_interrupt(
    prepared: AgentRunPreparationRecord,
    adapter_request: AgentAdapterRequest,
    *,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
) -> AgentAdapterResult:
    try:
        write_observation_before = _write_adapter_observation_before(
            adapter_request,
            adapter_cwd=adapter_cwd,
        )
        adapter_result = connect_agent_brain(
            adapter_request,
            local_callables=local_callables,
            command_runner=command_runner,
            cwd=adapter_cwd,
            timeout_seconds=adapter_timeout_seconds,
        )
        observed_write_result = _adapter_result_with_write_observation(
            adapter_result,
            write_observation_before,
            adapter_cwd=adapter_cwd,
        )
        return _adapter_result_with_proof_observation(
            observed_write_result,
            _proof_obligations_from_brick_row(prepared.step_rows.brick_row),
            adapter_cwd=adapter_cwd,
        )
    except AgentAdapterParked as parked:
        raise _AdapterRunParked(
            prepared=prepared,
            adapter_request=adapter_request,
            parked=parked,
        ) from parked
    except Exception as exc:
        raise _AdapterRunInterrupted(
            prepared=prepared,
            adapter_request=adapter_request,
            adapter_error=_adapter_error_mapping(exc),
        ) from exc


def _adapter_error_mapping(exc: Exception) -> Mapping[str, Any]:
    mapping: dict[str, Any] = {
        "error_kind": _adapter_error_kind(exc),
        "exception_type": type(exc).__name__,
        "message_excerpt": _safe_exception_excerpt(exc),
        "proof_limits": [
            "adapter exception frontier support evidence only",
            "not Agent returned payload",
            "not AgentFact",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "provider or local callable behavior after the adapter exception",
            "semantic correctness of the interrupted work",
            "caller/COO disposition after frontier observation",
        ],
    }
    mapping.update(_adapter_error_timeout_diagnostic_excerpts(exc))
    return mapping


def _adapter_error_timeout_diagnostic_excerpts(exc: Exception) -> Mapping[str, Any]:
    if not isinstance(exc, subprocess.TimeoutExpired):
        return {}
    partial = _timeout_expired_partial_output(exc)
    diagnostics: dict[str, Any] = {
        "timeout_reap_reason": _timeout_expired_reap_reason(exc),
    }
    stdout = partial.get("stdout", "")
    stderr = partial.get("stderr", "")
    if stdout:
        diagnostics["timeout_stdout_excerpt"] = _safe_diagnostic_excerpt(stdout, limit=420)
    if stderr:
        diagnostics["timeout_stderr_excerpt"] = _safe_diagnostic_excerpt(stderr, limit=420)
    return diagnostics


def _adapter_error_kind(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, FileNotFoundError):
        return "local_cli_missing"
    if isinstance(exc, subprocess.TimeoutExpired):
        # CONNECT-STALL LABEL SPLIT (TrackB 0619): the codex stall watchdog tags a
        # DEAD-connection reap with reap_reason == "stall" on the TimeoutExpired it
        # raises (agent_adapter._communicate_with_optional_codex_stall_watchdog).
        # Surface that as a DISTINCT kind so a connect-stall (dead worker) is no
        # longer hidden inside a generic timeout. This is a LABEL split only: both
        # kinds route to the SAME adapter-error HOLD/frontier outcome downstream
        # (_adapter_error_mapping -> _AdapterRunInterrupted -> adapter_error_frontier).
        # NO auto-retry / queue / scheduler: a connect-stall fast-fails to HOLD and
        # STOPS for a human (BRICK no-scheduler invariant).
        if _timeout_expired_reap_reason(exc) == "stall":
            return "local_cli_connect_stall"
        return "local_cli_timeout"
    if "adapter_error_classification=content_policy" in message:
        return "content_policy"
    if "non-zero" in message or "returned non-zero" in message:
        return "local_cli_nonzero"
    if "returned payload" in message or "forbidden returned" in message:
        return "adapter_return_shape_rejected"
    return "adapter_exception"


def _per_step_recorded_at() -> str:
    """Return a per-step RFC 3339 UTC timestamp at microsecond resolution.

    δ-b PER-STEP recorded_at: real datetime is available in run.py, so capture
    the wall-clock time when a step's agent dispatch completes. Microsecond
    resolution keeps back-to-back in-process steps distinct; the Z suffix matches
    the format produced by support.recording.capture.graph_ready_timestamp.
    """

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_exception_excerpt(exc: Exception) -> str:
    return _safe_diagnostic_excerpt(str(exc), limit=240)


def _safe_diagnostic_excerpt(value: str, *, limit: int) -> str:
    text = " ".join(value.split())
    secret_patterns = (
        (r"(?i)authorization\s*:\s*bearer\s+\S+", "authorization credential redacted"),
        (r"(?i)\bbearer\s+\S+", "credential redacted"),
        (r"(?i)\bapi[_-]?key\s*[:=]\s*\S+", "credential redacted"),
        (r"(?i)sk-[A-Za-z0-9._~+/=-]+", "credential redacted"),
        (r"(?i)xoxb-[A-Za-z0-9._~+/=-]+", "credential redacted"),
        (r"(?i)ghp_[A-Za-z0-9_]+", "credential redacted"),
        (r"(?i)gho_[A-Za-z0-9_]+", "credential redacted"),
        (r"(?i)github_pat_[A-Za-z0-9_]+", "credential redacted"),
        (r"(?i)AIza[A-Za-z0-9_-]+", "credential redacted"),
        # Provider/runtime session + resume artifacts. Per the AGENTS principle a
        # provider-specific session id must never reach a durable support record,
        # and an adapter exception excerpt IS durable support evidence. The
        # prefixed forms run before the bare-UUID sweep so they keep a specific
        # label; the UUID sweep is safe here because spine ids are slug-style and
        # content hashes are 64-hex sha256 (no UUID dashes), so it cannot eat
        # legitimate Brick/Agent/Link identifiers.
        (r"(?i)\bprovider-session-[A-Za-z0-9._~+/=-]+", "session id redacted"),
        (r"(?i)\bsess[_-][A-Za-z0-9._~+/=-]+", "session id redacted"),
        (r"(?i)\bresume[_-]token[_-][A-Za-z0-9._~+/=-]+", "resume token redacted"),
        (r"(?i)\bchatcmpl-[A-Za-z0-9._~+/=-]+", "session id redacted"),
        (r"\bya29\.[A-Za-z0-9._-]+", "credential redacted"),
        (r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}", "credential redacted"),
        (r"(?i)\bapi[_-]?key\b", "credential label redacted"),
        (r"(?i)\bbearer\b", "credential label redacted"),
        (
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "session id redacted",
        ),
        # Bare ULID (Crockford base32) session ids. Last so the prefixed/UUID forms
        # win their specific labels first; safe in error text where over-scrubbing
        # only costs a little debug detail and never breaks behavior.
        (r"\b[0-9A-HJKMNP-TV-Z]{26}\b", "session id redacted"),
    )
    for pattern, replacement in secret_patterns:
        text = re.sub(pattern, replacement, text)
    return text[:limit]


def build_minimal_crossing(
    work_statement: str,
    returned: object,
    *,
    link_fact: MovementFact,
    transition_fact: TransitionFact,
    transfer_gate_fact: GateFact | None = None,
    carry_gate_fact: GateFact | None = None,
    movement_gate_fact: GateFact | None = None,
    transfer_fact: "TransferFact | None" = None,
    carry_fact: "CarryFact | None" = None,
    comparison_rule: str = "",
    required_return_shape: str = "",
    proof_limits: Iterable[str] | str | None = None,
) -> MinimalCrossingRecord:
    """Build one crossing from explicit caller-supplied Link facts."""

    brick_work = BrickWork.from_parts(
        work_statement=work_statement,
        comparison_rule=comparison_rule,
        required_return_shape=required_return_shape,
    )
    _validate_no_payload_forbidden("returned", returned, _RETURN_FORBIDDEN_KEYS)
    agent_fact = make_agent_fact(received_work=brick_work, returned=returned)
    brick_comparison = BrickComparisonFact.from_parts(
        work_reference=brick_work.work_statement,
        comparison_evidence=(
            "public AgentFact returned value is available for Brick comparison",
        ),
        observed_match_kind="unknown",
        comparison_rule=brick_work.comparison_rule,
        required_return_shape_evidence=brick_work.required_return_shape,
        forbidden_shortcut_evidence=(
            "support/run did not classify the returned value",
            "support/run used caller-supplied Link public facts",
        ),
    )
    return record_from_public_facts(
        brick_work=brick_work,
        agent_fact=agent_fact,
        brick_comparison=brick_comparison,
        link_fact=link_fact,
        transition_fact=transition_fact,
        transfer_gate_fact=transfer_gate_fact,
        carry_gate_fact=carry_gate_fact,
        movement_gate_fact=movement_gate_fact,
        transfer_fact=transfer_fact,
        carry_fact=carry_fact,
        proof_limits=proof_limits,
    )


def record_from_public_facts(
    *,
    brick_work: BrickWork,
    agent_fact: AgentFact,
    brick_comparison: BrickComparisonFact,
    link_fact: MovementFact,
    transition_fact: TransitionFact,
    transfer_gate_fact: GateFact | None = None,
    carry_gate_fact: GateFact | None = None,
    movement_gate_fact: GateFact | None = None,
    transfer_fact: "TransferFact | None" = None,
    carry_fact: "CarryFact | None" = None,
    proof_limits: Iterable[str] | str | None = None,
) -> MinimalCrossingRecord:
    """Compose caller-supplied public facts into a narrow support record."""

    return MinimalCrossingRecord(
        brick_work=_require_fact("brick_work", brick_work, BrickWork),
        agent_fact=_require_fact("agent_fact", agent_fact, AgentFact),
        brick_comparison=_require_fact(
            "brick_comparison",
            brick_comparison,
            BrickComparisonFact,
        ),
        link_fact=_require_fact("link_fact", link_fact, MovementFact),
        transition_fact=_require_fact("transition_fact", transition_fact, TransitionFact),
        transfer_gate_fact=_optional_fact("transfer_gate_fact", transfer_gate_fact, GateFact),
        carry_gate_fact=_optional_fact("carry_gate_fact", carry_gate_fact, GateFact),
        movement_gate_fact=_optional_fact(
            "movement_gate_fact",
            movement_gate_fact,
            GateFact,
        ),
        transfer_fact=_optional_fact(
            "transfer_fact",
            transfer_fact,
            "brick_protocol.link.transfer",
            "TransferFact",
        ),
        carry_fact=_optional_fact(
            "carry_fact",
            carry_fact,
            "brick_protocol.link.carry",
            "CarryFact",
        ),
        proof_limits=_proof_limits_tuple(proof_limits),
    )


def prepare_agent_run_from_step_rows(
    fixture: Mapping[str, Any],
    *,
    building_id: str | None = None,
    proof_limits: Iterable[str] | str | None = None,
) -> AgentRunPreparationRecord:
    """Resolve one declared step row packet and Agent Object into support prep evidence."""

    _require_mapping_value("fixture", fixture)
    _validate_no_payload_forbidden("fixture", fixture, _FORBIDDEN_PAYLOAD_KEYS)
    step_rows = _three_axis_step_rows_from_mapping(
        _require_mapping_value("step_rows", fixture.get("step_rows"))
    )
    agent_ref = _required_text(
        "step_rows.agent_row.agent_object_ref",
        step_rows.agent_row.get("agent_object_ref"),
    )
    if "agent_objects" in fixture:
        agent_objects = _require_mapping_value("agent_objects", fixture.get("agent_objects"))
        agent_object = _agent_object_from_mapping(
            _require_mapping_value(f"agent_objects.{agent_ref}", agent_objects.get(agent_ref))
        )
    else:
        agent_object = load_agent_object_resource(agent_ref)
    if agent_object.object_ref != agent_ref:
        raise ValueError("Agent row ref must match Agent Object object_ref")

    brick_work = _brick_work_from_row(step_rows.brick_row)
    checked_building_id = _path_segment(
        "building_id",
        building_id or _optional_text_from_mapping(fixture, "building_id") or step_rows.step_ref,
    )
    agent_performer_fact = make_agent_performer_fact(
        name=agent_object.name,
        lane=agent_object.lane,
        callable_performers=agent_object.callable_performer_refs,
    )
    # MAIL-REPAIR (Smith ruling B2, 0611): the receipt records WHICH handoff
    # ADDRESSES were delivered with the work ("received" as fact) -- flattened
    # from the SAME link_handoff_refs packet the adapter request delivers
    # (declared and runtime lanes alike). Addresses only; data, no judgment.
    receipt_fact = make_receipt_fact(
        received_work=brick_work,
        received_at_reference=_optional_text_from_mapping(fixture, "received_at_reference"),
        evidence_reference=_optional_text_from_mapping(
            fixture,
            "receipt_evidence_reference",
        ),
        received_handoff_refs=_handoff_address_refs(fixture.get("link_handoff_refs")),
    )
    raw_refs = _merge_texts(
        step_rows.brick_row.get("raw_refs"),
        step_rows.link_row.get("raw_refs"),
        fixture.get("raw_refs"),
    )
    task_source_ref = _optional_text_from_mapping(fixture, "task_source_ref")
    if task_source_ref:
        raw_refs = _merge_texts(raw_refs, (task_source_ref,))
    brick_instance_ref = _required_text(
        "step_rows.brick_row.brick_instance_ref",
        step_rows.brick_row.get("brick_instance_ref", "brick-001"),
    )
    next_brick_instance_ref = _required_text(
        "step_rows.link_row.next_brick_instance_ref",
        step_rows.link_row.get("next_brick_instance_ref", "brick-002"),
    )
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else fixture.get("proof_limits")
    )
    call_preparation_refs = {
        "agent_object_ref": agent_object.object_ref,
        "agent_performer_fact_ref": f"agent-performer:{agent_object.object_ref}",
        "receipt_fact_ref": f"receipt:{checked_building_id}:{agent_object.object_ref}",
        "prompt_refs": agent_object.prompt_refs,
        "skill_refs": agent_object.skill_refs,
        "hook_refs": agent_object.hook_refs,
        "tool_policy_refs": agent_object.tool_policy_refs,
        "discipline_refs": agent_object.discipline_refs,
        "adapter_refs": agent_object.adapter_refs,
        "call_preparation_only": True,
    }
    if task_source_ref:
        call_preparation_refs["task_source_ref"] = task_source_ref
    return AgentRunPreparationRecord(
        building_id=checked_building_id,
        step_rows=step_rows,
        brick_work=brick_work,
        brick_instance_ref=brick_instance_ref,
        next_brick_instance_ref=next_brick_instance_ref,
        agent_object=agent_object,
        agent_performer_fact=agent_performer_fact,
        receipt_fact=receipt_fact,
        call_preparation_refs=call_preparation_refs,
        raw_refs=raw_refs,
        proof_limits=checked_proof_limits,
        not_proven=_agent_run_not_proven(),
    )


def complete_agent_run_from_prepared(
    prepared: AgentRunPreparationRecord,
    *,
    returned_value: Any,
    link_fact: MovementFact,
    transition_fact: TransitionFact,
    adapter_result: AgentAdapterResult | None = None,
    transfer_gate_fact: GateFact | None = None,
    carry_gate_fact: GateFact | None = None,
    movement_gate_fact: GateFact | None = None,
    transfer_fact: "TransferFact | None" = None,
    carry_fact: "CarryFact | None" = None,
    comparison_observation: BrickComparisonFact | Mapping[str, Any] | None = None,
    proof_limits: Iterable[str] | str | None = None,
) -> AgentRunCompletionRecord:
    """Record adapter return evidence and caller-supplied Link facts."""

    if not isinstance(prepared, AgentRunPreparationRecord):
        raise TypeError("prepared must be AgentRunPreparationRecord")
    _validate_no_payload_forbidden("returned_value", returned_value, _RETURN_FORBIDDEN_KEYS)
    agent_fact = make_agent_fact(received_work=prepared.brick_work, returned=returned_value)
    brick_comparison = _comparison_fact_from_observation(
        prepared,
        comparison_observation,
        returned_value=returned_value,
    )
    if movement_gate_fact is None:
        movement_gate_fact = _declared_movement_gate_fact(
            prepared,
            brick_comparison,
        )
    crossing_record = record_from_public_facts(
        brick_work=prepared.brick_work,
        agent_fact=agent_fact,
        brick_comparison=brick_comparison,
        link_fact=link_fact,
        transition_fact=transition_fact,
        transfer_gate_fact=transfer_gate_fact,
        carry_gate_fact=carry_gate_fact,
        movement_gate_fact=movement_gate_fact,
        transfer_fact=transfer_fact,
        carry_fact=carry_fact,
        proof_limits=proof_limits or prepared.proof_limits,
    )
    checked_proof_limits = crossing_record.proof_limits
    not_proven = _agent_run_not_proven()
    building_map_packet = agent_run_building_map_packet(
        prepared,
        crossing_record,
        proof_limits=checked_proof_limits,
        not_proven=not_proven,
    )
    lifecycle_packet_mapping = agent_run_lifecycle_mapping(
        prepared,
        crossing_record,
        building_map_packet=building_map_packet,
        proof_limits=checked_proof_limits,
        not_proven=not_proven,
    )
    return AgentRunCompletionRecord(
        preparation=prepared,
        adapter_result=adapter_result,
        agent_fact=agent_fact,
        brick_comparison=brick_comparison,
        crossing_record=crossing_record,
        link_handoff_packet=_agent_run_handoff_packet(
            prepared,
            crossing_record,
            not_proven,
            checked_proof_limits,
        ),
        building_map_packet=building_map_packet,
        lifecycle_packet_mapping=lifecycle_packet_mapping,
        proof_limits=checked_proof_limits,
        not_proven=not_proven,
    )


def _declared_movement_gate_fact(
    prepared: AgentRunPreparationRecord,
    brick_comparison: BrickComparisonFact,
) -> GateFact | None:
    gate_refs = _text_tuple(
        "declared_gate_refs",
        prepared.step_rows.link_row.get(_DECLARED_GATE_REFS_KEY, ()),
    )
    if not gate_refs:
        return None
    checked = f"brick-comparison:{prepared.building_id}:{prepared.step_rows.step_ref}"
    return evaluate_declared_movement_gate(
        gate_refs=gate_refs,
        required_return_fields=_brick_comparison_required_return_fields(brick_comparison),
        missing_return_fields=_brick_comparison_missing_return_fields(brick_comparison),
        observed_match_kind=brick_comparison.observed_match_kind,
        human_review_present=_link_row_has_non_empty_list(
            prepared.step_rows.link_row,
            ("route_decision_basis", "human_review_refs"),
        ),
        override_present=_link_row_has_non_empty_list(
            prepared.step_rows.link_row,
            ("route_decision_basis", "override_refs"),
        ),
        base_required_return_fields=_base_required_return_fields_for_gate(
            prepared,
            brick_comparison,
        ),
        checked_public_fact=checked,
        evidence_reference=checked,
    )


def _brick_comparison_required_return_fields(
    brick_comparison: BrickComparisonFact,
) -> tuple[str, ...]:
    return brick_comparison.required_return_fields()


def _brick_comparison_missing_return_fields(
    brick_comparison: BrickComparisonFact,
) -> tuple[str, ...]:
    return brick_comparison.missing_return_fields()


def _base_required_return_fields_for_gate(
    prepared: AgentRunPreparationRecord,
    brick_comparison: BrickComparisonFact,
) -> tuple[str, ...]:
    return _artifact_grounding_required_return_fields(
        prepared.brick_work.required_return_shape,
        brick_comparison.required_return_fields(),
    )


def _required_return_shape_fields(value: Any) -> tuple[str, ...]:
    return parse_required_return_shape(value)


def _link_row_has_non_empty_list(
    link_row: Mapping[str, Any],
    path: tuple[str, str],
) -> bool:
    outer = link_row.get(path[0])
    if not isinstance(outer, Mapping):
        return False
    value = outer.get(path[1])
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def load_agent_object_resource(
    agent_object_ref: str,
    *,
    object_root: Path | str | None = None,
) -> AgentObjectContractData:
    """Load a provider-neutral Agent Object resource by symbolic ref."""

    object_ref = _required_text("agent_object_ref", agent_object_ref)
    if not object_ref.startswith("agent-object:"):
        raise ValueError("Agent Object resource ref must start with agent-object:")
    slug = _resource_slug("agent_object_ref", object_ref.removeprefix("agent-object:"))
    root = Path(object_root) if object_root is not None else _DEFAULT_AGENT_OBJECT_ROOT
    value = _json_resource_mapping(root / f"{slug}.yaml")
    agent_object = _agent_object_from_mapping(value)
    if agent_object.object_ref != object_ref:
        raise ValueError("Agent Object resource object_ref does not match requested ref")
    _validate_agent_object_with_resource_resolver(object_ref, root)
    return agent_object


def _validate_agent_object_with_resource_resolver(
    agent_object_ref: str,
    object_root: Path,
) -> None:
    """Reuse the Agent resource resolver before the runner prepares a step.

    The runner remains a declared-road walker. This check only makes sure the
    Agent Object row is accepted by the Agent resource resolver before adapter
    preparation.
    """

    root = object_root.resolve()
    repo_root = root.parents[1] if root.name == "objects" and root.parent.name == "agent" else _REPO_ROOT
    validation = validate_agent_refs(agent_object_ref, repo_root=repo_root)
    if not validation.get("ok"):
        violations = validation.get("violations")
        if isinstance(violations, list) and violations:
            reason = "; ".join(str(item) for item in violations)
        else:
            reason = "Agent Object resource rejected by Agent resource resolver"
        raise ValueError(reason)


def _fixture_mapping(fixture: Mapping[str, Any] | str | Path) -> Mapping[str, Any]:
    if isinstance(fixture, Mapping):
        return fixture
    path = Path(fixture)
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("YAML Building Plan files require PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, Mapping):
        raise TypeError("fixture must be a JSON object")
    return value


def _three_axis_step_rows_from_mapping(value: Mapping[str, Any]) -> ThreeAxisStepRows:
    _validate_no_payload_forbidden("step_rows", value, _FORBIDDEN_PAYLOAD_KEYS)
    step_ref = _required_text("step_rows.step_ref", value.get("step_ref"))
    rows_value = value.get("rows")
    if not isinstance(rows_value, list):
        raise TypeError("step_rows.rows must be a JSON array")
    if len(rows_value) != 3:
        raise ValueError("Building Plan step rows must contain exactly three rows")
    rows = [
        _require_mapping_value(f"step_rows.rows[{index}]", item)
        for index, item in enumerate(rows_value)
    ]
    by_axis: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        axis = _required_text("step row axis", row.get("axis"))
        if axis in by_axis:
            raise ValueError(f"Building Plan step has duplicate {axis} row")
        by_axis[axis] = row
    if set(by_axis) != {"Brick", "Agent", "Link"}:
        raise ValueError("Building Plan step rows must be exactly Brick, Agent, Link")
    _require_only_keys("Brick row", by_axis["Brick"], _BRICK_ROW_ALLOWED_KEYS)
    _require_only_keys("Agent row", by_axis["Agent"], _AGENT_ROW_ALLOWED_KEYS)
    _require_only_keys("Link row", by_axis["Link"], _LINK_ROW_ALLOWED_KEYS)
    movement, target = _movement_and_target_from_link_row(by_axis["Link"])
    _validate_route_replay_plan_for_link_row(
        by_axis["Link"],
        movement=movement,
        target=target,
    )
    _validate_declared_gate_refs_for_link_row(by_axis["Link"])
    _validate_gate_sequence_policy_for_link_row(
        by_axis["Link"],
        source_brick_ref=_optional_text_from_mapping(
            by_axis["Brick"],
            "brick_instance_ref",
        )
        or "",
        target_brick_ref=target,
    )
    _validate_route_decision_basis_for_link_row(by_axis["Link"])
    _validate_transition_authoring_for_link_row(by_axis["Link"])
    _validate_transition_lifecycle_for_link_row(by_axis["Link"])
    _validate_building_lifecycle_for_link_row(by_axis["Link"])
    return ThreeAxisStepRows(
        step_ref=step_ref,
        brick_row=by_axis["Brick"],
        agent_row=by_axis["Agent"],
        link_row=by_axis["Link"],
        proof_limits=_proof_limits_tuple(value.get("proof_limits")),
    )


def _agent_object_from_mapping(value: Mapping[str, Any]) -> AgentObjectContractData:
    _require_only_keys("Agent Object", value, _AGENT_OBJECT_ALLOWED_KEYS)
    _validate_no_payload_forbidden("Agent Object", value, _FORBIDDEN_PAYLOAD_KEYS)
    kwargs: dict[str, Any] = {
        "object_ref": _required_text("Agent Object object_ref", value.get("object_ref")),
        "name": _required_text("Agent Object name", value.get("name")),
        "lane": _required_text("Agent Object lane", value.get("lane")),
        "callable_performer_refs": _text_tuple(
            "Agent Object callable_performer_refs",
            value.get("callable_performer_refs", ()),
        ),
    }
    # E2/S7 (mirror M1): the per-dial casting scalars collapsed to ONE opaque
    # ``casting`` bag keyed by the CASTING_FIELDS names. Built ONCE here by looping
    # the Agent-axis field-set; a declared dial is cleaned text (byte-identical to
    # the prior per-scalar _required_text), an undeclared dial is simply absent from
    # the bag (the dataclass never names a dial). A NEW casting field flows through
    # with NO edit here.
    casting: dict[str, str] = {}
    for descriptor in CASTING_FIELDS:
        if value.get(descriptor.field_name) is not None:
            casting[descriptor.field_name] = _required_text(
                f"Agent Object {descriptor.field_name}",
                value.get(descriptor.field_name),
            )
    kwargs["casting"] = casting
    for key in _AGENT_OBJECT_REF_FIELDS:
        kwargs[key] = _text_tuple(f"Agent Object {key}", value.get(key, ()))
    return AgentObjectContractData(**kwargs)


def _handoff_address_refs(value: Any) -> tuple[str, ...]:
    """Flatten a delivered link_handoff_refs packet to its ADDRESS strings.

    MAIL-REPAIR (Smith ruling B2, 0611): the AgentReceipt records which handoff
    addresses were delivered with the work. Addresses are the text items of
    ``*_refs`` list fields anywhere in the packet (declared incoming /
    route_replay handoffs AND runtime_handoffs alike), plus the singular
    ``from_step_output_ref`` address stamped on incoming step-output handoffs.
    Bodies never ride, so nothing else is collected. Order-preserving,
    de-duplicated; an absent or empty packet -> (). Pure data read; no Movement
    choice, no judgment.
    """

    collected: list[str] = []
    seen: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if key == "from_step_output_ref":
                    text = _optional_text_value(child)
                    if text and text not in seen:
                        seen.add(text)
                        collected.append(text)
                elif isinstance(key, str) and key.endswith("_refs") and isinstance(child, list):
                    for item in child:
                        text = _optional_text_value(item)
                        if text and text not in seen:
                            seen.add(text)
                            collected.append(text)
                else:
                    _walk(child)
        elif isinstance(node, list):
            for child in node:
                _walk(child)

    if isinstance(value, Mapping):
        _walk(value)
    return tuple(collected)


def _brick_work_from_row(row: Mapping[str, Any]) -> BrickWork:
    return BrickWork.from_parts(
        work_statement=_required_text("Brick row work_statement", row.get("work_statement")),
        comparison_rule=_optional_text_value(row.get("comparison_rule")) or "",
        required_return_shape=_optional_text_value(row.get("required_return_shape")) or "",
        source_facts=_text_tuple("Brick row source_facts", row.get("source_facts", ())),
    )


def _adapter_request_from_prepared(
    packet: Mapping[str, Any],
    prepared: AgentRunPreparationRecord,
    *,
    project_ref: str | None = None,
) -> AgentAdapterRequest:
    if "selected_adapter_ref" not in packet:
        raise ValueError("selected_adapter_ref must be declared by caller or Building Plan step")
    selected_adapter_ref = _required_text(
        "selected_adapter_ref",
        packet.get("selected_adapter_ref"),
    )
    if selected_adapter_ref not in prepared.agent_object.adapter_refs:
        raise ValueError("selected adapter must be referenced by Agent Object")
    callable_ref = ""
    if selected_adapter_ref == "adapter:local":
        callable_ref = _first_text(prepared.agent_object.callable_performer_refs)
    # CHARTER-INJECT (0618): the vessel project_ref reaches here two ways — the
    # live plan walker stamps it onto the step packet (from the building_root
    # via project_ref_for_building_root), and the single-step surface passes it
    # explicitly (derived from output_root + building_id). The explicit arg wins;
    # otherwise read it off the packet. render_agent_instruction_packet injects
    # that project's README charter into EVERY role's runtime packet so the
    # work/qa/closure Agent knows WHAT it builds and WHY. Absent/undeclared
    # (ref-less or default-root builds) -> no charter, no crash.
    resolved_project_ref = (
        project_ref or _optional_text_from_mapping(packet, "project_ref") or None
    )
    agent_instruction_packet = render_agent_instruction_packet(
        prepared.agent_object.object_ref,
        repo_root=_REPO_ROOT,
        project_ref=resolved_project_ref,
    )
    request_kwargs = {
        "building_id": prepared.building_id,
        "agent_object_ref": prepared.agent_object.object_ref,
        "adapter_ref": selected_adapter_ref,
        "callable_ref": callable_ref,
        "brick_instance_ref": prepared.brick_instance_ref,
        "next_brick_instance_ref": prepared.next_brick_instance_ref,
        # E2/S6★ (was S7/M2): the casting dials ride in the opaque casting bag,
        # built ONCE here by LOOPING the single-source NODE_CASTING_FIELDS from the
        # SAME packet values the named scalars read; the request's __post_init__
        # normalizes them inside the bag. A NEW casting dial (effort) flows through
        # with NO edit here — it is added to the field-set, not as a request field.
        "casting": {
            key: _optional_text_from_mapping(packet, key) or ""
            for key in NODE_CASTING_FIELDS
        },
        "prompt_refs": prepared.agent_object.prompt_refs,
        "skill_refs": prepared.agent_object.skill_refs,
        "hook_refs": prepared.agent_object.hook_refs,
        "tool_policy_refs": prepared.agent_object.tool_policy_refs,
        "discipline_refs": prepared.agent_object.discipline_refs,
        "input_packet_ref": _optional_text_from_mapping(packet, "adapter_input_packet_ref")
        or f"support-packet:{prepared.building_id}:{prepared.agent_object.object_ref}:input",
        "output_packet_ref": _optional_text_from_mapping(packet, "adapter_output_packet_ref")
        or f"support-packet:{prepared.building_id}:{prepared.agent_object.object_ref}:output",
        "work_statement": prepared.brick_work.work_statement,
        "comparison_rule": prepared.brick_work.comparison_rule,
        "required_return_shape": _adapter_required_return_shape(prepared),
        # branch (step-output drain): packet-aware source-fact body carry +
        # missing-step-output guard, NOT main's plain 1-arg _source_fact_bodies.
        "source_fact_bodies": _adapter_source_fact_bodies(
            packet,
            prepared.brick_work.source_facts,
            building_id=prepared.building_id,
        ),
        "link_handoff_refs": (
            _mapping("link_handoff_refs", packet["link_handoff_refs"])
            if "link_handoff_refs" in packet
            else {}
        ),
        "write_scope": _write_scope_from_brick_row(prepared.step_rows.brick_row),
        # ⑤ STATIC INSTRUCTION BODY: read the kind's brick.md ## body off the
        # brick_row (carried at compose time by plan_rendering/composition) EXACTLY
        # parallel to write_scope above, and thread it to the prompt. Absent (legacy
        # rows, no-template branch) -> "" -> the prompt key is present-but-empty
        # (the adapter injects the labeled section only when non-empty).
        "brick_instruction_body": _optional_text_value(
            prepared.step_rows.brick_row.get("brick_instruction_body")
        )
        or "",
        # ④ RE-INSTRUCTION: read the corrected how-to off the step PACKET (a
        # top-level key the kernel stamps onto the retried target's step packet
        # from the human/COO disposition row), parallel to session_continuity_mode
        # below. Absent on every normal run and every non-target step -> "" -> the
        # adapter injects the labeled correction section only when non-empty.
        "re_instruction": _optional_text_from_mapping(packet, "re_instruction") or "",
        "building_session_ref": _optional_text_from_mapping(packet, "building_session_ref") or "",
        "session_scope_ref": _optional_text_from_mapping(packet, "session_scope_ref") or "",
        "session_continuity_mode": _optional_text_from_mapping(
            packet,
            "session_continuity_mode",
        )
        or "none",
        "agent_instruction_packet": agent_instruction_packet,
        "proof_limits": prepared.proof_limits,
        "not_proven": prepared.not_proven,
    }
    return _agent_adapter_request_from_kwargs(request_kwargs)


def _adapter_required_return_shape(prepared: AgentRunPreparationRecord) -> Any:
    """The return shape the ADAPTER asks the Agent for: Brick shape + gate fields.

    GATE-SEAM CONSISTENCY (0610): the comparison side already requires the
    union of the Brick-declared return shape and the declared Link gates'
    evidence fields (plan_validation._required_agent_return_fields_for_brick_handoff
    -> link/gate.gate_required_return_fields). The adapter request previously
    asked for the Brick shape ONLY, so a declared link-gate:strict row could
    never be satisfied through a local CLI adapter (the prompt never asked for
    blocked_or_missing_evidence / remaining_delta, and adapter extraction drops
    unrequested keys) -- the gate recorded permanently-missing facts. This
    helper threads the SAME union into the request.

    NEUTRALITY SCOPE (qualified, codex review 0610): byte-neutrality holds
    ONLY when the declared gates add no field beyond the Brick shape -- every
    FRESHLY MATERIALIZED default-only / coo / human row today, because the
    live kind shapes already carry observed_evidence + not_proven; then the
    original declared value passes through VERBATIM and prompts do not change.
    It is NOT byte-neutral for STORED LEGACY plans whose Brick shape lacks a
    default-gate-required field (repro:
    brick/building_plans/fixture-link-route-replay-0.yaml
    has rows without observed_evidence): such a row's adapter request now asks
    the gate-implied union. That delta is DELIBERATE -- it corrects a historic
    under-ask the gate side would have recorded as permanently-missing facts
    anyway, and legacy stored plans are already strict-blocked at run
    admission for re-runs (require_write_need_marker), so no green walk flips.
    FIRE: adapter_gate_shape_union_case pins the NEW behavior (a row whose
    Brick shape lacks a default-gate-required field must be ASKED for the
    union; the old Brick-shape-only under-ask REDs that case).
    """

    base_fields = parse_required_return_shape(prepared.brick_work.required_return_shape)
    gate_refs = _text_tuple(
        "declared_gate_refs",
        prepared.step_rows.link_row.get(_DECLARED_GATE_REFS_KEY, ()),
    )
    union_fields = gate_required_return_fields(gate_refs, base_fields)
    if tuple(union_fields) == tuple(base_fields):
        return prepared.brick_work.required_return_shape
    return ", ".join(union_fields)


def _agent_adapter_request_from_kwargs(kwargs: Mapping[str, Any]) -> AgentAdapterRequest:
    """Build AgentAdapterRequest while adapter packet fields can land independently."""

    admitted_fields = {field.name for field in dataclasses.fields(AgentAdapterRequest)}
    return AgentAdapterRequest(
        **{key: value for key, value in kwargs.items() if key in admitted_fields}
    )


def _adapter_source_fact_bodies(
    packet: Mapping[str, Any],
    source_facts: Iterable[str],
    *,
    building_id: str = "",
) -> Mapping[str, str]:
    source_fact_refs = tuple(source_facts)
    supplied_bodies = _supplied_source_fact_bodies(packet)
    vessel_bodies = _vessel_step_output_source_fact_bodies(
        packet,
        source_fact_refs,
        building_id=building_id,
        supplied_bodies=supplied_bodies,
    )
    missing_step_output_refs = [
        source_fact
        for source_fact in source_fact_refs
        if _is_step_output_source_fact_ref(source_fact)
        and source_fact not in supplied_bodies
        and source_fact not in vessel_bodies
    ]
    if missing_step_output_refs:
        raise ValueError(
            "missing step-output source_fact body/evidence: "
            + ", ".join(missing_step_output_refs)
        )
    bodies = dict(
        _source_fact_bodies(
            source_fact
            for source_fact in source_fact_refs
            if not _is_step_output_source_fact_ref(source_fact)
            and source_fact != INLINE_TASK_SOURCE_REF
        )
    )
    # TASK-BY-TEXT (0611, codex FIX-A): the inline task sentinel resolves to
    # the statement body carried ON the packet (threaded from the plan by
    # _step_fixture_from_plan_step), never to a file -- parity with the file
    # flow where the declared task file body lands in the prompt. A sentinel
    # source fact WITHOUT a carried body is skipped exactly like an unreadable
    # file ref (run admission already rejects a sentinel task_source_ref
    # without a statement; this branch only feeds the prompt carry).
    if INLINE_TASK_SOURCE_REF in source_fact_refs:
        inline_statement = packet.get("task_statement")
        if isinstance(inline_statement, str) and inline_statement.strip():
            bodies[INLINE_TASK_SOURCE_REF] = safe_source_fact_body(inline_statement)
    for source_fact_ref, body in supplied_bodies.items():
        if not _is_step_output_source_fact_ref(source_fact_ref):
            raise ValueError(
                "source_fact_bodies packet carry is admitted only for step-output refs"
            )
        bodies[source_fact_ref] = safe_source_fact_body(str(body))
    for source_fact_ref, body in vessel_bodies.items():
        bodies.setdefault(source_fact_ref, safe_source_fact_body(str(body)))
    return bodies


def _vessel_step_output_source_fact_bodies(
    packet: Mapping[str, Any],
    source_fact_refs: Iterable[str],
    *,
    building_id: str,
    supplied_bodies: Mapping[str, str],
) -> Mapping[str, str]:
    missing_refs = [
        ref
        for ref in source_fact_refs
        if _is_step_output_source_fact_ref(ref) and ref not in supplied_bodies
    ]
    if not missing_refs:
        return {}
    roots = _candidate_source_fact_building_roots(packet, building_id=building_id)
    bodies: dict[str, str] = {}
    for ref in missing_refs:
        path = _vessel_step_output_path(ref, roots)
        if path is None:
            continue
        try:
            bodies[ref] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
    return bodies


def _candidate_source_fact_building_roots(
    packet: Mapping[str, Any],
    *,
    building_id: str,
) -> tuple[Path, ...]:
    roots: list[Path] = []
    project_ref = _optional_text_from_mapping(packet, "project_ref")
    if project_ref and building_id:
        try:
            roots.append((buildings_root_for(project_ref) / building_id).resolve())
        except ValueError:
            pass
    if building_id:
        roots.append((Path(DEFAULT_BUILDINGS_ROOT) / building_id).resolve())
    seen: set[str] = {str(root) for root in roots}
    if building_id:
        for base in (_REPO_ROOT / "project").glob("*/buildings"):
            candidate = (base / building_id).resolve()
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                roots.append(candidate)
    return tuple(roots)


def _vessel_step_output_path(
    source_fact_ref: str,
    roots: Iterable[Path],
) -> Path | None:
    normalized = _required_text("source_fact", source_fact_ref).replace("\\", "/")
    if normalized.startswith("step-output:"):
        return None
    marker = "work/step-outputs/"
    index = normalized.find(marker)
    if index < 0:
        return None
    relative = Path(normalized[index:])
    for root in roots:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if candidate.is_file():
            return candidate
    return None


def _supplied_source_fact_bodies(packet: Mapping[str, Any]) -> Mapping[str, str]:
    supplied = packet.get("source_fact_bodies")
    if supplied is None:
        return {}
    result: dict[str, str] = {}
    supplied_bodies = _mapping("source_fact_bodies", supplied)
    for source_fact_ref, body in supplied_bodies.items():
        ref = _required_text("source_fact_bodies ref", source_fact_ref)
        result[ref] = safe_source_fact_body(str(body))
    return result


def _source_fact_bodies(source_facts: Iterable[str]) -> Mapping[str, str]:
    bodies: dict[str, str] = {}
    for source_fact in source_facts:
        if _is_step_output_source_fact_ref(source_fact):
            raise ValueError(
                "step-output source_fact refs must be supplied from step-close evidence"
            )
        path = _readable_source_fact_path(source_fact)
        if path is None:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        bodies[source_fact] = safe_source_fact_body(body)
    return bodies


def _is_step_output_source_fact_ref(source_fact: str) -> bool:
    text = _required_text("source_fact", source_fact)
    normalized = text.replace("\\", "/")
    return (
        "work/step-outputs/" in normalized
        or normalized.startswith("step-output:")
        or normalized.endswith("/step-output.json")
    )


def _readable_source_fact_path(source_fact: str) -> Path | None:
    text = _required_text("source_fact", source_fact)
    if "://" in text or text.startswith(("env:", "keychain:", "external_secret:")):
        return None
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = _REPO_ROOT / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(_REPO_ROOT.resolve())
    except (OSError, ValueError):
        return None
    if not resolved.is_file():
        return None
    return resolved


__all__ = [
    "AdapterFrontierEvidenceWritten",
    "AgentObjectContractData",
    "AgentRunCompletionRecord",
    "AgentRunPreparationRecord",
    "BuildingPlanSupportResult",
    "BuildingRunSupportResult",
    "MinimalCrossingRecord",
    "ThreeAxisStepRows",
    "agent_run_building_map_packet",
    "agent_run_lifecycle_mapping",
    "build_minimal_crossing",
    "claim_chat_session_envelope",
    "complete_agent_run_from_prepared",
    "load_agent_object_resource",
    "prepare_agent_run_from_step_rows",
    "record_from_public_facts",
    "release_chat_session_claim",
    "resume_building_plan",
    "run_building_once",
    "run_building_plan",
    "submit_chat_session_return",
]
