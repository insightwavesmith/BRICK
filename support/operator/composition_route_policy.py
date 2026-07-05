"""Composition route-policy: reroute-budget + closure-policy cascade, validation,
provenance (leaf-utility, lowest blast radius).

Extracted verbatim from the pre-split composition module (module-separation). PURE relocation: no
logic/name/signature/order change. Imports siblings directly (no top-level import
of the composer facade, which would cycle).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.plan_rendering import _load_yaml_mapping
from brick_protocol.support.operator.composition_common import (
    ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT,
    _ROUTE_POLICY_PROVENANCE_VALUES,
    _materializer_step_template_slug,
)
from brick_protocol.support.recording.contracts import require_positive_int


REROUTE_DEFAULTS_PATH = Path("brick/templates/reroute-defaults.yaml")


def _materializer_reroute_budgets(
    raw: Any,
    *,
    source_label: str,
) -> Mapping[str, int]:
    """Validate a DECLARED per-kind reroute budget map (B).

    The HUMAN route author declares ``node_reroute_budgets`` as a mapping of
    step_template_ref -> positive int. This validates+copies it; support NEVER
    defaults a budget. The same validation runs for the PRESET-declared map and a
    per-Building OVERRIDE map (``source_label`` only names the source in errors).
    A declaration that supplies no budgets yields an empty map (and the closure
    policy target, which must be budgeted, then fails closed in compose_building).
    """
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(
            f"{source_label} node_reroute_budgets must be a mapping of "
            "step_template_ref -> positive int"
        )
    budgets: dict[str, int] = {}
    for raw_key, raw_value in raw.items():
        key = str(raw_key).strip()
        if not key:
            raise ValueError(f"{source_label} node_reroute_budgets key must be a step_template_ref")
        try:
            budgets[key] = require_positive_int(raw_value, f"{source_label} node_reroute_budgets value", allow_decimal_text=False)
        except ValueError:
            raise ValueError(
                f"{source_label} node_reroute_budgets value must be a positive int: " + key
            )
    return budgets


def _materializer_preset_reroute_budgets(
    preset: Mapping[str, Any],
) -> Mapping[str, int]:
    """Read the graph PRESET's DECLARED per-kind reroute budgets (B)."""
    return _materializer_reroute_budgets(
        preset.get("node_reroute_budgets"),
        source_label="graph preset",
    )


def _materializer_constitutional_default_reroute_budget(repo: Path) -> int:
    payload = _load_yaml_mapping(
        repo / REROUTE_DEFAULTS_PATH,
        "Brick reroute defaults",
    )
    declared_by = str(payload.get("declared_by", "")).strip()
    provenance = str(payload.get("provenance", "")).strip()
    if declared_by != "smith":
        raise ValueError("reroute defaults must declare declared_by: smith")
    if provenance != ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT:
        raise ValueError(
            "reroute defaults must declare provenance: "
            + ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT
        )
    budget = payload.get("default_node_reroute_budget")
    try:
        return require_positive_int(
            budget,
            "reroute defaults default_node_reroute_budget",
            allow_decimal_text=False,
            error_text="must be a positive int",
        )
    except ValueError:
        raise ValueError("reroute defaults default_node_reroute_budget must be a positive int")


def _materializer_reroute_budget_cascade(
    preset: Mapping[str, Any],
    *,
    repo: Path,
    override_reroute_budgets: Any,
) -> tuple[dict[str, int], dict[str, str], int | None]:
    preset_budgets = _materializer_preset_reroute_budgets(preset)
    override_budgets = _materializer_reroute_budgets(
        override_reroute_budgets,
        source_label="per-building override",
    )
    declared_budgets: dict[str, int] = dict(preset_budgets)
    declared_budgets.update(override_budgets)
    budget_provenance: dict[str, str] = {
        key: ("per-building" if key in override_budgets else "preset-default")
        for key in declared_budgets
    }
    default_budget = (
        None
        if preset_budgets
        else _materializer_constitutional_default_reroute_budget(repo)
    )
    return declared_budgets, budget_provenance, default_budget


def _materializer_apply_constitutional_default_reroute_budget(
    node: dict[str, Any],
    *,
    default_budget: int | None,
) -> None:
    """Stamp the Smith-declared fallback budget on one node when no value exists."""
    if default_budget is None:
        return
    if node.get("node_reroute_budget") is not None or node.get("reroute_budget") is not None:
        return
    node["node_reroute_budget"] = default_budget
    node["node_reroute_budget_provenance"] = ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT


