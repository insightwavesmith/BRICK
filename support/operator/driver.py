"""Bounded declared multi-Building driver for BUILDING-OPERATOR-DRIVER-0.

This support module composes the existing single-Building
``run_building_plan()`` surface over a caller/COO-declared finite portfolio. It
does not discover, invent, or choose Buildings. Brick owns the candidate plan
refs, Agent may return non-binding transition_concern_evidence, and Link /
declared portfolio policy owns adoption plus the finite transition budget.
"""

from __future__ import annotations

import json

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import validate_transition_concern_evidence
from brick_protocol.link.transition import DISPOSITION_ACTIONS
from brick_protocol.support.connection.agent_adapter import (
    AgentBrainCallable,
    CommandRunner,
)
from brick_protocol.support.operator.building_operation import observe_building_frontier
from brick_protocol.support.operator.composition import (
    declared_portfolio_gate_translations,
    materialize_building_intent,
    stamp_declared_portfolio_closure_gates,
)
from brick_protocol.support.operator.contracts import BuildingPlanSupportResult
from brick_protocol.support.operator.run import (
    ChatSessionParkFrontierEvidenceWritten,
    run_building_plan,
)
from brick_protocol.support.operator.worktree_sandbox import (
    WorktreeSandboxError,
    commit_sandbox_output,
    create_worktree_sandbox,
    dispose_worktree_sandbox,
    probe_worktree_capable,
    temp_dir_fallback,
)
from brick_protocol.support.recording.capture import DEFAULT_BUILDINGS_ROOT, buildings_root_for


PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "driver composes existing run_building_plan once per adopted Building",
    "candidate set is caller/COO declared and finite",
    "support authors no Building Plan, Movement, target, or adoption",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not provider reliability proof",
    "not scheduler / queue / retry behavior",
)
NOT_PROVEN: tuple[str, ...] = (
    "semantic correctness of Agent transition_concern_evidence",
    "caller/COO disposition after a portfolio HOLD",
    "real provider multi-Building autonomy",
    "parallel or concurrent execution",
    "process integrity across provider processes",
)

_DEFAULT_TRANSITION_GATE = "link-gate:default-transition"
_DEFAULT_TRANSITION_ADOPTED_BY = "link-gate:default-transition"
_PORTFOLIO_PROJECTION_KIND = "building_operator_driver0_portfolio_projection"
_PORTFOLIO_PROJECTION_SCHEMA = "portfolio-driver-projection-0"
_MODE_STATIC = "static_order"
_MODE_POLICY = "adoption_policy"
_ALLOWED_MODES = {_MODE_STATIC, _MODE_POLICY, "mode1", "mode2"}
_CANDIDATE_REF_PREFIXES = ("building-boundary:", "brick:", "brick-", "brick-boundary:", "brick-instance:")
_DECLARED_ADOPTER_PREFIXES = ("coo:", "human:", "caller:", "link-policy:", "portfolio-policy:")
_FORBIDDEN_ADOPTER_PREFIXES = ("support:", "agent:")


@dataclass(frozen=True)
class PortfolioDriveResult:
    """Support-only portfolio drive observation; not a BAL fact class."""

    portfolio_ref: str
    frontier_kind: str
    sequence: tuple[Mapping[str, Any], ...]
    projection: Mapping[str, Any]
    projection_path: Path
    child_results: tuple[BuildingPlanSupportResult, ...]
    proof_limits: tuple[str, ...]
    not_proven: tuple[str, ...]


@dataclass(frozen=True)
class BuildingIntakeRunResult:
    """Support-only observation of one confirmed-intent -> running-Building seam.

    Records the seam's mechanical handoff: the materialized plan written to disk,
    the graph-only run dispatch that lets ``run_building_plan`` derive the dynamic
    walker, and the downstream Building run result. It is not a BAL fact class and
    carries no Movement, success, quality, or preset choice.
    """

    building_id: str
    plan_path: Path
    plan_shape: str
    walker_mode: str
    walker_mode_basis: str
    run_result: BuildingPlanSupportResult
    # TASK-BY-TEXT (0611): records WHICH intake task-source form the caller
    # declared -- "task_source_ref" (file/machine flow) or "task_statement"
    # (inline text; the statement rides the declared plan and lands verbatim
    # as work/task.md). Mechanical provenance only; not a judgment.
    task_source_basis: str = "task_source_ref"


@dataclass(frozen=True)
class CustomerSandboxRunResult:
    """Support-only observation of one customer-facing sandboxed dispatch.

    Records the worktree-sandbox lifecycle bracket around ``run_building_intake``
    (W1): the isolation mode actually used, the pinned base + worktree path (when
    a worktree hosted the run), the durable evidence root (OUTSIDE the worktree),
    the observed frontier, and the commit SHA produced ONLY on genuine
    completion. Mechanical provenance only -- it carries no Movement, success,
    quality, or preset choice. ``intake_result`` is None only when the run never
    started (it never does today: any start failure raises).
    """

    building_id: str
    isolation_mode: str  # "worktree" | "temp_dir" (degraded fallback)
    isolation_reason: str
    base_sha: str
    worktree_path: str
    evidence_root: str
    frontier_kind: str
    commit_sha: str  # "" unless frontier_kind == "complete" with a real change
    worktree_disposed: bool
    intake_result: BuildingIntakeRunResult | None = None


@dataclass(frozen=True)
class _Candidate:
    candidate_ref: str
    plan_path: Path
    declared_plan_ref: str


@dataclass(frozen=True)
class _Adoption:
    candidate: _Candidate
    adopted_by: str
    adoption_basis_ref: str
    adoption_mode: str
    reason_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class _NextResolution:
    adoption: _Adoption | None
    complete: bool = False
    hold_reason: str = ""
    pending_candidate_ref: str = ""
    reason_refs: tuple[str, ...] = ()


_DECLARED_PLAN_FILENAME = "declared-building-plan.json"


