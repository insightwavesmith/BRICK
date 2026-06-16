"""Agent non-binding transition-concern adoption for the dynamic walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
extraction + validation of the Agent-returned NON-BINDING transition_concern
(binding:false) nested in the closed AgentFact returned shape, the existing-node
target resolution, and the invalid-concern HOLD were lifted out of the
dynamic_walker god-module into this single-concern collaborator.

ζ7: the Agent PROPOSES (non-binding); support reads the proposal and resolves an
EXISTING-node target (it never invents a node). A malformed concern PAUSEs
(HOLD) instead of crashing the writer or adopting Movement.

Support mechanics only. Homes NO axis crossing (it consumes the canonical
validate_transition_concern_evidence contract of agent/return_fact.py). Judges no
success or quality; chooses no Movement.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from brick_protocol.agent.return_fact import validate_transition_concern_evidence
from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import _optional_text_value
from brick_protocol.support.operator.walker_hold import _build_hold


@dataclasses.dataclass(frozen=True)
class _TransitionConcernObservation:
    concern: Mapping[str, Any] | None = None
    invalid_reason: str = ""
    raw_concern: Mapping[str, Any] | None = None


# The admitted non-brick-node prefix for related_boundary_refs (agent/return_fact
# validate_transition_concern_evidence admits brick:/brick-/brick-boundary:/
# brick-instance: for Brick NODES, plus building-boundary: for the BUILDING
# boundary). A building-boundary: ref names NO Brick node; it is the explicit
# "no reroute intended" sentinel an Agent uses to RAISE a non-binding concern
# WITHOUT proposing a reroute address.
_NON_REROUTE_BOUNDARY_PREFIX = "building-boundary:"


@dataclasses.dataclass(frozen=True)
class _RerouteTargetClassification:
    """The reroute address(es) named by a concern, CLASSIFIED (not picked).

    The Agent PROPOSES (non-binding); support resolves the named
    related_boundary_refs against the EXISTING declared Brick nodes WITHOUT
    inventing one and WITHOUT guessing among several. The classification is:

    - ``single``      exactly one named ref remains after the source Brick node
                      is stripped -> ``target`` is that node (the happy path;
                      the machine adopts within budget/gate).
    - ``ambiguous``   two or more named refs remain after the source Brick node
                      is stripped -> NO single owner; the machine must NOT pick
                      one -> the caller HOLDs.
    - ``non_reroute`` no actionable Brick ref remains: either zero brick refs
                      resolve, the list is NON-EMPTY, and EVERY named ref is a
                      building-boundary: sentinel (no Brick node targeted), OR
                      stripping the source Brick node leaves no resolving Brick
                      node -> an EXPLICIT non-reroute concern -> the caller
                      WALKS ON (carry forward), it does NOT HOLD.
    - ``none``        zero named refs resolve while a concern IS present AND the
                      non_reroute carve-out does not apply (empty list, or a
                      brick-targeting ref that failed to resolve) -> the
                      unaddressable concern must NOT be silently dropped -> the
                      caller HOLDs.

    STRICT carve-out (Smith ruling): a brick-targeting ref that is NAMED but does
    NOT resolve to a declared Brick AND is NOT a building-boundary: sentinel is a
    GARBAGE/typo/stale address. When such an unresolvable ref CO-OCCURS with an
    otherwise-valid single resolving ref, the garbage must NOT be silently dropped
    to return ``single`` -> the classifier returns ``kind="none"`` with a DISTINCT
    ``hold_reason`` (``unresolvable_reroute_address``) so a human sees the bad
    address. This is checked BEFORE the ``len(resolved)==1 -> single`` branch.

    ``resolved`` preserves declared-order, de-duplicated resolving nodes (for
    HOLD evidence). ``target`` is non-empty ONLY for ``single``. ``hold_reason``
    is non-empty ONLY when the classifier wants the caller to stamp a SPECIFIC
    reason on the HOLD (otherwise the caller derives the reason from ``kind``).
    """

    kind: str
    target: str = ""
    resolved: tuple[str, ...] = ()
    hold_reason: str = ""


def _classify_reroute_target(
    concern: Mapping[str, Any],
    *,
    declared_bricks: set[str],
    source_brick_ref: str = "",
) -> _RerouteTargetClassification:
    """Resolve ALL named reroute addresses and classify.

    Support reads the concern's related_boundary_refs and keeps only those that
    resolve to an EXISTING Brick node in this Building (it never invents a node).
    It does NOT return-first: when several resolve, that is a seam with no single
    owner and the machine must NOT choose one; when none resolve (but a concern
    is present), the unaddressable concern must NOT be silently dropped.

    Carve-out (Smith ruling): a NON-EMPTY related_boundary_refs whose refs are
    ALL building-boundary: sentinels (NO Brick-targeting ref) is an EXPLICIT
    non-reroute concern -- the Agent raised a concern but proposed no reroute
    address -- and is classified ``non_reroute`` so the caller WALKS ON (the old
    engine did) instead of HOLDing on an absent address. The walk-on is allowed
    ONLY when the list is non-empty AND every ref is building-boundary:-prefixed;
    an empty list, or any non-building-boundary ref that fails to resolve, still
    falls through to ``none`` (HOLD).

    STRICT carve-out (Smith ruling): an UNRESOLVABLE brick-targeting ref (named,
    not a declared Brick, not a building-boundary: sentinel = a garbage/typo/stale
    address) must NOT be silently dropped even when a valid ref also resolves. If
    ANY unresolvable ref is present, classify ``none`` with the DISTINCT
    ``hold_reason`` ``unresolvable_reroute_address`` BEFORE the
    ``len(resolved)==1 -> single`` branch, so a human sees the bad address. A pure
    single valid ref (no garbage) still resolves to ``single``; a valid ref beside
    a building-boundary: sentinel still resolves to ``single`` (the sentinel is
    not garbage).

    Self-reroute carve-out: when ``source_brick_ref`` is present, strip that
    SAME Brick node before classifying. A source-only list becomes
    ``non_reroute``; source+one other declared Brick becomes ``single`` for the
    other Brick; source+two or more other declared Bricks remains ``ambiguous``.
    """

    refs = concern.get("related_boundary_refs")
    resolved: list[str] = []
    seen: set[str] = set()
    text_refs: list[str] = []
    if isinstance(refs, list):
        for ref in refs:
            brick_ref = _optional_text_value(ref)
            if not brick_ref:
                continue
            text_refs.append(brick_ref)
            if brick_ref in declared_bricks and brick_ref not in seen:
                seen.add(brick_ref)
                resolved.append(brick_ref)
    # STRICT (Smith ruling): a named, non-resolving, non-building-boundary: ref is
    # a garbage brick-targeting address. When such garbage CO-OCCURS with an
    # otherwise-valid resolving ref, today the garbage is silently dropped and the
    # valid ref returns ``single``. It must instead HOLD with the DISTINCT
    # ``unresolvable_reroute_address`` reason so a human sees the bad address.
    # Checked BEFORE the ``len(resolved)==1 -> single`` branch. (Pure garbage with
    # NO resolving ref -- C8 / mixed sentinel+garbage -- already HOLDs via the
    # final ``none`` path with ``no_resolving_reroute_address`` and is untouched.)
    unresolvable = [
        ref
        for ref in text_refs
        if ref not in resolved
        and not ref.startswith(_NON_REROUTE_BOUNDARY_PREFIX)
    ]
    if unresolvable and resolved:
        return _RerouteTargetClassification(
            kind="none",
            resolved=tuple(resolved),
            hold_reason="unresolvable_reroute_address",
        )
    classified_resolved = [
        brick_ref
        for brick_ref in resolved
        if not source_brick_ref or brick_ref != source_brick_ref
    ]
    source_was_stripped = (
        bool(source_brick_ref) and len(classified_resolved) != len(resolved)
    )
    if not classified_resolved and source_was_stripped:
        return _RerouteTargetClassification(
            kind="non_reroute",
            resolved=(),
        )
    if len(classified_resolved) == 1:
        return _RerouteTargetClassification(
            kind="single",
            target=classified_resolved[0],
            resolved=(classified_resolved[0],),
        )
    if len(classified_resolved) >= 2:
        return _RerouteTargetClassification(
            kind="ambiguous",
            resolved=tuple(classified_resolved),
        )
    # Zero brick refs resolved. Walk on ONLY for an explicit non-reroute concern:
    # a non-empty list where EVERY ref is a building-boundary: sentinel.
    if text_refs and all(
        ref.startswith(_NON_REROUTE_BOUNDARY_PREFIX) for ref in text_refs
    ):
        return _RerouteTargetClassification(kind="non_reroute", resolved=())
    return _RerouteTargetClassification(kind="none", resolved=())


def _transition_concern_from_step_result(
    step_result: BuildingRunSupportResult,
) -> Mapping[str, Any] | None:
    return _transition_concern_observation_from_step_result(step_result).concern


def _transition_concern_observation_from_step_result(
    step_result: BuildingRunSupportResult,
) -> _TransitionConcernObservation:
    """Extract the Agent-returned non-binding transition_concern, if present.

    The concern is NESTED in the closed AgentFact ``returned`` shape under
    ``transition_concern_evidence``; AgentFact stays closed (received_work,
    returned). binding must be false (an unbinding proposal only).
    """

    returned = getattr(step_result.adapter_result, "returned_value", None)
    if not isinstance(returned, Mapping):
        return _TransitionConcernObservation()
    concern = returned.get("transition_concern_evidence")
    if concern in (None, False, ""):
        return _TransitionConcernObservation()
    if not isinstance(concern, Mapping):
        return _TransitionConcernObservation(
            invalid_reason="transition_concern_evidence must be a JSON-compatible mapping when present"
        )
    try:
        checked = validate_transition_concern_evidence(concern)
    except (TypeError, ValueError) as exc:
        return _TransitionConcernObservation(
            invalid_reason=str(exc),
            raw_concern=concern,
        )
    return _TransitionConcernObservation(concern=checked)


def _build_invalid_transition_concern_hold(
    *,
    building_id: str,
    plan_ref: str,
    source_step_ref: str,
    source_brick_ref: str,
    concern_observation: _TransitionConcernObservation,
    declared_bricks: set[str],
    cascade_depth: int,
    parent_reroute_ref: str,
    adoption_sequence_number: int,
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
    step: Mapping[str, Any],
    step_result: BuildingRunSupportResult,
) -> Mapping[str, Any]:
    raw_concern = concern_observation.raw_concern or {}
    target_brick = _proposed_target_brick(raw_concern, declared_bricks=declared_bricks) or source_brick_ref
    raw_concern_ref = raw_concern.get("concern_ref") if isinstance(raw_concern, Mapping) else None
    concern_ref = raw_concern_ref if isinstance(raw_concern_ref, str) and raw_concern_ref.strip() else ""
    if not concern_ref:
        concern_ref = f"transition-concern:invalid:{source_step_ref.replace(':', '-')}"
    concern_for_hold = {"concern_ref": concern_ref}
    return _build_hold(
        building_id=building_id,
        plan_ref=plan_ref,
        source_step_ref=source_step_ref,
        source_brick_ref=source_brick_ref,
        target_brick=target_brick,
        concern=concern_for_hold,
        cascade_depth=cascade_depth,
        parent_reroute_ref=parent_reroute_ref,
        adoption_sequence_number=adoption_sequence_number,
        node_budget=node_budget.get(target_brick, 0),
        attempt_number=node_landings.get(target_brick, 0),
        budget_exhausted=False,
        hold_reason="invalid_transition_concern_evidence",
        step=step,
        step_result=step_result,
    )


def _proposed_target_brick(
    concern: Mapping[str, Any],
    *,
    declared_bricks: set[str],
) -> str | None:
    """Return the SINGLE EXISTING-node reroute target, or None.

    Compatibility shape (``str | None``) over the classifier: it returns the
    target ONLY when exactly one named ref resolves to an EXISTING Brick node
    (the happy path). It returns None when the named refs are ambiguous (>=2
    resolve) or unresolved (0 resolve) -- support never invents a node and never
    picks one among several. Callers that must HOLD on the ambiguous/none seams
    (the dynamic walk) consume ``_classify_reroute_target`` directly.
    """

    classification = _classify_reroute_target(concern, declared_bricks=declared_bricks)
    if classification.kind == "single":
        return classification.target
    return None
