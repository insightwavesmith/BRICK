"""Customer-facing Brick CLI support entrypoint.

This is a support wrapper over existing operator/checker seams. It bootstraps
the checkout import identity before importing repo-local support modules so the
console script works from outside the repo with PYTHONPATH unset.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SOURCE_CANDIDATE_REPO_ROOT = Path(__file__).resolve().parents[2]
if (_SOURCE_CANDIDATE_REPO_ROOT / "support/operator/import_identity.py").is_file():
    _source_candidate_text = str(_SOURCE_CANDIDATE_REPO_ROOT)
    if _source_candidate_text not in sys.path:
        sys.path.insert(0, _source_candidate_text)
try:
    from brick_protocol.support.operator.import_identity import (
        install_source_import_paths,
        resolve_operator_identity,
    )
except ModuleNotFoundError:
    from support.operator.import_identity import (
        install_source_import_paths,
        resolve_operator_identity,
    )

_OPERATOR_IMPORT_IDENTITY = resolve_operator_identity(__file__)
install_source_import_paths(_OPERATOR_IMPORT_IDENTITY)
_REPO_ROOT = _OPERATOR_IMPORT_IDENTITY.repo_root
_IMPORT_IDENTITY_ROOT = _OPERATOR_IMPORT_IDENTITY.import_identity_root

import argparse
import contextlib
import io
import json
import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from brick_protocol.brick.spec import derived_worktree_write_scope
try:
    from brick_protocol.support.checkers import check_profile
except ModuleNotFoundError:
    from support.checkers import check_profile
from brick_protocol.support.connection.adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ALLOWED_ADAPTER_REFS,
    adapter_boundary_matrix,
)
from brick_protocol.support.connection.agent_adapter import adapter_is_write_capable
from brick_protocol.support.connection.adapter_subprocess import preflight_provider
from brick_protocol.support.operator.first_use import FIRST_USE_FILENAME, write_first_use
from brick_protocol.support.operator import onboard
from brick_protocol.support.operator import resume_declaration
from brick_protocol.support.operator.assembly import (
    assemble_graph_declaration,
    graph_declaration_action,
    graph_declaration_author_ref,
    graph_declaration_output_root,
    graph_declaration_timeout,
    load_graph_declaration,
    persist_proposed_building_graph,
)
from brick_protocol.support.operator.driver import (
    run_customer_building_in_sandbox,
)
from brick_protocol.support.operator.onboard import run_goal_approve_entry
from brick_protocol.support.operator.graph_draft import (
    draft_graph_declaration,
    write_draft_declaration,
)
from brick_protocol.support.recording.capture import default_buildings_root


ADAPTER_LOCAL = "adapter:local"
REAL_PROVIDER_SELECTION_ORDER = (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
)
DEFAULT_EXAMPLE_BUILDING_ID = "brick-cli-example"
DEFAULT_EXAMPLE_TASK_SOURCE_REF = "brick/templates/tasks/source-template.md"
DEFAULT_LOCAL_PRESET_REF = "building-chain-preset:onboarding-example-graph"
DEFAULT_REAL_TASK_PRESET_REF = "building-chain-preset:fast-fix"
DEFAULT_DECLARED_BY = "coo"
# build-unify #12 (표17 casting convergence): the CLI no longer synthesizes
# per-node ``selected_*`` casting. --real-provider now ONLY chooses stub vs a real
# observed-write adapter (D3); the per-step performer is interpreted at the SINGLE
# casting interpretation point (plan_rendering._resolve_casting_selection via the
# agent-object ladder), identically for CLI --preset and build(preset=) (D1/D2).
# The deleted REAL_PROVIDER_MODEL_REFS / REAL_TASK_STEP_TEMPLATE_REFS /
# _real_task_step_selection_overrides rung was support deciding the Agent
# performer -- the exact entry-casting asymmetry #12 removes.

PROOF_LIMITS = (
    "support CLI wrapper only",
    "existing seams own run/checker behavior",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN = (
    "provider reliability",
    "future Building correctness",
    "semantic quality of Agent returns",
    "real-provider credential readiness",
    "production runtime behavior",
)

# Retired raw graph CLI notes for stale in-scope checker text probes only:
# run_customer_graph_building_in_sandbox remains the internal DSL driver seam;
# def _load_graph_packet, graph_packet, "--graph-packet", "--graph",
# declare either graph packet mode or task/task-source mode, not both,
# graph-packet-declared, and public_route": "brick build / brick build --graph"
# are no longer live customer CLI behavior.


def _support_observation_packet() -> dict[str, Any]:
    """Return product-route observations that remain support evidence only."""

    evidence_limits = [
        "support CLI observation only",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]
    return {
        "readiness_blocker_observation": {
            "schema": "support-readiness-blocker-observation/v1",
            "observed_blockers": [],
            "proof_limits": evidence_limits,
            "not_proven": [
                "real-provider credential readiness",
                "future Building correctness",
            ],
        },
        "protocol_compliance_observation": {
            "schema": "support-protocol-compliance-observation/v1",
            "public_route": "brick build",
            "bare_brick_behavior": "status support evidence",
            "proof_limits": evidence_limits,
            "not_proven": [
                "external dynamic-design pipeline end-to-end proof",
                "future route-surface drift",
            ],
        },
    }


def _json_dump(packet: Any) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def _repo_from_args(args: argparse.Namespace) -> Path:
    raw_repo = getattr(args, "repo", None)
    if raw_repo:
        return Path(raw_repo).resolve()
    return _REPO_ROOT


def _git_stdout(argv: Sequence[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *argv],
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _resolved_repo_root_observation(repo: Path) -> dict[str, Any]:
    cwd_repo = _git_stdout(["rev-parse", "--show-toplevel"], cwd=Path.cwd())
    resolved = str(repo.resolve())
    warnings: list[str] = []
    if cwd_repo and Path(cwd_repo).resolve() != repo.resolve():
        warnings.append(f"repo_root differs from cwd git root: cwd_repo={Path(cwd_repo).resolve()}")

    upstream = _git_stdout(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo)
    behind_count = ""
    if upstream:
        counts = _git_stdout(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], cwd=repo)
        parts = counts.split()
        if len(parts) == 2:
            behind_count = parts[1]
            try:
                if int(behind_count) > 0:
                    warnings.append(f"repo_root HEAD is behind {upstream} by {behind_count} commit(s)")
            except ValueError:
                pass
    return {
        "repo_root": resolved,
        "cwd_repo_root": str(Path(cwd_repo).resolve()) if cwd_repo else "",
        "repo_root_warnings": warnings,
        "repo_root_upstream_ref": upstream,
        "repo_root_behind_count": behind_count,
    }


def _hermetic_verify_argv(repo: Path) -> list[str]:
    return ["--repo", str(repo), "--profile", "core"]


def _repo_root_behind_count(repo_observation: dict[str, Any]) -> int:
    raw = str(repo_observation.get("repo_root_behind_count") or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _emit_launch_repo_root_observation(
    args: argparse.Namespace,
    repo_observation: dict[str, Any],
) -> int | None:
    """Print the resolved repo_root (+ drift warnings) as the FIRST launch line.

    build-unify #12 D4 (표16). Returns a non-zero exit code when the repo_root is
    behind its upstream and the caller has not opted into --allow-stale-repo
    (fail-closed refusal before the walk spends lane cost); otherwise returns None
    and the launch proceeds. In --json mode the human-facing lines are written to
    STDERR so the stdout JSON contract stays a single object.
    """

    stream = sys.stderr if getattr(args, "json", False) else sys.stdout
    print(f"repo_root: {repo_observation.get('repo_root', '')}", file=stream)
    cwd_repo_root = repo_observation.get("cwd_repo_root") or ""
    if cwd_repo_root:
        print(f"cwd_repo_root: {cwd_repo_root}", file=stream)
    for warning in repo_observation.get("repo_root_warnings", []):
        print(f"warning: {warning}", file=stream)
    behind = _repo_root_behind_count(repo_observation)
    if behind > 0 and not getattr(args, "allow_stale_repo", False):
        upstream = repo_observation.get("repo_root_upstream_ref") or "upstream"
        print(
            "refusing to launch: repo_root HEAD is behind "
            f"{upstream} by {behind} commit(s); rerun with --allow-stale-repo to "
            "override (표16: stale-tree launches walk the wrong checkout)",
            file=sys.stderr,
        )
        return 3
    return None


def _default_builds_root() -> Path:
    """Return the customer-visible default evidence root used by ``brick build``.

    The function name is kept for older support projections, but the value is
    the active ref-less Building evidence root from the capture seam.
    """

    return _active_slack_buildings_root()


def _active_slack_buildings_root() -> Path:
    """Return this goal's active Slack-facing vessel root.

    This official CLI graph default follows the caller-local evidence home
    (``BRICK_HOME`` or ``~/.brick``) through the single capture seam. It is
    support evidence routing only, not source truth.
    """

    return default_buildings_root()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _task_building_id() -> str:
    return f"brick-cli-task-{_utc_stamp()}-{uuid4().hex[:8]}"


def _selected_build_preset(args: argparse.Namespace, *, adapter: str, task: str) -> str:
    declared = (getattr(args, "preset", "") or "").strip()
    if declared:
        return declared
    if task and adapter_is_write_capable(adapter):
        return DEFAULT_REAL_TASK_PRESET_REF
    return DEFAULT_LOCAL_PRESET_REF


def _task_write_scope(*, adapter: str, task: str) -> dict[str, Any] | None:
    if task and adapter_is_write_capable(adapter):
        return derived_worktree_write_scope()
    return None

def _readiness_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Return redacted provider-readiness evidence safe for CLI packets."""

    evidence: dict[str, Any] = {
        "adapter_ref": str(row.get("adapter_ref") or ""),
        "ok": bool(row.get("ok")),
        "installed": bool(row.get("installed")),
        "authed": str(row.get("authed") or "unknown"),
    }
    if "api_key_env_present" in row:
        evidence["api_key_env_present"] = bool(row.get("api_key_env_present"))
    if "credential_validity" in row:
        evidence["credential_validity"] = str(row.get("credential_validity") or "not_proven")
    return evidence


