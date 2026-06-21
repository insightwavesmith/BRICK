"""Shared leaf helpers + cross-cluster slugs/consts for compose_building.

The base layer of the composition module family: small pure helpers (slug,
optional-text, shape-field tokenization, step-template slug) and the
route-policy provenance vocabulary used by >=4 of the composition clusters.
Support strips and normalizes here; it authors no Movement and judges no
quality. This module imports siblings DIRECTLY and must never import from
``support.operator.composition`` at top level (cycle)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT = "constitutional-default"


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
