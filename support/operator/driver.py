"""Bounded declared multi-Building driver for BUILDING-OPERATOR-DRIVER-0.

This support module composes the existing single-Building
``run_building_plan()`` surface over a caller/COO-declared finite portfolio. It
does not discover, invent, or choose Buildings. Brick owns the candidate plan
refs, Agent may return non-binding transition_concern_evidence, and Link /
declared portfolio policy owns adoption plus the finite transition budget.
"""

from __future__ import annotations

import json

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import validate_transition_concern_evidence
from brick_protocol.brick.work import parse_required_return_shape
from brick_protocol.link.transition import DISPOSITION_ACTIONS
from brick_protocol.support.connection.agent_adapter import (
    AgentBrainCallable,
    CommandRunner,
)
from brick_protocol.support.operator.building_operation import observe_building_frontier
from brick_protocol.support.operator.composition_compose import compose_building
from brick_protocol.support.operator.composition_gate_translation import (
    declared_portfolio_gate_translations,
    stamp_declared_portfolio_closure_gates,
)
from brick_protocol.support.operator.composition_intent import (
    inline_task_source_carry,
    materialize_building_intent,
)
from brick_protocol.support.operator.contracts import BuildingPlanSupportResult
from brick_protocol.support.operator.plan_rendering import _load_shape_registry
from brick_protocol.support.operator.run import (
    ChatSessionParkFrontierEvidenceWritten,
    run_building_plan,
)
from brick_protocol.support.operator.worktree_sandbox import (
    WorktreeSandboxError,
    _git,
    _git_status_paths,
    anchor_wip_snapshot,
    commit_sandbox_output,
    create_worktree_sandbox,
    dispose_worktree_sandbox,
    probe_worktree_capable,
    reclaim_wip_anchor,
    temp_dir_fallback,
)
from brick_protocol.support.operator.assembly import _write_path_covered_by
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
_CUSTOMER_GRAPH_TEMPLATE_AUTHORITY_FIELDS = frozenset(
    (
        "required_return_shape",
        "carries_forward_fields",
        "brick_instruction_body",
        "brick_template_refs",
    )
)
_FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_FRONTIER = "human_review_waiting"
_FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_REASON = "fake_landing_write_scope_diff_absent"


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
    wip_anchor_ref: str  # "" unless a non-complete worktree run preserved WIP
    wip_commit_sha: str  # "" unless wip_anchor_ref resolves to a commit
    worktree_disposed: bool
    intake_result: BuildingIntakeRunResult | None = None
    frontier_reason: str = ""


def _customer_graph_node_items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        items: list[Mapping[str, Any]] = []
        for node_id, raw_node in value.items():
            if isinstance(raw_node, Mapping):
                merged = dict(raw_node)
                merged.setdefault("node_id", str(node_id))
                items.append(merged)
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _customer_graph_intake_packet(packet: Any) -> Mapping[str, Any]:
    """Coerce operator-drawn graph objects to the ordinary graph intake packet."""

    if isinstance(packet, Mapping):
        return packet
    as_intake_args = getattr(packet, "as_intake_args", None)
    if not callable(as_intake_args):
        raise TypeError("customer graph input must be a mapping or expose as_intake_args()")
    intake_packet = as_intake_args()
    if not isinstance(intake_packet, Mapping):
        raise TypeError("customer graph as_intake_args() must return a mapping")
    return intake_packet


def _customer_graph_fan_in_source_node_ids(packet: Mapping[str, Any]) -> frozenset[str]:
    edge_source_by_ref: dict[str, str] = {}
    raw_edges = packet.get("edges", ())
    if isinstance(raw_edges, Sequence) and not isinstance(raw_edges, (str, bytes)):
        for edge in raw_edges:
            if not isinstance(edge, Mapping):
                continue
            edge_ref = str(edge.get("edge_ref") or "").strip()
            source = str(edge.get("source") or "").strip()
            if edge_ref and source:
                edge_source_by_ref[edge_ref] = source

    source_ids: set[str] = set()
    raw_groups = packet.get("groups", ())
    if not isinstance(raw_groups, Sequence) or isinstance(raw_groups, (str, bytes)):
        return frozenset()
    for group in raw_groups:
        if not isinstance(group, Mapping):
            continue
        if str(group.get("group_role") or "").strip() != "fan_in":
            continue
        member_refs = group.get("member_refs", ())
        if not isinstance(member_refs, Sequence) or isinstance(member_refs, (str, bytes)):
            continue
        for member_ref in member_refs:
            source = edge_source_by_ref.get(str(member_ref).strip())
            if source:
                source_ids.add(source)
    return frozenset(source_ids)


