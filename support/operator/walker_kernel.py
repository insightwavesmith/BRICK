"""Forward step-walk kernel for the bounded agent-proposed dynamic graph walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
thin one-step-crossing FORWARD walk kernel of the dynamic_walker god-module. It
walks the declared graph over the existing execution_order linearization, and
after a node completes inspects the Agent return for a NON-BINDING reroute
proposal; if the declared gate adopts and the target node budget is available it
appends the target (+ declared replay scope) to the live attempt queue. On a
human/coo gate, an unbudgeted target, or budget exhaustion it HOLDs. The
separable concerns (reroute budget / HOLD / fan-in / transition-concern / step
fixtures / frontier) live in their own collaborator modules; this kernel
orchestrates them.

ζ7 boundary preserved: the Agent PROPOSES (binding:false); the DECLARED Link gate
ADOPTS or PAUSEs; support WALKS the adopted route and RECORDS. Support authors no
route or Movement, judges no success or quality, schedules nothing, retries
nothing, and calls no provider.

Support mechanics only. Homes NO axis crossing (the reroute-adoption record is
built from the recording contract field-spec).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from brick_protocol.support.connection.agent_adapter import (
    AgentBrainCallable,
    CommandRunner,
)
from brick_protocol.support.operator.contracts import (
    BuildingPlanSupportResult,
    BuildingRunSupportResult,
)
from brick_protocol.support.operator.gate_sequence import (
    GateSequenceDecision,
    run_gate_sequence_policy,
)
from brick_protocol.support.operator.plan_graph import (
    _graph_fan_in_sources_by_target_step_ref,
    _graph_fan_out_targets_by_source_step_ref,
    _linear_plan_from_graph_plan,
)
from brick_protocol.support.operator.plan_validation import (
    _incoming_link_handoff_refs,
    _plan_building_id,
    _step_fixture_from_plan_step,
    _task_source_ref_from_plan,
    validate_declared_building_plan,
)
from brick_protocol.support.operator.primitives import (
    _REPO_ROOT,
    _merge_texts,
    _optional_text_from_mapping,
    _optional_text_value,
)
from brick_protocol.support.operator.reporter import (
    building_event_kind_from_frontier,
    emit_building_event_for_policy,
    report_event_policy_from_plan,
)
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
    NOT_PROVEN,
    PROOF_LIMITS,
    RESUME_NOT_PROVEN,
)
from brick_protocol.support.operator.walker_fan_in import (
    _build_fan_in_wait_all_hold,
    _fan_in_cohort_replay_plan,
    _fan_in_wait_all_observations_for_held_source,
    _fan_in_wait_all_state,
    _graph_has_fan_groups,
    _graph_root_step_refs,
    _graph_successor_step_refs_by_source_step_ref,
    _splice_declared_successors,
)
from brick_protocol.support.operator.walker_frontier import (
    _write_dynamic_adapter_error_frontier,
)
from brick_protocol.support.operator.walker_hold import (
    _build_hold,
    _inject_fan_in_paused_link,
    _inject_hold_paused_link,
    _replace_held_source_with_lifecycle,
    _resumed_lifecycle_from_hold,
)
from brick_protocol.support.operator.walker_reroute_budget import (
    _carry_budget_evidence_ref,
    _node_reroute_budgets,
)
from brick_protocol.support.operator.walker_step_fixture import (
    _adopted_by_ref,
    _brick_instance_ref_from_linear_step,
    _declared_replay_scope_step_refs,
    _gate_disposition_for_step,
    _structured_field_observation_for_step,
)
from brick_protocol.support.operator.walker_transition_concern import (
    _build_invalid_transition_concern_hold,
    _classify_reroute_target,
    _transition_concern_observation_from_step_result,
)
from brick_protocol.support.recording.walker_evidence import (
    build_reroute_adoption_record,
    build_resume_observation,
)


def _source_fact_body_carry_for_step(
    *,
    building_root: Path,
    building_id: str,
    target_step_ref: str,
    cascade_depth: int,
    step: Mapping[str, Any],
    step_results: list[BuildingRunSupportResult],
    step_result_events: list[Mapping[str, Any]],
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    cohort_skip_carry_forward: set[tuple[str, int]] | None = None,
) -> Mapping[str, Any]:
    source_facts = _brick_source_facts(step)
    skip_carry_forward = cohort_skip_carry_forward or set()
    attempts = _step_result_attempt_indices(step_results)
    result_refs: dict[int, str] = {}
    for index, result in enumerate(step_results):
        attempt_index = attempts[index]
        step_ref = result.preparation.step_rows.step_ref
        result_refs[index] = _step_output_manifest_ref(step_ref, attempt_index)

    bodies: dict[str, str] = {}
    carried_step_output_refs: list[str] = []
    missing_source_fact_refs: list[str] = []
    carried_result_indices: set[int] = set()
    observed_source_step_refs: list[str] = []
    missing_source_step_refs: list[str] = []

    for source_fact in source_facts:
        match = _matching_step_output_index(
            source_fact,
            cascade_depth=cascade_depth,
            result_refs=result_refs,
            step_result_events=step_result_events,
        )
        if match is None:
            if "step-output" in source_fact:
                missing_source_fact_refs.append(source_fact)
            continue
        body = _step_output_body_from_file(building_root, result_refs[match])
        if body is None:
            missing_source_fact_refs.append(source_fact)
            source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
            if source_step_ref:
                missing_source_step_refs.append(source_step_ref)
            continue
        bodies[source_fact] = body
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
        if source_step_ref:
            observed_source_step_refs.append(source_step_ref)

    for source_step_ref in fan_in_sources_by_target.get(target_step_ref, ()):
        match = _latest_completed_step_index(
            source_step_ref,
            cascade_depth=cascade_depth,
            step_result_events=step_result_events,
        )
        if match is None and (source_step_ref, cascade_depth) in skip_carry_forward:
            # A HUMAN-vouched (sibling_independence) skipped sibling is not
            # re-walked at this reroute cascade-depth; carry its PRIOR PASS
            # (its most recent completion at an earlier depth) forward so the
            # fan-in target's carry gate is satisfied without re-running it.
            match = _latest_completed_step_index_any_depth(
                source_step_ref,
                step_result_events=step_result_events,
            )
        if match is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        if match in carried_result_indices:
            continue
        body = _step_output_body_from_file(building_root, result_refs[match])
        if body is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:step-output-body-missing:"
                f"cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        bodies.setdefault(result_refs[match], body)
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        observed_source_step_refs.append(source_step_ref)

    if not source_facts and target_step_ref not in fan_in_sources_by_target:
        return {"source_fact_bodies": bodies, "observation": None}

    carried_unique = list(dict.fromkeys(carried_step_output_refs))
    missing_unique = list(dict.fromkeys(missing_source_fact_refs))
    observation = {
        "kind": "source_fact_body_carry_observation",
        "target_step_ref": target_step_ref,
        "cascade_depth": cascade_depth,
        "declared_source_fact_refs": list(source_facts),
        "fan_in_source_step_refs": list(fan_in_sources_by_target.get(target_step_ref, ())),
        "observed_source_step_refs": list(dict.fromkeys(observed_source_step_refs)),
        "missing_source_step_refs": list(dict.fromkeys(missing_source_step_refs)),
        "carried_step_output_refs": carried_unique,
        "supplied_source_fact_body_refs": list(bodies),
        "missing_source_fact_refs": missing_unique,
        "body_absent": bool(missing_unique),
        "carry_gate_observation": _carry_gate_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
            missing_source_fact_refs=missing_unique,
        ),
        "carry_fact_observation": _carry_fact_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
        ),
        "proof_limits": [
            "Link carry/gate observation over declared step-output refs only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic sufficiency of carried bodies",
            "partial QA reuse",
        ],
    }
    return {"source_fact_bodies": bodies, "observation": observation}


def _carry_gate_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
    missing_source_fact_refs: list[str],
) -> Mapping[str, Any]:
    required = tuple(dict.fromkeys([*carried_step_output_refs, *missing_source_fact_refs]))
    missing = tuple(dict.fromkeys(missing_source_fact_refs))
    return {
        "kind": "link_carry_gate_observation",
        "stage": "carry",
        "sufficiency": "missing_required_facts" if missing else "sufficient",
        "checked_public_fact": f"step-output-carry:{target_step_ref}",
        "required_public_facts": list(required),
        "missing_required_facts": list(missing),
        "reason": (
            "declared Link fan-in carry gate over already-written step-output evidence"
        ),
        "proof_limits": [
            "support records Link carry gate observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _carry_fact_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
) -> Mapping[str, Any] | None:
    carried = tuple(dict.fromkeys(carried_step_output_refs))
    if not carried:
        return None
    return {
        "kind": "link_carry_fact_observation",
        "carried_fact_refs": list(carried),
        "source_owner_axis": "Agent",
        "target_boundary_ref": target_step_ref,
        "evidence_reference": f"step-output-carry:{target_step_ref}",
        "proof_limits": [
            "support records Link carry observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _fan_in_observation_from_carry_observation(
    observation: Mapping[str, Any],
    *,
    required_sources: tuple[str, ...],
) -> Mapping[str, Any]:
    observed_sources = tuple(
        str(ref)
        for ref in observation.get("observed_source_step_refs", ())
        if str(ref)
    )
    missing_sources = tuple(
        str(ref)
        for ref in observation.get("missing_source_step_refs", ())
        if str(ref)
    )
    carry_gate = observation.get("carry_gate_observation")
    missing_required_facts: list[str] = []
    if isinstance(carry_gate, Mapping):
        missing_required_facts = [
            str(ref)
            for ref in carry_gate.get("missing_required_facts", ())
            if str(ref)
        ]
    return {
        "kind": "fan_in_wait_all_observation",
        "target_step_ref": observation.get("target_step_ref", ""),
        "cascade_depth": observation.get("cascade_depth", 0),
        "required_source_step_refs": list(required_sources),
        "observed_source_step_refs": list(dict.fromkeys(observed_sources)),
        "missing_source_step_refs": list(dict.fromkeys(missing_sources)),
        "pending_source_step_refs": [],
        "carry_gate_observation": dict(carry_gate) if isinstance(carry_gate, Mapping) else {},
        "missing_required_facts": list(dict.fromkeys(missing_required_facts)),
        "proof_limits": list(observation.get("proof_limits", ())),
        "not_proven": list(observation.get("not_proven", ())),
    }


# run_building_intake (support/operator/driver.py) writes its materialized
# INPUT plan to <building_root>/declared-building-plan.json and then
# immediately walks it; without an admission for exactly that artifact, the
# first defaults use always self-collided here (FileExistsError). The
# admission is fail-closed and EXACT: a pre-existing root is admitted IFF it
# holds ONLY regular non-symlink file(s) named in this set -- any other name,
# any subdirectory, any symlink, or an EMPTY root still rejects. (The run's
# own work/declared-building-plan.json declaration packet lives under work/
# and is a different file.) Parity copy lives in run.py.
_PREEXISTING_ROOT_INTAKE_ARTIFACTS: frozenset[str] = frozenset(
    {"declared-building-plan.json"}
)


def _root_holds_only_intake_plan_artifact(root: Path) -> bool:
    entries = list(root.iterdir())
    if not entries:
        return False
    for entry in entries:
        if entry.name not in _PREEXISTING_ROOT_INTAKE_ARTIFACTS:
            return False
        if entry.is_symlink() or not entry.is_file():
            return False
    return True


def _preflight_step_output_building_root(
    output_root: Path | str,
    building_id: str,
    *,
    overwrite_existing: bool,
) -> Path:
    root = Path(output_root) / building_id
    if root.exists():
        if not root.is_dir():
            raise NotADirectoryError(f"Building lifecycle root is not a directory: {root}")
        if not overwrite_existing and not _root_holds_only_intake_plan_artifact(root):
            raise FileExistsError(
                "Building lifecycle root already exists; choose a new building_id "
                "or pass overwrite_existing=True"
            )
    return root


def _brick_source_facts(step: Mapping[str, Any]) -> tuple[str, ...]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return ()
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            raw = row.get("source_facts", ())
            if not isinstance(raw, list):
                return ()
            return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def _step_result_attempt_indices(
    step_results: list[BuildingRunSupportResult],
) -> tuple[int, ...]:
    counts: dict[str, int] = {}
    attempts: list[int] = []
    for result in step_results:
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        attempts.append(counts[step_ref])
    return tuple(attempts)


def _matching_step_output_index(
    source_fact: str,
    *,
    cascade_depth: int,
    result_refs: Mapping[int, str],
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    normalized = str(source_fact).strip()
    if not normalized:
        return None
    for index, ref in result_refs.items():
        if int(step_result_events[index].get("cascade_depth", 0)) != cascade_depth:
            continue
        if normalized == ref or normalized.endswith("/" + ref):
            return index
    return None


def _latest_completed_step_index(
    step_ref: str,
    *,
    cascade_depth: int,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    for index in range(len(step_result_events) - 1, -1, -1):
        event = step_result_events[index]
        if event.get("step_ref") == step_ref and int(event.get("cascade_depth", 0)) == cascade_depth:
            return index
    return None


def _latest_completed_step_index_any_depth(
    step_ref: str,
    *,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    """Latest completion of step_ref at ANY cascade-depth (prior-pass carry).

    Used only for a HUMAN-vouched (sibling_independence) skipped fan-in source:
    the sibling is not re-walked at the reroute depth, so its most recent prior
    completion carries forward to satisfy the fan-in target's carry gate.
    """

    for index in range(len(step_result_events) - 1, -1, -1):
        if step_result_events[index].get("step_ref") == step_ref:
            return index
    return None


def _step_ref_from_step_output_ref(step_output_ref: str) -> str:
    parts = str(step_output_ref).replace("\\", "/").split("/")
    if len(parts) < 3:
        return ""
    slug = parts[-2]
    marker = "-attempt-"
    if marker not in slug:
        return slug
    return slug[: slug.rindex(marker)]


def _step_output_body_from_file(building_root: Path, step_output_ref: str) -> str | None:
    try:
        return (building_root / step_output_ref).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


@dataclasses.dataclass(frozen=True)
class ResumeSeed:
    """Optional seeded-initial-state for the FORWARD walk, used ONLY by resume.

    When this is ``None`` (the default), ``_run_dynamic_graph_walker`` runs from
    scratch exactly as before (zero forward-path change). When present, resume
    REHYDRATES the forward walk by handing it the recorded Agent returns +
    declared budget delta + the human/COO disposition, then DELEGATES to the SAME
    forward loop so every forward behaviour (all HOLDs, fan-in join queueing,
    nested handling, body_absent, ambiguous/none, cohort re-verify) is inherited.

    The forward walk is DETERMINISTIC over (graph topology, Agent returns, gates,
    budgets): re-running it while REPLAYING the recorded returns (instead of
    calling the provider) reproduces the exact same path up to the original HOLD.
    At the held step occurrence the disposition is applied INLINE (raise = the
    budget delta below already lets the landing adopt; forward = the held
    concern/gate HOLD is walked-on once; stop = the building is closed) and the
    loop continues to completion / the next HOLD with full forward fidelity.

    Fields:
      ``replay_returns`` -- per ``step_ref`` FIFO of recorded ``returned`` values
        (realized order). The k-th time the loop reaches ``step_ref`` it pops the
        next recorded return and REPLAYS it; once exhausted the loop runs the step
        LIVE (a continued / post-HOLD step the provider must run).
      ``gate_records`` -- per ``step_ref`` FIFO of the recorded AT-TIME
        gate_sequence_decision_record (or None), aligned 1:1 with
        ``replay_returns`` so a replayed step READS its recorded gate decision back
        (never recomputed).
      ``replay_step`` -- the recorded-return replay executor
        (``_replay_building_step_from_returned``); no provider call.
      ``budget_delta`` -- per target Brick ref budget increment to ADD to the
        declared node budget before the walk (raise disposition; empty otherwise).
      ``disposition_action`` -- ``raise`` / ``forward`` / ``stop``.
      ``held_source_step_ref`` / ``held_cascade_depth`` / ``pending_target_ref``
        -- identify the held step occurrence the disposition resolves.
      ``author_ref`` / ``paused_at_ref`` / ``hold_record`` -- carry the resume
        evidence (resumed transition_lifecycle stamping + resume_observations).
    """

    replay_returns: dict[str, list[Any]]
    gate_records: dict[str, list[Any]]
    replay_step: Callable[..., BuildingRunSupportResult]
    budget_delta: Mapping[str, int]
    disposition_action: str
    held_source_step_ref: str
    held_cascade_depth: int
    pending_target_ref: str
    author_ref: str
    paused_at_ref: str
    hold_record: Mapping[str, Any]
    existing_resume_observations: tuple[Mapping[str, Any], ...] = ()
    # FAIL-CLOSED gap-1: per step_ref the count of occurrences that COMPLETED
    # BEFORE the HOLD (the recorded completed-step frontier, derived INDEPENDENTLY
    # from the on-disk step-output ledger -- NOT from replay_returns). The k-th
    # visit to step_ref is an EXPECTED replay iff k <= this count; an expected
    # replay whose recorded return is MISSING is corrupt evidence -> fail-closed
    # (do NOT run live). Visits BEYOND this count are genuine continued/post-HOLD
    # steps that legitimately run live. Empty => no guard (forward path / no seed).
    expected_replay_counts: Mapping[str, int] = dataclasses.field(default_factory=dict)
    # Per step_ref FIFO of the original recorded_at timestamps (realized order),
    # aligned 1:1 with replay_returns, so a replayed step preserves its ORIGINAL
    # recorded_at instead of being stamped with a fresh one (gap-6 evidence
    # fidelity). Empty => no seed (forward path stamps recorded_at as before).
    replay_recorded_at: Mapping[str, list[str]] = dataclasses.field(default_factory=dict)


def _step_declares_gate_sequence_policy(step: Mapping[str, Any]) -> bool:
    """True iff the step's Link row declares a NON-EMPTY gate_sequence_policy.

    FAIL-CLOSED gap-5 support. Mirrors gate_sequence.run_gate_sequence_policy's own
    declaration check (a policy is a non-empty list on the Link row), so the resume
    replay path uses the SAME definition of "declares a policy" the forward walk
    used. A step with no Link row / no policy / an empty policy declares none.
    """

    rows = step.get("rows")
    if not isinstance(rows, list):
        return False
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Link":
            policy = row.get("gate_sequence_policy")
            return isinstance(policy, list) and len(policy) > 0
    return False


def _next_recorded_return(
    resume_seed: "ResumeSeed | None",
    step_ref: str,
    replay_consumed: dict[str, int],
) -> tuple[Any, Any, str, bool]:
    """The next recorded return + gate record + recorded_at for this occurrence.

    Returns ``(returned_value, gate_record, recorded_at, is_replay)``. When there
    is no ``resume_seed`` (forward path) or this occurrence is a genuine continued
    / post-HOLD step (its index is BEYOND the recorded completed-step frontier),
    returns ``(None, None, "", False)`` so the caller runs the step LIVE. The
    per-step FIFO cursor advances only on a replay so the k-th loop visit consumes
    the k-th recorded return.

    FAIL-CLOSED (gap-1): an occurrence at/before the recorded completed-step
    frontier (``index < expected_replay_counts[step_ref]``) is an EXPECTED replay.
    If its recorded return is MISSING (the per-step FIFO is shorter than the
    frontier says it should be), the written evidence is CORRUPT -- raise rather
    than silently run the step LIVE (which would call a provider and diverge from
    the original walk). The frontier is derived INDEPENDENTLY of replay_returns
    (the on-disk step-output ledger), so a dropped/short recorded return cannot
    masquerade as a continued step.
    """

    if resume_seed is None:
        return None, None, "", False
    index = replay_consumed.get(step_ref, 0)
    recorded = resume_seed.replay_returns.get(step_ref) or []
    expected = int(resume_seed.expected_replay_counts.get(step_ref, 0))
    if index >= expected:
        # Beyond the recorded completed-step frontier: a genuine continued /
        # post-HOLD step the provider must run live.
        return None, None, "", False
    # index < expected: this occurrence completed BEFORE the HOLD and MUST replay.
    if index >= len(recorded):
        raise ValueError(
            f"resume corrupt evidence: step {step_ref!r} occurrence {index + 1} "
            f"completed before the HOLD (recorded completed-step frontier = {expected}) "
            "but has no recorded Agent return to replay; refusing to silently run it "
            "live (would call a provider and diverge from the original walk)"
        )
    replay_consumed[step_ref] = index + 1
    gate_records = resume_seed.gate_records.get(step_ref, [])
    gate_record = gate_records[index] if index < len(gate_records) else None
    recorded_at_list = resume_seed.replay_recorded_at.get(step_ref, [])
    recorded_at = recorded_at_list[index] if index < len(recorded_at_list) else ""
    return recorded[index], gate_record, str(recorded_at or ""), True


def _has_pending_recorded_returns(
    resume_seed: "ResumeSeed",
    step_ref: str,
    replay_consumed: dict[str, int],
) -> bool:
    """True iff this step still has UNconsumed recorded returns (more replays).

    The held step occurrence is the one that consumed the LAST recorded return for
    its step_ref (the original walk broke there). When more recorded returns remain
    for this step_ref it is NOT the held occurrence yet, so the disposition must not
    fire early.
    """

    recorded = resume_seed.replay_returns.get(step_ref) or []
    return replay_consumed.get(step_ref, 0) < len(recorded)


def _stamp_resumed_lifecycle_on_held_source(
    step_results: list[BuildingRunSupportResult],
    *,
    resume_seed: "ResumeSeed",
    disposition_action: str,
    building_id: str,
    replay_step,
    checked_proof_limits: tuple[str, ...],
    held_occurrence_index: int | None = None,
) -> list[BuildingRunSupportResult]:
    """Stamp the human/COO-authored resumed transition_lifecycle on the held source.

    Mirrors the prior resume verb's ``_replace_held_source_with_lifecycle`` so the
    resumed Building's evidence shows the disposition was authored by the human/COO
    (not support). For ``stop`` it also closes the Building lifecycle. Support reads
    the disposition row; it never authors the disposition (ζ7).

    FAIL-CLOSED gap-3: ``held_occurrence_index`` pins the EXACT held step_results
    occurrence (captured in the loop when the disposition was applied). A raise
    re-adoption can run the held ``step_ref`` AGAIN at a deeper cascade AFTER the
    held occurrence, so ``_replace_held_source_with_lifecycle``'s reverse-scan
    (first same-``step_ref`` match from the end) would stamp the LATER occurrence.
    We restrict the reverse-scan to ``step_results[:index+1]`` so it lands on the
    held occurrence, then re-attach the untouched tail. When the index is unknown
    (legacy callers) we fall back to the prior whole-list behaviour.
    """

    budget_increment = None
    if disposition_action == "raise":
        budget_increment = resume_seed.budget_delta.get(resume_seed.pending_target_ref)
    building_lifecycle = None
    boundary_ref = None
    if disposition_action == "stop":
        building_lifecycle = {
            "state": "closed",
            "reason": "ended-by-disposition",
            "not_proven": ["ended-by-disposition"],
            "proof_limits": list(PROOF_LIMITS),
        }
        boundary_ref = f"building-boundary:{building_id}-ended-by-disposition-closed"
    lifecycle = _resumed_lifecycle_from_hold(
        resume_seed.hold_record,
        paused_at_ref=resume_seed.paused_at_ref,
        disposition_action=disposition_action,
        budget_increment=budget_increment,
    )
    if held_occurrence_index is not None and 0 <= held_occurrence_index < len(step_results):
        # Pin the EXACT held occurrence: scope the reverse-scan to the prefix that
        # ENDS at the held occurrence, then re-attach the untouched tail (any deeper
        # same-step_ref occurrence a raise re-adoption created stays untouched).
        head = _replace_held_source_with_lifecycle(
            step_results[: held_occurrence_index + 1],
            hold_record=resume_seed.hold_record,
            lifecycle=lifecycle,
            building_lifecycle=building_lifecycle,
            boundary_ref=boundary_ref,
            author_ref=resume_seed.author_ref or "human:unknown",
            replay_step=replay_step,
            checked_proof_limits=checked_proof_limits,
        )
        return list(head) + step_results[held_occurrence_index + 1 :]
    return _replace_held_source_with_lifecycle(
        step_results,
        hold_record=resume_seed.hold_record,
        lifecycle=lifecycle,
        building_lifecycle=building_lifecycle,
        boundary_ref=boundary_ref,
        author_ref=resume_seed.author_ref or "human:unknown",
        replay_step=replay_step,
        checked_proof_limits=checked_proof_limits,
    )


def _build_resume_disposition_observation(
    *,
    resume_seed: "ResumeSeed",
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
) -> Mapping[str, Any]:
    """The resume_observation recording the applied disposition (FACTS only).

    Same shape/``applied`` vocabulary the prior resume verb emitted, so the
    rewritten dynamic_walker_evidence carries an equivalent disposition record.
    """

    action = resume_seed.disposition_action
    target = resume_seed.pending_target_ref
    applied = {
        "raise": "budget_raised_and_held_landing_reentered",
        "forward": "forwarded_past_held_gate_without_reroute_landing",
        "stop": "closed_by_human_or_coo_disposition",
    }[action]
    increment = (
        int(resume_seed.budget_delta.get(target, 0)) if action == "raise" else 0
    )
    not_proven = (
        ["ended-by-disposition", *RESUME_NOT_PROVEN]
        if action == "stop"
        else list(RESUME_NOT_PROVEN)
    )
    return build_resume_observation(
        resumed_from=resume_seed.paused_at_ref,
        paused_at_ref=resume_seed.paused_at_ref,
        pending_target_ref=target,
        disposition_action=action,
        applied=applied,
        budget_increment=increment,
        node_budget=int(node_budget.get(target, 0)),
        node_landings=int(node_landings.get(target, 0)),
        proof_limits=list(PROOF_LIMITS),
        not_proven=not_proven,
    )


def _run_dynamic_graph_walker(
    plan: Mapping[str, Any],
    *,
    output_root: Path | str,
    overwrite_existing: bool,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
    run_step,
    record_step_output,
    write_accumulated,
    write_adapter_error_frontier,
    resume_seed: "ResumeSeed | None" = None,
) -> BuildingPlanSupportResult:
    """Walk a declared graph plan with runtime, gate-adopted, budgeted reroute.

    ``run_step`` is the existing step executor
    (``_run_building_step_without_writing``); ``write_accumulated`` is the
    existing accumulated-evidence writer. They are injected by ``run.py`` so this
    module reuses the exact same step + writer surfaces as the linear walker (no
    duplicate execution path, no new BAL fact class).

    ``resume_seed`` is the OPTIONAL seeded-initial-state used ONLY by the resume
    verb (``walker_resume._resume_dynamic_graph_walker``). When ``None`` (the
    default) the walk runs from scratch, byte-for-byte as before -- the forward
    path is unchanged. When present the SAME loop runs but REPLAYS the recorded
    Agent returns for already-completed steps (no provider call), applies the
    human/COO disposition at the held step occurrence, and continues with full
    forward fidelity. See ``ResumeSeed``.
    """

    if _optional_text_from_mapping(plan, "plan_shape") != "graph":
        raise ValueError("walker_mode='dynamic' requires a plan_shape: graph Building Plan")

    # FORWARD path reuses the existing graph -> execution_order linearization.
    # LIVE RUN ADMISSION is STRICT about write grants (require_write_need_marker,
    # parity with run.py's linear admission): a brick row carrying write_scope
    # must EXPLICITLY declare its write NEED (requires_brick_write_scope: true).
    # The resume verb delegates back into this same loop, so a resumed walk is
    # re-admitted under the same strict gate.
    linear_plan, graph_context = _linear_plan_from_graph_plan(plan)
    validate_declared_building_plan(
        linear_plan,
        repo_root=_REPO_ROOT,
        require_write_need_marker=True,
    )

    plan_ref = _optional_text_from_mapping(linear_plan, "plan_ref") or "building-plan:anonymous"
    building_id = _plan_building_id(linear_plan, plan_ref)
    building_root = _preflight_step_output_building_root(
        output_root,
        building_id,
        overwrite_existing=overwrite_existing,
    )
    task_source_ref = _task_source_ref_from_plan(linear_plan)

    linear_steps = linear_plan["steps"]
    if not isinstance(linear_steps, list) or not linear_steps:
        raise ValueError("graph Building Plan projected to an empty steps list")
    steps_by_ref: dict[str, Mapping[str, Any]] = {}
    forward_order: list[str] = []
    for step in linear_steps:
        step_ref = _optional_text_from_mapping(step, "step_ref")
        if not step_ref:
            raise ValueError("projected graph step missing step_ref")
        steps_by_ref[step_ref] = step
        forward_order.append(step_ref)
    brick_ref_by_step = {
        step_ref: _brick_instance_ref_from_linear_step(step)
        for step_ref, step in steps_by_ref.items()
    }
    step_ref_by_brick = {brick: step for step, brick in brick_ref_by_step.items()}
    report_event_policy = report_event_policy_from_plan(linear_plan)
    report_event_observations: list[Mapping[str, Any]] = []
    # On RESUME the building already started; do NOT re-emit building_started (the
    # forward walk emits it once at first run). Only the terminal event is emitted
    # below after the resumed walk reaches completion / the next HOLD.
    if resume_seed is None:
        started_event = emit_building_event_for_policy(
            report_event_policy,
            event_kind="building_started",
            building_id=building_id,
            building_root=building_root,
            current_brick_ref=brick_ref_by_step.get(forward_order[0], ""),
            repo_root=_REPO_ROOT,
            overwrite_existing=overwrite_existing,
        )
        if started_event is not None:
            report_event_observations.append(started_event)
    has_fan_groups = _graph_has_fan_groups(graph_context)
    fan_successors_by_source = (
        _graph_successor_step_refs_by_source_step_ref(graph_context)
        if has_fan_groups
        else {}
    )
    fan_in_sources_by_target = (
        _graph_fan_in_sources_by_target_step_ref(graph_context)
        if has_fan_groups
        else {}
    )

    # Per-TARGET-node budget (Link-assigned, keyed by target Brick node ref,
    # SHARED across all reroute-landings on that node). Source = the Link-owned
    # node_reroute_budgets map declared on the graph plan. Each value is the
    # number of reroute-landings admitted on that node before HOLD.
    node_budget = _node_reroute_budgets(plan, declared_bricks=set(step_ref_by_brick))
    # RESUME raise disposition: the human/COO raised the held node's budget by a
    # declared budget_increment. The forward loop then adopts the held landing
    # naturally on the bigger budget -- raise is just "more budget" (verified:
    # byte-identical to a fresh forward walk with the bumped budget). The default
    # (forward) path has an empty budget_delta, so node_budget is unchanged.
    if resume_seed is not None:
        for target_brick, delta in resume_seed.budget_delta.items():
            if delta:
                node_budget[target_brick] = node_budget.get(target_brick, 0) + int(delta)
    # Live per-node consumed counter; consumed once per ADOPTED reroute-landing.
    node_landings: dict[str, int] = {brick: 0 for brick in node_budget}

    # The mutable attempt sequence (the live queue). Serial graphs keep the exact
    # execution_order seed. Fan graphs seed root node(s) and let completed nodes
    # splice declared successors into the live queue.
    if has_fan_groups:
        root_order = _graph_root_step_refs(forward_order, graph_context)
        attempt_queue: list[dict[str, Any]] = [
            {
                "step_ref": step_ref,
                "cascade_depth": 0,
                "parent_reroute_ref": "",
                "is_reroute_landing": False,
            }
            for step_ref in root_order
        ]
        scheduled_fan_steps: set[tuple[str, int]] = {
            (step_ref, 0) for step_ref in root_order
        }
    else:
        attempt_queue = [
            {"step_ref": step_ref, "cascade_depth": 0, "parent_reroute_ref": "", "is_reroute_landing": False}
            for step_ref in forward_order
        ]
        scheduled_fan_steps = set()

    step_results: list[BuildingRunSupportResult] = []
    reroute_records: list[Mapping[str, Any]] = []
    fan_in_wait_all_observations: list[Mapping[str, Any]] = []
    fan_in_cohort_records: list[Mapping[str, Any]] = []
    source_fact_body_carry_observations: list[Mapping[str, Any]] = []
    adoption_sequence_number = 0
    hold_record: Mapping[str, Any] | None = None
    fan_in_hold_record: Mapping[str, Any] | None = None
    completed_fan_steps: set[tuple[str, int]] = set()
    held_fan_steps: set[tuple[str, int]] = set()
    fan_in_deferrals: dict[tuple[str, int], int] = {}
    # (skipped_source_step_ref, reroute_cascade_depth) pairs for HUMAN-vouched
    # (sibling_independence) cohort siblings whose PRIOR pass carries forward.
    cohort_skip_carry_forward: set[tuple[str, int]] = set()
    step_result_events: list[Mapping[str, Any]] = []
    # RESUME replay state (no-op when resume_seed is None). Per step_ref FIFO
    # cursor over the recorded returns: the k-th loop visit to step_ref REPLAYS
    # the k-th recorded return; once exhausted the step runs LIVE (a continued /
    # post-HOLD step). disposition_applied flips once the held step occurrence has
    # been resolved by the disposition (so a later genuine HOLD is a real HOLD).
    replay_consumed: dict[str, int] = {}
    disposition_applied = False
    # FAIL-CLOSED gap-3: the EXACT step_results index of the held occurrence,
    # captured when the disposition is applied, so the resumed-lifecycle stamp lands
    # on the held occurrence (not a later same-step_ref occurrence a raise re-adopts).
    held_occurrence_index: int | None = None
    resume_body_carry_observations: list[Mapping[str, Any]] = []
    cursor = 0
    while cursor < len(attempt_queue):
        item = attempt_queue[cursor]
        cursor += 1
        step_ref = item["step_ref"]
        cascade_depth = int(item.get("cascade_depth", 0))
        if has_fan_groups:
            wait_state, wait_observation = _fan_in_wait_all_state(
                step_ref=step_ref,
                cascade_depth=cascade_depth,
                fan_in_sources_by_target=fan_in_sources_by_target,
                completed_fan_steps=completed_fan_steps,
                held_fan_steps=held_fan_steps,
                pending_queue=attempt_queue[cursor:],
                fan_in_deferrals=fan_in_deferrals,
            )
            if wait_observation is not None and wait_state == "hold":
                fan_in_wait_all_observations.append(wait_observation)
            if wait_state == "defer":
                attempt_queue.append(item)
                continue
            if wait_state == "hold":
                fan_in_hold_record = _build_fan_in_wait_all_hold(
                    building_id=building_id,
                    plan_ref=plan_ref,
                    target_step_ref=step_ref,
                    target_brick=brick_ref_by_step[step_ref],
                    cascade_depth=cascade_depth,
                    observation=wait_observation or {},
                    step_results=step_results,
                )
                break
        step = steps_by_ref[step_ref]
        index = len(step_results)
        step_fixture = _step_fixture_from_plan_step(
            linear_plan,
            step,
            index,
            building_id=building_id,
            incoming_link_handoff_refs=_incoming_link_handoff_refs(linear_steps, forward_order.index(step_ref))
            if step_ref in forward_order
            else {},
        )
        source_fact_body_carry = _source_fact_body_carry_for_step(
            building_root=building_root,
            building_id=building_id,
            target_step_ref=step_ref,
            cascade_depth=cascade_depth,
            step=step,
            step_results=step_results,
            step_result_events=step_result_events,
            fan_in_sources_by_target=fan_in_sources_by_target,
            cohort_skip_carry_forward=cohort_skip_carry_forward,
        )
        if source_fact_body_carry["source_fact_bodies"]:
            step_fixture = dict(step_fixture)
            step_fixture["source_fact_bodies"] = dict(
                source_fact_body_carry["source_fact_bodies"]
            )
        if source_fact_body_carry["observation"] is not None:
            source_fact_body_carry_observations.append(
                source_fact_body_carry["observation"]
            )
            if source_fact_body_carry["observation"].get("body_absent"):
                missing = source_fact_body_carry["observation"].get(
                    "missing_source_fact_refs",
                    [],
                )
                if has_fan_groups and step_ref in fan_in_sources_by_target:
                    fan_in_hold_record = _build_fan_in_wait_all_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        target_step_ref=step_ref,
                        target_brick=brick_ref_by_step[step_ref],
                        cascade_depth=cascade_depth,
                        observation=_fan_in_observation_from_carry_observation(
                            source_fact_body_carry["observation"],
                            required_sources=fan_in_sources_by_target.get(step_ref, ()),
                        ),
                        step_results=step_results,
                    )
                    break
                raise ValueError(
                    "missing step-output source_fact body/evidence: "
                    + ", ".join(str(item) for item in missing)
                )
        # RESUME replay-or-live decision: if resume seeded a recorded return for
        # this step occurrence, REPLAY it (no provider call); otherwise run LIVE.
        # The k-th visit to step_ref consumes the k-th recorded return (realized
        # order). A replayed step READS its recorded AT-TIME gate decision back;
        # a live step computes it (forward parity). Default (no seed) => live.
        recorded_return, recorded_gate_record, recorded_at, is_replay = _next_recorded_return(
            resume_seed, step_ref, replay_consumed
        )
        try:
            if is_replay:
                # gap-6: preserve the ORIGINAL recorded_at through the replay path
                # (evidence fidelity) instead of stamping a fresh timestamp.
                step_result = resume_seed.replay_step(  # type: ignore[union-attr]
                    step_fixture,
                    returned_value=recorded_return,
                    recorded_at=recorded_at,
                    gate_sequence_decision_record=recorded_gate_record,
                    proof_limits=checked_proof_limits,
                )
            else:
                step_result = run_step(
                    step_fixture,
                    local_callables=local_callables,
                    command_runner=command_runner,
                    adapter_cwd=adapter_cwd,
                    adapter_timeout_seconds=adapter_timeout_seconds,
                    proof_limits=checked_proof_limits,
                )
        except Exception as exc:  # noqa: BLE001 - distinguish adapter frontier below
            _write_dynamic_adapter_error_frontier(
                exc,
                building_id=building_id,
                plan_ref=plan_ref,
                linear_plan=linear_plan,
                completed_step_results=step_results,
                output_root=output_root,
                overwrite_existing=overwrite_existing or bool(step_results),
                checked_proof_limits=checked_proof_limits,
                graph_context=graph_context,
                reroute_records=reroute_records,
                node_budget=node_budget,
                node_landings=node_landings,
                held=False,
                hold_record=None,
                fan_in_wait_all_observations=fan_in_wait_all_observations,
                has_fan_groups=has_fan_groups,
                write_adapter_error_frontier=write_adapter_error_frontier,
            )
            raise AssertionError("unreachable after dynamic adapter frontier write")
        # E1 (U5.5 slice-3) + RESUME-GATE-RECORD — DYNAMIC-WALKER parity with run.py.
        # Compute the live gate-sequence disposition and attach it to the step result
        # BEFORE the step-output write so the AT-TIME step-output.json persists the
        # gate_sequence_decision_record (which resume reads back without recompute).
        # This is a PURE computation over the already-completed step_result + step; it
        # does NOT depend on the step-output file. The loop control below reads
        # gate_sequence_decision exactly as before — hold / reroute / fan-in / next /
        # break behaviour is unchanged, and the field survives the only later mutation
        # of an existing step_results entry (_inject_hold_paused_link /
        # _inject_fan_in_paused_link via _step_result_with_paused_lifecycle uses a
        # partial dataclasses.replace). Recording carry only.
        # On a REPLAYED step the gate decision was already RECONSTRUCTED from the
        # recorded AT-TIME record by replay_step (read-back, no recompute); keep it.
        # A no-policy replayed step has gate_sequence_decision None — normalize to a
        # no-action GateSequenceDecision so the loop control reads it like the
        # forward walk's run_gate_sequence_policy() no-policy result.
        if is_replay:
            # FAIL-CLOSED gap-5: a replayed step that DECLARED a non-empty
            # gate_sequence_policy MUST have a recorded gate decision to read back.
            # If it is absent (None) the policy's AT-TIME decision was lost, and
            # normalizing to a no-action GateSequenceDecision() would SILENTLY treat
            # a policy step as no-policy (divergence: a recorded HOLD/forward gate
            # decision would vanish). Raise instead -- only a genuinely no-policy
            # step legitimately has a None recorded decision.
            if (
                step_result.gate_sequence_decision is None
                and _step_declares_gate_sequence_policy(step)
            ):
                raise ValueError(
                    f"resume corrupt evidence: replayed step {step_ref!r} declares a "
                    "gate_sequence_policy but its step-output carries NO recorded gate "
                    "decision to read back; refusing to silently treat a policy step as "
                    "no-action (would drop the recorded gate decision and diverge)"
                )
            gate_sequence_decision = (
                step_result.gate_sequence_decision
                if step_result.gate_sequence_decision is not None
                else GateSequenceDecision()
            )
        else:
            gate_sequence_decision = run_gate_sequence_policy(
                step=step,
                step_result=step_result,
                source_brick_ref=brick_ref_by_step[step_ref],
                target_brick_ref=step_result.preparation.next_brick_instance_ref,
            )
            step_result = dataclasses.replace(
                step_result, gate_sequence_decision=gate_sequence_decision
            )
        step_result = record_step_output(
            building_root=building_root,
            building_id=building_id,
            step_result=step_result,
            completed_step_results=step_results,
            proof_limits=checked_proof_limits,
            task_source_ref=task_source_ref,
            overwrite_existing=overwrite_existing,
        )
        step_results.append(step_result)
        step_result_events.append(
            {
                "step_ref": step_ref,
                "cascade_depth": cascade_depth,
            }
        )
        if has_fan_groups:
            completed_fan_steps.add((step_ref, cascade_depth))
        # RESUME disposition application at the held step occurrence. The held step
        # is the LAST recorded step (the original walk broke there); on replay this
        # is the occurrence that just exhausted its recorded returns at the held
        # (step_ref, cascade_depth) identity. raise was already applied as a budget
        # bump (the landing adopts naturally below). forward => WALK ON past the
        # held concern/gate (treat as no actionable reroute). stop => close.
        if (
            resume_seed is not None
            and not disposition_applied
            and step_ref == resume_seed.held_source_step_ref
            and cascade_depth == resume_seed.held_cascade_depth
            and not _has_pending_recorded_returns(resume_seed, step_ref, replay_consumed)
        ):
            disposition_applied = True
            # gap-3: the held occurrence is the step_result just appended above.
            held_occurrence_index = len(step_results) - 1
            if resume_seed.disposition_action == "stop":
                # Human/COO ended the building at the held gate. Replace the held
                # source's Link row with a resumed->closed lifecycle and stop.
                step_results = _stamp_resumed_lifecycle_on_held_source(
                    step_results,
                    resume_seed=resume_seed,
                    disposition_action="stop",
                    building_id=building_id,
                    replay_step=resume_seed.replay_step,
                    checked_proof_limits=checked_proof_limits,
                    held_occurrence_index=held_occurrence_index,
                )
                break
            if resume_seed.disposition_action == "forward":
                # Walk ON past the held gate without a reroute landing: splice the
                # held step's declared successors (fan graph) or fall through to the
                # next queued step (serial), exactly like the kernel's no-actionable-
                # concern walk-on. The held concern/gate is NOT re-evaluated here.
                if has_fan_groups:
                    _splice_declared_successors(
                        attempt_queue,
                        insert_at=cursor,
                        source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        parent_reroute_ref=item["parent_reroute_ref"],
                        successors_by_source=fan_successors_by_source,
                        scheduled_fan_steps=scheduled_fan_steps,
                    )
                continue
            # raise: fall through to the normal branches; the bumped budget lets the
            # held landing ADOPT below (no special-casing needed).
        if gate_sequence_decision.action == "hold":
            target_brick = (
                gate_sequence_decision.pending_target_ref
                or step_result.preparation.next_brick_instance_ref
            )
            adoption_sequence_number += 1
            hold_record = _build_hold(
                building_id=building_id,
                plan_ref=plan_ref,
                source_step_ref=step_ref,
                source_brick_ref=brick_ref_by_step[step_ref],
                target_brick=target_brick,
                concern={"concern_ref": gate_sequence_decision.evidence_ref},
                cascade_depth=item["cascade_depth"],
                parent_reroute_ref=item["parent_reroute_ref"],
                adoption_sequence_number=adoption_sequence_number,
                node_budget=node_budget.get(target_brick, 0),
                attempt_number=node_landings.get(target_brick, 0),
                budget_exhausted=False,
                hold_reason=gate_sequence_decision.hold_reason
                or "gate_sequence_policy_hold",
                required_disposition_owner=(
                    gate_sequence_decision.required_disposition_owner
                    or "caller-or-coo"
                ),
                step=step,
                step_result=step_result,
            )
            reroute_records.append(hold_record)
            if has_fan_groups:
                held_fan_steps.add((step_ref, cascade_depth))
                fan_in_wait_all_observations.extend(
                    _fan_in_wait_all_observations_for_held_source(
                        held_source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        fan_in_sources_by_target=fan_in_sources_by_target,
                        completed_fan_steps=completed_fan_steps,
                        held_fan_steps=held_fan_steps,
                    )
                )
            break
        if gate_sequence_decision.action == "reroute":
            target_brick = gate_sequence_decision.target_brick_ref
            budget = node_budget.get(target_brick)
            if budget is None or node_landings.get(target_brick, 0) >= budget:
                adoption_sequence_number += 1
                hold_record = _build_hold(
                    building_id=building_id,
                    plan_ref=plan_ref,
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    target_brick=target_brick,
                    concern={"concern_ref": gate_sequence_decision.evidence_ref},
                    cascade_depth=item["cascade_depth"],
                    parent_reroute_ref=item["parent_reroute_ref"],
                    adoption_sequence_number=adoption_sequence_number,
                    node_budget=budget or 0,
                    attempt_number=node_landings.get(target_brick, 0),
                    budget_exhausted=True,
                    hold_reason=(
                        "gate_sequence_reroute_target_unbudgeted"
                        if budget is None
                        else "gate_sequence_reroute_budget_exhausted"
                    ),
                    step=step,
                    step_result=step_result,
                )
                reroute_records.append(hold_record)
                if has_fan_groups:
                    held_fan_steps.add((step_ref, cascade_depth))
                    fan_in_wait_all_observations.extend(
                        _fan_in_wait_all_observations_for_held_source(
                            held_source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            fan_in_sources_by_target=fan_in_sources_by_target,
                            completed_fan_steps=completed_fan_steps,
                            held_fan_steps=held_fan_steps,
                        )
                    )
                break
            node_landings[target_brick] = node_landings.get(target_brick, 0) + 1
            adoption_sequence_number += 1
            attempt_number = node_landings[target_brick]
            target_step_ref = step_ref_by_brick[target_brick]
            reroute_ref = (
                f"reroute-adoption:{building_id}:{adoption_sequence_number:02d}:"
                f"{target_brick.replace(':', '-')}"
            )
            reroute_cascade_depth = item["cascade_depth"] + 1
            attempt_queue[cursor:cursor] = [
                {
                    "step_ref": target_step_ref,
                    "cascade_depth": reroute_cascade_depth,
                    "parent_reroute_ref": reroute_ref,
                    "is_reroute_landing": True,
                }
            ]
            reroute_records.append(
                build_reroute_adoption_record(
                    reroute_ref=reroute_ref,
                    adoption_sequence_number=adoption_sequence_number,
                    cascade_depth=reroute_cascade_depth,
                    parent_reroute_ref=item["parent_reroute_ref"],
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    source_transition_concern_ref=gate_sequence_decision.evidence_ref,
                    transition_concern_binding=False,
                    adopted_by="link-policy:gate-sequence",
                    immediate_target_ref=target_brick,
                    target_brick=target_brick,
                    target_step_ref=target_step_ref,
                    replay_segment_refs=[],
                    attempt_number=attempt_number,
                    node_budget=budget,
                    budget_exhausted=False,
                    disposition_required=False,
                    carry_budget_evidence_ref=_carry_budget_evidence_ref(
                        building_id,
                        target_brick,
                    ),
                    proof_limits=list(PROOF_LIMITS),
                    not_proven=list(NOT_PROVEN),
                    structured_field_observation=_structured_field_observation_for_step(
                        step, step_result
                    ),
                )
            )
            continue

        # ζ7: inspect the Agent return for a NON-BINDING reroute proposal.
        concern_observation = _transition_concern_observation_from_step_result(step_result)
        if concern_observation.invalid_reason:
            adoption_sequence_number += 1
            hold_record = _build_invalid_transition_concern_hold(
                building_id=building_id,
                plan_ref=plan_ref,
                source_step_ref=step_ref,
                source_brick_ref=brick_ref_by_step[step_ref],
                concern_observation=concern_observation,
                declared_bricks=set(step_ref_by_brick),
                cascade_depth=item["cascade_depth"],
                parent_reroute_ref=item["parent_reroute_ref"],
                adoption_sequence_number=adoption_sequence_number,
                node_budget=node_budget,
                node_landings=node_landings,
                step=step,
                step_result=step_result,
            )
            reroute_records.append(hold_record)
            if has_fan_groups:
                held_fan_steps.add((step_ref, cascade_depth))
                fan_in_wait_all_observations.extend(
                    _fan_in_wait_all_observations_for_held_source(
                        held_source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        fan_in_sources_by_target=fan_in_sources_by_target,
                        completed_fan_steps=completed_fan_steps,
                        held_fan_steps=held_fan_steps,
                    )
                )
            break
        concern = concern_observation.concern
        adopted_reroute = False
        target_classification = (
            _classify_reroute_target(concern, declared_bricks=set(step_ref_by_brick))
            if concern is not None
            else None
        )
        # WALK ON (carry forward to closure, no HOLD, no reroute landing) when
        # there is NO concern OR the concern is an EXPLICIT non-reroute concern
        # (non-empty related_boundary_refs that are ALL building-boundary:
        # sentinels -> no Brick node targeted). The non_reroute carve-out matches
        # the legacy engine: an Agent may raise a non-binding concern WITHOUT
        # proposing a reroute address; that is not an unaddressable reroute, so it
        # must NOT HOLD. BUDGET-FREE: node_landings / node_budget untouched.
        if concern is None or (
            target_classification is not None
            and target_classification.kind == "non_reroute"
        ):
            if not has_fan_groups:
                continue
            reroute_insert_width = 0
        else:
            if target_classification.kind in ("ambiguous", "none"):
                # An Agent named EITHER several resolving nodes (ambiguous: no single
                # owner) OR none that resolve while a concern IS present (none: an
                # unaddressable concern). The machine must NOT pick one and must NOT
                # silently drop the concern -> HOLD (BUDGET-FREE: no node_landings /
                # node_budget touched; this is a pause, not a reroute LANDING). The
                # human/COO authors the disposition (caller-or-coo).
                hold_target = brick_ref_by_step[step_ref]
                # The classifier may stamp a SPECIFIC hold_reason (e.g. an
                # unresolvable brick-targeting address co-occurring with a valid
                # one -> unresolvable_reroute_address); otherwise derive the reason
                # from the kind (ambiguous vs none).
                hold_reason = target_classification.hold_reason or (
                    "multiple_reroute_addresses_no_single_owner"
                    if target_classification.kind == "ambiguous"
                    else "no_resolving_reroute_address"
                )
                adoption_sequence_number += 1
                hold_record = _build_hold(
                    building_id=building_id,
                    plan_ref=plan_ref,
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    target_brick=hold_target,
                    concern=concern,
                    cascade_depth=item["cascade_depth"],
                    parent_reroute_ref=item["parent_reroute_ref"],
                    adoption_sequence_number=adoption_sequence_number,
                    node_budget=0,
                    attempt_number=0,
                    budget_exhausted=False,
                    hold_reason=hold_reason,
                    step=step,
                    step_result=step_result,
                )
                reroute_records.append(hold_record)
                if has_fan_groups:
                    held_fan_steps.add((step_ref, cascade_depth))
                    fan_in_wait_all_observations.extend(
                        _fan_in_wait_all_observations_for_held_source(
                            held_source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            fan_in_sources_by_target=fan_in_sources_by_target,
                            completed_fan_steps=completed_fan_steps,
                            held_fan_steps=held_fan_steps,
                        )
                    )
                break
            else:
                target_brick = target_classification.target
                gate = _gate_disposition_for_step(step)
                if gate == "pause":
                    # human:/coo: gate on the reroute -> PAUSE (transition_lifecycle paused).
                    adoption_sequence_number += 1
                    hold_record = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=node_budget.get(target_brick, 0),
                        attempt_number=node_landings.get(target_brick, 0),
                        budget_exhausted=False,
                        hold_reason="human_or_coo_gate_pause",
                        step=step,
                        step_result=step_result,
                    )
                    reroute_records.append(hold_record)
                    if has_fan_groups:
                        held_fan_steps.add((step_ref, cascade_depth))
                        fan_in_wait_all_observations.extend(
                            _fan_in_wait_all_observations_for_held_source(
                                held_source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                fan_in_sources_by_target=fan_in_sources_by_target,
                                completed_fan_steps=completed_fan_steps,
                                held_fan_steps=held_fan_steps,
                            )
                        )
                    break

                # Default/template gate -> auto-adopt IF the target node budget is available.
                budget = node_budget.get(target_brick)
                if budget is None:
                    # A reroute target with no Link-assigned budget cannot be adopted; the
                    # bound depends on every target having a finite budget. HOLD.
                    adoption_sequence_number += 1
                    hold_record = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=0,
                        attempt_number=0,
                        budget_exhausted=True,
                        hold_reason="target_node_has_no_link_assigned_budget",
                        step=step,
                        step_result=step_result,
                    )
                    reroute_records.append(hold_record)
                    if has_fan_groups:
                        held_fan_steps.add((step_ref, cascade_depth))
                        fan_in_wait_all_observations.extend(
                            _fan_in_wait_all_observations_for_held_source(
                                held_source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                fan_in_sources_by_target=fan_in_sources_by_target,
                                completed_fan_steps=completed_fan_steps,
                                held_fan_steps=held_fan_steps,
                            )
                        )
                    break

                if node_landings[target_brick] >= budget:
                    # Budget EXHAUSTED -> the next reroute landing is NOT adopted. HOLD.
                    adoption_sequence_number += 1
                    hold_record = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=budget,
                        attempt_number=node_landings[target_brick],
                        budget_exhausted=True,
                        hold_reason="target_node_budget_exhausted",
                        step=step,
                        step_result=step_result,
                    )
                    reroute_records.append(hold_record)
                    if has_fan_groups:
                        held_fan_steps.add((step_ref, cascade_depth))
                        fan_in_wait_all_observations.extend(
                            _fan_in_wait_all_observations_for_held_source(
                                held_source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                fan_in_sources_by_target=fan_in_sources_by_target,
                                completed_fan_steps=completed_fan_steps,
                                held_fan_steps=held_fan_steps,
                            )
                        )
                    break

                # ADOPT: consume one from the TARGET node's SHARED budget (per landing),
                # append the target (+ declared replay scope) to the live queue, record.
                node_landings[target_brick] += 1
                adoption_sequence_number += 1
                attempt_number = node_landings[target_brick]
                target_step_ref = step_ref_by_brick[target_brick]
                reroute_ref = (
                    f"reroute-adoption:{building_id}:{adoption_sequence_number:02d}:"
                    f"{target_brick.replace(':', '-')}"
                )
                reroute_cascade_depth = item["cascade_depth"] + 1
                # Append the target landing, then its declared replay scope (forward
                # replay executions THROUGH downstream nodes; those do NOT consume budget).
                appended: list[dict[str, Any]] = [
                    {
                        "step_ref": target_step_ref,
                        "cascade_depth": reroute_cascade_depth,
                        "parent_reroute_ref": reroute_ref,
                        "is_reroute_landing": True,
                    }
                ]
                replay_scope = _declared_replay_scope_step_refs(
                    step, target_brick=target_brick, step_ref_by_brick=step_ref_by_brick
                )
                for replay_step_ref in replay_scope:
                    appended.append(
                        {
                            "step_ref": replay_step_ref,
                            "cascade_depth": reroute_cascade_depth,
                            "parent_reroute_ref": reroute_ref,
                            "is_reroute_landing": False,
                        }
                    )
                # COHORT RE-VERIFICATION (knot ③ stale-pass): if this landing
                # targets a node that is a fan-in SOURCE, re-verify its sibling
                # fan-in sources too (a fix in one lane can stale a sibling's
                # prior PASS). Cohort siblings replay FORWARD (is_reroute_landing:
                # False => BUDGET-FREE; node_landings untouched). A sibling is
                # skipped only on a HUMAN sibling_independence vouch; absent =>
                # re-verify all (conservative).
                (
                    cohort_replay_refs,
                    cohort_skipped_refs,
                    cohort_records,
                ) = _fan_in_cohort_replay_plan(
                    target_step_ref=target_step_ref,
                    graph_context=graph_context,
                    step_ref_by_brick=step_ref_by_brick,
                    already_scoped_step_refs=[target_step_ref, *replay_scope],
                )
                for cohort_step_ref in cohort_replay_refs:
                    appended.append(
                        {
                            "step_ref": cohort_step_ref,
                            "cascade_depth": reroute_cascade_depth,
                            "parent_reroute_ref": reroute_ref,
                            "is_reroute_landing": False,
                        }
                    )
                # A vouched-skipped sibling is NOT re-walked; carry its PRIOR pass
                # forward at the reroute cascade-depth so the shared fan-in
                # target's wait-all AND its carry gate are satisfied without
                # re-running it.
                for skipped_step_ref in cohort_skipped_refs:
                    completed_fan_steps.add(
                        (skipped_step_ref, reroute_cascade_depth)
                    )
                    cohort_skip_carry_forward.add(
                        (skipped_step_ref, reroute_cascade_depth)
                    )
                fan_in_cohort_records.extend(cohort_records)
                attempt_queue[cursor:cursor] = appended
                reroute_insert_width = len(appended)
                # CONTRACT-DERIVED emission (ζ6): build the record FROM the recording
                # contract field-spec (support/recording/walker_evidence.py iterates
                # support/recording/contracts.py). No inline dict literal: the shape can
                # no longer drift silently from a feature impl change.
                adoption_record = build_reroute_adoption_record(
                    reroute_ref=reroute_ref,
                    adoption_sequence_number=adoption_sequence_number,
                    cascade_depth=reroute_cascade_depth,
                    parent_reroute_ref=item["parent_reroute_ref"],
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    source_transition_concern_ref=_optional_text_value(
                        concern.get("concern_ref")
                    )
                    or "",
                    transition_concern_binding=False,
                    adopted_by=_adopted_by_ref(step),
                    immediate_target_ref=target_brick,
                    target_brick=target_brick,
                    target_step_ref=target_step_ref,
                    replay_segment_refs=list(replay_scope),
                    attempt_number=attempt_number,
                    node_budget=budget,
                    budget_exhausted=False,
                    disposition_required=False,
                    proof_limits=list(PROOF_LIMITS),
                    not_proven=list(NOT_PROVEN),
                    # Structured field-set observation (no judgment): the field SETS at
                    # this reroute boundary as FACTS (Brick declared / Agent observed /
                    # gate required) + set deltas. NO failing_axis / fault / success.
                    structured_field_observation=_structured_field_observation_for_step(
                        step, step_result
                    ),
                    carry_budget_evidence_ref=_carry_budget_evidence_ref(
                        building_id,
                        target_brick,
                    ),
                    # PERSIST the cohort plan so a HOLD-then-resume reconstruction
                    # rebuilds the SAME pending state (re-verify siblings + carry
                    # vouched-skipped sibling bodies). BUDGET-FREE (forward replay).
                    cohort_replay_segment_refs=list(cohort_replay_refs),
                    cohort_skipped_segment_refs=list(cohort_skipped_refs),
                )
                reroute_records.append(adoption_record)
                adopted_reroute = True
        if has_fan_groups and not adopted_reroute:
            _splice_declared_successors(
                attempt_queue,
                insert_at=cursor + reroute_insert_width,
                source_step_ref=step_ref,
                cascade_depth=cascade_depth,
                parent_reroute_ref=item["parent_reroute_ref"],
                successors_by_source=fan_successors_by_source,
                scheduled_fan_steps=scheduled_fan_steps,
            )

    # RESUME: stamp the human/COO-authored resumed transition_lifecycle on the held
    # source for raise/forward (stop already stamped + closed in the loop hook), and
    # build the resume_observation recording the applied disposition. Mirrors the
    # prior resume verb so the resumed Building's evidence shows the disposition was
    # human/COO-authored (ζ7: support reads it, never authors it).
    resume_observations: list[Mapping[str, Any]] = []
    if resume_seed is not None:
        # FAIL-CLOSED gap-2: assert the held occurrence was actually reached and the
        # disposition applied. The in-loop hook sets disposition_applied=True exactly
        # when (held_source_step_ref, held_cascade_depth) is hit as its held
        # occurrence and the raise/forward/stop action is applied. If the seeded
        # walk finished WITHOUT applying the disposition (the held occurrence was
        # never reached -- e.g. corrupt held identity, a divergent earlier HOLD, or
        # a replay that never reached it), a silent return would falsely claim the
        # disposition was applied. Raise instead of stamping a resumed lifecycle on a
        # disposition that never fired.
        if not disposition_applied:
            raise ValueError(
                "resume divergence: the seeded walk completed WITHOUT applying the "
                f"human/COO disposition ({resume_seed.disposition_action!r}) at the held "
                f"occurrence (source_step_ref={resume_seed.held_source_step_ref!r}, "
                f"cascade_depth={resume_seed.held_cascade_depth}); the held occurrence was "
                "never reached -- refusing to silently claim the disposition was applied"
            )
        resume_observations = list(resume_seed.existing_resume_observations)
        if resume_seed.disposition_action in {"raise", "forward"}:
            step_results = _stamp_resumed_lifecycle_on_held_source(
                step_results,
                resume_seed=resume_seed,
                disposition_action=resume_seed.disposition_action,
                building_id=building_id,
                replay_step=resume_seed.replay_step,
                checked_proof_limits=checked_proof_limits,
                held_occurrence_index=held_occurrence_index,
            )
        resume_observations.append(
            _build_resume_disposition_observation(
                resume_seed=resume_seed,
                node_budget=node_budget,
                node_landings=node_landings,
            )
        )
        resume_body_carry_observations = list(source_fact_body_carry_observations)

    # Thread the dynamic-walker evidence (reroute adoption records + HOLD) onto
    # the plan so the accumulated writer carries it in the link evidence (a NESTED
    # record, NOT a new BAL fact class). On HOLD we also inject a paused
    # transition_lifecycle Link row onto the source step so observe_building_frontier
    # reports link_paused (disposition_required).
    write_plan = dict(linear_plan)
    held = hold_record is not None or fan_in_hold_record is not None
    write_plan["dynamic_walker_evidence"] = {
        "kind": "dynamic_walker_evidence",
        "walker_mode": "dynamic",
        "reroute_adoption_records": list(reroute_records),
        "node_reroute_budgets": dict(node_budget),
        "node_reroute_landings": dict(node_landings),
        "held": held,
        "hold": hold_record or fan_in_hold_record or {},
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if source_fact_body_carry_observations:
        write_plan["dynamic_walker_evidence"]["source_fact_body_carry_observations"] = list(
            source_fact_body_carry_observations
        )
    if resume_seed is not None:
        # RESUME evidence: carry the resume_observations so the rewritten
        # dynamic_walker_evidence matches the prior resume verb's shape. The
        # RESUME_NOT_PROVEN merge is applied AFTER the fan block below so it wins
        # for a resumed graph (the prior resume verb's not_proven shape).
        write_plan["dynamic_walker_evidence"]["resume_observations"] = list(
            resume_observations
        )
    if has_fan_groups:
        write_plan["dynamic_walker_evidence"]["fan_in_wait_all_observations"] = list(
            fan_in_wait_all_observations
        )
        if fan_in_cohort_records:
            write_plan["dynamic_walker_evidence"]["fan_in_cohort_records"] = list(
                fan_in_cohort_records
            )
        write_plan["dynamic_walker_evidence"]["proof_limits"] = list(
            _merge_texts(PROOF_LIMITS, FAN_TOPOLOGY_PROOF_LIMITS)
        )
        write_plan["dynamic_walker_evidence"]["not_proven"] = list(
            _merge_texts(NOT_PROVEN, FAN_TOPOLOGY_NOT_PROVEN)
        )
    if resume_seed is not None:
        # RESUME not_proven wins (prior resume verb shape) over the fan-topology
        # variant for a resumed graph.
        write_plan["dynamic_walker_evidence"]["not_proven"] = list(
            _merge_texts(NOT_PROVEN, RESUME_NOT_PROVEN)
        )
    if hold_record is not None:
        step_results = _inject_hold_paused_link(step_results, hold_record)
    elif fan_in_hold_record is not None:
        step_results = _inject_fan_in_paused_link(step_results, fan_in_hold_record)

    evidence_write = write_accumulated(
        building_id=building_id,
        plan_ref=plan_ref,
        plan=write_plan,
        step_results=tuple(step_results),
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=checked_proof_limits,
        graph_context=graph_context,
        declaration_plan=plan,
        step_outputs_already_written=bool(step_results),
    )
    if report_event_policy:
        terminal_event_kind = building_event_kind_from_frontier(
            evidence_write.lifecycle_write.root,
            repo_root=_REPO_ROOT,
        )
        terminal_event = emit_building_event_for_policy(
            report_event_policy,
            event_kind=terminal_event_kind,
            building_id=building_id,
            building_root=evidence_write.lifecycle_write.root,
            repo_root=_REPO_ROOT,
            overwrite_existing=overwrite_existing,
        )
        if terminal_event is not None:
            report_event_observations.append(terminal_event)
    result = BuildingPlanSupportResult(
        building_id=building_id,
        plan_ref=plan_ref,
        step_results=tuple(step_results),
        lifecycle_write=evidence_write.lifecycle_write,
        building_map_write=evidence_write.building_map_write,
        written_files=evidence_write.written_files,
        capture_event_types=evidence_write.capture_event_types,
        building_map_packet=evidence_write.building_map_packet,
        proof_limits=_merge_texts(
            checked_proof_limits,
            PROOF_LIMITS,
            FAN_TOPOLOGY_PROOF_LIMITS if has_fan_groups else (),
            RESUME_NOT_PROVEN if resume_seed is not None else (),
            *(r.proof_limits for r in step_results),
        ),
        not_proven=_merge_texts(
            plan.get("not_proven"),
            NOT_PROVEN,
            FAN_TOPOLOGY_NOT_PROVEN if has_fan_groups and resume_seed is None else (),
            RESUME_NOT_PROVEN if resume_seed is not None else (),
            *(r.not_proven for r in step_results),
        ),
    )
    # In-memory side channel: the NESTED RerouteAdoptionRecords (NOT a new BAL
    # fact class, NOT a frozen dataclass field) for callers/checkers that walk the
    # dynamic walk in-process. The persistent HOLD signal is the paused
    # transition_lifecycle injected into link.jsonl (observe_building_frontier).
    object.__setattr__(result, "_dynamic_walker_reroute_records", tuple(reroute_records))
    object.__setattr__(
        result,
        "_dynamic_walker_evidence",
        write_plan["dynamic_walker_evidence"],
    )
    if report_event_observations:
        object.__setattr__(
            result,
            "_report_event_observations",
            tuple(report_event_observations),
        )
    return result