def _adapter_boundary_packet() -> dict[str, Any]:
    """Return customer-reportable adapter boundary evidence."""

    return {
        "schema": "support-adapter-boundary-matrix/v1",
        "rows": [dict(row) for row in adapter_boundary_matrix()],
        "proof_limits": [
            "support CLI report only",
            "adapter identity is not write authority",
            "write_effective still derives from Brick write_scope plus Agent policy plus observed-write support",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "credential validity",
            "provider availability",
            "provider process integrity",
            "future Building correctness",
        ],
    }


def _first_ready_real_provider_choice() -> dict[str, Any]:
    """Choose the first ready observed-write provider from declared support order.

    This is support readiness observation only. It stores no credential/session
    bodies and falls back to adapter:local when no observed-write provider is
    ready.
    """

    observed_rows: list[dict[str, Any]] = []
    for adapter_ref in REAL_PROVIDER_SELECTION_ORDER:
        status = preflight_provider(adapter_ref)
        row = _readiness_evidence(dict(status))
        observed_rows.append(row)
        if row["ok"] and adapter_is_write_capable(adapter_ref):
            return {
                "adapter_ref": adapter_ref,
                "adapter_choice_basis": (
                    "real-provider omitted --adapter; first ready observed-write "
                    f"adapter in declared order selected: {adapter_ref}"
                ),
                "provider_readiness_observations": observed_rows,
            }
    return {
        "adapter_ref": ADAPTER_LOCAL,
        "adapter_choice_basis": (
            "real-provider omitted --adapter; no ready observed-write provider "
            "observed in declared order -> adapter:local fallback"
        ),
        "provider_readiness_observations": observed_rows,
    }


def _customer_visible_frontier_state(frontier_kind: str) -> str:
    return "frontier_complete" if frontier_kind == "complete" else "not_ready"


def _customer_visible_frontier_message(frontier_kind: str) -> str:
    if frontier_kind == "complete":
        return (
            "frontier complete: evidence closed for this Building. "
            "This remains support evidence, not source truth or quality judgment."
        )
    if frontier_kind:
        return (
            f"not ready: Building frontier is {frontier_kind}; inspect evidence_root "
            "before treating output as customer-ready."
        )
    return (
        "not ready: no Building frontier was observed; inspect evidence_root before "
        "treating output as customer-ready."
    )


def _build_intent(args: argparse.Namespace) -> dict[str, Any]:
    # --real-provider is friendly sugar: when the customer opts into a real
    # provider and omits --adapter, observe provider readiness and select the
    # first ready observed-write adapter. An explicit --adapter always wins.
    explicit_adapter = bool(getattr(args, "adapter", ""))
    readiness_choice: dict[str, Any] = {}
    adapter = args.adapter if explicit_adapter else ADAPTER_LOCAL
    if getattr(args, "real_provider", False) and not explicit_adapter:
        readiness_choice = _first_ready_real_provider_choice()
        adapter = str(readiness_choice["adapter_ref"])
    if adapter not in ALLOWED_ADAPTER_REFS:
        raise ValueError(f"adapter_ref is not admitted for customer CLI: {adapter}")
    task = (args.task or "").strip()
    preset = _selected_build_preset(args, adapter=adapter, task=task)
    if task:
        building_id = args.building_id or _task_building_id()
        # build-unify #12 D1/D2: the confirmed task/preset intent is built by the
        # SINGLE shared builder onboard.build_preset_intent, so CLI --preset and
        # build_preset() cannot drift. The CLI adds ONLY human-declared rungs
        # (task text, preset, the plan-level adapter, worktree write_scope); it no
        # longer synthesizes per-node casting -- the per-step performer is
        # interpreted at the single casting interpretation point downstream.
        return onboard.build_preset_intent(
            declared_by=args.declared_by,
            selected_adapter_ref=adapter,
            chain_preset_ref=preset,
            task_statement=task,
            building_id=building_id,
            write_scope=_task_write_scope(adapter=adapter, task=task),
            adapter_choice_basis=(
                readiness_choice.get("adapter_choice_basis", "") if readiness_choice else ""
            ),
            provider_readiness_observations=(
                readiness_choice.get("provider_readiness_observations")
                if readiness_choice
                else None
            ),
        )
    return onboard.build_preset_intent(
        declared_by=args.declared_by,
        selected_adapter_ref=adapter,
        chain_preset_ref=preset,
        task_source_ref=args.task_source_ref,
        building_id=args.building_id or DEFAULT_EXAMPLE_BUILDING_ID,
        adapter_choice_basis=(
            readiness_choice.get("adapter_choice_basis", "") if readiness_choice else ""
        ),
        provider_readiness_observations=(
            readiness_choice.get("provider_readiness_observations")
            if readiness_choice
            else None
        ),
    )


