"""Resume-after-HOLD verb for the bounded agent-proposed dynamic graph walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
resume verb over the admitted dynamic walker (NOT a third walker_mode) plus its
orchestration helpers -- reading the written plan snapshot / dynamic_walker
evidence / recorded Agent returns / the human-or-COO-authored disposition Link
row, replaying completed steps from recorded payloads, reconstructing the
residual queue after the HOLD, and continuing the live queue per the disposition
action (raise / forward / stop) -- were lifted out of the dynamic_walker
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.link.transition import (
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
    _optional_text_from_mapping,
    _optional_text_value,
)
from brick_protocol.support.operator.walker_hold import (
    _hold_paused_at_ref,
)
from brick_protocol.support.operator.walker_kernel import (
    ResumeSeed,
    _run_dynamic_graph_walker,
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
            raise ValueError("dynamic Building already has an applied resume disposition")
        raise ValueError("resume_building_plan requires a held dynamic_walker_evidence record")
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
    if declared_plan is None:
        raise ValueError(
            "resume requires the declared-building-plan.json birth-certificate "
            "(full graph topology) to rehydrate the forward walk; it is absent or "
            "unreadable -- refusing to resume from the linearized snapshot alone "
            "(would drop fan-in/cohort/nested behaviour)"
        )
    # RE-ATTACH the Link-owned node_reroute_budgets onto the recovered declared
    # plan. The birth-certificate STRIPS runtime walker keys (incl.
    # node_reroute_budgets, see declaration_packets._DECLARED_PLAN_RUNTIME_KEYS),
    # but the budgets are the SAME Link-declared values the forward walk used and
    # were persisted in dynamic_walker_evidence. Without them the forward walk
    # would see no budget and HOLD every reroute target (target_node_has_no_link_
    # assigned_budget). raise's budget_delta is applied separately in the kernel.
    declared_plan = dict(declared_plan)
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
            declared_plan["node_reroute_budgets"] = dict(recorded_budgets)
        elif had_reroute_budgets:
            raise ValueError(
                "resume corrupt evidence: this Building engaged the reroute budget "
                "mechanism but the written dynamic_walker_evidence.node_reroute_budgets "
                "is EMPTY; refusing to resume with no budget map"
            )

    recorded_returns = _recorded_agent_returns(root)
    if not recorded_returns:
        raise ValueError("held Building evidence carries no recorded Agent returns to replay")
    # Per step_ref FIFO of recorded returns + AT-TIME gate records, in REALIZED
    # order, so the forward loop REPLAYS the k-th visit with the k-th recorded
    # return (and reads its recorded gate decision back). Once a step's recorded
    # returns are exhausted the loop runs it LIVE (a continued / post-HOLD step).
    replay_returns: dict[str, list[Any]] = {}
    gate_records: dict[str, list[Any]] = {}
    replay_recorded_at: dict[str, list[str]] = {}
    for item in recorded_returns:
        step_ref = _optional_text_value(item.get("step_ref")) or ""
        replay_returns.setdefault(step_ref, []).append(item.get("returned"))
        gate_records.setdefault(step_ref, []).append(
            item.get("gate_sequence_decision_record")
        )
        replay_recorded_at.setdefault(step_ref, []).append(
            _optional_text_value(item.get("recorded_at")) or ""
        )

    # FAIL-CLOSED gap-1: the recorded COMPLETED-STEP FRONTIER -- per step_ref the
    # number of occurrences that completed BEFORE the HOLD -- derived from the
    # ON-DISK step-output ledger (work/step-outputs/<slug>-attempt-N), which is
    # INDEPENDENT of raw/agent-return.jsonl. The kernel uses this to distinguish an
    # EXPECTED replay (occurrence at/before the frontier; a missing return =>
    # corrupt evidence => raise) from a genuine continued/post-HOLD step (beyond
    # the frontier; runs live). A missing/short agent-return.jsonl line therefore
    # CANNOT masquerade as a continued step and silently re-run a pre-HOLD step
    # live. FAIL CLOSED if the two ledgers disagree the WRONG way (more recorded
    # returns than completed step-outputs = an unaccounted occurrence).
    expected_replay_counts = _completed_step_frontier(root)
    for step_ref, returns in replay_returns.items():
        completed = expected_replay_counts.get(step_ref, 0)
        if len(returns) > completed:
            raise ValueError(
                f"resume corrupt evidence: step {step_ref!r} has {len(returns)} recorded "
                f"Agent return(s) but only {completed} completed step-output(s) on disk; "
                "the recorded-return ledger and the step-output ledger disagree -- "
                "refusing to resume from inconsistent evidence"
            )

    action = _required_disposition_action(disposition)
    pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
    paused_at_ref = (
        _optional_text_value(disposition.get("resumed_from_ref"))
        or _optional_text_value(disposition.get("paused_at_ref"))
        or _hold_paused_at_ref(hold_record)
    )
    author_ref = _optional_text_value(disposition.get("author_ref")) or "human:unknown"

    # raise => bump the held node's budget by the declared budget_increment so the
    # held landing ADOPTS naturally on the bigger budget (verified byte-identical
    # to a fresh forward walk with the bumped budget). forward/stop => no delta.
    budget_delta: dict[str, int] = {}
    if action == "raise":
        increment = _positive_int(
            disposition.get("budget_increment"),
            "transition_lifecycle.budget_increment",
        )
        if pending_target not in step_ref_by_brick_from_declared(declared_plan):
            raise ValueError("raise disposition pending_target_ref is not an existing Brick node")
        # FAIL-CLOSED gap-4 (B2): a `raise` adds a budget increment to the held
        # node. That is only meaningful when the HOLD was a BUDGET-EXHAUSTION hold
        # (the landing was refused because its node budget was used up). On a
        # human/COO gate pause (or any non-budget-exhaustion hold) the base budget
        # was NEVER consumed/recovered, so bumping it MANUFACTURES a budget value
        # that diverges from the Link-declared base. Admit the raise ONLY when the
        # held record is a budget-exhaustion hold; otherwise fail closed (the human
        # should use forward/stop on a gate pause, not raise).
        _require_budget_exhaustion_raise(hold_record, evidence, pending_target)
        budget_delta[pending_target] = increment

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
        hold_record=hold_record,
        existing_resume_observations=tuple(existing_resume_observations),
        expected_replay_counts=dict(expected_replay_counts),
        replay_recorded_at=replay_recorded_at,
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
        resume_seed=seed,
    )


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

    declared = root / "work" / "declared-building-plan.json"
    if not declared.is_file():
        return None
    try:
        packet = json.loads(declared.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(packet, Mapping):
        return None
    declared_plan = packet.get("declared_plan_copy")
    if not isinstance(declared_plan, Mapping):
        return None
    if _optional_text_from_mapping(declared_plan, "plan_shape") != "graph":
        return None
    return declared_plan


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


def _read_disposition_row(
    root: Path,
    hold_record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    pending_target = _optional_text_value(hold_record.get("pending_target_ref")) or ""
    if not pending_target:
        raise ValueError("HOLD record is missing pending_target_ref")
    for record in reversed(_jsonl_records(root / "raw" / "link.jsonl")):
        lifecycle = _flattened_or_nested_transition_lifecycle(record)
        action = _optional_text_value(lifecycle.get("disposition_action"))
        if not action:
            continue
        if _optional_text_value(lifecycle.get("pending_target_ref")) != pending_target:
            continue
        state = _optional_text_value(lifecycle.get("state"))
        if state != "resumed":
            raise ValueError("disposition transition_lifecycle.state must be resumed")
        author_ref = _disposition_author_ref(record)
        if not author_ref.startswith(_HUMAN_AUTHOR_PREFIXES):
            raise ValueError("disposition row author must start with human: or coo:")
        disposition = dict(lifecycle)
        disposition["author_ref"] = author_ref
        return disposition
    return None


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
