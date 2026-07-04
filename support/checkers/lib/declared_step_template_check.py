"""Declared step-template behavioral profile runners.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    rule_items,
)


def run_declared_step_template_plan_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "declared_step_template_plan_case")
    if not items:
        return 0
    from support.operator.building_operation import render_declared_step_template_plan
    count = 0
    for item in items:
        mapping = require_mapping(item, "declared_step_template_plan_case item")
        case, relative = _profile_case_document(repo, mapping, "declared_step_template_plan_case")
        rendered = render_declared_step_template_plan(case, repo_root=repo)
        expected = require_mapping(mapping.get("expected", {}), "declared_step_template_plan_case.expected")
        steps = rendered.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: no rendered steps")
        rows = require_mapping(steps[0], f"{relative}: steps[0]").get("rows")
        if not isinstance(rows, list):
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: rows missing")
        link_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Link"]
        if len(link_rows) != 1:
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: Link row missing")
        link_row = link_rows[0]
        for key in ("movement", "target_ref"):
            if key in expected and link_row.get(key) != expected[key]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {link_row.get(key)!r}"
                )
        if "declared_gate_refs" in expected and link_row.get("declared_gate_refs") != expected["declared_gate_refs"]:
            raise ProfileError(
                f"declared_step_template_plan_case rejected {relative}: declared_gate_refs mismatch"
            )
        if "brick_capability_class" in expected:
            brick_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Brick"]
            if len(brick_rows) != 1:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: Brick row missing"
                )
            observed_capability = brick_rows[0].get("capability_class")
            if observed_capability != expected["brick_capability_class"]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"brick_capability_class expected {expected['brick_capability_class']!r}, "
                    f"observed {observed_capability!r}"
                )
        step = require_mapping(steps[0], f"{relative}: steps[0]")
        for key in ("selected_adapter_ref", "selected_model_ref"):
            if key in expected and step.get(key) != expected[key]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {step.get(key)!r}"
                )
        # Optional: assert the stamped Agent row (proves a same-NEED author override
        # changes the agent the linear path stamps -- finding-2 regression net).
        if "agent_object_ref" in expected:
            agent_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Agent"]
            if len(agent_rows) != 1:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: Agent row missing"
                )
            observed_agent = agent_rows[0].get("agent_object_ref")
            if observed_agent != expected["agent_object_ref"]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"agent_object_ref expected {expected['agent_object_ref']!r}, observed {observed_agent!r}"
                )
        count += 1
    return count


def run_declared_step_template_plan_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "declared_step_template_plan_rejects")
    if not items:
        return 0
    from support.operator.building_operation import render_declared_step_template_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "declared_step_template_plan_rejects item")
        case, relative = _profile_case_document(repo, mapping, "declared_step_template_plan_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")
        try:
            render_declared_step_template_plan(case, repo_root=repo)
        except (TypeError, ValueError) as exc:
            if expected_message and expected_message not in str(exc):
                raise ProfileError(
                    f"declared_step_template_plan_rejects rejected {relative}: "
                    f"expected message {expected_message!r}, observed {exc}"
                ) from exc
            count += 1
            continue
        raise ProfileError(f"declared_step_template_plan_rejects expected rejection but passed: {relative}")
    return count