def _materialized_step_adapter_evidence(plan_path: Path) -> list[dict[str, str]]:
    try:
        packet = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    plan = packet.get("declared_plan_copy") if isinstance(packet, dict) else None
    if not isinstance(plan, dict):
        plan = packet if isinstance(packet, dict) else {}
    steps = plan.get("brick_steps")
    if not isinstance(steps, list):
        steps = plan.get("steps")
    if not isinstance(steps, list):
        return []
    rows: list[dict[str, str]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        row = {
            "step_ref": str(step.get("step_ref") or ""),
            "step_template_ref": str(step.get("step_template_ref") or ""),
            "selected_adapter_ref": str(step.get("selected_adapter_ref") or ""),
            "selected_model_ref": str(step.get("selected_model_ref") or ""),
        }
        if any(row.values()):
            rows.append(row)
    return rows


def _run_build(args: argparse.Namespace) -> dict[str, Any]:
    repo = _repo_from_args(args)
    if getattr(args, "graph_decl", ""):
        return _run_graph_declaration_build(args, repo=repo)
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else _active_slack_buildings_root()
    )
    intent = _build_intent(args)
    overwrite_existing = bool(args.overwrite_existing or not args.task)
    result = run_customer_building_in_sandbox(
        intent,
        customer_repo_root=repo,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        adapter_timeout_seconds=args.timeout,
        proof_limits=PROOF_LIMITS,
    )
    intake = result.intake_result
    frontier_kind = result.frontier_kind
    packet: dict[str, Any] = {
        "command": "build",
        "build_input_mode": "preset_task",
        "repo_root": str(repo),
        "output_root": str(output_root),
        "building_id": result.building_id,
        "declared_by": intent["declared_by"],
        "task_source_basis": "task_statement" if args.task else "task_source_ref",
        "chain_preset_ref": intent["chain_preset_ref"],
        "adapter_ref": intent["selected_adapter_ref"],
        "adapter_choice_basis": intent.get("adapter_choice_basis", "explicit-or-local-adapter"),
        "provider_readiness_observations": intent.get("provider_readiness_observations", []),
        "isolation_mode": result.isolation_mode,
        "isolation_reason": result.isolation_reason,
        "base_sha": result.base_sha,
        "worktree_path": result.worktree_path,
        "evidence_root": result.evidence_root,
        "frontier_kind": frontier_kind,
        "customer_visible_frontier_state": _customer_visible_frontier_state(frontier_kind),
        "customer_visible_not_ready": frontier_kind != "complete",
        "customer_visible_frontier_message": _customer_visible_frontier_message(frontier_kind),
        "commit_sha": result.commit_sha,
        "worktree_disposed": result.worktree_disposed,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    packet.update(_resolved_repo_root_observation(repo))
    packet.update(_support_observation_packet())
    if intake is not None:
        packet.update(
            {
                "plan_path": str(intake.plan_path),
                "plan_shape": intake.plan_shape,
                "walker_mode": intake.walker_mode,
                "walker_mode_basis": intake.walker_mode_basis,
                "materialized_step_adapters": _materialized_step_adapter_evidence(
                    intake.plan_path
                ),
            }
        )
    return packet


def _run_graph_declaration_build(args: argparse.Namespace, *, repo: Path) -> dict[str, Any]:
    declaration_path = Path(args.graph_decl).expanduser().resolve()
    declaration = load_graph_declaration(declaration_path)
    composed = assemble_graph_declaration(declaration, repo_root=repo)
    declared_output_root = graph_declaration_output_root(declaration)
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else Path(declared_output_root).expanduser().resolve()
        if declared_output_root
        else _active_slack_buildings_root()
    )
    proposal_path = persist_proposed_building_graph(
        composed,
        output_root,
        overwrite=bool(args.overwrite_existing),
    )
    action = graph_declaration_action(declaration)
    timeout = graph_declaration_timeout(declaration, args.timeout)
    approval = run_goal_approve_entry(
        proposal_path,
        action=action,
        author_ref=graph_declaration_author_ref(declaration),
        output_root=output_root,
        repo_root=repo,
        overwrite_existing=bool(args.overwrite_existing),
        adapter_timeout_seconds=timeout,
        proof_limits=PROOF_LIMITS,
    )
    packet: dict[str, Any] = {
        "command": "build",
        "build_input_mode": "graph_decl",
        "graph_decl_path": str(declaration_path),
        "output_root": str(output_root),
        "building_id": composed.building_id,
        "declared_by": composed.declared_by,
        "adapter_ref": composed.selected_adapter_ref,
        "selected_model_ref": composed.selected_model_ref,
        "chain_preset_ref": "",
        "proposal_ref": str(proposal_path),
        "approval_result": approval,
        "action": action,
        "ran": bool(approval.get("ran")),
        "plan_path": str(proposal_path),
        "plan_shape": composed.composed_plan.get("plan_shape", "graph"),
        "materialized_step_adapters": _materialized_step_adapter_evidence(proposal_path),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    packet.update(_resolved_repo_root_observation(repo))
    packet.update(_support_observation_packet())
    if approval.get("evidence_root"):
        packet["evidence_root"] = approval.get("evidence_root")
    if approval.get("frontier_kind"):
        frontier_kind = str(approval.get("frontier_kind"))
        packet["frontier_kind"] = frontier_kind
        packet["customer_visible_frontier_state"] = _customer_visible_frontier_state(frontier_kind)
        packet["customer_visible_not_ready"] = frontier_kind != "complete"
        packet["customer_visible_frontier_message"] = _customer_visible_frontier_message(frontier_kind)
    else:
        packet["frontier_kind"] = ""
        packet["customer_visible_frontier_state"] = "not_ready"
        packet["customer_visible_not_ready"] = True
        packet["customer_visible_frontier_message"] = "not ready: graph declaration action did not run a Building."
    return packet


def _render_build(packet: dict[str, Any]) -> str:
    lines = [
        f"repo_root: {packet['repo_root']}",
        "Brick build support evidence",
        f"build_input_mode: {packet.get('build_input_mode', 'preset_task')}",
        f"building_id: {packet['building_id']}",
        f"adapter_ref: {packet['adapter_ref']}",
        f"adapter_choice_basis: {packet.get('adapter_choice_basis', 'not recorded')}",
        f"chain_preset_ref: {packet['chain_preset_ref']}",
        f"isolation_mode: {packet.get('isolation_mode', 'proposal-approval')}",
        f"evidence_root: {packet.get('evidence_root', '')}",
        f"frontier_kind: {packet['frontier_kind']}",
        f"customer_visible_frontier_state: {packet['customer_visible_frontier_state']}",
        "customer_visible_not_ready: "
        + ("yes" if packet.get("customer_visible_not_ready") else "no"),
        f"frontier_message: {packet['customer_visible_frontier_message']}",
    ]
    if packet.get("plan_path"):
        lines.append(f"plan_path: {packet['plan_path']}")
    if packet.get("proposal_ref"):
        lines.append(f"proposal_ref: {packet['proposal_ref']}")
    if packet.get("action"):
        lines.append(f"action: {packet['action']}")
    for warning in packet.get("repo_root_warnings", []):
        lines.append(f"warning: {warning}")
    if packet.get("materialized_step_adapters"):
        lines.append("materialized_step_adapters:")
        for row in packet["materialized_step_adapters"]:
            lines.append(
                "- "
                + str(row.get("step_ref", ""))
                + ": "
                + str(row.get("selected_adapter_ref", ""))
                + " ("
                + str(row.get("selected_model_ref", ""))
                + ")"
            )
    if packet.get("worktree_path"):
        lines.append(f"worktree_path: {packet['worktree_path']}")
    if packet.get("commit_sha"):
        lines.append(f"commit_sha: {packet['commit_sha']}")
    lines.append("proof_limits: " + "; ".join(packet["proof_limits"]))
    lines.append("not_proven: " + "; ".join(packet["not_proven"]))
    return "\n".join(lines)


def _public_error_packet(args: argparse.Namespace, exc: Exception) -> dict[str, Any]:
    """Classify CLI errors without echoing raw exception bodies to customers."""

    raw_message = str(exc)
    error_kind = type(exc).__name__
    command = str(getattr(args, "command", "") or "")
    public_code = "operator_error"
    public_message = "command rejected; inspect support evidence and retry with corrected input"
    if isinstance(exc, FileExistsError):
        public_code = "building_root_exists"
        public_message = (
            "Building evidence root already exists; choose a new building id or "
            "pass --overwrite-existing deliberately"
        )
    elif isinstance(exc, ValueError):
        if "adapter_ref is not admitted" in raw_message:
            public_code = "adapter_ref_not_admitted"
            public_message = "adapter ref is not admitted for the customer CLI"
        else:
            public_code = "input_rejected"
            public_message = "input rejected by the support CLI boundary"
    elif isinstance(exc, ModuleNotFoundError):
        public_code = "import_identity_not_ready"
        public_message = (
            "import identity is not ready; run from the repo root or use the "
            "documented uv command"
        )
    return {
        "command": command,
        "error_kind": error_kind,
        "public_error_code": public_code,
        "public_error_message": public_message,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _render_doctor(packet: dict[str, Any]) -> str:
    lines = ["Brick doctor support evidence", "rows:"]
    for row in packet.get("rows", []):
        observed = "yes" if row.get("ok") else "no"
        details: list[str] = []
        if "api_key_env_present" in row:
            key_observed = "yes" if row.get("api_key_env_present") else "no"
            details.append(f"api_key_env_present={key_observed}")
        if row.get("credential_validity"):
            details.append(f"credential_validity={row.get('credential_validity')}")
        detail_text = f"; {'; '.join(details)}" if details else ""
        lines.append(
            f"- {row.get('target', '')}: observed_ok={observed}; "
            f"{row.get('message_ko', '')}{detail_text}"
        )
    lines.append("symptom_table:")
    for symptom, prescription in packet.get("symptom_table", []):
        lines.append(f"- {symptom} -> {prescription}")
    boundary = packet.get("adapter_boundary_matrix")
    if isinstance(boundary, dict):
        lines.append("adapter_boundary_matrix:")
        for row in boundary.get("rows", []):
            lines.append(
                "- "
                + str(row.get("adapter_ref", ""))
                + ": boundary_strength="
                + str(row.get("boundary_strength", ""))
                + "; credential_path_class="
                + str(row.get("credential_path_class", ""))
                + "; observed_write_adapter="
                + ("yes" if row.get("observed_write_adapter") else "no")
            )
    lines.append("proof_limits: diagnosis record only; no source truth, success, quality, or Movement authority")
    return "\n".join(lines)


def _status_packet(args: argparse.Namespace) -> dict[str, Any]:
    repo = _repo_from_args(args)
    builds_root = _default_builds_root()
    return {
        "command": "status",
        "repo_root": str(repo),
        "cwd": str(Path.cwd().resolve()),
        "entrypoint_file": str(Path(__file__).resolve()),
        "python_executable": sys.executable,
        "brick_home": str(builds_root.parents[2]),
        "brick_home_basis": "BRICK_HOME or ~/.brick through the capture seam",
        "default_builds_root": str(builds_root),
        "default_evidence_root": str(builds_root),
        "default_build_root_basis": (
            "same ref-less Building evidence root used by brick build when --output-root is omitted"
        ),
        "default_builds_root_exists": builds_root.exists(),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
        "adapter_boundary_matrix": _adapter_boundary_packet(),
        **_support_observation_packet(),
    }


def _render_status(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Brick status support evidence",
            f"repo_root: {packet['repo_root']}",
            f"cwd: {packet['cwd']}",
            f"entrypoint_file: {packet['entrypoint_file']}",
            f"python_executable: {packet['python_executable']}",
            f"brick_home: {packet['brick_home']}",
            f"brick_home_basis: {packet['brick_home_basis']}",
            f"default_evidence_root: {packet['default_evidence_root']}",
            f"default_builds_root: {packet['default_builds_root']}",
            f"default_build_root_basis: {packet['default_build_root_basis']}",
            f"default_builds_root_exists: {packet['default_builds_root_exists']}",
            "adapter_boundary_matrix_rows: "
            + str(len(packet.get("adapter_boundary_matrix", {}).get("rows", []))),
            "proof_limits: " + "; ".join(packet["proof_limits"]),
            "not_proven: " + "; ".join(packet["not_proven"]),
        ]
    )


def _cmd_doctor(args: argparse.Namespace) -> int:
    packet = onboard.run_doctor()
    packet["adapter_boundary_matrix"] = _adapter_boundary_packet()
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_doctor(packet))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    packet = _status_packet(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_status(packet))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    # build-unify #12 D4 (표16 repo_root + 표17 casting): emit the resolved
    # repo_root and its drift warnings as the FIRST launch output line, BEFORE the
    # walk runs, so a launch bound to a stale/second checkout is visible before any
    # lane cost is spent (the 표16 postmortem: 3 launches walked a 2-day-old tree).
    # In --json mode this pre-walk line goes to STDERR so the stdout JSON contract
    # stays a single object; the same observation is also embedded in the packet.
    # A repo_root that is behind its upstream is REFUSED unless --allow-stale-repo
    # is passed. The resolved-casting table rides the rendered packet
    # (materialized_step_adapters) below.
    repo = _repo_from_args(args)
    repo_observation = _resolved_repo_root_observation(repo)
    stale_refused = _emit_launch_repo_root_observation(args, repo_observation)
    if stale_refused is not None:
        return stale_refused
    packet = _run_build(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_build(packet))
    return 0


