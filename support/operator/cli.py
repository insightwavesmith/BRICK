"""Customer-facing Brick CLI support entrypoint.

This is a support wrapper over existing operator/checker seams. It bootstraps
the checkout import identity before importing repo-local support modules so the
console script works from outside the repo with PYTHONPATH unset.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_IMPORT_IDENTITY_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_IDENTITY_ROOT))

import argparse
import contextlib
import io
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from brick_protocol.brick.spec import derived_worktree_write_scope
from support.checkers import check_profile
from support.connection.adapter_constants import (
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
    ALLOWED_ADAPTER_REFS,
    MODEL_REF_CLAUDE_INHERIT,
    MODEL_REF_CODEX_DEFAULT,
    MODEL_REF_GEMINI_DEFAULT,
)
from support.connection.agent_adapter import adapter_is_write_capable
from support.connection.adapter_subprocess import preflight_provider
from support.operator.first_use import FIRST_USE_FILENAME, write_first_use
from support.operator import onboard
from support.operator.driver import (
    run_customer_building_in_sandbox,
    run_customer_graph_building_in_sandbox,
)


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
P3_EASY_LARGE_DEFAULT_DEV_LANES = 2
P3_EASY_LARGE_MIN_DEV_LANES = 2
P3_EASY_LARGE_MAX_DEV_LANES = 8
REAL_PROVIDER_MODEL_REFS = {
    ADAPTER_CLAUDE_LOCAL: MODEL_REF_CLAUDE_INHERIT,
    ADAPTER_CODEX_LOCAL: MODEL_REF_CODEX_DEFAULT,
    ADAPTER_GEMINI_LOCAL: MODEL_REF_GEMINI_DEFAULT,
}
REAL_TASK_STEP_TEMPLATE_REFS = (
    "building-step-template:work",
    "building-step-template:code-attack-qa",
    "building-step-template:closure",
)

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


def _json_dump(packet: Any) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def _repo_from_args(args: argparse.Namespace) -> Path:
    raw_repo = getattr(args, "repo", None)
    if raw_repo:
        return Path(raw_repo).resolve()
    return _REPO_ROOT


def _default_builds_root() -> Path:
    return Path.home() / ".brick" / "builds"


def _active_slack_buildings_root() -> Path:
    """Return this goal's active Slack-facing vessel root.

    This official CLI graph default is intentionally independent of provider
    subprocess HOME. It is support evidence routing only, not source truth.
    """

    return Path("/Users/smith/.brick/project/brick-protocol/buildings")


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


def _real_task_step_selection_overrides(adapter: str, preset: str) -> dict[str, dict[str, str]]:
    if preset != DEFAULT_REAL_TASK_PRESET_REF or adapter not in REAL_PROVIDER_MODEL_REFS:
        return {}
    return {
        step_template_ref: {
            "selected_adapter_ref": adapter,
            "selected_model_ref": REAL_PROVIDER_MODEL_REFS[adapter],
        }
        for step_template_ref in REAL_TASK_STEP_TEMPLATE_REFS
    }


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
        intent: dict[str, Any] = {
            "declared_by": args.declared_by,
            "task_statement": task,
            "chain_preset_ref": preset,
            "selected_adapter_ref": adapter,
            "building_id": building_id,
        }
        if readiness_choice:
            intent["adapter_choice_basis"] = readiness_choice["adapter_choice_basis"]
            intent["provider_readiness_observations"] = readiness_choice[
                "provider_readiness_observations"
            ]
        write_scope = _task_write_scope(adapter=adapter, task=task)
        if write_scope is not None:
            intent["write_scope"] = write_scope
        step_overrides = _real_task_step_selection_overrides(adapter, preset)
        if step_overrides:
            intent["step_selection_overrides"] = step_overrides
        return intent
    intent = {
        "declared_by": args.declared_by,
        "task_source_ref": args.task_source_ref,
        "chain_preset_ref": preset,
        "selected_adapter_ref": adapter,
        "building_id": args.building_id or DEFAULT_EXAMPLE_BUILDING_ID,
    }
    if readiness_choice:
        intent["adapter_choice_basis"] = readiness_choice["adapter_choice_basis"]
        intent["provider_readiness_observations"] = readiness_choice[
            "provider_readiness_observations"
        ]
    return intent


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


def _load_graph_packet(path: str) -> dict[str, Any]:
    packet_path = Path(path).expanduser().resolve()
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"could not read graph packet: {packet_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"graph packet is not valid JSON: {packet_path}: {exc}") from exc
    if not isinstance(packet, dict):
        raise ValueError("graph packet must be a JSON object")
    for key in ("task_statement", "declared_by", "building_id"):
        value = packet.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"graph packet requires non-empty {key}")
    nodes = packet.get("nodes")
    edges = packet.get("edges")
    if not isinstance(nodes, (list, dict)) or not nodes:
        raise ValueError("graph packet requires non-empty nodes list/object")
    if not isinstance(edges, list):
        raise ValueError("graph packet requires edges list")
    groups = packet.get("groups", ())
    if groups is not None and not isinstance(groups, list):
        raise ValueError("graph packet optional groups must be a list")
    graph_packet = dict(packet)
    if "selected_shape_ref" not in graph_packet and packet.get("selected_shape"):
        graph_packet["selected_shape_ref"] = str(packet["selected_shape"])
    if "transition_concern_adoption" not in graph_packet and packet.get("adoption"):
        graph_packet["transition_concern_adoption"] = str(packet["adoption"])
    graph_packet["_graph_packet_path"] = str(packet_path)
    return graph_packet


def _large_dev_lane_count(args: argparse.Namespace) -> int:
    raw = getattr(args, "dev_lanes", P3_EASY_LARGE_DEFAULT_DEV_LANES)
    try:
        count = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("--dev-lanes must be an integer from 2 through 8") from exc
    if count < P3_EASY_LARGE_MIN_DEV_LANES or count > P3_EASY_LARGE_MAX_DEV_LANES:
        raise ValueError("--dev-lanes must be an integer from 2 through 8")
    return count


def _p3_easy_large_node(
    node_id: str,
    step_template_ref: str,
    work_statement: str,
    *,
    adapter_ref: str | None = None,
    model_ref: str | None = None,
    write_scope: Mapping[str, Any] | None = None,
    requires_brick_write_scope: bool = False,
    required_return_shape: str = "",
    node_reroute_budget: int | None = None,
    completion_edge_ref: str = "",
    closure_transition_target_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "node_id": node_id,
        "step_ref": node_id,
        "step_template_ref": step_template_ref,
        "work_statement": work_statement,
    }
    if adapter_ref:
        node["selected_adapter_ref"] = adapter_ref
    if model_ref:
        node["selected_model_ref"] = model_ref
    if write_scope is not None:
        node["write_scope"] = dict(write_scope)
    if requires_brick_write_scope:
        node["requires_brick_write_scope"] = True
    if required_return_shape:
        node["required_return_shape"] = required_return_shape
    if node_reroute_budget is not None:
        node["node_reroute_budget"] = node_reroute_budget
    if completion_edge_ref:
        node["completion_edge_ref"] = completion_edge_ref
    if closure_transition_target_policy is not None:
        node["closure_transition_target_policy"] = dict(closure_transition_target_policy)
    return node


def _p3_easy_large_edge(edge_ref: str, source: str, target: str) -> dict[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source": source,
        "target": target,
        "movement": "forward",
    }


def _p3_easy_large_graph_packet(args: argparse.Namespace) -> dict[str, Any]:
    task = (getattr(args, "task", "") or "").strip()
    if not task:
        raise ValueError("--large requires --task")
    if getattr(args, "graph_packet", ""):
        raise ValueError("declare either --large or graph packet mode, not both")
    if (getattr(args, "task_source_ref", "") or "") != DEFAULT_EXAMPLE_TASK_SOURCE_REF:
        raise ValueError("--large accepts inline --task only, not --task-source-ref")
    if (getattr(args, "preset", "") or "").strip():
        raise ValueError("--large declares the P3 graph directly and does not accept --preset")
    adapter = (getattr(args, "adapter", "") or ADAPTER_CODEX_LOCAL).strip()
    if adapter not in ALLOWED_ADAPTER_REFS:
        raise ValueError(f"adapter_ref is not admitted for customer CLI: {adapter}")
    if not adapter_is_write_capable(adapter):
        raise ValueError("--large requires a write-capable adapter")

    building_id = args.building_id or _task_building_id()
    dev_lanes = _large_dev_lane_count(args)
    write_scope = derived_worktree_write_scope()
    lane_return = "observed_evidence, not_proven"

    prefix = building_id
    intake = f"{prefix}-task-intake"
    design = f"{prefix}-design"
    design_axis = f"{prefix}-design-axis-inspect"
    plan_confirm = f"{prefix}-closure-plan-confirmation"
    integration = f"{prefix}-integration-summary"
    final_code_qa = f"{prefix}-final-codex-code-qa"
    final_axis_qa = f"{prefix}-final-gemini-axis-evidence-qa"
    closure = f"{prefix}-codex-closure"
    final_fan_out_edges = [
        f"edge:{prefix}-integration-summary-to-final-codex-code-qa",
        f"edge:{prefix}-integration-summary-to-final-gemini-axis-evidence-qa",
    ]
    final_fan_in_edges = [
        f"edge:{prefix}-final-codex-code-qa-to-codex-closure",
        f"edge:{prefix}-final-gemini-axis-evidence-qa-to-codex-closure",
    ]

    nodes: list[dict[str, Any]] = [
        _p3_easy_large_node(
            intake,
            "building-step-template:inspect",
            f"Task intake for large P3 work: {task}",
            adapter_ref=ADAPTER_CODEX_LOCAL,
            model_ref=MODEL_REF_CODEX_DEFAULT,
        ),
        _p3_easy_large_node(
            design,
            "building-step-template:design",
            f"Design the large P3 work before implementation: {task}",
            adapter_ref=ADAPTER_CODEX_LOCAL,
            model_ref=MODEL_REF_CODEX_DEFAULT,
        ),
        _p3_easy_large_node(
            design_axis,
            "building-step-template:axis-attack-qa",
            "Inspect the design for Brick/Agent/Link boundaries before lane work.",
            adapter_ref=ADAPTER_GEMINI_LOCAL,
            model_ref=MODEL_REF_GEMINI_DEFAULT,
            write_scope=write_scope,
            requires_brick_write_scope=True,
            required_return_shape=lane_return,
        ),
        _p3_easy_large_node(
            plan_confirm,
            "building-step-template:closure",
            "Confirm the lane plan and carry open proof limits before parallel dev lanes.",
            adapter_ref=ADAPTER_CODEX_LOCAL,
            model_ref=MODEL_REF_CODEX_DEFAULT,
            completion_edge_ref=f"edge:{prefix}-plan-confirmation-to-dev-lane-1",
            node_reroute_budget=1,
        ),
    ]

    edges: list[dict[str, Any]] = [
        _p3_easy_large_edge(f"edge:{prefix}-task-intake-to-design", intake, design),
        _p3_easy_large_edge(f"edge:{prefix}-design-to-design-axis-inspect", design, design_axis),
        _p3_easy_large_edge(
            f"edge:{prefix}-design-axis-inspect-to-plan-confirmation",
            design_axis,
            plan_confirm,
        ),
    ]
    fan_out_edges: list[str] = []
    fan_in_edges: list[str] = []

    for lane in range(1, dev_lanes + 1):
        dev = f"{prefix}-dev-lane-{lane}"
        qa = f"{prefix}-dev-lane-{lane}-qa"
        dev_edge = f"edge:{prefix}-plan-confirmation-to-dev-lane-{lane}"
        qa_edge = f"edge:{prefix}-dev-lane-{lane}-to-qa"
        fan_in_edge = f"edge:{prefix}-dev-lane-{lane}-qa-to-integration-summary"
        nodes.extend(
            [
                _p3_easy_large_node(
                    dev,
                    "building-step-template:work",
                    f"Implement large P3 lane {lane} of {dev_lanes}: {task}",
                    adapter_ref=adapter,
                    model_ref=REAL_PROVIDER_MODEL_REFS.get(adapter, MODEL_REF_CODEX_DEFAULT),
                    write_scope=write_scope,
                    requires_brick_write_scope=True,
                    required_return_shape=lane_return,
                ),
                _p3_easy_large_node(
                    qa,
                    "building-step-template:code-attack-qa",
                    f"Run code/regression QA for large P3 lane {lane}.",
                    adapter_ref=ADAPTER_CODEX_LOCAL,
                    model_ref=MODEL_REF_CODEX_DEFAULT,
                    write_scope=write_scope,
                    requires_brick_write_scope=True,
                    required_return_shape=lane_return,
                ),
            ]
        )
        edges.extend(
            [
                _p3_easy_large_edge(dev_edge, plan_confirm, dev),
                _p3_easy_large_edge(qa_edge, dev, qa),
                _p3_easy_large_edge(fan_in_edge, qa, integration),
            ]
        )
        fan_out_edges.append(dev_edge)
        fan_in_edges.append(fan_in_edge)

    nodes.extend(
        [
            _p3_easy_large_node(
                integration,
                "building-step-template:closure",
                "Integrate parallel lane evidence and summarize remaining deltas.",
                adapter_ref=ADAPTER_CODEX_LOCAL,
                model_ref=MODEL_REF_CODEX_DEFAULT,
                completion_edge_ref=final_fan_out_edges[0],
                closure_transition_target_policy={
                    "implementation_gap": {"action": "target", "target_ref": plan_confirm},
                    "verification_gap": {"action": "hold"},
                },
            ),
            _p3_easy_large_node(
                final_code_qa,
                "building-step-template:code-attack-qa",
                "Final Codex code/regression QA over the integrated large P3 work.",
                adapter_ref=ADAPTER_CODEX_LOCAL,
                model_ref=MODEL_REF_CODEX_DEFAULT,
                write_scope=write_scope,
                requires_brick_write_scope=True,
                required_return_shape=lane_return,
            ),
            _p3_easy_large_node(
                final_axis_qa,
                "building-step-template:axis-attack-qa",
                "Final Gemini-local axis/evidence QA over the integrated large P3 work.",
                adapter_ref=ADAPTER_GEMINI_LOCAL,
                model_ref=MODEL_REF_GEMINI_DEFAULT,
                write_scope=write_scope,
                requires_brick_write_scope=True,
                required_return_shape=lane_return,
            ),
            _p3_easy_large_node(
                closure,
                "building-step-template:closure",
                "Codex closure synthesis for the large P3 Building.",
                adapter_ref=ADAPTER_CODEX_LOCAL,
                model_ref=MODEL_REF_CODEX_DEFAULT,
            ),
        ]
    )
    edges.extend(
        [
            _p3_easy_large_edge(final_fan_out_edges[0], integration, final_code_qa),
            _p3_easy_large_edge(final_fan_out_edges[1], integration, final_axis_qa),
            _p3_easy_large_edge(final_fan_in_edges[0], final_code_qa, closure),
            _p3_easy_large_edge(final_fan_in_edges[1], final_axis_qa, closure),
            _p3_easy_large_edge(f"edge:{prefix}-codex-closure-to-boundary", closure, f"building-boundary:{prefix}-closed"),
        ]
    )

    return {
        "task_statement": task,
        "declared_by": args.declared_by,
        "building_id": building_id,
        "nodes": nodes,
        "edges": edges,
        "groups": [
            {
                "group_id": f"group:{prefix}-dev-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": fan_out_edges,
            },
            {
                "group_id": f"group:{prefix}-dev-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": fan_in_edges,
            },
            {
                "group_id": f"group:{prefix}-final-qa-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": final_fan_out_edges,
            },
            {
                "group_id": f"group:{prefix}-final-qa-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": final_fan_in_edges,
            },
        ],
        "selected_adapter_ref": adapter,
        "selected_model_ref": REAL_PROVIDER_MODEL_REFS.get(adapter, MODEL_REF_CODEX_DEFAULT),
        "selected_shape_ref": "building-shape:design-needed",
        "transition_concern_adoption": "binding",
        "chain_preset_ref": "",
        "dev_lanes": dev_lanes,
    }


def _run_build(args: argparse.Namespace) -> dict[str, Any]:
    repo = _repo_from_args(args)
    graph_arg = (getattr(args, "graph_packet", "") or "").strip()
    large_mode = bool(getattr(args, "large", False))
    if large_mode:
        graph_packet = _p3_easy_large_graph_packet(args)
        output_root = (
            Path(args.output_root).expanduser().resolve()
            if args.output_root
            else _active_slack_buildings_root()
        )
        result = run_customer_graph_building_in_sandbox(
            graph_packet,
            customer_repo_root=repo,
            output_root=output_root,
            overwrite_existing=bool(args.overwrite_existing),
            adapter_timeout_seconds=args.timeout,
            proof_limits=PROOF_LIMITS,
        )
        intake = result.intake_result
        frontier_kind = result.frontier_kind
        packet: dict[str, Any] = {
            "command": "build",
            "build_input_mode": "p3_easy_large_graph",
            "repo_root": str(repo),
            "output_root": str(output_root),
            "building_id": result.building_id,
            "declared_by": graph_packet["declared_by"],
            "task_source_basis": "task_statement",
            "chain_preset_ref": "",
            "adapter_ref": str(graph_packet.get("selected_adapter_ref") or ""),
            "adapter_choice_basis": "large-graph-declared",
            "dev_lanes": graph_packet["dev_lanes"],
            "provider_readiness_observations": [],
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
    if graph_arg and ((getattr(args, "task", "") or "").strip() or getattr(args, "task_source_ref", "")):
        default_source = getattr(args, "task_source_ref", "") == DEFAULT_EXAMPLE_TASK_SOURCE_REF
        if (getattr(args, "task", "") or "").strip() or not default_source:
            raise ValueError("declare either graph packet mode or task/task-source mode, not both")
    if graph_arg:
        graph_packet = _load_graph_packet(graph_arg)
        output_root = (
            Path(args.output_root).expanduser().resolve()
            if args.output_root
            else _active_slack_buildings_root()
        )
        result = run_customer_graph_building_in_sandbox(
            graph_packet,
            customer_repo_root=repo,
            output_root=output_root,
            overwrite_existing=bool(args.overwrite_existing),
            adapter_timeout_seconds=args.timeout,
            proof_limits=PROOF_LIMITS,
        )
        intake = result.intake_result
        frontier_kind = result.frontier_kind
        packet: dict[str, Any] = {
            "command": "build",
            "build_input_mode": "graph_packet",
            "repo_root": str(repo),
            "output_root": str(output_root),
            "graph_packet_path": str(graph_packet["_graph_packet_path"]),
            "building_id": result.building_id,
            "declared_by": graph_packet["declared_by"],
            "task_source_basis": "task_statement",
            "chain_preset_ref": str(graph_packet.get("chain_preset_ref") or ""),
            "adapter_ref": str(graph_packet.get("selected_adapter_ref") or "adapter:local"),
            "adapter_choice_basis": "graph-packet-declared",
            "provider_readiness_observations": [],
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


def _render_build(packet: dict[str, Any]) -> str:
    lines = [
        "Brick build support evidence",
        f"build_input_mode: {packet.get('build_input_mode', 'preset_task')}",
        f"repo_root: {packet['repo_root']}",
        f"building_id: {packet['building_id']}",
        f"adapter_ref: {packet['adapter_ref']}",
        f"adapter_choice_basis: {packet.get('adapter_choice_basis', 'not recorded')}",
        f"chain_preset_ref: {packet['chain_preset_ref']}",
        f"isolation_mode: {packet['isolation_mode']}",
        f"evidence_root: {packet['evidence_root']}",
        f"frontier_kind: {packet['frontier_kind']}",
        f"customer_visible_frontier_state: {packet['customer_visible_frontier_state']}",
        "customer_visible_not_ready: "
        + ("yes" if packet.get("customer_visible_not_ready") else "no"),
        f"frontier_message: {packet['customer_visible_frontier_message']}",
    ]
    if packet.get("plan_path"):
        lines.append(f"plan_path: {packet['plan_path']}")
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
        "brick_home": str(Path.home() / ".brick"),
        "default_builds_root": str(builds_root),
        "default_builds_root_exists": builds_root.exists(),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
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
            f"default_builds_root: {packet['default_builds_root']}",
            f"default_builds_root_exists: {packet['default_builds_root_exists']}",
            "proof_limits: " + "; ".join(packet["proof_limits"]),
            "not_proven: " + "; ".join(packet["not_proven"]),
        ]
    )


def _cmd_doctor(args: argparse.Namespace) -> int:
    packet = onboard.run_doctor()
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
    packet = _run_build(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_build(packet))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    repo = _repo_from_args(args)
    if args.self_test:
        verify_argv = ["--self-test"]
    elif args.profile:
        verify_argv = ["--repo", str(repo), "--profile", args.profile]
    else:
        verify_argv = ["--repo", str(repo), "--all"]
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


def _cmd_init(args: argparse.Namespace) -> int:
    """One-shot install wizard: the ordered, idempotent, friendly-fallback flow.

    INSTALL-WIZARD-0623: converges the previously-thin init (doctor + example)
    with the richer onboard flow into ONE ordered sequence:

      1 PRESENT  -> doctor             (provider/gh readiness)
      2 PLUGIN   -> MCP register + skills place + recording hooks
      3 SLACK    -> provision/validate ~/.brick/report.env (0600)
      4+5 ONBOARD/EXAMPLE -> preflight + connect + example build + first-use
      6 VERIFY   -> check_profile --all ONCE (the CADENCE: per-step compileall,
                    --all once at the end)

    Each plugin/slack step is a friendly advisory that never hard-stops; only a
    failed example build is fatal (preserving the prior contract). The verify
    step runs LAST and is skipped when --skip-verify is passed.
    """

    repo = _repo_from_args(args)
    wizard = onboard.run_install_wizard(
        repo_root=repo,
        host=getattr(args, "host", "codex") or "codex",
        output_root=args.output_root,
        allow_real_provider=False,
        run_example=not args.skip_build,
        wire_recording=not getattr(args, "skip_recording", False),
        register_mcp=not getattr(args, "skip_plugin", False),
        place_skills=not getattr(args, "skip_plugin", False),
        slack_bot_token=getattr(args, "slack_bot_token", None),
        slack_channel_id=getattr(args, "slack_channel_id", None),
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

    # 6 VERIFY: check_profile --all ONCE (CADENCE). Skipped on --skip-verify.
    verify_packet = None
    if not getattr(args, "skip_verify", False):
        verify_argv = ["--repo", str(repo), "--all"]
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
            print(f"verify: check_profile --all green={verify_packet['green']} (exit {verify_packet['checker_exit_code']})")
        print("")
        print(_render_status(status_packet))
    # H3: the exit code reflects BOTH gates. The example build is the hard gate
    # (build_error => 1); when the VERIFY step ran (--all was actually executed),
    # a RED suite ALSO fails init -- otherwise `brick init` would pay the full
    # --all cost and still exit 0 over a RED tree, a fake green. When verify was
    # skipped (--skip-verify) it does not contribute (verify_packet is None).
    if build_error is not None:
        return 1
    if verify_packet is not None and not verify_packet["green"]:
        return 1
    return 0


def _render_wizard_steps(wizard: dict[str, Any]) -> str:
    lines = ["install steps (ordered, idempotent):"]
    steps = wizard.get("steps", {})
    for key in ("mcp_register", "skills_place", "recording", "slack"):
        step = steps.get(key)
        if not isinstance(step, dict):
            continue
        mark = "ok" if step.get("ok", True) else "advisory"
        lines.append(f"- {key}: {mark}: {step.get('message_ko', '')}")
    return "\n".join(lines)


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
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="One-shot install wizard: doctor + plugin (MCP/skills/hooks) + slack + example + verify.",
    )
    _add_common(init_parser)
    init_parser.add_argument("--skip-build", action="store_true", help="Skip the local example build.")
    init_parser.add_argument("--skip-plugin", action="store_true", help="Skip MCP register + skills placement.")
    init_parser.add_argument("--skip-recording", action="store_true", help="Skip the auto-recording hook wiring.")
    init_parser.add_argument("--skip-verify", action="store_true", help="Skip the final check_profile --all verify.")
    init_parser.add_argument("--host", default="codex", help="Onboarding host (codex/claude/gemini/local).")
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

    build = subparsers.add_parser("build", help="Run a declared Building through the existing driver seam.")
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
    build.add_argument("--declared-by", default=DEFAULT_DECLARED_BY, help="Caller/COO declaration ref.")
    build.add_argument(
        "--large",
        action="store_true",
        help="Declare the P3 easy-large graph through the existing graph wrapper.",
    )
    build.add_argument(
        "--dev-lanes",
        type=int,
        default=P3_EASY_LARGE_DEFAULT_DEV_LANES,
        help="Parallel dev lane count for --large. Valid range: 2..8.",
    )
    build.add_argument(
        "--graph",
        "--graph-packet",
        dest="graph_packet",
        default="",
        help="Caller/COO-declared graph packet JSON path.",
    )
    build.add_argument("--output-root", default=None, help="Evidence output root.")
    build.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Allow overwriting an existing Building evidence root.",
    )
    build.add_argument("--timeout", type=int, default=120, help="Adapter timeout seconds.")
    build.set_defaults(func=_cmd_build)

    verify = subparsers.add_parser("verify", aliases=["check"], help="Run check_profile over this checkout.")
    _add_common(verify)
    verify.add_argument("--profile", default="", help="Profile name or YAML path. Defaults to --all.")
    verify.add_argument("--self-test", action="store_true", help="Run the profile runner self-test.")
    verify.set_defaults(func=_cmd_verify)

    doctor = subparsers.add_parser("doctor", help="Run the existing onboard doctor.")
    _add_common(doctor)
    doctor.set_defaults(func=_cmd_doctor)

    status = subparsers.add_parser("status", help="Print local support status evidence.")
    _add_common(status)
    status.set_defaults(func=_cmd_status)

    auth = subparsers.add_parser("auth", help="Provider auth readiness + login guidance.")
    _add_common(auth)
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_login = auth_sub.add_parser("login", help="Show provider login guidance and readiness.")
    _add_common(auth_login)
    auth_login.set_defaults(func=_cmd_auth_login)
    auth.set_defaults(func=_cmd_auth_login)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        args_list = ["status"]
    parser = build_parser()
    args = parser.parse_args(args_list)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 -- CLI should report, not traceback
        packet = {
            "command": getattr(args, "command", ""),
            "error_kind": type(exc).__name__,
            "error_message": str(exc),
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
        if getattr(args, "json", False):
            print(_json_dump(packet), file=sys.stderr)
        else:
            print(f"brick command rejected evidence: {type(exc).__name__}: {exc}", file=sys.stderr)
            print("proof_limits: " + "; ".join(PROOF_LIMITS), file=sys.stderr)
        return 1


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
