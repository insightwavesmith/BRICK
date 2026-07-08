"""Chat-session step subsystem for the Building run surface (E2/S11 split).

PURE RELOCATION (E2/S11): the self-contained chat-session claim/submit/release
+ frontier-history-preservation subsystem lifted VERBATIM out of
brick_protocol/support/operator/run.py. It records support evidence for the human-as-agent
chat-session adapter lane; it chooses no Movement, creates no undeclared
GateFact, and judges no success or quality. run.py re-imports the public +
internal names it still references, so every existing call site is unchanged.
"""

from __future__ import annotations

import json
import os
import re
import secrets

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import make_agent_fact
from brick_protocol.brick.work import parse_required_return_shape
from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.walker_frontier import (
    _chat_session_park_hold_record,
    _chat_session_park_paused_lifecycle,
)
from brick_protocol.support.recording.contracts import require_positive_int
from brick_protocol.support.operator.primitives import (
    _RETURN_FORBIDDEN_KEYS,
    _merge_texts,
    _optional_text_value,
    _path_segment,
    _reject_session_like_text,
    _required_text,
    _resource_slug,
    _validate_no_payload_forbidden,
)
from brick_protocol.support.recording.capture import (
    graph_ready_json_object,
    graph_ready_timestamp,
)
from brick_protocol.support.recording.step_outputs import (
    _step_output_dir_ref,
)


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
        attempt_index = require_positive_int(
            attempt_index,
            "attempt_index",
            allow_decimal_text=False,
            error_text="must be positive when step_ref is supplied",
        )
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
    make_agent_fact(
        received_work={
            "building_root": str(building_root),
            "step_output_dir": str(step_dir),
            "work_envelope_ref": _optional_text_value(parked.get("work_envelope_ref")) or "",
        },
        returned=payload,
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
        source="brick_protocol/support/operator/run.py preserved chat-session receipt rows across resume",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=agent_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-park.jsonl",
        source="brick_protocol/support/operator/run.py preserved chat-session park rows across resume",
        content_shape="jsonl chat-session park observation rows",
        axis_owner="Agent",
        raw_refs=park_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-claim.jsonl",
        source="brick_protocol/support/operator/run.py preserved chat-session claim rows across resume",
        content_shape="jsonl chat-session claim observation rows",
        axis_owner="Agent",
        raw_refs=claim_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/chat-session-submission.jsonl",
        source="brick_protocol/support/operator/run.py preserved chat-session submission rows across resume",
        content_shape="jsonl chat-session submission observation rows",
        axis_owner="Agent",
        raw_refs=submission_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="brick_protocol/support/operator/run.py declared Link rows and preserved chat-session frontier rows",
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
        source="brick_protocol/support/operator/run.py preserved adapter-error receipt rows across resume",
        content_shape="jsonl Agent receipt rows",
        axis_owner="Agent",
        raw_refs=agent_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/adapter-error.jsonl",
        source="brick_protocol/support/operator/run.py preserved adapter exception rows across resume",
        content_shape="jsonl adapter exception observation rows",
        axis_owner="Agent",
        raw_refs=adapter_error_refs,
    )
    _merge_chat_session_manifest_entry(
        entries,
        path="raw/link.jsonl",
        source="brick_protocol/support/operator/run.py declared Link rows and preserved adapter-error frontier rows",
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
