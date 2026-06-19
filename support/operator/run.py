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
from brick_protocol.link.transition import TransitionFact
from brick_protocol.support.connection.agent_adapter import (
    ADAPTER_CHAT_SESSION,
    AgentAdapterRequest,
    AgentAdapterParked,
    AgentAdapterResult,
    AgentBrainCallable,
    CommandRunner,
    _timeout_expired_reap_reason,
    connect_agent_brain,
    safe_source_fact_body,
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
    INLINE_TASK_SOURCE_REF,
    _AGENT_OBJECT_ALLOWED_KEYS,
    _AGENT_ROW_ALLOWED_KEYS,
    _AGENT_OBJECT_REF_FIELDS,
    _BRICK_ROW_ALLOWED_KEYS,
    _DEFAULT_AGENT_OBJECT_ROOT,
    _DECLARED_GATE_REFS_KEY,
    _FORBIDDEN_PAYLOAD_KEYS,
    _LINK_ROW_ALLOWED_KEYS,
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
from brick_protocol.support.recording.building_map import BuildingMapWriteResult
from brick_protocol.support.recording.capture import (
    BuildingLifecycleWriteResult,
    DEFAULT_BUILDINGS_ROOT,
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


def _chat_session_park_frontier_transition_lifecycle(
    *,
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
) -> Mapping[str, Any]:
    hold_record = _chat_session_park_hold_record(
        building_id=building_id,
        completed_step_results=list(completed_step_results),
        failed_preparation=failed_preparation,
        reroute_records=[],
        node_budget={},
        node_landings={},
        cascade_depth=0,
        parent_reroute_ref="",
    )
    return _chat_session_park_paused_lifecycle(hold_record)


_CHAT_SESSION_TOKEN_RE = re.compile(r"[a-z]+(?:-[a-z]+){3,7}\Z")
_CHAT_SESSION_TOKEN_WORDS = (
    "amber",
    "basil",
    "cedar",
    "copper",
    "delta",
    "ember",
    "fable",
    "garden",
    "harbor",
    "ivory",
    "juniper",
    "kernel",
    "lantern",
    "meadow",
    "north",
    "orbit",
    "prairie",
    "quartz",
    "river",
    "silver",
    "timber",
    "umbra",
    "velvet",
    "willow",
)


def claim_chat_session_envelope(
    building_root: Path | str,
    *,
    lane_ref: str,
    step_ref: str = "",
    attempt_index: int = 0,
) -> Mapping[str, Any]:
    """Atomically claim one parked chat-session work envelope.

    This writes only passive support records next to the parked envelope. It
    does not invoke a provider, compute gates, resume, or choose Movement.
    """

    root = Path(building_root)
    step_dir = _chat_session_step_output_dir(
        root,
        step_ref=step_ref,
        attempt_index=attempt_index,
    )
    lane = _required_text("lane_ref", lane_ref)
    _reject_chat_session_session_text("lane_ref", lane)
    return _with_chat_session_claim_lock(
        step_dir,
        lambda: _claim_chat_session_envelope_locked(root, step_dir, lane_ref=lane),
    )


def submit_chat_session_return(
    building_root: Path | str,
    *,
    claim_token: str,
    returned: Mapping[str, Any],
    step_ref: str = "",
    attempt_index: int = 0,
) -> Mapping[str, Any]:
    """Passively write a claimed chat-session returned payload.

    The write is admission-only. It does not resume the Building and cannot
    compute gates; `resume_building_plan()` is the only consumer.
    """

    root = Path(building_root)
    step_dir = _chat_session_step_output_dir(
        root,
        step_ref=step_ref,
        attempt_index=attempt_index,
    )
    token = _validate_chat_session_claim_token(claim_token)
    claim = _active_chat_session_claim(step_dir)
    if claim.get("claim_token") != token:
        raise ValueError("chat-session submission claim_token does not match active claim")
    returned_payload = _validate_chat_session_submission_return(root, step_dir, returned)
    submission_path = step_dir / "submission.json"
    if submission_path.exists():
        raise FileExistsError(f"chat-session submission already exists: {submission_path}")
    building_id = _chat_session_building_id(root, claim)
    step = _required_text("claim.step_ref", claim.get("step_ref"))
    record = {
        "kind": "chat_session_submission_record",
        "schema_version": "chat-session-submission-record-0",
        "submission_ref": (
            "chat-session-submission:"
            + building_id
            + ":"
            + _resource_slug("step_ref", step.replace(":", "-"))
        ),
        "claim_ref": _required_text("claim.claim_ref", claim.get("claim_ref")),
        "claim_token": token,
        "building_id": building_id,
        "step_ref": step,
        "attempt_index": _chat_session_attempt_index_from_step_dir(step_dir),
        "returned": dict(returned_payload),
        "support_record_role": "passive-return-submission",
        "evidence_refs": {
            "claim_ref": "work/step-outputs/" + step_dir.name + "/claim.json",
            "submission_ref": "work/step-outputs/" + step_dir.name + "/submission.json",
            "work_envelope_ref": "work/step-outputs/" + step_dir.name + "/work-envelope.json",
        },
        "proof_limits": [
            "passive chat-session submission file only",
            "does not invoke provider",
            "does not compute gates",
            "does not resume Building",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "chat-session performer quality",
            "future resume behavior",
            "semantic correctness of submitted return",
        ],
    }
    recorded_at = graph_ready_timestamp()
    graph_record = graph_ready_json_object(
        record,
        building_id=building_id,
        local_id="work/step-outputs/" + step_dir.name + "/submission.json",
        recorded_at=recorded_at,
        event_type="bp.step_output.chat_session_submission",
        subject=step,
    )
    _write_json_exclusive(submission_path, graph_record)
    _append_chat_session_raw_record(
        root,
        "chat-session-submission",
        building_id=building_id,
        event_type="bp.raw.chat_session_submission",
        record=graph_record,
        recorded_at=recorded_at,
    )
    return graph_record


def release_chat_session_claim(
    building_root: Path | str,
    *,
    disposition_author_ref: str,
    reason_refs: Sequence[str],
    step_ref: str = "",
    attempt_index: int = 0,
) -> Mapping[str, Any]:
    """Invalidate an active claim by explicit human/COO disposition."""

    root = Path(building_root)
    step_dir = _chat_session_step_output_dir(
        root,
        step_ref=step_ref,
        attempt_index=attempt_index,
    )
    author_ref = _required_text("disposition_author_ref", disposition_author_ref)
    if not author_ref.startswith(("human:", "coo:")):
        raise ValueError("claim release disposition_author_ref must start with human: or coo:")
    checked_reason_refs = [
        _required_text(f"reason_refs[{index}]", value)
        for index, value in enumerate(reason_refs)
    ]
    if not checked_reason_refs:
        raise ValueError("claim release requires at least one reason_ref")
    return _with_chat_session_claim_lock(
        step_dir,
        lambda: _release_chat_session_claim_locked(
            root,
            step_dir,
            disposition_author_ref=author_ref,
            reason_refs=tuple(checked_reason_refs),
        ),
    )


def _claim_chat_session_envelope_locked(
    building_root: Path,
    step_dir: Path,
    *,
    lane_ref: str,
) -> Mapping[str, Any]:
    existing = _read_chat_session_optional_json(step_dir / "claim.json")
    if existing and existing.get("claim_state") == "claimed":
        existing_ref = _optional_text_value(existing.get("claim_ref")) or "<unknown-claim>"
        existing_lane = _optional_text_value(existing.get("lane_ref")) or "<unknown-lane>"
        raise FileExistsError(
            "chat-session envelope already claimed by "
            + existing_lane
            + " at "
            + existing_ref
        )
    token = _mint_chat_session_claim_token()
    parked = _read_chat_session_json_object(step_dir / "parked.json")
    building_id = _chat_session_building_id(building_root, parked)
    step_ref = _required_text("parked.step_ref", parked.get("step_ref"))
    attempt_index = _chat_session_attempt_index_from_step_dir(step_dir)
    claim_ref = (
        "chat-session-claim:"
        + building_id
        + ":"
        + _resource_slug("step_ref", step_ref.replace(":", "-"))
        + f":attempt-{attempt_index}"
    )
    record = {
        "kind": "chat_session_claim_record",
        "schema_version": "chat-session-claim-record-0",
        "claim_ref": claim_ref,
        "claim_state": "claimed",
        "claim_token": token,
        "building_id": building_id,
        "step_ref": step_ref,
        "attempt_index": attempt_index,
        "lane_ref": lane_ref,
        "work_envelope_ref": _required_text("parked.work_envelope_ref", parked.get("work_envelope_ref")),
        "parked_ref": _required_text("parked.parked_ref", parked.get("parked_ref")),
        "support_record_role": "exclusive-claim-for-passive-chat-session-submission",
        "evidence_refs": {
            "claim_ref": "work/step-outputs/" + step_dir.name + "/claim.json",
            "work_envelope_ref": "work/step-outputs/" + step_dir.name + "/work-envelope.json",
            "parked_ref": "work/step-outputs/" + step_dir.name + "/parked.json",
        },
        "proof_limits": [
            "chat-session claim support record only",
            "exclusive filesystem claim only",
            "not Agent returned payload",
            "not AgentFact",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "future submission behavior",
            "future resume behavior",
            "chat-session performer quality",
        ],
    }
    recorded_at = graph_ready_timestamp()
    graph_record = graph_ready_json_object(
        record,
        building_id=building_id,
        local_id="work/step-outputs/" + step_dir.name + "/claim.json",
        recorded_at=recorded_at,
        event_type="bp.step_output.chat_session_claimed",
        subject=step_ref,
    )
    _write_json_atomic(step_dir / "claim.json", graph_record)
    _append_chat_session_raw_record(
        building_root,
        "chat-session-claim",
        building_id=building_id,
        event_type="bp.raw.chat_session_claimed",
        record=graph_record,
        recorded_at=recorded_at,
    )
    return graph_record


def _release_chat_session_claim_locked(
    building_root: Path,
    step_dir: Path,
    *,
    disposition_author_ref: str,
    reason_refs: tuple[str, ...],
) -> Mapping[str, Any]:
    if (step_dir / "submission.json").exists():
        raise ValueError("chat-session claim with a submission cannot be released")
    claim = _active_chat_session_claim(step_dir)
    released = dict(claim)
    released["claim_state"] = "released"
    released["released_by_ref"] = disposition_author_ref
    released["release_reason_refs"] = list(reason_refs)
    released["support_record_role"] = "released-claim-slot"
    released["not_proven"] = list(
        _merge_texts(
            released.get("not_proven"),
            ("future claim behavior after release",),
        )
    )
    building_id = _chat_session_building_id(building_root, released)
    recorded_at = graph_ready_timestamp()
    released = graph_ready_json_object(
        released,
        building_id=building_id,
        local_id="work/step-outputs/" + step_dir.name + "/claim.json",
        recorded_at=recorded_at,
        event_type="bp.step_output.chat_session_claim_released",
        subject=_required_text("claim.step_ref", claim.get("step_ref")),
    )
    _write_json_atomic(step_dir / "claim.json", released)
    _append_chat_session_raw_record(
        building_root,
        "chat-session-claim",
        building_id=building_id,
        event_type="bp.raw.chat_session_claim_released",
        record=released,
        recorded_at=recorded_at,
    )
    return released


def _with_chat_session_claim_lock(step_dir: Path, callback):
    lock_path = step_dir / ".claim-update.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise FileExistsError(f"chat-session claim update already in progress: {lock_path}") from exc
    try:
        os.close(fd)
        return callback()
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _chat_session_step_output_dir(
    building_root: Path,
    *,
    step_ref: str,
    attempt_index: int,
) -> Path:
    root = building_root
    if step_ref:
        if attempt_index <= 0:
            raise ValueError("attempt_index must be positive when step_ref is supplied")
        step_dir = root / _step_output_dir_ref(step_ref, attempt_index)
    else:
        matches = sorted((root / "work" / "step-outputs").glob("*/parked.json"))
        if not matches:
            raise FileNotFoundError("chat-session parked step output not found")
        if len(matches) != 1:
            raise ValueError("multiple parked chat-session step outputs found; supply step_ref")
        step_dir = matches[0].parent
    if not (step_dir / "parked.json").is_file():
        raise FileNotFoundError(f"chat-session parked record not found: {step_dir / 'parked.json'}")
    if not (step_dir / "work-envelope.json").is_file():
        raise FileNotFoundError(
            f"chat-session work envelope not found: {step_dir / 'work-envelope.json'}"
        )
    return step_dir


def _chat_session_attempt_index_from_step_dir(step_dir: Path) -> int:
    marker = "-attempt-"
    if marker not in step_dir.name:
        raise ValueError(f"chat-session step-output directory lacks attempt marker: {step_dir}")
    text = step_dir.name.rsplit(marker, 1)[1]
    if not text.isdigit() or text.startswith("0"):
        raise ValueError(f"chat-session step-output directory has invalid attempt marker: {step_dir}")
    return int(text)


def _active_chat_session_claim(step_dir: Path) -> Mapping[str, Any]:
    if not (step_dir / "claim.json").is_file():
        raise ValueError("parked building resume requires active chat-session claim")
    claim = _read_chat_session_json_object(step_dir / "claim.json")
    if claim.get("kind") != "chat_session_claim_record":
        raise ValueError("chat-session claim.json has wrong kind")
    if claim.get("claim_state") != "claimed":
        raise ValueError("chat-session claim is not active")
    _validate_chat_session_claim_token(claim.get("claim_token"))
    return claim


def _mint_chat_session_claim_token() -> str:
    for _attempt in range(16):
        token = "-".join(secrets.choice(_CHAT_SESSION_TOKEN_WORDS) for _ in range(4))
        try:
            return _validate_chat_session_claim_token(token)
        except ValueError:
            continue
    raise RuntimeError("chat-session claim token minter produced no admitted token")


def _validate_chat_session_claim_token(value: Any) -> str:
    token = _required_text("claim_token", value)
    if not _CHAT_SESSION_TOKEN_RE.fullmatch(token):
        raise ValueError("chat-session claim_token must be a lower-case word tuple")
    _reject_chat_session_session_text("claim_token", token)
    return token


def _validate_chat_session_submission_return(
    building_root: Path,
    step_dir: Path,
    returned: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(returned, Mapping):
        raise TypeError("chat-session submission returned payload must be a mapping")
    payload = dict(returned)
    _validate_no_payload_forbidden(
        "chat_session_submission.returned",
        payload,
        _RETURN_FORBIDDEN_KEYS,
    )
    _reject_chat_session_session_text("chat_session_submission.returned", payload)
    parked = _read_chat_session_json_object(step_dir / "parked.json")
    required_shape = _optional_text_value(parked.get("required_return_shape"))
    if not required_shape:
        envelope = _read_chat_session_json_object(step_dir / "work-envelope.json")
        required_shape = _optional_text_value(envelope.get("required_return_shape"))
    missing = [
        field
        for field in parse_required_return_shape(required_shape)
        if field not in payload
    ]
    if missing:
        raise ValueError(
            "chat-session submission missing required return field(s): "
            + ", ".join(missing)
        )
    return payload


def _reject_chat_session_session_text(label: str, value: Any) -> None:
    _reject_session_like_text(label, value)


def _read_chat_session_optional_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    return _read_chat_session_json_object(path)


def _read_chat_session_json_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"failed to read chat-session JSON record: {path}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"chat-session JSON record must be an object: {path}")
    return value


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}-{secrets.token_hex(4)}")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _append_chat_session_raw_record(
    building_root: Path,
    stream_name: str,
    *,
    building_id: str,
    event_type: str,
    record: Mapping[str, Any],
    recorded_at: str,
) -> None:
    path = building_root / "raw" / f"{stream_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_record = graph_ready_json_object(
        record,
        building_id=building_id,
        local_id=f"raw/{stream_name}.jsonl",
        recorded_at=recorded_at,
        event_type=event_type,
        subject=_optional_text_value(record.get("step_ref")) or stream_name,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(raw_record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")


def _chat_session_frontier_history_snapshot(root: Path) -> Mapping[str, Any]:
    return {
        "agent_received_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "agent-received.jsonl"
        ),
        "chat_session_park_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "chat-session-park.jsonl"
        ),
        "chat_session_claim_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "chat-session-claim.jsonl"
        ),
        "chat_session_submission_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "chat-session-submission.jsonl"
        ),
        "link_frontier_records": tuple(
            record
            for record in _chat_session_jsonl_objects(root / "raw" / "link.jsonl")
            if any(
                ref.startswith("raw:link-frontier:")
                for ref in _chat_session_raw_refs_from_value(record)
            )
        ),
    }


