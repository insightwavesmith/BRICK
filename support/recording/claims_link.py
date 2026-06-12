"""Link crossing-family claim/raw emitters.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
Link transfer / movement / sufficiency / absence facts, the graph-edge Link raw
records + movement claim facts, the gate/transfer/carry claim bodies, the
declared-step Link raw row, the session-scope close fields, and the
transition-lifecycle support-evidence fields that
``support/operator/evidence_assembly.py`` previously hand-wrote were lifted here
as a single-concern per-crossing-family emitter.

This is the one emitter that reaches an axis-internal symbol: it imports the
canonical ``GateFact`` contract from ``link/gate.py`` (the link_gate crossing)
to read a caller-supplied GateFact's public fields into the sufficiency claim
body. It crosses ONLY via that canonical contract (elegance guard G3) and reads
every Link movement/route/transition projection through the support
plan_validation / plan_graph helpers. Authors no Movement, target, or judgment.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.link.gate import GATE_SUFFICIENCY_LITERALS, GateFact
from brick_protocol.support.operator.contracts import (
    AgentRunPreparationRecord,
    BuildingRunSupportResult,
    MinimalCrossingRecord,
)
from brick_protocol.support.operator.gate_sequence import ADMITTED_POLICY_ACTIONS
from brick_protocol.support.operator.plan_graph import (
    _graph_declared_edges,
    _graph_link_raw_ref,
    _graph_movement_fact_ref,
)
from brick_protocol.support.operator.plan_validation import (
    _building_lifecycle_evidence_fields,
    _building_lifecycle_state,
    _declared_gate_evidence_fields,
    _declared_movement_and_target,
    _movement_and_target_from_link_row,
    _route_decision_basis_evidence_fields,
    _route_replay_evidence_fields,
    _route_replay_plan_from_link_row,
    _transition_authoring_evidence_fields,
    _transition_authoring_from_link_row,
    _transition_lifecycle_evidence_fields,
)
from brick_protocol.support.operator.primitives import (
    _DEFAULT_NOT_PROVEN,
    _mapping,
    _merge_texts,
    _optional_text_or_none,
    _raw_ref,
    _required_text,
    _resource_slug,
    _step_fact_ref,
    _text_tuple,
)
from brick_protocol.support.recording.claims_common import (
    _claim_fact,
    _dynamic_reroute_records,
)

_TRANSITION_LIFECYCLE_CARRY_BUDGET_EVIDENCE_FIELD = (
    "transition_lifecycle_carry_budget_evidence_ref"
)
_RETURNED_FIELD_PUBLIC_FACT_PREFIX = (
    "BrickComparisonFact.comparison_evidence.returned_field."
)
_REPOSITORY_ARTIFACT_REF_SUFFIX = ".repository_artifact_ref"


def _graph_link_raw_records(
    building_id: str,
    graph_context: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for index, edge in enumerate(_graph_declared_edges(graph_context), start=1):
        edge_ref = _required_text("declared_edges.edge_ref", edge.get("edge_ref"))
        link_row = _mapping("declared_edges.link_row", edge.get("link_row"))
        movement, target = _movement_and_target_from_link_row(link_row)
        record = {
            "raw_ref": _graph_link_raw_ref(index, edge_ref),
            "raw_refs": [_graph_link_raw_ref(index, edge_ref)],
            "building_id": building_id,
            "edge_ref": edge_ref,
            "source_step_ref": edge.get("source_step_ref"),
            "target_step_ref": edge.get("target_step_ref"),
            "source_brick_instance_ref": edge.get("source_brick_instance_ref"),
            "target_brick_instance_ref": edge.get("target_brick_instance_ref"),
            "movement": movement,
            "movement_source": "declared graph Building Plan Link edge",
            "target": target,
            "declared_graph_edge": True,
            "is_completion_edge": bool(edge.get("is_completion_edge")),
        }
        record.update(_route_replay_evidence_fields(link_row))
        records.append(record)
    return tuple(records)


def _graph_link_movement_claim_facts(
    graph_context: Mapping[str, Any] | None,
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, edge in enumerate(_graph_declared_edges(graph_context), start=1):
        edge_ref = _required_text("declared_edges.edge_ref", edge.get("edge_ref"))
        link_row = _mapping("declared_edges.link_row", edge.get("link_row"))
        movement, target = _movement_and_target_from_link_row(link_row)
        fact_body = {
            "movement": movement,
            "movement_source": "declared graph Building Plan Link edge",
            "source_brick_instance_ref": edge.get("source_brick_instance_ref"),
            "target_boundary_ref": target,
            "link_edge_ref": edge_ref,
            "is_completion_edge": bool(edge.get("is_completion_edge")),
        }
        fact_body.update(_route_replay_evidence_fields(link_row))
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=_graph_movement_fact_ref(edge_ref),
                raw_refs=[_graph_link_raw_ref(index, edge_ref)],
                proof_limits=proof_limits,
                not_proven=edge.get("not_proven") or _DEFAULT_NOT_PROVEN,
                fact=fact_body,
            )
        )
    return facts


def _link_raw_records(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        movement = result.completion.crossing_record.link_fact.movement
        record = {
            "raw_ref": _raw_ref("link", index),
            "raw_refs": [_raw_ref("link", index)],
            "building_id": building_id,
            "step_ref": prepared.step_rows.step_ref,
            "source_brick_instance_ref": prepared.brick_instance_ref,
            "target_brick_instance_ref": prepared.next_brick_instance_ref,
            "movement": movement,
            "movement_source": "caller-declared Building Plan Link row",
            "target": _declared_movement_and_target({"rows": list(prepared.step_rows.brick_row and [prepared.step_rows.brick_row, prepared.step_rows.agent_row, prepared.step_rows.link_row])})[1],
        }
        record.update(_route_replay_evidence_fields(prepared.step_rows.link_row))
        record.update(_declared_gate_evidence_fields(prepared.step_rows.link_row))
        record.update(_route_decision_basis_evidence_fields(prepared.step_rows.link_row))
        record.update(_transition_authoring_evidence_fields(prepared.step_rows.link_row))
        record.update(_transition_lifecycle_evidence_fields(prepared.step_rows.link_row))
        record.update(
            _transition_lifecycle_support_evidence_fields(
                step_ref=prepared.step_rows.step_ref,
                link_row=prepared.step_rows.link_row,
                plan=plan,
            )
        )
        record.update(_building_lifecycle_evidence_fields(prepared.step_rows.link_row))
        record.update(_session_scope_close_fields(result))
        records.append(record)
    records.extend(_graph_link_raw_records(building_id, graph_context))
    return tuple(records)


def _link_transfer_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        transfer_fact = result.completion.crossing_record.transfer_fact
        if transfer_fact is None:
            facts.append(
                _link_absence_claim_fact(
                    absent_fact_type="TransferFact",
                    absence_ref_kind="link-transfer",
                    statement=(
                        "caller did not supply a Link TransferFact; "
                        "support/operator/run.py did not create one"
                    ),
                    index=index,
                    step_ref=prepared.step_rows.step_ref,
                    raw_refs=[_raw_ref("link", index)],
                    proof_limits=proof_limits,
                    not_proven=result.not_proven,
                )
            )
            continue
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=_step_fact_ref("transfer-fact", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("link", index)],
                proof_limits=proof_limits,
                not_proven=_merge_texts(result.not_proven, transfer_fact.not_proven),
                fact=_transfer_fact_claim_body(transfer_fact),
            )
        )
    return facts


def _link_sufficiency_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        gate_facts = _gate_claim_items(result.completion.crossing_record)
        if not gate_facts:
            facts.append(
                _link_absence_claim_fact(
                    absent_fact_type="GateFact",
                    absence_ref_kind="link-gate-sufficiency",
                    statement=(
                        "caller did not supply a Link Gate/sufficiency fact; "
                        "support/operator/run.py did not create one"
                    ),
                    index=index,
                    step_ref=prepared.step_rows.step_ref,
                    raw_refs=[_raw_ref("link", index)],
                    proof_limits=proof_limits,
                    not_proven=result.not_proven,
                )
            )
            continue
        for stage, gate_fact in gate_facts:
            facts.append(
                _claim_fact(
                    axis="Link",
                    fact_ref=_gate_claim_fact_ref(stage, index, prepared.step_rows.step_ref),
                    raw_refs=[_raw_ref("link", index)],
                    proof_limits=proof_limits,
                    not_proven=result.not_proven,
                    fact=_gate_fact_claim_body(gate_fact),
                )
            )
    return facts


def _link_gate_receipt_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    """E1 (U5.5 slice-3): the live gate-sequence GateFact receipt, per gate.

    For each step whose run.py gate_sequence_decision carries gate_results, emit
    ONE fact per evaluated gate (in declared sequence order) recording the Link
    GateFact sufficiency that loop control read at the time. A step with no
    decision or empty gate_results contributes NOTHING here (the no-gate case is
    already covered by the sufficiency ABSENCE variant; no absence is invented).
    Support recording shape only: it records FACTS (gate sufficiency + the public
    fact sets); it authors no Movement and judges no success/quality.
    """

    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        decision = result.gate_sequence_decision
        if decision is None or not decision.gate_results:
            continue
        step_ref = result.preparation.step_rows.step_ref
        for ordinal, (gate_ref, gate_fact) in enumerate(decision.gate_results, start=1):
            facts.append(
                _claim_fact(
                    axis="Link",
                    fact_ref=_step_fact_ref(
                        f"gate-receipt-fact-{ordinal}", index, step_ref
                    ),
                    raw_refs=[_raw_ref("link", index)],
                    proof_limits=proof_limits,
                    not_proven=result.not_proven,
                    fact=_gate_receipt_claim_body(gate_ref, ordinal, gate_fact),
                )
            )
    return facts


def _gate_receipt_claim_body(
    gate_ref: str,
    ordinal: int,
    gate_fact: GateFact,
) -> Mapping[str, Any]:
    sufficiency = gate_fact.sufficiency
    if sufficiency not in GATE_SUFFICIENCY_LITERALS:
        raise ValueError(
            f"gate-receipt sufficiency {sufficiency!r} is not one of "
            f"{GATE_SUFFICIENCY_LITERALS!r}"
        )
    return {
        "gate_ref": gate_ref,
        "ordinal": ordinal,
        "sufficiency": sufficiency,
        "checked_public_fact": gate_fact.checked_public_fact,
        "required_public_facts": _resolvable_required_public_facts(gate_fact),
        "missing_required_facts": list(gate_fact.missing_required_facts),
    }


def _link_policy_action_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    """E1 (U5.5 slice-3): the gate-sequence policy action(s), per step.

    For each step whose run.py gate_sequence_decision carries an admitted action
    (anything other than the no-policy ``"none"``), emit ONE fact PER gate in the
    decision's ``gate_action_sequence`` IN ORDER — including the intermediate
    ``"next"`` proceed decisions — each with an ORDINAL fact_ref
    ``policy-action-fact-{ordinal}`` (ordinal from 1, like gate-receipt-fact-N).
    FALLBACK: a decision built WITHOUT the sequence (empty ``gate_action_sequence``
    but action != ``"none"``) emits the single legacy ``policy-action-fact`` so
    nothing regresses. A step with no decision or action ``"none"`` contributes
    NOTHING. Support recording shape only: it records the action support OBSERVED
    loop control take; it authors no Movement and judges no success/quality.
    """

    policy_action_proof_limits = proof_limits + (
        "records each gate's action in the declared sequence, "
        "including intermediate next decisions",
    )
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        decision = result.gate_sequence_decision
        if decision is None or decision.action == "none":
            continue
        step_ref = result.preparation.step_rows.step_ref
        action_sequence = getattr(decision, "gate_action_sequence", ()) or ()
        if action_sequence:
            for ordinal, action_step in enumerate(action_sequence, start=1):
                facts.append(
                    _claim_fact(
                        axis="Link",
                        fact_ref=_step_fact_ref(
                            f"policy-action-fact-{ordinal}", index, step_ref
                        ),
                        raw_refs=[_raw_ref("link", index)],
                        proof_limits=policy_action_proof_limits,
                        not_proven=result.not_proven,
                        fact=_policy_action_claim_body(action_step),
                    )
                )
            continue
        # FALLBACK: a decision built without the sequence (legacy single fact).
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=_step_fact_ref("policy-action-fact", index, step_ref),
                raw_refs=[_raw_ref("link", index)],
                proof_limits=policy_action_proof_limits,
                not_proven=result.not_proven,
                fact=_policy_action_claim_body(decision),
            )
        )
    return facts


def _policy_action_claim_body(source: Any) -> Mapping[str, Any]:
    """The policy_action fact body from a GatePolicyActionStep OR a decision.

    Both carry the same public fields (action, hold_reason, reason_refs,
    pending_target_ref, target_brick_ref); a GatePolicyActionStep uses
    ``.action`` while a legacy decision uses ``.action`` too, so this reads the
    shared shape from either. Validates the action against ADMITTED_POLICY_ACTIONS.
    """

    action = source.action
    if action not in ADMITTED_POLICY_ACTIONS:
        raise ValueError(
            f"policy_action {action!r} is not one of {ADMITTED_POLICY_ACTIONS!r}"
        )
    return {
        "policy_action": action,
        "action_reason": getattr(source, "hold_reason", "") or "",
        "reason_refs": list(source.reason_refs),
        "pending_target_ref": getattr(source, "pending_target_ref", "") or "",
        "target_brick_ref": getattr(source, "target_brick_ref", "") or "",
    }


def _link_absence_claim_fact(
    *,
    absent_fact_type: str,
    absence_ref_kind: str,
    statement: str,
    index: int,
    step_ref: str,
    raw_refs: list[str],
    proof_limits: tuple[str, ...],
    not_proven: Iterable[str] | str | None,
) -> Mapping[str, Any]:
    return _claim_fact(
        axis="Link",
        fact_ref=_step_absence_ref(absence_ref_kind, index, step_ref),
        raw_refs=raw_refs,
        proof_limits=proof_limits,
        not_proven=not_proven,
        fact={
            "trace_role": "absence_placeholder",
            "absent_fact_type": absent_fact_type,
            "caller_supplied": False,
            "support_created_bal_fact": False,
            "statement": statement,
        },
    )


def _transfer_fact_claim_body(transfer_fact: Any) -> Mapping[str, Any]:
    return {
        "caller_supplied": True,
        "source_boundary_ref": transfer_fact.source_boundary_ref,
        "target_boundary_ref": transfer_fact.target_boundary_ref,
        "public_fact_refs": list(transfer_fact.public_fact_refs),
        "work_context_ref": transfer_fact.work_context_ref,
        "required_public_facts": list(transfer_fact.required_public_facts),
        "transfer_gate_reference": transfer_fact.transfer_gate_reference,
        "proof_limits": list(transfer_fact.proof_limits),
        "not_proven": list(transfer_fact.not_proven),
        "evidence_reference": transfer_fact.evidence_reference,
    }


def _carry_fact_claim_body(carry_fact: Any) -> Mapping[str, Any]:
    return {
        "caller_supplied": True,
        "carried_fact_refs": list(carry_fact.carried_fact_refs),
        "source_owner_axis": carry_fact.source_owner_axis,
        "target_boundary_ref": carry_fact.target_boundary_ref,
        "carry_gate_reference": carry_fact.carry_gate_reference,
        "proof_limits": list(carry_fact.proof_limits),
        "not_proven": list(carry_fact.not_proven),
        "evidence_reference": carry_fact.evidence_reference,
    }


def _gate_fact_claim_body(gate_fact: GateFact) -> Mapping[str, Any]:
    return {
        "caller_or_declared": True,
        "stage": gate_fact.stage,
        "sufficiency": gate_fact.sufficiency,
        "checked_public_fact": gate_fact.checked_public_fact,
        "required_public_facts": _resolvable_required_public_facts(gate_fact),
        "missing_required_facts": list(gate_fact.missing_required_facts),
        "reason": gate_fact.reason,
        "evidence_reference": gate_fact.evidence_reference,
    }


def _resolvable_required_public_facts(gate_fact: GateFact) -> list[str]:
    missing = set(gate_fact.missing_required_facts)
    return [
        public_fact
        for public_fact in gate_fact.required_public_facts
        if not _is_missing_repository_artifact_selector(public_fact, missing)
    ]


def _is_missing_repository_artifact_selector(
    public_fact: str,
    missing_required_facts: set[str],
) -> bool:
    return (
        public_fact in missing_required_facts
        and public_fact.startswith(_RETURNED_FIELD_PUBLIC_FACT_PREFIX)
        and public_fact.endswith(_REPOSITORY_ARTIFACT_REF_SUFFIX)
    )


def _gate_claim_items(crossing_record: MinimalCrossingRecord) -> tuple[tuple[str, GateFact], ...]:
    items: list[tuple[str, GateFact]] = []
    for stage, gate_fact in (
        ("transfer", crossing_record.transfer_gate_fact),
        ("carry", crossing_record.carry_gate_fact),
        ("movement", crossing_record.movement_gate_fact),
    ):
        if gate_fact is not None:
            items.append((stage, gate_fact))
    return tuple(items)


def _session_scope_close_fields(result: BuildingRunSupportResult) -> Mapping[str, Any]:
    request = result.adapter_result.request
    if _building_lifecycle_state(result.preparation.step_rows.link_row) != "closed":
        return {}
    if not request.building_session_ref:
        return {}
    return {
        "session_scope_close": {
            "building_session_ref": request.building_session_ref,
            "session_scope_ref": request.session_scope_ref,
            "session_continuity_mode": request.session_continuity_mode,
            "close_mode": "forget_after_building_close",
            "close_reason": "Building Plan Link row declared lifecycle state: closed",
            "proof_limits": [
                "provider-neutral session scope evidence only",
                "not raw provider session id",
                "not credential storage",
            ],
        }
    }


def _transition_lifecycle_support_evidence_fields(
    *,
    step_ref: str,
    link_row: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(link_row.get("transition_lifecycle"), Mapping):
        return {}
    carry_ref = _transition_lifecycle_carry_budget_evidence_ref(
        step_ref=step_ref,
        link_row=link_row,
        plan=plan,
    )
    if not carry_ref:
        return {}
    return {_TRANSITION_LIFECYCLE_CARRY_BUDGET_EVIDENCE_FIELD: carry_ref}


def _transition_lifecycle_carry_budget_evidence_ref(
    *,
    step_ref: str,
    link_row: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> str:
    evidence = plan.get("dynamic_walker_evidence")
    if not isinstance(evidence, Mapping):
        return ""
    lifecycle = link_row.get("transition_lifecycle")
    pending_target = (
        _optional_text_or_none(lifecycle.get("pending_target_ref"))
        if isinstance(lifecycle, Mapping)
        else None
    )
    records = _dynamic_reroute_records(evidence)
    hold_record = evidence.get("hold")
    if isinstance(hold_record, Mapping):
        records.append(hold_record)
    for record in reversed(records):
        if _optional_text_or_none(record.get("source_step_ref")) != step_ref:
            continue
        record_target = _optional_text_or_none(
            record.get("pending_target_ref")
        ) or _optional_text_or_none(record.get("target_brick"))
        if pending_target and record_target != pending_target:
            continue
        carry_ref = _optional_text_or_none(record.get("carry_budget_evidence_ref"))
        if carry_ref:
            return carry_ref
    return ""


def _gate_claim_fact_refs(
    crossing_record: MinimalCrossingRecord,
    index: int,
    step_ref: str,
) -> list[str]:
    return [_gate_claim_fact_ref(stage, index, step_ref) for stage, _ in _gate_claim_items(crossing_record)]


def _gate_claim_fact_ref(stage: str, index: int, step_ref: str) -> str:
    return _step_fact_ref(f"sufficiency-fact-{stage}", index, step_ref)


def _step_absence_ref(kind: str, index: int, step_ref: str) -> str:
    slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    return f"absence:{kind}:{index:02d}:{slug}"


def _link_movement_public_fact_refs(
    result: BuildingRunSupportResult,
    index: int,
) -> list[str]:
    step_ref = result.preparation.step_rows.step_ref
    refs = [
        _step_fact_ref("agent-fact", index, step_ref),
        _step_fact_ref("brick-comparison", index, step_ref),
    ]
    refs.extend(_gate_claim_fact_refs(result.completion.crossing_record, index, step_ref))
    route_plan = _route_replay_plan_from_link_row(result.preparation.step_rows.link_row)
    if route_plan is not None:
        refs.extend(_text_tuple("route_replay_plan.route_reason_refs", route_plan.get("route_reason_refs")))
    transition_authoring = _transition_authoring_from_link_row(result.preparation.step_rows.link_row)
    if transition_authoring is not None:
        refs.extend(
            _text_tuple(
                "transition_authoring.authoring_basis_refs",
                transition_authoring.get("authoring_basis_refs"),
            )
        )
        refs.extend(
            _text_tuple(
                "transition_authoring.transition_reason_refs",
                transition_authoring.get("transition_reason_refs", ()),
            )
        )
    return list(dict.fromkeys(refs))


def _link_movement_claim_facts(
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        movement = result.completion.crossing_record.link_fact.movement
        fact_body = {
            "movement": movement,
            "movement_source": "caller-declared Building Plan Link row",
            "public_fact_refs": _link_movement_public_fact_refs(result, index),
            "target_boundary_ref": f"brick:{prepared.next_brick_instance_ref}",
        }
        fact_body.update(_route_replay_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(_declared_gate_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(_route_decision_basis_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(_transition_authoring_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(_transition_lifecycle_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(
            _transition_lifecycle_support_evidence_fields(
                step_ref=prepared.step_rows.step_ref,
                link_row=prepared.step_rows.link_row,
                plan=plan,
            )
        )
        fact_body.update(_building_lifecycle_evidence_fields(prepared.step_rows.link_row))
        fact_body.update(_session_scope_close_fields(result))
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=_step_fact_ref("movement-fact", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("link", index)],
                proof_limits=proof_limits,
                not_proven=result.not_proven,
                fact=fact_body,
            )
        )
    facts.extend(_graph_link_movement_claim_facts(graph_context, proof_limits=proof_limits))
    return facts


def _adapter_error_link_frontier_raw_record(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: Any,
    index: int,
    *,
    transition_lifecycle: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    record = {
        "raw_ref": _raw_ref("link-frontier", index),
        "raw_refs": [_raw_ref("link-frontier", index)],
        "building_id": building_id,
        "step_ref": prepared.step_rows.step_ref,
        "observed_boundary_ref": prepared.brick_instance_ref,
        "source_brick_instance_ref": prepared.brick_instance_ref,
        "target_brick_instance_ref": prepared.brick_instance_ref,
        "transition_record_created": False,
        "adapter_error_ref": observation.adapter_error_ref,
        "frontier_kind": "agent_incomplete",
    }
    if isinstance(transition_lifecycle, Mapping):
        record.update(
            _transition_lifecycle_evidence_fields(
                {"transition_lifecycle": dict(transition_lifecycle)}
            )
        )
    return record


def _adapter_error_link_frontier_claim_fact(
    prepared: AgentRunPreparationRecord,
    observation: Any,
    index: int,
    proof_limits: tuple[str, ...],
) -> Mapping[str, Any]:
    return _claim_fact(
        axis="Link",
        fact_ref=_step_fact_ref("link-frontier", index, prepared.step_rows.step_ref),
        raw_refs=[_raw_ref("link-frontier", index)],
        proof_limits=proof_limits,
        not_proven=observation.not_proven,
        fact={
            "frontier_kind": "agent_incomplete",
            "observed_boundary_ref": prepared.brick_instance_ref,
            "transition_record_created": False,
            "disposition_record_created": False,
            "reason_refs": [observation.adapter_error_ref],
            "frontier_role": "Link transition not recorded because Agent returned evidence is absent",
        },
    )


def _chat_session_park_link_frontier_raw_record(
    building_id: str,
    prepared: AgentRunPreparationRecord,
    observation: Any,
    index: int,
    *,
    transition_lifecycle: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    record = {
        "raw_ref": _raw_ref("link-frontier", index),
        "raw_refs": [_raw_ref("link-frontier", index)],
        "building_id": building_id,
        "step_ref": prepared.step_rows.step_ref,
        "observed_boundary_ref": prepared.brick_instance_ref,
        "source_brick_instance_ref": prepared.brick_instance_ref,
        "target_brick_instance_ref": prepared.brick_instance_ref,
        "transition_record_created": False,
        "parked_ref": observation.parked_ref,
        "frontier_kind": "chat_session_parked",
    }
    if isinstance(transition_lifecycle, Mapping):
        record.update(
            _transition_lifecycle_evidence_fields(
                {"transition_lifecycle": dict(transition_lifecycle)}
            )
        )
    return record


def _chat_session_park_link_frontier_claim_fact(
    prepared: AgentRunPreparationRecord,
    observation: Any,
    index: int,
    proof_limits: tuple[str, ...],
) -> Mapping[str, Any]:
    return _claim_fact(
        axis="Link",
        fact_ref=_step_fact_ref("link-frontier", index, prepared.step_rows.step_ref),
        raw_refs=[_raw_ref("link-frontier", index)],
        proof_limits=proof_limits,
        not_proven=observation.not_proven,
        fact={
            "frontier_kind": "chat_session_parked",
            "observed_boundary_ref": prepared.brick_instance_ref,
            "transition_record_created": False,
            "disposition_record_created": False,
            "reason_refs": [observation.parked_ref],
            "frontier_role": "Link transition not recorded because chat-session work is parked",
        },
    )
