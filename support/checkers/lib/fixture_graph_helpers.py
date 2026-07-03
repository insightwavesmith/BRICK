"""Shared checker graph-fixture builders.

Support evidence only: these helpers build dictionaries for checker fixtures.
They do not choose Movement, route targets, gate sufficiency, success, or
quality.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_DEFAULT_GATE_REFS = ["link-gate:default-transition"]


def fixture_proof_limits() -> list[str]:
    """Return the shared support-boundary proof-limit text used by graph fixtures."""

    return [
        "support evidence only",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]


def fixture_brick_row(
    step_ref: str,
    brick_ref: str,
    *,
    work_statement: str,
    required_return_shape: str,
    source_facts: Sequence[str] | None = None,
    comparison_rule: str = "Observe support evidence only; do not choose Movement or judge quality.",
) -> Mapping[str, Any]:
    """Build a Brick row while keeping scenario-specific defaults with the caller."""

    return {
        "axis": "Brick",
        "row_ref": f"brick-row:{step_ref}",
        "brick_work_ref": f"work:{step_ref}",
        "brick_instance_ref": brick_ref,
        "work_statement": work_statement,
        "comparison_rule": comparison_rule,
        "required_return_shape": required_return_shape,
        "source_facts": list(source_facts or []),
    }


def fixture_agent_row(step_ref: str, *, agent_object_ref: str) -> Mapping[str, Any]:
    """Build an Agent row without assigning a shared default Agent Object."""

    return {
        "axis": "Agent",
        "row_ref": f"agent-row:{step_ref}",
        "agent_object_ref": agent_object_ref,
    }


def fixture_graph_brick_step(
    step_ref: str,
    brick_ref: str,
    completion_edge_ref: str,
    *,
    agent_object_ref: str,
    work_statement: str,
    required_return_shape: str,
    source_facts: Sequence[str] | None = None,
    selected_adapter_ref: str | None = None,
    step_template_ref: str = "",
) -> Mapping[str, Any]:
    """Build a graph Brick step from parameterized Brick and Agent rows."""

    step: dict[str, Any] = {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            fixture_brick_row(
                step_ref,
                brick_ref,
                work_statement=work_statement,
                required_return_shape=required_return_shape,
                source_facts=source_facts,
            ),
            fixture_agent_row(step_ref, agent_object_ref=agent_object_ref),
        ],
    }
    if selected_adapter_ref is not None:
        step["selected_adapter_ref"] = selected_adapter_ref
    if step_template_ref:
        step["step_template_ref"] = step_template_ref
    return step


def _resolved_gate_refs(
    declared_gate_refs: Sequence[str] | None,
    *,
    falsy_declared_gate_refs_use_default: bool,
) -> list[str]:
    if falsy_declared_gate_refs_use_default:
        return list(declared_gate_refs or _DEFAULT_GATE_REFS)
    if declared_gate_refs is not None:
        return list(declared_gate_refs)
    return list(_DEFAULT_GATE_REFS)


def fixture_graph_link_edge(
    edge_ref: str,
    source_step_ref: str,
    target_ref: str,
    *,
    target_step_ref: str = "",
    movement: str = "forward",
    route_replay_plan: Mapping[str, Any] | None = None,
    declared_gate_refs: Sequence[str] | None = None,
    close_reason: str | None = None,
    falsy_declared_gate_refs_use_default: bool = False,
) -> Mapping[str, Any]:
    """Build a graph Link edge while preserving existing falsy-gate variants.

    Falsy-gate divergence is intentional: loop0 uses ``gate or default`` in
    support/checkers/check_bounded_agent_proposed_routing_loop0.py:87 and :822,
    while case_runners treats only ``None`` as default at
    support/checkers/lib/case_runners.py:7995. Set
    ``falsy_declared_gate_refs_use_default`` for loop0-style aliases.
    """

    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{edge_ref}",
        "movement": movement,
        "target_ref": target_ref,
        "declared_gate_refs": _resolved_gate_refs(
            declared_gate_refs,
            falsy_declared_gate_refs_use_default=falsy_declared_gate_refs_use_default,
        ),
    }
    if route_replay_plan is not None:
        link_row["route_replay_plan"] = dict(route_replay_plan)
    edge: dict[str, Any] = {
        "edge_ref": edge_ref,
        "source_step_ref": source_step_ref,
        "rows": [link_row],
    }
    if target_step_ref:
        edge["target_step_ref"] = target_step_ref
    elif close_reason is not None:
        link_row["building_lifecycle"] = {"state": "closed", "reason": close_reason}
    return edge


def fixture_graph_helpers_self_check_violations() -> list[str]:
    """Compare representative current consumers with equivalent helper calls."""

    from support.checkers import check_bounded_agent_proposed_routing_loop0 as loop0
    from support.checkers.lib import case_runners

    violations: list[str] = []

    if fixture_proof_limits() != loop0._proof_limits():
        violations.append("fixture_proof_limits does not match loop0 _proof_limits sample")
    if fixture_proof_limits() != case_runners._step_output_drain_proof_limits():
        violations.append("fixture_proof_limits does not match case_runners proof-limits sample")

    loop0_step_ref = "step:self-check"
    loop0_step = fixture_graph_brick_step(
        loop0_step_ref,
        "brick:self-check",
        "edge:self-check-complete",
        agent_object_ref="agent-object:dev",
        work_statement=f"Declared work for {loop0_step_ref}.",
        required_return_shape="observed_evidence, not_proven",
        source_facts=["AGENTS.md", "support/operator/dynamic_walker.py"],
    )
    if loop0_step != loop0._brick_step(
        loop0_step_ref,
        "brick:self-check",
        "agent-object:dev",
        "edge:self-check-complete",
    ):
        violations.append("fixture_graph_brick_step does not match loop0 _brick_step sample")

    case_step_ref = "step:case-self-check"
    case_step = fixture_graph_brick_step(
        case_step_ref,
        "brick:case-self-check",
        "edge:case-self-check-complete",
        agent_object_ref="agent-object:coo",
        work_statement=f"Run checker live step-output drain step {case_step_ref}.",
        required_return_shape="body_marker, source_fact_body_refs, carried_markers, not_proven",
        source_facts=["AGENTS.md"],
        selected_adapter_ref="adapter:local",
        step_template_ref="building-step-template:work",
    )
    if case_step != case_runners._graph_brick_step(
        case_step_ref,
        "brick:case-self-check",
        "edge:case-self-check-complete",
        source_facts=["AGENTS.md"],
        step_template_ref="building-step-template:work",
    ):
        violations.append("fixture_graph_brick_step does not match case_runners _graph_brick_step sample")

    if fixture_graph_link_edge(
        "edge:self-check",
        "step:source",
        "brick:target",
        target_step_ref="step:target",
        declared_gate_refs=[],
        falsy_declared_gate_refs_use_default=True,
    ) != loop0._fwd_edge("edge:self-check", "step:source", "step:target", "brick:target", []):
        violations.append("fixture_graph_link_edge does not match loop0 _fwd_edge falsy-gate sample")

    route_replay_plan = {"plan_ref": "plan:self-check"}
    if fixture_graph_link_edge(
        "edge:reroute-self-check",
        "step:source",
        "brick:target",
        target_step_ref="step:target",
        movement="reroute",
        route_replay_plan=route_replay_plan,
        declared_gate_refs=[],
        falsy_declared_gate_refs_use_default=True,
    ) != loop0._reroute_edge(
        "edge:reroute-self-check",
        "step:source",
        "step:target",
        "brick:target",
        route_replay_plan=route_replay_plan,
        gate=[],
    ):
        violations.append("fixture_graph_link_edge does not match loop0 _reroute_edge falsy-gate sample")

    if fixture_graph_link_edge(
        "edge:close-self-check",
        "step:source",
        "building-boundary:self-check",
        close_reason="checker close sample",
        falsy_declared_gate_refs_use_default=True,
    ) != loop0._close_edge(
        "edge:close-self-check",
        "step:source",
        "checker close sample",
        "building-boundary:self-check",
    ):
        violations.append("fixture_graph_link_edge does not match loop0 _close_edge sample")

    if fixture_graph_link_edge(
        "edge:case-self-check",
        "step:source",
        "brick:target",
        target_step_ref="step:target",
        declared_gate_refs=[],
    ) != case_runners._graph_link_edge(
        "edge:case-self-check",
        "step:source",
        "step:target",
        "brick:target",
        declared_gate_refs=[],
    ):
        violations.append("fixture_graph_link_edge does not match case_runners empty-gate sample")

    if fixture_graph_link_edge(
        "edge:case-close-self-check",
        "step:source",
        "building-boundary:self-check",
        close_reason="checker live step-output drain close",
    ) != case_runners._graph_link_edge(
        "edge:case-close-self-check",
        "step:source",
        "",
        "building-boundary:self-check",
    ):
        violations.append("fixture_graph_link_edge does not match case_runners close sample")

    return violations


def main() -> int:
    violations = fixture_graph_helpers_self_check_violations()
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