def _default_drafts_root() -> Path:
    """Return the ``<brick_home>/drafts`` root for drafted graph-decls.

    Drafts NEVER default inside the repo tree (0706 path-shape defect): the
    build evidence root is ``<brick_home>/project/brick-protocol/buildings``, so
    ``parents[2]`` climbs back to ``<brick_home>`` and lands drafts beside it.
    """

    return _default_builds_root().parents[2] / "drafts"


def _draft_task_text(args: argparse.Namespace) -> str:
    task = getattr(args, "task", "") or ""
    task_file = getattr(args, "task_file", "") or ""
    if task and task_file:
        raise ValueError("draft accepts only one of --task or --task-file")
    if task_file:
        return Path(task_file).expanduser().resolve().read_text(encoding="utf-8")
    if not task:
        raise ValueError("draft requires --task or --task-file")
    return task


def _draft_answers(args: argparse.Namespace) -> dict[str, Any]:
    raw = getattr(args, "answers", "") or ""
    answers_file = getattr(args, "answers_file", "") or ""
    if raw and answers_file:
        raise ValueError("draft accepts only one of --answers or --answers-file")
    if answers_file:
        raw = Path(answers_file).expanduser().resolve().read_text(encoding="utf-8")
    if not raw:
        raise ValueError("draft requires --answers or --answers-file (JSON object)")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("draft --answers must be a JSON object of the 8 sizing answers")
    return loaded


