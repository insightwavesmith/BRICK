"""Link Carry + Carry-budget crossing-family claim emitters.

ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B): the
Link Carry claim facts plus the node-reroute and route-replay Carry-budget
observation facts that ``support/operator/evidence_assembly.py`` previously
hand-wrote were lifted here as a single-concern per-crossing-family emitter.
P3/P4 split: this module RECORDS declared and observed Carry budget facts only;
it never decides raise/forward/stop and creates no BAL fact (the human decides
after a HOLD). Consumes the link_carry crossing through the support contracts.

Support recording shape only: NESTED evidence, no fourth axis or fact class.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.plan_validation import (
    _route_replay_plan_from_link_row,
)
from brick_protocol.support.operator.primitives import (
    _optional_text_or_none,
    _raw_ref,
    _required_text,
    _resource_slug,
    _merge_texts,
    _step_fact_ref,
    _text_tuple,
)
from brick_protocol.support.recording.claims_common import (
    _claim_fact,
    _dynamic_reroute_records,
)
from brick_protocol.support.recording.claims_link import (
    _carry_fact_claim_body,
    _link_absence_claim_fact,
)

_CARRY_BUDGET_TRACE_PATH = "evidence/claim_trace/link/carry_trace.json"
_CARRY_BUDGET_PROOF_LIMITS: tuple[str, ...] = (
    "Link Carry budget evidence only",
    "records declared and observed carry budget facts only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_CARRY_BUDGET_NOT_PROVEN: tuple[str, ...] = (
    "semantic correctness of the reroute or replay budget",
    "caller/COO disposition after a HOLD",
    "future provider/runtime behavior",
)


def _link_carry_claim_facts(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    for index, result in enumerate(step_results, start=1):
        prepared = result.preparation
        carry_fact = result.completion.crossing_record.carry_fact
        if carry_fact is None:
            facts.append(
                _link_absence_claim_fact(
                    absent_fact_type="CarryFact",
                    absence_ref_kind="link-carry",
                    statement=(
                        "caller did not supply a Link CarryFact; "
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
                fact_ref=_step_fact_ref("carry-fact", index, prepared.step_rows.step_ref),
                raw_refs=[_raw_ref("link", index)],
                proof_limits=proof_limits,
                not_proven=_merge_texts(result.not_proven, carry_fact.not_proven),
                fact=_carry_fact_claim_body(carry_fact),
            )
        )
    facts.extend(
        _link_carry_budget_claim_facts(
            building_id,
            step_results,
            plan=plan,
            proof_limits=proof_limits,
        )
    )
    return facts


def _link_carry_budget_claim_facts(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    facts: list[Mapping[str, Any]] = []
    facts.extend(
        _node_reroute_budget_claim_facts(
            building_id,
            step_results,
            plan=plan,
            proof_limits=proof_limits,
        )
    )
    facts.extend(
        _route_replay_max_attempts_claim_facts(
            building_id,
            step_results,
            proof_limits=proof_limits,
        )
    )
    return facts


def _node_reroute_budget_claim_facts(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    plan: Mapping[str, Any],
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    dynamic_evidence = plan.get("dynamic_walker_evidence")
    evidence = dynamic_evidence if isinstance(dynamic_evidence, Mapping) else {}
    budget_source = evidence.get("node_reroute_budgets", plan.get("node_reroute_budgets"))
    budgets = _integer_mapping("node_reroute_budgets", budget_source, positive=True)
    landings = _integer_mapping(
        "node_reroute_landings",
        evidence.get("node_reroute_landings"),
        positive=False,
    )
    records = _dynamic_reroute_records(evidence)
    targets = _ordered_texts(
        budgets.keys(),
        landings.keys(),
        (
            _optional_text_or_none(record.get("target_brick"))
            or _optional_text_or_none(record.get("pending_target_ref"))
            or ""
            for record in records
        ),
    )
    if not targets:
        return []

    attempts_by_brick = Counter(
        result.preparation.brick_instance_ref for result in step_results
    )
    all_link_refs = [_raw_ref("link", index) for index in range(1, len(step_results) + 1)]
    facts: list[Mapping[str, Any]] = []
    for target in targets:
        target_records = [
            record
            for record in records
            if target
            in {
                _optional_text_or_none(record.get("target_brick")),
                _optional_text_or_none(record.get("pending_target_ref")),
            }
        ]
        exhausted_records = [
            record
            for record in target_records
            if record.get("budget_exhausted") is True
            or record.get("disposition_required") is True
        ]
        raw_refs = _raw_refs_for_dynamic_records(step_results, target_records) or all_link_refs
        fact_ref = _carry_budget_fact_ref(building_id, "node", target)
        declared_budget = budgets.get(target)
        fact_body: dict[str, Any] = {
            "trace_role": "carry_budget_observation",
            "budget_kind": "node_reroute_budget",
            "budget_scope": "target_brick_node",
            "target_boundary_ref": target,
            "declared_budget": declared_budget,
            "budget_source_refs": _node_budget_source_refs(target, declared_budget is not None),
            "observed_reroute_landings": landings.get(target, 0),
            "observed_step_attempt_count": attempts_by_brick.get(target, 0),
            "budget_exhausted": any(record.get("budget_exhausted") is True for record in exhausted_records),
            "disposition_required": any(record.get("disposition_required") is True for record in exhausted_records),
            "exhaustion_status": (
                "observed_exhausted"
                if any(record.get("budget_exhausted") is True for record in exhausted_records)
                else "not_observed"
            ),
            "exhaustion_record_refs": [
                ref
                for ref in (
                    _optional_text_or_none(record.get("reroute_ref"))
                    for record in exhausted_records
                )
                if ref
            ],
            "carry_budget_evidence_ref": _carry_budget_evidence_ref(fact_ref),
            "support_created_bal_fact": False,
            "proof_limits": list(_CARRY_BUDGET_PROOF_LIMITS),
            "not_proven": list(_CARRY_BUDGET_NOT_PROVEN),
        }
        if declared_budget is None:
            fact_body["budget_missing"] = True
            fact_body["not_proven"] = list(
                _merge_texts(
                    fact_body["not_proven"],
                    ("Link node_reroute_budget was not declared for this target",),
                )
            )
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=fact_ref,
                raw_refs=raw_refs,
                proof_limits=_merge_texts(proof_limits, _CARRY_BUDGET_PROOF_LIMITS),
                not_proven=fact_body["not_proven"],
                fact=fact_body,
            )
        )
    return facts


def _route_replay_max_attempts_claim_facts(
    building_id: str,
    step_results: tuple[BuildingRunSupportResult, ...],
    *,
    proof_limits: tuple[str, ...],
) -> list[Mapping[str, Any]]:
    attempts_by_brick = Counter(
        result.preparation.brick_instance_ref for result in step_results
    )
    facts: list[Mapping[str, Any]] = []
    seen_fact_refs: set[str] = set()
    for index, result in enumerate(step_results, start=1):
        route_plan = _route_replay_plan_from_link_row(result.preparation.step_rows.link_row)
        if route_plan is None or "max_attempts" not in route_plan:
            continue
        route_replay_ref = _required_text(
            "route_replay_plan.route_replay_ref",
            route_plan.get("route_replay_ref"),
        )
        immediate_target = _required_text(
            "route_replay_plan.immediate_target_ref",
            route_plan.get("immediate_target_ref"),
        )
        replay_refs = list(
            _text_tuple("route_replay_plan.replay_segment_refs", route_plan.get("replay_segment_refs"))
        )
        counted_refs = [immediate_target, *replay_refs]
        fact_ref = _carry_budget_fact_ref(building_id, "route-replay", route_replay_ref)
        if fact_ref in seen_fact_refs:
            continue
        seen_fact_refs.add(fact_ref)
        observed_total_execution_count_by_boundary = {
            ref: attempts_by_brick.get(ref, 0) for ref in counted_refs
        }
        fact_body = {
            "trace_role": "carry_budget_observation",
            "budget_kind": "route_replay_max_attempts",
            "budget_scope": "declared_route_replay_plan",
            "route_replay_ref": route_replay_ref,
            "source_step_ref": result.preparation.step_rows.step_ref,
            "declared_by_ref": _required_text(
                "route_replay_plan.author_ref",
                route_plan.get("author_ref"),
            ),
            "immediate_target_ref": immediate_target,
            "replay_segment_refs": replay_refs,
            "declared_budget": _positive_int_value(
                "route_replay_plan.max_attempts",
                route_plan.get("max_attempts"),
            ),
            "budget_source_refs": [
                (
                    "work/declared-building-plan.json#step."
                    + result.preparation.step_rows.step_ref
                    + ".route_replay_plan.max_attempts"
                ),
                "work/link-launch-policy.json#launch_rows.route_replay_plan.max_attempts",
            ],
            "observed_total_execution_count_by_boundary": observed_total_execution_count_by_boundary,
            "observed_replay_execution_count_by_boundary": {
                ref: max(count - 1, 0)
                for ref, count in observed_total_execution_count_by_boundary.items()
            },
            "budget_exhausted": False,
            "disposition_required": False,
            "exhaustion_status": "not_observed",
            "carry_budget_evidence_ref": _carry_budget_evidence_ref(fact_ref),
            "support_created_bal_fact": False,
            "proof_limits": list(_CARRY_BUDGET_PROOF_LIMITS),
            "not_proven": list(_CARRY_BUDGET_NOT_PROVEN),
        }
        facts.append(
            _claim_fact(
                axis="Link",
                fact_ref=fact_ref,
                raw_refs=[_raw_ref("link", index)],
                proof_limits=_merge_texts(proof_limits, _CARRY_BUDGET_PROOF_LIMITS),
                not_proven=fact_body["not_proven"],
                fact=fact_body,
            )
        )
    return facts


def _carry_budget_fact_ref(building_id: str, budget_kind: str, ref: str) -> str:
    return (
        "carry-budget:"
        + _resource_slug("building_id", building_id.replace(":", "-"))
        + ":"
        + _resource_slug("budget_kind", budget_kind.replace(":", "-"))
        + ":"
        + _resource_slug("budget_ref", ref.replace(":", "-"))
    )


def _carry_budget_evidence_ref(fact_ref: str) -> str:
    return _CARRY_BUDGET_TRACE_PATH + "#" + fact_ref


def _node_budget_source_refs(target: str, declared: bool) -> list[str]:
    if not declared:
        return ["work/declared-building-plan.json#node_reroute_budgets"]
    slug = _resource_slug("target_brick", target.replace(":", "-"))
    return [
        "work/declared-building-plan.json#node_reroute_budgets." + slug,
        "work/link-launch-policy.json#node_reroute_budgets." + slug,
    ]


def _integer_mapping(
    label: str,
    value: Any,
    *,
    positive: bool,
) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(label + " must be a mapping")
    result: dict[str, int] = {}
    for raw_key, raw_value in value.items():
        key = _optional_text_or_none(raw_key)
        if not key:
            raise ValueError(label + " keys must be non-empty text")
        if isinstance(raw_value, bool):
            raise ValueError(label + " values must be integers")
        if isinstance(raw_value, int):
            number = raw_value
        elif isinstance(raw_value, str) and raw_value.strip().isdecimal():
            number = int(raw_value)
        else:
            raise ValueError(label + " values must be integers")
        if positive and number <= 0:
            raise ValueError(label + " values must be positive integers")
        if not positive and number < 0:
            raise ValueError(label + " values must be non-negative integers")
        result[key] = number
    return result


def _positive_int_value(label: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(label + " must be a positive integer")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(label + " must be a positive integer")


def _ordered_texts(*groups: Iterable[str | None]) -> list[str]:
    values: list[str] = []
    for group in groups:
        for value in group:
            if value and value not in values:
                values.append(value)
    return values


def _raw_refs_for_dynamic_records(
    step_results: tuple[BuildingRunSupportResult, ...],
    records: list[Mapping[str, Any]],
) -> list[str]:
    step_refs = {
        step_ref
        for step_ref in (
            _optional_text_or_none(record.get("source_step_ref")) for record in records
        )
        if step_ref
    }
    refs: list[str] = []
    for index, result in enumerate(step_results, start=1):
        if result.preparation.step_rows.step_ref in step_refs:
            refs.append(_raw_ref("link", index))
    return refs
