"""Casting-node carry behavioral checker."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.plan_fixture_helpers import _graph_test_plan_from_linear
from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError


def _casting_node_carry_base_graph_plan() -> dict[str, Any]:
    """Compose ONE minimal valid graph plan for the casting-carry probe.

    The plan is a single-step forward-to-boundary building plan composed through
    the real ``compose_building`` front door (so the projected graph is genuinely
    plan-admissible, not a hand-stubbed dict). The probe then overlays differing
    casting refs on the brick_step vs the plan and re-projects it.
    """

    linear = {
        "plan_shape": "linear",
        "building_id": "casting-node-carry-probe",
        "plan_ref": "building-plan:casting-node-carry-probe",
        "declared_by": "coo",
        "selected_adapter_ref": "adapter:codex-local",
        "selected_model_ref": "model:default",
        "steps": [
            {
                "step_ref": "s1",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "br1",
                        "brick_instance_ref": "brick:casting-node-carry-probe-1",
                        "work_statement": "casting node carry probe step",
                        "required_return_shape": ["observed_evidence"],
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "ar1",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": "lr1",
                        "movement": "forward",
                        "target_ref": "building-boundary:casting-node-carry-probe-closed",
                    },
                ],
            }
        ],
    }
    return dict(_graph_test_plan_from_linear(linear))


def run_casting_node_carry(repo: Path) -> KernelResult:
    """Behavioral probe: the graph->linear projection carries every casting field
    with step-OR-plan precedence (step value when truthy, else plan; None when
    declared on neither side).

    This is the REAL probe that replaced the brittle ``selected_model_ref``
    grep shape-pin on plan_graph.py after S1 folded the per-field carry into the
    opaque casting bag (casting_bag / merge_casting_bags / stamp_casting). It
    drives the genuine ``brick_protocol/support/operator/plan_graph._linear_plan_from_graph_plan``
    over a composed graph plan and asserts the projected linear step against the
    real ``NODE_CASTING_FIELDS`` table, so a NEW casting field is auto-covered
    without touching this check.

    Mutation-RED witness: drop a field in ``primitives.stamp_casting`` (or in
    ``merge_casting_bags`` / ``casting_bag``) -> the step-wins scenario sees that
    field come back ``None`` instead of the declared step value -> RED.
    """

    from brick_protocol.support.operator.plan_graph import _linear_plan_from_graph_plan
    from brick_protocol.support.operator.primitives import NODE_CASTING_FIELDS

    fields = list(NODE_CASTING_FIELDS)
    if not fields:
        raise ProfileError(
            "kernel check casting_node_carry: NODE_CASTING_FIELDS is empty; "
            "the casting projection has nothing to carry"
        )

    def _projected_step(step_overlay: Mapping[str, Any], plan_overlay: Mapping[str, Any]) -> Mapping[str, Any]:
        plan = _casting_node_carry_base_graph_plan()
        brick_step = dict(plan["brick_steps"][0])
        # Overlay (and strip) the casting fields on the brick_step (the STEP side)
        # and on the top-level plan (the PLAN side) so precedence is exercised
        # against the composed defaults rather than absence alone.
        for field_name in fields:
            if field_name in step_overlay:
                brick_step[field_name] = step_overlay[field_name]
            else:
                brick_step.pop(field_name, None)
            if field_name in plan_overlay:
                plan[field_name] = plan_overlay[field_name]
            else:
                plan.pop(field_name, None)
        plan["brick_steps"] = [brick_step]
        linear_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        steps = linear_plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ProfileError(
                "kernel check casting_node_carry: projection produced no linear steps"
            )
        return steps[0]

    failures: list[str] = []

    # Scenario A: step AND plan both declare a casting field, with DIFFERENT
    # values -> the step value must win (step-OR-plan precedence, step truthy).
    step_a = {f: f"step::{f}" for f in fields}
    plan_a = {f: f"plan::{f}" for f in fields}
    projected_a = _projected_step(step_a, plan_a)
    for field_name in fields:
        observed = projected_a.get(field_name)
        if observed != step_a[field_name]:
            failures.append(
                f"step-wins: {field_name} expected {step_a[field_name]!r} "
                f"(step value), observed {observed!r}"
            )

    # Scenario B: step value is empty (falsey) but plan declares it -> the plan
    # value must carry (step-OR-plan precedence, step falsey -> fall through).
    step_b = {f: "" for f in fields}
    plan_b = {f: f"plan::{f}" for f in fields}
    projected_b = _projected_step(step_b, plan_b)
    for field_name in fields:
        observed = projected_b.get(field_name)
        if observed != plan_b[field_name]:
            failures.append(
                f"plan-fallback: {field_name} expected {plan_b[field_name]!r} "
                f"(plan value when step empty), observed {observed!r}"
            )

    # Scenario C: a casting field declared on NEITHER side -> it must still be
    # stamped, carrying None (full key set preserved, byte-identical to the
    # prior explicit per-field assignment).
    projected_c = _projected_step({}, {})
    for field_name in fields:
        if field_name not in projected_c:
            failures.append(
                f"neither: {field_name} absent from projected step; the full "
                "casting key set must be stamped"
            )
        elif projected_c.get(field_name) is not None:
            failures.append(
                f"neither: {field_name} expected None (declared on neither side), "
                f"observed {projected_c.get(field_name)!r}"
            )

    if failures:
        detail = "\n".join(f"- {failure}" for failure in failures)
        raise ProfileError(
            "kernel check casting_node_carry rejected the graph->linear casting "
            f"projection:\n{detail}"
        )

    return KernelResult(
        check_id="casting_node_carry",
        inspected=len(fields),
        output=(
            "casting node carry passed: graph->linear projection carries "
            f"{len(fields)} casting field(s) ({', '.join(fields)}) with step-OR-plan "
            "precedence (step-wins / plan-fallback / None-on-neither)."
        ),
    )