def _adapter_error_frontier_history_snapshot(root: Path) -> Mapping[str, Any]:
    return {
        "agent_received_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "agent-received.jsonl"
        ),
        "adapter_error_raw_refs": _chat_session_raw_refs_from_jsonl(
            root / "raw" / "adapter-error.jsonl"
        ),
        "link_frontier_records": tuple(
            record
            for record in _chat_session_jsonl_objects(root / "raw" / "link.jsonl")
            if any(
                ref.startswith("raw:link-frontier:")
                for ref in _chat_session_raw_refs_from_value(record)
            )
        ),
    }


def _preserve_chat_session_frontier_history_after_resume(
    root: Path,
    snapshot: Mapping[str, Any],
) -> None:
    _preserve_chat_session_link_frontier_records(root, snapshot)
    manifest_path = root / "raw" / "raw-manifest.json"
    if not manifest_path.is_file():
        return
    manifest = dict(_read_chat_session_json_object(manifest_path))
    entries_value = manifest.get("entries")
    entries = [dict(entry) for entry in entries_value if isinstance(entry, Mapping)] if isinstance(entries_value, list) else []
    raw_refs_value = manifest.get("raw_refs")
    raw_refs = [str(ref) for ref in raw_refs_value if isinstance(ref, str)] if isinstance(raw_refs_value, list) else []

    agent_refs = [str(ref) for ref in snapshot.get("agent_received_raw_refs", ()) if isinstance(ref, str)]
    park_refs = [str(ref) for ref in snapshot.get("chat_session_park_raw_refs", ()) if isinstance(ref, str)]
    claim_refs = [str(ref) for ref in snapshot.get("chat_session_claim_raw_refs", ()) if isinstance(ref, str)]
    submission_refs = [
        str(ref)
        for ref in snapshot.get("chat_session_submission_raw_refs", ())
        if isinstance(ref, str)
    ]
    link_frontier_refs = [
        ref
        for record in snapshot.get("link_frontier_records", ())
        if isinstance(record, Mapping)
        for ref in _chat_session_raw_refs_from_value(record)
        if ref.startswith("raw:link-frontier:")
    ]
    for ref in [*agent_refs, *park_refs, *claim_refs, *submission_refs, *link_frontier_refs]:
        if ref not in raw_refs:
            raw_refs.append(ref)
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/agent-received.jsonl",
        source="support/operator/run.py preserved chat-session receipt rows across resume",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=agent_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-park.jsonl",
        source="support/operator/run.py preserved chat-session park rows across resume",
        content_shape="jsonl chat-session park observation rows",
        axis_owner="Agent",
        raw_refs=park_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-claim.jsonl",
        source="support/operator/run.py preserved chat-session claim rows across resume",
        content_shape="jsonl chat-session claim observation rows",
        axis_owner="Agent",
        raw_refs=claim_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-submission.jsonl",
        source="support/operator/run.py preserved chat-session submission rows across resume",
        content_shape="jsonl chat-session submission observation rows",
        axis_owner="Agent",
        raw_refs=submission_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="support/operator/run.py declared Link rows and preserved chat-session frontier rows",
        content_shape="jsonl Link transition rows and frontier absence rows",
        axis_owner="Link",
        raw_refs=_chat_session_raw_refs_for_manifest_entry(root / "raw" / "link.jsonl"),
    )
    manifest["raw_refs"] = raw_refs
    manifest["entries"] = entries
    _write_json_atomic(manifest_path, manifest)


