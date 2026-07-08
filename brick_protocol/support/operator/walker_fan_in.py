"""Fan-out scheduling + fan-in wait-all observation/HOLD (dynamic walker).

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
graph fan-topology readers, the successor splice into the live queue, and the
fan-in wait-all state machine (ready / defer / hold) plus its observation and
HOLD record builders were lifted out of the dynamic_walker god-module into this
single-concern collaborator. It decides fan-in readiness for the live frontier
and pauses on a missing fan-in source; opt-in pool dispatch lives in
walker_kernel.py, not in this fan-in observation helper.

Support mechanics only. Homes NO axis crossing (it reads declared graph edges via
the plan_graph projection and emits the field-set observation via the recording
contract). Judges no success or quality.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.plan_graph import (
    _graph_declared_edges,
    _graph_fan_in_sibling_independence_by_target_step_ref,
    _graph_fan_in_sources_by_target_step_ref,
    _graph_fan_out_targets_by_source_step_ref,
)
from brick_protocol.support.operator.primitives import _optional_text_value
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
)
from brick_protocol.support.recording.walker_evidence import (
    build_structured_field_observation,
)


def _graph_has_fan_groups(graph_context: Mapping[str, Any] | None) -> bool:
    return bool(
        _graph_fan_out_targets_by_source_step_ref(graph_context)
        or _graph_fan_in_sources_by_target_step_ref(graph_context)
    )


def _graph_successor_step_refs_by_source_step_ref(
    graph_context: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    successors_by_source: dict[str, list[str]] = {}
    for edge in _graph_declared_edges(graph_context):
        source = _optional_text_value(edge.get("source_step_ref"))
        target = _optional_text_value(edge.get("target_step_ref"))
        if not source or not target:
            continue
        successors = successors_by_source.setdefault(source, [])
        if target not in successors:
            successors.append(target)
    return {source: tuple(successors) for source, successors in successors_by_source.items()}


def _graph_root_step_refs(
    forward_order: list[str],
    graph_context: Mapping[str, Any] | None,
) -> list[str]:
    targets = {
        target
        for edge in _graph_declared_edges(graph_context)
        for target in [_optional_text_value(edge.get("target_step_ref"))]
        if target
    }
    roots = [step_ref for step_ref in forward_order if step_ref not in targets]
    if not roots:
        raise ValueError("graph fan topology has no root step to seed")
    return roots


def _splice_declared_successors(
    attempt_queue: list[dict[str, Any]],
    *,
    insert_at: int,
    source_step_ref: str,
    cascade_depth: int,
    parent_reroute_ref: str,
    successors_by_source: Mapping[str, tuple[str, ...]],
    scheduled_fan_steps: set[tuple[str, int]],
) -> None:
    successors = successors_by_source.get(source_step_ref, ())
    if not successors:
        return
    appended: list[dict[str, Any]] = []
    for target_step_ref in successors:
        key = (target_step_ref, cascade_depth)
        if key in scheduled_fan_steps:
            continue
        scheduled_fan_steps.add(key)
        appended.append(
            {
                "step_ref": target_step_ref,
                "cascade_depth": cascade_depth,
                "parent_reroute_ref": parent_reroute_ref,
                "is_reroute_landing": False,
            }
        )
    if appended:
        attempt_queue[insert_at:insert_at] = appended


def _fan_in_wait_all_state(
    *,
    step_ref: str,
    cascade_depth: int,
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    completed_fan_steps: set[tuple[str, int]],
    running_fan_steps: set[tuple[str, int]],
    held_fan_steps: set[tuple[str, int]],
    pending_queue: list[dict[str, Any]],
    fan_in_deferrals: dict[tuple[str, int], int],
) -> tuple[str, Mapping[str, Any] | None]:
    incoming_sources = fan_in_sources_by_target.get(step_ref, ())
    if not incoming_sources:
        return "ready", None
    observed_sources = [
        source
        for source in incoming_sources
        if (source, cascade_depth) in completed_fan_steps
        and (source, cascade_depth) not in held_fan_steps
    ]
    missing_sources = [source for source in incoming_sources if source not in observed_sources]
    if not missing_sources:
        return "ready", None
    pending_sources = {
        item.get("step_ref")
        for item in pending_queue
        if int(item.get("cascade_depth", 0)) == cascade_depth
        and item.get("step_ref") in missing_sources
    }
    running_sources = {
        source
        for source in missing_sources
        if (source, cascade_depth) in running_fan_steps
    }
    wait_key = (step_ref, cascade_depth)
    if (pending_sources or running_sources) and fan_in_deferrals.get(wait_key, 0) < len(
        incoming_sources
    ):
        fan_in_deferrals[wait_key] = fan_in_deferrals.get(wait_key, 0) + 1
        return "defer", None
    return "hold", _build_fan_in_wait_all_observation(
        target_step_ref=step_ref,
        cascade_depth=cascade_depth,
        required_source_step_refs=incoming_sources,
        observed_source_step_refs=observed_sources,
        missing_source_step_refs=missing_sources,
        pending_source_step_refs=sorted(str(source) for source in pending_sources),
    )


def _fan_in_wait_all_observations_for_held_source(
    *,
    held_source_step_ref: str,
    cascade_depth: int,
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    completed_fan_steps: set[tuple[str, int]],
    held_fan_steps: set[tuple[str, int]],
) -> list[Mapping[str, Any]]:
    observations: list[Mapping[str, Any]] = []
    for target_step_ref, incoming_sources in fan_in_sources_by_target.items():
        if held_source_step_ref not in incoming_sources:
            continue
        observed_sources = [
            source
            for source in incoming_sources
            if (source, cascade_depth) in completed_fan_steps
            and (source, cascade_depth) not in held_fan_steps
        ]
        missing_sources = [
            source for source in incoming_sources if source not in observed_sources
        ]
        if not missing_sources:
            continue
        observations.append(
            _build_fan_in_wait_all_observation(
                target_step_ref=target_step_ref,
                cascade_depth=cascade_depth,
                required_source_step_refs=incoming_sources,
                observed_source_step_refs=observed_sources,
                missing_source_step_refs=missing_sources,
                pending_source_step_refs=[],
            )
        )
    return observations


def _build_fan_in_wait_all_observation(
    *,
    target_step_ref: str,
    cascade_depth: int,
    required_source_step_refs: Iterable[str],
    observed_source_step_refs: Iterable[str],
    missing_source_step_refs: Iterable[str],
    pending_source_step_refs: Iterable[str],
) -> Mapping[str, Any]:
    required = list(dict.fromkeys(str(ref) for ref in required_source_step_refs if str(ref)))
    observed = list(dict.fromkeys(str(ref) for ref in observed_source_step_refs if str(ref)))
    missing = list(dict.fromkeys(str(ref) for ref in missing_source_step_refs if str(ref)))
    pending = list(dict.fromkeys(str(ref) for ref in pending_source_step_refs if str(ref)))
    return {
        "kind": "fan_in_wait_all_observation",
        "target_step_ref": target_step_ref,
        "cascade_depth": cascade_depth,
        "required_source_step_refs": required,
        "observed_source_step_refs": observed,
        "missing_source_step_refs": missing,
        "pending_source_step_refs": pending,
        "structured_field_observation": build_structured_field_observation(
            brick_required_fields=required,
            observed_fields=observed,
            gate_required_fields=required,
        ),
        "proof_limits": list(FAN_TOPOLOGY_PROOF_LIMITS),
        "not_proven": list(FAN_TOPOLOGY_NOT_PROVEN),
    }


def _build_fan_in_wait_all_hold(
    *,
    building_id: str,
    plan_ref: str,
    target_step_ref: str,
    target_brick: str,
    cascade_depth: int,
    observation: Mapping[str, Any],
    step_results: list[BuildingRunSupportResult],
) -> Mapping[str, Any]:
    required_sources = tuple(
        str(ref)
        for ref in observation.get("required_source_step_refs", [])
        if str(ref)
    )
    source_result = _latest_completed_source_result(step_results, required_sources)
    source_step_ref = (
        source_result.preparation.step_rows.step_ref
        if source_result is not None
        else ""
    )
    source_brick_ref = (
        source_result.preparation.brick_instance_ref
        if source_result is not None
        else ""
    )
    return {
        "kind": "fan_in_wait_all_hold",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "target_step_ref": target_step_ref,
        "target_brick": target_brick,
        "pause_source_step_ref": source_step_ref,
        "source_brick_ref": source_brick_ref,
        "pending_target_ref": target_brick,
        "cascade_depth": cascade_depth,
        "disposition_required": True,
        "hold_reason": "fan_in_wait_all_missing_source",
        "required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_state": "paused",
        "fan_in_wait_all_observation": dict(observation),
        "proof_limits": list(FAN_TOPOLOGY_PROOF_LIMITS),
        "not_proven": list(FAN_TOPOLOGY_NOT_PROVEN),
    }


def _fan_in_cohort_replay_plan(
    *,
    target_step_ref: str,
    graph_context: Mapping[str, Any] | None,
    step_ref_by_brick: Mapping[str, str],
    already_scoped_step_refs: Iterable[str],
) -> tuple[list[str], list[str], list[Mapping[str, Any]]]:
    """Cohort re-verification for a reroute landing or replayed fan-in source.

    Knot ③ (stale-pass): when a reroute LANDS on a node X, X or a declared
    replay-scope node may be a fan-in SOURCE. The prior PASSes of that source's
    SIBLING fan-in sources may now be STALE (a fix in one lane can invalidate
    another). Brick models movement topology only (no node-to-node
    data-dependency graph), so the machine CANNOT know which siblings went
    stale. SAFE answer: re-verify the WHOLE fan-in COHORT (every source sharing
    the trigger source's fan-in target) as FORWARD REPLAY. A sibling is SKIPPED
    only if a HUMAN declared ``sibling_independence`` for it on the fan-in group;
    support READS that vouch and never decides independence. Absent vouch =>
    re-verify ALL (conservative).

    Returns ``(cohort_replay_step_refs, cohort_skipped_step_refs, cohort_records)``:
      - ``cohort_replay_step_refs``: sibling SOURCE step_refs to append to the
        live queue as FORWARD REPLAY items (``is_reroute_landing: False`` so they
        are BUDGET-FREE -- they do NOT increment node_landings / consume reroute
        budget; only the actual reroute LANDING does).
      - ``cohort_skipped_step_refs``: sibling SOURCE step_refs the HUMAN vouched
        as independent (NOT re-walked). The caller carries their PRIOR pass
        forward at the reroute cascade-depth so the shared fan-in target's
        wait-all is satisfied without re-running them.
      - ``cohort_records``: one auditable observation per sibling recording
        whether it was re-verified or SKIPPED, and for each skip the
        ``sibling_independence`` vouch ref(s).
    The trigger source is excluded; anything already in
    ``already_scoped_step_refs`` (the target + its declared replay scope) is not
    re-appended. Records distinguish the reroute landing from the actual
    ``cohort_trigger_step_ref`` because the trigger can be downstream in the
    replay scope.
    """

    sources_by_target = _graph_fan_in_sources_by_target_step_ref(graph_context)
    if not sources_by_target:
        return [], [], []
    vouch_by_target = _graph_fan_in_sibling_independence_by_target_step_ref(graph_context)
    brick_ref_by_step = {step: brick for brick, step in step_ref_by_brick.items()}
    already_scoped = {ref for ref in already_scoped_step_refs if ref}
    trigger_step_refs: list[str] = []
    for ref in (target_step_ref, *already_scoped_step_refs):
        if ref and ref not in trigger_step_refs:
            trigger_step_refs.append(ref)
    # Find every fan-in target for which the landing or a declared replay-scope
    # node is a source. The landing remains the Link reroute target; the trigger
    # identifies the fan-in source whose sibling cohort is being evaluated.
    cohort_target_triggers: list[tuple[str, str]] = []
    for trigger_step_ref in trigger_step_refs:
        for fan_in_target, sources in sources_by_target.items():
            if trigger_step_ref in sources and (
                fan_in_target,
                trigger_step_ref,
            ) not in cohort_target_triggers:
                cohort_target_triggers.append((fan_in_target, trigger_step_ref))
    if not cohort_target_triggers:
        return [], [], []

    # The vouch is PER fan-in target. A sibling source may belong to SEVERAL of
    # X's shared fan-in targets, and the human may have vouched independence on
    # SOME of them and NOT others. RE-VERIFY WINS: a sibling is re-verified if it
    # is NOT vouched-skip on AT LEAST ONE shared target; it is skipped ONLY if
    # vouched-skip on EVERY shared target. A fresh pass is always safe and feeds
    # every shared target's wait-all, so carrying a per-target vouch onto a target
    # where the human declared nothing would be support DECIDING independence.
    #
    # Resolve, per sibling, the FULL set of (shared target, vouch-ref-or-None)
    # decisions FIRST, then emit ONE truthful record per sibling carrying the
    # final disposition. In the single-target case this is exactly one record per
    # sibling with the same shape the prior implementation emitted.
    sibling_order: list[str] = []
    skip_targets: dict[str, list[tuple[str, str, str]]] = {}  # sibling -> [(target, trigger, vouch_ref)]
    reverify_targets: dict[str, list[tuple[str, str]]] = {}  # sibling -> [(target, trigger) with NO vouch]
    for fan_in_target, trigger_step_ref in cohort_target_triggers:
        siblings = [
            source
            for source in sources_by_target[fan_in_target]
            if source != trigger_step_ref
        ]
        # Resolve the human vouch for THIS target into the set of sibling
        # step_refs to skip. The vouch may name a sibling by step_ref OR by brick
        # ref (author convenience); both resolve to a sibling step_ref.
        vouch_refs = vouch_by_target.get(fan_in_target, ())
        skip_step_refs: dict[str, str] = {}
        for vouch_ref in vouch_refs:
            resolved = None
            if vouch_ref in siblings:
                resolved = vouch_ref
            elif vouch_ref in step_ref_by_brick:
                candidate = step_ref_by_brick[vouch_ref]
                if candidate in siblings:
                    resolved = candidate
            if resolved is not None:
                skip_step_refs[resolved] = vouch_ref
        for sibling in siblings:
            if sibling not in skip_targets:
                sibling_order.append(sibling)
                skip_targets[sibling] = []
                reverify_targets[sibling] = []
            if sibling in skip_step_refs:
                skip_targets[sibling].append(
                    (fan_in_target, trigger_step_ref, skip_step_refs[sibling])
                )
            else:
                reverify_targets[sibling].append((fan_in_target, trigger_step_ref))

    replay_refs: list[str] = []
    skipped_refs: list[str] = []
    records: list[Mapping[str, Any]] = []
    for sibling in sibling_order:
        sibling_brick = brick_ref_by_step.get(sibling, "")
        reverify_for = reverify_targets[sibling]
        skip_for = skip_targets[sibling]
        if not reverify_for:
            # Vouched-skip on EVERY shared target -> skip. Record the fan-in
            # target whose vouch governs the skip (the first one) and its vouch
            # ref. (Single-target case: this is the lone target + lone vouch.)
            governing_target, governing_trigger, vouch_ref = skip_for[0]
            if sibling not in skipped_refs:
                skipped_refs.append(sibling)
            record: dict[str, Any] = {
                "kind": "fan_in_cohort_sibling_disposition",
                "fan_in_target_step_ref": governing_target,
                "reroute_target_step_ref": target_step_ref,
                "reroute_landing_step_ref": target_step_ref,
                "cohort_trigger_step_ref": governing_trigger,
                "sibling_source_step_ref": sibling,
                "sibling_source_brick_ref": sibling_brick,
                "disposition": "skipped",
                "sibling_independence_vouch_ref": vouch_ref,
                "proof_limits": list(FAN_TOPOLOGY_PROOF_LIMITS),
                "not_proven": list(FAN_TOPOLOGY_NOT_PROVEN),
            }
        else:
            # NOT vouched on at least one shared target -> re-verify (wins). Record
            # against the first re-verify target. (Single-target case: this is the
            # lone target, sibling_independence_vouch_ref None, identical shape.)
            governing_target, governing_trigger = reverify_for[0]
            if sibling not in already_scoped and sibling not in replay_refs:
                replay_refs.append(sibling)
            record = {
                "kind": "fan_in_cohort_sibling_disposition",
                "fan_in_target_step_ref": governing_target,
                "reroute_target_step_ref": target_step_ref,
                "reroute_landing_step_ref": target_step_ref,
                "cohort_trigger_step_ref": governing_trigger,
                "sibling_source_step_ref": sibling,
                "sibling_source_brick_ref": sibling_brick,
                "disposition": "re_verified",
                "sibling_independence_vouch_ref": None,
                "proof_limits": list(FAN_TOPOLOGY_PROOF_LIMITS),
                "not_proven": list(FAN_TOPOLOGY_NOT_PROVEN),
            }
            if skip_for:
                # AUDIT: this sibling WAS vouched-skip on some other shared
                # target(s) but is re-verified because a different shared target
                # had no vouch. Record the overridden vouch(es) so the audit shows
                # WHY a vouched sibling was still re-verified (support records the
                # fact; it never decides independence).
                record["reverify_overrides_sibling_independence_vouch"] = [
                    {
                        "fan_in_target_step_ref": overridden_target,
                        "cohort_trigger_step_ref": overridden_trigger,
                        "sibling_independence_vouch_ref": overridden_vouch,
                    }
                    for overridden_target, overridden_trigger, overridden_vouch in skip_for
                ]
        records.append(record)
    return replay_refs, skipped_refs, records


def _latest_completed_source_result(
    step_results: list[BuildingRunSupportResult],
    source_step_refs: Iterable[str],
) -> BuildingRunSupportResult | None:
    source_set = {ref for ref in source_step_refs if ref}
    for result in reversed(step_results):
        if result.preparation.step_rows.step_ref in source_set:
            return result
    if step_results:
        return step_results[-1]
    return None
