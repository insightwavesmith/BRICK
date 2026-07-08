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
import os
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
) -> tuple[Path, Mapping[str, Any]]:
    """Append ONE per-step adapter token-usage record to the meter journal.

    ``adapter_usage`` is the codex-native usage mapping (counter keys ->
    int | None) parsed by the adapter, or ``None`` when no usage was observed.
    Returns the written path plus the graph-ready record that was appended.

    PURE APPEND-ONLY raw evidence: every pre-existing journal line (well-formed
    record OR malformed text, no distinction) is left BYTE-FOR-BYTE and
    ORDER untouched. We never read, re-parse, re-serialize, reorder, or rewrite
    them. We only count the existing non-empty lines to give the new record a
    monotonic ``record_index`` (so its ``local_id`` stays unique), then write the
    single new record line to the END of the file.
    """

    if not isinstance(building_root, Path):
        raise TypeError("building_root must be a Path")
    path = building_root / _ADAPTER_USAGE_RAW_STREAM
    record = build_adapter_usage_record(
        building_id=building_id,
        step_ref=step_ref,
        adapter_ref=adapter_ref,
        selected_model_ref=selected_model_ref,
        attempt_index=attempt_index,
        adapter_usage=adapter_usage,
        record_index=_existing_line_count(path) + 1,
    )
    _append_one_record(path, record)
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
    observed_at = recorded_at or graph_ready_timestamp()
    dispatched_model = _dispatched_model(adapter_ref, selected_model_ref, adapter_usage)
    record: dict[str, Any] = {
        "adapter_usage_ref": f"adapter-usage:{step_ref}:attempt-{attempt_index}",
        "building_id": building_id,
        "step_ref": step_ref,
        "attempt_index": attempt_index,
        "adapter_ref": adapter_ref,
        "selected_model_ref": selected_model_ref,
        "dispatched_model": dispatched_model,
        "adapter_usage_recorded_at": observed_at,
        "model_alias_resolution": {
            "adapter_ref": adapter_ref,
            "selected_model_ref": selected_model_ref,
            "dispatched_model": dispatched_model,
        },
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
        recorded_at=observed_at,
        event_type="bp.raw.adapter_usage",
        subject=step_ref,
    )


def _dispatched_model(
    adapter_ref: str,
    selected_model_ref: str,
    adapter_usage: Mapping[str, Any] | None,
) -> str:
    if isinstance(adapter_usage, Mapping):
        dispatched = adapter_usage.get("dispatched_model")
        if isinstance(dispatched, str) and dispatched.strip():
            return dispatched.strip()
    try:
        from brick_protocol.support.connection.adapter_model_casting import (
            project_model_ref_to_cli_arg,
        )
        from brick_protocol.support.operator.provider_registry import resolve_model_alias_ref

        projected = project_model_ref_to_cli_arg(
            adapter_ref,
            resolve_model_alias_ref(adapter_ref, selected_model_ref),
        )
    except (TypeError, ValueError):
        projected = ""
    return projected or "declared-default"


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


def _existing_line_count(path: Path) -> int:
    """Count the non-empty lines already in the journal (read-only, no rewrite).

    Used ONLY to derive the next record_index. We never parse, classify, or
    re-emit these lines -- they are append-only raw evidence and stay byte-for-byte
    where they are.
    """

    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _append_one_record(path: Path, record: Mapping[str, Any]) -> None:
    """Append exactly ONE record line to the END of the journal.

    Opens in append mode so no existing byte is read back or rewritten; the new
    line is the only thing written. Pre-existing lines (well-formed or malformed)
    keep their original bytes and order.

    If the file is non-empty and its LAST byte is not a newline (a truncated
    tail), we first append a single ``\n`` separator so the new record starts on
    its own line instead of fusing onto the broken tail. The separator is an
    ADDITION only -- no pre-existing byte is read back, modified, or rewritten, so
    the append-only / byte-preservation contract holds.

    Concurrency note: this assumes the single Building step-close write path
    (``record_index = existing-line-count + 1`` then append). Concurrent appends
    from multiple writers are out of scope here and to be re-examined if a
    multi-writer path is opened (#58 etc.).
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    needs_separator = False
    if path.is_file():
        size = path.stat().st_size
        if size > 0:
            with path.open("rb") as existing:
                existing.seek(-1, os.SEEK_END)
                needs_separator = existing.read(1) != b"\n"
    with path.open("a", encoding="utf-8") as journal:
        if needs_separator:
            journal.write("\n")
        journal.write(line)