def _materializer_closure_policy(
    raw: Any,
    *,
    building_slug: str,
) -> Mapping[str, Any] | None:
    """Validate + resolve a DECLARED closure routing policy (A).

    The HUMAN route author declares ``closure_transition_target_policy`` as a
    mapping of concern_kind -> {action, [target_step_template_ref]}. Support copies
    it onto the fan-in closure node, resolving any declared
    ``target_step_template_ref`` to that kind's runtime node_id
    (``<building_slug>-<kind_slug>``) so the policy target resolves to an existing
    budgeted node. Support invents no concern_kind, no action, and no target; a
    declaration that omits this returns None and the materializer fails closed at
    the closure node. The same validation runs for the PRESET-declared policy and
    a per-Building OVERRIDE policy.
    """
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError(
            "closure_transition_target_policy must be a mapping of "
            "concern_kind -> declared routing row"
        )
    policy: dict[str, Any] = {}
    for raw_kind, raw_row in raw.items():
        concern_kind = str(raw_kind).strip()
        if not concern_kind:
            raise ValueError("closure_transition_target_policy concern_kind must be non-empty text")
        if not isinstance(raw_row, Mapping):
            raise ValueError(
                f"closure_transition_target_policy.{concern_kind} must be a routing row mapping"
            )
        row: dict[str, Any] = {}
        for field, value in raw_row.items():
            field_name = str(field).strip()
            if field_name == "target_step_template_ref":
                target_ref = str(value).strip()
                if not target_ref:
                    raise ValueError(
                        f"closure_transition_target_policy.{concern_kind}.target_step_template_ref "
                        "must be non-empty text"
                    )
                kind_slug = _materializer_step_template_slug(target_ref)
                row["target_ref"] = f"{building_slug}-{kind_slug}"
            else:
                row[field_name] = value
        policy[concern_kind] = row
    return policy


def _materializer_preset_closure_policy(
    preset: Mapping[str, Any],
    *,
    building_slug: str,
) -> Mapping[str, Any] | None:
    """Read + resolve the graph PRESET's DECLARED closure routing policy (A)."""
    return _materializer_closure_policy(
        preset.get("closure_transition_target_policy"),
        building_slug=building_slug,
    )


def _composition_node_reroute_budgets(
    node_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, int]:
    budgets: dict[str, int] = {}
    for record in node_records:
        raw_budget = record.get("node_reroute_budget")
        if raw_budget is None:
            raw = record.get("raw")
            if isinstance(raw, Mapping):
                raw_budget = raw.get("node_reroute_budget", raw.get("reroute_budget"))
        if raw_budget is None:
            continue
        brick_ref = str(record.get("brick_ref", "")).strip()
        if not brick_ref:
            continue
        try:
            budgets[brick_ref] = require_positive_int(
                raw_budget,
                f"composition node_reroute_budget {brick_ref}",
            )
        except ValueError:
            continue
    return budgets


def _composition_direct_caller_provenance(*, value: Any, provenance: Any) -> Any:
    """Stamp explicit per-Building provenance for a direct-caller route-policy value.

    The resolver no longer auto-labels absent provenance (fail-closed). When the
    caller/COO declares a route-policy VALUE directly on the node passed to
    compose_building WITHOUT a provenance marker, that IS a per-Building HUMAN
    declaration -- so the legitimate direct-caller intake stamps "per-building"
    EXPLICITLY here. Behaviour preserved otherwise:
      * value absent -> provenance unchanged (no value, no stamp).
      * value present + provenance already present (e.g. a materializer-routed node,
        or a caller-supplied marker, including an invalid token) -> kept verbatim so
        the resolver still validates/fails-closed on it.
      * value present + provenance absent/blank -> "per-building".
    """

    if value is None:
        return provenance
    if provenance is None or (isinstance(provenance, str) and not provenance.strip()):
        return "per-building"
    return provenance


