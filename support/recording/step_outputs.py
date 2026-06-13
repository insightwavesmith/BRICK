"""Per-step output and non-binding transition concern recording writer."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import (
    RETURNED_FORBIDDEN_KEYS as _ROUTE_REQUEST_FORBIDDEN_KEYS,
    TRANSITION_CONCERN_ALLOWED_KEYS as _TRANSITION_CONCERN_ALLOWED_KEYS,
    TRANSITION_CONCERN_KINDS as _TRANSITION_CONCERN_KINDS,
    validate_transition_concern_evidence,
)
from brick_protocol.support.recording.capture import graph_ready_json_object, graph_ready_timestamp
from brick_protocol.support.recording.contracts import (
    AdapterErrorObservation,
    ChatSessionParkObservation,
    StepOutputObservation,
)

from brick_protocol.support.connection.secret_text import contains_raw_secret_text


def write_step_outputs(
    building_root: Path,
    building_id: str,
    observations: tuple[StepOutputObservation, ...],
    *,
    proof_limits: tuple[str, ...],
    existing_policy: str = "replace",
) -> tuple[Path, ...]:
    written: list[Path] = []
    # δ-b PER-STEP recorded_at: prefer the per-step wall-clock time captured by
    # the caller (run.py's step loop); fall back to a single graph_ready_timestamp
    # for callers that do not supply one so the writer stays backward-compatible.
    fallback_recorded_at = graph_ready_timestamp()
    attempts = _step_output_attempts(observations)
    for index, observation in enumerate(observations, start=1):
        attempt_index = attempts[index - 1]
        write_step_output(
            building_root,
            building_id,
            observation,
            attempt_index=attempt_index,
            proof_limits=proof_limits,
            recorded_at=observation.recorded_at or fallback_recorded_at,
            existing_policy=existing_policy,
            written=written,
        )
    return tuple(written)


def write_step_output(
    building_root: Path,
    building_id: str,
    observation: StepOutputObservation,
    *,
    attempt_index: int,
    proof_limits: tuple[str, ...],
    recorded_at: str = "",
    existing_policy: str = "replace",
    written: list[Path] | None = None,
) -> tuple[Path, ...]:
    if attempt_index <= 0:
        raise ValueError("attempt_index must be positive")
    target_written: list[Path] = written if written is not None else []
    _validate_existing_policy(existing_policy)
    step_ref = observation.step_ref
    output_ref = _step_output_manifest_ref(step_ref, attempt_index)
    route_request_ref = _step_output_route_request_ref(step_ref, attempt_index)
    transition_concern_ref = _step_output_transition_concern_ref(step_ref, attempt_index)
    route_request = _route_request_from_returned(observation.returned)
    transition_concern = _transition_concern_from_returned(observation.returned)
    if route_request is not None and transition_concern is not None:
        raise ValueError("Agent returned must not include both route_request and transition_concern_evidence")
    effective_recorded_at = recorded_at or observation.recorded_at or graph_ready_timestamp()
    output_packet: dict[str, Any] = {
        "step_output_ref": f"step-output:{_step_output_slug(step_ref)}:attempt-{attempt_index}",
        "building_id": building_id,
        "step_ref": step_ref,
        "attempt_index": attempt_index,
        "brick_instance_ref": observation.brick_instance_ref,
        "agent_object_ref": observation.agent_object_ref,
        "agent_fact_fields": ["received_work", "returned"],
        "received_work_ref": observation.received_work_ref,
        "returned_fact_ref": observation.returned_fact_ref,
        "returned": observation.returned,
        "transition_concern_ref": transition_concern_ref if transition_concern is not None else "",
        "route_request_ref": route_request_ref if route_request is not None else "",
        "evidence_refs": {
            "raw_ref": observation.raw_ref,
            "raw_stream_ref": "raw/agent-return.jsonl",
            "claim_trace_ref": "evidence/claim_trace/agent/returned_claims.json",
            "building_map_ref": "work/building-map.json",
        },
        "proof_limits": list(proof_limits),
        "not_proven": list(observation.not_proven),
    }
    if observation.task_source_ref:
        output_packet["task_source_ref"] = observation.task_source_ref
        output_packet["evidence_refs"]["task_source_ref"] = observation.task_source_ref
    # U5.5 RESUME-GATE-RECORD: persist the step's live gate-sequence decision AT-TIME
    # so resume can READ it back (never recompute). Absent when the step declared no
    # gate policy (record is None) — keeps no-policy step-outputs byte-stable.
    if observation.gate_sequence_decision_record is not None:
        output_packet["gate_sequence_decision_record"] = observation.gate_sequence_decision_record
    _write_json(
        building_root / output_ref,
        graph_ready_json_object(
            output_packet,
            building_id=building_id,
            local_id=output_ref,
            recorded_at=effective_recorded_at,
            event_type="bp.step_output",
            subject=step_ref,
        ),
        target_written,
        existing_policy=existing_policy,
    )
    if route_request is not None:
        route_packet = {
            "route_request_ref": f"route-request:{_step_output_slug(step_ref)}:attempt-{attempt_index}",
            "step_output_ref": output_ref,
            "building_id": building_id,
            "step_ref": step_ref,
            "attempt_index": attempt_index,
            "agent_object_ref": observation.agent_object_ref,
            "route_request_returned": route_request,
            "binding": bool(route_request.get("binding", False)),
            "link_role": "historical compatibility Agent carry evidence only",
            "route_phase_boundary": "historical route_request compatibility only",
            "proof_limits": [
                *proof_limits,
                "route_request is historical Agent returned evidence only",
                "not route policy matching",
                "not route materialization",
                "not automatic repair/replay execution",
            ],
            "not_proven": list(
                _merge_texts(
                    observation.not_proven,
                    (
                        "route request policy match",
                        "route request materialization",
                        "automatic repair/replay execution",
                    ),
                )
            ),
        }
        _write_json(
            building_root / route_request_ref,
            graph_ready_json_object(
                route_packet,
                building_id=building_id,
                local_id=route_request_ref,
                recorded_at=effective_recorded_at,
                event_type="bp.step_output.route_request",
                subject=step_ref,
            ),
            target_written,
            existing_policy=existing_policy,
        )
    if transition_concern is not None:
        concern_packet: dict[str, Any] = {
            "transition_concern_ref": f"transition-concern:{_step_output_slug(step_ref)}:attempt-{attempt_index}",
            "step_output_ref": output_ref,
            "building_id": building_id,
            "step_ref": step_ref,
            "attempt_index": attempt_index,
            "agent_object_ref": observation.agent_object_ref,
            "transition_concern_returned": transition_concern,
            "binding": bool(transition_concern.get("binding", False)),
            "link_role": "non-binding Agent transition concern evidence only",
            "transition_boundary": "Agent concern only; Link may adopt, not adopt, or override",
            "proof_limits": [
                *proof_limits,
                "transition_concern_evidence is Agent returned evidence only",
                "not Link Movement",
                "not Link target choice",
                "not route policy matching",
                "not route materialization",
                "not automatic repair/replay execution",
                "not Movement authority",
            ],
            "not_proven": list(
                _merge_texts(
                    observation.not_proven,
                    (
                        "transition concern semantic correctness",
                        "Link disposition correctness",
                        "automatic repair/replay execution",
                    ),
                )
            ),
        }
        _write_json(
            building_root / transition_concern_ref,
            graph_ready_json_object(
                concern_packet,
                building_id=building_id,
                local_id=transition_concern_ref,
                recorded_at=effective_recorded_at,
                event_type="bp.step_output.transition_concern",
                subject=step_ref,
            ),
            target_written,
            existing_policy=existing_policy,
        )
    return tuple(target_written) if written is None else ()


def write_adapter_error_outputs(
    building_root: Path,
    building_id: str,
    observations: tuple[AdapterErrorObservation, ...],
    *,
    proof_limits: tuple[str, ...],
) -> tuple[Path, ...]:
    written: list[Path] = []
    recorded_at = graph_ready_timestamp()
    for observation in observations:
        attempt_index = _adapter_error_attempt_index(observation)
        error_ref = _step_output_adapter_error_ref(observation.step_ref, attempt_index)
        packet: dict[str, Any] = {
            "adapter_error_ref": observation.adapter_error_ref,
            "building_id": building_id,
            "step_ref": observation.step_ref,
            "brick_instance_ref": observation.brick_instance_ref,
            "agent_object_ref": observation.agent_object_ref,
            "adapter_ref": observation.adapter_ref,
            "selected_model_ref": observation.selected_model_ref,
            "input_packet_ref": observation.input_packet_ref,
            "output_packet_ref": observation.output_packet_ref,
            "error_kind": observation.error_kind,
            "exception_type": observation.exception_type,
            "message_excerpt": observation.message_excerpt,
            "agent_fact_created": False,
            "received_work_ref": observation.received_work_ref,
            "evidence_refs": {
                "raw_ref": observation.raw_ref,
                "raw_stream_ref": "raw/adapter-error.jsonl",
                "receipt_trace_ref": "evidence/claim_trace/agent/receipt_trace.json",
                "frontier_trace_ref": "evidence/claim_trace/link/frontier_trace.json",
                "building_map_ref": "work/building-map.json",
            },
            "proof_limits": list(_merge_texts(proof_limits, observation.proof_limits)),
            "not_proven": list(observation.not_proven),
        }
        if observation.task_source_ref:
            packet["task_source_ref"] = observation.task_source_ref
            packet["evidence_refs"]["task_source_ref"] = observation.task_source_ref
        _write_json(
            building_root / error_ref,
            graph_ready_json_object(
                packet,
                building_id=building_id,
                local_id=error_ref,
                recorded_at=recorded_at,
                event_type="bp.step_output.adapter_error",
                subject=observation.step_ref,
            ),
            written,
        )
    return tuple(written)


def write_chat_session_park_outputs(
    building_root: Path,
    building_id: str,
    observations: tuple[ChatSessionParkObservation, ...],
    *,
    proof_limits: tuple[str, ...],
) -> tuple[Path, ...]:
    written: list[Path] = []
    recorded_at = graph_ready_timestamp()
    for observation in observations:
        attempt_index = _chat_session_park_attempt_index(observation)
        envelope_ref = _step_output_work_envelope_ref(observation.step_ref, attempt_index)
        parked_ref = _step_output_parked_ref(observation.step_ref, attempt_index)
        _write_json(
            building_root / envelope_ref,
            dict(observation.work_envelope),
            written,
        )
        packet: dict[str, Any] = {
            "kind": "chat_session_park_record",
            "schema_version": "chat-session-park-record-0",
            "parked_ref": observation.parked_ref,
            "building_id": building_id,
            "step_ref": observation.step_ref,
            "brick_instance_ref": observation.brick_instance_ref,
            "agent_object_ref": observation.agent_object_ref,
            "adapter_ref": observation.adapter_ref,
            "selected_model_ref": observation.selected_model_ref,
            "input_packet_ref": observation.input_packet_ref,
            "output_packet_ref": observation.output_packet_ref,
            "received_work_ref": observation.received_work_ref,
            "work_envelope_ref": observation.work_envelope_ref,
            "park_reason": "chat-session adapter parks declared work before provider invocation",
            "support_record_role": "waiting-for-chat-session-submission",
            "evidence_refs": {
                "raw_ref": observation.raw_ref,
                "raw_stream_ref": "raw/chat-session-park.jsonl",
                "work_envelope_ref": observation.work_envelope_ref,
                "receipt_trace_ref": "evidence/claim_trace/agent/receipt_trace.json",
                "frontier_trace_ref": "evidence/claim_trace/link/frontier_trace.json",
                "building_map_ref": "work/building-map.json",
            },
            "proof_limits": list(_merge_texts(proof_limits, observation.proof_limits)),
            "not_proven": list(observation.not_proven),
        }
        if observation.task_source_ref:
            packet["task_source_ref"] = observation.task_source_ref
            packet["evidence_refs"]["task_source_ref"] = observation.task_source_ref
        _write_json(
            building_root / parked_ref,
            graph_ready_json_object(
                packet,
                building_id=building_id,
                local_id=parked_ref,
                recorded_at=recorded_at,
                event_type="bp.step_output.chat_session_parked",
                subject=observation.step_ref,
            ),
            written,
        )
    return tuple(written)


def step_output_manifest_refs(observations: tuple[StepOutputObservation, ...]) -> list[str]:
    attempts = _step_output_attempts(observations)
    return [
        _step_output_manifest_ref(observation.step_ref, attempts[index])
        for index, observation in enumerate(observations)
    ]


def _step_output_attempts(observations: tuple[StepOutputObservation, ...]) -> tuple[int, ...]:
    counts: dict[str, int] = {}
    attempts: list[int] = []
    for observation in observations:
        step_ref = observation.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        attempts.append(counts[step_ref])
    return tuple(attempts)


def _step_output_slug(step_ref: str) -> str:
    return _resource_slug("step_ref", step_ref.replace(":", "-"))


def _step_output_dir_ref(step_ref: str, attempt_index: int) -> str:
    return f"work/step-outputs/{_step_output_slug(step_ref)}-attempt-{attempt_index}"


def _step_output_manifest_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/step-output.json"


def _step_output_adapter_error_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/adapter-error.json"


def _step_output_work_envelope_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/work-envelope.json"


def _step_output_parked_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/parked.json"


def _step_output_route_request_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/route-request.json"


def _step_output_transition_concern_ref(step_ref: str, attempt_index: int) -> str:
    return f"{_step_output_dir_ref(step_ref, attempt_index)}/transition-concern.json"


def _route_request_from_returned(returned: Any) -> Mapping[str, Any] | None:
    if not isinstance(returned, Mapping):
        return None
    route_request = returned.get("route_request")
    if route_request in (None, False, ""):
        return None
    if not isinstance(route_request, Mapping):
        raise ValueError("route_request must be a JSON-compatible mapping when present")
    _validate_no_payload_forbidden("route_request", route_request, _ROUTE_REQUEST_FORBIDDEN_KEYS)
    return dict(route_request)


def _transition_concern_from_returned(returned: Any) -> Mapping[str, Any] | None:
    if not isinstance(returned, Mapping):
        return None
    concern = returned.get("transition_concern_evidence")
    if concern in (None, False, ""):
        return None
    if not isinstance(concern, Mapping):
        return None
    try:
        _validate_no_payload_forbidden("transition_concern_evidence", concern, _ROUTE_REQUEST_FORBIDDEN_KEYS)
        return validate_transition_concern_evidence(concern)
    except (TypeError, ValueError):
        return None


def _required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _text_tuple(field_name: str, values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for index, value in enumerate(values):
        result.append(_required_text(f"{field_name}[{index}]", value))
    return tuple(result)


def _merge_texts(*values: Any) -> tuple[str, ...]:
    merged: list[str] = []
    for value in values:
        for item in _text_tuple("merged_texts", value):
            if item not in merged:
                merged.append(item)
    return tuple(merged)


def _path_segment(field_name: str, value: Any) -> str:
    cleaned = _required_text(field_name, value)
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"{field_name} must be one path segment")
    return cleaned


def _resource_slug(field_name: str, value: Any) -> str:
    cleaned = _path_segment(field_name, value)
    if ":" in cleaned:
        raise ValueError(f"{field_name} resource slug must not contain ':'")
    if not cleaned.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"{field_name} resource slug contains unsupported characters")
    return cleaned


def _normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _validate_no_payload_forbidden(
    name: str,
    value: Any,
    forbidden_keys: frozenset[str],
) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError(f"{name} contains non-text or blank key")
            key = _normalize_key(raw_key)
            if key in forbidden_keys:
                raise ValueError(f"{name} contains forbidden key {raw_key!r}")
            _validate_no_payload_forbidden(f"{name}.{raw_key}", child, forbidden_keys)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_payload_forbidden(f"{name}[{index}]", child, forbidden_keys)
    elif isinstance(value, str):
        if contains_raw_secret_text(value):
            raise ValueError(f"{name} contains raw credential-looking text")


def _write_json(
    path: Path,
    value: Mapping[str, Any],
    written: list[Path],
    *,
    existing_policy: str = "replace",
) -> None:
    _validate_existing_policy(existing_policy)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and existing_policy == "same_content_or_error":
        if path.is_dir():
            raise IsADirectoryError(f"step-output evidence path is a directory: {path}")
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"existing step-output evidence is not readable: {path}") from exc
        if existing != text:
            raise ValueError(f"existing step-output evidence differs from step-close write: {path}")
        written.append(path)
        return
    path.write_text(text, encoding="utf-8")
    written.append(path)


def _validate_existing_policy(value: str) -> None:
    if value not in {"replace", "same_content_or_error"}:
        raise ValueError("existing_policy must be 'replace' or 'same_content_or_error'")


def _adapter_error_attempt_index(observation: AdapterErrorObservation) -> int:
    suffix = observation.adapter_error_ref.rsplit(":attempt-", 1)
    if len(suffix) == 2:
        try:
            return int(suffix[1])
        except ValueError:
            pass
    return 1


def _chat_session_park_attempt_index(observation: ChatSessionParkObservation) -> int:
    suffix = observation.parked_ref.rsplit(":attempt-", 1)
    if len(suffix) == 2:
        try:
            return int(suffix[1])
        except ValueError:
            pass
    return 1