def _preserve_adapter_error_frontier_history_after_resume(
    root: Path,
    snapshot: Mapping[str, Any],
) -> None:
    _preserve_chat_session_link_frontier_records(root, snapshot)
    manifest_path = root / "raw" / "raw-manifest.json"
    if not manifest_path.is_file():
        return
    manifest = dict(_read_chat_session_json_object(manifest_path))
    entries_value = manifest.get("entries")
    entries = [dict(entry) for entry in entries_value if isinstance(entry, Mapping)] if isinstance(entries_value, list) else []
    raw_refs_value = manifest.get("raw_refs")
    raw_refs = [str(ref) for ref in raw_refs_value if isinstance(ref, str)] if isinstance(raw_refs_value, list) else []

    agent_refs = [str(ref) for ref in snapshot.get("agent_received_raw_refs", ()) if isinstance(ref, str)]
    adapter_error_refs = [str(ref) for ref in snapshot.get("adapter_error_raw_refs", ()) if isinstance(ref, str)]
    link_frontier_refs = [
        ref
        for record in snapshot.get("link_frontier_records", ())
        if isinstance(record, Mapping)
        for ref in _chat_session_raw_refs_from_value(record)
        if ref.startswith("raw:link-frontier:")
    ]
    for ref in [*agent_refs, *adapter_error_refs, *link_frontier_refs]:
        if ref not in raw_refs:
            raw_refs.append(ref)
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/agent-received.jsonl",
        source="support/operator/run.py preserved adapter-error receipt rows across resume",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=agent_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/adapter-error.jsonl",
        source="support/operator/run.py preserved adapter exception rows across resume",
        content_shape="jsonl adapter exception observation rows",
        axis_owner="Agent",
        raw_refs=adapter_error_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="support/operator/run.py declared Link rows and preserved adapter-error frontier rows",
        content_shape="jsonl Link transition rows and frontier absence rows",
        axis_owner="Link",
        raw_refs=_chat_session_raw_refs_for_manifest_entry(root / "raw" / "link.jsonl"),
    )
    manifest["raw_refs"] = raw_refs
    manifest["entries"] = entries
    _write_json_atomic(manifest_path, manifest)