def _fan_in_source_required_return_shape_matches_template(
    repo_root: Path,
    node: Mapping[str, Any],
    required_return_shape: Any,
) -> bool:
    step_template_ref = str(node.get("step_template_ref") or "").strip()
    if not step_template_ref:
        return False
    registry = _load_shape_registry(repo_root)
    step_templates = registry.get("step_templates")
    if not isinstance(step_templates, Mapping):
        return False
    step_template = step_templates.get(step_template_ref)
    if not isinstance(step_template, Mapping):
        return False
    try:
        return parse_required_return_shape(required_return_shape) == parse_required_return_shape(
            step_template.get("required_return_shape")
        )
    except (TypeError, ValueError):
        return False


def _reject_customer_graph_template_authority_overrides(
    packet: Mapping[str, Any],
    *,
    repo_root: Path,
) -> None:
    """Fail closed when customer graph input re-authors Brick template-owned fields.

    The customer graph route lets caller/COO choose the road: node kind, node order,
    and Link edges. Brick templates still own instruction bodies, template refs,
    required return shape, and carry subsets. Expert/internal composition helpers
    can use ``compose_building`` directly; the customer sandbox graph wrapper cannot
    accept those overrides. The one narrow exception is ``required_return_shape`` on
    a declared fan-in source when the supplied field list is byte-for-field
    equivalent to that node's Brick template return shape. This lets the fluent
    ``assemble()`` packet carry its materialized row data without reopening the old
    fan-in-source shape-shrink path; Link carry filtering stays owned by
    ``carries_forward_fields``.
    """

    offenders: list[str] = []
    fan_in_source_node_ids = _customer_graph_fan_in_source_node_ids(packet)
    for index, node in enumerate(_customer_graph_node_items(packet.get("nodes"))):
        node_id = str(node.get("node_id") or node.get("step_ref") or f"nodes[{index}]")
        locations = (node,)
        raw_brick = node.get("brick")
        if isinstance(raw_brick, Mapping):
            locations = (node, raw_brick)
        for location in locations:
            for field in sorted(_CUSTOMER_GRAPH_TEMPLATE_AUTHORITY_FIELDS):
                if field == "required_return_shape" and node_id in fan_in_source_node_ids:
                    if _fan_in_source_required_return_shape_matches_template(
                        repo_root,
                        node,
                        location.get(field),
                    ):
                        continue
                if field in location:
                    offenders.append(f"{node_id}.{field}")
    if offenders:
        raise ValueError(
            "customer graph_packet may not author Brick template-owned field(s): "
            + ", ".join(offenders)
            + "; choose step_template_ref/kind and let brick.md/return.yaml materialize"
        )


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


def _write_and_run_declared_graph_plan(
    plan: Mapping[str, Any],
    *,
    output: Path,
    overwrite_existing: bool,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    proof_limits: Iterable[str] | str | None,
    building_id_label: str,
    shape_error: str,
) -> tuple[str, Path, BuildingPlanSupportResult]:
    """Persist one declared graph plan and run it through the public run seam.

    This is support-only intake plumbing. It centralizes the on-disk plan
    handoff shared by the preset and direct-graph intakes; it does not author a
    plan, choose Movement, or classify the returned Building evidence.
    """

    plan_shape = str(plan.get("plan_shape") or "")
    if plan_shape != "graph":
        raise ValueError(shape_error)

    building_id = _required_text(plan.get("building_id"), building_id_label)
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
    return building_id, plan_path, run_result


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

    walker_mode = "dynamic"
    walker_mode_basis = (
        "driver requires graph plan and lets run_building_plan derive dynamic dispatch; "
        "not a Link Movement decision"
    )

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
    building_id, plan_path, run_result = _write_and_run_declared_graph_plan(
        plan,
        output=output,
        overwrite_existing=overwrite_existing,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
        proof_limits=proof_limits,
        building_id_label="materialized plan building_id",
        shape_error="driver run_building_intake admits only plan_shape: graph",
    )

    return BuildingIntakeRunResult(
        building_id=building_id,
        plan_path=plan_path,
        plan_shape="graph",
        walker_mode=walker_mode,
        walker_mode_basis=walker_mode_basis,
        run_result=run_result,
        task_source_basis=task_source_basis,
    )


