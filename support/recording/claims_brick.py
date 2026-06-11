"""Brick crossing-family claim/raw emitters.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
Brick raw records + Brick claim facts (work contract + comparison) that
``support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern per-crossing-family emitter. Consumes the Brick backbone
(brick_work / brick_comparison) through the support contracts; authors no
Movement, target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.primitives import _raw_ref, _step_fact_ref
from brick_protocol.support.recording.claims_common import _claim_fact


def _brick_raw_records(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        records.append(
            {
                "raw_ref": _raw_ref("brick", index),
                "raw_refs": [_raw_ref("brick", index)],
                "building_id": building_id,
                "step_ref": prepared.step_rows.step_ref,
                "brick_instance_ref": prepared.brick_instance_ref,
                "work_statement": prepared.brick_work.work_statement,
                "comparison_rule": prepared.brick_work.comparison_rule,
                "required_return_shape": prepared.brick_work.required_return_shape,
                "source_facts": list(prepared.brick_work.source_facts),
            }
        )
    return tuple(records)


def _brick_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        facts.append(
            _claim_fact(
                axis="Brick",
                fact_ref=_step_fact_ref("brick-work", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("brick", index)],
                proof_limits=proof_limits,
                not_proven=result.not_proven,
                fact={
                    "brick_instance_ref": prepared.brick_instance_ref,
                    "work_statement": prepared.brick_work.work_statement,
                    "comparison_rule": prepared.brick_work.comparison_rule,
                    "required_return_shape": prepared.brick_work.required_return_shape,
                    "source_facts": list(prepared.brick_work.source_facts),
                },
            )
        )
        facts.append(
            _claim_fact(
                axis="Brick",
                fact_ref=_step_fact_ref("brick-comparison", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("brick", index), _raw_ref("agent", index)],
                proof_limits=proof_limits,
                not_proven=result.not_proven,
                fact={
                    "work_reference": prepared.brick_work.work_statement,
                    "comparison_rule": prepared.brick_work.comparison_rule,
                    "observed_match_kind": result.completion.brick_comparison.observed_match_kind,
                    "comparison_evidence": list(
                        result.completion.brick_comparison.comparison_evidence
                    ),
                    "required_return_shape_evidence": (
                        result.completion.brick_comparison.required_return_shape_evidence
                    ),
                    "forbidden_shortcut_evidence": list(
                        result.completion.brick_comparison.forbidden_shortcut_evidence
                    ),
                    "comparison_observation": "contract observation only; not success judgment",
                },
            )
        )
        facts.append(
            _claim_fact(
                axis="Brick",
                fact_ref=f"brick-comparison:{prepared.building_id}:{prepared.step_rows.step_ref}",
                raw_refs=[_raw_ref("brick", index), _raw_ref("agent", index)],
                proof_limits=proof_limits,
                not_proven=result.not_proven,
                fact={
                    "alias_for": _step_fact_ref("brick-comparison", index, prepared.step_rows.step_ref),
                    "work_reference": prepared.brick_work.work_statement,
                    "comparison_rule": prepared.brick_work.comparison_rule,
                    "observed_match_kind": result.completion.brick_comparison.observed_match_kind,
                    "comparison_evidence": list(
                        result.completion.brick_comparison.comparison_evidence
                    ),
                    "required_return_shape_evidence": (
                        result.completion.brick_comparison.required_return_shape_evidence
                    ),
                    "forbidden_shortcut_evidence": list(
                        result.completion.brick_comparison.forbidden_shortcut_evidence
                    ),
                    "comparison_observation": "contract observation only; not success judgment",
                },
            )
        )
    return facts


def _adapter_error_brick_raw_record(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    index: int,
) -> Mapping[str, Any]:
    return {
        "raw_ref": _raw_ref("brick", index),
        "raw_refs": [_raw_ref("brick", index)],
        "building_id": building_id,
        "step_ref": prepared.step_rows.step_ref,
        "brick_instance_ref": prepared.brick_instance_ref,
        "work_statement": prepared.brick_work.work_statement,
        "comparison_rule": prepared.brick_work.comparison_rule,
        "required_return_shape": prepared.brick_work.required_return_shape,
        "source_facts": list(prepared.brick_work.source_facts),
    }


def _adapter_error_brick_claim_fact(
    prepared: AgentRunPreparationRecord,
    index: int,
    proof_limits: tuple[str, ...],
) -> Mapping[str, Any]:
    return _claim_fact(
        axis="Brick",
        fact_ref=_step_fact_ref("brick-work", index, prepared.step_rows.step_ref),
        raw_refs=[_raw_ref("brick", index)],
        proof_limits=proof_limits,
        not_proven=prepared.not_proven,
        fact={
            "brick_instance_ref": prepared.brick_instance_ref,
            "work_statement": prepared.brick_work.work_statement,
            "comparison_rule": prepared.brick_work.comparison_rule,
            "required_return_shape": prepared.brick_work.required_return_shape,
            "source_facts": list(prepared.brick_work.source_facts),
        },
    )