def run_building_intake(
    intent: Mapping[str, Any],
    *,
    repo_root: Path | str | None = None,
    output_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
) -> BuildingIntakeRunResult:
    """Sequence a confirmed building intent into a running Building (materialize -> run).

    This is the single PART-2 core seam from a confirmed ``task.md`` + selected
    chain preset to a running Building. It is pure support mechanics: it ONLY
    sequences the two already-admitted support helpers in order and records the
    handoff. It does not choose Movement, pick an agent outside the
    NEED<->CAPABILITY match, judge success / sufficiency / quality, or select a
    preset. The preset comes from the confirmed ``intent``; an intent with no
    registry preset hard-fails inside ``materialize_building_intent`` and the
    failure propagates unchanged (support does not work around it).

    TASK-BY-TEXT (0611, Smith ruling; codex FIX-A): humans SPEAK tasks; the
    machine records them as building evidence. The confirmed intent accepts
    EITHER ``task_source_ref`` (existing; file / machine-automation flows) OR
    ``task_statement`` (inline non-empty text; the human flow). The inline
    flow writes NO file anywhere (no repo-root ephemeral, no cleanup):
    ``materialize_building_intent`` records ``task_source_ref =
    "task-source:inline-statement"`` (sentinel token) and carries the
    statement body ON the declared plan (``task_statement``, normalized to a
    single trailing newline, with ``task_source_hash`` over that body); the
    evidence writer (``_write_declaration_work_evidence``) lands the body
    verbatim as the building's ``work/task.md`` straight from the plan, and
    the adapter prompt receives it through the same source-fact carry the
    file flow uses. REPLAY: because the statement travels with the persisted
    plan file, re-running that plan reproduces ``work/task.md`` (no external
    file to lose). Fail-closed (all raised by the materializer): BOTH
    ``task_source_ref`` AND ``task_statement`` declared -> reject (two task
    sources are ambiguous); empty/whitespace statement -> reject; a statement
    over the inline size limit (``INLINE_TASK_STATEMENT_MAX_BYTES``) ->
    reject with a pointer to the file flow; NEITHER -> the existing non-empty
    ``task_source_ref`` reject fires unchanged. FIX-IDEMPOTENCY: with
    ``building_id`` absent on the inline path the default id is a STABLE hash
    of (statement body + chain preset), so the same statement+preset retried
    collides loudly with the existing root instead of duplicating roots.

    PROJECT-0 S3-A (0611): the confirmed intent may carry an OPTIONAL
    ``project_ref`` (``project:<id>``) — the project vessel (그릇) the building
    belongs to. Membership is the PATH (design §1: 소속 = 경로가 1차 사실), so
    the ref's only mechanical effect here is the output root, and that root is
    derived EXCLUSIVELY through ``buildings_root_for`` (THE single derivation
    seam in support/recording/capture.py — no path-join logic lives here):

    * ``project_ref`` declared -> ``materialize_building_intent`` fail-closes
      it FIRST (malformed ref / missing vessel / undeclared-charterless vessel
      all reject loudly BEFORE any plan write or run) and stamps it on the
      plan as a recorded fact; the building then lands under
      ``buildings_root_for(project_ref)`` = ``project/<id>/buildings``.
    * ``project_ref`` absent -> today's behavior: the building lands in the
      project #1 root (``DEFAULT_BUILDINGS_ROOT``, itself derived through the
      SAME seam as ``buildings_root_for('project:brick-protocol')`` — no
      parallel literal). A mechanical compat default only, not a declaration.
    * ``project_ref`` AND an explicit ``output_root`` together -> reject
      (fail-closed: two output-root declarations are ambiguous, mirroring the
      task_source_ref/task_statement EITHER/OR rule).

    Order:

    1. ``materialize_building_intent(intent)`` -> a materialized building-plan dict
       (linear render or graph composition; the helper authors the rows, gates, and
       edges -- this seam does not).
    2. Write the materialized plan to ``output_root/<building_id>/declared-building-plan.json``
       using the same json plan serialization the render / compose / portfolio
       paths use (this is the on-disk plan ``run_building_plan`` reads back).
    3. Require ``plan_shape: graph`` at this driver seam; non-graph plans fail
       closed here instead of being walked by the legacy linear walker.
    4. ``run_building_plan(plan_path, ...)`` -> let the single-Building run
       entrypoint derive dynamic dispatch from the graph shape, walk the declared
       road once, and write Building evidence.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()

    # TASK-BY-TEXT (0611): mechanical provenance only -- WHICH intake form the
    # caller declared. The EITHER/OR, empty/whitespace, and size rejects are
    # raised by materialize_building_intent (single fail-closed owner); the
    # driver writes NO file for the inline flow (codex FIX-A: the statement
    # rides the declared plan itself).
    task_source_basis = (
        "task_statement" if intent.get("task_statement") is not None else "task_source_ref"
    )

    # PROJECT-0 S3-A: refuse the ambiguous double root declaration BEFORE the
    # materializer touches anything (earliest fail-close; same EITHER/OR
    # discipline as the two-task-sources reject above).
    if intent.get("project_ref") is not None and output_root is not None:
        raise ValueError(
            "declare EITHER intent.project_ref (the buildings root derives "
            "through buildings_root_for) OR an explicit output_root, not both "
            "(fail-closed: two output-root declarations are ambiguous)"
        )

    plan = materialize_building_intent(intent, repo_root=repo)
    if "report_event_policy" in intent:
        policy = intent.get("report_event_policy")
        plan["report_event_policy"] = dict(policy) if isinstance(policy, Mapping) else policy

    plan_shape = str(plan.get("plan_shape") or "")
    if plan_shape != "graph":
        raise ValueError("driver run_building_intake admits only plan_shape: graph")
    walker_mode = "dynamic"
    walker_mode_basis = (
        "driver requires graph plan and lets run_building_plan derive dynamic dispatch; "
        "not a Link Movement decision"
    )

    building_id = _required_text(plan.get("building_id"), "materialized plan building_id")
    # PROJECT-0 S3-A: derive the output root. The stamped plan fact (validated
    # by the materializer above) drives the vessel flow; the ref-less default
    # is DEFAULT_BUILDINGS_ROOT, which is itself buildings_root_for(
    # 'project:brick-protocol') — every branch routes through the ONE seam.
    plan_project_ref = plan.get("project_ref")
    if plan_project_ref is not None:
        output = buildings_root_for(str(plan_project_ref))
    elif output_root is not None:
        output = Path(output_root).resolve()
    else:
        output = DEFAULT_BUILDINGS_ROOT
    plan_path = output / _slug(building_id) / _DECLARED_PLAN_FILENAME
    if plan_path.exists() and not overwrite_existing:
        raise ValueError(f"declared Building plan already exists: {plan_path}")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    run_result = run_building_plan(
        plan_path,
        output_root=output,
        overwrite_existing=overwrite_existing,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
        proof_limits=proof_limits,
    )

    return BuildingIntakeRunResult(
        building_id=building_id,
        plan_path=plan_path,
        plan_shape=plan_shape,
        walker_mode=walker_mode,
        walker_mode_basis=walker_mode_basis,
        run_result=run_result,
        task_source_basis=task_source_basis,
    )


def run_customer_building_in_sandbox(
    intent: Mapping[str, Any],
    *,
    customer_repo_root: Path | str,
    output_root: Path | str,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
) -> CustomerSandboxRunResult:
    """Run a CUSTOMER-FACING building dispatch in an isolated git-worktree sandbox.

    W1 (operator-pinned, foundational safety). This is a THIN wrapper around the
    existing ``run_building_intake`` seam -- it does NOT touch the dispatch
    internals, the adapter_cwd default, or any axis. It exists so a customer's
    LIVE / working tree is NEVER written: the dispatch runs entirely inside an
    engine-created, disposable git worktree at a PINNED base SHA, and the
    building's CODE output becomes a COMMIT produced ONLY on genuine completion.
    Internal / checker dispatch keeps using ``run_building_intake`` directly with
    the bare ``adapter_cwd`` default, byte-identical to today.

    The 6 locked decisions + 4 mitigations live here as a create -> run ->
    capture/commit -> dispose bracket:

    1. BASE = the explicitly resolved HEAD SHA (probe records it; never a bare
       ``--detach`` race).
    2. WHERE = ~/.brick/worktrees/<building-id>/ (outside the repo).
    3. COMMIT on GENUINE completion only: after the run bracket we observe the
       durable evidence frontier and commit the worktree's changes ONLY if
       frontier_kind == "complete". Else NO commit (honesty).
    4. NON-GIT / DIRTY / no-git -> the probe fails closed and we fall back to a
       disposable temp dir as adapter_cwd; we NEVER write the live tree.
       CLEANUP: only the engine-created worktree is force-removed (engine-gated).
    5. Per-building granularity: one worktree per building id.
    6. REAL isolation: adapter_cwd AND repo_root point at the worktree for the
       dispatch, but output_root (evidence) stays durable OUTSIDE it.

    ``output_root`` is REQUIRED and must live OUTSIDE the worktree so evidence
    survives disposal (the caller owns where -- e.g. a project buildings root).
    """

    repo = Path(customer_repo_root).resolve()
    durable_output = Path(output_root).resolve()
    building_id = _required_text(intent.get("building_id"), "intent building_id")

    # MITIGATION 4 (probe FIRST): is this a clean git work tree with git
    # installed? ANY failure -> degrade to a temp dir; the live tree is never
    # written and no worktree is created.
    probe = probe_worktree_capable(repo)
    if not probe.ok:
        temp_dir = temp_dir_fallback()
        try:
            sandbox_cwd = Path(temp_dir.name).resolve()
            # DEGRADED MODE: the two cwd roles split. repo_root stays the customer
            # dir (READ-ONLY catalog/plan source -- never written: the only writer
            # is the adapter, and its cwd is the temp dir). adapter_cwd is the
            # disposable temp dir, so even a real provider's writes stay there and
            # the live tree is NEVER mutated. (A customer dir lacking the Brick
            # catalog fails materialization exactly as a bare dispatch does today;
            # the safety contract is only that we never WRITE the live tree.)
            intake = run_building_intake(
                intent,
                repo_root=repo,
                output_root=durable_output,
                overwrite_existing=overwrite_existing,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=sandbox_cwd,
                adapter_timeout_seconds=adapter_timeout_seconds,
                proof_limits=proof_limits,
            )
            frontier = observe_building_frontier(
                intake.run_result.lifecycle_write.root, repo_root=repo
            )
            return CustomerSandboxRunResult(
                building_id=intake.building_id,
                isolation_mode="temp_dir",
                isolation_reason=probe.reason,
                base_sha="",
                worktree_path="",
                evidence_root=str(intake.run_result.lifecycle_write.root),
                frontier_kind=str(frontier.get("frontier_kind") or ""),
                commit_sha="",  # a temp dir is not a repo: no commit, by design
                worktree_disposed=False,
                intake_result=intake,
            )
        finally:
            temp_dir.cleanup()

    # MITIGATION 1: create the engine worktree detached at the resolved BASE SHA.
    sandbox = create_worktree_sandbox(
        repo,
        building_id=building_id,
        base_sha=probe.base_sha,
    )
    commit_sha = ""
    frontier_kind = ""
    evidence_root = ""
    intake_result: BuildingIntakeRunResult | None = None
    try:
        # MITIGATION 6 (real isolation): the dispatch runs with BOTH adapter_cwd
        # AND repo_root pointing at the worktree, but evidence lands under the
        # durable output_root OUTSIDE the worktree.
        intake_result = run_building_intake(
            intent,
            repo_root=sandbox.path,
            output_root=durable_output,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=sandbox.path,
            adapter_timeout_seconds=adapter_timeout_seconds,
            proof_limits=proof_limits,
        )
        evidence_root = str(intake_result.run_result.lifecycle_write.root)
        # MITIGATION 3 (commit ONLY on genuine completion, AFTER the run bracket
        # so the write-observation HEAD guard is honored): observe the DURABLE
        # evidence frontier, then commit the worktree's changes only if complete.
        frontier = observe_building_frontier(
            intake_result.run_result.lifecycle_write.root,
            repo_root=sandbox.path,
        )
        frontier_kind = str(frontier.get("frontier_kind") or "")
        if frontier_kind == "complete":
            commit_sha = commit_sandbox_output(
                sandbox,
                message=(
                    f"BRICK building output: {building_id}\n\n"
                    f"frontier=complete base={sandbox.base_sha}\n"
                    f"evidence_root={evidence_root}\n"
                ),
            )
    finally:
        disposed = dispose_worktree_sandbox(sandbox)

    return CustomerSandboxRunResult(
        building_id=building_id,
        isolation_mode="worktree",
        isolation_reason=probe.reason,
        base_sha=sandbox.base_sha,
        worktree_path=str(sandbox.path),
        evidence_root=evidence_root,
        frontier_kind=frontier_kind,
        commit_sha=commit_sha,
        worktree_disposed=disposed,
        intake_result=intake_result,
    )


def run_declared_portfolio(
    portfolio: Mapping[str, Any] | str | Path,
    *,
    repo_root: Path | str | None = None,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    portfolio_output_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
) -> PortfolioDriveResult:
    """Drive a declared finite portfolio Building-by-Building.

    Portfolio packet shape:

    - ``portfolio_ref``: support projection id.
    - ``declared_by``: caller/COO declaration ref, used for the initial entry.
    - ``candidate_buildings``: finite list of existing Building Plan refs, each
      with ``candidate_ref`` and ``building_plan_ref`` or ``plan_ref``.
    - ``portfolio_transition_budget.max_transitions``: positive Link-owned
      portfolio transition budget.
    - MODE 1: ``mode: static_order`` and ``static_order`` candidate refs.
    - MODE 2: ``mode: adoption_policy``, ``start_candidate_ref``, and optional
      ``portfolio_adoption_policy.adoptions`` rows. A multi-candidate proposal is
      adopted only by a non-support declared Link / COO / portfolio policy row.
    - optional ``chain_preset_ref``: the DECLARING portfolio chain preset.
      GATE WIRING (0611): its ``gate_concept_profile`` review tokens translate
      through the SAME single-source composition translation
      (``declared_portfolio_gate_translations``) onto the TERMINAL candidate's
      closing Link row (real ``declared_gate_refs`` + ``gate_concept_provenance``)
      BEFORE that plan reaches the engine -- the existing engine gate machinery
      evaluates them unchanged. Review tokens require a declared terminal
      candidate, i.e. ``static_order`` mode (loud reject otherwise). Absent
      ``chain_preset_ref`` -> behavior unchanged.
    - optional ``route_decision_basis``: caller/COO-declared disposition facts
      (``override_refs`` / ``human_review_refs``) for the stamped portfolio
      closure gates; mechanically copied onto the stamped row only (support
      never invents a basis).
    """

    repo = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    packet, base_dir = _portfolio_mapping(portfolio, repo=repo)
    portfolio_ref = _required_text(packet.get("portfolio_ref", "portfolio:anonymous"), "portfolio_ref")
    mode = _portfolio_mode(packet)
    candidates_in_order, candidates_by_ref = _candidate_buildings(packet, base_dir=base_dir)
    max_transitions = _portfolio_budget(packet)
    checked_proof_limits = _merge_texts(
        PROOF_LIMITS,
        _text_tuple("proof_limits", proof_limits if proof_limits is not None else packet.get("proof_limits")),
    )
    checked_not_proven = _merge_texts(NOT_PROVEN, _text_tuple("not_proven", packet.get("not_proven")))

    output = Path(output_root).resolve()
    projection_root = (
        Path(portfolio_output_root).resolve()
        if portfolio_output_root is not None
        else output / "_portfolio-projections"
    )
    declared_by = _required_text(packet.get("declared_by", "caller:declared-portfolio"), "declared_by")

    # GATE WIRING (0611): translate the DECLARING portfolio preset's gate labels
    # up front (declaration side, fail-closed) -- see the docstring above.
    declaring_preset_ref = _optional_text(packet.get("chain_preset_ref"))
    raw_packet_basis = packet.get("route_decision_basis")
    if raw_packet_basis not in (None, False, "") and not isinstance(raw_packet_basis, Mapping):
        raise TypeError("route_decision_basis must be a mapping")
    packet_route_decision_basis = (
        raw_packet_basis if isinstance(raw_packet_basis, Mapping) else None
    )
    portfolio_gate_summary: Mapping[str, Any] | None = None
    terminal_candidate_ref = ""
    if declaring_preset_ref:
        portfolio_gate_summary = declared_portfolio_gate_translations(
            declaring_preset_ref,
            repo_root=repo,
        )
        if portfolio_gate_summary["translations"]:
            if mode != _MODE_STATIC:
                raise ValueError(
                    "portfolio preset review gates (coo-review / human-review) "
                    "need a declared terminal candidate: declare mode "
                    "static_order or drop the declaring chain_preset_ref"
                )
            terminal_candidate_ref = _static_order(packet, candidates_by_ref)[-1]

    current = _initial_adoption(
        packet,
        mode=mode,
        candidates_in_order=candidates_in_order,
        candidates_by_ref=candidates_by_ref,
        declared_by=declared_by,
    )
    consumed_transitions = 0
    driven_candidate_refs: list[str] = []
    sequence: list[Mapping[str, Any]] = []
    child_results: list[BuildingPlanSupportResult] = []
    frontier: Mapping[str, Any] | None = None
    previous_candidate_ref = "building-boundary:portfolio-start"

    while current is not None:
        if consumed_transitions >= max_transitions:
            frontier = _hold_frontier(
                portfolio_ref=portfolio_ref,
                reason="portfolio_transition_budget_exhausted",
                from_candidate_ref=previous_candidate_ref,
                pending_candidate_ref=current.candidate.candidate_ref,
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
                reason_refs=("observation:portfolio-transition-budget-exhausted",),
            )
            break
        if current.candidate.candidate_ref in driven_candidate_refs:
            frontier = _hold_frontier(
                portfolio_ref=portfolio_ref,
                reason="candidate_already_driven",
                from_candidate_ref=previous_candidate_ref,
                pending_candidate_ref=current.candidate.candidate_ref,
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
                reason_refs=("observation:portfolio-candidate-repeat-rejected",),
            )
            break

        plan_input: Mapping[str, Any] | Path = current.candidate.plan_path
        if terminal_candidate_ref and current.candidate.candidate_ref == terminal_candidate_ref:
            # The TERMINAL child's closure IS the portfolio closure boundary:
            # stamp the preset-declared translated gates there (single-source
            # composition stamp, provenance recorded) BEFORE the plan reaches
            # the engine. The engine evaluates them unchanged.
            stamped_plan, portfolio_gate_summary = stamp_declared_portfolio_closure_gates(
                _load_declared_plan_mapping(current.candidate.plan_path),
                chain_preset_ref=declaring_preset_ref,
                repo_root=repo,
                route_decision_basis=packet_route_decision_basis,
            )
            plan_input = stamped_plan
        try:
            child_result = run_building_plan(
                plan_input,
                output_root=output,
                overwrite_existing=overwrite_existing,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=adapter_cwd,
                adapter_timeout_seconds=adapter_timeout_seconds,
                proof_limits=checked_proof_limits,
            )
        except ChatSessionParkFrontierEvidenceWritten as parked:
            child_frontier = observe_building_frontier(parked.building_root, repo_root=repo)
            consumed_transitions += 1
            driven_candidate_refs.append(current.candidate.candidate_ref)
            sequence.append(
                _parked_child_sequence_record(
                    sequence_number=consumed_transitions,
                    adoption=current,
                    parked=parked,
                    child_frontier=child_frontier,
                    from_candidate_ref=previous_candidate_ref,
                )
            )
            frontier = _hold_frontier(
                portfolio_ref=portfolio_ref,
                reason="child_building_not_closed",
                from_candidate_ref=current.candidate.candidate_ref,
                pending_candidate_ref=current.candidate.candidate_ref,
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
                reason_refs=(f"observation:child-frontier-{child_frontier.get('frontier_kind', 'unknown')}",),
            )
            break
        child_frontier = observe_building_frontier(child_result.lifecycle_write.root, repo_root=repo)
        consumed_transitions += 1
        driven_candidate_refs.append(current.candidate.candidate_ref)
        child_results.append(child_result)
        sequence.append(
            _sequence_record(
                sequence_number=consumed_transitions,
                adoption=current,
                child_result=child_result,
                child_frontier=child_frontier,
                from_candidate_ref=previous_candidate_ref,
            )
        )

        if child_frontier.get("frontier_kind") != "complete":
            frontier = _hold_frontier(
                portfolio_ref=portfolio_ref,
                reason="child_building_not_closed",
                from_candidate_ref=current.candidate.candidate_ref,
                pending_candidate_ref=current.candidate.candidate_ref,
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
                reason_refs=(f"observation:child-frontier-{child_frontier.get('frontier_kind', 'unknown')}",),
            )
            break

        resolution = _resolve_next_adoption(
            packet,
            mode=mode,
            current_candidate_ref=current.candidate.candidate_ref,
            candidates_in_order=candidates_in_order,
            candidates_by_ref=candidates_by_ref,
            driven_candidate_refs=tuple(driven_candidate_refs),
            child_result=child_result,
        )
        previous_candidate_ref = current.candidate.candidate_ref
        if resolution.complete:
            frontier = _complete_frontier(
                portfolio_ref=portfolio_ref,
                from_candidate_ref=current.candidate.candidate_ref,
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
            )
            current = None
        elif resolution.adoption is not None:
            current = resolution.adoption
        else:
            frontier = _hold_frontier(
                portfolio_ref=portfolio_ref,
                reason=resolution.hold_reason or "no_adopted_next_building",
                from_candidate_ref=current.candidate.candidate_ref,
                pending_candidate_ref=resolution.pending_candidate_ref
                or "building-boundary:portfolio-disposition",
                consumed_transitions=consumed_transitions,
                max_transitions=max_transitions,
                reason_refs=resolution.reason_refs
                or ("observation:portfolio-no-adopted-next-building",),
            )
            current = None

    if frontier is None:
        frontier = _complete_frontier(
            portfolio_ref=portfolio_ref,
            from_candidate_ref=previous_candidate_ref,
            consumed_transitions=consumed_transitions,
            max_transitions=max_transitions,
        )

    projection = _portfolio_projection(
        portfolio_ref=portfolio_ref,
        mode=mode,
        declared_candidate_refs=tuple(candidate.candidate_ref for candidate in candidates_in_order),
        max_transitions=max_transitions,
        consumed_transitions=consumed_transitions,
        sequence=tuple(sequence),
        frontier=frontier,
        proof_limits=checked_proof_limits,
        not_proven=checked_not_proven,
        portfolio_gate_concept_translation=portfolio_gate_summary,
    )
    projection_path = _write_projection(
        projection_root,
        portfolio_ref=portfolio_ref,
        projection=projection,
        overwrite_existing=overwrite_existing,
    )
    return PortfolioDriveResult(
        portfolio_ref=portfolio_ref,
        frontier_kind=str(frontier.get("frontier_kind") or ""),
        sequence=tuple(sequence),
        projection=projection,
        projection_path=projection_path,
        child_results=tuple(child_results),
        proof_limits=checked_proof_limits,
        not_proven=checked_not_proven,
    )


def _portfolio_mapping(
    portfolio: Mapping[str, Any] | str | Path,
    *,
    repo: Path,
) -> tuple[Mapping[str, Any], Path]:
    if isinstance(portfolio, Mapping):
        return portfolio, repo
    path = Path(portfolio)
    if not path.is_absolute():
        path = (repo / path).resolve()
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("YAML portfolio files require PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, Mapping):
        raise TypeError("portfolio must be a JSON-compatible mapping")
    return value, path.parent


def _portfolio_mode(packet: Mapping[str, Any]) -> str:
    raw_mode = _required_text(packet.get("mode", _MODE_STATIC), "mode")
    if raw_mode not in _ALLOWED_MODES:
        raise ValueError("mode must be static_order/mode1 or adoption_policy/mode2")
    if raw_mode == "mode1":
        return _MODE_STATIC
    if raw_mode == "mode2":
        return _MODE_POLICY
    return raw_mode


def _candidate_buildings(
    packet: Mapping[str, Any],
    *,
    base_dir: Path,
) -> tuple[tuple[_Candidate, ...], dict[str, _Candidate]]:
    value = packet.get("candidate_buildings")
    if not isinstance(value, list) or not value:
        raise ValueError("candidate_buildings must be a non-empty finite list")
    candidates: list[_Candidate] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        item = _mapping(raw, f"candidate_buildings[{index}]")
        candidate_ref = _required_text(item.get("candidate_ref"), f"candidate_buildings[{index}].candidate_ref")
        if not candidate_ref.startswith(_CANDIDATE_REF_PREFIXES):
            raise ValueError("candidate_ref must name a Brick / building boundary")
        if candidate_ref in seen:
            raise ValueError(f"candidate_buildings contains duplicate candidate_ref: {candidate_ref}")
        seen.add(candidate_ref)
        raw_plan_ref = item.get("building_plan_ref", item.get("plan_ref"))
        declared_plan_ref = _required_text(raw_plan_ref, f"candidate_buildings[{index}].building_plan_ref")
        plan_path = _resolve_declared_plan_path(declared_plan_ref, base_dir=base_dir)
        plan_shape = str(_load_declared_plan_mapping(plan_path).get("plan_shape") or "")
        if plan_shape != "graph":
            raise ValueError("candidate_buildings[] Building Plan must declare plan_shape: graph")
        candidates.append(
            _Candidate(
                candidate_ref=candidate_ref,
                plan_path=plan_path,
                declared_plan_ref=declared_plan_ref,
            )
        )
    return tuple(candidates), {candidate.candidate_ref: candidate for candidate in candidates}


def _resolve_declared_plan_path(value: str, *, base_dir: Path) -> Path:
    raw = Path(value)
    path = raw if raw.is_absolute() else base_dir / raw
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"declared Building Plan ref does not resolve to an existing file: {value}")
    if path.suffix not in {".json", ".yaml", ".yml"}:
        raise ValueError("declared Building Plan ref must be a JSON/YAML file")
    return path


def _load_declared_plan_mapping(path: Path) -> Mapping[str, Any]:
    """Load one declared child Building Plan file as a mapping (read only)."""

    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("YAML Building Plan files require PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, Mapping):
        raise TypeError(f"declared Building Plan must be a JSON-compatible mapping: {path}")
    return value


def _portfolio_budget(packet: Mapping[str, Any]) -> int:
    budget = _mapping(packet.get("portfolio_transition_budget"), "portfolio_transition_budget")
    owner = _required_text(budget.get("owner_axis", "Link"), "portfolio_transition_budget.owner_axis")
    if owner != "Link":
        raise ValueError("portfolio_transition_budget.owner_axis must be Link")
    return _positive_int(budget.get("max_transitions"), "portfolio_transition_budget.max_transitions")


def _initial_adoption(
    packet: Mapping[str, Any],
    *,
    mode: str,
    candidates_in_order: tuple[_Candidate, ...],
    candidates_by_ref: Mapping[str, _Candidate],
    declared_by: str,
) -> _Adoption:
    if mode == _MODE_STATIC:
        order = _static_order(packet, candidates_by_ref)
        candidate = candidates_by_ref[order[0]]
    else:
        start_ref = _required_text(packet.get("start_candidate_ref"), "start_candidate_ref")
        candidate = _candidate_for_ref(start_ref, candidates_by_ref)
    if declared_by.startswith(_FORBIDDEN_ADOPTER_PREFIXES):
        raise ValueError("declared_by must not be support: or agent:")
    if not candidates_in_order:
        raise ValueError("candidate_buildings must be non-empty")
    return _Adoption(
        candidate=candidate,
        adopted_by=declared_by,
        adoption_basis_ref="portfolio:declared-start",
        adoption_mode="declared_start",
        reason_refs=("portfolio:declared-candidate-set",),
    )


def _resolve_next_adoption(
    packet: Mapping[str, Any],
    *,
    mode: str,
    current_candidate_ref: str,
    candidates_in_order: tuple[_Candidate, ...],
    candidates_by_ref: Mapping[str, _Candidate],
    driven_candidate_refs: tuple[str, ...],
    child_result: BuildingPlanSupportResult,
) -> _NextResolution:
    if mode == _MODE_STATIC:
        order = _static_order(packet, candidates_by_ref)
        current_index = order.index(current_candidate_ref)
        if current_index + 1 >= len(order):
            return _NextResolution(adoption=None, complete=True)
        next_ref = order[current_index + 1]
        return _NextResolution(
            adoption=_Adoption(
                candidate=candidates_by_ref[next_ref],
                adopted_by=_DEFAULT_TRANSITION_ADOPTED_BY,
                adoption_basis_ref=_DEFAULT_TRANSITION_GATE,
                adoption_mode="default_transition_static_order",
                reason_refs=("portfolio:static-order",),
            )
        )

    eligible = [
        candidate for candidate in candidates_in_order if candidate.candidate_ref not in driven_candidate_refs
    ]
    if not eligible:
        return _NextResolution(adoption=None, complete=True)
    if len(eligible) == 1:
        return _NextResolution(
            adoption=_Adoption(
                candidate=eligible[0],
                adopted_by=_DEFAULT_TRANSITION_ADOPTED_BY,
                adoption_basis_ref=_DEFAULT_TRANSITION_GATE,
                adoption_mode="default_transition_single_eligible",
                reason_refs=("portfolio:single-eligible-candidate",),
            )
        )

    concern = _latest_transition_concern(child_result)
    if concern is None:
        return _NextResolution(
            adoption=None,
            hold_reason="multi_candidate_no_agent_transition_concern",
            pending_candidate_ref="building-boundary:portfolio-disposition",
            reason_refs=("observation:no-transition-concern-for-multi-candidate-selection",),
        )
    eligible_refs = {candidate.candidate_ref for candidate in eligible}
    declared_refs = set(candidates_by_ref)
    proposed_declared_refs = [
        ref for ref in _related_boundary_refs(concern) if ref in declared_refs and ref in eligible_refs
    ]
    if not proposed_declared_refs:
        unknown_refs = [ref for ref in _related_boundary_refs(concern) if ref not in declared_refs]
        return _NextResolution(
            adoption=None,
            hold_reason="proposed_candidate_not_in_declared_set" if unknown_refs else "no_declared_candidate_proposed",
            pending_candidate_ref="building-boundary:portfolio-disposition",
            reason_refs=tuple(unknown_refs) or ("observation:no-declared-candidate-proposed",),
        )

    policy_adoption = _declared_policy_adoption(
        packet.get("portfolio_adoption_policy"),
        current_candidate_ref=current_candidate_ref,
        proposed_candidate_refs=tuple(proposed_declared_refs),
        candidates_by_ref=candidates_by_ref,
        eligible_refs=eligible_refs,
        concern=concern,
    )
    if policy_adoption is not None:
        return _NextResolution(adoption=policy_adoption)
    return _NextResolution(
        adoption=None,
        hold_reason="multi_candidate_requires_declared_policy",
        pending_candidate_ref=proposed_declared_refs[0],
        reason_refs=(
            str(concern.get("concern_ref") or "transition-concern:unknown"),
            "observation:bare-default-transition-rejected-for-multi-candidate-selection",
        ),
    )


def _static_order(packet: Mapping[str, Any], candidates_by_ref: Mapping[str, _Candidate]) -> tuple[str, ...]:
    order = _text_tuple("static_order", packet.get("static_order"))
    if not order:
        raise ValueError("static_order mode requires a non-empty static_order list")
    seen: set[str] = set()
    for ref in order:
        _candidate_for_ref(ref, candidates_by_ref)
        if ref in seen:
            raise ValueError("static_order must not repeat candidate refs")
        seen.add(ref)
    return order


def _candidate_for_ref(ref: str, candidates_by_ref: Mapping[str, _Candidate]) -> _Candidate:
    candidate = candidates_by_ref.get(ref)
    if candidate is None:
        raise ValueError(f"candidate ref is not in the declared candidate set: {ref}")
    return candidate


def _latest_transition_concern(result: BuildingPlanSupportResult) -> Mapping[str, Any] | None:
    for step_result in reversed(result.step_results):
        returned = step_result.adapter_result.returned_value
        if not isinstance(returned, Mapping):
            continue
        concern = returned.get("transition_concern_evidence")
        if concern in (None, False, ""):
            continue
        if not isinstance(concern, Mapping):
            raise ValueError("transition_concern_evidence must be a mapping when present")
        return validate_transition_concern_evidence(concern)
    return None


def _declared_policy_adoption(
    policy_value: Any,
    *,
    current_candidate_ref: str,
    proposed_candidate_refs: tuple[str, ...],
    candidates_by_ref: Mapping[str, _Candidate],
    eligible_refs: set[str],
    concern: Mapping[str, Any],
) -> _Adoption | None:
    if policy_value in (None, False, ""):
        return None
    policy = _mapping(policy_value, "portfolio_adoption_policy")
    policy_ref = _required_text(policy.get("policy_ref", "portfolio-policy:anonymous"), "portfolio_adoption_policy.policy_ref")
    rows = policy.get("adoptions", [])
    if not isinstance(rows, list):
        raise ValueError("portfolio_adoption_policy.adoptions must be a list")
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"portfolio_adoption_policy.adoptions[{index}]")
        from_ref = _optional_text(row.get("from_candidate_ref"))
        if from_ref and from_ref != current_candidate_ref:
            continue
        candidate_ref = _required_text(row.get("candidate_ref"), "portfolio_adoption_policy.adoptions[].candidate_ref")
        if candidate_ref not in proposed_candidate_refs or candidate_ref not in eligible_refs:
            continue
        adopted_by = _required_text(
            row.get("adopted_by", policy.get("adopter_ref", policy_ref)),
            "portfolio_adoption_policy.adoptions[].adopted_by",
        )
        basis_ref = _adoption_basis_ref(row, policy, policy_ref)
        if not _declared_adoption_is_authorized(adopted_by=adopted_by, basis_ref=basis_ref, policy_ref=policy_ref):
            continue
        reason_refs = _merge_texts(
            (str(concern.get("concern_ref") or "transition-concern:unknown"),),
            _text_tuple("portfolio_adoption_policy.adoptions[].reason_refs", row.get("reason_refs")),
        )
        return _Adoption(
            candidate=candidates_by_ref[candidate_ref],
            adopted_by=adopted_by,
            adoption_basis_ref=basis_ref,
            adoption_mode="declared_policy_adoption",
            reason_refs=reason_refs,
        )
    return None


def _adoption_basis_ref(row: Mapping[str, Any], policy: Mapping[str, Any], policy_ref: str) -> str:
    explicit = _optional_text(row.get("adoption_basis_ref"))
    if explicit:
        return explicit
    gate_ref = _optional_text(row.get("gate_ref"))
    if gate_ref:
        return gate_ref
    gate_refs = _text_tuple("portfolio_adoption_policy.declared_gate_refs", policy.get("declared_gate_refs"))
    if gate_refs:
        return gate_refs[0]
    return policy_ref


def _declared_adoption_is_authorized(*, adopted_by: str, basis_ref: str, policy_ref: str) -> bool:
    if adopted_by.startswith(_FORBIDDEN_ADOPTER_PREFIXES) or policy_ref.startswith("support:"):
        return False
    if adopted_by in {_DEFAULT_TRANSITION_ADOPTED_BY, "template:default-transition"}:
        return False
    if basis_ref == _DEFAULT_TRANSITION_GATE and not adopted_by.startswith(_DECLARED_ADOPTER_PREFIXES):
        return False
    if adopted_by.startswith(_DECLARED_ADOPTER_PREFIXES):
        return True
    if basis_ref.startswith("link-gate:") and basis_ref != _DEFAULT_TRANSITION_GATE:
        return True
    if policy_ref.startswith(("portfolio-policy:", "link-policy:")):
        return True
    return False


def _related_boundary_refs(concern: Mapping[str, Any]) -> tuple[str, ...]:
    return _text_tuple("transition_concern_evidence.related_boundary_refs", concern.get("related_boundary_refs"))


def _sequence_record(
    *,
    sequence_number: int,
    adoption: _Adoption,
    child_result: BuildingPlanSupportResult,
    child_frontier: Mapping[str, Any],
    from_candidate_ref: str,
) -> Mapping[str, Any]:
    return {
        "sequence_number": sequence_number,
        "candidate_ref": adoption.candidate.candidate_ref,
        "declared_plan_ref": adoption.candidate.declared_plan_ref,
        "child_plan_ref": child_result.plan_ref,
        "building_id": child_result.building_id,
        "child_evidence_root": str(child_result.lifecycle_write.root),
        "from_candidate_ref": from_candidate_ref,
        "adopted_by": adoption.adopted_by,
        "adoption_basis_ref": adoption.adoption_basis_ref,
        "adoption_mode": adoption.adoption_mode,
        "reason_refs": list(adoption.reason_refs),
        "child_frontier_kind": child_frontier.get("frontier_kind"),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _parked_child_sequence_record(
    *,
    sequence_number: int,
    adoption: _Adoption,
    parked: ChatSessionParkFrontierEvidenceWritten,
    child_frontier: Mapping[str, Any],
    from_candidate_ref: str,
) -> Mapping[str, Any]:
    return {
        "sequence_number": sequence_number,
        "candidate_ref": adoption.candidate.candidate_ref,
        "declared_plan_ref": adoption.candidate.declared_plan_ref,
        "child_plan_ref": adoption.candidate.declared_plan_ref,
        "building_id": parked.building_id,
        "child_evidence_root": str(parked.building_root),
        "from_candidate_ref": from_candidate_ref,
        "adopted_by": adoption.adopted_by,
        "adoption_basis_ref": adoption.adoption_basis_ref,
        "adoption_mode": adoption.adoption_mode,
        "reason_refs": list(adoption.reason_refs),
        "child_frontier_kind": child_frontier.get("frontier_kind"),
        "child_closed": False,
        "park_signal": "ChatSessionParkFrontierEvidenceWritten",
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _complete_frontier(
    *,
    portfolio_ref: str,
    from_candidate_ref: str,
    consumed_transitions: int,
    max_transitions: int,
) -> Mapping[str, Any]:
    return {
        "frontier_kind": "complete",
        "frontier_reason": "declared portfolio candidate sequence is exhausted",
        "portfolio_ref": portfolio_ref,
        "from_candidate_ref": from_candidate_ref,
        "portfolio_transition_budget": {
            "owner_axis": "Link",
            "max_transitions": max_transitions,
            "consumed_transitions": consumed_transitions,
            "remaining_transitions": max_transitions - consumed_transitions,
        },
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _hold_frontier(
    *,
    portfolio_ref: str,
    reason: str,
    from_candidate_ref: str,
    pending_candidate_ref: str,
    consumed_transitions: int,
    max_transitions: int,
    reason_refs: tuple[str, ...],
) -> Mapping[str, Any]:
    paused_at_ref = "link-transition:" + _slug(f"{portfolio_ref}-{reason}-{consumed_transitions + 1}")
    return {
        "frontier_kind": "link_paused",
        "frontier_reason": reason,
        "portfolio_ref": portfolio_ref,
        "latest_transition_lifecycle": {
            "transition_lifecycle_state": "paused",
            "transition_lifecycle_progress_state": "in_progress",
            "transition_lifecycle_paused_at_ref": paused_at_ref,
            "transition_lifecycle_from_brick_ref": from_candidate_ref,
            "transition_lifecycle_pending_target_ref": pending_candidate_ref,
            "transition_lifecycle_required_disposition_owner": "caller-or-coo",
            "transition_lifecycle_reason_refs": list(reason_refs),
        },
        "disposition_action_surface": {
            "allowed_values": list(DISPOSITION_ACTIONS),
            "authored_by_support": False,
        },
        "portfolio_transition_budget": {
            "owner_axis": "Link",
            "max_transitions": max_transitions,
            "consumed_transitions": consumed_transitions,
            "remaining_transitions": max_transitions - consumed_transitions,
        },
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _portfolio_projection(
    *,
    portfolio_ref: str,
    mode: str,
    declared_candidate_refs: tuple[str, ...],
    max_transitions: int,
    consumed_transitions: int,
    sequence: tuple[Mapping[str, Any], ...],
    frontier: Mapping[str, Any],
    proof_limits: tuple[str, ...],
    not_proven: tuple[str, ...],
    portfolio_gate_concept_translation: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    projection: dict[str, Any] = {
        "kind": _PORTFOLIO_PROJECTION_KIND,
        "schema_version": _PORTFOLIO_PROJECTION_SCHEMA,
        "portfolio_ref": portfolio_ref,
        "mode": mode,
        "recorded_at": _recorded_at(),
        "declared_candidate_refs": list(declared_candidate_refs),
        "portfolio_transition_budget": {
            "owner_axis": "Link",
            "max_transitions": max_transitions,
            "consumed_transitions": consumed_transitions,
            "remaining_transitions": max_transitions - consumed_transitions,
        },
        "sequence": [dict(item) for item in sequence],
        "frontier": dict(frontier),
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    if portfolio_gate_concept_translation is not None:
        # Machine-readable record of the declared-label translation (mirrors
        # the per-row gate_concept_provenance stamp; absent declaring preset ->
        # absent key, schema-additive).
        projection["portfolio_gate_concept_translation"] = _json_compatible(
            portfolio_gate_concept_translation
        )
    return projection


def _json_compatible(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


def _write_projection(
    root: Path,
    *,
    portfolio_ref: str,
    projection: Mapping[str, Any],
    overwrite_existing: bool,
) -> Path:
    path = root / _slug(portfolio_ref) / "portfolio-projection.json"
    if path.exists() and not overwrite_existing:
        raise ValueError(f"portfolio projection already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


def _optional_text(value: Any) -> str:
    if value in (None, False, ""):
        return ""
    return _required_text(value, "optional text")


def _text_tuple(label: str, value: Any) -> tuple[str, ...]:
    if value in (None, False, ""):
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, Iterable):
        raise TypeError(f"{label} must be text or a list of text")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_required_text(item, f"{label}[{index}]"))
    return tuple(result)


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be a finite positive integer")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(f"{label} must be a finite positive integer")


def _merge_texts(*groups: Any) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        if group in (None, False, ""):
            continue
        values = (group,) if isinstance(group, str) else group
        for value in values:
            text = _required_text(value, "text value")
            if text not in merged:
                merged.append(text)
    return tuple(merged)


def _recorded_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _slug(value: str) -> str:
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {":", "/", "_", "-", "."}:
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    return slug or "portfolio"


__all__ = [
    "BuildingIntakeRunResult",
    "CustomerSandboxRunResult",
    "PortfolioDriveResult",
    "run_building_intake",
    "run_customer_building_in_sandbox",
    "run_declared_portfolio",
]