def _preserve_chat_session_link_frontier_records(
    root: Path,
    snapshot: Mapping[str, Any],
) -> None:
    link_path = root / "raw" / "link.jsonl"
    preserved = [
        record
        for record in snapshot.get("link_frontier_records", ())
        if isinstance(record, Mapping)
    ]
    if not preserved:
        return
    current = _chat_session_jsonl_objects(link_path)
    current_refs = {
        ref for record in current for ref in _chat_session_raw_refs_from_value(record)
    }
    prefix: list[Mapping[str, Any]] = []
    for record in preserved:
        refs = _chat_session_raw_refs_from_value(record)
        if refs and all(ref in current_refs for ref in refs):
            continue
        prefix.append(dict(record))
        current_refs.update(refs)
    merged = prefix + list(current)
    link_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for record in merged
        ),
        encoding="utf-8",
    )


def _chat_session_jsonl_objects(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.is_file():
        return ()
    records: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, Mapping):
            records.append(value)
    return tuple(records)


def _chat_session_raw_refs_from_jsonl(path: Path) -> list[str]:
    refs: list[str] = []
    for record in _chat_session_jsonl_objects(path):
        for ref in _chat_session_raw_refs_from_value(record):
            if ref not in refs:
                refs.append(ref)
    return refs


def _chat_session_raw_refs_for_manifest_entry(path: Path) -> list[str]:
    return _chat_session_raw_refs_from_jsonl(path)


