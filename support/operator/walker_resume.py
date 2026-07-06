"""Resume-after-HOLD verb for the bounded agent-proposed dynamic graph walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
resume verb over the admitted dynamic walker (NOT a third walker_mode) plus its
orchestration helpers -- reading the written plan snapshot / dynamic_walker
evidence / recorded Agent returns / the human-or-COO-authored disposition Link
row, replaying completed steps from recorded payloads, reconstructing the
residual queue after the HOLD, and continuing the live queue per the disposition
action (raise / forward / stop / reroute) -- were lifted out of the dynamic_walker
god-module into this single-concern collaborator. The separable mechanics (HOLD /
fan-in / reroute budget / step fixtures / transition-concern / frontier) live in
their own collaborator modules; this verb orchestrates them.

ζ7: support reads the human/COO disposition row and walks/records; it never
authors the disposition. Support authors no route or Movement, judges no success
or quality, schedules nothing, retries nothing, and calls a provider only for
NOT-yet-completed steps (completed steps are replayed from recorded payloads).

Support mechanics only. Homes NO axis crossing (it consumes the canonical
transition-lifecycle author-prefix contract of link/transition.py to validate the
disposition author).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brick_protocol.link.transition import (
    DISPOSITION_ACTIONS as _DISPOSITION_ACTIONS,
    TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES as _HUMAN_AUTHOR_PREFIXES,
)
from brick_protocol.support.connection.agent_adapter import (
    AgentBrainCallable,
    CommandRunner,
)
from brick_protocol.support.operator.contracts import (
    BuildingPlanSupportResult,
)
from brick_protocol.support.operator.plan_graph import (
    _linear_plan_from_graph_plan,
)
from brick_protocol.support.operator.primitives import (
    _merge_texts,
    _optional_text_from_mapping,
    _optional_text_value,
)
from brick_protocol.support.operator.re_instruction_rules import (
    re_instruction_endline_rules,
    re_instruction_rule_violations,
)
from brick_protocol.support.recording.building_map import BuildingMapWriteResult
from brick_protocol.support.recording.capture import (
    BuildingLifecycleWriteResult,
    graph_ready_json_object,
    graph_ready_timestamp,
)
from brick_protocol.support.recording.declaration_packets import (
    _plan_snapshot,
    _valid_revision_chain_packets,
    latest_valid_declared_plan,
)
from brick_protocol.support.recording.walker_evidence import build_resume_observation
from brick_protocol.support.operator.walker_hold import (
    _hold_paused_at_ref,
    _resumed_lifecycle_from_hold,
)
from brick_protocol.support.operator.walker_kernel import (
    ResumeSeed,
    _run_dynamic_graph_walker,
    _runtime_handoff_unresolved_address,
)
from brick_protocol.support.operator.walker_reroute_budget import (
    _jsonl_records,
    _mapping_value,
    _positive_int,
    _required_disposition_action,
)
from brick_protocol.support.operator.walker_step_fixture import (
    _brick_instance_ref_from_linear_step,
)


@dataclass(frozen=True)
class ResumeBudgetRecoveryDecision:
    node_reroute_budgets: Mapping[str, int] | None = None
    bridge_evidence: bool = False


@dataclass(frozen=True)
class ResumeAdmissionDecision:
    """Closed result of the single-source resume admission sequence (D1).

    Support evidence only: this dataclass carries the accepted resume-admission
    facts the two firing points need to keep walking; it authors no disposition,
    Movement, route, sufficiency, quality, or success. ``adapter_error_stop``
    signals the resume-only paper-stop early-accept short-circuit (the ledger
    loaders were NOT invoked); ``raise_budget_increment`` is populated only when
    the caller enforces the resume-only budget_increment check.
    """

    action: str
    pending_target: str
    hold_record: Mapping[str, Any]
    budget_recovery: ResumeBudgetRecoveryDecision
    replay_returns: Mapping[str, list[Any]]
    recorded_returns: Sequence[Mapping[str, Any]]
    expected_replay_counts: Mapping[str, int]
    raise_budget_increment: int | None = None
    adapter_error_stop: bool = False


# ---------------------------------------------------------------------------
# Shared refusal literals (pinned verbatim). These are raised by BOTH the live
# resume path (post-persist, historical firing points) AND the pre-persist
# ``validate_disposition_intake`` gate (D1). Extracting them to module constants
# is the anti-drift mechanism for invariant I2 (intake accepts exactly what the
# resume path accepts, by DELEGATION -- same literal, no copied prose): the
# intake gate re-raises THE SAME string object the resume path would raise, so
# the accept/refuse literal can never silently diverge between the two firing
# points.
# ---------------------------------------------------------------------------
_BIRTH_CERTIFICATE_ABSENT_REFUSAL = (
    "resume requires the declared-building-plan.json birth-certificate "
    "(full graph topology) to rehydrate the forward walk; it is absent or "
    "unreadable -- refusing to resume from the linearized snapshot alone "
    "(would drop fan-in/cohort/nested behaviour)"
)
_NO_RECORDED_RETURNS_REFUSAL = (
    "held Building evidence carries no recorded Agent returns to replay"
)
_RAISE_TARGET_NOT_NODE_REFUSAL = (
    "raise disposition pending_target_ref is not an existing Brick node"
)
# Lifted verbatim from the previously-duplicated inline strings (resume side
# :237-238 and intake side :1407-1408) so BOTH firing points and the shared
# ``resume_admission_decision`` sequence raise THE SAME string object (invariant
# I2 anti-drift, same mechanism as the refusal literals above).
_APPLIED_RESUME_REFUSAL = "dynamic Building already has an applied resume disposition"
_NOT_HELD_REFUSAL = (
    "resume_building_plan requires a held dynamic_walker_evidence record"
)

# D2 (0706): the raw/link.jsonl record kind a support void verb appends to make a
# residual (already-persisted, refused) disposition row unselectable on the next
# resume read. It is a SUPPORT record kind, NOT a Link DISPOSITION_ACTION
# (link/transition.py DISPOSITION_ACTIONS is untouched -- Movement stays
# forward/reroute). It authors no Movement, route, sufficiency, quality, or
# success; it only records that a human/COO chose to disregard a specific
# residual row so a corrected disposition can be authored.
DISPOSITION_VOID_RECORD_KIND = "disposition_void_observation"


def hold_disposition_action_menu(
    hold_record: Mapping[str, Any],
    *,
    frontier_reason: str = "",
    public_approval: bool = True,
) -> tuple[str, ...]:
    """Return the caller/COO disposition actions admitted for a held frontier.

    This is support guidance over recorded HOLD facts. It does not choose an
    action, route, target, Movement, sufficiency, quality, or success.
    """

    if _adapter_error_hold_without_return(hold_record):
        return ("stop",)
    reason = (
        _optional_text_value(hold_record.get("hold_reason"))
        or _optional_text_value(frontier_reason)
        or ""
    )
    if hold_record.get("budget_exhausted") or reason == "target_node_budget_exhausted":
        if not public_approval:
            return tuple(_DISPOSITION_ACTIONS)
        return ("raise", "stop", "reroute")
    if reason in {
        "fake_landing_write_scope_diff_absent",
        "write_scope_forbidden_diff_present",
        "human_or_coo_gate_pause",
    }:
        return ("forward", "stop", "reroute")
    return ("forward", "stop", "reroute")


def validate_hold_disposition_action(
    action: str,
    hold_record: Mapping[str, Any],
    *,
    frontier_reason: str = "",
    public_approval: bool = True,
) -> tuple[str, ...]:
    allowed = hold_disposition_action_menu(
        hold_record,
        frontier_reason=frontier_reason,
        public_approval=public_approval,
    )
    if action not in allowed:
        reason = (
            _optional_text_value(hold_record.get("hold_reason"))
            or _optional_text_value(frontier_reason)
            or "unknown"
        )
        menu = ", ".join(allowed)
        source_step = _optional_text_value(hold_record.get("source_step_ref")) or "unknown"
        pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or "unknown"
        raise ValueError(
            f"disposition action {action!r} is not admitted for hold_reason={reason!r}; "
            f"allowed disposition actions: {menu}; "
            f"held_step_ref={source_step!r}; pending_target_ref={pending_target!r}"
        )
    return allowed


def _resume_dynamic_graph_walker(
    building_root: Path | str,
    *,
    output_root: Path | str,
    overwrite_existing: bool,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
    run_step,
    replay_step,
    record_step_output,
    write_accumulated,
    write_adapter_error_frontier,
    write_chat_session_park_frontier,
    chat_session_park_frontier_exception,
    repo_root: Path | str,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingPlanSupportResult:
    """Resume a held dynamic walk by REHYDRATING + DELEGATING to the FORWARD walk.

    ROOT-CAUSE REWRITE (C): resume no longer runs a parallel mini-engine. It reads
    the written evidence + the human/COO-authored disposition Link row, recovers
    the PURE declared graph plan from the Building birth-certificate
    (``work/declared-building-plan.json`` -- full topology: groups + link_edges),
    builds a ``ResumeSeed`` (the recorded Agent returns to REPLAY + the budget
    delta for a raise + the disposition), and DELEGATES to the SAME forward walk
    loop (``walker_kernel._run_dynamic_graph_walker``).

    Because the forward walk is DETERMINISTIC over (graph topology, Agent returns,
    gates, budgets), re-running it while replaying the recorded returns reproduces
    the exact path to the original HOLD; the disposition is applied INLINE at the
    held step occurrence and the SAME forward loop continues to completion / the
    next HOLD. Resume thus inherits EVERY forward behaviour for free -- all HOLDs,
    fan-in join queueing, nested handling, body_absent, ambiguous/none, cohort
    re-verify -- so the silent-proceed corners the old retrofitted resume engine
    had (in-resume reroute onto a fan-in source not queuing the join; body-carry
    proceeding on body_absent; non-recursive nested floor) DISAPPEAR.

    ζ7: support reads the human/COO disposition row and walks/records; it never
    authors the disposition, route, or Movement.
    """

    root = Path(building_root).resolve()
    plan, evidence = _read_written_dynamic_plan(root)
    existing_resume_observations = _resume_observations(evidence)
    if not evidence.get("held"):
        if existing_resume_observations:
            raise ValueError(_APPLIED_RESUME_REFUSAL)
        raise ValueError(_NOT_HELD_REFUSAL)
    hold_record = _mapping_value("dynamic_walker_evidence.hold", evidence.get("hold"))
    disposition = _read_disposition_row(root, hold_record)
    if disposition is None:
        pending = _optional_text_value(hold_record.get("pending_target_ref")) or "brick-unknown"
        raise ValueError(
            "no human/COO disposition row found for held pending_target_ref " + pending
        )

    # RECOVER the PURE declared graph plan (full topology) from the Building
    # birth-certificate. This is the SAME plan the forward walk received, so
    # delegating to the forward loop rebuilds the IDENTICAL graph scheduler
    # (fan-in wait-all, cohort re-verify, nested handling). The written evidence
    # snapshot is the LINEARIZED plan (no groups/edges) and is NOT a faithful
    # delegation source -- STOP rather than ship an unfaithful linear resume.
    declared_plan = _declared_graph_plan_from_birth_certificate(root)

    # SINGLE-SOURCE resume admission (D1/D2): delegate the whole overlapping
    # validation clause chain to resume_admission_decision. The ledger reads are
    # supplied as loaders invoked at the exact sequence position resume uses
    # today (past the paper-stop short-circuit). This firing point ENFORCES the
    # resume-only budget_increment check and TAKES the paper-stop early-accept.
    decision = resume_admission_decision(
        evidence=evidence,
        disposition=disposition,
        declared_plan=declared_plan,
        recorded_returns_loader=lambda: _recorded_agent_returns(root),
        completed_step_frontier_loader=lambda: _completed_step_frontier(root),
        returned_claims_present_loader=lambda: (
            root / "evidence" / "claim_trace" / "agent" / "returned_claims.json"
        ).is_file(),
        enforce_raise_budget_increment=True,
        adapter_error_stop_short_circuit=True,
    )
    action = decision.action
    pending_target = decision.pending_target
    hold_record = decision.hold_record
    budget_recovery = decision.budget_recovery

    # RE-ATTACH the Link-owned node_reroute_budgets onto the recovered declared
    # plan. The birth-certificate STRIPS runtime walker keys (incl.
    # node_reroute_budgets, see declaration_packets._DECLARED_PLAN_RUNTIME_KEYS),
    # but the budgets are the SAME Link-declared values the forward walk used and
    # were persisted in dynamic_walker_evidence. Without them the forward walk
    # would see no budget and HOLD every reroute target (target_node_has_no_link_
    # assigned_budget). raise's budget_delta is applied separately in the kernel.
    declared_plan = dict(declared_plan)
    bridged_evidence: Mapping[str, Any] = evidence
    if budget_recovery.node_reroute_budgets is not None:
        recovered_budgets = dict(budget_recovery.node_reroute_budgets)
        expansion_budgets = _expansion_node_budgets_from_revision_chain(
            root,
            declared_plan=declared_plan,
            evidence_budgets=recovered_budgets,
        )
        if expansion_budgets:
            recovered_budgets = {**expansion_budgets, **recovered_budgets}
        declared_plan["node_reroute_budgets"] = recovered_budgets
        if budget_recovery.bridge_evidence:
            bridged_evidence = {
                **evidence,
                "node_reroute_budgets": recovered_budgets,
            }
    seed_hold_record: Mapping[str, Any] = hold_record
    if action == "reroute":
        seed_hold_record = {**hold_record, "pending_target_ref": pending_target}
    paused_at_ref = (
        _optional_text_value(disposition.get("resumed_from_ref"))
        or _optional_text_value(disposition.get("paused_at_ref"))
        or _hold_paused_at_ref(hold_record)
    )
    author_ref = _optional_text_value(disposition.get("author_ref")) or "human:unknown"

    if decision.adapter_error_stop:
        return _paper_stop_adapter_error_hold(
            root,
            declared_plan=declared_plan,
            plan_ref=_optional_text_value(plan.get("plan_ref"))
            or _optional_text_value(declared_plan.get("plan_ref"))
            or "building-plan:anonymous",
            evidence=evidence,
            hold_record=hold_record,
            disposition=disposition,
            paused_at_ref=paused_at_ref,
            pending_target=pending_target,
            author_ref=author_ref,
            checked_proof_limits=checked_proof_limits,
        )

    # Per step_ref FIFO of recorded returns + AT-TIME gate records, in REALIZED
    # order, so the forward loop REPLAYS the k-th visit with the k-th recorded
    # return (and reads its recorded gate decision back). Once a step's recorded
    # returns are exhausted the loop runs it LIVE (a continued / post-HOLD step).
    # replay_returns is the SAME map the shared admission sequence built; the
    # gate_records / replay_recorded_at collections are resume-only seed inputs
    # (residue) rebuilt here from decision.recorded_returns.
    replay_returns: dict[str, list[Any]] = dict(decision.replay_returns)
    gate_records: dict[str, list[Any]] = {}
    replay_recorded_at: dict[str, list[str]] = {}
    for item in decision.recorded_returns:
        step_ref = _optional_text_value(item.get("step_ref")) or ""
        gate_records.setdefault(step_ref, []).append(
            item.get("gate_sequence_decision_record")
        )
        replay_recorded_at.setdefault(step_ref, []).append(
            _optional_text_value(item.get("recorded_at")) or ""
        )

    # FAIL-CLOSED gap-1 (completed-step frontier + torn-pair/skew + overrun) is
    # validated inside resume_admission_decision above; the accepted frontier is
    # carried on the decision.
    expected_replay_counts = decision.expected_replay_counts

    # raise => bump the held node's budget by the declared budget_increment so the
    # held landing ADOPTS naturally on the bigger budget (verified byte-identical
    # to a fresh forward walk with the bumped budget). forward/stop/reroute => no delta.
    budget_delta: dict[str, int] = {}
    if action == "raise":
        budget_delta[pending_target] = decision.raise_budget_increment

    # MAIL-REPAIR (0611, B3 lane 2): THIS resume's disposition row is a
    # truck-eligible runtime row -- its reason_refs (an ADMITTED
    # transition_lifecycle key) ride as ADDRESSES to the re-adopted redo landing
    # on a raise. B1 fail-closed AT SEED BUILD: a disposition address that
    # claims a ledger residence (step-output form) but has no document is a
    # broken ticket -- STOP LOUDLY here, before any walk, instead of silently
    # delivering it (no silent delivery).
    raw_disposition_reason_refs = disposition.get("reason_refs")
    disposition_reason_refs = tuple(
        text
        for text in (
            _optional_text_value(ref)
            for ref in (
                raw_disposition_reason_refs
                if isinstance(raw_disposition_reason_refs, list)
                else []
            )
        )
        if text
    )
    if disposition_reason_refs:
        unresolved = _runtime_handoff_unresolved_address(root, disposition_reason_refs)
        if unresolved:
            raise ValueError(
                "resume: runtime_handoff_address_unresolved_in_ledger -- the "
                f"human/COO disposition row carries reason_ref {unresolved!r} "
                "which claims a step-output ledger residence but no such document "
                "exists in this Building's ledger; refusing to silently deliver a "
                "broken address to the redo landing (B1 fails-closed)"
            )

    # ④ RE-INSTRUCTION: read the corrected how-to off the SAME human/COO
    # disposition transition_lifecycle row (an ADMITTED transition_lifecycle key;
    # the author-prefix gate above already validated the row authority). Carried
    # as plain text onto the seed; the kernel stamps it onto the live retried
    # target's prompt. Resume validates here too so direct raw/link authors
    # cannot bypass onboard's pre-write check.
    re_instruction = _validated_resume_re_instruction(
        action,
        disposition,
        repo=Path(repo_root).resolve(),
    )

    seed = ResumeSeed(
        replay_returns=replay_returns,
        gate_records=gate_records,
        replay_step=replay_step,
        budget_delta=budget_delta,
        disposition_action=action,
        held_source_step_ref=_optional_text_value(hold_record.get("source_step_ref")) or "",
        held_cascade_depth=int(hold_record.get("cascade_depth", 0)),
        pending_target_ref=pending_target,
        author_ref=author_ref,
        paused_at_ref=paused_at_ref,
        hold_record=seed_hold_record,
        existing_resume_observations=tuple(existing_resume_observations),
        expected_replay_counts=dict(expected_replay_counts),
        replay_recorded_at=replay_recorded_at,
        disposition_reason_refs=disposition_reason_refs,
        re_instruction=re_instruction,
        # FIX 3 (0611): the SELECTED disposition row's discriminator (current
        # hold identity + row raw_ref + 1-based same-hold index) rides into the
        # runtime-mail provenance so replaying the selection rule lands on the
        # SAME raw/link.jsonl row deterministically.
        disposition_row_provenance=(
            dict(disposition.get("selected_row_provenance"))
            if isinstance(disposition.get("selected_row_provenance"), Mapping)
            else {}
        ),
    )

    # DELEGATE to the SAME forward walk loop. Resume inherits every forward
    # behaviour; the silent-proceed corners disappear because the forward walker
    # (not a parallel resume engine) does the real work.
    return _run_dynamic_graph_walker(
        declared_plan,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
        checked_proof_limits=checked_proof_limits,
        run_step=run_step,
        record_step_output=record_step_output,
        write_accumulated=write_accumulated,
        write_adapter_error_frontier=write_adapter_error_frontier,
        write_chat_session_park_frontier=write_chat_session_park_frontier,
        chat_session_park_frontier_exception=chat_session_park_frontier_exception,
        repo_root=repo_root,
        resume_seed=seed,
        report_env=report_env,
        report_slack_sender=report_slack_sender,
    )


def _validated_resume_re_instruction(
    action: str,
    disposition: Mapping[str, Any],
    *,
    repo: Path,
) -> str:
    re_instruction = _optional_text_value(disposition.get("re_instruction")) or ""
    if action == "reroute" and not re_instruction:
        raise ValueError("resume: reroute disposition row requires re_instruction")
    if re_instruction:
        violations = re_instruction_rule_violations(
            re_instruction,
            re_instruction_endline_rules(repo),
        )
        if violations:
            details = "; ".join(str(item) for item in violations)
            raise ValueError(
                "resume: re_instruction_endline_rule_violation -- "
                "human/COO disposition row carries re_instruction that violates "
                f"declared endline rule(s): {details}"
            )
    return re_instruction


def _require_budget_exhaustion_raise(
    hold_record: Mapping[str, Any],
    evidence: Mapping[str, Any],
    pending_target: str,
) -> None:
    """FAIL-CLOSED gap-4 (B2): a `raise` is admitted ONLY on a budget-exhaustion hold.

    A `raise` disposition adds a budget increment to the held node so the refused
    landing re-adopts on the bigger budget. That semantics is only valid when the
    HOLD was a BUDGET-EXHAUSTION hold: the held record must carry
    ``budget_exhausted == True`` AND the pending target must have a recorded
    ``node_reroute_budget`` AND the recorded ``node_reroute_landings`` must have
    REACHED/exhausted that recorded budget. A human/COO gate pause (or any other
    non-budget-exhaustion hold) never consumed the base budget, so bumping it
    manufactures a budget value diverging from the Link-declared base -- the human
    should use forward/stop on a gate pause, not raise. Raise (fail closed) here so
    support never invents a recovered-budget base.
    """

    if not hold_record.get("budget_exhausted"):
        reason = _optional_text_value(hold_record.get("hold_reason")) or "<none>"
        raise ValueError(
            "resume: a raise disposition was authored on a NON-budget-exhaustion HOLD "
            f"(hold_reason={reason!r}, budget_exhausted=False) for pending_target_ref "
            f"{pending_target!r}; a raise adds budget and is admitted ONLY on a "
            "budget-exhaustion HOLD -- refusing to manufacture a recovered budget base "
            "(use forward or stop on a gate pause, not raise)"
        )
    recorded_budgets = evidence.get("node_reroute_budgets")
    recorded_landings = evidence.get("node_reroute_landings")
    if not isinstance(recorded_budgets, Mapping) or pending_target not in recorded_budgets:
        raise ValueError(
            "resume: a raise disposition for budget-exhaustion HOLD pending_target_ref "
            f"{pending_target!r} has NO recorded node_reroute_budget in "
            "dynamic_walker_evidence.node_reroute_budgets; refusing to raise a budget "
            "the building never recorded"
        )
    recorded_budget = recorded_budgets.get(pending_target)
    if (
        isinstance(recorded_budget, bool)
        or not isinstance(recorded_budget, int)
        or recorded_budget < 1
    ):
        raise ValueError(
            "resume: a raise disposition for budget-exhaustion HOLD pending_target_ref "
            f"{pending_target!r} has a malformed recorded node_reroute_budget "
            f"({recorded_budget!r}); a node budget must be a positive integer"
        )
    landings = 0
    if isinstance(recorded_landings, Mapping):
        value = recorded_landings.get(pending_target)
        if isinstance(value, int) and not isinstance(value, bool):
            landings = value
    if landings < recorded_budget:
        raise ValueError(
            "resume: a raise disposition for pending_target_ref "
            f"{pending_target!r} claims budget exhaustion but the recorded "
            f"node_reroute_landings ({landings}) did NOT reach the recorded "
            f"node_reroute_budget ({recorded_budget}); refusing to raise a budget "
            "that was not actually exhausted"
        )


def resume_budget_recovery_decision(
    *,
    evidence: Mapping[str, Any],
    action: str,
    hold_record: Mapping[str, Any],
    pending_target: str,
) -> ResumeBudgetRecoveryDecision:
    """Validate/recover reroute budgets exactly as resume does before walking.

    Support wrappers use this pure helper before persisting a disposition so the
    accept/refuse set stays identical to the resume path. It authors no
    disposition, movement, route, sufficiency, quality, or success fact.
    """

    recorded_budgets = evidence.get("node_reroute_budgets")
    # FAIL-CLOSED gap-4: a building that ENGAGED the reroute mechanism (it carries
    # reroute-adoption/HOLD records, or HELD on a budget-related reason) MUST carry
    # its Link-owned node_reroute_budgets in the written evidence. The old code only
    # re-attached the map `if isinstance(recorded_budgets, Mapping)` and otherwise
    # SILENTLY delegated with NO budget map -- so the forward walk saw no budget and
    # HOLDed every reroute target (target_node_has_no_link_assigned_budget) = a
    # DIVERGENT HOLD. Validate instead: a present-but-malformed map (not a Mapping,
    # or non-positive-int values) ALWAYS fails closed; a missing/empty map fails
    # closed only when the building actually had reroute budgets.
    had_reroute_budgets = _building_engaged_reroute_budgets(evidence)
    decision = ResumeBudgetRecoveryDecision()
    if recorded_budgets is None:
        if had_reroute_budgets:
            raise ValueError(
                "resume corrupt evidence: this Building engaged the reroute budget "
                "mechanism (it carries reroute-adoption/HOLD budget records) but the "
                "written dynamic_walker_evidence.node_reroute_budgets is MISSING; "
                "refusing to resume with no budget map (would divergently HOLD every "
                "reroute target on target_node_has_no_link_assigned_budget)"
            )
    elif not isinstance(recorded_budgets, Mapping):
        raise ValueError(
            "resume corrupt evidence: dynamic_walker_evidence.node_reroute_budgets is "
            f"present but not a mapping ({type(recorded_budgets).__name__}); refusing to "
            "resume from a malformed budget map"
        )
    else:
        for node_ref, value in recorded_budgets.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    "resume corrupt evidence: dynamic_walker_evidence.node_reroute_budgets "
                    f"has a malformed budget for {node_ref!r} ({value!r}); a node budget must "
                    "be a positive integer -- refusing to resume from a malformed budget map"
                )
        if recorded_budgets:
            decision = ResumeBudgetRecoveryDecision(
                node_reroute_budgets=dict(recorded_budgets)
            )
        elif had_reroute_budgets:
            if action == "raise" and hold_record.get("budget_exhausted"):
                recovered_budget = _positive_int(
                    hold_record.get("node_budget"),
                    "dynamic_walker_evidence.hold.node_budget",
                )
                decision = ResumeBudgetRecoveryDecision(
                    node_reroute_budgets={pending_target: recovered_budget},
                    bridge_evidence=True,
                )
            else:
                raise ValueError(
                    "resume corrupt evidence: this Building engaged the reroute budget "
                    "mechanism but the written dynamic_walker_evidence.node_reroute_budgets "
                    "is EMPTY; refusing to resume with no budget map"
                )
    if action == "raise":
        check_evidence: Mapping[str, Any] = evidence
        if decision.bridge_evidence and decision.node_reroute_budgets is not None:
            check_evidence = {
                **evidence,
                "node_reroute_budgets": dict(decision.node_reroute_budgets),
            }
        _require_budget_exhaustion_raise(
            hold_record,
            check_evidence,
            pending_target,
        )
    return decision


def resume_admission_decision(
    *,
    evidence: Mapping[str, Any],
    disposition: Mapping[str, Any],
    declared_plan: Mapping[str, Any] | None,
    recorded_returns_loader: Callable[[], Sequence[Mapping[str, Any]]],
    completed_step_frontier_loader: Callable[[], Mapping[str, int]],
    returned_claims_present_loader: Callable[[], bool],
    enforce_raise_budget_increment: bool,
    adapter_error_stop_short_circuit: bool,
) -> ResumeAdmissionDecision:
    """Single-source resume-admission validation sequence for BOTH firing points.

    This is the ONE pure sequence the live resume path
    (``_resume_dynamic_graph_walker``) and the pre-persist intake gate
    (``validate_disposition_intake``) both delegate to, so their accept/refuse SET
    can never silently diverge (Rule 11: the writer and reader of the same
    contract share the same validation rules). Clause ORDER is the current RESUME
    order; every refusal literal is raised verbatim (module constants or the
    inline strings lifted from the old duplicated bodies). Two measured
    resume-only non-overlaps are DECLARED as caller flags rather than silently
    unified: ``adapter_error_stop_short_circuit`` (the resume-only paper-stop
    early-accept, which must precede any ledger read) and
    ``enforce_raise_budget_increment`` (the resume-only ``_positive_int`` check on
    ``budget_increment``). Ledger reads enter as caller-supplied zero-arg loaders
    invoked at the exact sequence position resume uses today, because both loaders
    raise on corrupt ledgers and today run only AFTER the paper-stop early return
    -- value-eager staging would change the resume accept set.

    Support evidence only: it performs zero writes and authors no disposition,
    Movement, route, sufficiency, quality, or success fact. Refusals raise
    ``ValueError`` with the shared literal verbatim.
    """

    if not evidence.get("held"):
        if _resume_observations(evidence):
            raise ValueError(_APPLIED_RESUME_REFUSAL)
        raise ValueError(_NOT_HELD_REFUSAL)
    hold_record = _mapping_value("dynamic_walker_evidence.hold", evidence.get("hold"))
    if declared_plan is None:
        raise ValueError(_BIRTH_CERTIFICATE_ABSENT_REFUSAL)
    action = _required_disposition_action(disposition)
    pending_target = _disposition_pending_target_ref(
        action,
        disposition=disposition,
        hold_record=hold_record,
        declared_plan=declared_plan,
    )
    validate_hold_disposition_action(action, hold_record, public_approval=False)
    budget_recovery = resume_budget_recovery_decision(
        evidence=evidence,
        action=action,
        hold_record=hold_record,
        pending_target=pending_target,
    )

    # Resume-only paper-stop early-accept: BEFORE any ledger read (the loaders
    # raise on corrupt evidence, so invoking them here would flip an
    # adapter-error-stop hold with a corrupt ledger from accept to refusal).
    if (
        adapter_error_stop_short_circuit
        and action == "stop"
        and _adapter_error_hold_without_return(hold_record)
    ):
        return ResumeAdmissionDecision(
            action=action,
            pending_target=pending_target,
            hold_record=hold_record,
            budget_recovery=budget_recovery,
            replay_returns={},
            recorded_returns=(),
            expected_replay_counts={},
            adapter_error_stop=True,
        )

    recorded_returns = list(recorded_returns_loader())
    if not recorded_returns:
        raise ValueError(_NO_RECORDED_RETURNS_REFUSAL)
    replay_returns: dict[str, list[Any]] = {}
    for item in recorded_returns:
        step_ref = _optional_text_value(item.get("step_ref")) or ""
        replay_returns.setdefault(step_ref, []).append(item.get("returned"))

    # FAIL-CLOSED gap-1 (absorbs the old _require_return_frontier_consistency):
    # the completed-step frontier is derived from the ON-DISK step-output ledger,
    # independent of raw/agent-return.jsonl.
    expected_replay_counts = dict(completed_step_frontier_loader())
    for step_ref, completed in expected_replay_counts.items():
        recorded = len(replay_returns.get(step_ref, []))
        if completed > recorded:
            raise ValueError(
                f"resume corrupt evidence: step {step_ref!r} has {completed} completed "
                f"step-output(s) on disk but only {recorded} recorded Agent return(s); "
                "the step-output frontier is ahead of raw/agent-return.jsonl -- "
                "refusing to resume before replay adoption"
            )
    if expected_replay_counts and not returned_claims_present_loader():
        raise ValueError(
            "resume corrupt evidence: required claim_trace agent/returned_claims.json "
            "is absent while completed step-output replay obligations exist -- "
            "refusing to resume before replay adoption"
        )
    for step_ref, returns in replay_returns.items():
        completed = expected_replay_counts.get(step_ref, 0)
        if len(returns) > completed:
            raise ValueError(
                f"resume corrupt evidence: step {step_ref!r} has {len(returns)} recorded "
                f"Agent return(s) but only {completed} completed step-output(s) on disk; "
                "the recorded-return ledger and the step-output ledger disagree -- "
                "refusing to resume from inconsistent evidence"
            )

    raise_budget_increment: int | None = None
    if action == "raise":
        if enforce_raise_budget_increment:
            raise_budget_increment = _positive_int(
                disposition.get("budget_increment"),
                "transition_lifecycle.budget_increment",
            )
        if pending_target not in step_ref_by_brick_from_declared(declared_plan):
            raise ValueError(_RAISE_TARGET_NOT_NODE_REFUSAL)

    return ResumeAdmissionDecision(
        action=action,
        pending_target=pending_target,
        hold_record=hold_record,
        budget_recovery=budget_recovery,
        replay_returns=replay_returns,
        recorded_returns=tuple(recorded_returns),
        expected_replay_counts=expected_replay_counts,
        raise_budget_increment=raise_budget_increment,
    )


def _disposition_pending_target_ref(
    action: str,
    *,
    disposition: Mapping[str, Any],
    hold_record: Mapping[str, Any],
    declared_plan: Mapping[str, Any],
) -> str:
    if action != "reroute":
        pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
        if not pending_target:
            raise ValueError("HOLD record is missing pending_target_ref")
        return pending_target

    pending_target = _optional_text_value(disposition.get("pending_target_ref")) or ""
    if not pending_target:
        raise ValueError("reroute disposition pending_target_ref is required")
    if pending_target.startswith("building-boundary:"):
        raise ValueError("reroute disposition pending_target_ref must be a declared Brick node")
    source_brick = _optional_text_value(hold_record.get("source_brick_ref")) or ""
    if source_brick and pending_target == source_brick:
        raise ValueError("reroute disposition pending_target_ref must not be the held source Brick")
    if pending_target not in step_ref_by_brick_from_declared(declared_plan):
        raise ValueError("reroute disposition pending_target_ref is not an existing Brick node")
    return pending_target


def _adapter_error_hold_without_return(hold_record: Mapping[str, Any]) -> bool:
    if _optional_text_value(hold_record.get("hold_reason")) == "adapter_error_frontier":
        return True
    reason_refs = hold_record.get("transition_lifecycle_reason_refs")
    if not isinstance(reason_refs, list):
        return False
    return any(
        isinstance(ref, str) and "adapter_error_frontier" in ref
        for ref in reason_refs
    )


def _paper_stop_adapter_error_hold(
    root: Path,
    *,
    declared_plan: Mapping[str, Any],
    plan_ref: str,
    evidence: Mapping[str, Any],
    hold_record: Mapping[str, Any],
    disposition: Mapping[str, Any],
    paused_at_ref: str,
    pending_target: str,
    author_ref: str,
    checked_proof_limits: tuple[str, ...],
) -> BuildingPlanSupportResult:
    building_id = root.name
    closed_boundary = f"building-boundary:{building_id}-ended-by-disposition-closed"
    lifecycle = _resumed_lifecycle_from_hold(
        hold_record,
        paused_at_ref=paused_at_ref,
        disposition_action="stop",
        budget_increment=None,
    )
    link_path = root / "raw" / "link.jsonl"
    raw_ref = _next_link_raw_ref(link_path)
    link_record = graph_ready_json_object(
        {
            "raw_ref": raw_ref,
            "raw_refs": [raw_ref],
            "building_id": building_id,
            "step_ref": _optional_text_value(hold_record.get("source_step_ref")) or "",
            "source_brick_instance_ref": _optional_text_value(
                hold_record.get("source_brick_ref")
            )
            or _optional_text_value(hold_record.get("target_brick"))
            or "",
            "target_brick_instance_ref": closed_boundary,
            "target": closed_boundary,
            "transition_record_created": True,
            "transition_author_ref": author_ref,
            "movement_source": "human/COO stop disposition ended adapter-error hold without AgentFact",
            "building_lifecycle_state": "closed",
            "building_lifecycle_reason": "ended-by-disposition",
            "transition_lifecycle_state": "resumed",
            "transition_lifecycle_progress_state": "in_progress",
            "transition_lifecycle_paused_at_ref": lifecycle.get("paused_at_ref", ""),
            "transition_lifecycle_resumed_from_ref": lifecycle.get("resumed_from_ref", ""),
            "transition_lifecycle_from_brick_ref": lifecycle.get("from_brick_ref", ""),
            "transition_lifecycle_pending_target_ref": lifecycle.get("pending_target_ref", ""),
            "transition_lifecycle_required_disposition_owner": lifecycle.get(
                "required_disposition_owner",
                "",
            ),
            "transition_lifecycle_disposition_action": "stop",
            "transition_lifecycle_reason_refs": list(lifecycle.get("reason_refs", ())),
            "proof_limits": [
                "paper stop disposition support evidence only",
                "no AgentFact was created for the held adapter-error step",
                "no provider or adapter call was made by this resume path",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "semantic correctness of the stopped work",
                "whether caller/COO should launch a different Building",
            ],
        },
        building_id=building_id,
        local_id=f"raw/link.jsonl#{raw_ref.rsplit(':', maxsplit=1)[-1]}",
        recorded_at=graph_ready_timestamp(),
        event_type="bp.raw.link",
        subject=closed_boundary,
    )
    _append_jsonl_record(link_path, link_record)
    manifest_path = root / "raw" / "raw-manifest.json"
    _rewrite_raw_manifest_with_link_records(manifest_path, building_id, link_path)
    evidence_manifest_path = root / "evidence" / "evidence-manifest.json"
    resume_observation = build_resume_observation(
        resumed_from=paused_at_ref,
        paused_at_ref=paused_at_ref,
        pending_target_ref=pending_target,
        disposition_action="stop",
        applied="ended-by-disposition",
        budget_increment=0,
        node_budget=0,
        node_landings=0,
        proof_limits=[
            "support resume observation only",
            "adapter-error stop was recorded without Agent replay",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        not_proven=[
            "semantic correctness of stopped work",
            "future Building outcome",
        ],
        disposition_row_provenance=(
            dict(disposition.get("selected_row_provenance"))
            if isinstance(disposition.get("selected_row_provenance"), Mapping)
            else {}
        ),
    )
    _rewrite_paper_stop_evidence_manifest(
        evidence_manifest_path,
        plan_ref=plan_ref,
        declared_plan=declared_plan,
        evidence=evidence,
        hold_record=hold_record,
        resume_observation=resume_observation,
        raw_ref=raw_ref,
    )
    written_files = (link_path, manifest_path, evidence_manifest_path)
    building_map_path = root / "work" / "building-map.json"
    building_map_packet = _read_json_mapping(building_map_path)
    return BuildingPlanSupportResult(
        building_id=building_id,
        plan_ref=plan_ref,
        step_results=(),
        lifecycle_write=BuildingLifecycleWriteResult(
            root=root,
            written_files=written_files,
            proof_limits=checked_proof_limits,
        ),
        building_map_write=BuildingMapWriteResult(
            root=root,
            path=building_map_path,
            written_files=(),
        ),
        written_files=written_files,
        capture_event_types=(),
        building_map_packet=building_map_packet,
        proof_limits=_merge_texts(checked_proof_limits, resume_observation.get("proof_limits")),
        not_proven=_merge_texts(resume_observation.get("not_proven")),
    )


def _building_engaged_reroute_budgets(evidence: Mapping[str, Any]) -> bool:
    """True iff this held Building engaged the reroute-budget mechanism.

    FAIL-CLOSED gap-4 support. A building engaged reroute budgets if it carries any
    reroute-adoption record (an adopted landing draws a node budget) OR its HOLD is
    a budget-related HOLD (budget_exhausted / a budget-keyed hold_reason). Such a
    building MUST carry node_reroute_budgets in evidence; a missing/empty map is
    corrupt. A purely non-reroute HOLD (e.g. an ambiguous/none address pause that is
    budget-free) legitimately may have no budgets, so this returns False for it.
    """

    records = evidence.get("reroute_adoption_records")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            # An ADOPTED landing (not a HOLD) draws a node budget.
            if not record.get("disposition_required"):
                return True
            # A budget-exhaustion / unbudgeted-target HOLD engaged the budget axis.
            if record.get("budget_exhausted"):
                return True
            reason = str(record.get("hold_reason") or "")
            if "budget" in reason:
                return True
    hold = evidence.get("hold")
    if isinstance(hold, Mapping):
        if hold.get("budget_exhausted"):
            return True
        if "budget" in str(hold.get("hold_reason") or ""):
            return True
    return False


def _next_link_raw_ref(link_path: Path) -> str:
    max_index = 0
    for record in _jsonl_records(link_path):
        raw_ref = _optional_text_value(record.get("raw_ref")) or ""
        if not raw_ref.startswith("raw:link:"):
            continue
        suffix = raw_ref.rsplit(":", maxsplit=1)[-1]
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return f"raw:link:{max_index + 1:02d}"


def _append_jsonl_record(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        )


def _rewrite_raw_manifest_with_link_records(
    manifest_path: Path,
    building_id: str,
    link_path: Path,
) -> None:
    manifest = _read_json_mapping(manifest_path)
    entries_value = manifest.get("entries")
    entries = (
        [dict(entry) for entry in entries_value if isinstance(entry, Mapping)]
        if isinstance(entries_value, list)
        else []
    )
    raw_refs_value = manifest.get("raw_refs")
    raw_refs = (
        [str(ref) for ref in raw_refs_value if isinstance(ref, str)]
        if isinstance(raw_refs_value, list)
        else []
    )
    link_refs = [
        ref
        for record in _jsonl_records(link_path)
        for ref in _raw_refs_from_mapping(record)
    ]
    for ref in link_refs:
        if ref not in raw_refs:
            raw_refs.append(ref)
    _merge_raw_manifest_entry(entries, raw_refs=link_refs)
    manifest["building_id"] = str(manifest.get("building_id") or building_id)
    manifest["raw_refs"] = raw_refs
    manifest["entries"] = entries
    _write_json_mapping(manifest_path, manifest)


def _merge_raw_manifest_entry(
    entries: list[dict[str, Any]],
    *,
    raw_refs: list[str],
) -> None:
    cleaned = [ref for ref in dict.fromkeys(raw_refs) if ref]
    for entry in entries:
        if entry.get("path") != "raw/link.jsonl":
            continue
        existing = (
            list(entry.get("raw_refs", ()))
            if isinstance(entry.get("raw_refs"), list)
            else []
        )
        for ref in cleaned:
            if ref not in existing:
                existing.append(ref)
        entry.update(
            {
                "source": "support/operator/walker_resume.py paper stop disposition record",
                "content_shape": "jsonl Link transition rows and disposition records",
                "proof_limit": "support evidence only",
                "axis_owner": "Link",
                "record_role": "primary",
                "raw_refs": existing,
            }
        )
        return
    entries.append(
        {
            "path": "raw/link.jsonl",
            "source": "support/operator/walker_resume.py paper stop disposition record",
            "content_shape": "jsonl Link transition rows and disposition records",
            "proof_limit": "support evidence only",
            "axis_owner": "Link",
            "record_role": "primary",
            "raw_refs": cleaned,
        }
    )


def _rewrite_paper_stop_evidence_manifest(
    path: Path,
    *,
    plan_ref: str,
    declared_plan: Mapping[str, Any],
    evidence: Mapping[str, Any],
    hold_record: Mapping[str, Any],
    resume_observation: Mapping[str, Any],
    raw_ref: str,
) -> None:
    manifest = _read_json_mapping(path)
    plan_copy = dict(declared_plan)
    dynamic_evidence = dict(evidence)
    observations = [
        dict(item)
        for item in dynamic_evidence.get("resume_observations", ())
        if isinstance(item, Mapping)
    ]
    observations.append(dict(resume_observation))
    dynamic_evidence["held"] = False
    dynamic_evidence["hold"] = dict(hold_record)
    dynamic_evidence["resume_observations"] = observations
    dynamic_evidence["proof_limits"] = list(
        _merge_texts(
            dynamic_evidence.get("proof_limits"),
            resume_observation.get("proof_limits"),
        )
    )
    dynamic_evidence["not_proven"] = list(
        _merge_texts(
            dynamic_evidence.get("not_proven"),
            resume_observation.get("not_proven"),
        )
    )
    plan_copy["dynamic_walker_evidence"] = dynamic_evidence
    manifest["plan_snapshot"] = _plan_snapshot(plan_ref, plan_copy)
    manifest["frontier_observation"] = (
        "Adapter-error hold ended by human/COO stop disposition without AgentFact replay"
    )
    manifest["paper_stop_observation"] = {
        "kind": "adapter_error_paper_stop_observation",
        "raw_ref": raw_ref,
        "held_step_returned": False,
        "provider_invoked": False,
        "proof_limits": [
            "support evidence only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of stopped work",
            "future Building outcome",
        ],
    }
    _write_json_mapping(path, manifest)


def _raw_refs_from_mapping(record: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    raw_ref = record.get("raw_ref")
    if isinstance(raw_ref, str) and raw_ref.strip():
        refs.append(raw_ref)
    raw_refs = record.get("raw_refs")
    if isinstance(raw_refs, list):
        refs.extend(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
    return list(dict.fromkeys(refs))


def _read_json_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: JSON value must be an object")
    return dict(value)


def _write_json_mapping(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_written_dynamic_plan(root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    manifest = root / "evidence" / "evidence-manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("evidence-manifest.json must contain a mapping")
    snapshot = _mapping_value("evidence_manifest.plan_snapshot", value.get("plan_snapshot"))
    plan_copy = _optional_text_value(snapshot.get("plan_rows_copy"))
    if not plan_copy:
        raise ValueError("written Building evidence is missing plan_snapshot.plan_rows_copy")
    plan = json.loads(plan_copy)
    if not isinstance(plan, Mapping):
        raise ValueError("plan_snapshot.plan_rows_copy must decode to a mapping")
    evidence = _mapping_value(
        "plan_snapshot.dynamic_walker_evidence",
        plan.get("dynamic_walker_evidence"),
    )
    if evidence.get("walker_mode") != "dynamic":
        raise ValueError("written dynamic_walker_evidence must carry walker_mode=dynamic")
    return plan, evidence


def _declared_graph_plan_from_birth_certificate(root: Path) -> Mapping[str, Any] | None:
    """Recover the PURE declared graph plan from the Building birth-certificate.

    ``work/declared-building-plan.json`` (declaration_packets.py) records the
    ORIGINAL graph plan -- full topology: ``groups`` + ``link_edges`` -- before
    linearization. This is the SAME plan the forward walk received, so handing it
    back to ``_run_dynamic_graph_walker`` rebuilds the IDENTICAL graph scheduler
    (fan-in wait-all, cohort re-verify, nested handling). Read-only; returns None
    for a non-graph or absent/unreadable declaration so the caller STOPs rather
    than resume from the linearized snapshot (which would drop the fan topology).
    """

    try:
        declared_plan = latest_valid_declared_plan(root)
    except ValueError:
        return None
    if not isinstance(declared_plan, Mapping):
        return None
    if _optional_text_from_mapping(declared_plan, "plan_shape") != "graph":
        return None
    return declared_plan


def _brick_ref_by_step_ref_from_declared(declared_plan: Mapping[str, Any]) -> dict[str, str]:
    linear_plan, _graph_context = _linear_plan_from_graph_plan(declared_plan)
    refs: dict[str, str] = {}
    for step in linear_plan.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        step_ref = _optional_text_value(step.get("step_ref"))
        if step_ref:
            refs[step_ref] = _brick_instance_ref_from_linear_step(step)
    return refs


def _expansion_node_budgets_from_revision_chain(
    root: Path,
    *,
    declared_plan: Mapping[str, Any],
    evidence_budgets: Mapping[str, int],
) -> dict[str, int]:
    """Read valid revision expansion budgets as new-node-only resume overlay.

    Revision packets store ``expansion_node_budgets`` by the new ``step_ref`` they
    admitted; the dynamic walker consumes reroute budgets by Brick instance ref.
    Translate through the recovered latest plan and overlay only keys absent from
    written dynamic-walker evidence, so pre-revision evidence remains authoritative.
    """

    step_to_brick = _brick_ref_by_step_ref_from_declared(declared_plan)
    declared_bricks = set(step_to_brick.values())
    evidence_keys = set(evidence_budgets)
    expansion_budgets: dict[str, int] = {}
    for packet in _valid_revision_chain_packets(root)[1:]:
        raw = packet.get("expansion_node_budgets")
        if raw is None:
            continue
        if not isinstance(raw, Mapping):
            raise ValueError("declared plan revision expansion_node_budgets must be a mapping")
        for key, value in raw.items():
            budget_key = _optional_text_value(key)
            if not budget_key:
                raise ValueError("declared plan revision expansion_node_budgets keys must be non-empty strings")
            brick_ref = step_to_brick.get(budget_key) or (
                budget_key if budget_key in declared_bricks else ""
            )
            if not brick_ref:
                raise ValueError(
                    "declared plan revision expansion_node_budgets key does not resolve "
                    "to a declared Brick node: " + budget_key
                )
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    "declared plan revision expansion_node_budgets has a malformed "
                    f"budget for {budget_key!r} ({value!r}); a node budget must be "
                    "a positive integer"
                )
            if brick_ref not in evidence_keys:
                expansion_budgets[brick_ref] = value
    return expansion_budgets


def step_ref_by_brick_from_declared(declared_plan: Mapping[str, Any]) -> set[str]:
    """The set of declared Brick instance refs in the recovered graph plan.

    Used to validate a raise disposition's pending_target_ref is an existing node
    (parity with the prior resume verb's guard) without re-linearizing the plan.
    """

    linear_plan, _graph_context = _linear_plan_from_graph_plan(declared_plan)
    bricks: set[str] = set()
    for step in linear_plan.get("steps", []):
        if isinstance(step, Mapping):
            ref = _brick_instance_ref_from_linear_step(step)
            if ref:
                bricks.add(ref)
    return bricks


def _resume_observations(evidence: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = evidence.get("resume_observations", [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _disposition_void_observations(
    root: Path,
    current_hold_ref: str,
) -> set[tuple[str, int]]:
    """The (voided_raw_ref, same_hold_index) pairs a valid void row covers.

    D2 (0706 self-lock correction path). Reads the human/COO-authored
    ``disposition_void_observation`` rows in raw/link.jsonl that address THE
    CURRENT hold identity and returns the set of residual-row discriminators they
    void. Fail-closed: a void row addressed to this hold that is MALFORMED
    (foreign author, missing/blank voided raw_ref, or a non-positive
    same_hold_index) raises loudly rather than silently voiding nothing (I5 void
    groundedness). A void row addressed to a DIFFERENT hold is not this hold's
    concern and is skipped without inspection.

    This helper authors nothing; it only reports which residual rows a recorded
    void makes unselectable. It never chooses Movement, route, sufficiency,
    quality, or success.
    """

    voids: set[tuple[str, int]] = set()
    for record in _jsonl_records(root / "raw" / "link.jsonl"):
        if _optional_text_value(record.get("kind")) != DISPOSITION_VOID_RECORD_KIND:
            continue
        row_hold_ref = _optional_text_value(record.get("paused_at_ref"))
        if row_hold_ref != current_hold_ref:
            continue
        author_ref = _disposition_author_ref(record)
        if not author_ref.startswith(_HUMAN_AUTHOR_PREFIXES):
            raise ValueError(
                "disposition_void_observation author must start with human: or coo:"
            )
        voided_raw_ref = _optional_text_value(record.get("voided_raw_ref"))
        if not voided_raw_ref:
            raise ValueError(
                "disposition_void_observation is missing voided_raw_ref"
            )
        same_hold_index = record.get("same_hold_index")
        if (
            isinstance(same_hold_index, bool)
            or not isinstance(same_hold_index, int)
            or same_hold_index < 1
        ):
            raise ValueError(
                "disposition_void_observation same_hold_index must be a positive integer"
            )
        voids.add((voided_raw_ref, same_hold_index))
    return voids


def disposition_rows_for_current_hold(
    root: Path,
    hold_record: Mapping[str, Any],
) -> list[tuple[str, int]]:
    """The (raw_ref, 1-based same-hold index) of every disposition row in
    raw/link.jsonl addressed to THE CURRENT hold identity, in file order.

    D2 grounding support. Mirrors the matching predicate ``_read_disposition_row``
    uses (disposition_action present; hold-identity fields all equal the current
    hold; non-reroute rows must still name the held pending target) WITHOUT the
    void skip -- so a void verb can confirm the residual row it is asked to void
    actually exists before appending a void record (refuse groundless voids). It
    reads only; it authors no disposition, Movement, route, sufficiency, quality,
    or success.
    """

    hold_pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
    if not hold_pending_target:
        raise ValueError("HOLD record is missing pending_target_ref")
    current_hold_ref = _hold_paused_at_ref(hold_record)
    rows: list[tuple[str, int]] = []
    index = 0
    for record in _jsonl_records(root / "raw" / "link.jsonl"):
        lifecycle = _flattened_or_nested_transition_lifecycle(record)
        action = _optional_text_value(lifecycle.get("disposition_action"))
        if not action:
            continue
        row_pending_target = _optional_text_value(lifecycle.get("pending_target_ref")) or ""
        if action != "reroute" and row_pending_target != hold_pending_target:
            continue
        row_hold_refs = [
            value
            for value in (
                _optional_text_value(lifecycle.get("paused_at_ref")),
                _optional_text_value(lifecycle.get("resumed_from_ref")),
            )
            if value
        ]
        if not row_hold_refs or any(value != current_hold_ref for value in row_hold_refs):
            continue
        index += 1
        rows.append((_optional_text_value(record.get("raw_ref")) or "", index))
    return rows


def _read_disposition_row(
    root: Path,
    hold_record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """The LATEST raw/link.jsonl disposition row addressed to THE CURRENT hold.

    FIX 2 (0611 eligibility creep, "THIS resume only"): matching on
    ``pending_target_ref`` ALONE accepted a STALE row -- e.g. the recorded
    resumed-lifecycle row of a PREVIOUS resume of the SAME target -- as the
    current disposition. The row must additionally reference the CURRENT hold's
    identity string ``_hold_paused_at_ref(hold_record)``. That identity is
    collision-free across walk generations (0611 codex re-review BLOCKER fix):
    the bare reroute_ref embeds adoption_sequence_number, which RESETS each
    walk, so two same-target holds in different generations could share it and
    a stale prior-resume row (the stamped resumed-lifecycle row survives in the
    rewritten ledger) matched the current hold; the identity now also carries
    the held occurrence's source_step_ref + cascade_depth + attempt_number (see
    ``walker_hold._hold_paused_at_ref``), so the row must echo the EXACT
    current-generation hold -- which requires the attempt_number to match too.
    The disposition row's ``paused_at_ref`` / ``resumed_from_ref`` (the
    identity fields a disposition row actually carries in raw/link.jsonl) must
    equal it. A row that matches the target but NOT the current hold identity
    is NOT this resume's row and is SKIPPED; if none match, return None
    (fail-closed: the caller refuses to resume; nothing boards).

    FIX 3 (replay provenance): the selected row's discriminator is attached
    under ``selected_row_provenance`` (data only) so an auditor replaying the
    SAME selection rule -- file-order scan of raw/link.jsonl rows carrying a
    ``disposition_action`` whose hold identity matches the current hold (and, for
    non-reroute dispositions, whose ``pending_target_ref`` still names the held
    target), take the LAST -- lands on the SAME row deterministically. For
    reroute dispositions, ``pending_target_ref`` is the human/COO-selected target.
    HONEST LIMIT (0611): raw/link.jsonl is REWRITTEN (write_text, not appended;
    see raw_claim_trace._write_jsonl) on every walk, so any file-positional
    discriminator (offset, line number, match index) dangles across a resume:
    the human-appended row is not preserved verbatim and the post-resume ledger
    carries the STAMPED resumed-lifecycle row instead. The durable discriminator
    is therefore the STABLE pair (the generation-unique hold identity above --
    which embeds attempt_number and the reroute context -- plus the row's own
    ``raw_ref``); ``disposition_row_same_hold_index`` (1-based file-order index
    among matching rows; the selected row is the last, so index == match count)
    is carried as PRE-RESUME-SNAPSHOT-relative data only, valid against the
    ledger as it was when this selection ran, not against a later rewrite.
    """

    hold_pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
    if not hold_pending_target:
        raise ValueError("HOLD record is missing pending_target_ref")
    current_hold_ref = _hold_paused_at_ref(hold_record)
    # D2 (0706 self-lock correction path): collect the human/COO-authored
    # disposition-void observation rows for THIS hold first. A valid void makes a
    # SPECIFIC residual disposition row (keyed by hold identity + voided raw_ref +
    # 1-based same-hold match index) unselectable below. It NEVER creates, edits,
    # or reorders a disposition (I3); with nothing else matching, the EXISTING
    # fail-closed 'no human/COO disposition row found' refusal fires downstream.
    voids = _disposition_void_observations(root, current_hold_ref)
    selected_record: Mapping[str, Any] | None = None
    selected_lifecycle: dict[str, Any] | None = None
    matching_row_count = 0
    for record in _jsonl_records(root / "raw" / "link.jsonl"):
        lifecycle = _flattened_or_nested_transition_lifecycle(record)
        action = _optional_text_value(lifecycle.get("disposition_action"))
        if not action:
            continue
        row_pending_target = _optional_text_value(lifecycle.get("pending_target_ref")) or ""
        if action != "reroute" and row_pending_target != hold_pending_target:
            continue
        # FIX 2: the row must reference THE CURRENT hold. Every identity field
        # the row carries must equal the current hold's ref; a row carrying
        # NEITHER field cannot be scoped to this hold -> skip (fail-closed).
        row_hold_refs = [
            value
            for value in (
                _optional_text_value(lifecycle.get("paused_at_ref")),
                _optional_text_value(lifecycle.get("resumed_from_ref")),
            )
            if value
        ]
        if not row_hold_refs or any(value != current_hold_ref for value in row_hold_refs):
            continue
        matching_row_count += 1
        # D2: a valid void covering (this hold identity, this row's raw_ref, this
        # 1-based match index) makes the row unselectable. The match index is
        # counted BEFORE the skip so it stays the same file-order discriminator a
        # void authored against the pre-void snapshot named.
        if (
            _optional_text_value(record.get("raw_ref")),
            matching_row_count,
        ) in voids:
            continue
        selected_record = record
        selected_lifecycle = dict(lifecycle)
    if selected_record is None or selected_lifecycle is None:
        return None
    state = _optional_text_value(selected_lifecycle.get("state"))
    if state != "resumed":
        raise ValueError("disposition transition_lifecycle.state must be resumed")
    author_ref = _disposition_author_ref(selected_record)
    if not author_ref.startswith(_HUMAN_AUTHOR_PREFIXES):
        raise ValueError("disposition row author must start with human: or coo:")
    disposition = dict(selected_lifecycle)
    disposition["author_ref"] = author_ref
    disposition["selected_row_provenance"] = {
        "disposition_row_paused_at_ref": current_hold_ref,
        "disposition_row_raw_ref": _optional_text_value(selected_record.get("raw_ref"))
        or "",
        "disposition_row_same_hold_index": matching_row_count,
    }
    return disposition


def validate_disposition_intake(
    building_root: Path | str,
    row: Mapping[str, Any],
    *,
    repo_root: Path | str,
) -> None:
    """D1 (validate-before-persist): raise the resume path's OWN refusal literal
    for a would-be disposition ``row`` BEFORE it is appended to raw/link.jsonl.

    Support wrappers (``onboard.run_approve_entry``) call this AFTER constructing
    the disposition row and BEFORE the raw/link.jsonl append. A refused intake
    therefore leaves the ledger byte-identical (invariant I1) and the human/COO
    may retry with a corrected row. It adds NO new rejection semantics: it
    DELEGATES, in the SAME order, to the SAME pure validators the live resume path
    (``_resume_dynamic_graph_walker``) runs -- so the accept/refuse SET stays
    identical by construction (invariant I2), and the shared refusal literals are
    the module constants both firing points raise (no literal drift). The only
    addition is one intake-only identity assertion: the row's hold-identity field
    must equal ``_hold_paused_at_ref(hold_record)`` so ``_read_disposition_row``
    will actually SELECT the row about to persist -- closing the hold-identity
    drift self-lock (a persisted-then-unselectable row) as a pre-persist refusal.

    It authors no disposition, Movement, route, sufficiency, quality, or success;
    it only re-runs the resume-path validations earlier. On any refusal it raises
    ``ValueError`` with the delegated literal verbatim.
    """

    root = Path(building_root).resolve()
    repo = Path(repo_root).resolve()
    _plan, evidence = _read_written_dynamic_plan(root)

    # Build the disposition mapping the SAME way _read_disposition_row does (flat
    # transition_lifecycle_* keys -> lifecycle dict + author_ref) so the delegated
    # validators see the identical shape.
    disposition = _flattened_or_nested_transition_lifecycle(row)
    disposition["author_ref"] = _disposition_author_ref(row)

    declared_plan = _declared_graph_plan_from_birth_certificate(root)

    # SINGLE-SOURCE resume admission (D1/D2): delegate the whole overlapping
    # validation clause chain to the SAME pure sequence the live resume path
    # runs, so the accept/refuse SET stays identical by construction (invariant
    # I2). Intake does NOT enforce the resume-only budget_increment check and
    # does NOT take the resume-only paper-stop early-accept (both flags False) --
    # the measured resume-only divergences are preserved, not silently unified.
    decision = resume_admission_decision(
        evidence=evidence,
        disposition=disposition,
        declared_plan=declared_plan,
        recorded_returns_loader=lambda: _recorded_agent_returns(root),
        completed_step_frontier_loader=lambda: _completed_step_frontier(root),
        returned_claims_present_loader=lambda: (
            root / "evidence" / "claim_trace" / "agent" / "returned_claims.json"
        ).is_file(),
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    hold_record = decision.hold_record

    _validated_resume_re_instruction(decision.action, disposition, repo=repo)

    # Intake-only identity assertion (the drift self-lock closer): the row must
    # echo the CURRENT hold identity so _read_disposition_row will select it.
    current_hold_ref = _hold_paused_at_ref(hold_record)
    row_hold_refs = [
        value
        for value in (
            _optional_text_value(disposition.get("paused_at_ref")),
            _optional_text_value(disposition.get("resumed_from_ref")),
        )
        if value
    ]
    if not row_hold_refs or any(value != current_hold_ref for value in row_hold_refs):
        raise ValueError(
            "disposition intake: the disposition row's hold identity "
            f"({row_hold_refs!r}) does not match the current hold "
            f"({current_hold_ref!r}); refusing to persist a row the resume read "
            "would not select (hold-identity drift self-lock guard)"
        )


def _flattened_or_nested_transition_lifecycle(record: Mapping[str, Any]) -> dict[str, Any]:
    nested = record.get("transition_lifecycle")
    if isinstance(nested, Mapping):
        return dict(nested)
    prefix = "transition_lifecycle_"
    lifecycle: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(key, str) and key.startswith(prefix):
            lifecycle[key.removeprefix(prefix)] = value
    return lifecycle


def _disposition_author_ref(record: Mapping[str, Any]) -> str:
    for key in (
        "transition_author_ref",
        "author_ref",
        "route_replay_author_ref",
    ):
        value = _optional_text_value(record.get(key))
        if value:
            return value
    authoring = record.get("transition_authoring")
    if isinstance(authoring, Mapping):
        value = _optional_text_value(authoring.get("author_ref"))
        if value:
            return value
    return ""


def _recorded_agent_returns(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    occurrence_by_step: dict[str, int] = {}
    for record in _jsonl_records(root / "raw" / "agent-return.jsonl"):
        step_ref = _optional_text_value(record.get("step_ref"))
        if not step_ref:
            raise ValueError("raw/agent-return.jsonl record missing step_ref")
        occurrence_by_step[step_ref] = occurrence_by_step.get(step_ref, 0) + 1
        records.append(
            {
                "step_ref": step_ref,
                "returned": record.get("returned"),
                "recorded_at": _step_output_recorded_at(
                    root,
                    step_ref,
                    occurrence_by_step[step_ref],
                ),
                # U5.5 RESUME-GATE-RECORD: read back the gate-sequence decision the
                # step recorded AT-TIME (or None) so replay can RECONSTRUCT it
                # without recomputing it. Occurrence-matched like recorded_at.
                "gate_sequence_decision_record": _step_output_gate_sequence_record(
                    root,
                    step_ref,
                    occurrence_by_step[step_ref],
                ),
            }
        )
    return records


def _step_output_recorded_at(root: Path, step_ref: str, occurrence: int) -> str:
    matches = _step_output_field_matches(root, step_ref, "recorded_at")
    if matches:
        index = max(0, min(len(matches) - 1, occurrence - 1))
        return _optional_text_value(matches[index]) or ""
    return ""


def _step_output_gate_sequence_record(
    root: Path,
    step_ref: str,
    occurrence: int,
) -> Mapping[str, Any] | None:
    """The gate-sequence decision record this step persisted AT-TIME (or None).

    U5.5 RESUME-GATE-RECORD. Occurrence-matched mirror of ``_step_output_recorded_at``:
    reads the matching step-output.json's ``gate_sequence_decision_record`` so the
    replay path can READ the recorded decision back (it never recomputes). Absent
    when the step declared no gate policy (the key is omitted from step-output.json).
    """

    matches = _step_output_field_matches(root, step_ref, "gate_sequence_decision_record")
    if not matches:
        return None
    index = max(0, min(len(matches) - 1, occurrence - 1))
    value = matches[index]
    # codex P1 fix: distinguish ABSENT from PRESENT-MALFORMED. A None value is the
    # legitimate no-policy case (the key is omitted from step-output.json). A value
    # that is PRESENT but NOT a JSON object (e.g. [] / a string from a corrupt write)
    # must FAIL CLOSED — returning None would silently DROP a recorded gate decision
    # the replay should have read back.
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(
            f"{root}: step {step_ref!r} occurrence {occurrence} has a present but "
            f"non-object gate_sequence_decision_record ({type(value).__name__}); "
            "refusing to silently drop a recorded gate decision"
        )
    return value


def _completed_step_frontier(root: Path) -> dict[str, int]:
    """Per step_ref, the count of occurrences that COMPLETED before the HOLD.

    FAIL-CLOSED gap-1 support. Derived from the ON-DISK step-output ledger
    (``work/step-outputs/<slug>/step-output.json``) -- the authoritative record of
    which step occurrences actually completed and were written -- so it is
    INDEPENDENT of ``raw/agent-return.jsonl``. A missing/short agent-return line
    therefore cannot lower this frontier and masquerade a pre-HOLD step as a
    continued (run-live) one. Each completed step-output.json contributes one
    occurrence to its ``step_ref``. FAIL CLOSED on a missing/invalid attempt_index
    or a duplicate attempt slot (parity with ``_step_output_field_matches``).
    """

    attempts_by_step: dict[str, set[int]] = {}
    for path in (root / "work" / "step-outputs").glob("*/step-output.json"):
        # FAIL-CLOSED gap-1 (B1): a MALFORMED or NON-OBJECT step-output.json must
        # NOT be silently skipped. Skipping it lowers the completed-step frontier,
        # which (combined with a missing/short raw return) makes a COMPLETED pre-HOLD
        # step look like a continued/post-HOLD step and re-run LIVE -- a provider
        # re-call that hides corrupt evidence. A completed step-output ledger entry
        # is a replay OBLIGATION; corrupt evidence raises rather than converting it
        # into a live run.
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"resume: corrupt step-output ledger {path} (malformed JSON: {exc}) -- "
                "refusing to resume (would convert a replay obligation into a live run)"
            ) from exc
        if not isinstance(value, Mapping):
            raise ValueError(
                f"resume: corrupt step-output ledger {path} (non-object step-output: "
                f"{type(value).__name__}) -- refusing to resume (would convert a replay "
                "obligation into a live run)"
            )
        step_ref = _optional_text_value(value.get("step_ref"))
        if not step_ref:
            raise ValueError(
                f"resume: corrupt step-output ledger {path} (missing/empty step_ref) -- "
                "refusing to resume (would convert a replay obligation into a live run)"
            )
        attempt = value.get("attempt_index")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise ValueError(
                f"{path}: step-output for {step_ref!r} has a missing/invalid "
                f"attempt_index ({attempt!r}); cannot derive the completed-step frontier"
            )
        slots = attempts_by_step.setdefault(step_ref, set())
        if attempt in slots:
            raise ValueError(
                f"{root}: duplicate attempt_index {attempt} for step {step_ref!r}; "
                "completed-step frontier is ambiguous"
            )
        slots.add(attempt)
    return {step_ref: len(slots) for step_ref, slots in attempts_by_step.items()}


def _step_output_field_matches(root: Path, step_ref: str, field: str) -> list[Any]:
    # codex P1 fix: order the matching step-output occurrences by NUMERIC attempt_index,
    # NOT by lexical path. Step-output dirs are "<slug>-attempt-N" with NO zero-padding,
    # so a step run 10+ times sorts lexically as attempt-1, attempt-10, attempt-2 — which
    # would pair raw-return occurrence k with the WRONG attempt's recorded value (e.g. the
    # gate_sequence_decision_record / recorded_at of attempt-10 for occurrence 2). Sort by
    # the step-output body's integer attempt_index instead. FAIL CLOSED on a missing /
    # non-int attempt_index, or a DUPLICATE attempt_index for this step_ref (an ambiguous
    # occurrence slot). A malformed (unparseable) step-output.json is skipped as before.
    by_attempt: dict[int, Any] = {}
    for path in (root / "work" / "step-outputs").glob("*/step-output.json"):
        # FAIL-CLOSED gap-1 (B1): a MALFORMED step-output.json must NOT be silently
        # skipped here either -- a corrupt ledger entry could belong to THIS step_ref
        # but be unreadable, lowering the per-step occurrence count and masquerading a
        # completed occurrence as a continued (run-live) one. A NON-OBJECT step-output
        # is rejected by _completed_step_frontier (run before this); here we fail
        # closed on malformed JSON and only skip cleanly-parsed entries for OTHER
        # step_refs.
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"resume: corrupt step-output ledger {path} (malformed JSON: {exc}) -- "
                "refusing to resume (would convert a replay obligation into a live run)"
            ) from exc
        if not (isinstance(value, Mapping) and value.get("step_ref") == step_ref):
            continue
        attempt = value.get("attempt_index")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise ValueError(
                f"{path}: step-output for {step_ref!r} has a missing/invalid "
                f"attempt_index ({attempt!r}); cannot order resume occurrences"
            )
        if attempt in by_attempt:
            raise ValueError(
                f"{root}: duplicate attempt_index {attempt} for step {step_ref!r}; "
                "resume occurrence ordering is ambiguous"
            )
        by_attempt[attempt] = value.get(field)
    return [by_attempt[attempt] for attempt in sorted(by_attempt)]
