"""Materialized return-shape guards for behavioral profile cases."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    load_yaml_subset_file,
    require_string_list,
)


def _materialized_return_shape_fields(value: Any) -> list[str]:
    """Split a comma-joined required_return_shape string into trimmed field tokens.

    Whitespace/separator tolerant (the materializer joins with ', ' but the
    declared field ORDER is preserved). Returns the field names in order.
    """
    text = str(value or "")
    return [token.strip() for token in text.split(",") if token.strip()]


def _brick_return_shape_fields(repo: Path, kind: str, label: str) -> list[str]:
    """Read the LIVE brick return.yaml required_return_shape list for a kind.

    Reads ``brick/templates/bricks/<kind>/return.yaml`` (the kind's PRIMARY
    return template — the exact file the Builder derives the default
    required_return_shape from) and returns its declared field list in order.
    Reading the live file (not a static copy) makes the guard track the source
    of truth: if the brick declared shape changes, the expectation changes with
    it.
    """
    relative = f"brick/templates/bricks/{kind}/return.yaml"
    doc = load_yaml_subset_file(repo, relative)
    raw = doc.get("required_return_shape")
    if not isinstance(raw, list):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: brick return template "
            f"{relative} has no required_return_shape list"
        )
    fields: list[str] = []
    for token in raw:
        text = str(token).strip()
        if text:
            fields.append(text)
    return fields


def _materialized_brick_row_field(step: Mapping[str, Any], field: str) -> Any:
    """Return a field from the materialized Brick-axis row."""
    for row in step.get("rows") or []:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            return row.get(field)
    return None


def _materialized_brick_row_shape(step: Mapping[str, Any]) -> str | None:
    """Return the Brick-axis row's required_return_shape text for a materialized step."""
    return _materialized_brick_row_field(step, "required_return_shape")


def _check_materialized_node_return_shapes(
    repo: Path, plan: Mapping[str, Any], *, label: str
) -> None:
    """Assert the materialized node required_return_shape content (Phase 2.5 guard).

    Closes the false-green gap where the materializer could regress to a
    hardcoded / support-invented shape and stay GREEN. Three assertions, derived
    from the LIVE brick return.yaml + the plan's own fan-in group topology:

      1. NO materialized node's required_return_shape may contain the
         support-invented ``concern_observations`` (hard reject — the invention
         must never reappear).
      2. Each fan-in SOURCE node's required_return_shape MUST equal the source
         brick's declared required_return_shape exactly (proves it is
         brick-derived, not hardcoded or support-shrunk).
      3. The fan-in TARGET (closure) node's required_return_shape MUST contain
         transition_concern_evidence.
      4. Fan-in SOURCE Link carry stays narrowed by carries_forward_fields, so
         transition_concern_evidence is not carried by source-position QA rows.
    """
    if plan.get("plan_shape") != "graph":
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "assert_materialized_return_shapes requires a graph plan"
        )
    steps = {
        str(step.get("step_ref")): step
        for step in plan.get("brick_steps") or []
        if isinstance(step, Mapping)
    }

    def _kind_for(step: Mapping[str, Any]) -> str:
        template_ref = str(step.get("step_template_ref") or "")
        return template_ref.split(":", 1)[1] if ":" in template_ref else template_ref

    # (1) concern_observations must never reappear on ANY node.
    for step_ref, step in steps.items():
        fields = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        if any(field.lower() == "concern_observations" for field in fields):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: node {step_ref} "
                "required_return_shape contains the support-invented "
                "'concern_observations' (the invention must never reappear)"
            )

    # Derive fan-in SOURCE / TARGET steps from the plan's OWN fan-in group + edges.
    edges = {
        str(edge.get("edge_ref")): edge
        for edge in plan.get("link_edges") or []
        if isinstance(edge, Mapping)
    }
    fan_in_groups = [
        group
        for group in plan.get("groups") or []
        if isinstance(group, Mapping) and group.get("group_role") == "fan_in"
    ]
    if not fan_in_groups:
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "assert_materialized_return_shapes found no fan_in group to verify"
        )
    source_step_refs: list[str] = []
    target_step_refs: set[str] = set()
    for group in fan_in_groups:
        for member_ref in group.get("member_refs") or []:
            edge = edges.get(str(member_ref))
            if not isinstance(edge, Mapping):
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: fan_in member "
                    f"{member_ref!r} has no matching link edge"
                )
            source_ref = str(edge.get("source_step_ref") or "")
            target_ref = str(edge.get("target_step_ref") or "")
            if source_ref not in steps or target_ref not in steps:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: fan_in edge "
                    f"{member_ref!r} references unknown step(s)"
                )
            if source_ref not in source_step_refs:
                source_step_refs.append(source_ref)
            target_step_refs.add(target_ref)

    # (2) Each fan-in SOURCE shape == full brick-declared shape. Link carry is
    # filtered by carries_forward_fields, not by shrinking the Brick return contract.
    source_policy = plan.get("fan_in_source_transition_concern_adoption")
    if not isinstance(source_policy, Mapping):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: graph fan-in sources "
            "must carry declared advisory transition_concern_adoption policy"
        )
    if (
        source_policy.get("policy") != "advisory"
        or source_policy.get("scope") != "fan_in_sources"
    ):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: fan-in source "
            "transition_concern_adoption policy must be advisory for fan_in_sources"
        )
    declared_policy_sources = require_string_list(
        source_policy.get("source_step_refs", []),
        f"{label}: fan_in_source_transition_concern_adoption.source_step_refs",
    )
    if sorted(declared_policy_sources) != sorted(source_step_refs):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: fan-in source "
            "transition_concern_adoption source_step_refs do not match fan-in topology"
        )
    for source_ref in source_step_refs:
        step = steps[source_ref]
        kind = _kind_for(step)
        observed = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        brick_fields = _brick_return_shape_fields(repo, kind, label)
        if observed != brick_fields:
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: fan-in SOURCE node "
                f"{source_ref} ({kind}) required_return_shape is not brick-derived; "
                f"expected full brick return.yaml shape {brick_fields!r}, "
                f"observed {observed!r}"
            )
        carry_fields = _materialized_return_shape_fields(
            _materialized_brick_row_field(step, "carries_forward_fields")
        )
        if any(field.lower() == "transition_concern_evidence" for field in carry_fields):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: fan-in SOURCE node "
                f"{source_ref} ({kind}) carries_forward_fields must not carry "
                f"transition_concern_evidence; observed {carry_fields!r}"
            )

    # (3) The fan-in TARGET (closure) shape MUST carry transition_concern_evidence.
    for target_ref in sorted(target_step_refs):
        step = steps[target_ref]
        observed = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        if not any(field.lower() == "transition_concern_evidence" for field in observed):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: fan-in TARGET node "
                f"{target_ref} required_return_shape must contain "
                f"transition_concern_evidence; observed {observed!r}"
            )
