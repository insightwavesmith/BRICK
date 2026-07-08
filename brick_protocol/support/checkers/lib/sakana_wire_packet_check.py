"""Sakana wire packet resource-path redaction check.

Support checker mechanics only: fixture/in-process prompt rendering; no live
provider call, no source truth, no success/quality judgment, no Movement
authority.
"""

from __future__ import annotations

import copy
import importlib
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


_RESOURCE_ROW_LIST_KEYS = (
    "prompt_resources",
    "skill_resources",
    "discipline_resources",
    "charter_resources",
    "skill_manifest_refs",
    "tool_policy_resources",
)


def _path_labels(packet: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for key in _RESOURCE_ROW_LIST_KEYS:
        rows = packet.get(key)
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if isinstance(row, Mapping) and "path" in row:
                labels.append(f"{key}[{index}].path")
    hooks = packet.get("hook_resources")
    if isinstance(hooks, Mapping):
        for key in ("registry_path", "bindings_path"):
            if key in hooks:
                labels.append(f"hook_resources.{key}")
    return labels


def _prompt_payload(adapter: Any, grant_policy: Any, request: Any, *, spec: Any | None = None) -> dict[str, Any]:
    if spec is None:
        spec = adapter._LOCAL_CLI_SPECS[request.adapter_ref]
    return json.loads(grant_policy._build_prompt(request, spec))


def _instruction_request(adapter: Any, constants: Any, adapter_ref: str, packet: Mapping[str, Any]) -> Any:
    return adapter.AgentAdapterRequest(
        building_id="sakana-wire-packet-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_ref,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(constants.READ_WRITE_TOOL_POLICY_REF,),
        required_return_shape="made_changes,observed_evidence,blocked_or_missing_evidence,not_proven",
        agent_instruction_packet=packet,
    )


def _assert_sakana_wire_has_no_resource_paths(payload: Mapping[str, Any], *, label: str) -> None:
    packet = payload.get("agent_instruction_packet")
    if not isinstance(packet, Mapping):
        raise ProfileError(f"{label}: prompt omitted agent_instruction_packet")
    path_labels = _path_labels(packet)
    if path_labels:
        raise ProfileError(f"{label}: sakana wire packet exposed resource path labels: {path_labels}")


def _assert_ref_rows_survive(payload: Mapping[str, Any]) -> None:
    packet = payload["agent_instruction_packet"]
    for key in ("prompt_resources", "discipline_resources", "skill_resources"):
        rows = packet.get(key)
        if not isinstance(rows, list) or not rows:
            raise ProfileError(f"sakana wire packet lost non-empty {key}")
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping) or not row.get("ref"):
                raise ProfileError(f"sakana wire packet {key}[{index}] lost opaque ref")
    if not packet["prompt_resources"][0].get("body"):
        raise ProfileError("sakana wire packet lost inline prompt body")


def run_sakana_wire_packet(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")

    local_packet = resources.render_agent_instruction_packet("dev", repo_root=repo)
    local_paths = _path_labels(local_packet)
    if not local_paths:
        raise ProfileError("local evidence packet must preserve resource ref->path mappings")
    codex_payload = _prompt_payload(
        adapter,
        grant_policy,
        _instruction_request(adapter, constants, constants.ADAPTER_CODEX_LOCAL, local_packet),
    )
    codex_packet = codex_payload.get("agent_instruction_packet")
    if not isinstance(codex_packet, Mapping):
        raise ProfileError("non-sakana codex-local prompt packet omitted agent_instruction_packet")
    if _path_labels(codex_packet) != local_paths:
        raise ProfileError("non-sakana codex-local prompt packet did not preserve resource path labels")

    sakana_payload = _prompt_payload(
        adapter,
        grant_policy,
        _instruction_request(adapter, constants, constants.ADAPTER_CODEX_FUGU_LOCAL, local_packet),
    )
    _assert_sakana_wire_has_no_resource_paths(sakana_payload, label="green")
    _assert_ref_rows_survive(sakana_payload)
    if _path_labels(local_packet) != local_paths:
        raise ProfileError("sakana wire shaping mutated the local evidence packet")

    fugu_request = _instruction_request(
        adapter,
        constants,
        constants.ADAPTER_CODEX_FUGU_LOCAL,
        local_packet,
    )
    fugu_spec_without_wire_flag = replace(
        adapter._LOCAL_CLI_SPECS[constants.ADAPTER_CODEX_FUGU_LOCAL],
        opaque_resource_paths_on_wire=False,
    )
    fugu_without_wire_flag_payload = _prompt_payload(
        adapter,
        grant_policy,
        fugu_request,
        spec=fugu_spec_without_wire_flag,
    )
    fugu_without_wire_flag_packet = fugu_without_wire_flag_payload.get("agent_instruction_packet")
    if not isinstance(fugu_without_wire_flag_packet, Mapping):
        raise ProfileError("spec-flag negative control omitted agent_instruction_packet")
    if _path_labels(fugu_without_wire_flag_packet) != local_paths:
        raise ProfileError(
            "spec-flag negative control failed: codex-fugu-local adapter_ref alone removed resource path labels"
        )

    mutation_payload = copy.deepcopy(sakana_payload)
    mutation_packet = mutation_payload["agent_instruction_packet"]
    mutation_packet["prompt_resources"][0]["path"] = "brick_protocol/agent/prompts/dev.md"
    mutation_packet["tool_policy_resources"][0]["path"] = "brick_protocol/agent/tool_policies/read-write-scoped.yaml"
    mutation_packet["hook_resources"]["registry_path"] = "brick_protocol/agent/hooks/registry.yaml"
    try:
        _assert_sakana_wire_has_no_resource_paths(mutation_payload, label="mutation-RED")
    except ProfileError:
        pass
    else:
        raise ProfileError("mutation-RED failed: re-exposed sakana path label was accepted")

    return KernelResult(
        check_id="sakana_wire_packet",
        inspected=4,
        output=(
            "codex-local prompt packet preserved resource path labels; "
            "codex-fugu-local prompt packet omitted resource path labels; "
            "codex-fugu-local without spec wire flag preserved resource path labels; "
            "local evidence packet preserved resource ref->path mappings; "
            "mutation-RED observed: re-exposed sakana resource path labels are rejected"
        ),
    )
