"""Per-step Brick/Link row readers + gate disposition for the dynamic walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
per-step row builders, the declared-field-set observation, the declared gate
disposition read (template/default => adopt, human/coo => pause), and the
declared replay-scope reader were lifted out of the dynamic_walker god-module
into this single-concern collaborator. It READS declared rows and projects field
SETS as facts; it authors no gate and chooses no Movement.

Support mechanics only. Homes NO axis crossing (it consumes the canonical
transition-lifecycle author-prefix contract of brick_protocol/link/transition.py to classify a
declared gate). Judges no success or quality.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from brick_protocol.link.gate import (
    AUTO_ADOPT_GATE_REFS,
    HUMAN_DISPOSITION_GATE_REFS,
)
from brick_protocol.link.transition import (
    TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES as _HUMAN_AUTHOR_PREFIXES,
)
from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import _optional_text_value
from brick_protocol.support.recording.walker_evidence import (
    build_structured_field_observation,
)

# Gate-adoption authority refs (ζ7). A completion edge whose declared gate is the
# template/default-transition gate AUTO-ADOPTS the agent's non-binding proposal. A
# human:/coo: gate PAUSEs for a caller/COO disposition. Support reads the declared
# gate; it never authors one.
_TEMPLATE_GATE_REFS: frozenset[str] = AUTO_ADOPT_GATE_REFS
_HUMAN_GATE_REFS: frozenset[str] = HUMAN_DISPOSITION_GATE_REFS
_TEMPLATE_AUTHOR_PREFIXES: tuple[str, ...] = ("template:",)


def _brick_instance_ref_from_linear_step(step: Mapping[str, Any]) -> str:
    rows = step.get("rows")
    if not isinstance(rows, list):
        raise ValueError("projected graph step missing rows")
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            ref = _optional_text_value(row.get("brick_instance_ref"))
            if ref:
                return ref
    raise ValueError("projected graph step missing Brick row brick_instance_ref")


def _brick_row_from_linear_step(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        raise ValueError("projected graph step missing rows")
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            return row
    raise ValueError("projected graph step missing Brick row")


def _split_field_names(value: Any) -> list[str]:
    """Split a declared/required field-shape string into field-name tokens.

    A required_return_shape is a comma/whitespace separated list of declared
    field names (e.g. "observed_evidence, not_proven"). This is a mechanical
    tokenization, not a judgment.
    """

    text = _optional_text_value(value)
    if not text:
        return []
    names: list[str] = []
    for chunk in text.replace(";", ",").split(","):
        token = chunk.strip()
        if token:
            names.append(token)
    return names


def _brick_required_fields(step: Mapping[str, Any]) -> list[str]:
    """Fields the BRICK declared as the required return shape (an observation)."""

    brick_row = _brick_row_from_linear_step(step)
    return _split_field_names(brick_row.get("required_return_shape"))


def _observed_returned_fields(step_result: BuildingRunSupportResult) -> list[str]:
    """Top-level keys the AGENT actually returned (an observation, no judgment).

    Read from the closed AgentFact ``returned`` mapping; AgentFact stays closed.
    """

    returned = getattr(step_result.adapter_result, "returned_value", None)
    if not isinstance(returned, Mapping):
        return []
    return [str(key) for key in returned.keys()]


def _gate_required_fields(step: Mapping[str, Any]) -> list[str]:
    """Fields the GATE/route declared as required (an observation, no judgment).

    Read from the completing node's Link row gate declaration
    (declared_return_fields on the gate or route_replay_plan, if present). Absent
    => the gate declared no extra field requirement (empty set). Support reads the
    DECLARED requirement; it authors none.
    """

    link_row = _link_row_from_linear_step(step)
    for container_key in ("transition_authoring", "route_replay_plan"):
        container = link_row.get(container_key)
        if isinstance(container, Mapping):
            declared = container.get("required_return_fields")
            if declared is not None:
                return [str(name) for name in _coerce_name_list(declared)]
    declared = link_row.get("gate_required_return_fields")
    if declared is not None:
        return [str(name) for name in _coerce_name_list(declared)]
    return []


def _coerce_name_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return _split_field_names(value)
    if isinstance(value, (list, tuple)):
        names: list[str] = []
        for item in value:
            token = _optional_text_value(item)
            if token:
                names.append(token)
        return names
    return []


def _structured_field_observation_for_step(
    step: Mapping[str, Any],
    step_result: BuildingRunSupportResult,
) -> Mapping[str, Any]:
    """Build the structured field-set observation for a reroute/HOLD boundary.

    Pure FACTS: the field SETS (Brick declared / Agent observed / gate required)
    and the set deltas. NO failing_axis label, NO fault/failed/success verdict --
    attribution is the reader's inference.
    """

    return build_structured_field_observation(
        brick_required_fields=_brick_required_fields(step),
        observed_fields=_observed_returned_fields(step_result),
        gate_required_fields=_gate_required_fields(step),
    )


def _link_row_from_linear_step(step: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        raise ValueError("projected graph step missing rows")
    link_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Link"]
    if len(link_rows) != 1:
        raise ValueError("projected graph step must carry exactly one Link row")
    return link_rows[0]


def _gate_disposition_for_step(step: Mapping[str, Any]) -> str:
    """Return 'adopt' (template/default gate) or 'pause' (human/coo gate).

    The disposition is read from the completing node's declared Link gate
    (declared_gate_refs and/or transition_authoring.author_ref). Support reads
    the DECLARED gate; it authors none (ζ7). A human:/coo: gate PAUSEs; the
    template:/default-transition gate AUTO-ADOPTS.
    """

    link_row = _link_row_from_linear_step(step)
    gate_refs = link_row.get("declared_gate_refs")
    if isinstance(gate_refs, list):
        refs = {str(ref).strip() for ref in gate_refs if str(ref).strip()}
        if refs & _HUMAN_GATE_REFS:
            return "pause"
        if refs & _TEMPLATE_GATE_REFS:
            return "adopt"
    authoring = link_row.get("transition_authoring")
    if isinstance(authoring, Mapping):
        author_ref = _optional_text_value(authoring.get("author_ref")) or ""
        if author_ref.startswith(_HUMAN_AUTHOR_PREFIXES):
            return "pause"
        if author_ref.startswith(_TEMPLATE_AUTHOR_PREFIXES):
            return "adopt"
    route_plan = link_row.get("route_replay_plan")
    if isinstance(route_plan, Mapping):
        author_ref = _optional_text_value(route_plan.get("author_ref")) or ""
        if author_ref.startswith(_HUMAN_AUTHOR_PREFIXES):
            return "pause"
        if author_ref.startswith(_TEMPLATE_AUTHOR_PREFIXES):
            return "adopt"
    # No declared gate authority -> default-transition template adoption (the
    # autonomy dial: omitting a human gate is a template-authored adoption).
    return "adopt"


def _adopted_by_ref(step: Mapping[str, Any]) -> str:
    link_row = _link_row_from_linear_step(step)
    authoring = link_row.get("transition_authoring")
    if isinstance(authoring, Mapping):
        author_ref = _optional_text_value(authoring.get("author_ref"))
        if author_ref:
            return author_ref
    route_plan = link_row.get("route_replay_plan")
    if isinstance(route_plan, Mapping):
        author_ref = _optional_text_value(route_plan.get("author_ref"))
        if author_ref:
            return author_ref
    return "template:default-transition"


def _declared_replay_scope_step_refs(
    step: Mapping[str, Any],
    *,
    target_brick: str,
    step_ref_by_brick: Mapping[str, str],
) -> list[str]:
    """Return declared replay-segment step refs for an adopted reroute.

    The replay scope is the completing node's Link-owned
    route_replay_plan.replay_segment_refs (declared, not chosen by support),
    restricted to existing nodes. Walking THROUGH these as forward replay does
    NOT consume their reroute budget (rule #8). The target landing itself is
    appended by the caller; replay scope excludes the target.
    """

    link_row = _link_row_from_linear_step(step)
    route_plan = link_row.get("route_replay_plan")
    if not isinstance(route_plan, Mapping):
        return []
    refs = route_plan.get("replay_segment_refs")
    if not isinstance(refs, list):
        return []
    scope: list[str] = []
    for ref in refs:
        brick_ref = _optional_text_value(ref)
        if not brick_ref or brick_ref == target_brick:
            continue
        target_step = step_ref_by_brick.get(brick_ref)
        if target_step is not None and target_step not in scope:
            scope.append(target_step)
    return scope
