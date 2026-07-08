"""Resume-seed and replay-gate helpers for the dynamic graph walker."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.gate_sequence import GateSequenceDecision
from brick_protocol.support.operator.primitives import _merge_texts, _optional_text_value
from brick_protocol.support.operator.walker_common import PROOF_LIMITS, RESUME_NOT_PROVEN
from brick_protocol.support.operator.walker_hold import (
    _hold_paused_at_ref,
    _replace_held_source_with_lifecycle,
    _resumed_lifecycle_from_hold,
)
from brick_protocol.support.recording.walker_evidence import build_resume_observation


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
    budget delta below already lets the landing adopt; reroute = the human/COO
    selected target enters the existing adoption path; forward = the held
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
      ``disposition_action`` -- ``raise`` / ``forward`` / ``stop`` / ``reroute``.
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
    # MAIL-REPAIR (0611, B3 lane 2): the reason_refs the human/COO disposition
    # row carries (read FROM raw/link.jsonl by walker_resume; B1-checked there
    # fail-closed). On a raise disposition these ADDRESSES ride to the
    # re-adopted redo landing's handoff packet. Empty => nothing rides.
    disposition_reason_refs: tuple[str, ...] = ()
    # ④ RE-INSTRUCTION: the corrected how-to the human/COO disposition row
    # carries (read FROM raw/link.jsonl by walker_resume off the SAME
    # transition_lifecycle row as the disposition_action). When non-empty it is
    # stamped onto the LIVE retried target step packet (the pending_target_ref
    # redo landing) so the redo prompt carries a fixed instruction as its own
    # labeled section. Empty => the target runs its original plan work unchanged.
    # Rides INDEPENDENTLY of disposition_reason_refs (it is not an address truck)
    # and NEVER onto a replayed pre-HOLD occurrence (gated on the live target).
    re_instruction: str = ""
    # FIX 3 (0611 replay provenance): the SELECTED disposition row's
    # discriminator from walker_resume._read_disposition_row -- the current
    # hold identity (disposition_row_paused_at_ref), the row's own raw_ref
    # (disposition_row_raw_ref), and its 1-based index among rows matching the
    # selection rule in file order (disposition_row_same_hold_index) -- so the
    # runtime-mail provenance names the SPECIFIC raw/link.jsonl row, not just
    # the file. Data only (refs + an int); empty on the forward path.
    disposition_row_provenance: Mapping[str, Any] = dataclasses.field(
        default_factory=dict
    )
    # Chat-session S2/S3 uses the same replay machinery to consume a validated
    # passive submission at the parked step, but that authority is the
    # claim+submission admission key, not a human/COO Link disposition row.
    # Default False preserves generic resume behavior.
    skip_lifecycle_stamp: bool = False
    resume_authority_ref: str = ""


_REPLAY_GATE_COMPUTE_LIVE = "__brick_protocol_compute_live_gate_at_reentry__"


def replay_gate_compute_live_record() -> Mapping[str, Any]:
    """Sentinel gate record for a submitted parked step.

    The record is in-memory only. It tells the resume seed to validate the
    submitted return through replay, then compute the gate at re-entry instead
    of reading an at-time gate record that cannot exist for a parked step.
    """

    return {"support_replay_gate": _REPLAY_GATE_COMPUTE_LIVE}


def _replay_gate_record_requests_live_compute(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("support_replay_gate") == _REPLAY_GATE_COMPUTE_LIVE


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


def _resume_observation_for_hold(
    resume_seed: "ResumeSeed | None",
    hold_record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if resume_seed is None:
        return None
    hold_ref = _hold_paused_at_ref(hold_record)
    for observation in resume_seed.existing_resume_observations:
        if not isinstance(observation, Mapping):
            continue
        refs = {
            _optional_text_value(observation.get("paused_at_ref")),
            _optional_text_value(observation.get("resumed_from")),
        }
        provenance = observation.get("disposition_row_provenance")
        if isinstance(provenance, Mapping):
            refs.add(_optional_text_value(provenance.get("disposition_row_paused_at_ref")))
        if hold_ref in refs:
            return observation
    return None


def _resume_observations_for_frontier(
    resume_seed: "ResumeSeed | None",
    *,
    disposition_applied: bool,
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
) -> list[Mapping[str, Any]] | None:
    if resume_seed is None:
        return None
    observations = list(resume_seed.existing_resume_observations)
    if disposition_applied:
        observations.append(
            _build_resume_disposition_observation(
                resume_seed=resume_seed,
                node_budget=node_budget,
                node_landings=node_landings,
            )
        )
    return observations


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
    if resume_seed.skip_lifecycle_stamp and action == "forward":
        applied = "chat_session_submission_consumed_and_walk_continued"
    else:
        applied = {
            "raise": "budget_raised_and_held_landing_reentered",
            "forward": "forwarded_past_held_gate_without_reroute_landing",
            "stop": "closed_by_human_or_coo_disposition",
            "reroute": "rerouted_to_human_or_coo_selected_target",
        }[action]
    increment = (
        int(resume_seed.budget_delta.get(target, 0)) if action == "raise" else 0
    )
    not_proven = (
        ["ended-by-disposition", *RESUME_NOT_PROVEN]
        if action == "stop"
        else list(
            _merge_texts(
                RESUME_NOT_PROVEN,
                (
                    "chat-session claim/submission semantic correctness",
                    "chat-session performer quality",
                )
                if resume_seed.skip_lifecycle_stamp
                else (),
            )
        )
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
        # FIX 3 (0611): PERSIST the selected disposition row's discriminator
        # (generation-unique hold identity + the row's own raw_ref + the
        # pre-resume-snapshot match index) into the written resume
        # observation. The transient ResumeSeed provenance alone dangles on a
        # later replay because the resume REWRITES raw/link.jsonl
        # (raw_claim_trace._write_jsonl uses write_text, not append).
        disposition_row_provenance=(
            dict(resume_seed.disposition_row_provenance)
            if resume_seed.disposition_row_provenance
            else None
        ),
    )
