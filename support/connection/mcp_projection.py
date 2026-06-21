"""Read-only MCP-shaped projection over admitted support context.

MCP-PROJECTION-0 exposes already rendered Agent resource packets and the
BAR-v2 Building design context through a small JSON-RPC call door. It does not
call providers, execute hooks or tools, write files, store credentials, expand
AgentFact, create GateFacts, choose Movement, choose Building shape, or own
Agent / Brick meaning.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    _DIRECT_SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[2]
    # A real MCP host launches this file as a plain script with a clean env (no
    # PYTHONPATH). Put BOTH the repo root (for support.connection.* absolute
    # imports) AND support/import_identity (the shim that provides the
    # brick_protocol package those modules import) on sys.path, else the bare
    # launch crashes at import with ModuleNotFoundError: brick_protocol.
    for _direct_script_path in (
        _DIRECT_SCRIPT_REPO_ROOT,
        _DIRECT_SCRIPT_REPO_ROOT / "support" / "import_identity",
    ):
        if str(_direct_script_path) not in sys.path:
            sys.path.insert(0, str(_direct_script_path))

from support.connection.agent_resources import (
    AgentResourceError,
    list_agent_object_refs,
    render_agent_packet,
    render_agent_team_context,
    render_claude_projection_seed,
    render_codex_projection_seed,
)
from support.connection.building_design_toolkit import (
    BuildingDesignToolkitError,
    render_building_design_context,
)
from support.connection.coo_sync import render_agent_projection_sync_context


_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTOCOL_VERSION = "2025-06-18"
_SERVER_NAME = "brick-protocol-mcp-projection"
_SERVER_VERSION = "0.1.0"
_ALLOWED_TARGETS = frozenset({"codex", "claude"})
_AGENT_PACKET_TOOL = "brick_protocol_render_agent_packet"
_AGENT_TEAM_CONTEXT_TOOL = "brick_protocol_render_agent_team_context"
_AGENT_TEAM_CONTEXT_URI = "brick-protocol://agent/team/context"
_AGENT_PROJECTION_SYNC_CONTEXT_TOOL = "brick_protocol_render_agent_projection_sync_context"
_AGENT_PROJECTION_SYNC_CONTEXT_URI = "brick-protocol://agent/projection-sync/context"
_COO_PROJECTION_TOOL = "brick_protocol_render_coo_projection"
_BUILDING_DESIGN_CONTEXT_TOOL = "brick_protocol_render_building_design_context"
_COO_OPERATING_CHAIN_CONTEXT_TOOL = "brick_protocol_render_coo_operating_chain_context"
_COO_OPERATING_CHAIN_CONTEXT_URI = "brick-protocol://coo/operating-chain/context"
_STATIC_RESOURCE_SPECS = (
    {
        "uri": "brick-protocol://agent/coo/codex-projection",
        "name": "agent-object:coo Codex projection seed",
        "role": "coo",
        "kind": "codex-projection-seed",
        "description": "Read-only COO Codex projection seed; source remains agent/.",
    },
    {
        "uri": "brick-protocol://agent/coo/claude-projection",
        "name": "agent-object:coo Claude projection seed",
        "role": "coo",
        "kind": "claude-projection-seed",
        "description": "Read-only COO Claude projection seed; source remains agent/.",
    },
    {
        "uri": _AGENT_TEAM_CONTEXT_URI,
        "name": "Agent team context",
        "role": "coo",
        "kind": "agent-team-context",
        "description": "Read-only admitted Agent Object team context from agent/.",
    },
    {
        "uri": _AGENT_PROJECTION_SYNC_CONTEXT_URI,
        "name": "Agent projection sync context",
        "role": "coo",
        "kind": "agent-projection-sync-context",
        "description": "Read-only Agent source/projection sync-out and sync-in observation context.",
    },
    {
        "uri": "brick-protocol://building/design/context",
        "name": "BAR-v2 Building design context",
        "role": "coo",
        "kind": "building-design-context",
        "description": "Read-only task source, shape registry, and Human+AI design contract from brick/.",
    },
    {
        "uri": _COO_OPERATING_CHAIN_CONTEXT_URI,
        "name": "COO operating chain context",
        "role": "coo",
        "kind": "coo-operating-chain-context",
        "description": "Read-only COO task intake chain context; source remains brick/ and agent/.",
    },
)
_PROOF_LIMITS = (
    "support MCP-shaped projection evidence only",
    "Agent resource meaning remains owned by agent/",
    "Brick design meaning remains owned by brick/",
    "support/connection/agent_resources.py remains the admitted renderer",
    "support/connection/building_design_toolkit.py is read-only support context",
    "MCP vocabulary is a compatibility surface only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_NOT_PROVEN = (
    "Codex MCP installation behavior",
    "Claude MCP installation behavior",
    "external app reload behavior",
    "provider quality",
    "provider session behavior",
    "production MCP compliance",
    "external network transport",
    "native tool or hook execution",
    "future Building correctness",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)


class MCPProjectionError(ValueError):
    """Raised when an MCP projection request is outside admitted scope."""


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT


def _json_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _role_from_ref(ref: str) -> str:
    return ref.removeprefix("agent-object:")


def _resource_specs(repo: Path) -> tuple[dict[str, str], ...]:
    agent_packet_specs = tuple(
        {
            "uri": f"brick-protocol://agent/{_role_from_ref(ref)}/packet",
            "name": f"{ref} packet",
            "role": _role_from_ref(ref),
            "kind": "agent-resource-packet",
            "description": f"Read-only rendered {_role_from_ref(ref)} Agent resource packet from agent/.",
        }
        for ref in list_agent_object_refs(repo)
    )
    return agent_packet_specs + _STATIC_RESOURCE_SPECS


def _resource_specs_by_uri(repo: Path) -> dict[str, dict[str, str]]:
    return {
        str(spec["uri"]): {str(key): str(value) for key, value in spec.items()}
        for spec in _resource_specs(repo)
    }


def _metadata(spec: Mapping[str, str]) -> dict[str, Any]:
    return {
        "uri": spec["uri"],
        "name": spec["name"],
        "description": spec["description"],
        "mimeType": "application/json",
    }


def _read_payload_for_spec(spec: Mapping[str, str], repo: Path) -> dict[str, Any]:
    kind = spec["kind"]
    role = spec["role"]
    if kind == "agent-resource-packet":
        return render_agent_packet(role, repo_root=repo)
    if kind == "agent-team-context":
        return render_agent_team_context(repo_root=repo)
    if kind == "agent-projection-sync-context":
        return render_agent_projection_sync_context(repo_root=repo)
    if kind == "codex-projection-seed":
        return render_codex_projection_seed(role, repo_root=repo)
    if kind == "claude-projection-seed":
        return render_claude_projection_seed(role, repo_root=repo)
    if kind == "building-design-context":
        return render_building_design_context(repo_root=repo)
    if kind == "coo-operating-chain-context":
        return render_coo_operating_chain_context(repo_root=repo)
    raise MCPProjectionError(f"unsupported MCP projection resource kind: {kind}")


def _source_for_kind(kind: str) -> str:
    if kind in {
        "agent-resource-packet",
        "agent-team-context",
        "agent-projection-sync-context",
        "codex-projection-seed",
        "claude-projection-seed",
    }:
        return "agent/"
    if kind == "building-design-context":
        return "brick/"
    if kind == "coo-operating-chain-context":
        return "brick/ + agent/ + support/"
    raise MCPProjectionError(f"unsupported MCP projection resource kind: {kind}")


def _error_result(message: str, *, code: str = "invalid_request") -> dict[str, Any]:
    return {
        "isError": True,
        "content": [{"type": "text", "text": _json_text({"error": code, "message": message})}],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def mcp_projection_resources(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return read-only MCP resource metadata."""

    repo = _repo_root(repo_root)
    return {
        "resources": [_metadata(spec) for spec in _resource_specs(repo)],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def read_mcp_projection_resource(uri: str, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return one MCP resource content payload as JSON text."""

    if not isinstance(uri, str) or not uri:
        raise MCPProjectionError("resource uri must be a non-empty string")
    repo = _repo_root(repo_root)
    spec = _resource_specs_by_uri(repo).get(uri)
    if spec is None:
        raise MCPProjectionError(f"resource is not admitted for MCP-PROJECTION-0: {uri}")
    kind = str(spec["kind"])
    payload = {
        "kind": "mcp-projection-resource",
        "uri": uri,
        "source": _source_for_kind(kind),
        "projection": _read_payload_for_spec(spec, repo),
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }
    return {
        "contents": [{"uri": uri, "mimeType": "application/json", "text": _json_text(payload)}],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def mcp_projection_tools() -> dict[str, Any]:
    """Return read-only tool metadata for admitted Agent resource renders."""

    roles = sorted(_role_from_ref(ref) for ref in list_agent_object_refs(_DEFAULT_REPO_ROOT))
    return {
        "tools": [
            {
                "name": _AGENT_PACKET_TOOL,
                "description": "Render an admitted Agent Object packet from agent/ resources.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"role": {"type": "string", "enum": roles}},
                    "required": ["role"],
                    "additionalProperties": False,
                },
            },
            {
                "name": _AGENT_TEAM_CONTEXT_TOOL,
                "description": "Render admitted Agent Object team context from agent/ resources.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": _AGENT_PROJECTION_SYNC_CONTEXT_TOOL,
                "description": "Render Agent source/projection sync-out and sync-in observation context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": _COO_PROJECTION_TOOL,
                "description": "Render the admitted COO projection seed for Codex or Claude.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "enum": sorted(_ALLOWED_TARGETS)}},
                    "required": ["target"],
                    "additionalProperties": False,
                },
            },
            {
                "name": _BUILDING_DESIGN_CONTEXT_TOOL,
                "description": "Render read-only BAR-v2 Building design context from brick/.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": _COO_OPERATING_CHAIN_CONTEXT_TOOL,
                "description": "Render read-only COO operating chain context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        ],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_coo_operating_chain_context(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render generic read-only context for the COO task intake chain."""

    repo = _repo_root(repo_root)
    design_context = render_building_design_context(repo_root=repo)
    startup_surface_refs = [
        "brick_protocol.support.operator.run.run_building_plan",
        "brick_protocol.support.operator.driver.run_declared_portfolio",
        "brick_protocol.support.operator.composition_intent.render_declared_step_template_plan",
        "brick_protocol.support.operator.composition_compose.compose_building",
        "brick_protocol.support.operator.auto_repair_replay.run_declared_auto_repair_replay_case",
    ]
    return {
        "kind": "coo-operating-chain-context",
        "schema_version": "coo-operating-chain-0",
        "source": "brick/ + agent/ + support/",
        "coo_projection_skill": "brick-protocol-coo",
        "coo_agent_object_ref": "agent-object:coo",
        "task_intake_skill_ref": "skill:task_intake",
        "task_source_template_ref": "brick/templates/tasks/source-template.md",
        "active_task_source_evidence_ref": "project/brick-protocol/buildings/<building-id>/work/task.md",
        "shape_catalog_ref": "brick/templates/shapes/catalog.yaml",
        "shape_registry_ref": "brick/templates/shapes/catalog.yaml",
        "design_contract_ref": "brick/templates/building-design-contract.yaml",
        "operator_helper_ref": "support/operator/building_operation.py::coo_operating_chain_packet",
        "selection_rule": design_context.get("selection_rule", "caller_or_coo_declared_only"),
        "candidate_chain_presets": list(design_context.get("chain_presets", ())),
        "common_chain_presets": list(design_context.get("common_chain_presets", ())),
        "dogfood_chain_presets": list(design_context.get("dogfood_chain_presets", ())),
        "chain_preset_aliases": dict(design_context.get("chain_preset_aliases", {})),
        "chain_preset_binding_fields": [
            "chain_preset_ref",
            "canonical_chain_preset_ref",
            "compat_chain_preset_ref",
        ],
        "operating_chain_order": [
            "사용자 요청 해석",
            "task intake 질문",
            "task.md 후보",
            "task.md 확정",
            "catalog_scope 후보",
            "preset vs manual 후보",
            "route_family_case_analysis",
            "graph_movement_case_analysis",
            "fan_in_first_candidate",
            "startup path 후보",
        ],
        "route_ladder_candidate_fields": [
            "user_request_interpretation",
            "task_md_candidate",
            "task_md_confirmation_state",
            "candidate_catalog_scope",
            "preset_vs_manual_candidate",
            "preset_vs_manual_case_analysis",
            "route_family_candidate",
            "route_family_case_analysis",
            "graph_movement_case_analysis",
            "fan_in_first_candidate",
            "startup_path_candidate",
        ],
        "operating_chain_warnings": [
            "Claude master-sequence is support evidence only, not the center.",
            "Support, model output, checker output, and reporter output are evidence only.",
            "COO must not jump from task.md directly to run_building_plan.",
            "COO must separate candidates from declarations for shape, preset, graph, route family, and startup path.",
            "Slack is payload for dogfood, not the goal or success proof.",
            "fan-in-first means collect all declared QA bodies before closure synthesis.",
            "In hard fan-in QA cohorts, QA lanes return their own Brick fields without Link-facing transition_concern_evidence; closure-synthesis alone returns Link-facing transition_concern_evidence.",
            "partial QA reuse remains not_proven.",
        ],
        "startup_paths": [
            "AGENTS.md",
            "project/brick-protocol/PROGRESS.md",
            "brick/templates/tasks/source-template.md",
            "brick/templates/shapes/catalog.yaml",
            "brick/templates/presets/fast-fix.md",
            "brick/templates/presets/design-build-parallel.md",
            "brick/templates/presets/high-risk-change-inspected.md",
            "brick/templates/presets/governed-change-review.md",
            "brick/templates/presets/app-feature-basic.md",
            "brick/templates/presets/app-feature-inspected.md",
            "brick/templates/presets/docs-simple-review.md",
            "brick/templates/presets/portfolio-sequence.md",
            "brick/templates/presets/brick-protocol-constitution-change.md",
            "brick/templates/presets/brick-protocol-dashboard-dev-basic.md",
            "brick/templates/presets/brick-protocol-dashboard-dev-inspected.md",
            "brick/templates/presets/brick-protocol-engine-feature-hard.md",
            "brick/templates/presets/brick-protocol-portfolio-driver.md",
            "brick/templates/presets/brick-protocol-post-d-cleanup.md",
            "agent/skills/task_intake/SKILL.md",
            "support/operator/run.py",
        ],
        "startup_surface_refs": startup_surface_refs,
        "runner_surface_ref": startup_surface_refs[0],
        "mcp_resource_uri": _COO_OPERATING_CHAIN_CONTEXT_URI,
        "mcp_tool_name": _COO_OPERATING_CHAIN_CONTEXT_TOOL,
        "deep_intake_fields": [
            "Trigger Event",
            "User Context",
            "Desired Information / Outcome",
            "Current Workaround",
            "Pain Points",
            "Blocked Decisions",
            "Primary Signals",
            "Status Vocabulary",
            "Required Actions",
            "Forbidden Actions",
        ],
        "honest_report_contract_fields": [
            "observed_evidence",
            "made_changes",
            "blocked_or_missing_evidence",
            "open_questions",
            "not_proven",
            "remaining_delta",
            "review_needed",
            "transition_concern_evidence",
        ],
        "evidence_expectations": [
            "task_source_ref when declared by the Building Plan",
            "Building Plan ref",
            "Building evidence root",
            "step output refs",
            "raw refs",
            "claim_trace refs",
            "building-map projection",
            "closure parent delta",
        ],
        "forbidden_authority": [
            "task-authored reroute",
            "Agent route target choice",
            "MCP-authored shape",
            "MCP-authored plan",
            "runner-authored plan",
            "support-chosen Movement",
            "source truth",
            "success judgment",
            "quality judgment",
            "Movement authority",
        ],
        "proof_limits": [
            "MCP COO chain context is support projection only",
            "Brick task meaning remains owned by brick/",
            "Agent resources remain owned by agent/",
            "COO declaration is required for active shape and active plan",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic fitness of future task sources",
            "semantic fitness of selected shapes",
            "future Building Plan correctness",
            "future Agent or provider quality",
            "future reviewer Movement decision correctness",
        ],
    }


def call_mcp_projection_tool(
    name: str,
    arguments: Mapping[str, Any] | None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Call an admitted read-only MCP projection tool."""

    repo = _repo_root(repo_root)
    args = dict(arguments or {})
    try:
        if name == _AGENT_PACKET_TOOL:
            role = args.get("role")
            payload = render_agent_packet(str(role), repo_root=repo)
        elif name == _AGENT_TEAM_CONTEXT_TOOL:
            if args:
                raise MCPProjectionError("Agent team context tool takes no arguments")
            payload = render_agent_team_context(repo_root=repo)
        elif name == _AGENT_PROJECTION_SYNC_CONTEXT_TOOL:
            if args:
                raise MCPProjectionError("Agent projection sync context tool takes no arguments")
            payload = render_agent_projection_sync_context(repo_root=repo)
        elif name == _COO_PROJECTION_TOOL:
            target = args.get("target")
            if target == "codex":
                payload = render_codex_projection_seed("coo", repo_root=repo)
            elif target == "claude":
                payload = render_claude_projection_seed("coo", repo_root=repo)
            else:
                raise MCPProjectionError("target must be one of: codex, claude")
        elif name == _BUILDING_DESIGN_CONTEXT_TOOL:
            if args:
                raise MCPProjectionError("building design context tool takes no arguments")
            payload = render_building_design_context(repo_root=repo)
        elif name == _COO_OPERATING_CHAIN_CONTEXT_TOOL:
            if args:
                raise MCPProjectionError("COO operating chain context tool takes no arguments")
            payload = render_coo_operating_chain_context(repo_root=repo)
        else:
            return _error_result(f"tool is not admitted for MCP-PROJECTION-0: {name}", code="unknown_tool")
    except (AgentResourceError, BuildingDesignToolkitError, MCPProjectionError) as exc:
        return _error_result(str(exc), code="invalid_arguments")

    return {
        "isError": False,
        "content": [{"type": "text", "text": _json_text(payload)}],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def _jsonrpc_result(message_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": dict(result)}


def _jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": _PROTOCOL_VERSION,
        "capabilities": {"resources": {}, "tools": {}},
        "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
        "instructions": (
            "Brick Protocol MCP projection is read-only support evidence. "
            "Agent meaning remains in agent/. Link owns Movement."
        ),
    }


def handle_mcp_message(message: Mapping[str, Any], repo_root: str | Path | None = None) -> dict[str, Any] | None:
    """Handle one JSON-RPC MCP-shaped request or notification."""

    if not isinstance(message, Mapping):
        return _jsonrpc_error(None, -32600, "message must be a JSON object")
    method = message.get("method")
    message_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if not isinstance(method, str):
        return _jsonrpc_error(message_id, -32600, "method must be a string")

    try:
        if method == "initialize":
            return _jsonrpc_result(message_id, _initialize_result())
        if method == "resources/list":
            return _jsonrpc_result(message_id, mcp_projection_resources(repo_root=repo_root))
        if method == "resources/read":
            params = message.get("params")
            if not isinstance(params, Mapping):
                return _jsonrpc_error(message_id, -32602, "resources/read params must be an object")
            uri = params.get("uri")
            return _jsonrpc_result(message_id, read_mcp_projection_resource(str(uri), repo_root=repo_root))
        if method == "tools/list":
            return _jsonrpc_result(message_id, mcp_projection_tools())
        if method == "tools/call":
            params = message.get("params")
            if not isinstance(params, Mapping):
                return _jsonrpc_error(message_id, -32602, "tools/call params must be an object")
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str):
                return _jsonrpc_error(message_id, -32602, "tools/call name must be a string")
            if not isinstance(arguments, Mapping):
                return _jsonrpc_error(message_id, -32602, "tools/call arguments must be an object")
            result = call_mcp_projection_tool(name, arguments, repo_root=repo_root)
            return _jsonrpc_result(message_id, result)
    except MCPProjectionError as exc:
        return _jsonrpc_error(message_id, -32602, str(exc))
    except (AgentResourceError, BuildingDesignToolkitError) as exc:
        return _jsonrpc_error(message_id, -32602, str(exc))
    return _jsonrpc_error(message_id, -32601, f"method is not admitted: {method}")


def serve_stdio(
    repo_root: str | Path | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Serve newline-delimited JSON-RPC messages over stdio."""

    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    for line in input_stream:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            message = json.loads(stripped)
            response = handle_mcp_message(message, repo_root=repo_root)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_error(None, -32700, f"parse error: {exc}")
        if response is None:
            continue
        output_stream.write(_json_text(response) + "\n")
        output_stream.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(_DEFAULT_REPO_ROOT))
    args = parser.parse_args()
    serve_stdio(repo_root=args.repo)
    return 0


__all__ = [
    "MCPProjectionError",
    "mcp_projection_resources",
    "read_mcp_projection_resource",
    "mcp_projection_tools",
    "call_mcp_projection_tool",
    "_BUILDING_DESIGN_CONTEXT_TOOL",
    "_COO_OPERATING_CHAIN_CONTEXT_TOOL",
    "_AGENT_PROJECTION_SYNC_CONTEXT_TOOL",
    "render_coo_operating_chain_context",
    "handle_mcp_message",
    "serve_stdio",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
