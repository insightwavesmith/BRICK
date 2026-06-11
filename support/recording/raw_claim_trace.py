"""Raw stream and claim-trace recording writer."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from brick_protocol.support.recording.capture import graph_ready_json_object, graph_ready_timestamp
from brick_protocol.support.recording.contracts import AdapterErrorFrontierTracePacket, RawClaimTracePacket


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