def _composition_node_field_with_provenance_fallback(
    record: Mapping[str, Any],
    *,
    value_key: str,
    provenance_key: str,
) -> tuple[Any, Any]:
    """Read a route-policy value + its provenance off a node record.

    Reads the top-level record key first (set by compose_building), falling back
    to ``record['raw']`` (the node dict the materializer stamped) -- the same
    fallback ``_composition_node_reroute_budgets`` uses, so the value and its
    provenance are read from the SAME source and never drift apart.
    """
    value = record.get(value_key)
    provenance = record.get(provenance_key)
    if value is None:
        raw = record.get("raw")
        if isinstance(raw, Mapping):
            value = raw.get(value_key)
            if provenance is None:
                provenance = raw.get(provenance_key)
    elif provenance is None:
        raw = record.get("raw")
        if isinstance(raw, Mapping):
            provenance = raw.get(provenance_key)
    return value, provenance


def _composition_resolve_route_policy_provenance(
    node_id: str,
    field: str,
    provenance: Any,
) -> str:
    """Resolve the recorded provenance for a carried route-policy value.

    FAIL-CLOSED (Smith ruling): EVERY route-policy value must carry an EXPLICIT
    HUMAN provenance. Two cases (support NEVER synthesizes the VALUE; this only
    labels its origin):
      * constitutional-default | preset-default | per-building -> recorded
        verbatim (the materializer stamped it from the Smith-declared reroute
        defaults file, preset default, or a per-Building override; the
        compose_building direct-caller intake stamps "per-building" explicitly
        for a value declared directly on the node).
      * absent (None / "") | "support" | any other token -> FAIL CLOSED. An absent
        provenance can no longer be auto-labeled per-building: a value with no
        explicit HUMAN provenance trail (or one literally claiming support, or an
        unrecognized marker) means support injected/mislabeled the value; reject
        (mechanism must never inject a Movement policy value, and every value must
        carry its origin).
    """
    text = str(provenance).strip() if provenance is not None else ""
    if text in _ROUTE_POLICY_PROVENANCE_VALUES:
        return text
    raise ValueError(
        f"node {node_id} carries {field} with non-HUMAN provenance {provenance!r} "
        "(must be constitutional-default | preset-default | per-building; "
        "absent/blank provenance is rejected fail-closed -- every route-policy "
        "value must carry explicit HUMAN provenance); support must not inject or "
        "mislabel a Movement policy value"
    )


def _composition_route_policy_provenance(
    node_records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Record per-node PROVENANCE for the route-policy values (A + B).

    For every node carrying a reroute budget and/or a closure routing policy, the
    declared value's PROVENANCE (constitutional-default | preset-default |
    per-building) is recorded so an auditor can confirm support did not synthesize
    it. The provenance is read off
    the node the materializer stamped; support records it verbatim and NEVER writes
    a "support" value. A value carried with no/invalid provenance is a FAIL-CLOSED
    bug (support would have injected it) -- the materializer already rejects that,
    but this assembly-time guard fails closed too rather than silently dropping a
    value's provenance.
    """
    by_node: dict[str, dict[str, str]] = {}
    for record in node_records:
        node_id = str(record.get("node_id") or record.get("step_ref") or "").strip()
        if not node_id:
            continue
        entry: dict[str, str] = {}
        budget_value, budget_provenance = _composition_node_field_with_provenance_fallback(
            record,
            value_key="node_reroute_budget",
            provenance_key="node_reroute_budget_provenance",
        )
        if budget_value is not None:
            entry["node_reroute_budget"] = _composition_resolve_route_policy_provenance(
                node_id, "node_reroute_budget", budget_provenance
            )
        policy_value, policy_provenance = _composition_node_field_with_provenance_fallback(
            record,
            value_key="closure_transition_target_policy",
            provenance_key="closure_transition_target_policy_provenance",
        )
        if policy_value is not None:
            entry["closure_transition_target_policy"] = (
                _composition_resolve_route_policy_provenance(
                    node_id, "closure_transition_target_policy", policy_provenance
                )
            )
        if entry:
            by_node[node_id] = entry
    if not by_node:
        return {}
    return {
        "by_node": by_node,
        "allowed_provenance": sorted(_ROUTE_POLICY_PROVENANCE_VALUES),
        "rule": (
            "route reroute budget + closure routing policy are HUMAN Movement "
            "decisions; support records but never synthesizes them (provenance is "
            "constitutional-default for Smith-declared reroute defaults, "
            "preset-default for a reusable preset default, or per-building for a "
            "per-Building override, NEVER support)"
        ),
    }