def _run_draft(args: argparse.Namespace) -> dict[str, Any]:
    # No launch seam is reachable from this path: it calls ONLY graph_draft
    # functions (draft_graph_declaration / write_draft_declaration). It never
    # references the sandbox-run or goal-approve launch entrypoints, and never
    # reuses the build launch helpers (Rule 3: 자동발사 금지).
    repo = _repo_from_args(args)
    task = _draft_task_text(args)
    answers = _draft_answers(args)
    result = draft_graph_declaration(
        task,
        answers,
        repo_root=repo,
        building_id=(getattr(args, "building_id", "") or None),
        allowed_paths=tuple(getattr(args, "allowed_path", []) or []),
        forbidden_paths=tuple(getattr(args, "forbidden_path", []) or []) or (".git/**",),
        source_facts=tuple(getattr(args, "source_fact", []) or []),
        declared_by=getattr(args, "declared_by", DEFAULT_DECLARED_BY),
    )
    building_id = result.declaration["building_id"]
    out = (
        Path(args.out).expanduser().resolve()
        if getattr(args, "out", "")
        else _default_drafts_root() / f"{building_id}-decl.json"
    )
    draft_path = write_draft_declaration(result, out)
    rationale_path = draft_path.with_name(draft_path.stem + "-rationale.md")
    launch_guidance = (
        "발사는 운영자 몫: 초안을 검토한 뒤 직접 실행하세요 → "
        f"brick build --graph-decl {draft_path} "
        "(선언 action 기본값 stop; 이 표면에는 자동발사 경로가 없습니다)"
    )
    packet: dict[str, Any] = {
        "command": "draft",
        "draft_path": str(draft_path),
        "rationale_path": str(rationale_path),
        "building_id": building_id,
        "composed_ok": bool(result.precheck.get("composed_ok")),
        "composed_literal": result.precheck.get("literal", ""),
        "precheck": dict(result.precheck),
        "rationale_rows": [dict(row) for row in result.rationale_rows],
        "sizing_answers": dict(result.sizing_answers),
        "launch_guidance": launch_guidance,
        "proof_limits": list(result.proof_limits),
        "not_proven": list(result.not_proven),
    }
    return packet


def _render_draft(packet: dict[str, Any]) -> str:
    lines = [
        "Brick draft support evidence",
        f"building_id: {packet['building_id']}",
        f"draft_path: {packet['draft_path']}",
        f"rationale_path: {packet['rationale_path']}",
        "composed_ok: " + ("yes" if packet.get("composed_ok") else "no"),
        f"composed_literal: {packet.get('composed_literal', '')}",
    ]
    if packet.get("precheck", {}).get("reject_evidence"):
        lines.append(f"reject_evidence: {packet['precheck']['reject_evidence']}")
    lines.append("rationale_rows:")
    for row in packet.get("rationale_rows", []):
        lines.append(
            f"- {row.get('rule_id', '')}: {row.get('decision', '')} "
            f"({row.get('basis', '')})"
        )
    lines.append(f"launch_guidance: {packet['launch_guidance']}")
    lines.append("proof_limits: " + "; ".join(packet["proof_limits"]))
    lines.append("not_proven: " + "; ".join(packet["not_proven"]))
    return "\n".join(lines)


def _cmd_draft(args: argparse.Namespace) -> int:
    # Non-interactive by construction (no input() anywhere on this path) and no
    # launch seam reachable. Exit nonzero when the in-memory precheck fails so
    # the operator sees the failing draft on disk and fixes it.
    packet = _run_draft(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_draft(packet))
    return 0 if packet["composed_ok"] else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    repo = _repo_from_args(args)
    if args.self_test:
        verify_argv = ["--self-test"]
    elif args.profile:
        verify_argv = ["--repo", str(repo), "--profile", args.profile]
    elif args.all:
        verify_argv = ["--repo", str(repo), "--all"]
    else:
        verify_argv = _hermetic_verify_argv(repo)
    if not args.json:
        return check_profile.main(verify_argv)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = check_profile.main(verify_argv)
    print(
        _json_dump(
            {
                "command": "verify",
                "repo_root": str(repo),
                "checker_argv": verify_argv,
                "checker_exit_code": exit_code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "proof_limits": list(PROOF_LIMITS),
                "not_proven": list(NOT_PROVEN),
            }
        )
    )
    return exit_code