def _chat_session_raw_refs_from_value(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, Mapping):
        raw_ref = value.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.append(raw_ref)
        raw_refs = value.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.extend(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
        for child in value.values():
            refs.extend(_chat_session_raw_refs_from_value(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_chat_session_raw_refs_from_value(child))
    return list(dict.fromkeys(refs))


def _merge_chat_session_manifest_entry(
    entries: list[dict[str, Any]],
    *,
    path: str,
    source: str,
    content_shape: str,
    axis_owner: str,
    raw_refs: Sequence[str],
) -> None:
    cleaned_refs = [ref for ref in dict.fromkeys(raw_refs) if ref]
    if not cleaned_refs:
        return
    for entry in entries:
        if entry.get("path") == path:
            merged_refs = list(entry.get("raw_refs", ())) if isinstance(entry.get("raw_refs"), list) else []
            for ref in cleaned_refs:
                if ref not in merged_refs:
                    merged_refs.append(ref)
            entry["source"] = source
            entry["content_shape"] = content_shape
            entry["axis_owner"] = axis_owner
            entry["raw_refs"] = merged_refs
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


def _chat_session_building_id(building_root: Path, record: Mapping[str, Any]) -> str:
    value = _optional_text_value(record.get("building_id"))
    if value:
        return _path_segment("building_id", value)
    return _path_segment("building_id", building_root.name)


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
    checked_proof_limits = _proof_limits_tuple(
        proof_limits if proof_limits is not None else packet.get("proof_limits")
    )
    try:
        return _run_dynamic_graph_walker(
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
    except AdapterFrontierEvidenceWritten as adapter_frontier:
        # The adapter raised/timed out before an AgentFact existed; the dynamic
        # walker has already written the resumable adapter-error frontier (hold).
        # Return that already-held Building as a clean held result instead of
        # crashing -- a flaky adapter call ends recoverable, not fatal.
        return _held_result_from_adapter_frontier_signal(adapter_frontier)


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
    checked_proof_limits = _proof_limits_tuple(proof_limits)
    frontier = observe_building_frontier(root, repo_root=_REPO_ROOT)
    if frontier.get("frontier_kind") == "chat_session_parked":
        return _resume_chat_session_parked_building_plan(
            root,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            checked_proof_limits=checked_proof_limits,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
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
    return result


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
# and is a different file.) Parity copy lives in walker_kernel.py.
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
    # any Link field. Absent usage (no codex --json turn.completed) is recorded as
    # null. MEASUREMENT ONLY; no cap is applied.
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
    write_adapter_usage_meter(
        building_root,
        building_id,
        step_ref=step_ref,
        adapter_ref=request.adapter_ref,
        selected_model_ref=request.selected_model_ref,
        attempt_index=attempt_index,
        adapter_usage=adapter_result.adapter_usage,
        existing_records=_existing_adapter_usage_records(building_root),
    )


def _existing_adapter_usage_records(building_root: Path) -> tuple[Mapping[str, Any], ...]:
    path = building_root / "raw" / "adapter-usage.jsonl"
    if not path.is_file():
        return ()
    records: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            value = json.loads(text)
        except ValueError:
            continue
        if isinstance(value, Mapping):
            records.append(value)
    return tuple(records)


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
        return _adapter_result_with_write_observation(
            adapter_result,
            write_observation_before,
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
    return {
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
    text = " ".join(str(exc).split())
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
    return text[:240]


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


def _brick_comparison_fields_from_evidence(
    brick_comparison: BrickComparisonFact,
    prefix: str,
) -> tuple[str, ...]:
    return brick_comparison.fields_from_evidence(prefix)


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
    if value.get("preferred_adapter_ref") is not None:
        kwargs["preferred_adapter_ref"] = _required_text(
            "Agent Object preferred_adapter_ref",
            value.get("preferred_adapter_ref"),
        )
    for key in _AGENT_OBJECT_REF_FIELDS:
        kwargs[key] = _text_tuple(f"Agent Object {key}", value.get(key, ()))
    return AgentObjectContractData(**kwargs)


def _handoff_address_refs(value: Any) -> tuple[str, ...]:
    """Flatten a delivered link_handoff_refs packet to its ADDRESS strings.

    MAIL-REPAIR (Smith ruling B2, 0611): the AgentReceipt records which handoff
    addresses were delivered with the work. Addresses are the text items of
    ``*_refs`` list fields anywhere in the packet (declared incoming /
    route_replay handoffs AND runtime_handoffs alike); bodies never ride, so
    nothing else is collected. Order-preserving, de-duplicated; an absent or
    empty packet -> (). Pure data read; no Movement choice, no judgment.
    """

    collected: list[str] = []
    seen: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if (
                    isinstance(key, str)
                    and key.endswith("_refs")
                    and isinstance(child, list)
                ):
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
        "selected_model_ref": _optional_text_from_mapping(packet, "selected_model_ref") or "",
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
        ),
        "link_handoff_refs": (
            _mapping("link_handoff_refs", packet["link_handoff_refs"])
            if "link_handoff_refs" in packet
            else {}
        ),
        "write_scope": _write_scope_from_brick_row(prepared.step_rows.brick_row),
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
) -> Mapping[str, str]:
    source_fact_refs = tuple(source_facts)
    supplied_bodies = _supplied_source_fact_bodies(packet)
    missing_step_output_refs = [
        source_fact
        for source_fact in source_fact_refs
        if _is_step_output_source_fact_ref(source_fact)
        and source_fact not in supplied_bodies
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
    return bodies


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


def _step_output_relative_ref(source_fact: str) -> str | None:
    text = _required_text("source_fact", source_fact).replace("\\", "/")
    marker = "work/step-outputs/"
    if marker not in text:
        return None
    return text[text.index(marker) :]


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
