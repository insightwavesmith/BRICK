"""Shared gate-sequence policy reader for Building walkers.

This support helper reads a caller/COO-declared Link ``gate_sequence_policy``,
evaluates Link-owned GateFact sufficiency through ``brick_protocol/link/gate.py``, and returns
a support-only disposition observation. It does not author Movement, targets,
routes, GateFacts, success, or quality.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from brick_protocol.link.gate import (
    ADMITTED_POLICY_ACTIONS,
    GateFact,
    evaluate_declared_movement_gate,
    normalize_gate_policy_action,
)
from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.plan_validation import (
    _artifact_grounding_required_return_fields,
)
from brick_protocol.support.operator.primitives import _optional_text_value


_ADMITTED_ACTIONS = frozenset(ADMITTED_POLICY_ACTIONS)


@dataclass(frozen=True)
class GatePolicyActionStep:
    """One gate's chosen policy action in a declared sequence (recording only).

    Captures the action support's loop control read at ONE processed gate, in
    declared order, so the per-gate judgment sequence (including the intermediate
    ``"next"`` proceed decisions) is recorded — not just the terminal action.
    The implicit all-``"next"`` fall-through forward is recorded with an empty
    ``gate_ref``. Records FACTS only; authors no Movement and judges nothing.
    """

    gate_ref: str
    action: str
    evidence_ref: str = ""
    reason_refs: tuple[str, ...] = field(default_factory=tuple)
    hold_reason: str = ""
    pending_target_ref: str = ""
    target_brick_ref: str = ""


@dataclass(frozen=True)
class GateSequenceDecision:
    """Support-only result of reading a declared gate sequence."""

    action: str = "none"
    gate_ref: str = ""
    target_brick_ref: str = ""
    pending_target_ref: str = ""
    required_disposition_owner: str = ""
    hold_reason: str = ""
    evidence_ref: str = ""
    reason_refs: tuple[str, ...] = field(default_factory=tuple)
    gate_results: tuple[tuple[str, GateFact], ...] = field(default_factory=tuple)
    gate_action_sequence: tuple[GatePolicyActionStep, ...] = field(default_factory=tuple)


def run_gate_sequence_policy(
    *,
    step: Mapping[str, Any],
    step_result: BuildingRunSupportResult,
    source_brick_ref: str,
    target_brick_ref: str,
) -> GateSequenceDecision:
    """Evaluate one declared Link row gate sequence in order."""

    link_row = _link_row_from_step(step)
    policy = link_row.get("gate_sequence_policy")
    if not isinstance(policy, list) or not policy:
        return GateSequenceDecision()

    comparison = step_result.completion.brick_comparison
    checked = f"brick-comparison:{step_result.building_id}:{step_result.preparation.step_rows.step_ref}"
    gate_results = _declared_sequence_gate_results(
        policy=policy,
        base_required_return_fields=_base_required_return_fields_for_gate_sequence(comparison),
        missing_return_fields=comparison.missing_return_fields(),
        observed_match_kind=comparison.observed_match_kind,
        human_review_present=_link_row_has_non_empty_list(
            link_row,
            ("route_decision_basis", "human_review_refs"),
        ),
        override_present=_link_row_has_non_empty_list(
            link_row,
            ("route_decision_basis", "override_refs"),
        ),
        checked_public_fact=checked,
        evidence_reference=checked,
    )
    gate_result_by_ref = {gate_ref: gate_fact for gate_ref, gate_fact in gate_results}
    # RECORDING ONLY: accumulate every processed gate's chosen action (including
    # intermediate "next") so the per-gate judgment sequence is complete. Flow
    # control below is unchanged — it still reads decision.action/etc exactly as
    # before; this list never influences which branch is taken.
    action_steps: list[GatePolicyActionStep] = []
    for raw_step in policy:
        if not isinstance(raw_step, Mapping):
            continue
        gate_ref = _optional_text_value(raw_step.get("gate_ref")) or ""
        gate_fact = gate_result_by_ref.get(gate_ref)
        if gate_fact is None:
            continue
        missing = bool(gate_fact.missing_required_facts)
        action_row = raw_step.get(
            "on_missing_required_facts" if missing else "on_sufficient"
        )
        if not isinstance(action_row, Mapping):
            continue
        action = _action_literal(action_row.get("action"))
        if action not in _ADMITTED_ACTIONS:
            evidence_ref = _gate_sequence_evidence_ref(
                step_result,
                gate_ref=gate_ref,
                action="unadmitted-action",
            )
            reason_refs = _reason_refs(action_row, fallback=evidence_ref)
            hold_reason = f"gate_sequence_unadmitted_action:{gate_ref}"
            action_steps.append(
                GatePolicyActionStep(
                    gate_ref=gate_ref,
                    action="hold",
                    evidence_ref=evidence_ref,
                    reason_refs=reason_refs,
                    hold_reason=hold_reason,
                    pending_target_ref=target_brick_ref,
                )
            )
            return GateSequenceDecision(
                action="hold",
                gate_ref=gate_ref,
                pending_target_ref=target_brick_ref,
                required_disposition_owner="caller-or-coo",
                hold_reason=hold_reason,
                evidence_ref=evidence_ref,
                reason_refs=reason_refs,
                gate_results=gate_results,
                gate_action_sequence=tuple(action_steps),
            )
        evidence_ref = _gate_sequence_evidence_ref(
            step_result,
            gate_ref=gate_ref,
            action=action,
        )
        reason_refs = _reason_refs(action_row, fallback=evidence_ref)
        if action == "next":
            action_steps.append(
                GatePolicyActionStep(
                    gate_ref=gate_ref,
                    action="next",
                    evidence_ref=evidence_ref,
                    reason_refs=reason_refs,
                )
            )
            continue
        if action == "forward":
            action_steps.append(
                GatePolicyActionStep(
                    gate_ref=gate_ref,
                    action="forward",
                    evidence_ref=evidence_ref,
                    reason_refs=reason_refs,
                )
            )
            return GateSequenceDecision(
                action="forward",
                gate_ref=gate_ref,
                evidence_ref=evidence_ref,
                reason_refs=reason_refs,
                gate_results=gate_results,
                gate_action_sequence=tuple(action_steps),
            )
        if action == "hold":
            pending_target_ref = _target_ref(
                action_row,
                source_brick_ref=source_brick_ref,
                target_brick_ref=target_brick_ref,
                basis_key="pending_target_basis",
                ref_key="pending_target_ref",
                default_basis="target_brick",
            )
            hold_reason = f"gate_sequence_missing_required_facts:{gate_ref}"
            action_steps.append(
                GatePolicyActionStep(
                    gate_ref=gate_ref,
                    action="hold",
                    evidence_ref=evidence_ref,
                    reason_refs=reason_refs,
                    hold_reason=hold_reason,
                    pending_target_ref=pending_target_ref,
                )
            )
            return GateSequenceDecision(
                action="hold",
                gate_ref=gate_ref,
                pending_target_ref=pending_target_ref,
                required_disposition_owner=(
                    _optional_text_value(action_row.get("required_disposition_owner"))
                    or "caller-or-coo"
                ),
                hold_reason=hold_reason,
                evidence_ref=evidence_ref,
                reason_refs=reason_refs,
                gate_results=gate_results,
                gate_action_sequence=tuple(action_steps),
            )
        if action == "reroute":
            target_brick_ref_chosen = _target_ref(
                action_row,
                source_brick_ref=source_brick_ref,
                target_brick_ref=target_brick_ref,
                basis_key="target_basis",
                ref_key="target_ref",
            )
            hold_reason = f"gate_sequence_missing_required_facts:{gate_ref}"
            action_steps.append(
                GatePolicyActionStep(
                    gate_ref=gate_ref,
                    action="reroute",
                    evidence_ref=evidence_ref,
                    reason_refs=reason_refs,
                    hold_reason=hold_reason,
                    target_brick_ref=target_brick_ref_chosen,
                )
            )
            return GateSequenceDecision(
                action="reroute",
                gate_ref=gate_ref,
                target_brick_ref=target_brick_ref_chosen,
                hold_reason=hold_reason,
                evidence_ref=evidence_ref,
                reason_refs=reason_refs,
                gate_results=gate_results,
                gate_action_sequence=tuple(action_steps),
            )
    # All processed gates said "next": record the implicit forward (empty gate_ref).
    action_steps.append(GatePolicyActionStep(gate_ref="", action="forward"))
    return GateSequenceDecision(
        action="forward",
        gate_results=gate_results,
        gate_action_sequence=tuple(action_steps),
    )


def _base_required_return_fields_for_gate_sequence(comparison: Any) -> tuple[str, ...]:
    return _artifact_grounding_required_return_fields(
        comparison.required_return_shape_evidence,
        comparison.required_return_fields(),
    )


def gate_sequence_decision_to_record(
    decision: "GateSequenceDecision | None",
) -> dict | None:
    """Project a live gate-sequence decision to a JSON-safe record (or None).

    U5.5 RESUME-GATE-RECORD. Returns None when there is no policy (decision is
    None or ``decision.action == "none"``) so a no-policy step's step-output.json
    stays byte-stable. Otherwise returns a flat JSON-safe dict capturing
    EVERYTHING the claim-trace seam (``claims_link._link_gate_receipt_claim_facts``
    + ``_link_policy_action_claim_facts``) rebuilds the gate facts from: the
    decision header, the per-gate GateFact receipts, and the per-gate action
    sequence. Records FACTS only; authors no Movement and judges nothing.
    """

    if decision is None or decision.action == "none":
        return None
    return {
        "action": decision.action,
        "gate_ref": decision.gate_ref,
        "target_brick_ref": decision.target_brick_ref,
        "pending_target_ref": decision.pending_target_ref,
        "required_disposition_owner": decision.required_disposition_owner,
        "hold_reason": decision.hold_reason,
        "evidence_ref": decision.evidence_ref,
        "reason_refs": list(decision.reason_refs),
        "gate_results": [
            {
                "gate_ref": gate_ref,
                "sufficiency": gate_fact.sufficiency,
                "checked_public_fact": gate_fact.checked_public_fact,
                "required_public_facts": list(gate_fact.required_public_facts),
                "missing_required_facts": list(gate_fact.missing_required_facts),
            }
            for gate_ref, gate_fact in decision.gate_results
        ],
        "gate_action_sequence": [
            {
                "gate_ref": action_step.gate_ref,
                "action": action_step.action,
                "evidence_ref": action_step.evidence_ref,
                "reason_refs": list(action_step.reason_refs),
                "hold_reason": action_step.hold_reason,
                "pending_target_ref": action_step.pending_target_ref,
                "target_brick_ref": action_step.target_brick_ref,
            }
            for action_step in decision.gate_action_sequence
        ],
    }


def gate_sequence_decision_from_record(
    record: Mapping[str, Any],
) -> GateSequenceDecision:
    """Reconstruct a GateSequenceDecision from a recorded gate-sequence record.

    U5.5 RESUME-GATE-RECORD. The inverse of ``gate_sequence_decision_to_record``.
    It READS the recorded AT-TIME decision back (the resume path NEVER recomputes a
    replayed step's gate decision). The reconstructed decision round-trips: the
    claim-trace seam produces the SAME gate-receipt + policy-action facts from it
    as from the original. FAIL-CLOSED: a malformed record (missing required keys
    or wrong types) raises a clear error rather than producing a half decision.

    Reconstructed GateFacts use ``stage="movement"`` — the gate-receipt claim body
    reads only sufficiency / checked_public_fact / required_public_facts /
    missing_required_facts (never stage), and the live gate-sequence gate facts are
    always movement-stage, so the receipt facts are byte-identical.
    """

    if not isinstance(record, Mapping):
        raise TypeError("gate_sequence_decision_record must be a mapping")
    action = _record_policy_action(record, "action", required=True)
    # FAIL-CLOSED on a PARTIAL record: gate_sequence_decision_to_record ALWAYS emits
    # gate_results + gate_action_sequence (possibly empty lists) for a non-"none"
    # decision. A record with only the action header but missing either list is
    # malformed/corrupt — raise rather than silently reconstruct a DEGRADED decision
    # (which would drop the resumed step's gate facts without a flag).
    for _required_key in ("gate_results", "gate_action_sequence"):
        if _required_key not in record:
            raise ValueError(
                f"gate_sequence_decision_record missing required key {_required_key!r}"
            )
    gate_results: list[tuple[str, GateFact]] = []
    for raw in _record_list(record, "gate_results"):
        if not isinstance(raw, Mapping):
            raise ValueError("gate_results entry must be a mapping")
        gate_results.append(
            (
                _record_text(raw, "gate_ref", required=True),
                GateFact(
                    stage="movement",
                    sufficiency=_record_text(raw, "sufficiency", required=True),
                    checked_public_fact=_record_text(raw, "checked_public_fact"),
                    required_public_facts=_record_text_tuple(
                        raw, "required_public_facts"
                    ),
                    missing_required_facts=_record_text_tuple(
                        raw, "missing_required_facts"
                    ),
                ),
            )
        )
    action_sequence: list[GatePolicyActionStep] = []
    for raw in _record_list(record, "gate_action_sequence"):
        if not isinstance(raw, Mapping):
            raise ValueError("gate_action_sequence entry must be a mapping")
        action_sequence.append(
            GatePolicyActionStep(
                gate_ref=_record_text(raw, "gate_ref"),
                action=_record_policy_action(raw, "action", required=True),
                evidence_ref=_record_text(raw, "evidence_ref"),
                reason_refs=_record_text_tuple(raw, "reason_refs"),
                hold_reason=_record_text(raw, "hold_reason"),
                pending_target_ref=_record_text(raw, "pending_target_ref"),
                target_brick_ref=_record_text(raw, "target_brick_ref"),
            )
        )
    return GateSequenceDecision(
        action=action,
        gate_ref=_record_text(record, "gate_ref"),
        target_brick_ref=_record_text(record, "target_brick_ref"),
        pending_target_ref=_record_text(record, "pending_target_ref"),
        required_disposition_owner=_record_text(record, "required_disposition_owner"),
        hold_reason=_record_text(record, "hold_reason"),
        evidence_ref=_record_text(record, "evidence_ref"),
        reason_refs=_record_text_tuple(record, "reason_refs"),
        gate_results=tuple(gate_results),
        gate_action_sequence=tuple(action_sequence),
    )


def _record_text(record: Mapping[str, Any], key: str, *, required: bool = False) -> str:
    value = record.get(key)
    if value is None:
        if required:
            raise ValueError(f"gate_sequence_decision_record missing required key {key!r}")
        return ""
    if not isinstance(value, str):
        raise TypeError(f"gate_sequence_decision_record[{key!r}] must be text")
    if required and not value.strip():
        raise ValueError(f"gate_sequence_decision_record[{key!r}] must not be blank")
    return value


def _record_policy_action(
    record: Mapping[str, Any],
    key: str,
    *,
    required: bool = False,
) -> str:
    action = _record_text(record, key, required=required)
    if action and action not in _ADMITTED_ACTIONS:
        raise ValueError(
            f"gate_sequence_decision_record[{key!r}] action {action!r} is not admitted"
        )
    return action


def _record_list(record: Mapping[str, Any], key: str) -> list[Any]:
    value = record.get(key)
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"gate_sequence_decision_record[{key!r}] must be a list")
    return list(value)


def _record_text_tuple(record: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = record.get(key)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"gate_sequence_decision_record[{key!r}] must be a list of text")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(
                f"gate_sequence_decision_record[{key!r}][{index}] must be text"
            )
        items.append(item)
    return tuple(items)


def _declared_sequence_gate_results(
    *,
    policy: Sequence[Any],
    base_required_return_fields: Sequence[str],
    missing_return_fields: Sequence[str],
    observed_match_kind: str,
    human_review_present: bool,
    override_present: bool,
    checked_public_fact: str,
    evidence_reference: str,
) -> tuple[tuple[str, GateFact], ...]:
    results: list[tuple[str, GateFact]] = []
    for raw_step in policy:
        if not isinstance(raw_step, Mapping):
            continue
        gate_ref = _optional_text_value(raw_step.get("gate_ref")) or ""
        if not gate_ref:
            continue
        gate_fact = evaluate_declared_movement_gate(
            gate_refs=(gate_ref,),
            required_return_fields=(),
            missing_return_fields=missing_return_fields,
            observed_match_kind=observed_match_kind,
            human_review_present=human_review_present,
            override_present=override_present,
            base_required_return_fields=base_required_return_fields,
            checked_public_fact=checked_public_fact,
            evidence_reference=evidence_reference,
        )
        if gate_fact is not None:
            results.append((gate_ref, gate_fact))
    return tuple(results)


def _link_row_from_step(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Link":
            return row
    return {}


def _link_row_has_non_empty_list(
    link_row: Mapping[str, Any],
    path: tuple[str, str],
) -> bool:
    outer = link_row.get(path[0])
    if not isinstance(outer, Mapping):
        return False
    value = outer.get(path[1])
    return isinstance(value, list) and any(
        isinstance(item, str) and item.strip() for item in value
    )


def _action_literal(value: Any) -> str:
    text = _optional_text_value(value) or ""
    if not text:
        return ""
    return normalize_gate_policy_action(text)


def _target_ref(
    action_row: Mapping[str, Any],
    *,
    source_brick_ref: str,
    target_brick_ref: str,
    basis_key: str,
    ref_key: str,
    default_basis: str = "",
) -> str:
    explicit = _optional_text_value(action_row.get(ref_key))
    if explicit:
        return explicit
    basis = _optional_text_value(action_row.get(basis_key)) or default_basis
    if basis == "source_brick":
        return source_brick_ref
    if basis == "target_brick":
        return target_brick_ref
    return ""


def _reason_refs(
    action_row: Mapping[str, Any],
    *,
    fallback: str,
) -> tuple[str, ...]:
    raw = action_row.get("reason_refs")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        refs = tuple(str(item).strip() for item in raw if str(item).strip())
        if refs:
            return refs
    return (fallback,)


def _gate_sequence_evidence_ref(
    step_result: BuildingRunSupportResult,
    *,
    gate_ref: str,
    action: str,
) -> str:
    step_ref = step_result.preparation.step_rows.step_ref
    safe_gate = gate_ref.replace(":", "-")
    safe_action = action.replace(":", "-")
    return f"observation:gate-sequence-{step_result.building_id}-{step_ref}-{safe_gate}-{safe_action}"


__all__ = [
    "ADMITTED_POLICY_ACTIONS",
    "GatePolicyActionStep",
    "GateSequenceDecision",
    "gate_sequence_decision_from_record",
    "gate_sequence_decision_to_record",
    "run_gate_sequence_policy",
]
