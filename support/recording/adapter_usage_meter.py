"""Per-step adapter token-usage meter writer (TrackA-A1: INSTRUMENT FIRST).

This is a SUPPORT-ONLY meter. It records the per-step codex token usage parsed
from ``codex exec --json`` (the ``turn.completed.usage`` block) into a graph-ready
JSONL journal at ``raw/adapter-usage.jsonl``. It mirrors the writer shape of
``raw_claim_trace.py`` / ``step_outputs.py``.

INVARIANTS (gate-no-measure / truth-before-quality):
  * The token counts are a Brick-axis SUPPORT FACT. They live ONLY in this meter
    journal -- NEVER inside AgentFact.returned and NEVER inside any Link field.
  * NO quality / fault / success label is attached. The record carries raw
    counters and absence markers only.
  * NO cap / enforcement here. Measurement only (any cap is TrackA-A2).

GRACEFUL FALLBACK: when the adapter emitted no usage (older codex without
``--json``, or no ``turn.completed``), the record carries ``usage_present: False``
and every counter is ``None`` (null). The writer never crashes and never
fabricates a count.

KEY DISCIPLINE: the recorded counter keys are constrained to the canonical
``WORKFLOW_IMPORT_USAGE_METRIC_KEYS`` allowlist (reused, not re-declared). The
codex-native ``cached_input_tokens`` is mapped onto the allowlisted
``cache_read_input_tokens``; codex ``reasoning_output_tokens`` has no allowlist
slot and is recorded under the dedicated, clearly-non-allowlist
``reasoning_output_tokens`` provenance key so it is never mistaken for a
billable-input counter.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.workflow_import import (
    WORKFLOW_IMPORT_USAGE_METRIC_KEYS,
)
from brick_protocol.support.recording.capture import (
    graph_ready_json_object,
    graph_ready_timestamp,
)

# The codex-native usage counter -> allowlisted meter key mapping. Only the keys
# that have a home in WORKFLOW_IMPORT_USAGE_METRIC_KEYS are mapped here; codex's
# reasoning_output_tokens is recorded separately as provenance (see below).
_CODEX_USAGE_KEY_TO_ALLOWLIST_KEY: Mapping[str, str] = {
    "input_tokens": "input_tokens",
    "output_tokens": "output_tokens",
    "cached_input_tokens": "cache_read_input_tokens",
}

# codex emits this but the allowlist has no slot for it; keep it as labelled
# provenance so the raw codex shape is preserved without polluting the allowlist
# meter keys.
_CODEX_PROVENANCE_KEY = "reasoning_output_tokens"

# The allowlisted counter keys this meter records (always present, null when
# absent). Constrained to the canonical allowlist so the meter can never widen
# the usage vocabulary by accident.
_METER_ALLOWLIST_KEYS: tuple[str, ...] = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
)

_ADAPTER_USAGE_RAW_STREAM = "raw/adapter-usage.jsonl"


def write_adapter_usage_meter(
    building_root: Path,
    building_id: str,
    *,
    step_ref: str,
    adapter_ref: str,
    selected_model_ref: str = "",
    attempt_index: int = 1,
    adapter_usage: Mapping[str, Any] | None,
    existing_records: tuple[Mapping[str, Any], ...] = (),
) -> tuple[Path, Mapping[str, Any]]:
    """Append one per-step adapter token-usage record to the meter journal.

    ``adapter_usage`` is the codex-native usage mapping (counter keys ->
    int | None) parsed by the adapter, or ``None`` when no usage was observed.
    Returns the written path plus the graph-ready record that was appended.
    """

    if not isinstance(building_root, Path):
        raise TypeError("building_root must be a Path")
    record = build_adapter_usage_record(
        building_id=building_id,
        step_ref=step_ref,
        adapter_ref=adapter_ref,
        selected_model_ref=selected_model_ref,
        attempt_index=attempt_index,
        adapter_usage=adapter_usage,
        record_index=len(existing_records) + 1,
    )
    path = building_root / _ADAPTER_USAGE_RAW_STREAM
    records = (*existing_records, record)
    _append_jsonl(path, records)
    return path, record


def build_adapter_usage_record(
    *,
    building_id: str,
    step_ref: str,
    adapter_ref: str,
    selected_model_ref: str = "",
    attempt_index: int = 1,
    adapter_usage: Mapping[str, Any] | None,
    record_index: int = 1,
    recorded_at: str = "",
) -> Mapping[str, Any]:
    """Build the graph-ready support record for one step's adapter token usage."""

    if not isinstance(step_ref, str) or not step_ref.strip():
        raise ValueError("step_ref must be non-empty text")
    if not isinstance(adapter_ref, str) or not adapter_ref.strip():
        raise ValueError("adapter_ref must be non-empty text")
    usage_present = isinstance(adapter_usage, Mapping)
    usage_counters = _allowlisted_usage_counters(adapter_usage)
    reasoning = _optional_int(
        adapter_usage.get(_CODEX_PROVENANCE_KEY) if usage_present else None
    )
    record: dict[str, Any] = {
        "adapter_usage_ref": f"adapter-usage:{step_ref}:attempt-{attempt_index}",
        "building_id": building_id,
        "step_ref": step_ref,
        "attempt_index": attempt_index,
        "adapter_ref": adapter_ref,
        "selected_model_ref": selected_model_ref,
        "usage_present": usage_present,
        # ALLOWLISTED token counters (null when absent). NEVER a verdict.
        "usage": usage_counters,
        # codex-native provenance counter with no allowlist slot (null when absent).
        "reasoning_output_tokens": reasoning,
        "raw_ref": f"raw:adapter-usage:{step_ref}:attempt-{attempt_index}",
        "support_record_role": "adapter-token-usage-meter",
        "proof_limits": [
            "adapter token usage support evidence only",
            "not Agent returned payload",
            "not AgentFact",
            "not Link field",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "measurement only; carries no cap",
        ],
        "not_proven": [
            "cumulative session token budget",
            "token amplification cause",
        ],
    }
    return graph_ready_json_object(
        record,
        building_id=building_id,
        local_id=f"{_ADAPTER_USAGE_RAW_STREAM}#{record_index}",
        recorded_at=recorded_at or graph_ready_timestamp(),
        event_type="bp.raw.adapter_usage",
        subject=step_ref,
    )


def _allowlisted_usage_counters(adapter_usage: Mapping[str, Any] | None) -> dict[str, Any]:
    """Project codex usage onto the allowlisted counter keys (absent -> null).

    Every allowlisted key this meter records MUST be a member of the canonical
    WORKFLOW_IMPORT_USAGE_METRIC_KEYS allowlist -- enforced loudly so the meter
    can never silently widen the usage vocabulary.
    """

    counters: dict[str, Any] = {}
    for allowlist_key in _METER_ALLOWLIST_KEYS:
        if allowlist_key not in WORKFLOW_IMPORT_USAGE_METRIC_KEYS:
            raise ValueError(
                f"adapter usage meter key {allowlist_key!r} is not in the usage allowlist"
            )
        counters[allowlist_key] = None
    if not isinstance(adapter_usage, Mapping):
        return counters
    for codex_key, allowlist_key in _CODEX_USAGE_KEY_TO_ALLOWLIST_KEY.items():
        counters[allowlist_key] = _optional_int(adapter_usage.get(codex_key))
    return counters


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _append_jsonl(path: Path, records: tuple[Mapping[str, Any], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for value in records
    )
    path.write_text(text, encoding="utf-8")
