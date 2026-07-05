"""Append-only operator correction observations.

This support writer records a human/COO-authored correction over a measured
Building evidence tail. It never edits existing ledgers, fabricates Agent
returns or receipts, chooses Movement, or judges quality/success.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    REPO_ROOT,
    _jsonl_records,
    _rel,
    _repo_path,
)
from brick_protocol.support.operator.evidence_status import evidence_status
from brick_protocol.support.recording.capture import graph_ready_timestamp


CORRECTION_STREAM = "raw/operator-correction.jsonl"
ERROR_GROUNDLESS_CORRECTION = "groundless_correction"
ERROR_RETURN_FORGING_CORRECTION = "return_forging_correction"
ERROR_INVALID_CORRECTION_AUTHOR = "invalid_correction_author"


def author_correction_observation(
    building_root: str | Path,
    *,
    author_ref: str,
    grounds_refs: Sequence[str],
    note: str = "",
    declared_tail_snapshot: Mapping[str, Any] | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Append one correction observation after measuring the current tail.

    ``declared_tail_snapshot`` is optional caller evidence. When supplied, it
    must match the measured tail exactly; mismatches are refused as return
    forging risk because the caller would be asserting ledger facts support did
    not observe.
    """

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    author_text = str(author_ref or "").strip()
    grounds = [str(ref).strip() for ref in grounds_refs if str(ref).strip()]
    if not (author_text.startswith("human:") or author_text.startswith("coo:")):
        return _refusal(
            ERROR_INVALID_CORRECTION_AUTHOR,
            "correction author_ref must start with human: or coo:",
            root=root,
            repo=repo,
        )
    measured_tail = measure_correction_tail(root, repo_root=repo)
    if not _tail_has_correction_ground(measured_tail):
        return _refusal(
            ERROR_GROUNDLESS_CORRECTION,
            "no measurable evidence tail exists for correction",
            root=root,
            repo=repo,
            measured_tail=measured_tail,
        )
    if declared_tail_snapshot is not None and _normalized_tail(
        declared_tail_snapshot
    ) != _normalized_tail(measured_tail):
        return _refusal(
            ERROR_RETURN_FORGING_CORRECTION,
            "declared correction tail does not match measured evidence",
            root=root,
            repo=repo,
            measured_tail=measured_tail,
        )
    if not grounds:
        return _refusal(
            ERROR_GROUNDLESS_CORRECTION,
            "correction requires at least one grounds_ref",
            root=root,
            repo=repo,
            measured_tail=measured_tail,
        )

    stream_path = root / CORRECTION_STREAM
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    correction_index = len(_jsonl_records(stream_path)) + 1
    correction_ref = f"raw:operator-correction:{correction_index:02d}"
    row: dict[str, Any] = {
        "raw_ref": correction_ref,
        "correction_ref": correction_ref,
        "record_kind": "operator_correction_observation",
        "building_root": _rel(repo, root),
        "author_ref": author_text,
        "grounds_refs": grounds,
        "note": str(note or "").strip(),
        "measured_tail": measured_tail,
        "recorded_at": graph_ready_timestamp(),
        "proof_limits": [
            "support correction observation only",
            "append-only raw/operator-correction.jsonl row",
            "measured evidence tail only",
            "not a fabricated Agent return or receipt",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of the correction grounds",
            "whether caller/COO should approve a disposition",
            "future Building outcome",
        ],
    }
    with stream_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
    return {"ok": True, "correction_ref": correction_ref, "row": row}


def measure_correction_tail(
    building_root: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Measure the ledger tail fields a correction row may cover."""

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    status = evidence_status(root, repo_root=repo)
    received_records = _jsonl_records(root / "raw" / "agent-received.jsonl")
    return_records = _jsonl_records(root / "raw" / "agent-return.jsonl")
    if not return_records:
        return_records = _jsonl_records(root / "raw" / "agent-returns.jsonl")
    return {
        "missing_files": sorted(str(item) for item in status.missing_files),
        "agent_received_count": len(received_records),
        "agent_return_count": len(return_records),
        "agent_received_counts_by_step": _counts_by_step(received_records),
        "agent_return_counts_by_step": _counts_by_step(return_records),
    }


def _counts_by_step(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        step_ref = str(record.get("step_ref") or "unknown")
        counter[step_ref] += 1
    return dict(sorted(counter.items()))


def _tail_has_correction_ground(tail: Mapping[str, Any]) -> bool:
    if tail.get("missing_files"):
        return True
    try:
        received = int(tail.get("agent_received_count") or 0)
        returned = int(tail.get("agent_return_count") or 0)
    except (TypeError, ValueError):
        return False
    return received > returned


def _normalized_tail(tail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "missing_files": sorted(str(item) for item in tail.get("missing_files") or []),
        "agent_received_count": int(tail.get("agent_received_count") or 0),
        "agent_return_count": int(tail.get("agent_return_count") or 0),
        "agent_received_counts_by_step": {
            str(key): int(value)
            for key, value in dict(tail.get("agent_received_counts_by_step") or {}).items()
        },
        "agent_return_counts_by_step": {
            str(key): int(value)
            for key, value in dict(tail.get("agent_return_counts_by_step") or {}).items()
        },
    }


def _refusal(
    error_kind: str,
    message: str,
    *,
    root: Path,
    repo: Path,
    measured_tail: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "error_kind": error_kind,
        "error_message": message,
        "building_root": _rel(repo, root),
        "proof_limits": [
            "support correction refusal only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }
    if measured_tail is not None:
        result["measured_tail"] = dict(measured_tail)
    return result
