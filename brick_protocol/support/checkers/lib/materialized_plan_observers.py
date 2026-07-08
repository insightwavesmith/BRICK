"""Materialized plan observation helpers for behavioral profile cases."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_string_list,
)


def _link_rows_list_field(plan: Mapping[str, Any], key: str) -> list[list[Any]]:
    """Per-Link-row LIST field values in declared row order (both plan shapes).

    Linear plans iterate steps[].rows; graph plans iterate link_edges[].rows.
    A Link row without the field contributes [] so per-row assertions can pin
    ABSENCE as exactly as presence.
    """

    sources = (
        plan.get("link_edges", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    observed: list[list[Any]] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                value = row.get(key)
                observed.append(list(value) if isinstance(value, list) else [])
    return observed


def _materialized_step_values(plan: Mapping[str, Any], key: str) -> list[str]:
    sources = (
        plan.get("brick_steps", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    return [
        str(step.get(key))
        for step in sources or []
        if isinstance(step, Mapping) and step.get(key) is not None
    ]


def _link_rows_in_declared_order(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Every Link row in declared row order (both plan shapes)."""

    sources = (
        plan.get("link_edges", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    rows: list[Mapping[str, Any]] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                rows.append(row)
    return rows


def _link_rows_provenance_tokens(plan: Mapping[str, Any], label: str) -> list[list[str]]:
    """Per-Link-row gate_concept_provenance token lists (A1/A4 FIRE reader).

    A row WITHOUT the field contributes [] (absence pinned exactly like
    presence). A row WITH the field must carry a well-formed non-empty tokens
    list -- a present-but-empty/malformed provenance is REJECTED here instead
    of aliasing to absence (a malformed stamp must never look like "no stamp").
    """

    observed: list[list[str]] = []
    for row in _link_rows_in_declared_order(plan):
        if "gate_concept_provenance" not in row:
            observed.append([])
            continue
        provenance = row.get("gate_concept_provenance")
        if not isinstance(provenance, Mapping):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance must be a mapping, got {provenance!r}"
            )
        tokens = provenance.get("tokens")
        if (
            not isinstance(tokens, list)
            or not tokens
            or not all(isinstance(token, str) and token.strip() for token in tokens)
        ):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance.tokens must be a non-empty string list, "
                f"got {tokens!r}"
            )
        observed.append([token.strip() for token in tokens])
    return observed


def _link_rows_provenance_declared_by(plan: Mapping[str, Any], label: str) -> list[str]:
    """declared_by values of every provenance-carrying Link row (A4 FIRE reader)."""

    observed: list[str] = []
    for row in _link_rows_in_declared_order(plan):
        if "gate_concept_provenance" not in row:
            continue
        provenance = row.get("gate_concept_provenance")
        if not isinstance(provenance, Mapping):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance must be a mapping, got {provenance!r}"
            )
        declared_by = provenance.get("declared_by")
        if not isinstance(declared_by, str) or not declared_by.strip():
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance.declared_by must be non-empty text, "
                f"got {declared_by!r}"
            )
        observed.append(declared_by.strip())
    return observed


def _observed_link_row_values(plan: Mapping[str, Any], key: str) -> list[str]:
    sources = plan.get("link_edges", []) if plan.get("plan_shape") == "graph" else plan.get("steps", [])
    observed: list[str] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                observed.append(str(row.get(key)))
    return observed


def _check_materialize_building_declaration_evidence(
    building_root: Path,
    *,
    expected: Mapping[str, Any],
    label: str,
) -> None:
    work_files = require_string_list(
        expected.get("work_files", []),
        "materialize_building_intent_case.expected.declaration_evidence.work_files",
    )
    for relative in work_files:
        if not (building_root / relative).is_file():
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: missing declaration evidence {relative}"
            )
    intake = json.loads((building_root / "work" / "building-intake.json").read_text(encoding="utf-8"))
    if expected.get("task_source_hash_state") and intake.get("task_source_hash_state") != expected.get(
        "task_source_hash_state"
    ):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            f"task_source_hash_state expected {expected.get('task_source_hash_state')!r}, "
            f"observed {intake.get('task_source_hash_state')!r}"
        )
    if expected.get("task_source_hash_present") and not intake.get("task_source_hash"):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: intake task_source_hash missing"
        )
    preset_expansion = json.loads(
        (building_root / "work" / "preset-expansion.json").read_text(encoding="utf-8")
    )
    _check_declaration_ref_expectations(
        preset_expansion,
        expected,
        label=label,
        case_name="materialize_building_intent_case",
    )


def _check_declaration_ref_expectations(
    observed_packet: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
    case_name: str,
) -> None:
    for key, noun in (
        ("expanded_step_template_refs", "step template"),
        ("expanded_brick_spec_refs", "Brick spec"),
        ("expanded_brick_template_refs", "Brick return template"),
    ):
        required = set(
            require_string_list(
                expected.get(key, []),
                f"{case_name}.expected.declaration_evidence.{key}",
            )
        )
        if not required:
            continue
        observed = {
            str(item)
            for item in observed_packet.get(key, [])
            if isinstance(item, str)
        }
        missing = sorted(required - observed)
        if missing:
            raise ProfileError(
                f"{case_name} rejected {label}: missing {noun} provenance {missing}"
            )
