"""Adapter-error frontier write-plan + writer for the dynamic walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
support-only dynamic-walker evidence snapshot attached to a frontier plan, and
the adapter-error frontier writer that halts a walk when the provider adapter is
interrupted before an AgentFact can exist, were lifted out of the dynamic_walker
god-module into this single-concern collaborator. Both the forward walk kernel
and the resume verb route an adapter interruption through this writer.

Support mechanics only. Homes NO axis crossing. It records the adapter-error
frontier through the injected support writer; it classifies no success, chooses
no Movement, and invents no route.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import _merge_texts
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
    NOT_PROVEN,
    PROOF_LIMITS,
    RESUME_NOT_PROVEN,
)


def _dynamic_frontier_write_plan(
    linear_plan: Mapping[str, Any],
    *,
    reroute_records: list[Mapping[str, Any]],
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
    held: bool,
    hold_record: Mapping[str, Any] | None,
    fan_in_wait_all_observations: list[Mapping[str, Any]],
    has_fan_groups: bool,
    resume_observations: list[Mapping[str, Any]] | None = None,
) -> Mapping[str, Any]:
    """Attach support-only dynamic evidence to a frontier plan snapshot."""

    write_plan = dict(linear_plan)
    dynamic_evidence: dict[str, Any] = {
        "kind": "dynamic_walker_evidence",
        "walker_mode": "dynamic",
        "reroute_adoption_records": list(reroute_records),
        "node_reroute_budgets": dict(node_budget),
        "node_reroute_landings": dict(node_landings),
        "held": held,
        "hold": hold_record or {},
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if resume_observations is not None:
        dynamic_evidence["resume_observations"] = list(resume_observations)
        dynamic_evidence["not_proven"] = list(_merge_texts(NOT_PROVEN, RESUME_NOT_PROVEN))
    if has_fan_groups:
        dynamic_evidence["fan_in_wait_all_observations"] = list(
            fan_in_wait_all_observations
        )
        dynamic_evidence["proof_limits"] = list(
            _merge_texts(PROOF_LIMITS, FAN_TOPOLOGY_PROOF_LIMITS)
        )
        dynamic_evidence["not_proven"] = list(
            _merge_texts(dynamic_evidence["not_proven"], FAN_TOPOLOGY_NOT_PROVEN)
        )
    write_plan["dynamic_walker_evidence"] = dynamic_evidence
    return write_plan


def _write_dynamic_adapter_error_frontier(
    exc: Exception,
    *,
    building_id: str,
    plan_ref: str,
    linear_plan: Mapping[str, Any],
    completed_step_results: list[BuildingRunSupportResult],
    output_root: Path | str,
    overwrite_existing: bool,
    checked_proof_limits: tuple[str, ...],
    graph_context: Mapping[str, Any] | None,
    reroute_records: list[Mapping[str, Any]],
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
    held: bool,
    hold_record: Mapping[str, Any] | None,
    fan_in_wait_all_observations: list[Mapping[str, Any]],
    has_fan_groups: bool,
    write_adapter_error_frontier,
    resume_observations: list[Mapping[str, Any]] | None = None,
) -> None:
    """Write adapter-error frontier evidence for dynamic walks, then halt.

    The adapter interruption object is produced by run.py before AgentFact can
    exist. The dynamic walker records that frontier through the same support
    writer as the linear walker; it does not classify success, choose Movement,
    or invent a route.
    """

    prepared = getattr(exc, "prepared", None)
    adapter_request = getattr(exc, "adapter_request", None)
    adapter_error = getattr(exc, "adapter_error", None)
    if prepared is None or adapter_request is None or not isinstance(adapter_error, Mapping):
        raise exc
    write_adapter_error_frontier(
        building_id=building_id,
        plan_ref=plan_ref,
        plan=_dynamic_frontier_write_plan(
            linear_plan,
            reroute_records=reroute_records,
            node_budget=node_budget,
            node_landings=node_landings,
            held=held,
            hold_record=hold_record,
            fan_in_wait_all_observations=fan_in_wait_all_observations,
            has_fan_groups=has_fan_groups,
            resume_observations=resume_observations,
        ),
        completed_step_results=tuple(completed_step_results),
        failed_preparation=prepared,
        adapter_request=adapter_request,
        adapter_error=adapter_error,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=checked_proof_limits,
        graph_context=graph_context,
    )
    raise RuntimeError(
        "dynamic adapter exception frontier evidence written before AgentFact returned"
    ) from exc
