"""Shared leaf helpers + cross-cluster slugs/consts for compose_building.

The base layer of the composition module family: small pure helpers (slug,
optional-text, shape-field tokenization, step-template slug) and the
route-policy provenance vocabulary used by >=4 of the composition clusters.
Support strips and normalizes here; it authors no Movement and judges no
quality. This module imports siblings DIRECTLY and must never import from
``support.operator.composition`` at top level (cycle)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from brick_protocol.support.operator.building_operation_common import _clean_text


ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT = "constitutional-default"

GRAPH_CHAIN_TARGET_MARKERS = ("parallel", "fan_in")


def _materializer_step_template_slug(step_template_ref: str) -> str:
    tail = step_template_ref.split(":", 1)[-1]
    return _composition_slug(tail.removeprefix("building-step-template-"))


def _materializer_strip_field(shape: str, field: str) -> str:
    """Return a comma-joined required_return_shape with one field removed.

    Mechanically drops the named field (exact, case-insensitive match on the
    trimmed token) from a comma-separated field list and re-joins, preserving the
    declared order of the remaining fields. Support strips, it never reorders or
    invents fields.
    """
    fields = [token.strip() for token in shape.split(",") if token.strip()]
    kept = [token for token in fields if token.lower() != field.lower()]
    return ", ".join(kept)


def _composition_shape_has_field(shape: str, field: str) -> bool:
    """True iff the comma-joined required_return_shape contains the EXACT field.

    Membership is EXACT-TOKEN, case-insensitive on the trimmed token -- the same
    tokenization _materializer_strip_field uses. A naive ``field in shape``
    substring test FALSE-MATCHES a superstring field (e.g. it would report
    "transition_concern_evidence" present when the shape actually declares the
    distinct field "transition_concern_evidence_summary"), which false-greens the
    closure missing-field check and false-reds a legitimate fan-in source field.
    """
    fields = [token.strip().lower() for token in shape.split(",") if token.strip()]
    return field.lower() in fields


def _composition_slug(value: str) -> str:
    cleaned = "".join(
        char.lower() if char.isalnum() else "-"
        for char in str(value).strip()
    ).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "node"


_ROUTE_POLICY_PROVENANCE_VALUES: frozenset[str] = frozenset(
    {ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT, "preset-default", "per-building"}
)


def _composition_gate_sequence_ref(step: Mapping[str, Any]) -> str:
    return (
        _composition_optional_text(step.get("declared_link_gate"))
        or _composition_optional_text(step.get("gate_ref"))
        or ""
    )


def _composition_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _chain_preset_steps(preset: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    steps = preset.get("steps", ())
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        return ()
    return tuple(step for step in steps if isinstance(step, Mapping))


def _chain_preset_requires_fan_in_groups(preset: Mapping[str, Any]) -> bool:
    # E1 FULL-LEGO: an explicit graph_topology that DECLARES fan_in_groups needs
    # the same graph-group + hard-graph-contract validation the positional
    # parallel/fan-in markers trigger (the emitted plan must pass the SAME
    # compose_building validators). Absent the key -> unchanged.
    topology = preset.get("graph_topology")
    if isinstance(topology, Mapping):
        fan_in_groups = topology.get("fan_in_groups")
        if (
            isinstance(fan_in_groups, Sequence)
            and not isinstance(fan_in_groups, (str, bytes))
            and fan_in_groups
        ):
            return True
    for raw_step in _chain_preset_steps(preset):
        target_word = str(raw_step.get("target_word", "")).strip().lower()
        if any(marker in target_word for marker in GRAPH_CHAIN_TARGET_MARKERS):
            return True
    gate_concepts = preset.get("gate_concept_profile", ())
    if isinstance(gate_concepts, Sequence) and not isinstance(gate_concepts, (str, bytes)):
        return any("fan-in" in str(item).lower() for item in gate_concepts)
    return False


def _chain_preset_requires_graph(preset: Mapping[str, Any]) -> bool:
    if "node_reroute_budgets" in preset:
        return True
    return _chain_preset_requires_fan_in_groups(preset)


def _validate_declared_brick_spec_ref(
    raw_step: Mapping[str, Any],
    step_template: Mapping[str, Any],
    *,
    label: str,
) -> None:
    supplied = raw_step.get("brick_spec_ref")
    if supplied is None:
        return
    declared = _clean_text(f"{label}.brick_spec_ref", supplied)
    expected = step_template.get("brick_spec_ref")
    if declared != expected:
        raise ValueError(f"{label}.brick_spec_ref must match the registered single-Brick spec")