def run_composed_graph_intake(
    nodes: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    task_statement: Any,
    declared_by: str,
    groups: Sequence[Mapping[str, Any]] = (),
    selected_shape_ref: str = "",
    chain_preset_ref: str = "",
    plan_ref: str = "",
    building_id: str = "",
    selected_adapter_ref: str = "adapter:local",
    selected_model_ref: str = "model:default",
    transition_concern_adoption: str = "",
    repo_root: Path | str | None = None,
    output_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_cwd: Path | str | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
) -> BuildingIntakeRunResult:
    """Internal/checker-only seam, not a public ordering surface; main AI uses run_building_intake or assemble.

    H2a (heart H2 deterministic plumbing). This is the sibling of
    ``run_building_intake`` for the DIRECT-GRAPH flow: a caller (today the
    checker; tomorrow the H2b design AI that reads the board) hands a graph it
    already laid out as ``compose_building`` arguments -- nodes, edges, groups,
    declared_by -- together with the inline ``task_statement`` it is building
    against, and this seam runs it WITHOUT a chain preset. ``compose_building``
    treats ``chain_preset_ref`` as OPTIONAL and already emits ``plan_shape:
    graph``, but it OMITS the task-source/evidence carry that
    ``materialize_building_intent`` authors on the preset path. So this seam
    REATTACHES the REQUIRED inline carry (``inline_task_source_carry``, which
    reuses the materializer's own body normalization, sha256, basis, and STABLE
    id derive -- no duplication) onto the composed plan, then writes the plan
    and runs it through the SAME ``run_building_plan`` entrypoint the preset
    intake uses. The result is an evidence spine INDISTINGUISHABLE in validity
    from a preset-intake run: INLINE ``task_source_ref``, ``work/task.md`` body
    == ``task_statement`` verbatim, a STABLE/idempotent ``building_id``, and
    ``plan_shape: graph``.

    It is pure support mechanics. It composes ``compose_building`` (the caller
    owns every node/edge/gate choice) + the inline carry author + the existing
    single-Building run, and records the handoff. It does NOT choose Movement,
    pick an agent outside the NEED<->CAPABILITY match compose_building enforces,
    judge success / sufficiency / quality, or select a preset (there is none).
    The preset path (``run_building_intake`` / ``materialize_building_intent``)
    is UNTOUCHED and ``compose_building`` is called unchanged.

    Idempotency: when ``building_id`` is omitted, the STABLE inline default id
    (sha256 of statement body + preset) is used, so the same composed intent
    retried re-derives the SAME id and collides loudly with the existing
    declared-plan root instead of duplicating roots -- exactly the preset inline
    path's discipline.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()

    # 1. Compose the caller/COO-declared graph WITHOUT a preset. This call is
    #    byte-for-byte the same compose_building the checker compose path uses;
    #    it validates the graph and emits plan_shape: graph but omits the carry.
    plan = dict(
        compose_building(
            nodes,
            edges,
            selected_shape_ref=selected_shape_ref,
            declared_by=declared_by,
            groups=groups,
            chain_preset_ref=chain_preset_ref,
            plan_ref=plan_ref,
            building_id=building_id,
            selected_adapter_ref=selected_adapter_ref,
            selected_model_ref=selected_model_ref,
            transition_concern_adoption=transition_concern_adoption,
            repo_root=repo,
        )
    )

    # 2. Reattach the REQUIRED inline task-source evidence carry the preset path
    #    authors in materialize_building_intent. inline_task_source_carry is the
    #    single source of the body normalization + hash + id derive, so this
    #    carry is identical to the inline preset path's (declaration_packets.py
    #    re-hashes the carried body at evidence-write time and raises on drift;
    #    run admission rejects a sentinel ref with no body).
    carry = inline_task_source_carry(task_statement, chain_preset_ref=chain_preset_ref)
    plan["task_source_ref"] = carry["task_source_ref"]
    plan["task_statement"] = carry["task_statement"]
    plan["task_source_hash"] = carry["task_source_hash"]
    plan["task_source_hash_algorithm"] = carry["task_source_hash_algorithm"]
    plan["task_source_hash_basis"] = carry["task_source_hash_basis"]

    # 3. Stable/idempotent building_id: an explicit caller id wins; otherwise the
    #    materializer's STABLE inline default (sha256 of body + preset) so a
    #    retried intent collides loudly instead of duplicating roots.
    raw_building_id = str(plan.get("building_id") or "").strip()
    if not building_id.strip() and (not raw_building_id or raw_building_id == "composed-graph"):
        raw_building_id = str(carry["default_building_id"])
    plan["building_id"] = raw_building_id

    walker_mode = "dynamic"
    walker_mode_basis = (
        "driver requires graph plan and lets run_building_plan derive dynamic dispatch; "
        "not a Link Movement decision"
    )

    output = Path(output_root).resolve() if output_root is not None else DEFAULT_BUILDINGS_ROOT
    resolved_building_id, plan_path, run_result = _write_and_run_declared_graph_plan(
        plan,
        output=output,
        overwrite_existing=overwrite_existing,
        local_callables=local_callables,
        command_runner=command_runner,
        adapter_cwd=adapter_cwd,
        adapter_timeout_seconds=adapter_timeout_seconds,
        proof_limits=proof_limits,
        building_id_label="composed plan building_id",
        shape_error="driver run_composed_graph_intake admits only plan_shape: graph",
    )

    return BuildingIntakeRunResult(
        building_id=resolved_building_id,
        plan_path=plan_path,
        plan_shape="graph",
        walker_mode=walker_mode,
        walker_mode_basis=walker_mode_basis,
        run_result=run_result,
        task_source_basis="task_statement",
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

    # The customer-facing PRESET dispatch and the H3b customer-facing GOAL
    # dispatch share ONE worktree-sandbox lifecycle bracket (probe -> temp-dir
    # fallback / create -> run -> observe frontier -> commit-on-complete ->
    # dispose). Only the inner RUN differs: this preset path runs the confirmed
    # intent through run_building_intake; the goal path composes a graph and runs
    # it through run_composed_graph_intake. Sharing the bracket keeps the W1
    # live-tree-untouched invariant in ONE place (no fork).
    def _run_preset(repo_root: Path, adapter_cwd: Path) -> BuildingIntakeRunResult:
        return run_building_intake(
            intent,
            repo_root=repo_root,
            output_root=durable_output,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            proof_limits=proof_limits,
        )

    return _run_in_worktree_sandbox(
        repo,
        building_id=building_id,
        durable_output=durable_output,
        run_dispatch=_run_preset,
    )


def run_customer_graph_building_in_sandbox(
    packet: Any,
    *,
    customer_repo_root: Path | str,
    output_root: Path | str | None = None,
    overwrite_existing: bool = False,
    local_callables: Mapping[str, AgentBrainCallable] | None = None,
    command_runner: CommandRunner | None = None,
    adapter_timeout_seconds: int = 120,
    proof_limits: Iterable[str] | str | None = None,
) -> CustomerSandboxRunResult:
    """Run a caller/COO-declared graph packet through the customer sandbox.

    This is the customer-facing graph wrapper. It owns only the W1 sandbox
    bracket and delegates the declared graph body to the internal
    ``run_composed_graph_intake`` seam. It does not invent nodes, edges, gates,
    Movement, route targets, success, or quality.
    """

    repo = Path(customer_repo_root).resolve()
    packet = _customer_graph_intake_packet(packet)
    _reject_customer_graph_template_authority_overrides(packet, repo_root=repo)

    durable_output = Path(output_root).resolve() if output_root is not None else DEFAULT_BUILDINGS_ROOT
    building_id = _required_text(packet.get("building_id"), "graph packet building_id")

    def _run_graph(repo_root: Path, adapter_cwd: Path) -> BuildingIntakeRunResult:
        return run_composed_graph_intake(
            packet.get("nodes", ()),
            packet.get("edges", ()),
            task_statement=packet.get("task_statement"),
            declared_by=_required_text(packet.get("declared_by"), "graph packet declared_by"),
            groups=packet.get("groups", ()),
            selected_shape_ref=str(packet.get("selected_shape_ref") or ""),
            chain_preset_ref=str(packet.get("chain_preset_ref") or ""),
            plan_ref=str(packet.get("plan_ref") or ""),
            building_id=building_id,
            selected_adapter_ref=str(packet.get("selected_adapter_ref") or "adapter:local"),
            selected_model_ref=str(packet.get("selected_model_ref") or "model:default"),
            transition_concern_adoption=str(
                packet.get("transition_concern_adoption")
                or packet.get("adoption")
                or ""
            ),
            repo_root=repo_root,
            output_root=durable_output,
            overwrite_existing=overwrite_existing,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            proof_limits=proof_limits,
        )

    return _run_in_worktree_sandbox(
        repo,
        building_id=building_id,
        durable_output=durable_output,
        run_dispatch=_run_graph,
    )


def _run_in_worktree_sandbox(
    repo: Path,
    *,
    building_id: str,
    durable_output: Path,
    run_dispatch: "Callable[[Path, Path], BuildingIntakeRunResult]",
) -> CustomerSandboxRunResult:
    """Shared W1 worktree-sandbox lifecycle bracket around an inner dispatch.

    THE single home of the customer-facing live-tree-untouched invariant.
    ``run_customer_building_in_sandbox`` (preset path) routes through here; only
    ``run_dispatch`` differs. It is pure
    support mechanics: it owns no axis, chooses no Movement, judges no
    success/quality, and authors no plan -- it ONLY brackets the run with the
    worktree sandbox. ``run_dispatch(repo_root, adapter_cwd)`` runs the inner
    dispatch with the supplied roots and returns its ``BuildingIntakeRunResult``;
    its OWN ``output_root`` MUST be ``durable_output`` (OUTSIDE the worktree) so
    evidence survives disposal.

    The 6 locked decisions + 4 mitigations live here exactly as the customer
    preset path carried them (behavior unchanged for that path):

    1. BASE = the explicitly resolved HEAD SHA (probe records it; never a bare
       ``--detach`` race).
    2. WHERE = ~/.brick/worktrees/<building-id>/ (outside the repo).
    3. COMMIT on GENUINE completion only.
    4. NON-GIT / DIRTY / no-git -> probe fails closed -> disposable temp dir as
       adapter_cwd; the live tree is NEVER written.
    5. Per-building granularity: one worktree per building id.
    6. REAL isolation: adapter_cwd AND repo_root point at the worktree (or temp
       dir); ``durable_output`` (evidence) stays OUTSIDE it.
    """

    def _run_with_temp_dir(reason: str) -> CustomerSandboxRunResult:
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
            intake = run_dispatch(repo, sandbox_cwd)
            frontier = observe_building_frontier(
                intake.run_result.lifecycle_write.root, repo_root=repo
            )
            frontier_kind = str(frontier.get("frontier_kind") or "")
            frontier_reason = str(frontier.get("frontier_reason") or "")
            if (
                reason.startswith("worktree-create-failed:")
                and frontier_kind == "complete"
                and _write_need_complete_without_scoped_diff(
                    sandbox_cwd,
                    intake.plan_path,
                )
            ):
                frontier_kind = _FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_FRONTIER
                frontier_reason = _FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_REASON
            return CustomerSandboxRunResult(
                building_id=intake.building_id,
                isolation_mode="temp_dir",
                isolation_reason=reason,
                base_sha="",
                worktree_path="",
                evidence_root=str(intake.run_result.lifecycle_write.root),
                frontier_kind=frontier_kind,
                commit_sha="",  # a temp dir is not a repo: no commit, by design
                wip_anchor_ref="",
                wip_commit_sha="",
                worktree_disposed=False,
                intake_result=intake,
                frontier_reason=frontier_reason,
            )
        finally:
            temp_dir.cleanup()

    # MITIGATION 4 (probe FIRST): is this a git work tree with git installed?
    # ANY probe failure -> degrade to a temp dir; if the actual worktree creation
    # is blocked by host/sandbox metadata permissions, degrade the same way.
    probe = probe_worktree_capable(repo)
    if not probe.ok:
        return _run_with_temp_dir(probe.reason)

    # MITIGATION 1: create the engine worktree detached at the resolved BASE SHA.
    try:
        sandbox = create_worktree_sandbox(
            repo,
            building_id=building_id,
            base_sha=probe.base_sha,
        )
    except WorktreeSandboxError as exc:
        return _run_with_temp_dir(f"worktree-create-failed:{type(exc).__name__}")
    commit_sha = ""
    wip_anchor_ref = ""
    wip_commit_sha = ""
    frontier_kind = ""
    frontier_reason = ""
    evidence_root = ""
    intake_result: BuildingIntakeRunResult | None = None
    try:
        # MITIGATION 6 (real isolation): the dispatch runs with BOTH adapter_cwd
        # AND repo_root pointing at the worktree, but evidence lands under the
        # durable output_root OUTSIDE the worktree.
        intake_result = run_dispatch(sandbox.path, sandbox.path)
        evidence_root = str(intake_result.run_result.lifecycle_write.root)
        # MITIGATION 3 (commit ONLY on genuine completion, AFTER the run bracket
        # so the write-observation HEAD guard is honored): observe the DURABLE
        # evidence frontier, then commit the worktree's changes only if complete.
        frontier = observe_building_frontier(
            intake_result.run_result.lifecycle_write.root,
            repo_root=sandbox.path,
        )
        frontier_kind = str(frontier.get("frontier_kind") or "")
        frontier_reason = str(frontier.get("frontier_reason") or "")
        if frontier_kind == "complete" and _write_need_complete_without_scoped_diff(
            sandbox.path,
            intake_result.plan_path,
        ):
            frontier_kind = _FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_FRONTIER
            frontier_reason = _FAKE_LANDING_WRITE_SCOPE_DIFF_ABSENT_REASON
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
        try:
            if not commit_sha:
                wip_anchor_ref = anchor_wip_snapshot(
                    sandbox,
                    building_id,
                    message=(
                        f"BRICK WIP anchor: {building_id}\n\n"
                        f"frontier={frontier_kind or 'unknown'} base={sandbox.base_sha}\n"
                        f"frontier_reason={frontier_reason}\n"
                        f"evidence_root={evidence_root}\n"
                    ),
                )
                if wip_anchor_ref:
                    reclaimed = reclaim_wip_anchor(sandbox.repo_root, building_id)
                    if reclaimed is not None:
                        wip_anchor_ref, wip_commit_sha = reclaimed
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
        wip_anchor_ref=wip_anchor_ref,
        wip_commit_sha=wip_commit_sha,
        worktree_disposed=disposed,
        intake_result=intake_result,
        frontier_reason=frontier_reason,
    )


def _write_need_complete_without_scoped_diff(
    sandbox_path: Path,
    plan_path: Path,
) -> bool:
    """Observe a completed write-needed plan with no diff inside write_scope."""

    scopes = _write_need_scopes_from_plan_path(plan_path)
    if not scopes:
        return False
    changed_paths = _sandbox_changed_paths(sandbox_path)
    if not changed_paths:
        return True
    return not any(
        _path_allowed_by_write_scope(path, scope)
        for path in changed_paths
        for scope in scopes
    )


def _write_need_scopes_from_plan_path(plan_path: Path) -> tuple[Mapping[str, Any], ...]:
    try:
        payload = _load_declared_plan_mapping(plan_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return ()
    scopes: list[Mapping[str, Any]] = []
    for row in _walk_mappings(payload):
        if row.get("requires_brick_write_scope") is not True:
            continue
        scope = row.get("write_scope")
        if isinstance(scope, Mapping):
            scopes.append(scope)
    return tuple(scopes)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _walk_mappings(child)


def _sandbox_changed_paths(sandbox_path: Path) -> tuple[str, ...]:
    status = _git(sandbox_path, "status", "--porcelain", "--untracked-files=all")
    if status is None:
        return ()
    return _git_status_paths(status)


def _path_allowed_by_write_scope(path: str, write_scope: Mapping[str, Any]) -> bool:
    clean_path = str(path).strip().replace("\\", "/")
    if not clean_path:
        return False
    raw_forbidden = write_scope.get("forbidden_paths", ())
    forbidden_items = (
        raw_forbidden
        if isinstance(raw_forbidden, Sequence) and not isinstance(raw_forbidden, (str, bytes, bytearray))
        else ()
    )
    forbidden = tuple(
        str(item).strip()
        for item in forbidden_items
        if str(item).strip()
    )
    if any(_write_path_covered_by(clean_path, pattern) for pattern in forbidden):
        return False
    raw_allowed = write_scope.get("allowed_paths", ())
    allowed_items = (
        raw_allowed
        if isinstance(raw_allowed, Sequence) and not isinstance(raw_allowed, (str, bytes, bytearray))
        else ()
    )
    allowed = tuple(
        str(item).strip()
        for item in allowed_items
        if str(item).strip()
    )
    return any(_write_path_covered_by(clean_path, pattern) for pattern in allowed)


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
    "run_customer_graph_building_in_sandbox",
    "run_declared_portfolio",
]
