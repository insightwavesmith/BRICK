"""Per-axis claim-trace packet assembler.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
forward-path ``RawClaimTracePacket`` builder that
``support/operator/evidence_assembly.py`` previously hand-wrote sits here as the
single aggregator that pulls the per-crossing-family emitters (claims_brick /
claims_agent / claims_link / claims_carry_budget) into one packet. It owns no
crossing of its own; it composes the family emitters and is consumed by the two
forward-path writers (the accumulated-Building writer in the facade and the
adapter-error frontier writer). Authors no Movement, target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.recording.claims_agent import (
    _agent_claim_facts,
    _agent_output_text_raw_records,
    _agent_raw_records,
    _agent_received_raw_records,
)
from brick_protocol.support.recording.claims_brick import (
    _brick_claim_facts,
    _brick_raw_records,
)
from brick_protocol.support.recording.claims_carry_budget import (
    _link_carry_claim_facts,
)
from brick_protocol.support.recording.claims_link import (
    _link_gate_receipt_claim_facts,
    _link_movement_claim_facts,
    _link_policy_action_claim_facts,
    _link_raw_records,
    _link_sufficiency_claim_facts,
    _link_transfer_claim_facts,
)
from brick_protocol.support.recording.contracts import RawClaimTracePacket


def _raw_claim_trace_packet(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
) -> RawClaimTracePacket:
    return RawClaimTracePacket(
        brick_raw_records=_brick_raw_records(building_id, step_results),
        agent_raw_records=_agent_raw_records(building_id, step_results),
        link_raw_records=_link_raw_records(
            building_id,
            step_results,
            plan=plan,
            graph_context=graph_context,
        ),
        brick_claim_facts=tuple(_brick_claim_facts(step_results, proof_limits=proof_limits)),
        agent_claim_facts=tuple(_agent_claim_facts(step_results, proof_limits=proof_limits)),
        link_transfer_claim_facts=tuple(_link_transfer_claim_facts(step_results, proof_limits=proof_limits)),
        link_carry_claim_facts=tuple(
            _link_carry_claim_facts(
                building_id,
                step_results,
                plan=plan,
                proof_limits=proof_limits,
            )
        ),
        link_sufficiency_claim_facts=tuple(_link_sufficiency_claim_facts(step_results, proof_limits=proof_limits)),
        link_movement_claim_facts=tuple(
            _link_movement_claim_facts(
                step_results,
                plan=plan,
                proof_limits=proof_limits,
                graph_context=graph_context,
            )
        ),
        link_gate_receipt_claim_facts=tuple(
            _link_gate_receipt_claim_facts(step_results, proof_limits=proof_limits)
        ),
        link_policy_action_claim_facts=tuple(
            _link_policy_action_claim_facts(step_results, proof_limits=proof_limits)
        ),
        agent_output_text_raw_records=_agent_output_text_raw_records(building_id, step_results),
        agent_received_raw_records=_agent_received_raw_records(building_id, step_results),
    )
