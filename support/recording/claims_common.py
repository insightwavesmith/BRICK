"""Shared leaf primitives for the per-crossing-family claim/raw emitters.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B):
``support/operator/evidence_assembly.py`` was a god-module that hand-assembled
the raw records + claim facts for every axis crossing. Its per-family emitters
were lifted into ``support/recording/claims_*.py`` collaborators behind a thin
writer facade. This module holds the cross-family LEAF primitives those emitters
share -- the canonical claim-fact envelope, the manifest not-proven normaliser,
and the per-step output observation builders. It depends on NO claim family
(it sits at the bottom of the emitter import DAG) so the family modules import
it without a cycle.

Support recording shape only: NESTED evidence; it authors no Movement, no
target, no success/quality judgment, and admits no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.gate_sequence import gate_sequence_decision_to_record
from brick_protocol.support.operator.primitives import (
    _DEFAULT_NOT_PROVEN,
    _raw_ref,
    _resource_slug,
    _step_fact_ref,
    _text_tuple,
)
from brick_protocol.support.recording.contracts import StepOutputObservation
from brick_protocol.support.recording.step_outputs import (
    _step_output_manifest_ref,
    step_output_manifest_refs,
)


def _claim_fact(
    *,
    axis: str,
    fact_ref: str,
    raw_refs: list[str],
    proof_limits: tuple[str, ...],
    not_proven: Iterable[str] | str | None,
    fact: dict[str, Any] | Any,
) -> dict[str, Any]:
    return {
        "axis": axis,
        "fact_ref": fact_ref,
        "raw_refs": raw_refs,
        "proof_limits": list(proof_limits),
        "not_proven": list(_text_tuple("not_proven", not_proven or _DEFAULT_NOT_PROVEN)),
        "fact": dict(fact),
    }


def _manifest_not_proven(values: Iterable[str] | str | None) -> tuple[str, ...]:
    exact_authority_claims = {
        "source truth",
        "success judgment",
        "quality judgment",
        "movement authority",
    }
    adjusted: list[str] = []
    for value in _text_tuple("not_proven", values):
        lowered = value.strip().lower()
        if lowered in exact_authority_claims:
            adjusted.append(f"not proven: {value}")
        else:
            adjusted.append(value)
    return tuple(adjusted)


def _step_output_observations(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    task_source_ref: str | None = None,
) -> tuple[StepOutputObservation, ...]:
    observations: list[StepOutputObservation] = []
    for index, result in enumerate(step_results, start=1):
        step_ref = result.preparation.step_rows.step_ref
        observations.append(
            StepOutputObservation(
                building_id=building_id,
                step_ref=step_ref,
                brick_instance_ref=result.preparation.brick_instance_ref,
                agent_object_ref=result.preparation.agent_object.object_ref,
                returned=result.adapter_result.returned_value,
                received_work_ref=_step_fact_ref("brick-work", index, step_ref),
                returned_fact_ref=_step_fact_ref("agent-fact", index, step_ref),
                raw_ref=_raw_ref("agent", index),
                task_source_ref=task_source_ref or "",
                not_proven=result.not_proven,
                recorded_at=result.recorded_at,
                gate_sequence_decision_record=gate_sequence_decision_to_record(
                    result.gate_sequence_decision
                ),
            )
        )
    return tuple(observations)


def _step_output_manifest_refs(
    step_results: tuple[BuildingRunSupportResult, ...],
) -> list[str]:
    return step_output_manifest_refs(_step_output_observations("", step_results))


def _step_result_attempts(
    step_results: tuple[BuildingRunSupportResult, ...],
) -> tuple[int, ...]:
    counts: dict[str, int] = {}
    attempts: list[int] = []
    for result in step_results:
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        attempts.append(counts[step_ref])
    return tuple(attempts)


def _dynamic_reroute_records(evidence: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = evidence.get("reroute_adoption_records", [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _step_output_adapter_error_ref(step_ref: str, attempt_index: int) -> str:
    slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    return f"work/step-outputs/{slug}-attempt-{attempt_index}/adapter-error.json"


def _adapter_error_attempt_from_ref(adapter_error_ref: str) -> int:
    parts = adapter_error_ref.rsplit(":attempt-", 1)
    if len(parts) == 2:
        try:
            return int(parts[1])
        except ValueError:
            pass
    return 1


# Re-exported so building_map_emit can reach the per-step manifest ref builder
# through the shared claims base (single import surface for the emitters).
__all__ = [
    "_claim_fact",
    "_manifest_not_proven",
    "_step_output_observations",
    "_step_output_manifest_refs",
    "_step_output_manifest_ref",
    "_step_result_attempts",
    "_dynamic_reroute_records",
    "_step_output_adapter_error_ref",
    "_adapter_error_attempt_from_ref",
]
