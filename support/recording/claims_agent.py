"""Agent crossing-family claim/raw emitters.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
Agent raw records + Agent claim/receipt facts that
``support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern per-crossing-family emitter. Consumes the Agent return /
receipt / performer crossings; authors no Movement, target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.primitives import _raw_ref, _step_fact_ref
from brick_protocol.support.recording.claims_common import _claim_fact

# The adapter-error frontier observation carrier lives with the frontier writer,
# but the Agent receipt claim/raw emitters consume its public fields only.


def _agent_raw_records(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        records.append(
            {
                "raw_ref": _raw_ref("agent", index),
                "raw_refs": [_raw_ref("agent", index)],
                "building_id": building_id,
                "step_ref": prepared.step_rows.step_ref,
                "agent_object_ref": prepared.agent_object.object_ref,
                "agent_fact_fields": ["received_work", "returned"],
                "returned": result.adapter_result.returned_value,
            }
        )
    return tuple(records)


def _agent_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        facts.append(
            _claim_fact(
                axis="Agent",
                fact_ref=_step_fact_ref("agent-fact", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("agent", index)],
                proof_limits=proof_limits,
                not_proven=result.not_proven,
                fact={
                    "received_work": _step_fact_ref("brick-work", index, prepared.step_rows.step_ref),
                    "returned": result.adapter_result.returned_value,
                    "agent_object_ref": prepared.agent_object.object_ref,
                    "agent_fact_fields": ["received_work", "returned"],
                },
            )
        )
    return facts


def _adapter_error_agent_received_raw_records(
    building_id: str,
    completed_step_results: tuple[BuildingRunSupportResult, ...],
    failed_preparation: AgentRunPreparationRecord,
    observation: Any,
) -> Iterable[Mapping[str, Any]]:
    for index, result in enumerate(completed_step_results, start=1):
        prepared = result.preparation
        yield {
            "raw_ref": _raw_ref("agent-received", index),
            "raw_refs": [_raw_ref("agent-received", index)],
            "building_id": building_id,
            "step_ref": prepared.step_rows.step_ref,
            "agent_object_ref": prepared.agent_object.object_ref,
            "received_work_ref": _step_fact_ref("brick-work", index, prepared.step_rows.step_ref),
            "receipt_record_role": "received work observation only",
        }
    failed_index = len(completed_step_results) + 1
    yield {
        "raw_ref": _raw_ref("agent-received", failed_index),
        "raw_refs": [_raw_ref("agent-received", failed_index)],
        "building_id": building_id,
        "step_ref": failed_preparation.step_rows.step_ref,
        "agent_object_ref": failed_preparation.agent_object.object_ref,
        "received_work_ref": observation.received_work_ref,
        "receipt_record_role": "received work observation only",
        "adapter_error_ref": observation.adapter_error_ref,
    }


def _adapter_error_agent_receipt_claim_fact(
    prepared: AgentRunPreparationRecord,
    observation: Any,
    index: int,
    proof_limits: tuple[str, ...],
) -> Mapping[str, Any]:
    return _claim_fact(
        axis="Agent",
        fact_ref=_step_fact_ref("agent-receipt", index, prepared.step_rows.step_ref),
        raw_refs=[_raw_ref("agent-received", index)],
        proof_limits=proof_limits,
        not_proven=observation.not_proven,
        fact={
            "received_work_ref": observation.received_work_ref,
            "agent_object_ref": observation.agent_object_ref,
            "adapter_ref": observation.adapter_ref,
            "input_packet_ref": observation.input_packet_ref,
            "closed_agent_fact_absent": True,
            "returned_value_absent": True,
            "receipt_role": "Agent received declared work before adapter exception observation",
        },
    )
