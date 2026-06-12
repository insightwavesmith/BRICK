"""Raw stream and claim-trace recording writer."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.recording.capture import graph_ready_json_object, graph_ready_timestamp
from brick_protocol.support.recording.contracts import (
    AdapterErrorFrontierTracePacket,
    ChatSessionParkFrontierTracePacket,
    RawClaimTracePacket,
)


def write_raw_and_claim_trace(
    building_root: Path,
    building_id: str,
    packet: RawClaimTracePacket,
) -> tuple[Path, ...]:
    written: list[Path] = []
    raw_dir = building_root / "raw"
    claim_root = building_root / "evidence" / "claim_trace"
    recorded_at = graph_ready_timestamp()
    _write_jsonl(
        raw_dir / "brick-work.jsonl",
        _graph_ready_records(
            packet.brick_raw_records,
            building_id=building_id,
            local_prefix="raw/brick-work.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.brick_work",
        ),
        written,
    )
    _write_jsonl(
        raw_dir / "agent-return.jsonl",
        _graph_ready_records(
            packet.agent_raw_records,
            building_id=building_id,
            local_prefix="raw/agent-return.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.agent_return",
        ),
        written,
    )
    _write_jsonl(
        raw_dir / "link.jsonl",
        _graph_ready_records(
            packet.link_raw_records,
            building_id=building_id,
            local_prefix="raw/link.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.link",
        ),
        written,
    )
    _write_json(
        claim_root / "brick" / "work_contract.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.brick_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/brick/work_contract.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "agent" / "returned_claims.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.agent_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/agent/returned_claims.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "transfer_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_transfer_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/transfer_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "carry_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_carry_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/carry_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "sufficiency_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_sufficiency_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/sufficiency_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "movement_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_movement_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/movement_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    # E1 (U5.5 slice-3): the live gate-sequence GateFact receipts + the FINAL
    # policy action, recorded alongside the existing 4 Link claim traces.
    _write_json(
        claim_root / "link" / "gate_receipt_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_gate_receipt_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/gate_receipt_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "policy_action_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_policy_action_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/policy_action_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    return tuple(written)


def write_adapter_error_frontier_raw_and_claim_trace(
    building_root: Path,
    building_id: str,
    packet: AdapterErrorFrontierTracePacket,
) -> tuple[Path, ...]:
    written: list[Path] = []
    raw_dir = building_root / "raw"
    claim_root = building_root / "evidence" / "claim_trace"
    recorded_at = graph_ready_timestamp()
    if packet.brick_raw_records:
        _write_jsonl(
            raw_dir / "brick-work.jsonl",
            _graph_ready_records(
                packet.brick_raw_records,
                building_id=building_id,
                local_prefix="raw/brick-work.jsonl",
                recorded_at=recorded_at,
                event_type="bp.raw.brick_work",
            ),
            written,
        )
    _write_jsonl(
        raw_dir / "agent-received.jsonl",
        _graph_ready_records(
            packet.agent_received_raw_records,
            building_id=building_id,
            local_prefix="raw/agent-received.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.agent_received",
        ),
        written,
    )
    _write_jsonl(
        raw_dir / "adapter-error.jsonl",
        _graph_ready_records(
            packet.adapter_error_raw_records,
            building_id=building_id,
            local_prefix="raw/adapter-error.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.adapter_error",
        ),
        written,
    )
    if packet.link_raw_records:
        _write_jsonl(
            raw_dir / "link.jsonl",
            _graph_ready_records(
                packet.link_raw_records,
                building_id=building_id,
                local_prefix="raw/link.jsonl",
                recorded_at=recorded_at,
                event_type="bp.raw.link",
            ),
            written,
        )
    _write_json(
        claim_root / "brick" / "work_contract.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.brick_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/brick/work_contract.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "agent" / "receipt_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.agent_receipt_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/agent/receipt_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "frontier_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_frontier_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/frontier_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    return tuple(written)


def write_chat_session_park_frontier_raw_and_claim_trace(
    building_root: Path,
    building_id: str,
    packet: ChatSessionParkFrontierTracePacket,
) -> tuple[Path, ...]:
    written: list[Path] = []
    raw_dir = building_root / "raw"
    claim_root = building_root / "evidence" / "claim_trace"
    recorded_at = graph_ready_timestamp()
    if packet.brick_raw_records:
        _write_jsonl(
            raw_dir / "brick-work.jsonl",
            _graph_ready_records(
                packet.brick_raw_records,
                building_id=building_id,
                local_prefix="raw/brick-work.jsonl",
                recorded_at=recorded_at,
                event_type="bp.raw.brick_work",
            ),
            written,
        )
    _write_jsonl(
        raw_dir / "agent-received.jsonl",
        _graph_ready_records(
            packet.agent_received_raw_records,
            building_id=building_id,
            local_prefix="raw/agent-received.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.agent_received",
        ),
        written,
    )
    _write_jsonl(
        raw_dir / "chat-session-park.jsonl",
        _graph_ready_records(
            packet.park_raw_records,
            building_id=building_id,
            local_prefix="raw/chat-session-park.jsonl",
            recorded_at=recorded_at,
            event_type="bp.raw.chat_session_parked",
        ),
        written,
    )
    if packet.link_raw_records:
        _write_jsonl(
            raw_dir / "link.jsonl",
            _graph_ready_records(
                packet.link_raw_records,
                building_id=building_id,
                local_prefix="raw/link.jsonl",
                recorded_at=recorded_at,
                event_type="bp.raw.link",
            ),
            written,
        )
    _write_json(
        claim_root / "brick" / "work_contract.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.brick_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/brick/work_contract.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "agent" / "receipt_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.agent_receipt_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/agent/receipt_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    _write_json(
        claim_root / "link" / "frontier_trace.json",
        _graph_ready_claim_trace(
            {"facts": list(packet.link_frontier_claim_facts)},
            building_id=building_id,
            local_id="evidence/claim_trace/link/frontier_trace.json",
            recorded_at=recorded_at,
        ),
        written,
    )
    return tuple(written)


def _graph_ready_records(
    records: tuple[Mapping[str, object], ...],
    *,
    building_id: str,
    local_prefix: str,
    recorded_at: str,
    event_type: str,
) -> tuple[Mapping[str, object], ...]:
    enriched: list[Mapping[str, object]] = []
    for index, record in enumerate(records, start=1):
        enriched.append(
            graph_ready_json_object(
                record,
                building_id=building_id,
                local_id=f"{local_prefix}#{index}",
                recorded_at=recorded_at,
                event_type=event_type,
                subject=str(record.get("step_ref") or record.get("raw_ref") or index),
            )
        )
    return tuple(enriched)


def _graph_ready_claim_trace(
    value: Mapping[str, object],
    *,
    building_id: str,
    local_id: str,
    recorded_at: str,
) -> Mapping[str, object]:
    return graph_ready_json_object(
        value,
        building_id=building_id,
        local_id=local_id,
        recorded_at=recorded_at,
        event_type="bp.claim_trace",
    )


def _write_json(path: Path, value: Mapping[str, object], written: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(path)


def _write_jsonl(path: Path, values: tuple[Mapping[str, object], ...], written: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for value in values
    )
    path.write_text(text, encoding="utf-8")
    written.append(path)


def reconcile_claim_trace_raw_manifest_from_raw(building_root: Path | str) -> tuple[Path, ...]:
    """Repair raw-manifest resolution using only this Building root's raw streams.

    The verb is for already-written roots whose final accumulated rewrite left
    adapter-error frontier claim traces behind. It authors no Movement or
    verdict: it only makes present raw streams and claim_trace raw_refs agree.
    """

    root = Path(building_root)
    raw_dir = root / "raw"
    claim_root = root / "evidence" / "claim_trace"
    manifest_path = raw_dir / "raw-manifest.json"
    if not raw_dir.is_dir():
        raise ValueError(f"building root has no raw directory: {root}")
    if not claim_root.is_dir():
        raise ValueError(f"building root has no claim_trace directory: {root}")
    raw_records_by_path = _raw_jsonl_records_by_path(raw_dir)
    raw_index = _raw_ref_index(raw_records_by_path)
    claim_raw_refs = _claim_trace_raw_refs(claim_root)
    derived_link_records = _derive_missing_link_frontier_records(
        root,
        claim_raw_refs=claim_raw_refs,
        raw_index=raw_index,
        raw_records_by_path=raw_records_by_path,
    )
    for record in derived_link_records:
        for ref in _raw_refs_from_value(record):
            raw_index.setdefault(ref, ("raw/link.jsonl", record))

    unresolved = [ref for ref in claim_raw_refs if ref not in raw_index]
    if unresolved:
        raise ValueError(
            "claim_trace raw_ref cannot be derived from this root's raw streams: "
            + ", ".join(unresolved)
        )

    written: list[Path] = []
    if derived_link_records:
        link_path = raw_dir / "link.jsonl"
        existing_link_records = list(raw_records_by_path.get("raw/link.jsonl", ()))
        merged_link_records = [*existing_link_records, *derived_link_records]
        _write_jsonl(link_path, tuple(merged_link_records), written)
        raw_records_by_path["raw/link.jsonl"] = tuple(merged_link_records)

    manifest = _read_json_object(manifest_path) if manifest_path.is_file() else {}
    reconciled_manifest = _reconciled_raw_manifest(
        root.name,
        manifest,
        raw_records_by_path,
    )
    _write_json(manifest_path, reconciled_manifest, written)
    return tuple(written)


def _raw_jsonl_records_by_path(raw_dir: Path) -> dict[str, tuple[Mapping[str, Any], ...]]:
    records_by_path: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for path in sorted(raw_dir.glob("*.jsonl")):
        records = _read_jsonl_objects(path)
        if records:
            records_by_path[f"raw/{path.name}"] = records
    return records_by_path


def _read_jsonl_objects(path: Path) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{path}: invalid JSONL row {line_number}") from exc
        if not isinstance(value, Mapping):
            raise ValueError(f"{path}: JSONL row {line_number} must be an object")
        records.append(value)
    return tuple(records)


def _raw_ref_index(
    raw_records_by_path: Mapping[str, tuple[Mapping[str, Any], ...]],
) -> dict[str, tuple[str, Mapping[str, Any]]]:
    index: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for rel_path, records in raw_records_by_path.items():
        for record in records:
            for ref in _raw_refs_from_value(record):
                index.setdefault(ref, (rel_path, record))
    return index


def _claim_trace_raw_refs(claim_root: Path) -> list[str]:
    refs: list[str] = []
    for path in sorted(claim_root.glob("*/*.json")):
        value = _read_json_object(path)
        for ref in _raw_refs_from_claim_trace(value):
            if ref not in refs:
                refs.append(ref)
    return refs


def _raw_refs_from_claim_trace(value: Any) -> list[str]:
    refs: list[str] = []
    if not isinstance(value, Mapping):
        return refs
    facts = value.get("facts")
    if not isinstance(facts, list):
        return refs
    for fact in facts:
        if not isinstance(fact, Mapping):
            continue
        raw_refs = fact.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.extend(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
    return list(dict.fromkeys(refs))


def _derive_missing_link_frontier_records(
    root: Path,
    *,
    claim_raw_refs: list[str],
    raw_index: Mapping[str, tuple[str, Mapping[str, Any]]],
    raw_records_by_path: Mapping[str, tuple[Mapping[str, Any], ...]],
) -> tuple[Mapping[str, Any], ...]:
    missing_frontier_refs = [
        ref
        for ref in claim_raw_refs
        if ref.startswith("raw:link-frontier:") and ref not in raw_index
    ]
    if not missing_frontier_refs:
        return ()
    link_record_count = len(raw_records_by_path.get("raw/link.jsonl", ()))
    records: list[Mapping[str, Any]] = []
    for offset, frontier_ref in enumerate(missing_frontier_refs, start=1):
        index = frontier_ref.rsplit(":", maxsplit=1)[-1]
        adapter_ref = f"raw:adapter-error:{index}"
        adapter_entry = raw_index.get(adapter_ref)
        if adapter_entry is None:
            raise ValueError(
                "link-frontier raw_ref cannot be derived without matching adapter-error raw row: "
                f"{frontier_ref}"
            )
        adapter_record = adapter_entry[1]
        step_ref = str(adapter_record.get("step_ref") or "")
        recorded_at = str(
            adapter_record.get("recorded_at")
            or adapter_record.get("time")
            or adapter_record.get("generatedAtTime")
            or graph_ready_timestamp()
        )
        records.append(
            graph_ready_json_object(
                {
                    "adapter_error_ref": str(adapter_record.get("adapter_error_ref") or ""),
                    "building_id": str(adapter_record.get("building_id") or root.name),
                    "frontier_kind": "agent_incomplete",
                    "observed_boundary_ref": str(adapter_record.get("brick_instance_ref") or ""),
                    "raw_ref": frontier_ref,
                    "raw_refs": [frontier_ref],
                    "step_ref": step_ref,
                    "transition_record_created": False,
                },
                building_id=str(adapter_record.get("building_id") or root.name),
                local_id=f"raw/link.jsonl#{link_record_count + offset}",
                recorded_at=recorded_at,
                event_type="bp.raw.link",
                subject=step_ref or frontier_ref,
            )
        )
    return tuple(records)


def _reconciled_raw_manifest(
    building_id: str,
    manifest: Mapping[str, Any],
    raw_records_by_path: Mapping[str, tuple[Mapping[str, Any], ...]],
) -> Mapping[str, Any]:
    entries_value = manifest.get("entries")
    entries = [dict(entry) for entry in entries_value if isinstance(entry, Mapping)] if isinstance(entries_value, list) else []
    entry_paths = {str(entry.get("path")) for entry in entries if isinstance(entry.get("path"), str)}
    for rel_path in sorted(raw_records_by_path):
        raw_refs = _raw_refs_from_records(raw_records_by_path[rel_path])
        if not raw_refs:
            continue
        if rel_path in entry_paths:
            for entry in entries:
                if entry.get("path") == rel_path:
                    entry.update(_raw_manifest_entry(rel_path, raw_refs))
                    break
        else:
            entries.append(_raw_manifest_entry(rel_path, raw_refs))
    raw_refs = [
        ref
        for entry in entries
        for ref in _raw_refs_from_value(entry.get("raw_refs"))
    ]
    return {
        **dict(manifest),
        "building_id": str(manifest.get("building_id") or building_id),
        "raw_refs": list(dict.fromkeys(raw_refs)),
        "entries": entries,
    }


def _raw_manifest_entry(rel_path: str, raw_refs: list[str]) -> dict[str, Any]:
    source = "support/recording/raw_claim_trace.py reconciled from root raw streams"
    if rel_path == "raw/brick-work.jsonl":
        return {
            "path": rel_path,
            "source": source,
            "content_shape": "jsonl Brick work rows",
            "proof_limit": "support evidence only",
            "axis_owner": "Brick",
            "record_role": "primary",
            "raw_refs": raw_refs,
        }
    if rel_path in {
        "raw/agent-return.jsonl",
        "raw/agent-received.jsonl",
        "raw/adapter-error.jsonl",
        "raw/chat-session-park.jsonl",
        "raw/chat-session-claim.jsonl",
        "raw/chat-session-submission.jsonl",
    }:
        return {
            "path": rel_path,
            "source": source,
            "content_shape": _agent_raw_content_shape(rel_path),
            "proof_limit": "support evidence only",
            "axis_owner": "Agent",
            "record_role": "primary",
            "raw_refs": raw_refs,
        }
    if rel_path != "raw/link.jsonl":
        raise ValueError(f"unsupported raw stream for reconciliation: {rel_path}")
    return {
        "path": rel_path,
        "source": source,
        "content_shape": "jsonl Link transition rows and frontier absence rows",
        "proof_limit": "support evidence only",
        "axis_owner": "Link",
        "record_role": "primary",
        "raw_refs": raw_refs,
    }


def _agent_raw_content_shape(rel_path: str) -> str:
    if rel_path == "raw/agent-received.jsonl":
        return "jsonl Agent receipt rows"
    if rel_path == "raw/adapter-error.jsonl":
        return "jsonl adapter exception observation rows"
    if rel_path == "raw/chat-session-park.jsonl":
        return "jsonl chat-session park observation rows"
    if rel_path == "raw/chat-session-claim.jsonl":
        return "jsonl chat-session claim observation rows"
    if rel_path == "raw/chat-session-submission.jsonl":
        return "jsonl chat-session submission observation rows"
    return "jsonl Agent returned payload refs"


def _raw_refs_from_records(records: tuple[Mapping[str, Any], ...]) -> list[str]:
    refs: list[str] = []
    for record in records:
        for ref in _raw_refs_from_value(record):
            if ref not in refs:
                refs.append(ref)
    return refs


def _raw_refs_from_value(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, Mapping):
        raw_ref = value.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.append(raw_ref)
        raw_refs = value.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.extend(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
    elif isinstance(value, list):
        refs.extend(str(ref) for ref in value if isinstance(ref, str) and ref.strip())
    return list(dict.fromkeys(refs))


def _read_json_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path}: invalid JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: JSON value must be an object")
    return value