def _cmd_resume(args: argparse.Namespace) -> int:
    repo = _repo_from_args(args)
    repo_observation = _resolved_repo_root_observation(repo)
    stale_refused = _emit_launch_repo_root_observation(args, repo_observation)
    if stale_refused is not None:
        return stale_refused
    try:
        decl = resume_declaration.load_resume_declaration(args.decl)
        packet = resume_declaration.run_resume_declaration(
            decl,
            repo_root=repo,
            dry_run=bool(args.dry_run),
        )
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        packet = {
            "command": "resume",
            "decl_path": str(args.decl),
            "error_kind": type(exc).__name__,
            "error_message": str(exc),
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
        if args.json:
            print(_json_dump(packet))
        else:
            print(_render_resume(packet))
        return 2
    except ValueError as exc:
        packet = {
            "command": "resume",
            "decl_path": str(args.decl),
            "error_kind": "resume_declaration_rejected",
            "error_message": str(exc),
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
        if args.json:
            print(_json_dump(packet))
        else:
            print(_render_resume(packet))
        if "not admitted for hold_reason" in str(exc):
            return 5
        return 2
    packet.update(_resolved_repo_root_observation(repo))
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_resume(packet))
    if packet.get("ok"):
        return 0
    if packet.get("error_kind") == "resume_declaration_dead_end":
        return 4
    if packet.get("error_kind") == "resume_declaration_no_match":
        return 4
    return 1


def _render_resume(packet: dict[str, Any]) -> str:
    lines = [
        "Brick resume declaration support evidence",
        f"building_ref: {packet.get('building_ref', '')}",
        f"chain: {packet.get('chain', '')}",
        f"dry_run: {'yes' if packet.get('dry_run') else 'no'}",
    ]
    preflight = packet.get("preflight")
    if isinstance(preflight, Mapping):
        lines.extend(
            [
                f"frontier_kind: {preflight.get('frontier_kind', '')}",
                f"frontier_reason: {preflight.get('frontier_reason', '')}",
                f"matched: {'yes' if preflight.get('matched') else 'no'}",
            ]
        )
        if preflight.get("warning"):
            lines.append(str(preflight["warning"]))
    rounds = packet.get("rounds")
    if isinstance(rounds, Sequence) and not isinstance(rounds, (str, bytes)):
        lines.append(f"rounds: {len(rounds)}")
    if packet.get("message_ko"):
        lines.append(str(packet["message_ko"]))
    if packet.get("next_command"):
        lines.append(str(packet["next_command"]))
    if packet.get("error_kind"):
        lines.append(f"error_kind: {packet.get('error_kind', '')}")
    if packet.get("error_message"):
        lines.append(f"error_message: {packet.get('error_message', '')}")
    if packet.get("proof_limits"):
        lines.append("proof_limits: " + "; ".join(str(item) for item in packet["proof_limits"]))
    if packet.get("not_proven"):
        lines.append("not_proven: " + "; ".join(str(item) for item in packet["not_proven"]))
    return "\n".join(lines)


def _cmd_init(args: argparse.Namespace) -> int:
    """One-shot install wizard: the ordered, idempotent, friendly-fallback flow.

    INSTALL-WIZARD-0623: converges the previously-thin init (doctor + example)
    with the richer onboard flow into ONE ordered sequence:

      1 PRESENT  -> doctor             (provider/gh readiness)
      2 PLUGIN   -> MCP register + skills place + recording hooks
      3 SLACK    -> provision/validate ~/.brick/report.env (0600)
      4+5 ONBOARD/EXAMPLE -> preflight + connect + example build + first-use
      6 VERIFY   -> hermetic check_profile core profile (fresh-machine
                    default); developers can run `brick verify --all`
                    explicitly for the full sweep.

    Each plugin/slack step is a friendly advisory that never hard-stops; only a
    failed example build is fatal (preserving the prior contract). The verify
    step runs LAST and is skipped when --skip-verify is passed.
    """

    repo = _repo_from_args(args)
    interactive_provider_intake = None
    selected_host = getattr(args, "host", "codex") or "codex"
    selected_model_ref = None
    if sys.stdin.isatty() and not bool(getattr(args, "non_interactive", False)):
        interactive_provider_intake = onboard.run_interactive_provider_intake(
            prompt_func=input,
            host_default=selected_host,
        )
        if interactive_provider_intake.get("skipped"):
            selected_host = "local"
        else:
            selected_host = str(interactive_provider_intake.get("host") or selected_host)
            selected_model_ref = str(interactive_provider_intake.get("model_ref") or "") or None
            onboard.run_interactive_gemini_key_intake(
                prompt_func=input,
                host=selected_host,
            )
    wizard = onboard.run_install_wizard(
        repo_root=repo,
        host=selected_host,
        output_root=args.output_root,
        allow_real_provider=True,
        run_example=not args.skip_build,
        wire_recording=not getattr(args, "skip_recording", False),
        register_mcp=not getattr(args, "skip_plugin", False),
        place_skills=not getattr(args, "skip_plugin", False),
        slack_bot_token=getattr(args, "slack_bot_token", None),
        slack_channel_id=getattr(args, "slack_channel_id", None),
        provider_model_ref=selected_model_ref,
    )

    doctor_packet = wizard["steps"].get("present")
    onboard_step = wizard["steps"].get("onboard", {})
    example_result = onboard_step.get("example_result", {}) if isinstance(onboard_step, dict) else {}

    # Re-derive the build_packet shape the existing first-use writer expects, from
    # the example_result the wizard recorded (the wizard runs the example through
    # run_onboard, not _run_build, so we synthesize the small packet first_use needs).
    build_packet = None
    build_error = None
    first_use_packet = None
    if not args.skip_build:
        if example_result.get("ok") and example_result.get("ran"):
            frontier_kind = str(example_result.get("frontier_kind") or "")
            build_packet = {
                "repo_root": str(repo),
                "output_root": str(args.output_root) if args.output_root else str(_default_builds_root()),
                "building_id": example_result.get("building_id", DEFAULT_EXAMPLE_BUILDING_ID),
                "adapter_ref": example_result.get("adapter_ref", ADAPTER_LOCAL),
                "chain_preset_ref": example_result.get("chain_preset_ref", DEFAULT_LOCAL_PRESET_REF),
                "isolation_mode": "wizard-onboard-example",
                "evidence_root": example_result.get("evidence_root", ""),
                "frontier_kind": frontier_kind,
                "customer_visible_frontier_state": _customer_visible_frontier_state(frontier_kind),
                "customer_visible_not_ready": frontier_kind != "complete",
                "customer_visible_frontier_message": _customer_visible_frontier_message(frontier_kind),
                "materialized_step_adapters": example_result.get("materialized_step_adapters", []),
                "proof_limits": list(PROOF_LIMITS),
                "not_proven": list(NOT_PROVEN),
            }
            try:
                first_use_packet = write_first_use(
                    build_packet["output_root"],
                    doctor_packet=doctor_packet,
                    build_packet=build_packet,
                )
            except Exception as exc:  # noqa: BLE001 -- init reports friendly evidence
                build_error = {"error_kind": type(exc).__name__, "error_message": str(exc)}
        else:
            build_error = {
                "error_kind": example_result.get("error_kind", "example_not_ok"),
                "error_message": example_result.get("error_message", "example build did not complete"),
            }

    # 6 VERIFY: hermetic default verify. Skipped on --skip-verify.
    verify_packet = None
    if not getattr(args, "skip_verify", False):
        verify_argv = _hermetic_verify_argv(repo)
        verify_stdout = io.StringIO()
        verify_stderr = io.StringIO()
        with contextlib.redirect_stdout(verify_stdout), contextlib.redirect_stderr(verify_stderr):
            verify_exit = check_profile.main(verify_argv)
        verify_packet = {
            "checker_argv": verify_argv,
            "checker_exit_code": verify_exit,
            "green": verify_exit == 0,
        }

    status_packet = _status_packet(args)
    packet = {
        "command": "init",
        "non_interactive": bool(args.non_interactive),
        "wizard": wizard,
        "doctor": doctor_packet,
        "build": build_packet,
        "build_error": build_error,
        "verify": verify_packet,
        "status": status_packet,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if interactive_provider_intake is not None:
        packet["interactive_provider_intake"] = interactive_provider_intake
    if first_use_packet is not None:
        packet["first_use"] = first_use_packet
    if args.json:
        print(_json_dump(packet))
    else:
        print("Brick init support evidence (install wizard)")
        if doctor_packet is not None:
            print(_render_doctor(doctor_packet))
        print("")
        print(_render_wizard_steps(wizard))
        if build_packet is not None:
            print("")
            print(_render_build(build_packet))
        if build_error is not None:
            print("")
            print(f"build_error: {build_error['error_kind']}: {build_error['error_message']}")
        if first_use_packet is not None:
            print("")
            print(f"next: read {FIRST_USE_FILENAME}")
            print(f"first_use_path: {first_use_packet['path']}")
        if verify_packet is not None:
            print("")
            print(f"verify: check_profile core green={verify_packet['green']} (exit {verify_packet['checker_exit_code']})")
        print("")
        print(_render_status(status_packet))
    # H3: the exit code reflects BOTH gates. The example build is the hard gate
    # (build_error => 1); when the VERIFY step ran, a RED hermetic profile ALSO
    # fails init. When verify was skipped (--skip-verify) it does not contribute
    # (verify_packet is None).
    if build_error is not None:
        return 1
    if verify_packet is not None and not verify_packet["green"]:
        return 1
    return 0


def _render_wizard_steps(wizard: dict[str, Any]) -> str:
    lines = ["install steps (ordered, idempotent):"]
    steps = wizard.get("steps", {})
    for key in ("provider_register", "mcp_register", "skills_place", "recording", "slack"):
        step = steps.get(key)
        if not isinstance(step, dict):
            continue
        mark = "ok" if step.get("ok", True) else "advisory"
        lines.append(f"- {key}: {mark}: {step.get('message_ko', '')}")
    return "\n".join(lines)


def _render_provider_add(result: dict[str, Any]) -> str:
    action = str(result.get("action") or "")
    adapter_ref = str(result.get("adapter_ref") or "")
    if action in {"registered", "refreshed"}:
        state = "registered+ready"
    elif action.startswith("skipped"):
        state = "registered+not-ready-yet"
    else:
        state = "failed" if not result.get("ok", True) else action or "observed"
    lines = [
        "Brick provider add support evidence",
        f"provider: {adapter_ref or 'unknown'}",
        f"state: {state}",
    ]
    if result.get("message_ko"):
        lines.append(f"message: {result['message_ko']}")
    return "\n".join(lines)


def _render_sink_add(sink_name: str, result: dict[str, Any]) -> str:
    ready_key = "slack_ready" if sink_name == "slack" else "dashboard_ready"
    configured_key = "slack_configured" if sink_name == "slack" else "dashboard_configured"
    if result.get(ready_key) is True:
        state = "registered+ready"
    elif result.get(configured_key) is True:
        state = "registered+not-ready-yet"
    elif str(result.get("action") or "").startswith("skipped"):
        state = "not-configured"
    else:
        state = "failed" if not result.get("ok", True) else str(result.get("action") or "observed")
    lines = [
        f"Brick sink add {sink_name} support evidence",
        f"sink: {sink_name}",
        f"state: {state}",
    ]
    if result.get("message_ko"):
        lines.append(f"message: {result['message_ko']}")
    return "\n".join(lines)


def _cmd_provider_add(args: argparse.Namespace) -> int:
    result = onboard.run_provider_register_step(args.host)
    if args.json:
        print(
            _json_dump(
                {
                    "command": "provider-add",
                    "host": args.host,
                    "result": result,
                    "proof_limits": list(PROOF_LIMITS),
                    "not_proven": list(NOT_PROVEN),
                }
            )
        )
    else:
        print(_render_provider_add(result))
        print(f"proof_limits: {', '.join(PROOF_LIMITS)}")
    return 0 if result.get("ok", True) else 1


def _cmd_sink_add(args: argparse.Namespace) -> int:
    sink_name = str(args.sink_name)
    if sink_name == "slack":
        result = onboard.run_slack_provision_step(
            slack_bot_token=getattr(args, "slack_bot_token", None),
            slack_channel_id=getattr(args, "slack_channel_id", None),
        )
    elif sink_name == "dashboard":
        result = onboard.run_dashboard_provision_step(
            dashboard_ingest_url=getattr(args, "dashboard_ingest_url", None),
            dashboard_secret=getattr(args, "dashboard_secret", None),
            dashboard_sa_key_path=getattr(args, "dashboard_sa_key_path", None),
        )
    else:
        result = {
            "ok": False,
            "action": "unsupported_sink",
            "message_ko": "지원하지 않는 sink예요.",
        }
    if args.json:
        print(
            _json_dump(
                {
                    "command": "sink-add",
                    "sink": sink_name,
                    "result": result,
                    "proof_limits": list(PROOF_LIMITS),
                    "not_proven": list(NOT_PROVEN),
                }
            )
        )
    else:
        print(_render_sink_add(sink_name, result))
        print(f"proof_limits: {', '.join(PROOF_LIMITS)}")
    return 0 if result.get("ok", True) else 1


def _cmd_auth_login(args: argparse.Namespace) -> int:
    # Guided readiness funnel. This NEVER enters credentials -- it observes
    # provider readiness (doctor) and prints per-provider login guidance so the
    # customer runs the provider-native login themselves.
    doctor_packet = onboard.run_doctor()
    guidance = [
        "codex  -> codex login",
        "claude -> claude  (실행 후 안내에 따라 로그인 / run it, then follow the prompt)",
        "gemini -> gemini  (또는 GEMINI_API_KEY 설정 / or set GEMINI_API_KEY)",
        "local  -> 설치/로그인 불필요 / no install or login needed",
    ]
    next_step = 'brick build --task "..." --real-provider'
    if args.json:
        print(
            _json_dump(
                {
                    "command": "auth-login",
                    "doctor": doctor_packet,
                    "login_guidance": guidance,
                    "next": next_step,
                    "proof_limits": list(PROOF_LIMITS),
                    "not_proven": list(NOT_PROVEN),
                }
            )
        )
        return 0
    print("Brick auth login support evidence")
    print(_render_doctor(doctor_packet))
    print("")
    print("로그인 안내 / Login guidance:")
    for line in guidance:
        print(f"  {line}")
    print("")
    print(f"준비되면 / When ready:  {next_step}")
    print(f"proof_limits: {', '.join(PROOF_LIMITS)}")
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit JSON support evidence.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for input; current P1 commands never prompt.",
    )
    parser.add_argument("--repo", default=None, help="Repo root override.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brick",
        description="Brick Protocol support CLI entrypoint.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="One-shot install wizard: doctor + plugin (MCP/skills/hooks) + slack + example + verify.",
        allow_abbrev=False,
    )
    _add_common(init_parser)
    init_parser.add_argument("--skip-build", action="store_true", help="Skip the local example build.")
    init_parser.add_argument(
        "--skip-plugin",
        action="store_true",
        help=(
            "Skip MCP register + skills placement. Default stays on because MCP "
            "serves the user's own interactive CLI sessions."
        ),
    )
    init_parser.add_argument("--skip-recording", action="store_true", help="Skip the auto-recording hook wiring.")
    init_parser.add_argument("--skip-verify", action="store_true", help="Skip the final hermetic verify.")
    init_parser.add_argument("--host", default="codex", help="Onboarding host (codex/claude/gemini/fugu/local).")
    init_parser.add_argument(
        "--slack-bot-token",
        dest="slack_bot_token",
        default=None,
        help="Slack bot token to provision into ~/.brick/report.env (0600). Optional.",
    )
    init_parser.add_argument(
        "--slack-channel-id",
        dest="slack_channel_id",
        default=None,
        help="Slack channel id to provision into ~/.brick/report.env (0600). Optional.",
    )
    init_parser.add_argument("--output-root", default=None, help="Evidence output root.")
    init_parser.add_argument("--timeout", type=int, default=120, help="Adapter timeout seconds.")
    init_parser.set_defaults(func=_cmd_init)

    build = subparsers.add_parser(
        "build",
        help="Run a declared Building through the existing driver seam.",
        allow_abbrev=False,
    )
    _add_common(build)
    build.add_argument("--task", default="", help="Inline task statement. Omit for the bundled example.")
    build.add_argument(
        "--task-source-ref",
        default=DEFAULT_EXAMPLE_TASK_SOURCE_REF,
        help="Repo-relative task source for the bundled/file-flow build.",
    )
    build.add_argument(
        "--preset",
        default="",
        help=(
            "Declared chain preset ref. Defaults to the local onboarding graph for "
            "stub/example runs, or fast-fix for write-capable task runs."
        ),
    )
    build.add_argument("--adapter", default="", help="Declared adapter ref.")
    build.add_argument(
        "--real-provider",
        action="store_true",
        help=(
            "Use the first ready provider-backed observed-write adapter instead of "
            "the local example stub. Explicit --adapter still wins; no ready provider "
            "falls back to adapter:local. Run `brick auth login` to inspect readiness."
        ),
    )
    build.add_argument("--building-id", default="", help="Optional explicit Building id.")
    build.add_argument(
        "--allow-stale-repo",
        action="store_true",
        help=(
            "Allow launching when the resolved repo_root HEAD is behind its upstream. "
            "Default refuses (표16: stale-tree launches walk the wrong checkout)."
        ),
    )
    build.add_argument(
        "--graph-decl",
        default="",
        help=(
            "JSON/YAML assemble-argument graph declaration file; rejects raw graph packet keys. "
            "Declaration action defaults to stop, which writes only work/proposed-building-graph.json; "
            "set action=forward to run the declared Building."
        ),
    )
    build.add_argument("--declared-by", default=DEFAULT_DECLARED_BY, help="Caller/COO declaration ref.")
    build.add_argument("--output-root", default=None, help="Evidence output root.")
    build.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Allow overwriting an existing Building evidence root.",
    )
    build.add_argument("--timeout", type=int, default=120, help="Adapter timeout seconds.")
    build.set_defaults(func=_cmd_build)

    draft = subparsers.add_parser(
        "draft",
        help=(
            "Draft a graph-decl candidate from a task + 8 sizing answers. "
            "Non-interactive; never launches (초안은 후보, 발사는 운영자 몫)."
        ),
        allow_abbrev=False,
    )
    _add_common(draft)
    draft.add_argument("--task", default="", help="Inline task statement.")
    draft.add_argument("--task-file", default="", help="Task statement file (xor --task).")
    draft.add_argument(
        "--answers",
        default="",
        help="JSON object with the 8 sizing answers (walker_adjacent/size/...).",
    )
    draft.add_argument("--answers-file", default="", help="Answers JSON file (xor --answers).")
    draft.add_argument("--building-id", default="", help="Optional explicit Building id.")
    draft.add_argument(
        "--out",
        default="",
        help="Draft decl path. Defaults under <brick_home>/drafts/ (never inside the repo).",
    )
    draft.add_argument("--allowed-path", action="append", default=[], help="write_scope allowed path (repeatable).")
    draft.add_argument(
        "--forbidden-path",
        action="append",
        default=[],
        help="write_scope forbidden path (repeatable; default ['.git/**']).",
    )
    draft.add_argument("--source-fact", action="append", default=[], help="Verified source fact path (repeatable).")
    draft.add_argument("--declared-by", default=DEFAULT_DECLARED_BY, help="Caller/COO declaration ref.")
    draft.set_defaults(func=_cmd_draft)

    resume = subparsers.add_parser(
        "resume",
        help="Lower a JSON hold-disposition declaration into the existing resume seam.",
        allow_abbrev=False,
    )
    _add_common(resume)
    resume.add_argument("--decl", required=True, help="JSON resume declaration file.")
    resume.add_argument("--dry-run", action="store_true", help="Validate + preflight only.")
    resume.add_argument(
        "--allow-stale-repo",
        action="store_true",
        help=(
            "Allow launching when the resolved repo_root HEAD is behind its upstream. "
            "Default refuses before resume lowering."
        ),
    )
    resume.set_defaults(func=_cmd_resume)

    verify = subparsers.add_parser(
        "verify",
        aliases=["check"],
        help="Run check_profile over this checkout.",
        allow_abbrev=False,
    )
    _add_common(verify)
    verify.add_argument("--profile", default="", help="Profile name or YAML path. Defaults to the hermetic core profile.")
    verify.add_argument("--all", action="store_true", help="Run every support/checkers/profiles/*.yaml profile.")
    verify.add_argument("--self-test", action="store_true", help="Run the profile runner self-test.")
    verify.set_defaults(func=_cmd_verify)

    doctor = subparsers.add_parser("doctor", help="Run the existing onboard doctor.", allow_abbrev=False)
    _add_common(doctor)
    doctor.set_defaults(func=_cmd_doctor)

    status = subparsers.add_parser("status", help="Print local support status evidence.", allow_abbrev=False)
    _add_common(status)
    status.set_defaults(func=_cmd_status)

    auth = subparsers.add_parser("auth", help="Provider auth readiness + login guidance.", allow_abbrev=False)
    _add_common(auth)
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_login = auth_sub.add_parser(
        "login",
        help="Show provider login guidance and readiness.",
        allow_abbrev=False,
    )
    _add_common(auth_login)
    auth_login.set_defaults(func=_cmd_auth_login)
    auth.set_defaults(func=_cmd_auth_login)

    provider = subparsers.add_parser("provider", help="Provider registration commands.", allow_abbrev=False)
    _add_common(provider)
    provider_sub = provider.add_subparsers(dest="provider_command")
    provider_add = provider_sub.add_parser(
        "add",
        help="Register one ready provider host.",
        allow_abbrev=False,
    )
    _add_common(provider_add)
    provider_add.add_argument("host", choices=onboard.SUPPORTED_HOSTS, help="Provider host to register.")
    provider_add.set_defaults(func=_cmd_provider_add)

    sink = subparsers.add_parser("sink", help="Report sink registration commands.", allow_abbrev=False)
    _add_common(sink)
    sink_sub = sink.add_subparsers(dest="sink_command")
    sink_add = sink_sub.add_parser(
        "add",
        help="Register or validate one report sink.",
        allow_abbrev=False,
    )
    _add_common(sink_add)
    sink_add.add_argument("sink_name", choices=("slack", "dashboard"), help="Sink to register.")
    sink_add.add_argument("--slack-bot-token", dest="slack_bot_token", default=None)
    sink_add.add_argument("--slack-channel-id", dest="slack_channel_id", default=None)
    sink_add.add_argument("--dashboard-ingest-url", dest="dashboard_ingest_url", default=None)
    sink_add.add_argument("--dashboard-secret", dest="dashboard_secret", default=None)
    sink_add.add_argument("--dashboard-sa-key-path", dest="dashboard_sa_key_path", default=None)
    sink_add.set_defaults(func=_cmd_sink_add)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        args_list = ["status"]
    elif args_list[0].startswith("-") and args_list[0] not in ("-h", "--help"):
        args_list = ["status", *args_list]
    parser = build_parser()
    args = parser.parse_args(args_list)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 -- CLI should report, not traceback
        packet = _public_error_packet(args, exc)
        if getattr(args, "json", False):
            print(_json_dump(packet), file=sys.stderr)
        else:
            print(
                "brick command rejected evidence: "
                f"{packet['public_error_code']}: {packet['public_error_message']}",
                file=sys.stderr,
            )
            print("proof_limits: " + "; ".join(PROOF_LIMITS), file=sys.stderr)
        return 1


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
